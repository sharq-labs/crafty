"""Strict, campaign-bound statistical analysis for V0.3.5.

V0.3.4 analysis remains frozen for reproducibility.  This module validates
V0.3.5 artifacts before delegating the registered function-clustered
statistical analysis to the V0.3.4 implementation with the V0.3.5 adaptive
scientific identifier substituted at runtime.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from numbers import Integral, Real
from pathlib import Path


EXPECTED_ARMS = {
    "stacked_v0301",
    "stacked_fresh_weights_v034",
    "adaptive_stacked_v035",
}

_PID_RE = re.compile(r"bbob_f(\d+)_i(\d+)_d(\d+)")


def _reject_json_constant(token: str):
    raise ValueError(f"non-standard JSON constant {token!r} is not allowed")


def _strict_json_loads(text: str, *, context: str = "JSON"):
    """Parse JSON while rejecting NaN / Infinity extensions."""

    try:
        return json.loads(text, parse_constant=_reject_json_constant)
    except (TypeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid strict JSON in {context}: {exc}") from exc


def _strict_json_value(value):
    """Recursively convert non-finite real numbers to JSON ``null``.

    ``numbers.Real`` covers ordinary floats plus NumPy scalar real values
    without importing NumPy into the artifact layer. Integral values are kept
    as integers and booleans retain their JSON boolean semantics.
    """

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, dict):
        return {str(k): _strict_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_strict_json_value(v) for v in value]
    return value


def strict_json_dumps(value, **kwargs) -> str:
    """Serialize standards-compliant JSON only."""

    clean = _strict_json_value(value)
    kwargs.pop("allow_nan", None)
    return json.dumps(clean, allow_nan=False, **kwargs)


def _read_manifest(path: Path) -> dict:
    if not path.exists():
        raise ValueError(f"V0.3.5 manifest is missing: {path}")
    manifest = _strict_json_loads(
        path.read_text(encoding="utf-8"), context=str(path)
    )
    if not isinstance(manifest, dict):
        raise ValueError("V0.3.5 manifest must be a JSON object")
    return manifest


def _parse_problem_id(problem_id: str) -> tuple[int, int, int]:
    match = _PID_RE.search(str(problem_id))
    if match is None:
        raise ValueError(
            f"cannot validate problem_id {problem_id!r}; expected BBOB "
            "identifier containing bbob_f<fn>_i<instance>_d<dim>"
        )
    return tuple(int(v) for v in match.groups())


def _iter_journal(path: Path):
    last_line_no = 0
    for line_no, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        last_line_no = line_no
        rec = _strict_json_loads(line, context=f"{path}:{line_no}")
        if not isinstance(rec, dict):
            raise ValueError(f"journal line {line_no} is not a JSON object")
        yield line_no, rec
    if last_line_no == 0:
        raise ValueError("journal is empty")


def validate_journal_uniqueness(path) -> None:
    """Reject duplicate run records and multiple completion records.

    This low-level check intentionally does not require a manifest so it can be
    used in focused unit tests. Full scientific analysis uses
    :func:`validate_campaign_integrity` below.
    """

    path = Path(path)
    seen: set[tuple[str, str]] = set()
    completion_count = 0

    for line_no, rec in _iter_journal(path):
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


def validate_campaign_integrity(
    journal_path,
    manifest_path=None,
) -> dict:
    """Validate that one journal belongs to exactly one V0.3.5 campaign.

    Every record is bound to the manifest's campaign id. The validator checks
    configured problem membership, seed and budget formulas, exact evaluation
    counts, a complete rectangular arm matrix (or explicit failures), one final
    completion record, and per-arm accounting. This rejects concatenated,
    cropped, or scientifically mixed campaign journals before inference.
    """

    journal_path = Path(journal_path)
    manifest_path = (
        Path(manifest_path)
        if manifest_path is not None
        else journal_path.parent / "manifest.json"
    )
    manifest = _read_manifest(manifest_path)

    if manifest.get("kind") != "v035_ablation_manifest":
        raise ValueError("manifest kind is not v035_ablation_manifest")
    if manifest.get("schema") != "ablation-manifest/2":
        raise ValueError("unsupported V0.3.5 manifest schema")

    campaign_id = str(manifest.get("campaign_id") or "")
    if not campaign_id:
        raise ValueError("manifest campaign_id is missing")

    config = manifest.get("config")
    if not isinstance(config, dict):
        raise ValueError("manifest config is missing")

    arms = manifest.get("arms")
    if not isinstance(arms, dict):
        raise ValueError("manifest arms are missing")
    manifest_arms = {str(v) for v in arms.values()}
    if manifest_arms != EXPECTED_ARMS:
        raise ValueError(
            f"unexpected V0.3.5 arm set: {sorted(manifest_arms)}"
        )

    functions = {int(v) for v in config.get("functions", [])}
    dimensions = {int(v) for v in config.get("dimensions", [])}
    instances = {int(v) for v in config.get("instances", [])}
    if not functions or not dimensions or not instances:
        raise ValueError("manifest functions/dimensions/instances are incomplete")

    budget_multiplier = int(config.get("budget_multiplier", 0))
    base_seed = int(config.get("base_seed", 0))
    if budget_multiplier <= 0:
        raise ValueError("manifest budget_multiplier must be positive")

    expected_cases = len(functions) * len(dimensions) * len(instances)
    expected_runs = expected_cases * len(EXPECTED_ARMS)
    if int(manifest.get("expected_cases", -1)) != expected_cases:
        raise ValueError("manifest expected_cases is inconsistent with config")
    if int(manifest.get("expected_runs", -1)) != expected_runs:
        raise ValueError("manifest expected_runs is inconsistent with config")

    seen: set[tuple[str, str]] = set()
    run_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    failure_problem_ids: set[str] = set()
    run_arms_by_problem: dict[str, set[str]] = defaultdict(set)
    failure_arms_by_problem: dict[str, set[str]] = defaultdict(set)
    observed_case_ids: dict[tuple[int, int, int], str] = {}
    completions: list[tuple[int, dict]] = []
    last_record_line = 0
    run_records = 0

    def validate_problem_record(rec: dict, *, line_no: int) -> tuple[int, int, int]:
        problem_id = str(rec.get("problem_id") or "")
        fn, inst, dim_from_id = _parse_problem_id(problem_id)
        case_key = (fn, inst, dim_from_id)
        if fn not in functions or inst not in instances or dim_from_id not in dimensions:
            raise ValueError(
                f"journal line {line_no} problem {problem_id!r} is outside "
                "the manifest campaign configuration"
            )
        previous_id = observed_case_ids.get(case_key)
        if previous_id is not None and previous_id != problem_id:
            raise ValueError(
                f"journal line {line_no} aliases campaign case {case_key} "
                f"with two problem ids: {previous_id!r}, {problem_id!r}"
            )
        observed_case_ids[case_key] = problem_id
        if "dimension" in rec and int(rec["dimension"]) != dim_from_id:
            raise ValueError(
                f"journal line {line_no} dimension disagrees with problem_id"
            )
        return case_key

    for line_no, rec in _iter_journal(journal_path):
        last_record_line = line_no
        kind = rec.get("kind")
        if str(rec.get("campaign_id") or "") != campaign_id:
            raise ValueError(
                f"journal line {line_no} campaign_id does not match manifest"
            )

        if kind == "run":
            run_records += 1
            algorithm = str(rec.get("algorithm") or "")
            if algorithm not in EXPECTED_ARMS:
                raise ValueError(
                    f"journal line {line_no} has unexpected algorithm {algorithm!r}"
                )

            problem_id = str(rec.get("problem_id") or "")
            key = (problem_id, algorithm)
            if key in seen:
                raise ValueError(
                    "duplicate scientific run record at line "
                    f"{line_no}: problem_id={problem_id!r}, algorithm={algorithm!r}"
                )
            seen.add(key)
            run_arms_by_problem[problem_id].add(algorithm)

            fn, inst, dim = validate_problem_record(rec, line_no=line_no)
            required = ("dimension", "budget", "seed", "evaluations")
            missing = [name for name in required if name not in rec]
            if missing:
                raise ValueError(
                    f"journal line {line_no} missing run fields: {missing}"
                )

            budget = int(rec["budget"])
            seed = int(rec["seed"])
            evaluations = int(rec["evaluations"])
            expected_budget = budget_multiplier * dim
            expected_seed = base_seed + 10000 * inst + 100 * fn + dim

            if budget != expected_budget:
                raise ValueError(
                    f"journal line {line_no} budget {budget} != expected "
                    f"{expected_budget}"
                )
            if seed != expected_seed:
                raise ValueError(
                    f"journal line {line_no} seed {seed} != expected {expected_seed}"
                )
            if evaluations != budget:
                raise ValueError(
                    f"journal line {line_no} violates exact budget: "
                    f"evaluations={evaluations}, budget={budget}"
                )
            run_counts[algorithm] += 1

        elif kind == "failure":
            validate_problem_record(rec, line_no=line_no)
            problem_id = str(rec.get("problem_id"))
            arm = str(rec.get("arm") or "")
            if arm != "_setup" and arm not in EXPECTED_ARMS:
                raise ValueError(
                    f"journal line {line_no} has unexpected failure arm {arm!r}"
                )
            failure_problem_ids.add(problem_id)
            failure_arms_by_problem[problem_id].add(arm)
            if arm in EXPECTED_ARMS:
                failure_counts[arm] += 1

        elif kind == "campaign_complete":
            completions.append((line_no, rec))
        else:
            raise ValueError(
                f"journal line {line_no} has unknown record kind {kind!r}"
            )

    if len(observed_case_ids) != expected_cases:
        raise ValueError(
            f"journal covers {len(observed_case_ids)} campaign cases, "
            f"expected {expected_cases}"
        )

    for problem_id in observed_case_ids.values():
        run_arms = run_arms_by_problem.get(problem_id, set())
        failure_arms = failure_arms_by_problem.get(problem_id, set())
        if "_setup" in failure_arms:
            if run_arms or (failure_arms - {"_setup"}):
                raise ValueError(
                    f"setup-failed problem {problem_id} also contains arm records"
                )
            continue

        attempted_arms = run_arms | failure_arms
        if attempted_arms != EXPECTED_ARMS:
            missing = sorted(EXPECTED_ARMS - attempted_arms)
            extra = sorted(attempted_arms - EXPECTED_ARMS)
            raise ValueError(
                f"problem {problem_id} has incomplete arm accounting: "
                f"missing={missing}, extra={extra}"
            )
        if run_arms & failure_arms:
            overlap = sorted(run_arms & failure_arms)
            raise ValueError(
                f"problem {problem_id} records both run and failure for {overlap}"
            )

    if len(completions) != 1:
        raise ValueError(
            "V0.3.5 journal must contain exactly one campaign_complete record"
        )
    completion_line, completion = completions[0]
    if completion_line != last_record_line:
        raise ValueError("campaign_complete must be the final journal record")

    if int(completion.get("completed_runs", -1)) != run_records:
        raise ValueError("campaign_complete completed_runs does not match journal")

    matched_runs = sum(
        1 for problem_id, _algorithm in seen
        if problem_id not in failure_problem_ids
    )
    if int(completion.get("matched_runs", -1)) != matched_runs:
        raise ValueError("campaign_complete matched_runs does not match journal")

    completion_failed = completion.get("failed_cases", {})
    if not isinstance(completion_failed, dict):
        raise ValueError("campaign_complete failed_cases must be an object")
    if set(map(str, completion_failed.keys())) != failure_problem_ids:
        raise ValueError("campaign_complete failed_cases does not match failures")

    accounting = completion.get("per_arm_accounting")
    if not isinstance(accounting, dict) or set(accounting) != EXPECTED_ARMS:
        raise ValueError("campaign_complete per_arm_accounting arm set is invalid")

    for arm in EXPECTED_ARMS:
        row = accounting[arm]
        if not isinstance(row, dict):
            raise ValueError(f"per-arm accounting for {arm} is invalid")
        completed = int(row.get("completed", -1))
        failed = int(row.get("failed", -1))
        attempted = int(row.get("attempted", -1))
        if completed != run_counts[arm]:
            raise ValueError(f"per-arm completed count mismatch for {arm}")
        if failed != failure_counts[arm]:
            raise ValueError(f"per-arm failed count mismatch for {arm}")
        if attempted != completed + failed:
            raise ValueError(f"per-arm attempted count mismatch for {arm}")

    return {
        "campaign_id": campaign_id,
        "manifest": manifest,
        "run_records": run_records,
        "failure_problem_ids": sorted(failure_problem_ids),
        "completion": completion,
    }


def analyze(journal_path):
    integrity = validate_campaign_integrity(journal_path)

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
    report["campaign_id"] = integrity["campaign_id"]
    report["hardening"] = {
        "duplicate_run_records": "rejected",
        "mixed_campaign_records": "rejected",
        "campaign_manifest_binding": "required",
        "complete_arm_matrix_or_explicit_failure": "required",
        "completion_record": "exactly_one_and_final",
        "adaptive_arm": "adaptive_stacked_v035",
        "json_nonfinite_values": "serialized_as_null",
    }
    return report


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
        strict_json_dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"V0.3.5 analysis written: {out}")


if __name__ == "__main__":
    main()
