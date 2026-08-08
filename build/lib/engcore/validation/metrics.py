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


def validate_trace_matrix(traces: list[Trace]) -> set[str]:
    """
    Validate matched-problem benchmark structure before computing ranks.

    Every problem must contain exactly one row for every participating
    algorithm. Duplicate (problem_id, algorithm) rows and missing algorithms
    can silently corrupt ranks / win shares, so fail fast instead.
    """
    if not traces:
        return set()

    by_problem: dict[str, list[Trace]] = defaultdict(list)
    for trace in traces:
        by_problem[str(trace.problem_id)].append(trace)

    expected_algorithms: set[str] | None = None

    for problem_id, rows in by_problem.items():
        names = [str(row.algorithm) for row in rows]
        unique = set(names)
        if len(unique) != len(names):
            duplicates = sorted({
                name for name in names
                if names.count(name) > 1
            })
            raise ValueError(
                "Duplicate benchmark trace row(s) for "
                f"problem {problem_id}: {duplicates}"
            )

        if expected_algorithms is None:
            expected_algorithms = unique
            if not expected_algorithms:
                raise ValueError("Benchmark trace matrix has no algorithms")
        elif unique != expected_algorithms:
            missing = sorted(expected_algorithms - unique)
            extra = sorted(unique - expected_algorithms)
            raise ValueError(
                "Unmatched benchmark trace matrix for "
                f"problem {problem_id}: missing={missing}, extra={extra}"
            )

    return set(expected_algorithms or set())


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


def comparison_score(trace: Trace) -> float:
    """
    Scalar used for per-problem ordering.

    Prefer log10 target gap when a final target is available; otherwise use
    raw best_f. Exact equality of this scalar defines ties (no tolerance).
    """
    gap = log10_target_gap(trace)
    if gap is not None:
        return float(gap)
    return float(trace.best_f)


def average_ranks_for_scores(
    scores: list[float],
) -> list[float]:
    """
    Competition average ranks for a minimization score list.

    Example: scores [1.0, 1.0, 2.0] -> ranks [1.5, 1.5, 3.0]
    Ties use exact equality only.
    """
    n = len(scores)
    if n == 0:
        return []

    order = sorted(
        range(n),
        key=lambda i: scores[i],
    )
    ranks = [0.0] * n
    i = 0

    while i < n:
        j = i + 1
        while (
            j < n
            and scores[order[j]]
            == scores[order[i]]
        ):
            j += 1

        # 1-based positions i+1 .. j share the mean rank.
        mean_rank = 0.5 * (
            (i + 1) + j
        )
        for k in range(i, j):
            ranks[order[k]] = float(
                mean_rank
            )
        i = j

    return ranks


def summarize_traces(
    traces: list[Trace],
    deltas=DEFAULT_TARGET_DELTAS,
):
    """
    Aggregate Validation Lab metrics.

    Ranking is always computed per problem_id first, then averaged.

    Win policy (V0.3.2.6):
      - win_share: if N algorithms share the exact best score on a problem,
        each receives fractional credit 1/N. This is the scientifically
        meaningful win metric and is never algorithm-order dependent.
      - wins / unique_wins: integer count of problems where one algorithm is
        the sole best (exact unique minimum). Preserved for backward-
        compatible integer reporting.
    """
    if not traces:
        return {
            "algorithms": {},
            "per_problem_ranks": [],
            "ranking_policy": {
                "ranks": "average_ranks_exact_ties",
                "win_share": "fractional_1_over_N_at_best",
                "unique_wins": "sole_best_only",
            },
        }

    validate_trace_matrix(traces)

    by_problem = defaultdict(list)
    for t in traces:
        by_problem[t.problem_id].append(t)

    ranks = []
    unique_wins = defaultdict(int)
    win_share = defaultdict(float)

    for problem_id, rows in by_problem.items():
        scores = [
            comparison_score(t)
            for t in rows
        ]
        avg_ranks = average_ranks_for_scores(
            scores
        )

        for t, rank in zip(
            rows,
            avg_ranks,
        ):
            ranks.append({
                "problem_id": problem_id,
                "algorithm": t.algorithm,
                "rank": float(rank),
                "score": float(
                    comparison_score(t)
                ),
            })

        best = min(scores)
        tied = [
            t for t, s in zip(rows, scores)
            if s == best
        ]
        share = 1.0 / len(tied)
        for t in tied:
            win_share[t.algorithm] += share

        if len(tied) == 1:
            unique_wins[
                tied[0].algorithm
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
            # Backward-compatible integer: sole-best wins only.
            "wins":
                int(unique_wins[algorithm]),
            "unique_wins":
                int(unique_wins[algorithm]),
            "win_share":
                float(win_share[algorithm]),
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
        "ranking_policy": {
            "ranks": "average_ranks_exact_ties",
            "win_share": "fractional_1_over_N_at_best",
            "unique_wins": "sole_best_only",
        },
    }
