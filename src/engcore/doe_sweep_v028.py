from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from .benchmark import make_space
from .benchmark_suite import BENCHMARKS
from .constraint_adapter import with_continuous_constraints
from .logei_engine import LogEIGlobalLocalEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initials", default="8,12,16,24")
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--global-restarts", type=int, default=16)
    parser.add_argument("--global-raw", type=int, default=384)
    parser.add_argument("--guard", type=int, default=2048)
    parser.add_argument("--start-seed", type=int, default=1400)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="cpu")
    parser.add_argument("--constraint-mode", choices=["penalty", "margins"], default="penalty")
    args = parser.parse_args()

    initials = [
        int(v.strip())
        for v in args.initials.split(",")
        if v.strip()
    ]

    out_dir = Path("v028_doe_sweep")
    out_dir.mkdir(exist_ok=True)

    rows = []

    for initial in initials:
        if initial >= args.budget:
            continue

        for spec in BENCHMARKS:
            evaluator = (
                with_continuous_constraints(spec.name, spec.evaluator)
                if args.constraint_mode == "margins"
                else spec.evaluator
            )

            for i in range(args.runs):
                seed = args.start_seed + i
                space = make_space()

                engine = LogEIGlobalLocalEngine(
                    space,
                    evaluator,
                    seed=seed,
                    device=args.device,
                )
                result = engine.run(
                    initial_trials=initial,
                    smart_trials=args.budget - initial,
                    global_restarts=args.global_restarts,
                    global_raw_samples=args.global_raw,
                    fallback_guard_points=args.guard,
                )

                rows.append({
                    "initial": initial,
                    "benchmark": spec.name,
                    "seed": seed,
                    "score": float(result["best"].score),
                    "fit_failures":
                        result["fit_diagnostics"]["fit_failures"],
                })

                print(
                    f"initial={initial:2d} "
                    f"{spec.name:20s} "
                    f"seed={seed} "
                    f"score={result['best'].score:.3f}"
                )

    print()
    print("=" * 78)
    print("V0.2.8 Initial DOE Sweep")
    print("=" * 78)

    for initial in initials:
        sub = [r for r in rows if r["initial"] == initial]
        if not sub:
            continue
        print(
            f"Initial={initial:2d} "
            f"mean={np.mean([r['score'] for r in sub]):.6f} "
            f"median={np.median([r['score'] for r in sub]):.6f}"
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


if __name__ == "__main__":
    main()
