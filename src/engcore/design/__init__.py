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
from .population import DesignPopulation
from .space import DesignSpace, DesignSpaceReference

__all__ = [
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
    "ParetoArchive",
    "ProjectedObjective",
    "ResultBinding",
    "ScopedEliteArchive",
    "SelectionEligibility",
    "dominates",
    "project_objectives",
    "require_result_binding",
]
