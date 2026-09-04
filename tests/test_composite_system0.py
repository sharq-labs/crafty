"""COMPOSITE-SYSTEM0 — evidence-gated composite engineering system foundation.

Preregistration: ``docs/evidence/composite-system0-preregistration.md``
(commit ``dab4e1e``), written and committed **alone**, before any source file
on this branch was added or edited. Test identifiers below are the
preregistration's, §7.

Every predicted number asserted here was computed analytically, from the
equations of the preregistration's §8, in a throwaway script importing nothing
from ``engcore``. The assertions are against those preregistered values.

What this module is evidence *for*, stated so it is not overread: one consumer,
one author, one branch. Copper, aluminium, silver and an inline material are
variants of ONE consumer, not materially different architecture consumers. The
power chain is not the second materially different consumer the `ET-VERTICAL`
promotion criterion requires, and nothing here promotes anything.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

from src.engcore import coupling as cpl
from src.engcore.application import catalog, service
from src.engcore.domains import thermal_lumped as lump
from src.engcore.domains.electrical import conductor_material as cmat
from src.engcore.domains.electrical import material as legacy_mat
from src.engcore.domains.electrical.dc import ElectricalDCSolver
from src.engcore.scientific.composition import QuantityDependency
from src.engcore.scientific.errors import (
    InvalidScientificProblem,
    ScientificCoreError,
    UnitCompatibilityError,
)
from src.engcore.scientific.ir.values import CategoricalValue
from src.engcore.scientific.ir.variables import VariableRole
from src.engcore.scientific.models.definition import (
    InputSourceKind,
    ValidityStatus,
)
from src.engcore.scientific.realizations.registry import RealizationRegistry
from src.engcore.scientific.results.provenance import ProvenanceRecord
from src.engcore.scientific.solvers.protocol import ConvergenceState
from src.engcore.scientific.units.quantity import Quantity
from src.engcore.systems.electrothermal import coupled as legacy_coupled
from src.engcore.systems.electrothermal import power_chain as pc

import api_v0_case as api_case

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

KELVIN = "kelvin"
TOL = Quantity(1e-6, KELVIN)
SEED = Quantity(300.0, KELVIN)


# =====================================================================
# Declarations — one geometry, one load, one environment, one policy.
# Only the material ever differs between case A and case B.
# =====================================================================

LENGTH = Quantity(2.0, "meter")
AREA = Quantity(2.5e-6, "meter ** 2")
LOAD = Quantity(0.5, "ohm")
VOLTS = Quantity(12.0, "volt")


def body(cid, *, conductance=0.20, ambient=300.0, initial=300.0, duration=600.0):
    return lump.ThermalBody(
        body_id=cid,
        heat_capacity=Quantity(8.0, "joule/kelvin"),
        ambient_conductance=Quantity(conductance, "watt/kelvin"),
        ambient_temperature=Quantity(ambient, KELVIN),
        initial_temperature=Quantity(initial, KELVIN),
        duration=Quantity(duration, "second"),
    )


def wire(cid, material, *, length=LENGTH, area=AREA, **body_kwargs):
    return pc.WireSegment(
        conductor=cmat.MaterialConductor(cid, material, length, area),
        body=body(cid, **body_kwargs),
    )


def chain(material_a, material_b, *, volts=VOLTS, load=LOAD, chain_id="powerchain",
          **body_kwargs):
    """Source -> wire_A -> load -> wire_B -> gnd."""
    return pc.PowerChain(
        chain_id=chain_id,
        source_voltage=volts,
        elements=(
            wire("wire_A", material_a, **body_kwargs),
            pc.FixedLoad("load", load),
            wire("wire_B", material_b, **body_kwargs),
        ),
    )


def execute(target, *, seed=SEED, tolerance=TOL, budget=50, run_id="chain",
            metric=lump.TEMPERATURE_METRIC):
    problems, dependencies, plan = pc.compose(
        target, seed=seed, temperature_metric=metric,
        tolerance=tolerance, max_iterations=budget,
    )
    return pc.run_power_chain(target, plan, run_id=run_id), problems, plan


def resistivity_of(run, cid):
    return run.final.result_for(f"conductor_resistivity:{cid}").value("resistivity")


def resistance_of(run, cid):
    return run.final.result_for(f"conductor_resistance:{cid}").value("resistance")


def input_temperature_of(run, cid):
    """The temperature the last resistivity solve actually used.

    Read from that solve's own provenance, because the Gauss-Seidel order is
    resistivity -> resistance -> electrical -> thermal: within one sweep the
    resistivity is evaluated at the *previous* sweep's temperature, and the
    thermal result at the end of the same sweep is the next one. At
    convergence the two agree to the coupling tolerance, and asserting the
    property law against the value the solve was given is the exact statement.
    """
    return run.final.result_for(
        f"conductor_resistivity:{cid}"
    ).provenance.inputs[cmat.TEMPERATURE]


def temperature_of(run, cid):
    return run.final.result_for(
        lump.build_lumped_thermal_problem(body(cid)).problem_id
    ).value(lump.TEMPERATURE_METRIC)


def electrical(run, target):
    return run.final.result_for(target.electrical_problem_id)


@pytest.fixture(scope="module")
def case_a():
    target = chain(cmat.COPPER, cmat.COPPER)
    run, problems, plan = execute(target, run_id="caseA")
    return target, run, problems, plan


@pytest.fixture(scope="module")
def case_b():
    target = chain(cmat.ALUMINIUM, cmat.ALUMINIUM)
    run, problems, plan = execute(target, run_id="caseB")
    return target, run, problems, plan


@pytest.fixture(scope="module")
def case_d():
    """Only wire_A's material differs from CASE A. Everything else identical."""
    target = chain(cmat.ALUMINIUM, cmat.COPPER)
    run, problems, plan = execute(target, run_id="caseD")
    return target, run, problems, plan


# =====================================================================
# A — copper nominal
# =====================================================================

def test_a1_the_chain_is_seven_problems_eight_edges_and_two_tears(case_a):
    target, run, problems, plan = case_a
    assert len(problems) == 7
    assert [p.problem_id for p in problems] == [
        "electrical_dc:powerchain-wire_A-load-wire_B",
        "conductor_resistivity:wire_A",
        "conductor_resistance:wire_A",
        "thermal-lumped-wire_A",
        "conductor_resistivity:wire_B",
        "conductor_resistance:wire_B",
        "thermal-lumped-wire_B",
    ]
    assert len(plan.dependencies) == 8
    assert len(plan.torn) == 2
    assert plan.check_against(problems) == ()


def test_a2_copper_nominal_matches_the_preregistered_numbers(case_a):
    target, run, _, _ = case_a
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert resistance_of(run, "wire_A").magnitude_in("ohm") == pytest.approx(
        0.0159237236, rel=1e-8
    )
    assert temperature_of(run, "wire_A").magnitude_in(KELVIN) == pytest.approx(
        340.5324482, rel=1e-8
    )
    result = electrical(run, target)
    assert abs(result.value("source_current:V1").magnitude_in("ampere")) == (
        pytest.approx(22.56286095, rel=1e-8)
    )
    assert result.value("resistor_power:wire_A").magnitude_in("watt") == (
        pytest.approx(8.106492115, rel=1e-7)
    )
    assert result.value("resistor_power:load").magnitude_in("watt") == (
        pytest.approx(254.5413472, rel=1e-7)
    )


def test_a3_the_execution_order_is_computed_from_the_records(case_a):
    """The pack writes no order down; the graph readers derive it."""
    target, _, problems, plan = case_a
    order = cpl.execution_order([p.problem_id for p in problems], plan.uncut)
    assert order.index("conductor_resistivity:wire_A") < order.index(
        "conductor_resistance:wire_A"
    )
    assert order.index("conductor_resistance:wire_A") < order.index(
        target.electrical_problem_id
    )
    assert order.index(target.electrical_problem_id) < order.index(
        "thermal-lumped-wire_A"
    )


def test_a4_the_declared_cycle_is_a_four_cycle_per_wire(case_a):
    target, _, problems, plan = case_a
    cycles = cpl.cycle_edges(
        [p.problem_id for p in problems], plan.dependencies
    )
    assert len(cycles) == 8, "two 4-cycles sharing the electrical node"


def test_a5_the_twin_declares_the_material_and_the_geometry(case_a):
    target, _, _, _ = case_a
    twin = pc.build_chain_twin(target)
    names = {d.name for d in twin.declarations}
    assert {"length:wire_A", "cross_sectional_area:wire_A",
            "reference_resistivity:wire_A", "resistance:load"} <= names
    assert cmat.COPPER.source in " ".join(
        d.description for d in twin.declarations
    )


# =====================================================================
# B — aluminium nominal, and the required differential
# =====================================================================

def test_b1_aluminium_nominal_matches_the_preregistered_numbers(case_b):
    target, run, _, _ = case_b
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert resistance_of(run, "wire_A").magnitude_in("ohm") == pytest.approx(
        0.02770387106, rel=1e-8
    )
    assert temperature_of(run, "wire_A").magnitude_in(KELVIN) == pytest.approx(
        364.6619745, rel=1e-8
    )


def test_b2_the_two_cases_differ_in_the_material_and_in_nothing_else(
    case_a, case_b
):
    """The differential is only meaningful if everything else is identical."""
    a, b = case_a[0], case_b[0]
    assert a.source_voltage == b.source_voltage
    assert a.component_ids == b.component_ids
    assert a.loads == b.loads
    for wa, wb in zip(a.wires, b.wires):
        assert wa.body == wb.body
        assert wa.conductor.length == wb.conductor.length
        assert wa.conductor.cross_sectional_area == wb.conductor.cross_sectional_area
        assert wa.material != wb.material
    assert case_a[3].absolute_tolerance == case_b[3].absolute_tolerance
    assert case_a[3].max_iterations == case_b[3].max_iterations
    assert {e.initial_value for e in case_a[3].torn} == {
        e.initial_value for e in case_b[3].torn
    }


def test_b3_changing_only_the_material_moves_at_least_four_quantities(
    case_a, case_b
):
    """Preregistered §8: six quantities, and every direction stated in advance."""
    ta, ra, _, _ = case_a
    tb, rb, _, _ = case_b
    ea, eb = electrical(ra, ta), electrical(rb, tb)

    moved = {
        "wire_resistance": (
            resistance_of(ra, "wire_A").magnitude_in("ohm"),
            resistance_of(rb, "wire_A").magnitude_in("ohm"),
            "up",
        ),
        "circuit_current": (
            abs(ea.value("source_current:V1").magnitude_in("ampere")),
            abs(eb.value("source_current:V1").magnitude_in("ampere")),
            "down",
        ),
        "wire_voltage_drop": (
            abs(ea.value("resistor_voltage:wire_A").magnitude_in("volt")),
            abs(eb.value("resistor_voltage:wire_A").magnitude_in("volt")),
            "up",
        ),
        "wire_joule_loss": (
            ea.value("resistor_power:wire_A").magnitude_in("watt"),
            eb.value("resistor_power:wire_A").magnitude_in("watt"),
            "up",
        ),
        "wire_temperature": (
            temperature_of(ra, "wire_A").magnitude_in(KELVIN),
            temperature_of(rb, "wire_A").magnitude_in(KELVIN),
            "up",
        ),
        "delivered_load_power": (
            ea.value("resistor_power:load").magnitude_in("watt"),
            eb.value("resistor_power:load").magnitude_in("watt"),
            "down",
        ),
    }
    for name, (copper, aluminium, direction) in moved.items():
        assert copper != aluminium, f"{name} did not move"
        if direction == "up":
            assert aluminium > copper, f"{name} moved the wrong way"
        else:
            assert aluminium < copper, f"{name} moved the wrong way"
    assert len(moved) >= 4

    # The preregistered magnitudes, so a change of the right sign but the
    # wrong size cannot pass.
    assert moved["wire_resistance"][1] / moved["wire_resistance"][0] == (
        pytest.approx(1.73979, rel=1e-4)
    )
    assert moved["wire_temperature"][1] - moved["wire_temperature"][0] == (
        pytest.approx(24.1295, rel=1e-4)
    )


def test_b4_nothing_downstream_was_assigned_by_hand(case_b):
    """Every changed number is reachable through declared edges only.

    The chain of custody: the material's own declared quantities are the
    resistivity solve's provenance inputs; its result is what the declared
    resistivity edge transports; the resistance solve consumes exactly that;
    and the electrical problem's R parameter is what the resistance edge
    delivers. Nothing in the harness writes a downstream value.
    """
    target, run, problems, plan = case_b
    last = run.final
    edges = {d.name: d for d in plan.dependencies}

    rho = last.transported(edges["material-resistivity-sets-conductor-geometry-input:wire_A"])
    resistance = last.transported(edges["conductor-resistance-sets-circuit-element:wire_A"])
    conductor = target.wire("wire_A").conductor
    assert resistance.magnitude_in("ohm") == pytest.approx(
        rho.magnitude_in("ohm * meter") * conductor.length_m / conductor.area_m2,
        rel=1e-14,
    )
    # And the resistivity really is the material's own law at the temperature
    # that solve was given — not a number the harness chose.
    temperature = input_temperature_of(run, "wire_A")
    material = target.wire("wire_A").material
    expected = material.rho_ref_ohm_m * (
        1.0 + material.alpha_per_k
        * (temperature.magnitude_in(KELVIN) - material.t_ref_k)
    )
    assert rho.magnitude_in("ohm * meter") == pytest.approx(expected, rel=1e-14)
    # ...and that temperature is the converged one, to within the tolerance.
    assert abs(
        temperature.magnitude_in(KELVIN)
        - last.transported(
            edges["body-temperature-sets-material-state:wire_A"]
        ).magnitude_in(KELVIN)
    ) <= TOL.magnitude_in(KELVIN)


def test_b5_provenance_answers_why_the_value_changed(case_a, case_b):
    """material -> resistivity model -> R -> electrical -> Joule -> thermal."""
    for target, run in ((case_a[0], case_a[1]), (case_b[0], case_b[1])):
        last = run.final
        rho_result = last.result_for("conductor_resistivity:wire_A")
        binding = rho_result.provenance.bindings[0]
        assert binding.model.model_id == "electrical.material.linear_resistivity"
        assert binding.realization is not None
        assert binding.solver.solver_id == (
            "engcore.electrical.linear_resistivity_evaluator"
        )
        material = target.wire("wire_A").material
        # The scientific content of "which material" is in the record.
        assert rho_result.provenance.inputs["reference_resistivity"] == (
            material.reference_resistivity
        )
        assert rho_result.provenance.inputs["temperature_coefficient"] == (
            material.temperature_coefficient
        )
        r_result = last.result_for("conductor_resistance:wire_A")
        assert r_result.provenance.bindings[0].model.model_id == (
            "electrical.conductor.geometric_resistance"
        )
        assert r_result.provenance.inputs["length"] == LENGTH
        assert r_result.provenance.inputs["cross_sectional_area"] == AREA
        # ...and the run's own provenance carries every binding, so the whole
        # chain is one record.
        models = {b.model.model_id for b in run.provenance.bindings}
        assert {
            "electrical.material.linear_resistivity",
            "electrical.conductor.geometric_resistance",
            "thermal.lumped.first_order_capacity",
        } <= models


def test_b6_the_material_name_survives_on_the_problem_but_not_in_provenance(
    case_a,
):
    """A measured contract gap, recorded rather than routed around.

    ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]`` and refuses
    anything else, so a typed CATEGORICAL parameter — which is how material
    identity is declared — structurally cannot be recorded in provenance. The
    scientific content travels as quantities; the name does not. It is
    deliberately not smuggled through ``metadata``.
    """
    target, run, problems, _ = case_a
    problem = next(
        p for p in problems if p.problem_id == "conductor_resistivity:wire_A"
    )
    declared = problem.parameter("material").value
    assert isinstance(declared, CategoricalValue)
    assert declared.value == "copper"

    provenance = run.final.result_for(
        "conductor_resistivity:wire_A"
    ).provenance
    assert "material" not in provenance.inputs
    assert not provenance.metadata, "the name must not be smuggled through metadata"

    with pytest.raises(ScientificCoreError):
        ProvenanceRecord(
            run_id="probe", inputs={"material": CategoricalValue("copper")}
        )


# =====================================================================
# C — the thermal feedback genuinely closes
# =====================================================================

def _one_way(target, *, seed=SEED):
    """R at the seed temperature, one electrical solve, one thermal step. Stop.

    Deliberately the same participants and the same declared models — the only
    difference is that nothing is fed back.
    """
    resistances = pc.initial_resistances(target, seed_temperature=seed)
    circuit = target.circuit_at(resistances)
    result = pc.native_circuit_solver(circuit, "one-way")
    power = result.value("resistor_power:wire_A")
    solver = lump.LumpedThermalSolver()
    wire_segment = target.wire("wire_A")
    problem = lump.build_lumped_thermal_problem(wire_segment.body)
    solver.bind_body(wire_segment.body, problem.problem_id, heat_input=power)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    return resistances["wire_A"], power, metrics[lump.TEMPERATURE_METRIC]


def test_c1_the_converged_answer_is_not_the_one_way_answer(case_a):
    target, run, _, plan = case_a
    r_one_way, p_one_way, t_one_way = _one_way(target)

    assert r_one_way.magnitude_in("ohm") == pytest.approx(0.01378538079, rel=1e-8)
    assert t_one_way.magnitude_in(KELVIN) == pytest.approx(335.660686, rel=1e-7)
    assert p_one_way.magnitude_in("watt") == pytest.approx(7.132139384, rel=1e-7)

    delta_t = (
        temperature_of(run, "wire_A").magnitude_in(KELVIN)
        - t_one_way.magnitude_in(KELVIN)
    )
    assert delta_t == pytest.approx(4.87176, rel=1e-4)
    assert abs(delta_t) > plan.absolute_tolerance.magnitude_in(KELVIN) * 1e6, (
        "the converged answer must differ from the one-way answer by far more "
        "than the coupling tolerance, or the loop is spreadsheet arithmetic"
    )


def test_c2_the_iterate_sequence_contracts_monotonically(case_a):
    _, run, _, _ = case_a
    changes = [q.magnitude_in(KELVIN) for q in run.iterate_changes]
    assert run.iterations_run == 10
    assert changes[0] > changes[-1]
    assert all(b < a for a, b in zip(changes[1:], changes[2:])), (
        "after the seed transient the iterate change must contract"
    )
    assert changes[-1] <= TOL.magnitude_in(KELVIN)


def test_c3_a_temperature_perturbation_moves_the_answer_through_the_property(
):
    """Raise the ambient by 20 K and the whole chain moves — through rho(T)."""
    cool = chain(cmat.COPPER, cmat.COPPER, chain_id="cool")
    warm = chain(cmat.COPPER, cmat.COPPER, chain_id="warm",
                 ambient=320.0, initial=320.0)
    cool_run, _, _ = execute(cool, run_id="cool")
    warm_run, _, _ = execute(warm, seed=Quantity(320.0, KELVIN), run_id="warm")
    assert (
        temperature_of(warm_run, "wire_A").magnitude_in(KELVIN)
        > temperature_of(cool_run, "wire_A").magnitude_in(KELVIN)
    )
    assert (
        resistance_of(warm_run, "wire_A").magnitude_in("ohm")
        > resistance_of(cool_run, "wire_A").magnitude_in("ohm")
    )
    assert (
        abs(electrical(warm_run, warm).value(
            "source_current:V1").magnitude_in("ampere"))
        < abs(electrical(cool_run, cool).value(
            "source_current:V1").magnitude_in("ampere"))
    )


def test_c4_the_loop_is_not_time_marching(case_a):
    """Every iteration's thermal provenance records the same t0."""
    target, run, _, _ = case_a
    initial = target.wire("wire_A").body.initial_temperature
    for iteration in run.iterations:
        result = iteration.result_for("thermal-lumped-wire_A")
        assert result.provenance.inputs[lump.TEMPERATURE] == initial


# =====================================================================
# D — multiplicity, and no aliasing
# =====================================================================

def test_d1_two_identical_instances_agree_and_are_separately_identified(case_a):
    target, run, problems, _ = case_a
    a = resistance_of(run, "wire_A").magnitude_in("ohm")
    b = resistance_of(run, "wire_B").magnitude_in("ohm")
    assert a == pytest.approx(b, rel=1e-12)
    ids = [p.problem_id for p in problems]
    assert len(set(ids)) == len(ids)
    assert "conductor_resistivity:wire_A" in ids
    assert "conductor_resistivity:wire_B" in ids


def test_d2_changing_wire_a_does_not_touch_wire_b_s_declaration(case_a, case_d):
    """The instances are independent declarations, not one shared object."""
    base, changed = case_a[0], case_d[0]
    assert base.wire("wire_A").material != changed.wire("wire_A").material
    assert base.wire("wire_B") == changed.wire("wire_B")
    assert base.wire("wire_B").material is cmat.COPPER
    assert changed.wire("wire_B").material is cmat.COPPER
    assert (
        base.wire("wire_B").conductor.to_dict()
        == changed.wire("wire_B").conductor.to_dict()
    )
    assert base.loads == changed.loads


def test_d3_wire_b_still_evaluates_its_own_material_law(case_d):
    """The decisive no-aliasing assertion.

    wire_B's numbers legitimately move when wire_A's material changes — the
    two are in series and share a current, and a topology in which they could
    not influence each other would exercise nothing. What must hold is that
    wire_B's resistance is still *its own* material's law at *its own*
    temperature, which is what an aliased binding would break.
    """
    target, run, _, _ = case_d
    for cid, material in (("wire_A", cmat.ALUMINIUM), ("wire_B", cmat.COPPER)):
        temperature = input_temperature_of(run, cid).magnitude_in(KELVIN)
        expected_rho = material.rho_ref_ohm_m * (
            1.0 + material.alpha_per_k * (temperature - material.t_ref_k)
        )
        assert resistivity_of(run, cid).magnitude_in("ohm * meter") == (
            pytest.approx(expected_rho, rel=1e-14)
        )
        conductor = target.wire(cid).conductor
        assert resistance_of(run, cid).magnitude_in("ohm") == pytest.approx(
            expected_rho * conductor.length_m / conductor.area_m2, rel=1e-14
        )
    assert resistance_of(run, "wire_A") != resistance_of(run, "wire_B")
    assert temperature_of(run, "wire_A") != temperature_of(run, "wire_B")
    assert resistance_of(run, "wire_A").magnitude_in("ohm") == pytest.approx(
        0.02802845739, rel=1e-8
    )
    assert resistance_of(run, "wire_B").magnitude_in("ohm") == pytest.approx(
        0.01581666822, rel=1e-8
    )


def test_d4_each_instance_has_its_own_provenance(case_d):
    _, run, _, _ = case_d
    a = run.final.result_for("conductor_resistivity:wire_A").provenance
    b = run.final.result_for("conductor_resistivity:wire_B").provenance
    assert a.run_id != b.run_id
    assert a.inputs["reference_resistivity"] == cmat.ALUMINIUM.reference_resistivity
    assert b.inputs["reference_resistivity"] == cmat.COPPER.reference_resistivity
    assert "wire_A" in a.run_id and "wire_B" in b.run_id


def test_d5_two_instances_sharing_an_id_are_refused():
    with pytest.raises(InvalidScientificProblem, match="duplicate component id"):
        pc.PowerChain(
            chain_id="clash",
            source_voltage=VOLTS,
            elements=(wire("w", cmat.COPPER), wire("w", cmat.ALUMINIUM)),
        )


def test_d6_a_conductor_and_a_body_that_are_not_one_object_are_refused():
    conductor = cmat.MaterialConductor("wire_A", cmat.COPPER, LENGTH, AREA)
    with pytest.raises(InvalidScientificProblem, match="must share an id"):
        pc.WireSegment(conductor=conductor, body=body("wire_B"))


# =====================================================================
# E — admission: detection is not enforcement
# =====================================================================

class _Spy:
    """Counts every solve on every solver this milestone can reach."""

    TARGETS = (
        (cmat.LinearResistivitySolver, "solve"),
        (cmat.QuadraticResistivitySolver, "solve"),
        (cmat.GeometricResistanceSolver, "solve"),
        (lump.LumpedThermalSolver, "solve"),
        (ElectricalDCSolver, "solve"),
        (legacy_mat.ResistancePropertySolver, "solve"),
    )

    def __init__(self, monkeypatch):
        self.calls = []
        for cls, name in self.TARGETS:
            original = getattr(cls, name)

            def spied(inner_self, *args, _cls=cls, _original=original, **kwargs):
                self.calls.append(_cls.__name__)
                return _original(inner_self, *args, **kwargs)

            monkeypatch.setattr(cls, name, spied)


#: name -> (setup, action). ``setup`` prepares whatever the case needs and runs
#: BEFORE the spy is installed; ``action`` is the call that must be refused, and
#: it is the only thing the spy watches. Splitting them is deliberate: building
#: a valid composition legitimately executes the bootstrap solves, and folding
#: that into the measurement would make "no solver ran after the refusal" a
#: claim about setup rather than about enforcement.
NEGATIVE_CASES = {}


def _register(name, setup=None):
    def decorate(fn):
        NEGATIVE_CASES[name] = (setup or (lambda: None), fn)
        return fn
    return decorate


@_register("non_positive_area_zero")
def _zero_area(_):
    cmat.MaterialConductor("w", cmat.COPPER, LENGTH, Quantity(0.0, "meter ** 2"))


@_register("non_positive_area_negative")
def _negative_area(_):
    cmat.MaterialConductor("w", cmat.COPPER, LENGTH, Quantity(-2.5e-6, "meter ** 2"))


@_register("invalid_length_negative")
def _negative_length(_):
    """A negative length AND a negative area would give a positive resistance."""
    cmat.MaterialConductor(
        "w", cmat.COPPER, Quantity(-2.0, "meter"), Quantity(-2.5e-6, "meter ** 2")
    )


@_register("invalid_length_zero")
def _zero_length(_):
    cmat.MaterialConductor("w", cmat.COPPER, Quantity(0.0, "meter"), AREA)


@_register("unsupported_material_name")
def _unknown_material(_):
    cmat.resolve_material("unobtainium")


@_register("unit_mismatch_length")
def _unit_mismatch(_):
    cmat.MaterialConductor("w", cmat.COPPER, Quantity(2.0, KELVIN), AREA)


@_register("unit_mismatch_seed")
def _unit_mismatch_seed(_):
    pc.admit_power_chain(
        chain(cmat.COPPER, cmat.COPPER), seed_temperature=Quantity(300.0, "volt")
    )


@_register(
    "temperature_outside_applicability",
    setup=lambda: chain(cmat.COPPER, cmat.COPPER, chain_id="hot"),
)
def _outside_applicability(target):
    """Copper's declared range stops at 450 K; this run would start at 500 K."""
    pc.compose(target, seed=Quantity(500.0, KELVIN))


@_register(
    "unresolved_connection",
    setup=lambda: _broken_edge_setup(),
)
def _broken_edge(prepared):
    target, broken = prepared
    pc.run_power_chain(target, broken, run_id="broken")


def _broken_edge_setup():
    """A valid chain, and a plan whose edge names a problem it does not pose."""
    target = chain(cmat.COPPER, cmat.COPPER, chain_id="broken")
    _, dependencies, plan = pc.compose(target, seed=SEED)
    ghost = QuantityDependency(
        source_problem_id="conductor_resistance:ghost_wire",
        source_quantity=cmat.RESISTANCE_METRIC,
        target_problem_id=target.electrical_problem_id,
        target_quantity="R:wire_A",
        unit_exemplar=cmat.RESISTANCE_UNIT,
        name="broken",
    )
    mangled = (ghost,) + tuple(
        d for d in dependencies
        if d.name != "conductor-resistance-sets-circuit-element:wire_A"
    )
    broken = cpl.FixedPointCouplingPlan(
        plan_id="broken", dependencies=mangled, torn=plan.torn,
        absolute_tolerance=TOL, max_iterations=5,
    )
    return target, broken


@_register("duplicated_identity")
def _duplicate_identity(_):
    pc.PowerChain(
        chain_id="dup", source_voltage=VOLTS,
        elements=(wire("w", cmat.COPPER), pc.FixedLoad("w", LOAD)),
    )


@_register(
    "invalid_serialized_version",
    setup=lambda: chain(cmat.COPPER, cmat.COPPER).to_dict(),
)
def _bad_schema(payload):
    payload = dict(payload)
    payload["schema"] = "electrothermal_power_chain/2"
    pc.PowerChain.from_dict(payload)


@_register("unsupported_material_schema")
def _bad_material_schema(_):
    payload = dict(cmat.COPPER.to_dict())
    payload["schema"] = "cubic_resistivity_material/1"
    cmat.material_from_dict(payload)


@_register("unknown_property_form")
def _wrong_solver_for_material(_):
    """A material whose functional form this evaluator does not implement."""
    conductor = cmat.MaterialConductor("w", cmat.TUNGSTEN, LENGTH, AREA)
    cmat.LinearResistivitySolver().bind_conductor(conductor, "p", temperature=SEED)


@_register("chain_with_no_wire")
def _no_wire(_):
    pc.PowerChain(
        chain_id="loads-only", source_voltage=VOLTS,
        elements=(pc.FixedLoad("load", LOAD),),
    )


@_register("material_with_no_provenance")
def _no_source(_):
    cmat.LinearResistivityMaterial(
        name="anonymous",
        reference_resistivity=Quantity(1e-8, "ohm * meter"),
        temperature_coefficient=Quantity(4e-3, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(450.0, KELVIN),
        source="   ",
    )


@_register("material_reference_outside_its_own_range")
def _reference_outside_range(_):
    cmat.LinearResistivityMaterial(
        name="inconsistent",
        reference_resistivity=Quantity(1e-8, "ohm * meter"),
        temperature_coefficient=Quantity(4e-3, "1/kelvin"),
        reference_temperature=Quantity(600.0, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(450.0, KELVIN),
        source="probe",
    )


@_register("unstated_property_is_not_defaulted")
def _missing_coefficient(_):
    """An unstated property stays unstated; it is never invented as zero."""
    cmat.LinearResistivityMaterial(
        name="silent",
        reference_resistivity=Quantity(1e-8, "ohm * meter"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(450.0, KELVIN),
        source="probe",
    )


@_register("unstated_second_order_coefficient")
def _missing_second_order(_):
    cmat.QuadraticResistivityMaterial(
        name="silent-quadratic",
        reference_resistivity=Quantity(1e-8, "ohm * meter"),
        temperature_coefficient=Quantity(4e-3, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(450.0, KELVIN),
        source="probe",
    )


@_register("non_positive_reference_resistivity")
def _negative_rho(_):
    cmat.LinearResistivityMaterial(
        name="antimatter",
        reference_resistivity=Quantity(-1e-8, "ohm * meter"),
        temperature_coefficient=Quantity(4e-3, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(450.0, KELVIN),
        source="probe",
    )


@pytest.mark.parametrize("case", sorted(NEGATIVE_CASES))
def test_e1_every_invalid_configuration_is_refused(case, monkeypatch):
    setup, action = NEGATIVE_CASES[case]
    prepared = setup()
    spy = _Spy(monkeypatch)
    with pytest.raises((InvalidScientificProblem, ScientificCoreError,
                        UnitCompatibilityError, TypeError)):
        action(prepared)
    assert spy.calls == [], (
        f"{case}: {len(spy.calls)} solver call(s) ran despite the refusal — "
        f"detection is not enforcement"
    )


def test_e2_the_refusal_names_the_admissible_set():
    with pytest.raises(InvalidScientificProblem) as excinfo:
        cmat.resolve_material("unobtainium")
    message = str(excinfo.value)
    for name in cmat.known_material_names():
        assert name in message


def test_e3_admission_runs_on_the_executed_path_not_only_when_asked(monkeypatch):
    """A gate a caller can skip is detection, not enforcement."""
    target = chain(cmat.COPPER, cmat.COPPER, chain_id="hot2")
    # Built WITHOUT `compose`, which now admits first: the point of this test
    # is that `run_power_chain` gates on its own, for a caller who assembled a
    # plan by hand.
    hot = Quantity(500.0, KELVIN)
    problems = pc.chain_problems(
        target, {w.component_id: Quantity(1.0, "ohm") for w in target.wires}
    )
    plan = pc.chain_plan(
        target, pc.chain_dependencies(target, problems), seed=hot,
        tolerance=TOL, max_iterations=5,
    )
    calls = []
    original = pc.admit_power_chain
    monkeypatch.setattr(
        pc, "admit_power_chain",
        lambda *a, **k: (calls.append(1), original(*a, **k))[1],
    )
    with pytest.raises(InvalidScientificProblem):
        pc.run_power_chain(target, plan, run_id="hot2")
    assert calls, "run_power_chain must call the gate itself"


def test_e4_a_run_that_converges_outside_applicability_is_reported_not_hidden():
    """Assessed, never refused after the fact.

    The `ET-VERTICAL` gap, closed from the reporting side: a run that starts
    admissibly and converges outside a declared range must say so, and the
    record that makes it readable must survive.
    """
    target = chain(cmat.COPPER, cmat.COPPER, chain_id="overheat",
                   conductance=0.05)
    run, _, _ = execute(target, run_id="overheat", budget=200)
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assessments = pc.assess_run_applicability(target, run)
    assert set(assessments) == {"wire_A", "wire_B"}
    for cid, assessment in assessments.items():
        assert assessment.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        assert temperature_of(run, cid).magnitude_in(KELVIN) > 450.0
    # The sub-solves all succeeded, which is exactly why the assessment has to
    # be a separate answer.
    for result in run.final.results:
        assert result.convergence in (
            ConvergenceState.CONVERGED, ConvergenceState.NOT_APPLICABLE
        )


def test_e5_a_run_inside_the_range_reports_in_domain(case_a):
    target, run, _, _ = case_a
    assessments = pc.assess_run_applicability(target, run)
    assert all(
        a.status is ValidityStatus.IN_DOMAIN for a in assessments.values()
    )


# =====================================================================
# F — serialization
# =====================================================================

def test_f1_the_chain_round_trips_and_preserves_the_material_selection():
    target = chain(cmat.ALUMINIUM, cmat.TUNGSTEN, chain_id="mixed")
    payload = json.loads(json.dumps(target.to_dict()))
    restored = pc.PowerChain.from_dict(payload)
    assert restored == target
    assert restored.wire("wire_A").material.name == "aluminium"
    assert restored.wire("wire_B").material.name == "tungsten"
    assert isinstance(
        restored.wire("wire_B").material, cmat.QuadraticResistivityMaterial
    )
    assert restored.to_dict() == target.to_dict()


def test_f2_component_identities_and_order_are_stable_across_the_round_trip():
    target = chain(cmat.COPPER, cmat.SILVER, chain_id="ordered")
    restored = pc.PowerChain.from_dict(json.loads(json.dumps(target.to_dict())))
    assert restored.component_ids == target.component_ids == (
        "wire_A", "load", "wire_B"
    )
    assert restored.circuit_id == target.circuit_id
    assert restored.electrical_problem_id == target.electrical_problem_id


def test_f3_reconstruction_preserves_semantics_to_the_last_digit():
    target = chain(cmat.ALUMINIUM, cmat.COPPER, chain_id="powerchain")
    restored = pc.PowerChain.from_dict(json.loads(json.dumps(target.to_dict())))
    original_run, _, _ = execute(target, run_id="orig")
    restored_run, _, _ = execute(restored, run_id="restored")
    for cid in ("wire_A", "wire_B"):
        assert (
            resistance_of(restored_run, cid).magnitude
            == resistance_of(original_run, cid).magnitude
        )
        assert (
            temperature_of(restored_run, cid).magnitude
            == temperature_of(original_run, cid).magnitude
        )


def test_f4_an_unsupported_schema_fails_clearly():
    for payload, mutate, reader in (
        (chain(cmat.COPPER, cmat.COPPER).to_dict(),
         "electrothermal_power_chain/2", pc.PowerChain.from_dict),
        (cmat.COPPER.to_dict(), "linear_resistivity_material/2",
         cmat.LinearResistivityMaterial.from_dict),
        (cmat.MaterialConductor("w", cmat.COPPER, LENGTH, AREA).to_dict(),
         "material_conductor/2", cmat.MaterialConductor.from_dict),
    ):
        broken = dict(payload)
        broken["schema"] = mutate
        with pytest.raises(ScientificCoreError, match="unsupported schema"):
            reader(broken)


def test_f5_an_unknown_element_kind_is_refused_rather_than_guessed():
    payload = chain(cmat.COPPER, cmat.COPPER).to_dict()
    payload["elements"][1]["kind"] = "flux_capacitor"
    with pytest.raises(InvalidScientificProblem, match="element kind"):
        pc.PowerChain.from_dict(payload)


def test_f6_the_serialized_element_list_keeps_its_order():
    """Order is scientific content: it assigns the nodes."""
    target = chain(cmat.COPPER, cmat.COPPER)
    payload = target.to_dict()
    assert isinstance(payload["elements"], list)
    assert [e.get("component_id") or e["conductor"]["component_id"]
            for e in payload["elements"]] == ["wire_A", "load", "wire_B"]


def test_f7_a_wire_serializes_without_the_catalogue_being_consulted():
    """A material constructed inline round-trips identically."""
    inline = cmat.LinearResistivityMaterial(
        name="test-alloy",
        reference_resistivity=Quantity(4.4e-7, "ohm * meter"),
        temperature_coefficient=Quantity(1.0e-4, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(250.0, KELVIN),
        maximum_temperature=Quantity(700.0, KELVIN),
        source="declared inline by a test; not a catalogue entry",
    )
    conductor = cmat.MaterialConductor("w", inline, LENGTH, AREA)
    restored = cmat.MaterialConductor.from_dict(
        json.loads(json.dumps(conductor.to_dict()))
    )
    assert restored == conductor
    assert restored.material.name not in cmat.MATERIAL_CATALOGUE


# =====================================================================
# G — direct scientific execution is still compatible
# =====================================================================

def test_g1_the_existing_linear_tcr_path_is_untouched():
    """`ET-VERTICAL` CASE A, reproduced against the pre-existing pack."""
    conductor = legacy_mat.TemperatureDependentConductor(
        component_id="R1",
        reference_resistance=Quantity(10.0, "ohm"),
        temperature_coefficient=Quantity(0.00393, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
    )
    system = legacy_coupled.CoupledElectroThermalSystem(
        stages=(
            legacy_coupled.CoupledStage(
                conductor=conductor,
                body=lump.ThermalBody(
                    "R1", Quantity(2.5, "joule/kelvin"),
                    Quantity(0.05, "watt/kelvin"), Quantity(300.0, KELVIN),
                    Quantity(300.0, KELVIN), Quantity(120.0, "second"),
                ),
            ),
        ),
        source_voltage=Quantity(5.0, "volt"),
    )
    problems = legacy_coupled.coupled_problems(
        system, {"R1": conductor.reference_resistance}
    )
    dependencies = legacy_coupled.coupled_dependencies(system, problems)
    plan = legacy_coupled.nominal_plan(
        system, dependencies, seed=Quantity(300.0, KELVIN)
    )
    run = legacy_coupled.run_fixed_point_coupling(system, plan, run_id="g1")
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert run.iterations_run == api_case.CASE_A_ITERATIONS
    temperature = run.final.result_for(
        "thermal-lumped-R1"
    ).value(lump.TEMPERATURE_METRIC)
    assert temperature.magnitude_in(KELVIN) == pytest.approx(
        api_case.CASE_A_TEMPERATURE_K, abs=1e-6
    )


def test_g2_the_two_property_mechanisms_coexist_without_dispatch_collision():
    """Each solver matches on the model reference its problem carries."""
    legacy_conductor = legacy_mat.TemperatureDependentConductor(
        "R1", Quantity(10.0, "ohm"), Quantity(0.00393, "1/kelvin"),
        Quantity(293.15, KELVIN),
    )
    legacy_problem = legacy_mat.build_resistance_problem(legacy_conductor)
    new_conductor = cmat.MaterialConductor("w", cmat.COPPER, LENGTH, AREA)
    new_problem = cmat.build_resistivity_problem(new_conductor)
    quadratic_problem = cmat.build_resistivity_problem(
        cmat.MaterialConductor("t", cmat.TUNGSTEN, LENGTH, AREA)
    )
    geometric_problem = cmat.build_geometric_resistance_problem(new_conductor)

    assert legacy_mat.ResistancePropertySolver().supports(legacy_problem)
    assert not legacy_mat.ResistancePropertySolver().supports(new_problem)
    assert cmat.LinearResistivitySolver().supports(new_problem)
    assert not cmat.LinearResistivitySolver().supports(legacy_problem)
    assert not cmat.LinearResistivitySolver().supports(quadratic_problem)
    assert cmat.QuadraticResistivitySolver().supports(quadratic_problem)
    assert cmat.GeometricResistanceSolver().supports(geometric_problem)
    assert not cmat.GeometricResistanceSolver().supports(new_problem)


def test_g3_supports_is_stateless_and_works_for_an_uncatalogued_material():
    inline = cmat.LinearResistivityMaterial(
        name="never-catalogued",
        reference_resistivity=Quantity(9.9e-8, "ohm * meter"),
        temperature_coefficient=Quantity(2.0e-3, "1/kelvin"),
        reference_temperature=Quantity(300.0, KELVIN),
        minimum_temperature=Quantity(250.0, KELVIN),
        maximum_temperature=Quantity(500.0, KELVIN),
        source="declared inline by a test",
    )
    problem = cmat.build_resistivity_problem(
        cmat.MaterialConductor("w", inline, LENGTH, AREA)
    )
    # No binding has happened; the predicate must still answer.
    assert cmat.LinearResistivitySolver().supports(problem)


def test_g4_the_models_bind_cleanly_to_the_problems_they_are_named_in():
    conductor = cmat.MaterialConductor("w", cmat.TUNGSTEN, LENGTH, AREA)
    assert cmat.QUADRATIC_RESISTIVITY_MODEL.check_against(
        cmat.build_resistivity_problem(conductor)
    ).is_satisfied
    assert cmat.GEOMETRIC_RESISTANCE_MODEL.check_against(
        cmat.build_geometric_resistance_problem(conductor)
    ).is_satisfied


def test_g5_the_declared_capabilities_are_true_of_the_records_that_declare_them():
    """A geometry relation does not provide temperature-dependent resistance."""
    registry = cmat.conductor_material_realizations()
    providers = registry.providing(cmat.RESISTANCE_FROM_GEOMETRY)
    assert [r.realization_id for r in providers] == [
        "electrical.conductor.geometric_resistance.closed_form"
    ]
    resistivity_providers = registry.providing(
        cmat.TEMPERATURE_DEPENDENT_RESISTIVITY
    )
    assert len(resistivity_providers) == 2
    # The geometric realization does NOT claim the pre-existing capability.
    combined = RealizationRegistry(
        (legacy_mat.LINEAR_TCR_REALIZATION, cmat.GEOMETRIC_RESISTANCE_REALIZATION)
    )
    assert [
        r.realization_id
        for r in combined.providing(legacy_mat.TEMPERATURE_DEPENDENT_RESISTANCE)
    ] == ["electrical.material.linear_tcr_resistance.closed_form"]
    # ...and it declares the dependency that makes the composition readable.
    assert cmat.TEMPERATURE_DEPENDENT_RESISTIVITY in (
        cmat.GEOMETRIC_RESISTANCE_REALIZATION.required_capabilities
    )


def test_g6_three_models_register_under_distinct_identities():
    registry = cmat.conductor_material_registry()
    assert len(registry) == 3
    assert {m.model_id for m in registry} == {
        "electrical.material.linear_resistivity",
        "electrical.material.quadratic_resistivity",
        "electrical.conductor.geometric_resistance",
    }


# =====================================================================
# H — existing API/MCP semantics unchanged
# =====================================================================

def test_h1_the_execution_catalog_is_unchanged():
    assert catalog.execution_identities() == frozenset(
        {"electrothermal.series_self_heating/1"}
    )
    assert catalog.profile_names("electrothermal.series_self_heating/1") == (
        frozenset({"native", "ngspice"})
    )


def test_h2_the_canonical_external_request_returns_the_same_numbers():
    response = service.handle(api_case.canonical_request())
    assert response["schema"] == api_case.RESPONSE_SCHEMA
    assert response["status"] == "executed"
    assert response["result"]["coupling"]["outcome"] == "criterion_met"
    assert response["result"]["coupling"]["iterations_run"] == (
        api_case.CASE_A_ITERATIONS
    )
    temperature = api_case.output(response, "final_temperature")
    assert temperature["value"]["value"] == pytest.approx(
        api_case.CASE_A_TEMPERATURE_K, abs=1e-6
    )
    assert temperature["value"]["unit"] == "kelvin"
    resistance = api_case.output(response, "resistance")
    assert resistance["value"]["value"] == pytest.approx(
        api_case.CASE_A_RESISTANCE_OHM, abs=1e-6
    )
    power = api_case.output(response, "resistor_power:R1")
    assert power["value"]["value"] == pytest.approx(
        api_case.CASE_A_POWER_W, abs=1e-6
    )


def test_h3_the_request_schema_gained_nothing():
    fragment = catalog.EXECUTIONS[
        "electrothermal.series_self_heating/1"
    ].request_fragment()
    text = json.dumps(fragment)
    for word in ("material", "resistivity", "length", "cross_sectional_area",
                 "power_chain", "wire"):
        assert word not in text, (
            f"the external request schema mentions {word!r}; this milestone "
            f"was supposed to add nothing to the API surface"
        )


def test_h4_the_application_layer_cannot_reach_this_milestones_modules():
    for module in (
        "src/engcore/application/catalog.py",
        "src/engcore/application/service.py",
        "src/engcore/application/contract.py",
        "src/engcore/application/describe.py",
        "src/engcore/application/executions/electrothermal_series.py",
        "src/crafty_http/server.py",
        "src/crafty_mcp/server.py",
    ):
        source = (REPO_ROOT / module).read_text(encoding="utf-8")
        assert "conductor_material" not in source
        assert "power_chain" not in source


# =====================================================================
# T3 / T4 — the third and fourth materials
# =====================================================================

def test_t3_a_third_material_runs_end_to_end_as_catalogue_data_only():
    """Silver. The falsification test the milestone was asked for.

    If a third material had needed new code, the mechanism would be
    branch-driven rather than property-driven. It needed one frozen record in
    the catalogue table — asserted structurally by
    ``test_t6_no_material_name_appears_outside_the_catalogue_data``.
    """
    target = chain(cmat.SILVER, cmat.SILVER, chain_id="silver")
    run, _, _ = execute(target, run_id="silver")
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    assert resistance_of(run, "wire_A").magnitude_in("ohm") == pytest.approx(
        0.01486675835, rel=1e-8
    )
    assert temperature_of(run, "wire_A").magnitude_in(KELVIN) == pytest.approx(
        338.1446594, rel=1e-8
    )
    assert run.final.result_for(
        "conductor_resistivity:wire_A"
    ).provenance.bindings[0].solver.solver_id == (
        "engcore.electrical.linear_resistivity_evaluator"
    )


def test_t3b_silver_sits_between_copper_and_aluminium_as_physics_requires(
    case_a, case_b
):
    silver_run, _, _ = execute(
        chain(cmat.SILVER, cmat.SILVER, chain_id="silver2"), run_id="silver2"
    )
    silver = resistance_of(silver_run, "wire_A").magnitude_in("ohm")
    copper = resistance_of(case_a[1], "wire_A").magnitude_in("ohm")
    aluminium = resistance_of(case_b[1], "wire_A").magnitude_in("ohm")
    assert silver < copper < aluminium


def test_t4_a_material_the_catalogue_has_never_seen_runs_end_to_end():
    """Constructed here, in the test, and never registered anywhere."""
    alloy = cmat.LinearResistivityMaterial(
        name="constantan-like-test-alloy",
        reference_resistivity=Quantity(4.9e-7, "ohm * meter"),
        temperature_coefficient=Quantity(2.0e-5, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
        minimum_temperature=Quantity(200.0, KELVIN),
        maximum_temperature=Quantity(700.0, KELVIN),
        source=(
            "declared inline by test_t4; a resistance-alloy-like property set "
            "with a deliberately near-zero temperature coefficient. Not a "
            "catalogue entry and not a measured material."
        ),
    )
    assert alloy.name not in cmat.MATERIAL_CATALOGUE
    target = chain(alloy, alloy, chain_id="alloy", volts=Quantity(12.0, "volt"))
    run, _, _ = execute(target, run_id="alloy")
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    resistance = resistance_of(run, "wire_A").magnitude_in("ohm")
    temperature = temperature_of(run, "wire_A").magnitude_in(KELVIN)
    expected = alloy.rho_ref_ohm_m * (
        1.0 + alloy.alpha_per_k * (temperature - alloy.t_ref_k)
    ) * LENGTH.magnitude_in("meter") / AREA.magnitude_in("meter ** 2")
    assert resistance == pytest.approx(expected, rel=1e-14)
    # A near-zero coefficient means self-heating barely moves the resistance.
    assert abs(resistance / (4.9e-7 * 2.0 / 2.5e-6) - 1.0) < 5e-3


# =====================================================================
# T5 — the second functional form is load-bearing
# =====================================================================

def test_t5_the_quadratic_form_is_not_reachable_by_the_linear_model():
    """Closes the falsifier's X8 for the material claim.

    Tungsten at 20 V converges to a state the *same* material's linear form,
    anchored at the same reference resistivity, reference temperature and
    first-order coefficient, does not reach. If the two agreed, this consumer
    would be a reparameterization of a model the repository already executes.
    """
    target = pc.PowerChain(
        chain_id="tungsten",
        source_voltage=Quantity(20.0, "volt"),
        elements=(
            wire("wire_A", cmat.TUNGSTEN),
            pc.FixedLoad("load", LOAD),
            wire("wire_B", cmat.TUNGSTEN),
        ),
    )
    run, _, _ = execute(target, run_id="tungsten", budget=100)
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    quadratic_t = temperature_of(run, "wire_A").magnitude_in(KELVIN)
    quadratic_r = resistance_of(run, "wire_A").magnitude_in("ohm")
    assert quadratic_t == pytest.approx(759.553617, rel=1e-7)
    assert quadratic_r == pytest.approx(0.139281965, rel=1e-7)

    # Same rho_ref, same T_ref, same alpha — the linear form of the very same
    # material, expressed with the pre-existing mechanism.
    linear_twin = cmat.LinearResistivityMaterial(
        name="tungsten-linear-only",
        reference_resistivity=cmat.TUNGSTEN.reference_resistivity,
        temperature_coefficient=cmat.TUNGSTEN.temperature_coefficient,
        reference_temperature=cmat.TUNGSTEN.reference_temperature,
        minimum_temperature=cmat.TUNGSTEN.minimum_temperature,
        maximum_temperature=cmat.TUNGSTEN.maximum_temperature,
        source="the linear truncation of TUNGSTEN, built by test_t5",
    )
    linear_target = pc.PowerChain(
        chain_id="tungsten-linear",
        source_voltage=Quantity(20.0, "volt"),
        elements=(
            wire("wire_A", linear_twin),
            pc.FixedLoad("load", LOAD),
            wire("wire_B", linear_twin),
        ),
    )
    linear_run, _, _ = execute(linear_target, run_id="tungsten-linear", budget=100)
    linear_t = temperature_of(linear_run, "wire_A").magnitude_in(KELVIN)
    assert linear_t == pytest.approx(744.643001, rel=1e-7)
    assert abs(quadratic_t - linear_t) == pytest.approx(14.9106, rel=1e-3)
    assert abs(quadratic_t - linear_t) > 1e6 * TOL.magnitude_in(KELVIN)


def test_t5c_a_third_thermally_active_element_is_admitted_not_refused():
    """The fan-in wall is two sources on ONE endpoint, not one body per element.

    A third wire adds a third body, a third `heat_input` endpoint, a third
    4-cycle and a third torn edge. The plan admits all of it, which is the
    measured basis for saying that the `FixedLoad`'s thermal isolation is a
    design choice about what this milestone varies — not a contract limit.
    """
    target = pc.PowerChain(
        chain_id="three-wire",
        source_voltage=Quantity(18.0, "volt"),
        elements=(
            wire("wire_A", cmat.COPPER),
            wire("wire_M", cmat.ALUMINIUM),
            pc.FixedLoad("load", LOAD),
            wire("wire_B", cmat.SILVER),
        ),
    )
    problems, dependencies, plan = pc.compose(target, seed=SEED)
    assert len(problems) == 10          # 1 electrical + 3 per wire
    assert len(dependencies) == 12      # 4 per wire
    assert len(plan.torn) == 3
    assert plan.check_against(problems) == ()   # no fan-in, no unresolved edge
    run = pc.run_power_chain(target, plan, run_id="three")
    assert run.outcome is cpl.CouplingOutcome.CRITERION_MET
    # Three independent instances, three materials, three property laws.
    for cid, material in (("wire_A", cmat.COPPER), ("wire_M", cmat.ALUMINIUM),
                          ("wire_B", cmat.SILVER)):
        temperature = input_temperature_of(run, cid).magnitude_in(KELVIN)
        expected = material.rho_ref_ohm_m * (
            1.0 + material.alpha_per_k * (temperature - material.t_ref_k)
        )
        assert resistivity_of(run, cid).magnitude_in("ohm * meter") == (
            pytest.approx(expected, rel=1e-14)
        )
    resistances = {
        cid: resistance_of(run, cid).magnitude_in("ohm")
        for cid in ("wire_A", "wire_M", "wire_B")
    }
    assert len(set(resistances.values())) == 3
    assert resistances["wire_B"] < resistances["wire_A"] < resistances["wire_M"]


def test_t5b_material_identity_selects_the_model_that_is_evaluated():
    """The selection is data-driven: the record declares its own model."""
    assert cmat.COPPER.resistivity_model() is cmat.LINEAR_RESISTIVITY_MODEL
    assert cmat.TUNGSTEN.resistivity_model() is cmat.QUADRATIC_RESISTIVITY_MODEL
    assert type(cmat.resistivity_solver_for(cmat.COPPER)) is (
        cmat.LinearResistivitySolver
    )
    assert type(cmat.resistivity_solver_for(cmat.TUNGSTEN)) is (
        cmat.QuadraticResistivitySolver
    )
    copper_problem = cmat.build_resistivity_problem(
        cmat.MaterialConductor("w", cmat.COPPER, LENGTH, AREA)
    )
    tungsten_problem = cmat.build_resistivity_problem(
        cmat.MaterialConductor("w", cmat.TUNGSTEN, LENGTH, AREA)
    )
    assert copper_problem.models != tungsten_problem.models
    assert {p.name for p in tungsten_problem.parameters} - {
        p.name for p in copper_problem.parameters
    } == {"second_order_coefficient"}


# =====================================================================
# T6 — no domain conditionals, no new universal contracts, nothing else moved
# =====================================================================

NEW_FILES = (
    "src/engcore/domains/electrical/conductor_material.py",
    "src/engcore/systems/electrothermal/power_chain.py",
)

FROZEN_TREES = (
    "src/engcore/scientific",
    "src/engcore/coupling",
    "src/engcore/domains/electrical/dc",
    "src/engcore/application",
    "src/crafty_http",
    "src/crafty_mcp",
)


def _source(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_t6_no_material_name_appears_outside_the_catalogue_data():
    """Adding a material must be data, never a branch.

    Every material name may appear exactly where the catalogue declares it and
    nowhere else in production source — no ``if name == "aluminium"``, no
    lookup table of behaviour keyed by name, nothing.
    """
    names = set(cmat.known_material_names())
    source = _source(NEW_FILES[0])
    tree = ast.parse(source)
    # The catalogue's variable names are DERIVED from the module, never
    # transcribed: a hardcoded list would itself be a line that has to change
    # when a material is added, which is the very cost this test measures.
    catalogue_names = {
        name for name, value in vars(cmat).items()
        if isinstance(value, cmat.ConductorMaterial)
    } | {"MATERIAL_CATALOGUE"}
    catalogue_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in catalogue_names
            for t in node.targets
        ):
            catalogue_lines.update(range(node.lineno, (node.end_lineno or 0) + 1))
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in names and node.lineno not in catalogue_lines:
                offenders.append((node.lineno, node.value))
    assert not offenders, (
        f"material names outside the catalogue declaration: {offenders}"
    )
    for path in NEW_FILES[1:] + FROZEN_TREES:
        for file in (
            [REPO_ROOT / path] if str(path).endswith(".py")
            else sorted((REPO_ROOT / path).rglob("*.py"))
        ):
            text = file.read_text(encoding="utf-8")
            for name in names:
                assert f'"{name}"' not in text and f"'{name}'" not in text, (
                    f"{file} names material {name!r}"
                )


def test_t6b_universal_core_and_coupling_name_no_new_domain_vocabulary():
    forbidden = (
        "resistivity", "conductor_material", "power_chain", "cross_sectional",
        "MaterialConductor", "WireSegment", "PowerChain",
    )
    for tree in ("src/engcore/scientific", "src/engcore/coupling"):
        for file in sorted((REPO_ROOT / tree).rglob("*.py")):
            text = file.read_text(encoding="utf-8")
            for word in forbidden:
                assert word not in text, f"{file} names {word!r}"


def test_t6c_no_component_port_or_system_contract_was_created():
    """The kill criteria, asserted rather than asserted-about."""
    banned = (
        "class ComponentInstance", "class Port", "class Connector",
        "class SystemDefinition", "class MaterialBinding",
        "class MaterialProperty", "class MaterialState",
        "class PropertyRequirement", "class PropertyBinding",
    )
    for path in NEW_FILES:
        text = _source(path)
        for word in banned:
            assert word not in text, f"{path} declares {word!r}"
    # And universal core gained nothing at all.
    for tree in ("src/engcore/scientific", "src/engcore/coupling"):
        for file in sorted((REPO_ROOT / tree).rglob("*.py")):
            text = file.read_text(encoding="utf-8")
            for word in banned:
                assert word not in text, f"{file} declares {word!r}"


def test_t6d_the_new_modules_duplicate_no_existing_contract():
    for path in NEW_FILES:
        text = _source(path)
        for word in ("class ScientificProblem", "class QuantityDependency",
                     "class ScientificResult", "class ProvenanceRecord",
                     "class ExecutionBinding", "def run_fixed_point"):
            assert word not in text, f"{path} redefines {word!r}"


def test_t6e_the_new_modules_hold_no_untyped_property_dictionary():
    """No metadata escape hatch, and no bare-dict property bag."""
    for path in NEW_FILES:
        text = _source(path)
        assert "metadata=" not in text
        assert "dict[str, Any]" not in text.replace(
            "-> dict[str, Any]:", ""
        ), f"{path} carries an untyped mapping field"


def test_t6f_the_working_tree_changed_only_where_the_prereg_said_it_would():
    """Nothing outside the allowed set moved.

    Read from git rather than from a hand-maintained list, so a stray edit is
    loud instead of silent.
    """
    import subprocess

    committed = subprocess.run(
        ["git", "diff", "--name-only", "fdd3359", "HEAD"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
    ).stdout.split()
    # ...and the working tree, so an uncommitted stray edit is just as loud.
    working = [
        line[3:].strip().strip('"')
        for line in subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    ]
    diff = committed + working
    allowed = {
        ".gitignore",
        "docs/evidence/composite-system0-preregistration.md",
        "docs/evidence/composite-system0-evidence.md",
        "src/engcore/domains/electrical/conductor_material.py",
        "src/engcore/systems/electrothermal/power_chain.py",
        "src/engcore/systems/electrothermal/__init__.py",
        "tests/test_composite_system0.py",
        # ONE pre-existing test was modified, and only because it carried a
        # demonstrated defect: `test_e2`'s blanket "no system pack mints any
        # schema string" was broader than its own stated claim about the
        # COUPLING record family, and the replacement is stronger. Documented
        # in docs/evidence/composite-system0-evidence.md.
        "tests/test_coupling_pack_relocation.py",
        # ...and one historical scope guard, which read
        # `git diff <its own prereg commit>` and therefore failed for every
        # LATER milestone that adds a file under src/engcore/domains/ or
        # src/engcore/systems/electrothermal/. The repository already carries
        # this repair three times in test_executable_scientific_spec.py; this
        # is the fourth, and it weakens nothing that milestone claims.
        "tests/test_api_mcp_v0.py",
        # ...and THIS guard has the identical defect, for the identical reason.
        # It reads `git diff <COMPOSITE-SYSTEM0's own prereg commit> HEAD` over
        # the WHOLE tree, so every later milestone fails it however correct the
        # later work is. `PROPULSION0` is the first to trip it. The repair is
        # the narrowest available: the files that milestone adds are named
        # INDIVIDUALLY below, so a stray edit anywhere else is still loud, and
        # not one file COMPOSITE-SYSTEM0 asserts unchanged is excluded —
        # universal core, engcore.coupling, the Fluid-Thermal pack, the DC
        # domain, conductor_material.py and power_chain.py all remain covered.
        "docs/evidence/propulsion0-preregistration.md",
        "docs/evidence/propulsion0-evidence.md",
        "src/engcore/domains/mechanical_rotational.py",
        "src/engcore/systems/propulsion/__init__.py",
        "src/engcore/systems/propulsion/materials.py",
        "src/engcore/systems/propulsion/models.py",
        "src/engcore/systems/propulsion/drive.py",
        "tests/test_propulsion0.py",
        # The two historical scope guards PROPULSION0 had to repair, for the
        # same reason this file already excludes test_api_mcp_v0.py once.
        "docs/CRAFTY_MASTER_CONTEXT.md",
    }
    stray = sorted(set(diff) - allowed)
    assert not stray, f"files changed outside the preregistered set: {stray}"


def test_t6g_the_conductor_material_module_imports_no_thermal_code():
    """A real scientific dependency, declared by identifier and never imported."""
    tree = ast.parse(_source(NEW_FILES[0]))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
    assert not any("thermal" in m for m in imported), imported
    assert str(cmat.REQUIRED_BODY_TEMPERATURE) == "thermal:body_temperature"


def test_t6h_geometry_and_state_are_typed_and_carry_their_units():
    model = cmat.GEOMETRIC_RESISTANCE_MODEL
    by_name = {spec.name: spec for spec in model.inputs}
    assert by_name["length"].source_kind is InputSourceKind.PARAMETER
    assert by_name["cross_sectional_area"].source_kind is InputSourceKind.PARAMETER
    assert by_name["resistivity"].source_kind is InputSourceKind.VARIABLE
    assert by_name["resistivity"].role is VariableRole.CONTROL
    temperature = {
        s.name: s for s in cmat.LINEAR_RESISTIVITY_MODEL.inputs
    }["temperature"]
    assert temperature.source_kind is InputSourceKind.VARIABLE
    assert temperature.role is VariableRole.STATE


def test_t6i_a_material_range_has_exactly_one_authority():
    """The range lives on the record, and is restated by no model."""
    for model in (cmat.LINEAR_RESISTIVITY_MODEL,
                  cmat.QUADRATIC_RESISTIVITY_MODEL):
        assert {c.name for c in model.validity.conditions} == {
            "reference_resistivity"
        }
    domain = cmat.COPPER.applicability()
    condition = domain.conditions[0]
    assert condition.minimum == cmat.COPPER.minimum_temperature
    assert condition.maximum == cmat.COPPER.maximum_temperature
    assert cmat.assess_material_applicability(
        cmat.COPPER, Quantity(500.0, KELVIN)
    ).status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert cmat.assess_material_applicability(
        cmat.TUNGSTEN, Quantity(500.0, KELVIN)
    ).status is ValidityStatus.IN_DOMAIN


def test_t6j_geometry_validity_is_actually_evaluated_not_permanently_unknown():
    """The falsifier's X1: a condition on a variable would never be checked."""
    conductor = cmat.MaterialConductor("w", cmat.COPPER, LENGTH, AREA)
    assessment = cmat.assess_conductor_geometry(conductor)
    assert assessment.status is ValidityStatus.IN_DOMAIN
    assert not assessment.unknown, (
        "a validity condition that can never be evaluated makes every "
        "conductor unassessable"
    )
    assert set(assessment.satisfied) == {"length", "cross_sectional_area"}


def test_t6k_the_material_categorical_carries_no_catalogue_vocabulary():
    """The falsifier's X6: library membership must not enter a wire's record."""
    conductor = cmat.MaterialConductor("w", cmat.COPPER, LENGTH, AREA)
    before = cmat.build_resistivity_problem(conductor).to_dict()
    declared = cmat.build_resistivity_problem(conductor).parameter("material").value
    assert declared.vocabulary == ()
    text = json.dumps(before)
    for name in cmat.known_material_names():
        if name != "copper":
            assert name not in text, (
                "a wire's serialized record must not carry the catalogue"
            )


def test_t6l_the_coupling_package_was_not_edited():
    """Reused by object identity, not by copy."""
    import inspect

    source = inspect.getsource(cpl.run_fixed_point)
    assert "material" not in source
    assert "resistivity" not in source
    assert pc.run_fixed_point is cpl.run_fixed_point
