import numpy as np
from scipy.stats import qmc

def sobol_points(n: int, dim: int, seed: int = 42) -> np.ndarray:
    sampler = qmc.Sobol(d=dim, scramble=True, seed=seed)
    m = int(np.ceil(np.log2(max(n, 2))))
    pts = sampler.random_base2(m=m)
    return pts[:n]
