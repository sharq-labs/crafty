"""``electrothermal.series_self_heating/1`` — the one execution v0 exposes.

N self-heating conductors in series across one ideal DC source, each thermally
represented as a lumped body: the closed-loop electro-thermal vertical
`ET-VERTICAL` built and measured. **No science is added, changed or restated
here.** This module constructs
:class:`~engcore.domains.electrical.material.TemperatureDependentConductor`,
:class:`~engcore.domains.thermal_lumped.ThermalBody` and
:class:`~engcore.systems.electrothermal.CoupledElectroThermalSystem` from a
parsed request and calls ``run_fixed_point_coupling``. That is the whole
module.

Admission is not performed here
-------------------------------
Every refusal below comes from somewhere else. A non-positive reference
resistance is refused by the conductor's own ``__post_init__``; a wrong
dimension by ``require_compatible``; a seed on an endpoint a declared initial
condition already determines by ``FixedPointCouplingPlan.check_against``; a
composition nothing can order by ``run_fixed_point``. This module adds **two**
refusals of its own, and both are about the *size of the request* rather than
about any science:

* a stage count bound, and
* an iteration-budget bound,

because an external caller may not choose an unbounded amount of work. Both are
refusals rather than clamps: silently reducing a caller's budget would change
the question being asked without saying so.

Where the split between admission and execution lies
----------------------------------------------------
:func:`prepare` does everything up to and including plan construction.
:meth:`PreparedExecution.run` is the first line that can execute a solver. That
boundary is not a comment — the service classifies failures by *which side of
it* they were raised on, because ``InvalidScientificProblem`` is raised both by
a caller's malformed declaration and, inside the loop, by an executor
misattributing its own result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ...coupling import CoupledRun, FixedPointCouplingPlan
from ...domains import thermal_lumped as lump
from ...domains.electrical import material as mat
from ...systems.electrothermal import (
    CircuitSolver,
    CoupledElectroThermalSystem,
    CoupledStage,
    coupled_dependencies,
    coupled_problems,
    native_circuit_solver,
    nominal_plan,
    run_fixed_point_coupling,
)
from ..contract import (
    MAX_ITERATION_BUDGET,
    MAX_STAGES,
    ExternalRequestRefused,
    RefusalCode,
    parse_quantity,
    require_exact_keys,
    require_int,
    require_object,
    require_text,
)

__all__ = [
    "EXECUTION_ID",
    "INPUT_KEYS",
    "COUPLING_KEYS",
    "PreparedExecution",
    "STAGE_UNITS",
    "TRANSPORTED_TEMPERATURES",
    "prepare",
]

EXECUTION_ID = "electrothermal.series_self_heating/1"

#: The two kelvin-valued result metrics of the thermal problem a caller may
#: transport. Enumerated, never constructed from a caller's string.
#:
#: This is the sharpest single reason the enumeration exists rather than a free
#: string: both members are kelvin, so no dimension check can separate them,
#: and `ET-VERTICAL` measured that selecting one instead of the other moves the
#: converged answer by 3.376418 K. Only the enumerated name distinguishes them.
TRANSPORTED_TEMPERATURES: Mapping[str, str] = {
    "final_temperature": lump.TEMPERATURE_METRIC,
    "steady_state_temperature": lump.STEADY_STATE_TEMPERATURE_METRIC,
}

#: Each stage field, and the unit the receiving declaration already declares.
#: The caller may state a value in any dimensionally compatible unit; it is
#: restated in this one before it reaches the declaration.
STAGE_UNITS: Mapping[str, str] = {
    "reference_resistance": mat.RESISTANCE_UNIT,
    "temperature_coefficient": mat.TCR_UNIT,
    "reference_temperature": mat.TEMPERATURE_UNIT,
    "heat_capacity": lump.CAPACITY_UNIT,
    "ambient_conductance": lump.CONDUCTANCE_UNIT,
    "ambient_temperature": lump.TEMPERATURE_UNIT,
    "initial_temperature": lump.TEMPERATURE_UNIT,
    "duration": lump.TIME_UNIT,
}

STAGE_KEYS = frozenset(STAGE_UNITS) | {"component_id"}
INPUT_KEYS = frozenset({"source_voltage", "stages"})
COUPLING_KEYS = frozenset(
    {"transported_temperature", "seed_temperature", "tolerance", "max_iterations"}
)


@dataclass(frozen=True)
class PreparedExecution:
    """Admitted, not executed. Nothing here has run a solver."""

    system: CoupledElectroThermalSystem
    plan: FixedPointCouplingPlan
    circuit_solver: CircuitSolver

    def run(self, run_id: str) -> CoupledRun:
        """The first line that can execute anything. One call, no glue."""
        return run_fixed_point_coupling(
            self.system,
            self.plan,
            run_id=run_id,
            circuit_solver=self.circuit_solver,
        )


def _stage(payload: Any, index: int) -> CoupledStage:
    where = f"request.inputs.stages[{index}]"
    body = require_object(payload, where)
    require_exact_keys(body, required=STAGE_KEYS, where=where)

    component_id = require_text(body["component_id"], f"{where}.component_id")
    values = {
        name: parse_quantity(body[name], where=f"{where}.{name}", unit=unit)
        for name, unit in STAGE_UNITS.items()
    }
    # Both declarations refuse their own invalid input. Neither refusal is
    # restated here, and neither is anticipated: this call site does not know
    # what makes a conductor or a body admissible.
    return CoupledStage(
        conductor=mat.TemperatureDependentConductor(
            component_id=component_id,
            reference_resistance=values["reference_resistance"],
            temperature_coefficient=values["temperature_coefficient"],
            reference_temperature=values["reference_temperature"],
        ),
        body=lump.ThermalBody(
            body_id=component_id,
            heat_capacity=values["heat_capacity"],
            ambient_conductance=values["ambient_conductance"],
            ambient_temperature=values["ambient_temperature"],
            initial_temperature=values["initial_temperature"],
            duration=values["duration"],
        ),
    )


def prepare(
    inputs: Mapping[str, Any],
    coupling: Mapping[str, Any],
    circuit_solver: CircuitSolver | None = None,
) -> PreparedExecution:
    """Parse and admit. **Executes nothing.**"""
    require_exact_keys(inputs, required=INPUT_KEYS, where="request.inputs")
    require_exact_keys(coupling, required=COUPLING_KEYS, where="request.coupling")

    raw_stages = inputs["stages"]
    if not isinstance(raw_stages, list):
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"request.inputs.stages must be a list, got "
            f"{type(raw_stages).__name__}",
        )
    if not 1 <= len(raw_stages) <= MAX_STAGES:
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"request.inputs.stages must hold between 1 and {MAX_STAGES} "
            f"entries, got {len(raw_stages)}",
        )

    system = CoupledElectroThermalSystem(
        stages=tuple(_stage(entry, i) for i, entry in enumerate(raw_stages)),
        source_voltage=parse_quantity(
            inputs["source_voltage"],
            where="request.inputs.source_voltage",
            unit="volt",
        ),
    )

    metric_name = require_text(
        coupling["transported_temperature"],
        "request.coupling.transported_temperature",
    )
    try:
        metric = TRANSPORTED_TEMPERATURES[metric_name]
    except KeyError:
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"request.coupling.transported_temperature must be one of "
            f"{sorted(TRANSPORTED_TEMPERATURES)}, got {metric_name!r}. Both "
            f"are kelvin-valued, so this name — not a dimension check — is "
            f"what selects the physics that is transported.",
        ) from None

    budget = require_int(
        coupling["max_iterations"], "request.coupling.max_iterations"
    )
    if not 1 <= budget <= MAX_ITERATION_BUDGET:
        raise ExternalRequestRefused(
            RefusalCode.MALFORMED_REQUEST,
            f"request.coupling.max_iterations must lie in "
            f"[1, {MAX_ITERATION_BUDGET}], got {budget}",
        )

    problems = coupled_problems(
        system,
        {
            stage.component_id: stage.conductor.reference_resistance
            for stage in system.stages
        },
    )
    plan = nominal_plan(
        system,
        coupled_dependencies(system, problems, temperature_metric=metric),
        seed=parse_quantity(
            coupling["seed_temperature"],
            where="request.coupling.seed_temperature",
            unit=lump.TEMPERATURE_UNIT,
        ),
        # A DIFFERENCE, not a temperature. See parse_quantity's own docstring
        # for the measurement that made this flag exist.
        tolerance=parse_quantity(
            coupling["tolerance"],
            where="request.coupling.tolerance",
            unit=lump.TEMPERATURE_UNIT,
            difference=True,
        ),
        max_iterations=budget,
    )
    # The plan's own admission, run here so that it happens on the admission
    # side of the split rather than inside the loop. `run_fixed_point` runs it
    # again; a refusal firing twice is harmless, a refusal firing late is not.
    issues = plan.check_against(problems)
    if issues:
        raise ExternalRequestRefused(
            RefusalCode.SCIENTIFIC_ADMISSION_REFUSED,
            "the declared coupling plan cannot be executed against this "
            "composition: " + "; ".join(issues),
        )

    return PreparedExecution(
        system=system,
        plan=plan,
        circuit_solver=circuit_solver or native_circuit_solver,
    )
