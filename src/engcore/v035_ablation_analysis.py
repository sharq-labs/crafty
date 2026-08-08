"""Duplicate-safe statistical analysis for V0.3.5 campaigns.

V0.3.4 analysis is preserved for reproducibility. This wrapper validates the
journal before delegating to the registered clustered analysis logic, using the
V0.3.5 adaptive arm identifier.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def validate_journal_uniqueness(path) -> None:
    """Reject duplicate scientific run records instead of last-write-wins."""

    seen: set[tuple[str, str]] = set()
    completion_count = 0

    for line_no, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        rec = json.loads(line)
        kind = rec.get("kind")

        if kind == "run":
            key = (str(rec.get("problem_id")), str(rec.get("algorithm")))
            if key in seen:
                raise ValueError(
                    "duplicate scientific run record at line "
                    f"{line_no}: problem_id={key[0]!r}, algorithm={key[1]!r}"
                )
            seen.add(key)
        elif kind == "campaign_complete":
            completion_count += 1

    if completion_count > 1:
        raise ValueError(
            "journal contains multiple campaign_complete records; "
            "refusing to analyze a mixed/appended campaign"
        )


def analyze(journal_path):
    validate_journal_uniqueness(journal_path)

    from . import v034_ablation_analysis as legacy

    original_c = legacy.ARM_C
    original_contrasts = legacy.CONTRASTS
    legacy.ARM_C = "adaptive_stacked_v035"
    legacy.CONTRASTS = (
        ("B_vs_A", legacy.ARM_B, legacy.ARM_A),
        ("C_vs_B", legacy.ARM_C, legacy.ARM_B),
    )
    try:
        report = legacy.analyze(journal_path)
    finally:
        legacy.ARM_C = original_c
        legacy.CONTRASTS = original_contrasts

    report["kind"] = "v035_ablation_analysis"
    report["schema"] = "ablation-analysis/3"
    report["hardening"] = {
        "duplicate_run_records": "rejected",
        "multiple_completion_records": "rejected",
        "adaptive_arm": "adaptive_stacked_v035",
        "json_nonfinite_values": "serialized_as_null",
    }
    return report


def _strict_json_value(value):
    """Recursively replace non-finite floats with JSON ``null`` values."""

    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _strict_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_strict_json_value(v) for v in value]
    if isinstance(value, tuple):
        return [_strict_json_value(v) for v in value]
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--journal", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    report = _strict_json_value(analyze(args.journal))
    out = Path(args.out) if args.out else (
        Path(args.journal).parent / "ablation_analysis_v035.json"
    )
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(f"V0.3.5 analysis written: {out}")


if __name__ == "__main__":
    main()
