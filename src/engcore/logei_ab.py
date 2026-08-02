from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .constraint_adapter import with_continuous_constraints
from .gpu_engine import GPUSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine
from .logei_engine import LogEIGlobalLocalEngine
from .logei_modes import get_mode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--benchmark", default="multimodal")
    p.add_argument("--seed", type=int, default=601)
    p.add_argument("--budget", type=int, default=80)
    p.add_argument("--initial", type=int, default=12)
    p.add_argument("--legacy-pool", type=int, default=100000)
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
    args = p.parse_args()

    if args.initial >= args.budget:
        raise SystemExit("--initial must be smaller than --budget")

    spec = get_benchmark(args.benchmark)
    space = make_space()
    smart_trials = args.budget - args.initial

    legacy = GPUSmartExperimentEngine(
        space,
        spec.evaluator,
        seed=args.seed,
        force_cpu=False,
    )
    t0 = time.perf_counter()
    legacy_result = legacy.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        candidate_pool=args.legacy_pool,
        candidate_chunk_size=args.chunk,
        patience=max(1000, args.budget),
        refit_interval=4,
    )
    legacy_wall = time.perf_counter() - t0

    v027 = ConservativeRobustEngine(
        space,
        spec.evaluator,
        seed=args.seed,
        force_cpu=False,
    )
    t0 = time.perf_counter()
    v027_result = v027.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        candidate_pool=args.legacy_pool,
        candidate_chunk_size=args.chunk,
        refit_interval=4,
    )
    v027_wall = time.perf_counter() - t0

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
        seed=args.seed,
        device=args.device,
    )

    t0 = time.perf_counter()
    v028_result = v028.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        verbose=True,
        **get_mode(args.mode),
    )
    v028_wall = time.perf_counter() - t0

    s_l = float(legacy_result["best"].score)
    s_27 = float(v027_result["best"].score)
    s_28 = float(v028_result["best"].score)

    print("=" * 96)
    print("Engineering AI Core V0.2.8.3 — Focused A/B/C")
    print("=" * 96)
    print(f"Benchmark              : {spec.name}")
    print(f"Seed                   : {args.seed}")
    print(f"Budget                 : {args.budget}")
    print(f"Initial DOE            : {args.initial}")
    print(f"V0.2.8.3 mode          : {args.mode}")
    print(f"V0.2.8.3 device        : {v028_result['device']}")
    print(f"Constraint mode        : {args.constraint_mode}")
    print("")
    print(f"Legacy score           : {s_l:.6f}")
    print(f"V0.2.7 score           : {s_27:.6f}")
    print(f"V0.2.8.3 score         : {s_28:.6f}")
    print(f"V0.2.8.3 - Legacy      : {s_28 - s_l:+.6f}")
    print(f"V0.2.8.3 - V0.2.7      : {s_28 - s_27:+.6f}")
    print("")
    print(f"Legacy wall            : {legacy_wall:.3f} s")
    print(f"V0.2.7 wall            : {v027_wall:.3f} s")
    print(f"V0.2.8.3 wall          : {v028_wall:.3f} s")
    print("")
    print("V0.2.8.3 diagnostics")
    for key, value in v028_result["fit_diagnostics"].items():
        print(f"  {key:27s}: {value}")
    print("=" * 96)


if __name__ == "__main__":
    main()
