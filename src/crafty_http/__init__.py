"""HTTP framing for the Crafty application boundary. **Framing only.**

Deliberately outside ``engcore``. `API-MCP-V0`'s non-negotiable is that no
transport library type may become a Crafty scientific contract, and the
cheapest way to make that structurally true rather than promised is for
``engcore`` to have no transport package inside it at all.

Deliberately **stdlib only** — ``http.server`` and ``json``. No FastAPI, no
Starlette, no Flask, no Pydantic, no uvicorn. Two reasons, and neither is
minimalism for its own sake:

* it makes "no transport type crossed the boundary" auditable by reading two
  short files rather than by trusting a framework's serialization rules;
* a framework's request/response model is the exact thing that tends to become
  the de-facto contract, and here there is none to become one.

This package contains **no scientific logic**: it decodes a body, calls
``engcore.application.handle``, maps a refusal *code* to a status line through
a literal dict, and writes the boundary's payload back unmodified. It does not
construct a payload, does not interpret a verdict, and defines no error type.
"""

from __future__ import annotations

from .server import STATUS_FOR_CODE, build_server, main

__all__ = ["STATUS_FOR_CODE", "build_server", "main"]
