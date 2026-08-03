"""Diagnostic-only: run original smoke and print arbiter stats. Not product code."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engcore.validation.local_suite import make_local_suite
from src.engcore.validation.optimizers import (
    run_adaptive_stacked,
    run_stacked,
)
from src.engcore.models import DesignSpace, Variable
from src.engcore.adaptive_stacked_engine import (
    AdaptiveStackedGPBOEngine,
)
from src.engcore.stacked_modes import get_stacked_mode
from src.engcore.validation.problem import ObjectiveRecorder
import time
from botorch.generation.gen import gen_candidates_torch
from src.engcore.logei_engine import CandidateSource


SEED = 123
BUDGET = 20


def torch_adaptive(problem, func):
    rec = ObjectiveRecorder(
        func, problem.lower, problem.upper, BUDGET
    )
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

    class TorchAdaptive(AdaptiveStackedGPBOEngine):
        def _refine_informed_starts(
            self, cpu_acq, starts, maxiter, timeout_sec, seed
        ):
            torch = self.torch
            starts_np = np.asarray(starts, dtype=np.float64)
            if len(starts_np) == 0:
                return None
            initial_conditions = torch.as_tensor(
                starts_np, dtype=self.dtype, device=self.device
            ).unsqueeze(1)
            lower_t = torch.zeros(
                self.space.dim, dtype=self.dtype, device=self.device
            )
            upper_t = torch.ones(
                self.space.dim, dtype=self.dtype, device=self.device
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
                result = CandidateSource(
                    name="adaptive_refined_torch",
                    x01=np.clip(x01, 0.0, 1.0),
                    acquisition_value=acq_value,
                )
            except Exception:
                self.fit_diagnostics["refinement_failures"] += 1
                result = None
            self.timings["refinement_s"] += time.perf_counter() - t0
            return result

    eng = TorchAdaptive(
        design_space=space,
        evaluator=evaluator,
        seed=SEED,
        screen_device="cpu",
        record_diagnostics=True,
    )
    t0 = time.perf_counter()
    result = eng.run(
        initial_trials=initial,
        smart_trials=BUDGET - initial,
        verbose=False,
        **get_stacked_mode("fast"),
    )
    wall = time.perf_counter() - t0
    return rec, result, wall


def main():
    problems = [
        p
        for p in make_local_suite(dimensions=(2,), instances=(1,))
    ]
    print("SMOKE + ARBITER STATS")
    for p in problems:
        # stacked via adapter
        srow = run_stacked(
            problem_id=p.problem_id,
            func=p.func,
            lower=p.lower,
            upper=p.upper,
            budget=BUDGET,
            seed=SEED,
            mode="fast",
            screen_device="cpu",
            refinement_backend="torch",
        )
        rec, result, wall = torch_adaptive(p, p.func)
        best_a = float(rec.best_f)
        fd = result["fit_diagnostics"]
        ah = result["arbiter_history"]
        first_acc = None
        for row in ah:
            if row.get("arbiter_decision"):
                first_acc = row["evaluation"] + 1  # next eval?
                # evaluation field is len(history) before eval
                first_acc = int(row["evaluation"]) + 1
                break
        print(
            f"{p.problem_id:18s} stacked={srow.best_f:.6g} "
            f"adaptive={best_a:.6g} "
            f"gen={fd.get('adaptive_proposals_generated',0)} "
            f"acc={fd.get('adaptive_proposals_accepted',0)} "
            f"rej={fd.get('adaptive_proposals_rejected',0)} "
            f"rescue_g={fd.get('adaptive_rescue_proposals',0)} "
            f"rescue_a={fd.get('adaptive_rescue_accepted',0)} "
            f"forced_refit={fd.get('adaptive_forced_refits',0)} "
            f"first_accept_eval={first_acc} "
            f"wall_a={wall:.2f}s wall_s={srow.wall_s:.2f}s "
            f"obj={rec.evaluations}"
        )


if __name__ == "__main__":
    main()
