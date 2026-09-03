# HOSTILE CORE / DOMAIN STRESS PROOF — Evidence

**Milestone:** `HOSTILE-CORE-STRESS`
**Kind:** discovery / falsification. **No architecture was implemented.**
**Decision status:** none. This milestone freezes nothing.
**Evidence:** `L0 REASONED` + measured gaps. `L1 EXERCISED` for the probe pack's
own executed behaviour only. **No `L2`, no `L3`, no upgrade to any existing
holding.**
**Branch:** `hostile-core-domain-stress`
**Preregistration:** `docs/hostile-core-domain-stress-prereg.md`, committed at
`52932d6` before any source file on this branch was written. **Immutable.**
Nothing below is back-written into it.

> This document is written **after** execution. Where a preregistered
> prediction failed, it is recorded as a deviation with the measurement that
> refuted it, not quietly restated.

---

# A. Selected hostile consumer

**1D transient advection-diffusion of a normalized scalar.**

```text
∂c/∂t + u ∂c/∂x = D ∂²c/∂x²        x ∈ [0, 1] m,  u = 1 m/s,  D = 0.025 m²/s
Pe = uL/D = 40
```

`c` is dimensionless and normalized, following the baseline domain's explicit
refusal of an absolute scale. `u > 0`, so "upstream" is unambiguous *in the
physics* by construction — any failure to recover it is a failure of the
**records**.

Three frozen cases, two of which execute:

| Case | Statement | Executes |
|---|---|---|
| **S** | steady, `c(0)=1`, `c(L)=0`, exact closed form, `n_cells ∈ {8,16,40,80,160}` → `Pe_cell ∈ {5, 2.5, 1, 0.5, 0.25}` | yes |
| **T** | transient, `c(x,0)=0`, Dirichlet inflow, homogeneous Neumann outflow, backward Euler | yes |
| **N** | `D = 0`. Representation only | **no solves** |

Two discretizations: **CD** (2nd-order central) and **UW** (1st-order upwind).
Diffusion central in both.

## Probe is real physics, not a prop

| Measurement | Result |
|---|---|
| CASE S, CD vs exact, `n_cells` 8 → 160 | error falls monotonically `4.37e-1 → 1.93e-3` |
| CASE S, UW vs exact | `1.60e-1 → 4.17e-2` (first order, numerical diffusion) |
| CASE T, CD vs Ogata–Banks | `3.71e-3` |
| CASE T, UW vs Ogata–Banks | `2.13e-2` |
| Ogata–Banks window margin `L/2 − (u·t + 4√(Dt))` | **`+0.017157 m`**, positive |

The Ogata–Banks reference is **semi-infinite** and the domain is not. The margin
above is stated as a number, not asserted as a boolean, because agreement
outside that window would verify nothing. This is a concession against the
baseline domain, which deliberately chose a single Fourier mode so its reference
carried no approximation of its own.

---

# B. Why this consumer, and why the alternatives lost

`architecture-decision-reviewer` returned **ACCEPT WITH CHANGES**, selecting
candidate **B** in its modified form **B′**. Four required changes were carried
into the preregistration and all four were executed: a frozen three-case
configuration; a binding steelman requirement; a count-based instrument; and the
two-ledger rule.

**A — lumped pressure-driven pipe network: rejected on the binding criterion.**
It is structurally isomorphic to the existing `electrical/dc` MNA domain —
potential ↔ pressure, branch flow ↔ current, conductance ↔ inverse hydraulic
resistance, KCL ↔ mass conservation, reference node ↔ datum pressure. Scored
against thermal diffusion it looks different; scored against the *whole
repository* it differences against nothing, and against a domain that has
additionally been driven by a foreign provider.

**C — 2D Navier–Stokes skeleton: rejected on confounding and cost.** It fuses
six architectural pressures, so a representation failure could not be attributed
to a cause. Confounding is a **cost** in a discovery milestone. It is also on
the explicit do-not-build list twice.

**D — 2D scalar transport in a prescribed velocity field: rejected narrowly, on
one judgement.** It adds a genuine vector quantity, 2D multi-region boundaries
and a field-valued model input. It was rejected because those pressures target
concepts the repository **already records as deferred at `L0`**, while B′ targets
records that exist, are frozen, and had never been exercised. Cost was 3–5×.
**The reversal condition is preregistered:** if a later reader judges that
FLUID/PDE v0's *representational* risk dominates its *semantic* risk, D is the
right next probe and this milestone under-scoped.

**E — defer, per §61's ordering: rejected** because it defers the risk rather
than removing it.

---

# C. The zero-new-contract representation attempt

Preregistration §6 made the steelman **binding**, and §13.4 makes a gap declared
without one a fail condition. The reason is specific: the repository's only
existing PDE domain routed *around* the condition contracts — `BoundaryCondition`
has **zero producers anywhere in `src/engcore/domains/`** — so "you never tried"
is a live and correct objection.

What was tried, and what it bought:

| Encoding attempted | Outcome |
|---|---|
| Real `InitialCondition` records | **WORKS.** CASE T's uniform `c(x,0)=0` is representable |
| Real `BoundaryCondition(DIRICHLET, region, value)` + `(NEUMANN, region, gradient)` | **WORKS** for kind and value |
| `u`, `D`, `L`, `t_end` as typed `ScientificParameter` Quantities | **WORKS** |
| Separate `ModelRealizationDefinition` for CD and UW | **WORKS** for identity |
| `ExecutionBinding` in provenance | **WORKS** — the association is structural |
| Field as `ScientificDataReference` | **WORKS** for identity, unit and storage independence |
| `ScientificVariable.lower/upper` to bound the field | **REJECTED** — declarable and dimension-checked, but **no result path reads it**; a guard that guards nothing |
| `BoundaryCondition.coefficients` to carry a boundary coordinate | **REJECTED** — works mechanically, and the *key* would carry the science. `"position"`, `"x"`, `"origin"`, `"coord"` are all equally valid and mutually unintelligible |
| `ScientificCapability` / `SolverCapability` to carry the scheme | **REJECTED on layer grounds** — one is "a statement about nature", the other "what a backend can execute"; an upwind scheme is neither |
| `FlagCondition` / `CategoryCondition` for the resolution criterion | **REJECTED** — both work, and both require the *verdict* to be computed before the context is built, moving the judgement out of the record |
| `RangeCondition` on the **reciprocal** cell Péclet | **ADOPTED** |
| `ProvenanceRecord.inputs` for the mesh-dependent criterion | **ADOPTED** — see §J |

Each rejection above is **executed** in
`tests/test_hostile_core_domain_stress.py`, not asserted. That was a direct
requirement from the adversarial pass: "we tried everything" is exactly the
claim a discovery milestone must not make on trust.

---

# D. The recoverability matrix

A records-only reader is handed JSON payloads. It may import
`engcore.scientific` — a records reader legitimately knows its schema — and
**may not** import the probe's domain modules, asserted by AST scan.

`admit_free_text` decides whether meaning carried in an identifier or a
description counts as recovered. It applies to **every** question or to none;
granting it selectively was a defect the adversarial pass caught. Both passes are
reported.

| # | Question | Ledger | Strict | n | Permissive | n |
|---|---|---|---|---|---|---|
| Q1 | dependent scientific quantity | 1 | recoverable | 1 | recoverable | 1 |
| Q2 | scalar or spatially distributed | **2** | **impossible** | 0 | impossible | 0 |
| Q3 | physical unit | 1 | recoverable | 1 | recoverable | 1 |
| Q4 | spatial entity it is defined over | **2** | **impossible** | 0 | impossible | 0 |
| Q5 | initial state | 1 | recoverable | 1 | recoverable | 1 |
| Q6 | boundary conditions (kind + value) | 1 | recoverable | 2 | recoverable | 2 |
| **R1a** | boundary records injective onto physical systems | **1** | **impossible** | **2** | metadata-only | 1 |
| **R1b** | oriented boundary subset of a spatial entity | **2** | impossible | 0 | impossible | 0 |
| Q8 | governing model | 1 | recoverable | 1 | recoverable | 1 |
| Q9 | what transport direction means | 1 | **ambiguous** | — | ambiguous | — |
| Q10 | required solver capability | 1 | recoverable | 1 | recoverable | 1 |
| Q11 | storage independence of the field | 1 | recoverable | 1 | recoverable | 1 |
| **Q12** | same field, two discretizations | **1** | **impossible** | **2** | metadata-only | 1 |
| **R2a** | which realization identity ran | 1 | **recoverable** | **1** | recoverable | 1 |
| **R3** | is the problem transient | 1 | **recoverable** | 1 | — | — |
| **R4** | is the boundary set well posed | 1 | **impossible** | **0** | impossible | 0 |

Exactly two questions move under the permissive convention, and the concept with
no record at all — R1b — moves under neither. **No naming scheme conjures a
topology.**

## Q5 carries an unstated condition

`Q5 = recoverable` **only because CASE T's initial field is uniform**.
`InitialCondition.value` is a single `Quantity`, so the baseline domain's
`sin(πx/L)` has no home in the record — which is precisely why that domain
carries it as a metadata string. Counting Q5 as a clean pass without this
sentence would overstate it.

---

# E. `Quantity` — verdict

**No change forced. The contract survived every attack, including one this
milestone initially reported against it.**

* `Quantity.magnitude` is one `float`. The consumer needed no vector, tensor or
  array magnitude, and **none was added**. The field's bulk data went to
  `ScientificDataReference` throughout; a control-record scan confirms the
  longest sequence anywhere in a serialized record is **< 20** against a
  161-value field.
* `Quantity` refuses non-finite magnitudes. An earlier draft of this milestone
  reported that refusal as an unanticipated contract gap — see **deviation
  D-2**, §S. It is not one.

**DATA-BOUNDARY0's separation held under a field-valued consumer**: scientific
semantic identity and control stayed clear of bulk numerical state, with no
mesh-sized array in any `ScientificProblem`, `ScientificResult.values`,
`Quantity` or `ScientificParameter`.

---

# F. `ScientificDataReference` — verdict

**Storage independence holds. Field semantics were never claimed and are absent.**

Relocation from an in-memory store to a filesystem store leaves the reference
**byte-identical**, and resolution through the new backend returns the field
exactly. DATA-BOUNDARY0 is unchanged and **gains nothing here** — the field is
again 1-D contiguous float64, exactly as preregistered in **P8**.

The record carries exactly `{name, unit, count, dtype, digest, digest_algorithm}`.
Measured: a **steady** field and a **transient** field at `t_end`, both
`count=161`, differ in **no scientific field of the reference** — only the
content digest:

```text
steady    c:field[161 float64 dimensionless]@9f1ac8d10d19
transient c:field[161 float64 dimensionless]@79d073aab651
```

Six questions, six zeros: support, coordinates, topology relationship, time
level, component count, node/cell/face association. All **Ledger 2**, all
booked at **zero claimed evidence gain** — DATA-BOUNDARY0 records these
omissions as deliberate and this milestone re-confirms rather than discovers
them.

```text
ScientificDataReference != ScientificField      — measured, and already known
```

---

# G. Field semantics

**Ledger 2 throughout. Zero claimed evidence gain.**

Q2 and Q4 both return 0: a `ScientificVariable` that is a PDE field and one that
is a lumped scalar are **byte-identical records**, and nothing states what
spatial entity a field is defined over. `length` is a scalar parameter that
states an extent but not a domain, an orientation, or a set of boundary subsets.

This is a re-confirmation of `docs/scientific-core/README.md` "Deliberately
deferred" and master context §57. It is recorded because measuring a deferral
is worth something; it is **not** presented as new information.

---

# H. Topology / support

**Ledger 2. `LIKELY-FORCED`, at `L0`, with zero evidence gain claimed.**

R1b is the finding: closing R1a requires somewhere to say that region
`'boundary-a'` is the `x=0` end and carries outward normal `−x`. No support,
topology or region record exists to hold it. R1b is a **proper sub-part of Q4**,
and no change that leaves topology absent makes one recoverable without the
other.

**This is exactly where the adversarial pass caught the milestone overclaiming**
— see §N, BLOCKER 1.

---

# I. Boundary semantics

**The strongest Ledger-1 finding, and it is narrower than the milestone first
stated.**

## I.1 R1a — the `(kind, region, value)` triple is not injective

Measured empirically, not argued from types:

> Reversing the transport direction (`u = +1 → −1 m/s`) leaves **every
> serialized `BoundaryCondition` byte-identical**, while flipping which end is
> the inflow. One boundary-record set describes two physically different
> systems. Strict count: **2 admissible readings.**

The obvious fallback — *"Dirichlet means inflow"* — is killed by a record this
probe builds: CASE S declares Dirichlet at **both** ends, so the convention would
label two boundaries as the inflow of a one-dimensional flow.

**Universality, and this matters because the primary falsifier challenge was
aimed at it.** R1a is *not* reducible to a missing field concept.
`HETERO-NGSPICE` §66.4 needed a **passive-sign guard** for a two-terminal lumped
element with no continuum topology anywhere in sight. Orientation is a universal
scientific distinction; the *role names* "inflow/outflow" are the fluid-specific
part.

## I.2 What reacted to the reversal, and what did not

The only thing in the platform that noticed a direction reversal was a
`RangeCondition` on the **velocity parameter**, reporting
`OUTSIDE_VALIDATED_DOMAIN` with `violated = ('velocity',)`. It said the velocity
left its declared interval. It did not, and could not, say that the Neumann
condition is now sitting on the inflow end — which is the scientifically
important consequence.

## I.3 What already works

Q6 is a clean pass: kind and value are typed, serialized and dimension-checked
(for Dirichlet; the core deliberately does not constrain Neumann, and the probe's
`1/meter` gradient exercises that). Boundary *conditions* are well served.
Boundary **identity and orientation** are not.

```text
Boundary Condition  — represented
Boundary Identity   — not represented
```

---

# J. Discretization

## J.1 R2a — realization identity is recoverable. `ExecutionBinding` works.

`ProvenanceRecord.bindings` names the realization; `ImplementationReference.
implementation_id` differs between the two. Both typed, both serialized, count
**1**. This is `MODEL0-R` doing exactly what it was added to do, and it satisfies
`07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md` §16.E. **An H1 win, recorded with the
same prominence as the gaps.**

## J.2 R2b — selection semantics is the gap, not identity

Every typed **property** field of the two realizations is identical:
`formulation` (both `PDE`), `provided_capabilities`, `required_capabilities`,
`required_solver_capabilities`. Monotonicity — the property a planner would
actually select on — is stated only in `name`, `description` and `assumptions`.

> The records **distinguish** the two realizations and state no typed property
> by which a planner could **select** the bounded one.

**Counter-evidence, recorded rather than suppressed.**
`docs/scientific-core/README.md` "Fidelity: why the core declares none" rejected
a `RealizationFidelity` enum because its members conflated *"at least four"*
axes. That argument applies verbatim: "central vs upwind" conflates operator
family, order of accuracy, monotonicity/TVD character and staggering. It is the
strongest in-repo argument **against** a `FORCED` verdict on a `DESIGN-FROZEN`
contract, and §M weighs it.

## J.3 The mesh-dependent validity criterion — three encodings, three costs

`Pe_cell = u·dx/D` is a validity criterion of the **model** whose value is a
property of the **mesh**.

| Encoding | Criterion recoverable | Problem identity across refinement | Assessable pre-run |
|---|---|---|---|
| **A** — `n_cells` in `metadata` (what the baseline domain does) | metadata-only | mesh in metadata, so records differ | no |
| **B** — `n_cells` as a typed `IntegerValue` parameter | **recoverable** | **mesh enters problem identity**; two meshes are two problems, two `problem_id`s | yes |
| **C** — criterion as a typed `Quantity` in `ProvenanceRecord.inputs` | **recoverable** | **byte-identical across every mesh** | **no — run-scoped** |

Measured under ENCODING_C: `case_s(8)` and `case_s(160)` produce **identical
problem records**, `problem_id = transport-1d-advdiff-steady-u1-d0.025-l1-t0.2`,
while provenance carries `inverse_peclet_cell = 0.2` and `4.0` respectively. The
model's own condition then evaluates correctly —
`OUTSIDE_VALIDATED_DOMAIN` (violated `inverse_peclet_cell`) for the coarse mesh,
`IN_DOMAIN` for the fine one.

**An earlier draft of this milestone claimed a dilemma — "no encoding gives
both" — and that claim was false.** See deviation **D-3**, §S. What survives is
narrower, true, and contains **no fluid word**:

> A mesh-dependent validity criterion is assessable **per-run** and never
> **pre-run**, because its only typed home that keeps the problem mesh-free is a
> record that does not exist until a solve has produced it. `ValidityDomain`
> therefore cannot screen a proposed discretization before spending the solve.

This generalizes verbatim to CFL number, Courant number, y+, element aspect ratio
and element Jacobian.

## J.4 The baseline encoding cannot reach the criterion honestly

`ScientificProblem.validity_context` is built from typed parameters and documents
that it is *"deliberately not sourced from metadata"*. Under **ENCODING_A** —
the encoding the existing PDE domain actually uses — a reader obeying that rule
gets `UNKNOWN`, not `VIOLATED`, for a mesh at `Pe_cell = 5`. Only a reader
willing to break the platform's own stated rule reaches the right answer.

---

# K. Model / realization / solver

**The separation held. Nothing forced a change, and no evidence is claimed.**

`Scientific Model != Model Realization != Solver` was expressible throughout:
one `ScientificModelDefinition`, two `ModelRealizationDefinition` records, one
solver identity, association carried structurally by `ExecutionBinding`.

**No `MODEL0-R` evidence movement is claimed** from CD and UW being two
realizations of one model. `HETERO-NGSPICE` §66.3 withdrew exactly such a claim
because the differentiating record existed only inside the test. Same trap, same
answer: these two realization records were constructed by this proof, and a
proof cannot differentiate a contract using records it wrote for the purpose.

## K.1 Physical admissibility is a distinct verdict — and the platform can express it

`ValidationReport.status = PASS`, zero failures, attained levels
`{dimensionally_valid, numerically_converged}` — for CASE S, CD, `n_cells = 8`,
whose solution reaches **`c:max = 1.4301991580760791`**, a **43 % overshoot above
its own Dirichlet maximum**. Upwind is bounded at every rung; central violates
only at `Pe_cell ∈ {5, 2.5}`, exactly as the sign change at `Pe_cell = 2`
predicts.

**What this does NOT show, stated because an earlier draft claimed it and was
wrong.** It does not show the platform cannot express the check.
`ValidationCheck.name` is free text and `ValidationReport.status` returns `FAIL`
if any check fails, so a domain can write the boundedness check **today**, with
no contract change, from inputs already typed on these records. The probe writes
it: `maximum_principle_held`, `FAIL`, residual `0.4301991580760791`, and the
aggregate verdict flips to `FAIL`. See deviation **D-4**, §S.

**What survives is an asymmetry in the evidence ladder, and it is real:**

> A domain can record an admissibility **violation** (`outcome=FAIL`) and
> structurally **cannot record its attainment**. `ValidationLevel` has seven
> members and none denotes physical admissibility, so a *passing* check has
> nothing to put in `establishes=` and contributes to no attained level. The
> ladder can say "this is wrong" and cannot say "this was checked and is right".

Corroborating measurement: `ScientificVariable` carries typed, dimension-checked
`lower`/`upper` bounds, and `require_within_bounds` is called from exactly four
files — design space, experiment, optimizer adapter, and its own definition.
**Nothing under `results/` consults them.** §66.4's own lesson, one layer out:
*a check whose only effect is a field nothing consults is not a guard* — here the
field is consulted, just never against a solved state.

---

# L. Future coupling — analysis only, nothing implemented

**PROBE F. No `QuantityDependency` was declared, no second problem, no runtime.**

A dependency naming the solved field's bulk reference `"c:field"` returns
`MISSING`. That is correct and deliberate: `QuantityDependency` resolves an
endpoint through `result.values ∪ problem.variables ∪ problem.parameters` and
refuses to consult `data_references`, because — in its own words — *"nothing in
this record can state how a field is transported between two supports."* An
honest `MISSING` beats a clean check implying a transfer semantics no contract
provides.

**The trap, measured:** a dependency naming `"c:midpoint"` — a *scalar reduction*
of the field — **checks clean**.

> The only expressible coupling endpoint today is the one that has already
> thrown the field away.

`QuantityDependency` verdict: **scalar-endpoint-oriented, correctly and
knowingly so.** It was not extended, and the fluid/HVAC convective-transport
limit recorded at §64.3 is **not closed**.

---

# M. Candidate abstractions — reduction verdicts

Each asks: can this be avoided using existing typed contracts without semantic
ambiguity, metadata, duplicated identity, source-code interpretation, storage
leakage or discretization leakage?

| Candidate | Verdict | Ledger | Reasoning |
|---|---|---|---|
| **Boundary orientation / identity** (an outward normal or an ordering, *not* a general boundary system) | **FORCED** | 1 | R1a: the `(kind, region, value)` triple is not injective onto physical systems, measured by byte-identical records under reversal. Universal beyond PDEs — `HETERO-NGSPICE` §66.4's passive-sign guard is the field-free corroboration |
| **A route from problem structure into `validity_context`** | **FORCED** | 1 | R4: `validity_context` is built only from typed parameters, so no declarative criterion can reference a structural fact about the problem statement. Narrow, and it needs no new record — see §Q |
| **`FieldSupport` / `Topology`** | **LIKELY-FORCED** | **2** | R1b and Q4. Already recorded as deferred at `L0`; **zero evidence gain claimed**. The remedy for R1a lives here, which is why R1a's `FORCED` verdict is booked on the narrow injectivity claim and nothing wider |
| **Non-uniform `InitialCondition`** | **LIKELY-FORCED** | 1 | `InitialCondition.value` is one `Quantity`. The probe's uniform IC hid this; the baseline domain's `sin(πx/L)` does not fit and is carried as a metadata string. Measured on the existing domain, not on the probe |
| **`DiscretizationDefinition`** | **DEFER** | 1 | R2b is about **selection**, not identity, and identity already works. Weighed against it: the fidelity-conflation argument the core already used to refuse `RealizationFidelity`. Forcing a typed discretization field onto a `DESIGN-FROZEN` contract on one consumer's evidence is not warranted |
| **A physical-admissibility `ValidationLevel`** | **DEFER** | 1 | The *check* is writable today. Only the ladder's attainment side is missing, which is one enum member and needs a second consumer before it is worth a contract change |
| **`FieldDefinition`** | **DEFER** | 2 | Q2/Q4 are 0, but this milestone measured a 1-D scalar on one mesh and has no evidence about what a field record must carry. Deferring is the honest position |
| **`Mesh`** | **REJECT** | — | Nothing here needs it. The mesh appeared only as a count, and every question it touched was answered without one |
| **`VectorQuantity`** | **REJECT** | — | `u` is a signed scalar throughout. **Not probed** — see §P |
| **`FieldState`** | **REJECT** | — | No evidence whatsoever. `ScientificDataReference` + a time level would be the cheaper question, and it was not asked |
| **A general Boundary system** | **REJECT** | — | R1a needs orientation, not a BC taxonomy. OpenFOAM's library is evidence a mature CFD system needed one; it is not evidence Crafty needs one now |

**Only `FORCED` candidates enter the next milestone's design input, and none was
implemented here.**

---

# N. Falsifier results

`architecture-falsifier` returned **FALSIFIED**: **3 BLOCKERs, 3
BREAKING-RISKs. All six closed before commit.** The measurements very largely
survived; what was falsified was the **claim layer** built on them.

## BLOCKER 1 — "boundary orientation" was Topology wearing a Ledger-1 costume

The instrument booked a finding by *which record it inspected*, not by *which
record the missing concept belongs to*. The orientation finding inspected
`BoundaryCondition` (exists) while its remedy is an oriented boundary of a
topology (does not exist) — so the **same absent concept was booked Ledger 1
under R1 and Ledger 2 under Q4**. That is ledger blending, which prereg §13.5
declares a fail condition.

**Closed by:** stating the booking rule explicitly — *a finding is Ledger 1 only
when **both** the measurement and the remedy live in a record that exists* — and
**splitting** R1 into R1a (Ledger 1, narrow injectivity claim) and R1b
(Ledger 2, zero evidence gain). The falsifier also supplied a strengthening the
milestone had missed: §66.4's passive-sign guard, which makes R1a survive
independently of fields entirely.

## BLOCKER 2 — the encoding fork was a false dilemma

The claim *"no encoding gives both"* is a universal negative over encodings, and
one counterexample refutes it. `ProvenanceRecord.inputs` is
`Mapping[str, Quantity]` — typed, dimension-checked, serialized — on the record
documented as *"everything needed to attribute and re-derive a result"*, and
`validity_context`'s own docstring sanctions exactly this use for *"a Reynolds
number, a detected regime"*. **The probe already populated that field.**

**Closed by:** implementing and measuring **ENCODING_C**, withdrawing the
dilemma, and replacing it with the residual in §J.3 — which is narrower, true,
and generalizes to CFL, Courant, y+ and element aspect ratio.

## BLOCKER 3 — P7 claimed an inexpressibility the preregistration forbade claiming

The probe's own prose said *"no such concept exists anywhere in the platform —
there is no contract to express one on"*. Prereg §11 Attack 3 had pre-committed
the opposite restraint. And the claim was false: the check is writable today.

**Closed by:** deleting the sentence, writing the check (`admissibility_check`),
executing it, and restating the finding as the **evidence-ladder asymmetry** in
§K.1 plus the measured fact that nothing in universal core compares a result to
declared bounds.

## BREAKING-RISK 1 — two conventions on one channel

The instrument denied the free-text channel to R1 and granted it to R2b, then
reported the contrast as a finding.
**Closed by:** one `admit_free_text` switch applied to every question, with the
matrix reported under **both** conventions (§D). Exactly two questions move; R1b
moves under neither.

## BREAKING-RISK 2 — R2b excluded the one typed field that discriminates

`ImplementationReference.implementation_id` is typed, serialized, and differs
between the two realizations. The reader silently excluded it and reported a gap
that was not there.
**Closed by:** naming the identity fields explicitly, restating R2b as
**selection** semantics, and recording §16.E and the fidelity-conflation argument
as counter-evidence against a `FORCED` verdict.

## BREAKING-RISK 3 — R4's "not detectable at all" was too strong

A `RangeCondition` over a structural count evaluates fine if the context can
carry one.
**Closed by:** executing that counterexample —
`wellposedness_is_detectable_with_structural_context` returns
`OUTSIDE_VALIDATED_DOMAIN` — and narrowing R4 to the `validity_context` finding.
The regime-dependence half is attributed to preregistration baseline fact **B17**,
corroborated rather than discovered.

## The falsifier's own separation: fluid-specific vs universal

Stress-tested against linear elasticity, thermal conduction with flux BCs,
electromagnetics, battery P2D, lumped electrical DC, CFD, and long-lived
serialized records.

| | Fluid-specific | Universal to field/PDE | Universal beyond fields |
|---|---|---|---|
| **R1 orientation** | the role *names* "inflow/outflow"; a BC kind selected by flux sign | outward normal for any Neumann/Robin/flux condition | **yes** — passive sign convention, demonstrated in this repository's own lumped DC domain |
| **R2b selection** | — | discretization selection | **yes** — realization selection |
| **P7 admissibility** | — | positive-definiteness, `T > 0 K`, SOC and mole fraction in `[0,1]` | **yes** — the ladder asymmetry |
| **R4 well-posedness** | `Pe_cell` as the particular criterion | condition count vs operator order; rigid-body modes in traction-only elasticity | — |

**The primary challenge — "these gaps are artifacts of the fluid example" —
half succeeds.** R1's *role* half is a fluid artifact; R1's *orientation* half is
not, and is not even PDE-specific. R2b and P7 are not fluid artifacts at all. R4
is a PDE artifact but not a fluid one.

## What the falsifier explicitly did **not** find

No new contract is required by this milestone. Its `DEFER`/`REJECT` list was
judged appropriately conservative, the control-plane/data-plane separation held,
the capability grammar held, and the zero-core-edit discipline held.

**One thing it named that this milestone did not measure and therefore does not
claim:** `BoundaryCondition` has no `time` field while `InitialCondition` does,
so a time-varying inflow `c(0,t) = f(t)` has no home. CASE T froze the inflow
constant, so the probe could not see it. Recorded as the cost of that choice.

---

# O. Architecture fitness

| # | Would the attempted representation require... | Verdict |
|---|---|---|
| 1 | a domain branch in universal core | **NO** — `src/engcore/scientific/` byte-unchanged, asserted by `git diff` in a test |
| 2 | untyped metadata | **PARTLY** — ENCODING_A needs it and ENCODING_C does not; the probe measured both rather than settling for one |
| 3 | changing `ScientificDataReference` into field semantics | **NO** — refused; the gap is recorded instead |
| 4 | changing `Quantity` into a bulk-data container | **NO** — no mesh-sized array in any control record |
| 5 | solver identity in the scientific model | **NO** |
| 6 | mesh identity in scientific field identity | **NO under ENCODING_C**; **YES under ENCODING_B**, which is why ENCODING_B is not recommended |
| 7 | duplicated `ScientificTwin` authority | **NO** — no twin was constructed. `ScientificTwin` gains **zero evidence for a third consecutive milestone** |
| 8 | breaking an existing schema | **NO** — no schema version moved |
| 9 | modifying a frozen proven contract | **NO** — `src/engcore/domains/thermal/` byte-unchanged, asserted |
| 10 | reading domain source code to understand serialized meaning | **YES, for R1a and R2b under the strict convention** — this is the milestone's central measured gap |

Also asserted: the probe lives in `experiments/`, outside `src/`, and
`git grep hostile_core_stress -- src/` returns nothing, so it cannot be promoted
into production core by accident.

The lexical no-domain-leakage scan passes. **It is recorded as the weak claim it
is:** §64.3 already established that the one real leak found in this repository
contained no domain word, so a negative result here proves little. It is run
because a positive hit would still be decisive.

---

# P. What was NOT probed

Stated so the scoping is honest and so the next milestone is not built on
assumed coverage:

vector or tensor field rank · 2D/3D topology, unstructured meshes, mesh tags,
multi-region problems · field-valued parameters or coefficients · nonlinearity
and state-dependent coefficients · pressure–velocity coupling, saddle-point or
DAE structure · conservation/flux accounting across an interface · **any**
coupling: no `QuantityDependency` declared, no second problem, no `ET-VERTICAL`
record touched · external providers, concurrency, latency, scale, GPU,
distributed ownership · field transfer or interpolation between supports ·
`ScientificDataReference` shape/support descriptors · materials, substances,
property models · acausal composition and physical connectors · `ScientificTwin`
as instance authority · **time-varying boundary values** (CASE T froze the
inflow constant).

---

# Q. What NOT to build, and the exact minimum next milestone

## Do not build

`FIELD0`, `TOPO0`, `DISC0`, `EQIR0`, a generic boundary system, a mesh
framework, a CFD solver, a `VectorQuantity`, a `FieldState`, or a
`RealizationFidelity` in any disguise. None is forced by this milestone's
evidence, and three are explicitly rejected in §M.

Do **not** build the three `FORCED`/`LIKELY-FORCED` items as three roadmap
milestones either. The evidence-driven method used for electro-thermal applies:
define the **minimum foundation a real PDE consumer forces**, and nothing more.

## The next milestone

**`MIN-FOUNDATION-PDE` — the minimum semantic foundation a real field consumer
forces.** Scoped by exactly three questions, in this order:

1. **Boundary orientation** (`FORCED`, Ledger 1). The smallest record that makes
   the `(kind, region, value)` triple injective onto physical systems. It is
   *not* a topology and *not* a boundary taxonomy — §66.4's lumped passive-sign
   guard is the proof that orientation is separable from both. Reduction attack
   first: can an ordering live on the existing `BoundaryCondition` without a new
   record?
2. **A route from problem structure into `validity_context`** (`FORCED`,
   Ledger 1). Narrow, needs no new record, and it closes R4 and half of §J.4.
   Ask specifically whether the pre-run/per-run asymmetry in §J.3 is acceptable
   or must be closed.
3. **Non-uniform `InitialCondition`** (`LIKELY-FORCED`, Ledger 1). Measured on
   the *existing* domain, not on the probe, which makes it the least speculative
   of the three.

**Entry condition:** the consumer must be a real one, not another probe. The
reviewer's rejected candidate **D** — 2D scalar transport in a prescribed
velocity field — is the natural choice, because it is the cheapest consumer that
forces the representational half this milestone deliberately did not probe
(vector rank, 2D support, field-valued coefficients). If FLUID/PDE v0 is intended
as a real domain rather than another proof, run D first.

**Explicitly deferred to a later milestone with its own evidence:** the
admissibility `ValidationLevel` member, `DiscretizationDefinition`, and every
Ledger-2 item.

---

# R. Tests

`tests/test_hostile_core_domain_stress.py` — **41 tests, all passing.**

| Prereg §12 requirement | Where |
|---|---|
| zero-new-contract representation failure measurements | `test_recoverability_matrix_under_the_strict_convention` / `..._permissive_convention` — exact question→verdict maps |
| no bulk arrays inside scientific control records | `test_no_bulk_array_reaches_a_scientific_control_record` — longest serialized sequence < 20 against a 161-value field |
| storage relocation remains irrelevant | `test_probe_b_relocation_does_not_change_the_scientific_record` |
| current core cannot silently call a field a scalar | `test_probe_b_field_meaning_does_not_reduce_to_storage_identity` — measured, and it **can** |
| boundary ambiguity demonstrated deterministically | `test_p1_upstream_boundary_is_unrecoverable_from_records` — byte-identical records under reversal |
| no domain-specific core branches added | `test_no_universal_core_file_was_added_or_edited`, `test_no_thermal_domain_file_was_added_or_edited`, `test_the_probe_adds_no_domain_branch_to_universal_core` |
| all existing milestone regressions green | FULL suite |

Instrument integrity: `test_reader_cannot_see_the_domain` asserts by AST scan
that the records-only reader imports no probe module.

**Regression:**

```text
FAST   1262 → 1303   (+41)
FULL   1784 → 1825   (+41)
```

**No pre-existing test was edited. No tolerance was loosened. No test was
skipped, deleted or reordered.**

One environment note, recorded because it is not a code fact: pytest's default
temp root is not writable in this sandbox, so runs used `--basetemp`. This
affects four pre-existing `test_data_boundary0.py` tests identically and is not
introduced by this milestone.

---

# S. Deviations from the preregistration

Recorded here because §54.1 forbids back-writing them into the immutable
preregistration.

## D-1 — P7 confirmed in substance, **wrong in sign**

Prereg §8 P7 predicted *"CD at `Pe_cell = 5` produces `c(x) < 0`"*.
**Measured: an overshoot of `c:max = 1.4302` above the Dirichlet maximum, and
`c:min = 0` exactly — never negative.** With `c(0)=1` and `c(L)=0` the
central-difference oscillation grows towards the outflow, so it exceeds 1 rather
than falling below 0. The *substance* of the prediction — a value outside the
physically admissible range passing every check — holds exactly.

## D-2 — the "infinite cell Péclet" finding is **WITHDRAWN**

The probe initially declared its criterion as `peclet_cell ≤ 2`, found that at
`D = 0` the true value is infinite, that `Quantity` refuses non-finite
magnitudes, and reported that as an unanticipated contract gap that *"no lexical
scan could have found"*.

**It is not a contract finding.** `Pe ≤ 2` and `1/Pe ≥ 0.5` are the same
criterion, and the reciprocal is `0.0` at `D = 0` — finite, expressible, and
correctly reported as violated. Any scalar criterion on `[0, ∞]` admits a
monotone finite reparameterisation. **`Quantity`'s invariant survives intact.**

Both halves are asserted in the test suite so the withdrawal is a measurement
rather than a concession. The residual worth carrying is narrow:
`ValidityStatus.UNKNOWN` conflates *"the context did not supply this"* with
*"the context could not express this"*, so an author who picks the unbounded
parameterisation gets the second silently disguised as the first.

## D-3 — the encoding fork is **WITHDRAWN as a dilemma**

See §N BLOCKER 2 and §J.3. `ENCODING_C` gives a typed criterion *and* a
mesh-free problem identity. The residual — pre-run vs per-run assessability — is
what is claimed instead.

## D-4 — P7's inexpressibility claim is **WITHDRAWN**

See §N BLOCKER 3. The check is writable today and the probe writes it.

## D-5 — P5 **falsified**

Prereg P5 predicted the mesh-dependent criterion would not be reconstructible
from records. It is reconstructible from **three** sources at three different
costs (§J.3). The prediction was right about the encoding the baseline domain
uses and wrong about the space of encodings.

## D-6 — roadmap reordering

Recorded in the preregistration itself: this milestone ran ahead of
`API / MCP v0`, which §61 permits as a risk-driven reordering.

## Predictions that held

* **P1** — R1a admits 2 readings. Confirmed.
* **P2** — `is_time_dependent` is `False` for the repository's only transient
  PDE. Confirmed **on the existing domain**. The *contract* is correct: the
  steelman writes real `InitialCondition` records and the property is then right
  for both frozen cases. The defect is in the domain, not the contract.
* **P4** — no model can declare the conditions its equation requires.
  Confirmed, and narrowed (§N BREAKING-RISK 3).
* **P6** — the aimed shot at core. CASE S is steady, declares no initial
  condition, and has its state fixed entirely by Dirichlet boundaries.
  `unresolved_inputs` and `externally_imposed` both return `()`. **The
  `MIN-FOUNDATION-ET` repair holds.** No fourth structural assumption of that
  class was found in a core reader.
* **P8** — DATA-BOUNDARY0 gains nothing, and none is claimed.

---

# T. Evidence status

Per §55, and nothing stronger exists.

| Item | Decision | Evidence |
|---|---|---|
| Boundary orientation / injectivity | none — input to the next milestone | **`FORCED` / `L0` + measured gap** |
| Structural facts in `validity_context` | none | **`FORCED` / `L0` + measured gap** |
| Field support / topology | none | **`LIKELY-FORCED` / `L0`** — Ledger 2, **zero evidence gain** |
| Non-uniform `InitialCondition` | none | `LIKELY-FORCED` / `L0` + measured gap |
| Discretization separation | none | **`DEFER`** — identity works; selection is the gap |
| Physical-admissibility level | none | `DEFER` / `L0` |
| Field semantics | none | `DEFER` — Ledger 2, zero evidence gain |
| The probe pack's own execution | — | `L1 EXERCISED` |

**No abstraction that was never implemented is assigned `L1`.** A measured gap
is evidence *about* a missing abstraction; it is not evidence *for* a design
that does not exist.

**Unchanged, and explicitly not upgraded:** `MODEL0-R`, `DATA-BOUNDARY0`,
`MIN-FOUNDATION-ET`, `ET-VERTICAL`, `HETERO-NGSPICE`. `ScientificTwin` gains
zero evidence for the third consecutive milestone.

---

# U. Git

| Commit | Content |
|---|---|
| `52932d6` | `Preregister hostile core domain stress` — preregistration only, immutable |
| *(this)* | `Stress core against hostile PDE consumer` — probe pack, tests, evidence |

`src/engcore/scientific/` and `src/engcore/domains/thermal/` are byte-unchanged
on this branch, asserted by tests rather than by claim.
