# Engineering AI Core V0.3.2.6 — Validation Fairness Hardening

Validation-infrastructure release only. Optimizer search behavior is unchanged
from V0.3.2.5 / stacked_v0301.

## Changes

1. **Local arena factory contract**
   - `func_factory(algorithm=None) -> (func, cleanup)`
   - Local quick arena no longer binds the algorithm name as the objective
   - Arena no longer swallows `TypeError` from factories

2. **Strict budget assertion for every adapter**
   - Central `assert_exact_budget()` runs inside `_trace(...)`
   - Applies to random, sobol, de, ngopt, cmaes, stacked

3. **Exact-tie ranking**
   - Average ranks for exact score ties
   - `win_share`: fractional credit `1/N` among exact bests
   - `wins` / `unique_wins`: integer sole-best count only

4. **COCO nested result directories**
   - Parent directories are created before `cocoex.Observer(...)`
   - Actual `observer.result_folder` is recorded (COCO uniqueness retained)

5. **Observer lifecycle policy (cocoex 2.8.2 evidence)**
   - `Observer.free` exists and is callable on the public class
   - Calling it raises `AttributeError: ... no attribute '__dealloc__'`
   - Therefore V0.3.2.6 does **not** call `Observer.free()`
   - Required finalization remains `problem.free()` (+ `suite.free()`)
   - After `problem.free()`, COCO `.info` / `.dat` logs are present and readable

## Fairness self-test

```powershell
.\.venv\Scripts\python.exe -m src.engcore.validation_fairness_selftest
```

Also:

```powershell
.\.venv\Scripts\python.exe -m src.engcore.validation_selftest
.\.venv\Scripts\python.exe -m src.engcore.coco_target_selftest
.\.venv\Scripts\python.exe -m src.engcore.coco_check
```

## Explicitly unchanged

- GP kernels, LOO stacking, LogEI
- Screen pools, refinement, stagnation pulses, stacked modes
- NGOpt / CMA search configuration
- Optimizer architecture
