from __future__ import annotations

import argparse
import time
import numpy as np

from .benchmark import make_space
from .hard_domain import hard_cooling_benchmark
from .sampling import sobol_points
from .gpu_surrogate import TorchBotorchSurrogate, describe_device


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=64)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument(
        "--pools",
        default="10000,50000,100000,250000,500000",
    )
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    pools = [
        int(v.strip())
        for v in args.pools.split(",")
        if v.strip()
    ]

    space = make_space()
    X = sobol_points(args.train, space.dim, args.seed)

    y = np.asarray([
        hard_cooling_benchmark(
            space.denormalize(p)
        )[0]
        for p in X
    ], dtype=np.float64)

    surrogate = TorchBotorchSurrogate(
        space.dim, force_cpu=args.cpu
    )
    device = describe_device(surrogate.device)

    t0 = time.perf_counter()
    fit_info = surrogate.fit(X, y, optimize=True)
    surrogate.synchronize()
    fit_s = time.perf_counter() - t0

    best_y = float(np.max(y))

    print("=" * 78)
    print("Engineering AI Core V0.2.4 — GPU Throughput")
    print("=" * 78)
    print(f"Device       : {device.name}")
    print(f"CUDA         : {device.cuda}")
    print(f"Train points : {args.train}")
    print(f"Chunk        : {args.chunk}")
    print(f"Initial fit  : {fit_s:.3f} s")
    print(f"Fit fallback : {fit_info.fallback_used}")
    print("")
    print(f"{'Pool':>12} {'Seconds':>12} {'Candidates/sec':>20}")

    for pool_size in pools:
        candidates = sobol_points(
            pool_size,
            space.dim,
            args.seed + pool_size,
        )

        surrogate.reset_peak_memory()

        t0 = time.perf_counter()
        scores = surrogate.expected_improvement_scores(
            candidates,
            best_y=best_y,
            chunk_size=args.chunk,
        )
        surrogate.synchronize()
        elapsed = time.perf_counter() - t0

        rate = pool_size / elapsed if elapsed else 0.0
        print(
            f"{pool_size:12,d} "
            f"{elapsed:12.4f} "
            f"{rate:20,.0f}"
        )

        del candidates, scores
        surrogate.empty_cache()

    print("")
    print("Peak memory from final pass:")
    for key, value in surrogate.memory_stats().items():
        print(f"  {key:22s}: {value:.1f} MB")
    print("=" * 78)


if __name__ == "__main__":
    main()
