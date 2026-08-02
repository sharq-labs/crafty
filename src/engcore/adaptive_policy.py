"""
Minimal continuous adaptive policy for V0.3.3.

Maps online LandscapeDiagnostics -> search knobs.
No benchmark identity, no discrete landscape classifier.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .landscape_diagnostics import (
    LandscapeDiagnostics,
)


@dataclass(frozen=True)
class AdaptiveDecision:
    """
    Multiplicative / additive adjustments relative to a stacked mode baseline.
    """

    screen_pool_mult: float
    diversity_radius_mult: float
    refinement_top_k_delta: int
    refinement_maxiter_delta: int
    exploration_mix: float
    enable_rescue: bool
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def decide_adaptive_policy(
    diagnostics: LandscapeDiagnostics,
    *,
    base_stagnation_trigger: int = 6,
) -> AdaptiveDecision:
    """
    Continuous policy (not a one-shot landscape label).

    Hypothesis summary:
    - High model reliability + improving search => modest exploitation
      (smaller pools / tighter diversity, more refinement).
    - High model error/disagreement or stagnation => more global diversity
      and optional rescue.
    - Late budget + reliable model => exploit.
    - Over-concentration without improvement => expand exploration.
    """
    d = diagnostics

    screen_mult = 1.0
    diversity_mult = 1.0
    refine_k_delta = 0
    refine_iter_delta = 0
    exploration_mix = 0.0
    enable_rescue = False
    reasons = []

    # 1) Model-driven exploration/exploitation.
    if d.model_reliability >= 0.55 and d.recent_improvement_rate > 0.0:
        screen_mult *= 0.85
        diversity_mult *= 0.85
        refine_k_delta += 1
        refine_iter_delta += 10
        reasons.append("exploit_reliable_improving")
    elif d.model_error_proxy >= 0.55 or d.model_agreement < 0.15:
        screen_mult *= 1.35
        diversity_mult *= 1.35
        exploration_mix = max(exploration_mix, 0.25)
        refine_k_delta -= 1
        reasons.append("explore_unreliable_model")

    # 2) Stagnation / over-concentration.
    concentrated_fail = (
        d.stagnation_score >= 0.45
        and d.incumbent_locality >= 0.70
        and d.recent_improvement_rate <= 1e-12
    )
    if concentrated_fail:
        screen_mult *= 1.50
        diversity_mult *= 1.60
        exploration_mix = max(exploration_mix, 0.40)
        reasons.append("escape_local_concentration")

    if d.stagnation_score >= 0.60:
        enable_rescue = True
        screen_mult *= 1.25
        exploration_mix = max(exploration_mix, 0.35)
        reasons.append("stagnation_rescue")

    # Also rescue if we already exceed the baseline discrete stagnation trigger
    # in normalized units (keeps policy aligned with stacked pulse spirit).
    if (
        d.evaluations_since_improve
        >= max(int(base_stagnation_trigger), 4)
        and d.model_reliability < 0.45
    ):
        enable_rescue = True
        reasons.append("trigger_aligned_rescue")

    # 3) Late-budget exploitation if the model looks trustworthy.
    if (
        d.remaining_budget_fraction <= 0.25
        and d.model_reliability >= 0.50
        and d.stagnation_score < 0.70
    ):
        screen_mult *= 0.80
        diversity_mult *= 0.75
        refine_k_delta += 1
        refine_iter_delta += 15
        exploration_mix *= 0.5
        reasons.append("late_budget_exploit")

    # 4) Tiny-N conservatism.
    if d.n_obs < max(6, 2 * d.dimension):
        screen_mult = max(screen_mult, 1.0)
        enable_rescue = False
        exploration_mix = min(exploration_mix, 0.15)
        reasons.append("tiny_n_conservative")

    screen_mult = float(np_clip(screen_mult, 0.60, 2.00))
    diversity_mult = float(np_clip(diversity_mult, 0.60, 2.25))
    exploration_mix = float(np_clip(exploration_mix, 0.0, 0.50))
    refine_k_delta = int(np_clip(refine_k_delta, -2, 3))
    refine_iter_delta = int(np_clip(refine_iter_delta, -20, 40))

    if not reasons:
        reasons.append("baseline_neutral")

    return AdaptiveDecision(
        screen_pool_mult=screen_mult,
        diversity_radius_mult=diversity_mult,
        refinement_top_k_delta=refine_k_delta,
        refinement_maxiter_delta=refine_iter_delta,
        exploration_mix=exploration_mix,
        enable_rescue=bool(enable_rescue),
        reason="+".join(reasons),
    )


def np_clip(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def apply_decision_to_knobs(
    decision: AdaptiveDecision,
    *,
    screen_pool: int,
    pulse_screen_pool: int,
    severe_screen_pool: int,
    diversity_radius: float,
    refinement_top_k: int,
    refinement_maxiter: int,
    top_k: int,
) -> dict:
    """Materialize integer/float knobs for one BO step."""
    def _scale_pool(n):
        return int(
            max(
                1024,
                round(int(n) * decision.screen_pool_mult),
            )
        )

    refine_k = max(
        1,
        min(
            int(top_k),
            int(refinement_top_k)
            + int(decision.refinement_top_k_delta),
        ),
    )
    refine_iters = max(
        10,
        int(refinement_maxiter)
        + int(decision.refinement_maxiter_delta),
    )

    return {
        "screen_pool": _scale_pool(screen_pool),
        "pulse_screen_pool": _scale_pool(
            pulse_screen_pool
        ),
        "severe_screen_pool": _scale_pool(
            severe_screen_pool
        ),
        "diversity_radius": float(
            max(
                1e-4,
                float(diversity_radius)
                * decision.diversity_radius_mult,
            )
        ),
        "refinement_top_k": refine_k,
        "refinement_maxiter": refine_iters,
        "exploration_mix": float(
            decision.exploration_mix
        ),
        "enable_rescue": bool(
            decision.enable_rescue
        ),
        "reason": decision.reason,
    }
