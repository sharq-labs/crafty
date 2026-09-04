"""The two closed enumerations. **Literal dicts, no fallthrough, no defaults.**

This module is the whole of Crafty's externally reachable execution surface. If
a name is not a key here, no external caller can reach whatever it names —
there is no prefix match, no normalization, no alias table, no case folding, no
environment override, and no default-on-miss. A miss is a refusal.

Why an execution *profile* is exposed at all
--------------------------------------------
The alternative was to let Crafty pick the concrete solver from scientific and
capability constraints. That is the right long-term answer and it is **not
available**: no aggregated registry and no planner exist — registries are
per-domain factory functions and the Scientific Core README states plainly that
no global singleton exists — so choosing it in v0 would mean building one, which
is a second architecture.

The other alternative was to expose no selection at all. That was rejected on a
lesson this platform paid for once already: *a check whose only effect is a
field nothing consults is not a guard.* If the only rejectable profile name
mapped to nothing that could ever spawn a process, then "an unknown profile is
refused before any process launch" would be a restatement of ``KeyError``, not a
security claim. One of the two profiles here genuinely reaches
``subprocess.run``, which is what makes the refusal load-bearing.

Why the second profile is named for the provider
------------------------------------------------
Because ``ProvenanceRecord`` already reports the concrete solver truthfully —
``solver_id`` and ``backend`` both name it — so an opaque request-side name that
provenance immediately de-anonymizes would be obfuscation, not encapsulation.
The name is a **Crafty identity drawn from a closed enumeration**; it is never a
path, an argv element, a command, or an argument to one. What is *not* exposed
is every provider internal: the argv, the timeout, the netlist, the analysis
statement, the node naming and the version probe are all unreachable from a
request.

Import discipline
-----------------
The external-provider module is imported **lazily, inside the resolver**. A
deployment that only ever serves the native profile therefore never imports it
— asserted by test, because "the native path does not touch the provider" is a
claim worth being able to check rather than to assert.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from ..systems.electrothermal import CircuitSolver, native_circuit_solver
from .executions import electrothermal_series

__all__ = [
    "EXECUTIONS",
    "NATIVE_PROFILE",
    "PROFILES",
    "PROVIDER_PROFILE",
    "execution_identities",
    "profile_names",
    "resolve_circuit_solver",
]

NATIVE_PROFILE = "native"
PROVIDER_PROFILE = "ngspice"


def _native() -> CircuitSolver:
    """Crafty's own MNA solve. No process, no provider, no import."""
    return native_circuit_solver


def _external_provider() -> CircuitSolver:
    """The real external provider, in the electrical slot of the coupled loop.

    Constructed here and **only** from module-level identities. Nothing a
    caller sent reaches this function; it takes no argument at all. The
    provider's own discovery (``PATH``, then the one other supported route) and
    its optional environment override are process configuration set before the
    server starts — deployment facts, never request fields.
    """
    from ..domains.electrical import ngspice as provider

    solver = provider.NgspiceDCSolver()

    def solve(circuit, run_id: str):
        return provider.solve_circuit_with_ngspice(
            circuit, run_id=run_id, solver=solver
        )

    return solve


#: name -> zero-argument resolver. A resolver takes **no** caller input, which
#: is the structural reason no external string can influence how a provider is
#: invoked: there is nowhere for it to go.
PROFILES: Mapping[str, Callable[[], CircuitSolver]] = {
    NATIVE_PROFILE: _native,
    PROVIDER_PROFILE: _external_provider,
}

#: identity -> the module that parses and runs it. One entry in v0.
EXECUTIONS: Mapping[str, Any] = {
    electrothermal_series.EXECUTION_ID: electrothermal_series,
}


def execution_identities() -> frozenset[str]:
    return frozenset(EXECUTIONS)


def profile_names() -> frozenset[str]:
    return frozenset(PROFILES)


def resolve_circuit_solver(profile: str) -> CircuitSolver:
    """Closed-mapping lookup. Never reached for a name ``parse_request`` refused."""
    return PROFILES[profile]()
