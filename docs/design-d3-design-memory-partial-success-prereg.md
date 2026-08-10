# D3 — Scientific Design Memory / Partial Success V0.1 preregistration

Status: **FROZEN BEFORE IMPLEMENTATION**

Starting stable checkpoint: `4a5f58408b597beae852c99f0ea4e53201cf99f0` (MVR1 PASS/FROZEN)

## Purpose

Add the smallest domain-neutral layer that can **retain, attribute and re-serve partial scientific success** across evaluations, studies and generations.

Frozen D1 preserves plural success only as exact Pareto membership and scoped elite membership. MVR0 and MVR1 produced direct evidence that this is insufficient for a discovery workflow:

- MVR0 scoped single-objective archives retained exactly one exact extreme member per scope, discarding every near-extreme design;
- MVR0 observed a target dimension (endurance) that did not discriminate at all, so target pass/fail carried almost no retained information;
- MVR1 demonstrated that the *same* candidate can be a target failure under one Study and a target pass under another, because operating conditions change physics while thresholds only assess it.

D3 is therefore about **memory of why a design was interesting**, not about optimization.

D3 is not an optimizer, not an adaptive generation policy, not a recommender, not a surrogate model, not an LLM interpretation layer, and not a scientific validation engine.

## Architectural boundary

D3 may depend on frozen domain-neutral contracts from D0/D1/D2 and the Scientific Core:

- `DesignSpace` / `DesignSpaceReference`;
- `DesignCandidate` / `DesignCandidateReference`;
- `DesignPopulation`;
- `DesignEvaluation`, `ResultBinding`, `SelectionEligibility`;
- objective projection and exact Pareto dominance;
- `ScientificTwin` / `TwinKind`;
- typed `ScientificValue`, `Quantity`, `IntegerValue`, `CategoricalValue`, `BooleanValue`;
- deterministic serialization / scientific errors.

D3 must not import or branch on:

- concrete `engcore.domains` packages;
- any system pack, including the frozen multirotor pack;
- MVR0/MVR1 physics or target semantics;
- SRIA campaign policy;
- a concrete optimizer backend;
- an LLM provider;
- web/API/database frameworks.

The multirotor system pack must remain removable without modifying D3, and D3 must be usable by a kinetics or HVAC pack that never existed at D3 freeze time.

## Relationship to frozen milestones

D0/D1/D2, Scientific Twin, K-series, MVR0 and MVR1 remain **frozen**. D3 must not:

- widen frozen D1 archive semantics in place;
- retrofit retention policy into frozen Pareto/elite archives;
- alter `SelectionEligibility`;
- alter MVR1 Study identity, attribution or the physical consistency gate;
- change what any frozen milestone already recorded as a result.

D3 adds a **new adjacent layer**. Where D3 needs richer retention than frozen D1 offers, it builds a separate memory record referencing frozen D1 objects rather than mutating them.

## Scientific questions

D3 preregisters answers to the following questions, which are open at freeze time:

**Q1 — Is partial success representable domain-neutrally?**
Can "this design was nearly good, in this specific respect, under these specific conditions" be recorded exactly, without the general layer knowing what the respect or the condition physically means?

**Q2 — Is retained partial success attributable?**
Can every retained memory entry be traced back to exactly one attributable D1 evaluation, one candidate, one design space, and (where present) one study context — with no ambiguity about which physics produced it?

**Q3 — Does memory survive changing assessment without lying?**
When thresholds change but physics does not (MVR1 semantics), does a memory entry recorded under one assessment remain truthful, or does it silently become a false claim?

**Q4 — Does memory survive changing physics without conflating?**
When operating conditions change and physics *does* change, does D3 keep the two records distinct rather than merging them into one apparently-comparable population?

**Q5 — Is retention bounded and deterministic?**
Can retention be capped without the discarded/retained split becoming order-dependent or implementation-dependent?

**Q6 — Does memory avoid status inflation?**
Does retention of a near-miss ever get read as feasibility, validation, adequacy, safety, optimality or truth?

**Q7 — What is actually lost by exact-Pareto-only retention?**
Quantitatively, on a frozen reference population: how many scientifically valid, D1-eligible evaluations carrying near-extreme or near-target behavior are discarded by frozen D1 archives alone?

Q7 is the empirical motivation question. Q1–Q6 are the contract questions.

## Scope frozen for D3

### 1. Memory entry

An immutable `DesignMemoryEntry` records:

- exact `DesignCandidateReference`;
- exact `DesignSpaceReference`;
- exact evaluation identity and `ResultBinding` of the single attributable evaluation;
- optional opaque study/context reference;
- the exact typed assignments of the candidate;
- the exact typed objective/metric values retained;
- an explicit retention reason set;
- a deterministic entry digest.

An entry is a **record of a past attributable evaluation**. It is not evidence, not a recommendation, not a prediction, and not a claim about any other design space or condition.

### 2. Retention reason

Retention reasons are explicit, enumerated and domain-neutral. D3 V0.1 freezes exactly these:

- `PARETO_MEMBER` — exact D1 non-dominated membership;
- `SCOPED_ELITE` — exact D1 scoped elite membership;
- `NEAR_EXTREME` — within a caller-declared tolerance of a scoped extreme;
- `NEAR_THRESHOLD` — within a caller-declared tolerance of a caller-declared assessment threshold, on either side;
- `DIVERSITY_REPRESENTATIVE` — retained to cover a caller-declared discrete partition of the design space;
- `EXPLICIT` — retained because the caller explicitly asked, with a non-empty stated reason.

Tolerances and thresholds are **caller-supplied and recorded on the entry**. D3 never invents a tolerance, never defaults one silently, and never interprets what the threshold physically means.

An entry may carry more than one reason. Reasons are recorded, not ranked.

### 3. Memory scope and context separation

A `DesignMemoryScope` declares the exact conditions under which its entries are mutually comparable:

- exact design-space reference;
- exact objective projection identity;
- an opaque context reference (which MVR1-style studies would populate with study identity).

D3 must refuse to compare, dominate-check, or co-retain entries from different scopes.

This is the D3 answer to MVR1's central semantic result: **changed operating conditions produce a different scope; changed thresholds do not.**

### 4. Threshold-independence of recorded physics

A memory entry records the physical/objective values that were evaluated, and separately records the assessment (threshold set, margins, pass/fail) under which it was retained.

Re-assessing a retained entry under a different threshold set must be possible **without re-recording the physics** and without invalidating the original entry.

Assessment is derived and replaceable. Recorded physics is not.

### 5. Bounded deterministic retention

A `RetentionPolicy` declares:

- a finite maximum entry count per scope;
- a deterministic total ordering used to resolve which entries are retained when the cap binds;
- whether exact D1 Pareto members are unconditionally retained.

Retention must be **order-invariant with respect to insertion order**: the same set of candidate evaluations must produce the same retained set regardless of the sequence in which they were offered.

Cap exhaustion must never silently drop an entry that the policy declares unconditionally retained; that condition fails closed.

### 6. No status inflation

Retention means only: *an explicit, caller-declared retention rule matched an attributable evaluation.*

D3 must never describe a retained entry as feasible, validated, adequate, safe, optimal, promising, recommended, or true. Non-retention must never be described as refuted, infeasible or invalid.

### 7. Determinism and persistence

For the same D3 implementation, scope, policy, and offered evaluation set, the retained entry set, entry digests and serialized memory record must be byte-deterministic and round-trip without scientific type loss.

D3 does not claim cross-version cryptographic authenticity of arbitrary caller-supplied objects. Same-reference content mutation of `ScientificTwin` and `DesignSpace` remains **open Core identity/integrity debt inherited from MVR1** and is explicitly out of D3 scope.

## Experiment definition

### E1 — domain-neutral synthetic retention experiment

A synthetic, domain-neutral mixed design space with a deterministic analytic objective set.

- generate `1000` candidates via frozen D2 `halton_v1`;
- evaluate all under frozen D1 into one D3 scope;
- construct the frozen D1 exact Pareto archive and scoped elite archives;
- construct a D3 memory with all six retention reasons enabled and a declared finite cap;
- record: Pareto count, scoped elite count, retained count, retained-but-not-D1-archived count, discarded count.

Primary purpose: answer Q1, Q5, Q7 without any physics.

### E2 — insertion-order invariance experiment

Re-run E1 retention with at least three distinct deterministic permutations of the offered evaluation order, including reverse order.

Primary purpose: answer Q5.

### E3 — assessment-change experiment (physics fixed)

Take the E1 scope unchanged. Apply a second, stricter caller-declared threshold set.

- no physics is recomputed;
- entries are re-assessed;
- original entries remain valid and unmodified;
- `NEAR_THRESHOLD` retention under the new thresholds is computed from recorded values.

Primary purpose: answer Q3 and validate section 4.

### E4 — condition-change experiment (physics changed)

Construct a second scope with a different declared context reference and a genuinely different objective outcome for the same candidates.

- entries from scope 1 and scope 2 must not co-retain;
- cross-scope dominance comparison must fail closed;
- both scopes remain independently attributable.

Primary purpose: answer Q2 and Q4. This is the domain-neutral analogue of the MVR1 Study A / Study B result and must be expressible without importing MVR1.

### E5 — attribution adversarial experiment

Attempt to insert a memory entry whose claimed evaluation identity, candidate reference, or scope does not match its recorded values.

Every such attempt must fail closed.

Primary purpose: answer Q2 under adversarial conditions, using the MVR1 lesson that internally coherent metadata is not sufficient evidence of correct attribution.

### E6 — reference-population evidence run

Execute E1 at the frozen `1000`-candidate scale and record exact counts as the D3 frozen reference numbers, in the same style as the MVR0 1000-candidate outcome.

This produces the quantitative answer to Q7.

## Success / failure gates

### A1 — domain neutrality

D3 contains no concrete domain/system-pack imports and no product-specific branches. Removing every system pack leaves D3 fully testable.

### A2 — frozen milestone protection

D0/D1/D2, Scientific Twin, K-series, MVR0 and MVR1 source semantics are unmodified. D3 references frozen objects; it does not mutate or widen them.

### A3 — exact attribution

Every retained entry resolves to exactly one attributable D1 evaluation with an exact `ResultBinding`, one candidate, one design space and one scope. Mismatched attribution fails closed (E5).

### A4 — representable partial success

All six frozen retention reasons are recordable with exact typed values and caller-declared tolerances/thresholds, with no D3-invented defaults (E1).

### A5 — order invariance

Retention output is identical across all tested insertion permutations (E2).

### A6 — bounded retention fails closed

Cap exhaustion never silently drops unconditionally-retained entries; it raises (E1, E2).

### A7 — assessment/physics separation

Re-assessment under new thresholds changes derived assessment only. Recorded physics and original entry digests are unchanged and remain valid (E3).

### A8 — scope separation

Cross-scope co-retention and cross-scope dominance comparison fail closed (E4).

### A9 — no status inflation

No D3 API, field name, docstring or serialized value asserts feasibility, validation, adequacy, safety, optimality or truth for a retained entry, or refutation for a discarded one.

### A10 — deterministic round-trip

Memory scopes, policies and entries serialize deterministically and round-trip without scientific type loss.

### A11 — quantified retention evidence

E6 produces exact recorded counts for Pareto members, scoped elites, retained entries, retained-but-not-D1-archived entries and discarded evaluations at 1000-candidate scale.

### A12 — regression safety

Targeted D3 tests pass and the full repository regression remains green.

**Failure gate:** any of A1, A2, A3, A5, A6, A8 failing is a blocking D3 failure. A11 producing a retained-but-not-D1-archived count of zero is **not** a failure — it is a valid observed outcome and a successor design signal, and must not trigger retrospective rewriting of the frozen retention rules.

## Unresolved architectural decisions

These are **open at freeze time** and are explicitly not pre-decided by this preregistration. Each must be resolved during D3 implementation and recorded in the D3 freeze record.

**U1 — storage substrate.** Whether D3 memory persists through the existing Core campaign-persistence mechanism, a separate append-only memory record, or remains in-process with deterministic serialization only.

**U2 — entry identity.** Whether the entry digest covers recorded values only, or values plus the retention reasons and declared tolerances. This determines whether re-assessment (E3) can ever change an entry digest.

**U3 — tolerance representation.** Whether `NEAR_EXTREME` / `NEAR_THRESHOLD` tolerances are expressed as absolute typed `Quantity` values, relative fractions, or both — and whether mixing the two in one policy is permitted.

**U4 — diversity partition ownership.** Whether `DIVERSITY_REPRESENTATIVE` partitions are caller-declared opaque keys (D3 stays neutral) or derived by D3 from discrete variable kinds (D3 gains a rule it must then defend).

**U5 — deterministic tie-break ordering.** The exact total ordering used when the retention cap binds, and whether it may reference objective values or must be identity-only to avoid an implicit scalar preference.

**U6 — scope context opacity.** Whether the scope context reference is a fully opaque string (D3 cannot inspect it) or a structured reference. Opaque is safer for neutrality; structured is required if D3 is ever to answer "which contexts has this candidate been seen under".

**U7 — cross-scope query surface.** Whether D3 V0.1 exposes any read path that spans scopes at all, given that A8 forbids comparison. Listing is not comparison, but the boundary needs an explicit decision.

**U8 — relationship to future adaptive generation.** Whether D3 exposes a read interface shaped for a future generation policy to consume, or deliberately exposes none in V0.1 to avoid pre-committing to an optimizer contract.

## Explicitly deferred

Successor milestones, not D3 V0.1 acceptance requirements:

- adaptive or memory-directed candidate generation;
- Bayesian / evolutionary / mixed-variable optimization;
- surrogate models trained on memory;
- novelty search;
- multi-fidelity promotion policy;
- uncertainty-directed retention;
- cross-design-space transfer or analogy;
- LLM interpretation of retained entries;
- Generation 1 lineage semantics;
- SRIA integration;
- Core identity/integrity content hashing for `ScientificTwin` and `DesignSpace` (inherited MVR1 debt);
- `O(N^2)` archive/Pareto scaling work (inherited MVR0/MVR1 P3);
- any concrete system pack integration, including multirotor.

## Failure policy

If a concrete system pack later reveals a missing retention concept, add it through a successor milestone.

Do not insert domain-specific retention reasons, tolerances or scope rules into D3 after observing a concrete product implementation, and do not rewrite this preregistration after observing D3 experiment results.
