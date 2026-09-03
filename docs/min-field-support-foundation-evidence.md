# MINIMUM FIELD / SUPPORT FOUNDATION — Evidence

**Milestone:** `MIN-FIELD-SUPPORT-FOUNDATION`
**Decision status:** `PROPOSED`. **Not `DESIGN-FROZEN`.**
**Evidence level:** `L1 EXERCISED` for both new primitives, correct-when-called
and real-consumer-proven; `L0` for "architecturally necessary to a production
solve path" (see §J). `L1 EXERCISED` for the reduction findings (H1/H4/H5 —
no new record needed there).
**Reviewer verdict (`architecture-decision-reviewer`):** `ACCEPT WITH
CHANGES` — three named changes, all completed (see §L).
**Falsifier verdict (`architecture-falsifier`):** `SURVIVES WITH REQUIRED
CHANGES` — one `BREAKING-RISK` (C.1, an unenforced precedence between a
scalar `InitialCondition` and a coexisting bulk `data_references` entry for
the same variable), closed at the documentation level, the falsifier's own
recommended minimal fix (see §M).
**Date:** 2026-09-03
**Branch:** `min-field-support-foundation`, worktree
`/home/user/crafty-field-support`

> **Temporal boundary.** `docs/min-field-support-foundation-prereg.md` is the
> preregistration, committed alone at `f8bddb8` before any implementation
> file existed, and immutable. This document was written after execution.
> Deviations are recorded here, not back-written into the preregistration.

---

## A. Forcing fact table

Built before any abstraction was proposed, from the four real/near-real
consumers named in the prereg. "EXISTING TYPED HOME" = a current contract
states it; "METADATA" = carried in an untyped string bag; "STRING
CONVENTION" = a documented convention with no typed record; "DOMAIN CODE" =
computed/known only inside domain source; "MISSING" = no representation at
all, anywhere.

| Item | (A) Real Fluid `transport2d` | (B) Mechanics probe (cited, not re-run) | (C) Thermal `conduction1d` | (D) Species/CSTR |
|---|---|---|---|---|
| Scientific variable | EXISTING TYPED HOME (`ScientificVariable`) | EXISTING TYPED HOME | EXISTING TYPED HOME | EXISTING TYPED HOME |
| Physical object/body/domain | STRING CONVENTION — `side: Quantity` states an extent, not a shape | MISSING — see `docs/exec-spec-structured-input-stress-evidence.md` §E ("which body is discretized" has no carrier) | STRING CONVENTION — `length: Quantity` | MISSING (0D — no spatial body exists to represent) |
| Support (spatial domain a variable lives over) | MISSING | MISSING | MISSING | N/A — 0D |
| Boundary region | STRING CONVENTION — `BoundaryCondition.region`, opaque label | MISSING (constrained-DOF set, not a boundary region) | STRING CONVENTION (implicit; `u(0,t)=u(L,t)=0` is code, not a record) | N/A |
| Orientation requirement | **MISSING before this milestone** — R1a, byte-identical under reversal | N/A (no boundary orientation concept applies to a static mesh) | MISSING (1D end-labels, direction never tested) | N/A |
| Bulk data (output) | EXISTING TYPED HOME (`ScientificDataReference` + `VariableBulkLinkage`, from `REAL-FLUID-PDE-DOMAIN`) | EXISTING TYPED HOME, cited | MISSING — `conduction1d` computes a field internally but never emits a `ScientificDataReference` for it | N/A |
| Bulk data (input) | **MISSING before this milestone** | **MISSING** | **MISSING** | N/A |
| Coordinates / flattening | DOMAIN CODE ONLY — documented in `solver.py`'s module docstring, no typed record | DOMAIN CODE ONLY | N/A (index already a coordinate) | N/A |
| Discretization identity | EXISTING TYPED HOME (`Transport2DGrid`, domain-local pattern) | N/A | EXISTING TYPED HOME (`SlabDiscretization`) | N/A |
| Initial condition | N/A (steady problem) | N/A | **MISSING for the real non-uniform case** — `conduction1d` declares **zero** `InitialCondition` records; `sin(pi x/L)` lives only in a metadata string | EXISTING TYPED HOME (scalar `InitialCondition`, uniform) |
| Boundary condition | EXISTING TYPED HOME for kind+value (uniform Dirichlet only) | N/A | STRING CONVENTION (never a real `BoundaryCondition` record either) | N/A |
| Validity criterion (mesh-dependent) | **MISSING before this milestone** — `peak_cell_peclet` computed but never routed into `ValidityDomain` | N/A | Same gap, not touched this milestone (out of scope — see §F5) | N/A |

**Reading the table plainly:** every real spatial consumer independently
lands on the same three MISSING rows — orientation, input-side bulk data,
and mesh-dependent validity routing — and every consumer that is not
spatial (D, CSTR) correctly has nothing in those rows to fill, because the
concept does not apply. This is the fact table the rest of this document
answers against.

---

## B. Zero-new-contract attempts

Executed as real tests (`tests/test_min_field_support_foundation.py`,
section A, `test_a1`–`test_a6`), not reasoned about in prose.

| # | Attempt | Outcome | Test |
|---|---|---|---|
| A1 | State "`c` lives on the unit square" using `ScientificParameter("side", ...)` alone | **Insufficient** — states an extent, no shape/boundary-set/orientation field exists to check | `test_a1` |
| A2 | State an oriented boundary subset via `BoundaryCondition(region=...)`, reverse the real Fluid domain's prescribed velocity, diff the serialized records | **Byte-identical** — R1a reconfirmed on production code, not a probe | `test_a2` |
| A3 | Route a mesh-dependent criterion (`peak_cell_peclet`) into `ValidityDomain` via `problem.validity_context(extra=...)` + `ProvenanceRecord.inputs` | **Works today, zero core change** — `ENCODING_C`, wired into real Fluid production code | `test_a3` |
| A4 | State a non-uniform initial field (`sin(pi x/L)`) using only `InitialCondition.value: Quantity` | **Fails** — a `Quantity` is one float; a non-`Quantity` value is rejected outright (`InvalidScientificProblem`) | `test_a4` |
| A5 | State the same field via a string-valued `ScientificParameter` | **Rejected as meaning-in-key** — representable, not machine-actionable; a records-only reader cannot evaluate the string | `test_a5` |
| A6 | State a field-valued *model input* via `ScientificResult.data_references` | **Wrong layer** — that field exists only on results; before this milestone `ScientificProblem` had no bulk-input channel at all, confirmed by loading a genuine `/1` payload and observing `data_references == ()` **by schema version**, not by any inference | `test_a6` |

**Where existing contracts already sufficed, nothing was added for that
question** (validity routing, A3 — see §F).

---

## C. Exact residues

Three, matching the fact table:

1. **Boundary orientation injectivity (R1a).** The `(kind, region, value)`
   triple is not injective onto physical systems — reversing a prescribed
   direction leaves every serialized `BoundaryCondition` byte-identical.
2. **Field-valued input.** `ScientificProblem` had no typed home for
   input-side bulk data (a non-uniform initial/boundary field, a
   field-valued coefficient) — the channel that exists is output-only
   (`ScientificResult.data_references`).
3. **Mesh-dependent validity criteria are per-run, never pre-run
   assessable** — a residue this milestone re-confirms, does not close (see
   §F), and wires into real Fluid production code so the residue's shape
   is visible in a shipped result rather than only in a probe.

---

## D. Support decision (H1)

**No new type built. Existing contracts (a scalar `ScientificParameter`
extent + an opaque `region`/`domain_id` label) remain sufficient for every
real consumer measured.**

`test_b2` reconfirms both real spatial domains (Fluid, Thermal) state their
extent as one `Quantity` parameter and run correctly without more. `test_b1`
reconfirms, by direct source-text scan (not by trusting a claim), that
neither `kinetics/cstr` nor `electrical/dc` — both real, 0D — reference any
concept this milestone added; a 0D consumer is not, and must not be, forced
to declare spatial structure it does not have.

This is the fourth consecutive milestone
(`HOSTILE-CORE-STRESS`→`FLUID-PDE-PREPARATION`→`REAL-FLUID-PDE-DOMAIN`→this
one) to measure "which physical entity is a variable defined over" as
`LIKELY-FORCED`, Ledger 2, **zero evidence gain**. Building `ScientificSupport`
now would fail this codebase's own premature-abstraction discipline — the
`architecture-decision-reviewer`'s verdict on exactly this point: alternatives
(B)/(C) "would build a concept four independent prior milestones measured
`LIKELY-FORCED, Ledger 2, zero evidence gain` — building it now would fail
this codebase's own premature-abstraction check." **Decision: DEFER, again,
honestly, not silently.**

---

## E. Orientation decision (H2)

**Built: `engcore.scientific.ir.orientation` — `OrientationSign`
(`POSITIVE`/`NEGATIVE`), `BoundaryOrientation` (`boundary_name`,
`reference`, `sign`, `description`; schema `boundary_orientation/1`, no
prior reader to break), `MixedOrientationError`, and
`classify_sign(samples) -> OrientationSign`, which raises
`MixedOrientationError` when the samples disagree in sign.**

### Why this shape and no other

* **Not a field on `BoundaryCondition`.** That record is schema-pinned
  (`boundary_condition/1`, exact-string `require_schema`); a field would
  break every stored payload for a fact that is not intrinsic to a
  condition's kind or value. Standalone, following the precedent
  `VariableBulkLinkage`/`QuantityDependency` already established.
* **Not spatial.** `classify_sign` imports nothing geometric and takes an
  arbitrary `Sequence[float]`; the geometry (an outward normal, a velocity
  dot product) lives entirely in the caller. `test_c7` proves the `n=1`
  lumped case (one signed current/flow value, no continuum boundary at all)
  is handled identically to the 16-sample 2D case — direct corroboration of
  the passive-sign-convention universality
  `docs/hostile-core-domain-stress-evidence.md` §I.1/§66.4 already
  established for the electrical DC domain.
* **Refuses, does not resolve, the mixed case — the mandatory negative
  test.** Every one of the four sides of the real Fluid domain's real
  rotational-velocity benchmark is exactly half inflow, half outflow
  (`sign_changes == 1`, re-confirmed on production code, not a re-print).
  `classify_boundary_orientation`, called against the real grid and real
  velocity field, **raises `MixedOrientationError` for every side, every
  time** (`test_c1`). This is not solved and is not claimed to be solved:
  closing it for real needs a per-position orientation function or a
  sub-region discretization, both of which reintroduce the mesh/topology
  question this milestone's mission explicitly forbids building.

### Real consumer proof

`fluids/transport2d/validation.py` gains `classify_boundary_orientation`
and `boundary_orientation_report`, both calling the domain's real
`reference.side_orientation()` — the real prescribed velocity field, the
real production grid. This is production code, not a test scaffold, and it
is the milestone's required negative-test proof executed as shipped code.
**What it is honestly not**: `solve_transport2d` never calls either
function — this benchmark's Dirichlet-everywhere boundary treatment never
needed orientation to run correctly (re-confirming
`docs/real-fluid-pde-evidence.md` §5), so the production use is the
refusal demonstration, not a numerics-affecting call. The falsifier
attacked this directly and found it disclosed, not decorative: the prereg's
own H2 frames the *required* proof as refusal, and the module docstring
states exactly this.

### Reduction attack

Could this close onto an existing record? No candidate exists:
`BoundaryCondition`, `ScientificVariable`, `ScientificParameter` and
`VariableBulkLinkage` carry no sign concept today, and reduction onto any of
them would either violate schema-pinning discipline or conflate a
directional fact with an unrelated record's identity.

---

## F. Non-uniform condition decision (H3)

**Built: `ScientificProblem.data_references: tuple[ScientificDataReference,
...] = ()`, an additive field bumping the schema `scientific_problem/1 ->
/2` (reader accepts both via `require_schema_any`; a `/1` payload loads with
`data_references == ()` by version, not by key presence).
`VariableBulkLinkage.check_against` is extended, with no change to its own
shape, to resolve `reference_name` against `problem.data_references` as
well as `result.data_references` — result-side checked first, documented
and tested precedence (`test_c8`).**

### Why no new record type

`VariableBulkLinkage` already stated exactly the needed fact — *this bulk
reference's values, in the reference's own order, are the values of this
declared variable* — and the only gap was that a `ScientificProblem` had
nowhere for the reference to live. Widening `check_against`'s search rather
than inventing `ConditionBulkLinkage` or similar avoided a second, near
duplicate binding type for the same underlying fact.

### Real second consumer, and its honest ceiling

A genuine non-uniform initial condition — `sin(pi x/L)` at `t=0` — is
constructed in `tests/test_min_field_support_foundation.py` (`test_d1`–
`test_d4`) using **real, unedited `thermal/conduction1d` production types**:
`ConductionSlab`, `SlabDiscretization`, and the domain's own exact
closed-form `reference.exact_field()` function (not a re-derivation). The
values are bound to a new `STATE` variable `u:field` via
`ScientificProblem.data_references` + `VariableBulkLinkage`, and:

* resolve cleanly through `check_against` (`test_d1`);
* produce an **observable refusal** when the reference is removed (`test_d2`
  — required by step 12: "changing/removing the new semantic record must
  create an observable ambiguity/refusal");
* keep the control record O(1) against a 21-value field (`test_d3`,
  DATA-BOUNDARY0);
* are dimension-checked and name-checked, not an arbitrary blob — a
  mismatched-variable linkage is refused (`test_d4`).

**Stated at its true strength, per the `architecture-decision-reviewer`'s
required change 2 and the falsifier's own confirmation of the same
scoping choice**: this is a **test-level composition**, not an edit to
`thermal/conduction1d`'s own production problem-builder. `conduction1d`'s
real `build_conduction_problem` was deliberately **not** touched — it is
exercised by a holdout-declaration test and several other suites, and
retrofitting it is a materially larger, separate change this milestone's
mandate (determine the minimum foundation, not deploy it everywhere it
could apply) correctly excludes. The evidence is therefore:

* `L1 EXERCISED` — the new primitives are correct, non-decorative and
  dimension-checked when used against real production types and a real
  closed-form reference function;
* `L0` — no claim of architectural necessity to any current production
  solve path. No solver in this repository reads `data_references` for an
  input today.

### The falsifier's finding, and its resolution

The falsifier found (`BREAKING-RISK`, finding C.1) that nothing in
`ScientificProblem` relates a variable's scalar `InitialCondition` to a
coexisting `data_references` entry bound to the same variable — a future
solver reading only `initial_conditions` (the only convention that exists
today; `conduction1d` declares **zero** `InitialCondition` records at all)
would silently compute a uniform state instead of the true field. **Closed
at the documentation level**, the falsifier's own recommended minimal fix:
`ScientificProblem.data_references`'s docstring now states explicitly that
a linked bulk reference is authoritative for a variable's state, and a
coexisting scalar condition is representative/informational only — no new
type, no schema change. The next milestone to actually wire a solver to
this combination (most likely `ELECTRO-THERMAL VERTICAL PROOF`, thermal
and non-uniform-state-adjacent) should add the enforcing test then, exactly
as `test_c8` did for the linkage's own precedence rule.

---

## G. Validity-routing decision (H4)

**No new record.** `ProvenanceRecord.inputs` (`Mapping[str, Quantity]`,
typed, dimension-checked) plus `ScientificProblem.validity_context(extra=...)`
already gave `ENCODING_C` — measured and adopted by
`docs/hostile-core-domain-stress-evidence.md` §J.3 — everything needed. This
milestone's contribution is wiring it into real Fluid production code
rather than inventing anything: `solver.py` now computes
`inverse_peclet_cell` (the reciprocal cell Péclet number, avoiding a
non-finite `Quantity` at the theoretical `D=0` limit — the same
reparameterization `ENCODING_C` used), stores it as a typed `Quantity` in
`ProvenanceRecord.inputs`, and evaluates it against a new `RangeCondition`
added to `TRANSPORT2D_MODEL`'s existing `ValidityDomain`.

**Measured, not asserted** (`test_a3`): the same physical Fluid problem
(same `domain_id`, `side`, `diffusivity`, `angular_rate` — same
`fingerprint()`), solved at `n_cells=8` and `n_cells=64`, produces a
`mesh_validity_assessment` of `outside_validated_domain`
(`inverse_peclet_cell` violated, `0.113`) and `in_domain`
(`inverse_peclet_cell` satisfied, `0.905`) respectively — the criterion is
correctly per-run, and the problem's own physical identity (`domain_fingerprint`,
variables, boundary conditions, parameters) is unaffected by which grid
solved it, exactly matching `ENCODING_C`'s claim.

`test_f1` is the explicit reduction check: no new type import is required
to reproduce this result; `TRANSPORT2D_MODELS[0].validity.assess` and
`problem.validity_context` are both pre-existing.

---

## H. Coordinate/layout classification (H5)

**Classification: discretization/data-layout semantic, not scientific
semantic — reconfirmed, not newly discovered.** `VariableBulkLinkage` and
`ScientificDataReference` still carry no `shape`/`stride`/`flattening` field
(`test_e1`, asserted directly against both dataclasses' field sets). The
row-major `i*n+j` convention `fluids/transport2d/solver.py` uses remains
documented in exactly one place — that module's own docstring — a
pre-existing, disclosed residue (F5 in `docs/real-fluid-pde-evidence.md`)
this milestone neither closes nor worsens.

**Falsification attempt, honestly reported as failed to falsify the
default**: every real consumer this milestone touched (Fluid's field
output, the Thermal-typed non-uniform IC) resolved correctly using only
`{name, unit, count, dtype, digest}` plus a `VariableBulkLinkage` naming the
variable — none needed a typed flattening fact to be correctly interpreted
*by a caller that already knows the domain's own convention*, which is
exactly the residue DATA-BOUNDARY0 already named and left deferred. The
default (H5: "probably NOT") survives.

---

## I. Abstractions rejected

| Candidate | Verdict | Why |
|---|---|---|
| `ScientificSupport` / `Field` / `Topology` / `Mesh` | **REJECTED, again** | Zero evidence gain across four consecutive milestones; explicit mission non-goal; no real consumer measured here forces it either |
| A new `ConditionBulkLinkage` type (distinct from `VariableBulkLinkage`) | **REJECTED** | `VariableBulkLinkage`'s existing shape already stated the needed fact; widening `check_against`'s search closed the gap with no new type |
| A field on `BoundaryCondition` for orientation | **REJECTED** | Schema-pinned, exact-match `require_schema`; would break every stored payload for a fact orthogonal to a condition's kind/value |
| A three-state `OrientationSign` (`POSITIVE`/`NEGATIVE`/`TANGENT`) | **REJECTED** | Zero current consumer needs a distinct "exactly zero" classification; `classify_sign` refuses on all-zero input instead of inventing a member with no evidence behind it |
| `BoundaryOrientation.check_against(problem=...)` resolving `boundary_name` against real `ScientificProblem.boundary_conditions` | **DEFERRED, not rejected** | No current consumer needs it (Fluid's use never touches a `ScientificProblem`); a real asymmetry with `VariableBulkLinkage` noted by the falsifier as a non-breaking future extension |
| `problem_id`/`result_id` fields on the new records | **REJECTED** | Same precedent `VariableBulkLinkage`/`QuantityDependency` already established: scoped implicitly by whichever collection holds the record |

---

## J. Real consumer proof

**Real Fluid (primary forcing consumer).** `classify_boundary_orientation`/
`boundary_orientation_report` (production code in
`fluids/transport2d/validation.py`) execute against the real, shipped
domain's real velocity field and real production grid, and correctly
refuse for every boundary side, every time — the mandatory negative test,
run as shipped code. `solver.py`'s `inverse_peclet_cell` wiring is
production code exercised on every real solve, not only in a test.

**Second, materially different consumer.** Genuine `thermal/conduction1d`
production types (`ConductionSlab`, `SlabDiscretization`,
`reference.exact_field`) compose a non-uniform initial condition using
`data_references` + `VariableBulkLinkage`, at the honestly-disclosed ceiling
described in §F (test-composed, not wired into `conduction1d`'s own
production problem-builder).

**Changing/removing the new record produces an observable refusal, proven
for both primitives:**

* `test_c4` — a `BoundaryOrientation` claiming a fixed sign, checked against
  the real Fluid domain's genuinely mixed-sign samples, returns a non-empty
  issue naming the disagreement.
* `test_d2` — removing the `data_references` entry a `VariableBulkLinkage`
  depends on produces exactly one `MISSING` issue naming the reference.

**0D negative check, explicit.** `test_b1` verifies by direct source scan
that neither `kinetics/cstr` nor `electrical/dc` — both real, 0D — reference
any concept this milestone added; the falsifier independently re-verified
this by reading both packages' full source rather than trusting the test's
self-report.

---

## K. Fresh-process proof

`test_g1` serializes a `ScientificProblem` (carrying the non-uniform IC's
`data_references`), a `VariableBulkLinkage`, and a `BoundaryOrientation` to
JSON, launches a **genuinely separate `python3 -c ...` subprocess** (no
shared Python object identity, no pickling, no in-memory registry), and
reconstructs all three from `from_dict` alone. The child process:

* resolves the linkage with **zero** issues;
* reports the reconstructed reference's `count` and content `digest`
  matching the parent process's original values exactly;
* reports the reconstructed orientation's sign correctly;
* **imports no `fluids.*` module at all** (`modules_loaded == []`,
  asserted) — the reconstruction path used only universal core records, not
  domain code, confirming genuine records-only recoverability.

---

## L. Reviewer verdict (full)

`architecture-decision-reviewer`: **ACCEPT WITH CHANGES**. Verdict text
(condensed): the two-primitive choice (G) is "the right minimal choice among
(A)–(F), and it is right *on the measured evidence*" — (A) was executed and
shown insufficient; (B)/(C) would build a `Support` concept four independent
prior milestones measured `LIKELY-FORCED, Ledger 2, zero evidence gain`; (D)
would duplicate a distinction already shown universal (electrical DC's
passive-sign guard) once per domain; (E)/(F) are correctly deferred "on the
same grounds this codebase already used to reject `RealizationFidelity`."

Three required changes, all completed:

1. Run and record FULL regression before the milestone is considered done —
   done, see §N.
2. State H3's evidence ceiling precisely (test-composed, not a production
   domain module's own solve path) — done, see §F.
3. Add a collision test for `VariableBulkLinkage.check_against`'s
   result-vs-problem precedence — done, `test_c8`, and the precedence is now
   documented in `variable_binding.py`.

---

## M. Falsifier verdict (full)

`architecture-falsifier`: **SURVIVES WITH REQUIRED CHANGES**. Six named
attacks, all addressed:

| Attack | Result |
|---|---|
| 1. "You built `ScientificField` under another name" | **False** — `ScientificDataReference` unchanged this milestone; still carries no mesh/topology/shape field |
| 2. "Your Support is actually a mesh/discretization object" | **Does not apply** — no `Support` type of any kind exists in this diff |
| 3. "Boundary orientation is only correct for a Cartesian square" | **Held** — `classify_sign` takes an arbitrary `Sequence[float]`, no geometry import; caveat noted that the *positive* (non-mixed) case is exercised only synthetically, never against a second real non-Cartesian production domain |
| 4. "Coordinate ordering placed in scientific semantics" | **Held** — no shape/stride/flattening field exists on either new or touched record |
| 5. "Non-uniform conditions merely point at arbitrary blobs" | **Held for naming/dimension-checking; sharper version found and closed** — see finding C.1 below |
| 6. "Shared only because Fluid and Thermal both use spatial arrays" | **Partially lands, disclosed rather than hidden** — electrical DC/CSTR corroboration is a citation to prior, already-executed evidence, not a live second-domain caller of the new type this milestone built; the prereg discloses this explicitly |

**One `BREAKING-RISK` (C.1)**: nothing enforced a precedence between a
variable's scalar `InitialCondition` and a coexisting `data_references`
entry bound to it. **Closed** at the documentation level — see §F. No
`BLOCKER`. Every other finding (premature-generalization concerns about
`BoundaryOrientation`'s single production use being refusal-only,
`classify_sign`'s all-zero-samples refusal, the linkage precedence rule)
was traced to a real, disclosed, evidence-appropriate limit rather than a
defect, and none required building `Field`/`Mesh`/`Topology`.

---

## N. Core files changed (exact list)

```
src/engcore/scientific/ir/problem.py            data_references field, schema bump /1->/2
src/engcore/scientific/ir/__init__.py           export BoundaryOrientation etc.
src/engcore/scientific/ir/orientation.py        NEW — BoundaryOrientation, classify_sign
src/engcore/scientific/results/variable_binding.py   check_against extended (no schema change)
```

Four files, one new. Every other file under `src/engcore/scientific/`
byte-unchanged — this is the exact same discipline `HOSTILE-CORE-STRESS` and
`MIN-CROSS-DOMAIN-FOUNDATION` asserted by test rather than by claim, and the
existing canary tests in this repository (`test_no_universal_core_file_was_
added_or_edited` in three prior milestones' suites) were updated with a
named, documented exception set — the same pattern those suites already use
for `planner-provided-capabilities`' own prior, similarly-scoped exception.

**Domain files changed (non-core, real Fluid production use):**

```
src/engcore/domains/fluids/transport2d/problem.py     new RangeCondition on inverse_peclet_cell
src/engcore/domains/fluids/transport2d/solver.py      inverse_peclet_cell + mesh_validity_assessment wiring
src/engcore/domains/fluids/transport2d/validation.py  classify_boundary_orientation, boundary_orientation_report
src/engcore/domains/fluids/transport2d/__init__.py    exports
```

`src/engcore/domains/thermal/`, `src/engcore/domains/electrical/`,
`src/engcore/domains/kinetics/` are byte-unchanged (verified by `test_b1`'s
source scan and by `git diff` against the branch point).

---

## O. Migration / serialization impact

| Schema | Before | After | Impact |
|---|---|---|---|
| `scientific_problem` | `/1` | **`/2`** (additive) | A pre-milestone reader can no longer read a `/2` payload — the exact, accepted cost `scientific_result/1->/2` already paid (DATA-BOUNDARY0). A `/2`-aware reader still loads every `/1` payload unchanged (`data_references == ()`, by version). |
| `variable_bulk_linkage` | `/1` | `/1`, unchanged | `check_against`'s *behavior* changed (it now also looks at `problem.data_references`); its *serialized shape* did not. |
| `boundary_orientation` | did not exist | `/1`, new | No prior reader to break. |
| `boundary_condition`, `initial_condition`, `scientific_data_reference`, `validation_check`, `validation_report`, `scientific_result` | unchanged | unchanged | Verified directly (`test_h1`) and by three prior milestones' own updated schema-string assertions. |

No stored record format changed silently. Every version-string change is
disclosed in this document and in the code comments at the exact line that
changed it.

---

## P. Evidence level

| Claim | Level | Why |
|---|---|---|
| `classify_sign`/`BoundaryOrientation` correctly refuse a genuinely mixed-sign region | `L1 EXERCISED` | Proven against the real Fluid domain's real velocity field and real grid, every side, every time |
| `classify_sign` correctly classifies a genuinely single-signed region | `L1 EXERCISED` | Synthetic positive case (`test_c2`), the lumped `n=1` case (`test_c7`) |
| `BoundaryOrientation` is architecturally necessary to any current production solve path | `L0` | Its one production caller (`boundary_orientation_report`) is never called by `solve_transport2d`; used only for the required refusal demonstration |
| `ScientificProblem.data_references` + `VariableBulkLinkage` correctly bind a non-uniform field when used | `L1 EXERCISED` | Real thermal-typed second consumer, fresh-process reconstruction, O(1) control record, refusal on removal |
| `data_references` is architecturally necessary to any current production solve path | `L0` | No shipped solver reads it for an input; `conduction1d`'s own production problem-builder was deliberately not touched |
| No new `Support`/`Field`/`Topology` type is needed | `L1 EXERCISED` (reduction) | Reconfirmed on two real spatial domains plus two real 0D domains, the fourth consecutive milestone to measure this |
| No new record is needed for mesh-dependent validity routing | `L1 EXERCISED` | `ENCODING_C` wired into real Fluid production code, measured across two grid resolutions of one physical problem |
| Coordinate/flattening stays outside scientific semantics | `L1 EXERCISED` (reduction) | Every real consumer resolved correctly without a typed flattening fact |

**No claim here is rounded up past what §A–§K actually measured.**

---

## Q. Decision status

```
Decision status:   PROPOSED
Evidence:           L1 EXERCISED (correct-when-called, real-consumer-proven);
                     L0 (architectural necessity to a production solve path)
Milestone:          COMPLETE
```

**Not frozen.** In particular: `BoundaryOrientation`'s three-field shape and
`data_references`'s result-shadows-problem resolution precedence are both
places a real future consumer (most plausibly `ELECTRO-THERMAL VERTICAL
PROOF`) should be expected to press on first.

---

## R. Reversal triggers

Restated from the preregistration, none tripped during this milestone:

* If `data_references` on `ScientificProblem` turns out to need shape,
  stride or flattening metadata to be usable by any real consumer — not
  observed; every consumer touched resolved correctly without it.
* If a second real domain is found, during or after this milestone, to need
  a *mixed*-orientation boundary genuinely **resolved** (not merely detected
  and refused) — not observed; Fluid's Dirichlet-everywhere benchmark never
  needed orientation resolved, and no other spatial domain was added this
  milestone. **If this trips in a future milestone, the correct response is
  to stop and document the blocker — a genuine topology forcing — not to
  widen `BoundaryOrientation` under a different milestone's authority.**
* If the falsifier's 0D attack found either `electrical/dc` or
  `kinetics/cstr` forced to declare orientation or bulk data it does not
  need — **did not trip**; independently re-verified by the falsifier via
  direct source read, not merely by trusting `test_b1`.

**New reversal trigger, added by this milestone's own falsifier finding**:
if a future solver is wired to read `data_references` for an input and
simultaneously reads a coexisting scalar `InitialCondition`/
`BoundaryCondition.value` for the same variable, the documented precedence
(bulk reference authoritative) must be enforced by a test at that point —
not assumed to hold from documentation alone indefinitely.

---

## S. Tests

| Suite | Command | Result |
|---|---|---|
| Targeted (this milestone) | `pytest tests/test_min_field_support_foundation.py -q` | **25 passed** |
| Fluid + Thermal domain (regression) | `pytest tests/domains/fluids tests/domains/thermal -q` | **73 passed** |
| FAST | `pytest tests/ -m "not expensive" -q` | **1537 passed**, 565 deselected, 0 failed |
| FULL | `pytest tests/ -q -n auto` | **2101 passed**, 0 failed, 0 errors |

**Baseline, measured directly on this worktree before any implementation
file existed** (immediately after the preregistration commit `f8bddb8`, venv
installed, before `src/`/`tests/` edits began):

```text
FAST at f8bddb8 (prereg only): 1512 passed, 565 deselected, 0 failed
FULL at f8bddb8 (prereg only): 2064 passed, 13 failed, 0 errors
```

The 13 pre-existing FULL failures (all under `test_exec_spec_structured_
input.py`/`test_executable_scientific_spec.py`'s subprocess-based fresh-
interpreter reconstruction tests, and the three prior milestones' own
"byte-unchanged core" canaries, correctly firing because this milestone had
not yet committed) are **environmental/expected-at-that-point-in-time**, not
defects: the subprocess tests passed individually when checked
(`pytest ... -q` standalone, no `-n auto`), consistent with resource
contention under parallel execution on a 4-core sandbox — the same class of
caveat `docs/hostile-core-domain-stress-evidence.md` and
`docs/min-cross-domain-foundation-evidence.md` already recorded for this
environment (`ngspice` launcher and pytest temp-root caveats respectively).
The canaries are `git diff --name-only HEAD`-based checks that necessarily
fail while a milestone's own changes are uncommitted, by construction, and
were confirmed to pass again once this milestone's changes were committed
(no baseline-comparison trick was used to "resolve" them — the same test
code interrogates a different, now-clean git state).

**After this milestone's two commits (`f5dce14`, `0d99110`), FULL is
completely clean: `2101 passed, 0 failed, 0 errors`** — zero unexpected
failures, zero unexpected errors, no pre-existing test edited to loosen a
tolerance or skip a check. Every test-file edit in this milestone's diff
(`tests/test_cross_domain_coverage.py`, `tests/test_exec_spec_structured_
input.py`, `tests/test_executable_scientific_spec.py`,
`tests/test_hostile_core_domain_stress.py`,
`tests/test_min_cross_domain_foundation.py`,
`tests/test_min_foundation_electrothermal.py`) updates a stale expected
literal (a schema-version string, an independently re-measured coverage-
matrix cell) to the new, correct, disclosed fact — never a tolerance
loosening, a skip, or a deletion. Each such edit carries an inline comment
naming this milestone and the exact reason, following the identical pattern
three prior milestones in this lineage already used for their own
`planner-provided-capabilities`/`ngspice-cross-platform-portability`
exceptions.

**Independent, unsolicited corroboration**: `experiments/cross_domain_
coverage/instrument.py::probe_field_valued_input` — a probe this milestone
did not write or edit — live-checks `ScientificProblem` for a
`data_references` field on every run
(`instrument._problem_can_reference_bulk`). Adding the field flipped that
probe's own verdict for the B-transport consumer from `FORCED` to `SERVED`,
with zero edits to the probe itself. `tests/test_cross_domain_coverage.py`'s
updated assertions record this as what it is: a prior, independently-
authored instrument confirming the gap it measured is closed.

---

## T. Post-milestone strength delta

Per the mission's exact scope — seven dimensions only, same 0–5 scale as the
prior audit, no other dimension re-scored.

| Dimension | Before | After | Why |
|---|---|---|---|
| **Semantic Coverage** | 2/5 | **3/5** | Two real, measured gaps closed at the representation level: field-valued input (previously `ScientificProblem` had no bulk-input channel at all) and boundary-orientation injectivity for the single-signed case, with an honest, tested refusal for the genuinely mixed case rather than a silent wrong answer. Still missing: physical support/topology, discretization selection, a typed coordinate/flattening convention — all deliberately, evidence-groundedly deferred (§D, §H), so this is a partial, not a complete, close. |
| **Field/Distributed-State Readiness** | 2/5 | **3/5** | `VariableBulkLinkage` (the prior milestone's contribution) now serves both directions — output (unchanged) and input (`data_references`, new) — proven against a real second domain's real closed-form reference function, with fresh-process reconstruction and O(1) control-record size holding under the new direction too. Held at 3, not higher, because no shipped solver yet reads the input side in production (§F, §J — `L0` for architectural necessity), and support/topology remain unrepresented. |
| **Domain Extensibility** | 4/5 | **4/5 (unchanged)** | Both new primitives are additive and opt-in; zero existing domain was forced to adopt either (Thermal, CSTR, electrical DC untouched — verified by source scan, `test_b1`). No new structural extensibility barrier was removed and none was added; this milestone did not target this dimension and the evidence does not move it. |
| **Core Stability** | 5/5 | **5/5 (unchanged)** | The one core schema bump (`scientific_problem/1->/2`) followed the exact precedented, additive, backward-compatible discipline `scientific_result/1->/2` already established, with a version-gated reader and zero silent behavior change for `/1` payloads. FULL regression is 100% green post-change (`2101 passed, 0 failed, 0 errors`) with no test weakened to get there — every edit updates a stale literal to a new, correct, disclosed fact. Stability was preserved through discipline, not through avoidance of change. |
| **Fluid BC Coverage** (Fluid domain scorecard) | 1/5 | **2/5** | The domain now has real, production, tested infrastructure (`classify_boundary_orientation`) that correctly identifies exactly which of its own boundary conditions cannot be honestly described by a single orientation — a genuine, non-decorative diagnostic capability that did not exist before. Held at 2, not higher: the domain still declares exactly one `BoundaryKind` (Dirichlet, uniform) in production, no Neumann/Robin/flux condition exists yet, and the orientation infrastructure is not wired into any solve decision — it demonstrates refusal, it does not yet gate or inform a richer boundary treatment. |
| **Fluid Distributed-State Representation** (Fluid domain scorecard) | 2/5 | **2/5 (unchanged)** | The primary new evidence for input-side non-uniform state (§F) was demonstrated against Thermal-typed data, not Fluid's own production path — Fluid's manufactured boundary value is trivially uniform (zero on every side by construction of its manufactured solution), so this milestone found no real non-uniform-input case to exercise inside Fluid itself. The output-side representation (`c:field` via `VariableBulkLinkage`) is unchanged from the prior milestone. |
| **Fluid Multiphysics Readiness** (Fluid domain scorecard) | 1/5 | **1/5 (unchanged)** | Explicitly out of scope (mission non-goal: "NOT Fluid↔Thermal coupling"); no coupling code was written or proven. Worth naming as a directional note, not a score change: `docs/fluid-pde-preparation.md` §B9 already identified that Fluid's own field-valued-input gap was "a strict prerequisite for a real Fluid↔Thermal field coupling" — closing that gap this milestone (§F) removes one named prerequisite without yet building or proving the coupling itself, so the *readiness* score correctly stays flat until a coupling milestone actually exercises it. |

**Overall reading**: this milestone closed two real, independently-measured,
Ledger-1 gaps (orientation injectivity, field-valued input) with the
smallest records the evidence supported, left the Ledger-2 residues
(support, topology, coordinate/flattening) honestly deferred for a fourth
consecutive time, and demonstrated both new primitives against a real
production domain and a real second domain's real types — without moving
core stability, domain extensibility, or multiphysics readiness, and without
overclaiming any of the seven scores past what §A–§S actually measured.
