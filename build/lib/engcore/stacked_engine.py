from __future__ import annotations

import math
import time

import numpy as np

from .hybrid_engine import HybridLogEIEngine
from .logei_engine import CandidateSource
from .sampling import sobol_points
from .stacked_acquisition import StackedLogAcquisition


class StackedGPBOEngine(HybridLogEIEngine):
    """
    Engineering AI Core V0.3.0.1

    Two-surrogate Bayesian optimization:

        RBF ARD GP
              \
               -> LOO predictive stacking -> Stacked LogEI
              /
        Matern-2.5 ARD GP

    Both members use a small bounded learned nugget in standardized output
    space. The two models therefore differ primarily in covariance smoothness,
    rather than confounding kernel choice with fixed-vs-learned noise.

    Search:
      - 100k Sobol global GPU screening normally
      - 250k pulse under stagnation
      - 500k one-shot severe-stagnation pulse
      - Top-K diverse candidates
      - CPU refinement from a SMALL informed subset only
      - final discrete-vs-refined decision under the same stacked acquisition

    No UCB portfolio, no bandit, no forced uncertainty action, no trust region.
    """

    MEMBER_NAMES = ("rbf", "matern25")

    def __init__(
        self,
        design_space,
        evaluator,
        seed=42,
        screen_device="auto",
        duplicate_tol=1e-5,
        noise_lower=1e-8,
        noise_upper=1e-3,
        noise_initial=1e-4,
        stacking_weight_floor=0.10,
    ):
        super().__init__(
            design_space=design_space,
            evaluator=evaluator,
            seed=seed,
            screen_device=screen_device,
            standardized_noise_var=1e-5,
            duplicate_tol=duplicate_tol,
        )

        self.noise_lower = float(noise_lower)
        self.noise_upper = float(noise_upper)
        self.noise_initial = float(noise_initial)

        if not (
            0.0 < self.noise_lower
            < self.noise_initial
            < self.noise_upper
        ):
            raise ValueError(
                "Require 0 < noise_lower < noise_initial < noise_upper"
            )

        self.stacking_weight_floor = float(
            stacking_weight_floor
        )
        if not (
            0.0
            <= self.stacking_weight_floor
            < 0.5
        ):
            raise ValueError(
                "stacking_weight_floor must be in [0, 0.5)"
            )

        self._member_warm_states = {
            name: {}
            for name in self.MEMBER_NAMES
        }
        self._fit_round = 0

        # Start neutral. LOO stacking updates this after the first fit.
        self.stacking_weight_rbf = 0.5
        self.weight_history = []

        self.timings.update({
            "stacked_model_build_s": 0.0,
            "stacked_model_fit_s": 0.0,
            "loo_stacking_s": 0.0,
            "stacked_acquisition_build_s": 0.0,
        })

        self.fit_diagnostics.update({
            "rbf_optimized_fits": 0,
            "matern25_optimized_fits": 0,
            "rbf_warm_only_fits": 0,
            "matern25_warm_only_fits": 0,
            "rbf_fit_failures": 0,
            "matern25_fit_failures": 0,
            "rbf_fit_rollbacks": 0,
            "matern25_fit_rollbacks": 0,
            "loo_updates": 0,
            "loo_failures": 0,
            "stacking_floor_hits_rbf": 0,
            "stacking_floor_hits_matern": 0,
            "severe_stagnation_pulses": 0,
            "refinement_selected": 0,
            "discrete_selected": 0,
            "scipy_fit_abnormal_recovered": 0,
            "scipy_fit_other_warnings": 0,
            "torch_fit_fallback_attempts": 0,
            "torch_fit_fallback_successes": 0,
            "torch_fit_fallback_failures": 0,
        })

        # V0.3.0.1: fail fast if member names and diagnostic counters diverge.
        for _member in self.MEMBER_NAMES:
            for _suffix in (
                "optimized_fits",
                "warm_only_fits",
                "fit_failures",
                "fit_rollbacks",
            ):
                _key = f"{_member}_{_suffix}"
                if _key not in self.fit_diagnostics:
                    raise RuntimeError(
                        f"Missing diagnostic key for stacked GP member: {_key}"
                    )

    # ------------------------------------------------------------------
    # Model construction
    # ------------------------------------------------------------------

    def _raw_training_tensors_on(self, device):
        torch = self.torch

        X = torch.as_tensor(
            np.asarray(
                self.x01_history,
                dtype=np.float64,
            ),
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
                rows.append(
                    [result.score, *margins]
                )
            Y_np = np.asarray(
                rows,
                dtype=np.float64,
            )

        Y = torch.as_tensor(
            Y_np,
            dtype=self.dtype,
            device=device,
        )

        return X, Y

    def _make_member_model(
        self,
        X,
        Y,
        member_name,
    ):
        import torch
        from botorch.models import SingleTaskGP
        from botorch.models.transforms import Standardize
        from botorch.models.utils.gpytorch_modules import (
            get_covar_module_with_dim_scaled_prior,
        )
        from gpytorch.constraints import Interval
        from gpytorch.likelihoods import GaussianLikelihood

        if member_name not in self.MEMBER_NAMES:
            raise KeyError(member_name)

        num_outputs = int(Y.shape[-1])
        batch_shape = (
            torch.Size([num_outputs])
            if num_outputs > 1
            else torch.Size()
        )

        covar_module = (
            get_covar_module_with_dim_scaled_prior(
                ard_num_dims=self.space.dim,
                batch_shape=batch_shape,
                use_rbf_kernel=(
                    member_name == "rbf"
                ),
            )
        ).to(
            device=X.device,
            dtype=X.dtype,
        )

        likelihood = GaussianLikelihood(
            batch_shape=batch_shape,
            noise_constraint=Interval(
                self.noise_lower,
                self.noise_upper,
                initial_value=self.noise_initial,
            ),
        ).to(
            device=X.device,
            dtype=X.dtype,
        )

        model = SingleTaskGP(
            train_X=X,
            train_Y=Y,
            likelihood=likelihood,
            covar_module=covar_module,
            outcome_transform=Standardize(
                m=num_outputs
            ),
        ).to(
            device=X.device,
            dtype=X.dtype,
        )

        return model

    @staticmethod
    def _clone_state(model):
        return {
            key: value.detach().clone()
            for key, value
            in model.state_dict().items()
        }

    def _apply_member_warm_state(
        self,
        model,
        member_name,
    ):
        warm = self._member_warm_states[
            member_name
        ]
        if not warm:
            return False

        current = model.state_dict()
        applied = False

        for key, value in warm.items():
            if (
                key in current
                and current[key].shape
                == value.shape
            ):
                current[key] = value.to(
                    device=current[key].device,
                    dtype=current[key].dtype,
                )
                applied = True

        model.load_state_dict(
            current,
            strict=False,
        )
        return applied

    def _capture_member_warm_state(
        self,
        model,
        member_name,
    ):
        keep = {}

        for key, value in (
            model.state_dict().items()
        ):
            if (
                key.startswith("covar_module.")
                or key.startswith("mean_module.")
                or key.startswith("likelihood.")
            ):
                keep[key] = (
                    value.detach().clone()
                )

        self._member_warm_states[
            member_name
        ] = keep

    def _fit_member(
        self,
        member_name,
        optimize,
        fit_seed,
    ):
        import warnings

        from botorch.exceptions.warnings import (
            OptimizationWarning,
        )
        from botorch.fit import (
            fit_gpytorch_mll,
            fit_gpytorch_mll_torch,
        )
        from botorch.utils.sampling import manual_seed
        from gpytorch.mlls import (
            ExactMarginalLogLikelihood,
        )

        X, Y = self._raw_training_tensors_on(
            self.device
        )

        t0 = time.perf_counter()

        model = self._make_member_model(
            X=X,
            Y=Y,
            member_name=member_name,
        )

        self._apply_member_warm_state(
            model,
            member_name,
        )

        mll = ExactMarginalLogLikelihood(
            model.likelihood,
            model,
        ).to(
            device=self.device,
            dtype=self.dtype,
        )

        rollback = self._clone_state(model)

        self.timings[
            "stacked_model_build_s"
        ] += time.perf_counter() - t0

        t0 = time.perf_counter()
        fit_ok = True

        if optimize:
            scipy_error = None

            try:
                # fit_gpytorch_mll already has an internal retry policy.
                # Capture its OptimizationWarnings here so a recovered
                # intermediate SciPy failure does not pollute benchmark logs.
                with warnings.catch_warnings(
                    record=True
                ) as fit_warning_records:
                    warnings.simplefilter(
                        "always",
                        category=OptimizationWarning,
                    )

                    with manual_seed(
                        int(fit_seed)
                    ):
                        fit_gpytorch_mll(mll)

                abnormal_count = 0

                for warning_record in (
                    fit_warning_records
                ):
                    message = str(
                        warning_record.message
                    )

                    if (
                        "scipy_minimize"
                        in message
                        and (
                            "ABNORMAL"
                            in message.upper()
                        )
                    ):
                        abnormal_count += 1
                        continue

                    # Keep visibility for every OptimizationWarning we did not
                    # explicitly classify as a recovered SciPy line-search
                    # failure.
                    self.fit_diagnostics[
                        "scipy_fit_other_warnings"
                    ] += 1

                    warnings.warn_explicit(
                        message=message,
                        category=warning_record.category,
                        filename=warning_record.filename,
                        lineno=warning_record.lineno,
                    )

                if abnormal_count:
                    self.fit_diagnostics[
                        "scipy_fit_abnormal_recovered"
                    ] += int(
                        abnormal_count
                    )

                    self.events.append({
                        "event":
                            "gp_scipy_abnormal_recovered",
                        "member":
                            member_name,
                        "count":
                            int(
                                abnormal_count
                            ),
                    })

            except Exception as exc:
                scipy_error = exc

            # If all SciPy fitting attempts actually fail, do not silently
            # continue with the pre-fit model. Roll back, then use BoTorch's
            # torch.optim-based fitter as a real fallback.
            if scipy_error is not None:
                self.fit_diagnostics[
                    "torch_fit_fallback_attempts"
                ] += 1

                model.load_state_dict(
                    rollback,
                    strict=True,
                )

                mll = ExactMarginalLogLikelihood(
                    model.likelihood,
                    model,
                ).to(
                    device=self.device,
                    dtype=self.dtype,
                )

                try:
                    with manual_seed(
                        int(fit_seed)
                        + 1_000_003
                    ):
                        fit_gpytorch_mll(
                            mll,
                            optimizer=(
                                fit_gpytorch_mll_torch
                            ),
                            optimizer_kwargs={
                                "step_limit": 120,
                            },
                        )

                    self.fit_diagnostics[
                        "torch_fit_fallback_successes"
                    ] += 1

                    self.events.append({
                        "event":
                            "gp_torch_fit_fallback_success",
                        "member":
                            member_name,
                        "scipy_error":
                            str(
                                scipy_error
                            ),
                    })

                except Exception as torch_exc:
                    fit_ok = False

                    self.fit_diagnostics[
                        "torch_fit_fallback_failures"
                    ] += 1
                    self.fit_diagnostics[
                        f"{member_name}_fit_failures"
                    ] += 1
                    self.fit_diagnostics[
                        f"{member_name}_fit_rollbacks"
                    ] += 1
                    self.fit_diagnostics[
                        "fit_failures"
                    ] += 1
                    self.fit_diagnostics[
                        "fit_rollbacks"
                    ] += 1

                    model.load_state_dict(
                        rollback,
                        strict=True,
                    )

                    self.events.append({
                        "event":
                            "stacked_member_fit_failure",
                        "member":
                            member_name,
                        "scipy_error":
                            str(
                                scipy_error
                            ),
                        "torch_error":
                            str(
                                torch_exc
                            ),
                    })

            if fit_ok:
                invalid = (
                    self._invalid_learned_parameters(
                        model
                    )
                )

                if invalid:
                    fit_ok = False

                    self.fit_diagnostics[
                        "invalid_learned_parameter_failures"
                    ] += 1
                    self.fit_diagnostics[
                        f"{member_name}_fit_failures"
                    ] += 1
                    self.fit_diagnostics[
                        f"{member_name}_fit_rollbacks"
                    ] += 1
                    self.fit_diagnostics[
                        "fit_failures"
                    ] += 1
                    self.fit_diagnostics[
                        "fit_rollbacks"
                    ] += 1

                    model.load_state_dict(
                        rollback,
                        strict=True,
                    )

                    self.events.append({
                        "event":
                            "stacked_member_invalid_parameters",
                        "member":
                            member_name,
                        "parameters":
                            list(
                                invalid
                            ),
                    })

                else:
                    self.fit_diagnostics[
                        f"{member_name}_optimized_fits"
                    ] += 1
                    self.fit_diagnostics[
                        "optimized_fits"
                    ] += 1

        else:
            self.fit_diagnostics[
                f"{member_name}_warm_only_fits"
            ] += 1
            self.fit_diagnostics[
                "warm_only_fits"
            ] += 1

        self.timings[
            "stacked_model_fit_s"
        ] += time.perf_counter() - t0

        model.eval()
        model.likelihood.eval()

        if fit_ok or not optimize:
            self._capture_member_warm_state(
                model,
                member_name,
            )

        return model

    def _fit_pair(self, optimize):
        round_id = self._fit_round

        rbf = self._fit_member(
            "rbf",
            optimize=optimize,
            fit_seed=(
                self.seed
                + 50_000
                + round_id * 10
                + 1
            ),
        )

        matern = self._fit_member(
            "matern25",
            optimize=optimize,
            fit_seed=(
                self.seed
                + 50_000
                + round_id * 10
                + 2
            ),
        )

        self._fit_round += 1

        return rbf, matern

    # ------------------------------------------------------------------
    # LOO predictive stacking
    # ------------------------------------------------------------------

    @staticmethod
    def _gaussian_log_predictive_density(
        y,
        mean,
        variance,
    ):
        y = np.asarray(y, dtype=np.float64)
        mean = np.asarray(
            mean,
            dtype=np.float64,
        )
        variance = np.asarray(
            variance,
            dtype=np.float64,
        )

        variance = np.clip(
            variance,
            1e-12,
            np.inf,
        )

        logp = -0.5 * (
            np.log(
                2.0 * math.pi * variance
            )
            + ((y - mean) ** 2)
            / variance
        )

        # One predictive score per observation.
        # Sum across outputs if continuous constraint margins are present.
        return np.sum(
            logp,
            axis=-1,
        )

    @staticmethod
    def _stacking_weight_from_logps(
        logp_a,
        logp_b,
        weight_floor=0.10,
        grid_size=161,
    ):
        logp_a = np.asarray(
            logp_a,
            dtype=np.float64,
        ).reshape(-1)
        logp_b = np.asarray(
            logp_b,
            dtype=np.float64,
        ).reshape(-1)

        if logp_a.shape != logp_b.shape:
            raise ValueError(
                "LOO log-predictive arrays must match."
            )

        floor = float(weight_floor)
        lo = max(
            floor,
            1e-6,
        )
        hi = min(
            1.0 - floor,
            1.0 - 1e-6,
        )

        grid = np.linspace(
            lo,
            hi,
            int(grid_size),
        )

        best_w = 0.5
        best_score = -np.inf
        tie_tol = 1e-12

        for w in grid:
            mixed = np.logaddexp(
                math.log(float(w))
                + logp_a,
                math.log1p(-float(w))
                + logp_b,
            )

            score = float(
                np.sum(mixed)
            )

            if (
                score > best_score + tie_tol
                or (
                    abs(score - best_score) <= tie_tol
                    and abs(float(w) - 0.5)
                    < abs(best_w - 0.5)
                )
            ):
                best_score = score
                best_w = float(w)

        return best_w, best_score

    @staticmethod
    def _squeeze_loo_tensor(x):
        arr = (
            x.detach()
            .cpu()
            .double()
            .numpy()
        )

        # Current BoTorch LOO posterior:
        # n x 1 x m. Preserve n x m.
        if (
            arr.ndim >= 3
            and arr.shape[-2] == 1
        ):
            arr = np.squeeze(
                arr,
                axis=-2,
            )

        if arr.ndim == 1:
            arr = arr[:, None]

        return arr

    def _update_stacking_weight(
        self,
        rbf_model,
        matern_model,
    ):
        t0 = time.perf_counter()

        try:
            from botorch.cross_validation import (
                loo_cv,
            )

            _, Y = self._raw_training_tensors_on(
                self.device
            )
            y = (
                Y.detach()
                .cpu()
                .double()
                .numpy()
            )

            cv_rbf = loo_cv(
                rbf_model,
                observation_noise=True,
                untransform=True,
            )
            cv_mat = loo_cv(
                matern_model,
                observation_noise=True,
                untransform=True,
            )

            mean_rbf = self._squeeze_loo_tensor(
                cv_rbf.posterior.mean
            )
            var_rbf = self._squeeze_loo_tensor(
                cv_rbf.posterior.variance
            )
            mean_mat = self._squeeze_loo_tensor(
                cv_mat.posterior.mean
            )
            var_mat = self._squeeze_loo_tensor(
                cv_mat.posterior.variance
            )

            if (
                mean_rbf.shape != y.shape
                or mean_mat.shape != y.shape
                or var_rbf.shape != y.shape
                or var_mat.shape != y.shape
            ):
                raise RuntimeError(
                    "Unexpected LOO posterior shape: "
                    f"y={y.shape}, "
                    f"rbf={mean_rbf.shape}, "
                    f"matern={mean_mat.shape}"
                )

            logp_rbf = (
                self._gaussian_log_predictive_density(
                    y,
                    mean_rbf,
                    var_rbf,
                )
            )
            logp_mat = (
                self._gaussian_log_predictive_density(
                    y,
                    mean_mat,
                    var_mat,
                )
            )

            weight, objective = (
                self._stacking_weight_from_logps(
                    logp_a=logp_rbf,
                    logp_b=logp_mat,
                    weight_floor=(
                        self.stacking_weight_floor
                    ),
                )
            )

            self.stacking_weight_rbf = (
                float(weight)
            )

            tol = 1e-9
            if (
                abs(
                    weight
                    - self.stacking_weight_floor
                ) <= tol
            ):
                self.fit_diagnostics[
                    "stacking_floor_hits_rbf"
                ] += 1

            if (
                abs(
                    weight
                    - (
                        1.0
                        - self.stacking_weight_floor
                    )
                ) <= tol
            ):
                self.fit_diagnostics[
                    "stacking_floor_hits_matern"
                ] += 1

            self.fit_diagnostics[
                "loo_updates"
            ] += 1

            record = {
                "n": len(self.history),
                "weight_rbf":
                    float(weight),
                "weight_matern":
                    float(1.0 - weight),
                "stacking_objective":
                    float(objective),
                "mean_logp_rbf":
                    float(
                        np.mean(logp_rbf)
                    ),
                "mean_logp_matern":
                    float(
                        np.mean(logp_mat)
                    ),
            }
            self.weight_history.append(record)

            self.events.append({
                "event":
                    "loo_stacking_update",
                **record,
            })

        except Exception as exc:
            self.fit_diagnostics[
                "loo_failures"
            ] += 1

            # Keep the last known-good weight.
            self.events.append({
                "event":
                    "loo_stacking_failure",
                "error": str(exc),
                "retained_weight_rbf":
                    float(
                        self.stacking_weight_rbf
                    ),
            })

        self.timings[
            "loo_stacking_s"
        ] += time.perf_counter() - t0

    # ------------------------------------------------------------------
    # Acquisition construction
    # ------------------------------------------------------------------

    def _build_stacked_acquisition(
        self,
        rbf_model,
        matern_model,
    ):
        t0 = time.perf_counter()

        rbf_acq, rbf_mode = (
            self._build_acquisition(
                rbf_model
            )
        )
        mat_acq, mat_mode = (
            self._build_acquisition(
                matern_model
            )
        )

        if rbf_mode != mat_mode:
            raise RuntimeError(
                "Member acquisition modes disagree: "
                f"{rbf_mode} vs {mat_mode}"
            )

        stacked = StackedLogAcquisition(
            rbf_acq,
            mat_acq,
            weight_a=(
                self.stacking_weight_rbf
            ),
        )

        self.timings[
            "stacked_acquisition_build_s"
        ] += time.perf_counter() - t0

        return stacked, (
            f"Stacked{rbf_mode}"
        )

    def _clone_member_to_screen(
        self,
        cpu_model,
        member_name,
    ):
        if self.screen_device.type == "cpu":
            return cpu_model

        X, Y = self._raw_training_tensors_on(
            self.screen_device
        )

        screen_model = self._make_member_model(
            X=X,
            Y=Y,
            member_name=member_name,
        )

        screen_model.load_state_dict(
            cpu_model.state_dict(),
            strict=True,
        )
        screen_model.eval()
        screen_model.likelihood.eval()

        return screen_model

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(
        self,
        initial_trials=12,
        smart_trials=68,
        refit_interval=4,
        screen_pool=100_000,
        screen_chunk_size=2048,
        top_k=8,
        refinement_top_k=4,
        diversity_radius=0.035,
        refinement_maxiter=50,
        refinement_timeout_sec=3.0,
        stagnation_trigger=6,
        pulse_interval=6,
        pulse_screen_pool=250_000,
        severe_stagnation_trigger=12,
        severe_screen_pool=500_000,
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
        severe_used = False

        for step in range(total_steps):
            iter_t0 = time.perf_counter()

            pulse = (
                stagnation
                >= int(stagnation_trigger)
                and (
                    stagnation
                    - int(stagnation_trigger)
                )
                % max(
                    1,
                    int(pulse_interval),
                )
                == 0
            )

            severe_pulse = (
                stagnation
                >= int(
                    severe_stagnation_trigger
                )
                and not severe_used
            )

            if severe_pulse:
                severe_used = True
                self.fit_diagnostics[
                    "severe_stagnation_pulses"
                ] += 1

            if pulse or severe_pulse:
                self.fit_diagnostics[
                    "stagnation_pulses"
                ] += 1

            optimize_models = (
                step == 0
                or int(refit_interval) <= 1
                or step
                % int(refit_interval)
                == 0
                or pulse
                or severe_pulse
            )

            rbf_cpu, mat_cpu = (
                self._fit_pair(
                    optimize=optimize_models
                )
            )

            # LOO weights only need updating when hyperparameters are refit.
            if optimize_models:
                self._update_stacking_weight(
                    rbf_cpu,
                    mat_cpu,
                )

            cpu_acq, acquisition_mode = (
                self._build_stacked_acquisition(
                    rbf_cpu,
                    mat_cpu,
                )
            )

            if self.screen_device.type == "cpu":
                rbf_screen = rbf_cpu
                mat_screen = mat_cpu
                screen_acq = cpu_acq
            else:
                t0 = time.perf_counter()

                rbf_screen = (
                    self._clone_member_to_screen(
                        rbf_cpu,
                        "rbf",
                    )
                )
                mat_screen = (
                    self._clone_member_to_screen(
                        mat_cpu,
                        "matern25",
                    )
                )

                self.torch.cuda.synchronize()

                self.timings[
                    "screen_model_build_s"
                ] += (
                    time.perf_counter()
                    - t0
                )

                screen_acq, _ = (
                    self._build_stacked_acquisition(
                        rbf_screen,
                        mat_screen,
                    )
                )

            if severe_pulse:
                active_pool = int(
                    severe_screen_pool
                )
            elif pulse:
                active_pool = int(
                    pulse_screen_pool
                )
            else:
                active_pool = int(
                    screen_pool
                )

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
                    top_k=int(top_k),
                    diversity_radius=float(
                        diversity_radius
                    ),
                )
            )

            self.timings[
                "topk_selection_s"
            ] += time.perf_counter() - t0

            discrete = CandidateSource(
                name=(
                    "stacked_discrete_severe"
                    if severe_pulse
                    else (
                        "stacked_discrete_pulse"
                        if pulse
                        else "stacked_discrete"
                    )
                ),
                x01=starts[0].copy(),
                acquisition_value=float(
                    start_scores[0]
                ),
            )

            # Re-score on the CPU stacked acquisition so final comparison is
            # made under exactly one model/acquisition representation.
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

            refine_count = min(
                int(refinement_top_k),
                len(starts),
            )

            refined = (
                self._refine_informed_starts(
                    cpu_acq=cpu_acq,
                    starts=starts[
                        :refine_count
                    ],
                    maxiter=int(
                        refinement_maxiter
                    ),
                    timeout_sec=float(
                        refinement_timeout_sec
                    ),
                    seed=(
                        self.seed
                        + 900_000
                        + step
                    ),
                )
            )

            chosen = discrete

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
                ] += time.perf_counter() - t0

                if (
                    not self._is_duplicate(
                        refined.x01
                    )
                    and refined.acquisition_value
                    > discrete.acquisition_value
                    + 1e-12
                ):
                    refined.name = (
                        "stacked_refined"
                    )
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
                                "stacked_duplicate_recovery"
                            ),
                            x01=x.copy(),
                            acquisition_value=float(
                                value
                            ),
                        )
                        break

                if replacement is None:
                    raise RuntimeError(
                        "All stacked top candidates duplicate history."
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

            improved = (
                best
                > previous_best
                + 1e-10
            )

            if improved:
                stagnation = 0
                severe_used = False
            else:
                stagnation += 1

            iteration_s = (
                time.perf_counter()
                - iter_t0
            )
            self.timings[
                "total_iteration_s"
            ] += iteration_s

            event = {
                "step": step,
                "event": "iteration",
                "acquisition":
                    acquisition_mode,
                "source": chosen.name,
                "pulse": bool(pulse),
                "severe_pulse":
                    bool(severe_pulse),
                "pool": active_pool,
                "weight_rbf":
                    float(
                        self.stacking_weight_rbf
                    ),
                "weight_matern":
                    float(
                        1.0
                        - self.stacking_weight_rbf
                    ),
                "score":
                    float(result.score),
                "best": float(best),
                "stagnation":
                    int(stagnation),
                "iteration_s":
                    float(iteration_s),
            }
            self.events.append(event)

            if verbose and (
                step == 0
                or (step + 1) % 5 == 0
                or pulse
                or severe_pulse
                or step
                == total_steps - 1
            ):
                print(
                    f"[V0.3.0.1 {step+1:02d}/{total_steps}] "
                    f"acq={acquisition_mode:<14s} "
                    f"source={chosen.name:<24s} "
                    f"wRBF={self.stacking_weight_rbf:.3f} "
                    f"wMat={1.0-self.stacking_weight_rbf:.3f} "
                    f"pool={active_pool:<7d} "
                    f"best={best:.4f} "
                    f"stag={stagnation:02d} "
                    f"iter={iteration_s:.2f}s"
                )

            if self.screen_device.type == "cuda":
                # Release references before the next pair is built.
                del screen_acq
                del rbf_screen
                del mat_screen

        feasible = [
            r
            for r in self.history
            if r.feasible
        ]

        if not feasible:
            feasible = list(self.history)

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
            "trials_run":
                len(self.history),
            "best": feasible[0],
            "top": feasible[:8],
            "events":
                list(self.events),
            "timings":
                dict(self.timings),
            "fit_diagnostics":
                dict(
                    self.fit_diagnostics
                ),
            "weight_history":
                list(
                    self.weight_history
                ),
            "final_weight_rbf":
                float(
                    self.stacking_weight_rbf
                ),
            "final_weight_matern":
                float(
                    1.0
                    - self.stacking_weight_rbf
                ),
            "fit_device": "cpu",
            "screen_device":
                str(self.screen_device),
            "gpu_memory":
                gpu_memory,
        }
