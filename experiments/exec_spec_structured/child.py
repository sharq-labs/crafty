"""Fresh-process entry point.

    python -m experiments.exec_spec_structured.child <records_dir> <column>

Reads ``problem.json``, ``structure.json`` and (for the species column)
``numerics.json``, reconstructs, computes, and prints one JSON object.

**It imports :mod:`inject` and nothing else that matters**, and `inject` imports
no probe. That is the correction the adversarial pass forced: in this milestone
the ground truth lives in the *committed probes'* module constants, not in an
``encodings``-held instance, and the guard inherited from `EXEC-SPEC` filtered
only for `encodings`. The child therefore held the answer while its reported
metrics were computed by `mech.run_shear_case()` and `spc.integrate()` — the
probe compared against itself in two processes.

Now every number reported here is computed from the records, and the child
reports its own ``experiments.cross_domain_coverage`` module list so the parent
can assert it is empty rather than take the isolation on trust.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(json.dumps({"error": "usage: child <records_dir> <column>"}))
        return 2
    directory = pathlib.Path(argv[1])
    column = argv[2]

    def load(name: str) -> Any:
        path = directory / name
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    problem_payload = load("problem.json")
    structure_payload = load("structure.json")
    numerics_payload = load("numerics.json")

    from experiments.exec_spec_structured import inject

    try:
        report = dict(
            inject.reconstruct_and_inject(
                column, problem_payload, structure_payload, numerics_payload
            )
        )
    except inject.StructuredReconstructionError as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "detail": str(exc), "column": column}
            )
        )
        return 1

    # The isolation guard, pointed at where the originals actually live.
    report["probe_modules_loaded"] = sorted(
        name
        for name in sys.modules
        if name.startswith("experiments.cross_domain_coverage")
    )
    report["encoding_modules_loaded"] = sorted(
        name
        for name in sys.modules
        if name.endswith("exec_spec_structured.encodings")
        or name.endswith("exec_spec_structured.bridge")
    )
    report["python"] = sys.version.split()[0]
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main(sys.argv))
