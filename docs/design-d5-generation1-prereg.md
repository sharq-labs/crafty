# D5 - Generation 1 / Memory-Informed Candidate Generation V0.1 preregistration

Status: **FROZEN BEFORE IMPLEMENTATION**

Starting stable checkpoint: `0cb5e5b72d67a6e77cc17f388d1b3e4c17581ca2` (D4 PASS/FROZEN)

Milestone ID: `D5`

## Purpose

D5 tests the first controlled population-level successor generation:

```text
Generation 0
-> new scientific evaluation
-> D3 attributable memory
-> D4 compatibility / recombination
-> deterministic Generation 1 proposal set
-> new Generation 1 Candidates and ScientificTwins
-> new scientific evaluation
-> Generation 1 ScientificResults
```

D5 is not autonomous discovery. It does not implement an optimizer, adaptive
explore/exploit intelligence, Bayesian optimization, surrogate modeling,
evolutionary search, mutation/crossover framework, active learning, LLM
orchestration, hypothesis generation, coefficient tuning, or repeated
self-evolution loop.

The core principle remains:

```text
experiment pulls architecture
```

This document preregisters one concrete experiment only. D5 implementation must
not start until this document is frozen.

## Frozen inspection basis

D5 is preregistered after inspecting the frozen repository at the D4 checkpoint.

Relevant frozen semantics:

- D0 `DesignCandidate` is exact typed assignment identity bound to one exact
  `TwinReference`. Generation and parent references are explicit lineage only.
  They do not assert feasibility, validation, adequacy, safety, optimality, or
  truth.
- D1 `DesignEvaluation` binds one exact candidate, one exact Twin, one exact
  design space, and one complete attributable `ScientificResult`. Selection
  eligibility is explicit and is not inferred from result usability, target
  status, or archive membership.
- D2 `CandidateGenerationPlan` creates generation-zero candidates only and
  explicitly rejects nonzero generation. D5 must therefore not pretend D2 already
  supports memory-informed successor generation.
- D3 memory separates Layer A attributable observations from Layer B retention
  and classification policy. D3 retention reasons are decision provenance only.
  They are not inherited scientific truth.
- D4 compatibility and recombination demonstrated local source records,
  compatibility results, recombination events, derivation records, derived
  candidates, derived Twins, and mandatory new child evaluation. D4-local
  abstractions were not promoted into Core.
- ScientificTwin V0.1 keeps Candidate, Twin, Study/context, and
  ScientificResult separate. A derived Twin does not inherit parent evidence,
  results, validation, UQ, target pass, or Pareto/archive status.
- Existing persistent records use schema-versioned deterministic JSON, sorted
  mapping keys, typed scientific values, explicit identities, and fail-closed
  schema/digest checks.

## Critical scientific rule

Parent observations may influence which Generation 1 proposals are attempted.
They must not assert what the Generation 1 scientific result will be.

The following implication remains invalid:

```text
parent candidate had a good or retained observation
therefore child candidate has that observation
```

The only valid D5 flow is:

```text
Generation 0 result
-> D3 memory entry / retention reason as decision provenance
-> D5 proposal policy
-> D4 compatibility assessment
-> Generation 1 candidate materialization
-> new ScientificTwin identity
-> new D1 evaluation under the frozen study scope
-> new ScientificResult
```

Every Generation 1 candidate starts scientifically unknown.

## Scientific questions

**Q1 - Deterministic successor population.** Can a complete Generation 1
population be generated deterministically from attributable Generation 0
scientific evidence?

**Q2 - Memory influence without truth inheritance.** Can D3 memory influence
proposal generation while remaining decision provenance rather than scientific
truth?

**Q3 - Compatibility fail-closed boundary.** Can D4 compatibility prevent invalid
or incompatible proposals before materialization while still allowing accepted
children to remain scientifically uncertain?

**Q4 - Exact lineage.** Can every Generation 1 candidate be traced exactly to
its proposal, source parents, D3 memory entries, compatibility assessment,
recombination/materialization event, Twin, Study/evaluation, and result?

**Q5 - Identity separation.** Can Generation 1 candidate and Twin identities
remain deterministic and distinct from Generation 0 identities?

**Q6 - Mandatory new evaluation.** Does every Generation 1 scientific claim come
only from a new evaluation rather than inherited parent results, target status,
or Pareto/archive status?

**Q7 - Frozen comparison.** Under one frozen scientific scope, how does
Generation 1 compare with Generation 0 on preregistered metrics?

**Q8 - Core abstraction evidence.** Does the experiment justify adding generic
Core concepts such as `GenerationPlan`, `EvidenceInformedProposal`,
`GenerationLineage`, or `PopulationDerivation`, or should this policy remain
experiment/system owned?

Q8 is empirical. D5 must not answer it from architectural aesthetics.

## Concrete experiment

D5 uses the frozen D4 synthetic compositional system because it is the smallest
domain-neutral fixture already containing:

- typed mixed design slots;
- deterministic analytic evaluation equations;
- Generation 0 parent candidates;
- D3 attributable memory entries;
- D4 compatibility rules;
- D4 recombination/materialization lineage;
- mandatory new child scientific evaluation.

D5 must not generalize D4 abstractions into Core merely for convenience.

## Scientific scope

Generation 0 and Generation 1 are directly comparable only inside this exact
scope:

- design space id: `d4-domain-neutral-synthetic`
- design space version: `0.1`
- objective context reference: `d5-generation-comparison-scope-v0.1`
- model reference: `d4.synthetic.analytic@0.1`
- solver identity: `d4.closed-form.synthetic@0.1`
- problem id: `d4-synthetic-objectives-v0.1`

Objectives:

| Objective | Metric | Direction | Unit |
|---|---|---|---|
| `yield_score` | `yield_score` | maximize | `dimensionless` |
| `loss_score` | `loss_score` | minimize | `dimensionless` |
| `stability_score` | `stability_score` | maximize | `dimensionless` |

Target assessment is informative only:

```text
yield_score >= 70
loss_score <= 25
stability_score >= 50
```

Target pass/fail is not D1 eligibility, feasibility, validation, or scientific
truth.

If any implementation changes the scientific scope materially, objective
performance comparison must fail closed and report the populations separately.

## Design space

The experiment uses exactly five typed slots:

| Slot | Type | Values |
|---|---|---|
| `component_a` | categorical | `A_base`, `A_peak`, `A_stable` |
| `component_b` | categorical | `B_base`, `B_peak`, `B_filter` |
| `adapter` | categorical | `direct`, `buffered`, `isolated` |
| `control_level` | integer | `0`, `1`, `2` |
| `guard_enabled` | boolean | `false`, `true` |

All assignments use the frozen typed `ScientificValue` contracts:
`CategoricalValue`, `IntegerValue`, and `BooleanValue`.

## Frozen evaluation equations

For every materialized candidate in either generation:

```text
yield_score =
  A_yield[component_a]
  + B_yield[component_b]
  + adapter_yield[adapter]
  + 2 * control_level
  - 3 * guard_enabled
  + interaction_yield[component_a, component_b]

loss_score =
  A_loss[component_a]
  + B_loss[component_b]
  + adapter_loss[adapter]
  + control_level
  + 5 * guard_enabled
  + interaction_loss[component_a, component_b]

stability_score =
  A_stability[component_a]
  + B_stability[component_b]
  + adapter_stability[adapter]
  + 3 * control_level
  + 10 * guard_enabled
  + interaction_stability[component_a, component_b]
```

Base tables:

| Value | yield | loss | stability |
|---|---:|---:|---:|
| `A_base` | 20 | 5 | 10 |
| `A_peak` | 50 | 20 | -10 |
| `A_stable` | 25 | 8 | 25 |
| `B_base` | 12 | 4 | 8 |
| `B_peak` | 35 | 15 | -15 |
| `B_filter` | 10 | -10 | 20 |
| `direct` | 3 | 0 | -2 |
| `buffered` | -2 | 4 | 5 |
| `isolated` | -5 | 8 | 12 |

Interaction table defaults to `(0, 0, 0)` except:

| Pair | yield delta | loss delta | stability delta |
|---|---:|---:|---:|
| `A_peak` + `B_filter` | -25 | +18 | -30 |
| `A_stable` + `B_filter` | +12 | -4 | +10 |
| `A_stable` + `B_peak` | +18 | +10 | -8 |

The forbidden pair `A_peak` + `B_peak` has no scientific evaluation because it
must fail compatibility before materialization.

## Generation 0 definition

Generation 0 is a frozen non-memory-informed baseline population. It is
declared before D5 and is identical to the D4 parent evidence set so that D5 can
reuse the smallest already-frozen D3/D4 fixture.

- population id: `d5-g0-baseline-population-v0.1`
- generation number: `0`
- generator id: `d5-enumerated-baseline-v0.1`
- generator semantics: emit the following rows in table order with no random
  state, no memory input, no sorting by objective values, and no rejection path.
- candidate operator: `declared:d4-preregistered-parent`
- all candidates bind new or existing exact `ScientificTwin(kind=CANDIDATE)`
  references with id `d4-twin:<candidate_id>` and version `1`.
- all candidates receive new D1 evaluations under the scientific scope above.

| Candidate id | component_a | component_b | adapter | control_level | guard_enabled | Expected objective inputs |
|---|---|---|---|---:|---|---|
| `d4-parent-a` | `A_peak` | `B_base` | `buffered` | 2 | false | evaluate by frozen equations |
| `d4-parent-b` | `A_base` | `B_peak` | `direct` | 0 | false | evaluate by frozen equations |
| `d4-parent-c` | `A_stable` | `B_base` | `direct` | 1 | true | evaluate by frozen equations |
| `d4-parent-d` | `A_base` | `B_filter` | `buffered` | 2 | true | evaluate by frozen equations |

Generation 0 size is exactly `4`.

The Generation 0 D1 evaluations are eligible for selection archives only because
the synthetic closed-form evaluation completes and the caller supplies explicit
D1 eligibility reason:

```text
preregistered D5 Generation 0 synthetic evaluation
```

Eligibility does not imply target pass, feasibility, validation, or truth.

## Generation 0 D3 memory policy

D3 memory is built only after Generation 0 evaluation.

- scope: the scientific scope above;
- eligible set: the four Generation 0 D1 evaluations;
- retention policy id: `d5-g0-memory-policy-v0.1`;
- cap: `4`;
- elite scopes: `("yield_score")`, `("loss_score")`, `("stability_score")`;
- assessment context id: `d5-target-context-v0.1`;
- threshold map: the informative target thresholds above;
- threshold tolerances: `yield_score=0`, `loss_score=0`, `stability_score=0`;
- explicit retention: none;
- partition function: the exact byte string
  `component_a=<value>|component_b=<value>` encoded as UTF-8.

The D5 proposal policy may read:

- D3 entry identity;
- D3 entry digest;
- candidate reference;
- Twin reference;
- evaluation reference;
- typed assignments;
- retention reasons/classifications as decision provenance.

The D5 proposal policy may not read any D3 retention reason as child truth.

## D4 compatibility context reused by D5

D5 reuses the frozen D4 local context without modifying it:

```text
compatibility_context_id = d4-synthetic-compat-v0.1
slot_schema_id = d4-synthetic-slots-v0.1
materialization_semantics_id = d4-synthetic-materialization-v0.1
```

Compatibility is evaluated before materialization and before Generation 1
scientific evaluation.

Only `COMPATIBLE` proposals may materialize. `INCOMPATIBLE` and `INVALID`
proposals remain recorded proposal outcomes and create no candidate, no Twin,
and no ScientificResult.

## Generation 1 proposal policy

Generation 1 has one deterministic proposal plan:

- plan id: `d5-generation1-plan-v0.1`
- source population id: `d5-g0-baseline-population-v0.1`
- target generation number: `1`
- accepted population target: `4`
- proposal budget: `5`
- primary policy id: `d5-memory-informed-recombination-v0.1`
- novelty policy id: `d5-assignment-novelty-v0.1`
- duplicate policy: exact assignment digest duplicates fail closed;
- overflow policy: if more than four proposals materialize, keep the first four
  accepted proposals in proposal-label order and fail closed if any later
  accepted proposal would have a duplicate assignment or identity.

Proposal labels are evaluated in exact order: `A`, `B`, `C`, `D`, `E`.

No rule may be replaced by "take the best candidates." Parent objective values
and D3 retention classifications explain why the proposals were attempted; they
do not rank children or predict child results.

### Proposal identity

Each Generation 1 proposal identity is:

```text
d5-proposal:sha256:<digest>
```

The digest is over canonical deterministic JSON containing exactly:

1. schema: `d5_generation1_proposal/1`;
2. plan id;
3. source population id;
4. target generation number;
5. proposal label;
6. sorted parent candidate references;
7. sorted parent Twin references;
8. sorted D3 memory entry identities and entry digests;
9. sorted D1 parent evaluation references;
10. sorted selected slot source records;
11. complete proposed child assignment sorted by slot name;
12. compatibility context id;
13. slot schema id;
14. materialization semantics id;
15. novelty policy id.

Changing the generation identity, source population, D3 provenance,
compatibility context, selected source record, or assignment changes the
proposal identity.

### Candidate and Twin identities

For each compatible accepted proposal:

```text
candidate_id = d5-g1-candidate:sha256:<proposal_digest>
twin_id = d5-g1-twin:sha256:<proposal_digest>
twin version = 1
candidate generation = 1
candidate operator = recombine:d5-memory-informed-v0.1
```

Every child candidate must list the sorted unique parent candidate references.
Every child Twin must be a new `ScientificTwin(kind=DERIVED)` and must carry the
D5 proposal identity and D4 recombination event identity in metadata only as
provenance. Metadata must not enter `scientific_context()`.

D5 must not use a Generation 1 identity that collides with a Generation 0
candidate, a parent Twin, a parent result, or a D4 frozen child artifact.

## Generation 1 exact proposal table

Every selected slot value must match the named parent candidate assignment and
must cite that parent's D3 entry identity/digest and D1 evaluation reference.

| Label | Selected sources | Proposed child assignment | Expected pre-evaluation behavior |
|---|---|---|---|
| `A` | `component_a` from `d4-parent-a`; `component_b` from `d4-parent-b`; `adapter`, `control_level`, `guard_enabled` from `d4-parent-a` | `A_peak`, `B_peak`, `buffered`, `2`, `false` | `INCOMPATIBLE`; no child |
| `B` | `component_a` from `d4-parent-a`; `component_b`, `adapter`, `control_level`, `guard_enabled` from `d4-parent-d` | `A_peak`, `B_filter`, `buffered`, `2`, `true` | `COMPATIBLE`; materialize |
| `C` | `component_a`, `guard_enabled` from `d4-parent-c`; `component_b`, `adapter`, `control_level` from `d4-parent-d` | `A_stable`, `B_filter`, `buffered`, `2`, `true` | `COMPATIBLE`; materialize |
| `D` | `component_a`, `guard_enabled`, `control_level` from `d4-parent-c`; `component_b`, `adapter` from `d4-parent-b` | `A_stable`, `B_peak`, `direct`, `1`, `true` | `COMPATIBLE`; materialize |
| `E` | `component_a` from `d4-parent-a`; `component_b`, `adapter`, `control_level`, `guard_enabled` from `d4-parent-c` | `A_peak`, `B_base`, `direct`, `1`, `true` | `COMPATIBLE`; materialize |

Proposal `E` is the frozen diversity repair proposal. It exists so that the
accepted Generation 1 population remains size `4` after the preregistered
incompatible proposal `A` is rejected. It is not chosen because it is predicted
to perform well.

Generation 1 accepted population size is exactly `4`.

Generation 1 rejected proposal count is exactly `1` under the frozen
compatibility rules.

## Novelty and diversity policy

Novelty is exact assignment novelty:

```text
assignment_digest(Generation 1 candidate)
not in
{assignment_digest(candidate) for candidate in Generation 0}
```

No fuzzy or distance-based novelty exists in D5 V0.1.

Diversity rule:

- the accepted Generation 1 population must contain at least two distinct
  `component_a` values;
- it must contain at least two distinct `component_b` values;
- it must contain at least two distinct parent-pair sets;
- no Generation 1 assignment may duplicate another Generation 1 assignment;
- no Generation 1 assignment may duplicate a Generation 0 assignment.

These are blocking structural rules. They do not assert scientific quality.

## Generation 1 evaluation semantics

Every accepted Generation 1 candidate receives:

- a new candidate identity;
- a new `ScientificTwin(kind=DERIVED)` identity;
- a new D1 `DesignEvaluation`;
- a new `ScientificResult.result_id`;
- a new `ResultBinding` naming the Generation 1 candidate, Generation 1 Twin,
  and D4 synthetic design space;
- objective values computed by the frozen equations above;
- explicit D1 eligibility reason:

```text
preregistered D5 Generation 1 synthetic evaluation
```

Parent `ScientificResult` payloads, parent result ids, parent evaluation ids,
parent target status, parent Pareto/archive status, parent D1 eligibility,
parent evidence refs, parent validation/UQ/model-adequacy fields, and D3
classification labels must not appear in child result values, child result
provenance as evidence, child D1 eligibility, child target assessment, or child
archive membership.

## Comparison metrics

Metrics are computed after both generations have new evaluations under the same
scientific scope. No weighted quality score exists.

Report at minimum:

1. Generation 0 population size.
2. Generation 1 proposal count.
3. Generation 1 accepted/materialized population size.
4. Generation 1 compatibility rejected count by state: `INCOMPATIBLE` and
   `INVALID`.
5. Scientifically evaluated count per generation.
6. Target-pass count and rate per generation.
7. D1 Pareto count per generation under the three objective definitions.
8. Per-objective min/max range per generation.
9. Constraint/compatibility failure count and rate for Generation 1 proposals.
10. Materialized derived candidate count.
11. Duplicate assignment rate within each generation and across generations.
12. Exact novelty count/rate of Generation 1 relative to Generation 0.
13. Count of Generation 1 candidates improving at least one preregistered
    objective strictly relative to every relevant lineage parent, respecting
    objective direction.
14. Count of Generation 1 candidates underperforming at least one relevant
    lineage parent on at least one preregistered objective.
15. Count of attempted parent-result inheritance blocks.
16. Count of attempted target/Pareto/status inheritance blocks.
17. Serialization round-trip byte equality for proposals, compatibility
    records, lineage records, candidates, Twins, evaluations, and comparison
    summary.

Rates use the generation's own scientifically evaluated count as denominator
unless explicitly about Generation 1 proposals, in which case the denominator is
the five-proposal budget.

Generation 1 being worse than Generation 0 on any metric is a scientifically
valid result.

## Success and failure gates

Blocking gates:

- **A1 - Frozen milestone protection:** D0, D1, D2, D3, D4, ScientificTwin,
  MVR0, MVR1, and K-series frozen semantics are unmodified.
- **A2 - Deterministic Generation 0:** the four Generation 0 candidates,
  assignments, Twin references, evaluations, and population membership are
  byte-deterministic and order-invariant.
- **A3 - Exact D3 attribution:** every D3 entry used by a proposal resolves to
  exactly one Generation 0 candidate, Twin, D1 evaluation, and result binding.
- **A4 - Exact D4 attribution:** every selected slot resolves to the named
  parent assignment, parent Twin, parent evaluation, and D3 entry.
- **A5 - Deterministic Generation 1 proposal set:** labels `A` through `E`,
  proposal identities, selected sources, and child assignments are fixed before
  implementation.
- **A6 - Compatibility fail-closed behavior:** proposal `A` is rejected before
  materialization; invalid or forged proposals create no child, Twin, or result.
- **A7 - Deterministic child identities:** accepted child candidate and Twin
  identities are digest-derived, stable, and distinct from Generation 0.
- **A8 - Exact Generation 1 lineage:** child -> proposal -> D4 event ->
  parents -> D3 entries -> compatibility -> materialization -> Twin ->
  evaluation -> result round-trips exactly.
- **A9 - New Twin identity:** every Generation 1 candidate binds a new derived
  Twin, never a parent Twin.
- **A10 - No scientific truth inheritance:** no parent result, target status,
  Pareto/archive status, D1 eligibility, validation, UQ, adequacy, or evidence
  is copied into a child as scientific truth.
- **A11 - Mandatory new evaluation:** every accepted Generation 1 candidate has
  a new D1 evaluation and new ScientificResult before metrics are computed.
- **A12 - No duplicate or identity collision:** duplicates within Generation 1
  and between Generation 0 and Generation 1 fail closed.
- **A13 - Order/process invariance:** insertion order, parent order, process
  restart, and serialization round-trip do not change proposal membership,
  accepted membership, rejected membership, or comparison metrics.
- **A14 - Comparable scientific scope:** direct objective comparison is allowed
  only when both generations use the exact scope frozen above.
- **A15 - Deterministic serialization/round-trip:** all D5 persistent records
  serialize deterministically and round-trip without type or identity loss.
- **A16 - No status inflation:** compatibility, retention, proposal membership,
  materialization, target assessment, and Pareto/archive membership never imply
  feasibility, validation, adequacy, safety, optimality, or truth.
- **A17 - Full regression safety:** targeted D5 tests and the full repository
  regression pass before D5 freeze.

Informative gates/results:

- **A18 - Generation 1 novelty:** Generation 1 produces scientifically new
  candidate identities and assignment-novel candidates relative to Generation 0.
- **A19 - Objective improvement evidence:** at least one Generation 1 candidate
  may improve at least one preregistered objective relative to all relevant
  lineage parents; if none does, record that result without tuning the policy.
- **A20 - Target-pass rate comparison:** Generation 1 target-pass rate may be
  lower, equal, or higher than Generation 0 and must be reported as observed.
- **A21 - Pareto structure comparison:** Generation 1 Pareto structure may
  differ from Generation 0 and must be reported as observed.
- **A22 - Compatibility value:** proposal rejection counts show whether D4
  compatibility avoided materializing scientifically unnecessary or invalid
  proposals.
- **A23 - Core abstraction evidence:** Q8 is answered from implementation and
  adversarial review evidence, not from preference.

"Generation 1 is better" is not a blocking gate.

## Negative and adversarial cases

All cases fail closed unless explicitly marked otherwise.

| Case | Attempt | Expected behavior |
|---|---|---|
| N1 | Generation 1 proposal references nonexistent parent | `INVALID`; no materialization |
| N2 | D3 memory entry identity/digest belongs to a different candidate than the claimed parent | `INVALID`; no materialization |
| N3 | Incompatible `A_peak` + `B_peak` proposal attempts materialization | `INCOMPATIBLE`; no child, Twin, or result |
| N4 | Generation 1 assignment duplicates any Generation 0 assignment | fail closed before population acceptance |
| N5 | Duplicate Generation 1 proposal or candidate identity | fail closed |
| N6 | Same selected sources and assignment under altered generation identity | proposal digest changes; old candidate id cannot be reused |
| N7 | Same candidate assignment is assigned to Generation 0 and Generation 1 inconsistently | fail closed |
| N8 | Parent ScientificResult copied into child result or child evidence | fail closed |
| N9 | Parent target, Pareto, scoped-elite, or selection status copied into child status | fail closed |
| N10 | Compatibility state forged from `INCOMPATIBLE` or `INVALID` to `COMPATIBLE` | fail closed by recomputing compatibility from frozen inputs |
| N11 | Materialized assignments differ from proposed child assignments | fail closed |
| N12 | Proposal insertion/order permutation changes Generation 1 membership | fail closed |
| N13 | Missing proposal, source, compatibility, D3, parent, Twin, evaluation, or result lineage | fail closed |
| N14 | New child ScientificResult lacks attribution to the Generation 1 candidate/Twin/design space | fail closed |
| N15 | Generation 1 comparison mixes incompatible scope, objective definition, unit, model, or solver identity | fail closed and report populations separately |
| N16 | Parent order permutation changes proposal identity when canonical source records are unchanged | fail closed |
| N17 | Child Twin reference equals any parent Twin reference | fail closed |
| N18 | Child result id or evaluation id equals any parent result/evaluation id | fail closed |

## Architectural questions deliberately unresolved

D5 does not pre-decide what belongs in generic Core.

Possibly Core-worthy if the experiment justifies them:

- generic successor generation plan identity;
- generic evidence-informed proposal record;
- generic generation lineage record;
- generic population derivation record;
- generic no-inheritance guard for child scientific results;
- generic relation between D3 memory, D4 derivation records, and D1 populations;
- generic multi-parent ScientificTwin lineage.

Experiment/system-owned unless repeated evidence proves otherwise:

- which D3 observations to exploit;
- which parent slots to combine;
- proposal label ordering;
- diversity repair proposal `E`;
- target thresholds;
- compatibility rules;
- recombination/materialization semantics;
- synthetic objective equations;
- exploration fraction or accepted-population target.

Open empirical questions:

- Does a generic Core `GenerationPlan` add safety beyond existing D1
  `DesignPopulation` plus experiment-owned proposal records?
- Should proposal identity include D3 memory provenance, or should identical
  assignments converge independent of memory lineage?
- Should compatibility rejection records become generic population-generation
  artifacts?
- Is D4's local derivation record enough when lifted to population scale, or is
  a D5-specific generation lineage needed?
- Does ScientificTwin need multi-parent lineage as scientific context, or is
  metadata plus an external lineage record sufficient?
- Should memory-informed proposal policy remain outside Core because selection
  rules are inherently system/study policy?

These questions must be answered by D5 implementation results and adversarial
review, not by rewriting this preregistration.

## Falsifiability check

An independent implementer working only from this document has no remaining
freedom that can materially change:

- Generation 0 population membership;
- Generation 0 assignment table;
- Generation 0 evaluation equations and scope;
- D3 memory scope and policy inputs;
- Generation 1 proposal labels, order, source parents, selected slots, and
  child assignments;
- accepted/rejected proposal membership under compatibility;
- accepted Generation 1 population size;
- novelty and duplicate rules;
- candidate and Twin identity formulas;
- lineage coverage;
- scientific evaluation inputs;
- comparison metric definitions;
- blocking and informative gates;
- adversarial expected behavior.

If an implementation still has freedom to choose good parents, thresholds,
fractions, tie-breaks, novelty rules, overflow behavior, or comparison scope
after observing data, it is not implementing this D5 preregistration.

## Explicitly out of scope

D5 preregistration does not implement:

- D5 source code;
- D4 modifications;
- D3 modifications;
- Core abstractions;
- D6 next-experiment intelligence;
- Bayesian optimization;
- BoTorch;
- surrogate models;
- expected improvement;
- acquisition functions;
- active learning;
- reinforcement learning;
- evolutionary algorithm framework;
- mutation/crossover framework beyond the frozen D4 mechanism;
- autonomous experiment loops;
- LLM orchestration;
- hypothesis generation;
- automatic coefficient tuning;
- multirotor-specific logic.

## Freeze rule

This document is frozen before D5 implementation.

Implementation may not weaken the population definitions, proposal policy,
compatibility rules, identity semantics, novelty rules, lineage requirements,
evaluation equations, comparison metrics, adversarial cases, or gates after
observing Generation 1 results. If the experiment exposes that the
preregistered structure is insufficient, the gap is recorded as D5 evidence or
successor architecture rather than silently editing frozen D0/D1/D2/D3/D4,
ScientificTwin, or this preregistration.
