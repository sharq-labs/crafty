"""M5L — checkpoint, resume and idempotency.

A research campaign spends real compute and admits real scientific evidence, so
an interrupted run must resume without doing either twice. Every side effect
that must happen at most once is recorded by :class:`EffectLedger` under a
deterministic key. Legacy serialization remains unchanged; Core V0.3 adds only
an in-memory append-order view so incremental persistence can read effect deltas
without rescanning the entire applied mapping at every checkpoint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, TypeVar

from ...scientific.serialization import require_schema, schema_string
from ..decision.replay import canonical_digest
from .budget import BudgetLedger
from .events import CampaignEventLog
from .state import CampaignRun

EFFECT_SCHEMA = schema_string("sria_campaign_effect_ledger")
CHECKPOINT_SCHEMA = schema_string("sria_campaign_checkpoint")
PLAN_SCHEMA = schema_string("sria_campaign_iteration_plan")

T = TypeVar("T")


@dataclass(frozen=True)
class IterationPlan:
    """The exact artifacts one iteration was decided on, stored before it runs."""

    iteration: int
    snapshot: Any
    manifest: Any
    recommendation: Any
    action: Any
    charter_version: str = ""
    campaign_id: str = ""
    predicted_cost: float | None = None
    liveness_reason: str = ""

    def __post_init__(self) -> None:
        if self.iteration < 1:
            raise ValueError("an iteration plan starts at iteration 1")
        for label in ("snapshot", "manifest", "recommendation", "action"):
            if getattr(self, label) is None:
                raise ValueError(
                    f"an iteration plan requires the exact {label} it was "
                    f"decided on; a plan missing one cannot be resumed without "
                    f"re-deciding"
                )

    @property
    def action_id(self) -> str:
        return self.action.action_id

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PLAN_SCHEMA,
            "iteration": self.iteration,
            "snapshot": self.snapshot.to_dict(),
            "manifest": self.manifest.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "action": self.action.to_dict(),
            "charter_version": self.charter_version,
            "campaign_id": self.campaign_id,
            "predicted_cost": self.predicted_cost,
            "liveness_reason": self.liveness_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IterationPlan":
        require_schema(payload, PLAN_SCHEMA)
        from ..decision.actions import AtomicAction, CompositeAction
        from ..decision.belief_snapshot import BeliefSnapshot
        from ..decision.recommendation import DecisionRecommendation
        from ..decision.replay import ExecutionDependencyManifest

        raw_action = payload["action"]
        action_type = CompositeAction if "composite_id" in raw_action else AtomicAction
        return cls(
            iteration=int(payload["iteration"]),
            snapshot=BeliefSnapshot.from_dict(payload["snapshot"]),
            manifest=ExecutionDependencyManifest.from_dict(payload["manifest"]),
            recommendation=DecisionRecommendation.from_dict(payload["recommendation"]),
            action=action_type.from_dict(raw_action),
            charter_version=payload.get("charter_version", ""),
            campaign_id=payload.get("campaign_id", ""),
            predicted_cost=payload.get("predicted_cost"),
            liveness_reason=payload.get("liveness_reason", ""),
        )


class ResumeViolation(Exception):
    """A resume attempted something the recorded history forbids."""


@dataclass
class EffectLedger:
    """Records which at-most-once effects have already happened.

    ``_journal`` is an in-memory V0.3 acceleration only. It is deliberately not
    serialized, so the frozen V0.2 wire shape and digest semantics are unchanged.
    Reconstructing it once on load is O(N), which the V0.3 preregistration
    explicitly permits; persistence can then consume only newly appended effects.
    """

    applied: dict[str, str] = field(default_factory=dict)
    _journal: list[tuple[str, str]] = field(
        default_factory=list, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self.applied = {str(k): str(v) for k, v in dict(self.applied).items()}
        self._journal = list(self.applied.items())

    def key(self, run_id: str, iteration: int, kind: str, subject: str) -> str:
        return f"{run_id}:{iteration}:{kind}:{subject}"

    def is_applied(self, key: str) -> bool:
        return key in self.applied

    def reference(self, key: str) -> str:
        return self.applied.get(key, "")

    @property
    def journal_length(self) -> int:
        return len(self._journal)

    def entry_at(self, index: int) -> tuple[str, str]:
        return self._journal[index]

    def entries_from(self, index: int) -> tuple[tuple[str, str], ...]:
        """Return effect deltas without rescanning the committed prefix."""
        if index < 0 or index > len(self._journal):
            raise ResumeViolation(
                f"effect journal cursor {index} outside 0..{len(self._journal)}"
            )
        if len(self.applied) != len(self._journal):
            raise ResumeViolation(
                "effect mapping changed outside EffectLedger.mark/once; "
                "append history can no longer be trusted"
            )
        return tuple(self._journal[index:])

    def once(
        self,
        key: str,
        effect: Callable[[], T],
        *,
        reference: Callable[[T], str] = lambda value: "",
    ) -> tuple[T | None, bool]:
        """Run ``effect`` only if ``key`` has not already been applied."""
        if key in self.applied:
            return None, False
        value = effect()
        self.mark(key, str(reference(value)))
        return value, True

    def mark(self, key: str, reference: str = "") -> None:
        """Record an effect performed elsewhere. Refuses to overwrite."""
        key = str(key)
        if key in self.applied:
            raise ResumeViolation(
                f"effect {key!r} is already recorded as applied; recording it "
                f"again would license a duplicate side effect"
            )
        ref = str(reference)
        self.applied[key] = ref
        self._journal.append((key, ref))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": EFFECT_SCHEMA,
            "applied": dict(sorted(self.applied.items())),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EffectLedger":
        require_schema(payload, EFFECT_SCHEMA)
        return cls(applied=dict(payload.get("applied", {})))


@dataclass(frozen=True)
class CampaignCheckpoint:
    """Everything needed to resume, and nothing that would need recomputing."""

    run: CampaignRun
    events: CampaignEventLog
    budget: BudgetLedger
    effects: EffectLedger
    plan: IterationPlan | None = None
    obligation_state: Mapping[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "obligation_state",
            {str(k): bool(v) for k, v in dict(self.obligation_state).items()},
        )
        if self.events.run_id != self.run.run_id:
            raise ResumeViolation(
                f"event log belongs to run {self.events.run_id!r}, checkpoint to "
                f"{self.run.run_id!r}"
            )
        self.events.verify_chain()

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CHECKPOINT_SCHEMA,
            "run": self.run.to_dict(),
            "events": self.events.to_dict(),
            "budget": self.budget.to_dict(),
            "effects": self.effects.to_dict(),
            "plan": self.plan.to_dict() if self.plan else None,
            "obligation_state": dict(sorted(self.obligation_state.items())),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CampaignCheckpoint":
        require_schema(payload, CHECKPOINT_SCHEMA)
        return cls(
            run=CampaignRun.from_dict(payload["run"]),
            events=CampaignEventLog.from_dict(payload["events"]),
            budget=BudgetLedger.from_dict(payload["budget"]),
            effects=EffectLedger.from_dict(payload["effects"]),
            plan=(
                IterationPlan.from_dict(payload["plan"])
                if payload.get("plan")
                else None
            ),
            obligation_state=payload.get("obligation_state", {}),
        )


class CheckpointStore:
    """Append-only legacy checkpoint history for one run."""

    def __init__(self) -> None:
        self._checkpoints: list[CampaignCheckpoint] = []

    def __len__(self) -> int:
        return len(self._checkpoints)

    @property
    def history(self) -> tuple[CampaignCheckpoint, ...]:
        return tuple(self._checkpoints)

    def save(self, checkpoint: CampaignCheckpoint) -> CampaignCheckpoint:
        if self._checkpoints:
            previous = self._checkpoints[-1]
            if previous.run.run_id != checkpoint.run.run_id:
                raise ResumeViolation(
                    "a checkpoint store holds the history of exactly one run"
                )
            if len(checkpoint.events) < len(previous.events):
                raise ResumeViolation(
                    f"checkpoint event log shrank from {len(previous.events)} to "
                    f"{len(checkpoint.events)} entries; history is append-only"
                )
        self._checkpoints.append(checkpoint)
        return checkpoint

    def latest(self) -> CampaignCheckpoint | None:
        return self._checkpoints[-1] if self._checkpoints else None

    def to_dict(self) -> dict[str, Any]:
        return {"checkpoints": [c.to_dict() for c in self._checkpoints]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CheckpointStore":
        store = cls()
        for item in payload.get("checkpoints", ()):
            store._checkpoints.append(CampaignCheckpoint.from_dict(item))
        return store

    def save_to_path(self, path: str | Path) -> Path:
        target = Path(path)
        target.write_text(
            json.dumps(self.to_dict(), sort_keys=True, indent=2), encoding="utf-8"
        )
        return target

    @classmethod
    def load_from_path(cls, path: str | Path) -> "CheckpointStore":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
