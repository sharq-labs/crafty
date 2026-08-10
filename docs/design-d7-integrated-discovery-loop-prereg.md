# D7 - Integrated Scientific Discovery Loop / Cross-Milestone Object-Trace Conformance V0.1 preregistration

Status: **PREREGISTERED / NOT IMPLEMENTED**

Milestone ID: `D7`

Exact milestone name and version: **D7 - Integrated Scientific Discovery Loop / Cross-Milestone Object-Trace Conformance V0.1**

## Frozen inspection basis

This preregistration was written against these frozen checkpoints:

- D3 - Scientific Design Memory / Partial Success V0.1:
  `6abdf279141cf032abdb8052f6ee806c3c264953`;
- D4 - Compatibility / Recombination V0.1:
  `0cb5e5b72d67a6e77cc17f388d1b3e4c17581ca2`;
- D5 - Generation 1 / Memory-Informed Candidate Generation V0.1:
  `fa441e32254159feea3a9564a3866614d3606707`;
- D6 - Next Experiment Intelligence V0.1:
  `7171bf7d08cc43e3f3e5950238b72b84bddead92`.

The following remain frozen and must not be modified by D7: D0-D6, MVR0,
MVR1, ScientificTwin, and all previously frozen K-series semantics.

This document is the only D7 artifact created by preregistration. It contains
no implementation, test, database, object-store, scheduler, or service change.

## Purpose and blocking scientific claim

D7 tests one exact closed scientific-discovery cycle:

```text
Scientific Evidence
-> D3 Memory
-> D4 Compatibility / Recombination
-> D5 Successor Generation
-> NEW Scientific Evaluation
-> D6-style Next Experiment Decision
-> Selected Scientific Execution
-> NEW ScientificResult
-> valid D1 DesignEvaluation
-> D3 Memory
-> attributable D4 source for the NEXT cycle
```

The blocking return arrow is:

```text
D6-style selected execution -> D1 -> D3
```

The milestone passes only if the `ScientificResult` produced by the selected
next experiment is transformed, without manually inventing scientific
metadata, into an `ELIGIBLE` D1 `DesignEvaluation`, whose attributable
observation is admitted into `DesignMemoryLayerA` and accepted as an exact D4
source for the next cycle.

If any part of that return arrow fails, **D7 FAILS**, regardless of whether the
forward D3 -> D4 -> D5 -> D6 path succeeded.

"Without manually inventing scientific metadata" means every candidate, Twin,
run, result, binding, evaluation, memory, generation, evidence, option, decision,
and Study field crossing a milestone boundary is either:

1. read from an authoritative typed object already in the object graph;
2. produced by the frozen analytic execution; or
3. deterministically derived by an identity or admission rule in this
   preregistration.

No caller-supplied dictionary may repair a missing Candidate/Twin/Study/model/
solver/run/result relationship after execution.

## Scientific questions

**Q1 - Closed traversal.** Can one attributable scientific result traverse
D3 -> D4 -> D5 -> D6 and return as new D1/D3 evidence without manual semantic
reconstruction?

**Q2 - Scope separation.** Can physics scope remain distinct from
assessment/decision context across the entire loop?

**Q3 - Cross-scope failure.** Can incompatible scopes fail closed before
recombination or comparison?

**Q4 - Authoritative child identity.** Can one authoritative derived candidate
maintain exact identity and lineage across D4 and D5?

**Q5 - Typed decision evidence.** Can D6-style decisions consume typed,
attributable D5 evidence rather than result-id membership alone?

**Q6 - Return binding.** Can a selected experiment produce a correctly bound
Candidate, Twin, `ScientificResult`, `ResultBinding`, and `DesignEvaluation`
that becomes D3 evidence?

**Q7 - Evidence/provenance separation.** Can prior evidence remain decision
provenance without being attached as scientific evidence to an unevaluated new
Twin?

**Q8 - Deterministic continuation.** Can the complete loop save, reload,
validate, and continue deterministically?

**Q9 - Next-cycle usability.** Can the newly returned memory observation be
used as a source for the next generation?

**Q10 - Future Core evidence.** Which repeated cross-milestone contracts are
actually forced strongly enough to be considered future Core candidates?

Q10 is empirical. D7 must not answer it from architectural preference.

## Non-equivalences frozen for D7

- physics scope is not assessment context;
- assessment change is not physics change;
- compatible is not scientifically valid;
- retained is not scientifically true;
- D3 source provenance is not child evidence;
- D4 materialization is not new scientific evidence;
- D5 generation membership is not scientific success;
- a decision signal is not a `ScientificResult`;
- prediction is not evidence;
- declared uncertainty is not calculated UQ;
- selected is not valid, feasible, safe, adequate, optimal, or true;
- target pass/fail is not D1 eligibility;
- a result id is not an evidence binding;
- equal assignments are not necessarily equal derivations;
- Python object identity is not scientific object identity;
- a derived Twin is not a validated Twin;
- a new result is not D3 memory until a proper eligible D1 evaluation exists.

## Cross-milestone seams under direct test

The implementation must resolve the review findings empirically as follows:

| Finding | Direct D7 test |
|---|---|
| **F1 - D6 result re-entry** | Steps 10-13 and N16-N18 require the selected result to pass exact D1 binding/eligibility and D3 admission |
| **F2 - evidence vs decision provenance** | selected Twin evidence fields begin empty; N8 and N23 reject prior-result attachment |
| **F3 - physics vs assessment** | separate typed identities plus N2/N3 test both directions |
| **F4 - cross-scope recombination** | single-scope source validator and N1 reject mixed physical scope before materialization |
| **F5 - D4/D5 child ambiguity** | exact-child choice A and N7 prohibit a replacement D5 candidate |
| **F6 - D4 derivation authority** | full event/derivation rederivation plus N6 test coherent assignment substitution |
| **F7 - typed D5/D6 evidence** | full `LoopDecisionEvidenceBinding` graph plus N11 reject result-id-only spoofing |
| **F8 - signal derivation** | novelty, disagreement, contradiction, partial-success, and useful-failure predicates are rederived; uncertainty is explicitly declared |
| **F9 - option/decision identity** | full predictions and scientific inputs affect option identity; N12/N13 test mutation and reload |
| **F10 - execution binding** | exact decision -> Study -> Candidate -> Twin -> run -> result -> evaluation chain; N14-N17 test substitutions |
| **F11 - no inheritance** | one loop-owned combined validator and N8-N10/N23 test the full path |
| **F12 - D3 source selection** | choice B, any attributable Layer A entry, is frozen and next-cycle reuse is blocking |
| **F13 - multiple evaluations** | the primary/replicate `d4-parent-c` fixture and N4/N20 prohibit candidate-id last-wins lookup |

## Concrete domain-neutral system

D7 reuses the frozen D4/D5 five-slot synthetic design space and analytic
equations. It introduces no new domain science.

Exact design space:

| Slot | Type | Values |
|---|---|---|
| `component_a` | categorical | `A_base`, `A_peak`, `A_stable` |
| `component_b` | categorical | `B_base`, `B_peak`, `B_filter` |
| `adapter` | categorical | `direct`, `buffered`, `isolated` |
| `control_level` | integer | `0`, `1`, `2` |
| `guard_enabled` | boolean | `false`, `true` |

Exact objectives:

| Objective | Metric | Direction | Canonical unit |
|---|---|---|---|
| `yield_score` | `yield_score` | maximize | `dimensionless` |
| `loss_score` | `loss_score` | minimize | `dimensionless` |
| `stability_score` | `stability_score` | maximize | `dimensionless` |

The frozen D4 tables and interaction equations are reused byte-for-byte as
scientific execution semantics. Expected Generation 0 results are:

| Candidate | Assignments | yield | loss | stability |
|---|---|---:|---:|---:|
| `d4-parent-a` | `A_peak`, `B_base`, `buffered`, `2`, `false` | 64 | 30 | 9 |
| `d4-parent-b` | `A_base`, `B_peak`, `direct`, `0`, `false` | 58 | 20 | -7 |
| `d4-parent-c` | `A_stable`, `B_base`, `direct`, `1`, `true` | 39 | 18 | 44 |
| `d4-parent-d` | `A_base`, `B_filter`, `buffered`, `2`, `true` | 29 | 6 | 51 |

No random state, time, machine identity, network state, or mutable global is an
input to this experiment.

## Exact physics-scope definition

D7 introduces one loop-local `LoopPhysicsScope` only because the cross-
milestone experiment requires stronger scope attribution than a shared context
label. It is not promoted into Core.

The primary scope payload has schema `d7_loop_physics_scope/1` and contains
exactly:

1. design-space reference: `d4-domain-neutral-synthetic@0.1`;
2. problem/system identity: `d4-synthetic-objectives-v0.1`;
3. execution model reference: `d4.synthetic.analytic@0.1`;
4. solver identity: `d4.closed-form.synthetic@0.1`;
5. operating-conditions payload:
   `{"synthetic_environment":{"type":"categorical","value":"nominal"}}`;
6. fidelity payload:
   `{"kind":"NONE","reason":"closed-form analytic execution has no fidelity ladder"}`;
7. the exact three-objective projection above, including metric, direction, and
   canonical unit;
8. execution-semantics identity:
   `d7.d4-closed-form-integrated-execution@0.1`.

`physics_scope_identity` is `sha256` over UTF-8 canonical JSON of that payload,
with keys sorted, no insignificant whitespace, finite typed numbers only, and
no timestamp. Equality is exact digest equality.

Physics scope governs:

- physical comparability;
- D1/D3 comparable evidence;
- D4 source eligibility and single-scope recombination;
- D5 evidence-universe membership;
- objective/Pareto comparison;
- the model, solver, conditions, fidelity, and execution semantics used by a
  selected run.

Any change to design space, problem/system identity, execution model, solver,
operating conditions, scientifically relevant fidelity, objective projection,
or execution semantics changes `physics_scope_identity`. D7 V0.1 permits no
cross-physics recombination. Different operating conditions, model, solver, or
design space are rejected before compatibility assessment.

The D3 `DesignMemoryScope.context_reference` is exactly the
`physics_scope_identity`; it is never an assessment label or Study label.

## Exact assessment/decision-context definition

D7 introduces a separate loop-local `LoopAssessmentContext` with schema
`d7_loop_assessment_context/1`. Its identity payload contains exactly:

1. assessment-context id: `d7-loop-target-context-v0.1`;
2. threshold predicates:
   `yield_score >= 70`, `loss_score <= 25`, and
   `stability_score >= 50`, in canonical units;
3. combination rule: logical `AND` across all three predicates;
4. classification labels: `PASS` and `FAIL`;
5. reporting-context id: `d7-integrated-loop-report-v0.1`;
6. decision-context id: `d7-which-next-experiment-v0.1`;
7. study-question id: `d7-close-return-arrow-v0.1`.

`assessment_context_identity` is the digest of canonical JSON of this payload.
Assessment/decision context governs only target classification, PASS/FAIL
rules, reporting, decision rationale, and a physics-neutral study question.

It does not govern physical comparability. Changing only thresholds, reporting,
or a physics-neutral question changes `assessment_context_identity` but does
not change `physics_scope_identity` and causes no physics recomputation.
Conversely, retaining this assessment identity cannot conceal a changed model,
solver, design space, operating condition, fidelity, or execution semantics;
those changes require a new physics scope.

Every Study/execution specification carries both identities in separate
required fields. No overloaded `context` field may stand in for both.

## Generation 0, D1 evaluation, and multiple-evaluation fixture

Generation 0 contains exactly the four candidates in the table above. Each
gets a real `ScientificTwin(kind=CANDIDATE)`, a unique run, a new
`ScientificResult`, a producer-side `ResultBinding`, and an `ELIGIBLE` D1
`DesignEvaluation` under the primary physics scope.

Identity labels are deterministic:

```text
twin_id       = d4-twin:<candidate_id>, version 1
run_id        = d7-g0-run:<candidate_id>:primary
result_id     = d7-g0-result:<candidate_id>:primary
evaluation_id = d7-g0-evaluation:<candidate_id>:primary
```

The fixed eligibility reason is:

```text
preregistered D7 Generation 0 synthetic execution completed with finite projected objectives and exact result binding
```

Target assessment is computed separately and cannot affect eligibility.

To test exact evaluation attribution, `d4-parent-c` receives a second real,
attributable repeat execution under identical physics:

```text
run_id        = d7-g0-run:d4-parent-c:replicate
result_id     = d7-g0-result:d4-parent-c:replicate
evaluation_id = d7-g0-evaluation:d4-parent-c:replicate
```

It has the same analytic objective values but a distinct run, result, and
evaluation identity. Both evaluations are eligible and both become distinct
D3 Layer A entries. The preregistered D4 source is the `primary` evaluation,
never the `replicate`. Reversing their input order must not change source
selection. A candidate-id last-wins map is therefore observably incorrect.

The singular `initial_*` fields in the object trace name the primary
`d4-parent-c` chain. The trace also records arrays for all Generation 0 chains.

## D3 memory construction and exact source-selection rule

Generation 0 produces a `DesignMemoryLayerA` containing all five exact eligible
evaluations: four primaries plus the `d4-parent-c` replicate. Its
`DesignMemoryScope` is the primary physics scope and the exact objective
projection above.

The D7 classification policy is loop-local and deterministic:

- policy id: `d7-loop-memory-policy-v0.1`;
- cap: `16` entries per scope;
- scoped elites: each of the three singleton objective projections;
- assessment context: the exact D7 assessment context above;
- threshold tolerances: zero in each canonical unit;
- explicit retention: none;
- partition key: UTF-8 bytes of
  `component_a=<value>|component_b=<value>`.

### Frozen D3 source-selection choice: Layer A, not retained-only

D7 freezes choice **B**: D4 may select **any attributable D3 Layer A entry** in
the exact physics scope. D3 retained-entry membership is not required.

A D4 source selector accepts an entry only when all of the following resolve
and validate exactly:

1. supplied D3 entry identity and `entry_digest`;
2. exact D1 evaluation identity named by that entry;
3. full D1 evaluation and its exact `ScientificResult`;
4. full `ResultBinding` naming the same candidate, Twin, and design space;
5. exact candidate and Twin objects;
6. entry assignments equal the candidate assignments;
7. entry objective values equal the exact projected evaluation result;
8. D3 scope identity equals the loop physics-scope-backed memory scope;
9. requested slot/value equals the typed assignment in that exact candidate;
10. all sources in one recombination have identical physics scope.

Lookup is keyed by `(candidate_id, evaluation_id)` and then verified by entry
identity and digest. Candidate identity alone is never a source key.

D3 retention reasons, cap outcome, target status, Pareto/scoped-elite status,
threshold classification, and retention reason strings may be recorded only as
decision provenance explaining why a source was considered. They are not
scientific truth, are not source eligibility, and are never copied into a
child Candidate, Twin, result, eligibility record, or evidence reference.

## D4 compatibility, authority, and exact recombination

D7 performs exactly one forward recombination: frozen D4 Case C.

Selected exact sources:

- `component_a` and `guard_enabled` from the primary evaluation of
  `d4-parent-c`;
- `component_b`, `adapter`, and `control_level` from the primary evaluation of
  `d4-parent-d`.

Proposed assignment:

```text
component_a = A_stable
component_b = B_filter
adapter = buffered
control_level = 2
guard_enabled = true
```

All sources are in the same physics scope. Frozen D4 compatibility must return
`COMPATIBLE`. No objective value is read before materialization/evaluation.

### Authoritative event and derivation identities

The D7-bounded D4 event payload uses schema
`d7_authoritative_d4_event/1` and covers exactly:

1. physics-scope identity and complete scope payload;
2. compatibility-context id and complete compatibility-context/rule-set
   digest;
3. slot-schema id;
4. materialization-semantics id;
5. generation-admission-semantics id;
6. target generation number `1` and operator identity;
7. sorted full selected source records, each including candidate, Twin,
   evaluation, D3 entry identity/digest, typed slot, and typed value;
8. sorted parent candidate and Twin references;
9. complete sorted child assignment;
10. complete compatibility input and result, including failed rule ids;
11. frozen D4 analytic execution-semantics identity.

`d4_event_identity` is
`d7-d4-event:sha256:<canonical-event-payload-digest>`.

The candidate and Twin identities are deterministic functions of that event:

```text
candidate_id = d7-d4-child:sha256:<event-payload-digest>
twin_id      = d7-d4-derived-twin:sha256:<event-payload-digest>
twin version = 1
```

The materialized derivation payload uses schema
`d7_authoritative_d4_derivation/1` and covers the complete event payload and
identity, canonical child Candidate and Twin payloads and digests, child
assignment digest, exact parent/evaluation/D3 lineage, materialization
semantics, and generation-admission semantics.

`d4_derivation_identity` is
`d7-d4-derivation:sha256:<canonical-derivation-payload-digest>`.

The serialized derivation record is authoritative. `from_dict` must reconstruct
every nested typed object, rederive both identities and both child identities,
compare all recorded values, and fail closed on any mismatch. Changing a
source, parent, evaluation, Twin, D3 entry, assignment, physics scope,
compatibility input/result, rule-set digest, target generation, operator,
materialization semantics, or generation-admission semantics must change the
event or derivation identity. Reusing an old event, derivation, candidate, or
Twin identity with coherently substituted assignments is invalid.

## Exact D4 -> D5 child identity rule

D7 freezes identity choice **A**:

> D5 successor-generation membership consumes the exact authoritative D4
> materialized child identity.

D5 does not create a replacement candidate or replacement Twin. The canonical
child Candidate payload and reference stored by the D4 derivation are the only
Candidate payload and reference admitted to the successor generation. The
same is true of its Twin. "Same object" here means identical stable scientific
identity and byte-identical canonical payload; it does not mean the same Python
heap address after reload.

Lineage identities are acyclic and deterministic:

1. `generation_lineage_identity` covers source-generation identity, target
   generation `1`, exact child Candidate/Twin, sorted parents, D4 event and
   derivation identities, selected D3 source identities/digests, and operator;
2. `generation_member_identity` covers target generation `1`, exact child
   Candidate/Twin digests, lineage identity, and membership role
   `AUTHORITATIVE_D4_MATERIALIZATION`;
3. `successor_generation_identity` covers schema
   `d7_successor_generation/1`, source-generation identity, target generation,
   policy `d7-exact-d4-child-admission@0.1`, and the exact ordered member list.

The successor population has exactly one member. A different candidate with
equal assignments, a D5-prefixed replacement identity, or a new Twin fails
admission. Stored lineage alone must answer "yes" to "is this literally the
same stable scientific candidate object as the D4 child?"

## Loop-owned no-inheritance conformance rule

D7 owns one conformance validator across D4 materialization, D5 admission, and
D6-style selected execution. It remains loop-local.

Before a new child or selected-execution Twin is evaluated:

- `evidence_refs == ()`;
- `calibration_evidence_refs == ()`;
- no parent `ScientificResult` or result id is present;
- no parent evaluation id is present as child evidence;
- no parent validation, uncertainty/UQ, model adequacy, feasibility, safety,
  scientific validity, target status, Pareto/archive membership, D1
  eligibility, selection status, or evidence belonging to a parent system is
  inherited.

The combined normalized forbidden vocabulary is:

```text
adequacy
archive_membership
calibration_evidence_refs
evidence
evidence_refs
feasible
feasibility
model_adequacy
pareto
pareto_member
safety
safe
scientific_validity
selected
selection
selection_eligibility
selection_status
selection_truth
status
target
target_pass
truth
uq
uncertainty
valid
validation
validity
```

The validator recursively inspects candidate/Twin/pre-evaluation generation
payloads and non-scientific metadata. Required Twin schema fields
`evidence_refs` and `calibration_evidence_refs` are allowed only as empty
lists. A child result may contain its own newly produced validation or UQ only
when attributable to the child run; this experiment produces no UQ and uses an
empty validation report (`NOT_RUN`), so there is no inherited or manufactured
claim. After execution, the validator also rejects any parent result/evaluation
identity or payload appearing in child result values, provenance as evidence,
eligibility, assessment, archive, or status records.

Exact whitelisted lineage metadata contains only D4 event/derivation identity,
generation lineage/member identity, Study identity, selected option identity,
and execution-request identity. Decision-evidence binding ids remain on the
option/decision/Study provenance path; they are never placed in a new Twin's
`evidence_refs`.

## Successor scientific evaluation and typed D5 evidence

After exact D5 admission, the authoritative child is executed once under the
primary physics scope. The frozen D4 equations must produce:

```text
yield_score = 46.0
loss_score = 5.0
stability_score = 76.0
target = FAIL
```

The run, result, and evaluation are new and deterministic. The result contains
a producer-created D1 `ResultBinding` naming the exact D4 child Candidate, its
exact derived Twin, and `d4-domain-neutral-synthetic@0.1`. D1 eligibility is
set only after the result has all three finite canonical objectives and the
binding, scope, model, solver, run, and candidate validation gates pass.

### Exact D5 -> D6 evidence-binding rule

D6-style options consume `LoopDecisionEvidenceBinding` objects, never result-id
strings or population-id membership alone. The schema is
`d7_decision_evidence_binding/1`; each object contains and covers in its digest:

1. canonical Candidate payload and digest;
2. canonical ScientificTwin payload and digest;
3. canonical D1 `DesignEvaluation` payload and identity;
4. canonical `ScientificResult` payload, digest, and result id;
5. canonical D1 `ResultBinding` payload and digest;
6. provenance run identity;
7. physics-scope identity and payload digest;
8. source and successor generation identities;
9. generation member and lineage identities, or the explicit Generation 0
   baseline lineage identity;
10. D4 event/derivation identities when applicable;
11. exact objective projection and typed values.

`decision_evidence_binding_identity` is
`d7-decision-evidence:sha256:<binding-payload-digest>`.

Construction validates the whole graph: evaluation -> result -> ResultBinding
-> candidate/Twin/design space, run -> model/solver/scope, and generation ->
lineage. The evaluation's embedded result must be byte-identical to the bound
result. A correct result id with wrong content, binding, Candidate, Twin,
evaluation, lineage, run, or scope is invalid. Every option stores sorted
`(binding_identity, binding_digest)` pairs and the checkpoint stores the full
objects.

## Exact D6-style options and signal derivation

The evaluated candidate universe for novelty is the exact set of typed
Generation 0 primary/replicate evidence bindings plus the successor evidence
binding. Replicate assignments are deduplicated only for the mathematical set
used by Hamming distance; evidence lookup remains keyed by exact evaluation.
The canonical universe digest covers all binding identities/digests and all
typed assignments.

There are exactly three options:

| Label | Study id | Assignment | Exact typed evidence source |
|---|---|---|---|
| `A` | `d7-study-partial-success-adapter-variation-v0.1` | `A_stable`, `B_filter`, `isolated`, `2`, `true` | successor child binding |
| `B` | `d7-study-uncertainty-disagreement-boundary-v0.1` | `A_peak`, `B_filter`, `buffered`, `1`, `false` | successor child plus primary `d4-parent-a` and `d4-parent-d` bindings |
| `C` | `d7-study-novel-region-v0.1` | `A_base`, `B_base`, `isolated`, `0`, `true` | all evaluated-universe bindings |

Every Study specification carries the exact physics scope, assessment context,
complete typed assignment, execution model, solver, execution semantics,
decision question, and its source option identity.

### Declared scientific input records

The following are declared, attributable decision inputs rather than observed
scientific results:

- full alpha predictions from `d7.synthetic.model-alpha@0.1`;
- full beta predictions from `d7.synthetic.model-beta@0.1`;
- uncertainty values from
  `d7.synthetic.declared-uncertainty@0.1`;
- compute costs from `d7.synthetic.compute-cost@0.1`.

Declared uncertainty is a non-negative decision proxy for predicted
`yield_score` uncertainty. It is **not** calculated UQ and must never be stored
as `ScientificResult.uncertainty`.

### Derived signals

Novelty is deterministically computed from the exact evaluated assignment
universe:

```text
distance(a, b) = unequal_typed_slots(a, b) / 5
novelty(option) = min(distance(option, evaluated_candidate))
high_novelty = novelty >= 0.50
```

Model disagreement is derived from the full stored alpha/beta predictions:

```text
max(
  abs(alpha_yield - beta_yield) / 100,
  abs(alpha_loss - beta_loss) / 50,
  abs(alpha_stability - beta_stability) / 100
)
```

`high_disagreement` is `model_disagreement >= 0.20`.

Contradiction is derived, not declared: it is true exactly when alpha and beta
produce different PASS/FAIL classifications under the same exact assessment
context. `high_uncertainty` is true when declared uncertainty is `>= 0.25`.

`partial_success_relevance` is derived from typed evidence and exact lineage:
it is true only for a direct one-slot refinement of the successor child that
improved at least one objective relative to every relevant parent but failed
the overall target. `useful_failure_relevance` is derived from typed evidence:
it is true only for a one- or two-control-slot change from attributable
target-failing evidence whose parent-relative report records underperformance.
These are decision predicates, not truth about the unevaluated option.

The exact signal table is:

| Label | alpha `(yield,loss,stability)` | beta `(yield,loss,stability)` | declared uncertainty | derived disagreement | derived novelty | contradiction | partial success | useful failure | info units | cost | info/cost |
|---|---|---|---:|---:|---:|---|---|---|---:|---:|---|
| `A` | `(88,18,66)` | `(84,20,64)` | 0.08 | 0.04 | 0.20 | false | true | false | 1 | 1 | `1/1` |
| `B` | `(52,22,54)` | `(72,32,38)` | 0.31 | 0.20 | 0.40 | false | false | false | 2 | 2 | `2/2` |
| `C` | `(60,24,62)` | `(50,29,72)` | 0.18 | 0.10 | 0.60 | false | false | false | 1 | 5 | `1/5` |

`information_proxy_units` is the count of six predicates: high uncertainty,
high disagreement, high novelty, contradiction, partial-success relevance,
and useful-failure relevance. It is not Shannon information and is not a
quality score.

### Option and decision authority

An option identity is `d7-option:sha256:<digest>` over canonical schema
`d7_experiment_option/1` containing exactly:

1. option-set id and label;
2. complete Study specification and proposed assignment;
3. physics-scope and assessment-context identities and payload digests;
4. sorted evidence-binding identities and digests;
5. novelty-universe identity/digest;
6. complete alpha and beta prediction records, including source ids/versions
   and all three predictions;
7. declared uncertainty source/value;
8. all derived signals and their derivation-semantics ids;
9. partial-success/useful-failure source lineage;
10. compute-cost source/value;
11. decision-policy id/version;
12. execution-semantics id.

Changing a prediction while preserving the same disagreement value still
changes option identity. Any reuse of the old identity fails validation.

The exact selection policy is
`d7-information-per-compute-lexicographic@0.1`:

1. validate and rederive every option and signal;
2. reject missing/duplicate/invalid options;
3. maximize the exact rational `information_proxy_units / compute_cost`;
4. tie-break by higher information units;
5. then higher model disagreement;
6. then lexicographically smallest option identity.

Expected selected option: **B**. Its predicted target classification is FAIL;
selection does not assert success.

`decision_identity` is `d7-decision:sha256:<digest>` over schema
`d7_next_experiment_decision/1`, the full validated serialized option payloads
and digests, option-set id, exact policy identity/version and selection basis,
ordered ranking, selected option identity, physics scope, assessment context,
and evidence-universe digest.

The decision serializes its complete options. Reload must parse and validate
those stored options, rederive their signals and identities, re-run selection,
and compare the recorded decision identity and winner. It must not discard
serialized content and reconstruct a global hardcoded option table.

## Exact selected-execution binding requirements

Only option B executes. The exact typed chain is:

```text
NextExperimentDecision
-> selected option B
-> LoopStudy / execution specification
-> DesignCandidate
-> ScientificTwin(kind=DERIVED)
-> execution request / run
-> solver/model execution
-> ScientificResult
-> ResultBinding
-> ELIGIBLE DesignEvaluation
```

The `LoopStudy` identity covers selected option/decision identity, complete
assignment, both separate context identities, problem, model, solver,
execution semantics, and evidence bindings as decision provenance.

Exact identity derivation is:

```text
selected_study_identity = d7-study:sha256:<digest of d7_loop_study/1 payload>

selected_materialization_digest = sha256(canonical d7_selected_materialization/1 payload)
selected_candidate_identity = d7-selected-candidate:sha256:<selected_materialization_digest>
selected_twin_identity      = d7-selected-twin:sha256:<selected_materialization_digest>, version 1

execution_request_identity = d7-execution-request:sha256:<digest of d7_execution_request/1 payload>
selected_run_identity      = d7-selected-run:sha256:<execution-request-payload-digest>
selected_result_identity   = d7-selected-result:sha256:<digest of d7_execution_outcome/1 payload>
```

The materialization payload covers Study/decision/option identities, exact
assignment, design space, physics scope, assessment context, parent Twin
reference, and materialization semantics. The execution-request payload covers
the complete Study, Candidate, Twin, problem, model, solver, fidelity, scope,
assignment, and execution semantics. The outcome payload covers the complete
validated request, run, typed result values, convergence, model, solver,
problem, and result-binding digest.

The selected Candidate, Twin, and run identities are deterministic functions
of the validated reloaded Study and execution-request payloads. They are new
and globally distinct from every Generation 0/successor identity. The selected
Twin represents the proposed assignment, cites the authoritative predecessor
Twin only through ordinary derived lineage where frozen Twin semantics require
a parent, and starts with:

```text
evidence_refs = ()
calibration_evidence_refs = ()
```

Prior D5 results and decision-evidence bindings remain on the decision/Study
provenance path. They do not become evidence belonging to this unevaluated
Twin. After execution, the new result is attributable evidence *about* this
Twin through `ResultBinding` and D1; D7 does not mutate the immutable Twin or
pretend decision provenance was evidence.

Before the solver starts, an execution validator requires exact equality of:

- decision and selected option identity;
- Study identity and complete assignment;
- physics-scope and assessment-context identities in their separate fields;
- Candidate identity, design space, assignments, generation/operator, and
  Study derivation;
- Twin identity, version, kind, declarations/assignments, model, and empty
  evidence fields;
- problem identity, model reference, solver identity, fidelity marker, and
  execution semantics;
- deterministic execution-request and run identities.

No substituted assignment, Candidate, Twin, Study, scope, model, solver, or run
may execute under the recorded decision.

The frozen D4 equations produce the exact selected result:

```text
yield_score = 35.0
loss_score = 33.0
stability_score = -12.0
target = FAIL
```

The `ScientificResult` must contain:

- the exact new result id derived from the run and canonical outcome;
- the exact three typed dimensionless values;
- problem `d4-synthetic-objectives-v0.1`;
- model `d4.synthetic.analytic@0.1`;
- solver `d4.closed-form.synthetic@0.1`;
- exact provenance run id and direct execution inputs;
- exact D1 `ResultBinding` in provenance metadata;
- Study/decision/option references as decision provenance, not scientific
  evidence;
- empty computed-UQ map and empty validation report (`NOT_RUN`).

`selected_result_binding_digest` is SHA-256 over canonical
`ResultBinding.to_dict()`, and `selected_result_binding_identity` is
`d7-result-binding:sha256:<digest>`.

Every digest-derived record in D7 excludes its own recorded identity field from
the identity payload. `from_dict` always rederives the identity from the other
authoritative fields and compares it with the recorded identity.

The result id, run id, Candidate, Twin, design space, problem, model, solver,
scope, and Study must all be unique and exactly mutually consistent. A target
FAIL remains eligible if the scientific execution and binding gates pass.

## Exact D6 result -> D1 -> D3 admission rule

This is the primary blocking rule.

1. Construct `ResultBinding` directly from the already materialized selected
   Candidate reference, selected Twin reference, and exact design-space
   reference. No string-to-object repair map is permitted.
2. Require the `ScientificResult` provenance to carry that byte-identical
   binding and exact run/Study/scope/model/solver inputs.
3. Derive `selected_evaluation_identity` as
   `d7-returned-evaluation:sha256:<digest>` from schema
   `d7_returned_design_evaluation/1`, selected Candidate/Twin, result id and
   digest, ResultBinding digest, run id, physics scope, and fixed eligibility
   policy id `d7-closed-execution-eligibility@0.1`.
4. Create a D1 `DesignEvaluation` with that exact Candidate, Twin, design
   space, embedded result, and `SelectionEligibility.ELIGIBLE` only when the
   solver completed the preregistered closed-form execution, all three projected
   objectives are finite and correctly typed, and every exact execution/binding
   requirement above passes.
5. Use the fixed eligibility reason:

   ```text
   preregistered D7 selected synthetic execution completed with finite projected objectives and exact Candidate/Twin/Study/result binding
   ```

6. Call `DesignMemoryEntry.from_evaluation` with the real selected Candidate,
   real eligible evaluation, and the existing primary D3 physics scope. The
   builder must project values from the embedded result and revalidate the
   candidate/Twin/design-space `ResultBinding`; no entry field is caller
   invented.
7. Rebuild/extend `DesignMemoryLayerA` deterministically with the new entry,
   preserving all prior entries and exact scope. Reclassify under the same D7
   policy without converting retention reasons into truth.
8. Pass the returned entry through the exact D4 source selector for slot
   `component_a = A_peak`. The selector must produce a valid next-cycle source
   record bound to the returned evaluation, result, Candidate, Twin, entry
   identity/digest, and physics scope.
9. Record `next_cycle_d4_source_identity`; do not assess or materialize a
   Generation 2 recombination.

The new result alone is not admissible to D3. An ineligible, unknown, missing,
or improperly bound evaluation must be rejected by D3. If the returned entry
cannot become an exact D4 source, D7 fails even if it was retained or classified.

## Exact end-to-end experiment steps

1. **Construct and evaluate Generation 0.** Materialize the four exact
   candidates/Twins; execute four primary runs plus the `d4-parent-c` repeat;
   create real results, bindings, and eligible D1 evaluations.
2. **Build D3 memory.** Build the exact physics-backed D3 scope, five Layer A
   entries, and the deterministic D7 classification record.
3. **Select D4 sources.** Select the primary `d4-parent-c` and
   `d4-parent-d` evaluation entries under the Layer-A source rule; prove the
   replicate cannot substitute for the primary.
4. **Assess compatibility and materialize one authoritative child.** Execute
   frozen D4 Case C compatibility; derive the authoritative event,
   Candidate/Twin, and derivation identities; create no inherited evidence.
5. **Admit the exact child into the successor generation.** Use the literal D4
   Candidate/Twin and exact lineage; create no D5 replacement identity.
6. **Perform a new scientific evaluation.** Execute the admitted child once,
   create its new result/binding/eligible evaluation, and observe `(46,5,76)`.
7. **Construct typed D6-style evidence and options.** Build full evidence
   bindings, the evaluated-universe digest, three exact options, declared
   predictions/uncertainty/cost, and derived signals.
8. **Select exactly one next experiment.** Validate all options and select B
   deterministically under the exact information-per-compute policy.
9. **Save, terminate, reload, and continue.** Serialize the complete state at
   the decision-recorded/pre-execution boundary; discard all in-memory D7
   objects; reload, rederive, and validate the full graph and decision.
10. **Execute the selected typed Study/Candidate/Twin chain.** Materialize exact
    selected objects from the reloaded option and run the frozen solver/model.
11. **Create the new selected `ScientificResult`.** Record `(35,33,-12)` with
    exact run, scope, model, solver, binding, Study, and decision provenance.
12. **Create the proper eligible D1 evaluation and admit it to D3.** Apply the
    closed execution eligibility rule and build the returned Layer A entry only
    through D1/D3 typed builders.
13. **Prove next-cycle source usability, then stop.** Select the returned entry
    as an exact D4 source for a hypothetical next generation, record its source
    identity, and do not execute Generation 2.

## Machine-readable object trace

The final local artifact contains schema `d7_integrated_object_trace/1` and at
minimum these exact fields:

```text
initial_candidate_id
initial_twin_id
initial_evaluation_id
initial_result_id
initial_run_id
generation0_candidate_ids
generation0_twin_ids
generation0_evaluation_ids
generation0_result_ids
generation0_run_ids

memory_entry_identity
memory_entry_digest
memory_scope_identity

d4_source_evaluation_ids
d4_event_identity
d4_derivation_identity
d4_materialized_child_identity
d4_materialized_twin_identity

successor_generation_identity
generation_member_identity
generation_lineage_identity

successor_evaluation_id
successor_result_id
successor_run_id

decision_evidence_binding_ids
decision_evidence_binding_digests
experiment_option_identities
decision_identity
selected_option_identity

selected_study_identity
selected_candidate_identity
selected_twin_identity
selected_run_identity
selected_evaluation_identity
selected_result_identity
selected_result_binding_identity
selected_result_binding_digest

returned_memory_entry_identity
returned_memory_entry_digest
returned_memory_scope_identity

next_cycle_d4_source_identity
checkpoint_identity
final_trace_identity
```

`initial_*` is the primary `d4-parent-c` chain. Every field is copied from or
derived from a typed authoritative object; none is a manually maintained alias.
`final_trace_identity` is the digest of the complete trace excluding only that
field. Reload/replay must produce a byte-identical trace.

## Save / reload / continue semantics

The scientifically meaningful checkpoint boundary is after Step 8, when the
decision is authoritative, and before any selected execution exists.

The local checkpoint envelope has schema
`d7_integrated_loop_checkpoint/1`, phase
`DECISION_RECORDED_PRE_EXECUTION`, milestone name/version, a complete payload,
and `checkpoint_identity`. The payload contains canonical full serialized
objects for:

- physics scope and assessment context;
- all Generation 0 Candidates, Twins, results, bindings, evaluations, and runs;
- D3 scope, Layer A entries, policy, and classification record;
- D4 source records, compatibility result, event, materialized child/Twin, and
  authoritative derivation;
- successor generation, member, lineage, result, binding, and evaluation;
- every typed decision evidence binding and novelty-universe record;
- full declared prediction, uncertainty, and cost input records;
- complete serialized options, ranking, and decision;
- the partial object trace.

Serialization is UTF-8 canonical JSON with sorted keys, deterministic list
ordering defined by identity, finite typed numbers, explicit schema versions,
no insignificant whitespace, and no timestamp. `checkpoint_identity` is the
SHA-256 digest over the envelope payload excluding only the identity field.
The checkpoint is the local versioned file
`experiments/design_d7/artifacts/d7_checkpoint-v0.1.json`, written atomically.
The final trace/report payload is
`experiments/design_d7/artifacts/d7_results.json`. Neither may be a hidden test
fixture.

Continuation procedure:

1. write the checkpoint and retain only its bytes/path;
2. terminate or delete all D7 in-memory objects and mutable caches;
3. parse the serialized envelope using `from_dict` for every nested type;
4. rederive every digest/identity, validate exact schemas and required fields,
   validate global uniqueness, and validate all graph edges;
5. reconstruct D3 classifications from stored Layer A plus stored policy and
   compare byte-for-byte;
6. revalidate D4 event/derivation and exact D4 -> D5 object identity;
7. rederive every decision signal from stored evidence/predictions, validate
   full stored options, rerun selection, and compare the decision;
8. continue Step 10 using only the reloaded selected option and Study
   specification.

The serialized artifact is authoritative. Reload must not depend on Python
object identity, mutable globals, timestamps, hidden fixture regeneration,
process state, insertion order, or hardcoded D3-D6 milestone constants. Frozen
ids and policy versions may validate stored declarations; they may not replace
omitted or altered serialized objects. Missing lineage, scope, option content,
or evidence content fails closed.

## Adversarial cases and frozen outcomes

Unless an allowed outcome is explicitly stated, rejection means
`InvalidScientificProblem` before a new authoritative downstream object is
created.

| Case | Adversarial attempt | Frozen expected outcome |
|---|---|---|
| **N1** | Supply mixed physics scopes to D4 | Reject before compatibility/materialization; no authoritative event or child |
| **N2** | Change assessment thresholds/reporting only and treat it as physics change | Allowed re-assessment under a new assessment identity; physics identity, Layer A digests, and results remain unchanged; any forced physics split is a test failure |
| **N3** | Change model, solver, conditions, or design space while retaining the assessment label | New physics identity is mandatory; attempted comparison/recombination under the old scope is rejected |
| **N4** | Supply the correct candidate with the wrong D3 evaluation | Reject exact source attribution; the replicate cannot replace the preregistered primary |
| **N5** | Supply the wrong Twin for the correct D3 result | Reject through result-binding/evaluation/source validation |
| **N6** | Alter D4 child assignments while reusing the original event, derivation, or child identity | Reject; if honestly regenerated, event, derivation, Candidate, and Twin identities change |
| **N7** | Substitute an unrelated or assignment-equal D5 candidate for the D4 child | Reject generation admission; no successor member/evaluation |
| **N8** | Attach parent evidence to the unevaluated derived Twin | Reject under loop no-inheritance rule |
| **N9** | Copy a parent `ScientificResult` or result id into the successor child | Reject; no child evaluation |
| **N10** | Copy parent target, Pareto/archive, UQ, validation, adequacy, eligibility, selection, or status into the child | Reject under combined recursive vocabulary/identity scan |
| **N11** | Use a correct result id with wrong binding, content, evaluation, run, lineage, or scope as D6 evidence | Reject typed evidence binding; option invalid |
| **N12** | Alter any alpha/beta prediction while reusing the option identity, even if disagreement is unchanged | Reject identity mismatch; honest regeneration changes option and decision identity |
| **N13** | Alter serialized option content before decision reload | Reject checkpoint/option/decision validation; never rebuild from global option constants |
| **N14** | Execute selected option B with a different assignment | Reject before solver start; no result |
| **N15** | Execute selected option B with a different Twin | Reject before solver start; no result |
| **N16** | Produce selected result with wrong or missing `ResultBinding` metadata | D1 construction rejects; no eligible evaluation or D3 entry |
| **N17** | Mismatch Candidate, Twin, Study, scope, model, solver, run, result, or evaluation relationship | Reject exact execution graph; no return admission |
| **N18** | Admit a new `ScientificResult` to D3 without an `ELIGIBLE` D1 evaluation | D3 rejects; return arrow fails |
| **N19** | Duplicate any run, result, evaluation, option, generation-member, or returned-entry identity | Reject global uniqueness before continuation/admission |
| **N20** | Offer multiple evaluations for `d4-parent-c` in different orders and select by candidate-id last-wins behavior | Only the exact primary evaluation is accepted; both offer orders produce the same source; last-wins behavior is a test failure |
| **N21** | Alter checkpoint bytes/content before reload | Reject envelope digest or nested `from_dict` rederivation |
| **N22** | Omit lineage, scope, binding, option, or required trace content from checkpoint | Reject exact schema/graph completeness; no continuation |
| **N23** | Insert decision provenance or prior D5 result refs into the new selected Twin's `evidence_refs` | Reject before execution; fields must be empty |
| **N24** | Complete selected execution and D3 admission but fail to select the returned entry as a next-cycle D4 source | **D7 FAILS**; no Generation 2 execution is attempted |

## Blocking gates

All A1-A23 are blocking.

- **A1 - Frozen semantic protection.** D0-D6, MVR0, MVR1,
  ScientificTwin, and frozen milestone semantics are unmodified.
- **A2 - Typed physics scope.** Every comparable object and execution is bound
  to the exact loop physics scope; any scientific scope input change changes
  identity.
- **A3 - Assessment separation.** Assessment/decision context is separately
  typed and identified; assessment-only change preserves physics evidence, and
  physics change cannot hide behind an assessment label.
- **A4 - Single-scope D4 enforcement.** Every D4 source in a recombination has
  exactly one physics scope; mixed scopes fail closed before materialization.
- **A5 - Exact D3 evaluation attribution.** Sources are keyed by exact
  candidate/evaluation plus entry identity/digest; the multiple-evaluation
  adversary cannot select the wrong evaluation.
- **A6 - Authoritative D4 derivation.** Event and derivation identities cover
  every scientifically meaningful source, assignment, compatibility, scope,
  materialization, and generation input and validate under reload.
- **A7 - Exact D4 -> D5 child identity.** The successor member is the literal
  authoritative D4 child Candidate/Twin; no replacement identity exists.
- **A8 - Empty new-child evidence.** Every unevaluated derived/selected Twin
  begins with empty evidence and calibration-evidence refs.
- **A9 - Unified no-inheritance conformance.** One loop-owned validator blocks
  parent results, evidence, and the complete forbidden status vocabulary across
  D4, D5, and selected execution.
- **A10 - Typed D5 -> D6 evidence.** Every decision signal source is a complete
  validated evidence binding, not a result-id membership check.
- **A11 - Evidence-derived novelty.** Novelty is recomputed exactly from the
  complete typed evaluated-candidate universe and matches the frozen table.
- **A12 - Decision-relevant option identity.** Full predictions, evidence,
  scope, assignment, Study, uncertainty source/value, derived signals, cost,
  policy, and execution semantics affect option identity.
- **A13 - Authoritative decision reload.** Reload validates stored full options
  and reruns selection; it never replaces stored content with a global table.
- **A14 - Exact selected execution binding.** Decision, option, Study,
  Candidate, Twin, scope, model, solver, run, assignment, and result match
  exactly; substitutions fail before execution/admission.
- **A15 - Proper D1 `ResultBinding`.** The selected result carries the exact
  producer-side Candidate/Twin/design-space binding and a deterministic binding
  identity/digest.
- **A16 - Eligible D1 evaluation.** A new, unique, correctly bound D1
  evaluation becomes `ELIGIBLE` only under the frozen completed-execution rule;
  target FAIL does not change eligibility.
- **A17 - D3 return admission.** The eligible selected evaluation creates its
  D3 entry only through `DesignMemoryEntry.from_evaluation` and enters the
  exact physics-backed Layer A.
- **A18 - Next-cycle D4 usability.** The returned entry passes the exact D4
  source selector and produces `next_cycle_d4_source_identity`.
- **A19 - Save/reload/continue.** The complete decision-boundary checkpoint
  round-trips, validates, and continues without hidden reconstruction.
- **A20 - Order/process invariance.** Candidate/evaluation/source/option input
  permutations and a process restart produce the same authoritative identities,
  decision, selected execution, returned entry, and trace.
- **A21 - Adversarial conformance.** N1-N24 produce exactly their preregistered
  outcomes.
- **A22 - No status inflation.** Target, Pareto, retention, compatibility,
  generation, prediction, uncertainty, contradiction, and selection states
  never inflate into scientific validity, feasibility, safety, adequacy,
  optimization, or truth.
- **A23 - Full regression safety.** Targeted D7 tests and the complete repository
  regression pass before any D7 freeze.

Failure of any blocking gate means D7 fails. An expected target FAIL or model
prediction miss does not fail D7 when the execution remains attributable.

## Informative outcomes

The following are recorded as evidence and are not milestone pass conditions:

- **I1.** Whether D3 retention reasons are necessary for useful source
  selection. D7 deliberately permits any attributable Layer A entry.
- **I2.** Whether D4 child identity should become a general derivation-identity
  concept.
- **I3.** Whether the loop no-inheritance validator deserves future Core
  promotion.
- **I4.** Whether physics-scope representation should move toward a generic
  Core contract.
- **I5.** Whether generic provenance/lineage infrastructure is justified.
- **I6.** Whether general next-experiment option/decision abstractions are
  justified.
- **I7.** Whether D2 proposal/materialization contracts should be reused by
  future loop work.

## Architecture deliberately unresolved

D7 may force a bounded integration layer, loop-local physics/assessment scope,
loop-local authoritative derivation wrapper, loop-local typed evidence binding,
loop-local checkpoint envelope, loop-local no-inheritance validator, and
loop-local variable-cardinality generation/decision records.

It does not decide or promote:

- a generic Core physics-scope abstraction;
- a generic Core derivation/event identity;
- generic multi-parent ScientificTwin lineage;
- a generic generation/population abstraction;
- a generic evidence-binding graph;
- a generic `NextExperimentDecision` or signal framework;
- a generic no-inheritance vocabulary/validator;
- a generic provenance/lineage database;
- whether D2 proposal/materialization is the eventual loop boundary;
- optimization, repeated-loop, scheduling, or autonomous-agent architecture.

These remain empirical future questions. D3-D6 are not rewritten to make the
integrated path aesthetically uniform.

## Storage and explicit exclusions

D7 uses only local deterministic versioned serialized artifacts/checkpoints.

Explicitly out of scope:

- PostgreSQL;
- S3;
- Redis;
- external persistence;
- queues, schedulers, Kubernetes, or cloud services;
- distributed execution;
- production persistence;
- Bayesian optimization or BoTorch;
- surrogate/acquisition optimization;
- LLM orchestration or autonomous hypothesis generation;
- multi-fidelity optimization;
- a repeated or infinite loop;
- Generation 2 execution;
- D8, D9, or later milestones.

The checkpoint proves semantic replay, not durability, authenticity against a
malicious writer, or production storage architecture.

## Falsifiability and freeze rule

An independent implementation using only this preregistration must obtain the
same:

- exact physics/assessment separation;
- five Generation 0 evaluations and the multiple-evaluation source behavior;
- D4 Case C assignment and `(46,5,76)` successor result;
- authoritative D4 event/derivation and literal D4 -> D5 child identity rule;
- exact A-C options/signals and selected option B;
- decision-boundary save/reload behavior;
- selected assignment and `(35,33,-12)` result;
- exact D1 eligibility and D3 return-admission behavior;
- next-cycle D4 source acceptance;
- N1-N24 outcomes and A1-A23 gate outcomes;
- machine-readable object trace and replay identities.

If implementation freedom remains to choose scope fields, source eligibility,
child identity semantics, signal derivation, option membership, selection
policy, checkpoint reconstruction, execution binding, D1 eligibility, or D3
return admission after observing results, this is not a closed preregistration.

This document is frozen before implementation. A discovered insufficiency must
be reported as D7 evidence or addressed by an explicit new preregistration; it
must not be silently weakened after execution.
