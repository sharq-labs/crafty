"""The boundary itself: ``handle(payload) -> payload``.

One function, no class. An "application service" object here would hold no
state and would be a namespace with a constructor, so the abstraction was
reduced away before it was written.

Failure classification: **class AND position**
----------------------------------------------
Classifying by exception class alone is wrong, and the counterexample is in the
tree. ``InvalidScientificProblem`` is raised both by a caller's malformed
declaration *and*, inside ``run_fixed_point``, by an executor returning a
result attributed to the wrong problem — which is a Crafty defect. Class alone
would report that defect as a caller error.

So the classifier reads two things: the exception's **class object** (never its
message text) and the **stage** it was raised on. Everything raised before
:meth:`PreparedExecution.run` is entered is caller-facing; everything raised
inside it is an execution failure, whatever its class.

The classifier is total. Its default is its own code,
``unclassified_internal_failure`` — never a collapse into "error", and never a
silent success.

What ``handle`` never does
--------------------------
It never raises for a caller-caused condition; it returns a refusal payload.
Transports therefore need no error type of their own, which is why none exists.
It also never re-interprets a scientific verdict: a run that did not converge
is ``status: "executed"`` with an outcome that says so, because *the coupling
did not converge* is a scientific finding, not a failure of this boundary.
"""

from __future__ import annotations

import traceback
from typing import Any, Mapping

from ..scientific.errors import ScientificCoreError
from .catalog import EXECUTIONS
from .contract import (
    RESPONSE_SCHEMA,
    ExternalRequestRefused,
    RefusalCode,
    parse_request,
    project_run,
)

__all__ = ["decode_failure", "execute", "handle"]

#: Stages, in order. The classifier reads which one was current.
_REQUEST = "request"
_ADMISSION = "admission"
_EXECUTION = "execution"


def _refusal(
    code: RefusalCode,
    stage: str,
    detail: str,
    *,
    error_type: str = "",
    execution: str = "",
    profile: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    return {
        "schema": RESPONSE_SCHEMA,
        # Never "success", never a boolean. Three enumerated words, and the
        # only one that means anything happened makes no scientific claim.
        "status": "refused" if stage != _EXECUTION else "execution_failed",
        "execution": execution,
        "execution_profile": profile,
        "run_id": run_id,
        "result": None,
        "refusal": {
            "code": code.value,
            "stage": stage,
            "error_type": error_type,
            "detail": detail,
        },
    }


def _provider_error_classes(module: Any) -> tuple[type[BaseException], ...]:
    """*Ask* the resolved execution which failures mean "a provider broke".

    This layer must be able to classify a provider failure without naming a
    provider, and the first form named one — it read a module path out of
    ``sys.modules`` right here, which is a domain fact in a layer that must not
    hold one. An execution knows what runs underneath it; nothing above it
    does. Part of the execution-module protocol, and empty is a real answer.
    """
    ask = getattr(module, "provider_failure_types", None)
    return tuple(ask()) if callable(ask) else ()


def execute(payload: Any) -> dict[str, Any]:
    """Run one external request. Returns a response payload; never raises."""
    stage = _REQUEST
    execution = profile = run_id = ""
    module: Any = None
    try:
        request = parse_request(payload, executions=EXECUTIONS)
        execution, profile, run_id = (
            request.execution,
            request.execution_profile,
            request.run_id,
        )

        stage = _ADMISSION
        module = EXECUTIONS[request.execution]
        # The profile travels as the identity `parse_request` already validated
        # against THIS execution's own enumeration, and the execution resolves
        # it. This layer therefore names no solver, no circuit and no provider,
        # and cannot: it has no type from any of them.
        prepared = module.prepare(
            request.inputs, request.coupling, request.execution_profile
        )

        stage = _EXECUTION
        run = prepared.run(request.run_id)

    except ExternalRequestRefused as exc:
        # A refusal about the document itself. On the admission stage it may
        # still be a scientific refusal — the plan check raises it with the
        # scientific code — so the code travels with the exception rather than
        # being re-derived from where it was caught.
        return _refusal(
            exc.code,
            _ADMISSION
            if exc.code is RefusalCode.SCIENTIFIC_ADMISSION_REFUSED
            else _REQUEST,
            exc.detail,
            error_type=type(exc).__name__,
            execution=execution,
            profile=profile,
            run_id=run_id,
        )

    except ScientificCoreError as exc:
        # Crafty refused the science. Which side of the split decides whether
        # that is the caller's answer or Crafty's own defect.
        if stage is _EXECUTION:
            return _refusal(
                RefusalCode.SUBSOLVER_EXECUTION_FAILED,
                _EXECUTION,
                str(exc),
                error_type=type(exc).__name__,
                execution=execution,
                profile=profile,
                run_id=run_id,
            )
        return _refusal(
            RefusalCode.SCIENTIFIC_ADMISSION_REFUSED,
            _ADMISSION,
            str(exc),
            error_type=type(exc).__name__,
            execution=execution,
            profile=profile,
            run_id=run_id,
        )

    except BaseException as exc:  # noqa: BLE001 - the classifier must be total
        if isinstance(exc, _provider_error_classes(module)):
            return _refusal(
                RefusalCode.PROVIDER_EXECUTION_FAILED,
                _EXECUTION,
                str(exc),
                error_type=type(exc).__name__,
                execution=execution,
                profile=profile,
                run_id=run_id,
            )
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        # A Crafty defect, or something nobody enumerated. Say so; do not
        # dress it as a caller error and do not let it read as a refusal of
        # the science. The traceback stays on this side of the boundary.
        traceback.clear_frames(exc.__traceback__)
        return _refusal(
            RefusalCode.UNCLASSIFIED_INTERNAL_FAILURE,
            stage,
            f"{type(exc).__name__}: {exc}",
            error_type=type(exc).__name__,
            execution=execution,
            profile=profile,
            run_id=run_id,
        )

    return {
        "schema": RESPONSE_SCHEMA,
        # "executed" states that the boundary carried out an execution. It
        # makes NO scientific claim: a run that hit its iteration limit without
        # converging is "executed" too, and reports that in `coupling.outcome`.
        "status": "executed",
        "execution": execution,
        "execution_profile": profile,
        "run_id": run_id,
        "result": project_run(run),
        "refusal": None,
    }


def decode_failure(detail: str) -> dict[str, Any]:
    """A response for a body a transport could not decode into a payload.

    Published here, and used by **both** transports, for one reason: the shape
    of a refusal is part of the external contract, and a transport that
    hand-built one would be the first duplicated piece of the contract. A
    transport may decide its own status line; it may not decide what a refusal
    looks like.

    It is not a transport error type. Nothing is raised, and neither transport
    defines an exception of its own.
    """
    return _refusal(
        RefusalCode.MALFORMED_REQUEST,
        _REQUEST,
        detail,
        error_type="TransportDecodeFailure",
    )


def handle(payload: Any) -> dict[str, Any]:
    """The single entry point every transport calls. Alias of :func:`execute`.

    Kept as a distinct published name because *the thing a transport calls* and
    *the thing that runs one request* are the same today and need not stay so —
    if a second operation shape ever arrives, ``handle`` is where dispatch would
    go, and a transport should never have had to know that.
    """
    return execute(payload)
