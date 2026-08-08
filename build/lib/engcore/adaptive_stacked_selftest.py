"""V0.3.4 logic-hardening property and regression tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .adaptive_policy import (
    AdaptivePolicyController,
    MODEL_ONLY_EVIDENCE_CAP,
    compute_evidence_score,
    decide_adaptive_policy,
    is_early_neutral,
)
from .adaptive_stacked_engine import AdaptiveStackedGPBOEngine
from .candidate_arbiter import (
    ProposalView,
    arbitrate_proposals,
    components_disagree,
)
from .landscape_diagnostics import (
    LandscapeDiagnostics,
    compute_landscape_diagnostics,
)
from .models import DesignSpace, Variable
from .validation.metrics import summarize_traces
from .validation.optimizers import (
    ALGORITHMS,
    run_adaptive_stacked,
)
from .validation.problem import ObjectiveRecorder, Trace


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


def _prop(x, mix, rbf, mat, source="p", rescue=False):
    return ProposalView(
        x01=np.asarray(x, dtype=float),
        source=source,
        mixture_acq=float(mix),
        rbf_acq=float(rbf),
        matern_acq=float(mat),
        is_rescue=bool(rescue),
    )


def _trace(algorithm, problem_id, value):
    return Trace(
        algorithm=algorithm,
        problem_id=problem_id,
        dimension=2,
        budget=5,
        seed=1,
        best_f=float(value),
        evaluations=5,
        values=[float(value)] * 5,
        best_curve=[float(value)] * 5,
    )


def test_no_benchmark_tokens():
    root = Path(__file__).resolve().parent
    for name in (
        "adaptive_policy.py",
        "landscape_diagnostics.py",
        "adaptive_stacked_engine.py",
        "candidate_arbiter.py",
    ):
        text = (root / name).read_text(encoding="utf-8").lower()
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
            _require(banned not in text, f"{name}:{banned}")


def test_arbiter_rejects_worse_and_disagreement():
    identity = _prop([0.1, 0.2], 1.0, 1.0, 1.0, "identity")
    worse = _prop([0.9, 0.9], 0.5, 0.5, 0.5, "adaptive")
    chosen, dec = arbitrate_proposals(
        identity, worse, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "worse adaptive accepted")
    _require(np.allclose(chosen.x01, identity.x01), "identity not executed")

    disagree = _prop([0.3, 0.4], 1.2, 1.5, 0.5, "adaptive")
    _require(
        components_disagree(1.0, 1.0, 1.5, 0.5),
        "disagreement helper failed",
    )
    chosen, dec = arbitrate_proposals(
        identity, disagree, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "disagreement accepted")
    _require(dec.component_disagreement, "disagreement not flagged")


def test_arbiter_accepts_material_consensus_gain():
    identity = _prop([0.1, 0.2], 1.0, 1.0, 1.0)
    adaptive = _prop([0.3, 0.4], 1.5, 1.2, 1.1)
    chosen, dec = arbitrate_proposals(
        identity, adaptive, adaptive_enabled=True
    )
    _require(dec.choose_adaptive, "material consensus gain rejected")
    _require(np.allclose(chosen.x01, adaptive.x01), "adaptive not executed")


def test_arbiter_rejects_numerical_dust_gain():
    identity = _prop([0.1, 0.2], -10.0, -10.0, -10.0)
    adaptive = _prop(
        [0.3, 0.4],
        -10.0 + 1e-9,
        -10.0 + 1e-9,
        -10.0 + 1e-9,
    )
    _, dec = arbitrate_proposals(
        identity, adaptive, adaptive_enabled=True
    )
    _require(
        not dec.choose_adaptive,
        "scale-aware tolerance accepted numerical dust",
    )


def test_rescue_does_not_bypass_arbiter():
    identity = _prop([0.1, 0.2], 1.0, 1.0, 1.0)
    rescue = _prop(
        [0.8, 0.8],
        0.2,
        0.2,
        0.2,
        source="adaptive_rescue",
        rescue=True,
    )
    chosen, dec = arbitrate_proposals(
        identity, rescue, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "weak rescue bypassed arbiter")
    _require(np.allclose(chosen.x01, identity.x01), "identity not kept")


def test_policy_model_alone_cannot_enable():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=20,
        model_reliability=0.05,
        model_error_proxy=0.99,
        model_agreement=0.05,
        stagnation_score=0.05,
        recent_improvement_rate=0.3,
    )
    for step in range(5):
        dec = ctl.update(d, step=step)
    evidence, _ = compute_evidence_score(d)
    _require(evidence <= MODEL_ONLY_EVIDENCE_CAP + 1e-12, "model cap")
    _require(not dec.enable_adaptive_proposal, "model-only enabled adaptive")


def test_policy_helper_requires_persistent_controller():
    try:
        decide_adaptive_policy(_diag())
    except ValueError as exc:
        _require("persistent" in str(exc), "unexpected helper error")
    else:
        raise AssertionError("stateless policy helper silently accepted")


def test_early_neutral():
    d = _diag(n_obs=4, dimension=2, stagnation_score=0.9)
    _require(is_early_neutral(d), "early-neutral not detected")
    ctl = AdaptivePolicyController()
    dec = ctl.update(d, step=0)
    _require(not dec.enable_adaptive_proposal, "early proposal enabled")


def test_rescue_consumes_evidence_streak():
    ctl = AdaptivePolicyController()
    severe = _diag(
        n_obs=30,
        recent_improvement_rate=0.0,
        stagnation_score=1.0,
        incumbent_locality=0.9,
        exploration_coverage=0.1,
        model_reliability=0.0,
        model_error_proxy=1.0,
        model_agreement=0.0,
    )
    decision = None
    for step in range(8):
        decision = ctl.update(severe, step=step)
        if decision.enable_rescue_proposal:
            break
    _require(decision is not None and decision.enable_rescue_proposal, "no rescue")
    _require(ctl.consecutive_evidence == 0, "rescue did not consume streak")
    _require(ctl.cooldown_remaining > 0, "rescue cooldown missing")


def test_model_diagnostics_common_logp_shift_invariant():
    X = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
    y = np.array([-3.0, -2.0, -1.0])
    base = [{
        "weight_rbf": 0.6,
        "mean_logp_rbf": -2.0,
        "mean_logp_matern": -3.0,
    }]
    shifted = [{
        "weight_rbf": 0.6,
        "mean_logp_rbf": -102.0,
        "mean_logp_matern": -103.0,
    }]
    a = compute_landscape_diagnostics(
        x01_history=X,
        scores=y,
        best_score=-1.0,
        evaluations_since_improve=1,
        total_budget=20,
        dimension=2,
        weight_rbf=0.6,
        weight_history=base,
    )
    b = compute_landscape_diagnostics(
        x01_history=X,
        scores=y,
        best_score=-1.0,
        evaluations_since_improve=1,
        total_budget=20,
        dimension=2,
        weight_rbf=0.6,
        weight_history=shifted,
    )
    _require(
        abs(a.model_agreement - b.model_agreement) < 1e-12,
        "agreement changed under common logp shift",
    )
    _require(
        abs(a.model_reliability - b.model_reliability) < 1e-12,
        "reliability changed under common logp shift",
    )


def test_design_space_validation():
    try:
        DesignSpace([Variable("x", 1.0, 1.0)])
    except ValueError:
        pass
    else:
        raise AssertionError("invalid bounds accepted")

    space = _space(2)
    try:
        space.as_dict([1.0])
    except ValueError:
        pass
    else:
        raise AssertionError("wrong vector dimension silently truncated")


def test_objective_recorder_audit():
    rec = ObjectiveRecorder(
        lambda x: float("nan") if x[0] > 0.9 else float(np.sum(x * x)),
        [-1.0, -1.0],
        [1.0, 1.0],
        budget=2,
    )
    rec.evaluate([2.0, 0.0])
    _require(rec.candidate_clipped_count == 1, "clip not counted")
    _require(rec.objective_nonfinite_count == 1, "nonfinite objective not counted")

    try:
        rec.evaluate([float("nan"), 0.0])
    except ValueError:
        _require(rec.candidate_nonfinite_count == 1, "nonfinite x not counted")
    else:
        raise AssertionError("nonfinite candidate did not fail fast")


def test_trace_matrix_rejects_duplicate_and_missing_rows():
    duplicate = [
        _trace("A", "p1", 1.0),
        _trace("A", "p1", 1.1),
        _trace("B", "p1", 2.0),
    ]
    try:
        summarize_traces(duplicate)
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate trace rows accepted")

    missing = [
        _trace("A", "p1", 1.0),
        _trace("B", "p1", 2.0),
        _trace("A", "p2", 3.0),
    ]
    try:
        summarize_traces(missing)
    except ValueError:
        pass
    else:
        raise AssertionError("unmatched trace matrix accepted")


def test_frozen_baseline_matches_tag():
    import subprocess

    files = [
        "src/engcore/stacked_engine.py",
        "src/engcore/stacked_acquisition.py",
        "src/engcore/stacked_modes.py",
        "src/engcore/hybrid_engine.py",
        "src/engcore/logei_engine.py",
    ]
    tag = "v0.3.2.6-stacked_v0301"
    out = subprocess.check_output(
        ["git", "diff", "--name-only", tag, "--", *files],
        text=True,
    ).strip()
    _require(out == "", f"frozen baseline differs from {tag}: {out}")
    _require("adaptive_stacked" in ALGORITHMS, "adaptive registry missing")


def test_adaptive_exact_budget_and_single_use():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        return float(np.sum(np.asarray(x, dtype=float) ** 2))

    budget = 13
    row = run_adaptive_stacked(
        problem_id="budget",
        func=func,
        lower=np.array([-2.0, -2.0]),
        upper=np.array([2.0, 2.0]),
        budget=budget,
        seed=11,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )
    _require(row.evaluations == budget == calls["n"], "objective budget mismatch")
    _require(row.metadata["candidate_nonfinite_count"] == 0, "nonfinite candidate")

    def evaluator(x):
        f = float(np.sum(np.asarray(x, dtype=float) ** 2))
        return -f, True, {"objective_f": f}

    engine = AdaptiveStackedGPBOEngine(
        design_space=_space(2),
        evaluator=evaluator,
        seed=7,
        screen_device="cpu",
    )
    mode = {
        "screen_pool": 1024,
        "pulse_screen_pool": 1024,
        "severe_screen_pool": 1024,
        "refinement_timeout_sec": 0.25,
    }
    engine.run(initial_trials=4, smart_trials=2, verbose=False, **mode)
    try:
        engine.run(initial_trials=4, smart_trials=2, verbose=False, **mode)
    except RuntimeError as exc:
        _require("single-use" in str(exc), "unexpected reuse error")
    else:
        raise AssertionError("engine reuse silently retained old state")


def main():
    print("Engineering AI Core V0.3.4 — Logic Hardening Self-Test")
    print("=" * 72)

    fast_tests = [
        ("no benchmark leakage", test_no_benchmark_tokens),
        ("arbiter rejects worse/disagreement", test_arbiter_rejects_worse_and_disagreement),
        ("arbiter accepts material gain", test_arbiter_accepts_material_consensus_gain),
        ("arbiter rejects numerical dust", test_arbiter_rejects_numerical_dust_gain),
        ("rescue uses arbiter", test_rescue_does_not_bypass_arbiter),
        ("model-only policy cap", test_policy_model_alone_cannot_enable),
        ("persistent controller required", test_policy_helper_requires_persistent_controller),
        ("early-neutral", test_early_neutral),
        ("rescue consumes streak", test_rescue_consumes_evidence_streak),
        ("scale-robust model diagnostics", test_model_diagnostics_common_logp_shift_invariant),
        ("design-space validation", test_design_space_validation),
        ("objective-recorder audit", test_objective_recorder_audit),
        ("trace-matrix validation", test_trace_matrix_rejects_duplicate_and_missing_rows),
        ("frozen baseline tag integrity", test_frozen_baseline_matches_tag),
    ]

    for label, test in fast_tests:
        test()
        print(f"[PASS] {label}")

    print("[RUN ] adaptive exact-budget / engine lifecycle...")
    test_adaptive_exact_budget_and_single_use()
    print("[PASS] adaptive exact-budget / engine lifecycle")

    print("=" * 72)
    print("V0.3.4 logic-hardening self-test: PASS")


if __name__ == "__main__":
    main()
