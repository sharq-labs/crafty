"""ADMISSION-GATE-REPAIR — the evidence.

`TRUST-HARDENING` preregistered enforcement point (a) — numerical-validation
admission inside the loop, in the three executors of
``systems/electrothermal/coupled.py`` — and its evidence document published it as
shipped. It was never written: ``grep -rn require_admission
src/engcore/systems/electrothermal/`` returned nothing at `31ddcc7`.

The test that was supposed to record the gate's behaviour,
``test_trust_hardening.py::test_p1_7``, derived its requirement set from the checks
that had run, so it asserted "every check that ran, ran" and could not tell a
present gate from an absent one.

**The refusal tests — c, d, e, f — fail when the gate is removed, and `test_h`
proves that by removing it rather than asserting it.** The others do different
jobs and the distinction is stated rather than blurred: `test_a` and `test_b` pin
the requirement sets, and `test_g` records that the gate is inert on the shipped
sweep. `test_g` is not sensitive to the gate's *presence* — nothing that asserts
inertness can be — but unlike the assertion it replaces it does fail when a
declared requirement goes absent.

See `docs/evidence/admission-gate-repair-preregistration.md`.
"""
from __future__ import annotations

import copy
import dataclasses

import pytest

from engcore.application.executions import electrothermal_series as ets
from engcore.domains.electrical import material as mat
from engcore.domains import thermal_lumped as lump
from engcore.scientific.errors import ScientificValidationError
from engcore.scientific.results.validation import (
    ValidationCheck,
    ValidationOutcome,
    ValidationReport,
)
from engcore.systems.electrothermal import coupled as etc

from test_api_mcp_v0 import canonical_request


NOMINAL_VOLTS = 5.0

#: The operating points that RUN. TRUST-HARDENING's §2.2 table records the
#: iteration count at 9.0/10.0/10.6/11.0 V. The three points above these —
#: 12.0, 24.0, 48.0 V — are deliberately absent: they are refused by
#: enforcement point (b), applicability, before the numerical gate's inertness
#: is observable, and `test_trust_hardening.py` already covers that refusal.
SWEEP = (5.0, 9.0, 10.0, 10.6, 11.0, 11.5)


#: Which declared set governs which problem. Literals, matched by prefix, so a
#: result can never select its own requirements. Every executor is covered:
#: an unmatched problem_id raises rather than being skipped.
REQUIRED_BY_PREFIX = {
    "resistance-tcr": etc.PROPERTY_ADMISSION_REQUIREMENTS,
    "thermal-lumped": etc.THERMAL_ADMISSION_REQUIREMENTS,
    "electrical_dc:": frozenset({
        "dimensional_consistency",
        "linear_system_residual",
        "kirchhoff_current_law",
        "resistor_metric_consistency",
        "voltage_source_relation",
        "power_balance",
    }),
}


def _required_for(problem_id: str) -> frozenset[str]:
    for prefix, names in REQUIRED_BY_PREFIX.items():
        if problem_id.startswith(prefix):
            return names
    raise AssertionError(
        f"no declared requirement set governs {problem_id!r}; a new executor was "
        f"added and this test would otherwise have skipped it silently"
    )



def _prepared(volts: float):
    request = copy.deepcopy(canonical_request())
    request["inputs"]["source_voltage"]["value"] = volts
    return ets.prepare(
        request["inputs"], request["coupling"], request["execution_profile"]
    )


def _run(volts: float, run_id: str, circuit_solver=None):
    prepared = _prepared(volts)
    return etc.run_admitted_coupling(
        prepared.system,
        prepared.plan,
        run_id=run_id,
        circuit_solver=circuit_solver or prepared.circuit_solver,
    )


def _withhold(report: ValidationReport, name: str) -> ValidationReport:
    """The declared check exists but did not run.

    NOT_RUN rather than FAIL deliberately, following
    ``tests/domains/fluids/test_transport2d.py:464-491``: ``status`` does not flip
    to FAIL and ``is_usable`` stays True, so anything that passes here is passing
    because of ``require_admission`` and not because of a cheaper aggregate check.
    """
    assert any(c.name == name for c in report.checks), (
        f"{name!r} is not emitted by this solver; the test is testing nothing"
    )
    return ValidationReport(
        checks=tuple(
            ValidationCheck(
                name=c.name,
                outcome=ValidationOutcome.NOT_RUN if c.name == name else c.outcome,
                detail=c.detail,
                establishes=c.establishes,
            )
            for c in report.checks
        ),
        notes=f"{name} deliberately withheld",
    )


# =====================================================================
# The requirement sets are declared, not observed
# =====================================================================

def test_a_the_requirement_sets_are_literal_and_name_checks_that_exist():
    """The anti-tautology guard.

    `test_p1_7` failed because its requirement set was `{c.name for c in
    report.checks}` — derived from the result under test. These sets are literals,
    fixed before the run, and each names a check the solver actually emits.
    """
    assert etc.PROPERTY_ADMISSION_REQUIREMENTS == frozenset(
        {"resistance_strictly_positive"}
    )
    assert etc.THERMAL_ADMISSION_REQUIREMENTS == frozenset(
        {"lumped_balance_residual"}
    )

    run = _run(NOMINAL_VOLTS, run_id="a").run
    emitted = {
        c.name for result in run.final.results for c in result.validation.checks
    }
    for required in (
        etc.PROPERTY_ADMISSION_REQUIREMENTS | etc.THERMAL_ADMISSION_REQUIREMENTS
    ):
        assert required in emitted, (
            f"{required!r} is declared but no solver emits it — the gate would be "
            f"unsatisfiable, not inert"
        )


def test_b_the_electrical_gate_uses_the_producer_published_set():
    """Not consumer-invented: `build_dc_problem` publishes six requirements and
    the circuit result is gated against those, unmodified."""
    prepared = _prepared(NOMINAL_VOLTS)
    problems = etc.coupled_problems(
        prepared.system,
        {stage.component_id: stage.conductor.reference_resistance
         for stage in prepared.system.stages},
    )
    electrical = next(
        p for p in problems if p.problem_id.startswith("electrical_dc:")
    )
    assert electrical.validation_requirements == frozenset({
        "dimensional_consistency",
        "linear_system_residual",
        "kirchhoff_current_law",
        "resistor_metric_consistency",
        "voltage_source_relation",
        "power_balance",
    })


# =====================================================================
# Each of the three executors refuses a withheld requirement
# =====================================================================

@pytest.mark.parametrize("requirement", sorted(REQUIRED_BY_PREFIX["electrical_dc:"]))
def test_c_a_circuit_result_missing_a_declared_check_is_refused(requirement):
    """Through the shipped substitution seam — no monkeypatching.

    ``circuit_solver`` is a published seam (`API-MCP-V0`). A substitute that
    returns a result whose declared requirement never ran must be refused before
    its voltage is transported.

    **Parametrized over all six, and the reason is this milestone's own subject.**
    An adversarial round found that withholding only one or two of them left a
    suite that could not distinguish the shipped gate from one enforcing a
    *subset* — a gate silently narrowed to two names would have passed. That is
    the same species of defect as the test this milestone exists to replace, so
    every declared requirement is withheld in turn.
    """
    def withholding_solver(circuit, run_id):
        result = etc.native_circuit_solver(circuit, run_id)
        return dataclasses.replace(
            result,
            validation=_withhold(result.validation, requirement),
        )

    with pytest.raises(ScientificValidationError) as excinfo:
        _run(NOMINAL_VOLTS, run_id=f"c-{requirement}",
             circuit_solver=withholding_solver)
    assert requirement in str(excinfo.value)
    assert "electrothermal circuit result" in str(excinfo.value)


def test_d_a_property_result_missing_its_declared_check_is_refused(monkeypatch):
    real = mat.ResistancePropertySolver.validate

    def withholding(self, prepared, raw):
        return _withhold(real(self, prepared, raw), "resistance_strictly_positive")

    monkeypatch.setattr(mat.ResistancePropertySolver, "validate", withholding)
    with pytest.raises(ScientificValidationError) as excinfo:
        _run(NOMINAL_VOLTS, run_id="d")
    assert "resistance_strictly_positive" in str(excinfo.value)
    assert "electrothermal property result" in str(excinfo.value)


def test_e_a_thermal_result_missing_its_declared_check_is_refused(monkeypatch):
    real = lump.LumpedThermalSolver.validate

    def withholding(self, prepared, raw):
        return _withhold(real(self, prepared, raw), "lumped_balance_residual")

    monkeypatch.setattr(lump.LumpedThermalSolver, "validate", withholding)
    with pytest.raises(ScientificValidationError) as excinfo:
        _run(NOMINAL_VOLTS, run_id="e")
    assert "lumped_balance_residual" in str(excinfo.value)
    assert "electrothermal body result" in str(excinfo.value)


def test_f_the_refusal_transports_nothing():
    """A refused sub-solve stops the loop; no partial run is handed back."""
    def withholding_solver(circuit, run_id):
        result = etc.native_circuit_solver(circuit, run_id)
        return dataclasses.replace(
            result,
            validation=_withhold(result.validation, "kirchhoff_current_law"),
        )

    with pytest.raises(ScientificValidationError):
        _run(NOMINAL_VOLTS, run_id="f", circuit_solver=withholding_solver)


# =====================================================================
# The gate is inert on every shipped operating point — P-3
# =====================================================================

def test_g_the_gate_fires_on_none_of_the_swept_runs():
    """The honest form of the claim `test_p1_7` was written to make.

    Three properties the superseded assertion did not have, each of which it was
    measured to lack:

    * the requirement set is a **literal**, never re-derived from the result;
    * a declared requirement that is **absent** from the report fails this test —
      the original's derived set shrank with the missing check and stayed silent;
    * the **electrical** executor is covered, not skipped.
    """
    seen = set()
    for volts in SWEEP:
        run = _run(volts, run_id=f"g-{volts}").run
        assert run.final.results, f"no results at {volts} V"
        for result in run.final.results:
            declared = _required_for(result.problem_id)
            seen.add(result.problem_id.split(":")[0].split("-")[0])
            passing = {
                c.name for c in result.validation.checks
                if c.outcome is ValidationOutcome.PASS
            }
            missing = declared - passing
            assert not missing, (
                f"at {volts} V, {result.problem_id} declares {sorted(missing)} "
                f"which is absent or not passing — the gate would have refused "
                f"this run, and it is reported as inert"
            )
    assert seen >= {"resistance", "electrical_dc", "thermal"}, (
        f"the sweep did not exercise all three executors: {sorted(seen)}"
    )


# =====================================================================
# The proof that these tests can fail — P-4 / P-5
# =====================================================================

def test_h_every_test_above_depends_on_the_gate(monkeypatch):
    """Proven by removal, not by inspection.

    With ``require_admission`` stubbed to a no-op, the withheld requirement is
    transported and nothing raises. `PROPULSION0-EXT` round 2 found its own spy
    inert — six assertions no implementation could violate — so this milestone
    proves the opposite property by construction.
    """
    monkeypatch.setattr(
        ValidationReport, "require_admission", lambda self, req, *, context="": None
    )

    def withholding_solver(circuit, run_id):
        result = etc.native_circuit_solver(circuit, run_id)
        return dataclasses.replace(
            result,
            validation=_withhold(result.validation, "power_balance"),
        )

    # No raise: the gate is what test_c depends on, and it is gone.
    admitted = _run(NOMINAL_VOLTS, run_id="h", circuit_solver=withholding_solver)
    assert admitted.run.final.results, (
        "with the gate stubbed the run must complete — if it still refuses, the "
        "refusal came from somewhere else and test_c proves less than it claims"
    )
