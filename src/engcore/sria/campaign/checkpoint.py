"""M5L — checkpoint, resume and idempotency.

A research campaign spends real compute and admits real scientific evidence, so
an interrupted run must resume without doing either twice. "Re-run the loop and
hope it works out" is not a resume strategy: re-executing a completed simulation
burns budget that was already spent, and re-admitting a processed result would
add a second belief contribution from one experiment.

The mechanism is one idea applied uniformly. Every side effect that must happen
at most once is performed through :meth:`EffectLedger.once`, keyed by a
deterministic string derived from the run, iteration and subject. The ledger
records the key **and the result reference** before the effect is considered
done; a repeat call with the same key returns the recorded reference and does
not invoke the effect.

    execute   run:iter:execute:<action_id>
    evidence  run:iter:evidence:<action_id>
    admit     run:iter:admit:<evidence_id>
    calibrate run:iter:calibrate:<record_id>
    charge    run:iter:charge:<action_id>

That covers the four duplications the brief names — execution, admission,
calibration rows, budget — plus M3's single-use authorization, which is
protected twice over: once by the ledger, and once by the frozen
``consume_authorization`` in the admission authority itself.

A checkpoint is the run state, the event log, the budget ledger and the effect
ledger together. Resume rebuilds from the checkpoint and replays nothing.
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
    """The exact artifacts one iteration was decided on, stored before it runs.

    M5 rebuilt these on resume and argued the rebuild was equivalent. M5.1 does
    not rely on the argument. A decision is made against a specific snapshot, a
    specific dependency manifest and a specific candidate; if a resume rebuilds
    any of them it is making a *new* decision wearing the old one's iteration
    number. Storing the artifacts before execution begins removes the question.

    Nothing here is recomputed on load: the snapshot, manifest, recommendation
    and selected action are deserialized as recorded, which is also what keeps
    M4.4 coherence meaningful across a restart.
    """

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
        action_type = (
            CompositeAction
            if "composite_id" in raw_action
            else AtomicAction
        )
        return cls(
            iteration=int(payload["iteration"]),
            snapshot=BeliefSnapshot.from_dict(payload["snapshot"]),
            manifest=ExecutionDependencyManifest.from_dict(payload["manifest"]),
            recommendation=DecisionRecommendation.from_dict(
                payload["recommendation"]
            ),
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

    Not a cache. A cache may forget; this may not. The distinction matters
    because forgetting here means executing a simulation twice or admitting one
    result as two independent pieces of evidence.
    """

    applied: dict[str, str] = field(default_factory=dict)

    def key(self, run_id: str, iteration: int, kind: str, subject: str) -> str:
        return f"{run_id}:{iteration}:{kind}:{subject}"

    def is_applied(self, key: str) -> bool:
        return key in self.applied

    def reference(self, key: str) -> str:
        return self.applied.get(key, "")

    def once(
        self,
        key: str,
        effect: Callable[[], T],
        *,
        reference: Callable[[T], str] = lambda value: "",
    ) -> tuple[T | None, bool]:
        """Run ``effect`` only if ``key`` has not been applied.

        Returns ``(value, performed)``. On a repeat the value is ``None`` and
        ``performed`` is ``False`` — the caller is expected to consult
        :meth:`reference` rather than re-deriving the result, because
        re-deriving it is exactly what must not happen.
        """
        if key in self.applied:
            return None, False
        value = effect()
        self.applied[key] = str(reference(value))
        return value, True

    def mark(self, key: str, reference: str = "") -> None:
        """Record an effect performed elsewhere. Refuses to overwrite."""
        if key in self.applied:
            raise ResumeViolation(
                f"effect {key!r} is already recorded as applied; recording it "
                f"again would license a duplicate side effect"
            )
        self.applied[key] = str(reference)

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
    #: The in-flight iteration's exact decision artifacts, if one is in flight.
    plan: IterationPlan | None = None
    #: Which declared validation obligations have been assessed, and how.
    #:
    #: Durable because it is *scientific* state, not bookkeeping: it feeds the
    #: next snapshot's ``obligation_state`` (and therefore its digest), the
    #: validation-liveness reachability check, and the Arbiter's stopping
    #: review. Losing it on restart silently rewinds the campaign's assurance
    #: record to "nothing has ever been assessed".
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
    """Append-only checkpoint history for one run.

    Keeps every checkpoint rather than overwriting, so a resume can be audited
    against the state it actually resumed from. ``latest()`` is what a resume
    reads; the earlier entries are what an auditor reads.
    """

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
