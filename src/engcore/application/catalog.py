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
Five published names, and no base class::

    EXECUTION_ID: str
    PROFILES:     Mapping[str, Callable[[], Any]]   # closed, literal
    prepare(inputs, coupling, profile) -> object with .run(run_id) -> CoupledRun
    request_fragment() -> Mapping[str, Any]         # its half of the schema
    provider_failure_types() -> tuple[type[BaseException], ...]

The requirement inside ``prepare``'s return type is the load-bearing one and
an earlier form of this list omitted it: ``service.execute`` projects whatever
``run`` returns through ``project_run``, whose argument is a ``CoupledRun``. So
**every execution this deployment can expose is an iterative coupling**, and
``crafty_execution_response/1``'s ``result`` is coupling-shaped for that reason
— ``coupling.outcome``, ``coupling.iterate_changes`` and ``torn_endpoints`` are
properties of a torn fixed-point iteration, not of "a Crafty execution".

A single-solve execution therefore does **not** fit v0, and that is stated here
rather than discovered by whoever writes one. It requires
``crafty_execution_response/2``, which the response schema's exact-string
reading makes a loud, additive step. No result-shape abstraction is built for
it now: there is one execution, one shape, and no second consumer, and the
projection's independent identity is precisely what buys the escape hatch.
A sibling project had to break its public *configuration* format to repair a
conflation of this kind after publication; the cost of avoiding that here is
this paragraph.
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
