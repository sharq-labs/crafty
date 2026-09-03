"""The frozen hostile consumer: 1D transient advection-diffusion.

    dc/dt + u dc/dx = D d2c/dx2        x in [0, L],  t in [0, t_end]

``c`` IS DIMENSIONLESS. It is a normalized transported scalar, not a
concentration in mol/m^3, and it carries ``dimensionless`` everywhere it
appears. Calling it a concentration would imply a species, a solvent and a
reference state this probe does not have — the same refusal
``thermal/conduction1d`` makes for its normalized field, and made for the same
reason.

WHY THIS EQUATION AND NOT DIFFUSION
-----------------------------------
`thermal/conduction1d` already exercises 1D transient diffusion. What it cannot
exercise is a **direction**: ``d2u/dx2`` is symmetric, so both ends of that slab
are interchangeable and every question about orientation has a trivial answer.
``u dc/dx`` is not symmetric. One end is upstream and the other is not, and
which is which is a function of the sign of ``u`` — a *parameter value*, not a
modelling taste.

Everything else is held constant against that baseline on purpose: same slab
shape, same even ``n_cells``, same backward Euler, same tridiagonal assembly,
same dimensionless field. The difference against the baseline is the operator
and the boundaries, and nothing else.

THE THREE FROZEN CASES
----------------------
See `docs/hostile-core-domain-stress-prereg.md` §4. Summarized:

CASE S  steady, ``c(0)=1``, ``c(L)=0``, exact closed form, run at ``Pe = 40``
        across ``n_cells in {8, 16, 40, 80, 160}`` so ``Pe_cell`` straddles 2.
CASE T  transient, ``c(x,0)=0``, Dirichlet inflow, homogeneous Neumann outflow,
        compared against the Ogata-Banks semi-infinite solution inside a frozen
        validity window.
CASE N  ``D = 0``. Representation only. **Executes nothing.**

TWO DISCRETIZATIONS, AND WHY BOTH ARE REQUIRED
-----------------------------------------------
Central differencing of the advection term is second-order accurate and
**unbounded** above ``Pe_cell = 2``; first-order upwind is monotone and bounded
at every ``Pe_cell`` and pays for it in accuracy. They are the same science and
different numerics, which is precisely the separation the milestone is
measuring. Diffusion is central in both.

WHAT THIS MODULE IS NOT
-----------------------
It imports nothing from ``engcore``. It knows about no contract, no record and
no schema. Keeping the physics ignorant of the representation is what stops the
representation from quietly reaching into the physics when a record cannot say
something — which would be the probe measuring itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

# --- units, stated once ------------------------------------------------------
FIELD_UNIT = "dimensionless"
LENGTH_UNIT = "meter"
TIME_UNIT = "second"
VELOCITY_UNIT = "meter / second"
DIFFUSIVITY_UNIT = "m**2/s"
#: A homogeneous Neumann condition on a dimensionless field is a gradient, so
#: it carries 1/length and NOT the field's own dimension. The core deliberately
#: does not check this (only Dirichlet and initial conditions are dimensionally
#: constrained), which is itself one of the facts this probe reports on.
GRADIENT_UNIT = "1 / meter"


class AdvectionScheme(str, Enum):
    """How the advection term is discretized. Nothing else differs."""

    #: 2nd-order central. Unbounded for ``Pe_cell > 2``.
    CENTRAL = "central_difference_2nd_order"
    #: 1st-order upwind, written for ``u > 0``. Monotone at every ``Pe_cell``.
    UPWIND = "upwind_1st_order"


class TransportProbeError(Exception):
    """A configuration this probe refuses."""


@dataclass(frozen=True)
class TransportDiscretization:
    """How finely the interval is resolved. Purely numerical.

    ``n_cells`` is even, following the baseline domain, so ``x = L/2`` is a grid
    node and the midpoint QoI is an exact nodal value rather than an
    interpolation.
    """

    n_cells: int
    n_steps: int

    def __post_init__(self) -> None:
        for label in ("n_cells", "n_steps"):
            raw = getattr(self, label)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise TransportProbeError(
                    f"{label} must be an int, got {type(raw).__name__}"
                )
        if self.n_cells < 2 or self.n_cells % 2:
            raise TransportProbeError(
                f"n_cells must be an even integer >= 2, got {self.n_cells}"
            )
        if self.n_steps < 1:
            raise TransportProbeError(
                f"n_steps must be at least 1, got {self.n_steps}"
            )

    @property
    def n_nodes(self) -> int:
        return self.n_cells + 1


@dataclass(frozen=True)
class TransportCase:
    """One fully declared probe instance, in SI magnitudes.

    Magnitudes rather than Quantities: this module is the physics, and the
    units contract belongs to the representation. ``records`` is where these
    become ``Quantity`` values, and that separation is deliberate.
    """

    case_id: str
    length_m: float
    velocity_m_s: float
    diffusivity_m2_s: float
    end_time_s: float
    discretization: TransportDiscretization
    scheme: AdvectionScheme
    transient: bool

    def __post_init__(self) -> None:
        if not str(self.case_id).strip():
            raise TransportProbeError("case requires a non-empty case_id")
        for label in ("length_m", "end_time_s"):
            if not (math.isfinite(getattr(self, label)) and getattr(self, label) > 0):
                raise TransportProbeError(f"{label} must be finite and > 0")
        if not math.isfinite(self.velocity_m_s) or self.velocity_m_s == 0.0:
            raise TransportProbeError("velocity_m_s must be finite and non-zero")
        if not math.isfinite(self.diffusivity_m2_s) or self.diffusivity_m2_s < 0.0:
            raise TransportProbeError("diffusivity_m2_s must be finite and >= 0")
        object.__setattr__(self, "scheme", AdvectionScheme(self.scheme))

    # -- derived numbers ----------------------------------------------------
    @property
    def dx_m(self) -> float:
        return self.length_m / self.discretization.n_cells

    @property
    def dt_s(self) -> float:
        return self.end_time_s / self.discretization.n_steps

    @property
    def peclet(self) -> float:
        """Global Peclet number ``u L / D``. A property of the *physics*."""
        if self.diffusivity_m2_s == 0.0:
            return math.inf
        return self.velocity_m_s * self.length_m / self.diffusivity_m2_s

    @property
    def cell_peclet(self) -> float:
        """``u dx / D``. A property of the physics **and the mesh** together.

        This is the number the milestone cares about: it is a validity
        criterion that cannot be evaluated from the problem statement alone,
        because half of it lives in the discretization.
        """
        if self.diffusivity_m2_s == 0.0:
            return math.inf
        return abs(self.velocity_m_s) * self.dx_m / self.diffusivity_m2_s

    @property
    def inverse_cell_peclet(self) -> float:
        """``D / (u dx)`` — the same criterion as :attr:`cell_peclet`, finite.

        ``Pe_cell <= 2`` and ``1/Pe_cell >= 0.5`` are the *same* condition, and
        the reciprocal is defined and finite at ``D = 0``, where the cell Peclet
        number is genuinely infinite. Which of the two a model declares is a
        choice of parameterisation, and it decides whether the criterion can be
        expressed as a ``Quantity`` at all in the pure-advection limit.
        """
        return self.diffusivity_m2_s / (abs(self.velocity_m_s) * self.dx_m)

    @property
    def physical_id(self) -> str:
        """Identity of the PHYSICAL problem, excluding mesh and scheme.

        The baseline domain has the same idea in ``ConductionSlab.fingerprint``,
        and for the same reason: a refinement study is only a refinement study
        if every rung is the same physics. ``case_id`` deliberately includes the
        mesh and the scheme, so it cannot serve here.
        """
        regime = "transient" if self.transient else "steady"
        return (
            f"advdiff-{regime}"
            f"-u{self.velocity_m_s:g}"
            f"-d{self.diffusivity_m2_s:g}"
            f"-l{self.length_m:g}"
            f"-t{self.end_time_s:g}"
        )

    @property
    def nodes_m(self) -> tuple[float, ...]:
        return tuple(
            i * self.dx_m for i in range(self.discretization.n_nodes)
        )

    def with_discretization(
        self, discretization: TransportDiscretization
    ) -> "TransportCase":
        """The same physics at a different resolution.

        PROBE D uses this: every rung must be the same science, differing only
        numerically, or nothing measured across rungs is about discretization.
        """
        return TransportCase(
            case_id=self.case_id,
            length_m=self.length_m,
            velocity_m_s=self.velocity_m_s,
            diffusivity_m2_s=self.diffusivity_m2_s,
            end_time_s=self.end_time_s,
            discretization=discretization,
            scheme=self.scheme,
            transient=self.transient,
        )

    def with_scheme(self, scheme: AdvectionScheme) -> "TransportCase":
        """The same science and the same mesh, discretized differently."""
        return TransportCase(
            case_id=self.case_id,
            length_m=self.length_m,
            velocity_m_s=self.velocity_m_s,
            diffusivity_m2_s=self.diffusivity_m2_s,
            end_time_s=self.end_time_s,
            discretization=self.discretization,
            scheme=scheme,
            transient=self.transient,
        )

    def with_velocity(self, velocity_m_s: float) -> "TransportCase":
        """The same everything, transported the other way. PROBE E uses this."""
        return TransportCase(
            case_id=self.case_id,
            length_m=self.length_m,
            velocity_m_s=velocity_m_s,
            diffusivity_m2_s=self.diffusivity_m2_s,
            end_time_s=self.end_time_s,
            discretization=self.discretization,
            scheme=self.scheme,
            transient=self.transient,
        )


# =============================================================================
# The frozen configuration. Preregistered; not tunable.
# =============================================================================

#: ``u L / D = 1 * 1 / 0.025 = 40``.
FROZEN_LENGTH_M = 1.0
FROZEN_VELOCITY_M_S = 1.0
FROZEN_DIFFUSIVITY_M2_S = 0.025
FROZEN_PECLET = 40.0

#: ``u t + 4 sqrt(D t) = 0.2 + 4 sqrt(0.005) = 0.483 <= 0.5 L``. The front and
#: its diffusive spread stay clear of the outflow boundary, which is what makes
#: the semi-infinite reference applicable at all. See ``ogata_banks``.
FROZEN_END_TIME_S = 0.2

#: ``Pe_cell in {5, 2.5, 1, 0.5, 0.25}`` — straddling the boundedness threshold.
CASE_S_CELL_COUNTS = (8, 16, 40, 80, 160)

#: ``Pe_cell <= 2``, stated in the reciprocal form the model actually declares.
MIN_INVERSE_CELL_PECLET = 0.5

#: The physically admissible range of the transported scalar for CASE S and
#: CASE T. Both are bounded by their own boundary and initial data: a linear
#: transport equation with a maximum principle cannot produce a value outside
#: the range of its data. **Nothing in the platform can currently state this.**
ADMISSIBLE_MIN = 0.0
ADMISSIBLE_MAX = 1.0


def case_s(
    n_cells: int, scheme: AdvectionScheme = AdvectionScheme.CENTRAL
) -> TransportCase:
    """CASE S — steady, Dirichlet-Dirichlet. No initial condition."""
    return TransportCase(
        case_id=f"case-s-n{n_cells}-{scheme.value}",
        length_m=FROZEN_LENGTH_M,
        velocity_m_s=FROZEN_VELOCITY_M_S,
        diffusivity_m2_s=FROZEN_DIFFUSIVITY_M2_S,
        end_time_s=FROZEN_END_TIME_S,  # carried, unused: the case is steady
        discretization=TransportDiscretization(n_cells=n_cells, n_steps=1),
        scheme=scheme,
        transient=False,
    )


def case_t(
    n_cells: int = 160,
    n_steps: int = 200,
    scheme: AdvectionScheme = AdvectionScheme.CENTRAL,
) -> TransportCase:
    """CASE T — transient, Dirichlet inflow, homogeneous Neumann outflow."""
    return TransportCase(
        case_id=f"case-t-n{n_cells}-{scheme.value}",
        length_m=FROZEN_LENGTH_M,
        velocity_m_s=FROZEN_VELOCITY_M_S,
        diffusivity_m2_s=FROZEN_DIFFUSIVITY_M2_S,
        end_time_s=FROZEN_END_TIME_S,
        discretization=TransportDiscretization(n_cells=n_cells, n_steps=n_steps),
        scheme=scheme,
        transient=True,
    )


def case_n(n_cells: int = 160) -> TransportCase:
    """CASE N — ``D = 0``. Representation only; never handed to a solver.

    At ``D = 0`` the equation is first order and exactly **one** boundary
    condition is well posed. CASE T's two-condition set is therefore an
    over-specification, and the change is driven by a *parameter value*. That
    is the whole point of this case, and it costs zero solves.
    """
    return TransportCase(
        case_id=f"case-n-n{n_cells}-pure-advection",
        length_m=FROZEN_LENGTH_M,
        velocity_m_s=FROZEN_VELOCITY_M_S,
        diffusivity_m2_s=0.0,
        end_time_s=FROZEN_END_TIME_S,
        discretization=TransportDiscretization(n_cells=n_cells, n_steps=200),
        scheme=AdvectionScheme.UPWIND,
        transient=True,
    )


# =============================================================================
# Numerics
# =============================================================================

def solve_tridiagonal(
    sub: Sequence[float],
    diag: Sequence[float],
    sup: Sequence[float],
    rhs: Sequence[float],
) -> tuple[float, ...]:
    """Thomas algorithm. ``sub[0]`` and ``sup[-1]`` are ignored.

    No pivoting: every system this probe assembles is either diagonally
    dominant (upwind, and both transient schemes at the frozen ``dt``) or a
    small well-conditioned central-difference system whose failure mode is
    oscillation rather than breakdown. A zero pivot is refused loudly rather
    than producing a number nobody can attribute.
    """
    n = len(diag)
    if not (len(sub) == len(sup) == len(rhs) == n):
        raise TransportProbeError("tridiagonal bands must have equal length")
    c_prime = [0.0] * n
    d_prime = [0.0] * n
    pivot = diag[0]
    if pivot == 0.0:
        raise TransportProbeError("zero pivot at row 0")
    c_prime[0] = sup[0] / pivot
    d_prime[0] = rhs[0] / pivot
    for i in range(1, n):
        pivot = diag[i] - sub[i] * c_prime[i - 1]
        if pivot == 0.0:
            raise TransportProbeError(f"zero pivot at row {i}")
        c_prime[i] = sup[i] / pivot if i < n - 1 else 0.0
        d_prime[i] = (rhs[i] - sub[i] * d_prime[i - 1]) / pivot
    solution = [0.0] * n
    solution[-1] = d_prime[-1]
    for i in range(n - 2, -1, -1):
        solution[i] = d_prime[i] - c_prime[i] * solution[i + 1]
    return tuple(solution)


def solve_steady(case: TransportCase) -> tuple[float, ...]:
    """CASE S. Returns the nodal field, ``n_cells + 1`` values.

    Non-dimensionalized by ``dx^2 / D`` so the only free number is the cell
    Peclet ``P``:

        central   -(1 + P/2) c_{i-1} + 2 c_i + (P/2 - 1) c_{i+1} = 0
        upwind    -(1 + P)   c_{i-1} + (2 + P) c_i - c_{i+1}     = 0

    The upwind rows are an M-matrix — positive diagonal, non-positive
    off-diagonals, weak diagonal dominance — so the discrete solution obeys a
    maximum principle at every ``P``. The central rows are not, once
    ``P > 2`` flips the sign of the super-diagonal coefficient. That single
    sign is the whole boundedness story.
    """
    if case.diffusivity_m2_s <= 0.0:
        raise TransportProbeError(
            "solve_steady requires D > 0; CASE N is representation-only"
        )
    n = case.discretization.n_cells
    p = case.velocity_m_s * case.dx_m / case.diffusivity_m2_s
    left, right = 1.0, 0.0  # c(0) = 1, c(L) = 0

    size = n - 1  # interior nodes 1 .. n-1
    sub = [0.0] * size
    diag = [0.0] * size
    sup = [0.0] * size
    rhs = [0.0] * size
    for k in range(size):
        if case.scheme is AdvectionScheme.CENTRAL:
            a, b, c = -(1.0 + p / 2.0), 2.0, (p / 2.0 - 1.0)
        else:
            a, b, c = -(1.0 + p), (2.0 + p), -1.0
        sub[k], diag[k], sup[k] = a, b, c
        if k == 0:
            rhs[k] -= a * left
        if k == size - 1:
            rhs[k] -= c * right

    interior = solve_tridiagonal(sub, diag, sup, rhs)
    return (left, *interior, right)


def solve_transient(case: TransportCase) -> tuple[float, ...]:
    """CASE T. Backward Euler to ``end_time``. Returns the final nodal field.

    Node 0 is Dirichlet. Node ``N`` carries the homogeneous Neumann outflow,
    imposed by reflection through a ghost node ``c_{N+1} = c_{N-1}``, which
    makes the diffusive stencil ``2(c_{N-1} - c_N)/dx^2`` there.

    Note what the reflection does to the central scheme: it makes the advective
    term at the outflow node **identically zero**, because
    ``(c_{N+1} - c_{N-1})/2dx = 0`` by construction. The upwind scheme keeps a
    real advective term there. Two legitimate discretizations of one boundary
    condition therefore disagree about what that boundary *does* — recorded
    here because it is exactly the kind of thing that lives only in source
    code today.
    """
    if not case.transient:
        raise TransportProbeError("solve_transient requires a transient case")
    if case.diffusivity_m2_s <= 0.0:
        raise TransportProbeError(
            "solve_transient requires D > 0; CASE N is representation-only"
        )
    n = case.discretization.n_cells
    dx, dt = case.dx_m, case.dt_s
    r = case.diffusivity_m2_s * dt / (dx * dx)
    s = case.velocity_m_s * dt / dx
    left = 1.0  # c(0, t) = 1

    field = [0.0] * (n + 1)  # c(x, 0) = 0
    field[0] = left

    size = n  # unknowns 1 .. n
    for _ in range(case.discretization.n_steps):
        sub = [0.0] * size
        diag = [0.0] * size
        sup = [0.0] * size
        rhs = [0.0] * size
        for k in range(size):
            i = k + 1
            if i < n:  # interior
                if case.scheme is AdvectionScheme.CENTRAL:
                    a, b, c = -(s / 2.0) - r, 1.0 + 2.0 * r, (s / 2.0) - r
                else:
                    a, b, c = -s - r, 1.0 + s + 2.0 * r, -r
            else:  # outflow node, ghost reflection
                if case.scheme is AdvectionScheme.CENTRAL:
                    a, b, c = -2.0 * r, 1.0 + 2.0 * r, 0.0
                else:
                    a, b, c = -(s + 2.0 * r), 1.0 + s + 2.0 * r, 0.0
            sub[k], diag[k], sup[k] = a, b, c
            rhs[k] = field[i]
            if k == 0:
                rhs[k] -= a * left
        updated = solve_tridiagonal(sub, diag, sup, rhs)
        field = [left, *updated]
    return tuple(field)


# =============================================================================
# Independent references
# =============================================================================

def steady_reference(case: TransportCase, x_m: float) -> float:
    """Exact solution of CASE S.

        c(x) = (exp(Pe x/L) - exp(Pe)) / (1 - exp(Pe))

    Evaluated in a rearranged form that does not overflow at ``Pe = 40``:
    dividing through by ``exp(Pe)`` gives ``1 - exp(Pe (x/L - 1))``, whose
    exponent is non-positive everywhere on the interval.
    """
    if case.diffusivity_m2_s <= 0.0:
        raise TransportProbeError("steady_reference requires D > 0")
    pe = case.peclet
    xi = x_m / case.length_m
    return 1.0 - math.exp(pe * (xi - 1.0))


def _log_erfc(z: float) -> float:
    """``log(erfc(z))``, evaluated without underflowing for large ``z``.

    ``math.erfc`` underflows to exactly 0 around ``z ~ 27``, and the
    Ogata-Banks second term multiplies it by ``exp(u x / D)``, which is
    ``exp(40)`` at the far end. Computing the product naively would give
    ``inf * 0``. Working in log space keeps the product exact where it matters
    and correctly negligible where it does not.
    """
    value = math.erfc(z)
    if value > 0.0:
        return math.log(value)
    # Asymptotic expansion, valid precisely in the regime where erfc underflows.
    return -z * z - math.log(z * math.sqrt(math.pi)) + math.log1p(-1.0 / (2.0 * z * z))


def ogata_banks(case: TransportCase, x_m: float, t_s: float) -> float:
    """Ogata-Banks semi-infinite solution, the CASE T reference.

        c(x,t) = 1/2 [ erfc((x - ut)/(2 sqrt(Dt)))
                       + exp(ux/D) erfc((x + ut)/(2 sqrt(Dt))) ]

    **This reference is semi-infinite and the probe's domain is finite.** The
    baseline domain deliberately chose a single Fourier mode so that its
    reference carried no approximation of its own; this probe gives that up, and
    the concession is recorded rather than hidden. It is applicable only inside
    the frozen window ``u t + 4 sqrt(D t) <= L/2`` (see
    :func:`reference_window_margin`), where the front and its diffusive spread
    have not yet felt the outflow boundary. Agreement outside that window
    verifies nothing.
    """
    if t_s <= 0.0:
        return 1.0 if x_m <= 0.0 else 0.0
    u, d = case.velocity_m_s, case.diffusivity_m2_s
    if d <= 0.0:
        raise TransportProbeError("ogata_banks requires D > 0")
    spread = 2.0 * math.sqrt(d * t_s)
    first = math.erfc((x_m - u * t_s) / spread)
    z = (x_m + u * t_s) / spread
    exponent = u * x_m / d + _log_erfc(z)
    second = math.exp(exponent) if exponent > -745.0 else 0.0
    return 0.5 * (first + second)


def reference_window_margin(case: TransportCase) -> float:
    """``L/2 - (u t_end + 4 sqrt(D t_end))``. Positive means applicable.

    Reported as a number rather than asserted as a boolean so the evidence
    document can state the actual margin instead of claiming a binary.
    """
    reach = abs(case.velocity_m_s) * case.end_time_s + 4.0 * math.sqrt(
        case.diffusivity_m2_s * case.end_time_s
    )
    return 0.5 * case.length_m - reach


# =============================================================================
# Interpreted scalars
# =============================================================================

def field_metrics(case: TransportCase, field: Sequence[float]) -> dict[str, float]:
    """The scalars a `ScientificResult` can currently hold.

    Note what this function is: the place where a spatially distributed thing
    is crushed into numbers small enough for the control plane. The milestone's
    question is whether anything downstream can tell that this happened.
    """
    nodes = case.nodes_m
    if len(field) != len(nodes):
        raise TransportProbeError(
            f"field has {len(field)} values for {len(nodes)} nodes"
        )
    midpoint_index = case.discretization.n_cells // 2
    return {
        "c:midpoint": field[midpoint_index],
        "c:max": max(field),
        "c:min": min(field),
        "c:inlet": field[0],
        "c:outlet": field[-1],
    }


def admissibility_violation(field: Sequence[float]) -> float:
    """How far outside ``[0, 1]`` the field strays. Zero means bounded.

    A maximum principle holds for both frozen cases: their data lie in
    ``[0, 1]`` and linear transport cannot manufacture a value outside the
    range of its data. A positive number here is therefore an **unphysical**
    answer, regardless of what any residual says.

    Deliberately returned as a magnitude rather than raised: this probe must be
    able to *record* an inadmissible result and hand it to the platform's own
    checks, which is the measurement. Refusing it here would destroy the
    evidence.
    """
    below = max(0.0, ADMISSIBLE_MIN - min(field))
    above = max(0.0, max(field) - ADMISSIBLE_MAX)
    return max(below, above)
