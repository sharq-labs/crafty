"""The three claims that belong to the *assembly*, not to either physics.

`PROPULSION0`. Everything here is topology-shaped or composition-shaped, which
is exactly why none of it is in a domain module:

======================================  ==========================================
:data:`SERIES_LOOP_RESISTANCE_MODEL`    two elements carrying one current add
:data:`MOTOR_HEAT_GENERATION_MODEL`     two loss channels heat one body
:data:`DRIVE_OPERATING_POINT_MODEL`     the loop KVL solved jointly with the
                                        machine's five rotational claims
======================================  ==========================================

Why the first two exist at all: the fan-in wall, and the move that clears it
----------------------------------------------------------------------------
``FixedPointCouplingPlan`` refuses two dependencies sharing one
``(target_problem_id, target_quantity)`` endpoint, because **no record states
whether they sum, override or split**. `COMPOSITE-SYSTEM0` named that as the
next structural wall and predicted it would be hit "precisely when two sources
feed one endpoint". This milestone hits it **twice**:

* the motor's body receives ``P_copper`` from the circuit and
  ``P_internal_mechanical_loss`` from the machine;
* the machine's operating point needs ``R_wire_a + R_motor + R_wire_b``.

Neither is answered by inventing a combination rule in the coupling plan. Both
are answered the same way: **the combination is a scientific claim, so it is a
model.** Two edges into two *distinct* named inputs of a declared model, and one
edge out of its declared output. The plan's refusal is never tripped, no
universal fan-in semantics are minted, and every summed number carries an
``ExecutionBinding``.

Arity, and why these are binary — and where the two claims differ
------------------------------------------------------------------
:data:`SERIES_LOOP_RESISTANCE_MODEL` takes **exactly two** resistances and is
instantiated **N-1 times** for an N-element loop. A model that took "the three
resistances of a feed, a winding and a return" would have written the exercised
topology into a reusable record, so a four-element loop would need a *different
model*. Binary keeps the arity in the number of *problem instances*, where
topology belongs. The association is left-to-right in the declared element
order; in floating point the order affects the last bits, and the order is a
declared fact of the composition rather than an implementation detail.

**The two are not symmetric, and an earlier draft of this docstring wrongly
said they were.** Chaining is licensed for the series claim and *denied* by the
heat claim, because a partial sum of two loss channels is not itself a channel
dissipating into the body. So a four-element loop costs one more *problem
instance*, while a third loss channel — iron loss, say — costs a new *model
record*. That asymmetry is a real limit on the arity result and it is stated on
both records rather than left to be discovered.

A single generic "add two quantities of the same dimension" model was designed
and rejected: it would carry no assumptions and no validity domain, it would be
satisfiable by any two numbers that happen to share a unit, and it would make
"the two elements carry the same current" and "both loss channels heat the same
body" the same claim. Those are two different physical statements and they are
two different records.

Why the operating point is one model and not five
-------------------------------------------------
``ModelRealizationDefinition.model`` is a **single** ``ModelReference``, so no
realization record can state that one closed form discharges several model
records jointly. The five rotational claims live in
``engcore.domains.mechanical_rotational`` and are *referenced* by the operating
point problem; the joint solution is declared here as its own model with its own
realization, and the five constituent models appear in the result's provenance
with ``realization=None`` — which is a true answer, not a gap.

That is a measured contract observation, recorded as the **second independent
consumer** of a gap the platform already had on record. It is not repaired here.

Why the loop KVL is represented twice, on purpose
-------------------------------------------------
:data:`DRIVE_OPERATING_POINT_MODEL` states ``V = I R_loop + E`` and solves it in
closed form. The same loop is *also* posed as a ``DCCircuit`` and solved by
modified nodal analysis, because the circuit is what supplies the per-element
dissipation, the terminal voltages, and the external-provider substitution seam.

The duplication is real and is not hidden. It is converted into an **independent
numerical verification**: the pack reconciles the circuit's current against this
model's current, and the circuit's back-EMF-source absorbed power against this
model's converted power, and **raises** when they disagree. Two representations
of one law that must agree is a check; one representation trusted twice is not.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

from ...domains import mechanical_rotational as rot
from ...domains.electrical import conductor_material as cmat
from ...scientific.capabilities import ScientificCapability
from ...scientific.errors import InvalidScientificProblem
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from ...scientific.models.definition import (
    InputSourceKind,
    ModelInputSpec,
    ModelOutputSpec,
    ModelType,
    ModelValidationStatus,
    RangeCondition,
    ScientificModelDefinition,
    ValidityDomain,
)
from ...scientific.models.registry import ModelRegistry
from ...scientific.realizations.definition import (
    ImplementationReference,
    ModelFormulation,
    ModelRealizationDefinition,
)
from ...scientific.realizations.registry import RealizationRegistry
from ...scientific.results.validation import (
    ValidationCheck,
    ValidationOutcome,
    ValidationReport,
)
from ...scientific.solvers.capability import (
    CoreCapabilities,
    SolverCapability,
    SolverCapabilityId,
)
from ...scientific.solvers.protocol import (
    ConvergenceState,
    PreparedSolve,
    RawSolverOutput,
    SolverIdentity,
    SolverSettings,
)
from ...scientific.units.quantity import Quantity

__all__ = [
    "ANGULAR_VELOCITY_METRIC",
    "BACK_EMF_METRIC",
    "CONVERTED_POWER_METRIC",
    "CURRENT_METRIC",
    "DRIVE_OPERATING_POINT_MODEL",
    "DRIVE_OPERATING_POINT_REALIZATION",
    "ELECTRICAL_DISSIPATION",
    "ELECTROMAGNETIC_TORQUE_METRIC",
    "INTERNAL_LOSS_POWER_METRIC",
    "INTERNAL_LOSS_TORQUE_METRIC",
    "LOAD_TORQUE_METRIC",
    "LOOP_RESISTANCE",
    "MECHANICAL_DISSIPATION",
    "MECHANICAL_OUTPUT_POWER_METRIC",
    "MOTOR_HEAT_GENERATION_MODEL",
    "MOTOR_HEAT_GENERATION_REALIZATION",
    "RESISTANCE_A",
    "RESISTANCE_B",
    "ROTATIONAL_SPEED_METRIC",
    "SERIES_LOOP_RESISTANCE_MODEL",
    "SERIES_LOOP_RESISTANCE_REALIZATION",
    "SERIES_RESISTANCE_METRIC",
    "SUPPLY_VOLTAGE",
    "TOTAL_DISSIPATION",
    "DriveOperatingPointSolver",
    "MotorHeatGenerationSolver",
    "SeriesResistanceSolver",
    "build_motor_heat_problem",
    "build_operating_point_problem",
    "build_series_resistance_problem",
    "propulsion_model_registry",
    "propulsion_realizations",
    "propulsion_solver_capabilities",
]

MODEL_VERSION = "0.1.0"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.float"

POWER_UNIT = "watt"
VOLTAGE_UNIT = "volt"
CURRENT_UNIT = "ampere"

# ---- series resistance ------------------------------------------------
RESISTANCE_A = "resistance_a"
RESISTANCE_B = "resistance_b"
SERIES_RESISTANCE_METRIC = "series_resistance"

# ---- motor heat generation --------------------------------------------
ELECTRICAL_DISSIPATION = "electrical_dissipation"
MECHANICAL_DISSIPATION = "mechanical_dissipation"
TOTAL_DISSIPATION = "total_dissipation"

# ---- drive operating point --------------------------------------------
LOOP_RESISTANCE = "loop_resistance"
SUPPLY_VOLTAGE = "supply_voltage"
CURRENT_METRIC = "current"
ANGULAR_VELOCITY_METRIC = "angular_velocity"
ROTATIONAL_SPEED_METRIC = "rotational_speed"
BACK_EMF_METRIC = "back_emf"
ELECTROMAGNETIC_TORQUE_METRIC = "electromagnetic_torque"
LOAD_TORQUE_METRIC = "load_torque"
INTERNAL_LOSS_TORQUE_METRIC = "internal_loss_torque"
MECHANICAL_OUTPUT_POWER_METRIC = "mechanical_output_power"
INTERNAL_LOSS_POWER_METRIC = "internal_loss_power"
CONVERTED_POWER_METRIC = "converted_power"

PROVIDES_SERIES_RESISTANCE = ScientificCapability.parse(
    "electrical:series_loop_resistance"
)
PROVIDES_MOTOR_HEAT = ScientificCapability.parse("thermal:motor_heat_generation")
PROVIDES_OPERATING_POINT = ScientificCapability.parse(
    "electromechanical:drive_operating_point"
)

DRIVE_OPERATING_POINT_CAPABILITY = SolverCapability(
    "electromechanical:series_drive_operating_point",
    "Closed-form operating point of a single series electromechanical drive",
)


# =====================================================================
# Claim 1 — two elements carrying one current add
# =====================================================================

SERIES_LOOP_RESISTANCE_MODEL = ScientificModelDefinition(
    model_id="electrical.series.two_element_resistance",
    version=MODEL_VERSION,
    name="Series resistance of two elements carrying one current",
    domain="electrical",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Two resistive elements traversed by the same current present a "
        "resistance equal to the sum of theirs: R = R_a + R_b."
    ),
    inputs=(
        ModelInputSpec(
            name=RESISTANCE_A,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=cmat.RESISTANCE_UNIT,
            role=VariableRole.CONTROL,
            description="Resistance of the first element; imposed from outside.",
        ),
        ModelInputSpec(
            name=RESISTANCE_B,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=cmat.RESISTANCE_UNIT,
            role=VariableRole.CONTROL,
            description="Resistance of the second element; imposed from outside.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=SERIES_RESISTANCE_METRIC,
            unit_exemplar=cmat.RESISTANCE_UNIT,
            description="Resistance of the two elements in series.",
        ),
    ),
    assumptions=(
        "the two elements are traversed by one and the same current; this is "
        "what makes the sum correct and it is a property of the assembly, not "
        "of either element",
        "exactly two elements. A longer string is represented by instantiating "
        "this claim once per join, never by a wider model: the number of "
        "elements is a fact about a topology and does not belong in a reusable "
        "record",
        "the association is left-to-right in the declared element order; in "
        "floating point the order affects the final bits, and the order is "
        "therefore a declared fact of the composition",
    ),
    validity=ValidityDomain(
        conditions=(),
        # Both inputs arrive as VARIABLES, so a RangeCondition on either would
        # be permanently UNKNOWN in `ScientificProblem.validity_context`, which
        # is built from parameters. The positivity check is a solver
        # admissibility check instead — the same asymmetry the geometric
        # resistance model already records for its resistivity input.
        description=(
            "Both resistances are imposed controls rather than configured "
            "parameters, so their admissibility is checked by the evaluator "
            "and not by a validity condition that could never be assessed."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


# =====================================================================
# Claim 2 — two loss channels heat one body
# =====================================================================

MOTOR_HEAT_GENERATION_MODEL = ScientificModelDefinition(
    model_id="thermal.machine.two_channel_heat_generation",
    version=MODEL_VERSION,
    name="Heat generated in a machine by its resistive and mechanical losses",
    domain="thermal",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "The heat delivered to a machine's lumped body is the sum of the "
        "power dissipated resistively in its winding and the power absorbed "
        "by its internal mechanical loss: Q = P_electrical + P_mechanical."
    ),
    inputs=(
        ModelInputSpec(
            name=ELECTRICAL_DISSIPATION,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=POWER_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Power dissipated resistively in the winding; imposed from "
                "outside this claim."
            ),
        ),
        ModelInputSpec(
            name=MECHANICAL_DISSIPATION,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=POWER_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Power absorbed by internal mechanical loss; imposed from "
                "outside this claim."
            ),
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=TOTAL_DISSIPATION,
            unit_exemplar=POWER_UNIT,
            description="Heat delivered to the machine's lumped body.",
        ),
    ),
    assumptions=(
        "both channels dissipate into ONE lumped body at one temperature; a "
        "machine whose winding and whose bearings are at materially different "
        "temperatures is outside this claim",
        "all of the internal mechanical loss becomes heat in that same body — "
        "none of it leaves as sound, none of it leaves through the shaft",
        "iron/core loss, windage and stray load loss are NOT separately "
        "represented; whatever of them a caller intends is folded into the "
        "declared internal mechanical loss or is absent, and this model does "
        "not claim otherwise",
        "there are exactly two channels; a third heat source is a third input "
        "and therefore a different claim, not a wider one",
        "UNLIKE the series-resistance claim, this one does NOT license "
        "chaining. A partial sum of two channels is not itself a channel "
        "dissipating into the body, so an intermediate instance is not an "
        "admissible operand, and a third loss channel requires a different "
        "model record rather than a second instance of this one. Stated "
        "because the sibling binary claim licenses exactly the opposite and "
        "the two must not be read as one pattern",
    ),
    validity=ValidityDomain(
        conditions=(),
        description=(
            "Both inputs are imposed controls, so their admissibility is "
            "checked by the evaluator rather than by a condition that could "
            "never be assessed from the problem's parameters."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


# =====================================================================
# Claim 3 — the loop KVL solved jointly with the machine
# =====================================================================

DRIVE_OPERATING_POINT_MODEL = ScientificModelDefinition(
    model_id="electromechanical.series_drive.operating_point",
    version=MODEL_VERSION,
    name="Steady operating point of a single series electromechanical drive",
    domain="electromechanical",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "The simultaneous solution, for one series loop across one ideal "
        "source, of the loop KVL V = I R_loop + E together with the machine's "
        "back-EMF law, torque production law, viscous loss law, quadratic "
        "load law and steady-speed torque balance. Reduces to "
        "k_load w^2 + (b + k_t k_e / R_loop) w - k_t V / R_loop = 0, whose "
        "unique positive root is the operating speed."
    ),
    inputs=(
        ModelInputSpec(
            name=LOOP_RESISTANCE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=cmat.RESISTANCE_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Total resistance of the loop, including the machine winding; "
                "imposed from outside this claim."
            ),
        ),
        ModelInputSpec(
            name=SUPPLY_VOLTAGE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=VOLTAGE_UNIT,
            description="Ideal source voltage driving the loop.",
        ),
        ModelInputSpec(
            name=rot.TORQUE_CONSTANT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=rot.TORQUE_CONSTANT_UNIT,
            description="Machine torque constant.",
        ),
        ModelInputSpec(
            name=rot.BACK_EMF_CONSTANT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=rot.BACK_EMF_CONSTANT_UNIT,
            description="Machine back-EMF constant.",
        ),
        ModelInputSpec(
            name=rot.LOAD_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=rot.LOAD_COEFFICIENT_UNIT,
            description="Quadratic load coefficient.",
        ),
        ModelInputSpec(
            name=rot.VISCOUS_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=rot.VISCOUS_COEFFICIENT_UNIT,
            description="Internal viscous loss coefficient.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=ANGULAR_VELOCITY_METRIC,
            unit_exemplar=rot.ANGULAR_VELOCITY_UNIT,
            description="Shaft speed at which every declared torque balances.",
        ),
        ModelOutputSpec(
            metric=ROTATIONAL_SPEED_METRIC,
            unit_exemplar=rot.ROTATIONAL_SPEED_UNIT,
            description=(
                "The same speed, expressed in the unit an engineer reads. It "
                "is a UNIT CONVERSION performed by the units layer and not a "
                "second claim; no constant is applied anywhere in this pack."
            ),
        ),
        ModelOutputSpec(
            metric=CURRENT_METRIC,
            unit_exemplar=CURRENT_UNIT,
            description="Loop current at the operating point.",
        ),
        ModelOutputSpec(
            metric=BACK_EMF_METRIC,
            unit_exemplar=VOLTAGE_UNIT,
            description="Voltage the machine develops against the supply.",
        ),
        ModelOutputSpec(
            metric=ELECTROMAGNETIC_TORQUE_METRIC,
            unit_exemplar=rot.TORQUE_UNIT,
            description="Torque developed on the shaft.",
        ),
        ModelOutputSpec(
            metric=LOAD_TORQUE_METRIC,
            unit_exemplar=rot.TORQUE_UNIT,
            description="Torque absorbed by the declared load.",
        ),
        ModelOutputSpec(
            metric=INTERNAL_LOSS_TORQUE_METRIC,
            unit_exemplar=rot.TORQUE_UNIT,
            description="Torque absorbed internally by the machine.",
        ),
        ModelOutputSpec(
            metric=MECHANICAL_OUTPUT_POWER_METRIC,
            unit_exemplar=POWER_UNIT,
            description=(
                "Power delivered to the load. This is the useful output and "
                "is deliberately named apart from the internal loss."
            ),
        ),
        ModelOutputSpec(
            metric=INTERNAL_LOSS_POWER_METRIC,
            unit_exemplar=POWER_UNIT,
            description=(
                "Power absorbed by internal mechanical loss. It leaves the "
                "mechanical account and enters the thermal one."
            ),
        ),
        ModelOutputSpec(
            metric=CONVERTED_POWER_METRIC,
            unit_exemplar=POWER_UNIT,
            description=(
                "Power crossing the electromechanical boundary, E*I. Equal to "
                "the sum of the two mechanical channels iff k_e equals k_t in "
                "SI, which is why that identity is enforced at admission."
            ),
        ),
    ),
    assumptions=(
        "SINGLE SERIES LOOP across one ideal voltage source. A parallel "
        "branch, a second source or a shunt path invalidates the closed form "
        "outright; this is a topology-shaped claim and says so",
        "steady operating point: d(omega)/dt = 0 and dI/dt = 0. No inertia, no "
        "inductance, no transient",
        "the source is ideal: any internal resistance it has must be declared "
        "as part of the loop resistance, because nothing here represents it",
        "in SI the numerical value of k_e in V*s/rad equals that of k_t in "
        "N*m/A; the closed form does NOT enforce that identity, admission does",
        "the machine's winding resistance is part of the supplied loop "
        "resistance and is not separately visible to this claim",
        "the loop KVL stated here is also represented by the modified nodal "
        "analysis of the posed circuit; the two are reconciled numerically "
        "and a disagreement is raised, not recorded",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=SUPPLY_VOLTAGE,
                minimum=Quantity(0.0, VOLTAGE_UNIT),
                minimum_inclusive=False,
                description="A loop with no source has no operating point.",
            ),
            RangeCondition(
                name=rot.TORQUE_CONSTANT,
                minimum=Quantity(0.0, rot.TORQUE_CONSTANT_UNIT),
                minimum_inclusive=False,
                description="Strictly positive.",
            ),
            RangeCondition(
                name=rot.BACK_EMF_CONSTANT,
                minimum=Quantity(0.0, rot.BACK_EMF_CONSTANT_UNIT),
                minimum_inclusive=False,
                description="Strictly positive.",
            ),
            RangeCondition(
                name=rot.LOAD_COEFFICIENT,
                minimum=Quantity(0.0, rot.LOAD_COEFFICIENT_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive. A vanishing coefficient degenerates "
                    "the quadratic to a linear relation, and that is a "
                    "different model rather than a branch of this one."
                ),
            ),
            RangeCondition(
                name=rot.VISCOUS_COEFFICIENT,
                minimum=Quantity(0.0, rot.VISCOUS_COEFFICIENT_UNIT),
                minimum_inclusive=True,
                description="Non-negative; zero is a lossless shaft.",
            ),
        ),
        description=(
            "Every configured parameter is bounded here. The loop resistance "
            "is an imposed control and is checked by the evaluator instead, "
            "for the reason recorded on the series model."
        ),
    ),
    required_capabilities=frozenset(
        {
            CoreCapabilities.ALGEBRAIC.name,
            DRIVE_OPERATING_POINT_CAPABILITY.name,
        }
    ),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


def _realization(
    model: ScientificModelDefinition,
    suffix: str,
    name: str,
    description: str,
    provides: ScientificCapability,
    *,
    solver_capabilities: frozenset,
    assumptions: tuple[str, ...],
) -> ModelRealizationDefinition:
    return ModelRealizationDefinition(
        realization_id=f"{model.model_id}.{suffix}",
        version="0.1.0",
        model=ModelReference(model.model_id, model.version),
        formulation=ModelFormulation.ALGEBRAIC,
        name=name,
        description=description,
        provided_capabilities=frozenset({provides}),
        required_solver_capabilities=solver_capabilities,
        assumptions=assumptions,
        implementation=ImplementationReference(
            implementation_id="engcore.systems.propulsion.models",
            version="0.1.0",
            reference="see the model description",
        ),
    )


SERIES_LOOP_RESISTANCE_REALIZATION = _realization(
    SERIES_LOOP_RESISTANCE_MODEL,
    "direct",
    "Direct evaluation of the two-element series sum",
    "R = R_a + R_b, evaluated as written and in one declared order.",
    PROVIDES_SERIES_RESISTANCE,
    solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=(
        "the two operands are added once, left to right, with no "
        "compensated-summation technique applied",
    ),
)

MOTOR_HEAT_GENERATION_REALIZATION = _realization(
    MOTOR_HEAT_GENERATION_MODEL,
    "direct",
    "Direct evaluation of the two-channel heat sum",
    "Q = P_electrical + P_mechanical, evaluated as written.",
    PROVIDES_MOTOR_HEAT,
    solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=(
        "the two operands are added once, in the declared channel order",
    ),
)

DRIVE_OPERATING_POINT_REALIZATION = _realization(
    DRIVE_OPERATING_POINT_MODEL,
    "closed_form",
    "Closed-form root of the series drive speed balance",
    (
        "Substitutes the loop KVL and the four constitutive laws into the "
        "torque balance, producing k_load w^2 + (b + k_t k_e / R_loop) w - "
        "k_t V / R_loop = 0, and takes its unique positive root. No iteration "
        "is performed and no initial guess is needed."
    ),
    PROVIDES_OPERATING_POINT,
    solver_capabilities=frozenset(
        {
            SolverCapabilityId.coerce(DRIVE_OPERATING_POINT_CAPABILITY),
            SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC),
        }
    ),
    assumptions=(
        "exact for the algebraic system it solves; no discretization error "
        "and no convergence tolerance is involved",
        "the positive root is unique because the product of the roots is "
        "strictly negative for the declared parameter ranges, so no root "
        "selection heuristic is applied",
        "this realization discharges the model named on this record. The five "
        "rotational claims it also satisfies are referenced by the problem "
        "and appear in provenance with realization=None, because "
        "ModelRealizationDefinition.model is a single reference and no "
        "record can state a joint realization",
    ),
)


_PROPULSION_MODELS = (
    SERIES_LOOP_RESISTANCE_MODEL,
    MOTOR_HEAT_GENERATION_MODEL,
    DRIVE_OPERATING_POINT_MODEL,
)
_PROPULSION_REALIZATIONS = (
    SERIES_LOOP_RESISTANCE_REALIZATION,
    MOTOR_HEAT_GENERATION_REALIZATION,
    DRIVE_OPERATING_POINT_REALIZATION,
)


def propulsion_model_registry() -> ModelRegistry:
    return ModelRegistry(_PROPULSION_MODELS)


def propulsion_realizations() -> RealizationRegistry:
    return RealizationRegistry(_PROPULSION_REALIZATIONS)


def propulsion_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({DRIVE_OPERATING_POINT_CAPABILITY, CoreCapabilities.ALGEBRAIC})


# =====================================================================
# Problem statements
# =====================================================================

def _control(name: str, unit: str, description: str) -> ScientificVariable:
    return ScientificVariable(
        name=name, unit=unit, role=VariableRole.CONTROL, description=description
    )


def build_series_resistance_problem(problem_id: str) -> ScientificProblem:
    """One join of two resistances. The problem carries no value of its own.

    Both operands arrive across declared edges, so neither is a parameter here.
    A problem that carried them as parameters would state an operating point it
    cannot know before the composition runs.
    """
    return ScientificProblem(
        problem_id=problem_id,
        name=f"Series resistance join {problem_id}",
        description="Evaluate R = R_a + R_b for two elements carrying one current.",
        variables=(
            _control(
                RESISTANCE_A, cmat.RESISTANCE_UNIT,
                "Resistance of the first element; imposed from outside.",
            ),
            _control(
                RESISTANCE_B, cmat.RESISTANCE_UNIT,
                "Resistance of the second element; imposed from outside.",
            ),
        ),
        models=(
            ModelReference(
                SERIES_LOOP_RESISTANCE_MODEL.model_id,
                SERIES_LOOP_RESISTANCE_MODEL.version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def build_motor_heat_problem(problem_id: str) -> ScientificProblem:
    """Two loss channels, two named controls, one heat output."""
    return ScientificProblem(
        problem_id=problem_id,
        name=f"Machine heat generation {problem_id}",
        description=(
            "Evaluate the heat delivered to a machine's lumped body from its "
            "resistive and its internal mechanical losses."
        ),
        variables=(
            _control(
                ELECTRICAL_DISSIPATION, POWER_UNIT,
                "Resistive dissipation in the winding; imposed from outside.",
            ),
            _control(
                MECHANICAL_DISSIPATION, POWER_UNIT,
                "Internal mechanical dissipation; imposed from outside.",
            ),
        ),
        models=(
            ModelReference(
                MOTOR_HEAT_GENERATION_MODEL.model_id,
                MOTOR_HEAT_GENERATION_MODEL.version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def build_operating_point_problem(
    problem_id: str,
    *,
    supply_voltage: Quantity,
    constants: rot.MachineConstants,
    load: rot.RotationalLoad,
) -> ScientificProblem:
    """The operating-point statement, referencing every claim it discharges.

    ``models`` names **six** records: this pack's joint claim and the five
    rotational claims in the mechanical domain that the closed form also
    satisfies. Naming only the joint one would hide which physics was used;
    naming only the five would hide that they were solved together.
    """
    return ScientificProblem(
        problem_id=problem_id,
        name=f"Series drive operating point {problem_id}",
        description=(
            "Solve the loop KVL simultaneously with the machine's transduction "
            "laws, its internal loss law, the declared load law and the "
            "steady-speed torque balance."
        ),
        variables=(
            _control(
                LOOP_RESISTANCE, cmat.RESISTANCE_UNIT,
                "Total loop resistance; imposed from outside.",
            ),
        ),
        parameters=(
            ScientificParameter(
                name=SUPPLY_VOLTAGE,
                value=supply_voltage,
                description="Declared ideal source voltage.",
            ),
            *constants.machine_parameters(),
            *load.load_parameters(),
        ),
        models=(
            ModelReference(
                DRIVE_OPERATING_POINT_MODEL.model_id,
                DRIVE_OPERATING_POINT_MODEL.version,
            ),
            ModelReference(rot.BACK_EMF_MODEL.model_id, rot.BACK_EMF_MODEL.version),
            ModelReference(
                rot.TORQUE_PRODUCTION_MODEL.model_id,
                rot.TORQUE_PRODUCTION_MODEL.version,
            ),
            ModelReference(
                rot.VISCOUS_ROTATIONAL_LOSS_MODEL.model_id,
                rot.VISCOUS_ROTATIONAL_LOSS_MODEL.version,
            ),
            ModelReference(
                rot.QUADRATIC_ROTATIONAL_LOAD_MODEL.model_id,
                rot.QUADRATIC_ROTATIONAL_LOAD_MODEL.version,
            ),
            ModelReference(
                rot.ROTATIONAL_TORQUE_BALANCE_MODEL.model_id,
                rot.ROTATIONAL_TORQUE_BALANCE_MODEL.version,
            ),
        ),
        required_capabilities=frozenset(
            {
                CoreCapabilities.ALGEBRAIC.name,
                DRIVE_OPERATING_POINT_CAPABILITY.name,
                rot.MECHANICAL_OPERATING_POINT.name,
            }
        ),
    )


# =====================================================================
# Evaluators
# =====================================================================

def _admissible(value: Quantity, unit: str, label: str) -> float:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(f"{label} must be a Quantity")
    value.require_compatible(unit, context=label)
    magnitude = value.magnitude_in(unit)
    if magnitude <= 0.0:
        raise InvalidScientificProblem(
            f"{label} must be strictly positive, got {value}"
        )
    return magnitude


def _finite_non_negative(value: Quantity, unit: str, label: str) -> float:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(f"{label} must be a Quantity")
    value.require_compatible(unit, context=label)
    magnitude = value.magnitude_in(unit)
    if magnitude < 0.0:
        raise InvalidScientificProblem(
            f"{label} must be non-negative, got {value}"
        )
    return magnitude


@dataclass(frozen=True)
class _PreparedSum:
    left: float
    right: float
    realization: ModelRealizationDefinition


class _BinarySumSolver:
    """Shared machinery for the two binary claims. **Not a shared model.**

    The two models are different physical statements with different assumptions
    and different names, and they stay two records. What is shared here is only
    the arithmetic and the protocol plumbing, which carries no physics.
    """

    _MODEL: ScientificModelDefinition
    _REALIZATION: ModelRealizationDefinition
    _LEFT: str
    _RIGHT: str
    _OUTPUT: str
    _UNIT: str
    _SOLVER_ID: str

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[float, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(self._SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return frozenset({CoreCapabilities.ALGEBRAIC})

    def bind_operands(
        self, problem_id: str, *, left: Quantity, right: Quantity
    ) -> None:
        self._bound[str(problem_id)] = (
            self._admit(left, f"{self._LEFT} of {problem_id!r}"),
            self._admit(right, f"{self._RIGHT} of {problem_id!r}"),
        )

    def _admit(self, value: Quantity, label: str) -> float:
        raise NotImplementedError

    def supports(self, problem: ScientificProblem) -> bool:
        return any(r.model_id == self._MODEL.model_id for r in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition | None = None,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no operands are bound to problem {problem.problem_id!r}; "
                f"call bind_operands first"
            )
        left, right = bound
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=_PreparedSum(
                left=left, right=right,
                realization=realization or self._REALIZATION,
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        payload: _PreparedSum = prepared.payload
        started = time.perf_counter()
        return RawSolverOutput(
            values={self._OUTPUT: payload.left + payload.right},
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={self._LEFT: payload.left, self._RIGHT: payload.right},
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {self._OUTPUT: Quantity(raw.values[self._OUTPUT], self._UNIT)}

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Check the sum against the two operands the run actually recorded.

        Circular by construction for the arithmetic itself, and it says so. What
        it does test is that the **recorded** operands and the **recorded**
        output describe the same addition — which fails if a metric is extracted
        under the wrong name or a unit is mis-declared.
        """
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name=f"{self._OUTPUT}_sum",
                        outcome=ValidationOutcome.FAIL,
                        detail="the solve did not succeed; no sum exists",
                    ),
                )
            )
        expected = raw.diagnostics[self._LEFT] + raw.diagnostics[self._RIGHT]
        residual = abs(raw.values[self._OUTPUT] - expected)
        tolerance = 1e-15 * max(abs(expected), 1.0)
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name=f"{self._OUTPUT}_sum",
                    outcome=(
                        ValidationOutcome.PASS
                        if residual <= tolerance
                        else ValidationOutcome.FAIL
                    ),
                    establishes=None,
                    residual=residual,
                    tolerance=tolerance,
                    detail=(
                        "the recorded output equals the recorded operands' "
                        "sum. This verifies bookkeeping, not physics, and "
                        "establishes no validation level."
                    ),
                ),
            )
        )


class SeriesResistanceSolver(_BinarySumSolver):
    """``R = R_a + R_b`` for two elements carrying one current."""

    _MODEL = SERIES_LOOP_RESISTANCE_MODEL
    _REALIZATION = SERIES_LOOP_RESISTANCE_REALIZATION
    _LEFT = RESISTANCE_A
    _RIGHT = RESISTANCE_B
    _OUTPUT = SERIES_RESISTANCE_METRIC
    _UNIT = cmat.RESISTANCE_UNIT
    _SOLVER_ID = "engcore.propulsion.series_resistance_evaluator"

    def _admit(self, value: Quantity, label: str) -> float:
        return _admissible(value, cmat.RESISTANCE_UNIT, label)


class MotorHeatGenerationSolver(_BinarySumSolver):
    """``Q = P_electrical + P_mechanical`` into one lumped body."""

    _MODEL = MOTOR_HEAT_GENERATION_MODEL
    _REALIZATION = MOTOR_HEAT_GENERATION_REALIZATION
    _LEFT = ELECTRICAL_DISSIPATION
    _RIGHT = MECHANICAL_DISSIPATION
    _OUTPUT = TOTAL_DISSIPATION
    _UNIT = POWER_UNIT
    _SOLVER_ID = "engcore.propulsion.machine_heat_evaluator"

    def _admit(self, value: Quantity, label: str) -> float:
        # Non-negative rather than strictly positive: a lossless shaft
        # dissipates exactly zero mechanically, and refusing that would refuse
        # a case the loss model explicitly admits.
        return _finite_non_negative(value, POWER_UNIT, label)


@dataclass(frozen=True)
class PreparedOperatingPoint:
    supply_voltage_v: float
    loop_resistance_ohm: float
    k_t: float
    k_e: float
    k_load: float
    viscous: float
    realization: ModelRealizationDefinition


class DriveOperatingPointSolver:
    """Solves one series drive's operating point in closed form.

    The five rotational claims are evaluated **inside** this one solve. That is
    why the result it produces carries six model references and only one
    realization: see the module docstring.
    """

    _SOLVER_ID = "engcore.propulsion.series_drive_operating_point"

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, PreparedOperatingPoint] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(self._SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return propulsion_solver_capabilities()

    def bind_drive(
        self,
        problem_id: str,
        *,
        supply_voltage: Quantity,
        constants: rot.MachineConstants,
        load: rot.RotationalLoad,
        loop_resistance: Quantity,
        realization: ModelRealizationDefinition = DRIVE_OPERATING_POINT_REALIZATION,
    ) -> None:
        # Energy conservation is checked HERE as well as at the pack's
        # admission gate, and the duplication is the point.
        #
        # `architecture-falsifier` found the path: this solver is published, so
        # a caller holding it directly could bind an inconsistent constant pair,
        # get a number out of `solve`, and consume it while `validate` reported
        # FAIL — which is precisely the repository's own worst historical
        # defect (a validation FAIL whose value was consumed anyway, converging
        # 18 K wrong) reproduced one level below the gate that was supposed to
        # prevent it. A gate at the composition boundary does not protect the
        # record boundary, so the record boundary carries its own.
        rot.require_energy_consistent_constants(constants)
        self._bound[str(problem_id)] = PreparedOperatingPoint(
            supply_voltage_v=_admissible(
                supply_voltage, VOLTAGE_UNIT, f"supply voltage of {problem_id!r}"
            ),
            loop_resistance_ohm=_admissible(
                loop_resistance, cmat.RESISTANCE_UNIT,
                f"loop resistance of {problem_id!r}",
            ),
            k_t=constants.k_t_si,
            k_e=constants.k_e_si,
            k_load=load.k_load_si,
            viscous=load.b_si,
            realization=realization,
        )

    @staticmethod
    def verify_problem_matches_drive(
        problem: ScientificProblem,
        *,
        supply_voltage: Quantity,
        constants: rot.MachineConstants,
        load: rot.RotationalLoad,
    ) -> None:
        for name, declared in (
            (SUPPLY_VOLTAGE, supply_voltage),
            (rot.TORQUE_CONSTANT, constants.torque_constant),
            (rot.BACK_EMF_CONSTANT, constants.back_emf_constant),
            (rot.LOAD_COEFFICIENT, load.load_coefficient),
            (rot.VISCOUS_COEFFICIENT, load.viscous_coefficient),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound drive declares {declared}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        return DRIVE_OPERATING_POINT_CAPABILITY.name in problem.required_capabilities

    def prepare(self, problem: ScientificProblem) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no drive is bound to problem {problem.problem_id!r}; call "
                f"bind_drive first"
            )
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=bound,
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        p: PreparedOperatingPoint = prepared.payload
        started = time.perf_counter()

        omega = rot.positive_root_of_speed_balance(
            quadratic=p.k_load,
            linear=p.viscous + p.k_t * p.k_e / p.loop_resistance_ohm,
            constant=p.k_t * p.supply_voltage_v / p.loop_resistance_ohm,
        )
        back_emf = p.k_e * omega
        current = (p.supply_voltage_v - back_emf) / p.loop_resistance_ohm
        electromagnetic_torque = p.k_t * current
        load_torque = p.k_load * omega * omega
        loss_torque = p.viscous * omega

        return RawSolverOutput(
            values={
                ANGULAR_VELOCITY_METRIC: omega,
                CURRENT_METRIC: current,
                BACK_EMF_METRIC: back_emf,
                ELECTROMAGNETIC_TORQUE_METRIC: electromagnetic_torque,
                LOAD_TORQUE_METRIC: load_torque,
                INTERNAL_LOSS_TORQUE_METRIC: loss_torque,
                MECHANICAL_OUTPUT_POWER_METRIC: load_torque * omega,
                INTERNAL_LOSS_POWER_METRIC: loss_torque * omega,
                CONVERTED_POWER_METRIC: back_emf * current,
            },
            # A closed form neither converges nor fails to; saying CONVERGED
            # here would make an evaluation and an iteration the same token.
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "loop_resistance_ohm": p.loop_resistance_ohm,
                "supply_voltage_v": p.supply_voltage_v,
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        """Restore units, and let the units layer produce the readable speed.

        ``rotational_speed`` is obtained by asking the platform's own units
        registry to express the angular velocity in another unit. There is no
        factor, no 60, no 2*pi and no motor-specific function: a conversion is
        what a unit system is for, and a second authority on it would be a place
        for the two to disagree.
        """
        if not raw.succeeded:
            return {}
        angular_velocity = Quantity(
            raw.values[ANGULAR_VELOCITY_METRIC], rot.ANGULAR_VELOCITY_UNIT
        )
        return {
            ANGULAR_VELOCITY_METRIC: angular_velocity,
            ROTATIONAL_SPEED_METRIC: angular_velocity.to(rot.ROTATIONAL_SPEED_UNIT),
            CURRENT_METRIC: Quantity(raw.values[CURRENT_METRIC], CURRENT_UNIT),
            BACK_EMF_METRIC: Quantity(raw.values[BACK_EMF_METRIC], VOLTAGE_UNIT),
            ELECTROMAGNETIC_TORQUE_METRIC: Quantity(
                raw.values[ELECTROMAGNETIC_TORQUE_METRIC], rot.TORQUE_UNIT
            ),
            LOAD_TORQUE_METRIC: Quantity(
                raw.values[LOAD_TORQUE_METRIC], rot.TORQUE_UNIT
            ),
            INTERNAL_LOSS_TORQUE_METRIC: Quantity(
                raw.values[INTERNAL_LOSS_TORQUE_METRIC], rot.TORQUE_UNIT
            ),
            MECHANICAL_OUTPUT_POWER_METRIC: Quantity(
                raw.values[MECHANICAL_OUTPUT_POWER_METRIC], POWER_UNIT
            ),
            INTERNAL_LOSS_POWER_METRIC: Quantity(
                raw.values[INTERNAL_LOSS_POWER_METRIC], POWER_UNIT
            ),
            CONVERTED_POWER_METRIC: Quantity(
                raw.values[CONVERTED_POWER_METRIC], POWER_UNIT
            ),
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Three residuals, each of an equation the closed form did not evaluate.

        These are not restatements of the solve. The solve computes ``omega``
        from a quadratic root and everything else from ``omega``; the checks
        substitute the results back into the **loop KVL**, the **torque
        balance** and the **converted-power identity**, none of which the solve
        evaluated. A wrong root branch, a sign error, a mis-substituted
        resistance or an inconsistent constant pair each leave one of them
        non-zero.

        The third check is the energy trap made executable: ``E*I`` equals
        ``(tau_load + tau_loss)*omega`` **iff** ``k_e`` equals ``k_t`` in SI.
        Admission refuses an inconsistent pair before anything runs; this check
        is what proves the refusal is not the only thing standing between the
        platform and a machine that creates energy.
        """
        p: PreparedOperatingPoint = prepared.payload
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="drive_operating_point",
                        outcome=ValidationOutcome.FAIL,
                        detail="the solve did not succeed; no residual exists",
                    ),
                )
            )
        v = raw.values
        omega = v[ANGULAR_VELOCITY_METRIC]
        current = v[CURRENT_METRIC]

        kvl = abs(
            p.supply_voltage_v
            - current * p.loop_resistance_ohm
            - v[BACK_EMF_METRIC]
        )
        torque = abs(
            v[ELECTROMAGNETIC_TORQUE_METRIC]
            - v[LOAD_TORQUE_METRIC]
            - v[INTERNAL_LOSS_TORQUE_METRIC]
        )
        power = abs(
            v[CONVERTED_POWER_METRIC]
            - v[MECHANICAL_OUTPUT_POWER_METRIC]
            - v[INTERNAL_LOSS_POWER_METRIC]
        )

        def check(name: str, residual: float, scale: float, detail: str):
            tolerance = 1e-12 * max(abs(scale), 1.0)
            return ValidationCheck(
                name=name,
                outcome=(
                    ValidationOutcome.PASS
                    if residual <= tolerance
                    else ValidationOutcome.FAIL
                ),
                # Establishes no level: these verify the closed form against
                # the equations it solves. No independent reference exists and
                # nothing physical was measured.
                establishes=None,
                residual=residual,
                tolerance=tolerance,
                detail=detail,
            )

        return ValidationReport(
            checks=(
                check(
                    "loop_kvl_residual", kvl, p.supply_voltage_v,
                    f"|V - I R_loop - E| = {kvl:.3e} V",
                ),
                check(
                    "torque_balance_residual", torque,
                    v[ELECTROMAGNETIC_TORQUE_METRIC],
                    f"|tau_e - tau_load - tau_loss| = {torque:.3e} N*m",
                ),
                check(
                    "converted_power_identity", power, v[CONVERTED_POWER_METRIC],
                    f"|E I - (tau_load + tau_loss) omega| = {power:.3e} W. This "
                    f"is the energy-conservation identity and it holds only "
                    f"because k_e equals k_t in SI.",
                ),
            )
        )
