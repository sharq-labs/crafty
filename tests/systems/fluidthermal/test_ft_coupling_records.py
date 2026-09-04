"""FT-SCALAR-COUPLING — everything provable without solving the PDE.

The composition's records, the two property claims, the independent coupled
reference, the four preregistered negative results, and the architecture
guards. Nothing here runs the fluid solver; the executed coupling lives in
``test_ft_coupling_execution.py``.

Preregistered in ``docs/fluid-thermal-scalar-coupling-prereg.md``; this module
is not free to move the criteria it checks.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess

import pytest

from engcore.domains import thermal_lumped as lump
from engcore.domains.fluids import transport2d as fluid
from engcore.scientific.composition import (
    QuantityDependency,
    unresolved_inputs,
)
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.orientation import OrientationSign
from engcore.scientific.ir.variables import VariableRole
from engcore.scientific.units.quantity import Quantity
from engcore.systems import fluidthermal as ft
from engcore import coupling as cpl
from engcore.systems.fluidthermal import coupled as ftc
from engcore.systems.fluidthermal import properties as prop

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

#: The frozen declaration of the preregistration, restated once.
D_REF = 0.01
T_REF = 300.0
EXPONENT = 1.75
RHO_CP = 1.2e3
DEPTH = 1.0e-3
T_AMB = 300.0

REFERENCE_CONSTANTS = dict(
    ambient_k=T_AMB,
    reference_diffusivity=D_REF,
    reference_temperature_k=T_REF,
    exponent=EXPONENT,
    volumetric_heat_capacity=RHO_CP,
    depth_m=DEPTH,
)


def make_system(*, n_cells: int = 32, heat_w: float = 6.0) -> ft.FluidThermalSystem:
    """The preregistered system. One place, so no test can quietly retune it."""
    return ft.FluidThermalSystem(
        slice=ft.FluidSlice(
            slice_id="slab-a",
            side=Quantity(1.0, "meter"),
            angular_rate=Quantity(1.0, "1/s"),
            grid=fluid.Transport2DGrid(n_cells=n_cells),
        ),
        medium=ft.GasDiffusivity(
            medium_id="air-like",
            reference_diffusivity=Quantity(D_REF, "m**2/s"),
            reference_temperature=Quantity(T_REF, "kelvin"),
            temperature_exponent=Quantity(EXPONENT, "dimensionless"),
        ),
        wall=ft.WallCoupling(
            medium_id="air-like",
            volumetric_heat_capacity=Quantity(
                RHO_CP, "joule/(meter**3*kelvin)"
            ),
            depth=Quantity(DEPTH, "meter"),
        ),
        body=ft.HeatedBody(
            body_id="body-a",
            heat_capacity=Quantity(600.0, "joule/kelvin"),
            ambient_temperature=Quantity(T_AMB, "kelvin"),
            initial_temperature=Quantity(T_AMB, "kelvin"),
            duration=Quantity(600.0, "second"),
            heat_input=Quantity(heat_w, "watt"),
            posing_conductance=Quantity(0.1, "watt/kelvin"),
        ),
    )


# =====================================================================
# The composition's records
# =====================================================================

def test_the_composition_is_four_problems_and_four_declared_edges():
    system = make_system()
    problems = ft.coupled_problems(system)
    assert [p.problem_id for p in problems] == [
        system.diffusivity_problem_id,
        system.fluid_problem_id,
        system.wall_problem_id,
        system.thermal_problem_id,
    ]
    dependencies = ft.coupled_dependencies(system)
    assert len(dependencies) == 4
    assert {d.name for d in dependencies} == {
        ftc.DEPENDENCY_EFFLUX,
        ftc.DEPENDENCY_CONDUCTANCE,
        ftc.DEPENDENCY_TEMPERATURE,
        ftc.DEPENDENCY_DIFFUSIVITY,
    }
    plan = ft.nominal_plan(system, dependencies)
    assert plan.check_against(problems) == ()


def test_every_transported_quantity_is_a_scalar_and_carries_its_unit():
    """The whole reason this composition is buildable today."""
    system = make_system()
    dimensions = {d.name: d.dimension for d in ft.coupled_dependencies(system)}
    assert dimensions == {
        ftc.DEPENDENCY_EFFLUX: Quantity(1.0, "m**2/s").dimensionality,
        ftc.DEPENDENCY_CONDUCTANCE: Quantity(1.0, "watt/kelvin").dimensionality,
        ftc.DEPENDENCY_TEMPERATURE: Quantity(1.0, "kelvin").dimensionality,
        ftc.DEPENDENCY_DIFFUSIVITY: Quantity(1.0, "m**2/s").dimensionality,
    }
    # No edge names the fluid's bulk field, and nothing bulk crosses.
    sources = {d.source_quantity for d in ft.coupled_dependencies(system)}
    assert fluid.FIELD_VARIABLE not in sources


def test_the_cycle_has_four_admissible_tears_and_the_readers_rank_none():
    """The plan states a tear; nothing infers one."""
    system = make_system()
    problems = ft.coupled_problems(system)
    ids = [p.problem_id for p in problems]
    dependencies = ft.coupled_dependencies(system)
    assert cpl.execution_order(ids, dependencies) == ()
    assert len(cpl.cycle_edges(ids, dependencies)) == 4
    tears = [
        d
        for d in dependencies
        if cpl.execution_order(ids, [e for e in dependencies if e is not d])
    ]
    assert len(tears) == 4


def test_the_execution_order_is_computed_from_the_records():
    system = make_system()
    problems = ft.coupled_problems(system)
    plan = ft.nominal_plan(system, ft.coupled_dependencies(system))
    order = cpl.execution_order([p.problem_id for p in problems], plan.uncut)
    assert order == (
        system.diffusivity_problem_id,
        system.fluid_problem_id,
        system.wall_problem_id,
        system.thermal_problem_id,
    )


def test_the_seed_is_not_recoverable_from_any_record():
    """ET-VERTICAL §4's finding, unchanged by a second consumer."""
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    plan = ft.nominal_plan(system, ft.coupled_dependencies(system))
    (torn,) = plan.torn
    target = problems[torn.dependency.target_problem_id]
    determined = {c.variable for c in target.initial_conditions}
    determined |= {c.variable for c in target.boundary_conditions}
    assert torn.dependency.target_quantity not in determined
    assert not [
        p for p in target.parameters if p.name == torn.dependency.target_quantity
    ]


# =====================================================================
# N4 — records-only invisibility of a coupled parameter
# =====================================================================

def test_n4_a_records_only_reader_cannot_see_that_diffusivity_has_a_supplier():
    """Preparation finding A1, exhibited on a real composition.

    Both coupled *inputs* of this composition are declared
    ``ScientificParameter``s, which carry values, so they read as resolved even
    though a composition in fact supplies them. ``unresolved_inputs`` therefore
    reports nothing for either — and only the explicit ``QuantityDependency``
    states the truth. This is a measured limitation of the contracts, recorded
    rather than papered over, and it is NOT fixed by this milestone.
    """
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    fluid_problem = problems[system.fluid_problem_id]
    assert unresolved_inputs([fluid_problem]) == ()
    assert any(p.name == "diffusivity" for p in fluid_problem.parameters)

    thermal_problem = problems[system.thermal_problem_id]
    reported = {q for (_, q, _) in unresolved_inputs([thermal_problem])}
    # The thermal problem's coupled input is also a parameter and is also
    # invisible; what IS reported are its two declared CONTROL variables,
    # neither of which this composition supplies.
    assert lump.AMBIENT_CONDUCTANCE not in reported
    assert reported == {lump.HEAT_INPUT, lump.AMBIENT_TEMPERATURE}


# =====================================================================
# N3 — dimensional refusals, before anything solves
# =====================================================================

def test_n3_a_watt_valued_edge_into_the_conductance_endpoint_is_refused():
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    wrong = QuantityDependency(
        source_problem_id=system.wall_problem_id,
        source_quantity=prop.WALL_CONDUCTANCE_METRIC,
        target_problem_id=system.thermal_problem_id,
        target_quantity=lump.AMBIENT_CONDUCTANCE,
        unit_exemplar="watt",
    )
    issues = wrong.check_against(
        target_problem=problems[system.thermal_problem_id]
    )
    assert issues and any(
        i.kind.value == "wrong_dimension" for i in issues
    )


def test_n3_a_kelvin_valued_edge_into_the_diffusivity_endpoint_is_refused():
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    wrong = QuantityDependency(
        source_problem_id=system.thermal_problem_id,
        source_quantity=lump.STEADY_STATE_TEMPERATURE_METRIC,
        target_problem_id=system.fluid_problem_id,
        target_quantity="diffusivity",
        unit_exemplar="kelvin",
    )
    issues = wrong.check_against(target_problem=problems[system.fluid_problem_id])
    assert issues and any(i.kind.value == "wrong_dimension" for i in issues)


def test_n3_the_plan_refuses_a_mis_dimensioned_edge_before_the_first_sweep():
    system = make_system()
    problems = ft.coupled_problems(system)
    good = list(ft.coupled_dependencies(system))
    bad = QuantityDependency(
        source_problem_id=system.fluid_problem_id,
        source_quantity=fluid.PHI_D_METRIC,
        target_problem_id=system.wall_problem_id,
        target_quantity=prop.WALL_EFFLUX,
        unit_exemplar="kelvin",
        name=ftc.DEPENDENCY_EFFLUX,
    )
    good[0] = bad
    plan = ft.nominal_plan(system, good)
    assert plan.check_against(problems)


def test_the_scale_restoration_cannot_be_bypassed_by_wiring_efflux_to_conductance():
    """The contract is what FORCED the wall model to exist as a declared model.

    A m**2/s efflux simply cannot be wired into a watt/kelvin endpoint, so the
    conversion has to live somewhere with a version, a validity domain,
    declared parameters and a provenance binding — not inside coupling code.
    """
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    shortcut = QuantityDependency(
        source_problem_id=system.fluid_problem_id,
        source_quantity=fluid.PHI_D_METRIC,
        target_problem_id=system.thermal_problem_id,
        target_quantity=lump.AMBIENT_CONDUCTANCE,
        unit_exemplar="m**2/s",
    )
    issues = shortcut.check_against(
        target_problem=problems[system.thermal_problem_id]
    )
    assert issues and any(i.kind.value == "wrong_dimension" for i in issues)


# =====================================================================
# N2 — the QuantityDependency field-endpoint leak, recorded not fixed
# =====================================================================

def test_n2_a_field_endpoint_still_checks_clean_and_this_milestone_does_not_fix_it():
    """Preparation finding P6c, pinned on a real composition.

    ``QuantityDependency``'s docstring says ``data_references`` is deliberately
    not consulted, so that a field endpoint returns an honest ``MISSING``
    rather than a clean check implying transfer semantics no contract
    provides. That protection does not hold when a domain declares its field
    as a ``ScientificVariable`` — which ``transport2d`` must, so that
    ``VariableBulkLinkage`` has something to bind to.

    The leak is therefore REPORTED here, not patched: fixing it means changing
    universal core on one consumer's evidence, and creating ``ScientificField``
    is explicitly out of scope. What this milestone can honestly say is that it
    transports no field, which the next test proves structurally.
    """
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    fluid_problem = problems[system.fluid_problem_id]
    field_edge = QuantityDependency(
        source_problem_id=system.fluid_problem_id,
        source_quantity=fluid.FIELD_VARIABLE,
        target_problem_id=system.wall_problem_id,
        target_quantity=prop.WALL_EFFLUX,
        unit_exemplar="dimensionless",
    )
    # It checks CLEAN as a source. That is the leak.
    assert field_edge.check_against(source_problem=fluid_problem) == ()
    # And the field really is a declared variable, which is why.
    assert any(v.name == fluid.FIELD_VARIABLE for v in fluid_problem.variables)


def test_n2_a_field_endpoint_is_refused_by_this_PACK_and_the_guard_is_labelled():
    """A pack-local guard, and it is labelled as one.

    The contract cannot distinguish a scalar endpoint from a field one, so this
    pack distinguishes them the only way it honestly can: by naming, in its own
    declaration, the four edges it transports and refusing anything else. That
    is a *convention of this pack*, not a contract, and it protects this
    composition only. A different pack wiring ``c:field`` somewhere would still
    check clean.
    """
    system = make_system()
    declared = {d.source_quantity for d in ft.coupled_dependencies(system)}
    assert fluid.FIELD_VARIABLE not in declared
    # Every source this pack declares resolves to a SCALAR metric or variable,
    # and none of them is the bulk-bound field variable.
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    bulk_bound = {fluid.FIELD_VARIABLE}
    for dependency in ft.coupled_dependencies(system):
        assert dependency.source_quantity not in bulk_bound
    # The fluid problem names bulk data nowhere on its input side either.
    assert problems[system.fluid_problem_id].data_references == ()


# =====================================================================
# N1 — c:centre is unsuitable, and a future author who wires it breaks this
# =====================================================================

def test_n1_the_exact_centre_value_is_independent_of_the_diffusivity():
    """The half of the falsification that needs no solve.

    ``c*(x,y) = sin(pi x/L) sin(pi y/L)`` is pinned by an analytically derived
    source term, so the exact centre value is 1.0 for EVERY admissible D. A
    coupling closed on ``c:centre`` would therefore be closed on a quantity
    whose true value cannot respond to the fluid's own physical input — every
    volt of apparent sensitivity is discretization error. The executed half of
    this proof is in ``test_ft_coupling_execution.py``.
    """
    exact = {
        D: fluid.exact_centre(side_m=1.0, diffusivity_m2_s=D, omega_per_s=1.0)
        for D in (0.01, 0.02, 0.05, 0.10, 0.50)
    }
    assert all(value == pytest.approx(1.0, abs=1e-12) for value in exact.values())
    spread = max(exact.values()) - min(exact.values())
    assert spread == pytest.approx(0.0, abs=1e-12)


def test_n1_no_coupling_edge_in_this_pack_names_a_centre_max_or_min_metric():
    """The regression a future author trips over.

    This is deliberately phrased over the pack's declared dependencies rather
    than over its source text, so it catches a rewiring however it is written.
    """
    system = make_system()
    forbidden = {fluid.CENTRE_METRIC, fluid.MAX_METRIC, fluid.MIN_METRIC}
    for dependency in ft.coupled_dependencies(system):
        assert dependency.source_quantity not in forbidden, (
            f"{dependency.name!r} transports {dependency.source_quantity!r}, "
            f"whose exact value is independent of the fluid's own input: a "
            f"loop closed on it transports discretization error only. See "
            f"docs/fluid-thermal-preparation.md §FT0/P1."
        )
        assert dependency.target_quantity not in forbidden


# =====================================================================
# The independent closed-form coupled reference
# =====================================================================

def test_the_reference_module_imports_nothing_from_the_numerical_path():
    """Falsifier attack 7, closed by parsing rather than by assertion."""
    source = (
        REPO_ROOT / "src/engcore/systems/fluidthermal/reference.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or f"{'.' * node.level}<relative>")
    assert imported == {"__future__", "math"}, imported
    # Nothing an import could have brought in is referenced by name either.
    referenced = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    } | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }
    for forbidden in (
        "solve_transport2d", "run_fixed_point", "Quantity", "Transport2DDomain",
        "DiffusivityPropertySolver", "WallConductanceSolver",
        "LumpedThermalSolver", "build_transport2d_problem",
    ):
        assert forbidden not in referenced, forbidden


def test_the_reference_agrees_with_its_own_independent_algebraic_identity():
    """A second statement of the root, sharing no code path with the first."""
    for heat_w in (6.0, 40.0):
        root = ft.coupled_fixed_point(heat_w=heat_w, **REFERENCE_CONSTANTS)
        residual = ft.fixed_point_identity_residual(
            root,
            heat_w=heat_w,
            reference_diffusivity=D_REF,
            reference_temperature_k=T_REF,
            exponent=EXPONENT,
            volumetric_heat_capacity=RHO_CP,
            depth_m=DEPTH,
        )
        assert abs(residual) <= 1e-12


def test_the_preregistered_closed_form_values():
    """§5.3 of the preregistration, to the digits it committed."""
    assert ft.coupled_fixed_point(heat_w=6.0, **REFERENCE_CONSTANTS) == pytest.approx(
        348.163813, abs=1e-6
    )
    assert ft.coupled_fixed_point(heat_w=40.0, **REFERENCE_CONSTANTS) == pytest.approx(
        481.835346, abs=1e-6
    )
    assert ft.picard_gain(348.163813, ambient_k=T_AMB, exponent=EXPONENT) == (
        pytest.approx(-0.2421, abs=1e-4)
    )
    assert ft.picard_gain(481.835346, ambient_k=T_AMB, exponent=EXPONENT) == (
        pytest.approx(-0.6604, abs=1e-4)
    )


def test_the_reference_refuses_an_unbracketed_or_impossible_declaration():
    with pytest.raises(ValueError):
        ft.coupled_fixed_point(heat_w=-1.0, **REFERENCE_CONSTANTS)
    with pytest.raises(ValueError):
        ft.coupled_residual(0.0, heat_w=6.0, **REFERENCE_CONSTANTS)


# =====================================================================
# The two property claims
# =====================================================================

def test_the_property_models_bind_cleanly_to_the_problems_they_are_posed_on():
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    assert prop.POWER_LAW_DIFFUSIVITY_MODEL.check_against(
        problems[system.diffusivity_problem_id]
    ).issues == ()
    assert prop.WALL_CONDUCTANCE_MODEL.check_against(
        problems[system.wall_problem_id]
    ).issues == ()


def test_the_supplied_states_are_declared_state_variables_carrying_no_value():
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    for problem_id, name in (
        (system.diffusivity_problem_id, prop.TEMPERATURE),
        (system.wall_problem_id, prop.WALL_EFFLUX),
    ):
        problem = problems[problem_id]
        (variable,) = [v for v in problem.variables if v.name == name]
        assert variable.role is VariableRole.STATE
        assert not [p for p in problem.parameters if p.name == name]


def test_the_wall_model_refuses_a_non_positive_efflux():
    """An influx is not a conductance, and a negative hA is a runaway.

    The refusal is the model's own declared ``ValidityDomain``, checked in
    ``prepare`` — not a hand-written guard in coupling code.
    """
    system = make_system()
    problem = prop.build_wall_conductance_problem(
        system.wall, problem_id=system.wall_problem_id
    )
    solver = prop.WallConductanceSolver()
    solver.bind_medium(
        system.wall, problem.problem_id, wall_efflux=Quantity(-1.0, "m**2/s")
    )
    with pytest.raises(InvalidScientificProblem, match="validity"):
        solver.prepare(problem)


def test_the_diffusivity_model_reports_a_temperature_outside_its_declared_band():
    system = make_system()
    problem = prop.build_diffusivity_problem(
        system.medium, problem_id=system.diffusivity_problem_id
    )
    inside = prop.assess_diffusivity_validity(problem, Quantity(400.0, "kelvin"))
    outside = prop.assess_diffusivity_validity(problem, Quantity(50.0, "kelvin"))
    assert inside.violated == ()
    assert prop.TEMPERATURE in outside.violated


def test_no_property_hierarchy_was_minted():
    """The sibling electrical property module's argument, re-checked here."""
    source = (
        REPO_ROOT / "src/engcore/systems/fluidthermal/properties.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    assert classes == {
        "GasDiffusivity",
        "WallCoupling",
        "PreparedDiffusivityEvaluation",
        "PreparedConductanceEvaluation",
        "DiffusivityPropertySolver",
        "WallConductanceSolver",
    }
    for forbidden in (
        "MaterialProperty", "PropertyModel", "PropertyRequirement",
        "PropertyBinding", "ConstitutiveRelation",
    ):
        assert forbidden not in source


# =====================================================================
# The fluid domain's new reduction, as a record
# =====================================================================

def test_the_efflux_metric_is_declared_with_its_own_unit_not_the_field_unit():
    system = make_system()
    problem = ft.coupled_problems(system)[1]
    (variable,) = [v for v in problem.variables if v.name == fluid.PHI_D_METRIC]
    assert Quantity(1.0, variable.unit).dimensionality == (
        Quantity(1.0, fluid.EFFLUX_UNIT).dimensionality
    )
    assert Quantity(1.0, variable.unit).dimensionality != (
        Quantity(1.0, fluid.FIELD_UNIT).dimensionality
    )
    assert variable.role is VariableRole.OBSERVABLE
    assert fluid.METRIC_UNITS[fluid.PHI_D_METRIC] == "m**2/s"


def test_the_efflux_sign_convention_is_a_record_and_not_a_comment():
    orientations = fluid.wall_efflux_orientations()
    assert {o.boundary_name for o in orientations} == set(fluid.ALL_SIDES)
    for orientation in orientations:
        assert orientation.sign is OrientationSign.POSITIVE
        assert orientation.reference == fluid.EFFLUX_REFERENCE
    # And the problem declares that the check must have passed before a result
    # is admitted.
    system = make_system()
    problem = ft.coupled_problems(system)[1]
    assert "wall_efflux_orientation" in problem.validation_requirements


def test_the_model_version_moved_because_the_model_now_states_a_second_output():
    assert fluid.TRANSPORT2D_MODEL.version == "0.2.0"
    assert "phi_D" in {spec.metric for spec in fluid.TRANSPORT2D_MODEL.outputs}


# =====================================================================
# Architecture guards — the preregistered ceiling
# =====================================================================

def _diff(path: str) -> str:
    return subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", path],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_universal_core_was_not_touched_by_this_milestone():
    """§9's hard ceiling. Zero files changed under ``src/engcore/scientific``."""
    base = "6caa11395b1033802ab101b2c024857bff0ae305"
    changed = subprocess.run(
        ["git", "diff", "--name-only", base, "--", "src/engcore/scientific/"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert changed == "", changed
    assert _diff("src/engcore/scientific/") == ""


#: The commit at which `ET-VERTICAL` minted the coupling machinery inside the
#: electro-thermal pack, and the file it minted it in. `COUPLING-PACK-RELOCATION`
#: moved that code to ``src/engcore/coupling/``; this pair is what the move is
#: measured against.
_MINTED_AT = "6caa11395b1033802ab101b2c024857bff0ae305"
_MINTED_IN = "src/engcore/systems/electrothermal/coupled.py"

#: Every object `FT-SCALAR-COUPLING` executes against, directly or transitively.
_RELOCATED = (
    "is_ratio_scale", "shares_origin", "_require_ratio_scale", "edge_key",
    "CouplingOutcome", "TornEndpoint", "FixedPointCouplingPlan", "_edges",
    "execution_order", "cycle_edges", "CoupledIteration", "CoupledRun",
    "run_fixed_point",
)


#: The ONE executable edit `COUPLING-PACK-RELOCATION` had to make, named here
#: rather than hidden by a general normalizer. ``FixedPointCouplingPlan.
#: unsupplied`` imports ``externally_imposed`` by a *relative* path, and the
#: code moved one package level closer to ``engcore.scientific`` — so the dots
#: had to change or the import would resolve to nothing. It changes no value,
#: no branch and no target: both spellings name
#: ``engcore.scientific.composition.externally_imposed``.
_RELATIVE_IMPORT_REPAIR = ("from ...scientific.", "from ..scientific.")

#: …and it was needed by exactly one relocated object.
_NEEDED_THE_REPAIR = {"FixedPointCouplingPlan"}


def _executable_source(module_source: str, name: str) -> str:
    """The named top-level object's source with every string constant blanked.

    Docstrings explain a rule; they are not the rule. Blanking them is what
    lets a byte-identity claim survive a docstring that was rewritten to stop
    narrating one domain's physics, while still failing on any change to a
    single executable token.
    """
    tree = ast.parse(module_source)
    node = next(
        n for n in tree.body
        if getattr(n, "name", None) == name
        and isinstance(n, (ast.FunctionDef, ast.ClassDef))
    )
    for inner in ast.walk(node):
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
            inner.value = ""
    return ast.unparse(node)


def test_the_coupling_machinery_was_relocated_and_not_edited():
    """PR1, the preregistered promotion test, restated for a moved owner.

    The original form asserted ``git diff --name-only <base> --
    src/engcore/systems/electrothermal/`` was empty, which measured "the
    machinery was not edited to fit the second consumer" only for as long as
    the machinery stayed in that directory. `COUPLING-PACK-RELOCATION` moved
    it, so that form can no longer hold — and it is replaced by a **stronger**
    one rather than deleted: every relocated object's *executable* source must
    be byte-identical to the blob `ET-VERTICAL` committed, read straight out of
    git. Docstrings and the module's location are free to change; not one
    executable token is.

    If this ever fails, the promotion test has failed and the correct output is
    that finding — not an edit that makes a consumer fit.
    """
    minted = subprocess.run(
        ["git", "show", f"{_MINTED_AT}:{_MINTED_IN}"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    package = REPO_ROOT / "src/engcore/coupling"
    now = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(package.glob("*.py"))
    )
    repaired = set()
    for name in _RELOCATED:
        was, now_src = _executable_source(minted, name), _executable_source(now, name)
        if was != now_src:
            # Apply the one named repair, and only it — then demand equality.
            was = was.replace(*_RELATIVE_IMPORT_REPAIR)
            repaired.add(name)
        assert was == now_src, name
    # …and prove the repair was needed exactly where the milestone said, so a
    # future edit cannot hide behind it.
    assert repaired == _NEEDED_THE_REPAIR, sorted(repaired)


def test_the_relocated_machinery_left_no_copy_behind():
    """A move, not a fork. No pack may still define a relocated object."""
    for pack in ("electrothermal", "fluidthermal"):
        for path in sorted(
            (REPO_ROOT / "src/engcore/systems" / pack).glob("*.py")
        ):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            defined = {
                n.name for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.ClassDef))
            } | {
                t.id for n in tree.body if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)
            }
            clashes = sorted(defined & set(_RELOCATED))
            assert not clashes, f"{path.name} redefines {clashes}"


def test_the_loop_this_pack_uses_is_the_shared_generic_one_by_identity():
    """Not a copy, not a subclass, not a re-implementation — for BOTH packs."""
    from engcore.systems.electrothermal import coupled as etc

    for pack in (ftc, etc):
        assert pack.run_fixed_point is cpl.run_fixed_point
        assert pack.FixedPointCouplingPlan is cpl.FixedPointCouplingPlan
        assert pack.TornEndpoint is cpl.TornEndpoint
        assert pack.CoupledRun is cpl.CoupledRun


def test_neither_pack_republishes_a_generic_coupling_name():
    """The false ownership is gone, not renamed.

    A domain-named pack publishing a domain-neutral record is exactly what
    `COUPLING-PACK-RELOCATION` removed. Importing one for a module's own use is
    ordinary Python; re-exporting it is a second owner.
    """
    from engcore.systems import electrothermal as et_pack
    from engcore.systems import fluidthermal as ft_pack
    from engcore.systems.electrothermal import coupled as etc

    generic = set(cpl.__all__) | set(_RELOCATED)
    for module in (et_pack, ft_pack, etc, ftc):
        published = set(getattr(module, "__all__", ()))
        assert not published & generic, (module.__name__, sorted(published & generic))


def test_the_loop_still_cannot_name_either_science():
    """PR2. The generic loop gained no fluid or thermal branch."""
    source = (
        REPO_ROOT / "src/engcore/coupling/execution.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    body = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "run_fixed_point"
    )
    # Over the EXECUTABLE body only: the docstring legitimately discusses the
    # first consumer by name, and a scan that could not tell prose from code
    # would be measuring the comments rather than the loop.
    statements = [
        n
        for n in body.body
        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    ]
    text = "\n".join(
        (ast.get_source_segment(source, n) or "") for n in statements
    )
    stripped = "\n".join(
        line.split("#", 1)[0] for line in text.splitlines()
    )
    for forbidden in (
        "fluid", "transport2d", "diffusivity", "efflux", "phi_D",
        "thermal", "temperature", "conductance", "resistance", "circuit",
        "electrical", "kinetics", "cstr",
    ):
        assert forbidden not in stripped, forbidden


def test_this_pack_declares_no_new_schema_string():
    """No new universal record, no schema version moved by this pack."""
    for module in ("coupled.py", "properties.py", "reference.py", "__init__.py"):
        source = (
            REPO_ROOT / "src/engcore/systems/fluidthermal" / module
        ).read_text(encoding="utf-8")
        assert "schema_string(" not in source
        assert "require_schema(" not in source
