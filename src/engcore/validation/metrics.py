from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from .problem import Trace


DEFAULT_TARGET_DELTAS = (
    1e2,
    1e1,
    1e0,
    1e-1,
    1e-2,
    1e-4,
    1e-6,
)


def final_target_gap(trace: Trace) -> float | None:
    if trace.final_target is None:
        return None
    return max(
        0.0,
        float(trace.best_f)
        - float(trace.final_target),
    )


def log10_target_gap(
    trace: Trace,
    floor=1e-12,
) -> float | None:
    gap = final_target_gap(trace)
    if gap is None:
        return None
    return math.log10(
        max(float(gap), float(floor))
    )


def first_hit_evaluation(
    trace: Trace,
    delta: float,
) -> int | None:
    if trace.final_target is None:
        return None

    threshold = (
        float(trace.final_target)
        + float(delta)
    )

    for i, value in enumerate(
        trace.best_curve,
        start=1,
    ):
        if float(value) <= threshold:
            return i

    return None


def target_fraction(
    trace: Trace,
    deltas=DEFAULT_TARGET_DELTAS,
) -> float:
    if trace.final_target is None:
        return float("nan")

    hits = sum(
        first_hit_evaluation(
            trace,
            delta,
        ) is not None
        for delta in deltas
    )
    return hits / len(deltas)


def summarize_traces(
    traces: list[Trace],
    deltas=DEFAULT_TARGET_DELTAS,
):
    if not traces:
        return {
            "algorithms": {},
            "per_problem_ranks": [],
        }

    by_problem = defaultdict(list)
    for t in traces:
        by_problem[t.problem_id].append(t)

    ranks = []
    wins = defaultdict(int)

    for problem_id, rows in by_problem.items():
        sorted_rows = sorted(
            rows,
            key=lambda t: (
                log10_target_gap(t)
                if log10_target_gap(t)
                is not None
                else float(t.best_f)
            ),
        )

        for rank, t in enumerate(
            sorted_rows,
            start=1,
        ):
            ranks.append({
                "problem_id": problem_id,
                "algorithm": t.algorithm,
                "rank": rank,
            })

        if sorted_rows:
            wins[
                sorted_rows[0].algorithm
            ] += 1

    by_algorithm = defaultdict(list)
    for t in traces:
        by_algorithm[t.algorithm].append(t)

    result = {}

    for algorithm, rows in by_algorithm.items():
        row_ranks = [
            r["rank"]
            for r in ranks
            if r["algorithm"] == algorithm
        ]

        gaps = [
            log10_target_gap(t)
            for t in rows
        ]
        gaps = [
            g for g in gaps
            if g is not None
        ]

        target_fracs = [
            target_fraction(t, deltas)
            for t in rows
        ]
        target_fracs = [
            x for x in target_fracs
            if np.isfinite(x)
        ]

        target_rows = [
            t for t in rows
            if t.final_target is not None
        ]

        hit_rate = (
            sum(
                t.target_hit
                for t in target_rows
            )
            / len(target_rows)
            if target_rows
            else float("nan")
        )

        result[algorithm] = {
            "runs": len(rows),
            "mean_rank":
                float(np.mean(row_ranks))
                if row_ranks
                else float("nan"),
            "median_rank":
                float(np.median(row_ranks))
                if row_ranks
                else float("nan"),
            "wins":
                int(wins[algorithm]),
            "final_target_hit_rate":
                float(hit_rate),
            "mean_target_fraction":
                float(np.mean(target_fracs))
                if target_fracs
                else float("nan"),
            "median_log10_final_gap":
                float(np.median(gaps))
                if gaps
                else float("nan"),
            "mean_wall_s":
                float(np.mean([
                    t.wall_s for t in rows
                ])),
            "mean_evaluations":
                float(np.mean([
                    t.evaluations for t in rows
                ])),
        }

    return {
        "algorithms": result,
        "per_problem_ranks": ranks,
    }
