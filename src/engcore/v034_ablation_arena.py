"""Three-way V0.3.4 causal ablation arena.

Compares, under identical COCO problems / seeds / budgets:

A) stacked_v0301
B) stacked_fresh_weights_v034
C) adaptive_stacked_v034

The middle arm changes only stacking-weight refresh frequency. This lets us
separate gains caused by fresh model weights from gains caused by the adaptive
proposal / safety-arbiter path.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .stacked_fresh_weights_engine import FreshWeightsStackedGPBOEngine
from .validation.arena import write_results
from .validation.coco_bbob import (
    _get_problem,
    _import_coco,
    _resolve_bbob_final_target,
    _sanitize_observer_name,
    create_bbob_observer,
)
from .validation.optimizers import (
    _trace,
    run_adaptive_stacked,
    run_stacked,
)
from .validation.problem import ObjectiveRecorder


SCIENTIFIC_IDS = {
    "stacked": "stacked_v0301",
    "stacked_fresh_weights": "stacked_fresh_weights_v034",
    "adaptive_stacked": "adaptive_stacked_v034",
}


def _package_version(name):
    """Best-effort installed version string; never raises."""
    try:
        import importlib.metadata as _md
        return _md.version(name)
    except Exception:
        try:
            module = __import__(name)
            return str(getattr(module, "__version__", "unknown"))
        except Exception:
            return "unavailable"


def _git_state():
    """Commit + dirtiness of the repo that produced this campaign.

    Untracked files are counted separately from tracked modifications:
    only tracked changes make the apparatus scientifically 'dirty'.
    """
    repo_root = Path(__file__).resolve().parents[2]

    def _run(cmd):
        try:
            out = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(repo_root),
            )
            if out.returncode == 0:
                return out.stdout.strip()
        except Exception:
            pass
        return "unknown"

    commit = _run(["git", "rev-parse", "HEAD"])
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = _run(["git", "status", "--porcelain"])
    tracked_dirty = []
    untracked = 0
    if status not in ("", "unknown"):
        for line in status.splitlines():
            if line.startswith("??"):
                untracked += 1
            else:
                tracked_dirty.append(line)
    return {
        "commit": commit,
        "branch": branch,
        "tracked_dirty": bool(tracked_dirty),
        "tracked_dirty_entries": tracked_dirty[:20],
        "untracked_count": untracked,
    }


def _write_manifest(out_dir, args, functions, dimensions, instances):
    """Write manifest.json linking campaign output to code + environment."""
    expected_cases = len(functions) * len(dimensions) * len(instances)
    manifest = {
        "kind": "v034_ablation_manifest",
        "schema": "ablation-manifest/1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv[1:],
        "config": {
            "functions": functions,
            "dimensions": dimensions,
            "instances": instances,
            "budget_multiplier": int(args.budget_multiplier),
            "base_seed": int(args.seed),
            "stacked_mode": args.stacked_mode,
            "screen_device": args.screen_device,
            "refinement_backend": args.stacked_refinement_backend,
            "coco_observer": args.coco_observer,
            "seed_formula": "base_seed + 10000*instance + 100*function + dim",
        },
        "arms": dict(SCIENTIFIC_IDS),
        "expected_cases": expected_cases,
        "expected_runs": expected_cases * len(SCIENTIFIC_IDS),
        "git": _git_state(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                name: _package_version(name)
                for name in (
                    "numpy",
                    "scipy",
                    "scikit-learn",
                    "torch",
                    "gpytorch",
                    "botorch",
                    "cocoex",
                )
            },
        },
    }
    path = Path(out_dir) / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


class _ProgressJournal:
    """Append-only fsync'd JSONL journal so a crash cannot lose completed runs."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, payload):
        self._fh.write(
            json.dumps(payload, sort_keys=True, default=float) + "\n"
        )
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass


def _trace_payload(trace):
    """Full per-run record, including the convergence curve that
    write_results does not persist."""
    return {
        "kind": "run",
        "problem_id": trace.problem_id,
        "algorithm": trace.algorithm,
        "dimension": trace.dimension,
        "budget": trace.budget,
        "seed": trace.seed,
        "evaluations": trace.evaluations,
        "best_f": trace.best_f,
        "final_target": trace.final_target,
        "target_hit": bool(trace.target_hit),
        "wall_s": trace.wall_s,
        "best_curve": [float(v) for v in trace.best_curve],
        "metadata": trace.metadata,
    }


def _torch_refinement_engine(base_cls):
    """Attach the same validation-only Torch refinement used by the arena."""
    from botorch.generation.gen import gen_candidates_torch

    from .logei_engine import CandidateSource

    class TorchFreshWeights(base_cls):
        def _refine_informed_starts(
            self,
            cpu_acq,
            starts,
            maxiter,
            timeout_sec,
            seed,
        ):
            del seed
            torch = self.torch
            starts_np = np.asarray(starts, dtype=np.float64)
            if len(starts_np) == 0:
                return None

            initial_conditions = torch.as_tensor(
                starts_np,
                dtype=self.dtype,
                device=self.device,
            ).unsqueeze(1)
            lower_t = torch.zeros(
                self.space.dim,
                dtype=self.dtype,
                device=self.device,
            )
            upper_t = torch.ones(
                self.space.dim,
                dtype=self.dtype,
                device=self.device,
            )

            t0 = time.perf_counter()
            self.fit_diagnostics["refinement_attempts"] += 1

            try:
                candidates, values = gen_candidates_torch(
                    initial_conditions=initial_conditions,
                    acquisition_function=cpu_acq,
                    lower_bounds=lower_t,
                    upper_bounds=upper_t,
                    options={
                        "optimizer_options": {"lr": 0.025},
                        "stopping_criterion_options": {
                            "maxiter": int(maxiter)
                        },
                    },
                    timeout_sec=float(timeout_sec),
                )
                values = values.reshape(-1)
                idx = int(torch.argmax(values).item())
                x01 = (
                    candidates[idx]
                    .detach()
                    .cpu()
                    .double()
                    .numpy()
                    .reshape(-1)
                )
                acq_value = float(
                    values[idx].detach().cpu().double().item()
                )
                if (
                    not np.all(np.isfinite(x01))
                    or not np.isfinite(acq_value)
                ):
                    raise RuntimeError(
                        "Torch refinement returned non-finite result."
                    )
                result = CandidateSource(
                    name="fresh_weights_refined_torch",
                    x01=np.clip(x01, 0.0, 1.0),
                    acquisition_value=acq_value,
                )
            except Exception as exc:
                self.fit_diagnostics["refinement_failures"] += 1
                self.events.append({
                    "event": "torch_refinement_failure",
                    "error": str(exc),
                })
                result = None

            self.timings["refinement_s"] += time.perf_counter() - t0
            return result

    return TorchFreshWeights


def run_stacked_fresh_weights(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
    mode="fast",
    screen_device="auto",
    refinement_backend="torch",
):
    """Validation adapter for the fresh-weight-only ablation arm."""
    from .models import DesignSpace, Variable
    from .stacked_modes import get_stacked_mode

    rec = ObjectiveRecorder(func, lower, upper, budget)
    space = DesignSpace([
        Variable(f"x{i}", float(lo), float(hi), "")
        for i, (lo, hi) in enumerate(zip(rec.lower, rec.upper))
    ])

    def evaluator(x):
        f = rec.evaluate(x)
        return -float(f), True, {"objective_f": float(f)}

    initial = min(
        max(4, 2 * rec.dimension),
        max(2, rec.budget // 3),
        rec.budget - 1,
    )
    initial = max(1, int(initial))

    refinement_backend = str(refinement_backend).lower()
    if refinement_backend not in {"torch", "scipy"}:
        raise ValueError(
            "refinement_backend must be 'torch' or 'scipy'"
        )

    EngineClass = (
        _torch_refinement_engine(FreshWeightsStackedGPBOEngine)
        if refinement_backend == "torch"
        else FreshWeightsStackedGPBOEngine
    )

    engine = EngineClass(
        design_space=space,
        evaluator=evaluator,
        seed=int(seed),
        screen_device=screen_device,
    )

    t0 = time.perf_counter()
    result = engine.run(
        initial_trials=initial,
        smart_trials=(rec.budget - initial),
        verbose=False,
        **get_stacked_mode(mode),
    )
    wall = time.perf_counter() - t0

    return _trace(
        "stacked_fresh_weights_v034",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
        {
            "initial_trials": initial,
            "mode": mode,
            "refinement_backend": refinement_backend,
            "screen_device": result["screen_device"],
            "engine_id": FreshWeightsStackedGPBOEngine.ENGINE_ID,
            "final_weight_rbf": result["final_weight_rbf"],
            "final_weight_matern": result["final_weight_matern"],
            "loo_updates": result["fit_diagnostics"].get(
                "loo_updates", 0
            ),
            "loo_failures": result["fit_diagnostics"].get(
                "loo_failures", 0
            ),
            "rbf_optimized_fits": result["fit_diagnostics"].get(
                "rbf_optimized_fits", 0
            ),
            "matern25_optimized_fits": result["fit_diagnostics"].get(
                "matern25_optimized_fits", 0
            ),
            "rbf_warm_only_fits": result["fit_diagnostics"].get(
                "rbf_warm_only_fits", 0
            ),
            "matern25_warm_only_fits": result["fit_diagnostics"].get(
                "matern25_warm_only_fits", 0
            ),
        },
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--functions", default="1,3,8,12,15,21")
    p.add_argument("--dimensions", default="2")
    p.add_argument("--instances", default="71")
    p.add_argument("--budget-multiplier", type=int, default=20)
    p.add_argument("--seed", type=int, default=123)
    p.add_argument(
        "--stacked-mode",
        choices=["fast", "balanced", "quality"],
        default="fast",
    )
    p.add_argument(
        "--screen-device",
        choices=["cpu", "cuda", "auto"],
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
        default="validation_results/v034_ablation_smoke",
    )
    args = p.parse_args()

    cocoex = _import_coco()

    if args.functions.strip().lower() == "all":
        functions = list(range(1, 25))
    else:
        functions = [
            int(x) for x in args.functions.split(",") if x.strip()
        ]
    dimensions = [
        int(x) for x in args.dimensions.split(",") if x.strip()
    ]
    instances = [
        int(x) for x in args.instances.split(",") if x.strip()
    ]

    runners = {
        "stacked": run_stacked,
        "stacked_fresh_weights": run_stacked_fresh_weights,
        "adaptive_stacked": run_adaptive_stacked,
    }

    out_dir = Path(args.out)
    manifest_path = _write_manifest(
        out_dir, args, functions, dimensions, instances
    )
    journal = _ProgressJournal(out_dir / "progress.jsonl")
    print(f"Manifest: {manifest_path}")
    print(f"Progress journal: {journal.path}")

    observers = {}
    observer_folders = {}
    if args.coco_observer == "on":
        base = _sanitize_observer_name(args.out)
        for key, scientific_id in SCIENTIFIC_IDS.items():
            observer, folder = create_bbob_observer(
                cocoex,
                requested_folder=f"{base}/coco_logs/{key}",
                algorithm_name=scientific_id,
                algorithm_info=(
                    "Engineering AI Core V0.3.4 causal ablation; "
                    f"arena_key={key}; scientific_id={scientific_id}"
                ),
            )
            observers[key] = observer
            observer_folders[key] = folder

    traces = []
    failed_cases = {}
    total = len(functions) * len(dimensions) * len(instances)
    case_no = 0

    try:
        for dim in dimensions:
            for function in functions:
                for instance in instances:
                    case_no += 1
                    budget = int(args.budget_multiplier * dim)

                    try:
                        suite0, p0 = _get_problem(
                            cocoex, function, dim, instance
                        )
                        try:
                            problem_id = str(p0.id)
                            lower = np.asarray(
                                p0.lower_bounds, dtype=np.float64
                            ).copy()
                            upper = np.asarray(
                                p0.upper_bounds, dtype=np.float64
                            ).copy()
                            final_target, target_source = (
                                _resolve_bbob_final_target(p0)
                            )
                        finally:
                            p0.free()
                            suite0.free()
                    except Exception as exc:
                        case_key = (
                            f"bbob_f{function:03d}_i{instance}_d{dim:02d}"
                        )
                        failed_cases.setdefault(case_key, []).append(
                            {"arm": "_setup", "error": repr(exc)}
                        )
                        journal.write({
                            "kind": "failure",
                            "problem_id": case_key,
                            "arm": "_setup",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        })
                        print(
                            f"[{case_no:03d}/{total:03d}] {case_key:24s} "
                            f"SETUP FAILED: {exc!r} — case skipped"
                        )
                        continue

                    seed = (
                        int(args.seed)
                        + 10000 * instance
                        + 100 * function
                        + dim
                    )
                    rows = []

                    for key, runner in runners.items():
                        suite, problem = _get_problem(
                            cocoex, function, dim, instance
                        )
                        t_arm = time.perf_counter()
                        try:
                            if key in observers:
                                problem.observe_with(observers[key])

                            def func(x, _problem=problem):
                                return float(_problem(x))

                            row = runner(
                                problem_id=problem_id,
                                func=func,
                                lower=lower,
                                upper=upper,
                                budget=budget,
                                seed=seed,
                                final_target=final_target,
                                mode=args.stacked_mode,
                                screen_device=args.screen_device,
                                refinement_backend=(
                                    args.stacked_refinement_backend
                                ),
                            )
                            rows.append(row)
                            traces.append(row)
                            journal.write(_trace_payload(row))
                        except Exception as exc:
                            failed_cases.setdefault(
                                problem_id, []
                            ).append(
                                {
                                    "arm": SCIENTIFIC_IDS[key],
                                    "error": repr(exc),
                                }
                            )
                            journal.write({
                                "kind": "failure",
                                "problem_id": problem_id,
                                "arm": SCIENTIFIC_IDS[key],
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "wall_s": (
                                    time.perf_counter() - t_arm
                                ),
                            })
                            print(
                                f"    ARM FAILED {SCIENTIFIC_IDS[key]}"
                                f" on {problem_id}: {exc!r}"
                            )
                        finally:
                            problem.free()
                            suite.free()

                    if rows:
                        best_row = min(rows, key=lambda t: t.best_f)
                        status = (
                            "" if len(rows) == len(runners)
                            else f"  [PARTIAL {len(rows)}/{len(runners)}]"
                        )
                        print(
                            f"[{case_no:03d}/{total:03d}] "
                            f"{problem_id:24s} "
                            f"budget={budget:4d} "
                            f"winner={best_row.algorithm:28s} "
                            f"f={best_row.best_f:.6g} "
                            f"target={target_source}{status}"
                        )

        # Matched-case analysis: any case with a failed arm is excluded
        # from ALL arms in the summary (the per-run evidence stays in
        # progress.jsonl). This keeps the trace matrix rectangular for
        # validate_trace_matrix and keeps every contrast paired.
        matched_traces = [
            t for t in traces if t.problem_id not in failed_cases
        ]
        journal.write({
            "kind": "campaign_complete",
            "completed_runs": len(traces),
            "matched_runs": len(matched_traces),
            "failed_cases": {
                pid: arms for pid, arms in failed_cases.items()
            },
        })

        if failed_cases:
            print("")
            print(
                f"WARNING: {len(failed_cases)} case(s) had failures and "
                "are EXCLUDED from the matched summary "
                "(full detail in progress.jsonl):"
            )
            for pid, arms in failed_cases.items():
                print(f"  {pid}: {[a['arm'] for a in arms]}")

        if matched_traces:
            _, summary_text, csv_path, _, _ = write_results(
                matched_traces, out_dir
            )
            print("")
            print(summary_text)
            print(f"\nCSV: {csv_path}")
        else:
            print("\nNo matched cases completed; no summary written.")

        if observer_folders:
            print("")
            print("=" * 116)
            print("Official COCO observer data — V0.3.4 ablation")
            print("=" * 116)
            for key, folder in observer_folders.items():
                print(f"{key:24s}: {folder}")
            print("=" * 116)

    finally:
        journal.close()
        observers.clear()


if __name__ == "__main__":
    main()
