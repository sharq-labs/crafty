# MINIMUM FIELD / SUPPORT FOUNDATION — Preregistration

**Milestone:** `MIN-FIELD-SUPPORT-FOUNDATION`
**Branch:** `min-field-support-foundation`, worktree `/home/user/crafty-field-support`,
cut from `origin/cloud/crafty-post-fluid` @ `f58b5f923e4fe3bb17d4ee425aa32d287f0eb6a6`
(2077 passed, 0 failed, 0 errors).
**Kind:** closing the smallest repeatedly-forced semantic gaps exposed by the
real Fluid/PDE domain and four prior evidence milestones. **Not** a Field,
Mesh, Topology, Geometry, Equation IR, Relation IR, or planner milestone.

> Written before any implementation file exists on this branch. Immutable —
> divergence from what is predicted here is recorded in
> `docs/min-field-support-foundation-evidence.md`, not back-written here.

---

## 1. Governing prior evidence (not re-derived, cited)

Four milestones already measured this exact territory with real executed
probes and one real production domain:

* `docs/hostile-core-domain-stress-evidence.md` — 1D transient advection-diffusion.
  `FORCED`(L1): boundary orientation injectivity (R1a). `FORCED`(L1): a route
  from problem structure into `validity_context` (R4), closed by
  `ENCODING_C` (`ProvenanceRecord.inputs` + `validity_context(extra=...)`),
  **no core change**. `LIKELY-FORCED`(L0, Ledger 2, zero evidence gain):
  field/topology support (R1b, Q4). `LIKELY-FORCED`(L0): non-uniform
  `InitialCondition`, measured on the *existing* `thermal/conduction1d`
  domain's own `sin(pi x/L)` IC, which has no typed home today.
* `docs/fluid-pde-preparation.md` + `docs/real-fluid-pde-evidence.md` — the
  real, shipped `fluids/transport2d` domain. Re-confirms boundary
  orientation is real and sharp (every side of the rotational-field
  benchmark is exactly half inflow/half outflow, `sign_changes=1`), and
  reports it **honestly moot** for this specific domain because its
  boundary treatment is Dirichlet-everywhere and never consults orientation
  for anything. Re-confirms support/topology gap at zero evidence gain.
  Zero core files changed.
* `docs/min-cross-domain-foundation-evidence.md` — built `VariableBulkLinkage`
  and `ValidationReport.require_admission`, both `PROPOSED`, `L1 EXERCISED`
  for "correct when called", `L0` for "architecturally necessary" (falsifier
  C1: zero production callers at the time). `real-fluid-pde` later gave
  `VariableBulkLinkage` its first real production caller.
* `docs/exec-spec-structured-input-stress-evidence.md` — Mechanics and
  Species probes. Corroborates `VariableToBulkLinkage` 4/4 independently
  selected consumers. Explicitly rejects a generic matrix/relation
  abstraction (three different things share one numerical shape: a
  generated constitutive matrix, a stoichiometric relation, an addressing
  scheme). No Equation/Relation IR recommended.

This milestone's job is **not** to rediscover these findings. It is to
decide, on their evidence plus fresh measurement against the real Fluid
domain, exactly which `FORCED`/`LIKELY-FORCED` item — if any — is worth a
minimal typed record now, and to build only that.

## 2. Exact forcing consumers to be used

1. **Real Fluid/PDE** — `src/engcore/domains/fluids/transport2d/` (primary,
   already shipped, primary forcing consumer per the mission).
2. **Thermal conduction1d types, used compositionally** —
   `src/engcore/domains/thermal/conduction1d/` real
   `ScientificVariable`/model definitions/reference solution, exercised
   through a new test-level composition that does **not** edit
   `conduction1d/problem.py` or `solver.py` (both are exercised by a holdout
   declaration test and several other suites; editing them is out of this
   milestone's blast radius and not required to get real-typed evidence).
   This is the "materially different consumer" for non-uniform conditions,
   matching the prior milestone's own recommendation ("measured on the
   *existing* domain, not the probe").
3. **`kinetics/cstr`** — 0D, no spatial extent. Used **negatively**: to
   verify no new record forces a 0D consumer to declare spatial structure
   it does not have.
4. **`electrical/dc`** — 0D, lumped, two-terminal, already has an ordered
   terminal pair (`node_a`/`node_b`, passive sign convention). Used as the
   non-spatial corroboration for boundary/orientation universality, cited
   from `docs/hostile-core-domain-stress-evidence.md` §66.4/I.3 — **not**
   re-run; if anything new is needed there it will be a fresh, explicit
   measurement, recorded as such.

## 3. Zero-new-contract attempts (to be executed, not merely reasoned)

Written as concrete predictions; the evidence document reports the actual
executed outcome for each, in a new test file under
`tests/test_min_field_support_foundation.py`.

| # | Attempt | Predicted outcome |
|---|---|---|
| A1 | State "`c` lives on the unit square" using only `ScientificParameter("side", ...)` | Extent only; no shape, no boundary set, no orientation. **Insufficient**, reconfirming prior evidence, no new claim |
| A2 | State an oriented boundary subset using `BoundaryCondition(region=...)` alone, reverse the prescribed velocity field, compare serialized records | **Byte-identical** — reconfirms R1a on the real Fluid domain, not just the probe |
| A3 | Route `peak_cell_peclet` (mesh-dependent) into `ValidityDomain` via `problem.validity_context(extra=...)` + `ProvenanceRecord.inputs`, evaluate a `RangeCondition` on the reciprocal | **Works today**, zero core change — re-confirms `ENCODING_C`, this time wired into real Fluid production code rather than a probe |
| A4 | State a non-uniform initial field (`sin(pi x/L)`) using only `InitialCondition.value: Quantity` | **Fails** — one scalar cannot hold a function; reconfirms prior finding on the real domain rather than a probe |
| A5 | State the same non-uniform field via `ScientificParameter` (string-encoded formula) | **Rejected** — meaning-in-string, not a records-only-readable fact, matching `EXEC-SPEC-STRUCTURED`'s "meaning-in-key" failure mode |
| A6 | State a field-valued *model input* (a prescribed non-uniform boundary/initial array) using `ScientificResult.data_references` | **Wrong layer** — that field exists only on results, not on `ScientificProblem`; a *problem* cannot reference bulk input data at all today |

## 4. Hypotheses

* **H1 (support).** No new `Support`/`Field`/`Topology`/`Mesh` type is
  forced. Every real consumer (Fluid, Thermal, CSTR) is fully expressible
  today with a scalar physical extent (`ScientificParameter`) plus an
  opaque `region` label, and the residue (Q4/R1b: "which physical entity is
  this variable defined over, exactly") stays `LIKELY-FORCED` at Ledger 2,
  zero evidence gain, deferred again — consistent with four consecutive
  prior findings.
* **H2 (orientation).** A minimal, standalone, non-spatial orientation
  record — naming a `BoundaryCondition` and a single sign relative to a
  domain-declared reference direction — closes R1a (the univariate/lumped
  injectivity gap) without building a topology. It does **not**, and by
  construction **cannot**, resolve a region whose real physics mixes both
  signs (Fluid's rotational benchmark); a classification function must
  **refuse** rather than silently pick a side, and this refusal is provable
  today against the real Fluid domain's real velocity field.
* **H3 (non-uniform conditions).** `ScientificProblem` needs a
  `data_references` field (symmetric with `ScientificResult`'s, additive
  schema bump) so a *problem* can name input-side bulk data, and the
  existing `VariableBulkLinkage` (already `PROPOSED`) is the correct,
  sufficient binding mechanism once extended to resolve against
  `problem.data_references` as well as `result.data_references` — no new
  linkage type is forced.
* **H4 (validity-routing).** No new record is forced. `ENCODING_C`
  (`validity_context(extra=...)` + `ProvenanceRecord.inputs`) already
  closes this, and this milestone's contribution is wiring it into real
  Fluid production code, not inventing anything.
* **H5 (coordinate/flattening).** Data-layout/discretization semantic, not
  scientific semantic. `VariableBulkLinkage`/`ScientificDataReference`
  should **not** carry it. Falsification condition: a real consumer that
  cannot be correctly interpreted without a typed flattening convention
  even after naming which variable a bulk array instantiates.

## 5. Decision alternatives (weighed at step 10, not before)

(A) existing contracts only · (B) tiny `ScientificSupport` identity/reference
· (C) support + orientation relationship · (D) domain-owned support records
sharing only artifact infrastructure · (E) generic `Field` abstraction · (F)
generic `Topology` abstraction. E and F carry a very high evidence burden and
are not expected to be reached — nothing in four prior milestones' evidence
forces them, and this milestone predicts it will not either.

## 6. Forcing thresholds

A candidate is built only if: (a) a **real**, already-shipped consumer
demonstrably cannot state a fact it needs to state today, using every
existing typed contract, including the standalone-linkage pattern already
`PROPOSED`; (b) the fix is expressible as a small, standalone, additive
record (no field on a schema-pinned, already-shipped record without a
version bump with a working `require_schema_any` reader); (c) removing the
new record from the real consumer creates an observable ambiguity or a
refusal, not a silent behavior change.

## 7. Reduction conditions

Before anything is kept: can it be expressed by extending an *existing*
`PROPOSED` record's *checking* logic (as with `VariableBulkLinkage`) rather
than by minting a new type? `data_references` on `ScientificProblem` is
predicted to reduce this way; `BoundaryOrientation` is predicted **not** to
reduce onto any existing record, because none of `BoundaryCondition`,
`ScientificVariable`, `ScientificParameter` or `VariableBulkLinkage` carries
a sign concept today.

## 8. Negative tests (required)

* Construct the real Fluid benchmark's boundary sides (already-shipped
  `side_orientation()`), and prove a classification function that can only
  assign one sign to an entire named region **raises** for every one of the
  four sides (each has `sign_changes == 1`), rather than silently returning
  an arbitrary sign.
* Prove reversing the prescribed velocity field (`omega -> -omega`) changes
  which points are inflow/outflow (already measured) and, separately,
  changes what an honest domain's `BoundaryOrientation.sign` would have to
  be for a *non-mixed* region if one existed — demonstrated on a
  constructed single-signed boundary (not the real rotational one), so the
  positive case is exercised too, not only the refusal.
* Attempt to construct `data_references` scaling with mesh size (reject —
  `ScientificDataReference` is O(1) regardless of `count`, and the *problem*
  record holding a tuple of them stays O(number of field-valued inputs), not
  O(mesh)); assert this with a control-record-size test mirroring
  `hostile-core-domain-stress`'s own `< 20`-element scan.
* Prove `VariableBulkLinkage.check_against` still returns a `MISSING` issue
  (refusal, not silent success) when a `data_references` entry is *removed*
  from a problem that a non-uniform `InitialCondition` scenario depends on.

## 9. Falsification criteria

* H2 is falsified if the orientation record cannot be round-tripped through
  a fresh Python subprocess, or if it silently returns a sign for a region
  the real Fluid domain shows is mixed.
* H3 is falsified if `data_references` cannot be added to
  `ScientificProblem` without breaking `ScientificProblem.from_dict` on
  every pre-milestone-serialized `scientific_problem/1` payload (the
  additive-bump reader discipline `scientific_result/2` already
  established).
* H4 is falsified if wiring `peak_cell_peclet` into Fluid's
  `ProvenanceRecord.inputs` + `validity_context` requires any change to
  `src/engcore/scientific/`.
* Any hypothesis is falsified if the falsifier finds a `BLOCKER` that survives
  a design change, or if FULL is not green with zero unexpected
  failures/errors after remediation.

## 10. Evidence ceiling

`L1 EXERCISED` at best, for correctness-when-called and real-consumer
non-decorative use (following the exact precedent
`min-cross-domain-foundation` and `real-fluid-pde` set). **`L0`** for
"architecturally necessary to every future consumer" — one branch, this
session's author, matching every predecessor's own honest ceiling.
`DESIGN-FROZEN` is **not** claimed; status is `PROPOSED` throughout, per the
mission's explicit instruction to default to `PROPOSED`.

## 11. What will NOT be built, restated from the mission

`ScientificField`, `Mesh`, generic `Topology`, a `Geometry` framework,
`Equation`/`Relation` IR, `MatrixValue`, `StructuredScientificValue`,
`FunctionSpace`, a finite-element abstraction, a generic PDE solver
framework, cross-discretization transfer, Fluid↔Thermal coupling, Temporal
Semantics, Planner v0, an API/MCP layer. If investigation finds one of these
is genuinely necessary, the correct outcome is to stop and document the
blocker, not build it — and that remains true here.

## 12. Reversal triggers, preregistered before any code exists

* If `data_references` on `ScientificProblem` turns out to need shape,
  stride or flattening metadata to be usable by *any* real consumer this
  milestone touches — that is evidence H5 was wrong, and should be recorded
  as a deviation, not silently absorbed into the field's scope.
* If a second real domain (beyond Fluid) is found, during this milestone's
  own work, to need a *mixed*-orientation boundary resolved (not merely
  detected and refused) — that is evidence the orientation record under-scopes
  and a topology is genuinely forced; the correct action is to stop and
  document the blocker, not to build a topology under this milestone's name.
* If the falsifier's 0D attack (`electrical/dc`, `kinetics/cstr`) finds
  either domain is forced to declare orientation or bulk data references it
  does not need — that falsifies H2/H3's claimed universality and both
  should be narrowed in the evidence document.

---

**Commit discipline:** this document is committed alone, message
"Preregister minimum field support foundation", before any `src/` or
`tests/` file for this milestone exists. Nothing below this point is edited
after that commit; deviations go in
`docs/min-field-support-foundation-evidence.md`.
