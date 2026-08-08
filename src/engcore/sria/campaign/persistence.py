"""Core V0.3 — incremental, digest-committed campaign persistence.

The legacy checkpoint representation is logically correct but stores repeated
prefixes of growing campaign history. V0.3 stores each historical fact once in
append-only journals and lets compact checkpoints commit to exact journal
prefixes by count + head digest.

The persistence layer materializes the legacy ``CampaignCheckpoint`` shape on
resume. Storage changes; decision, evidence, budget, stopping and scientific
semantics do not.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ...scientific.serialization import require_schema, schema_string
from ..decision.replay import canonical_digest
from .budget import BudgetCharge, BudgetLedger
from .checkpoint import (
    CampaignCheckpoint,
    CheckpointStore as LegacyCheckpointStore,
    EffectLedger,
    IterationPlan,
    ResumeViolation,
)
from .events import CampaignEvent, CampaignEventLog
from .state import CampaignRun, ExecutionState, IterationRecord, PauseReason

PERSISTENCE_SCHEMA = schema_string("sria_campaign_persistence_store", 2)
BUDGET_DECLARATION_SCHEMA = schema_string("sria_campaign_budget_declaration_v3", 1)
BUDGET_JOURNAL_SCHEMA = schema_string("sria_campaign_budget_journal_entry", 1)
EFFECT_JOURNAL_SCHEMA = schema_string("sria_campaign_effect_journal_entry", 1)
ITERATION_JOURNAL_SCHEMA = schema_string("sria_campaign_iteration_journal_entry", 1)
RUN_STATE_SCHEMA = schema_string("sria_campaign_compact_run_state", 1)
CHECKPOINT_V3_SCHEMA = schema_string("sria_campaign_checkpoint_v3", 2)


class PersistenceIntegrityError(ResumeViolation):
    """Stored persistence state cannot be trusted for deterministic resume."""


class _ImmutableCheckpointMapping(dict[str, Any]):
    """Dict-compatible checkpoint payload mapping that rejects mutation."""

    _MUTATION_MESSAGE = "checkpoint record mappings are immutable"

    def _reject_mutation(self, *args: Any, **kwargs: Any) -> None:
        raise PersistenceIntegrityError(self._MUTATION_MESSAGE)

    def __setitem__(self, key: str, value: Any) -> None:
        self._reject_mutation()

    def __delitem__(self, key: str) -> None:
        self._reject_mutation()

    def clear(self) -> None:
        self._reject_mutation()

    def pop(self, key: str, default: Any = None) -> Any:
        self._reject_mutation()

    def popitem(self) -> tuple[str, Any]:
        self._reject_mutation()

    def setdefault(self, key: str, default: Any = None) -> Any:
        self._reject_mutation()

    def update(self, *args: Any, **kwargs: Any) -> None:
        self._reject_mutation()

    def __ior__(self, other: Mapping[str, Any]) -> "_ImmutableCheckpointMapping":
        self._reject_mutation()


class _ImmutableCheckpointList(list[Any]):
    """List-compatible checkpoint payload sequence that rejects mutation."""

    _MUTATION_MESSAGE = "checkpoint record sequences are immutable"

    def _reject_mutation(self, *args: Any, **kwargs: Any) -> None:
        raise PersistenceIntegrityError(self._MUTATION_MESSAGE)

    def __setitem__(self, index: Any, value: Any) -> None:
        self._reject_mutation()

    def __delitem__(self, index: Any) -> None:
        self._reject_mutation()

    def append(self, value: Any) -> None:
        self._reject_mutation()

    def clear(self) -> None:
        self._reject_mutation()

    def extend(self, values: Any) -> None:
        self._reject_mutation()

    def insert(self, index: int, value: Any) -> None:
        self._reject_mutation()

    def pop(self, index: int = -1) -> Any:
        self._reject_mutation()

    def remove(self, value: Any) -> None:
        self._reject_mutation()

    def reverse(self) -> None:
        self._reject_mutation()

    def sort(self, *args: Any, **kwargs: Any) -> None:
        self._reject_mutation()

    def __iadd__(self, values: Any) -> "_ImmutableCheckpointList":
        self._reject_mutation()

    def __imul__(self, value: int) -> "_ImmutableCheckpointList":
        self._reject_mutation()


def _freeze_checkpoint_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _ImmutableCheckpointMapping(
            {
                str(key): _freeze_checkpoint_payload(item)
                for key, item in dict(value).items()
            }
        )
    if isinstance(value, list | tuple):
        return _ImmutableCheckpointList(
            [_freeze_checkpoint_payload(item) for item in value]
        )
    return value


def _thaw_checkpoint_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _thaw_checkpoint_payload(item)
            for key, item in sorted(dict(value).items())
        }
    if isinstance(value, list | tuple):
        return [_thaw_checkpoint_payload(item) for item in value]
    return value


@dataclass(frozen=True)
class BudgetDeclaration:
    """Run-level budget configuration stored once rather than per checkpoint."""

    total_budget: float
    reserved_validation_budget: float = 0.0
    cost_unit: str = "hour"
    enforced_cap: float | None = None
    enforced_cap_source: str = ""

    def __post_init__(self) -> None:
        total = float(self.total_budget)
        reserved = float(self.reserved_validation_budget)
        if not math.isfinite(total) or total < 0.0:
            raise ValueError("total budget must be finite and non-negative")
        if not math.isfinite(reserved) or reserved < 0.0:
            raise ValueError("reserved validation budget must be finite and non-negative")
        if reserved > total:
            raise ValueError("reserved validation budget exceeds total budget")
        object.__setattr__(self, "total_budget", total)
        object.__setattr__(self, "reserved_validation_budget", reserved)
        if self.enforced_cap is not None:
            cap = float(self.enforced_cap)
            if not math.isfinite(cap) or cap < 0.0:
                raise ValueError("enforced cap must be finite and non-negative")
            if not str(self.enforced_cap_source).strip():
                raise ValueError("an enforced cap must name what enforces it")
            object.__setattr__(self, "enforced_cap", cap)

    @classmethod
    def from_ledger(cls, ledger: BudgetLedger) -> "BudgetDeclaration":
        return cls(
            total_budget=ledger.total_budget,
            reserved_validation_budget=ledger.reserved_validation_budget,
            cost_unit=ledger.cost_unit,
            enforced_cap=ledger.enforced_cap,
            enforced_cap_source=ledger.enforced_cap_source,
        )

    def materialize(self, charges: tuple[BudgetCharge, ...]) -> BudgetLedger:
        return BudgetLedger(
            total_budget=self.total_budget,
            reserved_validation_budget=self.reserved_validation_budget,
            charges=charges,
            cost_unit=self.cost_unit,
            enforced_cap=self.enforced_cap,
            enforced_cap_source=self.enforced_cap_source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BUDGET_DECLARATION_SCHEMA,
            "total_budget": self.total_budget,
            "reserved_validation_budget": self.reserved_validation_budget,
            "cost_unit": self.cost_unit,
            "enforced_cap": self.enforced_cap,
            "enforced_cap_source": self.enforced_cap_source,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BudgetDeclaration":
        require_schema(payload, BUDGET_DECLARATION_SCHEMA)
        return cls(
            total_budget=float(payload["total_budget"]),
            reserved_validation_budget=float(
                payload.get("reserved_validation_budget", 0.0)
            ),
            cost_unit=payload.get("cost_unit", "hour"),
            enforced_cap=payload.get("enforced_cap"),
            enforced_cap_source=payload.get("enforced_cap_source", ""),
        )


@dataclass(frozen=True)
class BudgetJournalEntry:
    sequence: int
    charge: BudgetCharge
    prev_digest: str = ""

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("budget journal sequence must be non-negative")

    def _chain_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "charge": self.charge.to_dict(),
            "prev_digest": self.prev_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self._chain_payload())

    def to_dict(self) -> dict[str, Any]:
        return {"schema": BUDGET_JOURNAL_SCHEMA, **self._chain_payload()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BudgetJournalEntry":
        require_schema(payload, BUDGET_JOURNAL_SCHEMA)
        return cls(
            sequence=int(payload["sequence"]),
            charge=BudgetCharge.from_dict(payload["charge"]),
            prev_digest=payload.get("prev_digest", ""),
        )


@dataclass(frozen=True)
class EffectJournalEntry:
    sequence: int
    key: str
    reference: str = ""
    prev_digest: str = ""

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("effect journal sequence must be non-negative")
        if not str(self.key).strip():
            raise ValueError("effect journal entry requires a key")

    def _chain_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "key": self.key,
            "reference": self.reference,
            "prev_digest": self.prev_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self._chain_payload())

    def to_dict(self) -> dict[str, Any]:
        return {"schema": EFFECT_JOURNAL_SCHEMA, **self._chain_payload()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EffectJournalEntry":
        require_schema(payload, EFFECT_JOURNAL_SCHEMA)
        return cls(
            sequence=int(payload["sequence"]),
            key=payload["key"],
            reference=payload.get("reference", ""),
            prev_digest=payload.get("prev_digest", ""),
        )


@dataclass(frozen=True)
class IterationJournalEntry:
    sequence: int
    record: IterationRecord
    prev_digest: str = ""

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("iteration journal sequence must be non-negative")

    def _chain_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "record": self.record.to_dict(),
            "prev_digest": self.prev_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self._chain_payload())

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ITERATION_JOURNAL_SCHEMA, **self._chain_payload()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IterationJournalEntry":
        require_schema(payload, ITERATION_JOURNAL_SCHEMA)
        return cls(
            sequence=int(payload["sequence"]),
            record=IterationRecord.from_dict(payload["record"]),
            prev_digest=payload.get("prev_digest", ""),
        )


@dataclass(frozen=True)
class CompactRunState:
    """Current ``CampaignRun`` state without cumulative iteration history."""

    run_id: str
    campaign_id: str
    charter_version: str = ""
    state: ExecutionState = ExecutionState.CREATED
    iteration: int = 0
    max_iterations: int = 1
    active_snapshot_digest: str = ""
    active_basis_digest: str = ""
    stop_proposal_recommendation_id: str = ""
    stop_review_outcome: str = ""
    pause_reason: PauseReason | None = None
    failure_reason: str = ""
    event_log_digest: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.run_id).strip() or not str(self.campaign_id).strip():
            raise ValueError("compact run state requires run_id and campaign_id")
        object.__setattr__(self, "state", ExecutionState(self.state))
        if self.pause_reason is not None:
            object.__setattr__(self, "pause_reason", PauseReason(self.pause_reason))
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if self.iteration < 0:
            raise ValueError("iteration must be non-negative")
        if self.state is ExecutionState.PAUSED and self.pause_reason is None:
            raise ValueError("a paused compact run state must record why")
        if self.state is ExecutionState.FAILED and not self.failure_reason.strip():
            raise ValueError("a failed compact run state must record why")
        object.__setattr__(
            self, "metadata", _freeze_checkpoint_payload(dict(self.metadata))
        )

    @classmethod
    def from_run(cls, run: CampaignRun) -> "CompactRunState":
        return cls(
            run_id=run.run_id,
            campaign_id=run.campaign_id,
            charter_version=run.charter_version,
            state=run.state,
            iteration=run.iteration,
            max_iterations=run.max_iterations,
            active_snapshot_digest=run.active_snapshot_digest,
            active_basis_digest=run.active_basis_digest,
            stop_proposal_recommendation_id=run.stop_proposal_recommendation_id,
            stop_review_outcome=run.stop_review_outcome,
            pause_reason=run.pause_reason,
            failure_reason=run.failure_reason,
            event_log_digest=run.event_log_digest,
            metadata=run.metadata,
        )

    def materialize(self, iterations: tuple[IterationRecord, ...]) -> CampaignRun:
        return CampaignRun(
            run_id=self.run_id,
            campaign_id=self.campaign_id,
            charter_version=self.charter_version,
            state=self.state,
            iteration=self.iteration,
            max_iterations=self.max_iterations,
            iterations=iterations,
            active_snapshot_digest=self.active_snapshot_digest,
            active_basis_digest=self.active_basis_digest,
            stop_proposal_recommendation_id=self.stop_proposal_recommendation_id,
            stop_review_outcome=self.stop_review_outcome,
            pause_reason=self.pause_reason,
            failure_reason=self.failure_reason,
            event_log_digest=self.event_log_digest,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RUN_STATE_SCHEMA,
            "run_id": self.run_id,
            "campaign_id": self.campaign_id,
            "charter_version": self.charter_version,
            "state": self.state.value,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "active_snapshot_digest": self.active_snapshot_digest,
            "active_basis_digest": self.active_basis_digest,
            "stop_proposal_recommendation_id": self.stop_proposal_recommendation_id,
            "stop_review_outcome": self.stop_review_outcome,
            "pause_reason": self.pause_reason.value if self.pause_reason else None,
            "failure_reason": self.failure_reason,
            "event_log_digest": self.event_log_digest,
            "metadata": _thaw_checkpoint_payload(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompactRunState":
        require_schema(payload, RUN_STATE_SCHEMA)
        return cls(
            run_id=payload["run_id"],
            campaign_id=payload["campaign_id"],
            charter_version=payload.get("charter_version", ""),
            state=ExecutionState(payload.get("state", "created")),
            iteration=int(payload.get("iteration", 0)),
            max_iterations=int(payload.get("max_iterations", 1)),
            active_snapshot_digest=payload.get("active_snapshot_digest", ""),
            active_basis_digest=payload.get("active_basis_digest", ""),
            stop_proposal_recommendation_id=payload.get(
                "stop_proposal_recommendation_id", ""
            ),
            stop_review_outcome=payload.get("stop_review_outcome", ""),
            pause_reason=(
                PauseReason(payload["pause_reason"])
                if payload.get("pause_reason")
                else None
            ),
            failure_reason=payload.get("failure_reason", ""),
            event_log_digest=payload.get("event_log_digest", ""),
            metadata=payload.get("metadata", {}),
        )


@dataclass(frozen=True)
class CampaignCheckpointV3:
    """Compact resumable state committing to exact journal prefixes."""

    checkpoint_sequence: int
    run_state: CompactRunState
    event_count: int
    event_head_digest: str
    budget_charge_count: int
    budget_head_digest: str
    budget_declaration_digest: str
    effect_count: int
    effect_head_digest: str
    iteration_record_count: int
    iteration_head_digest: str
    spent_general: float
    spent_validation: float
    spent_total: float
    budget_overrun: float
    plan: IterationPlan | None = None
    obligation_state: Mapping[str, bool] = field(default_factory=dict)
    previous_checkpoint_digest: str = ""

    def __post_init__(self) -> None:
        if self.checkpoint_sequence < 0:
            raise ValueError("checkpoint sequence must be non-negative")
        for label in (
            "event_count",
            "budget_charge_count",
            "effect_count",
            "iteration_record_count",
        ):
            if int(getattr(self, label)) < 0:
                raise ValueError(f"{label} must be non-negative")
        if not str(self.budget_declaration_digest).strip():
            raise ValueError("checkpoint requires a budget declaration digest")
        for label in (
            "spent_general",
            "spent_validation",
            "spent_total",
            "budget_overrun",
        ):
            number = float(getattr(self, label))
            if not math.isfinite(number) or number < 0.0:
                raise ValueError(f"{label} must be finite and non-negative")
        object.__setattr__(
            self,
            "obligation_state",
            _ImmutableCheckpointMapping(
                {str(k): bool(v) for k, v in dict(self.obligation_state).items()}
            ),
        )

    def _chain_payload(self) -> dict[str, Any]:
        return {
            "checkpoint_sequence": self.checkpoint_sequence,
            "run_state": self.run_state.to_dict(),
            "event_count": self.event_count,
            "event_head_digest": self.event_head_digest,
            "budget_charge_count": self.budget_charge_count,
            "budget_head_digest": self.budget_head_digest,
            "budget_declaration_digest": self.budget_declaration_digest,
            "effect_count": self.effect_count,
            "effect_head_digest": self.effect_head_digest,
            "iteration_record_count": self.iteration_record_count,
            "iteration_head_digest": self.iteration_head_digest,
            "spent_general": self.spent_general,
            "spent_validation": self.spent_validation,
            "spent_total": self.spent_total,
            "budget_overrun": self.budget_overrun,
            "plan": self.plan.to_dict() if self.plan else None,
            "obligation_state": dict(sorted(self.obligation_state.items())),
            "previous_checkpoint_digest": self.previous_checkpoint_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self._chain_payload())

    def to_dict(self) -> dict[str, Any]:
        return {"schema": CHECKPOINT_V3_SCHEMA, **self._chain_payload()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CampaignCheckpointV3":
        require_schema(payload, CHECKPOINT_V3_SCHEMA)
        if not payload.get("budget_declaration_digest"):
            raise PersistenceIntegrityError(
                "checkpoint is missing budget declaration commitment"
            )
        return cls(
            checkpoint_sequence=int(payload["checkpoint_sequence"]),
            run_state=CompactRunState.from_dict(payload["run_state"]),
            event_count=int(payload.get("event_count", 0)),
            event_head_digest=payload.get("event_head_digest", ""),
            budget_charge_count=int(payload.get("budget_charge_count", 0)),
            budget_head_digest=payload.get("budget_head_digest", ""),
            budget_declaration_digest=payload["budget_declaration_digest"],
            effect_count=int(payload.get("effect_count", 0)),
            effect_head_digest=payload.get("effect_head_digest", ""),
            iteration_record_count=int(payload.get("iteration_record_count", 0)),
            iteration_head_digest=payload.get("iteration_head_digest", ""),
            spent_general=float(payload.get("spent_general", 0.0)),
            spent_validation=float(payload.get("spent_validation", 0.0)),
            spent_total=float(payload.get("spent_total", 0.0)),
            budget_overrun=float(payload.get("budget_overrun", 0.0)),
            plan=(
                IterationPlan.from_dict(payload["plan"])
                if payload.get("plan")
                else None
            ),
            obligation_state=payload.get("obligation_state", {}),
            previous_checkpoint_digest=payload.get("previous_checkpoint_digest", ""),
        )


class IncrementalCheckpointStore:
    """Append-only V0.3 journals plus compact checkpoint commitments."""

    def __init__(
        self,
        *,
        run_id: str = "",
        budget_declaration: BudgetDeclaration | None = None,
    ) -> None:
        self._run_id = str(run_id)
        self._budget_declaration = budget_declaration
        self._events: list[CampaignEvent] = []
        self._budget_entries: list[BudgetJournalEntry] = []
        self._effect_entries: list[EffectJournalEntry] = []
        self._iteration_entries: list[IterationJournalEntry] = []
        self._checkpoints: list[CampaignCheckpointV3] = []
        self._effect_index: dict[str, str] = {}
        self._spent_general = 0.0
        self._spent_validation = 0.0
        self._spent_total = 0.0

    def __len__(self) -> int:
        return len(self._checkpoints)

    @property
    def records(self) -> tuple[CampaignCheckpointV3, ...]:
        return tuple(self._checkpoints)

    @property
    def event_record_count(self) -> int:
        return len(self._events)

    @property
    def budget_record_count(self) -> int:
        return len(self._budget_entries)

    @property
    def effect_record_count(self) -> int:
        return len(self._effect_entries)

    @property
    def iteration_record_count(self) -> int:
        return len(self._iteration_entries)

    @property
    def latest_record(self) -> CampaignCheckpointV3 | None:
        return self._checkpoints[-1] if self._checkpoints else None

    @property
    def history(self) -> tuple[CampaignCheckpoint, ...]:
        """Materialized compatibility history. Audit path, not save path."""
        return tuple(self.materialize(record) for record in self._checkpoints)

    def latest(self) -> CampaignCheckpoint | None:
        record = self.latest_record
        return self.materialize(record) if record is not None else None

    def _adopt_run_identity(self, run_id: str) -> None:
        run_id = str(run_id)
        if not run_id.strip():
            raise PersistenceIntegrityError("persistence requires a run_id")
        if not self._run_id:
            self._run_id = run_id
        elif self._run_id != run_id:
            raise PersistenceIntegrityError(
                f"store belongs to run {self._run_id!r}, not {run_id!r}"
            )

    def _require_committed_tail(self) -> None:
        if not self._checkpoints:
            if any(
                (
                    self._events,
                    self._budget_entries,
                    self._effect_entries,
                    self._iteration_entries,
                )
            ):
                raise PersistenceIntegrityError(
                    "journals exist without a committed checkpoint; refuse to append"
                )
            return
        head = self._checkpoints[-1]
        lengths = (
            ("event", len(self._events), head.event_count),
            ("budget", len(self._budget_entries), head.budget_charge_count),
            ("effect", len(self._effect_entries), head.effect_count),
            ("iteration", len(self._iteration_entries), head.iteration_record_count),
        )
        extras = [name for name, actual, committed in lengths if actual != committed]
        if extras:
            raise PersistenceIntegrityError(
                "cannot append while uncommitted journal suffixes exist: "
                + ", ".join(extras)
            )

    @staticmethod
    def _same_number(left: float, right: float) -> bool:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)

    def _budget_declaration_digest(self) -> str:
        if self._budget_declaration is None:
            raise PersistenceIntegrityError("checkpoint exists without budget declaration")
        return self._budget_declaration.digest

    def _current_budget_overrun(self) -> float:
        if self._budget_declaration is None:
            return 0.0
        return max(0.0, self._spent_total - self._budget_declaration.total_budget)

    def _sync_events(self, log: CampaignEventLog) -> None:
        if log.run_id != self._run_id:
            raise PersistenceIntegrityError("event log run id does not match store")
        persisted = len(self._events)
        if len(log) < persisted:
            raise PersistenceIntegrityError("event history shrank")
        if persisted:
            existing = log.event_at(persisted - 1)
            if existing.digest != self._events[-1].digest:
                raise PersistenceIntegrityError("event history changed before persisted head")
        previous = self._events[-1].digest if self._events else ""
        for event in log.events_from(persisted):
            expected = len(self._events)
            if event.sequence != expected:
                raise PersistenceIntegrityError(
                    f"event sequence {event.sequence} does not continue at {expected}"
                )
            if event.run_id != self._run_id:
                raise PersistenceIntegrityError("event belongs to a different run")
            if event.prev_digest != previous:
                raise PersistenceIntegrityError("new event does not follow persisted head")
            self._events.append(event)
            previous = event.digest

    def _sync_budget(
        self, ledger: BudgetLedger, *, legacy_prefix_validation: bool = False
    ) -> None:
        declaration = BudgetDeclaration.from_ledger(ledger)
        if self._budget_declaration is None:
            self._budget_declaration = declaration
        elif self._budget_declaration != declaration:
            raise PersistenceIntegrityError("budget declaration changed across checkpoints")

        persisted = len(self._budget_entries)
        if len(ledger.charges) < persisted:
            raise PersistenceIntegrityError("budget charge history shrank")
        if legacy_prefix_validation:
            for index, (incoming, existing) in enumerate(
                zip(ledger.charges[:persisted], self._budget_entries)
            ):
                if incoming.to_dict() != existing.charge.to_dict():
                    raise PersistenceIntegrityError(
                        f"legacy budget history changed before persisted head at "
                        f"charge {index}"
                    )
        elif persisted and (
            ledger.charges[persisted - 1].to_dict()
            != self._budget_entries[-1].charge.to_dict()
        ):
            raise PersistenceIntegrityError("budget history changed before persisted head")
        previous = self._budget_entries[-1].digest if self._budget_entries else ""
        for charge in ledger.charges[persisted:]:
            entry = BudgetJournalEntry(
                sequence=len(self._budget_entries),
                charge=charge,
                prev_digest=previous,
            )
            self._budget_entries.append(entry)
            self._spent_general += float(charge.from_general_pool)
            self._spent_validation += float(charge.from_validation_reservation)
            self._spent_total += float(charge.realized)
            previous = entry.digest

    def _append_effect_items(self, items) -> None:
        previous = self._effect_entries[-1].digest if self._effect_entries else ""
        for key, reference in items:
            key = str(key)
            reference = str(reference)
            if key in self._effect_index:
                raise PersistenceIntegrityError(
                    f"effect key {key!r} would be appended twice"
                )
            entry = EffectJournalEntry(
                sequence=len(self._effect_entries),
                key=key,
                reference=reference,
                prev_digest=previous,
            )
            self._effect_entries.append(entry)
            self._effect_index[key] = reference
            previous = entry.digest

    def _sync_effects(self, ledger: EffectLedger, *, legacy_scan: bool = False) -> None:
        persisted = len(self._effect_entries)
        if legacy_scan:
            # One-time migration compatibility: old serialized EffectLedger
            # mappings are sorted by key, so order is not a stable prefix across
            # legacy checkpoints. Migration may pay O(N); normal V0.3 saves may not.
            for key, reference in self._effect_index.items():
                if ledger.applied.get(key) != reference:
                    raise PersistenceIntegrityError(
                        f"applied effect {key!r} changed or disappeared"
                    )
            items = sorted(
                (key, reference)
                for key, reference in ledger.applied.items()
                if key not in self._effect_index
            )
            self._append_effect_items(items)
            return

        try:
            if ledger.journal_length < persisted:
                raise PersistenceIntegrityError("effect history shrank")
            if persisted:
                expected = (
                    self._effect_entries[-1].key,
                    self._effect_entries[-1].reference,
                )
                if ledger.entry_at(persisted - 1) != expected:
                    raise PersistenceIntegrityError(
                        "effect history changed before persisted head"
                    )
            items = ledger.entries_from(persisted)
        except ResumeViolation as exc:
            raise PersistenceIntegrityError(str(exc)) from exc
        self._append_effect_items(items)

    def _sync_iterations(
        self, run: CampaignRun, *, legacy_prefix_validation: bool = False
    ) -> None:
        persisted = len(self._iteration_entries)
        if len(run.iterations) < persisted:
            raise PersistenceIntegrityError("iteration history shrank")
        if legacy_prefix_validation:
            for index, (incoming, existing) in enumerate(
                zip(run.iterations[:persisted], self._iteration_entries)
            ):
                if incoming.to_dict() != existing.record.to_dict():
                    raise PersistenceIntegrityError(
                        f"legacy iteration history changed before persisted head "
                        f"at record {index}"
                    )
        elif persisted and (
            run.iterations[persisted - 1].to_dict()
            != self._iteration_entries[-1].record.to_dict()
        ):
            raise PersistenceIntegrityError("iteration history changed before persisted head")
        previous = self._iteration_entries[-1].digest if self._iteration_entries else ""
        for record in run.iterations[persisted:]:
            entry = IterationJournalEntry(
                sequence=len(self._iteration_entries),
                record=record,
                prev_digest=previous,
            )
            self._iteration_entries.append(entry)
            previous = entry.digest

    def save_state(
        self,
        *,
        run: CampaignRun,
        events: CampaignEventLog,
        budget: BudgetLedger,
        effects: EffectLedger,
        plan: IterationPlan | None = None,
        obligation_state: Mapping[str, bool] | None = None,
        _legacy_effect_scan: bool = False,
        _legacy_budget_prefix_validation: bool = False,
        _legacy_iteration_prefix_validation: bool = False,
    ) -> CampaignCheckpointV3:
        """Persist only deltas plus one compact current-state checkpoint."""
        self._adopt_run_identity(run.run_id)
        self._require_committed_tail()
        self._sync_events(events)
        self._sync_budget(
            budget,
            legacy_prefix_validation=_legacy_budget_prefix_validation,
        )
        self._sync_effects(effects, legacy_scan=_legacy_effect_scan)
        self._sync_iterations(
            run,
            legacy_prefix_validation=_legacy_iteration_prefix_validation,
        )

        previous = self._checkpoints[-1] if self._checkpoints else None
        record = CampaignCheckpointV3(
            checkpoint_sequence=len(self._checkpoints),
            run_state=CompactRunState.from_run(run),
            event_count=len(self._events),
            event_head_digest=self._events[-1].digest if self._events else "",
            budget_charge_count=len(self._budget_entries),
            budget_head_digest=(
                self._budget_entries[-1].digest if self._budget_entries else ""
            ),
            budget_declaration_digest=self._budget_declaration_digest(),
            effect_count=len(self._effect_entries),
            effect_head_digest=(
                self._effect_entries[-1].digest if self._effect_entries else ""
            ),
            iteration_record_count=len(self._iteration_entries),
            iteration_head_digest=(
                self._iteration_entries[-1].digest if self._iteration_entries else ""
            ),
            spent_general=self._spent_general,
            spent_validation=self._spent_validation,
            spent_total=self._spent_total,
            budget_overrun=self._current_budget_overrun(),
            plan=plan,
            obligation_state=obligation_state or {},
            previous_checkpoint_digest=previous.digest if previous else "",
        )
        self._verify_new_checkpoint(record, previous)
        self._checkpoints.append(record)
        return record

    def _verify_new_checkpoint(
        self,
        checkpoint: CampaignCheckpointV3,
        previous: CampaignCheckpointV3 | None,
    ) -> None:
        expected_sequence = 0 if previous is None else previous.checkpoint_sequence + 1
        if checkpoint.checkpoint_sequence != expected_sequence:
            raise PersistenceIntegrityError(
                f"new checkpoint declares sequence {checkpoint.checkpoint_sequence}; "
                f"expected {expected_sequence}"
            )
        expected_previous = previous.digest if previous is not None else ""
        if checkpoint.previous_checkpoint_digest != expected_previous:
            raise PersistenceIntegrityError("new checkpoint does not follow persisted head")
        if checkpoint.run_state.run_id != self._run_id:
            raise PersistenceIntegrityError("checkpoint belongs to another run")
        if checkpoint.budget_declaration_digest != self._budget_declaration_digest():
            raise PersistenceIntegrityError(
                "new checkpoint budget declaration commitment disagrees with store"
            )
        if previous is not None:
            old_counts = (
                previous.event_count,
                previous.budget_charge_count,
                previous.effect_count,
                previous.iteration_record_count,
            )
            new_counts = (
                checkpoint.event_count,
                checkpoint.budget_charge_count,
                checkpoint.effect_count,
                checkpoint.iteration_record_count,
            )
            if any(now < old for now, old in zip(new_counts, old_counts)):
                raise PersistenceIntegrityError("a checkpoint journal cursor shrank")
        self._verify_checkpoint_commitment(checkpoint, verify_budget=False)

    def save(self, checkpoint: CampaignCheckpoint) -> CampaignCheckpointV3:
        return self.save_state(
            run=checkpoint.run,
            events=checkpoint.events,
            budget=checkpoint.budget,
            effects=checkpoint.effects,
            plan=checkpoint.plan,
            obligation_state=checkpoint.obligation_state,
            _legacy_effect_scan=True,
            _legacy_budget_prefix_validation=True,
            _legacy_iteration_prefix_validation=True,
        )

    @staticmethod
    def _verify_journal_prefix(entries, count: int, head_digest: str, label: str) -> None:
        if count < 0 or count > len(entries):
            raise PersistenceIntegrityError(
                f"{label} checkpoint cursor {count} exceeds journal length {len(entries)}"
            )
        if count == 0:
            if head_digest:
                raise PersistenceIntegrityError(
                    f"empty {label} prefix declares a non-empty head digest"
                )
            return
        if entries[count - 1].digest != head_digest:
            raise PersistenceIntegrityError(
                f"{label} checkpoint head digest does not match committed prefix"
            )

    @staticmethod
    def _verify_chained_entries(entries, count: int, label: str) -> None:
        previous = ""
        for index, entry in enumerate(entries[:count]):
            if entry.sequence != index:
                raise PersistenceIntegrityError(
                    f"{label} entry {index} declares sequence {entry.sequence}"
                )
            if entry.prev_digest != previous:
                raise PersistenceIntegrityError(
                    f"{label} entry {index} does not follow its predecessor"
                )
            previous = entry.digest

    def _verify_event_chain(self, count: int) -> None:
        previous = ""
        for index, event in enumerate(self._events[:count]):
            if event.sequence != index:
                raise PersistenceIntegrityError(
                    f"event {index} declares sequence {event.sequence}"
                )
            if event.run_id != self._run_id:
                raise PersistenceIntegrityError(
                    f"event {index} belongs to run {event.run_id!r}"
                )
            if event.prev_digest != previous:
                raise PersistenceIntegrityError(
                    f"event {index} does not follow its predecessor"
                )
            previous = event.digest

    def _verify_checkpoint_chain(self) -> None:
        previous_digest = ""
        previous_counts = (0, 0, 0, 0)
        for index, checkpoint in enumerate(self._checkpoints):
            if checkpoint.checkpoint_sequence != index:
                raise PersistenceIntegrityError(
                    f"checkpoint {index} declares sequence "
                    f"{checkpoint.checkpoint_sequence}"
                )
            if checkpoint.previous_checkpoint_digest != previous_digest:
                raise PersistenceIntegrityError(
                    f"checkpoint {index} does not follow its predecessor"
                )
            if checkpoint.run_state.run_id != self._run_id:
                raise PersistenceIntegrityError("checkpoint belongs to another run")
            counts = (
                checkpoint.event_count,
                checkpoint.budget_charge_count,
                checkpoint.effect_count,
                checkpoint.iteration_record_count,
            )
            if any(now < old for now, old in zip(counts, previous_counts)):
                raise PersistenceIntegrityError("a checkpoint journal cursor shrank")
            self._verify_checkpoint_commitment(checkpoint, verify_budget=False)
            previous_counts = counts
            previous_digest = checkpoint.digest

    def _verify_checkpoint_commitment(
        self, checkpoint: CampaignCheckpointV3, *, verify_budget: bool = True
    ) -> None:
        if checkpoint.budget_declaration_digest != self._budget_declaration_digest():
            raise PersistenceIntegrityError(
                "checkpoint budget declaration commitment does not match store"
            )
        self._verify_journal_prefix(
            self._events,
            checkpoint.event_count,
            checkpoint.event_head_digest,
            "event",
        )
        self._verify_journal_prefix(
            self._budget_entries,
            checkpoint.budget_charge_count,
            checkpoint.budget_head_digest,
            "budget",
        )
        self._verify_journal_prefix(
            self._effect_entries,
            checkpoint.effect_count,
            checkpoint.effect_head_digest,
            "effect",
        )
        self._verify_journal_prefix(
            self._iteration_entries,
            checkpoint.iteration_record_count,
            checkpoint.iteration_head_digest,
            "iteration",
        )
        # ``CampaignRun.event_log_digest`` is operational state, not the V0.3
        # checkpoint-head commitment. Frozen M5 can checkpoint immediately after
        # appending an event, so this field may legitimately name an earlier
        # event. Preserve it exactly; event_count + event_head_digest commits the
        # persisted history.
        if verify_budget:
            self._verify_budget_summary(checkpoint)

    def _verify_budget_summary(self, checkpoint: CampaignCheckpointV3) -> None:
        if self._budget_declaration is None:
            raise PersistenceIntegrityError("checkpoint exists without budget declaration")
        charges = tuple(
            entry.charge for entry in self._budget_entries[: checkpoint.budget_charge_count]
        )
        ledger = self._budget_declaration.materialize(charges)
        checks = (
            ("spent_general", ledger.spent_general, checkpoint.spent_general),
            ("spent_validation", ledger.spent_validation, checkpoint.spent_validation),
            ("spent_total", ledger.spent_total, checkpoint.spent_total),
            ("budget_overrun", ledger.overrun, checkpoint.budget_overrun),
        )
        for label, actual, declared in checks:
            if not self._same_number(actual, declared):
                raise PersistenceIntegrityError(
                    f"checkpoint {label} {declared} disagrees with journal {actual}"
                )

    def _verify_budget_history(self) -> None:
        """Validate every checkpoint's budget summary in one monotone O(N) pass.

        Checkpoint digests prove that summaries were not changed *without*
        changing the checkpoint chain. They do not prove the summaries agree
        with the budget-journal prefixes. Walking charges once while checkpoint
        cursors advance closes that gap without re-materializing a full ledger
        for every checkpoint.
        """
        if not self._checkpoints:
            return
        declaration_digest = self._budget_declaration_digest()

        cursor = 0
        spent_general = 0.0
        spent_validation = 0.0
        spent_total = 0.0
        for checkpoint in self._checkpoints:
            if checkpoint.budget_declaration_digest != declaration_digest:
                raise PersistenceIntegrityError(
                    "checkpoint budget declaration commitment does not match store"
                )
            target = checkpoint.budget_charge_count
            if target < cursor or target > len(self._budget_entries):
                raise PersistenceIntegrityError(
                    "checkpoint budget cursor is not a valid monotone prefix"
                )
            while cursor < target:
                charge = self._budget_entries[cursor].charge
                spent_general += float(charge.from_general_pool)
                spent_validation += float(charge.from_validation_reservation)
                spent_total += float(charge.realized)
                cursor += 1
            overrun = max(
                0.0, spent_total - self._budget_declaration.total_budget
            )
            checks = (
                ("spent_general", spent_general, checkpoint.spent_general),
                (
                    "spent_validation",
                    spent_validation,
                    checkpoint.spent_validation,
                ),
                ("spent_total", spent_total, checkpoint.spent_total),
                ("budget_overrun", overrun, checkpoint.budget_overrun),
            )
            for label, actual, declared in checks:
                if not self._same_number(actual, declared):
                    raise PersistenceIntegrityError(
                        f"checkpoint {checkpoint.checkpoint_sequence} {label} "
                        f"{declared} disagrees with journal prefix {actual}"
                    )

    def _verify_effect_uniqueness(self, count: int) -> None:
        seen: set[str] = set()
        for entry in self._effect_entries[:count]:
            if entry.key in seen:
                raise PersistenceIntegrityError(
                    f"effect key {entry.key!r} occurs twice in effect journal"
                )
            seen.add(entry.key)

    def verify_committed(self) -> bool:
        self._verify_checkpoint_chain()
        if not self._checkpoints:
            return True
        head = self._checkpoints[-1]
        self._verify_event_chain(head.event_count)
        self._verify_chained_entries(
            self._budget_entries, head.budget_charge_count, "budget"
        )
        self._verify_chained_entries(
            self._effect_entries, head.effect_count, "effect"
        )
        self._verify_chained_entries(
            self._iteration_entries, head.iteration_record_count, "iteration"
        )
        self._verify_effect_uniqueness(head.effect_count)
        self._verify_budget_history()
        return True

    def verify_all(self) -> bool:
        self.verify_committed()
        self._verify_event_chain(len(self._events))
        self._verify_chained_entries(
            self._budget_entries, len(self._budget_entries), "budget"
        )
        self._verify_chained_entries(
            self._effect_entries, len(self._effect_entries), "effect"
        )
        self._verify_chained_entries(
            self._iteration_entries, len(self._iteration_entries), "iteration"
        )
        self._verify_effect_uniqueness(len(self._effect_entries))
        return True

    def materialize(
        self, checkpoint: CampaignCheckpointV3 | None = None
    ) -> CampaignCheckpoint:
        checkpoint = checkpoint or self.latest_record
        if checkpoint is None:
            raise PersistenceIntegrityError("cannot materialize an empty store")
        self._verify_checkpoint_commitment(checkpoint)
        self._verify_event_chain(checkpoint.event_count)
        self._verify_chained_entries(
            self._budget_entries, checkpoint.budget_charge_count, "budget"
        )
        self._verify_chained_entries(
            self._effect_entries, checkpoint.effect_count, "effect"
        )
        self._verify_chained_entries(
            self._iteration_entries,
            checkpoint.iteration_record_count,
            "iteration",
        )
        self._verify_effect_uniqueness(checkpoint.effect_count)

        events = CampaignEventLog(
            self._run_id,
            tuple(self._events[: checkpoint.event_count]),
        )
        if self._budget_declaration is None:
            raise PersistenceIntegrityError("store has no budget declaration")
        budget = self._budget_declaration.materialize(
            tuple(
                entry.charge
                for entry in self._budget_entries[: checkpoint.budget_charge_count]
            )
        )
        effects = EffectLedger(
            applied={
                entry.key: entry.reference
                for entry in self._effect_entries[: checkpoint.effect_count]
            }
        )
        iterations = tuple(
            entry.record
            for entry in self._iteration_entries[: checkpoint.iteration_record_count]
        )
        run = checkpoint.run_state.materialize(iterations)
        return CampaignCheckpoint(
            run=run,
            events=events,
            budget=budget,
            effects=effects,
            plan=checkpoint.plan,
            obligation_state=checkpoint.obligation_state,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PERSISTENCE_SCHEMA,
            "run_id": self._run_id,
            "budget_declaration": (
                self._budget_declaration.to_dict()
                if self._budget_declaration is not None
                else None
            ),
            "events": [event.to_dict() for event in self._events],
            "budget_journal": [entry.to_dict() for entry in self._budget_entries],
            "effect_journal": [entry.to_dict() for entry in self._effect_entries],
            "iteration_journal": [entry.to_dict() for entry in self._iteration_entries],
            "checkpoints": [checkpoint.to_dict() for checkpoint in self._checkpoints],
            "checkpoint_head_digest": (
                self._checkpoints[-1].digest if self._checkpoints else ""
            ),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IncrementalCheckpointStore":
        require_schema(payload, PERSISTENCE_SCHEMA)
        declaration = (
            BudgetDeclaration.from_dict(payload["budget_declaration"])
            if payload.get("budget_declaration")
            else None
        )
        store = cls(run_id=payload.get("run_id", ""), budget_declaration=declaration)
        store._events = [
            CampaignEvent.from_dict(item) for item in payload.get("events", ())
        ]
        store._budget_entries = [
            BudgetJournalEntry.from_dict(item)
            for item in payload.get("budget_journal", ())
        ]
        store._effect_entries = [
            EffectJournalEntry.from_dict(item)
            for item in payload.get("effect_journal", ())
        ]
        store._iteration_entries = [
            IterationJournalEntry.from_dict(item)
            for item in payload.get("iteration_journal", ())
        ]
        store._checkpoints = [
            CampaignCheckpointV3.from_dict(item)
            for item in payload.get("checkpoints", ())
        ]

        has_history = any(
            (
                store._events,
                store._budget_entries,
                store._effect_entries,
                store._iteration_entries,
                store._checkpoints,
            )
        )
        if has_history and not store._run_id.strip():
            raise PersistenceIntegrityError(
                "non-empty persistence history requires a non-empty run_id"
            )
        if (store._budget_entries or store._checkpoints) and (
            store._budget_declaration is None
        ):
            raise PersistenceIntegrityError(
                "budget history or checkpoints exist without a budget declaration"
            )

        store._effect_index = {
            entry.key: entry.reference for entry in store._effect_entries
        }
        store._spent_general = sum(
            float(entry.charge.from_general_pool) for entry in store._budget_entries
        )
        store._spent_validation = sum(
            float(entry.charge.from_validation_reservation)
            for entry in store._budget_entries
        )
        store._spent_total = sum(
            float(entry.charge.realized) for entry in store._budget_entries
        )
        declared_head = payload.get("checkpoint_head_digest", "")
        actual_head = store._checkpoints[-1].digest if store._checkpoints else ""
        if declared_head != actual_head:
            raise PersistenceIntegrityError(
                "stored checkpoint head digest does not match checkpoint chain"
            )
        # Valid uncommitted suffixes are allowed and remain outside the latest
        # resume cursor, but all bytes that were actually stored must still form
        # internally valid append-only chains. Corrupt suffix bytes fail closed.
        store.verify_all()
        return store

    @classmethod
    def from_legacy_store(
        cls, legacy: LegacyCheckpointStore
    ) -> "IncrementalCheckpointStore":
        store = cls()
        for checkpoint in legacy.history:
            store.save(checkpoint)
        return store

    def save_to_path(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), sort_keys=True, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return target

    @classmethod
    def load_from_path(cls, path: str | Path) -> "IncrementalCheckpointStore":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema") == PERSISTENCE_SCHEMA:
            return cls.from_dict(payload)
        if "checkpoints" in payload:
            return cls.from_legacy_store(LegacyCheckpointStore.from_dict(payload))
        raise PersistenceIntegrityError("unknown campaign persistence format")

    @classmethod
    def migrate_legacy_file(
        cls, source: str | Path, destination: str | Path
    ) -> "IncrementalCheckpointStore":
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        legacy = LegacyCheckpointStore.from_dict(payload)
        migrated = cls.from_legacy_store(legacy)
        migrated.save_to_path(destination)
        return migrated
