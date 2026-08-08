from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from .sampling import sobol_points
from .gpu_engine import GPUSmartExperimentEngine
from .logei_engine import LogEIGlobalLocalEngine
from .standard_benchmarks import (
    STANDARD_BENCHMARKS,
    make_unit_space,
)


def baseline(space, evaluator, points):
    best = -np.inf
    for p in points:
        score, feasible, _ = evaluator(
            space.denormalize(p)
        )
        if feasible and score > best:
            best = max(best, float(score))
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--budget", type=int, default=60)
    parser.add_argument("--initial", type=int, default=12)
    parser.add_argument("--legacy-pool", type=int, default=75000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--global-restarts", type=int, default=20)
    parser.add_argument("--global-raw", type=int, default=512)
    parser.add_argument("--guard", type=int, default=4096)
    parser.add_argument("--start-seed", type=int, default=1000)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    args = parser.parse_args()

    out_dir = Path("v028_standard_results")
    out_dir.mkdir(exist_ok=True)

    rows = []
    total = len(STANDARD_BENCHMARKS) * args.runs
    done = 0

    print("=" * 96)
    print("Engineering AI Core V0.2.8 — Independent Standard Benchmark Suite")
    print("=" * 96)
    print(f"Functions        : {[b.name for b in STANDARD_BENCHMARKS]}")
    print(f"Runs / function  : {args.runs}")
    print(f"Budget           : {args.budget}")
    print(f"Initial DOE      : {args.initial}")
    print("")

    for spec in STANDARD_BENCHMARKS:
        for i in range(args.runs):
            seed = args.start_seed + i
            space = make_unit_space(dim=4)

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
                refit_interval=args.refit_interval,
            )

            v028 = LogEIGlobalLocalEngine(
                space,
                spec.evaluator,
                seed=seed,
                force_cpu=False,
            )
            v028_result = v028.run(
                initial_trials=args.initial,
                smart_trials=smart_trials,
                refit_interval=args.refit_interval,
                global_restarts=args.global_restarts,
                global_raw_samples=args.global_raw,
                fallback_guard_points=args.guard,
            )

            values = {
                "random": float(random_score),
                "sobol": float(sobol_score),
                "legacy": float(legacy_result["best"].score),
                "v028": float(v028_result["best"].score),
            }
            winner = max(values, key=values.get)

            row = {
                "benchmark": spec.name,
                "seed": seed,
                **values,
                "v028_minus_legacy":
                    values["v028"] - values["legacy"],
                "winner": winner,
                "fit_failures":
                    v028_result["fit_diagnostics"]["fit_failures"],
            }
            rows.append(row)
            done += 1

            print(
                f"[{done:02d}/{total}] {spec.name:18s} seed={seed} "
                f"R={values['random']:.3f} "
                f"S={values['sobol']:.3f} "
                f"L={values['legacy']:.3f} "
                f"28={values['v028']:.3f} "
                f"ΔL={row['v028_minus_legacy']:+.3f} "
                f"winner={winner}"
            )

    delta = np.asarray(
        [r["v028_minus_legacy"] for r in rows],
        dtype=float,
    )

    v028_wins = sum(r["winner"] == "v028" for r in rows)

    lines = [
        "=" * 96,
        "V0.2.8 Standard Suite Summary",
        "=" * 96,
        f"Cases                     : {len(rows)}",
        f"V0.2.8 overall wins       : {v028_wins}/{len(rows)} ({100*v028_wins/len(rows):.1f}%)",
        f"Mean V0.2.8 - Legacy      : {np.mean(delta):+.6f}",
        f"Median V0.2.8 - Legacy    : {np.median(delta):+.6f}",
        f"Better than Legacy        : {100*np.mean(delta > 1e-10):.1f}%",
        f"Equal/better Legacy       : {100*np.mean(delta >= -1e-10):.1f}%",
        f"Fit failures              : {sum(r['fit_failures'] for r in rows)}",
        "",
        "PER FUNCTION",
    ]

    for spec in STANDARD_BENCHMARKS:
        sub = [r for r in rows if r["benchmark"] == spec.name]
        d = [r["v028_minus_legacy"] for r in sub]
        lines.extend([
            spec.name,
            f"  Legacy mean             : {np.mean([r['legacy'] for r in sub]):.6f}",
            f"  V0.2.8 mean             : {np.mean([r['v028'] for r in sub]):.6f}",
            f"  Mean delta              : {np.mean(d):+.6f}",
        ])

    summary = "\n".join(lines)
    print()
    print(summary)

    (out_dir / "summary.txt").write_text(
        summary,
        encoding="utf-8",
    )

    with (out_dir / "runs.csv").open(
        "w", newline="", encoding="utf-8"
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
