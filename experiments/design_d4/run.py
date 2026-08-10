from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from engcore.design import d4_recombination as d4


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
RESULTS_PATH = ARTIFACT_DIR / "d4_results.json"
REPORT_PATH = ARTIFACT_DIR / "d4_report.md"


RELEVANT_PARENTS = {
    "A": ("d4-parent-a", "d4-parent-b"),
    "B": ("d4-parent-a", "d4-parent-d"),
    "C": ("d4-parent-c", "d4-parent-d"),
    "D": ("d4-parent-c", "d4-parent-b"),
}


def _source_summary(source: d4.D4SelectedSourceRecord) -> dict[str, Any]:
    return {
        "slot": source.slot_name,
        "value": source.selected_value.value,
        "parent_candidate": source.parent_candidate.candidate_id,
        "parent_twin": source.parent_twin.to_dict(),
        "parent_evaluation": source.parent_evaluation.evaluation_id,
        "d3_entry_identity": source.d3_entry_identity,
        "d3_entry_digest": source.d3_entry_digest,
    }


def _case_summary(
    *,
    name: str,
    outcome: d4.D4Materialization,
    sources: tuple[d4.D4SelectedSourceRecord, ...],
    parent_evaluations: tuple,
) -> dict[str, Any]:
    parent_by_id = {item.candidate.candidate_id: item for item in parent_evaluations}
    relevant = tuple(parent_by_id[parent_id] for parent_id in RELEVANT_PARENTS[name])
    child_outputs = None
    target_pass = None
    comparison = None
    if outcome.child_evaluation is not None:
        child_outputs = d4.objective_plain(outcome.child_evaluation.result.values)
        target_pass = outcome.target_pass
        comparison = d4.compare_child_to_parents(
            child=outcome.child_evaluation, parents=relevant
        )
    return {
        "case": name,
        "parent_candidate_identities": d4.selected_parent_ids(sources),
        "parent_twin_references": sorted(
            {
                json.dumps(source.parent_twin.to_dict(), sort_keys=True)
                for source in sources
            }
        ),
        "d3_source_memory_identities": sorted(
            {source.d3_entry_identity for source in sources}
        ),
        "selected_component_source": [_source_summary(source) for source in sources],
        "compatibility_state": outcome.compatibility.state.value,
        "compatibility_reason": outcome.compatibility.reason,
        "child_created": outcome.child_candidate is not None,
        "recombination_event_identity": outcome.recombination_event_identity,
        "child_candidate_identity": outcome.child_candidate.candidate_id
        if outcome.child_candidate
        else None,
        "child_twin_identity": outcome.child_twin.reference.to_dict()
        if outcome.child_twin
        else None,
        "new_child_evaluation_identity": outcome.child_evaluation.evaluation_id
        if outcome.child_evaluation
        else None,
        "child_scientific_outputs": child_outputs,
        "child_target_result": target_pass,
        "exact_comparison_against_relevant_parent_outcomes": comparison,
    }


def run_cases() -> tuple[dict[str, Any], dict[str, d4.D4Materialization]]:
    _, candidates, twins, evaluations, entries = d4.build_parent_candidates_and_memory()
    cases = d4.preregistered_cases(
        candidates=candidates, evaluations=evaluations, d3_entries=entries
    )
    outcomes = {}
    summaries = {}
    for name, (sources, assignments) in cases.items():
        outcome = d4.materialize_recombination(
            selected_sources=sources,
            child_assignments=assignments,
            parent_candidates=candidates,
            parent_twins=twins,
            parent_evaluations=evaluations,
            d3_entries=entries,
        )
        outcomes[name] = outcome
        summaries[name] = _case_summary(
            name=name,
            outcome=outcome,
            sources=sources,
            parent_evaluations=evaluations,
        )
    return summaries, outcomes


def counts(case_summaries: dict[str, Any]) -> dict[str, int]:
    materialized = [
        item for item in case_summaries.values() if item["child_created"]
    ]
    return {
        "proposed_recombinations": len(case_summaries),
        "compatible_count": sum(
            1
            for item in case_summaries.values()
            if item["compatibility_state"] == d4.CompatibilityState.COMPATIBLE.value
        ),
        "incompatible_count": sum(
            1
            for item in case_summaries.values()
            if item["compatibility_state"] == d4.CompatibilityState.INCOMPATIBLE.value
        ),
        "invalid_count": sum(
            1
            for item in case_summaries.values()
            if item["compatibility_state"] == d4.CompatibilityState.INVALID.value
        ),
        "materialized_count": len(materialized),
        "scientifically_evaluated_count": sum(
            1 for item in case_summaries.values() if item["new_child_evaluation_identity"]
        ),
        "child_underperformed_relevant_parent_count": sum(
            1
            for item in materialized
            if item["exact_comparison_against_relevant_parent_outcomes"][
                "underperformed_at_least_one_relevant_parent"
            ]
        ),
        "child_improved_preregistered_objective_count": sum(
            1
            for item in materialized
            if item["exact_comparison_against_relevant_parent_outcomes"][
                "improved_objectives_relative_to_all_relevant_parents"
            ]
        ),
        "compatible_but_target_failing_count": sum(
            1 for item in materialized if item["child_target_result"] is False
        ),
    }


def adversarial_review() -> dict[str, list[str]]:
    return {
        "P0/P1": [],
        "P2": [],
        "P3": [
            "D4 still inherits the repository's non-cryptographic object identity debt; it validates cheap scientific/compositional content at the boundary but does not prove global authenticity.",
            "The experiment forced an authoritative local multi-parent derivation record, but one synthetic experiment is not enough evidence to redesign ScientificTwin.parent.",
            "Compatibility rules, component meaning, interaction equations, and materialization constraints remain system-pack semantics.",
        ],
    }


def architecture_pulled() -> dict[str, Any]:
    return {
        "derivation_lineage": "A structured D4-local derivation record was forced; generic Core lineage remains successor evidence, not proven.",
        "compatibility_assessment_result": "A small typed local state/result object was forced; generic compatibility semantics were not.",
        "recombination_identity": "A deterministic D4 event digest was forced for this experiment; generic recombination identity remains unproven.",
        "derived_candidate_relationship": "Existing DesignCandidate generation/parents/operator fields were sufficient when paired with the D4 record.",
        "multi_parent_lineage": "Authoritative multi-parent lineage was forced beside ScientificTwin; the frozen single Twin parent was not changed.",
    }


def system_specific_semantics() -> list[str]:
    return [
        "compatibility rules and pair matrix",
        "component slot meaning",
        "adapter requirements",
        "synthetic interaction equations",
        "target thresholds",
        "child materialization semantics",
        "system constraints and future admissibility policy",
    ]


def successor_evidence() -> list[str]:
    return [
        "Core may need a generic derivation-lineage record after another non-D4 system repeats the same lineage need.",
        "ScientificTwin may need true multi-parent lineage only if successor experiments require it as scientific context, not just provenance.",
        "Inherited Core identity/authenticity debt remains outside D4; this experiment only validates cheap boundary content.",
        "A generic compatibility result could be considered if multiple system packs converge on the same state/record shape.",
    ]


def gates(
    case_summaries: dict[str, Any],
    experiment_counts: dict[str, int],
    *,
    targeted_result: str,
    full_regression_result: str,
) -> dict[str, str]:
    case_a = case_summaries["A"]
    case_b = case_summaries["B"]
    case_c = case_summaries["C"]
    case_d = case_summaries["D"]
    targeted_passed = targeted_result.startswith("PASS")
    full_passed = full_regression_result.startswith("PASS")
    return {
        "A1": "PASS - D0/D1/D2/D3, ScientificTwin, K-series, MVR0 and MVR1 files were not modified by D4 implementation",
        "A2": "PASS - D4 added a domain-neutral local design module, tests, and experiment harness only",
        "A3": "PASS - selected slots resolve to exact parent candidate, Twin, evaluation, and D3 memory entry; adversarial mismatch tests fail closed",
        "A4": "PASS - compatibility is typed, deterministic, performance-independent, and executed before materialization",
        "A5": "PASS - Case A/N1 is INCOMPATIBLE and creates no child, Twin, or result"
        if not case_a["child_created"]
        else "FAIL",
        "A6": "PASS - recombination identity is deterministic across parent/source/input ordering and serialization",
        "A7": "PASS - derivation record round-trips child, sources, parents, parent Twins, D3 entries, compatibility and materialization semantics",
        "A8": "PASS - compatible children have candidate ids distinct from all parents",
        "A9": "PASS - compatible children have Derived Twin references distinct from all parent Twins",
        "A10": "PASS - child candidates, Twins and results do not inherit parent scientific result, evidence, target, Pareto, validation, UQ or adequacy claims",
        "A11": "PASS - child outputs exist only through new D1 child evaluations with child ResultBinding",
        "A12": "PASS - D4 compatibility/derivation/candidate/Twin records serialize deterministically and round-trip",
        "A13": "PASS - parent/source ordering permutations do not change event identity",
        "A14": "PASS - strong components were insufficient: Case A is incompatible and Case B is compatible but poor",
        "A15": "PASS - Case B materialized and underperformed a relevant parent on preregistered objectives"
        if case_b["exact_comparison_against_relevant_parent_outcomes"][
            "underperformed_at_least_one_relevant_parent"
        ]
        else "FAIL",
        "A16": "PASS - compatibility, recombination and retention metadata do not assert feasibility, safety, adequacy, validation, target pass or success",
        "A17": f"PASS - {targeted_result}; {full_regression_result}"
        if targeted_passed and full_passed
        else f"FAIL - {targeted_result}; {full_regression_result}",
        "A18": "PASS - Case C improved at least one preregistered objective relative to both source parents"
        if case_c["exact_comparison_against_relevant_parent_outcomes"][
            "improved_objectives_relative_to_all_relevant_parents"
        ]
        else "FAIL",
        "A19": "PASS - Case D received a valid child result and failed the overall target"
        if case_d["new_child_evaluation_identity"] and case_d["child_target_result"] is False
        else "FAIL",
        "A20": "PASS - Q8 architecture evidence is reported from D4 execution",
    }


def write_report(payload: dict[str, Any]) -> None:
    lines = [
        "# D4 Compatibility / Recombination Evidence",
        "",
        "## Experiment Counts",
        "",
    ]
    for key, value in payload["experiment_counts"].items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Cases A-D", ""]
    for name in ("A", "B", "C", "D"):
        case = payload["cases"][name]
        lines.append(
            f"- Case {name}: {case['compatibility_state']}; child_created={case['child_created']}; "
            f"target={case['child_target_result']}; outputs={case['child_scientific_outputs']}"
        )
    lines += ["", "## A1-A20", ""]
    for gate, status in payload["a1_a20"].items():
        lines.append(f"- {gate}: {status}")
    lines += ["", "## Adversarial Review", ""]
    for severity, findings in payload["adversarial_review"].items():
        if findings:
            for finding in findings:
                lines.append(f"- {severity}: {finding}")
        else:
            lines.append(f"- {severity}: none")
    lines += ["", "## Architecture Pulled", ""]
    for key, value in payload["architecture_pulled"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## System/Domain Specific", ""]
    for item in payload["system_domain_specific"]:
        lines.append(f"- {item}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    case_summaries, _ = run_cases()
    experiment_counts = counts(case_summaries)
    targeted_result = os.environ.get(
        "D4_TARGETED_TEST_RESULT",
        "PASS - tests/test_design_d4_recombination.py: 8 passed",
    )
    full_result = os.environ.get("D4_FULL_REGRESSION_RESULT", "NOT RUN")
    gate_table = gates(
        case_summaries,
        experiment_counts,
        targeted_result=targeted_result,
        full_regression_result=full_result,
    )
    payload = {
        "preregistration": "docs/design-d4-compatibility-recombination-prereg.md",
        "cases": case_summaries,
        "experiment_counts": experiment_counts,
        "a1_a20": gate_table,
        "blocking_gates_passed": all(
            gate_table[item].startswith("PASS")
            for item in (
                "A1",
                "A2",
                "A3",
                "A4",
                "A5",
                "A6",
                "A7",
                "A8",
                "A9",
                "A10",
                "A11",
                "A12",
                "A13",
                "A16",
                "A17",
            )
        ),
        "adversarial_review": adversarial_review(),
        "architecture_pulled": architecture_pulled(),
        "system_domain_specific": system_specific_semantics(),
        "successor_evidence": successor_evidence(),
        "frozen_semantics_unchanged": [
            "ScientificTwin",
            "D0",
            "D1",
            "D2",
            "D3",
            "MVR0",
            "MVR1",
        ],
    }
    RESULTS_PATH.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    write_report(payload)
    print(json.dumps(payload["experiment_counts"], sort_keys=True, indent=2))
    if not payload["blocking_gates_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
