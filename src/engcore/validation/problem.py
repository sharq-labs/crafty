from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np


@dataclass
class Trace:
    algorithm: str
    problem_id: str
    dimension: int
    budget: int
    seed: int
    best_f: float
    evaluations: int
    values: list[float] = field(default_factory=list)
    best_curve: list[float] = field(default_factory=list)
    final_target: float | None = None
    target_hit: bool = False
    wall_s: float = 0.0
    metadata: dict = field(default_factory=dict)


class ObjectiveRecorder:
    """
    Strict black-box minimization wrapper.

    The optimizer can see only:
      - x bounds
      - objective values returned from evaluate()

    Reference target information is kept outside the optimization path and is
    used only after a run to compute benchmark metrics.

    Validation behavior is intentionally observable:
      - non-finite candidate coordinates fail fast;
      - out-of-bounds coordinates are clipped only as a last numerical guard
        and counted;
      - non-finite objective values are converted to +inf and counted.
    """

    def __init__(
        self,
        func: Callable[[np.ndarray], float],
        lower_bounds: Sequence[float],
        upper_bounds: Sequence[float],
        budget: int,
    ):
        self.func = func
        self.lower = np.asarray(lower_bounds, dtype=np.float64)
        self.upper = np.asarray(upper_bounds, dtype=np.float64)
        self.budget = int(budget)

        if self.lower.shape != self.upper.shape:
            raise ValueError("lower/upper bounds shape mismatch")
        if np.any(~np.isfinite(self.lower)) or np.any(~np.isfinite(self.upper)):
            raise ValueError("Validation Lab requires finite bounds")
        if np.any(self.upper <= self.lower):
            raise ValueError("Every upper bound must be greater than lower")
        if self.budget <= 0:
            raise ValueError("budget must be positive")

        self.values: list[float] = []
        self.best_curve: list[float] = []
        self.best_f = float("inf")
        self.best_x: np.ndarray | None = None

        # Audit counters. These are validation metadata only and never alter
        # an optimizer's legal observation budget.
        self.candidate_nonfinite_count = 0
        self.candidate_clipped_count = 0
        self.objective_nonfinite_count = 0

    @property
    def dimension(self) -> int:
        return int(self.lower.size)

    @property
    def evaluations(self) -> int:
        return len(self.values)

    @property
    def remaining(self) -> int:
        return self.budget - self.evaluations

    def audit_metadata(self) -> dict[str, int]:
        return {
            "candidate_nonfinite_count": int(
                self.candidate_nonfinite_count
            ),
            "candidate_clipped_count": int(
                self.candidate_clipped_count
            ),
            "objective_nonfinite_count": int(
                self.objective_nonfinite_count
            ),
        }

    def evaluate(self, x) -> float:
        if self.evaluations >= self.budget:
            raise RuntimeError(
                f"Evaluation budget exhausted: {self.budget}"
            )

        x = np.asarray(x, dtype=np.float64).reshape(-1)
        if x.shape != self.lower.shape:
            raise ValueError(
                f"x shape {x.shape} != expected {self.lower.shape}"
            )

        if not np.all(np.isfinite(x)):
            self.candidate_nonfinite_count += 1
            raise ValueError(
                "Optimizer proposed non-finite candidate coordinates"
            )

        # Algorithms in the arena are responsible for respecting bounds.
        # Clip only as a last numerical guard and retain an auditable count.
        x_eval = np.clip(x, self.lower, self.upper)
        if not np.array_equal(x_eval, x):
            self.candidate_clipped_count += 1

        value = float(self.func(x_eval))

        if not np.isfinite(value):
            self.objective_nonfinite_count += 1
            value = float("inf")

        self.values.append(value)

        if value < self.best_f:
            self.best_f = value
            self.best_x = x_eval.copy()

        self.best_curve.append(float(self.best_f))
        return value
