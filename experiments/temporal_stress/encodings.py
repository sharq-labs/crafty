"""Z1-Z8 — the zero-new-contract attempts.

Preregistration §6 binds this module: **no residue may be declared before a
maximal honest attempt with the existing typed contracts has been executed.**
Every attempt therefore returns an :class:`EncodingAttempt` carrying *two*
lists, and the evidence document is required to print both:

``achieved``
    Ledger B. What the existing contracts genuinely expressed. A milestone
    that reports only what failed is advocating, not measuring.
``residue``
    Ledger A. What no typed field carried, with the reason.

Nothing in this module defines a temporal type, and nothing in it writes to
``src/``. Every record constructed here is an existing universal record used
exactly as its own contract permits.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Sequence

from engcore.domains import thermal_lumped as lump
from engcore.scientific.composition import QuantityDependency
from engcore.scientific.ir.conditions import InitialCondition
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from engcore.scientific.results.data_reference import (
    ScientificDataReference,
    content_digest,
    encode_float64,
)
from engcore.scientific.results.provenance import ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.variable_binding import (
    VariableBulkLinkage,
    unlinked_references,
)
from engcore.scientific.units.quantity import Quantity, dimensionality

from .reader import Outcome, RecordsOnlyTemporalReader

__all__ = [
    "EncodingAttempt",
    "z1_time_level_in_metric_name",
    "z2_one_variable_per_time_level",
    "z3_time_as_a_parameter",
    "z4_time_varying_input_as_two_bulk_references",
    "z5_event_as_problem_splitting",
    "z6_exposure_as_state_or_observable",
    "z7_history_as_dependency_chain",
    "z8_scalar_and_bulk_precedence_under_time",
    "all_attempts",
]

KELVIN = "kelvin"
SECOND = "second"
WATT = "watt"
EXPOSURE_UNIT = "kelvin * second"


@dataclass(frozen=True)
class EncodingAttempt:
    """One zero-new-contract attempt, both ledgers."""

    label: str
    question: str
    #: Ledger B — what the existing typed contracts did express.
    achieved: tuple[str, ...] = ()
    #: Ledger A — what no typed field carried.
    residue: tuple[str, ...] = ()
    #: Machine-checkable facts a test asserts against.
    facts: dict[str, Any] = field(default_factory=dict)

    @property
    def fully_expressible(self) -> bool:
        return not self.residue


def _provenance(run_id: str) -> ProvenanceRecord:
    return ProvenanceRecord(
        run_id=run_id, software_version="experiments.temporal_stress/0.1.0"
    )


def _reference(name: str, unit: str, values: Sequence[float]) -> ScientificDataReference:
    payload = encode_float64(values)
    return ScientificDataReference(
        name=name,
        unit=unit,
        count=len(values),
        digest=content_digest(payload),
    )


# =====================================================================
# Z1 — the time level spelled into an enumerated metric name
# =====================================================================

def z1_time_level_in_metric_name() -> EncodingAttempt:
    """Two executed consumers, two incompatible conventions, one reader.

    C1 reports ``final_temperature`` / ``steady_state_temperature``; C2 reports
    ``T:final`` / ``T:max`` / ``t:T_max``. Both are legal, enumerated,
    round-tripping metric names, and each is perfectly readable by a human.

    The attempt is to have a records-only reader answer *"give me each
    result's temperature at the end of its horizon"*. It cannot, and the two
    ways it fails are different in kind:

    * across consumers, the naming conventions do not agree, so alignment
      would require parsing name fragments — the meaning-in-key failure mode
      this platform has refused repeatedly;
    * within one consumer, ``final_temperature`` and
      ``steady_state_temperature`` share a dimension, share a physical
      variable, and differ only in time level, so no dimension check can
      separate them.
    """
    c1_metrics = (
        lump.TEMPERATURE_METRIC,
        lump.STEADY_STATE_TEMPERATURE_METRIC,
        lump.TIME_CONSTANT_METRIC,
    )
    from engcore.domains.kinetics.cstr import problem as cstr

    c2_metrics = tuple(sorted(cstr.METRIC_UNITS))

    reader = RecordsOnlyTemporalReader()
    result = ScientificResult(
        result_id="z1",
        values={
            lump.TEMPERATURE_METRIC: Quantity(307.98, KELVIN),
            lump.STEADY_STATE_TEMPERATURE_METRIC: Quantity(310.0, KELVIN),
            lump.TIME_CONSTANT_METRIC: Quantity(250.0, SECOND),
        },
        provenance=_provenance("z1"),
    )
    level = reader.time_level_of(result, lump.TEMPERATURE_METRIC)
    collisions = reader.same_quantity_different_time(result)

    return EncodingAttempt(
        label="Z1",
        question="can an enumerated metric name carry the time level?",
        achieved=(
            "a metric name is a stable, typed, round-tripping identifier and "
            "one consumer's own reader can use it as an exact-match key",
            "ScientificProblem._require_metric_coherence already refuses two "
            "declarations of one metric with incompatible dimensions",
            "C1's module comment already states the rule that keeps its own "
            "namespaces apart: 'temperature' the state and 'final_temperature' "
            "the metric must stay distinct names",
        ),
        residue=(
            "no typed field relates a metric to a time level; the reader "
            f"returns {level.outcome.value} for every metric of every result",
            "two consumers use incompatible conventions "
            f"({c1_metrics[0]!r} vs {'T:final'!r}); aligning them requires "
            "parsing a name's internal structure, which is refused",
            "final_temperature and steady_state_temperature are the same "
            "physical variable, the same dimension, different time levels, "
            "and a dimension check cannot separate them",
        ),
        facts={
            "c1_metrics": c1_metrics,
            "c2_metrics": c2_metrics,
            "time_level_outcome": level.outcome.value,
            "collision_outcome": collisions.outcome.value,
            "collision_candidates": collisions.candidates,
        },
    )


# =====================================================================
# Z2 — one declared variable per time level
# =====================================================================

def z2_one_variable_per_time_level() -> EncodingAttempt:
    """Declare ``temperature_t0`` and ``temperature_t1`` as separate variables.

    This encodes. ``ScientificProblem`` accepts both, they carry the right
    unit, the right role and independent bounds, and a records-only reader can
    enumerate them.

    What it cannot state is that they are *the same physical quantity*. To the
    records they are two unrelated kelvin-valued variables, exactly as
    ``temperature`` and ``ambient_temperature`` are. The relation a consumer
    actually needs — same quantity, two instants, ordered — has no home, and
    the encoding gets worse rather than better as time levels multiply: n
    levels means n variables, so the declaration scales O(N) with the number
    of instants a study cares about, which is the shape DATA-BOUNDARY0 exists
    to keep out of control-plane records.
    """
    problem = ScientificProblem(
        problem_id="z2",
        variables=(
            ScientificVariable(
                name="temperature_t0", unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name="temperature_t1", unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name="ambient_temperature", unit=KELVIN, role=VariableRole.CONTROL
            ),
        ),
    )
    dimensions = {
        v.name: str(dimensionality(v.unit)) for v in problem.variables
    }
    indistinguishable = len(set(dimensions.values())) == 1
    return EncodingAttempt(
        label="Z2",
        question="can one variable per time level carry temporal structure?",
        achieved=(
            "both levels declare, carry units, carry roles and round-trip",
            "a records-only reader can enumerate them",
        ),
        residue=(
            "nothing states that temperature_t0 and temperature_t1 are one "
            "physical quantity; to the records they are as unrelated as "
            "temperature_t0 and ambient_temperature, which share the same "
            "dimension",
            "nothing orders them: no typed field says t0 precedes t1",
            "the declaration scales O(N) in the number of instants, putting "
            "history-length growth into a control-plane record",
        ),
        facts={
            "variables": tuple(v.name for v in problem.variables),
            "all_one_dimension": indistinguishable,
            "dimensions": dimensions,
        },
    )


# =====================================================================
# Z3 — time as an ordinary parameter
# =====================================================================

def z3_time_as_a_parameter() -> EncodingAttempt:
    """``ScientificParameter`` carrying seconds — the steelman, executed.

    A parameter of dimension ``[time]`` encodes without complaint. So the
    records *can* carry a time-valued number. What they cannot carry is which
    role that number plays, and the two consumers already in the repository
    disagree in a way that makes the ambiguity concrete rather than
    hypothetical: C1's only time-dimensioned parameter is an integration
    horizon (``duration``); C2's only time-dimensioned parameter is a material
    residence time (``residence_time``) and its horizon is not on the record at
    all.

    A reader that took "the time-dimensioned parameter" to be the horizon
    would be right about C1 and wrong about C2, with nothing to warn it.
    """
    from engcore.domains.kinetics.cstr import problem as cstr

    body = lump.ThermalBody(
        body_id="z3",
        heat_capacity=Quantity(400.0, "joule/kelvin"),
        ambient_conductance=Quantity(2.0, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, KELVIN),
        initial_temperature=Quantity(300.0, KELVIN),
        duration=Quantity(600.0, SECOND),
    )
    c1_problem = lump.build_lumped_thermal_problem(body)
    run = cstr.ReactorRun(
        run_label="z3",
        chemistry=cstr.ReactorChemistry(
            k0=Quantity(1.0e10, "1/s"),
            activation_energy=Quantity(72_000.0, "J/mol"),
            heat_of_reaction=Quantity(-50_000.0, "J/mol"),
            density=Quantity(1000.0, "kg/m**3"),
            heat_capacity=Quantity(4180.0, "J/(kg*K)"),
        ),
        operation=cstr.ReactorOperation(
            volume=Quantity(1.0, "m**3"),
            flow_rate=Quantity(0.005, "m**3/s"),
            feed_concentration=Quantity(1000.0, "mol/m**3"),
            feed_temperature=Quantity(300.0, KELVIN),
            coolant_temperature=Quantity(295.0, KELVIN),
            ua=Quantity(500.0, "W/K"),
            end_time=Quantity(400.0, SECOND),
        ),
        initial_concentration=Quantity(1000.0, "mol/m**3"),
        initial_temperature=Quantity(300.0, KELVIN),
    )
    c2_problem = cstr.build_cstr_problem(run)

    reader = RecordsOnlyTemporalReader()
    c1_answer = reader.physical_horizon(c1_problem)
    c2_answer = reader.physical_horizon(c2_problem)
    c1_time_dependent = reader.is_time_dependent(c1_problem)
    c2_time_dependent = reader.is_time_dependent(c2_problem)

    return EncodingAttempt(
        label="Z3",
        question="can an ordinary parameter carry the physical time coordinate?",
        achieved=(
            "a [time]-dimensioned ScientificParameter encodes, validates and "
            "round-trips; the records can carry a time-valued number",
            "a records-only reader can find every time-dimensioned parameter "
            "by dimension alone, without parsing any name",
            "InitialCondition.time exists and accepts a Quantity, so 'this "
            "condition holds at this instant' is representable per condition",
        ),
        residue=(
            "nothing says what role a time-dimensioned parameter plays: C1's "
            f"{c1_answer.candidates} is an integration horizon and C2's "
            f"{c2_answer.candidates} is a material residence time, and the "
            "reader returns AMBIGUOUS for both",
            "C2's actual horizon (end_time) appears on NO universal record: "
            "it lives in the domain's ReactorOperation and reaches the "
            "problem only inside an opaque metadata fingerprint",
            "consequently C2 — a genuinely transient stiff integration — "
            f"reports is_time_dependent={c2_time_dependent.value}",
            "a parameter states a value at a time; it cannot state a function "
            "of time",
        ),
        facts={
            "c1_horizon_outcome": c1_answer.outcome.value,
            "c1_horizon_candidates": c1_answer.candidates,
            "c2_horizon_outcome": c2_answer.outcome.value,
            "c2_horizon_candidates": c2_answer.candidates,
            "c1_is_time_dependent": c1_time_dependent.value,
            "c2_is_time_dependent": c2_time_dependent.value,
            "c2_parameter_names": tuple(p.name for p in c2_problem.parameters),
            "c2_initial_condition_count": len(c2_problem.initial_conditions),
            # The concrete wrongness: a reader taking "the [time] parameter"
            # to be the horizon reads 200 s for a problem integrated to 400 s.
            "c2_recorded_time_parameter_s": c2_problem.parameter(
                "residence_time"
            ).value.magnitude_in(SECOND),
            "c2_actual_horizon_s": run.operation.end_time_s,
            "c1_recorded_time_parameter_s": c1_problem.parameter(
                lump.DURATION
            ).value.magnitude_in(SECOND),
            "c1_actual_horizon_s": body.duration_s,
        },
    )


# =====================================================================
# Z4 — a time-varying input as two bulk references + two linkages
# =====================================================================

def z4_time_varying_input_as_two_bulk_references() -> EncodingAttempt:
    """The strongest available encoding of ``ambient_temperature(t)``.

    A real scientific case: C1's ambient is a declared ``CONTROL`` variable,
    and a body cooling to a diurnally varying ambient is ordinary physics. The
    maximal honest attempt uses everything the platform has for bulk input:

    * two ``ScientificDataReference``s on ``ScientificProblem.data_references``
      — one values array in kelvin, one coordinate array in seconds;
    * two declared ``ScientificVariable``s to bind them to;
    * two ``VariableBulkLinkage``s, each checked with ``check_against`` and
      each returning **no issues**.

    Everything that check can check, passes. That is Ledger B and it is
    substantial: variable identity, unit, dimensional agreement, resolution
    against the problem's own reference set, and O(1) control-plane records
    naming O(N) arrays that never enter them.

    What no typed field states is the *relationship between the two arrays*:
    that they are the same length, that sample ``i`` of one corresponds to
    sample ``i`` of the other, and that one is the independent coordinate the
    other is a function of. A linkage is a per-array statement by construction
    — its own module docstring says so — and two per-array statements do not
    compose into a pairing.
    """
    times = tuple(float(i) * 60.0 for i in range(11))
    ambient = tuple(300.0 + 8.0 * math.sin(t / 600.0) for t in times)

    time_reference = _reference("ambient_temperature/t", SECOND, times)
    value_reference = _reference("ambient_temperature/values", KELVIN, ambient)

    problem = ScientificProblem(
        problem_id="z4",
        variables=(
            ScientificVariable(
                name=lump.TEMPERATURE, unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name=lump.AMBIENT_TEMPERATURE,
                unit=KELVIN,
                role=VariableRole.CONTROL,
            ),
            # The steelman's own move: declare the coordinate as a variable so
            # that a linkage has something to bind the time array to.
            ScientificVariable(
                name="sample_time", unit=SECOND, role=VariableRole.OBSERVABLE
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE,
                value=Quantity(300.0, KELVIN),
                time=Quantity(0.0, SECOND),
            ),
        ),
        data_references=(time_reference, value_reference),
    )
    linkages = (
        VariableBulkLinkage(
            variable_name=lump.AMBIENT_TEMPERATURE,
            reference_name=value_reference.name,
        ),
        VariableBulkLinkage(
            variable_name="sample_time", reference_name=time_reference.name
        ),
    )
    issues = tuple(
        issue
        for linkage in linkages
        for issue in linkage.check_against(problem=problem)
    )

    reader = RecordsOnlyTemporalReader()
    coordinate = reader.independent_coordinate(problem.data_references, linkages)
    samples = reader.sample_times(value_reference)

    # The mismatched-length case: nothing refuses it.
    short_time_reference = _reference("bad/t", SECOND, times[:5])
    bad_problem = ScientificProblem(
        problem_id="z4-mismatched",
        variables=problem.variables,
        data_references=(short_time_reference, value_reference),
    )
    bad_linkages = (
        VariableBulkLinkage(
            variable_name=lump.AMBIENT_TEMPERATURE,
            reference_name=value_reference.name,
        ),
        VariableBulkLinkage(
            variable_name="sample_time", reference_name=short_time_reference.name
        ),
    )
    bad_issues = tuple(
        issue
        for linkage in bad_linkages
        for issue in linkage.check_against(problem=bad_problem)
    )

    return EncodingAttempt(
        label="Z4",
        question="can bulk references + linkages carry a time-varying input?",
        achieved=(
            "two O(1) references name two O(N) arrays that never enter a "
            "control-plane record — DATA-BOUNDARY0 is preserved intact",
            "each array's variable identity, unit and dimensional agreement "
            "with its declared variable are typed and checked",
            "VariableBulkLinkage.check_against resolves both against "
            "ScientificProblem.data_references and returns no issues",
            "content digests give both arrays relocation-stable identity",
        ),
        residue=(
            "nothing states that the two arrays are paired, that they are the "
            "same length, or that sample i of one corresponds to sample i of "
            "the other; a 5-sample coordinate against an 11-sample value "
            f"array raises {len(bad_issues)} issues",
            "nothing states that one array is the INDEPENDENT coordinate the "
            f"other is a function of; the reader returns "
            f"{coordinate.outcome.value} over "
            f"{list(coordinate.candidates)}",
            "'sample_time' had to be declared as an OBSERVABLE variable, "
            "which is false: it is not produced by the solve, it is the axis "
            "the solve is posed over. VariableRole has no member for it",
            "the encoding cannot distinguish a time history from a spatial "
            "field: both are 'a values array plus a coordinate array', and "
            "MIN-FIELD-SUPPORT already uses that shape for space",
        ),
        facts={
            "linkage_issues": len(issues),
            "mismatched_length_issues": len(bad_issues),
            "coordinate_outcome": coordinate.outcome.value,
            "coordinate_candidates": coordinate.candidates,
            "sample_times_outcome": samples.outcome.value,
            "reference_fields": samples.candidates,
            "unlinked": unlinked_references(problem, linkages),
        },
    )


# =====================================================================
# Z5 — an event as a problem split
# =====================================================================

def z5_event_as_problem_splitting() -> EncodingAttempt:
    """A heater switching off at t = 300 s, encoded as two problems.

    This is the honest maximum. Each segment is a well-formed
    ``ScientificProblem`` with its own ``InitialCondition``, its own
    ``duration`` and its own imposed heat, and ``InitialCondition.time`` can
    even carry the absolute instant each segment starts at. C1's realization
    explicitly assumes a constant heat input over the integrated interval, so
    splitting at the discontinuity is not a workaround — it is the correct way
    to pose it.

    What the records do not say is that the two problems are two segments of
    one physical timeline. They are two independent problems. Nothing states
    that segment B follows segment A, that they abut at 300 s, that the same
    body is involved, or that the heat input was discontinuous there rather
    than the study simply asking two unrelated questions.
    """
    common = dict(
        heat_capacity=Quantity(400.0, "joule/kelvin"),
        ambient_conductance=Quantity(2.0, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, KELVIN),
    )
    before = lump.ThermalBody(
        body_id="z5",
        initial_temperature=Quantity(300.0, KELVIN),
        duration=Quantity(300.0, SECOND),
        **common,
    )
    problem_before = lump.build_lumped_thermal_problem(
        before, problem_id="z5-before"
    )
    solver = lump.LumpedThermalSolver()
    solver.bind_body(before, "z5-before", heat_input=Quantity(40.0, WATT))
    prepared = solver.prepare(problem_before)
    raw = solver.solve(prepared)
    switch_state = solver.extract_metrics(prepared, raw)[lump.TEMPERATURE_METRIC]

    after = lump.ThermalBody(
        body_id="z5",
        initial_temperature=switch_state,
        duration=Quantity(300.0, SECOND),
        **common,
    )
    problem_after = lump.build_lumped_thermal_problem(after, problem_id="z5-after")
    # The strongest thing the records permit: stamp the absolute instant.
    stamped_after = ScientificProblem(
        problem_id=problem_after.problem_id,
        variables=problem_after.variables,
        parameters=problem_after.parameters,
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE,
                value=switch_state,
                time=Quantity(300.0, SECOND),
            ),
        ),
        models=problem_after.models,
        required_capabilities=problem_after.required_capabilities,
    )

    reader = RecordsOnlyTemporalReader()
    event_answer = reader.events(stamped_after)

    return EncodingAttempt(
        label="Z5",
        question="can 'an event occurs at t_e' be stated without solver code?",
        achieved=(
            "each segment is a complete, valid, independently solvable "
            "ScientificProblem posed over its own interval",
            "InitialCondition.time carries the absolute instant a segment's "
            "state is stated at — so 'this value holds at t = 300 s' IS "
            "representable, per condition",
            "the segment boundary can be placed exactly at the discontinuity, "
            "which is what C1's constant-input realization requires anyway",
        ),
        residue=(
            "nothing relates the two problems: no typed field says B follows "
            "A, that they abut, or that they concern one physical timeline",
            "nothing says WHAT changed at the boundary; the heat input is a "
            "declared CONTROL with no value on either record, so the "
            "discontinuity is invisible even in principle",
            "nothing distinguishes 'one system across an event' from 'two "
            "unrelated studies of similar bodies'",
            f"the reader returns {event_answer.outcome.value} for the event "
            "question: InitialCondition.time states when a condition applies, "
            "not that anything changed there",
            "an event schedule of n switches needs n+1 problems, so the "
            "declaration again scales O(N) in the event count",
        ),
        facts={
            "switch_state_k": switch_state.magnitude_in(KELVIN),
            "event_outcome": event_answer.outcome.value,
            "stamped_condition_times": event_answer.candidates,
            "problems": (problem_before.problem_id, stamped_after.problem_id),
        },
    )


# =====================================================================
# Z6 — accumulated exposure: state variable, or observable?
# =====================================================================

def z6_exposure_as_state_or_observable() -> EncodingAttempt:
    """Encode ``E(t) = ∫₀ᵗ f(T(τ))dτ`` both ways and compare what is stated.

    (a) a ``STATE`` variable with an ``InitialCondition`` of zero;
    (b) an ``OBSERVABLE`` metric reported on the result.

    Both encode. Neither is refused, nothing warns that one is being used, and
    a records-only reader cannot tell which was intended — because to the
    records, (a) is exactly what a temperature state looks like and (b) is
    exactly what a final temperature looks like.

    The classification question A6 asks is therefore answered by measurement:
    the existing contracts do not distinguish "state variable", "derived
    observable", "history" and "relation result" for this quantity. They
    express (a) and (b) equally well and say nothing that separates them, so
    the choice is a convention, not a typed fact.
    """
    as_state = ScientificProblem(
        problem_id="z6-state",
        variables=(
            ScientificVariable(
                name=lump.TEMPERATURE, unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name="thermal_exposure",
                unit=EXPOSURE_UNIT,
                role=VariableRole.STATE,
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE, value=Quantity(300.0, KELVIN)
            ),
            InitialCondition(
                variable="thermal_exposure", value=Quantity(0.0, EXPOSURE_UNIT)
            ),
        ),
    )
    as_observable = ScientificProblem(
        problem_id="z6-observable",
        variables=(
            ScientificVariable(
                name=lump.TEMPERATURE, unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name="thermal_exposure",
                unit=EXPOSURE_UNIT,
                role=VariableRole.OBSERVABLE,
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE, value=Quantity(300.0, KELVIN)
            ),
        ),
    )
    result = ScientificResult(
        result_id="z6",
        values={
            lump.TEMPERATURE_METRIC: Quantity(307.98, KELVIN),
            "thermal_exposure:final": Quantity(2732.83, EXPOSURE_UNIT),
        },
        provenance=_provenance("z6"),
    )
    return EncodingAttempt(
        label="Z6",
        question="is accumulated exposure a state, an observable, or history?",
        achieved=(
            "an integral functional of the path encodes as a STATE variable "
            "with a zero InitialCondition, and the core validates the "
            "condition's dimension against the variable's",
            "the same quantity encodes equally well as an OBSERVABLE and as a "
            "reported result value carrying its K*s unit",
            "so the ANSWER TO A6 IS: existing contracts express it as a state "
            "variable, and that encoding is honest and O(1)",
        ),
        residue=(
            "nothing distinguishes the two encodings; a records-only reader "
            "sees a kelvin-second variable with a role, and roles do not "
            "encode 'accumulated over the path'",
            "nothing states that thermal_exposure is a functional OF another "
            "declared variable — the dependence on temperature is invisible",
            "nothing states the accumulation window; 'exposure since when' "
            "has no home, and two results reporting 2732.83 K*s over "
            "different windows are indistinguishable",
        ),
        facts={
            "state_encoding_variables": tuple(
                (v.name, v.role.value) for v in as_state.variables
            ),
            "observable_encoding_variables": tuple(
                (v.name, v.role.value) for v in as_observable.variables
            ),
            "state_is_time_dependent": as_state.is_time_dependent,
            "observable_is_time_dependent": as_observable.is_time_dependent,
            "exposure_reported": result.value(
                "thermal_exposure:final"
            ).magnitude_in(EXPOSURE_UNIT),
        },
    )


# =====================================================================
# Z7 — history as a dependency chain
# =====================================================================

def z7_history_as_dependency_chain() -> EncodingAttempt:
    """``QuantityDependency`` between segment problems — the last steelman.

    ``QuantityDependency`` is the platform's one record for "the quantity X of
    problem P supplies the quantity Y of problem Q". Chaining it across the
    segments of a schedule is the closest existing thing to a stated history.

    It does express supply, and that is real: a records-only reader can walk
    the chain and recover the order in which segments fed each other. What it
    cannot express is anything *temporal* about that order — how much physical
    time each segment spanned, whether the segments abut, whether any physical
    time elapsed between them at all, or what varied along the way. Two
    schedules with identical chains and different durations are identical
    records.
    """
    chain = (
        QuantityDependency(
            source_problem_id="seg-1",
            source_quantity=lump.TEMPERATURE_METRIC,
            target_problem_id="seg-2",
            target_quantity=lump.TEMPERATURE,
            unit_exemplar=KELVIN,
            name="seg1-to-seg2",
        ),
        QuantityDependency(
            source_problem_id="seg-2",
            source_quantity=lump.TEMPERATURE_METRIC,
            target_problem_id="seg-3",
            target_quantity=lump.TEMPERATURE,
            unit_exemplar=KELVIN,
            name="seg2-to-seg3",
        ),
    )
    fields = tuple(sorted(QuantityDependency.__dataclass_fields__))
    return EncodingAttempt(
        label="Z7",
        question="can a dependency chain carry scientific history?",
        achieved=(
            "supply is stated and typed: 'seg-1's final_temperature supplies "
            "seg-2's temperature', with a dimension the record carries",
            "a records-only reader can walk the chain and recover the order "
            "in which segments fed one another",
            "the chain is O(1) per edge, so it does not scale with the number "
            "of samples inside a segment",
        ),
        residue=(
            f"QuantityDependency's whole surface is {list(fields)}: no "
            "elapsed time, no start, no end, no ordering against a clock",
            "nothing says the segments abut; a schedule with 300 s gaps and "
            "one without produce identical chains",
            "nothing says what varied along the path, so two schedules that "
            "meet at the same endpoint through different histories chain "
            "identically",
            "the chain scales O(N) in the number of segments, so a fine "
            "schedule puts history length into control-plane records",
        ),
        facts={
            "chain_length": len(chain),
            "dependency_fields": fields,
            "carries_time": any("time" in f for f in fields),
        },
    )


# =====================================================================
# Z8 — scalar/bulk precedence, stressed temporally
# =====================================================================

def z8_scalar_and_bulk_precedence_under_time() -> EncodingAttempt:
    """The prose-only precedence rule, put under a temporal load.

    ``ScientificProblem.data_references`` carries a prose rule
    (MIN-FIELD-SUPPORT, falsifier finding C.1): when a variable carries both a
    scalar ``InitialCondition`` and a bulk reference bound by a
    ``VariableBulkLinkage``, **the bulk form is authoritative and the scalar is
    representative-only**.

    Two problems are built here that are *structurally identical* under that
    rule and mean different things:

    ``spatial``
        ``temperature`` has a scalar ``InitialCondition`` of 300 K and an
        11-value bulk array — a non-uniform initial field. The prose rule is
        correct: the array is the state at t₀ and the scalar is a
        representative value.
    ``temporal``
        ``ambient_temperature`` has a representative scalar and an 11-value
        bulk array that is a *time series* of the imposed control. Here the
        prose rule is not merely unhelpful, it is **wrong**: the array is not
        "the variable's initial/boundary state", it is the whole input
        trajectory, and reading element 0 as "the state" would silently
        discard ten samples.

    Nothing typed separates the two cases. Both are (variable, scalar,
    11-element reference, linkage), both check clean, and the rule that governs
    them is a sentence in a docstring that no reader can execute.
    """
    field_values = tuple(300.0 + 2.0 * i for i in range(11))
    series_values = tuple(300.0 + 8.0 * math.sin(i / 3.0) for i in range(11))
    field_reference = _reference("temperature/field", KELVIN, field_values)
    series_reference = _reference("ambient_temperature/series", KELVIN, series_values)

    spatial = ScientificProblem(
        problem_id="z8-spatial",
        variables=(
            ScientificVariable(
                name=lump.TEMPERATURE, unit=KELVIN, role=VariableRole.STATE
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE,
                value=Quantity(300.0, KELVIN),
                description="representative only; the field is authoritative",
            ),
        ),
        data_references=(field_reference,),
    )
    temporal = ScientificProblem(
        problem_id="z8-temporal",
        variables=(
            ScientificVariable(
                name=lump.TEMPERATURE, unit=KELVIN, role=VariableRole.STATE
            ),
            ScientificVariable(
                name=lump.AMBIENT_TEMPERATURE,
                unit=KELVIN,
                role=VariableRole.CONTROL,
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.TEMPERATURE, value=Quantity(300.0, KELVIN)
            ),
            # A representative scalar for the time-varying CONTROL. Note in
            # passing that the core accepts an InitialCondition on a CONTROL
            # variable without comment: nothing says a control has no initial
            # value, and nothing says this one is a representative sample of a
            # trajectory rather than the control's value at t0.
            InitialCondition(
                variable=lump.AMBIENT_TEMPERATURE,
                value=Quantity(300.0, KELVIN),
                description="representative only; the series is authoritative",
            ),
        ),
        data_references=(series_reference,),
    )
    spatial_linkage = VariableBulkLinkage(
        variable_name=lump.TEMPERATURE, reference_name=field_reference.name
    )
    temporal_linkage = VariableBulkLinkage(
        variable_name=lump.AMBIENT_TEMPERATURE,
        reference_name=series_reference.name,
    )
    spatial_issues = spatial_linkage.check_against(problem=spatial)
    temporal_issues = temporal_linkage.check_against(problem=temporal)

    # The signatures a records-only reader can see, side by side.
    def _signature(problem: ScientificProblem, linkage: VariableBulkLinkage):
        reference = problem.data_reference(linkage.reference_name)
        return {
            "variable_unit": problem.variable(linkage.variable_name).unit,
            "reference_unit": reference.unit,
            "count": reference.count,
            "dtype": reference.dtype,
            "has_scalar_condition": any(
                c.variable == linkage.variable_name
                for c in problem.initial_conditions
            ),
        }

    spatial_signature = _signature(spatial, spatial_linkage)
    temporal_signature = _signature(temporal, temporal_linkage)

    return EncodingAttempt(
        label="Z8",
        question="does the prose scalar/bulk precedence survive a time series?",
        achieved=(
            "both configurations construct, both linkages check clean, and "
            "both keep the O(N) array outside every control-plane record",
            "the prose rule is stated where a maintainer will find it, on the "
            "field it governs, and it is correct for the spatial case it was "
            "written for",
        ),
        residue=(
            "no typed field carries the precedence rule, so no reader can "
            "apply it; a consumer reading only initial_conditions computes "
            "with a wrong uniform state and nothing fires",
            "the rule's own words — 'the bulk reference is authoritative for "
            "that variable's actual initial/boundary state' — are FALSE for a "
            "time series: the array is a trajectory, not a state at an "
            "instant, and element 0 is not 'the state'",
            "the spatial and temporal cases are indistinguishable to a "
            f"records-only reader: {spatial_signature} vs "
            f"{temporal_signature} differ in no field that carries meaning",
            "the scalar's ROLE differs between the two cases (representative "
            "sample of a field vs representative sample of a trajectory) and "
            "nothing records which",
        ),
        facts={
            "spatial_issues": len(spatial_issues),
            "temporal_issues": len(temporal_issues),
            "spatial_signature": spatial_signature,
            "temporal_signature": temporal_signature,
            "signatures_agree_on_every_typed_field": (
                spatial_signature == temporal_signature
            ),
        },
    )


def all_attempts() -> tuple[EncodingAttempt, ...]:
    return (
        z1_time_level_in_metric_name(),
        z2_one_variable_per_time_level(),
        z3_time_as_a_parameter(),
        z4_time_varying_input_as_two_bulk_references(),
        z5_event_as_problem_splitting(),
        z6_exposure_as_state_or_observable(),
        z7_history_as_dependency_chain(),
        z8_scalar_and_bulk_precedence_under_time(),
    )
