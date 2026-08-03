"""V0.3.4 ablation APPARATUS self-test.

Tests the experiment apparatus (arena persistence, manifest, failure
tolerance, per-arm accounting) and the registered analysis module
(v034_ablation_analysis) — NOT optimizer performance.

Style follows the existing selftest convention (plain [PASS]/[FAIL],
exit code). Run from the repository root:

    .venv/Scripts/python.exe -m src.engcore.v034_apparatus_selftest

The two apparatus tests execute real tiny engine runs (budget 10, D=2,
scipy/cpu) and take roughly a minute on CPU.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _require(cond, message):
    if not cond:
        raise AssertionError(message)


def _read_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


ARENA_ARGS = [
    "--functions", "1", "--dimensions", "2", "--instances", "71",
    "--budget-multiplier", "5", "--seed", "123",
    "--stacked-mode", "fast", "--screen-device", "cpu",
    "--stacked-refinement-backend", "scipy", "--coco-observer", "off",
]

ARMS = [
    "stacked_v0301",
    "stacked_fresh_weights_v034",
    "adaptive_stacked_v034",
]


def test_apparatus_happy_path(out_dir):
    r = subprocess.run(
        [sys.executable, "-m", "src.engcore.v034_ablation_arena",
         *ARENA_ARGS, "--out", str(out_dir)],
        capture_output=True, text=True, timeout=900,
    )
    _require(r.returncode == 0, f"arena exited {r.returncode}: "
                                f"{r.stderr[-400:]}")

    manifest = json.loads(
        (out_dir / "manifest.json").read_text(encoding="utf-8")
    )
    for field in ("created_utc", "argv", "config", "arms",
                  "expected_cases", "expected_runs", "git",
                  "environment"):
        _require(field in manifest, f"manifest missing {field}")
    _require(len(manifest["git"].get("commit", "")) == 40,
             "manifest git commit not recorded")
    _require(manifest["config"]["refinement_backend"] == "scipy",
             "manifest backend wrong")
    _require("threading" in manifest["environment"],
             "manifest missing threading environment")
    _require(manifest["expected_runs"] == 3, "expected_runs != 3")

    lines = _read_jsonl(out_dir / "progress.jsonl")
    runs = [l for l in lines if l.get("kind") == "run"]
    complete = [l for l in lines if l.get("kind") == "campaign_complete"]
    _require(len(runs) == 3, f"expected 3 run lines, got {len(runs)}")
    _require(len(complete) == 1, "missing completion record")
    _require(complete[0]["matched_runs"] == 3, "matched_runs != 3")
    _require(complete[0]["failed_cases"] == {}, "unexpected failures")
    _require(sorted(l["algorithm"] for l in runs) == sorted(ARMS),
             "not all three arms journaled")
    _require(all(l["evaluations"] == 10 for l in runs),
             "budget not exact in journal")
    _require(
        all(len(l.get("best_curve", [])) == l["evaluations"]
            for l in runs),
        "convergence curve not persisted per run",
    )
    _require(
        all("refinement_s_total" in l["metadata"]
            and "refinement_attempts" in l["metadata"]
            for l in runs),
        "refinement telemetry missing from run metadata",
    )
    acct = complete[0]["per_arm_accounting"]
    _require(
        all(acct[a]["attempted"] == 1 and acct[a]["completed"] == 1
            and acct[a]["failed"] == 0 for a in ARMS),
        f"per-arm accounting wrong: {acct}",
    )
    _require((out_dir / "runs.csv").exists(), "runs.csv missing")


def test_apparatus_failure_tolerance(out_dir):
    sys.path.insert(0, str(Path.cwd()))
    import src.engcore.v034_ablation_arena as arena

    def _boom(**kwargs):
        raise RuntimeError("injected apparatus-test failure")

    orig, argv_backup = arena.run_stacked_fresh_weights, sys.argv
    arena.run_stacked_fresh_weights = _boom
    sys.argv = ["v034_ablation_arena", *ARENA_ARGS, "--out", str(out_dir)]
    try:
        arena.main()  # must not raise despite the failing arm
    finally:
        arena.run_stacked_fresh_weights = orig
        sys.argv = argv_backup

    lines = _read_jsonl(out_dir / "progress.jsonl")
    runs = [l for l in lines if l.get("kind") == "run"]
    fails = [l for l in lines if l.get("kind") == "failure"]
    complete = [l for l in lines if l.get("kind") == "campaign_complete"]
    _require(len(fails) == 1
             and fails[0]["arm"] == "stacked_fresh_weights_v034",
             f"failure not journaled correctly: {fails}")
    _require(len(runs) == 2, "sibling arm runs not preserved")
    _require(len(complete[0]["failed_cases"]) == 1,
             "completion missing failed case")
    _require(complete[0]["matched_runs"] == 0,
             "failed case not excluded from matched set")
    acct = complete[0]["per_arm_accounting"]
    _require(acct["stacked_fresh_weights_v034"]["failed"] == 1
             and acct["stacked_fresh_weights_v034"]["attempted"] == 1,
             f"failed arm accounting wrong: {acct}")
    _require(acct["stacked_v0301"]["excluded_by_matching"] == 1,
             "sibling exclusion not accounted")
    _require(
        len(acct["stacked_fresh_weights_v034"]["failure_reasons"]) == 1,
        "failure reason not recorded",
    )


def _synthetic_journal(tmp, spec):
    """spec: list of (problem_id, {arm: best_f}) — missing arm = failure."""
    path = Path(tmp) / "progress.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        for pid, arms in spec:
            for arm in ARMS:
                if arm in arms:
                    fh.write(json.dumps({
                        "kind": "run", "problem_id": pid,
                        "algorithm": arm, "dimension": 2, "budget": 10,
                        "seed": 1, "evaluations": 10,
                        "best_f": arms[arm], "final_target": None,
                        "target_hit": False, "wall_s": 0.1,
                        "best_curve": [arms[arm]] * 10, "metadata": {},
                    }) + "\n")
                else:
                    fh.write(json.dumps({
                        "kind": "failure", "problem_id": pid,
                        "arm": arm, "error_type": "RuntimeError",
                        "error": "synthetic",
                    }) + "\n")
    return path


def test_analysis_primary_stats(tmp):
    from src.engcore.v034_ablation_analysis import analyze
    # 10 cases: B beats A on 8, loses 2 (no ties); C ties B everywhere.
    spec = []
    for i in range(10):
        a = 100.0
        b = 90.0 if i < 8 else 110.0
        spec.append((f"p{i:02d}", {ARMS[0]: a, ARMS[1]: b, ARMS[2]: b}))
    report = analyze(_synthetic_journal(tmp, spec))
    ba = report["primary_matched_paired"]["B_vs_A"]
    _require(ba["wins"] == 8 and ba["losses"] == 2 and ba["ties"] == 0,
             f"B_vs_A W/L/T wrong: {ba}")
    # exact two-sided sign test, 8/10: p = 2 * P(X>=8) = 0.109375
    _require(abs(ba["p_value"] - 0.109375) < 1e-9,
             f"sign-test p wrong: {ba['p_value']}")
    _require(ba["ci_low"] < 0.5 < ba["ci_high"],
             "CI should cross 0.5 at 8/10 with 97.5% CI")
    _require(ba["verdict"].startswith("INCONCLUSIVE"),
             f"verdict wrong: {ba['verdict']}")
    cb = report["primary_matched_paired"]["C_vs_B"]
    _require(cb["ties"] == 10 and cb["n_nonties"] == 0,
             f"C_vs_B should be all ties: {cb}")
    _require(cb["verdict"].startswith("INCONCLUSIVE"), "all-tie verdict")


def test_analysis_decisive_and_holm(tmp):
    from src.engcore.v034_ablation_analysis import analyze
    # 20 cases: B beats A on 19/20 (decisive); C beats B on 15/20.
    spec = []
    for i in range(20):
        a = 100.0
        b = 90.0 if i != 0 else 110.0
        c = b - 1.0 if i < 15 else b + 1.0
        spec.append((f"p{i:02d}", {ARMS[0]: a, ARMS[1]: b, ARMS[2]: c}))
    report = analyze(_synthetic_journal(tmp, spec))
    ba = report["primary_matched_paired"]["B_vs_A"]
    cb = report["primary_matched_paired"]["C_vs_B"]
    _require(ba["verdict"] == "POSITIVE evidence",
             f"19/20 should be positive: {ba}")
    _require(ba["ci_low"] > 0.5, "decisive CI should clear 0.5")
    # Holm: smaller p doubled; larger p max(smaller*2, p2*1)
    _require(ba["p_value_holm"] >= ba["p_value"], "holm must not shrink p")
    _require(cb["p_value_holm"] >= cb["p_value"], "holm must not shrink p")
    _require(ba["p_value_holm"] <= 1.0 and cb["p_value_holm"] <= 1.0,
             "holm p out of range")


def test_analysis_robustness_failure_as_loss(tmp):
    from src.engcore.v034_ablation_analysis import analyze
    # 4 cases; B fails on the last one. Matched = 3, attempted = 4.
    spec = [
        ("p00", {ARMS[0]: 100.0, ARMS[1]: 90.0, ARMS[2]: 95.0}),
        ("p01", {ARMS[0]: 100.0, ARMS[1]: 90.0, ARMS[2]: 95.0}),
        ("p02", {ARMS[0]: 100.0, ARMS[1]: 110.0, ARMS[2]: 95.0}),
        ("p03", {ARMS[0]: 100.0, ARMS[2]: 95.0}),  # B failed here
    ]
    report = analyze(_synthetic_journal(tmp, spec))
    _require(report["matched_cases"] == 3, "matched should exclude p03")
    _require(report["attempted_cases"] == 4, "attempted should include p03")
    ba_m = report["primary_matched_paired"]["B_vs_A"]
    _require(ba_m["wins"] == 2 and ba_m["losses"] == 1,
             f"matched B_vs_A wrong: {ba_m}")
    ba_r = report["secondary_all_case_robustness"]["B_vs_A"]
    _require(ba_r["wins"] == 2 and ba_r["losses"] == 2,
             f"robustness must count B's failure as a loss: {ba_r}")
    _require(report["failed_cases"] == ["p03"], "failed case list wrong")


def main():
    print("V0.3.4 Apparatus Self-Test")
    print("=" * 72)
    failures = 0
    tests = []

    tmp_root = Path(tempfile.mkdtemp(prefix="v034_apparatus_"))
    happy = tmp_root / "happy"
    broken = tmp_root / "broken"
    tests.append(("apparatus happy path (real tiny 3-arm run)",
                  lambda: test_apparatus_happy_path(happy)))
    tests.append(("apparatus failure tolerance (injected arm failure)",
                  lambda: test_apparatus_failure_tolerance(broken)))
    tests.append(("analysis primary stats (exact sign test, CI)",
                  lambda: test_analysis_primary_stats(tmp_root / "a1")))
    tests.append(("analysis decisive verdict + Holm",
                  lambda: test_analysis_decisive_and_holm(tmp_root / "a2")))
    tests.append(("analysis robustness: failure counts as loss",
                  lambda: test_analysis_robustness_failure_as_loss(
                      tmp_root / "a3")))

    for name, fn in tests:
        try:
            (Path(tmp_root) / "a1").mkdir(exist_ok=True)
            (Path(tmp_root) / "a2").mkdir(exist_ok=True)
            (Path(tmp_root) / "a3").mkdir(exist_ok=True)
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {name}: {exc}")

    shutil.rmtree(tmp_root, ignore_errors=True)
    print("=" * 72)
    if failures:
        print(f"V0.3.4 apparatus self-test: FAIL ({failures})")
        return 1
    print("V0.3.4 apparatus self-test: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
