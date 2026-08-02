# Engineering AI Core V0.2.8.1

This patch addresses the two issues observed in the first V0.2.8 run:

1. Repeated GPyTorch very-small-noise warnings.
2. A severe slowdown / apparent hang in the 4096-point multi-output Sobol guard.

## What changed

### 1. Scale-aware fixed noise

`Standardize` transforms both outcomes and observation variances.

V0.2.8 used the same raw `1e-6` variance for:
- objective values on a ~100 scale
- constraint margins on a ~0.1 scale

After standardization, objective noise could fall below GPyTorch's numerical floor.

V0.2.8.1 targets approximately `1e-5` variance in standardized units per output:

```text
raw_Yvar_j ≈ empirical_variance(Y_j) * 1e-5
```

This is still tiny for deterministic synthetic functions but numerically safer.

### 2. Sobol guard is fallback-only

V0.2.8 scored 4096 Sobol points every BO iteration.

That is removed.

The normal path is now:

```text
Exact GP
→ LogEI / LogCEI
→ ONE global multi-start optimize_acqf
→ evaluate
```

The Sobol guard runs only if continuous acquisition optimization fails.

If it is needed, it is evaluated in chunks (default 256), avoiding a huge
multi-output posterior call.

### 3. Explicit local regions are OFF in balanced mode

BoTorch's `optimize_acqf` already uses multiple random restarts to approximate a
global optimum of a non-convex acquisition function.

Therefore balanced mode does not add three extra local optimize_acqf calls.

Quality mode has one optional local challenger for ablation.

### 4. Fair comparison mode

For Legacy comparisons, default is:

```text
--constraint-mode penalty
```

This gives V0.2.8.1 the same evaluator information as Legacy.

Continuous margin modeling remains available with:

```text
--constraint-mode margins
```

but should be benchmarked as a separate constrained-BO capability.

## First: smoke test ONLY V0.2.8.1

This avoids waiting for Legacy + V0.2.7 first:

```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --mode balanced
```

Expected:
- no repeated small-noise warning
- progress every 5 adaptive steps
- guard uses normally 0
- completion without hanging

Then full budget:

```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 80 --initial 12 --mode balanced
```

## Then fair A/B/C

```powershell
python -m src.engcore.logei_ab --benchmark multimodal --seed 601 --budget 80 --initial 12 --legacy-pool 100000 --chunk 1024 --mode balanced --constraint-mode penalty
```

## Speed modes

These are starting configurations for ablation, NOT final optimal values.

Fast:
```text
restarts=6
raw=128
local=0
maxiter=70
refit=8
```

Balanced:
```text
restarts=12
raw=256
local=0
maxiter=100
refit=6
```

Quality:
```text
restarts=20
raw=512
local=1
maxiter=180
refit=4
```

Compare on the same seed with:

```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 80 --initial 12 --mode fast
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 80 --initial 12 --mode balanced
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 80 --initial 12 --mode quality
```

Do not pick the fastest mode from one seed. Measure quality and wall time across
multiple benchmark families.
