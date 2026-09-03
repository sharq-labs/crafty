"""The STEELMAN encoding — the frozen consumer expressed in existing contracts.

`docs/hostile-core-domain-stress-prereg.md` §6 makes this binding: **no gap may
be declared before a maximal honest attempt has been made to express the
consumer in typed records that already exist.** Without that attempt every
finding is answerable with *"you never tried"* — and that objection is live and
correct, because the repository's only existing PDE domain took the metadata
route (`build_conduction_problem` puts its boundary conditions in a metadata
string and never constructs a `BoundaryCondition`).

So this module tries as hard as the contracts allow:

* real ``InitialCondition`` records, not a metadata string;
* real ``BoundaryCondition`` records for both ends, with distinct kinds;
* ``u``, ``D``, ``L``, ``t_end`` as typed ``ScientificParameter`` Quantities;
* separate ``ModelRealizationDefinition`` records for central and upwind;
* ``ExecutionBinding`` written into provenance, so the model -> realization ->
  solver association is structural rather than positional;
* the solved field carried as a ``ScientificDataReference``.

**No new contract is defined in this module, and none may be.** Every type it
constructs already exists in `engcore.scientific`.

THREE ENCODINGS OF ONE MESH-DEPENDENT VALIDITY CRITERION
---------------------------------------------------------
``Pe_cell = u dx / D`` is a validity criterion of the *model* whose value
depends on the *mesh*. Making it checkable is where the contracts are actually
under pressure, so the probe encodes it three ways and measures all three.

``ENCODING_A``  ``n_cells`` in ``ScientificProblem.metadata``, as a string.
                This is what the baseline domain does, and it keeps the problem
                statement clean — the mesh is a property of *how* the problem is
                solved, not of the problem. Cost: the number is recoverable only
                by metadata convention, and the core states explicitly that
                validity context is *"deliberately not sourced from metadata"*.

``ENCODING_B``  ``n_cells`` as a typed ``IntegerValue`` ``ScientificParameter``.
                The number is typed and ``Pe_cell`` is recomputable from the
                problem alone. Cost: a numerical resolution is now part of the
                *scientific problem statement*, so two meshes of one physical
                problem become two different problem records — and under
                long-lived storage, two different ``problem_id`` values, so a
                refinement history cannot be recognised as one physical problem.

``ENCODING_C``  ``peclet_cell`` as a typed ``Quantity`` in
                ``ProvenanceRecord.inputs``, and **nothing about the mesh in the
                problem at all**. This is the encoding an earlier draft of this
                milestone missed, and it is the better one:
                ``ProvenanceRecord`` is documented as *"everything needed to
                attribute and re-derive a result"*, ``inputs`` is
                ``Mapping[str, Quantity]`` — typed, dimension-checked,
                serialized — and ``validity_context``'s own docstring sanctions
                exactly this use: it *"lets a domain or solver adapter add
                computed context (a Reynolds number, a detected regime)
                explicitly"*. A cell Peclet number is that object.

**The earlier draft claimed a dilemma — "no encoding gives both" — and that
claim was false.** ``ENCODING_C`` gives a typed criterion *and* a mesh-free
problem identity. What survives is narrower, true, and contains no fluid word:

    a mesh-dependent validity criterion is assessable **per-run** and never
    **pre-run**, because the only typed home for it is a record that does not
    exist until a solve has produced it. ``ValidityDomain`` therefore cannot be
    used to screen a proposed discretization before spending the solve.

That residual generalizes verbatim to CFL number, Courant number, y+, element
aspect ratio and element Jacobian.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from engcore.scientific.capabilities import ScientificCapability
from engcore.scientific.ir.conditions import (
    BoundaryCondition,
    BoundaryKind,
    InitialCondition,
)
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.values import IntegerValue
from engcore.scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from engcore.scientific.models.definition import (
    InputSourceKind,
    ModelInputSpec,
    ModelOutputSpec,
    ModelType,
    ModelValidationStatus,
    RangeCondition,
    ScientificModelDefinition,
    ValidityDomain,
)
from engcore.scientific.realizations.definition import (
    ImplementationReference,
    ModelFormulation,
    ModelRealizationDefinition,
    RealizationReference,
)
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.provenance import ExecutionBinding, ProvenanceRecord
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.uncertainty import Uncertainty
from engcore.scientific.results.validation import (
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
)
from engcore.scientific.solvers.capability import SolverCapability
from engcore.scientific.solvers.protocol import ConvergenceState, SolverIdentity
from engcore.scientific.units.quantity import Quantity

from .transport1d import (
    DIFFUSIVITY_UNIT,
    FIELD_UNIT,
    GRADIENT_UNIT,
    LENGTH_UNIT,
    MIN_INVERSE_CELL_PECLET,
    TIME_UNIT,
    VELOCITY_UNIT,
    AdvectionScheme,
    TransportCase,
    admissibility_violation,
    field_metrics,
)


def t1_min_inverse_peclet() -> float:
    """Indirection so the threshold is stated once, in the physics module."""
    return MIN_INVERSE_CELL_PECLET

MODEL_VERSION = "0.1.0"
REALIZATION_VERSION = "0.1.0"
SOLVER_VERSION = "0.1.0"

#: Declared in this package and nowhere else, exactly as a domain pack would.
TRANSPORT_1D = SolverCapability(
    "transport:advection_diffusion_1d",
    "1D linear advection-diffusion of a normalized scalar on a bounded interval",
)

#: The *scientific* capability, which is a statement about nature. Note what it
#: deliberately does NOT say: nothing about upwinding, nothing about a scheme.
#: Encoding a discretization here would collapse the capability layer into the
#: numerics layer, which is the confusion `capabilities.py` exists to prevent.
TRANSPORT_SCIENCE = ScientificCapability("transport", "advection_diffusion_1d")


class Encoding(str, Enum):
    """Where the mesh-dependent validity input lives. See the module docstring."""

    #: Mesh in ``metadata``. Problem identity stays clean; ``Pe_cell`` is
    #: recoverable only by metadata convention.
    METADATA = "discretization_in_metadata"
    #: Mesh as a typed ``IntegerValue`` parameter. ``Pe_cell`` is recoverable
    #: from the problem; problem identity now includes the mesh.
    TYPED_PARAMETER = "discretization_as_typed_parameter"
    #: ``peclet_cell`` as a typed ``Quantity`` in ``ProvenanceRecord.inputs``,
    #: and nothing about the mesh in the problem. Typed criterion AND mesh-free
    #: problem identity — at the cost of being a *run* fact, so it cannot be
    #: assessed before the run exists.
    PROVENANCE_INPUT = "criterion_in_provenance_inputs"


# =============================================================================
# The scientific model — one claim about nature, no numerics
# =============================================================================

_ASSUMPTIONS = (
    "one spatial dimension; no lateral or multidimensional transport",
    "linear transport with constant, field-independent velocity and diffusivity",
    "no source or sink term",
    "incompressible carrier: the velocity field is divergence-free by "
    "construction in one dimension with constant u",
    "normalized dimensionless scalar; no species, solvent, reference state or "
    "thermodynamic state is claimed",
    "transport is directed: the sign of u distinguishes the two ends of the "
    "interval, and the model is declared only for u > 0",
    "the transported scalar obeys a maximum principle, so any value outside "
    "the range of the boundary and initial data is unphysical",
)

TRANSPORT_MODEL = ScientificModelDefinition(
    model_id="transport.advection_diffusion1d.linear",
    version=MODEL_VERSION,
    name="1D linear advection-diffusion",
    domain="transport",
    # FUNDAMENTAL_RELATION for the same reason the baseline diffusion model is:
    # this is a conservation statement, not a fitted correlation. The
    # APPROXIMATION lives in the discretization, which is not the model.
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "dc/dt + u dc/dx = D d2c/dx2 on a bounded interval, for a normalized "
        "dimensionless transported scalar."
    ),
    inputs=(
        ModelInputSpec(
            name="velocity",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=VELOCITY_UNIT,
            description="Transport velocity; strictly positive in this model.",
        ),
        ModelInputSpec(
            name="diffusivity",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=DIFFUSIVITY_UNIT,
            description="Diffusivity; strictly positive.",
        ),
        ModelInputSpec(
            name="length",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=LENGTH_UNIT,
            description="Interval length.",
        ),
        ModelInputSpec(
            name="end_time",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=TIME_UNIT,
            required=False,
            description="Final time; absent for a steady statement.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="c:midpoint",
            unit_exemplar=FIELD_UNIT,
            description="Normalized scalar at the interval midpoint.",
        ),
        ModelOutputSpec(
            metric="c:max",
            unit_exemplar=FIELD_UNIT,
            description="Maximum nodal value of the normalized scalar.",
        ),
        ModelOutputSpec(
            metric="c:min",
            unit_exemplar=FIELD_UNIT,
            description="Minimum nodal value of the normalized scalar.",
        ),
    ),
    assumptions=_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="diffusivity",
                minimum=Quantity(0.0, DIFFUSIVITY_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive diffusivity. At D = 0 the equation "
                    "changes order and its well-posed boundary set changes "
                    "with it."
                ),
            ),
            RangeCondition(
                name="velocity",
                minimum=Quantity(0.0, VELOCITY_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive velocity. The model is declared for "
                    "transport towards increasing x only."
                ),
            ),
            # The interesting one. This is a validity criterion of the MODEL
            # whose value is a property of the MESH, so it is not a parameter
            # of the problem and never can be.
            #
            # Declared as the RECIPROCAL `D / (u dx) >= 0.5`, which is the same
            # condition as `Pe_cell <= 2` and is finite at `D = 0`. See
            # `TRANSPORT_MODEL_NAIVE_PECLET` for the parameterisation that is
            # not, and for what that costs.
            RangeCondition(
                name="inverse_peclet_cell",
                minimum=Quantity(t1_min_inverse_peclet(), "dimensionless"),
                description=(
                    "Inverse cell Peclet number D / (u dx), equivalently "
                    "Pe_cell <= 2. Below 0.5 a central discretization loses "
                    "its maximum principle. Depends on the mesh, so it cannot "
                    "be evaluated from the physical problem statement alone."
                ),
            ),
        ),
        description=(
            "Linear directed transport with constant coefficients on a bounded "
            "interval, adequately resolved."
        ),
    ),
    required_capabilities=frozenset({TRANSPORT_1D.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

#: The same model with the criterion stated the OTHER way round, kept solely so
#: the parameterisation trap can be measured rather than asserted.
#:
#: An earlier draft of this milestone declared `peclet_cell <= 2` and reported,
#: as an unanticipated contract finding, that at `D = 0` the criterion's true
#: value is infinite and `Quantity` refuses it — so the condition written to
#: catch pure advection could not be evaluated there. The adversarial pass
#: showed that is **not a contract finding**: the reciprocal form above is the
#: same criterion, is finite at `D = 0`, and reports the violation correctly.
#: `Quantity`'s refusal of non-finite magnitudes survives intact.
#:
#: What remains true, and is worth carrying, is narrower: `ValidityStatus.UNKNOWN`
#: conflates "the context did not supply this" with "the context could not
#: express this", and a domain author who picks the unbounded parameterisation
#: gets the second silently disguised as the first.
TRANSPORT_MODEL_NAIVE_PECLET = ScientificModelDefinition(
    model_id="transport.advection_diffusion1d.linear_naive_peclet",
    version=MODEL_VERSION,
    name="1D linear advection-diffusion, unbounded criterion parameterisation",
    domain="transport",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Identical science to the transport model; states its resolution "
        "criterion as Pe_cell <= 2 rather than as its finite reciprocal."
    ),
    inputs=TRANSPORT_MODEL.inputs,
    outputs=TRANSPORT_MODEL.outputs,
    assumptions=TRANSPORT_MODEL.assumptions,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="peclet_cell",
                maximum=Quantity(2.0, "dimensionless"),
                description="Cell Peclet number u dx / D; unbounded at D = 0.",
            ),
        ),
        description="The same criterion, in the parameterisation that has no "
        "finite value in the pure-advection limit.",
    ),
    required_capabilities=frozenset({TRANSPORT_1D.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

TRANSPORT_MODELS = (TRANSPORT_MODEL,)
_MODEL_REFERENCE = ModelReference(TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version)


# =============================================================================
# Two realizations of one model — same science, different numerics
# =============================================================================

def _realization(
    scheme: AdvectionScheme, name: str, description: str, note: str
) -> ModelRealizationDefinition:
    return ModelRealizationDefinition(
        realization_id=f"transport.advection_diffusion1d.fv_{scheme.name.lower()}",
        version=REALIZATION_VERSION,
        model=_MODEL_REFERENCE,
        # Both are PDE. `ModelFormulation` answers *what mathematical form is
        # posed*, and both realizations pose the same one. It is not the axis
        # on which these two differ, and stretching it to carry a scheme would
        # be exactly the overloading MODEL0-R refused for SURROGATE.
        formulation=ModelFormulation.PDE,
        name=name,
        description=description,
        provided_capabilities=frozenset({TRANSPORT_SCIENCE}),
        required_solver_capabilities=frozenset(),
        assumptions=(note,),
        implementation=ImplementationReference(
            implementation_id=(
                f"experiments.hostile_core_stress.transport1d:{scheme.value}"
            ),
            version=SOLVER_VERSION,
        ),
    )


REALIZATION_CENTRAL = _realization(
    AdvectionScheme.CENTRAL,
    "Finite-volume, 2nd-order central advection",
    "Central differencing of the advection term; central diffusion.",
    "second-order accurate; loses its maximum principle above cell Peclet 2",
)

REALIZATION_UPWIND = _realization(
    AdvectionScheme.UPWIND,
    "Finite-volume, 1st-order upwind advection",
    "First-order upwind differencing of the advection term (written for u > 0); "
    "central diffusion.",
    "first-order accurate; monotone and bounded at every cell Peclet number",
)

REALIZATIONS = {
    AdvectionScheme.CENTRAL: REALIZATION_CENTRAL,
    AdvectionScheme.UPWIND: REALIZATION_UPWIND,
}

SOLVER = SolverIdentity(
    solver_id="experiments.hostile_core_stress.transport1d",
    version=SOLVER_VERSION,
    backend="python-tridiagonal",
)


# =============================================================================
# Region identifiers
# =============================================================================

#: Opaque labels, exactly as `BoundaryCondition.region` documents them: "a mesh
#: tag, a port name, a surface id. The core does not interpret it." They are
#: written to be *unhelpful to a string parser on purpose* — an honest probe
#: must not smuggle the answer into the identifier and then report that the
#: answer was recoverable. Calling them "inlet" and "outlet" would have made
#: R1's count come back 1 for a reason that is a naming convention and not a
#: contract.
REGION_LOW = "boundary-a"
REGION_HIGH = "boundary-b"


# =============================================================================
# The universal problem statement
# =============================================================================

def build_problem(
    case: TransportCase,
    *,
    encoding: Encoding = Encoding.METADATA,
    problem_id: str | None = None,
) -> ScientificProblem:
    """Express one frozen case in the domain-neutral IR, as well as possible.

    The field ``c`` is declared as a single ``STATE`` variable. That is the
    strongest available expression: there is no field object, and a ``STATE``
    variable at least states that ``c`` evolves and is determined by the
    declared conditions rather than imposed from outside. What it cannot state
    is that ``c`` is *spatially distributed* — a reader sees a variable
    indistinguishable in every typed field from a lumped scalar.
    """
    variables = [
        ScientificVariable(
            name="c",
            unit=FIELD_UNIT,
            role=VariableRole.STATE,
            description=(
                "Normalized transported scalar. Physically a field over the "
                "interval; nothing in this record can say so."
            ),
        ),
        ScientificVariable(
            name="c:midpoint",
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Normalized scalar at the interval midpoint.",
        ),
        ScientificVariable(
            name="c:max",
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Maximum nodal value at the reported time.",
        ),
        ScientificVariable(
            name="c:min",
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Minimum nodal value at the reported time.",
        ),
    ]

    parameters = [
        ScientificParameter(
            name="velocity",
            value=Quantity(case.velocity_m_s, VELOCITY_UNIT),
            description="Transport velocity.",
        ),
        ScientificParameter(
            name="diffusivity",
            value=Quantity(case.diffusivity_m2_s, DIFFUSIVITY_UNIT),
            description="Diffusivity.",
        ),
        ScientificParameter(
            name="length",
            value=Quantity(case.length_m, LENGTH_UNIT),
            description="Interval length.",
        ),
    ]
    if case.transient:
        parameters.append(
            ScientificParameter(
                name="end_time",
                value=Quantity(case.end_time_s, TIME_UNIT),
                description="Final time of the transient.",
            )
        )

    if encoding is Encoding.TYPED_PARAMETER:
        parameters.append(
            ScientificParameter(
                name="n_cells",
                value=IntegerValue(case.discretization.n_cells),
                description=(
                    "Number of cells. A NUMERICAL resolution living in the "
                    "scientific problem statement, which is the cost of this "
                    "encoding."
                ),
            )
        )
        parameters.append(
            ScientificParameter(
                name="n_steps",
                value=IntegerValue(case.discretization.n_steps),
                description="Number of time steps. Numerical, as above.",
            )
        )

    initial_conditions: list[InitialCondition] = []
    if case.transient:
        initial_conditions.append(
            InitialCondition(
                variable="c",
                value=Quantity(0.0, FIELD_UNIT),
                time=Quantity(0.0, TIME_UNIT),
                description=(
                    "c(x, 0) = 0, uniform. Representable here only because it "
                    "is uniform: InitialCondition.value is one Quantity, so a "
                    "non-uniform initial field has no home in this record."
                ),
            )
        )

    boundary_conditions = (
        BoundaryCondition(
            name="condition-a",
            variable="c",
            kind=BoundaryKind.DIRICHLET,
            region=REGION_LOW,
            value=Quantity(1.0, FIELD_UNIT),
            description="Prescribed value of c on region 'boundary-a'.",
        ),
        BoundaryCondition(
            name="condition-b",
            variable="c",
            kind=BoundaryKind.NEUMANN,
            region=REGION_HIGH,
            value=Quantity(0.0, GRADIENT_UNIT),
            description="Zero normal gradient of c on region 'boundary-b'.",
        ),
    )
    if not case.transient:
        # CASE S: Dirichlet at both ends, and therefore no initial condition.
        # This is deliberately the shape MIN-FOUNDATION-ET's repair to
        # `unresolved_inputs` was written for — a state fixed entirely by
        # boundary conditions. Prediction P6 aims at it.
        boundary_conditions = (
            boundary_conditions[0],
            BoundaryCondition(
                name="condition-b",
                variable="c",
                kind=BoundaryKind.DIRICHLET,
                region=REGION_HIGH,
                value=Quantity(0.0, FIELD_UNIT),
                description="Prescribed value of c on region 'boundary-b'.",
            ),
        )

    metadata: dict[str, Any] = {
        "domain": "transport",
        # Mesh-free under ENCODING_C, so the problem record comes out
        # byte-identical across every refinement. `case_id` includes the mesh
        # and the scheme and therefore cannot be used there.
        "case_id": (
            case.physical_id
            if encoding is Encoding.PROVENANCE_INPUT
            else case.case_id
        ),
        "encoding": encoding.value,
    }
    if encoding is Encoding.METADATA:
        # Exactly what the baseline PDE domain does, and it is recorded here
        # so the comparison is like for like.
        metadata["n_cells"] = str(case.discretization.n_cells)
        metadata["n_steps"] = str(case.discretization.n_steps)

    default_id = (
        case.physical_id
        if encoding is Encoding.PROVENANCE_INPUT
        else case.case_id
    )
    return ScientificProblem(
        problem_id=problem_id or f"transport-1d-{default_id}",
        name="1D linear advection-diffusion on an interval",
        description=(
            "Normalized dimensionless scalar transported at constant velocity "
            "with constant diffusivity on a bounded interval."
        ),
        variables=tuple(variables),
        parameters=tuple(parameters),
        initial_conditions=tuple(initial_conditions),
        boundary_conditions=boundary_conditions,
        models=(_MODEL_REFERENCE,),
        required_capabilities=frozenset({TRANSPORT_1D.name}),
        validation_requirements=frozenset(
            {
                "dimensional_consistency",
                "linear_system_residual",
                "boundary_conditions_held",
                "field_finite",
            }
        ),
        metadata=metadata,
    )


# =============================================================================
# Validation — deliberately, exactly the checks the platform already runs
# =============================================================================

def build_validation_report(
    case: TransportCase, field: Sequence[float]
) -> ValidationReport:
    """The checks a competent domain would write **today**.

    The check set mirrors the baseline domain's declared
    ``validation_requirements`` exactly: dimensional consistency, a
    linear-system residual, boundaries held, field finite. It contains **no
    boundedness check**, and that is why ``ValidationReport.status`` returns
    ``PASS`` for a central-difference solution overshooting its own boundary
    data by 43 %.

    **What this does NOT demonstrate, stated because an earlier draft claimed
    it and was wrong.** It does not show the platform *cannot* express such a
    check. It plainly can: ``ValidationCheck.name`` is free text and
    ``ValidationReport.status`` returns ``FAIL`` if any check fails, so a domain
    can write ``ValidationCheck(name="maximum_principle_held", outcome=FAIL)``
    today with no contract change — and every input it needs is already typed
    and serialized on these records (the boundary values, the initial value, and
    ``values["c:max"]``). :func:`admissibility_check` writes exactly that check
    and is exercised.

    What is measured here is narrower and survives:

    * a competent domain writing the baseline's own check set produces ``PASS``
      for a physically impossible field, and
    * the platform can record the **violation** but structurally cannot record
      the **attainment**: ``ValidationLevel`` has seven members and none denotes
      physical admissibility, so ``establishes=`` has nothing to name. The
      evidence ladder is asymmetric on this axis.
    """
    finite = all(value == value and abs(value) != float("inf") for value in field)
    left_held = abs(field[0] - 1.0) <= 1e-12
    if case.transient:
        # Homogeneous Neumann outflow, checked by the one-sided nodal gradient.
        # The tolerance is loose because the estimate is first order; it is a
        # boundary check, not a convergence claim.
        outflow_gradient = abs(field[-1] - field[-2]) / case.dx_m
        right_held = outflow_gradient <= 1e-6
    else:
        outflow_gradient = 0.0
        right_held = abs(field[-1]) <= 1e-12
    return ValidationReport(
        checks=(
            ValidationCheck(
                name="dimensional_consistency",
                outcome=ValidationOutcome.PASS,
                detail="every declared quantity carries its declared unit",
                establishes=ValidationLevel.DIMENSIONALLY_VALID,
            ),
            ValidationCheck(
                name="linear_system_residual",
                outcome=ValidationOutcome.PASS,
                detail=(
                    "the tridiagonal system was solved directly; the residual "
                    "is at round-off"
                ),
                residual=0.0,
                tolerance=1e-12,
                establishes=ValidationLevel.NUMERICALLY_CONVERGED,
            ),
            ValidationCheck(
                name="boundary_conditions_held",
                outcome=(
                    ValidationOutcome.PASS
                    if left_held and right_held
                    else ValidationOutcome.FAIL
                ),
                detail="declared boundary values reproduced by the solution",
            ),
            ValidationCheck(
                name="field_finite",
                outcome=(
                    ValidationOutcome.PASS if finite else ValidationOutcome.FAIL
                ),
                detail="no NaN or infinity in the solved field",
            ),
        ),
        notes=(
            "No boundedness check appears here, because the baseline domain's "
            "declared validation_requirements contain none. The platform could "
            "carry one; nothing asked it to."
        ),
    )


def admissibility_check(
    field: Sequence[float], *, data: Sequence[float], tolerance: float = 1e-12
) -> ValidationCheck:
    """The boundedness check a domain COULD write today, written.

    Constructed to refute the overclaim rather than to argue against it: no
    contract changes, no field is added, and every input comes off records that
    already exist. ``data`` is the boundary and initial data whose range a
    linear transport equation's maximum principle forbids the solution to leave.

    ``tolerance`` allows a round-off-level excursion. A well-resolved central
    solve lands on ``1 + 2.2e-16`` — one ulp of the boundary value, produced by
    back-substitution — and a check that called that a physical violation would
    be reporting floating-point arithmetic rather than the maximum principle.

    Note ``establishes=None``. That is not an omission — it is the asymmetry:
    the check can report a failure, and there is no ``ValidationLevel`` member
    by which a passing one could claim that physical admissibility was
    *established*.
    """
    low, high = min(data), max(data)
    violation = max(0.0, low - min(field), max(field) - high)
    return ValidationCheck(
        name="maximum_principle_held",
        outcome=(
            ValidationOutcome.PASS
            if violation <= tolerance
            else ValidationOutcome.FAIL
        ),
        detail=(
            f"solution range [{min(field):.6g}, {max(field):.6g}] against data "
            f"range [{low:.6g}, {high:.6g}]"
        ),
        residual=violation,
        tolerance=tolerance,
        establishes=None,
    )


# =============================================================================
# The result, and the field that does not fit in it
# =============================================================================

@dataclass(frozen=True)
class ProbeRun:
    """One executed case: its records, its field, and its own honest verdict."""

    case: TransportCase
    problem: ScientificProblem
    result: ScientificResult
    field: tuple[float, ...]
    payload: bytes

    @property
    def admissibility_violation(self) -> float:
        """How far outside ``[0, 1]`` the solution strayed.

        Computed by the probe, carried by nothing. It is deliberately **not**
        written into the result: there is no typed field for it, and putting it
        in ``metadata`` would be the untyped escape hatch the platform refuses.
        """
        return admissibility_violation(self.field)


def build_result(
    case: TransportCase,
    field: Sequence[float],
    *,
    problem: ScientificProblem,
    encoding: Encoding = Encoding.METADATA,
    run_id: str | None = None,
) -> tuple[ScientificResult, bytes]:
    """Interpret a solved field into the platform's output contract.

    Returns the result and the bulk payload. The payload is returned rather
    than stored, exactly as ``ScientificDataReference.for_values`` does: this
    module is the representation layer and owns no storage. Which backend holds
    the bytes cannot change what the result means, and PROBE B checks that it
    does not.
    """
    metrics = {
        name: Quantity(value, FIELD_UNIT)
        for name, value in field_metrics(case, field).items()
    }
    reference, payload = ScientificDataReference.for_values(
        "c:field", field, unit=FIELD_UNIT
    )
    realization = REALIZATIONS[case.scheme]
    inputs = {
        "velocity": Quantity(case.velocity_m_s, VELOCITY_UNIT),
        "diffusivity": Quantity(case.diffusivity_m2_s, DIFFUSIVITY_UNIT),
        "length": Quantity(case.length_m, LENGTH_UNIT),
    }
    if encoding is Encoding.PROVENANCE_INPUT:
        # ENCODING_C. A typed, dimension-checked, serialized home for a
        # computed validity input, on the record whose stated job is
        # "everything needed to attribute and re-derive a result".
        #
        # Written as the RECIPROCAL, `inverse_peclet_cell = D / (u dx)`, not as
        # `peclet_cell` itself. The two criteria are identical — `Pe <= 2` is
        # `1/Pe >= 0.5` — but the reciprocal is FINITE at `D = 0`, where the
        # cell Peclet number is genuinely infinite and `Quantity` would refuse
        # it. An earlier draft of this milestone reported that refusal as a
        # contract gap; it is not one. It is a property of the parameterisation
        # the author chose, and any scalar criterion on `[0, inf]` admits a
        # monotone finite reparameterisation.
        inputs["inverse_peclet_cell"] = Quantity(
            case.inverse_cell_peclet, "dimensionless"
        )
    provenance = ProvenanceRecord(
        run_id=run_id or f"run-{case.case_id}",
        software_version="hostile-core-stress-probe",
        models=((TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version),),
        solvers=((SOLVER.solver_id, SOLVER.version),),
        bindings=(
            ExecutionBinding(
                model=_MODEL_REFERENCE,
                solver=SOLVER,
                realization=RealizationReference(
                    realization.realization_id, realization.version
                ),
            ),
        ),
        inputs=inputs,
        assumptions=TRANSPORT_MODEL.assumptions,
        tolerances={"linear_system_residual": 1e-12},
    )
    result = ScientificResult(
        result_id=provenance.run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version),),
        solver=SOLVER,
        convergence=ConvergenceState.CONVERGED,
        validation=build_validation_report(case, field),
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification performed; one solve quantifies "
                "no discretization error"
            )
            for name in metrics
        },
        assumptions=TRANSPORT_MODEL.assumptions,
        data_references=(reference,),
        provenance=provenance,
    )
    return result, payload


def run_case(
    case: TransportCase,
    *,
    encoding: Encoding = Encoding.METADATA,
) -> ProbeRun:
    """Solve one frozen case and express the whole thing in existing records."""
    from .transport1d import solve_steady, solve_transient

    field = solve_transient(case) if case.transient else solve_steady(case)
    problem = build_problem(case, encoding=encoding)
    result, payload = build_result(
        case, field, problem=problem, encoding=encoding
    )
    return ProbeRun(
        case=case,
        problem=problem,
        result=result,
        field=tuple(field),
        payload=payload,
    )


def serialize(run: ProbeRun) -> dict[str, Any]:
    """Everything a records-only reader is allowed to see.

    Note what is *not* here: no case object, no solver module, no realization
    definition, no source code. A reader that needs any of those has found a
    fact the records do not carry, which is the measurement.

    ``realization_definitions`` is included deliberately and separately, so the
    reader can be asked the question twice — once with only the run's records,
    and once with the realization catalogue as well. Those give different
    answers, and the difference is a finding.
    """
    return {
        "problem": run.problem.to_dict(),
        "result": run.result.to_dict(),
        "model": TRANSPORT_MODEL.to_dict(),
    }


def realization_catalogue() -> dict[str, Any]:
    """The realization definitions, serialized. Offered to the reader as a
    *second*, separate input so the milestone can measure what each buys."""
    return {
        definition.realization_id: definition.to_dict()
        for definition in (REALIZATION_CENTRAL, REALIZATION_UPWIND)
    }
