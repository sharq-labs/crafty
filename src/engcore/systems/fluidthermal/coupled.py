"""Closed-loop Fluid ↔ Thermal scalar-reduction coupling.

`FT-SCALAR-COUPLING`. The second coupled pair this platform has executed, and
the first whose participants are a **2D PDE** and a **lumped body**::

        seed T⁽⁰⁾
            ↓
    ┌── T⁽ⁿ⁾ ─▶ D(T⁽ⁿ⁾) ─▶ fluid PDE solve ─▶ Φ_D ─▶ hA(Φ_D) ─▶ thermal ─┐
    │                                                                     │
    └────────────────── T⁽ⁿ⁺¹⁾ ◀── iterate change |T⁽ⁿ⁺¹⁾ − T⁽ⁿ⁾| ◀───────┘

Four problems, four declared `QuantityDependency` edges, one 4-cycle, one
`TornEndpoint`. Everything transported is a **scalar**; no field, no array and
no bulk reference crosses a problem boundary.

WHAT THIS MODULE DOES NOT CONTAIN
---------------------------------
No loop. The iteration is
:func:`engcore.systems.electrothermal.coupled.run_fixed_point`, **imported
unedited**, and that import is the point: `docs/electrothermal-vertical-prereg.md`
§16 preregistered "a second, materially different coupled consumer written
against these records without editing them" as the condition under which
`FixedPointCouplingPlan` / `TornEndpoint` / `CoupledRun` / `run_fixed_point`
become promotion candidates. This module is that consumer, and the fact that
a *fluids* pack has to reach into an *electrothermal* pack to find the machinery
is itself the measurement — see
``docs/fluid-thermal-scalar-coupling-evidence.md`` §P/§Q. Nothing is copied,
re-implemented or subclassed here; if it were, the promotion test would have
been answered by construction rather than by execution.

No relaxation factor, no damping, no acceleration, no divergence test, no
rollback, no scheduler, no participant registry, no transfer operator and no
time synchronization. The strong-feedback operating point in this system does
**not** converge undamped inside its budget, and that is reported as
``ITERATION_LIMIT_REACHED`` rather than tuned away.

WHY EVERY SWEEP REBUILDS TWO PROBLEMS
-------------------------------------
The two coupled inputs — the fluid's ``diffusivity`` and the body's
``ambient_conductance`` — are both declared `ScientificParameter`s, and
parameters are frozen on a problem record. So a fresh `Transport2DDomain` +
`ScientificProblem` and a fresh `ThermalBody` + `ScientificProblem` are
constructed on every sweep, under **stable problem ids**. This is the
configuration/state conflation `MIN-FOUNDATION-ET` measured on the DC circuit's
resistance, met twice more here, from two different domains at once. Its
consequence is measured rather than asserted: ``unresolved_inputs`` reports
**nothing** for either problem, so a records-only reader cannot tell a coupled
parameter from a configured one, and only the explicit `QuantityDependency`
states it.

ADMISSION IS ENFORCED BY THE PRODUCER, NOT BY THE LOOP
------------------------------------------------------
`run_fixed_point` transports ``result.values[dep.source_quantity]`` directly and
knows nothing about validation; it explicitly does not catch a sub-solve that
refuses. So the guard has to sit where the value is produced: each executor
below reads its own result through an **admission-guarded reader** before
returning it, and a failing check raises out of the loop. A fluid result that
does not satisfy its own declared requirements therefore never becomes a
transported number, and there is no path on which it is logged, defaulted,
retried or skipped.

The two participants are asymmetric here and the asymmetry is a finding, not a
defect papered over: `fluids/transport2d` declares its own
``validation_requirements`` on its problem record, while
`thermal_lumped` declares none — so for the thermal leg the **consumer** must
state what it demands (:data:`THERMAL_ADMISSION_REQUIREMENTS`). A requirement a
consumer invents is weaker evidence than one a producer publishes, and this
module says so rather than hiding the difference behind a uniform-looking call.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping, Sequence

from ...domains import thermal_lumped as lump
from ...domains.fluids.transport2d import (
    PHI_D_METRIC,
    Transport2DDomain,
    Transport2DGrid,
    build_transport2d_problem,
    read_wall_efflux_with_admission,
    solve_transport2d,
)
from ...scientific.composition import QuantityDependency
from ...scientific.errors import InvalidScientificProblem
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.results.provenance import ExecutionBinding, ProvenanceRecord
from ...scientific.results.result import ScientificResult
from ...scientific.results.uncertainty import Uncertainty
from ...scientific.units.quantity import Quantity
# The coupling machinery, imported UNEDITED from the pack that minted it.
# See the module docstring: this import is the preregistered promotion test.
from ..electrothermal.coupled import (
    CoupledRun,
    CouplingOutcome,
    FixedPointCouplingPlan,
    TornEndpoint,
    execution_order,
    run_fixed_point,
)
from . import properties as prop

__all__ = [
    "DEPENDENCY_CONDUCTANCE",
    "DEPENDENCY_DIFFUSIVITY",
    "DEPENDENCY_EFFLUX",
    "DEPENDENCY_TEMPERATURE",
    "FluidSlice",
    "FluidThermalSystem",
    "HeatedBody",
    "THERMAL_ADMISSION_REQUIREMENTS",
    "coupled_dependencies",
    "coupled_problems",
    "nominal_plan",
    "run_fluid_thermal_coupling",
    "sweep_timings",
]

#: Prose labels for the four declared edges. Nothing branches on them.
DEPENDENCY_EFFLUX = "wall-efflux-sets-exchange-conductance"
DEPENDENCY_CONDUCTANCE = "exchange-conductance-sets-body-ambient-path"
DEPENDENCY_TEMPERATURE = "body-temperature-sets-diffusivity-state"
DEPENDENCY_DIFFUSIVITY = "diffusivity-sets-transport-coefficient"

#: What this consumer demands of a thermal result before it will transport its
#: temperature. Stated here because `thermal_lumped` publishes no
#: ``validation_requirements`` of its own — a consumer-invented requirement,
#: weaker evidence than a producer-published one, and labelled as such.
THERMAL_ADMISSION_REQUIREMENTS = frozenset({"lumped_balance_residual"})

SOFTWARE_VERSION = "engcore.systems.fluidthermal.coupled/0.1.0"


# =====================================================================
# Declarations
# =====================================================================

@dataclass(frozen=True)
class FluidSlice:
    """The transport slice's geometry and resolution — **without** its diffusivity.

    The diffusivity is the coupled input and is therefore not part of what this
    slice *is*: including it would make the same slice at a second temperature
    a second physical system, which is exactly the conflation the sibling
    ``ThermalBody.physical_key`` refuses to commit.
    """

    slice_id: str
    side: Quantity
    angular_rate: Quantity
    grid: Transport2DGrid

    def __post_init__(self) -> None:
        slice_id = str(self.slice_id).strip()
        if not slice_id:
            raise InvalidScientificProblem("fluid slice requires a slice_id")
        object.__setattr__(self, "slice_id", slice_id)
        if not isinstance(self.grid, Transport2DGrid):
            raise InvalidScientificProblem("grid must be a Transport2DGrid")
        for label, value, unit in (
            ("side", self.side, "meter"),
            ("angular_rate", self.angular_rate, "1/s"),
        ):
            if not isinstance(value, Quantity):
                raise InvalidScientificProblem(
                    f"{label} must be a Quantity carrying {unit!r}"
                )
            value.require_compatible(unit, context=f"fluid slice {label}")

    def domain_at(self, diffusivity: Quantity) -> Transport2DDomain:
        """The same physical slice at one evaluated diffusivity."""
        return Transport2DDomain(
            domain_id=self.slice_id,
            side=self.side,
            diffusivity=diffusivity,
            angular_rate=self.angular_rate,
            grid=self.grid,
        )

    def with_grid(self, grid: Transport2DGrid) -> "FluidSlice":
        """The same physical slice at a different resolution."""
        return FluidSlice(
            slice_id=self.slice_id,
            side=self.side,
            angular_rate=self.angular_rate,
            grid=grid,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            "side_m": self.side.magnitude_in("meter"),
            "omega_per_s": self.angular_rate.magnitude_in("1/s"),
            "grid": self.grid.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FluidSlice":
        return cls(
            slice_id=payload["slice_id"],
            side=Quantity(float(payload["side_m"]), "meter"),
            angular_rate=Quantity(float(payload["omega_per_s"]), "1/s"),
            grid=Transport2DGrid.from_dict(payload["grid"]),
        )


@dataclass(frozen=True)
class HeatedBody:
    """The lumped body — **without** its ambient conductance.

    Same rule as :class:`FluidSlice`: the conductance is the coupled input.
    ``posing_conductance`` exists only so that a `ScientificProblem` can be
    *posed* before the composition has supplied one, exactly as the sibling
    electro-thermal system poses its DC circuit at each conductor's
    ``reference_resistance``. It is replaced on every sweep, it is not part of
    the body's identity, and a test asserts the coupled answer does not depend
    on it.
    """

    body_id: str
    heat_capacity: Quantity
    ambient_temperature: Quantity
    initial_temperature: Quantity
    duration: Quantity
    heat_input: Quantity
    posing_conductance: Quantity

    def __post_init__(self) -> None:
        body_id = str(self.body_id).strip()
        if not body_id:
            raise InvalidScientificProblem("heated body requires a body_id")
        object.__setattr__(self, "body_id", body_id)
        self.heat_input.require_compatible(
            lump.POWER_UNIT, context="imposed heat input"
        )

    def body_at(self, conductance: Quantity) -> lump.ThermalBody:
        return lump.ThermalBody(
            body_id=self.body_id,
            heat_capacity=self.heat_capacity,
            ambient_conductance=conductance,
            ambient_temperature=self.ambient_temperature,
            initial_temperature=self.initial_temperature,
            duration=self.duration,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "body_id": self.body_id,
            "heat_capacity_j_per_k": self.heat_capacity.magnitude_in(
                lump.CAPACITY_UNIT
            ),
            "ambient_temperature_k": self.ambient_temperature.magnitude_in(
                lump.TEMPERATURE_UNIT
            ),
            "initial_temperature_k": self.initial_temperature.magnitude_in(
                lump.TEMPERATURE_UNIT
            ),
            "duration_s": self.duration.magnitude_in("second"),
            "heat_input_w": self.heat_input.magnitude_in(lump.POWER_UNIT),
            "posing_conductance_w_per_k": self.posing_conductance.magnitude_in(
                lump.CONDUCTANCE_UNIT
            ),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HeatedBody":
        return cls(
            body_id=payload["body_id"],
            heat_capacity=Quantity(
                float(payload["heat_capacity_j_per_k"]), lump.CAPACITY_UNIT
            ),
            ambient_temperature=Quantity(
                float(payload["ambient_temperature_k"]), lump.TEMPERATURE_UNIT
            ),
            initial_temperature=Quantity(
                float(payload["initial_temperature_k"]), lump.TEMPERATURE_UNIT
            ),
            duration=Quantity(float(payload["duration_s"]), "second"),
            heat_input=Quantity(float(payload["heat_input_w"]), lump.POWER_UNIT),
            posing_conductance=Quantity(
                float(payload["posing_conductance_w_per_k"]),
                lump.CONDUCTANCE_UNIT,
            ),
        )


@dataclass(frozen=True)
class FluidThermalSystem:
    """One heated body cooled by a 2D scalar transport slice whose diffusivity
    depends on the body's temperature.

    Four declarations, each owned by the domain or property module that
    understands it. Nothing here is a coupling: the coupling is the four
    `QuantityDependency` records :func:`coupled_dependencies` builds.
    """

    slice: FluidSlice
    medium: prop.GasDiffusivity
    wall: prop.WallCoupling
    body: HeatedBody
    system_id: str = "fluidthermal-scalar"

    def __post_init__(self) -> None:
        if not isinstance(self.slice, FluidSlice):
            raise InvalidScientificProblem("slice must be a FluidSlice")
        if not isinstance(self.medium, prop.GasDiffusivity):
            raise InvalidScientificProblem("medium must be a GasDiffusivity")
        if not isinstance(self.wall, prop.WallCoupling):
            raise InvalidScientificProblem("wall must be a WallCoupling")
        if not isinstance(self.body, HeatedBody):
            raise InvalidScientificProblem("body must be a HeatedBody")
        if self.medium.medium_id != self.wall.medium_id:
            raise InvalidScientificProblem(
                f"the diffusivity declaration names medium "
                f"{self.medium.medium_id!r} and the scale restoration names "
                f"{self.wall.medium_id!r}; no universal record states that two "
                f"declarations describe one substance, so this pack keeps them "
                f"aligned by construction"
            )

    # -- problem ids, stated once ------------------------------------------
    @property
    def fluid_problem_id(self) -> str:
        return f"fluids-transport2d-{self.slice.slice_id}"

    @property
    def diffusivity_problem_id(self) -> str:
        return f"fluid-diffusivity-{self.medium.medium_id}"

    @property
    def wall_problem_id(self) -> str:
        return f"wall-conductance-{self.wall.medium_id}"

    @property
    def thermal_problem_id(self) -> str:
        return f"thermal-lumped-{self.body.body_id}"

    def with_grid(self, grid: Transport2DGrid) -> "FluidThermalSystem":
        """The same physical system at a different fluid resolution."""
        return FluidThermalSystem(
            slice=self.slice.with_grid(grid),
            medium=self.medium,
            wall=self.wall,
            body=self.body,
            system_id=self.system_id,
        )

    def to_dict(self) -> dict[str, Any]:
        """A plain-data projection, so a fresh interpreter can rebuild it.

        Domain-owned, exactly like ``Transport2DDomain.to_dict``. It is **not**
        a universal executable specification and it does not try to be one:
        what it cannot carry is measured and recorded rather than invented.
        """
        return {
            "system_id": self.system_id,
            "slice": self.slice.to_dict(),
            "medium": {
                "medium_id": self.medium.medium_id,
                "reference_diffusivity_m2_s": self.medium.d_ref_m2_s,
                "reference_temperature_k": self.medium.t_ref_k,
                "temperature_exponent": self.medium.exponent,
            },
            "wall": {
                "medium_id": self.wall.medium_id,
                "volumetric_heat_capacity_j_per_m3_k": (
                    self.wall.rho_cp_j_per_m3_k
                ),
                "depth_m": self.wall.depth_m,
            },
            "body": self.body.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FluidThermalSystem":
        medium = payload["medium"]
        wall = payload["wall"]
        return cls(
            system_id=payload["system_id"],
            slice=FluidSlice.from_dict(payload["slice"]),
            medium=prop.GasDiffusivity(
                medium_id=medium["medium_id"],
                reference_diffusivity=Quantity(
                    float(medium["reference_diffusivity_m2_s"]),
                    prop.DIFFUSIVITY_UNIT,
                ),
                reference_temperature=Quantity(
                    float(medium["reference_temperature_k"]),
                    prop.TEMPERATURE_UNIT,
                ),
                temperature_exponent=Quantity(
                    float(medium["temperature_exponent"]), "dimensionless"
                ),
            ),
            wall=prop.WallCoupling(
                medium_id=wall["medium_id"],
                volumetric_heat_capacity=Quantity(
                    float(wall["volumetric_heat_capacity_j_per_m3_k"]),
                    prop.VOLUMETRIC_HEAT_CAPACITY_UNIT,
                ),
                depth=Quantity(float(wall["depth_m"]), "meter"),
            ),
            body=HeatedBody.from_dict(payload["body"]),
        )


# =====================================================================
# Representation
# =====================================================================

def coupled_problems(
    system: FluidThermalSystem,
    *,
    diffusivity: Quantity | None = None,
    conductance: Quantity | None = None,
) -> tuple[ScientificProblem, ...]:
    """``(diffusivity, fluid, wall, thermal)`` — four separately posed problems.

    ``diffusivity`` and ``conductance`` have to be supplied to *build* two of
    them, because both domains carry those quantities as configured
    ``ScientificParameter``s. That is the configuration/state conflation
    `MIN-FOUNDATION-ET` measured, met here from two domains at once; it is why
    every sweep builds fresh records while their ``problem_id``s stay fixed.
    Defaults are the declared posing values, never a computed answer.
    """
    diffusivity = diffusivity or system.medium.reference_diffusivity
    conductance = conductance or system.body.posing_conductance
    return (
        prop.build_diffusivity_problem(
            system.medium, problem_id=system.diffusivity_problem_id
        ),
        build_transport2d_problem(
            system.slice.domain_at(diffusivity),
            problem_id=system.fluid_problem_id,
        ),
        prop.build_wall_conductance_problem(
            system.wall, problem_id=system.wall_problem_id
        ),
        lump.build_lumped_thermal_problem(
            system.body.body_at(conductance),
            heat_input=system.body.heat_input,
            problem_id=system.thermal_problem_id,
        ),
    )


def coupled_dependencies(
    system: FluidThermalSystem,
    *,
    temperature_metric: str = lump.STEADY_STATE_TEMPERATURE_METRIC,
) -> tuple[QuantityDependency, ...]:
    """The four directed edges of the cycle.

    ``temperature_metric`` selects which of the thermal problem's three
    kelvin-valued quantities is transported. It is the **only** difference
    between the coupled-steady-state configuration and the end-of-interval one,
    they converge to different temperatures, and a dimension check cannot
    separate them — only the enumerated name can. This milestone transports
    ``steady_state_temperature``: the fluid participant is steady by
    construction, so a steady ↔ steady-limit composition is the only one whose
    two legs describe the same regime.
    """
    return (
        QuantityDependency(
            source_problem_id=system.fluid_problem_id,
            source_quantity=PHI_D_METRIC,
            target_problem_id=system.wall_problem_id,
            target_quantity=prop.WALL_EFFLUX,
            unit_exemplar=prop.EFFLUX_UNIT,
            name=DEPENDENCY_EFFLUX,
            description=(
                "The boundary-integrated diffusive efflux of the transport "
                "field is the efflux whose extensive scale the wall model "
                "restores."
            ),
        ),
        QuantityDependency(
            source_problem_id=system.wall_problem_id,
            source_quantity=prop.WALL_CONDUCTANCE_METRIC,
            target_problem_id=system.thermal_problem_id,
            target_quantity=lump.AMBIENT_CONDUCTANCE,
            unit_exemplar=lump.CONDUCTANCE_UNIT,
            name=DEPENDENCY_CONDUCTANCE,
            description=(
                "The restored wall conductance is the body's single exchange "
                "path to its ambient."
            ),
        ),
        QuantityDependency(
            source_problem_id=system.thermal_problem_id,
            source_quantity=temperature_metric,
            target_problem_id=system.diffusivity_problem_id,
            target_quantity=prop.TEMPERATURE,
            unit_exemplar=prop.TEMPERATURE_UNIT,
            name=DEPENDENCY_TEMPERATURE,
            description=(
                "The body temperature is the state coordinate at which the "
                "medium's diffusivity is evaluated."
            ),
        ),
        QuantityDependency(
            source_problem_id=system.diffusivity_problem_id,
            source_quantity=prop.DIFFUSIVITY_METRIC,
            target_problem_id=system.fluid_problem_id,
            target_quantity="diffusivity",
            unit_exemplar=prop.DIFFUSIVITY_UNIT,
            name=DEPENDENCY_DIFFUSIVITY,
            description=(
                "The evaluated diffusivity is the transport coefficient the "
                "advection-diffusion problem is posed with."
            ),
        ),
    )


def nominal_plan(
    system: FluidThermalSystem,
    dependencies: Sequence[QuantityDependency],
    *,
    seed: Quantity | None = None,
    tolerance: Quantity = Quantity(1.0e-4, "kelvin"),
    max_iterations: int = 40,
    plan_id: str | None = None,
) -> FixedPointCouplingPlan:
    """Cut the temperature edge and seed it at the ambient.

    **This is a caller-side convenience and it does select a tear by a rule** —
    the edge whose target is the diffusivity problem's ``temperature``. What is
    true, and what matters, is that neither the loop nor the graph readers infer
    anything: :func:`execution_order` reports four admissible tears for this
    cycle and ranks none, and `FixedPointCouplingPlan` accepts whatever tear it
    is handed. The choice is made here, by a caller, and then becomes a typed
    field of a record rather than control flow.

    The seed is the body's declared ambient. It is **not** recoverable from any
    record and is deliberately not inferred; the same finding
    `ET-VERTICAL` §4 recorded, unchanged by a second consumer.
    """
    torn = tuple(
        TornEndpoint(
            dependency=d,
            initial_value=seed or system.body.ambient_temperature,
        )
        for d in dependencies
        if d.target_problem_id == system.diffusivity_problem_id
        and d.target_quantity == prop.TEMPERATURE
    )
    return FixedPointCouplingPlan(
        plan_id=plan_id or f"{system.system_id}-fixed-point",
        dependencies=tuple(dependencies),
        torn=torn,
        absolute_tolerance=tolerance,
        max_iterations=max_iterations,
    )


# =====================================================================
# Per-problem execution, supplied by this pack
# =====================================================================

def _diffusivity_result(
    *, run_id: str, system: FluidThermalSystem, problem: ScientificProblem,
    temperature: Quantity,
) -> ScientificResult:
    started = time.perf_counter()
    solver = prop.DiffusivityPropertySolver()
    solver.bind_medium(system.medium, problem.problem_id, temperature=temperature)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        prop.POWER_LAW_DIFFUSIVITY_MODEL.model_id,
        prop.POWER_LAW_DIFFUSIVITY_MODEL.version,
    )
    report = solver.validate(prepared, raw)
    result = ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=report,
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the declared "
                "power-law exponent"
            )
            for name in metrics
        },
        assumptions=prop.POWER_LAW_DIFFUSIVITY_MODEL.assumptions,
        provenance=ProvenanceRecord(
            run_id=run_id,
            software_version="engcore.systems.fluidthermal.properties/0.1.0",
            bindings=(
                ExecutionBinding(
                    model=model,
                    realization=prepared.payload.realization.reference(),
                    solver=solver.identity,
                ),
            ),
            inputs=dict(problem.parameter_values())
            | {prop.TEMPERATURE: temperature},
            assumptions=prop.POWER_LAW_DIFFUSIVITY_MODEL.assumptions,
        ),
        metadata={"wall_seconds_telemetry": str(time.perf_counter() - started)},
    )
    # Producer-published requirement, guarded before the value is transported.
    report.require_admission(
        problem.validation_requirements,
        context=f"fluidthermal diffusivity result {run_id!r}",
    )
    return result


def _fluid_result(
    *, run_id: str, system: FluidThermalSystem, diffusivity: Quantity,
    cross_check: bool = True,
) -> ScientificResult:
    started = time.perf_counter()
    domain = system.slice.domain_at(diffusivity)
    problem = build_transport2d_problem(
        domain, problem_id=system.fluid_problem_id
    )
    result = solve_transport2d(
        domain,
        run_id=run_id,
        problem=problem,
        cross_check=cross_check,
        software_version="engcore.domains.fluids.transport2d/0.1.0",
    )
    # THE ADMISSION INVARIANT, Fluid → Thermal direction. The guarded reader
    # raises `ScientificValidationError` when any requirement the FLUID problem
    # itself declared failed or did not run, and `run_fixed_point` does not
    # catch it — so an inadmissible fluid result cannot become a transported
    # efflux and cannot reach the thermal solve. FAIL is a refusal, never a
    # continuation.
    read_wall_efflux_with_admission(problem, result)
    # Whole-executor wall time, not the linear solve's own telemetry: for this
    # participant most of the cost is in `assemble`, and a coupling that
    # reported only `RawSolverOutput.wall_seconds` would understate the leg it
    # actually pays for by an order of magnitude.
    return replace(
        result,
        metadata=dict(result.metadata)
        | {"wall_seconds_telemetry": str(time.perf_counter() - started)},
    )


def _wall_result(
    *, run_id: str, system: FluidThermalSystem, problem: ScientificProblem,
    wall_efflux: Quantity,
) -> ScientificResult:
    started = time.perf_counter()
    solver = prop.WallConductanceSolver()
    solver.bind_medium(system.wall, problem.problem_id, wall_efflux=wall_efflux)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        prop.WALL_CONDUCTANCE_MODEL.model_id, prop.WALL_CONDUCTANCE_MODEL.version
    )
    report = solver.validate(prepared, raw)
    result = ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=report,
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the declared "
                "volumetric heat capacity or slice depth"
            )
            for name in metrics
        },
        assumptions=prop.WALL_CONDUCTANCE_MODEL.assumptions,
        provenance=ProvenanceRecord(
            run_id=run_id,
            software_version="engcore.systems.fluidthermal.properties/0.1.0",
            bindings=(
                ExecutionBinding(
                    model=model,
                    realization=prepared.payload.realization.reference(),
                    solver=solver.identity,
                ),
            ),
            inputs=dict(problem.parameter_values())
            | {prop.WALL_EFFLUX: wall_efflux},
            assumptions=prop.WALL_CONDUCTANCE_MODEL.assumptions,
        ),
        metadata={"wall_seconds_telemetry": str(time.perf_counter() - started)},
    )
    report.require_admission(
        problem.validation_requirements,
        context=f"fluidthermal wall conductance result {run_id!r}",
    )
    return result


def _thermal_result(
    *, run_id: str, system: FluidThermalSystem, conductance: Quantity,
) -> ScientificResult:
    started = time.perf_counter()
    body = system.body.body_at(conductance)
    problem = lump.build_lumped_thermal_problem(
        body,
        heat_input=system.body.heat_input,
        problem_id=system.thermal_problem_id,
    )
    solver = lump.LumpedThermalSolver()
    solver.bind_body(body, problem.problem_id, heat_input=system.body.heat_input)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        lump.LUMPED_CAPACITY_MODEL.model_id, lump.LUMPED_CAPACITY_MODEL.version
    )
    report = solver.validate(prepared, raw)
    result = ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=report,
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the lumped "
                "thermal declaration"
            )
            for name in metrics
        },
        assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
        provenance=ProvenanceRecord(
            run_id=run_id,
            software_version="engcore.domains.thermal_lumped/0.1.0",
            bindings=(
                ExecutionBinding(
                    model=model,
                    realization=prepared.payload.realization.reference(),
                    solver=solver.identity,
                ),
            ),
            inputs=dict(problem.parameter_values())
            | {
                lump.HEAT_INPUT: system.body.heat_input,
                lump.AMBIENT_TEMPERATURE: system.body.ambient_temperature,
                # The state at t0. Identical in every sweep: this loop iterates
                # the coupling, it does not march time.
                lump.TEMPERATURE: system.body.initial_temperature,
            },
            assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
        ),
        metadata={"wall_seconds_telemetry": str(time.perf_counter() - started)},
    )
    # THE ADMISSION INVARIANT, Thermal → Fluid direction. The requirement is
    # named by THIS CONSUMER because `thermal_lumped` publishes none on its
    # problem record — weaker evidence than the fluid side's, and labelled so.
    report.require_admission(
        THERMAL_ADMISSION_REQUIREMENTS,
        context=f"fluidthermal thermal result {run_id!r}",
    )
    return result


def _executors(
    system: FluidThermalSystem, *, cross_check: bool = True
) -> dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]]:
    """problem_id -> how this pack solves it, given its transported inputs.

    The only place the loop learns which science sits behind which problem, and
    it is built here, in the system pack, from declarations the caller supplied.
    :func:`run_fixed_point` receives it as data and contains no fluid or thermal
    branch of its own.
    """
    problems = coupled_problems(system)
    by_id = {p.problem_id: p for p in problems}

    def diffusivity_call(inputs: Mapping[str, Quantity], run_id: str):
        return _diffusivity_result(
            run_id=run_id,
            system=system,
            problem=by_id[system.diffusivity_problem_id],
            temperature=inputs[prop.TEMPERATURE],
        )

    def fluid_call(inputs: Mapping[str, Quantity], run_id: str):
        return _fluid_result(
            run_id=run_id,
            system=system,
            diffusivity=inputs["diffusivity"],
            cross_check=cross_check,
        )

    def wall_call(inputs: Mapping[str, Quantity], run_id: str):
        return _wall_result(
            run_id=run_id,
            system=system,
            problem=by_id[system.wall_problem_id],
            wall_efflux=inputs[prop.WALL_EFFLUX],
        )

    def thermal_call(inputs: Mapping[str, Quantity], run_id: str):
        return _thermal_result(
            run_id=run_id,
            system=system,
            conductance=inputs[lump.AMBIENT_CONDUCTANCE],
        )

    return {
        system.diffusivity_problem_id: diffusivity_call,
        system.fluid_problem_id: fluid_call,
        system.wall_problem_id: wall_call,
        system.thermal_problem_id: thermal_call,
    }


def run_fluid_thermal_coupling(
    system: FluidThermalSystem,
    plan: FixedPointCouplingPlan,
    *,
    run_id: str = "ft-coupled",
    cross_check: bool = True,
) -> CoupledRun:
    """Build the composition, then iterate it with the shared, unedited loop.

    Everything domain-specific happens here — the four problems and the
    dispatch table that says how each is solved. :func:`run_fixed_point`
    receives both as data and runs the iteration without being able to name
    either science.
    """
    problems = coupled_problems(system)
    return run_fixed_point(
        problems,
        _executors(system, cross_check=cross_check),
        plan,
        run_id=run_id,
        software_version=SOFTWARE_VERSION,
        assumptions=(
            "the diffusivity is evaluated at the transported body temperature "
            "and held uniform over the whole transport domain within a sweep",
            "the whole boundary-integrated diffusive efflux of the transport "
            "field is the body's single exchange path to its ambient",
            "the transported temperature is the thermal problem's steady-state "
            "limit, so both legs of the composition describe the same regime",
            "the fluid participant's own discretization error is inherited by "
            "the coupled answer and is NOT quantified by the coupling "
            "outcome; the two are reported separately",
        ),
    )


def sweep_timings(run: CoupledRun) -> tuple[dict[str, float], ...]:
    """Per-sweep wall time, per participant, from the results themselves.

    Read out of ``ScientificResult.metadata``, which every executor above
    stamps with its own solver's telemetry. Reported, never used to decide
    anything.
    """
    timings: list[dict[str, float]] = []
    for iteration in run.iterations:
        row: dict[str, float] = {}
        for result in iteration.results:
            telemetry = result.metadata.get("wall_seconds_telemetry")
            if telemetry is not None:
                row[result.problem_id] = float(telemetry)
        row["sweep_total"] = float(sum(row.values()))
        timings.append(row)
    return tuple(timings)
