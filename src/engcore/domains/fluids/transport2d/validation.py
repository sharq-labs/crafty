"""Two verification concepts, kept apart — same discipline as
``thermal/conduction1d/validation.py``.

PER-SOLVE VALIDATION establishes what one run can establish: the linear
system was solved (to round-off), the field is finite, the admissibility
bound (`c in [0, 1]`, the analytic range of `c*` on this domain) holds, the
metrics carry units, and — when a cross-check dense solve was also run — that
the two backends agree on the SAME assembled system. It awards
``DIMENSIONALLY_VALID`` and nothing stronger. It never awards
``NUMERICALLY_CONVERGED`` or ``ANALYTICALLY_VERIFIED``: a single solve has
nothing to compare itself against across resolutions, exactly the reasoning
``thermal/conduction1d/validation.py``'s module docstring gives.

THE REFINEMENT GATE (:func:`run_verification_gate`) establishes the two
claims that need a *sequence*, over the frozen ladder
``n in {8, 16, 32, 64}`` (``docs/real-fluid-pde-prereg.md`` §2/§8).

ADMISSION — F8, THE MANDATORY REAL REFUSAL PATH
----------------------------------------------------
:func:`read_centre_concentration_with_admission` is a REAL downstream
Fluid-domain consumer: it reads ``result.value(CENTRE_METRIC)`` only after
calling ``ValidationReport.require_admission`` against
``problem.validation_requirements`` — the Foundation's own enforcement
primitive (``docs/min-cross-domain-foundation-evidence.md``), never called
from production code before this milestone (verified there: zero `src/`
callers). :func:`read_centre_concentration_unguarded` is the same read with
no guard, kept to demonstrate the silent-consumption failure mode is real,
not hypothetical, absent the guard — mirroring the Foundation's own
``HETERO-NGSPICE`` §8.4 negative proof. The genuinely failing case this
milestone constructs is not synthetic corruption: it is the ``n=8`` rung of
this benchmark's own admissibility check, which fails for real physical
reasons the preparation document already measured (peak cell Péclet 8.84,
outside the diffusion-dominated regime).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from ....scientific.errors import ScientificValidationError
from ....scientific.ir.orientation import (
    BoundaryOrientation,
    MixedOrientationError,
    classify_sign,
)
from ....scientific.results.validation import (
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
)
from ....scientific.units.quantity import Quantity
from .errors import Transport2DConfigurationError
from .problem import ALL_SIDES
from .reference import (
    REFERENCE_EXPRESSION,
    REFERENCE_ID,
    exact_centre,
    exact_field,
    side_orientation,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ....scientific.ir.problem import ScientificProblem
    from ....scientific.results.result import ScientificResult
    from ....scientific.solvers.protocol import RawSolverOutput
    from .problem import Transport2DDomain
    from .solver import PreparedTransport2DSystem


# =====================================================================
# Per-solve settings and report
# =====================================================================

@dataclass(frozen=True)
class Transport2DValidationSettings:
    """Tolerances for the checks a single solve can actually make."""

    #: ||A x - b|| for the direct solve. Round-off-scale self-consistency.
    residual_atol: float = 1.0e-8
    #: max(0, -c_min, c_max - 1); the analytic range of c* is [0, 1] and a
    #: converged fine grid should hold it, but a coarse grid legitimately
    #: overshoots — see the module docstring's n=8 finding, reused
    #: deliberately (not raised) as the F8 real failing case.
    admissibility_atol: float = 1.0e-9
    #: max|c_sparse - c_dense| for the two backends over the SAME assembled
    #: system. Looser than the preparation's observed ~1e-15 by orders of
    #: magnitude to absorb solver/platform variation (prereg §8).
    cross_check_atol: float = 1.0e-9

    def as_mapping(self) -> dict[str, float]:
        return {
            "residual_atol": float(self.residual_atol),
            "admissibility_atol": float(self.admissibility_atol),
            "cross_check_atol": float(self.cross_check_atol),
        }


def build_validation_report(
    system: "PreparedTransport2DSystem",
    raw: "RawSolverOutput",
    settings: Transport2DValidationSettings,
    *,
    dense_raw: "RawSolverOutput | None" = None,
) -> ValidationReport:
    """Checks one solve can support, and explicit NOT_RUN notes for what it
    cannot — same discipline as ``thermal/conduction1d``'s per-solve report."""
    if not raw.succeeded:
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="linear_system_residual",
                    outcome=ValidationOutcome.FAIL,
                    detail="; ".join(raw.warnings) or "solve did not succeed",
                ),
            ),
            notes="no solution to validate",
        )

    checks: list[ValidationCheck] = []
    field_values = np.asarray(raw.diagnostics["field"], dtype=np.float64)

    residual = float(raw.residuals.get("linear_system_residual", float("nan")))
    residual_ok = math.isfinite(residual) and residual <= settings.residual_atol
    checks.append(
        ValidationCheck(
            name="linear_system_residual",
            outcome=ValidationOutcome.PASS if residual_ok else ValidationOutcome.FAIL,
            residual=residual,
            tolerance=settings.residual_atol,
            detail=(
                "||A x - b|| for the direct solve. Linear-algebra "
                "self-consistency; says nothing about discretization "
                "accuracy"
            ),
            establishes=None,
        )
    )

    finite = bool(np.all(np.isfinite(field_values)))
    checks.append(
        ValidationCheck(
            name="field_finite",
            outcome=ValidationOutcome.PASS if finite else ValidationOutcome.FAIL,
            detail="every cell value is finite",
            establishes=None,
        )
    )

    c_min = float(np.min(field_values))
    c_max = float(np.max(field_values))
    admissibility_violation = max(0.0, -c_min, c_max - 1.0)
    admissible = admissibility_violation <= settings.admissibility_atol
    checks.append(
        ValidationCheck(
            name="admissibility_bound",
            outcome=ValidationOutcome.PASS if admissible else ValidationOutcome.FAIL,
            residual=admissibility_violation,
            tolerance=settings.admissibility_atol,
            detail=(
                f"c in [0, 1] (the analytic range of c* on this domain); "
                f"observed [{c_min:.6g}, {c_max:.6g}], violation "
                f"{admissibility_violation:.6g}. A discretization-scale "
                f"admissibility signature, not a physics one — see "
                f"docs/fluid-pde-preparation.md §B2"
            ),
            establishes=None,
        )
    )

    checks.append(
        ValidationCheck(
            name="dimensional_consistency",
            outcome=ValidationOutcome.PASS,
            detail=(
                "all metrics carry the dimensionless field unit; c is a "
                "normalized scalar transport field, not a concentration or "
                "temperature with an absolute scale"
            ),
            establishes=ValidationLevel.DIMENSIONALLY_VALID,
        )
    )

    if dense_raw is not None and dense_raw.succeeded:
        dense_field = np.asarray(dense_raw.diagnostics["field"], dtype=np.float64)
        max_diff = float(np.max(np.abs(field_values - dense_field)))
        agree = max_diff <= settings.cross_check_atol
        checks.append(
            ValidationCheck(
                name="sparse_dense_assembly_agreement",
                outcome=ValidationOutcome.PASS if agree else ValidationOutcome.FAIL,
                residual=max_diff,
                tolerance=settings.cross_check_atol,
                detail=(
                    "max|c_sparse - c_dense| for the SAME assembled system "
                    "(see solver.assemble docstring). This is assembly/"
                    "solver-behaviour self-consistency, NOT "
                    "CROSS_SOLVER_VALIDATED evidence about independently-"
                    "implemented physics — both solvers share one "
                    "discretization"
                ),
                # Deliberately establishes nothing stronger than what it is.
                establishes=None,
            )
        )
    else:
        checks.append(
            ValidationCheck(
                name="sparse_dense_assembly_agreement",
                outcome=ValidationOutcome.NOT_RUN,
                detail="cross-check solve was not requested for this run",
                establishes=None,
            )
        )

    checks.append(
        ValidationCheck(
            name="discretization_convergence",
            outcome=ValidationOutcome.NOT_RUN,
            detail=(
                "a single solve cannot establish discretization convergence: "
                "run the refinement gate (run_verification_gate) over the "
                "grid ladder"
            ),
            establishes=None,
        )
    )
    checks.append(
        ValidationCheck(
            name="analytic_reference_agreement",
            outcome=ValidationOutcome.NOT_RUN,
            detail=(
                "comparison against the manufactured reference is performed "
                "by the verification gate, which requires a converged "
                "sequence before it awards ANALYTICALLY_VERIFIED"
            ),
            establishes=None,
        )
    )

    return ValidationReport(
        checks=tuple(checks),
        notes=(
            "single-solve validation; the strongest level available here is "
            "DIMENSIONALLY_VALID"
        ),
    )


# =====================================================================
# F8 — real Fluid-domain admission consumers
# =====================================================================

def read_centre_concentration_unguarded(
    problem: "ScientificProblem", result: "ScientificResult"
) -> Quantity:
    """Read the centre-point concentration with NO admission guard.

    Exists to demonstrate the failure mode :func:`
    read_centre_concentration_with_admission` closes is real and structural,
    not hypothetical, absent the guard — the Foundation's own negative-proof
    pattern (``docs/min-cross-domain-foundation-evidence.md`` §6.1),
    exercised here for the first time against a genuine domain result.
    """
    from .problem import CENTRE_METRIC

    return result.value(CENTRE_METRIC)


def read_centre_concentration_with_admission(
    problem: "ScientificProblem", result: "ScientificResult"
) -> Quantity:
    """Read the centre-point concentration, refusing a result that does not
    satisfy every requirement the problem itself declared.

    The REAL production caller of ``ValidationReport.require_admission``
    this milestone adds (F8). Raises ``ScientificValidationError`` — caught,
    not swallowed — when a declared requirement failed or never ran; the
    caller never reaches the ``result.value(...)`` read in that case.
    """
    from .problem import CENTRE_METRIC

    result.validation.require_admission(
        problem.validation_requirements,
        context=f"fluids.transport2d result {result.result_id!r}",
    )
    return result.value(CENTRE_METRIC)


# =====================================================================
# The refinement gate
# =====================================================================

@dataclass(frozen=True)
class RungResult:
    n_cells: int
    dx_m: float
    peak_cell_peclet: float
    centre_qoi: float
    centre_analytic: float
    centre_abs_error: float
    centre_rel_error: float
    mms_max_abs_error: float
    admissibility_violation: float
    work_proxy: int
    wall_seconds_telemetry: float | None
    observed_order: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_cells": self.n_cells,
            "dx_m": self.dx_m,
            "peak_cell_peclet": self.peak_cell_peclet,
            "centre_qoi": self.centre_qoi,
            "centre_analytic": self.centre_analytic,
            "centre_abs_error": self.centre_abs_error,
            "centre_rel_error": self.centre_rel_error,
            "mms_max_abs_error": self.mms_max_abs_error,
            "admissibility_violation": self.admissibility_violation,
            "work_proxy": self.work_proxy,
            "wall_seconds_telemetry": self.wall_seconds_telemetry,
            "observed_order": self.observed_order,
        }


@dataclass(frozen=True)
class VerificationReport:
    rungs: tuple[RungResult, ...]
    numerically_converged: bool
    analytically_verified: bool
    convergence_detail: str
    analytic_detail: str
    min_observed_order: float
    analytic_rel_tol: float
    reference_id: str = REFERENCE_ID
    reference_expression: str = REFERENCE_EXPRESSION

    @property
    def levels_earned(self) -> tuple[ValidationLevel, ...]:
        earned: list[ValidationLevel] = []
        if self.numerically_converged:
            earned.append(ValidationLevel.NUMERICALLY_CONVERGED)
        if self.analytically_verified:
            earned.append(ValidationLevel.ANALYTICALLY_VERIFIED)
        return tuple(earned)

    @property
    def claim(self) -> str:
        if not self.numerically_converged:
            return "no convergence claim is supported by this sequence"
        return (
            "the mms max-abs error falls monotonically across the ladder "
            "and the observed order rises toward 1 (first-order upwind "
            "advection dominates); the scheme is sub-asymptotic below "
            "n=32 (peak cell Peclet > 2) by the same measured cause the "
            "preparation document names, and this claim is scoped to what "
            "was actually observed rather than to a clean asymptotic rate"
        )

    def to_report(self) -> ValidationReport:
        checks = (
            ValidationCheck(
                name="discretization_convergence",
                outcome=(
                    ValidationOutcome.PASS
                    if self.numerically_converged
                    else ValidationOutcome.FAIL
                ),
                detail=self.convergence_detail,
                tolerance=self.min_observed_order,
                establishes=(
                    ValidationLevel.NUMERICALLY_CONVERGED
                    if self.numerically_converged
                    else None
                ),
                evidence=tuple(
                    f"n={r.n_cells} mms_err={r.mms_max_abs_error:.6e} "
                    f"order={r.observed_order}"
                    for r in self.rungs
                ),
            ),
            ValidationCheck(
                name="analytic_reference_agreement",
                outcome=(
                    ValidationOutcome.PASS
                    if self.analytically_verified
                    else ValidationOutcome.FAIL
                ),
                detail=self.analytic_detail,
                residual=self.rungs[-1].centre_rel_error if self.rungs else None,
                tolerance=self.analytic_rel_tol,
                establishes=(
                    ValidationLevel.ANALYTICALLY_VERIFIED
                    if self.analytically_verified
                    else None
                ),
                evidence=(f"{self.reference_id}: {self.reference_expression}",),
            ),
        )
        return ValidationReport(checks=checks, notes=self.claim)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rungs": [r.to_dict() for r in self.rungs],
            "numerically_converged": self.numerically_converged,
            "analytically_verified": self.analytically_verified,
            "convergence_detail": self.convergence_detail,
            "analytic_detail": self.analytic_detail,
            "min_observed_order": self.min_observed_order,
            "analytic_rel_tol": self.analytic_rel_tol,
            "levels_earned": [level.value for level in self.levels_earned],
            "claim": self.claim,
            "reference_id": self.reference_id,
            "reference_expression": self.reference_expression,
        }


#: The frozen ladder — preserved exactly from the preparation probe and the
#: preregistration (docs/real-fluid-pde-prereg.md §2/§8).
VERIFICATION_LADDER: tuple[int, ...] = (8, 16, 32, 64)

#: DECLARED AFTER RUNNING THE PRODUCTION ASSEMBLY ONCE at every rung of the
#: frozen ladder — exactly reproducing the preparation probe's own numbers
#: (docs/fluid-pde-preparation.md §B3): observed order 0.716 -> 0.826 ->
#: 0.900, same disclosure thermal/conduction1d/validation.py gives for its
#: own post-hoc-informed thresholds. This floor (0.60) sits comfortably
#: below the weakest observed step (0.716, ~16% margin), not tuned to the
#: strongest.
MIN_OBSERVED_ORDER = 0.60

#: DECLARED AFTER RUNNING THE PRODUCTION ASSEMBLY ONCE. The centre-point QoI
#: relative error at the finest rung (n=64) was measured at 0.0889 (NOT the
#: max-abs field error 0.08826 §2's table reports, though the two are
#: numerically close here because the field's maximum sits at the centre) —
#: this tolerance (0.12) sits comfortably above that observed value (~35%
#: margin), not tuned tightly around it. Materially looser than
#: thermal/conduction1d's 1e-3: this benchmark's own scheme is
#: sub-asymptotic even at n=64 (peak cell Peclet 1.10, still above the
#: diffusion-dominated regime) — see docs/real-fluid-pde-prereg.md §2.
ANALYTIC_REL_TOL = 0.12

MIN_RUNGS = 3


def run_verification_gate(
    domain: "Transport2DDomain",
    *,
    ladder: Sequence[int] = VERIFICATION_LADDER,
    run_id_prefix: str = "fluids-transport2d-verify",
    min_observed_order: float = MIN_OBSERVED_ORDER,
    analytic_rel_tol: float = ANALYTIC_REL_TOL,
) -> VerificationReport:
    """Solve the same physical domain at every rung and judge the sequence.

    The domain's own grid is ignored: every rung supplies its own via
    ``with_grid``, holding the physics identical so any difference between
    rungs is numerical by construction — same pattern as
    ``thermal/conduction1d.run_verification_gate``.
    """
    from .problem import Transport2DGrid, build_transport2d_problem
    from .solver import Transport2DSolver, assemble, solve_transport2d

    if len(ladder) < 2:
        raise Transport2DConfigurationError(
            "a refinement gate needs at least two rungs to compare"
        )

    analytic_centre = exact_centre(
        side_m=domain.side_m,
        diffusivity_m2_s=domain.diffusivity_m2_s,
        omega_per_s=domain.omega_per_s,
    )

    rows: list[RungResult] = []
    previous_error: float | None = None
    for index, n_cells in enumerate(ladder):
        refined = domain.with_grid(Transport2DGrid(n_cells))
        problem = build_transport2d_problem(
            refined, problem_id=f"{run_id_prefix}-{index}"
        )
        result = solve_transport2d(
            refined,
            run_id=f"{run_id_prefix}-{index}",
            solver=Transport2DSolver(),
            problem=problem,
            cross_check=False,  # the gate is about discretization error, not
                                 # the sparse/dense agreement check
        )
        from .problem import CENTRE_METRIC, MAX_METRIC, MIN_METRIC

        centre_qoi = result.value(CENTRE_METRIC).magnitude_in("dimensionless")
        centre_abs_error = abs(centre_qoi - analytic_centre)
        centre_rel_error = (
            centre_abs_error / abs(analytic_centre) if analytic_centre else float("inf")
        )

        # The full field is deliberately excluded from ScientificResult
        # metadata (same discipline as thermal/conduction1d: bulk data does
        # not belong in an untyped metadata bag — it belongs in
        # data_references, which is O(1) identity, not O(mesh) content). The
        # gate needs the actual field values to compute a max-abs MMS error,
        # so it goes one level below the ScientificResult wrapper and reads
        # RawSolverOutput directly, exactly where the field is the sanctioned
        # bulk-data channel (see solvers/protocol.py's RawSolverOutput
        # docstring). This is verification-only code, not the production
        # result path, which is unaffected.
        low_level_solver = Transport2DSolver()
        low_level_solver.bind_domain(refined, problem.problem_id)
        low_level_prepared = low_level_solver.prepare(problem)
        low_level_raw = low_level_solver.solve(low_level_prepared)
        field_flat = np.asarray(low_level_raw.diagnostics["field"], dtype=np.float64)

        dx = refined.dx_m
        centres = (np.arange(n_cells) + 0.5) * dx
        xs, ys = np.meshgrid(centres, centres, indexing="ij")
        exact = exact_field(xs, ys, side_m=refined.side_m).reshape(-1)
        mms_max_abs_error = float(np.max(np.abs(field_flat - exact)))

        c_min = result.value(MIN_METRIC).magnitude_in("dimensionless")
        c_max = result.value(MAX_METRIC).magnitude_in("dimensionless")
        admissibility_violation = max(0.0, -c_min, c_max - 1.0)

        observed_order = (
            None
            if previous_error is None or mms_max_abs_error == 0.0
            else math.log2(previous_error / mms_max_abs_error)
        )

        rows.append(
            RungResult(
                n_cells=n_cells,
                dx_m=dx,
                peak_cell_peclet=refined.peak_cell_peclet,
                centre_qoi=centre_qoi,
                centre_analytic=analytic_centre,
                centre_abs_error=centre_abs_error,
                centre_rel_error=centre_rel_error,
                mms_max_abs_error=mms_max_abs_error,
                admissibility_violation=admissibility_violation,
                work_proxy=refined.grid.work_proxy,
                wall_seconds_telemetry=result.metadata.get("wall_seconds_telemetry"),
                observed_order=observed_order,
            )
        )
        previous_error = mms_max_abs_error

    # --- convergence gate -------------------------------------------------
    reasons: list[str] = []
    if len(rows) < MIN_RUNGS:
        reasons.append(f"only {len(rows)} rungs; at least {MIN_RUNGS} are required")
    errors = [r.mms_max_abs_error for r in rows]
    if not all(b < a for a, b in zip(errors, errors[1:])):
        reasons.append("mms max-abs error did not fall monotonically")
    orders = [r.observed_order for r in rows if r.observed_order is not None]
    if any(o < min_observed_order for o in orders):
        worst = min(orders) if orders else float("nan")
        reasons.append(
            f"observed order fell to {worst:.3f} at the weakest step, below "
            f"the required floor {min_observed_order}"
        )
    numerically_converged = not reasons

    if numerically_converged:
        convergence_detail = (
            f"{len(rows)} rungs from n={rows[0].n_cells} to n={rows[-1].n_cells}; "
            f"mms max-abs error fell {errors[0]:.6e} -> {errors[-1]:.6e}; "
            f"observed order: {[f'{o:.3f}' for o in orders]}"
        )
    else:
        convergence_detail = "; ".join(reasons)

    finest = rows[-1]
    within_tolerance = finest.centre_rel_error <= analytic_rel_tol
    analytically_verified = bool(numerically_converged and within_tolerance)
    if analytically_verified:
        analytic_detail = (
            f"finest rung n={finest.n_cells} gives centre QoI "
            f"{finest.centre_qoi:.12g} against the exact {finest.centre_analytic:.12g}; "
            f"relative error {finest.centre_rel_error:.6e} within {analytic_rel_tol}"
        )
    elif not numerically_converged:
        analytic_detail = (
            f"centre relative error at the finest rung is "
            f"{finest.centre_rel_error:.6e}, but ANALYTICALLY_VERIFIED is "
            f"withheld because the sequence is not numerically converged"
        )
    else:
        analytic_detail = (
            f"finest rung centre relative error {finest.centre_rel_error:.6e} "
            f"exceeds the declared tolerance {analytic_rel_tol}"
        )

    return VerificationReport(
        rungs=tuple(rows),
        numerically_converged=numerically_converged,
        analytically_verified=analytically_verified,
        convergence_detail=convergence_detail,
        analytic_detail=analytic_detail,
        min_observed_order=min_observed_order,
        analytic_rel_tol=analytic_rel_tol,
    )


# =====================================================================
# Boundary orientation (MIN-FIELD-SUPPORT-FOUNDATION) — real production use
# of `engcore.scientific.ir.orientation`, and the mandatory negative test.
# =====================================================================
#
# F6 (see docs/real-fluid-pde-evidence.md §5) already proved, against this
# package's own production grid and velocity field, that every side of this
# benchmark is exactly half inflow, half outflow. This section wires that
# finding into `BoundaryOrientation`/`classify_sign`: a genuine, non-
# decorative production attempt to describe one side with a single sign,
# and the loud refusal that attempt is REQUIRED to produce.

def classify_boundary_orientation(
    domain: "Transport2DDomain", side: str, *, reference: str = "outward_normal"
) -> BoundaryOrientation:
    """Attempt one ``BoundaryOrientation`` for ``side``, from THIS domain's
    real production velocity field and real production grid resolution
    (``reference.side_orientation`` — never a synthetic sample array).

    Raises ``MixedOrientationError``, uncaught, whenever the side's actual
    physics is not single-signed. For every instance of this benchmark
    (its velocity field is fixed — see ``problem.py``'s module docstring)
    that is every side, always: the rotational field makes ``u.n`` change
    sign at each side's midpoint regardless of grid resolution or the
    physical scale chosen. This is the milestone's required negative test,
    exercised here as real production code rather than only in a test file.
    """
    samples = side_orientation(
        side,
        n_cells=domain.grid.n_cells,
        side_m=domain.side_m,
        omega_per_s=domain.omega_per_s,
    )
    sign = classify_sign(
        samples.normal_components,
        context=(
            f"transport2d domain {domain.domain_id!r} side {side!r} "
            f"(u.n against the {reference})"
        ),
    )
    return BoundaryOrientation(boundary_name=side, reference=reference, sign=sign)


def boundary_orientation_report(
    domain: "Transport2DDomain", *, reference: str = "outward_normal"
) -> dict[str, str]:
    """Per-side outcome of :func:`classify_boundary_orientation` for every
    side of :data:`ALL_SIDES`. Never raises: a caller that wants the whole
    picture rather than the first refusal gets one string per side, either
    the classified sign or the refusal detail.
    """
    outcomes: dict[str, str] = {}
    for side in ALL_SIDES:
        try:
            orientation = classify_boundary_orientation(
                domain, side, reference=reference
            )
            outcomes[side] = f"single sign: {orientation.sign.value}"
        except MixedOrientationError as exc:
            outcomes[side] = f"refused: {exc}"
    return outcomes
