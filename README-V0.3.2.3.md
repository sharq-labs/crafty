# Engineering AI Core V0.3.2.3 — COCO 2.8.2 Compatibility Patch

## Why this patch exists

`coco-experiment 2.8.2` can provide a `cocoex.Problem` object that does not
expose:

```text
problem.final_target_fvalue1
```

even though older/current generated API documentation may list the property.

V0.3.2.3 removes the hard dependency on that Python property.

## Target resolution

Preferred path:

```text
problem.final_target_fvalue1
```

Compatibility fallback for the noiseless `bbob` suite:

```text
fopt = problem(x_ref) - problem._f0(x_ref)
final_target = fopt + 1e-8
```

The calibration is performed on a temporary metadata-only COCO problem.

Every optimizer gets a NEW COCO problem instance afterward, and the target is
never provided to the optimizer itself.

This preserves the black-box boundary of the optimization algorithms while
allowing the Validation Lab to compute target-based metrics.

The fallback is deliberately NOT enabled for arbitrary suites such as noisy or
bi-objective benchmarks.

## Check

```powershell
python -m src.engcore.coco_target_selftest
```

Then:

```powershell
python -m src.engcore.coco_check
```

Expected on coco-experiment 2.8.2 builds where the documented property is not
available:

```text
COCO/BBOB integration check: PASS
...
target source   : _f0_calibration_plus_1e-8
```

## First BBOB pilot

```powershell
python -m src.engcore.coco_arena --functions 1,3,6,8,9,10,15,21,24 --dimensions 2 --instances 1,2,3 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_pilot_d2
```

The progress output also prints the target-resolution source for auditability.
