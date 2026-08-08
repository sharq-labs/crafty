"""Core V0.3 — incremental, digest-committed campaign persistence.

The legacy :mod:`checkpoint` representation is logically correct but repeats the
same growing histories inside every checkpoint.  This module keeps those
histories once, as append-only journals, and lets compact checkpoints commit to
verified prefixes by count + head digest.

It deliberately materializes the legacy ``CampaignCheckpoint`` API on resume so
existing campaign semantics do not have to be re-invented by the storage layer.
The new representation is a persistence change, not a decision, evidence,
budget, or scientific-policy change.
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

PERSISTENCE_SCHEMA = schema_string("sria_campaign_persistence_store", 1)
BUDGET_DECLARATION_SCHEMA = schema_string("sria_campaign_budget_declaration_v3", 1)
BUDGET_JOURNAL_SCHEMA = schema_string("sria_campaign_budget_journal_entry", 1)
EFFECT_JOURNAL_SCHEMA = schema_string("sria_campaign_effect_journal_entry", 1)
ITERATION_JOURNAL_SCHEMA = schema_string("sria_campaign_iteration_journal_entry", 1)
RUN_STATE_SCHEMA = schema_string("sria_campaign_compact_run_state", 1)
CHECKPOINT_V3_SCHEMA = schema_string("sria_campaign_checkpoint_v3", 1)


class PersistenceIntegrityError(ResumeViolation):
    """Stored persistence state cannot be trusted for deterministic resume."""


@dataclass(frozen=True)
class BudgetDeclaration:
    """Run-level budget configuration stored once rather than per checkpoint."""

    total_budget: float
    reserved_validation_budget: float = 0.0
    cost_unit: str = "hour"
    enforced_cap: float | None = None
    enforced_cap_source: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "total_budget", float(self.total_budget))
        object.__setattr__(
            self, "reserved_validation_budget", float(self.reserved_validation_budget)
        )
        if self.total_budget < 0.0 or self.reserved_validation_budget < 0.0:
            raise ValueError("budgets must be non-negative")
        if self.reserved_validation_budget > self.total_budget:
            raise ValueError("reserved validation budget exceeds total budget")
        if self.enforced_cap is not None:
            cap = float(self.enforced_cap)
            if cap < 0.0:
                raise ValueError("enforced cap must be non-negative")
            object.__setattr__(self, "enforced_cap", cap)
            if not str(self.enforced_cap_source).strip():
                raise ValueError("an enforced cap must name what enforces it")

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
    """Current CampaignRun state without its cumulative iteration history."""

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
        object.__setattr__(self, "metadata", dict(self.metadata))

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
            "metadata": dict(sorted(self.metadata.items())),
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
        object.__setattr__(
            self,
            "obligation_state",
            {str(k): bool(v) for k, v in dict(self.obligation_state).items()},
        )

    def _chain_payload(self) -> dict[str, Any]:
        return {
            "checkpoint_sequence": self.checkpoint_sequence,
            "run_state": self.run_state.to_dict(),
            "event_count": self.event_count,
            "event_head_digest": self.event_head_digest,
            "budget_charge_count": self.budget_charge_count,
            "budget_head_digest": self.budget_head_digest,
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
        return cls(
            checkpoint_sequence=int(payload["checkpoint_sequence"]),
            run_state=CompactRunState.from_dict(payload["run_state"]),
            event_count=int(payload.get("event_count", 0)),
            event_head_digest=payload.get("event_head_digest", ""),
            budget_charge_count=int(payload.get("budget_charge_count", 0)),
            budget_head_digest=payload.get("budget_head_digest", ""),
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
    """Append-only V0.3 persistence with compact checkpoint commitments.

    ``save_state`` is the fast runner-facing path. ``latest`` and ``history``
    materialize legacy ``CampaignCheckpoint`` objects for compatibility and are
    intentionally resume/audit operations rather than per-step persistence.
    """

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
        """Refuse writes when a loaded store has an uncommitted suffix.

        Resume may safely read the last committed prefix. Continuing to append
        through an abandoned suffix would require choosing whether that suffix
        happened, which storage is not allowed to guess.
        """
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

    def _sync_events(self, log: CampaignEventLog) -> None:
        if log.run_id != self._run_id:
            raise PersistenceIntegrityError("event log run id does not match store")
        persisted = len(self._events)
        if len(log) < persisted:
            raise PersistenceIntegrityError("event history shrank")
        if persisted:
            # One digest commits the whole old prefix; no O(N) prefix re-scan.
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

    def _sync_budget(self, ledger: BudgetLedger) -> None:
        declaration = BudgetDeclaration.from_ledger(ledger)
        if self._budget_declaration is None:
            self._budget_declaration = declaration
        elif self._budget_declaration != declaration:
            raise PersistenceIntegrityError("budget declaration changed across checkpoints")

        persisted = len(self._budget_entries)
        if len(ledger.charges) < persisted:
            raise PersistenceIntegrityError("budget charge history shrank")
        if persisted:
            if ledger.charges[persisted - 1].to_dict() != self._budget_entries[-1].charge.to_dict():
                raise PersistenceIntegrityError("budget history changed before persisted head")
        previous = self._budget_entries[-1].digest if self._budget_entries else ""
        for charge in ledger.charges[persisted:]:
            entry = BudgetJournalEntry(
                sequence=len(self._budget_entries),
                charge=charge,
                prev_digest=previous,
            )
            self._budget_entries.append(entry)
            previous = entry.digest

    def _sync_effects(self, ledger: EffectLedger) -> None:
        # Existing committed keys are checked by direct mapping lookup. New keys
        # are appended in sorted order for deterministic serialization within a
        # checkpoint, without assigning scientific meaning to that order.
        for key, reference in self._effect_index.items():
            if ledger.applied.get(key) != reference:
                raise PersistenceIntegrityError(
                    f"applied effect {key!r} changed or disappeared"
                )
        new_keys = sorted(set(ledger.applied) - set(self._effect_index))
        previous = self._effect_entries[-1].digest if self._effect_entries else ""
        for key in new_keys:
            entry = EffectJournalEntry(
                sequence=len(self._effect_entries),
                key=key,
                reference=str(ledger.applied[key]),
                prev_digest=previous,
            )
            self._effect_entries.append(entry)
            self._effect_index[key] = entry.reference
            previous = entry.digest

    def _sync_iterations(self, run: CampaignRun) -> None:
        persisted = len(self._iteration_entries)
        if len(run.iterations) < persisted:
            raise PersistenceIntegrityError("iteration history shrank")
        if persisted:
            if run.iterations[persisted - 1].to_dict() != self._iteration_entries[-1].record.to_dict():
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
    ) -> CampaignCheckpointV3:
        """Persist only new history plus one compact current-state checkpoint."""
        self._adopt_run_identity(run.run_id)
        self._require_committed_tail()
        self._sync_events(events)
        self._sync_budget(budget)
        self._sync_effects(effects)
        self._sync_iterations(run)

        previous_checkpoint = self._checkpoints[-1] if self._checkpoints else None
        record = CampaignCheckpointV3(
            checkpoint_sequence=len(self._checkpoints),
            run_state=CompactRunState.from_run(run),
            event_count=len(self._events),
            event_head_digest=self._events[-1].digest if self._events else "",
            budget_charge_count=len(self._budget_entries),
            budget_head_digest=(
                self._budget_entries[-1].digest if self._budget_entries else ""
            ),
            effect_count=len(self._effect_entries),
            effect_head_digest=(
                self._effect_entries[-1].digest if self._effect_entries else ""
            ),
            iteration_record_count=len(self._iteration_entries),
            iteration_head_digest=(
                self._iteration_entries[-1].digest if self._iteration_entries else ""
            ),
            spent_general=budget.spent_general,
            spent_validation=budget.spent_validation,
            spent_total=budget.spent_total,
            budget_overrun=budget.overrun,
            plan=plan,
            obligation_state=obligation_state or {},
            previous_checkpoint_digest=(
                previous_checkpoint.digest if previous_checkpoint else ""
            ),
        )
        self._checkpoints.append(record)
        self._verify_checkpoint_chain()
        self._verify_checkpoint_commitment(record)
        return record

    def save(self, checkpoint: CampaignCheckpoint) -> CampaignCheckpointV3:
        """Compatibility seam used by deterministic legacy migration/tests."""
        return self.save_state(
            run=checkpoint.run,
            events=checkpoint.events,
            budget=checkpoint.budget,
            effects=checkpoint.effects,
            plan=checkpoint.plan,
            obligation_state=checkpoint.obligation_state,
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
        previous = ""
        previous_counts = (0, 0, 0, 0)
        for index, checkpoint in enumerate(self._checkpoints):
            if checkpoint.checkpoint_sequence != index:
                raise PersistenceIntegrityError(
                    f"checkpoint {index} declares sequence "
                    f"{checkpoint.checkpoint_sequence}"
                )
            if checkpoint.previous_checkpoint_digest != previous:
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
            previous = checkpoint.digest

    def _verify_checkpoint_commitment(
        self, checkpoint: CampaignCheckpointV3, *, verify_budget: bool = True
    ) -> None:
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

    def verify_committed(self) -> bool:
        """Verify exactly the prefixes committed by the latest checkpoint."""
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
        # Effect keys may occur only once in the committed prefix.
        seen: set[str] = set()
        for entry in self._effect_entries[: head.effect_count]:
            if entry.key in seen:
                raise PersistenceIntegrityError(
                    f"effect key {entry.key!r} occurs twice in committed journal"
                )
            seen.add(entry.key)
        self._verify_budget_summary(head)
        return True

    def verify_all(self) -> bool:
        """Audit every stored record, including any uncommitted suffix."""
        self.verify_committed()
        self._verify_event_chain(len(self._events))
        self._verify_chained_entries(self._budget_entries, len(self._budget_entries), "budget")
        self._verify_chained_entries(self._effect_entries, len(self._effect_entries), "effect")
        self._verify_chained_entries(
            self._iteration_entries, len(self._iteration_entries), "iteration"
        )
        return True

    def materialize(
        self, checkpoint: CampaignCheckpointV3 | None = None
    ) -> CampaignCheckpoint:
        checkpoint = checkpoint or self.latest_record
        if checkpoint is None:
            raise PersistenceIntegrityError("cannot materialize an empty store")
        self._verify_checkpoint_commitment(checkpoint)

        # Verify each journal once to the selected cursor. This is the allowed
        # O(N) resume cost; persistence no longer pays it at every checkpoint.
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
        effect_items = self._effect_entries[: checkpoint.effect_count]
        effects = EffectLedger(applied={entry.key: entry.reference for entry in effect_items})
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
        store._events = [CampaignEvent.from_dict(item) for item in payload.get("events", ())]
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
        store._effect_index = {
            entry.key: entry.reference for entry in store._effect_entries
        }
        declared_head = payload.get("checkpoint_head_digest", "")
        actual_head = store._checkpoints[-1].digest if store._checkpoints else ""
        if declared_head != actual_head:
            raise PersistenceIntegrityError(
                "stored checkpoint head digest does not match checkpoint chain"
            )
        store.verify_committed()
        return store

    @classmethod
    def from_legacy_store(
        cls, legacy: LegacyCheckpointStore
    ) -> "IncrementalCheckpointStore":
        """Explicit in-memory migration. The legacy object is not modified."""
        store = cls()
        for checkpoint in legacy.history:
            store.save(checkpoint)
        return store

    def save_to_path(self, path: str | Path) -> Path:
        """Atomically replace one JSON image of the linearized store.

        This backend does not claim database transactions.  It does guarantee
        that a successfully replaced file contains journals and the checkpoint
        index from one deterministic in-memory state rather than a half-written
        JSON document.
        """
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
        # Legacy CheckpointStore deliberately had no store-level schema.
        if "checkpoints" in payload:
            return cls.from_legacy_store(LegacyCheckpointStore.from_dict(payload))
        raise PersistenceIntegrityError("unknown campaign persistence format")

    @classmethod
    def migrate_legacy_file(
        cls, source: str | Path, destination: str | Path
    ) -> "IncrementalCheckpointStore":
        """Create a new V0.3 artifact; never rewrite the legacy source."""
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        legacy = LegacyCheckpointStore.from_dict(payload)
        migrated = cls.from_legacy_store(legacy)
        migrated.save_to_path(destination)
        return migrated
