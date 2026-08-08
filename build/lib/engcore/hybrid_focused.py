from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode


CASES = [
    ("multimodal", 601),
    ("narrow_optimum", 215),
    ("deceptive_local", 213),
]


def main():
    p = argparse.ArgumentParser()
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
    args = p.parse_args()

    print("=" * 96)
    print(
        "Engineering AI Core V0.2.9 — "
        "Focused Three-Problem Check"
    )
    print("=" * 96)

    for name, seed in CASES:
        spec = get_benchmark(name)
        engine = HybridLogEIEngine(
            make_space(),
            spec.evaluator,
            seed=seed,
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
            verbose=False,
            **get_hybrid_mode(
                args.mode
            ),
        )
        wall = (
            time.perf_counter()
            - t0
        )

        d = result[
            "fit_diagnostics"
        ]

        print(
            f"{name:20s} "
            f"seed={seed:<4d} "
            f"score={result['best'].score:10.4f} "
            f"wall={wall:7.2f}s "
            f"fits={d['optimized_fits']:2d} "
            f"fail={d['fit_failures']:2d} "
            f"refSel={d['refinement_selected']:2d} "
            f"discSel={d['discrete_selected']:2d} "
            f"pulses={d['stagnation_pulses']:2d}"
        )

    print("=" * 96)


if __name__ == "__main__":
    main()
