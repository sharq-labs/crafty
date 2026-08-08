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
    _require(
        all("refinement_s_max" in l["metadata"]
            for l in runs
            if l["metadata"].get("refinement_attempts", 0) > 0),
        "refinement_s_max missing despite refinement attempts",
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


def _pid(fn, inst):
    return f"bbob_f{fn:03d}_i{inst:02d}_d02"


def _fn_spec(fn, b_deltas, c_delta=0.0):
    """One function, five instances; b_deltas[i] applied to arm B
    relative to A=100 (negative = B wins under minimization)."""
    rows = []
    for inst, d in enumerate(b_deltas, start=1):
        b = 100.0 + d
        rows.append((_pid(fn, inst),
                     {ARMS[0]: 100.0, ARMS[1]: b, ARMS[2]: b + c_delta}))
    return rows


def test_clustered_directions(tmp):
    """Required scenarios: unanimous 5-0, 3-2 majority, 2-2+tie, all
    ties — with correct sign-test sample size."""
    from src.engcore.v034_ablation_analysis import analyze
    spec = []
    spec += _fn_spec(1, [-1, -1, -1, -1, -1])       # 5-0  -> POSITIVE
    spec += _fn_spec(2, [-1, -1, -1, +1, +1])       # 3-2  -> POSITIVE
    spec += _fn_spec(3, [-1, -1, +1, +1, 0])        # 2-2+tie -> TIE
    spec += _fn_spec(4, [0, 0, 0, 0, 0])            # all tied -> ALL_TIED
    spec += _fn_spec(5, [+1, +1, +1, -1, -1])       # 2-3  -> NEGATIVE
    report = analyze(_synthetic_journal(tmp, spec))
    ba = report["primary_function_clustered"]["B_vs_A"]
    dirs = {e["function"]: e["direction"] for e in ba["per_function"]}
    _require(dirs == {1: "POSITIVE", 2: "POSITIVE", 3: "TIE",
                      4: "ALL_TIED", 5: "NEGATIVE"},
             f"directions wrong: {dirs}")
    scores = {e["function"]: e["function_score"]
              for e in ba["per_function"]}
    _require(scores[2] == 0.2 and scores[3] == 0.0
             and scores[4] is None and scores[5] == -0.2,
             f"function scores wrong: {scores}")
    _require(ba["positive_functions"] == 2
             and ba["negative_functions"] == 1
             and ba["tied_functions"] == 1
             and ba["all_tied_functions"] == 1,
             f"direction counts wrong: {ba}")
    # sign-test sample = non-tied FUNCTIONS only: n = 2 + 1 = 3
    _require(ba["n_nonties"] == 3,
             f"sign-test n must be 3 non-tied functions: {ba['n_nonties']}")
    # two-sided sign test, 2 of 3: p = 1.0
    _require(abs(ba["p_value"] - 1.0) < 1e-12,
             f"p wrong for 2/3: {ba['p_value']}")
    _require(ba["verdict"].startswith("INCONCLUSIVE"), ba["verdict"])


def test_clustered_decisive_and_holm(tmp):
    from src.engcore.v034_ablation_analysis import analyze
    # 12 functions, B wins all 5 instances of each (decisive);
    # C beats B on 4 of 5 instances of 8 functions, loses all of 4.
    spec = []
    for fn in range(1, 13):
        c_rows = _fn_spec(fn, [-1] * 5,
                          c_delta=(-0.5 if fn <= 8 else +0.5))
        spec += c_rows
    report = analyze(_synthetic_journal(tmp, spec))
    ba = report["primary_function_clustered"]["B_vs_A"]
    cb = report["primary_function_clustered"]["C_vs_B"]
    _require(ba["positive_functions"] == 12 and ba["n_nonties"] == 12,
             f"B_vs_A cluster counts wrong: {ba}")
    # 12/12: p = 2 * 0.5^12 = 0.00048828125
    _require(abs(ba["p_value"] - 2 * 0.5 ** 12) < 1e-12,
             f"decisive p wrong: {ba['p_value']}")
    _require(ba["ci_low"] > 0.5, "decisive CI should clear 0.5")
    _require(ba["verdict"] == "POSITIVE evidence", ba["verdict"])
    _require(cb["positive_functions"] == 8
             and cb["negative_functions"] == 4,
             f"C_vs_B clusters wrong: {cb}")
    # Holm on two p-values: smaller doubled, larger = max(2*smaller, larger)
    p_small, p_large = sorted([ba["p_value"], cb["p_value"]])
    holms = sorted([ba["p_value_holm"], cb["p_value_holm"]])
    _require(abs(holms[0] - min(1.0, 2 * p_small)) < 1e-12,
             f"holm smaller wrong: {holms[0]}")
    _require(abs(holms[1] - max(min(1.0, 2 * p_small),
                                min(1.0, p_large))) < 1e-12,
             f"holm larger wrong: {holms[1]}")


def test_analysis_robustness_failure_as_loss(tmp):
    from src.engcore.v034_ablation_analysis import analyze
    # Function 1: B fails on instance 5; matched excludes that case,
    # robustness counts it as a loss for B.
    spec = _fn_spec(1, [-1, -1, -1, +1])            # 4 complete cases
    spec.append((_pid(1, 5), {ARMS[0]: 100.0, ARMS[2]: 95.0}))  # B failed
    report = analyze(_synthetic_journal(tmp, spec))
    _require(report["matched_cases"] == 4, "matched should exclude i05")
    _require(report["attempted_cases"] == 5, "attempted should include i05")
    ba_d = report["secondary_case_level_descriptive"]["B_vs_A"]
    _require(ba_d["wins"] == 3 and ba_d["losses"] == 1,
             f"case-level descriptive wrong: {ba_d}")
    ba_r = report["secondary_all_case_robustness"]["B_vs_A"]
    _require(ba_r["wins"] == 3 and ba_r["losses"] == 2,
             f"robustness must count B's failure as a loss: {ba_r}")
    _require("not independent" in
             report["secondary_case_level_descriptive"]["note"],
             "case-level results must carry the non-independence label")
    _require(report["failed_cases"] == [_pid(1, 5)],
             "failed case list wrong")


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
    tests.append(("clustered directions (5-0, 3-2, 2-2+tie, all-tied, "
                  "sign-test n)",
                  lambda: test_clustered_directions(tmp_root / "a1")))
    tests.append(("clustered decisive verdict + Holm",
                  lambda: test_clustered_decisive_and_holm(
                      tmp_root / "a2")))
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
