"""API / MCP v0 — the two real transports, and the three-way differential.

Preregistration: ``docs/api-mcp-v0-prereg.md`` (commit 3f2e6dd).

**Nothing here is an in-process wrapper.** HTTP crosses a real TCP socket to a
separate OS process; MCP crosses a real pipe to a separate OS process, speaking
newline-delimited JSON-RPC 2.0 on its stdin and stdout. The provider tests
launch real ``ngspice``. That is why this module is labelled ``expensive`` and
its sibling ``test_api_mcp_v0.py`` is not.

What that does and does not earn, stated here so it cannot be overstated later
--------------------------------------------------------------------------------
Two separate processes and two different wire protocols make the boundary
genuinely reusable across a process boundary, which is more than a function
called twice. It is **not** ``L2 DIFFERENTIATED``: two transports written by
one author on one day against one interface are exactly what master context
§54.1 excludes from "materially different consumers". The preregistration
capped this at ``L1`` before any of it ran.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

import pytest

from api_v0_case import (
    CASE_A_ITERATIONS,
    CASE_A_POWER_W,
    CASE_A_RESISTANCE_OHM,
    CASE_A_TEMPERATURE_K,
    RESPONSE_SCHEMA,
    canonical_request,
    output,
)
from engcore.application import handle

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Preregistered acceptance tolerance for the differential (§12.1). The
#: *measured* value is reported separately and is expected to be exactly 0.0.
DIFFERENTIAL_RELATIVE_TOLERANCE = 1e-12

_TIMEOUT = 120.0


def _child_env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    env.update(extra)
    return env


# =====================================================================
# HTTP — a real socket, a real process
# =====================================================================

class _HttpServer:
    def __init__(self, **env: str) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "crafty_http", "--host", "127.0.0.1", "--port", "0"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(REPO_ROOT), env=_child_env(**env),
        )
        line = self.process.stdout.readline().strip()
        if not line:
            raise AssertionError(
                f"server did not report a port: {self.process.stderr.read()}"
            )
        self.port = int(line)

    @property
    def pid(self) -> int:
        return self.process.pid

    def post(self, payload, path: str = "/v0/run") -> tuple[int, dict]:
        return self.send(json.dumps(payload).encode("utf-8"), path=path)

    def send(
        self, body: bytes, *, path: str = "/v0/run", method: str = "POST"
    ) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=body,
            headers={"Content-Type": "application/json"}, method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def close(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            self.process.kill()


@pytest.fixture(scope="module")
def http():
    server = _HttpServer()
    yield server
    server.close()


# =====================================================================
# MCP — a real stdio pipe, a real process
# =====================================================================

class _McpServer:
    def __init__(self, **env: str) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "crafty_mcp"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=str(REPO_ROOT), env=_child_env(**env),
        )
        self._id = 0

    @property
    def pid(self) -> int:
        return self.process.pid

    def rpc(self, method: str, params=None, *, raw: str | None = None) -> dict:
        if raw is not None:
            self.process.stdin.write(raw + "\n")
        else:
            self._id += 1
            message = {"jsonrpc": "2.0", "id": self._id, "method": method}
            if params is not None:
                message["params"] = params
            self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:  # pragma: no cover - defensive
            raise AssertionError(f"server died: {self.process.stderr.read()}")
        return json.loads(line)

    def call(self, payload) -> dict:
        return self.rpc(
            "tools/call", {"name": "crafty_run", "arguments": payload}
        )["result"]

    def close(self) -> None:
        try:
            self.process.stdin.close()
        except OSError:  # pragma: no cover - defensive
            pass
        self.process.terminate()
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            self.process.kill()


@pytest.fixture(scope="module")
def mcp():
    server = _McpServer()
    server.rpc("initialize", {})
    yield server
    server.close()


# =====================================================================
# The three paths really are three processes
# =====================================================================

def test_the_transports_are_separate_operating_system_processes(http, mcp):
    """The claim the whole differential rests on, asserted rather than assumed.

    If these were in-process wrappers, "three transports agree" would collapse
    to "one function returned the same value three times" and the milestone
    would have measured nothing.
    """
    assert http.pid != os.getpid()
    assert mcp.pid != os.getpid()
    assert http.pid != mcp.pid
    assert http.process.poll() is None
    assert mcp.process.poll() is None
    # And the socket is real: something is listening on a port this process
    # never bound.
    status, _ = http.post(canonical_request())
    assert status == 200
    assert isinstance(http.port, int) and http.port > 0


# =====================================================================
# CASE A over each transport
# =====================================================================

@pytest.fixture(scope="module")
def direct_a() -> dict:
    return handle(canonical_request())


@pytest.fixture(scope="module")
def http_a(http) -> tuple[int, dict]:
    return http.post(canonical_request())


@pytest.fixture(scope="module")
def mcp_a(mcp) -> dict:
    return mcp.call(canonical_request())


def test_a_direct_python_executes_case_a(direct_a):
    assert direct_a["status"] == "executed"
    assert direct_a["result"]["coupling"]["iterations_run"] == CASE_A_ITERATIONS
    assert output(direct_a, "final_temperature")["value"]["value"] == pytest.approx(
        CASE_A_TEMPERATURE_K, abs=1e-6
    )


def test_a2_http_executes_case_a_over_a_socket(http_a):
    status, payload = http_a
    assert status == 200
    assert payload["schema"] == RESPONSE_SCHEMA
    assert payload["status"] == "executed"
    assert output(payload, "resistance")["value"]["value"] == pytest.approx(
        CASE_A_RESISTANCE_OHM, abs=1e-6
    )


def test_a3_mcp_executes_case_a_over_stdio(mcp_a):
    assert mcp_a["isError"] is False
    payload = mcp_a["structuredContent"]
    assert payload["status"] == "executed"
    assert output(payload, "resistor_power:R1")["value"]["value"] == pytest.approx(
        CASE_A_POWER_W, abs=1e-6
    )
    # The text carrier and the structured carrier are produced from one object
    # and therefore cannot disagree.
    assert json.loads(mcp_a["content"][0]["text"]) == payload


# =====================================================================
# THE DIFFERENTIAL — the milestone's central measurement
# =====================================================================

def _relative(a: float, b: float) -> float:
    scale = max(abs(a), abs(b))
    return abs(a - b) if scale == 0.0 else abs(a - b) / scale


def test_differential_the_three_paths_agree_on_every_scientific_quantity(
    direct_a, http_a, mcp_a
):
    """§12(1). Preregistered acceptance ``rel <= 1e-12``; measured separately."""
    _, http_payload = http_a
    paths = {
        "direct": direct_a,
        "http": http_payload,
        "mcp": mcp_a["structuredContent"],
    }
    keyed = {
        name: {
            (entry["problem_id"], entry["quantity"]): entry["value"]
            for entry in payload["result"]["outputs"]
        }
        for name, payload in paths.items()
    }
    assert keyed["direct"].keys() == keyed["http"].keys() == keyed["mcp"].keys()
    assert len(keyed["direct"]) == 13

    worst = 0.0
    for key, reference in keyed["direct"].items():
        for name in ("http", "mcp"):
            other = keyed[name][key]
            # Units are compared as strings, not converted. A transport that
            # silently restated a value in a different unit would agree
            # numerically only by accident.
            assert other["unit"] == reference["unit"], (name, key)
            worst = max(worst, _relative(other["value"], reference["value"]))
    assert worst <= DIFFERENTIAL_RELATIVE_TOLERANCE
    # The measured value, reported rather than merely bounded.
    assert worst == 0.0


def test_differential_the_three_paths_agree_on_the_coupling_outcome(
    direct_a, http_a, mcp_a
):
    """§12(2)."""
    _, http_payload = http_a
    couplings = [
        payload["result"]["coupling"]
        for payload in (direct_a, http_payload, mcp_a["structuredContent"])
    ]
    for coupling in couplings[1:]:
        assert coupling == couplings[0]
    assert couplings[0]["outcome"] == "criterion_met"


def test_differential_the_three_paths_agree_on_every_participant_verdict(
    direct_a, http_a, mcp_a
):
    """§12(3) and §12(4) — validation status, attained levels, convergence."""
    _, http_payload = http_a
    sets = [
        payload["result"]["participants"]
        for payload in (direct_a, http_payload, mcp_a["structuredContent"])
    ]
    for participants in sets[1:]:
        assert participants == sets[0]
    assert {p["validation_status"] for p in sets[0]} == {"pass"}
    assert {p["numerical_convergence"] for p in sets[0]} == {
        "converged", "not_applicable",
    }


def test_differential_the_three_paths_agree_on_provenance_identities(
    direct_a, http_a, mcp_a
):
    """§12(5). Not merely present in all three — the same identities."""
    _, http_payload = http_a

    def identities(payload):
        return {
            (
                b["model"]["model_id"], b["model"]["version"],
                (b["realization"] or {}).get("realization_id"),
                b["solver"]["solver_id"], b["solver"]["version"],
                b["solver"]["backend"],
            )
            for b in payload["result"]["provenance"]["bindings"]
        }

    reference = identities(direct_a)
    assert reference
    assert identities(http_payload) == reference
    assert identities(mcp_a["structuredContent"]) == reference


def test_differential_the_whole_payload_is_structurally_identical(
    direct_a, http_a, mcp_a
):
    """§12(7). A **measurement**, deliberately not a contract clause.

    Byte-equality is not promised by ``crafty_execution_response/1`` and no
    consumer may rely on it. It is asserted because it is currently achievable
    and an unexplained divergence would be worth knowing about.
    """
    _, http_payload = http_a
    mcp_payload = mcp_a["structuredContent"]
    assert http_payload == direct_a
    assert mcp_payload == direct_a
    assert (
        json.dumps(http_payload, sort_keys=True)
        == json.dumps(mcp_payload, sort_keys=True)
        == json.dumps(direct_a, sort_keys=True)
    )


def test_differential_holds_for_the_non_convergent_case_too(http, mcp):
    """One agreement on a converged run would not show the transports agree
    about *disagreement*. The budget-exhausted run is the one where a transport
    that mapped science onto status would diverge."""
    request = canonical_request()
    request["coupling"]["max_iterations"] = 2
    request["run_id"] = "api-v0-case-b"

    direct = handle(request)
    status, over_http = http.post(request)
    over_mcp = mcp.call(request)

    assert direct == over_http == over_mcp["structuredContent"]
    assert direct["result"]["coupling"]["outcome"] == "iteration_limit_reached"
    # HTTP says 200 and MCP says isError=False. Neither claims a scientific
    # verdict, and the payload — which does — is identical.
    assert status == 200
    assert over_mcp["isError"] is False


def test_differential_holds_for_a_refusal(http, mcp):
    """The framings differ by design; the boundary payload does not."""
    request = canonical_request()
    request["inputs"]["stages"][0]["reference_resistance"]["value"] = -10.0

    direct = handle(request)
    status, over_http = http.post(request)
    over_mcp = mcp.call(request)

    assert direct == over_http == over_mcp["structuredContent"]
    assert direct["refusal"]["code"] == "scientific_admission_refused"
    # The preregistered asymmetry, exhibited: HTTP 422, MCP a completed call.
    assert status == 422
    assert over_mcp["isError"] is False


# =====================================================================
# The transports' own framing — and its limits
# =====================================================================

def test_http_status_never_claims_a_scientific_verdict(http):
    """One request per taxonomy row that HTTP can reach without a provider."""
    expected = {
        200: canonical_request(),
        400: canonical_request(schema="crafty_execution_request/2"),
        422: canonical_request(),
    }
    expected[422]["inputs"]["stages"][0]["reference_resistance"]["value"] = -1.0

    for status, request in expected.items():
        got, payload = http.post(request)
        assert got == status, (status, payload.get("refusal"))

    # And the row that matters most: a run that did not converge is 200.
    budgeted = canonical_request()
    budgeted["coupling"]["max_iterations"] = 1
    status, payload = http.post(budgeted)
    assert status == 200
    assert payload["result"]["coupling"]["criterion_met"] is False


def test_http_refuses_everything_that_is_not_the_one_route(http):
    for path in ("/", "/v0/validate", "/v0/capabilities", "/v0/profiles"):
        assert http.send(b"", path=path, method="GET")[0] == 404, path
    assert http.send(b"", path="/v0/run", method="GET")[0] == 405
    assert http.send(b"{}", path="/v0/run/extra")[0] == 404


def test_a_routing_fault_does_not_wear_the_scientific_response_schema(http, mcp):
    """`architecture-falsifier` C-3, closed.

    "There is no route /healthz" is a transport fact. An earlier form answered
    it with a full ``crafty_execution_response/1`` carrying
    ``status: "refused"`` and a scientific taxonomy code — an UNDECLARED
    divergence from MCP, which answers an unknown method with a JSON-RPC error
    and no response envelope. The two transports now agree on what kind of
    object a protocol fault is.
    """
    for path, expected in (("/healthz", 404), ("/v0/run", 405)):
        status, body = http.send(b"", path=path, method="GET")
        assert status == expected
        assert set(body) == {"error"}
        assert "schema" not in body and "status" not in body
        assert "refusal" not in body

    unknown = mcp.rpc("healthz", {})
    assert "error" in unknown and "result" not in unknown


def test_http_refuses_a_body_that_is_not_json_or_is_too_large(http):
    status, payload = http.send(b"{not json at all")
    assert status == 400
    assert payload["refusal"]["code"] == "malformed_request"
    assert payload["result"] is None

    status, payload = http.send(b"[]")
    assert status == 400

    status, payload = http.send(b"x" * 300_000)
    assert status == 413
    assert payload["result"] is None


def test_mcp_publishes_exactly_one_tool_and_its_enforced_schema(mcp):
    tools = mcp.rpc("tools/list", {})["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["crafty_run"]
    schema = tools[0]["inputSchema"]
    assert schema["properties"]["schema"]["const"] == "crafty_execution_request/1"
    assert schema["properties"]["execution_profile"]["enum"] == ["native", "ngspice"]
    assert schema["additionalProperties"] is False
    # The description must tell an agent that a non-convergent run is not an
    # error, because an agent that retried one would loop forever.
    assert "iteration_limit_reached" in tools[0]["description"]


def test_mcp_distinguishes_a_protocol_error_from_a_scientific_refusal(mcp):
    """The one place the two transports were free to disagree, exhibited."""
    assert mcp.rpc("no/such/method", {})["error"]["code"] == -32601
    assert mcp.rpc(
        "tools/call", {"name": "crafty_validate", "arguments": {}}
    )["error"]["code"] == -32602
    assert mcp.rpc("tools/call", {"name": "crafty_run"}) is not None
    assert "error" in mcp.rpc("", raw="{not json")
    assert mcp.rpc("", raw="{not json")["error"]["code"] == -32700

    # A scientific refusal is a completed call, not an error.
    result = mcp.call(canonical_request(schema="nope"))
    assert result["isError"] is False
    assert result["structuredContent"]["refusal"]["code"] == (
        "unsupported_schema_version"
    )


def test_mcp_passes_arguments_through_without_repair(mcp):
    """A transport that normalized, defaulted or repaired an argument would be
    the first place the two transports could disagree about science."""
    for payload in ({}, [], "run it", 7, None):
        result = mcp.call(payload)
        assert result["isError"] is False
        assert result["structuredContent"]["status"] == "refused"
        assert result["structuredContent"]["result"] is None


# =====================================================================
# The real external provider, across a real process boundary
# =====================================================================

def _ngspice_present() -> bool:
    import shutil

    return shutil.which("ngspice") is not None


requires_ngspice = pytest.mark.skipif(
    not _ngspice_present(),
    reason="the external provider is not installed on this machine",
)


@requires_ngspice
def test_provider_profile_executes_real_ngspice_through_http(http):
    """The execution profile is load-bearing: this one genuinely spawns a
    process, which is what makes "an unknown profile is refused before any
    process launch" a security claim rather than a restatement of KeyError."""
    request = canonical_request(execution_profile="ngspice", run_id="api-v0-ngspice")
    status, payload = http.post(request)
    assert status == 200
    assert payload["status"] == "executed"
    assert payload["execution_profile"] == "ngspice"

    backends = {
        p["solver"]["backend"] for p in payload["result"]["participants"]
    }
    assert "ngspice" in backends

    native = canonical_request(run_id="api-v0-ngspice")
    _, native_payload = http.post(native)
    # Same science, different arithmetic. The provider identity is reported in
    # provenance and changes nothing about what the numbers mean.
    difference = _relative(
        output(payload, "final_temperature")["value"]["value"],
        output(native_payload, "final_temperature")["value"]["value"],
    )
    assert difference < 1e-12
    assert (
        payload["result"]["coupling"]["outcome"]
        == native_payload["result"]["coupling"]["outcome"]
    )
    assert (
        payload["result"]["coupling"]["iterations_run"]
        == native_payload["result"]["coupling"]["iterations_run"]
    )


@pytest.fixture(scope="module")
def sentinel(tmp_path_factory) -> tuple[pathlib.Path, pathlib.Path]:
    """A stand-in provider that records every launch and then fails.

    This is how "no process was launched" is proven **across** a process
    boundary, where a monkeypatched spy cannot reach: the server's provider is
    pointed at this script, and the marker file is the evidence.
    """
    directory = tmp_path_factory.mktemp("provider-sentinel")
    marker = directory / "launched.log"
    script = directory / "sentinel_provider.py"
    script.write_text(
        "import pathlib, sys\n"
        f"pathlib.Path({str(marker)!r}).open('a').write(' '.join(sys.argv) + '\\n')\n"
        "sys.exit(1)\n",
        encoding="utf-8",
    )
    return script, marker


@pytest.fixture(scope="module")
def hostile_http(sentinel):
    script, _ = sentinel
    server = _HttpServer(
        CRAFTY_NGSPICE_ARGV=f"{sys.executable} {script}"
    )
    yield server
    server.close()


def test_nothing_a_request_can_say_launches_a_process_and_then_one_legitimately_does(
    hostile_http, sentinel
):
    """Two halves of one measurement, in one test so ordering cannot drift.

    First: every hostile and unknown execution-selection request is submitted
    over a real socket to a server whose provider is a launch recorder. The
    marker file must not exist. Second: one legitimate provider request is
    submitted, the marker must appear, and the failure must classify as a
    provider failure — never as invalidity and never as non-convergence.
    """
    _, marker = sentinel
    assert not marker.exists()

    hostile_profiles = [
        "/usr/bin/ngspice",
        "/bin/sh",
        f"; touch {marker}",
        f"$(touch {marker})",
        f"`{sys.executable} -c \"open({str(marker)!r},'w')\"`",
        "ngspice --version",
        "NGSPICE",
        "ngspice ",
        "../../usr/bin/ngspice",
        "native;ngspice",
        {"argv": [sys.executable, "-c", "print(1)"]},
        ["ngspice"],
        None,
        0,
    ]
    for profile in hostile_profiles:
        status, payload = hostile_http.post(
            canonical_request(execution_profile=profile)
        )
        assert payload["result"] is None, profile
        assert status == 400, (profile, payload["refusal"])
        assert payload["refusal"]["code"] in {
            "unknown_execution_profile", "malformed_request",
        }, profile

    # Unknown executions and unsupported versions must not reach it either.
    for mutation in (
        {"execution": "electrothermal.series_self_heating/2"},
        {"execution": "/usr/bin/ngspice"},
        {"schema": "crafty_execution_request/2"},
    ):
        status, payload = hostile_http.post(
            canonical_request(execution_profile="ngspice", **mutation)
        )
        assert payload["result"] is None, mutation
        assert status == 400, mutation

    # An inadmissible declaration with the provider profile selected: admission
    # must stop it before the provider is reached.
    bad = canonical_request(execution_profile="ngspice")
    bad["inputs"]["stages"][0]["reference_resistance"]["value"] = -10.0
    status, payload = hostile_http.post(bad)
    assert status == 422 and payload["result"] is None

    # THE REPRODUCED EXPLOIT, across a real socket, against the profile that
    # really launches a process. `component_id` was the field the first
    # in-process injection test mutated and could not judge; the sentinel here
    # can, because it records every launch.
    for identifier in (
        f"R1\n.control\nshell touch {marker}\n.endc",
        "R1\n.param x=1",
        "R1\r\n.end",
        "R1 R2",
        "/usr/bin/ngspice",
        "." * 80,
    ):
        hostile = canonical_request(execution_profile="ngspice")
        hostile["inputs"]["stages"][0]["component_id"] = identifier
        status, payload = hostile_http.post(hostile)
        assert status == 400, (identifier, payload.get("refusal"))
        assert payload["refusal"]["code"] == "malformed_request", identifier
        assert payload["result"] is None, identifier

    # And a hostile run_id, which reaches provenance AND result identity.
    hostile = canonical_request(execution_profile="ngspice", run_id="a\n.control")
    assert hostile_http.post(hostile)[0] == 400

    # THE MEASUREMENT: nothing above launched anything.
    assert not marker.exists(), marker.read_text(encoding="utf-8")

    # Now one legitimate request, and the recorder must fire.
    status, payload = hostile_http.post(
        canonical_request(execution_profile="ngspice", run_id="api-v0-provider-fail")
    )
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip()

    # A provider failure is not a scientific verdict of any kind.
    assert status == 502
    assert payload["status"] == "execution_failed"
    assert payload["refusal"]["code"] == "provider_execution_failed"
    assert payload["result"] is None
    text = json.dumps(payload)
    for forbidden in ("criterion_met", "outcome", "validation_status", "converged"):
        assert forbidden not in text, forbidden
    # And no provider output, path or argv escapes.
    for forbidden in ("sentinel_provider", str(sys.executable), "Traceback"):
        assert forbidden not in text, forbidden


def test_a_hostile_server_still_serves_the_native_profile_unaffected(hostile_http):
    """Provider misconfiguration must not degrade the native path. If it did,
    the profile enumeration would not be selecting an implementation, it would
    be selecting a deployment."""
    status, payload = hostile_http.post(canonical_request())
    assert status == 200
    assert payload["status"] == "executed"
    assert output(payload, "final_temperature")["value"]["value"] == pytest.approx(
        CASE_A_TEMPERATURE_K, abs=1e-6
    )
