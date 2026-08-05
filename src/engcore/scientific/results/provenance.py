"""Provenance record.

Mandatory for every scientific result: a number whose origin cannot be
reconstructed is not a scientific result.

Privacy position: this module **collects nothing on its own**. Software
version, git commit, environment facts and timestamps are all supplied by the
caller. Auto-harvesting machine identity would be both a privacy problem and
a determinism problem (records would differ between runs that are otherwise
identical).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..errors import ScientificCoreError
from ..serialization import require_schema, schema_string
from ..units.quantity import Quantity

PROVENANCE_SCHEMA = schema_string("provenance_record")


@dataclass(frozen=True)
class ProvenanceRecord:
    """Everything needed to attribute and re-derive a result."""

    run_id: str
    software_version: str = ""
    git_commit: str | None = None
    models: tuple[tuple[str, str], ...] = ()      # (model_id, version)
    solvers: tuple[tuple[str, str], ...] = ()     # (solver_id, version)
    inputs: Mapping[str, Quantity] = field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    tolerances: Mapping[str, float] = field(default_factory=dict)
    environment: Mapping[str, str] = field(default_factory=dict)
    timestamp: str | None = None
    parent_run_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        run_id = str(self.run_id).strip()
        if not run_id:
            raise ScientificCoreError("provenance requires a non-empty run_id")
        object.__setattr__(self, "run_id", run_id)

        object.__setattr__(
            self, "models", tuple((str(a), str(b)) for a, b in self.models)
        )
        object.__setattr__(
            self, "solvers", tuple((str(a), str(b)) for a, b in self.solvers)
        )
        object.__setattr__(self, "assumptions", tuple(self.assumptions))

        inputs = dict(self.inputs)
        for name, value in inputs.items():
            if not isinstance(value, Quantity):
                raise ScientificCoreError(
                    f"provenance input {name!r} must be a Quantity — provenance "
                    f"never records unit-stripped values"
                )
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(
            self, "tolerances", {str(k): float(v) for k, v in self.tolerances.items()}
        )
        object.__setattr__(
            self, "environment", {str(k): str(v) for k, v in self.environment.items()}
        )
        object.__setattr__(self, "metadata", dict(self.metadata))

    def derived(self, run_id: str, **overrides: Any) -> "ProvenanceRecord":
        """A child record that keeps the lineage link explicit."""
        base = {
            "run_id": run_id,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "models": self.models,
            "solvers": self.solvers,
            "inputs": self.inputs,
            "assumptions": self.assumptions,
            "tolerances": self.tolerances,
            "environment": self.environment,
            "timestamp": self.timestamp,
            "parent_run_id": self.run_id,
            "metadata": self.metadata,
        }
        base.update(overrides)
        return ProvenanceRecord(**base)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PROVENANCE_SCHEMA,
            "run_id": self.run_id,
            "software_version": self.software_version,
            "git_commit": self.git_commit,
            "models": [list(m) for m in self.models],
            "solvers": [list(s) for s in self.solvers],
            "inputs": {k: self.inputs[k].to_dict() for k in sorted(self.inputs)},
            "assumptions": list(self.assumptions),
            "tolerances": dict(sorted(self.tolerances.items())),
            "environment": dict(sorted(self.environment.items())),
            "timestamp": self.timestamp,
            "parent_run_id": self.parent_run_id,
            "metadata": dict(sorted(self.metadata.items(), key=lambda kv: kv[0])),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProvenanceRecord":
        require_schema(payload, PROVENANCE_SCHEMA)
        return cls(
            run_id=payload["run_id"],
            software_version=payload.get("software_version", ""),
            git_commit=payload.get("git_commit"),
            models=tuple(tuple(m) for m in payload.get("models", ())),
            solvers=tuple(tuple(s) for s in payload.get("solvers", ())),
            inputs={
                k: Quantity.from_dict(v)
                for k, v in (payload.get("inputs") or {}).items()
            },
            assumptions=tuple(payload.get("assumptions", ())),
            tolerances=dict(payload.get("tolerances", {})),
            environment=dict(payload.get("environment", {})),
            timestamp=payload.get("timestamp"),
            parent_run_id=payload.get("parent_run_id"),
            metadata=dict(payload.get("metadata", {})),
        )
