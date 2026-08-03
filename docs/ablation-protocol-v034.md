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

## 3. Determinism classification

**Strongly controlled causal ablation.** All sampling, fitting, screening,
and refinement seeds are deterministic functions of (seed, step, fit_round);
device is fixed to CPU; configuration is identical across arms.

Residual nondeterminism, declared: the tag-frozen `fast` mode dictionary sets
`refinement_timeout_sec = 2.0`, a wall-clock cutoff inside
`optimize_acqf`. Removing it would alter the frozen research treatment, so it
stays. Mitigation: idle machine, and a pre-campaign determinism spot check
(one case run twice; `best_f` sequences must be identical) recorded alongside
the goldens.

With one seed per case at D=2, the campaign is **directional causal evidence
only**. It supports attribution decisions for the merge; it does not support
freeze-level performance claims. Any future freeze-level claim requires a
D=5 / budget-100 / >=3-seeds-per-case tier (not scheduled).

## 4. Primary endpoints and pre-declared decision rules

Primary endpoints: pairwise fractional win-share over the matched problem
set (exact ties split fractionally), for **(B vs A)** and **(C vs B)**.

Dead zone: win-share in **[42%, 58%]** = "no attribution possible" for that
contrast. Declared before running; not adjustable afterwards.

| # | Outcome | Pre-declared action |
|---|---|---|
| R1 | B > A above dead zone | Per-step weight refresh is the active ingredient. Document; fresh-weights engine becomes a recorded research finding (still no superiority claim). |
| R2 | A > B above dead zone (refresh harmful) | Amend the branch to revert per-step refresh in `adaptive_stacked_v034` **before** merge. Gates: re-run `adaptive_stacked_selftest` (recorded in README-V0.3.4), re-run arm C at the amended tip, re-tag `v0.3.4-rc2`. |
| R3 | C > B above dead zone | Adaptive machinery earns its complexity beyond fresh weights. Document; merge as-is. |
| R4 | Any endpoint in dead zone | No attribution for that contrast. Merge as-is with `adaptive_stacked_v034` explicitly labeled *behaviorally changed, performance-unvalidated* in README-V0.3.4 and in any future solver descriptor. The open question files as a follow-up hypothesis for the deferred multi-seed tier. |

The campaign runs **once**. No re-rolls, no post-hoc endpoint changes.
The merge decision itself remains with the product owner in all branches.

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
  versions, platform — written at campaign start.
- `progress.jsonl`: append-only fsync'd journal; one record per completed
  run (including the per-run convergence curve, which `runs.csv` does not
  carry) and one per failure. A crash loses at most the in-flight run.
- Failure policy: a case with any failed arm is excluded from ALL arms in
  the matched summary (paired contrasts stay paired); the failure and any
  completed sibling runs remain in `progress.jsonl`. Excluded-case count is
  reported in the summary output and the completion record.
- Official COCO observer logs are written per arm with scientific IDs for
  cocopp post-processing.

## 7. Apparatus-equivalence goldens (precondition)

Before tagging `v0.3.4-rc`, record goldens for `stacked_v0301` on a small
fixed case set under the registered configuration (scipy / cpu / fast), on
**both** `main` and the branch tip, and diff `best_f` per case. The branch
rewrote the validation adapter layer; these goldens are the evidence that
arm A is the same experiment as the published baseline. A mismatch is a
merge-review item and must be adjudicated before the campaign is
interpreted.
