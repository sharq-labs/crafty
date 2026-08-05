# Scientific Core V0 — Foundation

> **We do not reinvent decades of validated scientific work, and we do not
> reduce our platform to a thin wrapper around existing packages.**

That sentence is the design constraint this package exists to satisfy. Both
halves bind. We will not rewrite RK45, LAPACK or a finite-element assembler;
we will also not hand a user a number produced by someone else's library with
no unit, no model identity, no validity statement and no provenance.

## Status

**V0 foundation — contracts only.** No physical domain is implemented: no
Ohm's law, no Newtonian mechanics, no thermal or chemical model, no CFD, no
FEA, no mesh, no multiphysics coupling. The next phase (Domain Validation)
adds Electrical DC and Motion/ODE **through these same contracts**.

## Purpose

Give every future scientific domain one vocabulary for: what is being asked,
what model answers it, when that model is valid, which solver ran, what came
back, how well it was checked, how uncertain it is, and where it came from.

## Architecture

```
Scientific Core          contracts, IR, validity, results, provenance
        |
Domain Models            electrical, thermal, mechanics, chemistry (later)
        |
Solver Adapters          adapters satisfying ScientificSolver (later)
        |
Scientific Libraries     SciPy, SUNDIALS, FEniCSx, Cantera, ngspice, ...
```

```
Scientific Core          ScientificProblem / Quantity / ScientificResult
        |
Experiment Engine        ScientificExperiment, ScientificEvaluation
        |
Optimizer Adapter        CandidateCodec + ObjectiveEncoder  <- the ONE
        |                                                      translation
Optimization Backends    existing stacked_v0301 / adaptive_stacked_v034
```

The optimizer boundary is deliberately one-directional. The core defines
`NumericSearchBackend` as a protocol and **never imports a concrete
optimizer**; a test enforces this. Search sees normalized `[0,1]^d` vectors
and unitless scores. The scientific layer sees units, always.

## Dependency direction

```
units / results / provenance      (foundational services)
        ^
Scientific IR
        ^
Models
        ^
Solver contracts
        ^
Experiments
        ^
Platform / application layer
```

Nothing in `engcore.scientific` may import a web framework, an API layer, a
database, a visualization frontend, an LLM gateway, the optimizer research
stack, or a benchmark suite. Three guardrail tests enforce this by scanning
the package's own import statements.

## What the Scientific Core owns

Scientific IR (`ir/`) · units contract (`units/`) · model representation and
validity (`models/`) · solver orchestration contracts (`solvers/`) ·
validation semantics, uncertainty, provenance and the result record
(`results/`) · experiment representation and the optimizer boundary
(`experiments/`) · the error taxonomy and deterministic serialization.

## What external packages own

Numerical algorithms and their correctness: integration, linear algebra, root
finding, meshing, discretization, chemical equilibrium, circuit simulation.
Also the unit algebra itself — Pint is the units backend behind our
`Quantity` contract, chosen so the backend stays replaceable and never leaks
into a scientific record.

## AI independence

`engcore.scientific` imports no LLM provider and never will. If every AI
provider disappeared tomorrow, the Scientific Core would remain fully usable.
AI may later propose problems, models or candidates; it never computes,
validates or accepts a result. Deterministic scientific systems do that.

## Validation philosophy

1. **Numerical convergence is not scientific validity.** They are separate
   fields on a result and separate levels in a report.
2. **Checks coexist; the level is derived.** `ValidationReport` holds checks;
   an attained `ValidationLevel` must be *backed by a passing check that
   declares it*. `require_level` raises otherwise, and a hand-edited record
   claiming an unearned level is rejected on load.
3. **`NOT_RUN` is not `PASS`.** A check that never ran contributes no
   evidence. No result may claim validation that was not performed.
4. **A model states when it is valid.** `ValidityDomain` yields `IN_DOMAIN`,
   `OUTSIDE_VALIDATED_DOMAIN` or `UNKNOWN` — and an *empty* domain is
   `UNKNOWN`, because absence of declared limits is not evidence of unlimited
   validity.
5. **Uncertainty is never invented.** `UncertaintyKind.UNKNOWN` is the honest
   default; a quantified uncertainty must name the method that produced it.

## Provenance philosophy

Every `ScientificResult` requires a `ProvenanceRecord`: a number that cannot
be attributed is not a scientific result. The record carries run id, software
version, git commit, model and solver identities with versions, unit-carrying
inputs, assumptions, tolerances, environment, timestamp and parent run.

The core **collects nothing on its own**. Every environment fact is supplied
by the caller — auto-harvesting machine identity would be both a privacy
problem and a determinism problem. Serialization is deterministic: identical
inputs produce byte-identical JSON.

## Units policy

Scientific input and output preserve units, always. Numerical kernels may
receive plain arrays — through an adapter, via `Quantity.magnitude_in(unit)`
or `CandidateCodec`, which are the only sanctioned exits from the unit-aware
world. A bare number is never silently interpreted: `Quantity.parse("42")`
raises rather than assume dimensionless.

## Extension path for a new domain

1. Define `ScientificModelDefinition`s with required variables, assumptions,
   a `ValidityDomain` and provided metrics; register them in a
   `ModelRegistry` instance (no global singleton exists).
2. Declare domain capabilities as `SolverCapability("domain:name")` — the
   identifier is extensible, so no core change is needed.
3. Implement a solver adapter satisfying `ScientificSolver`
   (`supports/prepare/solve/validate/extract_metrics`) over a mature library.
4. Express studies as `ScientificProblem` + `ScientificExperiment`. Reuse
   `OptimizerAdapter` to drive any search backend.

Nothing in steps 1–4 requires editing the Scientific Core.

## Deliberately deferred

Symbolic/expression constraints; mixed-variable encoding (integer,
categorical, boolean are *representable* but not encodable in V0); PDE
machinery beyond generic condition types; a UQ engine; persistence and
databases; distributed scheduling; an AI planner; RAG; visualization.
