"""D1 — immutable population identity.

A population declares which candidate identities belong to one generation of
one exact design space. It does not generate, score, simulate, filter or rank
those candidates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..scientific.errors import InvalidScientificProblem
from ..scientific.serialization import require_schema, schema_string
from .candidate import DesignCandidateReference
from .space import DesignSpaceReference

DESIGN_POPULATION_SCHEMA = schema_string("design_population")


@dataclass(frozen=True)
class DesignPopulation:
    population_id: str
    design_space: DesignSpaceReference
    generation: int
    members: tuple[DesignCandidateReference, ...]

    def __post_init__(self) -> None:
        population_id = str(self.population_id).strip()
        if not population_id:
            raise InvalidScientificProblem("design population requires population_id")
        if not isinstance(self.design_space, DesignSpaceReference):
            raise InvalidScientificProblem(
                "design population requires exact DesignSpaceReference"
            )
        if isinstance(self.generation, bool) or not isinstance(self.generation, int):
            raise InvalidScientificProblem("population generation must be an integer")
        if self.generation < 0:
            raise InvalidScientificProblem("population generation cannot be negative")

        members = tuple(self.members)
        if not members:
            raise InvalidScientificProblem("design population requires at least one member")
        if any(not isinstance(member, DesignCandidateReference) for member in members):
            raise InvalidScientificProblem(
                "population members must be DesignCandidateReference records"
            )
        ids = [member.candidate_id for member in members]
        if len(ids) != len(set(ids)):
            raise InvalidScientificProblem("design population members must be unique")

        object.__setattr__(self, "population_id", population_id)
        object.__setattr__(
            self,
            "members",
            tuple(sorted(members, key=lambda member: member.candidate_id)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DESIGN_POPULATION_SCHEMA,
            "population_id": self.population_id,
            "design_space": self.design_space.to_dict(),
            "generation": self.generation,
            "members": [member.to_dict() for member in self.members],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DesignPopulation":
        require_schema(payload, DESIGN_POPULATION_SCHEMA)
        return cls(
            population_id=payload["population_id"],
            design_space=DesignSpaceReference.from_dict(payload["design_space"]),
            generation=payload["generation"],
            members=tuple(
                DesignCandidateReference.from_dict(item)
                for item in payload.get("members", ())
            ),
        )
