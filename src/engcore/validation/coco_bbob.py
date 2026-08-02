from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .arena import (
    run_problem_algorithms,
    write_results,
)


def _import_coco():
    try:
        import cocoex
        return cocoex
    except ImportError as exc:
        raise RuntimeError(
            "cocoex is not available in this Python environment. "
            "COCO's official Python interface is built from the COCO "
            "repository. See README-V0.3.2.md for Windows setup notes."
        ) from exc


def _get_problem(
    cocoex,
    function,
    dimension,
    instance,
):
    suite = cocoex.Suite(
        "bbob",
        "",
        "",
    )
    problem = (
        suite
        .get_problem_by_function_dimension_instance(
            int(function),
            int(dimension),
            int(instance),
        )
    )
    if problem is None:
        suite.free()
        raise RuntimeError(
            "COCO problem not found for "
            f"f={function}, d={dimension}, i={instance}"
        )
    return suite, problem



def _resolve_bbob_final_target(problem):
    """
    Best-effort target lookup for reporting only.

    On some coco-experiment 2.8.2 wheels, `final_target_fvalue1` is listed in
    generated documentation but missing from the actual compiled Problem
    object.

    V0.3.2.5 deliberately avoids private Cython/C access and does not attempt
    to reconstruct fopt. If the public property is unavailable, target-based
    assessment is delegated to official COCO Observer logs + cocopp.
    """
    try:
        value = getattr(
            problem,
            "final_target_fvalue1",
        )
    except Exception:
        value = None

    if value is not None:
        try:
            value = float(value)
            if np.isfinite(value):
                return (
                    value,
                    "final_target_fvalue1",
                )
        except (TypeError, ValueError):
            pass

    return (
        None,
        "unavailable_use_cocopp",
    )



def check_main():
    cocoex = _import_coco()

    suite, problem = _get_problem(
        cocoex,
        function=1,
        dimension=2,
        instance=1,
    )

    try:
        target, target_source = (
            _resolve_bbob_final_target(
                problem
            )
        )

        x = np.asarray(
            problem.initial_solution,
            dtype=np.float64,
        )
        y = float(problem(x))

        # Verify only the public API actually required by the arena.
        _ = np.asarray(
            problem.lower_bounds,
            dtype=np.float64,
        )
        _ = np.asarray(
            problem.upper_bounds,
            dtype=np.float64,
        )
        _ = int(problem.dimension)
        _ = str(problem.id)
        _ = int(problem.evaluations)

        print("=" * 96)
        print(
            "COCO/BBOB integration check: PASS"
        )
        print("=" * 96)
        print(
            f"cocoex version  : "
            f"{getattr(cocoex, '__version__', 'unknown')}"
        )
        print(
            f"problem id      : {problem.id}"
        )
        print(
            f"dimension       : {problem.dimension}"
        )
        print(
            f"initial f       : {y:.12g}"
        )
        print(
            f"evaluations     : {problem.evaluations}"
        )

        if target is None:
            print(
                "final target    : unavailable via this Python binding"
            )
            print(
                "target source   : unavailable_use_cocopp"
            )
            print(
                "official metrics: COCO Observer + cocopp"
            )
        else:
            print(
                f"final target    : {target:.12g}"
            )
            print(
                f"target source   : {target_source}"
            )

        print("=" * 96)

    finally:
        problem.free()
        suite.free()


def _sanitize_observer_name(value):
    import re

    value = str(value).replace("\\", "/")
    value = value.strip().strip("/")
    value = re.sub(
        r"[^A-Za-z0-9_./-]+",
        "_",
        value,
    )
    return value or "engcore_bbob"


def arena_main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--functions",
        default="1,3,6,8,9,10,15,21,24",
        help=(
            "Comma-separated BBOB function IDs. "
            "Use all for 1..24."
        ),
    )
    p.add_argument(
        "--dimensions",
        default="2,5",
    )
    p.add_argument(
        "--instances",
        default="1,2,3",
    )
    p.add_argument(
        "--budget-multiplier",
        type=int,
        default=20,
        help="budget = multiplier * dimension",
    )
    p.add_argument(
        "--algorithms",
        default="sobol,de,stacked",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=123,
    )
    p.add_argument(
        "--stacked-mode",
        choices=[
            "fast",
            "balanced",
            "quality",
        ],
        default="fast",
    )
    p.add_argument(
        "--screen-device",
        choices=[
            "cpu",
            "cuda",
            "auto",
        ],
        default="auto",
    )
    p.add_argument(
        "--stacked-refinement-backend",
        choices=["torch", "scipy"],
        default="torch",
    )
    p.add_argument(
        "--coco-observer",
        choices=["on", "off"],
        default="on",
    )
    p.add_argument(
        "--out",
        default="validation_results/coco_bbob",
    )
    args = p.parse_args()

    cocoex = _import_coco()

    if args.functions.strip().lower() == "all":
        functions = list(range(1, 25))
    else:
        functions = [
            int(x)
            for x in args.functions.split(",")
            if x.strip()
        ]

    dimensions = [
        int(x)
        for x in args.dimensions.split(",")
        if x.strip()
    ]
    instances = [
        int(x)
        for x in args.instances.split(",")
        if x.strip()
    ]
    algorithms = [
        x.strip()
        for x in args.algorithms.split(",")
        if x.strip()
    ]

    observers = {}
    observer_folders = {}

    if args.coco_observer == "on":
        base = _sanitize_observer_name(
            args.out
        )

        for algorithm in algorithms:
            folder = (
                f"{base}/coco_logs/{algorithm}"
            )
            options = (
                f"result_folder: {folder} "
                f"algorithm_name: {algorithm} "
                f'algorithm_info: "Engineering AI Core V0.3.2.5 arena"'
            )
            observer = cocoex.Observer(
                "bbob",
                options,
            )
            observers[algorithm] = observer

            try:
                observer_folders[
                    algorithm
                ] = str(
                    observer.result_folder
                )
            except Exception:
                observer_folders[
                    algorithm
                ] = folder

    traces = []
    total = (
        len(functions)
        * len(dimensions)
        * len(instances)
    )
    case_no = 0

    try:
        for dim in dimensions:
            for function in functions:
                for instance in instances:
                    case_no += 1
                    budget = int(
                        args.budget_multiplier
                        * dim
                    )

                    suite0, p0 = _get_problem(
                        cocoex,
                        function,
                        dim,
                        instance,
                    )
                    try:
                        problem_id = str(p0.id)
                        lower = np.asarray(
                            p0.lower_bounds,
                            dtype=np.float64,
                        ).copy()
                        upper = np.asarray(
                            p0.upper_bounds,
                            dtype=np.float64,
                        ).copy()
                        (
                            final_target,
                            target_source,
                        ) = _resolve_bbob_final_target(
                            p0
                        )
                    finally:
                        p0.free()
                        suite0.free()

                    def factory(
                        algorithm=None,
                        f=function,
                        d=dim,
                        i=instance,
                    ):
                        suite, problem = _get_problem(
                            cocoex,
                            f,
                            d,
                            i,
                        )

                        if (
                            algorithm is not None
                            and algorithm in observers
                        ):
                            problem.observe_with(
                                observers[algorithm]
                            )

                        def func(x):
                            return float(problem(x))

                        def cleanup():
                            problem.free()
                            suite.free()

                        return func, cleanup

                    rows = run_problem_algorithms(
                        problem_id=problem_id,
                        func_factory=factory,
                        lower=lower,
                        upper=upper,
                        budget=budget,
                        seed=(
                            int(args.seed)
                            + 10000 * instance
                            + 100 * function
                            + dim
                        ),
                        final_target=final_target,
                        algorithms=algorithms,
                        stacked_mode=args.stacked_mode,
                        screen_device=args.screen_device,
                        stacked_refinement_backend=(
                            args.stacked_refinement_backend
                        ),
                    )
                    traces.extend(rows)

                    best_row = min(
                        rows,
                        key=lambda t: t.best_f,
                    )

                    print(
                        f"[{case_no:03d}/{total:03d}] "
                        f"{problem_id:24s} "
                        f"budget={budget:4d} "
                        f"winner={best_row.algorithm:16s} "
                        f"f={best_row.best_f:.6g} "
                        f"target={target_source}"
                    )

        _, summary_text, csv_path, _, _ = (
            write_results(
                traces,
                Path(args.out),
            )
        )

        print("")
        print(summary_text)
        print(f"\nCSV: {csv_path}")

        if observer_folders:
            print("")
            print("=" * 116)
            print(
                "Official COCO observer data"
            )
            print("=" * 116)

            for algorithm, folder in (
                observer_folders.items()
            ):
                print(
                    f"{algorithm:20s}: {folder}"
                )

            print("")
            print(
                "Use cocopp on these folders for official "
                "target / ERT / ECDF post-processing."
            )
            print("=" * 116)

    finally:
        observers.clear()


if __name__ == "__main__":
    arena_main()
