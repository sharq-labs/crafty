from __future__ import annotations

import argparse
from pathlib import Path

from .arena import (
    run_problem_algorithms,
    write_results,
)
from .local_suite import (
    make_local_suite,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--dimensions",
        default="2,5",
        help="Comma-separated dimensions",
    )
    p.add_argument(
        "--instances",
        default="1",
        help="Comma-separated shifted/rotated local instances",
    )
    p.add_argument(
        "--budget-multiplier",
        type=int,
        default=20,
        help="budget = multiplier * dimension",
    )
    p.add_argument(
        "--algorithms",
        default="random,sobol,de,stacked",
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
        "--out",
        default="validation_results/local_quick",
    )
    args = p.parse_args()

    dims = tuple(
        int(x)
        for x in args.dimensions.split(",")
        if x.strip()
    )
    instances = tuple(
        int(x) for x in args.instances.split(",") if x.strip()
    )

    algorithms = [
        x.strip()
        for x in args.algorithms.split(",")
        if x.strip()
    ]

    traces = []

    for problem in make_local_suite(
        dims, instances=instances
    ):
        budget = int(
            args.budget_multiplier
            * problem.dimension
        )

        # Factory contract: func_factory(algorithm=None) -> (func, cleanup).
        # Local problems are stateless, so the algorithm key is ignored.
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
            budget=budget,
            seed=args.seed,
            final_target=(
                problem.final_target
            ),
            algorithms=algorithms,
            stacked_mode=(
                args.stacked_mode
            ),
            screen_device=(
                args.screen_device
            ),
            stacked_refinement_backend=(
                args.stacked_refinement_backend
            ),
        )
        traces.extend(rows)

        scores = ", ".join(
            f"{t.algorithm}={t.best_f:.4g}"
            for t in rows
        )
        print(
            f"{problem.problem_id:20s} "
            f"budget={budget:4d} | "
            f"{scores}"
        )

    _, text, csv_path, _, _ = (
        write_results(
            traces,
            Path(args.out),
        )
    )

    print("")
    print(text)
    print(f"\nCSV: {csv_path}")


if __name__ == "__main__":
    main()
