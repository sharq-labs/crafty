"""Installed-wheel-only Release 1 bounded-cycle gate.

The frozen D7 reference is explicitly loaded by file path.  It is never added
to sys.path and remains experiment-only.  Every engcore import must resolve to
the isolated wheel installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import engcore
from engcore.release1_cycle import run_release1_cycle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forbid-source-prefix", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-commit", required=True)
    args = parser.parse_args()

    package_file = Path(engcore.__file__).resolve()
    forbidden = args.forbid_source_prefix.resolve()
    if package_file.is_relative_to(forbidden):
        raise AssertionError(f"source-tree fallback detected: {package_file}")
    if any(
        Path(entry).resolve() == forbidden.parent.resolve()
        for entry in __import__("sys").path
        if entry
    ):
        raise AssertionError("repository root was added to installed-wheel sys.path")

    cycle = run_release1_cycle(
        output_path=args.output,
        reference_path=args.reference,
        release_commit=args.release_commit,
    )
    artifact_digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(
        json.dumps(
            {
                "status": "PASS",
                "installed_package": str(package_file),
                "source_tree_fallback": False,
                "reference_loaded_by_explicit_path": str(args.reference.resolve()),
                "cycle_identity": cycle.cycle_identity,
                "artifact_sha256": artifact_digest,
                "returned_memory_entry": cycle.selected_observation.memory_entry.identity,
                "generation_2_executed": cycle.generation_2_executed,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
