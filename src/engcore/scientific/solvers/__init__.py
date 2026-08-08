"""Solver contracts. No backend adapters are implemented in the core."""

from .capability import CoreCapabilities, SolverCapability, capability_names
from .protocol import (
    ConvergenceState,
    PreparedSolve,
    RawSolverOutput,
    ScientificSolver,
    SolverIdentity,
    SolverSettings,
    capability_gap,
)
from .registry import SolverRegistry

__all__ = [
    "CoreCapabilities",
    "SolverCapability",
    "capability_names",
    "ConvergenceState",
    "PreparedSolve",
    "RawSolverOutput",
    "ScientificSolver",
    "SolverIdentity",
    "SolverSettings",
    "capability_gap",
    "SolverRegistry",
]
