"""TRUST-HARDENING — the preregistered predictions, measured.

Preregistration: ``docs/evidence/trust-hardening-preregistration.md``, committed
alone at `437b2b8` before any source change.

The milestone creates no validation concept. It enforces that three concepts
which already exist stay separate and cannot be bypassed on the one execution a
consumer can reach:

    numerical validation    did the computation execute correctly?
    scientific applicability  is the model valid at this physical condition?
    operational safety      is the result fit for use?              (NOT BUILT)

The third has no declarer anywhere in the tree and none is invented here.

Every test below is named for the prediction it measures, so a failure names the
claim it refutes rather than only the assertion that broke.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest

from engcore.application import handle
from engcore.application.executions import electrothermal_series as ets
from engcore.coupling import CoupledRun
from engcore.domains.electrical import material as mat
from engcore.scientific.errors import ScientificValidationError
from engcore.scientific.models.definition import ValidityStatus
from engcore.systems import electrothermal as et
from engcore.systems.electrothermal import coupled as etc

from test_api_mcp_v0 import canonical_request

KELVIN = "kelvin"

#: The declared fit range of `LINEAR_TCR_MODEL`. A MODEL VALIDITY bound, not a
#: device rating: nothing in the tree declares what this resistor may survive.
LIMIT = mat.TCR_MAX_TEMPERATURE.magnitude_in(KELVIN)


def _request(volts: float) -> dict:
    request = copy.deepcopy(canonical_request())
    request["inputs"]["source_voltage"]["value"] = volts
    return request


def _prepared(volts: float):
    request = _request(volts)
    return ets.prepare(
        request["inputs"], request["coupling"], request["execution_profile"]
    )


def _admitted(volts: float, run_id: str = "th"):
    prepared = _prepared(volts)
    return etc.run_admitted_coupling(
        prepared.system,
        prepared.plan,
        run_id=run_id,
        circuit_solver=prepared.circuit_solver,
    )


def _converged_kelvin(run: CoupledRun) -> float:
    (value,) = run.final_values.values()
    return value.magnitude_in(KELVIN)


# =====================================================================
# §0 — the concept separation the ruling requires. F1, F2, F4.
# =====================================================================

def test_f1_no_validation_check_carries_an_applicability_verdict():
    """The applicability verdict never becomes a `ValidationCheck`.

    The status values are the discriminator: if a verdict had been mapped into a
    check, one of these three strings would appear as a check name or detail.
    """
    forbidden = {status.value for status in ValidityStatus}
    for volts in (5.0, 24.0):
        admitted = _admitted(volts, run_id=f"f1-{volts}")
        for result in admitted.run.final.results:
            for check in result.validation.checks:
                assert check.name != "model_applicability"
                assert not forbidden & {check.detail}
                assert "validity" not in check.name


def test_f2_the_solver_report_is_unwidened_and_c4_still_holds():
    """`ResistancePropertySolver.validate` emits exactly what it always did.

    `test_min_foundation_electrothermal.py::test_c4_validity_and_validation_are_kept_apart`
    asserts this for the solver at 600 K and passes unmodified. This is its
    sibling, asserted after the milestone, so "the solver did not start claiming
    applicability" is measured here rather than inferred from that test's silence.
    """
    from engcore.scientific.units.quantity import Quantity

    conductor = _prepared(5.0).system.stages[0].conductor
    problem = mat.build_resistance_problem(conductor)
    solver = mat.ResistancePropertySolver()
    solver.bind_conductor(
        conductor, problem.problem_id, temperature=Quantity(600.0, KELVIN)
    )
    prepared = solver.prepare(problem)
    report = solver.validate(prepared, solver.solve(prepared))

    assert {check.name for check in report.checks} == {"resistance_strictly_positive"}
    # 600 K is outside the declared domain and the solver still passes: the two
    # questions are different and the record keeps them different.
    assert mat.assess_resistance_validity(
        problem, Quantity(600.0, KELVIN)
    ).status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN


@pytest.mark.parametrize("volts", [5.0, 12.0, 24.0])
def test_f4_validation_semantics_do_not_depend_on_applicability(volts):
    """P1-4. `is_usable`, `status` and `attained_levels` never move.

    A result that is numerically fine but scientifically inapplicable keeps
    ``is_usable == True`` **on its own record**. That is not a bug to repair; it
    is the separation working. Admission is what refuses it, and admission is
    somewhere else.
    """
    admitted = _admitted(volts, run_id=f"f4-{volts}")
    for result in admitted.run.final.results:
        assert result.is_usable is True
        assert result.validation.status.value == "pass"


# =====================================================================
# P1 — admission enforcement
# =====================================================================

@pytest.mark.parametrize(
    "volts, admitted_expected",
    [(5.0, True), (10.0, True), (11.5, True), (12.0, False), (24.0, False)],
)
def test_p1_1_the_shipped_path_refuses_an_inapplicable_result(volts, admitted_expected):
    """P1-1. The whole milestone, measured at the public boundary."""
    response = handle(_request(volts))
    if admitted_expected:
        assert response["status"] == "executed"
        assert response["result"] is not None
        assert response["result"]["model_validity"]["assessed"] is True
    else:
        assert response["status"] == "execution_failed"
        assert response["result"] is None
        assert response["refusal"]["code"] == "scientific_admission_refused"


def test_p1_2_the_transition_is_monotone_and_where_it_was_predicted():
    """P1-2. Strictly between 11.5 V and 12.0 V, and it flips exactly once.

    Preregistered from the transported temperature crossing 450 K between
    449.111 K and 458.665 K — derived before the guard was written, not read off
    the implementation afterwards.
    """
    volts = [8.0, 9.0, 10.0, 10.5, 11.0, 11.5, 11.9, 12.0, 13.0, 24.0]
    refused = [bool(_admitted(v, run_id=f"p12-{v}").inapplicable) for v in volts]

    assert refused == sorted(refused), "the verdict must not oscillate"
    assert refused[volts.index(11.5)] is False
    assert refused[volts.index(12.0)] is True
    assert refused.count(False) + refused.count(True) == len(volts)


def test_p1_3_admission_changes_no_number_on_an_admitted_run():
    """P1-3. The guard costs nothing on the honest path.

    The assessed path and the original unassessed one are run side by side and
    compared as serialized records: every value, every provenance entry, every
    check. Bit-identical, not approximately equal.
    """
    prepared = _prepared(5.0)
    plain = etc.run_fixed_point_coupling(
        prepared.system, prepared.plan, run_id="same",
        circuit_solver=prepared.circuit_solver,
    )
    assessed = etc.run_admitted_coupling(
        prepared.system, prepared.plan, run_id="same",
        circuit_solver=prepared.circuit_solver,
    )
    assert json.dumps(assessed.run.to_dict(), sort_keys=True) == json.dumps(
        plain.to_dict(), sort_keys=True
    )


def test_p1_5_a_refused_run_still_constructs_serializes_and_reads():
    """P1-5. A failed run is still evidence.

    This is the constraint that makes admission opt-in at construction, and it
    survives the milestone intact: refusal happens at the point of TRANSPORT on
    the shipped path, never at the point of construction.
    """
    admitted = _admitted(24.0, run_id="refused")
    assert admitted.inapplicable == ("R1",)

    with pytest.raises(ScientificValidationError, match="admission refused"):
        et.require_coupled_admission(admitted)

    # ...and everything is still there and still readable.
    restored = CoupledRun.from_dict(json.loads(json.dumps(admitted.run.to_dict())))
    assert _converged_kelvin(restored) == _converged_kelvin(admitted.run)
    assert restored.final.results[0].values


def test_p1_6_a_scientific_refusal_is_classified_as_one():
    """P1-6. 422, not 500.

    `crafty_http` documents 500 as "the caller did nothing wrong ... nothing
    scientific is claimed". Both halves are false for this refusal: the science
    ran, and Crafty declined to hand over its answer.
    """
    from crafty_http.server import STATUS_FOR_CODE

    response = handle(_request(24.0))
    code = response["refusal"]["code"]
    assert code == "scientific_admission_refused"
    assert response["refusal"]["stage"] == "execution"
    assert STATUS_FOR_CODE[code] == 422


def test_p1_7_numerical_admission_fires_on_none_of_the_swept_runs():
    """P1-7. Enforcement point (a) is defence in depth, and this says so.

    Recorded because a milestone that implied its numerical gate carried the
    result would be overstating what it measured. Every declared requirement on
    the exposed path is satisfied at every swept operating point; what the gate
    buys is that a future failure is refused by the producer instead of
    transported.
    """
    for volts in (5.0, 10.0, 12.0, 24.0):
        admitted = _admitted(volts, run_id=f"p17-{volts}")
        for result in admitted.run.final.results:
            assert result.validation.admission_issues(
                {check.name for check in result.validation.checks}
            ) == ()


def test_p1_8_the_residue_the_verdict_does_not_cover():
    """P1-8. Preregistered limitation, measured rather than discovered later.

    The coupling transports `final_temperature`; the response also publishes
    `steady_state_temperature`. At 11.0 V the model was only ever evaluated
    INSIDE its declared range — so the verdict is correctly `in_domain` — while
    the published steady state sits outside it. The published value is an
    extrapolation beyond the state that was coupled.

    Not closed here: closing it means asserting one model's validity range
    against another model's reported output, which conflates two domains. Named
    so the milestone is not read as total coverage.
    """
    admitted = _admitted(11.0, run_id="residue")
    assert admitted.inapplicable == ()
    assert _converged_kelvin(admitted.run) < LIMIT

    steady = next(
        result.values["steady_state_temperature"].magnitude_in(KELVIN)
        for result in admitted.run.final.results
        if "steady_state_temperature" in result.values
    )
    assert steady > LIMIT


# =====================================================================
# P2 — reproducibility lock
# =====================================================================

def test_p2_3_the_scientific_environment_is_recorded_on_every_participant():
    """P2-3. The field existed, was serialized, and no producer filled it."""
    admitted = _admitted(5.0, run_id="env")
    assert admitted.run.final.results
    for result in admitted.run.final.results:
        environment = result.provenance.environment
        assert environment, result.problem_id
        assert set(environment) >= {"python", "numpy", "scipy", "blas_architecture"}


def test_p2_3_the_environment_is_recoverable_records_only():
    """P2-3. A fresh process, importing no engcore module, reads the stack.

    Version strings alone would not have been enough. The baseline that drifted
    did so at a byte-identical version tuple; `blas_architecture` is the only
    field in the whole stack that tracks the axis that actually moved.
    """
    blob = json.dumps(_admitted(5.0, run_id="env2").run.to_dict())
    child = subprocess.run(
        [sys.executable, "-c", (
            "import json, sys\n"
            "payload = json.loads(sys.stdin.read())\n"
            "seen = [r['provenance'].get('environment') or {}\n"
            "        for it in payload['iterations'] for r in it['results']]\n"
            "print(json.dumps({\n"
            "    'engcore_modules': [m for m in sys.modules if 'engcore' in m],\n"
            "    'blas': sorted({e.get('blas_architecture','') for e in seen if e}),\n"
            "    'numpy': sorted({e.get('numpy','') for e in seen if e}),\n"
            "}))\n"
        )],
        input=blob, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    recovered = json.loads(child.stdout)
    assert recovered["engcore_modules"] == []
    assert recovered["numpy"] and all(recovered["numpy"])
    assert len(recovered["blas"]) == 1


def test_p2_4_recording_the_environment_changed_no_number():
    """P2-4. Provenance is not an input to any computation."""
    admitted = _admitted(5.0, run_id="p24")
    # The value COUPLING-PACK-RELOCATION froze for this composition, asserted
    # here as the band `_BASELINE_REL` declares rather than as an exact double.
    assert _converged_kelvin(admitted.run) == pytest.approx(
        338.5770175652607, rel=1e-13
    )


# =====================================================================
# P3 — execution identity
# =====================================================================

def test_p3_1_two_runs_of_one_execution_differ_in_their_declaration():
    """P3-1. Not only in their numbers.

    Before this, a consumer holding two responses could see that the answers
    differed and could not see that the questions had.
    """
    five, ten = handle(_request(5.0)), handle(_request(10.0))

    def electrical(response):
        return next(
            participant
            for participant in response["result"]["participants"]
            if participant["problem_id"].startswith("electrical_dc:")
        )

    assert electrical(five)["inputs"] != electrical(ten)["inputs"]
    assert electrical(five)["inputs"]["Vs:V1"] == {"value": 5.0, "unit": "volt"}
    assert electrical(ten)["inputs"]["Vs:V1"] == {"value": 10.0, "unit": "volt"}


def test_p3_2_the_projection_is_additive_and_names_what_was_checked():
    """P3-2. Every previously published key keeps its meaning."""
    participant = handle(_request(5.0))["result"]["participants"][0]
    assert {
        "problem_id", "numerical_convergence", "validation_status",
        "attained_levels", "models", "solver", "inputs", "checks",
    } == set(participant)

    electrical = next(
        p for p in handle(_request(5.0))["result"]["participants"]
        if p["problem_id"].startswith("electrical_dc:")
    )
    names = {check["name"] for check in electrical["checks"]}
    assert "power_balance" in names
    assert all(check["outcome"] == "pass" for check in electrical["checks"])
