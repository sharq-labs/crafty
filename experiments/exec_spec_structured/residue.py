"""The two residue tables, the overlap analysis, and the false-universality test.

Preregistration §10 requires nine attributes per residue item, and §13.3 makes an
item recorded without all nine a fail condition. §13.2 makes calling two residues
"the same abstraction" on shape alone a fail condition, which is what
:func:`shared_semantics` exists to prevent: it asks what a records-only planner
could *do* with a candidate shared abstraction, not what shape the data has.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .encodings import ATTEMPTS, AttemptOutcome, EncodingAttempt

__all__ = [
    "ResidueClass",
    "ResidueItem",
    "MECH_RESIDUE",
    "SPECIES_RESIDUE",
    "RESIDUE",
    "residue_for",
    "Candidate",
    "CANDIDATES",
    "shared_semantics",
    "OverlapVerdict",
    "overlap",
]


class ResidueClass(str, Enum):
    """The classification the brief requires per item."""

    SCALAR_EXISTING_CONTRACT = "scalar-existing-contract"
    NON_SCALAR_SCIENTIFIC_STRUCTURE = "non-scalar-scientific-structure"
    DOMAIN_STRUCTURE = "domain-structure"
    CONSTITUTIVE_RELATION = "constitutive-relation"
    DISCRETIZATION = "discretization"
    RUNTIME_PREPARED = "runtime-prepared"


@dataclass(frozen=True)
class ResidueItem:
    """One fact no existing typed contract can carry, with all nine attributes."""

    column: str
    fact: str
    classification: ResidueClass
    #: Rank/shape as the science means it, not as bytes.
    shape: str
    #: Does it grow with the size of the problem?
    scales_with_problem: bool
    #: Would another science recognise this object as its own?
    domain_specific: bool
    #: Is there an analogue in the other column?
    analogue_in_other_column: str | None
    #: Does changing it change what physical system is described?
    changes_scientific_identity: bool
    #: Or does it only change how finely it is computed?
    changes_only_discretization: bool
    belongs_in_provenance: bool
    belongs_under_data_boundary0: bool
    note: str = ""

    @property
    def attempts(self) -> tuple[EncodingAttempt, ...]:
        return tuple(a for a in ATTEMPTS if a.column == self.column and a.fact == self.fact)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "fact": self.fact,
            "classification": self.classification.value,
            "shape": self.shape,
            "scales_with_problem": self.scales_with_problem,
            "domain_specific": self.domain_specific,
            "analogue_in_other_column": self.analogue_in_other_column,
            "changes_scientific_identity": self.changes_scientific_identity,
            "changes_only_discretization": self.changes_only_discretization,
            "belongs_in_provenance": self.belongs_in_provenance,
            "belongs_under_data_boundary0": self.belongs_under_data_boundary0,
            "note": self.note,
            "attempts": [a.to_dict() for a in self.attempts],
        }


MECH_RESIDUE: tuple[ResidueItem, ...] = (
    ResidueItem(
        column="col-mech",
        fact="node coordinates (4 nodes x 2 components, metres)",
        classification=ResidueClass.DOMAIN_STRUCTURE,
        shape="N x 2 continuous, dimensional",
        scales_with_problem=True,
        domain_specific=False,
        analogue_in_other_column=None,
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=True,
        note=(
            "The one residue item here that is genuinely bulk-shaped. Moving a "
            "node changes the physical system, so it is not discretization — but "
            "at mesh scale the values belong behind a ScientificDataReference "
            "with something naming what they are. Species has NO analogue: a "
            "reaction network has no coordinates at all."
        ),
    ),
    ResidueItem(
        column="col-mech",
        fact="which body is discretized (the domain the mesh covers)",
        classification=ResidueClass.DOMAIN_STRUCTURE,
        shape="a region, of which the node set is one representative",
        scales_with_problem=False,
        domain_specific=False,
        analogue_in_other_column=None,
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=False,
        note=(
            "SPLIT OUT after the decision review, which found that recording "
            "connectivity as one item left it identical to nu on both attributes "
            "that should separate a model from a discretization. The intended "
            "statement is that every mesh of one body is an equivalence class "
            "under which the science is invariant, while nu has no such class — "
            "every distinct nu is a distinct model. "
            "CARRIER CORRECTED after the falsification pass: an earlier note "
            "said 'the node set stands in for one'. A point set has no extent — "
            "the body is the union of the element closures — so the node set "
            "cannot carry it and the connectivity still absorbs the body "
            "identity. NO CARRIER EXISTS. Naming one is a topology/geometry "
            "object this milestone is forbidden to build and did not build."
        ),
    ),
    ResidueItem(
        column="col-mech",
        fact="element connectivity (2 triangles x 3 node indices, ordered)",
        classification=ResidueClass.DISCRETIZATION,
        shape="E x 3 ordinal index tuples, order load-bearing",
        scales_with_problem=True,
        domain_specific=False,
        analogue_in_other_column="stoichiometric matrix nu (shape only — see CANDIDATES)",
        changes_scientific_identity=True,
        changes_only_discretization=True,
        belongs_in_provenance=True,
        belongs_under_data_boundary0=True,
        note=(
            "Vertex ORDER fixes the signed area and therefore the sign of B — "
            "measured, because assemble_from_records refuses a non-positive "
            "signed area. Its entries are ORDINAL POSITIONS, not coefficients: "
            "the null space of this table is the set of nodes no element "
            "references, which is mesh hygiene and not a statement about the "
            "body. "
            "BOTH identity attributes are True, and an earlier form recorded "
            "changes_scientific_identity=False. The adversarial pass falsified "
            "that with a case inside this milestone's own executed path: keep "
            "the four corner coordinates and drop one element, and every guard "
            "passes while the assembled system is a TRIANGULAR PLATE — a "
            "different body, from a connectivity edit alone. The two attributes "
            "separate only once a topology/geometry object exists against which "
            "a mesh can be checked as one of its refinements (synthesis §17.6; "
            "OpenFOAM study Candidate N). This milestone produced no such "
            "object, so in the representation MEASURED, connectivity carries "
            "identity."
        ),
    ),
    ResidueItem(
        column="col-mech",
        fact="constrained degrees of freedom (4 of 8)",
        classification=ResidueClass.NON_SCALAR_SCIENTIFIC_STRUCTURE,
        shape="subset of an index set derived from nodes x components",
        scales_with_problem=True,
        domain_specific=False,
        analogue_in_other_column=None,
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=False,
        note=(
            "Expressible one component at a time as a BoundaryCondition — the "
            "attempt succeeds — but only against variables named 'u_x:n0', so the "
            "DOF numbering 2*node+component survives as a convention. The missing "
            "concept is that u_x and u_y are components of one vector at one "
            "node, which is the Rank1 row CROSS-DOMAIN-COVERAGE downgraded to "
            "CROSS-DOMAIN-CANDIDATE."
        ),
    ),
    ResidueItem(
        column="col-mech",
        fact="applied load, and which degrees of freedom receive it",
        classification=ResidueClass.NON_SCALAR_SCIENTIFIC_STRUCTURE,
        shape="scalar magnitude + index set",
        scales_with_problem=True,
        domain_specific=False,
        analogue_in_other_column=None,
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=False,
        note=(
            "The magnitude is a first-class Quantity and the target is a key. "
            "Half of this item is perfectly served by existing contracts."
        ),
    ),
)

SPECIES_RESIDUE: tuple[ResidueItem, ...] = (
    ResidueItem(
        column="col-species",
        fact="stoichiometric matrix nu (2 reactions x 3 species)",
        classification=ResidueClass.CONSTITUTIVE_RELATION,
        shape="R x S signed integers, both axes named, order load-bearing",
        scales_with_problem=True,
        domain_specific=True,
        analogue_in_other_column="element connectivity (shape only — see CANDIDATES)",
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=False,
        note=(
            "nu IS the model: dc/dt = nu^T r. It is not derivable from anything "
            "on any record, and the conserved weights (1,1,2) come from its null "
            "space and nowhere else — recovered here by SVD from the "
            "reconstructed coefficients, with species.CONSERVED_WEIGHTS never "
            "read. Every distinct nu is a distinct model; there is no "
            "refinement-equivalence class. "
            "WITHDRAWN after the adversarial review: an earlier note argued nu "
            "is excluded from DATA-BOUNDARY0 partly because its coefficients are "
            "integers that float64 bulk would widen. SUPPORTED_DTYPES is "
            "{float64} for the mesh connectivity too, so that argument does not "
            "separate them and is not independent corroboration. What excludes "
            "nu is that it is a model, not data."
        ),
    ),
    ResidueItem(
        column="col-species",
        fact="species identities, in state order",
        classification=ResidueClass.NON_SCALAR_SCIENTIFIC_STRUCTURE,
        shape="ordered index set of names",
        scales_with_problem=True,
        domain_specific=True,
        analogue_in_other_column="node coordinates (shape only — an index set over named entities)",
        changes_scientific_identity=True,
        changes_only_discretization=False,
        belongs_in_provenance=False,
        belongs_under_data_boundary0=False,
        note=(
            "A CategoricalValue vocabulary carries the SET; nothing states that "
            "vocabulary position is state-vector position, which is what makes "
            "nu's columns meaningful. Without it, three variables of one "
            "dimension are three unrelated numbers."
        ),
    ),
)

RESIDUE: tuple[ResidueItem, ...] = MECH_RESIDUE + SPECIES_RESIDUE


def residue_for(column: str) -> tuple[ResidueItem, ...]:
    return tuple(item for item in RESIDUE if item.column == column)


# =====================================================================
# The universality test
# =====================================================================

class Candidate(str, Enum):
    STRUCTURED_SCIENTIFIC_VALUE = "A: generic StructuredScientificValue"
    RELATION_COEFFICIENT_ARTIFACT = "B: generic relation/coefficient artifact"
    DOMAIN_OWNED_WITH_SHARED_INFRASTRUCTURE = (
        "C: domain-owned typed records sharing identity/schema/serialization/digest"
    )
    BULK_LINKAGE_ONLY = "D: bulk-data/reference linkage only"
    NO_SHARED_ABSTRACTION = "E: no shared abstraction beyond existing records"


@dataclass(frozen=True)
class CandidateVerdict:
    candidate: Candidate
    survives: bool
    planner_can_act: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.value,
            "survives": self.survives,
            "planner_can_act": self.planner_can_act,
            "reason": self.reason,
        }


#: The rejection test, applied to each candidate: would a records-only planner
#: understand the SCIENTIFIC MEANING, or would the abstraction only say "here is
#: a matrix"?
#:
#: **This table is `L0 REASONED` and carries near-zero evidential weight**, and
#: the adversarial review is why it says so. The rejection test asks whether a
#: planner could act on an abstraction's semantics, so the only candidate that
#: can pass is the one making no semantic claim — which is the incumbent. A test
#: only the incumbent can pass is confirmation-shaped, and two consecutive
#: milestones (§67.3, §68.3) were already falsified for instruments that
#: flattered their own hypothesis. The load-bearing evidence for the verdict is
#: the two EXECUTED measurements — D is derivable, nu is not and carries a
#: recoverable invariant — and not this table.
CANDIDATES: tuple[CandidateVerdict, ...] = (
    CandidateVerdict(
        Candidate.STRUCTURED_SCIENTIFIC_VALUE,
        survives=False,
        planner_can_act=False,
        reason=(
            "It would say 'this parameter is an R x S array of numbers'. A "
            "planner reading it could not tell a stoichiometric matrix from a "
            "constitutive tensor from a lookup table, so it could not choose a "
            "realization, check a conservation law, or refuse an incompatible "
            "coupling. FALSE UNIVERSALITY: the shape is shared and nothing else "
            "is."
        ),
    ),
    CandidateVerdict(
        Candidate.RELATION_COEFFICIENT_ARTIFACT,
        survives=False,
        planner_can_act=False,
        reason=(
            "The strongest case for reopening, and it fails on ALGEBRAIC TYPE "
            "rather than on prose. nu's entries are SIGNED INTEGERS on which "
            "null-space arithmetic is meaningful and yields a physical invariant "
            "— measured. Element-node entries are ORDINAL POSITIONS: the null "
            "space of that table is a number with no referent. "
            "CORRECTED after the adversarial review, which caught a false "
            "premise: Crafty's DC domain does NOT contain an oriented incidence "
            "matrix. `electrical_dc_circuit/1` stores typed components with "
            "semantically distinct terminal roles — resistor node_a/node_b, "
            "source positive_node/negative_node, from_node/to_node — and "
            "circuit.py records that terminal order must not be flattened "
            "because swapping it must produce a different identity. A generic "
            "signed incidence table erases exactly the distinction the "
            "passive-sign guard needed. The third data point was an inference "
            "presented as a fact, and reaction-network and Kirchhoff incidence "
            "are in any case one mathematical ancestor counted twice."
        ),
    ),
    CandidateVerdict(
        Candidate.DOMAIN_OWNED_WITH_SHARED_INFRASTRUCTURE,
        survives=True,
        planner_can_act=True,
        reason=(
            "The shared part is small and carries no scientific claim: a schema "
            "string, deterministic serialization, a content digest, and "
            "location-independent identity. The meaning stays in a domain schema "
            "a planner resolves by name. This is what EXEC-SPEC selected, and "
            "both columns exercise it without modification."
        ),
    ),
    CandidateVerdict(
        Candidate.BULK_LINKAGE_ONLY,
        survives=False,
        planner_can_act=False,
        reason=(
            "Necessary and not sufficient. It is the right home for mechanics' "
            "node coordinates and for both columns' solution arrays, and it is "
            "the WRONG home for nu: a reaction network is a model, not bulk "
            "data, its coefficients are integers, and DATA-BOUNDARY0 explicitly "
            "declines to carry semantics."
        ),
    ),
    CandidateVerdict(
        Candidate.NO_SHARED_ABSTRACTION,
        survives=False,
        planner_can_act=False,
        reason=(
            "Refuted by the measurement: both columns need the SAME thing from "
            "bulk references — a statement of which variable and which ordering "
            "an array instantiates. That is VariableToBulkLinkage, already forced "
            "4/4 by CROSS-DOMAIN-COVERAGE and forced again here by two more "
            "consumers. Something IS shared; it is just not a matrix record."
        ),
    ),
)


class OverlapVerdict(str, Enum):
    SAME_UNIVERSAL_SHAPE = "A: same universal shape forced"
    DIFFERENT_DOMAIN_OWNED = "B: different domain-owned structures"
    EXISTING_CONTRACTS_SUFFICE = "C: existing contracts suffice"
    MIXED = "D: mixed"


@dataclass(frozen=True)
class Overlap:
    verdict: OverlapVerdict
    shared_semantic: tuple[str, ...]
    shared_infrastructure: tuple[str, ...]
    not_shared: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict.value,
            "shared_semantic": list(self.shared_semantic),
            "shared_infrastructure": list(self.shared_infrastructure),
            "not_shared": list(self.not_shared),
        }


def shared_semantics() -> tuple[str, ...]:
    """**`L0 REASONED` — AUTHORED, not derived.** The label is the correction.

    An earlier docstring claimed this was "derived from the residue tables", and
    the body contained a dead `if mech_facts and species_facts: pass` branch
    that read the tables and did nothing with them, while the returned statement
    was appended unconditionally. A function whose output is invariant under
    emptying its stated inputs is not derived from them, and claiming otherwise
    tripped this milestone's own §13.9. The dead branch is deleted and the claim
    is withdrawn.

    What follows is the author's reading of the measurements, offered as
    reasoning. The load-bearing evidence is elsewhere: D is derivable from
    records, nu is not, and nu's null space yields the invariant. Those are
    executed. This is not.
    """
    return (
        "an array of values must be able to name the variable(s) and the "
        "component ordering it instantiates (VariableToBulkLinkage)",
    )


def overlap() -> Overlap:
    """**`L0 REASONED` — AUTHORED.** The verdict, with the same correction.

    An earlier docstring said "derived from the tables above"; the body returns
    literals. It is the author's conclusion from the measurements, and a reader
    should weigh it as that rather than as an instrument output.
    """
    return Overlap(
        verdict=OverlapVerdict.MIXED,
        shared_semantic=shared_semantics(),
        shared_infrastructure=(
            "an ordered index set of named entities whose order is load-bearing",
            "an integer table relating two such sets",
            "schema string + deterministic serialization + content digest",
        ),
        not_shared=(
            "what the coefficients mean (molar ratio vs vertex membership)",
            "what follows from them (a conservation law vs an assembly rule)",
            "whether the structure is a model (nu) or a discretized geometry "
            "(mesh) — nu changes the science, a finer mesh does not",
            "continuous coordinates: mechanics has them, species has none",
            "derivability: the mechanics constitutive matrix is computed from "
            "two scalars; the stoichiometric matrix is computed from nothing",
        ),
    )
