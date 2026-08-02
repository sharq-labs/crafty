from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .benchmark import make_space
from .benchmark_suite import BENCHMARKS, get_benchmark
from .sampling import sobol_points
from .gpu_engine import GPUSmartExperimentEngine
from .robust_engine import RobustSmartExperimentEngine


def evaluate_baseline(space, evaluator, points):
    best = -np.inf
    for p in points:
        x = space.denormalize(p)
        score, feasible, _ = evaluator(x)
        if feasible and score > best:
            best = float(score)
    return best


def run_case(spec, seed, budget, pool, chunk, refit_interval, force_cpu):
    space = make_space()
    rng = np.random.default_rng(seed)

    random_score = evaluate_baseline(
        space, spec.evaluator, rng.random((budget, space.dim))
    )
    sobol_score = evaluate_baseline(
        space, spec.evaluator, sobol_points(budget, space.dim, seed)
    )

    initial = min(24, max(12, budget // 3))
    smart_trials = budget - initial

    legacy = GPUSmartExperimentEngine(
        space,
        spec.evaluator,
        seed=seed,
        force_cpu=force_cpu,
    )
    t0 = time.perf_counter()
    legacy_result = legacy.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=pool,
        candidate_chunk_size=chunk,
        patience=max(25, budget),
        refit_interval=refit_interval,
    )
    legacy_wall = time.perf_counter() - t0

    robust = RobustSmartExperimentEngine(
        space,
        spec.evaluator,
        seed=seed,
        force_cpu=force_cpu,
        n_regions=3,
    )
    t0 = time.perf_counter()
    robust_result = robust.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=pool,
        candidate_chunk_size=chunk,
        refit_interval=refit_interval,
    )
    robust_wall = time.perf_counter() - t0

    values = {
        "random": random_score,
        "sobol": sobol_score,
        "legacy": legacy_result["best"].score,
        "robust": robust_result["best"].score,
    }
    winner = max(values, key=values.get)

    return {
        "benchmark": spec.name,
        "seed": seed,
        "random": random_score,
        "sobol": sobol_score,
        "legacy": legacy_result["best"].score,
        "robust": robust_result["best"].score,
        "robust_minus_legacy": robust_result["best"].score - legacy_result["best"].score,
        "robust_minus_random": robust_result["best"].score - random_score,
        "robust_minus_sobol": robust_result["best"].score - sobol_score,
        "winner": winner,
        "legacy_wall_s": legacy_wall,
        "robust_wall_s": robust_wall,
        "recoveries": sum(
            e.get("event") == "stagnation_recovery"
            for e in robust_result["events"]
        ),
        "robust_warnings": robust_result["fit_diagnostics"]["scipy_warnings"],
        "robust_fallbacks": robust_result["fit_diagnostics"]["fallback_fits"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--pool", type=int, default=75000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--start-seed", type=int, default=600)
    parser.add_argument(
        "--benchmarks",
        default="all",
        help="all or comma-separated names",
    )
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    if args.benchmarks == "all":
        specs = BENCHMARKS
    else:
        specs = [
            get_benchmark(name.strip())
            for name in args.benchmarks.split(",")
            if name.strip()
        ]

    out_dir = Path("v026_suite_results")
    out_dir.mkdir(exist_ok=True)

    rows = []
    total = len(specs) * args.runs
    done = 0

    print("=" * 94)
    print("Engineering AI Core V0.2.6 — Robust Benchmark Suite")
    print("=" * 94)
    print(f"Benchmarks       : {[s.name for s in specs]}")
    print(f"Runs / benchmark : {args.runs}")
    print(f"Budget           : {args.budget}")
    print(f"Pool             : {args.pool:,}")
    print("")

    t_all = time.perf_counter()

    for spec in specs:
        for i in range(args.runs):
            seed = args.start_seed + i

            row = run_case(
                spec,
                seed,
                args.budget,
                args.pool,
                args.chunk,
                args.refit_interval,
                args.cpu,
            )
            rows.append(row)
            done += 1

            print(
                f"[{done:02d}/{total}] {spec.name:20s} seed={seed} "
                f"R={row['random']:.2f} S={row['sobol']:.2f} "
                f"L={row['legacy']:.2f} Robust={row['robust']:.2f} "
                f"ΔL={row['robust_minus_legacy']:+.2f} "
                f"winner={row['winner']}"
            )

    total_wall = time.perf_counter() - t_all

    # Aggregate.
    benchmark_summaries = {}
    for spec in specs:
        subset = [r for r in rows if r["benchmark"] == spec.name]
        benchmark_summaries[spec.name] = {
            "robust_mean": float(np.mean([r["robust"] for r in subset])),
            "legacy_mean": float(np.mean([r["legacy"] for r in subset])),
            "random_mean": float(np.mean([r["random"] for r in subset])),
            "sobol_mean": float(np.mean([r["sobol"] for r in subset])),
            "robust_win_rate": float(np.mean([r["winner"] == "robust" for r in subset]) * 100),
            "robust_vs_legacy_mean": float(np.mean([r["robust_minus_legacy"] for r in subset])),
        }

    robust_wins = sum(r["winner"] == "robust" for r in rows)
    legacy_wins = sum(r["winner"] == "legacy" for r in rows)
    random_wins = sum(r["winner"] == "random" for r in rows)
    sobol_wins = sum(r["winner"] == "sobol" for r in rows)

    d_legacy = np.asarray([r["robust_minus_legacy"] for r in rows], dtype=float)

    summary_lines = [
        "=" * 94,
        "Engineering AI Core V0.2.6 — Robust Benchmark Suite Summary",
        "=" * 94,
        f"Cases                       : {len(rows)}",
        f"Total wall time             : {total_wall:.3f} s",
        "",
        "OVERALL WIN COUNT",
        f"Robust wins                 : {robust_wins}/{len(rows)} ({100*robust_wins/len(rows):.1f}%)",
        f"Legacy Smart wins           : {legacy_wins}/{len(rows)} ({100*legacy_wins/len(rows):.1f}%)",
        f"Random wins                 : {random_wins}/{len(rows)} ({100*random_wins/len(rows):.1f}%)",
        f"Sobol wins                  : {sobol_wins}/{len(rows)} ({100*sobol_wins/len(rows):.1f}%)",
        "",
        "ROBUST VS LEGACY",
        f"Mean advantage              : {np.mean(d_legacy):+.6f}",
        f"Median advantage            : {np.median(d_legacy):+.6f}",
        f"Robust better than Legacy   : {np.mean(d_legacy > 0)*100:.1f}%",
        f"Robust equal/better Legacy  : {np.mean(d_legacy >= -1e-10)*100:.1f}%",
        "",
        "STABILITY",
        f"Total GP warnings           : {sum(r['robust_warnings'] for r in rows)}",
        f"Total fallback fits         : {sum(r['robust_fallbacks'] for r in rows)}",
        f"Total recovery events       : {sum(r['recoveries'] for r in rows)}",
        "",
        "PER BENCHMARK",
    ]

    for name, data in benchmark_summaries.items():
        summary_lines.extend([
            f"{name}",
            f"  Random mean               : {data['random_mean']:.4f}",
            f"  Sobol mean                : {data['sobol_mean']:.4f}",
            f"  Legacy mean               : {data['legacy_mean']:.4f}",
            f"  Robust mean               : {data['robust_mean']:.4f}",
            f"  Robust win rate           : {data['robust_win_rate']:.1f}%",
            f"  Robust - Legacy mean      : {data['robust_vs_legacy_mean']:+.4f}",
        ])

    summary_lines.extend([
        "",
        "V0.2.6 TARGET",
        "- Robust should improve average performance across the suite, not only one benchmark.",
        "- Recovery should help deceptive / narrow / constrained cases.",
        "- No recurring GP fitting instability.",
        "- Use suite results to tune, not one benchmark seed.",
        "",
        "NOTE: synthetic optimizer validation only; not validated engineering physics.",
        "=" * 94,
    ])

    summary = "\n".join(summary_lines)
    print()
    print(summary)

    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")

    with (out_dir / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    (out_dir / "benchmark_summary.json").write_text(
        json.dumps(benchmark_summaries, indent=2),
        encoding="utf-8",
    )

    # One chart: robust-vs-legacy delta by case.
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    delta = [r["robust_minus_legacy"] for r in rows]
    ax.bar(range(1, len(delta)+1), delta)
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Benchmark case")
    ax.set_ylabel("Robust - Legacy final score")
    ax.set_title("V0.2.6 — Robust Improvement over Legacy Smart Engine")
    ax.grid(True, axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "robust_vs_legacy.png", dpi=170)
    plt.close(fig)

    print()
    print(f"Saved results: {out_dir}")


if __name__ == "__main__":
    main()
