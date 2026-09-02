"""Temperature-dependent conductor resistance: model, realization, evaluator.

MIN-FOUNDATION-ET. The material half of the minimum electro-thermal consumer:

    R(T) = R_ref * (1 + alpha_TCR * (T - T_ref))

This is a real constitutive claim with a declared temperature validity range,
not a lookup table and not a placeholder.

Why there is no parallel property hierarchy
-------------------------------------------
There is no ``MaterialProperty``, ``PropertyModel``, ``PropertyRequirement`` or
``PropertyBinding`` type here, and none is needed. A property that requires
computation **is a scientific claim computed by a realization**, so it is
stated with the contracts that already exist:

===============================  =========================================
``ScientificModelDefinition``    the claim: what relation holds, when it is
                                 valid, what it needs, what it produces
``ModelInputSpec``               the property *requirement*, already typed:
                                 name, source kind, dimension, value kind,
                                 role, required-ness
``ModelOutputSpec``              the property *identity*: metric + dimension
``ModelRealizationDefinition``   how the claim is computed
``ProvenanceRecord.bindings``    which realization actually computed it
===============================  =========================================

Building a second hierarchy beside these would duplicate every one of those
facts and put the duplicate somewhere the existing validity, capability and
provenance machinery could not see it.

Why this module names a thermal capability but imports no thermal code
----------------------------------------------------------------------
The realization declares ``required_capabilities = {thermal:body_temperature}``
— a genuine scientific dependency, because R(T) is undefined without a
temperature. It declares it **by identifier**, never by importing the thermal
package. Capability identifiers are open and registry-free precisely so that
one domain can require another domain's science without acquiring a code
dependency on it. Nothing in this file imports anything thermal, and a test
asserts it stays that way.

Note the asymmetry, which is a result rather than an oversight: the *thermal*
model does **not** declare a matching requirement on electrical dissipation.
Any heat source satisfies a lumped balance, so a requirement there would be a
false claim. The capability layer can therefore express the
thermal-to-electrical direction and structurally cannot express the
electrical-to-thermal one.

Relationship to ``electrical.dc.resistor_ohm``
----------------------------------------------
That model is **unchanged**, including its declared assumption
``"temperature-independent resistance"``. This model is the falsifiable
alternative to that assumption, not a correction of it, and the two coexisting
is how the boundary of the claim gets recorded. Ohm's law still relates V and I
for the resistor; this model supplies the *value* of R that Ohm's law uses.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

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
    "LINEAR_TCR_MODEL",
    "LINEAR_TCR_REALIZATION",
    "REFERENCE_RESISTANCE",
    "REFERENCE_TEMPERATURE",
    "RESISTANCE_METRIC",
    "RESISTANCE_UNIT",
    "TEMPERATURE",
    "TEMPERATURE_COEFFICIENT",
    "TEMPERATURE_UNIT",
    "TEMPERATURE_DEPENDENT_RESISTANCE",
    "REQUIRED_BODY_TEMPERATURE",
    "TCR_MAX_TEMPERATURE",
    "TCR_MIN_TEMPERATURE",
    "TemperatureDependentConductor",
    "ResistancePropertySolver",
    "assess_resistance_validity",
    "build_resistance_problem",
    "resistance_model_registry",
    "resistance_realizations",
    "resistance_solver_capabilities",
]

# --- units -------------------------------------------------------------------
RESISTANCE_UNIT = "ohm"
TEMPERATURE_UNIT = "kelvin"
TCR_UNIT = "1/kelvin"

# --- quantity names ----------------------------------------------------------
REFERENCE_RESISTANCE = "reference_resistance"
TEMPERATURE_COEFFICIENT = "temperature_coefficient"
REFERENCE_TEMPERATURE = "reference_temperature"
TEMPERATURE = "temperature"

RESISTANCE_METRIC = "resistance"

MODEL_VERSION = "0.1.0"

# --- capabilities ------------------------------------------------------------

#: What science this provides.
TEMPERATURE_DEPENDENT_RESISTANCE = ScientificCapability.parse(
    "electrical:temperature_dependent_resistance"
)

#: What science this *needs*. Declared by identifier; no thermal module is
#: imported anywhere in this file. This is the milestone's one exercised use of
#: ``required_capabilities``, which MODEL0-R left empty and unexercised.
REQUIRED_BODY_TEMPERATURE = ScientificCapability.parse("thermal:body_temperature")

#: The declared validity range of the linear TCR form. Outside it the linear
#: term is not evidence-backed; the model says so rather than extrapolating
#: silently.
TCR_MIN_TEMPERATURE = Quantity(200.0, TEMPERATURE_UNIT)
TCR_MAX_TEMPERATURE = Quantity(450.0, TEMPERATURE_UNIT)


_ASSUMPTIONS = (
    "linear first-order temperature coefficient about a reference state",
    "no self-heating term: T is supplied, never inferred from the resistance",
    "isotropic scalar resistance; no tensor conductivity",
    "no strain, ageing, frequency or magnetic-field dependence",
    "temperature is uniform over the conductor (consistent with a lumped body)",
)


LINEAR_TCR_MODEL = ScientificModelDefinition(
    model_id="electrical.material.linear_tcr_resistance",
    version=MODEL_VERSION,
    name="Linear temperature-coefficient conductor resistance",
    domain="electrical",
    # CONSTITUTIVE_MODEL: a material response relation, neither a conservation
    # law nor a fitted correlation of a specific device.
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Resistance of a conductor as a linear function of its temperature: "
        "R(T) = R_ref (1 + alpha (T - T_ref))."
    ),
    inputs=(
        ModelInputSpec(
            name=REFERENCE_RESISTANCE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=RESISTANCE_UNIT,
            description="Resistance at the reference temperature; positive.",
        ),
        ModelInputSpec(
            name=TEMPERATURE_COEFFICIENT,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TCR_UNIT,
            description=(
                "Temperature coefficient of resistance. Positive for metals, "
                "negative for a thermistor; both are representable."
            ),
        ),
        ModelInputSpec(
            name=REFERENCE_TEMPERATURE,
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TEMPERATURE_UNIT,
            description="Temperature at which the reference resistance holds.",
        ),
        # THE STATE COORDINATE THE PROPERTY DEPENDS ON.
        #
        # This one line is what makes "resistance depends on temperature" a
        # typed, deterministically inspectable fact. A reader holding only this
        # record knows: there is an input named `temperature`, it must come
        # from a VARIABLE rather than a configured parameter, it carries a
        # thermodynamic temperature, and it plays the role of an evolving
        # STATE. No metadata, no naming convention, no solver setting and no
        # branch in universal core carries any part of that.
        ModelInputSpec(
            name=TEMPERATURE,
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar=TEMPERATURE_UNIT,
            role=VariableRole.STATE,
            description=(
                "Conductor temperature. A state coordinate, supplied from "
                "outside this model; never inferred here."
            ),
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric=RESISTANCE_METRIC,
            unit_exemplar=RESISTANCE_UNIT,
            description="Resistance at the supplied temperature.",
        ),
    ),
    assumptions=_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name=TEMPERATURE,
                minimum=TCR_MIN_TEMPERATURE,
                maximum=TCR_MAX_TEMPERATURE,
                description=(
                    "Range over which the single linear coefficient is "
                    "declared to hold. Outside it the linear form is an "
                    "extrapolation with no evidence behind it."
                ),
            ),
            RangeCondition(
                name=REFERENCE_RESISTANCE,
                minimum=Quantity(0.0, RESISTANCE_UNIT),
                minimum_inclusive=False,
                description="Strictly positive reference resistance.",
            ),
        ),
        description="Linear TCR about a reference state, over a stated range.",
    ),
    required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    # SELF_CONSISTENT and no more. The linear TCR form is standard, but this
    # repository has measured no conductor and curates no reference set, and a
    # citation will not be invented to dress that up.
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)


LINEAR_TCR_REALIZATION = ModelRealizationDefinition(
    realization_id="electrical.material.linear_tcr_resistance.closed_form",
    version="0.1.0",
    model=ModelReference(LINEAR_TCR_MODEL.model_id, LINEAR_TCR_MODEL.version),
    formulation=ModelFormulation.ALGEBRAIC,
    name="Direct evaluation of the linear TCR expression",
    description=(
        "Evaluates R_ref (1 + alpha (T - T_ref)) once, at a supplied "
        "temperature. No iteration and no system solve."
    ),
    provided_capabilities=frozenset({TEMPERATURE_DEPENDENT_RESISTANCE}),
    # A real, machine-checkable scientific dependency: this computation cannot
    # be planned unless something provides a body temperature.
    required_capabilities=frozenset({REQUIRED_BODY_TEMPERATURE}),
    # Arithmetic, and nothing more specific is declared.
    #
    # This module and ``thermal_lumped`` made *opposite* choices here, and the
    # milestone records that rather than forcing agreement: the thermal
    # realization declares a domain solver capability beside ``core:algebraic``
    # and matches on it, this one declares none and matches on the model
    # reference the problem carries. Both are defensible and no contract
    # decides between them — capability identity is exact-string with no
    # registry and no subsumption, so granularity is a judgement call with
    # nothing to appeal to. That is MODEL0-R finding D5, met again from a
    # second direction and carried forward, not resolved by guesswork here.
    required_solver_capabilities=frozenset(
        {SolverCapabilityId.coerce(CoreCapabilities.ALGEBRAIC)}
    ),
    assumptions=(
        "single evaluation at one supplied temperature; no self-consistency "
        "loop between resistance and dissipation is performed here",
        "exact for the declared linear form; no discretization error exists",
    ),
    implementation=ImplementationReference(
        implementation_id="engcore.domains.electrical.material",
        version="0.1.0",
        reference="linear TCR closed form; see module docstring",
    ),
)


def resistance_model_registry() -> ModelRegistry:
    """A fresh registry. No global singleton exists."""
    return ModelRegistry((LINEAR_TCR_MODEL,))


def resistance_realizations() -> RealizationRegistry:
    """A fresh registry. No global singleton exists."""
    return RealizationRegistry((LINEAR_TCR_REALIZATION,))


def resistance_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({CoreCapabilities.ALGEBRAIC})


# =====================================================================
# Declaration
# =====================================================================

@dataclass(frozen=True)
class TemperatureDependentConductor:
    """One declared conductor whose resistance depends on its temperature.

    Carries the material declaration and the component id it belongs to. It
    carries no temperature: a temperature is a *state*, and freezing one into
    the declaration is precisely the configuration/state conflation this
    milestone exists to examine.
    """

    component_id: str
    reference_resistance: Quantity
    temperature_coefficient: Quantity
    reference_temperature: Quantity

    def __post_init__(self) -> None:
        component_id = str(self.component_id).strip()
        if not component_id:
            raise InvalidScientificProblem("conductor requires a component_id")
        object.__setattr__(self, "component_id", component_id)

        for label, unit in (
            ("reference_resistance", RESISTANCE_UNIT),
            ("temperature_coefficient", TCR_UNIT),
            ("reference_temperature", TEMPERATURE_UNIT),
        ):
            value = getattr(self, label)
            if not isinstance(value, Quantity):
                raise InvalidScientificProblem(
                    f"{label} must be a Quantity carrying {unit!r}, got "
                    f"{type(value).__name__} — a bare number is not a "
                    f"declaration"
                )
            value.require_compatible(unit, context=f"conductor {label}")

        if self.reference_resistance.magnitude_in(RESISTANCE_UNIT) <= 0.0:
            raise InvalidScientificProblem(
                f"conductor {component_id!r} requires a strictly positive "
                f"reference resistance"
            )
        if self.reference_temperature.magnitude_in(TEMPERATURE_UNIT) <= 0.0:
            raise InvalidScientificProblem(
                f"conductor {component_id!r} requires a positive absolute "
                f"reference temperature"
            )

    @property
    def r_ref_ohm(self) -> float:
        return self.reference_resistance.magnitude_in(RESISTANCE_UNIT)

    @property
    def alpha_per_k(self) -> float:
        return self.temperature_coefficient.magnitude_in(TCR_UNIT)

    @property
    def t_ref_k(self) -> float:
        return self.reference_temperature.magnitude_in(TEMPERATURE_UNIT)


def build_resistance_problem(
    conductor: TemperatureDependentConductor,
    *,
    problem_id: str | None = None,
) -> ScientificProblem:
    """The universal problem statement for one resistance evaluation.

    ``temperature`` is a **variable with role STATE** and carries no value: the
    problem states that a temperature is required and what dimension it has,
    without asserting which one. Where the value comes from is a separate fact
    and lives in a separate record.
    """
    return ScientificProblem(
        problem_id=problem_id or f"resistance-tcr-{conductor.component_id}",
        name=f"Temperature-dependent resistance of {conductor.component_id}",
        description=(
            "Evaluate R(T) for one conductor at one supplied temperature."
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
                name=REFERENCE_RESISTANCE,
                value=conductor.reference_resistance,
                description="Resistance at the reference temperature.",
            ),
            ScientificParameter(
                name=TEMPERATURE_COEFFICIENT,
                value=conductor.temperature_coefficient,
                description="Linear temperature coefficient of resistance.",
            ),
            ScientificParameter(
                name=REFERENCE_TEMPERATURE,
                value=conductor.reference_temperature,
                description="Temperature at which the reference value holds.",
            ),
        ),
        models=(
            ModelReference(LINEAR_TCR_MODEL.model_id, LINEAR_TCR_MODEL.version),
        ),
        required_capabilities=frozenset({CoreCapabilities.ALGEBRAIC.name}),
    )


def assess_resistance_validity(
    problem: ScientificProblem, temperature: Quantity
) -> ValidityAssessment:
    """Is the model applicable at this temperature? **Validity, not validation.**

    Kept as its own function, deliberately outside the solver's
    :class:`ValidationReport`. *Was this model applicable* and *was this result
    checked* are different questions, and the platform keeps them on different
    fields for exactly that reason.

    Note what has to happen for this to work at all: ``temperature`` is a
    **variable**, and :meth:`ScientificProblem.validity_context` is built from
    **parameters**, so the state value must be supplied explicitly through
    ``extra=``. A validity condition on a state coordinate is therefore never
    automatic — recorded as a finding, not worked around.
    """
    context = problem.validity_context(extra={TEMPERATURE: temperature})
    return LINEAR_TCR_MODEL.assess_validity(context)


# =====================================================================
# Evaluator
# =====================================================================

SOLVER_ID = "engcore.electrical.linear_tcr_evaluator"
SOLVER_VERSION = "0.1.0"
BACKEND = "python.float"


@dataclass(frozen=True)
class PreparedResistanceEvaluation:
    """The conductor and the temperature this evaluation will use."""

    conductor: TemperatureDependentConductor
    realization: ModelRealizationDefinition
    temperature_k: float


class ResistancePropertySolver:
    """Evaluates R(T) for one conductor. Satisfies ScientificSolver.

    It is a solver in the platform's sense — something that takes a prepared
    problem, produces raw output, and can be named in provenance — even though
    the computation is one line of arithmetic. Making it a special case would
    have meant the property evaluation could not appear in an
    :class:`ExecutionBinding`, and "which realization computed this resistance"
    would have gone unrecorded.
    """

    def __init__(self, settings: SolverSettings | None = None) -> None:
        self._bound: dict[str, tuple[TemperatureDependentConductor, float]] = {}
        self.settings = settings or SolverSettings()

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(SOLVER_ID, SOLVER_VERSION, backend=BACKEND)

    @property
    def capabilities(self) -> frozenset[SolverCapability]:
        return resistance_solver_capabilities()

    def bind_conductor(
        self,
        conductor: TemperatureDependentConductor,
        problem_id: str,
        *,
        temperature: Quantity,
    ) -> None:
        """Associate a conductor and a supplied temperature with a problem id.

        Rebinding a **different temperature** under one problem id is allowed
        and is the normal case: one conductor evaluated at two temperatures is
        one system at two states, not two systems. Rebinding a different
        *conductor* is refused.
        """
        if not isinstance(conductor, TemperatureDependentConductor):
            raise InvalidScientificProblem(
                "bind_conductor expects a TemperatureDependentConductor"
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
        problem: ScientificProblem, conductor: TemperatureDependentConductor
    ) -> None:
        """Refuse a problem describing a different conductor than the bound one.

        A result whose provenance contradicts the declaration that produced it
        is worse than no result, which is why the sibling DC domain checks the
        same thing before it assembles anything.
        """
        for name, declared in (
            (REFERENCE_RESISTANCE, conductor.reference_resistance),
            (TEMPERATURE_COEFFICIENT, conductor.temperature_coefficient),
            (REFERENCE_TEMPERATURE, conductor.reference_temperature),
        ):
            stated = problem.parameter(name).value
            if not isinstance(stated, Quantity) or stated.compare(declared) != 0.0:
                raise InvalidScientificProblem(
                    f"problem {problem.problem_id!r} states {name} = {stated} "
                    f"but the bound conductor declares {declared}"
                )

    def supports(self, problem: ScientificProblem) -> bool:
        """Does this evaluator implement the science the problem asks for?

        Matched on the **model reference the problem carries**, not on a
        capability alone: ``core:algebraic`` says a closed-form evaluation is
        needed, which is true of countless unrelated relations.
        """
        wanted = (LINEAR_TCR_MODEL.model_id, LINEAR_TCR_MODEL.version)
        return any(model.key == wanted for model in problem.models)

    def prepare(
        self,
        problem: ScientificProblem,
        *,
        realization: ModelRealizationDefinition = LINEAR_TCR_REALIZATION,
    ) -> PreparedSolve:
        bound = self._bound.get(problem.problem_id)
        if bound is None:
            raise InvalidScientificProblem(
                f"no conductor is bound to problem {problem.problem_id!r}; "
                f"call bind_conductor first"
            )
        conductor, kelvin = bound
        # Refuse an inconsistent pairing before evaluating, not after
        # attributing. Same discipline as the sibling DC domain's
        # ``verify_problem_matches_circuit``.
        self.verify_problem_matches_conductor(problem, conductor)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,
            settings=self.settings,
            payload=PreparedResistanceEvaluation(
                conductor=conductor,
                realization=realization,
                temperature_k=kelvin,
            ),
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        evaluation: PreparedResistanceEvaluation = prepared.payload
        conductor = evaluation.conductor
        started = time.perf_counter()
        resistance = conductor.r_ref_ohm * (
            1.0
            + conductor.alpha_per_k * (evaluation.temperature_k - conductor.t_ref_k)
        )
        return RawSolverOutput(
            values={RESISTANCE_METRIC: resistance},
            # NOT_APPLICABLE, not CONVERGED: a direct evaluation neither
            # converges nor fails to, and conflating the two would overstate
            # what the backend reported.
            convergence=ConvergenceState.NOT_APPLICABLE,
            iterations=1,
            wall_seconds=time.perf_counter() - started,
            diagnostics={
                "temperature_k": evaluation.temperature_k,
                "delta_t_k": evaluation.temperature_k - conductor.t_ref_k,
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
        """One admissibility check, establishing no evidence level.

        A positive resistance is a precondition for the surrounding linear DC
        formulation, which refuses zero and negative resistances. Checking it
        earns no ``ValidationLevel``: confirming that a number is in the
        physically admissible range is not verification against anything, and
        claiming a level for it would be exactly the unearned claim the result
        contract is built to refuse.
        """
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
        resistance = raw.values[RESISTANCE_METRIC]
        positive = resistance > 0.0
        return ValidationReport(
            checks=(
                ValidationCheck(
                    name="resistance_strictly_positive",
                    outcome=(
                        ValidationOutcome.PASS if positive else ValidationOutcome.FAIL
                    ),
                    detail=(
                        f"R = {resistance:.6g} ohm. A linear TCR form crosses "
                        f"zero at a large enough negative excursion; a "
                        f"non-positive resistance is refused rather than "
                        f"passed downstream."
                    ),
                ),
            ),
            notes=(
                "Admissibility only. Whether the model was applicable at this "
                "temperature is a validity question and is answered by "
                "assess_resistance_validity, not here."
            ),
        )
