"""MCP framing for the Crafty application boundary. **Framing only.**

Deliberately outside ``engcore``, and deliberately **stdlib only** — a
newline-delimited JSON-RPC 2.0 loop over ``stdin``/``stdout``. The ``mcp`` SDK
is not installed and not imported. The protocol's own churn is the argument:
JSON-RPC batching was added in one 2025 revision and removed in the next, and
three server features were deprecated in a later release candidate. A moving
target is exactly the sort of type that must never end up describing a Crafty
scientific record.

The boundary this file exists to hold
-------------------------------------
.. code-block:: text

    an LLM PROPOSES a request
        -> Crafty's deterministic admission decides whether it is admissible
        -> Crafty's deterministic execution produces the numbers
        -> Crafty's own convergence / validation / provenance verdicts
        -> the agent may only EXPLAIN them

The tool handler contains no scientific logic. It cannot interpret validity,
alter a convergence verdict, choose a solver outside the closed enumeration,
select a command, or construct provider semantics — **because none of those is
expressible in the request**, not because the handler declines to do them. An
LLM may never certify convergence, validity, evidence admission, or scientific
truth, and there is no field through which it could try.
"""

from __future__ import annotations

from .server import PROTOCOL_VERSION, TOOLS, main, respond, serve

__all__ = ["PROTOCOL_VERSION", "TOOLS", "main", "respond", "serve"]
