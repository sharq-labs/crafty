from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .adaptive_hybrid_engine import AdaptiveHybridLogEIEngine
from .adaptive_modes import get_adaptive_mode


CASES = [
    ("multimodal", 601),
    ("narrow_optimum", 215),
    ("deceptive_local", 213),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--budget", type=int, default=80)
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
    args = p.parse_args()

    print("=" * 108)
    print("Engineering AI Core V0.2.9.1 — Adaptive Focused Check")
    print("=" * 108)

    for name, seed in CASES:
        spec = get_benchmark(name)

        engine = AdaptiveHybridLogEIEngine(
            make_space(),
            spec.evaluator,
            seed=seed,
            screen_device=args.screen_device,
            noise_mode=args.noise,
            kernel_name=args.kernel,
        )

        t0 = time.perf_counter()
        result = engine.run(
            initial_trials=args.initial,
            smart_trials=args.budget - args.initial,
            verbose=False,
            **get_adaptive_mode(args.mode),
        )
        wall = time.perf_counter() - t0
        d = result["fit_diagnostics"]

        print(
            f"{name:20s} "
            f"seed={seed:<4d} "
            f"score={result['best'].score:10.4f} "
            f"wall={wall:7.2f}s "
            f"fits={d['optimized_fits']:2d} "
            f"fail={d['fit_failures']:2d} "
            f"ref={d['refinement_selected']:2d} "
            f"forceD={d['forced_discrete_selections']:2d} "
            f"unc={d['uncertainty_exploration_selections']:2d} "
            f"pulse={d['stagnation_pulses']:2d}"
        )

    print("=" * 108)


if __name__ == "__main__":
    main()
