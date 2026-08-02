from __future__ import annotations

import argparse
import csv
import math
import statistics
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .benchmark import make_space
from .sampling import sobol_points
from .hard_domain import hard_cooling_benchmark
from .gpu_engine import GPUSmartExperimentEngine


def finite_curve(curve):
    arr = np.asarray(curve, dtype=float)
    finite = np.where(np.isfinite(arr))[0]

    if len(finite) == 0:
        return np.zeros_like(arr)

    arr[:finite[0]] = arr[finite[0]]
    return arr


def evaluate_points(space, points01):
    best_score = -np.inf
    best_result = None
    curve = []

    for p in points01:
        x = space.denormalize(p)
        score, feasible, metadata = hard_cooling_benchmark(x)

        if feasible and score > best_score:
            best_score = float(score)
            best_result = (x.copy(), float(score), metadata)

        curve.append(best_score)

    return best_result, finite_curve(curve)


def smart_curve(history):
    best = -np.inf
    curve = []

    for result in history:
        if result.feasible and result.score > best:
            best = result.score
        curve.append(best)

    return finite_curve(curve)


def first_hit(curve, target):
    for i, value in enumerate(curve, start=1):
        if value >= target:
            return i
    return None


def normalized_auc(curve):
    arr = np.asarray(curve, dtype=float)

    if len(arr) == 0:
        return float("nan")
    if len(arr) == 1:
        return float(arr[0])

    return float(np.trapezoid(arr, dx=1.0) / (len(arr) - 1))


def bootstrap_mean_ci(values, confidence=0.95, samples=5000, seed=12345):
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        return float("nan"), float("nan")
    if len(values) == 1:
        return float(values[0]), float(values[0])

    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)

    for i in range(samples):
        draw = rng.choice(values, size=len(values), replace=True)
        means[i] = float(np.mean(draw))

    alpha = (1.0 - confidence) / 2.0

    return (
        float(np.quantile(means, alpha)),
        float(np.quantile(means, 1.0 - alpha)),
    )


def paired_wilcoxon_greater(a, b):
    """
    Tests H1: a > b for paired runs.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    try:
        result = stats.wilcoxon(
            a,
            b,
            alternative="greater",
            zero_method="wilcox",
        )
        return float(result.statistic), float(result.pvalue)
    except Exception:
        return float("nan"), float("nan")


def run_one(
    seed,
    budget,
    pool,
    chunk,
    refit_interval,
    force_cpu=False,
):
    space = make_space()

    # Random
    rng = np.random.default_rng(seed)

    t0 = time.perf_counter()
    random_best, random_curve = evaluate_points(
        space,
        rng.random((budget, space.dim)),
    )
    random_wall = time.perf_counter() - t0

    # Sobol
    t0 = time.perf_counter()
    sobol_best, sobol_curve = evaluate_points(
        space,
        sobol_points(budget, space.dim, seed),
    )
    sobol_wall = time.perf_counter() - t0

    # Smart
    initial = min(24, max(12, budget // 3))
    smart_trials = max(0, budget - initial)

    engine = GPUSmartExperimentEngine(
        space,
        hard_cooling_benchmark,
        seed=seed,
        force_cpu=force_cpu,
    )

    t0 = time.perf_counter()
    smart_result = engine.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=pool,
        candidate_chunk_size=chunk,
        patience=max(25, budget),
        refit_interval=refit_interval,
    )
    smart_wall = time.perf_counter() - t0

    s_curve = smart_curve(engine.history)

    random_score = float(random_best[1])
    sobol_score = float(sobol_best[1])
    smart_score = float(smart_result["best"].score)

    best_final = max(random_score, sobol_score, smart_score)
    target = 0.99 * best_final

    random_hit = first_hit(random_curve, target)
    sobol_hit = first_hit(sobol_curve, target)
    smart_hit = first_hit(s_curve, target)

    # Penalize failures as budget+1 rather than dropping them.
    random_pen = random_hit if random_hit is not None else budget + 1
    sobol_pen = sobol_hit if sobol_hit is not None else budget + 1
    smart_pen = smart_hit if smart_hit is not None else budget + 1

    scores = {
        "random": random_score,
        "sobol": sobol_score,
        "smart": smart_score,
    }

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    winner = ordered[0][0]

    # If essentially tied, record tie.
    if abs(ordered[0][1] - ordered[1][1]) <= 1e-10:
        winner = "tie"

    smart_steps = max(0, smart_result["trials_run"] - initial)
    total_candidates = smart_steps * pool
    scoring_s = float(smart_result["timings"]["candidate_scoring_s"])
    throughput = total_candidates / scoring_s if scoring_s > 0 else 0.0

    return {
        "seed": int(seed),
        "random_score": random_score,
        "sobol_score": sobol_score,
        "smart_score": smart_score,
        "smart_minus_random": smart_score - random_score,
        "smart_minus_sobol": smart_score - sobol_score,
        "winner": winner,
        "target_score": float(target),
        "random_hit": random_hit,
        "sobol_hit": sobol_hit,
        "smart_hit": smart_hit,
        "random_penalized": int(random_pen),
        "sobol_penalized": int(sobol_pen),
        "smart_penalized": int(smart_pen),
        "random_auc": normalized_auc(random_curve),
        "sobol_auc": normalized_auc(sobol_curve),
        "smart_auc": normalized_auc(s_curve),
        "random_wall_s": float(random_wall),
        "sobol_wall_s": float(sobol_wall),
        "smart_wall_s": float(smart_wall),
        "smart_trials_run": int(smart_result["trials_run"]),
        "candidate_throughput": float(throughput),
        "model_total_s": float(smart_result["timings"]["model_total_s"]),
        "candidate_scoring_s": scoring_s,
        "optimized_fits": int(
            smart_result["fit_diagnostics"]["optimized_fits"]
        ),
        "warm_only_fits": int(
            smart_result["fit_diagnostics"]["warm_only_fits"]
        ),
        "scipy_warnings": int(
            smart_result["fit_diagnostics"]["scipy_warnings"]
        ),
        "fallback_fits": int(
            smart_result["fit_diagnostics"]["fallback_fits"]
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="V0.2.5 statistical hard benchmark"
    )
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--budget", type=int, default=60)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--start-seed", type=int, default=200)
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force Smart engine to CPU.",
    )
    args = parser.parse_args()

    if args.runs < 2:
        raise SystemExit("--runs must be >= 2")
    if args.budget < 20:
        raise SystemExit("--budget must be >= 20")

    out_dir = Path("v025_statistical_results")
    out_dir.mkdir(exist_ok=True)

    rows = []

    print("=" * 88)
    print("Engineering AI Core V0.2.5 — Statistical Hard Benchmark")
    print("=" * 88)
    print(f"Runs             : {args.runs}")
    print(f"Budget           : {args.budget}")
    print(f"Pool             : {args.pool:,}")
    print(f"Chunk            : {args.chunk:,}")
    print(f"Refit interval   : {args.refit_interval}")
    print(f"Start seed       : {args.start_seed}")
    print(f"Forced CPU       : {args.cpu}")
    print("")

    total_t0 = time.perf_counter()

    for i in range(args.runs):
        seed = args.start_seed + i

        row = run_one(
            seed=seed,
            budget=args.budget,
            pool=args.pool,
            chunk=args.chunk,
            refit_interval=args.refit_interval,
            force_cpu=args.cpu,
        )
        rows.append(row)

        print(
            f"[{i+1:02d}/{args.runs}] seed={seed} "
            f"R={row['random_score']:.3f} "
            f"Sobol={row['sobol_score']:.3f} "
            f"Smart={row['smart_score']:.3f} "
            f"winner={row['winner']} "
            f"smart_wall={row['smart_wall_s']:.2f}s"
        )

    total_wall = time.perf_counter() - total_t0

    random_scores = np.asarray(
        [r["random_score"] for r in rows],
        dtype=float,
    )
    sobol_scores = np.asarray(
        [r["sobol_score"] for r in rows],
        dtype=float,
    )
    smart_scores = np.asarray(
        [r["smart_score"] for r in rows],
        dtype=float,
    )

    smart_minus_random = smart_scores - random_scores
    smart_minus_sobol = smart_scores - sobol_scores

    ci_sr = bootstrap_mean_ci(
        smart_minus_random,
        seed=args.start_seed + 10000,
    )
    ci_ss = bootstrap_mean_ci(
        smart_minus_sobol,
        seed=args.start_seed + 20000,
    )

    stat_sr, p_sr = paired_wilcoxon_greater(
        smart_scores,
        random_scores,
    )
    stat_ss, p_ss = paired_wilcoxon_greater(
        smart_scores,
        sobol_scores,
    )

    smart_wins = sum(r["winner"] == "smart" for r in rows)
    random_wins = sum(r["winner"] == "random" for r in rows)
    sobol_wins = sum(r["winner"] == "sobol" for r in rows)
    ties = sum(r["winner"] == "tie" for r in rows)

    random_hit_rate = 100.0 * sum(
        r["random_hit"] is not None for r in rows
    ) / args.runs
    sobol_hit_rate = 100.0 * sum(
        r["sobol_hit"] is not None for r in rows
    ) / args.runs
    smart_hit_rate = 100.0 * sum(
        r["smart_hit"] is not None for r in rows
    ) / args.runs

    random_pen = np.asarray(
        [r["random_penalized"] for r in rows],
        dtype=float,
    )
    sobol_pen = np.asarray(
        [r["sobol_penalized"] for r in rows],
        dtype=float,
    )
    smart_pen = np.asarray(
        [r["smart_penalized"] for r in rows],
        dtype=float,
    )

    random_auc = np.asarray(
        [r["random_auc"] for r in rows],
        dtype=float,
    )
    sobol_auc = np.asarray(
        [r["sobol_auc"] for r in rows],
        dtype=float,
    )
    smart_auc = np.asarray(
        [r["smart_auc"] for r in rows],
        dtype=float,
    )

    smart_walls = np.asarray(
        [r["smart_wall_s"] for r in rows],
        dtype=float,
    )
    throughputs = np.asarray(
        [r["candidate_throughput"] for r in rows],
        dtype=float,
    )

    model_times = np.asarray(
        [r["model_total_s"] for r in rows],
        dtype=float,
    )
    scoring_times = np.asarray(
        [r["candidate_scoring_s"] for r in rows],
        dtype=float,
    )

    warnings_total = sum(r["scipy_warnings"] for r in rows)
    fallback_total = sum(r["fallback_fits"] for r in rows)

    summary = f"""
========================================================================================
Engineering AI Core V0.2.5 — Statistical Hard Benchmark
========================================================================================
Runs                         : {args.runs}
Budget / method / run        : {args.budget}
Candidate pool / smart step  : {args.pool:,}
GPU chunk                    : {args.chunk:,}
Refit interval               : {args.refit_interval}
Total benchmark wall time    : {total_wall:.3f} s

FINAL SCORE
Random mean                  : {np.mean(random_scores):.6f}
Sobol mean                   : {np.mean(sobol_scores):.6f}
Smart mean                   : {np.mean(smart_scores):.6f}

Random median                : {np.median(random_scores):.6f}
Sobol median                 : {np.median(sobol_scores):.6f}
Smart median                 : {np.median(smart_scores):.6f}

Random std                   : {np.std(random_scores, ddof=1):.6f}
Sobol std                    : {np.std(sobol_scores, ddof=1):.6f}
Smart std                    : {np.std(smart_scores, ddof=1):.6f}

WIN RATE
Smart wins                   : {smart_wins}/{args.runs} ({100*smart_wins/args.runs:.1f}%)
Random wins                  : {random_wins}/{args.runs} ({100*random_wins/args.runs:.1f}%)
Sobol wins                   : {sobol_wins}/{args.runs} ({100*sobol_wins/args.runs:.1f}%)
Ties                         : {ties}/{args.runs}

PAIRED ADVANTAGE
Mean Smart - Random          : {np.mean(smart_minus_random):+.6f}
Median Smart - Random        : {np.median(smart_minus_random):+.6f}
95% CI Smart - Random        : [{ci_sr[0]:+.6f}, {ci_sr[1]:+.6f}]

Mean Smart - Sobol           : {np.mean(smart_minus_sobol):+.6f}
Median Smart - Sobol         : {np.median(smart_minus_sobol):+.6f}
95% CI Smart - Sobol         : [{ci_ss[0]:+.6f}, {ci_ss[1]:+.6f}]

99% TARGET HIT RATE
Random                       : {random_hit_rate:.1f}%
Sobol                        : {sobol_hit_rate:.1f}%
Smart                        : {smart_hit_rate:.1f}%

PENALIZED EXPERIMENTS TO TARGET
(failure = budget + 1 = {args.budget + 1})
Random mean                  : {np.mean(random_pen):.2f}
Sobol mean                   : {np.mean(sobol_pen):.2f}
Smart mean                   : {np.mean(smart_pen):.2f}

Random median                : {np.median(random_pen):.2f}
Sobol median                 : {np.median(sobol_pen):.2f}
Smart median                 : {np.median(smart_pen):.2f}

CONVERGENCE AUC
Random mean AUC              : {np.mean(random_auc):.6f}
Sobol mean AUC               : {np.mean(sobol_auc):.6f}
Smart mean AUC               : {np.mean(smart_auc):.6f}

STATISTICAL TESTS
Smart > Random Wilcoxon stat : {stat_sr}
Smart > Random p-value       : {p_sr}
Smart > Sobol Wilcoxon stat  : {stat_ss}
Smart > Sobol p-value        : {p_ss}

SMART ENGINE PERFORMANCE
Mean smart wall time         : {np.mean(smart_walls):.3f} s
Median smart wall time       : {np.median(smart_walls):.3f} s
Mean candidate throughput    : {np.mean(throughputs):,.0f} / sec
Median candidate throughput  : {np.median(throughputs):,.0f} / sec
Mean model time              : {np.mean(model_times):.3f} s
Mean candidate scoring time  : {np.mean(scoring_times):.3f} s
SciPy warnings total         : {warnings_total}
Fallback fits total          : {fallback_total}

PASS GUIDANCE FOR THIS SYNTHETIC BENCHMARK
- Smart win rate >= 80%
- Both 95% paired confidence intervals entirely above 0
- Both one-sided Wilcoxon p-values < 0.05
- Smart target-hit rate clearly above both baselines
- No recurring GP fitting instability

NOTE: these are project benchmark gates, not universal scientific thresholds.
NOTE: synthetic benchmark only; not validated engineering physics.
========================================================================================
""".strip()

    print()
    print(summary)

    # CSV
    csv_path = out_dir / "runs.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    (out_dir / "summary.txt").write_text(
        summary,
        encoding="utf-8",
    )

    # Chart 1 - final scores
    xs = np.arange(1, args.runs + 1)

    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)
    ax.plot(xs, random_scores, marker="o", label="Random")
    ax.plot(xs, sobol_scores, marker="o", label="Sobol")
    ax.plot(xs, smart_scores, marker="o", label="Smart GPU")
    ax.set_xlabel("Run")
    ax.set_ylabel("Final Best Feasible Score")
    ax.set_title("V0.2.5 — Final Score Across Seeds")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(
        out_dir / "final_scores.png",
        dpi=170,
    )
    plt.close(fig)

    # Chart 2 - paired advantages
    fig = plt.figure(figsize=(11, 6))
    ax = fig.add_subplot(111)
    ax.plot(
        xs,
        smart_minus_random,
        marker="o",
        label="Smart - Random",
    )
    ax.plot(
        xs,
        smart_minus_sobol,
        marker="o",
        label="Smart - Sobol",
    )
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Run")
    ax.set_ylabel("Paired Score Advantage")
    ax.set_title("V0.2.5 — Smart Engine Paired Advantage")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(
        out_dir / "smart_advantage.png",
        dpi=170,
    )
    plt.close(fig)

    # Chart 3 - penalized target efficiency
    labels = ["Random", "Sobol", "Smart"]
    values = [
        np.mean(random_pen),
        np.mean(sobol_pen),
        np.mean(smart_pen),
    ]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.bar(labels, values)
    ax.set_ylabel("Mean Penalized Experiments to 99% Target")
    ax.set_title("V0.2.5 — Experiment Efficiency")
    ax.grid(True, axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(
        out_dir / "target_efficiency.png",
        dpi=170,
    )
    plt.close(fig)

    print()
    print(f"Saved summary : {out_dir / 'summary.txt'}")
    print(f"Saved CSV     : {csv_path}")
    print(f"Saved charts  : {out_dir / 'final_scores.png'}")
    print(f"                {out_dir / 'smart_advantage.png'}")
    print(f"                {out_dir / 'target_efficiency.png'}")


if __name__ == "__main__":
    main()
