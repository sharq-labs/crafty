# TRUST-HARDENING — enforcing existing trust concepts on the reachable path: preregistration

**Written before any source change.** To be committed alone and not amended. Every
number below is either a **declaration** (measured on the unchanged tree at `053902e`,
stated so it can be re-measured) or a **prediction** (stated so a measurement can
contradict it). Each is labelled. Nothing here is back-written after execution.

| | |
|---|---|
| Baseline commit | `053902e` (PROPULSION0-EXT, KEEP, `PROPOSED / L1 EXERCISED`) |
| Sealed records not to be rewritten | `docs/evidence/propulsion0-evidence.md`, `docs/evidence/propulsion0-ext-evidence.md` |
| Scope | **P1** admission enforcement · **P2** reproducibility lock · **P3** execution identity |
| Measured FAST at baseline | 1917 passed / 3 failed / 1920 selected (all three failures environmental, itemised in §1.4) |
| Kind | hardening. **No new physics, no new domain, no new universal contract.** |

**Purpose, stated once.** This milestone does **not** create a validation concept. It
enforces that trust concepts which already exist cannot be bypassed on the one execution
a consumer can reach.

**Epistemic ceiling.** Nothing here is validated against hardware. The `200–450 K` bound
this milestone acts on is the declared fit range of `LINEAR_TCR_MODEL` — a *model
validity* statement. It is **not** a device rating, and this milestone introduces none.

---

## §0 The architectural ruling this preregistration is written under

The three concepts stay separate. They are not merged, not collapsed into one status,
and not expressed through one another.

| Concept | Question | Where it lives | Touched by this milestone? |
|---|---|---|---|
| **Numerical validation** | Did the computation execute correctly? | `ValidationReport` / `ValidationCheck` | **semantics unchanged** |
| **Scientific applicability** | Is this model valid at this physical condition? | `ValidityAssessment` / `ValidityStatus` | assessed and carried, **never as a check** |
| **Operational safety** | Is this result acceptable for real usage? | nowhere — no declarer exists | **not built** |

Required direction of flow:

```
Solver Result
      ↓
Numerical Validation
      ↓
Scientific Applicability Assessment
      ↓
Admission Decision
      ↓
Consumer
```

**This supersedes the earlier draft of this document.** That draft proposed composing the
applicability verdict into a `ValidationReport` as a `ValidationCheck`. It is **withdrawn**.
The draft itself preregistered this exact stop condition, naming the broad reading of
`domains/electrical/material.py:438-444` —

> Kept as its own function, deliberately outside the solver's `ValidationReport`. *Was
> this model applicable* and *was this result checked* are different questions, and the
> platform keeps them on **different fields** for exactly that reason.

— and committing to stop if that reading was operative. **It is operative.** The
withdrawal is recorded here rather than deleted, because a preregistration that quietly
replaces a refuted design is not a preregistration.

Consequence: `ValidationCheck`, `ValidationReport`, `ValidationOutcome`, `ValidationLevel`
and `attained_levels` are **untouched in both code and meaning**. No check named
`model_applicability` is created. No `ValidationLevel` rung is added.

---

## §1 Fail conditions (any one is STOP-and-report, not a workaround)

### 1.1 Concept-separation gates — new, and the reason this milestone exists

| # | Condition |
|---|---|
| **F1** | a `ValidationCheck` is created that reports an applicability, validity-domain or safety verdict |
| **F2** | `ValidityAssessment` or `ValidityStatus` is converted into, mapped onto, or stored inside a `ValidationReport` |
| **F3** | a `ValidationLevel` member is added, or `attained_levels` changes meaning |
| **F4** | `ValidationReport.status` or `ScientificResult.is_usable` changes semantics, or begins to depend on applicability |
| **F5** | an operational-safety concept appears — a device rating, insulation class, duty limit or any (C) declarer |

F4 is the sharpest. `is_usable` is documented as "the absence of known problems, not the
presence of proof", and it is derived from convergence and validation only. **A result
that is numerically fine but scientifically inapplicable must keep `is_usable == True`.**
That is not a bug to fix; it is the separation working. Admission is what refuses it.

### 1.2 Scope gates

| # | Condition |
|---|---|
| **F6** | any byte of `src/engcore/scientific/` changes |
| **F7** | any byte of `src/engcore/coupling/` changes |
| **F8** | any byte under `src/engcore/domains/` changes |
| **F9** | any byte of `src/engcore/systems/fluidthermal/` or `src/engcore/systems/propulsion/` changes |
| **F10** | a new schema string is minted, or an existing schema version is bumped |
| **F11** | an existing assertion is weakened, or a tolerance loosened, other than where §4 declares and justifies it |

F6–F8 are not stylistic. `tests/test_api_mcp_v0.py:1046` asserts a zero diff of
`src/engcore/scientific/` **against `PREREG_COMMIT = 3f2e6dd`, not against HEAD** — a
permanent history guard that committing does not clear. `src/engcore/domains/` is
constrained to a named additions set whose own guard comment states that extending it
weakens the claim that only the RCE repair edited a pre-existing file there.

### 1.3 The permitted change set — exhaustive

```
src/engcore/systems/electrothermal/coupled.py          P1, P2   (not pinned by any guard)
src/engcore/application/executions/electrothermal_series.py  P1
src/engcore/application/contract.py                    P1, P3
src/engcore/application/service.py                     P1
tests/test_coupling_pack_relocation.py                 P2
tests/test_api_mcp_v0.py                               P1  (test_h2 only — see §5.3)
tests/test_propulsion0.py                              guard repair — see §5.4
tests/test_propulsion0_ext.py                          guard repair — see §5.4
tests/test_composite_system0.py                        guard repair — see §5.4
tests/test_trust_hardening.py                          new
docs/evidence/trust-hardening-preregistration.md       this file, committed alone
docs/evidence/trust-hardening-evidence.md              written after execution
```

Anything outside this list is an F-condition.

### 1.4 Baseline failures that are NOT this milestone's to fix

Declared so a red suite is not mistaken for a regression:

| test | cause | class |
|---|---|---|
| `test_composite_system0.py::test_t6f` | untracked files in the working tree | local tree |
| `test_executable_scientific_spec.py::…boundary_condition_channel…` | Windows `\` vs `/`; six sibling sites guard this, two do not | portability |
| `test_ft_coupling_records.py::…relocated_and_not_edited` | `subprocess.run(text=True)` decodes `git show` as cp1252 | portability |

---

## §2 What is already proved and is NOT re-attempted

The admission mechanism exists and is correct. `ValidationReport.admission_issues` /
`is_admissible` / `require_admission` cross-reference
`ScientificProblem.validation_requirements` against named checks and treat `NOT_RUN` as
unsatisfied. It is **already enforced in production** at five call sites —
`systems/fluidthermal/coupled.py:631, :718, :785` and
`domains/fluids/transport2d/validation.py:361, :392` — under a rule that pack states at
`coupled.py:59-68`:

> ADMISSION IS ENFORCED BY THE PRODUCER, NOT BY THE LOOP.

That design is not re-litigated. **This milestone propagates an existing pattern to the
one execution a consumer can reach.** It does not invent one.

Equally not re-attempted: the opt-in decision. `require_admission` is not automatic *at
construction* because "a failed run is still evidence", and that reason is correct and
survives untouched. Every record this milestone refuses still **constructs, serializes,
round-trips and yields its values** to any consumer that asks for it deliberately.

---

## §3 The carrier problem, and why one pack-owned record is forced

Under §0, the applicability verdict may not live in `ValidationReport`. It must still
reach the admission decision. Every other candidate home is eliminated by a measured
constraint, not by preference:

| Candidate home | Eliminated by |
|---|---|
| `ValidationReport` / a `ValidationCheck` | §0 ruling — F1, F2 |
| a new field on `ScientificResult` | `engcore/scientific/` pinned to a zero diff against `3f2e6dd` — F6 |
| a new field on `CoupledRun` | `engcore/coupling/` — F7 |
| computed in the application layer | `tests/test_api_mcp_v0.py:882` asserts `"assess_resistance_validity" not in source` across the application package, because that "would have been a scientific act performed by a layer that did not execute the science" |
| `ScientificResult.metadata` | untyped escape hatch; the platform's own §59.2 fitness question 5 names this as a finding |

What remains is a **pack-owned record in the system pack that executed the science** —
the same shape `systems/propulsion` already ships as `DriveRun`
(`coupled: CoupledRun`, `thermal_masses`, `accounting: EnergyAccounting | None`).

> **This is precedent-following, not a new abstraction.** It introduces no universal
> contract, no schema, no serialization, and nothing outside
> `systems/electrothermal/`. It is ephemeral, exactly as `DriveRun` is.

**Deletion criteria, stated now.** The record is deleted, and its contents folded back,
if any one of these becomes true: (a) `ScientificResult` or `CoupledRun` gains a typed
applicability field in a later milestone permitted to edit core; (b) a second system pack
needs the same carrier, at which point the right move is to promote it rather than
duplicate it; (c) the admission decision is found to need nothing but the `CoupledRun`.

---

## §4 P2 — Reproducibility lock (executed first, because it gates measurement)

Priority order is P1 → P2 → P3. **Execution order is P2 first**, for one reason: the
suite is red at baseline on a numerical assertion, and the blast radius of P1 cannot be
measured against a red suite.

### 4.1 The declaration

`tests/test_coupling_pack_relocation.py::test_h_the_frozen_numerical_baselines_are_unchanged`
**fails at `053902e`**:

```
assert 362.0282839384465 == 362.0282839384463     # fluid-thermal, 2 ULP
```

The electro-thermal half of the same test — `338.5770175652607`,
`4.7410196657438064e-07` — **passes**. Measured invariant across
`OPENBLAS_NUM_THREADS` ∈ {1, 2, 4, 24}: identical at every thread count, so the drift is
**deterministic on this machine** and is not summation-order nondeterminism. Stack:
numpy 2.4.3 / scipy 1.18.0 / Python 3.14.2, BLAS `scipy-openblas 0.3.31.dev`.

The plan the FT run executes declares `absolute_tolerance = 1.0e-4 K` and terminates at
`final_iterate_change = 5.06e-05 K`. The frozen literal pins to `~2.3e-13 K` — about nine
orders tighter than the criterion the run itself declares — while the docstring states
"No tolerance is widened, because none is used." **A tolerance is in use.**

When that number moves, nothing in the record distinguishes *the science changed* from
*the numerical stack changed*. A falsification criterion that cannot separate those is
not measuring the science.

### 4.2 The change

- **Decisions** — `CouplingOutcome`, `iterations_run`, `execution_order` — keep exact
  equality. They are choices, not computed doubles.
- **Converged values** — a declared relative band, justified in the evidence document
  from a measured cross-environment span, and required to stay far tighter than the run's
  own `absolute_tolerance`.
- **`final_iterate_change`** — deleted, not re-banded. `coupling/execution.py` terminates
  precisely when `largest <= tolerance`, so `0 < change <= tolerance` is already implied
  by the `CRITERION_MET` assertion above it. Asserting it twice is not evidence.
- Every loosened assertion carries a **failure message capturing the numerical stack**:
  `numpy.__version__`, `scipy.__version__`, `platform.python_version()`, and the
  `architecture` / `version` lines from `numpy.show_runtime()`.
- **The scientific environment is recorded on the result**, satisfying P2's requirement
  that a result can be recreated with its stack: `systems/electrothermal/coupled.py`
  passes an `environment` mapping into the `ProvenanceRecord` it already constructs. The
  field already exists, already serializes, and is filled by **zero** of the tree's
  producers today.

### 4.3 Predictions

> **P2-1.** The exposure is small enough that no framework is warranted. **Declared
> measurement**, by AST scan over every module in `tests/`, counting float operands of an
> `==` comparison carrying ≥ 15 significant digits: **7 assertions across 3 files** — 4 in
> `test_coupling_pack_relocation.py`, 2 in `test_k31_predictive_admission.py`, 1 in
> `test_sria_m43_coherence.py`. (A regex over decimal literals alone finds 6; it misses
> `4.7410196657438064e-07`. The AST count is the one to reproduce.) **Falsified if** a
> re-scan finds materially more.

> **P2-2.** After the change, `test_h` passes **and** the electro-thermal literals still
> hold at their original exact values — the repair loosens only what measurement shows to
> be environment-dependent. **Falsified if** the ET literals must also be banded.

> **P2-3.** `ProvenanceRecord.environment` is non-empty on every result the exposed
> execution produces, and a fresh process can read the numpy/scipy/BLAS identity from the
> serialized record alone, importing no domain module. **Falsified if** any result ships
> an empty `environment`.

> **P2-4.** Recording the environment changes **no number**. **Falsified if** any output
> magnitude moves.

**Explicitly refused:** a lockfile or exact version pins. Pinning versions does not pin
the SIMD kernel selected at load time from CPUID; the drift occurred at a fixed version
tuple. It would neither have prevented this nor detect the next one. The lower-bound-only
policy in `pyproject.toml:10-12` stays. **Reproducibility here is an attribution claim,
not a determinism claim, and the docstring must say so.**

---

## §5 P1 — Admission enforcement

### 5.1 The declaration

`electrothermal.series_self_heating/1` is the only execution v0 exposes.
`LINEAR_TCR_MODEL` declares validity over `200.0 – 450.0 K`
(`domains/electrical/material.py:162-163`). `assess_resistance_validity`
(`material.py:435`) computes the verdict correctly and has **zero callers on the executed
path**.

Measured through the public `handle()` boundary, varying only `source_voltage` on the
canonical request:

| V | status | steady-state T | participants | coupling outcome |
|---|---|---|---|---|
| 5.0 | executed | 342.426 K | pass | criterion_met |
| 10.0 | executed | 433.105 K | pass | criterion_met |
| 11.0 | executed | **453.579 K** | pass | criterion_met |
| 12.0 | executed | **474.495 K** | pass | criterion_met |
| 24.0 | executed | **741.993 K** | pass | criterion_met |
| 48.0 | executed | **1300.924 K** | pass | **iteration_limit_reached** |

The 48 V row carries two independent trust failures at once: the coupling did not
converge, and every participant still reports `pass` inside a response marked `executed`.

### 5.2 The change — two enforcement points, at two different times

**(a) Numerical-validation admission — producer-side, inside the loop.** Each of the
three executors in `systems/electrothermal/coupled.py` reads its own result through
`result.validation.require_admission(problem.validation_requirements, context=…)` before
returning it, exactly as `systems/fluidthermal/coupled.py:631, :718, :785` already do. A
failing declared requirement raises out of the loop and **no result is transported**.

Where a problem builder declares no requirements, the requirement set is declared
**consumer-side in the pack**, following the shipped precedent at
`systems/fluidthermal/coupled.py:130-134` and labelled in its own docstring as "a
consumer-invented requirement, weaker evidence than a producer-published one". Editing
the domain builders to publish them is **F8** and is not done.

**(b) Applicability admission — after the loop, on the converged state only.** The pack
computes a per-component `ValidityAssessment` from the converged run and carries it on
the pack-owned record of §3. The **admission decision** then reads both the numerical
verdict and the applicability verdict and refuses consumption when either fails.

The assessment itself **reports and never refuses**; the *decision* refuses. That is the
separation the ruling requires, and it is why (b) cannot be folded into (a).

### 5.3 Why (b) must be after the loop — derived before building

The coupling is Gauss-Seidel from a seed; intermediate iterates overshoot and re-approach
the fixed point, so an iterate may leave the validity domain while the converged answer
sits inside it. Measured per-sweep on the unchanged tree:

| V | sweeps | peak iterate | final iterate | converged |
|---|---|---|---|---|
| 9.0 | 16 | 443.442 K | 402.912 K | in domain |
| 10.0 | 18 | **477.089 K** | 421.030 K | **in domain** |
| 10.6 | 19 | **498.977 K** | 432.147 K | **in domain** |
| 11.0 | 20 | **514.278 K** | 439.647 K | **in domain** |
| 12.0 | 22 | 555.008 K | 458.665 K | outside |

**Four of eight swept points are legitimate, in-domain converged answers whose
intermediate iterates leave the domain by up to 64 K.** An applicability refusal inside
the loop would destroy all four. This is measured, not argued, and it is the reason (b)
is post-loop while (a) is in-loop: **numerical validity is a property of each sub-solve at
the iterate it ran at; applicability is a property of the converged state alone.**

### 5.4 Two permitted test edits, each preregistered with its justification

**`test_api_mcp_v0.py::test_h2`.** It asserts `model_validity.assessed is False` and
`"NOT_RUN" in reason`, on the stated ground that "the executed coupled path produces no
model-applicability verdict". P1 makes that ground false by construction. The test is
updated to assert the verdict the execution now produces. **This is strengthening, not
weakening**: `assessed: True` carrying a real per-component verdict is strictly more than
`assessed: False`. Its third assertion — `"assess_resistance_validity" not in source`
across the application package — **must stay green and unmodified**, because the pack
computes the verdict and the boundary only projects it.

**Three historical scope guards.** Measured by probe (files touched, guards run, files
restored): the permitted change set trips exactly three —

```
tests/test_propulsion0.py::test_gate_no_pre_existing_domain_or_pack_was_modified
tests/test_propulsion0_ext.py::test_ext_gate_no_pre_existing_domain_or_pack_was_modified
tests/test_composite_system0.py::test_t6f_the_working_tree_changed_only_where_the_prereg_said_it_would
```

Each reads `git diff <its own prereg commit> HEAD` over trees including
`src/engcore/systems/electrothermal/` and `src/engcore/application/`, and therefore fails
for **every** later milestone that touches them, however correct. **The repository already
carries this exact repair five times**, and the repair is always the narrowest available:
this milestone's files are named **individually**, so a stray edit anywhere else stays
loud. No assertion is changed and no tolerance loosened.

> **P1-0.** Exactly three guards need repair, and no fourth appears once the change is
> real. **Falsified if** a fourth guard trips, or if any guard can only be satisfied by
> widening a tree rather than naming a file.

### 5.5 Predictions

> **P1-1.** After P1, at fixed canonical request varying only `source_voltage`: 5.0 V and
> 10.0 V are delivered as before; 12.0 V, 24.0 V and 48.0 V are **not consumable** —
> `handle()` does not return them as an ordinary executed result carrying numbers.
> **Falsified if** any of the five disagrees.

> **P1-2.** The transition is monotone in `source_voltage` and lies strictly between
> 11.5 V and 12.0 V, because the transported temperature crosses 450 K between 449.111 K
> and 458.665 K. **Falsified if** the flip is non-monotone or falls outside that interval.

> **P1-3.** P1 changes **no number** on any admitted run. Every value in every delivered
> response is bit-identical before and after. The enforcement costs nothing on the honest
> path. **Falsified if** any admitted output moves by one ULP.

> **P1-4.** `ValidationReport.status`, `attained_levels` and `is_usable` are **identical
> before and after** for every one of the swept runs, including the refused ones. A
> numerically fine but inapplicable result still reports `is_usable == True` on its own
> record. **Falsified if** any of the three moves — that would mean applicability leaked
> into validation, which is F4.

> **P1-5.** A refused run's records still construct, serialize, round-trip and yield their
> values when read deliberately. **Falsified if** any refused record cannot be built or
> read.

> **P1-6.** The refusal is classified as a **scientific** refusal, not an internal defect.
> `ScientificValidationError` reaching the boundary today is caught as
> `SUBSOLVER_EXECUTION_FAILED` → HTTP 500, which `crafty_http/server.py:67-68` documents
> as "the caller did nothing wrong … nothing scientific is claimed" — both false.
> `SCIENTIFIC_ADMISSION_REFUSED` → 422 already exists and is the correct code.
> **Falsified if** any refusal introduced here surfaces as 500.

> **P1-7.** Enforcement point (a) fires on **zero** of the swept runs. Measured: 2197
> executed requests produced 0 non-pass validations. It is defence in depth, and the
> evidence document must say so rather than imply it carries the milestone.
> **Falsified if** (a) fires on a nominal request — which would be a finding worth more
> than the prediction.

### 5.6 A known limitation, preregistered rather than discovered

The applicability verdict covers **the state the model was evaluated at**, which is not
every number the response publishes. `thermal_lumped` reports two metrics; the coupling
transports `final_temperature` while the response also publishes
`steady_state_temperature`. Measured on the unchanged tree:

| V | transported (assessed) | published steady-state | verdict | published value |
|---|---|---|---|---|
| 11.0 | 439.647 K | **453.579 K** | in domain | **outside domain** |
| 11.5 | 449.111 K | **463.988 K** | in domain | **outside domain** |
| 12.0 | 458.665 K | 474.495 K | outside | outside |

> **P1-8.** P1 does **not** close this. At 11.0 V and 11.5 V the verdict reads *in
> domain* — correctly, because the resistivity model was only ever evaluated inside its
> declared range — while the response publishes a steady-state temperature outside that
> range. **This is a stated residue, not an implementation defect**, and the evidence
> document must record it at full strength rather than report total coverage.

It is not closed here because closing it means asserting one model's validity range
against another model's reported output, which conflates two models' domains — the exact
confusion §0's ruling exists to prevent. The honest framing is that the published steady
state is an **extrapolation beyond the state that was coupled**, and naming that is a
separate question with its own declarer.

---

## §6 P3 — Execution identity

Scoped deliberately small, and last. The manifest is **not** a missing contract: a fresh
process importing zero engcore modules replayed a whole shipped coupled run from existing
records at 0 ULP. What the published record drops is the declaration it executed.

- `application/contract.py::_participant` publishes the executed `inputs` from the
  provenance the result already carries.
- It also publishes each participant's `checks[]` — name, outcome, `establishes`,
  residual, tolerance — fields that are exactly `ValidationCheck`'s own.

> **P3-1.** Two responses for a 5 V and a 10 V run of the same execution currently differ
> only in their numbers and never in what they say was run. After P3 they differ in the
> published `inputs`. **Falsified if** the two responses remain indistinguishable in
> declaration.

> **P3-2.** P3 adds fields and removes none; every existing key keeps its meaning and its
> value. **Falsified if** any existing response key changes.

**Not built:** an `ExecutionManifest` record, a request echo, auto-harvested git commit /
timestamp / hostname (the provenance module's collect-nothing policy is correct on privacy
grounds and stands), or any field on `CoupledRun`.

---

## §7 Presumed unnecessary — reaching for any of these is a visible deviation

- an experiment framework, fault framework, field framework, or new solver layer
- a device rating, insulation class, duty envelope, or any operational-safety declarer
- a `declarer` / `authority` / `constraint_kind` field on `ConstraintDefinition`
- a generic constraint-evaluation service, rule engine, or limits framework
- per-endpoint coupling tolerances, or any relaxation of the single-dimension torn-set rule
- a universal `Material`, `ComponentInstance`, `Port` or `Connector`

---

## §8 What this milestone does not claim

- **It does not close applicability for the platform.** It closes it for the one execution
  a consumer can reach. `systems/propulsion` remains unassessed and unreachable; hardening
  a pack no consumer can reach improves no consumer's trust.
- **It does not make admission automatic.** Records still construct and are still
  readable. What changes is that the *shipped execution path* will not hand a caller a
  result that failed admission.
- **It does not repair the transported-but-unconsumed hole.** A value can be declared on
  an edge, transported, recorded in provenance, and never read by the executor, with the
  run reporting `CRITERION_MET` — measured at 4000.0 A against a true 3076.92 A. The
  obvious guard was measured and rejected: its invariant is "a `__getitem__` occurred",
  not "the value influenced the result". Carried forward as an open finding with its
  reproduction attached, not closed with a check that cannot fail.
- **It does not touch the EV-axle blocker.** `coupling/plan.py:215-221` refuses a torn set
  spanning two dimensions, which is what a shared DC bus requires. The refusal is correct
  and `engcore/coupling/` is F7.

---

## §9 Acceptance

**KEEP** only if all of the following hold:

1. No F-condition fired — in particular F1–F5, the concept-separation gates.
2. `test_c4_validity_and_validation_are_kept_apart` passes **unmodified**, and
   `solver.validate` still emits exactly `{"resistance_strictly_positive"}`.
3. `test_h2`'s third assertion — `"assess_resistance_validity" not in source` across the
   application package — passes **unmodified**.
4. P1-1 … P1-8, P2-1 … P2-4, P3-1, P3-2 all hold as stated, or each failure is recorded as
   a deviation with the measurement that refuted it.
5. Exactly three historical guards were repaired, each by naming files individually
   (P1-0).
6. The FULL suite delta is exactly the number of tests added, with no pre-existing
   assertion changed beyond the two edits §5.4 declares.

A prediction that fails is recorded at full strength. **A failed prediction is the
milestone working, not the milestone failing.**

---

## §10 Evidence ceiling

`L1 EXERCISED` for the executed behaviour of P1, P2 and P3 on this tree. `L0 REASONED`
for every classification and recommendation. **No `L2`**: this milestone enforces one
model's applicability on one execution. `systems/fluidthermal` already implements the
admission pattern, which is *precedent* — not a second independent measurement of this
change.

**No freeze. No promotion of any existing holding.**
