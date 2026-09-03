# EXEC-SPEC STRUCTURED-INPUT STRESS — Evidence

**Milestone:** `EXEC-SPEC-STRUCTURED` — a narrowly-scoped reversal test of one
unresolved condition in `EXEC-SPEC`.
**Outcome:** **D — MIXED.** The two sciences share an *infrastructure* shape and
share no semantics.
**Effect on `EXEC-SPEC`:** **KEEP**, at `PROPOSED`, with its headline narrowed
and seven reversal triggers written down. It is **not** reopened.
**Evidence:** `L1 EXERCISED` for what executed; `L0 REASONED` — explicitly
**authored, not derived** — for every universality verdict. **`L2` not claimed.**
**Branch:** `exec-spec-structured-input-stress`, cut from `5c3962b`.
**Preregistration:** `docs/exec-spec-structured-input-stress-prereg.md`,
committed at `d744843` before any probe source was written. **Immutable.**

> Written after execution. Two preregistered predictions were falsified, one
> preregistered rule was overridden, and three of this milestone's own claims
> were falsified by its adversarial pass. All six are recorded below with the
> measurement that refuted them.

`docs/architecture-study/08_CRAFTY_SELF_AUDIT.md` is untracked, was not cited as
evidence, and is not committed by this milestone.

---

# A. The exact Mechanics consumer

`experiments/cross_domain_coverage/mechanics.py`, CASE A2 (shear), plane stress.
Committed at `38783ed`, **not edited**.

Unit square, thickness 0.01 m, split on one diagonal into two constant-strain
triangles. Four nodes, eight DOF, `E = 210 GPa`, `ν = 0.3`. Left edge clamped
(`CLAMPED_DOF = (0,1,6,7)`), `10 kN` applied in `+y` at each right-hand node.
`ε = Bu`, `σ = Dε`, `K = Σ t A Bᵀ D B`.

# B. The exact Species consumer

`experiments/cross_domain_coverage/species.py`, CASE C1. Committed, **not
edited**.

`A ⇌ B` (first order both ways) and `2B → C` (second order, irreversible),
closed, isothermal at 320 K. State `(c_A, c_B, c_C)`.

```text
nu = [[-1, +1,  0],
      [ 0, -2, +1]]     dc/dt = nu^T r,  r = (k1f c_A - k1r c_B,  k2 c_B^2)
```

The conserved quantity is `c_A + c_B + 2 c_C`. The **2** comes from `nu` and
nowhere else.

---

# C. Existing-contract reconstruction

Fifteen encoding attempts, all executed. No new universal record, no `src/`
change, `metadata` empty in both encodings (asserted).

| Column | Fact | Channel | Outcome |
|---|---|---|---|
| mech | constitutive matrix D | `ScientificParameter` | **refused-by-type** |
| mech | constitutive matrix D | (derivation) | **DERIVABLE** |
| mech | element connectivity | `ScientificParameter` | meaning-in-key |
| mech | which body is discretized | `ScientificParameter` | meaning-in-key |
| mech | node coordinates | `ScientificDataReference` | unlinked-bulk |
| mech | constrained DOF | `BoundaryCondition` | meaning-in-key |
| mech | applied load + its DOF | `ScientificParameter` | meaning-in-key |
| species | stoichiometric matrix ν | `ScientificParameter` | **refused-by-type** |
| species | stoichiometric matrix ν | `ScientificParameter` (six named ints) | meaning-in-key |
| species | stoichiometric matrix ν | `ScientificDataReference` | unlinked-bulk |
| species | species identities | `ScientificParameter` (categorical) | meaning-in-key |
| species | species identities | **`ScientificVariable`** | meaning-in-key |
| species | initial composition | `InitialCondition` | **works** |
| species | rate constants | `ScientificParameter` | **works** |
| species | conserved combination | (derivation from ν) | unlinked-bulk |

Two results carry the milestone.

**C.1 — D is NOT residue.** `constitutive_matrix()` takes `youngs_modulus_pa`
and `poisson_ratio` as arguments, so `D = f(E, ν, plane_assumption)` — two
`Quantity` parameters and one `CategoricalValue`, all representable today.
Recomputed from reconstructed records: **worst element difference 0.0**.

*Scope, corrected after review:* D is derivable whenever the constitutive law is
a closed-form function of **named scalars plus a category** — which includes
orthotropic and transversely isotropic laws, not only isotropic ones. What
breaks derivability is (a) fixed-arity component **ordering** once the constant
count makes name-keying unmanageable, (b) a **material frame**, which no contract
states, and (c) a **field-valued or state-dependent** property. None is measured
here.

**C.2 — ν IS residue, derivable from nothing.** The conserved weights were
recovered from the **SVD null space of the reconstructed ν**, with
`species.CONSERVED_WEIGHTS` never read on that path: measured
`(1.0, 1.0, 1.9999999999999991)`.

*Scope, added after falsification:* the recovery refuses anything but a
one-dimensional conserved space, and where the space is larger the SVD returns an
arbitrary orthonormal basis rather than the chemically meaningful non-negative
integer moiety vectors. The claim the measurement supports is **"ν determines the
conserved subspace"**, not "ν yields the weights".

---

# D. Fresh-process results

Both columns reconstruct and execute in a **separate interpreter**, launched with
`-B`, given JSON files and a column name.

| | mechanics | species |
|---|---|---|
| probe modules loaded in the child | **[]** | **[]** |
| encoding/bridge modules loaded | **[]** | **[]** |
| grade | **injected** | **injected** |
| agreement with the committed probe | ≤ 1e-9 relative, all metrics | ≤ 1e-9 relative, all metrics |
| conservation drift, computed in the child | — | 2.3e-14 |

**The isolation is structural, and it was not at first.** See §N, BLOCKER 1: the
guard inherited from `EXEC-SPEC` filtered for an `encodings` module, but in this
milestone the ground truth lives in the *committed probes'* module constants, and
`bridge` imported both probes. The child held the answer while its reported
metrics were computed by `mech.run_shear_case()` and `spc.integrate()` — the
probe compared against itself in two processes. The fix splits reconstruction and
computation into `inject.py`, which imports no probe, from comparison in
`bridge.py`, which runs in the parent only; the child reports its own
`experiments.cross_domain_coverage` module list and the parent asserts it empty.

**INJ-2** (species): `dc/dt = νᵀr` integrated from the reconstructed coefficients
reproduces the probe's final state to 1e-9.
**INJ-3** (mechanics): the 8×8 stiffness assembled and the shear system solved
from the reconstructed mesh, thickness and injected D; element stresses recovered
from the same. **Not preregistered — a declared deviation, §S, D-3.**

**What INJ-2 and INJ-3 establish, stated precisely.** Both are
operation-for-operation transcriptions of the probes' own arithmetic, so given
equal inputs a zero difference is **entailed, not corroborating**. What they do
establish is **executability from records** — the record set is sufficient to
compute — plus one genuine measurement: `assemble_from_records` refuses a
non-positive signed area, which makes vertex order load-bearing as a fact rather
than an assertion.

---

# E. Mechanics residue

Five items, each with the nine §10 attributes.

| Fact | Class | changes identity | only discretization | bulk | scales |
|---|---|---|---|---|---|
| node coordinates (N×2, metres) | domain-structure | yes | no | **yes** | yes |
| **which body is discretized** | domain-structure | yes | no | no | no |
| element connectivity (E×3, ordered) | discretization | **yes** | **yes** | yes | yes |
| constrained DOF set | non-scalar structure | yes | no | no | yes |
| applied load + its DOF indexing | non-scalar structure | yes | no | no | yes |

**Connectivity carries both attributes, and that is a falsified correction.** A
first correction recorded `changes_scientific_identity=False` — a refinement
leaves the science alone. The adversarial pass refuted it from inside this
milestone's own executed path: hold the four corner coordinates fixed, drop one
element, and every guard passes while what assembles is a **triangular plate**.
A different body, from a connectivity edit alone. Executed in
`test_connectivity_carries_body_identity_in_the_representation_measured`.

The model/discretization split is therefore a statement about a representation
Crafty **does not have**. It separates only once a topology/geometry object exists
against which a mesh can be checked as one of its refinements — synthesis §17.6
*"Topology/Geometry ≠ discretization-specific mesh view"*, OpenFOAM study
Candidate N. This milestone built none, and in the representation measured,
connectivity carries identity.

**"Which body" has no carrier.** A first note said "the node set stands in for
one". A point set has no extent — the body is the union of the element closures —
so the node set cannot hold it and the connectivity still absorbs it.

---

# F. Species residue

| Fact | Class | changes identity | bulk | scales |
|---|---|---|---|---|
| stoichiometric matrix ν (R×S signed ints) | constitutive-relation | yes | **no** | yes |
| species identities, in state order | non-scalar structure | yes | no | yes |

**The species-identity item narrowed under attack, and the narrowing is a
strengthening.** `Channel.VARIABLE` was declared in the steelman and never
attempted — a §13.4 trip, and exactly the check `HOSTILE-CORE-STRESS` records as
the one that catches a false gap. Executed now: a categorical
`ScientificVariable` carries an **ordered** tuple of named members that
round-trips deterministically (`categories` → `list` → `tuple`). So an ordered
index set of named entities **is** representable in universal core today, and
this milestone's first reading was wrong.

What remains is the **binding**: no record states that this ordering is the one
indexing ν's columns or the state vector. `rebuild_species` demonstrates it by
construction — it reads `species_order` from a domain payload and **refuses** a
transposed `stoichiometry_axes` rather than guessing, because nothing in the
numbers says which axis is reactions.

**ν is excluded from DATA-BOUNDARY0 because it is a model, not because of its
dtype.** A first note argued partly from integer coefficients being widened to
float64. `SUPPORTED_DTYPES == {float64}` applies identically to the mesh
connectivity, so that argument does not separate them and is **withdrawn as
corroboration**.

---

# G. Overlap analysis

**Outcome D — MIXED.**

**Shared semantics — one statement, and it is about results rather than inputs:**

> an array of values must be able to name the variable(s) and the component
> ordering it instantiates — `VariableToBulkLinkage`.

Mechanics needs it for an 8-value displacement over 4 nodes × 2 components;
species needs it for a 3-value state over 3 named species. `ScientificDataReference`
carries `{name, unit, count, dtype, digest}` and no such field; `count` is
documented as *"not a shape"*. This is already forced 4/4 by
`CROSS-DOMAIN-COVERAGE` and is `MIN-FOUNDATION-PDE`'s strongest input — this
milestone corroborates it from two more consumers and claims nothing new.

**Shared infrastructure — three, none carrying a scientific claim:** an ordered
index set of named entities whose order is load-bearing; an integer table
relating two such sets; schema string + deterministic serialization + content
digest.

**Not shared — five:** what the coefficients mean (molar ratio vs vertex
membership); what follows from them (a conservation law vs an assembly rule);
whether the structure is a model or a discretized geometry; continuous
coordinates (mechanics has them, species has none); derivability (D is computed
from two scalars, ν from nothing).

---

# H. The matrix-shape false-universality attack

The preregistered primary attack and its mirror were both run. The mirror — *did
you manufacture a difference between two things that are the same?* — is the one
that mattered, and the falsifier's verdict was that the difference is real.

**Candidate B (generic relation/coefficient artifact) is rejected on ALGEBRAIC
TYPE**, not on prose:

* ν's entries are **signed molar coefficients**. Null-space arithmetic on them is
  meaningful and yields a conservation law with units of mol/m³ — measured.
* Element–node entries are **ordinal positions** indexing a coordinate array. The
  null space of that table is the set of nodes no element references — mesh
  hygiene, not a statement about the body.

**A factual premise was corrected.** This milestone initially claimed Crafty's DC
domain contains an oriented incidence matrix, making a third data point. **It does
not.** `electrical_dc_circuit/1` stores typed components with semantically
distinct terminal roles — `node_a/node_b`, `positive_node/negative_node`,
`from_node/to_node` — and `circuit.py` records that terminal order must not be
flattened because swapping it must produce a different identity. A generic ±1
incidence table erases exactly the distinction `HETERO-NGSPICE`'s passive-sign
guard needed. The third data point was an inference presented as a fact.

**Control-system matrices (A,B,C,D) were tested as the strongest counterexample
and do not flip the verdict.** For linear kinetics `r = Kc`, so
`dc/dt = (νᵀK)c` and `A = νᵀK`: the control matrix is the reaction network's own
linearisation. It adds no independent lineage.

**One rule is recorded as unsound and is not relied on.** "Shared mathematical
ancestor ⇒ discount the data point" is structurally one-directional: it can only
ever reduce the count of sciences agreeing that an abstraction is forced, never
increase it. Applied evenhandedly it also cuts against this milestone's own
separation — element–node connectivity and reaction–species stoichiometry are
both bipartite incidence relations between two named entity sets. **The rejection
of candidate B rests on the algebraic-type argument alone**, which does not depend
on ancestry and which held under attack.

**The candidate table is `L0 REASONED` and carries near-zero evidential weight.**
Its rejection test asks whether a planner could act on an abstraction's
*semantics*, so the only candidate that can pass is the one making no semantic
claim — the incumbent. That is confirmation-shaped, it is labelled as such in
source, and a test asserts the label. The load-bearing evidence is §C.1 and §C.2.

---

# I. VariableToBulkLinkage result

**Forced by both columns, identically, and it is the strongest shared result.**
Mechanics: which `ScientificVariable` does an 8-value displacement array
instantiate, and in what component order? Species: which variables does a
3-value state or an N×3 trajectory instantiate? Neither is answerable from a
reference carrying `{name, unit, count, dtype, digest}`.

The measurement adds one thing to §68.2's 4/4: the **ordered index set** half is
representable today (§F), so what is missing is a *binding*, not a container.
That is a smaller and more precisely scoped thing to build.

---

# J. Relation / coefficient result

The distinction the milestone was asked to draw:

> The missing universal concept is **not** "matrix-valued data". It is that a
> **typed scientific relation references structured coefficients whose axes are
> named index sets**.

ν is a relation (`dc/dt = νᵀr`) whose coefficients happen to form a matrix. D is
a relation (`σ = Dε`) whose coefficients are **generated** from two scalars. The
connectivity is not a relation at all — it is an addressing scheme. Three
different things with one numerical shape.

**No Equation IR was built and none is recommended by this measurement.**

---

# K. SolverSettings classification

Per column, as §13 of the brief requires:

| Column | Numerics | Classification |
|---|---|---|
| mechanics | **none** — a direct dense linear solve, no tolerance, no step count | **not applicable**; no gap to classify |
| species | `n_steps = 2000`, RK4 fixed step | **EXECUTION SPEC GAP** — it materially determines the result and has no persistable home |

It is **not** a scientific-spec gap: the step count is not part of the statement
of the chemistry. It is **not** merely a provenance gap: provenance records what
*was* used, and this is needed *before* a run to reproduce it. `SolverSettings`
is typed and round-trips, and is a field of runtime-only `PreparedSolve` — the
gap `EXEC-SPEC` measured on its own kinetics column and did not close.

**A correction was forced here.** The numerics first travelled *inside* the
digested species structure payload, which collapsed a distinction the
preregistration declared binding and made the relocation identity digest cover a
solver choice: two payloads differing only in step count would have had different
scientific identities. They now travel as a separate `numerics` payload, outside
the structure digest, and a test asserts it.

---

# L. Planner inspectability

The five per-consumer questions, from records, without importing domain code:

**Mechanics** — which entities are connected: **recoverable** (element→node
incidence with vertex order). Which variable components are unknown:
**AMBIGUOUS** — eight scalar STATE variables named `u_x:n0`…, and nothing says
that pairs of them are components of one vector at one node. What constraints
exist: recoverable as DOF indices, meaningful only with the payload's own
`dof_index_rule`. What constitutive behaviour: recoverable (two scalars + a
category; the matrix they generate is on no record, correctly). Capabilities:
recoverable.

**Species** — which species exist, which reactions connect them, what
stoichiometric relationship, what state variables evolve, what capabilities: all
**recoverable**, every one of them from the domain payload rather than from core
records.

**The cost, measured for the first time.** `EXEC-SPEC` recorded option E's
*domains × consumers* cost as unmeasured. Two new consumers required **one
hand-written reader branch each**; the committed `EXEC-SPEC` reader returns
`IMPOSSIBLE — "does not know this schema"` for both columns unextended, asserted
by test.

**What that argues for, and the limit on the argument.** It argues for
**publishing** domain schemas — `ModelInputSpec`/`ModelRegistry`, already named in
`EXEC-SPEC` BLOCKER 3 — rather than unifying them: a generic structured record
would remove the field-spelling branch and leave the *meaning* branch intact, so
a reader would still need to know that axis 0 is reactions and that vertex order
fixes a signed area. **This comparison was reasoned, not measured** — the
universal-record branch was never written — and is recorded as `L0`.

---

# M. Architecture reviewer verdict

`architecture-decision-reviewer`, invoked after the residue table existed:
**ACCEPT WITH CHANGES — do not reopen.**

Its reasoning: the measurement does not clear `EXEC-SPEC`'s own reopen bar (≥ 2
columns with a same-shaped Ledger-1 residue), because mechanics produced **no**
constitutive-matrix residue. One coefficient-table residue, not two.

Eight required changes, all applied: re-ground candidate B on algebraic type and
correct the DC premise (R1); split the connectivity item so the table carries the
distinction (R2); withdraw the DATA-BOUNDARY0 dtype asymmetry (R3); label the
candidate table as near-zero weight (R4); correct the anisotropy scope (R5);
record the reader cost as pointing at schema publication with its multiplier
unmeasured (R6); enforce the decorative mechanics payload fields (R7); restrict
mechanics claims to what the grade supports (R8 — discharged by running INJ-3).

It also rejected **Alt-4 (reopen + adopt candidate B)** on scientific
correctness, breaking-change risk, reversibility and serialization, and
recommended combining KEEP with a **narrowed headline** and an explicit handoff
of the ordered-index-set question to `MIN-FOUNDATION-PDE`.

---

# N. Falsifier verdict

`architecture-falsifier`: **FALSIFIED** — 3 BLOCKERs, 6 BREAKING-RISKs, all
against the evidential record rather than the executed science. All nine
corrections applied before commit.

**BLOCKER 1 — the fresh-process isolation guard checked the wrong module.**
`bridge` imported both probes; the child therefore held the ground truth, and its
reported `metrics` were computed by `mech.run_shear_case()` / `spc.integrate()`
rather than from records. TEST F's metrics half was consequently **vacuous** for
both columns. A regression against `EXEC-SPEC`, where the isolation was real.
**Closed** by the `inject`/`bridge` split, a guard pointed at
`experiments.cross_domain_coverage`, and metrics computed from injected
quantities. TEST F's metrics half is now non-vacuous.

**BLOCKER 2 — `changes_scientific_identity=False` for connectivity was
falsified** by the triangular-plate counterexample. **Closed** by recording both
attributes True, citing §17.6/Candidate N as the target, and executing the
counterexample as a test.

**BLOCKER 3 — `overlap()` and `shared_semantics()` claimed a derivation they did
not perform.** A dead `if mech_facts and species_facts: pass` branch read the
tables and did nothing; the returned statement was appended unconditionally; the
verdict was a hard-coded literal, and a test asserted the literal. A §13.9 trip.
**Closed** by deleting the dead branch, relabelling both as `L0 REASONED —
AUTHORED`, and renaming the test.

**BREAKING-RISKs, all closed:** the `ScientificVariable` channel declared and
never attempted, and the false ordering claim it exposed (§F); P-2 falsified and
recorded as such (§S); INJ-3's deviation under-declared (§S); INJ-3's "exactly
0.0" reported as corroboration when it is entailed (§D); `analogue_in_other_column`
recorded one-directionally with a dangling target; numerics inside the digested
structure payload (§K).

**What the falsifier explicitly did not find.** The algebraic-type argument held
under direct attack and under the control-matrix counterexample. The corrected DC
claim is right. C.1's derivability is genuinely executed and correctly scoped.
The convention-field enforcement is real. The axis-order refusal is the right
control. No abstraction was smuggled: no new record, `metadata` empty, schemas
named for the milestone rather than the domain.

**Its closing judgement on the mirror attack:** *"You did not manufacture a
difference between two things that are the same… What you did manufacture is the
model-versus-discretization framing of that difference."* That framing is
withdrawn in §E; the difference is retained where it is real.

---

# O. Exact impact on the EXEC-SPEC decision

**KEEP. `EXEC-SPEC` stays `PROPOSED` / `L1 EXERCISED`. It is not reopened.**

Two changes to how it is stated:

1. **The headline is narrowed.** From *"no universal executable-specification
   record"* to: *no universal executable-specification record **is forced by the
   four scalar/lumped production domains, nor by these two non-scalar
   consumers***. The structured-input case is measured, not settled.
2. **`VariableToBulkLinkage` is explicitly outside it.** A universal record **is**
   forced elsewhere — 4/4 consumers, §68.2, now 6/6 — and this measurement
   neither weakens nor competes with it.

**Seven reversal triggers, written down so a future consumer fires them rather
than re-litigating:**

| # | Trigger | Fires |
|---|---|---|
| **T1** | A consumer whose Ledger-1 residue is a coefficient table over two named index sets **and** whose coefficients support the same planner operation as ν's (a null space, an invariant, a balance). **Two such, in different sciences ⇒ REOPEN.** An anisotropic-material domain does **not** fire this; a bond-graph, multi-reaction electrochemistry, or combustion domain would | `EXEC-SPEC` reopen |
| **T2** | A domain forces a fixed-arity ordered component convention names cannot carry (Voigt beyond four constants, rank-1 nodal vectors, component-ordered arrays) | `VariableToBulkLinkage` + ordered-index binding, inside `MIN-FOUNDATION-PDE` |
| **T3** | A **second** records-only consumer (API/MCP, a planner, a UI) must read a domain structure payload | schema **publication** (`ModelInputSpec`/`ModelRegistry`), not a universal record |
| **T4** | Any domain structure payload is stored durably or crosses a process boundary not spawned by its own test | the `require_schema` migration route must be decided **first** |
| **T5** | A structure payload exceeds whole-structure-in-memory, or becomes 1:N heterogeneous | `EXEC-SPEC` BREAKING-RISK 3, unchanged |
| **T6** | Falsification shows the residue labels rather than the measurements carry a verdict | restate as UNDECIDED. **Partially fired here**; discharged by §E and §H |
| **T7** | A constitutive relation appears that is not a closed-form function of named scalars plus a category — field-valued, state-dependent, or tabulated | a `MaterialPropertyModel` question, not an `EXEC-SPEC` reopen |

---

# P. Evidence levels

| Claim | Level |
|---|---|
| D is derivable from records; worst difference 0.0 | **`L1 EXERCISED`** |
| ν is not derivable; its null space yields the conserved subspace | **`L1 EXERCISED`** |
| Both columns reconstruct and execute in a fresh process from records, probes absent | **`L1 EXERCISED`** |
| INJ-2 / INJ-3 executability from records | **`L1 EXERCISED`**; agreement entailed, not corroborating |
| Relocation preserves the structure digest | **`L1 EXERCISED`** |
| The reader needed one branch per schema | **`L1 EXERCISED`** |
| Outcome D; the shared/not-shared lists; the candidate rejections | **`L0 REASONED — AUTHORED`** |
| "The reader cost argues for publication not unification" | **`L0 REASONED`** — the comparison branch was never written |
| Anything about anisotropy, large networks, meshes, or scale | **not claimed** |

**`L2` is not claimed.** Two probes at four nodes and three species, reconstructed
by one author on one day against a bridge that author wrote, is exercise.

**Tests.**

| Tier | Before | After | Delta | Wall |
|---|---|---|---|---|
| targeted (`tests/test_exec_spec_structured_input.py`) | — | **55 passed** | +55 | 13.9 s |
| FAST (`-m "not expensive"`) | 1382 | **1422 passed**, 565 deselected | +40 | 16.2 s |
| FULL | 1932 | **1987 passed** | +55 | 590 s |

40 of the 55 are static guards that stay in FAST — the residue tables, the
candidate rejections, the negative cases, both injections and the architecture
guards. The 15 that leave FAST launch a fresh interpreter per column.

No pre-existing test edited, skipped, deleted or reordered; no tolerance
loosened. `tests/conftest.py` gained one additive tier entry and its static-guard
set, the documented mechanism.

---

# Q. The exact next milestone

**`MIN-FOUNDATION-PDE`, unchanged and now twice-deferred.** This milestone
consumed none of its four questions and hands it two things:

1. **`VariableToBulkLinkage` is corroborated by two more consumers (6/6)**, and
   **narrowed**: the ordered index set is representable today, so what is missing
   is the *binding* of ordinal position to a state-vector index or a matrix axis.
2. **A named, unbuilt gap: no carrier for "which body"** (§E), which is the
   topology/geometry question §17.6 and OpenFOAM Candidate N already scope. It is
   documented, not built, and is a `MIN-FOUNDATION-PDE` input rather than an
   `EXEC-SPEC` one.

**Explicitly not next:** a universal structured record, a relation artifact, a
topology record, `MatrixValue`, an Equation IR, a structural domain, a chemistry
engine, `ModelInputSpec` publication (T3, awaiting a second consumer).

---

# S. Deviations from the preregistration

**D-1 — P-2 FALSIFIED.** P-2 predicted four mechanics residue items and named its
own falsifier: *"or a fifth item appearing."* There are five. The fifth ("which
body is discretized") arrived from the decision review's required split and is
substantively correct — and the prediction is recorded as falsified rather than
restated, because five was the stated falsifier.

**D-2 — P-6 held in substance, and its reason changed.** Both columns do force
the same `VariableToBulkLinkage` need. But the species half's stated ground — that
an ordered index set is unrepresentable — was **wrong**, caught by the
never-attempted `ScientificVariable` channel. The need is a binding, not a
container.

**D-3 — §7 and §13.5 OVERRIDDEN, deliberately.** §7 stated as a rule that *"B3
forces VERIFIED-EQUAL for the mechanics geometry"* and §13.5 made reporting it as
INJECTED a fail condition. INJ-3 reports it as INJECTED. The override is declared
because the decision review showed the inference had no basis: `species.derivative`
reads its stoichiometry from module scope in exactly the same way and was injected
anyway. **B3 constrains the probe, not the milestone**, and that inference is
withdrawn. The override *raises* the preregistered bar rather than lowering it,
and INJ-3 is bounded exactly as INJ-2 (two constant-strain triangles, one element
type, no framework, no quadrature abstraction).

**D-4 — three of this milestone's own claims were falsified** by its adversarial
pass and are corrected in place: the fresh-process isolation (§N BLOCKER 1), the
connectivity identity attribute (§E), and the derivation claim in `overlap()`
(§N BLOCKER 3).

**D-5 — the reviewer was invoked after the residue table**, not before, as §3 D-C
recorded in advance. That is the reverse of `EXEC-SPEC`'s order and was the
founder's instruction.

**Predictions that held:** P-1 (D not residue), P-3 (ν is residue, derivable from
nothing), P-4 (outcome D, not A), P-5 (both reconstruct with no new universal
record), P-7 (per-schema reader branches), P-8 (the SolverSettings gap classifies
differently per column — mechanics has none), P-9 (a reader without ν reports a
false conservation violation; weighted drift < 1e-9 against naive > 1.0).

---

# T. Git

```text
d744843  Preregister structured executable input stress
<impl>   Stress executable specification with structured scientific inputs
```
