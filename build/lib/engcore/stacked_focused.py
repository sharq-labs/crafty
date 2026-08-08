from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode


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
        default=80,
    )
    p.add_argument(
        "--initial",
        type=int,
        default=12,
    )
    p.add_argument(
        "--mode",
        choices=[
            "fast",
            "balanced",
            "quality",
        ],
        default="balanced",
    )
    p.add_argument(
        "--screen-device",
        choices=[
            "cpu",
            "cuda",
            "auto",
        ],
        default="auto",
    )
    args = p.parse_args()

    print("=" * 118)
    print(
        "Engineering AI Core V0.3.0.1 — "
        "Stacked-GP Focused Check"
    )
    print("=" * 118)

    for name, seed in CASES:
        spec = get_benchmark(name)

        engine = StackedGPBOEngine(
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
            verbose=False,
            **get_stacked_mode(
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
            f"wRBF={result['final_weight_rbf']:.3f} "
            f"wMat={result['final_weight_matern']:.3f} "
            f"loo={d['loo_updates']:2d} "
            f"looFail={d['loo_failures']:2d} "
            f"rbfFail={d['rbf_fit_failures']:2d} "
            f"matFail={d['matern25_fit_failures']:2d} "
            f"refSel={d['refinement_selected']:2d} "
            f"discSel={d['discrete_selected']:2d}"
        )

    print("=" * 118)


if __name__ == "__main__":
    main()
