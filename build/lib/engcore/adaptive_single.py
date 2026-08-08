from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .constraint_adapter import with_continuous_constraints
from .adaptive_hybrid_engine import AdaptiveHybridLogEIEngine
from .adaptive_modes import get_adaptive_mode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--benchmark", default="multimodal")
    p.add_argument("--seed", type=int, default=601)
    p.add_argument("--budget", type=int, default=40)
    p.add_argument("--initial", type=int, default=12)
    p.add_argument(
        "--mode",
        choices=["fast", "balanced", "quality"],
        default="balanced",
    )
    p.add_argument(
        "--screen-device",
        choices=["cpu", "cuda", "auto"],
        default="auto",
    )
    p.add_argument(
        "--noise",
        choices=["fixed", "learned"],
        default="learned",
    )
    p.add_argument(
        "--kernel",
        choices=["rbf", "matern25"],
        default="rbf",
    )
    p.add_argument(
        "--constraint-mode",
        choices=["penalty", "margins"],
        default="penalty",
    )
    args = p.parse_args()

    if args.initial >= args.budget:
        raise SystemExit("--initial must be smaller than --budget")

    spec = get_benchmark(args.benchmark)

    evaluator = (
        with_continuous_constraints(spec.name, spec.evaluator)
        if args.constraint_mode == "margins"
        else spec.evaluator
    )

    engine = AdaptiveHybridLogEIEngine(
        design_space=make_space(),
        evaluator=evaluator,
        seed=args.seed,
        screen_device=args.screen_device,
        noise_mode=args.noise,
        kernel_name=args.kernel,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=args.initial,
        smart_trials=args.budget - args.initial,
        verbose=True,
        **get_adaptive_mode(args.mode),
    )
    wall = time.perf_counter() - t0

    print("=" * 100)
    print("Engineering AI Core V0.2.9.1 — Adaptive Hybrid")
    print("=" * 100)
    print(f"Benchmark                : {spec.name}")
    print(f"Seed                     : {args.seed}")
    print(f"Mode                     : {args.mode}")
    print(f"Noise                    : {result['noise_mode']}")
    print(f"Kernel                   : {result['kernel_name']}")
    print(f"Constraint mode          : {args.constraint_mode}")
    print(f"GP / refinement device  : {result['fit_device']}")
    print(f"Screen device            : {result['screen_device']}")
    print(f"Trials                   : {result['trials_run']}")
    print(f"Best score               : {result['best'].score:.6f}")
    print(f"Wall time                : {wall:.3f} s")
    print("")
    print("Timing")
    for key, value in result["timings"].items():
        print(f"  {key:33s}: {value:.3f} s")
    print("")
    print("Diagnostics")
    for key, value in result["fit_diagnostics"].items():
        print(f"  {key:33s}: {value}")
    print("=" * 100)


if __name__ == "__main__":
    main()
