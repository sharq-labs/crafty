"""Lumped first-order thermal capacity: model, realization, problem, solver.

MIN-FOUNDATION-ET. The thermal half of the minimum electro-thermal consumer.
One body, one temperature, one heat input, one ambient environment::

    C dT/dt = Q_in - hA (T - T_amb)

There is no field, no mesh, no topology and no spatial coordinate. That is
deliberate: `FIELD0` and `TOPO0` are deferred, and a lumped body is enough to
ask every question this milestone asks.

Why this is not in ``domains/thermal/``
--------------------------------------
That tree is byte-pinned by three frozen experiments (T1/T2/T3), which assert
both a digest map and set-equality over its ``*.py`` files, and no unfreeze
mechanism exists. This module sits beside it — the pattern already used by
``thermal_conduction1d_bulk.py`` and ``thermal_conduction1d_schemes.py``.

It is also a different science. The frozen `Conduction1DSolver` solves a
*dimensionless* normalized field with **no source term** and welded homogeneous
Dirichlet ends; it explicitly claims no absolute temperature scale and no
material property. Joule heat has nowhere to enter it. This model carries a
real temperature in kelvin and a real heat input in watts.

What is deliberately absent
---------------------------
No coupling scheme, no iteration, no relaxation, no rollback, no
synchronization and no knowledge of where ``heat_input`` comes from. The heat
input is declared as an **externally imposed control**, and any heat source
satisfies it — combustion, friction, a heater, or Joule dissipation. A thermal
model that *required* electrical dissipation would be electrical physics
wearing a thermal name.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from ..scientific.capabilities import ScientificCapability
from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.conditions import InitialCondition
from ..scientific.ir.problem import ModelReference, ScientificProblem
from ..scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from ..scientific.models.definition import (
    InputSourceKind,
    ModelInputSpec,
    ModelOutputSpec,
    ModelType,
    ModelValidationStatus,
    RangeCondition,
    ScientificModelDefinition,
    ValidityDomain,
)
from ..scientific.models.registry import ModelRegistry
from ..scientific.realizations.definition import (
    ImplementationReference,
    ModelFormulation,
    ModelRealizationDefinition,
)
from ..scientific.realizations.registry import RealizationRegistry
from ..scientific.results.validation import (
    ValidationCheck,
    ValidationOutcome,
    ValidationReport,
)
from ..scientific.solvers.capability import (
    CoreCapabilities,
    SolverCapability,
    SolverCapabilityId,
)
from ..scientific.solvers.protocol import (
    ConvergenceState,
    PreparedSolve,
    RawSolverOutput,
    SolverIdentity,
    SolverSettings,
)
from ..scientific.units.quantity import Quantity

__all__ = [
    "AMBIENT_CONDUCTANCE",
    "AMBIENT_TEMPERATURE",
    "CAPACITY_UNIT",
    "CONDUCTANCE_UNIT",
    "DURATION",
    "HEAT_CAPACITY",
    "HEAT_INPUT",
    "BODY_TEMPERATURE",
    "LUMPED_CAPACITY_TRANSIENT",
    "LUMPED_CAPACITY_MODEL",
    "LUMPED_CLOSED_FORM_REALIZATION",
    "POWER_UNIT",
    "STEADY_STATE_TEMPERATURE_METRIC",
    "TEMPERATURE",
    "TEMPERATURE_UNIT",
    "TEMPERATURE_METRIC",
    "TIME_CONSTANT_METRIC",
    "ThermalBody",
    "LumpedThermalSolver",
    "build_lumped_thermal_problem",
    "lumped_model_registry",
    "lumped_realizations",
    "lumped_solver_capabilities",
]

# --- units -------------------------------------------------------------------
TEMPERATURE_UNIT = "kelvin"
POWER_UNIT = "watt"
CAPACITY_UNIT = "joule/kelvin"
CONDUCTANCE_UNIT = "watt/kelvin"
TIME_UNIT = "second"

# --- quantity names ----------------------------------------------------------
# Names, not conventions: every one of these is enumerated by the problem
# record itself. Nothing anywhere parses their internal structure.
TEMPERATURE = "temperature"
HEAT_INPUT = "heat_input"
AMBIENT_TEMPERATURE = "ambient_temperature"
HEAT_CAPACITY = "heat_capacity"
AMBIENT_CONDUCTANCE = "ambient_conductance"
DURATION = "duration"

# Metric names are distinct from the declaration names above, and must stay
# distinct. ``temperature`` the STATE variable is the body's temperature at
# t0; ``final_temperature`` the metric is its temperature at t = duration.
# Both are kelvin, so a name shared between the two namespaces would let one
# endpoint denote two different time levels of the same physical quantity with
# nothing — not even a dimension check — able to notice. One name means one
# thing, across a problem's declarations and the metrics of results computed
# from it.
TEMPERATURE_METRIC = "final_temperature"
STEADY_STATE_TEMPERATURE_METRIC = "steady_state_temperature"
TIME_CONSTANT_METRIC = "time_constant"

MODEL_VERSION = "0.1.0"

# --- capabilities, declared here and nowhere else ----------------------------

#: What science this provides. A *scientific* capability: it answers "which
#: physical operation is available", not "which computational operation a
#: backend can execute".
#:
#: Deliberately ``thermal:body_temperature`` and **not**
#: ``thermal:lumped_body_temperature``. A consumer that needs a body's
#: temperature needs a temperature; whether it was produced by a lumped
#: balance or by a resolved field is a property of *this* realization, stated
#: in ``formulation`` and ``assumptions``, and compressing it into the
#: capability identity would make a spatial realization unable to satisfy the
#: same consumer. Capability identity is exact-string with no registry and no
#: subsumption, so granularity is a choice with no contract to guide it —
#: recorded as a known unknown rather than resolved here.
BODY_TEMPERATURE = ScientificCapability.parse("thermal:body_temperature")

#: What a backend must be able to do. A *solver* capability.
LUMPED_CAPACITY_TRANSIENT = SolverCapability(
    "thermal:lumped_capacity_transient",
    "Transient temperature of a lumped body with one ambient exchange path",
)


_ASSUMPTIONS = (
    "lumped body: one uniform temperature, no internal spatial gradient",
    "Biot number small enough that internal conduction is not limiting",
    "constant heat capacity over the temperature range considered",
    "constant ambient conductance; one exchange path to one ambient",
    "no radiation, no phase change, no mass transport",
    "the heat input is externally imposed and its origin is not claimed here",
)


LUMPED_CAPACITY_MODEL = ScientificModelDefinition(
    model_id="thermal.lumped.first_order_capacity",
    version=MODEL_VERSION,
    name="Lumped first-order thermal capacity",
    domain="thermal",
    # FUNDAMENTAL_RELATION: an energy balance on a control volume. The lumped
    # assumption is an approximation of the *geometry*, declared in
    # `assumptions`; the balance itself is conservation.
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Energy balance on a lumped body: C dT/dt = Q_in - hA (T - T_amb). "
        "One temperature, one imposed heat input, one ambient exchange path."
    ),
    inputs=(
        ModelInputSpec(
            name=HEAT_CAPACITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=CAPACITY_UNIT,
            description="Total heat capacity of the body; strictly positive.",
        ),
        ModelInputSpec(
            name=AMBIENT_CONDUCTANCE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=CONDUCTANCE_UNIT,
            description=(
                "Conductance to the ambient; strictly positive. Zero would be "
                "an adiabatic body, which has no steady state and is outside "
                "this model's declared validity."
            ),
        ),
        ModelInputSpec(
            name=DURATION,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TIME_UNIT,
            description="Length of the interval over which the state advances.",
        ),
        # The state coordinate. Declared as a VARIABLE with role STATE, which
        # is what makes "this quantity evolves during the solve" a typed fact
        # rather than a naming habit.
        ModelInputSpec(
            name=TEMPERATURE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TEMPERATURE_UNIT,
            role=VariableRole.STATE,
            description="Body temperature; the evolving state.",
        ),
        # Imposed from outside the thermal problem. CONTROL says exactly that
        # and says nothing about the supplier — which is correct, because any
        # heat source satisfies this model.
        ModelInputSpec(
            name=HEAT_INPUT,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=POWER_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Heat delivered to the body, imposed externally. Its origin "
                "is not part of this model's claim."
            ),
        ),
        ModelInputSpec(
            name=AMBIENT_TEMPERATURE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TEMPERATURE_UNIT,
            role=VariableRole.CONTROL,
            description="Temperature of the ambient the body exchanges with.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=TEMPERATURE_METRIC,
            unit_exemplar=TEMPERATURE_UNIT,
            description=(
                "Body temperature at the end of the interval. Named "
                "distinctly from the `temperature` state variable, which is "
                "its value at the start."
            ),
        ),
        ModelOutputSpec(
            metric=STEADY_STATE_TEMPERATURE_METRIC,
            unit_exemplar=TEMPERATURE_UNIT,
            description=(
                "T_amb + Q_in/hA — the temperature approached as t grows, for "
                "a constant heat input."
            ),
        ),
        ModelOutputSpec(
            metric=TIME_CONSTANT_METRIC,
            unit_exemplar=TIME_UNIT,
            description="C/hA — the first-order time constant.",
        ),
    ),
    assumptions=_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=HEAT_CAPACITY,
                minimum=Quantity(0.0, CAPACITY_UNIT),
                minimum_inclusive=False,
                description="Strictly positive; zero capacity has no dynamics.",
            ),
            RangeCondition(
                name=AMBIENT_CONDUCTANCE,
                minimum=Quantity(0.0, CONDUCTANCE_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive; an adiabatic body has no steady state "
                    "and no finite time constant."
                ),
            ),
        ),
        description="Linear lumped exchange with a single ambient.",
    ),
    required_capabilities=frozenset({LUMPED_CAPACITY_TRANSIENT.name}),
    # SELF_CONSISTENT: the closed form is checked against the differential
    # balance it solves. Nothing physical was measured.
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


LUMPED_CLOSED_FORM_REALIZATION = ModelRealizationDefinition(
    realization_id="thermal.lumped.first_order_capacity.closed_form",
    version="0.1.0",
    model=ModelReference(
        LUMPED_CAPACITY_MODEL.model_id, LUMPED_CAPACITY_MODEL.version
    ),
    # The *model* poses an ODE. That is what `formulation` records — the
    # mathematical form of the claim, not how it happens to be discharged.
    formulation=ModelFormulation.ODE,
    name="Exact integration for a piecewise-constant heat input",
    description=(
        "Integrates the linear first-order balance in closed form over one "
        "interval of constant heat input: "
        "T(t) = T_ss + (T0 - T_ss) exp(-t/tau)."
    ),
    provided_capabilities=frozenset({BODY_TEMPERATURE}),
    # An ODE realization that needs no ODE integrator. This is exactly the
    # separation MODEL0-R evidenced: the formulation is a property of the
    # claim, the required solver capability is a property of the computation,
    # and they are allowed to disagree.
    required_solver_capabilities=frozenset(
        {
            SolverCapabilityId.coerce(LUMPED_CAPACITY_TRANSIENT),
            SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC),
        }
    ),
    assumptions=(
        "the heat input is constant over the integrated interval",
        "exact for the linear balance; no time-discretization error",
        "no linear system is solved; the update is a scalar exponential",
    ),
    implementation=ImplementationReference(
        implementation_id="engcore.domains.thermal_lumped",
        version="0.1.0",
        reference="closed-form first-order step; see module docstring",
    ),
)


def lumped_model_registry() -> ModelRegistry:
    """A fresh registry. No global singleton exists."""
    return ModelRegistry((LUMPED_CAPACITY_MODEL,))


def lumped_realizations() -> RealizationRegistry:
    """A fresh registry. No global singleton exists."""
    return RealizationRegistry((LUMPED_CLOSED_FORM_REALIZATION,))


def lumped_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({LUMPED_CAPACITY_TRANSIENT, CoreCapabilities.ALGEBRAIC})


# =====================================================================
# Declaration
# =====================================================================

def _positive(value: Any, unit: str, label: str) -> Quantity:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(
            f"{label} must be a Quantity carrying {unit!r}, got "
            f"{type(value).__name__} — a bare number is not a declaration"
        )
    magnitude = value.magnitude_in(unit)
    if not math.isfinite(magnitude) or magnitude <= 0.0:
        raise InvalidScientificProblem(
            f"{label} must be finite and strictly positive, got {magnitude!r} "
            f"{unit}"
        )
    return value


@dataclass(frozen=True)
class ThermalBody:
    """One declared lumped body, with its ambient and its initial state.

    The declaration carries the numbers. It carries no solver, no scheme, no
    tolerance and no coupling: those are execution properties, and a body that
    named one would have made changing an integrator into a change of physical
    identity.

    **Not everything on this record is part of the body's identity.**
    ``heat_capacity`` and ``ambient_conductance`` are what the body *is*;
    ``ambient_temperature`` is a declared ``CONTROL``, ``initial_temperature``
    is a state at one instant, and ``duration`` is an integration window. Those
    three are an operating point, not a system, and :attr:`physical_key` is the
    part that identity is taken over — the same split the frozen
    ``ConductionSlab.fingerprint`` makes when it excludes the discretization.

    They stay on this record because a caller declaring a run needs them in one
    place. What must not follow is that changing one makes it a different body.
    """

    body_id: str
    heat_capacity: Quantity
    ambient_conductance: Quantity
    ambient_temperature: Quantity
    initial_temperature: Quantity
    duration: Quantity

    def __post_init__(self) -> None:
        body_id = str(self.body_id).strip()
        if not body_id:
            raise InvalidScientificProblem("thermal body requires a body_id")
        object.__setattr__(self, "body_id", body_id)
        _positive(self.heat_capacity, CAPACITY_UNIT, "heat_capacity")
        _positive(self.ambient_conductance, CONDUCTANCE_UNIT, "ambient_conductance")
        _positive(self.duration, TIME_UNIT, "duration")
        _positive(self.ambient_temperature, TEMPERATURE_UNIT, "ambient_temperature")
        _positive(self.initial_temperature, TEMPERATURE_UNIT, "initial_temperature")

    @property
    def physical_key(self) -> tuple[str, float, float]:
        """What makes this *this body*: its id and its two thermal properties.

        The ambient, the initial state and the integration window are excluded
        deliberately. Including them would mean the same physical body at a
        second ambient, or over a second interval, was a second system — the
        configuration/state conflation this milestone was built to examine, and
        it would be dishonest to measure it in a sibling domain while
        committing it here.
        """
        return (
            self.body_id,
            self.heat_capacity.magnitude_in(CAPACITY_UNIT),
            self.ambient_conductance.magnitude_in(CONDUCTANCE_UNIT),
        )

    @property
    def capacity_j_per_k(self) -> float:
        return self.heat_capacity.magnitude_in(CAPACITY_UNIT)

    @property
    def conductance_w_per_k(self) -> float:
        return self.ambient_conductance.magnitude_in(CONDUCTANCE_UNIT)

    @property
    def ambient_k(self) -> float:
        return self.ambient_temperature.magnitude_in(TEMPERATURE_UNIT)

    @property
    def initial_k(self) -> float:
        return self.initial_temperature.magnitude_in(TEMPERATURE_UNIT)

    @property
    def duration_s(self) -> float:
        return self.duration.magnitude_in(TIME_UNIT)

    @property
    def time_constant_s(self) -> float:
        """C/hA. Strictly positive by construction."""
        return self.capacity_j_per_k / self.conductance_w_per_k


def build_lumped_thermal_problem(
    body: ThermalBody,
    *,
    heat_input: Quantity | None = None,
    problem_id: str | None = None,
) -> ScientificProblem:
    """The universal problem statement for one lumped body.

    ``heat_input`` and ``ambient_temperature`` are declared as **variables with
    role CONTROL** rather than as parameters. A parameter is a configured value
    of the problem; these are imposed from outside it. The distinction is the
    one the electrical domain does not make for a resistance, and recording it
    honestly here is the point.

    **TEMPORAL-DEFECT-B, repaired here.** Declaring a control said *that* it is
    imposed and never said *at what value*, so two runs of the same body under
    40 W and 4 W serialized byte-identically while their final temperatures
    differed by 15.6 K. The role declaration is right and is kept; what was
    missing is the operating point.

    ``imposed`` states it, using the one existing core record for "this
    variable holds this value at this stated instant" — an
    :class:`InitialCondition` carrying ``time = 0 s``. This is exact for this
    realization, whose declared assumption is that *the heat input is constant
    over the integrated interval*: a control that does not vary over the
    interval takes its interval-wide value at its start.

    What this deliberately does **not** do:

    * It does not turn a control into a parameter. ``unresolved_inputs``
      reports a ``CONTROL`` variable regardless of any condition on it, so a
      composition still sees both controls as inputs needing a supplier — the
      value is an operating point on the record, not a claim of closure.
    * It does not invent a history, a schedule, or an event. One constant value
      over one interval is all this realization integrates and all that is
      recorded.

    ``heat_input`` is optional because it genuinely may not be known when the
    problem is posed: in a composition it arrives across a declared
    :class:`~engcore.scientific.composition.QuantityDependency`, and a record
    that stated a value the loop then overrode would be worse than one that
    states none. Omitting it is therefore a real answer — "no imposed value is
    declared here" — and :meth:`LumpedThermalSolver.verify_problem_matches_body`
    enforces the other direction: a record that *does* state one may not be
    solved at a different one.

    ``ambient_temperature`` is not optional: the body declares it, so the
    record can always state it, and before this repair it could not.
    """
    imposed = [
        InitialCondition(
            variable=AMBIENT_TEMPERATURE,
            value=body.ambient_temperature,
            time=Quantity(0.0, TIME_UNIT),
            description=(
                "Imposed ambient temperature, constant over the interval."
            ),
        ),
    ]
    if heat_input is not None:
        if not isinstance(heat_input, Quantity):
            raise InvalidScientificProblem(
                "heat_input must be a Quantity carrying watts — a bare number "
                "is not a declaration"
            )
        heat_input.require_compatible(
            POWER_UNIT, context="imposed heat input"
        )
        if not math.isfinite(heat_input.magnitude_in(POWER_UNIT)):
            raise InvalidScientificProblem("imposed heat input must be finite")
        imposed.append(
            InitialCondition(
                variable=HEAT_INPUT,
                value=heat_input,
                time=Quantity(0.0, TIME_UNIT),
                description=(
                    "Imposed heat delivered to the body, constant over the "
                    "interval."
                ),
            )
        )
    return ScientificProblem(
        problem_id=problem_id or f"thermal-lumped-{body.body_id}",
        name=f"Lumped thermal body {body.body_id}",
        description=(
            "Transient temperature of one lumped body over a single interval "
            "of imposed heat input."
        ),
        variables=(
            ScientificVariable(
                name=TEMPERATURE,
                unit=TEMPERATURE_UNIT,
                role=VariableRole.STATE,
                description="Body temperature; evolves over the interval.",
            ),
            ScientificVariable(
                name=HEAT_INPUT,
                unit=POWER_UNIT,
                role=VariableRole.CONTROL,
                description="Externally imposed heat delivered to the body.",
            ),
            ScientificVariable(
                name=AMBIENT_TEMPERATURE,
                unit=TEMPERATURE_UNIT,
                role=VariableRole.CONTROL,
                description="Externally imposed ambient temperature.",
            ),
        ),
        parameters=(
            ScientificParameter(
                name=HEAT_CAPACITY,
                value=body.heat_capacity,
                description="Total heat capacity of the body.",
            ),
            ScientificParameter(
                name=AMBIENT_CONDUCTANCE,
                value=body.ambient_conductance,
                description="Conductance from the body to the ambient.",
            ),
            ScientificParameter(
                name=DURATION,
                value=body.duration,
                description="Length of the interval to advance.",
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=TEMPERATURE,
                value=body.initial_temperature,
                time=Quantity(0.0, TIME_UNIT),
                description="Body temperature at the start of the interval.",
            ),
            *imposed,
        ),
        models=(
            ModelReference(
                LUMPED_CAPACITY_MODEL.model_id, LUMPED_CAPACITY_MODEL.version
            ),
        ),
        required_capabilities=frozenset({LUMPED_CAPACITY_TRANSIENT.name}),
    )


# =====================================================================
# Solver
# =====================================================================

SOLVER_ID = "engcore.thermal.lumped_closed_form"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.math.exp"


@dataclass(frozen=True)
class PreparedLumpedStep:
    """The body, the imposed inputs and the interval this step will advance."""

    body: ThermalBody
    realization: ModelRealizationDefinition
    heat_input_w: float


class LumpedThermalSolver:
    """Advances one lumped body over one interval. Satisfies ScientificSolver.

    The body and its imposed heat input are bound to this instance by problem
    id, exactly as the electrical domain binds a circuit. The binding table is
    instance-local state, never a global registry.
    """

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[ThermalBody, float]] = {}
        self.settings = settings or SolverSettings()

    # -- identity ---------------------------------------------------------
    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return lumped_solver_capabilities()

    # -- binding ----------------------------------------------------------
    def bind_body(
        self, body: ThermalBody, problem_id: str, *, heat_input: Quantity
    ) -> None:
        """Associate a body and its imposed heat input with a problem id.

        Rebinding is idempotent for the same *physical* body and refused for a
        different one, keyed on :attr:`ThermalBody.physical_key`. So the same
        body at a second ambient, over a second interval, or under a second
        heat input rebinds freely — those are operating points — while swapping
        the body itself is refused, because that would let two results claim one
        identity while describing different systems.
        """
        if not isinstance(body, ThermalBody):
            raise InvalidScientificProblem("bind_body expects a ThermalBody")
        watts = heat_input.magnitude_in(POWER_UNIT)
        if not math.isfinite(watts):
            raise InvalidScientificProblem("heat input must be finite")
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0].physical_key != body.physical_key:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different body; "
                f"silently swapping the body behind a problem id would let "
                f"two results claim one identity while describing different "
                f"systems"
            )
        self._bound[key] = (body, watts)

    @staticmethod
    def verify_problem_matches_body(
        problem: ScientificProblem, body: ThermalBody
    ) -> None:
        """Refuse a problem that describes a different body than the one bound.

        The sibling Electrical DC domain guards exactly this with
        ``verify_problem_matches_circuit``, on the grounds that a result whose
        provenance contradicts the system that produced it is worse than no
        result. Without the guard, ``build_lumped_thermal_problem(bodyA, ...)``
        followed by ``bind_body(bodyB, ...)`` would yield a result attributed to
        a problem describing something else, with provenance mixing the two.
        """
        for name, declared in (
            (HEAT_CAPACITY, body.heat_capacity),
            (AMBIENT_CONDUCTANCE, body.ambient_conductance),
            (DURATION, body.duration),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound body declares {declared}"
                )
        conditions = {c.variable: c for c in problem.initial_conditions}
        state = conditions.get(TEMPERATURE)
        if state is None:
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r} must carry an initial "
                f"condition on {TEMPERATURE!r}"
            )
        if state.value.compare(body.initial_temperature) != 0.0:
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r} starts at {state.value} "
                f"but the bound body declares {body.initial_temperature}"
            )
        ambient = conditions.get(AMBIENT_TEMPERATURE)
        if ambient is None:
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r} states no value for the "
                f"imposed control {AMBIENT_TEMPERATURE!r}; a record that does "
                f"not carry its operating point cannot distinguish two runs "
                f"that differ only in it"
            )
        if ambient.value.compare(body.ambient_temperature) != 0.0:
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r} imposes an ambient of "
                f"{ambient.value} but the bound body declares "
                f"{body.ambient_temperature}"
            )

    @staticmethod
    def verify_problem_matches_heat_input(
        problem: ScientificProblem, heat_input: Quantity
    ) -> None:
        """Refuse a problem that states an imposed heat other than the bound one.

        TEMPORAL-DEFECT-B, enforced. Stating the operating point on the record
        is only half the repair: a record that states 40 W and is then solved
        at 4 W is a *worse* artefact than one that states nothing, because it
        reads as attributable and is not. When the record states no imposed
        heat this is silent — that is the composed case, where the value
        arrives across a declared dependency and no record could have carried
        it before the loop ran.
        """
        for condition in problem.initial_conditions:
            if condition.variable != HEAT_INPUT:
                continue
            if condition.value.compare(heat_input) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states an imposed heat "
                    f"input of {condition.value} but the solve was bound to "
                    f"{heat_input}; a result attributed to a record that "
                    f"describes a different operating point is unattributable"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        return LUMPED_CAPACITY_TRANSIENT.name in problem.required_capabilities

    # -- lifecycle --------------------------------------------------------
    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = LUMPED_CLOSED_FORM_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no thermal body is bound to problem "
                f"{problem.problem_id!r}; call bind_body first"
            )
        body, watts = bound
        # Refuse an inconsistent pairing before solving, not after attributing.
        self.verify_problem_matches_body(problem, body)
        self.verify_problem_matches_heat_input(
            problem, Quantity(watts, POWER_UNIT)
        )
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedLumpedStep(
                body=body, realization=realization, heat_input_w=watts
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        step: PreparedLumpedStep = prepared.payload
        body = step.body
        started = time.perf_counter()

        tau = body.time_constant_s
        steady = body.ambient_k + step.heat_input_w / body.conductance_w_per_k
        decay = math.exp(-body.duration_s / tau)
        final = steady + (body.initial_k - steady) * decay

        return RawSolverOutput(
            values={
                TEMPERATURE_METRIC: final,
                STEADY_STATE_TEMPERATURE_METRIC: steady,
                TIME_CONSTANT_METRIC: tau,
            },
            # NOT_APPLICABLE, not CONVERGED. This is a closed-form evaluation:
            # it neither converges nor fails to, and the core's own contract
            # says the two must not be conflated.
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "decay_factor": decay,
                "steps_of_tau": body.duration_s / tau,
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            TEMPERATURE_METRIC: Quantity(
                raw.values[TEMPERATURE_METRIC], TEMPERATURE_UNIT
            ),
            STEADY_STATE_TEMPERATURE_METRIC: Quantity(
                raw.values[STEADY_STATE_TEMPERATURE_METRIC], TEMPERATURE_UNIT
            ),
            TIME_CONSTANT_METRIC: Quantity(
                raw.values[TIME_CONSTANT_METRIC], TIME_UNIT
            ),
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Check the closed form against the balance it claims to solve.

        The residual of ``C dT/dt = Q - hA (T - T_amb)`` is evaluated at the
        end of the interval using the analytic derivative. This is
        self-consistency of the solution against its own differential
        equation — **not** a physical validation and not a coupled-convergence
        claim, and the check says so.
        """
        step: PreparedLumpedStep = prepared.payload
        body = step.body
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="lumped_balance_residual",
                        outcome=ValidationOutcome.FAIL,
                        detail="the solve did not succeed; no residual exists",
                    ),
                )
            )

        final = raw.values[TEMPERATURE_METRIC]
        steady = raw.values[STEADY_STATE_TEMPERATURE_METRIC]
        tau = raw.values[TIME_CONSTANT_METRIC]
        # dT/dt of the closed form at t = duration.
        derivative = -(body.initial_k - steady) * math.exp(
            -body.duration_s / tau
        ) / tau
        residual = abs(
            body.capacity_j_per_k * derivative
            - step.heat_input_w
            + body.conductance_w_per_k * (final - body.ambient_k)
        )
        scale = max(abs(step.heat_input_w), 1.0)
        passed = residual <= 1e-9 * scale
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="lumped_balance_residual",
                    outcome=(
                        ValidationOutcome.PASS if passed else ValidationOutcome.FAIL
                    ),
                    # ESTABLISHES NO LEVEL, deliberately.
                    #
                    # A first draft claimed ANALYTICALLY_VERIFIED. The residual
                    # is not circular — a wrong tau, a wrong steady state or a
                    # flipped exponent each leave it non-zero, so the check does
                    # real work — but it compares the closed form against the
                    # equation the closed form was derived from, with no
                    # independent reference. That is weaker than what every
                    # other solver in this repository has, and those claim only
                    # DIMENSIONALLY_VALID; the byte-pinned conduction solver
                    # measures error against a genuinely independent closed form
                    # and still claims no more. Being the one solver to award
                    # itself the highest level in the taxonomy, from the weakest
                    # evidence, is exactly the unearned claim the result
                    # contract exists to refuse.
                    establishes=None,
                    residual=residual,
                    tolerance=1e-9 * scale,
                    detail=(
                        f"|C dT/dt - Q + hA (T - T_amb)| = {residual:.3e} W "
                        f"against a scale of {scale:.3e} W. Verification of "
                        f"the closed form against the balance it solves; no "
                        f"physical validation and no coupled-convergence claim."
                    ),
                ),
            )
        )
