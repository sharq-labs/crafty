"""
Temporary diagnostic-only script for Rosenbrock adaptive regression.
Does NOT modify product code. Delete after diagnosis.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engcore.adaptive_policy import (
    AdaptiveDecision,
    AdaptivePolicyController,
    apply_decision_to_knobs,
    compute_evidence_score,
)
from src.engcore.landscape_diagnostics import (
    compute_landscape_diagnostics,
)
from src.engcore.models import DesignSpace, Variable
from src.engcore.sampling import sobol_points
from src.engcore.stacked_modes import get_stacked_mode
from src.engcore.validation.local_suite import make_local_suite
from src.engcore.validation.optimizers import (
    run_adaptive_stacked,
    run_stacked,
)
from src.engcore.validation.problem import ObjectiveRecorder


SEED = 123
BUDGET = 20
MODE = "fast"
DEVICE = "cpu"


def get_problem():
    probs = make_local_suite(dimensions=(2,), instances=(1,))
    for p in probs:
        if p.family == "rosenbrock":
            return p
    raise RuntimeError("rosenbrock not found")


def capture_trajectory(runner, problem, label):
    xs = []
    fs = []

    def func(x):
        x = np.asarray(x, dtype=float).copy()
        f = float(problem.func(x))
        xs.append(x)
        fs.append(f)
        return f

    row = runner(
        problem_id=problem.problem_id,
        func=func,
        lower=problem.lower,
        upper=problem.upper,
        budget=BUDGET,
        seed=SEED,
        mode=MODE,
        screen_device=DEVICE,
        refinement_backend="torch",
    )
    return {
        "label": label,
        "row": row,
        "xs": xs,
        "fs": fs,
        "best_f": float(row.best_f),
        "evaluations": int(row.evaluations),
    }


def build_torch_adaptive_engine(problem, func, *, counterfactual=None):
    """Mirror run_adaptive_stacked setup; optional counterfactual knob filter."""
    import time
    from botorch.generation.gen import gen_candidates_torch
    from src.engcore.adaptive_stacked_engine import (
        AdaptiveStackedGPBOEngine,
    )
    from src.engcore.logei_engine import CandidateSource

    rec = ObjectiveRecorder(
        func, problem.lower, problem.upper, BUDGET
    )
    space = DesignSpace([
        Variable(f"x{i}", float(lo), float(hi), "")
        for i, (lo, hi) in enumerate(
            zip(rec.lower, rec.upper)
        )
    ])

    def evaluator(x):
        f = rec.evaluate(x)
        return -float(f), True, {"objective_f": float(f)}

    initial = min(
        max(4, 2 * rec.dimension),
        max(2, rec.budget // 3),
        rec.budget - 1,
    )
    initial = max(1, int(initial))

    class TorchAdaptive(AdaptiveStackedGPBOEngine):
        def _refine_informed_starts(
            self, cpu_acq, starts, maxiter, timeout_sec, seed
        ):
            torch = self.torch
            starts_np = np.asarray(starts, dtype=np.float64)
            if len(starts_np) == 0:
                return None
            initial_conditions = torch.as_tensor(
                starts_np, dtype=self.dtype, device=self.device
            ).unsqueeze(1)
            lower_t = torch.zeros(
                self.space.dim, dtype=self.dtype, device=self.device
            )
            upper_t = torch.ones(
                self.space.dim, dtype=self.dtype, device=self.device
            )
            t0 = time.perf_counter()
            self.fit_diagnostics["refinement_attempts"] += 1
            try:
                candidates, values = gen_candidates_torch(
                    initial_conditions=initial_conditions,
                    acquisition_function=cpu_acq,
                    lower_bounds=lower_t,
                    upper_bounds=upper_t,
                    options={
                        "optimizer_options": {"lr": 0.025},
                        "stopping_criterion_options": {
                            "maxiter": int(maxiter)
                        },
                    },
                    timeout_sec=float(timeout_sec),
                )
                values = values.reshape(-1)
                idx = int(torch.argmax(values).item())
                x01 = (
                    candidates[idx]
                    .detach()
                    .cpu()
                    .double()
                    .numpy()
                    .reshape(-1)
                )
                acq_value = float(
                    values[idx].detach().cpu().double().item()
                )
                if not np.all(np.isfinite(x01)) or not np.isfinite(
                    acq_value
                ):
                    raise RuntimeError("non-finite refine")
                result = CandidateSource(
                    name="adaptive_refined_torch",
                    x01=np.clip(x01, 0.0, 1.0),
                    acquisition_value=acq_value,
                )
            except Exception as exc:
                self.fit_diagnostics["refinement_failures"] += 1
                result = None
            self.timings["refinement_s"] += time.perf_counter() - t0
            return result

    engine = TorchAdaptive(
        design_space=space,
        evaluator=evaluator,
        seed=SEED,
        screen_device=DEVICE,
        record_diagnostics=True,
    )
    engine._diag_counterfactual = counterfactual
    engine._diag_rec = rec
    engine._diag_initial = initial
    return engine


def neutralize_knobs(knobs, mode):
    """Diagnostic-only counterfactual transforms on materialized knobs."""
    k = dict(knobs)
    base_pool = 50_000  # fast mode
    base_pulse = 100_000
    base_severe = 250_000
    base_div = 0.035
    base_rk = 3
    base_rm = 35

    if mode == "A_no_search_realloc":
        k["enable_search_realloc"] = False
        k["screen_pool"] = base_pool
        k["pulse_screen_pool"] = base_pulse
        k["severe_screen_pool"] = base_severe
        k["diversity_radius"] = base_div
        k["refinement_top_k"] = base_rk
        k["refinement_maxiter"] = base_rm
        k["exploration_mix"] = 0.0
    elif mode == "B_no_forced_refit":
        k["force_model_refit"] = False
    elif mode == "C_no_rescue":
        k["enable_rescue_inject"] = False
        k["enable_rescue"] = False
    elif mode == "D_no_diversity_scale":
        k["diversity_radius"] = base_div
    elif mode == "E_no_screen_scale":
        k["screen_pool"] = base_pool
        k["pulse_screen_pool"] = base_pulse
        k["severe_screen_pool"] = base_severe
    elif mode == "F_no_refinement_changes":
        k["refinement_top_k"] = base_rk
        k["refinement_maxiter"] = base_rm
    elif mode == "G_no_strength_dynamics":
        # Identity search knobs + no interventions (strength forced inert)
        k["enable_search_realloc"] = False
        k["force_model_refit"] = False
        k["enable_rescue_inject"] = False
        k["enable_rescue"] = False
        k["screen_pool"] = base_pool
        k["pulse_screen_pool"] = base_pulse
        k["severe_screen_pool"] = base_severe
        k["diversity_radius"] = base_div
        k["refinement_top_k"] = base_rk
        k["refinement_maxiter"] = base_rm
        k["exploration_mix"] = 0.0
    elif mode == "DIAG_ONLY_NO_REPLACE":
        # Diagnostics/controller may run; candidate path forced baseline.
        k["enable_search_realloc"] = False
        k["force_model_refit"] = False
        k["enable_rescue_inject"] = False
        k["enable_rescue"] = False
        k["screen_pool"] = base_pool
        k["pulse_screen_pool"] = base_pulse
        k["severe_screen_pool"] = base_severe
        k["diversity_radius"] = base_div
        k["refinement_top_k"] = base_rk
        k["refinement_maxiter"] = base_rm
        k["exploration_mix"] = 0.0
    return k


def run_instrumented(problem, *, counterfactual=None, dual_candidates=True):
    """
    Copy of adaptive BO loop with dual baseline/adaptive candidate generation
    and optional counterfactual knob neutralization.
    """
    import time
    from src.engcore.logei_engine import CandidateSource

    xs = []
    fs = []

    def func(x):
        x = np.asarray(x, dtype=float).copy()
        f = float(problem.func(x))
        xs.append(x)
        fs.append(f)
        return f

    engine = build_torch_adaptive_engine(
        problem, func, counterfactual=counterfactual
    )
    mode_cfg = get_stacked_mode(MODE)
    initial = engine._diag_initial
    smart = BUDGET - initial

    # Monkeypatch apply path via wrapping controller update result
    original_apply = apply_decision_to_knobs

    step_traces = []

    # Inline run (mirrors AdaptiveStackedGPBOEngine.run with instrumentation)
    from src.engcore.adaptive_stacked_engine import AdaptiveStackedGPBOEngine

    # Use engine.run but intercept via patched apply_decision_to_knobs
    import src.engcore.adaptive_stacked_engine as ase

    traces_box = {"steps": []}

    def patched_apply(decision, **base_knobs):
        knobs = original_apply(decision, **base_knobs)
        knobs["_raw"] = dict(knobs)
        if counterfactual is not None:
            knobs = neutralize_knobs(knobs, counterfactual)
        return knobs

    # Dual-candidate instrumented run by subclassing and overriding run
    class Instr(engine.__class__):
        def run(self, **kwargs):
            # Call parent adaptive run but we need dual candidates —
            # reimplement with hooks by calling super then... can't.
            # Full instrumented loop below.
            return self._instr_run(**kwargs)

        def _instr_run(
            self,
            initial_trials=12,
            smart_trials=68,
            refit_interval=4,
            screen_pool=100_000,
            screen_chunk_size=2048,
            top_k=8,
            refinement_top_k=4,
            diversity_radius=0.035,
            refinement_maxiter=50,
            refinement_timeout_sec=3.0,
            stagnation_trigger=6,
            pulse_interval=6,
            pulse_screen_pool=250_000,
            severe_stagnation_trigger=12,
            severe_screen_pool=500_000,
            verbose=False,
            record_diagnostics=None,
        ):
            if record_diagnostics is None:
                record_diagnostics = self.record_diagnostics
            self.diagnostic_history = []
            self.policy_history = []
            self.policy_controller.reset()

            initial_pts = sobol_points(
                int(initial_trials), self.space.dim, self.seed
            )
            for p in initial_pts:
                self._evaluate01(p)

            total_steps = int(smart_trials)
            total_budget = int(initial_trials) + total_steps
            best = self._best_feasible_score()
            stagnation = 0
            severe_used = False

            base_knobs = dict(
                screen_pool=int(screen_pool),
                pulse_screen_pool=int(pulse_screen_pool),
                severe_screen_pool=int(severe_screen_pool),
                diversity_radius=float(diversity_radius),
                refinement_top_k=int(refinement_top_k),
                refinement_maxiter=int(refinement_maxiter),
                top_k=int(top_k),
            )

            for step in range(total_steps):
                eval_before = len(self.history)
                diagnostics = compute_landscape_diagnostics(
                    x01_history=self.x01_history,
                    scores=self._scores_array(),
                    best_score=float(best),
                    evaluations_since_improve=int(stagnation),
                    total_budget=total_budget,
                    dimension=self.space.dim,
                    weight_rbf=self.stacking_weight_rbf,
                    weight_history=self.weight_history,
                )
                evidence, parts = compute_evidence_score(diagnostics)
                decision = self.policy_controller.update(
                    diagnostics,
                    base_stagnation_trigger=int(stagnation_trigger),
                    step=step,
                )
                knobs_raw = original_apply(decision, **base_knobs)
                knobs = (
                    neutralize_knobs(knobs_raw, counterfactual)
                    if counterfactual is not None
                    else dict(knobs_raw)
                )

                # Identity baseline knobs for dual candidate
                knobs_base = neutralize_knobs(knobs_raw, "DIAG_ONLY_NO_REPLACE")

                pulse = (
                    stagnation >= int(stagnation_trigger)
                    and (stagnation - int(stagnation_trigger))
                    % max(1, int(pulse_interval))
                    == 0
                )
                severe_pulse = (
                    stagnation >= int(severe_stagnation_trigger)
                    and not severe_used
                )
                if severe_pulse:
                    severe_used = True

                opt_base = (
                    step == 0
                    or int(refit_interval) <= 1
                    or step % int(refit_interval) == 0
                    or pulse
                    or severe_pulse
                )
                opt_adapt = opt_base or bool(knobs["force_model_refit"])

                # Fit for adaptive path (executed path)
                rbf_cpu, mat_cpu = self._fit_pair(optimize=opt_adapt)
                if opt_adapt:
                    self._update_stacking_weight(rbf_cpu, mat_cpu)
                cpu_acq, acquisition_mode = self._build_stacked_acquisition(
                    rbf_cpu, mat_cpu
                )
                screen_acq = cpu_acq

                def gen_candidate(kn, optimize_flag_used, tag):
                    if severe_pulse:
                        active_pool = int(kn["severe_screen_pool"])
                    elif pulse:
                        active_pool = int(kn["pulse_screen_pool"])
                    else:
                        active_pool = int(kn["screen_pool"])
                    pool = sobol_points(
                        active_pool,
                        self.space.dim,
                        self.seed + 100_000 + step,
                    )
                    scores = self._score_global_pool(
                        acq=screen_acq,
                        pool=pool,
                        chunk_size=int(screen_chunk_size),
                    )
                    starts, start_scores = self._select_informed_starts(
                        pool=pool,
                        scores=scores,
                        top_k=int(top_k),
                        diversity_radius=float(kn["diversity_radius"]),
                    )
                    starts, start_scores = self._mix_exploration_starts(
                        starts,
                        start_scores,
                        mix=float(kn["exploration_mix"]),
                        seed=self.seed + 700_000 + step,
                    )
                    discrete = CandidateSource(
                        name=f"{tag}_discrete",
                        x01=starts[0].copy(),
                        acquisition_value=float(start_scores[0]),
                    )
                    discrete.acquisition_value = self._acq_value_cpu(
                        cpu_acq, discrete.x01
                    )
                    refine_count = min(
                        int(kn["refinement_top_k"]), len(starts)
                    )
                    refined = self._refine_informed_starts(
                        cpu_acq=cpu_acq,
                        starts=starts[:refine_count],
                        maxiter=int(kn["refinement_maxiter"]),
                        timeout_sec=float(refinement_timeout_sec),
                        seed=self.seed + 900_000 + step,
                    )
                    chosen = discrete
                    source = discrete.name
                    if refined is not None:
                        refined.acquisition_value = self._acq_value_cpu(
                            cpu_acq, refined.x01
                        )
                        if (
                            not self._is_duplicate(refined.x01)
                            and refined.acquisition_value
                            > discrete.acquisition_value + 1e-12
                        ):
                            chosen = refined
                            source = f"{tag}_refined"
                    if kn.get("enable_rescue_inject"):
                        rescue_X = self._build_rescue_candidates(
                            n_global=max(32, 8 * self.space.dim),
                            n_local=max(16, 4 * self.space.dim),
                            seed=self.seed + 300_000 + step,
                        )
                        rescue = self._best_rescue_by_acquisition(
                            cpu_acq, rescue_X
                        )
                        if (
                            rescue is not None
                            and rescue.acquisition_value
                            > chosen.acquisition_value + 1e-12
                        ):
                            chosen = rescue
                            source = "adaptive_rescue"
                    if self._is_duplicate(chosen.x01):
                        for x, value in zip(starts[1:], start_scores[1:]):
                            if not self._is_duplicate(x):
                                chosen = CandidateSource(
                                    name=f"{tag}_dup_recovery",
                                    x01=x.copy(),
                                    acquisition_value=float(value),
                                )
                                source = chosen.name
                                break
                    return {
                        "x01": chosen.x01.copy(),
                        "acq": float(chosen.acquisition_value),
                        "source": source,
                        "pool": active_pool,
                        "div": float(kn["diversity_radius"]),
                        "refine_k": int(kn["refinement_top_k"]),
                        "refine_m": int(kn["refinement_maxiter"]),
                        "mix": float(kn["exploration_mix"]),
                    }

                # Adaptive candidate first (executed path). Then baseline
                # under restored torch RNG so subsequent steps match a
                # single-candidate product run.
                torch_mod = self.torch
                pre_rng = torch_mod.random.get_rng_state()
                pre_cuda = None
                if torch_mod.cuda.is_available():
                    try:
                        pre_cuda = torch_mod.cuda.get_rng_state_all()
                    except Exception:
                        pre_cuda = None

                adapt_cand = gen_candidate(knobs, opt_adapt, "adapt")
                post_rng = torch_mod.random.get_rng_state()
                post_cuda = None
                if torch_mod.cuda.is_available():
                    try:
                        post_cuda = torch_mod.cuda.get_rng_state_all()
                    except Exception:
                        post_cuda = None

                torch_mod.random.set_rng_state(pre_rng)
                if pre_cuda is not None:
                    torch_mod.cuda.set_rng_state_all(pre_cuda)
                base_cand = gen_candidate(
                    knobs_base, opt_base, "base"
                )
                torch_mod.random.set_rng_state(post_rng)
                if post_cuda is not None:
                    torch_mod.cuda.set_rng_state_all(post_cuda)

                chosen_x = adapt_cand["x01"]
                chosen_src = adapt_cand["source"]
                chosen_acq = adapt_cand["acq"]

                def to_x(x01):
                    return self.space.denormalize(
                        np.asarray(x01, dtype=np.float64)
                    )

                previous_best = best
                result = self._evaluate01(chosen_x)
                best = self._best_feasible_score()
                improved = best > previous_best + 1e-10
                if improved:
                    stagnation = 0
                    severe_used = False
                else:
                    stagnation += 1

                obj_f = float(
                    result.metadata.get(
                        "objective_f", -result.score
                    )
                )
                row = {
                    "step": step,
                    "eval_number": eval_before + 1,
                    "x": to_x(chosen_x).tolist(),
                    "x01": chosen_x.tolist(),
                    "objective": obj_f,
                    "incumbent_score": float(best),
                    "incumbent_f": float(-best) if np.isfinite(best) else None,
                    "baseline_x": to_x(base_cand["x01"]).tolist(),
                    "adaptive_x": to_x(adapt_cand["x01"]).tolist(),
                    "baseline_x01": base_cand["x01"].tolist(),
                    "adaptive_x01": adapt_cand["x01"].tolist(),
                    "executed_x": to_x(chosen_x).tolist(),
                    "candidate_source": chosen_src,
                    "baseline_source": base_cand["source"],
                    "baseline_acq": base_cand["acq"],
                    "adaptive_acq": adapt_cand["acq"],
                    "candidates_differ": not np.allclose(
                        base_cand["x01"], adapt_cand["x01"]
                    ),
                    "evidence_score": float(decision.evidence_score),
                    "search_failure": float(parts["search_failure"]),
                    "model_support": float(parts["model_support"]),
                    "adaptation_strength": float(
                        decision.adaptation_strength
                    ),
                    "consecutive_evidence": int(
                        decision.consecutive_evidence
                    ),
                    "cooldown": int(decision.cooldown_remaining),
                    "search_realloc": bool(knobs["enable_search_realloc"]),
                    "forced_refit": bool(knobs["force_model_refit"]),
                    "rescue_inject": bool(knobs["enable_rescue_inject"]),
                    "raw_search_realloc": bool(
                        knobs_raw["enable_search_realloc"]
                    ),
                    "raw_forced_refit": bool(
                        knobs_raw["force_model_refit"]
                    ),
                    "raw_rescue_inject": bool(
                        knobs_raw["enable_rescue_inject"]
                    ),
                    "screen_mult": float(decision.screen_pool_mult),
                    "diversity_mult": float(
                        decision.diversity_radius_mult
                    ),
                    "refine_k_delta": int(
                        decision.refinement_top_k_delta
                    ),
                    "refine_iter_delta": int(
                        decision.refinement_maxiter_delta
                    ),
                    "exploration_mix": float(decision.exploration_mix),
                    "weight_rbf": float(self.stacking_weight_rbf),
                    "opt_base": bool(opt_base),
                    "opt_adapt": bool(opt_adapt),
                    "pool_base": base_cand["pool"],
                    "pool_adapt": adapt_cand["pool"],
                    "div_base": base_cand["div"],
                    "div_adapt": adapt_cand["div"],
                    "reason": decision.reason,
                    "intervention_type": decision.intervention_type,
                    "n_obs": int(diagnostics.n_obs),
                    "stagnation_score": float(
                        diagnostics.stagnation_score
                    ),
                    "model_reliability": float(
                        diagnostics.model_reliability
                    ),
                    "model_error_proxy": float(
                        diagnostics.model_error_proxy
                    ),
                    "incumbent_locality": float(
                        diagnostics.incumbent_locality
                    ),
                    "recent_improvement_rate": float(
                        diagnostics.recent_improvement_rate
                    ),
                    "exploration_coverage": float(
                        diagnostics.exploration_coverage
                    ),
                    "evaluations_since_improve": int(
                        diagnostics.evaluations_since_improve
                    ),
                }
                traces_box["steps"].append(row)

            best_trial = max(
                self.history, key=lambda r: r.score
            )
            return {
                "best": best_trial,
                "trials_run": len(self.history),
                "fit_diagnostics": dict(self.fit_diagnostics),
            }

    instr = Instr(
        design_space=engine.space,
        evaluator=engine.evaluator,
        seed=SEED,
        screen_device=DEVICE,
        record_diagnostics=True,
    )
    # share nothing — fresh engine
    result = instr._instr_run(
        initial_trials=initial,
        smart_trials=smart,
        verbose=False,
        **mode_cfg,
    )
    best_f = min(fs) if fs else float("inf")
    return {
        "best_f": best_f,
        "xs": xs,
        "fs": fs,
        "steps": traces_box["steps"],
        "initial": initial,
        "result": result,
        "n_obj": instr._diag_rec.n_calls
        if hasattr(instr, "_diag_rec")
        else len(fs),
    }


def main():
    problem = get_problem()
    print("=" * 72)
    print("ROSENBROCK DIAGNOSIS (diagnostic-only, no product edits)")
    print(f"problem={problem.problem_id} seed={SEED} budget={BUDGET}")
    print("=" * 72)

    print("\n[1] Capture stacked vs adaptive trajectories...")
    stacked = capture_trajectory(run_stacked, problem, "stacked")
    adaptive = capture_trajectory(
        run_adaptive_stacked, problem, "adaptive"
    )
    print(
        f"  stacked best_f={stacked['best_f']:.6g} "
        f"evals={stacked['evaluations']}"
    )
    print(
        f"  adaptive best_f={adaptive['best_f']:.6g} "
        f"evals={adaptive['evaluations']}"
    )

    first_div = None
    for i, (xs, xa) in enumerate(
        zip(stacked["xs"], adaptive["xs"])
    ):
        if not np.allclose(xs, xa, rtol=0, atol=1e-12):
            first_div = i
            break
    n_dev = sum(
        1
        for xs, xa in zip(stacked["xs"], adaptive["xs"])
        if not np.allclose(xs, xa, rtol=0, atol=1e-12)
    )
    print(f"  first divergence eval index (0-based)={first_div}")
    print(f"  number of executed deviations={n_dev}/{BUDGET}")

    print("\n[2] Instrumented adaptive dual-candidate run...")
    instr = run_instrumented(problem, counterfactual=None)
    print(
        f"  instrumented best_f={instr['best_f']:.6g} "
        f"steps={len(instr['steps'])} initial={instr['initial']}"
    )
    # Sanity: instrumented adaptive should match product adaptive best closely
    print(
        f"  product adaptive best_f={adaptive['best_f']:.6g} "
        f"(compare instrumented)"
    )

    # Align first divergence with instrumented step
    # DOE points are first `initial` evals; smart steps follow
    initial = instr["initial"]
    print(f"\n  DOE initial_trials={initial}")
    if first_div is not None:
        print(f"\n[FIRST DIVERGENCE DETAIL] eval#{first_div+1}")
        print(f"  stacked x={stacked['xs'][first_div]}")
        print(f"  adaptive x={adaptive['xs'][first_div]}")
        print(f"  stacked f={stacked['fs'][first_div]:.6g}")
        print(f"  adaptive f={adaptive['fs'][first_div]:.6g}")
        if first_div >= initial:
            step_i = first_div - initial
            if 0 <= step_i < len(instr["steps"]):
                s = instr["steps"][step_i]
                print("\n  --- instrumented policy state at this step ---")
                for key in (
                    "step",
                    "eval_number",
                    "n_obs",
                    "evidence_score",
                    "search_failure",
                    "model_support",
                    "adaptation_strength",
                    "consecutive_evidence",
                    "cooldown",
                    "search_realloc",
                    "forced_refit",
                    "rescue_inject",
                    "screen_mult",
                    "diversity_mult",
                    "refine_k_delta",
                    "refine_iter_delta",
                    "exploration_mix",
                    "pool_base",
                    "pool_adapt",
                    "div_base",
                    "div_adapt",
                    "opt_base",
                    "opt_adapt",
                    "baseline_acq",
                    "adaptive_acq",
                    "candidates_differ",
                    "baseline_source",
                    "candidate_source",
                    "reason",
                    "intervention_type",
                    "stagnation_score",
                    "model_reliability",
                    "model_error_proxy",
                    "incumbent_locality",
                    "recent_improvement_rate",
                    "exploration_coverage",
                    "evaluations_since_improve",
                    "weight_rbf",
                ):
                    print(f"  {key}: {s[key]}")
                print(f"  baseline_x: {s['baseline_x']}")
                print(f"  adaptive_x: {s['adaptive_x']}")
                print(f"  executed_x: {s['executed_x']}")
                # Which knobs differ?
                print("\n  knob deltas vs baseline identity:")
                print(
                    f"    pool {s['pool_base']} -> {s['pool_adapt']}"
                )
                print(
                    f"    diversity {s['div_base']} -> {s['div_adapt']}"
                )
                print(
                    f"    screen_mult={s['screen_mult']} "
                    f"div_mult={s['diversity_mult']} "
                    f"refine_k_delta={s['refine_k_delta']} "
                    f"refine_iter_delta={s['refine_iter_delta']} "
                    f"mix={s['exploration_mix']}"
                )
                print(
                    f"    force_refit schedule change: "
                    f"opt_base={s['opt_base']} opt_adapt={s['opt_adapt']}"
                )
                print(
                    f"    rescue_inject={s['rescue_inject']} "
                    f"source={s['candidate_source']}"
                )

    print("\n[3] Full step table (smart BO only):")
    print(
        f"{'ev':>3} {'evid':>6} {'sfail':>6} {'msup':>6} {'str':>6} "
        f"{'ce':>3} {'cd':>3} {'realloc':>7} {'refit':>5} {'rescue':>6} "
        f"{'smult':>5} {'dmult':>5} {'diff':>4} {'src':<22} {'f':>10}"
    )
    for s in instr["steps"]:
        print(
            f"{s['eval_number']:3d} {s['evidence_score']:6.3f} "
            f"{s['search_failure']:6.3f} {s['model_support']:6.3f} "
            f"{s['adaptation_strength']:6.3f} {s['consecutive_evidence']:3d} "
            f"{s['cooldown']:3d} {str(s['search_realloc']):>7} "
            f"{str(s['forced_refit']):>5} {str(s['rescue_inject']):>6} "
            f"{s['screen_mult']:5.2f} {s['diversity_mult']:5.2f} "
            f"{str(s['candidates_differ']):>4} {s['candidate_source']:<22} "
            f"{s['objective']:10.4g}"
        )

    print("\n[4] Counterfactual replays (one mechanism neutralized)...")
    modes = [
        "A_no_search_realloc",
        "B_no_forced_refit",
        "C_no_rescue",
        "D_no_diversity_scale",
        "E_no_screen_scale",
        "F_no_refinement_changes",
        "G_no_strength_dynamics",
        "DIAG_ONLY_NO_REPLACE",
    ]
    cf_results = {}
    for m in modes:
        r = run_instrumented(problem, counterfactual=m)
        cf_results[m] = r["best_f"]
        # Check identity vs stacked for DIAG_ONLY
        if m == "DIAG_ONLY_NO_REPLACE":
            identical = all(
                np.allclose(a, b, rtol=0, atol=1e-12)
                for a, b in zip(stacked["xs"], r["xs"])
            )
            cf_results[m + "_bit_identical_to_stacked"] = identical
        print(f"  {m:28s} best_f={r['best_f']:.6g}")

    # Deviation dominance: if we force match stacked until first div then...
    # Simpler: report cumulative best after each deviation
    print("\n[5] Trajectory recovery analysis")
    print(
        f"{'ev':>3} {'stack_f':>12} {'adapt_f':>12} {'stack_best':>12} "
        f"{'adapt_best':>12} {'diff':>5}"
    )
    sb = float("inf")
    ab = float("inf")
    for i in range(BUDGET):
        sb = min(sb, stacked["fs"][i])
        ab = min(ab, adaptive["fs"][i])
        diff = not np.allclose(
            stacked["xs"][i], adaptive["xs"][i], rtol=0, atol=1e-12
        )
        print(
            f"{i+1:3d} {stacked['fs'][i]:12.5g} {adaptive['fs'][i]:12.5g} "
            f"{sb:12.5g} {ab:12.5g} {str(diff):>5}"
        )

    # Complexity audit
    pol = (
        ROOT / "src" / "engcore" / "adaptive_policy.py"
    ).read_text(encoding="utf-8")
    lines = [
        ln
        for ln in pol.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    import re
    const_names = re.findall(
        r"^([A-Z][A-Z0-9_]+)\s*=\s*", pol, flags=re.M
    )
    # rough branch count
    branches = len(
        re.findall(r"\b(if|elif|else)\b", pol)
    )

    out = {
        "stacked_best": stacked["best_f"],
        "adaptive_best": adaptive["best_f"],
        "first_divergence_eval_1based": (
            None if first_div is None else first_div + 1
        ),
        "n_deviations": n_dev,
        "counterfactuals": cf_results,
        "complexity": {
            "logical_loc": len(lines),
            "constants": const_names,
            "n_constants": len(const_names),
            "n_if_elif_else": branches,
        },
        "steps": instr["steps"],
        "initial": initial,
    }
    out_path = Path(__file__).resolve().parent / "rosenbrock_diag.json"
    # make JSON safe
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {out_path}")

    print("\n[6] Complexity")
    print(f"  logical LOC (nonblank noncomment): {len(lines)}")
    print(f"  constants ({len(const_names)}): {const_names}")
    print(f"  if/elif/else count: {branches}")
    print(
        "  controller state: consecutive_evidence, consecutive_recovery, "
        "adaptation_strength, cooldown_remaining, last_intervention, "
        "intervention_start_step"
    )


if __name__ == "__main__":
    main()
