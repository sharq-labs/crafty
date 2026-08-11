"""Execute all curated examples against an isolated installed wheel."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import engcore


EXPECTED_LABELS = {
    "01_lab_dc.py": "ACTUAL ELECTRICAL DC EXECUTION",
    "02_twin_attributable_evaluation.py": "NOT PHYSICAL VALIDATION",
    "03_mind_reference.py": "NOT PHYSICAL VALIDATION",
    "04_closed_loop.py": "NOT PHYSICAL-WORLD VALIDATION",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forbid-source-prefix", type=Path, required=True)
    parser.add_argument("--examples-dir", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--release-commit", required=True)
    args = parser.parse_args()

    package_file = Path(engcore.__file__).resolve()
    forbidden = args.forbid_source_prefix.resolve()
    if package_file.is_relative_to(forbidden):
        raise AssertionError(f"source-tree fallback detected: {package_file}")

    example_paths = tuple(sorted(args.examples_dir.resolve().glob("*.py")))
    if [path.name for path in example_paths] != list(EXPECTED_LABELS):
        raise AssertionError("installed example inventory mismatch")

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    results: dict[str, str] = {}
    for path in example_paths:
        run_dir = args.output_root.resolve() / path.stem
        run_dir.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(path)]
        if path.name == "04_closed_loop.py":
            command.extend(
                (
                    "--reference",
                    str(args.reference.resolve()),
                    "--output-dir",
                    str(run_dir / "artifacts"),
                    "--release-commit",
                    args.release_commit,
                )
            )
        completed = subprocess.run(
            command,
            cwd=run_dir,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"{path.name} failed:\n{completed.stdout}{completed.stderr}"
            )
        if EXPECTED_LABELS[path.name] not in completed.stdout:
            raise AssertionError(f"{path.name} did not print its honesty label")
        if path.name == "04_closed_loop.py":
            payload = json.loads(completed.stdout[completed.stdout.find("{") :])
            if payload["generation_2_executed"] is not False:
                raise AssertionError("Example 04 executed Generation 2")
            if payload["physical_world_validation"] is not False:
                raise AssertionError("Example 04 misstated physical validation")
            if not all(payload["replay"].values()):
                raise AssertionError("Example 04 replay comparison failed")
        results[path.name] = "PASS"

    print(
        json.dumps(
            {
                "status": "PASS",
                "installed_package": str(package_file),
                "source_tree_fallback": False,
                "examples": results,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
