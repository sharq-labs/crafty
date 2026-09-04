"""The two prerequisite domain-defect repairs of FT-SCALAR-COUPLING.

Both were diagnosed by ``docs/temporal-semantics-stress-evidence.md`` as
**domain defects, not contract residues** (§15.3 R-A and R-B), and both are
repaired here in the domain that owns them. Nothing universal changed: no new
core record, no temporal contract, no history record.

DEFECT A — ``kinetics/cstr`` misreported itself as not time dependent
---------------------------------------------------------------------
``ScientificProblem.is_time_dependent`` is ``bool(initial_conditions)``.
``build_cstr_problem`` declared none, and declared no ``STATE`` variable for
either evolving state, so a genuinely transient stiff integration over
``[0, 400 s]`` reported ``False``. The same omission left the horizon off the
record entirely: the only ``[time]``-dimensioned parameter was
``residence_time`` = 200 s, so a records-only reader taking "the [time]
parameter" for the horizon was wrong by exactly a factor of two.

DEFECT B — ``thermal_lumped`` declared its controls without their values
-----------------------------------------------------------------------
``heat_input`` and ``ambient_temperature`` are correctly declared ``CONTROL``
variables. A ``ScientificVariable`` carries no value, so nothing on the record
said *at what value* they were imposed: two runs of one body at 40 W and 4 W
serialized byte-identically while their results differed by 15.6 K.
"""

from __future__ import annotations

import json

import pytest

from engcore.domains import thermal_lumped as lump
from engcore.domains.kinetics import cstr
from engcore.domains.kinetics.cstr.problem import build_cstr_problem
from engcore.scientific.composition import unresolved_inputs
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.variables import VariableRole
from engcore.scientific.units.quantity import Quantity


# =====================================================================
# Shared declarations
# =====================================================================

def _run(*, end_time_s: float = 400.0) -> cstr.ReactorRun:
    """The domain's own reference operating point: horizon 400 s, tau 200 s."""
    chemistry = cstr.ReactorChemistry(
        k0=Quantity(7.2e10, "1/s"),
        activation_energy=Quantity(72750.0, "J/mol"),
        heat_of_reaction=Quantity(-50000.0, "J/mol"),
        density=Quantity(1000.0, "kg/m**3"),
        heat_capacity=Quantity(239.0, "J/(kg*K)"),
    )
    operation = cstr.ReactorOperation(
        volume=Quantity(0.1, "m**3"),
        flow_rate=Quantity(5.0e-4, "m**3/s"),
        feed_concentration=Quantity(1000.0, "mol/m**3"),
        feed_temperature=Quantity(350.0, "kelvin"),
        coolant_temperature=Quantity(300.0, "kelvin"),
        ua=Quantity(50000.0, "W/K"),
        end_time=Quantity(end_time_s, "second"),
    )
    return cstr.ReactorRun(
        run_label="defect-a",
        chemistry=chemistry,
        operation=operation,
        initial_concentration=Quantity(1000.0, "mol/m**3"),
        initial_temperature=Quantity(350.0, "kelvin"),
    )


def _body(*, ambient_k: float = 300.0) -> lump.ThermalBody:
    return lump.ThermalBody(
        body_id="defect-b",
        heat_capacity=Quantity(600.0, "joule/kelvin"),
        ambient_conductance=Quantity(2.0, "watt/kelvin"),
        ambient_temperature=Quantity(ambient_k, "kelvin"),
        initial_temperature=Quantity(300.0, "kelvin"),
        duration=Quantity(600.0, "second"),
    )


def _payload(problem) -> str:
    return json.dumps(problem.to_dict(), sort_keys=True)


# =====================================================================
# DEFECT A
# =====================================================================

def test_defect_a_the_transient_reactor_now_reports_itself_transient():
    """The exact reproducer, inverted: it used to report ``False``."""
    problem = build_cstr_problem(_run())
    assert problem.is_time_dependent is True
    assert {c.variable for c in problem.initial_conditions} == {
        cstr.CA_STATE,
        cstr.T_STATE,
    }


def test_defect_a_the_evolving_states_are_declared_state_variables():
    problem = build_cstr_problem(_run())
    roles = {v.name: v.role for v in problem.variables}
    assert roles[cstr.CA_STATE] is VariableRole.STATE
    assert roles[cstr.T_STATE] is VariableRole.STATE
    # The metrics stay OBSERVABLE, and their names stay distinct from the
    # states'. One name means one thing.
    assert roles[cstr.CA_FINAL_METRIC] is VariableRole.OBSERVABLE
    assert cstr.CA_STATE != cstr.CA_FINAL_METRIC
    assert cstr.T_STATE != cstr.T_FINAL_METRIC


def test_defect_a_the_declared_states_carry_the_runs_own_initial_values():
    run = _run()
    problem = build_cstr_problem(run)
    conditions = {c.variable: c for c in problem.initial_conditions}
    assert conditions[cstr.CA_STATE].value.compare(
        run.initial_concentration
    ) == 0.0
    assert conditions[cstr.T_STATE].value.compare(run.initial_temperature) == 0.0
    # Every condition states the instant it holds at, and it is t = 0.
    for condition in problem.initial_conditions:
        assert condition.time is not None
        assert condition.time.magnitude_in("second") == 0.0


def test_defect_a_the_horizon_is_on_the_record_and_is_not_the_residence_time():
    """The measured 2x error a records-only reader used to make."""
    run = _run()
    problem = build_cstr_problem(run)
    horizon = problem.parameter(cstr.END_TIME_PARAMETER).value
    residence = problem.parameter("residence_time").value
    assert horizon.magnitude_in("second") == 400.0
    assert residence.magnitude_in("second") == 200.0
    assert horizon.magnitude_in("second") == pytest.approx(
        2.0 * residence.magnitude_in("second")
    )
    # The residue this repair does NOT close, pinned rather than remembered:
    # the two are still indistinguishable BY DIMENSION. Only the enumerated
    # names separate them, and a universal contract that could separate them
    # is deliberately not introduced by this milestone.
    assert horizon.dimensionality == residence.dimensionality


def test_defect_a_two_horizons_no_longer_serialize_identically():
    short = _payload(build_cstr_problem(_run(end_time_s=200.0)))
    long = _payload(build_cstr_problem(_run(end_time_s=400.0)))
    assert short != long


def test_defect_a_a_record_that_contradicts_the_run_is_refused():
    run = _run()
    problem = build_cstr_problem(run)
    other = cstr.ReactorRun(
        run_label=run.run_label,
        chemistry=run.chemistry,
        operation=run.operation,
        initial_concentration=run.initial_concentration,
        initial_temperature=Quantity(360.0, "kelvin"),
    )
    with pytest.raises(cstr.ReactorConfigurationError):
        cstr.verify_problem_matches_run(problem, other)


def test_defect_a_the_repaired_record_still_solves_and_still_agrees():
    """The repair is a declaration repair: the science is untouched.

    Kept in FAST deliberately: one 0.2 s stiff solve, the same judgement
    ``tests/conftest.py`` records for the electrical DC solver tests — the
    coverage is worth having after every edit.
    """
    run = _run()
    result = cstr.solve_reactor(run, run_id="defect-a-check")
    assert result.is_usable
    # The result's problem carries the repaired declaration.
    problem = build_cstr_problem(run)
    cstr.verify_problem_matches_run(problem, run)
    assert problem.is_time_dependent is True


# =====================================================================
# DEFECT B
# =====================================================================

def test_defect_b_the_original_reproducer_two_heats_one_record():
    """40 W and 4 W: byte-identical records, 15.6 K apart. Now separable."""
    body = _body()
    hot = lump.build_lumped_thermal_problem(
        body, heat_input=Quantity(40.0, "watt"), problem_id="p"
    )
    cold = lump.build_lumped_thermal_problem(
        body, heat_input=Quantity(4.0, "watt"), problem_id="p"
    )
    assert _payload(hot) != _payload(cold)

    finals = []
    for problem, watts in ((hot, 40.0), (cold, 4.0)):
        solver = lump.LumpedThermalSolver()
        solver.bind_body(body, problem.problem_id, heat_input=Quantity(watts, "watt"))
        raw = solver.solve(solver.prepare(problem))
        finals.append(raw.values[lump.TEMPERATURE_METRIC])
    assert finals[0] - finals[1] == pytest.approx(15.5640, abs=1e-3)


def test_defect_b_the_ambient_control_value_is_now_on_the_record():
    warm = lump.build_lumped_thermal_problem(_body(ambient_k=320.0), problem_id="p")
    cool = lump.build_lumped_thermal_problem(_body(ambient_k=300.0), problem_id="p")
    assert _payload(warm) != _payload(cool)
    conditions = {c.variable: c for c in warm.initial_conditions}
    assert conditions[lump.AMBIENT_TEMPERATURE].value.magnitude_in("kelvin") == 320.0


def test_defect_b_recording_a_control_value_does_not_make_it_resolved():
    """The role declaration is the point and it is preserved.

    ``unresolved_inputs`` reports a ``CONTROL`` variable regardless of any
    condition on it, so a composition still sees both controls as inputs
    needing a supplier. The repair added an operating point, not a claim of
    closure.
    """
    body = _body()
    problem = lump.build_lumped_thermal_problem(
        body, heat_input=Quantity(40.0, "watt"), problem_id="p"
    )
    names = {q for (_, q, _) in unresolved_inputs([problem])}
    assert lump.HEAT_INPUT in names
    assert lump.AMBIENT_TEMPERATURE in names
    roles = {v.name: v.role for v in problem.variables}
    assert roles[lump.HEAT_INPUT] is VariableRole.CONTROL
    assert roles[lump.AMBIENT_TEMPERATURE] is VariableRole.CONTROL


def test_defect_b_a_record_stating_one_heat_may_not_be_solved_at_another():
    body = _body()
    problem = lump.build_lumped_thermal_problem(
        body, heat_input=Quantity(40.0, "watt"), problem_id="p"
    )
    solver = lump.LumpedThermalSolver()
    solver.bind_body(body, "p", heat_input=Quantity(4.0, "watt"))
    with pytest.raises(InvalidScientificProblem, match="imposed heat input"):
        solver.prepare(problem)


def test_defect_b_an_omitted_heat_input_stays_omitted_and_stays_solvable():
    """The composed case: the value arrives across a declared dependency.

    A record that stated a value the coupling loop overrides on every sweep
    would be worse than one that states none, so omission remains a real
    answer and is not refused.
    """
    body = _body()
    problem = lump.build_lumped_thermal_problem(body, problem_id="p")
    assert lump.HEAT_INPUT not in {c.variable for c in problem.initial_conditions}
    solver = lump.LumpedThermalSolver()
    solver.bind_body(body, "p", heat_input=Quantity(7.0, "watt"))
    raw = solver.solve(solver.prepare(problem))
    assert raw.succeeded


def test_defect_b_an_ambient_that_contradicts_the_body_is_refused():
    problem = lump.build_lumped_thermal_problem(_body(ambient_k=300.0), problem_id="p")
    with pytest.raises(InvalidScientificProblem, match="ambient"):
        lump.LumpedThermalSolver.verify_problem_matches_body(
            problem, _body(ambient_k=320.0)
        )


def test_defect_b_no_universal_record_changed():
    """Both repairs are domain-side. The schema string does not move."""
    problem = lump.build_lumped_thermal_problem(_body(), problem_id="p")
    assert problem.to_dict()["schema"] == "scientific_problem/2"
    assert build_cstr_problem(_run()).to_dict()["schema"] == "scientific_problem/2"
