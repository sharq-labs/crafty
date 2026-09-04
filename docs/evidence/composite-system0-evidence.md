# COMPOSITE-SYSTEM0 — evidence

Preregistration: `docs/evidence/composite-system0-preregistration.md`, commit
`dab4e1e`, committed **alone** before any source file on this branch was added
or edited. Not amended; every divergence from it is recorded below in §13.

**Evidence level: PROPOSED / L1 EXERCISED.** Nothing here is frozen, nothing is
promoted, and §12 states plainly what this milestone did *not* prove.

---

## 1. Commits

| Commit | Contents |
|---|---|
| `f1ed553` | canonical base (code), `API-MCP-V0`, FULL **2306 passed / 0 failed / 0 errors** |
| `fdd3359` | docs-only canonical-state reconciliation (entry reading) |
| `dab4e1e` | **preregistration, committed alone** |
| `871abdb` | implementation: two new source files, one `__init__` export list, one test module |
| `37633e3` | two pre-existing test guards repaired (documented defects — §11) |
| `5d45f56` | this evidence document, the catalogue-name derivation in the new test module |

## 2. Test counts

| Tier | Before | After | Delta |
|---|---|---|---|
| Focused (`tests/test_composite_system0.py`) | — | **76 passed** | +76 |
| FAST (`-m "not expensive"`) | **1681 passed / 625 deselected** | **1757 passed / 625 deselected** | +76 |
| FULL (no marker, sequential, single process) | **2306 passed / 0 failed / 0 errors** (`f1ed553`) | **2382 passed / 0 failed / 0 errors** | +76 |

The FULL figure was measured **once, at the end, sequentially**, on the final
tree, in a single uninterrupted process.

**Environment divergence, recorded up front and not worked around.** On a bare
`venv`, `tests/test_min_field_support_foundation.py::test_g1_fresh_process_reconstructs_and_reports_no_issues`
fails: it launches a **subprocess** that imports `engcore`, and pytest's
`pythonpath` setting does not reach a child process. Repaired by putting `src/`
and the repo root on the venv's path with a `.pth` file. It is an environment
defect, not a code defect, and **no test file was edited for it**. The 1681
baseline above is measured *after* that repair.

## 3. Files changed

| File | Status | Lines |
|---|---|---|
| `src/engcore/domains/electrical/conductor_material.py` | **new** | 1727 |
| `src/engcore/systems/electrothermal/power_chain.py` | **new** | 1173 |
| `src/engcore/systems/electrothermal/__init__.py` | export list only | +36 |
| `tests/test_composite_system0.py` | **new** | 1574 |
| `tests/test_api_mcp_v0.py` | guard repair (§11) | +31 / −8 |
| `tests/test_coupling_pack_relocation.py` | guard repair (§11) | +53 / −8 |
| `.gitignore` | `.pytest_tmp_*/` | +3 |

`test_t6f_the_working_tree_changed_only_where_the_prereg_said_it_would` asserts
this against **git**, over both committed history and the working tree, rather
than against a hand-maintained list, so a stray edit is loud.

**Untouched, asserted by test:** every module under `engcore/scientific`,
`engcore/coupling`, `engcore/domains/electrical/dc`, `engcore/application`,
`crafty_http`, `crafty_mcp`; `engcore/domains/electrical/material.py`,
`engcore/domains/electrical/ngspice.py`, `engcore/domains/thermal_lumped.py`,
`engcore/systems/electrothermal/coupled.py`, `.../resistor_body.py`,
`engcore/systems/fluidthermal/`.

---

## 4. The zero-new-contracts gate — the primary result

Attempted **before any design**, using only `ScientificProblem`,
`ScientificModelDefinition`, `ModelRealizationDefinition`, `QuantityDependency`,
`ExecutionBinding`, `TemperatureDependentConductor`, `DCCircuit`, `ThermalBody`,
`run_fixed_point` and the existing serialization.

### 4.1 Contracts deliberately NOT added, and why each is not forced

| Candidate | Forced? | Measured reason |
|---|---|---|
| `ComponentInstance` | **No** | `CoupledStage` already pairs a conductor and a body under one `component_id`; `CoupledElectroThermalSystem` already refuses duplicate ids; each instance already poses its own `ScientificProblem`s with their own provenance. `ET-VERTICAL` already ran this at arity 2. Adding a material and a geometry — the case that was supposed to force it — did not. |
| `Port` / `Connector` | **No**, on all eight readings | See §4.2. |
| `SystemDefinition` | **No** | `PowerChain` is a pack-local declaration in the same category as `DCCircuit` and `CoupledElectroThermalSystem`. Nothing universal reads it and nothing needs to. |
| `MaterialBinding` | **No** | A conductor *has* a material as a typed field. A separate binding record would restate the field and put the duplicate somewhere the existing validity machinery could not see. |
| universal `Material` / `MaterialState` / `MaterialProperty` | **No** | `MODEL0-R` deferred materials from core; one consumer does not reopen that. Two independent consumers already do properties without such a hierarchy (`electrical/material.py`, `systems/fluidthermal/properties.py`). |
| a component or material registry in universal core | **No** | The catalogue is a pack-local data table and the mechanism is not catalogue-gated (§7.3). |
| a composite graph that is also an execution schedule | **No** | Topology stays in `DCCircuit`; dataflow stays in `QuantityDependency`; the order is *computed* by `execution_order` and written down nowhere (`test_a3`). |
| a second provenance system | **No** | `ExecutionBinding` / `ProvenanceRecord` carry the whole chain (§8). |

**"Component duplicates `ScientificProblem`" was the kill criterion this
milestone was most likely to hit. It was avoided by not creating a Component.**

### 4.2 Are ports/connectors forced? The eight readings, answered

| Reading | Forced? | Grounds |
|---|---|---|
| Topological connectivity | No | `DCCircuit` / `ElectricalNode` / `Resistor` already carry typed topology, node-existence checks, exactly-one declared reference node, polarity and duplicate-id refusal. |
| Equality of effort variables | No | Node-voltage equality is what an MNA node *is*; discharged inside one domain's assembly. |
| Conservation of flow | No | KCL is a stamp in the MNA assembly, not a connector obligation. No cross-domain flow conservation exists here. |
| Data dependency | No | `QuantityDependency` is exactly this record, and this milestone gives it a **third edge type** (`resistivity → resistivity`) at zero contract cost. |
| Unit compatibility | No | `QuantityDependency` carries a dimension; `ModelInputSpec.unit_exemplar` carries the other side; matching is by dimensionality. |
| Causality | No | Everything here is causal. Acausal composition is unexercised, and Modelica's retrofit of `stream` connectors in 3.1 is direct evidence of what freezing connector semantics early costs. |
| Direction | No | A `QuantityDependency` has no direction flag because source and target *are* the direction. |
| Multiplicity (fan-in) | No — and **actively refused** | `FixedPointCouplingPlan` rejects any endpoint receiving more than one edge, stating that no record says whether two sources sum, override or split. Measured live: `test_e1[unresolved_connection]`'s first form accidentally created a fan-in and was refused. |

**Conclusion: connections are not forced. Nothing was built, and no electrical
assumption was hidden inside a "universal" Port, because no Port exists.**

### 4.3 What the null attempt genuinely could not do

Computing `R_ref = rho_ref * L / A` in harness Python and feeding the existing
`TemperatureDependentConductor` produces the *right numbers* and four defects:

1. `L`, `A` and the material appear in **no** problem, twin, provenance record
   or serialized artifact;
2. a non-positive area cannot be refused by any contract — and `L < 0` with
   `A < 0` yields an **admitted** positive resistance (`test_e1[invalid_length_negative]`);
3. an unsupported material cannot be refused, because no material exists;
4. the `rho * L / A` step is an unmodelled scientific claim executed in demo
   code with no model, no realization, no solver and no `ExecutionBinding` —
   i.e. exactly the hardcoded demo propagation the milestone forbids.

## 5. What *was* actually forced

Two things, both **pack-local declaration records and declared models** in the
same category as records that already existed — not new universal contracts:

1. **A typed material record** (`ConductorMaterial`, with `LinearResistivityMaterial`
   and `QuadraticResistivityMaterial`). Forced because without material
   *identity* an unsupported material cannot be refused, per-material
   applicability has nowhere to live, and provenance cannot say what changed.
2. **Declared models for the two claims that were being computed in the dark**:
   `rho(T)` and `R = rho L / A`, each with a `ScientificModelDefinition`, a
   `ModelRealizationDefinition`, a solver and an `ExecutionBinding`.

Neither required a single line of `engcore.scientific` or `engcore.coupling`.

### 5.1 One model per functional form, never one per material

A model *per material* was designed and rejected before implementation. It
would have made `(model_id, version)` — the key `ModelRegistry` and
`ExecutionBinding` are built on — a function of a mutable data table, so a
data-only catalogue correction would silently change what an already-stored
provenance record claims; and the only route from a stored number back to its
material would be to **parse characters out of an identifier**. It also makes a
stateless `supports()` impossible for a material constructed outside the
catalogue (`test_g3`).

The axis that *does* justify more than one model is the **functional form**:
copper and aluminium are two parameter sets of one model; linear and quadratic
are two models.

### 5.2 Where a material's applicability range lives — a measured contract gap

`ValidityDomain` conditions are fixed `Quantity` bounds **on the model record**,
so one shared model structurally cannot carry three different per-material
temperature ranges. The range therefore lives on the material record with
**exactly one authority** and is assessed by building a `ValidityDomain` from
that record at assessment time (`test_t6i`). This is a real limitation of the
existing contract, recorded rather than worked around.

### 5.3 A second measured contract gap: provenance cannot record a category

`ProvenanceRecord.inputs` is `Mapping[str, Quantity]` and **refuses** anything
else. Material identity is declared as a typed `CategoricalValue`, so it
structurally cannot be recorded in provenance. The *scientific content* of
"which material" does travel — its three declared quantities are all in
`provenance.inputs` — but the **name** does not, and it is deliberately **not**
smuggled through `ProvenanceRecord.metadata`. Asserted, including the refusal
itself, in `test_b6`.

---

## 6. Copper → aluminium: the required differential

Identical topology (Source → wire_A → load → wire_B → gnd), identical geometry
(`L = 2.0 m`, `A = 2.5e-6 m^2`), identical load (`0.5 ohm`), identical source
(`12 V`), identical environment (`C = 8 J/K`, `hA = 0.2 W/K`, ambient 300 K,
`t = 600 s`), identical coupling policy (seed 300 K, tolerance `1e-6 K`, budget
50). **Only the material record differs** — asserted field by field in
`test_b2`.

| Quantity | Copper | Aluminium | Δ | % |
|---|---|---|---|---|
| wire resistance `R_A` (ohm) | 0.0159237236 | 0.0277038711 | +0.0117801 | **+73.98 %** |
| circuit current `I` (A) | 22.5628610 | 21.6057485 | −0.957112 | **−4.24 %** |
| wire voltage drop (V) | 0.35928476 | 0.59856287 | +0.239278 | **+66.60 %** |
| wire Joule loss (W) | 8.1064921 | 12.9323989 | +4.82591 | **+59.53 %** |
| wire temperature `T_A` (K) | 340.5324482 | 364.6619745 | +24.1295 | **+7.09 %** |
| delivered load power (W) | 254.5413472 | 233.4041845 | −21.1372 | **−8.30 %** |
| source delivered power (W) | 270.7543315 | 259.2689822 | −11.4853 | −4.24 % |
| iterations to convergence | 10 | 12 | +2 | — |

**Seven quantities moved, against a requirement of four**, and every direction
was preregistered in §8 before the run. Every value matches the analytic
prediction computed in a throwaway script importing nothing from `engcore`.

### 6.1 The thermal feedback genuinely closes

`test_c1` runs the *same participants and the same declared models* one-way —
`R` at the seed temperature, one electrical solve, one thermal step, stop — and
compares:

| | one-way | converged | Δ |
|---|---|---|---|
| `R_A` (ohm) | 0.0137853808 | 0.0159237236 | +0.00213834 |
| `T_A` (K) | 335.660686 | 340.5324482 | **+4.87176 K** |
| wire Joule loss (W) | 7.1321394 | 8.1064921 | +0.974353 |
| delivered load power (W) | 258.6848884 | 254.5413472 | −4.14354 |

The converged answer differs from the one-way answer by **4.87 K — 4.9 million
times the coupling tolerance**. It is not spreadsheet arithmetic. The iterate
sequence contracts monotonically over 10 sweeps
(44.3 → 6.4 → 0.81 → … → 4.7e-7 K, `test_c2`), and every iteration's thermal
provenance records the same `t0`, so it is coupling and not time marching
(`test_c4`).

### 6.2 The propagation chain, as a traceable record

```
ConductorMaterial(copper)                       declared record, with its source
  → rho_ref, alpha, T_ref as ScientificParameters   provenance.inputs
  → LINEAR_RESISTIVITY_MODEL @ T                ExecutionBinding(model, realization, solver)
  → resistivity  1.7231726e-8 ohm*m             result metric, transported by a declared edge
  → GEOMETRIC_RESISTANCE_MODEL with L, A        ExecutionBinding, L and A in provenance.inputs
  → R_wire_A     0.0159237236 ohm               transported to the electrical problem's R:wire_A
  → ELECTRICAL_DC_LINEAR (MNA)                  I = 22.5628610 A
  → resistor_power:wire_A  8.1064921 W          transported to the thermal problem's heat_input
  → LUMPED_CAPACITY_MODEL                       T = 340.5324482 K
  → back to LINEAR_RESISTIVITY_MODEL            the torn edge, seeded once, iterated 10 times
```

`test_b4` asserts each hand-off numerically **through the declared edges only**
(`R == rho * L / A` to `1e-14` relative; `rho` equals the material's own law at
the temperature its own provenance records). `test_b5` asserts the whole chain
appears in `CoupledRun.provenance.bindings` as one record. Nothing in the
harness writes a downstream value.

---

## 7. Multiplicity, and the third-material falsification

### 7.1 No aliasing

Case D changes **only wire_A's material** (aluminium), leaving wire_B copper.

| | wire_A (aluminium) | wire_B (copper) |
|---|---|---|
| resistance (ohm) | 0.0280284574 | 0.0158166682 |
| temperature (K) | 368.2308966 | 338.5032055 |

* With **identical** materials, wire_A and wire_B agree to better than `1e-12`
  relative (`test_d1`) — symmetric handling, no positional accident.
* Changing wire_A leaves wire_B's declaration, material record, conductor and
  serialized form **bit-identical** (`test_d2`).
* **The decisive assertion** (`test_d3`): each wire's resistivity still equals
  *its own* material's law at *its own* recorded temperature, to `1e-14`
  relative, and its resistance still equals `rho_i * L_i / A_i`.
* Each instance has its own provenance record with its own `run_id` and its own
  material quantities (`test_d4`).
* Two elements sharing an id are refused at construction (`test_d5`); a
  conductor and a body that are not one object are refused (`test_d6`).

**Stated plainly, because it is easy to misread:** wire_B's *numbers* do move
when wire_A's material changes — the two are in series and share a current.
That is coupling, not aliasing. A topology in which two instances could not
influence each other would exercise nothing, which is the same argument the
pre-existing `CoupledElectroThermalSystem` docstring already makes.

### 7.2 The third material — measured, zero code change

**Yes.** Two independent measurements:

* **Structural:** `test_t6` parses the module and asserts that no material name
  appears as a string literal anywhere outside the catalogue's own assignment
  block — in the new modules, in the DC domain, in `engcore.scientific`, in
  `engcore.coupling`, in `engcore.application` or in the transports. The
  catalogue's variable names are *derived from the module*, not transcribed, so
  the guard itself needs no edit when a material is added.
* **Experimental:** a **fifth** material (gold, `2.214e-8 ohm*m`, `3.40e-3 /K`)
  was added and measured, then reverted. The diff was **11 insertions and 1
  deletion in one file, entirely inside the catalogue data block** — the record
  literal plus its name in the catalogue tuple. It ran end-to-end immediately
  (`criterion_met`, 10 iterations, `R = 0.0212559 ohm`, `T = 351.999 K`) and the
  focused suite stayed at **76 passed**. Zero changes to any model,
  realization, solver, problem builder, admission check, serializer or coupling
  code.

Silver, the milestone's declared third material, runs end-to-end and lands
where physics requires — `R_Ag 0.0148668 < R_Cu 0.0159237 < R_Al 0.0277039`
(`test_t3`, `test_t3b`).

### 7.3 A fourth material the catalogue has never seen

`test_t4` constructs a resistance-alloy-like material **inside the test**,
never registered anywhere, and runs the whole chain on it; `test_g3` shows
`supports()` answers for it with no binding and no catalogue lookup. **The
mechanism is property-driven, not catalogue-gated and not branch-driven.**

### 7.4 The second functional form is load-bearing

Tungsten (quadratic `rho`) at 20 V converges to a state the *same material's*
linear form — same `rho_ref`, same `T_ref`, same first-order `alpha` — does not
reach:

| | quadratic | linear-only | Δ |
|---|---|---|---|
| `T_A` (K) | 759.553617 | 744.643001 | **14.9106 K** |
| `R_A` (ohm) | 0.13928197 | 0.12516787 | 0.01411 |

That is **1.5e7 × the coupling tolerance**, so the quadratic term is not
decorative. And material identity *selects the model that is evaluated*, from
data: `COPPER.resistivity_model()` is the linear model, `TUNGSTEN.resistivity_model()`
is the quadratic one, and the executor is looked up by **declared realization
id**, never by material name (`test_t5b`).

---

## 8. Serialization

| Property | Test | Result |
|---|---|---|
| chain round-trips and preserves material selection | `test_f1` | `PowerChain.from_dict(json.loads(json.dumps(...)))` equals the original; a quadratic material comes back as `QuadraticResistivityMaterial` |
| component identities and series order stable | `test_f2`, `test_f6` | `component_ids`, `circuit_id`, `electrical_problem_id` unchanged; elements serialize as a **list**, because the order assigns the nodes |
| reconstruction preserves semantics | `test_f3` | a chain rebuilt from JSON reproduces every resistance and temperature **to the last digit** |
| unsupported schema fails clearly | `test_f4`, `test_e1[invalid_serialized_version]`, `test_e1[unsupported_material_schema]` | `electrothermal_power_chain/2`, `linear_resistivity_material/2`, `material_conductor/2` and an unknown material schema are all refused by `require_schema` / a closed reader table |
| unknown element kind refused, not guessed | `test_f5` | refused, naming the admissible kinds |
| a wire's record carries no library membership | `test_t6k` | `CategoricalValue.vocabulary == ()`; no other catalogue name appears in a copper wire's serialized problem |
| the catalogue is not needed to serialize | `test_f7` | an inline material round-trips identically |

Three new schemas are minted, all pack-local: `conductor_material` family
(`linear_resistivity_material/1`, `quadratic_resistivity_material/1`),
`material_conductor/1`, `electrothermal_power_chain/1`. **No stored payload
exists yet**, which is why the record shape was settled before implementation
rather than after — `require_schema` is exact-match with no migration route.

## 9. Admission — detection is not enforcement

**17 negative cases**, each asserted to raise, each with a spy over *every*
solver this milestone can reach (`LinearResistivitySolver`,
`QuadraticResistivitySolver`, `GeometricResistanceSolver`,
`LumpedThermalSolver`, `ElectricalDCSolver`, `ResistancePropertySolver`)
asserting **zero solve calls after the refusal**:

`non_positive_area_zero`, `non_positive_area_negative`,
`invalid_length_zero`, `invalid_length_negative`,
`non_positive_reference_resistivity`, `unsupported_material_name`,
`unsupported_material_schema`, `unknown_property_form`,
`unit_mismatch_length`, `unit_mismatch_seed`,
`temperature_outside_applicability`, `unresolved_connection`,
`duplicated_identity`, `invalid_serialized_version`, `chain_with_no_wire`,
`material_with_no_provenance`, `material_reference_outside_its_own_range`.

Three properties beyond the raw list:

* **The gate is on the executed path.** `run_power_chain` and `compose` both
  call `admit_power_chain` themselves (`test_e3`). A gate a caller can skip is
  detection.
* **Ordering was repaired before it could be claimed.** `initial_resistances`
  bootstraps the first electrical record by *executing* the declared models, so
  a plan check placed after it would have let two solves per wire run before a
  broken connection was noticed. `declared_problem_ids` + `_refuse_unresolved_edges`
  compute the composition's problem ids **without solving**, and run first.
* **Refusal after a run is not enforcement either.** `assess_run_applicability`
  **assesses and never refuses** the material range at the *converged*
  temperature. `test_e4` drives a chain that starts admissibly at 300 K and
  converges past 450 K: every sub-solve reports success, `CouplingOutcome` is
  `CRITERION_MET`, and the assessment reports `OUTSIDE_VALIDATED_DOMAIN` for
  both wires. That closes the reporting half of the gap `ET-VERTICAL` measured,
  without destroying the record that makes it readable.

## 10. Falsifier findings and their disposition

`architecture-falsifier` returned **FALSIFIED** on the pre-implementation
design, with four BLOCKERs, four BREAKING-RISKs and one implementation concern.
**All nine were closed before a line of production code was written.**

| # | Finding | Disposition |
|---|---|---|
| **X1** BLOCKER | `resistivity > 0` as a `ValidityDomain` condition on a **variable** would be permanently `UNKNOWN`, so `admit_conductor` would refuse *every* conductor | Moved to `GeometricResistanceSolver.validate()` as an admissibility check, following `ResistancePropertySolver`'s own precedent. `test_t6j` asserts the geometry assessment has **no** unknown conditions. |
| **X2** BLOCKER | a per-material `model_id` makes a stateless `supports()` impossible for an uncatalogued material | One shared model per functional form. `supports()` compares one fixed `(model_id, version)` pair, no string parsing, no state (`test_g2`, `test_g3`). |
| **X3** BLOCKER | material identity could only be recovered by parsing a `model_id`, since `ProvenanceRecord` refuses non-`Quantity` inputs | The three material **quantities** are recorded; the name is not, and the gap is stated rather than routed through `metadata` (`test_b6`, §5.3). |
| **X4** BREAKING-RISK | model identity as a function of mutable data, with a literal `version` | Eliminated by X2's fix: no identity is derived from the catalogue. |
| **X5** BREAKING-RISK | the geometry realization would claim `electrical:temperature_dependent_resistance`, which it does not provide | It provides `electrical:resistance_from_geometry` and **requires** `electrical:temperature_dependent_resistivity`. `test_g5` asserts the pre-existing capability still resolves to exactly the pre-existing realization. |
| **X6** BREAKING-RISK | a catalogue-derived `CategoricalValue.vocabulary` would be a time-varying hidden registry inside a per-wire record, and unfalsifiable | `vocabulary=()`; refusal of an unknown material is `resolve_material`'s job (`test_t6k`, `test_e2`). |
| **X7** BREAKING-RISK | a pre-run gate cannot gate the converged state | The gate is named and scoped to the declaration and the seed; `assess_run_applicability` reports on the converged state and never refuses (`test_e4`). |
| **X8** BLOCKER | the linear consumer is algebraically a reparameterization of `LINEAR_TCR_MODEL` (`R_ref = rho_ref L / A`) and therefore could not disagree with it | **Partially closed.** A quadratic form was added, is inexpressible by the linear model, and differs by 14.9 K at the exercised operating point (§7.4). See §12 for what remains open. |
| **X9** concern | `initial_resistances` at each material's own reference temperature describes a state the system never occupies | Evaluated at the **seed**, so the declared record reproduces iteration 1. |

Findings the falsifier explicitly did **not** raise, and which this milestone
inherits unchanged: fan-in refusal, tolerance dimension, seed shadowing, the
`STATE`/`CONTROL` role convention, and the scalar-endpoint limitation of
`QuantityDependency`.

**Baseline note.** Both the reviewer and the falfifier initially read
`/home/user/crafty` (`03c30f6`, 48 commits behind) rather than the
`composite-system0` worktree. The falsifier was re-pointed and its findings are
against the correct tree. The reviewer's baseline reconciliation section
therefore contains four stale claims (no `engcore.coupling`, no
`engcore.application`, FULL 1784, `MODEL0-R` the only freeze); its
*architectural* reasoning does not depend on them, except for its sub-decision
(f), which it answered conditionally and which is resolved in §11.

## 11. Two pre-existing tests were modified

The brief permits this only for a demonstrated old-test defect, documented
explicitly. Both are documented here and in commit `37633e3`.

**(a) `tests/test_coupling_pack_relocation.py::test_e2_the_packs_declare_no_coupling_schema_of_their_own`.**
It asserted `"schema_string" not in called` — *no system pack may mint any
schema string at all*. That is broader than the test's own stated claim ("One
family, one owner. Neither pack mints a **coupling** schema string") and
broader than the relocation it guards. It cost nothing when written, because no
pack then owned a record of its own, and became wrong the moment one did: a
system pack owning the serialization of **its own composition declaration** is
the same ownership the DC domain already has over `electrical_dc_circuit/1`,
and the opposite of the false ownership `COUPLING-PACK-RELOCATION` removed. The
replacement is **stronger** in two directions: the forbidden set is derived from
`engcore.coupling`'s own published schema constants instead of a hand-written
token list, so it cannot rot when a coupling schema is renamed; and a computed
(non-literal) schema name is now refused outright, which the blanket form never
checked because it stopped at the call name.

**(b) `tests/test_api_mcp_v0.py`, two scope guards.** Both read
`git diff <that milestone's own prereg commit>`, so they describe "what changed
since `API-MCP-V0` began" rather than "what `API-MCP-V0` changed", and fail for
**every** later milestone that adds a file under `src/engcore/domains/` or
`src/engcore/systems/electrothermal/`. The repository already carries this
repair three times in `tests/test_executable_scientific_spec.py`
(`_PLANNER_DISCOVERY_EXCEPTIONS`, `_FIELD_SUPPORT_FOUNDATION_EXCEPTIONS`,
`_API_MCP_V0_EXCEPTIONS`); this is the fourth and follows that precedent. The
two new files are named individually, so an unexpected addition is still loud,
and everything `API-MCP-V0` actually claims is preserved: universal core, the
coupling package and the Fluid-Thermal pack are still asserted byte-for-byte
untouched, and the set of **pre-existing** files it edited is still exactly
three.

No other test was edited, and no assertion anywhere was weakened to let the new
architecture pass.

---

## 12. What this milestone proved, and what it did NOT prove

### Proved

* A real engineered system — Source → wire → load → wire, with material,
  geometry, thermal state and connections — is representable with **zero new
  universal contracts** and **zero edits to universal core or to the coupling
  package**.
* Changing **one** legitimate component property (the wire material)
  automatically moves **seven** downstream quantities through declared models
  and the pre-existing coupling loop, with no domain conditional anywhere and
  no manual downstream assignment.
* The thermal feedback closes: the converged fixed point differs from the
  one-way answer by 4.87 K, 4.9e6 × the tolerance.
* Two instances of one component definition keep independent identity, state,
  material binding and provenance; each evaluates its own material's law.
* A **third** and a **fifth** material are pure data — measured, 11 lines, one
  file, one block, zero code change. A **fourth**, never in the catalogue at
  all, works identically.
* Material identity selects the *model* that is evaluated, from data, and a
  second functional form changes the answer by 14.9 K.
* Invalid configuration stops before any solver executes, across 17 cases,
  proven with spies.
* Existing API/MCP semantics and every existing number are unchanged.
* Two concrete limitations of the existing contracts were *measured*:
  `ValidityDomain` cannot express per-material ranges on a shared model (§5.2),
  and `ProvenanceRecord.inputs` cannot record a typed categorical (§5.3).

### Did NOT prove

* **Nothing about generality across architectures.** Copper, aluminium, silver,
  tungsten and the inline alloy are variants of **one** consumer, not materially
  different architecture consumers. This is `L1 EXERCISED` and nothing more.
* **The power chain is not the second materially different consumer** that
  `ET-VERTICAL`'s promotion criterion requires: same author, same pack, same
  interface, same branch, same day. **Nothing is promoted by this milestone.**
* **X8 is only partly closed.** The *linear* half of this consumer remains
  algebraically a reparameterization of `LINEAR_TCR_MODEL` with
  `R_ref = rho_ref L / A`. The quadratic form is genuinely new to the
  repository, but it is one material in one pack, and the coupled physics is
  the physics `ET-VERTICAL` already holds. The new ground is the **data path**
  — material identity, geometry, admission, and a four-node cycle — not the
  coupled physics.
* **The declared series order is unfalsifiable by this consumer.** In a series
  loop across an ideal source the current is common, so permuting the elements
  changes no number.
* **Two epistemic standards for one physical object remain, inside one pack.**
  A wire's geometry is a declared scientific input on the *electrical* side,
  while the *same* wire's thermal side keeps geometry folded into a lumped
  `heat_capacity` and `ambient_conductance`. Nothing here forces resolving it;
  the day a consumer wants `rho_m c_p V`, the same argument that justified this
  milestone applies to `ThermalBody` — and at that moment `ConductorMaterial`
  is in the wrong package (the promotion trigger is written into its docstring).
* **Nothing about fluids, media, anisotropy, alloy composition or material
  state.** `CategoricalValue(name)` holds for solids with a fixed property set
  and does **not** generalise to a medium, where identity is phase +
  composition + state. It must not be treated as precedent for one.
* **Nothing about fan-in, two-state feedback, field-valued coupling, planning
  or selection among capability providers.** Two realizations now provide
  `electrical:temperature_dependent_resistivity`; `RealizationRegistry` filters
  and does not rank, no planner exists, and none was built.

## 13. Divergences from the preregistration

Recorded here rather than by amending it.

1. **Materials.** §4.1 preregistered "copper, aluminium, tungsten as the
   starting set" with silver added later as the third-material test. The
   committed catalogue holds all four from the first implementation commit,
   because the milestone's real question — "does a new material need code?" —
   is answered better by the *structural* guard plus the measured fifth-material
   (gold) experiment than by a commit-ordering claim. Both are reported in §7.2.
2. **`ThermalBody` serialization.** Not anticipated in §4.1. `ThermalBody`
   predates this milestone and has no `to_dict`. Rather than edit a frozen
   sibling domain for one consumer, `power_chain` writes and reads the body's
   own declared fields locally, with the finding recorded in the module: the
   day a second consumer needs the same thing, the method belongs on the record.
3. **`declared_problem_ids` / `_refuse_unresolved_edges`.** Not in §4.1. Added
   after the spy measurement showed that a bare `check_against` would fire only
   *after* the bootstrap had run two solves per wire (§9).
4. **`compose` admits before bootstrapping.** Same reason.
5. **Numerical predictions.** §8 predicted `rho_Cu(300 K) ≈ 1.691e-8` and
   `R ≈ 1.353e-2 ohm` from a coefficient referred to 300 K; the committed
   material refers its coefficient to 293.15 K, giving `1.7231726e-8` and
   `1.3785381e-2 ohm` at 300 K. The *directions*, the *ratios* and the
   ≥4-quantities criterion — the falsifiable content — are unchanged, and all
   asserted values were recomputed analytically before the suite ran.
6. **Two pre-existing tests modified** (§11), which §5 of the preregistration
   did not anticipate.

## 14. Architecture fitness vector

| # | Dimension | Assessment |
|---|---|---|
| 1 | **Scientific correctness** | Good. Every claim is a declared model with a stated validity domain, stated assumptions, `SELF_CONSISTENT` status and no invented citation. `rho(T)` and `R = rho L / A` fail independently and are separately falsifiable. The tungsten second-order coefficients are a two-point fit performed for this milestone and the record says so in its own `source` field. |
| 2 | **Domain extensibility** | Good. A new material is data (measured: 11 lines). A new functional form is one model + one realization + one solver + one table entry, and touches no existing material. No universal core edit is required for either. |
| 3 | **Breaking-change risk** | Low. Purely additive: 2 new files, 1 export list, 3 new pack-local schemas with no stored payload anywhere. Every pre-existing number is asserted unchanged. |
| 4 | **Reversibility** | High. Deleting the two files and the export block restores `f1ed553` behaviour exactly. Nothing else depends on them. |
| 5 | **Implementation complexity** | Moderate and honestly higher than the null: ~2 900 production lines against ~0. The cost buys typed geometry, material identity, 17 refusals, provenance and serialization that the null attempt structurally could not have. |
| 6 | **Runtime cost** | Negligible. Two extra scalar algebraic solves per wire per sweep; the 7-problem chain converges in 10–13 sweeps in milliseconds. The focused suite is 4.7 s and stays in FAST. |
| 7 | **Serialization impact** | Contained. Three new pack-local schemas, zero changes to any existing schema string, zero stored payloads. `require_schema` is exact-match, so the shape was settled *before* implementation, which is the only cheap moment. |
| 8 | **Time-to-proof** | Good. One reviewer round, one falsifier round, then executable evidence — the ~2-round cap held, and all nine falsifier corrections were absorbed before implementation rather than after. |
| 9 | **Time-to-commercial-relevance** | Modest and honest. This is the first Crafty consumer where a *bill-of-materials-like* fact (what a part is made of, how big it is) drives a physical answer end to end. It is not a materials platform, not a BOM, not a component library, and does not shorten the path to one by itself. |

## 15. Decision

**KEEP.**

The design as implemented survived the falsifier's nine corrections, holds
under 76 focused assertions and 2382 full-suite tests, and added **no universal
contract**. Its two known limitations (§5.2, §5.3) are limitations of the
*existing* contracts, are recorded with measurements, and are not worked around.

Reopen triggers, stated so they are recognised rather than discovered:

1. **A non-electrical domain needs a property of the same named material** —
   then `ConductorMaterial` is in the wrong package, and the choice is a
   domain-to-domain import or a duplicate. This is the most likely trigger and
   it is one consumer away.
2. **A consumer needs two feedback state coordinates of different dimension**
   (e.g. `R = f(T, SoC)`) — `FixedPointCouplingPlan` refuses that today, by
   declaration.
3. **A consumer needs fan-in** (two heat paths into one body) — refused today,
   by declaration.
4. **A consumer needs a medium rather than a solid** — `CategoricalValue(name)`
   does not generalise, and must not be treated as precedent.
5. **Anyone proposes to persist a `conductor_material/1` payload** — the record
   shape must be settled first; `require_schema` has no migration route.
6. **A planner or a selector among capability providers appears** — two
   realizations now provide one capability, deliberately unranked.

## 16. Recommendation for PROPULSION0

1. **Do not start by minting `ComponentInstance` or `Port`.** This milestone
   measured both as not forced at arity 2 with material, geometry and state
   attached. Re-run the zero-new-contracts gate first; it cost half a day here
   and removed most of the design.
2. **The one thing most likely to force a real contract next is the *second*
   domain wanting the *same* material** — a thermal model needing `rho_m`,
   `c_p` for the copper the electrical side already declares. If PROPULSION0
   includes that, it is the strongest available evidence for or against a
   material contract, and it should be designed for deliberately rather than
   discovered.
3. **Fan-in is the next structural wall.** Any propulsion topology where two
   sources feed one endpoint (two heat paths into one body, two torques into
   one shaft) hits `FixedPointCouplingPlan`'s refusal immediately. Decide the
   combination rule as a *declared* record before writing a consumer that needs
   it; do not let a loop invent one.
4. **Two feedback state coordinates of different dimension is the wall after
   that**, and the plan's tolerance is single-dimension by declaration.
5. **Do not treat copper-vs-aluminium as generality evidence.** If PROPULSION0
   needs an `L2` claim, it needs a *materially different* consumer written
   against these records unedited, by a different concern — not a second
   variant of this one.
6. **Reuse `initial_resistances`' discipline**: every number a harness produces
   must come out of a declared model with an `ExecutionBinding`, including
   bootstrap values. It costs two extra solves and removes an entire class of
   "the demo computed it" objection.
