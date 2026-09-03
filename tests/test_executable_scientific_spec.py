"""EXEC-SPEC — the residue measurement and the reconstruction proof.

Preregistration: `docs/executable-scientific-spec-prereg.md`, committed before
any source file of this milestone was written.

The suite has two halves and they answer different questions.

**The measurement.** What does a domain need in order to execute that no existing
typed contract can carry? Answered by executed encoding attempts, one shared
records-only reader, and a decision rule fixed before the results were seen.

**The proof.** Can a problem be persisted, reconstructed in a *separate
interpreter process*, and executed to the same answer? Answered by four domains,
three of which additionally run in a fresh process, one of which additionally
runs through an external provider.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess
import sys

import pytest

from engcore.scientific.errors import ScientificCoreError
from engcore.scientific.units.quantity import Quantity
from experiments.exec_spec_residue import bridge, cases, encodings, instrument, residue
from experiments.exec_spec_residue.instrument import AnswerStatus, PlannerQuestion

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

DC_TOLERANCE = 1e-9
SLAB_TOLERANCE = 1e-12
CSTR_TOLERANCE = 1e-9
#: The tolerance HETERO-NGSPICE preregistered for native-vs-provider agreement.
PROVIDER_TOLERANCE = 1e-6


# =====================================================================
# Instrument integrity
# =====================================================================

def test_the_reader_cannot_see_the_domain():
    """FAIL CONDITION: the records-only reader may not import a domain.

    Asserted by AST scan rather than by convention, because a convention is one
    convenient import away from being untrue.
    """
    source = pathlib.Path(instrument.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = sorted(
        name
        for name in imported
        if name.startswith("engcore.domains") or name.startswith("engcore.systems")
    )
    assert forbidden == [], f"the records-only reader imports {forbidden}"
    assert any(name.startswith("engcore.scientific") for name in imported), (
        "the reader is expected to know the core schema it reads"
    )


def test_one_instrument_serves_every_column():
    """FAIL CONDITION §13.4: a per-column reader is not permitted."""
    for column, encoding in encodings.ENCODINGS.items():
        payloads = encoding.to_payloads()
        answers = instrument.inspect(
            payloads["problem"], payloads.get("structure")
        )
        assert set(answers) == set(instrument.QUESTIONS), column


# =====================================================================
# The executed encoding attempts
# =====================================================================

def test_every_attempt_was_actually_executed():
    """Each attempt carries the outcome a real contract produced."""
    assert len(encodings.ATTEMPTS) == 11
    for attempt in encodings.ATTEMPTS:
        assert attempt.detail, attempt.fact


@pytest.mark.parametrize(
    "fact,channel,expected",
    [
        (
            "which nodes element R1 connects, in terminal order",
            encodings.Channel.DATA_REFERENCE,
            encodings.AttemptOutcome.REFUSED_BY_TYPE,
        ),
        (
            "which nodes element R1 connects, in terminal order",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.MEANING_IN_KEY,
        ),
        (
            "which nodes element R1 connects, in terminal order",
            encodings.Channel.BOUNDARY_CONDITION,
            encodings.AttemptOutcome.MEANING_IN_KEY,
        ),
        (
            "non-uniform initial field u(x,0) = sin(pi x / L)",
            encodings.Channel.INITIAL_CONDITION,
            encodings.AttemptOutcome.REFUSED_BY_TYPE,
        ),
        (
            "non-uniform initial field u(x,0) = sin(pi x / L)",
            encodings.Channel.DATA_REFERENCE,
            encodings.AttemptOutcome.NO_PERSISTABLE_HOME,
        ),
        (
            "homogeneous Dirichlet ends u(0,t) = u(L,t) = 0",
            encodings.Channel.BOUNDARY_CONDITION,
            encodings.AttemptOutcome.WORKS,
        ),
        (
            "initial concentration and temperature",
            encodings.Channel.INITIAL_CONDITION,
            encodings.AttemptOutcome.WORKS,
        ),
        (
            "integration method, tolerances, evaluation budget, output density",
            encodings.Channel.SOLVER_SETTINGS,
            encodings.AttemptOutcome.NO_PERSISTABLE_HOME,
        ),
        (
            "integration method, tolerances, evaluation budget, output density",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.LEAKS_INTO_IDENTITY,
        ),
        (
            "mesh resolution (n_cells, n_steps)",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.LEAKS_INTO_IDENTITY,
        ),
        (
            "reference resistance, temperature coefficient, reference temperature",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.WORKS,
        ),
    ],
)
def test_the_executed_encoding_outcomes(fact, channel, expected):
    matches = [
        a for a in encodings.ATTEMPTS if a.fact == fact and a.channel is channel
    ]
    assert len(matches) == 1, (fact, channel)
    assert matches[0].outcome is expected, matches[0].detail


def test_the_boundary_condition_channel_works_and_is_unused_in_production():
    """The slab's ends ARE representable. Thermal's production domain writes
    none of them — this is the measurement that keeps the slab's residue
    honest: what is missing there is the *non-uniform* initial condition,
    not boundary conditions.

    UPDATED by REAL-FLUID-PDE-DOMAIN (`docs/real-fluid-pde-evidence.md`):
    this test's own original assertion message anticipated exactly this —
    `f"BoundaryCondition now has producers: {producers}"` — a canary meant
    to be updated, not a frozen invariant. `fluids/transport2d` is now a
    real production producer: it declares four genuine
    `BoundaryCondition(kind=DIRICHLET, ...)` instances (one per side of the
    square domain), because the boundary VALUE channel this test measured as
    "works" is exactly what that domain needs — Dirichlet `c = c*(x,y)`
    restricted to each side. `thermal/conduction1d` still writes none (it
    fixes its own boundary condition as a metadata string, unchanged by this
    milestone), so the slab-specific finding above is unaffected; only the
    repo-wide "and nothing uses it" half of the old claim no longer holds.
    """
    encoding = encodings.ENCODINGS["col-slab"]
    assert len(encoding.problem.boundary_conditions) == 2
    domains = REPO_ROOT / "src" / "engcore" / "domains"
    producers = [
        str(path.relative_to(REPO_ROOT))
        for path in domains.rglob("*.py")
        if "BoundaryCondition(" in path.read_text(encoding="utf-8")
    ]
    assert producers == [
        "src/engcore/domains/fluids/transport2d/problem.py"
    ], f"BoundaryCondition producers changed unexpectedly: {producers}"


# =====================================================================
# The residue table and the preregistered decision rule
# =====================================================================

def test_every_residue_item_names_a_failed_attempt():
    """FAIL CONDITION §13.3: no residue item without a demonstrated attempt."""
    for item in residue.RESIDUE:
        assert item.attempts, item.fact
        assert any(
            a.outcome is not encodings.AttemptOutcome.WORKS for a in item.attempts
        ), item.fact


def test_the_strict_residue_table():
    """STRICT: only facts no existing contract can carry at all."""
    table = {
        column: tuple(i.fact for i in items)
        for column, items in residue.table(residue.Reading.STRICT).items()
    }
    assert table == {
        "col-dc": ("which nodes element R1 connects, in terminal order",),
        "col-slab": ("non-uniform initial field u(x,0) = sin(pi x / L)",),
        "col-cstr": (),
        "col-material": (),
    }


def test_the_placement_residue_table():
    """PLACEMENT: also facts a contract can hold only in the wrong place."""
    table = {
        column: len(items)
        for column, items in residue.table(residue.Reading.PLACEMENT).items()
    }
    assert table == {"col-dc": 1, "col-slab": 2, "col-cstr": 1, "col-material": 0}


def test_the_preregistered_decision_rule_selects_the_outcome():
    """§9, applied mechanically. No human chooses the cell.

    **Recorded deviation.** §9 row 1 says "non-empty for exactly one column" and
    the measured STRICT table has **two** non-empty columns (`col-dc` and
    `col-slab`); §9 row 3 also matches, and the preregistration states no
    precedence between them. `decide()` resolves it by ranking on ledger — the
    §67.3 booking rule — which is defensible and is **not** in §9. The
    adversarial pass caught this; it is recorded in the evidence document as a
    deviation rather than silently relied on.
    """
    strict_table = residue.table(residue.Reading.STRICT)
    non_empty = tuple(c for c, items in strict_table.items() if items)
    assert non_empty == ("col-dc", "col-slab"), "two columns are non-empty"

    decision = residue.decide(residue.Reading.STRICT)
    assert decision.outcome == "NO UNIVERSAL RECORD — E + F"
    assert decision.ledger1_columns == ("col-dc",)


def test_the_placement_reading_reaches_the_same_outcome_by_a_different_route():
    """And the agreement is NOT independent corroboration. Stated, not hidden.

    STRICT decides on a ledger-ranked count; PLACEMENT decides on whether the
    Ledger-1 residues share a `ResidueKind`. Those kind labels are **argued, not
    measured** — no executed attempt produces them — so relabelling the CSTR item
    would flip this outcome. The two readings agreeing therefore says the two
    Ledger-1 items were assigned different kinds; it does not independently
    confirm the decision.
    """
    decision = residue.decide(residue.Reading.PLACEMENT)
    assert decision.outcome == "NO UNIVERSAL RECORD — per-kind treatment"
    assert decision.ledger1_columns == ("col-dc", "col-cstr")
    kinds = {
        item.kind
        for column in decision.ledger1_columns
        for item in residue.residue_for(column, residue.Reading.PLACEMENT)
        if item.ledger is residue.Ledger.EXISTING_RECORD
    }
    assert kinds == {
        residue.ResidueKind.SCIENTIFIC_STRUCTURE,
        residue.ResidueKind.NUMERICAL_SETTING,
    }


def test_the_slab_residue_is_booked_ledger_two():
    """Both slab items are recorded MIN-FOUNDATION-PDE deferrals, not findings."""
    items = residue.residue_for("col-slab", residue.Reading.PLACEMENT)
    assert {i.ledger for i in items} == {residue.Ledger.ABSENT_RECORD}


def test_the_cstr_residue_is_placement_only_and_ledger_one():
    """The record exists (`SolverSettings`); nothing persistable references it."""
    strict = residue.residue_for("col-cstr", residue.Reading.STRICT)
    placement = residue.residue_for("col-cstr", residue.Reading.PLACEMENT)
    assert strict == ()
    assert len(placement) == 1
    assert placement[0].ledger is residue.Ledger.EXISTING_RECORD
    assert placement[0].kind is residue.ResidueKind.NUMERICAL_SETTING


# =====================================================================
# Planner inspectability
# =====================================================================

@pytest.mark.parametrize("column", list(encodings.ENCODINGS))
def test_the_reader_answers_every_planner_question_at_l1(column):
    """§7: eight questions, answered from records, without domain code."""
    payloads = encodings.ENCODINGS[column].to_payloads()
    answers = instrument.inspect(payloads["problem"], payloads.get("structure"))
    unanswered = sorted(
        q.value
        for q, a in answers.items()
        if a.status is AnswerStatus.IMPOSSIBLE
        and q is not PlannerQuestion.STRUCTURE
    )
    assert unanswered == [], f"{column}: {unanswered}"


def test_connectivity_is_unanswerable_from_the_problem_alone():
    """P-9: at L0 no column can answer the structure question."""
    for column, encoding in encodings.ENCODINGS.items():
        answers = instrument.inspect(encoding.problem.to_dict(), None)
        assert answers[PlannerQuestion.STRUCTURE].status is AnswerStatus.IMPOSSIBLE, column


def test_connectivity_is_answerable_for_the_network_column_at_l1():
    """P-9: with the domain's own published record, incidence is recoverable."""
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    answer = instrument.inspect(payloads["problem"], payloads["structure"])[
        PlannerQuestion.STRUCTURE
    ]
    assert answer.status is AnswerStatus.RECOVERABLE
    edges = {e["component_id"]: e["terminals"] for e in answer.value["edges"]}
    assert edges == {"R1": ["n0", "n1"], "R2": ["n1", "gnd"], "V1": ["n0", "gnd"]}
    assert answer.value["reference_nodes"] == ["gnd"]


def test_a_foreign_structure_schema_is_reported_not_guessed():
    """A reader that does not know a schema says so; it does not interpret it."""
    answer = instrument.inspect(
        encodings.ENCODINGS["col-dc"].problem.to_dict(),
        {"schema": "some_future_domain_artifact/1", "payload": [1, 2, 3]},
    )[PlannerQuestion.STRUCTURE]
    assert answer.status is AnswerStatus.IMPOSSIBLE
    assert "does not know" in answer.detail


def test_every_identifier_a_planner_would_read_actually_resolves():
    """Added after the adversarial pass, which found four that did not.

    `instrument.inspect` answers MODELS and CAPABILITIES from non-empty lists and
    never resolves an identifier — so four invented strings passed 58 tests. A
    planner's first act after reading a record is to look the identity up, and
    that is what this asserts.
    """
    from engcore.domains.electrical.dc import DC_MODELS, ELECTRICAL_DC_LINEAR
    from engcore.domains.electrical.material import LINEAR_TCR_MODEL
    from engcore.domains.kinetics.cstr import CSTR_MODELS, KINETICS_CSTR_NONISOTHERMAL
    from engcore.domains.thermal.conduction1d import (
        CONDUCTION_MODELS,
        THERMAL_CONDUCTION_1D,
    )
    from engcore.scientific.models.registry import ModelRegistry
    from engcore.scientific.solvers.capability import CoreCapabilities

    registry = ModelRegistry(
        (*DC_MODELS, *CONDUCTION_MODELS, *CSTR_MODELS, LINEAR_TCR_MODEL)
    )
    known_capabilities = {
        ELECTRICAL_DC_LINEAR.name,
        THERMAL_CONDUCTION_1D.name,
        KINETICS_CSTR_NONISOTHERMAL.name,
        CoreCapabilities.ALGEBRAIC.name,
    }
    for column, encoding in encodings.ENCODINGS.items():
        for reference in encoding.problem.models:
            # Raises ModelNotFoundError if the identity is invented.
            registry.get(reference.model_id, reference.version)
        unknown = set(encoding.problem.required_capabilities) - known_capabilities
        assert unknown == set(), f"{column} requires unknown capabilities {unknown}"


def test_three_columns_reconstruct_by_parameter_name_convention():
    """The measurement's own limit, made executable.

    `col-dc`'s incidence was rejected as residue partly because a categorical
    parameter would carry the relation in the *spelling* of its name. Three of
    four columns recover their physics by exactly that mechanism: the bridge asks
    for a parameter called "alpha" and puts it in `ConductionSlab.diffusivity`.
    No record publishes that mapping.

    So the reduction of the other three columns into existing contracts is
    **exhibited**, not proven, and this test is the counterexample that says so.
    """
    payloads = encodings.ENCODINGS["col-slab"].to_payloads()
    problem = json.loads(json.dumps(payloads["problem"]))
    for parameter in problem["parameters"]:
        if parameter["name"] == "alpha":
            parameter["name"] = "diffusivity"  # the same physics, a different word
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_slab(problem, payloads["structure"])


def test_the_slab_boundary_records_determine_a_variable_they_do_not_govern():
    """A measured consequence, and it is uncomfortable.

    The two `BoundaryCondition` records the slab encoding writes are read by no
    solver — the homogeneous Dirichlet ends are compiled into `assemble()`. They
    are nonetheless read by the CORE: `unresolved_inputs` treats a variable named
    by any boundary condition as determined, so the reader answers "nothing must
    be supplied" for the one column whose initial field this milestone declares
    unrepresentable.
    """
    answers = instrument.inspect(encodings.ENCODINGS["col-slab"].problem.to_dict())
    assert answers[PlannerQuestion.REQUIRED_INPUTS].value == []


def test_required_inputs_are_computed_by_the_core_not_by_this_milestone():
    """The reader answers 'what must be supplied' with the core's own function."""
    answers = instrument.inspect(
        encodings.ENCODINGS["col-material"].problem.to_dict()
    )
    required = answers[PlannerQuestion.REQUIRED_INPUTS].value
    assert required == [{"quantity": "temperature", "unit": "kelvin"}]


# =====================================================================
# No arbitrary code crosses the boundary
# =====================================================================

def test_a_persisted_problem_is_data_and_only_data():
    """§14: no callables, no import paths, no pickle, no shell."""
    for column, encoding in encodings.ENCODINGS.items():
        blob = json.dumps(encoding.to_payloads(), sort_keys=True)
        for forbidden in ("__", "import ", "lambda", "eval(", "exec(", "subprocess"):
            assert forbidden not in blob, f"{column} carries {forbidden!r}"
        # It must round-trip through plain JSON with no custom decoder.
        assert json.loads(blob) == json.loads(blob)


# =====================================================================
# Reconstruction — in process
# =====================================================================

@pytest.mark.parametrize(
    "column,rebuild,original",
    [
        ("col-slab", bridge.rebuild_slab, "SLAB"),
        ("col-cstr", bridge.rebuild_run, "RUN"),
        ("col-material", bridge.rebuild_conductor, "CONDUCTOR"),
    ],
)
def test_reconstruction_reproduces_the_original_artifact(column, rebuild, original):
    """The strongest available statement: rebuilt == original, by value."""
    payloads = encodings.ENCODINGS[column].to_payloads()
    rebuilt = rebuild(payloads["problem"], payloads.get("structure"))
    assert rebuilt == getattr(cases, original)


def test_the_circuit_round_trip_preserves_identity_but_not_python_equality():
    """MEASURED, and it is a finding rather than a defect.

    `DCCircuit.to_dict` sorts nodes and components by id; the constructor keeps
    the tuple it is given. So a serialize/load round trip returns a circuit that
    is **the same physical system** — same `fingerprint()`, same canonical
    description, same solution — and is **not** ``==`` to the original, because
    dataclass equality compares tuple order.

    That is the right behaviour for identity and a trap for any future code that
    reaches for ``==`` to mean "same system". Recorded here rather than hidden
    behind a sorted comparison.
    """
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    rebuilt = bridge.rebuild_circuit(payloads["problem"], payloads["structure"])

    assert rebuilt.fingerprint() == cases.CIRCUIT.fingerprint()
    assert rebuilt.canonical_dict() == cases.CIRCUIT.canonical_dict()
    assert rebuilt != cases.CIRCUIT
    assert sorted(rebuilt.node_ids) == sorted(cases.CIRCUIT.node_ids)
    assert rebuilt.reference_node == cases.CIRCUIT.reference_node
    assert {r.component_id: r.resistance for r in rebuilt.resistors} == {
        r.component_id: r.resistance for r in cases.CIRCUIT.resistors
    }


def test_the_dc_problem_is_a_projection_of_the_artifact_not_a_source():
    """Measured asymmetry: for the network column the artifact carries everything.

    The problem's typed parameters *verify* the circuit and cannot *produce* it.
    For the other three columns the direction is the opposite.
    """
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_circuit(payloads["problem"], None)
    # …while the artifact alone reconstructs the circuit completely.
    from engcore.domains.electrical.dc import DCCircuit

    assert (
        DCCircuit.from_dict(payloads["structure"]).fingerprint()
        == cases.CIRCUIT.fingerprint()
    )


# =====================================================================
# Negative tests — §11
# =====================================================================

def test_n_a_missing_structure_is_a_typed_failure():
    payloads = encodings.ENCODINGS["col-slab"].to_payloads()
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_slab(payloads["problem"], None)


def test_n_b_identity_mismatch_is_refused():
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    problem = json.loads(json.dumps(payloads["problem"]))
    for parameter in problem["parameters"]:
        if parameter["name"] == "R:R1":
            parameter["value"]["magnitude"] = 47.0
    with pytest.raises(bridge.IdentityMismatch):
        bridge.rebuild_circuit(problem, payloads["structure"])


def test_n_c_corrupted_structure_is_refused():
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["resistors"][0].pop("resistance")
    with pytest.raises(bridge.CorruptStructure):
        bridge.rebuild_circuit(payloads["problem"], structure)


def test_n_d_unsupported_schema_fails_loudly():
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["schema"] = "electrical_dc_circuit/99"
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_circuit(payloads["problem"], structure)


def test_n_e_a_valid_problem_without_its_structure_does_not_execute():
    payloads = encodings.ENCODINGS["col-cstr"].to_payloads()
    with pytest.raises(bridge.MissingStructure):
        bridge.execute("col-cstr", payloads["problem"], None)


def test_n_f_structure_for_the_wrong_domain_does_not_silently_bind():
    dc = encodings.ENCODINGS["col-dc"].to_payloads()
    slab = encodings.ENCODINGS["col-slab"].to_payloads()
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_circuit(dc["problem"], slab["structure"])
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_slab(slab["problem"], dc["structure"])


def test_reconstruction_failure_is_not_a_scientific_verdict():
    """Failing to rebuild is not a statement about nature.

    Same separation `engcore.data` draws for `BulkDataError` and the ngspice
    adapter draws for `NgspiceExecutionFailure`.
    """
    assert not issubclass(bridge.ReconstructionError, ScientificCoreError)


def test_a_residue_free_column_refuses_a_second_source_of_truth():
    payloads = encodings.ENCODINGS["col-material"].to_payloads()
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_conductor(payloads["problem"], {"schema": "anything/1"})


def test_an_unverified_element_type_is_a_hole_the_example_hid():
    """D-2, added after the adversarial pass.

    The frozen case has no current source, so `rebuild_circuit`'s verification
    loop for one whole element type never ran — an identity check that fires only
    when the example happens to contain the element is not a check. Exercised
    here on a circuit that does contain one.
    """
    from engcore.domains.electrical.dc import DCCurrentSource

    circuit = cases.CIRCUIT
    with_source = type(circuit)(
        circuit_id=circuit.circuit_id,
        nodes=circuit.nodes,
        resistors=circuit.resistors,
        voltage_sources=circuit.voltage_sources,
        current_sources=(
            DCCurrentSource("I1", "n1", "gnd", Quantity(0.25, "ampere")),
        ),
        description=circuit.description,
    )
    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    # The problem states nothing about I1, so the pairing must be refused.
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_circuit(payloads["problem"], with_source.to_dict())


def test_the_slab_refuses_a_boundary_set_the_solver_does_not_implement():
    """C-4, added after the adversarial pass.

    The solver reads no boundary record. A payload declaring a different set
    would therefore execute the homogeneous-Dirichlet physics while the records
    describe something else, and nothing refused it until now.
    """
    payloads = encodings.ENCODINGS["col-slab"].to_payloads()
    problem = json.loads(json.dumps(payloads["problem"]))
    for condition in problem["boundary_conditions"]:
        if condition["name"] == "left":
            condition["value"]["magnitude"] = 5.0
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_slab(problem, payloads["structure"])


def test_the_slab_refuses_an_initial_profile_it_cannot_represent():
    """The reconstruction is only valid because the profile is hard-coded.

    Recorded as a refusal rather than hidden: a payload naming any other profile
    would rebuild an object that computes different physics than the records
    describe, and no record can state what that physics is.
    """
    payloads = encodings.ENCODINGS["col-slab"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["initial_profile"] = "exp(-x/L)"
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_slab(payloads["problem"], structure)


# =====================================================================
# Execution — in process, against the domains' own baseline
# =====================================================================

def _baseline(column: str) -> dict[str, float]:
    from engcore.domains.electrical.dc import solve_circuit
    from engcore.domains.kinetics.cstr import solve_reactor
    from engcore.domains.thermal.conduction1d import solve_slab

    if column == "col-dc":
        result = solve_circuit(cases.CIRCUIT, run_id="baseline-dc")
    elif column == "col-slab":
        result = solve_slab(cases.SLAB, run_id="baseline-slab")
    elif column == "col-cstr":
        result = solve_reactor(cases.RUN, run_id="baseline-cstr")
    else:
        raise AssertionError(column)
    return {name: q.magnitude for name, q in result.values.items()}


@pytest.mark.parametrize(
    "column,tolerance",
    [
        ("col-dc", DC_TOLERANCE),
        ("col-slab", SLAB_TOLERANCE),
        ("col-cstr", CSTR_TOLERANCE),
    ],
)
def test_reconstructed_execution_matches_the_baseline(column, tolerance):
    payloads = encodings.ENCODINGS[column].to_payloads()
    produced = bridge.execute(
        column, payloads["problem"], payloads.get("structure"), run_id=f"rec-{column}"
    )
    expected = _baseline(column)
    assert set(produced) == set(expected)
    for name, value in expected.items():
        scale = max(1.0, abs(value))
        assert abs(produced[name] - value) <= tolerance * scale, name


def test_the_material_column_executes_from_the_problem_alone():
    payloads = encodings.ENCODINGS["col-material"].to_payloads()
    produced = bridge.execute(
        "col-material",
        payloads["problem"],
        None,
        temperature=cases.CONDUCTOR_TEMPERATURE,
    )
    conductor = cases.CONDUCTOR
    expected = conductor.reference_resistance.magnitude_in("ohm") * (
        1.0
        + conductor.temperature_coefficient.magnitude_in("1/kelvin")
        * (
            cases.CONDUCTOR_TEMPERATURE.magnitude_in("kelvin")
            - conductor.reference_temperature.magnitude_in("kelvin")
        )
    )
    assert abs(produced["resistance"] - expected) <= 1e-12 * abs(expected)


# =====================================================================
# Fresh process — §10, mandatory
# =====================================================================

def _write_records(directory: pathlib.Path, column: str) -> pathlib.Path:
    directory.mkdir(parents=True, exist_ok=True)
    payloads = encodings.ENCODINGS[column].to_payloads()
    (directory / "problem.json").write_text(
        json.dumps(payloads["problem"], sort_keys=True, indent=2), encoding="utf-8"
    )
    if "structure" in payloads:
        (directory / "structure.json").write_text(
            json.dumps(payloads["structure"], sort_keys=True, indent=2),
            encoding="utf-8",
        )
    return directory


def _run_child(directory: pathlib.Path, column: str, provider: str = "native") -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "experiments.exec_spec_residue.child",
            str(directory),
            column,
            provider,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, f"child failed: {proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize(
    "column,tolerance",
    [
        ("col-dc", DC_TOLERANCE),
        ("col-slab", SLAB_TOLERANCE),
        ("col-cstr", CSTR_TOLERANCE),
    ],
)
def test_a_fresh_interpreter_reconstructs_and_executes(column, tolerance, tmp_path):
    """§10. A separate process, given two JSON files and two strings.

    Nothing crosses from this process: no object graph, no registry, no import
    state. The child is launched with ``-B`` so it does not even inherit written
    bytecode as a side channel.
    """
    directory = _write_records(tmp_path / column, column)
    reported = _run_child(directory, column)
    assert reported["column"] == column
    assert reported["original_artifact_modules_loaded"] == [], (
        "the fresh process loaded the module holding the original artifacts"
    )
    expected = _baseline(column)
    assert set(reported["metrics"]) == set(expected)
    for name, value in expected.items():
        scale = max(1.0, abs(value))
        assert abs(reported["metrics"][name] - value) <= tolerance * scale, name


def test_the_fresh_process_receives_only_data(tmp_path):
    """What crosses the boundary is two files, and both are plain JSON."""
    directory = _write_records(tmp_path / "col-dc", "col-dc")
    written = sorted(p.name for p in directory.iterdir())
    assert written == ["problem.json", "structure.json"]
    for path in directory.iterdir():
        json.loads(path.read_text(encoding="utf-8"))


# =====================================================================
# Relocation — §11
# =====================================================================

def test_relocating_the_records_changes_no_scientific_identity(tmp_path):
    """Moving the bytes cannot change what they mean. DATA-BOUNDARY0's rule.

    The circuit's own fingerprint is the scientific identity here, and it is a
    function of the canonical description alone — no path, no directory, no host.
    """
    first = _write_records(tmp_path / "site-a" / "col-dc", "col-dc")
    second = tmp_path / "site-b" / "elsewhere"
    second.mkdir(parents=True)
    for path in first.iterdir():
        (second / path.name).write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    payloads = encodings.ENCODINGS["col-dc"].to_payloads()
    here = bridge.rebuild_circuit(payloads["problem"], payloads["structure"])
    there = bridge.rebuild_circuit(
        json.loads((second / "problem.json").read_text(encoding="utf-8")),
        json.loads((second / "structure.json").read_text(encoding="utf-8")),
    )
    assert here.fingerprint() == there.fingerprint()
    assert here == there

    reported_a = _run_child(first, "col-dc")
    reported_b = _run_child(second, "col-dc")
    assert reported_a["metrics"] == reported_b["metrics"]

    blob = json.dumps(payloads, sort_keys=True)
    for fragment in (str(tmp_path), "site-a", "site-b", "C:\\", "/home/"):
        assert fragment not in blob


# =====================================================================
# External provider — §13
# =====================================================================

def _ngspice_available() -> bool:
    try:
        from engcore.domains.electrical.ngspice import NgspiceInvocation

        NgspiceInvocation().probe_version()
    except Exception:  # noqa: BLE001 - availability, not correctness
        return False
    return True


@pytest.mark.skipif(
    not _ngspice_available(), reason="ngspice is not reachable in this environment"
)
def test_the_external_provider_accepts_the_reconstructed_structure(tmp_path):
    """§13. No original in-memory circuit, no bind state, no new semantics.

    The adapter is not modified: it receives a `DCCircuit` rebuilt from records
    and emits its netlist from that, exactly as it does from a circuit built in
    memory.
    """
    directory = _write_records(tmp_path / "provider", "col-dc")
    reported = _run_child(directory, "col-dc", provider="ngspice")
    native = _baseline("col-dc")
    assert set(reported["metrics"]) == set(native)
    for name, value in native.items():
        scale = max(1.0, abs(value))
        assert abs(reported["metrics"][name] - value) <= PROVIDER_TOLERANCE * scale, name


# =====================================================================
# Architecture fitness
# =====================================================================

#: The one file a later, execution-portability-only milestone
#: (`ngspice-cross-platform-portability`) is documented and authorized to
#: touch: `NgspiceInvocation`'s executable discovery, so the same provider
#: adapter reaches a native Linux `ngspice` as readily as the WSL route this
#: milestone's own machine used. No scientific model, result semantics or
#: validation logic changed there — see
#: docs/ngspice-cross-platform-portability-evidence.md. This guard's own
#: claim (EXEC-SPEC touches nothing under `src/`) is unaffected: it was true
#: when this milestone was written, and that fact does not change.
_PORTABILITY_EXCEPTION = "src/engcore/domains/electrical/ngspice.py"

#: The two files a later, model-discovery-only milestone
#: (`planner-provided-capabilities`) is documented and authorized to touch:
#: adding a `provided_capabilities` field to `ScientificModelDefinition` and
#: a matching `ModelRegistry.providers_of` query method, so a deterministic
#: caller can answer "which models provide capability X" without name
#: parsing or a metadata side-channel. No exec-spec structured-input
#: behaviour changed there — see
#: docs/planner-provided-capabilities-evidence.md. This guard's own claim
#: (EXEC-SPEC touches nothing under `src/`) is unaffected: it was true when
#: this milestone was written, and that fact does not change.
_PLANNER_DISCOVERY_EXCEPTIONS = {
    "src/engcore/scientific/models/definition.py",
    "src/engcore/scientific/models/registry.py",
}

#: The files a later milestone (`MIN-FIELD-SUPPORT-FOUNDATION`) is
#: documented and authorized to touch: an additive `data_references` field
#: on `ScientificProblem` (schema bumped to /2, reader accepts /1 and /2),
#: a new standalone `BoundaryOrientation`/`classify_sign` module, extending
#: `VariableBulkLinkage.check_against` to also resolve against
#: `problem.data_references`, and wiring both into the real Fluid domain
#: (boundary-orientation refusal, mesh-dependent validity routing). No
#: exec-spec structured-input behaviour changed there — see
#: docs/min-field-support-foundation-evidence.md. This guard's own claim
#: (EXEC-SPEC touches nothing under `src/`) is unaffected: it was true when
#: this milestone was written, and that fact does not change.
_FIELD_SUPPORT_FOUNDATION_EXCEPTIONS = {
    "src/engcore/scientific/ir/problem.py",
    "src/engcore/scientific/ir/__init__.py",
    "src/engcore/scientific/ir/orientation.py",
    "src/engcore/scientific/results/variable_binding.py",
    "src/engcore/domains/fluids/transport2d/problem.py",
    "src/engcore/domains/fluids/transport2d/solver.py",
    "src/engcore/domains/fluids/transport2d/validation.py",
    "src/engcore/domains/fluids/transport2d/__init__.py",
}


def test_no_src_file_was_added_or_edited():
    """FAIL CONDITION §13.6: this milestone touches nothing under `src/`."""
    diff = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", "src/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    changed = (
        set(diff.stdout.split())
        - {_PORTABILITY_EXCEPTION}
        - _PLANNER_DISCOVERY_EXCEPTIONS
        - _FIELD_SUPPORT_FOUNDATION_EXCEPTIONS
    )
    assert changed == set(), f"src/ was modified: {sorted(changed)}"
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "src/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert untracked.stdout.strip() == "", f"src/ gained files: {untracked.stdout}"


def test_the_milestone_lives_outside_the_package():
    """It cannot be promoted into production core by accident."""
    package = REPO_ROOT / "src" / "engcore"
    hits = [
        str(p.relative_to(REPO_ROOT))
        for p in package.rglob("*.py")
        if "exec_spec_residue" in p.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_no_scientific_problem_schema_moved():
    """FAIL CONDITION §12.6: `scientific_problem/1` is untouched.

    MIN-FIELD-SUPPORT-FOUNDATION additively bumped scientific_problem to
    /2 (a new `data_references` field, reader accepts /1 and /2 — see
    docs/min-field-support-foundation-evidence.md). This test's original
    intent — this milestone's own encodings do not carry a hidden schema
    change of their own — is unaffected; the expected literal moves with
    the (disclosed, additive, backward-compatible) core bump.
    """
    for encoding in encodings.ENCODINGS.values():
        assert encoding.problem.to_dict()["schema"] == "scientific_problem/2"


def test_the_residue_payloads_declare_their_schema():
    """Every payload that crosses the boundary says what it is."""
    for column, encoding in encodings.ENCODINGS.items():
        if encoding.structure_payload is None:
            continue
        assert encoding.structure_payload["schema"] == encoding.structure_schema, column


def test_no_metadata_was_used_to_carry_science():
    """The L2 encodings use the untyped escape hatch for nothing at all."""
    for column, encoding in encodings.ENCODINGS.items():
        assert encoding.problem.metadata == {}, column
