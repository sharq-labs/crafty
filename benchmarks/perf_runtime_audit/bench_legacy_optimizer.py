"""PERF-0 — profile of the legacy ``SmartExperimentEngine`` BO loop.

Separate from SRIA, and separate from the frozen V0.3.x optimizers. Nothing here
modifies the engine; it decomposes one Bayesian-optimization step into the three
costs the code actually pays each iteration:

* a Gaussian process refitted from scratch on the whole history
  (``n_restarts_optimizer=2``, so three optimizer runs per fit),
* posterior prediction over a freshly regenerated candidate pool,
* a ``pool x history x dim`` broadcast distance tensor for duplicate
  suppression.

The GP's ConvergenceWarnings are captured and counted rather than silenced, so
their frequency is evidence rather than noise.

    python benchmarks/perf_runtime_audit/bench_legacy_optimizer.py
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import tracemalloc
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from src.engcore.models import DesignSpace, Variable  # noqa: E402
from src.engcore.sampling import sobol_points  # noqa: E402
from src.engcore.surrogate import (  # noqa: E402
    GaussianSurrogate,
    expected_improvement,
)

#: Representative dimensionality. Six continuous variables is the shape the
#: legacy demos use; the point is the cost curve, not the design.
DIM = 6
POOL = 4096


def space(dim: int) -> DesignSpace:
    return DesignSpace(
        variables=tuple(
            Variable(name=f"v{i}", low=0.0, high=1.0) for i in range(dim)
        )
    )


def _objective(x01: np.ndarray) -> float:
    """Deterministic, cheap, and irrelevant to the measurement."""
    return float(-np.sum((x01 - 0.35) ** 2))


def step_costs(
    history_size: int, dim: int, pool_size: int, repeats: int
) -> dict[str, Any]:
    """Cost of one BO step at a given history length."""
    rng = np.random.default_rng(1234)
    X = rng.random((history_size, dim))
    y = np.array([_objective(row) for row in X])
    pool = sobol_points(pool_size, dim, 7)

    fit_times: list[float] = []
    predict_times: list[float] = []
    distance_times: list[float] = []
    warning_counts: Counter[str] = Counter()

    for _ in range(repeats):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            surrogate = GaussianSurrogate(dim)
            started = time.perf_counter()
            surrogate.fit(X, y)
            fit_times.append(time.perf_counter() - started)
        for w in caught:
            warning_counts[w.category.__name__] += 1

        started = time.perf_counter()
        mean, std = surrogate.predict(pool)
        expected_improvement(mean, std, float(np.max(y)))
        predict_times.append(time.perf_counter() - started)

        started = time.perf_counter()
        np.min(
            np.linalg.norm(pool[:, None, :] - X[None, :, :], axis=2), axis=1
        )
        distance_times.append(time.perf_counter() - started)

    # Peak memory of the distance tensor alone.
    tracemalloc.start()
    tracemalloc.reset_peak()
    np.min(np.linalg.norm(pool[:, None, :] - X[None, :, :], axis=2), axis=1)
    distance_peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    fit_m = statistics.median(fit_times)
    predict_m = statistics.median(predict_times)
    distance_m = statistics.median(distance_times)
    return {
        "history": history_size,
        "gp_fit_median_s": fit_m,
        "gp_fit_min_s": min(fit_times),
        "predict_and_ei_median_s": predict_m,
        "duplicate_distance_median_s": distance_m,
        "total_step_median_s": fit_m + predict_m + distance_m,
        "gp_fit_share": fit_m / (fit_m + predict_m + distance_m),
        "distance_tensor_elements": pool_size * history_size * dim,
        "distance_tensor_theoretical_bytes": pool_size * history_size * dim * 8,
        "distance_tensor_traced_peak_bytes": int(distance_peak),
        "warnings": dict(warning_counts),
        "repeats": repeats,
    }


def full_loop(dim: int, pool_size: int) -> dict[str, Any]:
    """One end-to-end legacy run, for a total-cost figure."""
    from src.engcore.engine import SmartExperimentEngine

    def evaluator(x):
        return _objective(x), True, {}

    engine = SmartExperimentEngine(space(dim), evaluator, seed=42)
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = engine.run(
            initial_trials=32, smart_trials=68, candidate_pool=pool_size
        )
    elapsed = time.perf_counter() - started
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    counts: Counter[str] = Counter()
    for w in caught:
        counts[w.category.__name__] += 1
    return {
        "seconds": elapsed,
        "trials_run": out["trials_run"],
        "gp_fits": out["trials_run"] - 32,
        "traced_peak_bytes": int(peak),
        "warnings": dict(counts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--histories", type=int, nargs="+", default=[32, 50, 75, 100]
    )
    parser.add_argument("--dim", type=int, default=DIM)
    parser.add_argument("--pool", type=int, default=POOL)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = []
    for n in args.histories:
        row = step_costs(n, args.dim, args.pool, args.repeats)
        rows.append(row)
        print(
            f"history={n:4d} gp_fit={row['gp_fit_median_s']:7.4f}s "
            f"predict+ei={row['predict_and_ei_median_s']:7.4f}s "
            f"dup_dist={row['duplicate_distance_median_s']:7.4f}s "
            f"step={row['total_step_median_s']:7.4f}s "
            f"gp_share={row['gp_fit_share']:5.1%} "
            f"dist_MB={row['distance_tensor_theoretical_bytes'] / 1e6:6.2f} "
            f"warn={row['warnings']}",
            flush=True,
        )

    loop = full_loop(args.dim, args.pool)
    print(
        f"full legacy run: {loop['seconds']:.2f}s over {loop['trials_run']} "
        f"trials ({loop['gp_fits']} GP fits), peak "
        f"{loop['traced_peak_bytes'] / 1e6:.1f} MB traced, "
        f"warnings={loop['warnings']}",
        flush=True,
    )

    payload = {"dim": args.dim, "pool": args.pool, "steps": rows, "full_loop": loop}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
