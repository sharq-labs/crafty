"""CSTRSolver — a ScientificSolver over SciPy's stiff initial-value integrators.

The five lifecycle stages stay strictly separated, exactly as the Electrical and
Thermal domains keep them:

``supports`` (capability question, never executes)
→ ``prepare`` (build the right-hand side, the analytic Jacobian, and the
   declaration's validity assessment)
→ ``solve`` (SciPy adaptive implicit integration, raw floats)
→ ``extract_metrics`` (units restored)
→ ``validate`` (independent checks)

WHY BDF, AND WHY RADAU AS THE SECOND ARM
-----------------------------------------
The system is stiff: ``dk/dT = k E/(R T**2)`` makes the chemical mode orders of
magnitude faster than the flow mode ``q/V`` during ignition, while the horizon
of interest is set by the slow mode. An explicit method must resolve the fast
mode for stability even where it is dynamically irrelevant, so its cost is set
by the stiffness ratio rather than by the accuracy wanted.

BDF is the production method. Variable-order (1-5) backward differentiation
with a quasi-Newton corrector and an analytic Jacobian: the standard choice for
stiff chemical kinetics, cheap per step because it reuses factorizations across
steps, and L-stable at every order it uses here.

Radau (5th-order Radau IIA, fully implicit Runge-Kutta) is the cross-method
arm. It is a genuinely different family — one-step rather than multistep, so
its error propagation and its startup behaviour have nothing structural in
common with BDF's — while also being L-stable, which is required: the fast
chemical mode must be *damped*, not oscillated, which is exactly what rules out
the trapezoidal/Crank-Nicolson family for this problem.

RK45 is admitted for one purpose only: as a measuring instrument. The ratio of
its right-hand-side evaluations to BDF's is how this domain evidences that a
regime is stiff, rather than asserting it. It is never a production method for
a stiff regime, and nothing here selects a method.

LSODA is deliberately excluded. It switches between stiff and non-stiff
internally, so a work count from it cannot be attributed to one method, and it
would corrupt the only stiffness measurement this domain has.

WHAT THIS SOLVER DOES NOT CLAIM
--------------------------------
``validate`` never awards ``NUMERICALLY_CONVERGED``. ``solve_ivp`` reporting
``status == 0`` means its local error estimate stayed under the tolerance it
was given — it is the integrator's opinion of its own step control, and it is
equally confident at rtol=1e-2 and rtol=1e-12. Numerical adequacy is a claim
about *tolerance independence*, which needs more than one solve, so it lives in
:mod:`validation` and is a claim about a sequence. The per-solve report says so
with an explicit NOT_RUN check rather than staying silent about it.

Nor does a successful integration mean a physically admissible one. A stiff
solve at loose tolerance can undershoot the concentration below zero and still
report success, and that result is executed-but-unusable rather than failed.
The per-solve report carries that as a FAILing state-admissibility check, which
is what makes ``ScientificResult.is_usable`` False while ``convergence``
correctly remains CONVERGED.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
from scipy.integrate import solve_ivp

from ....scientific.ir.problem import ScientificProblem
from ....scientific.results.provenance import ProvenanceRecord
from ....scientific.results.result import ScientificResult
from ....scientific.results.uncertainty import Uncertainty
from ....scientific.results.validation import ValidationReport
from ....scientific.solvers.protocol import (
    ConvergenceState,
    PreparedSolve,
    RawSolverOutput,
    SolverIdentity,
    SolverSettings,
)
from ....scientific.units.quantity import Quantity
from .errors import (
    IntegrationBudgetExceeded,
    ReactorBindingError,
    ReactorConfigurationError,
)
from .problem import (
    CA_FINAL_METRIC,
    CONVERSION_METRIC,
    CSTR_MODEL,
    CSTR_MODELS,
    KINETICS_CSTR_NONISOTHERMAL,
    METRIC_UNITS,
    T_AT_MAX_METRIC,
    T_FINAL_METRIC,
    T_MAX_METRIC,
    MOLAR_GAS_CONSTANT,
    GAS_CONSTANT_UNIT,
    ReactorRun,
    build_cstr_problem,
    cstr_solver_capabilities,
    verify_problem_matches_run,
)
from .validation import CSTRValidationSettings, build_validation_report

SOLVER_ID = "kinetics.cstr.scipy_implicit_ivp"
SOLVER_VERSION = "0.1.0"
BACKEND = "scipy.integrate.solve_ivp"

_R = MOLAR_GAS_CONSTANT.magnitude_in(GAS_CONSTANT_UNIT)


@dataclass
class _EvaluationCounter:
    """Right-hand-side evaluation count and the budget it must respect."""

    budget: int
    count: int = 0
    non_finite_events: int = 0
    non_positive_temperature_events: int = 0

    def charge(self, t: float) -> None:
        self.count += 1
        if self.count > self.budget:
            raise IntegrationBudgetExceeded(
                f"right-hand-side evaluation budget of {self.budget} exhausted "
                f"at t = {t:.6g} s; the integration was still progressing when "
                f"it was stopped",
                evaluations=self.count,
                budget=self.budget,
                t=t,
            )


@dataclass(frozen=True)
class PreparedCSTRSystem:
    """The assembled right-hand side, its Jacobian, and the declaration."""

    run: ReactorRun
    rhs: Any                    # callable (t, y) -> ndarray
    jacobian: Any               # callable (t, y) -> ndarray
    counter: _EvaluationCounter
    output_grid: np.ndarray     # uniform reporting/checking grid on [0, t_end]

    @property
    def initial_state(self) -> np.ndarray:
        return np.array(
            [self.run.ca0_mol_per_m3, self.run.t0_k], dtype=np.float64
        )


def assemble(run: ReactorRun) -> PreparedCSTRSystem:
    """Build the right-hand side and analytic Jacobian for one run.

    Closures over plain floats: this is the numeric kernel, and it is the one
    place in the domain where unit-carrying quantities have been left behind on
    purpose. They come back in ``extract_metrics``.

    The Jacobian is supplied analytically rather than left to finite
    differences. For a stiff system the Newton corrector's convergence is
    governed by Jacobian quality, and a differenced Arrhenius derivative is
    exactly where that quality is worst.
    """
    chemistry = run.chemistry
    operation = run.operation

    a = operation.dilution_rate_per_s
    caf = operation.caf_mol_per_m3
    tf = operation.tf_k
    tc = operation.tc_k
    beta = chemistry.beta_m3_k_per_mol
    gamma = run.gamma_per_s
    k0 = chemistry.k0_per_s
    energy = chemistry.e_j_per_mol

    counter = _EvaluationCounter(budget=run.integration.max_rhs_evaluations)

    def rate_constant(temperature: float) -> float:
        # Outside the domain of the model the Arrhenius factor is not merely
        # inaccurate, it is undefined. Returning NaN lets the integrator reject
        # the step rather than continuing on a fabricated number.
        if not np.isfinite(temperature) or temperature <= 0.0:
            return float("nan")
        with np.errstate(over="ignore"):
            return float(k0 * np.exp(-energy / (_R * temperature)))

    def rhs(t: float, y: np.ndarray) -> np.ndarray:
        counter.charge(float(t))
        concentration = float(y[0])
        temperature = float(y[1])
        if temperature <= 0.0 or not np.isfinite(temperature):
            counter.non_positive_temperature_events += 1
        k = rate_constant(temperature)
        reaction = k * concentration
        d_concentration = a * (caf - concentration) - reaction
        d_temperature = (
            a * (tf - temperature) + beta * reaction - gamma * (temperature - tc)
        )
        out = np.array([d_concentration, d_temperature], dtype=np.float64)
        if not np.all(np.isfinite(out)):
            counter.non_finite_events += 1
        return out

    def jacobian(t: float, y: np.ndarray) -> np.ndarray:
        concentration = float(y[0])
        temperature = float(y[1])
        k = rate_constant(temperature)
        if not np.isfinite(k) or temperature <= 0.0:
            return np.full((2, 2), np.nan, dtype=np.float64)
        with np.errstate(over="ignore", invalid="ignore"):
            dk_dt = k * energy / (_R * temperature * temperature)
        return np.array(
            [
                [-(a + k), -concentration * dk_dt],
                [beta * k, -(a + gamma) + beta * concentration * dk_dt],
            ],
            dtype=np.float64,
        )

    grid = np.linspace(
        0.0, operation.end_time_s, int(run.integration.n_output_points)
    )
    return PreparedCSTRSystem(
        run=run, rhs=rhs, jacobian=jacobian, counter=counter, output_grid=grid
    )


@dataclass
class CSTRSolver:
    """Transient non-isothermal CSTR solver satisfying the ScientificSolver protocol."""

    settings: CSTRValidationSettings = field(default_factory=CSTRValidationSettings)
    _runs: dict[str, ReactorRun] = field(default_factory=dict, repr=False)

    # ---- identity / capability ------------------------------------------
    @property
    def identity(self) -> SolverIdentity:
        import scipy

        return SolverIdentity(
            SOLVER_ID, SOLVER_VERSION, backend=f"{BACKEND}/scipy-{scipy.__version__}"
        )

    @property
    def capabilities(self):
        return cstr_solver_capabilities()

    def solver_settings(self, run: ReactorRun) -> SolverSettings:
        """Numerical settings actually used, recorded for provenance."""
        return SolverSettings(
            tolerances=run.integration.as_tolerance_mapping(),
            options={
                "method": run.integration.method,
                "jacobian": "analytic",
                "n_output_points": run.integration.n_output_points,
                "dense_output": True,
                "backend": BACKEND,
            },
        )

    # ---- domain-local run binding ----------------------------------------
    def bind_run(self, run: ReactorRun, problem_id: str) -> None:
        """Associate a reactor run with the problem describing it.

        Rebinding the same physics at a different tolerance or method is
        allowed — that is what the tolerance ladder and the cross-method arm
        do. Rebinding *different physics* to the same problem id is refused,
        because two results would then claim one identity while describing
        different reactors.
        """
        if not isinstance(run, ReactorRun):
            raise ReactorConfigurationError("bind_run expects a ReactorRun")
        key = str(problem_id)
        existing = self._runs.get(key)
        if (
            existing is not None
            and existing.physics_fingerprint() != run.physics_fingerprint()
        ):
            raise ReactorBindingError(
                f"problem {key!r} is already bound to a different reactor "
                f"(bound {existing.physics_fingerprint()[:12]}…, incoming "
                f"{run.physics_fingerprint()[:12]}…); rebinding to different "
                f"physics is refused — use a distinct problem id"
            )
        self._runs[key] = run

    def bound_run(self, problem_id: str) -> ReactorRun | None:
        return self._runs.get(str(problem_id))

    # ---- lifecycle --------------------------------------------------------
    def supports(self, problem: ScientificProblem) -> bool:
        """Capability question only — never attempts a solve."""
        if not isinstance(problem, ScientificProblem):
            return False
        declared = {capability.name for capability in self.capabilities}
        if not set(problem.required_capabilities).issubset(declared):
            return False
        domain_models = {model.model_id for model in CSTR_MODELS}
        referenced = {reference.model_id for reference in problem.models}
        if not referenced & domain_models:
            return False
        return KINETICS_CSTR_NONISOTHERMAL.name in problem.required_capabilities

    def prepare(self, problem: ScientificProblem) -> PreparedSolve:
        run = self.bound_run(problem.problem_id)
        if run is None:
            raise ReactorConfigurationError(
                f"no reactor bound for problem {problem.problem_id!r}; call "
                f"bind_run() first — the universal IR carries no chemistry"
            )
        if not self.supports(problem):
            raise ReactorConfigurationError(
                f"problem {problem.problem_id!r} is not a transient "
                f"non-isothermal CSTR analysis"
            )
        verify_problem_matches_run(problem, run)

        # The declaration is assessed against the MODEL's own validity domain
        # here, before any integration. The constructors already refuse the
        # gross violations; this records the model's verdict as evidence rather
        # than relying on the constructors having been the only gate.
        assessment = CSTR_MODEL.assess_validity(run.validity_context())

        system = assemble(run)
        integration = run.integration
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.solver_settings(run),
            payload=system,
            notes=(
                f"method={integration.method} rtol={integration.rtol:.3g} "
                f"atol=({integration.atol_concentration:.3g} mol/m**3, "
                f"{integration.atol_temperature:.3g} K) "
                f"budget={integration.max_rhs_evaluations} rhs evaluations",
                f"tau={run.operation.residence_time_s:.6g} s, "
                f"gamma={run.gamma_per_s:.6g} 1/s, "
                f"adiabatic_rise={run.adiabatic_rise_k:.6g} K, "
                f"Da(T_f)={run.damkohler_at_feed_temperature:.6g}",
                f"model validity assessment: {assessment.status.value}",
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        """Integrate, and classify what actually happened.

        Five outcomes are kept distinct, because collapsing them is how the
        difference between "the reactor cannot be simulated" and "this run was
        given too small a budget" gets lost:

        MAX_ITERATIONS  the explicit evaluation budget was exhausted while the
                        integration was still progressing
        FAILED          the backend raised, or reported an input/step failure
        NOT_CONVERGED   the step size collapsed below what the arithmetic can
                        represent (SciPy status -1)
        DIVERGED        the trajectory went non-finite
        CONVERGED       the integrator finished the horizon under its tolerance
        """
        system: PreparedCSTRSystem = prepared.payload
        run = system.run
        integration = run.integration
        started = time.perf_counter()

        common: dict[str, Any] = {
            "method": integration.method,
            "rtol": integration.rtol,
            "atol_concentration": integration.atol_concentration,
            "atol_temperature": integration.atol_temperature,
            "rhs_budget": integration.max_rhs_evaluations,
            "residence_time_s": run.operation.residence_time_s,
            "end_time_s": run.operation.end_time_s,
            "gamma_per_s": run.gamma_per_s,
            "adiabatic": run.operation.is_adiabatic,
            "physics_fingerprint": run.physics_fingerprint(),
        }

        # An analytic Jacobian is only used by the implicit methods; passing it
        # to RK45 is an error in SciPy, and the probe must not be handed an
        # advantage the production method does not also have.
        kwargs: dict[str, Any] = {}
        if integration.is_stiff_method:
            kwargs["jac"] = system.jacobian

        try:
            solution = solve_ivp(
                system.rhs,
                (0.0, run.operation.end_time_s),
                system.initial_state,
                method=integration.method,
                rtol=integration.rtol,
                atol=np.array(integration.atol_vector, dtype=np.float64),
                dense_output=True,
                **kwargs,
            )
        except IntegrationBudgetExceeded as exc:
            return RawSolverOutput(
                convergence=ConvergenceState.MAX_ITERATIONS,
                warnings=(
                    f"right-hand-side evaluation budget of {exc.budget} "
                    f"exhausted at t = {exc.t:.6g} s of "
                    f"{run.operation.end_time_s:.6g} s",
                ),
                iterations=exc.evaluations,
                wall_seconds=time.perf_counter() - started,
                diagnostics={
                    **common,
                    "outcome": "rhs_budget_exhausted",
                    "rhs_evaluations": exc.evaluations,
                    "abort_time_s": exc.t,
                    "fraction_of_horizon_completed": (
                        exc.t / run.operation.end_time_s
                        if run.operation.end_time_s
                        else 0.0
                    ),
                    "non_finite_rhs_events": system.counter.non_finite_events,
                    "non_positive_temperature_events":
                        system.counter.non_positive_temperature_events,
                },
            )
        except Exception as exc:  # backend raised for any other reason
            return RawSolverOutput(
                convergence=ConvergenceState.FAILED,
                warnings=(f"integrator raised {type(exc).__name__}",),
                iterations=system.counter.count,
                wall_seconds=time.perf_counter() - started,
                diagnostics={
                    **common,
                    "outcome": "backend_exception",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "rhs_evaluations": system.counter.count,
                    "non_finite_rhs_events": system.counter.non_finite_events,
                },
            )

        wall = time.perf_counter() - started
        times = np.asarray(solution.t, dtype=np.float64)
        states = np.asarray(solution.y, dtype=np.float64)
        finite_trajectory = bool(np.all(np.isfinite(states)))

        # SciPy's own accounting, kept alongside our budget counter. They
        # measure the same thing by different routes, and a disagreement is
        # itself worth seeing.
        work = {
            "rhs_evaluations": int(system.counter.count),
            "scipy_nfev": int(getattr(solution, "nfev", 0)),
            "scipy_njev": int(getattr(solution, "njev", 0)),
            "scipy_nlu": int(getattr(solution, "nlu", 0)),
            "accepted_steps": int(times.size - 1) if times.size else 0,
            "non_finite_rhs_events": system.counter.non_finite_events,
            "non_positive_temperature_events":
                system.counter.non_positive_temperature_events,
        }

        if solution.status == -1 or not finite_trajectory:
            # A partial trajectory is real evidence and is preserved: this is
            # the one layer where non-finite values may be recorded honestly.
            convergence = (
                ConvergenceState.DIVERGED
                if not finite_trajectory
                else ConvergenceState.NOT_CONVERGED
            )
            reached = float(times[-1]) if times.size else 0.0
            return RawSolverOutput(
                convergence=convergence,
                warnings=(
                    f"{solution.message}"
                    if solution.status == -1
                    else "trajectory contains non-finite values",
                ),
                iterations=int(system.counter.count),
                wall_seconds=wall,
                diagnostics={
                    **common,
                    **work,
                    "outcome": (
                        "step_size_collapse"
                        if solution.status == -1
                        else "non_finite_trajectory"
                    ),
                    "scipy_status": int(solution.status),
                    "scipy_message": str(solution.message),
                    "reached_time_s": reached,
                    "fraction_of_horizon_completed": (
                        reached / run.operation.end_time_s
                        if run.operation.end_time_s
                        else 0.0
                    ),
                    "trajectory_finite": finite_trajectory,
                    "partial_time_s": [float(v) for v in times],
                    "partial_concentration_mol_per_m3":
                        [float(v) for v in states[0]],
                    "partial_temperature_k": [float(v) for v in states[1]],
                },
            )

        if solution.status != 0:
            return RawSolverOutput(
                convergence=ConvergenceState.FAILED,
                warnings=(str(solution.message),),
                iterations=int(system.counter.count),
                wall_seconds=wall,
                diagnostics={
                    **common,
                    **work,
                    "outcome": "unexpected_status",
                    "scipy_status": int(solution.status),
                    "scipy_message": str(solution.message),
                },
            )

        # --- completed horizon -------------------------------------------
        concentration = states[0]
        temperature = states[1]
        peak_index = int(np.argmax(temperature))

        # The uniform grid is used for the invariant/conservation checks and
        # for cross-run comparison; it never influenced the integration path.
        grid = system.output_grid
        sampled = np.asarray(solution.sol(grid), dtype=np.float64)

        caf = run.operation.caf_mol_per_m3
        final_concentration = float(concentration[-1])
        conversion = (
            (caf - final_concentration) / caf if caf > 0.0 else 0.0
        )

        values = {
            CA_FINAL_METRIC: final_concentration,
            T_FINAL_METRIC: float(temperature[-1]),
            # Maximum over the integrator's OWN accepted steps, which cluster
            # where the solution moves fastest — that is, at the peak. Reading
            # it from a uniform grid instead would under-resolve a sharp
            # ignition and report a peak that never happened to be sampled.
            T_MAX_METRIC: float(temperature[peak_index]),
            T_AT_MAX_METRIC: float(times[peak_index]),
            CONVERSION_METRIC: float(conversion),
        }

        return RawSolverOutput(
            convergence=ConvergenceState.CONVERGED,
            values=values,
            residuals={},
            iterations=int(system.counter.count),
            wall_seconds=wall,
            diagnostics={
                **common,
                **work,
                "outcome": "completed_horizon",
                "scipy_status": int(solution.status),
                "scipy_message": str(solution.message),
                "trajectory_finite": True,
                "reached_time_s": float(times[-1]),
                "fraction_of_horizon_completed": 1.0,
                "min_concentration_mol_per_m3": float(np.min(concentration)),
                "max_concentration_mol_per_m3": float(np.max(concentration)),
                "min_temperature_k": float(np.min(temperature)),
                "max_temperature_k": float(np.max(temperature)),
                "peak_time_s": float(times[peak_index]),
                "concentration_ceiling_mol_per_m3":
                    run.concentration_ceiling_mol_per_m3,
                # The uniform sample used by the conservation/invariant checks.
                "grid_time_s": [float(v) for v in grid],
                "grid_concentration_mol_per_m3": [float(v) for v in sampled[0]],
                "grid_temperature_k": [float(v) for v in sampled[1]],
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        """Restore units. This is the boundary back into the unit-aware world.

        A run that did not complete the horizon yields no metrics: a partial
        trajectory has no "final concentration", and inventing one from the
        last point reached would report a number for a question that was never
        answered. The partial trajectory itself survives in the raw
        diagnostics, where it belongs.
        """
        if not raw.succeeded:
            return {}
        return {
            name: Quantity(value, METRIC_UNITS[name])
            for name, value in raw.values.items()
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        system: PreparedCSTRSystem = prepared.payload
        return build_validation_report(system.run, raw, self.settings)


# =====================================================================
# Public wrapper
# =====================================================================

def solve_reactor(
    run: ReactorRun,
    *,
    run_id: str,
    solver: CSTRSolver | None = None,
    problem: ScientificProblem | None = None,
    software_version: str = "engcore.domains.kinetics.cstr/0.1.0",
    git_commit: str | None = None,
    timestamp: str | None = None,
    environment: Mapping[str, str] | None = None,
    parent_run_id: str | None = None,
) -> ScientificResult:
    """Run the full contract lifecycle for one reactor and return a result.

    Orchestration only: every stage goes through the protocol.

    The large trajectory arrays are deliberately excluded from the result's
    metadata — they are evidence for the validation stage, not a diagnostic a
    reader of the result needs, and carrying thousands of points into every
    record would make the serialized artifacts unreadable. Everything scalar
    that describes how the solve went does survive, because E1 recorded that
    discarding it forces an experiment to re-derive it with a second solve.
    """
    solver = solver or CSTRSolver()
    problem = problem or build_cstr_problem(run)
    verify_problem_matches_run(problem, run)
    solver.bind_run(run, problem.problem_id)

    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    report = solver.validate(prepared, raw)

    model_identities = tuple((m.model_id, m.version) for m in CSTR_MODELS)
    assumptions = CSTR_MODEL.assumptions

    inputs = {
        "k0": run.chemistry.k0,
        "activation_energy": run.chemistry.activation_energy,
        "heat_of_reaction": run.chemistry.heat_of_reaction,
        "density": run.chemistry.density,
        "heat_capacity": run.chemistry.heat_capacity,
        "volume": run.operation.volume,
        "flow_rate": run.operation.flow_rate,
        "feed_concentration": run.operation.feed_concentration,
        "feed_temperature": run.operation.feed_temperature,
        "coolant_temperature": run.operation.coolant_temperature,
        "ua": run.operation.ua,
        "end_time": run.operation.end_time,
        "initial_concentration": run.initial_concentration,
        "initial_temperature": run.initial_temperature,
        "molar_gas_constant": MOLAR_GAS_CONSTANT,
    }

    bulky = {
        "grid_time_s",
        "grid_concentration_mol_per_m3",
        "grid_temperature_k",
        "partial_time_s",
        "partial_concentration_mol_per_m3",
        "partial_temperature_k",
    }
    diagnostics = {k: v for k, v in raw.diagnostics.items() if k not in bulky}

    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version=software_version,
        git_commit=git_commit,
        models=model_identities,
        solvers=((SOLVER_ID, SOLVER_VERSION),),
        inputs=inputs,
        assumptions=assumptions,
        tolerances=run.integration.as_tolerance_mapping(),
        environment=dict(environment or {}),
        timestamp=timestamp,
        parent_run_id=parent_run_id,
        metadata={
            "run_label": run.run_label,
            "physics_fingerprint": run.physics_fingerprint(),
            "integration_method": run.integration.method,
            "jacobian": "analytic",
            "backend": BACKEND,
            "solver_backend_identity": solver.identity.backend,
            "run_canonical": run.to_dict(),
        },
    )

    return ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=model_identities,
        solver=solver.identity,
        convergence=raw.convergence,
        validation=report,
        # No uncertainty quantification is performed by a single solve. The
        # tolerance ladder quantifies the numerical component and nothing here
        # quantifies the model component, so anything but UNKNOWN would be
        # fabrication.
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification performed by this solve; the "
                "numerical component is estimated by the tolerance gate and "
                "the model-form component is not estimated at all"
            )
            for name in metrics
        },
        assumptions=assumptions,
        warnings=raw.warnings,
        provenance=provenance,
        metadata={
            "run_label": run.run_label,
            "physics_fingerprint": run.physics_fingerprint(),
            "numerics": diagnostics,
            "iterations": raw.iterations,
            # Telemetry only. Never a scientific score.
            "wall_seconds_telemetry": raw.wall_seconds,
        },
    )
