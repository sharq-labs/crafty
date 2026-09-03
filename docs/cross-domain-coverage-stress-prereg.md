# CROSS-DOMAIN COVERAGE STRESS — Preregistration

**Milestone:** `CROSS-DOMAIN-COVERAGE` — attack the current Crafty core from four
materially different scientific domain families and **measure** which candidate
abstractions are genuinely universal and which are artifacts of transport/PDE
thinking.
**Kind:** coverage discovery. It is **not** `FIELD0`, `TOPO0`, `DISC0`, a
structural domain, CFD, a chemistry engine, a controls engine, API/MCP, or a
planner.
**Decision status target:** none. This milestone freezes nothing.
**Evidence target:** `L0 REASONED` + a measured coverage matrix. `L1 EXERCISED`
for the probe packs' own executed behaviour only. `L2` and `L3` are excluded
outright. See §14.
**Date:** 2026-09-03
**Branch:** `cross-domain-coverage-stress`
**Preregistered before implementation.** Everything below was written before any
probe source file was added on this branch. Working tree verified clean at
`222c437`.

> **This file is immutable.** It records what was committed to *before* results
> were observed. Executed results, deviations, corrections, adversarial findings
> and the final classification go in
> `docs/cross-domain-coverage-stress-evidence.md` and nowhere else.
>
> This is **not** a freeze document, and it authorizes no production
> architecture.

**Canonical milestones verified present before this document was written:**

| Milestone | Decision | Evidence | Record |
|---|---|---|---|
| `DATA-BOUNDARY0` | `PROPOSED` | `L1 EXERCISED` | master context §56 |
| `MODEL0-R` differential | `DESIGN-FROZEN` | `L2 DIFFERENTIATED` (scoped) | §58 |
| `MIN-FOUNDATION-ET` | `PROPOSED` | `L1 EXERCISED` / `L0` deferrals | §64 |
| `ET-VERTICAL` | `PROPOSED` | `L1 EXERCISED` | §65 |
| `HETERO-NGSPICE` | `PROPOSED` | `L1 EXERCISED`; scoped `L2` withdrawn | §66 |
| `HOSTILE-CORE-STRESS` | **none — freezes nothing** | `L0` + measured gaps | §67 |

---

# 1. The single question

> Which missing scientific abstractions are **genuinely universal** across
> multiple materially different domain families, and which are **artifacts of
> transport/PDE thinking**?

A concept must not become universal merely because one domain needs it. Strong
evidence for universal placement normally requires pressure from **multiple
materially different consumers**.

The output is a **defensible cross-domain coverage matrix** and a constrained
next milestone. It is not a foundation.

---

# 2. Roadmap deviation — recorded, not assumed (RC-6)

Two deviations, both stated here so no later reader has to reconstruct them.

**D-A. This is the second deferral of `API / MCP v0`.** §61 lists it as next;
`HOSTILE-CORE-STRESS` deferred it once and recorded that as its deviation D-6.
§61 self-describes as risk-driven rather than frozen, and §54.2 states work
packages are pulled by a proof. The reordering is permitted; it is recorded
because it is the second.

**D-B. This milestone consumes the consumer `MIN-FOUNDATION-PDE` reserved.**
§67.5 named the next milestone `MIN-FOUNDATION-PDE` with the binding entry
condition *"the consumer must be a real one, not another probe"*, and named 2D
scalar transport in a prescribed velocity field as its natural consumer.
Consumer B below **is that consumer, run as a minimised probe.**

The cost is stated in advance rather than discovered later:

> `MIN-FOUNDATION-PDE` will need either a fresh consumer or the **promotion of
> Consumer B's probe into a real domain pack.** The preregistered preference is
> **promotion**, because Consumer B will already carry the typed records, the
> boundary regions and the manufactured-solution reference that a real pack
> needs; what it will lack is transient behaviour, a second discretization and
> a refinement ladder. Whether promotion satisfies §67.5's entry condition is a
> founder decision and is **not** settled by this milestone.

---

# 3. Reviewer verdict and the option selected

`architecture-decision-reviewer` was invoked before this document was written,
on the question *"what four minimum consumers maximize architectural
differentiation while minimizing implementation cost?"*, against five
alternatives: **ALT-0** defer and run `MIN-FOUNDATION-PDE`; **ALT-1** four
consumers with B minimised plus a control group; **ALT-2** three new consumers
plus the existing hostile probe as family B; **ALT-3** the founder's four priors
uncheapened; **ALT-4** records-only with no execution.

**Verdict: `ACCEPT WITH CHANGES`. Selected: ALT-1**, with six required changes
(RC-1 … RC-6), all carried into this document and none optional.

**Why the losers lost.**

* **ALT-4** (records-only) is rejected on a repository-specific ground:
  `HOSTILE-CORE-STRESS` recorded **two false gaps** (D-2 infinite Péclet, D-3
  the encoding fork) that were caught *only because the probe executed and could
  be forced to write the counterexample*. A representation-only milestone cannot
  self-correct that way.
* **ALT-3** re-measures two things `HOSTILE-CORE-STRESS` already measured (a
  second discretization; a refinement ladder) at 3–5× the cost.
* **ALT-2** is the correct **fallback** if cost proves unaffordable. It loses
  exactly two unique pressures — a field-valued model *input*, and an inflow set
  determined by a sign that varies *along* a boundary — and the 2D half of
  family B.
* **ALT-0** is the correct choice if the founder judges that closing two
  measured `FORCED` findings outranks knowing whether they are universal. That
  is a strategic call; it was made in favour of coverage.

## 3.1 RC-3 spike, resolved before this document was committed

The entire cost case rests on one shared records-only instrument serving four
structurally unlike consumers. The reviewer required this be resolved **before**
preregistration rather than assumed.

**Measured on `experiments/hostile_core_stress/reader.py`:** 18 top-level
definitions; transport-specific literals appear in exactly **2** of them
(`_orientation_injectivity`, which names `"velocity"`; and
`recover_resolution_criterion`, which computes a cell Péclet number). The
remaining **15 introspect `engcore.scientific` contracts generically** —
dataclass fields, enum members, serialized payloads — and name no transport
quantity.

**Verdict: the assumption HOLDS and ALT-1 proceeds.** The shared instrument is
written **fresh** for this milestone rather than by editing the hostile reader,
because that package is committed evidence for an accepted milestone and must
stay byte-unchanged.

**Binding:** if a per-consumer reader is written instead, the milestone stops and
re-scopes to ALT-2. This is fail condition 11.

---

# 4. The four frozen consumers

## Consumer A — Structural / Mechanical: two-element plane-stress patch

Unit square `[0,1]²` m, thickness `t = 0.01 m`, split along one diagonal into
two constant-strain triangles. **Four nodes, eight DOF.** Linear isotropic,
`E = 210 GPa`, `ν = 0.3`.

```text
ε = B u            B is 3×6, constant per element
σ = D ε            D = E/(1−ν²) · [[1, ν, 0], [ν, 1, 0], [0, 0, (1−ν)/2]]
K = Σ_e t·A_e·Bᵀ D B
```

* **CASE A1 — patch test.** Prescribed uniform uniaxial displacement on the
  right edge, `u_x = 0` on the left, one `u_y` restraint. Verified by requiring
  the recovered `σ_xx = E·ε_xx` to machine precision **in both elements**, and
  `σ_yy = σ_xy = 0`.
* **CASE A2 — shear.** Verified by nodal force equilibrium `Σ F = 0` to machine
  precision and by reciprocity `K = Kᵀ`.
* **CASE A3 — representation only, no solve.** The *same* geometry, material and
  loads restated under **plane strain**, whose `D` differs and whose
  `σ_zz ≠ 0`.

**Isomorphism check.** A 1D bar, spring chain or pin-jointed truss **would be
isomorphic to the existing `electrical/dc` MNA solve** — stiffness ↔
conductance, displacement ↔ node potential, force ↔ current, fixed node ↔
reference node. That is the pipe-network trap and it is why a 1D bar is
rejected. The 2D patch breaks the isomorphism on three counts a records reader
can measure: the primary unknown is **rank-1 with two components per node**
(MNA has one scalar per node); the derived quantity is a **rank-2 symmetric
tensor with three independent components** (MNA derives a scalar branch
current); the constitutive law is a **matrix** (MNA's is a scalar conductance).

**Explicitly not built:** shape-function framework, quadrature abstraction,
element library, mesh reader, refinement study.

## Consumer B — Fluid / Transport: 2D steady advection-diffusion, minimised

Domain `[0,1]²`, structured cell-centred grid, **two resolutions only**
(`8×8`, `16×16`).

```text
∇·(u c) − D ∇²c = s(x, y)
u = ω(−(y−½), (x−½))      analytically divergence-free,  ω = 1 s⁻¹
D = 0.01 m²/s
```

**One** discretization: first-order upwind advection, central diffusion.
Reference: **method of manufactured solutions** — a smooth `c*(x,y)` is chosen
and `s` derived analytically, giving an exact reference at every point at
essentially zero extra cost. `s` is itself a **second field-valued input**.

All four sides are declared as **four distinct regions**, each with a
`BoundaryCondition` record. The physically correct assignment — Dirichlet where
`u·n < 0`, homogeneous Neumann where `u·n > 0` — **varies along each side**
because the flow rotates.

* **CASE B3 — representation only.** Reverse `ω` and measure whether any
  serialized record changes. The 2D generalisation of `HOSTILE-CORE-STRESS` R1a.

**Isomorphism check.** It shares the transport operator with
`hostile_core_stress`, and **that overlap is conceded in advance, not
discovered.** It differences on four measurable counts: the inflow set is a
*subset of each boundary determined by a sign that varies along it* rather than
a choice between two endpoints; the velocity is a **field-valued model input**;
the support is 2D with a connectivity `length` cannot express; and the source
term is a second field-valued input.

**Explicitly not built:** unstructured meshes, a second scheme, a refinement
ladder beyond two grids, transient behaviour, nonlinearity, momentum, pressure.

## Consumer C — Chemical / Species: closed isothermal batch, three species

```text
(R1)  A ⇌ B        first order both directions,  k₁f, k₁r
(R2)  2B → C       second order in B, irreversible,  k₂
```

Isothermal at 320 K, constant volume, **no flow**. State `(c_A, c_B, c_C)`, all
mol·m⁻³. Stoichiometric matrix `ν = [[−1, +1, 0], [0, −2, +1]]`.
Rates `r₁ = k₁f·c_A − k₁r·c_B`, `r₂ = k₂·c_B²`; `dc/dt = νᵀ r`.

**The conserved quantity is `c_A + c_B + 2c_C`** — weighted, so it **cannot be
recovered without `ν`**. That is the whole measurement.

Verified by: (i) invariant drift to machine precision, independent of
integration accuracy; (ii) a closed-form check on the `k₂ = 0` sub-case, a
linear reversible pair with an exact solution and known equilibrium
`c_B/c_A = k₁f/k₁r`; (iii) a tolerance-refinement pair.

**Isomorphism check.** The existing `kinetics/cstr` is **non-isothermal**, with
two coupled ODEs of *different dimensions* (mol·m⁻³ and K), Arrhenius `k(T)`,
stiffness, steady-state multiplicity, and **a single tracked species with B
never represented anywhere**. C removes every one of those and adds what the
CSTR structurally lacks: three dependent quantities **of the same dimension**,
**stoichiometry as data**, and a **conservation relation across the state
vector**. Isothermal is a deliberate cost paid to eliminate CSTR overlap;
**closed** is a second deliberate cost, paid to eliminate the shared lineage
with B that Modelica's stream-connector retrofit identifies (see §6).

**Explicitly not built:** energy balance, Arrhenius, flow, multiplicity,
equilibrium solver, thermochemistry database.

## Consumer D — Controls / Dynamics: planar pendulum in Cartesian coordinates

A genuine constrained-dynamics DAE.

```text
states (x, y, vx, vy);   constraint  g = x² + y² − L² = 0   with multiplier λ
ẋ = vx      ẏ = vy      m·v̇x = −2λx      m·v̇y = −mg − 2λy
L = 1 m,  m = 1 kg
```

**Executed realization:** index-reduced to acceleration level with
Baumgarte/GGL stabilisation. **Represented, not executed:** the index-3
statement itself, and a third realization — the 1-DOF `θ`-form ODE
`θ̈ = −(g/L)·sin θ`, which is the *same scientific model with a different state
vector*.

* **CASE D1** — free swing from `θ₀ = 0.5 rad`. Verified by energy conservation,
  a constraint-residual `|g|` time series, agreement with the `θ`-form to a
  preregistered tolerance, and the small-angle analytic period.
* **CASE D2 — representation only.** A prescribed time-varying drive
  `τ(t) = τ₀·sin(Ωt)`, to expose that a time-varying input has no home in
  `ScientificParameter`.
* **CASE D3 — representation only.** Four `InitialCondition` records that
  individually validate and **jointly violate** `g = 0` and `ġ = 0`.

**Isomorphism check.** A PI-controlled first-order plant **would be isomorphic
to `thermal_lumped`** — one first-order ODE with a `CONTROL` variable — which is
why no controller appears here. Against `kinetics/cstr`: two coupled ODEs with
no algebraic relation among unknowns. D adds four things no other consumer and
neither control has: an **algebraic equation among unknowns** (distinct from
`ConstraintDefinition`, which is a metric-vs-bound *acceptance* test); a
**differential/algebraic variable partition**; initial conditions that are a
**relation** rather than independent values; and a realization that changes what
the unknowns **are** — where CD/UW and native/ngspice both kept the same
unknowns.

**Explicitly not built:** controller, generic control framework, multibody
library, event handling, hybrid systems.

---

# 5. The control group (RC-1) — binding

Every candidate concept is scored not only against A/B/C/D but against **two
existing domains as they stand today**:

```text
ctl-1   src/engcore/domains/electrical/dc/       (MNA network solve)
ctl-2   src/engcore/domains/thermal_lumped.py    (first-order lumped ODE)
```

This is the single strongest cheap defence against the selection-bias attack:
it converts *"the intersection of four consumers I chose"* into *"the
intersection of six, two of which I did not choose for this purpose and which
predate this milestone by several milestones."*

**No control-group file may be edited.** They are read and scored, nothing more.

---

# 6. Measured baseline facts

Read directly from this working tree at `222c437`, before any probe was written.
These are **facts**, and the predictions in §8 are stated against them.

| # | Fact | Location |
|---|---|---|
| **F1** | **Nothing mechanical or structural exists anywhere in `src/`.** A repo-wide grep for `stress\|strain\|displacement\|elastic\|tensor\|modulus\|poisson` returns only optimizer/torch and generic-constraint matches | repo-wide |
| **F2** | **`ModelFormulation.DAE` and `.DISCRETE` have zero production consumers.** Only `tests/` references. MODEL0-R evidence §9 item 7 already records them as *"still no consumer, still provisional"* | grep of all `ModelFormulation.` uses |
| **F3** | **`ScientificProblem` has no `data_references`.** That field exists only on `ScientificResult` and `RawSolverOutput`. A **field-valued input** has no typed home in any problem statement | `results/result.py:74`, `solvers/protocol.py:177` |
| **F4** | `InputSourceKind` has exactly two members, `VARIABLE` and `PARAMETER`. A model cannot declare a condition, a field, or a structural relation as an input | `models/definition.py:377-381` |
| **F5** | `ScientificValue` is a closed union of scalars, so `ScientificParameter` **cannot carry a matrix, an array or a table** — no stiffness matrix, no stoichiometric matrix, no velocity field | `ir/values.py` |
| **F6** | `InitialCondition.value` is **one** `Quantity`, with no relation to any other variable and no consistency notion | `ir/conditions.py` |
| **F7** | `ConstraintDefinition` is `metric OP bound` with a scalar bound — a **study-level acceptance constraint, not an algebraic relation among unknowns**. Load-bearing for Consumer D | `ir/constraints.py` |
| **F8** | `BoundaryCondition` has **zero producers in `src/engcore/domains/`**; `region` is documented as opaque and uninterpreted | `ir/conditions.py` |
| **F9** | `ScientificVariable` has no rank, no component index, and no differential/algebraic marker. `VariableRole` is `{DESIGN, STATE, OBSERVABLE, CONTROL}` | `ir/variables.py` |
| **F10** | `electrical/material.py` already implements a **state-dependent scalar** material property `R(T)` and its docstring argues explicitly why no `MaterialProperty`/`PropertyRequirement` hierarchy was needed. **The scalar case is answered** | `domains/electrical/material.py` |
| **F11** | No chemical composition concept exists in `src/`. A grep for `stoichiom\|species\|composition\|mole_fraction` returns only *system* composition (`QuantityDependency`) — a genuine naming collision | repo-wide |
| **F12** | `ScientificTwin` is consumed by `src/engcore/design/generation.py` as `TwinKind.CANDIDATE`, **not** as runtime-state authority. §65.3/§66.3/§67.4 record zero evidence for the instance-authority role across three consecutive milestones | `design/generation.py` |
| **F13** | `ProvenanceRecord.inputs` is `Mapping[str, Quantity]`, typed and serialized — the channel `HOSTILE-CORE-STRESS` found for a computed validity input | `results/provenance.py:167` |

---

# 7. The instrument

One shared records-only reader, written fresh for this milestone.

* It is handed **serialized payloads** and nothing else.
* It may import `engcore.scientific` — a records reader legitimately knows its
  schema.
* It **may not import any probe module**, asserted by AST scan, exactly as
  `HOSTILE-CORE-STRESS` asserted it.
* Every verdict is derived **structurally** — from dataclass fields, enum
  members and serialized payloads — never from the author deciding what feels
  recoverable.

Per consumer, each candidate concept is classified into exactly one of:

```text
FULLY REPRESENTABLE
AMBIGUOUS
IMPOSSIBLE
REQUIRES METADATA
REQUIRES SOURCE-CODE KNOWLEDGE
```

and in the coverage matrix into **F** (forced), **P** (pressured), **–** (not
touched).

## 7.1 Carried forward verbatim (RC-5)

**The steelman requirement.** No gap may be declared for any consumer before a
maximal honest attempt to express it in existing typed contracts. A gap declared
without one is **fail condition 4**. Given F3, F5, F7 and F8, several encoding
attempts per consumer are expected and **some are expected to succeed** —
`HOSTILE-CORE-STRESS`'s most valuable outputs were the two claims it withdrew.

**The two-ledger booking rule.**

> A finding is **Ledger 1 only when BOTH the measurement AND the remedy live in
> a record that already exists.** If closing the gap requires a record the
> platform does not have, the finding is Ledger 2 — however interesting the
> measurement, and whichever record it was taken on.

Findings that straddle the line are **split**, not rounded.

---

# 8. The predicted coverage matrix — preregistered so it can be wrong

**F** forced · **P** pressured · **–** not touched. Control columns are the
existing domains as they stand today.

| # | Candidate concept | A patch | B transport | C batch | D pendulum | ctl dc | ctl lumped |
|---|---|---|---|---|---|---|---|
| 1 | ScientificField | **F** | **F** | – | – | – | – |
| 2 | FieldSupport | **F** | **F** | – | – | – | – |
| 3 | Domain / Topology | **F** | **F** | – | – | P | – |
| 4 | BoundaryIdentity | **F** | **F** | – | – | P | – |
| 5 | BoundaryOrientation — as sign | P | **F** | – | – | P | – |
| 6 | BoundaryOrientation — as vector normal | **F** | – | – | – | – | – |
| 7 | BoundaryCondition record adequacy | P | **F** | – | – | – | – |
| 8a | Rank-1 (vector) quantity semantics | **F** | P | – | **F** | – | – |
| 8b | Rank-2 symmetric tensor semantics | **F** | – | – | – | – | – |
| 9 | Field-valued **model input** | – | **F** | – | – | – | – |
| 10 | Constraint — algebraic relation among unknowns | – | – | P | **F** | – | – |
| 11 | Differential/algebraic variable partition | – | – | – | **F** | – | – |
| 12 | Relational / consistent InitialCondition | – | – | – | **F** | – | – |
| 13 | DynamicState | – | – | **F** | **F** | – | **P** |
| 14 | MaterialIdentity | P | P | P | – | P | P |
| 15 | MaterialState | – | – | – | – | **P** | – |
| 16 | PropertyRequirement — scalar | – | – | – | – | **P** | – |
| 17 | PropertyRequirement — rank-2 / anisotropic | **F** | – | – | – | – | – |
| 18 | SpeciesIdentity | – | – | **F** | – | – | – |
| 19 | Composition (chemical) | – | – | **F** | – | – | – |
| 20 | ReactionRelationship / stoichiometry as data | – | – | **F** | – | – | – |
| 21 | CausalPort | – | – | – | – | – | – |
| 22 | PhysicalConnector | – | – | – | – | – | – |
| 23 | DiscretizationDefinition | P | P | P | P | – | P |
| 24 | RuntimeState | – | – | – | P | – | – |
| 25 | Event | – | – | – | – | – | – |
| 26 | QuantityIdentity (N instances of one kind) | P | P | P | P | **P** | – |
| 27 | Admissibility **attainment** on the ValidationLevel ladder | **F** | **F** | **F** | **F** | P | – |

## 8.1 Preregistered readings, each falsifiable

* **P-1.** Each consumer forces at least **three** concepts no other of the four
  forces: A → {6, 8b, 17}; B → {5, 7, 9}; C → {18, 19, 20}; D → {10, 11, 12}.
  **If any consumer's unique count falls below three, that consumer was
  redundant** and the evidence document must say so.
* **P-2.** Rows **21, 22, 25** are all-dash **by construction** — no consumer is
  a coupled system and none has a discontinuity. **Any non-dash there is an
  instrument error, not a discovery.**
* **P-3.** Rows **15, 16** are forced by **none** of the four and pressured only
  by the control — a direct test of `electrical/material.py`'s recorded "no
  property hierarchy needed" argument (F10).
* **P-4.** Row **26** comes back **P, not F, everywhere including the control**,
  because `electrical/dc` already names per instance and `ET-VERTICAL` §65.2
  records that this works.
* **P-5.** Row **27** is the highest-expected-value single outcome. Four
  independent admissibility checks exist almost for free — A's patch-test
  exactness and `Σ F = 0`, B's MMS error bound, C's exact conservation
  invariant, D's constraint residual and energy conservation.
  `HOSTILE-CORE-STRESS` deferred the admissibility `ValidationLevel` member
  *specifically for want of a second consumer*; this supplies four across four
  families plus a control.
* **P-6.** The **A/B block (rows 1–4) duplicates.** Conceded in advance, not
  discovered. It is the price of the founder's fixed four families and it is why
  B is minimised — A already pays for most of the 2D/topology/boundary block.

## 8.2 Predicted negatives are a fail condition (RC-2)

At least three concepts are predicted **not forced by any consumer**:
**MaterialState (15)**, **scalar PropertyRequirement (16)**, **Event (25)**,
plus **CausalPort (21)** and **PhysicalConnector (22)** by construction.

> **If the matrix returns "everything is universal", the instrument cannot
> discriminate and the milestone has FAILED**, regardless of how the findings
> read. This is fail condition 5.

## 8.3 Pre-committed selection-artifact list

Named **before** execution so the falsifier's strongest attack is attackable
rather than fatal. The attack will be: *"every concept in your universal column
is forced by all four because you selected each consumer partly because it had
that property."* It is partly correct — C was chosen to have multiple
same-dimension unknowns, and D was chosen to have a constraint.

**The rows most exposed are 26 and 27.** The distinguishing evidence for row 27
is stated in advance: the four admissibility checks are of **four structurally
unrelated kinds** — an exactness identity, a discretization error bound, an
exact conservation invariant, and a constraint residual. That is much harder to
attribute to a common selection criterion than four instances of one kind.

---

# 9. Universality classification

Every candidate concept is classified exactly once:

```text
UNIVERSAL-CANDIDATE     forced by multiple materially different consumers
CROSS-DOMAIN-CANDIDATE  forced by two, or forced by one and pressured elsewhere
DOMAIN-SPECIFIC         forced by one family only
LIKELY-FORCED           strong pressure, no clean forcing measurement
DEFER                   not forced; revisit with a named future consumer
REJECT                  no consumer forces it and none is foreseen
```

## 9.1 The cross-domain reduction attack — required

For every candidate universal concept, ask explicitly: **can A work without it?
B? C? D?**

> If **only one** consumer requires it → default to **domain/local placement**
> unless there is a strong recorded architectural reason otherwise.
>
> If **multiple unrelated** consumers independently require the same semantic
> distinction → mark it a strong candidate for the next universal foundation.

---

# 10. Required attacks

1. **`Quantity`.** Do **not** turn it into a vector/tensor/field bulk container.
   Test whether **rank** belongs to `Quantity` semantics, to Field semantics, or
   to another layer entirely. Consumer A is the instrument: it has a rank-1
   unknown and a rank-2 derived quantity in one problem.
2. **`ScientificDataReference`.** Preserve
   `ScientificDataReference != ScientificField`. Do **not** solve field
   semantics by expanding storage identity.
3. **`ScientificTwin`.** Do not assume it is runtime-state authority. Measure
   whether **any** of the four consumers forces that role. F12 records that it
   has a real consumer in a *different* role. A fourth consecutive milestone at
   zero evidence for instance authority must be recorded as such.
4. **`MODEL0-R`.** Preserve the frozen separation. Determine whether controls,
   mechanics and transport expose missing semantics — in particular whether
   Consumer D's `θ`-form realization, which **changes what the unknowns are**,
   is expressible.
5. **Coupling.** Do **not** generalize the existing fixed-point engine. Ask only
   what *types* of relationship the four consumers would need. No
   `QuantityDependency` is declared.

---

# 11. What is forbidden

Absolute. Violating any of these invalidates the evidence.

1. **No new universal contract** in `src/engcore/scientific/`.
2. **No existing universal contract modified** to make a probe pass.
3. **No file under `src/engcore/domains/thermal/` added or edited** — byte-pinned
   by frozen T1/T2/T3 experiments.
4. **No control-group file edited** (§5).
5. **No file under `experiments/hostile_core_stress/` edited** — committed
   evidence for an accepted milestone.
6. **No domain-specific branch in universal core**, lexical or structural.
7. **No FIELD0, TOPO0, DISC0, structural domain, CFD, chemistry engine, controls
   engine, API/MCP, or planner.**
8. **No `QuantityDependency` and no coupling runtime.**
9. **No new evidence level invented**; no upgrade to any existing holding.
10. **No `MODEL0-R` evidence movement claimed** from Consumer D's three
    realizations. Same trap `HETERO-NGSPICE` §66.3 fell into and withdrew from:
    records constructed by a proof cannot differentiate a contract.

---

# 12. Required tests

1. Per-consumer representation classification, asserted as exact maps rather
   than prose.
2. The coverage matrix asserted cell-by-cell, so a later contract change moves
   the test rather than silently moving the evidence.
3. The preregistered negatives (§8.2) asserted as negatives.
4. Instrument integrity: AST scan proving the reader imports no probe module.
5. Physics integrity per consumer: A's patch test and `K = Kᵀ`; B's MMS error;
   C's conservation invariant drift; D's energy and constraint residual.
6. No bulk array in any scientific control record.
7. No universal-core edit, no thermal edit, no control-group edit, no hostile
   probe edit — asserted by `git diff`.
8. All existing milestone regressions green.

Run **TARGETED**, then **FAST**, then **FULL**. FULL is the gate.

---

# 13. Fail conditions

1. A file under `src/engcore/scientific/` was added or edited.
2. A file under `src/engcore/domains/thermal/` was added or edited.
3. A control-group file, or any `experiments/hostile_core_stress/` file, was
   edited.
4. A gap was declared for any consumer without the steelman attempt of §7.1.
5. **The matrix returns no negatives** — §8.2.
6. Ledger 1 and Ledger 2 findings were blended, or a Ledger 2 finding was
   reported as an evidence gain.
7. An evidence level above `L1` was claimed, or a new level invented.
8. Any existing holding was claimed to move.
9. A pre-existing test was edited or a tolerance loosened.
10. The FULL suite is not green.
11. A per-consumer reader was written instead of one shared instrument — §3.1.
12. A candidate concept was promoted to universal on the evidence of **one**
    consumer, without a recorded architectural reason.

---

# 14. Evidence ceiling, declared before running

```text
Coverage matrix                    at most  L0 REASONED + measured coverage
Any UNIVERSAL-CANDIDATE            at most  L0 + multi-consumer measured pressure
Any CROSS-DOMAIN-CANDIDATE         at most  L0 + measured pressure
The four probe packs' execution    at most  L1 EXERCISED
```

`L2` is excluded outright: one author, one interface, consumers selected
together for this purpose — §54.1's definition of "materially different"
explicitly excludes exactly that lineage. `L3` is excluded outright: no scale,
concurrency, latency or failure injection.

**No abstraction that was never implemented may be assigned `L1`.** A measured
coverage cell is evidence *about* a missing abstraction; it is not evidence
*for* a design that does not exist.

---

# 15. What the evidence document must refuse to claim

* That the coverage matrix proves any particular contract shape is correct.
* That a `UNIVERSAL-CANDIDATE` verdict authorizes implementation without its own
  preregistered milestone.
* That `DATA-BOUNDARY0`, `MODEL0-R`, `MIN-FOUNDATION-ET`, `ET-VERTICAL`,
  `HETERO-NGSPICE` or `HOSTILE-CORE-STRESS` gained evidence.
* That `ScientificTwin` gained evidence in **either** role.
* That four consumers written by one author on one branch constitute
  differentiation.
* That the A/B duplication in rows 1–4 is independent corroboration. It is not —
  §8.1 P-6 concedes it in advance.

---

# 16. Explicit exclusions — what the four together do NOT probe

**Any coupling whatsoever** — no `QuantityDependency`, no second problem, no
`ET-VERTICAL` or system-pack record touched; therefore **zero** evidence for
`CausalPort`, `PhysicalConnector`, fan-in, transfer between supports, coupling
convergence or `RuntimeState` · external providers, concurrency, latency, scale,
GPU, distributed ownership · 3D, unstructured meshes, adaptivity, mesh tags ·
nonlinear PDEs, turbulence, pressure–velocity coupling, saddle-point structure ·
time-varying **boundary** values on a field · **non-uniform `InitialCondition`**
(accepted loss under RC-4; already measured on the existing domain in
`HOSTILE-CORE-STRESS` §M) · events, discontinuities, state resets, hybrid
systems · mixtures, phases, materials databases · uncertainty, inference, UQ,
design, optimization · `ScientificTwin` as instance authority · schema migration
or long-lived-record evolution.

---

# 17. Placement

All four probe packs live under `experiments/cross_domain_coverage/`, outside
`src/`, so nothing can be promoted into production core by accident and nothing
ships with the package. A test asserts `git grep cross_domain_coverage -- src/`
returns nothing.

---

# 18. Stop rule

§60 applies: at most two adversarial rounds, then the milestone reports what it
measured.

**STOP once a defensible cross-domain coverage matrix exists.** Not one line
further.

---

# 19. Output

`docs/cross-domain-coverage-stress-evidence.md`, written **after** execution,
covering the twenty-two required sections. Nothing learned after this point is
back-written into this preregistration.

The deliverable is **a coverage matrix and a constrained next milestone**, not
architecture.
