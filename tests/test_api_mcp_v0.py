"""API / MCP v0 — the boundary, its taxonomy, its refusals and its fitness.

Preregistration: ``docs/api-mcp-v0-prereg.md`` (commit 3f2e6dd), written and
committed before any implementation file existed.

Everything here runs **in this process**. The two real transports — HTTP over a
TCP socket and MCP over a stdio pipe, each in its own OS process — and the
three-way differential live in ``test_api_mcp_v0_transports.py``, which is
labelled ``expensive`` because it spawns processes and invokes real
``ngspice``.

What this module is trying to falsify
-------------------------------------
The milestone's null hypothesis, in two halves: that exposing Crafty externally
requires transport-specific scientific interpretation, or that the current
internal execution boundary is not a reusable application boundary. Most of the
tests below are attempts to show the second — a leak of provider internals, a
scientific decision that migrated into the application layer, a refusal that
fires too late, a field that silently changes an answer.
"""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import subprocess
import sys

import pytest

from api_v0_case import (
    CASE_A_ITERATIONS,
    CASE_A_POWER_W,
    CASE_A_RESISTANCE_OHM,
    CASE_A_TEMPERATURE_K,
    EXECUTION,
    RESPONSE_SCHEMA,
    canonical_request,
    output,
)
from engcore.application import RefusalCode, handle
from engcore.application import catalog, contract, describe, service
from engcore.application.executions import electrothermal_series as ets
from engcore.systems.electrothermal import coupled as etc

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
APPLICATION_DIR = REPO_ROOT / "src" / "engcore" / "application"
HTTP_DIR = REPO_ROOT / "src" / "crafty_http"
MCP_DIR = REPO_ROOT / "src" / "crafty_mcp"


def _diff(path: str) -> str:
    return subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", path],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
    ).stdout.strip()


def _sources(directory: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(directory.rglob("*.py"))
    ]


def _code_only(source: str) -> str:
    """Executable source with every docstring removed.

    Prose that *explains* an absence would otherwise trip a scan looking for
    that absence — the `COUPLING-PACK-RELOCATION` guards learned the same
    lesson. What is scanned here is what runs.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body[0] = ast.Pass()
    return ast.unparse(tree)


class _Spies:
    """Counts every way this milestone's request can reach executing science.

    Three independent chokepoints, patched together: the coupling loop itself,
    the pack's own native circuit solve, and ``subprocess.run``. A refusal that
    fired late would have to slip past all three to go unnoticed.
    """

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.loop = 0
        self.native_solve = 0
        self.process = 0

        def loop(*args, **kwargs):
            self.loop += 1
            raise AssertionError("the coupling loop must not have been entered")

        def solve(*args, **kwargs):
            self.native_solve += 1
            raise AssertionError("no circuit may be solved")

        def run(*args, **kwargs):
            self.process += 1
            raise AssertionError("no process may be launched")

        monkeypatch.setattr(etc, "run_fixed_point", loop)
        monkeypatch.setattr(etc, "solve_circuit", solve)
        monkeypatch.setattr(subprocess, "run", run)

    @property
    def total(self) -> int:
        return self.loop + self.native_solve + self.process


@pytest.fixture(scope="module")
def case_a() -> dict:
    return handle(canonical_request())


# =====================================================================
# CASE A — a valid convergent run, through the boundary
# =====================================================================

def test_a_the_canonical_request_reproduces_et_vertical_case_a(case_a):
    """The external path must not change a single number of the executed science."""
    assert case_a["schema"] == RESPONSE_SCHEMA
    assert case_a["status"] == "executed"
    assert case_a["execution"] == EXECUTION
    assert case_a["refusal"] is None

    coupling = case_a["result"]["coupling"]
    assert coupling["outcome"] == "criterion_met"
    assert coupling["criterion_met"] is True
    assert coupling["iterations_run"] == CASE_A_ITERATIONS

    assert output(case_a, "final_temperature")["value"]["value"] == pytest.approx(
        CASE_A_TEMPERATURE_K, abs=1e-6
    )
    assert output(case_a, "resistance")["value"]["value"] == pytest.approx(
        CASE_A_RESISTANCE_OHM, abs=1e-6
    )
    assert output(case_a, "resistor_power:R1")["value"]["value"] == pytest.approx(
        CASE_A_POWER_W, abs=1e-6
    )


def test_a2_every_scientific_value_carries_its_unit(case_a):
    """§26.6. There is no place in this contract for a bare number."""
    for entry in case_a["result"]["outputs"]:
        assert set(entry["value"]) == {"value", "unit"}
        assert isinstance(entry["value"]["unit"], str) and entry["value"]["unit"]
    assert output(case_a, "final_temperature")["value"]["unit"] == "kelvin"
    assert output(case_a, "resistance")["value"]["unit"] == "ohm"
    assert output(case_a, "resistor_power:R1")["value"]["unit"] == "watt"


def test_a3_the_response_never_claims_success(case_a):
    """No ``{"success": true}``, anywhere, in any shape."""
    text = json.dumps(case_a)
    assert '"success"' not in text
    assert case_a["status"] in {"executed", "refused", "execution_failed"}
    assert not isinstance(case_a["status"], bool)


def test_a4_provenance_survives_the_projection(case_a):
    """§26.5. A number without attribution is not a scientific result."""
    provenance = case_a["result"]["provenance"]
    assert provenance["run_id"] == "api-v0-case-a"
    assert provenance["software_version"]
    assert provenance["assumptions"]
    # Five bindings over three solvers and two realizations — the multi-solver
    # record `MIN-FOUNDATION-ET` minted. If the projection dropped any of it,
    # the external result would attribute a number to a computation that did
    # not produce it.
    assert len(provenance["bindings"]) == 5
    solvers = {b["solver"]["solver_id"] for b in provenance["bindings"]}
    assert len(solvers) == 3
    realizations = {
        b["realization"]["realization_id"]
        for b in provenance["bindings"]
        if b["realization"]
    }
    assert len(realizations) == 2


def test_a5_uncertainty_travels_as_unknown_rather_than_as_absence(case_a):
    """§26.4. Unknown uncertainty is not the same claim as no uncertainty."""
    kinds = {entry["uncertainty"]["kind"] for entry in case_a["result"]["outputs"]}
    assert kinds == {"unknown"}
    assert all("uncertainty" in entry for entry in case_a["result"]["outputs"])


# =====================================================================
# CASE B — valid, and it did not converge. The load-bearing row.
# =====================================================================

@pytest.fixture(scope="module")
def case_b() -> dict:
    request = canonical_request()
    request["coupling"]["max_iterations"] = 2
    return handle(request)


def test_b_a_low_budget_is_an_executed_run_that_did_not_converge(case_b):
    """Handled successfully BUT coupling not converged. Never an error."""
    assert case_b["status"] == "executed"
    assert case_b["refusal"] is None
    assert case_b["result"]["coupling"]["outcome"] == "iteration_limit_reached"
    assert case_b["result"]["coupling"]["criterion_met"] is False
    assert case_b["result"]["coupling"]["iterations_run"] == 2


def test_b2_coupling_convergence_is_not_derived_from_the_sub_solves(case_b):
    """The sharpest single measurement `ET-VERTICAL` made, carried outward.

    Every sub-solve reports success in a run whose coupling did not converge.
    A boundary that computed one from the other would report this run as
    converged, or would report three healthy solves as failures.
    """
    for participant in case_b["result"]["participants"]:
        assert participant["numerical_convergence"] in {
            "converged", "not_applicable",
        }
        assert participant["validation_status"] == "pass"
    assert case_b["result"]["coupling"]["criterion_met"] is False


def test_b3_the_final_values_are_not_called_converged(case_b):
    """A field named *converged* holding an unconverged iterate is one name
    meaning two things. The endpoint travels as its two components, unparsed."""
    text = json.dumps(case_b)
    assert "converged_value" not in text
    for endpoint in case_b["result"]["torn_endpoints"]:
        assert set(endpoint) == {"problem_id", "quantity", "final_value"}
        assert "::" not in endpoint["problem_id"] + endpoint["quantity"]


def test_b4_the_iterate_change_history_is_one_scalar_per_sweep(case_b):
    changes = case_b["result"]["coupling"]["iterate_changes"]
    assert len(changes) == case_b["result"]["coupling"]["iterations_run"]
    assert all(set(c) == {"value", "unit"} for c in changes)
    assert case_b["result"]["coupling"]["final_iterate_change"] == changes[-1]


# =====================================================================
# CASE C — admission. DETECTION != ENFORCEMENT.
# =====================================================================

def _inadmissible_requests() -> dict[str, dict]:
    """One request per distinct admission site, each refused by different code."""
    negative = canonical_request()
    negative["inputs"]["stages"][0]["reference_resistance"]["value"] = -10.0

    wrong_dimension = canonical_request()
    wrong_dimension["inputs"]["stages"][0]["heat_capacity"]["unit"] = "volt"

    unparsable_unit = canonical_request()
    unparsable_unit["inputs"]["source_voltage"]["unit"] = "kilohm"

    zero_capacity = canonical_request()
    zero_capacity["inputs"]["stages"][0]["heat_capacity"]["value"] = 0.0

    affine_tolerance = canonical_request()
    affine_tolerance["coupling"]["tolerance"]["unit"] = "degC"

    non_positive_voltage = canonical_request()
    non_positive_voltage["inputs"]["source_voltage"]["unit"] = "second"

    duplicate_stage = canonical_request()
    duplicate_stage["inputs"]["stages"].append(
        copy.deepcopy(duplicate_stage["inputs"]["stages"][0])
    )

    return {
        "non_positive_reference_resistance": negative,
        "dimensionally_wrong_capacity": wrong_dimension,
        "unparsable_unit": unparsable_unit,
        "non_positive_heat_capacity": zero_capacity,
        "affine_tolerance": affine_tolerance,
        "dimensionally_wrong_voltage": non_positive_voltage,
        "duplicate_component_id": duplicate_stage,
    }


def test_c_an_inadmissible_declaration_is_refused_with_a_scientific_code():
    for label, request in _inadmissible_requests().items():
        response = handle(request)
        assert response["status"] == "refused", label
        assert response["result"] is None, label
        assert (
            response["refusal"]["code"]
            == RefusalCode.SCIENTIFIC_ADMISSION_REFUSED.value
        ), (label, response["refusal"])
        assert response["refusal"]["stage"] == "admission", label


def test_c2_no_solver_and_no_process_executes_after_an_admission_refusal(
    monkeypatch,
):
    """DETECTION != ENFORCEMENT, proven by instrumentation rather than argued.

    The prior lesson this milestone was told to carry: a check whose only
    effect is a field nothing consults is not a guard. So the refusal is not
    inspected — the three chokepoints are, and all three are booby-trapped to
    fail the test if they are reached at all.
    """
    spies = _Spies(monkeypatch)
    for label, request in _inadmissible_requests().items():
        response = handle(request)
        assert response["result"] is None, label
        assert response["status"] in {"refused", "execution_failed"}, label
    assert spies.total == 0
    assert (spies.loop, spies.native_solve, spies.process) == (0, 0, 0)


def test_c3_the_admission_sites_are_not_one_centralized_gate():
    """No ``admit()`` function was introduced. The refusals stay where the
    knowledge is, and the milestone proves the *ordering* instead."""
    for _, source in _sources(APPLICATION_DIR):
        tree = ast.parse(source)
        names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert not {"admit", "validate_request", "check_request"} & names, names


def test_c4_a_refused_request_carries_no_scientific_verdict():
    """A refusal must not be readable as a scientific finding of any kind."""
    request = canonical_request()
    request["inputs"]["stages"][0]["reference_resistance"]["value"] = -10.0
    response = handle(request)
    assert response["result"] is None
    text = json.dumps(response)
    for forbidden in (
        "criterion_met", "iteration_limit_reached", "converged",
        "validation_status", "attained_levels",
    ):
        assert forbidden not in text, forbidden


# =====================================================================
# CASE D — schema versions and silent field dropping
# =====================================================================

def test_d_an_unsupported_schema_version_fails_loudly():
    for schema in (
        "crafty_execution_request/2",
        "crafty_execution_request/0",
        "crafty_execution_request",
        "scientific_result/2",
        "coupling_fixed_point_run/1",
        None,
    ):
        request = canonical_request()
        if schema is None:
            del request["schema"]
        else:
            request["schema"] = schema
        response = handle(request)
        assert response["status"] == "refused", schema
        assert (
            response["refusal"]["code"]
            == RefusalCode.UNSUPPORTED_SCHEMA_VERSION.value
        ), schema
        assert response["result"] is None


def test_d2_an_unknown_field_is_refused_and_never_dropped():
    """A field this reader does not implement must produce a refusal, not a
    different number. The two probes are chosen because both name knobs that,
    if honoured, would change the answer."""
    relaxed = canonical_request()
    relaxed["coupling"]["relaxation_factor"] = 0.5

    extra_stage_field = canonical_request()
    extra_stage_field["inputs"]["stages"][0]["emissivity"] = 0.9

    top_level = canonical_request()
    top_level["metadata"] = {"anything": "at all"}

    nested_quantity = canonical_request()
    nested_quantity["inputs"]["source_voltage"]["tolerance"] = 0.1

    for label, request in (
        ("relaxation_factor", relaxed),
        ("emissivity", extra_stage_field),
        ("metadata", top_level),
        ("quantity_extra", nested_quantity),
    ):
        response = handle(request)
        assert response["status"] == "refused", label
        assert (
            response["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value
        ), label
        assert response["result"] is None, label


def test_d3_a_missing_field_is_not_defaulted():
    """No default anywhere in ``inputs`` or ``coupling``. A default here would
    be a default that changes an answer."""
    request = canonical_request()
    del request["run_id"]
    assert handle(request)["status"] == "refused"

    for section, field in (
        ("coupling", "seed_temperature"),
        ("coupling", "tolerance"),
        ("coupling", "max_iterations"),
        ("coupling", "transported_temperature"),
        ("inputs", "source_voltage"),
    ):
        request = canonical_request()
        del request[section][field]
        response = handle(request)
        assert response["status"] == "refused", (section, field)
        assert field in response["refusal"]["detail"], (section, field)


def test_d4_a_bare_number_is_not_a_scientific_value():
    request = canonical_request()
    request["inputs"]["source_voltage"] = 5.0
    response = handle(request)
    assert response["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value

    request = canonical_request()
    request["inputs"]["source_voltage"] = {"value": 5.0}
    assert handle(request)["status"] == "refused"


def test_d5_a_boolean_is_not_a_number():
    """``True`` is an ``int`` in Python and would silently become 1.0."""
    request = canonical_request()
    request["inputs"]["source_voltage"]["value"] = True
    assert handle(request)["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value

    request = canonical_request()
    request["coupling"]["max_iterations"] = True
    assert handle(request)["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value


def test_d6_the_transported_metric_is_enumerated_and_load_bearing():
    """Both members are kelvin; only the name separates them, and they converge
    to different temperatures. This is why the field is not a free string."""
    steady = canonical_request()
    steady["coupling"]["transported_temperature"] = "steady_state_temperature"
    response = handle(steady)
    assert response["status"] == "executed"
    transient = handle(canonical_request())
    difference = (
        output(response, "steady_state_temperature")["value"]["value"]
        - output(transient, "final_temperature")["value"]["value"]
    )
    assert abs(difference) > 3.0

    bogus = canonical_request()
    bogus["coupling"]["transported_temperature"] = "temperature"
    assert handle(bogus)["status"] == "refused"


# =====================================================================
# CASE E — unknown execution and unknown profile
# =====================================================================

def test_e_an_unknown_execution_is_refused_and_names_the_admissible_set():
    request = canonical_request()
    request["execution"] = "electrothermal.series_self_heating/2"
    response = handle(request)
    assert response["refusal"]["code"] == RefusalCode.UNKNOWN_EXECUTION.value
    # The refusal IS the discovery affordance. This is why no /capabilities
    # endpoint and no crafty_capabilities tool exists.
    assert EXECUTION in response["refusal"]["detail"]


def test_e2_an_unknown_profile_is_refused_before_anything_is_resolved(monkeypatch):
    """Refused before the closed mapping is even consulted, and long before any
    process could be launched."""
    spies = _Spies(monkeypatch)
    prepared = []

    def prepare(*args, **kwargs):
        prepared.append(args)
        raise AssertionError("admission must not have been attempted")

    monkeypatch.setattr(ets, "prepare", prepare)
    for profile in (
        "/usr/bin/ngspice",
        "ngspice; touch /tmp/crafty-pwned",
        "NGSPICE",
        "ngspice ",
        "native/../ngspice",
        "",
        "spice",
    ):
        request = canonical_request()
        request["execution_profile"] = profile
        response = handle(request)
        assert (
            response["refusal"]["code"]
            == RefusalCode.UNKNOWN_EXECUTION_PROFILE.value
        ), profile
        assert response["result"] is None, profile
    assert prepared == []
    assert spies.total == 0


def test_e3_a_non_string_profile_or_execution_is_refused(monkeypatch):
    spies = _Spies(monkeypatch)
    for value in ({"argv": ["/bin/sh", "-c", "id"]}, ["ngspice"], 7, None, True):
        request = canonical_request()
        request["execution_profile"] = value
        assert handle(request)["status"] == "refused", value
        request = canonical_request()
        request["execution"] = value
        assert handle(request)["status"] == "refused", value
    assert spies.total == 0


# =====================================================================
# CASE F — a sub-solve failing during the iteration
# =====================================================================

@pytest.fixture(scope="module")
def case_f() -> dict:
    """A negative-TCR conductor whose resistance goes non-positive at the
    temperature the loop transports. The DC domain refuses it — mid-iteration,
    on a request that was perfectly admissible when it was posed."""
    request = canonical_request()
    request["inputs"]["source_voltage"]["value"] = 12.0
    stage = request["inputs"]["stages"][0]
    stage["temperature_coefficient"]["value"] = -0.01
    stage["reference_temperature"]["value"] = 300.0
    stage["duration"]["value"] = 6000.0
    return handle(request)


def test_f_a_mid_iteration_failure_is_not_an_admission_refusal(case_f):
    """Class alone would misclassify this: ``InvalidScientificProblem`` is
    raised both by a caller's bad declaration and from inside the loop. The
    classifier reads the class **and** the position."""
    assert case_f["status"] == "execution_failed"
    assert case_f["refusal"]["code"] == RefusalCode.SUBSOLVER_EXECUTION_FAILED.value
    assert case_f["refusal"]["stage"] == "execution"
    assert case_f["refusal"]["error_type"] == "InvalidScientificProblem"


def test_f2_an_execution_failure_carries_no_convergence_or_validity_claim(case_f):
    """A failure must never be readable as *the science was invalid* or as
    *the coupling did not converge*. There is nothing there to read."""
    assert case_f["result"] is None
    text = json.dumps(case_f)
    for forbidden in ("outcome", "criterion_met", "validation_status", "participants"):
        assert forbidden not in text, forbidden


# =====================================================================
# CASE G — injection
# =====================================================================

#: Every hostile string this milestone tries in every string-valued field.
#: The list is shared with the cross-process test so neither can drift.
HOSTILE_STRINGS = (
    "/usr/bin/ngspice",
    "/bin/sh",
    "; touch MARKER",
    "$(touch MARKER)",
    "`touch MARKER`",
    "ngspice --version",
    "__import__('os').system('id')",
    "../../../../etc/passwd",
    "file:///etc/passwd",
    "ngspice\x00native",
    # The one that actually worked. See test_g0.
    "R1\n.control\nshell touch MARKER\n.endc",
    "R1\n.param x=1",
    "R1\r\n.end",
)

STRING_FIELDS = (
    ("execution_profile", lambda r, v: r.__setitem__("execution_profile", v)),
    ("execution", lambda r, v: r.__setitem__("execution", v)),
    ("run_id", lambda r, v: r.__setitem__("run_id", v)),
    ("component_id",
     lambda r, v: r["inputs"]["stages"][0].__setitem__("component_id", v)),
    ("unit", lambda r, v: r["inputs"]["source_voltage"].__setitem__("unit", v)),
    ("transported_temperature",
     lambda r, v: r["coupling"].__setitem__("transported_temperature", v)),
)


def test_g0_the_reproduced_remote_code_execution_is_closed(tmp_path):
    """A regression for a **reproduced** RCE, not a hypothetical one.

    `architecture-falsifier` found, and this milestone then executed, the
    following: `component_id` was validated for type only, flowed into
    ``CoupledElectroThermalSystem.circuit_id``, and the external-provider
    adapter emitted that identifier into its deck's **title line**. A newline
    ended the title; everything after it was parsed by the provider as deck
    input; a ``.control`` block placed there executed ``shell touch <path>``
    and the file appeared. The run reported ``executed`` / ``criterion_met``
    with every sub-solve passing and a ``ProvenanceRecord`` describing the
    circuit that was *declared* rather than the one that was solved.

    Two independent repairs, and this test exercises the request half of both:
    the identifier is constrained to a published character class here, and the
    provider adapter no longer emits any Crafty identifier into deck text.
    """
    marker = tmp_path / "rce"
    payload = f"R1\n.control\nshell touch {marker}\n.endc"
    for profile in ("native", "ngspice"):
        request = canonical_request(execution_profile=profile)
        request["inputs"]["stages"][0]["component_id"] = payload
        response = handle(request)
        assert response["status"] == "refused", profile
        assert (
            response["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value
        ), profile
        assert response["result"] is None, profile
    assert not marker.exists()


def test_g0b_an_identifier_is_a_name_and_not_free_text():
    for value in (
        "R1\n", "R1 R2", "R1;R2", "R1/R2", "R1\tX", "", " R1", "R1\x00",
        "_R1", "R" * 65, ".control", "R1$(id)",
    ):
        for field in ("run_id",):
            request = canonical_request()
            request[field] = value
            assert handle(request)["status"] == "refused", (field, value)
        request = canonical_request()
        request["inputs"]["stages"][0]["component_id"] = value
        assert handle(request)["status"] == "refused", value
    # And ordinary names still work.
    request = canonical_request()
    request["inputs"]["stages"][0]["component_id"] = "R1.a:b-c_d"
    assert handle(request)["status"] == "executed"


def test_g_no_injection_attempt_is_admitted_or_reaches_a_process(
    monkeypatch, tmp_path
):
    """Executable paths, shell fragments, deck fragments, argv objects and
    traversal, in **every** string-valued field.

    The assertion is ``spies.total == 0``, not ``result is None``. The first
    form asserted the latter and was **vacuous**: ``_Spies`` makes the coupling
    loop raise, so an *admitted* hostile request also produced ``result is
    None`` and the test passed while the request was in fact accepted. That is
    how the RCE in ``test_g0`` survived a test written to catch it.
    """
    marker = tmp_path / "crafty-pwned"
    spies = _Spies(monkeypatch)
    for raw in HOSTILE_STRINGS:
        value = raw.replace("MARKER", str(marker))
        for name, mutate in STRING_FIELDS:
            request = canonical_request()
            mutate(request, value)
            response = handle(request)
            assert response["status"] in {"refused", "execution_failed"}, (
                name, value,
            )
            assert response["result"] is None, (name, value)
    # Nothing above was admitted: not one request reached the loop, a circuit
    # solve, or a process.
    assert (spies.loop, spies.native_solve, spies.process) == (0, 0, 0)
    assert not marker.exists()


def test_g2_a_shell_like_unit_string_dies_in_the_unit_parser(tmp_path):
    """The unit string is the only free-form external string that reaches a
    parser at all, and the parser is pint's unit-expression parser. Executed,
    not asserted: nothing is created and every one is refused."""
    marker = tmp_path / "unit-pwned"
    for unit in (
        f"__import__('os').system('touch {marker}')",
        f"eval(\"open('{marker}','w')\")",
        "1;import os",
        "ohm; rm -rf /",
        "`id`",
        "/usr/bin/ngspice",
        "ohm|sh",
    ):
        request = canonical_request()
        request["inputs"]["source_voltage"]["unit"] = unit
        response = handle(request)
        assert response["status"] == "refused", unit
        assert (
            response["refusal"]["code"]
            == RefusalCode.SCIENTIFIC_ADMISSION_REFUSED.value
        ), unit
        assert response["refusal"]["error_type"] == "UnitCompatibilityError", unit
    assert not marker.exists()


def test_g3_an_unexpected_object_where_a_scalar_belongs_is_refused(monkeypatch):
    spies = _Spies(monkeypatch)
    for payload in (
        {"__class__": "os.system"},
        [1, 2, 3],
        "5 volt",
        None,
    ):
        request = canonical_request()
        request["inputs"]["source_voltage"] = payload
        assert handle(request)["status"] == "refused", payload
    request = canonical_request()
    request["inputs"]["stages"] = {"R1": {}}
    assert handle(request)["status"] == "refused"
    request = canonical_request()
    request["inputs"]["stages"] = []
    assert handle(request)["status"] == "refused"
    assert spies.total == 0


def test_g4_the_request_contains_no_free_form_mapping():
    """Structural, not lexical: an extra key at EVERY level is refused. If any
    level accepted one, that level would be an untyped escape hatch."""
    probes = [
        lambda r: r.__setitem__("extra", 1),
        lambda r: r["inputs"].__setitem__("extra", 1),
        lambda r: r["inputs"]["stages"][0].__setitem__("extra", 1),
        lambda r: r["inputs"]["stages"][0]["duration"].__setitem__("extra", 1),
        lambda r: r["inputs"]["source_voltage"].__setitem__("extra", 1),
        lambda r: r["coupling"].__setitem__("extra", 1),
        lambda r: r["coupling"]["tolerance"].__setitem__("extra", 1),
    ]
    for index, probe in enumerate(probes):
        request = canonical_request()
        probe(request)
        response = handle(request)
        assert response["status"] == "refused", index
        assert (
            response["refusal"]["code"] == RefusalCode.MALFORMED_REQUEST.value
        ), index


def test_g5_an_unbounded_amount_of_work_cannot_be_requested():
    for budget in (0, -1, 201, 10**9):
        request = canonical_request()
        request["coupling"]["max_iterations"] = budget
        assert handle(request)["status"] == "refused", budget

    request = canonical_request()
    stage = request["inputs"]["stages"][0]
    request["inputs"]["stages"] = [
        {**copy.deepcopy(stage), "component_id": f"R{i}"} for i in range(9)
    ]
    assert handle(request)["status"] == "refused"


def test_g6_no_external_string_reaches_a_process_argument_construction():
    """A source-level audit of the whole request -> provider flow.

    Not a blacklist over request values — a structural claim about the code:
    nothing in the application layer or either transport calls a process, an
    import, an eval, or a path constructor at all.
    """
    forbidden_calls = {
        "system", "popen", "spawn", "spawnl", "spawnv", "execv", "execve",
        "eval", "exec", "__import__", "import_module",
        "check_output", "check_call", "setattr", "loads_pickle",
    }
    for directory in (APPLICATION_DIR, HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = ""
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        name = node.func.attr
                    assert name not in forbidden_calls, (path.name, name)
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    targets = (
                        [a.name for a in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
                    for target in targets:
                        assert "subprocess" not in target, (path.name, target)
                        assert "shlex" not in target, (path.name, target)
                        assert "pickle" not in target, (path.name, target)
                        assert "os.path" not in target, (path.name, target)


def test_g7_nothing_external_reaches_the_environment():
    """``CRAFTY_NGSPICE_ARGV`` is deployment configuration. If a request could
    reach ``os.environ``, the closed profile enumeration would be decorative."""
    for directory in (APPLICATION_DIR, HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            code = _code_only(source)
            assert "environ" not in code, path.name
            assert "putenv" not in code, path.name
            assert "getenv" not in code, path.name


# =====================================================================
# The five distinctions, and what the boundary refuses to claim
# =====================================================================

def test_h_the_five_distinctions_are_separately_representable(case_a, case_b, case_f):
    """TRANSPORT != EXECUTION != NUMERICAL != COUPLING != VALIDITY.

    Three runs, and no two of the five fields move together across them.
    """
    # execution success and coupling convergence disagree in CASE B
    assert case_b["status"] == "executed"
    assert case_b["result"]["coupling"]["criterion_met"] is False
    # numerical convergence and coupling convergence disagree in CASE B
    assert all(
        p["numerical_convergence"] in {"converged", "not_applicable"}
        for p in case_b["result"]["participants"]
    )
    # execution success is absent entirely in CASE F, while nothing scientific
    # is claimed
    assert case_f["status"] == "execution_failed" and case_f["result"] is None
    # and validity is never claimed at all
    assert case_a["result"]["model_validity"]["assessed"] is False


def test_h2_model_validity_is_reported_as_not_assessed_rather_than_omitted(case_a):
    """NOT_RUN != PASS, and the honest answer is a measured negative finding:
    the executed coupled path produces no model-applicability verdict, so no
    transport can report one. Calling Crafty's own validity assessment from
    the application layer would have been a scientific act performed by a
    layer that did not execute the science."""
    validity = case_a["result"]["model_validity"]
    assert validity["assessed"] is False
    assert "NOT_RUN" in validity["reason"]
    for _, source in _sources(APPLICATION_DIR):
        assert "assess_resistance_validity" not in source


def test_h3_the_boundary_reports_only_verdicts_the_execution_produced(case_a):
    """Every field is traceable to a record the executed path wrote."""
    participants = {p["problem_id"] for p in case_a["result"]["participants"]}
    outputs = {o["problem_id"] for o in case_a["result"]["outputs"]}
    assert participants == outputs
    assert len(participants) == 3
    for participant in case_a["result"]["participants"]:
        assert participant["solver"] is not None
        assert participant["models"]


# =====================================================================
# Serialization
# =====================================================================

def test_the_external_schemas_are_their_own_identities():
    """Neither reuses a Scientific Core or coupling name. `require_schema` is
    exact-match with no migration path, so an external contract welded to an
    internal one prices every future internal rename at a public migration."""
    assert contract.REQUEST_SCHEMA == "crafty_execution_request/1"
    assert contract.RESPONSE_SCHEMA == "crafty_execution_response/1"
    from engcore.coupling import COUPLED_RUN_SCHEMA
    from engcore.scientific.results.result import RESULT_SCHEMA

    assert contract.RESPONSE_SCHEMA not in {COUPLED_RUN_SCHEMA, RESULT_SCHEMA}
    for token in (
        "coupled_run", "coupling_fixed_point", "torn_endpoint",
        "scientific_result", "provenance_record",
    ):
        assert token not in contract.RESPONSE_SCHEMA
        assert token not in contract.REQUEST_SCHEMA


def test_no_internal_schema_string_appears_in_a_response(case_a, case_b):
    """The projection is a projection, not a passthrough. A disclaimed
    passthrough key is still a key clients store."""
    for response in (case_a, case_b):
        text = json.dumps(response)
        for token in (
            "coupling_fixed_point_run", "coupling_fixed_point_iteration",
            "coupling_fixed_point_plan", "coupling_torn_endpoint",
            "scientific_result/", "provenance_record/", "quantity/1",
        ):
            assert token not in text, token


def test_the_response_leaks_no_provider_output_path_repr_or_traceback(
    case_a, case_b, case_f
):
    for response in (case_a, case_b, case_f):
        text = json.dumps(response)
        for forbidden in (
            "Traceback", "File \"", "/usr/bin", "/home/", "wsl.exe",
            "<object at 0x", "object at 0x", ".pyc", "netlist", "stdout",
            "\\x00",
        ):
            assert forbidden not in text, forbidden


def test_the_response_is_deterministic_and_json_round_trippable(case_a):
    again = handle(canonical_request())
    assert json.dumps(again, sort_keys=True) == json.dumps(case_a, sort_keys=True)
    assert json.loads(json.dumps(case_a)) == case_a


def test_the_projection_is_far_smaller_than_the_internal_record(case_a):
    """The measurement that decided against a passthrough key.

    The external contract is deliberately lossy: per-iteration participant
    results are not externally reachable in v0. Recorded as a limitation, not
    presented as a feature.
    """
    from engcore.scientific.serialization import to_json

    request = canonical_request()
    prepared = ets.prepare(request["inputs"], request["coupling"], "native")
    internal = len(to_json(prepared.run("api-v0-case-a")))
    external = len(json.dumps(case_a, sort_keys=True))
    assert external < internal / 10
    assert internal > 100_000


def test_no_bulk_data_crosses_the_boundary(case_a):
    """This consumer produces none, and nothing O(mesh) can appear."""

    def longest(node) -> int:
        if isinstance(node, list):
            return max([len(node)] + [longest(c) for c in node])
        if isinstance(node, dict):
            values = [longest(c) for c in node.values()]
            return max(values) if values else 0
        return 0

    assert longest(case_a) <= 50
    assert "data_references" not in json.dumps(case_a)


# =====================================================================
# Architecture fitness
# =====================================================================

#: The preregistration's fail condition 1 named `src/engcore/domains/` as
#: byte-unchanged, and **it was triggered**. `architecture-falsifier` found a
#: remote code execution through the external-provider adapter's deck title
#: line; the milestone reproduced it, and closing it required one line of
#: `ngspice.py`. The alternative was to publish an API with a reproduced RCE
#: behind it and record the fail condition as honoured. Recorded as deviation
#: D-1 in docs/api-mcp-v0-evidence.md rather than quietly absorbed.
_RCE_REPAIR = "src/engcore/domains/electrical/ngspice.py"


def test_universal_core_coupling_and_the_other_pack_are_untouched():
    """Fail conditions 1 and 2 of the preregistration, with one exception."""
    for path in (
        "src/engcore/scientific/",
        "src/engcore/coupling/",
        "src/engcore/systems/fluidthermal/",
    ):
        assert _diff(path) == "", path
    assert set(_diff("src/engcore/domains/").split()) == {_RCE_REPAIR}


def test_the_provider_adapter_change_is_the_rce_repair_and_nothing_else():
    """One line, and it removes a channel rather than filtering it."""
    diff = subprocess.run(
        ["git", "diff", "-U0", "3f2e6dd", "--", _RCE_REPAIR],
        cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
    ).stdout
    removed = [
        line for line in diff.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    assert removed == ['-    lines = [f"crafty {circuit.circuit_id}"]'], removed
    code = [line for line in added if not line.lstrip("+").lstrip().startswith("#")]
    assert code == ['+    lines = ["crafty circuit"]'], code

    # No Crafty identifier can reach deck text any more.
    from engcore.domains.electrical import ngspice as provider
    from engcore.domains.electrical.dc import (
        DCCircuit, DCVoltageSource, ElectricalNode, Resistor,
    )
    from engcore.scientific.units.quantity import Quantity

    circuit = DCCircuit(
        circuit_id="R1\n.control\nshell true\n.endc",
        nodes=(ElectricalNode("a"), ElectricalNode("gnd", is_reference=True)),
        resistors=(Resistor("R1", "a", "gnd", Quantity(10.0, "ohm")),),
        voltage_sources=(
            DCVoltageSource("V1", "a", "gnd", Quantity(5.0, "volt")),
        ),
    )
    netlist = provider.build_netlist(circuit).text
    assert "shell" not in netlist
    assert circuit.circuit_id not in netlist
    assert netlist.splitlines()[0] == "crafty circuit"


#: The preregistration commit — the tree as it stood before one line of this
#: milestone's implementation existed.
PREREG_COMMIT = "3f2e6dd"

#: The three trees this milestone ADDS. New code, importing inward only.
NEW_TREES = (
    "src/engcore/application/", "src/crafty_http/", "src/crafty_mcp/",
)


def test_exactly_three_pre_existing_source_files_were_edited():
    """Everything else under `src/` is new, and every edit is accounted for."""
    changed = set(
        subprocess.run(
            ["git", "diff", "--name-only", PREREG_COMMIT, "--", "src/"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        ).stdout.split()
    )
    edited = {
        path for path in changed
        if not any(path.startswith(tree) for tree in NEW_TREES)
    }
    assert edited == {
        # the additive execution seam
        "src/engcore/systems/electrothermal/coupled.py",
        "src/engcore/systems/electrothermal/__init__.py",
        # the RCE repair
        _RCE_REPAIR,
    }, sorted(edited)


def test_the_seam_changed_no_number():
    """The additive keyword must be invisible to every pre-existing caller."""
    from engcore.scientific.units.quantity import Quantity
    from engcore.domains import thermal_lumped as lump
    from engcore.domains.electrical import material as mat

    system = etc.CoupledElectroThermalSystem(
        stages=(
            etc.CoupledStage(
                mat.TemperatureDependentConductor(
                    "R1", Quantity(10.0, "ohm"), Quantity(0.00393, "1/kelvin"),
                    Quantity(293.15, "kelvin"),
                ),
                lump.ThermalBody(
                    "R1", Quantity(2.5, "joule/kelvin"),
                    Quantity(0.05, "watt/kelvin"), Quantity(300.0, "kelvin"),
                    Quantity(300.0, "kelvin"), Quantity(120.0, "second"),
                ),
            ),
        ),
        source_voltage=Quantity(5.0, "volt"),
    )
    problems = etc.coupled_problems(system, {"R1": Quantity(10.0, "ohm")})
    plan = etc.nominal_plan(
        system, etc.coupled_dependencies(system, problems),
        seed=Quantity(300.0, "kelvin"), tolerance=Quantity(1e-6, "kelvin"),
        max_iterations=50,
    )
    default = etc.run_fixed_point_coupling(system, plan, run_id="seam")
    explicit = etc.run_fixed_point_coupling(
        system, plan, run_id="seam", circuit_solver=etc.native_circuit_solver
    )
    from engcore.scientific.serialization import to_json

    assert to_json(default) == to_json(explicit)
    assert default.iterations_run == CASE_A_ITERATIONS
    assert default.final.result_for("thermal-lumped-R1").value(
        "final_temperature"
    ).magnitude_in("kelvin") == pytest.approx(CASE_A_TEMPERATURE_K, abs=1e-6)


def test_no_transport_library_is_importable_by_any_scientific_package():
    """Reviewer change CH-3. The existing guard covers ``scientific/`` only;
    nothing forbade a transport library from entering ``coupling/``,
    ``domains/`` or ``systems/``, which is how an unenforced promise rots."""
    forbidden = (
        "fastapi", "starlette", "flask", "django", "uvicorn", "pydantic",
        "aiohttp", "tornado", "requests", "httpx", "socket", "socketserver",
        "http.server", "http.client", "xmlrpc", "wsgiref", "asyncio",
        "mcp", "crafty_http", "crafty_mcp",
    )
    for package in ("scientific", "coupling", "domains", "systems", "application"):
        root = REPO_ROOT / "src" / "engcore" / package
        for path, source in _sources(root):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    targets = [node.module or ""]
                for target in targets:
                    head = target.split(".")[0]
                    assert head not in forbidden, (path.name, target)
                    assert target not in forbidden, (path.name, target)


def test_the_scientific_packages_do_not_import_the_application_layer():
    """Dependency direction. The application layer depends inward, never back."""
    for package in ("scientific", "coupling", "domains", "systems"):
        root = REPO_ROOT / "src" / "engcore" / package
        for path, source in _sources(root):
            for node in ast.walk(ast.parse(source)):
                targets: list[str] = []
                if isinstance(node, ast.Import):
                    targets = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    targets = [node.module or ""]
                for target in targets:
                    assert "application" not in target, (path.name, target)
                    assert "crafty_http" not in target, (path.name, target)
                    assert "crafty_mcp" not in target, (path.name, target)


def test_the_transports_import_only_the_boundary_from_engcore():
    """Neither transport may reach a domain, a system pack, the coupling
    package or the Scientific Core. If either could, the claim that they share
    one boundary would be unfalsifiable."""
    for directory in (HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.startswith("engcore"):
                        assert node.module.startswith("engcore.application"), (
                            path.name, node.module,
                        )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not alias.name.startswith("engcore.") or \
                            alias.name.startswith("engcore.application"), alias.name


def test_the_transports_carry_no_domain_vocabulary_in_their_code():
    """No scientific decision may live in a transport. Checked over executable
    source with docstrings and comments removed, because prose explaining the
    absence would otherwise trip the scan."""
    vocabulary = (
        "resistance", "resistor", "thermal", "temperature", "kelvin", "ohm",
        "watt", "volt", "ampere", "joule", "conductor", "conductance",
        "electrical", "circuit", "netlist", "ngspice", "heat", "lumped",
        "fluid", "kinetic", "mesh",
    )
    for directory in (HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            code = _code_only(source).lower()
            for word in vocabulary:
                assert word not in code, (path.name, word)
    # The guard must be able to fail.
    assert "kelvin" in _code_only('X = "kelvin"').lower()


def test_the_transports_do_no_arithmetic():
    """A transport that computed anything would be doing science."""
    for directory in (HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.BinOp):
                    # `|` is a type union in an annotation; `+` is string
                    # concatenation. Nothing multiplies, divides or powers.
                    assert isinstance(node.op, (ast.Add, ast.BitOr)), (
                        path.name, type(node.op).__name__,
                    )


def test_the_execution_module_states_declarations_and_computes_nothing():
    """The one execution-specific module in the application layer contains no
    equation: no multiplication, division, power or subtraction anywhere."""
    source = (APPLICATION_DIR / "executions" / "electrothermal_series.py").read_text(
        encoding="utf-8"
    )
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.BinOp):
            assert isinstance(node.op, (ast.BitOr, ast.Add)), type(node.op).__name__


def test_no_core_schema_string_moved():
    from engcore.coupling import (
        COUPLED_ITERATION_SCHEMA, COUPLED_RUN_SCHEMA, FIXED_POINT_PLAN_SCHEMA,
        TORN_ENDPOINT_SCHEMA,
    )
    from engcore.scientific.ir.problem import PROBLEM_SCHEMA
    from engcore.scientific.results.provenance import PROVENANCE_SCHEMA
    from engcore.scientific.results.result import RESULT_SCHEMA

    assert RESULT_SCHEMA == "scientific_result/2"
    assert PROVENANCE_SCHEMA == "provenance_record/2"
    assert PROBLEM_SCHEMA == "scientific_problem/2"
    assert COUPLED_RUN_SCHEMA == "coupling_fixed_point_run/1"
    assert COUPLED_ITERATION_SCHEMA == "coupling_fixed_point_iteration/1"
    assert FIXED_POINT_PLAN_SCHEMA == "coupling_fixed_point_plan/1"
    assert TORN_ENDPOINT_SCHEMA == "coupling_torn_endpoint/1"


# =====================================================================
# The catalog is closed, and the published contract cannot drift
# =====================================================================

def test_the_catalog_is_a_literal_dict_with_no_fallthrough():
    assert set(catalog.EXECUTIONS) == {EXECUTION}
    assert set(ets.PROFILES) == {"native", "ngspice"}
    for name in ("Ngspice", "ngspice ", " native", "native\n"):
        assert name not in ets.PROFILES
    source = (APPLICATION_DIR / "catalog.py").read_text(encoding="utf-8")
    for forbidden in ("startswith", "lower()", "strip()", "get(", "setdefault"):
        assert forbidden not in source, forbidden


def test_the_application_layer_names_no_solver_circuit_or_provider():
    """The falsifier's C-2. A platform-wide profile enumeration made the
    universal layer import ``CircuitSolver`` and ``native_circuit_solver`` —
    so a layer that must not know what it is executing named a *circuit* — and
    validated the two enumerations independently, which would have admitted a
    circuit solver for a fluid problem the moment a second execution existed.
    Profiles now belong to the execution that gives them meaning."""
    universal = ("circuit", "CircuitSolver", "native_circuit_solver",
                 "ngspice", "resistance", "kelvin", "watt", "ohm")
    for name in ("catalog.py", "contract.py", "service.py", "describe.py"):
        code = _code_only((APPLICATION_DIR / name).read_text(encoding="utf-8"))
        for word in universal:
            assert word not in code, (name, word)
    # `catalog.py` legitimately names the execution MODULE it exposes — that is
    # its entire job — so the domain-word scan excludes it and applies to the
    # three modules that must know nothing about what they are executing.
    for name in ("contract.py", "service.py", "describe.py"):
        code = _code_only((APPLICATION_DIR / name).read_text(encoding="utf-8"))
        for word in ("thermal", "electro", "fluid", "kinetic"):
            assert word not in code, (name, word)


def test_a_profile_is_validated_against_the_resolved_execution():
    """There is no platform-wide profile set to validate against."""
    assert catalog.profile_names(EXECUTION) == frozenset({"native", "ngspice"})
    assert not hasattr(catalog, "PROFILES")
    schema = describe.request_json_schema()
    # The relation between the two enumerations is published, not implied.
    (clause,) = schema["allOf"]
    assert clause["if"]["properties"]["execution"]["const"] == EXECUTION
    assert clause["then"]["properties"]["execution_profile"]["enum"] == [
        "native", "ngspice",
    ]


def test_the_profile_resolvers_take_no_caller_input():
    """The structural reason no external string can influence a provider
    invocation: the resolver has nowhere to put one."""
    import inspect

    for name, resolver in ets.PROFILES.items():
        assert inspect.signature(resolver).parameters == {}, name


def test_the_published_schema_cannot_drift_from_the_validator():
    """Fitness question 16 depends on the published contract being the enforced
    one. Derived from the same constants, and checked to be so."""
    schema = describe.request_json_schema()
    assert schema["properties"]["execution"]["enum"] == sorted(catalog.EXECUTIONS)
    assert schema["properties"]["schema"]["const"] == contract.REQUEST_SCHEMA
    assert set(schema["required"]) == {
        "schema", "execution", "execution_profile", "inputs", "coupling",
        "run_id",
    }
    (clause,) = schema["allOf"]
    body = clause["then"]["properties"]
    assert set(body["inputs"]["required"]) == set(ets.INPUT_KEYS)
    assert set(body["coupling"]["required"]) == set(ets.COUPLING_KEYS)
    stage = body["inputs"]["properties"]["stages"]["items"]
    assert set(stage["required"]) == set(ets.STAGE_KEYS)
    assert (
        body["coupling"]["properties"]["transported_temperature"]["enum"]
        == sorted(ets.TRANSPORTED_TEMPERATURES)
    )
    # The published identifier pattern is the enforced one, not a copy.
    assert stage["properties"]["component_id"]["pattern"] == (
        contract.IDENTIFIER_PATTERN
    )
    assert schema["properties"]["run_id"]["pattern"] == contract.IDENTIFIER_PATTERN
    # additionalProperties: False everywhere a mapping is described.
    def closed(node) -> None:
        if isinstance(node, dict):
            # Only where properties are declared. The two top-level `inputs`
            # and `coupling` placeholders stay open deliberately: JSON Schema
            # evaluates `additionalProperties` against the SAME schema object's
            # own `properties`, so closing them in the base would reject the
            # very fields the conditional clause adds.
            if node.get("type") == "object" and "properties" in node:
                assert node.get("additionalProperties") is False, node.get("title")
            for child in node.values():
                closed(child)
        elif isinstance(node, list):
            for child in node:
                closed(child)

    closed(schema)


def test_the_published_identifier_pattern_agrees_with_the_enforced_one():
    """Python's ``$`` also matches before a trailing newline; JSON Schema's does
    not. The enforced regex is anchored with ``\\A``/``\\Z`` for that reason,
    and this asserts the two agree rather than assuming it."""
    import re as _re

    published = _re.compile(contract.IDENTIFIER_PATTERN)
    probes = [
        "R1", "a", "R1.a:b-c_d", "R" * 64, "R" * 65, "", " R1", "R1 ", "_R1",
        "R1\n", "R1\nx", "R1\r", "R1\x00", ".control", "R1;x", "R1/x",
    ]
    for probe in probes:
        enforced_ok = True
        try:
            contract.require_identifier(probe, "probe")
        except contract.ExternalRequestRefused:
            enforced_ok = False
        json_schema_ok = bool(
            published.match(probe) and "\n" not in probe and "\r" not in probe
        )
        assert enforced_ok == json_schema_ok, probe


def test_the_published_schema_states_the_difference_constraint(monkeypatch):
    """The falsifier's C-5, and the drift guard that could not have caught it.

    The first form published one shared quantity fragment saying "any
    dimensionally compatible unit" — false of ``tolerance``, where a
    dimensionally compatible affine unit is refused. A name-level drift check
    is structurally unable to see a wrong *constraint*, so this one reads the
    call sites: every ``parse_quantity(..., difference=True)`` must have a
    schema entry that says so, and every ``difference=False`` must not.
    """
    import ast as _ast

    source = (APPLICATION_DIR / "executions" / "electrothermal_series.py").read_text(
        encoding="utf-8"
    )
    differences = set()
    values = set()
    for node in _ast.walk(_ast.parse(source)):
        if isinstance(node, _ast.Call) and getattr(node.func, "id", "") == (
            "parse_quantity"
        ):
            flag = next(
                (k.value.value for k in node.keywords if k.arg == "difference"),
                None,
            )
            where = next(
                (k.value for k in node.keywords if k.arg == "where"), None
            )
            label = getattr(where, "value", "")
            (differences if flag else values).add(label)
    # Exactly one difference-valued field exists, and it is the tolerance.
    assert differences == {"request.coupling.tolerance"}
    assert values

    body = describe.request_json_schema()["allOf"][0]["then"]["properties"]
    tolerance = body["coupling"]["properties"]["tolerance"]
    assert "REFUSED" in tolerance["properties"]["unit"]["description"]
    assert "ratio-scale" in tolerance["properties"]["unit"]["description"]
    seed = body["coupling"]["properties"]["seed_temperature"]
    assert "REFUSED" not in seed["properties"]["unit"]["description"]


def test_a_difference_field_cannot_be_added_without_answering_the_question():
    """``parse_quantity``'s ``difference`` has no default, so the unsafe answer
    is never the silent one."""
    import inspect

    parameter = inspect.signature(contract.parse_quantity).parameters["difference"]
    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_the_projection_refuses_to_understate_a_computation():
    """The falsifier's C-4. ``project_run`` is domain-neutral and reads only a
    ``CoupledRun``, so it cannot rely on the wired consumer being scalar. A
    result carrying bulk data has no representation in this response, and
    DATA-BOUNDARY0's own rule is that loud failure beats silent understatement.
    """
    from engcore.scientific.errors import ScientificCoreError
    from engcore.scientific.results.data_reference import ScientificDataReference
    from engcore.scientific.results.result import ScientificResult
    import dataclasses

    request = canonical_request()
    prepared = ets.prepare(request["inputs"], request["coupling"], "native")
    run = prepared.run("bulk-probe")
    assert project_run_ok(run)

    reference = ScientificDataReference(
        name="phi", unit="kelvin", count=4096, dtype="float64",
        digest="0" * 64, digest_algorithm="sha256",
    )
    victim = run.final.results[0]
    poisoned = dataclasses.replace(victim, data_references=(reference,))
    iteration = dataclasses.replace(
        run.final,
        results=(poisoned,) + tuple(run.final.results[1:]),
    )
    doctored = dataclasses.replace(run, iterations=run.iterations[:-1] + (iteration,))
    with pytest.raises(ScientificCoreError, match="bulk data"):
        contract.project_run(doctored)


def project_run_ok(run) -> bool:
    contract.project_run(run)
    return True


# =====================================================================
# Reduction attacks — what was deleted, asserted absent
# =====================================================================

def test_r3_no_application_service_class_exists():
    """It would have held no state. A namespace with a constructor is not an
    abstraction."""
    for path, source in _sources(APPLICATION_DIR):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ClassDef):
                assert "Service" not in node.name, (path.name, node.name)
                assert "Manager" not in node.name, (path.name, node.name)
                assert "Registry" not in node.name, (path.name, node.name)
                assert "Factory" not in node.name, (path.name, node.name)


def test_r5_neither_transport_defines_an_error_type():
    """The boundary never raises for a caller-caused condition, so a transport
    error type would have nothing to carry."""
    for directory in (HTTP_DIR, MCP_DIR):
        for path, source in _sources(directory):
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.ClassDef):
                    bases = {
                        b.id for b in node.bases if isinstance(b, ast.Name)
                    }
                    assert not bases & {"Exception", "BaseException"}, node.name


def test_r6_an_execution_profile_is_a_dict_key_and_not_a_record():
    for path, source in _sources(APPLICATION_DIR):
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ClassDef):
                assert node.name not in {
                    "ExecutionProfile", "CapabilityResponse", "TransportError",
                    "ProviderRegistry", "ExecutionOutcome", "JobRecord",
                }, node.name


def test_r4_no_capabilities_surface_exists():
    """Deleted from both transports. The refusal names the admissible set."""
    from crafty_mcp import TOOLS

    assert [tool["name"] for tool in TOOLS] == ["crafty_run"]
    http = (HTTP_DIR / "server.py").read_text(encoding="utf-8")
    tree = ast.parse(http)
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    routes = {value for value in literals if value.startswith("/v0")}
    assert routes == {"/v0/run"}


def test_r9_the_status_vocabulary_is_three_words_and_none_of_them_is_success():
    source = (APPLICATION_DIR / "service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert {"executed", "refused", "execution_failed"} <= literals
    assert "success" not in literals
    assert "ok" not in literals
    assert "failed" not in literals


def test_the_failure_taxonomy_has_no_generic_error_member():
    codes = {member.value for member in RefusalCode}
    assert len(codes) == 8
    assert "error" not in codes
    assert "failure" not in codes
    assert "unknown" not in codes
    # Non-convergence is deliberately NOT a refusal code.
    assert not any("converg" in code for code in codes)


def test_the_http_status_map_is_total_over_the_taxonomy():
    from crafty_http import STATUS_FOR_CODE

    assert set(STATUS_FOR_CODE) == {member.value for member in RefusalCode}
    # And a non-convergent run has no entry, because it is not a refusal.
    assert 200 not in STATUS_FOR_CODE.values()


def test_the_provider_profile_resolves_to_a_callable_without_running_anything(
    monkeypatch,
):
    """Resolution must not be a latent import error — and must not execute.

    This caught a real defect: the resolver's relative import was one level
    too deep, so every provider request classified as
    ``unclassified_internal_failure`` with ``ImportError`` instead of running.
    The cross-process test would have found it; nothing in-process would have.
    """
    spies = _Spies(monkeypatch)
    solver = ets.PROFILES["ngspice"]()
    assert callable(solver)
    assert spies.process == 0


def test_a_provider_failure_is_classified_as_one_not_as_a_crafty_defect(
    monkeypatch,
):
    """(E) in the taxonomy, in process and without launching anything.

    The domain deliberately made provider errors NOT ScientificCoreError, so
    "the provider was not installed" can never read as "the science does not
    hold". The boundary honours that split by asking the execution which
    failures mean a provider broke — it names no provider itself.
    """
    from engcore.domains.electrical import ngspice as provider

    def explode(self, netlist):
        raise provider.NgspiceExecutionFailure("the provider exited 1")

    monkeypatch.setattr(provider.NgspiceInvocation, "run", explode)
    monkeypatch.setattr(
        provider.NgspiceInvocation, "probe_version", lambda self: "42"
    )
    response = handle(canonical_request(execution_profile="ngspice"))
    assert response["status"] == "execution_failed"
    assert (
        response["refusal"]["code"] == RefusalCode.PROVIDER_EXECUTION_FAILED.value
    )
    assert response["refusal"]["error_type"] == "NgspiceExecutionFailure"
    # Not a scientific verdict of any kind.
    assert response["result"] is None
    text = json.dumps(response)
    for forbidden in ("criterion_met", "outcome", "validation_status"):
        assert forbidden not in text, forbidden


def test_the_universal_layer_names_no_provider_when_classifying():
    """The classifier asks the execution; it does not know a provider's name."""
    code = _code_only((APPLICATION_DIR / "service.py").read_text(encoding="utf-8"))
    assert "ngspice" not in code
    assert "sys.modules" not in code
    assert callable(ets.provider_failure_types)


def test_the_native_profile_never_imports_the_provider_module():
    """Executed in a fresh interpreter, because in this one the provider
    module may already be loaded by another test."""
    script = (
        "import sys, json;"
        "sys.path.insert(0, 'src');"
        "from engcore.application import handle;"
        f"request = {canonical_request()!r};"
        "response = handle(request);"
        "print(json.dumps({"
        "'status': response['status'],"
        "'provider_loaded': 'engcore.domains.electrical.ngspice' in sys.modules,"
        "}))"
    )
    done = subprocess.run(
        [sys.executable, "-c", script], cwd=str(REPO_ROOT),
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(done.stdout.strip().splitlines()[-1])
    assert payload["status"] == "executed"
    assert payload["provider_loaded"] is False
