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

Dimensional agreement is checked by **dimensionality, never by unit string**.
A model declaring `kelvin` accepts a problem in `degC`; `m` and `cm` are
interchangeable; `K` and `V` are not.

## Finiteness policy

`Quantity` refuses NaN and ±Inf. That single invariant keeps non-finite
values out of parameters, bounds, tolerances, results, uncertainties,
provenance and optimizer candidates without a check in each.

The one sanctioned home for non-finite numbers is `RawSolverOutput`: a
diverged backend must be able to report NaN honestly, and forcing an adapter
to hide it would make it lie. The boundary is therefore **raw backend output
may be non-finite; interpreted science may not.** `ObjectiveDefinition.weight`
and `SolverSettings.tolerances` carry their own finiteness checks since they
are plain floats rather than quantities.

## Constraint semantics

For measured `x`, bound `b`, tolerance `τ >= 0`:
`<=` → `x <= b + τ` · `<` → `x < b − τ` · `>=` → `x >= b − τ` ·
`>` → `x > b + τ` · `==` → `|x − b| <= τ`.

Tolerance **relaxes** a non-strict bound and **tightens** a strict one; at
`τ = 0` every operator has its exact mathematical meaning, so `x < b`
correctly fails at `x == b`. Exact equality is permitted — a study may demand
it — though non-zero tolerance is normally right for floating-point results.

## Condition validation: what the core owns

The universal core validates only dimension relationships that are true *by
definition*:

| Condition | Core enforces variable's dimension? |
|---|---|
| `InitialCondition` | **Yes** — it *is* the variable's value at t₀ |
| Dirichlet | **Yes** — it *is* a prescribed field value |
| Neumann | **No** — a derivative/flux, commonly `[variable]/[length]` |
| Robin | **No** — mixed coefficients of several dimensions |
| Periodic / Other | **No** — domain-defined |

Forcing a Neumann flux to match its field would reject correct physics. That
validation belongs to the domain or solver adapter, not here.

## Optimizer boundary policy

`CandidateCodec.encode` rejects a candidate outside its declared physical
bounds; `decode` rejects any component outside `[0, 1]`. Extrapolating past a
declared bound would silently invent a candidate the problem never
authorized. A backend that legitimately proposes just outside a box
constraint calls `clip()` — the explicit, recorded correction path.
`ScientificVariable.require_within_bounds` is named for what it does: it
rejects, it does not clamp.

## Typed scientific values

A parameter is not always dimensional. `ScientificValue` is a small **closed**
union — `Quantity`, `IntegerValue`, `BooleanValue`, `CategoricalValue` — each
schema-tagged and round-trip typed. Adding a kind is a deliberate contract
change, not something a caller can do by passing an arbitrary object.

**Representability is not optimizability.** A categorical parameter can be
declared today; `CandidateCodec` still refuses to encode non-continuous
*design variables*, because every naive encoding silently changes the search
geometry. Model validity context is derived from typed parameters through
`problem.validity_context(extra=...)` — `metadata` is never a side channel.

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
