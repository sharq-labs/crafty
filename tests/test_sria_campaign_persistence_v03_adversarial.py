"""Adversarial integrity tests required by the frozen Core V0.3 preregistration.

Each mutation models stored bytes that no longer describe the state that was
committed.  The loader/auditor must fail closed; none of these cases may be
silently repaired or reinterpreted during resume.
"""

from __future__ import annotations

import copy

import pytest

from src.engcore.sria.campaign.budget import BudgetLedger
from src.engcore.sria.campaign.checkpoint import EffectLedger
from src.engcore.sria.campaign.events import CampaignEventLog, CampaignEventType
from src.engcore.sria.campaign.persistence import (
    CampaignCheckpointV3,
    EffectJournalEntry,
    IncrementalCheckpointStore,
    PersistenceIntegrityError,
)
from src.engcore.sria.campaign.state import CampaignRun, ExecutionState, IterationRecord
from src.engcore.sria.decision.actions import ActionFamily

RUN_ID = "v03-adversarial"


def _store(n: int = 3) -> IncrementalCheckpointStore:
    store = IncrementalCheckpointStore()
    events = CampaignEventLog(RUN_ID)
    budget = BudgetLedger(total_budget=100.0, reserved_validation_budget=10.0)
    effects = EffectLedger()
    iterations: list[IterationRecord] = []

    for index in range(n):
        iteration = index + 1
        events.append(
            CampaignEventType.ITERATION_COMPLETED,
            iteration=iteration,
            payload={"iteration": iteration},
            at=f"t-{iteration}",
        )
        budget.settle(
            charge_id=f"charge-{iteration}",
            action_id=f"action-{iteration}",
            iteration=iteration,
            family=ActionFamily.EXPLORE,
            realized=1.0,
            predicted=1.0,
        )
        effects.mark(f"effect-{iteration}", f"ref-{iteration}")
        iterations.append(
            IterationRecord(
                iteration=iteration,
                selected_action_id=f"action-{iteration}",
                execution_id=f"exec-{iteration}",
                predicted_cost=1.0,
                realized_cost=1.0,
            )
        )
        run = CampaignRun(
            run_id=RUN_ID,
            campaign_id="campaign-adversarial",
            state=ExecutionState.READY,
            iteration=iteration,
            max_iterations=max(n, 1),
            iterations=tuple(iterations),
            event_log_digest=events.head_digest,
        )
        store.save_state(
            run=run,
            events=events,
            budget=budget,
            effects=effects,
            obligation_state={"adequacy": iteration >= 2},
        )
    return store


def _payload(n: int = 3) -> dict:
    return copy.deepcopy(_store(n).to_dict())


def _refresh_top_checkpoint_head(payload: dict) -> None:
    payload["checkpoint_head_digest"] = CampaignCheckpointV3.from_dict(
        payload["checkpoints"][-1]
    ).digest


def test_deleting_a_committed_event_fails_closed() -> None:
    payload = _payload()
    del payload["events"][1]
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_reordering_committed_events_fails_closed() -> None:
    payload = _payload()
    payload["events"][0], payload["events"][1] = (
        payload["events"][1],
        payload["events"][0],
    )
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_wrong_event_predecessor_digest_fails_closed() -> None:
    payload = _payload()
    payload["events"][1]["prev_digest"] = "not-the-predecessor"
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_wrong_event_sequence_fails_closed() -> None:
    payload = _payload()
    payload["events"][1]["sequence"] = 99
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_wrong_event_run_id_fails_closed() -> None:
    payload = _payload()
    payload["events"][1]["run_id"] = "another-run"
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_checkpoint_event_head_digest_mismatch_fails_closed() -> None:
    payload = _payload()
    payload["checkpoints"][-1]["event_head_digest"] = "wrong-event-head"
    _refresh_top_checkpoint_head(payload)
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_checkpoint_sequence_repeat_fails_closed() -> None:
    payload = _payload()
    payload["checkpoints"][1]["checkpoint_sequence"] = 0
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_checkpoint_sequence_skip_fails_closed() -> None:
    payload = _payload()
    payload["checkpoints"][1]["checkpoint_sequence"] = 7
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_checkpoint_cursor_shrink_fails_closed() -> None:
    payload = _payload()
    payload["checkpoints"][1]["event_count"] = 0
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_checkpoint_cursor_beyond_journal_length_fails_closed() -> None:
    payload = _payload()
    payload["checkpoints"][-1]["event_count"] = len(payload["events"]) + 1
    _refresh_top_checkpoint_head(payload)
    with pytest.raises(PersistenceIntegrityError):
        IncrementalCheckpointStore.from_dict(payload)


def test_tampered_budget_summary_fails_even_with_a_valid_checkpoint_digest() -> None:
    payload = _payload()
    payload["checkpoints"][-1]["spent_total"] += 5.0
    _refresh_top_checkpoint_head(payload)
    with pytest.raises(PersistenceIntegrityError, match="spent_total"):
        IncrementalCheckpointStore.from_dict(payload)


def test_run_state_event_digest_must_match_the_committed_event_head() -> None:
    payload = _payload()
    payload["checkpoints"][-1]["run_state"]["event_log_digest"] = "wrong-run-head"
    _refresh_top_checkpoint_head(payload)
    with pytest.raises(PersistenceIntegrityError, match="event_log_digest"):
        IncrementalCheckpointStore.from_dict(payload)


def test_duplicate_effect_key_in_a_committed_prefix_fails_closed() -> None:
    payload = _payload(1)
    first = EffectJournalEntry.from_dict(payload["effect_journal"][0])
    duplicate = EffectJournalEntry(
        sequence=1,
        key=first.key,
        reference=first.reference,
        prev_digest=first.digest,
    )
    payload["effect_journal"].append(duplicate.to_dict())
    payload["checkpoints"][-1]["effect_count"] = 2
    payload["checkpoints"][-1]["effect_head_digest"] = duplicate.digest
    _refresh_top_checkpoint_head(payload)

    with pytest.raises(PersistenceIntegrityError, match="occurs twice"):
        IncrementalCheckpointStore.from_dict(payload)
