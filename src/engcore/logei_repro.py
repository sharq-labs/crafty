from __future__ import annotations

import argparse
import numpy as np

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .logei_engine import LogEIGlobalLocalEngine
from .logei_modes import get_mode


def run_once(spec, args):
    engine = LogEIGlobalLocalEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        device=args.device,
    )
    result = engine.run(
        initial_trials=args.initial,
        smart_trials=args.budget - args.initial,
        verbose=False,
        **get_mode(args.mode),
    )

    xs = np.asarray(engine.x01_history, dtype=float)
    scores = np.asarray(
        [r.score for r in engine.history],
        dtype=float,
    )
    return result, xs, scores


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--benchmark", default="multimodal")
    p.add_argument("--seed", type=int, default=601)
    p.add_argument("--budget", type=int, default=24)
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
    args = p.parse_args()

    spec = get_benchmark(args.benchmark)

    r1, x1, y1 = run_once(spec, args)
    r2, x2, y2 = run_once(spec, args)

    same_x = np.array_equal(x1, x2)
    same_y = np.array_equal(y1, y2)

    max_x_diff = float(
        np.max(np.abs(x1 - x2))
    ) if x1.shape == x2.shape else float("inf")

    max_y_diff = float(
        np.max(np.abs(y1 - y2))
    ) if y1.shape == y2.shape else float("inf")

    print("=" * 82)
    print("V0.2.8.3 Reproducibility Check")
    print("=" * 82)
    print(f"Benchmark        : {spec.name}")
    print(f"Seed             : {args.seed}")
    print(f"Device           : {args.device}")
    print(f"Exact X match    : {same_x}")
    print(f"Exact score match: {same_y}")
    print(f"Max |ΔX|         : {max_x_diff:.12g}")
    print(f"Max |Δscore|     : {max_y_diff:.12g}")
    print(f"Run 1 best       : {r1['best'].score:.12f}")
    print(f"Run 2 best       : {r2['best'].score:.12f}")
    print("=" * 82)

    if not (same_x and same_y):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
