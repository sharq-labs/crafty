# Engineering AI Core V0.3.2.1 — Validation Fairness + Windows Runtime Patch

This patch fixes two issues discovered by the first strong-baseline run.

## Local benchmark fairness
The previous local Sphere / Rastrigin / Ackley optima were exactly at the midpoint of symmetric bounds, while Nevergrad was initialized at that midpoint. V0.3.2.1 uses deterministic shifted + rotated instances, and NGOpt/CMA start from deterministic non-midpoint points.

## Windows refinement runtime
The observed Windows/Python 3.14 run was interrupted inside SciPy -> threadpoolctl while BoTorch refined the acquisition. The Validation Lab now defaults to BoTorch `gen_candidates_torch` for the small informed refinement step. The original SciPy path remains available with `--stacked-refinement-backend scipy`.

## Run
```powershell
python -m src.engcore.validation_selftest
python -m src.engcore.validation_quick --dimensions 2,5 --instances 1 --budget-multiplier 20 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch
```

Then the multi-instance pilot:
```powershell
python -m src.engcore.validation_quick --dimensions 2,5 --instances 1,2,3 --budget-multiplier 20 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/local_shifted_3inst
```

Do not use the old NGOpt zero values as evidence of superiority; those runs had center-optimum bias.
