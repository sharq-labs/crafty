# Engineering AI Core V0.3.3 — Research Adaptive Optimizer

Branch: `research/v0.3.3-adaptive`  
Baseline tag: `v0.3.2.6-stacked_v0301` (immutable)

## Goal

Add a **separately selectable** adaptive stacked optimizer that:

- infers search state only from black-box observations
- adapts exploration / exploitation / rescue continuously
- preserves `stacked_v0301` unchanged

This is **not** a BBOB memorizer.

## Architecture audit (stacked_v0301 baseline)

| Stage | Behavior |
|---|---|
| Init | Sobol DOE in unit cube; all init evals count |
| Models | RBF ARD GP + Matern-2.5 ARD GP, bounded nugget |
| Fit | CPU `fit_gpytorch_mll`, warm-state between refits |
| Stacking | LOO predictive log densities → mixture weight |
| Acquisition | Stacked LogEI (`logaddexp` mixture) |
| Candidates | Large Sobol screen (GPU if available), diverse Top-K |
| Refinement | CPU continuous refine from informed starts |
| Fallback | Discrete vs refined by CPU acq; duplicate recovery |
| Stagnation | Pulse / severe pulse increases screen pool |
| Devices | Fit+refine CPU; screen optional CUDA |
| Budget | Exactly `initial_trials + smart_trials` objective calls |

## New modules

1. `landscape_diagnostics.py` — online features only from X/y/budget/model stack stats  
2. `adaptive_policy.py` — continuous knob policy (no landscape class labels)  
3. `adaptive_stacked_engine.py` — `AdaptiveStackedGPBOEngine` / `adaptive_stacked_v033`

## Adaptive policy (minimal)

Uses diagnostics every BO step:

- reliable + improving → modest exploitation (smaller screen, more refine)
- unreliable / disagreeing models → more global diversity
- stagnation + concentration → expand exploration + rescue
- late budget + reliable model → exploit
- tiny-N → conservative defaults

## Rescue mechanism

Triggers from policy (stagnation / unreliable model), not benchmark IDs.

- fresh Sobol space-filling candidates
- incumbent-centered Gaussian perturbations
- scored by acquisition only (no extra objective calls)
- selected only if acquisition beats current discrete/refined choice

## Performance

No semantic changes to `stacked_v0301` screening/refinement.

Adaptive engine remains dual-GP heavy by design; wall-clock optimization for cheap
objectives is secondary to sample efficiency. Implementation opts in the adaptive
path are limited to avoiding extra objective work in rescue/diagnostics.

## Validation registry

Algorithms now include:

`cmaes, ngopt, stacked, adaptive_stacked`

## Tests

```powershell
.\.venv\Scripts\python.exe -m src.engcore.adaptive_stacked_selftest
.\.venv\Scripts\python.exe -m src.engcore.validation_fairness_selftest
```

## Short smoke comparison (user/local)

```powershell
.\.venv\Scripts\python.exe -m src.engcore.validation_quick --dimensions 2 --instances 1 --budget-multiplier 10 --algorithms random,sobol,stacked,adaptive_stacked --stacked-mode fast --screen-device cpu --out validation_results/adaptive_smoke_v033
```

## Full COCO validation (manual; do not auto-run)

```powershell
.\.venv\Scripts\python.exe -m src.engcore.coco_arena --functions all --dimensions 2 --instances 1,2,3,4,5 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked,adaptive_stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_full_d2_v033

.\.venv\Scripts\python.exe -m src.engcore.coco_arena --functions all --dimensions 5 --instances 1,2,3,4,5 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked,adaptive_stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_full_d5_v033
```

## Guardrail statements

| Check | Value |
|---|---|
| BASELINE STACKED_v0301 MODIFIED | **NO** |
| SEARCH BEHAVIOR CHANGED IN NEW OPTIMIZER | **YES** |
| BENCHMARK-SPECIFIC LOGIC ADDED | **NO** |
| HIDDEN OBJECTIVE EVALUATIONS ADDED | **NO** |
| STRICT BUDGET PRESERVED | **YES** |
