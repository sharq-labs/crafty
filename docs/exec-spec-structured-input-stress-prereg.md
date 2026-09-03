# EXEC-SPEC STRUCTURED-INPUT STRESS — Preregistration

**Milestone:** `EXEC-SPEC-STRUCTURED` — a narrowly-scoped **reversal test** of one
unresolved condition in the `EXEC-SPEC` decision.
**Kind:** measurement. It is **not** a foundation milestone, not `FIELD0`, not
`TOPO0`, not an Equation IR, not `MatrixValue`, not a structural domain, not a
chemistry engine, not a planner.
**Decision status target:** the *existing* `EXEC-SPEC` decision may be
**KEPT / MODIFIED / REOPENED**. This milestone freezes nothing and creates no new
decision of its own.
**Evidence target:** `L1 EXERCISED` for what executes; `L0 REASONED` for
everything argued. **`L2` excluded outright.**
**Date:** 2026-09-03.
**Branch:** `exec-spec-structured-input-stress`, cut from `5c3962b`.
**Preregistered before any probe source was written.** Working tree verified
clean at `5c3962b` apart from one unrelated untracked file,
`docs/architecture-study/08_CRAFTY_SELF_AUDIT.md`, which is **not part of this
milestone**, is not read as canonical truth, and is not committed by it.

> **Immutable.** Results, deviations, corrections and adversarial findings go in
> `docs/exec-spec-structured-input-stress-evidence.md` and nowhere else.

**Milestones this one is conditional on:**

| Milestone | Decision | Evidence | Record |
|---|---|---|---|
| `CROSS-DOMAIN-COVERAGE` | none — freezes nothing | `L0` + measured matrix | `38783ed`, §68 |
| `EXEC-SPEC` | **`PROPOSED`** — no universal executable-specification record; per-domain **E + F** | `L1 EXERCISED` | prereg `b0e1353`, evidence `5c3962b` |

---

# 1. Why this milestone exists

`EXEC-SPEC`'s own evidence records the limit it is being run against, verbatim:

> The four columns are all scalar-parameter domains, while
> `experiments/cross_domain_coverage/mechanics.py` and `species.py` — committed
> and executed last milestone — both carry matrix-valued structure and were
> **not** columns. Under §9 either would produce a second Ledger-1 residue.
> **Before this decision is relied on by a structural or reaction-network domain,
> that fifth column must be run.**

This is that run. It is deliberately two columns rather than one, because the
question is not *"is there a residue?"* — `CROSS-DOMAIN-COVERAGE` already answered
that — but *"do two unrelated sciences force the **same** expensive-to-reverse
abstraction?"*

---

# 2. The single question

> Do Structural Mechanics and Reaction/Species **independently force the same**
> expensive-to-reverse universal abstraction for structured scientific inputs?

Admissible outcomes, none preferred:

| | Outcome | Consequence for `EXEC-SPEC` |
|---|---|---|
| **A** | same universal shape forced | **REOPEN** |
| **B** | different domain-owned structures | **KEEP**, strengthened |
| **C** | existing contracts suffice | **MODIFY** — reduce further |
| **D** | mixed | **KEEP `PROPOSED`** + preregistered reversal triggers |

**A is not assumed.** A milestone that returns B, C or D has succeeded if it
records precisely why.

---

# 3. Roadmap position — recorded

**D-A.** `MIN-FOUNDATION-PDE` (§68 §11) is deferred by one more milestone. This
is its **second** deferral. `EXEC-SPEC` §T recorded that its four questions stand
untouched; that remains true and this milestone consumes none of them.

**D-B.** `API / MCP v0` is deferred for a **fourth** time (§61 order; deferred by
§67, §68, `EXEC-SPEC`, and now here). §61 self-describes as risk-driven rather
than frozen and §54.2 states work packages are pulled by a proof. Recorded
because it is the fourth.

**D-C.** This milestone was directed by the founder as a reversal test rather
than selected by a reviewer. `architecture-decision-reviewer` is therefore
invoked **after** the residue table exists (§16 of the brief), not before — the
reverse of `EXEC-SPEC`'s order, and recorded as a difference in method.

---

# 4. Hypotheses

**H1 (the reversal hypothesis).** Mechanics and Species force the same universal
structured-input abstraction, and `EXEC-SPEC` must be reopened.

**H0.** They force **different** domain-owned structures that share no scientific
semantics, and `EXEC-SPEC`'s per-domain answer survives contact with two
non-scalar sciences.

**H2 (added, and it must be allowed to win).** They share an *infrastructure*
shape — identity, schema/version, deterministic serialization, digest — without
sharing a *semantic* one. If so the answer is neither A nor B but the small
shared invariant plus strong domain schemas, and the correct output is a
preregistered set of reversal triggers rather than a new record.

---

# 5. Measured baseline facts

Read from the committed probes at `5c3962b`, before any file of this milestone
was written.

| # | Fact | Location |
|---|---|---|
| **B1** | Mechanics' structured inputs are **module-level constants**: `NODES` (4×2 floats), `ELEMENTS` (2×3 ints), `CLAMPED_DOF` (4 ints), `SHEAR_FORCE_N`, `YOUNGS_MODULUS_PA`, `POISSON_RATIO`, `THICKNESS_M` | `mechanics.py:84-97,273-275,57-59` |
| **B2** | `constitutive_matrix()` **takes `youngs_modulus_pa` and `poisson_ratio` as parameters** and derives `D` from them plus the `PlaneAssumption` | `mechanics.py:100-138` |
| **B3** | `global_stiffness()` and `element_geometry()` read `NODES`/`ELEMENTS` from module scope; they cannot be given reconstructed geometry | `mechanics.py:156-193` |
| **B4** | `PlaneAssumption` changes the constitutive law and therefore `sigma_zz`; its own docstring calls two problems differing only in it *"different physics with an identical mesh, identical loads and identical unknowns"* | `mechanics.py:65-77` |
| **B5** | Species' `STOICHIOMETRY` is a 2×3 integer table at module scope, documented as having **no typed home**: *"`ScientificValue` is a closed union of scalars, so a `ScientificParameter` cannot carry a matrix"* | `species.py:69-76` |
| **B6** | `CONSERVED_WEIGHTS = (1,1,2)` is derived from the null space of `nu` and is documented as *"NOT something a records reader could recover"* | `species.py:78-81` |
| **B7** | `BatchCase` is a frozen dataclass taking **every** scalar as a field; `integrate(case)` consumes it. `derivative()` reads `STOICHIOMETRY`/`SPECIES` from module scope | `species.py:84-118,171-210` |
| **B8** | `naive_total` exists so the finding is measured: the **unweighted** sum is not conserved, and its drift is the size of the error a reader without `nu` would report | `species.py:217-238` |
| **B9** | `case_metrics` (mechanics) and `state_metrics` (species) are documented as the place where rank-1/rank-2 quantities are *"crushed into numbers small enough for the control plane"* | `mechanics.py:406`, `species.py:281` |
| **B10** | `EXEC-SPEC`'s records-only reader carries per-column schema knowledge — an element-key table and a closed `KNOWN_STRUCTURE_SCHEMAS` map — recorded there as the unmeasured *domains × consumers* cost of option E | `exec_spec_residue/instrument.py:126-142`, `EXEC-SPEC` §K.2 |
| **B11** | `SolverSettings` is typed, round-trips, and is a field of runtime-only `PreparedSolve`; no persistable record reaches it | `EXEC-SPEC` §D.3, `solvers/protocol.py` |
| **B12** | `ScientificDataReference` carries `{name, unit, count, dtype, digest, digest_algorithm}` and **no field naming a variable or an ordering** | `results/data_reference.py` |

---

# 6. The two columns

```text
col-mech     experiments/cross_domain_coverage/mechanics.py   CASE A2 (shear), plane stress
col-species  experiments/cross_domain_coverage/species.py     CASE C1 (both reactions)
```

**The committed probes are the forcing cases and are not edited.** Their physics
modules import nothing from `engcore`, which is what lets a bridge be written
against them without the science reaching into the representation.

**Classification required per item**, per the brief: `SCALAR EXISTING CONTRACT` /
`NON-SCALAR SCIENTIFIC STRUCTURE` / `DOMAIN STRUCTURE` / `CONSTITUTIVE RELATION` /
`DISCRETIZATION` / `RUNTIME-PREPARED`.

**Two distinctions are binding and must not be collapsed:**

* constitutive `D` **≠** assembled `K`. `K` is derived numerical state.
* scientific reaction-network structure **≠** integrator configuration.

---

# 7. The zero-new-universal-contract attempt

For both columns, in this order:

1. **L2 steelman** — every representable fact into a channel that already
   exists: `ScientificParameter`, `ScientificVariable`, `InitialCondition`,
   `BoundaryCondition`, `ScientificDataReference`. **No new universal record. No
   `src/` change. `metadata` is not a channel.**
2. **Domain-owned versioned structure payload** for whatever L2 cannot hold,
   carrying a schema string, deterministic serialization and a digest.
3. **Fresh-process reconstruction** — a separate interpreter, given serialized
   records only.

**Two grades of reconstruction are distinguished, and the weaker one must be
labelled as such:**

* **INJECTED** — the reconstructed value is *consumed by the computation*.
* **VERIFIED-EQUAL** — the reconstructed value is compared field-by-field
  against the probe's ground truth, and the probe then executes from its own
  module constants.

**B3 forces VERIFIED-EQUAL for the mechanics geometry**, because the probe reads
its coordinates and connectivity from module scope and this milestone may not
edit it. Reporting that as INJECTED is a fail condition (§13.5).

Two **injection** tests are required, because they carry the milestone's two
central claims:

* **INJ-1 (mechanics).** Recompute `D` from the *reconstructed* `E`, `nu` and
  assumption via `constitutive_matrix(...)`, and compare against the probe's `D`.
  This tests whether the constitutive matrix is irreducible input.
* **INJ-2 (species).** Integrate `dc/dt = nu^T r` from the *reconstructed*
  stoichiometry, rate constants and initial state with the probe's own RK4
  scheme reimplemented in ≤ 30 lines inside `experiments/`, and compare the
  trajectory against the probe's. This tests whether the record carries the
  stoichiometric meaning.

INJ-2's twenty lines are a probe, not a chemistry engine. If it grows beyond the
two reactions and three species of the committed case, it has violated §12.

---

# 8. Preregistered predictions

Stated so they can be wrong.

| # | Prediction | Falsified by |
|---|---|---|
| **P-1** | The mechanics residue does **not** include `D`. `D` is derivable from two scalars and one category, all representable today (B2) | INJ-1 disagreeing with the probe's `D` |
| **P-2** | The mechanics residue **is**: node coordinates, element connectivity, the constrained-DOF set, and the load's DOF indexing | any of the four turning out representable, or a fifth item appearing |
| **P-3** | The species residue **is** the stoichiometric matrix, and it is **not** derivable from anything on any record | deriving `nu` from typed records without parsing a name |
| **P-4** | The two residues share an **infrastructure** shape (named index sets + an integer table whose ordering is load-bearing) and **not** a scientific semantics — outcome **D**, not **A** | a shared semantic statement a records-only planner could act on |
| **P-5** | Both columns reconstruct in a fresh process with **no new universal record** | either failing |
| **P-6** | Both columns force the **same** `VariableToBulkLinkage` need — a bulk reference that names the variable(s) and the component ordering it instantiates — and this is **stronger** shared evidence than any matrix abstraction | the two needing different linkages |
| **P-7** | A records-only reader needs **per-schema knowledge** for each new column, so option E's *domains × consumers* cost is real and measurable as a diff | the existing reader answering the structure question for either column unchanged |
| **P-8** | `SolverSettings`: mechanics has **none** (a direct linear solve), species has `n_steps`, which materially determines the result. The gap classifies differently per column | both classifying identically |
| **P-9** | The conserved weights `(1,1,2)` are recoverable **only** from the stoichiometry, and a reader without it reports a violated conservation law for a perfectly conserved system | the naive sum being conserved, or the weights being derivable otherwise |

---

# 9. The universality test

Every candidate shared abstraction is scored against one question, and it is a
rejection test rather than a selection test:

> Would a records-only planner understand the **scientific meaning** without
> domain source code — or would the abstraction merely say *"here is a matrix"*?

Candidates to be scored:

```text
A  generic StructuredScientificValue
B  generic relation/coefficient artifact
C  domain-owned typed structural records sharing ONLY identity, schema/version,
   serialization and digest/reference
D  bulk-data/reference linkage only
E  no shared abstraction beyond existing records
```

**Binding rule:** two things are not the same abstraction because both are
matrices. A constitutive tensor and a stoichiometric matrix may share numerical
shape and share no meaning. A candidate that survives only on shape is recorded
as **false universality** and rejected.

---

# 10. Residue recording requirements

For every residue item, all nine, or the item is not recorded:

semantic meaning · shape/rank · does it scale with problem size · is it
domain-specific · does an analogous residue exist in the other column · does
changing it change scientific identity · does changing it only change
discretization · does it belong in provenance · does it belong under
DATA-BOUNDARY0.

---

# 11. Required tests

| # | Test |
|---|---|
| **A** | mechanics fresh-process reconstruction |
| **B** | species fresh-process reconstruction |
| **C** | results agree with the committed probes' executed baseline |
| **D** | corrupted structure rejected |
| **E** | unsupported structure schema rejected |
| **F** | relocation does not change scientific identity |
| **G** | records-only reader recovers the structure where claimed — and fails visibly where not |
| **H** | no universal core production change |
| **I** | existing milestone regressions green |
| **INJ-1** | `D` recomputed from reconstructed scalars equals the probe's `D` |
| **INJ-2** | trajectory integrated from reconstructed stoichiometry equals the probe's |
| **NEG** | a reader without the stoichiometry reports a violated conservation law (P-9) |

Targeted, **FAST**, **FULL**, all reported with exact counts.

---

# 12. What is forbidden

1. **No modification of `src/engcore/`** — asserted by test. If the decision is
   genuinely reopened, production change belongs to a later milestone with its
   own preregistration.
2. **No edit to `experiments/cross_domain_coverage/`** — committed evidence for
   an accepted milestone.
3. **No edit to `experiments/exec_spec_residue/`** — committed evidence for
   `EXEC-SPEC`. A reader extension is written *beside* it, and the extension is
   itself a measurement (P-7).
4. **No structural mechanics domain, no chemistry engine, no Equation IR, no
   `MatrixValue`, no generic topology, no generic relation graph, no artifact
   repository, no planner, no Field semantics.**
5. **No pickle, no `eval`/`exec`, no import-path execution, no callables in
   records.** A persisted problem stays data.
6. **No `ScientificProblem` schema bump**; `scientific_problem/1` untouched.
7. **No `L2` claim**, no upgrade to any existing holding, no new evidence level.
8. **No new universal record proposed** unless the reviewer *and* the falsifier
   both support reopening — and even then, its design belongs to the next
   milestone, not this one.
9. `docs/architecture-study/08_CRAFTY_SELF_AUDIT.md` is neither cited as evidence
   nor committed.

---

# 13. Fail conditions

1. Outcome **A** declared without a shared **semantic** statement a records-only
   planner could act on.
2. Two residues called "the same abstraction" on shape alone.
3. A residue item recorded without all nine attributes of §10.
4. A residue declared without a demonstrated failed encoding attempt against
   every applicable existing channel.
5. A **VERIFIED-EQUAL** reconstruction reported as **INJECTED**.
6. The fresh-process test satisfied by a same-process round trip, or process 2
   inheriting state from process 1.
7. Any file under `src/`, `experiments/cross_domain_coverage/` or
   `experiments/exec_spec_residue/` modified.
8. An existing test edited, skipped, deleted, reordered, or a tolerance loosened.
9. The evidence claiming a capability that was reasoned rather than executed.
10. INJ-2 growing past the committed case's two reactions and three species.

---

# 14. Evidence ceiling

* **`L1 EXERCISED`** — the two reconstructions, the two injections, the
  fresh-process runs, relocation, the negative cases, the reader diff.
* **`L0 REASONED`** — every universality verdict, every residue classification,
  and any statement about domains not measured here.
* **`L2` is excluded.** Two probes reconstructed by one author on one day against
  a bridge that author wrote is exercise, not differentiation.
* The `EXEC-SPEC` decision's status may not rise above **`PROPOSED`** as a result
  of this milestone. It may fall to **REOPENED**.

---

# 15. What the evidence document must refuse to claim

* That mechanics or species is now a supported domain.
* That the result generalizes to meshes, anisotropic materials, large reaction
  networks, or any consumer not measured here.
* That `EXEC-SPEC` is settled. It stays `PROPOSED` whatever this returns.
* That the absence of a forced universal record means no universal record is
  forced anywhere — `VariableToBulkLinkage` is separately forced by four
  consumers (§68.2) and is untouched by this measurement.
* That a VERIFIED-EQUAL reconstruction demonstrates the same thing an INJECTED
  one does.

---

# 16. Review and falsification

* `architecture-decision-reviewer` is invoked **after** the residue table exists,
  on: *"Do the Mechanics and Species structured-input residues justify reopening
  the EXEC-SPEC decision and introducing a universal structural/relation
  abstraction?"* It must compare at least the four candidates in §9.
* `architecture-falsifier` is invoked on the result, with the primary attack
  preregistered here: *"Prove that the proposed shared abstraction exists only
  because both test cases contain arrays, while their scientific meanings are
  unrelated."* Stress cases: circuit topology · PDE mesh · material property
  table · finite-element constitutive tensor · chemical stoichiometric network ·
  control-system matrices · experimental lookup table.

Both verdicts are recorded whether or not they support the outcome.

---

# 17. Stop rule

The milestone ends when: both residue tables are complete under §10, both
fresh-process reconstructions have returned a result or an explicit NOT RUN, the
reviewer and falsifier have reported, and `EXEC-SPEC` has been marked KEEP,
MODIFY or REOPEN with the reversal triggers written down.

**It does not design a record**, whatever the outcome. If reopening is
warranted, the design is the next milestone's preregistration.

---

# 18. Placement

```text
experiments/exec_spec_structured/                       probes, bridge, reader extension
tests/test_exec_spec_structured_input.py
docs/exec-spec-structured-input-stress-prereg.md        this file
docs/exec-spec-structured-input-stress-evidence.md      written after execution
```

Nothing under `src/`.
