"""The execution enumeration. **One literal dict, no fallthrough, no default.**

This module is the whole of Crafty's externally reachable execution surface. If
an identity is not a key here, no external caller can reach whatever it names —
there is no prefix match, no normalization, no alias table, no case folding, no
environment override, and no default-on-miss. A miss is a refusal, and the
refusal names the admissible set.

Where the execution *profiles* live, and why not here
-----------------------------------------------------
On the execution modules, one enumeration each. `API-MCP-V0`'s falsifier found
the first form's platform-wide profile set to be the milestone's own domain
leak: it made the application layer import ``CircuitSolver`` and
``native_circuit_solver`` — so a layer that must not know what it is executing
named a *circuit* — and it validated ``execution`` and ``execution_profile``
independently, which would have made ``{"execution": <a fluid coupling>,
"execution_profile": "ngspice"}`` an accepted request resolving a circuit solver
for a problem with no circuit. A second system pack with an entry point of
identical shape already exists in this repository, and its entry point has no
solver seam at all.

Nothing was broken, because there is one execution. The **shape** was, and the
fix is a relocation rather than a new abstraction: no registry, no planner, no
capability system, no discovery. An execution owns the enumeration of the ways
it can be executed, because it is the only thing that knows what one means.

The execution-module protocol
-----------------------------
Three published names, and no base class::

    EXECUTION_ID: str
    PROFILES:     Mapping[str, Callable[[], Any]]   # closed, literal
    prepare(inputs, coupling, profile) -> PreparedExecution
    request_fragment() -> Mapping[str, Any]         # its half of the schema
"""

from __future__ import annotations

from typing import Any, Mapping

from .executions import electrothermal_series

__all__ = ["EXECUTIONS", "execution_identities", "profile_names"]

#: identity -> the module that parses and runs it. One entry in v0.
EXECUTIONS: Mapping[str, Any] = {
    electrothermal_series.EXECUTION_ID: electrothermal_series,
}


def execution_identities() -> frozenset[str]:
    return frozenset(EXECUTIONS)


def profile_names(execution: str) -> frozenset[str]:
    """The profiles ONE execution exposes. There is no platform-wide set."""
    return frozenset(EXECUTIONS[execution].PROFILES)
