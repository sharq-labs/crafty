from __future__ import annotations

import argparse
import warnings

import numpy as np

from .benchmark import make_space
from .validation.local_suite import make_local_suite
from .validation.optimizers import run_ngopt
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--screen-device",
        choices=["cpu", "cuda", "auto"],
        default="auto",
    )
    args = p.parse_args()

    problem = make_local_suite(
        (2,),
        instances=(2,),
    )[0]

    print("=" * 96)
    print(
        "Engineering AI Core V0.3.2.5 — Warning Recovery Check"
    )
    print("=" * 96)

    # NGOpt check.
    with warnings.catch_warnings(
        record=True
    ) as records:
        warnings.simplefilter("always")

        ng = run_ngopt(
            problem_id=problem.problem_id,
            func=problem.func,
            lower=problem.lower,
            upper=problem.upper,
            budget=20,
            seed=123,
            final_target=problem.final_target,
        )

    leaked_cobyla = [
        w for w in records
        if "COBYLA: Invalid RHOEND"
        in str(w.message)
    ]

    print(
        "NGOpt COBYLA warning leaked :",
        len(leaked_cobyla),
    )
    print(
        "NGOpt autocorrection count  :",
        ng.metadata.get(
            "cobyla_rhoend_autocorrections",
            0,
        ),
    )

    if leaked_cobyla:
        raise SystemExit(
            "Targeted COBYLA warning still leaked."
        )

    # Small stacked run: enough to exercise model fitting.
    space = make_space()
    engine = StackedGPBOEngine(
        design_space=space,
        evaluator=(
            lambda x: (
                -float(
                    np.sum(
                        np.asarray(x, dtype=float)
                        ** 2
                    )
                ),
                True,
                {},
            )
        ),
        seed=321,
        screen_device=args.screen_device,
    )

    with warnings.catch_warnings(
        record=True
    ) as records:
        warnings.simplefilter("always")

        result = engine.run(
            initial_trials=8,
            smart_trials=4,
            verbose=False,
            **get_stacked_mode("fast"),
        )

    leaked_abnormal = [
        w for w in records
        if (
            "scipy_minimize"
            in str(w.message)
            and "ABNORMAL"
            in str(w.message).upper()
        )
    ]

    d = result["fit_diagnostics"]

    print(
        "GP ABNORMAL warning leaked  :",
        len(leaked_abnormal),
    )
    print(
        "Recovered SciPy warnings    :",
        d[
            "scipy_fit_abnormal_recovered"
        ],
    )
    print(
        "Torch fallback attempts     :",
        d[
            "torch_fit_fallback_attempts"
        ],
    )
    print(
        "Torch fallback successes    :",
        d[
            "torch_fit_fallback_successes"
        ],
    )
    print(
        "Final fit failures          :",
        d["fit_failures"],
    )
    print("=" * 96)

    if leaked_abnormal:
        raise SystemExit(
            "Recovered ABNORMAL warning still leaked."
        )


if __name__ == "__main__":
    main()
