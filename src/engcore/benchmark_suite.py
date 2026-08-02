from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np


Evaluator = Callable[[np.ndarray], tuple[float, bool, dict]]


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    description: str
    evaluator: Evaluator


def _u(x: np.ndarray) -> np.ndarray:
    """Project design variables -> normalized [0,1]^4."""
    d, pitch, rpm, duct = map(float, x)
    return np.array([
        (d - 100.0) / 160.0,
        (pitch - 10.0) / 32.0,
        (rpm - 900.0) / 3300.0,
        (duct - 80.0) / 440.0,
    ], dtype=float)


def _gauss(u, center, scale, height):
    center = np.asarray(center, dtype=float)
    scale = np.asarray(scale, dtype=float)
    return float(height * math.exp(-float(np.sum(((u - center) / scale) ** 2))))


def multimodal(x: np.ndarray):
    u = _u(x)
    p1 = _gauss(u, [0.64, 0.55, 0.56, 0.65], [0.15, 0.14, 0.14, 0.17], 125)
    p2 = _gauss(u, [0.31, 0.72, 0.36, 0.41], [0.12, 0.11, 0.13, 0.15], 86)
    p3 = _gauss(u, [0.77, 0.29, 0.42, 0.50], [0.16, 0.13, 0.15, 0.18], 72)
    ripple = 11 * math.sin(5*math.pi*u[0]) * math.cos(3*math.pi*u[2])
    base = 30 + 18*np.prod(np.sin(math.pi*np.clip(u, 0, 1)))
    score = float(base + p1 + p2 + p3 + ripple)
    feasible = bool(np.all((u >= 0.04) & (u <= 0.96)))
    if not feasible:
        score -= 150
    return score, feasible, {"normalized_position": u.tolist(), "family": "multimodal"}


def narrow_optimum(x: np.ndarray):
    u = _u(x)
    broad = _gauss(u, [0.33, 0.66, 0.40, 0.46], [0.20, 0.18, 0.19, 0.21], 80)
    narrow = _gauss(u, [0.68, 0.48, 0.62, 0.71], [0.055, 0.060, 0.050, 0.060], 155)
    ripple = 7 * math.sin(4*math.pi*u[0]) * math.sin(3*math.pi*u[3])
    score = float(25 + broad + narrow + ripple)
    feasible = bool(np.all((u >= 0.03) & (u <= 0.97)))
    if not feasible:
        score -= 160
    return score, feasible, {"normalized_position": u.tolist(), "family": "narrow_optimum"}


def constrained_islands(x: np.ndarray):
    u = _u(x)
    raw = (
        35
        + _gauss(u, [0.70, 0.54, 0.60, 0.68], [0.16,0.16,0.16,0.17], 140)
        + _gauss(u, [0.35, 0.32, 0.52, 0.40], [0.14,0.13,0.15,0.14], 85)
    )
    c1 = (u[0] - 0.62)**2 + (u[3] - 0.63)**2
    c2 = 0.58*u[2] + 0.32*u[0] + 0.18*u[1]
    c3 = abs((0.74*u[0] + 0.24*u[2]) - (0.16 + 0.80*u[3]))
    feasible = bool(
        0.015 <= c1 <= 0.20
        and c2 <= 0.84
        and c3 <= 0.27
        and 0.08 <= u[1] <= 0.91
    )
    score = float(raw if feasible else raw - 190.0)
    return score, feasible, {
        "normalized_position": u.tolist(),
        "family": "constrained_islands",
        "constraint_radial": float(c1),
        "constraint_loading": float(c2),
        "constraint_match": float(c3),
    }


def deceptive_local(x: np.ndarray):
    u = _u(x)
    # Very wide local optimum and a smaller-volume, higher global optimum.
    local = _gauss(u, [0.30, 0.66, 0.37, 0.43], [0.23,0.22,0.22,0.23], 118)
    global_peak = _gauss(u, [0.73, 0.38, 0.67, 0.72], [0.085,0.080,0.075,0.085], 178)
    valley = _gauss(u, [0.52, 0.52, 0.52, 0.52], [0.17,0.17,0.17,0.17], 65)
    score = float(22 + local + global_peak - valley)
    feasible = bool(np.all((u >= 0.04) & (u <= 0.96)))
    if not feasible:
        score -= 140
    return score, feasible, {"normalized_position": u.tolist(), "family": "deceptive_local"}


def flat_plateau(x: np.ndarray):
    u = _u(x)
    dist = float(np.linalg.norm((u - np.array([0.61,0.52,0.59,0.66])) / np.array([0.21,0.19,0.20,0.22])))
    # Broad plateau + subtle inner improvement, difficult for pure exploitation.
    plateau = 100.0 / (1.0 + math.exp(7.5*(dist - 1.0)))
    inner = _gauss(u, [0.61,0.52,0.59,0.66], [0.09,0.08,0.08,0.09], 32)
    ripple = 2.5 * math.sin(8*math.pi*u[0]) * math.cos(6*math.pi*u[2])
    score = float(32 + plateau + inner + ripple)
    feasible = bool(0.05 <= u[0] <= 0.95 and 0.05 <= u[3] <= 0.95)
    if not feasible:
        score -= 120
    return score, feasible, {"normalized_position": u.tolist(), "family": "flat_plateau"}


def mixed_sensitivity(x: np.ndarray):
    u = _u(x)
    # u0/u2 high sensitivity, u1/u3 lower sensitivity.
    peak = _gauss(u, [0.66,0.57,0.58,0.63], [0.075,0.26,0.065,0.24], 145)
    local = _gauss(u, [0.28,0.44,0.34,0.72], [0.10,0.28,0.09,0.24], 92)
    trend = 16*math.sin(math.pi*u[1]) + 12*math.sin(math.pi*u[3])
    score = float(30 + peak + local + trend)
    feasible = bool(
        (0.08 <= u[0] <= 0.94)
        and (0.07 <= u[2] <= 0.93)
        and (0.43*u[0] + 0.51*u[2] <= 0.72)
    )
    if not feasible:
        score -= 170
    return score, feasible, {"normalized_position": u.tolist(), "family": "mixed_sensitivity"}


BENCHMARKS = [
    BenchmarkSpec("multimodal", "Several local optima and oscillatory surface.", multimodal),
    BenchmarkSpec("narrow_optimum", "Small-volume global optimum hidden beside a broad basin.", narrow_optimum),
    BenchmarkSpec("constrained_islands", "Nonlinear feasibility islands and coupled constraints.", constrained_islands),
    BenchmarkSpec("deceptive_local", "Wide attractive local optimum hides narrower global optimum.", deceptive_local),
    BenchmarkSpec("flat_plateau", "Broad plateau with weak gradients and subtle central improvement.", flat_plateau),
    BenchmarkSpec("mixed_sensitivity", "Variables have strongly different sensitivities.", mixed_sensitivity),
]


def get_benchmark(name: str) -> BenchmarkSpec:
    for b in BENCHMARKS:
        if b.name == name:
            return b
    raise KeyError(f"Unknown benchmark: {name}")
