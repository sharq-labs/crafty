"""D1 — attributable design evaluation contracts.

An evaluation binds one exact candidate/Twin identity to one complete
ScientificResult. Selection eligibility is an explicit decision-layer input;
it is never inferred from convergence, ``ScientificResult.is_usable`` or an
archive membership.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.objectives import ObjectiveDefinition
from ..scientific.results.result import ScientificResult
from ..scientific.serialization import require_schema, schema_string
from ..scientific.twins.definition import TwinReference
from ..scientific.units.quantity import Quantity
from .candidate import DesignCandidate, DesignCandidateReference
from .fidelity import FidelityLadder
from .space import DesignSpaceReference

FIDELITY_SELECTION_SCHEMA = schema_string("fidelity_selection")
DESIGN_EVALUATION_REFERENCE_SCHEMA = schema_string("design_evaluation_reference")
DESIGN_EVALUATION_SCHEMA = schema_string("design_evaluation")
PROJECTED_OBJECTIVE_SCHEMA = schema_string("projected_objective")


class SelectionEligibility(str, Enum):
    UNKNOWN = "unknown"
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


@dataclass(frozen=True)
class FidelitySelection:
    """Exact ladder-version/rung binding, with no domain-specific meaning."""

    ladder_id: str
    ladder_version: str
    rung_id: str

    def __post_init__(self) -> None:
        for name in ("ladder_id", "ladder_version", "rung_id"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise InvalidScientificProblem(f"fidelity selection requires {name}")
            object.__setattr__(self, name, value)

    def validate_against(self, ladder: FidelityLadder) -> "FidelitySelection":
        if not isinstance(ladder, FidelityLadder):
            raise InvalidScientificProblem("fidelity selection requires FidelityLadder")
        if (self.ladder_id, self.ladder_version) != (
            ladder.ladder_id,
            ladder.version,
        ):
            raise InvalidScientificProblem(
                "fidelity selection does not match supplied ladder identity"
            )
        ladder.rung(self.rung_id)
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FIDELITY_SELECTION_SCHEMA,
            "ladder_id": self.ladder_id,
            "ladder_version": self.ladder_version,
            "rung_id": self.rung_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FidelitySelection":
        require_schema(payload, FIDELITY_SELECTION_SCHEMA)
        return cls(
            ladder_id=payload["ladder_id"],
            ladder_version=payload["ladder_version"],
            rung_id=payload["rung_id"],
        )


@dataclass(frozen=True)
class DesignEvaluationReference:
    evaluation_id: str

    def __post_init__(self) -> None:
        evaluation_id = str(self.evaluation_id).strip()
        if not evaluation_id:
            raise InvalidScientificProblem("evaluation reference requires evaluation_id")
        object.__setattr__(self, "evaluation_id", evaluation_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DESIGN_EVALUATION_REFERENCE_SCHEMA,
            "evaluation_id": self.evaluation_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DesignEvaluationReference":
        require_schema(payload, DESIGN_EVALUATION_REFERENCE_SCHEMA)
        return cls(evaluation_id=payload["evaluation_id"])


@dataclass(frozen=True)
class DesignEvaluation:
    """One exact candidate evaluation backed by one complete scientific result."""

    evaluation_id: str
    candidate: DesignCandidateReference
    twin: TwinReference
    design_space: DesignSpaceReference
    result: ScientificResult
    fidelity: FidelitySelection | None = None
    eligibility: SelectionEligibility = SelectionEligibility.UNKNOWN
    eligibility_reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        evaluation_id = str(self.evaluation_id).strip()
        if not evaluation_id:
            raise InvalidScientificProblem("design evaluation requires evaluation_id")
        if not isinstance(self.candidate, DesignCandidateReference):
            raise InvalidScientificProblem(
                "design evaluation requires DesignCandidateReference"
            )
        if not isinstance(self.twin, TwinReference):
            raise InvalidScientificProblem("design evaluation requires TwinReference")
        if not isinstance(self.design_space, DesignSpaceReference):
            raise InvalidScientificProblem(
                "design evaluation requires DesignSpaceReference"
            )
        if not isinstance(self.result, ScientificResult):
            raise InvalidScientificProblem(
                "design evaluation requires complete ScientificResult"
            )
        if self.fidelity is not None and not isinstance(
            self.fidelity, FidelitySelection
        ):
            raise InvalidScientificProblem(
                "design evaluation fidelity must be FidelitySelection"
            )

        eligibility = SelectionEligibility(self.eligibility)
        reasons = tuple(str(reason).strip() for reason in self.eligibility_reasons)
        if any(not reason for reason in reasons):
            raise InvalidScientificProblem("eligibility reasons must be non-empty")
        if eligibility is SelectionEligibility.UNKNOWN and reasons:
            raise InvalidScientificProblem(
                "UNKNOWN selection eligibility cannot carry decision reasons"
            )
        if eligibility is not SelectionEligibility.UNKNOWN and not reasons:
            raise InvalidScientificProblem(
                "explicit selection eligibility requires at least one reason"
            )

        object.__setattr__(self, "evaluation_id", evaluation_id)
        object.__setattr__(self, "eligibility", eligibility)
        object.__setattr__(self, "eligibility_reasons", reasons)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def reference(self) -> DesignEvaluationReference:
        return DesignEvaluationReference(self.evaluation_id)

    def validate_candidate(self, candidate: DesignCandidate) -> "DesignEvaluation":
        """Prove the D0 candidate/Twin/design-space identities agree exactly."""
        if not isinstance(candidate, DesignCandidate):
            raise InvalidScientificProblem("evaluation validation requires DesignCandidate")
        if self.candidate.candidate_id != candidate.candidate_id:
            raise InvalidScientificProblem("evaluation candidate identity mismatch")
        if self.twin.key != candidate.twin.key:
            raise InvalidScientificProblem("evaluation Twin identity mismatch")
        if self.design_space.key != candidate.design_space.key:
            raise InvalidScientificProblem("evaluation design-space identity mismatch")
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DESIGN_EVALUATION_SCHEMA,
            "evaluation_id": self.evaluation_id,
            "candidate": self.candidate.to_dict(),
            "twin": self.twin.to_dict(),
            "design_space": self.design_space.to_dict(),
            "result": self.result.to_dict(),
            "fidelity": self.fidelity.to_dict() if self.fidelity else None,
            "eligibility": self.eligibility.value,
            "eligibility_reasons": list(self.eligibility_reasons),
            "metadata": dict(sorted(self.metadata.items(), key=lambda item: item[0])),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DesignEvaluation":
        require_schema(payload, DESIGN_EVALUATION_SCHEMA)
        fidelity = payload.get("fidelity")
        return cls(
            evaluation_id=payload["evaluation_id"],
            candidate=DesignCandidateReference.from_dict(payload["candidate"]),
            twin=TwinReference.from_dict(payload["twin"]),
            design_space=DesignSpaceReference.from_dict(payload["design_space"]),
            result=ScientificResult.from_dict(payload["result"]),
            fidelity=FidelitySelection.from_dict(fidelity) if fidelity else None,
            eligibility=SelectionEligibility(payload.get("eligibility", "unknown")),
            eligibility_reasons=tuple(payload.get("eligibility_reasons", ())),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class ProjectedObjective:
    objective: ObjectiveDefinition
    value: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.objective, ObjectiveDefinition):
            raise InvalidScientificProblem(
                "projected objective requires ObjectiveDefinition"
            )
        if not isinstance(self.value, Quantity):
            raise InvalidScientificProblem("projected objective value must be Quantity")
        converted = self.value.to(self.objective.unit)
        object.__setattr__(self, "value", converted)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PROJECTED_OBJECTIVE_SCHEMA,
            "objective": self.objective.to_dict(),
            "value": self.value.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProjectedObjective":
        require_schema(payload, PROJECTED_OBJECTIVE_SCHEMA)
        return cls(
            objective=ObjectiveDefinition.from_dict(payload["objective"]),
            value=Quantity.from_dict(payload["value"]),
        )


def require_objectives(
    objectives: Iterable[ObjectiveDefinition],
) -> tuple[ObjectiveDefinition, ...]:
    declared = tuple(objectives)
    if not declared:
        raise InvalidScientificProblem("selection requires at least one objective")
    if any(not isinstance(item, ObjectiveDefinition) for item in declared):
        raise InvalidScientificProblem(
            "selection objectives must be ObjectiveDefinition records"
        )
    names = [item.name for item in declared]
    if len(names) != len(set(names)):
        raise InvalidScientificProblem("selection objective names must be unique")
    return declared


def project_objectives(
    evaluation: DesignEvaluation,
    objectives: Iterable[ObjectiveDefinition],
) -> tuple[ProjectedObjective, ...]:
    """Read exact declared metrics from the attributable ScientificResult."""
    if not isinstance(evaluation, DesignEvaluation):
        raise InvalidScientificProblem("objective projection requires DesignEvaluation")
    declared = require_objectives(objectives)
    projected: list[ProjectedObjective] = []
    for objective in declared:
        # ScientificResult.value fails closed when the metric is missing. The
        # Quantity conversion proves dimensional compatibility.
        value = evaluation.result.value(objective.metric).to(objective.unit)
        projected.append(ProjectedObjective(objective=objective, value=value))
    return tuple(projected)
