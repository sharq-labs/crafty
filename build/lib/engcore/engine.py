from dataclasses import asdict
import numpy as np
from .models import DesignSpace, ExperimentResult
from .sampling import sobol_points
from .surrogate import GaussianSurrogate, expected_improvement

class SmartExperimentEngine:
    def __init__(
        self,
        design_space: DesignSpace,
        evaluator,
        seed: int = 42,
    ):
        self.space = design_space
        self.evaluator = evaluator
        self.seed = seed
        self.history: list[ExperimentResult] = []

    def _evaluate01(self, x01: np.ndarray) -> ExperimentResult:
        x = self.space.denormalize(x01)
        score, feasible, metadata = self.evaluator(x)
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
        initial_trials: int = 32,
        smart_trials: int = 68,
        candidate_pool: int = 4096,
        patience: int = 16,
        min_improvement: float = 1e-3,
    ):
        # 1) Smart initial design-of-experiments
        x0 = sobol_points(initial_trials, self.space.dim, self.seed)
        x01_history = []
        y_history = []

        for p in x0:
            r = self._evaluate01(p)
            x01_history.append(p)
            y_history.append(r.score)

        best = max(y_history)
        no_progress = 0

        # 2) Sequential Bayesian-style selection
        for step in range(smart_trials):
            X = np.asarray(x01_history)
            y = np.asarray(y_history)

            surrogate = GaussianSurrogate(self.space.dim)
            surrogate.fit(X, y)

            pool = sobol_points(
                candidate_pool,
                self.space.dim,
                self.seed + 1000 + step,
            )

            mean, std = surrogate.predict(pool)
            ei = expected_improvement(mean, std, best)

            # Prevent near-duplicates
            if len(X):
                distances = np.min(
                    np.linalg.norm(pool[:, None, :] - X[None, :, :], axis=2),
                    axis=1,
                )
                ei = np.where(distances < 1e-4, -np.inf, ei)

            idx = int(np.argmax(ei))
            chosen = pool[idx]
            r = self._evaluate01(chosen)

            x01_history.append(chosen)
            y_history.append(r.score)

            improvement = r.score - best
            if improvement > min_improvement:
                best = r.score
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
        }
