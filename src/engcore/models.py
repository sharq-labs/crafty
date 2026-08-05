from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class Variable:
    name: str
    low: float
    high: float
    unit: str = ""

    def __post_init__(self):
        if not str(self.name).strip():
            raise ValueError("Variable name must be non-empty")
        if not np.isfinite(float(self.low)) or not np.isfinite(float(self.high)):
            raise ValueError(f"Variable {self.name!r} requires finite bounds")
        if float(self.high) <= float(self.low):
            raise ValueError(
                f"Variable {self.name!r} requires high > low "
                f"({self.low} >= {self.high})"
            )


@dataclass
class DesignSpace:
    variables: Sequence[Variable]

    def __post_init__(self):
        self.variables = tuple(self.variables)
        if not self.variables:
            raise ValueError("DesignSpace requires at least one variable")
        names = [v.name for v in self.variables]
        if len(set(names)) != len(names):
            raise ValueError("DesignSpace variable names must be unique")

    @property
    def dim(self) -> int:
        return len(self.variables)

    def _vector(self, x, *, name: str) -> np.ndarray:
        arr = np.asarray(x, dtype=float).reshape(-1)
        if arr.shape != (self.dim,):
            raise ValueError(
                f"{name} shape {arr.shape} != expected {(self.dim,)}"
            )
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains NaN/Inf")
        return arr

    def denormalize(self, x01: np.ndarray) -> np.ndarray:
        x01 = self._vector(x01, name="x01")
        lows = np.array([v.low for v in self.variables], dtype=float)
        highs = np.array([v.high for v in self.variables], dtype=float)
        return lows + x01 * (highs - lows)

    def normalize(self, x: np.ndarray) -> np.ndarray:
        x = self._vector(x, name="x")
        lows = np.array([v.low for v in self.variables], dtype=float)
        highs = np.array([v.high for v in self.variables], dtype=float)
        return (x - lows) / (highs - lows)

    def as_dict(self, x: np.ndarray) -> dict:
        x = self._vector(x, name="x")
        return {
            v.name: float(value)
            for v, value in zip(self.variables, x)
        }


@dataclass
class ExperimentResult:
    x: np.ndarray
    score: float
    feasible: bool
    metadata: dict
