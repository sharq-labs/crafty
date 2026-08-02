from __future__ import annotations

import importlib
import platform
import sys


def probe(module):
    try:
        mod = importlib.import_module(
            module
        )
        version = getattr(
            mod,
            "__version__",
            "unknown",
        )
        return True, str(version)
    except Exception as exc:
        return False, str(exc)


def main():
    checks = [
        ("numpy", True),
        ("scipy", True),
        ("torch", True),
        ("botorch", True),
        ("gpytorch", True),
        ("cocoex", False),
        ("nevergrad", False),
        ("cma", False),
    ]

    print("=" * 92)
    print(
        "Engineering AI Core V0.3.2.6 — Validation Environment Doctor"
    )
    print("=" * 92)
    print(
        f"Python   : {sys.version.split()[0]}"
    )
    print(
        f"Platform : {platform.platform()}"
    )
    print("")

    missing_required = []

    for module, required in checks:
        ok, info = probe(module)
        status = "OK" if ok else (
            "MISSING"
            if required
            else "OPTIONAL"
        )

        print(
            f"{module:12s}: "
            f"{status:8s} "
            f"{info}"
        )

        if required and not ok:
            missing_required.append(
                module
            )

    print("")
    print(
        "Core arena always available: "
        "random, sobol, de, stacked"
    )
    print(
        "Optional baselines: "
        "ngopt (nevergrad), cmaes (cma)"
    )
    print(
        "Official BBOB suite: "
        "requires cocoex"
    )
    print("=" * 92)

    if missing_required:
        raise SystemExit(
            "Missing required modules: "
            + ", ".join(
                missing_required
            )
        )


if __name__ == "__main__":
    main()
