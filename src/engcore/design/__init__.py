"""Domain-neutral design and discovery representation contracts."""

from .archives import ParetoArchive, ScopedEliteArchive, dominates
from .candidate import DesignCandidate, DesignCandidateReference
from .evaluation import (
    DesignEvaluation,
    DesignEvaluationReference,
    FidelitySelection,
    ProjectedObjective,
    ResultBinding,
    SelectionEligibility,
    project_objectives,
    require_result_binding,
)
from .fidelity import FidelityLadder, FidelityRung
from .generation import (
    GENERATION_BINDING_METADATA_KEY,
    CandidateGenerationBatch,
    CandidateGenerationPlan,
    CandidateProposal,
    GenerationStrategy,
    ProposalDecision,
    ProposalGate,
    ProposalRejection,
    TwinMaterializer,
    assignment_digest,
    bind_generation_to_twin,
    generate_initial_population,
    generation_binding_payload,
    validate_generation_binding,
)
from .population import DesignPopulation
from .sampling import MixedVariableSampler
from .space import DesignSpace, DesignSpaceReference

__all__ = [
    "GENERATION_BINDING_METADATA_KEY",
    "CandidateGenerationBatch",
    "CandidateGenerationPlan",
    "CandidateProposal",
    "DesignCandidate",
    "DesignCandidateReference",
    "DesignEvaluation",
    "DesignEvaluationReference",
    "DesignPopulation",
    "DesignSpace",
    "DesignSpaceReference",
    "FidelityLadder",
    "FidelityRung",
    "FidelitySelection",
    "GenerationStrategy",
    "MixedVariableSampler",
    "ParetoArchive",
    "ProjectedObjective",
    "ProposalDecision",
    "ProposalGate",
    "ProposalRejection",
    "ResultBinding",
    "ScopedEliteArchive",
    "SelectionEligibility",
    "TwinMaterializer",
    "assignment_digest",
    "bind_generation_to_twin",
    "dominates",
    "generate_initial_population",
    "generation_binding_payload",
    "project_objectives",
    "require_result_binding",
    "validate_generation_binding",
]
