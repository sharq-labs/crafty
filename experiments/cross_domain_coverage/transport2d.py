"""CONSUMER B — 2D steady advection-diffusion in a prescribed rotational field.

    div(u c) - D grad^2 c = s(x, y)        on [0,1]^2
    u = omega * (-(y - 1/2), (x - 1/2))    analytically divergence-free
    D = 0.01 m^2/s,  omega = 1 /s

`c` is dimensionless and normalized, following the convention every scalar
transport probe in this repository uses.

MINIMISED ON PURPOSE
--------------------
Steady, one discretization (first-order upwind advection, central diffusion),
two grids only. The previous milestone already measured a second scheme and a
refinement ladder in 1D, so spending here would buy a re-measurement. What is
kept is exactly what 1D could not reach.

WHAT THIS ADDS OVER THE 1D PROBE, AND IT IS CONCEDED THAT THE OPERATOR OVERLAPS
-------------------------------------------------------------------------------
1. **The inflow set is a subset of each boundary determined by a sign that
   varies ALONG it.** With a rotating field on a square, ``u . n`` changes sign
   at the midpoint of every side. In 1D the choice was between two endpoints; a
   boundary *region* was at least the right granularity. Here it is not: one
   side carries two different scientific roles, and a `BoundaryCondition` record
   names one region.
2. **The velocity is a field-valued MODEL INPUT.** `ScientificProblem` has no
   `data_references` — that field exists only on `ScientificResult` and
   `RawSolverOutput` — so a field-valued input has no typed home anywhere in a
   problem statement. In 1D the velocity was a scalar and this could not appear.
3. **The support is 2D**, with a connectivity that a scalar `length` cannot
   express.
4. **The source term is a second field-valued input**, with the same absence of
   a home.

THE REFERENCE IS A MANUFACTURED SOLUTION, WHICH IS EXACT
---------------------------------------------------------
A smooth ``c*`` is chosen and ``s`` is derived from it analytically, so the
reference is exact at every point at essentially zero cost. This is a strict
improvement over the previous milestone's Ogata-Banks reference, which was
semi-infinite on a finite domain and applicable only inside a measured window.
Here there is no window and no concession.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

FIELD_UNIT = "dimensionless"
LENGTH_UNIT = "meter"
VELOCITY_UNIT = "meter / second"
DIFFUSIVITY_UNIT = "m**2/s"
#: The manufactured source is a rate of change of a dimensionless scalar.
SOURCE_UNIT = "1 / second"

FROZEN_OMEGA = 1.0
FROZEN_DIFFUSIVITY = 0.01
FROZEN_SIDE_M = 1.0

#: Two resolutions only. Enough to observe that the error falls; not a ladder.
GRID_SIZES: tuple[int, ...] = (8, 16)

#: The four sides, in the order a reader will meet them. These are *region
#: identifiers* and nothing more — the core documents `BoundaryCondition.region`
#: as an opaque label it does not interpret.
REGIONS: tuple[str, ...] = ("side-w", "side-e", "side-s", "side-n")


class Transport2DError(Exception):
    """A configuration this probe refuses."""


@dataclass(frozen=True)
class Transport2DCase:
    """One frozen probe instance, in SI magnitudes."""

    case_id: str
    n_cells: int
    omega_per_s: float = FROZEN_OMEGA
    diffusivity_m2_s: float = FROZEN_DIFFUSIVITY
    side_m: float = FROZEN_SIDE_M

    def __post_init__(self) -> None:
        if self.n_cells < 2 or self.n_cells % 2:
            raise Transport2DError(
                f"n_cells must be an even integer >= 2, got {self.n_cells}"
            )
        if self.diffusivity_m2_s <= 0.0:
            raise Transport2DError("diffusivity must be strictly positive")

    @property
    def dx(self) -> float:
        return self.side_m / self.n_cells

    @property
    def centres(self) -> np.ndarray:
        """Cell-centre coordinates along one axis."""
        return (np.arange(self.n_cells) + 0.5) * self.dx

    @property
    def peak_speed_m_s(self) -> float:
        """``|u|`` at the corners, the largest speed in the domain."""
        return abs(self.omega_per_s) * self.side_m * math.sqrt(0.5)

    @property
    def peak_cell_peclet(self) -> float:
        return self.peak_speed_m_s * self.dx / self.diffusivity_m2_s

    def with_omega(self, omega_per_s: float) -> "Transport2DCase":
        """The same everything, rotating the other way. CASE B3 uses this."""
        return Transport2DCase(
            case_id=self.case_id,
            n_cells=self.n_cells,
            omega_per_s=omega_per_s,
            diffusivity_m2_s=self.diffusivity_m2_s,
            side_m=self.side_m,
        )


def case_b(n_cells: int) -> Transport2DCase:
    return Transport2DCase(case_id=f"case-b-n{n_cells}", n_cells=n_cells)


# =============================================================================
# The prescribed velocity field, and the manufactured solution
# =============================================================================

def velocity(case: Transport2DCase, x: float, y: float) -> tuple[float, float]:
    """Solid-body rotation about the centre. ``div u = 0`` analytically.

    This is the field-valued model input. It is a function here because there
    is nowhere in a `ScientificProblem` to put it as data.
    """
    half = 0.5 * case.side_m
    return (
        -case.omega_per_s * (y - half),
        case.omega_per_s * (x - half),
    )


def manufactured_solution(x: float, y: float) -> float:
    """``c*(x, y) = sin(pi x) sin(pi y)``. Smooth, and zero on all four sides."""
    return math.sin(math.pi * x) * math.sin(math.pi * y)


def manufactured_source(case: Transport2DCase, x: float, y: float) -> float:
    """``s = u . grad c* - D lap c*``, derived analytically.

    Because ``div u = 0``, ``div(u c) = u . grad c`` exactly, so no product-rule
    term is dropped and the manufactured source is exact rather than
    approximate.
    """
    ux, uy = velocity(case, x, y)
    pi = math.pi
    dcdx = pi * math.cos(pi * x) * math.sin(pi * y)
    dcdy = pi * math.sin(pi * x) * math.cos(pi * y)
    laplacian = -2.0 * pi * pi * math.sin(pi * x) * math.sin(pi * y)
    return ux * dcdx + uy * dcdy - case.diffusivity_m2_s * laplacian


def divergence_residual(case: Transport2DCase, samples: int = 32) -> float:
    """Largest ``|div u|`` measured by central differences. Should be ~0.

    Asserted rather than assumed: a manufactured source derived on the
    assumption ``div u = 0`` is wrong if the field is not actually solenoidal,
    and that error would masquerade as a discretization error.
    """
    h = 1.0e-6
    worst = 0.0
    for i in range(samples):
        for j in range(samples):
            x = (i + 0.5) * case.side_m / samples
            y = (j + 0.5) * case.side_m / samples
            dux = (velocity(case, x + h, y)[0] - velocity(case, x - h, y)[0]) / (2 * h)
            duy = (velocity(case, x, y + h)[1] - velocity(case, x, y - h)[1]) / (2 * h)
            worst = max(worst, abs(dux + duy))
    return worst


# =============================================================================
# Boundary orientation — the 2D finding
# =============================================================================

def outward_normal(region: str) -> tuple[float, float]:
    """The outward unit normal of one side. **A rank-1 boundary property.**

    There is no field on `BoundaryCondition` that can hold this: its members are
    `name`, `variable`, `kind`, `region`, `value`, `coefficients` and
    `description`, and `region` is an opaque string the core does not interpret.
    """
    return {
        "side-w": (-1.0, 0.0),
        "side-e": (1.0, 0.0),
        "side-s": (0.0, -1.0),
        "side-n": (0.0, 1.0),
    }[region]


def boundary_points(case: Transport2DCase, region: str, samples: int = 64):
    """Sample points along one side, at face centres."""
    step = case.side_m / samples
    for k in range(samples):
        t = (k + 0.5) * step
        if region == "side-w":
            yield 0.0, t
        elif region == "side-e":
            yield case.side_m, t
        elif region == "side-s":
            yield t, 0.0
        elif region == "side-n":
            yield t, case.side_m
        else:  # pragma: no cover - closed set
            raise Transport2DError(f"unknown region {region!r}")


def inflow_fraction(case: Transport2DCase, region: str, samples: int = 64) -> float:
    """Fraction of one side where ``u . n < 0``, i.e. where flow enters.

    **This is the measurement that 1D structurally could not make.** In 1D a
    boundary was a point and its role was a single fact. Here the role varies
    *along* the region, so a fraction strictly between 0 and 1 means one
    `BoundaryCondition` record is being asked to carry two different scientific
    roles at once.
    """
    normal = outward_normal(region)
    inflow = 0
    for x, y in boundary_points(case, region, samples):
        ux, uy = velocity(case, x, y)
        if ux * normal[0] + uy * normal[1] < 0.0:
            inflow += 1
    return inflow / samples


def orientation_summary(case: Transport2DCase, samples: int = 64) -> dict[str, float]:
    """Inflow fraction for every region. The 2D orientation finding, in one map."""
    return {region: inflow_fraction(case, region, samples) for region in REGIONS}


def inflow_signature(
    case: Transport2DCase, region: str, samples: int = 8
) -> tuple[bool, ...]:
    """Which sampled points of one side are inflow. The *set*, not the count.

    The fraction alone cannot show what reversal does: rotating the other way
    keeps every side half-inflow, so all four fractions stay at 0.5. The
    signature shows the sets **swap** — which is the point, because nothing in
    any record changes when they do.
    """
    normal = outward_normal(region)
    flags = []
    for x, y in boundary_points(case, region, samples):
        ux, uy = velocity(case, x, y)
        flags.append(ux * normal[0] + uy * normal[1] < 0.0)
    return tuple(flags)


def orientation_signature(
    case: Transport2DCase, samples: int = 8
) -> dict[str, tuple[bool, ...]]:
    """Inflow signature for every region."""
    return {
        region: inflow_signature(case, region, samples) for region in REGIONS
    }


# =============================================================================
# The solve
# =============================================================================

def solve_transport2d(case: Transport2DCase) -> np.ndarray:
    """Cell-centred finite differences: upwind advection, central diffusion.

    Dirichlet everywhere, taken from the manufactured solution. Neighbours
    outside the domain are evaluated from ``c*`` at the ghost cell centre, which
    is exact because ``c*`` is known analytically — so the boundary treatment
    contributes no error of its own and the measured error is the scheme's.

    Returns an ``n x n`` array of cell-centre values.
    """
    n = case.n_cells
    dx = case.dx
    d = case.diffusivity_m2_s
    centres = case.centres

    def index(i: int, j: int) -> int:
        return i * n + j

    matrix = np.zeros((n * n, n * n))
    rhs = np.zeros(n * n)

    for i in range(n):
        for j in range(n):
            x, y = centres[i], centres[j]
            ux, uy = velocity(case, x, y)
            row = index(i, j)
            rhs[row] = manufactured_source(case, x, y)

            diagonal = 4.0 * d / (dx * dx)

            def neighbour(di: int, dj: int, coefficient: float) -> None:
                nonlocal diagonal
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    matrix[row, index(ii, jj)] += coefficient
                else:
                    ghost_x = (ii + 0.5) * dx
                    ghost_y = (jj + 0.5) * dx
                    rhs[row] -= coefficient * manufactured_solution(ghost_x, ghost_y)

            # Diffusion, central.
            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbour(di, dj, -d / (dx * dx))

            # Advection, first-order upwind.
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

            matrix[row, row] += diagonal

    solution = np.linalg.solve(matrix, rhs)
    return solution.reshape((n, n))


def solution_error(case: Transport2DCase, field: np.ndarray) -> float:
    """Max nodal deviation from the manufactured solution. Exact reference."""
    centres = case.centres
    worst = 0.0
    for i, x in enumerate(centres):
        for j, y in enumerate(centres):
            worst = max(worst, abs(field[i, j] - manufactured_solution(x, y)))
    return worst


def field_metrics(case: Transport2DCase, field: np.ndarray) -> dict[str, float]:
    """The scalars a `ScientificResult` can currently hold."""
    half = case.n_cells // 2
    return {
        "c:centre": float(field[half, half]),
        "c:max": float(field.max()),
        "c:min": float(field.min()),
        "c:mean": float(field.mean()),
        "c:mms_error": solution_error(case, field),
    }


def admissibility_violation(field: np.ndarray) -> float:
    """How far outside ``[0, 1]`` the solution strays.

    ``c* = sin(pi x) sin(pi y)`` lies in ``[0, 1]`` on the unit square, and the
    source is constructed from it, so an excursion is a discretization artifact
    and not physics. First-order upwind is monotone, so this is expected to be
    at round-off — the check exists so that the *kind* of admissibility evidence
    this consumer contributes is the same kind the other three contribute.
    """
    return max(0.0, float(-field.min()), float(field.max() - 1.0))
