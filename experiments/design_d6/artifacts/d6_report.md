# D6 Next Experiment Intelligence Evidence

## Selection

- selected option: `B`
- selected option identity: `d6-option:sha256:0e42973a4337334c1ca49ebf3a113ea06bee53e5e291eee13d4f7e06b24c0031`
- decision identity: `d6-decision:sha256:fbf1a95b4a715675c30444b957ede59a5fd8aec0feb26f644af60f693e4f2416`
- best predicted-performance option: `A`
- raw information-units winner: `E`

## Signal Table

- A: alpha=(88.0, 18.0, 66.0), beta=(84.0, 20.0, 64.0), uncertainty=0.08, disagreement=0.04, novelty=0.2, info/cost=1/1
- B: alpha=(52.0, 22.0, 54.0), beta=(72.0, 32.0, 38.0), uncertainty=0.31, disagreement=0.2, novelty=0.4, info/cost=3/2
- C: alpha=(60.0, 24.0, 62.0), beta=(50.0, 29.0, 72.0), uncertainty=0.18, disagreement=0.1, novelty=0.6, info/cost=1/5
- D: alpha=(64.0, 30.0, 9.0), beta=(64.0, 30.0, 9.0), uncertainty=0.03, disagreement=0.0, novelty=0.0, info/cost=0/1
- E: alpha=(82.0, 22.0, 52.0), beta=(48.0, 38.0, 18.0), uncertainty=0.29, disagreement=0.34, novelty=0.4, info/cost=4/4
- F: alpha=(50.0, 8.0, 82.0), beta=(46.0, 5.0, 76.0), uncertainty=0.16, disagreement=0.06, novelty=0.4, info/cost=1/2

## Ordering

- 1. B: 3/2; info=3; disagreement=0.2
- 2. E: 4/4; info=4; disagreement=0.34
- 3. A: 1/1; info=1; disagreement=0.04
- 4. F: 1/2; info=1; disagreement=0.06
- 5. C: 1/5; info=1; disagreement=0.1
- 6. D: 0/1; info=0; disagreement=0.0

## Selected Execution

- assignment: `{'adapter': 'buffered', 'component_a': 'A_peak', 'component_b': 'B_filter', 'control_level': 1, 'guard_enabled': False}`
- ScientificResult: `{'loss_score': 33.0, 'stability_score': -12.0, 'yield_score': 35.0}`
- target_pass: `False`
- uncertainty/disagreement: `0.31/0.2` to `0.0/0.0`

## A1-A23

- A1: PASS - D6 added adjacent implementation/tests/evidence only; frozen D0-D5, ScientificTwin and external vertical-slice semantics unchanged
- A2: PASS - every D6 option source resolves to frozen D5 Gen0/Gen1 evidence and the declared D6 scope
- A3: PASS - all six option identities are digest-derived, stable and cost/evidence/signal sensitive
- A4: PASS - uncertainty, disagreement, novelty, predicates and information units match the frozen table exactly
- A5: PASS - adversarial missing, stale, forged, incompatible and non-finite inputs fail closed
- A6: PASS - D6 rejects mismatched decision scope, evidence universe, model output units and execution scope
- A7: PASS - decision identity payload contains no selected ScientificResult before execution
- A8: PASS - option B is selected under the frozen information-per-compute policy
- A9: PASS - insertion order, process rebuild, serialization and identity tie-breaks preserve the winner
- A10: PASS - compute cost is positive deterministic normalized units, not runtime
- A11: PASS - decision reconstructs option set, evidence refs, signals, costs, policy and selected option
- A12: PASS - executed study context, assignment, model, solver and scope match selected option B
- A13: PASS - selected execution creates a new ScientificResult with decision provenance after selection
- A14: PASS - option, decision, execution and result summaries round-trip deterministically
- A15: PASS - selection, target status, uncertainty, disagreement, novelty and memory provenance do not imply validity, adequacy, safety or truth
- A16: PASS - PASS - py -m pytest tests/test_design_d6_next_experiment.py -q (7 passed); PASS - py -m pytest --basetemp D:\engineering-ai-core-k2\.pytest_tmp_d6_full -q (1445 passed, 4 warnings)
- A17: PASS - selected B differs from best predicted-performance option A
- A18: PASS - selected B receives information units from high uncertainty, high disagreement and useful-failure relevance
- A19: PASS - novelty and useful-failure predicates change option information units and ranking
- A20: PASS - raw information-units winner E is not selected because B has higher information per compute
- A21: PASS - selected option local uncertainty/disagreement changed from 0.31/0.20 to 0.00/0.00 after execution
- A22: PASS - selected execution produced useful new evidence: target FAIL with observed 35.0/33.0/-12.0
- A23: PASS - D6 produced local abstraction evidence only; Core promotion remains a successor question

## N1-N18

- N1: PASS - missing evidence rejected: InvalidScientificProblem
- N2: PASS - scope mismatch rejected: InvalidScientificProblem
- N3: PASS - stale uncertainty source rejected: InvalidScientificProblem
- N4: PASS - non-finite uncertainty rejected: InvalidScientificProblem
- N5: PASS - incompatible model outputs rejected: InvalidScientificProblem
- N6: PASS - forged model disagreement rejected: InvalidScientificProblem
- N7: PASS - invalid novelty universe rejected: InvalidScientificProblem
- N8: PASS - duplicate option identity rejected: InvalidScientificProblem
- N9: PASS - altered cost changed option identity
- N10: PASS - altered evidence changed option identity
- N11: PASS - zero compute cost rejected: InvalidScientificProblem
- N12: PASS - future result copy rejected: InvalidScientificProblem
- N13: PASS - permuted option order preserved winner and decision identity
- N14: PASS - hidden timestamp rejected: InvalidScientificProblem
- N15: PASS - status inflation rejected: InvalidScientificProblem
- N16: PASS - incompatible scope comparison rejected: InvalidScientificProblem
- N17: PASS - selected execution mismatch rejected: InvalidScientificProblem
- N18: PASS - posthoc signal mutation rejected: InvalidScientificProblem

## Adversarial Review

- P0/P1: none
- P2: none
- P3: D6 forced local option, signal, decision, provenance, compute-cost and no-future-result records, but one synthetic decision is insufficient evidence for Core promotion.
- P3: Identity authenticity is deterministic and provenance-sensitive, but still relies on the experiment owning the frozen signal table.
- P3: The local closure proxy resolves only the selected synthetic option; it is not a general uncertainty update mechanism.

## Architecture Pulled

- ExperimentOption: strong D6-local evidence: option identity needed assignment, evidence refs, signals, model pair, cost and execution semantics.
- DecisionSignal: strong D6-local evidence: signal validation had to separate decision provenance from scientific truth.
- NextExperimentDecision: moderate D6-local evidence: deterministic selection and round-trip identity were useful, but policy remained local.
- ExperimentDecisionProvenance: strong D6-local evidence: selected execution needed to link to the decision without copying a future result into it.
- ComputeCostEstimate: moderate D6-local evidence: cost changed the selected option relative to raw information units.
- no-future-result guard: strong D6-local evidence: decisions and options had to reject pre-execution ScientificResult references.

## System-Owned Remaining

- signal predicate definitions
- signal ordering and tie-breaks
- novelty definition
- information proxy
- model comparison semantics
- cost model
- scientific question generation
- selected-experiment execution semantics
- local uncertainty/disagreement closure proxy

## Successor Evidence

- Repeat the option/signal/decision pattern in a non-D4 system before Core promotion.
- Persist multiple next-experiment decisions in a durable evidence store to test identity and replay pressure.
- Replace the local information proxy with a domain-owned estimate only after another preregistered comparison forces it.
- Test whether a generic no-future-result guard is useful outside this synthetic decision boundary.
- Defer any scheduler or repeated-loop semantics to a later milestone.
