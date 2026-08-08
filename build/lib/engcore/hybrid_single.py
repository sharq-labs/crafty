from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .constraint_adapter import with_continuous_constraints
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--benchmark",
        default="multimodal",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=601,
    )
    p.add_argument(
        "--budget",
        type=int,
        default=40,
    )
    p.add_argument(
        "--initial",
        type=int,
        default=12,
    )
    p.add_argument(
        "--search",
        choices=["discrete", "hybrid"],
        default="hybrid",
    )
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
        "--constraint-mode",
        choices=["penalty", "margins"],
        default="penalty",
    )
    args = p.parse_args()

    if args.initial >= args.budget:
        raise SystemExit(
            "--initial must be smaller than --budget"
        )

    spec = get_benchmark(
        args.benchmark
    )

    evaluator = (
        with_continuous_constraints(
            spec.name,
            spec.evaluator,
        )
        if args.constraint_mode
        == "margins"
        else spec.evaluator
    )

    engine = HybridLogEIEngine(
        design_space=make_space(),
        evaluator=evaluator,
        seed=args.seed,
        screen_device=(
            args.screen_device
        ),
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=args.initial,
        smart_trials=(
            args.budget
            - args.initial
        ),
        search_mode=args.search,
        verbose=True,
        **get_hybrid_mode(
            args.mode
        ),
    )
    wall = (
        time.perf_counter()
        - t0
    )

    print("=" * 96)
    print(
        "Engineering AI Core V0.2.9 — "
        "Global-First Hybrid"
    )
    print("=" * 96)
    print(
        f"Benchmark                : {spec.name}"
    )
    print(
        f"Seed                     : {args.seed}"
    )
    print(
        f"Search mode              : {args.search}"
    )
    print(
        f"Quality mode             : {args.mode}"
    )
    print(
        f"Constraint mode          : {args.constraint_mode}"
    )
    print(
        f"GP / refinement device  : {result['fit_device']}"
    )
    print(
        f"Screen device            : {result['screen_device']}"
    )
    print(
        f"Trials                   : {result['trials_run']}"
    )
    print(
        f"Best score               : {result['best'].score:.6f}"
    )
    print(
        f"Wall time                : {wall:.3f} s"
    )
    print("")
    print("Timing")
    for key, value in result[
        "timings"
    ].items():
        print(
            f"  {key:29s}: "
            f"{value:.3f} s"
        )

    print("")
    print("Diagnostics")
    for key, value in result[
        "fit_diagnostics"
    ].items():
        print(
            f"  {key:29s}: "
            f"{value}"
        )

    if result["gpu_memory"]:
        print("")
        print("GPU memory")
        for key, value in result[
            "gpu_memory"
        ].items():
            print(
                f"  {key:29s}: "
                f"{value:.2f}"
            )

    print("=" * 96)


if __name__ == "__main__":
    main()
