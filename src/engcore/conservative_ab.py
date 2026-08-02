from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .gpu_engine import GPUSmartExperimentEngine
from .conservative_robust_engine import ConservativeRobustEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="deceptive_local")
    parser.add_argument("--seed", type=int, default=213)
    parser.add_argument("--budget", type=int, default=80)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--refit-interval", type=int, default=4)
    args = parser.parse_args()

    spec = get_benchmark(args.benchmark)
    space = make_space()

    initial = min(24, max(12, args.budget // 3))
    smart_trials = args.budget - initial

    legacy = GPUSmartExperimentEngine(
        space, spec.evaluator, seed=args.seed
    )
    t0 = time.perf_counter()
    legacy_result = legacy.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=args.pool,
        candidate_chunk_size=args.chunk,
        patience=max(25, args.budget),
        refit_interval=args.refit_interval,
    )
    legacy_wall = time.perf_counter() - t0

    v027 = ConservativeRobustEngine(
        space, spec.evaluator, seed=args.seed
    )
    t0 = time.perf_counter()
    v027_result = v027.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=args.pool,
        candidate_chunk_size=args.chunk,
        refit_interval=args.refit_interval,
    )
    v027_wall = time.perf_counter() - t0

    print("=" * 82)
    print("Engineering AI Core V0.2.7 — Focused A/B")
    print("=" * 82)
    print(f"Benchmark          : {spec.name}")
    print(f"Seed               : {args.seed}")
    print(f"Budget             : {args.budget}")
    print("")
    print(f"Legacy score       : {legacy_result['best'].score:.6f}")
    print(f"V0.2.7 score       : {v027_result['best'].score:.6f}")
    print(f"Delta              : {v027_result['best'].score - legacy_result['best'].score:+.6f}")
    print("")
    print(f"Legacy wall        : {legacy_wall:.3f} s")
    print(f"V0.2.7 wall        : {v027_wall:.3f} s")
    print(f"Recovery pulses    : {v027_result['recovery_count']}")
    print(f"V0.2.7 trials      : {v027_result['trials_run']}")
    print(f"GP warnings        : {v027_result['fit_diagnostics']['scipy_warnings']}")
    print("=" * 82)


if __name__ == "__main__":
    main()
