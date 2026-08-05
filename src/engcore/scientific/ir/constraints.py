"""Constraint representation.

Constraints are *typed references*, never executable strings: a constraint
names a metric, an operator, and a bound with units. There is no ``eval``,
no ``exec``, and no dynamic expression compilation anywhere in the core.

Symbolic expressions (``stress <= allowable_stress(T)``) are deferred; V0
covers the ``metric OP bound`` form that real studies overwhelmingly use.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from ..errors import InvalidScientificProblem
from ..serialization import require_schema, schema_string
from ..units.quantity import Quantity
from ..units.validation import require_same_dimension

CONSTRAINT_SCHEMA = schema_string("constraint_definition")
CONSTRAINT_CHECK_SCHEMA = schema_string("constraint_check")


class ConstraintOperator(str, Enum):
    LESS_EQUAL = "<="
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    GREATER_THAN = ">"
    EQUAL = "=="


@dataclass(frozen=True)
class ConstraintCheck:
    """Outcome of testing one constraint against one measured value."""

    constraint: str
    satisfied: bool
    margin: Quantity
    value: Quantity

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CONSTRAINT_CHECK_SCHEMA,
            "constraint": self.constraint,
            "satisfied": self.satisfied,
            "margin": self.margin.to_dict(),
            "value": self.value.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConstraintCheck":
        require_schema(payload, CONSTRAINT_CHECK_SCHEMA)
        return cls(
            constraint=payload["constraint"],
            satisfied=bool(payload["satisfied"]),
            margin=Quantity.from_dict(payload["margin"]),
            value=Quantity.from_dict(payload["value"]),
        )


@dataclass(frozen=True)
class ConstraintDefinition:
    """e.g. ``temperature <= 350 K``, ``voltage >= 4.8 V``."""

    name: str
    metric: str
    operator: ConstraintOperator
    bound: Quantity
    tolerance: Quantity | None = None
    description: str = ""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        metric = str(self.metric).strip()
        if not name:
            raise InvalidScientificProblem("constraint name must be non-empty")
        if not metric:
            raise InvalidScientificProblem(
                f"constraint {name!r} must reference a metric name"
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "operator", ConstraintOperator(self.operator))
        if not isinstance(self.bound, Quantity):
            raise InvalidScientificProblem(
                f"constraint {name!r} bound must be a Quantity "
                f"(units are never implicit)"
            )
        if self.tolerance is not None:
            if not isinstance(self.tolerance, Quantity):
                raise InvalidScientificProblem(
                    f"constraint {name!r} tolerance must be a Quantity"
                )
            require_same_dimension(
                self.tolerance,
                self.bound,
                context=f"constraint {name!r} tolerance",
            )
            if self.tolerance.to(self.bound.units).magnitude < 0.0:
                raise InvalidScientificProblem(
                    f"constraint {name!r}: tolerance must be non-negative"
                )

    @property
    def unit(self) -> str:
        return self.bound.units

    def check(self, value: Quantity) -> ConstraintCheck:
        """Test a measured value. Raises on dimensional mismatch rather than
        silently comparing incompatible numbers."""
        require_same_dimension(
            value, self.bound, context=f"constraint {self.name!r} value"
        )
        measured = value.to(self.bound.units)
        tol = (
            self.tolerance.to(self.bound.units).magnitude
            if self.tolerance is not None
            else 0.0
        )
        delta = measured.magnitude - self.bound.magnitude

        if self.operator in (
            ConstraintOperator.LESS_EQUAL,
            ConstraintOperator.LESS_THAN,
        ):
            margin = -delta          # positive when satisfied
            satisfied = delta <= tol
        elif self.operator in (
            ConstraintOperator.GREATER_EQUAL,
            ConstraintOperator.GREATER_THAN,
        ):
            margin = delta
            satisfied = delta >= -tol
        else:  # EQUAL
            margin = tol - abs(delta)
            satisfied = abs(delta) <= tol

        return ConstraintCheck(
            constraint=self.name,
            satisfied=bool(satisfied),
            margin=Quantity(margin, self.bound.units),
            value=measured,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CONSTRAINT_SCHEMA,
            "name": self.name,
            "metric": self.metric,
            "operator": self.operator.value,
            "bound": self.bound.to_dict(),
            "tolerance": self.tolerance.to_dict() if self.tolerance else None,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConstraintDefinition":
        require_schema(payload, CONSTRAINT_SCHEMA)
        tolerance = payload.get("tolerance")
        return cls(
            name=payload["name"],
            metric=payload["metric"],
            operator=ConstraintOperator(payload["operator"]),
            bound=Quantity.from_dict(payload["bound"]),
            tolerance=Quantity.from_dict(tolerance) if tolerance else None,
            description=payload.get("description", ""),
        )
