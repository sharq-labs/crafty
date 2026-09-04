"""The external request and response contracts, and the projection between them.

Two versioned schema strings, both owned here and **neither reusing a
Scientific Core or coupling name**:

* ``crafty_execution_request/1``
* ``crafty_execution_response/1``

Why these are not the internal records
--------------------------------------
`COUPLING-PACK-RELOCATION` recorded that every remaining naming and shape
question about ``coupling_fixed_point_run/1`` is currently free **because zero
payloads exist**, and that this is a decaying fact: the first stored payload
converts each of them into a migration. Publishing that record as an external
API response is the mass production of stored payloads by parties Crafty cannot
migrate. It would also weld the external contract to a record whose own
documentation still carries an unresolved split — topology and execution policy
in one object — that a sibling project (preCICE) had to break its public
configuration format to repair.

So the external contract carries **its own identity**, and the internal records
stay free to move. Nothing reads the projection back, so the bidirectional
lossless round-tripping cost that made Kubernetes reconsider its own
internal/external split is not incurred here.

What the projection deliberately loses
--------------------------------------
Per-iteration participant results. One converged nominal run serializes to
**162 106 bytes** internally, dominated by every iteration's full
``ScientificResult`` set; that is ``O(iterations x results)`` inline data, which
`DATA-BOUNDARY0` refuses on principle. The external response carries the
iterate-change history (one scalar per sweep) and the final iteration's values.
A caller needing per-iteration detail uses Direct Python. **Adding a field later
is additive; removing a published one is not.**

The five distinctions this contract exists to keep apart
--------------------------------------------------------
.. code-block:: text

    TRANSPORT SUCCESS != EXECUTION SUCCESS != NUMERICAL CONVERGENCE
                      != COUPLING CONVERGENCE != SCIENTIFIC VALIDITY

``status`` states only the second. It is never a boolean and never the word
*success*. Transport success lives in the HTTP status line and the JSON-RPC
envelope, **outside this payload**. Numerical convergence is per participant.
Coupling convergence is one field the loop alone writes. Scientific validity is
reported as *not assessed*, because the executed path does not assess it — and
``NOT_RUN != PASS``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from ..coupling import CoupledRun, is_ratio_scale
from ..scientific.errors import UnitCompatibilityError
from ..scientific.results.result import ScientificResult
from ..scientific.results.uncertainty import Uncertainty
from ..scientific.units.quantity import Quantity

__all__ = [
    "MAX_ITERATION_BUDGET",
    "MAX_REQUEST_BYTES",
    "MAX_STAGES",
    "REQUEST_SCHEMA",
    "RESPONSE_SCHEMA",
    "ExecutionRequest",
    "ExternalRequestRefused",
    "RefusalCode",
    "parse_quantity",
    "parse_request",
    "project_run",
    "require_object",
    "require_exact_keys",
]

#: Deliberately *not* built with ``schema_string``: that helper belongs to the
#: Scientific Core's record family and these two strings are not members of it.
#: A reader must never be able to mistake an external envelope for a core record.
REQUEST_SCHEMA = "crafty_execution_request/1"
RESPONSE_SCHEMA = "crafty_execution_response/1"

#: Bounds. An external caller may not choose an unbounded amount of work.
#: These are refusals, not clamps: silently reducing a caller's budget would
#: change the science being asked for without saying so.
MAX_ITERATION_BUDGET = 200
MAX_STAGES = 8
MAX_REQUEST_BYTES = 262_144


class RefusalCode(str, Enum):
    """The external failure taxonomy. Eight cases, none collapsed to "error".

    Two of the eight are **not** members here, deliberately:

    * *coupling did not converge* is not a refusal at all. It is a successful
      execution whose ``coupling.outcome`` says so.
    * *transport failure* is not a member either. It has no scientific meaning
      and lives entirely in the transport's own framing.
    """

    #: (A) the document is not an interpretable request
    MALFORMED_REQUEST = "malformed_request"
    #: (B) the document announces a schema this reader does not implement
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    #: (D) the named execution is not one this deployment exposes
    UNKNOWN_EXECUTION = "unknown_execution"
    #: (D) the named execution profile is not in the closed enumeration
    UNKNOWN_EXECUTION_PROFILE = "unknown_execution_profile"
    #: (C) Crafty refused the science before executing any of it
    SCIENTIFIC_ADMISSION_REFUSED = "scientific_admission_refused"
    #: (E) an external provider process failed. Not a scientific verdict.
    PROVIDER_EXECUTION_FAILED = "provider_execution_failed"
    #: (F) a sub-solve raised during the coupling iteration
    SUBSOLVER_EXECUTION_FAILED = "subsolver_execution_failed"
    #: the classifier's total default. A Crafty defect, said out loud.
    UNCLASSIFIED_INTERNAL_FAILURE = "unclassified_internal_failure"


class ExternalRequestRefused(Exception):
    """The request *document* could not be interpreted.

    **One new exception class, and it carries a fact no existing Crafty error
    carries.** ``ScientificCoreError`` and its subclasses all mean *the science
    was refused*; ``NgspiceProviderError`` means *the provider broke*. Neither
    can say *this JSON is not a request*, which is a statement about a document
    and not about any science. Reusing ``InvalidScientificProblem`` for it would
    report a typo in a field name as a scientific refusal.

    It never crosses the boundary: :func:`~engcore.application.service.handle`
    catches it and returns a refusal payload.
    """

    def __init__(self, code: RefusalCode, detail: str) -> None:
        super().__init__(detail)
        self.code = RefusalCode(code)
        self.detail = str(detail)


# =====================================================================
# Parsing — structural, allowlisted, and loud
# =====================================================================

def require_object(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} must be an object, got {type(value).__name__}",
        )
    for key in value:
        if not isinstance(key, str):
            raise ExternalRequestRefused(
                RefusalCode.MALFORMED_REQUEST,
                f"{where} has a non-string key {key!r}",
            )
    return value


def require_exact_keys(
    payload: Mapping[str, Any],
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    where: str,
) -> None:
    """Allowlist, both ways. **Unknown keys are refused, never dropped.**

    A reader that ignores a field it does not understand answers a question it
    was not asked. This is the whole mechanism behind the milestone's
    "no silent field dropping" case: an extra key that *would* change the
    answer must produce a refusal, not a different number.
    """
    keys = set(payload)
    unknown = sorted(keys - required - optional)
    if unknown:
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} carries unknown field(s) {unknown}; this reader refuses "
            f"fields it does not implement rather than ignoring them. Known: "
            f"{sorted(required | optional)}",
        )
    missing = sorted(required - keys)
    if missing:
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} is missing required field(s) {missing}",
        )


def _require_number(value: Any, where: str) -> float:
    # ``bool`` is an ``int`` in Python, and ``True`` would silently become 1.0.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} must be a number, got {type(value).__name__}",
        )
    return float(value)


def require_text(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} must be a string, got {type(value).__name__}",
        )
    return value


def require_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"{where} must be an integer, got {type(value).__name__}",
        )
    return value


def parse_quantity(
    value: Any, *, where: str, unit: str, difference: bool = False
) -> Quantity:
    """``{"value": <number>, "unit": <string>}`` -> a Quantity in ``unit``.

    Two keys, both required, nothing else accepted. A bare number is refused:
    a scientific value without a unit is a contract violation, not a
    dimensionless default (Scientific Core §26.6).

    The caller's unit string is converted to this field's **declared canonical
    unit** immediately. Its only possible effect on execution is therefore a
    conversion factor: a dimensionally incompatible unit raises
    ``UnitCompatibilityError`` here, and an unparsable one raises it inside
    pint's unit-expression parser, which is the *only* parser any external
    string in this contract reaches.

    ``difference`` — and why it exists, because it was found by measurement
    ------------------------------------------------------------------------
    Some fields of this contract carry a **difference** rather than a value: a
    coupling tolerance is the largest change of an iterate, not a temperature.
    An affine unit cannot express one. ``Quantity(1e-6, "degC")`` converts to
    ``273.150001 kelvin``, and ``degC`` has the same dimensionality as
    ``kelvin``, so no dimension check anywhere can see the mistake.

    ``engcore.coupling`` already refuses an affine comparison unit for exactly
    this reason — and **that refusal could not fire here**, because the
    canonicalization two lines above had already turned the affine unit into a
    perfectly acceptable kelvin. Measured before this argument was written: a
    tolerance of ``1e-6 degC`` produced a converged run in **one** iteration
    reporting a temperature **5.695253 K** from the truth, with every sub-solve
    passing and every record self-consistent.

    So the check is applied to the caller's unit **before** conversion, and it
    is the coupling package's own ``is_ratio_scale`` rather than a second
    implementation of the same rule.
    """
    payload = require_object(value, where)
    require_exact_keys(payload, required=frozenset({"value", "unit"}), where=where)
    magnitude = _require_number(payload["value"], f"{where}.value")
    units = require_text(payload["unit"], f"{where}.unit")
    # UnitCompatibilityError (a ScientificCoreError) propagates: an unparsable
    # or wrongly-dimensioned unit is a *scientific* refusal, not a malformed
    # document, and the service classifies it as one.
    if difference and not is_ratio_scale(units):
        raise UnitCompatibilityError(
            f"{where} carries a difference and may not be stated in {units!r}: "
            f"its zero is conventional, so a difference expressed in it is not "
            f"a value of that unit and does not survive conversion. Use a "
            f"ratio scale, whose zero maps to zero in its base unit."
        )
    return Quantity(magnitude, units).to(unit)


@dataclass(frozen=True)
class ExecutionRequest:
    """The envelope. Typed, versioned, and complete by enumeration.

    ``inputs`` and ``coupling`` stay as the caller's sub-payloads because their
    shape is a property of the *named execution*, and the module that knows
    that execution is the one that parses them. This class checks the envelope,
    resolves the two closed enumerations, and hands the rest on.

    There is no ``metadata`` field, no ``options`` field, no ``extra`` field and
    no free-form mapping anywhere in this contract. Every accepted key is
    enumerated in source.
    """

    execution: str
    execution_profile: str
    run_id: str
    inputs: Mapping[str, Any]
    coupling: Mapping[str, Any]


def parse_request(
    payload: Any,
    *,
    known_executions: frozenset[str],
    known_profiles: frozenset[str],
) -> ExecutionRequest:
    """Envelope only. Raises :class:`ExternalRequestRefused` for A, B and D."""
    body = require_object(payload, "request")

    schema = body.get("schema")
    if schema != REQUEST_SCHEMA:
        raise ExternalRequestRefused(
            RefusalCode.UNSUPPORTED_SCHEMA_VERSION,
            f"unsupported request schema {schema!r}; this reader implements "
            f"exactly {REQUEST_SCHEMA!r}. A version is admitted only because "
            f"somebody checked that this reader handles it.",
        )

    require_exact_keys(
        body,
        required=frozenset(
            {"schema", "execution", "execution_profile", "inputs", "coupling"}
        ),
        optional=frozenset({"run_id"}),
        where="request",
    )

    execution = require_text(body["execution"], "request.execution")
    if execution not in known_executions:
        # The refusal names the admissible set. That is this deployment's
        # discovery affordance, and it is why no /capabilities endpoint and no
        # crafty_capabilities tool exists: a second surface restating this
        # would carry no independent meaning.
        raise ExternalRequestRefused(
            RefusalCode.UNKNOWN_EXECUTION,
            f"unknown execution {execution!r}; this deployment exposes "
            f"{sorted(known_executions)}",
        )

    profile = require_text(
        body["execution_profile"], "request.execution_profile"
    )
    if profile not in known_profiles:
        raise ExternalRequestRefused(
            RefusalCode.UNKNOWN_EXECUTION_PROFILE,
            f"unknown execution profile {profile!r}; this deployment exposes "
            f"{sorted(known_profiles)}. An execution profile is a Crafty "
            f"identity drawn from a closed enumeration; it is never a path, "
            f"a command, or an argument to one.",
        )

    run_id = require_text(body.get("run_id", "crafty-v0"), "request.run_id")
    if not run_id.strip():
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST, "request.run_id must be non-empty"
        )

    return ExecutionRequest(
        execution=execution,
        execution_profile=profile,
        run_id=run_id,
        inputs=require_object(body["inputs"], "request.inputs"),
        coupling=require_object(body["coupling"], "request.coupling"),
    )


# =====================================================================
# Projection — CoupledRun -> the external response payload
# =====================================================================

def _quantity(value: Quantity) -> dict[str, Any]:
    """The external form of a scientific value. Two keys, always both."""
    return {"value": value.magnitude, "unit": value.units}


def _uncertainty(record: Uncertainty) -> dict[str, Any]:
    """Unknown uncertainty travels as *unknown*, never as absence.

    Scientific Core §26.4: uncertainty must not be invented. A response that
    omitted the field where none was computed would read as "no uncertainty",
    which is a stronger claim than "not evaluated".
    """
    payload: dict[str, Any] = {"kind": record.kind.value}
    if record.notes:
        payload["notes"] = record.notes
    if record.standard_uncertainty is not None:
        payload["standard_uncertainty"] = _quantity(record.standard_uncertainty)
    if record.lower is not None:
        payload["lower"] = _quantity(record.lower)
    if record.upper is not None:
        payload["upper"] = _quantity(record.upper)
    if record.confidence_level is not None:
        payload["confidence_level"] = record.confidence_level
    return payload


def _participant(result: ScientificResult) -> dict[str, Any]:
    """One sub-solve's own verdicts. **Never derived from the coupling.**

    ``numerical_convergence`` is what the numerical backend said about its own
    termination; ``validation_status`` is whether the checks that ran passed.
    In a run that did not converge at all, every one of these still reports
    success — which is the executed fact the external contract exists to keep
    visible.
    """
    return {
        "problem_id": result.problem_id,
        "numerical_convergence": result.convergence.value,
        "validation_status": result.validation.status.value,
        "attained_levels": sorted(
            level.value for level in result.attained_levels
        ),
        "models": [[model_id, version] for model_id, version in result.models],
        "solver": (
            None
            if result.solver is None
            else {
                "solver_id": result.solver.solver_id,
                "version": result.solver.version,
                "backend": result.solver.backend,
            }
        ),
    }


def project_run(run: CoupledRun) -> dict[str, Any]:
    """The whole external result. Domain-neutral: it reads only a ``CoupledRun``.

    Nothing here knows what an ohm, a watt or a kelvin is, which is why this
    function is in the transport-neutral layer and not in a transport.
    """
    final = run.final
    outputs: list[dict[str, Any]] = []
    for result in sorted(final.results, key=lambda r: r.problem_id):
        for name in sorted(result.values):
            outputs.append(
                {
                    "problem_id": result.problem_id,
                    "quantity": name,
                    "value": _quantity(result.values[name]),
                    "uncertainty": _uncertainty(result.uncertainty_of(name)),
                }
            )

    bindings = [
        {
            "model": {
                "model_id": binding.model.model_id,
                "version": binding.model.version,
            },
            "realization": (
                None
                if binding.realization is None
                else {
                    "realization_id": binding.realization.realization_id,
                    "version": binding.realization.version,
                }
            ),
            "solver": {
                "solver_id": binding.solver.solver_id,
                "version": binding.solver.version,
                "backend": binding.solver.backend,
            },
        }
        for binding in run.provenance.bindings
    ]
    bindings.sort(key=lambda b: (
        b["model"]["model_id"], b["model"]["version"],
        (b["realization"] or {}).get("realization_id", ""),
        b["solver"]["solver_id"], b["solver"]["version"],
    ))

    return {
        "coupling": {
            # The ONLY statement of coupling convergence anywhere, carried
            # across unchanged. It is never computed from the sub-solves.
            "outcome": run.outcome.value,
            "criterion_met": run.criterion_met,
            "iterations_run": run.iterations_run,
            "max_iterations": run.plan.max_iterations,
            "tolerance": _quantity(run.plan.absolute_tolerance),
            "comparison_unit": run.plan.comparison_unit,
            "final_iterate_change": _quantity(run.final_iterate_change),
            # One scalar per sweep. O(iterations), never O(mesh).
            "iterate_changes": [_quantity(q) for q in run.iterate_changes],
        },
        "outputs": outputs,
        "torn_endpoints": [
            {
                "problem_id": problem_id,
                "quantity": quantity,
                # Named for what it is on BOTH exit paths. On a budget-exhausted
                # run this holds an unconverged iterate, and a field called
                # `converged_value` would be one name meaning two things.
                "final_value": _quantity(run.final_values[(problem_id, quantity)]),
            }
            for problem_id, quantity in sorted(run.final_values)
        ],
        "participants": [
            _participant(result)
            for result in sorted(final.results, key=lambda r: r.problem_id)
        ],
        "model_validity": {
            "assessed": False,
            "reason": (
                "the executed coupled path produces no model-applicability "
                "verdict. Crafty has such an assessment for this domain, but "
                "nothing in this execution calls it, and an application layer "
                "that called it would be performing a scientific assessment "
                "the execution did not perform. NOT_RUN is not PASS."
            ),
        },
        "provenance": {
            "run_id": run.provenance.run_id,
            "software_version": run.provenance.software_version,
            "assumptions": list(run.provenance.assumptions),
            "bindings": bindings,
        },
    }
