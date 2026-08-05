# Engineering AI Core V0.3.4 — Logic Hardening + Registered Causal Ablation

**Registered conclusion: INCONCLUSIVE on both primary contrasts. Decision rule
R4 applies. No performance claim is made for `adaptive_stacked_v034` or
`stacked_fresh_weights_v034`.**

## 1. RC identity

| Item | Value |
|---|---|
| RC tag | `v0.3.4-rc` (annotated) |
| Frozen SHA | `32b88b1d6b55eb0361527b6bdaab1a49208222c4` |
| Branch | `research/v0.3.4-logic-hardening` |
| Campaign checkout | fresh detached worktree at the tag; `git status` clean; manifest records `tracked_dirty: false` |
| Frozen baseline | tag `v0.3.2.6-stacked_v0301`; the five frozen engine files are byte-identical (test-enforced) |
| Registered protocol | `docs/ablation-protocol-v034.md` (committed and tagged **before** the campaign) |
| Registered analysis | `src/engcore/v034_ablation_analysis.py` (committed and tagged before the campaign) |

Arms: **A** `stacked_v0301` (frozen baseline) · **B** `stacked_fresh_weights_v034`
(per-step stacking-weight refresh only) · **C** `adaptive_stacked_v034`
(fresh weights + adaptive proposal / safety arbiter).

## 2. Environment

Python 3.14.2, Windows-11-10.0.26200-SP0, 24 CPUs, torch threads 16
(OMP/MKL/OpenBLAS/NumExpr unset). numpy 2.5.1, scipy 1.18.0,
scikit-learn 1.9.0, torch 2.13.0+cu132, gpytorch 1.15.2, botorch 0.18.1,
cocoex 2.8.2. Campaign start 2026-08-04T17:07:37Z. Full record:
`validation_results/v034_ablation_registered_d2_i71_75/manifest.json`.

Registered command (executed verbatim, once):

```
python -m src.engcore.v034_ablation_arena --functions all --dimensions 2 \
  --instances 71,72,73,74,75 --budget-multiplier 20 --seed 123 \
  --stacked-mode fast --screen-device cpu --stacked-refinement-backend scipy \
  --coco-observer on --out validation_results/v034_ablation_registered_d2_i71_75
```

## 3. Apparatus validity

The pre-registered apparatus-invalidity rule was **not** triggered. The
campaign is valid as an apparatus run.

| Check | Result |
|---|---|
| Runs completed | 360 / 360 (24 functions x 5 instances x 3 arms) |
| Exact evaluation budget | 40 on every run, all 360 (`assert_exact_budget` on every arm) |
| Hidden objective evaluations | none (counting-wrapper fairness selftest covers all arms incl. adaptive) |
| Non-finite candidates / clipped / non-finite objectives | 0 / 0 / 0 |
| Refinement failures | 0 |
| Adaptive forced refits | 0 (invariant held) |
| Pre-RC replay determinism | Arm A 24/24, Arm B 24/24, Arm C 24/24 — full trajectories, observer ON for B and C |
| Pre-RC parity vs `main` (6a589ca) | Arm A 24/24 full trajectories bit-exact |
| Selftests at RC checkout | logic-hardening PASS, fairness PASS, apparatus+analysis PASS |

## 4. Per-arm accounting

| Arm | Attempted | Completed | Failed | Excluded by matching |
|---|---|---|---|---|
| `stacked_v0301` | 120 | 120 | 0 | 0 |
| `stacked_fresh_weights_v034` | 120 | 120 | 0 | 0 |
| `adaptive_stacked_v034` | 120 | 120 | 0 | 0 |

No failures, no setup failures, no excluded cases; matched set = all 120
problems. NON_CONVERGED is not applicable (the legacy lab evaluator
contract has no such status).

## 5. PRIMARY (function-clustered) — B vs A

Effect of per-step stacking-weight refresh alone.

| Quantity | Value |
|---|---|
| Function directions | **+11 positive, −9 negative, 3 tied, 1 all-tied** (of 24) |
| Sign-test sample | 20 non-tied functions |
| Exact two-sided sign test | p = 0.824 (Holm-adjusted 1.000) |
| Function-level win probability | 0.550, CI **[0.288, 0.793]** (97.5%, Bonferroni-adjusted) |
| Effect size (rank-biserial) | +0.100 |
| **Verdict** | **INCONCLUSIVE** (CI crosses 0.50) |

## 6. PRIMARY (function-clustered) — C vs B

Marginal effect of the adaptive proposal / safety-arbiter path on top of
fresh weights.

| Quantity | Value |
|---|---|
| Function directions | **+2 positive, −1 negative, 0 tied, 21 all-tied** (of 24) |
| Sign-test sample | 3 non-tied functions |
| Exact two-sided sign test | p = 1.000 (Holm-adjusted 1.000) |
| Function-level win probability | 0.667, CI **[0.066, 0.996]** (97.5%) |
| Effect size (rank-biserial) | +0.333 |
| **Verdict** | **INCONCLUSIVE** (CI crosses 0.50) |

**The dominant finding here is the 21 all-tied functions**: on 117 of 120
problems arms C and B produced identical results. Treatment-activation
diagnostics explain why — see §8.

## 7. Descriptive 120-case results (secondary — NOT independent evidence)

Instances within a function are not independent; these counts must not be
read as n=120 inferential evidence.

| Contrast | Wins | Losses | Ties | Win share |
|---|---|---|---|---|
| B vs A | 57 | 53 | 10 | 0.517 (inside the descriptive small-effect band) |
| C vs B | 2 | 1 | 117 | 0.504 (inside the band) |

Three-way lab summary (descriptive): `stacked_v0301` mean rank 2.029 with
**53 sole-best wins**; `adaptive_stacked_v034` mean rank 1.983 and
`stacked_fresh_weights_v034` 1.988, each with 1 sole win and equal 31.833
win share. The apparent tension — baseline has by far the most sole wins
yet a marginally worse mean rank — is a direct consequence of B and C
tying each other on 117/120 problems and therefore splitting fractional
credit whenever either beats A. Both readings are descriptive; neither
carries inferential weight.

Mean wall time per run: A 16.2 s, B 15.9 s, C 24.3 s.

## 8. Treatment-activation diagnostics (descriptive characterization)

Evidence that each treatment was genuinely active, and why C ≈ B:

- **Arm B treatment active**: the final stacking weight differs from arm A
  on **70 of 120** problems, confirming the per-step refresh changed the
  fitted model — the B-vs-A contrast is a real contrast, not a null edit.
  (Arm B records 36 LOO weight updates per run; arm A's adapter does not
  emit that counter at all, so no baseline comparison figure is claimed.)
- **Arm C adaptive path rarely accepted**: 1616 adaptive proposals were
  generated across 113 of 120 runs, of which the safety arbiter **accepted
  41 (2.5%) and rejected 1575**; only **11 of 120 runs** had any accepted
  proposal, and 13 rescue proposals occurred. The conservative consensus
  arbiter is therefore the reason C matched B on 117/120 problems.

Read plainly: at D=2 with budget 40, the adaptive machinery is almost
always gated off by its own safety arbiter, so it has very little
opportunity to change outcomes in either direction. This is a
characterization of the treatment, not a performance claim.

## 9. Timeout telemetry

| Metric | Value |
|---|---|
| Max single refinement call, all 360 runs | **0.811 s** vs the frozen 2.0 s cutoff (**2.47x headroom**) |
| Mean per-call refinement duration | 0.151 s |
| Runs containing any call >= 1.8 s | **0** |
| Refinement failures | 0 |

No evidence of wall-clock truncation influencing execution. Documented
limitation: botorch's internal timeout event cannot be observed without
editing frozen engine files; `refinement_s_max` plus replay divergence are
the registered detectors, and neither fired.

## 10. Decision-rule outcome

Both primary contrasts are **INCONCLUSIVE**, therefore **rule R4 applies**:

> No attribution for either contrast. `adaptive_stacked_v034` is labeled
> **behaviorally changed, performance-unvalidated** in this README and in
> any future solver descriptor. The open questions file as follow-up
> hypotheses for the deferred D=5 / budget-100 / >=3-seeds-per-case tier.

R2 and R5 (harmful findings) did **not** trigger; no algorithm change is
required and no `v0.3.4-rc2` is created. R1 and R3 (positive findings) did
not trigger; no superiority claim is made for any arm. The causal question
"does the V0.3.4 adaptive gain come from fresh weights or from the adaptive
path?" is **closed as unresolved at this design point**, with the
additional concrete finding that the adaptive path is rarely active here.

## 11. Limitations

1. **Design size.** 24 function clusters, one seed per case. The primary
   test can only detect a consistent function-level majority; a 17/24
   split would still be inconclusive. Absence of evidence here is not
   evidence of absence.
2. **D=2 and budget 40 only.** GP stacking behavior and the
   dimension-scaled adaptive policy gates differ at higher dimension and
   budget; nothing here transfers to those regimes.
3. **Single seed per case.** Instance variation is the only replication;
   algorithmic run-to-run variance is unmeasured (the configuration is
   deterministic, so within-configuration variance is zero by
   construction, but across-seed variance is unknown).
4. **Function-level independence is an assumption.** BBOB's 24 functions
   fall into 5 structural families; clustering at the function level is
   standard practice and far better than case-level, but does not model
   family-level correlation.
5. **Adaptive path under-exercised.** With a 2.5% arbiter acceptance rate,
   this campaign is closer to a test of "the arbiter is conservative" than
   a powerful test of "the adaptive proposals help".
6. **Machine scope.** Determinism and timing headroom are established for
   this machine and pinned environment; cross-machine bit-identity is not
   claimed.
7. **Exploratory-evidence disclosure.** A pre-registration exploratory run
   (24 functions, instance 71 only, unseeded torch refinement backend,
   `screen_device auto`) exists at
   `validation_results/v034_ablation_d2_i71_all`. Its direction favored the
   baseline. It is **exploratory only**, was disclosed in the registered
   protocol before this campaign, and is **not** combined with this
   dataset; instance 71 was re-run here under the registered apparatus.

## 12. Artifacts

`validation_results/v034_ablation_registered_d2_i71_75/`:
`manifest.json` (identity + environment), `progress.jsonl` (per-run records
incl. convergence curves and telemetry; per-failure records), `runs.csv`,
`summary.txt`, `summary.json`, `ablation_analysis.json` (registered
clustered analysis output). Official COCO observer logs per arm are written
to `exdata/.../coco_logs/{stacked,stacked_fresh_weights,adaptive_stacked}`
in the campaign worktree for cocopp post-processing.

## 13. Guardrail statements

| Check | Value |
|---|---|
| Frozen baseline `stacked_v0301` modified | **NO** (tag-diff enforced) |
| Benchmark-specific logic added | **NO** (token ban enforced by selftest) |
| Hidden objective evaluations | **NO** (external counting wrapper, all arms) |
| Strict evaluation budget preserved | **YES** (40/40 on all 360 runs) |
| Adaptive forced refits | **0** |
| Universal superiority claim | **NO** |
| Registered analysis run on registered data | **YES**, once, as pre-registered |
| Extra analyses beyond the registered one | §8 activation diagnostics — labeled descriptive characterization |
