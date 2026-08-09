"""Shared inference contracts pulled by K1.5 evidence.

Only the numerical-prediction admission boundary exists here today.  Posterior
algorithms, observations, priors and inference backends belong to K2 and are
not pre-invented by this package.
"""

from .admissibility import (
    AdmissibleNumericalPrediction,
    InferenceAdmissibilityError,
    require_admissible_numerical_prediction,
)

__all__ = [
    "AdmissibleNumericalPrediction",
    "InferenceAdmissibilityError",
    "require_admissible_numerical_prediction",
]
