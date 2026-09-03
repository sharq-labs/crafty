"""The records-only reader. It may know the schema; it may not know the domain.

Handed serialized payloads and nothing else, it answers the eight questions a
planner must be able to answer *before* execution. It imports
`engcore.scientific`, because a records reader legitimately knows the contracts
it is reading, and it **must not import anything under `engcore.domains`** — a
rule asserted by AST scan in the test module, not by convention.

Why one reader and not four: preregistration §13.4 makes a per-column reader a
fail condition. The entire cost case for measuring four domains rests on one
instrument serving all of them, and a reader written per column would answer
questions using knowledge the column supplied.

**What the reader is allowed to do with a structure payload.** It may read the
payload's ``schema`` string and it may read fields whose meaning is fixed by a
*published schema*. It may not import the domain that produced it and it may not
infer meaning from the spelling of a key. Where a payload's meaning is only
recoverable by knowing what the producing module meant, the answer is
``IMPOSSIBLE`` and that is the finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from engcore.scientific.composition import unresolved_inputs
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.variables import VariableRole

__all__ = [
    "PlannerQuestion",
    "AnswerStatus",
    "Answer",
    "read_problem",
    "inspect",
    "QUESTIONS",
]


class PlannerQuestion(str, Enum):
    """The eight questions preregistration §7 requires be answerable."""

    PROBLEM_TYPE = "what scientific problem type is this?"
    QUANTITIES = "what variables/quantities participate?"
    STRUCTURE = "what structure/connectivity exists?"
    CONDITIONS = "what conditions exist?"
    CAPABILITIES = "what capabilities are required?"
    MODELS = "what models are bound or selectable?"
    REQUIRED_INPUTS = "what inputs must be supplied?"
    OUTPUTS = "what outputs/QoIs can be produced?"


QUESTIONS: tuple[PlannerQuestion, ...] = tuple(PlannerQuestion)


class AnswerStatus(str, Enum):
    """How well the records answered.

    ``AMBIGUOUS`` is reserved for an answer that is readable but admits more
    than one physical reading — it is not a synonym for a partial answer.
    """

    RECOVERABLE = "recoverable"
    AMBIGUOUS = "ambiguous"
    IMPOSSIBLE = "impossible"


@dataclass(frozen=True)
class Answer:
    status: AnswerStatus
    value: Any = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "value": self.value, "detail": self.detail}


def read_problem(payload: Mapping[str, Any]) -> ScientificProblem:
    """Rebuild a problem from its serialized form. Schema-checked by the core."""
    return ScientificProblem.from_dict(payload)


#: Structure payload schemas whose *shape* this reader understands. A reader is
#: entitled to know a published schema; it is not entitled to guess one. A
#: payload whose schema is absent from this set is readable as bytes and
#: meaningless as science, which is exactly what the reader must report.
KNOWN_STRUCTURE_SCHEMAS: dict[str, str] = {
    "electrical_dc_circuit/1": "node/terminal incidence with terminal order",
    "exec_spec_slab_residue/1": "mesh resolution and an initial-profile label",
    "exec_spec_cstr_numerics/1": "integration declaration",
}

#: Of those, the ones that actually carry *connectivity*. Read from the payload's
#: own typed fields, never from a key's spelling.
_CONNECTIVITY_SCHEMAS = frozenset({"electrical_dc_circuit/1"})


def _structure_answer(structure: Mapping[str, Any] | None) -> Answer:
    if structure is None:
        return Answer(
            AnswerStatus.IMPOSSIBLE,
            None,
            "no structural payload accompanies this problem; a ScientificProblem "
            "declares variables, parameters and conditions and has no field in "
            "which connectivity could be stated",
        )
    schema = str(structure.get("schema", ""))
    if schema not in KNOWN_STRUCTURE_SCHEMAS:
        return Answer(
            AnswerStatus.IMPOSSIBLE,
            None,
            f"structural payload declares schema {schema!r}, which this reader "
            f"does not know; understanding it would require importing the domain "
            f"that wrote it",
        )
    if schema not in _CONNECTIVITY_SCHEMAS:
        return Answer(
            AnswerStatus.RECOVERABLE,
            {"schema": schema, "connectivity": None},
            f"payload is {KNOWN_STRUCTURE_SCHEMAS[schema]}; it states no "
            f"connectivity, and for this problem none exists to state",
        )
    edges = []
    for kind, a_key, b_key in (
        ("resistor", "node_a", "node_b"),
        ("voltage_source", "positive_node", "negative_node"),
        ("current_source", "from_node", "to_node"),
    ):
        for element in structure.get(f"{kind}s", ()):
            edges.append(
                {
                    "kind": kind,
                    "component_id": element["component_id"],
                    "terminals": [element[a_key], element[b_key]],
                }
            )
    nodes = [n["node_id"] for n in structure.get("nodes", ())]
    reference = [
        n["node_id"] for n in structure.get("nodes", ()) if n.get("is_reference")
    ]
    return Answer(
        AnswerStatus.RECOVERABLE,
        {"nodes": nodes, "reference_nodes": reference, "edges": edges},
        "incidence and terminal order recovered from typed fields of a published "
        "schema, without importing the domain",
    )


def inspect(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None = None,
) -> dict[PlannerQuestion, Answer]:
    """Answer all eight questions from records alone."""
    problem = read_problem(problem_payload)
    answers: dict[PlannerQuestion, Answer] = {}

    capabilities = sorted(problem.required_capabilities)
    models = [f"{m.model_id}/{m.version}" for m in problem.models]

    answers[PlannerQuestion.PROBLEM_TYPE] = (
        Answer(
            AnswerStatus.RECOVERABLE,
            {"capabilities": capabilities, "models": models},
            "problem type is named by its required capabilities and its model "
            "references; both are typed identifiers",
        )
        if capabilities or models
        else Answer(
            AnswerStatus.IMPOSSIBLE,
            None,
            "the problem declares neither a capability nor a model",
        )
    )

    answers[PlannerQuestion.QUANTITIES] = Answer(
        AnswerStatus.RECOVERABLE,
        {
            "variables": [
                {"name": v.name, "unit": v.unit, "role": v.role.value}
                for v in problem.variables
            ],
            "parameters": [
                {"name": p.name, "kind": p.kind.value} for p in problem.parameters
            ],
        },
        "every participating quantity carries a name, a unit or a typed value "
        "kind, and a role",
    )

    answers[PlannerQuestion.STRUCTURE] = _structure_answer(structure_payload)

    conditions = {
        "initial": [
            {"variable": c.variable, "value": str(c.value)}
            for c in problem.initial_conditions
        ],
        "boundary": [
            {
                "name": c.name,
                "variable": c.variable,
                "kind": c.kind.value,
                "region": c.region,
                "value": str(c.value) if c.value is not None else None,
            }
            for c in problem.boundary_conditions
        ],
    }
    answers[PlannerQuestion.CONDITIONS] = Answer(
        AnswerStatus.RECOVERABLE,
        conditions,
        "initial and boundary conditions are typed records; an empty list means "
        "the problem declares none, which is itself a readable answer",
    )

    answers[PlannerQuestion.CAPABILITIES] = Answer(
        AnswerStatus.RECOVERABLE if capabilities else AnswerStatus.IMPOSSIBLE,
        capabilities,
        "required_capabilities is a set of namespaced identifiers",
    )

    answers[PlannerQuestion.MODELS] = Answer(
        AnswerStatus.RECOVERABLE if models else AnswerStatus.IMPOSSIBLE,
        models,
        "model references are versioned identities; the reader does not need the "
        "model definition to know which one is named",
    )

    unresolved = [
        {"quantity": name, "unit": unit}
        for _pid, name, unit in unresolved_inputs([problem])
    ]
    answers[PlannerQuestion.REQUIRED_INPUTS] = Answer(
        AnswerStatus.RECOVERABLE,
        unresolved,
        "computed by the core's own unresolved_inputs: CONTROL variables, and "
        "STATE variables no declared condition determines",
    )

    answers[PlannerQuestion.OUTPUTS] = Answer(
        AnswerStatus.RECOVERABLE,
        {
            "observables": [
                v.name
                for v in problem.variables
                if v.role is VariableRole.OBSERVABLE
            ],
            "objective_metrics": [o.metric for o in problem.objectives],
        },
        "observable variables and objective metrics are both typed",
    )

    return answers
