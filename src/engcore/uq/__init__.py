"""Shared quantified-uncertainty capabilities.

K3 pulls the first reusable implementation: posterior-predictive uncertainty
from an admitted posterior support and admitted forward predictions.
"""

from .predictive import (
    PredictiveObservableSpec,
    QuantifiedPredictiveResult,
    UQProblemError,
    posterior_predictive_uq,
)

__all__ = [
    "PredictiveObservableSpec",
    "QuantifiedPredictiveResult",
    "UQProblemError",
    "posterior_predictive_uq",
]
