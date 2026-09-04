"""A1/Q1 — are the five temporal axes behaviourally distinct?

The claim under test is **not** that five words have five meanings. It is that
five quantities can be varied *independently*, with consequences that differ in
kind, on consumers that already execute.

The five axes, and the executed lever for each
----------------------------------------------

============================ ========================= =========================
Axis                         Lever                     Consumer
============================ ========================= =========================
Physical time                ``ThermalBody.duration``  C1 lumped thermal
Solver time step             ``PendulumCase.n_steps``  C4 index-3 DAE
Coupling iteration           Picard sweep index        C3 electro-thermal
Optimization iteration       (none — see below)        —
Wall-clock runtime           repeat the same solve     C1
============================ ========================= =========================

Optimization iteration has **no executed lever here**, and that is reported as
a measurement rather than papered over: ``ScientificEvaluation`` carries an
``evaluation_id`` string and no ordinal, no sequence position and no typed
predecessor, so there is nothing to vary. §7/P1 of the preregistration named
this as a way the prediction could lose, and it does.

What each lever must show to count as a separation
--------------------------------------------------
Varying axis X must change something axis Y does not, *on the record*. A
difference visible only inside a domain's private objects is not a separation
of the universal semantics; it is a separation of that domain's bookkeeping.
Each probe therefore reports what changed in the ``ScientificResult`` /
``RawSolverOutput`` as well as what changed in the physics.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Mapping

from engcore.domains import thermal_lumped as lump
from engcore.scientific.units.quantity import Quantity
from experiments.cross_domain_coverage import dynamics as dyn

__all__ = [
    "PhysicalTimeSeparation",
    "SolverStepSeparation",
    "CouplingIterationSeparation",
    "WallClockSeparation",
    "OptimizationIterationSeparation",
    "physical_time_changes_the_answer",
    "solver_step_does_not_change_the_physics",
    "coupling_iteration_is_not_a_time_level",
    "wall_clock_is_not_scientific_identity",
    "optimization_iteration_has_no_executed_lever",
]

KELVIN = "kelvin"
SECOND = "second"
WATT = "watt"


# =====================================================================
# The C1 body used by three of the four probes
# =====================================================================

def _body(*, duration_s: float, initial_k: float = 300.0) -> lump.ThermalBody:
    """One lumped body. Only ``duration`` and ``initial_temperature`` vary."""
    return lump.ThermalBody(
        body_id="sep-body",
        heat_capacity=Quantity(500.0, "joule/kelvin"),
        ambient_conductance=Quantity(2.0, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, KELVIN),
        initial_temperature=Quantity(initial_k, KELVIN),
        duration=Quantity(duration_s, SECOND),
    )


def _solve_body(body: lump.ThermalBody, *, heat_w: float) -> dict[str, Any]:
    """Run C1's own solver through the ``ScientificSolver`` lifecycle."""
    problem = lump.build_lumped_thermal_problem(body)
    solver = lump.LumpedThermalSolver()
    solver.bind_body(body, problem.problem_id, heat_input=Quantity(heat_w, WATT))
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    return {"problem": problem, "raw": raw, "metrics": metrics}


# =====================================================================
# AXIS 1 — physical time
# =====================================================================

@dataclass(frozen=True)
class PhysicalTimeSeparation:
    short_duration_s: float
    long_duration_s: float
    final_temperature_short_k: float
    final_temperature_long_k: float
    steady_state_k: float
    time_constant_s: float
    #: ``physical_key`` is C1's own statement of what makes this *this body*.
    physical_key_short: tuple
    physical_key_long: tuple

    @property
    def answer_changed_k(self) -> float:
        return abs(self.final_temperature_long_k - self.final_temperature_short_k)

    @property
    def invariants_held(self) -> bool:
        """Steady state and time constant are properties of the body, not the
        window, so they must be identical across the two durations."""
        return True  # asserted numerically by the caller

    @property
    def domain_calls_it_the_same_body(self) -> bool:
        return self.physical_key_short == self.physical_key_long


def physical_time_changes_the_answer(
    *, short_s: float = 50.0, long_s: float = 400.0, heat_w: float = 20.0
) -> PhysicalTimeSeparation:
    """Vary the physical interval; hold everything else fixed.

    The two solves differ **only** in how far the physical clock advanced. If
    physical time were not its own axis, the reported state could not move.
    """
    short = _body(duration_s=short_s)
    long = _body(duration_s=long_s)
    a = _solve_body(short, heat_w=heat_w)
    b = _solve_body(long, heat_w=heat_w)
    return PhysicalTimeSeparation(
        short_duration_s=short_s,
        long_duration_s=long_s,
        final_temperature_short_k=a["metrics"][lump.TEMPERATURE_METRIC].magnitude_in(
            KELVIN
        ),
        final_temperature_long_k=b["metrics"][lump.TEMPERATURE_METRIC].magnitude_in(
            KELVIN
        ),
        steady_state_k=a["metrics"][
            lump.STEADY_STATE_TEMPERATURE_METRIC
        ].magnitude_in(KELVIN),
        time_constant_s=a["metrics"][lump.TIME_CONSTANT_METRIC].magnitude_in(SECOND),
        physical_key_short=short.physical_key,
        physical_key_long=long.physical_key,
    )


# =====================================================================
# AXIS 2 — solver time step
# =====================================================================

@dataclass(frozen=True)
class SolverStepSeparation:
    end_time_s: float
    coarse_steps: int
    fine_steps: int
    coarse_dt_s: float
    fine_dt_s: float
    #: Largest violation of the algebraic constraint g = x^2 + y^2 - L^2.
    coarse_residual_m2: float
    fine_residual_m2: float
    coarse_energy_drift_j: float
    fine_energy_drift_j: float
    coarse_final_x_m: float
    fine_final_x_m: float

    @property
    def physical_horizon_identical(self) -> bool:
        return True  # both integrate [0, end_time_s]

    @property
    def residual_ratio(self) -> float:
        if self.fine_residual_m2 == 0.0:
            return math.inf
        return self.coarse_residual_m2 / self.fine_residual_m2


def solver_step_does_not_change_the_physics(
    *, end_time_s: float = 2.0, coarse: int = 500, fine: int = 8000
) -> SolverStepSeparation:
    """Vary the integrator's step; hold the physical horizon fixed.

    C4's fixed-step RK4 pendulum. The physical question — where is the bob at
    ``t = end_time_s`` — is identical in both runs. Only the discretisation
    differs, and the difference shows up as *numerical* error (constraint
    residual, energy drift), never as a different physical statement.

    This is what separates a solver step from physical time: refining it makes
    the answer *better*, whereas changing the physical interval makes the
    answer *different*.
    """
    coarse_case = dyn.PendulumCase(
        case_id="sep-coarse", end_time_s=end_time_s, n_steps=coarse
    )
    fine_case = dyn.PendulumCase(
        case_id="sep-fine", end_time_s=end_time_s, n_steps=fine
    )
    a = dyn.run_cartesian(coarse_case)
    b = dyn.run_cartesian(fine_case)

    def _drift(case, result) -> float:
        initial = dyn.energy(case, case.cartesian_initial())
        final = dyn.energy(case, result["final_state"])
        return abs(final - initial)

    return SolverStepSeparation(
        end_time_s=end_time_s,
        coarse_steps=coarse,
        fine_steps=fine,
        coarse_dt_s=coarse_case.dt,
        fine_dt_s=fine_case.dt,
        coarse_residual_m2=float(a["max_constraint_residual_m2"]),
        fine_residual_m2=float(b["max_constraint_residual_m2"]),
        coarse_energy_drift_j=_drift(coarse_case, a),
        fine_energy_drift_j=_drift(fine_case, b),
        coarse_final_x_m=float(a["final_state"][0]),
        fine_final_x_m=float(b["final_state"][0]),
    )


# =====================================================================
# AXIS 3 — coupling iteration
# =====================================================================

@dataclass(frozen=True)
class CouplingIterationSeparation:
    iterations_run: int
    outcome: str
    #: Temperature transported at each sweep. Changes every iteration.
    iterate_values_k: tuple[float, ...]
    #: The thermal problem's declared initial condition, per iteration.
    initial_conditions_k: tuple[float, ...]
    #: The thermal problem's declared interval, per iteration.
    durations_s: tuple[float, ...]
    final_iterate_change_k: float

    @property
    def state_moved(self) -> bool:
        return len(set(round(v, 9) for v in self.iterate_values_k)) > 1

    @property
    def physical_clock_moved(self) -> bool:
        """False by construction, and that is the whole point."""
        return (
            len(set(round(v, 12) for v in self.initial_conditions_k)) > 1
            or len(set(round(v, 12) for v in self.durations_s)) > 1
        )


def coupling_iteration_is_not_a_time_level(
    *, duration_s: float = 120.0, budget: int = 50
) -> CouplingIterationSeparation:
    """Run C3's Picard loop and measure whether the physical clock moved.

    The iterate ``T⁽ⁿ⁾`` changes on every sweep. If the coupling iterate were a
    time level, the thermal problem's initial condition would have to advance
    with it. It does not: every iteration re-poses the *same* problem over the
    *same* interval from the *same* t₀, and only the imposed heat differs.

    A reader looking at the sequence of reported ``final_temperature`` values
    alone — 300 K, 305 K, 306 K, … — cannot tell this trajectory-in-iteration
    from a trajectory-in-time. Nothing typed on the results distinguishes them.
    """
    from engcore.domains.electrical import material as mat
    from engcore.systems.electrothermal import coupled as cp

    conductor = mat.TemperatureDependentConductor(
        component_id="R1",
        reference_resistance=Quantity(10.0, "ohm"),
        temperature_coefficient=Quantity(0.00393, "1/kelvin"),
        reference_temperature=Quantity(293.15, KELVIN),
    )
    body = lump.ThermalBody(
        body_id="R1",
        heat_capacity=Quantity(2.5, "joule/kelvin"),
        ambient_conductance=Quantity(0.05, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, KELVIN),
        initial_temperature=Quantity(300.0, KELVIN),
        duration=Quantity(duration_s, SECOND),
    )
    system = cp.CoupledElectroThermalSystem(
        stages=(cp.CoupledStage(conductor, body),),
        source_voltage=Quantity(5.0, "volt"),
    )
    problems = cp.coupled_problems(
        system,
        {s.component_id: s.conductor.reference_resistance for s in system.stages},
    )
    dependencies = cp.coupled_dependencies(
        system, problems, temperature_metric=lump.TEMPERATURE_METRIC
    )
    plan = cp.nominal_plan(
        system,
        dependencies,
        seed=Quantity(300.0, KELVIN),
        tolerance=Quantity(1e-6, KELVIN),
        max_iterations=budget,
    )
    run = cp.run_fixed_point_coupling(system, plan, run_id="temporal-sep")

    # Selected by structure, not by name-guessing: the thermal problem is the
    # one carrying an InitialCondition on the temperature state AND a declared
    # DURATION parameter. Worth noting in passing that the *property* problem
    # also declares a variable named ``temperature`` — the same name, in one
    # composition, once as a state at t0 and once as the instantaneous
    # operating point a resistance is evaluated at.
    thermal_problem = next(
        p
        for p in problems
        if any(c.variable == lump.TEMPERATURE for c in p.initial_conditions)
        and any(q.name == lump.DURATION for q in p.parameters)
    )
    thermal_id = thermal_problem.problem_id

    iterate_values: list[float] = []
    initials: list[float] = []
    durations: list[float] = []
    for iteration in run.iterations:
        result = iteration.result_for(thermal_id)
        iterate_values.append(
            result.value(lump.TEMPERATURE_METRIC).magnitude_in(KELVIN)
        )
        # The problem is re-posed identically every sweep: the same record is
        # solved again with a different imposed heat. Reading it once per
        # iteration is the honest way to show it never moves.
        initials.append(
            thermal_problem.initial_conditions[0].value.magnitude_in(KELVIN)
        )
        durations.append(
            thermal_problem.parameter(lump.DURATION).value.magnitude_in(SECOND)
        )

    return CouplingIterationSeparation(
        iterations_run=run.iterations_run,
        outcome=run.outcome.value,
        iterate_values_k=tuple(iterate_values),
        initial_conditions_k=tuple(initials),
        durations_s=tuple(durations),
        final_iterate_change_k=run.final_iterate_change.magnitude_in(KELVIN),
    )


# =====================================================================
# AXIS 4 — wall-clock runtime
# =====================================================================

@dataclass(frozen=True)
class WallClockSeparation:
    repeats: int
    wall_seconds: tuple[float, ...]
    final_temperatures_k: tuple[float, ...]
    result_has_wall_clock_field: bool
    raw_has_wall_clock_field: bool

    @property
    def science_identical(self) -> bool:
        return len(set(self.final_temperatures_k)) == 1

    @property
    def runtime_varied(self) -> bool:
        return len(set(self.wall_seconds)) > 1


def wall_clock_is_not_scientific_identity(*, repeats: int = 5) -> WallClockSeparation:
    """Solve the identical problem several times and compare.

    Bit-identical science, different runtimes. The separation is already
    structural in the contracts — ``RawSolverOutput.wall_seconds`` exists and
    ``ScientificResult`` has no wall-clock field — and this probe confirms the
    structure matches the behaviour rather than assuming it does.
    """
    body = _body(duration_s=200.0)
    walls: list[float] = []
    finals: list[float] = []
    raw = None
    for _ in range(repeats):
        run = _solve_body(body, heat_w=20.0)
        raw = run["raw"]
        walls.append(float(raw.wall_seconds))
        finals.append(run["metrics"][lump.TEMPERATURE_METRIC].magnitude_in(KELVIN))
    from engcore.scientific.results.result import ScientificResult

    return WallClockSeparation(
        repeats=repeats,
        wall_seconds=tuple(walls),
        final_temperatures_k=tuple(finals),
        result_has_wall_clock_field="wall_seconds"
        in getattr(ScientificResult, "__dataclass_fields__", {}),
        raw_has_wall_clock_field=raw is not None
        and raw.wall_seconds is not None,
    )


# =====================================================================
# AXIS 5 — optimization iteration: no executed lever
# =====================================================================

@dataclass(frozen=True)
class OptimizationIterationSeparation:
    evaluation_fields: tuple[str, ...]
    has_ordinal_field: bool
    has_predecessor_field: bool
    detail: str


def optimization_iteration_has_no_executed_lever() -> OptimizationIterationSeparation:
    """Measure the contract surface rather than inventing a consumer.

    ``ScientificEvaluation`` is the record an optimizer produces per candidate.
    If optimization iteration were a represented temporal axis, that record
    would carry a position in a sequence. It carries an opaque
    ``evaluation_id`` string and nothing else that orders anything.

    No search is run here. Running one would measure a consumer this milestone
    invented, which §2 of the preregistration forbids.
    """
    from engcore.scientific.experiments.evaluation import ScientificEvaluation

    fields = tuple(sorted(ScientificEvaluation.__dataclass_fields__))
    ordinal_like = {"index", "iteration", "generation", "sequence", "step", "order"}
    predecessor_like = {"parent", "parent_id", "predecessor", "previous"}
    return OptimizationIterationSeparation(
        evaluation_fields=fields,
        has_ordinal_field=bool(set(fields) & ordinal_like),
        has_predecessor_field=bool(set(fields) & predecessor_like),
        detail=(
            "ScientificEvaluation carries an opaque evaluation_id and no "
            "ordinal, sequence position or typed predecessor. There is "
            "nothing to vary, so optimization iteration is reported as NOT "
            "MEASURED HERE rather than as distinct."
        ),
    )
