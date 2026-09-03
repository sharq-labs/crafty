# EXECUTABLE SCIENTIFIC SPECIFICATION DECISION — Evidence

**Milestone:** `EXEC-SPEC`
**Kind:** architecture decision, gated on a measurement (`EXEC-SPEC-RESIDUE`).
**Decision:** **NO UNIVERSAL EXECUTABLE-SPECIFICATION RECORD.** Per-domain
answer: option **E + F**. Status **`PROPOSED`**. Nothing is frozen.
**Evidence:** `L1 EXERCISED` for what executed; `L0 REASONED` for everything
argued. **`L2` is not claimed and is excluded by the preregistration.**
**Branch:** `executable-scientific-spec-decision`, cut from `38783ed`.
**Preregistration:** `docs/executable-scientific-spec-prereg.md`, committed at
`b0e1353` before any source file of this milestone was written. **Immutable.**
Nothing below is back-written into it.

> Written **after** execution. Where a preregistered prediction failed, or a rule
> did not decide what it was supposed to decide, it is recorded as a deviation
> with the measurement that refuted it — not quietly restated.

---

# A. The current `bind_*` architecture, mapped

**FACT.** Six bind sites. Five in the four production domains this milestone
measured, one in a sibling module.

| Domain | Bind site | Artifact passed out of band | Link to the problem | Serializable? | Reconstructable? |
|---|---|---|---|---|---|
| electrical DC | `dc/solver.py:98 bind_circuit` | `DCCircuit` | four `metadata` keys + fingerprint | **yes**, `electrical_dc_circuit/1` | **yes**, `from_dict` |
| electrical DC via provider | `ngspice.py:493 bind_circuit` | `DCCircuit` | same | same | same |
| thermal conduction | `conduction1d/solver.py:162 bind_slab` | `ConductionSlab` | `metadata["slab_fingerprint"]` | `to_dict` only | **no reader** |
| kinetics CSTR | `cstr/solver.py:287 bind_run` | `ReactorRun` | `metadata["physics_fingerprint"]` | `to_dict` only | **no reader** |
| electrical material | `material.py:496 bind_conductor` | `(conductor, temperature)` | **typed parameter comparison, no fingerprint** | neither | n/a — problem is sufficient |
| thermal schemes | `thermal_conduction1d_schemes.py:454` | geometry **and a realization** | — | — | — |

Two error strings state the gap in the domains' own words:
`dc/solver.py:152` *"the universal IR carries no topology"*;
`conduction1d/solver.py:205` *"the universal IR carries no geometry"*.

**FACT.** `def from_dict` exists under `src/engcore/domains/` **only** in
electrical DC (5 classes). Serialization is write-only in two domains and absent
in two.

**FACT.** Three domains independently invented three incompatible untyped
artifact-reference conventions inside `ScientificProblem.metadata`.

---

# B. Alternatives considered

A–E were supplied by the milestone brief. F and G were added by the reviewer
because the brief's set contained neither a "do nothing new" option nor a
different-placement option.

| | Option |
|---|---|
| **A** | typed `StructuralArtifactReference` on or beside `ScientificProblem` |
| **B** | promote scientific structure **into** `ScientificProblem` |
| **C** | sibling `ExecutableProblemSpecification` record |
| **D** | domain-registered deterministic builder keyed by schema identity |
| **E** | formalize the current artifacts as typed, versioned, round-trippable records |
| **F** | contract-level reduction — move every representable fact into a channel that already exists; no new record |
| **G** | change `ScientificSolver.prepare` to take the structure explicitly, killing the bind maps |

---

# C. Reviewer decision

`architecture-decision-reviewer`, invoked **before** the preregistration was
written, returned **SPIKE REQUIRED** — not a selected option.

Its central finding, which this milestone is built on: *the deciding measurement
has never been taken.* The `CROSS-DOMAIN-COVERAGE` matrix has 30 rows and no
executability row. Every one of A–E was supported by an argument and none by a
count.

It also excluded two options before execution, on evidence:

* **B rejected** — §68.3 deviation **D-4** already withdrew, under falsification,
  the claim that `electrical/dc` forces universal topology, because connectivity
  travels by a separate typed channel bound by a verified fingerprint. B asks to
  reverse a falsifier-tested finding, and violates the frozen layer separation.
* **D rejected** — a builder keyed by schema identity means the record alone is
  never sufficient; the domain package must be installed at a compatible
  version, which defeats "reconstructed in a fresh process" and "transmitted".
  **See §P, D-3: the executed proof has this property too, and declares it less.**

And it fixed the placement *conditionally*: if a universal record turned out to
be forced, its placement would be **C** (standalone sibling), for the reason
recorded verbatim for `QuantityDependency` — `require_schema` is exact-match with
no migration path, so an inline field on `ScientificProblem` makes every stored
payload unreadable by a pre-milestone reader.

---

# D. The measurement, and why the alternatives lost

## D.1 The instrument

One records-only reader (`experiments/exec_spec_residue/instrument.py`), handed
serialized payloads only, forbidden by AST scan from importing anything under
`engcore.domains`. Four columns — the four production domains that bind an
artifact — at four information levels (L0 problem alone, L1 + existing artifact
serialization, L2 the binding steelman, L3 the residue).

## D.2 The executed encoding attempts

**FACT.** Eleven attempts, all executed. Nine call a contract and record its own
exception text or its acceptance; two establish a *structural absence* by reading
`dataclasses.fields` of the live record, because nothing can raise when the
finding is that a field does not exist.

| Column | Fact | Channel | Outcome |
|---|---|---|---|
| col-dc | incidence + terminal order | `ScientificParameter` | **meaning-in-key** |
| col-dc | incidence + terminal order | `BoundaryCondition` | **meaning-in-key** |
| col-dc | incidence + terminal order | `ScientificDataReference` | **refused-by-type** |
| col-slab | homogeneous Dirichlet ends | `BoundaryCondition` | **works** |
| col-slab | non-uniform initial field | `InitialCondition` | **refused-by-type** |
| col-slab | non-uniform initial field | `ScientificDataReference` | **no-persistable-home** |
| col-slab | mesh resolution | `ScientificParameter` | **leaks-into-identity** |
| col-cstr | initial concentration and temperature | `InitialCondition` | **works** |
| col-cstr | integration declaration | `SolverSettings` | **no-persistable-home** |
| col-cstr | integration declaration | `ScientificParameter` | **leaks-into-identity** |
| col-material | three conductor constants | `ScientificParameter` | **works** |

Two of these are findings about the **production domains**, not about the core:
the slab's Dirichlet ends and the CSTR's initial conditions are both fully
representable today, and neither domain writes them. `build_cstr_problem` writes
zero `InitialCondition` records, so `problem.is_time_dependent` is `False` for a
transient ODE domain.

## D.3 The residue table

**FACT, measured.** Two readings, reported because the difference between them is
the sharpest thing this milestone found.

**STRICT** — no existing contract can carry the fact at all:

| Column | Residue | Kind | Ledger |
|---|---|---|---|
| col-dc | incidence + terminal order | scientific-structure | **1** |
| col-slab | non-uniform initial field | condition | **2** |
| col-cstr | — | — | — |
| col-material | — | — | — |

**PLACEMENT** — also facts a contract holds only where it makes a different claim:

| Column | Residue | Kind | Ledger |
|---|---|---|---|
| col-dc | incidence + terminal order | scientific-structure | **1** |
| col-slab | non-uniform initial field | condition | 2 |
| col-slab | mesh resolution | discretization | 2 |
| col-cstr | integration declaration | numerical-setting | **1** |
| col-material | — | — | — |

## D.4 Why each alternative lost

* **B** — excluded before execution (§C), and the measurement corroborates:
  putting the mesh into `ScientificProblem` as typed parameters *works
  mechanically* and scores `leaks-into-identity`, which is precisely what B
  proposes to institutionalize.
* **D** — excluded before execution. §P D-3 records that the executed proof
  shares its weakness.
* **A** and **C** — not forced. A universal record requires ≥ 2 columns with a
  same-shaped Ledger-1 residue; the measurement found one under STRICT, and two
  of **different kinds** under PLACEMENT.
* **G** — out of scope, and confirmed still needed: P-8 held (see §M).
* **E + F** — selected, with the limits in §P.

---

# E. The selected semantic boundary

```text
ScientificProblem            what is asked: quantities, conditions, parameters,
                             capabilities, models. Intent and semantics.
        +
domain-owned structure       what makes it executable, where the science of the
record (per domain)          domain has structure no universal channel can hold:
                             typed, versioned, schema-carrying, round-trippable.
        ↓
typed identity check         the problem's own parameters verify the structure.
                             Not a fingerprint, not a metadata key.
        ↓
domain builder → solver      runtime. PreparedSolve stays runtime-only.
```

**What is NOT in the boundary, deliberately:** no new universal record, no
`ScientificProblem` schema change, no `ExecutableProblemSpecification`, no
builder registry, no equation representation, no `ScientificTwin`.

**The claim, in its exact scope:** for the four production domains that bind an
artifact, as they stand on 2026-09-03, measured by one instrument written by one
author on one branch — **no universal executable-specification record is forced.**

---

# F. Exact contracts: new, modified, none

**FACT. Nothing under `src/` was added, edited or removed.** Asserted by
`test_no_src_file_was_added_or_edited` (git diff + untracked scan) and
`test_the_milestone_lives_outside_the_package`.

| Contract | Status |
|---|---|
| `ScientificProblem` | **unchanged**, `scientific_problem/1`, asserted |
| every other core record | unchanged |
| every domain | unchanged |
| `electrical_dc_circuit/1` | **reused as-is**, not modified |
| `exec_spec_slab_residue/1`, `exec_spec_cstr_numerics/1` | defined in `experiments/`, **for measurement only**, not proposed as contracts |
| `tests/conftest.py` | one additive tier entry + its static-guard set. No existing entry touched |

---

# G. Two-domain proof — four columns, executed

**FACT.** All four columns reconstruct from records. Three additionally execute.

| Column | Reconstruction direction | Result |
|---|---|---|
| col-dc | artifact payload → circuit; **problem verifies it** | `fingerprint()` identical to the original; MNA agrees with baseline to `1e-9` |
| col-slab | **problem parameters** → slab; residue supplies the mesh | rebuilt `== ` original; agrees to `1e-12` |
| col-cstr | **problem parameters + initial conditions** → run; residue supplies numerics | rebuilt `==` original; agrees to `1e-9` |
| col-material | **problem alone** → conductor; no residue exists | rebuilt `==` original; `R(T)` agrees to `1e-12` relative |

Two materially different families are covered as required: a **lumped network**
(DC) and two **dynamic/continuum** domains (transient PDE, stiff nonlinear ODE).

**A measured asymmetry worth keeping.** For `col-dc` the artifact carries
everything and the problem *verifies*; for the other three the problem carries
the physics and *produces*. The DC problem is a **projection** of the circuit, not
a source of it — `rebuild_circuit(problem, None)` raises `MissingStructure`.

**A measured trap, recorded rather than hidden.** `DCCircuit.to_dict` sorts nodes
and components; the constructor preserves insertion order; dataclass `__eq__`
compares tuple order. A round trip therefore returns **the same physical system
with an identical `fingerprint()` and `canonical_dict()`** that is **not** `==` to
the original. Asserted explicitly in
`test_the_circuit_round_trip_preserves_identity_but_not_python_equality`.

---

# H. Fresh-process reconstruction

**FACT.** Three columns reconstruct and execute in a **separate interpreter
process**, launched with `-B`, given a directory containing two JSON files and
two command-line strings. Nothing else crosses.

The isolation is structural, not promised: `schemas.py` exists so that `bridge`
reaches its schema constants without importing `encodings` → `cases`, the module
holding the original artifacts. The child reports its own `sys.modules`, and the
parent asserts that neither module was loaded.

```text
process 1   build records → write problem.json (+ structure.json) → exit
process 2   read two JSON files → reconstruct → execute → print metrics
```

Agreement with the in-process baseline: `col-dc` 1e-9, `col-slab` 1e-12,
`col-cstr` 1e-9. **P-6 held.**

---

# I. Relocation

**FACT.** Records copied to a second directory reconstruct to a circuit with a
**byte-identical fingerprint**, and the fresh process returns identical metrics
from both locations. No absolute path, directory name or host appears anywhere in
the serialized payloads — asserted by substring scan.

This is DATA-BOUNDARY0's rule holding one layer up: where the bytes sit is an
execution fact and cannot change what they mean.

---

# J. External provider — RUN

**FACT. The ngspice case RAN. It did not skip.** ngspice **42**, reached as
`wsl.exe -e ngspice`. The provider received a `DCCircuit` reconstructed in a
**fresh process from records**, with no original in-memory circuit, no inherited
bind state, and **no modification to the adapter**. Its metrics agree with the
native baseline within the tolerance `HETERO-NGSPICE` preregistered.

**P-7 held — and it had almost no discriminating power, which is recorded rather
than dressed up.** `solve_circuit_with_ngspice` takes a `DCCircuit`; reconstruction
produces a `DCCircuit` with an identical fingerprint. Once `from_dict` round-trips,
no adapter could tell the two apart. The case confirms that reconstruction is
provider-neutral; it does **not** establish that provider integration survives
reconstruction in general, and no such claim is made.

---

# K. Planner inspectability

**FACT.** The records-only reader answers all eight questions for every column at
L1, and **cannot** answer connectivity at L0 for any column — P-9 held on both
halves. A payload whose schema it does not know is reported as unreadable, never
guessed.

For `col-dc` at L1 it recovers, from typed fields of a published schema and
without importing the domain:

```text
edges  {'R1': ['n0','n1'], 'R2': ['n1','gnd'], 'V1': ['n0','gnd']}
datum  ['gnd']
```

**Three limits, all measured, none cosmetic:**

1. **Identifier resolution was not part of the reader, and four identifiers were
   wrong.** The adversarial pass found that `instrument.inspect` answers MODELS
   and CAPABILITIES from non-empty lists and never resolves an identity — so four
   invented strings passed 58 tests. They are corrected, and
   `test_every_identifier_a_planner_would_read_actually_resolves` now resolves
   every `ModelReference` against a `ModelRegistry` and every capability against
   the domains' declared constants. **The original claim "answers all eight
   questions" overstated what had been demonstrated; this is a deviation, D-2
   below.**
2. **The reader is domain-agnostic by import and domain-specific by
   transcription.** `instrument.py` contains the DC element-key table and a
   `KNOWN_STRUCTURE_SCHEMAS` map. §13.4's fail condition — a per-column reader —
   is met in letter (one module) and evaded in substance (the per-column branches
   live inside it). **This is the cost side of option E and it is unmeasured:**
   every future records-only consumer must learn every domain schema, so cost
   grows as *domains × consumers*.
3. **Two decorative boundary records corrupt a different reader's answer.** The
   slab encoding writes two `BoundaryCondition` records the solver never reads.
   The **core** reads them: `unresolved_inputs` treats a variable named by any
   boundary condition as determined, so the reader answers *"nothing must be
   supplied"* for the one column whose initial field this milestone declares
   unrepresentable. This is §66.4's lesson running in reverse — a field nothing
   consults is not merely a non-guard; it can make a different reader wrong.

---

# L. The relation / equation gap that remains

Nothing was built. Classification as §16 requires:

| Relation | Classification | Why |
|---|---|---|
| stoichiometric matrix | **BLOCKS PLANNING**, not reconstruction | `col-cstr` reconstructs only because one reaction `A → B` has its stoichiometry compiled into the RHS. `experiments/cross_domain_coverage/species.py` already records that `ScientificParameter` cannot carry a matrix |
| constitutive stiffness matrix | **BLOCKS RECONSTRUCTION** for any structural domain | rank-2, no channel; `cross_domain_coverage/mechanics.py` carries a 3×3 `D` today |
| algebraic constraints among unknowns | **BLOCKS MONOLITHIC COMPOSITION** | `ConstraintDefinition` is `metric OP bound`, an acceptance test, not a relation |
| conservation relations | **BLOCKS PLANNING** | not statable; the species conservation weights are the ν no record holds |
| PDE operator structure | **DEFERRED** | `col-slab` reconstructs only because the operator, the ends and the profile are compiled in |

**The honest summary:** reconstruction works for these four domains because their
relations are compiled into installed code and their inputs are scalars. Where a
relation is *data* — a matrix — reconstruction stops.

---

# M. Concurrency implication

**FACT. P-8 held: reconstruction does not remove the bind maps.**
`bridge.execute("col-material", …)` still calls `solver.bind_conductor(...)`, and
every domain solver still holds `dict[problem_id → artifact]`.

**INFERENCE.** Making structure reconstructible removes the *reason* the bind
exists (nothing else could deliver the artifact) but not the bind itself.
Statelessness requires changing `ScientificSolver.prepare` — option **G** — which
is a public protocol with four implementations and touches `domains/thermal/`,
byte-pinned by three frozen experiments where §57.1 forbids improvising an
unfreeze. **G is a separate decision and is not taken here.**

---

# N. Provenance implications — listed, not built

**FACT.** The reconstruction is record-sufficient **relative to an installed,
unversioned, unverified domain package.** Nothing in the persisted records names
a domain package or its version. `ModelReference.version` exists and `bridge`
never reads it. This is the property on which option D was rejected, and the
executed proof declares it *less* than D would.

Missing fields, listed:

| Field | Class |
|---|---|
| domain package identity + version | execution provenance |
| structural artifact identity (a typed reference to the structure record) | scientific provenance |
| which discretization produced which result | execution provenance |
| non-scalar inputs (`ProvenanceRecord.inputs` is `Mapping[str, Quantity]`) | scientific provenance |
| random seed | execution provenance |
| environment / toolchain | infrastructure provenance |

None is implemented. No machine path is proposed for any scientific identity.

---

# O. Reduction attacks

| Attack | Result |
|---|---|
| Can the decision be replaced by serializing the existing artifact? | **That is the decision** (option E for one domain) |
| Can it be replaced by enriching `ScientificProblem`? | No — option B, excluded on recorded evidence, and the measurement shows the enrichment scores `leaks-into-identity` |
| Can it be replaced by a typed artifact reference (A)? | Not forced. A reference names a blob; it does not make anything reconstructable. The DC column already reconstructs without one |
| Can it be replaced by a builder registry (D)? | No — and §N records that the executed proof already has D's weakness without declaring it |
| Can the spike itself be reduced away? | **Partially, and that is the finding.** Three of four columns reduce into contracts that already exist. The spike is the measurement of whether that reduction succeeds, which had never been run |
| Is `ScientificTwin` needed? | **No.** Nothing in reconstruction needs an instance authority. Fifth consecutive milestone with zero evidence. Left alone |

**Duplicate truth, measured:** `R:`/`Vs:` exist as `ScientificParameter` **and**
inside `DCCircuit`. The chosen design does not increase the duplication — it makes
it *load-bearing*, by using the typed parameters to verify the structure instead
of comparing a metadata fingerprint. That is a better use of an existing
duplication than deleting one side would be, because the two now check each
other.

---

# P. Falsifier findings

`architecture-falsifier` returned **FALSIFIED**: 3 BLOCKERs, 6 BREAKING-RISKs.
**All against the claim layer; none against the executed science.** All twelve
required corrections were applied before commit.

## BLOCKER 1 — §9 did not decide the measured table without an unpreregistered rule

§9 row 1 says *"non-empty for exactly one column"*. The measured STRICT table has
**two** non-empty columns (`col-dc`, `col-slab`). Row 3 also matched, and the
preregistration states no precedence. `decide()` resolves it by ranking on
**ledger** — the §67.3 booking rule — which is defensible and is **not in §9**.

**Recorded as deviation D-1.** The claim *"the preregistered decision rule
selects…"* was false as stated. What is true: §9 plus the §67.3 ledger rule
selects it, and the ledger rule was applied as precedence without having been
preregistered as such.

**Also closed:** `ResidueKind` — the operational definition of §9's undefined
term "same shape", and the value `decide(PLACEMENT)` turns on — is **argued, not
measured**. One relabel of the CSTR item flips the PLACEMENT outcome.
`test_the_placement_reading_reaches_the_same_outcome_by_a_different_route` now
asserts this and its docstring says so. **The claim that "both readings agree" is
therefore withdrawn as independent corroboration:** they agree because the two
Ledger-1 items were assigned different kinds.

## BLOCKER 2 — four model/capability identifiers did not exist

`kinetics.cstr.nonisothermal`, `kinetics:cstr_nonisothermal`,
`electrical.material.linear_tcr` and `thermal:conduction_1d` appear nowhere in
the repository. 58 green tests could not catch it because nothing resolved an
identifier, and `bridge.execute("col-material", …)` discards the L2 problem and
calls the production builder, so the wrong reference never reached execution.

**Closed by:** correcting all four, and adding a test that resolves every
`ModelReference` against a `ModelRegistry` and every capability against the
declared constants. §K restates the planner claim accordingly.

## BLOCKER 3 — three of four columns reconstruct by the mechanism the measurement rejects

`_attempt_incidence_as_categorical_parameters` is rejected because the relation
would live in the *spelling* of a parameter name. But `rebuild_slab`,
`rebuild_run` and `rebuild_conductor` recover **all** their physics that way: a
parameter called `"alpha"` becomes `ConductionSlab.diffusivity` because two
modules in one package agree that it does. No record publishes that vocabulary.

**Closed by:** `test_three_columns_reconstruct_by_parameter_name_convention`,
which renames `alpha` → `diffusivity` — a valid `scientific_problem/1` payload
that answers every planner question identically — and shows reconstruction fails.
The residue note now records the limit, and the corrected claim is:

> The **F** half of E + F is **exhibited, not proven.** What distinguishes
> `col-dc` is not that its fact travels in a name — every column's does — it is
> that its fact **also** travels in a typed, versioned, schema-checked record,
> and the others' do not.

`ModelInputSpec` / `ModelRegistry` is the existing typed channel that could
publish that vocabulary. **Recorded, not built.**

## BREAKING-RISK 1 — the column set excludes every matrix-valued consumer

The four columns are "the production domains that bind an artifact", and Crafty
has no production domain with a rank-2 constitutive law or a stoichiometric
matrix — because it has not built one. The selection rule therefore correlates
with the null hypothesis.

Meanwhile `experiments/cross_domain_coverage/mechanics.py` (3×3 plane-stress `D`)
and `species.py` (3×3 stoichiometry, whose own comment reads *"a
ScientificParameter cannot carry a matrix"*) are **committed, executed consumers
from the immediately preceding milestone** and were not columns. Under §9 either
would produce a second Ledger-1 residue, and if labelled
`SCIENTIFIC_STRUCTURE` the rule returns *"UNIVERSAL RECORD JUSTIFIED"* — the
opposite of this decision.

**Closed by scoping, not by re-running:** the decision holds for the four
production domains that bind an artifact, as they stand today. This is stated in
§E and repeated in §R.

## BREAKING-RISK 2 — the slab's decorative boundary records

See §K.3. **Closed by** a refusal in `rebuild_slab` mirroring the one already
written for `initial_profile`: a boundary set the solver does not implement is
now refused rather than silently executed as something else. The
`unresolved_inputs` consequence is recorded as a measurement.

## BREAKING-RISK 3 — the `col-dc` pattern presumes one process holding the whole structure

`to_dict` and `canonical_dict` sort every node and component; `fingerprint()`
JSON-dumps and SHA-256s the whole document. At mesh scale that is a gather, and
partitioning — an execution fact — could then move a scientific identity, the
exact failure `data_reference.py` exists to prevent. `child.py` and
`ColumnEncoding` also assume **one** structure payload; an OpenFOAM case or a
mesh + function space + coefficient field is 1:N with heterogeneous kinds.

**Recorded:** the pattern was exercised on one 3-node circuit, is bounded by
single-process whole-structure-in-memory, and is **not** advanced as the pattern
for mesh-scale or multi-file artifacts.

## BREAKING-RISK 4 — option E promotes a domain serialization into a durable record

`electrical_dc_circuit/1` is an internal round-trip today; under E it becomes a
persistence contract, governed by an exact-match reader with no migration path.
Adding a component type forces `/2` and makes every stored payload unreadable.
**Recorded as a precondition of the implementation milestone, not of this
decision.**

**Also closed:** the identity check verified only `R:` and `Vs:` because the
frozen case has no current source, so one whole element type was unverified.
`rebuild_circuit` now verifies `Is:`, and
`test_an_unverified_element_type_is_a_hole_the_example_hid` exercises it.

## BREAKING-RISK 5 — record-sufficiency is relative to an installed package

See §N. **Closed by recording**, including the counterexample: change
`assemble()`'s hard-coded initial profile to `sin(2πx/L)` and every record stays
byte-identical, every check passes, and the fresh process returns different
physics with no refusal anywhere.

## BREAKING-RISK 6 — the headline is readable as "no universal record is needed"

`VariableToBulkLinkage` **is** forced — by all four consumers of
`CROSS-DOMAIN-COVERAGE`, §68.2 — and is that milestone's strongest input to
`MIN-FOUNDATION-PDE`. **Closed by naming the decision precisely:** *no universal
**executable-specification** record.* This measurement neither weakens nor
competes with `VariableToBulkLinkage`.

## IMPLEMENTATION-CONCERN — an attempt refused for the wrong reason

`_attempt_incidence_as_boundary_condition` originally omitted `value` and was
refused *because a Dirichlet condition requires one* — a refusal about a missing
value, recorded as though it were about incidence. Supplied with a value the
record **is** accepted, because `region` is an opaque label that will
mechanically hold the second terminal. **Closed by** re-running it with a value,
recording the true outcome (`meaning-in-key`), adding it to the parametrization
(it was the only attempt not asserted), and correcting the module docstring to
distinguish executed refusals from executed structural absences.

## What the falsifier explicitly did NOT find

The fresh-process isolation is real and correctly engineered; the relocation
invariance holds; the `SolverSettings`-unreachable finding is correct and
independently verified; the negative tests are genuine; `metadata` is empty in
all four encodings; no abstraction was smuggled; `ScientificTwin` was correctly
left alone; the `==`-versus-`fingerprint` asymmetry is a strength, not a weakness.

---

# Q. Architecture fitness

| # | Question | Answer |
|---|---|---|
| 1 | `ScientificProblem` schema changed? | **No.** `scientific_problem/1`, asserted |
| 2 | existing domain schema changed? | **No.** Nothing under `src/` touched |
| 3 | migration required? | **No**, for this decision. Yes eventually for `electrical_dc_circuit/1` — see §S |
| 4 | domain-specific branch added to universal core? | **No** in `src/`. **Yes in the instrument** — recorded, §K.2 |
| 5 | metadata/fingerprint convention removed or merely moved? | **Neither.** Left in place; the milestone demonstrates a typed alternative (parameter comparison) without adopting it |
| 6 | provider identity leaked upward? | **No.** ngspice appears in no record |
| 7 | discretization leaked into scientific problem identity? | **No.** Measured as `leaks-into-identity` and refused |
| 8 | duplicate source of truth introduced? | **No new one.** The existing `R:`/`Vs:` duplication is made load-bearing as a check |
| 9 | hidden Python artifact still required? | **Yes for `col-dc`** — but it is no longer hidden: it is a serialized, schema-carrying record |
| 10 | fresh-process reconstruction possible? | **Yes**, three columns, executed |
| 11 | remote reconstruction plausible? | **Unproven.** No consumer exists; records carry no package version (§N) |
| 12 | planner can inspect without domain source code? | **Partly.** Eight questions answered; the reader carries per-domain schema knowledge (§K.2) |
| 13 | solver bind-state reduced? | **No.** P-8 held (§M) |
| 14 | existing evidence still green? | **Yes.** FULL green, no test edited |

---

# R. Evidence and status

**Decision:** NO UNIVERSAL EXECUTABLE-SPECIFICATION RECORD. Per-domain: **E + F**.
**Decision status: `PROPOSED`.** Not `DESIGN-FROZEN` — the preregistration
excludes it, and BREAKING-RISK 1 is an open scope limit.

| Claim | Level |
|---|---|
| four columns reconstruct; three execute in a fresh process | **`L1 EXERCISED`** |
| relocation preserves scientific identity | **`L1 EXERCISED`** |
| ngspice accepts a reconstructed circuit unchanged | **`L1 EXERCISED`**, with low discriminating power (§J) |
| the residue table | **`L1 EXERCISED`** for the eleven attempts; **`L0 REASONED`** for the `ResidueKind` labels |
| "no universal record is forced" | **`L0 REASONED`**, scoped to four production domains as they stand |
| option F (reduce into existing contracts) | **exhibited, not proven** (BLOCKER 3) |

**`L2 DIFFERENTIATED` is not claimed anywhere.** Two domains reconstructed by one
author on one day against a bridge that author wrote is exercise, not
differentiation — the trap `HETERO-NGSPICE` §66.3 withdrew from.

**Tests.**

| Tier | Before | After | Delta | Wall |
|---|---|---|---|---|
| targeted (`tests/test_executable_scientific_spec.py`) | — | **65 passed** | +65 | 13.7 s |
| FAST (`-m "not expensive"`) | 1338 | **1382 passed**, 550 deselected | +44 | 13.8 s |
| FULL | 1867 | **1932 passed** | +65 | 589 s |

44 of the 65 are static guards that stay in FAST — the residue table, the
decision rule, the planner questions, the negative cases and the architecture
guards. The 21 that leave FAST are the ones that execute a domain, launch a fresh
interpreter, or drive ngspice.

No pre-existing test was edited, skipped, deleted or reordered; no tolerance was
loosened. `tests/conftest.py` gained one additive tier entry and its static-guard
set, which is the documented mechanism (`docs/TESTING.md`) and touches no
existing entry.

---

# S. Migration strategy

**Nothing migrates in this milestone.** For the implementation milestone that
follows, the route is:

1. **Additive per domain, never global.** `ConductionSlab`, `ReactorRun`,
   `ThermalBody` and `TemperatureDependentConductor` gain `from_dict` beside
   their existing `to_dict`. No schema version moves; a reader is added where
   only a writer existed.
2. **`electrical_dc_circuit/1` is promoted to a durable contract**, and the
   migration route for a future `/2` must be decided **before** any artifact is
   stored — `require_schema` is exact-match and `SUPPORTED_*` tuples are the
   existing mechanism.
3. **The `metadata` artifact-reference conventions stay** until something
   replaces them. Removing them would be a `scientific_problem` change; they
   become vestigial rather than invalid.
4. **`dc/problem.py:201` declares the wrong schema** — `CANONICAL_SCHEMA`, the
   fingerprint preimage with no `from_dict`, where the round-trippable
   `CIRCUIT_SCHEMA` is what a reader needs. One line, in a domain, in its own
   milestone.
5. **No silent migration.** Existing evidence stays interpretable: every stored
   record predating this decision loads unchanged, because nothing changed.

---

# T. The exact next milestone

**`MIN-FOUNDATION-PDE` — unchanged, and it is next.** This milestone deferred it
by one and did not consume it. Its four preregistered questions stand, and this
measurement adds nothing to them and takes nothing away:

1. boundary orientation;
2. a route from problem structure into `validity_context`;
3. **`VariableToBulkLinkage`** — untouched by this decision and still the
   strongest input (§P, BREAKING-RISK 6);
4. non-uniform `InitialCondition` — which this milestone re-confirmed at
   Ledger 2, zero evidence gain, from a second direction: it is the one strict
   residue item the slab column has.

**What this milestone hands it, and it is small:** `col-slab` is now a measured
example of a domain whose conditions are compiled in rather than declared, with
an executed refusal proving reconstruction cannot carry a different profile.

**Explicitly NOT the next milestone**, each with its trigger:

| Deferred | Trigger that would pull it in |
|---|---|
| implementing `from_dict` for the three domains (option E) | a consumer that needs to persist one of them |
| option **G**, `prepare(problem, structure)` | a second external provider, or a concurrency requirement |
| a matrix-valued fifth residue column | building a structural or reaction-network domain — at which point BREAKING-RISK 1 must be re-run before this decision is relied on |
| publishing the parameter-name vocabulary via `ModelInputSpec` | a records-only consumer that must reconstruct without the bridge |
| domain package identity in provenance | remote or distributed execution |

---

# U. Deviations from the preregistration

Recorded here because §54.1 forbids back-writing them into the immutable
preregistration.

**D-1 — §9's rows overlapped and the rule needed an unpreregistered precedence.**
Two columns are non-empty under STRICT; rows 1 and 3 both matched; ledger rank
was applied to break the tie. Defensible under §67.3 and not preregistered as
precedence. The claim "the preregistered rule selects" is corrected to "the
preregistered rule **plus the §67.3 ledger rule** selects".

**D-2 — P-9's planner claim was overstated.** The reader answered all eight
questions, and four of the identifiers in those answers did not exist. Corrected
and now tested; the claim is restated in §K.

**D-3 — P-3 held under STRICT and failed under PLACEMENT.** `col-cstr` was
predicted **empty**. Its strict residue is empty, as predicted. Its placement
residue is **not**: the integration declaration has no persistable home because
`SolverSettings` hangs off runtime-only `PreparedSolve`. This is the most useful
single finding the measurement produced, and the prediction that missed it is
recorded rather than adjusted.

**D-4 — one attempt was refused for a reason other than the one recorded**, and
was the only attempt no test asserted. Corrected; see §P.

**D-5 — the slab's boundary records were decorative and unguarded.** Written to
prove representability, read by nothing, and able to describe physics the
execution did not perform. Guarded after the adversarial pass.

**Predictions that held:** P-1 (DC residue is incidence + terminal order), P-2
(slab residue is discretization + non-uniform IC, both Ledger 2), P-4 (material
empty), P-5 (exactly one Ledger-1 column under STRICT), P-6 (fresh-process
agreement), P-7 (ngspice unchanged, with the caveat in §J), P-8 (bind maps
survive), P-9's second half (connectivity unanswerable at L0 everywhere).

---

# V. Git

```text
b0e1353  Preregister executable scientific specification decision
<impl>   Exercise reconstructable scientific problem specification
```

`docs/architecture-study/08_CRAFTY_SELF_AUDIT.md` remains untracked and is **not**
part of this milestone. It was not cited as evidence; every fact reused from it
was independently re-verified against source and is cited to source above.
