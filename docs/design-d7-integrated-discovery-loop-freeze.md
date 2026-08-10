# D7 - Integrated Scientific Discovery Loop / Cross-Milestone Object-Trace Conformance V0.1 freeze

Status: **PASS / FROZEN**

Milestone ID: `D7`

## Frozen identities

- Previous frozen D6 checkpoint:
  `7171bf7d08cc43e3f3e5950238b72b84bddead92`
- Frozen D7 preregistration checkpoint:
  `86f8b4879a7e3da4839d53b209f51f09e55a742b`
- Final tested D7 implementation checkpoint:
  `bb2dc415fa2c71f53326a2a70f334325cb46180a`
- Preregistration:
  `docs/design-d7-integrated-discovery-loop-prereg.md`
- Checkpoint artifact:
  `experiments/design_d7/artifacts/d7_checkpoint-v0.1.json`
- Evidence artifact:
  `experiments/design_d7/artifacts/d7_results.json`
- Scientific report:
  `experiments/design_d7/artifacts/d7_report.md`

The D7 preregistration remained **FROZEN BEFORE IMPLEMENTATION** and was not
rewritten after observing the closed-loop execution, selected result, return
admission, checkpoint replay, gate outcomes, artifacts or adversarial review.

## Exact frozen D7 conclusion

D7 is **PASS / FROZEN**.

D7 demonstrates one deterministic, attributable and replayable closed
scientific-discovery cycle:

```text
Scientific evidence
-> D3 memory
-> D4 compatibility/recombination
-> D5 successor generation
-> new scientific evaluation
-> information-oriented next-experiment decision
-> selected scientific execution
-> new ScientificResult
-> proper D1 ResultBinding
-> ELIGIBLE D1 DesignEvaluation
-> D3 memory
-> attributable next-cycle D4 source
```

This is the first milestone that proves the return arrow. It upgrades the
demonstrated architecture from separate discovery milestones to one closed
**Scientific Discovery Loop V0.1**.

The exact blocking return arrow is frozen as **PASS**:

```text
D6-style selected execution
-> ScientificResult
-> proper D1 ResultBinding
-> ELIGIBLE DesignEvaluation
-> D3 DesignMemoryEntry
-> DesignMemoryLayerA
-> valid D4 source for the next cycle
```

Target `FAIL` is not milestone failure, D1 ineligibility or scientific
invalidity.

## Maturity classification after D7

The exact demonstrated maturity after D7 is:

- architecture maturity: **Closed Scientific Discovery Loop V0.1**;
- project phase: **PHASE 3 - CLOSE THE LOOP: CLOSED**;
- release maturity: **PRE-RELEASE 1**;
- next phase: **RELEASE 1 PREPARATION**.

D7 completion does not itself constitute Release 1.

## Generation 0 and replicate evidence

| Evaluation | yield_score | loss_score | stability_score |
|---|---:|---:|---:|
| `d4-parent-a` primary | 64.0 | 30.0 | 9.0 |
| `d4-parent-b` primary | 58.0 | 20.0 | -7.0 |
| `d4-parent-c` primary | 39.0 | 18.0 | 44.0 |
| `d4-parent-c` replicate | 39.0 | 18.0 | 44.0 |
| `d4-parent-d` primary | 29.0 | 6.0 | 51.0 |

The primary and replicate `d4-parent-c` observations have distinct run,
`ScientificResult` and `DesignEvaluation` identities despite identical
objective values.

D3 source selection used the exact `(candidate_id, evaluation_id)` key and
selected:

- primary `d4-parent-c`;
- primary `d4-parent-d`.

Replicate substitution and candidate-id-only last-wins selection were
rejected.

## D4 / D5 continuity

- compatibility: `COMPATIBLE`;
- D4 event:
  `d7-d4-event:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa`;
- D4 derivation:
  `d7-d4-derivation:sha256:7a14b21ad0f617f6f29fa5fca35fcddf04231293a9e57b473edf27ed4d7ccc0a`;
- D4 child:
  `d7-d4-child:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa`;
- D4 derived Twin:
  `d7-d4-derived-twin:sha256:244b232fba2c6accbf6acbb328335532e18d2651e5e241b4a4b8d149ab7160fa@1`;
- D5 membership role: `AUTHORITATIVE_D4_MATERIALIZATION`.

The D4 child Candidate is the exact D5 successor member. Candidate canonical
payload equality is byte-identical. Twin canonical payload equality is
byte-identical. No `d5-g1-candidate:...` replacement identity was minted.

The successor evaluation produced:

| Metric | Observed |
|---|---:|
| `yield_score` | 46.0 |
| `loss_score` | 5.0 |
| `stability_score` | 76.0 |

Target: `FAIL`.

The target failure did not affect scientific eligibility.

## Typed D5 to D6 evidence

D7 replaced result-id-only decision evidence with typed
`LoopDecisionEvidenceBinding` records covering:

- Candidate;
- ScientificTwin;
- DesignEvaluation;
- ScientificResult;
- ResultBinding;
- run;
- physics scope;
- source and successor generation;
- generation member and lineage;
- D4 event/derivation where applicable;
- exact objective projection and typed values.

Novelty was derived from the complete typed evaluated-candidate universe.
Model disagreement and contradiction were rederived from stored predictions.
Uncertainty remained explicitly `DECLARED` and was never represented as
calculated UQ.

## Next-experiment decision

| Option | Information | Cost | Information/cost |
|---|---:|---:|---|
| `A` | 1 | 1 | `1/1` |
| `B` | 2 | 2 | `2/2` |
| `C` | 1 | 5 | `1/5` |

Frozen ordering:

1. `B`
2. `A`
3. `C`

Winner: `B`.

Decision identity:
`d7-decision:sha256:6d1dcb675cf44bb57419c4038a32effac87bd7d793c734bd870ee8e88616ee4a`.

## Save / reload / continue

- checkpoint identity:
  `f6689958a51160cb4276ed7e3a6ffe0da5e54795a084ede9fe1289f86e9579ce`;
- checkpoint schema: `d7_integrated_loop_checkpoint/1`;
- real save/discard/deserialize/from_dict/rederive/compare/continue: `PASS`;
- byte-identical replay trace: `PASS`;
- final trace identity:
  `180a6762b6c1c0c289491c90ab7247e495041fc3aefaa603920fcb06436c651a`.

The serialized checkpoint was authoritative. Reload did not reconstruct a
hidden global option table or depend on Python object identity, timestamps,
mutable caches or external storage.

## Selected execution

- Study:
  `d7-study:sha256:8f4bc3f739d7e8302a8e98c77a5766ef2ff87608877768cedb41ce2295b83206`;
- Candidate:
  `d7-selected-candidate:sha256:f7182f903d14c2875e3ad3ba6d01469d2e7b2a5cc1d8eef14b4bac7e50b4b1a6`;
- Twin:
  `d7-selected-twin:sha256:f7182f903d14c2875e3ad3ba6d01469d2e7b2a5cc1d8eef14b4bac7e50b4b1a6@1`;
- run:
  `d7-selected-run:sha256:61fc74aa0a55d0d3041b17faa08e5f2453f26e34534b86c9621fb5c915512de1`;
- result:
  `d7-selected-result:sha256:05772db87dac7b2f7a18ebc79645ebf85aea7e48a2ef3160354d216c109331b7`.

Observed selected result:

| Metric | Observed |
|---|---:|
| `yield_score` | 35.0 |
| `loss_score` | 33.0 |
| `stability_score` | -12.0 |

Target: `FAIL`.

The selected Twin began with empty `evidence_refs` and empty
`calibration_evidence_refs`. Decision evidence remained decision/Study
provenance and did not become evidence belonging to the new Twin.

## Frozen return arrow

- ResultBinding:
  `d7-result-binding:sha256:6893beb6b45ce16b53851b13cf175bcd437aa287941d7bd62bb84d3894131ad3`;
- returned D1 evaluation:
  `d7-returned-evaluation:sha256:18065f064abd489c07e2618bd8d2d912de39256fd49fb2e02379bfccfcb03cd4`;
- D1 eligibility: `ELIGIBLE`;
- returned D3 entry:
  `714b5c0e69c38b4b8bdecd93204909076837c8ee20a598852114794336e276f4`;
- returned D3 entry digest:
  `4bca7985bb87cf6a23c3f820f35d1b07949989e292c5a1110d629cacac689f94`;
- next-cycle D4 source:
  `d7-d4-source:sha256:5fcf3c38282145593ebdc8de639b757217419d44fb08f3377671560711385bc9`.

Return-arrow result: **PASS**.

Generation 2 was not materialized or executed.

## Targeted test gate

D7 targeted suite against implementation source
`bb2dc415fa2c71f53326a2a70f334325cb46180a`:

- `tests/test_design_d7_integrated_loop.py`;
- `15 passed`;
- `0 failed`;
- `0 errors`.

## Full regression gate

Full repository regression executed once against implementation source
`bb2dc415fa2c71f53326a2a70f334325cb46180a`:

- `1460 passed`;
- `0 failed`;
- `0 errors`;
- `4 warnings`.

The four warnings are the existing known sklearn convergence warnings and are
not D7 failures.

## Blocking gates

All A1-A23 gates passed.

| Gate | Frozen result |
|---|---|
| A1 | PASS - frozen semantic protection |
| A2 | PASS - typed physics scope |
| A3 | PASS - assessment separation |
| A4 | PASS - single-scope D4 enforcement |
| A5 | PASS - exact D3 evaluation attribution |
| A6 | PASS - authoritative D4 derivation |
| A7 | PASS - exact D4 to D5 child identity |
| A8 | PASS - empty new-child evidence |
| A9 | PASS - unified no-inheritance conformance |
| A10 | PASS - typed D5 to D6 evidence |
| A11 | PASS - evidence-derived novelty |
| A12 | PASS - decision-relevant option identity |
| A13 | PASS - authoritative decision reload |
| A14 | PASS - exact selected execution binding |
| A15 | PASS - proper D1 ResultBinding |
| A16 | PASS - eligible D1 evaluation |
| A17 | PASS - D3 return admission |
| A18 | PASS - next-cycle D4 usability |
| A19 | PASS - save/reload/continue |
| A20 | PASS - order/process invariance |
| A21 | PASS - adversarial conformance |
| A22 | PASS - no status inflation |
| A23 | PASS - full regression safety |

## Adversarial conformance

All N1-N24 adversarial cases produced their frozen outcomes.

| Case | Frozen result |
|---|---|
| N1 | PASS - mixed physics rejected before materialization |
| N2 | PASS - assessment-only change preserved physics evidence |
| N3 | PASS - changed physics could not hide behind assessment identity |
| N4 | PASS - wrong evaluation/replicate substitution rejected |
| N5 | PASS - wrong Twin rejected |
| N6 | PASS - D4 identity reuse after content substitution rejected |
| N7 | PASS - replacement D5 child rejected |
| N8 | PASS - parent evidence on derived Twin rejected |
| N9 | PASS - parent ScientificResult inheritance rejected |
| N10 | PASS - inherited result/status vocabulary rejected |
| N11 | PASS - correct result id with wrong binding/content rejected |
| N12 | PASS - prediction mutation with reused option identity rejected |
| N13 | PASS - mutated serialized options rejected |
| N14 | PASS - wrong selected assignment rejected before solver |
| N15 | PASS - wrong selected Twin rejected before solver |
| N16 | PASS - invalid ResultBinding rejected by D1 |
| N17 | PASS - inconsistent execution graph rejected |
| N18 | PASS - D3 admission without eligible D1 evaluation rejected |
| N19 | PASS - duplicate identities rejected |
| N20 | PASS - candidate-id last-wins source selection rejected |
| N21 | PASS - mutated checkpoint rejected |
| N22 | PASS - incomplete checkpoint rejected |
| N23 | PASS - decision provenance in Twin evidence rejected |
| N24 | PASS - unusable returned entry correctly fails D7 |

N24 freezes the blocking rule that D7 fails if the returned D3 observation
cannot become an exact D4 source for the next cycle.

## Final adversarial review

### P0

None.

### P1

None.

### P2

None.

### P3

Successor evidence recorded but not promoted or treated as a D7 blocker:

- a generic physics-scope contract requires future cross-domain evidence;
- the local derivation, evidence, decision and checkpoint records are not yet
  Core-ready;
- the checkpoint proves deterministic semantic replay, not production
  durability or malicious-writer authenticity.

## Claims D7 does not prove

D7 does **not** prove or implement:

- autonomous repeated discovery;
- Generation 2 or later generations;
- convergence;
- optimization superiority;
- general scientific intelligence;
- cross-domain generality;
- real uncertainty quantification;
- multi-fidelity planning;
- production persistence;
- distributed execution;
- database durability;
- PostgreSQL;
- S3 or object storage;
- Redis;
- queues, schedulers or Kubernetes;
- Bayesian optimization or BoTorch;
- hypothesis intelligence;
- LLM orchestration;
- safety or physical-world validation;
- Release 1 completion.

Target `FAIL` is not scientific invalidity and is not evidence for any of the
excluded claims.

## Architecture successor evidence

D7 records the following as successor evidence, not generic Core promotion:

- `LoopPhysicsScope` was necessary locally;
- `LoopAssessmentContext` was necessary locally;
- authoritative derivation identity was necessary locally;
- exact D4 to D5 Candidate/Twin identity continuity was necessary;
- typed decision evidence was necessary;
- unified no-inheritance conformance was useful;
- authoritative serialized options and checkpoint state were necessary;
- explicit lineage was necessary;
- D2 proposal/materialization reuse was not required;
- generic Core promotion still requires evidence outside the D4 synthetic
  domain.

## Frozen milestone protection

D7 completed without modifying frozen D0/D1/D2/D3/D4/D5/D6,
ScientificTwin, MVR0, MVR1 or previously frozen K-series semantics.

No D7-local abstraction was promoted into Core. D7 introduced no database,
PostgreSQL, S3, Redis, external persistence, queue, scheduler, Kubernetes,
distributed service or cloud infrastructure.

## Phase and release boundary

D7 completion closes **PHASE 3 - CLOSE THE LOOP**.

It does not constitute Release 1 and does not authorize Release 1
implementation in this freeze.

The next project phase is **RELEASE 1 PREPARATION**, focused on:

```text
Lab V1
+ Mind V1
+ integration
+ stability
+ documentation
+ release packaging
```

Release 1 preparation is successor work and was not implemented by this
freeze.

## Frozen boundary

D7 is **complete**.

D7 must not receive further polishing, hardening, refactoring or successor
implementation as part of this freeze. Future work belongs to explicitly
authorized Release 1 preparation or later preregistered milestones.

## Frozen outcome

D7 is **PASS / FROZEN**.

The milestone proves one deterministic, attributable, replayable closed
Scientific Discovery Loop V0.1, including the exact selected-execution return
through D1 and D3 into a valid next-cycle D4 source, while preserving the
boundaries that target failure is not scientific invalidity, decision
provenance is not Twin evidence, declared uncertainty is not calculated UQ,
and local integration records are not generic Core abstractions.
