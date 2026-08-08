from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .hard_statistical_benchmark import run_one


def main():
    parser = argparse.ArgumentParser(
        description="Compare GP refit intervals on the Smart engine."
    )
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--budget", type=int, default=60)
    parser.add_argument("--pool", type=int, default=100000)
    parser.add_argument("--chunk", type=int, default=1024)
    parser.add_argument("--intervals", default="1,4,6")
    parser.add_argument("--start-seed", type=int, default=500)
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    intervals = [
        int(v.strip())
        for v in args.intervals.split(",")
        if v.strip()
    ]

    out_dir = Path("v025_refit_sweep")
    out_dir.mkdir(exist_ok=True)

    rows = []

    print("=" * 84)
    print("Engineering AI Core V0.2.5 — Refit Interval Sweep")
    print("=" * 84)
    print(f"Intervals: {intervals}")
    print(f"Runs each : {args.runs}")
    print("")

    for interval in intervals:
        for i in range(args.runs):
            seed = args.start_seed + i

            row = run_one(
                seed=seed,
                budget=args.budget,
                pool=args.pool,
                chunk=args.chunk,
                refit_interval=interval,
                force_cpu=args.cpu,
            )

            rows.append({
                "interval": interval,
                "seed": seed,
                "smart_score": row["smart_score"],
                "smart_wall_s": row["smart_wall_s"],
                "smart_penalized": row["smart_penalized"],
                "smart_auc": row["smart_auc"],
                "candidate_throughput":
                    row["candidate_throughput"],
                "model_total_s": row["model_total_s"],
                "candidate_scoring_s":
                    row["candidate_scoring_s"],
                "scipy_warnings":
                    row["scipy_warnings"],
                "fallback_fits":
                    row["fallback_fits"],
            })

            print(
                f"interval={interval} "
                f"[{i+1}/{args.runs}] "
                f"seed={seed} "
                f"score={row['smart_score']:.3f} "
                f"wall={row['smart_wall_s']:.2f}s"
            )

    csv_path = out_dir / "refit_sweep.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    grouped = {}

    for interval in intervals:
        subset = [r for r in rows if r["interval"] == interval]

        grouped[interval] = {
            "score_mean":
                float(np.mean([r["smart_score"] for r in subset])),
            "score_median":
                float(np.median([r["smart_score"] for r in subset])),
            "wall_mean":
                float(np.mean([r["smart_wall_s"] for r in subset])),
            "target_mean":
                float(np.mean([r["smart_penalized"] for r in subset])),
            "auc_mean":
                float(np.mean([r["smart_auc"] for r in subset])),
            "model_time_mean":
                float(np.mean([r["model_total_s"] for r in subset])),
            "warnings":
                int(sum(r["scipy_warnings"] for r in subset)),
            "fallbacks":
                int(sum(r["fallback_fits"] for r in subset)),
        }

    lines = [
        "=" * 84,
        "Engineering AI Core V0.2.5 — Refit Interval Sweep",
        "=" * 84,
    ]

    for interval in intervals:
        g = grouped[interval]
        lines.extend([
            f"Refit interval {interval}",
            f"  Smart score mean        : {g['score_mean']:.6f}",
            f"  Smart score median      : {g['score_median']:.6f}",
            f"  Wall time mean          : {g['wall_mean']:.3f} s",
            f"  Penalized target mean   : {g['target_mean']:.2f}",
            f"  AUC mean                : {g['auc_mean']:.6f}",
            f"  Model time mean         : {g['model_time_mean']:.3f} s",
            f"  SciPy warnings          : {g['warnings']}",
            f"  Fallback fits           : {g['fallbacks']}",
            "",
        ])

    summary = "\n".join(lines).strip()
    print()
    print(summary)

    (out_dir / "summary.txt").write_text(
        summary,
        encoding="utf-8",
    )

    # One chart: score vs wall-time tradeoff.
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)

    for interval in intervals:
        g = grouped[interval]
        ax.scatter(
            [g["wall_mean"]],
            [g["score_mean"]],
            s=90,
            label=f"refit={interval}",
        )
        ax.annotate(
            str(interval),
            (g["wall_mean"], g["score_mean"]),
        )

    ax.set_xlabel("Mean Smart Wall Time (s)")
    ax.set_ylabel("Mean Smart Final Score")
    ax.set_title("V0.2.5 — Refit Quality vs Compute Cost")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(
        out_dir / "refit_tradeoff.png",
        dpi=170,
    )
    plt.close(fig)

    print()
    print(f"Saved: {out_dir}")


if __name__ == "__main__":
    main()
