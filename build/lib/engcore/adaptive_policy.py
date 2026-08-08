"""
Adaptive proposer policy — V0.3.4 logic hardening.

Role: decide whether an adaptive *proposal* may be generated, and with which
search-allocation knobs. Does not alter model refit schedules and does not
execute candidates; the safety arbiter chooses among proposals.

Architecture:
  observations → baseline model fit → identity_proposal
                                    → (optional) adaptive_proposal
                                    → arbiter → ONE objective eval

Constants are based on normalized [0,1] feature semantics and stability, not
benchmark identity. No function / instance metadata is consumed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .landscape_diagnostics import LandscapeDiagnostics


EARLY_NEUTRAL_ABS = 8
EARLY_NEUTRAL_DIM_MULT = 3

MODEL_SUPPORT_CAP = 0.35
MODEL_ONLY_EVIDENCE_CAP = 0.25
SEARCH_FAIL_CAP = 0.85

EVIDENCE_MILD = 0.45
EVIDENCE_SEVERE = 0.80
SUSTAIN_MILD = 2
SUSTAIN_RESCUE = 4
RECOVERY_STEPS = 2
COOLDOWN_RESCUE = 4

POOL_MULT_MILD = 1.25
POOL_MULT_SEVERE = 1.50
DIVERSITY_MULT_MILD = 1.25
DIVERSITY_MULT_SEVERE = 1.50
EXPLORE_MIX_MILD = 0.15
EXPLORE_MIX_SEVERE = 0.30
REFINE_ITER_DELTA_MILD = -5
REFINE_ITER_DELTA_SEVERE = -10


@dataclass(frozen=True)
class AdaptiveDecision:
    """Proposer knobs + enable flags. Never forces model refit."""

    enable_adaptive_proposal: bool
    enable_rescue_proposal: bool
    screen_pool_mult: float
    diversity_radius_mult: float
    refinement_top_k_delta: int
    refinement_maxiter_delta: int
    exploration_mix: float
    evidence_score: float
    consecutive_evidence: int
    cooldown_remaining: int
    recovering: bool
    proposal_level: str
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def _model_support(d: LandscapeDiagnostics) -> float:
    score = 0.0
    if d.model_reliability < 0.35:
        score += 0.15
    if d.model_error_proxy >= 0.55:
        score += 0.10
    if d.model_agreement < 0.15:
        score += 0.10
    return float(min(score, MODEL_SUPPORT_CAP))


def _search_failure(d: LandscapeDiagnostics) -> float:
    score = 0.0
    if d.stagnation_score >= 0.45:
        score += 0.25
    if d.stagnation_score >= 0.70:
        score += 0.15
    if (
        d.incumbent_locality >= 0.70
        and d.recent_improvement_rate <= 1e-12
    ):
        score += 0.25
    if (
        d.recent_improvement_rate <= 1e-12
        and d.stagnation_score >= 0.30
    ):
        score += 0.15

    need = max(
        EARLY_NEUTRAL_ABS,
        EARLY_NEUTRAL_DIM_MULT * int(d.dimension),
    )
    if d.n_obs >= need and d.exploration_coverage < 0.20:
        score += 0.10
    return float(min(score, SEARCH_FAIL_CAP))


def compute_evidence_score(
    d: LandscapeDiagnostics,
) -> tuple[float, dict]:
    model = _model_support(d)
    search = _search_failure(d)
    if search < 0.15:
        evidence = min(model, MODEL_ONLY_EVIDENCE_CAP)
    else:
        evidence = min(1.0, search + 0.5 * model)
    return float(evidence), {
        "model_support": model,
        "search_failure": search,
    }


def is_early_neutral(d: LandscapeDiagnostics) -> bool:
    need = max(
        EARLY_NEUTRAL_ABS,
        EARLY_NEUTRAL_DIM_MULT * int(d.dimension),
    )
    return int(d.n_obs) < int(need)


class AdaptivePolicyController:
    """Stateful proposer gate: early-neutral, sustain, cooldown, recovery."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.consecutive_evidence = 0
        self.consecutive_recovery = 0
        self.cooldown_remaining = 0

    def update(
        self,
        diagnostics: LandscapeDiagnostics,
        *,
        base_stagnation_trigger: int = 6,
        step: int = 0,
    ) -> AdaptiveDecision:
        del base_stagnation_trigger, step
        d = diagnostics
        evidence, parts = compute_evidence_score(d)
        early = is_early_neutral(d)
        reasons: list[str] = []

        if early:
            evidence = min(evidence, MODEL_ONLY_EVIDENCE_CAP)
            reasons.append("early_neutral")

        improving_hold = (
            d.recent_improvement_rate > 0.0
            and parts["search_failure"] < 0.20
        )
        if improving_hold:
            reasons.append("improving_hold")

        if (
            (not early)
            and (not improving_hold)
            and evidence >= EVIDENCE_MILD
        ):
            self.consecutive_evidence += 1
            self.consecutive_recovery = 0
        else:
            self.consecutive_recovery += 1
            if self.consecutive_recovery >= RECOVERY_STEPS:
                self.consecutive_evidence = 0
                reasons.append("recovering")

        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            reasons.append("cooldown")

        enable_mild = (
            (not early)
            and (not improving_hold)
            and evidence >= EVIDENCE_MILD
            and self.consecutive_evidence >= SUSTAIN_MILD
        )
        enable_severe = (
            enable_mild
            and evidence >= EVIDENCE_SEVERE
            and self.consecutive_evidence >= SUSTAIN_RESCUE
            and self.cooldown_remaining == 0
        )

        reported_streak = int(self.consecutive_evidence)

        if enable_severe:
            level = "severe"
            screen_mult = POOL_MULT_SEVERE
            div_mult = DIVERSITY_MULT_SEVERE
            explore_mix = EXPLORE_MIX_SEVERE
            refine_iter_delta = REFINE_ITER_DELTA_SEVERE
            enable_rescue = True
            reasons.append("severe_proposal")
            self.cooldown_remaining = max(
                self.cooldown_remaining,
                COOLDOWN_RESCUE,
            )
            # A rescue authorization consumes the sustained-evidence streak.
            # Another severe rescue must earn a fresh streak while cooldown
            # elapses; it cannot inherit pre-rescue evidence indefinitely.
            self.consecutive_evidence = 0
            self.consecutive_recovery = 0
        elif enable_mild:
            level = "mild"
            screen_mult = POOL_MULT_MILD
            div_mult = DIVERSITY_MULT_MILD
            explore_mix = EXPLORE_MIX_MILD
            refine_iter_delta = REFINE_ITER_DELTA_MILD
            enable_rescue = False
            reasons.append("mild_proposal")
        else:
            level = "none"
            screen_mult = 1.0
            div_mult = 1.0
            explore_mix = 0.0
            refine_iter_delta = 0
            enable_rescue = False
            reasons.append("identity_only")

        recovering = "recovering" in reasons
        return AdaptiveDecision(
            enable_adaptive_proposal=bool(enable_mild or enable_severe),
            enable_rescue_proposal=bool(enable_rescue),
            screen_pool_mult=float(screen_mult),
            diversity_radius_mult=float(div_mult),
            refinement_top_k_delta=0,
            refinement_maxiter_delta=int(refine_iter_delta),
            exploration_mix=float(explore_mix),
            evidence_score=float(evidence),
            consecutive_evidence=reported_streak,
            cooldown_remaining=int(self.cooldown_remaining),
            recovering=bool(recovering),
            proposal_level=str(level),
            reason="+".join(reasons),
        )


def decide_adaptive_policy(
    diagnostics: LandscapeDiagnostics,
    *,
    base_stagnation_trigger: int = 6,
    controller: AdaptivePolicyController | None = None,
    step: int = 0,
) -> AdaptiveDecision:
    """
    Stateful convenience wrapper.

    A controller is required because proposal enablement depends on sustained
    evidence across updates. Silently constructing a fresh controller on every
    call would make that state impossible to accumulate.
    """
    if controller is None:
        raise ValueError(
            "decide_adaptive_policy requires a persistent "
            "AdaptivePolicyController"
        )
    return controller.update(
        diagnostics,
        base_stagnation_trigger=base_stagnation_trigger,
        step=step,
    )


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
    """Materialize knobs for the adaptive proposal path only."""

    def _scale_pool(n):
        return int(
            max(
                1024,
                round(int(n) * float(decision.screen_pool_mult)),
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
        "pulse_screen_pool": _scale_pool(pulse_screen_pool),
        "severe_screen_pool": _scale_pool(severe_screen_pool),
        "diversity_radius": float(
            max(
                1e-4,
                float(diversity_radius)
                * float(decision.diversity_radius_mult),
            )
        ),
        "refinement_top_k": refine_k,
        "refinement_maxiter": refine_iters,
        "exploration_mix": float(decision.exploration_mix),
        "enable_adaptive_proposal": bool(
            decision.enable_adaptive_proposal
        ),
        "enable_rescue_proposal": bool(
            decision.enable_rescue_proposal
        ),
        "proposal_level": str(decision.proposal_level),
        "reason": decision.reason,
        "evidence_score": float(decision.evidence_score),
        "consecutive_evidence": int(decision.consecutive_evidence),
        "cooldown_remaining": int(decision.cooldown_remaining),
        "recovering": bool(decision.recovering),
    }


def identity_knobs(
    *,
    screen_pool: int,
    pulse_screen_pool: int,
    severe_screen_pool: int,
    diversity_radius: float,
    refinement_top_k: int,
    refinement_maxiter: int,
    top_k: int,
) -> dict:
    """Exact baseline search knobs for identity_proposal."""
    del top_k
    return {
        "screen_pool": int(screen_pool),
        "pulse_screen_pool": int(pulse_screen_pool),
        "severe_screen_pool": int(severe_screen_pool),
        "diversity_radius": float(diversity_radius),
        "refinement_top_k": int(refinement_top_k),
        "refinement_maxiter": int(refinement_maxiter),
        "exploration_mix": 0.0,
        "enable_adaptive_proposal": False,
        "enable_rescue_proposal": False,
        "proposal_level": "none",
        "reason": "identity",
        "evidence_score": 0.0,
        "consecutive_evidence": 0,
        "cooldown_remaining": 0,
        "recovering": False,
    }
