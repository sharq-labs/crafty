# COUPLING-PACK-RELOCATION — evidence

Preregistration: `docs/coupling-pack-relocation-prereg.md`, commit `237880d`,
written and committed **alone** before any source file on this branch was added
or edited. Implementation: `03a019a` plus the reviewer- and falsifier-mandated
corrections recorded in §T.

Baseline: `origin/cloud/crafty-post-fluid-thermal` @
`ad6e6cd0833be7161b1575d9b5b5e97d339e4b27`, verified FULL **2177 passed / 0
failed / 0 errors**.

**What this milestone is.** A move. Ownership, module path and four
serialization identities changed. No scientific model, no domain physics, no
solver algorithm, no numerical result, no admission semantics and no validation
semantics changed, and universal scientific Core gained and lost nothing.

**What it is not.** Not a multiphysics framework. `engcore.coupling` is
**domain-neutral coupling execution and composition infrastructure**, and it is
**explicitly not universal scientific semantics** — a distinction stated in the
package's own docstring, in `plan.py`, in `execution.py`, and checked by test
rather than asserted.

---

## A. Pre-relocation inventory

Everything the two production coupled systems used, measured on `ad6e6cd0`
**before** anything moved. All 17 candidates were defined in one file,
`src/engcore/systems/electrothermal/coupled.py` (1 598 lines).

| # | Object | Kind | Baseline lines |
|---|---|---|---|
| G1 | `is_ratio_scale` | function | 177–204 |
| G2 | `shares_origin` | function | 207–216 |
| G3 | `_require_ratio_scale` | function | 219–228 |
| G4 | `edge_key` | function | 231–245 |
| G5 | `CouplingOutcome` | enum | 252–269 |
| G6 | `TornEndpoint` | frozen dataclass | 272–324 |
| G7 | `FixedPointCouplingPlan` | frozen dataclass | 327–566 |
| G8 | `_edges` | function | 573–574 |
| G9 | `execution_order` | function | 577–611 |
| G10 | `cycle_edges` | function | 614–658 |
| G11 | `CoupledIteration` | frozen dataclass | 1026–1095 |
| G12 | `CoupledRun` | frozen dataclass | 1098–1224 |
| G13 | `run_fixed_point` | function | 1379–1565 |
| G14–G17 | the four schema constants | module constants | 159–162 |

Pack-specific objects in the same file, inventoried and **not** candidates:
`DEPENDENCY_HEAT`, `DEPENDENCY_TEMPERATURE`, `DEPENDENCY_RESISTANCE`,
`SOURCE_ID`, `REFERENCE_NODE`, `CoupledStage`,
`CoupledElectroThermalSystem`, `coupled_problems`, `stage_problems`,
`coupled_dependencies`, `nominal_plan`, `build_coupled_twin`,
`_property_result`, `_thermal_result`, `_electrical_result`, `_executors`,
`run_fixed_point_coupling`.

Pack-specific objects in `src/engcore/systems/fluidthermal/`:
`DEPENDENCY_EFFLUX`, `DEPENDENCY_CONDUCTANCE`, `DEPENDENCY_TEMPERATURE`,
`DEPENDENCY_DIFFUSIVITY`, `THERMAL_ADMISSION_REQUIREMENTS`,
`SOFTWARE_VERSION`, `FluidSlice`, `HeatedBody`, `FluidThermalSystem`,
`coupled_problems`, `coupled_dependencies`, `nominal_plan`,
`_diffusivity_result`, `_fluid_result`, `_wall_result`, `_thermal_result`,
`_executors`, `run_fluid_thermal_coupling`, `sweep_timings`, plus all of
`properties.py` and `reference.py`.

### A.1 Two-consumer measurement, made before implementing

Direct AST name usage in production source, and in each consumer's own test
suite, on the baseline commit:

| Object | ET prod | FT prod | FT tests | Reached transitively at runtime by FT |
|---|---|---|---|---|
| `run_fixed_point` | yes | yes | yes | — |
| `FixedPointCouplingPlan` | yes | yes | yes | — |
| `TornEndpoint` | yes | yes | yes | — |
| `CoupledRun` | yes | yes | yes | — |
| `CouplingOutcome` | yes | no | yes (9×) | yes, via `run.outcome` |
| `execution_order` | yes | no | yes (3×) | yes, inside `run_fixed_point` |
| `cycle_edges` | no | no | yes (1×) | **no — see §D.3** |
| `CoupledIteration` | yes | no | no | yes, via `run.iterations` |
| `edge_key`, `_edges` | yes | no | no | yes, via `plan.uncut` / `__post_init__` |
| `is_ratio_scale`, `shares_origin`, `_require_ratio_scale` | yes | no | no | yes, via `plan.__post_init__` |
| the four schema constants | yes | no | no | yes, via `run.to_dict()` |

### A.2 A third caller, found during implementation and recorded

`tests/test_heterogeneous_ngspice.py` (`HETERO-NGSPICE`) is a **third direct
caller of `run_fixed_point`**, and it was not in the preregistered inventory.
It builds the ET composition, swaps **one** entry of the executor table for a
closure that shells out to a real external `ngspice-42` process, and calls
`run_fixed_point` itself with its own `software_version` and no assumptions.

Why it matters, and exactly how much. It exercises the one property the
falsifier called the best-supported piece of the package — the executor as an
opaque `Callable[[Mapping[str, Quantity], str], ScientificResult]`, with an
**external-process provider** behind it — and it does so without one line of
production glue. `run_fixed_point`'s refusal of a result attributed to another
problem, and its union of provenance bindings across every iteration rather
than the last, both exist for that case.

Why it is **not** a third data point about the coupling contract: it is the
*same* coupling class as consumer one — the same ET system, the same three
edges, the same single kelvin tear, the same scalar tolerance — with a
different **provider** behind one participant. It is a third *provider*, not a
third *coupling class*, and §Q's stress is unchanged by it.

Its import was repointed to `engcore.coupling` like every other call site.

**Stated honestly, because the reviewer required it (§M change 3):** after
relocation, each production consumer *directly imports* **4 of the 13**
relocated objects (`CoupledRun`, `FixedPointCouplingPlan`, `TornEndpoint`,
`run_fixed_point`). The other nine are transitive-runtime collaborators reached
through those four. "Two consumers share the coupling package" and "two
consumers share four objects and their call graph" are different claims, and
only the second is measured. It still satisfies the preregistered promotion
rule (§17.1: *directly or transitively at runtime*), and it is weaker than the
first sentence would suggest.

---

## B. Generic-vs-pack classification

Categories per prereg §4: **USC** universal scientific core · **DNCI**
domain-neutral coupling infrastructure · **ET** / **FT** pack-specific ·
**RT** runtime-only · **SER** serialization-only.

| Candidate | Class | Basis (measured) |
|---|---|---|
| `FixedPointCouplingPlan` | DNCI | zero domain tokens in executable source; both consumers construct one |
| `TornEndpoint` | DNCI | both consumers construct one |
| `CoupledIteration` | DNCI + SER | produced by the shared loop for both |
| `CoupledRun` | DNCI + SER | both consumers receive one |
| `CouplingOutcome` | DNCI | both consumers' suites assert on it |
| the four schema strings | SER | §E |
| `run_fixed_point` | DNCI + RT | shared unedited, **by object identity** (§I) |
| `execution_order`, `cycle_edges`, `_edges`, `edge_key` | DNCI | pure readers of `QuantityDependency` |
| iterate-change / stopping criterion | DNCI | an iterate change, never an equation residual; nothing computes the second |
| `is_ratio_scale`, `shares_origin`, `_require_ratio_scale` | DNCI | the rule is "does zero map to zero"; carries no dimension |
| `_executors` (×2) | ET / FT | build closures over domain solvers |
| `R(T)`, `I²R`, `D(T)`, boundary efflux, `hA(Φ_D)` | ET / FT | physics |
| model identities (`LINEAR_TCR_MODEL`, `POWER_LAW_DIFFUSIVITY_MODEL`, …) | ET / FT | domain declarations |
| result extraction (`_property_result`, `_fluid_result`, …) | ET / FT | name domain metrics |
| **anything at all** | **USC** | **zero. Predicted zero; measured zero.** |

**Universal scientific Core count: 0.** Nothing was proposed for, or moved
into, `engcore.scientific`. See §R.

---

## C. Files moved

New package `src/engcore/coupling/`, five modules, one per existing seam in the
source. No module was created that does not receive relocated code, except the
package `__init__.py`, which carries the boundary statement and the published
surface and defines nothing of its own.

| File | Receives | Lines |
|---|---|---|
| `scales.py` | G1 G2 G3 | 76 |
| `graph.py` | G4 G8 G9 G10 | 124 |
| `plan.py` | G5 G6 G7 G14 G15 | 364 |
| `execution.py` | G11 G12 G13 G16 G17 | 492 |
| `__init__.py` | the boundary statement + the published surface | 98 |

`src/engcore/systems/electrothermal/coupled.py`: 1 598 → 705 lines. It now
imports `CoupledRun`, `FixedPointCouplingPlan`, `TornEndpoint` and
`run_fixed_point` from `...coupling` for its own use, and publishes none of
them.

`src/engcore/systems/fluidthermal/coupled.py`: the single import line changed
from `from ..electrothermal.coupled import …` to `from ...coupling import …`.
No other executable change. The dependency inversion
`FT-SCALAR-COUPLING` recorded — a *fluids* pack importing an *electrothermal*
pack to reach a loop that names no domain — is gone.

---

## D. Files and objects deliberately NOT moved

### D.1 All pack physics stays pack-owned

Everything in §A's pack-specific lists. The rule applied: a generic package
may transport identities and values and execute a plan; it must not know that
a transported watt is Joule dissipation, or that a transported kelvin is the
state coordinate of a temperature-dependent resistance. Those statements are
made by the pack that knows the physics.

Concretely retained and **not** genericized: the two **tear rules**, which are
materially different — ET cuts *every* edge whose `target_quantity ==
mat.TEMPERATURE` across N stages; FT cuts the single edge keyed on
`d.target_problem_id == system.diffusivity_problem_id and d.target_quantity ==
prop.TEMPERATURE`. A common owner for those two would need a domain-keyed
branch or a new parameter. That is the measurement that refutes option (C) in
§M.

### D.2 `sweep_timings` and the wall-clock metadata

Left in `systems/fluidthermal/coupled.py`. It reads
`ScientificResult.metadata["coupling_executor_wall_seconds"]`, an untyped bag
this platform rejects by name elsewhere, used there under a stated objection
that `FT-SCALAR-COUPLING` wrote against itself. Moving it would have imported
that objection into a neutral package. Its *serialization* consequence is
recorded in §J.2.

### D.3 `cycle_edges` — published, with the exception recorded

`cycle_edges` is exported from `engcore.coupling` although it satisfies
**neither** limb of the preregistered promotion rule (§17.1, "both production
consumers use it, directly or transitively"). Measured: **zero production
callers** anywhere in `src/` — neither pack invokes it and `run_fixed_point`
does not — and exactly **one** caller in the repository, a Fluid↔Thermal test
asserting the declared cycle really is a 4-cycle.

It is kept published because it is one of three readers of the same graph and
splitting the trio would be churn. This is a **preregistration divergence**,
it is stated in the package's own `__init__.py` beside the import, and
`architecture-decision-reviewer` required that it be stated here rather than
only in a source comment.

### D.4 The two known holes

Neither was fixed; see §O and §P.

---

## E. Schema rename table

| Old | New | Version |
|---|---|---|
| `electrothermal_torn_endpoint/1` | `coupling_torn_endpoint/1` | `/1` |
| `electrothermal_fixed_point_plan/1` | `coupling_fixed_point_plan/1` | `/1` |
| `electrothermal_coupled_iteration/1` | `coupling_fixed_point_iteration/1` | `/1` |
| `electrothermal_coupled_run/1` | `coupling_fixed_point_run/1` | `/1` |

**Version stays `/1`** because the `(name, version)` pair is new. Nothing has
ever read `coupling_fixed_point_run/1`; a bump to `/2` would falsely imply a
`/1` of that name once existed and was readable.

**Divergence from the preregistration, recorded here as prereg §1 requires.**
Prereg §6 preregistered `coupling_iteration/1` and `coupling_run/1`.
`architecture-decision-reviewer` returned ACCEPT WITH CHANGES and required the
correction, on an argument I accept on the merits: `CoupledRun.from_dict`
requires a `FixedPointCouplingPlan` **by containment**, so a
`coupling_run/1` payload is fixed-point-only whatever its name says, and
`CoupledIteration.largest_iterate_change` is a *sweep* quantity with no meaning
under a time-windowed or accelerated scheme. A bare `coupling_run/1` would have
been a name broader than the record's actual semantics — the same class of
error this milestone exists to remove, one order smaller. The correction cost
two string literals; after the first stored payload it would have cost a
migration.

`coupling_torn_endpoint/1` stays scheme-neutral on purpose, and the falsifier
tested that asymmetry and accepted it: a `TornEndpoint` is only ever reachable
by containment inside a `coupling_fixed_point_plan/1`, so the outer version
governs, and a cut edge paired with a seed is what *any* iterative scheme
needs, not only Picard.

**Consequence for a second scheme.** Because the scheme is encoded in the
schema *name* and the record *type* rather than in a field, a second coupling
scheme attaches as a new module plus a new schema family
(`coupling_<scheme>_plan/1`), additively. It does not require a `/2` of
anything shipped here.

---

## F. Stored-payload search

Executed on the baseline commit **before** the preregistration was written, and
re-executed as a permanent test.

Searched: `src/`, `tests/`, `docs/`, `experiments/`, `benchmarks/`,
`benchmark_results/`, `validation_results/`, `statistical_results/`,
`parallel_statistical_results/`, `v024_results/`, `v025_statistical_results/`,
`v026_results/`, `v026_suite_results/`, `v027_suite_results/`, and every
`*.json` / `*.jsonl` / `*.yaml` / `*.yml` in the repository (38 JSON files
outside `.venv`).

Tokens: the four full schema strings, plus the bare tokens `torn_endpoint`,
`fixed_point_plan`, `coupled_iteration`, `coupled_run`.

**Result — 5 files, every one of them source or prose:**

| File | Kind |
|---|---|
| `src/engcore/systems/electrothermal/coupled.py` | source |
| `tests/test_electrothermal_vertical.py` | source |
| `docs/electrothermal-vertical-prereg.md` | prose |
| `docs/electrothermal-vertical-evidence.md` | prose |
| `docs/fluid-thermal-scalar-coupling-evidence.md` | prose |

**ZERO stored, external or persisted payloads.** No fixture, no frozen config,
no results archive, no example payload, no experiment output contains a
coupling record. The prereg's STOP condition (§6: *if any real payload IS
discovered, design an explicit migration*) was therefore never reached and no
`require_schema_any` acceptance of the old names was added.

**The claim is guarded so it cannot rot.**
`tests/test_coupling_pack_relocation.py::test_f_no_stored_payload_carries_a_coupling_schema_string`
re-runs the sweep over every JSON/YAML file outside `.git` and `.venv` on every
test run. If a fixture or archive ever starts carrying a coupling record, it
fails and the compatibility question becomes live again.

**Residual, stated rather than hidden:** the search cannot see payloads outside
this repository, or in a format it does not enumerate. No evidence any exist.

---

## G. Python import compatibility

**Decision: no compatibility shim, no alias module, no re-export.** All call
sites were updated.

Import paths that existed on the baseline, and what happened to each:

| Site | Before | After |
|---|---|---|
| `systems/fluidthermal/coupled.py:95` | `from ..electrothermal.coupled import …` | `from ...coupling import …` |
| `systems/electrothermal/__init__.py` | re-exported 11 generic names | re-exports none |
| `systems/electrothermal/coupled.py` `__all__` | listed 11 generic names | lists none |
| `tests/test_electrothermal_vertical.py` | `cp.<generic>` (90 sites) | `cpl.<generic>`, from `engcore.coupling` |
| `tests/test_heterogeneous_ngspice.py` | `cp.<generic>` (9 sites) | `cpl.<generic>` |
| `tests/systems/fluidthermal/*.py` | `et.<generic>` (19 sites) + `import … electrothermal` | `cpl.<generic>`; the electrothermal import deleted as dead |

**Evidence that no published import contract existed.** No README, no
architecture document, no example, no notebook and no experiment imports the
coupling machinery from `engcore.systems.electrothermal`. Every site was inside
this repository, and every one was updated.

**Precision required by `architecture-falsifier` (C-5), and I restate the claim
rather than rebuild anything.** What was removed is the **re-export**:
`engcore.systems.electrothermal` and `engcore.systems.electrothermal.coupled`
publish no generic coupling name in `__all__`, and two tests assert it
(`test_i3_no_pack_republishes_a_generic_coupling_name`,
`test_neither_pack_republishes_a_generic_coupling_name`). Because
`electrothermal/coupled.py` still imports the four names it uses at module
level — which is ordinary Python, not an alias —
`engcore.systems.electrothermal.coupled.CoupledRun` still *resolves*. A third
pack could still reach it that way and the guards, which check `__all__`, would
not catch it. "Removed the false ownership path" overstates that. The accurate
claim is: **the re-export was removed and is guarded; the module-level import
path resolves as a consequence of Python's import model.**

---

## H. Numerical zero-change proof

Baselines frozen **before implementation** (prereg §10), by a script run
against a clean `git archive` export of `ad6e6cd0`, and re-run unchanged
against the relocated tree. Each case digest carries: outcome, iteration count,
execution order, every iterate change, every final value, the full
per-iteration per-metric value table, every convergence state, every validation
status and per-check outcome, provenance run id / software version / bindings /
inputs / assumptions, and a SHA-256 of the canonical serialized `CoupledRun`.

### H.1 The fifteen cases

| Case | Outcome | Sweeps | Final torn value (K) | Payload SHA-256 (16) before | after | equal |
|---|---|---|---|---|---|---|
| **A** ET nominal, `temperature` | `criterion_met` | 10 | `338.5770175652607` | `31a90bd2de080552` | `31a90bd2de080552` | ✔ |
| **A2** ET nominal, steady-state | `criterion_met` | 11 | `341.9534358052658` | `6bf5438bbb4e5a44` | `6bf5438bbb4e5a44` | ✔ |
| **A3** ET two-stage series | `criterion_met` | 8 | `328.89814624739336`, `355.08951310521945` | `00be3e8d835d55e7` | `00be3e8d835d55e7` | ✔ |
| **A4** ET overheated | `criterion_met` | 25 | `498.9947931081921` | `9b2f5d7d6a996d51` | `9b2f5d7d6a996d51` | ✔ |
| **B** ET non-convergence (CASE C2) | `iteration_limit_reached` | 50 | `422.54901960784315` | `963ff1499ebbb8fe` | `963ff1499ebbb8fe` | ✔ |
| **B2** ET budget 2 (CASE C1) | `iteration_limit_reached` | 2 | `337.8580264196312` | `e29152c1c5f3f595` | `e29152c1c5f3f595` | ✔ |
| **B3** ET marginal, t₀ metric | `criterion_met` | 23 | `377.1383888809374` | `a170c05cdf13bd29` | `a170c05cdf13bd29` | ✔ |
| **C16** FT nominal n = 16 | `criterion_met` | 16 | `362.0282839384463` | `58368c5b246b65dc` | `58368c5b246b65dc` | ✔ |
| **C32** FT nominal n = 32 | `criterion_met` | 13 | `355.667840150113` | `0a818b6a3002abf5` | `0a818b6a3002abf5` | ✔ |
| **C64** FT nominal n = 64 | `criterion_met` | 12 | `352.1157729997134` | `bad8ca66273b3ab4` | `bad8ca66273b3ab4` | ✔ |
| **D** FT 40-sweep limit | `iteration_limit_reached` | 40 | `493.99157857158644` | `68cdc836ad2b51ef` | `68cdc836ad2b51ef` | ✔ |
| **E** FT 200-budget | `criterion_met` | **56** | `493.995086273094` | `072ebf207c88bd70` | `072ebf207c88bd70` | ✔ |
| **E2** FT one sweep | `iteration_limit_reached` | 1 | `394.9058601536987` | `c3530943e4b761f6` | `c3530943e4b761f6` | ✔ |
| **E3** FT four sweeps | `iteration_limit_reached` | 4 | `401.9696019796013` | `d1008825c2a320d7` | `d1008825c2a320d7` | ✔ |
| **E4** FT seed 450 K | `criterion_met` | 16 | `362.0283097346873` | `bfbd3d7f6dfa373a` | `bfbd3d7f6dfa373a` | ✔ |

**15 / 15 identical.** A whole-digest structural diff of the two JSON files
returns **32 differences, and every one of them is a schema string, a raw SHA
that contains a schema string, or the recorded `coupling_home` module path.
Zero unexplained differences.** No value, unit, count, order, convergence
state, validation outcome, provenance field or assumption moved.

Execution orders, unchanged: ET single stage `('resistance-tcr-R1',
'electrical_dc:electrothermal-series-R1', 'thermal-lumped-R1')`; ET two-stage
`('resistance-tcr-R1', 'resistance-tcr-R2',
'electrical_dc:electrothermal-series-R1-R2', 'thermal-lumped-R1',
'thermal-lumped-R2')`; FT `('fluid-diffusivity-air-like',
'fluids-transport2d-slab-a', 'wall-conductance-air-like',
'thermal-lumped-body-a')`.

### H.2 Admission and validation refusals — identical, by exception type and message

| Case | Exception | Before == after |
|---|---|---|
| ET tolerance on an affine scale (`degC`) | `InvalidScientificProblem` — "coupling tolerance may not use 'degree_Celsius'…" | ✔ |
| ET 2:1 fan-in into one endpoint | `InvalidScientificProblem` — "1 endpoint(s) receive more than one of this plan's dependencies…" | ✔ |
| ET plan with no torn edge | `InvalidScientificProblem` — "a coupling plan must cut at least one edge…" | ✔ |
| ET seed over a declared condition | `InvalidScientificProblem` from `check_against` | ✔ |
| FT coarse grid n = 8 | `ScientificValidationError` — "admission refused; declared req…" | ✔ |
| FT cross-check disabled | `ScientificValidationError` — "…not_run…" | ✔ |

The whole refusal map compares equal, byte for byte.

### H.3 A preregistration defect, recorded as a defect and not as a passed gate

Prereg §10 demanded a **byte-identical JSON digest, including every SHA**, and
said "a float difference anywhere is a finding, not an accepted rounding."

**That gate was unachievable as written, and the reason is not the
relocation.** `systems/fluidthermal/coupled.py` stamps
`metadata={"coupling_executor_wall_seconds": str(time.perf_counter() -
started)}` into three of its four executors' results;
`ScientificResult.to_dict` serializes `metadata`; `CoupledIteration.to_dict`
serializes every result; `CoupledRun.to_dict` serializes every iteration. So
wall-clock telemetry is **inside the hashed payload**.

Measured rather than assumed: the same FT case was serialized **twice on the
baseline commit `ad6e6cd0`**, before this package existed, and the two payloads
differ — in `coupling_executor_wall_seconds` and in the fluid domain's own
`wall_seconds_telemetry`, and in nothing else. The comparison in §H.1
therefore normalizes exactly those three keys
(`coupling_executor_wall_seconds`, `wall_seconds_telemetry`, `wall_seconds`)
to a constant before hashing, and normalizes **nothing** scientific.

**Which cases needed the carve-out:** the seven **ET** cases did **not** — an
AST search finds no `metadata=` stamp anywhere in
`systems/electrothermal/coupled.py`, and the ET digests matched under
schema-only normalization. All eight **FT** cases did.

This is a defect in the preregistered gate, not a passed gate, and
`architecture-decision-reviewer` required it be recorded as one. §J.2 records
the consequence for the record's own claims.

---

## I. Both-consumer object-identity proof

`tests/test_coupling_pack_relocation.py::test_i_both_production_consumers_use_the_same_objects_by_identity`
asserts, with `is` and not `==`:

```
etc.run_fixed_point           is cpl.run_fixed_point
etc.FixedPointCouplingPlan    is cpl.FixedPointCouplingPlan
etc.TornEndpoint              is cpl.TornEndpoint
etc.CoupledRun                is cpl.CoupledRun
ftc.run_fixed_point           is cpl.run_fixed_point            (and the rest)
cpl.run_fixed_point           is engcore.coupling.execution.run_fixed_point
cpl.FixedPointCouplingPlan    is engcore.coupling.plan.FixedPointCouplingPlan
cpl.execution_order           is engcore.coupling.graph.execution_order
cpl.is_ratio_scale            is engcore.coupling.scales.is_ratio_scale
```

**No copied equivalent remains.**
`test_i2_no_pack_retains_a_copied_equivalent` walks the AST of **every** module
under `src/engcore` outside the new package and asserts none of the thirteen
relocated names is defined there.
`tests/systems/fluidthermal/test_ft_coupling_records.py::test_the_relocated_machinery_left_no_copy_behind`
repeats it for the two packs specifically.

**`engcore.coupling` imports no science.**
`test_i4_the_generic_package_imports_no_domain_and_no_system_pack` asserts, per
file, that no import target contains `domains` or `systems` and that no
relative import exceeds level 2 (which is the level that reaches
`engcore.<module>`; level ≥ 3 would leave `engcore` entirely). The dependency
direction is inward-only.

### I.1 The move was a move — byte identity against the minting blob

`tests/systems/fluidthermal/test_ft_coupling_records.py::test_the_coupling_machinery_was_relocated_and_not_edited`
reads the blob `ET-VERTICAL` committed —
`git show 6caa1139…:src/engcore/systems/electrothermal/coupled.py` — and
compares the *executable* source (every string constant blanked, via
`ast.unparse`) of all thirteen relocated objects against the new package.

**Result: byte-identical, with exactly one repair.**
`FixedPointCouplingPlan.unsupplied` imports `externally_imposed` by a relative
path, and the code moved one package level closer to `engcore.scientific`, so
`from ...scientific.composition` had to become `from ..scientific.composition`
or resolve to nothing. Both spellings name
`engcore.scientific.composition.externally_imposed`; no value, branch or target
changes. The repair is pinned as a named constant
(`_RELATIVE_IMPORT_REPAIR`) and the test additionally asserts
`repaired == {"FixedPointCouplingPlan"}` — so it is proved to be needed exactly
where the milestone says, and a future edit cannot hide behind it.

This replaces the baseline's
`test_the_electrothermal_coupling_machinery_was_not_edited`, which asserted
`git diff --name-only <base> -- src/engcore/systems/electrothermal/` was empty.
That form measured "not edited to fit the second consumer" only for as long as
the machinery stayed in that directory, and this milestone moves it. The
replacement is **stronger**, not weaker: a directory diff cannot see a
one-token change to a function that stayed put, and the byte-identity form can.
The adaptation was preregistered in §19.1 before it was made.

### I.2 A weaker form of Z1 than preregistered — stated

Prereg §9 Z1 said "docstrings stripped … only … object docstrings and the four
schema-string literals change." As implemented, the comparison blanks **every**
string constant, not only docstrings. So a change to a non-docstring literal —
an error message, the `f"{run_id}-{index}-{problem_id}"` result-id format, the
`f"{p}::{q}"` provenance key separator, a `context=` label — is invisible to
*that* test. Two of those literals are identity-bearing.

They are covered instead by the §H digest, which hashes provenance `run_id`,
`software_version`, `bindings` and `inputs` for all fifteen cases — a change to
either format string would move it. Recorded because
`architecture-falsifier` (C-7) is right that the two forms are not the same
guarantee.

---

## J. Serialization

### J.1 Round-trip, both consumers, same identities

`test_j_every_relocated_record_round_trips_for_both_consumers`, parametrized
over ET and FT, asserts for each:

* every `TornEndpoint` satisfies `from_dict(to_dict()) == self`;
* `FixedPointCouplingPlan`, `CoupledIteration` and `CoupledRun` round-trip to a
  **byte-identical** `json.dumps(..., sort_keys=True)`;
* `CoupledRun` preserves `outcome` (by identity), `iterations_run`, and the
  `final_values` key set.

`test_j2_both_consumers_serialize_under_the_same_generic_identities` asserts
that the ET payload and the FT payload carry the **same four schema strings**
at the same four positions.

`test_j3_the_pack_specific_payload_content_stayed_pack_specific` asserts the
converse: the two runs' participant id sets are **disjoint**, ET names
`electrical_dc:…` and `resistance-tcr-…`, FT names `fluids-transport2d-…` and
`fluid-diffusivity-…`. A shared schema is not a shared payload.

### J.2 What a `coupling_fixed_point_run/1` payload does NOT promise

Recorded here and in `CoupledIteration`'s own docstring, because
`architecture-falsifier` (C-2) is right that the neutral name invites the
stronger claim:

> A `coupling_fixed_point_run/1` payload is **not byte-reproducible** and must
> not be described as digest-stable or content-addressable, for as long as any
> participant writes runtime telemetry into `ScientificResult.metadata`.

`CoupledRun` carries whole `ScientificResult` records, and `metadata` is an
untyped mapping a *participant* owns. One shipped participant (the FT pack)
writes per-executor wall-clock into it. This is a property of that participant,
measured on the baseline before this package existed (§H.3), not a property the
relocation introduced — but it is now attached to a domain-neutral identity, so
it must be stated at that identity.

**Not fixed here.** Removing the telemetry lives in the FT pack, is additive-safe
later, and would move a frozen digest field now.

---

## K. Fresh-process reconstruction

`test_k_the_generic_records_reconstruct_in_a_genuinely_fresh_interpreter`,
parametrized over **both** systems. A `subprocess` interpreter receives **only
JSON on stdin** — the serialized plan and the serialized run — and:

1. rebuilds the `FixedPointCouplingPlan` from `coupling_fixed_point_plan/1`;
2. **recovers the participant set from the run record itself** —
   `run["iterations"][0]["results"][*]["problem_id"]`, since every participant
   is solved in every sweep;
3. recomputes the execution order with `execution_order` over that recovered
   set and the plan's uncut edges;
4. rebuilds the `CoupledRun` and reports its outcome, sweep count and final
   values.

The parent then asserts the recovered participant set equals the composition's
own, and that plan id, schema, torn endpoints, budget, edge count, outcome,
sweep count and every final value (in kelvin, exactly) agree with the
in-process objects.

**The participant set is recovered, not injected.** The first implementation
handed `problem_ids` in from the pack-aware parent, which left prereg §14's
"from the records alone" unproven; `architecture-falsifier` (C-6) caught it and
it was corrected.

`test_k2_the_fresh_process_holds_no_reference_to_either_system_pack` closes
attack (8) directly: after reconstruction, the fresh interpreter's `sys.modules`
contains **zero** `engcore.systems.*` and **zero** `engcore.domains.*` entries,
and the outcome and sweep count are still correct.

The FT pack's own pre-existing fresh-process test
(`test_the_coupled_specification_reconstructs_and_re_executes_in_a_fresh_process`)
additionally re-**executes** the coupling in a fresh interpreter; its import
was repointed to `engcore.coupling` and it still passes.

**Pack executors remain pack code and are not claimed to be serialized.** The
`problem_id → callable` mapping is not a record and could not be one today —
the same finding `ET-VERTICAL` and `FT-SCALAR-COUPLING` both recorded,
unchanged.

---

## L. Provenance naming result

The defect `FT-SCALAR-COUPLING` recorded as falsifier C-4 and named in its §V
as "the cheapest-now / expensive-later item in the milestone" is **closed**.

`test_l_a_fluid_thermal_record_no_longer_calls_itself_electrothermal` asserts,
over the serialized fluid ↔ thermal run:

* the substrings `electrothermal`, `electro-thermal` and `electrical` appear
  **nowhere** in the payload;
* `schema == "coupling_fixed_point_run/1"`;
* the outcome is one of the two members;
* the participant set recovered from the record is exactly the four fluid ↔
  thermal problems;
* the four exchange dependencies are recoverable with their endpoints.

A records-only reader can therefore identify the coupled run, its participants,
its exchange dependencies and its iteration outcome **without being told the
coupling is electrothermal when it is fluidthermal.**

`test_l2_an_electro_thermal_record_is_equally_unbranded` proves the identity is
generic in both directions, while confirming that the ET pack's own problem ids
still say `electrothermal-series` — that is payload *content*, and it is the
pack's to name.

`ProvenanceRecord` was **not** redesigned. Nothing under
`src/engcore/scientific/` changed.

### L.1 Provenance gaps carried forward, recorded and not expanded into scope

Unchanged from `FT-SCALAR-COUPLING`: the torn-endpoint **seed is recoverable
from no record**; the execution mapping `problem_id → callable` is not a record
and could not be one today; **demanded** admission sets do not survive
serialization; the cross-check solver that gates FT admission is absent from
provenance; per-executor cost lives in the untyped `ScientificResult.metadata`
bag. None blocked the relocation, so none was expanded into scope.

### L.2 A provenance rule calibrated on one participant, now platform-wide

`architecture-falsifier` (C-1, SERIOUS) found this, and it is recorded rather
than fixed. `run_fixed_point`'s binding union has a fallback:

```python
if result.provenance.bindings:
    bindings.extend(result.provenance.bindings)
else:
    bindings.extend(
        ExecutionBinding(model=ModelReference(model_id, version),
                         realization=None, solver=result.solver)
        for model_id, version in result.models
    )
```

Its own comment names the motivation — "producers predating MODEL0-R declare
participants without an association. The electrical solver is one." For a
participant returning **several** `models` with empty `provenance.bindings`,
this *manufactures* an association nobody stated: it would claim each model was
bound to `result.solver`. The vocabulary scan cannot see it, because the branch
contains no domain token; it is domain-neutral in spelling and
domain-calibrated in justification.

**Not fixed, for a stated reason.** Provenance bindings are inside the frozen
§H digest, so changing the branch would move a frozen artifact and trip the
milestone's own falsification criterion F1, and it would break the §I.1
byte-identity claim. It was already in the machinery before the relocation; the
relocation neither introduced nor worsened it.

**Reopen trigger, named:** the first participant that returns **multiple**
`models` with an empty `provenance.bindings`.

---

## M. Reviewer verdict

`architecture-decision-reviewer`, invoked on "Did we relocate genuinely shared
coupling infrastructure, or create a generic multiphysics framework
prematurely?", comparing all four options and inspecting both production
consumers.

**Verdict: ACCEPT WITH CHANGES**, selecting **(B) relocate only the shared,
domain-neutral records and execution helpers**.

Its reasons for rejecting the others, each measured rather than argued:

* **(A) keep everything under `systems/electrothermal/`** — refuted by a defect
  the *prior* milestone measured: `fluidthermal` importing `electrothermal`
  inverts the recorded dependency direction ("domain packs depend inward"), and
  the serialization defect stops being fixable at the first stored payload.
* **(C) one generic package owning all coupling code** — refuted by
  measurement: the two tear rules and the two executor tables genuinely differ,
  so a common owner needs a domain-keyed branch or new parameters, and a new
  domain would then have to edit the generic package.
* **(D) promote into universal Core** — refuted by the standing constraint that
  `MIN-FOUNDATION-ET` deferred "a coupling runtime of any kind", by the absence
  of any Core *reader* of a coupling record, and by negative precedent: preCICE
  v3.0.0 **removed** Broyden acceleration, extrapolation and
  `min-iteration-convergence-measure` at a breaking version — the coupling
  scheme surface is the churniest part of a coupling system and the worst
  candidate for Core's strictest versioning.

It also recorded, explicitly, that this is **not** a premature abstraction
under its own gate, because the "no current consumer" condition fails on two
counts.

**The five required changes, and what was done:**

| # | Required | Done |
|---|---|---|
| 1 | Correct the two overclaiming schema names | **Done** — `coupling_fixed_point_run/1`, `coupling_fixed_point_iteration/1` (§E) |
| 2 | `cycle_edges` published on test demand alone — fix or record | **Recorded** (§D.3) and stated in the package `__init__.py` |
| 3 | State the two-consumer evidence honestly: 4 of 13 direct, 9 transitive | **Done** (§A.1) |
| 4 | Record the wall-clock normalization as a prereg defect, per case, and say whether ET needed it | **Done** (§H.3) — ET did not; FT did |
| 5 | Record the topology/policy conflation with its cost curve | **Done** (§U.2) |

**What the reviewer explicitly declined to credit.** The plan shape breaks for
the same four of six structurally different roadmap systems that
`FT-SCALAR-COUPLING` §V measured; the relocation neither improves nor worsens
that, "which is the correct outcome for a move, and it is the reason the
Coupling Readiness score should not move on this milestone." §S follows that.

---

## N. Falsifier verdict

`architecture-falsifier`, invoked with all eight required attacks stated
explicitly.

**Verdict: SURVIVES WITH REQUIRED CHANGES. No BLOCKER.**

| # | Attack | Result |
|---|---|---|
| 1 | Electrothermal assumptions moved into a generic directory | **Landed partially** as C-1 — the provenance-binding fallback is domain-neutral in spelling, domain-calibrated in justification. Recorded in §L.2, not fixed, with a named reopen trigger. |
| 2 | FT shares only scalar fixed-point structure, so the package fails for another coupling class | **Landed as a scope observation, correct and already absorbed.** Both consumers are steady, scalar, single-tear, single-dimension, single-process, no fan-in. What defeats it as a *falsification*: the package is now **named and versioned for exactly that class** (`run_fixed_point`, `coupling_fixed_point_*`), it **refuses** the cases it cannot serve rather than mishandling them, and a second scheme attaches additively. The claim's scope was narrowed to match the evidence. |
| 3 | Schema names generic, payload semantics still electrothermal | **Did not land.** §L: the FT payload contains no `electrothermal`/`electrical` token anywhere, and its participants and edges are recoverable. |
| 4 | Old aliases preserved → architecture duplicated | **Did not land** as stated — two AST sweeps prove no module redefines a relocated object. Survived only in the weakened form C-5, which is a **claim** correction, recorded in §G. |
| 5 | Persisted records broken despite the claim none exist | **Did not land.** §F; the search is now a permanent test. |
| 6 | The relocation changed numerical behaviour | **Did not land** — 15/15 payloads identical (§H) — but required the §H.3/§J.2 concession about wall-clock reproducibility. |
| 7 | The package now owns relaxation/execution policy evidence did not force | **Did not land.** No `omega`/`relax`/`damp`/`aitken`/`anderson`/`rollback`/`checkpoint` identifier anywhere in the package, asserted per-file. |
| 8 | Fresh-process reconstruction works only because pack objects survive | **Did not land** — `sys.modules` in the fresh interpreter contains zero pack and zero domain modules — but exposed C-6, corrected in §K. |

**The six required corrections, and what was done:**

| # | Finding | Severity | Action |
|---|---|---|---|
| C-3 | Two schema guards scanned source with *all string constants blanked*, so they could not find a string literal — guards incapable of failing | SERIOUS | **Fixed in code (tests only).** A `_string_literals` helper collects non-docstring string constants; both guards now scan those, and each additionally proves it *can* fail on a synthetic emitter and does *not* fire on prose. |
| C-8 | FULL regression not supplied; "targeted 151" not reconciled against the preregistered 210 | SERIOUS | **Done** (§Q). 151 was a different selection. The preregistered 4-module selection is now **212** (210 + 2 new guards), and the whole targeted set is **238**. |
| C-4 | Two prereg divergences with no durable record; three source files cite an evidence document that did not exist | SERIOUS | **Done** — this document; divergences in §E and §D.3. |
| C-2 | `coupling_fixed_point_run/1` is not byte-reproducible | SERIOUS (inherited) | **Claim bounded**, in `CoupledIteration`'s docstring and §J.2. FT pack unchanged. |
| C-1 | Provenance rule calibrated on one legacy participant is now platform-wide | SERIOUS | **Recorded** in §L.2 with a reopen trigger; not fixed, because fixing it would move a frozen digest field (F1). |
| C-5 | "Removed the false ownership path" overstates "removed the re-export" | MINOR | **Claim restated** in §G. |
| C-6 | Fresh process was handed the participant set | MINOR | **Fixed in code (tests only)** — recovered from the run record (§K). |
| C-7 | Z1 as implemented is weaker than Z1 as preregistered | MINOR | **Stated** in §I.2. |

Explicitly **not** built, on the falsifier's own recommendation: per-edge
tolerances, a fan-in combination rule, a `CouplingScheme` abstraction, a
participant lifecycle, a transfer operator, a relaxation knob, a `DIVERGED`
enum member, `require_schema_any` acceptance of the old names.

---

## O. The QuantityDependency field-endpoint leak — unchanged

**Deliberately not fixed, per prereg §12(a).** A field-valued
`ScientificVariable` endpoint still passes the unit check although field
transfer is unsupported.

The two canary tests are **preserved unchanged** in
`tests/systems/fluidthermal/test_ft_coupling_records.py`:

* `test_n2_a_field_endpoint_still_checks_clean_and_this_milestone_does_not_fix_it`
* `test_n2_a_field_endpoint_is_refused_by_this_PACK_and_the_guard_is_labelled`

`git diff ad6e6cd0` over that file touches neither — the only changes to it are
import-path rewrites and the two replaced ownership guards (§I.1).

No `ScientificField`, no field endpoint type and no transfer operator was
introduced. `test_p3_no_field_mesh_or_transfer_concept_entered_the_package`
asserts that structurally, over the whole new package.

---

## P. Relaxation — explicitly not added

**Per prereg §12(b).** `FT-SCALAR-COUPLING` measured 40 sweeps → iteration
limit and 56 sweeps → convergence on the same contracting map with **no
relaxation**; those numbers are still frozen, unchanged, as cases **D** and
**E** in §H.1.

`test_p_relaxation_was_not_added_anywhere_in_the_package` walks every
identifier — `Name`, `Attribute`, `arg`, `FunctionDef`, `ClassDef` — in every
module of the new package and asserts none contains `omega`, `relax`, `damp`,
`aitken`, `anderson`, `rollback`, `checkpoint`, `accelerat`, `underrelax` or
`over_relax`.

`test_p2_the_outcome_enum_still_has_exactly_two_members` asserts
`CouplingOutcome` still has exactly `criterion_met` and
`iteration_limit_reached`. No `DIVERGED` member was minted from intuition by
the move.

---

## Q. Third-consumer stress — conceptual only, nothing implemented

Paper analysis. **Nothing was widened, generalized or parameterized to satisfy
a hypothetical consumer.**

| Future system | Verdict | Why |
|---|---|---|
| **Thermal ↔ Structural** | **Survives** | One tear (temperature → thermal strain), scalar, no fan-in. Structurally the same class as both existing consumers — which is why it is a *weak* confirmation, not a third data point. |
| **Reaction ↔ Transport** | **Bends** | Fine on a single torn dimension. Tearing concentration *and* temperature together hits the single-scalar-tolerance limit and is **refused with a stated reason**, not normalized by invention. |
| **Electrical ↔ Thermal ↔ Structural (three-way)** | **Bends / breaks** | Two failure modes, both refusals: two torn dimensions (as above), and 2:1 fan-in into one endpoint, which `FixedPointCouplingPlan.__post_init__` refuses because no record states whether contributions sum, override or split. Three-way couplings routinely need summed contributions. |
| **Transient Fluid ↔ Thermal (implicit, time-windowed)** | **Breaks** | No time window, no checkpoint/rollback, no time synchronization; every participant is re-solved every sweep from identical declared conditions, and `check_against` *actively refuses* to seed a quantity a declared condition determines — i.e. the package refuses to become time marching. A correct refusal. Under a windowed scheme an iteration nests inside a window, which is precisely why `coupling_fixed_point_iteration/1` is scheme-named (§E). |

**Already measured, not hypothetical:** the external-provider case (§A.2). A
real `ngspice` process stands in for one participant behind the opaque executor
contract, with no production glue and no change to the loop.

**What obviously survives** for all four: the participant/dependency/tear
vocabulary; the graph readers; the ratio-scale rule for a comparison unit; the
outcome-vs-solver-convergence separation; provenance references; the
executor-as-opaque-callable contract, which is the best-supported piece —
`run_fixed_point` refuses a result attributed to another problem and unions
bindings across iterations specifically to survive a provider degrading
mid-run.

**What obviously does not:** the single scalar tolerance; the single torn
dimension; the fan-in refusal; the absence of time windows and checkpointing;
the scalar `TornEndpoint.initial_value` and scalar `final_values`, which is
where field-valued exchange breaks (§O).

**This is exactly the four-of-six breakage `FT-SCALAR-COUPLING` §V already
measured.** The relocation neither improves nor worsens it, which is the
correct outcome for a move, and it is the reason §S does not raise Coupling
Readiness.

---

## R. Core files changed

**Zero.**

```
$ git diff --name-only ad6e6cd0 -- src/engcore/scientific/
(empty)
```

Asserted permanently by
`tests/test_coupling_pack_relocation.py::test_r_universal_core_is_untouched`,
and by the pre-existing
`tests/systems/fluidthermal/test_ft_coupling_records.py::test_universal_core_was_not_touched_by_this_milestone`,
which still diffs against `6caa1139` and still returns empty.

`test_r2_no_coupling_name_was_promoted_into_core` additionally asserts that
`engcore.scientific.__all__` and `engcore.coupling.__all__` are **disjoint**,
and that no file under `src/engcore/scientific/` mentions `CoupledRun`,
`FixedPointCouplingPlan`, `TornEndpoint`, `CouplingOutcome`,
`run_fixed_point` or `engcore.coupling` in executable code.

No schema version moved anywhere in Core:
`quantity_dependency/1`, `provenance_record/2`, `execution_binding/1`,
`scientific_result/2`, `raw_solver_output/2` — all unchanged, asserted by
`test_o3_no_existing_schema_version_moved`.

Complete list of files changed against `ad6e6cd0`:

```
docs/coupling-pack-relocation-prereg.md          (new)
docs/coupling-pack-relocation-evidence.md        (new)
src/engcore/coupling/__init__.py                 (new)
src/engcore/coupling/execution.py                (new)
src/engcore/coupling/graph.py                    (new)
src/engcore/coupling/plan.py                     (new)
src/engcore/coupling/scales.py                   (new)
src/engcore/systems/electrothermal/__init__.py
src/engcore/systems/electrothermal/coupled.py
src/engcore/systems/fluidthermal/__init__.py
src/engcore/systems/fluidthermal/coupled.py
tests/systems/fluidthermal/test_ft_coupling_execution.py
tests/systems/fluidthermal/test_ft_coupling_records.py
tests/test_coupling_pack_relocation.py           (new)
tests/test_electrothermal_vertical.py
tests/test_heterogeneous_ngspice.py
```

---

## R2. Test results and the exact delta

Requirement: **0 failed, 0 errors**, no test weakened, skipped or xfailed.
Baseline: **2177 passed**.

| Selection | Baseline `ad6e6cd0` | After | Delta |
|---|---|---|---|
| Coupling-targeted (`tests/test_coupling_pack_relocation.py`) | — | **26** | +26 (new module) |
| The preregistered §19 four-module set — `test_electrothermal_vertical.py`, `systems/fluidthermal/`, `test_min_foundation_electrothermal.py`, `test_heterogeneous_ngspice.py` | **210** | **212** | **+2** |
| Both together | — | **238** | — |
| FAST (`-m "not expensive"`) | — | **1602 passed / 0 failed** | — |
| **FULL** | **2177 passed / 0 failed / 0 errors** | **2205 passed / 0 failed / 0 errors** (20 m 39 s) | **+28** |

### Reconciling the delta, test by test

**+2 in the preregistered four-module set.** Two guards were **added** to
`tests/systems/fluidthermal/test_ft_coupling_records.py`:
`test_the_relocated_machinery_left_no_copy_behind` and
`test_neither_pack_republishes_a_generic_coupling_name`. Two guards were
**replaced in place**, not removed:
`test_the_electrothermal_coupling_machinery_was_not_edited` →
`test_the_coupling_machinery_was_relocated_and_not_edited` (a directory diff
became a byte-identity comparison against the minting blob — strictly
stronger, §I.1), and
`test_the_loop_this_pack_uses_is_the_electrothermal_one_by_identity` →
`…_is_the_shared_generic_one_by_identity` (now asserted for **both** packs, not
one). Both replacements were preregistered in §19.1 **before** they were made.

**+26 from the new module.** `tests/test_coupling_pack_relocation.py`, 26
tests, all new, none replacing anything.

**+28 in FULL = 26 + 2, and it reconciles exactly.** 2177 → 2205. The new
module contributes 26 and the two added Fluid↔Thermal guards contribute 2.
Nothing else in the repository gained or lost a test.

**Nothing removed, weakened, skipped or xfailed.** No `pytest.mark.skip`, no
`xfail`, no widened tolerance, no deleted assertion anywhere in the diff. Two
assertions were made *stronger* (the two replacements above) and two guards
that could not fail were repaired so that they can (falsifier C-3, §N) — each
now additionally proving, on a synthetic input, that it fires on a real
offender and stays quiet on prose.

**A note on the two working-tree guards.**
`tests/test_exec_spec_structured_input.py::test_h_no_universal_core_or_committed_evidence_was_modified`
and `tests/test_executable_scientific_spec.py::test_no_src_file_was_added_or_edited`
compare `git diff --name-only HEAD -- src/`, i.e. the **uncommitted working
tree**. They fail on any milestone while its `src/` changes are unstaged and
pass once committed. `FT-SCALAR-COUPLING` modified `src/` the same way and
added no exception registry, for the same reason. No exception was added here
either, and none was needed.

---

## S. Evidence level

**EXECUTED, for a move.** Every claim in §H, §I, §J, §K, §L, §O, §P and §R is
produced by code that ran, not by argument:

* the numerical gate compares two JSON digests produced by the *same script*
  run against a clean `git archive` of the baseline and against the relocated
  tree;
* byte identity is compared against the actual git blob, not against a copy;
* object identity is asserted with `is`;
* fresh-process reconstruction runs in a real `subprocess` with a proven-empty
  pack/domain module set;
* the stored-payload search is a permanent test, not a one-off grep.

**What this evidence does NOT establish, stated plainly.** Two consumers of one
coupling *kind* is an executable proof performed twice, not an architectural
proof. Both are steady, scalar, single-dimension, single-tear, single-process,
with no fan-in, no persisted artifact and no external provider. The claim this
milestone can carry is: *the shared machinery is genuinely shared, the
ownership boundary is correct, the serialized identity is honest, and no number
moved* — for scalar single-dimension steady fixed-point coupling. No more.

§Q's paper analysis is **conceptual only** and is labelled as such.

---

## T. Decision status

**PROPOSED.**

`architecture-decision-reviewer`: ACCEPT WITH CHANGES — all five made (§M).
`architecture-falsifier`: SURVIVES WITH REQUIRED CHANGES, no BLOCKER — all six
made (§N), of which two were code changes and both were test-only.

Nothing here is frozen. `engcore.coupling` is a *placement*, not a contract
freeze: the four schema identities are new, nothing has read them, and the
records they name are known to be narrow.

---

## U. Reversal triggers

Any one of these reopens the decision.

1. **A real persisted payload appears under a coupling schema name.**
   `test_f_no_stored_payload_carries_a_coupling_schema_string` fails, and the
   compatibility question in §F becomes live: the correct response is an
   explicit `require_schema_any` migration, not a silent break.
2. **The byte-identity gate fails.**
   `test_the_coupling_machinery_was_relocated_and_not_edited` fails, or
   `repaired != {"FixedPointCouplingPlan"}`. Then this was a redesign wearing
   the name of a move, and the relocation must be re-argued on its merits.
3. **A domain token, domain import or domain branch enters
   `engcore.coupling`.** Any of `test_q*`, `test_i4` fails. The package name
   becomes false in exactly the way `electrothermal` was.
4. **A relaxation, acceleration, checkpoint or rollback identifier enters the
   package**, or `CouplingOutcome` gains a member, without a *measurement* that
   forced it. `test_p`, `test_p2` fail.
5. **Any file under `src/engcore/scientific/` changes for a coupling reason.**
   `test_r`, `test_r2` fail. Promotion into universal Core requires a universal
   *reader* that does not exist today.
6. **A third coupling class arrives that the boundary cannot serve without
   editing the generic package.** Then option (C) or a scheme-layer split
   becomes live, and the reviewer's rejection of (C) must be re-run against the
   new consumer.
7. **A participant returns multiple `models` with empty
   `provenance.bindings`.** The manufactured-association rule in §L.2 starts
   inventing attribution, and it must be fixed — at which point the frozen §H
   digest for that field is renegotiated deliberately.
8. **A consumer branches on `ScientificResult.metadata`'s wall-clock keys**, or
   a `coupling_fixed_point_run/1` payload is treated as content-addressable.
   §J.2's bound is violated and the telemetry needs a typed home.
9. **The topology/policy split becomes necessary.** See §U.2.
10. **Any frozen number in §H moves**, or FULL drops below the recorded count,
    or a test is weakened, skipped or xfailed to keep it green.

### U.1 What is cheap now and stops being cheap

Everything in §E and §U.9 is currently free **because zero payloads exist**.
That is a decaying fact. The first stored `CoupledRun` converts every remaining
naming or shape question into a migration.

### U.2 A recorded open item: topology and execution policy in one record

`FixedPointCouplingPlan` serializes both sides of a separation this platform's
own preCICE study reached as one of its strongest conclusions — a *physics
graph* (scientific dependencies and transfers) and an *execution plan*
(ordering, iterations, tolerances, budgets, time windows, checkpoint policy)
are independent objects. The record carries `dependencies` + `torn`
(topology) alongside `absolute_tolerance` + `max_iterations` (policy).

**This is pre-existing from `ET-VERTICAL` and unchanged by the relocation.**
Z1/Z2 forbade fixing it here and no measurement forces it. It is recorded
because the rename moment was when it would have been cheapest to split, and
because the cost curve is the same as §U.1's: free today, a migration after the
first stored payload.

---

## V. Post-milestone strength delta

Re-scored: the four dimensions the mission named, and no others. Same 0–5 scale
as the prior audits.

**A score is not raised because files moved.** It is raised only if an actual
ambiguity or false ownership was removed *and* §A–§U measures it.

| Dimension | Before | After | Basis |
|---|---|---|---|
| **Coupling Readiness** | 4/5 | **4/5 (unchanged)** | Nothing about *coupling capability* changed. No new coupling class executed, no third consumer, no relaxation, no fan-in rule, no time window, no field transfer. §Q measures the same four-of-six breakage `FT-SCALAR-COUPLING` §V measured, unchanged. `architecture-decision-reviewer` said so explicitly: "the relocation neither improves nor worsens that… which is the reason the Coupling Readiness score should not move on this milestone." Holding it flat is the finding. |
| **Core Stability** | 5/5 | **5/5 (unchanged)** | **Zero files under `src/engcore/scientific/`**, measured against `ad6e6cd0` and against `6caa1139`, asserted by two tests. No Core schema version moved. No new Core record, no new Core enum member. Already at ceiling and held there through a 1 145-line deletion and a 2 173-line addition. Cannot rise. |
| **Domain Extensibility** | 4/5 | **4/5 (unchanged)** | A real friction was **removed** — a new coupled pack now imports `engcore.coupling` instead of a domain-named `systems/electrothermal`, restoring "domain modules depend inward", which is precisely the packaging defect `FT-SCALAR-COUPLING` §V recorded and named as the next milestone's subject. That is worth stating and it is **not worth a point**: a third coupled pack still inherits every shape limit in §Q, must still write its own participant construction, executor table, dependency declarations and tear rule, and the two tear rules that stayed pack-side are the measurement proving that is unavoidable. Extensibility of the *packaging* improved; extensibility of the *coupling* did not, and only the second is what this dimension scores. |
| **Provenance / Reproducibility** | 4/5 | **4/5 (unchanged)** | The one defect this milestone closes is real and was named by the prior milestone: a fluid ↔ thermal run no longer serializes under `electrothermal_coupled_run/1`, and §L proves a records-only reader recovers run, participants, edges and outcome with no misattributing token. Against that, **three things argue directly against raising it, two of them newly measured by this milestone's own falsifier**: (i) every gap that held it at 4 is unchanged — the seed is recoverable from no record, `problem_id → callable` is not a record, demanded admission sets are unserialized, the cross-check solver is absent from provenance, per-executor cost is in an untyped bag; (ii) **new** — §J.2: a `coupling_fixed_point_run/1` payload is *not byte-reproducible*, because a participant writes wall-clock into `ScientificResult.metadata`, which is inside the hashed payload; a reproducibility dimension cannot rise on a milestone that had to document that its records are not digest-stable; (iii) **new** — §L.2: the provenance-binding fallback manufactures an association nobody stated, for any participant returning multiple models with empty bindings. Honest naming was gained; reproducibility was not. |

**Overall reading.** Four dimensions re-scored, **none moved.** That is the
correct outcome for a milestone that deliberately changed ownership, naming and
serialization identity and nothing else — and it is the outcome the reviewer
predicted before the scores were written. The milestone's value is that a false
ownership boundary and a false serialized identity were removed **while they
still cost three string literals and a directory move**, and that the two
adversarial passes converted two vague claims into measured ones (§J.2, §L.2)
and two unfalsifiable guards into falsifiable ones (§N, C-3).
