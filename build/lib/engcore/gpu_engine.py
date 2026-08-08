from __future__ import annotations

import time
import numpy as np

from .models import ExperimentResult
from .sampling import sobol_points
from .gpu_surrogate import TorchBotorchSurrogate, describe_device


class GPUSmartExperimentEngine:
    def __init__(self, design_space, evaluator, seed=42, force_cpu=False):
        self.space = design_space
        self.evaluator = evaluator
        self.seed = seed
        self.force_cpu = force_cpu
        self.history = []

        self.timings = {
            "evaluation_s": 0.0,
            "model_total_s": 0.0,
            "model_optimized_s": 0.0,
            "model_warm_only_s": 0.0,
            "candidate_scoring_s": 0.0,
        }

        self.fit_diagnostics = {
            "optimized_fits": 0,
            "warm_only_fits": 0,
            "warm_starts_used": 0,
            "scipy_warnings": 0,
            "fallback_fits": 0,
            "fallback_steps": 0,
        }

        self.device_info = None

    def _evaluate01(self, x01):
        t0 = time.perf_counter()

        x = self.space.denormalize(x01)
        score, feasible, metadata = self.evaluator(x)

        self.timings["evaluation_s"] += time.perf_counter() - t0

        result = ExperimentResult(
            x=x.copy(),
            score=float(score),
            feasible=bool(feasible),
            metadata=metadata,
        )
        self.history.append(result)
        return result

    def run(
        self,
        initial_trials=24,
        smart_trials=56,
        candidate_pool=100_000,
        candidate_chunk_size=1024,
        patience=35,
        min_improvement=1e-6,
        refit_interval=4,
        fallback_steps=50,
    ):
        x0 = sobol_points(
            initial_trials, self.space.dim, self.seed
        )

        x_history = []
        y_history = []

        for p in x0:
            result = self._evaluate01(p)
            x_history.append(p)
            y_history.append(result.score)

        best = max(y_history)
        no_progress = 0

        surrogate = TorchBotorchSurrogate(
            self.space.dim,
            force_cpu=self.force_cpu,
        )
        self.device_info = describe_device(surrogate.device)
        surrogate.reset_peak_memory()

        for step in range(smart_trials):
            X = np.asarray(x_history, dtype=np.float64)
            y = np.asarray(y_history, dtype=np.float64)

            optimize = (
                step == 0
                or refit_interval <= 1
                or step % refit_interval == 0
            )

            t0 = time.perf_counter()
            fit_info = surrogate.fit(
                X,
                y,
                optimize=optimize,
                fallback_steps=fallback_steps,
            )
            surrogate.synchronize()
            fit_dt = time.perf_counter() - t0

            self.timings["model_total_s"] += fit_dt

            if optimize:
                self.timings["model_optimized_s"] += fit_dt
                self.fit_diagnostics["optimized_fits"] += 1
            else:
                self.timings["model_warm_only_s"] += fit_dt
                self.fit_diagnostics["warm_only_fits"] += 1

            if fit_info.used_warm_start:
                self.fit_diagnostics["warm_starts_used"] += 1
            if fit_info.scipy_warning:
                self.fit_diagnostics["scipy_warnings"] += 1
            if fit_info.fallback_used:
                self.fit_diagnostics["fallback_fits"] += 1
                self.fit_diagnostics["fallback_steps"] += (
                    fit_info.fallback_steps
                )

            pool = sobol_points(
                candidate_pool,
                self.space.dim,
                self.seed + 10_000 + step,
            )

            t0 = time.perf_counter()
            ei = surrogate.expected_improvement_scores(
                pool,
                best_y=best,
                chunk_size=candidate_chunk_size,
            )
            surrogate.synchronize()
            self.timings["candidate_scoring_s"] += (
                time.perf_counter() - t0
            )

            chosen = pool[int(np.argmax(ei))]
            result = self._evaluate01(chosen)

            x_history.append(chosen)
            y_history.append(result.score)

            improvement = result.score - best

            if improvement > min_improvement:
                best = result.score
                no_progress = 0
            else:
                no_progress += 1

            if no_progress >= patience:
                break

        feasible = [r for r in self.history if r.feasible]
        if not feasible:
            feasible = self.history

        feasible.sort(key=lambda r: r.score, reverse=True)

        return {
            "trials_run": len(self.history),
            "best": feasible[0],
            "top": feasible[:5],
            "device": self.device_info,
            "timings": dict(self.timings),
            "fit_diagnostics": dict(self.fit_diagnostics),
            "gpu_memory": surrogate.memory_stats(),
        }
