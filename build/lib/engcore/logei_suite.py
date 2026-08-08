from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np
from scipy import stats

from .benchmark import make_space
from .benchmark_suite import BENCHMARKS
from .constraint_adapter import with_continuous_constraints
from .sampling import sobol_points
from .gpu_engine import GPUSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine
from .logei_engine import LogEIGlobalLocalEngine
from .logei_modes import get_mode


def baseline(space, evaluator, points):
    best = -np.inf
    for p in points:
        score, feasible, _ = evaluator(
            space.denormalize(p)
        )
        if feasible and score > best:
            best = float(score)
    return best


def bootstrap_ci(values, samples=5000, seed=20282):
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
    p = argparse.ArgumentParser()
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--budget", type=int, default=80)
    p.add_argument("--initial", type=int, default=12)
    p.add_argument("--legacy-pool", type=int, default=75000)
    p.add_argument("--chunk", type=int, default=1024)
    p.add_argument(
        "--mode",
        choices=["fast", "balanced", "quality"],
        default="balanced",
    )
    p.add_argument(
        "--device",
        choices=["cpu", "cuda", "auto"],
        default="cpu",
    )
    p.add_argument(
        "--constraint-mode",
        choices=["penalty", "margins"],
        default="penalty",
    )
    p.add_argument("--start-seed", type=int, default=600)
    args = p.parse_args()

    if args.initial >= args.budget:
        raise SystemExit("--initial must be smaller than --budget")

    out_dir = Path("v0282_suite_results")
    out_dir.mkdir(exist_ok=True)

    rows = []
    total = len(BENCHMARKS) * args.runs
    done = 0
    all_t0 = time.perf_counter()

    print("=" * 106)
    print("Engineering AI Core V0.2.8.3 — Fair Custom Suite")
    print("=" * 106)
    print(f"Runs / benchmark : {args.runs}")
    print(f"Budget           : {args.budget}")
    print(f"Initial          : {args.initial}")
    print(f"Mode             : {args.mode}")
    print(f"V0.2.8.3 device  : {args.device}")
    print(f"Constraint mode  : {args.constraint_mode}")
    print("")

    for spec in BENCHMARKS:
        for i in range(args.runs):
            seed = args.start_seed + i
            space = make_space()

            rng = np.random.default_rng(seed)
            random_score = baseline(
                space,
                spec.evaluator,
                rng.random((args.budget, space.dim)),
            )
            sobol_score = baseline(
                space,
                spec.evaluator,
                sobol_points(
                    args.budget,
                    space.dim,
                    seed,
                ),
            )

            smart_trials = args.budget - args.initial

            legacy = GPUSmartExperimentEngine(
                space,
                spec.evaluator,
                seed=seed,
                force_cpu=False,
            )
            legacy_result = legacy.run(
                initial_trials=args.initial,
                smart_trials=smart_trials,
                candidate_pool=args.legacy_pool,
                candidate_chunk_size=args.chunk,
                patience=max(1000, args.budget),
                refit_interval=4,
            )

            v027 = ConservativeRobustEngine(
                space,
                spec.evaluator,
                seed=seed,
                force_cpu=False,
            )
            v027_result = v027.run(
                initial_trials=args.initial,
                smart_trials=smart_trials,
                candidate_pool=args.legacy_pool,
                candidate_chunk_size=args.chunk,
                refit_interval=4,
            )

            evaluator_v028 = (
                with_continuous_constraints(
                    spec.name,
                    spec.evaluator,
                )
                if args.constraint_mode == "margins"
                else spec.evaluator
            )

            v028 = LogEIGlobalLocalEngine(
                space,
                evaluator_v028,
                seed=seed,
                device=args.device,
            )

            t0 = time.perf_counter()
            v028_result = v028.run(
                initial_trials=args.initial,
                smart_trials=smart_trials,
                verbose=False,
                **get_mode(args.mode),
            )
            v028_wall = time.perf_counter() - t0

            values = {
                "random": float(random_score),
                "sobol": float(sobol_score),
                "legacy": float(legacy_result["best"].score),
                "v027": float(v027_result["best"].score),
                "v0282": float(v028_result["best"].score),
            }

            winner = max(values, key=values.get)
            diag = v028_result["fit_diagnostics"]

            row = {
                "benchmark": spec.name,
                "seed": seed,
                **values,
                "v0282_minus_legacy":
                    values["v0282"] - values["legacy"],
                "v0282_minus_v027":
                    values["v0282"] - values["v027"],
                "winner": winner,
                "v0282_wall_s": v028_wall,
                "fit_failures": diag["fit_failures"],
                "fit_rollbacks": diag["fit_rollbacks"],
                "global_opt_failures":
                    diag["global_opt_failures"],
                "duplicates": diag["duplicate_candidates"],
                "duplicate_recoveries":
                    diag["duplicate_recoveries"],
                "stagnation_pulses":
                    diag["stagnation_pulses"],
            }
            rows.append(row)
            done += 1

            print(
                f"[{done:02d}/{total}] {spec.name:20s} seed={seed} "
                f"R={values['random']:.2f} "
                f"S={values['sobol']:.2f} "
                f"L={values['legacy']:.2f} "
                f"27={values['v027']:.2f} "
                f"282={values['v0282']:.2f} "
                f"ΔL={row['v0282_minus_legacy']:+.2f} "
                f"winner={winner}"
            )

    total_wall = time.perf_counter() - all_t0

    delta_l = np.asarray(
        [r["v0282_minus_legacy"] for r in rows],
        dtype=float,
    )
    delta_27 = np.asarray(
        [r["v0282_minus_v027"] for r in rows],
        dtype=float,
    )

    ci_l = bootstrap_ci(delta_l)

    try:
        p_l = float(stats.wilcoxon(
            [r["v0282"] for r in rows],
            [r["legacy"] for r in rows],
            alternative="greater",
            zero_method="wilcox",
        ).pvalue)
    except Exception:
        p_l = float("nan")

    winners = {
        name: sum(r["winner"] == name for r in rows)
        for name in ["random", "sobol", "legacy", "v027", "v0282"]
    }

    lines = [
        "=" * 106,
        "Engineering AI Core V0.2.8.3 — Suite Summary",
        "=" * 106,
        f"Cases                         : {len(rows)}",
        f"Total wall time               : {total_wall:.3f} s",
        f"Constraint mode               : {args.constraint_mode}",
        "",
        "OVERALL WIN COUNT",
        f"V0.2.8.3 wins                 : {winners['v0282']}/{len(rows)} ({100*winners['v0282']/len(rows):.1f}%)",
        f"V0.2.7 wins                   : {winners['v027']}/{len(rows)} ({100*winners['v027']/len(rows):.1f}%)",
        f"Legacy wins                   : {winners['legacy']}/{len(rows)} ({100*winners['legacy']/len(rows):.1f}%)",
        f"Random wins                   : {winners['random']}/{len(rows)} ({100*winners['random']/len(rows):.1f}%)",
        f"Sobol wins                    : {winners['sobol']}/{len(rows)} ({100*winners['sobol']/len(rows):.1f}%)",
        "",
        "V0.2.8.3 VS LEGACY",
        f"Mean advantage                : {np.mean(delta_l):+.6f}",
        f"Median advantage              : {np.median(delta_l):+.6f}",
        f"95% bootstrap CI              : [{ci_l[0]:+.6f}, {ci_l[1]:+.6f}]",
        f"Better than Legacy            : {100*np.mean(delta_l > 1e-10):.1f}%",
        f"Equal/better Legacy           : {100*np.mean(delta_l >= -1e-10):.1f}%",
        f"Wilcoxon p                    : {p_l}",
        "",
        "V0.2.8.3 VS V0.2.7",
        f"Mean advantage                : {np.mean(delta_27):+.6f}",
        f"Median advantage              : {np.median(delta_27):+.6f}",
        "",
        "DIAGNOSTICS",
        f"Fit failures                  : {sum(r['fit_failures'] for r in rows)}",
        f"Fit rollbacks                 : {sum(r['fit_rollbacks'] for r in rows)}",
        f"Global opt failures           : {sum(r['global_opt_failures'] for r in rows)}",
        f"Duplicate candidates          : {sum(r['duplicates'] for r in rows)}",
        f"Duplicate recoveries          : {sum(r['duplicate_recoveries'] for r in rows)}",
        f"Stagnation pulses             : {sum(r['stagnation_pulses'] for r in rows)}",
        "",
        "NOTE: synthetic optimizer validation only; not validated engineering physics.",
        "=" * 106,
    ]

    summary = "\n".join(lines)
    print()
    print(summary)

    (out_dir / "summary.txt").write_text(
        summary,
        encoding="utf-8",
    )

    with (out_dir / "runs.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    print()
    print(f"Saved results: {out_dir}")


if __name__ == "__main__":
    main()
