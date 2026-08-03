import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _diag_tmp.diagnose_rosenbrock_v033 import (
    get_problem,
    capture_trajectory,
    run_instrumented,
)
from src.engcore.validation.optimizers import run_stacked

problem = get_problem()
stacked = capture_trajectory(run_stacked, problem, "stacked")


def ndev(xs):
    return sum(
        1
        for a, b in zip(stacked["xs"], xs)
        if not np.allclose(a, b, rtol=0, atol=1e-12)
    )


def first(xs):
    for i, (a, b) in enumerate(zip(stacked["xs"], xs)):
        if not np.allclose(a, b, rtol=0, atol=1e-12):
            return i + 1
    return None


for mode in [
    "A_no_search_realloc",
    "B_no_forced_refit",
    "DIAG_ONLY_NO_REPLACE",
]:
    r = run_instrumented(problem, counterfactual=mode)
    identical = all(
        np.allclose(a, b, rtol=0, atol=1e-12)
        for a, b in zip(stacked["xs"], r["xs"])
    )
    print(
        mode,
        "best=",
        f"{r['best_f']:.6g}",
        "first_div=",
        first(r["xs"]),
        "ndev=",
        ndev(r["xs"]),
        "identical=",
        identical,
    )
