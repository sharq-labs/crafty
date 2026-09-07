# Architecture Study 09 — Physics Runtime · Trust Layer · AI Interface

**Purpose:** audit the repository against the stated strategic target
**Physics Runtime + Trust Layer + AI Interface**, and answer four questions:
is the architecture suitable, what must change before AI scales on it, what must
never change, and what the next milestone is.

**Repository:** `D:\PhysicsX core`, branch `trust-hardening`, HEAD `c5c7c70`
(*Preregister the admission gate repair*), 354 commits, **75 ahead of `origin/main`,
0 behind**. Every measurement below was taken against `c5c7c70` plus the then-uncommitted
`ADMISSION-GATE-REPAIR` working-tree edit.
**Study date:** 2026-09-05.

> **Provenance note, added after the measurements.** While this audit was being
> written, that edit was committed as `53f9f02` (*Wire the admission gate
> TRUST-HARDENING preregistered and did not ship*), together with
> `docs/evidence/admission-gate-repair-evidence.md`, `tests/test_admission_gate_repair.py`
> and three guard repairs. Re-verified at `53f9f02`: the three
> `require_admission` call sites in `systems/electrothermal/coupled.py` are now
> committed, and `src/engcore/coupling/` still contains **zero** admission or
> validation references. **Finding C2 is therefore unchanged in substance** — its
> §3.2 half (the gate was published and absent) is now a closed defect with its own
> evidence document; its §3.3 half (enforcement is a per-producer convention that
> the transporting layer does not enforce) stands at `53f9f02`. Line numbers cited
> below are `c5c7c70` line numbers.
**Mode:** read-only. **No source file was added or edited. This document freezes
nothing, authorizes no architecture, and moves no evidence holding.**

Labels: **FACT** (measured in this tree, this session), **INFERENCE** (drawn from
structure), **RECOMMENDATION**.

> Study 08 audited this tree at `a3db20d` (2026-09-03). Thirty commits have
> landed since — `CROSS-DOMAIN-COVERAGE`, `API-MCP-V0`, `COUPLING-PACK-RELOCATION`,
> `MIN-FIELD-SUPPORT`, the real fluid PDE domain, `FT-SCALAR-COUPLING`,
> `COMPOSITE-SYSTEM0`, `PROPULSION0`, `PROPULSION0-EXT`, `TRUST-HARDENING`.
> This study re-measures rather than restates. Where 08's finding still holds it
> is marked **[08 open]**; where the tree has moved it is re-measured; where a
> finding has been *reproduced into new code* it is escalated.

---

# Phase 1 — Repository reality

## 1.1 What was measured

**FACT.** Python 3.14.2, numpy 2.4.3, scipy 1.18.0, pint 0.25.3, Windows.

| Measurement | Result |
|---|---|
| Python modules under `src/` | **279** |
| Source lines under `src/` | **84,871** |
| Test lines under `tests/` | **61,598** (97 test files) |
| Documentation lines under `docs/` | **41,543** |
| Preregistration / evidence / freeze documents | **35 / 22 / 9** |
| FAST tier (`-m "not expensive"`) | **1951 passed, 3 failed**, 47.5 s |
| SCIENTIFIC tier (`-m "not campaign"`) | **2571 passed, 5 failed, 1 skipped**, 336 s |
| LICENSE / NOTICE / CONTRIBUTING | **all absent** |
| `pyproject.toml` project name | `engineering-ai-core`, *"Smart experiment engine proof of concept"* |
| `README-V0.x.y.md` files at repository root | **17** |

The three FAST failures are exactly the three declared in
`docs/evidence/trust-hardening-preregistration.md` §1.4 as environmental
(`test_t6f` untracked-files guard; a Windows `\` vs `/` path assertion; a
`git show` cp1252 decode). The suite is otherwise green. **Two further failures
appear only in the SCIENTIFIC tier** — see §1.5.

## 1.2 Reachability: what is actually the product

**FACT.** An AST import graph over all 279 modules, walked from the two external
transports (`crafty_http.server`, `crafty_mcp.server`):

| Set | Modules | Source lines |
|---|---|---|
| Reachable from the external API | **59** (21%) | **19,478** |
| Reachable from tests but not the API | 139 | — |
| Reached by **nothing** — no API, no test, no experiment, no benchmark | **78** | **18,309** (21.6%) |

The 59 reachable modules are: `application/*`, `coupling/*`, `scientific/*`
(most of it), `domains/electrical/*`, `domains/thermal_lumped`,
`systems/electrothermal/*`. **That is the whole shipped product.**

The 78 unreached modules are the Bayesian-optimization research heritage in
`src/engcore/*.py` (`stacked_*`, `adaptive_*`, `logei_*`, `hybrid_*`, `robust_*`,
`gpu_*`, `coco_*`, `v034_*`, `validation/*`, `standard_*`, `statistical_*`).

## 1.3 The three-way split

**FACT.** Lines by subsystem:

```text
src/engcore/
├── *.py            16,997   Optimizer heritage. 18,309 lines unreached by anything.
├── sria/           19,863   Decision-theoretic campaign engine. ZERO importers in src/.
├── scientific/      8,203   The universal core. Reachable, exercised.
├── domains/        17,454   6 domain packs (electrical, thermal, kinetics, fluids,
│                            thermal_lumped, mechanical_rotational).
├── systems/        11,167   4 system packs (electrothermal, fluidthermal,
│                            propulsion, aerospace).
├── coupling/        1,154   Shared fixed-point coupling. 3 consumers.
├── application/     1,783   The external boundary.
├── design/          3,547   Design/discovery D0–D3. Not reachable externally.
├── validation/      2,230   Optimizer benchmarking arena. Unreached.
└── data/ uq/ inference/ adequacy/   ~2,000 combined. Not reachable externally.
src/crafty_http/       237
src/crafty_mcp/        240
```

**FACT.** `sria/` reaches the core almost entirely through one module:
`scientific.serialization` (39 import sites), plus `results.validation` (2),
`results.uncertainty` (4), `ir.values` (2), and one each of `units.quantity`,
`solvers.protocol`, `results.result`, `results.provenance`, `errors`.
**Nothing anywhere in `src/` imports `sria`.**

## 1.4 Production-ready / experimental / dead

**Production-ready** — executed on the reachable path, gated by tests, evidence
documents written and falsified:

* `scientific/` units, IR, models, realizations, results, provenance, validation,
  serialization, capabilities
* `coupling/` — plan, graph, scales, `run_fixed_point`
* `domains/electrical/{dc, material, conductor_material, ngspice}`,
  `domains/thermal_lumped`
* `systems/electrothermal/`
* `application/` + both transports

**Experimental** — real, tested, but not reachable by any consumer outside tests:

* `domains/{kinetics, fluids, thermal}`, `domains/mechanical_rotational`,
  `domains/thermal_conduction1d_*`
* `systems/{fluidthermal, propulsion, aerospace}`
* `data/`, `uq/`, `inference/`, `adequacy/`, `design/`
* `sria/` — 19,863 lines, the largest single subsystem, **architecturally orphaned**

**Dead / unreachable** — 78 modules, 18,309 lines: the entire optimizer research
line. It is not merely unused by the product; it is unused by the *tests*.

## 1.5 Two failures that are not in the declared baseline

**FACT.** `tests/test_min_field_support_foundation.py::test_g1_fresh_process_reconstructs_and_reports_no_issues`
fails unless `PYTHONPATH=src` is exported into the environment. It launches
`subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT, check=True)`
(line 557) with **no `env=`**. `pytest`'s `pythonpath = ["src", "."]` ini option
inserts into the *pytest process's* `sys.path`; it does not set the environment
variable a child process inherits. Measured: fails with `python -m pytest`;
passes with `PYTHONPATH=src python -m pytest`.

This is the headline evidence test for `MIN-FIELD-SUPPORT-FOUNDATION` — *"a fresh
process reconstructs from records alone"*. `.github/workflows/sria-tests.yml`
runs `python -m pytest tests/` and sets no `PYTHONPATH`, so **the claim's own
regression test would fail in CI**.

**FACT.** `tests/test_api_mcp_v0_transports.py` — two failures at module scope:
`test_nothing_a_request_can_say_launches_a_process_and_then_one_legitimately_does`
fails on its **positive control** (`assert marker.exists()` at line 706, after
every negative assertion passed). The sentinel that proves the instrument is live
never fired on this machine, so the reproduced-RCE guard is **unverified here** —
the test correctly declines to claim a guard works when it cannot prove the
detector was on. `test_both_transports_agree_that_a_size_fault_is_a_transport_fault`
**passes in isolation and fails in a module run** — order-dependent.

## 1.6 CI does not gate this work

**FACT.** `.github/workflows/logic-hardening-checks.yml` triggers on PRs touching
`src/engcore/**` and runs inline probes importing `src.engcore.adaptive_policy`,
`candidate_arbiter`, `landscape_diagnostics`, `validation.metrics`,
`validation.problem` — **five modules from the 78-module dead set**. It never
invokes pytest.

`.github/workflows/sria-tests.yml` is the real gate. It triggers on
`push: sria/**, main` and on PRs. The last ten milestone branches match neither
push pattern. **75 commits are unmerged to `origin/main`**, and the 2571-test
suite is a local ritual.

---

# Phase 2 — Physics Runtime architecture review

## 2.1 Mapped onto the project's own target layers

Study 07 §10 defines nine layers. Measured against this tree:

| Layer | Owns | Status |
|---|---|---|
| **A — Scientific Meaning** | units, problem, capability, model, validity, provenance | **IMPLEMENTED, STRONG** |
| **B — Computational Realization** | realization, formulation, required capabilities | **IDENTITY ONLY** — see §2.5 |
| **C — System Composition** | components, ports, connections | **ABSENT** — see §2.7 |
| **D — Representation / Discretization** | fields, topology, equation IR, operators | **ABSENT ENTIRELY** |
| **E — Numerical Runtime** | linear/nonlinear/time solvers, preconditioners | **ABSENT AS A LAYER** — see §2.6 |
| **F — Coupling Runtime** | participants, transfers, sync, relaxation, rollback | **PARTIAL** — see §2.8 |
| **G — Simulation Runtime** | plan compilation, scheduling, run lifecycle, run identity | **ABSENT** |
| **H — Scientific Governance** | adequacy, UQ, assurance, admission | **PARTIAL + ORPHANED** |
| **I — Discovery / Decision** | design variables, optimization, scientific memory | **PRESENT, UNREACHABLE** |

**INFERENCE.** Layers A and F are the load-bearing achievements. **D, E and G —
the three layers that make something a *runtime* — are absent, and D is not on
any milestone list.**

## 2.2 Domain separation — real, and enforced by tests

**FACT.** `src/engcore/scientific/` has been **byte-unchanged across eight
consecutive milestones** (last edit `0d99110`, before the real fluid PDE domain,
the fluid-thermal coupling, the coupling relocation, API/MCP, COMPOSITE-SYSTEM0,
PROPULSION0, PROPULSION0-EXT and TRUST-HARDENING). This is asserted, not merely
observed: `tests/test_api_mcp_v0.py:1162` runs `git diff --name-only 3f2e6dd -- src/`
inside a test, against that milestone's own preregistration commit rather than
against `HEAD`, so committing does not clear the guard.

**FACT.** Grep for domain vocabulary under `scientific/` returns docstring
matches only — zero code branches. The core imports no domain, no LLM, no
storage, no web, no optimizer.

**This is the strongest structural claim in the repository and it is true.**

## 2.3 …and why that fact is weaker evidence than it looks

**FACT.** Thirteen `bind_*` sites across ten modules hand the solver a
domain-native artifact **out of band**, keyed by `problem_id` in a per-instance
mutable dict:

```text
electrical/dc/solver.py:98         bind_circuit    "the universal IR carries no topology"
electrical/ngspice.py:542          bind_circuit
fluids/transport2d/solver.py:296   bind_domain     "the universal IR carries no geometry"
thermal/conduction1d/solver.py:162 bind_slab       "the universal IR carries no geometry"
kinetics/cstr/solver.py:287        bind_run        "the universal IR carries no chemistry"
electrical/material.py:496         bind_conductor
electrical/conductor_material.py:1339, :1586   bind_conductor
thermal_conduction1d_schemes.py:716            bind_reduced
thermal_lumped.py:634                          bind_body
systems/fluidthermal/properties.py:706, :883   bind_medium
systems/propulsion/models.py:874, :1040        bind_operands / bind_drive
```

**INFERENCE — the central architectural finding of this audit.**
The core does not need to change when a domain is added **because the core is not
on the critical path of the physics.** `ScientificProblem` describes; a
domain-native artifact executes. The zero-core-edit metric therefore measures
*decoupling*, not *extensibility of representation* — and the two are being read
as the same thing.

Study 08 §4.1 called this *"must not be carried forward."* It has been carried
forward: `fluids/transport2d`, the newest and most sophisticated domain, added
after that audit, reproduces the pattern verbatim.

## 2.4 Equation representation, and what the records actually carry

**FACT.** `domains/fluids/transport2d/problem.py:484-597` builds the IR for the
2-D rotational advection–diffusion benchmark. The `ScientificProblem` it returns
carries: five `ScientificVariable`s (name, unit, role, description), three scalar
`ScientificParameter`s, four Dirichlet `BoundaryCondition`s with `value = 0` on
opaque region labels, five `ModelReference`s, one required capability, five
validation-requirement *names* — and this `metadata`:

```python
"boundary_conditions": "c = c*(x,y) on all four sides",
"velocity_field":      "u = omega*(-(y-L/2), (x-L/2))",
"n_cells":             str(domain.grid.n_cells),
"field_unit":          FIELD_UNIT,
"domain_fingerprint":  domain.fingerprint(),
```

**The velocity field and the discretization are prose strings in a free
dictionary.** No equation, operator, residual, weak form, Jacobian or
discretization record exists anywhere in `src/`. A reader holding only the
records cannot state what relation is claimed, and `ScientificProblem.validity_context`
documents that it is *"deliberately not sourced from metadata"* — so a reader
obeying the platform's own rule gets `UNKNOWN` for facts the metadata answers.

## 2.5 Realizations are identifiable but not selectable

**FACT.** `ModelRealizationDefinition` (`realizations/definition.py:263-273`)
carries `realization_id, version, model, formulation, name, description,
provided_capabilities, required_capabilities, required_solver_capabilities,
assumptions, implementation`. **There is no applicability or validity field.**

**FACT.** `domains/thermal_conduction1d_schemes.py:243` holds
`_APPLICABILITY: dict[tuple[str, str], ValidityDomain]` — a module-level dict
keyed by realization identity, with the comment *"Looked up by realization
identity because the record cannot carry it."* It is built from `ValidityDomain`
and `RangeCondition`, types that already exist in the core and are simply not
reachable from a realization record.

**INFERENCE.** The headline claim *model validity ≠ realization adequacy* is
expressible only in a side table owned by one domain. A planner asked to choose
between backward and forward Euler has, on the record, **nothing to choose on**:
every typed property of the two is identical. **[08 open, unchanged.]**

## 2.6 Solver abstraction: universal, and under-determined

**FACT.** `ScientificSolver` (`solvers/protocol.py:250-285`) is a `Protocol`
with `identity`, `capabilities`, `supports`, `prepare`, `solve`, `validate`,
`extract_metrics`. `prepare(self, problem)` carries **no type annotation on
`problem`**; `PreparedSolve.problem: Any`, `PreparedSolve.payload: Any`.

**FACT.** No solver in the repository can satisfy `prepare(problem)` from the
problem alone (§2.3). Solvers are stateful — fingerprint-guarded, but per-instance
mutable — inside a protocol whose other members are pure.

**FACT.** The project has already measured this. `docs/executable-scientific-spec-evidence.md`
ran a records-only reader over four domains at four information levels, and
decided **no universal executable-specification record** (option E+F: per-domain
typed structure records + typed identity checks). Its §M records verbatim:

> **P-8 held: reconstruction does not remove the bind maps.** … Statelessness
> requires changing `ScientificSolver.prepare` — option **G** — which is a public
> protocol with four implementations… **G is a separate decision and is not taken
> here.**

**Option G is the open decision this audit converges on.** See the final section.

## 2.7 System composition is a naming convention

**FACT.** `systems/propulsion/drive.py:19-45` — one `Motor` record owns **eight
distinct problem identities** (`R:<id>`, `Vs:<id>-emf`, `conductor_resistivity:<id>`,
`conductor_resistance:<id>`, `conductor_thermal_mass:<id>`, `thermal-lumped-<id>`,
`drive_operating_point:<id>`, `machine_heat_generation:<id>`), each *derived from
`component_id` by a published accessor on that pack's record*. The module states
the finding itself: *"no universal record states the correspondence."*

**FACT.** No `Component`, `Port`, `Connector`, `SystemDefinition` or
`PhysicalEntityReference` record exists. `QuantityDependency` is explicitly
one-way and causal.

**INFERENCE.** PROPULSION0 is genuine — 14 problems, 20 edges, 3 torn endpoints,
one motor in three physics simultaneously, zero core edits. But *what a system
is* is currently a string-derivation convention inside one Python module. A
second pack that derives identities differently produces two incompatible
notions of "the same component", and nothing detects it.

## 2.8 Coupling: the one layer that generalized

**FACT.** `COUPLING-PACK-RELOCATION` moved the fixed-point machinery to
`engcore/coupling/` (1,154 lines), now imported by three system packs
(`electrothermal`, `fluidthermal`, `propulsion`) and by `application/contract.py`.
`run_fixed_point` contains no domain branch; order is computed (Kahn, sorted
tie-break); tears are declared; convergence is one scalar in one ratio-scale unit
fixed by the plan, never derived from a participant's own convergence.

**FACT.** Refusals rather than inventions, verified in `coupling/plan.py`:
fan-in *"refused rather than combined by invention"* (:197); mixed-dimension tears
*"Refused rather than normalized by invention"* (:222); seed dimension checked
against the edge (:97); affine comparison units refused by `scales.is_ratio_scale`.

**FACT, absent:** relaxation, acceleration, rollback, checkpointing, time
synchronization, events, transfer/interpolation operators, conservation
accounting, participant registry, concurrency. Endpoints are
`Mapping[str, Quantity]` — **one scalar per name**; a field endpoint is refused.

## 2.9 Materials, boundary and initial conditions, units

* **Units — GENUINELY UNIVERSAL.** `Quantity` refuses bare numbers, non-finite
  magnitudes and unparsable units; the registry is core-owned, not pint's mutable
  application registry (`units/quantity.py:41-52`). Dimensional coherence is
  enforced at problem construction. Survives six domains unchanged.
* **Boundary conditions — LOW.** `BoundaryCondition` exists and is typed;
  `region` is an opaque label the core does not interpret. `MIN-FIELD-SUPPORT`
  added `BoundaryOrientation` as a *standalone* record to make `(kind, region,
  value)` injective — and `classify_sign` correctly **refuses** when a single
  named region is half inflow and half outflow, rather than mislabelling half of
  it. That refusal is right and it also states the ceiling: no record here can
  describe a boundary at finer granularity than a whole named region.
* **Initial conditions — PARTIAL.** `InitialCondition` carries a `time`;
  `BoundaryCondition` does not. `MIN-FIELD-SUPPORT` added
  `ScientificProblem.data_references` for bulk input fields, with precedence
  between a scalar condition and a bulk reference documented in a **comment**
  (`ir/problem.py:145-163`) because *"nothing here enforces it"*.
* **Materials — LOW.** No substance, phase, composition, anisotropy or property
  identity. A property is a model + a realization — a good decision, proven only
  for scalars.
* **Fields — NONE.** `ScientificVariable` (`ir/variables.py:55-63`) carries
  `name, unit, kind, role, lower, upper, categories, description`. **No rank, no
  support, no component index.** A PDE field and a lumped scalar remain
  byte-identical records. The same type still carries `VariableRole.DESIGN`
  (normalized to a unit hypercube by `design/`'s codec) and `VariableRole.STATE`
  (a PDE unknown) — 08 §10.2's overload hypothesis, unresolved.

## 2.10 The four answers

**Can we add a new physics domain without modifying core?**
**Yes — measured over eight consecutive milestones, asserted by in-test `git diff`.**
And the reason is §2.3: the core carries identity and refusals, not physics.

**Can different physics domains share infrastructure?**
**Partially.** Shared and proven: units, records, provenance, validation
vocabulary, the coupling loop, the bulk-data plane. **Not shared:** numerics
(six solver modules call `scipy` directly; no kernel layer), discretization,
assembly, equations, admission enforcement, materials, session lifetime.

**Framework / application / library / prototype collection?**

Not A: a framework's core is on the critical path of the physics; this one is not,
and there is no equation, field, discretization or numerical layer to build on.
Not B: there is no product, workflow, UI, persistence, scheduler or run lifecycle.
Not D: it is coherent, boundary-enforced, and covered by 2571 tests and 22
falsified evidence documents.

> **It is (C) — a scientific library — of an unusual and valuable kind: a
> *record-and-refusal* library that decides what may be said about a computation,
> plus six thin domain verticals that prove the contracts survive contact with
> real physics. One of those verticals (electro-thermal) has been productized
> into a (B)-shaped application surface.**

The target is (A). The distance to (A) is Layers D, E and G, and the
executable-specification decision in §2.6.

---

# Phase 3 — Trust layer review

## 3.1 Can every result answer the six questions?

Measured by executing one real request end-to-end through
`engcore.application.handle` and inspecting the returned payload.

| Question | Internally | **Externally (what an API caller gets)** |
|---|---|---|
| **Who generated it?** | Software version + solver identities. **No actor, principal, user or agent identity exists anywhere in `src/`.** HTTP has no authentication. | `software_version`, `solver` per participant. **No actor.** |
| **With which model?** | `ProvenanceRecord.bindings` — the canonical `model → realization → solver` ternary, deduplicated, order-independent. Excellent. | **Yes** — 5 bindings projected, with realization where one exists. |
| **With which inputs?** | `ProvenanceRecord.inputs: Mapping[str, Quantity]` — never unit-stripped. | **Yes** — per participant (TRUST-HARDENING P3). Measured: `R:R1 = 125.115 ohm`, `Vs:V1 = 12.0 volt`. |
| **Under which conditions?** | `ProvenanceRecord.environment` = `{python, numpy, scipy, blas_architecture}`. Measured live: `blas_architecture: "Haswell"`. Added by TRUST-HARDENING P2 *because a frozen baseline drifted when OpenBLAS selected a different SIMD kernel from CPUID*. | **NO.** `project_run` (`contract.py:661-666`) projects only `run_id`, `software_version`, `assumptions`, `bindings`. **`environment`, `git_commit`, `timestamp`, `tolerances`, `parent_run_id` are all dropped.** |
| **Was it valid?** | Seven-rung `ValidationLevel`, `attained_levels` backed only by *passing* checks, `NOT_RUN ≠ PASS`, per-check residual and tolerance. | **Yes, and well** — full per-participant check list with residuals and tolerances. |
| **Why was it accepted?** | Model-applicability verdict (`ValidityAssessment`) + admission decision. | **Partially** — `model_validity` is projected on success. **On a refusal `result` is `null`, so the caller gets *less* structured information than on success** (see §3.4). |

**INFERENCE.** Five of six are answerable internally and four externally. The one
that fails outright — *under which conditions* — is precisely the fact the project
deliberately added two commits ago after measuring a real reproducibility failure.
**The reproducibility lock exists and does not leave the process.**

## 3.2 The admission story, measured

**FACT.** Two distinct concepts, kept correctly separate by
`docs/evidence/trust-hardening-preregistration.md` §0:

* **(a) numerical-validation admission** — `ValidationReport.require_admission`
  cross-references `ScientificProblem.validation_requirements` (a set of check
  *names*) against passing checks. `NOT_RUN`, `WARNING` and `FAIL` all count as
  unsatisfied.
* **(b) scientific-applicability admission** — `require_coupled_admission` refuses
  a run that converged to a state outside the model's declared validity domain.

**FACT — (b) works, end to end, over the real API.** Executed at four supply
voltages against the shipped electro-thermal execution:

```text
12 V  -> status "executed",        criterion_met, model_validity in_domain
30 V  -> refused: "the run converged to a state at which the model is not
         declared valid: 'R1': temperature outside the declared validity domain.
         The numbers are what the equations give; the model is not claimed to
         hold there"
60 V  -> same        120 V -> same
```

**No mainstream CAE tool refuses a converged answer because the model is not
declared valid there. This does, and it is measured.**

**FACT — (a) was published as shipped and did not exist.** At HEAD, grep for
`require_admission` under `src/` returns five production call sites — three in
`systems/fluidthermal/coupled.py`, two in `domains/fluids/transport2d/validation.py`
— **and none on the electro-thermal path an external caller reaches.**
`docs/evidence/trust-hardening-evidence.md` §2.2 tabulated it as one of "two
enforcement points". The regression test that was supposed to cover it
(`test_p1_7`) passed
`{check.name for check in result.validation.checks}` as the requirement set —
derived from the result under test — so it asserted *"every check that ran, ran"*
and could not distinguish a present gate from an absent one. The project found
this itself and preregistered `ADMISSION-GATE-REPAIR`; the fix landed as
`53f9f02` while this audit was being written (see the provenance note at the top).

## 3.3 Missing enforcement — the structural finding

**FACT.** `src/engcore/coupling/*.py` contains **zero occurrences** of
`validation`, `admission`, `require_admission` or `is_usable` outside one
docstring reference. `run_fixed_point` transports `result.values[...]` and never
reads `result.validation`.

**FACT.** `ValidationReport.require_admission`'s own docstring states the design:
*"A caller that does not call it gets no protection — enforcement is not automatic
on construction."* `systems/electrothermal/coupled.py` (working tree) states the
consequence out loud: two of its three gates use **consumer-invented**
requirement sets, because `thermal_lumped` and `electrical/material` publish no
`validation_requirements` of their own — *"weaker evidence than a producer-published
one, and labelled as such."*

**INFERENCE.** The measured 18.05 K failure (`HETERO-NGSPICE`: a provider's sign
convention produced `validation_status = FAIL` and the coupled loop transported
the value anyway) is closed **by convention, not by structure**. Every future
domain, provider and system pack must independently remember to call
`require_admission`, and the one execution a consumer could reach forgot — and
the test written to prove it hadn't could not tell. That is the definition of a
fake guarantee, and the repository has now measured it on itself.

**Study 08 §9.4 proposed the fix a chain of milestones ago:** *a coupling may not
transport a value from a result whose validation status is `FAIL`*. It has still
not been made a rule of `coupling/execution.py`.

## 3.4 Information that exists internally and disappears externally

| Fact | Where it lives | Reaches an API caller? |
|---|---|---|
| Resolved numerical stack (`blas_architecture`, numpy/scipy/python versions) | `ProvenanceRecord.environment` | **No** |
| `git_commit`, `timestamp`, `parent_run_id`, `tolerances` | `ProvenanceRecord` | **No** |
| Per-iteration participant results | `CoupledRun.iterations` | **No** — deliberate and documented (162 kB for 10 iterations) |
| Bulk data references | `ScientificResult.data_references` | **No representation** — `project_run` **refuses** rather than understating (`contract.py:559-567`). Correct. |
| Which validity criterion was violated, and by how much | `ValidityAssessment.violated` + the actual `Quantity` | **Name only.** The refusal says `'R1': temperature outside the declared validity domain` — not the value reached, not the declared 200–450 K bound. |
| Model applicability on a **refused** run | `AdmittedCoupledRun.applicability` | **No** — `result` is `null` on refusal |
| Domain package identity and version | **nowhere** — recorded as a known gap in `docs/executable-scientific-spec-evidence.md` §N | No |

**INFERENCE.** The trust layer is genuinely strong *inside the process* and
**lossy at exactly the boundary where trust has to be transferred**. For an AI
consumer this is the difference between "Crafty is trustworthy" and "Crafty can
prove to me that this number is trustworthy".

## 3.5 What the trust layer gets right, and should not lose

Verified in this tree, not taken on trust:

1. `NOT_RUN ≠ PASS` — an empty report aggregates to `NOT_RUN`, never `PASS`.
2. `attained_levels` is **derived** from passing checks and **recomputed and
   verified on deserialization**; a hand-edited record cannot smuggle in an
   unearned claim (`validation.py:283-292`).
3. `ValidityDomain.assess` returns `UNKNOWN` for an empty domain — absence of
   declared limits is not evidence of validity.
4. `Uncertainty.unknown(...)` is a real answer; nothing invents a number.
5. Provenance **collects nothing on its own** — no hostname, path, user or
   timestamp — on stated privacy *and determinism* grounds.
6. `ExecutionBinding` keeps `model → realization → solver` **structurally**, so
   the association survives any number of participants and any ordering; a
   `models`/`solvers` set that contradicts the bindings is refused, not reconciled.
7. Identity ≠ location: `ScientificDataReference` carries a digest and no path,
   URI, host or store, and its docstring is unusually careful about what a digest
   does **not** prove.
8. Refusal over invention, in five measured places.

**Gap in the ladder, still open [08 §4.5]:** no `ValidationLevel` member denotes
physical admissibility, so a *passing* boundedness or conservation check has
nothing to put in `establishes=`. A domain can record "this is wrong" and cannot
record "this was checked and is right". Corroborating: `ScientificVariable.lower/upper`
are typed and dimension-checked and **nothing under `results/` consults them**.

**No result-level integrity.** Bulk data is content-addressed; the
`ScientificResult` record itself carries no digest or signature. `sria/signatures.py`
hashes calibration keys, not results.

---

# Phase 4 — AI interface readiness

Assessed by driving the real MCP server and the real boundary, as an agent would.

## 4.1 The six agent questions

**1. Can an AI agent discover available physics capabilities?**
**Barely.** `tools/list` returns exactly one tool, `crafty_run`, whose
`inputSchema` enumerates **one execution** (`electrothermal.series_self_heating/1`)
and two profiles (`native`, `ngspice`). There is no capability endpoint, no model
list, no domain list — deliberately: `crafty_http/server.py` documents deleting
`GET /v0/capabilities` because *"no aggregated registry and no planner exist, so a
capabilities surface would publish discovery no caller can act on."* That
reasoning is correct **and** the consequence is that the five other domain packs
and three other system packs in this repository are invisible and unreachable.

**2. Can it understand required inputs? — YES, and this is the strongest part.**
The 7,835-byte JSON Schema is **derived from the constants the validator
enforces**, not transcribed, with a test asserting the derivation. It uses
`additionalProperties: false` at every level, publishes per-execution `if/then`
clauses so `execution` and `execution_profile` cannot be read as independent, and
publishes the *affine-unit* constraint in prose on the fields that carry a
difference. Two refusals JSON Schema cannot express (byte limit; identifier
uniqueness) are stated in the schema `description` rather than left to be
discovered.

**3. Can it create a valid request?** **Yes, in ~4 turns.** Measured: my first
four attempts were each refused, and **each refusal named the admissible set**:

```text
"stages[0] carries unknown field(s) ['resistance_at_reference','thermal_resistance'];
 this reader refuses fields it does not implement rather than ignoring them.
 Known: ['ambient_conductance','ambient_temperature','component_id','duration',
 'heat_capacity','initial_temperature','reference_resistance',
 'reference_temperature','temperature_coefficient']"

"transported_temperature must be one of ['final_temperature','steady_state_temperature'],
 got 'body_temperature'. Both are kelvin-valued, so this name — not a dimension
 check — is what selects the physics that is transported."
```

**This is a model of agent-legible error design.** Unknown fields are refused
rather than ignored, so a request that *would* change the answer cannot silently
produce a different number.

**4. Can it execute? — Yes.** MCP `tools/call`, HTTP `POST /v0/run`, and Direct
Python all carry the identical payload with deliberately different framing.

**5. Can it understand limitations?** **Partially, and worse on refusal than on
success.** On success it receives `model_validity` with satisfied/violated/unknown
criterion names, `assumptions`, and per-check residuals and tolerances. On the
applicability refusal it receives a sentence naming the criterion — and no
value, no bound, no structured `model_validity` object, because `result` is
`null`. **An agent cannot compute a corrective action; it must guess.**

**6. Can it explain the result?** **Mostly yes**, and better than most CAE APIs.
Five distinctions are held apart in the payload —
`TRANSPORT ≠ EXECUTION ≠ NUMERICAL CONVERGENCE ≠ COUPLING CONVERGENCE ≠ VALIDITY`
— `status` is never a boolean and never the word *success*, and the tool
description tells the agent in plain language that a budget-exhausted run *"is a
SUCCESSFUL execution … it is not an error and must not be retried as one."*
Measured: a 2-iteration budget returns `status: "executed"`,
`outcome: "iteration_limit_reached"`, with all three participants reporting
`validation_status: "pass"` — the executed fact, kept visible.

## 4.2 Four concrete API defects

**D1 — `status` and `refusal.code` disagree about fault attribution.**
Measured: a validity-domain refusal returns
`{"status": "execution_failed", "refusal": {"code": "scientific_admission_refused"}}`.
`_refusal` in `service.py:80-85` sets `status` from the *stage*, and a scientific
refusal raised on the execution stage therefore reads as an execution failure. On
HTTP the status line is correct (422, keyed on the code), but an agent keying on
the payload's `status` — the field the contract elevates — sees a word that means
*Crafty broke* for an event that means *your science was refused*. That is exactly
the blind-retry loop the MCP framing decision exists to prevent.

**D2 — no published response contract.** `describe.py` publishes
`request_json_schema()`; there is **no** `response_json_schema()` and the MCP tool
declares **no `outputSchema`**, although it returns `structuredContent`. The
response shape is documented only in prose in `contract.py`'s module docstring. An
agent can build a request from data and must reverse-engineer the reply.

**D3 — one execution, and the response shape is welded to coupling.**
`project_run` takes a `CoupledRun`. `result.coupling` and `result.torn_endpoints`
are properties of a torn fixed-point iteration, not of "a Crafty execution". The
code says so and names the escape hatch (`crafty_execution_response/2`). Correct
foresight — and it means the *first* non-coupled execution to be exposed is a
schema bump, not an addition.

**D4 — provenance is truncated at the boundary.** §3.4.

## 4.3 What the AI interface gets right

* **The transports carry the identical boundary payload and disagree only about
  framing**, and the differential test compares the payload and never the framing.
* **A refused request is a completed tool call** (`isError: false`) with the
  refusal in `structuredContent`, so an agent can read *why*.
* **A malformed JSON-RPC envelope is a JSON-RPC error**, and a 404 on HTTP is a
  bare `{"error": ...}` with no schema string — a routing fault is not dressed as
  a scientific refusal.
* **The size limit is enforced from one constant in both transports** — a real
  asymmetry that was found and closed.
* **No default anywhere that would select which implementation computes the
  answer:** `execution_profile` is required precisely so no default picks a solver.
* The `MAX_REQUEST_BYTES`, `MAX_ITERATION_BUDGET`, `MAX_STAGES` bounds are
  **refusals, not clamps** — silently reducing a caller's budget would change the
  science without saying so.
* A reproduced remote-code-execution through `component_id` was found by the
  falsifier and closed; the regression test uses a launch sentinel with a positive
  control (§1.5).

---

# Phase 5 — Industry-standard comparison

Compared on extensibility, scientific correctness, trust and automation
readiness — not feature count.

| | **Modelica / FMI** | **OpenFOAM** | **FEniCS** | **COMSOL** | **ANSYS workflow** | **Crafty (today)** |
|---|---|---|---|---|---|---|
| **Extensibility** | equations in a language; acausal connectors; flattening compiler | runtime-selected `fvm::` operators; new solver = new app | UFL: write the weak form, get the assembly | physics interfaces, closed | closed, ACT scripting | **new domain = new Python pack + own artifact + own solver.** Core untouched — because the core carries no physics |
| **Scientific correctness** | equation-level; units checked | discretization-level; user owns validity | strongest formal path from PDE to code | validated libraries, opaque | validated, opaque | **validity domains, dimensional coherence at construction, refusal over invention** — but no equation to check against |
| **Trust** | FMU carries `modelDescription.xml`, no validity semantics | none beyond residuals | none | none in the artifact | report generation | **best-in-class semantics**: `NOT_RUN ≠ PASS`, `UNKNOWN ≠ valid`, mandatory provenance, `model → realization → solver` binding, applicability admission that refuses a converged answer |
| **Automation readiness** | FMI is *the* machine contract; co-simulation is standardized | dictionaries; scriptable, not discoverable | Python-native | GUI-first, LiveLink | Workbench/ACT | **one MCP tool, one execution, derived request schema, no response schema, no planner** |

**Three specific comparisons worth stating plainly.**

* **FMI's `modelDescription.xml` is exactly what `ScientificProblem` is trying to
  be and is not.** An FMU is self-describing *and* executable: variables, causality,
  variability, units, and a binary that can be stepped from the description alone.
  Crafty has the description and hands the executable part over the side via
  `bind_*`. **This is the single sharpest gap between Crafty and the nearest
  industrial standard, and it is the same gap as §2.6.**
* **UFL is the equation IR Crafty has not named.** FEniCS shows the payoff:
  one representation, many discretizations, solver-neutral assembly. Without one,
  a Crafty "realization" has nothing to *be* except an implementation id — which is
  precisely §2.5.
* **preCICE is the coupling runtime Crafty is a scalar-only subset of.** Crafty's
  loop is genuinely well-built (declared graph, computed order, declared tears,
  independent convergence criterion), and it lacks participants-as-records,
  mappings, time windows, acceleration and rollback. The project's own study 04
  already records this. Crafty deliberately refuses what it cannot represent, which
  is the right posture — and it caps the addressable coupling class at
  *scalar-endpoint, memoryless, single-cycle, solved-to-completion*.

**Where Crafty genuinely leads all five.** None of Modelica, OpenFOAM, FEniCS,
COMSOL or ANSYS will refuse to hand you a converged number because the model is
not declared valid at the state it converged to. Crafty does, measured, on the
shipped path. None of them distinguishes *the check did not run* from *the check
passed* as a type-level invariant. None carries a provenance record that structurally
cannot lose which realization computed which model on which solver. **That is the
product.**

---

# Phase 6 — Findings

## CRITICAL

### C1 — The IR is not executable, and the pattern is now the extension mechanism
**Evidence.** 13 `bind_*` sites in 10 modules (§2.3); three solvers state it in
their own error text — *"the universal IR carries no topology / geometry /
chemistry"*; `prepare(self, problem)` is unannotated and `PreparedSolve.payload: Any`;
`fluids/transport2d`, written after study 08 flagged this, reproduces it.
**Why it matters.** A planner cannot select what the records do not describe. Every
claim in the master context about capability graphs, model/realization selection
and an AI choosing physics is blocked here, not on planner code. It also forces
per-instance mutable solver state, which blocks concurrency, sessions and any
provider with a lifetime (an FMU, a licensed session, a warm-started solver).
**Recommended fix.** Take **option G**, already named and deferred by the
project's own EXEC-SPEC decision (§2.6, §M): change `ScientificSolver.prepare` to
receive the domain structure explicitly, removing `dict[problem_id → artifact]`.
Scope it to one domain and one measurement first. Do **not** revisit the
already-decided question of a universal executable-spec record — that was measured
and correctly answered *no*.

### C2 — Trust enforcement is a convention, not a structure
**Evidence.** `coupling/execution.py` has zero references to validation or
admission (§3.3), and still does not at `53f9f02`. `require_admission` is opt-in
by design. At `c5c7c70` the **one execution an external caller can reach had zero
numerical-admission gates**, after a milestone published them as shipped, and the
regression test could not detect their absence (§3.2). Two of the three gates
`53f9f02` added use consumer-invented requirement sets because the producers
publish none.
**Why it matters.** This is the measured 18.05 K wrong-answer failure mode. A
guarantee that every new participant must remember is not a guarantee, and the
repository has now proved that on itself.
**Recommended fix.** Make the *loop* the enforcement point, as study 08 §9.4
proposed: `run_fixed_point` refuses to transport a value from a result whose
declared `validation_requirements` are not satisfied. It needs no new record, it
is testable, and it converts N per-pack conventions into one invariant. Keep the
per-producer gates as defence in depth. Separately: make
`validation_requirements` **mandatory and non-empty** for any problem whose
result is transported, so a consumer never has to invent one.

### C3 — The trust record does not cross the boundary
**Evidence.** `ProvenanceRecord.environment` — measured live as
`{python 3.14.2, numpy 2.4.3, scipy 1.18.0, blas_architecture "Haswell"}`, added
two commits ago *because a baseline drifted on a SIMD kernel change* — is not
projected. Nor are `git_commit`, `timestamp`, `tolerances`, `parent_run_id`. No
actor identity exists anywhere. No published response schema. Refusals carry less
structure than successes.
**Why it matters.** The strategic target is a trust layer an AI can *rely on*.
Trust that does not leave the process is not a trust layer; it is a diary. An
agent asked "can I reuse this number?" currently cannot answer it from the payload.
**Recommended fix.** `crafty_execution_response/2`: add `provenance.environment`,
`provenance.git_commit`, per-participant `tolerances`, a structured
`model_validity` on refusal payloads, and the domain-package identity + version
already listed as missing in `docs/executable-scientific-spec-evidence.md` §N.
Publish `response_json_schema()` and wire it to the MCP tool's `outputSchema`.

## HIGH

### H1 — Science lives in `metadata` prose strings
**Evidence.** `transport2d/problem.py:589-596` carries the velocity field
`"u = omega*(-(y-L/2), (x-L/2))"`, the boundary condition
`"c = c*(x,y) on all four sides"` and `n_cells` as strings, while
`ScientificProblem.validity_context` is documented as *"deliberately not sourced
from metadata"*. The policy is inconsistent: `ModelRealizationDefinition` and
`QuantityDependency` refuse `metadata` at length; `ScientificProblem`,
`ScientificParameter`, `ScientificModelDefinition` and `ScientificResult` all
carry it.
**Why it matters.** Purity on the newest records without a typed home does not
prevent the leak; it relocates it to the older ones. Three domains have already
invented three incompatible artifact-reference conventions inside `metadata`
(EXEC-SPEC §A).
**Recommended fix.** Not a new universal record — that was measured and declined.
Land the E+F boundary EXEC-SPEC actually selected: typed, versioned,
round-trippable per-domain structure records with a typed identity check, and
delete the corresponding `metadata` keys as each domain converts. Currently
`from_dict` exists under `domains/` **only** in electrical DC.

### H2 — Realization applicability is off-record; realizations are not selectable
**Evidence.** §2.5, `_APPLICABILITY` at `thermal_conduction1d_schemes.py:243`.
**Why it matters.** Blocks the planner independently of C1, and is the reason
`admissible_realizations` — the only selection-shaped function in the tree —
correctly refuses to select.
**Recommended fix.** Add a validity/applicability field to
`ModelRealizationDefinition`, reusing the existing `ValidityDomain`. It is the
smallest change in this list that unblocks a real capability.

### H3 — 21.6 % of the source is unreachable, and CI gates *that* rather than the product
**Evidence.** 78 modules / 18,309 lines reached by nothing (§1.2).
`logic-hardening-checks.yml` runs five of those modules on every PR touching
`src/engcore/**` and never invokes pytest (§1.6).
**Why it matters.** Diligence noise, review noise, and a CI signal that is
actively misleading — a green check that exercised dead code.
**Recommended fix.** Move the optimizer heritage to `research/` or a tagged
branch; retire `logic-hardening-checks.yml`; make `sria-tests.yml` trigger on all
branches and set `PYTHONPATH=src`.

### H4 — SRIA is architecturally orphaned and is a second vocabulary
**Evidence.** 19,863 lines (23 % of `src/`); zero importers; reaches the core
essentially only through `scientific.serialization` (39 sites);
`sria/domain_pack.py::DomainPack` restates `model_references`,
`parameter_semantics`, `qois`, `scope`, `assumptions`, `fidelity_ladder` as
strings and `Any`, all of which exist typed in `scientific/models/definition.py`.
**Why it matters.** It is the largest single asset in the repository and the
hardest to explain to a buyer, because nothing consumes it. Reconciliation cost
rises with every SRIA milestone.
**Recommended fix.** A one-page mapping document, not code, before any further
SRIA work — and a decision: is SRIA Layer H of Crafty, or a separable product?

### H5 — `status` misattributes fault on a scientific refusal
**Evidence.** §4.2 D1. **Fix.** Add a fourth `status` word, or set `status` from
the refusal code rather than the stage.

### H6 — Refusals are not actionable for physical bounds
**Evidence.** §3.4, §4.1 Q5. The refusal names the criterion; not the value
reached, not the declared bound, and `result` is `null` so `model_validity` is
lost. **Fix.** Carry the `ValidityAssessment` (and the violating `Quantity`) in
the refusal payload. The record already exists; only the projection is missing.

### H7 — Evidence tests carry hidden environment dependencies
**Evidence.** §1.5 — a headline evidence test passes only when `PYTHONPATH=src`
is exported, and would fail under this repository's own CI command; the reproduced
RCE guard's positive control does not fire on this machine, leaving the security
claim unverified here; one transport test is order-dependent.
**Why it matters.** In a project whose entire method is evidence, a test whose
result depends on undeclared environment is the same class of defect as the
vacuous `test_p1_7` — it can pass without measuring.
**Fix.** Pass an explicit `env=` to every `subprocess.run` in tests; treat a
positive control that does not fire as an **error**, not a failure, so it cannot be
confused with the guard breaking.

## MEDIUM

* **M1 — No field, rank or support; `ScientificVariable` is overloaded.** The same
  type carries a `DESIGN` variable normalized to a unit hypercube by an optimizer
  codec and a `STATE` PDE unknown. Study 08 §10.2's hypothesis — that the "missing
  field semantics" gap is at least as much a *type-overload* gap — remains untested
  and cheap to test.
* **M2 — No system / component / port record.** §2.7. Composition identity is a
  string-derivation convention in one pack; a second pack deriving differently is
  undetectable.
* **M3 — No equation, residual, operator or Jacobian representation anywhere,**
  and none on any milestone list. Reversal cost rises with every domain written
  before it exists.
* **M4 — No numerical-runtime layer.** Six solver modules call `scipy` directly;
  there is no shared kernel, no preconditioner policy, no backend policy.
* **M5 — Solver lifetime is one call**, and solvers hold per-instance mutable
  `dict[problem_id → artifact]`. Blocks the second external provider.
* **M6 — No result-level integrity.** Bulk data is content-addressed; the
  `ScientificResult` is not. Only `attained_levels` is recomputed-and-verified on
  load.
* **M7 — Packaging and IP hygiene.** No LICENSE, no NOTICE, no CONTRIBUTING;
  `pyproject` still declares `engineering-ai-core` / *"Smart experiment engine
  proof of concept"*; 17 `README-V0.x.y.md` files at the root describing the dead
  optimizer line. Diligence asks on day one.
* **M8 — `ConstraintDefinition` is a name collision.** It means *metric OP bound*
  — a study acceptance test. Structural mechanics, DAEs, contact, incompressibility
  and stoichiometric closure all mean *relation among unknowns*. Rename or namespace
  before a domain author binds a DAE to it.
* **M9 — 75 commits unmerged to `origin/main`,** with `main` sitting at
  `03c30f6` (HETERO-NGSPICE). The repository's public history stops eight
  milestones behind its actual state.

## LOW

* **L1** — MCP tool declares no `outputSchema` while returning `structuredContent`.
* **L2** — `ScientificTwin` is produced in five modules and **read by none**. Five
  milestones, zero evidence for its motivating instance-authority role. Decide:
  promote or retire the name.
* **L3** — Registries are per-domain factory functions; no cross-domain query, and
  `SolverRegistry` still has no non-test consumer.
* **L4** — UQ is a dense grid over one parameter (`inference/grid.py`), lives only
  in the kinetics vertical, and is unreachable externally. "We have quantified
  uncertainty" is currently a claim about one-parameter problems.
* **L5** — `solve_circuit` writes `circuit.canonical_dict()` into
  `ProvenanceRecord.metadata` on every solve: `O(iterations × topology)` bytes in
  the control plane the data boundary exists to keep small.
* **L6** — `BoundaryCondition` has no `time` field though `InitialCondition` does;
  no data reference carries a time level; nothing represents a schedule or window.

---

# Final decision

## 1. Is the current architecture suitable for a Physics Runtime?

**As a Trust Layer: yes, and it is ahead of the industry.** As a **Physics
Runtime: not yet, and not for the reason usually assumed.**

The obstacle is not missing physics. It is that **the universal records describe
computations they cannot specify.** Every solver in the tree needs a domain-native
artifact handed to it out of band; every discretization fact lives in a metadata
string or a module-level dict; no record anywhere states the relation a model
claims to hold. The consequence is exact:

> **A planner cannot select what the records do not describe, and a coupling
> cannot transport what the records cannot represent.**

The eight-milestone zero-core-edit result is real, and it is currently evidence of
*decoupling* rather than of *extensible representation* — because the core is not
load-bearing for the physics. That is the one sentence of this audit I would most
want challenged, and §2.3 is the evidence for it.

## 2. What must change before AI scales on this

The AI interface already exists and is well built. What must change before it is
worth scaling, in order:

1. **C2 — enforcement into the loop.** Cheapest, highest-value, closes a measured
   wrong answer, and stops the next domain from re-deriving an invariant from memory.
2. **C3 — the trust record must cross the boundary,** with a published response
   schema. Without this, an agent cannot answer *under which conditions* and cannot
   act on a refusal.
3. **C1 / option G — stateless `prepare`,** for one domain, as a measurement.
   Everything downstream — planner, concurrency, sessions, a second provider, a
   second execution — is behind it.
4. **H2 — realization applicability on the record.** The smallest change that turns
   *identifiable* into *selectable*.

**And one thing that must not change first:** do not add a second execution to the
API before C2 and C3. A second execution multiplies a convention-based guarantee
and a truncated provenance projection across two surfaces instead of one.

## 3. What should never be changed

These are the assets. Several are rare enough to be the commercial case.

1. **Units are never implicit.** `Quantity` refuses bare numbers, non-finite
   magnitudes, and a process-global registry.
2. **`NOT_RUN ≠ PASS`**, and `attained_levels` derived from passing checks only,
   recomputed and verified on load.
3. **Empty validity domain ≠ unlimited validity** — `assess` returns `UNKNOWN`.
4. **`UNKNOWN` is a real answer for uncertainty.** Nothing invents a number.
5. **Refusal over invention** — fan-in, mixed-dimension tolerances, affine
   comparison units, best-effort data resolution, mixed-sign boundary orientation.
   Make this an explicitly written core principle: it is currently enforced by
   author discipline and it is the behaviour most likely to erode under schedule
   pressure or a second contributor.
6. **Identity ≠ location** for bulk data, with an honest digest contract.
7. **Model ≠ Realization ≠ Solver, held by `ExecutionBinding`** as a structural
   ternary, with contradiction refused rather than reconciled.
8. **Provenance auto-collects nothing.** Privacy *and* determinism.
9. **The core never imports a domain**, asserted by in-test `git diff` against a
   preregistration commit rather than against `HEAD`.
10. **The coupling loop has no domain branch,** and coupling convergence is never
    derived from a participant's own convergence.
11. **Transport status is not scientific truth** — a non-converged run is 200 OK
    and a successful tool call.
12. **Preregistration → evidence → adversarial falsification, with refuted
    predictions recorded as deviations.** This method just caught a published
    guarantee that did not exist in the code. Very few projects of any size produce
    falsifiable negative results about themselves. **This is the most transferable
    asset in the repository.**

**One thing currently defended that should *not* be preserved:** the "no
centralized `admit()`" position in `application/__init__.py`. It is correct that
the *application layer* must not hold a scientific gate. It does not follow that
*no* layer should — and §3.3 measured the cost of that inference. The coupling
loop is the right home: it is domain-neutral, it is the only thing that transports
a value between problems, and it already refuses four other things.

## 4. The correct next milestone

**`ADMISSION-GATE-REPAIR` is in flight and should be finished and committed
first** — including the vacuous-test correction, which is the more important half.

Then, one milestone, one question:

> ### `EXEC-G0` — Can a solver be prepared without being bound?
>
> **Question.** Take **one** domain — `domains/electrical/dc`, which is the only
> one with a complete `from_dict` reader and is already schema-versioned as
> `electrical_dc_circuit/1` — and change `ScientificSolver.prepare` to receive the
> structure explicitly. Measure: does the `dict[problem_id → artifact]` disappear?
> Does the solver become stateless and re-entrant? What does the change cost in the
> other three implementations and in `domains/thermal/`, which is byte-pinned by
> three frozen experiments?
>
> **Why this and not something else.** The project's own EXEC-SPEC evidence
> already names option G, records that P-8 held, states that reconstruction alone
> does not remove the bind maps, and explicitly defers G as *"a separate decision
> … not taken here."* This milestone takes it, on one domain, as a measurement
> rather than as an architecture.
>
> **Why not a bigger milestone.** A field record, an equation IR, a component/port
> contract and a numerical-runtime layer are all genuinely missing (M1–M4). Every
> one of them is downstream of *"can a solver be prepared from what the records
> hold?"* Building any of them first means building a representation for a runtime
> whose execution contract is still `Any`.
>
> **Fold in, as sub-items with their own tests, both under one day:** the
> transport-admissibility rule in `coupling/execution.py` (C2) and
> `response/2` + `response_json_schema()` + `outputSchema` (C3). Both are
> independent of the outcome of the G measurement, both close measured defects, and
> both get more expensive once a second execution or a second stored payload exists.

**Explicitly not next:** a second execution on the API; a new domain; any further
SRIA milestone; a field or equation record; anything in `design/` or the optimizer
heritage.

---

**Closing observation.** The repository's evidence discipline is ahead of its
architecture, and that is the right way round — it is why this audit could be
written against measurements rather than against prose, and why the project found
its own false guarantee before an external reviewer did. The architecture's single
weakness is also single: the records describe, and something else executes. Close
that, and Layers D, E and G become buildable rather than speculative. Leave it
open, and every layer above the records keeps waiting on it.
