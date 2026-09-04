"""The records-only temporal reader — the instrument for forcing criterion F2.

What it is allowed to do
------------------------
Read the *typed* fields of ``ScientificProblem``, ``ScientificResult``,
``ScientificDataReference``, ``VariableBulkLinkage``, ``QuantityDependency``
and ``RawSolverOutput``. Ask the units contract for a dimensionality. Compare
dimensionalities. Enumerate names.

What it is forbidden to do, and why
-----------------------------------
* **Import any domain or system module.** A reader that imported
  ``thermal_lumped`` could ask ``ThermalBody.duration`` and would then be
  measuring the domain's private record, not the universal one.
* **Parse the internal structure of any name.** ``final_temperature``,
  ``T:final`` and ``t:T_max`` are enumerated names; splitting on ``_`` or
  ``:`` and matching the fragment ``final`` is precisely the meaning-in-key
  failure ``EXEC-SPEC-STRUCTURED`` §C catalogued and refused. Names may be
  compared for equality and nothing else.
* **Read ``metadata``.** It is the untyped side channel this platform refuses
  everywhere else; ``ScientificProblem.validity_context`` is explicitly *not*
  sourced from it, and neither is this.
* **Read a docstring, a description or any prose field.** ``description`` is
  documentation for a human. A records-only reader that read it would be a
  natural-language reader.

The distinction that matters
----------------------------
Every method below returns a ``TemporalAnswer`` carrying an ``Outcome``. The
three outcomes are deliberately not two:

``KNOWN``
    The reader recovered the fact from a typed field.
``UNRECOVERABLE``
    No typed field carries the fact. This is a Ledger A residue.
``AMBIGUOUS``
    Typed fields carry *candidates* and nothing selects among them. This is
    the dangerous outcome and the one this milestone exists to find: an
    ``AMBIGUOUS`` answer is one a naive consumer will silently resolve by
    picking the first, or the only, candidate — and be wrong without any
    check firing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from engcore.scientific.units.quantity import dimensionality

__all__ = [
    "Outcome",
    "TemporalAnswer",
    "RecordsOnlyTemporalReader",
    "TIME_DIMENSION",
]

#: The dimensionality of a second, asked of the units contract rather than
#: spelled as a string. ``[time]`` in Pint's vocabulary.
TIME_DIMENSION = dimensionality("second")


class Outcome(str, Enum):
    KNOWN = "known"
    AMBIGUOUS = "ambiguous"
    UNRECOVERABLE = "unrecoverable"


@dataclass(frozen=True)
class TemporalAnswer:
    """What the reader could say, and what it had to go on."""

    question: str
    outcome: Outcome
    value: Any = None
    #: Typed candidates the reader could see. Non-empty with ``AMBIGUOUS``.
    candidates: tuple[str, ...] = ()
    detail: str = ""

    @property
    def recovered(self) -> bool:
        return self.outcome is Outcome.KNOWN


@dataclass(frozen=True)
class RecordsOnlyTemporalReader:
    """Answers temporal questions from universal records alone."""

    #: Recorded on the instrument itself so a test can assert it: the modules
    #: this reader is allowed to have imported.
    permitted_imports: tuple[str, ...] = field(
        default=("engcore.scientific.units.quantity",)
    )

    # -- Q: is this problem posed over physical time? ----------------------
    def is_time_dependent(self, problem: Any) -> TemporalAnswer:
        """``ScientificProblem.is_time_dependent`` and what it actually means.

        The property is derived from ``initial_conditions`` being non-empty
        and from nothing else. So the reader can report what the record says;
        it cannot report whether the record is *right*, and this method makes
        no claim that it is.
        """
        stated = bool(getattr(problem, "is_time_dependent", False))
        return TemporalAnswer(
            question="is the problem posed over physical time?",
            outcome=Outcome.KNOWN,
            value=stated,
            detail=(
                "derived solely from initial_conditions being non-empty; a "
                "transient problem that declares none reads as False"
            ),
        )

    # -- Q: over what physical interval is it posed? -----------------------
    def physical_horizon(self, problem: Any) -> TemporalAnswer:
        """The interval the problem advances over.

        The only typed handle is dimension: enumerate the parameters whose
        value is a ``Quantity`` of dimension ``[time]``. That is a legitimate
        records-only operation — it reads a unit through the units contract,
        not a name.

        It is also not enough. A time-dimensioned parameter may be an
        integration horizon, a residence time, a relaxation time constant, a
        period or a sampling interval, and no typed field says which. The
        reader therefore returns ``AMBIGUOUS`` whenever it finds candidates
        and ``UNRECOVERABLE`` when it finds none — never ``KNOWN``, because
        there is no case in which it could honestly be sure.
        """
        candidates = tuple(
            parameter.name
            for parameter in getattr(problem, "parameters", ())
            if _is_time_quantity(getattr(parameter, "value", None))
        )
        if not candidates:
            return TemporalAnswer(
                question="over what physical interval is the problem posed?",
                outcome=Outcome.UNRECOVERABLE,
                detail="no parameter carries a [time] dimension",
            )
        return TemporalAnswer(
            question="over what physical interval is the problem posed?",
            outcome=Outcome.AMBIGUOUS,
            candidates=candidates,
            detail=(
                "time-dimensioned parameters exist; nothing typed says which "
                "(if any) is an integration horizon rather than a residence "
                "time, a time constant, a period or a sample interval"
            ),
        )

    # -- Q: at what time does this reported value hold? --------------------
    def time_level_of(self, result: Any, metric: str) -> TemporalAnswer:
        """At which point on the physical time axis does ``metric`` hold?

        There is no typed field anywhere on ``ScientificResult`` that answers
        this. ``values`` is ``name -> Quantity``; the ``Quantity`` carries a
        magnitude and a unit and no coordinate. So the answer is
        ``UNRECOVERABLE`` for every metric of every result, which is exactly
        what makes it worth executing rather than asserting.
        """
        values = dict(getattr(result, "values", {}))
        if metric not in values:
            return TemporalAnswer(
                question=f"at what time does {metric!r} hold?",
                outcome=Outcome.UNRECOVERABLE,
                detail=f"result reports no value named {metric!r}",
            )
        # The steelman the previous milestone's falsifier used to overturn a
        # claimed gap (master context §67.3): ``ProvenanceRecord.inputs`` is a
        # typed ``Mapping[str, Quantity]``, so a producer CAN put a
        # [time]-dimensioned input there and a records-only reader CAN read it
        # without parsing a name. It is consulted here rather than assumed
        # empty.
        provenance = getattr(result, "provenance", None)
        instants = tuple(
            sorted(
                name
                for name, value in dict(
                    getattr(provenance, "inputs", {}) or {}
                ).items()
                if _is_time_quantity(value)
            )
        )
        if not instants:
            return TemporalAnswer(
                question=f"at what time does {metric!r} hold?",
                outcome=Outcome.UNRECOVERABLE,
                detail=(
                    "ScientificResult.values maps a name to a Quantity; a "
                    "Quantity carries a magnitude and a unit and no time "
                    "coordinate. ProvenanceRecord.inputs — the one other "
                    "typed Quantity channel on a result — carries no "
                    "[time]-dimensioned entry either."
                ),
            )
        return TemporalAnswer(
            question=f"at what time does {metric!r} hold?",
            outcome=Outcome.AMBIGUOUS,
            candidates=instants,
            detail=(
                "ProvenanceRecord.inputs carries [time]-dimensioned "
                f"entries {list(instants)}, so a producer CAN record an "
                "instant in a typed field. Nothing relates any of them to "
                f"{metric!r} in particular, or says which is the level the "
                "value holds at."
            ),
        )

    # -- Q: which reported values are the same physical quantity? ----------
    def same_quantity_different_time(self, result: Any) -> TemporalAnswer:
        """Groups of reported values a reader cannot tell apart.

        Collects the result's values by dimensionality. Two values of one
        dimension may be the same physical quantity at two time levels, two
        different physical quantities, or one quantity and one property of the
        same dimension. Nothing typed separates the three.
        """
        groups: dict[str, list[str]] = {}
        for name, quantity in sorted(getattr(result, "values", {}).items()):
            groups.setdefault(str(dimensionality(quantity.units)), []).append(name)
        collisions = tuple(
            f"{dimension}: {sorted(names)}"
            for dimension, names in sorted(groups.items())
            if len(names) > 1
        )
        if not collisions:
            return TemporalAnswer(
                question="which values are one quantity at different times?",
                outcome=Outcome.UNRECOVERABLE,
                detail="no two values share a dimension in this result",
            )
        return TemporalAnswer(
            question="which values are one quantity at different times?",
            outcome=Outcome.AMBIGUOUS,
            candidates=collisions,
            detail=(
                "values sharing a dimension are indistinguishable as "
                "(same quantity, different time) / (different quantities) / "
                "(a quantity and a property of the same dimension)"
            ),
        )

    # -- Q: when does each sample of a bulk array exist? -------------------
    def sample_times(
        self, reference: Any, siblings: Sequence[Any] = ()
    ) -> TemporalAnswer:
        """The time coordinate of a bulk array's samples.

        ``ScientificDataReference`` carries name, unit, count, dtype, digest
        and digest algorithm. ``count`` is documented as a count of values and
        explicitly not a shape, mesh, topology or support. Nothing states an
        ordering, an independent coordinate, or a pairing with another array.
        """
        fields = tuple(
            sorted(
                key
                for key in vars(reference)
                if not key.startswith("_")
            )
        )
        # A sibling reference of [time] dimension and equal count is the
        # strongest circumstantial evidence available. It is circumstantial,
        # not a statement, and the outcome says so — but it is READ, so this
        # answer is a function of its arguments.
        candidate_coordinates = tuple(
            sorted(
                sibling.name
                for sibling in siblings
                if sibling is not reference
                and dimensionality(sibling.unit) == TIME_DIMENSION
                and sibling.count == reference.count
            )
        )
        if candidate_coordinates:
            return TemporalAnswer(
                question="when does each sample of this bulk array exist?",
                outcome=Outcome.AMBIGUOUS,
                candidates=candidate_coordinates,
                detail=(
                    "a sibling reference of [time] dimension and equal count "
                    f"exists ({list(candidate_coordinates)}). Equal count is "
                    "a coincidence a reader can observe, not a statement any "
                    "record makes: nothing says the two are paired, ordered "
                    "the same way, or that either is a coordinate."
                ),
            )
        return TemporalAnswer(
            question="when does each sample of this bulk array exist?",
            outcome=Outcome.UNRECOVERABLE,
            candidates=fields,
            detail=(
                "the reference's entire typed surface is "
                f"{list(fields)}; none of it is a coordinate, an ordering "
                "statement, or a pairing with another reference, and no "
                "sibling reference of [time] dimension and equal count was "
                "offered"
            ),
        )

    # -- Q: which of two arrays is the independent coordinate? -------------
    def independent_coordinate(
        self,
        references: Sequence[Any],
        linkages: Sequence[Any] = (),
    ) -> TemporalAnswer:
        """Given several references (and their variable linkages), which one
        is the independent coordinate the others are functions of?

        ``VariableBulkLinkage`` states "``reference_name``'s values, in the
        reference's own order, are the values of variable ``variable_name``".
        That is a per-array statement. It says nothing about any relationship
        *between* two arrays — not that they are the same length, not that
        sample ``i`` of one corresponds to sample ``i`` of the other, and not
        that one is the coordinate of the other.
        """
        by_dimension: dict[str, list[str]] = {}
        for reference in references:
            by_dimension.setdefault(
                str(dimensionality(reference.unit)), []
            ).append(reference.name)
        time_like = tuple(sorted(by_dimension.get(str(TIME_DIMENSION), ())))
        if not time_like:
            return TemporalAnswer(
                question="which array is the independent time coordinate?",
                outcome=Outcome.UNRECOVERABLE,
                detail="no reference carries a [time] dimension",
            )
        # ``count`` IS typed and readable, so a reader can observe whether the
        # lengths even agree. Booking that in Ledger B rather than claiming
        # total blindness: what a reader cannot do is know they were SUPPOSED
        # to agree, or which array is the coordinate of which.
        counts = {reference.name: reference.count for reference in references}
        lengths_agree = len(set(counts.values())) == 1
        return TemporalAnswer(
            question="which array is the independent time coordinate?",
            outcome=Outcome.AMBIGUOUS,
            candidates=time_like,
            value={"counts": counts, "lengths_agree": lengths_agree},
            detail=(
                "a [time]-dimensioned reference exists, and counts "
                f"{counts} are readable — so a reader can OBSERVE whether "
                "lengths agree. What no typed field states is that they were "
                "required to agree, that sample i of one corresponds to "
                "sample i of another, or which array is the coordinate of "
                f"which; {len(tuple(linkages))} linkage(s) each name one "
                "array's variable and relate no two arrays"
            ),
        )

    # -- Q: did anything discontinuous happen, and when? -------------------
    def events(self, problem: Any, result: Any = None) -> TemporalAnswer:
        """Discontinuities on the physical time axis.

        Nothing on ``ScientificProblem`` or ``ScientificResult`` is an event.
        ``InitialCondition.time`` is the nearest thing: a ``Quantity | None``
        on a record whose name says *initial*. The reader reports what it can
        see — the set of declared condition times — and says outright that a
        condition time is not an event.
        """
        conditions = tuple(getattr(problem, "initial_conditions", ()))
        times = tuple(
            f"{c.variable}@{c.time}"
            for c in conditions
            if getattr(c, "time", None) is not None
        )
        # Two conditions on ONE variable at two stated instants is the closest
        # thing to a declared discontinuity the records permit — and the core
        # accepts it without comment. The reader reports it as a candidate,
        # not as an event, because nothing says the second SUPERSEDES the
        # first rather than contradicting it.
        per_variable: dict[str, int] = {}
        for condition in conditions:
            per_variable[condition.variable] = (
                per_variable.get(condition.variable, 0) + 1
            )
        restated = tuple(
            sorted(name for name, n in per_variable.items() if n > 1)
        )
        if restated:
            return TemporalAnswer(
                question="did a discontinuity occur, and at what time?",
                outcome=Outcome.AMBIGUOUS,
                candidates=restated,
                detail=(
                    f"variable(s) {list(restated)} carry more than one "
                    "declared condition, which the core accepts without "
                    "comment. Nothing says whether the later one supersedes "
                    "the earlier (a discontinuity), refines it, or "
                    "contradicts it — and nothing orders them."
                ),
            )
        return TemporalAnswer(
            question="did a discontinuity occur, and at what time?",
            outcome=Outcome.UNRECOVERABLE,
            candidates=times,
            detail=(
                "no typed field on any universal record denotes an event, an "
                "event time, or a before/after partition of a time axis. "
                "InitialCondition.time states when a condition applies, not "
                "that anything changed there."
            ),
        )

    # -- Q: how was the state reached? -------------------------------------
    def history(self, result: Any) -> TemporalAnswer:
        """The path by which a reported state was reached.

        ``ProvenanceRecord.parent_run_id`` chains runs, and it is worth being
        precise about what that is: a single optional string naming one
        predecessor run. It is not ordered against a physical clock, it does
        not say how much physical time elapsed between the two runs, it
        carries no branch semantics, and nothing forbids two different physical
        histories from producing identical chains.
        """
        provenance = getattr(result, "provenance", None)
        parent = getattr(provenance, "parent_run_id", None)
        if parent is not None:
            return TemporalAnswer(
                question="by what path was this state reached?",
                outcome=Outcome.AMBIGUOUS,
                candidates=(str(parent),),
                detail=(
                    f"ProvenanceRecord.parent_run_id names {parent!r}, so ONE "
                    "predecessor is recoverable. Nothing states how much "
                    "physical time elapsed between the two, nothing orders "
                    "them against a clock, and two different physical "
                    "histories may produce identical chains."
                ),
            )
        return TemporalAnswer(
            question="by what path was this state reached?",
            outcome=Outcome.UNRECOVERABLE,
            candidates=(),
            detail=(
                "the only path-shaped typed field is "
                "ProvenanceRecord.parent_run_id: one optional predecessor "
                "run id, with no elapsed physical time, no ordering against a "
                "clock, and no statement of what differed between the runs"
            ),
        )

    # -- Q: how much runtime did this cost? --------------------------------
    def wall_clock(self, result: Any, raw: Any = None) -> TemporalAnswer:
        """Wall-clock runtime, and where it is allowed to live.

        ``RawSolverOutput.wall_seconds`` exists. ``ScientificResult`` has no
        such field, and no ``ScientificResult`` in this repository carries one.
        The reader reports that separation as a KNOWN fact, because it is one:
        the contracts already place runtime outside the interpreted record.
        """
        on_result = hasattr(result, "wall_seconds")
        on_raw = raw is not None and getattr(raw, "wall_seconds", None) is not None
        return TemporalAnswer(
            question="how much wall-clock runtime did this cost?",
            outcome=Outcome.KNOWN,
            value={"on_result": on_result, "on_raw_output": on_raw},
            detail=(
                "RawSolverOutput.wall_seconds carries runtime; "
                "ScientificResult has no wall-clock field at all"
            ),
        )


def _is_time_quantity(value: Any) -> bool:
    """True when ``value`` is a Quantity of dimension ``[time]``.

    Duck-typed on ``units`` rather than isinstance-checked against ``Quantity``,
    so that the non-Quantity members of the ``ScientificValue`` union (integer,
    boolean, categorical) fall through without the reader having to import the
    union.
    """
    unit = getattr(value, "units", None)
    if unit is None:
        return False
    try:
        return dimensionality(unit) == TIME_DIMENSION
    except Exception:  # pragma: no cover - a non-unit string cannot occur here
        return False


def answers_by_outcome(
    answers: Sequence[TemporalAnswer],
) -> Mapping[Outcome, tuple[str, ...]]:
    """Group answers by outcome — the shape the evidence tables are built from."""
    grouped: dict[Outcome, list[str]] = {outcome: [] for outcome in Outcome}
    for answer in answers:
        grouped[answer.outcome].append(answer.question)
    return {outcome: tuple(questions) for outcome, questions in grouped.items()}


# =====================================================================
# The instrument's own variance — required by the falsifier (finding C.2)
# =====================================================================

@dataclass(frozen=True)
class MethodVariance:
    """Whether one reader method's outcome is a function of its argument."""

    method: str
    outcomes_observed: tuple[str, ...]

    @property
    def varies(self) -> bool:
        return len(self.outcomes_observed) > 1


def instrument_variance() -> tuple[MethodVariance, ...]:
    """Publish how many of this instrument's own cells actually move.

    `architecture-falsifier` returned this milestone's second BLOCKER: four
    reader methods returned ``UNRECOVERABLE`` for **every possible argument**,
    so a test asserting that outcome asserted nothing about the records. It
    was the third consecutive Crafty milestone to earn that finding — master
    context §67.3 and §68.3 record the two before it — and the first not to
    have applied the published defence, which is to *measure the instrument*.

    This function is that defence. Each method is exercised against two
    deliberately different arguments and the distinct outcomes are reported.
    A method whose ``varies`` is False is one whose answer is a property of
    the reader, and any claim resting on it must say so.

    Nothing here is a contract; it is the instrument reporting on itself.
    """
    from engcore.scientific.results.data_reference import (
        ScientificDataReference,
    )
    from engcore.scientific.results.provenance import ProvenanceRecord
    from engcore.scientific.results.result import ScientificResult
    from engcore.scientific.ir.conditions import InitialCondition
    from engcore.scientific.ir.problem import ScientificProblem
    from engcore.scientific.ir.variables import (
        ScientificVariable,
        VariableRole,
    )
    from engcore.scientific.units.quantity import Quantity

    reader = RecordsOnlyTemporalReader()
    kelvin, second = "kelvin", "second"

    def _result(*, inputs=None, parent=None, values=None) -> ScientificResult:
        return ScientificResult(
            result_id="variance",
            values=values or {"T": Quantity(300.0, kelvin)},
            provenance=ProvenanceRecord(
                run_id="variance",
                inputs=inputs or {},
                parent_run_id=parent,
            ),
        )

    bare = _result()
    stamped = _result(inputs={"t_eval": Quantity(600.0, second)})
    chained = _result(parent="earlier-run")
    two_values = _result(
        values={"T": Quantity(300.0, kelvin), "T_ss": Quantity(310.0, kelvin)}
    )

    variable = ScientificVariable(name="T", unit=kelvin, role=VariableRole.STATE)
    empty_problem = ScientificProblem(problem_id="v0", variables=(variable,))
    one_condition = ScientificProblem(
        problem_id="v1",
        variables=(variable,),
        initial_conditions=(
            InitialCondition("T", Quantity(300.0, kelvin), time=Quantity(0.0, second)),
        ),
    )
    two_conditions = ScientificProblem(
        problem_id="v2",
        variables=(variable,),
        initial_conditions=(
            InitialCondition("T", Quantity(300.0, kelvin), time=Quantity(0.0, second)),
            InitialCondition("T", Quantity(350.0, kelvin), time=Quantity(300.0, second)),
        ),
    )
    timed_problem = ScientificProblem(
        problem_id="v3",
        variables=(variable,),
        parameters=(
            __import__(
                "engcore.scientific.ir.variables", fromlist=["ScientificParameter"]
            ).ScientificParameter(name="duration", value=Quantity(600.0, second)),
        ),
    )

    values_reference = ScientificDataReference(
        name="v", unit=kelvin, count=11, digest="aa" * 32
    )
    time_reference = ScientificDataReference(
        name="t", unit=second, count=11, digest="bb" * 32
    )

    def _outcomes(*answers: TemporalAnswer) -> tuple[str, ...]:
        return tuple(sorted({a.outcome.value for a in answers}))

    return (
        MethodVariance(
            "is_time_dependent",
            _outcomes(
                reader.is_time_dependent(empty_problem),
                reader.is_time_dependent(one_condition),
            ),
        ),
        MethodVariance(
            "physical_horizon",
            _outcomes(
                reader.physical_horizon(empty_problem),
                reader.physical_horizon(timed_problem),
            ),
        ),
        MethodVariance(
            "time_level_of",
            _outcomes(
                reader.time_level_of(bare, "T"),
                reader.time_level_of(stamped, "T"),
                reader.time_level_of(bare, "absent"),
            ),
        ),
        MethodVariance(
            "same_quantity_different_time",
            _outcomes(
                reader.same_quantity_different_time(bare),
                reader.same_quantity_different_time(two_values),
            ),
        ),
        MethodVariance(
            "sample_times",
            _outcomes(
                reader.sample_times(values_reference),
                reader.sample_times(values_reference, (time_reference,)),
            ),
        ),
        MethodVariance(
            "independent_coordinate",
            _outcomes(
                reader.independent_coordinate((values_reference,)),
                reader.independent_coordinate((values_reference, time_reference)),
            ),
        ),
        MethodVariance(
            "events",
            _outcomes(
                reader.events(one_condition),
                reader.events(two_conditions),
            ),
        ),
        MethodVariance(
            "history",
            _outcomes(reader.history(bare), reader.history(chained)),
        ),
        MethodVariance(
            "wall_clock",
            _outcomes(reader.wall_clock(bare)),
        ),
    )
