from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

import numpy as np

from .validation.arena import (
    run_problem_algorithms,
    write_results,
)
from .validation.coco_bbob import (
    create_bbob_observer,
    prepare_coco_observer_parents,
)
from .validation.local_suite import (
    make_local_suite,
)
from .validation.metrics import (
    average_ranks_for_scores,
    summarize_traces,
)
from .validation.optimizers import (
    ALGORITHMS,
    assert_exact_budget,
    run_cmaes,
    run_de,
    run_ngopt,
    run_random,
    run_sobol,
    run_stacked,
)
from .validation.problem import (
    ObjectiveRecorder,
    Trace,
)


def _counting_func(base_func):
    state = {"n": 0}

    def func(x):
        state["n"] += 1
        return float(base_func(x))

    return func, state


def _require(cond, message):
    if not cond:
        raise AssertionError(message)


def test_local_factory_regression():
    problem = make_local_suite(
        (2,),
        instances=(1,),
    )[0]
    budget = 8

    def factory(
        algorithm=None,
        func=problem.func,
    ):
        _require(
            callable(func),
            "factory bound a non-callable objective "
            f"(algorithm={algorithm!r}, func={func!r})",
        )
        return func, (lambda: None)

    rows = run_problem_algorithms(
        problem_id=problem.problem_id,
        func_factory=factory,
        lower=problem.lower,
        upper=problem.upper,
        budget=budget,
        seed=321,
        final_target=problem.final_target,
        algorithms=["random", "sobol", "de"],
    )

    _require(len(rows) == 3, "expected 3 local arena traces")
    for row in rows:
        _require(
            row.evaluations == budget,
            f"{row.algorithm} local factory budget mismatch",
        )


def test_exact_budget_adapters():
    problem = make_local_suite(
        (2,),
        instances=(1,),
    )[0]
    budget = 10

    runners = [
        ("random", run_random, {}),
        ("sobol", run_sobol, {}),
        ("de", run_de, {}),
    ]

    if importlib.util.find_spec("cma") is not None:
        runners.append(("cmaes", run_cmaes, {}))

    if importlib.util.find_spec("nevergrad") is not None:
        runners.append(("ngopt", run_ngopt, {}))

    for name, runner, extra in runners:
        counted, state = _counting_func(
            problem.func
        )
        row = runner(
            problem_id=problem.problem_id,
            func=counted,
            lower=problem.lower,
            upper=problem.upper,
            budget=budget,
            seed=111,
            final_target=problem.final_target,
            **extra,
        )
        _require(
            row.evaluations == budget,
            f"{name} evaluations != budget",
        )
        _require(
            state["n"] == budget,
            f"{name} raw objective calls != budget "
            f"({state['n']})",
        )


def test_exact_budget_stacked_tiny():
    problem = make_local_suite(
        (2,),
        instances=(1,),
    )[0]
    budget = 12
    counted, state = _counting_func(
        problem.func
    )

    row = run_stacked(
        problem_id=problem.problem_id,
        func=counted,
        lower=problem.lower,
        upper=problem.upper,
        budget=budget,
        seed=222,
        final_target=problem.final_target,
        mode="fast",
        screen_device="cpu",
        refinement_backend="torch",
    )

    _require(
        row.evaluations == budget,
        "stacked evaluations != budget",
    )
    _require(
        state["n"] == budget,
        f"stacked raw objective calls != budget "
        f"({state['n']})",
    )
    _require(
        row.algorithm == "stacked_v0301",
        "unexpected stacked algorithm name",
    )


def test_assert_exact_budget_helper():
    def sphere(x):
        x = np.asarray(x, dtype=float)
        return float(np.sum(x * x))

    rec = ObjectiveRecorder(
        sphere,
        [-1.0, -1.0],
        [1.0, 1.0],
        budget=3,
    )
    rec.evaluate([0.0, 0.0])
    rec.evaluate([0.1, 0.1])

    try:
        assert_exact_budget(rec, "probe")
    except RuntimeError as exc:
        _require(
            "budget mismatch" in str(exc),
            "unexpected assert_exact_budget error",
        )
    else:
        raise AssertionError(
            "assert_exact_budget should fail on under-budget"
        )

    rec.evaluate([0.2, 0.2])
    assert_exact_budget(rec, "probe")


def test_average_rank_ties():
    two = average_ranks_for_scores(
        [1.0, 1.0, 2.0]
    )
    _require(
        two == [1.5, 1.5, 3.0],
        f"two-way tie ranks wrong: {two}",
    )

    three = average_ranks_for_scores(
        [5.0, 5.0, 5.0]
    )
    _require(
        three == [2.0, 2.0, 2.0],
        f"three-way tie ranks wrong: {three}",
    )

    none = average_ranks_for_scores(
        [3.0, 1.0, 2.0]
    )
    _require(
        none == [3.0, 1.0, 2.0],
        f"no-tie ranks wrong: {none}",
    )


def _make_trace(
    algorithm,
    problem_id,
    best_f,
):
    return Trace(
        algorithm=algorithm,
        problem_id=problem_id,
        dimension=2,
        budget=10,
        seed=1,
        best_f=float(best_f),
        evaluations=10,
        values=[float(best_f)],
        best_curve=[float(best_f)],
        final_target=None,
        target_hit=False,
        wall_s=0.0,
    )


def test_summarize_tie_policy_and_isolation():
    # Two-way tie on problem A; sole winner on problem B.
    traces = [
        _make_trace("A", "p1", 1.0),
        _make_trace("B", "p1", 1.0),
        _make_trace("C", "p1", 2.0),
        _make_trace("A", "p2", 10.0),
        _make_trace("B", "p2", 3.0),
        _make_trace("C", "p2", 4.0),
    ]

    # Reverse insertion order must not change ranks / win_share.
    summary_fwd = summarize_traces(traces)
    summary_rev = summarize_traces(
        list(reversed(traces))
    )

    for summary in (
        summary_fwd,
        summary_rev,
    ):
        algs = summary["algorithms"]
        _require(
            abs(algs["A"]["mean_rank"] - 2.25)
            < 1e-12,
            f"A mean_rank={algs['A']['mean_rank']}",
        )
        _require(
            abs(algs["B"]["mean_rank"] - 1.25)
            < 1e-12,
            f"B mean_rank={algs['B']['mean_rank']}",
        )
        _require(
            abs(algs["C"]["mean_rank"] - 2.5)
            < 1e-12,
            f"C mean_rank={algs['C']['mean_rank']}",
        )

        # p1: A/B share win -> 0.5 each; p2: B sole -> +1
        _require(
            abs(algs["A"]["win_share"] - 0.5)
            < 1e-12,
            f"A win_share={algs['A']['win_share']}",
        )
        _require(
            abs(algs["B"]["win_share"] - 1.5)
            < 1e-12,
            f"B win_share={algs['B']['win_share']}",
        )
        _require(
            abs(algs["C"]["win_share"] - 0.0)
            < 1e-12,
            f"C win_share={algs['C']['win_share']}",
        )
        _require(
            algs["A"]["wins"] == 0,
            "A unique wins should be 0",
        )
        _require(
            algs["B"]["wins"] == 1,
            "B unique wins should be 1",
        )
        _require(
            algs["C"]["wins"] == 0,
            "C unique wins should be 0",
        )

    # Per-problem isolation: raw values from p2 must not affect p1 ranks.
    p1_ranks = {
        r["algorithm"]: r["rank"]
        for r in summary_fwd["per_problem_ranks"]
        if r["problem_id"] == "p1"
    }
    _require(
        p1_ranks
        == {"A": 1.5, "B": 1.5, "C": 3.0},
        f"p1 ranks not isolated: {p1_ranks}",
    )


def test_three_way_win_share():
    traces = [
        _make_trace("A", "p", 0.0),
        _make_trace("B", "p", 0.0),
        _make_trace("C", "p", 0.0),
    ]
    summary = summarize_traces(traces)
    for name in ("A", "B", "C"):
        _require(
            abs(
                summary["algorithms"][name][
                    "win_share"
                ]
                - (1.0 / 3.0)
            )
            < 1e-12,
            f"{name} three-way win_share wrong",
        )
        _require(
            summary["algorithms"][name][
                "wins"
            ]
            == 0,
            f"{name} unique wins should be 0",
        )
        _require(
            abs(
                summary["algorithms"][name][
                    "mean_rank"
                ]
                - 2.0
            )
            < 1e-12,
            f"{name} three-way mean_rank wrong",
        )


def test_nested_coco_observer_path_and_finalize():
    coco_spec = importlib.util.find_spec(
        "cocoex"
    )
    if coco_spec is None:
        print(
            "SKIP nested COCO observer test "
            "(cocoex not installed)"
        )
        return

    import cocoex

    root = Path(
        "validation_results"
    ) / "_fairness_nested_coco"
    if root.exists():
        shutil.rmtree(root)
    ex_root = Path("exdata") / root
    if ex_root.exists():
        shutil.rmtree(ex_root)

    requested = (
        root
        / "level1"
        / "level2"
        / "level3"
        / "algo"
    )
    parents = prepare_coco_observer_parents(
        requested
    )
    _require(
        parents.parent.exists(),
        "requested observer parent missing",
    )
    _require(
        (Path("exdata") / parents.parent).exists(),
        "exdata observer parent missing",
    )

    observer, actual = create_bbob_observer(
        cocoex,
        requested_folder=requested,
        algorithm_name="fairness_probe",
        algorithm_info=(
            "Engineering AI Core V0.3.2.6 "
            "fairness selftest"
        ),
    )
    actual_path = Path(actual)
    _require(
        actual_path.exists(),
        f"observer result_folder missing: {actual}",
    )

    suite = cocoex.Suite("bbob", "", "")
    problem = (
        suite
        .get_problem_by_function_dimension_instance(
            1,
            2,
            1,
        )
    )
    try:
        problem.observe_with(observer)
        float(problem([0.0, 0.0]))
    finally:
        problem.free()
        suite.free()

    info_files = list(
        actual_path.rglob("*.info")
    )
    dat_files = list(
        actual_path.rglob("*.dat")
    )
    _require(
        len(info_files) >= 1,
        "COCO .info missing after problem.free()",
    )
    _require(
        len(dat_files) >= 1,
        "COCO .dat missing after problem.free()",
    )
    text = info_files[0].read_text(
        encoding="utf-8",
        errors="replace",
    )
    _require(
        len(text) > 0,
        "COCO .info unreadable after problem.free()",
    )

    # Documented policy: do not call Observer.free() on cocoex 2.8.2.
    free = getattr(observer, "free", None)
    _require(
        callable(free),
        "expected Observer.free to exist on this wheel",
    )
    del observer


def test_algorithms_registry():
    expected = {
        "random",
        "sobol",
        "de",
        "ngopt",
        "cmaes",
        "stacked",
        "adaptive_stacked",
    }
    _require(
        set(ALGORITHMS) == expected,
        f"unexpected ALGORITHMS keys: {set(ALGORITHMS)}",
    )


def main():
    print(
        "Engineering AI Core V0.3.2.6 — "
        "Validation Fairness Self-Test"
    )
    print("=" * 72)

    test_algorithms_registry()
    print("[PASS] algorithm registry")

    test_local_factory_regression()
    print("[PASS] local factory regression")

    test_assert_exact_budget_helper()
    print("[PASS] assert_exact_budget helper")

    test_exact_budget_adapters()
    print(
        "[PASS] exact budget "
        "(random/sobol/de[+cmaes][+ngopt])"
    )

    test_average_rank_ties()
    print("[PASS] average-rank ties")

    test_summarize_tie_policy_and_isolation()
    print(
        "[PASS] win_share / unique_wins / "
        "per-problem isolation"
    )

    test_three_way_win_share()
    print("[PASS] three-way win_share")

    test_nested_coco_observer_path_and_finalize()
    print(
        "[PASS] nested COCO observer path + "
        "problem.free finalization"
    )

    print(
        "[RUN ] stacked tiny exact-budget "
        "(may take ~15s on CPU)..."
    )
    test_exact_budget_stacked_tiny()
    print(
        "[PASS] stacked tiny exact-budget / "
        "no hidden objective evals"
    )

    with tempfile.TemporaryDirectory() as d:
        problem = make_local_suite(
            (2,),
            instances=(1,),
        )[0]

        def factory(
            algorithm=None,
            func=problem.func,
        ):
            return func, (lambda: None)

        rows = run_problem_algorithms(
            problem_id=problem.problem_id,
            func_factory=factory,
            lower=problem.lower,
            upper=problem.upper,
            budget=6,
            seed=7,
            final_target=problem.final_target,
            algorithms=["random", "sobol"],
        )
        summary, text, *_ = write_results(
            rows,
            Path(d),
        )
        _require(
            "WinShare" in text,
            "summary text missing WinShare",
        )
        _require(
            "win_share"
            in next(
                iter(
                    summary[
                        "algorithms"
                    ].values()
                )
            ),
            "summary json missing win_share",
        )

    print("[PASS] write_results schema")
    print("=" * 72)
    print(
        "V0.3.2.6 Validation Fairness "
        "self-test: PASS"
    )


if __name__ == "__main__":
    main()
