from __future__ import annotations

import json

import pytest

from engcore.design import (
    DesignCandidate,
    DesignCandidateReference,
    DesignEvaluation,
    DesignEvaluationReference,
    DesignPopulation,
    DesignSpaceReference,
    FidelityLadder,
    FidelityRung,
    FidelitySelection,
    ParetoArchive,
    ScopedEliteArchive,
    SelectionEligibility,
    dominates,
    project_objectives,
)
from engcore.scientific.ir.objectives import ObjectiveDefinition, ObjectiveDirection
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.twins.definition import TwinReference
from engcore.scientific.units.quantity import Quantity
from engcore.scientific.errors import InvalidScientificProblem, ScientificCoreError


SPACE = DesignSpaceReference("general-design", "1")
TWIN_A = TwinReference("twin-a", "1")
TWIN_B = TwinReference("twin-b", "1")
TWIN_C = TwinReference("twin-c", "1")
TWIN_D = TwinReference("twin-d", "1")

RANGE = ObjectiveDefinition(
    name="maximize-range",
    metric="range",
    direction=ObjectiveDirection.MAXIMIZE,
    unit="m",
)
MASS = ObjectiveDefinition(
    name="minimize-mass",
    metric="mass",
    direction=ObjectiveDirection.MINIMIZE,
    unit="kg",
)


def _result(result_id: str, range_m: float, mass_kg: float) -> ScientificResult:
    return ScientificResult(
        result_id=result_id,
        values={"range": Quantity(range_m, "m"), "mass": Quantity(mass_kg, "kg")},
        provenance=ProvenanceRecord(run_id=f"run-{result_id}"),
    )


def _evaluation(
    suffix: str,
    twin: TwinReference,
    range_m: float,
    mass_kg: float,
    *,
    eligibility: SelectionEligibility = SelectionEligibility.ELIGIBLE,
) -> DesignEvaluation:
    reasons = () if eligibility is SelectionEligibility.UNKNOWN else ("declared gate",)
    return DesignEvaluation(
        evaluation_id=f"eval-{suffix}",
        candidate=DesignCandidateReference(f"cand-{suffix}"),
        twin=twin,
        design_space=SPACE,
        result=_result(f"result-{suffix}", range_m, mass_kg),
        eligibility=eligibility,
        eligibility_reasons=reasons,
    )


def test_population_is_deterministic_and_rejects_duplicate_members() -> None:
    population = DesignPopulation(
        population_id="population-0",
        design_space=SPACE,
        generation=0,
        members=(DesignCandidateReference("b"), DesignCandidateReference("a")),
    )
    assert [item.candidate_id for item in population.members] == ["a", "b"]
    payload = population.to_dict()
    assert DesignPopulation.from_dict(payload).to_dict() == payload

    with pytest.raises(InvalidScientificProblem):
        DesignPopulation(
            population_id="bad",
            design_space=SPACE,
            generation=0,
            members=(DesignCandidateReference("a"), DesignCandidateReference("a")),
        )


def test_fidelity_selection_binds_exact_ladder_version_and_rung() -> None:
    ladder = FidelityLadder(
        ladder_id="ladder",
        version="1",
        rungs=(FidelityRung("r0", 0), FidelityRung("r1", 1)),
    )
    selection = FidelitySelection("ladder", "1", "r1")
    assert selection.validate_against(ladder) is selection
    assert FidelitySelection.from_dict(selection.to_dict()) == selection

    with pytest.raises(InvalidScientificProblem):
        FidelitySelection("ladder", "2", "r1").validate_against(ladder)
    with pytest.raises(InvalidScientificProblem):
        FidelitySelection("ladder", "1", "missing").validate_against(ladder)


def test_design_evaluation_requires_explicit_eligibility_reasons_and_candidate_identity() -> None:
    with pytest.raises(InvalidScientificProblem):
        DesignEvaluation(
            evaluation_id="bad",
            candidate=DesignCandidateReference("cand-a"),
            twin=TWIN_A,
            design_space=SPACE,
            result=_result("bad", 1.0, 1.0),
            eligibility=SelectionEligibility.ELIGIBLE,
        )

    evaluation = _evaluation("a", TWIN_A, 10.0, 5.0)
    candidate = DesignCandidate(
        candidate_id="cand-a",
        design_space=SPACE,
        twin=TWIN_A,
        assignments={},
    )
    assert evaluation.validate_candidate(candidate) is evaluation

    mismatch = DesignCandidate(
        candidate_id="cand-a",
        design_space=SPACE,
        twin=TwinReference("different", "1"),
        assignments={},
    )
    with pytest.raises(InvalidScientificProblem):
        evaluation.validate_candidate(mismatch)


def test_objective_projection_reads_only_attributable_result_metrics_and_units() -> None:
    evaluation = _evaluation("a", TWIN_A, 10.0, 5.0)
    projected = project_objectives(evaluation, (RANGE, MASS))
    assert [item.value.magnitude for item in projected] == [10.0, 5.0]
    assert [item.value.unit for item in projected] == ["meter", "kilogram"]

    missing = ObjectiveDefinition(
        name="missing",
        metric="not-in-result",
        direction=ObjectiveDirection.MAXIMIZE,
        unit="m",
    )
    with pytest.raises(ScientificCoreError):
        project_objectives(evaluation, (missing,))


def test_exact_pareto_dominance_preserves_tradeoffs_and_ties() -> None:
    a = _evaluation("a", TWIN_A, 10.0, 5.0)
    b = _evaluation("b", TWIN_B, 9.0, 4.0)
    c = _evaluation("c", TWIN_C, 8.0, 6.0)
    d = _evaluation("d", TWIN_D, 10.0, 5.0)

    assert dominates(a, c, (RANGE, MASS))
    assert dominates(b, c, (RANGE, MASS))
    assert not dominates(a, b, (RANGE, MASS))
    assert not dominates(b, a, (RANGE, MASS))
    assert not dominates(a, d, (RANGE, MASS))
    assert not dominates(d, a, (RANGE, MASS))

    archive = ParetoArchive.build(
        archive_id="pareto",
        design_space=SPACE,
        objectives=(RANGE, MASS),
        evaluations=(c, d, b, a),
    )
    assert [item.evaluation_id for item in archive.members] == [
        "eval-a",
        "eval-b",
        "eval-d",
    ]


def test_pareto_archive_is_order_invariant_and_excludes_noneligible() -> None:
    a = _evaluation("a", TWIN_A, 10.0, 5.0)
    b = _evaluation("b", TWIN_B, 9.0, 4.0)
    c = _evaluation(
        "c", TWIN_C, 1000.0, 0.1, eligibility=SelectionEligibility.INELIGIBLE
    )

    first = ParetoArchive.build(
        archive_id="pareto",
        design_space=SPACE,
        objectives=(RANGE, MASS),
        evaluations=(a, b, c),
    )
    second = ParetoArchive.build(
        archive_id="pareto",
        design_space=SPACE,
        objectives=(RANGE, MASS),
        evaluations=(c, b, a),
    )
    assert first.to_dict() == second.to_dict()
    assert [item.evaluation_id for item in first.members] == ["eval-a", "eval-b"]


def test_scoped_elite_archive_preserves_partial_success_without_component_semantics() -> None:
    a = _evaluation("a", TWIN_A, 10.0, 5.0)
    b = _evaluation("b", TWIN_B, 9.0, 4.0)
    c = _evaluation("c", TWIN_C, 8.0, 6.0)

    range_elite = ScopedEliteArchive.build(
        archive_id="scope-range",
        scope_ref="scope:alpha",
        design_space=SPACE,
        objectives=(RANGE,),
        evaluations=(a, b, c),
    )
    mass_elite = ScopedEliteArchive.build(
        archive_id="scope-mass",
        scope_ref="scope:beta",
        design_space=SPACE,
        objectives=(MASS,),
        evaluations=(a, b, c),
    )

    assert [item.evaluation_id for item in range_elite.members] == ["eval-a"]
    assert [item.evaluation_id for item in mass_elite.members] == ["eval-b"]


def test_d1_records_round_trip_deterministically() -> None:
    evaluation = _evaluation("a", TWIN_A, 10.0, 5.0)
    evaluation_payload = evaluation.to_dict()
    assert DesignEvaluation.from_dict(evaluation_payload).to_dict() == evaluation_payload

    archive = ParetoArchive.build(
        archive_id="pareto",
        design_space=SPACE,
        objectives=(RANGE, MASS),
        evaluations=(evaluation,),
    )
    archive_payload = archive.to_dict()
    assert ParetoArchive.from_dict(archive_payload).to_dict() == archive_payload

    scoped = ScopedEliteArchive.build(
        archive_id="scoped",
        scope_ref="scope:opaque",
        design_space=SPACE,
        objectives=(RANGE,),
        evaluations=(evaluation,),
    )
    scoped_payload = scoped.to_dict()
    assert ScopedEliteArchive.from_dict(scoped_payload).to_dict() == scoped_payload

    assert json.dumps(archive_payload, sort_keys=True) == json.dumps(
        ParetoArchive.from_dict(archive_payload).to_dict(), sort_keys=True
    )
