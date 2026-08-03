# Engineering AI Core V0.3.0 — Stacked Dual-GP Bayesian Optimization

V0.3.0 is a model-uncertainty release.

The previous experiments showed that no single surrogate configuration behaved
best on all three focused landscapes:

- fixed/RBF was excellent on multimodal
- learned-noise/Matern-2.5 was much stronger on narrow_optimum
- refinement was valuable on some landscapes but harmful when one surrogate
  became overconfident

V0.3.0 therefore stops choosing one GP globally.

## Architecture

```text
                         observations
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
       RBF ARD GP                      Matern-2.5 ARD GP
       bounded nugget                  bounded nugget
             |                                 |
             +---------------+-----------------+
                             |
                   efficient LOO CV
                             |
                   predictive stacking
                             |
                     w_RBF , w_Matern
                             |
                      Stacked LogEI
                             |
                 100k GPU global screen
                             |
                    diverse Top-8
                             |
             refine best 4 informed starts
                             |
              compare discrete vs refined
                             |
                         evaluate
```

## Important mathematical choice

Each member produces a log expected improvement value.

The mixture acquisition is:

```text
EI_mix(x) = w * EI_RBF(x) + (1-w) * EI_Matern(x)
```

and is evaluated stably as:

```text
logEI_mix =
    logaddexp(
        log(w)     + logEI_RBF,
        log(1 - w) + logEI_Matern
    )
```

No ordinary-EI conversion is required.

## How the weights are learned

Weights are NOT based on which model happened to propose the last evaluated
candidate.

BoTorch efficient Leave-One-Out cross-validation estimates each GP's
out-of-sample predictive density with its fitted hyperparameters held fixed.

A one-dimensional predictive-stacking objective chooses the weight that
maximizes:

```text
sum_i log(
    w * p_RBF(y_i | D_-i)
    + (1-w) * p_Matern(y_i | D_-i)
)
```

For small-data stability, neither member can receive less than 10% weight in
this first release.

## Nugget / noise model

Both members use the SAME bounded learned nugget in standardized output space:

```text
lower   = 1e-8
initial = 1e-4
upper   = 1e-3
```

This deliberately separates kernel-shape uncertainty from the earlier
fixed-vs-learned-noise confound.

The benchmarks are deterministic; the nugget is treated as numerical /
surrogate mismatch tolerance, not as a claim that the evaluator is physically
noisy.

## Search policy

Balanced mode:

```text
normal global pool          100,000
stagnation pulse            250,000
severe stagnation once      500,000

global Top-K                8
continuous refinement       best 4 starts only
refinement max iterations   50
```

No:
- UCB portfolio
- reward bandit
- manual model schedule
- forced uncertainty experiment
- trust region
- random global optimize_acqf restarts

## Validation order

### 0. Pure stacking math self-test

```powershell
python -m src.engcore.stacking_selftest
```

### 1. Reproducibility

```powershell
python -m src.engcore.stacked_repro --benchmark multimodal --seed 601 --budget 20 --initial 12 --mode fast --screen-device auto
```

Required:

```text
Exact X match       : True
Exact score match   : True
Exact weight match  : True
```

### 2. Narrow stress test at budget 40

```powershell
python -m src.engcore.stacked_single --benchmark narrow_optimum --seed 215 --budget 40 --initial 12 --mode balanced --screen-device auto
```

Watch:

```text
Best score
Final RBF weight
Final Matern weight
loo_updates
loo_failures
rbf_fit_failures
matern25_fit_failures
refinement_selected
discrete_selected
```

### 3. Multimodal budget 40

```powershell
python -m src.engcore.stacked_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --mode balanced --screen-device auto
```

### 4. Focused budget 80

```powershell
python -m src.engcore.stacked_focused --budget 80 --initial 12 --mode balanced --screen-device auto
```

The first serious gate is whether one fixed V0.3.0 configuration can remain
competitive on:

```text
multimodal
narrow_optimum
deceptive_local
```

without benchmark-specific switches.

### 5. Historical A/B

After the focused test is clean:

```powershell
python -m src.engcore.stacked_ab --benchmark multimodal --seed 601 --budget 80 --initial 12 --legacy-pool 100000 --chunk 1024 --mode balanced --screen-device auto
```

## Compatibility

The implementation targets:

```text
botorch >= 0.17.1
gpytorch >= 1.14
```

If efficient `loo_cv` is unavailable or fails, the engine keeps the previous
known-good stacking weight and reports `loo_failures`; it does not silently
invent a new weight.

## Scientific status

These benchmark functions are synthetic optimizer stress tests.

They do NOT validate engineering physics, CAD correctness, CFD/FEA fidelity,
or real-world safety.
