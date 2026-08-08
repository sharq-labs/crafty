import math
import numpy as np

def cooling_benchmark(x: np.ndarray) -> tuple[float, bool, dict]:
    '''
    Benchmark اصطناعي فقط لإثبات الـoptimization loop.

    variables:
      x[0] = fan_diameter_mm
      x[1] = blade_pitch_deg
      x[2] = rpm
      x[3] = duct_area_cm2

    score أعلى = أفضل.
    '''
    d, pitch, rpm, duct = map(float, x)

    # Cheap feasibility gates
    feasible = True
    reasons = []

    tip_speed = math.pi * (d / 1000.0) * rpm / 60.0
    if tip_speed > 95:
        feasible = False
        reasons.append("tip_speed_limit")

    if duct < 0.45 * (math.pi * (d / 20.0) ** 2):
        feasible = False
        reasons.append("duct_too_small")

    if not 14 <= pitch <= 38:
        feasible = False
        reasons.append("pitch_range")

    # Toy physics/performance surface — not production physics.
    size_factor = (d / 180.0) ** 1.55
    rpm_factor = (rpm / 2600.0) ** 1.18
    pitch_factor = math.exp(-((pitch - 27.0) / 8.5) ** 2)
    duct_factor = 1.0 - math.exp(-duct / 170.0)

    cooling = 120.0 * size_factor * rpm_factor * pitch_factor * duct_factor
    power = 0.000018 * (rpm ** 2) * (d / 180.0) ** 2.2
    noise_proxy = (tip_speed / 55.0) ** 2.2
    mass_proxy = 0.012 * d + 0.0025 * duct

    score = cooling - 0.22 * power - 7.0 * noise_proxy - 0.8 * mass_proxy

    if not feasible:
        score -= 250.0

    return score, feasible, {
        "cooling_proxy": cooling,
        "power_proxy": power,
        "noise_proxy": noise_proxy,
        "mass_proxy": mass_proxy,
        "tip_speed_m_s": tip_speed,
        "reasons": reasons,
    }
