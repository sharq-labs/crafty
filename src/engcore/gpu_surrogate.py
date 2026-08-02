from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
import numpy as np


@dataclass
class DeviceInfo:
    device: str
    name: str
    cuda: bool


@dataclass
class FitInfo:
    optimized: bool
    used_warm_start: bool
    scipy_warning: bool
    fallback_used: bool
    fallback_steps: int


def get_device(force_cpu: bool = False):
    import torch
    if force_cpu or not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device("cuda")


def describe_device(device):
    import torch
    if device.type == "cuda":
        return DeviceInfo(str(device), torch.cuda.get_device_name(device), True)
    return DeviceInfo(str(device), "CPU", False)


class TorchBotorchSurrogate:
    """
    V0.2.4:
    - float64 for BoTorch GP stability
    - warm-start kernel/likelihood hyperparameters
    - optional refit skipping
    - Adam fallback after optimizer warning
    - memory-safe fast_pred_var scoring
    """

    def __init__(self, dim: int, force_cpu: bool = False):
        import torch
        from botorch.models import SingleTaskGP
        from botorch.models.transforms import Standardize
        from gpytorch.mlls import ExactMarginalLogLikelihood

        self.torch = torch
        self.SingleTaskGP = SingleTaskGP
        self.Standardize = Standardize
        self.ExactMarginalLogLikelihood = ExactMarginalLogLikelihood

        self.dim = dim
        self.device = get_device(force_cpu)
        self.dtype = torch.float64

        self.model = None
        self.mll = None
        self._warm_hyperparameters = {}

    def _capture_hyperparameters(self):
        state = self.model.state_dict()
        self._warm_hyperparameters = {
            key: value.detach().clone()
            for key, value in state.items()
            if key.startswith("covar_module.") or key.startswith("likelihood.")
        }

    def _apply_warm_start(self):
        if not self._warm_hyperparameters:
            return False

        current = self.model.state_dict()
        applied = False

        for key, value in self._warm_hyperparameters.items():
            if key in current and current[key].shape == value.shape:
                current[key] = value.to(
                    device=current[key].device,
                    dtype=current[key].dtype,
                )
                applied = True

        self.model.load_state_dict(current, strict=False)
        return applied

    def _adam_fallback(self, steps=50, lr=0.04):
        torch = self.torch

        self.model.train()
        self.model.likelihood.train()

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        train_x = self.model.train_inputs[0]
        train_y = self.model.train_targets

        completed = 0
        for _ in range(steps):
            optimizer.zero_grad(set_to_none=True)

            output = self.model(train_x)
            loss = -self.mll(output, train_y)

            if not torch.isfinite(loss):
                break

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 10.0)
            optimizer.step()
            completed += 1

        self.model.eval()
        self.model.likelihood.eval()
        return completed

    def fit(self, x01, y, optimize=True, fallback_steps=50):
        from botorch.fit import fit_gpytorch_mll

        try:
            from botorch.exceptions.warnings import OptimizationWarning
        except Exception:
            OptimizationWarning = Warning

        torch = self.torch
        X = torch.as_tensor(x01, dtype=self.dtype, device=self.device)
        Y = torch.as_tensor(y, dtype=self.dtype, device=self.device).unsqueeze(-1)

        # x01 is already in [0,1], so no Normalize transform is needed.
        self.model = self.SingleTaskGP(
            train_X=X,
            train_Y=Y,
            outcome_transform=self.Standardize(m=1),
        ).to(device=self.device, dtype=self.dtype)

        warm_started = self._apply_warm_start()

        self.mll = self.ExactMarginalLogLikelihood(
            self.model.likelihood, self.model
        ).to(device=self.device, dtype=self.dtype)

        scipy_warning = False
        fallback_used = False
        completed_steps = 0

        if optimize:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    fit_gpytorch_mll(self.mll)
                except Exception:
                    scipy_warning = True

                if any(
                    issubclass(w.category, OptimizationWarning)
                    for w in caught
                ):
                    scipy_warning = True

            if scipy_warning:
                fallback_used = True
                completed_steps = self._adam_fallback(
                    steps=fallback_steps
                )

        self.model.eval()
        self.model.likelihood.eval()
        self._capture_hyperparameters()

        return FitInfo(
            optimized=bool(optimize),
            used_warm_start=bool(warm_started),
            scipy_warning=bool(scipy_warning),
            fallback_used=bool(fallback_used),
            fallback_steps=int(completed_steps),
        )

    def _score_chunk(self, chunk, best_y, xi):
        import gpytorch

        torch = self.torch
        X = torch.as_tensor(
            chunk, dtype=self.dtype, device=self.device
        )

        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            posterior = self.model.posterior(X)
            mean = posterior.mean.squeeze(-1)
            variance = posterior.variance.squeeze(-1).clamp_min(1e-14)
            std = torch.sqrt(variance)

            improvement = mean - float(best_y) - float(xi)
            z = improvement / std

            cdf = 0.5 * (
                1.0 + torch.erf(z / math.sqrt(2.0))
            )
            pdf = (
                1.0 / math.sqrt(2.0 * math.pi)
            ) * torch.exp(-0.5 * z * z)

            ei = improvement * cdf + std * pdf

        result = ei.detach().cpu().numpy()
        del X, posterior, mean, variance, std, improvement, z, cdf, pdf, ei
        return result


    def predict_mean_std(
        self,
        candidates01,
        chunk_size=1024,
        min_chunk_size=64,
    ):
        """
        Memory-safe posterior mean/std for acquisition portfolios.
        """
        import gpytorch

        torch = self.torch
        if self.model is None:
            raise RuntimeError("fit() must be called first")

        means = np.empty(len(candidates01), dtype=np.float64)
        stds = np.empty(len(candidates01), dtype=np.float64)

        start = 0
        current_chunk = max(min_chunk_size, int(chunk_size))

        while start < len(candidates01):
            end = min(start + current_chunk, len(candidates01))

            try:
                X = torch.as_tensor(
                    candidates01[start:end],
                    dtype=self.dtype,
                    device=self.device,
                )

                with torch.no_grad(), gpytorch.settings.fast_pred_var():
                    posterior = self.model.posterior(X)
                    mean = posterior.mean.squeeze(-1)
                    variance = posterior.variance.squeeze(-1).clamp_min(1e-14)
                    std = torch.sqrt(variance)

                means[start:end] = mean.detach().cpu().numpy()
                stds[start:end] = std.detach().cpu().numpy()

                del X, posterior, mean, variance, std
                start = end

            except torch.OutOfMemoryError:
                if self.device.type != "cuda":
                    raise
                torch.cuda.empty_cache()
                new_chunk = current_chunk // 2
                if new_chunk < min_chunk_size:
                    raise RuntimeError(
                        "CUDA OOM at minimum safe chunk. Reduce --chunk."
                    )
                print(
                    f"[GPU memory guard] predict chunk "
                    f"{current_chunk:,} -> {new_chunk:,}"
                )
                current_chunk = new_chunk

        return means, stds

    def expected_improvement_scores(
        self,
        candidates01,
        best_y,
        xi=0.01,
        chunk_size=1024,
        min_chunk_size=64,
    ):
        torch = self.torch

        if self.model is None:
            raise RuntimeError("fit() must be called first")

        output = np.empty(len(candidates01), dtype=np.float64)
        start = 0
        current_chunk = max(min_chunk_size, int(chunk_size))

        while start < len(candidates01):
            end = min(start + current_chunk, len(candidates01))

            try:
                output[start:end] = self._score_chunk(
                    candidates01[start:end],
                    best_y,
                    xi,
                )
                start = end

            except torch.OutOfMemoryError:
                if self.device.type != "cuda":
                    raise

                torch.cuda.empty_cache()
                new_chunk = current_chunk // 2

                if new_chunk < min_chunk_size:
                    raise RuntimeError(
                        "CUDA OOM at minimum safe chunk. "
                        "Reduce --chunk."
                    )

                print(
                    f"[GPU memory guard] chunk {current_chunk:,} -> "
                    f"{new_chunk:,}"
                )
                current_chunk = new_chunk

        return output

    def synchronize(self):
        if self.device.type == "cuda":
            self.torch.cuda.synchronize()

    def empty_cache(self):
        if self.device.type == "cuda":
            self.torch.cuda.empty_cache()

    def reset_peak_memory(self):
        if self.device.type == "cuda":
            self.torch.cuda.reset_peak_memory_stats(self.device)

    def memory_stats(self):
        torch = self.torch

        if self.device.type != "cuda":
            return {
                "allocated_mb": 0.0,
                "reserved_mb": 0.0,
                "max_allocated_mb": 0.0,
                "max_reserved_mb": 0.0,
            }

        return {
            "allocated_mb":
                torch.cuda.memory_allocated(self.device) / 1024**2,
            "reserved_mb":
                torch.cuda.memory_reserved(self.device) / 1024**2,
            "max_allocated_mb":
                torch.cuda.max_memory_allocated(self.device) / 1024**2,
            "max_reserved_mb":
                torch.cuda.max_memory_reserved(self.device) / 1024**2,
        }
