from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from .models import ExperimentResult
from .sampling import sobol_points


@dataclass
class CandidateSource:
    name: str
    x01: np.ndarray
    acquisition_value: float


class LogEIGlobalLocalEngine:
    """
    Engineering AI Core V0.2.9.1

    Goals of this release:
    - deterministic / reproducible optimize_acqf initialisation
    - CPU-first exact-GP + analytic LogEI for the current low-dimensional regime
    - safe GP fit rollback
    - acquisition timeout
    - duplicate-candidate protection
    - fallback guard only when needed
    - adaptive compute pulse on sustained stagnation
    - no acquisition-function switching
    - no mandatory local regions
    """

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        device="cpu",
        standardized_noise_var=1e-5,
        duplicate_tol=1e-5,
        noise_mode="fixed",
        kernel_name="rbf",
    ):
        import torch

        self.space = design_space
        self.evaluator = evaluator
        self.seed = int(seed)
        self.standardized_noise_var = float(standardized_noise_var)
        self.duplicate_tol = float(duplicate_tol)

        self.noise_mode = str(noise_mode).lower()
        if self.noise_mode not in {"fixed", "learned"}:
            raise ValueError("noise_mode must be 'fixed' or 'learned'")

        self.kernel_name = str(kernel_name).lower()
        if self.kernel_name not in {"rbf", "matern25"}:
            raise ValueError("kernel_name must be 'rbf' or 'matern25'")

        requested = str(device).lower()
        if requested not in {"cpu", "cuda", "auto"}:
            raise ValueError("device must be one of: cpu, cuda, auto")

        if requested == "auto":
            # Current profiling showed CPU faster for q=1, d=4 optimize_acqf.
            # Keep AUTO conservative for the current low-dimensional regime.
            requested = "cpu" if self.space.dim <= 8 else (
                "cuda" if torch.cuda.is_available() else "cpu"
            )

        if requested == "cuda" and not torch.cuda.is_available():
            requested = "cpu"

        self.torch = torch
        self.device = torch.device(requested)
        self.dtype = torch.float64

        self.history = []
        self.x01_history = []
        self.margin_history = []
        self.events = []

        self.timings = {
            "evaluation_s": 0.0,
            "tensor_build_s": 0.0,
            "model_build_s": 0.0,
            "model_fit_s": 0.0,
            "acquisition_build_s": 0.0,
            "global_opt_s": 0.0,
            "local_opt_s": 0.0,
            "fallback_guard_s": 0.0,
            "duplicate_recovery_s": 0.0,
            "total_iteration_s": 0.0,
        }

        self.fit_diagnostics = {
            "optimized_fits": 0,
            "warm_only_fits": 0,
            "fit_failures": 0,
            "fit_rollbacks": 0,
            "invalid_learned_parameter_failures": 0,
            "global_opt_failures": 0,
            "global_opt_timeouts_or_errors": 0,
            "local_opt_failures": 0,
            "fallback_guard_uses": 0,
            "duplicate_candidates": 0,
            "duplicate_recoveries": 0,
            "stagnation_pulses": 0,
        }

        # Known-good hyperparameter subset only.
        self._warm_state = {}

    def _sync(self):
        if self.device.type == "cuda":
            self.torch.cuda.synchronize()

    def _evaluate01(self, x01):
        t0 = time.perf_counter()

        x01 = np.asarray(x01, dtype=float)
        x = self.space.denormalize(x01)
        score, feasible, metadata = self.evaluator(x)
        metadata = dict(metadata)
        margins = list(metadata.get("constraint_margins", []))

        self.timings["evaluation_s"] += time.perf_counter() - t0

        result = ExperimentResult(
            x=x.copy(),
            score=float(score),
            feasible=bool(feasible),
            metadata=metadata,
        )
        self.history.append(result)
        self.x01_history.append(x01.copy())
        self.margin_history.append([float(v) for v in margins])
        return result

    def _constraint_count(self):
        for margins in self.margin_history:
            if margins:
                return len(margins)
        return 0

    def _training_tensors(self):
        """
        Standardize transforms Y and Yvar.

        We therefore choose raw per-output fixed noise so transformed variance
        is approximately standardized_noise_var for every outcome.
        """
        torch = self.torch
        t0 = time.perf_counter()

        X = torch.as_tensor(
            np.asarray(self.x01_history, dtype=np.float64),
            dtype=self.dtype,
            device=self.device,
        )

        m = self._constraint_count()

        if m == 0:
            Y_np = np.asarray(
                [[r.score] for r in self.history],
                dtype=np.float64,
            )
        else:
            rows = []
            for result, margins in zip(self.history, self.margin_history):
                if len(margins) != m:
                    raise RuntimeError(
                        "Constraint margin dimensionality changed during one run."
                    )
                rows.append([result.score, *margins])
            Y_np = np.asarray(rows, dtype=np.float64)

        Y = torch.as_tensor(
            Y_np,
            dtype=self.dtype,
            device=self.device,
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
                device=self.device,
            )

        empirical_var = torch.where(
            torch.isfinite(empirical_var) & (empirical_var > 1e-12),
            empirical_var,
            torch.ones_like(empirical_var),
        )

        Yvar = (
            empirical_var * self.standardized_noise_var
        ).expand_as(Y).clone()

        self.timings["tensor_build_s"] += time.perf_counter() - t0
        return X, Y, Yvar

    @staticmethod
    def _invalid_learned_parameters(model):
        """
        Return actual LEARNABLE parameters containing NaN/Inf.

        Do not inspect every state_dict buffer here. GPyTorch constraints store
        metadata such as lower/upper bounds in buffers, and unbounded
        constraints may legitimately contain +/-inf. Those are not learned
        model parameters and must not invalidate a successful GP fit.
        """
        import torch

        invalid = []

        for name, parameter in model.named_parameters():
            if not torch.isfinite(parameter.detach()).all():
                invalid.append(name)

        return invalid

    @staticmethod
    def _clone_state_dict(model):
        return {
            key: value.detach().clone()
            for key, value in model.state_dict().items()
        }

    def _capture_warm_state(self, model):
        keep = {}
        for key, value in model.state_dict().items():
            if (
                key.startswith("covar_module.")
                or key.startswith("mean_module.")
                or key.startswith("likelihood.")
            ):
                keep[key] = value.detach().clone()
        self._warm_state = keep

    def _apply_warm_state(self, model):
        if not self._warm_state:
            return False

        current = model.state_dict()
        applied = False

        for key, value in self._warm_state.items():
            if key in current and current[key].shape == value.shape:
                current[key] = value.to(
                    device=current[key].device,
                    dtype=current[key].dtype,
                )
                applied = True

        model.load_state_dict(current, strict=False)
        return applied


    def _make_model(self, X, Y, Yvar=None):
        """
        Central model factory so CPU fitting and GPU screening use the exact
        same GP structure.

        rbf:
            BoTorch SingleTaskGP default covariance module.

        matern25:
            Explicit ARD Matern-5/2 covariance for diagnostic ablation.

        fixed:
            Use scale-aware train_Yvar.

        learned:
            Omit train_Yvar and let SingleTaskGP learn observation noise,
            matching the successful Legacy surrogate more closely.
        """
        from botorch.models import SingleTaskGP
        from botorch.models.transforms import Standardize

        kwargs = {
            "train_X": X,
            "train_Y": Y,
            "outcome_transform": Standardize(m=Y.shape[-1]),
        }

        if self.noise_mode == "fixed":
            if Yvar is None:
                raise RuntimeError("fixed noise mode requires Yvar")
            kwargs["train_Yvar"] = Yvar

        if self.kernel_name == "matern25":
            from gpytorch.kernels import MaternKernel, ScaleKernel

            kwargs["covar_module"] = ScaleKernel(
                MaternKernel(
                    nu=2.5,
                    ard_num_dims=self.space.dim,
                )
            )

        model = SingleTaskGP(**kwargs).to(
            device=X.device,
            dtype=self.dtype,
        )
        return model

    def _fit_model(self, optimize=True):
        from botorch.fit import fit_gpytorch_mll
        from gpytorch.mlls import ExactMarginalLogLikelihood

        X, Y, Yvar = self._training_tensors()

        t0 = time.perf_counter()
        model = self._make_model(
            X=X,
            Y=Y,
            Yvar=Yvar,
        )

        self._apply_warm_state(model)

        mll = ExactMarginalLogLikelihood(
            model.likelihood,
            model,
        ).to(device=self.device, dtype=self.dtype)

        # Checkpoint BEFORE the optimizer touches parameters.
        rollback_state = self._clone_state_dict(model)

        self._sync()
        self.timings["model_build_s"] += time.perf_counter() - t0

        t0 = time.perf_counter()
        fit_ok = True

        if optimize:
            try:
                fit_gpytorch_mll(mll)

                invalid_parameters = self._invalid_learned_parameters(
                    model
                )
                if invalid_parameters:
                    raise RuntimeError(
                        "GP fit produced NaN/Inf in learned parameter(s): "
                        + ", ".join(invalid_parameters)
                    )

                self.fit_diagnostics["optimized_fits"] += 1
            except Exception as exc:
                fit_ok = False
                self.fit_diagnostics["fit_failures"] += 1
                self.fit_diagnostics["fit_rollbacks"] += 1

                if "NaN/Inf in learned parameter" in str(exc):
                    self.fit_diagnostics[
                        "invalid_learned_parameter_failures"
                    ] += 1

                model.load_state_dict(rollback_state, strict=True)

                self.events.append({
                    "event": "fit_failure_rollback",
                    "error": str(exc),
                })
        else:
            self.fit_diagnostics["warm_only_fits"] += 1

        self._sync()
        self.timings["model_fit_s"] += time.perf_counter() - t0

        model.eval()
        model.likelihood.eval()

        # Never let a failed / partially modified fit poison future warm starts.
        if fit_ok or not optimize:
            self._capture_warm_state(model)

        return model

    def _observed_feasible_mask(self):
        m = self._constraint_count()

        if m == 0:
            return np.ones(len(self.history), dtype=bool)

        arr = np.asarray(self.margin_history, dtype=float)
        return np.all(arr >= 0.0, axis=1)

    def _best_feasible_score(self):
        feasible = [
            r.score for r in self.history
            if r.feasible
        ]
        if feasible:
            return float(max(feasible))
        return float(max(r.score for r in self.history))

    def _build_acquisition(self, model):
        from botorch.acquisition.analytic import (
            LogConstrainedExpectedImprovement,
            LogExpectedImprovement,
            LogProbabilityOfFeasibility,
        )

        t0 = time.perf_counter()
        m = self._constraint_count()

        if m == 0:
            acq = LogExpectedImprovement(
                model=model,
                best_f=float(max(r.score for r in self.history)),
                maximize=True,
            )
            mode = "LogEI"
        else:
            constraints = {
                i: (0.0, None)
                for i in range(1, m + 1)
            }
            feasible_mask = self._observed_feasible_mask()

            if np.any(feasible_mask):
                scores = np.asarray(
                    [r.score for r in self.history],
                    dtype=float,
                )
                acq = LogConstrainedExpectedImprovement(
                    model=model,
                    best_f=float(np.max(scores[feasible_mask])),
                    objective_index=0,
                    constraints=constraints,
                    maximize=True,
                )
                mode = "LogCEI"
            else:
                acq = LogProbabilityOfFeasibility(
                    model=model,
                    constraints=constraints,
                )
                mode = "LogPF"

        self.timings["acquisition_build_s"] += time.perf_counter() - t0
        return acq, mode

    def _bounds_tensor(self, low=None, high=None):
        if low is None:
            low = np.zeros(self.space.dim, dtype=float)
        if high is None:
            high = np.ones(self.space.dim, dtype=float)

        return self.torch.as_tensor(
            np.vstack([low, high]),
            dtype=self.dtype,
            device=self.device,
        )

    def _optimize_box(
        self,
        acq,
        low,
        high,
        num_restarts,
        raw_samples,
        maxiter,
        timeout_sec,
        seed,
        label,
    ):
        from botorch.optim import optimize_acqf
        from botorch.utils.sampling import manual_seed

        # BoTorch's initial conditions are stochastic. Make them reproducible.
        with manual_seed(int(seed)):
            candidate, value = optimize_acqf(
                acq_function=acq,
                bounds=self._bounds_tensor(low, high),
                q=1,
                num_restarts=int(num_restarts),
                raw_samples=int(raw_samples),
                options={
                    "maxiter": int(maxiter),
                },
                timeout_sec=(
                    None if timeout_sec is None
                    else float(timeout_sec)
                ),
                return_best_only=True,
                retry_on_optimization_warning=True,
            )

        x01 = (
            candidate.detach()
            .to("cpu")
            .double()
            .numpy()
            .reshape(-1)
        )
        scalar_value = float(
            value.detach()
            .to("cpu")
            .double()
            .reshape(-1)[0]
            .item()
        )

        if not np.all(np.isfinite(x01)):
            raise RuntimeError("Acquisition optimizer returned non-finite X.")
        if not math.isfinite(scalar_value):
            raise RuntimeError(
                "Acquisition optimizer returned non-finite value."
            )

        return CandidateSource(
            name=label,
            x01=np.clip(x01, 0.0, 1.0),
            acquisition_value=scalar_value,
        )

    def _diverse_elites(self, count=1, min_distance=0.12):
        feasible = [
            (i, r.score)
            for i, r in enumerate(self.history)
            if r.feasible
        ]
        if not feasible:
            feasible = [
                (i, r.score)
                for i, r in enumerate(self.history)
            ]

        feasible.sort(key=lambda t: t[1], reverse=True)
        chosen = []

        for idx, score in feasible:
            p = self.x01_history[idx]

            if not chosen:
                chosen.append((idx, score))
            else:
                centers = np.asarray(
                    [self.x01_history[j] for j, _ in chosen],
                    dtype=float,
                )
                distance = np.min(
                    np.linalg.norm(
                        centers - p[None, :],
                        axis=1,
                    )
                )
                if distance >= min_distance:
                    chosen.append((idx, score))

            if len(chosen) >= count:
                break

        return chosen

    def _local_boxes(self, step, total_steps, count=1):
        if count <= 0:
            return []

        progress = step / max(1, total_steps - 1)
        half_width = float(np.clip(
            0.26 - 0.12 * progress,
            0.12,
            0.26,
        ))

        boxes = []
        for j, (idx, _) in enumerate(self._diverse_elites(count)):
            center = self.x01_history[idx]
            low = np.clip(center - half_width, 0.0, 1.0)
            high = np.clip(center + half_width, 0.0, 1.0)
            boxes.append((j, low, high))

        return boxes

    def _min_history_distance(self, x01):
        if not self.x01_history:
            return float("inf")

        history = np.asarray(self.x01_history, dtype=float)
        return float(np.min(
            np.linalg.norm(
                history - np.asarray(x01, dtype=float)[None, :],
                axis=1,
            )
        ))

    def _is_duplicate(self, x01):
        return self._min_history_distance(x01) <= self.duplicate_tol

    def _discrete_acq_search(
        self,
        acq,
        points,
        seed,
        chunk_size=256,
        exclude_duplicates=True,
        label="fallback_guard",
    ):
        """
        Deterministic, chunked safety search.

        This is NOT the normal candidate generator.
        It is used after optimizer failure or duplicate recovery.
        """
        torch = self.torch

        if points <= 0:
            return None

        X_np = sobol_points(
            int(points),
            self.space.dim,
            int(seed),
        )

        best_value = float("-inf")
        best_x = None

        with torch.no_grad():
            for start in range(0, len(X_np), int(chunk_size)):
                block_np = X_np[start:start + int(chunk_size)]

                if exclude_duplicates and self.x01_history:
                    distances = np.linalg.norm(
                        block_np[:, None, :]
                        - np.asarray(self.x01_history, dtype=float)[None, :, :],
                        axis=2,
                    )
                    keep = np.min(distances, axis=1) > self.duplicate_tol
                    block_np = block_np[keep]

                if len(block_np) == 0:
                    continue

                block = torch.as_tensor(
                    block_np,
                    dtype=self.dtype,
                    device=self.device,
                ).unsqueeze(-2)

                values = acq(block).reshape(-1)
                local_idx = int(torch.argmax(values).item())
                local_value = float(
                    values[local_idx].detach().cpu().item()
                )

                if local_value > best_value:
                    best_value = local_value
                    best_x = block_np[local_idx].copy()

        self._sync()

        if best_x is None:
            return None

        return CandidateSource(
            name=label,
            x01=best_x,
            acquisition_value=best_value,
        )

    def run(
        self,
        initial_trials=12,
        smart_trials=68,
        refit_interval=6,
        global_restarts=12,
        global_raw_samples=256,
        maxiter=100,
        acquisition_timeout_sec=5.0,
        local_regions=0,
        local_restarts=4,
        local_raw_samples=96,
        fallback_guard_points=2048,
        guard_chunk_size=256,
        duplicate_recovery_points=2048,
        stagnation_trigger=6,
        pulse_interval=6,
        pulse_restarts=20,
        pulse_raw_samples=512,
        pulse_maxiter=160,
        pulse_timeout_sec=8.0,
        pulse_local_regions=1,
        verbose=False,
    ):
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

            # One expensive search pulse every `pulse_interval` stagnating steps,
            # rather than running maximum compute every iteration.
            pulse = (
                stagnation >= int(stagnation_trigger)
                and (
                    stagnation - int(stagnation_trigger)
                ) % max(1, int(pulse_interval)) == 0
            )

            if pulse:
                self.fit_diagnostics["stagnation_pulses"] += 1

            optimize_model = (
                step == 0
                or refit_interval <= 1
                or step % int(refit_interval) == 0
                or pulse
            )

            model = self._fit_model(optimize=optimize_model)
            acq, acquisition_mode = self._build_acquisition(model)

            candidates = []

            active_restarts = (
                int(pulse_restarts) if pulse
                else int(global_restarts)
            )
            active_raw = (
                int(pulse_raw_samples) if pulse
                else int(global_raw_samples)
            )
            active_maxiter = (
                int(pulse_maxiter) if pulse
                else int(maxiter)
            )
            active_timeout = (
                float(pulse_timeout_sec) if pulse
                else float(acquisition_timeout_sec)
            )

            # Main full-domain optimization.
            t0 = time.perf_counter()
            try:
                candidates.append(
                    self._optimize_box(
                        acq=acq,
                        low=np.zeros(self.space.dim),
                        high=np.ones(self.space.dim),
                        num_restarts=active_restarts,
                        raw_samples=active_raw,
                        maxiter=active_maxiter,
                        timeout_sec=active_timeout,
                        seed=self.seed + 10_000 * (step + 1),
                        label=(
                            "global_pulse"
                            if pulse else "global"
                        ),
                    )
                )
            except Exception as exc:
                self.fit_diagnostics["global_opt_failures"] += 1
                self.fit_diagnostics[
                    "global_opt_timeouts_or_errors"
                ] += 1
                self.events.append({
                    "step": step,
                    "event": "global_opt_failure",
                    "pulse": bool(pulse),
                    "error": str(exc),
                })

            self._sync()
            self.timings["global_opt_s"] += (
                time.perf_counter() - t0
            )

            # Explicit local challenger is normally OFF.
            # It activates only during a stagnation pulse unless caller asks
            # for always-on local regions.
            active_local_regions = max(
                int(local_regions),
                int(pulse_local_regions) if pulse else 0,
            )

            if active_local_regions > 0:
                t0 = time.perf_counter()

                for j, low, high in self._local_boxes(
                    step,
                    total_steps,
                    count=active_local_regions,
                ):
                    try:
                        candidates.append(
                            self._optimize_box(
                                acq=acq,
                                low=low,
                                high=high,
                                num_restarts=int(local_restarts),
                                raw_samples=int(local_raw_samples),
                                maxiter=min(
                                    int(active_maxiter),
                                    100,
                                ),
                                timeout_sec=min(
                                    float(active_timeout),
                                    5.0,
                                ),
                                seed=(
                                    self.seed
                                    + 10_000 * (step + 1)
                                    + 100 + j
                                ),
                                label=f"local_{j}",
                            )
                        )
                    except Exception as exc:
                        self.fit_diagnostics[
                            "local_opt_failures"
                        ] += 1
                        self.events.append({
                            "step": step,
                            "event": "local_opt_failure",
                            "region": j,
                            "error": str(exc),
                        })

                self._sync()
                self.timings["local_opt_s"] += (
                    time.perf_counter() - t0
                )

            # If every continuous optimization failed, use the deterministic
            # chunked guard.
            if not candidates:
                t0 = time.perf_counter()
                guard = self._discrete_acq_search(
                    acq=acq,
                    points=int(fallback_guard_points),
                    seed=self.seed + 900_000 + step,
                    chunk_size=int(guard_chunk_size),
                    exclude_duplicates=True,
                    label="fallback_guard",
                )
                self._sync()
                self.timings["fallback_guard_s"] += (
                    time.perf_counter() - t0
                )

                if guard is not None:
                    candidates.append(guard)
                    self.fit_diagnostics[
                        "fallback_guard_uses"
                    ] += 1

            if not candidates:
                raise RuntimeError(
                    "No valid acquisition candidate could be generated."
                )

            chosen = max(
                candidates,
                key=lambda c: c.acquisition_value,
            )

            # Do not spend a precious experiment on an already-evaluated point.
            if self._is_duplicate(chosen.x01):
                self.fit_diagnostics["duplicate_candidates"] += 1

                t0 = time.perf_counter()
                replacement = self._discrete_acq_search(
                    acq=acq,
                    points=int(duplicate_recovery_points),
                    seed=self.seed + 950_000 + step,
                    chunk_size=int(guard_chunk_size),
                    exclude_duplicates=True,
                    label="duplicate_recovery",
                )
                self._sync()
                self.timings["duplicate_recovery_s"] += (
                    time.perf_counter() - t0
                )

                if replacement is not None:
                    chosen = replacement
                    self.fit_diagnostics[
                        "duplicate_recoveries"
                    ] += 1

            previous_best = best
            result = self._evaluate01(chosen.x01)
            best = self._best_feasible_score()

            if best > previous_best + 1e-10:
                stagnation = 0
            else:
                stagnation += 1

            iteration_s = time.perf_counter() - iter_t0
            self.timings["total_iteration_s"] += iteration_s

            self.events.append({
                "step": step,
                "event": "iteration",
                "acquisition": acquisition_mode,
                "source": chosen.name,
                "pulse": bool(pulse),
                "restarts": active_restarts,
                "raw_samples": active_raw,
                "acquisition_value": float(
                    chosen.acquisition_value
                ),
                "score": float(result.score),
                "feasible": bool(result.feasible),
                "best": float(best),
                "stagnation": int(stagnation),
                "iteration_s": float(iteration_s),
                "min_history_distance_before_eval": float(
                    self._min_history_distance(chosen.x01)
                    if len(self.x01_history) > 1
                    else float("inf")
                ),
            })

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or pulse
                or step == total_steps - 1
            ):
                print(
                    f"[V0.2.8.2 {step+1:02d}/{total_steps}] "
                    f"acq={acquisition_mode:<6s} "
                    f"source={chosen.name:<18s} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d} "
                    f"pulse={str(pulse):<5s} "
                    f"iter={iteration_s:.2f}s"
                )

        feasible = [
            r for r in self.history
            if r.feasible
        ]
        if not feasible:
            feasible = list(self.history)

        feasible.sort(
            key=lambda r: r.score,
            reverse=True,
        )

        gpu_memory = {}
        if self.device.type == "cuda":
            gpu_memory = {
                "allocated_mb":
                    self.torch.cuda.memory_allocated(
                        self.device
                    ) / 1024**2,
                "reserved_mb":
                    self.torch.cuda.memory_reserved(
                        self.device
                    ) / 1024**2,
                "max_allocated_mb":
                    self.torch.cuda.max_memory_allocated(
                        self.device
                    ) / 1024**2,
                "max_reserved_mb":
                    self.torch.cuda.max_memory_reserved(
                        self.device
                    ) / 1024**2,
            }

        return {
            "trials_run": len(self.history),
            "best": feasible[0],
            "top": feasible[:8],
            "events": list(self.events),
            "timings": dict(self.timings),
            "fit_diagnostics": dict(self.fit_diagnostics),
            "device": str(self.device),
            "gpu_memory": gpu_memory,
        }
