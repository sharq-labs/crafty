# V0.3.4 Three-Way Ablation — Registered Protocol

Status: **PRE-REGISTERED, NOT YET RUN.**
This protocol must be committed and tagged (`v0.3.4-rc`) before the registered
campaign is executed. Results obtained under any other apparatus or
configuration are exploratory and must not be merged into the registered
dataset.

## 1. Scientific question

Decompose the V0.3.4 adaptive optimizer's behavior into two causal factors,
under identical problems, seeds, and budgets:

- **B − A**: the effect of per-step stacking-weight refresh alone
  (`stacked_fresh_weights_v034` vs frozen baseline `stacked_v0301`).
- **C − B**: the marginal effect of the adaptive-proposal / safety-arbiter
  machinery on top of fresh weights
  (`adaptive_stacked_v034` vs `stacked_fresh_weights_v034`).

`adaptive_stacked_v034` bundles both changes; without arm B any comparison
against the baseline is confounded.

## 2. Registered configuration

Exactly one command, run once, from the tagged apparatus (`v0.3.4-rc`), on a
single otherwise-idle machine, using the repository venv:

```
.venv/Scripts/python.exe -m src.engcore.v034_ablation_arena \
  --functions all \
  --dimensions 2 \
  --instances 71,72,73,74,75 \
  --budget-multiplier 20 \
  --seed 123 \
  --stacked-mode fast \
  --screen-device cpu \
  --stacked-refinement-backend scipy \
  --coco-observer on \
  --out validation_results/v034_ablation_registered_d2_i71_75
```

- Expected cases: 24 functions x 1 dimension x 5 instances = **120 matched
  problems**; 3 arms = **360 engine runs**; budget 40 evaluations per run.
- Per-case seed: `123 + 10000*instance + 100*function + dim`, identical
  across all three arms.
- `--stacked-refinement-backend scipy`: the frozen engines' native, seeded
  refinement path (`seed + 900_000 + step`). The torch refinement wrapper is
  validation-only glue that discards the seed (`del seed`) and is therefore
  excluded from the registered configuration.
- `--screen-device cpu`: removes CUDA-availability dependence.
- All three arms run under exactly the same configuration. If any instance
  must be rerun for any reason, the entire campaign is rerun; partial mixes
  across apparatus or configuration versions are prohibited.

## 3. Determinism classification and apparatus-validity rule

**Strongly controlled causal ablation.** All sampling, fitting, screening,
and refinement seeds are deterministic functions of (seed, step, fit_round);
device is fixed to CPU; configuration is identical across arms.

Residual nondeterminism, declared: the tag-frozen `fast` mode dictionary sets
`refinement_timeout_sec = 2.0`, a wall-clock cutoff inside
`optimize_acqf`. Removing it would alter the frozen research treatment, so it
stays. Observability without modifying frozen code: per-run refinement
telemetry (`refinement_attempts`, `refinement_s_total`,
`refinement_s_mean`) is recorded into every trace's metadata by the
apparatus-layer adapters and journaled; a per-attempt mean approaching
2.0 s is the registered warning signal. Exact per-call timeout-hit
detection is **not** possible without editing frozen engine files and is
therefore not claimed. The manifest records the numerical threading
environment (OMP/MKL/OpenBLAS/NumExpr thread settings, torch thread count,
CPU count).

**Pre-registered apparatus-validity rule:** if the pre-campaign
full-trajectory determinism replay fails, or if refinement telemetry or
trajectory checks indicate that wall-clock truncation altered execution
between repeats or asymmetrically across arms, the campaign is **INVALID AS
AN APPARATUS RUN** and must not be interpreted. Remediate the apparatus and
rerun the complete campaign. This is apparatus failure, not performance
re-rolling.

With one seed per case at D=2, the campaign is **directional causal evidence
only**. It supports attribution decisions for the merge; it does not support
freeze-level performance claims. Any future freeze-level claim requires a
D=5 / budget-100 / >=3-seeds-per-case tier (not scheduled).

## 4. Primary endpoints and pre-declared decision rules

**Registered analysis code:** `src/engcore/v034_ablation_analysis.py`,
committed and tagged with the apparatus. Its output
(`ablation_analysis.json`) is the only analysis feeding these rules.

**Primary endpoints (matched complete cases — every arm completed):**
for **(B vs A)** and **(C vs B)**, on paired per-problem `best_f`:

- wins / losses / ties (tie = exact `best_f` equality, lab convention),
  win-share (ties split fractionally);
- exact two-sided paired **sign test** on non-ties;
- **Holm correction** across the two primary contrasts (family alpha 0.05);
- **Clopper–Pearson CI for the win probability among non-ties at the
  Bonferroni-adjusted 97.5% level** (family 95%);
- effect size: win probability and rank-biserial delta = 2·p̂ − 1.

**Pre-registered decision semantics (per contrast):**

- CI entirely above 0.50 → **positive evidence**
- CI entirely below 0.50 → **harmful evidence**
- CI crossing 0.50 → **inconclusive**

The Holm-adjusted p-values are reported alongside; if CI position and
Holm-adjusted significance ever disagree at the margin, the CI position
governs, as registered here. Win-share within [0.42, 0.58] is reported as a
**secondary descriptive** "small practical effect at this design size"
band; it has **no decision authority**.

| # | Outcome | Pre-declared action |
|---|---|---|
| R1 | B vs A positive | Per-step weight refresh is the active ingredient. Document; fresh-weights engine becomes a recorded research finding (still no superiority claim). |
| R2 | B vs A harmful (refresh harmful) | Amend the branch to revert per-step refresh in `adaptive_stacked_v034`. **Any registered-evidence-driven algorithm change invalidates the old results as validation of the new algorithm**: create `v0.3.4-rc2` and rerun the **complete three-arm matched campaign** under the one rc2 apparatus. Never combine arms across RC apparatus versions into one causal dataset. The rc1 campaign is archived as evidence about the rc1 treatments only. |
| R3 | C vs B positive | Adaptive machinery earns its complexity beyond fresh weights. Document; merge as-is. |
| R4 | Inconclusive endpoint(s) | No attribution for that contrast. Merge as-is with `adaptive_stacked_v034` explicitly labeled *behaviorally changed, performance-unvalidated* in README-V0.3.4 and in any future solver descriptor. The open question files as a follow-up hypothesis for the deferred multi-seed tier. |

Rule R2's rerun requirement applies to **any** treatment-changing
modification triggered by registered evidence, not only weight-refresh
reversion. The campaign runs **once per RC apparatus**. No re-rolls, no
post-hoc endpoint changes. The merge decision itself remains with the
product owner in all branches.

**Secondary endpoint — all-case robustness:** the same two contrasts over
**all attempted cases**, with a failed arm scored as a loss against a
completed arm (two failures tie). A treatment-dependent failure is evidence
about that treatment; failure-dependent cases must not disappear from the
final judgment. Descriptive, reported with the same statistics, never
decision-driving.

## 5. Exploratory-evidence disclosure

Before this registration, an exploratory run was executed on the pre-RC
apparatus: all 24 functions, D=2, **instance 71 only**, budget 40, with the
**unseeded torch refinement backend** and `--screen-device auto`
(`validation_results/v034_ablation_d2_i71_all`). Its direction: baseline
`stacked_v0301` led (mean rank 1.79, win-share ~57%), `adaptive_stacked_v034`
second (2.08), `stacked_fresh_weights_v034` third (2.13).

This peek is disclosed here because it preceded registration. The registered
campaign **re-runs instance 71 under the registered apparatus**; the
exploratory dataset remains archived as exploratory evidence only and is
never combined with the registered dataset.

## 6. Evidence handling

- `manifest.json`: git commit + dirty state, full configuration, package
  versions, platform, numerical threading environment — written at
  campaign start.
- `progress.jsonl`: append-only fsync'd journal; one record per completed
  run (including the per-run convergence curve, which `runs.csv` does not
  carry, and per-run refinement telemetry) and one per failure with arm
  identity and reason. A crash loses at most the in-flight run.
- **Failures are first-class scientific outcomes.** The registered report
  must include, per arm: attempted cases, successful valid cases, failed
  cases with reasons, and cases excluded from the matched set
  (NON_CONVERGED: not applicable — the legacy lab evaluator contract has
  no such status). The arena emits this per-arm accounting in its
  completion record and console summary; the registered analysis
  reproduces it in `ablation_analysis.json`.
- Matched-case policy: a case with any failed arm is excluded from the
  matched **paired-performance** endpoint for ALL arms (contrasts stay
  paired), but that case fully participates in the all-case robustness
  endpoint, and the failure itself is reported. Failure-dependent cases
  never disappear from the final judgment.
- Official COCO observer logs are written per arm with scientific IDs for
  cocopp post-processing.
- Apparatus verification is versioned with the apparatus:
  `src/engcore/v034_apparatus_selftest.py` (arena persistence, failure
  tolerance, per-arm accounting, registered-analysis statistics) and
  `src/engcore/v034_golden_parity.py` (full-trajectory baseline parity).

## 7. Apparatus-equivalence goldens (precondition)

Before tagging `v0.3.4-rc`, run `v034_golden_parity` for `stacked_v0301`
on **all 24 BBOB functions**, D=2, **instance 1** (disjoint from the
registered campaign instances), budget 40, registered configuration
(scipy / cpu / fast), same seed formula — on **both** the `main` tree and
the branch tip, comparing the **full evaluation trajectories** (every
evaluated x vector and every returned f), not only final objective values,
plus a tree-B repeat pass for full-trajectory determinism. The branch
rewrote the validation adapter layer; this parity run is the evidence that
arm A is the same experiment as the published baseline. Any mismatch is
reported exactly (first divergent evaluation index) and must be adjudicated
before the campaign is interpreted. If parity or the determinism repeat
fails, the apparatus-validity rule of §3 applies.
