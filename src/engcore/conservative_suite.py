from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .benchmark import make_space
from .benchmark_suite import BENCHMARKS, get_benchmark
from .sampling import sobol_points
from .gpu_engine import GPUSmartExperimentEngine
from .robust_engine import RobustSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine


def baseline(space, evaluator, points):
    best = -np.inf
    for p in points:
        score, feasible, _ = evaluator(
            space.denormalize(p)
        )
        if feasible and score > best:
            best = float(score)
    return best


def run_case(spec, seed, budget, pool, chunk, refit_interval, cpu):
    space = make_space()
    rng = np.random.default_rng(seed)

    random_score = baseline(
        space,
        spec.evaluator,
        rng.random((budget, space.dim)),
    )

    sobol_score = baseline(
        space,
        spec.evaluator,
        sobol_points(budget, space.dim, seed),
    )

    initial = min(24, max(12, budget // 3))
    smart_trials = budget - initial

    legacy = GPUSmartExperimentEngine(
        space, spec.evaluator, seed=seed, force_cpu=cpu
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

    conservative = ConservativeRobustEngine(
        space,
        spec.evaluator,
        seed=seed,
        force_cpu=cpu,
        n_regions=3,
    )
    t0 = time.perf_counter()
    conservative_result = conservative.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=pool,
        candidate_chunk_size=chunk,
        refit_interval=refit_interval,
    )
    conservative_wall = time.perf_counter() - t0

    values = {
        "random": random_score,
        "sobol": sobol_score,
        "legacy": float(legacy_result["best"].score),
        "v027": float(conservative_result["best"].score),
    }

    winner = max(values, key=values.get)

    return {
        "benchmark": spec.name,
        "seed": seed,
        "random": random_score,
        "sobol": sobol_score,
        "legacy": values["legacy"],
        "v027": values["v027"],
        "v027_minus_legacy": values["v027"] - values["legacy"],
        "v027_minus_random": values["v027"] - random_score,
        "v027_minus_sobol": values["v027"] - sobol_score,
        "winner": winner,
        "legacy_wall_s": legacy_wall,
        "v027_wall_s": conservative_wall,
        "v027_recoveries": conservative_result["recovery_count"],
        "v027_warnings":
            conservative_result["fit_diagnostics"]["scipy_warnings"],
        "v027_fallbacks":
            conservative_result["fit_diagnostics"]["fallback_fits"],
        "v027_trials": conservative_result["trials_run"],
    }


def bootstrap_ci(values, samples=5000, seed=1234):
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)

    for i in range(samples):
        means[i] = np.mean(
            rng.choice(arr, size=len(arr), replace=True)
        )

    return (
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--pool", type=int, default=75000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--start-seed", type=int, default=600)
    parser.add_argument("--benchmarks", default="all")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    specs = (
        BENCHMARKS
        if args.benchmarks == "all"
        else [
            get_benchmark(x.strip())
            for x in args.benchmarks.split(",")
            if x.strip()
        ]
    )

    out_dir = Path("v027_suite_results")
    out_dir.mkdir(exist_ok=True)

    rows = []
    total = len(specs) * args.runs
    done = 0

    print("=" * 98)
    print("Engineering AI Core V0.2.7 — Conservative Robust Suite")
    print("=" * 98)
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
                spec, seed,
                args.budget, args.pool, args.chunk,
                args.refit_interval, args.cpu,
            )
            rows.append(row)
            done += 1

            print(
                f"[{done:02d}/{total}] {spec.name:20s} seed={seed} "
                f"R={row['random']:.2f} S={row['sobol']:.2f} "
                f"Legacy={row['legacy']:.2f} V027={row['v027']:.2f} "
                f"ΔL={row['v027_minus_legacy']:+.2f} "
                f"winner={row['winner']}"
            )

    total_wall = time.perf_counter() - t_all

    delta = np.asarray(
        [r["v027_minus_legacy"] for r in rows],
        dtype=float,
    )
    ci = bootstrap_ci(delta)

    try:
        w = stats.wilcoxon(
            np.asarray([r["v027"] for r in rows]),
            np.asarray([r["legacy"] for r in rows]),
            alternative="greater",
            zero_method="wilcox",
        )
        wilcoxon_p = float(w.pvalue)
    except Exception:
        wilcoxon_p = float("nan")

    v027_wins = sum(r["winner"] == "v027" for r in rows)
    legacy_wins = sum(r["winner"] == "legacy" for r in rows)
    random_wins = sum(r["winner"] == "random" for r in rows)
    sobol_wins = sum(r["winner"] == "sobol" for r in rows)

    lines = [
        "=" * 98,
        "Engineering AI Core V0.2.7 — Conservative Robust Suite Summary",
        "=" * 98,
        f"Cases                         : {len(rows)}",
        f"Total wall time               : {total_wall:.3f} s",
        "",
        "OVERALL WIN COUNT",
        f"V0.2.7 wins                   : {v027_wins}/{len(rows)} ({100*v027_wins/len(rows):.1f}%)",
        f"Legacy wins                   : {legacy_wins}/{len(rows)} ({100*legacy_wins/len(rows):.1f}%)",
        f"Random wins                   : {random_wins}/{len(rows)} ({100*random_wins/len(rows):.1f}%)",
        f"Sobol wins                    : {sobol_wins}/{len(rows)} ({100*sobol_wins/len(rows):.1f}%)",
        "",
        "V0.2.7 VS LEGACY",
        f"Mean advantage                : {np.mean(delta):+.6f}",
        f"Median advantage              : {np.median(delta):+.6f}",
        f"95% bootstrap CI              : [{ci[0]:+.6f}, {ci[1]:+.6f}]",
        f"Better than Legacy            : {np.mean(delta > 1e-10)*100:.1f}%",
        f"Equal/better than Legacy      : {np.mean(delta >= -1e-10)*100:.1f}%",
        f"Wilcoxon p (V027 > Legacy)    : {wilcoxon_p}",
        "",
        "STABILITY",
        f"GP warnings                   : {sum(r['v027_warnings'] for r in rows)}",
        f"Fallback fits                 : {sum(r['v027_fallbacks'] for r in rows)}",
        f"Recovery pulses               : {sum(r['v027_recoveries'] for r in rows)}",
        f"Budget fully consumed         : {sum(r['v027_trials'] == args.budget for r in rows)}/{len(rows)}",
        "",
        "PER BENCHMARK",
    ]

    for spec in specs:
        sub = [r for r in rows if r["benchmark"] == spec.name]
        d = np.asarray(
            [r["v027_minus_legacy"] for r in sub],
            dtype=float,
        )
        lines.extend([
            spec.name,
            f"  Legacy mean                 : {np.mean([r['legacy'] for r in sub]):.4f}",
            f"  V0.2.7 mean                 : {np.mean([r['v027'] for r in sub]):.4f}",
            f"  Mean delta                  : {np.mean(d):+.4f}",
            f"  Equal/better Legacy         : {np.mean(d >= -1e-10)*100:.1f}%",
        ])

    lines.extend([
        "",
        "INTERPRETATION",
        "- V0.2.7 must first recover the performance lost in V0.2.6.",
        "- A positive suite-wide delta is more important than one spectacular seed.",
        "- If V0.2.7 is only equal to Legacy, keep Legacy and simplify.",
        "- Only add complexity that produces measurable robustness.",
        "",
        "NOTE: synthetic optimizer validation only.",
        "=" * 98,
    ])

    summary = "\n".join(lines)
    print()
    print(summary)

    (out_dir / "summary.txt").write_text(summary, encoding="utf-8")

    with (out_dir / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(111)
    ax.bar(
        range(1, len(delta) + 1),
        delta,
    )
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Suite case")
    ax.set_ylabel("V0.2.7 - Legacy final score")
    ax.set_title("V0.2.7 Conservative Robustness vs Legacy")
    ax.grid(True, axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(
        out_dir / "v027_vs_legacy.png",
        dpi=170,
    )
    plt.close(fig)

    print()
    print(f"Saved results: {out_dir}")


if __name__ == "__main__":
    main()
