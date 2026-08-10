# D6 - Next Experiment Intelligence V0.1 preregistration

Status: **FROZEN BEFORE IMPLEMENTATION**

Milestone ID: `D6`

## Frozen inspection basis

D6 is preregistered after D5 was frozen.

Relevant frozen checkpoints:

- D5 frozen checkpoint: `fa441e32254159feea3a9564a3866614d3606707`
- D5 final tested implementation checkpoint: `a80defa51df6c773d5bfca275ed9bedf4fee84e2`
- D5 frozen preregistration checkpoint: `ab91741880b70499abdc0d2a29d58ab487fd30c6`
- Previous frozen D4 checkpoint: `0cb5e5b72d67a6e77cc17f388d1b3e4c17581ca2`

Inspected frozen semantics:

- D1 binds an exact candidate, Twin, design space and complete
  `ScientificResult`; selection eligibility is explicit and is not inferred from
  result usability, target status or archive membership.
- D3 Layer A records attributable observations; D3 Layer B records
  policy-derived retention/classification. D3 memory is decision provenance and
  does not manufacture scientific truth.
- D4 compatibility and recombination create local compatibility/derivation
  evidence but do not assert future child performance or scientific validity.
- D5 creates one deterministic Generation 1 population and new evaluations. D5
  demonstrated memory-informed generation without optimization and without
  inherited scientific truth.
- `ScientificResult` requires unit-bearing values, provenance, solver/model
  attribution, optional uncertainty and validation. Missing uncertainty is
  explicitly `UNKNOWN`, not zero uncertainty.
- Existing UQ contracts distinguish quantified uncertainty from unknown
  uncertainty. They do not invent model discrepancy.
- Existing model adequacy/competition contracts score bounded held-out evidence
  and do not convert disagreement into model truth probabilities.
- Provenance records are caller supplied and deterministic; timestamps are not
  harvested automatically because timestamps would break deterministic identity.
- Study records identify scientific experiments and budget accounting, not
  schedulers or autonomous loops.
- Deterministic records use schema strings, sorted JSON mappings, exact typed
  values and fail-closed digest checks.

## Purpose

D6 tests whether attributable evidence from D3-D5 can be transformed into a
deterministic decision about **one next scientific experiment**.

D6 is not autonomous discovery. It does not implement a repeated loop, a
general active-learning framework, Bayesian optimization, BoTorch, surrogate
model optimization, expected improvement, LLM hypothesis generation, equation
discovery, a multifidelity scheduler, a distributed task queue or D7.

The D6 decision is decision provenance only. It is not scientific evidence about
the future result of the selected experiment.

## Central scientific goal

Test whether the system can select the next experiment for scientific
information value using explicit attributable decision signals:

- quantified uncertainty from a frozen synthetic uncertainty source;
- model disagreement from two frozen synthetic prediction models;
- exact novelty relative to D5 evaluated evidence;
- contradiction and useful-failure indicators;
- partial-success relevance;
- an explicit deterministic compute-cost estimate.

The selected option must be executable afterward and must produce a new
`ScientificResult` that may confirm or contradict the D6 decision rationale.

## Scientific questions

**Q1 - Evidence to deterministic decision inputs.** Can attributable evidence
from D3-D5 be transformed into deterministic next-experiment decision inputs
without inventing scientific truth?

**Q2 - Information-oriented comparison.** Can experiment options be compared on
information-oriented criteria rather than predicted performance alone?

**Q3 - Uncertainty and disagreement.** Can uncertainty and model disagreement
increase experiment priority without being misrepresented as physical truth?

**Q4 - Novelty and useful failure.** Can novelty and useful failure influence
experiment selection without becoming scientific validation?

**Q5 - Compute-cost semantics.** Can computational cost be represented
explicitly so the system can reason about information value per compute?

**Q6 - Identity and provenance.** Can experiment identity and decision
provenance be reconstructed exactly?

**Q7 - Execute selected experiment.** Can the selected experiment be executed
afterward and produce a new `ScientificResult` that may confirm or contradict
the selection rationale?

**Q8 - Core abstraction evidence.** Does D6 justify a generic
`NextExperimentDecision` abstraction in Core, or should decision policy remain
experiment/system owned?

Q8 is empirical. D6 must not answer it from architectural preference.

## Scientific scope

D6 uses the frozen D4/D5 synthetic design space because it is the smallest
domain-neutral fixture with:

- typed mixed design slots;
- deterministic analytic execution equations;
- Gen0 and Gen1 attributable evidence;
- D3 memory provenance;
- D4 compatibility/recombination provenance;
- D5 evidence that memory-informed generation is not optimization.

Frozen scope:

- design space id: `d4-domain-neutral-synthetic`
- design space version: `0.1`
- decision scope id: `d6-next-experiment-intelligence-scope-v0.1`
- option set id: `d6-next-experiment-option-set-v0.1`
- decision policy id: `d6-information-per-compute-lexicographic-v0.1`
- execution problem id: `d4-synthetic-objectives-v0.1`
- execution model reference: `d4.synthetic.analytic@0.1`
- execution solver identity: `d4.closed-form.synthetic@0.1`
- execution semantics id: `d6.closed-form.selected-experiment@0.1`

Objectives remain:

| Objective | Metric | Direction | Unit |
|---|---|---|---|
| `yield_score` | `yield_score` | maximize | `dimensionless` |
| `loss_score` | `loss_score` | minimize | `dimensionless` |
| `stability_score` | `stability_score` | maximize | `dimensionless` |

Target assessment remains informative only:

```text
yield_score >= 70
loss_score <= 25
stability_score >= 50
```

Target pass/fail is not validity, feasibility, model adequacy, selection truth
or expected success.

## Evidence universe

D6 may read these frozen D5 records:

- `experiments/design_d5/artifacts/d5_results.json`
- Gen0 population `d5-g0-baseline-population-v0.1`
- Gen1 population `d5-g1-derived-population-v0.1`
- D5 frozen checkpoint `fa441e32254159feea3a9564a3866614d3606707`

Gen0 evaluation/result references:

| Candidate | Evaluation | Result |
|---|---|---|
| `d4-parent-a` | `d5-g0-evaluation:d4-parent-a` | `d5-g0-result:d4-parent-a` |
| `d4-parent-b` | `d5-g0-evaluation:d4-parent-b` | `d5-g0-result:d4-parent-b` |
| `d4-parent-c` | `d5-g0-evaluation:d4-parent-c` | `d5-g0-result:d4-parent-c` |
| `d4-parent-d` | `d5-g0-evaluation:d4-parent-d` | `d5-g0-result:d4-parent-d` |

Gen1 accepted evaluation/result references:

| D5 proposal | Candidate | Evaluation | Result |
|---|---|---|---|
| `B` | `d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803` | `d5-g1-evaluation:d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803` | `d5-g1-result:d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803` |
| `C` | `d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae` | `d5-g1-evaluation:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae` | `d5-g1-result:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae` |
| `D` | `d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d` | `d5-g1-evaluation:d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d` | `d5-g1-result:d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d` |
| `E` | `d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994` | `d5-g1-evaluation:d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994` | `d5-g1-result:d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994` |

D3 memory entries used by D5 proposals:

| D3 entry identity | D3 entry digest |
|---|---|
| `0fd7c1db20ca6da0a2279a432e48a7d0536c04e92969d4e3417bb20e74d7183a` | `ef136c12584e73ed6e5fa5fd0e893da3895a1f83abd8b57e2fd174451f55159d` |
| `739304e0d2df1a765d4959971175b8d0c775991e900ce7d0f1d96b9f6eb7a2ae` | `0bf50fc3efe8b5a1899d3b61784dc8593917a2e7be18130118033210f5a4c458` |
| `d5e1f1e753ac0017c7c36f37d558383f83605b896ced9a1af44090af2014e7a6` | `281bd0f1f6e2529aa9bc2015b54c1c191ae9a673f5568106dc0d23a521941153` |
| `fc76894d4103c0fd739c16dc846b3820cc188fb6692feb85de4ca06b9b97c81e` | `85a9975a91f119979fd69e298f5955122adc647a4a71861423975d044b502180` |

D6 may read D5 target status, Pareto membership and retention classifications
only as decision provenance. These statuses must not become validity or
expected-success claims.

## Frozen signal definitions

Every option carries all signals below. Missing, stale, non-finite,
dimensionally incompatible or unattributable signal inputs make the option
`INVALID` and unavailable for selection.

### Predicted performance

Predicted performance is used only to test whether the selected next experiment
differs from the best predicted physical outcome. It is not a selection score.

Frozen primary prediction model:

- model id: `d6.synthetic.model-alpha`
- version: `0.1`
- source: frozen synthetic decision-signal table in this preregistration

Best predicted performance is determined lexicographically:

1. predicted target pass, with `true` before `false`;
2. higher predicted `yield_score`;
3. lower predicted `loss_score`;
4. higher predicted `stability_score`;
5. option identity tie-break.

### Uncertainty magnitude

Uncertainty comes from the frozen synthetic uncertainty source
`d6.synthetic.uq@0.1`.

It is a quantified standard uncertainty proxy for `yield_score` in
`dimensionless` normalized units. It is not error, model inadequacy or physical
falsity.

Behavior:

- valid range: finite `>= 0`;
- high-uncertainty predicate: `uncertainty_magnitude >= 0.25`;
- stale if the source id/version, evidence universe id or decision scope differs
  from the frozen values above;
- non-finite or negative values are `INVALID`.

### Model disagreement

Frozen model pair:

- `d6.synthetic.model-alpha@0.1`
- `d6.synthetic.model-beta@0.1`

Comparable outputs are exactly `yield_score`, `loss_score` and
`stability_score` in `dimensionless`.

Disagreement is:

```text
max(
  abs(alpha_yield - beta_yield) / 100,
  abs(alpha_loss - beta_loss) / 50,
  abs(alpha_stability - beta_stability) / 100
)
```

High-disagreement predicate:

```text
model_disagreement >= 0.20
```

Disagreement does not mean either model is wrong.

### Novelty

Novelty is exact normalized Hamming distance over the five D4/D5 typed slots:

```text
slots = component_a, component_b, adapter, control_level, guard_enabled
novelty_distance =
  min(distance(option_assignment, evaluated_assignment) for all D5 Gen0+Gen1 evaluated assignments)

distance = count(slots with unequal typed value) / 5
```

High-novelty predicate:

```text
novelty_distance >= 0.50
```

No fuzzy novelty or similarity threshold exists beyond this exact formula.

### Contradiction indicator

Contradiction is a decision-signal predicate, not scientific truth.

For D6 V0.1:

```text
contradiction_indicator = true
```

only when the frozen signal table says that `model-alpha` predicts target pass
and `model-beta` predicts target fail for the same option under comparable
scope. Target pass is evaluated with the informative D5 thresholds above.

Contradiction is distinct from target failure, model disagreement and D4
compatibility.

### Partial-success relevance

Partial-success relevance is true only when the option is explicitly sourced to
a D5 candidate that improved at least one preregistered objective relative to
all relevant lineage parents but still failed the overall target.

For D6 V0.1 this may cite D5 proposal `C` or a direct deterministic refinement
of its assignment.

Partial-success relevance is decision provenance only.

### Useful-failure relevance

Useful-failure relevance is true only when the option changes one or two
non-component control slots from a D5 target-failing candidate whose parent
relative comparison recorded underperformance. It is intended to test a
failure mode, not to assert future success.

### Information proxy units

D6 V0.1 does not claim Shannon information gain.

The information proxy is an integer coverage count of the following six
independent preregistered predicates:

1. high uncertainty;
2. high model disagreement;
3. high novelty;
4. contradiction indicator;
5. partial-success relevance;
6. useful-failure relevance.

Each predicate contributes one unit if true. This is a count of covered
scientific inquiry predicates, not an arbitrary weighted score.

### Compute cost

Compute cost is deterministic normalized compute units.

It is a preregistered estimate of expected fixed solver/evaluation effort for
the synthetic experiment, not wall-clock time.

Valid cost is a finite positive integer. `0`, negative, non-integer, non-finite
or missing cost is `INVALID`.

Information per compute is compared as an exact rational pair:

```text
information_proxy_units / compute_cost_units
```

No floating tolerance is used for selection.

## Exact experiment-option set

Proposal labels are evaluated in exact label order `A` through `F`. The option
set size is exactly `6`.

Option identity is:

```text
d6-option:sha256:<digest>
```

The digest is over canonical deterministic JSON containing exactly:

1. schema `d6_experiment_option/1`;
2. option set id;
3. decision scope id;
4. option label;
5. proposed Study/context id;
6. complete proposed assignment sorted by slot name;
7. model pair;
8. sorted source evidence references;
9. complete decision-signal table;
10. execution semantics id.

Changing cost, evidence provenance, model pair, signal values, assignment,
scope, execution semantics or option label changes the option identity.

| Label | Option identity | Study/context id | Proposed assignment | Source evidence refs |
|---|---|---|---|---|
| `A` | `d6-option:sha256:23d4790eedf423cc9f9518d23f6986785f472c61e9edf3aa1d8c688b0e33d4eb` | `d6-study-option-a-performance-confirmation-v0.1` | `A_stable`, `B_filter`, `isolated`, `2`, `true` | D5 proposal `C` result |
| `B` | `d6-option:sha256:0e42973a4337334c1ca49ebf3a113ea06bee53e5e291eee13d4f7e06b24c0031` | `d6-study-option-b-uncertainty-disagreement-boundary-v0.1` | `A_peak`, `B_filter`, `buffered`, `1`, `false` | D5 proposal `B`, Gen0 `d4-parent-a`, Gen0 `d4-parent-d` results |
| `C` | `d6-option:sha256:86d6d993b843a347abceab0a71bee200974ecdb35df262c60e3af9c7a1a54d66` | `d6-study-option-c-novel-expensive-region-v0.1` | `A_base`, `B_base`, `isolated`, `0`, `true` | D5 Gen0 and Gen1 populations |
| `D` | `d6-option:sha256:cc5ac36d0b69c69f1000d8c309d3bf43bb44c8e7819215e24da41c777bd8e3f5` | `d6-study-option-d-cheap-redundant-repeat-v0.1` | `A_peak`, `B_base`, `direct`, `1`, `true` | D5 proposal `E` result |
| `E` | `d6-option:sha256:4201db700a0ea78d55c5a46903a2a6001effb01c3877b790a33b4cbcaeef9405` | `d6-study-option-e-contradiction-useful-failure-v0.1` | `A_stable`, `B_peak`, `direct`, `2`, `false` | D5 proposal `D` result |
| `F` | `d6-option:sha256:92e2a02e2f0c533ca1556e28b3016675d5211c6f8f11217665d654ae35ae0b3b` | `d6-study-option-f-partial-success-refinement-v0.1` | `A_stable`, `B_filter`, `isolated`, `1`, `true` | D5 proposal `C` result |

Canonical source evidence references used in the option identity payloads:

| Label | Sorted source evidence refs |
|---|---|
| `A` | `d5-g1-result:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae` |
| `B` | `d5-g0-result:d4-parent-a`; `d5-g0-result:d4-parent-d`; `d5-g1-result:d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803` |
| `C` | `d5-g0-baseline-population-v0.1`; `d5-g1-derived-population-v0.1` |
| `D` | `d5-g1-result:d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994` |
| `E` | `d5-g1-result:d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d` |
| `F` | `d5-g1-result:d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae` |

## Frozen decision-signal table

| Label | alpha predicted yield | alpha predicted loss | alpha predicted stability | alpha target pass | uncertainty | disagreement | novelty | contradiction | partial success | useful failure | information units | compute cost | information / compute |
|---|---:|---:|---:|---|---:|---:|---:|---|---|---|---:|---:|---|
| `A` | 88.0 | 18.0 | 66.0 | true | 0.08 | 0.04 | 0.20 | false | true | false | 1 | 1 | `1/1` |
| `B` | 52.0 | 22.0 | 54.0 | false | 0.31 | 0.20 | 0.40 | false | false | true | 3 | 2 | `3/2` |
| `C` | 60.0 | 24.0 | 62.0 | false | 0.18 | 0.10 | 0.60 | false | false | false | 1 | 5 | `1/5` |
| `D` | 64.0 | 30.0 | 9.0 | false | 0.03 | 0.00 | 0.00 | false | false | false | 0 | 1 | `0/1` |
| `E` | 82.0 | 22.0 | 52.0 | true | 0.29 | 0.34 | 0.40 | true | false | true | 4 | 4 | `4/4` |
| `F` | 50.0 | 8.0 | 82.0 | false | 0.16 | 0.06 | 0.40 | false | true | false | 1 | 2 | `1/2` |

The frozen `model-beta` predictions used to compute disagreement and
contradiction are:

| Label | beta predicted yield | beta predicted loss | beta predicted stability | beta target pass |
|---|---:|---:|---:|---|
| `A` | 84.0 | 20.0 | 64.0 | true |
| `B` | 72.0 | 32.0 | 38.0 | false |
| `C` | 50.0 | 29.0 | 72.0 | false |
| `D` | 64.0 | 30.0 | 9.0 | false |
| `E` | 48.0 | 38.0 | 18.0 | false |
| `F` | 46.0 | 5.0 | 76.0 | false |

By predicted performance alone, option `A` is best. By raw information units,
option `E` is highest. By information per compute, option `B` is selected.

## Selection policy

Policy id:

```text
d6-information-per-compute-lexicographic-v0.1
```

Selection is deterministic and fixed before implementation:

1. Build the exact six options above.
2. Recompute every decision signal from frozen evidence and frozen signal
   tables.
3. Reject `INVALID` options fail-closed.
4. Reject duplicate option identities fail-closed.
5. Do not remove option `D` merely because it is redundant; redundancy is
   represented by `novelty = 0.00` and `information_units = 0`.
6. Select the valid option with maximum exact rational
   `information_units / compute_cost`.
7. If tied, select higher `information_units`.
8. If still tied, select higher `model_disagreement`.
9. If still tied, select lexicographically smallest option identity.

Expected selected option:

```text
label: B
identity: d6-option:sha256:0e42973a4337334c1ca49ebf3a113ea06bee53e5e291eee13d4f7e06b24c0031
```

Decision identity is:

```text
d6-decision:sha256:fbf1a95b4a715675c30444b957ede59a5fd8aec0feb26f644af60f693e4f2416
```

The decision digest is over canonical deterministic JSON containing:

1. schema `d6_next_experiment_decision/1`;
2. option set id;
3. decision scope id;
4. policy id;
5. sorted candidate option identities;
6. selected option identity;
7. selected option label;
8. ordered selection-basis strings.

The decision must serialize deterministically and round-trip byte-identically.

## Selected experiment execution

Only after the D6 decision is recorded, the selected experiment is executed.

Execution flow:

```text
Existing Evidence
-> D6 decision
-> selected experiment identity
-> NEW Study / execution context
-> ScientificTwin / system
-> NEW execution
-> NEW ScientificResult
-> compare observed result against D6 rationale
```

The selected option is `B` with assignment:

```text
component_a = A_peak
component_b = B_filter
adapter = buffered
control_level = 1
guard_enabled = false
```

The execution uses the frozen D4 equations, model reference
`d4.synthetic.analytic@0.1`, solver `d4.closed-form.synthetic@0.1`, problem id
`d4-synthetic-objectives-v0.1`, and a new Study/context id
`d6-study-option-b-uncertainty-disagreement-boundary-v0.1`.

Expected selected-execution result under frozen equations:

```text
yield_score = 35.0
loss_score = 33.0
stability_score = -12.0
target = FAIL
```

This result may contradict the selection rationale. That is valid scientific
evidence and not a D6 failure.

The selected execution must create:

- a new Study/execution context identity;
- a new ScientificTwin identity/reference if materialized as a design Twin;
- a new D1 evaluation identity if represented in D1;
- a new `ScientificResult.result_id`;
- a new provenance record linking to the D6 decision as decision provenance
  only.

The D6 decision must not copy a future `ScientificResult` into the decision
record.

## Comparison reports

D6 must report separately:

- best predicted-performance option;
- raw information-units winner;
- information-per-compute selected option;
- selected option execution result;
- whether selected execution confirmed or contradicted each signal rationale;
- whether uncertainty/disagreement was reduced after execution, if D6 implements
  the preregistered reduction proxy below.

Reduction proxy:

```text
post_execution_disagreement_for_selected_option = 0.00
post_execution_uncertainty_for_selected_option = 0.00
```

only for the selected option after its new ScientificResult is attributable.
This is a local closure marker for this one synthetic option, not a global
posterior update or Bayesian information gain.

## Negative and adversarial cases

All cases fail closed unless explicitly marked informative.

| Case | Attempt | Expected behavior |
|---|---|---|
| `N1` | missing evidence reference | `INVALID`; option unavailable; no decision if selected option depends on it |
| `N2` | mismatched Study/scope | `INVALID`; no cross-scope signal comparison |
| `N3` | stale uncertainty source id/version/evidence universe | `INVALID` |
| `N4` | non-finite or negative uncertainty | `INVALID` |
| `N5` | incompatible model outputs or units | `INVALID` |
| `N6` | forged model disagreement not matching recomputed alpha/beta predictions | `INVALID` |
| `N7` | invalid novelty input or missing evaluated assignment universe | `INVALID` |
| `N8` | duplicate experiment option identity | fail closed before selection |
| `N9` | same experiment with altered cost identity | option identity changes; old identity cannot be reused |
| `N10` | same experiment with altered evidence provenance | option identity changes; old identity cannot be reused |
| `N11` | option with zero, negative, non-integer or non-finite cost | `INVALID` |
| `N12` | option or decision copies future `ScientificResult` | fail closed |
| `N13` | decision order permutation changes winner | fail closed |
| `N14` | hidden timestamp changes identity | fail closed; timestamps are excluded or explicit identity inputs |
| `N15` | target-pass status treated as validity or scientific truth | fail closed / no status inflation |
| `N16` | incompatible scopes compared | fail closed and report separately |
| `N17` | selected experiment execution does not match decision record | fail closed |
| `N18` | post-hoc modification of decision signals after result is observed | fail closed by recomputing decision identity and signals |

## Success and failure gates

Blocking gates:

- **A1 - Frozen milestone protection:** ScientificTwin, D0, D1, D2, D3, D4,
  D5, MVR0 and MVR1 semantics are unmodified.
- **A2 - Exact evidence attribution:** every signal source resolves to frozen
  D3-D5 evidence, exact candidate/evaluation/result bindings and the declared
  decision scope.
- **A3 - Deterministic option identity:** all six option identities are
  digest-derived, stable and sensitive to scope, evidence, signals and cost.
- **A4 - Deterministic signal computation:** uncertainty, disagreement, novelty,
  contradiction, partial-success, useful-failure and information proxy values
  match this preregistration exactly.
- **A5 - Fail-closed invalid evidence:** missing, stale, forged,
  dimensionally-incompatible or non-finite evidence/signal inputs are rejected.
- **A6 - Scope compatibility:** no direct comparison occurs across incompatible
  study, design-space, objective, model-output or unit scope.
- **A7 - No future-result leakage:** decision records contain no selected
  experiment ScientificResult before execution.
- **A8 - Deterministic selection:** option `B` is selected under the frozen
  information-per-compute policy.
- **A9 - Order/process invariance:** option insertion order, process restart,
  serialization round-trip and identity tie-breaks do not change the winner.
- **A10 - Explicit compute-cost semantics:** compute cost is positive
  deterministic normalized units, never wall-clock runtime.
- **A11 - Exact decision provenance:** the decision reconstructs option set,
  source evidence refs, signal inputs, cost, policy and selected option.
- **A12 - Selected execution matches decision:** executed assignment, study
  context, model, solver and scope match the selected decision record exactly.
- **A13 - New ScientificResult required:** selected execution creates a new
  attributable ScientificResult before any post-decision scientific claim.
- **A14 - Deterministic round-trip:** options, decision, execution request and
  result summary serialize deterministically and round-trip without identity or
  type loss.
- **A15 - No status inflation:** uncertainty, disagreement, novelty,
  contradiction, target pass, Pareto status, memory retention and selection do
  not imply validity, feasibility, adequacy, safety, optimality or truth.
- **A16 - Full regression safety:** targeted D6 tests and full repository
  regression pass before D6 freeze.

Informative outcomes:

- **A17 - Selected option differs from best predicted-performance option:** D6
  should observe selected `B` while best predicted performance is `A`.
- **A18 - Uncertainty/disagreement affects selection:** option `B` is selected
  because uncertainty/disagreement contribute to information units.
- **A19 - Novelty/failure evidence affects selection:** novelty/failure signals
  change raw information units, but may not decide the winner.
- **A20 - Compute cost changes choice:** raw information-units winner `E` is not
  selected because `B` has higher information per compute.
- **A21 - Selected experiment reduces local uncertainty/disagreement after
  execution:** observed only if the local closure proxy is implemented exactly.
- **A22 - Selected experiment reveals contradiction or useful new evidence:** the
  selected result may fail target and may contradict model-alpha prediction;
  report as evidence, not failure.
- **A23 - Core abstraction evidence:** Q8 is answered from implementation,
  tests and adversarial review, not preference.

Informative outcomes must not be converted into blocking requirements if the
selected execution produces an unexpected but attributable scientific result.

## Architecture questions deliberately unresolved

Possibly Core-worthy if D6 and later experiments justify them:

- generic `ExperimentOption`;
- generic `DecisionSignal`;
- generic `NextExperimentDecision`;
- generic `ExperimentDecisionProvenance`;
- generic `ComputeCostEstimate`;
- generic no-future-result guard for decision records.

Experiment/system-owned unless repeated evidence proves otherwise:

- signal predicate definitions;
- signal ordering and tie-breaks;
- novelty definition;
- information proxy;
- model comparison semantics;
- cost model;
- scientific question generation;
- selected-experiment execution semantics;
- local uncertainty/disagreement closure proxy.

D6 must not promote abstractions to Core merely because they look reusable.

## Falsifiability check

An independent implementer working only from this preregistration should obtain
the same:

- option set `A-F`;
- decision signals;
- option identities;
- valid/rejected behavior;
- selected option `B`;
- decision identity;
- selected execution input;
- selected execution result under frozen equations;
- gate and adversarial expectations.

If implementation freedom remains to choose weights, thresholds, option
membership, signal definitions, costs, tie-breaks or selected option after
observing results, it is not implementing this D6 preregistration.

## Explicitly out of scope

D6 preregistration does not implement:

- D6 source code;
- D5 modifications;
- D0-D4 modifications;
- ScientificTwin modifications;
- D7;
- repeated autonomous loops;
- LLM hypothesis generation;
- natural-language scientific orchestration;
- Bayesian optimization;
- BoTorch;
- surrogate-model optimization;
- acquisition functions;
- general active learning;
- reinforcement learning;
- autonomous model invention;
- equation discovery;
- full multifidelity scheduling;
- distributed compute scheduling;
- production task queues.

## Freeze rule

This document is frozen before D6 implementation.

Implementation may not weaken the option set, signal definitions, cost model,
selection policy, identity semantics, selected execution semantics, adversarial
cases or gates after observing selected-experiment results. If the experiment
exposes that the preregistered structure is insufficient, the gap must be
recorded as D6 evidence or successor architecture rather than silently editing
frozen D0-D5, ScientificTwin or this preregistration.
