# Engineering AI Core V0.2.9.1 — Adaptive Hybrid + Narrow Diagnostic

## Evidence behind this release

V0.2.9 at budget 80:

```text
multimodal:
  discrete 135.15
  hybrid   165.93

narrow_optimum:
  discrete 41.29
  hybrid   31.51

deceptive_local:
  discrete 137.00
  hybrid   156.82
```

V0.2.9 hybrid selected the refined candidate on every adaptive iteration:

```text
refinement_selected = 68
discrete_selected   = 0
```

Therefore refinement is useful, but was over-trusted.

The narrow-optimum weakness also exists in discrete mode, so refinement alone
is not the root cause.

## What V0.2.9.1 changes

### Adaptive refinement gate

Refinement is now a challenger.

Balanced mode:

```text
first 12 adaptive iterations:
    forced discrete

after warmup:
    every 3rd iteration forced discrete

other iterations:
    refinement must beat discrete LogEI by >= 0.25 log units
```

This prevents the GP from sending the entire budget through refinement.

### Rare uncertainty experiment

After long stagnation, one experiment can be selected by maximum posterior
uncertainty from the same global screened domain.

This is NOT a weighted UCB/novelty portfolio.

It is a rare forced diagnostic/exploration action.

### Noise model diagnostic

V0.2.9.1 supports:

```text
--noise fixed
--noise learned
```

The Legacy engine used a learned-noise SingleTaskGP, while V0.2.8/0.2.9 used
tiny fixed deterministic noise.

The narrow diagnostic tests whether fixed-noise overconfidence is contributing
to missed small-volume optima.

### Kernel diagnostic

V0.2.9.1 supports:

```text
--kernel rbf
--kernel matern25
```

RBF remains available.
Matern-5/2 is an explicit ARD alternative for rougher / less infinitely-smooth
landscapes.

Do not declare Matern better without benchmark evidence.

## Run order

### 1. Narrow diagnostic FIRST

```powershell
python -m src.engcore.narrow_diagnostic --seed 215 --budget 40 --initial 12 --mode balanced --screen-device auto
```

It compares:

```text
fixed + RBF
learned noise + RBF
learned noise + Matern-5/2
```

This is the most important next result.

### 2. If learned-RBF wins the diagnostic

Run:

```powershell
python -m src.engcore.adaptive_focused --budget 80 --initial 12 --mode balanced --screen-device auto --noise learned --kernel rbf
```

### 3. If learned-Matern wins clearly

Run:

```powershell
python -m src.engcore.adaptive_focused --budget 80 --initial 12 --mode balanced --screen-device auto --noise learned --kernel matern25
```

### 4. Do not run a large suite yet

The next gate is:

```text
multimodal
narrow_optimum
deceptive_local
```

all at budget 80.

## Important interpretation

The synthetic `narrow_optimum` benchmark contains a very small-volume high peak.
Missing it does not automatically mean the optimizer is generally poor, but it
is a useful robustness stress test.

Current benchmarks still do not validate real engineering physics.
