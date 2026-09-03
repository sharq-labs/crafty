"""CONSUMER D — planar pendulum in Cartesian coordinates. A genuine DAE.

    states (x, y, vx, vy),  multiplier lambda
    x_dot = vx        y_dot = vy
    m vx_dot = -2 lambda x
    m vy_dot = -m g - 2 lambda y
    g(x, y) = x^2 + y^2 - L^2 = 0            <-- an ALGEBRAIC relation among unknowns

L = 1 m, m = 1 kg, g = 9.80665 m/s^2.

WHY NOT A CONTROLLED PLANT
--------------------------
A PI-controlled first-order plant would be **isomorphic to the existing
`thermal_lumped`** — one first-order ODE with a `CONTROL` variable — which is
why no controller appears here at all. Against `kinetics/cstr`: that is two
coupled ODEs with no algebraic relation among unknowns.

WHAT THIS ADDS THAT NOTHING ELSE IN THE REPOSITORY HAS
-------------------------------------------------------
1. **An algebraic equation among unknowns.** This is *not*
   `ConstraintDefinition`, which is `metric OP bound` — a study-level acceptance
   test comparing one produced number against a fixed scalar. ``g = 0`` relates
   two unknowns to each other and must hold at every instant of the solution.
2. **A differential/algebraic variable partition.** SUNDIALS IDA documents that
   the caller must identify the differential and algebraic sub-vectors, and
   `VariableRole` has four members — `DESIGN`, `STATE`, `OBSERVABLE`,
   `CONTROL` — none of which makes that distinction. ``lambda`` is a genuine
   unknown solved for at every step and it is not a state: it has no initial
   value and no derivative.
3. **Initial conditions that are a RELATION, not independent values.**
   `InitialCondition.value` is one `Quantity` with no reference to any other
   variable. Four such records can each be individually valid and jointly
   inconsistent, because a consistent start requires ``g = 0`` *and*
   ``g_dot = 0``.
4. **A realization that changes what the unknowns ARE.** The ``theta``-form is
   the same scientific model with a one-dimensional state vector. Every previous
   realization pair in this repository — central/upwind, native/ngspice — kept
   the same unknowns and changed only how they were computed.

WHAT IS DELIBERATELY NOT BUILT
------------------------------
No controller, no generic control framework, no multibody library, no event
handling, no hybrid systems, no index-reduction machinery beyond the single
hard-coded stabilised form below.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

LENGTH_UNIT = "meter"
TIME_UNIT = "second"
MASS_UNIT = "kilogram"
VELOCITY_UNIT = "meter / second"
ENERGY_UNIT = "joule"
ANGLE_UNIT = "radian"
#: lambda multiplies a length-squared constraint, so 2*lambda*x is a force.
MULTIPLIER_UNIT = "newton / meter"
TORQUE_UNIT = "newton * meter"

GRAVITY_M_S2 = 9.80665
FROZEN_LENGTH_M = 1.0
FROZEN_MASS_KG = 1.0
FROZEN_THETA0_RAD = 0.5

#: Baumgarte stabilisation gains. Not physics: a numerical device that keeps the
#: index-reduced form from drifting off the constraint manifold. That it is
#: *numerical* is exactly why it belongs to a realization and not to the model,
#: and this probe measures whether any record can say so.
BAUMGARTE_ALPHA = 10.0
BAUMGARTE_BETA = 10.0


class DynamicsFormulation(str, Enum):
    """Which set of unknowns the realization solves for.

    The two members do not differ in *how* they compute the same unknowns —
    they differ in **what the unknowns are**. That is the axis every previous
    realization pair in this repository held constant.
    """

    #: (x, y, vx, vy) with lambda solved algebraically. Four states, one
    #: multiplier, one constraint.
    CARTESIAN_INDEX1 = "cartesian_index_reduced_baumgarte"
    #: (theta, omega). Two states, no constraint, no multiplier.
    ANGULAR_ODE = "angular_minimal_coordinate"


class DynamicsProbeError(Exception):
    """A configuration this probe refuses."""


@dataclass(frozen=True)
class PendulumCase:
    """One frozen probe instance, in SI magnitudes."""

    case_id: str
    theta0_rad: float = FROZEN_THETA0_RAD
    length_m: float = FROZEN_LENGTH_M
    mass_kg: float = FROZEN_MASS_KG
    end_time_s: float = 4.0
    n_steps: int = 40000

    def __post_init__(self) -> None:
        for label in ("length_m", "mass_kg", "end_time_s"):
            if getattr(self, label) <= 0.0:
                raise DynamicsProbeError(f"{label} must be positive")
        if self.n_steps < 1:
            raise DynamicsProbeError("n_steps must be at least 1")

    @property
    def dt(self) -> float:
        return self.end_time_s / self.n_steps

    @property
    def small_angle_period_s(self) -> float:
        """``2 pi sqrt(L/g)``. Exact only in the limit; used as a sanity anchor."""
        return 2.0 * math.pi * math.sqrt(self.length_m / GRAVITY_M_S2)

    @property
    def exact_period_s(self) -> float:
        """First-order finite-amplitude correction, ``T0 (1 + theta0^2/16)``."""
        return self.small_angle_period_s * (1.0 + self.theta0_rad**2 / 16.0)

    def cartesian_initial(self) -> tuple[float, float, float, float]:
        """``(x, y, vx, vy)`` at rest, hanging at ``theta0`` from the downward
        vertical. Consistent by construction: ``g = 0`` and ``g_dot = 0``."""
        return (
            self.length_m * math.sin(self.theta0_rad),
            -self.length_m * math.cos(self.theta0_rad),
            0.0,
            0.0,
        )


def case_d(n_steps: int = 40000) -> PendulumCase:
    return PendulumCase(case_id="case-d-free-swing", n_steps=n_steps)


# =============================================================================
# The constraint, and the multiplier that enforces it
# =============================================================================

def constraint(case: PendulumCase, state: tuple[float, ...]) -> float:
    """``g = x^2 + y^2 - L^2``. Zero on the manifold."""
    x, y = state[0], state[1]
    return x * x + y * y - case.length_m**2


def constraint_velocity(state: tuple[float, ...]) -> float:
    """``g_dot = 2(x vx + y vy)``. Zero for a consistent state."""
    x, y, vx, vy = state
    return 2.0 * (x * vx + y * vy)


def multiplier(case: PendulumCase, state: tuple[float, ...]) -> float:
    """``lambda``, solved from the twice-differentiated constraint.

    Differentiating ``g`` twice and substituting the equations of motion gives

        g_ddot = 2(vx^2 + vy^2) - 4 lambda (x^2 + y^2)/m - 2 y g

    and Baumgarte replaces ``g_ddot = 0`` with
    ``g_ddot + 2 alpha g_dot + beta^2 g = 0``, which is asymptotically stable
    and pulls the solution back onto the manifold instead of letting it drift.

    ``lambda`` is a genuine unknown of the system, determined at every instant
    by an algebraic equation. It is not a state — it has no initial value and
    no derivative — and `VariableRole` has no member that says so.
    """
    x, y, vx, vy = state
    radius_sq = x * x + y * y
    if radius_sq <= 0.0:
        raise DynamicsProbeError("pendulum passed through the pivot")
    numerator = (
        2.0 * (vx * vx + vy * vy)
        - 2.0 * y * GRAVITY_M_S2
        + 4.0 * BAUMGARTE_ALPHA * (x * vx + y * vy)
        + BAUMGARTE_BETA**2 * constraint(case, state)
    )
    return case.mass_kg * numerator / (4.0 * radius_sq)


def cartesian_derivative(
    case: PendulumCase, state: tuple[float, ...]
) -> tuple[float, ...]:
    """``(x_dot, y_dot, vx_dot, vy_dot)`` with ``lambda`` eliminated."""
    x, y, vx, vy = state
    lam = multiplier(case, state)
    return (
        vx,
        vy,
        -2.0 * lam * x / case.mass_kg,
        -GRAVITY_M_S2 - 2.0 * lam * y / case.mass_kg,
    )


def angular_derivative(
    case: PendulumCase, state: tuple[float, ...]
) -> tuple[float, ...]:
    """``(theta_dot, omega_dot)`` for the minimal-coordinate realization.

    No constraint, no multiplier, two unknowns instead of five. The same
    scientific model.
    """
    theta, omega = state
    return (omega, -(GRAVITY_M_S2 / case.length_m) * math.sin(theta))


# =============================================================================
# Integration
# =============================================================================

def _rk4(case: PendulumCase, state, derivative_fn, dt: float):
    def add(a, b, scale):
        return tuple(x + scale * y for x, y in zip(a, b))

    k1 = derivative_fn(case, state)
    k2 = derivative_fn(case, add(state, k1, dt / 2.0))
    k3 = derivative_fn(case, add(state, k2, dt / 2.0))
    k4 = derivative_fn(case, add(state, k3, dt))
    return tuple(
        s + dt / 6.0 * (a + 2.0 * b + 2.0 * c + d)
        for s, a, b, c, d in zip(state, k1, k2, k3, k4)
    )


def energy(case: PendulumCase, state: tuple[float, ...]) -> float:
    """``½ m v² + m g y``, with ``y`` measured from the pivot."""
    x, y, vx, vy = state
    return 0.5 * case.mass_kg * (vx * vx + vy * vy) + case.mass_kg * GRAVITY_M_S2 * y


def run_cartesian(case: PendulumCase) -> dict[str, object]:
    """CASE D1, the executed realization. Index-reduced, Baumgarte-stabilised."""
    state = case.cartesian_initial()
    initial_energy = energy(case, state)
    worst_constraint = abs(constraint(case, state))
    worst_energy_drift = 0.0
    trajectory = [state]
    for _ in range(case.n_steps):
        state = _rk4(case, state, cartesian_derivative, case.dt)
        trajectory.append(state)
        worst_constraint = max(worst_constraint, abs(constraint(case, state)))
        worst_energy_drift = max(
            worst_energy_drift, abs(energy(case, state) - initial_energy)
        )
    return {
        "formulation": DynamicsFormulation.CARTESIAN_INDEX1,
        "final_state": state,
        "trajectory": trajectory,
        "initial_energy_j": initial_energy,
        "max_constraint_residual_m2": worst_constraint,
        "max_energy_drift_j": worst_energy_drift,
        "final_multiplier": multiplier(case, state),
    }


def run_angular(case: PendulumCase) -> dict[str, object]:
    """The second realization. Different unknowns, same scientific model."""
    state = (case.theta0_rad, 0.0)
    trajectory = [state]
    for _ in range(case.n_steps):
        state = _rk4(case, state, angular_derivative, case.dt)
        trajectory.append(state)
    return {
        "formulation": DynamicsFormulation.ANGULAR_ODE,
        "final_state": state,
        "trajectory": trajectory,
    }


def cartesian_from_angular(
    case: PendulumCase, state: tuple[float, ...]
) -> tuple[float, float, float, float]:
    """Map ``(theta, omega)`` into ``(x, y, vx, vy)`` for comparison."""
    theta, omega = state
    return (
        case.length_m * math.sin(theta),
        -case.length_m * math.cos(theta),
        case.length_m * omega * math.cos(theta),
        case.length_m * omega * math.sin(theta),
    )


def realization_agreement(case: PendulumCase) -> dict[str, float]:
    """Largest position discrepancy between the two realizations.

    Not a tolerance chosen to pass: the two integrate *different state vectors*
    through different equations, so agreement is a real cross-check that the
    constrained form is solving the pendulum and not something adjacent.
    """
    cartesian = run_cartesian(case)
    angular = run_angular(case)
    worst = 0.0
    for lhs, rhs in zip(cartesian["trajectory"], angular["trajectory"]):
        mapped = cartesian_from_angular(case, rhs)
        worst = max(worst, max(abs(a - b) for a, b in zip(lhs[:2], mapped[:2])))
    return {
        "max_position_difference_m": worst,
        "cartesian_constraint_residual_m2": cartesian["max_constraint_residual_m2"],
        "cartesian_energy_drift_j": cartesian["max_energy_drift_j"],
    }


def measured_period_s(case: PendulumCase, result: dict[str, object]) -> float:
    """Period from successive upward zero crossings of ``x``.

    Linear interpolation between the bracketing samples, so the estimate is not
    limited to the step size.
    """
    trajectory = result["trajectory"]
    crossings: list[float] = []
    for index in range(1, len(trajectory)):
        previous, current = trajectory[index - 1][0], trajectory[index][0]
        if previous < 0.0 <= current:
            fraction = -previous / (current - previous)
            crossings.append((index - 1 + fraction) * case.dt)
        if len(crossings) == 2:
            break
    if len(crossings) < 2:
        raise DynamicsProbeError("fewer than two upward crossings observed")
    return crossings[1] - crossings[0]


# =============================================================================
# CASE D3 — inconsistent initial conditions that each validate
# =============================================================================

def inconsistent_initial_state(case: PendulumCase) -> tuple[float, float, float, float]:
    """Four values, each individually reasonable, jointly off the manifold.

    ``(0.5, -0.5, 0, 0)`` sits at radius ``0.707`` on a pendulum of length 1, so
    ``g = -0.5``. Every one of the four numbers is finite, correctly
    dimensioned, and inside any plausible range a `ScientificVariable` could
    declare. The inconsistency is a property of the **set**, and no record
    relates one `InitialCondition` to another.
    """
    return (0.5, -0.5, 0.0, 0.0)


def initial_consistency(
    case: PendulumCase, state: tuple[float, float, float, float]
) -> dict[str, float]:
    """The two residuals a consistent start must satisfy."""
    return {
        "g": constraint(case, state),
        "g_dot": constraint_velocity(state),
    }


# =============================================================================
# CASE D2 — a time-varying input, representation only
# =============================================================================

TORQUE_AMPLITUDE_N_M = 0.2
TORQUE_FREQUENCY_RAD_S = 3.0


def drive_torque(t: float) -> float:
    """``tau(t) = tau0 sin(Omega t)``. Never executed; represented only.

    A `ScientificParameter` holds one `Quantity` — a single magnitude and a
    unit. There is no typed way to say that an input is a *function of time*,
    so this consumer can state the amplitude and the frequency and cannot state
    that they describe a signal.
    """
    return TORQUE_AMPLITUDE_N_M * math.sin(TORQUE_FREQUENCY_RAD_S * t)


# =============================================================================
# Interpreted scalars
# =============================================================================

def state_metrics(case: PendulumCase, result: dict[str, object]) -> dict[str, float]:
    """The scalars a `ScientificResult` can currently hold."""
    state = result["final_state"]
    if result["formulation"] is DynamicsFormulation.ANGULAR_ODE:
        state = cartesian_from_angular(case, state)
    x, y, vx, vy = state
    return {
        "x:final": x,
        "y:final": y,
        "vx:final": vx,
        "vy:final": vy,
        "energy:final": energy(case, state),
        "constraint_residual:max": float(
            result.get("max_constraint_residual_m2", 0.0)
        ),
    }


def admissibility_violation(case: PendulumCase, result: dict[str, object]) -> float:
    """Largest constraint residual. Non-zero is off the manifold, i.e. unphysical.

    A fourth *kind* of admissibility evidence: not an exactness identity
    (mechanics), not a discretization error bound (transport), not a
    conservation invariant (species), but a residual of an algebraic relation
    the solution is required to satisfy.
    """
    if result["formulation"] is DynamicsFormulation.ANGULAR_ODE:
        return 0.0  # the minimal coordinate satisfies it identically
    return float(result["max_constraint_residual_m2"])
