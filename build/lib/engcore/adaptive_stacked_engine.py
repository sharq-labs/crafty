"""
Adaptive Stacked GP-BO engine — V0.3.4 logic hardening.

Architecture:
  observations
     → baseline hyperparameter refit schedule
     → fresh stacking-weight update on current observations
     → diagnostics / proposer policy
     → identity_proposal  (baseline search knobs, current observations)
     → adaptive_proposal  (optional; same models, adapted search knobs)
     → robust arbiter
     → ONE objective evaluation of the chosen proposal

identity_proposal means what the baseline search logic would propose from the
CURRENT adaptive-run observations. It is not a full counterfactual baseline
trajectory after prior adaptive deviations.
"""

from __future__ import annotations

import time

import numpy as np

from .adaptive_policy import (
    AdaptivePolicyController,
    apply_decision_to_knobs,
    identity_knobs,
)
from .candidate_arbiter import ProposalView, arbitrate_proposals
from .landscape_diagnostics import compute_landscape_diagnostics
from .logei_engine import CandidateSource
from .sampling import sobol_points
from .stacked_engine import StackedGPBOEngine


class AdaptiveStackedGPBOEngine(StackedGPBOEngine):
    ENGINE_ID = "adaptive_stacked_v034"

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
        self.record_diagnostics = bool(record_diagnostics)
        self.diagnostic_history = []
        self.policy_history = []
        self.arbiter_history = []
        self.policy_controller = AdaptivePolicyController()
        self.fit_diagnostics.update({
            "adaptive_policy_updates": 0,
            "adaptive_proposals_generated": 0,
            "adaptive_proposals_accepted": 0,
            "adaptive_proposals_rejected": 0,
            "adaptive_rescue_search_attempts": 0,
            "adaptive_rescue_proposals": 0,
            "adaptive_rescue_accepted": 0,
            "adaptive_forced_refits": 0,
            "identity_proposals": 0,
        })

    def _scores_array(self):
        return np.asarray(
            [float(r.score) for r in self.history],
            dtype=np.float64,
        )

    def _incumbent_x01(self):
        if not self.history:
            return np.full(self.space.dim, 0.5, dtype=np.float64)
        scores = self._scores_array()
        idx = int(np.argmax(scores))
        return np.asarray(
            self.x01_history[idx], dtype=np.float64
        ).copy()

    def _build_rescue_candidates(
        self,
        *,
        n_global: int,
        n_local: int,
        seed: int,
        sigma: float = 0.12,
    ):
        parts = []
        if n_global > 0:
            parts.append(
                sobol_points(int(n_global), self.space.dim, int(seed))
            )
        if n_local > 0:
            rng = np.random.default_rng(int(seed) + 17)
            center = self._incumbent_x01()
            local = center[None, :] + sigma * rng.standard_normal(
                (int(n_local), self.space.dim)
            )
            parts.append(np.clip(local, 0.0, 1.0))
        if not parts:
            return np.zeros((0, self.space.dim), dtype=np.float64)
        return np.vstack(parts)

    def _mix_exploration_starts(
        self, starts, start_scores, *, mix: float, seed: int
    ):
        starts = np.asarray(starts, dtype=np.float64)
        start_scores = np.asarray(start_scores, dtype=np.float64)
        if len(starts) <= 1 or mix <= 0.0:
            return starts, start_scores
        n_replace = int(round(mix * (len(starts) - 1)))
        n_replace = max(0, min(n_replace, len(starts) - 1))
        if n_replace == 0:
            return starts, start_scores
        explorers = sobol_points(n_replace, self.space.dim, int(seed))
        out_x = starts.copy()
        out_s = start_scores.copy()
        out_x[-n_replace:] = explorers
        out_s[-n_replace:] = -np.inf
        return out_x, out_s

    def _best_rescue_by_acquisition(self, cpu_acq, candidates):
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

    def _torch_rng_snapshot(self):
        torch = self.torch
        snap = {"cpu": torch.random.get_rng_state()}
        if torch.cuda.is_available():
            try:
                snap["cuda"] = torch.cuda.get_rng_state_all()
            except Exception:
                snap["cuda"] = None
        else:
            snap["cuda"] = None
        return snap

    def _torch_rng_restore(self, snap):
        torch = self.torch
        torch.random.set_rng_state(snap["cpu"])
        if snap.get("cuda") is not None:
            try:
                torch.cuda.set_rng_state_all(snap["cuda"])
            except Exception:
                pass

    def _score_proposal_views(
        self, x01, *, mixture_acq, rbf_acq, mat_acq
    ):
        return {
            "mixture_acq": float(
                self._acq_value_cpu(mixture_acq, x01)
            ),
            "rbf_acq": float(self._acq_value_cpu(rbf_acq, x01)),
            "matern_acq": float(
                self._acq_value_cpu(mat_acq, x01)
            ),
        }

    def _generate_search_proposal(
        self,
        *,
        knobs: dict,
        screen_acq,
        cpu_acq,
        rbf_acq,
        mat_acq,
        step: int,
        top_k: int,
        screen_chunk_size: int,
        refinement_timeout_sec: float,
        pulse: bool,
        severe_pulse: bool,
        tag: str,
        enable_rescue: bool,
    ) -> ProposalView:
        if severe_pulse:
            active_pool = int(knobs["severe_screen_pool"])
        elif pulse:
            active_pool = int(knobs["pulse_screen_pool"])
        else:
            active_pool = int(knobs["screen_pool"])

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
            diversity_radius=float(knobs["diversity_radius"]),
        )
        starts, start_scores = self._mix_exploration_starts(
            starts,
            start_scores,
            mix=float(knobs["exploration_mix"]),
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
            int(knobs["refinement_top_k"]), len(starts)
        )
        refined = self._refine_informed_starts(
            cpu_acq=cpu_acq,
            starts=starts[:refine_count],
            maxiter=int(knobs["refinement_maxiter"]),
            timeout_sec=float(refinement_timeout_sec),
            seed=self.seed + 900_000 + step,
        )

        chosen = discrete
        source = discrete.name
        is_rescue = False
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

        if enable_rescue:
            self.fit_diagnostics[
                "adaptive_rescue_search_attempts"
            ] += 1
            rescue_X = self._build_rescue_candidates(
                n_global=max(32, 8 * self.space.dim),
                n_local=max(16, 4 * self.space.dim),
                seed=self.seed + 300_000 + step,
            )
            rescue = self._best_rescue_by_acquisition(cpu_acq, rescue_X)
            if (
                rescue is not None
                and rescue.acquisition_value
                > chosen.acquisition_value + 1e-12
            ):
                chosen = rescue
                source = "adaptive_rescue"
                is_rescue = True
                self.fit_diagnostics[
                    "adaptive_rescue_proposals"
                ] += 1

        if self._is_duplicate(chosen.x01):
            self.fit_diagnostics["duplicate_candidates"] += 1
            replacement = None
            for x, value in zip(starts[1:], start_scores[1:]):
                if not self._is_duplicate(x):
                    replacement = CandidateSource(
                        name=f"{tag}_dup_recovery",
                        x01=x.copy(),
                        acquisition_value=float(value),
                    )
                    break
            if replacement is None:
                raise RuntimeError(
                    "All adaptive proposal candidates duplicate history"
                )
            chosen = replacement
            source = chosen.name
            is_rescue = False
            self.fit_diagnostics["duplicate_recoveries"] += 1

        acq_scores = self._score_proposal_views(
            chosen.x01,
            mixture_acq=cpu_acq,
            rbf_acq=rbf_acq,
            mat_acq=mat_acq,
        )
        return ProposalView(
            x01=np.asarray(chosen.x01, dtype=np.float64).copy(),
            source=str(source),
            mixture_acq=acq_scores["mixture_acq"],
            rbf_acq=acq_scores["rbf_acq"],
            matern_acq=acq_scores["matern_acq"],
            is_rescue=bool(is_rescue),
        )

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
        if self.history or self.x01_history or self.margin_history:
            raise RuntimeError(
                "Engine instances are single-use; create a new engine for "
                "each independent optimization run"
            )

        if record_diagnostics is None:
            record_diagnostics = self.record_diagnostics

        self.diagnostic_history = []
        self.policy_history = []
        self.arbiter_history = []
        self.policy_controller.reset()

        initial = sobol_points(
            int(initial_trials), self.space.dim, self.seed
        )
        for p in initial:
            self._evaluate01(p)

        total_steps = int(smart_trials)
        total_budget = int(initial_trials) + total_steps
        best = self._best_feasible_score()
        stagnation = 0
        severe_used = False

        base_knob_args = dict(
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
                self.fit_diagnostics[
                    "severe_stagnation_pulses"
                ] += 1
            if pulse or severe_pulse:
                self.fit_diagnostics["stagnation_pulses"] += 1

            optimize_models = (
                step == 0
                or int(refit_interval) <= 1
                or step % int(refit_interval) == 0
                or pulse
                or severe_pulse
            )

            rbf_cpu, mat_cpu = self._fit_pair(
                optimize=optimize_models
            )

            # Stacking weights depend on the observation set as well as fitted
            # hyperparameters, so refresh them on every newly-built posterior.
            self._update_stacking_weight(rbf_cpu, mat_cpu)

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
            decision = self.policy_controller.update(
                diagnostics,
                base_stagnation_trigger=int(stagnation_trigger),
                step=step,
            )
            adapt_knobs = apply_decision_to_knobs(
                decision, **base_knob_args
            )
            id_knobs = identity_knobs(**base_knob_args)
            self.fit_diagnostics["adaptive_policy_updates"] += 1

            if record_diagnostics:
                self.diagnostic_history.append({
                    "step": step,
                    "evaluation": int(len(self.history)),
                    **diagnostics.as_dict(),
                })
                self.policy_history.append({
                    "step": step,
                    "evaluation": int(len(self.history)),
                    **decision.as_dict(),
                })

            rbf_acq, rbf_mode = self._build_acquisition(rbf_cpu)
            mat_acq, mat_mode = self._build_acquisition(mat_cpu)
            if rbf_mode != mat_mode:
                raise RuntimeError(
                    "Member acquisition modes disagree: "
                    f"{rbf_mode} vs {mat_mode}"
                )
            cpu_acq, acquisition_mode = self._build_stacked_acquisition(
                rbf_cpu, mat_cpu
            )

            if self.screen_device.type == "cpu":
                screen_acq = cpu_acq
            else:
                t0 = time.perf_counter()
                rbf_screen = self._clone_member_to_screen(
                    rbf_cpu, "rbf"
                )
                mat_screen = self._clone_member_to_screen(
                    mat_cpu, "matern25"
                )
                self.torch.cuda.synchronize()
                self.timings[
                    "screen_model_build_s"
                ] += time.perf_counter() - t0
                screen_acq, _ = self._build_stacked_acquisition(
                    rbf_screen, mat_screen
                )

            identity = self._generate_search_proposal(
                knobs=id_knobs,
                screen_acq=screen_acq,
                cpu_acq=cpu_acq,
                rbf_acq=rbf_acq,
                mat_acq=mat_acq,
                step=step,
                top_k=int(top_k),
                screen_chunk_size=int(screen_chunk_size),
                refinement_timeout_sec=float(refinement_timeout_sec),
                pulse=pulse,
                severe_pulse=severe_pulse,
                tag="identity",
                enable_rescue=False,
            )
            self.fit_diagnostics["identity_proposals"] += 1

            adaptive = None
            if decision.enable_adaptive_proposal:
                rng_snap = self._torch_rng_snapshot()
                try:
                    adaptive = self._generate_search_proposal(
                        knobs=adapt_knobs,
                        screen_acq=screen_acq,
                        cpu_acq=cpu_acq,
                        rbf_acq=rbf_acq,
                        mat_acq=mat_acq,
                        step=step,
                        top_k=int(top_k),
                        screen_chunk_size=int(screen_chunk_size),
                        refinement_timeout_sec=float(
                            refinement_timeout_sec
                        ),
                        pulse=pulse,
                        severe_pulse=severe_pulse,
                        tag="adaptive",
                        enable_rescue=bool(
                            decision.enable_rescue_proposal
                        ),
                    )
                finally:
                    self._torch_rng_restore(rng_snap)
                self.fit_diagnostics[
                    "adaptive_proposals_generated"
                ] += 1

            chosen_view, arb = arbitrate_proposals(
                identity,
                adaptive,
                adaptive_enabled=bool(
                    decision.enable_adaptive_proposal
                ),
            )
            if arb.choose_adaptive:
                self.fit_diagnostics[
                    "adaptive_proposals_accepted"
                ] += 1
                if chosen_view.is_rescue:
                    self.fit_diagnostics[
                        "adaptive_rescue_accepted"
                    ] += 1
            elif adaptive is not None:
                self.fit_diagnostics[
                    "adaptive_proposals_rejected"
                ] += 1

            if record_diagnostics:
                self.arbiter_history.append({
                    "step": step,
                    "evaluation": int(len(self.history)),
                    "identity_x01": identity.x01.tolist(),
                    "adaptive_x01": (
                        None if adaptive is None else adaptive.x01.tolist()
                    ),
                    "executed_x01": chosen_view.x01.tolist(),
                    "identity_source": identity.source,
                    "adaptive_source": (
                        None if adaptive is None else adaptive.source
                    ),
                    "executed_source": chosen_view.source,
                    "arbiter_decision": arb.choose_adaptive,
                    "arbiter_reason": arb.reason,
                    "identity_mixture_acq": identity.mixture_acq,
                    "adaptive_mixture_acq": (
                        None if adaptive is None else adaptive.mixture_acq
                    ),
                    "identity_rbf_acq": identity.rbf_acq,
                    "adaptive_rbf_acq": (
                        None if adaptive is None else adaptive.rbf_acq
                    ),
                    "identity_matern_acq": identity.matern_acq,
                    "adaptive_matern_acq": (
                        None if adaptive is None else adaptive.matern_acq
                    ),
                    "component_disagreement": arb.component_disagreement,
                    "evidence_score": float(decision.evidence_score),
                    "consecutive_evidence": int(
                        decision.consecutive_evidence
                    ),
                    "adaptation_enabled": bool(
                        decision.enable_adaptive_proposal
                    ),
                    "rescue_proposal_enabled": bool(
                        decision.enable_rescue_proposal
                    ),
                    "proposal_level": decision.proposal_level,
                })

            chosen = CandidateSource(
                name=chosen_view.source,
                x01=chosen_view.x01.copy(),
                acquisition_value=float(chosen_view.mixture_acq),
            )

            if "refined" in chosen.name:
                self.fit_diagnostics["refinement_selected"] += 1
            else:
                self.fit_diagnostics["discrete_selected"] += 1

            previous_best = best
            result = self._evaluate01(chosen.x01)
            best = self._best_feasible_score()
            improved = best > previous_best + 1e-10
            if improved:
                stagnation = 0
                severe_used = False
            else:
                stagnation += 1

            iteration_s = time.perf_counter() - iter_t0
            self.timings["total_iteration_s"] += iteration_s

            self.events.append({
                "step": step,
                "event": "iteration",
                "engine": self.ENGINE_ID,
                "acquisition": acquisition_mode,
                "source": chosen.name,
                "pulse": bool(pulse),
                "severe_pulse": bool(severe_pulse),
                "arbiter_reason": arb.reason,
                "choose_adaptive": bool(arb.choose_adaptive),
                "evidence_score": float(decision.evidence_score),
                "proposal_level": decision.proposal_level,
                "weight_rbf": float(self.stacking_weight_rbf),
                "score": float(result.score),
                "best": float(best),
                "stagnation": int(stagnation),
                "iteration_s": float(iteration_s),
            })

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or arb.choose_adaptive
                or step == total_steps - 1
            ):
                print(
                    f"[{self.ENGINE_ID} {step+1:02d}/{total_steps}] "
                    f"exec={arb.executed_source:<8s} "
                    f"arb={arb.reason:<28s} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d}"
                )

            if self.screen_device.type == "cuda":
                del screen_acq
                del rbf_screen
                del mat_screen

        feasible = [r for r in self.history if r.feasible]
        if not feasible:
            feasible = list(self.history)
        feasible.sort(key=lambda r: r.score, reverse=True)

        gpu_memory = {}
        if self.screen_device.type == "cuda":
            gpu_memory = {
                "allocated_mb": self.torch.cuda.memory_allocated()
                / (1024 ** 2),
                "reserved_mb": self.torch.cuda.memory_reserved()
                / (1024 ** 2),
            }

        return {
            "best": feasible[0],
            "top": feasible[:5],
            "history": self.history,
            "events": self.events,
            "trials_run": len(self.history),
            "timings": self.timings,
            "fit_diagnostics": self.fit_diagnostics,
            "diagnostic_history": self.diagnostic_history,
            "policy_history": self.policy_history,
            "arbiter_history": self.arbiter_history,
            "weight_history": self.weight_history,
            "final_weight_rbf": float(self.stacking_weight_rbf),
            "final_weight_matern": float(
                1.0 - self.stacking_weight_rbf
            ),
            "fit_device": "cpu",
            "screen_device": str(self.screen_device),
            "gpu_memory": gpu_memory,
            "engine_id": self.ENGINE_ID,
        }
