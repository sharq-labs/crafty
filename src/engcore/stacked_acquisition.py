from __future__ import annotations

import math

from botorch.acquisition.acquisition import AcquisitionFunction


class StackedLogAcquisition(AcquisitionFunction):
    """
    Numerically stable mixture of two log-space acquisition functions.

    If the member acquisitions return log(EI_A) and log(EI_B), then

        log(EI_mix)
        = log(w * EI_A + (1 - w) * EI_B)
        = logaddexp(log(w) + logEI_A, log(1-w) + logEI_B).

    The child acquisition functions retain their own fitted models. The base
    AcquisitionFunction model is set to member A only to satisfy BoTorch's
    acquisition API; forward() always evaluates both members explicitly.
    """

    _log = True

    def __init__(self, acq_a, acq_b, weight_a: float):
        super().__init__(model=acq_a.model)

        self.acq_a = acq_a
        self.acq_b = acq_b
        self.weight_a = float(weight_a)

        if not (0.0 < self.weight_a < 1.0):
            raise ValueError("weight_a must be strictly between 0 and 1")

    def forward(self, X):
        import torch

        a = self.acq_a(X)
        b = self.acq_b(X)

        return torch.logaddexp(
            a + math.log(self.weight_a),
            b + math.log1p(-self.weight_a),
        )
