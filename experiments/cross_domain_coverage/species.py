"""CONSUMER C — closed isothermal batch, three species, two reactions.

    (R1)  A <-> B      first order both ways,  k1f, k1r
    (R2)  2B  -> C     second order in B, irreversible,  k2

Isothermal at 320 K, constant volume, no flow. State ``(c_A, c_B, c_C)``, all
mol/m^3.

    nu = [[-1, +1,  0],
          [ 0, -2, +1]]          stoichiometric matrix, reactions x species

    r  = (k1f c_A - k1r c_B,  k2 c_B^2)
    dc/dt = nu^T r

THE CONSERVED QUANTITY IS WEIGHTED, AND THAT IS THE MEASUREMENT
---------------------------------------------------------------
``c_A + c_B + 2 c_C`` is invariant. The ``2`` comes from ``nu`` and from nowhere
else: a reader holding the three concentrations, their units, and every typed
record this platform can produce **cannot derive it**, because the stoichiometric
coefficients are not on any record. An unweighted sum is not conserved and a
reader that assumed one would report a violated conservation law for a
perfectly conserved system.

WHY ISOTHERMAL, AND WHY CLOSED
-------------------------------
Both are deliberate costs, paid to buy differentiation.

**Isothermal** eliminates overlap with the existing `kinetics/cstr`, which is a
non-isothermal reactor with Arrhenius ``k(T)``, stiffness, steady-state
multiplicity, and two coupled states of *different* dimensions. Keeping a
temperature here would have made this consumer a weaker re-run of that one.
What the CSTR structurally lacks, and this has: **three dependent quantities of
the same dimension**, **stoichiometry as data**, and a **conservation relation
across the state vector**. Species B is never represented anywhere in the CSTR.

**Closed** — no flow — eliminates the shared lineage with Consumer B. The
Modelica specification records that across/through connector pairs were
insufficient for bidirectional convective transport of chemical composition,
which is a concept sitting exactly on the B/C intersection. A flow reactor here
would have made B and C one data point about orientation rather than two
independent ones.

WHAT IS DELIBERATELY NOT BUILT
------------------------------
No energy balance, no Arrhenius, no flow, no multiplicity, no equilibrium
solver, no thermochemistry database.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

CONCENTRATION_UNIT = "mol / m**3"
TIME_UNIT = "second"
TEMPERATURE_UNIT = "kelvin"
FIRST_ORDER_RATE_UNIT = "1 / second"
SECOND_ORDER_RATE_UNIT = "m**3 / (mol * second)"

#: Species names, in the order they index the state vector and ``nu``.
SPECIES: tuple[str, ...] = ("A", "B", "C")

#: Reaction labels, in the order they index ``nu`` and the rate vector.
REACTIONS: tuple[str, ...] = ("R1", "R2")

#: Rows are reactions, columns are species. This object is the finding: there
#: is no typed home for it. `ScientificValue` is a closed union of scalars, so
#: a `ScientificParameter` cannot carry a matrix.
STOICHIOMETRY: tuple[tuple[int, ...], ...] = (
    (-1, +1, 0),   # R1:  A -> B
    (0, -2, +1),   # R2:  2B -> C
)

#: The weights of the conserved quantity, derived from the null space of nu.
#: `w . nu^T = 0`, so `w . c` is invariant. Stated here as the answer the
#: measurement checks against, NOT as something a records reader could recover.
CONSERVED_WEIGHTS: tuple[float, ...] = (1.0, 1.0, 2.0)

FROZEN_TEMPERATURE_K = 320.0


class SpeciesProbeError(Exception):
    """A configuration this probe refuses."""


@dataclass(frozen=True)
class BatchCase:
    """One frozen probe instance, in SI magnitudes."""

    case_id: str
    k1f_per_s: float
    k1r_per_s: float
    k2_m3_per_mol_s: float
    initial: tuple[float, float, float]
    end_time_s: float
    n_steps: int
    temperature_k: float = FROZEN_TEMPERATURE_K

    def __post_init__(self) -> None:
        if len(self.initial) != len(SPECIES):
            raise SpeciesProbeError(
                f"initial state must have {len(SPECIES)} entries, got "
                f"{len(self.initial)}"
            )
        for name, value in zip(SPECIES, self.initial):
            if value < 0.0:
                raise SpeciesProbeError(
                    f"initial concentration of {name} must be >= 0, got {value}"
                )
        for label in ("k1f_per_s", "k1r_per_s", "k2_m3_per_mol_s"):
            if getattr(self, label) < 0.0:
                raise SpeciesProbeError(f"{label} must be >= 0")
        if self.n_steps < 1:
            raise SpeciesProbeError("n_steps must be at least 1")
        if self.end_time_s <= 0.0:
            raise SpeciesProbeError("end_time_s must be positive")

    @property
    def dt(self) -> float:
        return self.end_time_s / self.n_steps

    def with_steps(self, n_steps: int) -> "BatchCase":
        """The same chemistry, integrated more finely."""
        return BatchCase(
            case_id=self.case_id,
            k1f_per_s=self.k1f_per_s,
            k1r_per_s=self.k1r_per_s,
            k2_m3_per_mol_s=self.k2_m3_per_mol_s,
            initial=self.initial,
            end_time_s=self.end_time_s,
            n_steps=n_steps,
            temperature_k=self.temperature_k,
        )


def case_c(n_steps: int = 2000) -> BatchCase:
    """CASE C1 — both reactions active."""
    return BatchCase(
        case_id="case-c-full",
        k1f_per_s=0.8,
        k1r_per_s=0.2,
        k2_m3_per_mol_s=0.05,
        initial=(10.0, 0.0, 0.0),
        end_time_s=20.0,
        n_steps=n_steps,
    )


def case_c_linear(n_steps: int = 2000) -> BatchCase:
    """CASE C2 — ``k2 = 0``. A linear reversible pair with an exact solution."""
    return BatchCase(
        case_id="case-c-linear",
        k1f_per_s=0.8,
        k1r_per_s=0.2,
        k2_m3_per_mol_s=0.0,
        initial=(10.0, 0.0, 0.0),
        end_time_s=20.0,
        n_steps=n_steps,
    )


# =============================================================================
# The physics
# =============================================================================

def reaction_rates(case: BatchCase, state: tuple[float, ...]) -> tuple[float, ...]:
    """``(r1, r2)`` in mol/(m^3 s)."""
    c_a, c_b, _ = state
    return (
        case.k1f_per_s * c_a - case.k1r_per_s * c_b,
        case.k2_m3_per_mol_s * c_b * c_b,
    )


def derivative(case: BatchCase, state: tuple[float, ...]) -> tuple[float, ...]:
    """``dc/dt = nu^T r``. The stoichiometric matrix is the whole model."""
    rates = reaction_rates(case, state)
    return tuple(
        sum(STOICHIOMETRY[reaction][species] * rates[reaction]
            for reaction in range(len(REACTIONS)))
        for species in range(len(SPECIES))
    )


def integrate(case: BatchCase) -> tuple[tuple[float, ...], list[tuple[float, ...]]]:
    """Classical RK4 at fixed step. Returns the final state and the trajectory.

    RK4 rather than anything adaptive because the conservation check must be a
    statement about the *equations*, not about an error controller: the
    invariant is preserved by RK4 to round-off for any step size, since every
    stage derivative already lies in the null space of the weights.
    """
    state = tuple(float(v) for v in case.initial)
    trajectory = [state]
    dt = case.dt

    def add(a: tuple[float, ...], b: tuple[float, ...], scale: float):
        return tuple(x + scale * y for x, y in zip(a, b))

    for _ in range(case.n_steps):
        k1 = derivative(case, state)
        k2 = derivative(case, add(state, k1, dt / 2.0))
        k3 = derivative(case, add(state, k2, dt / 2.0))
        k4 = derivative(case, add(state, k3, dt))
        state = tuple(
            s + dt / 6.0 * (a + 2.0 * b + 2.0 * c + d)
            for s, a, b, c, d in zip(state, k1, k2, k3, k4)
        )
        trajectory.append(state)
    return state, trajectory


def conserved_quantity(state: tuple[float, ...]) -> float:
    """``c_A + c_B + 2 c_C``. Requires ``nu``; not derivable from the record."""
    return sum(w * c for w, c in zip(CONSERVED_WEIGHTS, state))


def naive_total(state: tuple[float, ...]) -> float:
    """``c_A + c_B + c_C`` — what a reader without ``nu`` would compute.

    Included so the finding is a *measurement* rather than an assertion: this
    quantity is **not** conserved, and the drift a reader would report is the
    size of the error caused by the missing stoichiometry.
    """
    return sum(state)


def conservation_drift(trajectory: list[tuple[float, ...]]) -> float:
    """Largest absolute departure of the weighted invariant from its start."""
    reference = conserved_quantity(trajectory[0])
    return max(abs(conserved_quantity(s) - reference) for s in trajectory)


def naive_drift(trajectory: list[tuple[float, ...]]) -> float:
    """Largest departure of the *unweighted* sum. Expected to be large."""
    reference = naive_total(trajectory[0])
    return max(abs(naive_total(s) - reference) for s in trajectory)


# =============================================================================
# The exact reference for CASE C2
# =============================================================================

def linear_reference(case: BatchCase, t: float) -> tuple[float, float, float]:
    """Exact solution of the ``k2 = 0`` sub-case.

    With C inert, ``c_A + c_B`` is constant at ``S`` and

        c_A(t) = c_A_eq + (c_A0 - c_A_eq) exp(-(k1f + k1r) t)
        c_A_eq = k1r S / (k1f + k1r)

    so the equilibrium ratio is ``c_B/c_A = k1f/k1r`` exactly.
    """
    if case.k2_m3_per_mol_s != 0.0:
        raise SpeciesProbeError("linear_reference requires k2 = 0")
    c_a0, c_b0, c_c0 = case.initial
    total = c_a0 + c_b0
    rate_sum = case.k1f_per_s + case.k1r_per_s
    if rate_sum <= 0.0:
        return (c_a0, c_b0, c_c0)
    c_a_eq = case.k1r_per_s * total / rate_sum
    c_a = c_a_eq + (c_a0 - c_a_eq) * math.exp(-rate_sum * t)
    return (c_a, total - c_a, c_c0)


def equilibrium_ratio(case: BatchCase) -> float:
    """``k1f / k1r``, the exact equilibrium ``c_B/c_A`` of the linear sub-case."""
    if case.k1r_per_s == 0.0:
        return math.inf
    return case.k1f_per_s / case.k1r_per_s


# =============================================================================
# Interpreted scalars
# =============================================================================

def state_metrics(case: BatchCase, state: tuple[float, ...]) -> dict[str, float]:
    """The scalars a `ScientificResult` can currently hold.

    Note that ``c:A``, ``c:B`` and ``c:C`` are **three quantities of one
    dimension**. Nothing on any record says they are concentrations of distinct
    chemical species rather than three unrelated numbers that happen to share a
    unit — which is the `SpeciesIdentity` measurement.
    """
    metrics = {f"c:{name}": value for name, value in zip(SPECIES, state)}
    metrics["conserved:weighted"] = conserved_quantity(state)
    metrics["conserved:naive"] = naive_total(state)
    return metrics


def admissibility_violation(trajectory: list[tuple[float, ...]]) -> float:
    """How far any concentration goes negative. Zero is the only physical value.

    A negative concentration is unphysical regardless of what any residual says
    — the same class of statement as the mechanics patch-test identity, the
    transport error bound and the pendulum constraint residual, and
    deliberately of a *different kind* from each of them.
    """
    return max(0.0, max(-min(state) for state in trajectory))
