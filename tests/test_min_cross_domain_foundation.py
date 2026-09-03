"""MIN-CROSS-DOMAIN-FOUNDATION — executed evidence.

Preregistered in ``docs/min-cross-domain-foundation-prereg.md``, committed at
``76f6dd4`` before any implementation source was written. Evidence written
after execution lives in ``docs/min-cross-domain-foundation-evidence.md``.

Three candidates, repeatedly pressured by prior milestones and never built:
Variable<->Bulk Binding, Admissibility Attainment, Enforced Admission. This
module executes the zero-contract attempts preregistered in prereg §4 first,
then exercises what was actually built — ``VariableBulkLinkage`` and
``ValidationReport.require_admission`` — against real, already-existing
consumers (two probes and one production ``src/`` domain), and closes with
the mandatory negative proof (§A5 of the governing task): a result that
fails a declared requirement must be refused, not silently consumed.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from engcore.scientific.errors import (
    InvalidScientificProblem,
    ScientificValidationError,
)
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.variables import (
    ScientificVariable,
    VariableKind,
    VariableRole,
)
from engcore.scientific.models.definition import BindingIssueKind
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.validation import (
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
)
from engcore.scientific.results.variable_binding import (
    VARIABLE_BULK_LINKAGE_SCHEMA,
    VariableBulkLinkage,
    unlinked_references,
)
from engcore.scientific.units.quantity import Quantity, dimensionality

from experiments.cross_domain_coverage import mechanics as mech
from experiments.cross_domain_coverage import species as spc

REPO_ROOT = Path(__file__).resolve().parents[1]

Q = Quantity


def _core_sources() -> list[Path]:
    return sorted((REPO_ROOT / "src" / "engcore" / "scientific").rglob("*.py"))


def _provenance(run_id: str) -> ProvenanceRecord:
    return ProvenanceRecord(run_id=run_id)


# =============================================================================
# PART A — zero-new-contract attempts (prereg §4.1), executed
# =============================================================================

def test_a1_reference_name_alone_is_not_a_typed_cross_reference():
    """Attempt 1: the reference's own free-text name.

    A human reads ``"c:A:trajectory"`` as species A's concentration. A
    records-only reader — one that may inspect ``ScientificVariable`` and
    ``ScientificDataReference`` payloads but never parses a name's internal
    structure or reads domain source — has no typed field connecting that
    string to the declared variable named ``"concentration_A"`` below. This is
    executed, not asserted: the reader function only ever looks at ``.name``
    equality against *declared* variable names, and a name that merely looks
    related is not equal to one.
    """
    reference = ScientificDataReference(
        name="c:A:trajectory", unit="mol/m**3", count=4,
        digest="a" * 64,
    )
    declared_variable_names = {"concentration_A"}

    def records_only_reader_resolves(ref: ScientificDataReference) -> bool:
        """The only legitimate operation: exact-name membership. No parsing."""
        return ref.name in declared_variable_names

    assert records_only_reader_resolves(reference) is False


def test_a2_categorical_variable_gives_ordering_but_not_a_binding():
    """Attempt 2: ``ScientificVariable.categories`` alone.

    Corroborates ``EXEC-SPEC-STRUCTURED`` §F: an ordered named-member set is
    already representable today. It is executed here again because it is the
    steelman this milestone must not skip — and it still does not say that
    any *particular* bulk reference instantiates the variable at all.
    """
    species_axis = ScientificVariable(
        name="species", unit="dimensionless",
        kind=ScientificVariable.__dataclass_fields__["kind"].default.__class__("categorical"),
        categories=("A", "B", "C"),
        role=VariableRole.OBSERVABLE,
    )
    assert species_axis.categories == ("A", "B", "C")
    # Nothing on the variable, or reachable from it, names a
    # ScientificDataReference. The ordering exists; the binding does not.
    assert not hasattr(species_axis, "data_references")
    assert not hasattr(species_axis, "reference")


def test_a3_parameter_carrying_a_reference_name_is_unchecked_data():
    """Attempt 3: a ``ScientificParameter`` holding the reference name.

    Constructible, and that is exactly the problem: nothing about
    ``ScientificParameter`` validates that its string value resolves to an
    existing reference, or is dimensionally consistent with anything.
    """
    from engcore.scientific.ir.variables import ScientificParameter
    from engcore.scientific.ir.values import CategoricalValue

    parameter = ScientificParameter(
        name="field_reference",
        value=CategoricalValue("c:A:trajectory"),
    )
    # It round-trips as a category. It asserts nothing about a reference
    # actually named "c:A:trajectory" existing, being a bulk array, or
    # sharing a dimension with any variable.
    assert parameter.value.value == "c:A:trajectory"


def test_a5_split_per_variable_references_still_need_a_typed_binding():
    """Attempt 5: splitting one combined array into per-variable references.

    Removes the interleaving/stride question (each reference then holds
    exactly one quantity's values), which is why the record built for this
    milestone carries no axis-order field. It does **not** remove the need
    for a typed binding: two references, each named only descriptively,
    still cannot be resolved to declared variables without one — proven
    below by attempting resolution first with no linkage (ambiguous/failed)
    and then with one (succeeds), on the same two records.
    """
    u_x = ScientificVariable(name="u_x", unit="meter", role=VariableRole.OBSERVABLE)
    u_y = ScientificVariable(name="u_y", unit="meter", role=VariableRole.OBSERVABLE)
    ref_x = ScientificDataReference(
        name="u_x:field", unit="meter", count=4, digest="b" * 64
    )
    ref_y = ScientificDataReference(
        name="u_y:field", unit="meter", count=4, digest="c" * 64
    )

    def resolve(reference: ScientificDataReference, variables, linkages):
        matches = [
            l.variable_name for l in linkages if l.reference_name == reference.name
        ]
        if not matches:
            return None
        (name,) = matches
        return next(v for v in variables if v.name == name)

    variables = (u_x, u_y)
    assert resolve(ref_x, variables, ()) is None  # no linkage: unresolved
    linkages = (
        VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field"),
        VariableBulkLinkage(variable_name="u_y", reference_name="u_y:field"),
    )
    assert resolve(ref_x, variables, linkages) is u_x
    assert resolve(ref_y, variables, linkages) is u_y


# =============================================================================
# PART B — VariableBulkLinkage: construction, serialization, checking
# =============================================================================

def test_b1_construction_requires_non_empty_names():
    with pytest.raises(InvalidScientificProblem):
        VariableBulkLinkage(variable_name="", reference_name="x")
    with pytest.raises(InvalidScientificProblem):
        VariableBulkLinkage(variable_name="x", reference_name="   ")


def test_b2_round_trips_through_dict():
    linkage = VariableBulkLinkage(
        variable_name="u_x", reference_name="u_x:field",
        description="component of the shear-case displacement",
    )
    payload = linkage.to_dict()
    assert payload["schema"] == VARIABLE_BULK_LINKAGE_SCHEMA
    assert VariableBulkLinkage.from_dict(payload) == linkage


def test_b3_it_carries_no_field_beyond_two_names_and_prose():
    fields = set(VariableBulkLinkage.__dataclass_fields__)
    assert fields == {"variable_name", "reference_name", "description"}


def test_c1_check_against_reports_missing_variable():
    problem = ScientificProblem(problem_id="p1")  # no variables declared
    linkage = VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field")
    issues = linkage.check_against(problem=problem)
    # MIN-FIELD-SUPPORT-FOUNDATION added ScientificProblem.data_references
    # and extended check_against to resolve reference_name against it (not
    # only against result.data_references) — see
    # docs/min-field-support-foundation-evidence.md. A problem with neither
    # the named variable nor the named reference now correctly reports BOTH
    # as missing, not only the variable: passing problem= alone used to skip
    # reference resolution entirely (it only ever looked at a `result`),
    # which is exactly the residue this milestone closed.
    assert len(issues) == 2
    assert all(issue.kind is BindingIssueKind.MISSING for issue in issues)
    assert {issue.name for issue in issues} == {"u_x", "u_x:field"}


def test_c2_check_against_reports_missing_reference():
    result = ScientificResult(
        result_id="r1", values={}, provenance=_provenance("r1")
    )
    linkage = VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field")
    issues = linkage.check_against(result=result)
    assert len(issues) == 1
    assert issues[0].kind is BindingIssueKind.MISSING


def test_c3_check_against_reports_wrong_dimension():
    problem = ScientificProblem(
        problem_id="p1",
        variables=(
            ScientificVariable(
                name="u_x", unit="volt", role=VariableRole.OBSERVABLE
            ),
        ),
    )
    reference = ScientificDataReference(
        name="u_x:field", unit="meter", count=4, digest="d" * 64
    )
    result = ScientificResult(
        result_id="r1", values={}, data_references=(reference,),
        provenance=_provenance("r1"),
    )
    linkage = VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field")
    issues = linkage.check_against(problem=problem, result=result)
    assert len(issues) == 1
    assert issues[0].kind is BindingIssueKind.WRONG_DIMENSION


def test_c4_check_against_is_clean_when_both_resolve_and_agree():
    problem = ScientificProblem(
        problem_id="p1",
        variables=(
            ScientificVariable(
                name="u_x", unit="meter", role=VariableRole.OBSERVABLE
            ),
        ),
    )
    reference = ScientificDataReference(
        name="u_x:field", unit="meter", count=4, digest="e" * 64
    )
    result = ScientificResult(
        result_id="r1", values={}, data_references=(reference,),
        provenance=_provenance("r1"),
    )
    linkage = VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field")
    assert linkage.check_against(problem=problem, result=result) == ()


def test_c5_absent_arguments_check_nothing():
    linkage = VariableBulkLinkage(variable_name="u_x", reference_name="u_x:field")
    assert linkage.check_against() == ()


# =============================================================================
# PART D — mechanics probe (rank-1 nodal displacement, real physics)
# =============================================================================

def _mechanics_problem_and_result():
    """Build real records from the shear case, split per component.

    Mirrors zero-contract attempt 5: rather than one 8-value array needing an
    axis-order statement, two 4-value arrays (u_x, u_y over the four nodes)
    each need only a name.
    """
    case = mech.run_shear_case()
    displacement = case["displacement"]
    u_x = tuple(displacement[2 * n] for n in range(mech.N_NODES))
    u_y = tuple(displacement[2 * n + 1] for n in range(mech.N_NODES))

    problem = ScientificProblem(
        problem_id="mechanics-shear",
        variables=(
            ScientificVariable(
                name="displacement_x", unit="meter", role=VariableRole.OBSERVABLE,
                description="x-displacement at each node, node-major order",
            ),
            ScientificVariable(
                name="displacement_y", unit="meter", role=VariableRole.OBSERVABLE,
                description="y-displacement at each node, node-major order",
            ),
        ),
    )
    ref_x, _ = ScientificDataReference.for_values(
        "u_x:field", u_x, unit="meter"
    )
    ref_y, _ = ScientificDataReference.for_values(
        "u_y:field", u_y, unit="meter"
    )
    result = ScientificResult(
        result_id="mechanics-shear-run",
        problem_id=problem.problem_id,
        values={},
        data_references=(ref_x, ref_y),
        provenance=_provenance("mechanics-shear-run"),
    )
    linkages = (
        VariableBulkLinkage(
            variable_name="displacement_x", reference_name="u_x:field"
        ),
        VariableBulkLinkage(
            variable_name="displacement_y", reference_name="u_y:field"
        ),
    )
    return problem, result, linkages


def test_d1_mechanics_linkages_check_clean():
    problem, result, linkages = _mechanics_problem_and_result()
    for linkage in linkages:
        assert linkage.check_against(problem=problem, result=result) == ()


def test_d2_mechanics_unlinked_references_is_empty_once_both_are_bound():
    problem, result, linkages = _mechanics_problem_and_result()
    assert unlinked_references(result, linkages) == ()


def test_d3_mechanics_missing_one_linkage_is_measured_not_hidden():
    problem, result, linkages = _mechanics_problem_and_result()
    assert unlinked_references(result, linkages[:1]) == ("u_y:field",)


# =============================================================================
# PART E — species probe (state trajectory, real physics)
# =============================================================================

def _species_problem_and_result():
    case = spc.case_c_linear(n_steps=50)
    _, trajectory = spc.integrate(case)
    # Split per species: three separate references, each the trajectory of
    # one named quantity, sharing the same implicit time index — exactly the
    # reduction attempt 5 in the prereg.
    by_species = {
        name: tuple(state[i] for state in trajectory)
        for i, name in enumerate(spc.SPECIES)
    }
    problem = ScientificProblem(
        problem_id="species-batch",
        variables=tuple(
            ScientificVariable(
                name=f"concentration_{name}", unit="mol/m**3",
                role=VariableRole.STATE,
                description=f"trajectory of species {name}",
            )
            for name in spc.SPECIES
        ),
    )
    references = tuple(
        ScientificDataReference.for_values(
            f"c_{name}:trajectory", values, unit="mol/m**3"
        )[0]
        for name, values in by_species.items()
    )
    result = ScientificResult(
        result_id="species-batch-run", problem_id=problem.problem_id,
        values={}, data_references=references,
        provenance=_provenance("species-batch-run"),
    )
    linkages = tuple(
        VariableBulkLinkage(
            variable_name=f"concentration_{name}", reference_name=f"c_{name}:trajectory"
        )
        for name in spc.SPECIES
    )
    return problem, result, linkages


def test_e1_species_linkages_check_clean():
    problem, result, linkages = _species_problem_and_result()
    for linkage in linkages:
        assert linkage.check_against(problem=problem, result=result) == ()


def test_e2_species_and_mechanics_force_the_same_residue():
    """H1's falsification condition: do the two consumers force the SAME
    shape of binding record, or does one need something the other does not?

    Both close with the identical two-field record and identical
    ``check_against`` call shape — no consumer-specific field was added for
    either.
    """
    _, _, mech_linkages = _mechanics_problem_and_result()
    _, _, species_linkages = _species_problem_and_result()
    for linkage in (*mech_linkages, *species_linkages):
        assert isinstance(linkage, VariableBulkLinkage)
        assert set(linkage.to_dict()) == {
            "schema", "variable_name", "reference_name", "description",
        }


# =============================================================================
# PART F — real production consumer: thermal_conduction1d_bulk
# =============================================================================

def test_f1_the_shipped_slab_problem_declares_no_variable_for_its_own_field():
    """The strongest real-world corroboration: the one existing ``src/``
    producer of a ``ScientificDataReference`` pairs it with a problem that
    does not declare a variable for the field at all — only two scalar
    summaries (``u:midpoint``, ``u:max_abs``). A records-only reader cannot
    even get as far as a dimension mismatch; the target is simply absent.

    This is measured against the frozen, byte-pinned tree exactly as shipped
    — nothing here edits it.
    """
    from engcore.domains.thermal.conduction1d import (
        ConductionSlab, SlabDiscretization, build_conduction_problem,
    )
    from engcore.domains.thermal_conduction1d_bulk import (
        FIELD_DATA_NAME, solve_slab_with_bulk_field,
    )

    slab = ConductionSlab(
        slab_id="mincross-f1", length=Q(1.0, "meter"),
        diffusivity=Q(1.0e-4, "m**2/s"), end_time=Q(2.0, "second"),
        discretization=SlabDiscretization(n_cells=20, n_steps=40),
    )
    problem = build_conduction_problem(slab)
    result, _store = solve_slab_with_bulk_field(slab, run_id="mincross-f1-run")

    linkage = VariableBulkLinkage(
        variable_name="u", reference_name=FIELD_DATA_NAME
    )
    issues = linkage.check_against(problem=problem, result=result)
    assert len(issues) == 1
    assert issues[0].kind is BindingIssueKind.MISSING
    assert issues[0].name == "u"


def test_f2_augmenting_the_problem_with_the_missing_variable_closes_it():
    """Not an edit to the frozen tree: a second, equivalent problem built in
    this test, carrying the one additional declaration the shipped problem
    omits. Proves the gap is closeable with today's contracts once a domain
    chooses to declare the variable — the binding record does the rest.
    """
    from engcore.domains.thermal.conduction1d import (
        ConductionSlab, SlabDiscretization,
    )
    from engcore.domains.thermal.conduction1d.problem import FIELD_UNIT
    from engcore.domains.thermal_conduction1d_bulk import (
        FIELD_DATA_NAME, solve_slab_with_bulk_field,
    )

    slab = ConductionSlab(
        slab_id="mincross-f2", length=Q(1.0, "meter"),
        diffusivity=Q(1.0e-4, "m**2/s"), end_time=Q(2.0, "second"),
        discretization=SlabDiscretization(n_cells=20, n_steps=40),
    )
    augmented_problem = ScientificProblem(
        problem_id="mincross-f2-augmented",
        variables=(
            ScientificVariable(
                name="u", unit=FIELD_UNIT, role=VariableRole.OBSERVABLE,
                description="the normalized field this bulk reference holds",
            ),
        ),
    )
    result, _store = solve_slab_with_bulk_field(slab, run_id="mincross-f2-run")
    linkage = VariableBulkLinkage(
        variable_name="u", reference_name=FIELD_DATA_NAME
    )
    assert linkage.check_against(problem=augmented_problem, result=result) == ()


def test_f3_wrong_dimension_is_still_caught_on_the_real_producer():
    from engcore.domains.thermal.conduction1d import (
        ConductionSlab, SlabDiscretization,
    )
    from engcore.domains.thermal_conduction1d_bulk import (
        FIELD_DATA_NAME, solve_slab_with_bulk_field,
    )

    slab = ConductionSlab(
        slab_id="mincross-f3", length=Q(1.0, "meter"),
        diffusivity=Q(1.0e-4, "m**2/s"), end_time=Q(2.0, "second"),
        discretization=SlabDiscretization(n_cells=20, n_steps=40),
    )
    wrong_unit_problem = ScientificProblem(
        problem_id="mincross-f3-wrong",
        variables=(
            ScientificVariable(name="u", unit="kelvin", role=VariableRole.OBSERVABLE),
        ),
    )
    result, _store = solve_slab_with_bulk_field(slab, run_id="mincross-f3-run")
    linkage = VariableBulkLinkage(variable_name="u", reference_name=FIELD_DATA_NAME)
    issues = linkage.check_against(problem=wrong_unit_problem, result=result)
    assert len(issues) == 1 and issues[0].kind is BindingIssueKind.WRONG_DIMENSION


# =============================================================================
# PART G — cross-domain isolation and reduction attacks
# =============================================================================

def test_g1_a_domain_pair_this_milestone_never_imports_can_use_the_record():
    """Mirrors MIN-FOUNDATION-ET's test_d3 and EXEC-SPEC-STRUCTURED's
    isolation guard: nothing about the record depends on which two sciences
    are involved."""
    linkage = VariableBulkLinkage(
        variable_name="shaft_torque_history", reference_name="mechanical:trace"
    )
    assert VariableBulkLinkage.from_dict(linkage.to_dict()) == linkage


def test_g2_no_domain_vocabulary_in_the_new_module():
    """Same word list ``MIN-FOUNDATION-ET``'s ``test_d2`` already established
    for ``composition/`` — the terms that identify a *physical domain's*
    vocabulary, not every English word a docstring's illustrative examples
    happen to use (this record's own docstring names its forcing consumers
    by description, exactly as every other milestone's evidence prose does;
    that is documentation, not a domain branch in the contract)."""
    path = REPO_ROOT / "src/engcore/scientific/results/variable_binding.py"
    text = path.read_text(encoding="utf-8").lower()
    for word in (
        "electrical", "thermal", "resistor", "resistance", "joule",
        "voltage", "ampere", "ohm", "watt", "temperature", "heat",
        "circuit", "conductor", "dissipation",
    ):
        assert word not in text, f"{word!r} leaked into variable_binding.py"


def test_g3_reuses_binding_issue_no_parallel_issue_type_was_minted():
    """R4: no duplication of an existing record."""
    source = (
        REPO_ROOT / "src/engcore/scientific/results/variable_binding.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    # The only class defined in this module is the linkage itself; the issue
    # vocabulary is imported, not redefined.
    assert class_names == {"VariableBulkLinkage"}
    assert "from ..models.definition import BindingIssue, BindingIssueKind" in source


def test_g4_no_field_beyond_two_names_and_prose_r1():
    """R1: remove any candidate extra field (axis order, stride, component)
    and show nothing here ever needed one — the dataclass fields are the
    complete inventory, asserted in test_b3, and every consumer in Parts D-F
    closed using only ``variable_name``/``reference_name``."""
    assert set(VariableBulkLinkage.__dataclass_fields__) == {
        "variable_name", "reference_name", "description",
    }


def test_g5_frozen_domain_trees_are_byte_unchanged():
    for path in (
        "src/engcore/domains/thermal/conduction1d/",
        "src/engcore/domains/kinetics/cstr/",
        "src/engcore/domains/electrical/dc/",
        "experiments/cross_domain_coverage/mechanics.py",
        "experiments/cross_domain_coverage/species.py",
    ):
        diff = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", path],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        )
        assert diff.stdout.strip() == "", f"{path} was modified: {diff.stdout}"


def test_g6_no_schema_string_moved():
    """Only ``variable_bulk_linkage/1`` is new at THIS milestone. Every
    existing schema string this milestone touches (results/validation.py,
    results/__init__.py, the package __init__) is unchanged.

    ``PROBLEM_SCHEMA`` is the one documented exception, added later by
    `MIN-FIELD-SUPPORT-FOUNDATION`: an additive ``data_references`` field
    bumped it to ``scientific_problem/2``, with the reader still accepting
    ``/1`` — see docs/min-field-support-foundation-evidence.md. This test's
    own claim (nothing else in this list moved) is otherwise unaffected.
    """
    from engcore.scientific.results.data_reference import DATA_REFERENCE_SCHEMA
    from engcore.scientific.results.result import RESULT_SCHEMA
    from engcore.scientific.results.validation import CHECK_SCHEMA, REPORT_SCHEMA
    from engcore.scientific.ir.problem import PROBLEM_SCHEMA

    assert DATA_REFERENCE_SCHEMA == "scientific_data_reference/1"
    assert RESULT_SCHEMA == "scientific_result/2"
    assert CHECK_SCHEMA == "validation_check/1"
    assert REPORT_SCHEMA == "validation_report/1"
    assert PROBLEM_SCHEMA == "scientific_problem/2"
    assert VARIABLE_BULK_LINKAGE_SCHEMA == "variable_bulk_linkage/1"


# =============================================================================
# PART H — H2: no new ValidationLevel member; the real asymmetry, measured
# =============================================================================

def test_h1_validation_level_has_no_admissibility_member():
    names = {level.value for level in ValidationLevel}
    assert not any("admiss" in name for name in names)
    assert names == {
        "unverified", "dimensionally_valid", "numerically_converged",
        "analytically_verified", "benchmark_validated",
        "cross_solver_validated", "experimentally_validated",
    }


def test_h2_a_passing_admissibility_check_establishes_nothing_by_design():
    """Reproduces the asymmetry HOSTILE-CORE-STRESS and CROSS-DOMAIN-COVERAGE
    both measured: an admissibility check can PASS and still contribute no
    attained level, because none exists for it to attain. This is not a bug
    this milestone fixes — H2 rejects a new level — it is the fact that
    forces the enforcement primitive in Part I instead."""
    check = ValidationCheck(
        name="state_physically_admissible", outcome=ValidationOutcome.PASS,
        establishes=None,
    )
    report = ValidationReport(checks=(check,))
    assert report.attained_levels == frozenset()
    assert report.status is ValidationOutcome.PASS


def _benign_cstr_run():
    """A small, real reactor run, built entirely through the
    ``engcore.*``-prefixed import path so every ``Quantity``/``isinstance``
    check downstream resolves against one class object. (Reusing the
    ``src.engcore.*``-prefixed fixtures from ``tests/domains/kinetics`` would
    mix two distinct import paths the project's ``pythonpath`` both expose
    for the same module, which ``isinstance`` cannot see through — this is
    an environment fact, not a contract one, and is worked around here by
    not mixing the two paths rather than by touching either.)"""
    from engcore.domains.kinetics.cstr.problem import (
        ReactorChemistry, ReactorOperation, ReactorRun,
    )

    chemistry = ReactorChemistry(
        k0=Q(7.2e10 / 60.0, "1/s"),
        activation_energy=Q(8750.0 * 8.314462618, "J/mol"),
        heat_of_reaction=Q(-5.0e4, "J/mol"),
        density=Q(1000.0, "kg/m**3"),
        heat_capacity=Q(239.0, "J/(kg*K)"),
    )
    operation = ReactorOperation(
        volume=Q(0.1, "m**3"), flow_rate=Q(0.1 / 60.0, "m**3/s"),
        feed_concentration=Q(1000.0, "mol/m**3"),
        feed_temperature=Q(350.0, "kelvin"),
        coolant_temperature=Q(290.0, "kelvin"),
        ua=Q(5.0e4 / 60.0, "W/K"), end_time=Q(1800.0, "second"),
    )
    return ReactorRun(
        run_label="mincross-benign", chemistry=chemistry, operation=operation,
        initial_concentration=Q(1000.0, "mol/m**3"),
        initial_temperature=Q(300.0, "kelvin"),
    )


def test_h3_the_real_cstr_domain_already_declares_the_correspondence():
    """The exact unconsumed field this milestone spends: three shipped
    domains populate ``validation_requirements`` with names that are the
    literal ``ValidationCheck.name`` values their own validators produce."""
    from engcore.domains.kinetics.cstr.problem import build_cstr_problem

    problem = build_cstr_problem(_benign_cstr_run(), problem_id="h3-declared")
    assert problem.validation_requirements == frozenset(
        {
            "dimensional_consistency", "integration_reported_success",
            "state_physically_admissible", "trajectory_finite",
        }
    )


# =============================================================================
# PART I — Enforced Admission: require_admission, real and constructed
# =============================================================================

def test_i1_require_admission_passes_a_clean_report():
    report = ValidationReport(
        checks=(
            ValidationCheck(name="a", outcome=ValidationOutcome.PASS),
            ValidationCheck(name="b", outcome=ValidationOutcome.PASS),
        )
    )
    report.require_admission({"a", "b"})  # must not raise


def test_i2_require_admission_raises_on_fail():
    report = ValidationReport(
        checks=(ValidationCheck(name="a", outcome=ValidationOutcome.FAIL),)
    )
    with pytest.raises(ScientificValidationError):
        report.require_admission({"a"})


def test_i3_require_admission_treats_not_run_as_unsatisfied():
    """The same 'NOT_RUN is not PASS' principle this module already states
    for ``ValidationLevel``, applied to a named requirement instead."""
    report = ValidationReport(
        checks=(ValidationCheck(name="a", outcome=ValidationOutcome.NOT_RUN),)
    )
    with pytest.raises(ScientificValidationError):
        report.require_admission({"a"})


def test_i4_require_admission_raises_on_a_missing_requirement():
    report = ValidationReport(checks=())
    with pytest.raises(ScientificValidationError):
        report.require_admission({"never_declared"})


def test_i5_admission_issues_and_is_admissible_agree_with_require_admission():
    report = ValidationReport(
        checks=(ValidationCheck(name="a", outcome=ValidationOutcome.WARNING),)
    )
    assert report.admission_issues({"a"}) == ("'a': warning",)
    assert report.is_admissible({"a"}) is False
    with pytest.raises(ScientificValidationError):
        report.require_admission({"a"})


def test_i6_a_real_cstr_solve_passes_its_own_declared_requirements():
    """Positive integration proof against real production code, not just a
    constructed report: a benign CSTR solve satisfies every name its own
    problem declares required."""
    from engcore.domains.kinetics.cstr.problem import build_cstr_problem
    from engcore.domains.kinetics.cstr.solver import solve_reactor

    run = _benign_cstr_run()
    problem = build_cstr_problem(run, problem_id="i6-benign")
    result = solve_reactor(run, run_id="i6-benign-run", problem=problem)
    result.validation.require_admission(problem.validation_requirements)


# =============================================================================
# PART J — A5, the mandatory negative proof
# =============================================================================

def _cstr_like_result_with_a_failed_declared_requirement() -> tuple[
    ScientificProblem, ScientificResult
]:
    """A ScientificResult with plausible-looking numeric values and one
    declared requirement that failed — modelled on two already-executed
    incidents: HETERO-NGSPICE's halved-power provider (§8.4, 18.05 K of
    wrong physics admitted) and kinetics/cstr's own
    ``state_physically_admissible`` check (a negative concentration)."""
    problem = ScientificProblem(
        problem_id="j-negative-proof",
        variables=(
            ScientificVariable(
                name="C_A:final", unit="mol/m**3", role=VariableRole.OBSERVABLE
            ),
        ),
        validation_requirements=frozenset({"state_physically_admissible"}),
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="state_physically_admissible",
                outcome=ValidationOutcome.FAIL,
                detail="concentration reached -3.1 mol/m**3, below the "
                "physical floor of zero",
                establishes=None,
            ),
        )
    )
    result = ScientificResult(
        result_id="j-negative-proof-run",
        problem_id=problem.problem_id,
        # Plausible-looking: a finite, ordinarily-shaped number. The
        # violation is in the *trajectory* the check inspected, not in the
        # sign of the final value reported here — exactly as in the CSTR
        # domain, where a bad trajectory can still report a completed solve.
        values={"C_A:final": Q(2.5, "mol/m**3")},
        convergence=result_convergence(),
        validation=report,
        provenance=_provenance("j-negative-proof-run"),
    )
    return problem, result


def result_convergence():
    from engcore.scientific.solvers.protocol import ConvergenceState
    return ConvergenceState.CONVERGED


def test_j1_unguarded_consumption_silently_proceeds_on_bad_admissibility():
    """The forbidden outcome, proven to be real and structural absent the
    guard — mirrors the 'before fixing' measurement in
    docs/heterogeneous-ngspice-evidence.md §8.4. This is not a defect
    introduced by this milestone: it is the baseline behaviour of
    ``ScientificResult`` today, executed here as the negative control the
    mandatory proof requires."""
    problem, result = _cstr_like_result_with_a_failed_declared_requirement()

    def unguarded_downstream_consumer(problem, result):
        # Exactly what a coupling/inference loop does today: read the value.
        # No admission check. This is the pattern HETERO-NGSPICE measured
        # transporting 18.05 K of wrong physics.
        return result.value("C_A:final").magnitude_in("mol/m**3")

    # It "succeeds" — silently, on a result whose declared requirement failed.
    consumed = unguarded_downstream_consumer(problem, result)
    assert consumed == pytest.approx(2.5)
    # The failure is real and was available the whole time; nothing forced
    # anyone to look at it.
    assert result.validation.status is ValidationOutcome.FAIL
    assert result.is_usable is False


def test_j2_guarded_consumption_is_refused_before_the_value_is_read():
    """The required outcome: FAIL -> deterministic refusal, raised and
    caught, proving the downstream path never reaches its use of the value."""
    problem, result = _cstr_like_result_with_a_failed_declared_requirement()
    reached_use = {"value": False}

    def guarded_downstream_consumer(problem, result):
        result.validation.require_admission(
            problem.validation_requirements,
            context=f"result {result.result_id!r}",
        )
        reached_use["value"] = True  # must never execute
        return result.value("C_A:final").magnitude_in("mol/m**3")

    with pytest.raises(ScientificValidationError) as excinfo:
        guarded_downstream_consumer(problem, result)

    assert reached_use["value"] is False
    assert "state_physically_admissible" in str(excinfo.value)


def test_j3_a_passing_requirement_is_not_refused():
    """The guard is not a blanket refusal — a genuinely satisfied requirement
    consumes normally, proving this is admission, not paranoia."""
    problem = ScientificProblem(
        problem_id="j3-clean",
        variables=(
            ScientificVariable(
                name="C_A:final", unit="mol/m**3", role=VariableRole.OBSERVABLE
            ),
        ),
        validation_requirements=frozenset({"state_physically_admissible"}),
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="state_physically_admissible", outcome=ValidationOutcome.PASS,
            ),
        )
    )
    result = ScientificResult(
        result_id="j3-clean-run", problem_id=problem.problem_id,
        values={"C_A:final": Q(2.5, "mol/m**3")},
        convergence=result_convergence(), validation=report,
        provenance=_provenance("j3-clean-run"),
    )

    def guarded_downstream_consumer(problem, result):
        result.validation.require_admission(problem.validation_requirements)
        return result.value("C_A:final").magnitude_in("mol/m**3")

    assert guarded_downstream_consumer(problem, result) == pytest.approx(2.5)


# =============================================================================
# PART K — SRIA admission is a different concern, not unified with this
# =============================================================================

def test_k1_sria_admission_and_scientific_admission_share_no_type():
    """Do NOT conflate scientific-result admission with SRIA evidence
    admission (per the governing task). Measured: the two vocabularies share
    no dataclass, no schema, no error type and no method name."""
    from engcore.sria import admission as sria_admission

    sria_schema_strings = {
        sria_admission.ADMISSION_SCHEMA,
        sria_admission.DECISION_BINDING_SCHEMA,
        sria_admission.ADMISSION_ATTEMPT_SCHEMA,
    }
    assert VARIABLE_BULK_LINKAGE_SCHEMA not in sria_schema_strings
    assert "scientific_result" not in " ".join(sria_schema_strings)

    # SRIA's declaration authenticates an ISSUER (HMAC signature, one-way
    # authorization commitment) over an EVIDENCE RECORD; nothing here has, or
    # needs, an issuer, a signature, or an authorization commitment. Fields,
    # not prose:
    sria_fields = set(sria_admission.AdmissionDeclaration.__dataclass_fields__)
    admission_fields = {"admitted", "issuer_id", "issued_signature", "arbiter_id"}
    assert admission_fields <= sria_fields
    assert admission_fields.isdisjoint(
        set(ValidationReport.__dataclass_fields__)
    )


def test_k2_the_shared_invariant_is_a_principle_not_a_type():
    """Both fail closed on an unmet declared requirement — that is the only
    thing genuinely shared, and it is a design principle each implements
    independently in its own vocabulary, not a contract either could reuse
    from the other without importing a governance layer into scientific
    core (forbidden) or an authentication layer into a solver result
    (unjustified by any evidence here)."""
    from engcore.sria.admission import AdmissionAuthority, AdmissionAuthorityRegistry

    registry = AdmissionAuthorityRegistry()
    # An unverifiable declaration is refused, exactly as an unsatisfied
    # scientific requirement is refused — independently implemented.
    from engcore.sria.admission import AdmissionDeclaration

    bad = AdmissionDeclaration(admitted=True, arbiter_id="nobody")
    attempt = registry.verify(bad, subject_record_hash="x" * 64)
    assert attempt.succeeded is False


# =============================================================================
# PART L — architecture non-goals held
# =============================================================================

def test_l1_no_field_shape_mesh_or_topology_concept_was_added():
    for path in _core_sources():
        text = path.read_text(encoding="utf-8")
        for forbidden in (
            "class ScientificField", "class MatrixValue",
            "class StructuredScientificValue", "class Topology",
            "class Mesh", "class ExecutableScientificSpecification",
        ):
            assert forbidden not in text, f"{forbidden} found in {path.name}"


def test_l2_no_bulk_array_reaches_a_scientific_control_record():
    problem, result, linkages = _species_problem_and_result()
    longest = 0
    for linkage in linkages:
        blob = repr(linkage.to_dict())
        longest = max(longest, len(blob))
    assert longest < 500  # two names and prose; nowhere near O(steps)
    problem_blob = repr(problem.to_dict())
    assert "0.8" not in problem_blob or len(problem_blob) < 5000
