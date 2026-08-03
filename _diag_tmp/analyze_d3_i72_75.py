"""Analysis-only script for i72-75 holdout + combined i71-75 COCO metrics."""
from __future__ import annotations

import csv
import json
import math
import shutil
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "validation_results/bbob_holdout_d3_i72_75_v033/runs.csv"


def short(alg: str) -> str:
    return alg.split("/")[-1]


def analyze_lab():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    print("n_rows", len(rows))
    bad = [r for r in rows if int(r["evaluations"]) != 60]
    print("budget_mismatches", len(bad))
    nans = []
    for r in rows:
        bf = float(r["best_f"])
        if not math.isfinite(bf):
            nans.append(r["problem_id"] + ":" + r["algorithm"])
    print("nans", nans)

    by = defaultdict(dict)
    for r in rows:
        by[r["problem_id"]][r["algorithm"]] = r

    adapt_better = stack_better = ties = 0
    deltas = []
    for pid, d in sorted(by.items()):
        s = float(d["stacked_v0301"]["best_f"])
        a = float(d["adaptive_stacked_v033"]["best_f"])
        deltas.append((pid, a - s, s, a))
        if abs(a - s) <= 1e-12:
            ties += 1
        elif a < s:
            adapt_better += 1
        else:
            stack_better += 1
    print(
        "PAIRWISE adaptive_better",
        adapt_better,
        "stack_better",
        stack_better,
        "ties",
        ties,
    )
    deltas_sorted = sorted(deltas, key=lambda t: t[1])
    print("largest_improve", deltas_sorted[0])
    print("largest_regress", deltas_sorted[-1])

    # catastrophic: a > 50*|s| and a-s > 1, or a-s > 100 absolute when s reasonable
    cat = []
    for pid, dlt, s, a in deltas:
        floor = max(abs(s), 1e-12)
        if a > 50.0 * floor and a - s > 1.0:
            cat.append((pid, dlt, s, a))
        elif a - s > 100.0 and a > s:
            cat.append((pid, dlt, s, a, "abs100"))
    print("catastrophic_count", len(cat))
    for c in cat[:20]:
        print("  CAT", c)

    gen = acc = rej = resg = resa = forced = pol = 0
    active = []
    per_acc = {}
    for r in rows:
        if r["algorithm"] != "adaptive_stacked_v033":
            continue
        md = json.loads(r["metadata_json"])
        g = int(md.get("adaptive_proposals_generated", 0))
        a = int(md.get("adaptive_proposals_accepted", 0))
        j = int(md.get("adaptive_proposals_rejected", 0))
        rg = int(md.get("adaptive_rescue_proposals", 0))
        ra = int(md.get("adaptive_rescue_accepted", 0))
        fr = int(md.get("adaptive_forced_refits", 0))
        upd = int(md.get("adaptive_policy_updates", 0))
        gen += g
        acc += a
        rej += j
        resg += rg
        resa += ra
        forced += fr
        pol += upd
        if a > 0:
            active.append(r["problem_id"])
            per_acc[r["problem_id"]] = a

    print("ADAPTIVE gen", gen, "acc", acc, "rej", rej)
    print(
        "rate",
        (acc / gen if gen else 0.0),
        "active_problems",
        len(active),
        "/",
        len(by),
    )
    print(
        "rescue_g",
        resg,
        "rescue_a",
        resa,
        "forced",
        forced,
        "identity_exec",
        pol - acc,
        "policy_updates",
        pol,
    )
    print("active_ids_count", len(active))
    # distribution of accepts
    hist = defaultdict(int)
    for v in per_acc.values():
        hist[v] += 1
    print("accept_count_hist", dict(sorted(hist.items())))
    return {
        "adapt_better": adapt_better,
        "stack_better": stack_better,
        "ties": ties,
        "gen": gen,
        "acc": acc,
        "rej": rej,
        "active": len(active),
        "resg": resg,
        "resa": resa,
        "forced": forced,
        "identity": pol - acc,
        "cat": len(cat),
        "n_problems": len(by),
        "largest_improve": deltas_sorted[0],
        "largest_regress": deltas_sorted[-1],
        "per_acc": per_acc,
    }


def combine_logs_for_cocopp():
    """
    Merge i71 and i72-75 observer trees into a temp combined folder by
    copying .info/.dat files. Does not modify original optimizer results.
    """
    dest = ROOT / "exdata/validation_results/_combined_d3_i71_75_v033/coco_logs"
    if dest.exists():
        shutil.rmtree(dest)
    sources = [
        ROOT / "exdata/validation_results/bbob_holdout_d3_i71_v033/coco_logs",
        ROOT / "exdata/validation_results/bbob_holdout_d3_i72_75_v033/coco_logs",
    ]
    for algo in ("cmaes", "ngopt", "stacked", "adaptive_stacked"):
        out_algo = dest / algo
        out_algo.mkdir(parents=True, exist_ok=True)
        for src_root in sources:
            src = src_root / algo
            if not src.is_dir():
                raise SystemExit(f"missing {src}")
            for p in src.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(src)
                    target = out_algo / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # For colliding filenames (same f*.info), concatenate
                    # is wrong for COCO; coco uses one info per function
                    # with multiple instances as lines. Need to merge .info
                    # carefully and copy unique data files.
                    if target.exists() and p.suffix == ".info":
                        # append instance lines from second source
                        old = target.read_text(encoding="utf-8", errors="replace")
                        new = p.read_text(encoding="utf-8", errors="replace")
                        # keep header from first; append unique data lines
                        old_lines = old.splitlines()
                        new_lines = new.splitlines()
                        merged = list(old_lines)
                        for ln in new_lines:
                            if ln not in merged:
                                # Prefer appending instance data lines
                                if ln.startswith("function_evaluation") or "data_f" in ln or ln.strip().startswith("%"):
                                    # header-ish: skip duplicates
                                    if ln in merged:
                                        continue
                                if ln not in merged:
                                    merged.append(ln)
                        # Simpler robust approach: for COCO, second copy's
                        # info may reference same relative data paths —
                        # better to use cocopp on both folders separately
                        # OR rebuild by suite. Fall back: overwrite with
                        # concatenated unique non-empty lines.
                        target.write_text(
                            "\n".join(merged) + "\n",
                            encoding="utf-8",
                        )
                    elif target.exists() and p.suffix != ".info":
                        # data files: if names collide, suffix source tag
                        # COCO data files for different instances usually
                        # append in same file. Check size — if same name,
                        # concatenate.
                        with target.open("ab") as fo, p.open("rb") as fi:
                            fo.write(b"\n")
                            fo.write(fi.read())
                    else:
                        shutil.copy2(p, target)
    return dest


def coco_metrics(log_dirs):
    warnings.filterwarnings("ignore")
    import cocopp

    dsl = cocopp.load(log_dirs)
    targets = 10.0 ** np.linspace(2, -8, 51)
    scores = {}
    hits = {}
    for alg in sorted({d.algId for d in dsl}):
        ds = [d for d in dsl if d.algId == alg and d.dim == 3]
        rates = []
        solved = total = 0
        for d in ds:
            sr = np.asarray(d.detSuccessRates(targets), dtype=float).reshape(-1)
            rates.append(sr)
            ert = np.asarray(d.detERT(targets), dtype=float)
            # For multi-instance, ERT is aggregate; count finite ERTs
            # with ERT <= 60 as "hit within budget" proxy is imperfect.
            # Use mean success rate instead.
            total += ert.size
            solved += int(np.sum(np.isfinite(ert) & (ert <= 60)))
        R = np.vstack(rates)
        scores[short(alg)] = float(R.mean())
        hits[short(alg)] = (solved, total, solved / total if total else 0.0)
    print("COCO mean success over targets x datasets:")
    for k, v in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f"  {k:20s} auc={v:.6f} ert_hits_leq60={hits[k]}")
    return scores, hits


def main():
    print("=" * 70)
    print("LAB ANALYSIS i72-75")
    print("=" * 70)
    lab = analyze_lab()

    print("=" * 70)
    print("COMBINED COCO i71-75 via multi-folder load")
    print("=" * 70)
    # Prefer loading both folder trees directly without fragile merge.
    dirs = []
    for base in (
        "exdata/validation_results/bbob_holdout_d3_i71_v033/coco_logs",
        "exdata/validation_results/bbob_holdout_d3_i72_75_v033/coco_logs",
    ):
        for algo in ("cmaes", "ngopt", "stacked", "adaptive_stacked"):
            dirs.append(str(ROOT / base / algo))
    scores, hits = coco_metrics(dirs)

    # Also run cocopp postprocess into a combined ppdata folder for plots
    print("=" * 70)
    print("Running cocopp postprocess on 8 log folders (4 algos x 2 runs)")
    print("=" * 70)
    import cocopp

    out = cocopp.main(dirs)
    print("cocopp returned", out)


if __name__ == "__main__":
    main()
