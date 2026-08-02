from __future__ import annotations

import argparse
import time

from .benchmark import make_space
from .benchmark_suite import get_benchmark
from .adaptive_hybrid_engine import AdaptiveHybridLogEIEngine
from .adaptive_modes import get_adaptive_mode
from .hybrid_engine import HybridLogEIEngine
from .hybrid_modes import get_hybrid_mode


def run_adaptive(spec, seed, budget, initial, mode, device, noise, kernel):
    engine = AdaptiveHybridLogEIEngine(
        make_space(),
        spec.evaluator,
        seed=seed,
        screen_device=device,
        noise_mode=noise,
        kernel_name=kernel,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=budget - initial,
        verbose=False,
        **get_adaptive_mode(mode),
    )
    wall = time.perf_counter() - t0
    return result, wall


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=215)
    p.add_argument("--budget", type=int, default=40)
    p.add_argument("--initial", type=int, default=12)
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

    spec = get_benchmark("narrow_optimum")

    configs = [
        ("fixed-rbf", "fixed", "rbf"),
        ("learned-rbf", "learned", "rbf"),
        ("learned-matern25", "learned", "matern25"),
    ]

    print("=" * 106)
    print("V0.2.9.1 — Narrow Optimum Diagnostic")
    print("=" * 106)
    print(
        "Purpose: isolate whether narrow-optimum weakness is driven by "
        "fixed noise / overconfidence, kernel smoothness, or search policy."
    )
    print("")

    rows = []

    for label, noise, kernel in configs:
        result, wall = run_adaptive(
            spec=spec,
            seed=args.seed,
            budget=args.budget,
            initial=args.initial,
            mode=args.mode,
            device=args.screen_device,
            noise=noise,
            kernel=kernel,
        )

        d = result["fit_diagnostics"]

        row = {
            "label": label,
            "score": float(result["best"].score),
            "wall": wall,
            "fits": d["optimized_fits"],
            "fit_failures": d["fit_failures"],
            "refinement_selected": d["refinement_selected"],
            "forced_discrete": d["forced_discrete_selections"],
            "uncertainty": d["uncertainty_exploration_selections"],
            "pulses": d["stagnation_pulses"],
        }
        rows.append(row)

        print(
            f"{label:20s} "
            f"score={row['score']:10.4f} "
            f"wall={row['wall']:7.2f}s "
            f"fits={row['fits']:2d} "
            f"fail={row['fit_failures']:2d} "
            f"ref={row['refinement_selected']:2d} "
            f"forcedD={row['forced_discrete']:2d} "
            f"unc={row['uncertainty']:2d} "
            f"pulse={row['pulses']:2d}"
        )

    winner = max(rows, key=lambda r: r["score"])

    print("")
    print(f"Best diagnostic config: {winner['label']} -> {winner['score']:.6f}")
    print("=" * 106)


if __name__ == "__main__":
    main()
