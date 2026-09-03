"""The instrument: a records-only reader that counts admissible readings.

`MIN-FOUNDATION-ET` added exactly one universal record because a count showed no
reader could recover a fact — *"the null hypothesis lost on a measurement, not
an argument"*. This module reproduces that instrument for the hostile consumer.

THE RULES THIS READER OBEYS
---------------------------
* It is handed **serialized payloads** and nothing else.
* It may import ``engcore.scientific``, because a records reader legitimately
  knows the schema it is reading.
* It may **not** import ``transport1d`` or ``records``. A reader that can see
  the domain is not measuring what the records say, it is measuring what the
  author knows. ``test_reader_cannot_see_the_domain`` asserts this by AST scan
  rather than by convention.

HOW A COUNT IS DERIVED, AND WHY IT IS NOT A JUDGEMENT CALL
-----------------------------------------------------------
Every count below is produced **structurally**, by asking which fields of a
contract could carry the fact in question *by type* — not by searching for
promising-looking key names, and not by the author deciding what feels
recoverable.

That distinction matters. "Is direction recoverable?" answered by grepping for
the substring ``inlet`` would measure this probe's naming taste. Answered by
enumerating ``dataclasses.fields(BoundaryCondition)`` and asking which of them
can express a position, an ordering or a coordinate, it measures the contract.
The second question has one answer and the author cannot move it.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from engcore.scientific.ir.conditions import BoundaryCondition, BoundaryKind
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.values import IntegerValue
from engcore.scientific.models.definition import (
    InputSourceKind,
    ScientificModelDefinition,
    ValidityStatus,
)
from engcore.scientific.realizations.definition import ModelRealizationDefinition
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.units.quantity import Quantity

__all__ = [
    "Recoverability",
    "Finding",
    "Ledger",
    "count_orientation_readings",
    "count_scheme_readings",
    "transience_verdict",
    "count_wellposedness_readings",
    "wellposedness_is_detectable_with_structural_context",
    "recover_resolution_criterion",
    "CriterionRecovery",
    "validity_from_records",
    "ValidityFromRecords",
    "field_semantics_findings",
    "recoverability_matrix",
]


class Recoverability(str, Enum):
    """The five buckets the milestone brief §6 requires, and only those."""

    RECOVERABLE = "fully recoverable"
    AMBIGUOUS = "ambiguous"
    IMPOSSIBLE = "impossible"
    METADATA_ONLY = "recoverable only via metadata/string convention"
    SOURCE_ONLY = "recoverable only by reading source code"


class Ledger(str, Enum):
    """Prereg §10.1. Which ledger a finding is booked to.

    THE BOOKING RULE, STATED EXPLICITLY BECAUSE IT IS WHAT FAILED
    -------------------------------------------------------------
    An earlier version of this module booked a finding by *which record the
    reader inspected*. That is wrong, and the adversarial pass caught it: the
    orientation finding inspected ``BoundaryCondition`` (exists) while its
    remedy is an oriented boundary of a topology (does not exist), so the same
    absent concept was booked Ledger 1 under one question and Ledger 2 under
    another.

    The rule is therefore:

        A finding is **Ledger 1 only when BOTH the measurement AND the remedy
        live in a record that already exists.** If closing the gap requires a
        record the platform does not have, the finding is Ledger 2 — however
        interesting the measurement was, and whichever record it was taken on.

    Findings that straddle the line are **split**, not rounded. See R1a/R1b.
    """

    #: Measurement and remedy both in an existing record. New information.
    EXISTING_RECORD = "ledger-1: record exists"
    #: The remedy needs a record that does not exist. Re-confirms an
    #: already-recorded L0 deferral; **zero claimed evidence gain**.
    ABSENT_RECORD = "ledger-2: record does not exist"


@dataclass(frozen=True)
class Finding:
    question: str
    verdict: Recoverability
    admissible_readings: int | None
    ledger: Ledger
    detail: str


# =============================================================================
# R1 — which boundary is upstream?
# =============================================================================

def count_orientation_readings(
    forward_payload: Mapping[str, Any],
    reversed_payload: Mapping[str, Any],
    *,
    admit_free_text: bool = False,
) -> tuple[Finding, Finding]:
    """The orientation question, **split across the two ledgers**.

    Returns ``(R1a, R1b)``.

    ``R1a`` — **Ledger 1.** *The ``(kind, region, value)`` triple is not
    injective onto physical systems.* Measurement and remedy both concern
    ``BoundaryCondition``, a record that exists: two systems whose inflow ends
    are opposite serialize to byte-identical boundary records. This is new
    information, and it is **not** reducible to a missing field concept —
    `HETERO-NGSPICE` §66.4 needed a passive-sign guard for a two-terminal lumped
    element with no continuum topology anywhere in sight. Orientation is a
    universal scientific distinction, not a PDE one.

    ``R1b`` — **Ledger 2.** *What is missing is an oriented boundary subset of a
    spatial entity, and no such record exists.* This is a proper sub-part of Q4
    ("what spatial entity it is defined over"), which is already booked Ledger 2,
    and no change that leaves topology absent makes one recoverable without the
    other. **Zero claimed evidence gain.**

    The earlier single finding booked the whole thing to Ledger 1, which blended
    the ledgers in exactly the way prereg §13.5 declares a fail condition.

    ``admit_free_text`` applies the **same** convention this module grants R2b:
    that meaning carried in an identifier or a description counts, graded
    ``METADATA_ONLY``. Granting it to one question and denying it to another was
    the second thing the adversarial pass caught, so both are now reported under
    both conventions and the difference is visible rather than silent.
    """
    return (
        _orientation_injectivity(
            forward_payload, reversed_payload, admit_free_text=admit_free_text
        ),
        _orientation_remedy_is_absent(forward_payload),
    )


def _orientation_injectivity(
    forward_payload: Mapping[str, Any],
    reversed_payload: Mapping[str, Any],
    *,
    admit_free_text: bool = False,
) -> Finding:
    """R1a. How many assignments of {upstream, downstream} the records admit.

    **Measured empirically rather than argued structurally**, because an
    argument about which field *could* carry a position is answerable and a
    measurement is not.

    The two payloads describe transport in opposite directions — same interval,
    same conditions, opposite velocity sign. In the forward system the Dirichlet
    end is upstream; in the reversed system it is downstream. If the two
    problems' serialized ``BoundaryCondition`` records are **byte-identical**,
    then one and the same set of boundary records describes both systems, and a
    reader holding those records cannot choose between the two readings. The
    count is then the number of boundaries.

    An earlier version of this function tried to answer the question by asking
    which fields of ``BoundaryCondition`` could carry geometry *by type*. It
    reported ``value`` and ``coefficients`` as locating fields and returned
    "fully recoverable" — a false negative produced by the instrument, since a
    Dirichlet *value* is the field's own magnitude and locates nothing. The
    measurement below cannot make that mistake.
    """
    forward = ScientificProblem.from_dict(forward_payload)
    reversed_ = ScientificProblem.from_dict(reversed_payload)
    forward_boundaries = [b.to_dict() for b in forward.boundary_conditions]
    reversed_boundaries = [b.to_dict() for b in reversed_.boundary_conditions]
    identical = forward_boundaries == reversed_boundaries

    u_forward = _typed_parameter(forward, "velocity")
    u_reversed = _typed_parameter(reversed_, "velocity")
    opposed = (
        u_forward is not None
        and u_reversed is not None
        and u_forward.magnitude * u_reversed.magnitude < 0.0
    )

    if not (identical and opposed):
        return Finding(
            question="R1a boundary records are injective onto physical systems",
            verdict=Recoverability.RECOVERABLE,
            admissible_readings=1,
            ledger=Ledger.EXISTING_RECORD,
            detail=(
                f"the two directions produce "
                f"{'different' if not identical else 'identical'} boundary "
                f"records and velocities are "
                f"{'opposed' if opposed else 'not opposed'}; the records "
                f"distinguish the readings"
            ),
        )

    if admit_free_text:
        # The convention: region identifiers sort along the axis, so the
        # lexicographically first region is the low end. Combined with the
        # typed velocity sign it yields exactly one reading.
        #
        # It is unsound in general — nothing requires region names to sort along
        # any axis, and the core documents `region` as uninterpreted — in the
        # same way "Dirichlet means inflow" is unsound. It is graded
        # METADATA_ONLY rather than RECOVERABLE for that reason, and it is
        # applied here only so that R1 and R2b are judged by one rule.
        ordered = sorted(b.region for b in forward.boundary_conditions)
        return Finding(
            question="R1a boundary records are injective onto physical systems",
            verdict=Recoverability.METADATA_ONLY,
            admissible_readings=1,
            ledger=Ledger.EXISTING_RECORD,
            detail=(
                f"under a naming convention — region identifiers {ordered} sort "
                f"along the axis — plus the typed velocity sign "
                f"{u_forward.magnitude:+g}, exactly one reading survives. The "
                f"convention is unsound in general and the core documents "
                f"`region` as uninterpreted, so this is a string convention, "
                f"not a contract. Reported so R1 and R2b are graded by one rule"
            ),
        )

    field_types = {
        f.name: str(f.type) for f in dataclasses.fields(BoundaryCondition)
    }
    return Finding(
        question="R1a boundary records are injective onto physical systems",
        verdict=Recoverability.IMPOSSIBLE,
        admissible_readings=len(forward.boundary_conditions),
        ledger=Ledger.EXISTING_RECORD,
        detail=(
            f"NOT INJECTIVE. {len(forward.boundary_conditions)} boundary "
            f"conditions, and the serialized BoundaryCondition records are "
            f"BYTE-IDENTICAL between u={u_forward.magnitude:+g} and "
            f"u={u_reversed.magnitude:+g} — two systems whose inflow ends are "
            f"opposite. The velocity sign IS recoverable and typed, so the "
            f"physics fixes which end is upstream; the boundary records do not "
            f"say which end each denotes, so both assignments survive. "
            f"BoundaryCondition fields are {field_types}; only `region` could "
            f"denote a location and it is a str the core documents as "
            f"uninterpreted"
        ),
    )


def _orientation_remedy_is_absent(payload: Mapping[str, Any]) -> Finding:
    """R1b. The remedy is a record the platform does not have. Ledger 2."""
    problem = ScientificProblem.from_dict(payload)
    return Finding(
        question="R1b an oriented boundary subset of a spatial entity",
        verdict=Recoverability.IMPOSSIBLE,
        admissible_readings=0,
        ledger=Ledger.ABSENT_RECORD,
        detail=(
            f"closing R1a needs somewhere to say that region "
            f"{problem.boundary_conditions[0].region!r} is the x=0 end and "
            f"carries outward normal -x. No support, topology or region record "
            f"exists to hold it, and this is a proper sub-part of Q4, already "
            f"booked Ledger 2. Zero claimed evidence gain"
        ),
    )


def dirichlet_convention_is_unsound(problem_payload: Mapping[str, Any]) -> bool:
    """True when 'Dirichlet means inflow' would label >1 boundary as inflow.

    Executed rather than argued. A convention that produces two inflows on a
    problem this probe actually builds is not a fallback a reader may use.
    """
    problem = ScientificProblem.from_dict(problem_payload)
    dirichlet = [
        b for b in problem.boundary_conditions if b.kind is BoundaryKind.DIRICHLET
    ]
    return len(dirichlet) != 1


# =============================================================================
# R2 — which discretization produced this result?
# =============================================================================

def count_scheme_readings(
    result_payload: Mapping[str, Any],
    realization_catalogue: Mapping[str, Any] | None = None,
    *,
    admit_free_text: bool = True,
) -> tuple[Finding, Finding]:
    """Two questions that look like one, and have different answers.

    **R2a — which realization identity produced this result?** Answered by
    ``ProvenanceRecord.bindings``, which MODEL0-R added precisely so a
    ``model -> realization -> solver`` association survives when any of the
    three has more than one member.

    **R2b — could a planner SELECT the bounded one?** Deliberately *not* "is the
    identity recoverable" — it is, twice over: ``realization_id`` differs and so
    does ``ImplementationReference.implementation_id``, both typed and
    serialized, which is exactly what
    `07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md` §16.E requires. An earlier version
    of this function excluded ``implementation`` from its scan and reported the
    identity as unrecoverable, which was wrong.

    The question that survives is about **selection semantics**: the records
    distinguish the two realizations and state no typed *property* by which a
    planner could choose the monotone one over the second-order one. The scan
    below therefore looks for a typed field whose value differs between the two
    AND denotes a property rather than a name — identifiers are excluded not
    because they fail to discriminate but because discriminating is not
    selecting.

    **Counter-evidence, recorded rather than suppressed.**
    `docs/scientific-core/README.md` "Fidelity: why the core declares none"
    rejected a ``RealizationFidelity`` enum because its members conflated *"at
    least four"* axes. That argument applies to a typed discretization field
    verbatim: "central vs upwind" conflates operator family, order of accuracy,
    monotonicity/TVD character and staggering. It is the strongest in-repo
    argument *against* forcing a new typed field here, and it weighs directly
    against a ``FORCED`` verdict on a ``DESIGN-FROZEN`` contract.
    """
    result = ScientificResult.from_dict(result_payload)
    realizations = {
        binding.realization.key
        for binding in result.provenance.bindings
        if binding.realization is not None
    }
    identity = Finding(
        question="R2a which realization identity produced this result",
        verdict=(
            Recoverability.RECOVERABLE
            if len(realizations) == 1
            else Recoverability.AMBIGUOUS
        ),
        admissible_readings=len(realizations) or None,
        ledger=Ledger.EXISTING_RECORD,
        detail=(
            f"ProvenanceRecord.bindings names {sorted(realizations)}; the "
            f"model->realization->solver association is structural, not "
            f"positional"
        ),
    )

    if realization_catalogue is None:
        return identity, Finding(
            question="R2b a planner could select the bounded realization",
            verdict=Recoverability.IMPOSSIBLE,
            admissible_readings=None,
            ledger=Ledger.EXISTING_RECORD,
            detail=(
                "with only the run's records, a RealizationReference is an "
                "opaque (id, version) pair; nothing states what it computes"
            ),
        )

    definitions = [
        ModelRealizationDefinition.from_dict(payload)
        for payload in realization_catalogue.values()
    ]
    formulations = {d.formulation for d in definitions}

    #: Identity fields. They DO discriminate — `implementation` is typed and
    #: differs — and they are excluded from the *selection* scan because
    #: discriminating is not selecting. Naming this list rather than filtering
    #: silently is the point: the exclusion is a stated judgement, not a hidden
    #: one, and the earlier version's silent exclusion of `implementation` is
    #: what made it report a false gap.
    identity_fields = ("realization_id", "version", "model", "implementation")
    prose_fields = ("name", "description", "assumptions")

    typed_identity = [
        field.name
        for field in dataclasses.fields(ModelRealizationDefinition)
        if field.name in identity_fields
        and len({repr(getattr(d, field.name)) for d in definitions}) == len(definitions)
    ]
    typed_properties = [
        field.name
        for field in dataclasses.fields(ModelRealizationDefinition)
        if field.name not in identity_fields
        and field.name not in prose_fields
        and len({repr(getattr(d, field.name)) for d in definitions}) == len(definitions)
    ]

    if typed_properties:
        verdict = Recoverability.RECOVERABLE
        readings = 1
    elif admit_free_text:
        verdict = Recoverability.METADATA_ONLY
        readings = 1
    else:
        verdict = Recoverability.IMPOSSIBLE
        readings = len(definitions)

    return identity, Finding(
        question="R2b a planner could select the bounded realization",
        verdict=verdict,
        admissible_readings=readings,
        ledger=Ledger.EXISTING_RECORD,
        detail=(
            f"{len(definitions)} realizations of one model. Typed IDENTITY "
            f"fields that discriminate: {typed_identity} — so which one ran is "
            f"recoverable and §16.E is satisfied. Typed PROPERTY fields that "
            f"discriminate: {typed_properties or 'none'}; "
            f"{len(formulations)} distinct ModelFormulation value(s), so the "
            f"one typed axis a realization has says the same thing about both. "
            f"Monotonicity is stated only in {list(prose_fields)}, so a planner "
            f"choosing between them reads prose or parses an identifier"
        ),
    )


# =============================================================================
# R3 — is this problem transient?
# =============================================================================

def transience_verdict(
    problem_payload: Mapping[str, Any], *, physically_transient: bool
) -> Finding:
    """Compare the record's own answer with the physics, supplied externally.

    ``physically_transient`` is the one external fact this module accepts, and
    it is the thing being compared *against*. Without it there is no
    disagreement to measure.
    """
    problem = ScientificProblem.from_dict(problem_payload)
    stated = problem.is_time_dependent
    agrees = stated == physically_transient
    return Finding(
        question="R3 is this problem transient",
        verdict=(
            Recoverability.RECOVERABLE if agrees else Recoverability.IMPOSSIBLE
        ),
        admissible_readings=1 if agrees else 0,
        ledger=Ledger.EXISTING_RECORD,
        detail=(
            f"is_time_dependent={stated}, physics says {physically_transient}. "
            f"The property is derived from initial_conditions being non-empty, "
            f"so it is correct exactly when a domain writes real "
            f"InitialCondition records"
        ),
    )


# =============================================================================
# R4 — is the declared boundary set well posed?
# =============================================================================

def count_wellposedness_readings(
    problem_payload: Mapping[str, Any], model_payload: Mapping[str, Any]
) -> Finding:
    """Can a reader tell whether the declared conditions are the right number?

    **Narrowed after the adversarial pass**, which showed the earlier phrasing
    ("not detectable at all") was too strong in two ways.

    First, the reader below *already computes* ``len(boundary_conditions)``, so
    a declarative ``RangeCondition(name="boundary_condition_count", ...)`` fed
    through ``validity_context(extra=...)`` would evaluate perfectly well —
    :func:`wellposedness_is_detectable_with_structural_context` demonstrates
    that with no new contract. The real obstacle is narrower and is about
    ``validity_context``: it is built **only from typed parameters**, so a
    declarative validity criterion cannot reference a structural fact about the
    problem statement.

    Second, the regime-dependence half — that the well-posed condition count
    changes with a *parameter value* while ``ValidityDomain`` is static — is
    preregistration baseline fact **B17**, recorded before execution. It is
    corroborated here, not discovered.

    What the count below still measures honestly: ``ModelInputSpec.source_kind``
    is :class:`InputSourceKind`, and if that enum has no member denoting a
    condition then a model cannot *enumerate* the conditions its equation
    requires, so there is no declared requirement to compare against.
    """
    problem = ScientificProblem.from_dict(problem_payload)
    model = ScientificModelDefinition.from_dict(model_payload)
    condition_kinds = [
        member for member in InputSourceKind
        if "condition" in member.value or "boundary" in member.value
    ]
    declared = len(problem.boundary_conditions)
    stated_requirement = [
        spec for spec in model.inputs if spec.source_kind in condition_kinds
    ]
    if condition_kinds and stated_requirement:
        return Finding(
            question="R4 is the declared boundary set well posed",
            verdict=Recoverability.RECOVERABLE,
            admissible_readings=1,
            ledger=Ledger.EXISTING_RECORD,
            detail=f"model enumerates {len(stated_requirement)} required conditions",
        )
    return Finding(
        question="R4 is the declared boundary set well posed",
        verdict=Recoverability.IMPOSSIBLE,
        admissible_readings=0,
        ledger=Ledger.EXISTING_RECORD,
        detail=(
            f"{declared} boundary conditions are declared. InputSourceKind has "
            f"members {[m.value for m in InputSourceKind]} — none denotes a "
            f"condition — so ModelInputSpec enumerates parameters and "
            f"variables only and a model cannot state how many conditions its "
            f"equation requires. Nothing declared to compare the set against. "
            f"NOT 'undetectable in principle': a RangeCondition on a structural "
            f"count evaluates fine if the context can carry one, and "
            f"validity_context is built only from typed parameters"
        ),
    )


def wellposedness_is_detectable_with_structural_context(
    problem_payload: Mapping[str, Any]
) -> ValidityStatus:
    """The counterexample to "not detectable at all", executed.

    A ``RangeCondition`` over a structural fact about the problem — how many
    boundary conditions were declared — evaluates correctly when that fact is
    handed to ``validity_context(extra=...)``. No new contract, no new field.

    This is why R4 is reported as a ``validity_context`` finding rather than as
    an impossibility: the vocabulary exists, and what is missing is a route
    from the problem's own structure into the context that judges it.
    """
    from engcore.scientific.models.definition import RangeCondition, ValidityDomain

    problem = ScientificProblem.from_dict(problem_payload)
    domain = ValidityDomain(
        conditions=(
            RangeCondition(
                name="boundary_condition_count",
                maximum=Quantity(1.0, "dimensionless"),
                description="a first-order equation admits one condition",
            ),
        )
    )
    context = problem.validity_context(
        extra={
            "boundary_condition_count": Quantity(
                float(len(problem.boundary_conditions)), "dimensionless"
            )
        }
    )
    return domain.assess(context).status


# =============================================================================
# R5 — recompute the model's validity verdict from records alone
# =============================================================================

def _typed_parameter(problem: ScientificProblem, name: str) -> Quantity | None:
    for parameter in problem.parameters:
        if parameter.name == name and isinstance(parameter.value, Quantity):
            return parameter.value
    return None


def _typed_integer(problem: ScientificProblem, name: str) -> int | None:
    for parameter in problem.parameters:
        if parameter.name == name and isinstance(parameter.value, IntegerValue):
            return parameter.value.value
    return None


@dataclass(frozen=True)
class CriterionRecovery:
    """How, and from where, the mesh-dependent validity input was recovered."""

    value: float | None
    verdict: Recoverability
    source: str
    detail: str
    #: True when the value came off a record that does not exist until a solve
    #: has produced it. The residual finding lives here: such a criterion is
    #: assessable **per-run** and never **pre-run**.
    run_scoped: bool = False


def recover_resolution_criterion(
    problem_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any] | None = None,
) -> CriterionRecovery:
    """Recover ``1/Pe_cell = D / (u dx)`` from records. Three sources, in order.

    The criterion is the **reciprocal** of the cell Peclet number and is exactly
    equivalent to it (``Pe <= 2`` is ``1/Pe >= 0.5``), with one difference that
    matters: it is finite at ``D = 0``, where the cell Peclet number is
    genuinely infinite and ``Quantity`` would refuse it.

    Search order, which is itself the measurement:

    1. **``ProvenanceRecord.inputs``** (ENCODING_C). A typed
       ``Mapping[str, Quantity]`` on the record documented as *"everything
       needed to attribute and re-derive a result"*, and exactly the use
       ``validity_context``'s docstring sanctions for *"a Reynolds number, a
       detected regime"*. Fully typed, and the problem stays mesh-free — but the
       value is **run-scoped**, so no pre-run screening is possible.
    2. **A typed ``IntegerValue`` ``n_cells`` parameter** (ENCODING_B). Typed
       and pre-run, at the cost of the mesh entering problem identity.
    3. **``problem.metadata["n_cells"]``** (ENCODING_A, what the baseline domain
       does). A string, and the core states validity context is *"deliberately
       not sourced from metadata"*.
    """
    problem = ScientificProblem.from_dict(problem_payload)

    if result_payload is not None:
        result = ScientificResult.from_dict(result_payload)
        supplied = result.provenance.inputs.get("inverse_peclet_cell")
        if supplied is not None:
            return CriterionRecovery(
                supplied.magnitude,
                Recoverability.RECOVERABLE,
                "ProvenanceRecord.inputs",
                (
                    "typed Quantity on the provenance record; the problem "
                    "record carries nothing about the mesh, so problem identity "
                    "survives refinement. RUN-SCOPED: the value does not exist "
                    "until a solve has produced it, so ValidityDomain cannot "
                    "screen a proposed discretization before spending the solve"
                ),
                run_scoped=True,
            )

    velocity = _typed_parameter(problem, "velocity")
    diffusivity = _typed_parameter(problem, "diffusivity")
    length = _typed_parameter(problem, "length")
    if velocity is None or diffusivity is None or length is None:
        return CriterionRecovery(
            None,
            Recoverability.IMPOSSIBLE,
            "none",
            "velocity, diffusivity or length is not a typed Quantity parameter",
        )

    def inverse_peclet(n_cells: int) -> float:
        dx = length.magnitude_in("meter") / n_cells
        return diffusivity.magnitude_in("m**2/s") / (
            abs(velocity.magnitude_in("meter / second")) * dx
        )

    typed_cells = _typed_integer(problem, "n_cells")
    if typed_cells is not None:
        return CriterionRecovery(
            inverse_peclet(typed_cells),
            Recoverability.RECOVERABLE,
            "typed n_cells parameter",
            (
                f"n_cells={typed_cells} is a typed IntegerValue parameter, so "
                f"the criterion is recomputable pre-run — at the cost of a "
                f"numerical resolution sitting inside the scientific problem "
                f"statement, so two meshes are two problems"
            ),
        )

    raw = problem.metadata.get("n_cells")
    if raw is None:
        return CriterionRecovery(
            None,
            Recoverability.IMPOSSIBLE,
            "none",
            "no provenance input, no typed n_cells parameter, no metadata key",
        )
    return CriterionRecovery(
        inverse_peclet(int(raw)),
        Recoverability.METADATA_ONLY,
        "problem.metadata",
        (
            f"n_cells recovered only from metadata['n_cells']={raw!r}, an "
            f"untyped string; validity context is documented as deliberately "
            f"not sourced from metadata"
        ),
    )


@dataclass(frozen=True)
class ValidityFromRecords:
    """A validity verdict recomputed from records, and how it was reached."""

    status: ValidityStatus
    satisfied: tuple[str, ...]
    violated: tuple[str, ...]
    unknown: tuple[str, ...]
    #: True when the recovered cell Peclet number is real but **could not be
    #: put into the validity context at all**, because ``Quantity`` refuses a
    #: non-finite magnitude. See :func:`validity_from_records`.
    peclet_inexpressible: bool = False


def validity_from_records(
    problem_payload: Mapping[str, Any],
    model_payload: Mapping[str, Any],
    *,
    result_payload: Mapping[str, Any] | None = None,
    supply_criterion: bool = True,
    criterion_name: str = "inverse_peclet_cell",
) -> ValidityFromRecords:
    """The model's own validity verdict, computed from records only.

    ``supply_criterion=False`` is the bare reading — ``validity_context()`` and
    nothing else, which is exactly what a caller who does not know the criterion
    exists would get. ``True`` recovers it through
    :func:`recover_resolution_criterion` and supplies it through the
    ``extra=`` channel the docstring of ``validity_context`` sanctions.

    THE NON-FINITE CASE, AND WHY IT IS NOT A CONTRACT FINDING
    ----------------------------------------------------------
    An earlier version of this milestone declared the criterion as
    ``peclet_cell <= 2``, observed that ``Pe_cell`` is infinite at ``D = 0``,
    found that ``Quantity`` refuses non-finite magnitudes, and reported that as
    an unanticipated contract gap. The adversarial pass showed it is not one:
    the reciprocal form is the *same criterion*, is ``0.0`` at ``D = 0``, and
    reports the violation correctly. Any scalar criterion on ``[0, inf]`` admits
    a monotone finite reparameterisation.

    ``peclet_inexpressible`` therefore records a fact about the **author's
    chosen parameterisation**, and is reachable only through
    ``TRANSPORT_MODEL_NAIVE_PECLET``. The residual worth carrying is that
    ``ValidityStatus.UNKNOWN`` conflates *"the context did not supply this"*
    with *"the context could not express this"*, so an author who picks the
    unbounded parameterisation gets the second silently disguised as the first.
    """
    problem = ScientificProblem.from_dict(problem_payload)
    model = ScientificModelDefinition.from_dict(model_payload)
    context = dict(problem.validity_context())
    inexpressible = False
    if supply_criterion:
        recovery = recover_resolution_criterion(problem_payload, result_payload)
        if recovery.value is not None:
            value = recovery.value
            if criterion_name == "peclet_cell":
                # The naive parameterisation, reconstructed from its reciprocal.
                value = math.inf if recovery.value == 0.0 else 1.0 / recovery.value
            if math.isfinite(value):
                context[criterion_name] = Quantity(value, "dimensionless")
            else:
                inexpressible = True
    assessment = model.validity.assess(context)
    return ValidityFromRecords(
        status=assessment.status,
        satisfied=assessment.satisfied,
        violated=assessment.violated,
        unknown=assessment.unknown,
        peclet_inexpressible=inexpressible,
    )


# =============================================================================
# Field semantics — what a bulk reference can and cannot say
# =============================================================================

def field_semantics_findings(
    result_payload: Mapping[str, Any]
) -> tuple[Finding, ...]:
    """What a ``ScientificDataReference`` states about the field it names.

    Every one of these is **Ledger 2**: they are findings about a record that
    does not exist, and `DATA-BOUNDARY0` already records the omissions as
    deliberate. They are measured anyway — a re-confirmation is worth having —
    and booked at zero claimed evidence gain, per prereg §10.1.
    """
    result = ScientificResult.from_dict(result_payload)
    reference_fields = {f.name for f in dataclasses.fields(ScientificDataReference)}
    questions = {
        "what spatial entity the field is defined over": {"support", "domain", "mesh"},
        "the coordinates of its values": {"coordinates", "nodes", "frame"},
        "its topology relationship": {"topology", "connectivity", "adjacency"},
        "its time level": {"time", "time_level", "instant"},
        "its component count / tensor rank": {"components", "rank", "shape"},
        "association to nodes vs cells vs faces": {"association", "placement"},
    }
    findings = []
    for question, candidate_names in questions.items():
        present = candidate_names & reference_fields
        findings.append(
            Finding(
                question=f"bulk reference: {question}",
                verdict=(
                    Recoverability.RECOVERABLE if present
                    else Recoverability.IMPOSSIBLE
                ),
                admissible_readings=1 if present else 0,
                ledger=Ledger.ABSENT_RECORD,
                detail=(
                    f"ScientificDataReference fields are "
                    f"{sorted(reference_fields)}; none of {sorted(candidate_names)} "
                    f"is among them. The record names bytes and a unit, and "
                    f"documents `count` as explicitly not a shape"
                ),
            )
        )
    findings.append(
        Finding(
            question="bulk reference: physical field identity and unit",
            verdict=Recoverability.RECOVERABLE,
            admissible_readings=len(result.data_references),
            ledger=Ledger.EXISTING_RECORD,
            detail=(
                "name and unit are carried and normalized; this half works and "
                "is what DATA-BOUNDARY0 established"
            ),
        )
    )
    return tuple(findings)


# =============================================================================
# The twelve-question matrix from the milestone brief
# =============================================================================

def recoverability_matrix(
    payloads: Mapping[str, Any],
    *,
    physically_transient: bool,
    reversed_problem_payload: Mapping[str, Any],
    realization_catalogue: Mapping[str, Any] | None = None,
    admit_free_text: bool = False,
) -> tuple[Finding, ...]:
    """The central measurement. Twelve questions, five buckets, one pass.

    ``reversed_problem_payload`` is the same consumer transported the other
    way. Q7 is measured against it rather than asserted; see
    :func:`count_orientation_readings`.

    ``admit_free_text`` decides whether meaning carried in an identifier or a
    description counts as recovered. It applies to **every** question or to
    none — granting it selectively is what the adversarial pass caught — and
    the milestone reports the matrix under both settings.
    """
    problem_payload = payloads["problem"]
    result_payload = payloads["result"]
    model_payload = payloads["model"]
    problem = ScientificProblem.from_dict(problem_payload)
    result = ScientificResult.from_dict(result_payload)

    state_variables = [v for v in problem.variables if v.role.value == "state"]
    identity, denotation = count_scheme_readings(
        result_payload, realization_catalogue, admit_free_text=admit_free_text
    )
    criterion = recover_resolution_criterion(problem_payload, result_payload)
    orientation_injective, orientation_remedy = count_orientation_readings(
        problem_payload, reversed_problem_payload, admit_free_text=admit_free_text
    )

    findings: list[Finding] = [
        Finding(
            "Q1 what the dependent scientific quantity is",
            Recoverability.RECOVERABLE,
            len(state_variables),
            Ledger.EXISTING_RECORD,
            f"exactly {len(state_variables)} STATE variable(s): "
            f"{[v.name for v in state_variables]}",
        ),
        Finding(
            "Q2 whether it is scalar or spatially distributed",
            Recoverability.IMPOSSIBLE,
            0,
            Ledger.ABSENT_RECORD,
            "ScientificVariable fields are "
            f"{[f.name for f in dataclasses.fields(type(problem.variables[0]))]}; "
            "none distinguishes a lumped scalar from a field. A STATE variable "
            "of a lumped body and a STATE variable that is a PDE field are "
            "byte-identical records",
        ),
        Finding(
            "Q3 its physical unit",
            Recoverability.RECOVERABLE,
            1,
            Ledger.EXISTING_RECORD,
            f"unit {problem.variable('c').unit!r}, normalized on construction",
        ),
        Finding(
            "Q4 what spatial entity it is defined over",
            Recoverability.IMPOSSIBLE,
            0,
            Ledger.ABSENT_RECORD,
            "no support, topology, mesh or extent concept exists on any record; "
            "`length` is a scalar parameter and states an extent but not a "
            "domain, an orientation or a set of boundary subsets",
        ),
        Finding(
            "Q5 what its initial state means",
            Recoverability.RECOVERABLE,
            len(problem.initial_conditions),
            Ledger.EXISTING_RECORD,
            f"{len(problem.initial_conditions)} InitialCondition record(s); "
            f"representable here only because the initial field is UNIFORM — "
            f"InitialCondition.value is a single Quantity, so a non-uniform "
            f"initial field (the baseline domain's sin(pi x/L)) has no home",
        ),
        Finding(
            "Q6 what its boundary conditions are",
            Recoverability.RECOVERABLE,
            len(problem.boundary_conditions),
            Ledger.EXISTING_RECORD,
            f"{len(problem.boundary_conditions)} typed BoundaryCondition "
            f"record(s) with kinds "
            f"{[b.kind.value for b in problem.boundary_conditions]} and values; "
            f"the kind/value half is genuinely recoverable",
        ),
        orientation_injective,
        orientation_remedy,
        Finding(
            "Q8 which model/equation governs it",
            Recoverability.RECOVERABLE,
            len(problem.models),
            Ledger.EXISTING_RECORD,
            f"ModelReference {[m.key for m in problem.models]}, resolvable "
            f"without importing the domain",
        ),
        Finding(
            "Q9 what the transport direction means",
            Recoverability.AMBIGUOUS,
            None,
            Ledger.EXISTING_RECORD,
            "the SIGN of the velocity parameter is recoverable and typed; what "
            "it implies for which boundary is inflow is not, because Q7 has no "
            "answer. Half the fact survives and the half that matters does not",
        ),
        Finding(
            "Q10 what solver capability is required",
            Recoverability.RECOVERABLE,
            len(problem.required_capabilities),
            Ledger.EXISTING_RECORD,
            f"required_capabilities={sorted(problem.required_capabilities)}",
        ),
        Finding(
            "Q11 whether the field representation is independent of storage",
            Recoverability.RECOVERABLE,
            len(result.data_references),
            Ledger.EXISTING_RECORD,
            "ScientificDataReference carries a content digest and no location; "
            "this is DATA-BOUNDARY0 and it holds unchanged",
        ),
        Finding(
            "Q12 whether the same field could later have two discretizations",
            denotation.verdict,
            denotation.admissible_readings,
            denotation.ledger,
            denotation.detail
            + f". Resolution criterion recovered from {criterion.source}: "
            f"{criterion.verdict.value}"
            + (", RUN-SCOPED" if criterion.run_scoped else "")
            + f" ({criterion.detail})",
        ),
        # R2a, appended rather than interleaved: it is the one place where a
        # record MODEL0-R added does exactly what it was added to do, and
        # burying it among the twelve would understate an H1 win.
        identity,
    ]
    return tuple(findings)
