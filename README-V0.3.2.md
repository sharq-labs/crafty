# Engineering AI Core V0.3.2 — Optimizer Validation Lab

This release deliberately pauses optimizer invention.

The next question is no longer:

> Can we improve one synthetic benchmark score?

It is:

> Across standard black-box optimization landscapes, dimensions, instances,
> and budgets, where does our optimizer actually rank against strong,
> independent baselines?

## Why COCO/BBOB

COCO's `bbob` suite is a standard continuous black-box benchmark suite.

The official suite exposes 24 noiseless single-objective functions and standard
dimensions including:

```text
2, 3, 5, 10, 20, 40
```

A COCO problem is callable, exposes its dimension and region-of-interest
bounds, and tracks objective evaluations.

V0.3.2 never gives the optimizer the reference target. The target is read only
for AFTER-RUN metrics.

## Arena algorithms

Always available:

```text
random
sobol
de       = exact-budget DE/rand/1/bin
stacked  = our V0.3.0.1 Stacked Dual-GP optimizer
```

Optional:

```text
ngopt    = Nevergrad NGOpt
cmaes    = pycma CMA-ES
```

The internal DE implementation is included so we always have a serious global
evolutionary baseline with an exact evaluation budget.

## Fairness rules

Every optimizer receives:

```text
same function instance
same decision bounds
same black-box evaluation budget
deterministic seed
```

Each optimizer gets a FRESH COCO problem object so evaluation counters cannot
leak between methods.

The optimization algorithm never sees:

```text
final_target_fvalue1
future observations
other optimizer results
```

## Metrics

Raw function values are not averaged across unrelated functions.

V0.3.2 reports:

```text
per-problem rank
mean / median rank
wins
final target hit rate
fraction of standard target deltas reached
median log10 final target gap
wall time
```

Standard target deltas used by this first lab:

```text
1e2
1e1
1e0
1e-1
1e-2
1e-4
1e-6
```

This is intentionally closer to target-based black-box benchmarking than
averaging arbitrary raw scores.

## Budget

The BBOB command uses:

```text
budget = budget_multiplier × dimension
```

Example:

```text
dimension 2, multiplier 20 -> 40 evaluations
dimension 5, multiplier 20 -> 100 evaluations
dimension 10, multiplier 20 -> 200 evaluations
```

This lets us study scaling rather than giving all dimensions the same budget.

---

# Run order

## 1. Environment doctor

```powershell
python -m src.engcore.validation_doctor
```

This reports:

```text
required:
numpy scipy torch botorch gpytorch

optional:
cocoex
nevergrad
cma
```

## 2. Validation self-test

No COCO / Nevergrad / CMA required:

```powershell
python -m src.engcore.validation_selftest
```

Expected:

```text
V0.3.2 Validation Lab self-test: PASS
```

## 3. Local quick arena

Start small:

```powershell
python -m src.engcore.validation_quick --dimensions 2 --budget-multiplier 15 --algorithms sobol,de,stacked --stacked-mode fast --screen-device auto
```

Then:

```powershell
python -m src.engcore.validation_quick --dimensions 2,5 --budget-multiplier 20 --algorithms random,sobol,de,stacked --stacked-mode fast --screen-device auto
```

Results are written under:

```text
validation_results/local_quick/
```

## 4. Optional independent baselines

Install:

```powershell
pip install nevergrad cma
```

Then:

```powershell
python -m src.engcore.validation_quick --dimensions 2,5 --budget-multiplier 20 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto
```

Nevergrad is used through its ask/tell API with an exact number of evaluations.

CMA-ES uses pycma with bounded coordinates and `maxfevals`; if a partial
generation remains at the strict budget edge, the unused evaluations are
filled without updating an invalid partial CMA generation.

## 5. Official COCO/BBOB integration

COCO's official Python interface is `cocoex`.

The official documentation builds it from the `numbbo/coco` source repository.
On Windows / very new Python versions this may be the least convenient
dependency in the lab, so it is kept optional rather than silently replacing
it with a lookalike package.

After `cocoex` is available:

```powershell
python -m src.engcore.coco_check
```

Expected:

```text
COCO/BBOB integration check: PASS
```

## 6. First official BBOB pilot

Do NOT start with all 24 × many dimensions immediately.

```powershell
python -m src.engcore.coco_arena --functions 1,3,6,8,9,10,15,21,24 --dimensions 2,5 --instances 1,2,3 --budget-multiplier 20 --algorithms sobol,de,stacked --stacked-mode fast --screen-device auto
```

That is:

```text
9 functions
× 2 dimensions
× 3 instances
= 54 independent problem cases
```

and 162 optimizer runs for 3 algorithms.

## 7. Strong-baseline pilot

When Nevergrad and CMA-ES are available:

```powershell
python -m src.engcore.coco_arena --functions 1,3,6,8,9,10,15,21,24 --dimensions 2,5 --instances 1,2,3 --budget-multiplier 20 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto
```

## 8. Full BBOB gate

Only after runtime and metrics look correct:

```powershell
python -m src.engcore.coco_arena --functions all --dimensions 2,3,5,10 --instances 1,2,3,4,5 --budget-multiplier 30 --algorithms sobol,de,cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --out validation_results/bbob_full_gate
```

This is deliberately expensive.

---

# What counts as optimizer progress now?

A new optimizer version should not be accepted because it wins one seed.

It should improve one or more of:

```text
mean rank
target fraction
target hit rate
scaling with dimension
wall time
reliability
```

without a large regression elsewhere.

## Next milestones after V0.3.2

Validation Lab is only the first half of the "100% optimizer" goal.

Planned gates:

```text
V0.3.2  BBOB + baseline arena
V0.3.3  multi-seed / ECDF / ERT reporting
V0.3.4  noisy benchmark gate
V0.3.5  constrained optimization gate
V0.3.6  multi-objective Pareto / hypervolume gate
V0.3.7  mixed integer / categorical variables
V0.3.8  batch / parallel expensive evaluations
V0.3.9  automatic algorithm selection
V1.0    optimizer validation release
```

The point of V0.3.9 is important:

If BBOB reveals that no one optimizer dominates all function families, the
final system should learn which search strategy to allocate budget to instead
of forcing a single GP architecture onto every engineering problem.

## Scientific status

This lab validates optimization behavior.

It still does NOT validate CAD, FEA, CFD, electromagnetics, thermal simulation,
or any real engineering design.
