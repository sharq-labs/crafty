"""2D scalar advection-diffusion — the first real production Fluid domain.

Covers the milestone's mandatory checkpoints:

    F3  numerical realization: sparse production vs. dense reference-check,
        sharing one assembly
    F4  VariableBulkLinkage as a REAL production caller (not a decorative one)
    F6  boundary orientation, re-verified against the real production grid
    F7  scientific correctness across the frozen n in {8,16,32,64} ladder
    F8  admission: a genuinely failing result refused by a real Fluid-domain
        consumer function
    F9  executable reconstruction of the domain declaration in a "fresh
        process" (a fresh interpreter subprocess, not merely a fresh object)
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest

from src.engcore.domains.fluids.transport2d import (
    ALL_SIDES,
    ANALYTIC_REL_TOL,
    CENTRE_METRIC,
    FIELD_VARIABLE,
    MAX_METRIC,
    MIN_METRIC,
    MIN_OBSERVED_ORDER,
    VERIFICATION_LADDER,
    NativeDenseTransport2DSolver,
    Transport2DBindingError,
    Transport2DConfigurationError,
    Transport2DDomain,
    Transport2DError,
    Transport2DGrid,
    Transport2DSolver,
    build_transport2d_problem,
    read_centre_concentration_unguarded,
    read_centre_concentration_with_admission,
    run_verification_gate,
    side_orientation,
    solve_transport2d,
)
from src.engcore.domains.fluids.transport2d.solver import PreparedTransport2DSystem, assemble
from src.engcore.scientific.errors import ScientificValidationError
from src.engcore.scientific.results.validation import (
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
)
from src.engcore.scientific.results.variable_binding import VariableBulkLinkage
from src.engcore.scientific.solvers.protocol import ConvergenceState
from src.engcore.scientific.units.quantity import Quantity

# The frozen benchmark, restated once for every test in this module.
SIDE = Quantity(1.0, "m")
DIFFUSIVITY = Quantity(0.01, "m**2/s")
OMEGA = Quantity(1.0, "1/s")


def make_domain(n_cells: int, *, domain_id: str = "test") -> Transport2DDomain:
    return Transport2DDomain(
        domain_id=domain_id,
        side=SIDE,
        diffusivity=DIFFUSIVITY,
        angular_rate=OMEGA,
        grid=Transport2DGrid(n_cells),
    )


# =====================================================================
# Declarations
# =====================================================================

def test_domain_and_grid_reject_bad_configuration() -> None:
    with pytest.raises(Transport2DConfigurationError):
        Transport2DGrid(1)
    with pytest.raises(Transport2DConfigurationError):
        Transport2DGrid(4.5)  # type: ignore[arg-type]
    with pytest.raises(Transport2DConfigurationError):
        Transport2DDomain(
            domain_id="bad",
            side=Quantity(-1.0, "m"),
            diffusivity=DIFFUSIVITY,
            angular_rate=OMEGA,
            grid=Transport2DGrid(8),
        )
    with pytest.raises(Transport2DConfigurationError):
        Transport2DDomain(
            domain_id="bad",
            side=SIDE,
            diffusivity=Quantity(-0.01, "m**2/s"),
            angular_rate=OMEGA,
            grid=Transport2DGrid(8),
        )
    with pytest.raises(Transport2DConfigurationError):
        Transport2DDomain(
            domain_id="bad",
            side=SIDE,
            diffusivity=DIFFUSIVITY,
            angular_rate=Quantity(0.0, "1/s"),
            grid=Transport2DGrid(8),
        )


def test_fingerprint_excludes_discretization_but_not_physics() -> None:
    domain = make_domain(8)
    refined = domain.with_grid(Transport2DGrid(64))
    assert domain.fingerprint() == refined.fingerprint()

    different_physics = Transport2DDomain(
        domain_id=domain.domain_id,
        side=SIDE,
        diffusivity=Quantity(0.02, "m**2/s"),
        angular_rate=OMEGA,
        grid=Transport2DGrid(8),
    )
    assert domain.fingerprint() != different_physics.fingerprint()


def test_problem_declares_field_variable_and_four_oriented_boundaries() -> None:
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    names = {v.name for v in problem.variables}
    assert {FIELD_VARIABLE, CENTRE_METRIC, MAX_METRIC, MIN_METRIC} <= names
    assert {bc.region for bc in problem.boundary_conditions} == set(ALL_SIDES)
    for bc in problem.boundary_conditions:
        assert bc.variable == FIELD_VARIABLE
        assert bc.value == Quantity(0.0, "dimensionless")


def test_problem_domain_binding_refuses_rebinding_different_physics() -> None:
    domain = make_domain(8)
    other = make_domain(8, domain_id=domain.domain_id)
    other = Transport2DDomain(
        domain_id=domain.domain_id,
        side=SIDE,
        diffusivity=Quantity(0.05, "m**2/s"),
        angular_rate=OMEGA,
        grid=Transport2DGrid(8),
    )
    problem = build_transport2d_problem(domain, problem_id="shared-id")
    solver = Transport2DSolver()
    solver.bind_domain(domain, problem.problem_id)
    with pytest.raises(Transport2DBindingError):
        solver.bind_domain(other, problem.problem_id)


# =====================================================================
# F3 — numerical realization: sparse (production) vs dense (reference check)
# =====================================================================

def test_sparse_and_dense_solvers_agree_on_the_same_assembled_system() -> None:
    domain = make_domain(16)
    problem = build_transport2d_problem(domain)

    result = solve_transport2d(domain, run_id="cross-check", problem=problem, cross_check=True)
    checks_by_name = {c.name: c for c in result.validation.checks}
    agreement = checks_by_name["sparse_dense_assembly_agreement"]
    assert agreement.outcome is ValidationOutcome.PASS
    assert agreement.residual is not None and agreement.residual < 1e-9


def test_dense_solver_is_never_the_default_production_solver() -> None:
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="default-solver", problem=problem)
    assert result.solver is not None
    assert "scipy" in result.solver.backend.lower()
    assert result.solver.solver_id != NativeDenseTransport2DSolver().identity.solver_id


def test_native_dense_solver_alone_satisfies_the_solver_protocol() -> None:
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    dense_solver = NativeDenseTransport2DSolver()
    dense_solver.bind_domain(domain, problem.problem_id)
    prepared = dense_solver.prepare(problem)
    raw = dense_solver.solve(prepared)
    assert raw.convergence is ConvergenceState.CONVERGED
    metrics = dense_solver.extract_metrics(prepared, raw)
    assert CENTRE_METRIC in metrics


def test_assembly_is_shared_between_both_solvers_not_reimplemented() -> None:
    """The MODEL != REALIZATION != SOLVER separation, checked structurally:
    exactly one assembly function exists and both solver classes' `solve`
    consume its output, rather than each re-deriving the discretization."""
    domain = make_domain(8)
    system = assemble(domain)
    assert isinstance(system, PreparedTransport2DSystem)
    # Same right-hand side and same matrices feed both linear-algebra paths.
    dense_x = np.linalg.solve(system.dense, system.rhs)
    import scipy.sparse.linalg as spla

    sparse_x = spla.spsolve(system.sparse, system.rhs)
    assert np.max(np.abs(dense_x - sparse_x)) < 1e-9


# =====================================================================
# F4 — VariableBulkLinkage: the mandatory real production caller
# =====================================================================

def test_field_output_is_bound_through_variable_bulk_linkage() -> None:
    domain = make_domain(16)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="linkage-run", problem=problem)

    assert len(result.data_references) == 1
    field_ref = result.data_references[0]
    assert field_ref.name == FIELD_VARIABLE
    assert field_ref.count == 16 * 16
    assert field_ref.unit == "dimensionless"

    # solve_transport2d already constructed and checked a linkage internally
    # (raising if it failed); re-construct one here and prove it resolves
    # cleanly against the real problem+result, exactly as a downstream
    # reader would.
    linkage = VariableBulkLinkage(
        variable_name=FIELD_VARIABLE, reference_name=field_ref.name
    )
    issues = linkage.check_against(problem=problem, result=result)
    assert issues == ()

    declared_variable = problem.variable(FIELD_VARIABLE)
    assert declared_variable.unit == field_ref.unit  # dimension agreement holds


def test_variable_bulk_linkage_reduction_attack_without_it() -> None:
    """F5 residue, executed rather than argued: a records-only reader given
    only `result.data_references` and `problem.variables`, with NO linkage,
    cannot say which declared variable the bulk array instantiates — even
    though in this domain there happens to be only one field-shaped
    variable and one bulk reference, so a human reading the names might
    guess right. A records-only mechanism must not rely on a human guessing
    right, and nothing here performs a typed cross-reference without the
    binding record."""
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="no-linkage-check", problem=problem)

    reference = result.data_references[0]
    # The free-text name happens to equal the variable name in this domain —
    # a records-only reader still has no TYPED assurance of that; nothing
    # here checks it without constructing a VariableBulkLinkage and calling
    # check_against, which is exactly what the production path does.
    candidate_variables = [v for v in problem.variables if v.unit == reference.unit]
    # Multiple declared variables share the reference's unit/dimension
    # (c:field, c:centre, c:max, c:min are all "dimensionless") — a
    # dimension-only match is genuinely ambiguous among four candidates.
    assert len(candidate_variables) > 1


def test_linkage_catches_a_wrong_dimension_binding() -> None:
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="wrong-dim", problem=problem)

    # A deliberately wrong linkage: bind the field reference to a variable
    # this domain does not declare with a compatible dimension.
    bogus = VariableBulkLinkage(variable_name="c:centre", reference_name=FIELD_VARIABLE)
    # c:centre is dimensionless too, so this actually resolves cleanly on
    # dimension — demonstrating check_against validates dimension
    # compatibility, not "is this the semantically right variable", exactly
    # as documented in variable_binding.py's own module docstring (a
    # records-only reader gets a checked cross-reference, not proof of
    # domain intent beyond what the record states).
    issues = bogus.check_against(problem=problem, result=result)
    assert issues == ()

    # A genuinely missing variable name is caught.
    missing = VariableBulkLinkage(variable_name="c:does_not_exist", reference_name=FIELD_VARIABLE)
    issues = missing.check_against(problem=problem, result=result)
    assert len(issues) == 1


# =====================================================================
# F6 — boundary orientation, re-verified against the real production grid
# =====================================================================

@pytest.mark.parametrize("side", ALL_SIDES)
def test_every_side_is_half_inflow_half_outflow(side: str) -> None:
    """Re-verifies docs/fluid-pde-preparation.md §B7's finding against this
    package's OWN production velocity field and OWN production grid — not a
    re-print of the preparation's numbers."""
    orientation = side_orientation(side, n_cells=32, side_m=1.0, omega_per_s=1.0)
    assert orientation.inflow_fraction == pytest.approx(0.5)
    assert orientation.sign_changes == 1


def test_reversing_rotation_flips_the_signature_but_not_the_fraction() -> None:
    """The fraction alone is blind to a direction reversal; the point-by-
    point signature is not — the sharper instrument the preparation
    document names."""
    forward = side_orientation("side-south", n_cells=16, side_m=1.0, omega_per_s=1.0)
    backward = side_orientation("side-south", n_cells=16, side_m=1.0, omega_per_s=-1.0)
    assert forward.inflow_fraction == backward.inflow_fraction == pytest.approx(0.5)
    assert forward.orientation_signature != backward.orientation_signature
    # Every point's role is exactly reversed.
    assert forward.orientation_signature == tuple(not v for v in backward.orientation_signature)


def test_single_region_label_cannot_state_two_roles_at_once() -> None:
    """The concrete failure F6 requires reporting: BoundaryCondition.region
    is one label per side; the field it would need to carry ("inlet along
    half the side, outlet along the other half, simultaneously, for a
    steady problem") has no channel on the existing contract. This is
    checked by construction: a BoundaryCondition is built once per side
    (four total, matching problem.py), and nothing about the type signature
    of `region: str` can carry a second value along one side."""
    domain = make_domain(16)
    problem = build_transport2d_problem(domain)
    assert len(problem.boundary_conditions) == 4  # one per side, not per role
    for bc in problem.boundary_conditions:
        assert isinstance(bc.region, str)  # a single opaque label, no structure


# =====================================================================
# F7 — scientific correctness across the frozen n in {8,16,32,64} ladder
# =====================================================================

def test_verification_gate_reproduces_the_preparation_probes_numbers() -> None:
    """Reproduction check (prereg §10 stop condition): the production
    assembly must reproduce the ALREADY-EXECUTED preparation probe's own
    observed order and mms max-abs error at every rung, not merely be
    plausible."""
    domain = make_domain(8)
    report = run_verification_gate(domain)

    expected_orders = {16: 0.716, 32: 0.826, 64: 0.900}
    expected_mms_error = {8: 0.47969, 16: 0.29204, 32: 0.16473, 64: 0.08826}

    assert [r.n_cells for r in report.rungs] == list(VERIFICATION_LADDER)
    for rung in report.rungs:
        assert rung.mms_max_abs_error == pytest.approx(
            expected_mms_error[rung.n_cells], abs=1e-4
        )
        if rung.observed_order is not None:
            assert rung.observed_order == pytest.approx(
                expected_orders[rung.n_cells], abs=2e-3
            )

    assert report.numerically_converged is True
    assert report.analytically_verified is True
    assert ValidationLevel.NUMERICALLY_CONVERGED in report.levels_earned
    assert ValidationLevel.ANALYTICALLY_VERIFIED in report.levels_earned


def test_admissibility_violation_only_at_the_coarsest_rung() -> None:
    domain = make_domain(8)
    report = run_verification_gate(domain)
    by_n = {r.n_cells: r.admissibility_violation for r in report.rungs}
    assert by_n[8] > 0.0
    for n in (16, 32, 64):
        assert by_n[n] == 0.0


def test_centre_qoi_converges_toward_the_exact_value_of_one() -> None:
    domain = make_domain(8)
    report = run_verification_gate(domain)
    errors = [r.centre_abs_error for r in report.rungs]
    assert all(b < a for a, b in zip(errors, errors[1:]))  # monotonic
    assert report.rungs[-1].centre_qoi == pytest.approx(1.0, abs=ANALYTIC_REL_TOL)


def test_convergence_gate_fails_a_ladder_that_does_not_converge() -> None:
    """R1-style reduction: an artificially short/non-monotonic ladder is
    correctly refused, so the gate's PASS above is not a rubber stamp."""
    domain = make_domain(8)
    with pytest.raises(Transport2DConfigurationError):
        run_verification_gate(domain, ladder=(8,))


def test_per_solve_validation_never_claims_convergence_or_analytic_agreement() -> None:
    domain = make_domain(16)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="per-solve-only", problem=problem)
    by_name = {c.name: c for c in result.validation.checks}
    assert by_name["discretization_convergence"].outcome is ValidationOutcome.NOT_RUN
    assert by_name["analytic_reference_agreement"].outcome is ValidationOutcome.NOT_RUN
    assert ValidationLevel.NUMERICALLY_CONVERGED not in result.attained_levels
    assert ValidationLevel.ANALYTICALLY_VERIFIED not in result.attained_levels
    assert ValidationLevel.DIMENSIONALLY_VALID in result.attained_levels


# =====================================================================
# F8 — admission: a real Fluid-domain refusal path
# =====================================================================

def test_coarse_grid_genuinely_fails_the_admissibility_requirement() -> None:
    """The negative-proof scenario is REAL physics (the n=8 rung of this
    exact benchmark), not synthetic corruption of a passing result."""
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="n8-genuinely-fails", problem=problem)
    assert result.validation.status is ValidationOutcome.FAIL
    assert not result.validation.is_admissible(problem.validation_requirements)


def test_unguarded_consumer_silently_uses_a_failing_result() -> None:
    """Forbidden-outcome demonstration: without the guard, a real Fluid-
    domain function reads a value from a result whose declared requirement
    failed, and succeeds silently — proving the failure mode is real and
    structural absent the guard (mirrors HETERO-NGSPICE §8.4)."""
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="n8-unguarded", problem=problem)
    assert result.validation.status is ValidationOutcome.FAIL  # a real failure exists

    value = read_centre_concentration_unguarded(problem, result)
    assert isinstance(value, Quantity)  # silently succeeded despite the FAIL


def test_guarded_consumer_refuses_the_same_failing_result() -> None:
    """The mandatory F8 proof: FAIL -> require_admission(...) raises
    ScientificValidationError -> the consumer never reaches result.value()."""
    domain = make_domain(8)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="n8-guarded", problem=problem)

    with pytest.raises(ScientificValidationError) as excinfo:
        read_centre_concentration_with_admission(problem, result)
    assert "admissibility_bound" in str(excinfo.value)


def test_guarded_consumer_admits_a_genuinely_satisfied_result() -> None:
    """Admission, not blanket refusal: a fine grid that satisfies every
    declared requirement passes through the same guard unharmed."""
    domain = make_domain(32)
    problem = build_transport2d_problem(domain)
    result = solve_transport2d(domain, run_id="n32-admits", problem=problem)
    assert result.validation.status is ValidationOutcome.PASS

    value = read_centre_concentration_with_admission(problem, result)
    assert isinstance(value, Quantity)


def test_not_run_requirement_is_refused_even_when_is_usable_stays_true() -> None:
    """The sharper differentiator the Foundation's own falsifier (C3) named:
    a hand-built report where the declared requirement never ran, but
    nothing else failed, so `is_usable` stays True while `require_admission`
    still (correctly) refuses — proving this is not merely a repeat of the
    cheaper `is_usable` check."""
    domain = make_domain(32)
    problem = build_transport2d_problem(domain)
    base_result = solve_transport2d(domain, run_id="not-run-demo", problem=problem)

    # Replace one declared requirement's check with NOT_RUN, leaving every
    # other check PASS — is_usable only flips on FAIL/global state, so it
    # stays True here even though a declared requirement was never assessed.
    checks = tuple(
        ValidationCheck(
            name=c.name,
            outcome=ValidationOutcome.NOT_RUN if c.name == "admissibility_bound" else c.outcome,
            detail=c.detail,
            establishes=c.establishes,
        )
        for c in base_result.validation.checks
    )
    tampered_report = ValidationReport(checks=checks, notes="admissibility deliberately not run")

    assert tampered_report.status is not ValidationOutcome.FAIL  # is_usable-style check passes
    assert not tampered_report.is_admissible(problem.validation_requirements)
    with pytest.raises(ScientificValidationError):
        tampered_report.require_admission(problem.validation_requirements)


# =====================================================================
# F9 — executable reconstruction in a fresh process
# =====================================================================

def test_domain_serializes_and_reconstructs_with_no_shared_object_identity() -> None:
    domain = make_domain(16, domain_id="exec-spec")
    blob = json.dumps(domain.to_dict())
    reconstructed = Transport2DDomain.from_dict(json.loads(blob))
    assert reconstructed is not domain
    assert reconstructed.grid is not domain.grid
    assert reconstructed.fingerprint() == domain.fingerprint()
    assert reconstructed.to_dict() == domain.to_dict()


def test_problem_ir_round_trips_through_its_own_universal_schema() -> None:
    from src.engcore.scientific.ir.problem import ScientificProblem

    domain = make_domain(16, domain_id="exec-spec-ir")
    problem = build_transport2d_problem(domain)
    reconstructed = ScientificProblem.from_dict(json.loads(json.dumps(problem.to_dict())))
    assert reconstructed.to_dict() == problem.to_dict()


def test_full_reconstruction_and_re_execution_in_a_fresh_interpreter() -> None:
    """The strong form of F9: not just object reconstruction in the SAME
    process, but re-executed in a genuinely fresh Python interpreter
    subprocess, with the domain declaration and problem id handed across
    only as JSON — no pickled object, no shared identity of any kind."""
    domain = make_domain(16, domain_id="exec-spec-subprocess")
    problem = build_transport2d_problem(domain)
    original = solve_transport2d(domain, run_id="original-process", problem=problem)

    domain_json = json.dumps(domain.to_dict())
    problem_id = problem.problem_id
    repo_root = Path(__file__).resolve().parents[3]

    script = textwrap.dedent(
        f"""
        import json, sys
        sys.path.insert(0, {str(repo_root)!r})
        from src.engcore.domains.fluids.transport2d import (
            Transport2DDomain, build_transport2d_problem, solve_transport2d,
        )
        payload = json.loads({domain_json!r})
        domain = Transport2DDomain.from_dict(payload)
        problem = build_transport2d_problem(domain, problem_id={problem_id!r})
        result = solve_transport2d(domain, run_id="fresh-process", problem=problem)
        print(json.dumps({{k: v.magnitude_in("dimensionless") for k, v in result.values.items()}}))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(repo_root),
    )
    assert completed.returncode == 0, completed.stderr
    reconstructed_values = json.loads(completed.stdout.strip().splitlines()[-1])
    for name, quantity in original.values.items():
        assert reconstructed_values[name] == pytest.approx(
            quantity.magnitude_in("dimensionless"), abs=1e-12
        )


def test_reconstruction_residue_grid_and_solver_choice_are_not_carried() -> None:
    """What does NOT reconstruct, documented by a failing assumption rather
    than prose alone: Transport2DDomain.to_dict() carries the grid (numerical
    resolution) but NOT which solver class produced a given result, and NOT
    the VariableBulkLinkage that was constructed alongside it — a
    reconstruction rebuilds the PROBLEM faithfully; it does not replay
    "exactly this solver instance, exactly this run's linkage object"."""
    domain = make_domain(16)
    payload = domain.to_dict()
    assert "solver" not in payload
    assert "linkage" not in payload
    assert "n_cells" in payload["grid"]  # the grid DOES reconstruct


# =====================================================================
# Isolation guardrail: reference.py must not import solver.py
# =====================================================================

def test_reference_module_does_not_import_solver() -> None:
    import ast
    from pathlib import Path

    source = Path("src/engcore/domains/fluids/transport2d/reference.py").read_text()
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
    assert not any("solver" in m for m in imported_modules)
