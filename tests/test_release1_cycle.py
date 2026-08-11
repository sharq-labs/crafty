from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from engcore.design import SelectionEligibility
from engcore.design.candidate import DesignCandidateReference
from engcore.design.evaluation import ResultBinding
from engcore.release1_api import PUBLIC_V1_MANIFEST
from engcore.release1_cycle import (
    RELEASE1_CYCLE_SCHEMA,
    Release1CycleResult,
    Release1LabObservation,
    Release1MindDecision,
    Release1StudyRequest,
    revalidate_release1_cycle,
    run_release1_cycle,
)
from engcore.scientific.errors import InvalidScientificProblem


REPOSITORY = Path(__file__).resolve().parents[1]
REFERENCE = REPOSITORY / "experiments/design_d7/loop.py"


@pytest.fixture(scope="module")
def cycle_and_path(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("release1-cycle") / "release1-cycle.json"
    cycle = run_release1_cycle(
        output_path=path,
        reference_path=REFERENCE,
        release_commit="focused-release1-test",
    )
    return cycle, path


def test_release1_cycle_is_typed_bounded_and_attributable(cycle_and_path) -> None:
    cycle, path = cycle_and_path
    assert isinstance(cycle, Release1CycleResult)
    assert isinstance(cycle.initial_observation, Release1LabObservation)
    assert isinstance(cycle.initial_observation.study, Release1StudyRequest)
    assert isinstance(cycle.mind_decision, Release1MindDecision)
    assert cycle.initial_observation.evaluation.eligibility is SelectionEligibility.ELIGIBLE
    assert cycle.selected_observation.evaluation.eligibility is SelectionEligibility.ELIGIBLE
    assert (
        cycle.initial_observation.result_binding.to_dict()
        == cycle.initial_observation.evaluation.result_binding.to_dict()
    )
    assert (
        cycle.selected_observation.result_binding.to_dict()
        == cycle.selected_observation.evaluation.result_binding.to_dict()
    )
    assert cycle.selected_observation.memory_entry.identity in (
        cycle.final_memory.layer_a.entry_by_identity()
    )
    assert cycle.generation_2_executed is False
    assert path.is_file()


def test_release1_exact_reference_identities(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    assert cycle.initial_observation.candidate.candidate_id == "d4-parent-c"
    assert cycle.initial_observation.twin.reference.key == ("d4-twin:d4-parent-c", "1")
    assert cycle.initial_observation.result.result_id == "d7-g0-result:d4-parent-c:primary"
    assert (
        cycle.mind_decision.decision_identity
        == "d7-decision:sha256:6d1dcb675cf44bb57419c4038a32effac87bd7d793c734bd870ee8e88616ee4a"
    )
    assert cycle.mind_decision.selected_option_label == "B"
    assert cycle.selected_observation.candidate.generation == 1
    assert (
        cycle.selected_observation.result.result_id
        == "d7-selected-result:sha256:05772db87dac7b2f7a18ebc79645ebf85aea7e48a2ef3160354d216c109331b7"
    )


def test_release_record_round_trip_rederives_exact_graph(cycle_and_path) -> None:
    cycle, path = cycle_and_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == RELEASE1_CYCLE_SCHEMA
    assert payload["release"]["distribution_version"] == "1.0.0"
    assert payload["release"]["public_api_manifest_identity"]
    assert payload["environment"]["release_commit"] == "focused-release1-test"
    assert set(payload["environment"]["dependencies"]) == {
        "numpy", "scipy", "scikit-learn", "pint"
    }
    assert payload["scientific_configuration"]["tolerances"] == {}
    loaded = revalidate_release1_cycle(path, reference_path=REFERENCE)
    assert loaded.to_dict() == cycle.to_dict()
    assert Release1CycleResult.from_dict(payload["cycle"]).to_dict() == cycle.to_dict()


def test_two_fresh_cycle_builds_are_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    kwargs = {
        "reference_path": REFERENCE,
        "release_commit": "deterministic-release1-test",
    }
    first_cycle = run_release1_cycle(output_path=first, **kwargs)
    second_cycle = run_release1_cycle(output_path=second, **kwargs)
    assert first.read_bytes() == second.read_bytes()
    assert first_cycle.cycle_identity == second_cycle.cycle_identity


def test_fresh_process_reloads_and_revalidates(tmp_path: Path) -> None:
    record = tmp_path / "fresh-process.json"
    run_release1_cycle(
        output_path=record,
        reference_path=REFERENCE,
        release_commit="fresh-process-release1-test",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(REPOSITORY / "src"), str(REPOSITORY))
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "engcore.release1_cycle",
            "--output",
            str(record),
            "--reference",
            str(REFERENCE),
            "--release-commit",
            "ignored-during-revalidation",
            "--revalidate-only",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["revalidated"] is True


def test_wrong_candidate_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    observation = cycle.initial_observation
    changed_candidate = replace(observation.candidate, candidate_id="substituted-candidate")
    changed_study = replace(observation.study, candidate=changed_candidate)
    with pytest.raises(InvalidScientificProblem):
        replace(observation, study=changed_study)


def test_wrong_twin_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    observation = cycle.initial_observation
    changed_twin = replace(observation.twin, twin_id="substituted-twin")
    with pytest.raises(InvalidScientificProblem):
        replace(observation.study, twin=changed_twin)


def test_wrong_result_binding_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    observation = cycle.initial_observation
    changed_binding = ResultBinding(
        candidate=DesignCandidateReference("substituted-candidate"),
        twin=observation.result_binding.twin,
        design_space=observation.result_binding.design_space,
    )
    with pytest.raises(InvalidScientificProblem):
        replace(observation, result_binding=changed_binding)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("problem_id", "substituted-problem"),
        ("solver_identity", ("substituted-solver", "0.1")),
        ("physics_scope_identity", "substituted-scope"),
    ),
)
def test_wrong_study_problem_solver_or_scope_fails_closed(
    cycle_and_path, field: str, value
) -> None:
    cycle, _ = cycle_and_path
    observation = cycle.initial_observation
    changed_study = replace(observation.study, **{field: value})
    with pytest.raises(InvalidScientificProblem):
        replace(observation, study=changed_study)


def test_wrong_model_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    with pytest.raises(InvalidScientificProblem):
        replace(
            cycle.initial_observation.study,
            model_identity=("substituted-model", "0.1"),
        )


def test_ineligible_evaluation_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    observation = cycle.initial_observation
    changed_evaluation = replace(
        observation.evaluation,
        eligibility=SelectionEligibility.INELIGIBLE,
        eligibility_reasons=("focused substitution test",),
    )
    with pytest.raises(InvalidScientificProblem):
        replace(observation, evaluation=changed_evaluation)


def test_unrelated_memory_entry_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    with pytest.raises(InvalidScientificProblem):
        replace(
            cycle.initial_observation,
            memory_entry=cycle.selected_observation.memory_entry,
        )


def test_substituted_selected_candidate_or_twin_fails_closed(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    selected = cycle.selected_observation
    changed_candidate = replace(selected.candidate, candidate_id="substituted-selected")
    changed_study = replace(selected.study, candidate=changed_candidate)
    with pytest.raises(InvalidScientificProblem):
        replace(selected, study=changed_study)
    changed_twin = replace(selected.twin, twin_id="substituted-selected-twin")
    with pytest.raises(InvalidScientificProblem):
        replace(selected.study, twin=changed_twin)


def test_prediction_or_decision_provenance_cannot_be_evidence(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    selected = cycle.selected_observation
    decision_as_evidence = replace(
        selected.twin,
        evidence_refs=(cycle.mind_decision.decision_identity,),
    )
    changed_study = replace(selected.study, twin=decision_as_evidence)
    with pytest.raises(InvalidScientificProblem):
        replace(selected, study=changed_study)
    prediction_as_evidence = replace(
        selected.twin,
        evidence_refs=("prediction:d7-reference-alpha",),
    )
    changed_study = replace(selected.study, twin=prediction_as_evidence)
    with pytest.raises(InvalidScientificProblem):
        replace(selected, study=changed_study)


def test_result_id_alone_is_not_mind_evidence(cycle_and_path) -> None:
    cycle, _ = cycle_and_path
    with pytest.raises(InvalidScientificProblem):
        replace(
            cycle.mind_decision,
            source_evidence=(
                {"result_id": cycle.initial_observation.result.result_id},
            ),
        )


def test_tampered_record_fails_rederivation_even_with_recomputed_cycle_identity(
    cycle_and_path, tmp_path: Path
) -> None:
    _cycle, source_path = cycle_and_path
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["cycle"]["mind_decision"]["selected_option_label"] = "A"
    destination = tmp_path / "tampered.json"
    destination.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    with pytest.raises(InvalidScientificProblem):
        revalidate_release1_cycle(destination, reference_path=REFERENCE)


def test_release_cycle_symbols_remain_release_internal() -> None:
    declared = {
        (module_name, symbol)
        for namespaces in PUBLIC_V1_MANIFEST["categories"].values()
        for module_name, symbols in namespaces.items()
        for symbol in symbols
    }
    assert not any(module_name == "engcore.release1_cycle" for module_name, _ in declared)
    assert not {
        "Release1StudyRequest",
        "Release1LabObservation",
        "Release1MindDecision",
        "Release1CycleResult",
        "run_release1_cycle",
        "revalidate_release1_cycle",
    } & {symbol for _, symbol in declared}
