"""Domain-local errors.

All inherit one base so a caller can catch the whole domain without catching
the core, and the core never learns these names exist.
"""

from __future__ import annotations


class KineticsCSTRError(Exception):
    """Base for every error raised by the CSTR domain."""


class ReactorConfigurationError(KineticsCSTRError):
    """A declaration is outside the model's validity envelope, or malformed.

    Raised BEFORE any integration is attempted. An input that violates the
    envelope is not a solve that failed; it is a solve that must never run.
    """


class ReactorBindingError(KineticsCSTRError):
    """A problem id was rebound to different physics."""


class IntegrationBudgetExceeded(KineticsCSTRError):
    """The preregistered right-hand-side evaluation budget was exhausted.

    Raised from inside the RHS closure so it propagates out of ``solve_ivp``.
    This is an *explicit computational limit*, not a numerical failure: the
    integration was still making progress when it was stopped. The solver
    adapter catches it and reports MAX_ITERATIONS, which is the existing
    convergence state that means exactly "stopped at a work cap".
    """

    def __init__(self, message: str, *, evaluations: int, budget: int, t: float):
        super().__init__(message)
        self.evaluations = int(evaluations)
        self.budget = int(budget)
        self.t = float(t)
