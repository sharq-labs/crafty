from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .gpu_engine import GPUSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode


def timed_hybrid(
    spec,
    seed,
    budget,
    initial,
    mode,
    screen_device,
    search_mode,
):
    engine = HybridLogEIEngine(
        make_space(),
        spec.evaluator,
        seed=seed,
        screen_device=screen_device,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=(
            budget - initial
        ),
        search_mode=search_mode,
        verbose=False,
        **get_hybrid_mode(mode),
    )
    wall = (
        time.perf_counter()
        - t0
    )

    return result, wall


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
        choices=["fast", "balanced", "quality"],
        default="balanced",
    )
    p.add_argument(
        "--screen-device",
        choices=["cpu", "cuda", "auto"],
        default="auto",
    )
    args = p.parse_args()

    if args.initial >= args.budget:
        raise SystemExit(
            "--initial must be smaller than --budget"
        )

    spec = get_benchmark(
        args.benchmark
    )
    space = make_space()
    smart_trials = (
        args.budget
        - args.initial
    )

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
        candidate_pool=(
            args.legacy_pool
        ),
        candidate_chunk_size=(
            args.chunk
        ),
        patience=max(
            1000,
            args.budget,
        ),
        refit_interval=4,
    )
    legacy_wall = (
        time.perf_counter()
        - t0
    )

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
        candidate_pool=(
            args.legacy_pool
        ),
        candidate_chunk_size=(
            args.chunk
        ),
        refit_interval=4,
    )
    v027_wall = (
        time.perf_counter()
        - t0
    )

    discrete_result, discrete_wall = (
        timed_hybrid(
            spec=spec,
            seed=args.seed,
            budget=args.budget,
            initial=args.initial,
            mode=args.mode,
            screen_device=(
                args.screen_device
            ),
            search_mode="discrete",
        )
    )

    hybrid_result, hybrid_wall = (
        timed_hybrid(
            spec=spec,
            seed=args.seed,
            budget=args.budget,
            initial=args.initial,
            mode=args.mode,
            screen_device=(
                args.screen_device
            ),
            search_mode="hybrid",
        )
    )

    scores = {
        "Legacy": float(
            legacy_result["best"].score
        ),
        "V0.2.7": float(
            v027_result["best"].score
        ),
        "V0.2.9 discrete": float(
            discrete_result["best"].score
        ),
        "V0.2.9 hybrid": float(
            hybrid_result["best"].score
        ),
    }

    winner = max(
        scores,
        key=scores.get,
    )

    print("=" * 104)
    print(
        "Engineering AI Core V0.2.9 — "
        "Global Screening / Refinement A/B"
    )
    print("=" * 104)
    print(
        f"Benchmark              : {spec.name}"
    )
    print(
        f"Seed                   : {args.seed}"
    )
    print(
        f"Budget                 : {args.budget}"
    )
    print(
        f"Initial DOE            : {args.initial}"
    )
    print(
        f"Mode                   : {args.mode}"
    )
    print(
        f"Screen device          : {hybrid_result['screen_device']}"
    )
    print("")
    print(
        f"Legacy score           : {scores['Legacy']:.6f}"
    )
    print(
        f"V0.2.7 score           : {scores['V0.2.7']:.6f}"
    )
    print(
        f"V0.2.9 discrete score  : {scores['V0.2.9 discrete']:.6f}"
    )
    print(
        f"V0.2.9 hybrid score    : {scores['V0.2.9 hybrid']:.6f}"
    )
    print("")
    print(
        f"Hybrid - Legacy        : "
        f"{scores['V0.2.9 hybrid'] - scores['Legacy']:+.6f}"
    )
    print(
        f"Hybrid - V0.2.7        : "
        f"{scores['V0.2.9 hybrid'] - scores['V0.2.7']:+.6f}"
    )
    print(
        f"Hybrid - Discrete      : "
        f"{scores['V0.2.9 hybrid'] - scores['V0.2.9 discrete']:+.6f}"
    )
    print(
        f"Winner                 : {winner}"
    )
    print("")
    print(
        f"Legacy wall            : {legacy_wall:.3f} s"
    )
    print(
        f"V0.2.7 wall            : {v027_wall:.3f} s"
    )
    print(
        f"V0.2.9 discrete wall   : {discrete_wall:.3f} s"
    )
    print(
        f"V0.2.9 hybrid wall     : {hybrid_wall:.3f} s"
    )
    print("")
    print("V0.2.9 hybrid diagnostics")
    for key in [
        "optimized_fits",
        "fit_failures",
        "screen_candidates_scored",
        "screen_chunk_reductions",
        "refinement_attempts",
        "refinement_failures",
        "refinement_selected",
        "discrete_selected",
        "duplicate_candidates",
        "stagnation_pulses",
    ]:
        print(
            f"  {key:29s}: "
            f"{hybrid_result['fit_diagnostics'].get(key, 0)}"
        )

    print("=" * 104)


if __name__ == "__main__":
    main()
