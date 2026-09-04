"""One material declaration that drives both an electrical and a thermal property.

`PROPULSION0`. The record this milestone was warned about, and the move the
warning did not list.

The pre-registered promotion trigger, and what happened to it
------------------------------------------------------------
``engcore.domains.electrical.conductor_material`` carries a trigger written a
milestone in advance:

    The first time a non-electrical domain needs a property of the same named
    material — the moment a thermal pack wants ``rho_m c_p V`` for the same
    copper instead of a lumped ``heat_capacity`` — this record is in the wrong
    package, because **the only two moves available at that moment are a
    domain-to-domain import and a duplicate**, and both are architecture
    findings.

This milestone needs exactly that: one declaration supplying resistivity, TCR,
density and specific heat, with ``C = rho_m L A c_p``. And the note's premise is
**measurably false**, because a third move exists that it does not enumerate:

    leave the electrical record where it is, and let a **consumer that already
    sits above both domains** compose it.

:class:`ThermophysicalConductor` is that composition. It holds the existing
``ConductorMaterial`` **by reference** — ``COPPER_THERMOPHYSICAL.conductor_material
is cmat.COPPER`` — and adds the two properties the electrical record has no
business declaring. No number is copied, no electrical file is edited, no
thermal file is edited, no universal ``Material`` contract is minted, and the
import direction is strictly downward: a system pack depends on two domains,
which ``power_chain`` already does.

What this **defers rather than defeats**, stated plainly
--------------------------------------------------------
1. The trigger's stated condition — *a non-electrical **domain** needs the
   property* — is never satisfied here, because the consumer is a system pack.
   The trigger therefore remains **armed and untested**.
2. One physical copper now has **two declaration records with disjoint property
   sets, and no contract binds them.** That is a real cost, and it is the reason
   this record refuses to restate a single electrical number.
3. The in-process link is **object identity**; the serialized link is the
   material's **name**, because ``from_dict`` re-binds through
   ``cmat.material_from_dict``. Those are not the same guarantee, and the name
   is therefore a de facto key — the thing ``COMPOSITE-SYSTEM0`` avoided when it
   gave the material's ``CategoricalValue`` an empty vocabulary.

Placement, and the dissent that was recorded before the code was written
------------------------------------------------------------------------
``architecture-decision-reviewer`` preferred this record in ``domains/`` so that
a second pack would not need a system-to-system import. It is here instead, and
the preregistration states why in advance: a composing record placed in
``domains/`` and importing ``domains/electrical/conductor_material`` **is** the
domain-to-domain import the trigger names — it would satisfy the trigger rather
than measure it — and there is no second consumer, so building the reusable
placement for one is the speculative move this lineage refuses.

**New promotion trigger, replacing the one this record deferred:** the first
time a *second pack*, or any *thermal domain module*, needs ``rho_m``/``c_p``
for a named material, this record is in the wrong package and a materials
decision is the answer — not a third composition.

Why the heat capacity is derived once, and not on a coupling edge
-----------------------------------------------------------------
``heat_capacity`` **is** a declared ``ScientificParameter`` of the lumped
thermal problem, so it is a perfectly legal ``QuantityDependency`` target and an
edge would work. It is not one here because ``rho_m`` and ``c_p`` are declared
temperature-independent, so the capacity does not move during the coupling and a
static derivation is the smaller architecture. The day someone declares
``c_p(T)``, the edge route exists at zero contract cost. Recorded so the reason
is the real one.

What is **not** allowed is computing ``rho_m L A c_p`` in caller Python. That
would be an unmodelled scientific claim with no model, no realization, no solver
and no ``ExecutionBinding`` — the exact defect ``COMPOSITE-SYSTEM0`` refused for
``rho L / A``. So it goes through :data:`CONDUCTOR_THERMAL_MASS_MODEL`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

from ...domains.electrical import conductor_material as cmat
from ...scientific.capabilities import ScientificCapability
from ...scientific.errors import InvalidScientificProblem
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.ir.values import CategoricalValue
from ...scientific.ir.variables import ScientificParameter
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
    "ALUMINIUM_THERMOPHYSICAL",
    "CONDUCTOR_THERMAL_MASS_MODEL",
    "CONDUCTOR_THERMAL_MASS_REALIZATION",
    "COPPER_THERMOPHYSICAL",
    "DENSITY",
    "DENSITY_UNIT",
    "HEAT_CAPACITY_METRIC",
    "HEAT_CAPACITY_UNIT",
    "SPECIFIC_HEAT",
    "SPECIFIC_HEAT_UNIT",
    "THERMOPHYSICAL_CONDUCTOR_SCHEMA",
    "ConductorThermalMassSolver",
    "ThermophysicalConductor",
    "build_thermal_mass_problem",
    "thermal_mass_model_registry",
    "thermal_mass_realizations",
    "thermal_mass_solver_capabilities",
]

DENSITY_UNIT = "kilogram / meter ** 3"
SPECIFIC_HEAT_UNIT = "joule / (kilogram * kelvin)"
HEAT_CAPACITY_UNIT = "joule / kelvin"

DENSITY = "density"
SPECIFIC_HEAT = "specific_heat"
HEAT_CAPACITY_METRIC = "heat_capacity"

MODEL_VERSION = "0.1.0"
THERMOPHYSICAL_CONDUCTOR_SCHEMA = schema_string("thermophysical_conductor")

CONDUCTOR_HEAT_CAPACITY = ScientificCapability.parse("thermal:conductor_heat_capacity")

CONDUCTOR_THERMAL_MASS = SolverCapability(
    "thermal:conductor_thermal_mass",
    "Total heat capacity of a uniform conductor from its material and geometry",
)


# =====================================================================
# The claim
# =====================================================================

CONDUCTOR_THERMAL_MASS_MODEL = ScientificModelDefinition(
    model_id="thermal.conductor.geometric_thermal_mass",
    version=MODEL_VERSION,
    name="Thermal mass of a uniform conductor",
    domain="thermal",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Total heat capacity of a prismatic conductor from its material and "
        "its geometry: C = rho_m * L * A * c_p."
    ),
    inputs=(
        ModelInputSpec(
            name=DENSITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=DENSITY_UNIT,
            description="Mass density of the material; strictly positive.",
        ),
        ModelInputSpec(
            name=SPECIFIC_HEAT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=SPECIFIC_HEAT_UNIT,
            description="Specific heat capacity of the material; positive.",
        ),
        ModelInputSpec(
            name=cmat.LENGTH,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=cmat.LENGTH_UNIT,
            description="Conductor length; strictly positive.",
        ),
        ModelInputSpec(
            name=cmat.CROSS_SECTIONAL_AREA,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=cmat.AREA_UNIT,
            description="Uniform cross-sectional area; strictly positive.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=HEAT_CAPACITY_METRIC,
            unit_exemplar=HEAT_CAPACITY_UNIT,
            description="Total heat capacity of the conductor.",
        ),
    ),
    assumptions=(
        "prismatic body: the cross-section is uniform along the length, so "
        "the volume is L*A",
        "the density and the specific heat are uniform over the body and "
        "independent of temperature over the interval considered",
        "the conductor is solid material only: no insulation, no potting, no "
        "former and no air is included in the thermal mass",
        "this is the capacity of the conductor alone; whether that is the "
        "right lumped body for a given assembly is the caller's declaration, "
        "not this model's claim",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=DENSITY,
                minimum=Quantity(0.0, DENSITY_UNIT),
                minimum_inclusive=False,
                description="A body with no mass has no thermal mass.",
            ),
            RangeCondition(
                name=SPECIFIC_HEAT,
                minimum=Quantity(0.0, SPECIFIC_HEAT_UNIT),
                minimum_inclusive=False,
                description="Strictly positive; zero would be an inert body.",
            ),
            RangeCondition(
                name=cmat.LENGTH,
                minimum=Quantity(0.0, cmat.LENGTH_UNIT),
                minimum_inclusive=False,
                description="Strictly positive length.",
            ),
            RangeCondition(
                name=cmat.CROSS_SECTIONAL_AREA,
                minimum=Quantity(0.0, cmat.AREA_UNIT),
                minimum_inclusive=False,
                description="Strictly positive area.",
            ),
        ),
        description=(
            "All four inputs are parameters, so all four are assessable "
            "before anything runs — unlike the geometric resistance model, "
            "whose resistivity arrives as a variable and therefore cannot "
            "carry a validity condition."
        ),
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


CONDUCTOR_THERMAL_MASS_REALIZATION = ModelRealizationDefinition(
    realization_id="thermal.conductor.geometric_thermal_mass.direct",
    version="0.1.0",
    model=ModelReference(
        CONDUCTOR_THERMAL_MASS_MODEL.model_id, CONDUCTOR_THERMAL_MASS_MODEL.version
    ),
    formulation=ModelFormulation.ALGEBRAIC,
    name="Direct evaluation of the prismatic thermal mass",
    description="C = rho_m * L * A * c_p, evaluated as written.",
    provided_capabilities=frozenset({CONDUCTOR_HEAT_CAPACITY}),
    required_solver_capabilities=frozenset(
        {
            SolverCapabilityId.coerce(CONDUCTOR_THERMAL_MASS),
            SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC),
        }
    ),
    assumptions=(
        "no discretization, no iteration and no approximation is introduced "
        "between the claim and the number",
    ),
    implementation=ImplementationReference(
        implementation_id="engcore.systems.propulsion.materials",
        version="0.1.0",
        reference="single algebraic expression; see the model description",
    ),
)


def thermal_mass_model_registry() -> ModelRegistry:
    return ModelRegistry((CONDUCTOR_THERMAL_MASS_MODEL,))


def thermal_mass_realizations() -> RealizationRegistry:
    return RealizationRegistry((CONDUCTOR_THERMAL_MASS_REALIZATION,))


def thermal_mass_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({CONDUCTOR_THERMAL_MASS, CoreCapabilities.ALGEBRAIC})


# =====================================================================
# The composed declaration
# =====================================================================

def _require_positive(value: Any, unit: str, label: str) -> None:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(f"{label} must be a Quantity")
    value.require_compatible(unit, context=label)
    if value.magnitude_in(unit) <= 0.0:
        raise InvalidScientificProblem(
            f"{label} must be strictly positive, got {value}"
        )


@dataclass(frozen=True)
class ThermophysicalConductor:
    """One material, stated once, supplying an electrical and a thermal claim.

    ``conductor_material`` is the **existing** electrical record, held by
    reference. Its resistivity, its temperature coefficient, its reference
    temperature, its applicability range and its provenance string are not
    restated here and could not be: this record has no field for them.

    ``density`` and ``specific_heat`` carry **no default**. An unstated property
    stays unstated, and a material declared without a density would silently
    become a massless one.
    """

    conductor_material: cmat.ConductorMaterial
    density: Quantity
    specific_heat: Quantity
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.conductor_material, cmat.ConductorMaterial):
            raise InvalidScientificProblem(
                f"a thermophysical conductor composes an existing "
                f"ConductorMaterial, got "
                f"{type(self.conductor_material).__name__}"
            )
        source = str(self.source).strip()
        if not source:
            raise InvalidScientificProblem(
                f"the thermophysical property set of "
                f"{self.conductor_material.name!r} requires a non-empty "
                f"provenance source; a property set with no stated origin is "
                f"not a declaration"
            )
        object.__setattr__(self, "source", source)
        _require_positive(
            self.density, DENSITY_UNIT,
            f"material {self.conductor_material.name!r} density",
        )
        _require_positive(
            self.specific_heat, SPECIFIC_HEAT_UNIT,
            f"material {self.conductor_material.name!r} specific_heat",
        )

    @property
    def name(self) -> str:
        """One authority for the material's name: the electrical record."""
        return self.conductor_material.name

    @property
    def density_si(self) -> float:
        return self.density.magnitude_in(DENSITY_UNIT)

    @property
    def specific_heat_si(self) -> float:
        return self.specific_heat.magnitude_in(SPECIFIC_HEAT_UNIT)

    def thermal_parameters(self) -> tuple[ScientificParameter, ...]:
        return (
            ScientificParameter(
                name=DENSITY,
                value=self.density,
                description=(
                    f"Declared density of material {self.name!r}. "
                    f"Source: {self.source}"
                ),
            ),
            ScientificParameter(
                name=SPECIFIC_HEAT,
                value=self.specific_heat,
                description=(
                    f"Declared specific heat of material {self.name!r}. "
                    f"Source: {self.source}"
                ),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": THERMOPHYSICAL_CONDUCTOR_SCHEMA,
            # The whole electrical record travels, not a name pointing at a
            # catalogue: a payload that named a library entry would mean
            # something different after the library changed.
            "conductor_material": self.conductor_material.to_dict(),
            "density": self.density.to_dict(),
            "specific_heat": self.specific_heat.to_dict(),
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ThermophysicalConductor":
        require_schema(payload, THERMOPHYSICAL_CONDUCTOR_SCHEMA)
        return cls(
            conductor_material=cmat.material_from_dict(
                payload["conductor_material"]
            ),
            density=Quantity.from_dict(payload["density"]),
            specific_heat=Quantity.from_dict(payload["specific_heat"]),
            source=payload["source"],
        )


#: Handbook thermophysical properties, paired with the **existing** electrical
#: catalogue entries by object reference. No electrical number appears here.
COPPER_THERMOPHYSICAL = ThermophysicalConductor(
    conductor_material=cmat.COPPER,
    density=Quantity(8960.0, DENSITY_UNIT),
    specific_heat=Quantity(385.0, SPECIFIC_HEAT_UNIT),
    source=(
        "standard handbook thermophysical properties of pure metals near "
        "room temperature; copper 8960 kg/m^3, 385 J/(kg*K). Paired with the "
        "electrical record engcore.domains.electrical.conductor_material."
        "COPPER by reference, not restated."
    ),
)

ALUMINIUM_THERMOPHYSICAL = ThermophysicalConductor(
    conductor_material=cmat.ALUMINIUM,
    density=Quantity(2700.0, DENSITY_UNIT),
    specific_heat=Quantity(897.0, SPECIFIC_HEAT_UNIT),
    source=(
        "standard handbook thermophysical properties of pure metals near "
        "room temperature; aluminium 2700 kg/m^3, 897 J/(kg*K). Paired with "
        "the electrical record engcore.domains.electrical.conductor_material."
        "ALUMINIUM by reference, not restated."
    ),
)


# =====================================================================
# Problem statement
# =====================================================================

def build_thermal_mass_problem(
    conductor: cmat.MaterialConductor,
    material: ThermophysicalConductor,
    *,
    problem_id: str | None = None,
) -> ScientificProblem:
    """The universal problem statement for one ``C = rho_m L A c_p`` evaluation.

    The geometry is read from the **same** :class:`~engcore.domains.electrical.
    conductor_material.MaterialConductor` the resistance is computed from, so
    the length and the area that set ``R`` and the length and the area that set
    ``C`` are one declaration and cannot drift apart.
    """
    if not isinstance(conductor, cmat.MaterialConductor):
        raise InvalidScientificProblem(
            "a thermal mass problem requires a MaterialConductor"
        )
    if not isinstance(material, ThermophysicalConductor):
        raise InvalidScientificProblem(
            "a thermal mass problem requires a ThermophysicalConductor"
        )
    if conductor.material is not material.conductor_material:
        raise InvalidScientificProblem(
            f"conductor {conductor.component_id!r} declares material "
            f"{conductor.material.name!r} while the thermophysical set "
            f"describes {material.name!r}; one physical object has one "
            f"material, and this pack refuses to compute a thermal mass from "
            f"a property set that belongs to something else"
        )
    return ScientificProblem(
        problem_id=problem_id or f"conductor_thermal_mass:{conductor.component_id}",
        name=f"Thermal mass of {conductor.component_id}",
        description="Evaluate C = rho_m L A c_p for one conductor.",
        parameters=(
            ScientificParameter(
                name=cmat.MATERIAL,
                value=CategoricalValue(material.name),
                description=(
                    "Which material's declared property set was evaluated. "
                    "The vocabulary is empty for the same reason the "
                    "electrical resistivity problem's is: library membership "
                    "is not a property of this conductor."
                ),
            ),
            *material.thermal_parameters(),
            *conductor.geometry_parameters(),
        ),
        models=(
            ModelReference(
                CONDUCTOR_THERMAL_MASS_MODEL.model_id,
                CONDUCTOR_THERMAL_MASS_MODEL.version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def assess_thermal_mass_validity(
    conductor: cmat.MaterialConductor, material: ThermophysicalConductor
):
    """Is the thermal-mass model applicable to this declaration? **Reported.**"""
    problem = build_thermal_mass_problem(conductor, material)
    return CONDUCTOR_THERMAL_MASS_MODEL.assess_validity(problem.validity_context())


# =====================================================================
# Evaluator
# =====================================================================

THERMAL_MASS_SOLVER_ID = "engcore.propulsion.conductor_thermal_mass_evaluator"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.float"


@dataclass(frozen=True)
class PreparedThermalMass:
    conductor: cmat.MaterialConductor
    material: ThermophysicalConductor
    realization: ModelRealizationDefinition


class ConductorThermalMassSolver:
    """Evaluates ``C = rho_m L A c_p`` for one conductor. Satisfies the protocol.

    Bound by problem id, exactly as every sibling evaluator in this repository
    binds its declaration, and refusing a rebind to a different physical object
    for the same reason.
    """

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[cmat.MaterialConductor, ThermophysicalConductor]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(THERMAL_MASS_SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return thermal_mass_solver_capabilities()

    def bind_conductor(
        self,
        conductor: cmat.MaterialConductor,
        material: ThermophysicalConductor,
        problem_id: str,
    ) -> None:
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0] != conductor:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different conductor; "
                f"silently swapping the object behind a problem id would let "
                f"two results claim one identity while describing different "
                f"systems"
            )
        self._bound[key] = (conductor, material)

    @staticmethod
    def verify_problem_matches_conductor(
        problem: ScientificProblem,
        conductor: cmat.MaterialConductor,
        material: ThermophysicalConductor,
    ) -> None:
        for name, declared in (
            (cmat.LENGTH, conductor.length),
            (cmat.CROSS_SECTIONAL_AREA, conductor.cross_sectional_area),
            (DENSITY, material.density),
            (SPECIFIC_HEAT, material.specific_heat),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound declaration carries {declared}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        return any(
            reference.model_id == CONDUCTOR_THERMAL_MASS_MODEL.model_id
            for reference in problem.models
        )

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = CONDUCTOR_THERMAL_MASS_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no conductor is bound to problem {problem.problem_id!r}; "
                f"call bind_conductor first"
            )
        conductor, material = bound
        self.verify_problem_matches_conductor(problem, conductor, material)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedThermalMass(
                conductor=conductor, material=material, realization=realization
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        payload: PreparedThermalMass = prepared.payload
        started = time.perf_counter()
        volume = payload.conductor.length_m * payload.conductor.area_m2
        capacity = payload.material.density_si * volume * payload.material.specific_heat_si
        return RawSolverOutput(
            values={HEAT_CAPACITY_METRIC: capacity},
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={"volume_m3": volume},
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            HEAT_CAPACITY_METRIC: Quantity(
                raw.values[HEAT_CAPACITY_METRIC], HEAT_CAPACITY_UNIT
            )
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Recompute the product from the problem record, not from the payload.

        A check that re-multiplied the same four floats the solve used would be
        a check that cannot fail. This one reads the four values back out of the
        **posed problem** and in their declared units, so a solve that read a
        different declaration, or converted a unit wrongly, is caught.
        """
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="thermal_mass_product",
                        outcome=ValidationOutcome.FAIL,
                        detail="the solve did not succeed; no product exists",
                    ),
                )
            )
        problem = prepared.problem
        expected = (
            problem.parameter(DENSITY).value.magnitude_in(DENSITY_UNIT)
            * problem.parameter(cmat.LENGTH).value.magnitude_in(cmat.LENGTH_UNIT)
            * problem.parameter(cmat.CROSS_SECTIONAL_AREA).value.magnitude_in(
                cmat.AREA_UNIT
            )
            * problem.parameter(SPECIFIC_HEAT).value.magnitude_in(SPECIFIC_HEAT_UNIT)
        )
        actual = raw.values[HEAT_CAPACITY_METRIC]
        residual = abs(actual - expected)
        tolerance = 1e-12 * max(abs(expected), 1.0)
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="thermal_mass_product",
                    outcome=(
                        ValidationOutcome.PASS
                        if residual <= tolerance
                        else ValidationOutcome.FAIL
                    ),
                    # Establishes no level: this verifies the computation
                    # against the record it claims to have used. It is not a
                    # physical validation of the handbook properties.
                    establishes=None,
                    residual=residual,
                    tolerance=tolerance,
                    detail=(
                        f"|C - rho_m L A c_p| = {residual:.3e} J/K, recomputed "
                        f"from the posed problem's own declared parameters. "
                        f"Verification against the record, not a physical "
                        f"validation."
                    ),
                ),
            )
        )
