# ADMISSION-GATE-REPAIR — Evidence

**Milestone:** `ADMISSION-GATE-REPAIR`
**Kind:** correction. **No new physics, no new domain, no new universal contract.**
**Decision status:** PROPOSED. **Evidence:** `L1 EXERCISED` for the executed behaviour;
`L0 REASONED` for every classification. **No `L2`. No freeze.**
**Branch:** `trust-hardening` **Baseline:** `31ddcc7` (EXECUTION-IDENTITY preregistration)
**Preregistration:** `docs/evidence/admission-gate-repair-preregistration.md`, committed
**alone** at `c5c7c70` before any source file was touched. Immutable; nothing below is
back-written into it.

> Written after execution. Two predictions failed and one declaration in the
> preregistration was itself wrong; each is recorded below as a deviation with the
> measurement that refuted it. The change set was widened twice, on the owner's explicit
> decision, and that is recorded at full strength rather than quietly absorbed.

---

# 0. Headline

**Enforcement point (a) now exists.** `TRUST-HARDENING` preregistered it, its evidence
document published it as shipped, and it was never written.

```
at 31ddcc7:  grep -rn "require_admission" src/engcore/systems/electrothermal/  ->  (nothing)
now:         coupled.py:613  report.require_admission(PROPERTY_ADMISSION_REQUIREMENTS, ...)
             coupled.py:671  report.require_admission(THERMAL_ADMISSION_REQUIREMENTS, ...)
             coupled.py:766  result.validation.require_admission(problem.validation_requirements, ...)
```

**The gate is not inert, and that is the finding this milestone did not predict.** It fires
on one shipped, exercised case — `test_api_mcp_v0.py`'s CASE F — and changes that case's
published refusal from `subsolver_execution_failed` (HTTP 500) to
`scientific_admission_refused` (HTTP 422). §3.2 argues the new code is the correct one.

**A correction to a sealed record, made here rather than by rewriting it.**
`docs/evidence/trust-hardening-evidence.md` §2.2 tabulates enforcement point (a) as one of
"two enforcement points", with an `on failure` of *"raises out of the loop; no result
transported"*. **No such call existed.** Its headline — the gate *"fires on zero of every
operating point measured"* — is true of an absent gate as much as of an inert one, and no
measurement in that milestone could tell the two apart, because its own regression test
could not (§2). That document is **not edited**; this section is the correction.

---

# 1. What was changed

Three call sites and two module constants in one file, plus tests.

| site | gated against | source of the requirement |
|---|---|---|
| `_property_result` (`coupled.py:613`) | `PROPERTY_ADMISSION_REQUIREMENTS` = `{"resistance_strictly_positive"}` | **consumer-invented** — `electrical.material` publishes none |
| `_thermal_result` (`coupled.py:671`) | `THERMAL_ADMISSION_REQUIREMENTS` = `{"lumped_balance_residual"}` | **consumer-invented** — `thermal_lumped` publishes none |
| `_electrical_result` (`coupled.py:766`) | `problem.validation_requirements` — six names | **producer-published**, `dc/problem.py:184` |

The consumer-invented label is the shipped precedent's, reused verbatim
(`systems/fluidthermal/coupled.py:132-136`). Neither constant is exported; `__all__` is
byte-unchanged and the public surface did not grow.

`_electrical_result` gained a `problem` parameter and gates the result the `circuit_solver`
seam returned, so both shipped profiles are gated identically and neither adapter was edited.

---

# 2. The superseded test, and what it could and could not see

`test_trust_hardening.py::test_p1_7` passed `{check.name for check in
result.validation.checks}` as its requirement set — derived from the result under test.

**Measured, with `ValidationReport.require_admission` replaced by `return None`:**

| perturbation | superseded form | replacement form |
|---|---|---|
| the **gate** removed | **PASSES** — blind | n/a; `test_admission_gate_repair.py::test_c` and `::test_f` **FAIL** |
| a declared check **withheld** (`NOT_RUN`) | FAILS — detects it | FAILS — detects it |
| a declared check **removed** from the report | **PASSES** — blind | **FAILS** — detects it |

**Deviation D-A — the preregistration's §1.4 overstated the defect.** It claimed the old
assertion read *"every check that ran, ran — true of any result, on any tree"*. That is
**false**, and the middle row above refutes it: a withheld check stays in the report, so it
stays in the derived set, and the original does catch it. The original was blind in exactly
two ways, not universally: a declared requirement **vanishing**, and the gate's own
existence — the second being the one it was named for. Recorded rather than repaired,
because the preregistration is immutable.

---

# 3. Predictions

| # | Prediction | Outcome |
|---|---|---|
| P-1 | exactly three call sites | **HELD** — `coupled.py:613, 671, 766` |
| P-2 | swept behaviour byte-unchanged | **HELD** — see §3.1 |
| P-3 | the gate fires on nothing | **HELD as written** (every swept point) — **but see §3.2** |
| P-4 | the replacement tests can fail | **HELD** — measured by removal, §2 |
| P-5 | the superseded test was blind to the gate | **HELD** — measured, §2 |
| P-6 | regression delta is exactly the tests added, **and no pre-existing test changes outcome except `test_p1_7`** | **FALSIFIED on its second clause** — `test_api_mcp_v0.py::test_f` changed outcome (§3.2), which is what forced W-1. The count clause holds (§7). |
| P-7 | no scope guard fires | **FALSIFIED** — §3.3 |
| D-1 | `test_p1_7` passes against a stubbed gate | **MEASURED**, not assumed — §2 |

## 3.1 P-2 — both profiles, unchanged

Measured through the public boundary, `handle(request)`, varying only supply voltage:

| V | native | ngspice | TRUST-HARDENING §2.2 |
|---|---|---|---|
| 5.0 | `executed`, 10 sweeps | `executed`, 10 | — |
| 9.0 | `executed`, 16 | — | 16 |
| 10.0 | `executed`, 18 | `executed`, 18 | 18 |
| 10.6 | `executed`, 19 | — | 19 |
| 11.0 | `executed`, 20 | — | 20 |
| 11.5 | `executed`, 21 | `executed`, 21 | — |
| 12.0 / 24.0 / 48.0 | `scientific_admission_refused` | `scientific_admission_refused` | refused |

Every iteration count the sealed evidence records is reproduced exactly, on both profiles.
The frozen numerical baselines in `test_electrothermal_vertical.py` and
`test_trust_hardening.py` pass unchanged: **F11 holds.**

**The ngspice profile is gated and not refused.** A falsifier round raised this as a
candidate BLOCKER — the provider adds two checks of its own and the gate demands the
producer's six — and resolved it *statically* on the belief that ngspice was unavailable.
It is available here through `wsl.exe`: `tests/test_heterogeneous_ngspice.py` runs
**40 passed**, and the table above is a live ngspice run, not an emulation. The mechanism is
`ngspice.py:849`, which calls the native `build_validation_report` and appends to it — a
superset, so the six are always present.

## 3.2 The unpredicted finding — the gate fires on API CASE F

`test_api_mcp_v0.py::case_f` declares a **negative** temperature coefficient
(`-0.01`), so resistance goes non-positive at the temperature the loop transports.

| | before | after |
|---|---|---|
| where it is caught | the DC domain, one step downstream | the property executor, at the producer |
| exception | `InvalidScientificProblem` | `ScientificValidationError` |
| refusal code | `subsolver_execution_failed` | `scientific_admission_refused` |
| HTTP | **500** | **422** |
| detail | — | names `resistance_strictly_positive` and the producer |

**The new classification is the correct one, on `service.py`'s own account** (`:190-196`):
*"A solver that could not produce a number is a subsolver failure. A refusal to ADMIT a
number that was produced is a scientific verdict — the science ran, and Crafty declines to
hand it over — and it is the caller's answer, not Crafty's defect."* The property solver
**did** produce a number; it produced a negative resistance and its own check failed. The
old 500 told the caller *"you did nothing wrong, nothing scientific is claimed"* — which is
the exact sentence `TRUST-HARDENING` §2.3 identified as false and set out to eliminate.
**Enforcement point (a), had it shipped, would have fixed CASE F too. It did not ship, which
is why CASE F still returned 500.**

`test_f`'s stated principle — *the classifier reads the class **and** the position* — is
intact and still tested: the stage is still `execution`, and an admission refusal raised at
the *admission* stage remains a different row with a different `error_type`.

## 3.3 Deviation D-B — P-7 falsified, and its stated mechanism was wrong

`test_composite_system0.py::test_t6f` **does** fire. The preregistration reasoned that this
milestone touches `src/engcore/systems/electrothermal/`, *"which none of those three asserts
unchanged"*. True, and irrelevant: the guard is a **whole-tree allow-list**, so any file not
named in it is stray regardless of directory. The reasoning was wrong even though the
conclusion about `coupled.py` was right — `coupled.py` is already allow-listed.

Measured stray set before repair:

```
['docs/architecture-study/08_CRAFTY_SELF_AUDIT.md',
 'docs/evidence/admission-gate-repair-preregistration.md',
 'docs/evidence/execution-identity-preregistration.md',
 'tests/test_admission_gate_repair.py']
```

**Two of those four are not this milestone's.** `execution-identity-preregistration.md` was
committed alone at `31ddcc7` and made this guard stray *then*; the untracked self-audit file
was already declared environmental. **So the guard has been failing for two reasons while
only one was recorded**, and nobody could see the second because the first already failed it.

This is the **seventh** recurrence of a defect the repository has now repaired six times, and
`TRUST-HARDENING` §3.3 wrote the count into its own evidence. It is not a defect of any
milestone that trips it.

---

# 4. Deviations — the change set was widened twice

The preregistration §2.1 is exhaustive and says a forced change outside it is
**STOP-and-report, not a widening**. That is what happened: execution stopped, both findings
were reported with their measurements, and the owner decided each explicitly. Recorded here
at full strength.

| # | File added to the set | Why it was forced | Decision |
|---|---|---|---|
| W-1 | `tests/test_api_mcp_v0.py` | §3.2 — CASE F's published refusal code changed | widen; assert the new classification and record why |
| W-2 | `tests/test_composite_system0.py` | §3.3 — the seventh scope-guard repair | repair by the same narrow form used six times |

**W-1's honest reading:** the preregistration was drawn one line too narrowly, in the same
way `TRUST-HARDENING` §3.1 admitted of its own — *"changing the return type of a published
protocol method has call sites, and the preregistration should have said so."* Here: adding
a producer-side gate changes which exception class reaches the classifier, and the
classifier's output is a published contract. The preregistration should have said so.

**W-2's repair names this milestone's files individually**, so a stray edit anywhere else is
still loud, and it additionally names `execution-identity-preregistration.md` so the count is
honest. After the repair, `test_t6f` fails on **exactly one** file — the untracked
`08_CRAFTY_SELF_AUDIT.md`, which is the declared environmental failure and which this
milestone did not create and does not remove.

**Neither widening weakened an assertion.** `test_f` gained an assertion (the detail names
the producer). `test_t6f` gained allow-list entries and no predicate change.

---

# 5. Adversarial round

Five independent falsifiers plus an adjudicator that re-verified every BLOCKER and MAJOR
against the tree. Overall: **SURVIVES WITH REQUIRED CHANGES.** The required changes were made.

## 5.1 Two BLOCKERs, both real

**B-1 — CASE F.** Found independently by two lenses and confirmed by the adjudicator. Not a
defect of the change: it is §3.2, and it forced W-1.

**B-2 — `test_g` reproduced the exact defect this milestone exists to repair.** Its first
form was written

```python
assert not (declared & set(c.name for c in result.validation.checks) - satisfied)
```

which, because `-` binds tighter than `&`, reads `declared & (present − passing)` — blind to
a declared requirement being **absent**, and silent about the electrical executor, which it
skipped. Rewritten to demand the declared set be present *and* passing, with an explicit
`AssertionError` when no set governs a problem id, and an assertion that all three executors
were exercised. **Verified by removal:** with `resistance_strictly_positive` deleted from the
report, the first form passed and the current one fails.

## 5.2 One MAJOR closed by mutation — the suite could not see a *narrowed* gate

The adjudicator's sharpest surviving finding: only `power_balance` and
`kirchhoff_current_law` were ever withheld, so **a gate silently narrowed to those two —
leaving four of the six producer-published requirements unenforced — passed the entire
suite.** In a milestone whose whole subject is a test that passed while measuring nothing,
that is the same species of defect.

`test_c` is now parametrized over all six. Measured against a mutant gate that intersects
its requirements with `{power_balance, kirchhoff_current_law}`:

| withheld requirement | mutant |
|---|---|
| `dimensional_consistency` | **caught** |
| `linear_system_residual` | **caught** |
| `resistor_metric_consistency` | **caught** |
| `voltage_source_relation` | **caught** |
| `kirchhoff_current_law` | survives — correctly; the mutant still enforces it |
| `power_balance` | survives — correctly |

**4 of 6 detect the narrowing. Before parametrization, 0 of 6 did.**

## 5.3 Three findings collapsed on re-verification

Reported as BLOCKER/MAJOR by three separate lenses, all **falsified by the adjudicator
against the file on disk**: they described an earlier revision of
`tests/test_admission_gate_repair.py`, already superseded by §5.1's repair. Every cited line
number was wrong and the quoted code did not exist. Recorded because three independent
falsifiers converging on one wrong target is itself worth knowing: convergence is not
corroboration when they share a stale premise.

## 5.4 One finding this document corrects in the falsifiers' favour, and one against

**Against.** Two lenses resolved the ngspice question *statically*, on the stated basis that
*"ngspice is not installed on this machine"*. It is installed, reached through `wsl.exe`:
`tests/test_heterogeneous_ngspice.py` runs 40 passed, and §3.1's table is a live ngspice run
on the coupled path. Their conclusion was right; their evidence was weaker than available.

**In their favour.** The refusal **detail lost information**, which this document would
otherwise not have recorded:

```
before:  "resistor 'R1' requires resistance > 0, got -18.799999999999997 ohm"
after:   "admission refused; declared requirement(s) not satisfied by a passing check:
          'resistance_strictly_positive': fail"
```

The gate names *which check* failed and *which producer* refused; the domain named *what the
number was*. Both are useful and the caller now gets only the first.

---

# 6. The residue this milestone does not close

* **A numerical-admission refusal and an applicability refusal are now
  indistinguishable at the public boundary.** The adjudicator's second surviving MAJOR, and
  the most important thing in this document. Both produce identical `code`
  (`scientific_admission_refused`), identical `stage` (`execution`) and identical
  `error_type` (`ScientificValidationError`); only free-text `detail` separates them. This
  is **newly reachable** — before this change no numerical-admission refusal could be
  reached from the electrothermal path at all, so the collision could not occur.
  It is in tension with the concept separation `TRUST-HARDENING` §0 exists to protect and
  which this milestone's own §0 declares settled and not reopened. **Not closed here**,
  because closing it means either a new `RefusalCode` member or a discriminating field on
  the response — F6 and F7 respectively, and a schema decision belongs to a milestone that
  preregisters it. Named so the next milestone does not discover it.
* **The refusal detail no longer names the offending value.** §5.4. The gate reports which
  check failed and which producer refused; the domain reported that the resistance was
  −18.8 ohm. A caller debugging a negative-TCR declaration is now told less.
* **`SUBSOLVER_EXECUTION_FAILED` has lost its only positive test coverage.** Measured:
  `grep -rn "SUBSOLVER_EXECUTION_FAILED" tests/` returned exactly one hit, CASE F's
  assertion, and §3.2 moved it. The branch still exists at `service.py:195`. Reaching it
  now requires a sub-solve that fails **without** producing a number, and the profile
  enumeration is closed, so constructing one means a new hostile profile or a domain edit —
  both outside this milestone. **Named, not closed.**
* **`power_chain.py:1015` calls the circuit seam with no gate.** The coverage claim is
  scoped to `coupled.py`. `power_chain` is not reachable from the application layer, so no
  external consumer is exposed; a second consumer of the seam is nonetheless ungated.
* **The electrical gate cannot see the provider's own two checks.**
  `realization_precondition_non_singular` and `provider_element_metric_consistency` are
  added by `ngspice.py:852-858` and are not in the producer's six, so a FAIL on either is
  invisible to `require_admission`. Requiring them would mean the pack naming a provider it
  is forbidden to know.
* **The two consumer-invented sets are not enforced to stay complete** as their producers
  evolve. `test_a` pins them against what the solvers emit today; nothing fails if a solver
  later adds a check that should be required.

---

# 7. Regression

Baseline at `31ddcc7`: **2568 collected.** This milestone adds **13** tests
(8, of which `test_c` is parametrized over the six electrical requirements → +5) → **2581**.

**FULL: 2575 passed / 5 failed / 1 skipped, 732.87 s** (sequential).

`2575 + 5 + 1 = 2581 = 2568 + 13`. **The count clause of P-6 holds exactly**: no test was
deleted, skipped or de-selected to reach it.

Environment note, so the figure is comparable: this machine's sandbox denies pytest's
`%TEMP%\pytest-of-*` root and does not have the package installed, which alone produces 39
errors and 4 failures unrelated to any code. Both are removed by `--basetemp` in a writable
directory and `PYTHONPATH=src`; every figure in this document was measured with both set.

Remaining failures and their causes:

| test | cause | this milestone's? |
|---|---|---|
| `test_ft_coupling_records::…relocated_and_not_edited` | cp1252 decode of `git show` | no — declared at TRUST-HARDENING §7.1 |
| `test_composite_system0::test_t6f` | one untracked file, `08_CRAFTY_SELF_AUDIT.md` | no — declared; §3.3 removed the other three strays, so it now fails on exactly the one declared cause |
| `test_executable_scientific_spec::…boundary_condition_channel…` | Windows `\` vs `/` | no — declared |
| `test_api_mcp_v0_transports::test_nothing_a_request_can_say_launches_a_process…` | sandboxed `subprocess.Popen` | no — declared |
| `test_api_mcp_v0_transports::…a_size_fault_is_a_transport_fault` | binds a socket; **flaky under suite load** | no — **proven**: it failed on the *unmodified* tree in this session's first FULL run, and it **passes in isolation** on the changed tree |

**`test_api_mcp_v0.py` is fully green**, including the rewritten `test_f`. The last row was
not asserted to be pre-existing on the strength of its traceback — it was reproduced on the
baseline tree and then re-run alone, because "it looks environmental" is the reasoning that
lets a real regression through.

## 7.1 Scope gates, measured after the fact

Zero files changed under `src/engcore/scientific/`, `src/engcore/coupling/`,
`src/engcore/domains/`, `src/engcore/systems/fluidthermal/`,
`src/engcore/systems/propulsion/`, `src/engcore/systems/aerospace/`,
`src/engcore/application/`, `src/crafty_http/` and `src/crafty_mcp/` — **F1 through F5 all
hold.** No record, dataclass or enum member was created (F6); no schema minted or bumped
(F7); `ValidationReport`, `ValidityAssessment`, `is_usable` and `require_admission` are
byte-unchanged (F8); no sealed evidence document was edited (F9); no assertion was weakened,
no tolerance loosened and no test deleted (F10); no swept numerical result moved (F11).

**Public surface growth: zero.** Neither new constant is exported.

---

# 8. Evidence ceiling

`L1 EXERCISED` for the executed behaviour; `L0 REASONED` for every classification and for
§3.2's argument that 422 is the correct code. **No `L2`** — one pack, one composition, two
profiles of one execution. **No freeze, and no promotion of any existing holding.** This
milestone lowers no bar and raises none; it makes one published claim true, and corrects two
records that were not.
