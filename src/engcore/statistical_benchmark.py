from __future__ import annotations

from pathlib import Path
import argparse
import csv
import math
import statistics
import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
from sklearn.exceptions import ConvergenceWarning

from .benchmark import (
    make_space,
    random_search,
    smart_search,
    safe_curve,
)
from .domain import cooling_benchmark

warnings.filterwarnings("ignore", category=ConvergenceWarning)


def first_hit(curve, target):
    for i, value in enumerate(curve, start=1):
        if value >= target:
            return i
    return None


def normalized_auc(curve):
    """
    Area under best-so-far convergence curve, normalized by number of trials.
    Higher is better. Useful for measuring how quickly a method finds good designs.
    """
    arr = np.asarray(curve, dtype=float)
    if len(arr) == 0:
        return float("nan")
    if len(arr) == 1:
        return float(arr[0])
    return float(np.trapezoid(arr, dx=1.0) / (len(arr) - 1))


def bootstrap_ci(values, confidence=0.95, samples=4000, seed=12345):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return float("nan"), float("nan")
    if len(values) == 1:
        return float(values[0]), float(values[0])

    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    n = len(values)

    for i in range(samples):
        draw = rng.choice(values, size=n, replace=True)
        means[i] = np.mean(draw)

    alpha = (1.0 - confidence) / 2.0
    return (
        float(np.quantile(means, alpha)),
        float(np.quantile(means, 1.0 - alpha)),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Statistical benchmark: Random Search vs Smart Experiment Engine"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of independent seeds/runs. Recommended: 20-50.",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=100,
        help="Maximum experiment budget per method per run.",
    )
    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=2048,
        help="Reserved for future tuning. Current smart_search uses its internal pool.",
    )
    args = parser.parse_args()

    if args.runs < 2:
        raise SystemExit("--runs must be >= 2")
    if args.budget < 16:
        raise SystemExit("--budget must be >= 16")

    out_dir = Path("statistical_results")
    out_dir.mkdir(exist_ok=True)

    space = make_space()
    rows = []

    random_scores = []
    smart_scores = []
    score_diffs = []
    random_aucs = []
    smart_aucs = []
    target_random_hits = []
    target_smart_hits = []

    random_wins = 0
    smart_wins = 0
    ties = 0

    for run_index in range(args.runs):
        seed = 100 + run_index

        random_best, random_curve = random_search(
            space,
            cooling_benchmark,
            trials=args.budget,
            seed=seed,
        )

        smart_result, smart_curve = smart_search(
            space,
            cooling_benchmark,
            total_budget=args.budget,
            seed=seed,
        )

        random_curve = safe_curve(random_curve)
        smart_curve = safe_curve(smart_curve)

        random_score = float(random_best[1]) if random_best else float("-inf")
        smart_score = float(smart_result["best"].score)

        best_final = max(random_score, smart_score)
        target = 0.99 * best_final

        random_hit = first_hit(random_curve, target)
        smart_hit = first_hit(smart_curve, target)

        random_auc = normalized_auc(random_curve)
        smart_auc = normalized_auc(smart_curve)

        diff = smart_score - random_score
        diff_pct = (diff / abs(random_score) * 100.0) if random_score != 0 else float("nan")

        if smart_score > random_score + 1e-12:
            smart_wins += 1
            winner = "smart"
        elif random_score > smart_score + 1e-12:
            random_wins += 1
            winner = "random"
        else:
            ties += 1
            winner = "tie"

        random_scores.append(random_score)
        smart_scores.append(smart_score)
        score_diffs.append(diff)
        random_aucs.append(random_auc)
        smart_aucs.append(smart_auc)

        if random_hit is not None:
            target_random_hits.append(random_hit)
        if smart_hit is not None:
            target_smart_hits.append(smart_hit)

        rows.append({
            "run": run_index + 1,
            "seed": seed,
            "random_score": random_score,
            "smart_score": smart_score,
            "smart_minus_random": diff,
            "improvement_pct": diff_pct,
            "winner": winner,
            "target_score": target,
            "random_experiments_to_target": random_hit,
            "smart_experiments_to_target": smart_hit,
            "random_auc": random_auc,
            "smart_auc": smart_auc,
            "smart_trials_run": smart_result["trials_run"],
        })

        print(
            f"[{run_index + 1:02d}/{args.runs}] seed={seed} "
            f"random={random_score:.4f} smart={smart_score:.4f} "
            f"diff={diff:+.4f} winner={winner}"
        )

    csv_path = out_dir / "runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    random_scores_np = np.asarray(random_scores)
    smart_scores_np = np.asarray(smart_scores)
    diffs_np = np.asarray(score_diffs)

    # Paired non-parametric test: same seed, two methods.
    try:
        wilcoxon = stats.wilcoxon(
            smart_scores_np,
            random_scores_np,
            alternative="greater",
            zero_method="wilcox",
        )
        wilcoxon_stat = float(wilcoxon.statistic)
        wilcoxon_p = float(wilcoxon.pvalue)
    except Exception:
        wilcoxon_stat = float("nan")
        wilcoxon_p = float("nan")

    ci_low, ci_high = bootstrap_ci(diffs_np)

    smart_win_rate = smart_wins / args.runs * 100.0
    random_win_rate = random_wins / args.runs * 100.0

    avg_random_hit = (
        statistics.mean(target_random_hits) if target_random_hits else float("nan")
    )
    avg_smart_hit = (
        statistics.mean(target_smart_hits) if target_smart_hits else float("nan")
    )

    random_hit_rate = len(target_random_hits) / args.runs * 100.0
    smart_hit_rate = len(target_smart_hits) / args.runs * 100.0

    summary_lines = [
        "=" * 78,
        "Engineering AI Core V0.2.1 — Statistical Benchmark",
        "=" * 78,
        f"Runs                    : {args.runs}",
        f"Budget / method / run   : {args.budget}",
        "",
        "FINAL SCORE",
        f"Random mean             : {np.mean(random_scores_np):.6f}",
        f"Smart mean              : {np.mean(smart_scores_np):.6f}",
        f"Random median           : {np.median(random_scores_np):.6f}",
        f"Smart median            : {np.median(smart_scores_np):.6f}",
        f"Random std              : {np.std(random_scores_np, ddof=1):.6f}",
        f"Smart std               : {np.std(smart_scores_np, ddof=1):.6f}",
        "",
        "PAIRED PERFORMANCE",
        f"Average smart advantage : {np.mean(diffs_np):+.6f}",
        f"Median smart advantage  : {np.median(diffs_np):+.6f}",
        f"95% bootstrap CI        : [{ci_low:+.6f}, {ci_high:+.6f}]",
        f"Smart wins              : {smart_wins}/{args.runs} ({smart_win_rate:.1f}%)",
        f"Random wins             : {random_wins}/{args.runs} ({random_win_rate:.1f}%)",
        f"Ties                    : {ties}/{args.runs}",
        "",
        "CONVERGENCE SPEED",
        f"Random mean AUC         : {np.mean(random_aucs):.6f}",
        f"Smart mean AUC          : {np.mean(smart_aucs):.6f}",
        f"Random target hit rate  : {random_hit_rate:.1f}%",
        f"Smart target hit rate   : {smart_hit_rate:.1f}%",
        f"Random avg exp to target: {avg_random_hit}",
        f"Smart avg exp to target : {avg_smart_hit}",
        "",
        "STATISTICAL TEST",
        f"Wilcoxon statistic      : {wilcoxon_stat}",
        f"One-sided p-value       : {wilcoxon_p}",
        "",
        "INTERPRETATION",
        "- Smart win rate > 50% suggests the smart engine is more reliable than random.",
        "- Positive bootstrap CI entirely above 0 is stronger evidence of real advantage.",
        "- Higher AUC means good designs are found earlier, not only at the final trial.",
        "- Lower experiments-to-target means less expensive real simulation work.",
        "",
        "NOTE: synthetic benchmark only; not validated engineering physics.",
        "=" * 78,
    ]

    summary_text = "\n".join(summary_lines)
    (out_dir / "summary.txt").write_text(summary_text, encoding="utf-8")

    # Chart 1: paired final scores
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    xs = np.arange(1, args.runs + 1)
    ax.plot(xs, random_scores_np, marker="o", label="Random Search")
    ax.plot(xs, smart_scores_np, marker="o", label="Smart Experiment Engine")
    ax.set_xlabel("Run")
    ax.set_ylabel("Final Best Score")
    ax.set_title("Final Score Across Independent Seeds")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "final_scores.png", dpi=160)
    plt.close(fig)

    # Chart 2: per-run paired improvement
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.bar(xs, diffs_np)
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Run")
    ax.set_ylabel("Smart Score - Random Score")
    ax.set_title("Smart Engine Advantage per Run")
    ax.grid(True, axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "paired_improvement.png", dpi=160)
    plt.close(fig)

    print()
    print(summary_text)
    print()
    print(f"Saved CSV    : {csv_path}")
    print(f"Saved summary: {out_dir / 'summary.txt'}")
    print(f"Saved charts : {out_dir / 'final_scores.png'}")
    print(f"               {out_dir / 'paired_improvement.png'}")


if __name__ == "__main__":
    main()
