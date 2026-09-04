"""``POST /v0/run`` — the entire HTTP surface.

One route. Every candidate endpoint had to justify itself and two did not:

``POST /v0/validate``
    Deleted. ``FixedPointCouplingPlan.unsupplied()`` is documented *"Reported,
    never refused"*, and ``check_against`` cannot check sources that are result
    metrics because they do not exist until a solve has produced them. A
    ``/validate`` returning *OK* would therefore assert admissibility the
    records cannot establish, for a request that may still fail mid-iteration —
    ``NOT_RUN`` reported as ``PASS``, at the API layer. Adding it later is
    additive; publishing a promise Crafty cannot keep is not.

``GET /v0/capabilities`` / ``GET /v0/profiles``
    Deleted. No aggregated registry and no planner exist, so a capabilities
    surface would publish discovery no caller can act on, and building the
    aggregation would put a list of domain names into a would-be-universal
    layer. ``/profiles`` survived that argument and died to a smaller one: a
    refusal for an unknown execution or profile already **names the admissible
    set**, so a second surface restating it carries no independent meaning.

Not present, and not by oversight: authentication, users, organizations,
billing, projects, databases, job queues, WebSocket, uploads, dashboards, rate
limiting, orchestration and async workers.

The status line is not a scientific verdict
-------------------------------------------
This is the one rule this module exists to hold. A valid request that reaches
its iteration limit without converging is **200 OK** with
``coupling.outcome = "iteration_limit_reached"``. It is not a 500. The status
line reports whether HTTP carried the exchange; the payload reports what the
science did. Mapping the second onto the first would destroy a distinction
`ET-VERTICAL` spent a milestone measuring — fifty iterations, every sub-solve
reporting success, coupling convergence false.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from engcore.application import decode_failure, handle
from engcore.application.contract import MAX_REQUEST_BYTES, RefusalCode

__all__ = ["STATUS_FOR_CODE", "build_server", "main"]

RUN_PATH = "/v0/run"

#: Refusal code -> HTTP status. A literal, total mapping, keyed on the
#: enumeration and never on message text.
#:
#: Note what is absent: there is no entry for a non-convergent run, because a
#: non-convergent run is not a refusal. It is an execution, and it is 200.
STATUS_FOR_CODE: dict[str, int] = {
    RefusalCode.MALFORMED_REQUEST.value: 400,
    RefusalCode.UNSUPPORTED_SCHEMA_VERSION.value: 400,
    RefusalCode.UNKNOWN_EXECUTION.value: 400,
    RefusalCode.UNKNOWN_EXECUTION_PROFILE.value: 400,
    # 422: the document was understood and the science was refused. Separating
    # this from 400 is the only place this module encodes anything about what
    # a refusal means, and it encodes only "the request parsed".
    RefusalCode.SCIENTIFIC_ADMISSION_REFUSED.value: 422,
    # 502: an upstream this server depends on failed. Deliberately NOT 4xx —
    # the caller did nothing wrong — and deliberately not 200, because nothing
    # scientific was produced.
    RefusalCode.PROVIDER_EXECUTION_FAILED.value: 502,
    RefusalCode.SUBSOLVER_EXECUTION_FAILED.value: 500,
    RefusalCode.UNCLASSIFIED_INTERNAL_FAILURE.value: 500,
}


def _status_for(payload: dict[str, Any]) -> int:
    refusal = payload.get("refusal")
    if refusal is None:
        return 200
    # A code this mapping does not know is a defect in this file, not in the
    # boundary, and must not be reported as a success.
    return STATUS_FOR_CODE.get(refusal.get("code"), 500)


class _Handler(BaseHTTPRequestHandler):
    server_version = "crafty-http/0"
    #: Fixed, so the response bytes do not vary with the wire protocol the
    #: client happened to speak.
    protocol_version = "HTTP/1.1"

    def log_message(self, *args: Any) -> None:  # pragma: no cover - noise
        return

    def _write(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        self._write(
            405 if self.path == RUN_PATH else 404,
            decode_failure(
                f"{RUN_PATH} accepts POST only"
                if self.path == RUN_PATH
                else f"no route {self.path!r}; this server exposes "
                f"POST {RUN_PATH} and nothing else"
            ),
        )

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path != RUN_PATH:
            self._write(
                404,
                decode_failure(
                    f"no route {self.path!r}; this server exposes "
                    f"POST {RUN_PATH} and nothing else"
                ),
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0:
            self._write(400, decode_failure("unreadable Content-Length"))
            return
        if length > MAX_REQUEST_BYTES:
            self._write(
                413,
                decode_failure(
                    f"request body of {length} bytes exceeds the "
                    f"{MAX_REQUEST_BYTES}-byte limit"
                ),
            )
            return

        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            # The boundary owns the shape of a refusal; this module owns only
            # the status line. Hand-building a payload here would be the first
            # duplicated piece of the external contract.
            self._write(400, decode_failure(f"body is not valid JSON: {exc}"))
            return

        response = handle(payload)
        self._write(_status_for(response), response)


def build_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """A real socket server. Port 0 asks the OS for a free port."""
    return ThreadingHTTPServer((host, port), _Handler)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - entry point
    parser = argparse.ArgumentParser(description="Crafty HTTP v0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    server = build_server(args.host, args.port)
    # The bound port, on one line, so a supervisor need not guess it.
    print(server.server_address[1], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    sys.exit(main())
