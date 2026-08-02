from __future__ import annotations

import numpy as np

from .stacked_engine import StackedGPBOEngine


def main():
    # A is clearly better.
    a = np.array([
        -0.1, -0.2, -0.1, -0.3
    ])
    b = np.array([
        -3.0, -2.5, -3.2, -2.8
    ])

    w, _ = (
        StackedGPBOEngine
        ._stacking_weight_from_logps(
            a,
            b,
            weight_floor=0.10,
        )
    )
    assert w > 0.5

    # B is clearly better.
    w2, _ = (
        StackedGPBOEngine
        ._stacking_weight_from_logps(
            b,
            a,
            weight_floor=0.10,
        )
    )
    assert w2 < 0.5

    # Equal predictions should remain approximately neutral.
    w3, _ = (
        StackedGPBOEngine
        ._stacking_weight_from_logps(
            a,
            a,
            weight_floor=0.10,
        )
    )
    assert abs(w3 - 0.5) <= 0.01

    print("V0.3.0.1 stacking self-test: PASS")
    print(f"better-A weight = {w:.3f}")
    print(f"better-B weight = {w2:.3f}")
    print(f"equal weight    = {w3:.3f}")


if __name__ == "__main__":
    main()
