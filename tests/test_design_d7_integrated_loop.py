from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from engcore.design import d4_recombination as d4
from engcore.design.evaluation import SelectionEligibility
from engcore.design.memory import DesignMemoryEntry
from engcore.scientific.errors import InvalidScientificProblem
from experiments.design_d7 import loop as d7


@pytest.fixture(scope="module")
def state() -> d7.PreExecutionState:
    return d7.build_pre_execution_state()


def test_exact_generation_zero_and_multiple_evaluation_fixture(state: d7.PreExecutionState) -> None:
    g0 = state.generation_zero
    assert [item.candidate_id for item in g0.candidates] == [
        "d4-parent-a", "d4-parent-b", "d4-parent-c", "d4-parent-d"
    ]
    expected = {
        "d4-parent-a": {"loss_score": 30.0, "stability_score": 9.0, "yield_score": 64.0},
        "d4-parent-b": {"loss_score": 20.0, "stability_score": -7.0, "yield_score": 58.0},
        "d4-parent-c": {"loss_score": 18.0, "stability_score": 44.0, "yield_score": 39.0},
        "d4-parent-d": {"loss_score": 6.0, "stability_score": 51.0, "yield_score": 29.0},
    }
    for evaluation in g0.evaluations:
        assert d7._quantity_plain(evaluation.result.values) == expected[evaluation.candidate.candidate_id]
        assert evaluation.eligibility is SelectionEligibility.ELIGIBLE
    c_evaluations = [item for item in g0.evaluations if item.candidate.candidate_id == "d4-parent-c"]
    assert len(c_evaluations) == 2
    assert len({item.evaluation_id for item in c_evaluations}) == 2
    assert len({item.result.result_id for item in c_evaluations}) == 2
    assert len({item.result.provenance.run_id for item in c_evaluations}) == 2


def test_physics_and_assessment_are_separate_and_cross_scope_fails(state: d7.PreExecutionState) -> None:
    changed_assessment = replace(state.assessment_context, reporting_context_id="changed-report")
    assert changed_assessment.assessment_context_identity != state.assessment_context.assessment_context_identity
    assert d7.build_memory(state.generation_zero, changed_assessment).layer_a.to_dict() == state.memory.layer_a.to_dict()
    changed_physics = replace(state.physics_scope, solver_identity=("changed-solver", "0.1"))
    assert changed_physics.physics_scope_identity != state.physics_scope.physics_scope_identity
    with pytest.raises(InvalidScientificProblem):
        replace(state.authoritative_d4.sources[0], physics_scope=changed_physics)


def test_exact_evaluation_keyed_source_selection_is_order_invariant(state: d7.PreExecutionState) -> None:
    kwargs = {
        "slot_name": "component_a",
        "candidate_id": "d4-parent-c",
        "evaluation_id": "d7-g0-evaluation:d4-parent-c:primary",
        "memory": state.memory,
        "physics_scope": state.physics_scope,
    }
    forward = d7.select_d4_source(
        candidates=state.generation_zero.candidates,
        twins=state.generation_zero.twins,
        evaluations=state.generation_zero.evaluations,
        **kwargs,
    )
    reverse = d7.select_d4_source(
        candidates=tuple(reversed(state.generation_zero.candidates)),
        twins=tuple(reversed(state.generation_zero.twins)),
        evaluations=tuple(reversed(state.generation_zero.evaluations)),
        **kwargs,
    )
    assert forward.to_dict() == reverse.to_dict()
    assert forward.evaluation.evaluation_id.endswith(":primary")
    replicate = d7.select_d4_source(
        slot_name="component_a",
        candidate_id="d4-parent-c",
        evaluation_id="d7-g0-evaluation:d4-parent-c:replicate",
        candidates=state.generation_zero.candidates,
        twins=state.generation_zero.twins,
        evaluations=state.generation_zero.evaluations,
        memory=state.memory,
        physics_scope=state.physics_scope,
    )
    assert replicate.source_identity != forward.source_identity


def test_authoritative_d4_case_c_and_identity_substitution(state: d7.PreExecutionState) -> None:
    authoritative = state.authoritative_d4
    assert authoritative.compatibility.state is d4.CompatibilityState.COMPATIBLE
    assert d7._assignment_plain(authoritative.assignment) == {
        "adapter": "buffered", "component_a": "A_stable", "component_b": "B_filter",
        "control_level": 2, "guard_enabled": True,
    }
    payload = json.loads(json.dumps(authoritative.to_dict()))
    payload["assignment"] = d7._assignment_dict(d4.typed_assignments("A_peak", "B_filter", "buffered", 2, True))
    with pytest.raises(InvalidScientificProblem):
        d7.AuthoritativeD4.from_dict(payload)
    assert d7.AuthoritativeD4.from_dict(authoritative.to_dict()).to_dict() == authoritative.to_dict()


def test_literal_d4_to_d5_identity_and_no_inheritance(state: d7.PreExecutionState) -> None:
    member = state.successor_generation.members[0]
    assert member.role == "AUTHORITATIVE_D4_MATERIALIZATION"
    assert member.candidate.to_dict() == state.authoritative_d4.candidate.to_dict()
    assert member.twin.to_dict() == state.authoritative_d4.twin.to_dict()
    assert not member.candidate.candidate_id.startswith("d5-g1-candidate:")
    assert member.twin.evidence_refs == ()
    assert member.twin.calibration_evidence_refs == ()
    d7.validate_no_inheritance(member.candidate, member.twin)
    with pytest.raises(InvalidScientificProblem):
        d7.validate_no_inheritance(member.candidate, replace(member.twin, evidence_refs=("parent-result",)))


def test_successor_evaluation_and_typed_evidence(state: d7.PreExecutionState) -> None:
    successor = state.successor_evaluation
    assert d7._quantity_plain(successor.evaluation.result.values) == {
        "loss_score": 5.0, "stability_score": 76.0, "yield_score": 46.0
    }
    assert state.assessment_context.classify(successor.evaluation.result.values) == "FAIL"
    assert len(state.evidence_bindings) == 6
    for binding in state.evidence_bindings:
        assert d7.LoopDecisionEvidenceBinding.from_dict(binding.to_dict()).to_dict() == binding.to_dict()
    payload = json.loads(json.dumps(state.evidence_bindings[0].to_dict()))
    payload["result_binding"]["candidate"]["candidate_id"] = "spoof"
    with pytest.raises(InvalidScientificProblem):
        d7.LoopDecisionEvidenceBinding.from_dict(payload)


def test_evidence_derived_novelty_option_identity_and_exact_selection(state: d7.PreExecutionState) -> None:
    expected = {
        "A": (1, 1, "1/1", 0.20),
        "B": (2, 2, "2/2", 0.40),
        "C": (1, 5, "1/5", 0.60),
    }
    for option in state.decision.options:
        assert (
            option.derived_signals["information_proxy_units"], option.compute_cost,
            option.derived_signals["information_per_compute"], option.derived_signals["novelty"],
        ) == expected[option.option_label]
    assert [item.option_label for item in d7.rank_options(state.decision.options)] == ["B", "A", "C"]
    assert state.decision.selected_option.option_label == "B"
    option_a = state.decision.options[0]
    altered = replace(option_a, alpha_prediction=replace(option_a.alpha_prediction, values={**option_a.alpha_prediction.values, "yield_score": 89.0}))
    assert altered.option_identity != option_a.option_identity


def test_checkpoint_is_complete_canonical_and_actually_reloaded(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint, reloaded = d7.real_checkpoint_reload(path)
    assert reloaded
    assert checkpoint.to_bytes() == path.read_bytes()
    assert checkpoint.to_dict()["schema"] == "d7_integrated_loop_checkpoint/1"
    assert d7.D7Checkpoint.from_bytes(path.read_bytes()).to_bytes() == path.read_bytes()
    mutated = json.loads(path.read_text(encoding="utf-8"))
    mutated["payload"]["decision"]["options"][0]["alpha_prediction"]["values"]["yield_score"] += 1
    mutated["checkpoint_identity"] = d7.digest({key: value for key, value in mutated.items() if key != "checkpoint_identity"})
    with pytest.raises(InvalidScientificProblem):
        d7.D7Checkpoint.from_bytes(d7.canonical_bytes(mutated))
    incomplete = json.loads(path.read_text(encoding="utf-8"))
    del incomplete["payload"]["successor_generation"]["lineage"]
    incomplete["checkpoint_identity"] = d7.digest({key: value for key, value in incomplete.items() if key != "checkpoint_identity"})
    with pytest.raises(InvalidScientificProblem):
        d7.D7Checkpoint.from_bytes(d7.canonical_bytes(incomplete))


def test_selected_execution_exact_binding_and_return_arrow(state: d7.PreExecutionState) -> None:
    execution = d7.execute_selected(state)
    selected = execution.request.selected
    assert d7._assignment_plain(selected.candidate.assignments) == {
        "adapter": "buffered", "component_a": "A_peak", "component_b": "B_filter",
        "control_level": 1, "guard_enabled": False,
    }
    assert selected.twin.kind.value == "derived"
    assert selected.candidate.generation == 1
    assert selected.twin.evidence_refs == ()
    assert selected.twin.calibration_evidence_refs == ()
    assert d7._quantity_plain(execution.result.values) == {
        "loss_score": 33.0, "stability_score": -12.0, "yield_score": 35.0
    }
    assert execution.target == "FAIL"
    assert execution.evaluation.eligibility is SelectionEligibility.ELIGIBLE
    assert execution.result.provenance.metadata[d7.RESULT_BINDING_METADATA_KEY] == execution.result_binding.to_dict()
    admission = d7.admit_return(state, execution)
    expected = DesignMemoryEntry.from_evaluation(
        scope=state.memory.layer_a.scope,
        candidate=selected.candidate,
        evaluation=execution.evaluation,
    )
    assert admission.returned_entry.to_dict() == expected.to_dict()
    assert admission.next_cycle_source.entry.to_dict() == admission.returned_entry.to_dict()
    assert admission.next_cycle_source.selected_value.value == "A_peak"


def test_selected_execution_substitutions_fail_before_result(state: d7.PreExecutionState) -> None:
    with pytest.raises(InvalidScientificProblem):
        d7.execute_selected(
            state,
            attempted_assignment=d4.typed_assignments("A_peak", "B_filter", "buffered", 2, False),
        )
    selected = d7.materialize_selected(state)
    with pytest.raises(InvalidScientificProblem):
        d7.execute_selected(state, attempted_twin=replace(selected.twin, twin_id="wrong-twin"))


def test_full_object_trace_is_deterministic_from_checkpoint_bytes(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint, _ = d7.real_checkpoint_reload(path)
    first = d7.complete_object_trace(checkpoint, d7.admit_return(checkpoint.state, d7.execute_selected(checkpoint.state)))
    reloaded = d7.D7Checkpoint.from_bytes(path.read_bytes())
    second = d7.complete_object_trace(reloaded, d7.admit_return(reloaded.state, d7.execute_selected(reloaded.state)))
    assert d7.canonical_bytes(first) == d7.canonical_bytes(second)
    assert first["schema"] == "d7_integrated_object_trace/1"
    assert first["next_cycle_d4_source_identity"]
    assert first["final_trace_identity"] == d7.digest({key: value for key, value in first.items() if key != "final_trace_identity"})


def test_process_restart_replays_same_trace_identity(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint, _ = d7.real_checkpoint_reload(checkpoint_path)
    expected = d7.complete_object_trace(checkpoint, d7.admit_return(checkpoint.state, d7.execute_selected(checkpoint.state)))["final_trace_identity"]
    code = (
        "from pathlib import Path; from experiments.design_d7 import loop as d; "
        f"c=d.D7Checkpoint.from_bytes(Path(r'{checkpoint_path}').read_bytes()); "
        "a=d.admit_return(c.state,d.execute_selected(c.state)); "
        "print(d.complete_object_trace(c,a)['final_trace_identity'])"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join([str(Path.cwd() / "src"), str(Path.cwd())])
    output_path = tmp_path / "restart-trace.txt"
    with output_path.open("w", encoding="utf-8") as output:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            text=True,
            env=environment,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=False,
        )
    assert completed.returncode == 0, output_path.read_text(encoding="utf-8")
    observed = output_path.read_text(encoding="utf-8").strip()
    assert observed == expected


def test_n1_n24_all_match_frozen_outcomes(tmp_path: Path) -> None:
    checkpoint, _ = d7.real_checkpoint_reload(tmp_path / "checkpoint.json")
    admission = d7.admit_return(checkpoint.state, d7.execute_selected(checkpoint.state))
    results = d7.adversarial_case_results(checkpoint, admission)
    assert list(results) == [f"N{index}" for index in range(1, 25)]
    assert all(item["status"] == "PASS" for item in results.values())


def test_a1_a23_are_all_blocking_and_pass_with_completed_evidence(tmp_path: Path) -> None:
    payload = d7.experiment_payload(
        checkpoint_path=tmp_path / "checkpoint.json",
        targeted_tests="PASS - focused D7",
        full_regression="PASS - repository",
    )
    assert list(payload["a1_a23"]) == [f"A{index}" for index in range(1, 24)]
    assert all(value.startswith("PASS") for value in payload["a1_a23"].values())
    assert payload["blocking_gates_passed"]
    assert payload["adversarial_cases_passed"]
    assert not payload["adversarial_review_has_p0_p1"]
    assert payload["generation_2_executed"] is False


def test_frozen_preregistration_checkpoint_label_and_local_architecture() -> None:
    assert d7.PREREGISTRATION_CHECKPOINT == "86f8b4879a7e3da4839d53b209f51f09e55a742b"
    source = Path(d7.__file__).read_text(encoding="utf-8").lower()
    for forbidden in ("postgresql", "redis", "kubernetes", "boto3"):
        assert forbidden not in source
    assert "src/engcore" not in str(Path(d7.__file__).as_posix())
