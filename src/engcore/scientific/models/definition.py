"""Scientific model definition and validity domain.

A model is not an equation string. It is a versioned scientific claim with
declared requirements, assumptions, a validity domain, references and a
validation status. Recording *when a model is valid* is as important as
recording what it computes — a model evaluated outside its validated domain
must be reportable as such rather than silently trusted.

No physical laws are implemented here, and none are registered by the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..errors import InvalidScientificProblem, ModelValidityError
from ..serialization import require_schema, schema_string
from ..units.quantity import Quantity
from ..units.validation import require_same_dimension

MODEL_SCHEMA = schema_string("scientific_model_definition")
RANGE_CONDITION_SCHEMA = schema_string("validity_range_condition")
CATEGORY_CONDITION_SCHEMA = schema_string("validity_category_condition")
FLAG_CONDITION_SCHEMA = schema_string("validity_flag_condition")
VALIDITY_DOMAIN_SCHEMA = schema_string("validity_domain")
VALIDITY_ASSESSMENT_SCHEMA = schema_string("validity_assessment")


class ModelType(str, Enum):
    """Epistemic character of a model — how much it is derived versus fitted."""

    FUNDAMENTAL_RELATION = "fundamental_relation"
    CONSTITUTIVE_MODEL = "constitutive_model"
    EMPIRICAL_CORRELATION = "empirical_correlation"
    APPROXIMATION = "approximation"
    NUMERICAL_MODEL = "numerical_model"
    DATA_DRIVEN_MODEL = "data_driven_model"


class ModelValidationStatus(str, Enum):
    """What has actually been established about this model."""

    UNVALIDATED = "unvalidated"
    SELF_CONSISTENT = "self_consistent"
    BENCHMARK_VALIDATED = "benchmark_validated"
    EXPERIMENTALLY_VALIDATED = "experimentally_validated"
    DEPRECATED = "deprecated"


class ValidityStatus(str, Enum):
    IN_DOMAIN = "in_domain"
    OUTSIDE_VALIDATED_DOMAIN = "outside_validated_domain"
    UNKNOWN = "unknown"          # required context was not supplied


# ---- validity conditions -------------------------------------------------
# Structured predicates, deliberately generic: the core knows about ranges,
# category membership and flags. It does not know about temperature, Reynolds
# number or phase — domains express those *through* these primitives.


@dataclass(frozen=True)
class RangeCondition:
    """``minimum <= context[name] <= maximum`` with unit awareness."""

    name: str
    minimum: Quantity | None = None
    maximum: Quantity | None = None
    description: str = ""

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ModelValidityError("range condition requires a name")
        object.__setattr__(self, "name", str(self.name).strip())
        if self.minimum is None and self.maximum is None:
            raise ModelValidityError(
                f"range condition {self.name!r} needs a minimum or a maximum"
            )
        for bound in (self.minimum, self.maximum):
            if bound is not None and not isinstance(bound, Quantity):
                raise ModelValidityError(
                    f"range condition {self.name!r} bounds must be Quantities"
                )
        if self.minimum is not None and self.maximum is not None:
            require_same_dimension(
                self.minimum, self.maximum,
                context=f"validity range {self.name!r}",
            )
            if self.maximum.to(self.minimum.units).magnitude < self.minimum.magnitude:
                raise ModelValidityError(
                    f"range condition {self.name!r}: maximum below minimum"
                )

    def evaluate(self, value: Any) -> ValidityStatus:
        if not isinstance(value, Quantity):
            return ValidityStatus.UNKNOWN
        reference = self.minimum or self.maximum
        if not value.is_compatible_with(reference):
            raise ModelValidityError(
                f"validity condition {self.name!r}: value {value} is not "
                f"dimensionally compatible with {reference}"
            )
        if self.minimum is not None:
            if value.to(self.minimum.units).magnitude < self.minimum.magnitude:
                return ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        if self.maximum is not None:
            if value.to(self.maximum.units).magnitude > self.maximum.magnitude:
                return ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        return ValidityStatus.IN_DOMAIN

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RANGE_CONDITION_SCHEMA,
            "name": self.name,
            "minimum": self.minimum.to_dict() if self.minimum else None,
            "maximum": self.maximum.to_dict() if self.maximum else None,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RangeCondition":
        require_schema(payload, RANGE_CONDITION_SCHEMA)
        minimum, maximum = payload.get("minimum"), payload.get("maximum")
        return cls(
            name=payload["name"],
            minimum=Quantity.from_dict(minimum) if minimum else None,
            maximum=Quantity.from_dict(maximum) if maximum else None,
            description=payload.get("description", ""),
        )


@dataclass(frozen=True)
class CategoryCondition:
    """``context[name] in allowed`` — e.g. material class, phase, regime."""

    name: str
    allowed: frozenset[str] = frozenset()
    description: str = ""

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ModelValidityError("category condition requires a name")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "allowed", frozenset(self.allowed))
        if not self.allowed:
            raise ModelValidityError(
                f"category condition {self.name!r} needs allowed values"
            )

    def evaluate(self, value: Any) -> ValidityStatus:
        if value is None:
            return ValidityStatus.UNKNOWN
        if not isinstance(value, str):
            return ValidityStatus.UNKNOWN
        return (
            ValidityStatus.IN_DOMAIN
            if value in self.allowed
            else ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CATEGORY_CONDITION_SCHEMA,
            "name": self.name,
            "allowed": sorted(self.allowed),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CategoryCondition":
        require_schema(payload, CATEGORY_CONDITION_SCHEMA)
        return cls(
            name=payload["name"],
            allowed=frozenset(payload.get("allowed", ())),
            description=payload.get("description", ""),
        )


@dataclass(frozen=True)
class FlagCondition:
    """``context[name] is expected`` — e.g. steady_state=True, linear=True."""

    name: str
    expected: bool = True
    description: str = ""

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ModelValidityError("flag condition requires a name")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "expected", bool(self.expected))

    def evaluate(self, value: Any) -> ValidityStatus:
        if not isinstance(value, bool):
            return ValidityStatus.UNKNOWN
        return (
            ValidityStatus.IN_DOMAIN
            if value is self.expected
            else ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FLAG_CONDITION_SCHEMA,
            "name": self.name,
            "expected": self.expected,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FlagCondition":
        require_schema(payload, FLAG_CONDITION_SCHEMA)
        return cls(
            name=payload["name"],
            expected=bool(payload.get("expected", True)),
            description=payload.get("description", ""),
        )


ValidityCondition = RangeCondition | CategoryCondition | FlagCondition

_CONDITION_DECODERS = {
    RANGE_CONDITION_SCHEMA: RangeCondition,
    CATEGORY_CONDITION_SCHEMA: CategoryCondition,
    FLAG_CONDITION_SCHEMA: FlagCondition,
}


def _decode_condition(payload: Mapping[str, Any]) -> ValidityCondition:
    decoder = _CONDITION_DECODERS.get(payload.get("schema"))
    if decoder is None:
        raise ModelValidityError(
            f"unknown validity condition schema {payload.get('schema')!r}"
        )
    return decoder.from_dict(payload)


@dataclass(frozen=True)
class ValidityAssessment:
    """Result of testing a validity domain against a context."""

    status: ValidityStatus
    satisfied: tuple[str, ...] = ()
    violated: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": VALIDITY_ASSESSMENT_SCHEMA,
            "status": self.status.value,
            "satisfied": list(self.satisfied),
            "violated": list(self.violated),
            "unknown": list(self.unknown),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ValidityAssessment":
        require_schema(payload, VALIDITY_ASSESSMENT_SCHEMA)
        return cls(
            status=ValidityStatus(payload["status"]),
            satisfied=tuple(payload.get("satisfied", ())),
            violated=tuple(payload.get("violated", ())),
            unknown=tuple(payload.get("unknown", ())),
        )


@dataclass(frozen=True)
class ValidityDomain:
    """The conditions under which a model's results are considered validated."""

    conditions: tuple[ValidityCondition, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "conditions", tuple(self.conditions))
        names = [c.name for c in self.conditions]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ModelValidityError(
                f"duplicate validity condition names: {sorted(duplicates)}"
            )

    def assess(self, context: Mapping[str, Any]) -> ValidityAssessment:
        """Classify a context as in-domain, outside-domain, or unknown.

        A domain with no conditions is UNKNOWN, not valid: absence of declared
        limits is not evidence of unlimited validity.
        """
        if not self.conditions:
            return ValidityAssessment(status=ValidityStatus.UNKNOWN)

        satisfied: list[str] = []
        violated: list[str] = []
        unknown: list[str] = []
        for condition in self.conditions:
            outcome = condition.evaluate(context.get(condition.name))
            if outcome is ValidityStatus.IN_DOMAIN:
                satisfied.append(condition.name)
            elif outcome is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN:
                violated.append(condition.name)
            else:
                unknown.append(condition.name)

        if violated:
            status = ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        elif unknown:
            status = ValidityStatus.UNKNOWN
        else:
            status = ValidityStatus.IN_DOMAIN

        return ValidityAssessment(
            status=status,
            satisfied=tuple(satisfied),
            violated=tuple(violated),
            unknown=tuple(unknown),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": VALIDITY_DOMAIN_SCHEMA,
            "conditions": [c.to_dict() for c in self.conditions],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ValidityDomain":
        require_schema(payload, VALIDITY_DOMAIN_SCHEMA)
        return cls(
            conditions=tuple(
                _decode_condition(c) for c in payload.get("conditions", ())
            ),
            description=payload.get("description", ""),
        )


@dataclass(frozen=True)
class ScientificModelDefinition:
    """A versioned scientific model contract."""

    model_id: str
    version: str
    name: str = ""
    domain: str = ""
    model_type: ModelType = ModelType.APPROXIMATION
    description: str = ""
    required_variables: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()
    provided_metrics: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    validity: ValidityDomain = field(default_factory=ValidityDomain)
    references: tuple[str, ...] = ()
    required_capabilities: frozenset[str] = frozenset()
    validation_status: ModelValidationStatus = ModelValidationStatus.UNVALIDATED
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for label in ("model_id", "version"):
            if not str(getattr(self, label)).strip():
                raise InvalidScientificProblem(f"model requires a non-empty {label}")
            object.__setattr__(self, label, str(getattr(self, label)).strip())
        object.__setattr__(self, "model_type", ModelType(self.model_type))
        object.__setattr__(
            self, "validation_status", ModelValidationStatus(self.validation_status)
        )
        for label in (
            "required_variables", "required_parameters", "provided_metrics",
            "assumptions", "references",
        ):
            object.__setattr__(self, label, tuple(getattr(self, label)))
        object.__setattr__(
            self, "required_capabilities", frozenset(self.required_capabilities)
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def key(self) -> tuple[str, str]:
        return (self.model_id, self.version)

    def assess_validity(self, context: Mapping[str, Any]) -> ValidityAssessment:
        return self.validity.assess(context)

    def missing_requirements(self, problem) -> tuple[str, ...]:
        """Names this model needs that the problem does not supply."""
        available = {v.name for v in problem.variables}
        available |= {p.name for p in problem.parameters}
        missing = [
            name
            for name in (*self.required_variables, *self.required_parameters)
            if name not in available
        ]
        return tuple(missing)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MODEL_SCHEMA,
            "model_id": self.model_id,
            "version": self.version,
            "name": self.name,
            "domain": self.domain,
            "model_type": self.model_type.value,
            "description": self.description,
            "required_variables": list(self.required_variables),
            "required_parameters": list(self.required_parameters),
            "provided_metrics": list(self.provided_metrics),
            "assumptions": list(self.assumptions),
            "validity": self.validity.to_dict(),
            "references": list(self.references),
            "required_capabilities": sorted(self.required_capabilities),
            "validation_status": self.validation_status.value,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ScientificModelDefinition":
        require_schema(payload, MODEL_SCHEMA)
        return cls(
            model_id=payload["model_id"],
            version=payload["version"],
            name=payload.get("name", ""),
            domain=payload.get("domain", ""),
            model_type=ModelType(payload.get("model_type", "approximation")),
            description=payload.get("description", ""),
            required_variables=tuple(payload.get("required_variables", ())),
            required_parameters=tuple(payload.get("required_parameters", ())),
            provided_metrics=tuple(payload.get("provided_metrics", ())),
            assumptions=tuple(payload.get("assumptions", ())),
            validity=ValidityDomain.from_dict(payload["validity"])
            if payload.get("validity")
            else ValidityDomain(),
            references=tuple(payload.get("references", ())),
            required_capabilities=frozenset(payload.get("required_capabilities", ())),
            validation_status=ModelValidationStatus(
                payload.get("validation_status", "unvalidated")
            ),
            metadata=dict(payload.get("metadata", {})),
        )
