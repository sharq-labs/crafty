# Engineering AI Core V0.3.2.5 — Official COCO Observer Integration

This release removes all fragile target-value workarounds.

The tested coco-experiment 2.8.2 wheel has:

```text
Problem.final_target_fvalue1 -> unavailable
Problem._f0                  -> depends on the broken property
cocoex.function              -> unavailable
```

V0.3.2.5 therefore does not reverse engineer BBOB fopt.

## Live arena

The live comparison still gives trustworthy same-problem metrics:

```text
best objective value
per-problem rank
wins
mean rank
wall time
```

Unknown additive objective offsets do not affect ranking within the exact same
function / dimension / instance case.

## Official BBOB metrics

Each algorithm gets its own real:

```python
cocoex.Observer("bbob", ...)
```

COCO writes native experiment logs, including its own target triggers.

Use:

```powershell
python -m cocopp <folder1> <folder2> <folder3>
```

after the arena. The arena prints the exact result folders.

`cocopp` is now the authority for official target-based BBOB performance such
as ERT and ECDF, instead of our custom code depending on a broken binding
property.

## Checks

```powershell
python -m src.engcore.coco_target_selftest
python -m src.engcore.coco_check
```

Expected on the affected wheel:

```text
COCO/BBOB integration check: PASS
...
final target    : unavailable via this Python binding
target source   : unavailable_use_cocopp
official metrics: COCO Observer + cocopp
```

## First pilot

```powershell
python -m src.engcore.coco_arena --functions 1,3,6,8,9,10,15,21,24 --dimensions 2 --instances 1,2,3 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_pilot_d2
```

At the end, copy the three COCO observer folders printed by the command and
pass them to `python -m cocopp`.
