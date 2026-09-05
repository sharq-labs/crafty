# TRUST-HARDENING — Evidence

**Milestone:** `TRUST-HARDENING`
**Kind:** hardening. **No new physics, no new domain, no new universal contract.**
**Decision status:** PROPOSED. **Evidence:** `L1 EXERCISED` for the executed behaviour;
`L0 REASONED` for every classification. **No `L2`. No freeze.**
**Branch:** `trust-hardening` **Baseline:** `053902e` (PROPULSION0-EXT)
**Preregistration:** `docs/evidence/trust-hardening-preregistration.md`, committed
**alone** at `437b2b8` before any source file was touched. Immutable; nothing below is
back-written into it.

> Written after execution. Where a preregistered prediction failed it is recorded as a
> deviation with the measurement that refuted it. Where the change set exceeded what was
> preregistered, that is recorded as a deviation too, at full strength, rather than
> quietly widened.

---

# 0. Headline

**The shipped execution path can no longer hand a caller a result whose model is not
declared valid at the state the run reached.** Measured at the public boundary, varying
only supply voltage on the canonical request:

| V | before | after |
|---|---|---|
| 5.0 | `executed`, 342.4 K, all `pass`, `model_validity.assessed: false` | `executed`, **`assessed: true`, `R1=in_domain`** |
| 10.0 | `executed`, 433.1 K, all `pass`, not assessed | `executed`, `assessed: true`, `in_domain` |
| 11.5 | `executed`, 464.0 K, all `pass`, not assessed | `executed`, `assessed: true`, `in_domain` |
| 12.0 | `executed`, 474.5 K, all `pass`, not assessed | **`execution_failed` · `scientific_admission_refused` · `result: null`** |
| 24.0 | `executed`, 742.0 K, all `pass`, not assessed | **refused** |
| 48.0 | `executed`, 1300.9 K, all `pass`, **coupling did not converge** | **refused** |

`LINEAR_TCR_MODEL` declares validity over `200–450 K`. Before this milestone, 24 V
returned a resistance computed 292 K outside that range as an ordinary successful
execution.

**The three concepts stayed separate.** No `ValidationCheck` carries an applicability
verdict; no `ValidityAssessment` was mapped into a `ValidationReport`; no
`ValidationLevel` member was added; `is_usable` and `ValidationReport.status` are
byte-identical on refused runs. Operational safety was **not built** — nothing in the
tree declares what this resistor may survive, and inventing a declarer was refused.

**The second headline is less comfortable.** The change set exceeded the preregistered
one by two test call sites (§3), and the milestone's own numerical gate — enforcement
point (a) — fires on **zero** of every operating point measured. It is defence in depth,
and saying so is part of the result.

---

# 1. P2 — reproducibility lock

## 1.1 The drift was not what anyone assumed

`test_h_the_frozen_numerical_baselines_are_unchanged` failed at baseline:

```
assert 362.0282839384465 == 362.0282839384463     # 2 ULP
```

The preregistration recorded the drift as deterministic and not thread-related
(identical at `OPENBLAS_NUM_THREADS` ∈ {1,2,4,24}). Execution located the actual axis:
**OpenBLAS `DYNAMIC_ARCH` runtime kernel dispatch.** Sweeping `OPENBLAS_CORETYPE` at
fixed numpy 2.4.3 / scipy 1.18.0 / Python 3.14.2 / CPU / source tree:

| kernel | value |
|---|---|
| Haswell · Zen · default | `362.0282839384465` |
| Nehalem · Barcelona | `362.0282839384464` |
| Core2 · Prescott | `362.02828393844646` |
| Sandybridge | `362.02828393844635` |

Four distinct doubles for one unchanged computation. **A lockfile would not have
prevented this and would not detect the next one** — every value above was produced at
one fully pinned version tuple. `pyproject.toml`'s lower-bound-only policy therefore
stands, unchanged.

`iterations_run == 16` and `outcome == CRITERION_MET` were **invariant across every
kernel**, which is the empirical basis for keeping decisions at exact equality.

## 1.2 What the assertion actually was

The FT run declares `absolute_tolerance = 1.0e-4 K` and terminates at
`final_iterate_change = 5.06e-05 K`. The frozen literal pinned to `~2.3e-13 K` — nine
orders tighter — while the docstring said *"No tolerance is widened, because none is
used."* A tolerance was in use.

That assertion was not a falsification criterion. **It was a machine fingerprint**: it
fires on a fact with no scientific content and cannot distinguish a physics regression
from a kernel dispatch change, so a red result was uninterpretable.

## 1.3 The repair

Three strengths, by what each quantity is:

- **decisions** (`CouplingOutcome`, `iterations_run`, `execution_order`) — exact.
- **converged values** — `pytest.approx(rel=1e-13)`: ~180× the measured 5.5e-16
  cross-kernel spread, and 2.7e6 times **tighter** than the run's own convergence
  tolerance. Proven non-vacuous: the band rejects a 1e-12 relative move and a 1 mK move.
- **`final_iterate_change`** — deleted, not re-banded. `run_fixed_point` terminates
  precisely when `largest <= tolerance`, so asserting it is within tolerance is already
  implied by the `CRITERION_MET` assertion above it. Asserting it twice is not evidence.

Every loosened assertion carries a failure message naming the resolved stack.

## 1.4 The environment is now recorded

`ProvenanceRecord.environment` has existed, typed and serialized, since the record was
minted, and **no producer in the tree filled it**. All three participants of the exposed
execution now carry it:

```
{'python': '3.14.2', 'numpy': '2.4.3', 'scipy': '1.18.0', 'blas_architecture': 'Haswell'}
```

Recovered in a fresh process from the serialized record alone, with
`engcore_modules == []`. `blas_architecture` is included because version strings alone
are **measurably insufficient**: the four values in §1.1 would have recorded
byte-identical environments.

Nothing is auto-collected. No hostname, path, user or timestamp — `provenance.py`'s
collect-nothing policy is correct on privacy grounds and stands. Only the resolved
numerical stack, which is a scientific input to the answer.

---

# 2. P1 — admission enforcement

## 2.1 The design, and the constraint that produced it

Applicability may not live in `ValidationReport` (the ruling), on `ScientificResult` or
`CoupledRun` (both pinned to zero diffs against preregistration commits), in
`ScientificResult.metadata` (an untyped escape hatch), or be computed by the application
layer (`test_api_mcp_v0.py:882` forbids it, because that would be *"a scientific act
performed by a layer that did not execute the science"*).

What remained was a **pack-owned record in the pack that executed the science** —
`AdmittedCoupledRun`, the same shape `systems/propulsion.DriveRun` already ships.
Ephemeral, unserialized, not a universal contract, with deletion criteria written into
its docstring.

## 2.2 Two enforcement points, at two different times

| | numerical validation | scientific applicability |
|---|---|---|
| what | `require_admission` against declared requirements | `assess_resistance_validity` at the converged state |
| when | **inside** the loop, per sub-solve | **after** the loop, once |
| on failure | raises out of the loop; no result transported | records a verdict; refuses only at transport |

**They cannot share a mechanism, and the reason is measured.** The coupling is
Gauss-Seidel from a seed, so iterates overshoot the fixed point and re-approach it:

| V | sweeps | peak iterate | converged | verdict |
|---|---|---|---|---|
| 9.0 | 16 | 443.4 K | 402.9 K | in domain |
| 10.0 | 18 | **477.1 K** | 421.0 K | **in domain** |
| 10.6 | 19 | **499.0 K** | 432.1 K | **in domain** |
| 11.0 | 20 | **514.3 K** | 439.6 K | **in domain** |
| 12.0 | 22 | 555.0 K | 458.7 K | outside |

**Four of eight swept points are legitimate in-domain answers whose intermediate iterates
leave the domain by up to 64 K.** An applicability refusal inside the loop would have
destroyed all four; a `WARNING` per iterate would have marked all four suspect.
Assessment reads `run.final_values` and nothing else.

Assessment reports. Admission refuses. They are separate functions because the same
verdict is a finding to one caller and a stop to another.

## 2.3 The refusal is classified as scientific

`ScientificValidationError` raised on the execution stage was previously caught as
`SUBSOLVER_EXECUTION_FAILED` → **HTTP 500**, which `crafty_http/server.py:67-68`
documents as *"the caller did nothing wrong … nothing scientific is claimed"*. Both
halves are false for this refusal. It now classifies as
`SCIENTIFIC_ADMISSION_REFUSED` → **422**, *"the document was understood and the science
was refused"*.

## 2.4 What did not move

- **P1-3.** The assessed and unassessed paths were run side by side and compared as
  serialized records — every value, provenance entry and check. **Bit-identical.** The
  guard costs nothing on the honest path.
- **P1-4.** `is_usable`, `validation.status` and `attained_levels` are unchanged on
  refused runs. A numerically fine but inapplicable result still reports
  `is_usable == True` on its own record. That is the separation working.
- **P1-5.** A refused run's records still construct, serialize, round-trip and yield
  their values. **A failed run is still evidence**; refusal happens at transport, never
  at construction.

---

# 3. Deviations

## 3.1 The change set exceeded the preregistered one — two test call sites

The preregistration named `tests/test_api_mcp_v0.py` as permitted for **`test_h2` only**.
Two further tests in that module required edits, both mechanical:

| test | why | edit |
|---|---|---|
| `test_the_projection_is_far_smaller_than_the_internal_record` | serialized `prepared.run(...)`, whose return type changed | `.run` added |
| `test_the_projection_refuses_to_understate_a_computation` | read `.final` off the same value | `.run` added |

Neither changes an assertion or a tolerance; both measure exactly what they measured
before, on the `CoupledRun` now carried inside the returned record. **They were still
outside the preregistered set**, and the honest reading is that §1.3 of the
preregistration was drawn one line too narrowly: changing the return type of a published
protocol method has call sites, and the preregistration should have said so.

`test_h_the_five_distinctions_are_separately_representable` also asserted
`assessed is False`. That is the same fact `test_h2` records and was foreseen in
substance if not by name; it is now strengthened to assert that validity and coupling
convergence **disagree** across two cases, which is what that test exists to prove.

## 3.2 `test_h2` was updated, and its load-bearing assertion was not

Its first two assertions recorded a measured negative finding — *the executed coupled
path produces no model-applicability verdict* — which this milestone makes false by
construction. They now assert the verdict produced.

**Its third assertion is unmodified and still passes:** the application layer never names
Crafty's validity assessment. That was the real content of the original test, and it
survives intact because the verdict is computed one package away and only projected.

## 3.3 Three historical scope guards were repaired

Preregistered (P1-0) and measured by probe before any change: exactly three, and no
fourth appeared once the change was real.

```
test_propulsion0.py::test_gate_no_pre_existing_domain_or_pack_was_modified
test_propulsion0_ext.py::test_ext_gate_no_pre_existing_domain_or_pack_was_modified
test_composite_system0.py::test_t6f_the_working_tree_changed_only_where_the_prereg_said_it_would
```

Each reads `git diff <its own prereg commit> HEAD` over whole trees and therefore fails
for every later milestone that touches one, however correct. **The repository already
carried this repair five times; this is the sixth.** The form is the narrowest available:
this milestone's files are named individually, so a stray edit anywhere else in those
trees is still loud, and not one file those milestones assert unchanged is excluded.

---

# 4. The residue this milestone does not close

**P1-8, preregistered rather than discovered.** The verdict covers the state the model
was *evaluated at*, which is not every number the response publishes. The coupling
transports `final_temperature`; the response also publishes `steady_state_temperature`.

| V | transported (assessed) | published steady-state | verdict | published value |
|---|---|---|---|---|
| 11.0 | 439.6 K | **453.6 K** | in domain | **outside domain** |
| 11.5 | 449.1 K | **464.0 K** | in domain | **outside domain** |

At 11.0 V and 11.5 V the verdict reads *in domain* — correctly, because the resistivity
model was only ever evaluated inside its declared range — while the response publishes a
steady-state temperature outside it. **This milestone is not total coverage.**

Not closed here because closing it means asserting one model's validity range against
another model's reported output, which conflates two models' domains — the exact
confusion the ruling exists to prevent. The published steady state is an **extrapolation
beyond the state that was coupled**, and naming that is a separate question with its own
declarer.

---

# 5. Predictions

| # | Prediction | Outcome |
|---|---|---|
| P1-0 | exactly three guards need repair | **HELD** — measured by probe, and no fourth appeared |
| P1-1 | 5/10/11.5 delivered; 12/24/48 not consumable | **HELD** |
| P1-2 | flip monotone, strictly between 11.5 V and 12.0 V | **HELD** — ten points, one transition, no oscillation |
| P1-3 | no number changes on an admitted run | **HELD** — serialized records bit-identical |
| P1-4 | validation semantics identical before and after | **HELD** |
| P1-5 | refused records construct, serialize, round-trip, read | **HELD** |
| P1-6 | refusal surfaces as 422, never 500 | **HELD** |
| P1-7 | numerical admission fires on zero swept runs | **HELD** — and recorded as a limitation, not a success |
| P1-8 | the published-metric residue is not closed | **HELD** — measured and named |
| P2-1 | 7 long-float equalities across 3 files | **HELD** — AST scan reproduced |
| P2-2 | ET literals still hold; only FT needed banding | **HELD** |
| P2-3 | environment on every participant, records-only recoverable | **HELD** |
| P2-4 | recording the environment changes no number | **HELD** |
| P3-1 | two runs differ in declaration, not only in numbers | **HELD** |
| P3-2 | projection additive; existing keys unchanged | **HELD** |

**No prediction was refuted.** That is a weaker statement than it looks: fifteen
predictions written by the same author who wrote the implementation, three days after
that author's own earlier design was refused by a ruling. The predictions that would have
been most informative — P1-7 and P1-8 — are the two that record limitations, and both
were written into the preregistration precisely because they were expected to be
uncomfortable.

---

# 6. What was not built

Every item below was available, and each was refused on a measured or ruled ground:

- a `ValidationCheck` for applicability, or any mapping of `ValidityStatus` into a report
- a `ValidationLevel` rung (`PHYSICALLY_APPLICABLE`, `OPERATIONALLY_SAFE`)
- a device rating, insulation class, duty envelope, or any operational-safety declarer
- a `declarer` / `authority` field on `ConstraintDefinition`
- an `ExecutionManifest`, or any field on `CoupledRun` or `FixedPointCouplingPlan`
- a lockfile or exact version pins; a numerical-reproducibility framework
- an experiment framework, fault framework, field framework, or new solver layer
- auto-collected git commit, timestamp, hostname or machine identity

Also **not** repaired, and carried forward as an open finding with its reproduction
attached: a value can be declared on an edge, transported by the loop, recorded in
provenance, and **never read by the executor**, with the run reporting `CRITERION_MET` —
measured at 4000.0 A against a true 3076.92 A. The obvious guard was measured and
rejected: its invariant is *"a `__getitem__` occurred"*, not *"the value influenced the
result"*, and two executors were constructed that pass it while ignoring the transported
value. Closing it with a check that cannot fail would be worse than leaving it named.

---

# 7. Regression

Baseline FAST at `053902e`: **1917 passed / 3 failed / 1920 selected.** The three
failures are environmental and pre-existing, itemised in the preregistration §1.4: an
untracked file in the working tree, a Windows path-separator assertion, and a cp1252
decode of `git show`.

After the milestone: **1917 passed / 3 failed / 1920 selected**, plus
`tests/test_trust_hardening.py` — **21 tests, all passing.** The same three environmental
failures, and **no new failure**.

## 7.1 FULL

**2563 passed / 4 failed / 1 skipped, 783.42 s** (sequential, `-p no:randomly`).

**The count is exactly the delta the preregistration commits to.** The sealed baseline
figure is 2547 (`docs/CRAFTY_MASTER_CONTEXT.md` §71); this milestone adds 21 tests;
`2547 + 21 = 2568`, and `2563 + 4 + 1 = 2568`. No test was deleted, skipped or
de-selected to reach it.

**All four failures are environmental and none is caused by this milestone.** Three were
declared in the preregistration §1.4. The fourth is new *to this document* but not new to
the tree — it is marked `expensive`, so the baseline FAST measurement never ran it:

| test | cause | proven how |
|---|---|---|
| `test_ft_coupling_records::…relocated_and_not_edited` | `subprocess.run(text=True)` decodes `git show` as cp1252; a UTF-8 byte kills the reader thread | declared at baseline |
| `test_composite_system0::test_t6f` | one untracked file in the working tree (`docs/architecture-study/08_CRAFTY_SELF_AUDIT.md`), which this milestone did not create and did not remove | declared at baseline; the guard's stray list names that file and nothing of this milestone's |
| `test_executable_scientific_spec::…boundary_condition_channel…` | Windows `\` vs `/`; six sibling sites in the suite guard this, two do not | declared at baseline |
| `test_api_mcp_v0_transports::test_nothing_a_request_can_say_launches_a_process_and_then_one_legitimately_does` | `OSError [WinError 50]` from `subprocess.Popen` — the sandbox blocks process launch, and the test's second half exists to launch one | **measured**: the milestone's source changes were stashed and the test fails identically on the baseline tree |

The fourth was not asserted to be pre-existing on the strength of its traceback. It was
stashed-and-re-run, because "it looks environmental" is the reasoning that lets a real
regression through.

## 7.2 Scope gates, measured after the fact

Zero files changed under `src/engcore/scientific/`, `src/engcore/coupling/`,
`src/engcore/domains/`, `src/engcore/systems/fluidthermal/`,
`src/engcore/systems/propulsion/`, `src/crafty_http/` and `src/crafty_mcp/` — F6 through
F9 all hold. Total change set: **10 files, 526 insertions, 49 deletions.**

Every deleted assertion is accounted for and preregistered: two `model_validity` negative
findings (§3.2, the milestone's own evidence), one exact ET literal now carried as a
declared band, two `final_iterate_change` freezes deleted under §4.2's tautology
argument, and two whole-tree guard predicates now allow-listed by file (§3.3). **No
assertion was weakened and no tolerance loosened outside those.**

Public surface grew by exactly five names, all in one system pack:
`AdmittedCoupledRun`, `assess_coupled_applicability`, `require_coupled_admission`,
`run_admitted_coupling`, `scientific_environment`.
