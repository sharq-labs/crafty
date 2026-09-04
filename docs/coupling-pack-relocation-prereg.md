# COUPLING-PACK-RELOCATION — preregistration

Committed **alone, before any implementation commit on this branch**. Nothing
below is edited afterwards; every divergence is recorded in
`docs/coupling-pack-relocation-evidence.md`.

Baseline: `origin/cloud/crafty-post-fluid-thermal` @
`ad6e6cd0833be7161b1575d9b5b5e97d339e4b27`. Verified FULL regression on that
commit: **2177 passed / 0 failed / 0 errors**.

---

## 1. What this milestone is, and what it is not

Two materially different production coupled systems now exist:

* `src/engcore/systems/electrothermal/` — Electrical ↔ Thermal (`ET-VERTICAL`)
* `src/engcore/systems/fluidthermal/` — Fluid ↔ Thermal (`FT-SCALAR-COUPLING`)

`FT-SCALAR-COUPLING` measured that the second consumer reuses the first's
coupling machinery **by object identity, unedited**, and recorded two
consequences of that machinery living inside a domain-named pack:

* a fluid ↔ thermal run serializes under `electrothermal_coupled_run/1`
  (fluid-thermal evidence §V, falsifier C-4 — named "the cheapest-now /
  expensive-later item in the milestone");
* a new coupled pack must import a **domain-named** system pack to reach the
  loop, inverting "domain modules depend inward" (fluid-thermal evidence §V,
  Domain Extensibility row).

This milestone corrects **ownership, naming and serialization identity, only
where measurement justifies it.** It is not a multiphysics framework.

**Explicitly not built, in any form:** Generic Multiphysics Framework,
`ScientificField`, Mesh, Topology, Equation IR, Relation IR, temporal
semantics, planner, provider framework, cross-mesh transfer, field-valued
coupling, relaxation framework, scheduler, graph execution engine, API/MCP.

**Explicitly not changed:** scientific models, domain physics, solver
algorithms, coupling numerical results, admission semantics, validation
semantics.

The target boundary, stated once and repeated in the new package's own
docstring:

> `engcore.coupling` is **domain-neutral coupling execution and composition
> infrastructure**. It is explicitly **NOT universal scientific semantics** and
> is not a promotion into `engcore.scientific`. It may transport identities and
> values and execute a declared plan; it may not know what any transported
> value means.

---

## 2. Exact generic candidates (proposed to relocate)

Every object below is defined today in
`src/engcore/systems/electrothermal/coupled.py`.

| # | Object | Kind | Line (baseline) |
|---|---|---|---|
| G1 | `is_ratio_scale` | function | 177 |
| G2 | `shares_origin` | function | 207 |
| G3 | `_require_ratio_scale` | function | 219 |
| G4 | `edge_key` | function | 231 |
| G5 | `CouplingOutcome` | enum | 252 |
| G6 | `TornEndpoint` | frozen dataclass | 273 |
| G7 | `FixedPointCouplingPlan` | frozen dataclass | 328 |
| G8 | `_edges` | function | 573 |
| G9 | `execution_order` | function | 577 |
| G10 | `cycle_edges` | function | 614 |
| G11 | `CoupledIteration` | frozen dataclass | 1027 |
| G12 | `CoupledRun` | frozen dataclass | 1099 |
| G13 | `run_fixed_point` | function | 1379 |
| G14 | `TORN_ENDPOINT_SCHEMA` | schema constant | 159 |
| G15 | `FIXED_POINT_PLAN_SCHEMA` | schema constant | 160 |
| G16 | `COUPLED_ITERATION_SCHEMA` | schema constant | 161 |
| G17 | `COUPLED_RUN_SCHEMA` | schema constant | 162 |

## 3. Exact pack-specific candidates (proposed to retain, unmoved)

**Electrothermal-specific** (`systems/electrothermal/`): `DEPENDENCY_HEAT`,
`DEPENDENCY_TEMPERATURE`, `DEPENDENCY_RESISTANCE`, `SOURCE_ID`,
`REFERENCE_NODE`, `CoupledStage`, `CoupledElectroThermalSystem`,
`coupled_problems`, `stage_problems`, `coupled_dependencies`, `nominal_plan`,
`build_coupled_twin`, `_property_result`, `_thermal_result`,
`_electrical_result`, `_executors`, `run_fixed_point_coupling`, and the whole
of `resistor_body.py`.

**Fluidthermal-specific** (`systems/fluidthermal/`): `DEPENDENCY_EFFLUX`,
`DEPENDENCY_CONDUCTANCE`, `DEPENDENCY_TEMPERATURE`, `DEPENDENCY_DIFFUSIVITY`,
`THERMAL_ADMISSION_REQUIREMENTS`, `SOFTWARE_VERSION`, `FluidSlice`,
`HeatedBody`, `FluidThermalSystem`, `coupled_problems`,
`coupled_dependencies`, `nominal_plan`, `_diffusivity_result`,
`_fluid_result`, `_wall_result`, `_thermal_result`, `_executors`,
`run_fluid_thermal_coupling`, `sweep_timings`, and the whole of
`properties.py` and `reference.py`.

**Rule applied:** pack-specific physics — `R(T)`, `I²R`, the electrical →
thermal mapping, `D(T)`, boundary efflux, the `hA` mapping, participant
construction, executor construction and result extraction — stays pack-owned.
Renaming a variable does not make anything generic.

## 4. Classification of every candidate

Categories: **USC** universal scientific core · **DNCI** domain-neutral
coupling infrastructure · **ET** electrothermal-specific · **FT**
fluidthermal-specific · **RT** runtime-only · **SER** serialization-only.

| Candidate | Class | Basis |
|---|---|---|
| coupling plan record (`FixedPointCouplingPlan`) | DNCI | names no domain; both consumers construct one |
| torn-endpoint record (`TornEndpoint`) | DNCI | both consumers construct one |
| iteration record (`CoupledIteration`) | DNCI + SER | produced by the shared loop for both |
| coupled-run record (`CoupledRun`) | DNCI + SER | both consumers receive one |
| outcome enum (`CouplingOutcome`) | DNCI | both consumers assert on it |
| coupled-run serialization (4 schema strings) | SER | see §5 |
| execution helper (`run_fixed_point`) | DNCI + RT | shared, unedited, by object identity |
| dependency ordering (`execution_order`, `cycle_edges`, `_edges`, `edge_key`) | DNCI | pure readers of `QuantityDependency` |
| residual / convergence calculation | DNCI | iterate-change only; no equation residual exists anywhere |
| comparison-unit admissibility (`is_ratio_scale`, `shares_origin`, `_require_ratio_scale`) | DNCI | rule is "does zero map to zero"; carries no dimension |
| executor bindings (`_executors` ×2) | ET / FT | build closures over domain solvers |
| conversion / mapping logic (`R(T)`, `D(T)`, `hA(Φ_D)`) | ET / FT | physics |
| pack model identities | ET / FT | `LINEAR_TCR_MODEL`, `POWER_LAW_DIFFUSIVITY_MODEL`, … |
| result extraction (`_property_result`, `_fluid_result`, …) | ET / FT | name domain metrics |
| **anything at all** | **USC** | **expected default: nothing.** No object in this inventory is proposed for `engcore.scientific`. |

**Predicted USC count: 0.** Files changed under `src/engcore/scientific/`:
**predicted 0.** A non-zero result is a milestone-level finding and is reported
loudly, not absorbed.

## 5. Two-consumer test — measured, before implementing

Direct AST name usage in production source, and in each consumer's own test
suite (measured on the baseline commit):

| Object | ET prod | FT prod | FT tests | Transitively reached by FT at runtime |
|---|---|---|---|---|
| `run_fixed_point` | yes | yes | yes | — |
| `FixedPointCouplingPlan` | yes | yes | yes | — |
| `TornEndpoint` | yes | yes | yes | — |
| `CoupledRun` | yes | yes | yes | — |
| `CouplingOutcome` | yes | no | yes (9×) | yes (`run.outcome`) |
| `execution_order` | yes | no | yes (3×) | yes (inside `run_fixed_point`) |
| `cycle_edges` | no | no | yes (1×) | — |
| `CoupledIteration` | yes | no | no | yes (`run.iterations`) |
| `edge_key` | yes | no | no | yes (`plan.uncut`, `__post_init__`) |
| `is_ratio_scale` / `shares_origin` / `_require_ratio_scale` | yes | no | no | yes (`plan.__post_init__`) |
| 4 schema constants | yes | no | no | yes (`run.to_dict()`) |

**Domain-vocabulary gate.** Each relocated object must contain, in its
*executable* source (string constants blanked), none of: `electrical`,
`thermal`, `joule`, `resistor`, `circuit`, `fluid`, `transport2d`,
`diffusivity`, `efflux`, `conductance`, `temperature`, `heat`, `kelvin`,
`watt`, `ohm`, `kinetics`, `cstr`. This is already asserted for a subset by
`test_i3` / `test_m2` and is extended to the whole new package.
Docstrings are prose about a rule, not the rule; they are scanned separately
and are permitted to *name* a consumer historically, but the new package's
docstrings are rewritten to be domain-neutral where they currently narrate
electro-thermal physics.

## 6. Schema identity cleanup

Coupling-related schema strings in the repository, complete:

| Schema string | Declared at | Any other occurrence |
|---|---|---|
| `electrothermal_torn_endpoint/1` | `electrothermal/coupled.py:159` | `tests/test_electrothermal_vertical.py`, 3 `docs/*.md` |
| `electrothermal_fixed_point_plan/1` | `:160` | same |
| `electrothermal_coupled_iteration/1` | `:161` | same |
| `electrothermal_coupled_run/1` | `:162` | same |

**Stored-payload search (executed before writing this document).** Searched
`src/`, `tests/`, `docs/`, `experiments/`, `benchmarks/`, `validation_results/`,
`statistical_results/`, `v02*_results/`, `benchmark_results/`,
`parallel_statistical_results/`, and every `*.json` / `*.jsonl` / `*.yaml` /
`*.yml` in the repository (38 JSON files outside `.venv`), for the four schema
strings and for the bare tokens `torn_endpoint`, `fixed_point_plan`,
`coupled_iteration`, `coupled_run`.

**Result: 5 files, all of them source or prose — 2 `.py`, 3 `.md`. ZERO
stored, external or persisted payloads exist.** No fixture, no frozen config,
no results archive, no example payload contains a coupling record.

Therefore, **preregistered decision: rename now.** Misleading
`electrothermal_*` names are not preserved for hypothetical backward
compatibility.

| Old | New |
|---|---|
| `electrothermal_torn_endpoint/1` | `coupling_torn_endpoint/1` |
| `electrothermal_fixed_point_plan/1` | `coupling_fixed_point_plan/1` |
| `electrothermal_coupled_iteration/1` | `coupling_iteration/1` |
| `electrothermal_coupled_run/1` | `coupling_run/1` |

Version stays `/1`: the `(name, version)` pair is new, nothing has ever read
`coupling_run/1`, and a bump to `/2` would falsely imply a `/1` once existed.

**If any real payload is discovered during implementation: STOP.** Design an
explicit migration / accepted-version strategy using
`require_schema_any`, record it, and do not silently break the payload.

## 7. Compatibility — two separate questions

**(A) Persisted payloads.** Answered in §6: none. No `require_schema_any`
acceptance of the old names is added.

**(B) Python imports.** Import paths involved:

* `from ..electrothermal.coupled import (CoupledRun, FixedPointCouplingPlan,
  TornEndpoint, run_fixed_point)` — `systems/fluidthermal/coupled.py:95`
* `from src.engcore.systems.electrothermal import coupled as cp` —
  `tests/test_electrothermal_vertical.py:41`, `tests/test_heterogeneous_ngspice.py:48`
* `from engcore.systems.electrothermal import coupled as et` —
  `tests/systems/fluidthermal/test_ft_coupling_execution.py:39`,
  `tests/systems/fluidthermal/test_ft_coupling_records.py:31`
* re-exports in `src/engcore/systems/electrothermal/__init__.py`

All of these are **internal to this repository**. No published API document,
README, example, notebook or external consumer imports the coupling machinery
from `engcore.systems.electrothermal`. **Preregistered decision: update every
call site and remove the false ownership path. No permanent compatibility
shim, no alias module, no re-export of a generic name from a domain-named
pack.** A guard test asserts that `engcore.systems.electrothermal` and
`engcore.systems.electrothermal.coupled` publish no generic coupling name in
their `__all__`.

If implementation surfaces evidence of a published/public import contract, it
is recorded and handled explicitly rather than broken.

## 8. Proposed new package structure

```
src/engcore/coupling/
    __init__.py     the boundary statement + the published surface
    scales.py       G1 G2 G3    comparison-unit admissibility
    graph.py        G4 G8 G9 G10 dependency-graph readers
    plan.py         G5 G6 G7 G14 G15  the pre-execution declaration
    execution.py    G11 G12 G13 G16 G17  the loop and the records it produces
```

Five files, one per existing seam in the source. No file is added that does not
receive relocated code.

## 9. Zero-behaviour-change requirement

The relocation is a **move**. The preregistered requirement is stronger than
"the tests still pass":

* **Z1.** For each of G1–G13, the *executable* source (docstrings stripped) of
  the relocated object is **byte-identical** to its baseline source at
  `ad6e6cd0`. Only module location, module docstrings, object docstrings, and
  the four schema-string literals change. Asserted by a test that reads the
  baseline blob out of git.
* **Z2.** No new field, parameter, default, branch or member is added to any
  relocated object.
* **Z3.** `CouplingOutcome` keeps exactly two members.
* **Z4.** No relaxation, damping, acceleration, Aitken, Anderson, rollback or
  checkpoint identifier appears anywhere in the new package (§12).

## 10. Frozen numerical baselines

Frozen **before implementation**, by
`freeze_baseline.py` run against `ad6e6cd0`, into a JSON digest carrying, per
case: outcome, iteration count, execution order, every iterate change, every
final value, the full per-iteration per-metric value table, every convergence
state, every validation status and check outcome, provenance run id / software
version / bindings / inputs / assumptions, and a SHA-256 of the canonical
serialized `CoupledRun`.

| Case | Declaration | Outcome | Iters | Final torn value (K) | Last iterate change (K) | `to_dict()` SHA-256 (16) |
|---|---|---|---|---|---|---|
| **A** ET nominal, `temperature` metric | `NOMINAL`, seed 300 K, tol 1e-6 K, budget 50 | `criterion_met` | 10 | `338.5770175652607` | `4.7410196657438064e-07` | `b29093d4582e7d07` |
| **A2** ET nominal, `steady_state_temperature` | as A | `criterion_met` | 11 | `341.9534358052658` | `1.396014681631641e-07` | `597ac4ec118a7769` |
| **A3** ET two-stage series | `TWO_STAGE`, 12 V | `criterion_met` | 8 | R1 `328.89814624739336`, R2 `355.08951310521945` | `1.453976210541441e-07` | `8aca9212d61e6e49` |
| **A4** ET overheated | `OVERHEATED`, 12 V, 600 s | `criterion_met` | 25 | `498.9947931081921` | `7.416340395138832e-07` | `abf6217b45dbe2ad` |
| **B** ET non-convergence (CASE C2) | `MARGINAL`, steady-state metric, budget 50 | `iteration_limit_reached` | 50 | `422.54901960784315` | see digest | `b6d014b8a1fcd5c1` |
| **B2** ET budget-2 (CASE C1) | `NOMINAL`, budget 2 | `iteration_limit_reached` | 2 | `337.8580264196312` | see digest | `1e0e265825cb17bb` |
| **B3** ET marginal, `temperature` metric | `MARGINAL`, budget 50 | `criterion_met` | 23 | `377.1383888809374` | `4.6184084112610435e-07` | `119f2ed055194308` |
| **C16** FT nominal n=16 | 6 W, budget 40 | `criterion_met` | 16 | `362.0282839384463` | `5.0614276972282823e-05` | `797fc57bc9d3ca5e` |
| **C32** FT nominal n=32 | 6 W, budget 40 | `criterion_met` | 13 | `355.667840150113` | `9.556225506912597e-05` | `6fb3426e33eec7c7` |
| **C64** FT nominal n=64 | 6 W, budget 40 | `criterion_met` | 12 | `352.1157729997134` | `7.417475899273995e-05` | `268b4997c964245c` |
| **D** FT 40-sweep iteration limit | n=32, 40 W, budget 40 | `iteration_limit_reached` | 40 | `493.99157857158644` | `0.008241125203198862` | `8d6f270f0c68bb19` |
| **E** FT 200-budget convergence | n=32, 40 W, budget 200 | `criterion_met` | **56** | `493.995086273094` | `9.396716853871112e-05` | `4d1d1feb6cdf9eda` |
| **E2** FT one sweep | n=16, 6 W, budget 1 | `iteration_limit_reached` | 1 | `394.9058601536987` | `94.90586015369871` | `1024b54e40029986` |
| **E3** FT four sweeps | n=16, 40 W, budget 4 | `iteration_limit_reached` | 4 | `401.9696019796013` | `312.9500527587752` | `534d49ae6eca1db9` |
| **E4** FT seed 450 K | n=16, 6 W | `criterion_met` | 16 | `362.0283097346873` | `4.330370251182103e-05` | `b5ae56371216ae32` |

Execution order, frozen: ET single stage
`('resistance-tcr-R1', 'electrical_dc:electrothermal-series-R1', 'thermal-lumped-R1')`;
ET two-stage
`('resistance-tcr-R1', 'resistance-tcr-R2', 'electrical_dc:electrothermal-series-R1-R2', 'thermal-lumped-R1', 'thermal-lumped-R2')`;
FT
`('fluid-diffusivity-air-like', 'fluids-transport2d-slab-a', 'wall-conductance-air-like', 'thermal-lumped-body-a')`.

**(F) Admission / validation refusal cases**, frozen by exception type and
message:

| Case | Exception |
|---|---|
| ET tolerance on an affine scale (`degC`) | `InvalidScientificProblem`, "coupling tolerance may not use 'degree_Celsius'…" |
| ET 2:1 fan-in into one endpoint | `InvalidScientificProblem`, "1 endpoint(s) receive more than one…" |
| ET plan with no torn edge | `InvalidScientificProblem`, "a coupling plan must cut at least one edge…" |
| ET seed over a declared condition | `InvalidScientificProblem` from `check_against` |
| FT coarse grid n=8 | `ScientificValidationError`, "admission refused; declared req…" |
| FT cross-check disabled | `ScientificValidationError`, "…not_run…" |

**Gate.** After relocation the same script is re-run and compared field by
field. Required: **byte-identical JSON digest**, including every SHA, except
for the four schema strings, which change exactly as §6 states. **No tolerance
is widened. No comparison is loosened.** A float difference anywhere is a
finding, not an accepted rounding.

## 11. Serialization round-trip

For each of `TornEndpoint`, `FixedPointCouplingPlan`, `CoupledIteration`,
`CoupledRun`, for **both** consumers: `from_dict(to_dict())` reproduces a
record whose `to_dict()` is byte-identical under `json.dumps(sort_keys=True)`,
and whose `outcome` / `iterations_run` / `final_values` / execution order
agree. Both consumers' records must carry the **same four generic schema
identities**; pack-specific payload content (problem ids, metric names,
model references) stays pack-specific and is asserted to differ.

## 12. Two known holes, preserved deliberately

**(a) QuantityDependency field-endpoint leak — DO NOT FIX.** A field-valued
`ScientificVariable` endpoint can still pass the unit check although field
transfer is unsupported. The existing negative/canary test is preserved
**unchanged**. No `ScientificField`, no field endpoint type, no transfer
operator is introduced.

**(b) Relaxation — DO NOT ADD.** `FT-SCALAR-COUPLING` measured 40 sweeps →
iteration limit and 56 sweeps → convergence on the same contracting map with
no relaxation. The new package gains **no** relaxation, damping, acceleration,
Aitken, Anderson, rollback or checkpoint field, parameter or identifier.
Asserted by an AST identifier scan over the whole new package.

## 13. Provenance cleanup — scope, stated in advance

Only naming that became **objectively false** through cross-domain reuse is
corrected: the four schema strings. `ProvenanceRecord` is **not** redesigned.

Success criterion: a records-only reader of a serialized fluid ↔ thermal
`CoupledRun` can identify the coupled run, its participants, its exchange
dependencies and its iteration outcome **without any token telling it the
coupling is electrothermal.** Asserted by scanning the serialized fluid ↔
thermal payload for the substring `electrothermal` and requiring zero hits.

Other provenance gaps carried forward from `FT-SCALAR-COUPLING` (seed not
recoverable from any record; `problem_id → callable` mapping is not a record;
demanded admission sets unserialized; cross-check solver absent from
provenance; per-executor cost in untyped metadata) are **recorded, not
expanded into scope**, unless one of them blocks the relocation.

## 14. Fresh-process reconstruction

For **both** systems, in a genuinely fresh `subprocess` interpreter with no
inherited objects: load the serialized `CoupledRun` from JSON on disk, rebuild
the plan and the run, recompute the dependency order from the records alone,
and confirm outcome, iteration count, final values and torn endpoints. Pack
executors remain pack code and are **not** claimed to be serialized.

## 15. Reviewer and falsifier

`architecture-decision-reviewer` is invoked after the candidate exists, on:
"Did we relocate genuinely shared coupling infrastructure, or create a generic
multiphysics framework prematurely?", comparing **(A)** keep everything under
electrothermal, **(B)** relocate only shared neutral records + execution
helpers, **(C)** move all coupling code into one generic package, **(D)**
promote coupling semantics into universal Core. B is the expected outcome; C
and D require strong proof. The reviewer must inspect both production
consumers.

`architecture-falsifier` is invoked with these eight attacks stated
explicitly: (1) electrothermal assumptions moved into a generic directory;
(2) Fluid↔Thermal shares only scalar fixed-point structure, so the package
fails immediately for another coupling class; (3) schema names generic,
payload semantics still electrothermal; (4) old aliases preserved →
architecture duplicated; (5) persisted records broken despite the claim that
none exist; (6) relocation changed numerical behaviour; (7) the generic
package now owns relaxation/execution policy evidence did not force; (8)
fresh-process reconstruction works only because pack-specific hidden objects
survive. All BLOCKERs closed before evidence is written. ≈2 serious rounds.

## 16. Third-consumer stress — conceptual only

Stressed on paper against Thermal↔Structural, Reaction↔Transport,
Electrical↔Thermal↔Structural (three-way), and Transient Fluid↔Thermal.
**Nothing is implemented, widened, generalized or parameterized to satisfy a
hypothetical consumer.** The output is a survives/fails table.

## 17. Promotion and rejection criteria

**Promote an object into `engcore.coupling`** only if all hold:

1. Both production consumers use it, directly or transitively at runtime.
2. Its executable source contains no domain vocabulary from the §5 list.
3. Neither consumer requires domain-specific behaviour *inside* it.
4. Relocating it changes no number in §10.

**Reject (keep in the pack)** if any of: it names a domain model, metric,
solver or unit; it constructs participants; it extracts domain results; it is
used by exactly one consumer and its second use would require a new parameter.

**Promote into `engcore.scientific` (universal Core):** requires a *universal
reader* of the record that exists today. **Predicted: nothing qualifies; zero
Core files change.**

## 18. Falsification criteria — what makes this milestone fail

The relocation is **rejected and reverted** if any of:

* **F1.** Any frozen number in §10 changes.
* **F2.** Any relocated object needs an edit (beyond docstring and schema
  literal) to serve both consumers.
* **F3.** A domain token from §5 survives in the new package's executable
  source.
* **F4.** A real persisted payload is found under the old schema names.
* **F5.** The new package acquires a domain-specific branch, a relaxation
  knob, or a field/mesh/transfer concept.
* **F6.** Any file under `src/engcore/scientific/` changes.
* **F7.** `architecture-decision-reviewer` returns REJECT, or selects (A).
* **F8.** `architecture-falsifier` returns FALSIFIED with an unclosed BLOCKER.
* **F9.** FULL regression is not 0 failed / 0 errors, or any test is weakened,
  skipped or xfailed to make it pass.
* **F10.** The passing count drops below 2177.

"Relocation is not justified" is an acceptable outcome and is reported plainly.

## 19. Tests

Run, in order: coupling-targeted, Electro↔Thermal, Fluid↔Thermal,
serialization, fresh-process, admission regressions, FAST
(`-m "not expensive"`), then FULL once at the end.

Requirement: **0 failed, 0 errors.** Baseline 2177 passed. The exact delta is
recorded and explained. A pure relocation may legitimately **add** tests; it
must not remove or weaken any. Targeted baseline measured on `ad6e6cd0`:
`tests/test_electrothermal_vertical.py`, `tests/systems/fluidthermal/`,
`tests/test_min_foundation_electrothermal.py`,
`tests/test_heterogeneous_ngspice.py` → **210 passed**.

### 19.1 Tests known in advance to require adaptation

Stated here so no adaptation looks like a convenience afterwards.

* `tests/systems/fluidthermal/test_ft_coupling_records.py::test_the_electrothermal_coupling_machinery_was_not_edited`
  asserts `git diff --name-only <base> -- src/engcore/systems/electrothermal/`
  is empty. This milestone moves code out of that directory, so the assertion
  as written cannot hold. Its **intent** — the machinery was not edited to fit
  the second consumer — is preserved and made *stronger*: the executable
  source of every relocated object must be byte-identical to the baseline blob
  (§9 Z1). The weaker directory-diff form is replaced by the stronger
  byte-identity form; it is not deleted for convenience.
* `test_the_loop_this_pack_uses_is_the_electrothermal_one_by_identity`
  becomes `…_is_the_shared_generic_one_by_identity` and additionally asserts
  the **electro-thermal** pack uses the same objects, i.e. that both consumers
  share one identity.
* `test_the_loop_still_cannot_name_either_science`,
  `test_l3_no_relaxation_appears_anywhere_in_the_module`,
  `test_i2_the_new_module_uses_published_contracts_only` read a hard-coded
  module path; the path moves and the scan is **widened** to the whole new
  package.
* `test_o3_no_existing_schema_version_moved` pins the four old schema strings;
  it is updated to the four new ones and additionally asserts the old names
  appear nowhere in `src/`.
* Imports of generic names in `tests/test_electrothermal_vertical.py`,
  `tests/test_heterogeneous_ngspice.py` and
  `tests/systems/fluidthermal/*` move to `engcore.coupling`.

No test is skipped, xfailed, deleted for convenience, or given a looser bound.

## 20. Strength delta — scored after FULL passes

Re-scored: **Coupling Readiness** (4/5), **Core Stability** (5/5), **Domain
Extensibility** (4/5), **Provenance / Reproducibility** (4/5). No other
dimension.

**A score is not raised merely because files moved.** It is raised only if an
actual ambiguity or false ownership was removed *and* §A–§U measures it. Flat
scores are an acceptable and expected outcome.

## 21. Evidence document

`docs/coupling-pack-relocation-evidence.md`, sections **A–U** as specified:
A inventory · B classification · C files moved · D files deliberately not
moved · E schema rename table · F stored-payload search · G Python import
compatibility · H numerical zero-change proof · I both-consumer object
identity · J serialization · K fresh-process · L provenance naming · M
reviewer verdict · N falsifier verdict · O field-endpoint leak unchanged · P
relaxation not added · Q third-consumer stress · R Core files changed · S
evidence level · T decision status (default **PROPOSED**) · U reversal
triggers.
