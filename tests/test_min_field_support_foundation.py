"""MIN-FIELD-SUPPORT-FOUNDATION — zero-contract attempts, the two new
primitives, real-consumer proof (Fluid + Thermal-typed), the mandatory
negative tests, DATA-BOUNDARY0 preservation, and a fresh-process proof.

See docs/min-field-support-foundation-prereg.md (preregistration) and
docs/min-field-support-foundation-evidence.md (written after execution).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from engcore.domains.fluids.transport2d import (
    ALL_SIDES,
    Transport2DDomain,
    Transport2DGrid,
    boundary_orientation_report,
    build_transport2d_problem,
    classify_boundary_orientation,
    solve_transport2d,
)
from engcore.domains.thermal.conduction1d import (
    THERMAL_CONDUCTION_1D,
    ConductionSlab,
    SlabDiscretization,
    exact_field,
)
from engcore.scientific.errors import InvalidScientificProblem
from engcore.scientific.ir.conditions import BoundaryCondition, BoundaryKind
from engcore.scientific.ir.orientation import (
    BoundaryOrientation,
    MixedOrientationError,
    OrientationSign,
    classify_sign,
)
from engcore.scientific.ir.problem import PROBLEM_SCHEMA, ScientificProblem
from engcore.scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from engcore.scientific.ir.conditions import InitialCondition
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.variable_binding import VariableBulkLinkage
from engcore.scientific.units.quantity import Quantity

REPO_ROOT = Path(__file__).resolve().parent.parent


# =====================================================================
# A — zero-new-contract attempts (prereg §3), executed for real
# =====================================================================

def test_a1_physical_support_cannot_state_shape_or_orientation():
    """A1: ScientificParameter('side', ...) states an extent, not a shape,
    boundary set or orientation. Reconfirmed on the real Fluid domain."""
    domain = Transport2DDomain(
        domain_id="a1",
        side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"),
        grid=Transport2DGrid(n_cells=8),
    )
    problem = build_transport2d_problem(domain)
    side_param = problem.parameter("side")
    # The parameter states a length, nothing else — no field on
    # ScientificParameter/ScientificValue can carry "the unit square" as a
    # shape, and this is what makes that concrete.
    assert side_param.value == Quantity(1.0, "meter")
    assert not hasattr(side_param, "boundary_set")
    assert not hasattr(side_param, "orientation")


def test_a2_reversing_velocity_leaves_boundary_conditions_byte_identical():
    """A2: R1a, reconfirmed on the real Fluid domain (not the probe)."""
    domain_pos = Transport2DDomain(
        domain_id="a2", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=8),
    )
    domain_neg = Transport2DDomain(
        domain_id="a2", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(-1.0, "1/s"), grid=Transport2DGrid(n_cells=8),
    )
    problem_pos = build_transport2d_problem(domain_pos)
    problem_neg = build_transport2d_problem(domain_neg)
    assert problem_pos.boundary_conditions == problem_neg.boundary_conditions


def test_a3_mesh_dependent_criterion_routes_through_validity_context():
    """A3: ENCODING_C, wired into real Fluid production code (solver.py).
    No core change was needed for this — existing contracts."""
    # Same physical system (same domain_id, side, diffusivity, angular_rate),
    # two grids — the ENCODING_C claim is specifically that the PHYSICAL
    # identity (fingerprint) stays the same while the mesh-dependent
    # criterion, evaluated per-run, correctly differs.
    coarse = Transport2DDomain(
        domain_id="a3-shared", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=8),
    )
    fine = Transport2DDomain(
        domain_id="a3-shared", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=64),
    )
    assert coarse.fingerprint() == fine.fingerprint()

    coarse_result = solve_transport2d(coarse, run_id="a3-coarse-run")
    fine_result = solve_transport2d(fine, run_id="a3-fine-run")
    coarse_assessment = coarse_result.provenance.metadata["mesh_validity_assessment"]
    fine_assessment = fine_result.provenance.metadata["mesh_validity_assessment"]
    assert coarse_assessment["status"] == "outside_validated_domain"
    assert "inverse_peclet_cell" in coarse_assessment["violated"]
    assert fine_assessment["status"] == "in_domain"
    assert "inverse_peclet_cell" in fine_assessment["satisfied"]
    # The physical problem identity (excluding grid, exactly like
    # Transport2DDomain.fingerprint()) is unaffected by which grid solved
    # it — mesh dependence lives only in provenance (run-scoped), never in
    # problem identity.
    coarse_problem = build_transport2d_problem(coarse, problem_id="a3-shared-problem")
    fine_problem = build_transport2d_problem(fine, problem_id="a3-shared-problem")
    coarse_metadata = dict(coarse_problem.metadata)
    fine_metadata = dict(fine_problem.metadata)
    assert coarse_metadata.pop("domain_fingerprint") == fine_metadata.pop(
        "domain_fingerprint"
    )
    for key in ("n_cells", "work_proxy"):
        assert coarse_metadata.pop(key) != fine_metadata.pop(key)
    assert coarse_metadata == fine_metadata
    assert coarse_problem.variables == fine_problem.variables
    assert coarse_problem.boundary_conditions == fine_problem.boundary_conditions
    assert coarse_problem.parameters == fine_problem.parameters


def test_a4_non_uniform_field_cannot_fit_one_quantity():
    """A4: InitialCondition.value is one Quantity; sin(pi x/L) cannot be one
    number. This is a real, existing residue on the real Thermal domain —
    reconfirmed, not invented, here."""
    with pytest.raises(InvalidScientificProblem):
        InitialCondition(variable="u:field", value="sin(pi x / L)")  # not a Quantity


def test_a5_string_encoded_formula_is_meaning_in_key():
    """A5: ScientificParameter carrying the formula as a string is
    constructible but not a records-only-readable scientific fact — a
    records-only reader would have to parse and interpret it, exactly the
    EXEC-SPEC-STRUCTURED "meaning-in-key" failure mode."""
    from engcore.scientific.ir.values import CategoricalValue

    param = ScientificParameter(
        name="initial_condition_formula",
        value=CategoricalValue("sin(pi x / L)", ("sin(pi x / L)", "other")),
    )
    # It is representable; it is not machine-actionable. A reader cannot
    # evaluate this string to recover bulk values without domain-specific
    # code — no test asserts otherwise here, this documents the limitation.
    assert param.value.value == "sin(pi x / L)"


def test_a6_problem_had_no_bulk_input_channel_before_this_milestone():
    """A6, negative half: before MIN-FIELD-SUPPORT-FOUNDATION,
    ScientificProblem had no data_references field at all. This is recorded
    from the schema version itself: /1 payloads (pre-milestone) load with
    data_references == () BY VERSION, not by key presence."""
    v1_payload = {
        "schema": "scientific_problem/1",
        "problem_id": "legacy",
        "name": "", "description": "", "variables": [], "parameters": [],
        "objectives": [], "constraints": [], "initial_conditions": [],
        "boundary_conditions": [], "models": [], "required_capabilities": [],
        "uncertainty": None, "validation_requirements": [], "metadata": {},
    }
    problem = ScientificProblem.from_dict(v1_payload)
    assert problem.data_references == ()
    assert problem.to_dict()["schema"] == PROBLEM_SCHEMA == "scientific_problem/2"


# =====================================================================
# B — support: reconfirm no new type is forced (H1)
# =====================================================================

def test_b1_cstr_needs_no_spatial_support_at_all():
    """0D negative check: kinetics/cstr (a 0D, well-stirred reactor with no
    spatial extent) must not be forced to declare spatial structure it does
    not have. Verified by inspection: this milestone touched neither
    kinetics/cstr nor electrical/dc, and neither module's source references
    any of the concepts this milestone added."""
    forbidden = ("boundaryorientation", "classify_sign", "data_references")
    for package in ("kinetics/cstr", "electrical/dc"):
        root = REPO_ROOT / "src" / "engcore" / "domains" / package
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for token in forbidden:
                assert token.lower() not in text, (path, token)


def test_b2_thermal_and_fluid_both_use_a_bare_scalar_extent():
    """Both real spatial domains state their extent as one ScientificParameter
    Quantity; neither needed a Support/Field/Mesh type to run."""
    slab = ConductionSlab(
        slab_id="b2", length=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"), end_time=Quantity(0.2, "second"),
        discretization=SlabDiscretization(n_cells=20, n_steps=50),
    )
    domain = Transport2DDomain(
        domain_id="b2", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=8),
    )
    assert isinstance(slab.length, Quantity)
    assert isinstance(domain.side, Quantity)
    # Neither carries a shape/topology field — the ledger-2 residue this
    # milestone measured and, per its own forcing thresholds, did not close.


# =====================================================================
# C — boundary orientation (H2): real Fluid production use + mandatory
# negative test
# =====================================================================

def test_c1_every_side_of_the_real_benchmark_refuses_single_orientation():
    """MANDATORY NEGATIVE TEST. Every side of the real Fluid domain's
    rotational velocity field is half inflow, half outflow — a
    representation that can only assign one sign to the whole region MUST
    refuse, not silently pick a side."""
    domain = Transport2DDomain(
        domain_id="c1", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=16),
    )
    for side in ALL_SIDES:
        with pytest.raises(MixedOrientationError):
            classify_boundary_orientation(domain, side)
    report = boundary_orientation_report(domain)
    assert all(outcome.startswith("refused:") for outcome in report.values())


def test_c2_single_signed_boundary_is_correctly_classified():
    """Positive case: a boundary whose samples genuinely agree in sign is
    classified, not refused — this is not a blanket refusal mechanism."""
    inflow_samples = (-2.0, -1.5, -0.3, -0.1)
    outflow_samples = (0.1, 0.4, 1.2, 3.0)
    assert classify_sign(inflow_samples) is OrientationSign.NEGATIVE
    assert classify_sign(outflow_samples) is OrientationSign.POSITIVE

    orientation = BoundaryOrientation(
        boundary_name="inlet", reference="outward_normal",
        sign=OrientationSign.NEGATIVE,
    )
    assert orientation.check_against(inflow_samples) == ()
    assert orientation.check_against(outflow_samples) != ()


def test_c3_reversal_flips_the_real_per_point_signature():
    """The prereg's required positive-case reversal check. u.n at a fixed
    sample point on a real side flips sign when the rotation reverses, even
    though a single side's aggregate stays mixed either way."""
    from engcore.domains.fluids.transport2d import side_orientation

    forward = side_orientation(
        "side-south", n_cells=16, side_m=1.0, omega_per_s=1.0
    )
    backward = side_orientation(
        "side-south", n_cells=16, side_m=1.0, omega_per_s=-1.0
    )
    assert forward.normal_components != backward.normal_components
    assert all(
        f == -b for f, b in zip(forward.normal_components, backward.normal_components)
    )


def test_c4_removing_boundary_orientation_produces_an_observable_refusal():
    """Step 12: changing/removing the record creates an observable refusal,
    not a silent behavior change. Here 'removing' means what it means for a
    non-spatial consumer: a single fixed sign claimed for a genuinely mixed
    set of samples must be caught, not accepted."""
    orientation = BoundaryOrientation(
        boundary_name="side-south", reference="outward_normal",
        sign=OrientationSign.POSITIVE,
    )
    domain = Transport2DDomain(
        domain_id="c4", side=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        angular_rate=Quantity(1.0, "1/s"), grid=Transport2DGrid(n_cells=16),
    )
    from engcore.domains.fluids.transport2d import side_orientation

    samples = side_orientation(
        "side-south", n_cells=16, side_m=1.0, omega_per_s=1.0
    ).normal_components
    issues = orientation.check_against(samples)
    assert issues, "a mixed-sign region must produce an observable issue"
    assert "disagree in sign" in issues[0]


def test_c5_boundary_orientation_round_trips():
    orientation = BoundaryOrientation(
        boundary_name="side-south", reference="outward_normal",
        sign=OrientationSign.NEGATIVE, description="test",
    )
    payload = orientation.to_dict()
    assert payload["schema"] == "boundary_orientation/1"
    assert BoundaryOrientation.from_dict(payload) == orientation


def test_c6_empty_samples_refuse_rather_than_default():
    with pytest.raises(InvalidScientificProblem):
        classify_sign(())


def test_c7_lumped_two_terminal_case_is_single_signed_and_never_refuses():
    """Universality corroboration: a lumped, non-spatial consumer (one
    signed current/flow value, no continuum boundary at all) is exactly the
    n=1 case classify_sign handles without any special-casing."""
    assert classify_sign((3.5,)) is OrientationSign.POSITIVE
    assert classify_sign((-3.5,)) is OrientationSign.NEGATIVE


def test_c8_result_side_reference_shadows_a_same_named_problem_side_one():
    """Documents check_against's precedence as a tested rule, not an
    accident of code order (architecture-decision-reviewer, required
    change 3): when a result and a problem both carry a data_references
    entry with the SAME name but different content, the result-side one is
    resolved first and its dimension is what a linkage is checked against."""
    problem_ref, _ = ScientificDataReference.for_values(
        "shared:name", [1.0, 2.0, 3.0], unit="meter"
    )
    result_ref, _ = ScientificDataReference.for_values(
        "shared:name", [9.0, 9.0], unit="volt"
    )
    variable = ScientificVariable(
        name="v", unit="volt", role=VariableRole.OBSERVABLE
    )
    problem = ScientificProblem(
        problem_id="c8", variables=(variable,), data_references=(problem_ref,)
    )

    class _FakeResult:
        result_id = "c8-result"
        data_references = (result_ref,)

    linkage = VariableBulkLinkage(
        variable_name="v", reference_name="shared:name"
    )
    # Resolved against the RESULT's reference (volt, matching the variable)
    # even though a problem-side reference of the same name also exists
    # (meter, which would NOT have matched) — proving the precedence
    # concretely rather than leaving it implicit.
    issues = linkage.check_against(problem=problem, result=_FakeResult())
    assert issues == ()


# =====================================================================
# D — non-uniform conditions (H3): real Thermal-typed second consumer
# =====================================================================

def _thermal_nonuniform_ic_problem():
    """A genuine non-uniform initial condition, using REAL production
    thermal/conduction1d types and its REAL closed-form reference function
    (reference.exact_field) — composed here, not by editing
    thermal/conduction1d/problem.py (which several other suites, including a
    holdout declaration, depend on byte-for-byte)."""
    slab = ConductionSlab(
        slab_id="d1", length=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.02, "m**2/s"), end_time=Quantity(0.1, "second"),
        discretization=SlabDiscretization(n_cells=20, n_steps=10),
    )
    n_nodes = slab.discretization.n_cells + 1
    x_nodes = np.linspace(0.0, slab.length_m, n_nodes)
    ic_values = exact_field(
        x_nodes, length_m=slab.length_m, alpha_m2_s=slab.alpha_m2_s, time_s=0.0
    )
    # sin(pi x/L) at t=0: exact by construction, not an approximation of one.
    assert ic_values[0] == pytest.approx(0.0, abs=1e-12)
    assert ic_values[-1] == pytest.approx(0.0, abs=1e-12)
    midpoint_value = float(ic_values[n_nodes // 2])
    assert midpoint_value == pytest.approx(1.0, abs=1e-9)

    field_variable = ScientificVariable(
        name="u:field", unit="dimensionless", role=VariableRole.STATE,
        description="Normalized field over the slab, non-uniform initial state",
    )
    field_reference, _ = ScientificDataReference.for_values(
        "u:field:initial", ic_values.tolist(), unit="dimensionless"
    )
    representative_ic = InitialCondition(
        variable="u:field",
        value=Quantity(midpoint_value, "dimensionless"),
        description=(
            "Representative sample (the slab midpoint, x=L/2) of the true "
            "non-uniform field sin(pi x/L); the full field lives in "
            "data_references, bound by VariableBulkLinkage below"
        ),
    )
    problem = ScientificProblem(
        problem_id="thermal-conduction1d-nonuniform-ic-d1",
        variables=(field_variable,),
        initial_conditions=(representative_ic,),
        data_references=(field_reference,),
        required_capabilities=frozenset({THERMAL_CONDUCTION_1D.name}),
    )
    linkage = VariableBulkLinkage(
        variable_name="u:field", reference_name="u:field:initial"
    )
    return slab, x_nodes, ic_values, problem, linkage


def test_d1_non_uniform_initial_condition_resolves_through_the_linkage():
    slab, x_nodes, ic_values, problem, linkage = _thermal_nonuniform_ic_problem()
    issues = linkage.check_against(problem=problem)
    assert issues == ()
    assert problem.is_time_dependent is True


def test_d2_removing_the_data_reference_produces_an_observable_refusal():
    """Step 12: removing the new record creates an observable ambiguity —
    not a silent behavior change."""
    slab, x_nodes, ic_values, problem, linkage = _thermal_nonuniform_ic_problem()
    stripped = ScientificProblem(
        problem_id=problem.problem_id,
        variables=problem.variables,
        initial_conditions=problem.initial_conditions,
        data_references=(),  # removed
        required_capabilities=problem.required_capabilities,
    )
    issues = linkage.check_against(problem=stripped)
    assert len(issues) == 1
    assert "no data reference named" in issues[0].detail


def test_d3_control_record_stays_o1_against_a_161_value_field():
    """DATA-BOUNDARY0 preservation: the problem's serialized record does not
    scale with the field size it names."""
    slab, x_nodes, ic_values, problem, linkage = _thermal_nonuniform_ic_problem()
    payload = json.loads(json.dumps(problem.to_dict()))

    def largest_sequence(node) -> int:
        if isinstance(node, list):
            return max([len(node)] + [largest_sequence(c) for c in node], default=0)
        if isinstance(node, dict):
            values = [largest_sequence(c) for c in node.values()]
            return max(values) if values else 0
        return 0

    assert len(ic_values) == 21
    assert largest_sequence(payload) < 20


def test_d4_non_uniform_condition_is_not_smuggled_bulk_with_no_meaning():
    """Attack 5 (falsifier, preregistered): the reference is not an
    arbitrary blob — VariableBulkLinkage names WHICH declared variable it
    instantiates, and the values are the field's own manufactured solution,
    checked against thermal/conduction1d's own reference function."""
    slab, x_nodes, ic_values, problem, linkage = _thermal_nonuniform_ic_problem()
    reference = problem.data_reference("u:field:initial")
    assert reference.count == len(ic_values)
    assert linkage.variable_name in {v.name for v in problem.variables}
    # A mismatched-dimension linkage is refused, not silently accepted.
    bad_linkage = VariableBulkLinkage(
        variable_name="does-not-exist", reference_name="u:field:initial"
    )
    issues = bad_linkage.check_against(problem=problem)
    assert len(issues) == 1
    assert "declares no variable named" in issues[0].detail


# =====================================================================
# E — coordinate / flattening classification (H5): not solved, not
# absorbed. Re-confirmed rather than newly discovered.
# =====================================================================

def test_e1_data_reference_still_carries_no_shape_or_flattening():
    """H5: VariableBulkLinkage and ScientificDataReference remain silent on
    layout — this milestone did not add a flattening field to either,
    consistent with classifying it as data-layout, not scientific,
    semantics."""
    ref_fields = set(ScientificDataReference.__dataclass_fields__)
    assert "shape" not in ref_fields
    assert "stride" not in ref_fields
    assert "flattening" not in ref_fields
    linkage_fields = set(VariableBulkLinkage.__dataclass_fields__)
    assert linkage_fields == {"variable_name", "reference_name", "description"}


# =====================================================================
# F — validity routing (H4): already demonstrated in section A3 above with
# real production Fluid code; this section adds the reduction check.
# =====================================================================

def test_f1_no_new_record_was_needed_for_validity_routing():
    """H4 reduction check: ProvenanceRecord + validity_context(extra=...)
    are pre-existing contracts; no import of a new type is required to
    reproduce the A3 result."""
    import inspect

    from engcore.domains.fluids.transport2d import solver as fluid_solver

    source = inspect.getsource(fluid_solver)
    assert "validity_context" in source
    assert "TRANSPORT2D_MODELS[0].validity.assess" in source


# =====================================================================
# G — fresh-process proof
# =====================================================================

_FRESH_PROCESS_SCRIPT = r"""
import json, sys
from engcore.domains.thermal.conduction1d import exact_field
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.orientation import BoundaryOrientation, classify_sign
from engcore.scientific.results.variable_binding import VariableBulkLinkage

payload = json.loads(sys.stdin.read())
problem = ScientificProblem.from_dict(payload["problem"])
linkage = VariableBulkLinkage.from_dict(payload["linkage"])
issues = linkage.check_against(problem=problem)
reference = problem.data_reference(linkage.reference_name)

orientation = BoundaryOrientation.from_dict(payload["orientation"])

print(json.dumps({
    "issues": len(issues),
    "reference_count": reference.count,
    "reference_digest": reference.digest,
    "orientation_sign": orientation.sign.value,
    "modules_loaded": [m for m in sys.modules if "domains.fluids" in m],
}))
"""


def test_g1_fresh_process_reconstructs_and_reports_no_issues():
    """No original Python object identity, no hidden registry, no arbitrary
    code in the payload — a genuinely separate interpreter reconstructs the
    non-uniform-condition problem and the orientation record from JSON
    alone and reports the same facts."""
    slab, x_nodes, ic_values, problem, linkage = _thermal_nonuniform_ic_problem()
    orientation = BoundaryOrientation(
        boundary_name="side-south", reference="outward_normal",
        sign=OrientationSign.POSITIVE,
    )
    payload = json.dumps(
        {
            "problem": problem.to_dict(),
            "linkage": linkage.to_dict(),
            "orientation": orientation.to_dict(),
        }
    )
    proc = subprocess.run(
        [sys.executable, "-c", _FRESH_PROCESS_SCRIPT],
        input=payload, capture_output=True, text=True, cwd=str(REPO_ROOT),
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["issues"] == 0
    assert result["reference_count"] == len(ic_values)
    assert result["reference_digest"] == problem.data_reference("u:field:initial").digest
    assert result["orientation_sign"] == "positive"
    # The child process never imported the Fluid domain at all — the
    # reconstruction path used only universal core records.
    assert result["modules_loaded"] == []


# =====================================================================
# H — no schema/serialization impact beyond the documented additive bump
# =====================================================================

def test_h1_untouched_schema_strings_did_not_move():
    from engcore.scientific.ir.conditions import (
        BOUNDARY_CONDITION_SCHEMA,
        INITIAL_CONDITION_SCHEMA,
    )
    from engcore.scientific.results.data_reference import DATA_REFERENCE_SCHEMA

    assert BOUNDARY_CONDITION_SCHEMA == "boundary_condition/1"
    assert INITIAL_CONDITION_SCHEMA == "initial_condition/1"
    assert DATA_REFERENCE_SCHEMA == "scientific_data_reference/1"


def test_h2_problem_v1_and_v2_payloads_both_load():
    problem = ScientificProblem(problem_id="h2")
    v2 = problem.to_dict()
    assert v2["schema"] == "scientific_problem/2"
    v1 = dict(v2)
    v1["schema"] = "scientific_problem/1"
    del v1["data_references"]
    reconstructed_v1 = ScientificProblem.from_dict(v1)
    assert reconstructed_v1.data_references == ()
    reconstructed_v2 = ScientificProblem.from_dict(v2)
    assert reconstructed_v2 == problem
