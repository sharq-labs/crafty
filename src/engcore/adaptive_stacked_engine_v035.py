"""V0.3.5 hardening wrapper for the adaptive stacked optimizer.

This module intentionally leaves the registered V0.3.4 implementation frozen.
It fixes two review findings for future experiments:

1. exploration starts are inserted immediately after the best acquisition
   start so they actually participate in the normal refinement path;
2. failure of the optional adaptive proposal degrades safely to the already
   available identity proposal instead of failing the whole optimization run.
"""

from __future__ import annotations

import numpy as np

from .adaptive_stacked_engine import AdaptiveStackedGPBOEngine
from .sampling import sobol_points


class AdaptiveStackedGPBOEngineV035(AdaptiveStackedGPBOEngine):
    """Behavior-hardening successor to ``adaptive_stacked_v034``.

    The V0.3.4 class remains unchanged for scientific reproducibility.
    """

    ENGINE_ID = "adaptive_stacked_v035"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fit_diagnostics.setdefault(
            "adaptive_proposal_generation_failures", 0
        )

    def _mix_exploration_starts(
        self,
        starts,
        start_scores,
        *,
        mix: float,
        seed: int,
    ):
        """Inject exploration starts into positions used by refinement.

        V0.3.4 replaced the *tail* of ``starts``. In the registered fast mode
        only the first few starts are refined, so the exploration points could
        remain outside the normal candidate path. V0.3.5 preserves the best
        acquisition start at position 0 and inserts explorers directly after
        it. With the registered fast configuration (top_k=6, refine_k=3), both
        mild (1 explorer) and severe (2 explorers) adaptation therefore enter
        refinement.
        """

        starts = np.asarray(starts, dtype=np.float64)
        start_scores = np.asarray(start_scores, dtype=np.float64)

        if len(starts) <= 1 or float(mix) <= 0.0:
            return starts, start_scores

        n_replace = int(round(float(mix) * (len(starts) - 1)))
        n_replace = max(0, min(n_replace, len(starts) - 1))
        if n_replace == 0:
            return starts, start_scores

        explorers = sobol_points(
            n_replace,
            self.space.dim,
            int(seed),
        )

        out_x = starts.copy()
        out_s = start_scores.copy()

        # Position zero remains the best acquisition candidate. Put explorers
        # in the earliest refinement-eligible slots rather than at the tail.
        first = 1
        last = first + n_replace
        out_x[first:last] = explorers
        out_s[first:last] = -np.inf
        return out_x, out_s

    def _generate_search_proposal(self, *args, **kwargs):
        """Fail closed to identity when only the adaptive proposal fails.

        The parent run loop has already generated a valid identity proposal
        before it asks for the optional adaptive proposal. Returning ``None``
        here is supported by the safety arbiter and causes identity execution.
        Identity proposal failures still propagate because they indicate the
        baseline search path itself is unusable.
        """

        tag = str(kwargs.get("tag", ""))
        try:
            return super()._generate_search_proposal(*args, **kwargs)
        except Exception as exc:
            if tag != "adaptive":
                raise

            self.fit_diagnostics[
                "adaptive_proposal_generation_failures"
            ] = int(
                self.fit_diagnostics.get(
                    "adaptive_proposal_generation_failures", 0
                )
            ) + 1

            self.events.append({
                "event": "adaptive_proposal_generation_failure",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "fallback": "identity",
            })
            return None
