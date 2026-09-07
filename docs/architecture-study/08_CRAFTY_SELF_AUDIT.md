# Architecture Study 08 — CRAFTY ITSELF (self-audit)

**Purpose:** answer the standing repository-review question — *does this repository
materially help build Crafty?* — with the repository under review being **Crafty's
own working tree**.
**Repository studied:** `D:\PhysicsX core`, branch `cross-domain-coverage-stress`,
HEAD `a3db20d`, remote `git@github.com:sharq-labs/crafty.git`.
**Study date:** 2026-09-03.
**Mode:** read-only audit. **No source file was added or edited. This document
freezes nothing, authorizes no architecture, and moves no evidence holding.**

> Studies 01–07 examine external projects. This one does not. The review protocol
> was applied to Crafty itself, which converts the question *"can we learn from
> this repo"* into the more useful one: **how much of Crafty's stated architecture
> is executable, and where does the code contradict the plan?**

Labels used throughout: **FACT** (directly measured in this tree), **INFERENCE**
(drawn from structure), **RECOMMENDATION** (what I think Crafty should do).

---

# 0. What was actually done for this audit

**FACT.** Measurements taken on 2026-09-03, Python 3.14.2 (Windows), from this tree:

| Measurement | Result |
|---|---|
| FAST tier `-m "not expensive"` | **1303 passed**, 522 deselected, 12.84 s |
| SCIENTIFIC tier `-m "not campaign"` | **1821 passed**, 4 deselected, 155.97 s |
| `tests/test_heterogeneous_ngspice.py` alone | **40 passed**, 10.18 s |
| ngspice actually present | **version 42**, reached as `('wsl.exe','-e','ngspice')` |
| Python source files under `src/` | 242 |
| `scientific/ + domains/ + systems/ + data/ + uq/ + inference/ + adequacy/` | 25,523 lines |
| `sria/` | 19,863 lines |
| top-level `src/engcore/*.py` (legacy optimizer stack) | 16,997 lines |
| `design/` | 3,547 lines |
| LICENSE file | **absent** |
| Commits not on `origin/main` | 3 |

Files read in full or in substantial part: every module under
`src/engcore/scientific/`, `src/engcore/data/`, `src/engcore/systems/electrothermal/`,
the four domain packs' entry points, `src/engcore/sria/{charter,gateway,domain_pack,
admission}` plus `decision/` and `campaign/runner.py` headers, and the
preregistration/evidence pairs for `MODEL0-R`, `DATA-BOUNDARY0`, `MIN-FOUNDATION-ET`,
`ET-VERTICAL`, `HETERO-NGSPICE`, `HOSTILE-CORE-STRESS` and the not-yet-executed
`CROSS-DOMAIN-COVERAGE` preregistration.

---

# 1. What this repository actually is

## 1.1 It is four codebases in one tree

**FACT.**

```text
src/engcore/
├── *.py  (top level, ~17.0k lines)   Engineering AI Core: BBOB/Bayesian-optimization
│                                     research stack — stacked GP + LogEI, adaptive
│                                     policy, candidate arbiter, COCO arenas,
│                                     statistical benchmark harnesses.
│                                     pyproject still names the project
│                                     "engineering-ai-core … Smart experiment engine
│                                     proof of concept".
├── scientific/   (~4.5k lines)       CRAFTY CORE. Domain-neutral records: units,
│                                     IR, models, realizations, capabilities, solver
│                                     protocol, results/provenance/validation/
│                                     uncertainty, twins, composition, experiments.
├── sria/         (~19.9k lines)      Decision-theoretic research campaign engine:
│                                     charter, evidence ledger, critics, arbiter,
│                                     belief-update gateway, EVSI/utility, six action
│                                     families, bounded campaign runner with
│                                     checkpoint/replay/persistence.
├── domains/      electrical/dc (MNA), electrical/material (R(T)), electrical/ngspice,
│                 thermal/conduction1d (+ bulk, + schemes), thermal_lumped,
│                 kinetics/cstr (stiff nonlinear ODE), fluids/aerodynamics (2 formulas)
├── systems/      electrothermal (coupled fixed-point loop), aerospace/multirotor
├── data/         storage-independent bulk data plane (store, resolver, capture)
└── design/, uq/, inference/, adequacy/, validation/
```

**INFERENCE.** The top-level optimizer stack is *heritage*, not Crafty. Nothing in
`scientific/` imports it (verified: `scientific/` contains only intra-package relative
imports), and the only bridge is the `NumericSearchBackend` protocol in
`scientific/experiments/optimizer_adapter.py`, which deliberately imports no backend.
From the product's point of view it is dead weight; from an acquirer's it is diligence
noise.

## 1.2 Abstraction level: it is a *control plane*, not an engine

**FACT.** The scientific core owns **records and refusals**, not numerics. It declares
this itself (`scientific/__init__.py`: *"What this package deliberately does not own:
numerical algorithms"*), and the code matches: no discretization framework, no
assembly, no linear algebra, no scheduler, no persistence. The numerics that exist live
in four thin domain packs (MNA 154 lines; 1-D conduction 432; CSTR 941) driven by
scipy/numpy.

**INFERENCE.** Crafty today is best described as:

> **a scientific record architecture with executable proofs attached** — a contract
> layer that decides what may be *said* about a computation, plus enough real physics
> to prove the contracts survive contact with one.

It is **not**: a solver, a modelling language (no equation syntax anywhere), a
runtime/scheduler, a mesh/field system, a data platform, or a product. It **is**: a
scientific IR + provenance/validation semantics + one partitioned coupling loop + one
external-provider adapter + a separate decision-theoretic campaign engine.

## 1.3 Intended users

**FACT.** There is no API, no CLI for the scientific core, no service surface, no MCP
server, and no persistence for scientific records (SRIA has campaign checkpointing;
`scientific/` has `to_json` and nothing else). The consumers in-tree are tests,
`experiments/`, and system packs.

**INFERENCE.** The current user is the author and the AI sessions working the repo.
That is consistent with the documented strategy (§54.2, *work packages are pulled by a
proof*), but it means **every contract in the core has been validated against consumers
written by the same author in the same week** — which the repository itself repeatedly
flags (`HETERO-NGSPICE` §66.3 withdrew a claim for exactly this reason).

## 1.4 Architectural boundaries that are real

**FACT**, each verified by grep/AST rather than by prose:

1. `scientific/` imports no domain, no LLM, no storage, no web, no optimizer. A
   case-insensitive scan for `electrical|thermal|circuit|resistor|ngspice|kinetics|
   reactor|voltage|temperature` under `src/engcore/scientific/` returns **only
   docstring and comment matches** — zero code branches.
2. `sria/` imports `scientific/`; `scientific/` never imports `sria/`.
3. `data/` (locations) is separate from `scientific/results/data_reference.py`
   (identity). The reference carries a content digest and **no path, URI, host or
   store**.
4. Provider identity is confined to the adapter: `NgspiceInvocation` appears in no
   problem, model, realization or provenance record, and a test asserts the serialized
   result is byte-identical when the executable moves.

## 1.5 Marketing versus implementation

**FACT.** `docs/CRAFTY_MASTER_CONTEXT.md` §5 states *"Crafty = Scientific Simulation
Operating System"*, §17 *"Fields are first-class"*, §18 *"Coupling is a first-class
scientific object"*, and §24 lists a 21-box core including Materials, Fields, Geometry,
Physics Graph, Scientific Capability Graph, Simulation Runtime and Scientific Memory.

Measured against the tree:

| Claim | Implementation status |
|---|---|
| Scientific Simulation OS | No planner, no scheduler, no runtime, no API. **NOT IMPLEMENTED.** |
| Fields are first-class | **Absent.** No field record. `ScientificVariable` has no rank and no support. A PDE field and a lumped scalar are byte-identical records (measured, `HOSTILE-CORE-STRESS` Q2/Q4). |
| Coupling is a first-class object | **Pack-local.** `FixedPointCouplingPlan` lives in `systems/electrothermal/coupled.py`, deliberately not in core. |
| Capability graph | Identity grammar exists; **no traversal, no resolver, no graph.** |
| Materials core | **Absent as a concept.** One state-dependent property `R(T)` expressed as model + realization. |
| Physics execution graph | A directed `QuantityDependency` set + Kahn sort inside one system pack. |
| Scientific memory | `design/memory.py` (design observations) and the SRIA evidence ledger. Not scientific-knowledge memory. |
| Model ≠ Realization ≠ Solver | **IMPLEMENTED and exercised.** |
| Storage-independent bulk data | **IMPLEMENTED and exercised.** |
| External provider substitution | **IMPLEMENTED and executed** (ngspice 42, 40 tests). |
| V&V semantics | **IMPLEMENTED**, with one measured asymmetry (§4.5). |
| UQ | Real but narrow: grid posterior + posterior-predictive + model adequacy, kinetics only. |

**INFERENCE.** The gap between §24 and the tree is not dishonesty — the master context
is explicitly a *target*, and §54.2 says work is pulled by proofs. But the gap is
**large**, and the documents a third party reads first describe a system roughly ten
milestones ahead of the code.

---

# 2. Crafty layer coverage

Because the repository *is* Crafty, "relevance" is re-read as **executable coverage of
that layer today**.

| # | Layer | Coverage | Why |
|---|---|---|---|
| A | Scientific semantics | **HIGH** | Units mandatory (`Quantity` refuses bare numbers and non-finite magnitudes), typed value union, validity domains where `UNKNOWN ≠ valid`, dimensional coherence enforced at problem construction. |
| B | Capability representation | **MEDIUM** | `ScientificCapability` (open, registry-free, `namespace:name`) is real and **matched across two domains**: `thermal_lumped` provides `thermal:body_temperature`, `electrical/material` requires it *by identifier with no code import*. But nothing consumes capabilities for selection. |
| C | Model representation | **HIGH** | `ScientificModelDefinition` with typed inputs/outputs, assumptions, validity domain, `ModelType`, validation status, and `check_against(problem)` producing typed `BindingIssue`s. |
| D | Realization / discretization separation | **MEDIUM-HIGH for realization, NONE for discretization** | `ModelRealizationDefinition` + `ExecutionBinding` proven differentially (backward vs forward Euler; native vs ngspice). But no discretization record exists: `n_cells` lives in `problem.metadata`, and realization *applicability* lives in a module-level dict `_APPLICABILITY` in `thermal_conduction1d_schemes.py`, **not on the record**. |
| E | Field representation | **NONE** | Measured, not assumed. `ScientificDataReference` carries `{name, unit, count, dtype, digest}` — a count is not a shape. |
| F | Geometry / topology | **NONE** | `BoundaryCondition.region` is an opaque label. No support, no normal, no connectivity. |
| G | Boundary / constraint semantics | **LOW** | `BoundaryCondition` exists and has **zero producers in `src/engcore/domains/`** (verified). `ConstraintDefinition` is `metric OP bound` — a study acceptance test, **not** an algebraic relation among unknowns. |
| H | Materials / properties | **LOW** | One constitutive claim `R(T)` with an explicit, well-argued refusal to build a property hierarchy. No substance, phase, composition or anisotropy. |
| I | System / component composition | **LOW** | `CoupledStage` and `CoupledElectroThermalSystem` are pack-local and domain-named. No component, port or connector record anywhere. |
| J | Multiphysics coupling | **MEDIUM** | One executed closed loop, domain-neutral in its execution function, pack-local in its records. See §7. |
| K | Solver abstraction | **MEDIUM** | `ScientificSolver` protocol is real and satisfied by four solvers; `SolverRegistry` has **zero production consumers** (tests only). |
| L | External provider integration | **MEDIUM-HIGH** | One real provider, executed, with a metric-boundary admission gate. No provider framework — deliberately. |
| M | Runtime state | **LOW** | `ScientificTwin` is produced in four modules but **never as instance/runtime-state authority** — four consecutive milestones record zero evidence for that role. Solver lifetime is one call. |
| N | Provenance | **HIGH** | Mandatory `ProvenanceRecord`; `ExecutionBinding` preserves the model→realization→solver ternary structurally; environment facts are caller-supplied, never auto-harvested. |
| O | V&V | **HIGH with one hole** | Seven-rung `ValidationLevel`, checks that declare what they establish, `NOT_RUN ≠ PASS`. Hole: the ladder records an admissibility *violation* and structurally cannot record its *attainment*. |
| P | Uncertainty quantification | **MEDIUM** | `Uncertainty` refuses invention (`UNKNOWN` is a real answer); real grid-posterior inference, posterior-predictive UQ and model-adequacy competition — all inside the kinetics vertical. |
| Q | Optimization / design | **MEDIUM** | `design/` D0–D3 (space, candidates, archives, mixed generation, memory) plus a serious optimizer heritage — but the optimizer is wired to the core only through a protocol, never in production. |
| R | Planning / reasoning | **LOW for Crafty's sense of the word** | SRIA is genuine decision-theoretic reasoning, but it plans **which experiment to buy next**, not which model/realization/solver/coupling to use. See §8. |
| S | Extensibility to new domains | **MEDIUM-HIGH, measured** | Four milestones added domains, a coupling and an external provider with `src/engcore/scientific/` byte-unchanged — asserted by `git diff` inside tests. This is the strongest structural claim the repo holds. |

---

# 3. Patterns worth keeping and generalizing

Twelve, each with location and verdict. Verdicts are re-read for a self-audit as
**KEEP-AND-GENERALIZE / KEEP-LOCAL / KEEP-BUT-FIX / RETIRE**.

### 3.1 Preregistration → evidence → freeze, with a two-ledger discipline
*Where:* `docs/*-prereg.md` + `docs/*-evidence.md` pairs; commit order verified
(`52932d6` prereg, then `222c437` implementation).
*Problem solved:* prevents back-writing predictions after seeing results, and prevents
a passing demo being read as proof of generality.
*Layer:* method, not architecture. *Verdict:* **KEEP-AND-GENERALIZE.**
**INFERENCE:** this is the single most transferable asset in the repository. The
`HOSTILE-CORE-STRESS` evidence document *withdraws two of its own claims* (a false
dilemma about encodings, and an inexpressibility claim) because the falsifier refuted
them. Very few solo projects produce falsifiable negative results about themselves.

### 3.2 The capability grammar: open, registry-free, namespaced
*Where:* `scientific/capabilities.py`, `scientific/solvers/capability.py`.
*Problem solved:* a new domain declares `thermal:body_temperature` without editing
core, and identity excludes prose so rewording a docstring cannot fork a capability.
*Verdict:* **KEEP.** *Caveat:* no consumer beyond declaration (§4.8).

### 3.3 Model ≠ Realization ≠ Solver, with `ExecutionBinding` as the ternary
*Where:* `scientific/realizations/definition.py`, `scientific/results/provenance.py`.
*Problem solved:* "the model is valid here but this realization is not adequate"
becomes sayable; and a set of participants cannot lose which realization computed which
model on which solver. *Verdict:* **KEEP-AND-GENERALIZE.**

### 3.4 Identity ≠ location for bulk data
*Where:* `scientific/results/data_reference.py`, `data/{store,resolver,capture}.py`.
*Problem solved:* relocation cannot mint a new scientific record; substitution is
detected; content addressing dedups for free. The docstring is unusually careful about
what a digest does **not** prove (byte identity ≠ scientific equivalence).
*Verdict:* **KEEP-AND-GENERALIZE.**

### 3.5 A domain-neutral fixed-point loop over a declared dependency graph
*Where:* `systems/electrothermal/coupled.py::run_fixed_point`.
*Problem solved:* the loop takes `(problems, executors, dependencies, plan)` and
contains **no domain branch** — the science lives in a caller-supplied dispatch table.
Execution order is *computed* (Kahn with sorted tie-break); tears are *declared*.
*Verdict:* **KEEP-LOCAL** until a second coupled pair exists (the repo's own promotion
criterion), then **GENERALIZE**.

### 3.6 Admission at the metric boundary
*Where:* `domains/electrical/ngspice.py::_admit_element_power`.
*Problem solved:* a provider whose power channel used another sign convention produced
`validation_status = FAIL` **and the coupled loop transported it anyway**, converging
18.05 K from truth. The fix reconciles the provider's power against its own
voltage/current channels and Crafty's declared resistance, and raises rather than
reporting. *Verdict:* **KEEP-BUT-FIX** — the guard is right, its *placement* is not
general (§4.4).

### 3.7 A property requirement is a model input, not a property hierarchy
*Where:* `domains/electrical/material.py`.
*Problem solved:* avoids a second registry duplicating validity, capability and
provenance machinery. `ModelInputSpec` **is** the property requirement;
`ModelOutputSpec` **is** the property identity. *Verdict:* **KEEP** — noting it is
proven only for a *scalar* property.

### 3.8 Refusal over invention
*Where:* fan-in refused in `FixedPointCouplingPlan.__post_init__`; mixed-dimension
tolerances refused; affine (`degC`) comparison units refused by a ratio-scale test;
`BulkDataResolver` has no best-effort path; `QuantityDependency` refuses to resolve a
field endpoint and returns `MISSING`.
*Problem solved:* a combination rule invented from one consumer becomes a permanent
architectural commitment hidden in an insertion order. *Verdict:*
**KEEP-AND-GENERALIZE.**
**RECOMMENDATION:** make this an explicit written core principle. It is currently
enforced by author discipline, and it is the behaviour most likely to erode under
schedule pressure or a second contributor.

### 3.9 Schema strings with exact-match readers and additive bumps
*Where:* `scientific/serialization.py`; `scientific_result/2`, `provenance_record/2`,
`raw_solver_output/2` with explicit `SUPPORTED_*` tuples.
*Verdict:* **KEEP-BUT-FIX** — exact-match with no migration path is the right default
and a known future cost (§9.8).

### 3.10 Frozen experiments pinned by SHA-256
*Where:* `experiments/electrical_e2/e2_config.py` pins `tests/test_sria_e1_electrical.py`;
tier markers are applied from `conftest.py` precisely so pinned files stay
byte-identical. *Verdict:* **KEEP.**

### 3.11 `ValidityDomain` where absence of limits is not evidence of validity
*Where:* `models/definition.py::ValidityDomain.assess` → `UNKNOWN`.
*Verdict:* **KEEP-AND-GENERALIZE.** An uncommon default, and the correct one.

### 3.12 One write path to belief
*Where:* `sria/gateway.py` — a capability token mintable once; every admission
attributable to a registered authority; rejections logged rather than silent; the
docstring is honest that this is an architectural boundary, not security.
*Verdict:* **KEEP-AND-GENERALIZE** — the analogous rule for the scientific plane
(*one path by which a number becomes transportable science*) does not exist and should
(§9.4).

---

# 4. Patterns that would damage Crafty if generalized

Adversarial. Each works *here* and would break the stated goal if carried forward
unchanged.

### 4.1 `ScientificProblem` is not an executable specification — the deepest issue
**FACT.** `domains/electrical/dc/solver.py:152` raises *"no circuit bound for problem
…; call `bind_circuit()` first — **the universal IR carries no topology**"*. Thermal,
kinetics and ngspice are the same shape: the solver receives a **domain-native
artifact** (`DCCircuit`, `ConductionSlab`, `ReactorRun`) out of band, and the
`ScientificProblem` is a *description* linked to it by a fingerprint string in
`metadata`.

**INFERENCE.** Three structural consequences:
1. `ScientificSolver.prepare(problem)` cannot be satisfied from the problem alone by
   any solver in the repository. The universal protocol is under-determined.
2. Solvers are **stateful** (`self._circuits: dict[problem_id, DCCircuit]`) inside a
   protocol whose other members are pure. Fingerprint-guarded, but still per-instance
   mutable runtime.
3. **A planner cannot be built on the IR.** Anything selecting a realization or solver
   from records selects against a record that does not contain the problem.

*Verdict:* **must not be carried forward.** Highest-cost item in this audit, and it is
not on the current coverage-stress matrix.

### 4.2 `metadata` as the home of unrepresentable science
**FACT.** `domains/thermal/conduction1d/problem.py:429` carries
`"boundary_conditions": "u(0,t) = u(L,t) = 0"` and
`"initial_condition": "u(x,0) = sin(pi x / L)"` as prose strings, plus `n_cells`,
`n_steps`, `field_unit`. Meanwhile `ScientificProblem.validity_context` documents that
it is *"deliberately not sourced from metadata"* — so a reader obeying the platform's
own rule gets `UNKNOWN` for a criterion the metadata answers.

**FACT.** The policy is inconsistent across records: `ScientificProblem`,
`ScientificParameter`, `ScientificModelDefinition` and `ScientificResult` all carry
`metadata: Mapping[str, Any]`; `ModelRealizationDefinition` and `QuantityDependency`
deliberately carry none and say so at length.

**INFERENCE.** Purity on the newest records without a typed home for the concept does
not prevent the leak — it **relocates** it to the older records. The PDE domain is the
proof.

### 4.3 The domain-artifact fingerprint is a load-bearing untyped string
**FACT.** `DOMAIN_ARTIFACT_FINGERPRINT_KEY` in `metadata` is what stops a problem being
paired with a different circuit. It is checked (`verify_problem_matches_circuit`), so
it is not lax — but the association between the universal record and the thing that
actually determines the physics is an untyped key in a free dictionary.

### 4.4 Admission is per-adapter; the coupling boundary trusts blindly
**FACT.** `run_fixed_point` transports `result.values[...]` and never reads
`result.validation`. The ngspice adapter's docstring states the measured consequence
and why the guard was pushed into the adapter.
**INFERENCE.** Every future provider and every future domain must independently
re-derive its own admission guard, and the coupling layer has no rule that a value from
a `FAIL`ed result may not be transported. That is an extension mechanism requiring each
new participant to remember an invariant the core does not enforce — exactly the
failure mode Crafty's architecture principle exists to prevent.

### 4.5 The validation ladder is asymmetric
**FACT.** `ValidationLevel` has seven members and none denotes physical admissibility,
so a *passing* boundedness/positivity/conservation check has nothing to put in
`establishes=`. A domain can record "this is wrong" and cannot record "this was checked
and is right". Corroborating: `ScientificVariable.lower/upper` are typed and
dimension-checked, and **nothing under `results/` ever consults them**.

### 4.6 Realization applicability lives off-record
**FACT.** `thermal_conduction1d_schemes.py::_APPLICABILITY` is a module dict keyed by
realization identity, commented *"Looked up by realization identity because the record
cannot carry it."*
**INFERENCE.** The headline claim — *model validity ≠ realization adequacy* — is
currently expressible only in a side-table owned by one domain. The record supports the
distinction rhetorically, not structurally.

### 4.7 Solver lifetime is one call
**FACT.** Recorded as `ET-VERTICAL` known unknown 6: a fresh solver per problem per
iteration. **INFERENCE.** Any provider with session state — an FMU, a licensed session,
a warm-started nonlinear solver, a persistent mesh — is reset every coupling iteration.
This is the item most likely to block the *next* external provider, and it is not on
the coverage-stress matrix either.

### 4.8 Contracts with no production consumer
**FACT.** `SolverRegistry`: zero non-test consumers. `ScientificCapability` is declared
by four domain modules and consumed by none. `ModelFormulation.DAE` and `.DISCRETE`:
zero production consumers. `ScientificTwin`: produced in four modules, **never** in the
instance-authority role that motivates it.
**INFERENCE.** Roughly a third of the universal surface is validated only by tests
written to validate it. The repo knows this in the individual cases; the *cumulative*
effect is a core whose most-advertised abstractions are its least-exercised ones.

### 4.9 Two model vocabularies: SRIA is a parallel universe
**FACT.** `sria/domain_pack.py::DomainPack` requires `model_references()`,
`parameter_semantics()`, `qois()`, `scope()`, `assumptions()`, `fidelity_ladder()`.
Every one already exists, typed, in `scientific/models/definition.py` and
`design/fidelity.py` — and `DomainPack` restates them as strings and `Any`. SRIA does
not consume `ScientificProblem`, `ModelRealizationDefinition` or `ScientificCapability`
at all; it imports `ScientificResult`, `Uncertainty`, `ValidationOutcome` and
`serialization`.
**INFERENCE.** Two descriptions of "what a domain is" now exist. Reconciling them is
cheap today and gets more expensive with every SRIA milestone.

### 4.10 Three fidelity concepts
**FACT.** `RealizationFidelity` was removed from the core with an excellent argument
(four conflated axes). But `design/fidelity.py::FidelityLadder` and
`sria/domain_pack.py::FidelityLevel` both exist, with rank-ordered rungs, in two
packages. The concept the core refused is implemented twice elsewhere.

### 4.11 Provenance bloat
**FACT.** `solve_circuit` writes `circuit.canonical_dict()` into
`ProvenanceRecord.metadata` on every solve: 162 kB for 10 coupling iterations, 790 kB
for 50 (recorded, `ET-VERTICAL` known unknown 3). `O(iterations × topology)` in bytes,
in the *control* plane the data boundary exists to keep small.

### 4.12 Grid inference will not scale
**FACT.** `inference/grid.py` builds a dense posterior grid (E2 uses 401 points for one
parameter). **INFERENCE.** Fine for 1–2 parameters, unusable at 5+. Every UQ and
adequacy result in the repository rests on it, so "we have quantified uncertainty" is
currently a claim about one-parameter problems.

### 4.13 CI does not gate the current work
**FACT.** `sria-tests.yml` triggers on `push: sria/**, main` and on PRs touching `src/`
or `tests/`. The last five milestone branches match neither push pattern, and only
three branches exist on the remote. The 1825-test gate is a **local** ritual.

### 4.14 Naming and packaging drift
**FACT.** `pyproject.toml` still declares `name = "engineering-ai-core"`,
`description = "Smart experiment engine proof of concept"`. The root holds 14
`README-V0.x.y.md` files describing the optimizer research line. The repo is on GitHub
as `sharq-labs/crafty`.

---

# 5. Cross-domain: which abstractions actually survive

The audit question — *are these concepts universal, or do they merely share a name?* —
answered from this tree's four domains plus the coupled system and the external
provider.

| Concept | Status here | Evidence |
|---|---|---|
| **Quantity / unit** | **GENUINELY UNIVERSAL** | Survives DC, conduction, kinetics, aerodynamics, ngspice and the coupling loop unchanged. Scalar magnitude was attacked by a field consumer and **needed no change**, because bulk data went to the data plane. |
| **Model identity + validity** | **GENUINELY UNIVERSAL** | Four domains, plus the `R(T)` constitutive claim, plus the two-realization proof. `UNKNOWN ≠ valid` held throughout. |
| **Realization identity** | **UNIVERSAL AS IDENTITY, ABSENT AS SELECTION** | Two schemes and two solvers were distinguishable; every typed *property* of the CD/UW pair is identical, so a planner has nothing to choose on. |
| **Solver identity / protocol** | **UNIVERSAL, BUT UNDER-DETERMINED** | Four solvers satisfy it; none can prepare from the problem alone (§4.1). |
| **Provenance / ExecutionBinding** | **GENUINELY UNIVERSAL** | Recovered the realization identity from serialized records in the hostile probe. |
| **Validation report** | **UNIVERSAL, ASYMMETRIC** | Works across all four domains; cannot record admissibility attainment. |
| **Data reference** | **UNIVERSAL FOR BULK IDENTITY** | Storage relocation left the reference byte-identical under a field consumer. |
| **State** | **NAME ONLY** | `VariableRole.STATE` and `TwinDatumRole.STATE` are two vocabularies with **no mapping** (recorded twice as a known unknown). No dynamic-state record exists. |
| **Boundary** | **NAME ONLY** | `BoundaryCondition` has **zero producers in `src/`**; its only user is a probe under `experiments/`. Boundary *identity* and orientation are absent, and the `(kind, region, value)` triple was measured **non-injective**: reversing the flow direction left every serialized boundary record byte-identical. |
| **Constraint** | **NAME COLLISION — DANGEROUS** | `ConstraintDefinition` is `metric OP bound`, a study acceptance test. It is **not** an algebraic relation among unknowns — which is what a DAE, contact, incompressibility or stoichiometric closure needs. |
| **Material** | **NOT A CONCEPT** | One constitutive model. No identity, no state, no composition. |
| **Component** | **PACK-LOCAL** | `CoupledStage` names an electro-thermal stage. Nothing universal. |
| **Port / Connector** | **ABSENT** | `QuantityDependency` is explicitly one-way and causal; its docstring says an acausal potential/flow connector is *"a different and much larger contract"*. |
| **Equation / residual** | **ABSENT ENTIRELY** | No equation, operator, residual or Jacobian representation anywhere. Physics exists only as Python inside domain packs. |
| **Discretization** | **ABSENT** | `n_cells` is a metadata string; the mesh appears only as a count. |
| **Coupling** | **PACK-LOCAL, SCALAR-ONLY** | `Mapping[str, Quantity]` plus a float max-norm presupposes one scalar per name (recorded as known unknown 9). |

**INFERENCE — the answer this repository can actually support today:**

> Only five concepts have survived contact with materially different consumers:
> **quantity/unit, model identity + validity, realization identity, solver identity,
> and provenance binding.** Everything on Crafty's candidate list concerning *where* a
> quantity lives (field, support, topology, boundary identity), *how many components it
> has* (rank), *what relates unknowns to each other* (equation, algebraic constraint),
> and *what a system is made of* (component, port, connector) is either absent or shares
> a name with something else.

**FACT.** The already-preregistered `CROSS-DOMAIN-COVERAGE` milestone is designed
precisely to test this with four consumers (plane-stress patch, 2D rotating
advection–diffusion, three-species batch, Cartesian pendulum) plus a two-domain control
group of existing packs. It is **preregistered and not yet executed** — no probe source
exists on this branch. Its predicted matrix already anticipates most of the table
above.

---

# 6. Field / PDE architecture: real separations or conceptual?

| Separation | Real? | Evidence |
|---|---|---|
| scientific field identity ≠ field values | **REAL** | `ScientificDataReference` is O(1) and digest-addressed; a 161-value field never entered a control record (longest serialized sequence measured < 20). |
| field ≠ discrete representation | **NOT REPRESENTED** | There is no field record to separate from. |
| domain/support ≠ mesh | **NOT REPRESENTED** | `length` is a scalar parameter stating an extent, not a support. |
| equations ≠ discretization | **NOT REPRESENTED** | No equation representation exists at all. |
| discretization ≠ solver | **PARTIAL** | Two realizations of one model, run by one solver, distinguished in provenance — real. But the discretization is untyped and realization applicability sits off-record. |
| boundary identity ≠ boundary condition | **NOT REPRESENTED** | Measured: byte-identical `BoundaryCondition` records describe two physically different systems. |
| storage ≠ semantics | **REAL** | Relocation between in-memory and filesystem stores changes nothing scientific; the resolver verifies length then digest and refuses substitutes. |

**INFERENCE.** The one separation Crafty has genuinely achieved in the field area is
the *data-plane* one. Every *semantic* field separation is still a plan. That is
defensible for the current evidence level — but it means "Real Fluid/PDE Domain" is not
one milestone away; it is one **representation foundation** away.

---

# 7. Multiphysics: exactly how it works

**FACT.** Mechanism, from `systems/electrothermal/coupled.py`:

- **Partitioned**, not monolithic. No global residual, no coupled Jacobian.
- **Gauss–Seidel (Picard) fixed-point** over a **torn dependency cycle**.
- **Declared graph**: `QuantityDependency` records; transported values are looked up as
  `result_of(source_problem).values[source_quantity]` — no metric name is constructed
  or parsed inside the loop.
- **Tears are declared** (`TornEndpoint` with a seed), **order is computed** (Kahn with
  sorted tie-break), **the cyclic core is computed** by peeling (after an earlier wrong
  implementation was found and fixed).
- **Convergence** = largest change of any torn iterate in one ratio-scale unit fixed by
  the plan — explicitly **not** derived from any participant's own convergence
  (measured: every sub-solve reported success in all 50 non-converging iterations).
- **Refusals**: fan-in (no combination rule), mixed-dimension tears (no normalization),
  affine comparison units (a difference in `degC` is not a difference).
- **Absent**: relaxation, acceleration, rollback, checkpointing, time synchronization,
  events, transfer/interpolation operators, conservation accounting, participant
  registry, concurrency.

**Does adding a new coupling require editing central infrastructure?**
**FACT: no core edit is required** — `src/engcore/scientific/` was byte-unchanged
across `MIN-FOUNDATION-ET`, `ET-VERTICAL`, `HETERO-NGSPICE` and `HOSTILE-CORE-STRESS`,
asserted by tests that run `git diff`.
**INFERENCE: but a new coupling requires a new system pack that re-implements the
executor table, and the *plan record itself* must change shape** for any of: two edges
into one endpoint, tears of differing dimension, a field endpoint, a transient or
time-windowed exchange, or a stateful participant. The loop is domain-neutral; the
**coupling contract is not yet general**.

**Could it support domains the authors did not anticipate?**
Yes for participants that are scalar-endpoint, memoryless, single-cycle and solved to
completion each pass — verified across a heterogeneous provider swap. No for transient
co-simulation, conservative interface transport, field coupling, stateful providers,
2:1 fan-in, or event-driven and hybrid systems. All measured or recorded, none
speculative.

---

# 8. Scientific reasoning / planning

**FACT.** SRIA is real reasoning, not configuration and not dependency injection:

- A **terminal decision** is required before value of information means anything
  (`charter.py`); `OPEN_RESEARCH` campaigns are reserved rather than faked.
- **Posterior is derived state**; nothing may write belief directly (`gateway.py`:
  single-mint capability token, registered admission authorities, logged rejections).
- **Six action-family generators** propose and explicitly cannot score; one utility
  engine scores everything; there is deliberately **no mode controller**, because a
  mode would make the mode the decision.
- Cost is **converted through a declared exchange rate**, never subtracted raw; a
  missing component makes a candidate `NOT_SCORABLE` rather than defaulting.
- **Stopping requires two independent conditions**: no affordable action has positive
  net value **and** the terminal decision lies inside justified support — otherwise
  `STOP_NOT_CERTIFIABLE / UNSUPPORTED_TRANSPORT`. This is genuinely novel relative to
  everything in studies 01–07, none of which reason about when to stop computing.
- Campaign execution is resumable through an effect ledger, so no simulation executes
  twice.

**FACT.** What SRIA does **not** do: it never reads `ScientificProblem`,
`ScientificCapability`, `ModelRealizationDefinition` or `SolverRegistry`. It plans
**which experiment to buy**, over a domain pack's declared action space.

**INFERENCE — the important finding for Crafty's differentiator:**

> The pipeline *problem → capabilities → models → realizations → solvers → coupling
> plan* has **no implementation and no partial implementation**. What exists is the
> record vocabulary it would read. The blocking obstacle is not planner code — it is
> **representation**: (a) realizations expose no typed property to select on, (b) the
> problem record does not contain the problem (§4.1), and (c) there is no equation
> representation to bind a realization to. A planner written today would select on
> `name` and `description` strings.

`admissible_realizations` in `thermal_conduction1d_schemes.py` is the only
selection-shaped function in the tree, and it deliberately refuses to select — the right
call, and also a demonstration that the records do not yet support the decision.

---

# 9. What the current plan may be missing

Nine items, with reversal cost and timing.

### 9.1 There is no equation / residual representation, and it is not on any list
**FACT.** No equation, operator, residual, Jacobian or weak-form object exists
anywhere. **FACT.** The `CROSS-DOMAIN-COVERAGE` predicted matrix has 27 rows and
**none is an equation or residual row** — the closest are "Constraint — algebraic
relation among unknowns" and "Differential/algebraic variable partition", which are
about *variables*, not about the relations themselves.
**Why current concepts are insufficient:** without one, (i) a realization has nothing
to *be* other than a Python function, so "choose a computational realization" reduces to
choosing an implementation id; (ii) monolithic coupling is permanently out of reach;
(iii) no solver-neutral assembly path can exist, so every domain keeps shipping its own
artifact plus its own solver — precisely the outcome the master context wants to avoid.
**Reversal cost:** very high; every domain written before it exists needs retrofitting.
**Timing: investigate NOW — as one added row in the coverage matrix, not as a
milestone.** All four preregistered consumers already have equations (a stiffness
matrix, a divergence-form operator, a stoichiometric matrix, an index-3 DAE). Asking
"what would a records-only reader need to reconstruct the equation?" costs almost
nothing during a run that is already building those four, and cannot be asked later
without rebuilding them.

### 9.2 The problem record does not contain the problem
See §4.1. **Reversal cost:** high — it changes the solver protocol.
**Timing: NOW**, at least as a measured row ("can a records-only reader reconstruct
enough to solve?"). It is the precondition for every planning claim in the master
context.

### 9.3 No time semantics
**FACT.** `BoundaryCondition` has no `time` field though `InitialCondition` does; a data
reference has no time level; the coupling iterate is explicitly not a time level;
nothing represents a schedule or a window.
**Timing: LATER**, but Consumer D's CASE D2 (`τ(t) = τ₀ sin Ωt`) already touches it —
**add a row** so the measurement is recorded rather than merely noticed.

### 9.4 No transport-admissibility rule
**FACT.** The measured 18.05 K failure mode (§4.4). A one-line universal rule — *a
coupling may not transport a value from a result whose validation status is `FAIL`* —
closes it, needs no new record, and is testable.
**Reversal cost:** low now, higher once several packs carry their own guards.
**Timing: NOW.** The cheapest real correctness win available.

### 9.5 Instance / system identity is unresolved
**FACT.** `ScientificTwin` has been produced for four milestones and has never held the
role it was designed for, while system structure lives in pack-local records.
**RECOMMENDATION:** force the decision at the end of the coverage stress — either the
twin becomes instance authority, or it is retired to `TwinKind.CANDIDATE` use in
`design/` and the name stops implying more. A contract carried four milestones without
evidence is a liability in a repository whose whole method is evidence-gating.

### 9.6 Provider session/state lifetime
See §4.7. **Timing: LATER**, but name it as the entry condition for the *second*
external provider — ngspice's statelessness is the only reason the current design
survived the first.

### 9.7 Two domain vocabularies (SRIA vs core)
See §4.9. **Reversal cost:** moderate and rising. **Timing: NOW-ish** — a one-page
mapping document, not code.

### 9.8 Schema evolution has no migration path
**FACT.** `require_schema` is exact-match; `data_reference.py` records the consequence
itself. **Timing: LATER**, but the decision *how* a field record is introduced (new
version vs sibling record) should be taken with this constraint explicit.

### 9.9 Nothing is concurrent, distributed, or at scale
**FACT.** Single process, synchronous, in-memory. `ET-VERTICAL` known unknown 13 says it
plainly. **Timing: NOT NOW** — the correct call. But it belongs in any external-facing
claim, because "simulation operating system" implies otherwise.

---

# 10. Negative evidence — where Crafty's current assumptions look wrong

### 10.1 Separations that may not be earning their keep
- `ScientificCapability` vs `SolverCapability`: intellectually right, **zero
  consumers**. The many-to-many relation it preserves has never been traversed. Cheap
  to keep; should not be cited as proven.
- `ScientificTwin`: four milestones, zero evidence for its motivating role.
- `ModelFormulation.DAE` / `.DISCRETE`: zero production consumers, already flagged
  provisional. Consumer D will resolve `DAE`; `DISCRETE` still has nothing.

### 10.2 A separation that was *not* made and probably should have been
**`ScientificVariable` conflates a search variable with a physical unknown.** The same
type carries `VariableRole.DESIGN` (consumed by `CandidateCodec`, normalized to a unit
hypercube by an optimizer) and `VariableRole.STATE` (a PDE field, a DAE state).
**INFERENCE:** this is *why* rank, support, component index and the
differential/algebraic partition have nowhere to live — adding them to
`ScientificVariable` would put field semantics inside the optimizer's codec input. The
repository has been reading this as "fields are missing"; it is at least as much "one
type is doing two unrelated jobs". This is a concrete, testable hypothesis the coverage
stress can settle for free: Consumer A has a rank-1 unknown, Consumer D a mixed
differential/algebraic state, and `design/` supplies the design-variable witness.

### 10.3 Naming that will cause damage
`ConstraintDefinition` means *acceptance test*. Structural mechanics, DAEs, contact,
incompressibility and stoichiometric closure all mean *relation among unknowns*. Two
different things share the most obvious name, in a core meant to be extended by domain
authors who read the name before the docstring.

### 10.4 An assumption that already failed once, quietly
"A validation report protects downstream consumers." It does not: the coupling loop
reads values, not reports. Found by measurement; the fix was local. The general lesson —
**a check whose only effect is a field nothing consults is not a guard** — appears twice
in the repository's own evidence and has not yet become a core rule.

### 10.5 Elegance that will hurt in production
- `RawSolverOutput.diagnostics: Mapping[str, Any]` is the default array channel;
  `capture_bulk` lifts arrays out **only if the caller remembers to call it**.
- `PreparedSolve.payload: Any` — deliberate, and also the hole through which domain
  artifacts, meshes and sessions will arrive untyped.
- Frozen dataclasses with `object.__setattr__` normalization everywhere are elegant and
  make every record construction allocate and validate. **Measured:** a 4000-variable
  problem constructs in ~1 ms; 2000 objectives in ~22 ms (quadratic in the duplicate
  scan). **Not a current problem** — worth knowing before anything builds problems with
  10⁴+ named entities.

### 10.6 Where the repository's own claims read stronger than they are
- "Four scientific domains" is really: one 154-line MNA solve, one 1-D linear diffusion,
  one two-state stiff ODE, and two aerodynamic formulas.
- "Cross-solver validation" is one provider on one problem class.
- "Quantified uncertainty" is a dense grid over one parameter.
- These are *appropriate* for the evidence levels claimed in the evidence documents.
  They are not appropriate for the language in the master context and the READMEs,
  which an investor or buyer reads first.

---

# 11. License / IP assessment

**FACT.** There is **no LICENSE file**. Default: all rights reserved. No copyright
headers, no `NOTICE`, no `CONTRIBUTING`, no IP-provenance statement.

**Dependencies** (`pyproject.toml`): `numpy`, `scipy`, `scikit-learn`, `pint` — all
BSD-family; dev-only `pytest`, `pytest-xdist` (MIT). **INFERENCE:** no copyleft exposure
through Python dependencies. The GPU path in the legacy stack (`torch`) is BSD-3, also
clean.

**External provider.** ngspice is reached as a **separate process** (`subprocess`,
netlist on stdin, `-b`), never linked, and its identity never enters a scientific
record. **INFERENCE:** this is the licensing-safe integration pattern regardless of how
ngspice's mixed licensing is read, and it should be stated as *policy* rather than left
as one adapter's behaviour.

**Studies 01–07** record reading MOOSE (LGPL), OpenFOAM (GPL), PETSc (BSD-2), FEniCSx
(LGPL), MFEM (BSD-3), preCICE (LGPL), OpenMDAO (Apache-2) and Modelica tooling. The
stated policy — read source, understand pattern, write Crafty design, implement
independently — is correct and visibly followed: nothing in `scientific/` resembles any
of those codebases structurally.

**RECOMMENDATIONS**
1. Add a `LICENSE` (proprietary/all-rights-reserved is fine) and a short `NOTICE`
   listing third-party dependencies and licenses. Diligence asks on day one, and its
   absence is a cheap thing to fix badly late.
2. Add one paragraph of **IP provenance**: architecture studies are read-only, no
   third-party source was copied, AI assistance was used under review. The
   prereg/evidence trail is unusually strong support for an independent-creation claim —
   it would be a shame not to state it.
3. Keep process separation for external providers as **written policy** in
   `docs/scientific-core/README.md`.
4. Decide before the first pilot whether domain packs and core carry the same licence.
   The core / domain pack / system pack split is already shaped for open-core; choose
   deliberately rather than inherit.

---

# 12. Scores

Scored as *"how much does this repository advance Crafty's stated goal, today"*.

| Dimension | Score | Note |
|---|---|---|
| Architecture relevance | **92** | It is the architecture. Boundaries are real and enforced by tests. |
| Scientific-domain relevance | **45** | Four narrow domains; nothing mechanical, no fields, no species, no EM/acoustics. |
| Cross-domain learning value | **55** | Two genuinely different families plus a PDE probe; the four-family stress is designed but unexecuted. |
| Multiphysics learning value | **70** | One real closed loop with honest measured limits; no transient, field or conservative coupling. |
| Solver / runtime learning value | **60** | Solver contract and provider substitution are real; no runtime, scheduling, sessions or concurrency. |
| Scientific reasoning / planning value | **55** | SRIA is excellent at experiment-level reasoning and does not touch model/solver planning. |
| Potential as external dependency/provider | **n/a (own IP)** | If ever split out, the reusable parts are the data boundary and the record vocabulary. |
| Risk of importing wrong assumptions | **60** (higher is worse) | Scalar-only endpoints, non-executable IR, metadata leakage and the acceptance-vs-algebraic constraint collision are each one careless generalization from permanence. |
| **Overall strategic value** | **80** | The method and the record architecture are strong assets; scientific coverage and the planning layer are the weak halves, and both are known. |

---

# 13. Roadmap impact

**Verdict: KEEP ROADMAP — with three additions inside step 1 and one insertion before
step 2.** Nothing in this audit justifies reordering.

```text
1. Cross-Domain Coverage Stress   KEEP — already preregistered (a3db20d), well designed.
                                  ADD three rows before executing (below).
2. Minimum Universal Foundation   KEEP — but its scope must include realization
                                  SELECTION semantics, or step 5 slips again.
   ↳ INSERT: transport admissibility (≈1 day, closes a measured failure)
3. Real Fluid/PDE Domain          KEEP — decide the entry-condition question NOW,
                                  not after step 1 (promote Consumer B, or new consumer?).
4. Fluid ↔ Thermal Proof          KEEP — expect the coupling contract to change shape
                                  here (fan-in, field endpoints, time windows).
5. Scientific planning/reasoning  KEEP — blocked on representation, not on planner code.
6. API / MCP / product surface    KEEP LAST, but timebox: it has now been deferred twice.
```

**Three rows to add to the coverage matrix before writing probe source** (cheap *now*,
impossible afterwards without re-running the consumers):

1. **Equation / residual representation** — can a records-only reader recover *what
   relation is claimed*, for a stiffness matrix, a divergence-form operator, a
   stoichiometric matrix and an index-3 DAE? §9.1.
2. **Executable problem specification** — can a records-only reader reconstruct enough
   to *solve*, or does each consumer need an out-of-band artifact as `bind_circuit` and
   the slab do today? §4.1 / §9.2.
3. **Time level / time-varying input** — Consumer D's CASE D2 already probes it and
   there is no row to record the result. §9.3.

**One free hypothesis to test while the instrument runs:** whether the missing
field/rank/DAE semantics are a *field* gap or a **`ScientificVariable` overload** gap
(§10.2). Consumer A + Consumer D + the existing `design/` stack are exactly the three
witnesses needed, and no new consumer is required.

**RECOMMENDATION on evidence honesty:** the preregistration's fail condition 5 ("if the
matrix returns *everything is universal*, the instrument cannot discriminate and the
milestone has FAILED") is the right guard. Three added rows predicted **F** everywhere
weaken it slightly — so state predicted negatives for the new rows too, or they will
read as confirmation.

---

# 14. Deltas

## WHAT CRAFTY ALREADY HAS RIGHT

1. **The method.** Preregistration before implementation, evidence documents that record
   refuted predictions as deviations, an adversarial falsifier and a neutral decision
   reviewer as read-only subagents, and a two-ledger rule refusing to book a finding as
   new evidence when the missing concept was already recorded as deferred.
2. **Refusal over invention.** Fan-in, mixed-dimension tolerances, affine comparison
   units, best-effort data resolution and field endpoints in dependencies are all
   *refused* rather than guessed. Every one of those guesses would have become
   permanent.
3. **Identity ≠ location** for bulk data, proven under relocation and substitution.
4. **Model ≠ realization ≠ solver**, proven differentially in both directions (two
   schemes / one solver; one model / two solvers).
5. **Capability identity as an open grammar**, with a real cross-domain match
   (`thermal:body_temperature` provided by thermal, required by electrical, with no code
   dependency).
6. **A coupling loop with no domain branch in it**, driven by declared records, with
   coupling convergence explicitly separated from participant convergence.
7. **Provenance and validation semantics** most commercial CAE lacks: `NOT_RUN ≠ PASS`,
   empty validity ≠ unlimited validity, uncertainty that may answer `UNKNOWN`.
8. **A real external provider**, substituted inside the same coupled simulation, with
   provider identity kept out of every scientific record.

## WHAT THIS REPOSITORY DOES BETTER (than its own plan)

- Its **evidence discipline is ahead of its architecture**. The measured findings in
  `HOSTILE-CORE-STRESS` are more useful than most of §24's target boxes.
- Its **refusals are better documented than most systems' features**. The removal of
  `RealizationFidelity`, with the four-conflated-axes argument, is better design writing
  than the fidelity systems in the projects studied in 01–07.
- **SRIA's stopping rule** (decision-theoretic condition **and** support condition) is a
  genuinely novel contribution relative to everything in those studies.

## WHAT CRAFTY IS CURRENTLY MISSING

1. **Any equation / residual representation.** Not deferred — *unnamed*. (§9.1)
2. **An executable problem specification.** The IR describes; the artifact executes.
   (§4.1)
3. **Field, support, topology, boundary identity, rank.** Known, measured, deferred.
4. **A typed property by which a realization can be selected.** Blocks the planner.
5. **A universal transport-admissibility rule** at the coupling boundary. (§9.4)
6. **Admissibility attainment** on the validation ladder. (§4.5)
7. **Algebraic relations among unknowns**, distinct from acceptance constraints.
8. **Time semantics**: time-varying inputs, time levels on data, coupling windows.
9. **Provider session/state lifetime.**
10. **One vocabulary for "what a domain is"** (SRIA `DomainPack` vs core records).

## WHAT WE SHOULD LEARN BUT NOT COPY

- **The fixed-point loop's shape.** Learn: records drive execution, execution knows no
  domain. Do not copy: single-cycle, scalar-endpoint, memoryless-participant assumptions
  into a universal coupling contract.
- **The ngspice admission gate.** Learn: reconcile a provider's channels against a
  quantity Crafty declared, before the value becomes science. Do not copy: putting the
  guard in each adapter.
- **The material-property pattern.** Learn: a property is a model + a realization, not a
  parallel hierarchy. Do not copy the conclusion to rank-2/anisotropic properties
  without evidence — that case is untested.
- **`metadata` fingerprints.** Learn: proving a record and an artifact describe the same
  system is necessary. Do not copy: doing it with an untyped key in a free dict.

## WHAT WE SHOULD REJECT

1. **`bind_circuit`-style out-of-band artifact binding as a permanent pattern.**
   Acceptable as a bridge; must not become the extension mechanism.
2. **Science in `metadata`** — boundary and initial conditions as prose strings.
3. **Per-adapter safety invariants** — anything every new participant must re-implement
   from memory.
4. **A second fidelity ladder.** Three exist already (`design`, `sria`, and the one the
   core correctly refused); do not add a fourth.
5. **`ConstraintDefinition` as the name for physical constraints.** Rename or namespace
   before a domain author binds a DAE to it.
6. **Growing the SRIA vocabulary further before reconciling it with the core's.**

## WHAT SHOULD CHANGE IN OUR NEXT 3 MILESTONES

**Milestone 1 — `CROSS-DOMAIN-COVERAGE` (in flight, unexecuted).**
Amend the instrument *before* writing probe source; since the preregistration is
immutable, the amendment is its own recorded deviation:
- add rows for **equation/residual recoverability**, **executable problem
  specification**, and **time level / time-varying input**;
- state predicted negatives for the three new rows so fail condition 5 stays sharp;
- record the **`ScientificVariable` overload hypothesis** (§10.2) as an explicit
  question A + D can answer.

**Milestone 2 — the minimum universal foundation.**
- Scope it by what the matrix *forces*, as planned — but require that whatever is built
  makes a realization **selectable**, not merely identifiable, or the planning milestone
  is blocked a third time.
- Fold in the **transport-admissibility rule** (a coupling may not transport a value
  from a `FAIL`ed result) as a one-day sub-item with its own test. It is the only
  correctness defect this audit found that has already been *measured* to produce a
  wrong scientific answer.
- Decide the `ScientificTwin` question: instance authority, or retire the ambition.

**Milestone 3 — the real fluid/PDE domain.**
- Settle **now** whether Consumer B is promoted or a fresh consumer is written; the
  preregistration flags this as an open founder decision and it will otherwise be
  settled by convenience after the fact.
- Treat "solver session/state lifetime" as its entry condition if any external provider
  is involved.

---

# FINAL VERDICT

**1. Is this repository strategically important to Crafty? — YES.** It *is* Crafty. The
question that matters is the second one: is what it contains the right half? The answer
is **the record architecture and the method are right; the scientific coverage and the
planning layer are the missing half, and both are correctly identified in the
repository's own documents.**

**2. Strategic relevance score: 80 / 100.**
Deductions: no equation representation and no path to one (−8); the IR is not executable
(−6); roughly a third of the universal surface has no production consumer (−3);
scientific coverage is four narrow domains (−3).

**3. The five most valuable concepts to study (and generalize)**
1. Preregistration → evidence → falsifier, with two-ledger evidence booking.
2. Identity ≠ location — content-addressed bulk data with an honest digest contract.
3. Model ≠ realization ≠ solver, held together by `ExecutionBinding`.
4. Refusal over invention — refusing fan-in, mixed dimensions and affine deltas rather
   than inventing a rule from one consumer.
5. SRIA's two-condition stopping rule (decision value **and** support), and its single
   write path to belief.

**4. The five most dangerous concepts to copy blindly**
1. `bind_circuit`-style out-of-band artifact binding — it makes the IR decorative.
2. `metadata` as the home for science with no typed home.
3. Scalar-endpoint coupling (`Mapping[str, Quantity]` + float max-norm) as *the*
   coupling signature.
4. `ConstraintDefinition` as the universal name for "constraint".
5. Per-adapter safety guards — the admission gate is correct science in the wrong place.

**5. Should the next milestone change?**
**No — but its instrument should.** `CROSS-DOMAIN-COVERAGE` is the right next milestone,
is already preregistered, and its four consumers are well chosen (the isomorphism checks
against `electrical/dc` and `thermal_lumped` are exactly the right defence). Add the
three rows in §13 before writing probe source. The only sequence change worth making is
small: fold the transport-admissibility rule into milestone 2 rather than leaving it to
be rediscovered by the next provider.

**6. The single most important lesson**

The repository has proved, with executed evidence, that Crafty can add domains, a
coupled loop and a foreign solver without editing universal core — and in the same
breath it has measured *why* that success does not yet generalize: the universal records
describe computations they cannot specify. Every solver in the tree needs a domain-native
artifact handed to it out of band, every discretization fact lives in a metadata string
or a module-level dict, and no record anywhere states the relation a model claims to
hold. The consequence is precise, and it is the whole of Crafty's current risk: **a
planner cannot select what the records do not describe, and a coupling cannot transport
what the records cannot represent.** The next foundation should therefore be judged by
one question rather than by how universal it looks — *can a reader holding only the
records reconstruct enough to choose and to run?* Today the answer is no, and every
layer above the records is waiting on it.
