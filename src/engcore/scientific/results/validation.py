"""Validation reporting.

Two deliberate design decisions:

1. **Checks coexist; the level is derived, never asserted.** A single scalar
   "validation level" is misleading, because dimensional validity, numerical
   convergence and experimental agreement are independent claims. A report
   therefore holds a list of checks, and any attained level must be *backed
   by a passing check that declares it*.

2. **NOT_RUN is distinct from PASS.** A check that never executed can never
   contribute evidence. This is the mechanism that prevents a result from
   claiming validation that was not actually performed.

A third, added by MIN-CROSS-DOMAIN-FOUNDATION:

3. **Detection is not enforcement.** A report can say a check failed; nothing
   makes anything refuse to consume the result anyway, unless something
   explicitly asks. ``require_admission``/``is_admissible``/
   ``admission_issues`` are that explicit ask — a caller opts in by calling
   one, cross-referencing this report's checks against a set of *names* a
   problem declared required (``ScientificProblem.validation_requirements``).
   No new record and no new ``ValidationLevel`` member were added for this:
   both fields already existed, were already populated by every shipped
   domain, and nothing before this cross-referenced them. See
   docs/min-cross-domain-foundation-evidence.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from ..errors import ScientificValidationError
from ..serialization import require_schema, schema_string

CHECK_SCHEMA = schema_string("validation_check")
REPORT_SCHEMA = schema_string("validation_report")


class ValidationOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_RUN = "not_run"


class ValidationLevel(str, Enum):
    """What has been established, in increasing evidentiary strength.

    These are *claims about evidence*, not a quality score. A result may
    attain several independently (dimensional validity and numerical
    convergence say different things).
    """

    UNVERIFIED = "unverified"
    DIMENSIONALLY_VALID = "dimensionally_valid"
    NUMERICALLY_CONVERGED = "numerically_converged"
    ANALYTICALLY_VERIFIED = "analytically_verified"
    BENCHMARK_VALIDATED = "benchmark_validated"
    CROSS_SOLVER_VALIDATED = "cross_solver_validated"
    EXPERIMENTALLY_VALIDATED = "experimentally_validated"


@dataclass(frozen=True)
class ValidationCheck:
    """One executed (or deliberately skipped) verification step."""

    name: str
    outcome: ValidationOutcome
    detail: str = ""
    establishes: ValidationLevel | None = None
    residual: float | None = None
    tolerance: float | None = None
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ScientificValidationError("validation check requires a name")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "outcome", ValidationOutcome(self.outcome))
        if self.establishes is not None:
            object.__setattr__(self, "establishes", ValidationLevel(self.establishes))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.residual is not None:
            object.__setattr__(self, "residual", float(self.residual))
        if self.tolerance is not None:
            object.__setattr__(self, "tolerance", float(self.tolerance))

    @property
    def passed(self) -> bool:
        return self.outcome is ValidationOutcome.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CHECK_SCHEMA,
            "name": self.name,
            "outcome": self.outcome.value,
            "detail": self.detail,
            "establishes": self.establishes.value if self.establishes else None,
            "residual": self.residual,
            "tolerance": self.tolerance,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ValidationCheck":
        require_schema(payload, CHECK_SCHEMA)
        establishes = payload.get("establishes")
        return cls(
            name=payload["name"],
            outcome=ValidationOutcome(payload["outcome"]),
            detail=payload.get("detail", ""),
            establishes=ValidationLevel(establishes) if establishes else None,
            residual=payload.get("residual"),
            tolerance=payload.get("tolerance"),
            evidence=tuple(payload.get("evidence", ())),
        )


@dataclass(frozen=True)
class ValidationReport:
    """The set of checks performed on one result, and what they establish."""

    checks: tuple[ValidationCheck, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", tuple(self.checks))
        names = [c.name for c in self.checks]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ScientificValidationError(
                f"duplicate validation check names: {sorted(duplicates)}"
            )

    # ---- derived state --------------------------------------------------
    @property
    def status(self) -> ValidationOutcome:
        """Aggregate outcome. FAIL dominates; an empty report is NOT_RUN."""
        outcomes = {c.outcome for c in self.checks}
        if ValidationOutcome.FAIL in outcomes:
            return ValidationOutcome.FAIL
        if ValidationOutcome.WARNING in outcomes:
            return ValidationOutcome.WARNING
        if ValidationOutcome.PASS in outcomes:
            return ValidationOutcome.PASS
        return ValidationOutcome.NOT_RUN

    @property
    def attained_levels(self) -> frozenset[ValidationLevel]:
        """Levels backed by a *passing* check. Never asserted directly."""
        return frozenset(
            c.establishes
            for c in self.checks
            if c.passed and c.establishes is not None
        )

    def claims(self, level: ValidationLevel) -> bool:
        return ValidationLevel(level) in self.attained_levels

    @property
    def failures(self) -> tuple[ValidationCheck, ...]:
        return tuple(c for c in self.checks if c.outcome is ValidationOutcome.FAIL)

    @property
    def warnings(self) -> tuple[ValidationCheck, ...]:
        return tuple(c for c in self.checks if c.outcome is ValidationOutcome.WARNING)

    @property
    def not_run(self) -> tuple[ValidationCheck, ...]:
        return tuple(c for c in self.checks if c.outcome is ValidationOutcome.NOT_RUN)

    def with_check(self, check: ValidationCheck) -> "ValidationReport":
        return ValidationReport(checks=(*self.checks, check), notes=self.notes)

    def require_level(self, level: ValidationLevel) -> None:
        """Raise unless the level was actually established."""
        if not self.claims(level):
            raise ScientificValidationError(
                f"validation level {ValidationLevel(level).value!r} was not "
                f"established by any passing check"
            )

    # ---- admission (MIN-CROSS-DOMAIN-FOUNDATION) -------------------------
    #
    # A problem may declare, in ``ScientificProblem.validation_requirements``,
    # which *named* checks a result computed from it must satisfy — every
    # shipped domain already populates this field with names that are the
    # literal ``ValidationCheck.name`` values its own validator produces
    # (``kinetics/cstr``'s ``state_physically_admissible``,
    # ``trajectory_finite`` and so on). Nothing before this method
    # cross-referenced the two: ``require_level`` gates on an *evidentiary
    # level*, which every admissibility check in this codebase deliberately
    # declines to establish (``establishes=None`` — a passing admissibility
    # check is not stronger evidence of numerical accuracy, and correctly
    # claims none), and ``ScientificResult.is_usable`` is global over the
    # whole report rather than scoped to a *specific declared name* — a
    # required check that never ran (``NOT_RUN``) does not by itself flip
    # ``is_usable`` unless something else in the report also failed.
    #
    # This closes that gap by reusing exactly the two fields that already
    # exist and are already populated, rather than adding a record or a
    # ``ValidationLevel`` member. See docs/min-cross-domain-foundation-
    # evidence.md for the executed measurement and the negative proof that
    # motivated it: a provider silently halving reported power produced a
    # ``FAIL``ing check that nothing consumed, and a coupled loop converged
    # 18 K away from the honest answer with the bad value never refused.
    def admission_issues(self, requirements: Iterable[str]) -> tuple[str, ...]:
        """Why ``requirements`` are not all satisfied by a *passing* check of
        the same name. Empty means every named requirement passed.

        ``NOT_RUN`` counts as unsatisfied, on the same principle stated at
        the top of this module: a check that never executed contributes no
        evidence, and a *required* admission gate needs evidence, not
        silence. ``WARNING`` and ``FAIL`` are likewise unsatisfied — a
        required check that only warns has not established what it was
        required to establish.
        """
        by_name = {check.name: check for check in self.checks}
        issues: list[str] = []
        for name in sorted(set(requirements)):
            check = by_name.get(name)
            if check is None:
                issues.append(f"{name!r}: never checked")
            elif not check.passed:
                issues.append(f"{name!r}: {check.outcome.value}")
        return tuple(issues)

    def is_admissible(self, requirements: Iterable[str]) -> bool:
        """``True`` iff every named requirement is backed by a passing check."""
        return not self.admission_issues(requirements)

    def require_admission(
        self, requirements: Iterable[str], *, context: str = ""
    ) -> None:
        """Raise unless every declared requirement is backed by a passing
        check of the same name.

        This is the enforcement primitive: a caller that calls this before
        consuming ``result.value(...)`` cannot silently proceed past a
        declared requirement that failed or never ran. A caller that does
        not call it gets no protection — enforcement is not automatic on
        construction, exactly as ``require_level`` is not automatic, because
        a result may legitimately exist and be reported on (a failed run is
        still evidence) without every consumer of every result needing the
        strictest possible gate.
        """
        issues = self.admission_issues(requirements)
        if issues:
            prefix = f"{context}: " if context else ""
            raise ScientificValidationError(
                f"{prefix}admission refused; declared requirement(s) not "
                f"satisfied by a passing check: {'; '.join(issues)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": REPORT_SCHEMA,
            "checks": [c.to_dict() for c in self.checks],
            "status": self.status.value,
            "attained_levels": sorted(l.value for l in self.attained_levels),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ValidationReport":
        require_schema(payload, REPORT_SCHEMA)
        report = cls(
            checks=tuple(
                ValidationCheck.from_dict(c) for c in payload.get("checks", ())
            ),
            notes=payload.get("notes", ""),
        )
        # Derived fields in the payload are advisory; recompute and verify so a
        # hand-edited record cannot smuggle in an unearned validation claim.
        declared = set(payload.get("attained_levels", ()))
        recomputed = {l.value for l in report.attained_levels}
        if declared and declared != recomputed:
            raise ScientificValidationError(
                f"serialized attained_levels {sorted(declared)} do not match "
                f"the levels established by its checks {sorted(recomputed)}"
            )
        return report


def unverified_report(reason: str = "no validation performed") -> ValidationReport:
    """An explicit 'nothing was checked' report — better than an empty one."""
    return ValidationReport(
        checks=(
            ValidationCheck(
                name="validation_performed",
                outcome=ValidationOutcome.NOT_RUN,
                detail=reason,
            ),
        )
    )
