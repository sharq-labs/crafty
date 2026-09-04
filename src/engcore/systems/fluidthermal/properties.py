"""The two property claims that close the Fluid ↔ Thermal cycle.

`FT-SCALAR-COUPLING`. Neither of these is a coupling. Each is a *scientific
claim* that happens to sit on one edge of a cycle, stated with the contracts
that already exist — one :class:`ScientificModelDefinition`, one
:class:`ModelRealizationDefinition`, one problem builder, one evaluator —
structurally file-for-file the shape of
``src/engcore/domains/electrical/material.py``.

    P — gas diffusivity           D(T)   = D_ref (T / T_ref)^n
    W — wall conductance          hA(Φ_D) = (ρ c_p) Φ_D d

**There is no constitutive-relation IR here, and none is needed.** A property
that requires computation *is* a scientific claim computed by a realization.
``ModelInputSpec`` already types the requirement (name, source kind, dimension,
value kind, role, required-ness), ``ModelOutputSpec`` already types the
identity, and ``ProvenanceRecord.bindings`` already records which realization
computed it. A second hierarchy beside those would duplicate every one of those
facts somewhere the existing validity, capability and provenance machinery
could not see them. That argument is not new: ``electrical/material.py`` made
it first, and this module is the second consumer that did not need the
hierarchy either — which is the only kind of evidence that the absence is
right.

WHY W EXISTS AT ALL, AND WHY IT IS A DECLARED MODEL
---------------------------------------------------
``Φ_D`` carries ``m**2/s``: the Fluid domain's field is dimensionless and
claims no thermodynamic scale, deliberately and permanently. ``hA`` carries
``watt/kelvin``. Something has to restore the scale, and the only two honest
places for it are a declared model or a hidden multiplication inside the
coupling loop. ``QuantityDependency`` forces the first: its ``unit_exemplar``
is dimension-checked at both endpoints, so a ``m**2/s``-valued edge simply
cannot be wired into a ``watt/kelvin`` endpoint. The conversion therefore has
to exist as something with a version, a validity domain, declared parameters
and a provenance binding. The contract doing its job is what produced this
module.

``ρ c_p`` (a volumetric heat capacity) and ``d`` (the depth of the
two-dimensional slice, per unit of which the Fluid domain reports everything)
are its two declared parameters. Both are physical facts about the system being
modelled, both are on the record, and neither is a fudge factor: change either
and the coupled answer moves in the way the algebra says it must.

WHAT IS DELIBERATELY ABSENT
---------------------------
No coupling, no iteration, no relaxation, no tolerance, no knowledge of where
``T`` or ``Φ_D`` comes from. Each model declares its input as an externally
supplied ``STATE`` variable and says nothing about the supplier — because any
supplier satisfies it, exactly as any heat source satisfies a lumped balance.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

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
    ValidityAssessment,
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
    "CONDUCTANCE_UNIT",
    "DEPTH",
    "DIFFUSIVITY_METRIC",
    "DIFFUSIVITY_UNIT",
    "EFFLUX_UNIT",
    "GasDiffusivity",
    "POWER_LAW_DIFFUSIVITY_MODEL",
    "POWER_LAW_DIFFUSIVITY_REALIZATION",
    "REFERENCE_DIFFUSIVITY",
    "REFERENCE_TEMPERATURE",
    "TEMPERATURE",
    "TEMPERATURE_EXPONENT",
    "TEMPERATURE_UNIT",
    "VOLUMETRIC_HEAT_CAPACITY",
    "WALL_CONDUCTANCE_METRIC",
    "WALL_CONDUCTANCE_MODEL",
    "WALL_CONDUCTANCE_REALIZATION",
    "WALL_EFFLUX",
    "WallCoupling",
    "DiffusivityPropertySolver",
    "WallConductanceSolver",
    "assess_diffusivity_validity",
    "build_diffusivity_problem",
    "build_wall_conductance_problem",
    "property_model_registry",
    "property_realizations",
    "property_solver_capabilities",
]

# --- units -------------------------------------------------------------------
DIFFUSIVITY_UNIT = "m**2/s"
TEMPERATURE_UNIT = "kelvin"
EFFLUX_UNIT = "m**2/s"
CONDUCTANCE_UNIT = "watt/kelvin"
VOLUMETRIC_HEAT_CAPACITY_UNIT = "joule/(meter**3*kelvin)"
LENGTH_UNIT = "meter"
DIMENSIONLESS = "dimensionless"

# --- quantity names ----------------------------------------------------------
REFERENCE_DIFFUSIVITY = "reference_diffusivity"
REFERENCE_TEMPERATURE = "reference_temperature"
TEMPERATURE_EXPONENT = "temperature_exponent"
TEMPERATURE = "temperature"
DIFFUSIVITY_METRIC = "diffusivity"

VOLUMETRIC_HEAT_CAPACITY = "volumetric_heat_capacity"
DEPTH = "depth"
WALL_EFFLUX = "wall_efflux"
WALL_CONDUCTANCE_METRIC = "wall_conductance"

MODEL_VERSION = "0.1.0"

# --- capabilities, declared here and nowhere else ----------------------------

#: What P provides.
TEMPERATURE_DEPENDENT_DIFFUSIVITY = ScientificCapability.parse(
    "fluids:temperature_dependent_diffusivity"
)

#: What P *needs*, declared by identifier. Nothing thermal is imported by this
#: module — the same discipline, and the same asymmetry, `electrical/material`
#: recorded: `D(T)` is undefined without a temperature, while the wall
#: conductance relation is satisfied by any wall efflux whatever produced it,
#: so W declares no matching requirement and would be lying if it did.
REQUIRED_BODY_TEMPERATURE = ScientificCapability.parse("thermal:body_temperature")

#: What W provides.
WALL_EXCHANGE_CONDUCTANCE = ScientificCapability.parse(
    "thermal:wall_exchange_conductance"
)

#: Declared validity of the power-law form. Below ~200 K the Fuller correlation
#: is not evidence-backed for common binary gas pairs and above ~1500 K
#: dissociation and non-ideality break the assumptions the exponent came from.
DIFFUSIVITY_MIN_TEMPERATURE = Quantity(200.0, TEMPERATURE_UNIT)
DIFFUSIVITY_MAX_TEMPERATURE = Quantity(1500.0, TEMPERATURE_UNIT)


_P_ASSUMPTIONS = (
    "binary-gas power-law temperature scaling about a reference state",
    "the exponent is a property of the gas pair, declared and not fitted here",
    "pressure is constant and is not a declared input; the Fuller correlation's "
    "1/p dependence is absorbed into the reference value",
    "isotropic scalar diffusivity; no tensor and no composition dependence",
    "no self-consistency loop: T is supplied, never inferred from D",
)

POWER_LAW_DIFFUSIVITY_MODEL = ScientificModelDefinition(
    model_id="fluids.material.power_law_gas_diffusivity",
    version=MODEL_VERSION,
    name="Power-law temperature-dependent gas diffusivity",
    domain="fluids",
    # CONSTITUTIVE_MODEL: a material response relation. Not a conservation law,
    # and not a correlation fitted to a specific device by this repository.
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Binary-gas scalar diffusivity as a power law in absolute "
        "temperature: D(T) = D_ref (T / T_ref)^n, with n = 1.75 the Fuller "
        "correlation's temperature exponent."
    ),
    inputs=(
        ModelInputSpec(
            name=REFERENCE_DIFFUSIVITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=DIFFUSIVITY_UNIT,
            description="Diffusivity at the reference temperature; positive.",
        ),
        ModelInputSpec(
            name=REFERENCE_TEMPERATURE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TEMPERATURE_UNIT,
            description="Absolute temperature at which the reference holds.",
        ),
        ModelInputSpec(
            name=TEMPERATURE_EXPONENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=DIMENSIONLESS,
            description=(
                "Temperature exponent n. 1.75 for the Fuller binary-gas "
                "correlation; 1.5 for rigid-sphere kinetic theory. Both are "
                "representable and neither is fitted here."
            ),
        ),
        ModelInputSpec(
            name=TEMPERATURE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TEMPERATURE_UNIT,
            role=VariableRole.STATE,
            description="Absolute gas temperature; supplied, never chosen.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=DIFFUSIVITY_METRIC,
            unit_exemplar=DIFFUSIVITY_UNIT,
            description="Scalar diffusivity at the supplied temperature.",
        ),
    ),
    assumptions=_P_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=TEMPERATURE,
                minimum=DIFFUSIVITY_MIN_TEMPERATURE,
                maximum=DIFFUSIVITY_MAX_TEMPERATURE,
                description=(
                    "The band the power-law exponent is evidence-backed over. "
                    "Outside it the form is not merely inaccurate, the "
                    "assumptions it was derived under fail."
                ),
            ),
            RangeCondition(
                name=REFERENCE_DIFFUSIVITY,
                minimum=Quantity(0.0, DIFFUSIVITY_UNIT),
                minimum_inclusive=False,
                description="Strictly positive; zero is not diffusion.",
            ),
        ),
        description="Binary-gas diffusion at moderate temperature and pressure.",
    ),
    # SELF_CONSISTENT and nothing stronger: this repository has measured no
    # gas pair and curates no reference set. A citation will not be invented to
    # dress that up.
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


_W_ASSUMPTIONS = (
    "the two-dimensional transport field is a slice of uniform depth d, and "
    "every extensive quantity scales linearly with that depth",
    "the supplied field is INTERPRETED as a normalized excess "
    "(T - T_amb)/(T_w - T_amb) of the transported scalar. This is an "
    "interpretive convention of this claim, NOT a property established of any "
    "supplier: nothing in the composition defines the normalization reference "
    "(T_w - T_amb), nothing reconciles it with the body's own excess "
    "(T_body - T_amb), and no record could carry that reconciliation today",
    "no conservation is claimed ACROSS the interface. This model relates a "
    "wall efflux to a conductance; it does not assert that the energy leaving "
    "the body equals the energy entering the transport slice, and the two "
    "participants' sources are unrelated",
    "the supplying field may be a manufactured-solution benchmark whose "
    "interior is pinned by a non-physical volumetric source term. Only the "
    "wall efflux is used, and only its dependence on the transport "
    "coefficient is load-bearing",
    "constant volumetric heat capacity over the temperature range considered",
    "the whole wall efflux enters the body; no bypass and no second path",
    "no radiation and no phase change",
)

WALL_CONDUCTANCE_MODEL = ScientificModelDefinition(
    model_id="fluids.thermal.wall_efflux_conductance",
    version=MODEL_VERSION,
    name="Wall exchange conductance from a boundary-integrated efflux",
    domain="fluids",
    # CONSTITUTIVE_MODEL, not FUNDAMENTAL_RELATION: it is not a conservation
    # statement. It is the declared relation between a normalized transport
    # field's wall efflux and the extensive exchange conductance of the body
    # that field describes, and it is true only under the assumptions listed.
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Extensive wall exchange conductance of a body whose normalized "
        "transport field has boundary-integrated diffusive efflux Phi_D: "
        "hA = (rho c_p) Phi_D d."
    ),
    inputs=(
        ModelInputSpec(
            name=VOLUMETRIC_HEAT_CAPACITY,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=VOLUMETRIC_HEAT_CAPACITY_UNIT,
            description="rho c_p of the transporting medium; positive.",
        ),
        ModelInputSpec(
            name=DEPTH,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=LENGTH_UNIT,
            description=(
                "Depth of the two-dimensional slice, per unit of which the "
                "transport domain reports its efflux; positive."
            ),
        ),
        ModelInputSpec(
            name=WALL_EFFLUX,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=EFFLUX_UNIT,
            role=VariableRole.STATE,
            description=(
                "Boundary-integrated outward diffusive efflux of the "
                "normalized field, per unit depth. Supplied; its producer is "
                "not part of this claim."
            ),
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=WALL_CONDUCTANCE_METRIC,
            unit_exemplar=CONDUCTANCE_UNIT,
            description="Extensive conductance from the body to its ambient.",
        ),
    ),
    assumptions=_W_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=WALL_EFFLUX,
                minimum=Quantity(0.0, EFFLUX_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive: a non-positive efflux is either an "
                    "influx or no exchange at all, and neither is a "
                    "conductance to an ambient. The sign convention this "
                    "depends on is a declared BoundaryOrientation on the "
                    "producing domain, not a comment here."
                ),
            ),
            RangeCondition(
                name=VOLUMETRIC_HEAT_CAPACITY,
                minimum=Quantity(0.0, VOLUMETRIC_HEAT_CAPACITY_UNIT),
                minimum_inclusive=False,
                description="Strictly positive volumetric heat capacity.",
            ),
        ),
        description="Scale restoration for a normalized 2D transport slice.",
    ),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


POWER_LAW_DIFFUSIVITY_REALIZATION = ModelRealizationDefinition(
    realization_id="fluids.material.power_law_gas_diffusivity.closed_form",
    version="0.1.0",
    model=ModelReference(
        POWER_LAW_DIFFUSIVITY_MODEL.model_id, POWER_LAW_DIFFUSIVITY_MODEL.version
    ),
    formulation=ModelFormulation.ALGEBRAIC,
    name="Direct evaluation of the power-law expression",
    description=(
        "Evaluates D_ref (T/T_ref)^n once, at a supplied temperature. No "
        "iteration and no system solve."
    ),
    provided_capabilities=frozenset({TEMPERATURE_DEPENDENT_DIFFUSIVITY}),
    required_capabilities=frozenset({REQUIRED_BODY_TEMPERATURE}),
    required_solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=(
        "single evaluation at one supplied temperature; no self-consistency "
        "loop between diffusivity and temperature is performed here",
        "exact for the declared power law; no discretization error exists",
    ),
    implementation=ImplementationReference(
        implementation_id="engcore.systems.fluidthermal.properties",
        version="0.1.0",
        reference="power-law closed form; see module docstring",
    ),
)

WALL_CONDUCTANCE_REALIZATION = ModelRealizationDefinition(
    realization_id="fluids.thermal.wall_efflux_conductance.closed_form",
    version="0.1.0",
    model=ModelReference(
        WALL_CONDUCTANCE_MODEL.model_id, WALL_CONDUCTANCE_MODEL.version
    ),
    formulation=ModelFormulation.ALGEBRAIC,
    name="Direct evaluation of the scale-restoration product",
    description="Evaluates (rho c_p) Phi_D d once, at a supplied efflux.",
    provided_capabilities=frozenset({WALL_EXCHANGE_CONDUCTANCE}),
    # No required capability, and that absence is a result rather than an
    # omission: any producer of a wall efflux satisfies this claim, so a
    # declared requirement on the Fluid domain specifically would be false.
    required_capabilities=frozenset(),
    required_solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=(
        "single evaluation at one supplied efflux",
        "exact for the declared product; no discretization error exists",
    ),
    implementation=ImplementationReference(
        implementation_id="engcore.systems.fluidthermal.properties",
        version="0.1.0",
        reference="scale-restoration product; see module docstring",
    ),
)


def property_model_registry() -> ModelRegistry:
    """A fresh registry. No global singleton exists."""
    return ModelRegistry((POWER_LAW_DIFFUSIVITY_MODEL, WALL_CONDUCTANCE_MODEL))


def property_realizations() -> RealizationRegistry:
    """A fresh registry. No global singleton exists."""
    return RealizationRegistry(
        (POWER_LAW_DIFFUSIVITY_REALIZATION, WALL_CONDUCTANCE_REALIZATION)
    )


def property_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({CoreCapabilities.ALGEBRAIC})


# =====================================================================
# Declarations
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
class GasDiffusivity:
    """One declared gas whose diffusivity depends on its temperature.

    Carries no temperature. A temperature is a *state*, and freezing one into
    a material declaration is the configuration/state conflation the sibling
    electrical property module was built to avoid committing.
    """

    medium_id: str
    reference_diffusivity: Quantity
    reference_temperature: Quantity
    temperature_exponent: Quantity

    def __post_init__(self) -> None:
        medium_id = str(self.medium_id).strip()
        if not medium_id:
            raise InvalidScientificProblem("gas diffusivity requires a medium_id")
        object.__setattr__(self, "medium_id", medium_id)
        _positive(self.reference_diffusivity, DIFFUSIVITY_UNIT, REFERENCE_DIFFUSIVITY)
        _positive(self.reference_temperature, TEMPERATURE_UNIT, REFERENCE_TEMPERATURE)
        if not isinstance(self.temperature_exponent, Quantity):
            raise InvalidScientificProblem(
                f"{TEMPERATURE_EXPONENT} must be a dimensionless Quantity"
            )
        exponent = self.temperature_exponent.magnitude_in(DIMENSIONLESS)
        if not math.isfinite(exponent):
            raise InvalidScientificProblem(
                f"{TEMPERATURE_EXPONENT} must be finite, got {exponent!r}"
            )

    @property
    def d_ref_m2_s(self) -> float:
        return self.reference_diffusivity.magnitude_in(DIFFUSIVITY_UNIT)

    @property
    def t_ref_k(self) -> float:
        return self.reference_temperature.magnitude_in(TEMPERATURE_UNIT)

    @property
    def exponent(self) -> float:
        return self.temperature_exponent.magnitude_in(DIMENSIONLESS)


@dataclass(frozen=True)
class WallCoupling:
    """One declared scale restoration: the medium's rho c_p and the slice depth.

    Carries no efflux, for the same reason :class:`GasDiffusivity` carries no
    temperature.
    """

    medium_id: str
    volumetric_heat_capacity: Quantity
    depth: Quantity

    def __post_init__(self) -> None:
        medium_id = str(self.medium_id).strip()
        if not medium_id:
            raise InvalidScientificProblem("wall coupling requires a medium_id")
        object.__setattr__(self, "medium_id", medium_id)
        _positive(
            self.volumetric_heat_capacity,
            VOLUMETRIC_HEAT_CAPACITY_UNIT,
            VOLUMETRIC_HEAT_CAPACITY,
        )
        _positive(self.depth, LENGTH_UNIT, DEPTH)

    @property
    def rho_cp_j_per_m3_k(self) -> float:
        return self.volumetric_heat_capacity.magnitude_in(
            VOLUMETRIC_HEAT_CAPACITY_UNIT
        )

    @property
    def depth_m(self) -> float:
        return self.depth.magnitude_in(LENGTH_UNIT)


# =====================================================================
# Problem statements
# =====================================================================

def build_diffusivity_problem(
    medium: GasDiffusivity, *, problem_id: str | None = None
) -> ScientificProblem:
    """The universal problem statement for one diffusivity evaluation.

    ``temperature`` is a **variable with role STATE** and carries no value: the
    problem states that a temperature is required and what dimension it has,
    without asserting which one. Where the value comes from is a separate fact
    living in a separate record — a :class:`QuantityDependency`.
    """
    return ScientificProblem(
        problem_id=problem_id or f"fluid-diffusivity-{medium.medium_id}",
        name=f"Temperature-dependent diffusivity of {medium.medium_id}",
        description="Evaluate D(T) for one medium at one supplied temperature.",
        variables=(
            ScientificVariable(
                name=TEMPERATURE,
                unit=TEMPERATURE_UNIT,
                role=VariableRole.STATE,
                description="Gas temperature; supplied, not chosen.",
            ),
        ),
        parameters=(
            ScientificParameter(
                name=REFERENCE_DIFFUSIVITY,
                value=medium.reference_diffusivity,
                description="Diffusivity at the reference temperature.",
            ),
            ScientificParameter(
                name=REFERENCE_TEMPERATURE,
                value=medium.reference_temperature,
                description="Temperature at which the reference value holds.",
            ),
            ScientificParameter(
                name=TEMPERATURE_EXPONENT,
                value=medium.temperature_exponent,
                description="Power-law temperature exponent.",
            ),
        ),
        models=(
            ModelReference(
                POWER_LAW_DIFFUSIVITY_MODEL.model_id,
                POWER_LAW_DIFFUSIVITY_MODEL.version,
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
        validation_requirements=frozenset({"power_law_identity"}),
    )


def build_wall_conductance_problem(
    coupling: WallCoupling, *, problem_id: str | None = None
) -> ScientificProblem:
    """The universal problem statement for one scale restoration."""
    return ScientificProblem(
        problem_id=problem_id or f"wall-conductance-{coupling.medium_id}",
        name=f"Wall exchange conductance of {coupling.medium_id}",
        description=(
            "Evaluate hA = (rho c_p) Phi_D d for one medium at one supplied "
            "boundary-integrated efflux."
        ),
        variables=(
            ScientificVariable(
                name=WALL_EFFLUX,
                unit=EFFLUX_UNIT,
                role=VariableRole.STATE,
                description=(
                    "Boundary-integrated outward diffusive efflux per unit "
                    "depth; supplied, not chosen."
                ),
            ),
        ),
        parameters=(
            ScientificParameter(
                name=VOLUMETRIC_HEAT_CAPACITY,
                value=coupling.volumetric_heat_capacity,
                description="rho c_p of the transporting medium.",
            ),
            ScientificParameter(
                name=DEPTH,
                value=coupling.depth,
                description="Depth of the two-dimensional slice.",
            ),
        ),
        models=(
            ModelReference(
                WALL_CONDUCTANCE_MODEL.model_id, WALL_CONDUCTANCE_MODEL.version
            ),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
        validation_requirements=frozenset({"scale_restoration_identity"}),
    )


def assess_diffusivity_validity(
    problem: ScientificProblem, temperature: Quantity
) -> ValidityAssessment:
    """Is the power law applicable at this temperature? **Validity, not validation.**

    Note what has to happen for this to work at all: ``temperature`` is a
    *variable*, and :meth:`ScientificProblem.validity_context` is built from
    *parameters*, so the state value must be supplied explicitly through
    ``extra=``. A validity condition on a state coordinate is never automatic.
    That is the sibling electrical module's finding, met a second time here and
    carried forward rather than worked around.
    """
    context = problem.validity_context(extra={TEMPERATURE: temperature})
    return POWER_LAW_DIFFUSIVITY_MODEL.assess_validity(context)


# =====================================================================
# Evaluators
# =====================================================================

DIFFUSIVITY_SOLVER_ID = "engcore.fluids.power_law_diffusivity_evaluator"
CONDUCTANCE_SOLVER_ID = "engcore.fluids.wall_conductance_evaluator"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.float"


@dataclass(frozen=True)
class PreparedDiffusivityEvaluation:
    medium: GasDiffusivity
    realization: ModelRealizationDefinition
    temperature_k: float


@dataclass(frozen=True)
class PreparedConductanceEvaluation:
    coupling: WallCoupling
    realization: ModelRealizationDefinition
    efflux_m2_s: float


class DiffusivityPropertySolver:
    """Evaluates D(T) for one medium. Satisfies ScientificSolver.

    It is a solver in the platform's sense — prepared problem in, raw output
    out, nameable in provenance — even though the computation is one line of
    arithmetic. Making it a special case would mean the evaluation could not
    appear in an :class:`ExecutionBinding`, and "which realization computed
    this diffusivity" would go unrecorded.
    """

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[GasDiffusivity, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(DIFFUSIVITY_SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return property_solver_capabilities()

    def bind_medium(
        self, medium: GasDiffusivity, problem_id: str, *, temperature: Quantity
    ) -> None:
        """Associate a medium and a supplied temperature with a problem id.

        Rebinding a **different temperature** under one problem id is the
        normal case: one medium at two temperatures is one system at two
        states. Rebinding a different *medium* is refused.
        """
        if not isinstance(medium, GasDiffusivity):
            raise InvalidScientificProblem("bind_medium expects a GasDiffusivity")
        kelvin = temperature.magnitude_in(TEMPERATURE_UNIT)
        if not math.isfinite(kelvin):
            raise InvalidScientificProblem("temperature must be finite")
        if kelvin <= 0.0:
            raise InvalidScientificProblem(
                f"temperature must be a positive absolute temperature, got "
                f"{kelvin!r} K — the power law is undefined at and below "
                f"absolute zero"
            )
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0] != medium:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different medium"
            )
        self._bound[key] = (medium, kelvin)

    @staticmethod
    def verify_problem_matches_medium(
        problem: ScientificProblem, medium: GasDiffusivity
    ) -> None:
        """Refuse a problem describing a different medium than the bound one."""
        for name, declared in (
            (REFERENCE_DIFFUSIVITY, medium.reference_diffusivity),
            (REFERENCE_TEMPERATURE, medium.reference_temperature),
            (TEMPERATURE_EXPONENT, medium.temperature_exponent),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound medium declares {declared}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        """Matched on the model reference the problem carries, not on a
        capability alone: ``core:algebraic`` is true of countless relations."""
        wanted = (
            POWER_LAW_DIFFUSIVITY_MODEL.model_id,
            POWER_LAW_DIFFUSIVITY_MODEL.version,
        )
        return any(model.key == wanted for model in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = POWER_LAW_DIFFUSIVITY_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no medium is bound to problem {problem.problem_id!r}; call "
                f"bind_medium first"
            )
        medium, kelvin = bound
        self.verify_problem_matches_medium(problem, medium)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedDiffusivityEvaluation(
                medium=medium, realization=realization, temperature_k=kelvin
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        evaluation: PreparedDiffusivityEvaluation = prepared.payload
        medium = evaluation.medium
        started = time.perf_counter()
        diffusivity = medium.d_ref_m2_s * (
            evaluation.temperature_k / medium.t_ref_k
        ) ** medium.exponent
        return RawSolverOutput(
            values={DIFFUSIVITY_METRIC: diffusivity},
            # NOT_APPLICABLE, not CONVERGED: a direct evaluation neither
            # converges nor fails to.
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "temperature_k": evaluation.temperature_k,
                "temperature_ratio": evaluation.temperature_k / medium.t_ref_k,
            },
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            DIFFUSIVITY_METRIC: Quantity(
                raw.values[DIFFUSIVITY_METRIC], DIFFUSIVITY_UNIT
            )
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Check the evaluated value against the relation it claims to compute.

        Verification of an expression against itself in logarithmic form:
        ``ln(D/D_ref) - n ln(T/T_ref)`` must vanish. Not circular — a wrong
        exponent, a flipped ratio or a wrong reference each leave it non-zero —
        but it compares a closed form against the relation the closed form came
        from, with no independent reference, and it therefore ``establishes``
        nothing. That is the same restraint ``thermal_lumped`` applies to its
        own balance residual.
        """
        evaluation: PreparedDiffusivityEvaluation = prepared.payload
        medium = evaluation.medium
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="power_law_identity",
                        outcome=ValidationOutcome.FAIL,
                        detail="the evaluation did not succeed",
                    ),
                )
            )
        value = raw.values[DIFFUSIVITY_METRIC]
        residual = abs(
            math.log(value / medium.d_ref_m2_s)
            - medium.exponent
            * math.log(evaluation.temperature_k / medium.t_ref_k)
        )
        tolerance = 1e-12
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="power_law_identity",
                    outcome=(
                        ValidationOutcome.PASS
                        if residual <= tolerance
                        else ValidationOutcome.FAIL
                    ),
                    establishes=None,
                    residual=residual,
                    tolerance=tolerance,
                    detail=(
                        f"|ln(D/D_ref) - n ln(T/T_ref)| = {residual:.3e}. "
                        f"Verification of the closed form against the relation "
                        f"it computes; no physical validation."
                    ),
                ),
            )
        )


class WallConductanceSolver:
    """Evaluates hA = (rho c_p) Phi_D d. Satisfies ScientificSolver."""

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[WallCoupling, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(CONDUCTANCE_SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return property_solver_capabilities()

    def bind_medium(
        self, coupling: WallCoupling, problem_id: str, *, wall_efflux: Quantity
    ) -> None:
        if not isinstance(coupling, WallCoupling):
            raise InvalidScientificProblem("bind_medium expects a WallCoupling")
        efflux = wall_efflux.magnitude_in(EFFLUX_UNIT)
        if not math.isfinite(efflux):
            raise InvalidScientificProblem("wall efflux must be finite")
        key = str(problem_id)
        existing = self._bound.get(key)
        if existing is not None and existing[0] != coupling:
            raise InvalidScientificProblem(
                f"problem {key!r} is already bound to a different medium"
            )
        self._bound[key] = (coupling, efflux)

    @staticmethod
    def verify_problem_matches_medium(
        problem: ScientificProblem, coupling: WallCoupling
    ) -> None:
        for name, declared in (
            (VOLUMETRIC_HEAT_CAPACITY, coupling.volumetric_heat_capacity),
            (DEPTH, coupling.depth),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound medium declares {declared}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        wanted = (WALL_CONDUCTANCE_MODEL.model_id, WALL_CONDUCTANCE_MODEL.version)
        return any(model.key == wanted for model in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = WALL_CONDUCTANCE_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no medium is bound to problem {problem.problem_id!r}; call "
                f"bind_medium first"
            )
        coupling, efflux = bound
        self.verify_problem_matches_medium(problem, coupling)
        # The declared validity of this claim is checked HERE, before an
        # inadmissible efflux becomes a conductance. A non-positive efflux is
        # an influx or no exchange, and neither is a conductance to an
        # ambient — so it is refused rather than propagated as a negative hA
        # that a lumped body would happily integrate into a runaway.
        assessment = WALL_CONDUCTANCE_MODEL.assess_validity(
            problem.validity_context(
                extra={WALL_EFFLUX: Quantity(efflux, EFFLUX_UNIT)}
            )
        )
        if assessment.violated:
            raise InvalidScientificProblem(
                f"problem {problem.problem_id!r}: the supplied wall efflux "
                f"{efflux!r} {EFFLUX_UNIT} violates this model's declared "
                f"validity condition(s) {sorted(assessment.violated)}; a "
                f"non-positive efflux is an influx or no exchange at all, and "
                f"neither is a conductance to an ambient"
            )
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedConductanceEvaluation(
                coupling=coupling, realization=realization, efflux_m2_s=efflux
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        evaluation: PreparedConductanceEvaluation = prepared.payload
        coupling = evaluation.coupling
        started = time.perf_counter()
        conductance = (
            coupling.rho_cp_j_per_m3_k * evaluation.efflux_m2_s * coupling.depth_m
        )
        return RawSolverOutput(
            values={WALL_CONDUCTANCE_METRIC: conductance},
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={"wall_efflux_m2_s": evaluation.efflux_m2_s},
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {
            WALL_CONDUCTANCE_METRIC: Quantity(
                raw.values[WALL_CONDUCTANCE_METRIC], CONDUCTANCE_UNIT
            )
        }

    def validate(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> ValidationReport:
        """Check the product against a recomputation through the unit algebra.

        The product is re-formed from the typed :class:`Quantity` declarations
        rather than from the floats the solve used, so a unit-conversion defect
        between the declaration and the base-unit accessors would not survive
        it.

        **What it does NOT catch, stated because an earlier draft claimed
        otherwise.** It cannot catch a *mis-declared* constant. Both sides read
        the same two declarations, so a depth declared as one metre when one
        millimetre was meant moves both sides identically and the residual is
        zero. Worse, ``rho_cp`` and ``d`` enter only as a product on both sides
        and in the closed-form reference, so doubling one and halving the other
        is undetectable by any check in this milestone. Both are declaration
        risks with no home in any contract here, and they are recorded rather
        than papered over. Like its sibling ``power_law_identity``, this check
        ``establishes`` nothing.
        """
        evaluation: PreparedConductanceEvaluation = prepared.payload
        coupling = evaluation.coupling
        if not raw.succeeded:
            return ValidationReport(
                checks=(
                    ValidationCheck(
                        name="scale_restoration_identity",
                        outcome=ValidationOutcome.FAIL,
                        detail="the evaluation did not succeed",
                    ),
                )
            )
        typed = (
            coupling.volumetric_heat_capacity
            * Quantity(evaluation.efflux_m2_s, EFFLUX_UNIT)
            * coupling.depth
        )
        residual = abs(
            typed.magnitude_in(CONDUCTANCE_UNIT)
            - raw.values[WALL_CONDUCTANCE_METRIC]
        )
        scale = max(abs(raw.values[WALL_CONDUCTANCE_METRIC]), 1e-30)
        tolerance = 1e-12 * scale
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="scale_restoration_identity",
                    outcome=(
                        ValidationOutcome.PASS
                        if residual <= tolerance
                        else ValidationOutcome.FAIL
                    ),
                    establishes=None,
                    residual=residual,
                    tolerance=tolerance,
                    detail=(
                        f"|(rho c_p)(Phi_D)(d) recomputed through Quantity - "
                        f"reported| = {residual:.3e} W/K. Exercises the unit "
                        f"algebra as well as the arithmetic; no physical "
                        f"validation."
                    ),
                ),
            )
        )
