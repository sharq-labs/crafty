from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engcore.design import d4_recombination as d4
from engcore.design.evaluation import RESULT_BINDING_METADATA_KEY
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.twins.definition import TwinKind
from engcore.scientific.units.quantity import Quantity


def _fixture():
    space, candidates, twins, evaluations, entries = (
        d4.build_parent_candidates_and_memory()
    )
    cases = d4.preregistered_cases(
        candidates=candidates, evaluations=evaluations, d3_entries=entries
    )
    return space, candidates, twins, evaluations, entries, cases


def _run_case(name: str):
    _, candidates, twins, evaluations, entries, cases = _fixture()
    sources, assignments = cases[name]
    return d4.materialize_recombination(
        selected_sources=sources,
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )


def test_all_compatibility_states_pair_matrix_and_adapter_requirements() -> None:
    _, candidates, twins, evaluations, entries, cases = _fixture()
    case_a = _run_case("A")
    assert case_a.compatibility.state is d4.CompatibilityState.INCOMPATIBLE
    assert case_a.child_candidate is None
    assert case_a.child_twin is None
    assert case_a.child_evaluation is None

    case_b = _run_case("B")
    assert case_b.compatibility.state is d4.CompatibilityState.COMPATIBLE
    assert case_b.child_candidate is not None

    b_sources, _ = cases["B"]
    invalid_adapter = d4.typed_assignments("A_peak", "B_filter", "direct", 2, True)
    incompatible = d4.assess_compatibility(
        selected_sources=b_sources,
        child_assignments=invalid_adapter,
        parent_candidates=candidates,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )
    assert incompatible.state is d4.CompatibilityState.INVALID
    assert "child-source-assignment-match" in incompatible.failed_rule_ids

    altered_context = d4.materialize_recombination(
        selected_sources=b_sources,
        child_assignments=cases["B"][1],
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
        compatibility_context_id="d4-synthetic-compat-v0.1-altered",
    )
    assert altered_context.compatibility.state is d4.CompatibilityState.INVALID
    assert altered_context.child_candidate is None
    assert (
        altered_context.recombination_event_identity
        != case_b.recombination_event_identity
    )


def test_adapter_requirement_incompatible_when_all_source_records_match() -> None:
    _, candidates, twins, evaluations, entries, _ = _fixture()
    sources = (
        d4.source_record(
            slot_name="component_a",
            parent_id="d4-parent-a",
            candidates=candidates,
            evaluations=evaluations,
            d3_entries=entries,
        ),
        d4.source_record(
            slot_name="component_b",
            parent_id="d4-parent-d",
            candidates=candidates,
            evaluations=evaluations,
            d3_entries=entries,
        ),
        d4.source_record(
            slot_name="adapter",
            parent_id="d4-parent-b",
            candidates=candidates,
            evaluations=evaluations,
            d3_entries=entries,
        ),
        d4.source_record(
            slot_name="control_level",
            parent_id="d4-parent-d",
            candidates=candidates,
            evaluations=evaluations,
            d3_entries=entries,
        ),
        d4.source_record(
            slot_name="guard_enabled",
            parent_id="d4-parent-d",
            candidates=candidates,
            evaluations=evaluations,
            d3_entries=entries,
        ),
    )
    result = d4.materialize_recombination(
        selected_sources=sources,
        child_assignments=d4.typed_assignments(
            "A_peak", "B_filter", "direct", 2, True
        ),
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )
    assert result.compatibility.state is d4.CompatibilityState.INCOMPATIBLE
    assert "adapter-requirement" in result.compatibility.failed_rule_ids
    assert result.child_candidate is None


def test_exact_parent_d3_and_component_attribution_fail_closed() -> None:
    _, candidates, twins, evaluations, entries, cases = _fixture()
    sources, assignments = cases["B"]
    missing_parent = replace(
        sources[0], parent_candidate=d4.DesignCandidateReference("missing-parent")
    )
    result = d4.materialize_recombination(
        selected_sources=(missing_parent,) + sources[1:],
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )
    assert result.compatibility.state is d4.CompatibilityState.INVALID
    assert "parent-exists" in result.compatibility.failed_rule_ids

    wrong_twin = replace(sources[0], parent_twin=candidates[1].twin)
    assert d4.assess_compatibility(
        selected_sources=(wrong_twin,) + sources[1:],
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_evaluations=evaluations,
        d3_entries=entries,
    ).state is d4.CompatibilityState.INVALID

    wrong_entry = replace(
        sources[0],
        d3_entry_identity=entries[1].identity,
        d3_entry_digest=entries[1].entry_digest,
    )
    assert d4.assess_compatibility(
        selected_sources=(wrong_entry,) + sources[1:],
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_evaluations=evaluations,
        d3_entries=entries,
    ).failed_rule_ids == ("d3-entry-candidate-match",)

    wrong_value = replace(
        sources[0],
        selected_value=d4.typed_assignments("A_base", "B_base", "direct", 0, False)[
            "component_a"
        ],
    )
    assert d4.assess_compatibility(
        selected_sources=(wrong_value,) + sources[1:],
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_evaluations=evaluations,
        d3_entries=entries,
    ).failed_rule_ids == ("source-value-parent-match",)

    bad_digest = replace(sources[0], d3_entry_digest="0" * 64)
    assert d4.assess_compatibility(
        selected_sources=(bad_digest,) + sources[1:],
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_evaluations=evaluations,
        d3_entries=entries,
    ).failed_rule_ids == ("d3-entry-attribution",)


def test_parent_permutation_identity_and_round_trip_determinism() -> None:
    _, candidates, twins, evaluations, entries, cases = _fixture()
    sources, assignments = cases["C"]
    baseline = d4.materialize_recombination(
        selected_sources=sources,
        child_assignments=assignments,
        parent_candidates=candidates,
        parent_twins=twins,
        parent_evaluations=evaluations,
        d3_entries=entries,
    )
    permuted = d4.materialize_recombination(
        selected_sources=tuple(reversed(sources)),
        child_assignments=dict(reversed(tuple(assignments.items()))),
        parent_candidates=tuple(reversed(candidates)),
        parent_twins=tuple(reversed(twins)),
        parent_evaluations=tuple(reversed(evaluations)),
        d3_entries=tuple(reversed(entries)),
    )
    assert baseline.recombination_event_identity == permuted.recombination_event_identity
    assert baseline.child_candidate.candidate_id == permuted.child_candidate.candidate_id
    assert baseline.child_candidate.candidate_id.startswith("d4-child:sha256:")
    assert baseline.child_candidate.candidate_id not in {
        item.candidate_id for item in candidates
    }
    assert baseline.child_twin.reference.key not in {item.reference.key for item in twins}

    payload = json.loads(baseline.derivation.to_json())
    rebuilt = d4.D4DerivationRecord.from_dict(payload)
    assert rebuilt.to_json() == baseline.derivation.to_json()
    assert rebuilt.parent_candidates == baseline.derivation.parent_candidates
    assert rebuilt.d3_sources == baseline.derivation.d3_sources


def test_identity_collision_materialization_mismatch_and_no_inheritance_guards() -> None:
    _, candidates, twins, evaluations, entries, cases = _fixture()
    sources, assignments = cases["B"]
    with pytest.raises(InvalidScientificProblem, match="supplied child id"):
        d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
            supplied_child_id="d4-child:sha256:wrong",
        )
    with pytest.raises(InvalidScientificProblem, match="assignments differ"):
        d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
            materialized_assignments=d4.typed_assignments(
                "A_peak", "B_filter", "buffered", 1, True
            ),
        )
    with pytest.raises(InvalidScientificProblem, match="parent ScientificResult"):
        d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
            attempted_parent_result_attachment=(evaluations[0].result,),
        )
    with pytest.raises(InvalidScientificProblem, match="forbidden"):
        d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
            attempted_status_inheritance={"pareto_member": True},
        )


def test_child_evaluation_must_bind_child_and_not_parent_result_or_twin() -> None:
    outcome = _run_case("C")
    _, _, _, evaluations, _, _ = _fixture()
    d4.validate_child_scientific_independence(
        derivation=outcome.derivation,
        child_candidate=outcome.child_candidate,
        child_twin=outcome.child_twin,
        child_evaluation=outcome.child_evaluation,
        parent_evaluations=evaluations,
    )
    parent_result = evaluations[0].result
    forged = replace(
        outcome.child_evaluation,
        result=ScientificResult(
            result_id=parent_result.result_id,
            values=outcome.child_evaluation.result.values,
            provenance=ProvenanceRecord(
                run_id="d4-forged-child-run",
                metadata={
                    RESULT_BINDING_METADATA_KEY: outcome.child_evaluation.result_binding.to_dict()
                },
            ),
        ),
    )
    with pytest.raises(InvalidScientificProblem, match="parent ScientificResult"):
        d4.validate_child_scientific_independence(
            derivation=outcome.derivation,
            child_candidate=outcome.child_candidate,
            child_twin=outcome.child_twin,
            child_evaluation=forged,
            parent_evaluations=evaluations,
        )
    forged_twin = replace(outcome.child_twin, twin_id=evaluations[0].twin.twin_id)
    with pytest.raises(InvalidScientificProblem, match="Twin"):
        d4.validate_child_scientific_independence(
            derivation=outcome.derivation,
            child_candidate=outcome.child_candidate,
            child_twin=forged_twin,
            child_evaluation=outcome.child_evaluation,
            parent_evaluations=evaluations,
        )
    assert outcome.child_twin.kind is TwinKind.DERIVED
    assert outcome.child_twin.evidence_refs == ()
    assert outcome.child_twin.calibration_evidence_refs == ()


def test_cases_a_through_d_observed_outcomes_and_counts() -> None:
    _, candidates, _, evaluations, _, _ = _fixture()
    parent_by_id = {item.candidate.candidate_id: item for item in evaluations}
    outcomes = {name: _run_case(name) for name in ("A", "B", "C", "D")}
    assert outcomes["A"].compatibility.state is d4.CompatibilityState.INCOMPATIBLE
    assert outcomes["A"].child_candidate is None

    case_b_values = d4.objective_plain(outcomes["B"].child_evaluation.result.values)
    assert case_b_values == {
        "loss_score": 39.0,
        "stability_score": 1.0,
        "yield_score": 34.0,
    }
    case_b_comparison = d4.compare_child_to_parents(
        child=outcomes["B"].child_evaluation,
        parents=(parent_by_id["d4-parent-a"], parent_by_id["d4-parent-d"]),
    )
    assert case_b_comparison["underperformed_at_least_one_relevant_parent"]

    case_c_values = d4.objective_plain(outcomes["C"].child_evaluation.result.values)
    assert case_c_values == {
        "loss_score": 5.0,
        "stability_score": 76.0,
        "yield_score": 46.0,
    }
    case_c_comparison = d4.compare_child_to_parents(
        child=outcomes["C"].child_evaluation,
        parents=(parent_by_id["d4-parent-c"], parent_by_id["d4-parent-d"]),
    )
    assert set(
        case_c_comparison["improved_objectives_relative_to_all_relevant_parents"]
    ) == {"yield_score", "loss_score", "stability_score"}

    case_d_values = d4.objective_plain(outcomes["D"].child_evaluation.result.values)
    assert case_d_values == {
        "loss_score": 39.0,
        "stability_score": 13.0,
        "yield_score": 80.0,
    }
    assert outcomes["D"].target_pass is False
    assert outcomes["D"].child_evaluation is not None

    assert sum(
        1
        for item in outcomes.values()
        if item.compatibility.state is d4.CompatibilityState.COMPATIBLE
    ) == 3
    assert sum(1 for item in outcomes.values() if item.child_candidate is not None) == 3
    assert len({item.candidate_id for item in candidates}) == 4


def test_d4_source_remains_domain_neutral_and_frozen_d3_compatible() -> None:
    space, candidates, twins, evaluations, entries, cases = _fixture()
    assert space.reference.key == d4.design_space().reference.key
    assert all(entry.design_space.key == space.reference.key for entry in entries)
    for name, (sources, assignments) in cases.items():
        result = d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
        )
        assert result.compatibility.state in {
            d4.CompatibilityState.COMPATIBLE,
            d4.CompatibilityState.INCOMPATIBLE,
        }
        assert name in {"A", "B", "C", "D"}
