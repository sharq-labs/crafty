"""The records-only reader EXTENSION — and its size is the measurement.

`EXEC-SPEC` shipped a records-only reader whose structure question is answered
from a **closed** map of known schemas and a per-element-type key table, and its
own evidence recorded the consequence as unmeasured:

> `instrument.py` contains per-column schema knowledge … **the domains ×
> consumers cost of option E is unmeasured.**

This file measures it. `EXEC-SPEC` may not be edited (preregistration §12.3), so
two new consumers arrive as an extension written beside it. Every line below
that is *specific to mechanics or to species* is the cost of one more domain,
for one consumer. Multiply by the number of records-only consumers Crafty
eventually has.

The rules are unchanged: serialized payloads only, `engcore.scientific` may be
imported, **nothing under `engcore.domains` and nothing from the probes** may be —
asserted by AST scan in the test module. The probes are physics, not schema, and
importing them to understand a payload would be exactly the failure being
measured.
"""

from __future__ import annotations

from typing import Any, Mapping

from experiments.exec_spec_residue.instrument import (
    Answer,
    AnswerStatus,
    PlannerQuestion,
    inspect as base_inspect,
)

from .schemas import MECH_STRUCTURE_SCHEMA, SPECIES_STRUCTURE_SCHEMA

__all__ = ["inspect", "structure_answer", "domain_questions", "DomainQuestion"]

DomainQuestion = str

#: The domain questions the brief requires be answerable per consumer. They are
#: NOT the eight universal ones — that is the point. Each is specific to its
#: science, and each needed a hand-written reader branch.
MECHANICS_QUESTIONS: tuple[DomainQuestion, ...] = (
    "which entities are connected?",
    "which variable components are unknown?",
    "what constraints exist?",
    "what constitutive behaviour applies?",
    "what capabilities are required?",
)

SPECIES_QUESTIONS: tuple[DomainQuestion, ...] = (
    "which species exist?",
    "which reactions connect them?",
    "what stoichiometric relationship exists?",
    "what state variables evolve?",
    "what capabilities are required?",
)


def structure_answer(structure: Mapping[str, Any] | None) -> Answer:
    """The structure question, extended to the two new schemas.

    Note what had to be written: one branch per schema, each naming that
    schema's own field spellings. A reader cannot ask a payload what it means.
    """
    if structure is None:
        return Answer(
            AnswerStatus.IMPOSSIBLE,
            None,
            "no structural payload; a ScientificProblem has no field in which "
            "connectivity or a coefficient table could be stated",
        )
    schema = str(structure.get("schema", ""))
    if schema == MECH_STRUCTURE_SCHEMA:
        return Answer(
            AnswerStatus.RECOVERABLE,
            {
                "kind": "incidence",
                "entities": {
                    "nodes": len(structure["node_coordinates"]),
                    "elements": len(structure["elements"]),
                },
                "edges": [
                    {"element": index, "nodes": list(nodes)}
                    for index, nodes in enumerate(structure["elements"])
                ],
                "constrained_dof": list(structure["constrained_dof"]),
                "loaded_dof": list(structure["loaded_dof"]),
                "dof_index_rule": structure["dof_index_rule"],
            },
            "element-to-node incidence with vertex order, from typed fields of a "
            "published schema",
        )
    if schema == SPECIES_STRUCTURE_SCHEMA:
        return Answer(
            AnswerStatus.RECOVERABLE,
            {
                "kind": "coefficient-table",
                "entities": {
                    "species": list(structure["species_order"]),
                    "reactions": list(structure["reaction_order"]),
                },
                "axes": list(structure["stoichiometry_axes"]),
                "coefficients": [list(row) for row in structure["stoichiometry"]],
            },
            "signed coefficient table over two named index sets, from typed "
            "fields of a published schema",
        )
    return base_inspect({"schema": "scientific_problem/1", "problem_id": "probe"}, structure)[
        PlannerQuestion.STRUCTURE
    ]


def inspect(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None = None,
) -> dict[PlannerQuestion, Answer]:
    """The eight universal questions, with the structure branch extended."""
    answers = base_inspect(problem_payload, None)
    answers[PlannerQuestion.STRUCTURE] = structure_answer(structure_payload)
    return answers


def domain_questions(
    column: str,
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
) -> dict[DomainQuestion, Answer]:
    """The five per-consumer questions the brief requires.

    Every answer below is assembled by code that knows this consumer's schema.
    That is not a defect of the implementation; it is the finding. A reader
    holding only `engcore.scientific` contracts and a payload it has never seen
    can report the payload's schema string and nothing else about its meaning.
    """
    universal = inspect(problem_payload, structure_payload)
    structure = universal[PlannerQuestion.STRUCTURE]
    quantities = universal[PlannerQuestion.QUANTITIES]
    capabilities = universal[PlannerQuestion.CAPABILITIES]

    if column == "col-mech":
        constitutive = [
            entry
            for entry in quantities.value["parameters"]
            if entry["name"] in {"youngs_modulus", "poisson_ratio", "plane_assumption"}
        ]
        return {
            MECHANICS_QUESTIONS[0]: structure,
            MECHANICS_QUESTIONS[1]: Answer(
                AnswerStatus.AMBIGUOUS,
                [
                    entry["name"]
                    for entry in quantities.value["variables"]
                    if entry["role"] == "state"
                ],
                "eight scalar STATE variables named 'u_x:n0'…: a reader can list "
                "them and cannot know that pairs of them are components of one "
                "vector at one node. The pairing is in the spelling",
            ),
            MECHANICS_QUESTIONS[2]: Answer(
                AnswerStatus.RECOVERABLE
                if structure.status is AnswerStatus.RECOVERABLE
                else AnswerStatus.IMPOSSIBLE,
                None
                if structure.value is None
                else structure.value.get("constrained_dof"),
                "degree-of-freedom indices, meaningful only with the payload's "
                "own dof_index_rule",
            ),
            MECHANICS_QUESTIONS[3]: Answer(
                AnswerStatus.RECOVERABLE,
                constitutive,
                "two dimensional scalars and one category; the 3x3 matrix they "
                "generate is derived and is on no record — correctly",
            ),
            MECHANICS_QUESTIONS[4]: capabilities,
        }
    if column == "col-species":
        return {
            SPECIES_QUESTIONS[0]: Answer(
                AnswerStatus.RECOVERABLE
                if structure.status is AnswerStatus.RECOVERABLE
                else AnswerStatus.IMPOSSIBLE,
                None if structure.value is None else structure.value["entities"]["species"],
                "the species index set, in state order, from the structure payload",
            ),
            SPECIES_QUESTIONS[1]: Answer(
                AnswerStatus.RECOVERABLE
                if structure.status is AnswerStatus.RECOVERABLE
                else AnswerStatus.IMPOSSIBLE,
                None if structure.value is None else structure.value["coefficients"],
                "the coefficient table states which species each reaction "
                "consumes and produces",
            ),
            SPECIES_QUESTIONS[2]: structure,
            SPECIES_QUESTIONS[3]: Answer(
                AnswerStatus.RECOVERABLE,
                [
                    entry["name"]
                    for entry in quantities.value["variables"]
                    if entry["role"] == "state"
                ],
                "three STATE variables of one dimension; that they are chemical "
                "species rather than three unrelated quantities is stated only "
                "by the structure payload",
            ),
            SPECIES_QUESTIONS[4]: capabilities,
        }
    raise ValueError(f"unknown column {column!r}")
