from __future__ import annotations

import math
import time

import numpy as np

from .hybrid_engine import HybridLogEIEngine
from .logei_engine import CandidateSource
from .sampling import sobol_points


class AdaptiveHybridLogEIEngine(HybridLogEIEngine):
    """
    V0.2.9.1 Adaptive Hybrid.

    It fixes two behaviors observed in V0.2.9:
    1) refinement won 68/68 selections, even when it hurt early performance.
    2) narrow_optimum remained weak in both discrete and hybrid modes.

    Strategy:
    - global GPU screening remains the champion mechanism
    - refinement is a challenger, not an automatic winner
    - early BO phase is forced-discrete
    - after warmup, discrete is still forced periodically
    - refinement must clear a LogEI gain threshold to be selected
    - long stagnation can force ONE uncertainty-search experiment
    - no weighted acquisition portfolio
    """

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        screen_device="auto",
        standardized_noise_var=1e-5,
        duplicate_tol=1e-5,
        noise_mode="learned",
        kernel_name="rbf",
    ):
        # HybridLogEIEngine currently fixes GP device to CPU.
        super().__init__(
            design_space=design_space,
            evaluator=evaluator,
            seed=seed,
            screen_device=screen_device,
            standardized_noise_var=standardized_noise_var,
            duplicate_tol=duplicate_tol,
        )

        # Base constructor came from the older signature, so explicitly set the
        # new GP ablation controls inherited from LogEIGlobalLocalEngine.
        self.noise_mode = str(noise_mode).lower()
        if self.noise_mode not in {"fixed", "learned"}:
            raise ValueError("noise_mode must be fixed or learned")

        self.kernel_name = str(kernel_name).lower()
        if self.kernel_name not in {"rbf", "matern25"}:
            raise ValueError("kernel_name must be rbf or matern25")

        self.timings.update({
            "uncertainty_scoring_s": 0.0,
        })

        self.fit_diagnostics.update({
            "forced_discrete_selections": 0,
            "gated_refinement_rejections": 0,
            "uncertainty_exploration_selections": 0,
        })

    def _clone_fitted_model_to_screen_device(self, cpu_model):
        """
        Rebuild the exact same GP structure on the screening device, then load
        the already-fitted CPU state.
        """
        if self.screen_device.type == "cpu":
            return cpu_model

        t0 = time.perf_counter()

        X, Y, Yvar = self._training_tensors_on(
            self.screen_device
        )

        screen_model = self._make_model(
            X=X,
            Y=Y,
            Yvar=Yvar,
        )

        screen_model.load_state_dict(
            cpu_model.state_dict(),
            strict=True,
        )
        screen_model.eval()
        screen_model.likelihood.eval()

        self.torch.cuda.synchronize()
        self.timings["screen_model_build_s"] += (
            time.perf_counter() - t0
        )

        return screen_model

    def _max_uncertainty_candidate(
        self,
        model,
        pool,
        chunk_size=2048,
    ):
        """
        Rare model-uncertainty exploration.

        This is intentionally NOT mixed into LogEI with a custom weight.
        It is only used as a forced experiment after prolonged stagnation.
        """
        import gpytorch

        torch = self.torch
        t0 = time.perf_counter()

        pool = np.asarray(pool, dtype=np.float64)
        history = np.asarray(
            self.x01_history,
            dtype=np.float64,
        )

        best_std = float("-inf")
        best_x = None

        for start in range(
            0,
            len(pool),
            int(chunk_size),
        ):
            block_np = pool[
                start:start + int(chunk_size)
            ]

            distances = np.linalg.norm(
                block_np[:, None, :]
                - history[None, :, :],
                axis=2,
            )
            keep = (
                np.min(distances, axis=1)
                > self.duplicate_tol
            )

            block_np = block_np[keep]
            if len(block_np) == 0:
                continue

            X = torch.as_tensor(
                block_np,
                dtype=self.dtype,
                device=self.screen_device,
            )

            with (
                torch.no_grad(),
                gpytorch.settings.fast_pred_var(),
            ):
                posterior = model.posterior(X)

                # Objective output is the first output if constraints exist.
                variance = posterior.variance

                if variance.ndim > 1:
                    variance = variance[..., 0]

                std = torch.sqrt(
                    variance.clamp_min(1e-14)
                ).reshape(-1)

            idx = int(torch.argmax(std).item())
            value = float(
                std[idx].detach().cpu().item()
            )

            if value > best_std:
                best_std = value
                best_x = block_np[idx].copy()

        if self.screen_device.type == "cuda":
            torch.cuda.synchronize()

        self.timings["uncertainty_scoring_s"] += (
            time.perf_counter() - t0
        )

        if best_x is None:
            return None

        return CandidateSource(
            name="forced_uncertainty",
            x01=best_x,
            acquisition_value=float("-inf"),
        )

    def run(
        self,
        initial_trials=12,
        smart_trials=68,
        refit_interval=4,
        screen_pool=100_000,
        screen_chunk_size=2048,
        top_k=12,
        refinement_top_k=8,
        diversity_radius=0.035,
        refinement_maxiter=60,
        refinement_timeout_sec=3.0,
        refinement_warmup=12,
        forced_discrete_interval=3,
        refinement_logei_gain=0.25,
        stagnation_trigger=6,
        pulse_interval=6,
        pulse_screen_pool=250_000,
        pulse_top_k=20,
        pulse_refinement_top_k=12,
        pulse_refinement_maxiter=100,
        pulse_refinement_timeout_sec=5.0,
        uncertainty_trigger=14,
        uncertainty_interval=10,
        verbose=False,
    ):
        initial = sobol_points(
            int(initial_trials),
            self.space.dim,
            self.seed,
        )

        for p in initial:
            self._evaluate01(p)

        total_steps = int(smart_trials)
        best = self._best_feasible_score()
        stagnation = 0

        for step in range(total_steps):
            iter_t0 = time.perf_counter()

            pulse = (
                stagnation >= int(stagnation_trigger)
                and (
                    stagnation - int(stagnation_trigger)
                ) % max(1, int(pulse_interval)) == 0
            )

            if pulse:
                self.fit_diagnostics[
                    "stagnation_pulses"
                ] += 1

            force_uncertainty = (
                stagnation >= int(uncertainty_trigger)
                and (
                    stagnation - int(uncertainty_trigger)
                ) % max(1, int(uncertainty_interval)) == 0
            )

            optimize_model = (
                step == 0
                or int(refit_interval) <= 1
                or step % int(refit_interval) == 0
                or pulse
                or force_uncertainty
            )

            cpu_model = self._fit_model(
                optimize=optimize_model
            )
            cpu_acq, acquisition_mode = (
                self._build_acquisition(
                    cpu_model
                )
            )

            screen_model = (
                self._clone_fitted_model_to_screen_device(
                    cpu_model
                )
            )

            if screen_model is cpu_model:
                screen_acq = cpu_acq
            else:
                screen_acq, _ = (
                    self._build_acquisition(
                        screen_model
                    )
                )

            active_pool = (
                int(pulse_screen_pool)
                if pulse
                else int(screen_pool)
            )
            active_top_k = (
                int(pulse_top_k)
                if pulse
                else int(top_k)
            )
            active_refine_k = (
                int(pulse_refinement_top_k)
                if pulse
                else int(refinement_top_k)
            )
            active_refine_maxiter = (
                int(pulse_refinement_maxiter)
                if pulse
                else int(refinement_maxiter)
            )
            active_refine_timeout = (
                float(pulse_refinement_timeout_sec)
                if pulse
                else float(refinement_timeout_sec)
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
                    top_k=active_top_k,
                    diversity_radius=float(
                        diversity_radius
                    ),
                )
            )
            self.timings["topk_selection_s"] += (
                time.perf_counter() - t0
            )

            discrete = CandidateSource(
                name=(
                    "gpu_discrete_pulse"
                    if pulse
                    else "gpu_discrete"
                ),
                x01=starts[0].copy(),
                acquisition_value=float(
                    start_scores[0]
                ),
            )

            # Compare final candidates on the CPU model.
            t0 = time.perf_counter()
            discrete.acquisition_value = (
                self._acq_value_cpu(
                    cpu_acq,
                    discrete.x01,
                )
            )
            self.timings[
                "final_acq_compare_s"
            ] += time.perf_counter() - t0

            chosen = discrete
            source_reason = "discrete_default"
            refined = None
            refined_gain = float("-inf")

            # Rare, forced uncertainty point after long stagnation.
            if force_uncertainty:
                uncertainty_candidate = (
                    self._max_uncertainty_candidate(
                        model=screen_model,
                        pool=pool,
                        chunk_size=int(
                            screen_chunk_size
                        ),
                    )
                )

                if (
                    uncertainty_candidate is not None
                    and not self._is_duplicate(
                        uncertainty_candidate.x01
                    )
                ):
                    chosen = uncertainty_candidate
                    source_reason = "long_stagnation_uncertainty"
                    self.fit_diagnostics[
                        "uncertainty_exploration_selections"
                    ] += 1

            else:
                # Refinement remains a challenger.
                refine_count = min(
                    active_refine_k,
                    len(starts),
                )

                refined = self._refine_informed_starts(
                    cpu_acq=cpu_acq,
                    starts=starts[:refine_count],
                    maxiter=active_refine_maxiter,
                    timeout_sec=active_refine_timeout,
                    seed=(
                        self.seed
                        + 900_000
                        + step
                    ),
                )

                if refined is not None:
                    t0 = time.perf_counter()
                    refined.acquisition_value = (
                        self._acq_value_cpu(
                            cpu_acq,
                            refined.x01,
                        )
                    )
                    self.timings[
                        "final_acq_compare_s"
                    ] += time.perf_counter() - t0

                    refined_gain = (
                        refined.acquisition_value
                        - discrete.acquisition_value
                    )

                early_phase = (
                    step < int(refinement_warmup)
                )

                periodic_discrete = (
                    int(forced_discrete_interval) > 0
                    and (
                        (step + 1)
                        % int(forced_discrete_interval)
                        == 0
                    )
                )

                if early_phase or periodic_discrete:
                    chosen = discrete
                    source_reason = (
                        "early_discrete"
                        if early_phase
                        else "periodic_discrete"
                    )
                    self.fit_diagnostics[
                        "forced_discrete_selections"
                    ] += 1

                elif (
                    refined is not None
                    and not self._is_duplicate(
                        refined.x01
                    )
                    and refined_gain
                    >= float(refinement_logei_gain)
                ):
                    chosen = refined
                    source_reason = "refinement_gate_pass"
                    self.fit_diagnostics[
                        "refinement_selected"
                    ] += 1

                else:
                    chosen = discrete
                    source_reason = "refinement_gate_reject"
                    self.fit_diagnostics[
                        "discrete_selected"
                    ] += 1

                    if refined is not None:
                        self.fit_diagnostics[
                            "gated_refinement_rejections"
                        ] += 1

            # Final duplicate safety.
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
                            name="screen_duplicate_recovery",
                            x01=x.copy(),
                            acquisition_value=float(value),
                        )
                        break

                if replacement is None:
                    raise RuntimeError(
                        "All globally screened top candidates duplicate history."
                    )

                chosen = replacement
                source_reason = "duplicate_recovery"
                self.fit_diagnostics[
                    "duplicate_recoveries"
                ] += 1

            previous_best = best
            result = self._evaluate01(
                chosen.x01
            )
            best = self._best_feasible_score()

            if best > previous_best + 1e-10:
                stagnation = 0
            else:
                stagnation += 1

            iteration_s = (
                time.perf_counter()
                - iter_t0
            )
            self.timings[
                "total_iteration_s"
            ] += iteration_s

            self.events.append({
                "step": step,
                "event": "iteration",
                "acquisition": acquisition_mode,
                "source": chosen.name,
                "source_reason": source_reason,
                "pulse": bool(pulse),
                "force_uncertainty": bool(
                    force_uncertainty
                ),
                "pool": active_pool,
                "discrete_acq": float(
                    discrete.acquisition_value
                ),
                "refined_acq": (
                    None
                    if refined is None
                    else float(
                        refined.acquisition_value
                    )
                ),
                "refined_logei_gain": (
                    None
                    if refined is None
                    else float(refined_gain)
                ),
                "score": float(result.score),
                "feasible": bool(result.feasible),
                "best": float(best),
                "stagnation": int(stagnation),
                "iteration_s": float(
                    iteration_s
                ),
            })

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or pulse
                or force_uncertainty
                or step == total_steps - 1
            ):
                print(
                    f"[V0.2.9.1 {step+1:02d}/{total_steps}] "
                    f"acq={acquisition_mode:<6s} "
                    f"source={chosen.name:<20s} "
                    f"reason={source_reason:<25s} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d} "
                    f"pulse={str(pulse):<5s} "
                    f"iter={iteration_s:.2f}s"
                )

            if (
                self.screen_device.type == "cuda"
                and screen_model is not cpu_model
            ):
                del screen_acq
                del screen_model

        feasible = [
            r for r in self.history
            if r.feasible
        ]
        if not feasible:
            feasible = list(self.history)

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
                "max_allocated_mb":
                    self.torch.cuda.max_memory_allocated(
                        self.screen_device
                    ) / 1024**2,
                "max_reserved_mb":
                    self.torch.cuda.max_memory_reserved(
                        self.screen_device
                    ) / 1024**2,
            }

        return {
            "trials_run": len(self.history),
            "best": feasible[0],
            "top": feasible[:8],
            "events": list(self.events),
            "timings": dict(self.timings),
            "fit_diagnostics": dict(
                self.fit_diagnostics
            ),
            "fit_device": "cpu",
            "screen_device": str(
                self.screen_device
            ),
            "noise_mode": self.noise_mode,
            "kernel_name": self.kernel_name,
            "gpu_memory": gpu_memory,
        }
