"""V0.3.5 hardening wrapper for the adaptive stacked optimizer.

This module intentionally leaves the registered V0.3.4 implementation frozen.
It fixes review findings for future experiments:

1. exploration starts are inserted immediately after the best acquisition
   start so they participate in the normal refinement path;
2. exploration is capped to slots that refinement can actually consume, so a
   custom ``refinement_top_k`` cannot create dead exploratory starts;
3. failure of the optional adaptive proposal degrades safely to the already
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
        self.fit_diagnostics.setdefault(
            "adaptive_exploration_starts_capped", 0
        )
        self.fit_diagnostics.setdefault(
            "adaptive_exploration_mix_disabled", 0
        )

    def _record_exploration_cap(
        self,
        *,
        requested: int,
        used: int,
        visible_slots: int,
    ) -> None:
        if requested <= used:
            return

        diagnostics = getattr(self, "fit_diagnostics", None)
        events = getattr(self, "events", None)

        if isinstance(diagnostics, dict):
            diagnostics["adaptive_exploration_starts_capped"] = int(
                diagnostics.get("adaptive_exploration_starts_capped", 0)
            ) + int(requested - used)
            if used == 0:
                diagnostics["adaptive_exploration_mix_disabled"] = int(
                    diagnostics.get("adaptive_exploration_mix_disabled", 0)
                ) + 1

        if isinstance(events, list):
            events.append({
                "event": "adaptive_exploration_mix_capped",
                "requested_explorers": int(requested),
                "used_explorers": int(used),
                "refinement_visible_slots": int(visible_slots),
            })

    def _mix_exploration_starts(
        self,
        starts,
        start_scores,
        *,
        mix: float,
        seed: int,
    ):
        """Inject only explorers that can enter the refinement slice.

        Position zero remains the best acquisition candidate. Explorers occupy
        the earliest slots after it, but their count is capped by
        ``refinement_top_k - 1`` for the current proposal. If a custom
        configuration exposes no refinement slot beyond the best candidate,
        exploration mixing is explicitly disabled rather than generating dead
        Sobol starts that can never participate in the normal candidate path.
        """

        starts = np.asarray(starts, dtype=np.float64)
        start_scores = np.asarray(start_scores, dtype=np.float64)

        if len(starts) <= 1 or float(mix) <= 0.0:
            return starts, start_scores

        requested = int(round(float(mix) * (len(starts) - 1)))
        requested = max(0, min(requested, len(starts) - 1))
        if requested == 0:
            return starts, start_scores

        # Direct helper calls (e.g. focused tests) have no proposal context and
        # therefore default to all post-best slots being refinement-visible.
        visible_slots = int(
            getattr(
                self,
                "_v035_refinement_visible_slots",
                len(starts) - 1,
            )
        )
        visible_slots = max(0, min(visible_slots, len(starts) - 1))
        n_replace = min(requested, visible_slots)

        self._record_exploration_cap(
            requested=requested,
            used=n_replace,
            visible_slots=visible_slots,
        )

        if n_replace == 0:
            return starts, start_scores

        explorers = sobol_points(
            n_replace,
            self.space.dim,
            int(seed),
        )

        out_x = starts.copy()
        out_s = start_scores.copy()
        first = 1
        last = first + n_replace
        out_x[first:last] = explorers
        out_s[first:last] = -np.inf
        return out_x, out_s

    def _generate_search_proposal(self, *args, **kwargs):
        """Bound exploration to refinement slots and fail adaptive safely.

        The parent run loop has already generated a valid identity proposal
        before it asks for the optional adaptive proposal. Returning ``None``
        for an adaptive-only generation failure is supported by the safety
        arbiter and causes identity execution. Identity proposal failures still
        propagate because the mandatory baseline search path is then unusable.
        """

        tag = str(kwargs.get("tag", ""))
        knobs = kwargs.get("knobs")
        previous_visible = getattr(
            self, "_v035_refinement_visible_slots", None
        )
        had_previous_visible = hasattr(
            self, "_v035_refinement_visible_slots"
        )

        if isinstance(knobs, dict):
            refinement_top_k = max(
                0, int(knobs.get("refinement_top_k", 0))
            )
            self._v035_refinement_visible_slots = max(
                0, refinement_top_k - 1
            )

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
        finally:
            if isinstance(knobs, dict):
                if had_previous_visible:
                    self._v035_refinement_visible_slots = previous_visible
                else:
                    try:
                        del self._v035_refinement_visible_slots
                    except AttributeError:
                        pass
