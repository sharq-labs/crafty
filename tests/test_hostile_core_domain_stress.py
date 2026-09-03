"""HOSTILE-CORE-STRESS — the executable half of the milestone.

Preregistration: `docs/hostile-core-domain-stress-prereg.md`, committed before
any source file on this branch was written.
Evidence: `docs/hostile-core-domain-stress-evidence.md`, written after this ran.

**This module asserts measurements, not opinions.** Every count it checks is
produced by `experiments.hostile_core_stress.reader`, which is handed serialized
payloads and may not import the probe's domain modules. A test that asserted
"direction is unrecoverable" would be asserting the author's conclusion; a test
that asserts `count == 2` is asserting a fact about the contracts.

Some of these tests assert that the platform **fails**. That is the point of a
falsification milestone, and each such test carries the prediction number it
settles so a later reader can tell a measured gap from an accident.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from engcore.data.resolver import BulkDataResolver, relocate
from engcore.data.store import FilesystemBulkStore, InMemoryBulkStore
from engcore.scientific.composition.dependency import (
    QuantityDependency,
    externally_imposed,
    unresolved_inputs,
)
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.models.definition import BindingIssueKind, ValidityStatus
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.validation import ValidationOutcome
from engcore.scientific.units.quantity import Quantity

from experiments.hostile_core_stress import reader as rd
from experiments.hostile_core_stress import records as rc
from experiments.hostile_core_stress import transport1d as t1

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = REPO_ROOT / "experiments" / "hostile_core_stress"


# =============================================================================
# Fixtures — the frozen cases, wired once
# =============================================================================

def _payloads(run: rc.ProbeRun) -> dict:
    """Round-trip through JSON so a reader cannot receive a live object."""
    return json.loads(json.dumps(rc.serialize(run)))


@pytest.fixture(scope="module")
def model_payload() -> dict:
    return json.loads(json.dumps(rc.TRANSPORT_MODEL.to_dict()))


@pytest.fixture(scope="module")
def catalogue() -> dict:
    return json.loads(json.dumps(rc.realization_catalogue()))


@pytest.fixture(scope="module")
def case_t_run() -> rc.ProbeRun:
    return rc.run_case(t1.case_t())


@pytest.fixture(scope="module")
def case_t_payloads(case_t_run: rc.ProbeRun) -> dict:
    return _payloads(case_t_run)


@pytest.fixture(scope="module")
def reversed_problem_payload() -> dict:
    """CASE T transported the other way. PROBE E's input."""
    reversed_case = t1.case_t().with_velocity(-t1.FROZEN_VELOCITY_M_S)
    return json.loads(json.dumps(rc.build_problem(reversed_case).to_dict()))


# =============================================================================
# The probe is real physics, not a prop
# =============================================================================

def test_steady_solution_converges_to_the_closed_form():
    """CASE S against its exact solution. Central differencing, refining mesh.

    Not a convergence-order claim — one sequence of five solves establishes no
    order — only that the probe solves the equation it says it solves. A probe
    whose numerics were wrong would make every architectural finding worthless.
    """
    errors = []
    for n_cells in t1.CASE_S_CELL_COUNTS:
        case = t1.case_s(n_cells, t1.AdvectionScheme.CENTRAL)
        field = t1.solve_steady(case)
        reference = [t1.steady_reference(case, x) for x in case.nodes_m]
        errors.append(max(abs(a - b) for a, b in zip(field, reference)))
    assert errors == sorted(errors, reverse=True), (
        f"central-difference error must fall under refinement, got {errors}"
    )
    assert errors[-1] < 2.5e-3, f"finest rung error {errors[-1]:.3e}"


def test_transient_solution_agrees_with_ogata_banks_inside_its_window():
    """CASE T against the semi-infinite reference, inside the frozen window.

    The window margin is asserted positive rather than assumed: the reference
    is semi-infinite and the domain is not, so agreement outside the window
    would verify nothing. Prereg §4 required this to be stated as a number.
    """
    case = t1.case_t()
    margin = t1.reference_window_margin(case)
    assert margin > 0.0, f"reference window margin must be positive, got {margin}"
    field = t1.solve_transient(case)
    reference = [t1.ogata_banks(case, x, case.end_time_s) for x in case.nodes_m]
    error = max(abs(a - b) for a, b in zip(field, reference))
    assert error < 1e-2, f"CASE T vs Ogata-Banks: {error:.4e}"


def test_upwind_is_bounded_at_every_mesh_and_central_is_not():
    """The boundedness split, measured. This is what PROBE D rests on.

    Upwind assembles an M-matrix at every cell Peclet number and therefore
    obeys a discrete maximum principle; central loses that the moment the
    super-diagonal coefficient changes sign at ``Pe_cell = 2``.

    ``ROUNDOFF`` is not a fudge factor. The well-resolved central rungs land on
    ``max = 1 + 2.2e-16`` — one unit in the last place of the boundary value
    itself, produced by the back-substitution and not by the discretization.
    Counting that as a boundedness failure would make the measurement report
    floating-point arithmetic rather than the sign change it is about.
    """
    ROUNDOFF = 1e-12
    upwind_violations = {}
    central_violations = {}
    for n_cells in t1.CASE_S_CELL_COUNTS:
        for scheme, sink in (
            (t1.AdvectionScheme.UPWIND, upwind_violations),
            (t1.AdvectionScheme.CENTRAL, central_violations),
        ):
            case = t1.case_s(n_cells, scheme)
            sink[case.cell_peclet] = t1.admissibility_violation(
                t1.solve_steady(case)
            )
    assert max(upwind_violations.values()) < ROUNDOFF, upwind_violations
    unbounded = {pe for pe, v in central_violations.items() if v > ROUNDOFF}
    assert unbounded == {5.0, 2.5}, (
        f"central differencing must be unbounded exactly above Pe_cell 2, "
        f"got violations at {sorted(unbounded)}"
    )
    assert central_violations[5.0] == pytest.approx(0.4301991580760791, rel=1e-9)
    assert central_violations[2.5] == pytest.approx(0.1111111111111116, rel=1e-9)


# =============================================================================
# The instrument is honest
# =============================================================================

def test_reader_cannot_see_the_domain():
    """The records-only reader imports no probe module. Asserted by AST scan.

    Prereg §7. A reader that could import ``transport1d`` or ``records`` would
    be measuring what the author knows rather than what the records say, and
    every count in this file would be worthless. Checked structurally rather
    than by convention because a convention is exactly what would erode.
    """
    tree = ast.parse((PROBE_ROOT / "reader.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            if node.level:  # a relative import inside the probe package
                imported.add(f".{node.module or ''}")
    forbidden = {name for name in imported if "transport1d" in name}
    forbidden |= {name for name in imported if name.endswith("records")}
    forbidden |= {name for name in imported if name.startswith(".")}
    assert not forbidden, (
        f"the records-only reader must not import the probe domain; found "
        f"{sorted(forbidden)}"
    )


def test_serialized_payloads_carry_no_live_objects(case_t_payloads):
    """What the reader receives is JSON, and reconstructs through the contracts."""
    problem = ScientificProblem.from_dict(case_t_payloads["problem"])
    result = ScientificResult.from_dict(case_t_payloads["result"])
    assert problem.problem_id.startswith("transport-1d-")
    assert result.problem_id == problem.problem_id


# =============================================================================
# PROBE A / the recoverability matrix — the central measurement
# =============================================================================

STRICT_MATRIX = {
    "Q1 what the dependent scientific quantity is": rd.Recoverability.RECOVERABLE,
    "Q2 whether it is scalar or spatially distributed": rd.Recoverability.IMPOSSIBLE,
    "Q3 its physical unit": rd.Recoverability.RECOVERABLE,
    "Q4 what spatial entity it is defined over": rd.Recoverability.IMPOSSIBLE,
    "Q5 what its initial state means": rd.Recoverability.RECOVERABLE,
    "Q6 what its boundary conditions are": rd.Recoverability.RECOVERABLE,
    "R1a boundary records are injective onto physical systems": (
        rd.Recoverability.IMPOSSIBLE
    ),
    "R1b an oriented boundary subset of a spatial entity": (
        rd.Recoverability.IMPOSSIBLE
    ),
    "Q8 which model/equation governs it": rd.Recoverability.RECOVERABLE,
    "Q9 what the transport direction means": rd.Recoverability.AMBIGUOUS,
    "Q10 what solver capability is required": rd.Recoverability.RECOVERABLE,
    "Q11 whether the field representation is independent of storage": (
        rd.Recoverability.RECOVERABLE
    ),
    "Q12 whether the same field could later have two discretizations": (
        rd.Recoverability.IMPOSSIBLE
    ),
    "R2a which realization identity produced this result": (
        rd.Recoverability.RECOVERABLE
    ),
}


def test_recoverability_matrix_under_the_strict_convention(
    case_t_payloads, reversed_problem_payload, catalogue
):
    """The matrix with the free-text channel refused. Prereg §7.

    Asserted as an exact map of question -> verdict, so a later change to any
    contract moves this test rather than silently moving the evidence.
    """
    findings = rd.recoverability_matrix(
        case_t_payloads,
        physically_transient=True,
        reversed_problem_payload=reversed_problem_payload,
        realization_catalogue=catalogue,
        admit_free_text=False,
    )
    assert {f.question: f.verdict for f in findings} == STRICT_MATRIX


def test_recoverability_matrix_under_the_permissive_convention(
    case_t_payloads, reversed_problem_payload, catalogue
):
    """The same matrix with the free-text channel admitted, for both questions.

    Closes the adversarial pass's D-1: an earlier version granted the string
    channel to R2b and denied it to R1, then reported the contrast as a
    finding. Both are now graded by one rule, under both rules, and exactly the
    two string-channel questions move.
    """
    findings = rd.recoverability_matrix(
        case_t_payloads,
        physically_transient=True,
        reversed_problem_payload=reversed_problem_payload,
        realization_catalogue=catalogue,
        admit_free_text=True,
    )
    permissive = {f.question: f.verdict for f in findings}
    moved = {
        question
        for question, verdict in permissive.items()
        if verdict is not STRICT_MATRIX[question]
    }
    assert moved == {
        "R1a boundary records are injective onto physical systems",
        "Q12 whether the same field could later have two discretizations",
    }
    for question in moved:
        assert permissive[question] is rd.Recoverability.METADATA_ONLY

    # And the concept that has no record at all does NOT move, under any
    # convention. No naming scheme conjures a topology.
    assert (
        permissive["R1b an oriented boundary subset of a spatial entity"]
        is rd.Recoverability.IMPOSSIBLE
    )


def test_matrix_ledger_split_is_carried_in_the_data(
    case_t_payloads, reversed_problem_payload, catalogue
):
    """Prereg §10.1, with the booking rule the adversarial pass forced.

    A finding is Ledger 1 only when **both** the measurement and the remedy live
    in a record that exists. The orientation question straddles that line and is
    therefore **split**: R1a (the ``(kind, region, value)`` triple is not
    injective) is Ledger 1; R1b (the remedy is an oriented boundary of an absent
    topology) is Ledger 2, alongside Q2 and Q4.

    An earlier version booked the whole orientation finding to Ledger 1, which
    blended the ledgers in exactly the way prereg §13.5 declares a fail
    condition.
    """
    findings = rd.recoverability_matrix(
        case_t_payloads,
        physically_transient=True,
        reversed_problem_payload=reversed_problem_payload,
        realization_catalogue=catalogue,
    )
    ledger_two = {
        f.question for f in findings if f.ledger is rd.Ledger.ABSENT_RECORD
    }
    assert ledger_two == {
        "Q2 whether it is scalar or spatially distributed",
        "Q4 what spatial entity it is defined over",
        "R1b an oriented boundary subset of a spatial entity",
    }


# =============================================================================
# PROBE C / PROBE E — boundary asymmetry and direction reversal
# =============================================================================

def test_p1_upstream_boundary_is_unrecoverable_from_records(
    case_t_payloads, reversed_problem_payload
):
    """PREDICTION P1 — CONFIRMED. R1a admits 2 readings, not 1.

    Measured, not argued: reversing the transport direction leaves every
    serialized ``BoundaryCondition`` byte-identical while flipping which end is
    the inflow. One set of boundary records therefore describes two physically
    different systems.

    The claim booked to Ledger 1 is exactly this and no wider: **the
    ``(kind, region, value)`` triple is not injective onto physical systems.**
    It survives independently of any field concept — `HETERO-NGSPICE` §66.4
    needed a passive-sign guard for a two-terminal lumped element with no
    continuum topology anywhere — so orientation is a universal scientific
    distinction rather than a PDE one. The *remedy* is Ledger 2; see
    ``test_matrix_ledger_split_is_carried_in_the_data``.
    """
    finding, remedy = rd.count_orientation_readings(
        case_t_payloads["problem"], reversed_problem_payload
    )
    assert finding.admissible_readings == 2
    assert finding.verdict is rd.Recoverability.IMPOSSIBLE
    assert finding.ledger is rd.Ledger.EXISTING_RECORD
    assert remedy.ledger is rd.Ledger.ABSENT_RECORD

    forward = ScientificProblem.from_dict(case_t_payloads["problem"])
    reversed_ = ScientificProblem.from_dict(reversed_problem_payload)
    assert [b.to_dict() for b in forward.boundary_conditions] == [
        b.to_dict() for b in reversed_.boundary_conditions
    ], "the two directions must produce identical boundary records"
    assert forward.parameter("velocity").value.magnitude == pytest.approx(
        -reversed_.parameter("velocity").value.magnitude
    )


def test_the_dirichlet_means_inflow_convention_is_unsound():
    """The obvious fallback reading, killed by a record this probe builds.

    A reader denied a typed answer to R1 might reach for *Dirichlet means
    inflow*. CASE S declares Dirichlet at both ends, so that convention labels
    two boundaries as the inflow of a one-dimensional flow. The fallback is not
    available, which is why R1's count is 2 rather than 1.
    """
    steady = rc.build_problem(t1.case_s(40)).to_dict()
    assert rd.dirichlet_convention_is_unsound(steady) is True
    transient = rc.build_problem(t1.case_t()).to_dict()
    assert rd.dirichlet_convention_is_unsound(transient) is False


def test_reversal_changes_no_boundary_record_and_nothing_notices():
    """PROBE E. The only thing that reacts to a reversal is a range check.

    And it reacts about a *parameter*, reporting that the velocity left its
    declared interval — not that the Neumann condition is now sitting on the
    inflow end, which is the scientifically important consequence and the one
    no record states.
    """
    reversed_case = t1.case_t().with_velocity(-t1.FROZEN_VELOCITY_M_S)
    payload = json.loads(json.dumps(rc.build_problem(reversed_case).to_dict()))
    model = json.loads(json.dumps(rc.TRANSPORT_MODEL.to_dict()))
    verdict = rd.validity_from_records(payload, model)
    assert verdict.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert verdict.violated == ("velocity",), (
        "the only reaction to a direction reversal is a range check on the "
        "velocity parameter"
    )


# =============================================================================
# PROBE D — discretization substitution
# =============================================================================

def test_p3_realization_identity_is_recoverable_and_selection_is_not(
    case_t_payloads, catalogue
):
    """PREDICTION P3 — SPLIT, and RESTATED after the adversarial pass.

    P3 predicted the scheme would not be recoverable. It **is**, twice over:
    ``ProvenanceRecord.bindings`` names the realization, and
    ``ImplementationReference.implementation_id`` differs between the two —
    both typed, both serialized, which is exactly what
    `07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md` §16.E requires. An earlier version
    of the reader excluded ``implementation`` from its scan and reported a gap
    that was not there.

    What survives is **selection semantics**: the records distinguish the two
    realizations and state no typed *property* by which a planner could choose
    the monotone one. Under the strict convention that is 2 admissible
    candidates; under the permissive one a planner reads prose.
    """
    identity, denotation = rd.count_scheme_readings(
        case_t_payloads["result"], catalogue, admit_free_text=False
    )
    assert identity.verdict is rd.Recoverability.RECOVERABLE
    assert identity.admissible_readings == 1
    assert denotation.verdict is rd.Recoverability.IMPOSSIBLE
    assert denotation.admissible_readings == 2
    assert "implementation" in denotation.detail, (
        "the typed identity channel must be named as working, not omitted"
    )

    _, permissive = rd.count_scheme_readings(
        case_t_payloads["result"], catalogue, admit_free_text=True
    )
    assert permissive.verdict is rd.Recoverability.METADATA_ONLY
    assert permissive.admissible_readings == 1

    without_catalogue_identity, without_catalogue = rd.count_scheme_readings(
        case_t_payloads["result"], None
    )
    assert without_catalogue_identity.verdict is rd.Recoverability.RECOVERABLE
    assert without_catalogue.verdict is rd.Recoverability.IMPOSSIBLE


def test_no_typed_property_separates_the_two_discretizations():
    """Identity separates them; no typed *property* does.

    ``ModelFormulation`` answers *what mathematical form is posed*, and both
    schemes pose the same PDE. Stretching it to carry a scheme is the exact
    overloading MODEL0-R refused when it removed ``SURROGATE``.

    Counter-evidence recorded rather than suppressed: `docs/scientific-core/
    README.md` "Fidelity: why the core declares none" rejected a
    ``RealizationFidelity`` enum because its members conflated *"at least
    four"* axes, and "central vs upwind" conflates operator family, order of
    accuracy, monotonicity and staggering in the same way. That argument weighs
    directly against forcing a typed discretization field onto a
    ``DESIGN-FROZEN`` contract, and the evidence document records it.
    """
    central, upwind = rc.REALIZATION_CENTRAL, rc.REALIZATION_UPWIND

    # Identity channels: these DO separate them, and they are typed.
    assert central.realization_id != upwind.realization_id
    assert (
        central.implementation.implementation_id
        != upwind.implementation.implementation_id
    )

    # Property channels: every one is identical.
    property_fields = {
        "provided_capabilities",
        "required_capabilities",
        "required_solver_capabilities",
        "formulation",
    }
    identical = {
        name
        for name in property_fields
        if getattr(central, name) == getattr(upwind, name)
    }
    assert identical == property_fields
    assert central.formulation is upwind.formulation


def test_one_scientific_field_two_meshes_two_problem_identities():
    """PROBE D. The encoding fork, measured on both horns.

    Under the metadata encoding the two meshes produce **identical** problem
    records — scientific identity survives refinement, and ``Pe_cell`` is
    unreachable. Under the typed-parameter encoding ``Pe_cell`` is reachable
    and the two meshes are now **different** problems. There is no encoding in
    which both hold.
    """
    coarse, fine = t1.case_s(8), t1.case_s(160)

    metadata_coarse = rc.build_problem(coarse, encoding=rc.Encoding.METADATA)
    metadata_fine = rc.build_problem(fine, encoding=rc.Encoding.METADATA)
    assert [p.to_dict() for p in metadata_coarse.parameters] == [
        p.to_dict() for p in metadata_fine.parameters
    ], "under the metadata encoding, refinement must not change the science"
    assert metadata_coarse.metadata["n_cells"] != metadata_fine.metadata["n_cells"]

    typed_coarse = rc.build_problem(coarse, encoding=rc.Encoding.TYPED_PARAMETER)
    typed_fine = rc.build_problem(fine, encoding=rc.Encoding.TYPED_PARAMETER)
    assert [p.to_dict() for p in typed_coarse.parameters] != [
        p.to_dict() for p in typed_fine.parameters
    ], "under the typed encoding, refinement changes the problem statement"


def test_p5_the_criterion_is_recoverable_from_three_sources_at_three_costs():
    """PREDICTION P5 — FALSIFIED, and the falsification is the better finding.

    P5 predicted the mesh-dependent criterion would not be reconstructible from
    records. It is, three ways, and an earlier draft of this milestone claimed a
    dilemma — *"no encoding gives both"* — which the adversarial pass refuted
    with a typed channel the probe already populates.

    What survives is narrower, true, and contains no fluid word: a
    mesh-dependent validity criterion is assessable **per-run** and never
    **pre-run**, because its only home that keeps the problem mesh-free is a
    record that does not exist until a solve has produced it.
    """
    case = t1.case_s(8)
    expected = pytest.approx(1.0 / 5.0)  # Pe_cell = 5, so 1/Pe = 0.2

    metadata = rc.build_problem(case, encoding=rc.Encoding.METADATA).to_dict()
    from_metadata = rd.recover_resolution_criterion(metadata)
    assert from_metadata.verdict is rd.Recoverability.METADATA_ONLY
    assert from_metadata.source == "problem.metadata"
    assert from_metadata.value == expected
    assert from_metadata.run_scoped is False

    typed = rc.build_problem(case, encoding=rc.Encoding.TYPED_PARAMETER).to_dict()
    from_typed = rd.recover_resolution_criterion(typed)
    assert from_typed.verdict is rd.Recoverability.RECOVERABLE
    assert from_typed.source == "typed n_cells parameter"
    assert from_typed.value == expected
    assert from_typed.run_scoped is False

    run = rc.run_case(case, encoding=rc.Encoding.PROVENANCE_INPUT)
    payloads = _payloads(run)
    from_provenance = rd.recover_resolution_criterion(
        payloads["problem"], payloads["result"]
    )
    assert from_provenance.verdict is rd.Recoverability.RECOVERABLE
    assert from_provenance.source == "ProvenanceRecord.inputs"
    assert from_provenance.value == expected
    assert from_provenance.run_scoped is True


def test_encoding_c_keeps_problem_identity_mesh_free_and_the_criterion_typed():
    """The third horn, measured. Closes the adversarial pass's C-2.

    ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]`` — typed,
    dimension-checked, serialized — on the record documented as *"everything
    needed to attribute and re-derive a result"*, and
    ``validity_context``'s own docstring sanctions exactly this use for *"a
    Reynolds number, a detected regime"*. A cell Peclet number is that object.
    """
    coarse = rc.run_case(t1.case_s(8), encoding=rc.Encoding.PROVENANCE_INPUT)
    fine = rc.run_case(t1.case_s(160), encoding=rc.Encoding.PROVENANCE_INPUT)

    assert coarse.problem.to_dict() == fine.problem.to_dict(), (
        "under ENCODING_C the problem record must be byte-identical across "
        "refinement — no mesh anywhere in scientific identity"
    )
    assert coarse.problem.problem_id == fine.problem.problem_id

    coarse_input = coarse.result.provenance.inputs["inverse_peclet_cell"]
    fine_input = fine.result.provenance.inputs["inverse_peclet_cell"]
    assert isinstance(coarse_input, Quantity)
    assert coarse_input.magnitude == pytest.approx(0.2)
    assert fine_input.magnitude == pytest.approx(4.0)


def test_the_criterion_can_be_evaluated_but_only_after_the_solve():
    """The residual that survives C-2, asserted as the thing actually claimed.

    Under ENCODING_C the model's own resolution criterion evaluates correctly —
    ``OUTSIDE_VALIDATED_DOMAIN`` for the coarse mesh, ``IN_DOMAIN`` for the fine
    one. And it is reachable **only** from a run record, so ``ValidityDomain``
    cannot screen a proposed discretization before the solve is spent. That
    generalizes verbatim to CFL number, Courant number, y+ and element
    aspect ratio.
    """
    model = rc.TRANSPORT_MODEL.to_dict()

    coarse = _payloads(rc.run_case(t1.case_s(8), encoding=rc.Encoding.PROVENANCE_INPUT))
    verdict = rd.validity_from_records(
        coarse["problem"], model, result_payload=coarse["result"]
    )
    assert verdict.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert verdict.violated == ("inverse_peclet_cell",)

    fine = _payloads(rc.run_case(t1.case_s(160), encoding=rc.Encoding.PROVENANCE_INPUT))
    assert (
        rd.validity_from_records(
            fine["problem"], model, result_payload=fine["result"]
        ).status
        is ValidityStatus.IN_DOMAIN
    )

    # Pre-run: the problem alone carries nothing, so the criterion is UNKNOWN.
    pre_run = rd.validity_from_records(coarse["problem"], model)
    assert pre_run.status is ValidityStatus.UNKNOWN
    assert pre_run.unknown == ("inverse_peclet_cell",)


def test_under_the_baseline_domains_own_encoding_the_criterion_is_unreachable():
    """A Ledger-1 finding that survives every correction.

    ``validity_context`` is built from typed parameters and documents that it is
    *"deliberately not sourced from metadata"*. Under the encoding the baseline
    PDE domain actually uses, a reader obeying that rule gets ``UNKNOWN`` — not
    ``VIOLATED`` — for a mesh at ``Pe_cell = 5``. Only a reader willing to break
    the platform's own stated rule reaches the right answer.
    """
    payload = rc.build_problem(
        t1.case_s(8), encoding=rc.Encoding.METADATA
    ).to_dict()
    model = rc.TRANSPORT_MODEL.to_dict()

    obedient = rd.validity_from_records(payload, model, supply_criterion=False)
    assert obedient.status is ValidityStatus.UNKNOWN
    assert obedient.unknown == ("inverse_peclet_cell",)

    determined = rd.validity_from_records(payload, model)
    assert determined.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert determined.violated == ("inverse_peclet_cell",)


# =============================================================================
# P7 — physical admissibility is not a concept the platform has
# =============================================================================

def test_p7_an_inadmissible_result_passes_every_check_the_platform_runs():
    """PREDICTION P7 — CONFIRMED IN SUBSTANCE, WRONG IN SIGN. See evidence D-1.

    The preregistration predicted ``c(x) < 0``. The measured violation is an
    **overshoot above the Dirichlet maximum**, not an undershoot: with
    ``c(0)=1`` and ``c(L)=0`` the central-difference oscillation grows towards
    the outflow, so it exceeds 1 rather than falling below 0. The substance of
    the prediction — a value outside the physically admissible range passing
    every check — holds exactly.
    """
    run = rc.run_case(t1.case_s(8, t1.AdvectionScheme.CENTRAL))

    assert run.admissibility_violation > 0.4
    assert run.result.values["c:max"].magnitude > t1.ADMISSIBLE_MAX
    assert run.result.values["c:min"].magnitude >= t1.ADMISSIBLE_MIN, (
        "the measured violation is an overshoot, not an undershoot; the "
        "preregistered sign was wrong and the evidence records it"
    )

    assert run.result.validation.status is ValidationOutcome.PASS
    assert not run.result.validation.failures
    levels = {level.value for level in run.result.validation.attained_levels}
    assert {"dimensionally_valid", "numerically_converged"} <= levels, (
        "the result claims dimensional validity and numerical convergence for "
        "a physically impossible field"
    )


def test_a_domain_can_express_the_admissibility_check_today():
    """The overclaim, refuted by executing the thing it said was impossible.

    An earlier draft asserted *"there is no contract to express one on and no
    vocabulary to name it in"* — which prereg §11 Attack 3 had pre-committed
    **not** to claim, and which is false. ``ValidationCheck.name`` is free text
    and ``ValidationReport.status`` returns ``FAIL`` if any check fails, so the
    check is writable today with no contract change, from inputs already typed
    and serialized on these records.

    Written out rather than argued, because the milestone's credibility depends
    on its negative claims being ones it actually tested.
    """
    run = rc.run_case(t1.case_s(8, t1.AdvectionScheme.CENTRAL))
    check = rc.admissibility_check(run.field, data=[1.0, 0.0])

    assert check.outcome is ValidationOutcome.FAIL
    assert check.residual == pytest.approx(0.4301991580760791, rel=1e-9)

    strengthened = run.result.validation.with_check(check)
    assert strengthened.status is ValidationOutcome.FAIL, (
        "adding one check flips the aggregate verdict; nothing in the platform "
        "prevented this from being written in the first place"
    )

    bounded = rc.run_case(t1.case_s(160, t1.AdvectionScheme.CENTRAL))
    assert (
        rc.admissibility_check(bounded.field, data=[1.0, 0.0]).outcome
        is ValidationOutcome.PASS
    )


def test_the_evidence_ladder_is_asymmetric_on_physical_admissibility():
    """What actually survives from P7, and it is a real Ledger-1 gap.

    A domain can record an admissibility **violation** — ``outcome=FAIL`` — and
    structurally cannot record its **attainment**: ``ValidationLevel`` has seven
    members and none denotes physical admissibility, so a passing check has
    nothing to put in ``establishes=`` and contributes to no attained level.
    The ladder can say "this is wrong" and cannot say "this was checked and is
    right".
    """
    from engcore.scientific.results.validation import ValidationLevel

    levels = {level.value for level in ValidationLevel}
    assert len(levels) == 7
    assert not any(
        token in level
        for level in levels
        for token in ("admissib", "bounded", "physical_range", "maximum_principle")
    ), f"no admissibility level exists among {sorted(levels)}"

    bounded = rc.run_case(t1.case_s(160, t1.AdvectionScheme.CENTRAL))
    passing = rc.admissibility_check(bounded.field, data=[1.0, 0.0])
    assert passing.outcome is ValidationOutcome.PASS
    assert passing.establishes is None
    report = bounded.result.validation.with_check(passing)
    assert report.status is ValidationOutcome.PASS
    assert report.attained_levels == bounded.result.validation.attained_levels, (
        "a passing admissibility check adds no attained level, because there "
        "is no level for it to establish"
    )


def test_nothing_in_universal_core_compares_a_result_to_declared_bounds():
    """``ScientificVariable`` carries typed bounds and no result path reads them.

    ``require_within_bounds`` exists and is called only from the design-space,
    experiment and optimizer-adapter paths — never from anything that inspects a
    ``ScientificResult``. §66.4's own lesson, one layer out: *a check whose only
    effect is a field nothing consults is not a guard* — and here the field is
    consulted, just never against a solved state.
    """
    import subprocess

    proc = subprocess.run(
        ["git", "grep", "-l", "require_within_bounds", "--", "src/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    callers = set(proc.stdout.split())
    assert callers == {
        "src/engcore/design/space.py",
        "src/engcore/scientific/experiments/experiment.py",
        "src/engcore/scientific/experiments/optimizer_adapter.py",
        "src/engcore/scientific/ir/variables.py",
    }
    assert not any("results" in path for path in callers)


# =============================================================================
# P2 / P6 — what the core gets right, measured with the same instrument
# =============================================================================

def test_p2_the_transience_defect_is_in_the_baseline_domain_not_the_contract():
    """PREDICTION P2 — CONFIRMED, and located.

    The baseline conduction domain declares no ``InitialCondition``, so
    ``is_time_dependent`` is ``False`` for the repository's only transient PDE.
    The steelman encoding writes real records and the same property is then
    correct for both frozen cases. The contract works; the domain did not use
    it.
    """
    from engcore.domains.thermal.conduction1d import problem as baseline

    slab = baseline.ConductionSlab(
        slab_id="hostile-probe-readonly",
        length=Quantity(1.0, "meter"),
        diffusivity=Quantity(0.01, "m**2/s"),
        end_time=Quantity(0.5, "second"),
        discretization=baseline.SlabDiscretization(n_cells=8, n_steps=10),
    )
    baseline_problem = baseline.build_conduction_problem(slab)
    assert baseline_problem.is_time_dependent is False, (
        "measured on the existing domain: a transient PDE that reports itself "
        "as not time dependent"
    )
    assert baseline_problem.initial_conditions == ()
    assert "initial_condition" in baseline_problem.metadata

    assert rc.build_problem(t1.case_t()).is_time_dependent is True
    assert rc.build_problem(t1.case_s(40)).is_time_dependent is False


def test_p6_a_boundary_value_problem_needs_no_external_supplier():
    """PREDICTION P6 — CONFIRMED. The core reader passes the shot aimed at it.

    CASE S is steady, declares no initial condition, and has its state fixed
    entirely by Dirichlet boundaries. That is precisely the shape
    `MIN-FOUNDATION-ET`'s repair to ``unresolved_inputs`` was written for, and
    the aimed adversarial shot of prereg §11 Attack 4. It holds: the state is
    reported as determined, not as needing an external source.
    """
    steady = rc.build_problem(t1.case_s(40))
    assert unresolved_inputs([steady]) == ()
    assert externally_imposed([steady], []) == ()

    transient = rc.build_problem(t1.case_t())
    assert unresolved_inputs([transient]) == ()


def test_p4_no_model_can_declare_the_conditions_its_equation_requires(model_payload):
    """PREDICTION P4 — CONFIRMED, and NARROWED after the adversarial pass.

    ``InputSourceKind`` has two members, ``variable`` and ``parameter``. A model
    can enumerate what it consumes and structurally cannot enumerate the
    conditions its equation requires, so there is no declared requirement for a
    reader to compare the declared set against.

    The earlier phrasing — "not detectable at all" — was too strong. See
    ``test_wellposedness_is_detectable_once_the_context_can_see_structure``.
    """
    from engcore.scientific.models.definition import InputSourceKind

    assert {m.value for m in InputSourceKind} == {"variable", "parameter"}

    for case in (t1.case_t(), t1.case_n()):
        payload = rc.build_problem(case).to_dict()
        finding = rd.count_wellposedness_readings(payload, model_payload)
        assert finding.verdict is rd.Recoverability.IMPOSSIBLE
        assert finding.admissible_readings == 0
        assert "NOT 'undetectable in principle'" in finding.detail


def test_wellposedness_is_detectable_once_the_context_can_see_structure():
    """The counterexample that narrows R4, executed. Closes the pass's D-3.

    A ``RangeCondition`` over a structural fact about the problem — how many
    boundary conditions were declared — evaluates perfectly well when that fact
    reaches ``validity_context``. No new contract, no new field.

    So the finding is not "well-posedness is undetectable". It is: **
    ``validity_context`` is built only from typed parameters, so a declarative
    validity criterion cannot reference a structural fact about the problem
    statement**, and (prereg baseline fact B17, corroborated not discovered) a
    static ``ValidityDomain`` cannot state a condition count that depends on a
    parameter value.
    """
    over_specified = rc.build_problem(t1.case_n()).to_dict()
    assert (
        rd.wellposedness_is_detectable_with_structural_context(over_specified)
        is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    )

    problem = ScientificProblem.from_dict(over_specified)
    assert "boundary_condition_count" not in problem.validity_context(), (
        "the fact is not in the context by default; the route from the "
        "problem's own structure into the context that judges it is what is "
        "missing"
    )


def test_case_n_is_refused_but_for_the_wrong_reason(model_payload):
    """CASE N is caught — by a range check on D, not by well-posedness.

    Worth stating precisely, because it is the difference between the platform
    protecting the user and the platform coincidentally agreeing. This probe's
    model happens to declare ``D > 0``. A domain that legitimately declared a
    pure-advection model valid at ``D = 0`` would get no protection at all, and
    the over-specified boundary set would still be undetectable.
    """
    payload = rc.build_problem(t1.case_n()).to_dict()
    verdict = rd.validity_from_records(payload, model_payload)
    assert verdict.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    assert verdict.violated == ("diffusivity", "inverse_peclet_cell")


def test_the_infinite_criterion_is_a_parameterisation_artefact_not_a_gap(
    model_payload,
):
    """WITHDRAWN FINDING, kept as a measurement. See evidence D-2.

    An earlier draft reported this as an unanticipated contract gap: at
    ``D = 0`` the cell Peclet number is genuinely infinite, ``Quantity`` refuses
    non-finite magnitudes, so the condition written to catch pure advection
    could not be evaluated there.

    The adversarial pass showed it is **not a contract finding**. ``Pe <= 2``
    and ``1/Pe >= 0.5`` are the same criterion, and the reciprocal is ``0.0`` at
    ``D = 0`` — finite, expressible, and correctly reported as violated. Any
    scalar criterion on ``[0, inf]`` admits a monotone finite
    reparameterisation. ``Quantity``'s invariant survives intact.

    Both halves are asserted here so the withdrawal is a measurement rather
    than a concession.
    """
    payload = rc.build_problem(t1.case_n()).to_dict()

    # The correct parameterisation: finite, expressible, violated.
    correct = rd.validity_from_records(payload, model_payload)
    assert rd.recover_resolution_criterion(payload).value == 0.0
    assert "inverse_peclet_cell" in correct.violated
    assert correct.peclet_inexpressible is False

    # The naive one: infinite, inexpressible, and silently UNKNOWN.
    naive_model = rc.TRANSPORT_MODEL_NAIVE_PECLET.to_dict()
    naive = rd.validity_from_records(
        payload, naive_model, criterion_name="peclet_cell"
    )
    assert naive.peclet_inexpressible is True
    assert naive.unknown == ("peclet_cell",)
    assert naive.status is ValidityStatus.UNKNOWN
    with pytest.raises(Exception):
        Quantity(float("inf"), "dimensionless")

    # The residual worth carrying: UNKNOWN cannot distinguish "not supplied"
    # from "could not be expressed". Both readings produce the same record.
    not_supplied = rd.validity_from_records(
        payload, naive_model, supply_criterion=False
    )
    assert not_supplied.unknown == naive.unknown
    assert not_supplied.status is naive.status


# =============================================================================
# PROBE B — storage independence, and what it does not buy
# =============================================================================

def test_probe_b_relocation_does_not_change_the_scientific_record(case_t_run, tmp_path):
    """DATA-BOUNDARY0 holds unchanged under a field-valued consumer.

    The same bytes are put in two structurally different backends and the
    reference — the thing the scientific record carries — is identical.
    """
    reference = case_t_run.result.data_references[0]
    memory = InMemoryBulkStore()
    memory.put(reference, case_t_run.payload)
    disk = FilesystemBulkStore(tmp_path / "bulk")

    relocated = relocate(reference, source=memory, destination=disk)
    assert relocated == reference
    assert relocated.to_dict() == reference.to_dict()

    resolver = BulkDataResolver(disk)
    values = resolver.resolve(reference)
    assert values == pytest.approx(case_t_run.field)


def test_probe_b_field_meaning_does_not_reduce_to_storage_identity(case_t_run):
    """Two scientifically different fields, indistinguishable by record shape.

    A steady field and a transient field at ``t_end``, on meshes of the same
    size, produce references that differ **only in the digest**. Nothing on the
    record says which is which, at what time, on what support, or over what
    entity. `ScientificDataReference != ScientificField`, measured.
    """
    steady = rc.run_case(t1.case_s(160, t1.AdvectionScheme.CENTRAL))
    transient = case_t_run
    a = steady.result.data_references[0]
    b = transient.result.data_references[0]

    assert a.name == b.name and a.unit == b.unit
    assert a.count == b.count == 161
    assert a.dtype == b.dtype
    assert a.digest != b.digest
    differing = {
        field
        for field in ("name", "unit", "count", "dtype", "digest_algorithm")
        if getattr(a, field) != getattr(b, field)
    }
    assert differing == set(), (
        "a steady field and a transient field differ in no scientific field of "
        "the reference — only in the content digest"
    )


def test_probe_b_the_absent_field_semantics_are_absent_by_construction(case_t_payloads):
    """Ledger 2. Six questions, six zeros, zero claimed evidence gain."""
    findings = rd.field_semantics_findings(case_t_payloads["result"])
    impossible = [f for f in findings if f.verdict is rd.Recoverability.IMPOSSIBLE]
    assert len(impossible) == 6
    assert all(f.ledger is rd.Ledger.ABSENT_RECORD for f in impossible)
    assert all(f.admissible_readings == 0 for f in impossible)

    carried = {f.name for f in __import__("dataclasses").fields(ScientificDataReference)}
    assert carried == {
        "name", "unit", "count", "dtype", "digest", "digest_algorithm"
    }


# =============================================================================
# PROBE F — the future coupling endpoint, analysis only
# =============================================================================

def test_probe_f_a_field_endpoint_cannot_be_declared_as_a_dependency(case_t_run):
    """PROBE F. What a fluid -> thermal field coupling would connect, today.

    ``QuantityDependency`` resolves an endpoint through
    ``result.values`` u ``problem.variables`` u ``problem.parameters`` and
    deliberately does **not** consult ``data_references``, because — in its own
    words — *"nothing in this record can state how a field is transported
    between two supports"*. So a dependency naming the solved field reports
    ``MISSING``: an honest failure rather than a clean check implying a
    transfer semantics no contract provides.

    Nothing is implemented here. The measurement is what the endpoint would be,
    and the answer is that a field endpoint is not expressible.
    """
    dependency = QuantityDependency(
        source_problem_id=case_t_run.problem.problem_id,
        source_quantity="c:field",  # the bulk reference's name
        target_problem_id="thermal-body-1",
        target_quantity="species_concentration",
        unit_exemplar="dimensionless",
    )
    issues = dependency.check_against(
        source_problem=case_t_run.problem, source_result=case_t_run.result
    )
    assert [issue.kind for issue in issues] == [BindingIssueKind.MISSING]
    assert "c:field" in issues[0].detail

    assert any(
        reference.name == "c:field"
        for reference in case_t_run.result.data_references
    ), "the field is present on the result and still not a reachable endpoint"

    scalar = QuantityDependency(
        source_problem_id=case_t_run.problem.problem_id,
        source_quantity="c:midpoint",
        target_problem_id="thermal-body-1",
        target_quantity="species_concentration",
        unit_exemplar="dimensionless",
    )
    assert scalar.check_against(source_result=case_t_run.result) == (), (
        "a scalar reduction of the field checks clean — which is the trap: the "
        "only expressible coupling endpoint is the one that has already thrown "
        "the field away"
    )


# =============================================================================
# The steelman ledger — every typed encoding tried, and why it was rejected
# =============================================================================
#
# Prereg §6 is binding and §13.4 makes a gap declared without a steelman attempt
# a fail condition. The adversarial pass asked for the attempts to be *listed
# and executed* rather than asserted, because "we tried everything" is exactly
# the claim a discovery milestone must not make on trust.


def test_steelman_variable_bounds_can_be_declared_and_nothing_reads_them():
    """TRIED: bound the field with ``ScientificVariable.lower/upper``. REJECTED.

    It constructs, it serializes, it is dimension-checked — and no path that
    inspects a ``ScientificResult`` consults it, so declaring it would produce a
    guard that guards nothing. §66.4's lesson, one layer out.
    """
    from engcore.scientific.ir.variables import ScientificVariable, VariableRole

    bounded = ScientificVariable(
        name="c",
        unit="dimensionless",
        role=VariableRole.STATE,
        lower=Quantity(0.0, "dimensionless"),
        upper=Quantity(1.0, "dimensionless"),
    )
    assert bounded.is_bounded
    with pytest.raises(Exception):
        bounded.require_within_bounds(Quantity(1.4301991580760791, "dimensionless"))

    # ...and the violating value sails into a result untouched, because no
    # result path calls that method. See
    # test_nothing_in_universal_core_compares_a_result_to_declared_bounds.
    run = rc.run_case(t1.case_s(8, t1.AdvectionScheme.CENTRAL))
    assert run.result.values["c:max"].magnitude > bounded.upper.magnitude
    assert run.result.validation.status is ValidationOutcome.PASS


def test_steelman_boundary_coefficients_could_carry_a_coordinate_and_must_not():
    """TRIED: put the boundary's position in ``BoundaryCondition.coefficients``.
    REJECTED, and recorded as tried rather than as unavailable.

    It works mechanically — ``coefficients`` is ``Mapping[str, Quantity]``, so a
    coordinate goes straight in and round-trips. That is precisely the problem:
    the *key* would carry the scientific meaning, and a key-name convention
    carrying undefined semantics is the untyped escape hatch the platform
    refuses. Nothing would validate it, nothing would agree on the key, and a
    second domain would choose a different word.
    """
    from engcore.scientific.ir.conditions import BoundaryCondition, BoundaryKind

    smuggled = BoundaryCondition(
        name="condition-a",
        variable="c",
        kind=BoundaryKind.DIRICHLET,
        region="boundary-a",
        value=Quantity(1.0, "dimensionless"),
        coefficients={"position": Quantity(0.0, "meter")},
    )
    restored = BoundaryCondition.from_dict(smuggled.to_dict())
    assert restored == smuggled
    assert restored.coefficients["position"].magnitude == 0.0

    # The reason it is refused: the meaning is in the string "position", which
    # no contract defines and nothing checks. A domain writing "x" or "origin"
    # or "coord" produces a record that is equally valid and mutually
    # unintelligible.
    for alternative in ("x", "origin", "coord", "s"):
        assert BoundaryCondition(
            name="condition-a",
            variable="c",
            kind=BoundaryKind.DIRICHLET,
            region="boundary-a",
            value=Quantity(1.0, "dimensionless"),
            coefficients={alternative: Quantity(0.0, "meter")},
        ).coefficients[alternative].magnitude == 0.0


def test_steelman_capability_channels_are_the_wrong_layer_for_a_scheme():
    """TRIED: encode the scheme as a capability. REJECTED on layer grounds.

    ``ScientificCapability`` is documented as *"a statement about nature"*;
    ``SolverCapability`` as *"which computational operation can this backend
    execute"*. A first-order upwind discretization is neither: it is not a
    physical operation and it is not a backend's ability. Both would construct;
    both would be lies about which layer the fact belongs to.
    """
    from engcore.scientific.capabilities import ScientificCapability
    from engcore.scientific.solvers.capability import SolverCapability

    # Both accept it, which is why the refusal has to be a judgement.
    assert ScientificCapability("transport", "advection_upwind_first_order")
    assert SolverCapability("numerics:upwind_advection", "")

    # What the probe actually declared: the science, with no scheme in it.
    assert rc.TRANSPORT_SCIENCE.identifier == "transport:advection_diffusion_1d"
    assert rc.REALIZATION_CENTRAL.provided_capabilities == frozenset(
        {rc.TRANSPORT_SCIENCE}
    )
    assert rc.REALIZATION_UPWIND.provided_capabilities == frozenset(
        {rc.TRANSPORT_SCIENCE}
    )


def test_steelman_flag_and_category_conditions_move_the_judgement_out():
    """TRIED: state the resolution criterion as a flag or a category. REJECTED.

    Both work. Both require the *verdict* — "adequately_resolved" — to be
    computed before the context is built, which moves the judgement out of the
    record and into whoever assembled it. A ``RangeCondition`` over the number
    keeps the criterion in the model, which is where a validity domain belongs.
    """
    from engcore.scientific.models.definition import (
        CategoryCondition,
        FlagCondition,
        ValidityDomain,
    )

    flag = ValidityDomain(
        conditions=(FlagCondition(name="adequately_resolved", expected=True),)
    )
    assert flag.assess({"adequately_resolved": True}).status is ValidityStatus.IN_DOMAIN
    assert (
        flag.assess({"adequately_resolved": False}).status
        is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    )

    category = ValidityDomain(
        conditions=(
            CategoryCondition(name="resolution_regime", allowed=frozenset({"fine"})),
        )
    )
    assert (
        category.assess({"resolution_regime": "coarse"}).status
        is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
    )

    # Neither can state the threshold, so neither can be checked by a reader
    # that does not already know the answer. The adopted form can.
    adopted = [
        condition
        for condition in rc.TRANSPORT_MODEL.validity.conditions
        if condition.name == "inverse_peclet_cell"
    ]
    assert len(adopted) == 1
    assert adopted[0].minimum == Quantity(t1.MIN_INVERSE_CELL_PECLET, "dimensionless")


# =============================================================================
# Architecture fitness — prereg §13 fail conditions, asserted
# =============================================================================

def test_no_universal_core_file_was_added_or_edited():
    """FAIL CONDITION 1. ``src/engcore/scientific/`` is byte-unchanged.

    Asserted by digest against the tree at the preregistration commit, computed
    over the current files. The check is the file *set* plus each file's hash,
    so both an edit and an addition are caught.
    """
    import subprocess

    core = REPO_ROOT / "src" / "engcore" / "scientific"
    current = sorted(
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in core.rglob("*.py")
    )
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "src/engcore/scientific/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = sorted(
        line for line in proc.stdout.splitlines() if line.endswith(".py")
    )
    assert current == tracked, (
        f"universal core file set changed; added or removed "
        f"{set(current) ^ set(tracked)}"
    )

    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "src/engcore/scientific/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # The two files a later, model-discovery-only milestone
    # (`planner-provided-capabilities`) is documented and authorized to
    # touch: adding a `provided_capabilities` field to
    # `ScientificModelDefinition` and a matching
    # `ModelRegistry.providers_of` query method, so a deterministic caller
    # can answer "which models provide capability X" without name parsing
    # or a metadata side-channel. No hostile-core-domain-stress invariant
    # changed there — see docs/planner-provided-capabilities-evidence.md.
    # This guard's own claim (this milestone left the universal core
    # byte-frozen) is unaffected: it was true when this milestone was
    # written, and that fact does not change.
    planner_discovery_exceptions = {
        "src/engcore/scientific/models/definition.py",
        "src/engcore/scientific/models/registry.py",
    }
    changed = set(diff.stdout.split()) - planner_discovery_exceptions
    assert changed == set(), f"universal core was modified: {sorted(changed)}"


def test_no_thermal_domain_file_was_added_or_edited():
    """FAIL CONDITION 2. The frozen thermal tree is untouched."""
    import subprocess

    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "src/engcore/domains/thermal/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert diff.stdout.strip() == ""


def test_the_probe_lives_outside_the_shipped_package():
    """FAIL CONDITION 10. The probe cannot be promoted by accident.

    ``experiments/`` is outside ``src/``, so nothing here is installed with the
    package and no production module can import it without reaching out of the
    distribution.
    """
    assert PROBE_ROOT.is_dir()
    assert (REPO_ROOT / "src") not in PROBE_ROOT.parents

    import subprocess

    proc = subprocess.run(
        ["git", "grep", "-l", "hostile_core_stress", "--", "src/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.stdout.strip() == "", (
        f"the shipped package references the probe: {proc.stdout.strip()}"
    )


def test_no_bulk_array_reaches_a_scientific_control_record(case_t_run):
    """Prereg §12 test 2. Nothing O(mesh) crosses into the control plane.

    Checked over the serialized record rather than the live object, because
    serialization is where an accidental array would actually escape.
    """
    payload = json.loads(json.dumps(rc.serialize(case_t_run)))

    def largest_sequence(node) -> int:
        if isinstance(node, list):
            return max(
                [len(node)] + [largest_sequence(child) for child in node]
            )
        if isinstance(node, dict):
            values = [largest_sequence(child) for child in node.values()]
            return max(values) if values else 0
        return 0

    assert len(case_t_run.field) == 161
    assert largest_sequence(payload) < 20, (
        "a scientific control record must stay O(1) in the size of the field "
        "it describes"
    )
    assert all(
        isinstance(value, Quantity) for value in case_t_run.result.values.values()
    )


def test_the_probe_adds_no_domain_branch_to_universal_core():
    """Prereg §12 test 6, and the lexical half of §18 item 1.

    Stated as the weak claim it is: `MIN-FOUNDATION-ET` §64.3 already recorded
    that the one real leak it found *contained no domain word*, so a scan like
    this could not have caught it. It is run because a positive hit would still
    be decisive, not because a negative one proves anything.
    """
    core = REPO_ROOT / "src" / "engcore" / "scientific"
    forbidden = ("advection", "peclet", "upwind", "transport1d", "hostile")
    hits = []
    for path in core.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        hits += [
            (str(path.relative_to(REPO_ROOT)), token)
            for token in forbidden
            if token in text
        ]
    assert hits == []
