"""
V0.3.3 adaptive policy — baseline by default, adapt on sustained multi-signal evidence.

Design principles:
  - LOO / model diagnostics are supporting evidence only (never a sole trigger
    for strong search changes).
  - Early / tiny-N regimes stay near stacked_v0301 (uncertainty is expected).
  - Interventions are decoupled:
      A) search reallocation (pool / diversity / explore mix)
      B) forced model refit
      C) rescue candidate injection (strongest)
  - Hysteresis + cooldown + recovery prevent flip-flopping.

No benchmark identity, no landscape class labels, no BBOB-derived thresholds.
Constants below are justified by normalized [0,1] feature semantics and
stability/safety, not by smoke/BBOB scores.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .landscape_diagnostics import LandscapeDiagnostics


# ---------------------------------------------------------------------------
# Numeric constants (normalized-feature / safety rationale — not benchmark-tuned)
# ---------------------------------------------------------------------------

# Early-neutral: need enough observations before adaptation may leave baseline.
# Uses max(8, 3*dim): generic sample-size floor for GP/stacking stability.
EARLY_NEUTRAL_ABS = 8
EARLY_NEUTRAL_DIM_MULT = 3

# Evidence score ceilings / gates on [0, 1].
# Model-only contribution is hard-capped so saturated LOO cannot dominate.
MODEL_SUPPORT_CAP = 0.35
MODEL_ONLY_EVIDENCE_CAP = 0.25
SEARCH_FAIL_CAP = 0.85

# Activation thresholds on sustained evidence.
EVIDENCE_WEAK = 0.30          # at/below → recover toward baseline
EVIDENCE_MILD = 0.45          # mild search reallocation
EVIDENCE_STRONG = 0.65        # stronger exploration reallocation
EVIDENCE_SEVERE = 0.80        # rescue candidate injection eligible

# Consecutive BO steps of compatible evidence before escalating.
SUSTAIN_MILD = 2
SUSTAIN_STRONG = 3
SUSTAIN_RESCUE = 4
SUSTAIN_REFIT = 3
RECOVERY_STEPS = 2

# Strength EMA / decay (unitless mixing weights).
STRENGTH_ATTACK = 0.35        # how fast strength rises toward target
STRENGTH_DECAY = 0.80         # multiplicative decay when evidence weak
STRENGTH_HYSTERESIS = 0.05    # deadband against oscillation

# Cooldown after strong interventions (BO steps, not objective extras).
COOLDOWN_STRONG = 3
COOLDOWN_RESCUE = 4

# Proportional knob amplitudes at strength=1 (mild at lower strength).
POOL_MULT_MAX = 1.50
DIVERSITY_MULT_MAX = 1.55
EXPLORE_MIX_MAX = 0.35
REFINE_K_DELTA_MIN = -1
REFINE_ITER_DELTA_MIN = -10


@dataclass(frozen=True)
class AdaptiveDecision:
    """
    Knobs + intervention flags relative to a stacked mode baseline.
    """

    screen_pool_mult: float
    diversity_radius_mult: float
    refinement_top_k_delta: int
    refinement_maxiter_delta: int
    exploration_mix: float
    enable_search_realloc: bool
    force_model_refit: bool
    enable_rescue_inject: bool
    evidence_score: float
    consecutive_evidence: int
    adaptation_strength: float
    intervention_type: str
    cooldown_remaining: int
    recovering: bool
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)

    # Backward-compatible alias used by older debug printers.
    @property
    def enable_rescue(self) -> bool:
        return bool(self.enable_rescue_inject)


def np_clip(value, lo, hi):
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _model_support(d: LandscapeDiagnostics) -> float:
    """
    Supporting model concern in [0, MODEL_SUPPORT_CAP].

    Intentionally weak: saturated early LOO "error" alone cannot authorize
    strong search changes.
    """
    score = 0.0
    if d.model_reliability < 0.35:
        score += 0.15
    if d.model_error_proxy >= 0.55:
        score += 0.10
    if d.model_agreement < 0.15:
        score += 0.10
    return float(min(score, MODEL_SUPPORT_CAP))


def _search_failure(d: LandscapeDiagnostics) -> float:
    """Behavioral failure evidence in [0, SEARCH_FAIL_CAP]."""
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
    # Low coverage only after enough samples exist to judge coverage.
    if (
        d.n_obs >= max(EARLY_NEUTRAL_ABS, EARLY_NEUTRAL_DIM_MULT * d.dimension)
        and d.exploration_coverage < 0.20
    ):
        score += 0.10
    return float(min(score, SEARCH_FAIL_CAP))


def compute_evidence_score(
    d: LandscapeDiagnostics,
) -> tuple[float, dict]:
    """
    Multi-signal evidence in [0, 1].

    Model diagnostics modulate search-failure evidence; model-only snapshots
    are hard-capped to MODEL_ONLY_EVIDENCE_CAP.
    """
    model = _model_support(d)
    search = _search_failure(d)

    if search < 0.15:
        # No meaningful behavioral failure → model concern alone stays weak.
        evidence = min(model, MODEL_ONLY_EVIDENCE_CAP)
    else:
        # Search failure primary; model may add a bounded assist.
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
    """
    Stateful policy with hysteresis, cooldown, and recovery.
    """

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.consecutive_evidence = 0
        self.consecutive_recovery = 0
        self.adaptation_strength = 0.0
        self.cooldown_remaining = 0
        self.last_intervention = "none"
        self.intervention_start_step = -1

    def update(
        self,
        diagnostics: LandscapeDiagnostics,
        *,
        base_stagnation_trigger: int = 6,
        step: int = 0,
    ) -> AdaptiveDecision:
        d = diagnostics
        evidence, parts = compute_evidence_score(d)
        early = is_early_neutral(d)
        reasons = []

        if early:
            evidence = min(evidence, MODEL_ONLY_EVIDENCE_CAP)
            reasons.append("early_neutral")

        # Sustained evidence counters.
        if evidence >= EVIDENCE_MILD and not early:
            self.consecutive_evidence += 1
            self.consecutive_recovery = 0
        else:
            self.consecutive_recovery += 1
            if self.consecutive_recovery >= RECOVERY_STEPS:
                self.consecutive_evidence = 0

        # Target strength from sustained evidence (not a single snapshot).
        target = 0.0
        if (
            not early
            and evidence >= EVIDENCE_SEVERE
            and self.consecutive_evidence >= SUSTAIN_RESCUE
        ):
            target = 1.0
            reasons.append("severe_sustained")
        elif (
            not early
            and evidence >= EVIDENCE_STRONG
            and self.consecutive_evidence >= SUSTAIN_STRONG
        ):
            target = 0.75
            reasons.append("strong_sustained")
        elif (
            not early
            and evidence >= EVIDENCE_MILD
            and self.consecutive_evidence >= SUSTAIN_MILD
        ):
            target = 0.40
            reasons.append("mild_sustained")
        else:
            reasons.append("baseline_hold")

        # Continuing improvement with only model concern → stay near baseline.
        if (
            d.recent_improvement_rate > 0.0
            and parts["search_failure"] < 0.20
        ):
            target = min(target, 0.15)
            reasons.append("improving_hold")

        # Strength EMA + decay / hysteresis.
        recovering = False
        if target + STRENGTH_HYSTERESIS < self.adaptation_strength:
            self.adaptation_strength *= STRENGTH_DECAY
            recovering = True
            reasons.append("recovering")
        elif target > self.adaptation_strength + STRENGTH_HYSTERESIS:
            self.adaptation_strength = (
                (1.0 - STRENGTH_ATTACK) * self.adaptation_strength
                + STRENGTH_ATTACK * target
            )
        # else: hold strength (hysteresis band)

        if self.adaptation_strength < 0.05:
            self.adaptation_strength = 0.0

        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            reasons.append("cooldown")

        strength = float(self.adaptation_strength)

        # --- Decoupled interventions ---------------------------------------
        enable_search_realloc = (
            strength >= 0.20
            and not early
            and self.consecutive_evidence >= SUSTAIN_MILD
        )

        # Forced refit: independent of rescue injection.
        force_model_refit = (
            not early
            and self.consecutive_evidence >= SUSTAIN_REFIT
            and d.evaluations_since_improve
            >= max(int(base_stagnation_trigger), 4)
            and parts["search_failure"] >= 0.40
            and self.cooldown_remaining == 0
        )

        # Rescue injection: strongest; requires severe sustained evidence
        # and no active cooldown.
        enable_rescue_inject = (
            not early
            and evidence >= EVIDENCE_SEVERE
            and self.consecutive_evidence >= SUSTAIN_RESCUE
            and self.cooldown_remaining == 0
            and strength >= 0.70
        )

        # Cooldown blocks repeating *strong* interventions; strength/evidence
        # may continue to accumulate so a later rescue remains reachable.
        if self.cooldown_remaining > 0:
            enable_rescue_inject = False
            force_model_refit = False

        intervention = "none"
        if enable_rescue_inject:
            intervention = "rescue_inject"
            self.cooldown_remaining = max(
                self.cooldown_remaining,
                COOLDOWN_RESCUE,
            )
            self.intervention_start_step = int(step)
            reasons.append("rescue_inject")
        elif force_model_refit and enable_search_realloc and strength >= 0.55:
            # Refit + strong realloc: cooldown so we observe effect before
            # another forced refit / escalation. Does not freeze strength.
            intervention = "strong_explore_refit"
            self.cooldown_remaining = max(
                self.cooldown_remaining,
                COOLDOWN_STRONG,
            )
            self.intervention_start_step = int(step)
            reasons.append("force_refit")
        elif enable_search_realloc and strength >= 0.55:
            intervention = "strong_explore"
            reasons.append("search_realloc_strong")
        elif enable_search_realloc:
            intervention = "mild_realloc"
            reasons.append("search_realloc_mild")
        elif force_model_refit:
            intervention = "forced_refit_only"
            self.cooldown_remaining = max(
                self.cooldown_remaining,
                COOLDOWN_STRONG,
            )
            self.intervention_start_step = int(step)
            reasons.append("force_refit")

        self.last_intervention = intervention

        # Proportional knobs (identity at strength 0).
        if enable_search_realloc and strength > 0.0:
            # Interpolate from 1.0 toward max amplitudes.
            t = float(np_clip(strength, 0.0, 1.0))
            screen_mult = 1.0 + (POOL_MULT_MAX - 1.0) * t
            diversity_mult = 1.0 + (DIVERSITY_MULT_MAX - 1.0) * t
            exploration_mix = EXPLORE_MIX_MAX * t
            refine_k_delta = int(
                round(REFINE_K_DELTA_MIN * t)
            )
            refine_iter_delta = int(
                round(REFINE_ITER_DELTA_MIN * t)
            )
        else:
            screen_mult = 1.0
            diversity_mult = 1.0
            exploration_mix = 0.0
            refine_k_delta = 0
            refine_iter_delta = 0

        # Mild late-budget exploit only with improving/reliable search state —
        # not from model-alone saturation.
        if (
            d.remaining_budget_fraction <= 0.25
            and d.stagnation_score < 0.45
            and d.recent_improvement_rate > 0.0
            and d.model_reliability >= 0.45
            and not enable_rescue_inject
        ):
            screen_mult = min(screen_mult, 0.90)
            diversity_mult = min(diversity_mult, 0.90)
            refine_k_delta = max(refine_k_delta, 1)
            refine_iter_delta = max(refine_iter_delta, 10)
            reasons.append("late_budget_exploit")

        screen_mult = float(np_clip(screen_mult, 0.75, POOL_MULT_MAX))
        diversity_mult = float(
            np_clip(diversity_mult, 0.75, DIVERSITY_MULT_MAX)
        )
        exploration_mix = float(
            np_clip(exploration_mix, 0.0, EXPLORE_MIX_MAX)
        )
        refine_k_delta = int(np_clip(refine_k_delta, -2, 2))
        refine_iter_delta = int(
            np_clip(refine_iter_delta, -20, 20)
        )

        if early:
            # Hard baseline in early-neutral region.
            screen_mult = 1.0
            diversity_mult = 1.0
            exploration_mix = 0.0
            refine_k_delta = 0
            refine_iter_delta = 0
            enable_search_realloc = False
            force_model_refit = False
            enable_rescue_inject = False
            intervention = "none"
            strength = 0.0
            self.adaptation_strength = 0.0

        return AdaptiveDecision(
            screen_pool_mult=screen_mult,
            diversity_radius_mult=diversity_mult,
            refinement_top_k_delta=refine_k_delta,
            refinement_maxiter_delta=refine_iter_delta,
            exploration_mix=exploration_mix,
            enable_search_realloc=bool(
                enable_search_realloc
            ),
            force_model_refit=bool(force_model_refit),
            enable_rescue_inject=bool(
                enable_rescue_inject
            ),
            evidence_score=float(evidence),
            consecutive_evidence=int(
                self.consecutive_evidence
            ),
            adaptation_strength=float(strength),
            intervention_type=str(intervention),
            cooldown_remaining=int(
                self.cooldown_remaining
            ),
            recovering=bool(recovering),
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
    Convenience wrapper.

    For production BO loops, reuse one AdaptivePolicyController across steps.
    A fresh controller is created when none is provided (stateless one-shot).
    """
    ctl = (
        controller
        if controller is not None
        else AdaptivePolicyController()
    )
    return ctl.update(
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
    """Materialize integer/float knobs for one BO step."""

    def _scale_pool(n):
        return int(
            max(
                1024,
                round(
                    int(n) * float(decision.screen_pool_mult)
                ),
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
                * float(decision.diversity_radius_mult),
            )
        ),
        "refinement_top_k": refine_k,
        "refinement_maxiter": refine_iters,
        "exploration_mix": float(
            decision.exploration_mix
        ),
        "enable_search_realloc": bool(
            decision.enable_search_realloc
        ),
        "force_model_refit": bool(
            decision.force_model_refit
        ),
        "enable_rescue_inject": bool(
            decision.enable_rescue_inject
        ),
        # Alias for clarity in older call sites.
        "enable_rescue": bool(
            decision.enable_rescue_inject
        ),
        "reason": decision.reason,
        "evidence_score": float(
            decision.evidence_score
        ),
        "consecutive_evidence": int(
            decision.consecutive_evidence
        ),
        "adaptation_strength": float(
            decision.adaptation_strength
        ),
        "intervention_type": str(
            decision.intervention_type
        ),
        "cooldown_remaining": int(
            decision.cooldown_remaining
        ),
        "recovering": bool(decision.recovering),
    }
