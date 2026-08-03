# Engineering AI Core V0.3.2.2 — Warning Recovery Patch

This patch addresses the two warnings observed during the corrected
multi-instance validation run.

## 1. Nevergrad / SciPy COBYLA RHOEND warning

Observed message:

```text
COBYLA: Invalid RHOEND; it should be a positive number and RHOEND <= RHOBEG;
it is set to 1e-06
```

This comes from an internal optimizer path selected by NGOpt. SciPy explicitly
self-corrects the value to `1e-06`.

V0.3.2.2 captures only this exact self-corrected warning family and stores its
count in NGOpt trace metadata:

```text
cobyla_rhoend_autocorrections
```

Every unrelated warning is re-emitted normally. This is deliberately not a
global `ignore warnings` switch.

## 2. BoTorch SciPy GP-fit ABNORMAL warning

Observed message:

```text
OptimizationWarning:
scipy_minimize terminated with ... FAILURE ... ABNORMAL
```

This warning is generated while fitting GP hyperparameters, not while running
the Validation Lab's Torch acquisition refinement.

BoTorch's high-level `fit_gpytorch_mll` already has retry behavior. The patch
therefore:

1. captures OptimizationWarnings around the complete high-level fit,
2. records recovered `ABNORMAL` attempts when the final fit succeeds,
3. keeps all unrelated OptimizationWarnings visible,
4. if SciPy fitting actually fails after its retry policy, rolls the model
   back and tries BoTorch's `fit_gpytorch_mll_torch`,
5. only reports a real fit failure when both paths fail.

New diagnostics:

```text
scipy_fit_abnormal_recovered
scipy_fit_other_warnings
torch_fit_fallback_attempts
torch_fit_fallback_successes
torch_fit_fallback_failures
```

## Test

```powershell
python -m src.engcore.validation_warning_check --screen-device auto
```

Then rerun the corrected arena:

```powershell
python -m src.engcore.validation_quick --dimensions 2,5 --instances 1,2,3 --budget-multiplier 20 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/local_shifted_3inst_v0322
```

Expected result:

- no repeated COBYLA `Invalid RHOEND` lines in the console,
- no recovered BoTorch `ABNORMAL` line-search warnings in the console,
- diagnostics still record if either condition occurred,
- unrelated warnings remain visible.
