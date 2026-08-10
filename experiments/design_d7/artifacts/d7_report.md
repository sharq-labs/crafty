# D7 Integrated Scientific Discovery Loop Evidence

## Closed Return Arrow

- selected option: `B`
- selected ScientificResult: `d7-selected-result:sha256:05772db87dac7b2f7a18ebc79645ebf85aea7e48a2ef3160354d216c109331b7` = `{'loss_score': 33.0, 'stability_score': -12.0, 'yield_score': 35.0}`; target `FAIL`
- D1 evaluation: `d7-returned-evaluation:sha256:18065f064abd489c07e2618bd8d2d912de39256fd49fb2e02379bfccfcb03cd4` / `eligible`
- returned D3 entry: `714b5c0e69c38b4b8bdecd93204909076837c8ee20a598852114794336e276f4`
- next-cycle D4 source: `d7-d4-source:sha256:5fcf3c38282145593ebdc8de639b757217419d44fb08f3377671560711385bc9`
- Generation 2 executed: `false`

## Generation 0 and Replicate

- `d7-g0-evaluation:d4-parent-a:primary`: candidate `d4-parent-a`, run `d7-g0-run:d4-parent-a:primary`, result `d7-g0-result:d4-parent-a:primary`, values `{'loss_score': 30.0, 'stability_score': 9.0, 'yield_score': 64.0}`, target `FAIL`
- `d7-g0-evaluation:d4-parent-b:primary`: candidate `d4-parent-b`, run `d7-g0-run:d4-parent-b:primary`, result `d7-g0-result:d4-parent-b:primary`, values `{'loss_score': 20.0, 'stability_score': -7.0, 'yield_score': 58.0}`, target `FAIL`
- `d7-g0-evaluation:d4-parent-c:primary`: candidate `d4-parent-c`, run `d7-g0-run:d4-parent-c:primary`, result `d7-g0-result:d4-parent-c:primary`, values `{'loss_score': 18.0, 'stability_score': 44.0, 'yield_score': 39.0}`, target `FAIL`
- `d7-g0-evaluation:d4-parent-c:replicate`: candidate `d4-parent-c`, run `d7-g0-run:d4-parent-c:replicate`, result `d7-g0-result:d4-parent-c:replicate`, values `{'loss_score': 18.0, 'stability_score': 44.0, 'yield_score': 39.0}`, target `FAIL`
- `d7-g0-evaluation:d4-parent-d:primary`: candidate `d4-parent-d`, run `d7-g0-run:d4-parent-d:primary`, result `d7-g0-result:d4-parent-d:primary`, values `{'loss_score': 6.0, 'stability_score': 51.0, 'yield_score': 29.0}`, target `FAIL`

## D3 / D4 / D5

- exact D3 selected evaluations: `['d7-g0-evaluation:d4-parent-c:primary', 'd7-g0-evaluation:d4-parent-d:primary']`
- replicate substituted: `False`
- D4 event: `d7-d4-event:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa`
- D4 derivation: `d7-d4-derivation:sha256:7a14b21ad0f617f6f29fa5fca35fcddf04231293a9e57b473edf27ed4d7ccc0a`
- D4 child: `d7-d4-child:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa` / `d7-d4-derived-twin:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa@1`
- D4 child equals D5 member: `{'candidate': True, 'twin': True, 'membership_role': 'AUTHORITATIVE_D4_MATERIALIZATION'}`
- successor result: `{'evaluation_id': 'd7-successor-evaluation:sha256:8bf0697d6c109f54092ade8b9bfd36dd80e1b7df351126bbfcb67238cb92e9b4', 'result_id': 'd7-successor-result:sha256:434a5f4404fedc323f246890071c34fffa55bf83bca7656cb5da81060a15b8f6', 'run_id': 'd7-successor-run:sha256:9a48263a6e9a14b06f54dece645b3b7b16ff61d85cf9922d45509a31c11ad91f', 'values': {'loss_score': 5.0, 'stability_score': 76.0, 'yield_score': 46.0}, 'target': 'FAIL'}`

## Typed D5 to D6 Evidence

- `d7-decision-evidence:sha256:1e198e779e494284f0140041ea34dc375af9987d83873defcd0dece8ce55b6e7` / `1e198e779e494284f0140041ea34dc375af9987d83873defcd0dece8ce55b6e7`: candidate `d7-d4-child:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa`, evaluation `d7-successor-evaluation:sha256:8bf0697d6c109f54092ade8b9bfd36dd80e1b7df351126bbfcb67238cb92e9b4`, result `d7-successor-result:sha256:434a5f4404fedc323f246890071c34fffa55bf83bca7656cb5da81060a15b8f6`, run `d7-successor-run:sha256:9a48263a6e9a14b06f54dece645b3b7b16ff61d85cf9922d45509a31c11ad91f`
- `d7-decision-evidence:sha256:3c556b586ce23d5d58d973aefd2da8a4afa63e6a6ff21fbbb7321abce3b693ed` / `3c556b586ce23d5d58d973aefd2da8a4afa63e6a6ff21fbbb7321abce3b693ed`: candidate `d4-parent-a`, evaluation `d7-g0-evaluation:d4-parent-a:primary`, result `d7-g0-result:d4-parent-a:primary`, run `d7-g0-run:d4-parent-a:primary`
- `d7-decision-evidence:sha256:54ebe5075d4a1683e0db96975885855c23d9157251ab7e0d37efd44a427838f4` / `54ebe5075d4a1683e0db96975885855c23d9157251ab7e0d37efd44a427838f4`: candidate `d4-parent-c`, evaluation `d7-g0-evaluation:d4-parent-c:primary`, result `d7-g0-result:d4-parent-c:primary`, run `d7-g0-run:d4-parent-c:primary`
- `d7-decision-evidence:sha256:885342a2ce6af2ad1449a44879a24ace64a00eaa29d717e66741540989d56e44` / `885342a2ce6af2ad1449a44879a24ace64a00eaa29d717e66741540989d56e44`: candidate `d4-parent-c`, evaluation `d7-g0-evaluation:d4-parent-c:replicate`, result `d7-g0-result:d4-parent-c:replicate`, run `d7-g0-run:d4-parent-c:replicate`
- `d7-decision-evidence:sha256:c650f3095b454d3e125b004cbb2b1693fe35c26a72da11ad0866312be74f9d55` / `c650f3095b454d3e125b004cbb2b1693fe35c26a72da11ad0866312be74f9d55`: candidate `d4-parent-b`, evaluation `d7-g0-evaluation:d4-parent-b:primary`, result `d7-g0-result:d4-parent-b:primary`, run `d7-g0-run:d4-parent-b:primary`
- `d7-decision-evidence:sha256:e6b45c982536a820981219fd9a7f7f989c1d3604a3f5111c94f13bc72fed09da` / `e6b45c982536a820981219fd9a7f7f989c1d3604a3f5111c94f13bc72fed09da`: candidate `d4-parent-d`, evaluation `d7-g0-evaluation:d4-parent-d:primary`, result `d7-g0-result:d4-parent-d:primary`, run `d7-g0-run:d4-parent-d:primary`

## Option Signals and Selection

- A: information `1`, cost `1`, ratio `1/1`, novelty `0.2`, disagreement `0.04`
- B: information `2`, cost `2`, ratio `2/2`, novelty `0.4`, disagreement `0.2`
- C: information `1`, cost `5`, ratio `1/5`, novelty `0.6`, disagreement `0.1`

- rank 1: B / `d7-option:sha256:2d6446678f3db03d6955ab50bcaffd81681129b4c77594784dc90920912cc2a9` / ratio `2/2` / information `2`
- rank 2: A / `d7-option:sha256:43c0172f0ce3383db4d4a39fe1bf970dade3ddecadad5f77c675b580a4d8405b` / ratio `1/1` / information `1`
- rank 3: C / `d7-option:sha256:fc9e0ef52eacea9b6ce87df3519f3a3fe47f86793e4b45edcc76ff7deb509fd0` / ratio `1/5` / information `1`

## Checkpoint / Selected Execution / Return

- checkpoint: `{'identity': 'f6689958a51160cb4276ed7e3a6ffe0da5e54795a084ede9fe1289f86e9579ce', 'schema': 'd7_integrated_loop_checkpoint/1', 'real_reload_from_serialized_bytes': True, 'replay_byte_identical_trace': True}`
- selected identities: `{'study': 'd7-study:sha256:8f4bc3f739d7e8302a8e98c77a5766ef2ff87608877768cedb41ce2295b83206', 'candidate': 'd7-selected-candidate:sha256:f7182f903d14c2875e3ad3ba6d01469d2e7b2a5cc1d8eef14b4bac7e50b4b1a6', 'twin': 'd7-selected-twin:sha256:f7182f903d14c2875e3ad3ba6d01469d2e7b2a5cc1d8eef14b4bac7e50b4b1a6@1', 'execution_request': 'd7-execution-request:sha256:61fc74aa0a55d0d3041b17faa08e5f2453f26e34534b86c9621fb5c915512de1', 'run': 'd7-selected-run:sha256:61fc74aa0a55d0d3041b17faa08e5f2453f26e34534b86c9621fb5c915512de1'}`
- ResultBinding: `d7-result-binding:sha256:6893beb6b45ce16b53851b13cf175bcd437aa287941d7bd62bb84d3894131ad3` / `6893beb6b45ce16b53851b13cf175bcd437aa287941d7bd62bb84d3894131ad3`
- final trace identity: `180a6762b6c1c0c289491c90ab7247e495041fc3aefaa603920fcb06436c651a`

## A1-A23

- A1: PASS - D7 added only bounded experiment implementation/tests/artifacts; frozen semantics were not edited
- A2: PASS - every comparable object and execution carries the exact typed physics scope
- A3: PASS - separately typed assessment changes preserve physics evidence
- A4: PASS - mixed D4 source physics fails before authoritative materialization
- A5: PASS - D3 selection uses exact candidate/evaluation plus entry identity/digest
- A6: PASS - D4 event/derivation identities cover sources, assignment, compatibility, scope and materialization
- A7: PASS - successor member is byte-identical to authoritative D4 Candidate/Twin
- A8: PASS - every unevaluated D4/selected Twin starts with empty evidence fields
- A9: PASS - one D7-local full-vocabulary no-inheritance validator covers D4/D5/selected execution
- A10: PASS - D6-style inputs are complete typed evidence bindings
- A11: PASS - novelty is rederived from the complete typed evaluated universe
- A12: PASS - full predictions/evidence/scope/Study/cost/signals affect option identity
- A13: PASS - reload validates stored full options and reruns selection without fixture rebuilding
- A14: PASS - decision/Study/Candidate/Twin/run/result graph is exact before execution
- A15: PASS - ResultBinding d7-result-binding:sha256:6893beb6b45ce16b53851b13cf175bcd437aa287941d7bd62bb84d3894131ad3 / 6893beb6b45ce16b53851b13cf175bcd437aa287941d7bd62bb84d3894131ad3
- A16: PASS - eligible D1 evaluation d7-returned-evaluation:sha256:18065f064abd489c07e2618bd8d2d912de39256fd49fb2e02379bfccfcb03cd4; target FAIL did not affect eligibility
- A17: PASS - returned D3 entry 714b5c0e69c38b4b8bdecd93204909076837c8ee20a598852114794336e276f4 built only by DesignMemoryEntry.from_evaluation
- A18: PASS - next-cycle D4 source d7-d4-source:sha256:5fcf3c38282145593ebdc8de639b757217419d44fb08f3377671560711385bc9
- A19: PASS - real checkpoint save/discard/reload/continue and trace replay succeeded
- A20: PASS - exact source/options and byte reload are order/replay invariant
- A21: PASS - N1-N24 matched frozen outcomes
- A22: PASS - compatibility, target, retention, generation, prediction and selection never inflate scientific status
- A23: PASS - PASS - 15 passed in 4.14s; PASS - 1460 passed, 4 warnings in 581.62s

## N1-N24

- N1: PASS - mixed physics scope rejected before materialization: InvalidScientificProblem
- N2: PASS - assessment-only change preserved physics identity, Layer A and results
- N3: PASS - changed model required new physics and old-scope source failed: InvalidScientificProblem
- N4: PASS - correct candidate with replicate substituted for primary rejected: InvalidScientificProblem
- N5: PASS - wrong Twin for correct result rejected: InvalidScientificProblem
- N6: PASS - assignment substitution with reused D4 identities rejected: InvalidScientificProblem
- N7: PASS - replacement D5 Candidate/Twin rejected: InvalidScientificProblem
- N8: PASS - parent evidence on derived Twin rejected: InvalidScientificProblem
- N9: PASS - parent ScientificResult inheritance rejected: InvalidScientificProblem
- N10: PASS - combined forbidden status vocabulary rejected: InvalidScientificProblem
- N11: PASS - correct result id with wrong binding rejected: InvalidScientificProblem
- N12: PASS - changed prediction with reused option identity rejected: InvalidScientificProblem
- N13: PASS - mutated serialized option rejected after valid outer digest: InvalidScientificProblem
- N14: PASS - wrong selected assignment rejected before solver: InvalidScientificProblem
- N15: PASS - wrong selected Twin rejected before solver: InvalidScientificProblem
- N16: PASS - invalid ResultBinding rejected by D1: InvalidScientificProblem
- N17: PASS - inconsistent execution graph rejected: InvalidScientificProblem
- N18: PASS - D3 admission without eligible D1 evaluation rejected: InvalidScientificProblem
- N19: PASS - duplicate identity rejected: InvalidScientificProblem
- N20: PASS - both offer orders selected the exact primary evaluation
- N21: PASS - mutated checkpoint bytes rejected: InvalidScientificProblem
- N22: PASS - incomplete checkpoint rejected: InvalidScientificProblem
- N23: PASS - decision provenance in Twin evidence rejected: InvalidScientificProblem
- N24: PASS - returned D3 entry unusable as exact next-cycle source made D7 fail: InvalidScientificProblem

## One Adversarial Scientific Review

- P0/P1: none
- P2: none
- P3: A generic physics-scope contract may become useful only after another domain forces the same fields.
- P3: The D7-local derivation, evidence graph, decision and checkpoint records are evidence for future reuse, not Core promotion.
- P3: The checkpoint proves deterministic semantic replay, not malicious-writer authenticity or production durability.
- Resolved during review: Removed an accidental Generation 2 label from the selected Study materialization; D7 now creates no Generation 2 object or execution.
- Resolved during review: Strengthened result scope-payload checks and checkpoint graph validation for exact D4 lineage, successor execution, and typed evidence bindings.

## Architecture Actually Pulled

- LoopPhysicsScope: D7-local exact physical comparability and execution boundary.
- LoopAssessmentContext: D7-local target/report/decision context kept physics-neutral.
- AuthoritativeD4: D7-local full event and derivation wrapper over frozen D4 compatibility.
- SuccessorGeneration: D7-local variable-cardinality generation with literal D4 child admission.
- LoopDecisionEvidenceBinding: D7-local full evidence graph replacing result-id membership.
- LoopExperimentOption/NextExperimentDecision: D7-local typed option identity and deterministic policy replay.
- D7Checkpoint: D7-local canonical decision-boundary save/reload envelope.
- no-inheritance validator: One D7-local recursive conformance validator across new Twins.

## Informative I1-I7

- I1: Attributable Layer A source selection worked independently of retained-only membership; retention reasons remained provenance.
- I2: The integrated path needed a D7-local authoritative derivation identity, but one synthetic case is insufficient for Core promotion.
- I3: One combined no-inheritance validator closed D4/D5/selected seams; broader reuse remains unproven.
- I4: Typed physics scope was necessary locally; a generic Core scope contract remains unresolved.
- I5: Explicit lineage made literal child/evidence checks possible; generic provenance infrastructure is not yet justified.
- I6: Typed options and decisions were required for deterministic reload; general next-experiment abstractions remain future evidence.
- I7: D7 did not require reuse or modification of D2 proposal/materialization contracts.

## Frozen Semantics

Unchanged: `['D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'ScientificTwin', 'MVR0', 'MVR1', 'previously frozen K-series semantics']`.
