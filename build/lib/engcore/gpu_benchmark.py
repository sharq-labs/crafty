from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .domain import cooling_benchmark
from .gpu_engine import GPUSmartExperimentEngine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=40)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cpu", action="store_true", help="Force CPU for comparison")
    args = parser.parse_args()

    space = make_space()
    initial = min(32, max(8, args.budget // 3))
    smart = max(0, args.budget - initial)

    engine = GPUSmartExperimentEngine(
        space,
        cooling_benchmark,
        seed=args.seed,
        force_cpu=args.cpu,
    )

    wall0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=smart,
        candidate_pool=args.pool,
        candidate_chunk_size=args.chunk,
        patience=max(20, args.budget),
    )
    wall = time.perf_counter() - wall0

    total_scored = args.pool * max(0, result["trials_run"] - initial)
    scoring_s = result["timings"]["candidate_scoring_s"]
    candidates_per_sec = total_scored / scoring_s if scoring_s > 0 else 0.0

    print("=" * 78)
    print("Engineering AI Core V0.2.3 — Memory-Safe GPU Smart Engine")
    print("=" * 78)
    print(f"Device                 : {result['device'].name}")
    print(f"Backend                : {result['device'].device}")
    print(f"CUDA active            : {result['device'].cuda}")
    print(f"Experiment budget      : {args.budget}")
    print(f"Candidate pool / step  : {args.pool:,}")
    print(f"GPU chunk size         : {args.chunk:,}")
    print(f"Experiments run        : {result['trials_run']}")
    print(f"Best score             : {result['best'].score:.6f}")
    print(f"Wall time              : {wall:.3f} s")
    print(f"Approx candidates/sec  : {candidates_per_sec:,.0f}")
    print("")
    print("Timing breakdown")
    for key, value in result["timings"].items():
        print(f"  {key:22s}: {value:.3f} s")
    print("")
    print("GPU memory")
    for key, value in result["gpu_memory"].items():
        print(f"  {key:22s}: {value:.1f} MB")
    print("")
    print("Best design")
    for k, v in space.as_dict(result["best"].x).items():
        print(f"  {k:22s}: {v:.4f}")
    print("")
    print("NOTE: synthetic benchmark only; not validated engineering physics.")
    print("=" * 78)


if __name__ == "__main__":
    main()
