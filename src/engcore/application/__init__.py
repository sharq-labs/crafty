"""The Crafty **application layer** — the one boundary external callers reach.

`API-MCP-V0`. This package occupies the top box of the dependency map that
``docs/scientific-core/README.md`` and the architecture synthesis have named
since before any of this existed and which had, until now, **zero occupants**:

.. code-block:: text

    Product API / MCP / UI / LLM adapters        <- crafty_http, crafty_mcp
    ------------------------------------------
    Platform / application layer                 <- THIS PACKAGE
    ------------------------------------------
    System packs / domain packs / coupling
    ------------------------------------------
    Universal Scientific Core

It is **not a new layer, and not a second scientific architecture.** It owns no
physics, no equation, no numerical method, no convergence rule, no validity
rule, no tolerance, and no unit conversion other than restating a caller's
value in the unit the receiving declaration already declares. Everything
scientific happens where it already happened; this package translates a
versioned external document into the existing typed declarations, calls the
existing entry point, and projects the record that comes back.

What it deliberately is not
---------------------------
No job platform, no scheduler, no queue, no session, no persistence, no
registry, no planner, no capability selector, no provider framework, no
plugin system, no async runtime, and no centralized ``admit()`` gate.

The last one is the load-bearing absence. Admission in Crafty is **distributed**
— it lives in the declaration validators, in
``FixedPointCouplingPlan.check_against`` and in ``run_fixed_point``'s own
guards, each where the knowledge is. A single gate here would duplicate every
one of those refusals in a layer that does not know the science, which is
exactly the second architecture this milestone's null hypothesis predicts.
What this package does instead is **prove the ordering**: every one of those
refusals fires before any executor is called, measured with spies rather than
asserted.

Transport independence
----------------------
Nothing here imports a socket, an HTTP library, an MCP SDK, a server, a
framework or a serializer beyond ``json``-compatible primitives.
:func:`handle` takes a mapping and returns a mapping. Direct Python callers
call it directly — the direct consumer **is** the service, not a third adapter
— and each transport adds framing only.
"""

from __future__ import annotations

from .catalog import (
    EXECUTIONS,
    PROFILES,
    execution_identities,
    profile_names,
)
from .contract import (
    REQUEST_SCHEMA,
    RESPONSE_SCHEMA,
    ExecutionRequest,
    ExternalRequestRefused,
    RefusalCode,
    parse_request,
    project_run,
)
from .service import decode_failure, execute, handle

__all__ = [
    "EXECUTIONS",
    "ExecutionRequest",
    "ExternalRequestRefused",
    "PROFILES",
    "REQUEST_SCHEMA",
    "RESPONSE_SCHEMA",
    "RefusalCode",
    "decode_failure",
    "execute",
    "execution_identities",
    "handle",
    "parse_request",
    "profile_names",
    "project_run",
]
