# Release 1 architecture

This document describes the implemented architecture of Scientific Discovery
Platform — Release 1. AI/LLM orchestration is not part of Release 1.

## Components and ownership

**Stable Scientific Core** owns domain-neutral typed contracts: quantities and
units, scientific values and problems, model/validity records, solver
protocols, validation, uncertainty representation, provenance,
`ScientificResult`, `ScientificTwin`, Study/evaluation records, and
schema-bearing serialization. It does not supply domain equations or decide
what to investigate.

LAB owns scientific execution. It binds a declared scientific task to a
domain/system pack, model, solver or declared analytic execution, conditions,
validation, and provenance. Its evidence product is a complete
`ScientificResult`, optionally bound through `ResultBinding` and
`DesignEvaluation` to an exact design candidate and Twin.

MIND consumes attributable, eligible evidence and chooses or derives a
bounded next inquiry. Public Mind V1 is D3 attributable memory and its
classification/retention operations. The D4/D5/D6/D7 compatibility,
generation, and selection behavior used by the closed-loop demonstration is a
frozen synthetic release reference, not a generic public Mind engine.
MIND does not manufacture scientific truth or evidence.

**Domain/System Packs** own scientific equations, assumptions, units, validity
envelopes, solver tolerances, validation thresholds, objectives, constraints,
and reference-system policies. Release 1 contains proven Electrical DC,
Thermal conduction1d, Kinetics CSTR, rotor-hover, and multirotor paths within
their declared envelopes.

**ScientificTwin** represents one specific versioned system, object, or
candidate, including typed declarations, model references, assumptions, and
attributable evidence references. A `DesignMemoryRecord` is a scoped retention
record over observations; DesignMemory is not a Twin.

## Evidence flow

```text
User / caller
↓
Typed Study
↓
LAB
↓
ScientificResult
↓
ResultBinding
↓
DesignEvaluation
↓
MIND
↓
Memory / Decision / Next Study
↓
LAB
↓
New Evidence
```

The reusable public Study record is `ScientificExperiment`. The D7 reference's
Study-like records remain experiment-local. The Release 1 runner uses a thin,
release-internal typed aggregate to verify the exact Mind-to-Lab handoff; it
does not create a second Public V1 Study contract.

## Boundary invariants

Lab → Mind passes a `DesignCandidate`, eligible `DesignEvaluation`, and
`DesignMemoryScope`. The evaluation contains the full `ScientificResult`; its
provenance contains the exact `ResultBinding`. A result ID or caller-authored
dictionary alone is insufficient.

Mind → Lab passes the selected candidate, its full exact `ScientificTwin`, and
the declared problem/Study execution identity. Decision and prediction
identities remain decision provenance; they are not attached as scientific
evidence.

Candidate, Twin, design-space, Study, model, solver, result binding,
eligibility, and memory scope mismatches fail closed.

## Bounded Release 1 sequence

The closed reference begins with one Generation 0 synthetic Study, executes
Lab, admits attributable evidence to memory, runs the frozen synthetic
compatibility/successor/selection policy, executes one selected Generation 1
Study, returns its new evidence to memory, saves and revalidates the graph, and
stops. Generation 2 is not executed.

This architecture demonstrates one bounded typed integration. It does not
establish autonomous discovery, convergence, physical validation of the D7
cycle, or a production execution/persistence architecture.
