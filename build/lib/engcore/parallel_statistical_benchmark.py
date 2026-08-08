from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import csv
import os
import statistics
import time

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .benchmark import make_space, random_search, smart_search, safe_curve
from .domain import cooling_benchmark


def first_hit(curve, target):
    for i, value in enumerate(curve, start=1):
        if value >= target:
            return i
    return None


def normalized_auc(curve):
    arr = np.asarray(curve, dtype=float)
    if len(arr) <= 1:
        return float(arr[0]) if len(arr) else float("nan")
    return float(np.trapezoid(arr, dx=1.0) / (len(arr) - 1))


def run_one(seed: int, budget: int):
    space = make_space()

    random_best, random_curve = random_search(
        space, cooling_benchmark, trials=budget, seed=seed
    )
    smart_result, smart_curve = smart_search(
        space, cooling_benchmark, total_budget=budget, seed=seed
    )

    random_curve = safe_curve(random_curve)
    smart_curve = safe_curve(smart_curve)

    random_score = float(random_best[1]) if random_best else float("-inf")
    smart_score = float(smart_result["best"].score)

    target = 0.99 * max(random_score, smart_score)
    random_hit = first_hit(random_curve, target)
    smart_hit = first_hit(smart_curve, target)

    # Corrected metric:
    # a failure to hit within budget is budget + 1 rather than being dropped.
    random_penalized = random_hit if random_hit is not None else budget + 1
    smart_penalized = smart_hit if smart_hit is not None else budget + 1

    return {
        "seed": seed,
        "random_score": random_score,
        "smart_score": smart_score,
        "diff": smart_score - random_score,
        "winner": "smart" if smart_score > random_score else (
            "random" if random_score > smart_score else "tie"
        ),
        "target": target,
        "random_hit": random_hit,
        "smart_hit": smart_hit,
        "random_penalized": random_penalized,
        "smart_penalized": smart_penalized,
        "random_auc": normalized_auc(random_curve),
        "smart_auc": normalized_auc(smart_curve),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, (os.cpu_count() or 4) // 2)),
    )
    args = parser.parse_args()

    out_dir = Path("parallel_statistical_results")
    out_dir.mkdir(exist_ok=True)

    seeds = [100 + i for i in range(args.runs)]
    rows = []

    print("=" * 78)
    print("Engineering AI Core V0.2.2 — Parallel Statistical Benchmark")
    print("=" * 78)
    print(f"Runs    : {args.runs}")
    print(f"Budget  : {args.budget}")
    print(f"Workers : {args.workers}")
    print("")

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(run_one, seed, args.budget): seed
            for seed in seeds
        }
        done = 0
        for future in as_completed(future_map):
            row = future.result()
            rows.append(row)
            done += 1
            print(
                f"[{done:02d}/{args.runs}] seed={row['seed']} "
                f"random={row['random_score']:.4f} "
                f"smart={row['smart_score']:.4f} "
                f"diff={row['diff']:+.4f} "
                f"winner={row['winner']}"
            )

    wall = time.perf_counter() - t0
    rows.sort(key=lambda r: r["seed"])

    smart_wins = sum(r["winner"] == "smart" for r in rows)
    random_wins = sum(r["winner"] == "random" for r in rows)
    ties = args.runs - smart_wins - random_wins

    random_scores = np.array([r["random_score"] for r in rows])
    smart_scores = np.array([r["smart_score"] for r in rows])
    diffs = smart_scores - random_scores

    random_hit_rate = 100 * sum(r["random_hit"] is not None for r in rows) / args.runs
    smart_hit_rate = 100 * sum(r["smart_hit"] is not None for r in rows) / args.runs

    random_pen = np.array([r["random_penalized"] for r in rows], dtype=float)
    smart_pen = np.array([r["smart_penalized"] for r in rows], dtype=float)

    try:
        wilcoxon = stats.wilcoxon(
            smart_scores,
            random_scores,
            alternative="greater",
            zero_method="wilcox",
        )
        p_value = float(wilcoxon.pvalue)
    except Exception:
        p_value = float("nan")

    summary = f"""
==============================================================================
Engineering AI Core V0.2.2 — Parallel Statistical Benchmark
==============================================================================
Runs                    : {args.runs}
Budget / method / run   : {args.budget}
Parallel workers        : {args.workers}
Wall time               : {wall:.3f} s

FINAL SCORE
Random mean             : {np.mean(random_scores):.6f}
Smart mean              : {np.mean(smart_scores):.6f}
Random median           : {np.median(random_scores):.6f}
Smart median            : {np.median(smart_scores):.6f}

PAIRED PERFORMANCE
Average smart advantage : {np.mean(diffs):+.6f}
Median smart advantage  : {np.median(diffs):+.6f}
Smart wins              : {smart_wins}/{args.runs} ({100*smart_wins/args.runs:.1f}%)
Random wins             : {random_wins}/{args.runs} ({100*random_wins/args.runs:.1f}%)
Ties                    : {ties}/{args.runs}

CORRECTED TARGET METRICS
Random target hit rate  : {random_hit_rate:.1f}%
Smart target hit rate   : {smart_hit_rate:.1f}%
Random penalized mean   : {np.mean(random_pen):.2f} experiments
Smart penalized mean    : {np.mean(smart_pen):.2f} experiments
Random penalized median : {np.median(random_pen):.2f} experiments
Smart penalized median  : {np.median(smart_pen):.2f} experiments

CONVERGENCE
Random mean AUC         : {np.mean([r['random_auc'] for r in rows]):.6f}
Smart mean AUC          : {np.mean([r['smart_auc'] for r in rows]):.6f}

STATISTICAL TEST
One-sided Wilcoxon p    : {p_value}

NOTE: A failed target hit is counted as budget + 1 in the penalized metric.
NOTE: synthetic benchmark only; not validated engineering physics.
==============================================================================
""".strip()

    print()
    print(summary)

    csv_path = out_dir / "runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")

    xs = np.arange(1, args.runs + 1)
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.bar(xs, diffs)
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Run")
    ax.set_ylabel("Smart - Random Final Score")
    ax.set_title("V0.2.2 Paired Improvement")
    ax.grid(True, axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "paired_improvement.png", dpi=160)
    plt.close(fig)

    print(f"\nSaved results: {out_dir}")


if __name__ == "__main__":
    main()
