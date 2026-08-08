from __future__ import annotations

import math
import time

import numpy as np

from .problem import ObjectiveRecorder, Trace


def assert_exact_budget(recorder: ObjectiveRecorder, algorithm: str) -> None:
    """
    Central post-run invariant for every Validation Lab adapter.

    Initialization evaluations count toward the budget. Adapters must not
    silently under- or over-consume objective calls.
    """
    if recorder.evaluations != recorder.budget:
        raise RuntimeError(
            f"{algorithm} budget mismatch: "
            f"{recorder.evaluations} != {recorder.budget}"
        )


def _instrument_refinement_timing(base_cls):
    """Behavior-neutral apparatus-layer timing wrapper.

    Subclasses the engine and times each _refine_informed_starts call
    around a plain super() delegation. Adds NO logic, NO RNG interaction,
    and touches no frozen file; it only observes wall-clock durations so
    refinement_s_max can be journaled (timeout-hit audit). Neutrality is
    verified by the full-trajectory golden parity harness.
    """
    class _TimedRefinement(base_cls):
        def _refine_informed_starts(self, *args, **kwargs):
            t0 = time.perf_counter()
            try:
                return super()._refine_informed_starts(*args, **kwargs)
            finally:
                durations = getattr(self, "_refinement_call_s", None)
                if durations is None:
                    durations = []
                    self._refinement_call_s = durations
                durations.append(time.perf_counter() - t0)

    _TimedRefinement.__name__ = f"Timed{base_cls.__name__}"
    return _TimedRefinement


def _refinement_telemetry(result, engine=None):
    """Wall-clock refinement telemetry (timeout-risk observability).

    Observation-only: reads the engine's returned timings and
    fit_diagnostics after the run completes. It cannot detect an
    individual optimize_acqf timeout hit exactly without modifying
    frozen engine code; the registered warning signal is a per-attempt
    mean duration approaching the mode's refinement_timeout_sec.
    """
    timings = result.get("timings", {}) or {}
    diags = result.get("fit_diagnostics", {}) or {}
    attempts = int(diags.get("refinement_attempts", 0))
    total_s = float(timings.get("refinement_s", 0.0))
    telemetry = {
        "refinement_attempts": attempts,
        "refinement_failures": int(
            diags.get("refinement_failures", 0)
        ),
        "refinement_s_total": total_s,
        "refinement_s_mean": (
            (total_s / attempts) if attempts else 0.0
        ),
    }
    durations = getattr(engine, "_refinement_call_s", None)
    if durations:
        telemetry["refinement_calls"] = len(durations)
        telemetry["refinement_s_max"] = float(max(durations))
    return telemetry


def _trace(
    name,
    problem_id,
    recorder,
    seed,
    final_target,
    wall_s,
    metadata=None,
):
    assert_exact_budget(recorder, name)

    final_target = (
        None
        if final_target is None
        else float(final_target)
    )

    target_hit = bool(
        final_target is not None
        and recorder.best_f <= final_target
    )

    trace_metadata = dict(metadata or {})
    trace_metadata.update(recorder.audit_metadata())

    return Trace(
        algorithm=name,
        problem_id=str(problem_id),
        dimension=recorder.dimension,
        budget=recorder.budget,
        seed=int(seed),
        best_f=float(recorder.best_f),
        evaluations=recorder.evaluations,
        values=list(recorder.values),
        best_curve=list(recorder.best_curve),
        final_target=final_target,
        target_hit=target_hit,
        wall_s=float(wall_s),
        metadata=trace_metadata,
    )


def run_random(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
):
    rec = ObjectiveRecorder(func, lower, upper, budget)
    rng = np.random.default_rng(seed)

    t0 = time.perf_counter()
    for _ in range(rec.budget):
        x = rec.lower + rng.random(rec.dimension) * (
            rec.upper - rec.lower
        )
        rec.evaluate(x)
    wall = time.perf_counter() - t0

    return _trace(
        "random",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
    )


def run_sobol(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
):
    from ..sampling import sobol_points

    rec = ObjectiveRecorder(func, lower, upper, budget)

    t0 = time.perf_counter()
    X01 = sobol_points(
        rec.budget,
        rec.dimension,
        int(seed),
    )

    for x01 in X01:
        x = rec.lower + x01 * (
            rec.upper - rec.lower
        )
        rec.evaluate(x)

    wall = time.perf_counter() - t0
    return _trace(
        "sobol",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
    )


def run_de(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
    mutation=0.8,
    crossover=0.9,
):
    """Exact-budget DE/rand/1/bin baseline."""
    from ..sampling import sobol_points

    rec = ObjectiveRecorder(func, lower, upper, budget)
    rng = np.random.default_rng(seed)

    dim = rec.dimension
    popsize = min(
        rec.budget,
        max(8, 4 * dim),
    )

    X01 = sobol_points(
        popsize,
        dim,
        int(seed) + 9001,
    )
    pop = (
        rec.lower[None, :]
        + X01 * (rec.upper - rec.lower)[None, :]
    )
    fitness = np.empty(popsize, dtype=np.float64)

    t0 = time.perf_counter()

    for i in range(popsize):
        fitness[i] = rec.evaluate(pop[i])

    if popsize < 4:
        while rec.remaining > 0:
            x = rec.lower + rng.random(dim) * (
                rec.upper - rec.lower
            )
            rec.evaluate(x)

        wall = time.perf_counter() - t0
        return _trace(
            "de_rand1bin",
            problem_id,
            rec,
            seed,
            final_target,
            wall,
            {"popsize": popsize},
        )

    target_i = 0

    while rec.remaining > 0:
        i = target_i % popsize
        candidates = np.delete(np.arange(popsize), i)
        a, b, c = rng.choice(
            candidates,
            size=3,
            replace=False,
        )

        mutant = pop[a] + float(mutation) * (pop[b] - pop[c])
        mutant = np.clip(mutant, rec.lower, rec.upper)

        mask = rng.random(dim) < float(crossover)
        mask[rng.integers(0, dim)] = True
        trial = np.where(mask, mutant, pop[i])

        f_trial = rec.evaluate(trial)

        if f_trial <= fitness[i]:
            pop[i] = trial
            fitness[i] = f_trial

        target_i += 1

    wall = time.perf_counter() - t0

    return _trace(
        "de_rand1bin",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
        {
            "popsize": int(popsize),
            "mutation": float(mutation),
            "crossover": float(crossover),
        },
    )


def run_ngopt(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
):
    import warnings

    try:
        import nevergrad as ng
    except ImportError as exc:
        raise RuntimeError(
            "Nevergrad is not installed. "
            "Install it with: pip install nevergrad"
        ) from exc

    rec = ObjectiveRecorder(func, lower, upper, budget)

    init_rng = np.random.default_rng(int(seed) + 424242)
    init = (
        rec.lower
        + init_rng.random(rec.dimension)
        * (rec.upper - rec.lower)
    )

    cobyla_rhoend_autocorrections = 0

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        parametrization = ng.p.Array(init=init).set_bounds(
            rec.lower,
            rec.upper,
        )

        # Seed the parametrization before constructing NGOpt. This guarantees
        # constructor-time stochastic choices cannot occur before seeding.
        try:
            parametrization.random_state.seed(int(seed))
        except Exception:
            np.random.seed(int(seed))

        optimizer = ng.optimizers.NGOpt(
            parametrization=parametrization,
            budget=rec.budget,
            num_workers=1,
        )

        t0 = time.perf_counter()

        for _ in range(rec.budget):
            candidate = optimizer.ask()
            value = rec.evaluate(candidate.value)
            optimizer.tell(candidate, value)

        wall = time.perf_counter() - t0

    for warning_record in caught:
        message = str(warning_record.message)

        if (
            "COBYLA: Invalid RHOEND" in message
            and "it is set to 1e-06" in message
        ):
            cobyla_rhoend_autocorrections += 1
            continue

        warnings.warn_explicit(
            message=message,
            category=warning_record.category,
            filename=warning_record.filename,
            lineno=warning_record.lineno,
        )

    return _trace(
        "ngopt",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
        {
            "cobyla_rhoend_autocorrections": int(
                cobyla_rhoend_autocorrections
            ),
        },
    )


def run_cmaes(
    problem_id,
    func,
    lower,
    upper,
    budget,
    seed,
    final_target=None,
):
    try:
        import cma
    except ImportError as exc:
        raise RuntimeError(
            "pycma is not installed. "
            "Install it with: pip install cma"
        ) from exc

    rec = ObjectiveRecorder(func, lower, upper, budget)

    ranges = rec.upper - rec.lower

    center_rng = np.random.default_rng(int(seed) + 515151)
    center = (
        rec.lower
        + center_rng.random(rec.dimension)
        * ranges
    )

    sigma0 = 0.25
    opts = {
        "bounds": [
            rec.lower.tolist(),
            rec.upper.tolist(),
        ],
        "CMA_stds": (
            ranges / max(float(np.max(ranges)), 1e-12)
        ).tolist(),
        "seed": int(seed),
        "maxfevals": int(rec.budget),
        "verb_disp": 0,
        "verbose": -9,
        "eval_final_mean": False,
    }

    t0 = time.perf_counter()

    es = cma.CMAEvolutionStrategy(
        center.tolist(),
        sigma0 * float(np.max(ranges)),
        opts,
    )

    while (
        not es.stop()
        and rec.remaining >= es.popsize
    ):
        xs = es.ask()
        ys = [rec.evaluate(x) for x in xs]
        es.tell(xs, ys)

    # Preserve exact budget but make the non-CMA tail explicit in metadata.
    random_tail_evaluations = int(rec.remaining)
    if rec.remaining > 0:
        rng = np.random.default_rng(int(seed) + 777)
        while rec.remaining > 0:
            x = rec.lower + rng.random(rec.dimension) * (
                rec.upper - rec.lower
            )
            rec.evaluate(x)

    wall = time.perf_counter() - t0

    return _trace(
        "cmaes",
        problem_id,
        rec,
        seed,
        final_target,
        wall,
        {
            "cma_popsize": int(es.popsize),
            "random_tail_evaluations": random_tail_evaluations,
        },
    )


class _TorchRefinementStackedGPBOEngine:
    """Validation-only stacked engine using BoTorch torch refinement."""

    @staticmethod
    def build():
        import time

        import numpy as np
        from botorch.generation.gen import gen_candidates_torch

        from ..logei_engine import CandidateSource
        from ..stacked_engine import StackedGPBOEngine

        class TorchRefinementEngine(StackedGPBOEngine):
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
                lower = torch.zeros(
                    self.space.dim,
                    dtype=self.dtype,
                    device=self.device,
                )
                upper = torch.ones(
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
                        lower_bounds=lower,
                        upper_bounds=upper,
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
                        name="refined_torch",
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
                self.timings["refinement_s"] += (
                    time.perf_counter() - t0
                )
                return result

        return TorchRefinementEngine


def run_stacked(
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
    from ..models import DesignSpace, Variable
    from ..stacked_engine import StackedGPBOEngine
    from ..stacked_modes import get_stacked_mode

    rec = ObjectiveRecorder(func, lower, upper, budget)

    space = DesignSpace([
        Variable(
            f"x{i}",
            float(lo),
            float(hi),
            "",
        )
        for i, (lo, hi) in enumerate(zip(rec.lower, rec.upper))
    ])

    def evaluator(x):
        f = rec.evaluate(x)
        return (
            -float(f),
            True,
            {"objective_f": float(f)},
        )

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

    EngineClass = _instrument_refinement_timing(
        _TorchRefinementStackedGPBOEngine.build()
        if refinement_backend == "torch"
        else StackedGPBOEngine
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
        "stacked_v0301",
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
            "final_weight_rbf": result["final_weight_rbf"],
            "final_weight_matern": result["final_weight_matern"],
            "loo_failures": result[
                "fit_diagnostics"
            ]["loo_failures"],
            "refinement_selected": result[
                "fit_diagnostics"
            ]["refinement_selected"],
            "discrete_selected": result[
                "fit_diagnostics"
            ]["discrete_selected"],
            **_refinement_telemetry(result, engine),
        },
    )


def run_adaptive_stacked(
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
    """Validation adapter for adaptive_stacked_v034 research branch."""
    from ..adaptive_stacked_engine import AdaptiveStackedGPBOEngine
    from ..models import DesignSpace, Variable
    from ..stacked_modes import get_stacked_mode

    rec = ObjectiveRecorder(func, lower, upper, budget)

    space = DesignSpace([
        Variable(
            f"x{i}",
            float(lo),
            float(hi),
            "",
        )
        for i, (lo, hi) in enumerate(zip(rec.lower, rec.upper))
    ])

    def evaluator(x):
        f = rec.evaluate(x)
        return (
            -float(f),
            True,
            {"objective_f": float(f)},
        )

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

    if refinement_backend == "torch":
        from botorch.generation.gen import gen_candidates_torch

        from ..logei_engine import CandidateSource

        class _TorchAdaptive(AdaptiveStackedGPBOEngine):
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
                        name="adaptive_refined_torch",
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
                self.timings["refinement_s"] += (
                    time.perf_counter() - t0
                )
                return result

        EngineClass = _instrument_refinement_timing(_TorchAdaptive)
    else:
        EngineClass = _instrument_refinement_timing(
            AdaptiveStackedGPBOEngine
        )

    engine = EngineClass(
        design_space=space,
        evaluator=evaluator,
        seed=int(seed),
        screen_device=screen_device,
        record_diagnostics=True,
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
        "adaptive_stacked_v034",
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
            "engine_id": result["engine_id"],
            "final_weight_rbf": result["final_weight_rbf"],
            "final_weight_matern": result["final_weight_matern"],
            **_refinement_telemetry(result, engine),
            "adaptive_proposals_generated": result[
                "fit_diagnostics"
            ].get("adaptive_proposals_generated", 0),
            "adaptive_proposals_accepted": result[
                "fit_diagnostics"
            ].get("adaptive_proposals_accepted", 0),
            "adaptive_proposals_rejected": result[
                "fit_diagnostics"
            ].get("adaptive_proposals_rejected", 0),
            "adaptive_rescue_search_attempts": result[
                "fit_diagnostics"
            ].get("adaptive_rescue_search_attempts", 0),
            "adaptive_rescue_proposals": result[
                "fit_diagnostics"
            ].get("adaptive_rescue_proposals", 0),
            "adaptive_rescue_accepted": result[
                "fit_diagnostics"
            ].get("adaptive_rescue_accepted", 0),
            "adaptive_forced_refits": result[
                "fit_diagnostics"
            ].get("adaptive_forced_refits", 0),
            "adaptive_policy_updates": result[
                "fit_diagnostics"
            ]["adaptive_policy_updates"],
            "diagnostic_history_len": len(
                result["diagnostic_history"]
            ),
            "arbiter_history_len": len(
                result.get("arbiter_history", [])
            ),
        },
    )


ALGORITHMS = {
    "random": run_random,
    "sobol": run_sobol,
    "de": run_de,
    "ngopt": run_ngopt,
    "cmaes": run_cmaes,
    "stacked": run_stacked,
    "adaptive_stacked": run_adaptive_stacked,
}
