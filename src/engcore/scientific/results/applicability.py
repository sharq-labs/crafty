"""Model applicability, as a field of the result rather than a note beside it.

A result says what was computed. This says whether the model it was computed
with was *applicable to the case it was computed for* — a different claim, and
one that four of the five shipped paths were making nowhere. The CSTR solver
computed a full :class:`ValidityAssessment`, rendered ``assessment.status.value``
into a free-text note, and dropped the rest on the floor.

**Why this is in the core rather than in four domains.** Four domains omitted
it because the core permitted omission. A fifth would omit it for the same
reason and the drone would be the sixth. So the permission is what changed:
the field exists on every result, always, and there is no way to have one
without saying something.

Three states, and they are deliberately three rather than two:

``ASSESSED``
    Somebody ran a validity domain against a context and this is what it said.
    The mapping **may be empty** — that means "assessed, and no model in this
    result declared a validity domain to assess". That is a real answer.

``NOT_ASSESSED``
    A stated position: this path deliberately did not assess applicability,
    and here is why. Requires a reason; carrying assessments is refused.

``UNDECLARED``
    Nobody said anything. This is what a producer that has never heard of
    applicability gets, and it is **not** the same as either of the above:
    "assessed and found nothing to check", "deliberately not assessed", and
    "the question was never reached" are three different answers, and
    collapsing them is how a result comes to look more examined than it is.

A reader can always tell which one it is looking at, because ``status`` is
serialized explicitly and every state carries it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from ..errors import ScientificCoreError
from ..models.definition import ValidityAssessment, ValidityStatus
from ..serialization import require_schema, schema_string

APPLICABILITY_SCHEMA = schema_string("applicability_report")


class ApplicabilityState(str, Enum):
    UNDECLARED = "undeclared"
    NOT_ASSESSED = "not_assessed"
    ASSESSED = "assessed"


@dataclass(frozen=True)
class ApplicabilityReport:
    """Whether model applicability was assessed for a result, and what it said.

    Constructed through :meth:`assessed`, :meth:`not_assessed` or
    :meth:`undeclared` rather than positionally, so that the state and the
    payload cannot disagree.
    """

    state: ApplicabilityState = ApplicabilityState.UNDECLARED
    reason: str = ""
    assessments: Mapping[str, ValidityAssessment] = field(default_factory=dict)

    def __post_init__(self) -> None:
        state = ApplicabilityState(self.state)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "reason", str(self.reason).strip())

        entries = dict(self.assessments)
        for name, assessment in entries.items():
            if not isinstance(assessment, ValidityAssessment):
                raise ScientificCoreError(
                    f"applicability entry {name!r} must be a ValidityAssessment, "
                    f"got {type(assessment).__name__}"
                )
        object.__setattr__(self, "assessments", entries)

        if state is ApplicabilityState.ASSESSED:
            # An empty mapping IS allowed here and means something: assessed,
            # and no model declared a validity domain. That is why the state
            # is a field and not inferred from `bool(assessments)`.
            return
        if entries:
            raise ScientificCoreError(
                f"applicability state {state.value!r} carries "
                f"{len(entries)} assessment(s); a result that did not assess "
                f"applicability cannot also report what the assessment found"
            )
        if state is ApplicabilityState.NOT_ASSESSED and not self.reason:
            raise ScientificCoreError(
                "'not assessed' is a stated position and requires a reason; "
                "a bare absence is UNDECLARED, which is a different answer"
            )
        if state is ApplicabilityState.UNDECLARED and self.reason:
            raise ScientificCoreError(
                "UNDECLARED means nothing was said; a record that carries a "
                "reason has said something and is NOT_ASSESSED"
            )

    # ---- construction ---------------------------------------------------
    @classmethod
    def undeclared(cls) -> "ApplicabilityReport":
        """The producing path said nothing. The default, and never a pass."""
        return cls(state=ApplicabilityState.UNDECLARED)

    @classmethod
    def not_assessed(cls, reason: str) -> "ApplicabilityReport":
        """A stated position: deliberately not assessed, and why."""
        return cls(state=ApplicabilityState.NOT_ASSESSED, reason=str(reason))

    @classmethod
    def assessed(
        cls,
        assessments: Mapping[str, ValidityAssessment] | None = None,
        *,
        reason: str = "",
    ) -> "ApplicabilityReport":
        """What a validity domain said, per component. May be empty."""
        return cls(
            state=ApplicabilityState.ASSESSED,
            reason=reason,
            assessments=dict(assessments or {}),
        )

    # ---- derived state --------------------------------------------------
    @property
    def was_assessed(self) -> bool:
        return self.state is ApplicabilityState.ASSESSED

    @property
    def violated(self) -> tuple[str, ...]:
        """``component_id`` of every assessment that left the declared domain.

        Empty when nothing was assessed — which is why callers must ask
        :attr:`was_assessed` first, and why :meth:`require_assessed` exists.
        An empty violation list from an unassessed report is not good news.
        """
        return tuple(
            sorted(
                name
                for name, assessment in self.assessments.items()
                if assessment.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
            )
        )

    @property
    def unknown(self) -> tuple[str, ...]:
        """``component_id`` of every assessment that could not be decided."""
        return tuple(
            sorted(
                name
                for name, assessment in self.assessments.items()
                if assessment.status is ValidityStatus.UNKNOWN
            )
        )

    def require_declared(self, *, context: str = "") -> None:
        """Raise only on silence. A stated position is allowed through.

        The distinction this whole record exists for, made enforceable:
        ``NOT_ASSESSED`` is an answer — "we did not assess applicability, and
        here is why" — and a consumer can be told that and decide. ``UNDECLARED``
        is not an answer, and there is nothing for a consumer to decide about.

        This, and not :meth:`require_assessed`, is what a reporting boundary
        should use. Refusing a stated position there would destroy a real
        capability: a path that legitimately does not assess applicability
        could never report at all.
        """
        if self.state is not ApplicabilityState.UNDECLARED:
            return
        prefix = f"{context}: " if context else ""
        raise ScientificCoreError(
            f"{prefix}model applicability is UNDECLARED — the path that "
            f"produced this result said nothing about whether its model "
            f"applies to the case it was run on. Declare it: pass "
            f"applicability=ApplicabilityReport.assessed(...) with what a "
            f"ValidityDomain said, or "
            f"ApplicabilityReport.not_assessed('<why>') to state that "
            f"position on the record"
        )

    def require_assessed(self, *, context: str = "") -> None:
        """Raise unless applicability was actually assessed.

        The enforcement primitive. ``UNDECLARED`` and ``NOT_ASSESSED`` are
        both refused, and the message distinguishes them, because "nobody
        asked" and "we decided not to ask" need different fixes.
        """
        if self.was_assessed:
            return
        prefix = f"{context}: " if context else ""
        if self.state is ApplicabilityState.NOT_ASSESSED:
            raise ScientificCoreError(
                f"{prefix}model applicability was deliberately not assessed "
                f"({self.reason}); this consumer requires an assessment, and "
                f"'not assessed' is not 'applicable'"
            )
        raise ScientificCoreError(
            f"{prefix}model applicability is UNDECLARED — the path that "
            f"produced this result said nothing about whether its model "
            f"applies to the case it was run on. Declare it: pass "
            f"applicability=ApplicabilityReport.assessed(...) with what a "
            f"ValidityDomain said, or "
            f"ApplicabilityReport.not_assessed('<why>') to state that "
            f"position on the record"
        )

    # ---- serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": APPLICABILITY_SCHEMA,
            # Always present, in every state. This is what makes the three
            # distinguishable to a reader that has only the payload.
            "state": self.state.value,
            "reason": self.reason,
            "assessments": {
                name: self.assessments[name].to_dict()
                for name in sorted(self.assessments)
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ApplicabilityReport":
        require_schema(payload, APPLICABILITY_SCHEMA)
        return cls(
            state=ApplicabilityState(payload["state"]),
            reason=payload.get("reason", ""),
            assessments={
                name: ValidityAssessment.from_dict(value)
                for name, value in (payload.get("assessments") or {}).items()
            },
        )
