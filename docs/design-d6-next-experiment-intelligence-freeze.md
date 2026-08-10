# D6 - Next Experiment Intelligence V0.1 freeze

Status: **PASS / FROZEN**

Milestone ID: `D6`

## Frozen identities

- Previous frozen D5 checkpoint: `fa441e32254159feea3a9564a3866614d3606707`
- Frozen D6 preregistration checkpoint: `23f3d4b916f3b45b813f4fb8b4ebe156005ac8ba`
- Final tested D6 implementation checkpoint: `db55384d06e88c425ad7989e76bdd1778fcda3f2`
- Preregistration: `docs/design-d6-next-experiment-intelligence-prereg.md`
- Evidence artifact: `experiments/design_d6/artifacts/d6_results.json`

The D6 preregistration remained **FROZEN BEFORE IMPLEMENTATION** and was not
rewritten after observing the selected experiment result, gate outcomes,
experiment artifacts or adversarial review findings.

## Scope actually delivered

D6 demonstrates one deterministic next-experiment decision from frozen
D3-D5 evidence:

```text
Existing Evidence
-> Candidate Experiment Options
-> Attributable Decision Signals
-> Information-per-Compute Selection
-> Selected Experiment
-> NEW Scientific Execution
-> NEW Evidence
```

D6 does not implement repeated autonomous discovery, autonomous hypothesis
generation, Bayesian optimization, BoTorch, active learning, general
uncertainty reduction, general information theory, autonomous scientific
question generation, multi-fidelity scheduling, distributed experiment
scheduling, LLM scientific authority or D7.

## Key scientific conclusion

D6 demonstrated that a deterministic information-oriented policy can select a
different experiment from the highest predicted-performance option.

The selected experiment was not selected because it had the best predicted
performance. It was selected by the preregistered
`information_proxy_units / compute_cost_units` policy without introducing an
arbitrary weighted quality score.

## Frozen boundaries

D6 freezes these scientific boundaries:

- Next Experiment Intelligence is not optimization.
- Next Experiment Intelligence is not predicted-success ranking.
- `DecisionSignal` is not `ScientificResult`.
- Prediction is not scientific truth.
- Uncertainty is not error.
- Model disagreement is not proof a model is wrong.
- Novelty is not scientific value by itself.
- Target failure is not scientific invalidity.
- The D6 decision is decision provenance.
- Only execution creates new scientific evidence.

## Experiment option signals

The canonical A-F signal table is preserved in
`experiments/design_d6/artifacts/d6_results.json`.

| Option | uncertainty | disagreement | novelty | contradiction | partial_success | useful_failure | information | cost | information/cost |
|---|---:|---:|---:|---|---|---|---:|---:|---|
| `A` | 0.08 | 0.04 | 0.20 | false | true | false | 1 | 1 | `1/1` |
| `B` | 0.31 | 0.20 | 0.40 | false | false | true | 3 | 2 | `3/2` |
| `C` | 0.18 | 0.10 | 0.60 | false | false | false | 1 | 5 | `1/5` |
| `D` | 0.03 | 0.00 | 0.00 | false | false | false | 0 | 1 | `0/1` |
| `E` | 0.29 | 0.34 | 0.40 | true | false | true | 4 | 4 | `4/4` |
| `F` | 0.16 | 0.06 | 0.40 | false | true | false | 1 | 2 | `1/2` |

## Selection

Frozen ordering:

1. `B`
2. `E`
3. `A`
4. `F`
5. `C`
6. `D`

Selected option:

- label: `B`
- option identity:
  `d6-option:sha256:0e42973a4337334c1ca49ebf3a113ea06bee53e5e291eee13d4f7e06b24c0031`
- decision identity:
  `d6-decision:sha256:fbf1a95b4a715675c30444b957ede59a5fd8aec0feb26f644af60f693e4f2416`

## Selected execution

Assignment:

- `component_a = A_peak`
- `component_b = B_filter`
- `adapter = buffered`
- `control_level = 1`
- `guard_enabled = false`

Execution context:

- study: `d6-study-option-b-uncertainty-disagreement-boundary-v0.1`
- model: `d4.synthetic.analytic@0.1`
- solver: `d4.closed-form.synthetic@0.1`

## New ScientificResult

Observed selected-execution result:

| Metric | Observed |
|---|---:|
| `yield_score` | 35.0 |
| `loss_score` | 33.0 |
| `stability_score` | -12.0 |

Target: `FAIL`

Target failure is not a D6 failure. The experiment was selected for scientific
information value, not predicted target success.

## Pre/post evidence

For the selected option only:

| Measure | Before selected execution | After selected execution |
|---|---:|---:|
| uncertainty | 0.31 | 0.00 |
| model disagreement | 0.20 | 0.00 |

This is frozen only as the local D6 synthetic closure result. It is not evidence
for a general uncertainty-update algorithm.

## Architecture actually pulled

D6 justified local experiment-level representations for:

- `ExperimentOption`;
- `DecisionSignal`;
- `NextExperimentDecision`;
- `ExperimentDecisionProvenance`;
- `ComputeCostEstimate`;
- no-future-result guard.

These are not frozen as generic Core abstractions.

## System and policy ownership

The concrete experiment supports keeping these experiment/system owned:

- signal predicates;
- decision ordering and tie-breaks;
- novelty semantics;
- information proxy;
- model comparison semantics;
- compute-cost model;
- scientific question generation;
- selected-experiment execution semantics;
- local uncertainty/disagreement closure proxy.

## Targeted test gate

D6 targeted suite against implementation source
`db55384d06e88c425ad7989e76bdd1778fcda3f2`:

- `tests/test_design_d6_next_experiment.py`;
- `7 passed`;
- `0 failed`;
- `0 errors`.

## Full regression gate

Full repository regression executed against implementation source
`db55384d06e88c425ad7989e76bdd1778fcda3f2`:

- `1445 passed`;
- `0 failed`;
- `0 errors`;
- `4 warnings`.

The four warnings are the existing known sklearn warnings and are not D6
failures.

## Acceptance criteria

All A1-A23 gates passed.

All N1-N18 adversarial cases passed.

## Adversarial review

### P0/P1

No scientific correctness or evidence-corruption blocker exists.

### P2

No important D6 capability correctness issue remains as a freeze blocker.

### P3

Successor evidence recorded but not fixed in D6:

- repeat D6 evidence outside the D4/D5 synthetic system;
- persist and replay multiple sequential decisions;
- test stronger decision identity and replay pressure;
- validate reuse of the no-future-result guard;
- D6-local identity currently depends on the experiment-owned frozen signal
  table;
- local uncertainty/disagreement closure is not a general uncertainty-update
  method;
- scheduler and repeated-loop semantics are deferred;
- generic Core promotion requires more evidence.

These are successor evidence, not D6 blockers.

## Frozen milestone protection

D6 was completed without modifying frozen D0/D1/D2/D3/D4/D5, ScientificTwin,
MVR0 or MVR1 semantics.

D6-local abstractions were not promoted into Core. D6 did not implement D7,
Bayesian optimization, BoTorch, autonomous repeated loops, an integrated
discovery loop, general active learning, surrogate-model optimization or
unrelated Git housekeeping.

## Frozen boundary

D6 is **complete**.

D6 must not receive further polishing, hardening or successor-milestone
implementation as part of this freeze. Future work belongs to successor
preregistered milestones.

## Frozen outcome

D6 is **PASS / FROZEN**.

The milestone proves the controlled transition from frozen existing evidence
through candidate experiment options, attributable decision signals and
information-per-compute selection into one selected experiment with new
scientific execution evidence, while preserving the boundary that decisions,
predictions, uncertainty, disagreement, novelty and target status do not create
scientific truth.
