"""
Adaptive Stacked GP-BO engine — V0.3.3 / adaptive_stacked_v033

Extends StackedGPBOEngine without modifying stacked_v0301 semantics.
Adds online diagnostics, a minimal adaptive knob policy, and a budget-safe
rescue candidate source (acquisition-scored only).
"""

from __future__ import annotations

import time

import numpy as np

from .adaptive_policy import (
    apply_decision_to_knobs,
    decide_adaptive_policy,
)
from .landscape_diagnostics import (
    compute_landscape_diagnostics,
)
from .logei_engine import CandidateSource
from .sampling import sobol_points
from .stacked_engine import StackedGPBOEngine


class AdaptiveStackedGPBOEngine(StackedGPBOEngine):
    """
    Observation -> diagnostics -> policy -> candidate allocation -> evaluate.
    """

    ENGINE_ID = "adaptive_stacked_v033"

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        screen_device="auto",
        record_diagnostics=True,
        **kwargs,
    ):
        super().__init__(
            design_space=design_space,
            evaluator=evaluator,
            seed=seed,
            screen_device=screen_device,
            **kwargs,
        )
        self.record_diagnostics = bool(
            record_diagnostics
        )
        self.diagnostic_history = []
        self.policy_history = []
        self.fit_diagnostics.update({
            "adaptive_rescue_triggers": 0,
            "adaptive_rescue_selected": 0,
            "adaptive_exploration_mix_uses": 0,
            "adaptive_policy_updates": 0,
        })

    def _scores_array(self):
        return np.asarray(
            [float(r.score) for r in self.history],
            dtype=np.float64,
        )

    def _incumbent_x01(self):
        if not self.history:
            return np.full(
                self.space.dim,
                0.5,
                dtype=np.float64,
            )
        scores = self._scores_array()
        idx = int(np.argmax(scores))
        return np.asarray(
            self.x01_history[idx],
            dtype=np.float64,
        ).copy()

    def _build_rescue_candidates(
        self,
        *,
        n_global: int,
        n_local: int,
        seed: int,
        sigma: float = 0.12,
    ):
        """
        Generic rescue sources (no objective calls):
        - fresh space-filling Sobol
        - incumbent-centered Gaussian perturbations clipped to [0,1]
        """
        parts = []
        if n_global > 0:
            parts.append(
                sobol_points(
                    int(n_global),
                    self.space.dim,
                    int(seed),
                )
            )
        if n_local > 0:
            rng = np.random.default_rng(int(seed) + 17)
            center = self._incumbent_x01()
            local = center[None, :] + sigma * rng.standard_normal(
                (int(n_local), self.space.dim)
            )
            parts.append(np.clip(local, 0.0, 1.0))
        if not parts:
            return np.zeros(
                (0, self.space.dim),
                dtype=np.float64,
            )
        return np.vstack(parts)

    def _mix_exploration_starts(
        self,
        starts,
        start_scores,
        *,
        mix: float,
        seed: int,
    ):
        """Replace a fraction of non-best starts with diverse Sobol points."""
        starts = np.asarray(starts, dtype=np.float64)
        start_scores = np.asarray(
            start_scores,
            dtype=np.float64,
        )
        if len(starts) <= 1 or mix <= 0.0:
            return starts, start_scores

        n_replace = int(
            round(mix * (len(starts) - 1))
        )
        n_replace = max(
            0,
            min(n_replace, len(starts) - 1),
        )
        if n_replace == 0:
            return starts, start_scores

        self.fit_diagnostics[
            "adaptive_exploration_mix_uses"
        ] += 1

        explorers = sobol_points(
            n_replace,
            self.space.dim,
            int(seed),
        )
        out_x = starts.copy()
        out_s = start_scores.copy()
        # Keep best start; replace from the end.
        out_x[-n_replace:] = explorers
        out_s[-n_replace:] = -np.inf
        return out_x, out_s

    def _best_rescue_by_acquisition(
        self,
        cpu_acq,
        candidates,
    ):
        best = None
        for x in candidates:
            x = np.asarray(x, dtype=np.float64).reshape(-1)
            if self._is_duplicate(x):
                continue
            value = self._acq_value_cpu(cpu_acq, x)
            if not np.isfinite(value):
                continue
            if best is None or value > best.acquisition_value:
                best = CandidateSource(
                    name="adaptive_rescue",
                    x01=np.clip(x, 0.0, 1.0),
                    acquisition_value=float(value),
                )
        return best

    def run(
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

        initial = sobol_points(
            int(initial_trials),
            self.space.dim,
            self.seed,
        )
        for p in initial:
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
            iter_t0 = time.perf_counter()

            diagnostics = compute_landscape_diagnostics(
                x01_history=self.x01_history,
                scores=self._scores_array(),
                best_score=float(best),
                evaluations_since_improve=int(
                    stagnation
                ),
                total_budget=total_budget,
                dimension=self.space.dim,
                weight_rbf=self.stacking_weight_rbf,
                weight_history=self.weight_history,
            )
            decision = decide_adaptive_policy(
                diagnostics,
                base_stagnation_trigger=int(
                    stagnation_trigger
                ),
            )
            knobs = apply_decision_to_knobs(
                decision,
                **base_knobs,
            )
            self.fit_diagnostics[
                "adaptive_policy_updates"
            ] += 1

            if record_diagnostics:
                self.diagnostic_history.append({
                    "step": step,
                    **diagnostics.as_dict(),
                })
                self.policy_history.append({
                    "step": step,
                    **decision.as_dict(),
                    **{
                        k: knobs[k]
                        for k in (
                            "screen_pool",
                            "diversity_radius",
                            "refinement_top_k",
                            "refinement_maxiter",
                            "exploration_mix",
                            "enable_rescue",
                            "reason",
                        )
                    },
                })

            pulse = (
                stagnation
                >= int(stagnation_trigger)
                and (
                    stagnation
                    - int(stagnation_trigger)
                )
                % max(1, int(pulse_interval))
                == 0
            )
            severe_pulse = (
                stagnation
                >= int(severe_stagnation_trigger)
                and not severe_used
            )
            if severe_pulse:
                severe_used = True
                self.fit_diagnostics[
                    "severe_stagnation_pulses"
                ] += 1
            if pulse or severe_pulse:
                self.fit_diagnostics[
                    "stagnation_pulses"
                ] += 1

            optimize_models = (
                step == 0
                or int(refit_interval) <= 1
                or step % int(refit_interval) == 0
                or pulse
                or severe_pulse
                or knobs["enable_rescue"]
            )

            rbf_cpu, mat_cpu = self._fit_pair(
                optimize=optimize_models
            )
            if optimize_models:
                self._update_stacking_weight(
                    rbf_cpu,
                    mat_cpu,
                )

            cpu_acq, acquisition_mode = (
                self._build_stacked_acquisition(
                    rbf_cpu,
                    mat_cpu,
                )
            )

            if self.screen_device.type == "cpu":
                screen_acq = cpu_acq
            else:
                t0 = time.perf_counter()
                rbf_screen = self._clone_member_to_screen(
                    rbf_cpu,
                    "rbf",
                )
                mat_screen = self._clone_member_to_screen(
                    mat_cpu,
                    "matern25",
                )
                self.torch.cuda.synchronize()
                self.timings[
                    "screen_model_build_s"
                ] += time.perf_counter() - t0
                screen_acq, _ = (
                    self._build_stacked_acquisition(
                        rbf_screen,
                        mat_screen,
                    )
                )

            if severe_pulse:
                active_pool = int(
                    knobs["severe_screen_pool"]
                )
            elif pulse:
                active_pool = int(
                    knobs["pulse_screen_pool"]
                )
            else:
                active_pool = int(
                    knobs["screen_pool"]
                )

            t0 = time.perf_counter()
            pool = sobol_points(
                active_pool,
                self.space.dim,
                self.seed + 100_000 + step,
            )
            self.timings[
                "screen_pool_generation_s"
            ] += time.perf_counter() - t0

            scores = self._score_global_pool(
                acq=screen_acq,
                pool=pool,
                chunk_size=int(screen_chunk_size),
            )

            t0 = time.perf_counter()
            starts, start_scores = (
                self._select_informed_starts(
                    pool=pool,
                    scores=scores,
                    top_k=int(top_k),
                    diversity_radius=float(
                        knobs["diversity_radius"]
                    ),
                )
            )
            self.timings[
                "topk_selection_s"
            ] += time.perf_counter() - t0

            starts, start_scores = (
                self._mix_exploration_starts(
                    starts,
                    start_scores,
                    mix=float(
                        knobs["exploration_mix"]
                    ),
                    seed=self.seed + 700_000 + step,
                )
            )

            discrete = CandidateSource(
                name="adaptive_discrete",
                x01=starts[0].copy(),
                acquisition_value=float(
                    start_scores[0]
                ),
            )
            discrete.acquisition_value = (
                self._acq_value_cpu(
                    cpu_acq,
                    discrete.x01,
                )
            )

            refine_count = min(
                int(knobs["refinement_top_k"]),
                len(starts),
            )
            refined = self._refine_informed_starts(
                cpu_acq=cpu_acq,
                starts=starts[:refine_count],
                maxiter=int(
                    knobs["refinement_maxiter"]
                ),
                timeout_sec=float(
                    refinement_timeout_sec
                ),
                seed=self.seed + 900_000 + step,
            )

            chosen = discrete
            if refined is not None:
                refined.acquisition_value = (
                    self._acq_value_cpu(
                        cpu_acq,
                        refined.x01,
                    )
                )
                if (
                    not self._is_duplicate(
                        refined.x01
                    )
                    and refined.acquisition_value
                    > discrete.acquisition_value
                    + 1e-12
                ):
                    refined.name = "adaptive_refined"
                    chosen = refined
                    self.fit_diagnostics[
                        "refinement_selected"
                    ] += 1
                else:
                    self.fit_diagnostics[
                        "discrete_selected"
                    ] += 1
            else:
                self.fit_diagnostics[
                    "discrete_selected"
                ] += 1

            if knobs["enable_rescue"]:
                self.fit_diagnostics[
                    "adaptive_rescue_triggers"
                ] += 1
                rescue_X = self._build_rescue_candidates(
                    n_global=max(
                        32,
                        8 * self.space.dim,
                    ),
                    n_local=max(
                        16,
                        4 * self.space.dim,
                    ),
                    seed=self.seed + 300_000 + step,
                )
                rescue = self._best_rescue_by_acquisition(
                    cpu_acq,
                    rescue_X,
                )
                if (
                    rescue is not None
                    and rescue.acquisition_value
                    > chosen.acquisition_value
                    + 1e-12
                ):
                    chosen = rescue
                    self.fit_diagnostics[
                        "adaptive_rescue_selected"
                    ] += 1

            if self._is_duplicate(chosen.x01):
                self.fit_diagnostics[
                    "duplicate_candidates"
                ] += 1
                replacement = None
                for x, value in zip(
                    starts[1:],
                    start_scores[1:],
                ):
                    if not self._is_duplicate(x):
                        replacement = CandidateSource(
                            name="adaptive_duplicate_recovery",
                            x01=x.copy(),
                            acquisition_value=float(
                                value
                            ),
                        )
                        break
                if replacement is None:
                    raise RuntimeError(
                        "All adaptive top candidates duplicate history."
                    )
                chosen = replacement
                self.fit_diagnostics[
                    "duplicate_recoveries"
                ] += 1

            previous_best = best
            result = self._evaluate01(chosen.x01)
            best = self._best_feasible_score()
            improved = best > previous_best + 1e-10
            if improved:
                stagnation = 0
                severe_used = False
            else:
                stagnation += 1

            iteration_s = (
                time.perf_counter() - iter_t0
            )
            self.timings[
                "total_iteration_s"
            ] += iteration_s

            self.events.append({
                "step": step,
                "event": "iteration",
                "engine": self.ENGINE_ID,
                "acquisition": acquisition_mode,
                "source": chosen.name,
                "pulse": bool(pulse),
                "severe_pulse": bool(severe_pulse),
                "pool": active_pool,
                "policy_reason": knobs["reason"],
                "rescue": bool(
                    knobs["enable_rescue"]
                ),
                "weight_rbf": float(
                    self.stacking_weight_rbf
                ),
                "score": float(result.score),
                "best": float(best),
                "stagnation": int(stagnation),
                "stagnation_score": float(
                    diagnostics.stagnation_score
                ),
                "model_reliability": float(
                    diagnostics.model_reliability
                ),
                "iteration_s": float(iteration_s),
            })

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or knobs["enable_rescue"]
                or step == total_steps - 1
            ):
                print(
                    f"[{self.ENGINE_ID} {step+1:02d}/{total_steps}] "
                    f"src={chosen.name:<24s} "
                    f"reason={knobs['reason']:<32s} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d}"
                )

            if self.screen_device.type == "cuda":
                del screen_acq
                if "rbf_screen" in locals():
                    del rbf_screen
                    del mat_screen

        feasible = [
            r for r in self.history if r.feasible
        ] or list(self.history)
        feasible.sort(
            key=lambda r: r.score,
            reverse=True,
        )

        gpu_memory = {}
        if self.screen_device.type == "cuda":
            gpu_memory = {
                "allocated_mb":
                    self.torch.cuda.memory_allocated(
                        self.screen_device
                    ) / 1024**2,
                "reserved_mb":
                    self.torch.cuda.memory_reserved(
                        self.screen_device
                    ) / 1024**2,
            }

        return {
            "engine_id": self.ENGINE_ID,
            "trials_run": len(self.history),
            "best": feasible[0],
            "top": feasible[:8],
            "events": list(self.events),
            "timings": dict(self.timings),
            "fit_diagnostics": dict(
                self.fit_diagnostics
            ),
            "weight_history": list(
                self.weight_history
            ),
            "diagnostic_history": list(
                self.diagnostic_history
            ),
            "policy_history": list(
                self.policy_history
            ),
            "final_weight_rbf": float(
                self.stacking_weight_rbf
            ),
            "final_weight_matern": float(
                1.0 - self.stacking_weight_rbf
            ),
            "fit_device": "cpu",
            "screen_device": str(
                self.screen_device
            ),
            "gpu_memory": gpu_memory,
        }
