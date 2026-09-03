"""The shared records-only instrument. ONE reader, four consumers.

Writing a per-consumer reader is preregistered **fail condition 11**, because
the entire cost case for this milestone rests on one instrument serving four
structurally unlike consumers. The spike that resolved it is recorded in
preregistration §3.1: of 18 definitions in the previous milestone's reader,
transport-specific literals appeared in exactly 2, and the other 15 introspect
`engcore.scientific` contracts generically.

THE RULES THIS READER OBEYS
---------------------------
* It is handed **serialized payloads** and nothing else.
* It may import `engcore.scientific`, because a records reader legitimately
  knows the schema it is reading.
* It **may not import any probe module** — not `mechanics`, `transport2d`,
  `species`, `dynamics` or `records`. Asserted by AST scan, not by convention.

TWO DIFFERENT QUESTIONS, KEPT APART
------------------------------------
The milestone asks two things that are easy to conflate, and conflating them is
how a coverage matrix becomes an opinion.

**Recoverability** — *can a reader recover this fact from the records?* This is
answered records-only, structurally, from dataclass fields and enum members. The
reader decides it and nothing else informs it.

**Forcing** — *does this consumer's science require the concept at all?* A
records reader cannot answer this: a record that says nothing about tensors
looks identical whether the science had a tensor or not. So each consumer
**declares** which concepts its physics involves, on its bundle, and the F/P/–
verdict is then derived by the mechanical rule in :func:`forcing_verdict`.

That split is what makes the matrix auditable. The declaration is a small,
inspectable set per consumer; the verdict is a function of it and of a
records-only measurement, and no human chooses a cell.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from engcore.scientific.ir.conditions import BoundaryCondition
from engcore.scientific.ir.constraints import ConstraintDefinition
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.values import ValueKind
from engcore.scientific.ir.variables import ScientificVariable, VariableRole
from engcore.scientific.models.definition import (
    InputSourceKind,
    ScientificModelDefinition,
)
from engcore.scientific.realizations.definition import (
    ModelFormulation,
    ModelRealizationDefinition,
)
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.validation import ValidationLevel

__all__ = [
    "Recoverability",
    "Forcing",
    "Ledger",
    "ConceptFinding",
    "CONCEPTS",
    "forcing_verdict",
    "classify_concept",
    "coverage_row",
    "coverage_matrix",
    "column_variance",
    "unique_forcings",
]


class Recoverability(str, Enum):
    """The five buckets the milestone brief requires, and only those."""

    FULLY_REPRESENTABLE = "fully representable"
    AMBIGUOUS = "ambiguous"
    IMPOSSIBLE = "impossible"
    REQUIRES_METADATA = "requires metadata"
    REQUIRES_SOURCE = "requires source-code knowledge"


class Forcing(str, Enum):
    """A coverage-matrix cell.

    ``SERVED`` exists because the adversarial pass found that collapsing
    "the science needs this and the contracts provide it" into the same token
    as "the science never touched this" had already produced two misreadings.
    A dash now means *untouched*, and a concept the contracts genuinely handle
    is visible as such.
    """

    FORCED = "F"
    PRESSURED = "P"
    SERVED = "S"
    UNTOUCHED = "-"


class Ledger(str, Enum):
    """Carried verbatim from `HOSTILE-CORE-STRESS`, including its booking rule.

    > A finding is **Ledger 1 only when BOTH the measurement AND the remedy live
    > in a record that already exists.** If closing the gap requires a record
    > the platform does not have, the finding is Ledger 2 — however interesting
    > the measurement, and whichever record it was taken on.
    """

    EXISTING_RECORD = "ledger-1: record exists"
    ABSENT_RECORD = "ledger-2: record does not exist"


@dataclass(frozen=True)
class ConceptFinding:
    concept: str
    consumer: str
    recoverability: Recoverability
    forcing: Forcing
    ledger: Ledger
    detail: str


def forcing_verdict(
    involved: bool, recoverability: Recoverability
) -> Forcing:
    """The mechanical rule that turns a measurement into a matrix cell.

    Stated as a function rather than applied by hand, so that no cell in the
    published matrix is a judgement call:

    * the science does not involve the concept  -> ``-``
    * involved and fully representable          -> ``S``  (served; not a gap)
    * involved and impossible to recover        -> ``F``
    * involved and recoverable only awkwardly   -> ``P``

    The second line used to return a dash, which made "served" and "untouched"
    indistinguishable in the published matrix. The adversarial pass showed that
    collapse had already produced two misreadings, so a served concept now has
    its own token.
    """
    if not involved:
        return Forcing.UNTOUCHED
    if recoverability is Recoverability.FULLY_REPRESENTABLE:
        return Forcing.SERVED
    if recoverability is Recoverability.IMPOSSIBLE:
        return Forcing.FORCED
    return Forcing.PRESSURED


# =============================================================================
# Structural helpers — "could a contract carry that fact, by type?"
# =============================================================================

def _field_names(record_type: type) -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(record_type))


def _variables_sharing_unit(problem: ScientificProblem) -> dict[str, int]:
    counts: dict[str, int] = {}
    for variable in problem.variables:
        counts[variable.unit] = counts.get(variable.unit, 0) + 1
    return counts


def _matrix_valued_parameter_possible() -> bool:
    """Can a `ScientificParameter` hold a matrix? Answered from the closed union.

    `ScientificValue` is `Quantity | IntegerValue | BooleanValue |
    CategoricalValue`. A `Quantity` holds one float. So the answer is a
    structural no, and it is the same no for a stiffness matrix, a
    stoichiometric matrix and a velocity field.
    """
    return False


def _problem_can_reference_bulk() -> bool:
    """Does `ScientificProblem` have a `data_references` field? Structural."""
    return "data_references" in _field_names(ScientificProblem)


# =============================================================================
# The concept probes
# =============================================================================
#
# Each probe answers ONE recoverability question, records-only. The signature is
# uniform so the matrix can be built by iteration rather than by hand.

Probe = Callable[[Mapping[str, Any]], tuple[Recoverability, Ledger, str]]


def _decode(payloads: Mapping[str, Any]):
    problem = ScientificProblem.from_dict(payloads["problem"])
    model = ScientificModelDefinition.from_dict(payloads["model"])
    result = (
        ScientificResult.from_dict(payloads["result"])
        if payloads.get("result")
        else None
    )
    realizations = [
        ModelRealizationDefinition.from_dict(r)
        for r in (payloads.get("realizations") or {}).values()
    ]
    return problem, model, result, realizations


def probe_spatial_field_semantics(payloads):
    """Can a reader tell a spatially distributed variable from a lumped one?

    Split out of a former single `ScientificField` probe, which conflated this
    with the linkage question below. The two have different column profiles —
    spatial semantics are an A/B concern, and the linkage gap is exhibited by
    all four consumers — so one row was understating the second by half.
    """
    problem, _, _, _ = _decode(payloads)
    states = [v for v in problem.variables if v.role is VariableRole.STATE]
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        f"{len(states)} STATE variable(s); a ScientificVariable that is a field "
        f"and one that is a lumped scalar are byte-identical records",
    )


def probe_variable_to_bulk_linkage(payloads):
    """Which declared variable does a bulk array hold the values of?

    `ScientificDataReference` carries name, unit, count, dtype and a digest —
    and no reference to any `ScientificVariable`. For a multi-variable
    trajectory the ordering is not recorded either, so a reader cannot say
    which values belong to which quantity. The link survives only in the name
    spelling, which is the untyped escape hatch the platform exists to avoid.
    """
    problem, _, result, _ = _decode(payloads)
    if result is None or not result.data_references:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "no bulk data accompanies this result, so no linkage is needed",
        )
    reference_fields = sorted(_field_names(ScientificDataReference))
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"{len(result.data_references)} bulk reference(s) against "
        f"{len(problem.variables)} declared variable(s); "
        f"ScientificDataReference fields are {reference_fields} and none names "
        f"a variable, so neither the association nor the ordering is recorded",
    )


def probe_field_support(payloads):
    problem, _, _, _ = _decode(payloads)
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no support, extent, connectivity or coordinate concept exists on any "
        "record; scalar parameters can state a length and cannot state a domain",
    )


def probe_topology(payloads):
    """Payload-sensitive, and it had to become so.

    An earlier version returned a constant IMPOSSIBLE after decoding only the
    problem and the model. That scored `electrical/dc` as forcing topology —
    which contradicts a decision recorded in the file being scored.
    `dc/problem.py` states that it translates a circuit *"without smuggling
    topology into the IR"*, because connectivity travels to the solver through
    the prepared-solve payload, bound to the problem by a verified fingerprint.

    So topology is not unrepresentable there. It is **deliberately represented
    elsewhere**, in a typed domain record. A probe that cannot see that channel
    reports a design decision as a platform gap.

    This version looks for a domain artifact carrying adjacency. Finding one
    means the concept is served by a domain-local typed record — which is a
    real answer, and a different one from "the universal core carries it".
    """
    artifact = payloads.get("domain_artifact")
    if artifact:
        adjacency = sorted(
            key
            for key in artifact
            if key in ("nodes", "edges", "resistors", "elements", "connectivity")
        )
        if adjacency:
            return (
                Recoverability.REQUIRES_SOURCE,
                Ledger.EXISTING_RECORD,
                f"adjacency travels in a typed DOMAIN artifact carrying "
                f"{adjacency}, bound to the problem by a fingerprint and "
                f"deliberately kept out of the IR; recoverable, but only by a "
                f"reader that knows this domain's artifact schema",
            )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no universal record carries adjacency, connectivity or a boundary "
        "decomposition, and no domain artifact accompanies this problem",
    )


def probe_boundary_identity(payloads):
    problem, _, _, _ = _decode(payloads)
    regions = sorted({b.region for b in problem.boundary_conditions})
    if not regions:
        return (
            Recoverability.IMPOSSIBLE,
            Ledger.ABSENT_RECORD,
            "no boundary conditions declared",
        )
    return (
        Recoverability.REQUIRES_METADATA,
        Ledger.EXISTING_RECORD,
        f"{len(regions)} region identifier(s) {regions} carried as opaque "
        f"strings the core documents as uninterpreted; a region is nameable "
        f"and not resolvable",
    )


def probe_boundary_orientation_sign(payloads):
    problem, _, _, _ = _decode(payloads)
    fields = _field_names(BoundaryCondition)
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"BoundaryCondition fields are {sorted(fields)}; none can state which "
        f"way flux crosses the region, and the role may vary ALONG a region "
        f"rather than between regions",
    )


def probe_boundary_orientation_normal(payloads):
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "an outward normal is a rank-1 geometric property of a boundary; there "
        "is no boundary geometry record for it to live on",
    )


def probe_boundary_condition_adequacy(payloads):
    problem, model, _, _ = _decode(payloads)
    kinds = sorted({b.kind.value for b in problem.boundary_conditions})
    if not kinds:
        return (
            Recoverability.IMPOSSIBLE,
            Ledger.EXISTING_RECORD,
            "no boundary conditions declared",
        )
    condition_sources = [
        m for m in InputSourceKind if "condition" in m.value or "boundary" in m.value
    ]
    return (
        Recoverability.AMBIGUOUS,
        Ledger.EXISTING_RECORD,
        f"kinds {kinds} and their values are recoverable; whether the declared "
        f"set is the right SIZE is not, because InputSourceKind has members "
        f"{[m.value for m in InputSourceKind]} and none denotes a condition "
        f"(condition-denoting members found: {len(condition_sources)})",
    )


def probe_rank1(payloads):
    problem, _, _, _ = _decode(payloads)
    fields = _field_names(ScientificVariable)
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"ScientificVariable fields are {sorted(fields)}; none carries a rank, "
        f"a component index or a grouping, so components of one vector are "
        f"independent scalars distinguishable only by name spelling",
    )


def probe_rank2(payloads):
    problem, _, result, _ = _decode(payloads)
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        "nothing relates several declared quantities as components of one "
        "rank-2 tensor, and nothing records the symmetry that makes three "
        "in-plane components sufficient",
    )


def probe_field_valued_input(payloads):
    if _problem_can_reference_bulk():
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "ScientificProblem carries data_references",
        )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        "ScientificProblem has no data_references field — that exists only on "
        "ScientificResult and RawSolverOutput — and ScientificValue is a "
        "closed scalar union, so a field-valued INPUT has no typed home "
        "anywhere in a problem statement",
    )


def probe_constraint(payloads):
    problem, _, _, _ = _decode(payloads)
    fields = _field_names(ConstraintDefinition)
    declared = len(problem.constraints)
    return (
        Recoverability.AMBIGUOUS,
        Ledger.EXISTING_RECORD,
        f"{declared} ConstraintDefinition record(s); its fields are "
        f"{sorted(fields)} — a metric compared against a scalar bound. That is "
        f"a study-level ACCEPTANCE test, not an algebraic relation among "
        f"unknowns that must hold at every instant",
    )


def probe_dae_partition(payloads):
    problem, _, _, _ = _decode(payloads)
    roles = sorted({r.value for r in VariableRole})
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"VariableRole members are {roles}; none distinguishes a differential "
        f"unknown from an algebraic one, so a Lagrange multiplier and a state "
        f"are indistinguishable in the record",
    )


def probe_relational_initial_condition(payloads):
    problem, _, _, _ = _decode(payloads)
    count = len(problem.initial_conditions)
    if count == 0:
        return (
            Recoverability.IMPOSSIBLE,
            Ledger.EXISTING_RECORD,
            "no initial conditions declared",
        )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"{count} InitialCondition record(s), each holding one Quantity for one "
        f"variable with no reference to any other; a consistency requirement "
        f"over the SET has no home, so records that individually validate can "
        f"jointly describe an impossible start",
    )


def probe_dynamic_state(payloads):
    problem, _, _, _ = _decode(payloads)
    states = [v for v in problem.variables if v.role is VariableRole.STATE]
    if problem.is_time_dependent and states:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            f"{len(states)} STATE variable(s) and "
            f"{len(problem.initial_conditions)} initial condition(s); "
            f"is_time_dependent is True and agrees with the physics",
        )
    return (
        Recoverability.AMBIGUOUS,
        Ledger.EXISTING_RECORD,
        f"{len(states)} STATE variable(s) but is_time_dependent="
        f"{problem.is_time_dependent}; the property is derived from initial "
        f"conditions being non-empty",
    )


def probe_material_identity(payloads):
    problem, _, _, _ = _decode(payloads)
    return (
        Recoverability.REQUIRES_METADATA,
        Ledger.EXISTING_RECORD,
        "material properties are declarable as scalar parameters and the "
        "material itself is not named by any record; which substance the "
        "numbers belong to survives only in prose",
    )


def probe_material_state(payloads):
    """Structural answer only; see :func:`probe_causal_port`.

    Note what this does NOT say. `electrical/material.py` implements a
    state-dependent scalar ``R(T)`` as a domain-local model with no property
    hierarchy, and that recorded argument is unchallenged. What is absent is a
    *universal* record for the relationship — a different question, and the one
    this probe answers.
    """
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no universal record ties a material property to the solution state; "
        "the scalar case is served domain-locally by a model, which is a "
        "domain answer rather than a core one",
    )


def probe_property_requirement_scalar(payloads):
    return (
        Recoverability.FULLY_REPRESENTABLE,
        Ledger.EXISTING_RECORD,
        "a scalar property is a ScientificParameter carrying a Quantity, and "
        "ModelInputSpec declares the requirement with a unit exemplar",
    )


def probe_property_requirement_rank2(payloads):
    if _matrix_valued_parameter_possible():
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "a matrix-valued parameter is expressible",
        )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        "ScientificValue is a closed union of scalars, so a matrix-valued "
        "material property cannot be a ScientificParameter and ModelInputSpec "
        "cannot declare a requirement for one",
    )


def probe_species_identity(payloads):
    """Payload-sensitive: it uses the count it measures rather than ignoring it."""
    problem, _, _, _ = _decode(payloads)
    shared = _variables_sharing_unit(problem)
    if not shared:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "no variables declared, so no identity question arises",
        )
    worst_unit, worst_count = max(shared.items(), key=lambda kv: kv[1])
    if worst_count < 2:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "every declared variable carries a distinct unit, so no two "
            "quantities could be confused for one another",
        )
    return (
        Recoverability.REQUIRES_METADATA,
        Ledger.EXISTING_RECORD,
        f"{worst_count} variable(s) share the unit {worst_unit!r}; nothing "
        f"says they are distinct chemical substances rather than unrelated "
        f"quantities of one dimension, so identity survives only in the name "
        f"spelling and in a metadata list",
    )


def probe_composition(payloads):
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no record groups several species quantities into one composition, so "
        "there is nothing to attach a sum-to-one or a mass-balance rule to",
    )


def probe_reaction_relationship(payloads):
    if _matrix_valued_parameter_possible():
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "a stoichiometric matrix is expressible",
        )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        "the stoichiometric matrix is integer-valued, rectangular and indexed "
        "by (reaction, species); ScientificValue is a closed scalar union, so "
        "it has no typed home and the conservation weights it implies cannot "
        "be derived by any reader",
    )


def probe_causal_port(payloads):
    """Structural answer only.

    Whether a consumer *needs* a port is the declaration's business, not this
    probe's — see the module docstring's split. An earlier version returned
    FULLY_REPRESENTABLE on the grounds that "no consumer here is a coupled
    system", which answers the **forcing** question with a **recoverability**
    label. That would have silently served a dash to any future consumer that
    did declare a port, which is the exact false-negative shape the previous
    milestone hit twice.
    """
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no port, terminal or directed-interface record exists in "
        "engcore.scientific; ports are a recorded deferral",
    )


def probe_physical_connector(payloads):
    """Structural answer only; see :func:`probe_causal_port`."""
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no acausal connector record with across/through semantics exists; "
        "connectors are a recorded deferral",
    )


def probe_discretization(payloads):
    problem, _, _, realizations = _decode(payloads)
    integer_params = [
        p.name for p in problem.parameters if p.kind is ValueKind.INTEGER
    ]
    metadata_hints = sorted(
        k for k in problem.metadata if k.startswith("n_") or "cell" in k
    )
    formulations = sorted({r.formulation.value for r in realizations})
    return (
        Recoverability.REQUIRES_METADATA,
        Ledger.EXISTING_RECORD,
        f"resolution reachable as typed integer parameter(s) {integer_params} "
        f"or metadata key(s) {metadata_hints}; realization formulations "
        f"{formulations} state the mathematical form and not the scheme",
    )


def probe_runtime_state(payloads):
    """Structural answer only; see :func:`probe_causal_port`."""
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no record carries state across runs or claims instance authority over "
        "it; ScientificTwin exists and is consumed as a design candidate, not "
        "as runtime-state authority",
    )


def probe_event(payloads):
    """Structural answer only; see :func:`probe_causal_port`."""
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.ABSENT_RECORD,
        "no event, discontinuity, state-reset or switching record exists",
    )


def probe_quantity_identity(payloads):
    problem, _, _, _ = _decode(payloads)
    shared = _variables_sharing_unit(problem)
    repeated = {unit: n for unit, n in shared.items() if n > 1}
    if not repeated:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            "every declared variable carries a distinct unit",
        )
    return (
        Recoverability.REQUIRES_METADATA,
        Ledger.EXISTING_RECORD,
        f"units carrying more than one variable: {repeated}; instances are "
        f"distinguished by name spelling, which the domain owns and the core "
        f"never parses",
    )


def probe_admissibility_attainment(payloads):
    """Payload-sensitive, and it had to become so.

    An earlier version decoded the result and then never read it, so it
    returned the same verdict for a consumer carrying a real admissibility
    check and for a control payload carrying no result at all. The 6/6 it
    produced was one enum fact replicated six times.

    This version requires the record to **exhibit** an admissibility check
    before reporting anything about it, and then measures the narrow, true
    thing: such a check can report PASS or FAIL, and `establishes=` has no
    `ValidationLevel` member to name, so admissibility can never enter
    `attained_levels`, be gated by `require_level`, or be compared across
    results.
    """
    _, _, result, _ = _decode(payloads)
    levels = sorted(level.value for level in ValidationLevel)
    named = [
        level
        for level in levels
        if any(
            token in level
            for token in ("admissib", "bounded", "physical_range", "maximum_principle")
        )
    ]
    if named:
        return (
            Recoverability.FULLY_REPRESENTABLE,
            Ledger.EXISTING_RECORD,
            f"ValidationLevel carries {named}",
        )
    if result is None:
        return (
            Recoverability.AMBIGUOUS,
            Ledger.EXISTING_RECORD,
            "no result accompanies this problem, so whether an admissibility "
            "check was performed cannot be read at all — which is itself the "
            "weaker half of the finding",
        )
    exhibited = [
        check.name
        for check in result.validation.checks
        if check.establishes is None and check.tolerance is not None
    ]
    if not exhibited:
        return (
            Recoverability.AMBIGUOUS,
            Ledger.EXISTING_RECORD,
            "the record carries no check that looks like an admissibility "
            "criterion, so nothing here exhibits the gap",
        )
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        f"checks {exhibited} report a physical-admissibility criterion and "
        f"every one carries establishes=None, because ValidationLevel has "
        f"{len(levels)} members {levels} and none denotes physical "
        f"admissibility; such a check can never enter attained_levels or be "
        f"gated by require_level",
    )


#: Concept name -> (probe, human label). Order is the published matrix order.
CONCEPTS: tuple[tuple[str, Probe], ...] = (
    ("SpatialFieldSemantics", probe_spatial_field_semantics),
    ("VariableToBulkLinkage", probe_variable_to_bulk_linkage),
    ("FieldSupport", probe_field_support),
    ("Domain/Topology", probe_topology),
    ("BoundaryIdentity", probe_boundary_identity),
    ("BoundaryOrientation-sign", probe_boundary_orientation_sign),
    ("BoundaryOrientation-normal", probe_boundary_orientation_normal),
    ("BoundaryCondition", probe_boundary_condition_adequacy),
    ("Rank1", probe_rank1),
    ("Rank2", probe_rank2),
    ("FieldValuedInput", probe_field_valued_input),
    ("Constraint", probe_constraint),
    ("DifferentialAlgebraicPartition", probe_dae_partition),
    ("RelationalInitialCondition", probe_relational_initial_condition),
    ("DynamicState", probe_dynamic_state),
    ("MaterialIdentity", probe_material_identity),
    ("MaterialState", probe_material_state),
    ("PropertyRequirement-scalar", probe_property_requirement_scalar),
    ("PropertyRequirement-rank2", probe_property_requirement_rank2),
    ("SpeciesIdentity", probe_species_identity),
    ("Composition", probe_composition),
    ("ReactionRelationship", probe_reaction_relationship),
    ("CausalPort", probe_causal_port),
    ("PhysicalConnector", probe_physical_connector),
    ("DiscretizationDefinition", probe_discretization),
    ("RuntimeState", probe_runtime_state),
    ("Event", probe_event),
    ("QuantityIdentity", probe_quantity_identity),
    ("AdmissibilityAttainment", probe_admissibility_attainment),
    ("TimeVaryingInput", None),  # filled below; needs its own probe
)


def probe_time_varying_input(payloads):
    problem, _, _, _ = _decode(payloads)
    return (
        Recoverability.IMPOSSIBLE,
        Ledger.EXISTING_RECORD,
        "a ScientificParameter holds one Quantity — one magnitude and a unit — "
        "so an input that is a function of time can have its amplitude and its "
        "frequency declared and cannot be declared to be a signal",
    )


CONCEPTS = tuple(
    (name, probe_time_varying_input if probe is None else probe)
    for name, probe in CONCEPTS
)


# =============================================================================
# Building the matrix
# =============================================================================

def classify_concept(
    concept: str, probe: Probe, payloads: Mapping[str, Any], involved: bool
) -> ConceptFinding:
    """One cell, derived. No human chooses the verdict."""
    recoverability, ledger, detail = probe(payloads)
    return ConceptFinding(
        concept=concept,
        consumer=payloads["consumer"],
        recoverability=recoverability,
        forcing=forcing_verdict(involved, recoverability),
        ledger=ledger,
        detail=detail,
    )


def coverage_row(
    concept: str,
    probe: Probe,
    columns: Mapping[str, tuple[Mapping[str, Any], frozenset[str]]],
) -> dict[str, ConceptFinding]:
    """One matrix row: this concept across every column."""
    return {
        name: classify_concept(concept, probe, payloads, concept in science)
        for name, (payloads, science) in columns.items()
    }


def coverage_matrix(
    columns: Mapping[str, tuple[Mapping[str, Any], frozenset[str]]]
) -> dict[str, dict[str, ConceptFinding]]:
    """The full matrix: every concept against every column."""
    return {
        concept: coverage_row(concept, probe, columns)
        for concept, probe in CONCEPTS
    }


def column_variance(
    columns: Mapping[str, tuple[Mapping[str, Any], frozenset[str]]]
) -> dict[str, bool]:
    """Does each probe's RECOVERABILITY verdict vary across columns?

    **This is the instrument measuring its own discriminating power, and it was
    added because the adversarial pass showed it was needed.**

    A probe whose verdict is the same for every payload contributes exactly one
    global fact about `engcore.scientific`; the cross-column pattern of that row
    is then the `science` declarations re-printed, not a measurement of the
    consumers. Such a row is a **contract-gap measurement** and must not be
    reported as evidence that N materially different consumers independently
    need something.

    A probe whose verdict varies is reading the records, and its row is a
    genuine **coverage measurement**.

    Publishing this per row is what keeps the distinction visible instead of
    letting a reader assume every row means the same thing.
    """
    varies: dict[str, bool] = {}
    for concept, probe in CONCEPTS:
        verdicts = {probe(payloads)[0] for payloads, _ in columns.values()}
        varies[concept] = len(verdicts) > 1
    return varies


def unique_forcings(
    matrix: Mapping[str, Mapping[str, ConceptFinding]], consumers: tuple[str, ...]
) -> dict[str, tuple[str, ...]]:
    """Concepts each consumer forces that **no other consumer** forces.

    Preregistered reading P-1: each consumer must uniquely force at least
    three, or it was redundant and the evidence must say so. Controls are
    excluded from the uniqueness test — they are scored to demote concepts, not
    to claim them.
    """
    unique: dict[str, list[str]] = {name: [] for name in consumers}
    for concept, row in matrix.items():
        forcing_consumers = [
            name
            for name in consumers
            if row[name].forcing is Forcing.FORCED
        ]
        if len(forcing_consumers) == 1:
            unique[forcing_consumers[0]].append(concept)
    return {name: tuple(sorted(values)) for name, values in unique.items()}
