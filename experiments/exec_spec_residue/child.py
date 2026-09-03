"""The fresh-process entry point. Run as a separate interpreter, never imported.

    python -m experiments.exec_spec_residue.child <records_dir> <column> [provider]

It reads ``problem.json`` and, if present, ``structure.json`` from the directory,
reconstructs the executable artifact, runs it, and prints one JSON object on
stdout.

**What it deliberately does not import.** Not :mod:`cases`, which holds the
original artifacts, and not :mod:`encodings`, which imports `cases`. The parent
test asserts this against the module list this process reports, so "the child
could have read the original object" is a checkable claim rather than a promise.

**What it deliberately does not receive.** No pickled object, no import path to
execute, no code. Two JSON files and two strings. That is the whole input.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            json.dumps({"error": "usage: child <records_dir> <column> [provider]"}),
            file=sys.stdout,
        )
        return 2
    directory = pathlib.Path(argv[1])
    column = argv[2]
    provider = argv[3] if len(argv) > 3 else "native"

    problem_payload = json.loads(
        (directory / "problem.json").read_text(encoding="utf-8")
    )
    structure_path = directory / "structure.json"
    structure_payload: Any = None
    if structure_path.is_file():
        structure_payload = json.loads(structure_path.read_text(encoding="utf-8"))

    # Imported here, after the records are in hand, so the import list this
    # process reports is exactly what reconstruction needed.
    from experiments.exec_spec_residue import bridge

    try:
        metrics = bridge.execute(
            column,
            problem_payload,
            structure_payload,
            run_id=f"fresh-process:{column}",
            provider=provider,
        )
    except bridge.ReconstructionError as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "detail": str(exc), "column": column}
            )
        )
        return 1

    leaked = sorted(
        name
        for name in sys.modules
        if name.endswith("exec_spec_residue.cases")
        or name.endswith("exec_spec_residue.encodings")
    )
    print(
        json.dumps(
            {
                "column": column,
                "provider": provider,
                "metrics": metrics,
                # Reported, not asserted here: the parent decides what it means.
                "original_artifact_modules_loaded": leaked,
                "python": sys.version.split()[0],
                "pid": None,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main(sys.argv))
