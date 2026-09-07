"""CORE-MECHANISMS — six mechanisms every domain inherits.

A domain defect belongs to one domain. A core defect is silently in all five
domains and in the sixth nobody has written yet. Everything measured here is
core: the unit registry, the applicability field, the routes to a
``ValidationCheck``, construction-time serializability, dependency existence,
and declared cross-domain transfer.

Each guard in this module was **observed failing before it was written to
pass**. A check that cannot fail is indistinguishable from one that passes,
and one that cannot pass measures nothing; the mutations in
``tests/mutation_guards.py`` are how that stays true after today.
"""

from __future__ import annotations

import copy
import pathlib
import subprocess
import sys

import pytest

from core_mechanisms_scope import BASE, CORE_FILES
from engcore.scientific.errors import ScientificCoreError, UnitRegistryFrozen
from engcore.scientific.units.quantity import (
    Quantity,
    _mutator_names,
    _NOT_MUTATORS,
    registry,
    require_pristine_registry,
    units_fingerprint,
)

# =====================================================================
# THE DECLARED SCOPE
#
# Eleven historical guards assert the universal core is byte-untouched. This
# milestone changes the core on purpose, so each of them subtracts one shared
# list. That list is a single point of weakening, so it is a claim rather than
# a licence: it must match the tree exactly, in both directions.
# =====================================================================


def test_the_declared_core_scope_matches_the_tree_exactly():
    """No undeclared core edit, and no dead entry in the exception list.

    The first direction is what the eleven guards were protecting. The second
    is what stops the list becoming a place to park a name that quietly
    exempts a file nothing actually changed.
    """
    changed = {
        line.strip()
        for line in subprocess.run(
            ["git", "diff", "--name-only", BASE, "HEAD", "--",
             "src/engcore/scientific/"],
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    }
    # ...and the working tree, so an uncommitted core edit is just as loud.
    changed |= {
        line[3:].strip().strip('"')
        for line in subprocess.run(
            ["git", "status", "--porcelain", "--", "src/engcore/scientific/"],
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    }
    assert changed - CORE_FILES == set(), sorted(changed - CORE_FILES)
    assert CORE_FILES - changed == set(), sorted(CORE_FILES - changed)


# =====================================================================
# TASK 1 — the shared UnitRegistry
#
# The decision: an ENFORCED REFUSAL to allow registry mutation, not per-run
# isolation. Isolation is only needed when state can change; if it cannot,
# a shared registry is observationally identical to a per-run one, because
# unit algebra over a fixed definition set is a pure function of
# (magnitude, unit string). A fresh registry was measured at 101.8 ms and
# buys nothing sealing does not already give.
#
# The cost, stated rather than discovered later: a domain that needs a unit
# pint does not define cannot add one at runtime.
# =====================================================================


def test_the_registry_refuses_to_define_a_new_unit():
    """The route that changes what a later run can even parse."""
    with pytest.raises(UnitRegistryFrozen) as excinfo:
        registry().define("widget = 5 * meter")
    assert "sealed" in str(excinfo.value)


def test_the_registry_refuses_to_redefine_an_existing_unit():
    """The dangerous route: it changes an answer without changing a count.

    Measured on pint 0.25.3 against an unsealed registry — redefining
    ``millivolt`` turns ``1 V -> 1000 mV`` into ``1 V -> 1000000 mV``, with
    ``len(_units)`` unchanged. That is a wrong number someone builds on.
    """
    before = Quantity(1.0, "volt").to("millivolt").magnitude
    with pytest.raises(UnitRegistryFrozen):
        registry().define("millivolt = 1e-6 * volt = mV")
    assert Quantity(1.0, "volt").to("millivolt").magnitude == before == 1000.0


def test_the_seal_survives_the_reference_pint_hands_back():
    """A wrapper would not be enough, so the seal is not a wrapper.

    ``registry().Quantity(...)._REGISTRY`` **is** the real registry object.
    Every quantity this module has ever returned carried one, so a proxy
    around ``registry()`` would be bypassed by any code holding a quantity.
    """
    leaked = registry().Quantity(1.0, "volt")._REGISTRY
    assert leaked is registry()
    with pytest.raises(UnitRegistryFrozen):
        leaked.define("widget = 5 * meter")


def test_every_mutator_shaped_member_is_sealed():
    """Not a hand-maintained list of method names.

    The seal is applied by matching name shapes against ``dir(registry)``, so
    a mutator introduced by a future pint release is sealed the moment it
    appears rather than the moment somebody remembers it. This asserts the
    sweep actually found members and actually replaced them.
    """
    names = _mutator_names(registry())
    assert len(names) >= 10, names
    assert "define" in names
    sealed = [n for n in names if n not in _NOT_MUTATORS]
    for name in sealed:
        with pytest.raises(UnitRegistryFrozen):
            getattr(registry(), name)()


def test_offset_and_log_unit_arithmetic_still_works():
    """The seal must not break reads that merely LOOK like writes.

    ``_add_ref_of_log_or_offset_unit`` matches the ``_add_`` shape and writes
    nothing — it returns a ``UnitsContainer``. Sealing it broke every degC
    conversion in the suite, which is how it was found. An over-broad seal
    fails loudly; a missed mutator would not. This keeps the loud failure
    available rather than relying on someone re-running the whole suite.
    """
    assert Quantity(0.0, "degC").to("kelvin").magnitude == pytest.approx(273.15)
    assert Quantity(100.0, "degC").to("degF").magnitude == pytest.approx(212.0)
    require_pristine_registry(context="after offset-unit arithmetic")


def test_lazy_prefix_expansion_is_not_mistaken_for_a_mutation():
    """pint materializes ``millivolt`` into ``_units`` on first use.

    That is an expansion of the sealed prefix ``milli`` and the sealed unit
    ``volt``, not a new definition. If the guard could not tell the two
    apart it would fire on ordinary arithmetic and be switched off.
    """
    for expression in (
        "millivolt", "mV", "kilometer", "MPa", "kohm", "GHz", "uA",
        "picofarad", "mol/m**3", "W/(m*K)", "kg/m**3", "centipoise",
    ):
        registry().Unit(expression)
    require_pristine_registry(context="after lazy expansion")


def test_the_content_check_catches_what_no_seal_can_block():
    """A direct write into ``_units`` calls no method, so no seal stops it.

    This is the difference between a guard that knows the ways in and one
    that knows the answer. Both are here on purpose: the seal refuses at the
    moment of mutation, and this refuses at the next run boundary whatever
    route was used.
    """
    units = registry()._units
    units["widget"] = units["meter"]
    try:
        with pytest.raises(UnitRegistryFrozen) as excinfo:
            require_pristine_registry(context="run 2")
        assert "widget" in str(excinfo.value)
    finally:
        units.pop("widget", None)
    require_pristine_registry()


def test_a_changed_definition_is_caught_and_an_equal_rebinding_is_not():
    """Equality, not identity — and the reason is pint's own behaviour.

    Parsing ``kg/m**3`` makes pint REBIND ``_units['kilogram']`` to a new
    but value-equal ``UnitDefinition``. An identity comparison fires on that,
    i.e. on correct arithmetic, and a guard that fires on correct work gets
    switched off. A real redefinition changes the converter
    (``scale=0.001`` -> ``scale=1e-06``) and is not equal, so equality
    separates the two exactly.
    """
    units = registry()._units
    original = units["volt"]

    # An equal rebinding — what pint itself does — must NOT be reported.
    units["volt"] = copy.copy(original)
    try:
        require_pristine_registry()
    finally:
        units["volt"] = original

    # A changed definition must be.
    import dataclasses

    units["volt"] = dataclasses.replace(original, defined_symbol="VV")
    try:
        with pytest.raises(UnitRegistryFrozen) as excinfo:
            require_pristine_registry()
        assert "volt" in str(excinfo.value)
    finally:
        units["volt"] = original
    require_pristine_registry()


def test_pint_definitions_are_still_frozen():
    """The premise the value comparison rests on, asserted rather than
    assumed.

    The sealed baseline holds the definition OBJECTS. That is only sound
    while they cannot change in place — an in-place edit would move both
    sides of the comparison at once and be invisible. The day a pint release
    makes these mutable, this fails instead of the guard quietly weakening.
    """
    import dataclasses

    reg = registry()
    samples = (
        reg._units["meter"],
        next(iter(reg._prefixes.values())),
        next(iter(reg._dimensions.values())),
    )
    for definition in samples:
        assert dataclasses.is_dataclass(definition), definition
        assert definition.__dataclass_params__.frozen, definition


def test_the_fingerprint_is_stable_across_ordinary_work():
    """Safe to record in provenance: it does not move as a process runs."""
    first = units_fingerprint()
    for i in range(100):
        Quantity(float(i), "volt").to("millivolt")
    assert units_fingerprint() == first


# ---------------------------------------------------------------------
# TASK 1, THE FAIL-CLOSED PROOF
#
# The mechanism is not opt-in. It is checked inside ProvenanceRecord, which
# is mandatory on every ScientificResult, so a domain cannot decline it by
# not calling anything — including a domain that does not know it exists.
# ---------------------------------------------------------------------

# =====================================================================
# TASK 2 — applicability is a field of the result, not a note beside it
#
# It was populated on ONE path of five. Four domains said nothing, and the
# CSTR computed a full assessment, rendered `status.value` into a note, and
# discarded the condition names. The fix is to the CORE's permission, not to
# four domains: three states that cannot be confused, on every result, always.
# =====================================================================


def test_the_three_states_are_impossible_to_confuse():
    """"Assessed and empty", "deliberately not assessed" and "nobody said" are
    three different answers. Collapsing any two is how a result comes to look
    more examined than it is."""
    from engcore.scientific.models.definition import (
        ValidityAssessment, ValidityStatus,
    )
    from engcore.scientific.results.applicability import (
        ApplicabilityReport, ApplicabilityState,
    )

    empty = ApplicabilityReport.assessed({})
    stated = ApplicabilityReport.not_assessed("this path solves no model")
    silent = ApplicabilityReport.undeclared()

    assert empty.state is ApplicabilityState.ASSESSED
    assert stated.state is ApplicabilityState.NOT_ASSESSED
    assert silent.state is ApplicabilityState.UNDECLARED
    assert len({empty.state, stated.state, silent.state}) == 3

    # ...and a reader holding only the payload can tell them apart.
    assert empty.to_dict()["state"] == "assessed"
    assert stated.to_dict()["state"] == "not_assessed"
    assert silent.to_dict()["state"] == "undeclared"
    assert empty.to_dict()["assessments"] == {}
    assert silent.to_dict()["assessments"] == {}
    assert empty.to_dict() != silent.to_dict()

    # Only the assessed one is an assessment.
    assert empty.was_assessed
    assert not stated.was_assessed
    assert not silent.was_assessed

    # Round-trip preserves the distinction rather than normalising it away.
    for report in (empty, stated, silent):
        assert ApplicabilityReport.from_dict(report.to_dict()) == report

    real = ApplicabilityReport.assessed(
        {"R1": ValidityAssessment(status=ValidityStatus.IN_DOMAIN,
                                  satisfied=("temperature",))}
    )
    assert ApplicabilityReport.from_dict(real.to_dict()) == real


def test_the_states_cannot_be_constructed_inconsistently():
    """The state and the payload cannot disagree."""
    from engcore.scientific.errors import ScientificCoreError
    from engcore.scientific.models.definition import (
        ValidityAssessment, ValidityStatus,
    )
    from engcore.scientific.results.applicability import (
        ApplicabilityReport, ApplicabilityState,
    )

    assessment = ValidityAssessment(status=ValidityStatus.IN_DOMAIN)

    # 'not assessed' is a POSITION, and a position needs a reason.
    with pytest.raises(ScientificCoreError, match="requires a reason"):
        ApplicabilityReport(state=ApplicabilityState.NOT_ASSESSED)

    # ...and silence cannot carry one, or it is not silence.
    with pytest.raises(ScientificCoreError, match="has said something"):
        ApplicabilityReport(state=ApplicabilityState.UNDECLARED, reason="hm")

    # A record that did not assess cannot report what the assessment found.
    for state in (ApplicabilityState.UNDECLARED, ApplicabilityState.NOT_ASSESSED):
        with pytest.raises(ScientificCoreError, match="cannot also report"):
            ApplicabilityReport(
                state=state, reason="x", assessments={"R1": assessment}
            )


def test_every_result_says_something_about_applicability():
    """There is no way to have a result with nothing in this field.

    The default is UNDECLARED — a visible declaration, not an empty mapping
    that reads like an assessment finding nothing.
    """
    from engcore.scientific.results.applicability import ApplicabilityState
    from engcore.scientific.results.provenance import ProvenanceRecord
    from engcore.scientific.results.result import ScientificResult

    result = ScientificResult(
        result_id="r1", values={}, provenance=ProvenanceRecord(run_id="r1")
    )
    assert result.applicability.state is ApplicabilityState.UNDECLARED
    assert result.to_dict()["applicability"]["state"] == "undeclared"

    with pytest.raises(ScientificCoreError, match="UNDECLARED"):
        result.require_applicability()


def test_a_bare_mapping_is_refused_as_the_applicability_field():
    """The exact shape the four silent domains would have reached for."""
    from engcore.scientific.results.provenance import ProvenanceRecord
    from engcore.scientific.results.result import ScientificResult

    with pytest.raises(ScientificCoreError, match="ApplicabilityReport"):
        ScientificResult(
            result_id="r1", values={},
            provenance=ProvenanceRecord(run_id="r1"),
            applicability={},
        )


def test_an_older_payload_loads_as_undeclared_and_never_as_a_position():
    """Absence stays absence. A /2 record's author stated nothing, and
    inventing NOT_ASSESSED for it would put a position into a record whose
    author never took one."""
    from engcore.scientific.results.applicability import ApplicabilityState
    from engcore.scientific.results.provenance import ProvenanceRecord
    from engcore.scientific.results.result import (
        RESULT_SCHEMA, RESULT_SCHEMA_V2, ScientificResult,
    )

    assert RESULT_SCHEMA == "scientific_result/3"
    payload = ScientificResult(
        result_id="r1", values={}, provenance=ProvenanceRecord(run_id="r1")
    ).to_dict()
    old = {k: v for k, v in payload.items() if k != "applicability"}
    old["schema"] = RESULT_SCHEMA_V2
    restored = ScientificResult.from_dict(old)
    assert restored.applicability.state is ApplicabilityState.UNDECLARED
    assert restored.applicability.reason == ""


def test_electrical_dc_declares_applicability_per_component():
    """LIVE, not declared. Wiring is the test.

    Keyed by ``component_id`` rather than by model: the resistor model's one
    condition is ``resistance > 0`` and a circuit has many resistances, so a
    per-model verdict would be one answer for components that can disagree.
    """
    from engcore.domains.electrical.dc.circuit import DCCircuit
    from engcore.domains.electrical.dc.components import (
        DCVoltageSource, ElectricalNode, Resistor,
    )
    from engcore.domains.electrical.dc.solver import solve_circuit
    from engcore.scientific.results.applicability import ApplicabilityState
    from engcore.scientific.units.quantity import Quantity

    circuit = DCCircuit(
        circuit_id="applicability-probe",
        nodes=(
            ElectricalNode("gnd", is_reference=True),
            ElectricalNode("n1"),
            ElectricalNode("n2"),
        ),
        resistors=(
            Resistor("R1", "n1", "n2", Quantity(1.0, "kohm")),
            Resistor("R2", "n2", "gnd", Quantity(2.0, "kohm")),
        ),
        voltage_sources=(
            DCVoltageSource("V1", "n1", "gnd", Quantity(10.0, "volt")),
        ),
    )
    result = solve_circuit(circuit, run_id="applicability-probe")
    report = result.applicability

    assert report.state is ApplicabilityState.ASSESSED
    assert sorted(report.assessments) == ["R1", "R2"]
    assert report.violated == ()
    result.require_applicability()  # does not raise
    assert result.to_dict()["applicability"]["state"] == "assessed"


def test_the_frozen_thermal_path_is_visibly_undeclared():
    """The fifth path, reported rather than worked around.

    ``src/engcore/domains/thermal/`` may not be edited by this milestone, so
    its result cannot declare an assessment. What the mechanism buys even here
    is that the silence is now VISIBLE and refusable, rather than
    indistinguishable from an assessment that found nothing.
    """
    from engcore.domains.thermal.conduction1d.problem import (
        ConductionSlab, SlabDiscretization,
    )
    from engcore.domains.thermal.conduction1d.solver import solve_slab
    from engcore.scientific.results.applicability import ApplicabilityState
    from engcore.scientific.units.quantity import Quantity

    slab = ConductionSlab(
        slab_id="applicability-probe",
        length=Quantity(0.1, "meter"),
        diffusivity=Quantity(1.2e-5, "m**2/s"),
        end_time=Quantity(60.0, "second"),
        discretization=SlabDiscretization(32, 40),
    )
    result = solve_slab(slab, run_id="thermal-undeclared-probe")
    assert result.applicability.state is ApplicabilityState.UNDECLARED
    assert result.to_dict()["applicability"]["state"] == "undeclared"
    with pytest.raises(ScientificCoreError, match="UNDECLARED"):
        result.require_applicability()


def test_the_projection_refuses_an_undeclared_applicability():
    """THE FAIL-CLOSED PROOF for TASK 2, and the honest limit on it.

    `project_run` is the boundary where numbers become an answer somebody
    builds on. An execution that reaches it saying nothing about applicability
    is refused. This is enforcement, not declaration — but note what it is
    NOT: making the field mandatory on `ScientificResult` itself would require
    editing `src/engcore/domains/thermal/`, which this milestone may not
    touch. So a result can still be CONSTRUCTED undeclared; it cannot be
    PROJECTED undeclared.

    A stated position projects, because refusing one would destroy a real
    capability rather than protect anything.
    """
    from api_v0_case import canonical_request
    from engcore.application import contract
    from engcore.application.executions import electrothermal_series as ets
    from engcore.scientific.results.applicability import ApplicabilityReport

    request = canonical_request()
    prepared = ets.prepare(request["inputs"], request["coupling"], "native")
    run = prepared.run("applicability-projection-probe").run

    with pytest.raises(ScientificCoreError, match="UNDECLARED"):
        contract.project_run(run)

    # ...and a STATED position is reported, not refused.
    projected = contract.project_run(
        run,
        applicability=ApplicabilityReport.not_assessed(
            "this probe does not assess applicability"
        ),
    )
    assert projected["model_validity"]["state"] == "not_assessed"
    assert projected["model_validity"]["assessed"] is False


def test_every_result_producer_is_accounted_for():
    """The enumeration, so that "four of five" is measured and not asserted.

    Declaring is not testing — but an enumeration read from the tree is the
    one thing a live test cannot give: it names every producer, including the
    ones nothing in this suite exercises, so a NEW producer that declares
    nothing shows up here as a change rather than as silence.
    """
    import ast

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "engcore"
    declaring: set[str] = set()
    silent: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "ScientificResult(" not in text:
            continue
        name = path.relative_to(root).as_posix()
        # AST, not a substring: `systems/electrothermal/coupled.py` contains
        # `applicability=` on its OWN record (`AdmittedCoupledRun`) and not on
        # any ScientificResult, so a substring scan called it migrated when it
        # is not. The question is specifically what the RESULT carries.
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, ast.Call):
                continue
            called = node.func
            if not (isinstance(called, ast.Name) and called.id == "ScientificResult"):
                continue
            keywords = {k.arg for k in node.keywords}
            (declaring if "applicability" in keywords else silent).add(name)

    assert declaring == {
        "domains/electrical/dc/solver.py",
        "domains/fluids/transport2d/solver.py",
        "domains/kinetics/cstr/solver.py",
    }, sorted(declaring)

    # Everything else leaves the field UNDECLARED — visibly, and refusably.
    # `domains/thermal/` is frozen by this milestone's rules and is the fifth
    # path; the rest are producers CORE-MECHANISMS did not migrate, and this
    # is exactly the list a follow-up has to work through.
    assert "domains/thermal/conduction1d/solver.py" in silent
    assert silent == {
        "domains/electrical/ngspice.py",
        "domains/thermal/conduction1d/solver.py",
        "domains/thermal_conduction1d_bulk.py",
        "domains/thermal_conduction1d_schemes.py",
        "systems/aerospace/multirotor/reference.py",
        "systems/electrothermal/coupled.py",
        "systems/electrothermal/power_chain.py",
        "systems/electrothermal/resistor_body.py",
        "systems/fluidthermal/coupled.py",
        "systems/propulsion/drive.py",
    }, sorted(silent)


# =====================================================================
# TASK 3 — every route into a ValidationCheck
#
# The task's premise was that `record_check` bypassed a constructor rule
# called GUARD 2. Neither exists in this repository: there is no
# `record_check`, and the constructor enforced NO evidentiary rule on ANY
# axis. So the guard that was "complete on one axis" was complete on none,
# and the work is to install the rule and cover every route at once.
#
# THE ENUMERATION, measured rather than reasoned about:
#
#   1. ValidationCheck(...)              __post_init__ ran
#   2. ValidationCheck.from_dict(...)    __post_init__ ran (delegates to 1)
#   3. dataclasses.replace(...)          __post_init__ ran (calls __init__)
#   4. copy.copy(...)                    DID NOT RUN  -> closed by __reduce__
#   5. copy.deepcopy(...)                DID NOT RUN  -> closed by __reduce__
#   6. pickle round-trip                 DID NOT RUN  -> closed by __reduce__
#   7. ValidationReport(checks=(...))    accepted a non-check, refusing it
#                                        only incidentally via AttributeError
#   8. ValidationReport.with_check(...)  takes an already-built check (1-6)
#   9. object.__new__ + object.__setattr__   reachable by NO construction
#                                        rule; this is vandalism, not a route
# =====================================================================


def test_the_enumeration_of_routes_into_a_validation_check_is_complete():
    """Routes 1-6: every one now goes through the constructor.

    4, 5 and 6 did not, and that is the finding: three routes that look like
    they COPY a record rather than build one, each of which reconstructed a
    frozen dataclass without running a single rule.
    """
    import dataclasses
    import pickle
    from engcore.scientific.results.validation import (
        ValidationCheck, ValidationLevel, ValidationOutcome,
    )

    ran: list[str] = []
    original = ValidationCheck.__post_init__

    def spy(self):
        ran.append(self.name)
        original(self)

    good = ValidationCheck(
        name="c", outcome=ValidationOutcome.PASS,
        establishes=ValidationLevel.NUMERICALLY_CONVERGED,
        residual=1e-12, tolerance=1e-9,
    )
    ValidationCheck.__post_init__ = spy
    try:
        routes = {
            "constructor": lambda: ValidationCheck(name="x", outcome="pass"),
            "from_dict": lambda: ValidationCheck.from_dict(good.to_dict()),
            "replace": lambda: dataclasses.replace(good, name="y"),
            "copy": lambda: copy.copy(good),
            "deepcopy": lambda: copy.deepcopy(good),
            "pickle": lambda: pickle.loads(pickle.dumps(good)),
        }
        for label, build in routes.items():
            before = len(ran)
            rebuilt = build()
            assert isinstance(rebuilt, ValidationCheck), label
            assert len(ran) > before, f"{label} bypassed __post_init__"
    finally:
        ValidationCheck.__post_init__ = original


def test_copy_cannot_launder_a_check_past_the_rule():
    """Route 4/5/6, exercised against the rule rather than against a spy.

    A record that could not be constructed must not be reachable by copying
    one that could — otherwise `copy` is a laundering step.
    """
    import pickle
    from engcore.scientific.errors import ScientificValidationError
    from engcore.scientific.results.validation import (
        ValidationCheck, ValidationLevel, ValidationOutcome,
    )

    backed = ValidationCheck(
        name="benchmark", outcome=ValidationOutcome.PASS,
        establishes=ValidationLevel.BENCHMARK_VALIDATED,
        evidence=("NIST SRM 1234 case 3",),
    )
    # Strip the backing behind the constructor's back, exactly as a
    # __dict__-level copy would have produced before __reduce__ existed.
    object.__setattr__(backed, "evidence", ())
    for rebuild in (copy.copy, copy.deepcopy,
                    lambda c: pickle.loads(pickle.dumps(c))):
        with pytest.raises(ScientificValidationError, match="not evidence"):
            rebuild(backed)


def test_a_passing_check_cannot_claim_a_level_it_cannot_back():
    """THE ROUTE THE TASK NAMES. It was open on every axis, not one."""
    from engcore.scientific.errors import ScientificValidationError
    from engcore.scientific.results.validation import (
        ValidationCheck, ValidationLevel, ValidationOutcome, ValidationReport,
    )

    for level in (
        ValidationLevel.NUMERICALLY_CONVERGED,
        ValidationLevel.ANALYTICALLY_VERIFIED,
        ValidationLevel.BENCHMARK_VALIDATED,
        ValidationLevel.CROSS_SOLVER_VALIDATED,
        ValidationLevel.EXPERIMENTALLY_VALIDATED,
    ):
        with pytest.raises(ScientificValidationError, match="not evidence"):
            ValidationCheck(name="claims", outcome=ValidationOutcome.PASS,
                            establishes=level)

    # Either form of backing satisfies it: a comparison, or named artefacts.
    ValidationCheck(name="a", outcome=ValidationOutcome.PASS,
                    establishes=ValidationLevel.NUMERICALLY_CONVERGED,
                    residual=1e-12, tolerance=1e-9)
    ValidationCheck(name="b", outcome=ValidationOutcome.PASS,
                    establishes=ValidationLevel.BENCHMARK_VALIDATED,
                    evidence=("NIST SRM 1234 case 3",))

    # DIMENSIONALLY_VALID is exempt on purpose: it is not a numerical claim,
    # and it is established by the check having run and passed.
    ValidationCheck(name="dimensional_consistency", outcome=ValidationOutcome.PASS,
                    establishes=ValidationLevel.DIMENSIONALLY_VALID)

    # ...and a residual alone is not a comparison. It needs its bound.
    with pytest.raises(ScientificValidationError, match="not evidence"):
        ValidationCheck(name="half", outcome=ValidationOutcome.PASS,
                        establishes=ValidationLevel.NUMERICALLY_CONVERGED,
                        residual=1e-12)


def test_a_non_passing_check_may_still_record_what_was_attempted():
    """The capability a stricter rule would have destroyed.

    Forbidding `establishes` on any non-passing check was written first and
    backed out. "We tried to establish benchmark validation and could not" is
    genuinely different from "we never tried", and only a PASSING check
    reaches `attained_levels`, so only a passing check can make an unbacked
    claim count.
    """
    from engcore.scientific.results.validation import (
        ValidationCheck, ValidationLevel, ValidationOutcome, ValidationReport,
    )

    for outcome in (ValidationOutcome.NOT_RUN, ValidationOutcome.FAIL):
        check = ValidationCheck(name="benchmark", outcome=outcome,
                                establishes=ValidationLevel.BENCHMARK_VALIDATED)
        report = ValidationReport(checks=(check,))
        assert not report.claims(ValidationLevel.BENCHMARK_VALIDATED)
        assert report.attained_levels == frozenset()


def test_a_passing_check_cannot_contradict_its_own_tolerance():
    """A PASS whose residual exceeds its own bound is a self-contradicting
    record, and worse than a failing one."""
    from engcore.scientific.errors import ScientificValidationError
    from engcore.scientific.results.validation import (
        ValidationCheck, ValidationOutcome,
    )

    with pytest.raises(ScientificValidationError, match="contradicts itself"):
        ValidationCheck(name="r", outcome=ValidationOutcome.PASS,
                        residual=1.0, tolerance=1e-9)
    # A FAILING check with the same numbers is exactly what a failure looks
    # like, and is not refused.
    ValidationCheck(name="r", outcome=ValidationOutcome.FAIL,
                    residual=1.0, tolerance=1e-9)


def test_the_report_refuses_a_non_check_for_a_stated_reason():
    """Route 7. It refused before — by AttributeError, from a duplicate-name
    scan reaching `.name`. That is not a scientific error, says nothing about
    what is wrong, and would have stopped refusing the day anything with a
    `.name` was passed instead."""
    from engcore.scientific.errors import ScientificValidationError
    from engcore.scientific.results.validation import ValidationReport

    class LooksLikeACheck:
        name = "plausible"
        outcome = "pass"

    for entry in ("not a check at all", LooksLikeACheck()):
        with pytest.raises(ScientificValidationError, match="must be ValidationCheck"):
            ValidationReport(checks=(entry,))


# =====================================================================
# TASK 4 — refuse at construction, and refuse the SAME things
#
# The second half is the harder half. Two refusals over the same value space
# that do not agree is a worse defect than either alone — and they did not
# agree: `encode()` refused an unserializable value with a ScientificCoreError
# naming its type, while a record's own `to_dict()` passed the value straight
# through and the process died later inside `json.dumps` with a TypeError that
# named no field, no record and no run.
# =====================================================================


def _bare_result(**kwargs):
    from engcore.scientific.results.provenance import ProvenanceRecord
    from engcore.scientific.results.result import ScientificResult

    return ScientificResult(
        result_id="r", values={}, provenance=ProvenanceRecord(run_id="r"), **kwargs
    )


def test_an_unrecordable_value_is_refused_at_construction():
    """Naming the field and the type, where the caller still knows which
    field they were filling in."""
    with pytest.raises(ScientificCoreError) as excinfo:
        _bare_result(metadata={"probe": object()})
    message = str(excinfo.value)
    assert "'probe'" in message          # the field
    assert "object" in message           # the type
    assert "provenance does not exist" in message


def test_provenance_refuses_it_too():
    """A result whose provenance cannot be recorded has no provenance."""
    from engcore.scientific.results.provenance import ProvenanceRecord

    with pytest.raises(ScientificCoreError, match="provenance metadata key 'p'"):
        ProvenanceRecord(run_id="r", metadata={"p": object()})


def test_the_two_refusals_cannot_disagree():
    """ONE acceptance rule, with two callers — not two rules that happen to
    line up today.

    Asserted over a value space that includes the case where they DID
    disagree: an Enum is accepted by `encode` and was accepted by
    construction, and then `json.dumps(to_dict())` died on it. Now
    construction admits exactly what serialization can write, and
    serialization writes exactly what construction admitted.
    """
    import enum
    import json
    from engcore.scientific.serialization import encode, to_json

    class Colour(enum.Enum):
        RED = "red"

    space = [
        None, True, 3, 4.5, "text",
        Colour.RED,
        {"b": 2, "a": 1},
        [1, 2, 3], (1, 2), {1, 2}, frozenset({3}),
        object(), lambda: None, iter([]), complex(1, 2), b"bytes",
    ]
    for value in space:
        try:
            encode(value)
        except ScientificCoreError:
            encode_accepts = False
        else:
            encode_accepts = True

        try:
            result = _bare_result(metadata={"v": value})
        except ScientificCoreError:
            construction_accepts = False
        else:
            construction_accepts = True

        assert encode_accepts == construction_accepts, (
            f"{type(value).__name__}: encode says {encode_accepts}, "
            f"construction says {construction_accepts}"
        )

        if construction_accepts:
            # ...and anything construction admitted must actually serialize,
            # which is the half that used to raise TypeError from json.
            json.loads(to_json(result))


def test_a_result_that_exists_can_always_be_recorded():
    """The invariant the two halves add up to."""
    import json
    from engcore.scientific.serialization import to_json

    result = _bare_result(metadata={"nested": {"z": 1, "a": [1, {"k": "v"}]}})
    payload = json.loads(to_json(result))
    assert payload["metadata"]["nested"]["a"][1]["k"] == "v"


def test_design_memory_canonical_bytes_still_has_no_explicit_refusal():
    """The disagreement the task asked about, reported rather than assumed.

    `_canonical_bytes` in `engcore/design/memory.py` is a bare `json.dumps`
    with NO explicit refusal — the "new explicit refusal" the task refers to
    does not exist in this tree. So it cannot yet disagree with the rule
    installed here; it simply raises `TypeError` where the core raises a
    scientific error. That is recorded as a KNOWN GAP rather than fixed:
    `design/memory.py` is the subject of a frozen test module, and the
    records it hashes are built from typed references rather than from the
    untyped metadata channel this task is about.
    """
    import inspect
    from engcore.design import memory

    source = inspect.getsource(memory._canonical_bytes)
    assert "raise" not in source
    with pytest.raises(TypeError):
        memory._canonical_bytes({"x": object()})


_INFLUENCE = """
import json
from engcore.scientific.units.quantity import registry, Quantity
from engcore.scientific.results.provenance import ProvenanceRecord

# RUN 1 — a domain vandalises the registry by the one route no seal blocks.
before = Quantity(1.0, "volt").to("millivolt").magnitude
units = registry()._units
units["widget"] = units["meter"]

# RUN 2 — a DIFFERENT domain, which knows nothing about run 1, builds the
# provenance every scientific result is required to carry.
try:
    ProvenanceRecord(run_id="run-2")
    print(json.dumps({"refused": False}))
except Exception as exc:
    print(json.dumps({"refused": True, "type": type(exc).__name__,
                      "message": str(exc)}))
"""


def test_two_runs_in_one_process_cannot_influence_each_other():
    """THE MEASUREMENT. Constructed deliberately, in a real second process.

    Run 1 changes the unit algebra. Run 2 is a different domain that calls
    nothing new and opts into nothing. It is refused before it can report a
    number, because the check lives where every run already has to go.
    """
    # PYTHONPATH is pinned to the `src` THIS process imported engcore from,
    # not left to the interpreter's default. Without it the child resolves
    # engcore from whatever is installed, so the child would exercise a
    # different tree than the parent — which is exactly how a mutation test
    # comes back green against unmutated source.
    import engcore
    import json
    import os

    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONPATH"] = str(
        pathlib.Path(engcore.__file__).resolve().parents[1]
    )
    completed = subprocess.run(
        [sys.executable, "-c", _INFLUENCE],
        capture_output=True, text=True, check=True, env=environment,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["refused"] is True, payload
    assert payload["type"] == "UnitRegistryFrozen", payload
    assert "widget" in payload["message"], payload
