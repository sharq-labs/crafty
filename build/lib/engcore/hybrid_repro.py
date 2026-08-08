from __future__ import annotations

import argparse
import numpy as np

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode


def run_once(spec, args):
    engine = HybridLogEIEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        screen_device=(
            args.screen_device
        ),
    )

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

    xs = np.asarray(
        engine.x01_history,
        dtype=float,
    )
    ys = np.asarray(
        [
            r.score
            for r in engine.history
        ],
        dtype=float,
    )

    return result, xs, ys


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
        default=20,
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
        default="fast",
    )
    p.add_argument(
        "--screen-device",
        choices=["cpu", "cuda", "auto"],
        default="auto",
    )
    args = p.parse_args()

    spec = get_benchmark(
        args.benchmark
    )

    r1, x1, y1 = run_once(
        spec,
        args,
    )
    r2, x2, y2 = run_once(
        spec,
        args,
    )

    same_x = np.array_equal(
        x1,
        x2,
    )
    same_y = np.array_equal(
        y1,
        y2,
    )

    max_dx = (
        float(
            np.max(
                np.abs(x1 - x2)
            )
        )
        if x1.shape == x2.shape
        else float("inf")
    )
    max_dy = (
        float(
            np.max(
                np.abs(y1 - y2)
            )
        )
        if y1.shape == y2.shape
        else float("inf")
    )

    print("=" * 88)
    print(
        "V0.2.9 Hybrid Reproducibility"
    )
    print("=" * 88)
    print(
        f"Benchmark          : {spec.name}"
    )
    print(
        f"Search             : {args.search}"
    )
    print(
        f"Mode               : {args.mode}"
    )
    print(
        f"Screen device      : {args.screen_device}"
    )
    print(
        f"Exact X match      : {same_x}"
    )
    print(
        f"Exact score match  : {same_y}"
    )
    print(
        f"Max |ΔX|           : {max_dx:.12g}"
    )
    print(
        f"Max |Δscore|       : {max_dy:.12g}"
    )
    print(
        f"Run 1 best         : {r1['best'].score:.12f}"
    )
    print(
        f"Run 2 best         : {r2['best'].score:.12f}"
    )
    print("=" * 88)

    if not (
        same_x
        and same_y
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
