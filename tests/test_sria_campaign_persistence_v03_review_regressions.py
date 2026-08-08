"""Regressions for integrity findings from the final Core V0.3 review."""

from __future__ import annotations

import copy

import pytest

from src.engcore.scientific.ir.values import IntegerValue
from src.engcore.sria.actions import ExecutorType, ResearchAction
from src.engcore.sria.campaign.budget import (
    BudgetCharge,
    BudgetHistoryViolation,
    BudgetLedger,
)
from src.engcore.sria.campaign.checkpoint import (
    CampaignCheckpoint,
    CheckpointStore,
    EffectLedger,
    IterationPlan,
    ResumeViolation,
)
from src.engcore.sria.campaign.events import (
    CampaignEvent,
    CampaignEventLog,
    CampaignEventType,
)
from src.engcore.sria.campaign.persistence import (
    CampaignCheckpointV3,
    CHECKPOINT_TUPLE_SCHEMA,
    IncrementalCheckpointStore,
    PersistenceIntegrityError,
)
from src.engcore.sria.campaign.state import (
    CampaignRun,
    ExecutionState,
    IterationRecord,
)
from src.engcore.sria.decision.actions import ActionFamily, ActionProposal, AtomicAction
from src.engcore.sria.decision.belief_snapshot import BeliefSnapshot
from src.engcore.sria.decision.recommendation import (
    DecisionRecommendation,
    RecommendationOutcome,
)
from src.engcore.sria.decision.replay import ExecutionDependencyManifest

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


def _review_plan() -> IterationPlan:
    snapshot = BeliefSnapshot(
        snapshot_id="review-snapshot",
        campaign_id="v03-review-campaign",
        charter_version="1",
        metadata={"nested": {"attempts": [1]}},
    )
    manifest = ExecutionDependencyManifest(
        snapshot_digest=snapshot.digest,
        charter_version="1",
        candidate_set_digest="candidate-set",
    )
    action = AtomicAction(
        action=ResearchAction(
            action_id="review-action",
            executor_type=ExecutorType.SIMULATION,
            target_ref="target",
            parameters={"replicas": IntegerValue(2)},
            metadata={"nested": {"attempts": [1]}},
        ),
        proposal=ActionProposal(
            family=ActionFamily.EXPLORE,
            target_ref="target",
            rationale="review fixture",
        ),
    )
    recommendation = DecisionRecommendation(
        recommendation_id="review-recommendation",
        outcome=RecommendationOutcome.RECOMMEND_ACTION,
        snapshot_digest=snapshot.digest,
        campaign_id="v03-review-campaign",
        charter_version="1",
        chosen_action_id=action.action_id,
        chosen_family=action.family,
        dependency_manifest=manifest,
        reason="review fixture",
    )
    return IterationPlan(
        iteration=1,
        snapshot=snapshot,
        manifest=manifest,
        recommendation=recommendation,
        action=action,
        charter_version="1",
        campaign_id="v03-review-campaign",
        predicted_cost=1.0,
    )


def _rechain_checkpoints(payload: dict) -> None:
    previous = ""
    for raw in payload["checkpoints"]:
        raw["previous_checkpoint_digest"] = previous
        checkpoint = CampaignCheckpointV3.from_dict(raw)
        previous = checkpoint.digest
    payload["checkpoint_head_digest"] = previous


def _charge(
    charge_id: str,
    *,
    realized: float,
    predicted: float | None = None,
    general: float | None = None,
    validation: float = 0.0,
    family: ActionFamily = ActionFamily.EXPLORE,
) -> BudgetCharge:
    if general is None:
        general = realized - validation
    return BudgetCharge(
        charge_id=charge_id,
        action_id=f"action-{charge_id}",
        iteration=int(charge_id.split("-")[-1]),
        family=family,
        realized=realized,
        predicted=predicted,
        from_general_pool=general,
        from_validation_reservation=validation,
        detail=f"detail-{charge_id}",
    )


def _legacy_checkpoint(
    *,
    iteration: int,
    charges: tuple[BudgetCharge, ...],
    iterations: tuple[IterationRecord, ...] = (),
    total_budget: float = 100.0,
    reserved_validation_budget: float = 20.0,
    cost_unit: str = "hour",
    enforced_cap: float | None = 90.0,
    enforced_cap_source: str = "test executor",
) -> CampaignCheckpoint:
    events = CampaignEventLog(RUN_ID)
    for index in range(iteration):
        events.append(
            CampaignEventType.BUDGET_UPDATED,
            iteration=index + 1,
            payload={"iteration": index + 1},
        )
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=iteration,
        max_iterations=5,
        iterations=iterations,
        event_log_digest=events.head_digest,
    )
    return CampaignCheckpoint(
        run=run,
        events=events,
        budget=BudgetLedger(
            total_budget=total_budget,
            reserved_validation_budget=reserved_validation_budget,
            charges=charges,
            cost_unit=cost_unit,
            enforced_cap=enforced_cap,
            enforced_cap_source=enforced_cap_source,
        ),
        effects=EffectLedger(),
    )


def _iteration(
    index: int,
    *,
    recommendation_id: str | None = None,
    selected_action_id: str | None = None,
    execution_id: str | None = None,
    evidence_ids: tuple[str, ...] = (),
    admitted_evidence_ids: tuple[str, ...] = (),
    calibration_entry_ids: tuple[str, ...] = (),
    predicted_cost: float | None = None,
    realized_cost: float | None = None,
    detail: str | None = None,
) -> IterationRecord:
    return IterationRecord(
        iteration=index,
        snapshot_digest=f"snapshot-{index}",
        decision_basis_digest=f"basis-{index}",
        recommendation_id=recommendation_id or f"rec-{index}",
        recommendation_outcome="recommend_action",
        selected_action_id=selected_action_id or f"action-{index}",
        execution_id=execution_id or f"exec-{index}",
        evidence_ids=evidence_ids or (f"evidence-{index}",),
        assessment_ids=(f"assessment-{index}",),
        arbiter_decision_id=f"arbiter-{index}",
        arbiter_verdict="accepted",
        admitted_evidence_ids=admitted_evidence_ids or (f"evidence-{index}",),
        calibration_entry_ids=calibration_entry_ids or (f"calibration-{index}",),
        predicted_cost=predicted_cost if predicted_cost is not None else float(index),
        realized_cost=realized_cost if realized_cost is not None else float(index),
        stop_proposed=False,
        detail=detail or f"iteration-{index}",
    )


def _legacy_store(*checkpoints: CampaignCheckpoint) -> CheckpointStore:
    legacy = CheckpointStore()
    for checkpoint in checkpoints:
        legacy.save(checkpoint)
    return legacy


def _budget_fields(ledger: BudgetLedger) -> dict:
    return {
        "to_dict": ledger.to_dict(),
        "charges": [charge.to_dict() for charge in ledger.charges],
        "total_budget": ledger.total_budget,
        "reserved_validation_budget": ledger.reserved_validation_budget,
        "spent_general": ledger.spent_general,
        "spent_validation": ledger.spent_validation,
        "spent_total": ledger.spent_total,
        "overrun": ledger.overrun,
        "cost_unit": ledger.cost_unit,
        "enforced_cap": ledger.enforced_cap,
        "enforced_cap_source": ledger.enforced_cap_source,
    }


def _iteration_dicts(checkpoint: CampaignCheckpoint) -> list[dict]:
    return [record.to_dict() for record in checkpoint.run.iterations]


def test_earlier_budget_summary_tamper_is_detected_even_after_rechaining() -> None:
    payload = copy.deepcopy(_store().to_dict())

    # An attacker who can rewrite bytes could recompute the checkpoint chain.
    # The budget-journal prefix is an independent commitment and must still
    # contradict this altered historical summary.
    payload["checkpoints"][0]["spent_total"] += 7.0
    _rechain_checkpoints(payload)

    with pytest.raises(PersistenceIntegrityError, match="checkpoint 0 spent_total"):
        IncrementalCheckpointStore.from_dict(payload)


def test_budget_declaration_total_budget_tamper_fails_closed() -> None:
    payload = copy.deepcopy(_store(1).to_dict())
    payload["budget_declaration"]["total_budget"] += 10.0

    with pytest.raises(
        PersistenceIntegrityError,
        match="budget declaration commitment",
    ):
        IncrementalCheckpointStore.from_dict(payload)


def test_budget_declaration_reserved_validation_tamper_fails_closed() -> None:
    payload = copy.deepcopy(_store(1).to_dict())
    payload["budget_declaration"]["reserved_validation_budget"] += 5.0

    with pytest.raises(
        PersistenceIntegrityError,
        match="budget declaration commitment",
    ):
        IncrementalCheckpointStore.from_dict(payload)


def test_budget_declaration_enforced_cap_tamper_fails_closed() -> None:
    source = _legacy_checkpoint(
        iteration=1,
        charges=(_charge("charge-1", realized=1.0, predicted=1.0),),
        enforced_cap=90.0,
        enforced_cap_source="test executor",
    )
    payload = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(source)
    ).to_dict()
    payload["budget_declaration"]["enforced_cap"] = 99.0

    with pytest.raises(
        PersistenceIntegrityError,
        match="budget declaration commitment",
    ):
        IncrementalCheckpointStore.from_dict(payload)


def test_budget_declaration_enforced_cap_source_tamper_fails_closed() -> None:
    source = _legacy_checkpoint(
        iteration=1,
        charges=(_charge("charge-1", realized=1.0, predicted=1.0),),
        enforced_cap=90.0,
        enforced_cap_source="test executor",
    )
    payload = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(source)
    ).to_dict()
    payload["budget_declaration"]["enforced_cap_source"] = "different executor"

    with pytest.raises(
        PersistenceIntegrityError,
        match="budget declaration commitment",
    ):
        IncrementalCheckpointStore.from_dict(payload)


def test_budget_declaration_round_trip_preserves_exact_budget_semantics() -> None:
    source = _legacy_checkpoint(
        iteration=1,
        charges=(
            _charge(
                "charge-1",
                realized=6.0,
                predicted=5.0,
                general=2.0,
                validation=4.0,
                family=ActionFamily.VALIDATE,
            ),
        ),
        total_budget=10.0,
        reserved_validation_budget=5.0,
        cost_unit="gpu-hour",
        enforced_cap=8.0,
        enforced_cap_source="gpu quota",
    )
    store = IncrementalCheckpointStore.from_legacy_store(_legacy_store(source))

    assert store.records[0].budget_declaration_digest

    reloaded = IncrementalCheckpointStore.from_dict(copy.deepcopy(store.to_dict()))
    restored = reloaded.latest()
    assert restored is not None
    assert _budget_fields(restored.budget) == _budget_fields(source.budget)


def test_legacy_migration_rejects_mutated_early_charge_with_same_tail() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    charge_b = _charge("charge-2", realized=2.0, predicted=2.0)
    charge_c = _charge("charge-3", realized=3.0, predicted=3.0)
    mutated_a = _charge("charge-1", realized=4.0, predicted=1.0)
    legacy = _legacy_store(
        _legacy_checkpoint(iteration=1, charges=(charge_a, charge_b)),
        _legacy_checkpoint(iteration=2, charges=(mutated_a, charge_b, charge_c)),
    )

    with pytest.raises(PersistenceIntegrityError, match="charge 0"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_rejects_pool_split_mutation() -> None:
    charge_a = _charge(
        "charge-1",
        realized=6.0,
        predicted=6.0,
        general=2.0,
        validation=4.0,
        family=ActionFamily.VALIDATE,
    )
    mutated_a = _charge(
        "charge-1",
        realized=6.0,
        predicted=6.0,
        general=3.0,
        validation=3.0,
        family=ActionFamily.VALIDATE,
    )
    charge_b = _charge("charge-2", realized=2.0, predicted=2.0)
    legacy = _legacy_store(
        _legacy_checkpoint(iteration=1, charges=(charge_a,)),
        _legacy_checkpoint(iteration=2, charges=(mutated_a, charge_b)),
    )

    with pytest.raises(PersistenceIntegrityError, match="charge 0"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_rejects_realized_cost_mutation() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    mutated_a = _charge("charge-1", realized=2.0, predicted=1.0)
    charge_b = _charge("charge-2", realized=2.0, predicted=2.0)
    legacy = _legacy_store(
        _legacy_checkpoint(iteration=1, charges=(charge_a,)),
        _legacy_checkpoint(iteration=2, charges=(mutated_a, charge_b)),
    )

    with pytest.raises(PersistenceIntegrityError, match="charge 0"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_accepts_valid_growing_budget_prefixes() -> None:
    charges = (
        _charge("charge-1", realized=1.0, predicted=1.0),
        _charge(
            "charge-2",
            realized=6.0,
            predicted=5.0,
            general=2.0,
            validation=4.0,
            family=ActionFamily.VALIDATE,
        ),
        _charge("charge-3", realized=3.0, predicted=3.0),
        _charge("charge-4", realized=4.0, predicted=4.0),
    )
    checkpoints = tuple(
        _legacy_checkpoint(iteration=index, charges=charges[:index])
        for index in range(1, 5)
    )
    migrated = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(*checkpoints)
    )

    assert len(migrated.records) == len(checkpoints)
    for source, restored in zip(checkpoints, migrated.history):
        assert _budget_fields(restored.budget) == _budget_fields(source.budget)


def test_repeated_charge_id_semantics_survive_valid_legacy_migration() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    restored = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(_legacy_checkpoint(iteration=1, charges=(charge_a,)))
    ).latest()
    assert restored is not None

    before = restored.budget.to_dict()
    existing = restored.budget.settle(
        charge_id="charge-1",
        action_id="different-action",
        iteration=99,
        family=ActionFamily.EXPLORE,
        realized=99.0,
        predicted=99.0,
    )
    assert existing.to_dict() == charge_a.to_dict()
    assert restored.budget.to_dict() == before


def test_legacy_migration_rejects_mutated_early_iteration_with_same_tail() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    i1 = _iteration(1)
    i2 = _iteration(2)
    i3 = _iteration(3)
    i1_modified = _iteration(1, execution_id="exec-1-modified")
    legacy = _legacy_store(
        _legacy_checkpoint(iteration=2, charges=(charge_a,), iterations=(i1, i2)),
        _legacy_checkpoint(
            iteration=3,
            charges=(charge_a,),
            iterations=(i1_modified, i2, i3),
        ),
    )

    with pytest.raises(PersistenceIntegrityError, match="record 0"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_rejects_middle_iteration_mutation() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    i1 = _iteration(1)
    i2 = _iteration(2)
    i3 = _iteration(3)
    i4 = _iteration(4)
    i2_modified = _iteration(2, admitted_evidence_ids=("different-evidence",))
    legacy = _legacy_store(
        _legacy_checkpoint(
            iteration=3,
            charges=(charge_a,),
            iterations=(i1, i2, i3),
        ),
        _legacy_checkpoint(
            iteration=4,
            charges=(charge_a,),
            iterations=(i1, i2_modified, i3, i4),
        ),
    )

    with pytest.raises(PersistenceIntegrityError, match="record 1"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_rejects_same_iteration_id_altered_payload() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    i1 = _iteration(1)
    i2 = _iteration(2)
    i1_same_id_modified_payload = _iteration(1, detail="same-id-different-payload")
    legacy = _legacy_store(
        _legacy_checkpoint(iteration=1, charges=(charge_a,), iterations=(i1,)),
        _legacy_checkpoint(
            iteration=2,
            charges=(charge_a,),
            iterations=(i1_same_id_modified_payload, i2),
        ),
    )

    with pytest.raises(PersistenceIntegrityError, match="record 0"):
        IncrementalCheckpointStore.from_legacy_store(legacy)


def test_legacy_migration_accepts_valid_growing_iteration_prefixes() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    iterations = (_iteration(1), _iteration(2), _iteration(3))
    checkpoints = tuple(
        _legacy_checkpoint(
            iteration=index,
            charges=(charge_a,),
            iterations=iterations[:index],
        )
        for index in range(1, 4)
    )

    migrated = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(*checkpoints)
    )

    assert len(migrated.records) == len(checkpoints)


def test_legacy_migration_materializes_exact_iteration_history_for_each_checkpoint() -> None:
    charge_a = _charge("charge-1", realized=1.0, predicted=1.0)
    iterations = (_iteration(1), _iteration(2), _iteration(3))
    checkpoints = tuple(
        _legacy_checkpoint(
            iteration=index,
            charges=(charge_a,),
            iterations=iterations[:index],
        )
        for index in range(1, 4)
    )

    migrated = IncrementalCheckpointStore.from_legacy_store(
        _legacy_store(*checkpoints)
    )

    for source, restored in zip(checkpoints, migrated.history):
        assert _iteration_dicts(restored) == _iteration_dicts(source)


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


def test_effect_applied_direct_overwrite_fails_closed() -> None:
    effects = EffectLedger(applied={"k": "A"})

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        effects.applied["k"] = "B"

    assert effects.reference("k") == "A"
    assert effects.is_applied("k") is True
    assert effects.entries_from(0) == (("k", "A"),)


def test_effect_applied_direct_delete_fails_closed() -> None:
    effects = EffectLedger(applied={"k": "A"})

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        del effects.applied["k"]

    assert effects.reference("k") == "A"
    assert effects.entries_from(0) == (("k", "A"),)


def test_effect_applied_direct_addition_fails_closed() -> None:
    effects = EffectLedger(applied={"k": "A"})

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        effects.applied["new"] = "B"

    assert effects.reference("new") == ""
    assert effects.entries_from(0) == (("k", "A"),)


def test_effect_applied_bulk_update_fails_closed() -> None:
    effects = EffectLedger(applied={"k": "A"})

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        effects.applied.update({"new": "B"})

    assert effects.reference("new") == ""
    assert effects.entries_from(0) == (("k", "A"),)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda applied: applied.clear(),
        lambda applied: applied.pop("k"),
        lambda applied: applied.popitem(),
        lambda applied: applied.setdefault("new", "B"),
        lambda applied: applied.__ior__({"new": "B"}),
    ],
)
def test_effect_applied_other_mutators_fail_closed(mutate) -> None:
    effects = EffectLedger(applied={"k": "A"})

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        mutate(effects.applied)

    assert effects.reference("k") == "A"
    assert effects.entries_from(0) == (("k", "A"),)


def test_effect_mark_still_updates_mapping_and_journal_once() -> None:
    effects = EffectLedger(applied={"k": "A"})

    effects.mark("new", "B")

    assert effects.reference("new") == "B"
    assert effects.applied == {"k": "A", "new": "B"}
    assert effects.entries_from(0) == (("k", "A"), ("new", "B"))
    assert effects.entries_from(1) == (("new", "B"),)


def test_effect_once_still_uses_mark_and_preserves_duplicate_semantics() -> None:
    effects = EffectLedger(applied={"k": "A"})

    value, performed = effects.once("new", lambda: "payload", reference=lambda v: v)
    duplicate, duplicated = effects.once("k", lambda: "must-not-run")

    assert (value, performed) == ("payload", True)
    assert (duplicate, duplicated) == (None, False)
    assert effects.reference("new") == "payload"
    assert effects.entries_from(1) == (("new", "payload"),)


def test_effect_ledger_v03_checkpoint_round_trip_preserves_references() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    effects = EffectLedger()
    effects.mark("effect:execute", "execution-ref")
    effects.mark("effect:admit", "evidence-ref")
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()

    store.save_state(run=run, events=events, budget=budget, effects=effects)
    restored = IncrementalCheckpointStore.from_dict(copy.deepcopy(store.to_dict()))
    latest = restored.latest()

    assert latest is not None
    assert latest.effects.reference("effect:execute") == "execution-ref"
    assert latest.effects.reference("effect:admit") == "evidence-ref"
    assert latest.effects.to_dict() == {
        "schema": effects.to_dict()["schema"],
        "applied": {
            "effect:admit": "evidence-ref",
            "effect:execute": "execution-ref",
        },
    }


def test_effect_applied_direct_mutation_cannot_persist_stale_reference() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    effects = EffectLedger()
    effects.mark("k", "reference-A")

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        effects.applied["k"] = "reference-B"

    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(run=run, events=events, budget=budget, effects=effects)
    restored = IncrementalCheckpointStore.from_dict(copy.deepcopy(store.to_dict()))
    latest = restored.latest()

    assert effects.reference("k") == "reference-A"
    assert latest is not None
    assert latest.effects.reference("k") == effects.reference("k")


def test_effect_applied_attribute_rebind_fails_closed() -> None:
    effects = EffectLedger()
    effects.mark("k", "reference-A")

    with pytest.raises(ResumeViolation, match="EffectLedger.mark/once"):
        effects.applied = {"k": "reference-B"}

    assert effects.reference("k") == "reference-A"
    assert effects.entries_from(0) == (("k", "reference-A"),)


def test_checkpoint_record_obligation_state_mutation_fails_closed() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
        obligation_state={"pending-obligation": True},
    )
    record = store.latest_record
    assert record is not None
    before = record.digest

    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.obligation_state["pending-obligation"] = False

    assert record.obligation_state == {"pending-obligation": True}
    assert record.digest == before
    assert store.to_dict()["checkpoints"][-1]["obligation_state"] == {
        "pending-obligation": True
    }


def test_checkpoint_record_run_metadata_mutation_fails_closed() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
        metadata={
            "phase": "ready",
            "nested": {"flags": {"accepted": True}, "attempts": [1, 2]},
        },
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )
    record = store.latest_record
    assert record is not None
    before = record.digest

    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.run_state.metadata["phase"] = "rewritten"
    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.run_state.metadata["nested"]["flags"]["accepted"] = False
    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.run_state.metadata["nested"]["attempts"].append(3)

    assert record.run_state.metadata["phase"] == "ready"
    assert record.run_state.metadata["nested"]["flags"] == {"accepted": True}
    assert record.run_state.metadata["nested"]["attempts"] == [1, 2]
    assert record.digest == before
    assert store.to_dict()["checkpoints"][-1]["run_state"]["metadata"] == {
        "nested": {"attempts": [1, 2], "flags": {"accepted": True}},
        "phase": "ready",
    }


def test_checkpoint_record_plan_mutation_fails_closed() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.ACTION_SELECTED,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    plan = _review_plan()
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
        plan=plan,
    )

    plan.action.action.metadata["nested"]["attempts"].append(99)
    record = store.latest_record
    assert record is not None
    assert record.plan is not None
    before = record.digest

    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.plan.action.action.parameters["replicas"] = IntegerValue(3)
    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.plan.action.action.metadata["nested"]["attempts"].append(2)
    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        record.plan.snapshot.metadata["nested"]["attempts"].append(2)

    assert record.plan.action.action.metadata["nested"]["attempts"] == [1]
    assert record.plan.snapshot.metadata["nested"]["attempts"] == [1]
    assert record.digest == before
    assert store.to_dict()["checkpoints"][-1]["plan"]["action"]["action"][
        "metadata"
    ] == {"nested": {"attempts": [1]}}


def test_materialized_run_metadata_is_thawed_for_legacy_compatibility() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
        metadata={"nested": {"attempts": [1]}},
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )

    materialized = store.latest()
    assert materialized is not None
    materialized.run.metadata["nested"]["attempts"].append(2)

    assert materialized.run.metadata == {"nested": {"attempts": [1, 2]}}
    assert store.to_dict()["checkpoints"][-1]["run_state"]["metadata"] == {
        "nested": {"attempts": [1]}
    }


def test_checkpoint_payload_freezing_preserves_tuple_metadata_types(tmp_path) -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
        metadata={
            "bounds": (1, 2),
            "nested": {"choices": ("alpha", "beta")},
        },
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )

    record = store.latest_record
    assert record is not None
    assert record.run_state.metadata["bounds"] == (1, 2)
    assert isinstance(record.run_state.metadata["bounds"], tuple)
    assert record.run_state.metadata["nested"]["choices"] == ("alpha", "beta")
    assert isinstance(record.run_state.metadata["nested"]["choices"], tuple)

    materialized = store.latest()
    assert materialized is not None
    assert materialized.run.metadata["bounds"] == (1, 2)
    assert isinstance(materialized.run.metadata["bounds"], tuple)
    assert materialized.run.metadata["nested"]["choices"] == ("alpha", "beta")
    assert isinstance(materialized.run.metadata["nested"]["choices"], tuple)

    loaded = IncrementalCheckpointStore.load_from_path(
        store.save_to_path(tmp_path / "tuple-metadata.json")
    )
    loaded_materialized = loaded.latest()
    assert loaded_materialized is not None
    assert loaded_materialized.run.metadata["bounds"] == (1, 2)
    assert isinstance(loaded_materialized.run.metadata["bounds"], tuple)
    assert loaded_materialized.run.metadata["nested"]["choices"] == (
        "alpha",
        "beta",
    )
    assert isinstance(loaded_materialized.run.metadata["nested"]["choices"], tuple)


def test_checkpoint_payload_freezing_preserves_tuple_plan_fields(tmp_path) -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.ACTION_SELECTED,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    plan = _review_plan()
    plan.action.action.metadata["bounds"] = (1, 2)
    plan.snapshot.metadata["choices"] = ("alpha", "beta")
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
        plan=plan,
    )

    record = store.latest_record
    assert record is not None
    assert record.plan is not None
    assert record.plan.action.proposal.assumptions == ()
    assert isinstance(record.plan.action.proposal.assumptions, tuple)
    assert record.plan.snapshot.active_evidence == ()
    assert isinstance(record.plan.snapshot.active_evidence, tuple)
    assert record.plan.action.action.metadata["bounds"] == (1, 2)
    assert isinstance(record.plan.action.action.metadata["bounds"], tuple)
    assert record.plan.snapshot.metadata["choices"] == ("alpha", "beta")
    assert isinstance(record.plan.snapshot.metadata["choices"], tuple)

    loaded = IncrementalCheckpointStore.load_from_path(
        store.save_to_path(tmp_path / "tuple-plan.json")
    )
    loaded_record = loaded.latest_record
    assert loaded_record is not None
    assert loaded_record.plan is not None
    assert loaded_record.plan.action.proposal.assumptions == ()
    assert isinstance(loaded_record.plan.action.proposal.assumptions, tuple)
    assert loaded_record.plan.snapshot.active_evidence == ()
    assert isinstance(loaded_record.plan.snapshot.active_evidence, tuple)
    assert loaded_record.plan.action.action.metadata["bounds"] == (1, 2)
    assert isinstance(loaded_record.plan.action.action.metadata["bounds"], tuple)
    assert loaded_record.plan.snapshot.metadata["choices"] == ("alpha", "beta")
    assert isinstance(loaded_record.plan.snapshot.metadata["choices"], tuple)


def test_checkpoint_payload_encoding_escapes_reserved_user_mappings(tmp_path) -> None:
    collision = {
        "schema": CHECKPOINT_TUPLE_SCHEMA,
        "items": ["literal", "user", "mapping"],
    }
    near_collision = {
        "schema": CHECKPOINT_TUPLE_SCHEMA,
        "items": "not-an-internal-tuple",
    }
    events = CampaignEventLog(RUN_ID)
    events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload={
            "collision": collision,
            "near_collision": near_collision,
        },
    )
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.ACTION_SELECTED,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
        metadata={
            "collision": collision,
            "near_collision": near_collision,
            "nested": {"collision": collision},
        },
    )
    plan = _review_plan()
    plan.action.action.metadata["collision"] = collision
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
        plan=plan,
    )

    record = store.latest_record
    assert record is not None
    assert record.plan is not None
    assert record.run_state.metadata["collision"] == collision
    assert isinstance(record.run_state.metadata["collision"], dict)
    assert record.run_state.metadata["near_collision"] == near_collision
    assert record.plan.action.action.metadata["collision"] == collision

    loaded = IncrementalCheckpointStore.load_from_path(
        store.save_to_path(tmp_path / "reserved-mapping.json")
    )
    loaded_record = loaded.latest_record
    assert loaded_record is not None
    assert loaded_record.plan is not None
    assert loaded_record.run_state.metadata["collision"] == collision
    assert isinstance(loaded_record.run_state.metadata["collision"], dict)
    assert loaded_record.run_state.metadata["near_collision"] == near_collision
    assert loaded_record.run_state.metadata["nested"]["collision"] == collision
    assert loaded_record.plan.action.action.metadata["collision"] == collision

    loaded_materialized = loaded.latest()
    assert loaded_materialized is not None
    assert loaded_materialized.run.metadata["collision"] == collision
    assert isinstance(loaded_materialized.run.metadata["collision"], dict)
    assert loaded_materialized.events.events[0].payload["collision"] == collision
    assert isinstance(loaded_materialized.events.events[0].payload["collision"], dict)


def test_materialized_events_are_defensive_copies(tmp_path) -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload={"nested": {"attempts": [1]}},
    )
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )
    before = copy.deepcopy(store.to_dict()["events"])

    materialized = store.latest()
    assert materialized is not None
    materialized.events.events[0].payload["nested"]["attempts"].append(2)

    with pytest.raises(PersistenceIntegrityError, match="immutable"):
        store._events[0].payload["nested"]["attempts"].append(3)

    assert materialized.events.events[0].payload["nested"]["attempts"] == [1, 2]
    assert store.to_dict()["events"] == before
    assert store.verify_committed()
    path = store.save_to_path(tmp_path / "checkpoint.json")
    assert IncrementalCheckpointStore.load_from_path(path).verify_committed()


def test_saved_events_do_not_share_caller_payload() -> None:
    payload = {"nested": {"attempts": [1]}}
    events = CampaignEventLog(RUN_ID)
    events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload=payload,
    )
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=1,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )
    before = copy.deepcopy(store.to_dict()["events"])

    payload["nested"]["attempts"].append(2)
    with pytest.raises(TypeError, match="immutable"):
        events.events[0].payload["nested"]["attempts"].append(3)

    assert store.to_dict()["events"] == before
    assert store.verify_committed()


def test_event_payload_prefix_mutation_fails_at_source() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(
        CampaignEventType.CAMPAIGN_CREATED,
        iteration=0,
        payload={"nested": {"attempts": [1]}},
    )
    events.append(
        CampaignEventType.SNAPSHOT_CREATED,
        iteration=1,
        payload={"tail": True},
    )
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=2,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )
    before = copy.deepcopy(store.to_dict()["events"])

    with pytest.raises(TypeError, match="immutable"):
        events.events[0].payload["nested"]["attempts"].append(2)

    assert store.to_dict()["events"] == before
    assert events.to_dict()["events"] == before
    assert store.verify_committed()


def test_budget_charge_history_rebind_fails_closed_on_normal_saves() -> None:
    events = CampaignEventLog(RUN_ID)
    events.append(CampaignEventType.CAMPAIGN_CREATED, iteration=0)
    budget = BudgetLedger(total_budget=10.0, reserved_validation_budget=1.0)
    first = budget.settle(
        charge_id="charge-1",
        action_id="action-1",
        iteration=1,
        family=ActionFamily.EXPLORE,
        realized=1.0,
        predicted=1.0,
    )
    budget.settle(
        charge_id="charge-2",
        action_id="action-2",
        iteration=2,
        family=ActionFamily.EXPLORE,
        realized=2.0,
        predicted=2.0,
    )
    run = CampaignRun(
        run_id=RUN_ID,
        campaign_id="v03-review-campaign",
        state=ExecutionState.READY,
        iteration=1,
        max_iterations=2,
        event_log_digest=events.head_digest,
    )
    store = IncrementalCheckpointStore()
    store.save_state(
        run=run,
        events=events,
        budget=budget,
        effects=EffectLedger(),
    )
    before = copy.deepcopy(store.to_dict()["budget_journal"])
    altered = BudgetCharge(
        charge_id=first.charge_id,
        action_id=first.action_id,
        iteration=first.iteration,
        family=first.family,
        realized=3.0,
        predicted=first.predicted,
        from_general_pool=3.0,
        detail=first.detail,
    )

    with pytest.raises(BudgetHistoryViolation, match="BudgetLedger.settle"):
        budget.charges = (altered, budget.charges[-1])

    assert budget.charges[0].to_dict() == first.to_dict()
    assert store.to_dict()["budget_journal"] == before
    assert store.verify_committed()
