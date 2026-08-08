import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, ConstantKernel, WhiteKernel
from scipy.stats import norm

class GaussianSurrogate:
    def __init__(self, dim: int):
        kernel = (
            ConstantKernel(1.0, (1e-3, 1e3))
            * Matern(length_scale=np.ones(dim), nu=2.5)
            + WhiteKernel(noise_level=1e-6, noise_level_bounds=(1e-9, 1e-2))
        )
        self.model = GaussianProcessRegressor(
            kernel=kernel,
            normalize_y=True,
            n_restarts_optimizer=2,
            random_state=42,
        )

    def fit(self, x01: np.ndarray, y: np.ndarray) -> None:
        self.model.fit(x01, y)

    def predict(self, x01: np.ndarray):
        mean, std = self.model.predict(x01, return_std=True)
        return mean, np.maximum(std, 1e-9)

def expected_improvement(mean, std, best_y, xi=0.01):
    improvement = mean - best_y - xi
    z = improvement / std
    return improvement * norm.cdf(z) + std * norm.pdf(z)
