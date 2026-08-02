from __future__ import annotations

import csv
import json
from pathlib import Path

from .metrics import (
    DEFAULT_TARGET_DELTAS,
    final_target_gap,
    log10_target_gap,
    summarize_traces,
    target_fraction,
)
from .optimizers import ALGORITHMS


def run_problem_algorithms(
    *,
    problem_id,
    func_factory,
    lower,
    upper,
    budget,
    seed,
    final_target,
    algorithms,
    stacked_mode="fast",
    screen_device="auto",
    stacked_refinement_backend="torch",
):
    traces = []

    for algorithm in algorithms:
        if algorithm not in ALGORITHMS:
            raise KeyError(
                f"Unknown algorithm: {algorithm}"
            )

        # Each solver gets a NEW black-box function object. This is critical
        # for COCO where evaluation counters and observer state live on the
        # problem instance.
        try:
            func, cleanup = func_factory(
                algorithm
            )
        except TypeError:
            func, cleanup = func_factory()

        kwargs = dict(
            problem_id=problem_id,
            func=func,
            lower=lower,
            upper=upper,
            budget=int(budget),
            seed=int(seed),
            final_target=final_target,
        )

        if algorithm == "stacked":
            kwargs.update(
                mode=stacked_mode,
                screen_device=screen_device,
                refinement_backend=stacked_refinement_backend,
            )

        try:
            trace = ALGORITHMS[
                algorithm
            ](**kwargs)
            traces.append(trace)
        finally:
            cleanup()

    return traces



def _fmt_metric(value, width, precision=3):
    import math

    try:
        value = float(value)
    except Exception:
        return f"{'N/A':>{width}s}"

    if not math.isfinite(value):
        return f"{'N/A':>{width}s}"

    return f"{value:{width}.{precision}f}"



def write_results(
    traces,
    out_dir,
):
    out_dir = Path(out_dir)
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = out_dir / "runs.csv"

    fieldnames = [
        "problem_id",
        "algorithm",
        "dimension",
        "budget",
        "seed",
        "evaluations",
        "best_f",
        "final_target",
        "target_hit",
        "target_fraction",
        "final_gap",
        "log10_final_gap",
        "wall_s",
        "metadata_json",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for t in traces:
            writer.writerow({
                "problem_id":
                    t.problem_id,
                "algorithm":
                    t.algorithm,
                "dimension":
                    t.dimension,
                "budget":
                    t.budget,
                "seed":
                    t.seed,
                "evaluations":
                    t.evaluations,
                "best_f":
                    t.best_f,
                "final_target":
                    t.final_target,
                "target_hit":
                    int(t.target_hit),
                "target_fraction":
                    target_fraction(t),
                "final_gap":
                    final_target_gap(t),
                "log10_final_gap":
                    log10_target_gap(t),
                "wall_s":
                    t.wall_s,
                "metadata_json":
                    json.dumps(
                        t.metadata,
                        sort_keys=True,
                    ),
            })

    summary = summarize_traces(
        traces,
        DEFAULT_TARGET_DELTAS,
    )

    json_path = (
        out_dir / "summary.json"
    )
    json_path.write_text(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    algorithms = summary[
        "algorithms"
    ]

    ranked = sorted(
        algorithms.items(),
        key=lambda kv: (
            kv[1]["mean_rank"],
            -kv[1][
                "mean_target_fraction"
            ],
        ),
    )

    lines = []
    lines.append("=" * 116)
    lines.append(
        "Engineering AI Core V0.3.2.5 — Optimizer Validation Lab"
    )
    lines.append("=" * 116)
    lines.append(
        "Ranking is per-problem, then averaged. "
        "Lower mean rank is better."
    )
    lines.append(
        "Target fraction = fraction of standard target deltas "
        "[1e2 ... 1e-6] reached within budget."
    )
    lines.append("")

    header = (
        f"{'Algorithm':20s} "
        f"{'Runs':>5s} "
        f"{'MeanRank':>9s} "
        f"{'Wins':>5s} "
        f"{'TargetFrac':>10s} "
        f"{'FinalHit':>8s} "
        f"{'MedLogGap':>10s} "
        f"{'Wall(s)':>9s}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for name, s in ranked:
        lines.append(
            f"{name:20s} "
            f"{s['runs']:5d} "
            f"{s['mean_rank']:9.3f} "
            f"{s['wins']:5d} "
            f"{_fmt_metric(s['mean_target_fraction'], 10)} "
            f"{_fmt_metric(s['final_target_hit_rate'], 8)} "
            f"{_fmt_metric(s['median_log10_final_gap'], 10)} "
            f"{s['mean_wall_s']:9.3f}"
        )

    lines.append("")
    if any(
        t.final_target is None
        for t in traces
    ):
        lines.append(
            "TargetFrac / FinalHit / MedLogGap are N/A when the installed "
            "cocoex binding does not expose the final target."
        )
        lines.append(
            "Use official COCO Observer logs + cocopp for target-based "
            "BBOB assessment."
        )

    lines.append(
        "NOTE: This lab measures optimizer behavior. "
        "It does not validate engineering physics."
    )
    lines.append("=" * 116)

    summary_txt = "\n".join(lines)
    txt_path = (
        out_dir / "summary.txt"
    )
    txt_path.write_text(
        summary_txt,
        encoding="utf-8",
    )

    return (
        summary,
        summary_txt,
        csv_path,
        json_path,
        txt_path,
    )
