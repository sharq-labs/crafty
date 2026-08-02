from __future__ import annotations

import math
import numpy as np


def hard_cooling_benchmark(x: np.ndarray) -> tuple[float, bool, dict]:
    """
    Hard synthetic engineering-style benchmark for optimizer validation only.

    Properties:
    - global region is interior, not at variable maxima
    - multiple local optima
    - coupled nonlinear constraints
    - boundary penalties
    - interacting variables

    NOT validated engineering physics.
    """
    d, pitch, rpm, duct = map(float, x)

    u = np.array([
        (d - 100.0) / 160.0,
        (pitch - 10.0) / 32.0,
        (rpm - 900.0) / 3300.0,
        (duct - 80.0) / 440.0,
    ], dtype=float)

    u0, u1, u2, u3 = map(float, u)

    feasible = True
    reasons = []

    envelopes = [
        (u0, 0.05, 0.95, "diameter_operating_envelope"),
        (u1, 0.10, 0.90, "pitch_operating_envelope"),
        (u2, 0.06, 0.94, "rpm_operating_envelope"),
        (u3, 0.05, 0.96, "duct_operating_envelope"),
    ]
    for value, low, high, reason in envelopes:
        if not (low <= value <= high):
            feasible = False
            reasons.append(reason)

    loading = 0.52 * u2 + 0.35 * u0 + 0.18 * u1
    if loading > 0.90:
        feasible = False
        reasons.append("combined_loading_limit")

    flow_match = abs((0.72 * u0 + 0.28 * u2) - (0.20 + 0.74 * u3))
    if flow_match > 0.34:
        feasible = False
        reasons.append("flow_match")

    # Main interior basin.
    c1 = np.array([0.64, 0.55, 0.56, 0.65])
    s1 = np.array([0.15, 0.14, 0.14, 0.17])
    peak1 = 125.0 * math.exp(-float(np.sum(((u - c1) / s1) ** 2)))

    # Local optimum 1.
    c2 = np.array([0.31, 0.72, 0.36, 0.41])
    s2 = np.array([0.12, 0.11, 0.13, 0.15])
    peak2 = 82.0 * math.exp(-float(np.sum(((u - c2) / s2) ** 2)))

    # Local optimum 2.
    c3 = np.array([0.75, 0.30, 0.40, 0.51])
    s3 = np.array([0.17, 0.13, 0.16, 0.19])
    peak3 = 66.0 * math.exp(-float(np.sum(((u - c3) / s3) ** 2)))

    base = (
        42.0
        + 23.0 * math.sin(math.pi * u0) * math.sin(math.pi * u3)
        + 15.0 * math.sin(math.pi * u1)
        + 13.0 * math.sin(math.pi * u2)
    )

    ripple = (
        8.0 * math.sin(5.0 * math.pi * u0) * math.cos(3.0 * math.pi * u2)
        + 5.5 * math.cos(4.0 * math.pi * u1) * math.sin(3.0 * math.pi * u3)
    )

    power_proxy = 18.0 + 72.0 * (u2 ** 2.25) + 24.0 * (u0 ** 1.8) + 8.0 * u1 * u2
    noise_proxy = 4.0 + 38.0 * (u2 ** 2.0) * (0.45 + 0.55 * u0)
    mass_proxy = 5.0 + 18.0 * u0 + 11.0 * u3

    boundary_penalty = 0.0
    for value in u:
        boundary_penalty += 12.0 * (
            math.exp(-((value - 0.04) / 0.055) ** 2)
            + math.exp(-((value - 0.96) / 0.055) ** 2)
        )

    performance_proxy = base + peak1 + peak2 + peak3 + ripple

    score = (
        performance_proxy
        - 0.31 * power_proxy
        - 0.17 * noise_proxy
        - 0.20 * mass_proxy
        - boundary_penalty
    )

    if not feasible:
        score -= 180.0

    return float(score), bool(feasible), {
        "performance_proxy": float(performance_proxy),
        "power_proxy": float(power_proxy),
        "noise_proxy": float(noise_proxy),
        "mass_proxy": float(mass_proxy),
        "boundary_penalty": float(boundary_penalty),
        "loading_proxy": float(loading),
        "flow_match_proxy": float(flow_match),
        "normalized_position": [float(v) for v in u],
        "reasons": reasons,
    }
