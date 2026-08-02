from __future__ import annotations

from .validation.coco_bbob import (
    _resolve_bbob_final_target,
)


class WorkingPublicAPI:
    final_target_fvalue1 = 123.00000001


class BrokenPublicAPI:
    @property
    def final_target_fvalue1(self):
        raise AttributeError(
            "simulated broken cocoex binding"
        )


def main():
    target, source = (
        _resolve_bbob_final_target(
            WorkingPublicAPI()
        )
    )
    assert abs(
        target - 123.00000001
    ) < 1e-14
    assert source == "final_target_fvalue1"

    target2, source2 = (
        _resolve_bbob_final_target(
            BrokenPublicAPI()
        )
    )
    assert target2 is None
    assert source2 == "unavailable_use_cocopp"

    print(
        "V0.3.2.5 COCO target compatibility self-test: PASS"
    )
    print(
        f"working public target : {target:.12g}"
    )
    print(
        "broken binding target : N/A (official metrics delegated to cocopp)"
    )


if __name__ == "__main__":
    main()
