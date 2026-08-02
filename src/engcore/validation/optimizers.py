from __future__ import annotations

import math
import time

import numpy as np

from .problem import ObjectiveRecorder, Trace


def _trace(
    name,
    problem_id,
    recorder,
    seed,
    final_target,
    wall_s,
    metadata=None,
):
    final_target = (
        None
        if final_target is None
        else float(final_target)
    )

    target_hit = bool(
        final_target is not None
        and recorder.best_f <= final_target
    )

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
        metadata=dict(metadata or {}),
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
    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )
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

    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )

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
    """
    Exact-budget DE/rand/1/bin baseline.

    Kept inside the project so the most important evolutionary baseline does
    not depend on an external package and every run consumes the same number
    of black-box evaluations.
    """
    from ..sampling import sobol_points

    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )
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
        + X01 * (
            rec.upper - rec.lower
        )[None, :]
    )
    fitness = np.empty(popsize, dtype=np.float64)

    t0 = time.perf_counter()

    for i in range(popsize):
        fitness[i] = rec.evaluate(pop[i])

    if popsize < 4:
        # Too little budget for a valid DE generation. Fill by random search.
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
        candidates = np.delete(
            np.arange(popsize),
            i,
        )
        a, b, c = rng.choice(
            candidates,
            size=3,
            replace=False,
        )

        mutant = (
            pop[a]
            + float(mutation)
            * (pop[b] - pop[c])
        )
        mutant = np.clip(
            mutant,
            rec.lower,
            rec.upper,
        )

        mask = (
            rng.random(dim)
            < float(crossover)
        )
        mask[
            rng.integers(0, dim)
        ] = True

        trial = np.where(
            mask,
            mutant,
            pop[i],
        )

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

    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )

    init_rng = np.random.default_rng(
        int(seed) + 424242
    )
    init = (
        rec.lower
        + init_rng.random(rec.dimension)
        * (rec.upper - rec.lower)
    )

    # Nevergrad may internally select a SciPy / PRIMA COBYLA path.
    # Current SciPy can emit:
    #
    #   COBYLA: Invalid RHOEND ... it is set to 1e-06
    #
    # This is an upstream self-corrected configuration warning. Capture only
    # that exact family so the arena log stays clean, while preserving and
    # re-emitting every unrelated warning.
    cobyla_rhoend_autocorrections = 0

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        parametrization = ng.p.Array(
            init=init
        ).set_bounds(
            rec.lower,
            rec.upper,
        )

        optimizer = ng.optimizers.NGOpt(
            parametrization=parametrization,
            budget=rec.budget,
            num_workers=1,
        )

        # Nevergrad uses numpy RNG internally; the parametrization owns a
        # RandomState which can be seeded deterministically.
        try:
            parametrization.random_state.seed(
                int(seed)
            )
        except Exception:
            np.random.seed(int(seed))

        t0 = time.perf_counter()

        for _ in range(rec.budget):
            candidate = optimizer.ask()
            value = rec.evaluate(
                candidate.value
            )
            optimizer.tell(
                candidate,
                value,
            )

        wall = time.perf_counter() - t0

    for warning_record in caught:
        message = str(
            warning_record.message
        )

        if (
            "COBYLA: Invalid RHOEND"
            in message
            and "it is set to 1e-06"
            in message
        ):
            cobyla_rhoend_autocorrections += 1
            continue

        # Never hide unrelated third-party warnings.
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
            "cobyla_rhoend_autocorrections":
                int(
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

    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )

    ranges = rec.upper - rec.lower

    center_rng = np.random.default_rng(
        int(seed) + 515151
    )
    center = (
        rec.lower
        + center_rng.random(rec.dimension)
        * ranges
    )

    # pycma uses one scalar sigma plus optional coordinate scales.
    sigma0 = 0.25
    opts = {
        "bounds": [
            rec.lower.tolist(),
            rec.upper.tolist(),
        ],
        "CMA_stds": (
            ranges / max(
                float(np.max(ranges)),
                1e-12,
            )
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
        sigma0 * float(
            np.max(ranges)
        ),
        opts,
    )

    while (
        not es.stop()
        and rec.remaining
        >= es.popsize
    ):
        xs = es.ask()
        ys = [
            rec.evaluate(x)
            for x in xs
        ]
        es.tell(xs, ys)

    # Use the remaining budget exactly, without updating a partial CMA
    # generation. This keeps black-box budget fairness and preserves the valid
    # CMA state.
    if rec.remaining > 0:
        rng = np.random.default_rng(
            int(seed) + 777
        )
        while rec.remaining > 0:
            x = rec.lower + rng.random(
                rec.dimension
            ) * (
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
            "cma_popsize":
                int(es.popsize),
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
            def _refine_informed_starts(self,cpu_acq,starts,maxiter,timeout_sec,seed):
                torch=self.torch
                starts_np=np.asarray(starts,dtype=np.float64)
                if len(starts_np)==0: return None
                initial_conditions=torch.as_tensor(starts_np,dtype=self.dtype,device=self.device).unsqueeze(1)
                lower=torch.zeros(self.space.dim,dtype=self.dtype,device=self.device)
                upper=torch.ones(self.space.dim,dtype=self.dtype,device=self.device)
                t0=time.perf_counter(); self.fit_diagnostics['refinement_attempts']+=1
                try:
                    candidates,values=gen_candidates_torch(
                        initial_conditions=initial_conditions, acquisition_function=cpu_acq,
                        lower_bounds=lower, upper_bounds=upper,
                        options={'optimizer_options':{'lr':0.025},'stopping_criterion_options':{'maxiter':int(maxiter)}},
                        timeout_sec=float(timeout_sec))
                    values=values.reshape(-1); idx=int(torch.argmax(values).item())
                    x01=candidates[idx].detach().cpu().double().numpy().reshape(-1)
                    acq_value=float(values[idx].detach().cpu().double().item())
                    if not np.all(np.isfinite(x01)) or not np.isfinite(acq_value):
                        raise RuntimeError('Torch refinement returned non-finite result.')
                    result=CandidateSource(name='refined_torch',x01=np.clip(x01,0.0,1.0),acquisition_value=acq_value)
                except Exception as exc:
                    self.fit_diagnostics['refinement_failures']+=1
                    self.events.append({'event':'torch_refinement_failure','error':str(exc)})
                    result=None
                self.timings['refinement_s']+=time.perf_counter()-t0
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
    from ..models import (
        Variable,
        DesignSpace,
    )
    from ..stacked_engine import (
        StackedGPBOEngine,
    )
    from ..stacked_modes import (
        get_stacked_mode,
    )

    rec = ObjectiveRecorder(
        func, lower, upper, budget
    )

    space = DesignSpace([
        Variable(
            f"x{i}",
            float(lo),
            float(hi),
            "",
        )
        for i, (lo, hi)
        in enumerate(
            zip(
                rec.lower,
                rec.upper,
            )
        )
    ])

    def evaluator(x):
        f = rec.evaluate(x)
        return (
            -float(f),  # project engines maximize score
            True,
            {"objective_f": float(f)},
        )

    # DOE scales with dimension while retaining enough adaptive budget.
    initial = min(
        max(4, 2 * rec.dimension),
        max(2, rec.budget // 3),
        rec.budget - 1,
    )
    initial = max(
        1,
        int(initial),
    )

    refinement_backend = str(refinement_backend).lower()
    if refinement_backend not in {"torch", "scipy"}:
        raise ValueError("refinement_backend must be 'torch' or 'scipy'")

    EngineClass = (
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
        smart_trials=(
            rec.budget - initial
        ),
        verbose=False,
        **get_stacked_mode(mode),
    )

    wall = time.perf_counter() - t0

    # Engine must consume exactly the objective budget.
    if rec.evaluations != rec.budget:
        raise RuntimeError(
            "Stacked engine budget mismatch: "
            f"{rec.evaluations} != {rec.budget}"
        )

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
            "screen_device":
                result["screen_device"],
            "final_weight_rbf":
                result["final_weight_rbf"],
            "final_weight_matern":
                result["final_weight_matern"],
            "loo_failures":
                result[
                    "fit_diagnostics"
                ]["loo_failures"],
            "refinement_selected":
                result[
                    "fit_diagnostics"
                ]["refinement_selected"],
            "discrete_selected":
                result[
                    "fit_diagnostics"
                ]["discrete_selected"],
        },
    )


ALGORITHMS = {
    "random": run_random,
    "sobol": run_sobol,
    "de": run_de,
    "ngopt": run_ngopt,
    "cmaes": run_cmaes,
    "stacked": run_stacked,
}
