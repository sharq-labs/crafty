"""The steady-state reference's bracketing scan is array arithmetic now.

The scan that locates sign changes is evaluated over the whole temperature grid
at once rather than one Python call per point. That is a pure speed change only
if it is *bit*-identical: a residual that differed by one unit in the last place
could put a sign change on the other side of a grid node, hand Brent a different
bracket, and move a reported steady state. A reported steady state is what K1
compares its end states against.

So these tests do not assert closeness. They assert equality, against the scalar
formulation, on every preregistered regime.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.engcore.domains.kinetics.cstr.reference import (
    _R_J_PER_MOL_K,
    steady_state_residual,
    steady_states,
)
from src.engcore.domains.kinetics.cstr.errors import ReactorConfigurationError
from src.engcore.domains.kinetics.cstr.validation import (
    MAX_VALID_TEMPERATURE_K,
    MIN_VALID_TEMPERATURE_K,
)
from experiments.kinetics_k1.k1_config import REGIMES

SCAN_POINTS = 20001


def _physics(run) -> dict:
    return dict(
        dilution_rate_per_s=run.operation.dilution_rate_per_s,
        feed_concentration_mol_per_m3=run.operation.caf_mol_per_m3,
        feed_temperature_k=run.operation.tf_k,
        coolant_temperature_k=run.operation.tc_k,
        beta_m3_k_per_mol=run.chemistry.beta_m3_k_per_mol,
        gamma_per_s=run.gamma_per_s,
        k0_per_s=run.chemistry.k0_per_s,
        activation_energy_j_per_mol=run.chemistry.e_j_per_mol,
    )


def _scalar_scan(grid: np.ndarray, physics: dict) -> np.ndarray:
    """The original formulation: one Python call per grid point."""
    return np.array([steady_state_residual(float(t), **physics) for t in grid])


def _vector_scan(grid: np.ndarray, physics: dict) -> np.ndarray:
    """The formulation the reference now uses."""
    a = physics["dilution_rate_per_s"]
    rate = physics["k0_per_s"] * np.exp(
        -physics["activation_energy_j_per_mol"] / (_R_J_PER_MOL_K * grid)
    )
    ca_star = a * physics["feed_concentration_mol_per_m3"] / (a + rate)
    return (
        a * (physics["feed_temperature_k"] - grid)
        + physics["beta_m3_k_per_mol"] * rate * ca_star
        - physics["gamma_per_s"] * (grid - physics["coolant_temperature_k"])
    )


def _brackets(grid: np.ndarray, values: np.ndarray) -> list[tuple[str, int]]:
    """Exactly the bracket-selection rule ``steady_states`` applies."""
    out: list[tuple[str, int]] = []
    for index in range(len(grid) - 1):
        left, right = float(values[index]), float(values[index + 1])
        if left == 0.0:
            out.append(("zero", index))
        elif left * right < 0.0:
            out.append(("sign", index))
    if float(values[-1]) == 0.0:
        out.append(("zero_last", len(grid) - 1))
    return out


REGIME_IDS = [spec.regime_id for spec in REGIMES]


@pytest.mark.parametrize("spec", REGIMES, ids=REGIME_IDS)
def test_the_array_scan_is_bit_identical_to_the_scalar_scan(spec) -> None:
    physics = _physics(spec.build())
    grid = np.linspace(
        MIN_VALID_TEMPERATURE_K, MAX_VALID_TEMPERATURE_K, SCAN_POINTS
    )
    scalar = _scalar_scan(grid, physics)
    vector = _vector_scan(grid, physics)

    # Not allclose. Equal.
    assert np.array_equal(scalar, vector), (
        f"{spec.regime_id}: the array scan disagrees with the scalar scan at "
        f"{int(np.count_nonzero(scalar != vector))} of {SCAN_POINTS} points"
    )


@pytest.mark.parametrize("spec", REGIMES, ids=REGIME_IDS)
def test_both_formulations_bracket_the_same_sign_changes(spec) -> None:
    physics = _physics(spec.build())
    grid = np.linspace(
        MIN_VALID_TEMPERATURE_K, MAX_VALID_TEMPERATURE_K, SCAN_POINTS
    )
    assert _brackets(grid, _scalar_scan(grid, physics)) == _brackets(
        grid, _vector_scan(grid, physics)
    )


@pytest.mark.parametrize("spec", REGIMES, ids=REGIME_IDS)
def test_roots_stay_ordered_and_transversal(spec) -> None:
    """Ordering is part of the contract: the nearest-root comparison uses it."""
    found = steady_states(
        **_physics(spec.build()),
        search_min_k=MIN_VALID_TEMPERATURE_K,
        search_max_k=MAX_VALID_TEMPERATURE_K,
    )
    temperatures = [s.temperature_k for s in found]
    assert temperatures == sorted(temperatures)
    for state in found:
        assert MIN_VALID_TEMPERATURE_K <= state.temperature_k <= MAX_VALID_TEMPERATURE_K


# =====================================================================
# The refusals the scalar residual used to make on every call
# =====================================================================

def _valid_physics() -> dict:
    return _physics(REGIMES[0].build())


@pytest.mark.parametrize(
    "field, bad",
    (
        ("k0_per_s", 0.0),
        ("k0_per_s", -1.0),
        ("activation_energy_j_per_mol", -1.0),
    ),
)
def test_an_invalid_rate_declaration_is_still_refused(field: str, bad: float) -> None:
    """Vectorizing must not turn a refusal into a fabricated residual curve."""
    physics = _valid_physics()
    physics[field] = bad
    with pytest.raises(ReactorConfigurationError):
        steady_states(
            **physics,
            search_min_k=MIN_VALID_TEMPERATURE_K,
            search_max_k=MAX_VALID_TEMPERATURE_K,
        )
