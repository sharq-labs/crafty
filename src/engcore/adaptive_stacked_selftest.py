"""
Fast V0.3.3 adaptive optimizer property + smoke-guard tests.

Uses synthetic diagnostic states and tiny randomized toy landscapes.
Does NOT select thresholds from BBOB / named smoke scores.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .adaptive_policy import (
    AdaptivePolicyController,
    EVIDENCE_MILD,
    EVIDENCE_SEVERE,
    MODEL_ONLY_EVIDENCE_CAP,
    compute_evidence_score,
    decide_adaptive_policy,
)
from .adaptive_stacked_engine import (
    AdaptiveStackedGPBOEngine,
)
from .landscape_diagnostics import (
    LandscapeDiagnostics,
    compute_landscape_diagnostics,
)
from .models import DesignSpace, Variable
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode
from .validation.optimizers import (
    ALGORITHMS,
    run_adaptive_stacked,
    run_stacked,
)
from .validation.problem import ObjectiveRecorder


def _require(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _space(dim=2, bound=2.0):
    return DesignSpace([
        Variable(f"x{i}", -bound, bound, "")
        for i in range(dim)
    ])


def _diag(**kwargs):
    base = dict(
        n_obs=20,
        dimension=2,
        remaining_budget_fraction=0.5,
        best_score=-0.1,
        evaluations_since_improve=0,
        recent_improvement_rate=0.25,
        normalized_improvement_velocity=0.1,
        stagnation_score=0.0,
        sample_diversity=0.4,
        incumbent_locality=0.2,
        exploration_coverage=0.4,
        model_agreement=0.5,
        model_error_proxy=0.5,
        model_reliability=0.5,
        weight_rbf=0.5,
        weight_matern=0.5,
    )
    base.update(kwargs)
    return LandscapeDiagnostics(**base)


def test_diagnostics_small_n_finite():
    d0 = compute_landscape_diagnostics(
        x01_history=[],
        scores=[],
        best_score=float("-inf"),
        evaluations_since_improve=0,
        total_budget=20,
        dimension=2,
    )
    _require(d0.n_obs == 0, "n_obs")
    _require(np.isfinite(d0.stagnation_score), "stag")


def test_no_benchmark_tokens():
    root = Path(__file__).resolve().parent
    for name in (
        "adaptive_policy.py",
        "landscape_diagnostics.py",
        "adaptive_stacked_engine.py",
    ):
        text = (root / name).read_text(
            encoding="utf-8"
        ).lower()
        for banned in (
            "bbob_f",
            "fopt",
            "function_id",
            "cocoex.function",
            "benchmarkfunction",
            "rastrigin",
            "rosenbrock",
            "weierstrass",
            "gallagher",
        ):
            _require(
                banned not in text,
                f"{name} contains {banned}",
            )


def test_A_weak_model_alone_no_strong_adaptation():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=20,
        model_reliability=0.05,
        model_error_proxy=0.99,
        model_agreement=0.05,
        stagnation_score=0.05,
        recent_improvement_rate=0.3,
        incumbent_locality=0.2,
    )
    # Several steps of model-only concern.
    last = None
    for step in range(6):
        last = ctl.update(d, step=step)
    evidence, parts = compute_evidence_score(d)
    _require(
        evidence <= MODEL_ONLY_EVIDENCE_CAP + 1e-12,
        f"model-only evidence too large: {evidence}",
    )
    _require(
        parts["search_failure"] < 0.15,
        "search failure unexpectedly high",
    )
    _require(
        not last.enable_search_realloc
        or last.adaptation_strength < 0.20,
        "strong realloc from model alone",
    )
    _require(
        not last.enable_rescue_inject,
        "rescue from model alone",
    )
    _require(
        abs(last.screen_pool_mult - 1.0) < 1e-12,
        "screen changed from model alone",
    )


def test_B_low_reliability_but_improving_near_baseline():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=24,
        model_reliability=0.1,
        model_error_proxy=0.9,
        stagnation_score=0.1,
        recent_improvement_rate=0.4,
        incumbent_locality=0.25,
        evaluations_since_improve=0,
    )
    for step in range(5):
        dec = ctl.update(d, step=step)
    _require(
        abs(dec.screen_pool_mult - 1.0) < 1e-9
        or dec.adaptation_strength < 0.2,
        "improving run left baseline too far",
    )
    _require(not dec.enable_rescue_inject, "rescue")


def test_C_persistent_stagnation_concentration_adapts():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=24,
        model_reliability=0.4,
        model_error_proxy=0.4,
        stagnation_score=0.75,
        recent_improvement_rate=0.0,
        incumbent_locality=0.85,
        exploration_coverage=0.1,
        evaluations_since_improve=10,
    )
    saw_realloc = False
    for step in range(6):
        dec = ctl.update(d, step=step)
        if dec.enable_search_realloc:
            saw_realloc = True
    _require(saw_realloc, "no realloc under persistent failure")
    _require(dec.adaptation_strength > 0.2, "strength")


def test_D_one_step_spike_no_rescue():
    ctl = AdaptivePolicyController()
    mild = _diag(n_obs=20, stagnation_score=0.1)
    ctl.update(mild, step=0)
    spike = _diag(
        n_obs=24,
        stagnation_score=0.95,
        recent_improvement_rate=0.0,
        incumbent_locality=0.95,
        exploration_coverage=0.05,
        evaluations_since_improve=20,
        model_reliability=0.2,
    )
    dec = ctl.update(spike, step=1)
    _require(
        not dec.enable_rescue_inject,
        "one-step spike triggered rescue",
    )
    _require(
        dec.consecutive_evidence < 4,
        "sustain counter jumped incorrectly",
    )


def test_E_sustained_severe_can_rescue():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=30,
        stagnation_score=0.95,
        recent_improvement_rate=0.0,
        incumbent_locality=0.9,
        exploration_coverage=0.05,
        evaluations_since_improve=20,
        model_reliability=0.25,
        model_error_proxy=0.7,
    )
    rescued = False
    for step in range(8):
        dec = ctl.update(d, step=step)
        if dec.enable_rescue_inject:
            rescued = True
            break
    _require(rescued, "severe sustained never rescued")
    _require(dec.evidence_score >= EVIDENCE_SEVERE - 1e-9, "ev")


def test_F_recovery_toward_baseline():
    ctl = AdaptivePolicyController()
    bad = _diag(
        n_obs=30,
        stagnation_score=0.8,
        recent_improvement_rate=0.0,
        incumbent_locality=0.85,
        evaluations_since_improve=12,
    )
    for step in range(5):
        ctl.update(bad, step=step)
    _require(ctl.adaptation_strength > 0.15, "pre")
    good = _diag(
        n_obs=36,
        stagnation_score=0.05,
        recent_improvement_rate=0.5,
        incumbent_locality=0.2,
        evaluations_since_improve=0,
    )
    for step in range(5, 12):
        dec = ctl.update(good, step=step)
    _require(
        dec.adaptation_strength < 0.2
        or abs(dec.screen_pool_mult - 1.0) < 1e-9,
        "did not recover toward baseline",
    )
    _require(dec.recovering or dec.adaptation_strength < 0.15, "flag")


def test_G_cooldown_blocks_repeat_strong():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=30,
        stagnation_score=0.95,
        recent_improvement_rate=0.0,
        incumbent_locality=0.9,
        exploration_coverage=0.05,
        evaluations_since_improve=20,
        model_reliability=0.2,
    )
    first_rescue_step = None
    second_rescue_step = None
    for step in range(12):
        dec = ctl.update(d, step=step)
        if dec.enable_rescue_inject:
            if first_rescue_step is None:
                first_rescue_step = step
            elif second_rescue_step is None:
                second_rescue_step = step
    _require(first_rescue_step is not None, "no rescue")
    if second_rescue_step is not None:
        _require(
            second_rescue_step - first_rescue_step >= 3,
            "cooldown failed to space rescues",
        )


def test_H_exact_budget():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        x = np.asarray(x, dtype=float)
        return float(np.sum((x - 0.25) ** 2))

    for budget in (7, 13, 25):
        calls["n"] = 0
        row = run_adaptive_stacked(
            problem_id=f"b{budget}",
            func=func,
            lower=np.array([-2.0, -2.0]),
            upper=np.array([2.0, 2.0]),
            budget=budget,
            seed=11,
            mode="fast",
            screen_device="cpu",
            refinement_backend="torch",
        )
        _require(
            row.evaluations == budget == calls["n"],
            f"budget {budget}",
        )


def test_I_deterministic_replay():
    def make_engine(seed):
        def evaluator(x):
            f = float(np.sum(np.asarray(x) ** 2))
            return -f, True, {"objective_f": f}

        return AdaptiveStackedGPBOEngine(
            design_space=_space(2),
            evaluator=evaluator,
            seed=seed,
            screen_device="cpu",
            record_diagnostics=True,
        )

    mode = dict(get_stacked_mode("fast"))
    mode.update({
        "screen_pool": 2048,
        "pulse_screen_pool": 4096,
        "severe_screen_pool": 4096,
        "refinement_timeout_sec": 0.5,
    })
    r1 = make_engine(7).run(
        initial_trials=4, smart_trials=6, verbose=False, **mode
    )
    r2 = make_engine(7).run(
        initial_trials=4, smart_trials=6, verbose=False, **mode
    )
    _require(
        np.allclose(r1["best"].x, r2["best"].x),
        "best x mismatch",
    )
    _require(r1["trials_run"] == r2["trials_run"] == 10, "trials")


def test_J_neutral_controller_matches_stacked_identity_path():
    """
    With a controller forced to stay at strength 0 (early-neutral diagnostics),
    adaptive knobs are identity. Full bit-identity vs stacked is covered by
    running both engines on the same seed with early-dominated short budgets
    in the holdout / budget tests; here we assert identity knobs.
    """
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=4,
        dimension=2,
        stagnation_score=0.9,
        model_error_proxy=0.99,
        recent_improvement_rate=0.0,
        incumbent_locality=0.9,
    )
    dec = ctl.update(d, step=0)
    _require(abs(dec.screen_pool_mult - 1.0) < 1e-12, "pool")
    _require(abs(dec.diversity_radius_mult - 1.0) < 1e-12, "div")
    _require(dec.exploration_mix == 0.0, "mix")
    _require(not dec.enable_rescue_inject, "rescue")
    _require(not dec.force_model_refit, "refit")
    _require(not dec.enable_search_realloc, "realloc")


def test_neutral_run_bit_identical_to_stacked():
    """Property J (engine-level): short run under early-neutral ⇒ identical X."""
    rng_y = []

    def func(x):
        x = np.asarray(x, dtype=float)
        # Fixed analytic toy — not a named benchmark family selector.
        return float(
            np.sum((x - 0.2) ** 2)
            + 0.05 * np.sin(3 * x[0])
        )

    lower = np.array([-1.5, -1.5])
    upper = np.array([1.5, 1.5])
    # Keep every BO decision in early-neutral: need n_obs < max(8, 3*dim)
    # at the start of each smart step ⇒ budget - 1 < 8 for dim=2.
    budget = 8
    xs = []
    xa = []
    for runner, bag in (
        (run_stacked, xs),
        (run_adaptive_stacked, xa),
    ):
        state = {"xs": []}

        def counted(x, st=state):
            st["xs"].append(np.asarray(x, dtype=float).copy())
            return func(x)

        row = runner(
            problem_id="neutral_id",
            func=counted,
            lower=lower,
            upper=upper,
            budget=budget,
            seed=99,
            mode="fast",
            screen_device="cpu",
            refinement_backend="torch",
        )
        _require(row.evaluations == budget, "budget")
        bag.extend(state["xs"])

    _require(len(xs) == len(xa) == budget, "len")
    identical = all(
        np.allclose(a, b) for a, b in zip(xs, xa)
    )
    _require(
        identical,
        "adaptive early-neutral trajectory != stacked",
    )


def test_baseline_still_runnable():
    def func(x):
        return float(np.sum(np.asarray(x) ** 2))

    row = run_stacked(
        problem_id="base",
        func=func,
        lower=np.array([-2.0, -2.0]),
        upper=np.array([2.0, 2.0]),
        budget=10,
        seed=5,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )
    _require(row.algorithm == "stacked_v0301", "id")
    _require("adaptive_stacked" in ALGORITHMS, "reg")
    _require(isinstance(StackedGPBOEngine, type), "cls")


def test_K_evidence_requires_multi_signal_for_mild():
    evidence, parts = compute_evidence_score(
        _diag(
            model_error_proxy=0.99,
            model_reliability=0.05,
            stagnation_score=0.0,
            recent_improvement_rate=0.4,
        )
    )
    _require(evidence <= MODEL_ONLY_EVIDENCE_CAP + 1e-12, "cap")
    _require(parts["search_failure"] < 0.15, "search")
    _require(evidence < EVIDENCE_MILD, "below mild")


def run_randomized_holdout():
    """
    Small fixed-seed generic holdout (regression guard, not threshold tuning).
    """
    from .validation.metrics import summarize_traces
    from .validation.problem import Trace

    rng = np.random.default_rng(20260333)
    dim = 2
    budget = 16
    problems = []

    for i in range(8):
        shift = rng.uniform(-0.4, 0.4, size=dim)
        # Random orthogonal-ish 2x2 via QR.
        A = rng.normal(size=(dim, dim))
        Q, _ = np.linalg.qr(A)
        cond = 10 ** rng.uniform(0.0, 1.5)
        scale = np.array([1.0, cond], dtype=float)
        mix = rng.uniform(0.0, 0.35)
        freq = rng.uniform(2.0, 6.0)

        def make_func(shift, Q, scale, mix, freq):
            def func(x):
                x = np.asarray(x, dtype=float)
                z = Q @ (x - shift)
                quad = float(np.sum((scale * z) ** 2))
                rugged = float(
                    mix * np.sum(np.sin(freq * z) ** 2)
                )
                return quad + rugged

            return func

        problems.append({
            "id": f"holdout_{i}",
            "func": make_func(shift, Q, scale, mix, freq),
            "lower": np.full(dim, -2.0),
            "upper": np.full(dim, 2.0),
        })

    traces = []
    catastrophic = 0
    for p in problems:
        rows = {}
        for key, runner in (
            ("stacked", run_stacked),
            ("adaptive_stacked", run_adaptive_stacked),
        ):
            row = runner(
                problem_id=p["id"],
                func=p["func"],
                lower=p["lower"],
                upper=p["upper"],
                budget=budget,
                seed=1000 + hash(p["id"]) % 1000,
                mode="fast",
                screen_device="cpu",
                refinement_backend="torch",
            )
            _require(row.evaluations == budget, "holdout budget")
            rows[key] = row
            traces.append(row)
        s = rows["stacked"].best_f
        a = rows["adaptive_stacked"].best_f
        floor = max(abs(s), 1e-12)
        if a > 50.0 * floor and a - s > 1.0:
            catastrophic += 1

    summary = summarize_traces(traces)
    algs = summary["algorithms"]
    return {
        "summary": algs,
        "catastrophic": catastrophic,
        "n_problems": len(problems),
    }


def main():
    print(
        "Engineering AI Core V0.3.3 — "
        "Adaptive Policy Property Self-Test"
    )
    print("=" * 72)

    test_diagnostics_small_n_finite()
    print("[PASS] diagnostics finite")

    test_no_benchmark_tokens()
    print("[PASS] no benchmark leakage tokens")

    test_A_weak_model_alone_no_strong_adaptation()
    print("[PASS] A weak model alone != strong adaptation")

    test_B_low_reliability_but_improving_near_baseline()
    print("[PASS] B improving + low reliability ~ baseline")

    test_C_persistent_stagnation_concentration_adapts()
    print("[PASS] C sustained stagnation/concentration adapts")

    test_D_one_step_spike_no_rescue()
    print("[PASS] D one-step spike != rescue")

    test_E_sustained_severe_can_rescue()
    print("[PASS] E sustained severe can rescue")

    test_F_recovery_toward_baseline()
    print("[PASS] F recovery toward baseline")

    test_G_cooldown_blocks_repeat_strong()
    print("[PASS] G cooldown spacing")

    test_K_evidence_requires_multi_signal_for_mild()
    print("[PASS] K multi-signal evidence gate")

    test_J_neutral_controller_matches_stacked_identity_path()
    print("[PASS] J early-neutral knobs are identity")

    test_baseline_still_runnable()
    print("[PASS] baseline stacked_v0301 runnable")

    print("[RUN ] exact budgets / replay / neutral identity...")
    test_H_exact_budget()
    print("[PASS] H exact objective budgets")

    test_I_deterministic_replay()
    print("[PASS] I deterministic replay")

    test_neutral_run_bit_identical_to_stacked()
    print("[PASS] J engine neutral == stacked (early budget)")

    print("[RUN ] randomized mini holdout...")
    hold = run_randomized_holdout()
    print(
        "[PASS] randomized holdout "
        f"n={hold['n_problems']} "
        f"catastrophic={hold['catastrophic']}"
    )
    for name, s in hold["summary"].items():
        print(
            f"  {name:22s} mean_rank={s['mean_rank']:.3f} "
            f"wins={s['wins']} win_share={s['win_share']:.2f}"
        )
    _require(
        hold["catastrophic"] <= 1,
        f"too many catastrophic regressions: {hold['catastrophic']}",
    )

    print("=" * 72)
    print("V0.3.3 Adaptive Policy property self-test: PASS")
    return hold


if __name__ == "__main__":
    main()
