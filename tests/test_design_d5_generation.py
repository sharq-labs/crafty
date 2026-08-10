from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engcore.design import d4_recombination as d4
from engcore.design import d5_generation as d5
from engcore.design.candidate import DesignCandidate
from engcore.design.evaluation import DesignEvaluation
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.twins.definition import ScientificTwin


def _plain_assignments(candidate: DesignCandidate) -> dict[str, object]:
    return {
        name: value.value
        for name, value in sorted(candidate.assignments.items(), key=lambda item: item[0])
    }


def _fixture():
    g0 = d5.build_generation0()
    derivation = d5.derive_generation1(g0=g0)
    metrics = d5.comparison_metrics(g0=g0, derivation=derivation)
    return g0, derivation, metrics


def test_deterministic_generation0_construction_and_memory() -> None:
    first = d5.build_generation0()
    second = d5.build_generation0()
    assert first.population.to_dict() == second.population.to_dict()
    assert [candidate.to_dict() for candidate in first.candidates] == [
        candidate.to_dict() for candidate in second.candidates
    ]
    assert first.population.population_id == d5.G0_POPULATION_ID
    assert first.population.generation == 0
    assert [candidate.candidate_id for candidate in first.candidates] == [
        "d4-parent-a",
        "d4-parent-b",
        "d4-parent-c",
        "d4-parent-d",
    ]
    assert [_plain_assignments(candidate) for candidate in first.candidates] == [
        {
            "adapter": "buffered",
            "component_a": "A_peak",
            "component_b": "B_base",
            "control_level": 2,
            "guard_enabled": False,
        },
        {
            "adapter": "direct",
            "component_a": "A_base",
            "component_b": "B_peak",
            "control_level": 0,
            "guard_enabled": False,
        },
        {
            "adapter": "direct",
            "component_a": "A_stable",
            "component_b": "B_base",
            "control_level": 1,
            "guard_enabled": True,
        },
        {
            "adapter": "buffered",
            "component_a": "A_base",
            "component_b": "B_filter",
            "control_level": 2,
            "guard_enabled": True,
        },
    ]
    assert all(
        evaluation.eligibility_reasons
        == ("preregistered D5 Generation 0 synthetic evaluation",)
        for evaluation in first.evaluations
    )
    assert len(first.d3_entries) == 4
    assert first.memory_record.policy.policy_id == d5.G0_MEMORY_POLICY_ID
    assert first.memory_record.layer_a.scope.context_reference == d5.SCIENTIFIC_SCOPE_CONTEXT


def test_exact_proposal_set_a_rejection_and_b_through_e_materialization() -> None:
    g0 = d5.build_generation0()
    proposals = d5.proposal_set(g0)
    assert [proposal.label for proposal in proposals] == ["A", "B", "C", "D", "E"]
    assert len({proposal.proposal_identity for proposal in proposals}) == 5
    assert all(proposal.proposal_identity.startswith("d5-proposal:sha256:") for proposal in proposals)
    assert d5.D5Generation1Proposal.from_dict(proposals[2].to_dict()).to_json() == proposals[2].to_json()

    derivation = d5.derive_generation1(g0=g0, proposals=proposals)
    outcomes = {outcome.proposal.label: outcome for outcome in derivation.outcomes}
    assert outcomes["A"].compatibility.state is d4.CompatibilityState.INCOMPATIBLE
    assert outcomes["A"].child_candidate is None
    for label in ("B", "C", "D", "E"):
        outcome = outcomes[label]
        assert outcome.compatibility.state is d4.CompatibilityState.COMPATIBLE
        assert outcome.child_candidate is not None
        assert outcome.child_twin is not None
        assert outcome.child_evaluation is not None
        assert outcome.lineage is not None
        assert outcome.child_candidate.candidate_id == outcome.proposal.candidate_id
        assert outcome.child_twin.twin_id == outcome.proposal.twin_id
        assert outcome.child_candidate.generation == 1
        assert outcome.child_candidate.operator == d5.G1_OPERATOR
        assert outcome.child_evaluation.eligibility_reasons == (
            "preregistered D5 Generation 1 synthetic evaluation",
        )
        d5.validate_lineage(outcome)


def test_d3_d4_provenance_candidate_identity_new_twin_and_no_inheritance() -> None:
    g0, derivation, _ = _fixture()
    parent_candidate_ids = {candidate.candidate_id for candidate in g0.candidates}
    parent_twin_keys = {twin.reference.key for twin in g0.twins}
    parent_eval_ids = {evaluation.evaluation_id for evaluation in g0.evaluations}
    parent_result_ids = {evaluation.result.result_id for evaluation in g0.evaluations}
    d3_by_candidate = {entry.candidate.candidate_id: entry for entry in g0.d3_entries}

    for outcome in derivation.outcomes:
        for source in outcome.proposal.selected_sources:
            assert source.d3_entry_identity == d3_by_candidate[
                source.parent_candidate.candidate_id
            ].identity
            assert source.d3_entry_digest == d3_by_candidate[
                source.parent_candidate.candidate_id
            ].entry_digest
            assert source.parent_evaluation.evaluation_id.startswith("d5-g0-evaluation:")
        if outcome.child_candidate is None:
            continue
        assert outcome.child_candidate.candidate_id not in parent_candidate_ids
        assert outcome.child_twin.reference.key not in parent_twin_keys
        assert outcome.child_evaluation.evaluation_id not in parent_eval_ids
        assert outcome.child_evaluation.result.result_id not in parent_result_ids
        assert outcome.child_twin.scientific_context() == {
            datum.name: datum.value.value for datum in outcome.child_twin.declarations
        }
        assert "d5_proposal_identity" in outcome.child_twin.metadata
        assert "d4_recombination_event" in outcome.child_twin.metadata
        assert outcome.child_twin.evidence_refs == ()
        assert outcome.child_twin.calibration_evidence_refs == ()
        d5.validate_no_inheritance(
            child_candidate=outcome.child_candidate,
            child_twin=outcome.child_twin,
            child_evaluation=outcome.child_evaluation,
            parent_evaluations=g0.evaluations,
        )


def test_novelty_duplicates_diversity_lineage_and_serialization_roundtrip() -> None:
    g0, derivation, _ = _fixture()
    assert derivation.duplicate_count == 0
    assert derivation.novel_assignment_count == 4
    accepted = [outcome for outcome in derivation.outcomes if outcome.child_candidate]
    assert len(accepted) == 4
    assert len(
        {d5.assignment_digest(outcome.child_candidate.assignments) for outcome in accepted}
    ) == 4
    assert {
        d5.assignment_digest(candidate.assignments) for candidate in g0.candidates
    }.isdisjoint(
        {d5.assignment_digest(outcome.child_candidate.assignments) for outcome in accepted}
    )
    assert len({outcome.child_candidate.assignments["component_a"].value for outcome in accepted}) >= 2
    assert len({outcome.child_candidate.assignments["component_b"].value for outcome in accepted}) >= 2
    assert len({tuple(parent.candidate_id for parent in outcome.child_candidate.parents) for outcome in accepted}) >= 2
    assert derivation.deterministic_round_trip is True
    assert json.loads(derivation.to_json())["schema"] == d5.D5_DERIVATION_SCHEMA
    for outcome in accepted:
        rebuilt = d5.D5GenerationLineage.from_dict(outcome.lineage.to_dict())
        assert rebuilt.to_json() == outcome.lineage.to_json()


def test_permutation_invariance_for_proposal_input_and_parent_source_order() -> None:
    g0 = d5.build_generation0()
    proposals = d5.proposal_set(g0)
    baseline = d5.derive_generation1(g0=g0, proposals=proposals)
    permuted = d5.derive_generation1(g0=g0, proposals=tuple(reversed(proposals)))
    assert d5.proposal_outcome_summary(permuted) == d5.proposal_outcome_summary(baseline)
    proposal_c = next(proposal for proposal in proposals if proposal.label == "C")
    reversed_sources = replace(
        proposal_c,
        selected_sources=tuple(reversed(proposal_c.selected_sources)),
    )
    assert reversed_sources.proposal_identity == proposal_c.proposal_identity
    assert reversed_sources.candidate_id == proposal_c.candidate_id


def test_exact_gen0_gen1_scientific_results_and_comparison_metrics() -> None:
    _, derivation, metrics = _fixture()
    assert metrics["generation0"]["results"] == {
        "d4-parent-a": {"loss_score": 30.0, "stability_score": 9.0, "yield_score": 64.0},
        "d4-parent-b": {"loss_score": 20.0, "stability_score": -7.0, "yield_score": 58.0},
        "d4-parent-c": {"loss_score": 18.0, "stability_score": 44.0, "yield_score": 39.0},
        "d4-parent-d": {"loss_score": 6.0, "stability_score": 51.0, "yield_score": 29.0},
    }
    outcomes = d5.proposal_outcome_summary(derivation)
    assert outcomes["A"]["compatibility_state"] == "INCOMPATIBLE"
    assert outcomes["A"]["child_created"] is False
    assert outcomes["B"]["scientific_result"] == {
        "loss_score": 39.0,
        "stability_score": 1.0,
        "yield_score": 34.0,
    }
    assert outcomes["C"]["scientific_result"] == {
        "loss_score": 5.0,
        "stability_score": 76.0,
        "yield_score": 46.0,
    }
    assert outcomes["D"]["scientific_result"] == {
        "loss_score": 39.0,
        "stability_score": 13.0,
        "yield_score": 80.0,
    }
    assert outcomes["E"]["scientific_result"] == {
        "loss_score": 30.0,
        "stability_score": 9.0,
        "yield_score": 64.0,
    }
    assert metrics["pareto_mode"] == "per-generation"
    assert metrics["generation0"]["population_size"] == 4
    assert metrics["generation0"]["evaluated_count"] == 4
    assert metrics["generation0"]["target_pass_count"] == 0
    assert metrics["generation0"]["pareto_count"] == 4
    assert metrics["generation1"]["proposal_count"] == 5
    assert metrics["generation1"]["accepted_population_size"] == 4
    assert metrics["generation1"]["evaluated_count"] == 4
    assert metrics["generation1"]["target_pass_count"] == 0
    assert metrics["generation1"]["pareto_count"] == 3
    assert metrics["generation1"]["compatibility_rejection_count_by_state"] == {
        "INCOMPATIBLE": 1,
        "INVALID": 0,
    }
    assert metrics["parent_relative_objective_improvements"] == 2
    assert metrics["parent_relative_underperformance"] == 3
    assert metrics["deterministic_round_trip_result"] is True


def test_no_inheritance_and_scope_fail_closed_boundaries() -> None:
    g0, derivation, _ = _fixture()
    outcome = next(item for item in derivation.outcomes if item.proposal.label == "B")
    with pytest.raises(InvalidScientificProblem, match="ScientificResult"):
        d5.materialize_proposal(
            outcome.proposal,
            g0=g0,
            attempted_parent_results=(g0.evaluations[0].result,),
        )
    with pytest.raises(InvalidScientificProblem, match="forbidden"):
        d5.materialize_proposal(
            outcome.proposal,
            g0=g0,
            attempted_status_inheritance={"target_pass": True},
        )
    forged_eval = replace(
        outcome.child_evaluation,
        evaluation_id=g0.evaluations[0].evaluation_id,
    )
    with pytest.raises(InvalidScientificProblem, match="evaluation identity"):
        d5.validate_no_inheritance(
            child_candidate=outcome.child_candidate,
            child_twin=outcome.child_twin,
            child_evaluation=forged_eval,
            parent_evaluations=g0.evaluations,
        )
    forged_scope = replace(
        outcome.child_evaluation.result,
        problem_id="wrong-problem",
    )
    with pytest.raises(InvalidScientificProblem, match="problem id"):
        d5.validate_comparable_scope(
            (
                replace(
                    outcome.child_evaluation,
                    result=forged_scope,
                ),
            )
        )


def test_n1_through_n18_adversarial_cases_pass_closed() -> None:
    results = d5.adversarial_case_results()
    assert list(results) == [f"N{index}" for index in range(1, 19)]
    assert all(item["status"] == "PASS" for item in results.values())


def test_a1_through_a23_gates_and_experiment_payload() -> None:
    payload = d5.experiment_payload(
        targeted_tests="PASS - tests/test_design_d5_generation.py",
        full_regression="PASS - full repository regression",
    )
    gates = payload["a1_a23"]
    assert list(gates) == [f"A{index}" for index in range(1, 24)]
    assert all(gates[f"A{index}"].startswith("PASS") for index in range(1, 18))
    assert all(gates[f"A{index}"].startswith("PASS") for index in range(18, 24))
    assert payload["blocking_gates_passed"] is True
    assert payload["informative_results_recorded"] is True
    assert payload["adversarial_review"]["P0/P1"] == []
    assert set(payload["architecture_pulled"]) == {
        "EvidenceInformedProposal",
        "GenerationLineage",
        "GenerationPlan",
        "PopulationDerivation",
        "no-inheritance guard",
    }
    assert payload["frozen_semantics_unchanged"] == [
        "ScientificTwin",
        "D0",
        "D1",
        "D2",
        "D3",
        "D4",
        "aerospace vertical-slice milestones",
    ]


def test_d5_source_does_not_introduce_forbidden_optimization_or_systems() -> None:
    source = d5.__loader__.get_source(d5.__name__).lower()
    forbidden = (
        "botorch",
        "bayesian",
        "surrogate",
        "acquisition",
        "active learning",
        "reinforcement",
        "evolutionary",
        "llm",
        "database",
        "redis",
        "multirotor",
    )
    for token in forbidden:
        assert token not in source
