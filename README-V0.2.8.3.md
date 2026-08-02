# Engineering AI Core V0.2.8.3

V0.2.8.3 fixes a false GP-fit failure introduced by V0.2.8.2.

## Root cause

V0.2.8.2 validated a fit by iterating over:

```python
model.state_dict()
```

and rejecting any tensor containing `NaN` or `Inf`.

That is too broad for GPyTorch.

A model state contains not only learned parameters, but also buffers and
constraint metadata. Constraint objects can legitimately contain infinite
bounds for unbounded sides.

Therefore:

```text
"GP fit produced non-finite parameters"
```

did not prove that a learned GP hyperparameter was invalid.

In the observed run this caused:

```text
optimized_fits = 0
fit_failures   = 6
fit_rollbacks  = 6
```

even though `fit_gpytorch_mll` itself returned normally.

## Fix

V0.2.8.3 validates only:

```python
model.named_parameters()
```

Actual trainable parameters must all be finite.

Constraint buffers and other non-learned state are not treated as learned
hyperparameters.

If a real learned parameter becomes invalid, the error now includes its exact
name, for example:

```text
GP fit produced NaN/Inf in learned parameter(s): covar_module.raw_lengthscale
```

Rollback protection remains enabled.

## Keep the successful V0.2.8.2 changes

Still included:

- reproducible `optimize_acqf` seeding
- CPU-first default
- acquisition timeout
- duplicate protection
- scale-aware fixed noise
- fallback-only chunked guard
- adaptive stagnation pulses
- fair penalty-mode comparison with Legacy

## Validation order

### 1. Reproducibility

```powershell
python -m src.engcore.logei_repro --benchmark multimodal --seed 601 --budget 24 --initial 12 --mode balanced --device cpu
```

Expected:

```text
Exact X match     : True
Exact score match : True
```

### 2. Short GP-fit diagnostic

```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 24 --initial 12 --mode balanced --device cpu
```

Important diagnostics:

```text
optimized_fits
fit_failures
fit_rollbacks
invalid_learned_parameter_failures
```

Desired result:

```text
optimized_fits > 0
fit_failures = 0
fit_rollbacks = 0
invalid_learned_parameter_failures = 0
```

### 3. 40-evaluation run

Only after step 2 passes:

```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --mode balanced --device cpu
```

Do not run the large suite until fit diagnostics are clean.
