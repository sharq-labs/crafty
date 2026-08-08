"""Solver capabilities.

Capabilities are *extensible identifiers*, not a closed enum: a future domain
package must be able to declare ``CIRCUIT_TRANSIENT`` without editing the
core. Well-known names are provided as constants for convenience, but the
core never depends on any particular physical capability existing.

A capability answers exactly one question: which solver can support this
ScientificProblem?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ..errors import ScientificCoreError
from ..serialization import require_schema, schema_string

CAPABILITY_SCHEMA = schema_string("solver_capability")


@dataclass(frozen=True)
class SolverCapability:
    """A namespaced capability identifier, e.g. ``core:ode``."""

    name: str
    description: str = ""

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise ScientificCoreError("capability name must be non-empty")
        if any(ch.isspace() for ch in name):
            raise ScientificCoreError(
                f"capability name {name!r} must not contain whitespace"
            )
        object.__setattr__(self, "name", name)

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.name

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CAPABILITY_SCHEMA,
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SolverCapability":
        require_schema(payload, CAPABILITY_SCHEMA)
        return cls(
            name=payload["name"], description=payload.get("description", "")
        )


def capability_names(capabilities: Iterable[SolverCapability | str]) -> frozenset[str]:
    """Normalize a mixed iterable of capabilities/names to a name set."""
    return frozenset(
        c.name if isinstance(c, SolverCapability) else str(c) for c in capabilities
    )


class CoreCapabilities:
    """Solver-shape capabilities the core itself can reason about.

    These describe the *mathematical form* of a problem, not a physical
    domain. Domain packages add their own names (``electrical:dc``,
    ``thermal:steady``) without touching this class.
    """

    ALGEBRAIC = SolverCapability("core:algebraic", "Closed-form algebraic evaluation")
    LINEAR_SYSTEM = SolverCapability("core:linear_system", "Linear system solve")
    NONLINEAR_SYSTEM = SolverCapability(
        "core:nonlinear_system", "Nonlinear root finding"
    )
    ODE = SolverCapability("core:ode", "Ordinary differential equations")
    DAE = SolverCapability("core:dae", "Differential algebraic equations")
    PDE = SolverCapability("core:pde", "Partial differential equations")
    OPTIMIZATION = SolverCapability("core:optimization", "Numerical optimization")
    STOCHASTIC = SolverCapability("core:stochastic", "Stochastic/Monte Carlo methods")

    @classmethod
    def all(cls) -> tuple[SolverCapability, ...]:
        return tuple(
            value
            for key, value in sorted(vars(cls).items())
            if isinstance(value, SolverCapability)
        )
