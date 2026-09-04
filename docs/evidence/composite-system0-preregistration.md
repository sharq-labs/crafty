# COMPOSITE-SYSTEM0 — preregistration

Written and committed **alone**, before any source file on this branch was
added or edited. Not amended afterwards: divergences are recorded in
`docs/evidence/composite-system0-evidence.md`.

* Branch `composite-system0`, worktree `/home/user/crafty-composite`.
* Base `f1ed553` (canonical, FULL 2306 passed / 0 failed / 0 errors) plus the
  docs-only reconciliation commit `fdd3359`.
* Entry reading: `docs/evidence/canonical-state-reconciliation-2026-09-04.md`.

---

## 1. Hypothesis

Can Crafty represent a real engineered system as reusable component instances
with material / state / connection semantics, such that changing **one**
legitimate component property propagates automatically through the existing
scientific models and the existing coupling machinery — **without** domain
conditionals in universal core, hardcoded demo propagation, duplicating
`ScientificProblem` or `QuantityDependency`, embedding solver semantics into
components, untyped metadata escape hatches, or a universal "God graph"?

The reconciliation note narrows this. Two questions are genuinely open:

* **(a)** Is a component-*instance* contract forced beyond the identity that
  existing per-problem / per-declaration structures already provide?
* **(b)** Do material identity plus geometry force new semantics?

Whether Crafty can evaluate a temperature-dependent property is **not** open:
`src/engcore/domains/electrical/material.py` already does it, and closed-loop
`R(T)` coupling already runs at arity 2.

## 2. Baseline

| Fact | Value |
|---|---|
| Base commit | `fdd3359` (docs) on `f1ed553` (code) |
| FULL at `f1ed553` | 2306 passed / 0 failed / 0 errors (independently re-verified) |
| FAST re-measured in this worktree, this session | **1681 passed / 625 deselected** |
| Environment | `.venv` (numpy, scipy, pint, pytest, scikit-learn) + a `.pth` putting `src/` and the repo root on `sys.path` |

**Environment divergence recorded up front.** With a bare `venv` and no
`.pth`, `tests/test_min_field_support_foundation.py::test_g1_fresh_process_reconstructs_and_reports_no_issues`
fails, because it launches a **subprocess** that imports `engcore` and pytest's
`pythonpath` setting does not reach a child process. That is an environment
defect, not a code defect, and it is repaired by putting `src/` on the venv's
path. No test file is edited for it.

## 3. Step-1 result: the zero-new-contracts gate

Attempted honestly before any design, using only `ScientificProblem`,
`ScientificModelDefinition`, `ModelRealizationDefinition`, `QuantityDependency`,
`ExecutionBinding`, `TemperatureDependentConductor`, `DCCircuit`, `ThermalBody`,
`run_fixed_point` and the existing serialization.

**What is NOT forced (recorded as results, not as omissions):**

* **`ComponentInstance` is not forced.** `CoupledStage` already pairs a
  conductor and a body under one `component_id`, `CoupledElectroThermalSystem`
  already refuses duplicate component ids, and each instance already poses its
  own `ScientificProblem`s with their own provenance. Two wires are already two
  stages. **Kill criterion "Component duplicates `ScientificProblem`" is
  answered by not creating a Component.**
* **`Port` / connector is not forced**, on any of the eight readings the brief
  enumerates. `DCCircuit` already carries typed topology (node existence,
  exactly one declared reference node, polarity, duplicate-id refusal);
  `QuantityDependency` already carries data dependency, direction and unit
  compatibility; `FixedPointCouplingPlan` already **refuses** fan-in rather
  than inventing a combination rule. Nothing in this milestone can
  differentiate a connector contract.
* **`SystemDefinition` and `MaterialBinding` are not forced.**
* **A universal `Material` / `MaterialState` / `MaterialProperty` contract is
  not forced.** One consumer does not reopen `MODEL0-R`'s deferral of
  materials from core.
* The topology Source → Wire A → Load → Wire B is already expressible.

**What genuinely does not work today:** `R(T) = rho(T)*L/A`. The existing
`LINEAR_TCR_MODEL` is parameterised by `reference_resistance`, so geometry has
no home, resistivity has no home, and material identity does not exist. If the
harness computes `R_ref = rho_ref*L/A` in Python and feeds the existing
conductor, then

1. `L`, `A` and the material appear in no problem, twin, provenance record or
   serialized artifact;
2. a non-positive area cannot be refused by any contract (and `L < 0` with
   `A < 0` yields an *admitted* positive resistance);
3. an unsupported material cannot be refused, because no material exists;
4. the `rho*L/A` step is an unmodelled scientific claim executed in demo code
   with no model, no realization, no solver and no `ExecutionBinding` — i.e.
   exactly the hardcoded demo propagation this milestone forbids.

## 4. Chosen alternative

**D1 — pack-local material data plus declared claims; zero new universal
contracts.** Selected by `architecture-decision-reviewer`
(ACCEPT WITH CHANGES on alternative A1, six changes, all adopted) over: A0
null / caller-side arithmetic (rejected: defects 1–4 above); A2 universal
composite contracts (deferred: no consumer, and Modelica's retrofit of a third
connector variable kind in 3.1 is direct negative precedent); A3 extend
`TemperatureDependentConductor` in place and branch in its solver (rejected:
a solver-level branch, and it edits a file three milestones' quoted numbers
rest on); A4 universal material contract (deferred: reopens a documented
deferral with one consumer); A5 catalogue-free (partially adopted — inline
materials are supported alongside the catalogue).

Then attacked by `architecture-falsifier`, which returned **FALSIFIED** with
four BLOCKERs (X1, X2, X3, X8), four BREAKING-RISKs (X4–X7) and one
implementation concern (X9). **All nine corrections G0–G6 plus X9 are adopted
before implementation.** The design preregistered below is the corrected one.
The pre-correction design is recorded in the evidence document.

### 4.1 What gets built

**New file `src/engcore/domains/electrical/conductor_material.py`**

* `ConductorMaterial` — a frozen, serializable **base declaration**: `name`,
  `reference_temperature`, `minimum_temperature`, `maximum_temperature` (the
  material's own validated applicability range), `source` (a non-empty
  provenance string). It declares **science, never execution**: it exposes the
  `ScientificModelDefinition` and `ModelRealizationDefinition` for its own
  resistivity claim and the `ScientificParameter`s that claim needs. It
  exposes no solver — mapping a declared realization to an executor is the
  pack's job, not the record's.
* Two concrete forms, because **functional form**, not material name, is what
  justifies more than one model (falsifier G0):
  * `LinearResistivityMaterial` — `rho(T) = rho_ref (1 + alpha dT)`
  * `QuadraticResistivityMaterial` — `rho(T) = rho_ref (1 + alpha dT + beta dT^2)`
* `LINEAR_RESISTIVITY_MODEL` and `QUADRATIC_RESISTIVITY_MODEL` — **two shared**
  `ScientificModelDefinition`s (one per form; *not* one per material — falsifier
  G1). Output metric `resistivity` [ohm*m]. Validity domain carries only
  universally true conditions (`reference_resistivity > 0`, strict). The
  **per-material temperature range stays on the material record and has exactly
  one authority there**; it is assessed by constructing a `ValidityDomain` from
  the material at assessment time.
* `GEOMETRIC_RESISTANCE_MODEL` — one shared model, `R = rho * L / A`; inputs
  `resistivity` (VARIABLE, role CONTROL), `length` and `cross_sectional_area`
  (PARAMETER); output metric `resistance` [ohm]; validity `length > 0` and
  `cross_sectional_area > 0`, both strict. `resistivity > 0` is a **solver
  admissibility check**, not a validity condition, because
  `ScientificProblem.validity_context` is built from parameters only and a
  variable-sourced condition would be permanently `UNKNOWN` (falsifier G2).
* Capabilities, declared truthfully (falsifier G4): resistivity realizations
  provide `electrical:temperature_dependent_resistivity` and require
  `thermal:body_temperature`; the geometric realization provides
  `electrical:resistance_from_geometry` and requires
  `electrical:temperature_dependent_resistivity`. The geometric realization
  does **not** claim `electrical:temperature_dependent_resistance`, which it
  does not provide on its own.
* `MATERIAL_CATALOGUE` — copper, aluminium, tungsten (quadratic) as the
  starting set; `resolve_material(name)` refuses an unknown name and names the
  known set. Inline construction without the catalogue is equally supported.
* `MaterialConductor(component_id, material, length, cross_sectional_area)` —
  frozen, serializable, refuses non-positive or wrong-dimension geometry in
  `__post_init__`.
* `build_resistivity_problem` / `build_geometric_resistance_problem` — two
  `ScientificProblem`s per conductor. Material identity travels on the
  resistivity problem as `ScientificParameter(name="material",
  value=CategoricalValue(name))` with an **empty vocabulary** (falsifier G5:
  a catalogue-derived vocabulary would be a time-varying hidden registry
  serialized into a per-wire record).
* `LinearResistivitySolver`, `QuadraticResistivitySolver`,
  `GeometricResistanceSolver` — each satisfies the existing solver protocol,
  binds its declaration to a `problem_id`, verifies the problem restates the
  bound declaration, and dispatches `supports()` on **one fixed model key**
  (stateless; no string parsing of a `model_id`).
* `resistivity_solver_for(material)` — a module-level mapping from **declared
  realization id** to executor. Data-driven, and not a branch on a material
  name.
* `assess_material_applicability(material, temperature)` and
  `assess_conductor_geometry(conductor)` — validity, reported.
* `admit_conductor(conductor, temperature)` — enforcement, raising.

**New file `src/engcore/systems/electrothermal/power_chain.py`**

* `WireSegment(conductor, body)` (shared `component_id`, same pack convention
  `CoupledStage` uses) and `FixedLoad(component_id, resistance)`.
* `PowerChain(chain_id, source_voltage, elements)` — an ordered series from the
  source through the elements to the reference node; refuses duplicate
  component ids and requires at least one wire. Exercised topology:
  **Source → Wire A → Load → Wire B → gnd.**
* `chain_problems` — 1 electrical + 3 per wire = **7** for the two-wire chain.
* `chain_dependencies` — **four** `QuantityDependency` edges per wire:
  `electrical.resistor_power:<cid> → thermal.heat_input`;
  `thermal.final_temperature → resistivity.temperature`;
  `resistivity.resistivity → geometric.resistivity`;
  `geometric.resistance → electrical.R:<cid>`. A 4-cycle per wire.
* `chain_plan` — tears the thermal→resistivity temperature edge only.
* `run_power_chain` — calls the admission gate itself, builds the dispatch
  table, and hands everything to `run_fixed_point` **unedited**.
* `initial_resistances` — builds the first electrical problem record by
  **executing the declared models at the seed temperature** through the
  published solver path (falsifier X9), so no arithmetic anywhere in the
  harness computes a resistance outside a declared model.
* `admit_power_chain(chain, *, seed_temperature)` — gates the **declaration and
  the seed**, which is all it can gate, and is named accordingly;
  `assess_run_applicability(chain, run)` **assesses, never refuses**, the
  material range at the *converged* temperature (falsifier G6).
* `PowerChain.to_dict` / `from_dict` under `electrothermal_power_chain/1`.

**Nothing else is edited** beyond the two packs' `__init__.py` export lists,
`.gitignore`, and the two documents.

## 5. Contracts expected untouched

`engcore.scientific` (every module), `engcore.coupling` (every module),
`engcore.domains.electrical.dc`, `engcore.domains.electrical.material`,
`engcore.domains.electrical.ngspice`, `engcore.domains.thermal_lumped`,
`engcore.systems.electrothermal.coupled`,
`engcore.systems.electrothermal.resistor_body`, `engcore.application`,
`src/crafty_http`, `src/crafty_mcp`, and every existing test file.

Asserted, not assumed: a test diffs the tracked source tree and fails if any
file outside the allowed set changed.

## 6. Contracts deliberately NOT added

`ComponentInstance`, `Port`, `Connector`, `SystemDefinition`,
`MaterialBinding`, a universal `Material`/`MaterialState`/`MaterialProperty`
hierarchy, a component or material registry in universal core, a hierarchical
composite graph, a scheduler, a planner, a property-provider framework, a
second provenance system, a materials database, CAD/BOM ingestion, and any
`ScientificProblem`- or `QuantityDependency`-like record.

## 7. Mandatory tests (A–H)

| Id | Test |
|---|---|
| **A** | Copper nominal: the chain converges; every declared quantity is reported. |
| **B** | Aluminium nominal: **identical** topology, source, geometry, load, environment, seed, tolerance and budget — only the material record differs. |
| **C** | Temperature perturbation proves the feedback closes: the converged fixed point differs from the one-way single-pass answer by more than the coupling tolerance, and the iterate sequence is monotone toward it. |
| **D** | Multiplicity / no aliasing: wire_A and wire_B are two instances of one component definition with independent identity, state, material binding and provenance; changing wire_A's material leaves wire_B's resistance bit-identical. |
| **E** | Invalid material / property / geometry is refused **before any solver executes**, proven with spies. |
| **F** | Serialization round trip: identities stable, material selections preserved, reconstruction semantically equal, unsupported schema refused. |
| **G** | Direct scientific execution still compatible: the existing `LINEAR_TCR_MODEL` path, the existing `CoupledElectroThermalSystem` and the existing DC domain produce unchanged numbers. |
| **H** | Existing API / MCP semantics unchanged: the execution catalog, its contract and its numbers are byte-identical. |

Plus, beyond A–H:

* **T3 — third material, zero code change.** Silver is added as a
  `LinearResistivityMaterial` **catalogue entry only** and runs end-to-end. A
  test asserts that the set of non-data symbols is unchanged.
* **T4 — fourth material, never in the catalogue.** A material constructed
  inline in the test runs end-to-end, proving the mechanism is not
  catalogue-gated.
* **T5 — the second functional form is load-bearing.** The quadratic material's
  converged answer is not reproducible by *any* reparameterization of the
  existing `LINEAR_TCR_MODEL` anchored at the same reference state.
* **T6 — no domain conditionals.** An AST scan over the new modules and over
  `engcore.scientific` / `engcore.coupling` refuses `if <material name>`,
  `if domain ==`, `if component.type ==` and every material name as a literal
  outside the catalogue data.

## 8. Numerical expectations

The chain: `V = 12 V`; two wires each `L = 2.0 m`, `A = 2.5e-6 m^2`
(≈ AWG 13); a fixed load `R = 0.5 ohm`; each wire a lumped body with
`C = 8.0 J/K`, `hA = 0.05 W/K`, ambient 300 K, initial 300 K, duration 600 s;
seed 300 K; tolerance `1e-6 K`; budget 50.

Predicted, from the equations alone, in a throwaway script importing nothing
from `engcore`, and recorded in the evidence document before the suite is run:

* `rho_Cu(300 K)` ≈ 1.691e-8 ohm*m → `R_wireA(300 K)` ≈ 1.353e-2 ohm.
* `rho_Al(300 K)` ≈ 2.667e-8 ohm*m → `R_wireA(300 K)` ≈ 2.134e-2 ohm.
* Aluminium's higher resistivity must **raise** wire resistance, **lower**
  circuit current, **raise** the wire voltage drop, **raise** wire Joule loss,
  **raise** wire temperature and **lower** delivered load power. Six
  quantities, against a requirement of four.
* Wire A and wire B are identical by construction, so their converged
  resistances must agree to `1e-12` relative — and must **stop** agreeing when
  only wire A's material is changed.

Falsification: if fewer than four quantities move, if any moves in the wrong
direction, if the converged answer equals the one-way answer to within the
coupling tolerance, or if changing wire A perturbs wire B, the hypothesis
fails and is reported as failed.

## 9. Failure criteria (kill criteria)

Stop and report rather than force, if any of these becomes true:

1. any new record becomes a God object;
2. any new record duplicates `ScientificProblem` or `QuantityDependency`;
3. a port or connector secretly encodes electrical-only semantics;
4. material becomes an arbitrary dict / untyped metadata;
5. the composite graph becomes both physical topology **and** execution
   scheduler;
6. the wire example needs a domain conditional in universal core;
7. existing contracts need broad migration for one demo;
8. propagation only works because the harness manually assigns downstream
   values;
9. a third material requires new code.

## 10. Architecture fitness vector (measured, all nine)

1. Scientific correctness; 2. domain extensibility; 3. breaking-change risk;
4. reversibility; 5. implementation complexity; 6. runtime cost;
7. serialization impact; 8. time-to-proof; 9. time-to-commercial-relevance.

## 11. Evidence claim allowed

**PROPOSED / L1 EXERCISED.** Nothing higher, and specifically:

* Copper, aluminium, silver and the inline material are variants of **one**
  consumer, not materially different architecture consumers.
* The power chain is written by the same author into the same pack in the same
  milestone, so it is **not** the second materially different consumer the
  `ET-VERTICAL` promotion criterion requires, and it promotes nothing.
* The falsifier's X8 finding — that the linear half of this consumer is
  algebraically a reparameterization of `LINEAR_TCR_MODEL` — is only partly
  closed by the quadratic form, and the evidence document must say so.

No claim of `VERIFIED`, `PROVEN` or any `L2`+ level is permitted from this
milestone.
