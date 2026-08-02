from __future__ import annotations

import argparse
import numpy as np

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode


def run_once(spec, args):
    engine = StackedGPBOEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        screen_device=args.screen_device,
    )

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

    xs = np.asarray(
        engine.x01_history,
        dtype=np.float64,
    )
    ys = np.asarray(
        [
            r.score
            for r in engine.history
        ],
        dtype=np.float64,
    )
    ws = np.asarray(
        [
            x["weight_rbf"]
            for x
            in result["weight_history"]
        ],
        dtype=np.float64,
    )

    return result, xs, ys, ws


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
        "--mode",
        choices=[
            "fast",
            "balanced",
            "quality",
        ],
        default="fast",
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

    spec = get_benchmark(
        args.benchmark
    )

    r1, x1, y1, w1 = (
        run_once(spec, args)
    )
    r2, x2, y2, w2 = (
        run_once(spec, args)
    )

    same_x = np.array_equal(
        x1,
        x2,
    )
    same_y = np.array_equal(
        y1,
        y2,
    )
    same_w = np.array_equal(
        w1,
        w2,
    )

    print("=" * 92)
    print(
        "V0.3.0.1 Stacked-GP Reproducibility"
    )
    print("=" * 92)
    print(
        f"Benchmark           : {spec.name}"
    )
    print(
        f"Exact X match       : {same_x}"
    )
    print(
        f"Exact score match   : {same_y}"
    )
    print(
        f"Exact weight match  : {same_w}"
    )
    print(
        f"Run 1 best          : {r1['best'].score:.12f}"
    )
    print(
        f"Run 2 best          : {r2['best'].score:.12f}"
    )
    print(
        f"Run 1 final wRBF    : {r1['final_weight_rbf']:.12f}"
    )
    print(
        f"Run 2 final wRBF    : {r2['final_weight_rbf']:.12f}"
    )
    print("=" * 92)

    if not (
        same_x
        and same_y
        and same_w
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
