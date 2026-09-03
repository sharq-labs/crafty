# HOSTILE CORE / DOMAIN STRESS PROOF — Preregistration

**Milestone:** `HOSTILE-CORE-STRESS` — attack the current Crafty scientific
architecture with a scientifically different PDE/transport consumer and
**measure** which abstractions are genuinely missing.
**Kind:** discovery / falsification. It is **not** `FLUID0`, not `FIELD0`, not
`TOPO0`, not `DISC0`, not `EQIR0`, not a generic PDE runtime, not a mesh
framework, not API/MCP work.
**Decision status target:** none. This milestone freezes no design.
**Evidence target:** `L0 REASONED` + **measured gaps** for the distinctions it
attacks; at most `L1 EXERCISED` for the probe pack's own executed behaviour.
`L2` and `L3` are excluded outright. See §14.
**Date:** 2026-09-03
**Branch:** `hostile-core-domain-stress`
**Preregistered before implementation.** Everything below was written before any
source file was added or edited on this branch. The working tree was verified
clean at `03c30f6` (`Admit provider power only when independently reconciled`).

> **This file is immutable.** It records what was committed to *before* results
> were observed. Executed results, deviations, corrections, adversarial findings
> and the final classification go in
> `docs/hostile-core-domain-stress-evidence.md` and nowhere else.
>
> This is **not** a freeze document, and it authorizes no production
> architecture.

**Canonical milestones verified present before this document was written:**

| Milestone | Decision | Evidence | Record |
|---|---|---|---|
| `DATA-BOUNDARY0` | `PROPOSED` | `L1 EXERCISED` | master context §56 |
| `MODEL0-R` differential | `DESIGN-FROZEN` | `L2 DIFFERENTIATED` (scoped) | master context §58 |
| `MIN-FOUNDATION-ET` | `PROPOSED` | `L1 EXERCISED` / `L0` deferrals | master context §64 |
| `ET-VERTICAL` | `PROPOSED` | `L1 EXERCISED`; several claims `L0` | master context §65 |
| `HETERO-NGSPICE` | `PROPOSED` | `L1 EXERCISED`; scoped `L2` **withdrawn** | master context §66 |

**Roadmap deviation, recorded rather than assumed.** `CRAFTY_MASTER_CONTEXT.md`
§61 places `API / MCP v0` next and a cross-architecture hostile proof after it.
This milestone runs the hostile proof **first**. §61 self-describes as "a
risk-driven roadmap, not a frozen sequence", and §54.2 states work packages are
pulled by a proof rather than pushed by a layer map, so this is a reordering the
recorded strategy permits. It is a reordering nonetheless, and it is stated here
so no later reader has to reconstruct it.

---

# 1. The single question

> Can the current Crafty scientific architecture **represent and plan** a
> materially different PDE/transport consumer without domain-specific branches
> in universal core, untyped metadata, abused scalar `Quantity` semantics,
> confusion of field identity with bulk-data transport, boundary/topology
> semantics hidden in strings, duplicated `ScientificProblem` /
> `ScientificTwin` authority, or solver/provider semantics invented at the
> wrong layer?

**If not:** identify the **smallest expensive-to-reverse boundaries** that the
next real Fluid/PDE consumer will force — and do **not** implement them here.

The measurement is a **count**, reproducing the instrument that made
`MIN-FOUNDATION-ET` lose its null hypothesis "on a measurement, not an
argument" (§64.1). Narrative is not the deliverable.

---

# 2. Reviewer verdict, and the consumer selected

`architecture-decision-reviewer` was invoked before this document was written,
on the question *"what is the cheapest scientifically different consumer that
maximizes architecture information before FLUID/PDE v0?"*, against candidates
**A** (lumped pressure-driven pipe/network flow), **B** (1D transient
advection-diffusion), **C** (minimal incompressible 2D Navier-Stokes skeleton),
plus **D** (2D scalar transport in a prescribed velocity field) and **E**
(defer), which the reviewer proposed.

**Verdict: `ACCEPT WITH CHANGES`.** Selected: **B**, adopted in the reviewer's
modified form **B′** — B at a frozen configuration with a preregistered
recoverability instrument. The four required changes are carried into §4, §6,
§7 and §8 below and are not optional.

## 2.1 Why A lost

A lumped pressure-driven pipe network is **structurally isomorphic to the
existing `electrical/dc` MNA domain** — potential ↔ pressure, branch flow ↔
current, conductance ↔ inverse hydraulic resistance, KCL ↔ mass conservation,
reference node ↔ datum pressure. Every pressure it would apply (graph topology,
source-vs-flow boundaries, a symmetric linear solve) is **already exercised**,
and exercised through a domain that has additionally been run by a foreign
provider under `HETERO-NGSPICE`. The milestone brief scores difference against
thermal diffusion; scored against the *whole repository*, A differences against
nothing.

## 2.2 Why C lost

C confounds six architectural pressures simultaneously — field rank, 2D
topology, saddle-point/DAE structure, nonlinearity, multiple coupled unknowns,
a real BC family — so a representation failure could not be attributed to a
cause. Confounding is a **cost** in a discovery milestone, not a benefit. It is
additionally on the explicit do-not-build list twice
(`07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md` §21; `CRAFTY_MASTER_CONTEXT.md` §39.2
and §42), and a wrong NS skeleton would contaminate every conclusion drawn
from it.

## 2.3 Why D lost, and it lost narrowly

D (2D scalar transport in a prescribed divergence-free velocity field) is a
genuine competitor: it adds a vector-valued quantity, 2D multi-region
boundaries, and a **field-valued model input**, which has no home in
`ModelInputSpec.unit_exemplar` or `ScientificParameter.value`. It is rejected
on one judgement, recorded here as a judgement and not as a measurement:

> D's additional pressures target concepts the repository **already records as
> deliberately deferred at `L0`** (`docs/scientific-core/README.md`
> "Deliberately deferred"; §57). B′ targets records that **exist, are
> exercised nowhere, and are frozen**. Probing an exercised-never record yields
> more new information per unit cost than re-confirming a recorded deferral.

D costs roughly 3–5× B′. If a later reader judges that FLUID/PDE v0's
*representational* risk dominates its *semantic* risk, D is the correct next
probe and this milestone under-scoped. That reversal condition is preregistered
here so it can be checked rather than argued.

## 2.4 Why E (defer) lost

E follows §61 as written and is not absurd. It is rejected because it defers
the risk rather than removing it: FLUID/PDE v0 would then design its boundary,
orientation and discretization contracts with the assumptions in §8 still
`L0 REASONED` and unconfronted.

---

# 3. Measured baseline facts

Read directly from this working tree at `03c30f6`, before any file was written.
These are **facts**, not predictions, and the hypotheses in §5 are stated
against them.

| # | Fact | Location |
|---|---|---|
| **B1** | **No domain pack anywhere constructs a `BoundaryCondition`.** `BoundaryCondition`/`BoundaryKind` appear in exactly 4 files under `src/engcore/scientific/` and 2 test files. Zero producers in `src/engcore/domains/`. | `grep -rn 'BoundaryCondition(' src/ \| grep -v scientific/` returns nothing |
| **B2** | `InitialCondition` is constructed in exactly **one** domain file. | `src/engcore/domains/thermal_lumped.py:509` |
| **B3** | The repository's **only transient PDE problem declares no initial condition**: `build_conduction_problem` emits none, and carries `u(x,0) = sin(pi x / L)` as a `metadata` string. | `src/engcore/domains/thermal/conduction1d/problem.py` |
| **B4** | Consequently `ScientificProblem.is_time_dependent`, which is derived from `initial_conditions` being non-empty, returns **False for a transient PDE**. | `src/engcore/scientific/ir/problem.py:333` |
| **B5** | The 1D conduction field `u` reaches the universal IR only as **two scalar `OBSERVABLE` variables**, `u:midpoint` and `u:max_abs`. There is no field object. | `problem.py`, `build_conduction_problem` |
| **B6** | Boundary conditions for that domain live as the metadata string `"u(0,t) = u(L,t) = 0"` and inside a Python-level `fingerprint()`. | `problem.py` |
| **B7** | `n_cells` / `n_steps` are carried as **metadata strings**. | `problem.py`, `build_conduction_problem` |
| **B8** | Discretization identity is an **untyped string in `SolverSettings.options`**: `"space_discretization": "central_difference_2nd_order"`. | `.../conduction1d/solver.py:154-156`, `:395` |
| **B9** | `ProvenanceRecord.tolerances` is `Mapping[str, float]`, so a discretization *name* structurally cannot travel in it; it reaches a record only via untyped `metadata`. | `src/engcore/scientific/results/provenance.py:169` |
| **B10** | `ScientificProblem.validity_context(extra=…)` is built at **call time** from typed parameters plus a caller-supplied mapping, and `to_dict()` does **not** serialize it. | `ir/problem.py:312`, `:338` |
| **B11** | `BoundaryCondition.region` is documented as *"an opaque label owned by the domain (a mesh tag, a port name, a surface id). The core does not interpret it."* | `ir/conditions.py` |
| **B12** | The core enforces the variable's dimension for `InitialCondition` and **Dirichlet only**; Neumann, Robin, Periodic and Other are explicitly unchecked. | `ir/problem.py::_require_condition_dimensions` |
| **B13** | `Quantity.magnitude` is a single `float`, refused if non-finite. The `ScientificValue` union is closed at `Quantity | IntegerValue | BooleanValue | CategoricalValue`. | `units/quantity.py`, `ir/values.py` |
| **B14** | `ScientificDataReference` carries `name, unit, count, dtype, digest` and **deliberately no shape, support, topology, frame, tensor rank or time level**. `count` is documented as *"not a shape"*. | `results/data_reference.py` |
| **B15** | `QuantityDependency` **deliberately refuses to consult `data_references`**, because *"nothing in this record can state how a field is transported between two supports"*. | `composition/dependency.py` |
| **B16** | `ModelRealizationDefinition` has a single `model` field; `HETERO-NGSPICE` §66.3 already recorded it cannot state a joint realization. | `realizations/definition.py:265` |
| **B17** | `ValidityDomain` conditions are evaluated against a **static** context; there is no state-dependent applicability mechanism. | `models/definition.py` |
| **B18** | `conduction1d`'s `validation_requirements` are `dimensional_consistency`, `linear_system_residual`, `boundary_conditions_held`, `field_finite`, `amplitude_decay`. **No boundedness or physical-admissible-range concept exists anywhere.** | `problem.py` |

---

# 4. The frozen consumer — B′

**1D transient advection-diffusion of a normalized scalar.**

```text
∂c/∂t + u ∂c/∂x = D ∂²c/∂x²        x ∈ [0, L],  t ∈ [0, t_end]
```

`c` is **dimensionless and normalized**, following `conduction1d`'s explicit
refusal of an absolute scale — calling it a concentration in mol/m³ would imply
a species, a reference state and a solvent this probe does not have. `u` carries
`meter/second` and is **strictly positive**, so "upstream" is unambiguous by
construction and any failure to recover it is a failure of the *records*, not of
the physics. `D` carries `m**2/s`. The spatial/temporal declaration mirrors
`conduction1d` (`length`, even `n_cells ≥ 2`, `n_steps ≥ 1`) so that the
difference against the baseline is **controlled**: only the operator and the
boundaries change.

Three cases are frozen. Two execute; one is representation-only.

## CASE S — steady, Dirichlet–Dirichlet, exact closed form

```text
u dc/dx = D d²c/dx²        c(0) = 1,  c(L) = 0
c(x) = (exp(Pe·x/L) − exp(Pe)) / (1 − exp(Pe)),      Pe = uL/D
```

Run at fixed `Pe = 40` with `n_cells ∈ {8, 16, 40, 80, 160}`, giving
`Pe_cell = u·dx/D ∈ {5, 2.5, 1, 0.5, 0.25}` — straddling `Pe_cell = 2`.

CASE S has **no initial condition**: its state is fixed entirely by Dirichlet
boundaries. This is deliberate; see §8, prediction **P6**.

## CASE T — transient, asymmetric boundaries

```text
∂c/∂t + u ∂c/∂x = D ∂²c/∂x²
c(x,0) = 0                 (initial condition)
c(0,t) = 1                 (Dirichlet — inflow)
∂c/∂x|_{x=L} = 0           (homogeneous Neumann — outflow)
```

Backward Euler in time, identical to `conduction1d`, so **time integration is
held constant** against the baseline.

Reference: the Ogata–Banks semi-infinite solution

```text
c(x,t) = ½[ erfc((x − ut)/(2√(Dt))) + exp(ux/D)·erfc((x + ut)/(2√(Dt))) ]
```

with `t_end` frozen so that `u·t_end + 4√(D·t_end) ≤ 0.5·L`, keeping the front
and its diffusive spread far from the outflow boundary.

**Recorded honestly, because it is a concession:** `conduction1d`'s docstring
deliberately chose a single Fourier mode so the reference carried *no*
approximation of its own. The Ogata–Banks form is a **semi-infinite** solution
used on a finite domain, so the window above is an assumption **of the
reference, not of the solver**. The evidence document must state the measured
reference-validity margin and must not present agreement outside that window as
verification.

## CASE N — representation only, executes nothing

`D = 0`. The PDE degenerates to first order and **exactly one** boundary
condition is well posed, so CASE T's boundary set becomes an over-specification.
Cost: one extra record set, **zero solves**.

CASE N exists to defeat a specific falsifier attack — see §11, Attack 2.

## Two discretizations, both required

* **CD** — 2nd-order central differencing of the advection term.
* **UW** — 1st-order upwind differencing of the advection term.

Diffusion stays central in both. The difference is a handful of lines and it is
what makes the boundedness measurement in §8 **P7** possible at all.

---

# 5. Hypotheses

## H1 — primary

> The current Crafty contracts are **sufficient, or nearly sufficient**, to
> express the selected hostile consumer without introducing a large new
> universal foundation.

H1 is supported if every recoverability count in §7 returns exactly **1** with
no reliance on metadata convention or source-code reading.

## H0 — null, and it is allowed and expected to win partially

> The hostile consumer exposes one or more currently missing semantic
> distinctions that **cannot be safely represented** using existing contracts.

Candidate forced distinctions, none of which is assumed to exist:

```text
Scientific Field         !=  bulk ScientificDataReference
Field                    !=  Discrete Field Representation
Field Support            !=  Topology
Topology                 !=  Mesh
Boundary Identity        !=  Boundary Condition
Equation/PDE meaning     !=  Discretization
State variable           !=  solution array
```

**A partial H0 win is the expected outcome and is not a failure of the
milestone.** A milestone that reports H1 unqualified after a probe designed to
break it should be read as having probed too gently.

---

# 6. Steelman requirement — no gap may be declared before a maximal honest attempt

This is reviewer Change 2 and it is **binding**. Before anything is reported
unrecoverable, the probe must first express the consumer as well as the existing
typed contracts allow:

* real `InitialCondition` records (CASE T), not metadata strings;
* real `BoundaryCondition(kind=DIRICHLET, region=…, value=Quantity(1.0, "dimensionless"))`
  and `BoundaryCondition(kind=NEUMANN, region=…, value=Quantity(0.0, "dimensionless/meter"))`;
* `u`, `D`, `L`, `t_end` as typed `ScientificParameter`s — **not** metadata;
* `validity_context(extra={"peclet_cell": …})` actually populated;
* **separate** `ModelRealizationDefinition` records for CD and UW.

Without this, every finding is answerable with *"you never tried"* — and B6/B7
above make that objection live and correct, because the existing PDE domain took
the metadata route.

**Any place where the steelman encoding succeeds is a win for H1 and must be
reported as one**, with the same prominence as a gap.

---

# 7. The instrument — a records-only reader, and a count

Reproducing `MIN-FOUNDATION-ET` §64.1. The probe serializes its records
(`to_dict()` → JSON), and a reader is handed **only the serialized payloads**.
The reader:

* may **not** import the probe pack;
* may **not** read domain source code;
* may read universal core contracts, because a records reader legitimately
  knows the schema it is reading.

For each question the reader reports the number of **admissible readings**.

| # | Question | Gap iff |
|---|---|---|
| **R1** | Which boundary is upstream (inflow) and which is downstream (outflow)? | count ≠ 1 |
| **R2** | Which advection scheme produced this result, and is it the bounded one? | count ≠ 1 |
| **R3** | Is this problem transient? | `is_time_dependent` disagrees with the physics |
| **R4** | Is the declared boundary set well posed for the declared parameters? (CASE T vs CASE N) | count ≠ 1, or "not detectable at all" |
| **R5** | Recompute the model's validity verdict from records alone. | `Pe_cell` not reconstructible |

Additionally, the twelve recoverability questions from the milestone brief are
answered for the steelman encoding and classified into exactly one of five
buckets each — **fully recoverable / ambiguous / impossible / recoverable only
via metadata or string convention / recoverable only by reading source code**:

1. what the dependent scientific quantity is;
2. whether it is scalar or spatially distributed;
3. its physical unit;
4. what spatial entity it is defined over;
5. what its initial state means;
6. what its boundary conditions are;
7. which boundary is inflow vs outflow;
8. which model/equation governs it;
9. what the transport direction means;
10. what solver capability is required;
11. whether the field representation is independent of storage location;
12. whether the same scientific field could later have two discretizations.

**This matrix is the central measurement of the milestone.**

---

# 8. Predictions, stated so the milestone can lose

Preregistered before execution. Each may fail, and a failure is a clean negative
result to be reported as such.

| # | Prediction | Basis |
|---|---|---|
| **P1** | **R1 ≥ 2.** A records-only reader cannot determine which boundary is upstream. | B11: `region` is documented opaque; recovering direction would require *parsing a region name*, which `composition/dependency.py` explicitly forbids. |
| **P2** | **R3 disagrees for the existing conduction problem**: `is_time_dependent` is `False` for a transient PDE. | B3, B4. A **pre-existing measured defect this probe surfaces rather than creates.** |
| **P3** | **R2 > 1.** The advection scheme is not recoverable from records. | B8, B9: an untyped `SolverSettings.options` string that cannot reach `ProvenanceRecord.tolerances`; `ModelFormulation` is `PDE` for both CD and UW. |
| **P4** | **R4 is "not detectable at all."** | Nothing states how many conditions the declared model requires; `ModelInputSpec` enumerates parameters, not conditions. |
| **P5** | **R5 not reconstructible.** `Pe_cell` cannot be recomputed from serialized records. | B7, B10: `n_cells` is a metadata string, `validity_context` `extra` is call-time and unserialized, and the core states validity context is *deliberately not sourced from metadata*. |
| **P6** | CASE S — steady, no initial condition, state fixed by Dirichlet — is **correctly** reported by `unresolved_inputs`/`externally_imposed` as needing no external supplier. | `MIN-FOUNDATION-ET` repaired exactly this leak. **This prediction expects existing core to pass**, and is included to hunt a fourth instance of the class of structural assumption three consecutive milestones have each found. |
| **P7** | CD at `Pe_cell = 5` produces `c(x) < 0` while the linear solve reports success at round-off residual, and **every check the platform currently runs passes**. | B18: no boundedness or admissible-range concept exists. |
| **P8** | The solved field is again 1-D contiguous float64, so `ScientificDataReference` carries it without strain — and therefore **DATA-BOUNDARY0 gains nothing and none is claimed**. | B14. |

**If every count comes back 1, H1 survives a genuinely different consumer and
this milestone reports that outcome without hedging.**

---

# 9. What is forbidden in this milestone

Absolute. Violating any of these invalidates the evidence.

1. **No new universal contract** is added to `src/engcore/scientific/`. Not
   `FieldDefinition`, not `FieldSupport`, not `Topology`, not
   `BoundaryDefinition`, not `DiscretizationDefinition`, not `Mesh`, not
   `VectorQuantity`, not `FieldState`.
2. **No existing universal contract is modified** to make a probe pass. In
   particular: no shape/support/topology field is added to
   `ScientificDataReference`; `Quantity` is not generalized to hold arrays,
   vectors or tensors; `QuantityDependency` is not extended to field endpoints.
3. **No `src/engcore/domains/thermal/` file is added or edited.** That tree is
   pinned byte-for-byte by frozen T1/T2/T3 experiment digests and by
   `test_every_thermal_source_file_is_pinned`, which asserts *set equality*;
   there is no sanctioned unfreeze path (§57.1).
4. **No domain-specific branch in universal core**, lexical or structural.
5. **No mesh framework, no CFD solver, no generic PDE runtime, no boundary
   system.**
6. **No `MODEL0-R` evidence movement is claimed** from CD/UW being two
   realizations of one model. `HETERO-NGSPICE` §66.3 withdrew exactly such a
   claim because the differentiating record existed only inside the test. Same
   trap, same answer.
7. **No new evidence level is invented.** The ladder is `L0`–`L3` and
   `PROPOSED` / `DESIGN-FROZEN` / `SUPERSEDED`.
8. **No fluid↔thermal coupling is implemented.** §15 of the brief is analysis
   only: no `QuantityDependency` record, no second problem, no coupling runtime.

---

# 10. Reduction attack — required, before any candidate is promoted

For **each** candidate abstraction below, the evidence document must ask
whether it can be avoided using existing typed contracts **without** semantic
ambiguity, metadata, duplicated identity, source-code interpretation, storage
leakage or discretization leakage:

```text
FieldDefinition   FieldSupport   Topology   BoundaryDefinition
BoundaryCondition(new)   DiscretizationDefinition   Mesh
VectorQuantity   FieldState
```

Each is classified **exactly once** as `FORCED` / `LIKELY-FORCED` / `DEFER` /
`REJECT`. **Only `FORCED` candidates enter the next milestone's design input,
and none is implemented here.**

## 10.1 The two-ledger rule — binding

This is reviewer Change 1's mitigation and the milestone's principal defence
against overclaiming. Findings are split **before** publication:

* **Ledger 1 — findings about a record that EXISTS**: `BoundaryCondition`,
  `ValidityDomain` / `validity_context`, `is_time_dependent`,
  `SolverSettings.options`, `ValidationReport` semantics,
  `ModelRealizationDefinition`. These are **new information**.
* **Ledger 2 — findings about a record that DOES NOT EXIST**: field, support,
  frame, topology, tensor rank. These **re-confirm an already-recorded `L0`
  deferral** (`docs/scientific-core/README.md` "Deliberately deferred"; §57)
  and are booked at **zero claimed evidence gain**.

Blending the two ledgers is how this milestone would overclaim, and doing so is
a fail condition (§13).

---

# 11. Anticipated falsifier attacks, and the answers prepared in advance

`architecture-falsifier` will be invoked after the probes with the primary
challenge: *"prove the proposed gaps are artifacts of the chosen fluid example
rather than genuinely universal scientific distinctions."* Three lines are
expected and are pre-answered so the answers cannot be invented after the fact.

**Attack 1 — "1D is the artifact."** Every orientation and support gap
dissolves once topology exists; the probe measured the absence of
`TOPO0`/`FIELD0`, which the repository already records as deferred.
**This attack lands and partly succeeds.** Answer: the two-ledger rule (§10.1).

**Attack 2 — "the outflow BC is your modelling choice."** A competent author
would have used Dirichlet at both ends and the asymmetry vanishes. Answer:
**CASE N** makes the asymmetry a property of the *equation type*, not of the
author — at `D = 0` the number of well-posed boundary conditions changes with a
*parameter value*, and no modelling taste negotiates that. Reinforced by one
narrow checkable external fact: OpenFOAM ships `inletOutlet`, a boundary
condition whose **kind is selected by the sign of the flux across the patch** —
a shape a frozen `(kind, region, value)` record structurally cannot hold. Cited
as one fact about one shipped BC, **not** as a vote from three FVM-lineage
projects.

**Attack 3 — "the discretization finding is a solver bug, not an architecture
gap."** Central differencing oscillating above `Pe_cell = 2` is textbook, and
`assumptions` free text can record it today. **This is the strongest attack.**
Answer: claim exactly two measured things and nothing more — the count **R2**,
and the fact that a value outside `[0, 1]` passed every check the platform
currently runs. Do **not** claim "the platform cannot express this."

**Attack 4, from Crafty's own history.** `MIN-FOUNDATION-ET`, `ET-VERTICAL` and
`HETERO-NGSPICE` each found a structural assumption containing no domain word
that no lexical scan could see. A fourth should be expected. The adversarial
pass is **directed at** the fixed-direction/initial-value assumption class in
core readers — prediction **P6** is the aimed shot.

---

# 12. Required probes and tests

## Probes

| Probe | Content |
|---|---|
| **A** | Current contracts only — full typed steelman representation, zero new contracts (§6). |
| **B** | Storage independence — show scientific field meaning cannot be reduced to artifact/storage identity. |
| **C** | Boundary asymmetry — two boundaries whose scientific roles differ (inflow/outflow). |
| **D** | Discretization substitution — same scientific field and model, CD vs UW. |
| **E** | Direction reversal — reverse `u` and check whether inflow/outflow semantics remain correct without source-code special casing. |
| **F** | Coupling preview — describe what a future fluid→thermal field coupling endpoint would be. **Analysis only, no execution.** |

## Tests

Executable, and at minimum:

1. the zero-new-contract representation **failure measurements** (§7 counts),
   asserted as exact numbers, not as prose;
2. **no bulk arrays inside scientific control records** — a scan asserting no
   `ScientificProblem`, `ScientificResult.values`, `Quantity` or
   `ScientificParameter` produced by the probe carries O(mesh) data;
3. **storage relocation remains irrelevant** — the field's reference is
   unchanged across two backends;
4. **current core cannot silently call a field a scalar** — or, if it can, that
   is asserted as the measured finding;
5. **boundary ambiguity is demonstrated deterministically** — same records, two
   admissible readings, asserted;
6. **no domain-specific core branch was added** — `src/engcore/scientific/`
   byte-unchanged, asserted by digest;
7. all existing milestone regressions remain green.

Run **TARGETED**, then **FAST**, then **FULL**. FULL is the gate.

---

# 13. Fail conditions

Any one of these means the milestone failed, regardless of what else it found.

1. A file under `src/engcore/scientific/` was added, edited, or its bytes
   changed.
2. A file under `src/engcore/domains/thermal/` was added or edited.
3. A candidate abstraction from §10 was implemented in production core.
4. A gap was declared without the steelman attempt of §6 having been made.
5. Ledger 1 and Ledger 2 findings were blended, or a Ledger 2 finding was
   reported as an evidence gain.
6. An evidence level above `L1` was claimed anywhere, or a new level invented.
7. A `MODEL0-R`, `DATA-BOUNDARY0`, `ET-VERTICAL` or `HETERO-NGSPICE` evidence
   upgrade was claimed.
8. A pre-existing test was edited or a tolerance loosened.
9. The FULL suite is not green.
10. Experimental abstractions were left in the tree without being either
    deleted or clearly isolated as permanent evidence fixtures.

---

# 14. Evidence ceiling, declared before running

```text
Field semantics             at most  FORCED or LIKELY-FORCED / L0 + measured gap
Topology / support          at most  LIKELY-FORCED / L0        (Ledger 2)
Discretization separation   at most  FORCED or DEFER / L0 + measured gap
Boundary semantics          at most  FORCED / L0 + measured gap
Probe pack's own execution  at most  L1 EXERCISED
```

`L2` is **excluded outright**: this milestone has one author, one day, one
interface, and §54.1's definition of "materially different" explicitly excludes
exactly that. `L3` is excluded outright: nothing here touches scale,
concurrency, latency or failure injection.

**No abstraction that was never implemented may be assigned `L1`.** A measured
gap is evidence *about* a missing abstraction; it is not evidence *for* a
design that does not exist.

---

# 15. What the evidence document must refuse to claim

* That the probe proves any particular contract shape is correct.
* That a `FORCED` verdict authorizes implementation without its own
  preregistered milestone.
* That agreement with the Ogata–Banks reference outside its validity window
  verifies anything.
* That `DATA-BOUNDARY0` gained evidence (**P8**).
* That `ScientificTwin` gained evidence. It has gained **zero for two
  consecutive milestones** and must not be pressed into service here to change
  that.
* That the fluid/HVAC convective-transport limit recorded at §64.3 was closed.
* That "no domain leakage" was established by a lexical scan. §64.3 already
  recorded that the one real leak found contained no domain word.

---

# 16. Explicit exclusions — what this probe does NOT examine

Stated so the scoping is honest and so the falsifier attacks the right surface:

vector or tensor field rank (`u` is a signed scalar) · 2D/3D topology,
unstructured meshes, mesh tags, multi-region problems · field-valued parameters
or coefficients (`u`, `D` constant) · nonlinearity and state-dependent
coefficients · pressure-velocity coupling, saddle-point or DAE structure ·
conservation/flux accounting across an interface · **any** coupling: no
`QuantityDependency`, no second problem, no `ET-VERTICAL` record · external
providers, concurrency, latency, scale, GPU, distributed ownership · field
transfer or interpolation between supports (one mesh throughout) ·
`ScientificDataReference` shape/support descriptors · materials, substances,
property models · acausal composition and physical connectors · `ScientificTwin`
as instance authority.

---

# 17. Placement

The probe pack lives at a path **outside** `src/engcore/domains/thermal/`
(fail condition 2) and outside `src/engcore/scientific/` (fail condition 1). It
is experimental and is either deleted before the final commit or retained as a
clearly isolated, clearly labelled permanent evidence fixture — never promoted
into production core.

---

# 18. Stop rule

`CRAFTY_MASTER_CONTEXT.md` §60 applies: at most two adversarial rounds, then the
milestone reports what it measured. Findings that survive without a measurement
are recorded as `L0` opinions and labelled as such.

---

# 19. Output

`docs/hostile-core-domain-stress-evidence.md`, written **after** execution,
recording sections A–S of the milestone brief. Nothing learned after this point
is back-written into this preregistration.

The deliverable of this milestone is **evidence and a sharply constrained next
milestone**, not architecture.
