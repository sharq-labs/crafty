"""One tool, ``crafty_run``, over newline-delimited JSON-RPC 2.0 on stdio.

``crafty_validate`` and ``crafty_capabilities`` were both considered and are
both **deleted**, for the same reasons their HTTP counterparts were: a validate
tool would report ``NOT_RUN`` as ``PASS`` — the plan's own ``unsupplied()`` is
documented *"Reported, never refused"* — and a capabilities tool would restate a
set that an unknown-name refusal already names. Only demonstrated tools are
kept.

The deliberate asymmetry with HTTP, recorded rather than smoothed over
--------------------------------------------------------------------
A **scientific** refusal — a malformed request, an unsupported schema version,
an unknown execution, an inadmissible declaration, a provider failure — comes
back as a *successful tool call whose structured content reports the refusal*
(``isError`` false). An agent must be able to read why Crafty refused; an opaque
error invites a blind retry, and a retry loop against a deterministic refusal is
the failure mode this framing exists to prevent.

A malformed **JSON-RPC envelope** — an unparsable frame, an unknown method — is
a JSON-RPC error. That is transport, and it carries no scientific meaning.

HTTP maps the same refusals onto 4xx/5xx status codes. So the two transports
genuinely disagree about *framing* while carrying the **identical boundary
payload**. That is the point rather than a defect: transport status is not
scientific truth, and this milestone's differential compares the payload and
never the framing.

What this module may not do, and structurally cannot
----------------------------------------------------
It does not interpret validity, does not compute or adjust convergence, does
not select a solver, does not build a command, and does not touch a unit. It
decodes a frame, calls ``engcore.application.handle``, and encodes what comes
back. The tool's ``inputSchema`` is not written here either: it is derived from
the same constants the validator uses, so the published contract cannot drift
from the enforced one.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping, TextIO

from engcore.application import handle
from engcore.application.describe import request_json_schema

__all__ = ["PROTOCOL_VERSION", "TOOLS", "main", "respond", "serve"]

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "crafty-mcp", "version": "0"}

RUN_TOOL = "crafty_run"

_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602


def _tools() -> list[dict[str, Any]]:
    return [
        {
            "name": RUN_TOOL,
            "title": "Run a Crafty scientific execution",
            "description": (
                "Execute one named Crafty scientific execution and return its "
                "outputs, coupling outcome, per-participant numerical "
                "convergence and validation verdicts, and provenance.\n\n"
                "Crafty decides admission, execution, convergence and "
                "validity. This tool reports what Crafty decided; it never "
                "certifies any of them, and neither may the agent calling it. "
                "A run that reaches its iteration budget without converging "
                "is a SUCCESSFUL execution reporting "
                "coupling.outcome = iteration_limit_reached — it is not an "
                "error and must not be retried as one.\n\n"
                "The arguments are exactly a crafty_execution_request/1 "
                "document. Unknown fields are refused, not ignored."
            ),
            "inputSchema": request_json_schema(),
        }
    ]


#: Evaluated once at import, so ``tools/list`` cannot answer differently
#: between two calls in one session.
TOOLS: list[dict[str, Any]] = _tools()


def _result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _tool_result(payload: dict[str, Any]) -> dict[str, Any]:
    """One boundary payload, in MCP's two carriers, byte-identical in both.

    ``structuredContent`` is the payload itself. ``content`` carries the same
    object serialized deterministically, for hosts that read only text. They
    are produced from one object, so they cannot disagree.
    """
    text = json.dumps(payload, sort_keys=True, indent=2)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        # A refused request is still a completed tool call. The refusal is in
        # the payload, where an agent can read it.
        "isError": False,
    }


def respond(message: Any) -> dict[str, Any] | None:
    """One decoded JSON-RPC message in, one response out (``None`` = notify)."""
    if not isinstance(message, Mapping):
        return _error(None, _INVALID_REQUEST, "message must be a JSON object")

    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return _error(request_id, _INVALID_REQUEST, "missing method")
    # A notification carries no id and expects no reply.
    is_notification = "id" not in message

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        }
        return None if is_notification else _result(request_id, result)

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})

    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, Mapping):
            return _error(request_id, _INVALID_PARAMS, "params must be an object")
        name = params.get("name")
        if name != RUN_TOOL:
            # Unknown *tool* is a protocol-level fact, not a scientific one.
            return _error(
                request_id,
                _INVALID_PARAMS,
                f"unknown tool {name!r}; this server exposes {RUN_TOOL!r}",
            )
        arguments = params.get("arguments", {})
        # Straight through. No normalization, no defaulting, no repair — the
        # boundary owns every one of those decisions, and a transport that made
        # one would be the first place the two transports could disagree about
        # science.
        return _result(request_id, _tool_result(handle(arguments)))

    return _error(request_id, _METHOD_NOT_FOUND, f"unknown method {method!r}")


def serve(stdin: TextIO, stdout: TextIO) -> None:
    """Newline-delimited JSON-RPC. One message per line, one response per line."""
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            response: dict[str, Any] | None = _error(
                None, _PARSE_ERROR, f"invalid JSON: {exc}"
            )
        else:
            response = respond(message)
        if response is not None:
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()


def main() -> int:  # pragma: no cover - entry point
    serve(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
