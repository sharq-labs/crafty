"""Release 1 Example 04: one bounded synthetic release-reference cycle.

This is the sole curated example allowed to import ``engcore.release1_cycle``.
That module is an explicit release-reference seam, not Public V1. The caller
must supply (or use this release bundle's default) frozen D7 ``loop.py`` path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from engcore.release1_cycle import revalidate_release1_cycle, run_release1_cycle


def _binding_sha256(binding) -> str:
    encoded = json.dumps(
        binding.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    release_bundle_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference",
        type=Path,
        default=release_bundle_root / "experiments/design_d7/loop.py",
        help="explicit read-only frozen D7 loop.py reference",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "release1-example-output",
    )
    parser.add_argument(
        "--release-commit",
        default="release1-installed-wheel-example",
    )
    args = parser.parse_args()

    reference = args.reference.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    frozen_artifact_dir = (reference.parent / "artifacts").resolve()
    if output_dir == frozen_artifact_dir or output_dir.is_relative_to(frozen_artifact_dir):
        raise SystemExit("refusing to write into frozen D7 artifacts")
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact = output_dir / "release1-cycle.json"
    replay_artifact = output_dir / "release1-cycle.replay.json"
    cycle = run_release1_cycle(
        output_path=artifact,
        reference_path=reference,
        release_commit=args.release_commit,
    )
    replay = run_release1_cycle(
        output_path=replay_artifact,
        reference_path=reference,
        release_commit=args.release_commit,
    )
    reloaded = revalidate_release1_cycle(artifact, reference_path=reference)

    initial = cycle.initial_observation
    selected = cycle.selected_observation
    summary = {
        "reference_system": "D4/D7 synthetic analytic reference",
        "physical_world_validation": False,
        "initial": {
            "study_id": initial.study.study_identity,
            "candidate_id": initial.candidate.candidate_id,
            "twin_id": initial.twin.twin_id,
            "model_identity": list(initial.study.model_identity),
            "solver_identity": list(initial.study.solver_identity),
            "result_id": initial.result.result_id,
            "eligibility": initial.evaluation.eligibility.value,
            "binding_sha256": _binding_sha256(initial.result_binding),
            "memory_identity": initial.memory_entry.identity,
        },
        "mind": {
            "decision_identity": cycle.mind_decision.decision_identity,
            "policy_identity": cycle.mind_decision.policy_identity,
            "selected_option": cycle.mind_decision.selected_option_label,
            "selected_study_id": cycle.mind_decision.selected_study.study_identity,
        },
        "selected_execution": {
            "study_id": selected.study.study_identity,
            "candidate_id": selected.candidate.candidate_id,
            "twin_id": selected.twin.twin_id,
            "result_id": selected.result.result_id,
            "eligibility": selected.evaluation.eligibility.value,
            "binding_sha256": _binding_sha256(selected.result_binding),
            "returned_memory_identity": selected.memory_entry.identity,
        },
        "replay": {
            "cycle_identity": cycle.cycle_identity,
            "byte_identical_fresh_runs": artifact.read_bytes()
            == replay_artifact.read_bytes(),
            "fresh_run_identity_match": replay.cycle_identity == cycle.cycle_identity,
            "reload_revalidation_identity_match": reloaded.cycle_identity
            == cycle.cycle_identity,
        },
        "artifacts": {
            "cycle": str(artifact),
            "replay": str(replay_artifact),
        },
        "generation_2_executed": cycle.generation_2_executed,
    }
    print("REFERENCE SYNTHETIC SCIENTIFIC SYSTEM")
    print("NOT PHYSICAL-WORLD VALIDATION")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
