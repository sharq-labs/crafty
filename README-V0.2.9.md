# Engineering AI Core V0.2.9 — Global-First Hybrid

V0.2.9 changes the search architecture based on the measured V0.2.8.3 result.

## Why this version exists

On the 80-evaluation multimodal case:

```text
Legacy          ≈ 150.27
V0.2.7          ≈ 154.98
V0.2.8.3 LogEI  ≈ 106.21
```

V0.2.8.3 was reproducible and numerically clean, but continuous multi-start
acquisition optimization did not provide enough global coverage.

V0.2.9 therefore does not ask `optimize_acqf` to discover the global basin.

## Architecture

```text
CPU exact GP
    ↓
LogEI / LogCEI
    ↓
large full-domain Sobol candidate pool
    ↓
GPU chunked acquisition scoring
    ↓
Top-K acquisition candidates
    ↓
50% diversity coverage + 50% pure acquisition rank
    ↓
optional CPU refinement from those informed starts
    ↓
compare discrete and refined candidate using CPU acquisition
    ↓
evaluate best candidate
```

## What was intentionally removed from the main search

No:
- random global optimize_acqf restarts
- always-on local trust regions
- UCB / novelty acquisition mixtures
- acquisition portfolio
- TuRBO
- Matern switch

Those are not needed to test the global-first hypothesis.

## What remains from V0.2.8.3

- CPU GP fitting
- reproducible seeded workflow
- fixed scale-aware deterministic noise
- safe GP fit rollback
- duplicate protection
- LogEI / LogCEI
- no numerical-warning suppression
- fair penalty-mode benchmarking

## Stagnation behavior

Normal iteration:

```text
100k global candidates
```

Balanced stagnation pulse:

```text
250k global candidates
more Top-K seeds
stronger refinement
```

The acquisition function does not change.

The search actually broadens instead of simply repeating more random
continuous restarts.

## Search modes

### discrete

```text
global screening
→ best discrete candidate
```

This answers:

> How much of V0.2.9's performance comes from dense global coverage alone?

### hybrid

```text
global screening
→ informed Top-K starts
→ CPU continuous refinement
→ choose best acquisition
```

This answers:

> Does continuous refinement add enough quality to justify its cost?

## Validation order

Do NOT run the large statistical suite first.

### 1. Reproducibility

```powershell
python -m src.engcore.hybrid_repro --benchmark multimodal --seed 601 --budget 20 --initial 12 --search hybrid --mode fast --screen-device auto
```

Desired:

```text
Exact X match     : True
Exact score match : True
```

### 2. 40-budget discrete-only multimodal

```powershell
python -m src.engcore.hybrid_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --search discrete --mode balanced --screen-device auto
```

### 3. Same run with refinement

```powershell
python -m src.engcore.hybrid_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --search hybrid --mode balanced --screen-device auto
```

Compare:
- best score
- wall time
- refinement_selected
- discrete_selected
- screen_scoring_s
- refinement_s

### 4. Focused three-problem check

```powershell
python -m src.engcore.hybrid_focused --budget 40 --initial 12 --search hybrid --mode balanced --screen-device auto
```

Problems:

```text
multimodal       seed 601
narrow_optimum   seed 215
deceptive_local  seed 213
```

### 5. Full-budget four-way A/B

Only after the above runs are clean:

```powershell
python -m src.engcore.hybrid_ab --benchmark multimodal --seed 601 --budget 80 --initial 12 --legacy-pool 100000 --chunk 1024 --mode balanced --screen-device auto
```

This compares:

```text
Legacy
V0.2.7
V0.2.9 discrete
V0.2.9 hybrid
```

The key number is:

```text
Hybrid - Discrete
```

If refinement adds negligible score but large wall time, remove refinement.

If discrete / hybrid still cannot match Legacy, the next investigation should
focus on the GP/acquisition model difference rather than adding more search
machinery.

## Notes

Current benchmarks are synthetic optimizer tests only.
They are not validated engineering physics.
