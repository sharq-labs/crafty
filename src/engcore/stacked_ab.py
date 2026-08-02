from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .gpu_engine import GPUSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode


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
        default=80,
    )
    p.add_argument(
        "--initial",
        type=int,
        default=12,
    )
    p.add_argument(
        "--legacy-pool",
        type=int,
        default=100000,
    )
    p.add_argument(
        "--chunk",
        type=int,
        default=1024,
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

    spec = get_benchmark(
        args.benchmark
    )
    smart_trials = (
        args.budget
        - args.initial
    )

    # Legacy
    legacy = GPUSmartExperimentEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        force_cpu=False,
    )
    t0 = time.perf_counter()
    legacy_r = legacy.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        candidate_pool=(
            args.legacy_pool
        ),
        candidate_chunk_size=args.chunk,
        patience=max(
            1000,
            args.budget,
        ),
        refit_interval=4,
    )
    legacy_t = (
        time.perf_counter()
        - t0
    )

    # V0.2.7
    v027 = ConservativeRobustEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        force_cpu=False,
    )
    t0 = time.perf_counter()
    v027_r = v027.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        candidate_pool=(
            args.legacy_pool
        ),
        candidate_chunk_size=args.chunk,
        refit_interval=4,
    )
    v027_t = (
        time.perf_counter()
        - t0
    )

    # V0.2.9 hybrid
    v029 = HybridLogEIEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        screen_device=(
            args.screen_device
        ),
    )
    t0 = time.perf_counter()
    v029_r = v029.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        search_mode="hybrid",
        verbose=False,
        **get_hybrid_mode(
            args.mode
        ),
    )
    v029_t = (
        time.perf_counter()
        - t0
    )

    # V0.3.0.1 stacked
    v030 = StackedGPBOEngine(
        make_space(),
        spec.evaluator,
        seed=args.seed,
        screen_device=(
            args.screen_device
        ),
    )
    t0 = time.perf_counter()
    v030_r = v030.run(
        initial_trials=args.initial,
        smart_trials=smart_trials,
        verbose=False,
        **get_stacked_mode(
            args.mode
        ),
    )
    v030_t = (
        time.perf_counter()
        - t0
    )

    scores = {
        "Legacy":
            float(
                legacy_r["best"].score
            ),
        "V0.2.7":
            float(
                v027_r["best"].score
            ),
        "V0.2.9 hybrid":
            float(
                v029_r["best"].score
            ),
        "V0.3.0.1 stacked":
            float(
                v030_r["best"].score
            ),
    }

    winner = max(
        scores,
        key=scores.get,
    )

    print("=" * 112)
    print(
        "Engineering AI Core V0.3.0.1 — "
        "Focused A/B/C/D"
    )
    print("=" * 112)
    print(
        f"Benchmark              : {spec.name}"
    )
    print(
        f"Seed                   : {args.seed}"
    )
    print(
        f"Budget                 : {args.budget}"
    )
    print("")
    for name, score in scores.items():
        print(
            f"{name:22s}: "
            f"{score:.6f}"
        )

    print("")
    print(
        f"V0.3.0.1 - Legacy        : "
        f"{scores['V0.3.0.1 stacked'] - scores['Legacy']:+.6f}"
    )
    print(
        f"V0.3.0.1 - V0.2.7        : "
        f"{scores['V0.3.0.1 stacked'] - scores['V0.2.7']:+.6f}"
    )
    print(
        f"V0.3.0.1 - V0.2.9 hybrid : "
        f"{scores['V0.3.0.1 stacked'] - scores['V0.2.9 hybrid']:+.6f}"
    )
    print(
        f"Winner                 : {winner}"
    )
    print("")
    print(
        f"Legacy wall            : {legacy_t:.3f} s"
    )
    print(
        f"V0.2.7 wall            : {v027_t:.3f} s"
    )
    print(
        f"V0.2.9 hybrid wall     : {v029_t:.3f} s"
    )
    print(
        f"V0.3.0.1 stacked wall    : {v030_t:.3f} s"
    )
    print("")
    print(
        f"V0.3.0.1 final weights   : "
        f"RBF={v030_r['final_weight_rbf']:.3f}, "
        f"Matern={v030_r['final_weight_matern']:.3f}"
    )
    print("=" * 112)


if __name__ == "__main__":
    main()
