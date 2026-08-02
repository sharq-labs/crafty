from __future__ import annotations

import numpy as np


def _normalized_project_x(x):
    d, pitch, rpm, duct = map(float, x)
    return np.array([
        (d - 100.0) / 160.0,
        (pitch - 10.0) / 32.0,
        (rpm - 900.0) / 3300.0,
        (duct - 80.0) / 440.0,
    ], dtype=float)


def constraint_margins_for(name: str, x):
    """
    Continuous margins: >= 0 means feasible.

    These margins reproduce the boolean feasibility rules of the existing
    synthetic benchmark suite so LogConstrainedExpectedImprovement can model
    constraints continuously instead of relying on a classifier.
    """
    u = _normalized_project_x(x)
    u0, u1, u2, u3 = map(float, u)

    if name == "multimodal":
        return [
            min(u0 - 0.04, 0.96 - u0),
            min(u1 - 0.04, 0.96 - u1),
            min(u2 - 0.04, 0.96 - u2),
            min(u3 - 0.04, 0.96 - u3),
        ]

    if name == "narrow_optimum":
        return [
            min(u0 - 0.03, 0.97 - u0),
            min(u1 - 0.03, 0.97 - u1),
            min(u2 - 0.03, 0.97 - u2),
            min(u3 - 0.03, 0.97 - u3),
        ]

    if name == "constrained_islands":
        c1 = (u0 - 0.62) ** 2 + (u3 - 0.63) ** 2
        c2 = 0.58 * u2 + 0.32 * u0 + 0.18 * u1
        c3 = abs((0.74 * u0 + 0.24 * u2) - (0.16 + 0.80 * u3))
        return [
            c1 - 0.015,
            0.20 - c1,
            0.84 - c2,
            0.27 - c3,
            u1 - 0.08,
            0.91 - u1,
        ]

    if name == "deceptive_local":
        return [
            min(u0 - 0.04, 0.96 - u0),
            min(u1 - 0.04, 0.96 - u1),
            min(u2 - 0.04, 0.96 - u2),
            min(u3 - 0.04, 0.96 - u3),
        ]

    if name == "flat_plateau":
        return [
            min(u0 - 0.05, 0.95 - u0),
            min(u3 - 0.05, 0.95 - u3),
        ]

    if name == "mixed_sensitivity":
        return [
            min(u0 - 0.08, 0.94 - u0),
            min(u2 - 0.07, 0.93 - u2),
            0.72 - (0.43 * u0 + 0.51 * u2),
        ]

    return []


def with_continuous_constraints(name, evaluator):
    def wrapped(x):
        score, feasible, metadata = evaluator(x)
        metadata = dict(metadata)
        margins = constraint_margins_for(name, x)
        metadata["constraint_margins"] = [float(v) for v in margins]

        # Sanity: continuous margins should match the benchmark boolean rule.
        if margins:
            margin_feasible = all(v >= -1e-12 for v in margins)
            metadata["margin_feasible"] = bool(margin_feasible)

        return score, feasible, metadata

    return wrapped
