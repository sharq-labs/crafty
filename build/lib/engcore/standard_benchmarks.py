from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .models import DesignSpace, Variable


@dataclass(frozen=True)
class StandardBenchmark:
    name: str
    description: str
    evaluator: Callable
    optimum_score: float | None = None


def make_unit_space(dim=4):
    return DesignSpace([
        Variable(f"x{i}", 0.0, 1.0, "")
        for i in range(dim)
    ])


def _map(x01, low, high):
    x01 = np.asarray(x01, dtype=float)
    return low + x01 * (high - low)


def ackley(x01):
    x = _map(x01, -5.0, 5.0)
    d = len(x)
    a = 20.0
    b = 0.2
    c = 2.0 * math.pi
    term1 = -a * math.exp(
        -b * math.sqrt(float(np.sum(x*x)) / d)
    )
    term2 = -math.exp(
        float(np.sum(np.cos(c*x))) / d
    )
    f = term1 + term2 + a + math.e
    return -float(f), True, {}


def rastrigin(x01):
    x = _map(x01, -5.12, 5.12)
    f = 10.0 * len(x) + float(
        np.sum(x*x - 10.0*np.cos(2.0*math.pi*x))
    )
    return -f, True, {}


def rosenbrock(x01):
    x = _map(x01, -2.0, 2.0)
    f = float(np.sum(
        100.0 * (x[1:] - x[:-1]**2)**2
        + (1.0 - x[:-1])**2
    ))
    return -f, True, {}


def levy(x01):
    x = _map(x01, -10.0, 10.0)
    w = 1.0 + (x - 1.0) / 4.0

    term1 = math.sin(math.pi * w[0])**2
    term3 = (
        (w[-1] - 1.0)**2
        * (1.0 + math.sin(2.0*math.pi*w[-1])**2)
    )

    mid = np.sum(
        (w[:-1] - 1.0)**2
        * (
            1.0
            + 10.0*np.sin(math.pi*w[:-1] + 1.0)**2
        )
    )

    f = float(term1 + mid + term3)
    return -f, True, {}


def styblinski_tang(x01):
    x = _map(x01, -5.0, 5.0)
    f = 0.5 * float(
        np.sum(x**4 - 16.0*x**2 + 5.0*x)
    )
    return -f, True, {}


def griewank(x01):
    x = _map(x01, -20.0, 20.0)
    indices = np.arange(1, len(x)+1, dtype=float)
    f = (
        float(np.sum(x*x)) / 4000.0
        - float(np.prod(np.cos(x / np.sqrt(indices))))
        + 1.0
    )
    return -float(f), True, {}


STANDARD_BENCHMARKS = [
    StandardBenchmark(
        "ackley",
        "Classic multimodal benchmark.",
        ackley,
        0.0,
    ),
    StandardBenchmark(
        "rastrigin",
        "Highly multimodal periodic benchmark.",
        rastrigin,
        0.0,
    ),
    StandardBenchmark(
        "rosenbrock",
        "Narrow curved valley benchmark.",
        rosenbrock,
        0.0,
    ),
    StandardBenchmark(
        "levy",
        "Multimodal benchmark with structured valleys.",
        levy,
        0.0,
    ),
    StandardBenchmark(
        "styblinski_tang",
        "Separable multimodal polynomial benchmark.",
        styblinski_tang,
        None,
    ),
    StandardBenchmark(
        "griewank",
        "Product-plus-quadratic multimodal benchmark.",
        griewank,
        0.0,
    ),
]
