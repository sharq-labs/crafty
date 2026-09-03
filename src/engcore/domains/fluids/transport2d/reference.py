"""The closed-form reference solution, the prescribed velocity field, and the
boundary-orientation stress point (F6). Verification side only.

This module is what the solver is checked AGAINST, so it must not be
reachable FROM the solver: a verification that shares code with the thing it
verifies tests only that the shared code is self-consistent. It imports
``math``/``numpy`` and this package's own units-adjacent constants, and
nothing from :mod:`solver` — a test asserts that, mirroring
``thermal/conduction1d``'s identical discipline.

THE MANUFACTURED SOLUTION
--------------------------
    c*(x, y) = sin(pi x / L) sin(pi y / L)

chosen (unchanged from ``docs/fluid-pde-preparation.md`` §B2) because it is
exact by construction — the source term ``s`` is derived analytically from
it, so a disagreement between a solver's output and this reference can only
be the solver's discretization error, never approximation error in the
reference itself.

THE VELOCITY FIELD, AND WHY IT IS NOT A CONFIGURATION KNOB
-------------------------------------------------------------
    u(x, y) = omega * (-(y - L/2), (x - L/2))

Solid-body rotation about the domain centre, exactly divergence-free
(``du_x/dx + du_y/dy = 0`` identically). It was chosen — by the preparation
milestone this one continues, not by this module — *because* it makes the
sign of ``u . n`` (velocity dotted with the outward boundary normal) vary
*within* a single labelled boundary side, which is F6's mandatory stress
point: see :func:`inflow_fraction` and :func:`orientation_signature` below,
and re-verify it is real (not a preparation-only claim) by running
:func:`inflow_fraction` here, against this package's own production
``Transport2DDomain`` and its own production grid, not a re-print of the
preparation's numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .errors import Transport2DConfigurationError

REFERENCE_ID = "fluids.transport2d.rotational_manufactured_sine"
REFERENCE_EXPRESSION = "c*(x,y) = sin(pi*x/L) * sin(pi*y/L)"


def _checked(side_m: float, diffusivity_m2_s: float, omega_per_s: float) -> tuple[float, float, float]:
    side = float(side_m)
    diffusivity = float(diffusivity_m2_s)
    omega = float(omega_per_s)
    if not math.isfinite(side) or side <= 0.0:
        raise Transport2DConfigurationError(f"side must be finite and positive, got {side!r}")
    if not math.isfinite(diffusivity) or diffusivity <= 0.0:
        raise Transport2DConfigurationError(
            f"diffusivity must be finite and positive, got {diffusivity!r}"
        )
    if not math.isfinite(omega) or omega == 0.0:
        raise Transport2DConfigurationError(f"omega must be finite and non-zero, got {omega!r}")
    return side, diffusivity, omega


def velocity(x: float, y: float, *, side_m: float, omega_per_s: float) -> tuple[float, float]:
    """u(x, y) — the prescribed, divergence-free solid-body rotation."""
    half = 0.5 * side_m
    return (-omega_per_s * (y - half), omega_per_s * (x - half))


def c_star(x: float, y: float, *, side_m: float) -> float:
    """The exact manufactured solution."""
    length = side_m
    return math.sin(math.pi * x / length) * math.sin(math.pi * y / length)


def source(x: float, y: float, *, side_m: float, diffusivity_m2_s: float, omega_per_s: float) -> float:
    """s(x,y) = u . grad(c*) - D laplacian(c*), derived analytically and
    exactly — see the module docstring."""
    length = side_m
    ux, uy = velocity(x, y, side_m=length, omega_per_s=omega_per_s)
    pi = math.pi
    k = pi / length
    dcdx = k * math.cos(k * x) * math.sin(k * y)
    dcdy = k * math.sin(k * x) * math.cos(k * y)
    lap = -2.0 * k * k * math.sin(k * x) * math.sin(k * y)
    return ux * dcdx + uy * dcdy - diffusivity_m2_s * lap


def exact_centre(*, side_m: float, diffusivity_m2_s: float, omega_per_s: float) -> float:
    """c*(L/2, L/2). sin(pi/2)^2 = 1 identically, independent of L, D, omega
    — the QoI's reference value is exactly 1.0 for every valid instance of
    this benchmark, which is why it is a useful single-scalar QoI."""
    side_m, diffusivity_m2_s, omega_per_s = _checked(side_m, diffusivity_m2_s, omega_per_s)
    return 1.0


def exact_field(x_m, y_m, *, side_m: float) -> np.ndarray:
    """c*(x, y) at the given positions (broadcastable arrays)."""
    length = float(side_m)
    if not math.isfinite(length) or length <= 0.0:
        raise Transport2DConfigurationError(f"side must be finite and positive, got {length!r}")
    x = np.asarray(x_m, dtype=np.float64)
    y = np.asarray(y_m, dtype=np.float64)
    return np.sin(np.pi * x / length) * np.sin(np.pi * y / length)


# =====================================================================
# F6 — boundary orientation, re-verified against a real production grid
# =====================================================================

@dataclass(frozen=True)
class SideOrientation:
    """u.n sampled at every boundary-adjacent cell centre along one side."""

    side: str
    normal_components: tuple[float, ...]   # u . n at each sample point
    positions: tuple[float, ...]           # coordinate along the side

    @property
    def inflow_fraction(self) -> float:
        """Fraction of sample points where u.n < 0 (flow entering)."""
        if not self.normal_components:
            return float("nan")
        inflow = sum(1 for v in self.normal_components if v < 0.0)
        return inflow / len(self.normal_components)

    @property
    def sign_changes(self) -> int:
        """Number of sample-to-sample sign reversals of u.n along the side.

        Zero would mean the whole side is one physically coherent role
        (inlet, or outlet, or exactly tangent); this benchmark's own
        rotational field is expected to produce exactly one, at the side's
        midpoint (see the module docstring and F6's finding)."""
        signs = [1 if v >= 0.0 else -1 for v in self.normal_components]
        return sum(1 for a, b in zip(signs, signs[1:]) if a != b)

    @property
    def orientation_signature(self) -> tuple[bool, ...]:
        """Point-by-point inflow/outflow, the finer instrument the
        preparation document's own module names — the aggregate fraction
        alone cannot see a rotation reversal, this can."""
        return tuple(v < 0.0 for v in self.normal_components)


# Outward unit normals, by side label. Matches problem.SIDE_* constants;
# duplicated here (not imported) because this module must not depend on
# anything the solver could also depend on for its own boundary handling —
# see the module docstring's isolation requirement.
_OUTWARD_NORMALS: dict[str, tuple[float, float]] = {
    "side-south": (0.0, -1.0),
    "side-north": (0.0, 1.0),
    "side-west": (-1.0, 0.0),
    "side-east": (1.0, 0.0),
}


def side_orientation(
    side: str,
    *,
    n_cells: int,
    side_m: float,
    omega_per_s: float,
) -> SideOrientation:
    """u.n at every boundary-adjacent CELL CENTRE along ``side``, for the
    REAL production grid resolution — not an analytic continuum claim.

    Sampling at the actual cell-centre positions a solver of this exact
    resolution would use is deliberate: F6 requires checking this "against
    your real velocity field and boundary geometry", not just conceptually.
    """
    if side not in _OUTWARD_NORMALS:
        raise Transport2DConfigurationError(f"unknown side {side!r}")
    nx, ny = _OUTWARD_NORMALS[side]
    dx = side_m / n_cells
    centres = [(i + 0.5) * dx for i in range(n_cells)]

    normal_components: list[float] = []
    positions: list[float] = []
    for coordinate in centres:
        if side in ("side-south", "side-north"):
            x = coordinate
            y = 0.0 if side == "side-south" else side_m
        else:
            y = coordinate
            x = 0.0 if side == "side-west" else side_m
        ux, uy = velocity(x, y, side_m=side_m, omega_per_s=omega_per_s)
        normal_components.append(ux * nx + uy * ny)
        positions.append(coordinate)

    return SideOrientation(
        side=side,
        normal_components=tuple(normal_components),
        positions=tuple(positions),
    )
