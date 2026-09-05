"""PROPULSION0-EXT — executable evidence for the four coverage gaps.

G1 multiple operating points, G2 two motors, G3 the four missing negative
cases, G4 efficiency classification. Preregistered in
``docs/evidence/propulsion0-ext-preregistration.md``.

**Nothing here is a re-run of PROPULSION0.** Its harness is imported rather than
rebuilt, and its claims are not re-asserted.

**Acceptance is on governing relations, never on frozen numbers.** Every sweep
assertion is a *sign* derived in the preregistration from the governing
equations, or a residual of an equation recomputed from the record. The three
reference magnitudes that appear do so only as loose sanity bands beside such an
assertion.

MODEL-CONSISTENT only: fixture machine constants and handbook material data.
Nothing here is validated against hardware.
"""

from __future__ import annotations

import ast
import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

from engcore.coupling import (
    CouplingOutcome,
    FixedPointCouplingPlan,
    run_fixed_point,
)
from engcore.domains import mechanical_rotational as rot
from engcore.domains import thermal_lumped as lump
from engcore.domains.electrical import conductor_material as cmat
from engcore.scientific.errors import (
    InvalidScientificProblem,
    UnitCompatibilityError,
)
from engcore.scientific.models.definition import (
    ScientificModelDefinition,
    ValidityStatus,
)
from engcore.scientific.units.quantity import Quantity as Q
from engcore.systems.propulsion import drive as pd
from engcore.systems.propulsion import materials as pmat
from engcore.systems.propulsion import models as pmod
from tests.test_propulsion0 import (
    SEED,
    _SolverSpy,
    build_drive,
    machine,
    mechanical_load,
    wire,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
KELVIN = "kelvin"
RAD_S = rot.ANGULAR_VELOCITY_UNIT
NM = rot.TORQUE_UNIT

#: The declaration PROPULSION0 measured, reused unchanged as the sweep's centre.
REFERENCE_VOLTS = 24.0
REFERENCE_K = 0.0295
REFERENCE_K_LOAD = 2.444e-7
REFERENCE_B = 2.0e-5

#: Preregistration §2.6. Bounded above by copper's declared [200, 450] K: the
#: endpoints were scouted for ADMISSIBILITY only, and `k_load = 1.0e-6` was
#: excluded in advance because it leaves that range.
KLOAD_SWEEP = (5.0e-8, 1.0e-7, REFERENCE_K_LOAD, 4.0e-7, 6.0e-7)
B_SWEEP = (2.0e-6, REFERENCE_B, 8.0e-5)

#: A fixed loop resistance for the dense algebraic sweeps. It is a CONTROL
#: imposed on the closed form — the model's own docstring says the loop
#: resistance is an imposed control checked by the evaluator — and holding it
#: fixed is what makes §2.2's nine relations theorems rather than observations.
FIXED_LOOP_OHM = 0.53


# =====================================================================
# Shared machinery
# =====================================================================

@pytest.fixture
def spy(monkeypatch):
    """PROPULSION0's solver spy, imported rather than rebuilt.

    It counts every solver factory this pack can reach, so `spy.calls == []`
    means no solver object was ever constructed — not merely that none was run.
    """
    return _SolverSpy().install(monkeypatch)


@pytest.fixture
def circuit_spy(monkeypatch):
    """A LIVE circuit spy: it replaces the pack's default solver.

    `architecture-falsifier`'s second round found the first version of this
    fixture inert — it returned a callable that was never passed as
    ``circuit_solver=``, so its six `calls == []` assertions were vacuously
    true for every possible implementation, and one of them sat in a test that
    solved circuits twice. That is exactly the "a guard that cannot fail" defect
    this milestone's own gates were written to avoid, reproduced in its tests.

    It is now installed over ``pd.native_circuit_solver``, which is the default
    argument's *binding site* for every published entry point, so a refusal test
    that reached a circuit would fail. It is used only in tests where no circuit
    should ever be built, and `_SolverSpy` does NOT cover this: it counts seven
    solver factories and the circuit solver is not one of them.
    """
    calls: list[str] = []

    def solver(circuit, *, run_id, **_ignored):
        calls.append(run_id)
        raise AssertionError("a circuit must never be solved for a refused input")

    # Patched at the DC package boundary the seam ultimately calls, not at the
    # seam itself: `native_circuit_solver` is bound as a DEFAULT ARGUMENT of
    # `run_propulsion_drive` and `_executors`, so rebinding the module name
    # would leave both defaults pointing at the original — an inert spy with a
    # convincing docstring, which is the very defect being repaired.
    monkeypatch.setattr(pd, "solve_circuit", solver)
    solver.calls = calls
    return solver


def _algebraic_point(*, k_load, b, loop_ohm=FIXED_LOOP_OHM, volts=REFERENCE_VOLTS,
                     k=REFERENCE_K, index=0):
    """One operating point through the PUBLISHED solver, at a fixed loop R.

    No caller arithmetic evaluates the balance: the closed form is the pack's,
    reached through ``bind_drive`` / ``prepare`` / ``solve``.
    """
    constants = rot.MachineConstants(
        torque_constant=Q(k, rot.TORQUE_CONSTANT_UNIT),
        back_emf_constant=Q(k, rot.BACK_EMF_CONSTANT_UNIT),
        source="fixture; representative small brushed DC machine",
    )
    load = rot.RotationalLoad(
        load_id="Lsweep",
        load_coefficient=Q(k_load, rot.LOAD_COEFFICIENT_UNIT),
        viscous_coefficient=Q(b, rot.VISCOUS_COEFFICIENT_UNIT),
        source="fixture sweep load law",
    )
    problem_id = f"drive_operating_point:sweep-{index}"
    solver = pmod.DriveOperatingPointSolver()
    problem = pmod.build_operating_point_problem(
        problem_id, supply_voltage=Q(volts, "volt"), constants=constants, load=load
    )
    solver.bind_drive(
        problem_id,
        supply_voltage=Q(volts, "volt"),
        constants=constants,
        load=load,
        loop_resistance=Q(loop_ohm, cmat.RESISTANCE_UNIT),
    )
    raw = solver.solve(solver.prepare(problem))
    values = dict(raw.values)
    values["source_power"] = volts * values[pmod.CURRENT_METRIC]
    values["efficiency"] = (
        values[pmod.MECHANICAL_OUTPUT_POWER_METRIC] / values["source_power"]
    )
    return values


def _log_grid(low, high, count):
    step = (high / low) ** (1.0 / (count - 1))
    return tuple(low * step ** i for i in range(count))


#: The three turning points and the ceiling, in the closed forms the
#: preregistration derived (§2.3, §2.4). Written as functions of the DECLARED
#: constants, so nothing here is a frozen number.
def _w_noload(volts=REFERENCE_VOLTS, k_e=REFERENCE_K):
    return volts / k_e


def _w_pmech(volts=REFERENCE_VOLTS, k=REFERENCE_K, b=REFERENCE_B,
             loop_ohm=FIXED_LOOP_OHM):
    return k * volts / (2.0 * (b * loop_ohm + k * k))


def _w_converted(volts=REFERENCE_VOLTS, k_e=REFERENCE_K):
    return volts / (2.0 * k_e)


def _w_efficiency(volts=REFERENCE_VOLTS, k=REFERENCE_K, b=REFERENCE_B,
                  loop_ohm=FIXED_LOOP_OHM):
    a = b * loop_ohm + k * k
    return (volts / k) * (1.0 - (1.0 - k * k / a) ** 0.5)


def _strictly(values, increasing):
    pairs = list(zip(values, values[1:]))
    if increasing:
        return [(x, y) for x, y in pairs if not y > x]
    return [(x, y) for x, y in pairs if not y < x]


def _run(drive, *, seed=SEED, tolerance=Q(1e-9, KELVIN), max_iterations=60,
         run_id="ext"):
    *_, plan = pd.compose(
        drive, seed=seed, tolerance=tolerance, max_iterations=max_iterations
    )
    return pd.run_propulsion_drive(drive, plan, run_id=run_id)


def _temperatures(run, drive):
    return {
        element.component_id: run.coupled.final_values[
            (element.conductor.resistivity_problem_id, cmat.TEMPERATURE)
        ].magnitude_in(KELVIN)
        for element in drive.conducting_elements
    }


def _operating(run, drive):
    result = run.coupled.final.result_for(drive.motor.operating_point_problem_id)
    return {
        metric: result.value(metric)
        for metric in (
            pmod.ANGULAR_VELOCITY_METRIC, pmod.CURRENT_METRIC,
            pmod.BACK_EMF_METRIC, pmod.ELECTROMAGNETIC_TORQUE_METRIC,
            pmod.LOAD_TORQUE_METRIC, pmod.INTERNAL_LOSS_TORQUE_METRIC,
            pmod.MECHANICAL_OUTPUT_POWER_METRIC,
            pmod.INTERNAL_LOSS_POWER_METRIC, pmod.CONVERTED_POWER_METRIC,
        )
    }


@pytest.fixture(scope="module")
def kload_sweep():
    """Five converged runs. The only expensive fixture in this module."""
    points = []
    for index, k_load in enumerate(KLOAD_SWEEP):
        drive = build_drive(load=mechanical_load(k_load=k_load, b=REFERENCE_B))
        run = _run(drive, run_id=f"kload-{index}")
        points.append((k_load, drive, run))
    return tuple(points)


@pytest.fixture(scope="module")
def b_sweep():
    points = []
    for index, b in enumerate(B_SWEEP):
        drive = build_drive(load=mechanical_load(k_load=REFERENCE_K_LOAD, b=b))
        run = _run(drive, run_id=f"b-{index}")
        points.append((b, drive, run))
    return tuple(points)


# =====================================================================
# G1 — multiple operating points
# =====================================================================

#: Preregistration §2.2. The nine relations the governing equations guarantee
#: UNCONDITIONALLY in `k_load` at fixed loop resistance, and nothing else.
#: `(metric, increasing)`.
KLOAD_GUARANTEED = (
    (pmod.ANGULAR_VELOCITY_METRIC, False),
    (pmod.BACK_EMF_METRIC, False),
    (pmod.CURRENT_METRIC, True),
    (pmod.ELECTROMAGNETIC_TORQUE_METRIC, True),
    (pmod.INTERNAL_LOSS_TORQUE_METRIC, False),
    (pmod.INTERNAL_LOSS_POWER_METRIC, False),
    (pmod.LOAD_TORQUE_METRIC, True),
    ("source_power", True),
)

#: Preregistration §2.8. In `b` the SAME implicit-function argument gives
#: `dw/db < 0`, so the speed-driven half is identical — but the load torque and
#: the mechanical output REVERSE, because `k_load` is now fixed, and the two
#: viscous terms become ambiguous and are therefore absent from this table.
B_GUARANTEED = (
    (pmod.ANGULAR_VELOCITY_METRIC, False),
    (pmod.BACK_EMF_METRIC, False),
    (pmod.CURRENT_METRIC, True),
    (pmod.ELECTROMAGNETIC_TORQUE_METRIC, True),
    (pmod.LOAD_TORQUE_METRIC, False),
    (pmod.MECHANICAL_OUTPUT_POWER_METRIC, False),
    ("source_power", True),
    # Deviation D-1: the preregistration called this one ambiguous in `b`. It
    # is not — see `test_g1_the_viscous_pair_in_b_and_the_deviation_...`.
    (pmod.INTERNAL_LOSS_TORQUE_METRIC, True),
)


@pytest.fixture(scope="module")
def dense_kload():
    grid = _log_grid(1.0e-8, 1.0e-5, 241)
    return grid, tuple(
        _algebraic_point(k_load=k, b=REFERENCE_B, index=i)
        for i, k in enumerate(grid)
    )


@pytest.fixture(scope="module")
def dense_b():
    grid = _log_grid(1.0e-6, 1.0e-3, 241)
    return grid, tuple(
        _algebraic_point(k_load=REFERENCE_K_LOAD, b=b, index=i)
        for i, b in enumerate(grid)
    )


@pytest.mark.parametrize("metric, increasing", KLOAD_GUARANTEED)
def test_g1_every_derived_kload_relation_holds_at_all_240_consecutive_pairs(
    dense_kload, metric, increasing
):
    """§2.2, over three decades — a relation, not three fixtures.

    241 log-spaced points spanning `1e-8 .. 1e-5`, every consecutive pair
    checked. A fixture triple can be right by accident; 240 strict inequalities
    derived from one implicit-function-theorem argument cannot.

    **What this does NOT establish, stated so the count is not inflated.** At
    fixed `R` five of the eight series are strictly monotone transforms of the
    speed or of the current, and `source_power` is literally `V*I` computed in
    the harness. The independent propositions here are two: `dw/dk_load < 0`,
    and `tau_load` increasing. The coupled versions of the same eight ARE
    independent of each other, because `R` moves with `k_load` there and the
    fixed-`R` theorem no longer applies — that is the load-bearing difference,
    and it is why both are asserted separately.
    """
    _, points = dense_kload
    series = [p[metric] for p in points]
    assert len(series) == 241
    assert _strictly(series, increasing) == [], (metric, increasing)


@pytest.mark.parametrize("metric, increasing", B_GUARANTEED)
def test_g1_the_b_family_reverses_exactly_the_two_relations_predicted(
    dense_b, metric, increasing
):
    """§2.8 — the asymmetry that proves the derivation is load-bearing.

    `load_torque` and `mechanical_output_power` are strictly INCREASING in
    `k_load` and strictly DECREASING in `b`, and the two viscous terms are
    strictly decreasing in `k_load` and ambiguous in `b`. No fixture triple has
    a reason to behave that way; the governing equations do.
    """
    _, points = dense_b
    series = [p[metric] for p in points]
    assert _strictly(series, increasing) == [], (metric, increasing)


def test_g1_the_viscous_pair_in_b_and_the_deviation_the_measurement_forced():
    """One of the two abstentions was right; the other was an under-claim.

    **Deviation D-1, recorded rather than left standing.** Preregistration §2.8
    called both `tau_loss = b*w` and `P_int = b*w^2` ambiguous in `b`. Carrying
    the differentiation through the balance instead of stopping at "a rising
    factor times a falling one" gives

        d(tau_loss)/db = w * (1 - b/(2*k_load*w + b + k_t*k_e/R))
        d(P_int)/db    = w^2 * (1 - 2b/(2*k_load*w + b + k_t*k_e/R))

    The first bracket is **strictly positive for every positive `b`**, because
    its denominator exceeds its numerator by `2*k_load*w + k_t*k_e/R > 0`. So
    `tau_loss` is unconditionally increasing in `b` and the preregistration
    under-claimed. The second vanishes at `b = 2*k_load*w + k_t*k_e/R`, so
    `P_int` really does turn and that abstention was necessary.

    Both halves are asserted here, and the turning point is compared to its
    closed form rather than merely observed.
    """
    grid = _log_grid(1.0e-6, 1.0e-1, 241)
    points = [
        _algebraic_point(k_load=REFERENCE_K_LOAD, b=b, index=i)
        for i, b in enumerate(grid)
    ]
    speeds = [p[pmod.ANGULAR_VELOCITY_METRIC] for p in points]

    # D-1: unconditionally increasing, over five decades of `b`.
    torque = [p[pmod.INTERNAL_LOSS_TORQUE_METRIC] for p in points]
    assert _strictly(torque, True) == []

    # ...and the power really does turn, where the derivation says.
    internal = [p[pmod.INTERNAL_LOSS_POWER_METRIC] for p in points]
    assert _strictly(internal, True) != []
    assert _strictly(internal, False) != []
    peak = max(range(len(internal)), key=lambda i: internal[i])
    assert 0 < peak < len(internal) - 1
    predicted = (
        2.0 * REFERENCE_K_LOAD * speeds[peak]
        + REFERENCE_K * REFERENCE_K / FIXED_LOOP_OHM
    )
    assert grid[peak - 1] <= predicted <= grid[peak + 1]


def test_g1_the_three_conditional_turning_points_are_where_the_closed_form_says(
    dense_kload
):
    """§2.3 — each turning point located, and compared to its derivation.

    `P_mech`, `P_conv` and `eta` are each non-monotone in `k_load`, and the
    preregistration derived where each turns. The grid's argmax is compared to
    that closed form: agreement within one grid spacing is the acceptance
    criterion, and the closed forms are evaluated from the DECLARED constants
    here, never from a stored number.
    """
    grid, points = dense_kload
    ratio = (grid[-1] / grid[0]) ** (1.0 / (len(grid) - 1))
    speeds = [p[pmod.ANGULAR_VELOCITY_METRIC] for p in points]

    for metric, predicted in (
        (pmod.MECHANICAL_OUTPUT_POWER_METRIC, _w_pmech()),
        (pmod.CONVERTED_POWER_METRIC, _w_converted()),
        ("efficiency", _w_efficiency()),
    ):
        series = [p[metric] for p in points]
        peak = max(range(len(series)), key=lambda i: series[i])
        # interior, so it really is a turning point and not an endpoint
        assert 0 < peak < len(series) - 1, metric
        # ...and the speed at the peak is the derived one, to a grid step.
        neighbours = (speeds[peak - 1], speeds[peak + 1])
        assert min(neighbours) <= predicted <= max(neighbours), (
            metric, speeds[peak], predicted
        )
        # ...and it really does turn: strictly up before, strictly down after.
        assert _strictly(series[: peak + 1], True) == [], metric
        assert _strictly(series[peak:], False) == [], metric
    assert ratio > 1.0


def test_g1_a_lossless_shaft_has_no_interior_efficiency_maximum():
    """The degenerate consistency check the derivation predicts.

    With `b = 0` the efficiency turning point `w_eta` collapses onto the no-load
    speed, which is unattainable — so efficiency must be strictly monotone over
    the whole grid instead of turning. Derived in §2.3 before any run.
    """
    assert _w_efficiency(b=0.0) == pytest.approx(_w_noload(), rel=1e-12)
    grid = _log_grid(1.0e-8, 1.0e-5, 121)
    series = [
        _algebraic_point(k_load=k, b=0.0, index=i)["efficiency"]
        for i, k in enumerate(grid)
    ]
    assert _strictly(series, False) == []


def test_g1_the_speed_ceiling_is_the_exact_supremum_over_loop_resistance():
    """§2.4 — `V/k_e` is the least upper bound, not a conservative bound."""
    ceiling = _w_noload()
    speeds = [
        _algebraic_point(
            k_load=REFERENCE_K_LOAD, b=REFERENCE_B, loop_ohm=ohm, index=i
        )[pmod.ANGULAR_VELOCITY_METRIC]
        for i, ohm in enumerate((1.0, 1.0e-1, 1.0e-3, 1.0e-5, 1.0e-7))
    ]
    assert all(speed < ceiling for speed in speeds)
    assert _strictly(speeds, True) == []          # approached from below
    assert speeds[-1] == pytest.approx(ceiling, rel=1e-6)   # and attained in the limit
    assert pd.no_load_speed(build_drive()).magnitude_in(RAD_S) == pytest.approx(
        ceiling, rel=1e-12
    )


def test_g1_every_coupled_sweep_point_satisfies_its_own_governing_equations(
    kload_sweep
):
    """No point is a fixture: each is re-derived from the record that produced it.

    The speed balance, the back-EMF law, the loop KVL, the torque production
    law, the load law, the viscous law and both power definitions are
    recomputed at each converged point from the *transported* loop resistance
    and the declared constants, and must reproduce the reported numbers.
    """
    for k_load, drive, run in kload_sweep:
        assert run.converged
        values = _operating(run, drive)
        loop = run.coupled.final.result_for(
            drive.series_join_ids[1]
        ).value(pmod.SERIES_RESISTANCE_METRIC).magnitude_in(cmat.RESISTANCE_UNIT)
        w = values[pmod.ANGULAR_VELOCITY_METRIC].magnitude_in(RAD_S)
        current = values[pmod.CURRENT_METRIC].magnitude_in("ampere")
        emf = values[pmod.BACK_EMF_METRIC].magnitude_in("volt")
        k_t = drive.motor.constants.k_t_si
        k_e = drive.motor.constants.k_e_si
        b = drive.load.b_si

        assert emf == pytest.approx(k_e * w, rel=1e-12)
        assert current == pytest.approx((REFERENCE_VOLTS - emf) / loop, rel=1e-12)
        assert values[pmod.ELECTROMAGNETIC_TORQUE_METRIC].magnitude_in(NM) == (
            pytest.approx(k_t * current, rel=1e-12)
        )
        assert values[pmod.LOAD_TORQUE_METRIC].magnitude_in(NM) == pytest.approx(
            k_load * w * w, rel=1e-12
        )
        assert values[pmod.INTERNAL_LOSS_TORQUE_METRIC].magnitude_in(NM) == (
            pytest.approx(b * w, rel=1e-12)
        )
        # the balance itself, residual against the driving term
        assert k_load * w * w + b * w == pytest.approx(k_t * current, rel=1e-11)
        assert values[pmod.MECHANICAL_OUTPUT_POWER_METRIC].magnitude_in("watt") == (
            pytest.approx(k_load * w ** 3, rel=1e-12)
        )
        assert values[pmod.INTERNAL_LOSS_POWER_METRIC].magnitude_in("watt") == (
            pytest.approx(b * w * w, rel=1e-12)
        )


@pytest.mark.parametrize("metric, increasing", KLOAD_GUARANTEED)
def test_g1_the_coupled_sweep_preserves_every_unconditional_relation(
    kload_sweep, metric, increasing
):
    """§2.5's second reason: the derivation holds `R` fixed; coupling does not.

    A reversal here would be a real discovery about the thermal feedback rather
    than an arithmetic slip, and it is asserted separately for exactly that
    reason.
    """
    series = []
    for _k, drive, run in kload_sweep:
        values = _operating(run, drive)
        if metric in values:
            series.append(values[metric].magnitude)
        else:
            series.append(run.accounting.source_power.magnitude_in("watt"))
    assert _strictly(series, increasing) == [], (metric, series)


def test_g1_energy_closes_at_every_point_of_both_coupled_sweeps(kload_sweep, b_sweep):
    """§2.7(5) — the declared 1e-9 relative, at every operating point."""
    residuals = []
    for _x, drive, run in kload_sweep + b_sweep:
        assert run.accounting is not None
        residual = run.accounting.relative_balance_residual
        residuals.append(residual)
        assert residual <= pd.ENERGY_RELATIVE_TOLERANCE, (drive.drive_id, residual)
    # and the closure is at machine precision, not merely inside the budget
    assert max(residuals) < 1e-13


def test_g1_efficiency_is_not_monotone_across_the_coupled_sweep(kload_sweep):
    """§2.7(4) — the preregistered prediction, and where the maximum falls.

    Predicted BEFORE the sweep: `eta` rises then falls, with its maximum at the
    third of the five points, because `w_eta` (from the declared constants at
    the reference loop resistance) lies between the third and fourth speeds.
    """
    etas = [
        pd.drive_efficiency(run.accounting).magnitude for _k, _d, run in kload_sweep
    ]
    speeds = [
        _operating(run, drive)[pmod.ANGULAR_VELOCITY_METRIC].magnitude_in(RAD_S)
        for _k, drive, run in kload_sweep
    ]
    peak = max(range(len(etas)), key=lambda i: etas[i])
    assert peak == 2, etas
    assert _strictly(etas[: peak + 1], True) == []
    assert _strictly(etas[peak:], False) == []
    # ...and the turning point brackets the predicted speed, at the SHARPER
    # bracket §2.7(4) actually preregistered — between this point and the next,
    # not the two-spacing window discrete unimodality already forces.
    predicted = _w_efficiency()
    assert speeds[peak + 1] < predicted < speeds[peak]
    assert speeds[peak + 1] < predicted < speeds[peak - 1]
    assert 0.0 < min(etas) and max(etas) < 1.0


def test_g1_the_thermal_state_is_coherent_at_every_coupled_point(kload_sweep, b_sweep):
    """Coherence stated as relations, not as a temperature band.

    Four claims at every point: each body sits strictly between ambient and its
    own steady-state rise `Q/hA` (finite duration, so neither end is attained);
    the machine is hotter than either lead; every converged resistance is
    exactly `rho(T)*L/A` at that body's own temperature; and every material
    reports `IN_DOMAIN` at the state the loop converged to.
    """
    for _x, drive, run in kload_sweep + b_sweep:
        temperatures = _temperatures(run, drive)
        electrical = run.coupled.final.result_for(drive.electrical_problem_id)
        heat = run.coupled.final.result_for(
            drive.motor.heat_generation_problem_id
        ).value(pmod.TOTAL_DISSIPATION).magnitude_in("watt")
        ambient = drive.motor.thermal.ambient_temperature.magnitude_in(KELVIN)

        for element in drive.conducting_elements:
            body_heat = heat if element is drive.motor else electrical.value(
                drive.power_metric(element.component_id)
            ).magnitude_in("watt")
            conductance = element.thermal.ambient_conductance.magnitude_in(
                lump.CONDUCTANCE_UNIT
            )
            final = temperatures[element.component_id]
            assert ambient < final < ambient + body_heat / conductance
            resistivity = run.coupled.final.result_for(
                element.conductor.resistivity_problem_id
            ).value(cmat.RESISTIVITY_METRIC).magnitude_in(cmat.RESISTIVITY_UNIT)
            resistance = run.coupled.final.result_for(
                element.conductor.resistance_problem_id
            ).value(cmat.RESISTANCE_METRIC).magnitude_in(cmat.RESISTANCE_UNIT)
            length = element.conductor.length.magnitude_in("meter")
            area = element.conductor.cross_sectional_area.magnitude_in("meter ** 2")
            assert resistance == pytest.approx(resistivity * length / area, rel=1e-12)

        assert temperatures[drive.motor.component_id] > max(
            temperatures[drive.feed.component_id],
            temperatures[drive.ret.component_id],
        )
        assessments = pd.assess_run_applicability(drive, run.coupled)
        assert {a.status for a in assessments.values()} == {ValidityStatus.IN_DOMAIN}


def test_g1_the_machine_heat_is_the_declared_two_channel_sum_at_every_point(
    kload_sweep
):
    """The channel that makes `T_motor` non-monotone, measured rather than assumed.

    The preregistration refused to predict a direction for the machine's body
    because its heat is a rising copper channel plus a falling mechanical one.
    Here both channels are read at every point and the falling one is shown to
    fall while the total rises — which is the fact that made the abstention
    correct, not cautious.
    """
    copper, mechanical, totals = [], [], []
    for _k, drive, run in kload_sweep:
        result = run.coupled.final.result_for(drive.motor.heat_generation_problem_id)
        electrical = run.coupled.final.result_for(drive.electrical_problem_id).value(
            drive.power_metric(drive.motor.component_id)
        ).magnitude_in("watt")
        internal = run.accounting.internal_mechanical_loss.magnitude_in("watt")
        total = result.value(pmod.TOTAL_DISSIPATION).magnitude_in("watt")
        assert total == pytest.approx(electrical + internal, rel=1e-12)
        copper.append(electrical)
        mechanical.append(internal)
        totals.append(total)
    assert _strictly(copper, True) == []
    assert _strictly(mechanical, False) == []
    # the two channels are the same size at the reference point, which is why
    # no direction was preregistered for the sum
    assert 0.5 < copper[2] / mechanical[2] < 2.0


def test_g1_the_sweep_moved_only_the_load_declaration(kload_sweep):
    """Nothing else was varied: the whole sweep is one coefficient."""
    payloads = {
        json.dumps(
            {k: v for k, v in drive.to_dict().items() if k != "load"}, sort_keys=True
        )
        for _k, drive, _run in kload_sweep
    }
    assert len(payloads) == 1
    coefficients = {
        drive.load.k_load_si for _k, drive, _run in kload_sweep
    }
    assert len(coefficients) == len(KLOAD_SWEEP)
    assert {drive.load.b_si for _k, drive, _run in kload_sweep} == {REFERENCE_B}


# =====================================================================
# G2 — two motors
# =====================================================================

def _named_drive(tag, *, volts, k_load, b, winding_length, k, area=3.0e-7):
    """A whole drive under one naming prefix. Same TYPE, different parameters."""
    return pd.PropulsionDrive(
        drive_id=f"D{tag}",
        source_voltage=Q(volts, "volt"),
        feed=wire(f"{tag}_feed"),
        motor=machine(f"{tag}_M", length=winding_length, area=area, k_t=k, k_e=k),
        ret=wire(f"{tag}_ret"),
        load=rot.RotationalLoad(
            load_id=f"L{tag}",
            load_coefficient=Q(k_load, rot.LOAD_COEFFICIENT_UNIT),
            viscous_coefficient=Q(b, rot.VISCOUS_COEFFICIENT_UNIT),
            source="fixture load law for the second-machine composition",
        ),
    )


def _motor_a():
    return _named_drive("A", volts=24.0, k_load=REFERENCE_K_LOAD, b=REFERENCE_B,
                        winding_length=6.25, k=REFERENCE_K)


def _motor_b(k_load=5.0e-7):
    return _named_drive("B", volts=36.0, k_load=k_load, b=3.0e-5,
                        winding_length=8.0, k=0.04)


def _union(first, second, *, tolerance=Q(1e-9, KELVIN), max_iterations=80,
           run_id="two-machines"):
    """ONE composition holding two machines.

    Both halves come from the pack's published ``compose``; only the executor
    table is reached for privately, and that omission is itself a finding —
    see ``test_g2_composing_two_drives_has_no_public_entry_point``.
    """
    left = pd.compose(first, seed=SEED, max_iterations=max_iterations)
    right = pd.compose(second, seed=SEED, max_iterations=max_iterations)
    problems = tuple(left[2]) + tuple(right[2])
    plan = FixedPointCouplingPlan(
        plan_id=f"{first.drive_id}-{second.drive_id}",
        dependencies=tuple(left[3]) + tuple(right[3]),
        torn=tuple(left[4].torn) + tuple(right[4].torn),
        absolute_tolerance=tolerance,
        max_iterations=max_iterations,
    )
    executors = dict(pd._executors(first, left[0], left[2]))
    executors.update(pd._executors(second, right[0], right[2]))
    return plan, run_fixed_point(
        problems, executors, plan, run_id=run_id,
        software_version="tests.test_propulsion0_ext/two-machines",
    )


def _speed(run, drive):
    return run.final.result_for(
        drive.motor.operating_point_problem_id
    ).value(pmod.ANGULAR_VELOCITY_METRIC).magnitude_in(RAD_S)


@pytest.fixture(scope="module")
def two_machines():
    a, b = _motor_a(), _motor_b()
    plan, run = _union(a, b)
    return a, b, plan, run


def test_g2_two_machines_of_the_same_type_pose_disjoint_problems():
    """P1 — distinct component ids, therefore disjoint identity."""
    a, b = _motor_a(), _motor_b()
    assert type(a.motor) is type(b.motor) is pd.Motor
    assert a.motor.constants != b.motor.constants
    ids_a = pd.declared_problem_ids(a)
    ids_b = pd.declared_problem_ids(b)
    assert len(ids_a) == len(ids_b) == 14
    assert ids_a.isdisjoint(ids_b)
    # ...and every one of the eight machine identities is distinct too.
    assert set(a.motor.physical_identities()).isdisjoint(
        set(b.motor.physical_identities())
    )
    assert len(set(a.motor.physical_identities())) == 8


def test_g2_two_machines_converge_inside_one_composition(two_machines):
    """P1 — 28 problems, one plan, one `run_fixed_point`, six torn endpoints.

    This is the N = 2 question the eight-identity result was never asked. It is
    answered by the **unedited** `FixedPointCouplingPlan` and `run_fixed_point`:
    neither was touched, and the composition is block-diagonal only because the
    two drives share no identity, not because anything enforces separation.
    """
    a, b, plan, run = two_machines
    assert run.outcome is CouplingOutcome.CRITERION_MET
    assert len(plan.torn) == 6
    assert len({endpoint.endpoint for endpoint in plan.torn}) == 6
    assert len(plan.dependencies) == 40
    assert _speed(run, a) > 0.0 and _speed(run, b) > 0.0
    assert _speed(run, a) != _speed(run, b)


def test_g2_each_machine_in_the_union_equals_its_standalone_answer(two_machines):
    """P2 — and any residual is convergence depth, not interaction.

    The union's stopping criterion is the largest change over **six** torn
    endpoints rather than three, so a drive whose own block settles early keeps
    being swept while the other block catches up. That, and nothing else, is
    what separates the union answer from the stand-alone one: tightening the
    tolerance makes the gap shrink to the float noise floor, which is not how an
    interaction behaves.
    """
    a, b, _plan, run = two_machines
    gaps = {}
    for tolerance in (1e-9, 1e-11):
        _plan2, union = _union(
            a, b, tolerance=Q(tolerance, KELVIN), run_id=f"union-{tolerance:g}"
        )
        assert union.outcome is CouplingOutcome.CRITERION_MET
        for drive in (a, b):
            solo = _run(drive, tolerance=Q(tolerance, KELVIN), run_id="solo")
            assert solo.converged
            union_speed = _speed(union, drive)
            solo_speed = _speed(solo.coupled, drive)
            gaps[(tolerance, drive.drive_id)] = (
                abs(union_speed - solo_speed) / solo_speed
            )
    for key, gap in gaps.items():
        assert gap <= 1e-12, key
    for drive_id in ("DA", "DB"):
        # deeper convergence closes the gap; an interaction would not care
        assert gaps[(1e-11, drive_id)] <= gaps[(1e-9, drive_id)]
        assert gaps[(1e-11, drive_id)] <= 1e-15
    # ...and the gap is never a physical difference: at every depth it is at or
    # below the float resolution of the speed itself, which an interaction
    # could not be. (The previous version froze `gaps[(1e-9, "DB")] == 0.0`,
    # an exact measurement in a module whose own docstring forbids them —
    # `architecture-falsifier` C-9.)
    for key, gap in gaps.items():
        assert gap * _speed(run, a) < 1e-9, key
    assert _speed(run, a) > 0.0


def test_g2_changing_one_machine_leaves_the_other_bit_identical(two_machines):
    """P3 — cross-contamination: NO, and the bar is bit-equality."""
    a, _b, _plan, run = two_machines
    changed = _motor_b(k_load=9.0e-7)
    plan, other = _union(a, changed, run_id="two-machines-changed")
    assert other.outcome is CouplingOutcome.CRITERION_MET
    # B moved a long way...
    assert _speed(other, changed) != pytest.approx(
        _speed(run, _motor_b()), rel=1e-3
    )
    # ...the iteration counts differ, so the loops really were shared...
    assert len(other.iterations) != len(run.iterations)
    # ...and A did not move by one bit.
    assert _speed(other, a) == _speed(run, a)
    for element in a.conducting_elements:
        endpoint = (element.conductor.resistivity_problem_id, cmat.TEMPERATURE)
        assert (
            other.final_values[endpoint].magnitude_in(KELVIN)
            == run.final_values[endpoint].magnitude_in(KELVIN)
        )


def test_g2_each_machine_keeps_its_own_energy_balance_in_the_union(two_machines):
    """Both machines reconcile, against the pack's own enforcement point."""
    a, b, _plan, run = two_machines
    for drive in (a, b):
        accounting = pd.reconcile_drive_energy(drive, run)
        assert accounting.relative_balance_residual < 1e-13
        efficiency = pd.drive_efficiency(accounting).magnitude
        assert 0.0 < efficiency < 1.0


def test_g2_provenance_separates_the_machines_only_through_problem_ids(two_machines):
    """P7 — measured, and the half that is NOT clean is stated.

    Every result names the problem it solved and every problem id is derived
    from a `component_id`, so attribution is unambiguous. But the two drives
    share **one** `run_id`, so run-level provenance does not distinguish them:
    provenance is clean *through problem identity only*.
    """
    a, b, _plan, run = two_machines
    ids_a, ids_b = pd.declared_problem_ids(a), pd.declared_problem_ids(b)
    solved = {result.problem_id for result in run.final.results}
    assert ids_a <= solved and ids_b <= solved
    assert len(solved) == len(ids_a) + len(ids_b)
    run_ids = {result.provenance.run_id for result in run.final.results}
    # ...and here is the half that is not clean: one run id over both machines.
    assert all("two-machines" in name for name in run_ids)
    a_result = run.final.result_for(a.motor.operating_point_problem_id)
    b_result = run.final.result_for(b.motor.operating_point_problem_id)
    assert a_result.provenance.run_id.replace(
        a.motor.operating_point_problem_id, ""
    ) == b_result.provenance.run_id.replace(
        b.motor.operating_point_problem_id, ""
    )


def test_g2_the_two_machines_share_declaration_objects_without_sharing_state():
    """Sharing an immutable declaration is not contamination — proved, not assumed."""
    a, b = _motor_a(), _motor_b()
    assert a.feed.material is b.feed.material is pmat.COPPER_THERMOPHYSICAL
    assert a.motor.conductor.material is b.motor.conductor.material is cmat.COPPER
    for record in (pmat.COPPER_THERMOPHYSICAL, cmat.COPPER):
        assert dataclasses.is_dataclass(record)
        assert record.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.motor.constants.torque_constant = Q(1.0, rot.TORQUE_CONSTANT_UNIT)


def test_g2_eleven_of_the_fourteen_problem_ids_carry_no_drive_id():
    """P5 — finding F-1, quantified exactly.

    Only the circuit and the two series joins are namespaced by `drive_id`. The
    other eleven are namespaced by `component_id` alone, which is why two drives
    are independent **only because the caller chose distinct component ids** —
    a naming discipline, not a structural guarantee.
    """
    left = build_drive(drive_id="DL")
    right = build_drive(drive_id="DR")
    ids_l, ids_r = pd.declared_problem_ids(left), pd.declared_problem_ids(right)
    assert len(ids_l) == 14
    shared = ids_l & ids_r
    assert len(shared) == 11
    carries_drive_id = ids_l - shared
    assert carries_drive_id == {
        left.electrical_problem_id, *left.series_join_ids
    }
    # `architecture-falsifier`'s correction to the denominator: three more ids
    # are derived and posed — the thermal-mass problems, which `compose` solves
    # before the loop starts and which `declared_problem_ids` does not list.
    # They carry no `drive_id` either, so the honest counts are 14 of 17
    # derived ids, and 11 of the 14 the plan is checked against.
    derived_l = ids_l | {
        e.thermal_mass_problem_id for e in left.conducting_elements
    }
    derived_r = ids_r | {
        e.thermal_mass_problem_id for e in right.conducting_elements
    }
    assert len(derived_l) == 17
    assert len(derived_l & derived_r) == 14


def test_g2_colliding_component_ids_are_refused_by_the_unedited_plan():
    """P4 — and it FALSIFIES the second half of finding F-1.

    F-1 recorded that "two `PropulsionDrive`s in one process sharing an element
    id collide, and `FixedPointCouplingPlan` would accept the union". The
    collision is real (previous test). The acceptance is **not**: the plan's
    own fan-in guard sees twelve endpoints receiving two dependencies and
    refuses. Nothing in `engcore.coupling` was edited to make that true.
    """
    left = build_drive(drive_id="DL")
    right = build_drive(drive_id="DR", load=mechanical_load(k_load=5.0e-7))
    ldeps = pd.compose(left, seed=SEED)
    rdeps = pd.compose(right, seed=SEED)
    with pytest.raises(InvalidScientificProblem, match="more than one") as excinfo:
        FixedPointCouplingPlan(
            plan_id="union",
            dependencies=tuple(ldeps[3]) + tuple(rdeps[3]),
            torn=tuple(ldeps[4].torn) + tuple(rdeps[4].torn),
            absolute_tolerance=Q(1e-9, KELVIN),
            max_iterations=50,
        )
    assert "12 endpoint(s)" in str(excinfo.value)


def test_g2_colliding_problem_ids_are_refused_by_the_unedited_run():
    """P4 — the second, independent refusal, one layer down.

    Even if a caller hand-built a plan that dodged the fan-in guard,
    `run_fixed_point`'s duplicate-problem-id guard refuses the union of the two
    problem lists. Two guards, neither this milestone's, neither edited.
    """
    left = build_drive(drive_id="DL")
    right = build_drive(drive_id="DR", load=mechanical_load(k_load=5.0e-7))
    lc = pd.compose(left, seed=SEED)
    rc = pd.compose(right, seed=SEED)
    executors = dict(pd._executors(left, lc[0], lc[2]))
    executors.update(pd._executors(right, rc[0], rc[2]))
    with pytest.raises(InvalidScientificProblem, match="duplicate problem id"):
        run_fixed_point(
            tuple(lc[2]) + tuple(rc[2]), executors, lc[4],
            run_id="collide", software_version="test",
        )


def test_g2_a_plan_is_accepted_by_a_composition_that_would_never_declare_it():
    """P6 **WITHDRAWN as unfalsifiable**, and replaced by what is measurable.

    Two adversarial rounds were needed to get this right, and both corrections
    are recorded rather than quietly absorbed.

    Round 1 swapped a plan carrying a looser tolerance and a distant seed and
    called the resulting error an identity failure. Round 2 observed that the
    replacement — a plan carrying a different transported quantity — had merely
    moved the lever from one ``compose`` keyword to another, and produced the
    decisive field analysis: a plan composed by :func:`compose` is a **pure
    function of** ``(drive_id, the component ids, seed, tolerance,
    max_iterations, temperature_metric)``. No load coefficient, no machine
    constant, no voltage, no geometry and no material enters it. So for two
    drives sharing a ``drive_id`` and component ids, the two plans are
    field-for-field equal, and "drive B's plan" **is** drive A's plan.

    **Measured here:** the plan composed from the other drive and the plan
    composed from this one compare equal, and running this drive with either
    produces a bit-identical result. P6 predicted that a plan composed for a
    different drive would return a different answer *because* it came from a
    different drive. No such instance exists. The prediction is withdrawn as
    **unfalsifiable in this composition**, not recorded as confirmed.

    **What is left after the withdrawal is real, and is not an N = 2 finding.**
    ``compose`` and ``run_propulsion_drive`` are two independent authorities
    over one composition, and ``_refuse_unresolved_edges`` checks only that the
    plan's problem ids are a *subset* of this drive's. A plan whose edges
    transport the body's steady-state temperature instead of its final one is
    therefore accepted by a drive that would never have declared it — the run
    reports ``converged = True``, reconciles to 2.6e-15, and converges **12 K**
    away. That bites at **N = 1**, with one drive and its own ids, and
    drive-scoped problem-id namespacing would not touch it.
    """
    own = build_drive(drive_id="DX")
    other = build_drive(drive_id="DX", load=mechanical_load(k_load=6.0e-7))
    assert pd.declared_problem_ids(own) == pd.declared_problem_ids(other)

    *_, own_plan = pd.compose(own, seed=SEED)
    kwargs = dict(seed=SEED, temperature_metric=lump.STEADY_STATE_TEMPERATURE_METRIC)
    *_, from_other = pd.compose(other, **kwargs)
    *_, from_own = pd.compose(own, **kwargs)

    # P6 withdrawn: the "foreign" plan IS this drive's plan.
    assert from_other == from_own
    assert from_other.plan_id == own_plan.plan_id

    truth = pd.run_propulsion_drive(own, own_plan, run_id="own")
    swapped = pd.run_propulsion_drive(own, from_other, run_id="foreign")
    self_authored = pd.run_propulsion_drive(own, from_own, run_id="self")

    # ...and the second drive is inert: the harm is identical without it.
    assert _temperatures(swapped, own) == _temperatures(self_authored, own)
    assert _speed(swapped.coupled, own) == _speed(self_authored.coupled, own)

    # What remains, and it is a real defect at N = 1.
    assert swapped.converged is True
    assert swapped.accounting.relative_balance_residual < 1e-13
    gap = abs(
        _temperatures(swapped, own)[own.motor.component_id]
        - _temperatures(truth, own)[own.motor.component_id]
    )
    assert gap > 10.0
    assert _speed(swapped.coupled, own) != pytest.approx(
        _speed(truth.coupled, own), rel=1e-4
    )
    # ...and the only thing that differs between the two plans is what the
    # declared edges transport, which is a scientific choice, not a control.
    assert own_plan.absolute_tolerance == from_own.absolute_tolerance
    assert own_plan.max_iterations == from_own.max_iterations
    assert {e.initial_value.magnitude for e in own_plan.torn} == {
        e.initial_value.magnitude for e in from_own.torn
    }
    assert {d.source_quantity for d in own_plan.dependencies} != {
        d.source_quantity for d in from_own.dependencies
    }


def test_g2_the_plan_carries_no_drive_physics_at_all():
    """The field analysis that made P6 unfalsifiable, asserted directly.

    Two drives differing in **every** physical declaration — voltage, machine
    constants, winding geometry, both load coefficients — compose to two plans
    that compare equal, provided their ids and ``compose`` options match. That
    is the finding: a `FixedPointCouplingPlan` under-identifies the composition
    it was built for, by construction and not by accident, and no assertion
    about two *drives* can be made from a plan swap.
    """
    left = build_drive(drive_id="DX", volts=24.0, motor=machine(k_t=0.0295,
                                                               k_e=0.0295),
                       load=mechanical_load(k_load=2.444e-7, b=2.0e-5))
    right = build_drive(drive_id="DX", volts=30.0,
                        motor=machine(k_t=0.04, k_e=0.04, length=8.0),
                        load=mechanical_load(k_load=6.0e-7, b=5.0e-5))
    assert left.to_dict() != right.to_dict()
    *_, left_plan = pd.compose(left, seed=SEED)
    *_, right_plan = pd.compose(right, seed=SEED)
    assert left_plan == right_plan
    # ...and the two drives really are physically different.
    assert _speed(_run(left, run_id="l").coupled, left) != pytest.approx(
        _speed(_run(right, run_id="r").coupled, right), rel=1e-3
    )


def test_g2_a_plan_naming_problems_this_drive_does_not_pose_is_refused():
    """The one binding that does exist, and exactly how far it reaches.

    `_refuse_unresolved_edges` refuses a plan whose problem ids are not a subset
    of this drive's — so distinct component ids do make the swap impossible.
    What it cannot see is a plan that names the right problems and transports
    the wrong quantity, which is the residue above.
    """
    other = build_drive(drive_id="DX", load=mechanical_load(k_load=6.0e-7))
    *_, foreign = pd.compose(
        other, seed=SEED, temperature_metric=lump.STEADY_STATE_TEMPERATURE_METRIC
    )
    renamed = pd.PropulsionDrive(
        drive_id="DX", source_voltage=Q(REFERENCE_VOLTS, "volt"),
        feed=wire("other_feed"), motor=machine("other_M"), ret=wire("other_ret"),
        load=mechanical_load(),
    )
    with pytest.raises(InvalidScientificProblem, match="does not pose"):
        pd.run_propulsion_drive(renamed, foreign, run_id="renamed")


def test_g2_a_single_drive_cannot_hold_two_machines(spy):
    """The fixed-slot limit PROPULSION0 recorded, re-measured at N = 2.

    A `PropulsionDrive` declares three concrete slots and `isinstance`-checks
    them, so "two motors in one drive" is not expressible and "two motors in one
    process" had to be answered at the composition level instead.
    """
    with pytest.raises(InvalidScientificProblem, match="must be a DriveWire"):
        build_drive(feed=machine("M2"))
    assert spy.calls == []
    assert len(build_drive().elements) == 3
    assert sum(isinstance(e, pd.Motor) for e in build_drive().elements) == 1


def test_g2_composing_two_drives_has_no_public_entry_point():
    """A measured cost, recorded rather than repaired.

    The pack publishes `compose` for one drive and nothing for two. Building the
    union needed the private `_executors`, so the N = 2 composition is
    expressible but not *published*. Not repaired here: one consumer.
    """
    assert "_executors" not in pd.__all__
    assert not any(name.startswith("_") for name in pd.__all__)
    assert not hasattr(pd, "compose_drives")
    assert not hasattr(pd, "run_propulsion_drives")


# =====================================================================
# G3 — the four negative cases PROPULSION0 did not cover
# =====================================================================
#
# Detection is not enforcement. Every case below must refuse BEFORE a solver
# object exists, and `spy.calls == []` is the proof: the spy wraps every solver
# factory the pack can reach, so an empty list means none was constructed, not
# merely that none produced a number.

def test_g3_a_missing_mechanical_load_is_refused_before_any_solver(spy, circuit_spy):
    """A drive with no load is refused at construction — nothing to execute."""
    with pytest.raises(InvalidScientificProblem, match="requires a RotationalLoad"):
        build_drive(load=object())
    with pytest.raises(TypeError):
        pd.PropulsionDrive(
            drive_id="D1", source_voltage=Q(24.0, "volt"),
            feed=wire("wire_a"), motor=machine(), ret=wire("wire_b"),
        )
    # ...and a load record that declares no load at all is refused one level
    # further out, by the load record itself.
    with pytest.raises(InvalidScientificProblem):
        mechanical_load(k_load=0.0)
    assert spy.calls == []
    assert circuit_spy.calls == []


@pytest.mark.parametrize(
    "speed",
    [
        REFERENCE_VOLTS / REFERENCE_K,              # exactly the supremum
        REFERENCE_VOLTS / REFERENCE_K + 1.0,
        2.0 * REFERENCE_VOLTS / REFERENCE_K,
    ],
)
def test_g3_an_unsupported_operating_point_is_refused_before_any_solver(
    spy, circuit_spy, speed
):
    """A demand with no real solution **for any positive loop resistance**.

    Refused from the declarations alone, so no problem is posed, no plan is
    built and no solver is constructed. The bound is the supremum, so the
    supremum itself is refused too: it is approached and never attained.
    """
    drive = build_drive()
    with pytest.raises(InvalidScientificProblem, match="cannot support"):
        pd.admit_speed_demand(drive, Q(speed, RAD_S))
    assert spy.calls == []
    assert circuit_spy.calls == []



def _ceiling_torque(drive):
    """The ceiling, obtained from the LOAD MODEL'S OWN EVALUATOR.

    Binds the published operating-point solver at a vanishing loop resistance —
    where the speed tends to the supremum `V/k_e` — and reads the `load_torque`
    the solver reports, which is `QUADRATIC_ROTATIONAL_LOAD_MODEL` evaluated by
    its own realization. Constructs a solver, so it is never called under the
    solver spy.
    """
    solver = pmod.DriveOperatingPointSolver()
    problem_id = "drive_operating_point:ceiling-probe"
    problem = pmod.build_operating_point_problem(
        problem_id, supply_voltage=drive.source_voltage,
        constants=drive.motor.constants, load=drive.load,
    )
    solver.bind_drive(
        problem_id, supply_voltage=drive.source_voltage,
        constants=drive.motor.constants, load=drive.load,
        loop_resistance=Q(1.0e-9, cmat.RESISTANCE_UNIT),
    )
    raw = solver.solve(solver.prepare(problem))
    return raw.values[pmod.LOAD_TORQUE_METRIC]


def _gate_torque_boundary(drive):
    """The smallest torque `admit_torque_demand` refuses — found by BISECTION.

    `architecture-falsifier` C-13 found the tests computing the demand with the
    same `k_load * speed**2` line the gate uses, so the guard shared the defect
    it would have to catch. This function treats the gate as a black box and
    shares no arithmetic with it at all: it brackets the boundary behaviourally
    and returns it. It constructs no solver, so it is safe under the spy.
    """
    low, high = 1.0e-9, 1.0e9
    assert not _refuses(pd.admit_torque_demand, drive, Q(low, NM))
    assert _refuses(pd.admit_torque_demand, drive, Q(high, NM))
    for _ in range(200):
        middle = 0.5 * (low + high)
        if middle <= low or middle >= high:
            break
        if _refuses(pd.admit_torque_demand, drive, Q(middle, NM)):
            high = middle
        else:
            low = middle
    return high


def test_g3_the_torque_ceiling_agrees_with_the_load_models_own_evaluator():
    """C-13's guard: the gate's restated law against the model's evaluator.

    `admit_torque_demand` restates `tau = k_load*w^2`, which the rotational
    domain owns and `DriveOperatingPointSolver` evaluates. The two authorities
    are compared here through code that shares no expression with either: the
    gate's boundary is found by bisecting the gate itself, and the model's is
    the `load_torque` the solver reports as the loop resistance vanishes. They
    must agree, and the day `RotationalLoad` gains a constant term they will
    not — which is the failure this guard exists to catch.
    """
    for drive in (build_drive(), build_drive(load=mechanical_load(k_load=6.0e-7)),
                  _motor_b()):
        boundary = _gate_torque_boundary(drive)
        assert _ceiling_torque(drive) == pytest.approx(boundary, rel=1e-6)
        assert _refuses(pd.admit_torque_demand, drive, Q(boundary, NM))
        assert not _refuses(
            pd.admit_torque_demand, drive, Q(boundary * (1.0 - 1e-9), NM)
        )


@pytest.mark.parametrize("factor", [1.0, 1.5, 10.0])
def test_g3_an_impossible_torque_demand_is_refused_before_any_solver(
    spy, circuit_spy, factor
):
    """A load torque the declared law cannot absorb below the speed ceiling."""
    drive = build_drive()
    # the boundary is found by bisecting the gate, never by restating the
    # expression the gate uses (`architecture-falsifier` C-13)
    boundary = _gate_torque_boundary(drive)
    with pytest.raises(InvalidScientificProblem, match="cannot meet"):
        pd.admit_torque_demand(drive, Q(boundary * factor, NM))
    assert spy.calls == []
    assert circuit_spy.calls == []


def test_g3_a_demanded_speed_or_torque_must_itself_be_positive(spy):
    """A non-positive demand is a malformed demand, not a satisfiable one."""
    drive = build_drive()
    for value in (0.0, -1.0):
        with pytest.raises(InvalidScientificProblem, match="strictly positive"):
            pd.admit_speed_demand(drive, Q(value, RAD_S))
        with pytest.raises(InvalidScientificProblem, match="strictly positive"):
            pd.admit_torque_demand(drive, Q(value, NM))
    # ...and a demand in the wrong dimension is refused by the units layer,
    # before this pack's own check ever sees a number.
    with pytest.raises(UnitCompatibilityError):
        pd.admit_speed_demand(drive, Q(100.0, NM))
    with pytest.raises(UnitCompatibilityError):
        pd.admit_torque_demand(drive, Q(100.0, RAD_S))
    assert spy.calls == []


def test_g3_the_two_demand_gates_are_one_ceiling_in_two_units(spy):
    """Stated in the preregistration and checked here rather than double-counted.

    The torque gate is the speed gate composed with the load law, so the two
    refuse exactly the same set of physical states. They are two refusals
    because a caller demanding a torque should be told about torque — not two
    pieces of evidence.

    **And this test contributes no independent evidence either.** Composing the
    ceiling with `(speed/ceiling)**2` reproduces the gate's own expression, so
    `speed_refused is torque_refused` cannot fail for any implementation that
    shares the duplication. It records the *relationship* between the two
    gates, which is the claim; the guard against that relationship drifting
    from the model is
    `test_g3_the_torque_ceiling_agrees_with_the_load_models_own_evaluator`,
    which shares arithmetic with neither.
    """
    drive = build_drive()
    ceiling = pd.no_load_speed(drive).magnitude_in(RAD_S)
    torque_ceiling = _gate_torque_boundary(drive)
    for speed in (0.5 * ceiling, 0.99 * ceiling, 1.01 * ceiling, 1.5 * ceiling):
        # the load law is the SUBJECT of this test — it is the map the two
        # gates are composed through — so stating it here is the claim, not a
        # hidden duplication. The guard against the gate's restatement drifting
        # from the model is the bisection cross-check above.
        torque = torque_ceiling * (speed / ceiling) ** 2
        speed_refused = _refuses(pd.admit_speed_demand, drive, Q(speed, RAD_S))
        torque_refused = _refuses(pd.admit_torque_demand, drive, Q(torque, NM))
        assert speed_refused is torque_refused, speed
    assert spy.calls == []


def _refuses(gate, drive, demand):
    try:
        gate(drive, demand)
    except InvalidScientificProblem:
        return True
    return False


def test_g3_the_demand_gates_are_tight_but_not_sufficient(spy):
    """The gate's declared limit, measured rather than asserted in prose.

    `V/k_e` is the exact supremum over loop resistance, so nothing weaker can be
    refused without knowing `R`. But a demand this admits may still exceed what
    the drive reaches at its own loop resistance — admission is not a promise,
    and here is a demand that is admitted and then missed by 16 %.
    """
    drive = build_drive()
    reached = _run(drive, run_id="reached")
    achieved = _operating(reached, drive)[pmod.LOAD_TORQUE_METRIC].magnitude_in(NM)
    boundary = _gate_torque_boundary(drive)
    demand = 0.5 * (achieved + boundary)
    assert achieved < demand < boundary
    pd.admit_torque_demand(drive, Q(demand, NM))       # admitted...
    assert achieved < demand                            # ...and not delivered
    # the gate is tight: it refuses everything at or above the supremum and
    # nothing below it, which is the strongest gate available without `R`, and
    # the supremum is the load model's own torque as the loop resistance
    # vanishes.
    assert _refuses(pd.admit_torque_demand, drive, Q(boundary, NM))
    assert _ceiling_torque(drive) == pytest.approx(boundary, rel=1e-6)


def test_g3_efficiency_outside_its_validity_range_is_refused_before_any_solver(
    spy, circuit_spy
):
    """The fourth negative case: a ratio taken over a state it is not valid over.

    `EnergyAccounting` is a published record, so a caller can build one without
    ever passing through `reconcile_drive_energy`. Several ways for such a
    record to sit outside the range this relation is **declared** over, each
    refused rather than returned.

    The stale claim that stood here — "the range `0 < eta < 1`, which the
    balance *derives* rather than declares" — is the one round 1 falsified, and
    round 2 found it still standing forty lines above the comment that corrects
    it. It is deleted rather than left to contradict its own test.
    """
    watt = "watt"

    def accounting(**overrides):
        fields = dict(
            source_power=Q(100.0, watt), feed_loss=Q(2.0, watt),
            return_loss=Q(2.0, watt), winding_loss=Q(6.0, watt),
            mechanical_output=Q(80.0, watt),
            internal_mechanical_loss=Q(10.0, watt),
            balance_residual=Q(0.0, watt),
            current_disagreement=Q(0.0, "dimensionless"),
            converted_power_disagreement=Q(0.0, "dimensionless"),
        )
        fields.update(overrides)
        return pd.EnergyAccounting(**fields)

    assert pd.drive_efficiency(accounting()).magnitude == pytest.approx(0.8)

    with pytest.raises(InvalidScientificProblem, match="non-positive input"):
        pd.drive_efficiency(accounting(source_power=Q(0.0, watt)))
    with pytest.raises(InvalidScientificProblem, match="negative loss channel"):
        pd.drive_efficiency(accounting(feed_loss=Q(-2.0, watt)))
    with pytest.raises(InvalidScientificProblem, match="does not close"):
        pd.drive_efficiency(accounting(mechanical_output=Q(50.0, watt)))
    # ...and the balance is recomputed from the six terms rather than read from
    # the record's own field, so a record that certifies itself is refused too.
    with pytest.raises(InvalidScientificProblem, match="does not close"):
        pd.drive_efficiency(
            accounting(mechanical_output=Q(50.0, watt),
                       balance_residual=Q(0.0, watt))
        )
    with pytest.raises(InvalidScientificProblem, match="misreports its own"):
        pd.drive_efficiency(accounting(balance_residual=Q(30.0, watt)))

    # The two boundaries, each with a CLOSING balance — so it is the range that
    # refuses them, not the reconciliation.
    #
    # `architecture-falsifier` C-12: these two records are exactly why the
    # DERIVED range is `0 <= eta <= 1` and not `0 < eta < 1`. Both satisfy every
    # premise — positive source, four non-negative losses, exact closure — so
    # neither is impossible, and the refusal message no longer says it is. The
    # strict endpoints are this composition's own declaration, justified by
    # `P_mech = k_load*w^3 > 0` for a strictly positive quadratic load.
    lossless = dict(
        feed_loss=Q(0.0, watt), return_loss=Q(0.0, watt),
        winding_loss=Q(0.0, watt), internal_mechanical_loss=Q(0.0, watt),
    )
    with pytest.raises(InvalidScientificProblem, match="outside the range"):
        pd.drive_efficiency(
            accounting(mechanical_output=Q(100.0, watt), **lossless)
        )
    with pytest.raises(InvalidScientificProblem, match="outside the range"):
        pd.drive_efficiency(
            accounting(mechanical_output=Q(0.0, watt),
                       winding_loss=Q(86.0, watt))
        )
    # ...and `architecture-falsifier` C-4: a NEGATIVE mechanical output also
    # satisfies every checked premise with an exact closure, so `eta >= 0` is
    # not derived from them either. It is caught by the declared endpoints, not
    # by the derivation, and the message now says so.
    with pytest.raises(InvalidScientificProblem, match="outside the range"):
        pd.drive_efficiency(
            accounting(mechanical_output=Q(-10.0, watt),
                       internal_mechanical_loss=Q(100.0, watt))
        )
    assert spy.calls == []
    assert circuit_spy.calls == []


def test_g3_efficiency_of_a_run_that_never_converged_is_refused():
    """`accounting is None` is a state, not a missing number.

    A run stopped at its iteration budget carries no accounting, precisely
    because reconciling a state the loop never reached would report the residual
    of an equation nothing claims to have solved. Asking it for an efficiency is
    refused for the same reason.
    """
    drive = build_drive()
    *_, plan = pd.compose(drive, seed=SEED, max_iterations=2)
    run = pd.run_propulsion_drive(drive, plan, run_id="budgeted")
    assert run.coupled.outcome is CouplingOutcome.ITERATION_LIMIT_REACHED
    assert run.accounting is None
    with pytest.raises(InvalidScientificProblem, match="did not converge"):
        pd.drive_efficiency(run.accounting)
    with pytest.raises(InvalidScientificProblem, match="expects an EnergyAccounting"):
        pd.drive_efficiency(run.coupled)

    # `architecture-falsifier` C-8, closed. The refusal used to live ONLY in
    # `run_propulsion_drive`, which sets `accounting = None`. But
    # `reconcile_drive_energy` is published and G2's own two-machine
    # composition calls `run_fixed_point` directly and never builds a
    # `DriveRun`, so the published pair reconstructed an efficiency for a
    # budget-exhausted run: measured at 0.80268 against a true 0.80225, with a
    # 1.4e-14 residual, because the balance closes at EVERY iterate. The gate
    # now sits on the function that produces the number.
    with pytest.raises(InvalidScientificProblem, match="rather than convergence"):
        pd.reconcile_drive_energy(drive, run.coupled)


def test_g3_the_new_gates_construct_no_problem_no_plan_and_no_circuit(spy, monkeypatch):
    """Structural: the refusals cannot reach an executor even by accident."""
    posed: list[str] = []
    for module, name in (
        (pmod, "build_operating_point_problem"),
        (pmod, "build_series_resistance_problem"),
        (cmat, "build_resistivity_problem"),
    ):
        original = getattr(module, name)

        def factory(*args, _n=name, _o=original, **kwargs):
            posed.append(_n)
            return _o(*args, **kwargs)

        monkeypatch.setattr(module, name, factory)

    drive = build_drive()
    for gate, demand in (
        (pd.admit_speed_demand, Q(5000.0, RAD_S)),
        (pd.admit_torque_demand, Q(500.0, NM)),
    ):
        with pytest.raises(InvalidScientificProblem):
            gate(drive, demand)
    pd.no_load_speed(drive)
    assert posed == []
    assert spy.calls == []


# =====================================================================
# G4 — what efficiency IS
# =====================================================================

def _model_definitions():
    """Every model record this pack and the rotational domain publish."""
    found = {}
    for module in (pmod, pmat, rot):
        for name in dir(module):
            value = getattr(module, name)
            if isinstance(value, ScientificModelDefinition):
                found[value.model_id] = value
    return found


def test_g4_efficiency_is_not_a_material_property(kload_sweep):
    """It moves while every material record stays byte-identical."""
    payloads = set()
    efficiencies = set()
    for _k, drive, run in kload_sweep:
        for element in drive.conducting_elements:
            payloads.add(json.dumps(element.material.to_dict(), sort_keys=True))
        efficiencies.add(pd.drive_efficiency(run.accounting).magnitude)
    assert len(payloads) == 1                       # ONE material declaration
    assert len(efficiencies) == len(KLOAD_SWEEP)    # five different efficiencies
    for record in (pmat.COPPER_THERMOPHYSICAL, cmat.COPPER):
        assert not any(
            "efficiency" in field.name for field in dataclasses.fields(record)
        )


def test_g4_efficiency_is_not_a_model_parameter():
    """No model names it as an input, a parameter or a validity condition."""
    models = _model_definitions()
    assert len(models) >= 9
    for model in models.values():
        names = (
            [spec.name for spec in model.inputs]
            + [condition.name for condition in model.validity.conditions]
        )
        assert not any("efficiency" in name for name in names), model.model_id


def test_g4_efficiency_is_not_a_solver_output(kload_sweep):
    """No solver computes it and no result in a converged run carries it."""
    for _k, _drive, run in kload_sweep:
        for result in run.coupled.final.results:
            assert not any("efficiency" in metric for metric in result.values)
    models = _model_definitions()
    for model in models.values():
        assert not any("efficiency" in out.metric for out in model.outputs)


def test_g4_efficiency_is_a_relation_over_terms_that_already_exist(kload_sweep):
    """It introduces no number: both operands are already reconciled terms.

    The relation is recomputed here from the run's own results — the circuit's
    source power and the machine's mechanical output, two different problems —
    and must equal what the function returns. If it were double-counting a term,
    this identity is where that would show.
    """
    for _k, drive, run in kload_sweep:
        accounting = run.accounting
        source = -run.coupled.final.result_for(drive.electrical_problem_id).value(
            pd.SOURCE_POWER_METRIC.format(component_id="V1")
        ).magnitude_in("watt")
        output = run.coupled.final.result_for(
            drive.motor.operating_point_problem_id
        ).value(pmod.MECHANICAL_OUTPUT_POWER_METRIC).magnitude_in("watt")
        relation = pd.drive_efficiency(accounting).magnitude
        assert relation == pytest.approx(output / source, rel=1e-15)
        assert accounting.source_power.magnitude_in("watt") == pytest.approx(
            source, rel=1e-15
        )
        # ...and it is a PURE relation: repeated calls agree, and calling it
        # changes nothing about the record it reads.
        before = dataclasses.asdict(accounting)
        assert pd.drive_efficiency(accounting).magnitude == relation
        assert dataclasses.asdict(accounting) == before
        assert pd.drive_efficiency(accounting).units == "dimensionless"


def test_g4_efficiency_added_no_field_no_schema_no_problem_and_no_edge():
    """The failure mode this milestone was told to avoid, made checkable."""
    drive = build_drive()
    payload = json.dumps(drive.to_dict(), sort_keys=True)
    assert "efficiency" not in payload
    assert not any(
        "efficiency" in field.name for field in dataclasses.fields(pd.EnergyAccounting)
    )
    assert not any("efficiency" in pid for pid in pd.declared_problem_ids(drive))
    _bodies, _masses, problems, dependencies, plan = pd.compose(drive, seed=SEED)
    assert not any("efficiency" in dep.name for dep in dependencies)
    assert not any(
        "efficiency" in (dep.source_quantity + dep.target_quantity)
        for dep in dependencies
    )
    assert len(problems) == 14
    assert len(plan.torn) == 3
    for token in (pd.DRIVE_SCHEMA, pd.CONDUCTING_ELEMENT_SCHEMA,
                  pd.THERMAL_DECLARATION_SCHEMA, pmat.THERMOPHYSICAL_CONDUCTOR_SCHEMA):
        assert "efficiency" not in token


def test_g4_the_composition_is_unchanged_by_the_relation_existing(kload_sweep):
    """Removing the relation would change no number the composition produces.

    Asserted by construction: the reference point's converged answer is the one
    PROPULSION0 recorded, to a loose band, and the number of problems, edges and
    tears is unchanged.
    """
    _k, drive, run = kload_sweep[2]
    speeds = _operating(run, drive)
    assert speeds[pmod.ANGULAR_VELOCITY_METRIC].magnitude_in(RAD_S) == (
        pytest.approx(726.0, rel=1e-2)
    )
    assert run.accounting.source_power.magnitude_in("watt") == pytest.approx(
        117.0, rel=1e-2
    )
    _bodies, _masses, problems, dependencies, _plan = pd.compose(drive, seed=SEED)
    assert (len(problems), len(dependencies)) == (14, 20)


# =====================================================================
# Gates — the fail conditions of preregistration §1, measured
# =====================================================================

#: This milestone's preregistration commit. Read the same way PROPULSION0's
#: gates read theirs — `--diff-filter=MD` so a LATER milestone that adds a file
#: does not fail a guard about THIS one's edits, plus a working-tree read so an
#: uncommitted edit to universal core is seen rather than merely absent from
#: HEAD. Both halves of that semantics are proved below.
_EXT_PREREG_COMMIT = "57164d8"

#: The five files PROPULSION0 added, and the only ones this milestone edits.
#: **No new file is created under `src/`** — see §7 of the preregistration:
#: `test_propulsion0.py::test_the_scope_gates_can_fail_and_do_not_fail_on_an_addition`
#: pins the file SET of those trees, and keeping that prediction true is why
#: every new function went into a file that already existed.
_PROPULSION_TREES = (
    "src/engcore/systems/propulsion/",
    "src/engcore/domains/mechanical_rotational.py",
)


def _ext_touched(tree: str) -> list[str]:
    committed = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=MD", _EXT_PREREG_COMMIT,
         "HEAD", "--", tree],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
    ).stdout.split()
    working = [
        line[3:].strip().strip('"')
        for line in subprocess.run(
            ["git", "status", "--porcelain", "--", tree],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip() and not line.startswith("??")
    ]
    return sorted(set(committed) | set(working))


def test_ext_gate_universal_core_and_the_coupling_package_are_byte_untouched():
    """Fail condition F1. Two motors, five operating points, four refusals — zero."""
    for tree in ("src/engcore/scientific/", "src/engcore/coupling/"):
        assert _ext_touched(tree) == [], tree


def test_ext_gate_no_pre_existing_domain_or_pack_was_modified():
    """Fail condition F2."""
    for tree in (
        "src/engcore/systems/electrothermal/",
        "src/engcore/systems/fluidthermal/",
        "src/engcore/domains/electrical/",
        "src/engcore/domains/thermal_lumped.py",
        "src/engcore/domains/thermal/",
        "src/engcore/application/",
        "src/crafty_http/",
        "src/crafty_mcp/",
    ):
        assert _ext_touched(tree) == [], tree


def test_ext_gate_no_source_file_was_added_and_only_two_were_edited():
    """Everything new lives in files PROPULSION0 already added.

    Scoped to this milestone's own trees, never to all of `src/` — the guard-rot
    `architecture-falsifier` caught in PROPULSION0's own meta-test.
    """
    def diff(args, tree):
        return subprocess.run(
            ["git", "diff", "--name-only", *args, _EXT_PREREG_COMMIT, "HEAD",
             "--", tree],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        ).stdout.split()

    added, edited = set(), set()
    for tree in _PROPULSION_TREES:
        added |= set(diff(["--diff-filter=A"], tree))
        edited |= set(diff(["--diff-filter=M"], tree))
    assert added == set()
    assert edited == {
        "src/engcore/systems/propulsion/drive.py",
        "src/engcore/systems/propulsion/__init__.py",
    }
    # ...and the filter really does distinguish the two, so neither half is
    # vacuous: this milestone modified a test file, and the MD filter sees it.
    assert "tests/test_composite_system0.py" in diff(["--diff-filter=MD"], "tests/")


def test_ext_gate_no_universal_contract_was_minted():
    """Fail condition F3, over the same five files plus this milestone's names."""
    forbidden = (
        "class PhysicalEntityReference", "class ComponentInstance", "class Port",
        "class Connector", "class SystemDefinition", "class MaterialIdentity",
        "class Material", "class MaterialProperty", "class MechanicalSystem",
        "class StateVector", "class FanInRule", "class CouplingScheme",
        "class DriveDemand", "class EfficiencyModel", "class OperatingPoint",
        "class Sweep", "class DriveRegistry", "class ComponentRegistry",
        "def run_fixed_point", "class FixedPointCouplingPlan",
        "class TornEndpoint", "class QuantityDependency",
        "class ScientificProblem", "class ScientificResult",
    )
    sources = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/engcore/domains/mechanical_rotational.py",
            "src/engcore/systems/propulsion/__init__.py",
            "src/engcore/systems/propulsion/materials.py",
            "src/engcore/systems/propulsion/models.py",
            "src/engcore/systems/propulsion/drive.py",
        )
    }
    for path, source in sources.items():
        for word in forbidden:
            assert word not in source, f"{path} defines {word!r}"
    # ...and no new schema token was minted either: PROPULSION0 declared six
    # across these five files, and there are still six.
    assert sum(
        source.count("schema_string(") for source in sources.values()
    ) == 6


def test_ext_gate_the_new_code_carries_no_product_specific_branching():
    """Fail condition F4, over the four functions this milestone added.

    No branch on a material, component or domain name; no manually assigned
    torque; no rpm factor. The whole-file scans in `test_propulsion0.py` already
    cover these files and now cover this code with them — this test names the
    new functions individually so the coverage is not merely incidental.
    """
    source = (REPO_ROOT / "src/engcore/systems/propulsion/drive.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    new_names = {
        "no_load_speed", "admit_speed_demand", "admit_torque_demand",
        "drive_efficiency",
        # ...and the function the adversarial rounds edited, which the first
        # version of this scan did not name (`architecture-falsifier` C-10).
        "reconcile_drive_energy",
    }
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in new_names:
            continue
        seen.add(node.name)
        for inner in ast.walk(node):
            if isinstance(inner, ast.Compare):
                operands = [inner.left, *inner.comparators]
                assert not [
                    o for o in operands
                    if isinstance(o, ast.Constant) and isinstance(o.value, str)
                ], node.name
            if isinstance(inner, ast.Constant) and isinstance(
                inner.value, (int, float)
            ) and not isinstance(inner.value, bool):
                assert inner.value not in {60, 60.0, 3.141592653589793,
                                           6.283185307179586, 9.549296585513721}
            assert not isinstance(inner, ast.Match), node.name
    assert seen == new_names
    # ...and no torque is ever assigned anywhere in the module: the only torque
    # this milestone names is a caller's DEMAND, which is refused or admitted
    # and never computed. Asserted over the AST rather than by substring, which
    # `architecture-falsifier` C-10 pointed out was defeated by `torque=` or by
    # any name ending in `torque`.
    assigned = {
        target.id
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    assert not any("torque" in name for name in assigned), sorted(assigned)


def test_ext_gate_the_shared_coupling_objects_are_still_used_by_identity():
    """Two machines in one composition, and still not a private copy."""
    import engcore.coupling as cpl

    assert pd.run_fixed_point is cpl.run_fixed_point
    assert pd.FixedPointCouplingPlan is cpl.FixedPointCouplingPlan
    assert run_fixed_point is cpl.run_fixed_point
    assert set(pd.__all__).isdisjoint(set(cpl.__all__))


def test_ext_gate_the_four_new_names_are_published_and_nothing_else_is():
    """The pack's public surface grew by exactly four names."""
    from engcore.systems import propulsion

    added = {
        "no_load_speed", "admit_speed_demand", "admit_torque_demand",
        "drive_efficiency",
    }
    assert added <= set(propulsion.__all__)
    assert added <= set(pd.__all__)
    assert set(propulsion.__all__) - added == {
        "ALUMINIUM_THERMOPHYSICAL", "CONDUCTOR_THERMAL_MASS_MODEL",
        "COPPER_THERMOPHYSICAL", "DRIVE_OPERATING_POINT_MODEL", "DriveElement",
        "DriveRun", "DriveWire", "EnergyAccounting", "MOTOR_HEAT_GENERATION_MODEL",
        "Motor", "PropulsionDrive", "SERIES_LOOP_RESISTANCE_MODEL",
        "ThermalDeclaration", "ThermophysicalConductor", "admit_drive",
        "assess_run_applicability", "build_drive_twin", "compose",
        "declared_problem_ids", "derive_thermal_masses", "drive_dependencies",
        "drive_plan", "drive_problems", "native_circuit_solver",
        "reconcile_drive_energy", "run_propulsion_drive",
    }


# =====================================================================
# G1 — the three preregistered predictions the first pass left unmeasured
# =====================================================================
#
# `architecture-falsifier` C-3 and C-4: §2.2 lists `P_wire = I^2*R_element` as
# one of the nine unconditional relations and §2.7(2)-(3) predict `P_mech` and
# `P_conv` increasing throughout the coupled sweep. None of the three was
# asserted anywhere. They are asserted here rather than quietly dropped, and
# the two conditional ones carry their conditions.

def test_g1_both_lead_losses_rise_across_the_coupled_sweep(kload_sweep):
    """§2.2's ninth relation, on the coupled path where it is not a theorem.

    At fixed `R` this is `I^2*R` with `I` rising. Under coupling `R` rises too,
    so it is doubly increasing — but `R`'s rise also depresses `I`, and the net
    sign is a fixed-point property rather than an algebraic one. Asserted for
    both leads and for the winding.
    """
    feed, ret, winding = [], [], []
    for _k, _drive, run in kload_sweep:
        feed.append(run.accounting.feed_loss.magnitude_in("watt"))
        ret.append(run.accounting.return_loss.magnitude_in("watt"))
        winding.append(run.accounting.winding_loss.magnitude_in("watt"))
    for series in (feed, ret, winding):
        assert _strictly(series, True) == []
    # the two leads are declared separately and are geometrically identical, so
    # they track each other to 1e-12 at every point. They are NOT bit-identical:
    # they occupy different node spans in the MNA system and their losses are
    # accumulated in different orders, which is float ordering, not aliasing —
    # asserted as agreement rather than claimed as equality.
    for left, right in zip(feed, ret):
        assert left == pytest.approx(right, rel=1e-12)
    assert feed != ret


def test_g1_the_two_conditional_relations_hold_where_their_conditions_hold(
    kload_sweep
):
    """§2.7(2) and §2.7(3), each with its condition evaluated at its own point.

    `P_mech` rises in `k_load` only while `w > w_P`, and `P_conv` only while
    `w > V/(2*k_e)`. Both thresholds are recomputed **per point** from that
    point's own converged loop resistance, so this is the conditional
    guarantee being checked, not a monotonicity being assumed.
    """
    mechanical, converted = [], []
    for _k, drive, run in kload_sweep:
        values = _operating(run, drive)
        speed = values[pmod.ANGULAR_VELOCITY_METRIC].magnitude_in(RAD_S)
        loop = run.coupled.final.result_for(
            drive.series_join_ids[1]
        ).value(pmod.SERIES_RESISTANCE_METRIC).magnitude_in(cmat.RESISTANCE_UNIT)
        assert speed > _w_pmech(loop_ohm=loop), (speed, loop)
        assert speed > _w_converted()
        mechanical.append(
            values[pmod.MECHANICAL_OUTPUT_POWER_METRIC].magnitude_in("watt")
        )
        converted.append(values[pmod.CONVERTED_POWER_METRIC].magnitude_in("watt"))
    assert _strictly(mechanical, True) == []
    assert _strictly(converted, True) == []


def test_g1_the_conditional_guarantees_are_not_vacuous():
    """...and the conditions really can fail, so they are conditions.

    The same two relations, evaluated on the algebraic sweep beyond their own
    thresholds: both reverse. A "conditional guarantee" whose condition never
    fails is an unconditional one wearing a hedge.
    """
    grid = _log_grid(1.0e-8, 1.0e-3, 241)
    points = [
        _algebraic_point(k_load=k, b=REFERENCE_B, index=i)
        for i, k in enumerate(grid)
    ]
    speeds = [p[pmod.ANGULAR_VELOCITY_METRIC] for p in points]
    for metric, threshold in (
        (pmod.MECHANICAL_OUTPUT_POWER_METRIC, _w_pmech()),
        (pmod.CONVERTED_POWER_METRIC, _w_converted()),
    ):
        series = [p[metric] for p in points]
        above = [v for v, w in zip(series, speeds) if w > threshold]
        below = [v for v, w in zip(series, speeds) if w <= threshold]
        assert len(above) > 10 and len(below) > 10, metric
        assert _strictly(above, True) == [], metric      # holds above
        assert _strictly(below, False) == [], metric     # reverses below


def test_the_circuit_spy_can_fail(circuit_spy):
    """The guard that proves the guard is live.

    `architecture-falsifier`'s second round found the first circuit spy inert —
    six assertions that no implementation could violate. A replacement that is
    merely *believed* live would be the same defect with a longer docstring, so
    it is demonstrated: under this fixture, a drive that really does reach the
    circuit fails.
    """
    drive = build_drive()
    *_, plan = pd.compose(drive, seed=SEED)
    with pytest.raises(AssertionError, match="must never be solved"):
        pd.run_propulsion_drive(drive, plan, run_id="live-spy")
    assert circuit_spy.calls != []
