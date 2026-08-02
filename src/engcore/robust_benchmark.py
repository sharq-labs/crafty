from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .robust_engine import RobustSmartExperimentEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="deceptive_local")
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=213)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--regions", type=int, default=3)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    spec = get_benchmark(args.benchmark)
    space = make_space()

    initial = min(24, max(12, args.budget // 3))
    smart_trials = args.budget - initial

    engine = RobustSmartExperimentEngine(
        space,
        spec.evaluator,
        seed=args.seed,
        force_cpu=args.cpu,
        n_regions=args.regions,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=args.pool,
        candidate_chunk_size=args.chunk,
        refit_interval=args.refit_interval,
    )
    wall = time.perf_counter() - t0

    print("=" * 88)
    print("Engineering AI Core V0.2.6 — Robust Autonomous Optimizer")
    print("=" * 88)
    print(f"Benchmark                 : {spec.name}")
    print(f"Description               : {spec.description}")
    print(f"Device                    : {result['device'].name}")
    print(f"CUDA active               : {result['device'].cuda}")
    print(f"Budget                    : {args.budget}")
    print(f"Base candidate pool       : {args.pool:,}")
    print(f"Trust regions             : {args.regions}")
    print(f"Refit interval            : {args.refit_interval}")
    print(f"Experiments run           : {result['trials_run']}")
    print(f"Best score                : {result['best'].score:.6f}")
    print(f"Wall time                 : {wall:.3f} s")
    print("")
    print("Best design")
    for key, value in space.as_dict(result["best"].x).items():
        print(f"  {key:24s}: {value:.4f}")
    print("")
    pos = result["best"].metadata.get("normalized_position", [])
    if pos:
        print("Normalized position:")
        print("  " + ", ".join(f"{v:.3f}" for v in pos))
    print("")
    print("Timing")
    for key, value in result["timings"].items():
        print(f"  {key:24s}: {value:.3f} s")
    print("")
    print("Fit diagnostics")
    for key, value in result["fit_diagnostics"].items():
        print(f"  {key:24s}: {value}")
    print("")
    recoveries = [
        e for e in result["events"]
        if e.get("event") == "stagnation_recovery"
    ]
    print(f"Stagnation recoveries     : {len(recoveries)}")
    print("Final trust-region radii  : " + ", ".join(
        f"{r['radius']:.3f}" for r in result["regions"]
    ))
    print("=" * 88)

    out = Path("v026_results")
    out.mkdir(exist_ok=True)
    (out / f"{spec.name}_seed_{args.seed}_events.json").write_text(
        json.dumps(result["events"], indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
