"""V0.3.4 ablation: frozen stacked search with fresh LOO weights.

This engine exists only to isolate one behavior change discovered during the
V0.3.4 logic review: recomputing the stacking weight after every newly built
posterior / observation set, while preserving the frozen stacked_v0301 search
loop, refit schedule, acquisition, screening, refinement, and evaluation budget.

It is not an adaptive optimizer and must not be used to attribute V0.3.3/D3
results. Its purpose is causal ablation only.
"""

from __future__ import annotations

from .stacked_engine import StackedGPBOEngine


class FreshWeightsStackedGPBOEngine(StackedGPBOEngine):
    """Stacked V0.3.0.1 behavior + one fresh-weight update per BO step."""

    ENGINE_ID = "stacked_fresh_weights_v034"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fresh_weight_updated_at_n: int | None = None

    def _update_stacking_weight(self, rbf_model, matern_model):
        """Avoid duplicate LOO work when the parent run also requests update."""
        n_obs = int(len(self.history))
        if self._fresh_weight_updated_at_n == n_obs:
            return

        super()._update_stacking_weight(rbf_model, matern_model)
        self._fresh_weight_updated_at_n = n_obs

    def _fit_pair(self, optimize):
        """Use the frozen fit schedule, then refresh weights on current data."""
        rbf_model, matern_model = super()._fit_pair(optimize=optimize)
        self._update_stacking_weight(rbf_model, matern_model)
        return rbf_model, matern_model
