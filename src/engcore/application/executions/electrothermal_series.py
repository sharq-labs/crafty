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
composition nothing can order by ``run_fixed_point``; an affine unit for a
quantity that is a *difference* by ``engcore.coupling.scales.is_ratio_scale``.

This module adds **three** refusals of its own, and none is a scientific
judgement:

* a stage-count bound and an iteration-budget bound, because an external caller
  may not choose an unbounded amount of work — refusals rather than clamps,
  since silently reducing a caller's budget would change the question being
  asked without saying so; and
* the transported-temperature **enumeration**, which is a selection among two
  metrics the thermal problem already publishes, not a new fact about either.

Where the split between admission and execution lies
----------------------------------------------------
:func:`prepare` does everything up to and including plan construction, and its
**last** statement resolves the execution profile — so an inadmissible request
never reaches profile resolution, and not even a solver object is constructed
for it. :meth:`PreparedExecution.run` is the first line that can execute
anything.

That boundary is not a comment — the service classifies failures by *which side
of it* they were raised on, because ``InvalidScientificProblem`` is raised both
by a caller's malformed declaration and, inside the loop, by an executor
misattributing its own result.
"""

from __future__ import annotations

import sys
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
    IDENTIFIER_PATTERN,
    MAX_ITERATION_BUDGET,
    MAX_STAGES,
    ExternalRequestRefused,
    RefusalCode,
    parse_quantity,
    require_exact_keys,
    require_identifier,
    require_int,
    require_object,
    require_text,
)

__all__ = [
    "EXECUTION_ID",
    "PROFILES",
    "provider_failure_types",
    "request_fragment",
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


# =====================================================================
# The ways THIS execution can be executed. A closed, literal enumeration.
# =====================================================================

NATIVE_PROFILE = "native"
PROVIDER_PROFILE = "ngspice"


def _native() -> CircuitSolver:
    """Crafty's own MNA solve. No process, no provider, no import."""
    return native_circuit_solver


def _external_provider() -> CircuitSolver:
    """The real external provider in the electrical slot of the coupled loop.

    Constructed here and **only** from module-level identities. This function
    takes no argument at all, which is the structural reason no external string
    can influence how the provider is invoked: there is nowhere for one to go.
    Where the binary lives, and by which supported route it is reached, is
    deployment configuration read before any request arrives — never a request
    field.

    The import is local so that a deployment serving only the native profile
    never loads the provider module. That is asserted by a test in a fresh
    interpreter, because "the native path does not touch the provider" is a
    claim worth being able to check.
    """
    from ...domains.electrical import ngspice as provider

    solver = provider.NgspiceDCSolver()

    def solve(circuit, run_id: str):
        return provider.solve_circuit_with_ngspice(
            circuit, run_id=run_id, solver=solver
        )

    return solve


#: name -> zero-argument resolver. Closed, literal, no fallthrough.
#:
#: One of the two genuinely reaches ``subprocess.run``, and that is deliberate:
#: if the only rejectable profile name mapped to nothing that could ever spawn
#: a process, then "an unknown profile is refused before any process launch"
#: would be a restatement of ``KeyError`` rather than a security claim. A check
#: whose only effect is a field nothing consults is not a guard.
#:
#: The provider is named rather than hidden because ``ProvenanceRecord``
#: already reports ``solver_id`` and ``backend`` truthfully, so an opaque
#: request-side name that provenance immediately de-anonymizes would be
#: obfuscation rather than encapsulation. What is not exposed is every provider
#: internal: the argv, the timeout, the deck, the analysis statement, the node
#: naming and the version probe are all unreachable from a request.
PROFILES: Mapping[str, Any] = {
    NATIVE_PROFILE: _native,
    PROVIDER_PROFILE: _external_provider,
}


def provider_failure_types() -> tuple[type[BaseException], ...]:
    """The failure family meaning *an external provider broke*, for THIS
    execution. Part of the execution-module protocol.

    The domain deliberately made its provider errors **not**
    ``ScientificCoreError``, so that "the provider was not installed" can never
    be read as "the science does not hold". The boundary honours that split by
    asking the execution rather than by knowing a provider's name: the
    classifier in ``service.py`` must be able to say "the provider broke"
    without any module above this one naming a provider.

    Resolved from ``sys.modules`` rather than by importing, so a deployment
    serving only the native profile still never loads the provider module. The
    lookup uses ``getattr`` with a default because a concurrent first import
    can expose a partially initialized module, and an ``AttributeError`` raised
    inside the classifier would be the one path by which ``handle`` could raise
    instead of classifying.
    """
    module = sys.modules.get("engcore.domains.electrical.ngspice")
    family = getattr(module, "NgspiceProviderError", None) if module else None
    return (family,) if isinstance(family, type) else ()


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

    component_id = require_identifier(
        body["component_id"], f"{where}.component_id"
    )
    values = {
        name: parse_quantity(
            body[name], where=f"{where}.{name}", unit=unit, difference=False
        )
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
    profile: str,
) -> PreparedExecution:
    """Parse and admit. **Executes nothing.**

    ``profile`` is the identity the envelope parser already validated against
    :data:`PROFILES`. It is resolved here, by the module that knows what a
    profile means for this execution, so the application layer never holds a
    solver, a circuit or a provider of any kind.

    It is a required positional argument with no default. An earlier form
    accepted ``None`` and silently fell back to the native solver, which is a
    default that selects which implementation computes the answer.
    """
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
            difference=False,
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
        # An absolute temperature: the first value the cut edge takes. `degC`
        # is a legitimate spelling of one and converts correctly.
        seed=parse_quantity(
            coupling["seed_temperature"],
            where="request.coupling.seed_temperature",
            unit=lump.TEMPERATURE_UNIT,
            difference=False,
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
        system=system, plan=plan, circuit_solver=PROFILES[profile]()
    )


# =====================================================================
# This execution's half of the published request contract
# =====================================================================

def request_fragment() -> dict[str, Any]:
    """What ``inputs`` and ``coupling`` may contain, and which profiles exist.

    Derived from the same constants :func:`prepare` enforces, so the published
    contract cannot drift from the enforced one — and **per field**, not only
    per field name. The first form published one shared quantity fragment
    saying "any dimensionally compatible unit", which is false of ``tolerance``:
    ``degC`` is dimensionally compatible with kelvin and is refused. That is the
    exact distinction this milestone paid a measured 5.695253 K error to find,
    and publishing it wrongly would have handed a fourth transport the bug.
    """
    from ..describe import quantity_fragment

    stage = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(STAGE_KEYS),
        "properties": {
            "component_id": {
                "type": "string",
                "pattern": IDENTIFIER_PATTERN,
                "maxLength": 64,
                "description": (
                    "Names one conductor and the thermal body it dissipates "
                    "into; the two share this id by this system pack's own "
                    "convention. It is a name, not free text: it is carried "
                    "into problem ids, result ids and provenance keys."
                ),
            },
            **{
                name: quantity_fragment(unit)
                for name, unit in sorted(STAGE_UNITS.items())
            },
        },
    }

    return {
        "profiles": sorted(PROFILES),
        "inputs": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(INPUT_KEYS),
            "properties": {
                "source_voltage": quantity_fragment("volt"),
                "stages": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_STAGES,
                    "items": stage,
                },
            },
        },
        "coupling": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(COUPLING_KEYS),
            "properties": {
                "transported_temperature": {
                    "type": "string",
                    "enum": sorted(TRANSPORTED_TEMPERATURES),
                    "description": (
                        "Which kelvin-valued thermal result is carried back "
                        "into the conductor's state. Both members are kelvin, "
                        "so no dimension check separates them, and the two "
                        "converge to different temperatures. Only this name "
                        "selects the physics."
                    ),
                },
                "seed_temperature": quantity_fragment(
                    lump.TEMPERATURE_UNIT,
                    "The first value every cut coupling edge takes.",
                ),
                "tolerance": quantity_fragment(
                    lump.TEMPERATURE_UNIT,
                    "Coupling criterion: the largest change of any cut "
                    "iterate between sweeps. Not the residual of any "
                    "equation, and not any sub-solve's own tolerance.",
                    difference=True,
                ),
                "max_iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_ITERATION_BUDGET,
                    "description": (
                        "Sweep budget. Exhausting it is a legitimate outcome, "
                        "reported as iteration_limit_reached, and is not an "
                        "error."
                    ),
                },
            },
        },
    }
