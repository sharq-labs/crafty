from __future__ import annotations

import numpy as np

from .benchmark import make_space
from .hard_domain import hard_cooling_benchmark
from .sampling import sobol_points


def main():
    space = make_space()
    points = sobol_points(20000, space.dim, 2024)

    best_score = -float("inf")
    best_x = None
    feasible_count = 0

    for p in points:
        x = space.denormalize(p)
        score, feasible, _ = hard_cooling_benchmark(x)

        if feasible:
            feasible_count += 1
            if score > best_score:
                best_score = score
                best_x = x.copy()

    pos = space.normalize(best_x)

    print("=" * 72)
    print("V0.2.4 Hard Benchmark Verification")
    print("=" * 72)
    print(f"Feasible points : {feasible_count}/20000")
    print(f"Best Sobol score: {best_score:.6f}")
    print("Best normalized position:")
    print("  " + ", ".join(f"{v:.3f}" for v in pos))
    print("")
    print(f"Minimum coordinate: {np.min(pos):.3f}")
    print(f"Maximum coordinate: {np.max(pos):.3f}")
    print("")
    print("PASS condition: best region is interior, not all variables near 1.0.")
    print("=" * 72)


if __name__ == "__main__":
    main()
