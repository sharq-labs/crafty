"""Regressions for integrity findings from the final Core V0.3 review."""

from __future__ import annotations

import copy

import pytest

from src.engcore.sria.campaign.budget import BudgetLedger
from src.engcore.sria.campaign.checkpoint import EffectLedger, ResumeViolation
from src.engcore.sria.campaign.events import (
    CampaignEvent,
    CampaignEventLog,
    CampaignEventType,
)
from src.engcore.sria.campaign.persistence import (
    CampaignCheckpointV3,
    IncrementalCheckpointStore,
    PersistenceIntegrityError,
)
from src.engcore.sria.campaign.state import CampaignRun, ExecutionState
from src.engcore.sria.decision.actions import ActionFamily

RUN_ID = "v03-review-regression"


def _store(n: int = 3) -> IncrementalCheckpointStore:
    store = IncrementalCheckpointStore()
    events = CampaignEventLog(RUN_ID)
    budget = BudgetLedger(total_budget=100.0, reserved_validation_budget=10.0)
    effects = EffectLedger()

    for index in range(n):
        iteration = index + 1
        events.append(
            CampaignEventType.BUDGET_UPDATED,
            iteration=iteration,
            payload={"iteration": iteration},
        )
        budget.settle(
            charge_id=f"charge-{iteration}",
            action_id=f"action-{iteration}",
            iteration=iteration,
            family=ActionFamily.EXPLORE,
            realized=float(iteration),
            predicted=float(iteration),
        )
        run = CampaignRun(
            run_id=RUN_ID,
            campaign_id="v03-review-campaign",
            state=ExecutionState.READY,
            iteration=iteration,
            max_iterations=n,
            event_log_digest=events.head_digest,
        )
        store.save_state(
            run=run,
            events=events,
            budget=budget,
            effects=effects,
        )
    return store


def _rechain_checkpoints(payload: dict) -> None:
    previous = ""
    for raw in payload["checkpoints"]:
        raw["previous_checkpoint_digest"] = previous
        checkpoint = CampaignCheckpointV3.from_dict(raw)
        previous = checkpoint.digest
    payload["checkpoint_head_digest"] = previous


def test_earlier_budget_summary_tamper_is_detected_even_after_rechaining() -> None:
    payload = copy.deepcopy(_store().to_dict())

    # An attacker who can rewrite bytes could recompute the checkpoint chain.
    # The budget-journal prefix is an independent commitment and must still
    # contradict this altered historical summary.
    payload["checkpoints"][0]["spent_total"] += 7.0
    _rechain_checkpoints(payload)

    with pytest.raises(PersistenceIntegrityError, match="checkpoint 0 spent_total"):
        IncrementalCheckpointStore.from_dict(payload)


def test_corrupt_uncommitted_event_suffix_fails_closed_on_load() -> None:
    payload = copy.deepcopy(_store(1).to_dict())
    last = CampaignEvent.from_dict(payload["events"][-1])
    suffix = CampaignEvent(
        sequence=last.sequence + 1,
        event_type=CampaignEventType.CAMPAIGN_PAUSED,
        run_id=RUN_ID,
        iteration=1,
        payload={"uncommitted": True},
        prev_digest="corrupt-predecessor",
    )
    payload["events"].append(suffix.to_dict())

    # The latest checkpoint still commits the original prefix, but corrupt bytes
    # after it are not silently accepted merely because resume would ignore them.
    with pytest.raises(PersistenceIntegrityError, match="does not follow"):
        IncrementalCheckpointStore.from_dict(payload)


def test_non_empty_store_requires_explicit_run_identity() -> None:
    payload = copy.deepcopy(_store(1).to_dict())
    payload["run_id"] = ""
    with pytest.raises(PersistenceIntegrityError, match="requires a non-empty run_id"):
        IncrementalCheckpointStore.from_dict(payload)


def test_absolute_event_cursor_rejects_negative_index() -> None:
    events = CampaignEventLog("cursor-run")
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    with pytest.raises(IndexError, match="outside the log"):
        events.event_at(-1)


def test_absolute_effect_cursor_rejects_negative_index() -> None:
    effects = EffectLedger()
    effects.mark("one", "ref")
    with pytest.raises(ResumeViolation, match="outside"):
        effects.entry_at(-1)
