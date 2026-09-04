"""Conductor materials: named property sets, geometry, and R = rho(T)*L/A.

`COMPOSITE-SYSTEM0`. This module answers one narrow question that the existing
:mod:`engcore.domains.electrical.material` cannot: **what is this conductor
made of, and how big is it?**

Why this is not a duplicate of ``material.py``
----------------------------------------------
``material.py`` states ``R(T) = R_ref (1 + alpha (T - T_ref))``. It is
parameterised by a *reference resistance*, so a caller supplies a number and
neither the material nor the geometry exists anywhere in the record. Two
consequences were measured before this module was written:

* a non-positive cross-section cannot be refused by any contract — and a
  negative length with a negative area yields an **admitted** positive
  resistance;
* ``rho_ref * L / A`` computed in caller Python is an unmodelled scientific
  claim with no model, no realization, no solver and no ``ExecutionBinding``.

So the gap is real. What closes it is **not** a new universal contract.

What is deliberately NOT created here
-------------------------------------
No ``ComponentInstance``, no ``Port``, no ``Connector``, no
``SystemDefinition``, no ``MaterialBinding``, no universal
``Material``/``MaterialState``/``MaterialProperty`` hierarchy, no registry in
universal core, and nothing resembling ``ScientificProblem`` or
``QuantityDependency``. Every one of those was attempted against the existing
contracts first and none of them was forced: ``CoupledStage`` already carries
instance identity at arity 2, ``DCCircuit`` already carries typed topology,
``QuantityDependency`` already carries data dependency with direction and
dimension, and ``FixedPointCouplingPlan`` already *refuses* fan-in rather than
inventing a combination rule. Recording that they are not forced is the result.

What is created is what a property that depends on a material and a geometry
actually needs, stated with the contracts that already exist — exactly the
argument ``material.py``'s own docstring makes, applied a second time:

======================================  ====================================
``ScientificModelDefinition``           the constitutive claim
``ModelInputSpec``                      the typed property requirement
``ModelRealizationDefinition``          how the claim is computed
``ScientificParameter``/``Variable``    where rho, L, A and T live
``CategoricalValue``                    material identity, typed, not a string
``ProvenanceRecord.bindings``           which realization computed what
======================================  ====================================

One model per *functional form*, never one per material
-------------------------------------------------------
There are two resistivity models here, and the axis that separates them is the
**functional form**, not the material name:

* :data:`LINEAR_RESISTIVITY_MODEL`     ``rho = rho_ref (1 + a dT)``
* :data:`QUADRATIC_RESISTIVITY_MODEL`  ``rho = rho_ref (1 + a dT + b dT^2)``

Copper and aluminium are two *parameter sets of one model*; linear and
quadratic are two *models*. A model per material was designed and rejected: it
would have made ``(model_id, version)`` — the key ``ModelRegistry`` and
``ExecutionBinding`` are built on — a function of a mutable data table, so a
data-only correction to a catalogue entry would silently change what an
already-stored provenance record claims, and the only route from a stored
number back to its material would be to *parse characters out of an
identifier*. It would also have made a stateless ``supports()`` impossible for
a material constructed outside the catalogue.

Where a material's applicability range lives, and why it is not on the model
---------------------------------------------------------------------------
``ValidityDomain`` conditions are fixed ``Quantity`` bounds on the **model**
record, so one shared model structurally cannot carry three different
per-material temperature ranges. The range therefore lives on the material
record, with **exactly one authority**, and is assessed by building a
``ValidityDomain`` from that record at assessment time — inside the existing
contract, minting no model identity. This is a measured contract observation,
recorded rather than worked around.

What the models' own validity domains keep is only what is universally true of
the form: a strictly positive reference resistivity, and strictly positive
length and area. Note what is *absent* from
:data:`GEOMETRIC_RESISTANCE_MODEL`'s domain: ``resistivity > 0``. It is a
solver admissibility check instead, because
:meth:`ScientificProblem.validity_context` is built from **parameters** and
``resistivity`` arrives as a **variable**, so a validity condition on it would
be permanently ``UNKNOWN`` and would make every conductor unassessable. Same
asymmetry ``assess_resistance_validity`` already records for ``temperature``.

Promotion trigger, stated so it is not discovered by accident
-------------------------------------------------------------
This record is pack-local on purpose. **The first time a non-electrical domain
needs a property of the same named material** — the moment a thermal pack wants
``rho_m c_p V`` for the same copper instead of a lumped ``heat_capacity`` — this
record is in the wrong package, because the only two moves available at that
moment are a domain-to-domain import and a duplicate, and both are architecture
findings. Nothing in this milestone forces it, so nothing here is promoted.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Mapping

from ...scientific.capabilities import ScientificCapability
from ...scientific.errors import InvalidScientificProblem, ScientificCoreError
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.ir.values import CategoricalValue
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
    ValidityAssessment,
    ValidityDomain,
    ValidityStatus,
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
from ...scientific.serialization import require_schema, schema_string
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
    "AREA",
    "AREA_UNIT",
    "CROSS_SECTIONAL_AREA",
    "GEOMETRIC_RESISTANCE_MODEL",
    "GEOMETRIC_RESISTANCE_REALIZATION",
    "GEOMETRIC_RESISTANCE_SOLVER_ID",
    "LENGTH",
    "LENGTH_UNIT",
    "LINEAR_RESISTIVITY_MODEL",
    "LINEAR_RESISTIVITY_REALIZATION",
    "LINEAR_MATERIAL_SCHEMA",
    "MATERIAL",
    "MATERIAL_CATALOGUE",
    "MATERIAL_CONDUCTOR_SCHEMA",
    "QUADRATIC_RESISTIVITY_MODEL",
    "QUADRATIC_RESISTIVITY_REALIZATION",
    "QUADRATIC_MATERIAL_SCHEMA",
    "REFERENCE_RESISTIVITY",
    "REFERENCE_TEMPERATURE",
    "RESISTANCE_FROM_GEOMETRY",
    "RESISTANCE_METRIC",
    "RESISTANCE_UNIT",
    "RESISTIVITY_METRIC",
    "RESISTIVITY_UNIT",
    "SECOND_ORDER_COEFFICIENT",
    "TEMPERATURE",
    "TEMPERATURE_COEFFICIENT",
    "TEMPERATURE_DEPENDENT_RESISTIVITY",
    "TEMPERATURE_UNIT",
    "ConductorMaterial",
    "GeometricResistanceSolver",
    "LinearResistivityMaterial",
    "LinearResistivitySolver",
    "MaterialConductor",
    "QuadraticResistivityMaterial",
    "QuadraticResistivitySolver",
    "admit_conductor",
    "assess_conductor_geometry",
    "assess_material_applicability",
    "build_geometric_resistance_problem",
    "build_resistivity_problem",
    "conductor_material_registry",
    "conductor_material_realizations",
    "known_material_names",
    "material_from_dict",
    "resistivity_solver_for",
    "resolve_material",
]

# --- units -------------------------------------------------------------------
RESISTIVITY_UNIT = "ohm * meter"
RESISTANCE_UNIT = "ohm"
TEMPERATURE_UNIT = "kelvin"
LENGTH_UNIT = "meter"
AREA_UNIT = "meter ** 2"
TCR_UNIT = "1 / kelvin"
TCR2_UNIT = "1 / kelvin ** 2"

# --- quantity names ----------------------------------------------------------
REFERENCE_RESISTIVITY = "reference_resistivity"
TEMPERATURE_COEFFICIENT = "temperature_coefficient"
SECOND_ORDER_COEFFICIENT = "second_order_coefficient"
REFERENCE_TEMPERATURE = "reference_temperature"
TEMPERATURE = "temperature"
MATERIAL = "material"
LENGTH = "length"
CROSS_SECTIONAL_AREA = "cross_sectional_area"
AREA = CROSS_SECTIONAL_AREA

RESISTIVITY_METRIC = "resistivity"
RESISTANCE_METRIC = "resistance"

MODEL_VERSION = "0.1.0"

# --- capabilities ------------------------------------------------------------

#: What the resistivity models provide. A *new* capability, deliberately not
#: ``electrical:temperature_dependent_resistance``: a resistivity is not a
#: resistance, and claiming the second would be untrue of a record that never
#: sees a geometry.
TEMPERATURE_DEPENDENT_RESISTIVITY = ScientificCapability.parse(
    "electrical:temperature_dependent_resistivity"
)

#: What the geometric model provides. Also new, and also deliberately narrow:
#: ``R = rho L / A`` has **no** temperature dependence of its own. Declaring
#: ``electrical:temperature_dependent_resistance`` here would hand
#: ``RealizationRegistry.providing()`` — a real consumer that filters on
#: exactly this field and does not rank — a realization that will happily
#: compute a temperature-*independent* resistance from a constant resistivity,
#: with no record able to notice. A prior milestone already had to repair one
#: untruthful shared capability for that reason; this one is truthful by
#: construction.
RESISTANCE_FROM_GEOMETRY = ScientificCapability.parse(
    "electrical:resistance_from_geometry"
)

#: A real scientific dependency, declared by identifier and never by import:
#: no thermal module is imported anywhere in this file.
REQUIRED_BODY_TEMPERATURE = ScientificCapability.parse("thermal:body_temperature")


# =====================================================================
# The material declaration
# =====================================================================

LINEAR_MATERIAL_SCHEMA = schema_string("linear_resistivity_material")
QUADRATIC_MATERIAL_SCHEMA = schema_string("quadratic_resistivity_material")
MATERIAL_CONDUCTOR_SCHEMA = schema_string("material_conductor")


def _require(value: Any, unit: str, label: str) -> Quantity:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(
            f"{label} must be a Quantity carrying {unit!r}, got "
            f"{type(value).__name__} — a bare number is not a declaration"
        )
    value.require_compatible(unit, context=label)
    return value


def _require_positive(value: Any, unit: str, label: str) -> Quantity:
    quantity = _require(value, unit, label)
    if quantity.magnitude_in(unit) <= 0.0:
        raise InvalidScientificProblem(
            f"{label} must be strictly positive, got {quantity}"
        )
    return quantity


@dataclass(frozen=True)
class ConductorMaterial:
    """A named conductor material: **science only, never execution.**

    It declares what it is (a reference resistivity at a reference
    temperature), the temperature range over which its property set is
    declared to hold, and where the numbers came from. It exposes the
    :class:`ScientificModelDefinition` and
    :class:`ModelRealizationDefinition` of its own constitutive claim, and the
    :class:`ScientificParameter`\\ s that claim needs.

    It exposes **no solver**, no tolerance, no backend and no evaluation
    method. Mapping a declared realization onto something that executes it is
    the pack's job (:func:`resistivity_solver_for`), not the record's — a
    declaration that named a solver would have made changing an evaluator into
    a change of material identity.

    It also carries **no temperature**. A temperature is a *state*, and
    freezing one into a material declaration is the configuration/state
    conflation this lineage of milestones exists to keep apart.

    ``minimum_temperature``/``maximum_temperature`` are this material's own
    validated applicability range and are the **single** authority on it. They
    are deliberately not copied into any model's ``ValidityDomain``; see the
    module docstring.
    """

    name: str
    reference_resistivity: Quantity
    reference_temperature: Quantity
    minimum_temperature: Quantity
    maximum_temperature: Quantity
    source: str

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise InvalidScientificProblem("a material requires a name")
        object.__setattr__(self, "name", name)

        source = str(self.source).strip()
        if not source:
            raise InvalidScientificProblem(
                f"material {name!r} requires a non-empty provenance source; a "
                f"property set with no stated origin is not a declaration"
            )
        object.__setattr__(self, "source", source)

        _require_positive(
            self.reference_resistivity, RESISTIVITY_UNIT,
            f"material {name!r} reference_resistivity",
        )
        for label in (
            "reference_temperature", "minimum_temperature", "maximum_temperature",
        ):
            _require_positive(
                getattr(self, label), TEMPERATURE_UNIT, f"material {name!r} {label}"
            )
        low = self.minimum_temperature.magnitude_in(TEMPERATURE_UNIT)
        high = self.maximum_temperature.magnitude_in(TEMPERATURE_UNIT)
        if high <= low:
            raise InvalidScientificProblem(
                f"material {name!r} declares an empty applicability range "
                f"[{self.minimum_temperature}, {self.maximum_temperature}]"
            )
        reference = self.reference_temperature.magnitude_in(TEMPERATURE_UNIT)
        if not low <= reference <= high:
            raise InvalidScientificProblem(
                f"material {name!r} anchors its property set at "
                f"{self.reference_temperature}, which lies outside the range "
                f"it declares the set valid over "
                f"[{self.minimum_temperature}, {self.maximum_temperature}]"
            )

    # ---- accessors -----------------------------------------------------
    @property
    def rho_ref_ohm_m(self) -> float:
        return self.reference_resistivity.magnitude_in(RESISTIVITY_UNIT)

    @property
    def t_ref_k(self) -> float:
        return self.reference_temperature.magnitude_in(TEMPERATURE_UNIT)

    # ---- the scientific claim this material makes ----------------------
    def resistivity_model(self) -> ScientificModelDefinition:
        raise NotImplementedError(
            "ConductorMaterial is a base declaration; use a concrete "
            "functional form such as LinearResistivityMaterial"
        )

    def resistivity_realization(self) -> ModelRealizationDefinition:
        raise NotImplementedError(
            "ConductorMaterial is a base declaration; use a concrete "
            "functional form such as LinearResistivityMaterial"
        )

    def resistivity_parameters(self) -> tuple[ScientificParameter, ...]:
        raise NotImplementedError(
            "ConductorMaterial is a base declaration; use a concrete "
            "functional form such as LinearResistivityMaterial"
        )

    def applicability(self) -> ValidityDomain:
        """This material's own range, as a domain the existing contract reads.

        Constructed here rather than stored on a model, so that the range has
        exactly one authority — the record you are holding.
        """
        return ValidityDomain(
            conditions=(
                RangeCondition(
                    name=TEMPERATURE,
                    minimum=self.minimum_temperature,
                    maximum=self.maximum_temperature,
                    description=(
                        f"Range over which {self.name!r}'s declared property "
                        f"set is stated to hold. Source: {self.source}"
                    ),
                ),
            ),
            description=f"Declared applicability of material {self.name!r}.",
        )

    # ---- serialization -------------------------------------------------
    def _common_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "reference_resistivity": self.reference_resistivity.to_dict(),
            "reference_temperature": self.reference_temperature.to_dict(),
            "minimum_temperature": self.minimum_temperature.to_dict(),
            "maximum_temperature": self.maximum_temperature.to_dict(),
            "source": self.source,
        }

    @staticmethod
    def _common_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "name": payload["name"],
            "reference_resistivity": Quantity.from_dict(
                payload["reference_resistivity"]
            ),
            "reference_temperature": Quantity.from_dict(
                payload["reference_temperature"]
            ),
            "minimum_temperature": Quantity.from_dict(
                payload["minimum_temperature"]
            ),
            "maximum_temperature": Quantity.from_dict(
                payload["maximum_temperature"]
            ),
            "source": payload["source"],
        }


@dataclass(frozen=True)
class LinearResistivityMaterial(ConductorMaterial):
    """``rho(T) = rho_ref (1 + a (T - T_ref))``.

    The coefficient carries **no default**. A material declared without one
    would silently become a zero-TCR material — a property invented on the
    caller's behalf, which is the one thing a property mechanism must never
    do. An unstated property stays unstated, and construction fails.
    """

    temperature_coefficient: Quantity

    def __post_init__(self) -> None:
        super().__post_init__()
        _require(
            self.temperature_coefficient, TCR_UNIT,
            f"material {self.name!r} temperature_coefficient",
        )

    @property
    def alpha_per_k(self) -> float:
        return self.temperature_coefficient.magnitude_in(TCR_UNIT)

    def resistivity_model(self) -> ScientificModelDefinition:
        return LINEAR_RESISTIVITY_MODEL

    def resistivity_realization(self) -> ModelRealizationDefinition:
        return LINEAR_RESISTIVITY_REALIZATION

    def resistivity_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=REFERENCE_RESISTIVITY, value=self.reference_resistivity,
                description="Resistivity at the reference temperature.",
            ),
            ScientificParameter(
                name=TEMPERATURE_COEFFICIENT, value=self.temperature_coefficient,
                description="First-order temperature coefficient of resistivity.",
            ),
            ScientificParameter(
                name=REFERENCE_TEMPERATURE, value=self.reference_temperature,
                description="Temperature at which the reference value holds.",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": LINEAR_MATERIAL_SCHEMA,
            **self._common_dict(),
            "temperature_coefficient": self.temperature_coefficient.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LinearResistivityMaterial":
        require_schema(payload, LINEAR_MATERIAL_SCHEMA)
        return cls(
            **ConductorMaterial._common_fields(payload),
            temperature_coefficient=Quantity.from_dict(
                payload["temperature_coefficient"]
            ),
        )


@dataclass(frozen=True)
class QuadraticResistivityMaterial(ConductorMaterial):
    """``rho(T) = rho_ref (1 + a dT + b dT^2)``.

    A second functional form, not a second material. It exists because the
    linear form is a *reparameterization* of a model this repository already
    executes — the same claim with ``R_ref = rho_ref L / A`` — so a consumer
    built only on it could not disagree with what is already on the record.
    A second-order term makes the claim, and the fixed-point map it induces,
    genuinely different.

    Neither coefficient carries a default, for the reason
    :class:`LinearResistivityMaterial` states: a second-order coefficient
    defaulting to zero would quietly turn this record back into the linear
    form while still claiming the quadratic model.
    """

    temperature_coefficient: Quantity
    second_order_coefficient: Quantity

    def __post_init__(self) -> None:
        super().__post_init__()
        _require(
            self.temperature_coefficient, TCR_UNIT,
            f"material {self.name!r} temperature_coefficient",
        )
        _require(
            self.second_order_coefficient, TCR2_UNIT,
            f"material {self.name!r} second_order_coefficient",
        )

    @property
    def alpha_per_k(self) -> float:
        return self.temperature_coefficient.magnitude_in(TCR_UNIT)

    @property
    def beta_per_k2(self) -> float:
        return self.second_order_coefficient.magnitude_in(TCR2_UNIT)

    def resistivity_model(self) -> ScientificModelDefinition:
        return QUADRATIC_RESISTIVITY_MODEL

    def resistivity_realization(self) -> ModelRealizationDefinition:
        return QUADRATIC_RESISTIVITY_REALIZATION

    def resistivity_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=REFERENCE_RESISTIVITY, value=self.reference_resistivity,
                description="Resistivity at the reference temperature.",
            ),
            ScientificParameter(
                name=TEMPERATURE_COEFFICIENT, value=self.temperature_coefficient,
                description="First-order temperature coefficient of resistivity.",
            ),
            ScientificParameter(
                name=SECOND_ORDER_COEFFICIENT, value=self.second_order_coefficient,
                description="Second-order temperature coefficient of resistivity.",
            ),
            ScientificParameter(
                name=REFERENCE_TEMPERATURE, value=self.reference_temperature,
                description="Temperature at which the reference value holds.",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": QUADRATIC_MATERIAL_SCHEMA,
            **self._common_dict(),
            "temperature_coefficient": self.temperature_coefficient.to_dict(),
            "second_order_coefficient": self.second_order_coefficient.to_dict(),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "QuadraticResistivityMaterial":
        require_schema(payload, QUADRATIC_MATERIAL_SCHEMA)
        return cls(
            **ConductorMaterial._common_fields(payload),
            temperature_coefficient=Quantity.from_dict(
                payload["temperature_coefficient"]
            ),
            second_order_coefficient=Quantity.from_dict(
                payload["second_order_coefficient"]
            ),
        )


#: Schema -> reader. A table, not a chain of ``if``s, and closed: a payload
#: naming an unknown schema is refused rather than guessed at.
_MATERIAL_READERS = {
    LINEAR_MATERIAL_SCHEMA: LinearResistivityMaterial.from_dict,
    QUADRATIC_MATERIAL_SCHEMA: QuadraticResistivityMaterial.from_dict,
}


def material_from_dict(payload: Mapping[str, Any]) -> ConductorMaterial:
    """Rebuild a material, refusing a schema this reader does not know."""
    schema = payload.get("schema")
    reader = _MATERIAL_READERS.get(schema)
    if reader is None:
        raise ScientificCoreError(
            f"unsupported schema {schema!r}; expected one of "
            f"{sorted(_MATERIAL_READERS)}"
        )
    return reader(payload)


# =====================================================================
# The models — one per functional form
# =====================================================================

_LINEAR_ASSUMPTIONS = (
    "linear first-order temperature coefficient about a reference state",
    "isotropic scalar resistivity; no tensor conductivity",
    "no strain, ageing, frequency, purity or magnetic-field dependence",
    "temperature is uniform over the material (consistent with a lumped body)",
    "the applicability range is a property of the material, not of this form, "
    "and is carried by the material record",
)

_QUADRATIC_ASSUMPTIONS = (
    "second-order polynomial in temperature about a reference state",
    "isotropic scalar resistivity; no tensor conductivity",
    "no strain, ageing, frequency, purity or magnetic-field dependence",
    "temperature is uniform over the material (consistent with a lumped body)",
    "the applicability range is a property of the material, not of this form, "
    "and is carried by the material record",
)

_TEMPERATURE_INPUT = ModelInputSpec(
    name=TEMPERATURE,
    source_kind=InputSourceKind.VARIABLE,
    unit_exemplar=TEMPERATURE_UNIT,
    role=VariableRole.STATE,
    description=(
        "Material temperature. A state coordinate, supplied from outside "
        "this model; never inferred here."
    ),
)

_POSITIVE_RHO = RangeCondition(
    name=REFERENCE_RESISTIVITY,
    minimum=Quantity(0.0, RESISTIVITY_UNIT),
    minimum_inclusive=False,
    description="Strictly positive reference resistivity.",
)


LINEAR_RESISTIVITY_MODEL = ScientificModelDefinition(
    model_id="electrical.material.linear_resistivity",
    version=MODEL_VERSION,
    name="Linear temperature-dependent conductor resistivity",
    domain="electrical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Resistivity of a conductor material as a linear function of its "
        "temperature: rho(T) = rho_ref (1 + a (T - T_ref))."
    ),
    inputs=(
        ModelInputSpec(
            name=REFERENCE_RESISTIVITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=RESISTIVITY_UNIT,
            description="Resistivity at the reference temperature; positive.",
        ),
        ModelInputSpec(
            name=TEMPERATURE_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TCR_UNIT,
            description="First-order temperature coefficient of resistivity.",
        ),
        ModelInputSpec(
            name=REFERENCE_TEMPERATURE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TEMPERATURE_UNIT,
            description="Temperature at which the reference resistivity holds.",
        ),
        _TEMPERATURE_INPUT,
    ),
    outputs=(
        ModelOutputSpec(
            metric=RESISTIVITY_METRIC,
            unit_exemplar=RESISTIVITY_UNIT,
            description="Resistivity at the supplied temperature.",
        ),
    ),
    assumptions=_LINEAR_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(_POSITIVE_RHO,),
        description=(
            "What is universally true of the linear form. The temperature "
            "range over which any particular material's coefficients hold is "
            "a fact about that material and is carried by its own record; "
            "duplicating it here would create a second authority for one "
            "question."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


QUADRATIC_RESISTIVITY_MODEL = ScientificModelDefinition(
    model_id="electrical.material.quadratic_resistivity",
    version=MODEL_VERSION,
    name="Second-order temperature-dependent conductor resistivity",
    domain="electrical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Resistivity of a conductor material as a second-order polynomial in "
        "its temperature: rho(T) = rho_ref (1 + a dT + b dT^2)."
    ),
    inputs=(
        ModelInputSpec(
            name=REFERENCE_RESISTIVITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=RESISTIVITY_UNIT,
            description="Resistivity at the reference temperature; positive.",
        ),
        ModelInputSpec(
            name=TEMPERATURE_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TCR_UNIT,
            description="First-order temperature coefficient of resistivity.",
        ),
        ModelInputSpec(
            name=SECOND_ORDER_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TCR2_UNIT,
            description="Second-order temperature coefficient of resistivity.",
        ),
        ModelInputSpec(
            name=REFERENCE_TEMPERATURE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TEMPERATURE_UNIT,
            description="Temperature at which the reference resistivity holds.",
        ),
        _TEMPERATURE_INPUT,
    ),
    outputs=(
        ModelOutputSpec(
            metric=RESISTIVITY_METRIC,
            unit_exemplar=RESISTIVITY_UNIT,
            description="Resistivity at the supplied temperature.",
        ),
    ),
    assumptions=_QUADRATIC_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(_POSITIVE_RHO,),
        description=(
            "What is universally true of the quadratic form; per-material "
            "applicability is carried by the material record."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


GEOMETRIC_RESISTANCE_MODEL = ScientificModelDefinition(
    model_id="electrical.conductor.geometric_resistance",
    version=MODEL_VERSION,
    name="Resistance of a uniform prismatic conductor",
    domain="electrical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Resistance of a conductor of uniform cross-section: R = rho L / A."
    ),
    inputs=(
        # THE ONE INPUT THAT IS NOT CONFIGURED.
        #
        # Resistivity arrives from *another* model's result across a declared
        # QuantityDependency, so it is a VARIABLE with role CONTROL — imposed
        # from outside, saying nothing about who supplies it. The same
        # distinction thermal_lumped already draws between its imposed
        # ``heat_input`` (CONTROL) and its evolving ``temperature`` (STATE).
        ModelInputSpec(
            name=RESISTIVITY_METRIC,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=RESISTIVITY_UNIT,
            role=VariableRole.CONTROL,
            description=(
                "Material resistivity at the conductor's temperature. "
                "Imposed from outside this model."
            ),
        ),
        ModelInputSpec(
            name=LENGTH,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=LENGTH_UNIT,
            description="Conducting path length; strictly positive.",
        ),
        ModelInputSpec(
            name=CROSS_SECTIONAL_AREA,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=AREA_UNIT,
            description="Uniform cross-sectional area; strictly positive.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=RESISTANCE_METRIC,
            unit_exemplar=RESISTANCE_UNIT,
            description="Resistance of the conductor.",
        ),
    ),
    assumptions=(
        "uniform prismatic cross-section over the whole length",
        "uniform current density; no skin effect, proximity effect or "
        "current crowding",
        "isotropic scalar resistivity",
        "length and area are integration extents of a lumped conductor; they "
        "are NOT a geometry or topology contract and must not be read as one",
        "no contact, termination or joint resistance is represented",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=LENGTH,
                minimum=Quantity(0.0, LENGTH_UNIT),
                minimum_inclusive=False,
                description="Strictly positive conducting length.",
            ),
            RangeCondition(
                name=CROSS_SECTIONAL_AREA,
                minimum=Quantity(0.0, AREA_UNIT),
                minimum_inclusive=False,
                description="Strictly positive cross-section.",
            ),
        ),
        description=(
            "Conditions on the configured geometry, which are the only "
            "conditions this domain can evaluate before a solve: "
            "ScientificProblem.validity_context is built from PARAMETERS, and "
            "resistivity arrives as a VARIABLE. A condition on resistivity "
            "here would be permanently UNKNOWN and would make every conductor "
            "unassessable, so positivity of the supplied resistivity is a "
            "solver admissibility check instead."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


def _resistivity_realization(
    model: ScientificModelDefinition, suffix: str, description: str
) -> ModelRealizationDefinition:
    return ModelRealizationDefinition(
        realization_id=f"{model.model_id}.closed_form",
        version="0.1.0",
        model=ModelReference(model.model_id, model.version),
        formulation=ModelFormulation.ALGEBRAIC,
        name=f"Direct evaluation of the {suffix} resistivity expression",
        description=description,
        provided_capabilities=frozenset({TEMPERATURE_DEPENDENT_RESISTIVITY}),
        required_capabilities=frozenset({REQUIRED_BODY_TEMPERATURE}),
        required_solver_capabilities=frozenset(
            {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
        ),
        assumptions=(
            "single evaluation at one supplied temperature",
            "exact for the declared form; no discretization error exists",
        ),
        implementation=ImplementationReference(
            implementation_id="engcore.domains.electrical.conductor_material",
            version="0.1.0",
            reference="closed form; see module docstring",
        ),
    )


LINEAR_RESISTIVITY_REALIZATION = _resistivity_realization(
    LINEAR_RESISTIVITY_MODEL, "linear",
    "Evaluates rho_ref (1 + a dT) once, at a supplied temperature.",
)

QUADRATIC_RESISTIVITY_REALIZATION = _resistivity_realization(
    QUADRATIC_RESISTIVITY_MODEL, "quadratic",
    "Evaluates rho_ref (1 + a dT + b dT^2) once, at a supplied temperature.",
)

GEOMETRIC_RESISTANCE_REALIZATION = ModelRealizationDefinition(
    realization_id="electrical.conductor.geometric_resistance.closed_form",
    version="0.1.0",
    model=ModelReference(
        GEOMETRIC_RESISTANCE_MODEL.model_id, GEOMETRIC_RESISTANCE_MODEL.version
    ),
    formulation=ModelFormulation.ALGEBRAIC,
    name="Direct evaluation of R = rho L / A",
    description="One division and one multiplication, at a supplied resistivity.",
    #: Truthful, and narrower than it is tempting to write. See
    #: RESISTANCE_FROM_GEOMETRY.
    provided_capabilities=frozenset({RESISTANCE_FROM_GEOMETRY}),
    #: A real machine-checkable dependency: this computation cannot be planned
    #: unless something supplies a temperature-dependent resistivity.
    required_capabilities=frozenset({TEMPERATURE_DEPENDENT_RESISTIVITY}),
    required_solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=("exact for the declared form; no discretization error exists",),
    implementation=ImplementationReference(
        implementation_id="engcore.domains.electrical.conductor_material",
        version="0.1.0",
        reference="R = rho L / A; see module docstring",
    ),
)


def conductor_material_registry() -> ModelRegistry:
    """A fresh registry. No global singleton exists."""
    return ModelRegistry(
        (
            LINEAR_RESISTIVITY_MODEL,
            QUADRATIC_RESISTIVITY_MODEL,
            GEOMETRIC_RESISTANCE_MODEL,
        )
    )


def conductor_material_realizations() -> RealizationRegistry:
    """A fresh registry. No global singleton exists."""
    return RealizationRegistry(
        (
            LINEAR_RESISTIVITY_REALIZATION,
            QUADRATIC_RESISTIVITY_REALIZATION,
            GEOMETRIC_RESISTANCE_REALIZATION,
        )
    )


def conductor_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({CoreCapabilities.ALGEBRAIC})


# =====================================================================
# The catalogue — DATA
# =====================================================================
#
# Everything below this line is data. Adding a material is adding one frozen
# record to this table: no model, no realization, no solver, no problem
# builder, no admission check and no coupling code changes. That is asserted
# by test, not asserted here.
#
# PROVENANCE, stated because a number with no stated origin is not a
# declaration. The four entries below carry resistivity at 20 degC (293.15 K)
# and a first-order temperature coefficient referred to the same temperature,
# as tabulated in the standard handbook tables of electrical resistivity of
# pure metals. This repository has measured no conductor and curates no
# reference set, so every model above is SELF_CONSISTENT with no references,
# and no citation is invented to dress that up. The tungsten second-order
# coefficient is NOT a published correlation: it is a two-point fit performed
# for this milestone against tabulated tungsten resistivity at 500 K and 800 K
# anchored at 300 K, and its `source` string says so.

COPPER = LinearResistivityMaterial(
    name="copper",
    reference_resistivity=Quantity(1.678e-8, RESISTIVITY_UNIT),
    temperature_coefficient=Quantity(3.93e-3, TCR_UNIT),
    reference_temperature=Quantity(293.15, TEMPERATURE_UNIT),
    minimum_temperature=Quantity(200.0, TEMPERATURE_UNIT),
    maximum_temperature=Quantity(450.0, TEMPERATURE_UNIT),
    source=(
        "standard handbook resistivity of pure metals at 20 degC; annealed "
        "copper 1.678e-8 ohm*m, alpha 3.93e-3 /K. Range stated to match the "
        "linear-form range already declared by "
        "engcore.domains.electrical.material.LINEAR_TCR_MODEL."
    ),
)

ALUMINIUM = LinearResistivityMaterial(
    name="aluminium",
    reference_resistivity=Quantity(2.650e-8, RESISTIVITY_UNIT),
    temperature_coefficient=Quantity(4.29e-3, TCR_UNIT),
    reference_temperature=Quantity(293.15, TEMPERATURE_UNIT),
    minimum_temperature=Quantity(200.0, TEMPERATURE_UNIT),
    maximum_temperature=Quantity(450.0, TEMPERATURE_UNIT),
    source=(
        "standard handbook resistivity of pure metals at 20 degC; aluminium "
        "2.650e-8 ohm*m, alpha 4.29e-3 /K."
    ),
)

#: The third material. Added as DATA ONLY, after the mechanism worked for
#: copper and aluminium, with zero change to any model, realization, solver,
#: problem builder, admission check or coupling code.
SILVER = LinearResistivityMaterial(
    name="silver",
    reference_resistivity=Quantity(1.587e-8, RESISTIVITY_UNIT),
    temperature_coefficient=Quantity(3.80e-3, TCR_UNIT),
    reference_temperature=Quantity(293.15, TEMPERATURE_UNIT),
    minimum_temperature=Quantity(200.0, TEMPERATURE_UNIT),
    maximum_temperature=Quantity(450.0, TEMPERATURE_UNIT),
    source=(
        "standard handbook resistivity of pure metals at 20 degC; silver "
        "1.587e-8 ohm*m, alpha 3.80e-3 /K."
    ),
)

#: The material whose property set needs a *different functional form*, which
#: is the axis on which more than one model is justified.
TUNGSTEN = QuadraticResistivityMaterial(
    name="tungsten",
    reference_resistivity=Quantity(5.440e-8, RESISTIVITY_UNIT),
    temperature_coefficient=Quantity(4.21934e-3, TCR_UNIT),
    second_order_coefficient=Quantity(1.23775e-6, TCR2_UNIT),
    reference_temperature=Quantity(300.0, TEMPERATURE_UNIT),
    minimum_temperature=Quantity(290.0, TEMPERATURE_UNIT),
    maximum_temperature=Quantity(900.0, TEMPERATURE_UNIT),
    source=(
        "rho(300 K) = 5.44e-8 ohm*m from the standard handbook table of "
        "electrical resistivity of pure metals. The two coefficients are NOT "
        "a published correlation: they are a two-point fit of "
        "rho_ref(1 + a dT + b dT^2) performed for COMPOSITE-SYSTEM0 against "
        "the same table's 500 K (10.3e-8) and 800 K (18.6e-8) entries, "
        "anchored at 300 K. Stated as SELF_CONSISTENT; no reference set is "
        "claimed and none is invented."
    ),
)

#: The curated set. Callers may equally construct a material inline and never
#: touch this table — the mechanism is not catalogue-gated, which is asserted
#: by test.
MATERIAL_CATALOGUE: Mapping[str, ConductorMaterial] = {
    material.name: material
    for material in (ALUMINIUM, COPPER, SILVER, TUNGSTEN)
}


def known_material_names() -> tuple[str, ...]:
    return tuple(sorted(MATERIAL_CATALOGUE))


def resolve_material(name: str) -> ConductorMaterial:
    """Look one up by name, refusing an unknown one.

    Refusal names the known set, because "which materials are there" is a
    question a caller who got this wrong needs answered.
    """
    key = str(name).strip()
    try:
        return MATERIAL_CATALOGUE[key]
    except KeyError:
        raise InvalidScientificProblem(
            f"unsupported conductor material {name!r}; the catalogue declares "
            f"{list(known_material_names())}. A material outside it may be "
            f"declared explicitly as a ConductorMaterial record, but it is "
            f"never invented from a name."
        ) from None


# =====================================================================
# The conductor declaration
# =====================================================================

@dataclass(frozen=True)
class MaterialConductor:
    """One declared conductor: what it is made of, and how big it is.

    It carries no temperature and no resistance. A temperature is a state, and
    a resistance is a *result* — the whole point of this record is that the
    resistance is computed from the material and the geometry through declared
    models rather than supplied as a number.
    """

    component_id: str
    material: ConductorMaterial
    length: Quantity
    cross_sectional_area: Quantity

    def __post_init__(self) -> None:
        component_id = str(self.component_id).strip()
        if not component_id:
            raise InvalidScientificProblem("conductor requires a component_id")
        object.__setattr__(self, "component_id", component_id)

        if not isinstance(self.material, ConductorMaterial):
            raise InvalidScientificProblem(
                f"conductor {component_id!r} must declare a ConductorMaterial, "
                f"got {type(self.material).__name__}"
            )
        _require_positive(
            self.length, LENGTH_UNIT, f"conductor {component_id!r} length"
        )
        _require_positive(
            self.cross_sectional_area, AREA_UNIT,
            f"conductor {component_id!r} cross_sectional_area",
        )

    @property
    def length_m(self) -> float:
        return self.length.magnitude_in(LENGTH_UNIT)

    @property
    def area_m2(self) -> float:
        return self.cross_sectional_area.magnitude_in(AREA_UNIT)

    @property
    def resistivity_problem_id(self) -> str:
        return f"conductor_resistivity:{self.component_id}"

    @property
    def resistance_problem_id(self) -> str:
        return f"conductor_resistance:{self.component_id}"

    def geometry_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=LENGTH, value=self.length,
                description="Conducting path length.",
            ),
            ScientificParameter(
                name=CROSS_SECTIONAL_AREA, value=self.cross_sectional_area,
                description="Uniform cross-sectional area.",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": MATERIAL_CONDUCTOR_SCHEMA,
            "component_id": self.component_id,
            "material": self.material.to_dict(),
            "length": self.length.to_dict(),
            "cross_sectional_area": self.cross_sectional_area.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaterialConductor":
        require_schema(payload, MATERIAL_CONDUCTOR_SCHEMA)
        return cls(
            component_id=payload["component_id"],
            material=material_from_dict(payload["material"]),
            length=Quantity.from_dict(payload["length"]),
            cross_sectional_area=Quantity.from_dict(
                payload["cross_sectional_area"]
            ),
        )


# =====================================================================
# Problem statements
# =====================================================================

def build_resistivity_problem(
    conductor: MaterialConductor, *, problem_id: str | None = None
) -> ScientificProblem:
    """The universal problem statement for one resistivity evaluation.

    ``material`` is carried as a **typed categorical parameter**, not as a
    metadata string. Its ``vocabulary`` is deliberately **empty**: a vocabulary
    built from the catalogue would write library membership into a per-wire
    record, so the same physical wire would serialize to different bytes after
    an unrelated catalogue addition — and, unioned with the wire's own
    material, it would be satisfiable by construction and so unfalsifiable.
    Refusing an unsupported material is :func:`resolve_material`'s job.
    """
    return ScientificProblem(
        problem_id=problem_id or conductor.resistivity_problem_id,
        name=f"Temperature-dependent resistivity of {conductor.component_id}",
        description=(
            "Evaluate rho(T) for one conductor material at one supplied "
            "temperature."
        ),
        variables=(
            ScientificVariable(
                name=TEMPERATURE,
                unit=TEMPERATURE_UNIT,
                role=VariableRole.STATE,
                description="Conductor temperature; supplied, not chosen.",
            ),
        ),
        parameters=(
            ScientificParameter(
                name=MATERIAL,
                value=CategoricalValue(conductor.material.name),
                description=(
                    "Which material's declared property set was evaluated."
                ),
            ),
            *conductor.material.resistivity_parameters(),
        ),
        models=(
            ModelReference(
                conductor.material.resistivity_model().model_id,
                conductor.material.resistivity_model().version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def build_geometric_resistance_problem(
    conductor: MaterialConductor, *, problem_id: str | None = None
) -> ScientificProblem:
    """The universal problem statement for one ``R = rho L / A`` evaluation.

    ``resistivity`` is a **variable with role CONTROL** carrying no value: the
    problem states that a resistivity is required and what dimension it has,
    without asserting which one. Where the value comes from is a separate fact
    and lives in a separate record — a ``QuantityDependency``.
    """
    return ScientificProblem(
        problem_id=problem_id or conductor.resistance_problem_id,
        name=f"Geometric resistance of {conductor.component_id}",
        description="Evaluate R = rho L / A for one conductor.",
        variables=(
            ScientificVariable(
                name=RESISTIVITY_METRIC,
                unit=RESISTIVITY_UNIT,
                role=VariableRole.CONTROL,
                description="Material resistivity; imposed from outside.",
            ),
        ),
        parameters=conductor.geometry_parameters(),
        models=(
            ModelReference(
                GEOMETRIC_RESISTANCE_MODEL.model_id,
                GEOMETRIC_RESISTANCE_MODEL.version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


# =====================================================================
# Validity (reported) and admission (enforced)
# =====================================================================

def assess_material_applicability(
    material: ConductorMaterial, temperature: Quantity
) -> ValidityAssessment:
    """Is this material's declared property set applicable at this temperature?

    **Validity, not validation**, and *reported*, not enforced. The material's
    own range is the single authority; no model restates it.
    """
    _require(temperature, TEMPERATURE_UNIT, "applicability temperature")
    return material.applicability().assess({TEMPERATURE: temperature})


def assess_conductor_geometry(conductor: MaterialConductor) -> ValidityAssessment:
    """Is the geometric model applicable to this conductor's geometry?

    Evaluated from the problem's own parameters, through
    :meth:`ScientificProblem.validity_context`, so nothing here restates a
    bound that the model record already carries.
    """
    problem = build_geometric_resistance_problem(conductor)
    return GEOMETRIC_RESISTANCE_MODEL.assess_validity(problem.validity_context())


def admit_conductor(
    conductor: MaterialConductor, temperature: Quantity
) -> None:
    """Refuse a conductor that must not be executed. **Enforcement.**

    Detection is not enforcement: :func:`assess_material_applicability` returns
    a record, and a record nobody acts on is not a guard. This raises, and it
    raises *before* any solver is constructed.

    What it can gate is the **declaration and the supplied temperature** —
    which is all a pre-run gate can gate. Whether the *converged* state stayed
    inside the material's range is a different question that only exists after
    a run, and it is answered by reporting, never by refusing.
    """
    geometry = assess_conductor_geometry(conductor)
    if geometry.status is not ValidityStatus.IN_DOMAIN:
        raise InvalidScientificProblem(
            f"conductor {conductor.component_id!r} is inadmissible: the "
            f"geometric resistance model reports {geometry.status.value} "
            f"(violated: {list(geometry.violated)}, "
            f"unknown: {list(geometry.unknown)})"
        )
    applicability = assess_material_applicability(conductor.material, temperature)
    if applicability.status is not ValidityStatus.IN_DOMAIN:
        raise InvalidScientificProblem(
            f"conductor {conductor.component_id!r} declares material "
            f"{conductor.material.name!r}, whose property set is declared "
            f"valid over [{conductor.material.minimum_temperature}, "
            f"{conductor.material.maximum_temperature}]; at {temperature} the "
            f"material reports {applicability.status.value}. Extrapolating a "
            f"declared property set outside its stated range is refused, not "
            f"performed silently."
        )


# =====================================================================
# Evaluators
# =====================================================================

LINEAR_SOLVER_ID = "engcore.electrical.linear_resistivity_evaluator"
QUADRATIC_SOLVER_ID = "engcore.electrical.quadratic_resistivity_evaluator"
GEOMETRIC_RESISTANCE_SOLVER_ID = "engcore.electrical.geometric_resistance_evaluator"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.float"


@dataclass(frozen=True)
class PreparedResistivityEvaluation:
    conductor: MaterialConductor
    realization: ModelRealizationDefinition
    temperature_k: float


@dataclass(frozen=True)
class PreparedResistanceEvaluation:
    conductor: MaterialConductor
    realization: ModelRealizationDefinition
    resistivity_ohm_m: float


class _ResistivitySolverBase:
    """Shared machinery for the two resistivity evaluators.

    Each concrete subclass names **one fixed model key**, so ``supports`` is
    stateless and needs no string parsing of a model id and no knowledge of
    which materials exist. A material constructed outside the catalogue is
    therefore supported for free.
    """

    _model: ScientificModelDefinition
    _realization: ModelRealizationDefinition
    _material_type: type
    _solver_id: str

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[MaterialConductor, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(self._solver_id, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return conductor_solver_capabilities()

    def bind_conductor(
        self,
        conductor: MaterialConductor,
        problem_id: str,
        *,
        temperature: Quantity,
    ) -> None:
        if not isinstance(conductor, MaterialConductor):
            raise InvalidScientificProblem(
                "bind_conductor expects a MaterialConductor"
            )
        if not isinstance(conductor.material, self._material_type):
            raise InvalidScientificProblem(
                f"{type(self).__name__} evaluates "
                f"{self._material_type.__name__} declarations; conductor "
                f"{conductor.component_id!r} declares "
                f"{type(conductor.material).__name__}"
            )
        kelvin = temperature.magnitude_in(TEMPERATURE_UNIT)
        if not math.isfinite(kelvin):
            raise InvalidScientificProblem("temperature must be finite")
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0] != conductor:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different conductor"
            )
        self._bound[key] = (conductor, kelvin)

    @staticmethod
    def verify_problem_matches_conductor(
        problem: ScientificProblem, conductor: MaterialConductor
    ) -> None:
        """Refuse a problem describing a different conductor than the bound one.

        A result whose provenance contradicts the declaration that produced it
        is worse than no result, which is why every domain in this repository
        has this guard.
        """
        stated_material = problem.parameter(MATERIAL).value
        if (
            not isinstance(stated_material, CategoricalValue)
            or stated_material.value != conductor.material.name
        ):
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r} states material "
                f"{stated_material!r} but the bound conductor declares "
                f"{conductor.material.name!r}"
            )
        for parameter in conductor.material.resistivity_parameters():
            stated = problem.parameter(parameter.name).value
            if (
                not isinstance(stated, Quantity)
                or stated.compare(parameter.value) != 0.0
            ):
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states "
                    f"{parameter.name} = {stated} but the bound material "
                    f"declares {parameter.value}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        """Matched on the model reference the problem carries.

        Not on a capability: ``core:algebraic`` says a closed-form evaluation
        is needed, which is true of countless unrelated relations. Not by
        parsing a model id either — the key is a fixed pair.
        """
        wanted = self._model.key
        return any(model.key == wanted for model in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition | None = None,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no conductor is bound to problem {problem.problem_id!r}; "
                f"call bind_conductor first"
            )
        conductor, kelvin = bound
        self.verify_problem_matches_conductor(problem, conductor)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedResistivityEvaluation(
                conductor=conductor,
                realization=realization or self._realization,
                temperature_k=kelvin,
            ),
        )

    def _resistivity(self, conductor: MaterialConductor, kelvin: float) -> float:
        raise NotImplementedError

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        evaluation: PreparedResistivityEvaluation = prepared.payload
        started = time.perf_counter()
        resistivity = self._resistivity(
            evaluation.conductor, evaluation.temperature_k
        )
        material = evaluation.conductor.material
        return RawSolverOutput(
            values={RESISTIVITY_METRIC: resistivity},
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "temperature_k": evaluation.temperature_k,
                "delta_t_k": evaluation.temperature_k - material.t_ref_k,
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            RESISTIVITY_METRIC: Quantity(
                raw.values[RESISTIVITY_METRIC], RESISTIVITY_UNIT
            )
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """One admissibility check, establishing no evidence level.

        A positive resistivity is a precondition for the geometric model and
        for the linear DC formulation downstream. Checking it earns no
        ``ValidationLevel``: confirming that a number is in the physically
        admissible range is not verification against anything.
        """
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="resistivity_strictly_positive",
                        outcome=ValidationOutcome.FAIL,
                        detail="the evaluation did not succeed",
                    ),
                )
            )
        value = raw.values[RESISTIVITY_METRIC]
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="resistivity_strictly_positive",
                    outcome=(
                        ValidationOutcome.PASS if value > 0.0
                        else ValidationOutcome.FAIL
                    ),
                    detail=(
                        f"rho = {value:.6g} ohm*m. A polynomial form crosses "
                        f"zero at a large enough negative excursion; a "
                        f"non-positive resistivity is refused rather than "
                        f"passed downstream."
                    ),
                ),
            ),
            notes=(
                "Admissibility only. Whether the material's property set was "
                "applicable at this temperature is a validity question and is "
                "answered by assess_material_applicability, not here.",
            ),
        )


class LinearResistivitySolver(_ResistivitySolverBase):
    """``rho = rho_ref (1 + a dT)``."""

    _model = LINEAR_RESISTIVITY_MODEL
    _realization = LINEAR_RESISTIVITY_REALIZATION
    _material_type = LinearResistivityMaterial
    _solver_id = LINEAR_SOLVER_ID

    def _resistivity(self, conductor: MaterialConductor, kelvin: float) -> float:
        material: LinearResistivityMaterial = conductor.material
        return material.rho_ref_ohm_m * (
            1.0 + material.alpha_per_k * (kelvin - material.t_ref_k)
        )


class QuadraticResistivitySolver(_ResistivitySolverBase):
    """``rho = rho_ref (1 + a dT + b dT^2)``."""

    _model = QUADRATIC_RESISTIVITY_MODEL
    _realization = QUADRATIC_RESISTIVITY_REALIZATION
    _material_type = QuadraticResistivityMaterial
    _solver_id = QUADRATIC_SOLVER_ID

    def _resistivity(self, conductor: MaterialConductor, kelvin: float) -> float:
        material: QuadraticResistivityMaterial = conductor.material
        delta = kelvin - material.t_ref_k
        return material.rho_ref_ohm_m * (
            1.0 + material.alpha_per_k * delta + material.beta_per_k2 * delta * delta
        )


#: Declared realization id -> the evaluator that runs it.
#:
#: This table is what maps *science* onto *execution*. It is keyed by a
#: declared identity, never by a material name, so adding a material to the
#: catalogue does not touch it — and a material that names an unknown
#: realization is refused rather than guessed at.
_RESISTIVITY_SOLVERS = {
    LINEAR_RESISTIVITY_REALIZATION.realization_id: LinearResistivitySolver,
    QUADRATIC_RESISTIVITY_REALIZATION.realization_id: QuadraticResistivitySolver,
}


def resistivity_solver_for(material: ConductorMaterial):
    """A fresh evaluator for whatever functional form this material declares."""
    realization_id = material.resistivity_realization().realization_id
    try:
        factory = _RESISTIVITY_SOLVERS[realization_id]
    except KeyError:
        raise InvalidScientificProblem(
            f"material {material.name!r} declares realization "
            f"{realization_id!r}, which this pack has no evaluator for; "
            f"known: {sorted(_RESISTIVITY_SOLVERS)}"
        ) from None
    return factory()


class GeometricResistanceSolver:
    """``R = rho L / A`` for one conductor at one supplied resistivity."""

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[MaterialConductor, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(
            GEOMETRIC_RESISTANCE_SOLVER_ID, SOLVER_VERSION, backend=BACKEND
        )

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return conductor_solver_capabilities()

    def bind_conductor(
        self,
        conductor: MaterialConductor,
        problem_id: str,
        *,
        resistivity: Quantity,
    ) -> None:
        if not isinstance(conductor, MaterialConductor):
            raise InvalidScientificProblem(
                "bind_conductor expects a MaterialConductor"
            )
        value = resistivity.magnitude_in(RESISTIVITY_UNIT)
        if not math.isfinite(value):
            raise InvalidScientificProblem("resistivity must be finite")
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0] != conductor:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different conductor"
            )
        self._bound[key] = (conductor, value)

    @staticmethod
    def verify_problem_matches_conductor(
        problem: ScientificProblem, conductor: MaterialConductor
    ) -> None:
        for parameter in conductor.geometry_parameters():
            stated = problem.parameter(parameter.name).value
            if (
                not isinstance(stated, Quantity)
                or stated.compare(parameter.value) != 0.0
            ):
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states "
                    f"{parameter.name} = {stated} but the bound conductor "
                    f"declares {parameter.value}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        wanted = GEOMETRIC_RESISTANCE_MODEL.key
        return any(model.key == wanted for model in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = GEOMETRIC_RESISTANCE_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no conductor is bound to problem {problem.problem_id!r}; "
                f"call bind_conductor first"
            )
        conductor, resistivity = bound
        self.verify_problem_matches_conductor(problem, conductor)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedResistanceEvaluation(
                conductor=conductor,
                realization=realization,
                resistivity_ohm_m=resistivity,
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        evaluation: PreparedResistanceEvaluation = prepared.payload
        conductor = evaluation.conductor
        started = time.perf_counter()
        resistance = (
            evaluation.resistivity_ohm_m * conductor.length_m / conductor.area_m2
        )
        return RawSolverOutput(
            values={RESISTANCE_METRIC: resistance},
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "resistivity_ohm_m": evaluation.resistivity_ohm_m,
                "length_m": conductor.length_m,
                "area_m2": conductor.area_m2,
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            RESISTANCE_METRIC: Quantity(
                raw.values[RESISTANCE_METRIC], RESISTANCE_UNIT
            )
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Two admissibility checks, establishing no evidence level.

        ``resistivity_strictly_positive`` lives here rather than in the
        model's ``ValidityDomain`` on purpose: resistivity arrives as a
        *variable*, ``validity_context`` is built from *parameters*, and a
        validity condition on it would be permanently UNKNOWN — so it would
        have made every conductor unassessable while checking nothing.
        """
        evaluation: PreparedResistanceEvaluation = prepared.payload
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="resistance_strictly_positive",
                        outcome=ValidationOutcome.FAIL,
                        detail="the evaluation did not succeed",
                    ),
                )
            )
        resistivity = evaluation.resistivity_ohm_m
        resistance = raw.values[RESISTANCE_METRIC]
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="resistivity_strictly_positive",
                    outcome=(
                        ValidationOutcome.PASS if resistivity > 0.0
                        else ValidationOutcome.FAIL
                    ),
                    detail=(
                        f"rho = {resistivity:.6g} ohm*m was supplied. A "
                        f"non-positive resistivity is not a conductor."
                    ),
                ),
                ValidationCheck(
                    name="resistance_strictly_positive",
                    outcome=(
                        ValidationOutcome.PASS if resistance > 0.0
                        else ValidationOutcome.FAIL
                    ),
                    detail=(
                        f"R = {resistance:.6g} ohm. The surrounding linear DC "
                        f"formulation refuses zero and negative resistances."
                    ),
                ),
            ),
            notes=(
                "Admissibility only. Geometry validity is a separate question "
                "answered by assess_conductor_geometry.",
            ),
        )
