from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .constraint_adapter import with_continuous_constraints
from .logei_engine import LogEIGlobalLocalEngine
from .logei_modes import get_mode


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
        "--device",
        choices=["cpu", "cuda", "auto"],
        default="cpu",
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
        with_continuous_constraints(
            spec.name,
            spec.evaluator,
        )
        if args.constraint_mode == "margins"
        else spec.evaluator
    )

    engine = LogEIGlobalLocalEngine(
        make_space(),
        evaluator,
        seed=args.seed,
        device=args.device,
    )

    cfg = get_mode(args.mode)

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=args.initial,
        smart_trials=args.budget - args.initial,
        verbose=True,
        **cfg,
    )
    wall = time.perf_counter() - t0

    print("=" * 92)
    print("Engineering AI Core V0.2.8.3 — Single Engine")
    print("=" * 92)
    print(f"Benchmark              : {spec.name}")
    print(f"Seed                   : {args.seed}")
    print(f"Mode                   : {args.mode}")
    print(f"Constraint mode        : {args.constraint_mode}")
    print(f"Requested device       : {args.device}")
    print(f"Actual device          : {result['device']}")
    print(f"Trials                 : {result['trials_run']}")
    print(f"Best score             : {result['best'].score:.6f}")
    print(f"Wall time              : {wall:.3f} s")
    print("")
    print("Timing")
    for key, value in result["timings"].items():
        print(f"  {key:27s}: {value:.3f} s")
    print("")
    print("Diagnostics")
    for key, value in result["fit_diagnostics"].items():
        print(f"  {key:27s}: {value}")
    print("=" * 92)


if __name__ == "__main__":
    main()
