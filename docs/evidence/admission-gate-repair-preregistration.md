# ADMISSION-GATE-REPAIR: preregistration

**Written before any source change.** To be committed alone and not amended. Every number
below is either a **declaration** (measured on the unchanged tree at `31ddcc7`, stated so it
can be re-measured) or a **prediction** (stated so a measurement can contradict it). Each is
labelled.

| | |
|---|---|
| Baseline commit | `31ddcc7` (EXECUTION-IDENTITY preregistration, committed alone) |
| Branch | `trust-hardening` (continues; this milestone is additive to it) |
| Sealed records not to be rewritten | `docs/evidence/trust-hardening-*.md`, `docs/evidence/propulsion0-*.md`, `docs/evidence/execution-identity-preregistration.md` |
| Scope | **one defect**: preregistered enforcement point (a) is absent from the tree, and the test that records it cannot detect its absence |
| Kind | correction. **No new physics, no new domain, no new universal contract.** |
| Measured FULL at baseline | 2568 collected. Clean-machine figure declared by TRUST-HARDENING §7.1: 2563 passed / 4 failed / 1 skipped, 783.42 s |

**This milestone exists because a preregistration promised a specific edit to a specific
file, the evidence document published that edit as shipped, and the edit was never made.**
That is the failure mode the preregistration/evidence discipline exists to prevent, so the
correction is written the same way the original should have been checked.

---

## §0 What is already proved and is NOT re-attempted

- The separation of numerical validation from scientific applicability is settled by
  TRUST-HARDENING and is not reopened. Enforcement point **(b)** — applicability admission
  after the loop, `require_coupled_admission` at
  `src/engcore/application/executions/electrothermal_series.py:241` — **exists, is wired,
  and is correct.** It is not touched.
- `ValidationReport.require_admission`
  (`src/engcore/scientific/results/validation.py:234-256`) is correct and is not changed.
  Its opt-in design — *"enforcement is not automatic on construction"* — is deliberate and
  is not re-litigated.
- The refusal classification `SCIENTIFIC_ADMISSION_REFUSED` → HTTP 422 is settled.
- `AdmittedCoupledRun` is ephemeral by design.

---

## §1 The defect, measured before any change

### 1.1 What was preregistered

`docs/evidence/trust-hardening-preregistration.md` §5.2, quoted exactly:

> **(a) Numerical-validation admission — producer-side, inside the loop.** Each of the
> three executors in `systems/electrothermal/coupled.py` reads its own result through
> `result.validation.require_admission(problem.validation_requirements, context=…)` before
> returning it, exactly as `systems/fluidthermal/coupled.py:631, :718, :785` already do. A
> failing declared requirement raises out of the loop and **no result is transported**.

### 1.2 What is in the tree

```
$ grep -rn "require_admission" src/engcore/systems/electrothermal/ src/engcore/domains/electrical/
(no matches)
```

**Zero call sites.** `ValidationReport.require_admission` is called in exactly two places in
the repository — `src/engcore/domains/fluids/transport2d/validation.py:361, :392` and
`src/engcore/systems/fluidthermal/coupled.py:631, :718, :785` — and neither is on the
shipped electro-thermal path.

The three executors named by §5.2(a) are
`_property_result` (`coupled.py:553`), `_thermal_result` (`coupled.py:599`) and
`_electrical_result` (`coupled.py:728`). None calls it.

### 1.3 What the evidence published

`docs/evidence/trust-hardening-evidence.md` §2.2 presents (a) as one of "two enforcement
points, at two different times", tabulated with a `what` of *"`require_admission` against
declared requirements"* and an `on failure` of *"raises out of the loop; no result
transported"*. The headline states it *"fires on **zero** of every operating point
measured"* and calls it *"defence in depth"*.

**A gate that does not exist also fires on zero operating points.** The evidence is not
false about the observation; it is false about the mechanism, and no measurement in the
milestone could distinguish the two — which is §1.4.

### 1.4 Why the regression test could not catch it

`tests/test_trust_hardening.py:230-245`, `test_p1_7_numerical_admission_fires_on_none_of_the_swept_runs`:

```python
for result in admitted.run.final.results:
    assert result.validation.admission_issues(
        {check.name for check in result.validation.checks}
    ) == ()
```

The requirement set is **derived from the checks that ran**. The assertion therefore reads
"every check that ran, ran" — true of any result, on any tree, whether or not any gate
exists. It never calls `require_admission`, never references
`problem.validation_requirements`, and would pass unchanged if `require_admission` were
deleted from the repository.

> **Declaration D-1.** Deleting the body of `ValidationReport.require_admission` and
> replacing it with `return None` leaves `test_p1_7` passing. To be measured and recorded,
> not assumed.

### 1.5 What is available to gate against

Measured, because the repair's shape depends on it and the original preregistration already
anticipated the split:

| executor | problem builder | producer-published `validation_requirements` | check name actually emitted |
|---|---|---|---|
| `_electrical_result` | `domains/electrical/dc/problem.py:184` | **yes — 6 names** | `dimensional_consistency`, `linear_system_residual`, `kirchhoff_current_law`, `resistor_metric_consistency`, `voltage_source_relation`, `power_balance` |
| `_property_result` | `domains/electrical/material.py` | **none** | `resistance_strictly_positive` (`material.py:634, :645`) |
| `_thermal_result` | `domains/thermal_lumped.py` | **none** | `lumped_balance_residual` (`thermal_lumped.py:831, :855`) |

`systems/fluidthermal/coupled.py:132-136` is the shipped precedent for the second case, and
labels itself *"a consumer-invented requirement, weaker evidence than a producer-published
one"*. That label is reused verbatim rather than improved on.

---

## §2 Fail conditions (any one is STOP-and-report)

| # | Condition |
|---|---|
| **F1** | any byte of `src/engcore/scientific/` changes |
| **F2** | any byte of `src/engcore/coupling/` changes |
| **F3** | any byte under `src/engcore/domains/` changes — including publishing `validation_requirements` on the two builders that lack them |
| **F4** | any byte of `src/engcore/systems/fluidthermal/`, `src/engcore/systems/propulsion/` or `src/engcore/systems/aerospace/` changes |
| **F5** | any byte of `src/engcore/application/` changes |
| **F6** | a new record, dataclass or enum member is created anywhere |
| **F7** | a schema string is minted, or an existing schema version bumped |
| **F8** | `ValidationReport`, `ValidityAssessment`, `is_usable` or `require_admission` changes meaning |
| **F9** | a sealed evidence document is edited |
| **F10** | an existing assertion is weakened, a tolerance loosened, or a test deleted |
| **F11** | the numerical result of any swept operating point changes |

F3 is the constraint that shapes the repair. Publishing requirements on the domain builders
would be the stronger fix and is **refused here**: it changes two domains to repair one
pack's omission, and the original preregistration already ruled it out as its own F8.

### 2.1 Permitted change set — exhaustive

```
src/engcore/systems/electrothermal/coupled.py     the three call sites + two consumer-side frozensets
tests/test_admission_gate_repair.py               new, the evidence
tests/test_trust_hardening.py                     test_p1_7 only — replaced, not deleted
docs/evidence/admission-gate-repair-preregistration.md   this file, committed alone
docs/evidence/admission-gate-repair-evidence.md   written after execution
```

**No other file may change.** `tests/test_trust_hardening.py` is a test module, not a sealed
evidence document; F9 covers `docs/evidence/trust-hardening-*.md`, which are **not** touched.
The correction to their §2.2 is recorded in this milestone's own evidence, forward-referenced,
because a sealed record is corrected by a successor and never by rewriting.

### 2.2 Baseline failures that are NOT this milestone's to fix

Four, all environmental, all declared in TRUST-HARDENING §7.1: an untracked file in the
working tree, a Windows path-separator assertion, a cp1252 decode of `git show`, and a
sandboxed `subprocess.Popen` refusal. On a sandbox that also denies pytest's `tmp_path`
root, add 39 errors and 4 further failures; both classes are reproduced away with
`--basetemp` in a writable directory and `PYTHONPATH=src`, and neither is a regression.

---

## §3 The change

Three call sites, placed immediately before each executor returns, in the shape
`systems/fluidthermal/coupled.py:631` already ships:

1. **`_electrical_result`** — gate against `problem.validation_requirements`, the
   producer-published set. This is the strongest form and requires no invention. The problem
   is reachable in `_executors` (`coupled.py:736`), which already selects it.
2. **`_property_result`** — gate against a pack-level frozenset naming
   `resistance_strictly_positive`, labelled consumer-invented.
3. **`_thermal_result`** — gate against a pack-level frozenset naming
   `lumped_balance_residual`, labelled consumer-invented.

The two frozensets are module constants beside the existing `DEPENDENCY_*` labels. They are
data, not a mechanism: nothing branches on them and no registry is created.

**The substitution seam is preserved.** `_electrical_result` delegates to `circuit_solver`,
which may be `native_circuit_solver` or the ngspice adapter. The gate is applied to the
result the seam returns, so both profiles are gated identically and neither adapter is edited.

---

## §4 Predictions

> **P-1.** After the change, `grep -rn "require_admission" src/engcore/systems/electrothermal/`
> returns **exactly three** call sites. **Falsified if** it returns any other number.

> **P-2 — behaviour is unchanged.** Every swept operating point (5.0, 10.0, 11.0, 11.5, 12.0,
> 24.0, 48.0 V) produces a byte-identical response to the baseline: same
> `CouplingOutcome`, same `iterations_run`, same converged temperature to the last bit, same
> `model_validity` verdict, same refusals at 12 V and above. **Falsified if** any published
> value moves. The gate is defence in depth and must be inert today.

> **P-3 — enforcement point (a) still fires on nothing.** At every swept point, every
> declared requirement is satisfied by a passing check, so no `ScientificValidationError` is
> raised by any of the three new call sites. **Falsified if** any point now refuses — which
> would mean the shipped path had been transporting a numerically unadmitted result, and
> would make this a much larger finding than a correction.

> **P-4 — the replacement test can fail.** With `require_admission` stubbed to `return None`,
> the new `tests/test_admission_gate_repair.py` **fails**. Proven by deletion, not by
> inspection, in the manner `PROPULSION0-EXT` proved its circuit spy could fail.
> **Falsified if** it passes against the stub — which would make it as vacuous as the test
> it replaces.

> **P-5 — the old test was vacuous.** `test_p1_7` as written passes against the same stub.
> **Falsified if** it fails, which would mean it had content after all and §1.4 is wrong.

> **P-6 — regression delta is exactly the tests added.** FULL moves from 2568 collected by
> the number of new tests, and no pre-existing test changes outcome except `test_p1_7`,
> which is replaced. **Falsified if** any other test's outcome moves.

> **P-7 — no scope guard fires.** The whole-tree guards in `test_propulsion0.py`,
> `test_propulsion0_ext.py` and `test_composite_system0.py` read `git diff <their own prereg> HEAD`
> and have needed repair six times. This milestone touches
> `src/engcore/systems/electrothermal/`, which **none** of those three asserts unchanged.
> **Falsified if** any of them fails — the seventh recurrence, and it would be recorded as
> such rather than repaired silently.

---

## §5 The ordering consequence, stated rather than discovered

`docs/evidence/execution-identity-preregistration.md` is committed alone at `31ddcc7`,
declares its baseline as `139c9b9`, and forbids amendment. **This milestone changes the tree
that preregistration measured**, and its F3/F4 forbid exactly the file this milestone edits.

That is not a conflict — F-conditions bind the milestone that declares them — but it has two
consequences which are recorded now so they are not presented later as discoveries:

1. Every **declaration** in the execution-identity preregistration (§2's byte sizes, the
   nine-question table, the four distinct doubles) must be **re-measured** against the
   post-repair tree before that milestone executes. Any that moved is a deviation of that
   milestone, recorded there.
2. Its §0 states *"the applicability verdict, the admission decision … were settled by
   TRUST-HARDENING and are not reopened."* This milestone does not reopen them. It repairs a
   gate TRUST-HARDENING published and did not ship, which is a different act, and its §2.1
   change set is disjoint from the execution-identity §1.1 change set.

---

## §6 Presumed unnecessary — reaching for any of these is a visible deviation

A validation-requirement registry; a base class or protocol for executors; publishing
`validation_requirements` on the two domain builders; a `trusted` boolean; auto-collected
machine identity; a completeness-enforcement gate; any change to `require_admission` itself;
a generic "gate every executor" helper. There are three call sites and one shipped
precedent; a helper for three call sites is a helper for nothing.

---

## §7 Acceptance

KEEP only if:

1. No F-condition fired.
2. P-1 … P-7 each held, or each failure is recorded as a deviation with the measurement that
   refuted it.
3. D-1 was measured, not assumed.
4. The change set is a subset of §2.1.
5. The correction to `trust-hardening-evidence.md` §2.2 is recorded in **this** milestone's
   evidence, and that document is not edited.
6. A falsifier round was run against the *repair*, and its findings are recorded at full
   strength.

---

## §8 Evidence ceiling

`L1 EXERCISED` for the executed behaviour; `L0 REASONED` for every classification. **No
`L2`** — one pack, one composition, one consumer. **No freeze, and no promotion of any
existing holding.** This milestone lowers no bar and raises none; it makes one published
claim true.
