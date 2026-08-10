# D4 - Compatibility / Recombination V0.1 preregistration

Status: **FROZEN BEFORE IMPLEMENTATION**

Starting stable checkpoint: `6abdf279141cf032abdb8052f6ee806c3c264953` (D3 PASS/FROZEN)

## Purpose

D4 tests whether scientifically attributable design memory can motivate a
small, deterministic recombination attempt without confusing compatibility,
lineage, or parent success with child scientific truth.

D4 is preregistration-only at this checkpoint. It must not implement a
compatibility engine, recombination framework, optimizer, genetic algorithm,
surrogate, graph database, UI, LLM workflow, or successor generation policy.

The core principle is:

```text
experiment pulls architecture
```

The experiment asks whether a generic Core abstraction is justified. It does
not assume that one is justified.

## Frozen inspection basis

D4 is preregistered after inspecting the frozen repository at the D3 freeze
checkpoint.

Relevant frozen semantics:

- D0 `DesignCandidate` is an immutable exact assignment set bound to one exact
  `TwinReference`. It can carry parent candidate references and a generation
  number, but a candidate is not evidence, feasibility, validation, adequacy,
  safety, optimality, or truth.
- D1 `DesignEvaluation` binds one exact candidate, one exact Twin, one exact
  design space, and one complete `ScientificResult`. `ResultBinding` is carried
  in result provenance and must match the evaluation identity. Selection
  eligibility is explicit and is not inferred from result usability or archive
  membership.
- D2 generation creates generation-zero candidates only. D2 materialization
  proves internal Proposal -> Candidate -> Twin correspondence, but the
  caller-owned materializer remains responsible for scientific meaning.
- `ScientificTwin` is a versioned scientific system-instance declaration. A
  `TwinKind.DERIVED` exists but frozen Twin V0.1 has only a single `parent`
  reference, so D4 must test whether exact multi-parent derivation lineage
  belongs beside Twin or requires a Core successor.
- D3 memory separates Layer A attributable observations from Layer B retention
  policy. Retention and classification are decision provenance only. They are
  not transferable scientific truth.
- MVR1 showed that study/context attribution matters: internally coherent
  metadata is not enough when scientific conditions change. D4 must therefore
  treat D3 memory entries as attributable selection provenance, not as child
  evidence.
- Existing serialization conventions use schema-versioned deterministic JSON,
  sorted mapping keys, typed scientific values, and explicit fail-closed schema
  checks.

## Critical scientific rule

Parent observations:

```text
Parent A has property X
Parent B has property Y
```

do not imply:

```text
Child(A,B) has X and Y
```

The child is a new scientific object.

The only valid D4 flow is:

```text
D3 attributable parent observations
-> compatibility assessment
-> recombination proposal
-> derived DesignCandidate
-> derived ScientificTwin
-> new scientific evaluation
-> new ScientificResult
```

No parent `ScientificResult`, target status, Pareto membership, validation,
UQ, model adequacy, or evidence may be copied as child evidence.

## Scientific questions

**Q1 - Memory-to-component eligibility.** Can scientifically attributable D3
observations identify exact parent component-slot assignments that are eligible
for recombination without turning D3 retention metadata into scientific truth?

**Q2 - Deterministic compatibility.** Can compatibility be represented
deterministically without the Core knowing domain-specific physical meaning?

**Q3 - Incompatible strong components.** Can individually strong parent
components be rejected before materialization when their preregistered
compatibility relation fails?

**Q4 - Derived candidate identity.** Can compatible components produce a new
deterministic `DesignCandidate` identity with exact parent and assignment
lineage?

**Q5 - Derived Twin boundary.** Can a derived `ScientificTwin` identity/reference
be created without copying parent scientific results, evidence, target pass,
Pareto membership, validation, UQ, or model adequacy?

**Q6 - Interaction effects after re-evaluation.** After new child evaluation,
can the system demonstrate both:

```text
good parent component + good parent component -> poor child
```

and:

```text
partial-success parent component + partial-success parent component
-> improved child on at least one preregistered objective
```

without changing compatibility rules, equations, thresholds, or cases after
observing results?

**Q7 - Identity invariance.** Can recombination identity remain stable across
execution order, process changes, serialization round-trip, and parent order
permutation?

**Q8 - Core boundary.** Does the experiment prove that a generic compatibility
or recombination abstraction belongs in Core, or should semantics remain
system-pack owned?

Q8 is empirical and must remain unresolved before implementation.

## Non-equivalences frozen for D4

Compatibility is not scientific validity.

Compatibility is not target pass.

Compatibility is not good performance.

Compatibility is not model adequacy.

Compatibility is not safety.

Recombination is not optimization.

A derived candidate is not a scientifically successful candidate.

A derived Twin is not a validated Twin.

Parent success is not inherited child success.

## Concrete synthetic experiment

D4 uses a small domain-neutral compositional design space. It does not depend
on multirotor physics.

### Candidate structure

Each candidate has exactly five typed design slots:

| Slot | Type | Values |
|---|---|---|
| `component_a` | categorical | `A_base`, `A_peak`, `A_stable` |
| `component_b` | categorical | `B_base`, `B_peak`, `B_filter` |
| `adapter` | categorical | `direct`, `buffered`, `isolated` |
| `control_level` | integer | `0`, `1`, `2` |
| `guard_enabled` | boolean | `false`, `true` |

These are opaque domain-neutral component slots. D4 must not introduce a vague
generic `Trait` object. The transferable item is exactly one declared
component-slot assignment, or an exact group of slot assignments, copied from
an exact parent candidate.

### Preregistered seed parents

The seed parents are generation-zero D0 candidates evaluated under D1 and then
retained/classified by D3.

| Parent | Assignments | D3 use in D4 |
|---|---|---|
| `d4-parent-a` | `A_peak`, `B_base`, `buffered`, `2`, `false` | `A_peak` is eligible because the parent has a high `yield_score` observation |
| `d4-parent-b` | `A_base`, `B_peak`, `direct`, `0`, `false` | `B_peak` is eligible because the parent has a high `yield_score` observation |
| `d4-parent-c` | `A_stable`, `B_base`, `direct`, `1`, `true` | `A_stable` and `guard_enabled=true` are eligible from a partial-success robustness observation |
| `d4-parent-d` | `A_base`, `B_filter`, `buffered`, `2`, `true` | `B_filter`, `buffered`, and `control_level=2` are eligible from partial-success `loss_score` / robustness observations |

D3 entries motivate the selection. They do not become child evidence.

### Synthetic scientific objectives

Every materialized child must receive a fresh D1 evaluation with a new
`ScientificResult`.

The domain-neutral objectives are:

- `yield_score`, maximize, dimensionless;
- `loss_score`, minimize, dimensionless;
- `stability_score`, maximize, dimensionless.

The target assessment used only for Case D is:

```text
yield_score >= 70
loss_score <= 25
stability_score >= 50
```

Target pass/fail is not D1 eligibility and is not scientific validity.

### Frozen synthetic equations

For any compatible child assignment, compute:

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

These equations are frozen before implementation. They must not be tuned after
observing child results.

### Preregistered recombination cases

| Case | Parent components selected | Expected pre-evaluation behavior | Expected scientific outcome after new child evaluation |
|---|---|---|---|
| A | `A_peak` from `d4-parent-a` + `B_peak` from `d4-parent-b` | incompatible; no child | no child result exists |
| B | `A_peak` from `d4-parent-a` + `B_filter`, `buffered`, `control_level=2`, `guard_enabled=true` from `d4-parent-d` | compatible; child produced | child evaluates poorly because the `A_peak`/`B_filter` interaction penalty dominates |
| C | `A_stable`, `guard_enabled=true` from `d4-parent-c` + `B_filter`, `buffered`, `control_level=2` from `d4-parent-d` | compatible; child produced | child improves at least one preregistered objective relative to both parents |
| D | `A_stable`, `guard_enabled=true` from `d4-parent-c` + `B_peak`, `direct` from `d4-parent-b` + `control_level=1` | compatible; child produced | child has a valid new result but fails overall target |

Case C improvement is an experimental outcome gate only under the frozen
equations. If implementation faithfully applies the frozen equations and no
improvement is observed due to an implementation defect, the defect is fixed.
If a later successor experiment uses different frozen equations and observes no
improved child, that would be valid evidence. D4 V0.1 does not permit tuning
after observation.

## Eligible recombination information

The only information from a parent eligible to participate in recombination is:

- exact parent `DesignCandidateReference`;
- exact parent `TwinReference`;
- exact D3 `DesignMemoryEntry` identity and digest used as decision provenance;
- exact parent D1 evaluation identity referenced by that D3 entry;
- exact typed parent assignment for a declared D4 slot;
- exact source slot name and selected slot value;
- optional exact grouped assignments when the group is preregistered by the
  experiment, such as `adapter` plus `control_level`.

The following are not transferable components and must not be copied into a
child as scientific evidence:

- objective values;
- signed margins or near-extreme distances;
- retention reason labels;
- Pareto/scoped-elite membership;
- target pass/fail;
- `SelectionEligibility`;
- `ScientificResult`;
- validation or model adequacy claims;
- UQ;
- evidence references.

D3 memory is selection provenance only.

## Compatibility semantics

The D4 experiment uses one explicit compatibility context:

```text
compatibility_context_id = d4-synthetic-compat-v0.1
slot_schema_id = d4-synthetic-slots-v0.1
materialization_semantics_id = d4-synthetic-materialization-v0.1
```

Compatibility is evaluated before child materialization and before scientific
evaluation.

Compatibility rules:

1. Every selected slot must exist in the D4 design space and have the declared
   type.
2. Every selected value must equal the value in the named parent candidate's
   assignment for that slot.
3. Every D3 memory entry used as motivation must reference the same parent
   candidate and D1 evaluation claimed by the recombination source record.
4. A source record cannot claim a slot that its parent candidate does not
   contain.
5. The complete recombined assignment must contain exactly the five D4 slots:
   no missing slot and no undeclared extra slot.
6. Pair compatibility is fail-closed:
   - `A_peak` + `B_peak` is incompatible.
   - every other `component_a` + `component_b` pair in the table is
     structurally compatible.
7. Adapter requirements are fail-closed:
   - `A_peak` + `B_filter` requires `adapter=buffered`;
   - `A_stable` + `B_peak` requires `adapter=direct`;
   - `A_stable` + `B_filter` allows `adapter=buffered` or `adapter=isolated`;
   - all other compatible pairs allow any declared adapter.
8. `control_level` must be one of `0`, `1`, `2`.
9. `guard_enabled` must be boolean.
10. Compatibility cannot read child scientific objective values because those
    values do not exist yet.
11. Compatibility cannot create, infer, or copy scientific outputs.

Compatibility result states for the experiment:

- `COMPATIBLE`: all structural, attribution, pair, adapter and type rules pass;
- `INCOMPATIBLE`: a declared compatibility rule rejects the assignment;
- `INVALID`: identity, attribution, missing-object, schema, type or
  materialization-declaration checks fail.

Only `COMPATIBLE` may proceed to materialization.

## Recombination identity semantics

D4 recombination is component-slot keyed, not parent-list ordered.

For this concrete experiment, parent order is **commutative**:

```text
A + B == B + A
```

when the selected source records, assigned slots, values, compatibility
context, and materialization semantics are identical after canonical sorting.

Canonical recombination-event identity is the SHA-256 digest over deterministic
JSON containing exactly:

1. schema: `d4_recombination_event/1`;
2. compatibility context id;
3. slot schema id;
4. materialization semantics id;
5. sorted parent candidate references;
6. sorted parent Twin references;
7. sorted D3 memory entry identities and digests used as decision provenance;
8. sorted selected source records:
   - slot name;
   - selected value encoded as existing `ScientificValue`;
   - source parent candidate reference;
   - source parent Twin reference;
   - source D1 evaluation reference;
   - source D3 entry identity and digest;
9. complete child assignment payload, sorted by slot name;
10. compatibility result payload, including pass/fail state and failed rule ids;
11. child generation number;
12. child operator label `recombine:d4-synthetic-v0.1`.

Child candidate id is:

```text
d4-child:sha256:<recombination-event-digest>
```

The child candidate id therefore changes if parent identities, D3 provenance,
source slot assignments, compatibility context, rule set identity, or
materialization semantics change.

The same structural assignment derived from different parent/D3 provenance is
a different D4 child candidate in this experiment because D4 is testing exact
derivation lineage, not only assignment equality.

Any attempt to supply a child id that disagrees with the digest-derived id must
fail closed as an identity collision attempt.

## Lineage semantics

Every compatible materialized child must have an exact derivation record.

The derivation record must contain:

- child `DesignCandidateReference`;
- child `TwinReference`;
- recombination event identity;
- compatibility context identity and result;
- complete selected assignment sources;
- parent `DesignCandidateReference` records;
- parent `TwinReference` records;
- D3 memory entries used as decision provenance;
- parent D1 evaluation references used by those D3 entries;
- materialization semantics id;
- child assignment digest;
- timestamp-free deterministic serialization.

The child `DesignCandidate` must:

- have generation `1`;
- have parents equal to the sorted unique parent candidate references;
- use operator `recombine:d4-synthetic-v0.1`;
- bind a new child `TwinReference`;
- carry assignments exactly equal to the derivation record's declared child
  assignments.

The child `ScientificTwin` must:

- have a new identity/reference distinct from every parent Twin;
- be materialized from the child assignments;
- carry no parent `ScientificResult`;
- carry no parent evidence refs or calibration evidence refs;
- carry no parent target/Pareto/validation/UQ/model-adequacy status;
- carry deterministic derivation-record identity in metadata only as
  provenance, not as scientific context;
- expose scientific context from its own declarations only.

Frozen Twin V0.1 has only a single `parent` field for `TwinKind.DERIVED`.
D4 must not pretend that this single field is complete multi-parent lineage.
The experiment therefore treats the D4 derivation record as authoritative for
multi-parent lineage. Whether Core should add generic multi-parent Twin lineage
is an architectural question left for Q8.

## Derived evaluation semantics

A child evaluation must be new:

- new `ScientificResult.result_id`;
- new D1 `DesignEvaluation.evaluation_id`;
- new `ResultBinding` matching the child candidate, child Twin and D4 design
  space;
- objective values computed from the frozen D4 synthetic equations;
- explicit D1 eligibility supplied for successfully computed synthetic
  results, independent of target pass.

Parent scientific results must not appear in child result values, provenance
as evidence, eligibility reasons, target status, archive membership, or
assessment output.

## Negative and adversarial cases

All cases are preregistered fail-closed unless explicitly marked otherwise.

| Case | Attempt | Expected behavior |
|---|---|---|
| N1 | Incompatible `A_peak` + `B_peak` | compatibility result `INCOMPATIBLE`; no child candidate, Twin, or result |
| N2 | nonexistent parent candidate id | `INVALID`; no compatibility pass and no materialization |
| N3 | parent identity mismatch between source record and candidate payload | `INVALID`; no child |
| N4 | D3 memory entry references a different candidate than the claimed parent | `INVALID`; no child |
| N5 | component claimed from a parent that does not contain the slot/value | `INVALID`; no child |
| N6 | same assignments under altered compatibility context id | event digest changes; old child id cannot be reused |
| N7 | parent order permutation for the same source records | byte-identical event digest and child id |
| N8 | caller-supplied child id collides with/differs from digest-derived id | fail closed |
| N9 | attempt to attach a parent `ScientificResult` to child evidence/result | fail closed |
| N10 | attempt to copy parent target/Pareto/selection status into child status | fail closed |
| N11 | recombination using invalid or unattributable D3 observation | `INVALID`; no child |
| N12 | materialized child assignments differ from declared recombination assignments | fail closed |
| N13 | child Twin reference equals a parent Twin reference | fail closed |
| N14 | child result `ResultBinding` still names a parent candidate/Twin | fail closed |
| N15 | compatible child fails target but has successful scientific evaluation | allowed; target failure recorded separately |

## Success and failure gates

Blocking gates:

- **A1 - Frozen milestone protection:** D0/D1/D2/D3, Scientific Twin, K-series,
  MVR0 and MVR1 frozen semantics are unmodified.
- **A2 - Domain-neutral Core boundary:** no concrete product/system/domain
  imports or product-specific branches are added to generic Core.
- **A3 - Exact parent attribution:** every selected slot resolves to an exact
  parent candidate, parent Twin, D1 evaluation and D3 memory entry; mismatch
  fails closed.
- **A4 - Deterministic compatibility:** compatibility is explicit,
  preregistered, typed, performance-independent and evaluated before child
  materialization.
- **A5 - Incompatible combinations fail closed:** Case A/N1 creates no child,
  Twin or result.
- **A6 - Deterministic recombination identity:** the same event produces the
  same digest/id across serialization, execution order and process changes.
- **A7 - Exact lineage preservation:** child -> derivation record -> parents ->
  parent Twins -> D3 memory entries -> compatibility assessment ->
  materialization semantics round-trips exactly.
- **A8 - New derived candidate identity:** every compatible child has a new
  candidate id distinct from all parents.
- **A9 - New derived Twin identity:** every compatible child has a new Twin
  reference distinct from all parents.
- **A10 - No parent scientific truth inheritance:** no parent result, evidence,
  target pass, Pareto membership, validation, UQ or model adequacy is copied as
  child evidence.
- **A11 - New child evaluation required:** child scientific claims begin only
  after a new D1 evaluation with a child `ResultBinding`.
- **A12 - Deterministic round-trip:** compatibility records, derivation records,
  derived candidates and derived Twin references serialize deterministically and
  round-trip without identity loss.
- **A13 - Execution/order invariance:** input ordering and parent order
  permutation cannot change event identity except where the source provenance
  itself changes.
- **A16 - No status inflation:** compatibility, recombination and retention do
  not assert feasibility, safety, adequacy, validation, target pass or success.
- **A17 - Full regression safety:** targeted D4 tests and full repository
  regression pass before D4 freeze.

Informative experimental outcome gates:

- **A14 - Parent interaction effect observed:** at least one faithful run shows
  that individually strong parent components are insufficient to predict child
  success.
- **A15 - Compatible-but-poor child observed:** Case B materializes and then
  evaluates worse on at least one preregistered objective because of the frozen
  interaction equation.
- **A18 - Partial-success recombination evidence:** Case C improves at least
  one preregistered objective relative to both source parents under the frozen
  equations.
- **A19 - Compatible target failure observed:** Case D receives a valid child
  result but fails the overall target assessment.
- **A20 - Core abstraction evidence recorded:** Q8 is answered from the
  experiment, not from aesthetics.

If an informative outcome fails despite faithful implementation of frozen
rules, the result is recorded as evidence and D4 must not be retroactively
tuned. Blocking gates are implementation/scientific-contract requirements.

## Architectural questions deliberately left unresolved

D4 does not pre-decide what belongs in generic Core.

Possibly Core-worthy only if the experiment justifies them:

- generic derivation lineage record;
- generic compatibility result representation;
- generic recombination event identity;
- generic derived-candidate relationship;
- generic multi-parent Twin lineage support;
- generic child-result no-inheritance guard.

System-pack or experiment-owned unless evidence proves otherwise:

- what components exist;
- which component pairs are compatible;
- adapter/slot compatibility rules;
- physical interaction semantics;
- synthetic objective equations;
- target thresholds;
- how a child is materialized;
- whether a structurally compatible child is scientifically useful.

Open architecture questions:

- Is `DesignCandidate.parents` sufficient generic lineage for D4, or is a
  richer derivation record required in Core?
- Is frozen `ScientificTwin.parent` too narrow for multi-parent derived Twins?
- Should compatibility be a generic typed result object, or just
  system-owned admission output?
- Should recombination identity include D3 provenance, or should identical
  child assignments converge to one candidate identity independent of memory
  provenance?
- Should D3 memory provide a read API for recombination, or should D4 consume
  deterministic exported Layer A records?
- Is compatibility context identity a generic Core concept or a system-pack
  artifact identity?

These must be answered by the D4 experiment and adversarial review, not by
preference.

## Explicitly out of scope

D4 preregistration does not implement:

- compatibility engine;
- recombination code;
- derived Twin code;
- generation 1 execution;
- D5;
- optimizer;
- genetic or evolutionary algorithm;
- BoTorch or Bayesian optimization;
- surrogate model;
- next-experiment intelligence;
- LLM;
- UI;
- storage/database changes;
- multirotor-specific logic.

## Freeze rule

This document is frozen before D4 implementation.

Implementation may not weaken the compatibility rules, identity semantics,
lineage requirements, equations, target thresholds, cases, or gates after
observing child results. If the experiment exposes that the preregistered
structure is insufficient, the gap is recorded as D4 evidence or successor
architecture rather than silently editing frozen D0/D1/D2/D3 or this
preregistration.
