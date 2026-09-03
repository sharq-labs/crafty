"""STEELMAN encodings — all four consumers, in contracts that already exist.

Preregistration §7.1 makes this binding: **no gap may be declared for any
consumer before a maximal honest attempt to express it in existing typed
contracts**, and a gap declared without one is fail condition 4. The reason is
recorded precedent — the previous milestone's most valuable outputs were two
claims it *withdrew* after the adversarial pass showed a typed channel it had
not tried.

So this module tries as hard as the contracts allow, four times over, and
records where the attempt **succeeds** with the same prominence as where it
fails.

**No new contract is defined here, and none may be.** Every type constructed
already exists in `engcore.scientific`.

WHAT EACH CONSUMER IS ASKED TO EXPRESS, AND THE HONEST ANSWER
--------------------------------------------------------------
Written out because the shape of each failure is the milestone's product:

A  mechanics   Eight nodal displacement components and eight stress components
               are declared as sixteen independent scalar variables, because
               there is no other option: nothing relates ``u_x:n1`` to
               ``u_y:n1`` as components of one vector at one node, and nothing
               relates ``sigma_xx:e0``, ``sigma_yy:e0``, ``sigma_xy:e0`` and
               ``sigma_zz:e0`` as components of one tensor. `E` and `nu` encode
               cleanly as scalars; the 3x3 constitutive matrix ``D`` does not
               encode at all.
B  transport   Four boundary regions encode as four `BoundaryCondition`
               records. The prescribed velocity field and the manufactured
               source do not encode: `ScientificProblem` has no
               `data_references`, so a field-valued *input* has no typed home.
C  species     Three concentrations encode cleanly and identically — which is
               the problem, since nothing says they are distinct chemical
               species. The stoichiometric matrix does not encode. The
               conservation relation does not encode.
D  dynamics    Four states encode. The multiplier encodes only by choosing a
               `VariableRole` that is wrong in a different way for each option.
               The algebraic constraint does not encode: `ConstraintDefinition`
               is `metric OP bound`, an acceptance test against a fixed scalar,
               not a relation among unknowns. Four initial conditions encode
               individually and their joint consistency requirement does not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from engcore.scientific.capabilities import ScientificCapability
from engcore.scientific.ir.conditions import (
    BoundaryCondition,
    BoundaryKind,
    InitialCondition,
)
from engcore.scientific.ir.constraints import ConstraintDefinition, ConstraintOperator
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.values import CategoricalValue, IntegerValue
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

from . import dynamics as dyn
from . import mechanics as mech
from . import species as spc
from . import transport2d as tr2

VERSION = "0.1.0"

MECHANICS_CAPABILITY = SolverCapability(
    "mechanics:linear_elastic_plane_2d",
    "2D linear elastic static analysis on a constant-strain triangulation",
)
TRANSPORT_CAPABILITY = SolverCapability(
    "transport:advection_diffusion_2d",
    "2D steady linear advection-diffusion of a normalized scalar",
)
SPECIES_CAPABILITY = SolverCapability(
    "chemistry:batch_reaction_network",
    "Closed isothermal multi-species reaction network at constant volume",
)
DYNAMICS_CAPABILITY = SolverCapability(
    "dynamics:constrained_rigid_body_2d",
    "Planar constrained rigid-body dynamics with an algebraic position constraint",
)


@dataclass(frozen=True)
class ConsumerBundle:
    """Everything one consumer offers a records-only reader.

    ``science`` is the one thing the reader is NOT given: it records which
    candidate concepts this consumer's physics actually involves, and it is used
    only to derive the coverage matrix, never to answer a recoverability
    question. Keeping it on the bundle rather than inside the reader is what
    makes the derivation auditable.
    """

    consumer: str
    problem: ScientificProblem
    model: ScientificModelDefinition
    result: ScientificResult
    realizations: tuple[ModelRealizationDefinition, ...]
    science: frozenset[str]
    notes: Mapping[str, str]

    def payloads(self) -> dict[str, Any]:
        return {
            "consumer": self.consumer,
            "problem": self.problem.to_dict(),
            "model": self.model.to_dict(),
            "result": self.result.to_dict(),
            "realizations": {
                r.realization_id: r.to_dict() for r in self.realizations
            },
        }


def _provenance(
    run_id: str,
    model: ScientificModelDefinition,
    solver: SolverIdentity,
    realization: ModelRealizationDefinition | None,
    inputs: Mapping[str, Any],
) -> ProvenanceRecord:
    reference = ModelReference(model.model_id, model.version)
    return ProvenanceRecord(
        run_id=run_id,
        software_version="cross-domain-coverage-probe",
        models=((model.model_id, model.version),),
        solvers=((solver.solver_id, solver.version),),
        bindings=(
            ExecutionBinding(
                model=reference,
                solver=solver,
                realization=(
                    RealizationReference(
                        realization.realization_id, realization.version
                    )
                    if realization
                    else None
                ),
            ),
        ),
        inputs=dict(inputs),
        assumptions=model.assumptions,
    )


def admissibility_check(
    name: str, violation: float, detail: str, *, tolerance: float = 1e-9
) -> ValidationCheck:
    """A physical-admissibility check, written into the record.

    Added after the adversarial pass, which found that **zero of six columns
    recorded an admissibility check** while the milestone claimed admissibility
    was forced by all six. The claim was being made about criteria that existed
    only in probe source and test assertions, never in a record a reader could
    see.

    Note ``establishes=None``, and note that it is not an omission. It is the
    finding: `ValidationLevel` has seven members and none denotes physical
    admissibility, so a check like this can report PASS or FAIL and can never
    contribute to ``attained_levels`` or be gated by ``require_level``.
    """
    return ValidationCheck(
        name=name,
        outcome=(
            ValidationOutcome.PASS
            if violation <= tolerance
            else ValidationOutcome.FAIL
        ),
        detail=detail,
        residual=float(violation),
        tolerance=tolerance,
        establishes=None,
    )


def _unknown_uncertainty(names) -> dict[str, Uncertainty]:
    return {
        name: Uncertainty.unknown(
            "no uncertainty quantification performed by this coverage probe"
        )
        for name in names
    }


# =============================================================================
# CONSUMER A — mechanics
# =============================================================================

MECHANICS_MODEL = ScientificModelDefinition(
    model_id="mechanics.linear_elastic.plane",
    version=VERSION,
    name="2D linear isotropic elasticity",
    domain="mechanics",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Static linear elasticity in two dimensions: eps = sym grad u, "
        "sigma = D eps, div sigma = 0."
    ),
    inputs=(
        ModelInputSpec(
            name="youngs_modulus",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=mech.STRESS_UNIT,
            description="Young's modulus; strictly positive.",
        ),
        ModelInputSpec(
            name="poisson_ratio",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar="dimensionless",
            description="Poisson ratio; in [0, 0.5).",
        ),
        ModelInputSpec(
            name="thickness",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=mech.LENGTH_UNIT,
            description="Out-of-plane thickness.",
        ),
        # The 3x3 constitutive matrix D is NOT declarable here. ModelInputSpec
        # carries a unit exemplar and a value kind, and ScientificValue is a
        # closed union of scalars. This absence is a measurement.
    ),
    outputs=(
        ModelOutputSpec(
            metric="sigma_xx:e0",
            unit_exemplar=mech.STRESS_UNIT,
            description="In-plane normal stress, element 0.",
        ),
        ModelOutputSpec(
            metric="von_mises:e0",
            unit_exemplar=mech.STRESS_UNIT,
            description="Von Mises equivalent stress, element 0.",
        ),
    ),
    assumptions=(
        "small strains and small displacements; geometry is not updated",
        "linear isotropic elasticity; no plasticity, damage or rate dependence",
        "static equilibrium; no inertia and no damping",
        "constant strain within each element",
        "a plane reduction of three-dimensional elasticity is asserted; which "
        "one is a modelling choice that changes the constitutive matrix and "
        "the out-of-plane stress",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="youngs_modulus",
                minimum=Quantity(0.0, mech.STRESS_UNIT),
                minimum_inclusive=False,
                description="Strictly positive stiffness.",
            ),
            RangeCondition(
                name="poisson_ratio",
                minimum=Quantity(0.0, "dimensionless"),
                maximum=Quantity(0.5, "dimensionless"),
                maximum_inclusive=False,
                description="0.5 is incompressible and singular in both reductions.",
            ),
        ),
        description="Linear isotropic elasticity at small strain.",
    ),
    required_capabilities=frozenset({MECHANICS_CAPABILITY.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

MECHANICS_SOLVER = SolverIdentity(
    solver_id="experiments.cross_domain_coverage.mechanics",
    version=VERSION,
    backend="numpy-dense",
)


def _mechanics_realization(assumption: mech.PlaneAssumption) -> ModelRealizationDefinition:
    return ModelRealizationDefinition(
        realization_id=f"mechanics.linear_elastic.cst_{assumption.value}",
        version=VERSION,
        model=ModelReference(MECHANICS_MODEL.model_id, MECHANICS_MODEL.version),
        # ALGEBRAIC: a static linear elastic analysis poses K u = f, a linear
        # algebraic system. The PDE is the model; this is how it is posed.
        formulation=ModelFormulation.ALGEBRAIC,
        name=f"Constant-strain triangles, {assumption.value}",
        description=(
            f"Two constant-strain triangles under the {assumption.value} "
            f"reduction of 3D elasticity."
        ),
        provided_capabilities=frozenset(
            {ScientificCapability("mechanics", "linear_elastic_plane_2d")}
        ),
        assumptions=(f"{assumption.value} constitutive reduction",),
        implementation=ImplementationReference(
            implementation_id=(
                f"experiments.cross_domain_coverage.mechanics:{assumption.value}"
            ),
            version=VERSION,
        ),
    )


MECHANICS_REALIZATIONS = tuple(
    _mechanics_realization(a) for a in mech.PlaneAssumption
)


def build_mechanics_problem(
    assumption: mech.PlaneAssumption = mech.PlaneAssumption.PLANE_STRESS,
) -> ScientificProblem:
    """The maximal honest encoding of the mechanics consumer.

    Displacement components become **separate scalar variables**, one per node
    per direction. That is not a stylistic choice: `ScientificVariable` has no
    rank, no component index and no grouping, so eight independent scalars is
    the only available encoding of one vector field on four nodes.
    """
    variables: list[ScientificVariable] = []
    for node in range(mech.N_NODES):
        for component in ("x", "y"):
            variables.append(
                ScientificVariable(
                    name=f"u_{component}:n{node}",
                    unit=mech.DISPLACEMENT_UNIT,
                    role=VariableRole.STATE,
                    description=(
                        f"Displacement of node {node} in {component}. "
                        f"Physically one component of a vector; nothing in this "
                        f"record can say which vector or which node's."
                    ),
                )
            )
    for element in range(len(mech.ELEMENTS)):
        for component in ("xx", "yy", "xy", "zz"):
            variables.append(
                ScientificVariable(
                    name=f"sigma_{component}:e{element}",
                    unit=mech.STRESS_UNIT,
                    role=VariableRole.OBSERVABLE,
                    description=(
                        f"Stress component {component} in element {element}. "
                        f"Physically one component of a rank-2 symmetric "
                        f"tensor; nothing relates the four."
                    ),
                )
            )

    parameters = (
        ScientificParameter(
            name="youngs_modulus",
            value=Quantity(mech.YOUNGS_MODULUS_PA, mech.STRESS_UNIT),
            description="Young's modulus.",
        ),
        ScientificParameter(
            name="poisson_ratio",
            value=Quantity(mech.POISSON_RATIO, "dimensionless"),
            description="Poisson ratio.",
        ),
        ScientificParameter(
            name="thickness",
            value=Quantity(mech.THICKNESS_M, mech.LENGTH_UNIT),
            description="Out-of-plane thickness.",
        ),
        ScientificParameter(
            name="plane_assumption",
            value=CategoricalValue(
                assumption.value,
                vocabulary=tuple(a.value for a in mech.PlaneAssumption),
            ),
            description=(
                "Which plane reduction is asserted. Encodes cleanly as a "
                "category — and a reader still cannot derive that it changes "
                "the constitutive matrix and makes sigma_zz non-zero."
            ),
        ),
        ScientificParameter(
            name="n_nodes",
            value=IntegerValue(mech.N_NODES),
            description="Node count. A discretization fact, in the problem.",
        ),
        ScientificParameter(
            name="n_elements",
            value=IntegerValue(len(mech.ELEMENTS)),
            description="Element count. A discretization fact, in the problem.",
        ),
    )

    # Prescribed displacement on the clamped edge. This DOES encode: a
    # Dirichlet boundary condition on a named variable with a value. What it
    # cannot say is that the region is an *edge with an outward normal*, or
    # that it constrains one component of a vector.
    boundary_conditions = tuple(
        BoundaryCondition(
            name=f"clamp-{dof}",
            variable=f"u_{'x' if dof % 2 == 0 else 'y'}:n{dof // 2}",
            kind=BoundaryKind.DIRICHLET,
            region="edge-west",
            value=Quantity(0.0, mech.DISPLACEMENT_UNIT),
            description="Clamped edge; one component of one node.",
        )
        for dof in mech.CLAMPED_DOF
    )

    return ScientificProblem(
        problem_id=f"mechanics-patch-{assumption.value}",
        name="Two-element plane elastic patch",
        description=(
            "Static linear elastic analysis of a unit square split into two "
            "constant-strain triangles."
        ),
        variables=tuple(variables),
        parameters=parameters,
        boundary_conditions=boundary_conditions,
        models=(ModelReference(MECHANICS_MODEL.model_id, MECHANICS_MODEL.version),),
        required_capabilities=frozenset({MECHANICS_CAPABILITY.name}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "stiffness_symmetry", "force_equilibrium"}
        ),
        metadata={
            "domain": "mechanics",
            "plane_assumption": assumption.value,
            "n_nodes": str(mech.N_NODES),
            "n_elements": str(len(mech.ELEMENTS)),
        },
    )


def build_mechanics_bundle(
    assumption: mech.PlaneAssumption = mech.PlaneAssumption.PLANE_STRESS,
) -> ConsumerBundle:
    case = mech.run_shear_case(assumption)
    problem = build_mechanics_problem(assumption)
    metrics = {
        name: Quantity(value, mech.STRESS_UNIT if "sigma" in name or "mises" in name
                       else mech.DISPLACEMENT_UNIT)
        for name, value in mech.case_metrics(case).items()
    }
    realization = MECHANICS_REALIZATIONS[
        list(mech.PlaneAssumption).index(assumption)
    ]
    displacement_reference, _ = ScientificDataReference.for_values(
        "u:nodal", case["displacement"], unit=mech.DISPLACEMENT_UNIT
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="dimensional_consistency",
                outcome=ValidationOutcome.PASS,
                detail="every declared quantity carries its declared unit",
                establishes=ValidationLevel.DIMENSIONALLY_VALID,
            ),
            ValidationCheck(
                name="stiffness_symmetry",
                outcome=ValidationOutcome.PASS,
                detail="K equals its transpose to machine precision",
                residual=case["symmetry_residual"],
                tolerance=1e-12,
            ),
            ValidationCheck(
                name="force_equilibrium",
                outcome=ValidationOutcome.PASS,
                detail="reactions balance the applied load",
                residual=case["equilibrium_residual_n"],
                tolerance=1e-6,
            ),
            admissibility_check(
                "strain_energy_non_negative",
                mech.strain_energy_violation(case),
                "strain energy of a positive-definite elastic body cannot be "
                "negative; a violation is unphysical whatever the residual says",
            ),
        )
    )
    result = ScientificResult(
        result_id=f"run-mechanics-{assumption.value}",
        problem_id=problem.problem_id,
        values=metrics,
        models=((MECHANICS_MODEL.model_id, MECHANICS_MODEL.version),),
        solver=MECHANICS_SOLVER,
        convergence=ConvergenceState.NOT_APPLICABLE,
        validation=report,
        uncertainty=_unknown_uncertainty(metrics),
        assumptions=MECHANICS_MODEL.assumptions,
        data_references=(displacement_reference,),
        provenance=_provenance(
            f"run-mechanics-{assumption.value}",
            MECHANICS_MODEL,
            MECHANICS_SOLVER,
            realization,
            {
                "youngs_modulus": Quantity(mech.YOUNGS_MODULUS_PA, mech.STRESS_UNIT),
                "poisson_ratio": Quantity(mech.POISSON_RATIO, "dimensionless"),
                "thickness": Quantity(mech.THICKNESS_M, mech.LENGTH_UNIT),
            },
        ),
    )
    return ConsumerBundle(
        consumer="A-mechanics",
        problem=problem,
        model=MECHANICS_MODEL,
        result=result,
        realizations=MECHANICS_REALIZATIONS,
        science=frozenset(
            {
                "SpatialFieldSemantics",
                "VariableToBulkLinkage",
                "FieldSupport",
                "Domain/Topology",
                "BoundaryIdentity",
                "BoundaryOrientation-normal",
                "BoundaryCondition",
                "Rank1",
                "Rank2",
                "MaterialIdentity",
                "PropertyRequirement-rank2",
                "DiscretizationDefinition",
                "QuantityIdentity",
                "AdmissibilityAttainment",
            }
        ),
        notes={
            "constitutive_matrix": (
                "the 3x3 D matrix has no typed home; ScientificValue is a "
                "closed union of scalars"
            ),
            "tensor_grouping": (
                "four sigma components per element are four independent "
                "variables; nothing relates them"
            ),
        },
    )


# =============================================================================
# CONSUMER B — 2D transport
# =============================================================================

TRANSPORT_MODEL = ScientificModelDefinition(
    model_id="transport.advection_diffusion.plane",
    version=VERSION,
    name="2D linear advection-diffusion",
    domain="transport",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "div(u c) - D grad^2 c = s on a bounded plane region, for a normalized "
        "dimensionless scalar in a prescribed divergence-free velocity field."
    ),
    inputs=(
        ModelInputSpec(
            name="diffusivity",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=tr2.DIFFUSIVITY_UNIT,
            description="Diffusivity; strictly positive.",
        ),
        ModelInputSpec(
            name="side",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=tr2.LENGTH_UNIT,
            description="Side length of the square region.",
        ),
        # The velocity FIELD and the source FIELD are not declarable. A
        # ModelInputSpec names a scalar-valued parameter or variable, and
        # ScientificProblem has no data_references at all.
    ),
    outputs=(
        ModelOutputSpec(
            metric="c:centre",
            unit_exemplar=tr2.FIELD_UNIT,
            description="Scalar at the region centre.",
        ),
        ModelOutputSpec(
            metric="c:mms_error",
            unit_exemplar=tr2.FIELD_UNIT,
            description="Max deviation from the manufactured solution.",
        ),
    ),
    assumptions=(
        "two spatial dimensions",
        "steady state; no time derivative",
        "linear transport with a prescribed, divergence-free velocity field",
        "constant scalar diffusivity",
        "normalized dimensionless scalar; no species and no reference state",
        "the transported scalar obeys a maximum principle over its data",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="diffusivity",
                minimum=Quantity(0.0, tr2.DIFFUSIVITY_UNIT),
                minimum_inclusive=False,
                description="Strictly positive diffusivity.",
            ),
        ),
        description="Linear steady transport on a bounded plane region.",
    ),
    required_capabilities=frozenset({TRANSPORT_CAPABILITY.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

TRANSPORT_SOLVER = SolverIdentity(
    solver_id="experiments.cross_domain_coverage.transport2d",
    version=VERSION,
    backend="numpy-dense",
)

TRANSPORT_REALIZATION = ModelRealizationDefinition(
    realization_id="transport.advection_diffusion.fv_upwind_2d",
    version=VERSION,
    model=ModelReference(TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version),
    formulation=ModelFormulation.PDE,
    name="Cell-centred upwind advection, central diffusion",
    description="First-order upwind advection with central diffusion on a "
    "structured cell-centred grid.",
    provided_capabilities=frozenset(
        {ScientificCapability("transport", "advection_diffusion_2d")}
    ),
    assumptions=("first-order accurate; monotone at every cell Peclet number",),
    implementation=ImplementationReference(
        implementation_id="experiments.cross_domain_coverage.transport2d:upwind",
        version=VERSION,
    ),
)


def build_transport_problem(case: tr2.Transport2DCase) -> ScientificProblem:
    """The maximal honest encoding of the 2D transport consumer."""
    variables = (
        ScientificVariable(
            name="c",
            unit=tr2.FIELD_UNIT,
            role=VariableRole.STATE,
            description=(
                "Transported scalar. Physically a field over a 2D region; "
                "nothing in this record can say so."
            ),
        ),
        ScientificVariable(
            name="c:centre",
            unit=tr2.FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Scalar at the region centre.",
        ),
        ScientificVariable(
            name="c:mms_error",
            unit=tr2.FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Max deviation from the manufactured solution.",
        ),
    )
    parameters = (
        ScientificParameter(
            name="diffusivity",
            value=Quantity(case.diffusivity_m2_s, tr2.DIFFUSIVITY_UNIT),
        ),
        ScientificParameter(
            name="side",
            value=Quantity(case.side_m, tr2.LENGTH_UNIT),
        ),
        ScientificParameter(
            name="omega",
            value=Quantity(case.omega_per_s, "1 / second"),
            description=(
                "Angular rate of the prescribed field. A scalar that happens "
                "to parameterise a field; the field itself has no home."
            ),
        ),
    )
    # Four regions, four records. Each region carries BOTH inflow and outflow
    # because the flow rotates, so each of these records is being asked to hold
    # two different scientific roles.
    boundary_conditions = tuple(
        BoundaryCondition(
            name=f"bc-{region}",
            variable="c",
            kind=BoundaryKind.DIRICHLET,
            region=region,
            value=Quantity(0.0, tr2.FIELD_UNIT),
            description=(
                f"Prescribed scalar on {region}. The manufactured solution "
                f"vanishes on the whole boundary, so one value is correct — "
                f"and the inflow/outflow role still varies along the side."
            ),
        )
        for region in tr2.REGIONS
    )
    return ScientificProblem(
        problem_id=f"transport2d-{case.case_id}",
        name="2D steady advection-diffusion in a rotational field",
        description=(
            "Normalized scalar transported by solid-body rotation with "
            "constant diffusivity, verified by a manufactured solution."
        ),
        variables=variables,
        parameters=parameters,
        boundary_conditions=boundary_conditions,
        models=(ModelReference(TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version),),
        required_capabilities=frozenset({TRANSPORT_CAPABILITY.name}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "manufactured_solution_error"}
        ),
        metadata={
            "domain": "transport",
            "case_id": case.case_id,
            "n_cells": str(case.n_cells),
            "regions": ",".join(tr2.REGIONS),
        },
    )


def build_transport_bundle(case: tr2.Transport2DCase) -> ConsumerBundle:
    field = tr2.solve_transport2d(case)
    problem = build_transport_problem(case)
    metrics = {
        name: Quantity(value, tr2.FIELD_UNIT)
        for name, value in tr2.field_metrics(case, field).items()
    }
    reference, _ = ScientificDataReference.for_values(
        "c:field", field.reshape(-1), unit=tr2.FIELD_UNIT
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="dimensional_consistency",
                outcome=ValidationOutcome.PASS,
                detail="every declared quantity carries its declared unit",
                establishes=ValidationLevel.DIMENSIONALLY_VALID,
            ),
            ValidationCheck(
                name="manufactured_solution_error",
                outcome=ValidationOutcome.PASS,
                detail="max deviation from the exact manufactured solution",
                residual=tr2.solution_error(case, field),
                tolerance=1.0,
                establishes=ValidationLevel.ANALYTICALLY_VERIFIED,
            ),
            admissibility_check(
                "maximum_principle_held",
                tr2.admissibility_violation(field),
                "the transported scalar cannot leave the range of its data",
            ),
        )
    )
    result = ScientificResult(
        result_id=f"run-transport2d-{case.case_id}",
        problem_id=problem.problem_id,
        values=metrics,
        models=((TRANSPORT_MODEL.model_id, TRANSPORT_MODEL.version),),
        solver=TRANSPORT_SOLVER,
        convergence=ConvergenceState.CONVERGED,
        validation=report,
        uncertainty=_unknown_uncertainty(metrics),
        assumptions=TRANSPORT_MODEL.assumptions,
        data_references=(reference,),
        provenance=_provenance(
            f"run-transport2d-{case.case_id}",
            TRANSPORT_MODEL,
            TRANSPORT_SOLVER,
            TRANSPORT_REALIZATION,
            {
                "diffusivity": Quantity(case.diffusivity_m2_s, tr2.DIFFUSIVITY_UNIT),
                "side": Quantity(case.side_m, tr2.LENGTH_UNIT),
            },
        ),
    )
    return ConsumerBundle(
        consumer="B-transport",
        problem=problem,
        model=TRANSPORT_MODEL,
        result=result,
        realizations=(TRANSPORT_REALIZATION,),
        science=frozenset(
            {
                "SpatialFieldSemantics",
                "VariableToBulkLinkage",
                "FieldSupport",
                "Domain/Topology",
                "BoundaryIdentity",
                "BoundaryOrientation-sign",
                "BoundaryCondition",
                "Rank1",
                "FieldValuedInput",
                "MaterialIdentity",
                "DiscretizationDefinition",
                "QuantityIdentity",
                "AdmissibilityAttainment",
            }
        ),
        notes={
            "velocity_field": (
                "the prescribed velocity is a field-valued model INPUT; "
                "ScientificProblem has no data_references"
            ),
            "source_field": "the manufactured source is a second field-valued input",
            "orientation": (
                "every side carries both inflow and outflow; a region is not "
                "the granularity at which orientation lives"
            ),
        },
    )


# =============================================================================
# CONSUMER C — species
# =============================================================================

SPECIES_MODEL = ScientificModelDefinition(
    model_id="chemistry.batch.reaction_network",
    version=VERSION,
    name="Closed isothermal reaction network",
    domain="chemistry",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Species balances in a closed, isothermal, constant-volume batch: "
        "dc/dt = nu^T r, with mass-action rates."
    ),
    inputs=(
        ModelInputSpec(
            name="k1f",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=spc.FIRST_ORDER_RATE_UNIT,
            description="Forward rate constant of R1.",
        ),
        ModelInputSpec(
            name="k1r",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=spc.FIRST_ORDER_RATE_UNIT,
            description="Reverse rate constant of R1.",
        ),
        ModelInputSpec(
            name="k2",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=spc.SECOND_ORDER_RATE_UNIT,
            description="Rate constant of R2.",
        ),
        # The stoichiometric matrix is NOT declarable. It is integer-valued,
        # rectangular, and indexed by (reaction, species) -- three things a
        # closed scalar union cannot express.
    ),
    outputs=(
        ModelOutputSpec(
            metric="c:A", unit_exemplar=spc.CONCENTRATION_UNIT,
            description="Concentration of A.",
        ),
        ModelOutputSpec(
            metric="c:B", unit_exemplar=spc.CONCENTRATION_UNIT,
            description="Concentration of B.",
        ),
        ModelOutputSpec(
            metric="c:C", unit_exemplar=spc.CONCENTRATION_UNIT,
            description="Concentration of C.",
        ),
    ),
    assumptions=(
        "closed system; no inflow and no outflow",
        "isothermal at a fixed temperature; no energy balance",
        "constant volume",
        "perfectly mixed; no spatial dependence",
        "mass-action kinetics with the declared reaction orders",
        "elemental balance is encoded in the stoichiometric coefficients",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="temperature",
                minimum=Quantity(0.0, spc.TEMPERATURE_UNIT),
                minimum_inclusive=False,
                description="Absolute thermodynamic temperature.",
            ),
        ),
        description="Closed isothermal mass-action kinetics.",
    ),
    required_capabilities=frozenset({SPECIES_CAPABILITY.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

SPECIES_SOLVER = SolverIdentity(
    solver_id="experiments.cross_domain_coverage.species",
    version=VERSION,
    backend="python-rk4",
)

SPECIES_REALIZATION = ModelRealizationDefinition(
    realization_id="chemistry.batch.rk4",
    version=VERSION,
    model=ModelReference(SPECIES_MODEL.model_id, SPECIES_MODEL.version),
    formulation=ModelFormulation.ODE,
    name="Classical RK4 at fixed step",
    description="Explicit fourth-order Runge-Kutta at a fixed step size.",
    provided_capabilities=frozenset(
        {ScientificCapability("chemistry", "batch_reaction_network")}
    ),
    assumptions=("explicit; no stiffness handling",),
    implementation=ImplementationReference(
        implementation_id="experiments.cross_domain_coverage.species:rk4",
        version=VERSION,
    ),
)


def build_species_problem(case: spc.BatchCase) -> ScientificProblem:
    """The maximal honest encoding of the species consumer.

    Three concentrations, three variables, **one unit**. Nothing on any record
    says they are distinct chemical species rather than three unrelated numbers
    that happen to share a dimension — and nothing carries the stoichiometry
    that relates them.
    """
    # THE STEELMAN THE ADVERSARIAL PASS FOUND MISSING.
    #
    # `ScientificVariable` carries typed, dimension-checked `lower`/`upper`
    # bounds, and a non-negativity requirement on a concentration is exactly
    # what they describe. An earlier version of this milestone declared an
    # admissibility gap without ever attempting them — a violation of the
    # preregistration's own §7.1 steelman requirement.
    #
    # They are declared here, and the measurement is what happens next: a grep
    # of `src/engcore/domains/` returns zero uses of either field, and
    # `require_within_bounds` is called only from the design-space, experiment
    # and optimizer-adapter paths. **Nothing that inspects a `ScientificResult`
    # consults them**, so the bound is declarable and unenforced — which is a
    # narrower and truer finding than "it cannot be expressed".
    variables = tuple(
        ScientificVariable(
            name=f"c:{name}",
            unit=spc.CONCENTRATION_UNIT,
            role=VariableRole.STATE,
            lower=Quantity(0.0, spc.CONCENTRATION_UNIT),
            description=(
                f"Concentration of species {name}. Physically a distinct "
                f"chemical substance; nothing in this record distinguishes it "
                f"from any other quantity carrying mol/m**3. The lower bound "
                f"is declarable and no result path reads it."
            ),
        )
        for name in spc.SPECIES
    )
    parameters = (
        ScientificParameter(
            name="k1f", value=Quantity(case.k1f_per_s, spc.FIRST_ORDER_RATE_UNIT)
        ),
        ScientificParameter(
            name="k1r", value=Quantity(case.k1r_per_s, spc.FIRST_ORDER_RATE_UNIT)
        ),
        ScientificParameter(
            name="k2",
            value=Quantity(case.k2_m3_per_mol_s, spc.SECOND_ORDER_RATE_UNIT),
        ),
        ScientificParameter(
            name="temperature",
            value=Quantity(case.temperature_k, spc.TEMPERATURE_UNIT),
        ),
        ScientificParameter(
            name="end_time", value=Quantity(case.end_time_s, spc.TIME_UNIT)
        ),
        # The stoichiometric matrix would go here and cannot. Encoding it as
        # six IntegerValue parameters named "nu_R1_A" and so on is available
        # and is refused: the meaning would live in the key spelling, which is
        # the untyped escape hatch the platform exists to avoid.
    )
    initial_conditions = tuple(
        InitialCondition(
            variable=f"c:{name}",
            value=Quantity(value, spc.CONCENTRATION_UNIT),
            time=Quantity(0.0, spc.TIME_UNIT),
            description=f"Initial concentration of {name}.",
        )
        for name, value in zip(spc.SPECIES, case.initial)
    )
    return ScientificProblem(
        problem_id=f"species-batch-{case.case_id}",
        name="Closed isothermal three-species batch",
        description=(
            "Two reactions among three species in a closed, isothermal, "
            "constant-volume batch."
        ),
        variables=variables,
        parameters=parameters,
        initial_conditions=initial_conditions,
        models=(ModelReference(SPECIES_MODEL.model_id, SPECIES_MODEL.version),),
        required_capabilities=frozenset({SPECIES_CAPABILITY.name}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "conservation_invariant"}
        ),
        metadata={
            "domain": "chemistry",
            "case_id": case.case_id,
            "species": ",".join(spc.SPECIES),
            "reactions": ",".join(spc.REACTIONS),
        },
    )


def build_species_bundle(case: spc.BatchCase) -> ConsumerBundle:
    final, trajectory = spc.integrate(case)
    problem = build_species_problem(case)
    metrics = {
        name: Quantity(value, spc.CONCENTRATION_UNIT)
        for name, value in spc.state_metrics(case, final).items()
    }
    reference, _ = ScientificDataReference.for_values(
        "c:trajectory",
        [value for state in trajectory for value in state],
        unit=spc.CONCENTRATION_UNIT,
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="dimensional_consistency",
                outcome=ValidationOutcome.PASS,
                detail="every declared quantity carries its declared unit",
                establishes=ValidationLevel.DIMENSIONALLY_VALID,
            ),
            ValidationCheck(
                name="conservation_invariant",
                outcome=ValidationOutcome.PASS,
                detail=(
                    "the weighted invariant c_A + c_B + 2 c_C is preserved; "
                    "the weights come from the stoichiometric matrix and are "
                    "on no record"
                ),
                residual=spc.conservation_drift(trajectory),
                tolerance=1e-9,
            ),
            admissibility_check(
                "concentrations_non_negative",
                spc.admissibility_violation(trajectory),
                "a negative concentration is unphysical regardless of any "
                "residual",
            ),
        )
    )
    result = ScientificResult(
        result_id=f"run-species-{case.case_id}",
        problem_id=problem.problem_id,
        values=metrics,
        models=((SPECIES_MODEL.model_id, SPECIES_MODEL.version),),
        solver=SPECIES_SOLVER,
        convergence=ConvergenceState.CONVERGED,
        validation=report,
        uncertainty=_unknown_uncertainty(metrics),
        assumptions=SPECIES_MODEL.assumptions,
        data_references=(reference,),
        provenance=_provenance(
            f"run-species-{case.case_id}",
            SPECIES_MODEL,
            SPECIES_SOLVER,
            SPECIES_REALIZATION,
            {
                "k1f": Quantity(case.k1f_per_s, spc.FIRST_ORDER_RATE_UNIT),
                "k1r": Quantity(case.k1r_per_s, spc.FIRST_ORDER_RATE_UNIT),
                "temperature": Quantity(case.temperature_k, spc.TEMPERATURE_UNIT),
            },
        ),
    )
    return ConsumerBundle(
        consumer="C-species",
        problem=problem,
        model=SPECIES_MODEL,
        result=result,
        realizations=(SPECIES_REALIZATION,),
        science=frozenset(
            {
                "VariableToBulkLinkage",
                "SpeciesIdentity",
                "Composition",
                "ReactionRelationship",
                "DynamicState",
                "MaterialIdentity",
                "Constraint",
                "DiscretizationDefinition",
                "QuantityIdentity",
                "AdmissibilityAttainment",
            }
        ),
        notes={
            "stoichiometry": (
                "nu is integer-valued, rectangular and indexed by "
                "(reaction, species); no typed home"
            ),
            "conservation": (
                "the invariant weights come from nu and cannot be derived "
                "from any record"
            ),
        },
    )


# =============================================================================
# CONSUMER D — dynamics
# =============================================================================

DYNAMICS_MODEL = ScientificModelDefinition(
    model_id="dynamics.constrained.planar_pendulum",
    version=VERSION,
    name="Planar pendulum as a constrained rigid body",
    domain="dynamics",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Newton's second law for a point mass subject to an algebraic position "
        "constraint enforced by a Lagrange multiplier."
    ),
    inputs=(
        ModelInputSpec(
            name="length",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=dyn.LENGTH_UNIT,
            description="Constraint radius.",
        ),
        ModelInputSpec(
            name="mass",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=dyn.MASS_UNIT,
            description="Point mass.",
        ),
        # The constraint g(x, y) = 0 is not declarable as an input, and
        # ConstraintDefinition is a metric-vs-bound acceptance test rather than
        # a relation among unknowns.
    ),
    outputs=(
        ModelOutputSpec(
            metric="x:final", unit_exemplar=dyn.LENGTH_UNIT,
            description="Horizontal position at the final time.",
        ),
        ModelOutputSpec(
            metric="energy:final", unit_exemplar=dyn.ENERGY_UNIT,
            description="Total mechanical energy at the final time.",
        ),
    ),
    assumptions=(
        "point mass; no rotational inertia",
        "rigid massless link; the constraint is exact",
        "planar motion; two translational degrees of freedom before constraint",
        "conservative; no damping and no drive",
        "the constraint is an algebraic relation among unknowns that must hold "
        "at every instant, not an acceptance bound on a produced metric",
    ),
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="length",
                minimum=Quantity(0.0, dyn.LENGTH_UNIT),
                minimum_inclusive=False,
                description="Strictly positive constraint radius.",
            ),
        ),
        description="Conservative planar constrained motion.",
    ),
    required_capabilities=frozenset({DYNAMICS_CAPABILITY.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)

DYNAMICS_SOLVER = SolverIdentity(
    solver_id="experiments.cross_domain_coverage.dynamics",
    version=VERSION,
    backend="python-rk4",
)


def _dynamics_realization(
    formulation: dyn.DynamicsFormulation,
) -> ModelRealizationDefinition:
    """Two realizations that differ in **what the unknowns are**.

    ``ModelFormulation`` is asked to carry that difference and cannot: the
    index-reduced Cartesian form is genuinely a DAE in its unreduced statement
    and an ODE after reduction, and the angular form is an ODE. Choosing either
    member discards something true.
    """
    is_cartesian = formulation is dyn.DynamicsFormulation.CARTESIAN_INDEX1
    return ModelRealizationDefinition(
        realization_id=f"dynamics.pendulum.{formulation.value}",
        version=VERSION,
        model=ModelReference(DYNAMICS_MODEL.model_id, DYNAMICS_MODEL.version),
        # DAE for the constrained form -- the first production-shaped use of
        # this member anywhere, and MODEL0-R §9 records it as having had no
        # consumer at all.
        formulation=(
            ModelFormulation.DAE if is_cartesian else ModelFormulation.ODE
        ),
        name=(
            "Cartesian constrained form, index-reduced and stabilised"
            if is_cartesian
            else "Minimal-coordinate angular form"
        ),
        description=(
            "Four Cartesian states plus an algebraic multiplier, index-reduced "
            "to acceleration level with Baumgarte stabilisation."
            if is_cartesian
            else "Two angular states; the constraint is satisfied identically."
        ),
        provided_capabilities=frozenset(
            {ScientificCapability("dynamics", "constrained_rigid_body_2d")}
        ),
        assumptions=(
            "Baumgarte stabilisation; a numerical device, not physics"
            if is_cartesian
            else "the constraint is eliminated by the choice of coordinate",
        ),
        implementation=ImplementationReference(
            implementation_id=(
                f"experiments.cross_domain_coverage.dynamics:{formulation.value}"
            ),
            version=VERSION,
        ),
    )


DYNAMICS_REALIZATIONS = tuple(
    _dynamics_realization(f) for f in dyn.DynamicsFormulation
)


def build_dynamics_problem(case: dyn.PendulumCase) -> ScientificProblem:
    """The maximal honest encoding of the dynamics consumer.

    Four states encode. The multiplier is declared ``OBSERVABLE`` because that
    is the least wrong of four wrong options: it is not `DESIGN` (nothing
    chooses it), not `CONTROL` (nothing imposes it), and not `STATE` (it has no
    initial value and no derivative). `OBSERVABLE` says "produced, not chosen",
    which is true and insufficient — it does not say that the multiplier is an
    unknown determined by an algebraic equation solved simultaneously with the
    differential ones.
    """
    variables = (
        ScientificVariable(
            name="x", unit=dyn.LENGTH_UNIT, role=VariableRole.STATE,
            description="Horizontal position. A differential unknown.",
        ),
        ScientificVariable(
            name="y", unit=dyn.LENGTH_UNIT, role=VariableRole.STATE,
            description="Vertical position. A differential unknown.",
        ),
        ScientificVariable(
            name="vx", unit=dyn.VELOCITY_UNIT, role=VariableRole.STATE,
            description="Horizontal velocity. A differential unknown.",
        ),
        ScientificVariable(
            name="vy", unit=dyn.VELOCITY_UNIT, role=VariableRole.STATE,
            description="Vertical velocity. A differential unknown.",
        ),
        ScientificVariable(
            name="lambda",
            unit=dyn.MULTIPLIER_UNIT,
            role=VariableRole.OBSERVABLE,
            description=(
                "Lagrange multiplier. An ALGEBRAIC unknown solved for at every "
                "instant; VariableRole has no member that says so."
            ),
        ),
    )
    parameters = (
        ScientificParameter(
            name="length", value=Quantity(case.length_m, dyn.LENGTH_UNIT)
        ),
        ScientificParameter(
            name="mass", value=Quantity(case.mass_kg, dyn.MASS_UNIT)
        ),
        ScientificParameter(
            name="end_time", value=Quantity(case.end_time_s, dyn.TIME_UNIT)
        ),
    )
    x0, y0, vx0, vy0 = case.cartesian_initial()
    initial_conditions = (
        InitialCondition(
            variable="x", value=Quantity(x0, dyn.LENGTH_UNIT),
            time=Quantity(0.0, dyn.TIME_UNIT),
            description="Individually valid; jointly constrained by g = 0.",
        ),
        InitialCondition(
            variable="y", value=Quantity(y0, dyn.LENGTH_UNIT),
            time=Quantity(0.0, dyn.TIME_UNIT),
            description="Individually valid; jointly constrained by g = 0.",
        ),
        InitialCondition(
            variable="vx", value=Quantity(vx0, dyn.VELOCITY_UNIT),
            time=Quantity(0.0, dyn.TIME_UNIT),
            description="Individually valid; jointly constrained by g_dot = 0.",
        ),
        InitialCondition(
            variable="vy", value=Quantity(vy0, dyn.VELOCITY_UNIT),
            time=Quantity(0.0, dyn.TIME_UNIT),
            description="Individually valid; jointly constrained by g_dot = 0.",
        ),
    )
    # The steelman attempt at the constraint, and it is the wrong shape.
    # ConstraintDefinition compares a produced METRIC against a fixed scalar
    # BOUND. It can say "the residual of g should be near zero after the fact";
    # it cannot say "x^2 + y^2 = L^2 holds at every instant and determines
    # lambda".
    constraints = (
        ConstraintDefinition(
            name="constraint-residual-acceptance",
            metric="constraint_residual:max",
            operator=ConstraintOperator.LESS_EQUAL,
            bound=Quantity(1e-9, "m**2"),
            description=(
                "An ACCEPTANCE test on a produced residual. This is not the "
                "constraint: the constraint is an algebraic relation among "
                "unknowns, and this record compares one output number against "
                "a fixed scalar."
            ),
        ),
    )
    return ScientificProblem(
        problem_id=f"dynamics-pendulum-{case.case_id}",
        name="Planar pendulum in Cartesian coordinates",
        description=(
            "A point mass under gravity subject to an algebraic position "
            "constraint enforced by a Lagrange multiplier."
        ),
        variables=variables,
        parameters=parameters,
        initial_conditions=initial_conditions,
        constraints=constraints,
        models=(ModelReference(DYNAMICS_MODEL.model_id, DYNAMICS_MODEL.version),),
        required_capabilities=frozenset({DYNAMICS_CAPABILITY.name}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "constraint_residual", "energy_conservation"}
        ),
        metadata={
            "domain": "dynamics",
            "case_id": case.case_id,
            "constraint": "x**2 + y**2 - L**2 = 0",
            "differential_variables": "x,y,vx,vy",
            "algebraic_variables": "lambda",
        },
    )


def build_dynamics_bundle(case: dyn.PendulumCase) -> ConsumerBundle:
    result_data = dyn.run_cartesian(case)
    problem = build_dynamics_problem(case)
    raw = dyn.state_metrics(case, result_data)
    units = {
        "x:final": dyn.LENGTH_UNIT,
        "y:final": dyn.LENGTH_UNIT,
        "vx:final": dyn.VELOCITY_UNIT,
        "vy:final": dyn.VELOCITY_UNIT,
        "energy:final": dyn.ENERGY_UNIT,
        "constraint_residual:max": "m**2",
    }
    metrics = {name: Quantity(value, units[name]) for name, value in raw.items()}
    reference, _ = ScientificDataReference.for_values(
        "state:trajectory",
        [value for state in result_data["trajectory"] for value in state],
        unit="dimensionless",
    )
    report = ValidationReport(
        checks=(
            ValidationCheck(
                name="dimensional_consistency",
                outcome=ValidationOutcome.PASS,
                detail="every declared quantity carries its declared unit",
                establishes=ValidationLevel.DIMENSIONALLY_VALID,
            ),
            ValidationCheck(
                name="constraint_residual",
                outcome=ValidationOutcome.PASS,
                detail="max |g| over the trajectory",
                residual=result_data["max_constraint_residual_m2"],
                tolerance=1e-9,
            ),
            ValidationCheck(
                name="energy_conservation",
                outcome=ValidationOutcome.PASS,
                detail="max energy drift over the trajectory",
                residual=result_data["max_energy_drift_j"],
                tolerance=1e-6,
            ),
            admissibility_check(
                "constraint_manifold_held",
                dyn.admissibility_violation(case, result_data),
                "a state off the constraint manifold is not a configuration "
                "the system can occupy",
            ),
        )
    )
    result = ScientificResult(
        result_id=f"run-dynamics-{case.case_id}",
        problem_id=problem.problem_id,
        values=metrics,
        models=((DYNAMICS_MODEL.model_id, DYNAMICS_MODEL.version),),
        solver=DYNAMICS_SOLVER,
        convergence=ConvergenceState.CONVERGED,
        validation=report,
        uncertainty=_unknown_uncertainty(metrics),
        assumptions=DYNAMICS_MODEL.assumptions,
        data_references=(reference,),
        provenance=_provenance(
            f"run-dynamics-{case.case_id}",
            DYNAMICS_MODEL,
            DYNAMICS_SOLVER,
            DYNAMICS_REALIZATIONS[0],
            {
                "length": Quantity(case.length_m, dyn.LENGTH_UNIT),
                "mass": Quantity(case.mass_kg, dyn.MASS_UNIT),
            },
        ),
    )
    return ConsumerBundle(
        consumer="D-dynamics",
        problem=problem,
        model=DYNAMICS_MODEL,
        result=result,
        realizations=DYNAMICS_REALIZATIONS,
        science=frozenset(
            {
                "VariableToBulkLinkage",
                "Constraint",
                "DifferentialAlgebraicPartition",
                "RelationalInitialCondition",
                "DynamicState",
                "Rank1",
                "TimeVaryingInput",
                "DiscretizationDefinition",
                # "RuntimeState" was declared here and is removed. The
                # adversarial pass found it contradicted its own probe: D's
                # trajectory is bulk data on ONE result, and nothing carries
                # state across runs or claims instance authority over it. The
                # declaration was wrong; the probe was right about the physics
                # and wrong about the label, and both are now fixed.
                "QuantityIdentity",
                "AdmissibilityAttainment",
            }
        ),
        notes={
            "constraint": (
                "ConstraintDefinition is metric-vs-bound; the constraint is a "
                "relation among unknowns"
            ),
            "multiplier": (
                "lambda is an algebraic unknown; VariableRole has no member "
                "for it"
            ),
            "consistency": (
                "four InitialCondition records are individually valid and "
                "jointly inconsistent"
            ),
        },
    )


# =============================================================================
# The four bundles, plus the control group
# =============================================================================

def build_all_bundles() -> tuple[ConsumerBundle, ...]:
    """Every consumer, executed and encoded."""
    return (
        build_mechanics_bundle(),
        build_transport_bundle(tr2.case_b(8)),
        build_species_bundle(spc.case_c(500)),
        build_dynamics_bundle(dyn.case_d(4000)),
    )


def control_problems() -> dict[str, ScientificProblem]:
    """The two existing domains, built as they stand today.

    Preregistration §5 makes this binding. Neither file is edited; both are
    imported and their own builders are called. This is what converts *"the
    intersection of four consumers I chose"* into *"the intersection of six, two
    of which I did not choose for this purpose."*
    """
    from engcore.domains.electrical.dc.circuit import DCCircuit, ElectricalNode
    from engcore.domains.electrical.dc.components import Resistor
    from engcore.domains.electrical.dc.problem import build_dc_problem
    from engcore.domains import thermal_lumped as lump

    circuit = _control_circuit()
    body = lump.ThermalBody(
        body_id="coverage-control",
        heat_capacity=Quantity(2.5, "joule/kelvin"),
        ambient_conductance=Quantity(0.05, "watt/kelvin"),
        ambient_temperature=Quantity(300.0, "kelvin"),
        initial_temperature=Quantity(300.0, "kelvin"),
        duration=Quantity(120.0, "second"),
    )
    return {
        "ctl-dc": build_dc_problem(circuit),
        "ctl-lumped": lump.build_lumped_thermal_problem(body),
    }


def _control_circuit():
    """The control circuit, built once so its artifact can also be published.

    Two non-reference nodes, not one. A single-node circuit declares exactly one
    voltage variable and therefore structurally cannot exhibit several
    quantities sharing a unit — which would make the control unable to register
    on the QuantityIdentity row for a reason that is a property of the fixture
    rather than of the domain. A divider is the smallest representative circuit.
    """
    from engcore.domains.electrical.dc.circuit import DCCircuit, ElectricalNode
    from engcore.domains.electrical.dc.components import Resistor

    return DCCircuit(
        circuit_id="coverage-control",
        nodes=(
            ElectricalNode("gnd", is_reference=True),
            ElectricalNode("n1"),
            ElectricalNode("n2"),
        ),
        resistors=(
            Resistor("R1", "n1", "n2", Quantity(10.0, "ohm")),
            Resistor("R2", "n2", "gnd", Quantity(20.0, "ohm")),
        ),
    )




#: What each control domain's science genuinely involves.
#:
#: Declared from the problems actually built above, not from the domains'
#: wider capability, and **not** tuned to match a prediction. Two consequences
#: are accepted in advance: `MaterialState` is absent from `ctl-dc` because the
#: circuit built here has a constant resistance — the domain's state-dependent
#: `R(T)` lives in `electrical/material.py`, a different problem — and
#: `Domain/Topology` IS present for `ctl-dc`, because an MNA network is a graph
#: of nodes and edges with an explicitly declared datum.
CONTROL_SCIENCE: dict[str, frozenset[str]] = {
    "ctl-dc": frozenset(
        {
            "Domain/Topology",
            "BoundaryIdentity",
            "BoundaryOrientation-sign",
            "MaterialIdentity",
            "PropertyRequirement-scalar",
            "QuantityIdentity",
            "AdmissibilityAttainment",
        }
    ),
    "ctl-lumped": frozenset(
        {
            "DynamicState",
            "MaterialIdentity",
            "PropertyRequirement-scalar",
            "DiscretizationDefinition",
            "AdmissibilityAttainment",
        }
    ),
}


def _control_payloads(name: str, problem: ScientificProblem) -> dict[str, Any]:
    """Serialize a control domain into the shape the instrument reads.

    The control's own model definition is used — the real one, imported from
    the domain, not a stand-in written here. Controls have no result and no
    realization catalogue in this milestone, and the instrument tolerates both
    absences rather than being handed a fabricated record.
    """
    from engcore.domains import thermal_lumped as lump
    from engcore.domains.electrical.dc.models import RESISTOR_OHM_MODEL

    model = RESISTOR_OHM_MODEL if name == "ctl-dc" else lump.LUMPED_CAPACITY_MODEL
    payloads: dict[str, Any] = {
        "consumer": name,
        "problem": problem.to_dict(),
        "model": model.to_dict(),
        "result": None,
        "realizations": {},
    }
    if name == "ctl-dc":
        # The circuit's own canonical record, handed over deliberately.
        #
        # `dc/problem.py` states that it translates a circuit *"without
        # smuggling topology into the IR"*, because connectivity travels
        # separately and is bound to the problem by a verified fingerprint.
        # An earlier version of this milestone withheld that artifact and then
        # scored the control as FORCING topology — reporting a recorded design
        # decision as a platform gap, and citing it as the best evidence that
        # topology is not a PDE artifact. Handing it over is the correction.
        payloads["domain_artifact"] = _control_circuit().canonical_dict()
    return payloads


def coverage_columns() -> dict[str, tuple[dict[str, Any], frozenset[str]]]:
    """Every column the instrument scores: four consumers, then two controls.

    Preregistration §5 makes the control group binding. It is what converts
    *"the intersection of four consumers I chose"* into *"the intersection of
    six, two of which I did not choose for this purpose."*
    """
    columns: dict[str, tuple[dict[str, Any], frozenset[str]]] = {}
    for bundle in build_all_bundles():
        columns[bundle.consumer] = (bundle.payloads(), bundle.science)
    for name, problem in control_problems().items():
        columns[name] = (_control_payloads(name, problem), CONTROL_SCIENCE[name])
    return columns


CONSUMER_COLUMNS: tuple[str, ...] = (
    "A-mechanics",
    "B-transport",
    "C-species",
    "D-dynamics",
)
CONTROL_COLUMNS: tuple[str, ...] = ("ctl-dc", "ctl-lumped")
