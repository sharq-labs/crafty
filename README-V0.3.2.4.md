# Engineering AI Core V0.3.2.4 — COCO Target API Fix

## Root cause

On the tested environment:

```text
coco-experiment 2.8.2
Python 3.14
Windows
```

`cocoex.Problem.final_target_fvalue1` raises `AttributeError`.

V0.3.2.3 tried `Problem._f0` as a fallback. Runtime testing proved that this is
not independent: `_f0` itself calls the same broken
`final_target_fvalue1` property in this build.

Therefore V0.3.2.3's `_f0` fallback has been removed.

## Correct V0.3.2.4 fallback

The separate COCO class:

```python
from cocoex.function import BenchmarkFunction
```

exposes:

```python
BenchmarkFunction(...).best_value()
```

which calls COCO's C-level `coco_problem_get_best_value`.

For the noiseless BBOB suite the Validation Lab now resolves:

```text
fopt = BenchmarkFunction("bbob", function, dimension, instance).best_value()

final_target = fopt + 1e-8
```

The target remains benchmark metadata only and is never passed to Random,
Sobol, DE, CMA-ES, NGOpt, or our Stacked optimizer.

## Test order

```powershell
python -m src.engcore.coco_target_selftest
python -m src.engcore.coco_check
```

Expected:

```text
V0.3.2.4 COCO target compatibility self-test: PASS
```

and then:

```text
COCO/BBOB integration check: PASS
...
target source   : BenchmarkFunction.best_value_plus_1e-8
```

## First official pilot

```powershell
python -m src.engcore.coco_arena --functions 1,3,6,8,9,10,15,21,24 --dimensions 2 --instances 1,2,3 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_pilot_d2
```
