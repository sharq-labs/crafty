"""TRACK B preparation probe — grounding B2/B3 with executed numbers.

This is a standalone, isolated probe. It imports nothing from
``src/engcore`` and nothing from ``experiments/cross_domain_coverage`` — it
re-derives the same governing equations from the module docstring in
``experiments/cross_domain_coverage/transport2d.py`` (CROSS-DOMAIN-COVERAGE,
consumer B) independently, so that this probe's numbers are not a re-print of
that milestone's own instrument.

GOVERNING PROBLEM (identical physics to CROSS-DOMAIN-COVERAGE consumer B)
---------------------------------------------------------------------------
    div(u c) - D grad^2 c = s(x, y)        on [0, 1]^2
    u = omega * (-(y - 1/2), (x - 1/2))    solid-body rotation, div-free
    D = 0.01 m^2/s,  omega = 1 /s
    c* = sin(pi x) sin(pi y)   (manufactured solution, exact source s derived
                                 from it; Dirichlet c* on all four sides)

WHAT THIS PROBE ADDS THAT WAS NOT ALREADY MEASURED
----------------------------------------------------
CROSS-DOMAIN-COVERAGE deliberately minimised to two grids (n=8, n=16) and one
scheme. It measured MMS error 0.480 -> 0.292 and a coarse-grid admissibility
violation (c_min = -0.0136) but did not compute an observed convergence
*order*, did not identify the grid at which the scheme becomes admissible, and
did not compare the cost of a dense native solve against a sparse SciPy
solve as the resolution needed to actually see first-order convergence grows.
Those three numbers are what TRACK B (B2 acceptance tolerances / B3 execution
path) needs and are what this script measures.

Two solvers are exercised for the SAME discretization (first-order upwind
advection, second-order central diffusion, backward-style implicit steady
solve via a single global linear system):

  * NATIVE  — dense numpy matrix + numpy.linalg.solve (mirrors the prior
    minimised probe's approach).
  * SCIPY   — the identical matrix assembled directly in CSR form and solved
    with scipy.sparse.linalg.spsolve.

Both must agree to near machine precision (same linear system, different
solvers) — this is checked, not assumed. Their assembly costs and solve
times are timed and reported to ground the "cheapest credible execution
path" question (B3) in real numbers rather than intuition.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

OMEGA = 1.0
DIFFUSIVITY = 0.01
SIDE = 1.0


def velocity(x: float, y: float) -> tuple[float, float]:
    half = 0.5 * SIDE
    return (-OMEGA * (y - half), OMEGA * (x - half))


def c_star(x: float, y: float) -> float:
    return math.sin(math.pi * x) * math.sin(math.pi * y)


def source(x: float, y: float) -> float:
    ux, uy = velocity(x, y)
    pi = math.pi
    dcdx = pi * math.cos(pi * x) * math.sin(pi * y)
    dcdy = pi * math.sin(pi * x) * math.cos(pi * y)
    lap = -2.0 * pi * pi * math.sin(pi * x) * math.sin(pi * y)
    return ux * dcdx + uy * dcdy - DIFFUSIVITY * lap


@dataclass(frozen=True)
class AssembledSystem:
    n: int
    dx: float
    dense: np.ndarray
    sparse: "lil_matrix"
    rhs: np.ndarray


def assemble(n: int) -> AssembledSystem:
    dx = SIDE / n
    centres = (np.arange(n) + 0.5) * dx
    dense = np.zeros((n * n, n * n))
    sparse = lil_matrix((n * n, n * n))
    rhs = np.zeros(n * n)

    def index(i: int, j: int) -> int:
        return i * n + j

    for i in range(n):
        for j in range(n):
            x, y = centres[i], centres[j]
            ux, uy = velocity(x, y)
            row = index(i, j)
            rhs[row] = source(x, y)
            diagonal = 4.0 * DIFFUSIVITY / (dx * dx)

            def neighbour(di: int, dj: int, coeff: float) -> None:
                nonlocal diagonal
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    dense[row, index(ii, jj)] += coeff
                    sparse[row, index(ii, jj)] += coeff
                else:
                    gx = (ii + 0.5) * dx
                    gy = (jj + 0.5) * dx
                    rhs[row] -= coeff * c_star(gx, gy)

            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbour(di, dj, -DIFFUSIVITY / (dx * dx))

            if ux >= 0.0:
                diagonal += ux / dx
                neighbour(-1, 0, -ux / dx)
            else:
                diagonal += -ux / dx
                neighbour(1, 0, ux / dx)
            if uy >= 0.0:
                diagonal += uy / dx
                neighbour(0, -1, -uy / dx)
            else:
                diagonal += -uy / dx
                neighbour(0, 1, uy / dx)

            dense[row, row] += diagonal
            sparse[row, row] += diagonal

    return AssembledSystem(n=n, dx=dx, dense=dense, sparse=sparse, rhs=rhs)


def solve_native(sys_: AssembledSystem) -> tuple[np.ndarray, float]:
    t0 = time.perf_counter()
    solution = np.linalg.solve(sys_.dense, sys_.rhs)
    dt = time.perf_counter() - t0
    return solution.reshape((sys_.n, sys_.n)), dt


def solve_scipy(sys_: AssembledSystem) -> tuple[np.ndarray, float]:
    csr = sys_.sparse.tocsr()
    t0 = time.perf_counter()
    solution = spsolve(csr, sys_.rhs)
    dt = time.perf_counter() - t0
    return solution.reshape((sys_.n, sys_.n)), dt


def mms_error(n: int, dx: float, field: np.ndarray) -> float:
    centres = (np.arange(n) + 0.5) * dx
    worst = 0.0
    for i, x in enumerate(centres):
        for j, y in enumerate(centres):
            worst = max(worst, abs(field[i, j] - c_star(x, y)))
    return worst


def peak_cell_peclet(dx: float) -> float:
    peak_speed = abs(OMEGA) * SIDE * math.sqrt(0.5)
    return peak_speed * dx / DIFFUSIVITY


def admissibility_violation(field: np.ndarray) -> float:
    return max(0.0, float(-field.min()), float(field.max() - 1.0))


def main() -> None:
    grid_sizes = (8, 16, 32, 64)
    rows = []
    prev_error = None
    for n in grid_sizes:
        sys_ = assemble(n)

        native_field, native_dt = solve_native(sys_)
        scipy_field, scipy_dt = solve_scipy(sys_)

        cross_solver_max_diff = float(np.max(np.abs(native_field - scipy_field)))

        err = mms_error(n, sys_.dx, native_field)
        order = None
        if prev_error is not None:
            order = math.log2(prev_error / err)
        prev_error = err

        rows.append(
            {
                "n_cells": n,
                "dof": n * n,
                "dx": sys_.dx,
                "peak_cell_peclet": peak_cell_peclet(sys_.dx),
                "mms_error": err,
                "observed_order_vs_prev": order,
                "admissibility_violation": admissibility_violation(native_field),
                "native_solve_seconds": native_dt,
                "scipy_solve_seconds": scipy_dt,
                "native_vs_scipy_max_diff": cross_solver_max_diff,
            }
        )

    print(json.dumps(rows, indent=2))

    print("\n--- summary table ---")
    header = (
        f"{'n':>4} {'dof':>6} {'Pe_cell':>9} {'mms_err':>10} "
        f"{'order':>7} {'admiss_viol':>12} {'native_s':>9} {'scipy_s':>9} "
        f"{'cross_diff':>11}"
    )
    print(header)
    for r in rows:
        order_str = f"{r['observed_order_vs_prev']:.3f}" if r["observed_order_vs_prev"] is not None else "   n/a"
        print(
            f"{r['n_cells']:>4} {r['dof']:>6} {r['peak_cell_peclet']:>9.3f} "
            f"{r['mms_error']:>10.5f} {order_str:>7} "
            f"{r['admissibility_violation']:>12.6f} {r['native_solve_seconds']:>9.4f} "
            f"{r['scipy_solve_seconds']:>9.4f} {r['native_vs_scipy_max_diff']:>11.2e}"
        )


if __name__ == "__main__":
    main()
