"""Rotational mechanics of an electromechanical machine: the reusable claims.

`PROPULSION0`. Five constitutive/fundamental statements about a rotating shaft
and the transduction between an electrical port and that shaft, and **nothing
else**::

    E        = k_e * omega        back-EMF
    tau_e    = k_t * I            torque production
    tau_loss = b * omega          internal viscous loss
    tau_load = k_load * omega^2   a declared mechanical load law
    tau_e    = tau_load + tau_loss    steady-speed torque balance

Why this is a domain module and not a system pack
-------------------------------------------------
Each of the five is a claim about *a machine and a shaft*, reusable by any
composition that has one. None of them mentions a wire, a circuit topology, a
thermal body, an ambient, a coupling plan or a solve order. The claim that is
topology-shaped — "the loop resistance of a single series drive across one
ideal source" — is deliberately **not** here; it lives in the system pack that
declares that loop, because it is a property of the assembly.

What is deliberately absent
---------------------------
**No inertia.** ``tau_e = tau_load + tau_loss`` is stated at ``d(omega)/dt = 0``.
An inertia term would be a capability no test in this milestone exercises, and
future capability is not evidence. :data:`ROTATIONAL_TORQUE_BALANCE_MODEL` says
so in its assumptions rather than leaving the omission to be inferred.

**No rpm.** ``rpm`` is a *unit*, not a model: the platform's units layer already
converts ``radian/second`` to ``revolutions_per_minute`` exactly, so a
conversion declared here would be a second authority on a fact the units layer
owns, and a hard-coded ``60/(2*pi)`` would be a motor function pretending to be
physics. Neither the constant 60 nor 2*pi appears anywhere in this module.

**No solver.** Nothing in this milestone evaluates these five claims
*separately*: the drive operating point solves them simultaneously with a loop
KVL, in closed form, in the system pack. That is a measured contract
observation and is recorded rather than worked around — see
:data:`ROTATIONAL_TORQUE_BALANCE_MODEL`'s note on joint realization.

**No propeller, no fluid, no blade element.**
:data:`QUADRATIC_ROTATIONAL_LOAD_MODEL` is a *mechanical load law*: a declared
torque that grows with the square of speed. It contains no aerodynamics, no
density, no advance ratio and no blade geometry, and calling it a propeller
model would be a claim this module cannot support.

The energy identity, and why both constants are still declared
--------------------------------------------------------------
Electrical conversion power ``E*I = k_e*omega*I`` must equal mechanical
converted power ``tau_e*omega = k_t*I*omega``, which holds **iff k_e and k_t
are numerically equal in SI**. That is not a coincidence to be documented; it
is a conservation law.

:class:`MachineConstants` nevertheless declares *both*, because a record that
derived one from the other could not be given an inconsistent pair, and a
consistency law that cannot be violated cannot be enforced either. The pair is
constructible and then **refused** by
:func:`require_energy_consistent_constants`, which is called at the composition
gate *and* at the record boundary where a machine is bound to a solve — never
from ``__post_init__``, because a record that could not hold a violating pair
would give the enforcement nothing to catch.

A measured limitation of universal core shapes how that check is written.
``Quantity.is_compatible_with`` compares dimensionality **strings**, and the
units backend renders the one dimension of ``volt*second/radian`` as
``[mass] * [length] ** 2 / [time] ** 2 / [current]`` and of
``newton*meter/ampere`` as ``[length] ** 2 * [mass] / [time] ** 2 / [current]``
— two spellings of one dimension that compare unequal. So ``k_e`` cannot be
converted into ``k_t``'s unit directly.

It is still not compared as two bare floats. :data:`_SI_COHERENCE_FACTOR`
obtains the conversion from the units layer by a route the defect does not
block — the **ratio** of the two units, which reduces to dimensionless — so the
check depends on no undeclared agreement between two module-level strings. The
defect is recorded as a finding about ``engcore.scientific.units.quantity``;
universal core is not edited here, and the defect is fail-closed: string
equality is strictly stronger than dimensional equality, so it produces false
refusals and never false acceptances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..scientific.capabilities import ScientificCapability
from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.problem import ModelReference
from ..scientific.ir.variables import ScientificParameter, VariableRole
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
from ..scientific.serialization import require_schema, schema_string
from ..scientific.solvers.capability import (
    CoreCapabilities,
    SolverCapability,
    SolverCapabilityId,
)
from ..scientific.units.quantity import Quantity

__all__ = [
    "ANGULAR_VELOCITY",
    "ANGULAR_VELOCITY_UNIT",
    "BACK_EMF",
    "BACK_EMF_CONSTANT",
    "BACK_EMF_CONSTANT_UNIT",
    "BACK_EMF_MODEL",
    "CURRENT",
    "ELECTROMAGNETIC_TORQUE",
    "INTERNAL_LOSS_TORQUE",
    "LOAD_COEFFICIENT",
    "LOAD_COEFFICIENT_UNIT",
    "LOAD_TORQUE",
    "MACHINE_CONSTANTS_SCHEMA",
    "MECHANICAL_OPERATING_POINT",
    "QUADRATIC_ROTATIONAL_LOAD_MODEL",
    "ROTATIONAL_LOAD_SCHEMA",
    "ROTATIONAL_SPEED_UNIT",
    "ROTATIONAL_TORQUE_BALANCE_MODEL",
    "TORQUE_CONSTANT",
    "TORQUE_CONSTANT_UNIT",
    "TORQUE_PRODUCTION_MODEL",
    "TORQUE_UNIT",
    "VISCOUS_COEFFICIENT",
    "VISCOUS_COEFFICIENT_UNIT",
    "VISCOUS_ROTATIONAL_LOSS_MODEL",
    "MachineConstants",
    "RotationalLoad",
    "ENERGY_IDENTITY_RELATIVE_TOLERANCE",
    "positive_root_of_speed_balance",
    "require_energy_consistent_constants",
    "rotational_model_registry",
    "rotational_realizations",
    "rotational_solver_capabilities",
]

# =====================================================================
# Units and names
# =====================================================================

ANGULAR_VELOCITY_UNIT = "radian / second"
#: Presentation unit only. Named here because the *unit* is what performs the
#: conversion; no model and no arithmetic in this repository converts to it.
ROTATIONAL_SPEED_UNIT = "revolutions_per_minute"
TORQUE_UNIT = "newton * meter"
CURRENT_UNIT = "ampere"
VOLTAGE_UNIT = "volt"
POWER_UNIT = "watt"
BACK_EMF_CONSTANT_UNIT = "volt * second / radian"
TORQUE_CONSTANT_UNIT = "newton * meter / ampere"
LOAD_COEFFICIENT_UNIT = "newton * meter * second ** 2 / radian ** 2"
VISCOUS_COEFFICIENT_UNIT = "newton * meter * second / radian"

ANGULAR_VELOCITY = "angular_velocity"
CURRENT = "current"
BACK_EMF = "back_emf"
ELECTROMAGNETIC_TORQUE = "electromagnetic_torque"
LOAD_TORQUE = "load_torque"
INTERNAL_LOSS_TORQUE = "internal_loss_torque"
BACK_EMF_CONSTANT = "back_emf_constant"
TORQUE_CONSTANT = "torque_constant"
LOAD_COEFFICIENT = "load_coefficient"
VISCOUS_COEFFICIENT = "viscous_coefficient"

MODEL_VERSION = "0.1.0"

MACHINE_CONSTANTS_SCHEMA = schema_string("rotational_machine_constants")
ROTATIONAL_LOAD_SCHEMA = schema_string("rotational_quadratic_load")

#: What a backend must be able to state, not how it computes it.
MECHANICAL_OPERATING_POINT = ScientificCapability.parse(
    "mechanical:rotational_operating_point"
)

#: What each elementary claim *provides*, so a realization can say what it
#: satisfies rather than being trusted to.
PROVIDES_BACK_EMF = ScientificCapability.parse("mechanical:back_emf")
PROVIDES_ELECTROMAGNETIC_TORQUE = ScientificCapability.parse(
    "mechanical:electromagnetic_torque"
)
PROVIDES_INTERNAL_LOSS_TORQUE = ScientificCapability.parse(
    "mechanical:internal_loss_torque"
)
PROVIDES_LOAD_TORQUE = ScientificCapability.parse("mechanical:load_torque")


# =====================================================================
# The five claims
# =====================================================================

_MACHINE_ASSUMPTIONS = (
    "an idealised DC-equivalent machine: one electrical port, one shaft, and "
    "a single lumped transduction constant",
    "the machine constant is independent of current, speed, temperature and "
    "rotor position; saturation, commutation, cogging and armature reaction "
    "are not represented",
    "in SI the numerical value of k_e in V*s/rad equals that of k_t in "
    "N*m/A; this is required by energy conservation and is enforced at "
    "admission, not assumed",
)

_ANGULAR_VELOCITY_INPUT = ModelInputSpec(
    name=ANGULAR_VELOCITY,
    source_kind=InputSourceKind.VARIABLE,
    unit_exemplar=ANGULAR_VELOCITY_UNIT,
    role=VariableRole.STATE,
    description="Shaft angular velocity; the mechanical state coordinate.",
)


BACK_EMF_MODEL = ScientificModelDefinition(
    model_id="mechanical.rotational.back_emf",
    version=MODEL_VERSION,
    name="Back-EMF of a rotating electromechanical machine",
    domain="mechanical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "The voltage a rotating machine develops against its own supply: "
        "E = k_e * omega."
    ),
    inputs=(
        ModelInputSpec(
            name=BACK_EMF_CONSTANT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=BACK_EMF_CONSTANT_UNIT,
            description="Machine back-EMF constant; strictly positive.",
        ),
        _ANGULAR_VELOCITY_INPUT,
    ),
    outputs=(
        ModelOutputSpec(
            metric=BACK_EMF,
            unit_exemplar=VOLTAGE_UNIT,
            description="Voltage developed by the rotating machine.",
        ),
    ),
    assumptions=_MACHINE_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=BACK_EMF_CONSTANT,
                minimum=Quantity(0.0, BACK_EMF_CONSTANT_UNIT),
                minimum_inclusive=False,
                description="A machine with no flux linkage develops no EMF.",
            ),
        ),
        description="What is universally true of the linear transduction form.",
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


TORQUE_PRODUCTION_MODEL = ScientificModelDefinition(
    model_id="mechanical.rotational.torque_production",
    version=MODEL_VERSION,
    name="Electromagnetic torque of an electromechanical machine",
    domain="mechanical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "The shaft torque a machine develops from its winding current: "
        "tau_e = k_t * I."
    ),
    inputs=(
        ModelInputSpec(
            name=TORQUE_CONSTANT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TORQUE_CONSTANT_UNIT,
            description="Machine torque constant; strictly positive.",
        ),
        ModelInputSpec(
            name=CURRENT,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=CURRENT_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Winding current, imposed from outside this claim. Where it "
                "comes from is not part of what this model states."
            ),
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=ELECTROMAGNETIC_TORQUE,
            unit_exemplar=TORQUE_UNIT,
            description="Torque developed on the shaft.",
        ),
    ),
    assumptions=_MACHINE_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=TORQUE_CONSTANT,
                minimum=Quantity(0.0, TORQUE_CONSTANT_UNIT),
                minimum_inclusive=False,
                description="A machine with no flux linkage develops no torque.",
            ),
        ),
        description="What is universally true of the linear transduction form.",
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


VISCOUS_ROTATIONAL_LOSS_MODEL = ScientificModelDefinition(
    model_id="mechanical.rotational.viscous_loss",
    version=MODEL_VERSION,
    name="Viscous internal loss torque of a rotating shaft",
    domain="mechanical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Speed-proportional internal resisting torque: tau_loss = b * omega."
    ),
    inputs=(
        ModelInputSpec(
            name=VISCOUS_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=VISCOUS_COEFFICIENT_UNIT,
            description="Viscous loss coefficient; non-negative.",
        ),
        _ANGULAR_VELOCITY_INPUT,
    ),
    outputs=(
        ModelOutputSpec(
            metric=INTERNAL_LOSS_TORQUE,
            unit_exemplar=TORQUE_UNIT,
            description="Internal resisting torque at this speed.",
        ),
    ),
    assumptions=(
        "one lumped speed-proportional loss channel",
        "no Coulomb (speed-independent) friction term is represented",
        "iron loss, windage and bearing loss are NOT separately represented; "
        "whatever of them a caller intends is folded into this one coefficient "
        "or is absent",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=VISCOUS_COEFFICIENT,
                minimum=Quantity(0.0, VISCOUS_COEFFICIENT_UNIT),
                minimum_inclusive=True,
                description=(
                    "Zero is admissible and means a lossless shaft; negative "
                    "would be a shaft that drives itself."
                ),
            ),
        ),
        description="What is universally true of the linear loss form.",
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


QUADRATIC_ROTATIONAL_LOAD_MODEL = ScientificModelDefinition(
    model_id="mechanical.rotational.quadratic_load",
    version=MODEL_VERSION,
    name="Quadratic-in-speed mechanical load law",
    domain="mechanical",
    # APPROXIMATION, and deliberately not EMPIRICAL_CORRELATION: nothing here
    # was fitted to data, and nothing here derives the exponent from a physical
    # argument. It is a declared load law and is typed as one.
    model_type=ModelType.APPROXIMATION,
    description=(
        "A declared mechanical load whose resisting torque grows with the "
        "square of shaft speed: tau_load = k_load * omega^2."
    ),
    inputs=(
        ModelInputSpec(
            name=LOAD_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=LOAD_COEFFICIENT_UNIT,
            description="Quadratic load coefficient; strictly positive.",
        ),
        _ANGULAR_VELOCITY_INPUT,
    ),
    outputs=(
        ModelOutputSpec(
            metric=LOAD_TORQUE,
            unit_exemplar=TORQUE_UNIT,
            description="Load torque demanded at this speed.",
        ),
    ),
    assumptions=(
        "the load's resisting torque is proportional to the square of speed "
        "over the whole speed range considered",
        "this is a MECHANICAL LOAD LAW and not a propeller model: it carries "
        "no fluid density, no advance ratio, no blade geometry and no "
        "blade-element content, and it must not be described as one",
        "the load is passive: it absorbs shaft power and returns none",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=LOAD_COEFFICIENT,
                minimum=Quantity(0.0, LOAD_COEFFICIENT_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive. A zero coefficient is not a degenerate "
                    "case to branch on: it removes the quadratic term, and a "
                    "consumer that wants a linear load wants a different model."
                ),
            ),
        ),
        description="What is universally true of the quadratic form.",
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


ROTATIONAL_TORQUE_BALANCE_MODEL = ScientificModelDefinition(
    model_id="mechanical.rotational.steady_torque_balance",
    version=MODEL_VERSION,
    name="Steady-speed rotational torque balance",
    domain="mechanical",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Newton's second law for rotation at zero angular acceleration: the "
        "developed torque equals the sum of the load torque and the internal "
        "loss torque, tau_e = tau_load + tau_loss."
    ),
    inputs=(
        ModelInputSpec(
            name=ELECTROMAGNETIC_TORQUE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TORQUE_UNIT,
            role=VariableRole.CONTROL,
            description="Torque developed on the shaft.",
        ),
        ModelInputSpec(
            name=LOAD_TORQUE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TORQUE_UNIT,
            role=VariableRole.CONTROL,
            description="Torque demanded by the load.",
        ),
        ModelInputSpec(
            name=INTERNAL_LOSS_TORQUE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TORQUE_UNIT,
            role=VariableRole.CONTROL,
            description="Torque absorbed internally.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=ANGULAR_VELOCITY,
            unit_exemplar=ANGULAR_VELOCITY_UNIT,
            description=(
                "The speed at which the three torques balance. It is the "
                "unknown of this relation, not an input to it."
            ),
        ),
    ),
    assumptions=(
        "d(omega)/dt = 0: this is an operating point, not a transient",
        "NO INERTIA is represented. A rotational inertia J would make this a "
        "different relation with a different unknown, and no case in this "
        "milestone requires one; future capability is not evidence",
        "one shaft, one load path, one loss path; no gearbox, no compliance, "
        "no backlash and no torsional dynamics",
    ),
    validity=ValidityDomain(
        conditions=(),
        description=(
            "A balance carries no parameter of its own, so it carries no "
            "range condition of its own. The conditions that matter belong to "
            "the four claims whose outputs it balances, and each of those "
            "records states its own."
        ),
    ),
    required_capabilities=frozenset(
        {CoreCapabilities.ALGEBRAIC.name, MECHANICAL_OPERATING_POINT.name}
    ),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


_ROTATIONAL_MODELS = (
    BACK_EMF_MODEL,
    TORQUE_PRODUCTION_MODEL,
    VISCOUS_ROTATIONAL_LOSS_MODEL,
    QUADRATIC_ROTATIONAL_LOAD_MODEL,
    ROTATIONAL_TORQUE_BALANCE_MODEL,
)


def _direct_realization(
    model: ScientificModelDefinition,
    suffix: str,
    description: str,
    provides: ScientificCapability,
) -> ModelRealizationDefinition:
    """One realization per elementary claim: evaluate the relation directly.

    Every one of them is a single algebraic expression, so the realization
    record adds no method choice — and that is exactly why it is honest to
    write it down: it says "no approximation was made between the claim and
    the number", which is a real statement about how the claim was discharged.
    """
    return ModelRealizationDefinition(
        realization_id=f"{model.model_id}.{suffix}",
        version="0.1.0",
        model=ModelReference(model.model_id, model.version),
        formulation=ModelFormulation.ALGEBRAIC,
        name=f"Direct evaluation of {model.name.lower()}",
        description=description,
        provided_capabilities=frozenset({provides}),
        required_solver_capabilities=frozenset(
            {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
        ),
        assumptions=(
            "the relation is evaluated directly; no discretization, no "
            "iteration and no approximation is introduced between the claim "
            "and the number",
        ),
        implementation=ImplementationReference(
            implementation_id="engcore.domains.mechanical_rotational",
            version="0.1.0",
            reference="single algebraic expression; see the model description",
        ),
    )


BACK_EMF_REALIZATION = _direct_realization(
    BACK_EMF_MODEL,
    "direct",
    "E = k_e * omega, evaluated as written.",
    PROVIDES_BACK_EMF,
)
TORQUE_PRODUCTION_REALIZATION = _direct_realization(
    TORQUE_PRODUCTION_MODEL,
    "direct",
    "tau_e = k_t * I, evaluated as written.",
    PROVIDES_ELECTROMAGNETIC_TORQUE,
)
VISCOUS_ROTATIONAL_LOSS_REALIZATION = _direct_realization(
    VISCOUS_ROTATIONAL_LOSS_MODEL,
    "direct",
    "tau_loss = b * omega, evaluated as written.",
    PROVIDES_INTERNAL_LOSS_TORQUE,
)
QUADRATIC_ROTATIONAL_LOAD_REALIZATION = _direct_realization(
    QUADRATIC_ROTATIONAL_LOAD_MODEL,
    "direct",
    "tau_load = k_load * omega^2, evaluated as written.",
    PROVIDES_LOAD_TORQUE,
)

#: There is deliberately **no** realization of
#: :data:`ROTATIONAL_TORQUE_BALANCE_MODEL` here, and the absence is the finding.
#:
#: The balance is not evaluated; it is *solved*, and it cannot be solved alone —
#: its unknown ``omega`` appears in three of the four claims it balances and in
#: the electrical loop that supplies the current. What discharges it is a
#: simultaneous closed-form solution of all five claims together with a loop
#: KVL, and ``ModelRealizationDefinition.model`` is a **single**
#: ``ModelReference``, so no realization record can state a joint discharge.
#: That gap is already recorded once in the master context; this milestone is
#: its second independent consumer. Writing a realization here that named only
#: the balance would claim an attribution that is false.
_JOINT_REALIZATION_GAP = (
    "no ModelRealizationDefinition can state that one closed form discharges "
    "several model records jointly; the balance is therefore realized in the "
    "composition that owns the loop, and its binding there carries "
    "realization=None"
)

_ROTATIONAL_REALIZATIONS = (
    BACK_EMF_REALIZATION,
    TORQUE_PRODUCTION_REALIZATION,
    VISCOUS_ROTATIONAL_LOSS_REALIZATION,
    QUADRATIC_ROTATIONAL_LOAD_REALIZATION,
)


def rotational_model_registry() -> ModelRegistry:
    """A fresh registry. No global singleton exists."""
    return ModelRegistry(_ROTATIONAL_MODELS)


def rotational_realizations() -> RealizationRegistry:
    """A fresh registry. No global singleton exists."""
    return RealizationRegistry(_ROTATIONAL_REALIZATIONS)


def rotational_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset(
        {
            CoreCapabilities.ALGEBRAIC,
            SolverCapability(
                MECHANICAL_OPERATING_POINT.name,
                "Solve a steady rotational operating point",
            ),
        }
    )


# =====================================================================
# Declarations
# =====================================================================

def _positive(value: Any, unit: str, label: str, *, allow_zero: bool = False):
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(f"{label} must be a Quantity")
    value.require_compatible(unit, context=label)
    magnitude = value.magnitude_in(unit)
    if magnitude < 0.0 or (magnitude == 0.0 and not allow_zero):
        bound = "non-negative" if allow_zero else "strictly positive"
        raise InvalidScientificProblem(
            f"{label} must be {bound}, got {value}"
        )
    return magnitude


@dataclass(frozen=True)
class MachineConstants:
    """The transduction constants of one machine. **Science only.**

    Both are declared. Deriving one from the other would make the energy
    identity unfalsifiable — a law that cannot be violated cannot be enforced —
    so the pair is stated and then **refused** if it is inconsistent.

    The record carries no resistance, no inductance, no geometry, no thermal
    property and no rated point. A winding resistance is a property of a
    conductor, and this platform already has a record for that.
    """

    torque_constant: Quantity
    back_emf_constant: Quantity
    source: str

    def __post_init__(self) -> None:
        source = str(self.source).strip()
        if not source:
            raise InvalidScientificProblem(
                "machine constants require a non-empty provenance source; a "
                "constant set with no stated origin is not a declaration"
            )
        object.__setattr__(self, "source", source)
        _positive(
            self.torque_constant, TORQUE_CONSTANT_UNIT, "torque_constant"
        )
        _positive(
            self.back_emf_constant, BACK_EMF_CONSTANT_UNIT, "back_emf_constant"
        )

    @property
    def k_t_si(self) -> float:
        return self.torque_constant.magnitude_in(TORQUE_CONSTANT_UNIT)

    @property
    def k_e_si(self) -> float:
        return self.back_emf_constant.magnitude_in(BACK_EMF_CONSTANT_UNIT)

    def machine_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=TORQUE_CONSTANT,
                value=self.torque_constant,
                description=f"Declared torque constant. Source: {self.source}",
            ),
            ScientificParameter(
                name=BACK_EMF_CONSTANT,
                value=self.back_emf_constant,
                description=f"Declared back-EMF constant. Source: {self.source}",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MACHINE_CONSTANTS_SCHEMA,
            "torque_constant": self.torque_constant.to_dict(),
            "back_emf_constant": self.back_emf_constant.to_dict(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MachineConstants":
        require_schema(payload, MACHINE_CONSTANTS_SCHEMA)
        return cls(
            torque_constant=Quantity.from_dict(payload["torque_constant"]),
            back_emf_constant=Quantity.from_dict(payload["back_emf_constant"]),
            source=payload["source"],
        )


#: Relative tolerance on the SI identity ``k_e == k_t``. Tight on purpose: this
#: is not a measurement agreeing with a model, it is one number written twice.
ENERGY_IDENTITY_RELATIVE_TOLERANCE = 1e-12

#: How many :data:`TORQUE_CONSTANT_UNIT` there are in one
#: :data:`BACK_EMF_CONSTANT_UNIT`, obtained from the units layer itself.
#:
#: A first version of the check below compared ``k_e`` and ``k_t`` as bare SI
#: magnitudes and was correct *only because* the two declared unit strings
#: happen to be SI-coherent — an undeclared, unchecked dependency between two
#: module-level constants. `architecture-falsifier` produced the counterexample:
#: respell :data:`TORQUE_CONSTANT_UNIT` as ``millinewton * meter / ampere`` and
#: the conservation law is wrong by 1000x while every test still passes.
#:
#: This factor removes the assumption instead of documenting it. Note *how* it
#: is obtained: the two units cannot be compared directly, because
#: ``Quantity.is_compatible_with`` compares dimensionality strings and the
#: backend spells this one dimension two ways (see the module docstring). Their
#: **ratio**, however, reduces to dimensionless in one spelling, so the units
#: layer answers the question through a route its own defect does not block.
#: For the units as declared the factor is exactly 1.0, so nothing about the
#: check's behaviour changes today. What changes is precisely this and no more:
#: the **check** no longer depends on an unstated agreement between two module
#: constants. The closed form in the system pack still multiplies ``k_t`` and
#: ``k_e`` as bare SI floats, so respelling either unit would still make that
#: arithmetic wrong — it would simply surface as a raised energy-reconciliation
#: failure instead of as a silently passing check. Making the arithmetic itself
#: unit-string-independent would be speculative hardening against an edit
#: nobody has made, and is deliberately not done.
_SI_COHERENCE_FACTOR = (
    Quantity(1.0, BACK_EMF_CONSTANT_UNIT) / Quantity(1.0, TORQUE_CONSTANT_UNIT)
).magnitude_in("dimensionless")


def require_energy_consistent_constants(constants: MachineConstants) -> None:
    """Refuse a machine that would create or destroy energy. **Enforcement.**

    ``E*I = k_e*omega*I`` is the electrical power converted; ``tau_e*omega =
    k_t*I*omega`` is the mechanical power converted. They are the same power,
    so the two constants are the same number in SI. A pair that disagrees
    describes a machine that manufactures energy from nothing, or annihilates
    it, and such a machine is **refused, not reported** — reporting it would
    put a number that violates conservation into a record that reads as
    attributable.

    ``k_e`` is expressed in the torque constant's own declared unit through
    :data:`_SI_COHERENCE_FACTOR`, so the comparison assumes nothing about how
    either unit is spelled. See the module docstring for the measured
    units-layer limitation that makes a ``require_compatible`` between the two
    impossible today, and for what this check does and does not buy.
    """
    if not isinstance(constants, MachineConstants):
        raise InvalidScientificProblem(
            "require_energy_consistent_constants expects a MachineConstants"
        )
    # k_e expressed in the torque constant's own declared unit, so the
    # comparison never assumes the two unit strings are SI-coherent.
    k_t = constants.k_t_si
    k_e = constants.k_e_si * _SI_COHERENCE_FACTOR
    scale = max(abs(k_t), abs(k_e))
    if abs(k_t - k_e) > ENERGY_IDENTITY_RELATIVE_TOLERANCE * scale:
        raise InvalidScientificProblem(
            f"machine constants violate energy conservation: k_e = "
            f"{constants.k_e_si!r} {BACK_EMF_CONSTANT_UNIT} and k_t = "
            f"{k_t!r} {TORQUE_CONSTANT_UNIT} must be the same number once "
            f"expressed in one unit, "
            f"because the converted electrical power k_e*omega*I and the "
            f"converted mechanical power k_t*I*omega are the same power. The "
            f"relative difference is "
            f"{abs(k_t - k_e) / scale:.3e}, above "
            f"{ENERGY_IDENTITY_RELATIVE_TOLERANCE:.0e}. A machine that creates "
            f"energy is refused, not reported. Source: {constants.source!r}"
        )


@dataclass(frozen=True)
class RotationalLoad:
    """A quadratic mechanical load plus the shaft's internal viscous loss.

    Two coefficients, two claims, one record — and the record is honest about
    which is which: ``load_coefficient`` is *what the machine is driving* and
    its power leaves the system as useful output; ``viscous_coefficient`` is
    *what the machine wastes* and its power stays as heat. Folding them into
    one number would make the output power and the loss power the same
    quantity, which is the accounting error this milestone exists to refuse.
    """

    load_id: str
    load_coefficient: Quantity
    viscous_coefficient: Quantity
    source: str

    def __post_init__(self) -> None:
        load_id = str(self.load_id).strip()
        if not load_id:
            raise InvalidScientificProblem("a rotational load requires a load_id")
        object.__setattr__(self, "load_id", load_id)
        source = str(self.source).strip()
        if not source:
            raise InvalidScientificProblem(
                f"load {load_id!r} requires a non-empty provenance source"
            )
        object.__setattr__(self, "source", source)
        _positive(
            self.load_coefficient, LOAD_COEFFICIENT_UNIT,
            f"load {load_id!r} load_coefficient",
        )
        _positive(
            self.viscous_coefficient, VISCOUS_COEFFICIENT_UNIT,
            f"load {load_id!r} viscous_coefficient", allow_zero=True,
        )

    @property
    def k_load_si(self) -> float:
        return self.load_coefficient.magnitude_in(LOAD_COEFFICIENT_UNIT)

    @property
    def b_si(self) -> float:
        return self.viscous_coefficient.magnitude_in(VISCOUS_COEFFICIENT_UNIT)

    def load_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=LOAD_COEFFICIENT,
                value=self.load_coefficient,
                description=(
                    f"Declared quadratic load coefficient. Source: {self.source}"
                ),
            ),
            ScientificParameter(
                name=VISCOUS_COEFFICIENT,
                value=self.viscous_coefficient,
                description=(
                    f"Declared viscous loss coefficient. Source: {self.source}"
                ),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ROTATIONAL_LOAD_SCHEMA,
            "load_id": self.load_id,
            "load_coefficient": self.load_coefficient.to_dict(),
            "viscous_coefficient": self.viscous_coefficient.to_dict(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RotationalLoad":
        require_schema(payload, ROTATIONAL_LOAD_SCHEMA)
        return cls(
            load_id=payload["load_id"],
            load_coefficient=Quantity.from_dict(payload["load_coefficient"]),
            viscous_coefficient=Quantity.from_dict(payload["viscous_coefficient"]),
            source=payload["source"],
        )


def positive_root_of_speed_balance(
    *, quadratic: float, linear: float, constant: float
) -> float:
    """The unique positive root of ``quadratic*w^2 + linear*w - constant = 0``.

    Stated as its own function, in SI floats, because it is the one place the
    *branch* of the quadratic is chosen and that choice must be readable rather
    than buried in an expression.

    With ``quadratic > 0``, ``linear >= 0`` and ``constant > 0`` the product of
    the roots is ``-constant/quadratic < 0``, so exactly one root is positive
    and the ``+sqrt`` branch is it. A caller that hands in a non-positive
    ``quadratic`` is refused rather than routed to a linear form: a degenerate
    coefficient is a different model, not a second code path.
    """
    if not quadratic > 0.0:
        raise InvalidScientificProblem(
            f"the quadratic coefficient must be strictly positive, got "
            f"{quadratic!r}; a vanishing coefficient degenerates the balance "
            f"to a linear relation, which is a different model rather than a "
            f"branch of this one"
        )
    if linear < 0.0:
        raise InvalidScientificProblem(
            f"the linear coefficient must be non-negative, got {linear!r}; a "
            f"negative one describes a shaft that accelerates itself"
        )
    if not constant > 0.0:
        raise InvalidScientificProblem(
            f"the driving term must be strictly positive, got {constant!r}; a "
            f"machine with no driving torque has no positive operating speed"
        )
    discriminant = linear * linear + 4.0 * quadratic * constant
    return (-linear + discriminant ** 0.5) / (2.0 * quadratic)
