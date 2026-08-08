"""Guarded V0.3.5 ablation entry point.

The registered V0.3.4 arena is preserved byte-for-byte. This wrapper reuses its
apparatus while applying two future-run protections:

- use ``adaptive_stacked_v035`` for the adaptive arm;
- refuse to run into a non-empty output directory, preventing accidental
  append/overwrite corruption of ``progress.jsonl`` and ``manifest.json``.

A true resume mechanism can be added later; until then fail-fast is safer than
silently mixing campaigns.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .adaptive_stacked_engine_v035 import AdaptiveStackedGPBOEngineV035


def _requested_out(argv: list[str]) -> Path:
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            raise SystemExit("--out requires a directory")
        return Path(argv[i + 1])
    return Path("validation_results/v035_ablation_smoke")


def _guard_empty_output(out_dir: Path) -> None:
    if not out_dir.exists():
        return
    if not out_dir.is_dir():
        raise SystemExit(f"Refusing campaign: --out is not a directory: {out_dir}")
    if any(out_dir.iterdir()):
        raise SystemExit(
            "Refusing campaign: output directory is not empty. "
            "Use a new --out directory; V0.3.5 does not silently append or "
            "overwrite scientific campaign state."
        )


def run_adaptive_stacked_v035(*args, **kwargs):
    """Reuse the validated adapter while substituting the V0.3.5 engine."""

    from . import adaptive_stacked_engine as legacy_module
    from .validation.optimizers import run_adaptive_stacked

    original = legacy_module.AdaptiveStackedGPBOEngine
    legacy_module.AdaptiveStackedGPBOEngine = AdaptiveStackedGPBOEngineV035
    try:
        trace = run_adaptive_stacked(*args, **kwargs)
    finally:
        legacy_module.AdaptiveStackedGPBOEngine = original

    trace.algorithm = "adaptive_stacked_v035"
    trace.metadata = dict(trace.metadata or {})
    trace.metadata["engine_id"] = "adaptive_stacked_v035"
    trace.metadata["review_hardening"] = {
        "exploration_starts_refinement_visible": True,
        "adaptive_generation_failure_fallback": "identity",
    }
    return trace


def main() -> None:
    argv = list(sys.argv[1:])
    out_dir = _requested_out(argv)
    _guard_empty_output(out_dir)

    # Make the default output V0.3.5-specific when the caller did not supply it.
    if "--out" not in argv:
        sys.argv.extend(["--out", str(out_dir)])

    from . import v034_ablation_arena as arena

    original_runner = arena.run_adaptive_stacked
    original_id = arena.SCIENTIFIC_IDS["adaptive_stacked"]
    arena.run_adaptive_stacked = run_adaptive_stacked_v035
    arena.SCIENTIFIC_IDS["adaptive_stacked"] = "adaptive_stacked_v035"
    try:
        arena.main()
    finally:
        arena.run_adaptive_stacked = original_runner
        arena.SCIENTIFIC_IDS["adaptive_stacked"] = original_id


if __name__ == "__main__":
    main()
