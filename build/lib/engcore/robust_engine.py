from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import qmc

from .models import ExperimentResult
from .sampling import sobol_points
from .gpu_surrogate import TorchBotorchSurrogate, describe_device


@dataclass
class RegionState:
    center: np.ndarray
    radius: float
    score: float
    successes: int = 0
    failures: int = 0


class RobustSmartExperimentEngine:
    """
    V0.2.6 Robust Autonomous Optimizer.

    Architecture:
    - global Sobol exploration
    - multiple local trust regions around diverse elite designs
    - adaptive exploration/exploitation portfolio
    - EI + UCB + uncertainty + novelty score fusion
    - stagnation recovery bursts
    - adaptive trust-region radius
    - dynamic candidate budget
    - GP warm start / periodic refit inherited from V0.2.4+
    """

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        force_cpu=False,
        n_regions=3,
    ):
        self.space = design_space
        self.evaluator = evaluator
        self.seed = int(seed)
        self.force_cpu = force_cpu
        self.n_regions = int(n_regions)

        self.history = []
        self.x01_history = []
        self.regions = []
        self.events = []

        self.timings = {
            "evaluation_s": 0.0,
            "model_s": 0.0,
            "candidate_generation_s": 0.0,
            "candidate_scoring_s": 0.0,
            "novelty_s": 0.0,
        }

        self.fit_diagnostics = {
            "optimized_fits": 0,
            "warm_only_fits": 0,
            "scipy_warnings": 0,
            "fallback_fits": 0,
        }

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
        self.x01_history.append(np.asarray(x01, dtype=float).copy())
        return result

    def _elite_indices(self, count):
        feasible = [
            (i, r.score)
            for i, r in enumerate(self.history)
            if r.feasible
        ]
        if not feasible:
            feasible = [(i, r.score) for i, r in enumerate(self.history)]

        feasible.sort(key=lambda t: t[1], reverse=True)

        chosen = []
        for idx, score in feasible:
            p = self.x01_history[idx]
            if not chosen:
                chosen.append((idx, score))
            else:
                existing = np.asarray([self.x01_history[i] for i, _ in chosen])
                dist = np.min(np.linalg.norm(existing - p[None, :], axis=1))
                if dist >= 0.12:
                    chosen.append((idx, score))
            if len(chosen) >= count:
                break

        if len(chosen) < count:
            for idx, score in feasible:
                if all(idx != c[0] for c in chosen):
                    chosen.append((idx, score))
                if len(chosen) >= count:
                    break

        return chosen

    def _refresh_regions(self, default_radius=0.22):
        elites = self._elite_indices(self.n_regions)
        old = self.regions
        new_regions = []

        for j, (idx, score) in enumerate(elites):
            center = self.x01_history[idx].copy()

            if j < len(old):
                radius = old[j].radius
            else:
                radius = default_radius

            new_regions.append(
                RegionState(
                    center=center,
                    radius=float(np.clip(radius, 0.06, 0.38)),
                    score=float(score),
                )
            )

        self.regions = new_regions

    def _local_points(self, center, radius, n, seed):
        # Sobol perturbations in [-1,1], then clip to [0,1].
        sampler = qmc.Sobol(d=self.space.dim, scramble=True, seed=seed)
        m = int(math.ceil(math.log2(max(2, n))))
        z = sampler.random_base2(m)[:n]
        delta = (z * 2.0 - 1.0) * radius
        return np.clip(center[None, :] + delta, 0.0, 1.0)

    def _dynamic_pool(self, base_pool, step, total_steps, stagnation):
        progress = step / max(1, total_steps - 1)

        if stagnation >= 8:
            return int(base_pool * 1.8)
        if progress < 0.25:
            return int(base_pool * 1.35)
        if progress < 0.70:
            return int(base_pool)
        return max(20_000, int(base_pool * 0.65))

    def _generate_candidates(self, pool_size, step, stagnation):
        t0 = time.perf_counter()

        if not self.regions:
            self._refresh_regions()

        # During stagnation, allocate more to global exploration.
        global_fraction = 0.58 if stagnation >= 8 else 0.34
        global_n = max(1024, int(pool_size * global_fraction))
        local_n_total = max(0, pool_size - global_n)

        global_points = sobol_points(
            global_n,
            self.space.dim,
            self.seed + 50_000 + step,
        )

        parts = [global_points]

        if self.regions and local_n_total > 0:
            per_region = max(128, local_n_total // len(self.regions))

            for j, region in enumerate(self.regions):
                radius = region.radius
                if stagnation >= 8:
                    radius = min(0.42, radius * 1.55)

                pts = self._local_points(
                    region.center,
                    radius,
                    per_region,
                    self.seed + 70_000 + 997*step + j,
                )
                parts.append(pts)

        pool = np.vstack(parts)

        if len(pool) > pool_size:
            pool = pool[:pool_size]

        self.timings["candidate_generation_s"] += time.perf_counter() - t0
        return pool

    @staticmethod
    def _normalize_metric(values):
        values = np.asarray(values, dtype=float)
        lo = np.quantile(values, 0.02)
        hi = np.quantile(values, 0.98)
        scale = max(1e-12, hi - lo)
        return np.clip((values - lo) / scale, 0.0, 1.0)

    def _novelty(self, pool):
        t0 = time.perf_counter()

        history = np.asarray(self.x01_history, dtype=float)

        # History is tiny (~tens/hundreds), pool can be large.
        # cdist remains manageable and fast in chunks.
        novelty = np.empty(len(pool), dtype=float)
        chunk = 25_000

        for start in range(0, len(pool), chunk):
            block = pool[start:start+chunk]
            d = cdist(block, history, metric="euclidean")
            novelty[start:start+len(block)] = np.min(d, axis=1)

        self.timings["novelty_s"] += time.perf_counter() - t0
        return novelty

    def _portfolio_scores(
        self,
        surrogate,
        pool,
        best_y,
        step,
        total_steps,
        stagnation,
        chunk_size,
    ):
        t0 = time.perf_counter()
        mean, std = surrogate.predict_mean_std(
            pool,
            chunk_size=chunk_size,
        )
        surrogate.synchronize()
        self.timings["candidate_scoring_s"] += time.perf_counter() - t0

        novelty = self._novelty(pool)

        # EI from analytic formula.
        improvement = mean - best_y - 0.01
        z = improvement / np.maximum(std, 1e-12)
        from scipy.special import ndtr
        pdf = np.exp(-0.5*z*z) / math.sqrt(2.0*math.pi)
        ei = improvement * ndtr(z) + std * pdf

        # UCB exploration coefficient decreases over time, but rises on stagnation.
        progress = step / max(1, total_steps - 1)
        beta = 2.8 - 1.5*progress
        if stagnation >= 8:
            beta += 2.0
        ucb = mean + beta * std

        ei_n = self._normalize_metric(ei)
        ucb_n = self._normalize_metric(ucb)
        unc_n = self._normalize_metric(std)
        nov_n = self._normalize_metric(novelty)

        # Adaptive portfolio.
        if stagnation >= 8:
            weights = (0.18, 0.25, 0.32, 0.25)  # EI, UCB, uncertainty, novelty
            mode = "recovery"
        elif progress < 0.30:
            weights = (0.30, 0.28, 0.22, 0.20)
            mode = "explore"
        elif progress < 0.75:
            weights = (0.46, 0.26, 0.15, 0.13)
            mode = "balanced"
        else:
            weights = (0.61, 0.20, 0.10, 0.09)
            mode = "exploit"

        score = (
            weights[0] * ei_n
            + weights[1] * ucb_n
            + weights[2] * unc_n
            + weights[3] * nov_n
        )

        # Hard novelty floor against near-duplicates.
        score = np.where(novelty < 0.008, -np.inf, score)

        return score, {
            "mode": mode,
            "weights": weights,
            "mean": mean,
            "std": std,
            "novelty": novelty,
            "ei": ei,
        }

    def _update_regions(self, chosen, result, previous_best):
        if not self.regions:
            self._refresh_regions()
            return

        centers = np.asarray([r.center for r in self.regions])
        j = int(np.argmin(np.linalg.norm(centers - chosen[None, :], axis=1)))
        region = self.regions[j]

        if result.feasible and result.score > previous_best + 1e-8:
            region.successes += 1
            region.failures = 0
            region.center = chosen.copy()
            region.score = result.score

            if region.successes >= 2:
                region.radius = min(0.38, region.radius * 1.18)
                region.successes = 0
        else:
            region.failures += 1
            region.successes = 0

            if region.failures >= 3:
                region.radius = max(0.06, region.radius * 0.72)
                region.failures = 0

    def run(
        self,
        initial_trials=24,
        smart_trials=56,
        candidate_pool=100_000,
        candidate_chunk_size=1024,
        refit_interval=4,
        patience=40,
        recovery_after=8,
    ):
        initial = sobol_points(
            initial_trials,
            self.space.dim,
            self.seed,
        )

        y_history = []

        for p in initial:
            result = self._evaluate01(p)
            y_history.append(result.score)

        best = max(
            r.score for r in self.history
            if r.feasible
        ) if any(r.feasible for r in self.history) else max(y_history)

        self._refresh_regions()

        surrogate = TorchBotorchSurrogate(
            self.space.dim,
            force_cpu=self.force_cpu,
        )
        device_info = describe_device(surrogate.device)
        surrogate.reset_peak_memory()

        stagnation = 0
        total_no_progress = 0

        for step in range(smart_trials):
            X = np.asarray(self.x01_history, dtype=np.float64)
            y = np.asarray([r.score for r in self.history], dtype=np.float64)

            optimize = (
                step == 0
                or refit_interval <= 1
                or step % refit_interval == 0
                or stagnation == recovery_after
            )

            t0 = time.perf_counter()
            fit_info = surrogate.fit(
                X,
                y,
                optimize=optimize,
                fallback_steps=50,
            )
            surrogate.synchronize()
            self.timings["model_s"] += time.perf_counter() - t0

            if optimize:
                self.fit_diagnostics["optimized_fits"] += 1
            else:
                self.fit_diagnostics["warm_only_fits"] += 1
            if fit_info.scipy_warning:
                self.fit_diagnostics["scipy_warnings"] += 1
            if fit_info.fallback_used:
                self.fit_diagnostics["fallback_fits"] += 1

            pool_size = self._dynamic_pool(
                candidate_pool,
                step,
                smart_trials,
                stagnation,
            )

            if stagnation == recovery_after:
                self.events.append({
                    "step": step,
                    "event": "stagnation_recovery",
                    "best": best,
                    "pool": pool_size,
                })
                # Re-seed region centers from diverse elites and expand.
                self._refresh_regions(default_radius=0.30)
                for region in self.regions:
                    region.radius = min(0.40, max(0.28, region.radius * 1.35))

            pool = self._generate_candidates(
                pool_size,
                step,
                stagnation,
            )

            scores, details = self._portfolio_scores(
                surrogate,
                pool,
                best_y=best,
                step=step,
                total_steps=smart_trials,
                stagnation=stagnation,
                chunk_size=candidate_chunk_size,
            )

            idx = int(np.nanargmax(scores))
            chosen = pool[idx]

            previous_best = best
            result = self._evaluate01(chosen)

            if result.feasible and result.score > best + 1e-8:
                best = result.score
                stagnation = 0
                total_no_progress = 0
            else:
                stagnation += 1
                total_no_progress += 1

            self._update_regions(
                chosen,
                result,
                previous_best,
            )

            # Periodically refresh region centers from globally diverse elites.
            if (step + 1) % 6 == 0:
                self._refresh_regions()

            self.events.append({
                "step": step,
                "event": "iteration",
                "mode": details["mode"],
                "pool": pool_size,
                "score": result.score,
                "feasible": result.feasible,
                "best": best,
                "stagnation": stagnation,
                "region_radii": [r.radius for r in self.regions],
            })

            if total_no_progress >= patience:
                break

        feasible = [r for r in self.history if r.feasible]
        if not feasible:
            feasible = list(self.history)

        feasible.sort(key=lambda r: r.score, reverse=True)

        return {
            "trials_run": len(self.history),
            "best": feasible[0],
            "top": feasible[:8],
            "device": device_info,
            "timings": dict(self.timings),
            "fit_diagnostics": dict(self.fit_diagnostics),
            "gpu_memory": surrogate.memory_stats(),
            "events": list(self.events),
            "regions": [
                {
                    "center": r.center.tolist(),
                    "radius": r.radius,
                    "score": r.score,
                }
                for r in self.regions
            ],
        }
