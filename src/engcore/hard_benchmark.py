from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .benchmark import make_space
from .sampling import sobol_points
from .hard_domain import hard_cooling_benchmark
from .gpu_engine import GPUSmartExperimentEngine


def evaluate_points(space, points):
    best_score = -np.inf
    best_result = None
    curve = []

    for p in points:
        x = space.denormalize(p)
        score, feasible, metadata = hard_cooling_benchmark(x)

        if feasible and score > best_score:
            best_score = float(score)
            best_result = (x.copy(), float(score), metadata)

        curve.append(best_score)

    curve = np.asarray(curve, dtype=float)
    finite = np.where(np.isfinite(curve))[0]

    if len(finite) == 0:
        curve[:] = 0.0
    else:
        curve[:finite[0]] = curve[finite[0]]

    return best_result, curve


def smart_curve(history):
    best = -np.inf
    values = []

    for result in history:
        if result.feasible and result.score > best:
            best = result.score
        values.append(best)

    values = np.asarray(values, dtype=float)
    finite = np.where(np.isfinite(values))[0]

    if len(finite) == 0:
        values[:] = 0.0
    else:
        values[:finite[0]] = values[finite[0]]

    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", type=int, default=60)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--refit-interval", type=int, default=4)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    space = make_space()
    out_dir = Path("v024_results")
    out_dir.mkdir(exist_ok=True)

    rng = np.random.default_rng(args.seed)

    t0 = time.perf_counter()
    random_best, random_curve = evaluate_points(
        space,
        rng.random((args.budget, space.dim)),
    )
    random_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    sobol_best, sobol_curve = evaluate_points(
        space,
        sobol_points(args.budget, space.dim, args.seed),
    )
    sobol_time = time.perf_counter() - t0

    initial = min(24, max(12, args.budget // 3))
    smart_trials = max(0, args.budget - initial)

    engine = GPUSmartExperimentEngine(
        space,
        hard_cooling_benchmark,
        seed=args.seed,
        force_cpu=args.cpu,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=smart_trials,
        candidate_pool=args.pool,
        candidate_chunk_size=args.chunk,
        patience=max(25, args.budget),
        refit_interval=args.refit_interval,
    )
    smart_time = time.perf_counter() - t0

    smart_values = smart_curve(engine.history)

    random_score = random_best[1]
    sobol_score = sobol_best[1]
    smart_score = result["best"].score

    target = 0.99 * max(
        random_score, sobol_score, smart_score
    )

    def hit(curve):
        for i, value in enumerate(curve, 1):
            if value >= target:
                return i
        return None

    smart_steps = max(0, result["trials_run"] - initial)
    total_candidates = smart_steps * args.pool
    scoring_s = result["timings"]["candidate_scoring_s"]
    rate = (
        total_candidates / scoring_s
        if scoring_s > 0 else 0.0
    )

    print("=" * 84)
    print("Engineering AI Core V0.2.4 — Hard Optimizer Benchmark")
    print("=" * 84)
    print(f"Device                     : {result['device'].name}")
    print(f"CUDA active                : {result['device'].cuda}")
    print(f"Budget / method            : {args.budget}")
    print(f"Candidate pool / smart step: {args.pool:,}")
    print(f"Chunk                      : {args.chunk:,}")
    print(f"Refit interval             : {args.refit_interval}")
    print("")
    print("FINAL SCORE")
    print(f"Random                     : {random_score:.6f}")
    print(f"Sobol                      : {sobol_score:.6f}")
    print(f"Smart                      : {smart_score:.6f}")
    print("")
    print("99% TARGET")
    print(f"Target                     : {target:.6f}")
    print(f"Random experiments         : {hit(random_curve)}")
    print(f"Sobol experiments          : {hit(sobol_curve)}")
    print(f"Smart experiments          : {hit(smart_values)}")
    print("")
    print("WALL TIME")
    print(f"Random                     : {random_time:.3f} s")
    print(f"Sobol                      : {sobol_time:.3f} s")
    print(f"Smart                      : {smart_time:.3f} s")
    print(f"Candidate throughput       : {rate:,.0f} / sec")
    print("")
    print("SMART TIMING")
    for key, value in result["timings"].items():
        print(f"  {key:25s}: {value:.3f} s")
    print("")
    print("FIT DIAGNOSTICS")
    for key, value in result["fit_diagnostics"].items():
        print(f"  {key:25s}: {value}")
    print("")
    print("GPU MEMORY")
    for key, value in result["gpu_memory"].items():
        print(f"  {key:25s}: {value:.1f} MB")
    print("")
    print("SMART BEST DESIGN")
    for key, value in space.as_dict(result["best"].x).items():
        print(f"  {key:25s}: {value:.4f}")
    print("")
    pos = result["best"].metadata.get("normalized_position", [])
    print("Normalized position (0..1):")
    print("  " + ", ".join(f"{v:.3f}" for v in pos))
    print("")
    print("NOTE: synthetic benchmark only; not validated engineering physics.")
    print("=" * 84)

    csv_path = out_dir / "convergence.csv"
    max_len = max(
        len(random_curve), len(sobol_curve), len(smart_values)
    )

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "experiment",
            "random_best",
            "sobol_best",
            "smart_best",
        ])

        for i in range(max_len):
            writer.writerow([
                i + 1,
                random_curve[min(i, len(random_curve) - 1)],
                sobol_curve[min(i, len(sobol_curve) - 1)],
                smart_values[min(i, len(smart_values) - 1)],
            ])

    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.plot(
        range(1, len(random_curve) + 1),
        random_curve,
        label="Random",
    )
    ax.plot(
        range(1, len(sobol_curve) + 1),
        sobol_curve,
        label="Sobol",
    )
    ax.plot(
        range(1, len(smart_values) + 1),
        smart_values,
        label="Smart GPU",
    )
    ax.set_xlabel("Experiments")
    ax.set_ylabel("Best Feasible Score So Far")
    ax.set_title("V0.2.4 — Hard Synthetic Benchmark")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_dir / "convergence.png", dpi=170)
    plt.close(fig)

    print(f"\nSaved CSV  : {csv_path}")
    print(f"Saved graph: {out_dir / 'convergence.png'}")


if __name__ == "__main__":
    main()
