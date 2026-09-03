# CROSS-DOMAIN COVERAGE STRESS — Evidence

**Milestone:** `CROSS-DOMAIN-COVERAGE`
**Kind:** coverage discovery. **No architecture was implemented.**
**Decision status:** none. This milestone freezes nothing.
**Evidence:** `L0 REASONED` + a measured coverage matrix. `L1 EXERCISED` for the
four probe packs' own executed behaviour only. **No `L2`, no `L3`, no upgrade to
any existing holding.**
**Branch:** `cross-domain-coverage-stress`
**Preregistration:** `docs/cross-domain-coverage-stress-prereg.md`, committed at
`a3db20d` before any probe source file was written. **Immutable.**

> Written **after** execution. Where a preregistered prediction failed it is
> recorded as a deviation with the measurement that refuted it. Where the
> adversarial pass falsified a claim, the claim is **withdrawn here** rather
> than softened.

---

# 1. The four consumers

| | Family | Consumer | Executes |
|---|---|---|---|
| **A** | Structural / Mechanical | Two-element plane-stress CST patch, unit square, `E = 210 GPa`, `ν = 0.3`, 4 nodes / 8 DOF | patch test, shear solve, plane-strain contrast |
| **B** | Fluid / Transport | 2D steady advection-diffusion in a prescribed rotational field, `ω = 1 s⁻¹`, `D = 0.01 m²/s`, verified by manufactured solution, grids 8 and 16 | two solves |
| **C** | Chemical / Species | Closed isothermal 3-species batch: `A ⇌ B`, `2B → C` | two integrations |
| **D** | Controls / Dynamics | Planar pendulum in Cartesian coordinates — a genuine constrained-dynamics DAE | two realizations |

## 1.1 Executed results

| Measurement | Result |
|---|---|
| A — patch test, recovered `σ_xx` vs `E·ε` | **relative error `0.0`**, both elements; transverse stress `4.4e-9 Pa` |
| A — stiffness symmetry `‖K − Kᵀ‖` | **`0.0`** |
| A — force equilibrium residual | `3.6e-12 N` against `2e4 N` applied |
| A — `σ_zz`, plane stress vs plane strain | `0` vs **`702 kPa`** |
| B — `div u` (measured, not assumed) | **`0.0`** |
| B — MMS error, 8 → 16 cells | `0.480 → 0.292` |
| B — admissibility, 8 cells | **`c_min = −0.0136` — inadmissible** |
| B — admissibility, 16 cells | admissible |
| C — weighted invariant `c_A + c_B + 2c_C` drift | **`1.1e-14`** |
| C — **naive unweighted** sum drift | **`4.576`** |
| C — linear sub-case vs exact solution | `6.2e-15`; equilibrium ratio `4.0` |
| D — constraint residual `max\|g\|` | `1.4e-14` |
| D — energy drift | `7.3e-14` |
| D — two realizations with **different unknowns** | agree to `2.6e-14 m` |
| D — measured period vs finite-amplitude prediction | `2.03822` vs `2.03776 s` |

---

# 2. Why each consumer, and what it differences against

The binding constraint was the previous milestone's lesson: a consumer must be
scored against the **whole repository**, not against one neighbour.

**A — a 1D bar was rejected.** A bar, spring chain or pin-jointed truss is
isomorphic to the existing `electrical/dc` MNA solve — stiffness ↔ conductance,
displacement ↔ node potential, force ↔ current, fixed node ↔ reference node.
The 2D patch breaks that on three counts a records reader can measure: a
**rank-1 unknown with two components per node**, a **rank-2 symmetric derived
tensor**, and a **matrix constitutive law**.

**B — minimised deliberately.** Steady, one scheme, two grids. A second scheme
and a refinement ladder were already measured in 1D by `HOSTILE-CORE-STRESS`;
spending there would have bought a re-measurement. The transport-operator
overlap with that milestone is **conceded, not discovered**.

**C — isothermal and closed, both as costs paid for differentiation.**
Isothermal eliminates overlap with the existing non-isothermal `kinetics/cstr`
(Arrhenius, stiffness, multiplicity, two states of *different* dimensions, and
species B never represented). Closed eliminates the B/C shared lineage that
Modelica's stream-connector retrofit identifies — a flow reactor would have made
B and C **one** data point about orientation rather than two.

**D — a PI-controlled plant was rejected** as isomorphic to `thermal_lumped`
(one first-order ODE with a `CONTROL` variable), which is why no controller
appears at all.

---

# 3. The zero-new-core-contract representation attempt

All four encode with **zero contract changes**, and every one round-trips.

| Consumer | What encoded cleanly | What did not |
|---|---|---|
| **A** | `E`, `ν`, thickness as scalars; plane assumption as a `CategoricalValue`; clamped DOF as `BoundaryCondition(DIRICHLET)` | the 3×3 constitutive matrix `D`; any relation among the 8 displacement components or the 8 stress components |
| **B** | four boundary regions as four `BoundaryCondition` records; `D`, side, `ω` as scalars | the prescribed **velocity field** and the manufactured **source field** — `ScientificProblem` has no `data_references` |
| **C** | three concentrations, three `InitialCondition`s, rate constants — **cleanly and identically**, which is the problem | the stoichiometric matrix `ν`; the conservation relation it implies |
| **D** | four states; four initial conditions; two realizations (`DAE` / `ODE`) | the algebraic constraint `g = 0`; the differential/algebraic partition; the joint consistency of the four initial conditions; a time-varying input |

**Encodings tried and rejected, recorded rather than left implicit:** encoding
`ν` as six `IntegerValue` parameters named `nu_R1_A` (refused — the meaning
would live in the key spelling, the untyped escape hatch the platform exists to
avoid); `ScientificCapability` / `SolverCapability` to carry a discretization
(refused on layer grounds).

**One encoding was missed and is recorded as a fail-condition-4 violation
caught adversarially:** `ScientificVariable.lower`/`upper` is an existing typed
channel for admissibility bounds and was never attempted. It is now declared on
every species concentration, and the measurement is what happens next — it is
declarable, dimension-checked, serialized, and **no path that inspects a
`ScientificResult` reads it**. `require_within_bounds` is called only from the
design-space, experiment and optimizer-adapter paths. A bound that binds
nothing is a narrower and truer finding than "it cannot be expressed".

---

# 4. The coverage matrix

`F` forced · `P` pressured · `S` served · `–` untouched.
Columns: A-mechanics, B-transport, C-species, D-dynamics, ctl-dc, ctl-lumped.

Every cell is derived by `forcing_verdict(involved, recoverability)` from a
records-only probe and a per-consumer declaration. A test asserts every cell
equals that function of its inputs.

| Concept | A | B | C | D | ctl-dc | ctl-lumped | probe varies? |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| SpatialFieldSemantics | F | F | – | – | – | – | no |
| **VariableToBulkLinkage** | **F** | **F** | **F** | **F** | – | – | **yes** |
| FieldSupport | F | F | – | – | – | – | no |
| Domain/Topology | F | F | – | – | **P** | – | **yes** |
| BoundaryIdentity | P | P | – | – | F | – | **yes** |
| BoundaryOrientation-sign | – | F | – | – | F | – | no |
| BoundaryOrientation-normal | F | – | – | – | – | – | no |
| BoundaryCondition | P | P | – | – | – | – | **yes** |
| Rank1 | F | F | – | F | – | – | no |
| Rank2 | F | – | – | – | – | – | no |
| FieldValuedInput | – | F | – | – | – | – | no |
| Constraint | – | – | P | P | – | – | no |
| DifferentialAlgebraicPartition | – | – | – | F | – | – | no |
| RelationalInitialCondition | – | – | – | F | – | – | no |
| DynamicState | – | – | **S** | **S** | – | **S** | **yes** |
| MaterialIdentity | P | P | P | – | P | P | no |
| MaterialState | – | – | – | – | – | – | no |
| PropertyRequirement-scalar | – | – | – | – | **S** | **S** | no |
| PropertyRequirement-rank2 | F | – | – | – | – | – | no |
| SpeciesIdentity | – | – | P | – | – | – | no |
| Composition | – | – | F | – | – | – | no |
| ReactionRelationship | – | – | F | – | – | – | no |
| CausalPort | – | – | – | – | – | – | no |
| PhysicalConnector | – | – | – | – | – | – | no |
| DiscretizationDefinition | P | P | P | P | – | P | no |
| RuntimeState | – | – | – | – | – | – | no |
| Event | – | – | – | – | – | – | no |
| QuantityIdentity | P | P | P | P | P | – | no |
| **AdmissibilityAttainment** | **F** | **F** | **F** | **F** | P | P | **yes** |
| TimeVaryingInput | – | – | – | F | – | – | no |

## 4.1 The method's limit, measured — and this is the most important line in the document

**24 of 30 probes return the same recoverability verdict for every payload.**

A column-constant probe contributes exactly **one global fact about
`engcore.scientific`**. The cross-column pattern of that row is then the
`science` declarations re-printed — not a measurement of the consumers. Such a
row is a **contract-gap measurement**, and reporting it as evidence that N
materially different consumers independently need something would be circular.

Only **six** rows are genuinely read out of the records:
`VariableToBulkLinkage`, `Domain/Topology`, `BoundaryIdentity`,
`BoundaryCondition`, `DynamicState`, `AdmissibilityAttainment`.

**Every claim in §6 is drawn from those six rows or is explicitly labelled as a
contract-gap measurement.** The instrument now measures and publishes this
itself (`column_variance`), because the adversarial pass showed that without it
a reader would assume every row meant the same thing.

## 4.2 Recoverability classification

| Bucket | Concepts |
|---|---|
| **FULLY REPRESENTABLE** | DynamicState; scalar PropertyRequirement; VariableToBulkLinkage *(controls only, no bulk data)* |
| **AMBIGUOUS** | BoundaryCondition adequacy; Constraint; AdmissibilityAttainment *(controls — no result to read)* |
| **IMPOSSIBLE** | SpatialFieldSemantics, FieldSupport, Domain/Topology *(no artifact)*, BoundaryOrientation ×2, Rank1, Rank2, FieldValuedInput, DifferentialAlgebraicPartition, RelationalInitialCondition, PropertyRequirement-rank2, Composition, ReactionRelationship, CausalPort, PhysicalConnector, Event, MaterialState, RuntimeState, TimeVaryingInput, VariableToBulkLinkage *(consumers)*, AdmissibilityAttainment *(consumers)* |
| **REQUIRES METADATA** | BoundaryIdentity, MaterialIdentity, SpeciesIdentity, DiscretizationDefinition, QuantityIdentity |
| **REQUIRES SOURCE-CODE KNOWLEDGE** | Domain/Topology *for `ctl-dc`* — recoverable from a typed domain artifact by a reader that knows that domain's schema |

---

# 5. Concepts forced by one domain only

| Concept | Forced by | Verdict |
|---|---|---|
| Rank2 (symmetric tensor) | A | `DOMAIN-SPECIFIC`, **but see §9** |
| PropertyRequirement-rank2 | A | `DOMAIN-SPECIFIC`, **but see §9** |
| BoundaryOrientation-normal | A | `DOMAIN-SPECIFIC` |
| FieldValuedInput | B | `DOMAIN-SPECIFIC` |
| BoundaryOrientation-sign | B (+ `ctl-dc`) | `CROSS-DOMAIN-CANDIDATE` |
| Composition | C | `DOMAIN-SPECIFIC` |
| ReactionRelationship | C | `DOMAIN-SPECIFIC` |
| DifferentialAlgebraicPartition | D | `DOMAIN-SPECIFIC` |
| RelationalInitialCondition | D | `DOMAIN-SPECIFIC` |
| TimeVaryingInput | D | `DOMAIN-SPECIFIC` |

**Uniquely forced counts: A = 3, B = 2, C = 2, D = 3.**

---

# 6. Concepts forced independently by multiple consumers

## 6.1 `VariableToBulkLinkage` — the strongest result, and it is measured

**Forced by all four consumers. Column-varying probe.** Each consumer attaches
a bulk `ScientificDataReference` to a multi-variable problem, and that record
carries `{name, unit, count, dtype, digest, digest_algorithm}` — **no field
naming a variable**. Neither the association nor the ordering is recorded. C's
`c:trajectory` holds 3N values against three declared species; D's
`state:trajectory` holds 4N values against four states. A reader cannot say
which values belong to which quantity.

Both controls score `–` because neither carries bulk data, which is what makes
the probe column-varying rather than constant.

This row was **split out of a former `ScientificField` row** that conflated
spatial-field semantics with variable↔bulk linkage. The two have different
column profiles, and the conflation was understating the linkage gap by half.

## 6.2 `AdmissibilityAttainment` — forced by four, at 4/6 not 6/6

Every consumer now writes a real admissibility check into its
`ValidationReport`, and the four are of **four genuinely different kinds**:

| Consumer | Criterion | Kind |
|---|---|---|
| A | `strain_energy_non_negative` | sign of a positive-definite invariant |
| B | `maximum_principle_held` | range excursion under a maximum principle |
| C | `concentrations_non_negative` | non-negativity excursion |
| D | `constraint_manifold_held` | residual of an algebraic relation |

Every one carries `establishes=None`, because `ValidationLevel` has **seven
members and none denotes physical admissibility**. Such a check can report PASS
or FAIL and can never enter `attained_levels`, be gated by `require_level`, or
be compared across results.

**The controls score `P`, not `F`:** they carry no result, so the question is
unreadable for them. The earlier 6/6 is withdrawn — see deviation **D-3**.

### The unplanned finding, and the sharpest single result of the milestone

Consumer B's **coarse grid produces `c_min = −0.0136`** — a physically
inadmissible value of a scalar whose manufactured solution lies in `[0, 1]`.
That record simultaneously:

* **claims `ANALYTICALLY_VERIFIED`**, from its manufactured-solution check, and
* **carries a failed admissibility check that can attain nothing.**

Refining to 16 cells restores admissibility, which confirms the coarse failure
is a discretization artifact rather than a modelling error — **and the platform
cannot say that either.**

## 6.3 `Rank1` — downgraded to `CROSS-DOMAIN-CANDIDATE`

Forced by A, B and D; by neither control; **probe is column-constant**.

The honest reading, after the adversarial pass: **A and D exhibit it; B declares
it.** B's problem record declares no vector components at all — its variables are
`c`, `c:centre`, `c:mms_error`, all scalars, and the velocity enters only as the
scalar `ω`. So the count in the records is 2, not 3.

What survives, and it is the milestone's strongest genuine *structural* result:
**A's rank-1 lives on a support and D's does not.** Separating rank from support
is a real distinction, and two consumers that share no operator exhibit it.

## 6.4 `SpatialFieldSemantics` / `FieldSupport` — A and B only

Conceded in advance by preregistration P-6, not discovered. This is the price of
the founder's fixed four families and the reason B was minimised: A already pays
for most of the 2D/topology/boundary block. **Ledger 2 — zero claimed evidence
gain.**

---

# 7. Universality classification

| Classification | Concepts |
|---|---|
| **UNIVERSAL-CANDIDATE** | **`VariableToBulkLinkage`** — four consumers, measured, column-varying probe, `Ledger 1`. **`AdmissibilityAttainment`** — four consumers exhibiting four different kinds of criterion, column-varying probe, `Ledger 1` |
| **CROSS-DOMAIN-CANDIDATE** | `Rank1` (A + D exhibited, B declared); `BoundaryOrientation-sign` (B + `ctl-dc`); `SpatialFieldSemantics`, `FieldSupport`, `Domain/Topology` (A + B, `Ledger 2`) |
| **DOMAIN-SPECIFIC** | `Rank2`, `PropertyRequirement-rank2`, `BoundaryOrientation-normal` (A); `FieldValuedInput` (B); `Composition`, `ReactionRelationship` (C); `DifferentialAlgebraicPartition`, `RelationalInitialCondition`, `TimeVaryingInput` (D) |
| **LIKELY-FORCED** | `BoundaryIdentity`, `BoundaryCondition` adequacy — pressured by both field consumers and forced in `ctl-dc` |
| **DEFER** | `SpeciesIdentity`, `MaterialIdentity`, `QuantityIdentity`, `DiscretizationDefinition`, `Constraint` — pressured, never forced |
| **REJECT** | `MaterialState`, `PropertyRequirement-scalar`, `DynamicState`, `CausalPort`, `PhysicalConnector`, `Event`, `RuntimeState` — forced by nothing |

## 7.1 The reduction attack

For each candidate universal: can A work without it? B? C? D?

* **`VariableToBulkLinkage`** — no consumer can work without it *and* keep its
  bulk data interpretable. All four attach bulk data; none can say what it is
  of. **Multiple unrelated consumers, independently. Strong candidate.**
* **`AdmissibilityAttainment`** — every consumer can *run* without it; none can
  *report* physical admissibility as established. Four families plus the fact
  that `HOSTILE-CORE-STRESS` deferred this exact member "pending a second
  consumer". **Strong candidate.**
* **`Rank1`** — C works entirely without it. A and D cannot state their vectors.
  **Two exhibited. Cross-domain, not universal.**
* **`Rank2`, `Composition`, `ReactionRelationship`, DAE partition** — three of
  four consumers work without each. **Default to domain-local placement.**

---

# 8. Contract verdicts

**`Quantity` — no change forced, and none may be inferred.** It was not
generalized to vectors, tensors or arrays. The three objects that have no home —
the 3×3 constitutive matrix, the stoichiometric matrix, the velocity field —
are all matrices or fields, and the remedy is **not** a bulk container in a
control record. A test asserts the longest sequence in any serialized control
record is `< 40` against a 16 004-number trajectory.

**`ScientificDataReference` — storage identity holds; field semantics remain
absent, and the *linkage* gap is now measured.** `ScientificDataReference !=
ScientificField` is preserved. Nothing was added to it.

**Field — `CROSS-DOMAIN-CANDIDATE` at `Ledger 2`, zero evidence gain.** A and B
only; already a recorded deferral.

**State — `REJECT`, and this is a win for the contracts.** `DynamicState` is
**served**: `ScientificVariable(role=STATE)` + `InitialCondition` +
`is_time_dependent` represent an evolving state cleanly for C, D and
`ctl-lumped`. The preregistration predicted it forced; it is not.

**Materials / properties — `REJECT`, corroborating a recorded argument.**
`MaterialState` and scalar `PropertyRequirement` are forced by nothing, and the
scalar requirement is visibly **served** in both controls. This directly
supports `electrical/material.py`'s recorded argument that no property
hierarchy was needed. `PropertyRequirement-rank2` is a separate, A-only gap.

**Boundary / topology — `LIKELY-FORCED` / `Ledger 2`.** `Domain/Topology` is
forced by A and B and **pressured, not forced, in `ctl-dc`** — see deviation
**D-4**, a withdrawn claim.

**Discretization — `DEFER`.** Pressured by all four and by one control; forced
by none. `ModelFormulation.DAE` received its first production-shaped use and is
**still insufficient**: it names the mathematical form and cannot state the
index, which unknowns are algebraic, or whether the statement or its
index-reduced form is meant.

**`ScientificTwin` — zero evidence, for the fourth consecutive milestone.** No
consumer forces instance authority. It is consumed by `design/generation.py` as
a `CANDIDATE`, which is a different role and unchanged here.

**Coupling — analysis only.** No `QuantityDependency` was declared and no
coupling runtime touched, so `CausalPort` and `PhysicalConnector` have **zero
evidence by construction**. What the four *would* need is recorded: C and D
would connect through a **relation among several quantities** rather than a
scalar endpoint, which the current scalar-endpoint dependency cannot express.

---

# 9. Falsifier results

`architecture-falsifier` returned **SURVIVES WITH REQUIRED CHANGES**: four
BLOCKERs and five BREAKING-RISKs, all against the **claim layer**, none against
the executed science. All are closed. The primary challenge — *"the proposed
universals are intersections chosen by the author"* — **landed**, and three of
the four claims I intended to make did not survive it.

| # | Finding | Resolution |
|---|---|---|
| **C-1** | 26 of 29 probes column-constant; the matrix's cross-column pattern is largely the `science` declarations re-printed | **Published as a measurement** (§4.1). `column_variance` added; four claim-bearing rows made payload-sensitive; variance now 6 of 30 |
| **C-2** | Five probes answered *recoverability* with a *forcing* argument, all returning fully-representable — **an armed false-negative generator** | All five now return the structural answer; the dash is earned by the declaration |
| **C-3** | `RuntimeState`: D's declaration and D's probe contradicted each other in one published cell | Declaration removed — a trajectory is bulk data on **one** result |
| **C-4** | `Domain/Topology` forced by `ctl-dc` was a **false gap** contradicting `dc/problem.py`'s recorded decision that topology travels by a separate typed channel | **Claim withdrawn.** The artifact is now handed to the instrument; the cell is `P` |
| **C-5** | §7.1 steelman not performed for admissibility — `ScientificVariable.lower/upper` never attempted (fail condition 4) | Attempted; gap narrowed to the `ValidationLevel` membership fact |
| **C-8** | §8.3's "four unrelated kinds" defence was **falsified by the probe source** — three were harmonised excursion measures and A had no admissibility notion at all | `strain_energy_violation` added (a positive-definite invariant); all four checks now written **into the records** |
| **C-6** | `ScientificField` conflated spatial semantics with variable↔bulk linkage | Split into two rows with different profiles |
| **C-9** | `Rank1` is exhibited by two consumers, declared by a third, forced by neither control | Downgraded to `CROSS-DOMAIN-CANDIDATE` |
| **C-7** | The **row set** is author-selected and uncontrolled | Recorded — see §9.1 |
| **C-10/11** | `unique_forcings` excludes controls; `probe_species_identity` ignored its own measurement | Both noted / fixed |

## 9.1 The method's uncontrolled surface, recorded

The control group governs the **columns**. **Nothing governs the rows.** A
concept not on the 29-item list is not "not forced" — it is *invisible*.

The falsifier's counterexample: **complex-valued quantities.** `Quantity` holds
one float and `ScientificValue` is a closed union of real scalars. AC circuit
analysis, frequency-domain acoustics, impedance and modal analysis all need a
complex amplitude. No row covers it, and the control is `electrical/**dc**`, so
even the control cannot surface it.

Consequently: **the fourteen never-forced concepts are not proof of instrument
discrimination**, because three of them (`CausalPort`, `PhysicalConnector`,
`Event`) are excluded by construction.

## 9.2 Cross-domain stress of the claimed universals

| System | Result |
|---|---|
| **Electromagnetics** | `Rank2` and `PropertyRequirement-rank2` forced by a second family — so their `DOMAIN-SPECIFIC` labels are artifacts of *this consumer set*, not measured negatives |
| **Frequency-domain acoustics** | **Breaks the method** — complex amplitudes are invisible to the row set (§9.1) |
| **Geoscience / porous flow** | Anisotropic permeability independently forces `PropertyRequirement-rank2` |
| **Biological compartment networks** | Would move C's rows from `DOMAIN-SPECIFIC` to cross-domain |
| **Optimization / design** | `ConstraintDefinition`'s metric-vs-bound shape is *correct* there — which is precisely why it is wrong for D |
| **External PDE providers** | Confirms the field rows are real gaps independent of this milestone |
| **Long-lived serialized records** | Adding a `ValidationLevel` member later is **additive** — `establishes` is nullable and levels are derived, never asserted. This is why §11 does not treat it as urgent |

---

# 10. Architecture fitness

| Question | Verdict |
|---|---|
| Domain branch in universal core? | **NO** — `src/engcore/scientific/` byte-unchanged, asserted by `git diff` |
| Untyped metadata? | **PARTLY** — species identity, discretization and region identity survive only as metadata; measured, not smuggled |
| `ScientificDataReference` turned into field semantics? | **NO** |
| `Quantity` turned into a bulk container? | **NO** — longest serialized sequence `< 40` |
| Solver identity in the scientific model? | **NO** |
| Mesh identity in scientific field identity? | **NO** |
| Duplicated `ScientificTwin` authority? | **NO** — zero evidence, fourth consecutive milestone |
| Existing schema broken? | **NO** — no version moved |
| Frozen contract modified? | **NO** — `domains/thermal/`, `domains/electrical/`, `thermal_lumped.py` and `experiments/hostile_core_stress/` all byte-unchanged, asserted |
| Source-code knowledge needed to read serialized meaning? | **YES** — for `ν`, the constitutive matrix, the velocity field, the DAE partition, and the variable↔bulk association |

The probe lives in `experiments/`, outside `src/`; `git grep cross_domain_coverage -- src/`
returns nothing.

---

# 11. What NOT to build, and the exact next milestone

## Do not build

`FIELD0`, `TOPO0`, `DISC0`, a structural domain, CFD, a chemistry engine, a
controls engine, API/MCP, a planner, a `ValidationLevel` member, a rank field, a
topology record, or a fifth consumer. **Adding a `ValidationLevel` member later
is additive**, so it fails the "cheaper now than later" test and must not be
rushed on this evidence.

## The next milestone

**`MIN-FOUNDATION-PDE` — unchanged in name from §67.5, and now better scoped.**
This milestone did **not** displace it; it sharpened what it must carry.

Entry condition, unchanged and binding: **a real consumer, not another probe.**
Consumer B here was run as a *minimised probe*, so §67.5's reserved consumer is
spent. The preregistered preference (prereg §2, D-B) is **promotion of B's probe
into a real domain pack** — it already carries the typed records, the boundary
regions and an exact manufactured-solution reference; it lacks transient
behaviour, a second discretization and a refinement ladder.

Scoped by four questions, in this order:

1. **Boundary orientation** (`FORCED` from `HOSTILE-CORE-STRESS`, corroborated
   here by B and `ctl-dc`) — the smallest record making `(kind, region, value)`
   injective. This milestone adds a 2D constraint the 1D probe could not see:
   **a boundary region is not the granularity at which orientation lives.**
   Under solid-body rotation `u·n` changes sign at the midpoint of **every**
   side, so each of four `BoundaryCondition` records carries two roles.
2. **A route from problem structure into `validity_context`** (`FORCED`,
   carried forward unchanged).
3. **`VariableToBulkLinkage`** (`UNIVERSAL-CANDIDATE`, new) — the smallest way
   for a bulk reference to name the variable and ordering it holds. Forced by
   all four consumers, measured, `Ledger 1`. **This is the strongest new input.**
4. **Non-uniform `InitialCondition`** (`LIKELY-FORCED`, carried forward).

**Explicitly deferred with their own evidence required:** admissibility on the
`ValidationLevel` ladder (additive; wait for a real consumer that needs to *gate*
on it); rank-1 semantics (two exhibited consumers is not enough for a universal);
everything `DOMAIN-SPECIFIC` in §5.

---

# 12. Deviations from the preregistration

Recorded here because §54.1 forbids back-writing them into the immutable
preregistration.

**D-1 — P-1 partially falsified.** Predicted every consumer uniquely forces ≥ 3.
Measured **3 / 2 / 2 / 3**. B lost `BoundaryCondition` and C lost
`SpeciesIdentity`; both came back **pressured**, not forced — awkwardly
representable via naming convention and metadata, not impossible. The
preregistration says a consumer below three "was redundant". **The measurement
does not support that word:** each still uniquely forces two concepts no other
consumer forces at all. What is falsified is the threshold, not the consumers.

**D-2 — `DynamicState` falsified.** Predicted `F` for C and D, `P` for
`ctl-lumped`. Forced by nobody; **served** by all three. A win for the contracts.

**D-3 — `AdmissibilityAttainment` withdrawn from 6/6 to 4/6.** The original
score came from a probe that decoded the result and never read it, while **zero
of six columns recorded an admissibility check**. Every consumer now writes one;
the controls carry no result and score `P`.

**D-4 — the `Domain/Topology` non-PDE claim is WITHDRAWN.** `ctl-dc` was scored
as *forcing* topology and cited as the best answer to "these gaps are PDE
artifacts". It was a false gap: `dc/problem.py` records that it translates a
circuit *"without smuggling topology into the IR"*, because connectivity travels
separately and is bound by a verified fingerprint. The probe was never handed
that artifact. With it, the cell is `P`, and topology is forced only by the two
field consumers — **exactly the PDE-shaped profile the withdrawn claim denied.**

**D-5 — P-3 held on substance, failed on its control half.** `MaterialState` and
scalar `PropertyRequirement` are forced by nobody. They are not *pressured* in
the control as predicted — they come back **served**, a stronger negative.

**D-6 — three unreported cell reversals**, surfaced by the falsifier: `Rank1` B
`P→F`; `Domain/Topology` `ctl-dc` `P→F` (since corrected to `P`); `RuntimeState`
D `P→–`. The first two occurred because those probes were structurally incapable
of returning `P`.

**D-7 — an unplanned finding**: B's coarse grid produces an inadmissible field
whose record still claims `ANALYTICALLY_VERIFIED` (§6.2).

## Predictions that held

* **P-2** — `CausalPort`, `PhysicalConnector`, `Event` all-dash by construction.
* **P-5** — admissibility is the highest-value row, though at 4/6 not 6/6.
* **P-6** — the A/B block duplicates, conceded in advance.
* **Fail condition 5** — the matrix returns fourteen never-forced concepts, so
  it discriminates. **Qualified by §9.1**: three are excluded by construction.

---

# 13. Tests

`tests/test_cross_domain_coverage.py` — **42 tests, all passing.**

Physics integrity per consumer; instrument integrity by AST scan; the coverage
matrix asserted cell-by-cell; `column_variance` asserted; every cell asserted to
equal `forcing_verdict` of its inputs; the preregistered negatives asserted as
negatives; and the fail conditions asserted by `git diff`.

```text
FAST   1303 → 1345   (+42)
FULL   1825 → 1867   (+42)
```

**No pre-existing test was edited. No tolerance was loosened. No control-group
file, frozen thermal file, or prior probe file was touched.**

One environment note: pytest's default temp root is not writable in this
sandbox, so runs used `--basetemp`. This affects four pre-existing
`test_data_boundary0.py` tests identically and is not introduced here.

---

# 14. Evidence status

| Item | Decision | Evidence |
|---|---|---|
| `VariableToBulkLinkage` | none — input to the next milestone | **`UNIVERSAL-CANDIDATE` / `L0` + measured, 4 consumers** |
| `AdmissibilityAttainment` | none | **`UNIVERSAL-CANDIDATE` / `L0` + measured, 4 consumers** |
| `Rank1` | none | `CROSS-DOMAIN-CANDIDATE` / `L0` — 2 exhibited, 1 declared |
| Boundary orientation | none | `CROSS-DOMAIN-CANDIDATE` / `L0` + measured |
| Field / support / topology | none | `CROSS-DOMAIN-CANDIDATE` / `L0` — **Ledger 2, zero evidence gain** |
| Everything in §5 | none | `DOMAIN-SPECIFIC` / `L0` |
| The four probe packs' execution | — | `L1 EXERCISED` |

**No abstraction that was never implemented is assigned `L1`.** `L2` is excluded
outright — four consumers by one author on one branch is exactly the lineage
§54.1 excludes from "materially different".

**Unchanged and explicitly not upgraded:** `MODEL0-R`, `DATA-BOUNDARY0`,
`MIN-FOUNDATION-ET`, `ET-VERTICAL`, `HETERO-NGSPICE`, `HOSTILE-CORE-STRESS`.

---

# 15. Git

| Commit | Content |
|---|---|
| `a3db20d` | `Preregister cross-domain coverage stress` — immutable |
| *(this)* | `Stress core across scientific domain families` |
