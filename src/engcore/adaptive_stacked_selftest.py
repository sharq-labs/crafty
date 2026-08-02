"""
Fast V0.3.3 adaptive optimizer self-tests.

Toy functions only. No COCO campaigns.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .adaptive_policy import (
    decide_adaptive_policy,
)
from .adaptive_stacked_engine import (
    AdaptiveStackedGPBOEngine,
)
from .landscape_diagnostics import (
    compute_landscape_diagnostics,
)
from .models import DesignSpace, Variable
from .stacked_engine import StackedGPBOEngine
from .stacked_modes import get_stacked_mode
from .validation.optimizers import (
    ALGORITHMS,
    run_adaptive_stacked,
    run_stacked,
)
from .validation.problem import (
    ObjectiveRecorder,
)


def _require(cond, msg):
    if not cond:
        raise AssertionError(msg)


def _sphere(x):
    x = np.asarray(x, dtype=float)
    return float(np.sum(x * x))


def _space(dim=2, bound=2.0):
    return DesignSpace([
        Variable(f"x{i}", -bound, bound, "")
        for i in range(dim)
    ])


def test_diagnostics_small_n_finite():
    d0 = compute_landscape_diagnostics(
        x01_history=[],
        scores=[],
        best_score=float("-inf"),
        evaluations_since_improve=0,
        total_budget=20,
        dimension=2,
    )
    _require(d0.n_obs == 0, "n_obs")
    _require(
        np.isfinite(d0.stagnation_score),
        "stag finite",
    )

    X = np.array(
        [[0.1, 0.2], [0.4, 0.5], [0.3, 0.1]],
        dtype=float,
    )
    y = np.array([-1.0, -0.5, -0.8])
    d = compute_landscape_diagnostics(
        x01_history=X,
        scores=y,
        best_score=-0.5,
        evaluations_since_improve=1,
        total_budget=20,
        dimension=2,
        weight_rbf=0.6,
        weight_history=[{
            "mean_logp_rbf": -0.2,
            "mean_logp_matern": -0.8,
        }],
    )
    for key, value in d.as_dict().items():
        if key in {
            "best_score",
            "normalized_improvement_velocity",
        }:
            continue
        if isinstance(value, (int, float)):
            _require(
                np.isfinite(value),
                f"non-finite {key}={value}",
            )


def test_policy_deterministic_and_generic():
    d = compute_landscape_diagnostics(
        x01_history=np.random.default_rng(0).random(
            (12, 2)
        ),
        scores=np.linspace(-2, -0.1, 12),
        best_score=-0.1,
        evaluations_since_improve=8,
        total_budget=40,
        dimension=2,
        weight_rbf=0.2,
        weight_history=[{
            "mean_logp_rbf": -1.5,
            "mean_logp_matern": -1.4,
        }],
    )
    a = decide_adaptive_policy(d).as_dict()
    b = decide_adaptive_policy(d).as_dict()
    _require(a == b, "policy not deterministic")

    # Source must not mention benchmark identity.
    root = Path(__file__).resolve().parent
    for name in (
        "adaptive_policy.py",
        "landscape_diagnostics.py",
        "adaptive_stacked_engine.py",
    ):
        text = (
            root / name
        ).read_text(encoding="utf-8").lower()
        for banned in (
            "bbob_f",
            "fopt",
            "function_id",
            "cocoex.function",
            "benchmarkfunction",
        ):
            _require(
                banned not in text,
                f"{name} contains banned token {banned}",
            )


def test_exact_budget_and_no_hidden_evals():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        return _sphere(x)

    budget = 12
    lower = np.array([-2.0, -2.0])
    upper = np.array([2.0, 2.0])
    row = run_adaptive_stacked(
        problem_id="toy_sphere",
        func=func,
        lower=lower,
        upper=upper,
        budget=budget,
        seed=99,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )
    _require(
        row.evaluations == budget,
        "budget mismatch",
    )
    _require(
        calls["n"] == budget,
        f"hidden evals? calls={calls['n']}",
    )
    _require(
        row.algorithm
        == "adaptive_stacked_v033",
        "identity",
    )
    _require(
        row.metadata.get(
            "diagnostic_history_len",
            0,
        )
        > 0,
        "diagnostics not recorded",
    )


def test_reproducibility():
    def make_engine(seed):
        space = _space(2)

        def evaluator(x):
            f = _sphere(x)
            return -f, True, {"objective_f": f}

        return AdaptiveStackedGPBOEngine(
            design_space=space,
            evaluator=evaluator,
            seed=seed,
            screen_device="cpu",
            record_diagnostics=True,
        )

    mode = get_stacked_mode("fast")
    # Shrink pools for fast test without changing identity semantics much.
    mode = dict(mode)
    mode["screen_pool"] = 2048
    mode["pulse_screen_pool"] = 4096
    mode["severe_screen_pool"] = 4096
    mode["refinement_timeout_sec"] = 0.5

    r1 = make_engine(7).run(
        initial_trials=4,
        smart_trials=6,
        verbose=False,
        **mode,
    )
    r2 = make_engine(7).run(
        initial_trials=4,
        smart_trials=6,
        verbose=False,
        **mode,
    )
    x1 = np.asarray(r1["best"].x, dtype=float)
    x2 = np.asarray(r2["best"].x, dtype=float)
    _require(
        np.allclose(x1, x2),
        "adaptive reproducibility failed",
    )
    _require(
        r1["trials_run"] == r2["trials_run"] == 10,
        "trial count",
    )


def test_baseline_stacked_unchanged_identity():
    calls = {"n": 0}

    def func(x):
        calls["n"] += 1
        return _sphere(x)

    row = run_stacked(
        problem_id="toy_sphere_base",
        func=func,
        lower=np.array([-2.0, -2.0]),
        upper=np.array([2.0, 2.0]),
        budget=10,
        seed=5,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )
    _require(
        row.algorithm == "stacked_v0301",
        "baseline identity changed",
    )
    _require(
        row.evaluations == 10
        and calls["n"] == 10,
        "baseline budget broken",
    )
    _require(
        isinstance(
            StackedGPBOEngine,
            type,
        ),
        "StackedGPBOEngine missing",
    )
    _require(
        "adaptive_stacked" in ALGORITHMS,
        "adaptive not registered",
    )
    _require(
        "stacked" in ALGORITHMS,
        "stacked missing",
    )


def test_rescue_obeys_budget():
    # Force a tiny run and ensure rescue never adds objective calls.
    rec = ObjectiveRecorder(
        _sphere,
        [-1.5, -1.5],
        [1.5, 1.5],
        budget=10,
    )

    def evaluator(x):
        f = rec.evaluate(x)
        return -float(f), True, {
            "objective_f": float(f)
        }

    engine = AdaptiveStackedGPBOEngine(
        design_space=_space(2, 1.5),
        evaluator=evaluator,
        seed=123,
        screen_device="cpu",
    )
    mode = get_stacked_mode("fast")
    mode = dict(mode)
    mode["screen_pool"] = 1024
    mode["pulse_screen_pool"] = 1024
    mode["severe_screen_pool"] = 1024
    mode["stagnation_trigger"] = 2
    mode["refinement_timeout_sec"] = 0.25
    result = engine.run(
        initial_trials=3,
        smart_trials=7,
        verbose=False,
        **mode,
    )
    _require(
        rec.evaluations == 10,
        "rescue broke budget",
    )
    _require(
        result["fit_diagnostics"][
            "adaptive_policy_updates"
        ]
        == 7,
        "policy updates missing",
    )


def main():
    print(
        "Engineering AI Core V0.3.3 — "
        "Adaptive Stacked Self-Test"
    )
    print("=" * 72)

    test_diagnostics_small_n_finite()
    print("[PASS] diagnostics finite / tiny-N")

    test_policy_deterministic_and_generic()
    print(
        "[PASS] policy deterministic / "
        "no benchmark tokens"
    )

    test_baseline_stacked_unchanged_identity()
    print(
        "[PASS] baseline stacked_v0301 still runnable"
    )

    test_exact_budget_and_no_hidden_evals()
    print(
        "[PASS] adaptive exact budget / "
        "no hidden evals"
    )

    test_rescue_obeys_budget()
    print("[PASS] rescue obeys budget")

    test_reproducibility()
    print("[PASS] adaptive reproducibility")

    print("=" * 72)
    print(
        "V0.3.3 Adaptive Stacked self-test: PASS"
    )


if __name__ == "__main__":
    main()
