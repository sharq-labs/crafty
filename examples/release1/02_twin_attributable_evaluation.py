"""Release 1 Example 02: exact Twin/candidate/result attribution."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json

from engcore.scientific import InvalidScientificProblem, ScientificResult
from engcore.systems.aerospace.multirotor import run_reference_study


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    run = run_reference_study(
        count=1,
        attempt_budget=10,
        source_revision="release1-example-02",
    )
    candidate = run.batch.candidates[0]
    twin = run.batch.twins[0]
    evaluation = run.evaluations[0]
    assessment = run.assessments[0]
    result = evaluation.result
    binding = evaluation.result_binding

    assert isinstance(result, ScientificResult)
    evaluation.validate_candidate(candidate)
    assert candidate.twin.key == twin.reference.key == binding.twin.key

    # A substituted candidate is not tolerated. The expected rejection is
    # caught so the successful tutorial can report the fail-closed behavior.
    mismatch_rejected = False
    try:
        evaluation.validate_candidate(
            replace(candidate, candidate_id="release1-substituted-candidate")
        )
    except InvalidScientificProblem:
        mismatch_rejected = True

    summary = {
        "system": "MVR0 multirotor analytic reference",
        "physical_validation": False,
        "candidate_id": candidate.candidate_id,
        "twin_id": twin.twin_id,
        "twin_version": twin.version,
        "model_identities": [list(item) for item in result.models],
        "solver_identity": "closed analytic reference; not a numerical solver",
        "result_id": result.result_id,
        "binding_sha256": _digest(binding.to_dict()),
        "binding": {
            "candidate_id": binding.candidate.candidate_id,
            "twin_key": list(binding.twin.key),
            "design_space_key": list(binding.design_space.key),
        },
        "evaluation_id": evaluation.evaluation_id,
        "selection_eligibility": evaluation.eligibility.value,
        "reference_target_pass": assessment.meets_target,
        "selected_metrics": {
            "total_mass_kg": result.value("total_mass").magnitude_in("kg"),
            "hover_endurance_s": result.value("hover_endurance").magnitude_in("s"),
        },
        "fail_closed_candidate_mismatch_rejected": mismatch_rejected,
    }
    print("LAB V1 - ATTRIBUTABLE TWIN EVALUATION")
    print("ANALYTIC REFERENCE SYSTEM - NOT PHYSICAL VALIDATION")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
