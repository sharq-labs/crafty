"""Dual-golden baseline parity: full-trajectory comparison across two trees.

Runs stacked_v0301 under the registered ablation configuration
(scipy refinement / cpu screening / fast mode) in TWO repository trees
(e.g. main and the research branch) as separate subprocesses, recording
EVERY evaluation (the exact x vector and returned f) — not just final
objective values — and compares the trajectories bit-exactly.

Optionally repeats the run in tree B to verify same-machine determinism at
full-trajectory resolution.

Usage (from the branch tree root, sequential by design — parallel runs
would perturb the wall-clock refinement timeout this harness helps audit):

    .venv/Scripts/python.exe -m src.engcore.v034_golden_parity \
        --tree-a <path-to-main-tree> --tree-b <path-to-branch-tree> \
        --functions all --instance 1 --budget 40 --repeat-b \
        --out validation_results/golden_parity_d2_i1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# Child program executed with cwd = target tree root. Self-contained:
# imports the target tree's own adapter and records every evaluation.
_CHILD = r"""
import json, sys
import numpy as np
sys.path.insert(0, ".")
from src.engcore.validation.coco_bbob import (
    _get_problem, _import_coco, _resolve_bbob_final_target,
)

fn, inst, budget, seed, out, arm, obs_dir = (
    int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]),
    int(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7],
)
if arm == "stacked":
    from src.engcore.validation.optimizers import run_stacked as runner
    sci_id = "stacked_v0301"
elif arm == "fresh_weights":
    from src.engcore.v034_ablation_arena import (
        run_stacked_fresh_weights as runner,
    )
    sci_id = "stacked_fresh_weights_v034"
elif arm == "adaptive":
    from src.engcore.validation.optimizers import (
        run_adaptive_stacked as runner,
    )
    sci_id = "adaptive_stacked_v034"
else:
    raise SystemExit(f"unknown arm {arm}")

cocoex = _import_coco()
observer = None
if obs_dir != "off":
    from src.engcore.validation.coco_bbob import create_bbob_observer
    observer, _folder = create_bbob_observer(
        cocoex, requested_folder=obs_dir, algorithm_name=sci_id,
        algorithm_info=f"golden-parity replay; arm={arm}",
    )
suite, prob = _get_problem(cocoex, fn, 2, inst)
try:
    if observer is not None:
        prob.observe_with(observer)
    pid = str(prob.id)
    lower = np.asarray(prob.lower_bounds, dtype=np.float64).copy()
    upper = np.asarray(prob.upper_bounds, dtype=np.float64).copy()
    ft, _src = _resolve_bbob_final_target(prob)
    evals = []
    def func(x, _p=prob):
        v = float(_p(x))
        evals.append(
            {"x": [float(c) for c in np.asarray(x).reshape(-1)], "f": v}
        )
        return v
    tr = runner(
        problem_id=pid, func=func, lower=lower, upper=upper,
        budget=budget, seed=seed, final_target=ft,
        mode="fast", screen_device="cpu", refinement_backend="scipy",
    )
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "problem_id": pid, "seed": seed, "budget": budget,
            "best_f": tr.best_f, "n_evals": len(evals), "evals": evals,
            "metadata": tr.metadata,
        }, fh)
finally:
    prob.free()
    suite.free()
"""

# Metadata keys excluded from deterministic comparison: pure wall-clock
# measurements legitimately differ between bit-identical runs.
_NONDETERMINISTIC_META_PREFIXES = ("refinement_s_", "wall")


def _run_child(python, tree, fn, instance, budget, seed, out_path,
               arm="stacked", obs_dir="off"):
    r = subprocess.run(
        [python, "-c", _CHILD, str(fn), str(instance), str(budget),
         str(seed), str(out_path), arm, str(obs_dir)],
        cwd=str(tree), capture_output=True, text=True, timeout=1800,
    )
    if r.returncode != 0:
        raise RuntimeError(
            f"child failed in {tree} for f{fn} arm={arm}: "
            f"{r.stderr[-500:]}"
        )
    return json.loads(Path(out_path).read_text(encoding="utf-8"))


def _compare(label, rec_a, rec_b, compare_metadata=False):
    """Exact comparison of full evaluation trajectories."""
    if rec_a["n_evals"] != rec_b["n_evals"]:
        return {"match": False, "detail":
                f"eval count {rec_a['n_evals']} != {rec_b['n_evals']}"}
    for i, (ea, eb) in enumerate(zip(rec_a["evals"], rec_b["evals"])):
        if ea["x"] != eb["x"] or ea["f"] != eb["f"]:
            return {
                "match": False,
                "detail": (
                    f"first divergence at evaluation {i}: "
                    f"x {ea['x']} vs {eb['x']}; f {ea['f']} vs {eb['f']}"
                ),
            }
    if rec_a["best_f"] != rec_b["best_f"]:
        return {"match": False,
                "detail": f"best_f {rec_a['best_f']} != {rec_b['best_f']}"}
    if compare_metadata:
        def _det(md):
            return {
                k: v for k, v in md.items()
                if not any(k.startswith(p)
                           for p in _NONDETERMINISTIC_META_PREFIXES)
            }
        ma, mb = _det(rec_a.get("metadata", {})), _det(
            rec_b.get("metadata", {}))
        if ma != mb:
            diff = {k: (ma.get(k), mb.get(k))
                    for k in set(ma) | set(mb) if ma.get(k) != mb.get(k)}
            return {"match": False,
                    "detail": f"deterministic metadata differs: {diff}"}
    return {"match": True, "detail": "bit-exact full trajectory"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tree-a", required=True, help="e.g. main tree root")
    p.add_argument("--tree-b", required=True, help="e.g. branch tree root")
    p.add_argument("--functions", default="all")
    p.add_argument("--instance", type=int, default=1)
    p.add_argument("--budget", type=int, default=40)
    p.add_argument("--base-seed", type=int, default=123)
    p.add_argument("--repeat-b", action="store_true",
                   help="run tree B twice for a determinism check")
    p.add_argument("--arm",
                   choices=["stacked", "fresh_weights", "adaptive"],
                   default="stacked")
    p.add_argument("--coco-observer", choices=["on", "off"],
                   default="off",
                   help="attach a real COCO observer to every child run "
                        "(matches the registered campaign's observer "
                        "configuration)")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    same_tree = (Path(args.tree_a).resolve()
                 == Path(args.tree_b).resolve())

    if args.functions.strip().lower() == "all":
        functions = list(range(1, 25))
    else:
        functions = [int(x) for x in args.functions.split(",") if x.strip()]

    # Absolute: children run with cwd set to the target tree, so a
    # relative --out would resolve against the wrong directory.
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable

    results = []
    all_ab, all_bb = True, True
    telemetry_max_mean = 0.0
    t0 = time.perf_counter()
    def _obs(tag):
        if args.coco_observer != "on":
            return "off"
        return str(out_dir / f"coco_{tag}")

    for fn in functions:
        seed = args.base_seed + 10000 * args.instance + 100 * fn + 2
        rec_a = _run_child(python, args.tree_a, fn, args.instance,
                           args.budget, seed,
                           out_dir / f"f{fn:02d}_a.json",
                           arm=args.arm, obs_dir=_obs("a"))
        rec_b = _run_child(python, args.tree_b, fn, args.instance,
                           args.budget, seed,
                           out_dir / f"f{fn:02d}_b.json",
                           arm=args.arm, obs_dir=_obs("b"))
        # Deterministic-metadata comparison only for same-tree replay:
        # cross-tree runs legitimately differ in metadata schema.
        cmp_ab = _compare("A-vs-B", rec_a, rec_b,
                          compare_metadata=same_tree)
        entry = {"function": fn, "seed": seed, "arm": args.arm,
                 "problem_id": rec_b["problem_id"],
                 "a_vs_b": cmp_ab}
        all_ab = all_ab and cmp_ab["match"]

        if args.repeat_b:
            rec_b2 = _run_child(python, args.tree_b, fn, args.instance,
                                args.budget, seed,
                                out_dir / f"f{fn:02d}_b2.json",
                                arm=args.arm, obs_dir=_obs("b2"))
            cmp_bb = _compare("B-vs-B2", rec_b, rec_b2,
                              compare_metadata=True)
            entry["b_repeat"] = cmp_bb
            all_bb = all_bb and cmp_bb["match"]

        md = rec_b.get("metadata", {})
        if "refinement_s_mean" in md:
            telemetry_max_mean = max(
                telemetry_max_mean, float(md["refinement_s_mean"])
            )
            entry["refinement_s_mean_b"] = md["refinement_s_mean"]
            entry["refinement_attempts_b"] = md.get("refinement_attempts")
        if "refinement_s_max" in md:
            entry["refinement_s_max_b"] = md["refinement_s_max"]

        results.append(entry)
        flag = "OK " if cmp_ab["match"] else "DIVERGED"
        rep = ""
        if args.repeat_b:
            rep = ("  repeat=OK" if entry["b_repeat"]["match"]
                   else "  repeat=DIVERGED")
        print(f"f{fn:02d}  {flag}{rep}  ({rec_b['problem_id']})")

    verdict = {
        "kind": "golden_parity_report",
        "schema": "golden-parity/1",
        "tree_a": str(args.tree_a),
        "tree_b": str(args.tree_b),
        "instance": args.instance,
        "budget": args.budget,
        "functions": functions,
        "config": {"mode": "fast", "screen_device": "cpu",
                   "refinement_backend": "scipy", "arm": args.arm,
                   "coco_observer": args.coco_observer},
        "a_vs_b_all_match": all_ab,
        "b_repeat_all_match": all_bb if args.repeat_b else None,
        "max_refinement_s_mean_tree_b": telemetry_max_mean,
        "wall_s_total": time.perf_counter() - t0,
        "cases": results,
    }
    (out_dir / "parity_report.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True), encoding="utf-8"
    )
    print("")
    print(f"A-vs-B full-trajectory parity: "
          f"{'EXACT MATCH (all functions)' if all_ab else 'MISMATCH'}")
    if args.repeat_b:
        print(f"B determinism repeat:          "
              f"{'EXACT MATCH (all functions)' if all_bb else 'MISMATCH'}")
    print(f"max per-attempt refinement mean (tree B): "
          f"{telemetry_max_mean:.3f}s")
    print(f"Report: {out_dir / 'parity_report.json'}")
    return 0 if (all_ab and (all_bb or not args.repeat_b)) else 1


if __name__ == "__main__":
    sys.exit(main())
