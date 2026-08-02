from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
from scipy.spatial.distance import cdist
from scipy.special import ndtr
from scipy.stats import qmc
from sklearn.ensemble import ExtraTreesClassifier

from .models import ExperimentResult
from .sampling import sobol_points
from .gpu_surrogate import TorchBotorchSurrogate, describe_device


@dataclass
class Region:
    center: np.ndarray
    radius: float
    score: float


class ConservativeRobustEngine:
    """
    V0.2.7

    Principle:
      Keep proven Expected Improvement as the champion.
      Improve WHERE we search, not replace EI with an over-exploratory mixture.

    Normal mode:
      - EI is the dominant acquisition.
      - candidate pool = global Sobol + multiple local trust regions.
      - feasibility probability gates candidates when enough labels exist.
      - a small novelty term only breaks near-ties.

    Recovery mode:
      - triggered only after sustained stagnation.
      - ONE controlled exploration pulse, then immediately return to EI.
      - UCB / uncertainty / novelty are allowed only behind quality gates.

    No early termination before the requested experiment budget is consumed.
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
        self.events = []
        self.regions = []

        self.timings = {
            "evaluation_s": 0.0,
            "model_s": 0.0,
            "candidate_generation_s": 0.0,
            "candidate_scoring_s": 0.0,
            "feasibility_s": 0.0,
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

    def _best_feasible(self):
        feasible = [r.score for r in self.history if r.feasible]
        if feasible:
            return float(max(feasible))
        return float(max(r.score for r in self.history))

    def _diverse_elites(self, count):
        ranked = [
            (i, r.score)
            for i, r in enumerate(self.history)
            if r.feasible
        ]
        if not ranked:
            ranked = [(i, r.score) for i, r in enumerate(self.history)]

        ranked.sort(key=lambda t: t[1], reverse=True)

        chosen = []
        min_separation = 0.11

        for idx, score in ranked:
            p = self.x01_history[idx]

            if not chosen:
                chosen.append((idx, score))
            else:
                centers = np.asarray(
                    [self.x01_history[j] for j, _ in chosen],
                    dtype=float,
                )
                distance = np.min(
                    np.linalg.norm(centers - p[None, :], axis=1)
                )
                if distance >= min_separation:
                    chosen.append((idx, score))

            if len(chosen) >= count:
                break

        # Fill if diversity constraint was too strict.
        if len(chosen) < count:
            used = {idx for idx, _ in chosen}
            for idx, score in ranked:
                if idx not in used:
                    chosen.append((idx, score))
                    used.add(idx)
                if len(chosen) >= count:
                    break

        return chosen

    def _refresh_regions(self, step, total_steps):
        elites = self._diverse_elites(self.n_regions)

        # Coarse-to-fine schedule, but never collapse too aggressively.
        progress = step / max(1, total_steps - 1)
        base_radius = 0.24 - 0.10 * progress
        base_radius = float(np.clip(base_radius, 0.12, 0.24))

        old_radii = [r.radius for r in self.regions]
        new_regions = []

        for j, (idx, score) in enumerate(elites):
            radius = old_radii[j] if j < len(old_radii) else base_radius
            # Slowly move radius toward scheduled scale.
            radius = 0.65 * radius + 0.35 * base_radius

            new_regions.append(
                Region(
                    center=self.x01_history[idx].copy(),
                    radius=float(np.clip(radius, 0.10, 0.30)),
                    score=float(score),
                )
            )

        self.regions = new_regions

    def _local_sobol(self, center, radius, n, seed):
        sampler = qmc.Sobol(
            d=self.space.dim,
            scramble=True,
            seed=seed,
        )
        m = int(math.ceil(math.log2(max(2, n))))
        points = sampler.random_base2(m)[:n]
        delta = (2.0 * points - 1.0) * radius
        return np.clip(center[None, :] + delta, 0.0, 1.0)

    def _generate_pool(self, pool_size, step, total_steps, recovery=False):
        t0 = time.perf_counter()

        self._refresh_regions(step, total_steps)

        # Preserve a large truly-global component so we never become worse
        # simply because local trust regions guessed wrong.
        global_fraction = 0.60 if not recovery else 0.78
        global_n = int(pool_size * global_fraction)
        local_total = pool_size - global_n

        global_points = sobol_points(
            global_n,
            self.space.dim,
            self.seed + 100_000 + step,
        )

        parts = [global_points]

        if self.regions and local_total > 0:
            per_region = max(64, local_total // len(self.regions))

            for j, region in enumerate(self.regions):
                radius = region.radius
                if recovery:
                    radius = min(0.34, radius * 1.35)

                parts.append(
                    self._local_sobol(
                        region.center,
                        radius,
                        per_region,
                        self.seed + 200_000 + 1009 * step + j,
                    )
                )

        pool = np.vstack(parts)
        if len(pool) > pool_size:
            pool = pool[:pool_size]

        self.timings["candidate_generation_s"] += (
            time.perf_counter() - t0
        )
        return pool

    @staticmethod
    def _scale01(values):
        values = np.asarray(values, dtype=float)
        lo = float(np.quantile(values, 0.02))
        hi = float(np.quantile(values, 0.98))
        if hi - lo < 1e-12:
            return np.zeros_like(values)
        return np.clip((values - lo) / (hi - lo), 0.0, 1.0)

    def _novelty(self, pool):
        t0 = time.perf_counter()
        history = np.asarray(self.x01_history, dtype=float)
        out = np.empty(len(pool), dtype=float)

        block_size = 25_000
        for start in range(0, len(pool), block_size):
            block = pool[start:start + block_size]
            distances = cdist(block, history)
            out[start:start + len(block)] = np.min(distances, axis=1)

        self.timings["novelty_s"] += time.perf_counter() - t0
        return out

    def _fit_feasibility_model(self):
        labels = np.asarray(
            [1 if r.feasible else 0 for r in self.history],
            dtype=int,
        )

        # Need both classes and enough observations.
        if (
            len(labels) < 20
            or len(np.unique(labels)) < 2
            or min(np.sum(labels == 0), np.sum(labels == 1)) < 3
        ):
            return None

        X = np.asarray(self.x01_history, dtype=float)

        model = ExtraTreesClassifier(
            n_estimators=96,
            max_depth=8,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=self.seed + len(self.history),
            n_jobs=-1,
        )
        model.fit(X, labels)
        return model

    def _feasibility_probability(self, model, pool):
        if model is None:
            return np.ones(len(pool), dtype=float)

        t0 = time.perf_counter()
        classes = list(model.classes_)
        if 1 not in classes:
            return np.ones(len(pool), dtype=float)

        idx = classes.index(1)
        probability = model.predict_proba(pool)[:, idx]
        self.timings["feasibility_s"] += time.perf_counter() - t0

        # Keep a floor so the model cannot permanently forbid unexplored areas.
        return 0.15 + 0.85 * probability

    def _acquisition(
        self,
        surrogate,
        pool,
        best_y,
        chunk_size,
        recovery,
    ):
        t0 = time.perf_counter()
        mean, std = surrogate.predict_mean_std(
            pool,
            chunk_size=chunk_size,
        )
        surrogate.synchronize()
        self.timings["candidate_scoring_s"] += (
            time.perf_counter() - t0
        )

        improvement = mean - float(best_y) - 0.01
        z = improvement / np.maximum(std, 1e-12)
        pdf = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        ei = improvement * ndtr(z) + std * pdf

        novelty = self._novelty(pool)
        feasibility_model = self._fit_feasibility_model()
        p_feasible = self._feasibility_probability(
            feasibility_model,
            pool,
        )

        ei_n = self._scale01(ei)
        novelty_n = self._scale01(novelty)

        if not recovery:
            # Champion policy: EI dominates.
            # Novelty only nudges near-ties.
            score = (
                0.965 * ei_n
                + 0.035 * novelty_n
            ) * (p_feasible ** 1.25)

            # Never spend experiments on almost exact duplicates.
            score = np.where(novelty < 0.006, -np.inf, score)

            return score, {
                "mode": "champion_ei",
                "ei": ei,
                "mean": mean,
                "std": std,
                "novelty": novelty,
                "p_feasible": p_feasible,
            }

        # Recovery pulse. Exploration is quality-gated.
        ucb = mean + 2.6 * std
        ucb_n = self._scale01(ucb)
        std_n = self._scale01(std)

        # Only candidates with meaningful EI OR promising predicted mean are
        # eligible for aggressive exploration.
        mean_n = self._scale01(mean)
        eligible = (ei_n >= 0.35) | (mean_n >= 0.72)

        recovery_score = (
            0.50 * ei_n
            + 0.26 * ucb_n
            + 0.14 * std_n
            + 0.10 * novelty_n
        ) * (p_feasible ** 1.10)

        # If candidate fails quality gate, fall back to normal EI score.
        champion_score = (
            0.965 * ei_n + 0.035 * novelty_n
        ) * (p_feasible ** 1.25)

        score = np.where(
            eligible,
            recovery_score,
            champion_score,
        )
        score = np.where(novelty < 0.006, -np.inf, score)

        return score, {
            "mode": "controlled_recovery",
            "ei": ei,
            "mean": mean,
            "std": std,
            "novelty": novelty,
            "p_feasible": p_feasible,
        }

    def run(
        self,
        initial_trials=24,
        smart_trials=56,
        candidate_pool=100_000,
        candidate_chunk_size=1024,
        refit_interval=4,
        recovery_after=9,
    ):
        initial = sobol_points(
            initial_trials,
            self.space.dim,
            self.seed,
        )

        for p in initial:
            self._evaluate01(p)

        best = self._best_feasible()
        stagnation = 0

        surrogate = TorchBotorchSurrogate(
            self.space.dim,
            force_cpu=self.force_cpu,
        )
        device_info = describe_device(surrogate.device)
        surrogate.reset_peak_memory()

        total_steps = smart_trials

        for step in range(smart_trials):
            X = np.asarray(self.x01_history, dtype=np.float64)
            y = np.asarray(
                [r.score for r in self.history],
                dtype=np.float64,
            )

            recovery = (
                stagnation >= recovery_after
                and (stagnation - recovery_after) % 6 == 0
            )

            optimize = (
                step == 0
                or refit_interval <= 1
                or step % refit_interval == 0
                or recovery
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

            # Recovery gets a larger global pool for one pulse only.
            pool_size = (
                int(candidate_pool * 1.45)
                if recovery
                else candidate_pool
            )

            pool = self._generate_pool(
                pool_size,
                step,
                total_steps,
                recovery=recovery,
            )

            scores, details = self._acquisition(
                surrogate,
                pool,
                best_y=best,
                chunk_size=candidate_chunk_size,
                recovery=recovery,
            )

            idx = int(np.nanargmax(scores))
            chosen = pool[idx]
            previous_best = best
            result = self._evaluate01(chosen)

            if result.feasible and result.score > best + 1e-8:
                best = float(result.score)
                stagnation = 0
            else:
                stagnation += 1

            # Adapt nearest trust region mildly.
            if self.regions:
                centers = np.asarray(
                    [r.center for r in self.regions],
                    dtype=float,
                )
                j = int(np.argmin(
                    np.linalg.norm(
                        centers - chosen[None, :],
                        axis=1,
                    )
                ))

                if result.feasible and result.score > previous_best + 1e-8:
                    self.regions[j].center = chosen.copy()
                    self.regions[j].score = result.score
                    self.regions[j].radius = min(
                        0.30,
                        self.regions[j].radius * 1.08,
                    )
                elif not recovery:
                    self.regions[j].radius = max(
                        0.10,
                        self.regions[j].radius * 0.97,
                    )

            self.events.append({
                "step": step,
                "mode": details["mode"],
                "recovery": recovery,
                "pool": pool_size,
                "score": float(result.score),
                "feasible": bool(result.feasible),
                "best": float(best),
                "stagnation": int(stagnation),
                "mean_p_feasible": float(
                    np.mean(details["p_feasible"])
                ),
                "max_ei": float(np.max(details["ei"])),
            })

        # IMPORTANT: no early stop; consume full requested budget.
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
            "recovery_count": int(sum(
                1 for e in self.events if e["recovery"]
            )),
        }
