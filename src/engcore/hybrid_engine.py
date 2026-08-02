from __future__ import annotations

import math
import time

import numpy as np

from .logei_engine import CandidateSource, LogEIGlobalLocalEngine
from .sampling import sobol_points


class HybridLogEIEngine(LogEIGlobalLocalEngine):
    """
    Engineering AI Core V0.2.9

    Global-first hybrid Bayesian Optimization:

        CPU exact GP fit
            ↓
        LogEI / LogCEI
            ↓
        large Sobol global screening
        (GPU when available, chunked)
            ↓
        top acquisition candidates
            ↓
        half-diverse / half-exploitative starts
            ↓
        optional CPU continuous refinement
        seeded by those informed starts
            ↓
        compare discrete vs refined under CPU acquisition
            ↓
        evaluate one point

    Key design choice:
    optimize_acqf is NOT responsible for discovering the global basin from
    random starts. Dense global screening does that first.

    Search modes:
    - discrete: screening only
    - hybrid: screening + continuous refinement
    """

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        screen_device="auto",
        standardized_noise_var=1e-5,
        duplicate_tol=1e-5,
    ):
        # GP fitting and continuous refinement stay on CPU.
        super().__init__(
            design_space=design_space,
            evaluator=evaluator,
            seed=seed,
            device="cpu",
            standardized_noise_var=standardized_noise_var,
            duplicate_tol=duplicate_tol,
        )

        torch = self.torch

        requested = str(screen_device).lower()
        if requested not in {"cpu", "cuda", "auto"}:
            raise ValueError(
                "screen_device must be one of: cpu, cuda, auto"
            )

        if requested == "auto":
            requested = (
                "cuda"
                if torch.cuda.is_available()
                else "cpu"
            )

        if requested == "cuda" and not torch.cuda.is_available():
            requested = "cpu"

        self.screen_device = torch.device(requested)

        # Extend V0.2.8.3 timing / diagnostics rather than discarding them.
        self.timings.update({
            "screen_model_build_s": 0.0,
            "screen_pool_generation_s": 0.0,
            "screen_scoring_s": 0.0,
            "topk_selection_s": 0.0,
            "refinement_s": 0.0,
            "final_acq_compare_s": 0.0,
        })

        self.fit_diagnostics.update({
            "screen_candidates_scored": 0,
            "screen_chunk_reductions": 0,
            "refinement_attempts": 0,
            "refinement_failures": 0,
            "refinement_selected": 0,
            "discrete_selected": 0,
            "stagnation_pulses": 0,
        })

    def _training_tensors_on(self, device):
        """
        Rebuild training tensors on another device using exactly the same
        fixed-noise rule as the CPU fitting model.
        """
        torch = self.torch

        X = torch.as_tensor(
            np.asarray(self.x01_history, dtype=np.float64),
            dtype=self.dtype,
            device=device,
        )

        m = self._constraint_count()

        if m == 0:
            Y_np = np.asarray(
                [[r.score] for r in self.history],
                dtype=np.float64,
            )
        else:
            rows = []
            for result, margins in zip(
                self.history,
                self.margin_history,
            ):
                if len(margins) != m:
                    raise RuntimeError(
                        "Constraint margin dimensionality changed during one run."
                    )
                rows.append([result.score, *margins])
            Y_np = np.asarray(rows, dtype=np.float64)

        Y = torch.as_tensor(
            Y_np,
            dtype=self.dtype,
            device=device,
        )

        if Y.shape[-2] > 1:
            empirical_var = Y.var(
                dim=-2,
                correction=1,
                keepdim=True,
            )
        else:
            empirical_var = torch.ones(
                (1, Y.shape[-1]),
                dtype=self.dtype,
                device=device,
            )

        empirical_var = torch.where(
            torch.isfinite(empirical_var)
            & (empirical_var > 1e-12),
            empirical_var,
            torch.ones_like(empirical_var),
        )

        Yvar = (
            empirical_var
            * self.standardized_noise_var
        ).expand_as(Y).clone()

        return X, Y, Yvar

    def _clone_fitted_model_to_screen_device(self, cpu_model):
        """
        Build a fresh SingleTaskGP on the screening device and load the
        already-fitted CPU model state.

        We avoid relying on Module.to(...) to migrate ExactGP train_inputs.
        """
        if self.screen_device.type == "cpu":
            return cpu_model

        t0 = time.perf_counter()

        X, Y, Yvar = self._training_tensors_on(
            self.screen_device
        )

        screen_model = self._make_model(
            X=X,
            Y=Y,
            Yvar=Yvar,
        )

        screen_model.load_state_dict(
            cpu_model.state_dict(),
            strict=True,
        )
        screen_model.eval()
        screen_model.likelihood.eval()

        self.torch.cuda.synchronize()
        self.timings["screen_model_build_s"] += (
            time.perf_counter() - t0
        )

        return screen_model

    def _acq_value_cpu(self, acq, x01):
        torch = self.torch

        X = torch.as_tensor(
            np.asarray(x01, dtype=np.float64),
            dtype=self.dtype,
            device=self.device,
        ).reshape(1, 1, -1)

        with torch.no_grad():
            value = acq(X).reshape(-1)[0]

        return float(
            value.detach().cpu().item()
        )

    def _score_global_pool(
        self,
        acq,
        pool,
        chunk_size,
        min_chunk_size=128,
    ):
        """
        Score a full-domain Sobol pool in bounded chunks.

        This deliberately mirrors the proven discrete-GPU strategy while using
        BoTorch LogEI / LogCEI rather than the old manual EI formula.
        """
        import gpytorch

        torch = self.torch
        pool = np.asarray(pool, dtype=np.float64)

        scores = np.full(
            len(pool),
            -np.inf,
            dtype=np.float64,
        )

        history = (
            np.asarray(self.x01_history, dtype=np.float64)
            if self.x01_history
            else None
        )

        current_chunk = int(chunk_size)
        start = 0
        t0 = time.perf_counter()

        while start < len(pool):
            end = min(
                start + current_chunk,
                len(pool),
            )
            block_np = pool[start:end]

            valid = np.ones(
                len(block_np),
                dtype=bool,
            )

            if history is not None and len(history):
                # Work chunk-by-chunk so duplicate protection never allocates
                # a candidate_pool × history matrix for the whole pool.
                distances = np.linalg.norm(
                    block_np[:, None, :]
                    - history[None, :, :],
                    axis=2,
                )
                valid = (
                    np.min(distances, axis=1)
                    > self.duplicate_tol
                )

            if not np.any(valid):
                start = end
                continue

            try:
                valid_np = block_np[valid]

                X = torch.as_tensor(
                    valid_np,
                    dtype=self.dtype,
                    device=self.screen_device,
                ).unsqueeze(-2)

                with (
                    torch.no_grad(),
                    gpytorch.settings.fast_pred_var(),
                ):
                    values = acq(X).reshape(-1)

                block_scores = (
                    values.detach()
                    .to("cpu")
                    .double()
                    .numpy()
                )

                local_positions = np.flatnonzero(valid)
                scores[
                    start + local_positions
                ] = block_scores

                if self.screen_device.type == "cuda":
                    torch.cuda.synchronize()

                self.fit_diagnostics[
                    "screen_candidates_scored"
                ] += len(valid_np)

                del X, values

                start = end

            except RuntimeError as exc:
                is_oom = (
                    self.screen_device.type == "cuda"
                    and "out of memory" in str(exc).lower()
                )

                if (
                    is_oom
                    and current_chunk
                    > int(min_chunk_size)
                ):
                    current_chunk = max(
                        int(min_chunk_size),
                        current_chunk // 2,
                    )
                    self.fit_diagnostics[
                        "screen_chunk_reductions"
                    ] += 1
                    torch.cuda.empty_cache()
                    continue

                raise

        self.timings["screen_scoring_s"] += (
            time.perf_counter() - t0
        )

        return scores

    @staticmethod
    def _select_informed_starts(
        pool,
        scores,
        top_k,
        diversity_radius,
    ):
        """
        Preserve both exploitation and basin coverage.

        - best acquisition candidate is always retained
        - roughly half the starts are greedily diverse
        - remaining starts are filled by pure acquisition rank

        This avoids forcing all starts to be far apart while also preventing
        all starts collapsing into one tiny region.
        """
        pool = np.asarray(pool, dtype=np.float64)
        scores = np.asarray(scores, dtype=np.float64)

        finite = np.flatnonzero(np.isfinite(scores))
        if len(finite) == 0:
            raise RuntimeError(
                "Global screening produced no finite acquisition values."
            )

        k = min(
            int(top_k),
            len(finite),
        )

        preselect = min(
            len(finite),
            max(k * 16, 128),
        )

        finite_scores = scores[finite]

        if preselect < len(finite):
            rel = np.argpartition(
                finite_scores,
                -preselect,
            )[-preselect:]
            candidate_idx = finite[rel]
        else:
            candidate_idx = finite

        candidate_idx = candidate_idx[
            np.argsort(
                scores[candidate_idx]
            )[::-1]
        ]

        chosen = [int(candidate_idx[0])]
        diverse_target = max(
            1,
            min(k, (k + 1) // 2),
        )

        # Diverse half.
        for idx in candidate_idx[1:]:
            if len(chosen) >= diverse_target:
                break

            x = pool[int(idx)]
            existing = pool[np.asarray(chosen)]

            distance = float(np.min(
                np.linalg.norm(
                    existing - x[None, :],
                    axis=1,
                )
            ))

            if distance >= float(diversity_radius):
                chosen.append(int(idx))

        # Exploitative half.
        if len(chosen) < k:
            used = set(chosen)
            for idx in candidate_idx:
                idx = int(idx)
                if idx in used:
                    continue
                chosen.append(idx)
                used.add(idx)
                if len(chosen) >= k:
                    break

        chosen = np.asarray(
            chosen[:k],
            dtype=int,
        )

        return (
            pool[chosen].copy(),
            scores[chosen].copy(),
        )

    def _refine_informed_starts(
        self,
        cpu_acq,
        starts,
        maxiter,
        timeout_sec,
        seed,
    ):
        """
        Refine only globally informed starts.

        No raw/random acquisition initialization is performed here.
        """
        from botorch.optim import optimize_acqf
        from botorch.utils.sampling import manual_seed

        torch = self.torch

        starts = np.asarray(
            starts,
            dtype=np.float64,
        )

        if len(starts) == 0:
            return None

        initial_conditions = torch.as_tensor(
            starts,
            dtype=self.dtype,
            device=self.device,
        ).unsqueeze(1)

        bounds = self._bounds_tensor(
            np.zeros(self.space.dim),
            np.ones(self.space.dim),
        )

        t0 = time.perf_counter()

        self.fit_diagnostics[
            "refinement_attempts"
        ] += 1

        try:
            with manual_seed(int(seed)):
                candidate, value = optimize_acqf(
                    acq_function=cpu_acq,
                    bounds=bounds,
                    q=1,
                    num_restarts=len(starts),
                    raw_samples=None,
                    batch_initial_conditions=(
                        initial_conditions
                    ),
                    options={
                        "maxiter": int(maxiter),
                    },
                    timeout_sec=float(timeout_sec),
                    return_best_only=True,
                    retry_on_optimization_warning=False,
                )

            x01 = (
                candidate.detach()
                .cpu()
                .double()
                .numpy()
                .reshape(-1)
            )
            acq_value = float(
                value.detach()
                .cpu()
                .double()
                .reshape(-1)[0]
                .item()
            )

            if not np.all(np.isfinite(x01)):
                raise RuntimeError(
                    "Refinement returned non-finite X."
                )

            if not math.isfinite(acq_value):
                raise RuntimeError(
                    "Refinement returned non-finite acquisition value."
                )

            result = CandidateSource(
                name="refined",
                x01=np.clip(
                    x01,
                    0.0,
                    1.0,
                ),
                acquisition_value=acq_value,
            )

        except Exception as exc:
            self.fit_diagnostics[
                "refinement_failures"
            ] += 1
            self.events.append({
                "event": "refinement_failure",
                "error": str(exc),
            })
            result = None

        self.timings["refinement_s"] += (
            time.perf_counter() - t0
        )

        return result

    def run(
        self,
        initial_trials=12,
        smart_trials=68,
        search_mode="hybrid",
        refit_interval=4,
        screen_pool=100_000,
        screen_chunk_size=2048,
        top_k=12,
        refinement_top_k=8,
        diversity_radius=0.035,
        refinement_maxiter=60,
        refinement_timeout_sec=3.0,
        stagnation_trigger=6,
        pulse_interval=6,
        pulse_screen_pool=250_000,
        pulse_top_k=20,
        pulse_refinement_top_k=12,
        pulse_refinement_maxiter=100,
        pulse_refinement_timeout_sec=5.0,
        verbose=False,
    ):
        if search_mode not in {
            "discrete",
            "hybrid",
        }:
            raise ValueError(
                "search_mode must be discrete or hybrid"
            )

        initial = sobol_points(
            int(initial_trials),
            self.space.dim,
            self.seed,
        )

        for p in initial:
            self._evaluate01(p)

        total_steps = int(smart_trials)
        best = self._best_feasible_score()
        stagnation = 0

        for step in range(total_steps):
            iter_t0 = time.perf_counter()

            pulse = (
                stagnation >= int(stagnation_trigger)
                and (
                    stagnation - int(stagnation_trigger)
                )
                % max(1, int(pulse_interval))
                == 0
            )

            if pulse:
                self.fit_diagnostics[
                    "stagnation_pulses"
                ] += 1

            optimize_model = (
                step == 0
                or int(refit_interval) <= 1
                or step % int(refit_interval) == 0
                or pulse
            )

            # Fit on CPU.
            cpu_model = self._fit_model(
                optimize=optimize_model
            )
            cpu_acq, acquisition_mode = (
                self._build_acquisition(
                    cpu_model
                )
            )

            # Clone already-fitted GP to GPU for bulk global scoring.
            screen_model = (
                self._clone_fitted_model_to_screen_device(
                    cpu_model
                )
            )

            if screen_model is cpu_model:
                screen_acq = cpu_acq
            else:
                screen_acq, _ = (
                    self._build_acquisition(
                        screen_model
                    )
                )

            active_pool = (
                int(pulse_screen_pool)
                if pulse
                else int(screen_pool)
            )
            active_top_k = (
                int(pulse_top_k)
                if pulse
                else int(top_k)
            )
            active_refine_k = (
                int(pulse_refinement_top_k)
                if pulse
                else int(refinement_top_k)
            )
            active_refine_maxiter = (
                int(pulse_refinement_maxiter)
                if pulse
                else int(refinement_maxiter)
            )
            active_refine_timeout = (
                float(
                    pulse_refinement_timeout_sec
                )
                if pulse
                else float(
                    refinement_timeout_sec
                )
            )

            # Deterministic full-domain Sobol pool.
            t0 = time.perf_counter()
            pool = sobol_points(
                active_pool,
                self.space.dim,
                self.seed
                + 100_000
                + step,
            )
            self.timings[
                "screen_pool_generation_s"
            ] += time.perf_counter() - t0

            scores = self._score_global_pool(
                acq=screen_acq,
                pool=pool,
                chunk_size=int(
                    screen_chunk_size
                ),
            )

            t0 = time.perf_counter()
            starts, start_scores = (
                self._select_informed_starts(
                    pool=pool,
                    scores=scores,
                    top_k=active_top_k,
                    diversity_radius=float(
                        diversity_radius
                    ),
                )
            )
            self.timings["topk_selection_s"] += (
                time.perf_counter() - t0
            )

            # Candidate 1: best full-domain discrete screen candidate.
            discrete = CandidateSource(
                name=(
                    "gpu_discrete_pulse"
                    if pulse
                    else "gpu_discrete"
                ),
                x01=starts[0].copy(),
                acquisition_value=float(
                    start_scores[0]
                ),
            )

            # Score final decisions under the same CPU acquisition.
            t0 = time.perf_counter()
            discrete.acquisition_value = (
                self._acq_value_cpu(
                    cpu_acq,
                    discrete.x01,
                )
            )
            self.timings[
                "final_acq_compare_s"
            ] += time.perf_counter() - t0

            chosen = discrete

            # Candidate 2: continuously refine the best globally-informed starts.
            if search_mode == "hybrid":
                refine_count = min(
                    active_refine_k,
                    len(starts),
                )

                refined = (
                    self._refine_informed_starts(
                        cpu_acq=cpu_acq,
                        starts=starts[
                            :refine_count
                        ],
                        maxiter=(
                            active_refine_maxiter
                        ),
                        timeout_sec=(
                            active_refine_timeout
                        ),
                        seed=(
                            self.seed
                            + 900_000
                            + step
                        ),
                    )
                )

                if refined is not None:
                    t0 = time.perf_counter()
                    refined.acquisition_value = (
                        self._acq_value_cpu(
                            cpu_acq,
                            refined.x01,
                        )
                    )
                    self.timings[
                        "final_acq_compare_s"
                    ] += (
                        time.perf_counter()
                        - t0
                    )

                    # If refinement converges back onto an evaluated point,
                    # preserve the valid global discrete candidate.
                    if (
                        not self._is_duplicate(
                            refined.x01
                        )
                        and refined.acquisition_value
                        > discrete.acquisition_value
                        + 1e-12
                    ):
                        chosen = refined
                        self.fit_diagnostics[
                            "refinement_selected"
                        ] += 1
                    else:
                        self.fit_diagnostics[
                            "discrete_selected"
                        ] += 1
                else:
                    self.fit_diagnostics[
                        "discrete_selected"
                    ] += 1

            else:
                self.fit_diagnostics[
                    "discrete_selected"
                ] += 1

            # Screening already excludes prior observations, but retain a final
            # guard against numerical / refinement convergence duplicates.
            if self._is_duplicate(chosen.x01):
                self.fit_diagnostics[
                    "duplicate_candidates"
                ] += 1

                replacement = None
                for x, value in zip(
                    starts[1:],
                    start_scores[1:],
                ):
                    if not self._is_duplicate(x):
                        replacement = CandidateSource(
                            name=(
                                "screen_duplicate_recovery"
                            ),
                            x01=x.copy(),
                            acquisition_value=float(
                                value
                            ),
                        )
                        break

                if replacement is None:
                    raise RuntimeError(
                        "All globally screened top candidates duplicate history."
                    )

                chosen = replacement
                self.fit_diagnostics[
                    "duplicate_recoveries"
                ] += 1

            previous_best = best
            result = self._evaluate01(
                chosen.x01
            )
            best = self._best_feasible_score()

            if best > previous_best + 1e-10:
                stagnation = 0
            else:
                stagnation += 1

            iteration_s = (
                time.perf_counter()
                - iter_t0
            )
            self.timings[
                "total_iteration_s"
            ] += iteration_s

            self.events.append({
                "step": step,
                "event": "iteration",
                "acquisition": (
                    acquisition_mode
                ),
                "search_mode": search_mode,
                "source": chosen.name,
                "pulse": bool(pulse),
                "pool": active_pool,
                "top_k": active_top_k,
                "refinement_top_k": (
                    active_refine_k
                    if search_mode == "hybrid"
                    else 0
                ),
                "acquisition_value": float(
                    chosen.acquisition_value
                ),
                "score": float(
                    result.score
                ),
                "feasible": bool(
                    result.feasible
                ),
                "best": float(best),
                "stagnation": int(
                    stagnation
                ),
                "iteration_s": float(
                    iteration_s
                ),
            })

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or pulse
                or step == total_steps - 1
            ):
                print(
                    f"[V0.2.9 {step+1:02d}/{total_steps}] "
                    f"acq={acquisition_mode:<6s} "
                    f"mode={search_mode:<8s} "
                    f"source={chosen.name:<20s} "
                    f"pool={active_pool:<7d} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d} "
                    f"pulse={str(pulse):<5s} "
                    f"iter={iteration_s:.2f}s"
                )

            # Let local refs go out of scope before next GPU model is created.
            if (
                self.screen_device.type == "cuda"
                and screen_model is not cpu_model
            ):
                del screen_acq
                del screen_model

        feasible = [
            r
            for r in self.history
            if r.feasible
        ]

        if not feasible:
            feasible = list(
                self.history
            )

        feasible.sort(
            key=lambda r: r.score,
            reverse=True,
        )

        gpu_memory = {}

        if self.screen_device.type == "cuda":
            gpu_memory = {
                "allocated_mb":
                    self.torch.cuda.memory_allocated(
                        self.screen_device
                    ) / 1024**2,
                "reserved_mb":
                    self.torch.cuda.memory_reserved(
                        self.screen_device
                    ) / 1024**2,
                "max_allocated_mb":
                    self.torch.cuda.max_memory_allocated(
                        self.screen_device
                    ) / 1024**2,
                "max_reserved_mb":
                    self.torch.cuda.max_memory_reserved(
                        self.screen_device
                    ) / 1024**2,
            }

        return {
            "trials_run": len(
                self.history
            ),
            "best": feasible[0],
            "top": feasible[:8],
            "events": list(
                self.events
            ),
            "timings": dict(
                self.timings
            ),
            "fit_diagnostics": dict(
                self.fit_diagnostics
            ),
            "fit_device": "cpu",
            "screen_device": str(
                self.screen_device
            ),
            "gpu_memory": gpu_memory,
        }
