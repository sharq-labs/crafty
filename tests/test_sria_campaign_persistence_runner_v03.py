"""The V0.3 runner changes only the persistence seam.

No campaign harness is needed here: the overridden private seam is exercised on
manually declared runner state so the test can prove that durable transitions
write journal deltas directly rather than constructing a legacy full-history
checkpoint first.
"""

from __future__ import annotations

from src.engcore.sria.campaign.budget import BudgetLedger
from src.engcore.sria.campaign.checkpoint import EffectLedger
from src.engcore.sria.campaign.events import CampaignEventLog, CampaignEventType
from src.engcore.sria.campaign.persistence import IncrementalCheckpointStore
from src.engcore.sria.campaign.persistence_runner import IncrementalCampaignRunner
from src.engcore.sria.campaign.state import CampaignRun, ExecutionState


def _bare_runner() -> IncrementalCampaignRunner:
    runner = object.__new__(IncrementalCampaignRunner)
    runner._checkpoints = IncrementalCheckpointStore()
    runner._run = CampaignRun(
        run_id="runner-v03",
        campaign_id="campaign-v03",
        state=ExecutionState.READY,
        max_iterations=3,
    )
    runner._events = CampaignEventLog("runner-v03")
    runner._budget = BudgetLedger(total_budget=100.0)
    runner._effects = EffectLedger()
    runner._plan = None
    runner._obligation_state = {}
    runner._recommendations = {}
    runner._snapshots = {}
    return runner


def test_incremental_runner_checkpoint_writes_only_new_event_history() -> None:
    runner = _bare_runner()

    runner._events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload={"campaign_id": "campaign-v03"},
    )
    first = runner._checkpoint()
    assert first.event_count == 1
    assert runner._checkpoints.event_record_count == 1

    runner._events.append(
        CampaignEventType.CAMPAIGN_PAUSED,
        iteration=0,
        payload={"reason": "test"},
    )
    second = runner._checkpoint()
    assert second.event_count == 2
    assert runner._checkpoints.event_record_count == 2
    assert len(runner._checkpoints.records) == 2


def test_restore_latest_materializes_existing_runner_state_without_replay() -> None:
    runner = _bare_runner()
    runner._events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload={"campaign_id": "campaign-v03"},
    )
    runner._obligation_state = {"adequacy": True}
    runner._checkpoint()

    restored = object.__new__(IncrementalCampaignRunner)
    restored._checkpoints = runner._checkpoints
    restored._recommendations = {}
    restored._snapshots = {}

    run = restored.restore_latest()
    assert run.to_dict() == runner._run.to_dict()
    assert restored._events.to_dict() == runner._events.to_dict()
    assert restored._budget.to_dict() == runner._budget.to_dict()
    assert restored._effects.to_dict() == runner._effects.to_dict()
    assert restored._obligation_state == {"adequacy": True}
