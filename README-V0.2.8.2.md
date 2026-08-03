# Engineering AI Core V0.2.8.2

V0.2.8.2 is a correctness + reproducibility + performance-control release.

It deliberately does NOT add a new acquisition portfolio, a new kernel, TuRBO,
or GPU hybrid screening yet.

## Evidence that drove this release

For the same 40-evaluation multimodal case:

```text
CUDA balanced:
score ≈ 62.5625
wall  ≈ 50.3 s

CPU balanced:
score ≈ 62.5563
wall  ≈ 23.8 s
```

The score was effectively identical while CPU was much faster.

Profiling also showed acquisition optimization dominated runtime.

Therefore V0.2.8.2 defaults to CPU for the current low-dimensional q=1 regime.

## V0.2.8.2 changes

### Reproducibility
Every `optimize_acqf` call runs inside BoTorch `manual_seed(...)`.

### Safe GP fitting
A model state checkpoint is captured before hyperparameter fitting.
If fitting throws or produces non-finite state:
- roll back
- do not save the failed state as a future warm start.

### Timeout
Every acquisition optimization has `timeout_sec`.

### No forced batch_limit=4
BoTorch is allowed to batch the restart optimization itself.

### Duplicate protection
A candidate too close to an already evaluated point is rejected and replaced
using a deterministic chunked acquisition search.

### CPU-first
`--device cpu` is the default.
CUDA remains available for controlled comparison.

### Adaptive compute
Normal iterations use the selected mode.
After sustained stagnation, one stronger search pulse is triggered.
The acquisition remains LogEI / LogCEI; only search effort changes.

### Fair constraints
Custom-suite default is:
```text
--constraint-mode penalty
```
so V0.2.8.2 receives the same evaluator information as Legacy.

Continuous constraint margins remain a separate experiment:
```text
--constraint-mode margins
```

## DO NOT start with the large suite

### 1. Syntax/import check
```powershell
python -m src.engcore.logei_single --help
```

### 2. Reproducibility test FIRST
```powershell
python -m src.engcore.logei_repro --benchmark multimodal --seed 601 --budget 24 --initial 12 --mode balanced --device cpu
```

Pass condition:
```text
Exact X match     : True
Exact score match : True
```

If this fails, do not benchmark.

### 3. 40-budget smoke/performance test
```powershell
python -m src.engcore.logei_single --benchmark multimodal --seed 601 --budget 40 --initial 12 --mode balanced --device cpu
```

Watch:
- wall time
- global_opt_s
- stagnation_pulses
- duplicates
- fit failures
- global optimization failures

### 4. Repeat the exact same command
The best score and trajectory should reproduce.

### 5. Difficult focused cases
```powershell
python -m src.engcore.logei_single --benchmark narrow_optimum --seed 215 --budget 40 --initial 12 --mode balanced --device cpu
```

```powershell
python -m src.engcore.logei_single --benchmark deceptive_local --seed 213 --budget 40 --initial 12 --mode balanced --device cpu
```

### 6. Only after those pass, A/B/C
```powershell
python -m src.engcore.logei_ab --benchmark multimodal --seed 601 --budget 80 --initial 12 --legacy-pool 100000 --chunk 1024 --mode balanced --device cpu --constraint-mode penalty
```

### 7. Suite comes last
```powershell
python -m src.engcore.logei_suite --runs 3 --budget 80 --initial 12 --legacy-pool 75000 --chunk 1024 --mode balanced --device cpu --constraint-mode penalty
```

## What is intentionally NOT in V0.2.8.2

Not yet:
- Matern kernel switch
- GPU-screening hybrid
- TuRBO
- acquisition portfolios
- UCB/novelty mixtures
- many always-on local trust regions

Those need isolated ablation evidence first.

## Important

These are synthetic optimizer benchmarks.
They do not validate engineering physics.
