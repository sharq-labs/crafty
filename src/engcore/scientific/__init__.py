"""Scientific Core V0 — domain-neutral contracts for scientific computation.

Principle
---------
We do not reinvent decades of validated scientific work, and we do not reduce
our platform to a thin wrapper around existing packages.

What this package owns: the scientific IR, model representation and validity,
solver orchestration contracts, validation semantics, uncertainty, provenance,
experiment representation, and the optimizer integration boundary.

What it deliberately does not own: numerical algorithms. Mature libraries
(SciPy, SUNDIALS, FEniCSx, Cantera, ngspice, ...) will be reached through
adapters that satisfy :class:`~engcore.scientific.solvers.ScientificSolver`.

Independence
------------
Nothing here imports an LLM provider, a web framework, a database, or a
visualization layer — and nothing may. If every AI provider disappeared, the
Scientific Core would remain fully usable.

Status: **V0 foundation.** Contracts only; no physical domain is implemented.
"""

from __future__ import annotations

from .errors import (
    AmbiguousSolverError,
    DuplicateRegistrationError,
    InvalidScientificProblem,
    ModelNotFoundError,
    ModelValidityError,
    ScientificCoreError,
    ScientificValidationError,
    SolverNotFoundError,
    UnitCompatibilityError,
)
from .experiments import (
    CandidateCodec,
    EvaluationStatus,
    ExperimentBudget,
    NumericSearchBackend,
    ObjectiveEncoder,
    OptimizerAdapter,
    ScientificEvaluation,
    ScientificExperiment,
)
from .ir import (
    BoundaryCondition,
    BoundaryKind,
    ConstraintCheck,
    ConstraintDefinition,
    ConstraintOperator,
    InitialCondition,
    ModelReference,
    ObjectiveDefinition,
    ObjectiveDirection,
    ScientificParameter,
    ScientificProblem,
    ScientificVariable,
    UncertaintyRequirement,
    UncertaintySpecification,
    VariableKind,
    VariableRole,
)
from .models import (
    CategoryCondition,
    FlagCondition,
    ModelRegistry,
    ModelType,
    ModelValidationStatus,
    RangeCondition,
    ScientificModelDefinition,
    ValidityAssessment,
    ValidityDomain,
    ValidityStatus,
)
from .results import (
    ProvenanceRecord,
    ScientificResult,
    Uncertainty,
    UncertaintyKind,
    ValidationCheck,
    ValidationLevel,
    ValidationOutcome,
    ValidationReport,
    unverified_report,
)
from .serialization import to_json
from .solvers import (
    ConvergenceState,
    CoreCapabilities,
    PreparedSolve,
    RawSolverOutput,
    ScientificSolver,
    SolverCapability,
    SolverIdentity,
    SolverRegistry,
    SolverSettings,
)
from .units import Quantity, coerce_quantity, dimensionality, normalize_unit

SCIENTIFIC_CORE_VERSION = "0.1.0-v0-foundation"

__all__ = [
    "SCIENTIFIC_CORE_VERSION",
    # errors
    "ScientificCoreError",
    "InvalidScientificProblem",
    "UnitCompatibilityError",
    "ModelNotFoundError",
    "ModelValidityError",
    "SolverNotFoundError",
    "AmbiguousSolverError",
    "DuplicateRegistrationError",
    "ScientificValidationError",
    # units
    "Quantity",
    "coerce_quantity",
    "dimensionality",
    "normalize_unit",
    # ir
    "ScientificProblem",
    "ScientificVariable",
    "ScientificParameter",
    "VariableKind",
    "VariableRole",
    "ObjectiveDefinition",
    "ObjectiveDirection",
    "ConstraintDefinition",
    "ConstraintOperator",
    "ConstraintCheck",
    "InitialCondition",
    "BoundaryCondition",
    "BoundaryKind",
    "ModelReference",
    "UncertaintySpecification",
    "UncertaintyRequirement",
    # models
    "ScientificModelDefinition",
    "ModelType",
    "ModelValidationStatus",
    "ModelRegistry",
    "ValidityDomain",
    "ValidityStatus",
    "ValidityAssessment",
    "RangeCondition",
    "CategoryCondition",
    "FlagCondition",
    # solvers
    "ScientificSolver",
    "SolverIdentity",
    "SolverSettings",
    "SolverCapability",
    "CoreCapabilities",
    "SolverRegistry",
    "PreparedSolve",
    "RawSolverOutput",
    "ConvergenceState",
    # results
    "ScientificResult",
    "ValidationReport",
    "ValidationCheck",
    "ValidationOutcome",
    "ValidationLevel",
    "unverified_report",
    "Uncertainty",
    "UncertaintyKind",
    "ProvenanceRecord",
    # experiments
    "ScientificExperiment",
    "ExperimentBudget",
    "ScientificEvaluation",
    "EvaluationStatus",
    "OptimizerAdapter",
    "CandidateCodec",
    "ObjectiveEncoder",
    "NumericSearchBackend",
    # serialization
    "to_json",
]
