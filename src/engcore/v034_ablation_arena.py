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
import time
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
    total = len(functions) * len(dimensions) * len(instances)
    case_no = 0

    try:
        for dim in dimensions:
            for function in functions:
                for instance in instances:
                    case_no += 1
                    budget = int(args.budget_multiplier * dim)

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
                        finally:
                            problem.free()
                            suite.free()

                    best_row = min(rows, key=lambda t: t.best_f)
                    print(
                        f"[{case_no:03d}/{total:03d}] "
                        f"{problem_id:24s} "
                        f"budget={budget:4d} "
                        f"winner={best_row.algorithm:28s} "
                        f"f={best_row.best_f:.6g} "
                        f"target={target_source}"
                    )

        _, summary_text, csv_path, _, _ = write_results(
            traces, Path(args.out)
        )
        print("")
        print(summary_text)
        print(f"\nCSV: {csv_path}")

        if observer_folders:
            print("")
            print("=" * 116)
            print("Official COCO observer data — V0.3.4 ablation")
            print("=" * 116)
            for key, folder in observer_folders.items():
                print(f"{key:24s}: {folder}")
            print("=" * 116)

    finally:
        observers.clear()


if __name__ == "__main__":
    main()
