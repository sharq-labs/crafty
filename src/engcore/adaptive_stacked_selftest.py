"""
Fast V0.3.3 adaptive + arbiter property tests.

Uses synthetic states and tiny randomized toy landscapes.
Does NOT select thresholds from BBOB / named smoke scores.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .adaptive_policy import (
    AdaptivePolicyController,
    EVIDENCE_MILD,
    MODEL_ONLY_EVIDENCE_CAP,
    compute_evidence_score,
    is_early_neutral,
)
from .adaptive_stacked_engine import (
    AdaptiveStackedGPBOEngine,
)
from .candidate_arbiter import (
    ProposalView,
    arbitrate_proposals,
    components_disagree,
)
from .landscape_diagnostics import LandscapeDiagnostics
from .models import DesignSpace, Variable
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode
from .validation.optimizers import (
    ALGORITHMS,
    run_adaptive_stacked,
    run_stacked,
)


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


def test_A_neutral_equals_stacked():
    def func(x):
        x = np.asarray(x, dtype=float)
        return float(
            np.sum((x - 0.2) ** 2) + 0.05 * np.sin(3 * x[0])
        )

    lower = np.array([-1.5, -1.5])
    upper = np.array([1.5, 1.5])
    budget = 8  # early-neutral throughout for dim=2
    xs, xa = [], []
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
    _require(
        all(np.allclose(a, b) for a, b in zip(xs, xa)),
        "neutral trajectory != stacked",
    )


def test_B_rejected_executes_identity():
    identity = _prop([0.1, 0.2], mix=1.0, rbf=1.0, mat=1.0, source="identity")
    adaptive = _prop([0.9, 0.9], mix=0.5, rbf=0.5, mat=0.5, source="adaptive")
    chosen, dec = arbitrate_proposals(
        identity, adaptive, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "should reject")
    _require(np.allclose(chosen.x01, identity.x01), "identity exec")
    _require(dec.executed_source == "identity", "src")


def test_C_consensus_accepts_adaptive():
    identity = _prop([0.1, 0.2], mix=1.0, rbf=1.0, mat=1.0)
    adaptive = _prop([0.3, 0.4], mix=1.5, rbf=1.2, mat=1.1)
    chosen, dec = arbitrate_proposals(
        identity, adaptive, adaptive_enabled=True
    )
    _require(dec.choose_adaptive, "should accept")
    _require(np.allclose(chosen.x01, adaptive.x01), "adaptive exec")
    _require("consensus_accept" in dec.reason, "reason")


def test_D_component_disagreement_prefers_identity():
    identity = _prop([0.1, 0.2], mix=1.0, rbf=1.0, mat=1.0)
    # RBF prefers adaptive, Matern prefers identity
    adaptive = _prop([0.3, 0.4], mix=1.2, rbf=1.5, mat=0.5)
    _require(
        components_disagree(1.0, 1.0, 1.5, 0.5),
        "disagree helper",
    )
    chosen, dec = arbitrate_proposals(
        identity, adaptive, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "reject on disagree")
    _require(dec.component_disagreement, "flag")
    _require(np.allclose(chosen.x01, identity.x01), "identity")


def test_E_rescue_does_not_bypass_arbiter():
    identity = _prop([0.1, 0.2], mix=1.0, rbf=1.0, mat=1.0)
    rescue = _prop(
        [0.8, 0.8],
        mix=0.2,
        rbf=0.2,
        mat=0.2,
        source="adaptive_rescue",
        rescue=True,
    )
    chosen, dec = arbitrate_proposals(
        identity, rescue, adaptive_enabled=True
    )
    _require(not dec.choose_adaptive, "rescue rejected")
    _require(np.allclose(chosen.x01, identity.x01), "identity")

    # Even a strong rescue must pass consensus
    rescue_ok = _prop(
        [0.3, 0.3],
        mix=2.0,
        rbf=1.5,
        mat=1.4,
        source="adaptive_rescue",
        rescue=True,
    )
    chosen2, dec2 = arbitrate_proposals(
        identity, rescue_ok, adaptive_enabled=True
    )
    _require(dec2.choose_adaptive, "rescue can pass consensus")
    _require("rescue" in dec2.reason, "rescue reason")


def test_F_dual_proposals_no_extra_objective_calls():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        x = np.asarray(x, dtype=float)
        return float(np.sum((x - 0.3) ** 2))

    budget = 16
    row = run_adaptive_stacked(
        problem_id="dual",
        func=func,
        lower=np.array([-2.0, -2.0]),
        upper=np.array([2.0, 2.0]),
        budget=budget,
        seed=21,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )
    _require(row.evaluations == budget == calls["n"], "obj calls")
    meta = row.metadata
    # dual proposals may be generated; objective count still exact
    _require(
        meta.get("adaptive_forced_refits", 0) == 0,
        "forced refits must be zero",
    )


def test_G_exact_budgets():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        return float(np.sum(np.asarray(x) ** 2))

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


def test_H_deterministic_replay():
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
        initial_trials=4, smart_trials=8, verbose=False, **mode
    )
    r2 = make_engine(7).run(
        initial_trials=4, smart_trials=8, verbose=False, **mode
    )
    _require(
        np.allclose(r1["best"].x, r2["best"].x),
        "best x mismatch",
    )
    xs1 = [np.asarray(r.x) for r in r1["history"]]
    xs2 = [np.asarray(r.x) for r in r2["history"]]
    _require(
        all(np.allclose(a, b) for a, b in zip(xs1, xs2)),
        "trajectory mismatch",
    )


def test_I_no_benchmark_leakage():
    test_no_benchmark_tokens()


def test_J_baseline_files_unchanged():
    import subprocess

    files = [
        "src/engcore/stacked_engine.py",
        "src/engcore/stacked_acquisition.py",
        "src/engcore/stacked_modes.py",
        "src/engcore/hybrid_engine.py",
        "src/engcore/logei_engine.py",
    ]
    out = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "--", *files],
        text=True,
    ).strip()
    _require(out == "", f"baseline files dirty: {out}")
    _require(isinstance(StackedGPBOEngine, type), "cls")
    _require("adaptive_stacked" in ALGORITHMS, "reg")


def test_K_no_adaptive_forced_refit():
    """Refit schedule follows stacked semantics; forced-refit counter is 0."""

    def func(x):
        return float(np.sum((np.asarray(x) - 0.1) ** 2))

    lower = np.array([-2.0, -2.0])
    upper = np.array([2.0, 2.0])
    budget = 8

    # Capture engine diagnostics via direct engines on identical short run.
    def run_eng(Engine, seed=5):
        def evaluator(x):
            f = func(x)
            return -float(f), True, {"objective_f": float(f)}

        kwargs = dict(
            design_space=_space(2),
            evaluator=evaluator,
            seed=seed,
            screen_device="cpu",
        )
        if Engine is AdaptiveStackedGPBOEngine:
            kwargs["record_diagnostics"] = True
        eng = Engine(**kwargs)
        mode = dict(get_stacked_mode("fast"))
        mode.update({
            "screen_pool": 2048,
            "pulse_screen_pool": 4096,
            "severe_screen_pool": 4096,
            "refinement_timeout_sec": 0.5,
        })
        return eng.run(
            initial_trials=4,
            smart_trials=budget - 4,
            verbose=False,
            **mode,
        )

    r_s = run_eng(StackedGPBOEngine)
    r_a = run_eng(AdaptiveStackedGPBOEngine)
    _require(
        r_a["fit_diagnostics"].get("adaptive_forced_refits", 0) == 0,
        "forced refits nonzero",
    )
    # Same observation schedule (early-neutral → identity always):
    # optimized fit counts must match.
    _require(
        r_s["fit_diagnostics"]["rbf_optimized_fits"]
        == r_a["fit_diagnostics"]["rbf_optimized_fits"],
        "rbf optimized fits diverge",
    )
    _require(
        r_s["fit_diagnostics"]["matern25_optimized_fits"]
        == r_a["fit_diagnostics"]["matern25_optimized_fits"],
        "matern optimized fits diverge",
    )


def test_policy_model_alone_cannot_enable():
    ctl = AdaptivePolicyController()
    d = _diag(
        n_obs=20,
        model_reliability=0.05,
        model_error_proxy=0.99,
        stagnation_score=0.05,
        recent_improvement_rate=0.3,
    )
    for step in range(5):
        dec = ctl.update(d, step=step)
    evidence, parts = compute_evidence_score(d)
    _require(evidence <= MODEL_ONLY_EVIDENCE_CAP + 1e-12, "cap")
    _require(not dec.enable_adaptive_proposal, "enabled")


def test_early_neutral():
    d = _diag(n_obs=4, dimension=2, stagnation_score=0.9)
    _require(is_early_neutral(d), "early")
    ctl = AdaptivePolicyController()
    dec = ctl.update(d, step=0)
    _require(not dec.enable_adaptive_proposal, "prop")
    _require(dec.proposal_level == "none", "level")


def run_randomized_holdout():
    from .validation.metrics import summarize_traces

    rng = np.random.default_rng(20260333)
    dim = 2
    budget = 16
    problems = []
    for i in range(8):
        shift = rng.uniform(-0.4, 0.4, size=dim)
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
    gen = acc = rej = res_g = res_a = 0
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
        md = rows["adaptive_stacked"].metadata
        gen += int(md.get("adaptive_proposals_generated", 0))
        acc += int(md.get("adaptive_proposals_accepted", 0))
        rej += int(md.get("adaptive_proposals_rejected", 0))
        res_g += int(md.get("adaptive_rescue_proposals", 0))
        res_a += int(md.get("adaptive_rescue_accepted", 0))

    summary = summarize_traces(traces)
    reject_rate = (rej / gen) if gen else 0.0
    return {
        "summary": summary["algorithms"],
        "catastrophic": catastrophic,
        "n_problems": len(problems),
        "proposals_generated": gen,
        "proposals_accepted": acc,
        "proposals_rejected": rej,
        "reject_rate": reject_rate,
        "rescue_generated": res_g,
        "rescue_accepted": res_a,
        "adaptive_effectively_disabled": gen == 0 or acc == 0,
    }


def main():
    print(
        "Engineering AI Core V0.3.3 — "
        "Adaptive Arbiter Property Self-Test"
    )
    print("=" * 72)

    test_I_no_benchmark_leakage()
    print("[PASS] I no benchmark leakage")

    test_B_rejected_executes_identity()
    print("[PASS] B rejected => identity executed")

    test_C_consensus_accepts_adaptive()
    print("[PASS] C consensus can accept adaptive")

    test_D_component_disagreement_prefers_identity()
    print("[PASS] D disagreement => identity")

    test_E_rescue_does_not_bypass_arbiter()
    print("[PASS] E rescue does not bypass arbiter")

    test_policy_model_alone_cannot_enable()
    print("[PASS] model-alone cannot enable proposals")

    test_early_neutral()
    print("[PASS] early-neutral identity-only")

    test_J_baseline_files_unchanged()
    print("[PASS] J baseline files unchanged")

    print("[RUN ] budgets / dual-proposal / replay / neutral...")
    test_F_dual_proposals_no_extra_objective_calls()
    print("[PASS] F dual proposals add 0 objective calls")

    test_G_exact_budgets()
    print("[PASS] G exact budgets 7/13/25")

    test_H_deterministic_replay()
    print("[PASS] H deterministic replay")

    test_A_neutral_equals_stacked()
    print("[PASS] A neutral == stacked")

    test_K_no_adaptive_forced_refit()
    print("[PASS] K no adaptive forced refit / schedule match")

    print("[RUN ] randomized mini holdout...")
    hold = run_randomized_holdout()
    print(
        "[PASS] holdout "
        f"n={hold['n_problems']} cat={hold['catastrophic']} "
        f"gen={hold['proposals_generated']} "
        f"acc={hold['proposals_accepted']} "
        f"rej={hold['proposals_rejected']} "
        f"reject_rate={hold['reject_rate']:.2f} "
        f"rescue_g={hold['rescue_generated']} "
        f"rescue_a={hold['rescue_accepted']}"
    )
    for name, s in hold["summary"].items():
        print(
            f"  {name:22s} mean_rank={s['mean_rank']:.3f} "
            f"wins={s['wins']} win_share={s['win_share']:.2f}"
        )
    _require(
        hold["catastrophic"] <= 1,
        f"too many catastrophic: {hold['catastrophic']}",
    )
    # Safety without permanent disable: allow zero accepts on tiny holdout,
    # but require that mild evidence *can* generate proposals in unit tests
    # (covered by C). Warn only via return flag.
    print(
        "  adaptive_effectively_disabled_on_holdout="
        f"{hold['adaptive_effectively_disabled']}"
    )

    print("=" * 72)
    print("V0.3.3 Adaptive Arbiter property self-test: PASS")
    return hold


if __name__ == "__main__":
    main()
