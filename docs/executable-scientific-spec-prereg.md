# EXECUTABLE SCIENTIFIC SPECIFICATION DECISION — Preregistration

**Milestone:** `EXEC-SPEC` — decide the smallest durable architectural relationship
between `ScientificProblem` and the typed scientific structure required to
reconstruct and execute it.
**Kind:** architecture decision, gated on a measurement. It is **not** `FIELD0`,
`TOPO0`, `DISC0`, an Equation IR, a planner, API/MCP, a remote runtime, an
artifact repository, or a domain migration.
**Decision status target:** a decision **is** expected. Its status ceiling is
`PROPOSED`. `DESIGN-FROZEN` is **excluded** by this document.
**Evidence target:** `L1 EXERCISED` for whatever is executed, across two
materially different domains. `L2 DIFFERENTIATED` is **excluded outright** — see
§14.
**Date:** 2026-09-03.
**Branch:** `executable-scientific-spec-decision`, cut from `38783ed`.
**Preregistered before implementation.** Working tree verified clean at `38783ed`
apart from one unrelated untracked file, `docs/architecture-study/08_CRAFTY_SELF_AUDIT.md`,
which is **not part of this milestone** and is neither read as canonical truth nor
committed by it.

> **This file is immutable.** It records what was committed to *before* results
> were observed. Executed results, deviations, corrections, adversarial findings
> and the final decision go in `docs/executable-scientific-spec-evidence.md` and
> nowhere else.

**Canonical milestones verified present before this document was written:**

| Milestone | Decision | Evidence | Record |
|---|---|---|---|
| `DATA-BOUNDARY0` | `PROPOSED` | `L1 EXERCISED` | master context §56 |
| `MODEL0-R` differential | `DESIGN-FROZEN` | `L2 DIFFERENTIATED` (scoped) | §58 |
| `MIN-FOUNDATION-ET` | `PROPOSED` | `L1 EXERCISED` | §64 |
| `ET-VERTICAL` | `PROPOSED` | `L1 EXERCISED` | §65 |
| `HETERO-NGSPICE` | `PROPOSED` | `L1 EXERCISED` | §66 |
| `HOSTILE-CORE-STRESS` | none — freezes nothing | `L0` + measured gaps | §67 |
| `CROSS-DOMAIN-COVERAGE` | none — freezes nothing | `L0` + measured matrix | §68 |

---

# 1. The single question

> What is the smallest, durable architectural relationship between
> `ScientificProblem` and the typed scientific structure required to reconstruct
> and execute it?

The answer must eventually allow Crafty to persist a scientific problem,
reconstruct it in a fresh process, transmit it to another machine, inspect it
without domain source-code knowledge, plan against it, choose
realizations/providers, execute it without hidden in-memory domain state, and
reproduce the execution from records and referenced artifacts.

**It is not assumed that the answer is a new class**, and specifically not one
named `ExecutableScientificSpecification`.

---

# 2. Roadmap deviation — recorded, not assumed

`CROSS-DOMAIN-COVERAGE` (§68 §11) names the next milestone as
**`MIN-FOUNDATION-PDE`**, with a binding entry condition (*a real consumer, not
another probe*) and four scoped questions. **This milestone is not one of those
four, and running it defers `MIN-FOUNDATION-PDE` by one.**

Recorded consequences, stated in advance rather than discovered later:

* **D-A.** This is the **third consecutive deferral of `API / MCP v0`** (§61
  order; deferred by §67, §68, and now here). §61 self-describes as risk-driven
  rather than frozen and §54.2 states work packages are pulled by a proof, so the
  reordering is permitted. It is recorded because it is the third.
* **D-B.** `MIN-FOUNDATION-PDE`'s four questions are **not** consumed, blocked or
  answered here. Two of them — `DiscretizationDefinition` and non-uniform
  `InitialCondition` — are expected to appear in this milestone's residue. Where
  they do, they are booked **Ledger 2, zero evidence gain**, as re-confirmations
  of an existing deferral, never as new findings (§67.3 booking rule).
* **D-C.** The `architecture-decision-reviewer` was invoked **before** this
  document was written and returned **SPIKE REQUIRED**, not a selected option.
  This preregistration therefore commits to a *measurement plus a decision rule*,
  and not to an architecture. That is the deviation from the milestone brief's
  expectation that an option would be selected up front.

---

# 3. Hypotheses

**H1.** A small typed relationship can make current Crafty scientific problems
persistable and reconstructable without collapsing scientific semantics into
domain implementation artifacts.

**H0.** The current `ScientificProblem` abstraction is too shallow or incorrectly
scoped, and supporting executable reconstruction requires a deeper redesign of
problem representation.

**H0 must be allowed to win, and a third outcome must also be allowed to win:**

**H2 (added by the reviewer's evidence, preregistered here so it can win).** The
gap is **not uniform across domains**. Some domains carry irreducible scientific
structure that no existing contract can hold; others merely **under-populate
typed contracts that already exist**. If so, no universal record is forced, and
the correct answer is per-domain rather than architectural.

A milestone that returns H2 has **not failed**. Returning "we need a new
universal contract" when the measurement does not force one is the failure.

---

# 4. Reviewer verdict, carried verbatim

`architecture-decision-reviewer`, invoked 2026-09-03 against options A–E supplied
by the milestone brief, returned:

> **SPIKE REQUIRED.**

Its reasoning, recorded because this document is bound by it:

* The five supplied options differ on **two independent axes** — *placement of the
  link* and *what the linked thing must satisfy* — which must not be decided
  together.
* **Option B (promote structure into `ScientificProblem`) is rejected** on
  evidence, not taste: §68.3 deviation **D-4** already withdrew, under
  falsification, the claim that `electrical/dc` forces universal topology,
  because connectivity travels by a separate typed channel bound by a verified
  fingerprint. B asks to reverse a falsifier-tested finding, and it violates the
  frozen layer separation in `07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md`.
* **Option D (registered builder) is rejected**: a builder keyed by schema
  identity means the record alone is never sufficient — the domain package must
  be installed at a compatible version — which defeats "reconstructed in a fresh
  process" and "transmitted".
* **If** a universal record turns out to be forced, its placement is **C**
  (standalone sibling), for the reason recorded verbatim for `QuantityDependency`:
  `require_schema` is exact-match with no migration path, so an inline field on
  `ScientificProblem` makes every stored payload unreadable by a pre-milestone
  reader.
* Two options the brief did not list were added and are in scope here:
  **F — contract-level reduction, no new record** (move every representable fact
  into a typed channel that already exists), and **G — `prepare(problem,
  structure)`** (kill the bind maps at the protocol boundary). G is **out of
  scope for this milestone** and is recorded as a separate future decision.
* **The deciding measurement has never been taken.** The `CROSS-DOMAIN-COVERAGE`
  matrix has no executability row.

---

# 5. Measured baseline facts

Read from this working tree at `38783ed`, before any file of this milestone was
written. These are **facts**, and every prediction in §8 is stated against them.

| # | Fact | Location |
|---|---|---|
| **B1** | No domain executes from records. Five bind sites: `bind_circuit` (native and ngspice), `bind_slab`, `bind_run`, `bind_conductor`. A sixth binds geometry *and a realization* | `dc/solver.py:98`, `ngspice.py:493`, `conduction1d/solver.py:162`, `cstr/solver.py:287`, `material.py:496`, `thermal_conduction1d_schemes.py:454` |
| **B2** | The universal IR is documented as insufficient **by the domains themselves**: *"the universal IR carries no topology"*, *"…carries no geometry"*, *"…carries neither"* | `dc/solver.py:152`, `conduction1d/solver.py:205`, `thermal_conduction1d_schemes.py` |
| **B3** | Three domains independently invented **incompatible untyped artifact references inside `ScientificProblem.metadata`**: four keys (DC), `slab_fingerprint` (thermal), `physics_fingerprint` (kinetics) | `dc/problem.py:44-47,199-202`; `conduction1d/problem.py:429`; `cstr/problem.py:966,978` |
| **B4** | `def from_dict` exists under `src/engcore/domains/` **only** in electrical DC (5 classes). `ConductionSlab` and `ReactorRun` have `to_dict` and no reader. `ThermalBody` and `TemperatureDependentConductor` have neither | repo-wide grep |
| **B5** | `DCCircuit` already carries the full pattern: `CIRCUIT_SCHEMA` round-trip, unit-normalised `canonical_dict()` excluding labels and preserving terminal order, SHA-256 `fingerprint()` | `dc/circuit.py:25-26,137-244` |
| **B6** | **The DC problem declares the wrong schema.** `DOMAIN_ARTIFACT_SCHEMA_KEY` is set to `CANONICAL_SCHEMA` (`electrical_dc_circuit_canonical/1`) — the fingerprint preimage, which has **no `from_dict`**. The round-trippable schema is `electrical_dc_circuit/1` | `dc/problem.py:201`; verified independently |
| **B7** | **`ConductionSlab.fingerprint()` excludes the discretization by design**, and hard-codes the boundary and initial conditions as the string literals `"dirichlet_zero_both_ends"` and `"sin(pi x / L)"` inside the identity preimage. `with_discretization()` exists to vary resolution at constant identity | `conduction1d/problem.py:304-338`; verified independently |
| **B8** | **`build_cstr_problem` writes zero `InitialCondition` records** for two scalar initial values `InitialCondition` accepts today, so `problem.is_time_dependent` is `False` for a transient ODE domain. Integration settings travel as `repr()` strings in metadata | `cstr/problem.py:941-973`; verified independently |
| **B9** | `verify_problem_matches_conductor` compares the conductor against **typed `ScientificParameter` values**, not a fingerprint; the bind caches `(conductor, temperature)` where temperature is runtime state | `material.py:526-541` |
| **B10** | Every field of `ReactorChemistry`, `ReactorOperation` and `ReactorRun` is a scalar `Quantity`, a string, or a numerical setting. No non-scalar structure | `cstr/problem.py:416-723` |
| **B11** | `ThermalBody`'s own docstring already draws the split this milestone is about: ambient is a `CONTROL`, initial temperature *"a state at one instant"*, duration *"an integration window"* — *"an operating point, not a system"* | `thermal_lumped.py:378-388` |
| **B12** | Prior art for identity-not-location: `ScientificDataReference` = `{name, unit, count, dtype, digest, digest_algorithm}`, no path/URI/store; relocation leaves it byte-identical | `results/data_reference.py` |
| **B13** | `require_schema` is exact-string match with no migration path; version bumps are additive with explicit `SUPPORTED_*` tuples | `scientific/serialization.py:26-55` |
| **B14** | `BoundaryCondition` has **zero producers** in `src/engcore/domains/` | repo-wide grep |
| **B15** | **No consumer exists** for persist / reconstruct-in-fresh-process / transmit / records-only planning / remote execution anywhere outside `tests/` and `experiments/`. `scientific/` has `to_json` and no persistence | repo-wide |
| **B16** | `SolverRegistry` returns stored solver instances; solvers hold mutable per-problem dicts | `solvers/registry.py`, the five bind sites |
| **B17** | No representation of a governing relation exists anywhere: no stoichiometric matrix, no constitutive matrix, no algebraic relation among unknowns | §68.4 |

---

# 6. The measurement — `EXEC-SPEC-RESIDUE`

**Question.** *After a maximal honest re-encoding of each existing domain into
typed contracts that already exist, what information remains that no existing
contract can carry?*

**Four columns**, the four production domains that bind an artifact:

```text
col-dc        src/engcore/domains/electrical/dc/          network / lumped
col-slab      src/engcore/domains/thermal/conduction1d/   1-D transient PDE
col-cstr      src/engcore/domains/kinetics/cstr/          stiff nonlinear ODE
col-material  src/engcore/domains/electrical/material.py  constitutive property
```

**Four information levels**, measured per column:

| Level | What the reader is given |
|---|---|
| **L0** | `ScientificProblem.to_dict()` alone |
| **L1** | L0 + the domain artifact serialized by its **existing** `to_dict()`, where one exists |
| **L2** | **The binding steelman.** The re-encoding may move *every representable fact* into a typed channel that already exists — `ScientificParameter`, `InitialCondition`, `BoundaryCondition`, `SolverSettings.tolerances/options`, `ScientificDataReference`. **No core change and no domain-source change is permitted.** |
| **L3** | The **residue** at L2: what remains that no existing contract can carry |

**The steelman is binding.** As `HOSTILE-CORE-STRESS` §67.2 established, no gap
may be declared before a maximal honest attempt in existing typed contracts. A
residue item declared without a demonstrated failed encoding attempt is a **fail
condition** (§13.3).

**Instrument.** One records-only reader, handed serialized payloads only. It may
import `engcore.scientific` — a records reader legitimately knows its schema — and
**may not import any module under `src/engcore/domains/`**, asserted by AST scan,
not by convention. Writing a per-column reader is a fail condition (§13.4).

---

# 7. The reconstruction proof

The measurement decides the architecture; the proof falsifies it. Both are
required, and the proof runs on **two materially different domains** at minimum.

**CASE A — electrical DC (network).** Persist enough typed information to
reconstruct an equivalent `DCCircuit` in a **fresh interpreter process** without
the original in-memory object, then execute the native MNA path and compare
against the in-process baseline.

**CASE B — thermal conduction 1-D (transient PDE).** Same, for the slab.

**CASE C — kinetics CSTR (stiff nonlinear ODE).** Same, for the reactor run.

A **test-only bridge is permitted and expected**: reconstruction code lives under
`experiments/`, never under `src/`. No domain is migrated. `src/engcore/` is not
modified by this milestone at all (§12.1).

**Fresh process is mandatory and is not simulated.** Process 1 writes records to
a directory and exits. Process 2 is a **separate interpreter invocation** that
loads the records and executes. No object graph, module-level registry, cache or
import state may cross between them. A same-process round trip does not satisfy
this and is a fail condition (§13.5).

**Relocation.** Serialized records are moved to a second directory and
reconstructed there. Scientific identity — fingerprints and any content digest —
must be unchanged. No absolute path may appear in any scientific identity
(DATA-BOUNDARY0 principle, B12).

**Planner inspectability.** The records-only reader must answer, before
execution and without importing domain code: problem type; participating
quantities; structure/connectivity where present; conditions; required
capabilities; bound or selectable models; required inputs; producible
outputs/QoIs. Domain-specific **typed schemas** are permitted. Domain-specific
**hidden semantics** are not.

**External provider.** The ngspice adapter must accept the **reconstructed**
electrical structure — no original in-memory `DCCircuit`, no inherited bind
state, no new provider-specific scientific semantics — and agree with the native
path within the tolerance `HETERO-NGSPICE` already preregistered. If ngspice is
unavailable in the environment, that case is reported as **NOT RUN**, never as
passed.

---

# 8. Preregistered predictions

Stated so they can be wrong. The first four are the reviewer's, adopted verbatim
so that a disagreement between its code reading and the executed result is
visible rather than absorbed.

| # | Prediction | Falsified by |
|---|---|---|
| **P-1** | `col-dc` residue is **non-empty**: node/terminal incidence, the reference node, and terminal *order* as a sign convention | reconstructing an executable circuit from L2 records alone |
| **P-2** | `col-slab` residue is **non-empty** and consists of `SlabDiscretization` plus a non-uniform initial condition — **both Ledger 2**, both already-recorded `MIN-FOUNDATION-PDE` deferrals | a residue item that is neither |
| **P-3** | `col-cstr` residue is **empty** | any fact needed to execute that no existing typed channel accepts |
| **P-4** | `col-material` residue is **empty** | same |
| **P-5** | Exactly **one** column returns a Ledger-1 residue, so **no universal record is forced** and the decision rule selects the per-domain answer | two or more columns returning same-shaped Ledger-1 residue |
| **P-6** | Fresh-process reconstruction succeeds for all three executed cases and reproduces the in-process metrics to within each domain's own tolerance | any case that cannot be reconstructed or disagrees |
| **P-7** | ngspice accepts the reconstructed circuit with **no change to the adapter** | an adapter edit being required |
| **P-8** | Reconstruction **does not by itself remove** the solver bind maps; statelessness needs a protocol change (option G), which is out of scope | the bind map becoming unnecessary without touching `prepare` |
| **P-9** | The reader can answer every planner question for `col-dc` at L1 and **cannot** answer the connectivity question for any column at L0 | either half failing |

**A predicted-empty residue that returns non-empty is the most valuable outcome
available and must be reported as a win for the measurement**, not softened.

---

# 9. The decision rule — binding, written before execution

Carried from the reviewer and **not revisable after results are seen**:

| Measured residue | Decision |
|---|---|
| Non-empty for **exactly one** column | **No universal record.** Answer is **E + F**: state the artifact contract for the one domain that has irreducible structure; reduce the other three into contracts that already exist |
| Non-empty for **≥ 2 columns with the same shape** | A universal record is justified. Placement is **C** — a standalone sibling record, never an inline field on `ScientificProblem` (B13) |
| Only `SlabDiscretization` + non-uniform `InitialCondition` | **Ledger 2, zero evidence gain.** Re-confirmations of `MIN-FOUNDATION-PDE` deferrals, not new findings |
| Empty everywhere | The entire proposal set is withdrawn; the finding is that domains under-populate contracts they already have |

**Option B is excluded before execution** on §4's recorded evidence. **Option D
is excluded** on the record-insufficiency argument. Neither may be selected by
this milestone whatever the residue shows.

---

# 10. Required attacks

1. **Attack `ScientificProblem`.** Do not preserve it because it exists. Decide
   between: correctly scoped but incomplete / should become richer / is one layer
   inside a larger specification. Report which fields belong elsewhere.
2. **Attack the artifacts.** Classify every field of `DCCircuit`,
   `ConductionSlab`, `ReactorRun`, `ThermalBody` and
   `TemperatureDependentConductor` as SCIENTIFIC SEMANTICS / SCIENTIFIC STRUCTURE
   / MODEL PARAMETER / CONDITION / DISCRETIZATION / RUNTIME / PROVIDER-SPECIFIC.
   If an artifact already holds the right structure, do **not** rebuild it in a
   parallel universal structure for elegance.
3. **Reduction attack on whatever wins.** Can it be removed in favour of
   serializing the existing artifact, enriching the problem, a typed reference, or
   a builder — while preserving reconstructability, planner inspectability,
   provenance and domain extensibility?
4. **Duplicate-truth attack.** `R:`/`Vs:`/`Is:` already exist as
   `ScientificParameter` *and* inside `DCCircuit`. Report which is authoritative
   and whether the chosen design increases or reduces the duplication.
5. **`ScientificTwin`.** Determine whether it has any necessary role here. Five
   consecutive milestones record zero evidence for instance authority. If the
   selected architecture does not need it, leave it alone and say so.

---

# 11. Negative tests — required

| # | Case | Required behaviour |
|---|---|---|
| **N-A** | executable structure missing | deterministic typed failure, not a guess |
| **N-B** | problem/structure identity mismatch | refused |
| **N-C** | corrupted serialized structure | refused |
| **N-D** | unsupported schema version | loud failure |
| **N-E** | valid `ScientificProblem`, required structure absent | no execution |
| **N-F** | structure for the wrong domain/problem | no silent bind |

---

# 12. What is forbidden

Absolute. Violating any of these invalidates the evidence.

1. **No modification of `src/engcore/scientific/`.**
2. **No modification of any file under `src/engcore/domains/` or
   `src/engcore/systems/`.** This milestone is decision-first; the residue is
   measured against the domains **as they stand**.
3. **No file under `src/engcore/` added or edited at all.** If the decision later
   requires production code, that is a separate implementation milestone with its
   own preregistration.
4. **No Equation IR, no `Mesh`, no `FieldDefinition`, no `TOPO0`, no `DISC0`, no
   planner, no API/MCP, no remote runtime, no artifact repository.**
5. **No pickle, no `eval`/`exec`, no import-path execution, no callables in
   records, no shell commands as specification.** A persisted scientific problem
   must remain data.
6. **No `ScientificProblem` schema bump.** `scientific_problem/1` is untouched.
7. **No unfreezing of `src/engcore/domains/thermal/`**, byte-pinned by three
   frozen experiments; §57.1 forbids improvising an unfreeze mechanism.
8. **No claim of `L2 DIFFERENTIATED`** and no upgrade to any existing holding.
9. **No new evidence level invented.**
10. **`docs/architecture-study/08_CRAFTY_SELF_AUDIT.md` is not committed by this
    milestone** and is not cited as evidence. It is an AI-authored analysis
    snapshot; every fact reused from it was independently re-verified and is cited
    to source above.

---

# 13. Fail conditions

1. A decision is declared without the residue measurement having been executed.
2. Option B or D is selected.
3. A residue item is declared without a demonstrated failed encoding attempt
   against every applicable existing typed channel (§6).
4. A per-column reader is written instead of one shared instrument.
5. The fresh-process test is satisfied by a same-process round trip, or process 2
   inherits any state from process 1.
6. Any file under `src/engcore/` is modified.
7. An existing test is edited, skipped, deleted, reordered, or has a tolerance
   loosened.
8. The evidence document claims a capability that was reasoned rather than
   executed, or reports a NOT RUN case as passed.
9. The decision rule in §9 is revised after results are observed.
10. `L2` is claimed, or any existing holding is upgraded.

---

# 14. Evidence ceiling, declared before running

* **`L1 EXERCISED`** for: whatever reconstruction actually executes, per case.
* **`L0 REASONED`** for: every residue item that is argued rather than exercised,
  and for every statement about domains not measured here.
* **`L2 DIFFERENTIATED` is excluded outright.** Two domains reconstructed by one
  author on one day against a bridge that author wrote is *exercise*, not
  differentiation — the trap `HETERO-NGSPICE` §66.3 fell into and withdrew from.
* The decision's status ceiling is **`PROPOSED`**. Nothing here may be called
  `DESIGN-FROZEN`.

---

# 15. What the evidence document must refuse to claim

* That Crafty can persist and reconstruct *arbitrary* scientific problems.
* That the architecture generalizes to meshes, fields, distributed solvers,
  long-running providers or remote execution — none is tested.
* That reconstruction implies reproducibility. Reproducibility additionally needs
  provenance fields this milestone does not add (seed, artifact identity,
  non-scalar inputs).
* That the residue is complete. It is complete **for four domains as they stand
  today**, measured by one instrument.
* That the relation/equation gap is addressed. It is not, and §16 records exactly
  what it still blocks.

---

# 16. The relation gap — classification required, construction forbidden

This milestone will expose what reconstruction still cannot recover because
governing relations are implementation-only (B17). The evidence document must
classify each of the following as **BLOCKS RECONSTRUCTION / BLOCKS PLANNING /
BLOCKS MONOLITHIC COMPOSITION / DEFERRED**, and must build **none** of them:

stoichiometric matrix · constitutive stiffness matrix · algebraic constraints
among unknowns · conservation relations · PDE operator structure.

---

# 17. Provenance and concurrency — record, do not build

* **Provenance.** Determine what a re-derivable run must reference (spec identity,
  structural artifact identity, model, realization, solver/provider, inputs,
  conditions, numerical settings, external bulk artifacts). Missing fields are
  **listed**, not implemented, unless a proof forces one.
* **Concurrency.** Record whether the selected architecture naturally removes the
  mutable `bind_*` maps (B16). Do **not** redesign `ScientificSolver`. Option G is
  a separate future decision.

---

# 18. Migration strategy — required output, no execution

If the decision implies any future contract change, the evidence must state the
migration route — additive sibling record / new schema version / adapter from the
existing artifact / gradual producer migration — and must confirm that existing
evidence stays interpretable. **No silent migration**, and none performed here.

---

# 19. Required tests

* `tests/test_executable_scientific_spec.py`, new, including the fresh-process
  test, the relocation test, the planner-inspectability assertions, the six
  negative cases, and the AST guard on the instrument.
* Targeted; **FAST**; **FULL**. All three reported with exact counts.
* `DATA-BOUNDARY0`, `MODEL0-R`, `MIN-FOUNDATION-ET`, `ET-VERTICAL`,
  `HETERO-NGSPICE` and `CROSS-DOMAIN-COVERAGE` evidence must remain green and
  unedited.

---

# 20. Placement

Everything this milestone writes lives in:

```text
experiments/exec_spec_residue/          instrument, encodings, reconstruction
tests/test_executable_scientific_spec.py
docs/executable-scientific-spec-prereg.md      this file
docs/executable-scientific-spec-evidence.md    written after execution
```

Nothing under `src/`.

---

# 21. Stop rule

The measurement ends when the L3 residue is enumerated for all four columns and
the three reconstruction cases have each returned a result or an explicit NOT
RUN. **The spike does not design a record.** If the decision rule selects a
universal record, its design is the *next* milestone's preregistration, not this
one's output.

---

# 22. Output

1. `docs/executable-scientific-spec-evidence.md`, written after execution, with
   the sections the milestone brief requires (A–T).
2. A decision, at status `PROPOSED`, selected by §9's rule.
3. The exact next milestone, scoped by what was measured.

Commits: this preregistration alone, then implementation plus evidence.
