from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from .validation.local_suite import (
    make_local_suite,
)
from .validation.optimizers import (
    run_de,
    run_random,
    run_sobol,
)
from .validation.arena import (
    write_results,
)


def main():
    problem = make_local_suite(
        (2,), instances=(1,)
    )[0]

    midpoint = (problem.lower + problem.upper) / 2.0
    assert not np.allclose(problem.optimum_x, midpoint)

    rows = []

    for runner in (
        run_random,
        run_sobol,
        run_de,
    ):
        rows.append(
            runner(
                problem_id=problem.problem_id,
                func=problem.func,
                lower=problem.lower,
                upper=problem.upper,
                budget=20,
                seed=123,
                final_target=(
                    problem.final_target
                ),
            )
        )

    assert all(
        r.evaluations == 20
        for r in rows
    )
    assert all(
        len(r.best_curve) == 20
        for r in rows
    )
    assert all(
        np.all(
            np.diff(
                np.asarray(
                    r.best_curve,
                    dtype=float,
                )
            ) <= 1e-12
        )
        for r in rows
    )

    with tempfile.TemporaryDirectory() as d:
        summary, text, csv_path, json_path, txt_path = (
            write_results(
                rows,
                Path(d),
            )
        )

        assert csv_path.exists()
        assert json_path.exists()
        assert txt_path.exists()
        assert len(
            summary["algorithms"]
        ) == 3

    print(
        "V0.3.2.5 Validation Lab self-test: PASS"
    )
    for r in rows:
        print(
            f"{r.algorithm:12s} "
            f"evals={r.evaluations:2d} "
            f"best={r.best_f:.6g}"
        )


if __name__ == "__main__":
    main()
