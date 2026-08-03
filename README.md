# Engineering AI Core V0.3.3 — Adaptive Stacked Optimizer with Safety Arbiter

Branch: `research/v0.3.3-adaptive`  
Scientific checkpoint: `df67b78722ec7508a0938171fc478cc26e73f29a`  
Baseline tag: `v0.3.2.6-stacked_v0301` (immutable)

## Goal

Add a **separately selectable** adaptive stacked optimizer that:

- infers search state only from legal black-box observations
- may propose alternate search knobs under evidence gates
- accepts an adaptive candidate only via a conservative safety arbiter
- preserves `stacked_v0301` unchanged

This is **not** a BBOB memorizer and does **not** claim universal superiority.

## Architecture audit (stacked_v0301 baseline)

| Stage | Behavior |
|---|---|
| Init | Sobol DOE in unit cube; all init evals count |
| Models | RBF ARD GP + Matern-2.5 ARD GP, bounded nugget |
| Fit | CPU `fit_gpytorch_mll`, warm-state between refits |
| Stacking | LOO predictive log densities → mixture weight |
| Acquisition | Stacked LogEI (`logaddexp` mixture) |
| Candidates | Large Sobol screen (GPU if available), diverse Top-K |
| Refinement | CPU continuous refine from informed starts |
| Fallback | Discrete vs refined by CPU acq; duplicate recovery |
| Stagnation | Pulse / severe pulse increases screen pool |
| Devices | Fit+refine CPU; screen optional CUDA |
| Budget | Exactly `initial_trials + smart_trials` objective calls |

## Validated V0.3.3 dual-proposal architecture

Each BO step (after the shared baseline model fit on current observations):

1. **identity proposal** — baseline `stacked_v0301` search knobs on the current adaptive-run observations  
2. **adaptive proposal** (optional) — same fitted models; alternate search knobs if the policy enables a proposal  
3. **`candidate_arbiter.py`** — conservative dual-proposal safety arbiter chooses exactly one unevaluated candidate  
4. **one objective evaluation** of the chosen proposal  

Rescue candidates are generated only when the policy authorizes them and **must pass through the same arbiter**. There is no rescue bypass.

### Adaptive proposer policy (`adaptive_policy.py`)

Not a generic continuous knob controller. It is a **mild / severe evidence-gated proposal policy**:

- early-neutral: identity-only until enough observations exist  
- evidence from search-failure signals plus capped model-support (model-alone cannot enable proposals)  
- **mild**: sustained evidence above the mild gate → modest pool / diversity / explore mix deltas; adaptive proposal may be generated  
- **severe**: stronger sustained evidence + cooldown clear → larger deltas and rescue authorization  
- recovery / cooldown reset escalation so proposals are not sticky  

The policy **does not** change the GP refit schedule and **never** forces adaptive refits.

### Safety arbiter (`candidate_arbiter.py`)

Adaptive replaces identity only under **component consensus**. Accept adaptive only if all hold:

- adaptive proposal generation was enabled by policy evidence  
- **RBF and Matern both must not prefer identity** (adaptive is not worse on either component)  
- **at least one component must strictly prefer adaptive**  
- **stacked mixture must prefer adaptive**  
- **component disagreement rejects adaptive** (one GP prefers adaptive, the other identity)  

Otherwise identity is executed.

### Budget / evaluation guardrails

| Check | Value |
|---|---|
| Extra objective evaluations from dual proposals | **0** |
| Hidden objective evaluations | **NO** |
| Adaptive forced GP refits | **0** |
| Strict objective budget | **YES** |
| Baseline `stacked_v0301` modified | **NO** |
| Benchmark-specific / fopt / instance selectors | **NO** |

## New modules

1. `landscape_diagnostics.py` — online features from X/y/budget/model stack stats only  
2. `adaptive_policy.py` — mild/severe evidence-gated adaptive *proposer*  
3. `candidate_arbiter.py` — consensus safety arbiter between identity and adaptive  
4. `adaptive_stacked_engine.py` — `AdaptiveStackedGPBOEngine` / `adaptive_stacked_v033`

## Validation registry

Algorithms include:

`cmaes, ngopt, stacked, adaptive_stacked`

## Tests

```powershell
.\.venv\Scripts\python.exe -m src.engcore.adaptive_stacked_selftest
.\.venv\Scripts\python.exe -m src.engcore.validation_fairness_selftest
```

## D3 validation status (external holdout)

Controlled BBOB D3 external replication (instances 71–80) showed the adaptive path to be **active and safe** under the dual-proposal arbiter.

This does **not** justify a universal superiority claim. V0.3.3 remains a research optimizer.

## Short smoke comparison (user/local)

```powershell
.\.venv\Scripts\python.exe -m src.engcore.validation_quick --dimensions 2 --instances 1 --budget-multiplier 10 --algorithms random,sobol,stacked,adaptive_stacked --stacked-mode fast --screen-device cpu --out validation_results/adaptive_smoke_v033
```

## Full COCO validation (manual; do not auto-run)

```powershell
.\.venv\Scripts\python.exe -m src.engcore.coco_arena --functions all --dimensions 2 --instances 1,2,3,4,5 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked,adaptive_stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_full_d2_v033

.\.venv\Scripts\python.exe -m src.engcore.coco_arena --functions all --dimensions 5 --instances 1,2,3,4,5 --budget-multiplier 20 --algorithms cmaes,ngopt,stacked,adaptive_stacked --stacked-mode fast --screen-device auto --stacked-refinement-backend torch --out validation_results/bbob_full_d5_v033
```

## Guardrail statements

| Check | Value |
|---|---|
| BASELINE STACKED_v0301 MODIFIED | **NO** |
| SEARCH BEHAVIOR CHANGED IN NEW OPTIMIZER | **YES** |
| BENCHMARK-SPECIFIC LOGIC ADDED | **NO** |
| HIDDEN OBJECTIVE EVALUATIONS ADDED | **NO** |
| STRICT BUDGET PRESERVED | **YES** |
| ADAPTIVE FORCED REFITS | **0** |
| UNIVERSAL SUPERIORITY CLAIM | **NO** |
