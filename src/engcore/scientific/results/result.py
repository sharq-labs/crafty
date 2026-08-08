"""ScientificResult — the platform's output contract.

A result is never just ``temperature = 84``. It is:

    VALUE + UNIT + SOURCE MODEL + SOLVER + ASSUMPTIONS
          + UNCERTAINTY + VALIDATION STATUS + PROVENANCE

Every one of those is a typed field here, and the type system refuses the
degenerate case: values must be Quantities, provenance is mandatory, and the
validation report can only claim what its checks established.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..errors import ScientificCoreError
from ..serialization import require_schema, schema_string
from ..solvers.protocol import ConvergenceState, SolverIdentity
from ..units.quantity import Quantity
from ..units.validation import check_unit_map
from .provenance import ProvenanceRecord
from .uncertainty import Uncertainty
from .validation import ValidationLevel, ValidationOutcome, ValidationReport

RESULT_SCHEMA = schema_string("scientific_result")


@dataclass(frozen=True)
class ScientificResult:
    """An interpreted, attributable scientific output."""

    result_id: str
    values: Mapping[str, Quantity]
    provenance: ProvenanceRecord
    problem_id: str = ""
    models: tuple[tuple[str, str], ...] = ()
    solver: SolverIdentity | None = None
    convergence: ConvergenceState = ConvergenceState.NOT_APPLICABLE
    validation: ValidationReport = field(default_factory=ValidationReport)
    uncertainty: Mapping[str, Uncertainty] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        result_id = str(self.result_id).strip()
        if not result_id:
            raise ScientificCoreError("result requires a non-empty result_id")
        object.__setattr__(self, "result_id", result_id)

        values = dict(self.values)
        for name, value in values.items():
            if not isinstance(value, Quantity):
                raise ScientificCoreError(
                    f"result value {name!r} must be a Quantity — a bare number "
                    f"is not a scientific result"
                )
        object.__setattr__(self, "values", values)

        if not isinstance(self.provenance, ProvenanceRecord):
            raise ScientificCoreError(
                "result requires a ProvenanceRecord: an unattributable number "
                "is not a scientific result"
            )

        object.__setattr__(self, "convergence", ConvergenceState(self.convergence))
        object.__setattr__(self, "models", tuple(tuple(m) for m in self.models))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", dict(self.metadata))

        uncertainty = dict(self.uncertainty)
        for name, record in uncertainty.items():
            if not isinstance(record, Uncertainty):
                raise ScientificCoreError(
                    f"uncertainty for {name!r} must be an Uncertainty record"
                )
            if name not in values:
                raise ScientificCoreError(
                    f"uncertainty declared for unknown value {name!r}"
                )
        object.__setattr__(self, "uncertainty", uncertainty)

    # ---- accessors ------------------------------------------------------
    def value(self, name: str) -> Quantity:
        try:
            return self.values[name]
        except KeyError:
            raise ScientificCoreError(
                f"result {self.result_id!r} has no value {name!r}"
            ) from None

    def uncertainty_of(self, name: str) -> Uncertainty:
        """Uncertainty for a value; explicitly UNKNOWN when none was computed."""
        self.value(name)  # existence check
        return self.uncertainty.get(name, Uncertainty.unknown())

    @property
    def validation_status(self) -> ValidationOutcome:
        return self.validation.status

    @property
    def attained_levels(self) -> frozenset[ValidationLevel]:
        return self.validation.attained_levels

    @property
    def is_usable(self) -> bool:
        """Converged (or not applicable) and no failed validation check.

        Deliberately conservative and deliberately *not* called ``is_valid``:
        it reports the absence of known problems, not the presence of proof.
        """
        return (
            self.convergence
            in (ConvergenceState.CONVERGED, ConvergenceState.NOT_APPLICABLE)
            and self.validation.status is not ValidationOutcome.FAIL
        )

    def check_units_against(self, expected_units: Mapping[str, str]) -> None:
        """Verify reported values carry the dimensionality the problem declared."""
        check_unit_map(self.values, expected_units, context=f"result {self.result_id!r}")

    # ---- serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": RESULT_SCHEMA,
            "result_id": self.result_id,
            "problem_id": self.problem_id,
            "values": {k: self.values[k].to_dict() for k in sorted(self.values)},
            "models": [list(m) for m in self.models],
            "solver": self.solver.to_dict() if self.solver else None,
            "convergence": self.convergence.value,
            "validation": self.validation.to_dict(),
            "uncertainty": {
                k: self.uncertainty[k].to_dict() for k in sorted(self.uncertainty)
            },
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "artifacts": list(self.artifacts),
            "provenance": self.provenance.to_dict(),
            "metadata": dict(sorted(self.metadata.items(), key=lambda kv: kv[0])),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ScientificResult":
        require_schema(payload, RESULT_SCHEMA)
        solver = payload.get("solver")
        return cls(
            result_id=payload["result_id"],
            problem_id=payload.get("problem_id", ""),
            values={
                k: Quantity.from_dict(v)
                for k, v in (payload.get("values") or {}).items()
            },
            models=tuple(tuple(m) for m in payload.get("models", ())),
            solver=SolverIdentity.from_dict(solver) if solver else None,
            convergence=ConvergenceState(payload.get("convergence", "not_applicable")),
            validation=ValidationReport.from_dict(payload["validation"])
            if payload.get("validation")
            else ValidationReport(),
            uncertainty={
                k: Uncertainty.from_dict(v)
                for k, v in (payload.get("uncertainty") or {}).items()
            },
            assumptions=tuple(payload.get("assumptions", ())),
            warnings=tuple(payload.get("warnings", ())),
            artifacts=tuple(payload.get("artifacts", ())),
            provenance=ProvenanceRecord.from_dict(payload["provenance"]),
            metadata=dict(payload.get("metadata", {})),
        )
