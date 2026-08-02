from dataclasses import dataclass
from typing import Callable, Sequence
import numpy as np

@dataclass(frozen=True)
class Variable:
    name: str
    low: float
    high: float
    unit: str = ""

@dataclass
class DesignSpace:
    variables: Sequence[Variable]

    @property
    def dim(self) -> int:
        return len(self.variables)

    def denormalize(self, x01: np.ndarray) -> np.ndarray:
        lows = np.array([v.low for v in self.variables], dtype=float)
        highs = np.array([v.high for v in self.variables], dtype=float)
        return lows + x01 * (highs - lows)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        lows = np.array([v.low for v in self.variables], dtype=float)
        highs = np.array([v.high for v in self.variables], dtype=float)
        return (np.asarray(x, dtype=float) - lows) / (highs - lows)

    def as_dict(self, x: np.ndarray) -> dict:
        return {v.name: float(value) for v, value in zip(self.variables, x)}

@dataclass
class ExperimentResult:
    x: np.ndarray
    score: float
    feasible: bool
    metadata: dict
