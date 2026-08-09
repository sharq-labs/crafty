"""Domain-neutral design representation contracts."""

from .candidate import DesignCandidate, DesignCandidateReference
from .fidelity import FidelityLadder, FidelityRung
from .space import DesignSpace, DesignSpaceReference

__all__ = [
    "DesignCandidate",
    "DesignCandidateReference",
    "DesignSpace",
    "DesignSpaceReference",
    "FidelityLadder",
    "FidelityRung",
]
