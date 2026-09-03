# MINIMUM CROSS-DOMAIN FOUNDATION — Evidence

**Milestone:** `MIN-CROSS-DOMAIN-FOUNDATION`
**Decision status:** `PROPOSED`. **Not `DESIGN-FROZEN`.**
**Evidence level:** `L1 EXERCISED` for both abstractions built; **the falsifier's
central finding narrows what `L1` means here** — see §7.
**Reviewer verdict:** `ACCEPT WITH CHANGES` (both changes are documentation
honesty, not design changes — see §6).
**Falsifier verdict:** `SURVIVES CURRENT EVIDENCE`. No `BLOCKER`, no
`BREAKING-RISK`. One real defect found and fixed before this document was
written (domain vocabulary leaked into two docstrings) — see §7.
**Date of this record:** 2026-09-03
**Branch:** `min-cross-domain-foundation`

> **Temporal boundary.** `docs/min-cross-domain-foundation-prereg.md` is the
> preregistration: committed at `76f6dd4`, before any implementation source
> was added or edited, and immutable. **This** document was written after
> execution. Deviations, corrections, adversarial findings and the final
> classification live here and nowhere else.
>
> This is **not** a freeze document.

---

# 1. Result against the preregistered hypotheses

**H1 supported, at its narrowest stated shape. H2 supported (a non-build).
H3 supported, with one factual correction and one honestly-reported
limitation on how strong the corroboration actually is.**

| # | Hypothesis | Outcome |
|---|---|---|
| H1 | Variable↔Bulk Binding is forced; minimal shape is a standalone two-name record | **Supported.** `VariableBulkLinkage(variable_name, reference_name, description="")` |
| H2 | No new `ValidationLevel` member is forced | **Supported.** Nothing built; the enum is unchanged |
| H3 | Enforced Admission is forced; minimal shape is a method, not a record | **Supported, narrowly.** `ValidationReport.require_admission`/`is_admissible`/`admission_issues`, reusing `ScientificProblem.validation_requirements` |
| H0(A) | Zero contracts survive everywhere | **Refuted for H1 and H3**, on measurements, not on argument — see §2 |
| H0(B) | The new abstractions are domain vocabulary in disguise | **Refuted**, after one real violation was found and fixed — see §7 |

---

# 2. Zero-new-contract attempts and their outcomes

Executed in `tests/test_min_cross_domain_foundation.py` Part A, not reasoned
about in prose.

## 2.1 Variable↔Bulk Binding (prereg §4.1)

| # | Attempt | Outcome | Test |
|---|---|---|---|
| 1 | `ScientificDataReference.name` as a descriptive string | **REJECTED** — a records-only reader has no typed path from a name string to a declared `ScientificVariable`; exact-name membership is the only legitimate operation and a merely-related string is not a match | `test_a1` |
| 2 | `ScientificVariable.categories` alone | **REJECTED, informatively** — corroborates `EXEC-SPEC-STRUCTURED` §F that an ordered named-member set is already representable; it states nothing about which bulk reference instantiates the variable | `test_a2` |
| 3 | `ScientificParameter` carrying the reference name as a string value | **REJECTED** — constructible and unchecked; nothing verifies resolution or dimensional agreement | `test_a3` |
| 4 | `ScientificResult.metadata` | **REJECTED** — the untyped escape hatch this platform refuses everywhere else; not executed as a separate test because every other milestone already executes this refusal and nothing here would differ |
| 5 | Splitting one combined array into per-variable references, relying on the reference's free-text name | **Removes the interleaving question, does not remove the binding question** — two named references still cannot be resolved to declared variables without a typed cross-reference; demonstrated by resolving first with no linkage (fails) and then with one (succeeds), on the same two records | `test_a5` |

**H0(A) is refuted by measurement**: attempt 5 was the steelman, and it still
needed a typed binding once actually built and checked against a
records-only resolver, not merely asserted representable.

## 2.2 Admissibility Attainment / Enforced Admission (prereg §4.2)

| # | Attempt | Outcome |
|---|---|---|
| 1 | `ValidationReport.require_level(...)` | **REJECTED** — gates on an evidentiary level; every admissibility check in every shipped domain deliberately `establishes=None` |
| 2 | `ScientificResult.is_usable` | **REJECTED** — global over the whole report; a required check that is `NOT_RUN` does not by itself flip it unless something else also failed |
| 3 | `ScientificProblem.validation_requirements`, read manually by each consumer | **REJECTED as a universal answer** — see §2.3, deviation D-1, for the correction to what was originally claimed here |
| 4 | A new `ValidationLevel` member | **REJECTED, see §4** |
| 5 | A new universal `AdmissionDecision` record modeled on `sria.admission.AdmissionDeclaration` | **REJECTED in advance and confirmed after the fact** — see §5 |

### 2.3 Deviation D-1 — a factual correction to the preregistration

Prereg §4.2 attempt 3 claimed `kinetics/cstr`'s `run_verification_gate`
*"hand-rolls exactly this cross-reference"* (i.e., reads
`validation_requirements` and matches it against `ValidationCheck.name`s).
**This is false, and the falsifier caught it** (§7, finding C4):
`src/engcore/domains/kinetics/cstr/validation.py` contains zero references to
`validation_requirements`; `run_verification_gate` gates per-rung
admissibility on `result.is_usable` instead — the coarse mechanism this
milestone's own H0(A) rejects. Verified directly: `grep -n
"validation_requirements" src/engcore/domains/kinetics/cstr/validation.py`
returns nothing.

**What survives the correction.** `kinetics/cstr`'s own gate independently
re-deriving an admissibility-adjacent check using a *different*, coarser
mechanism (`is_usable`) is itself weak corroborating evidence that a
consumer wants *some* admissibility gate — it is not, as originally
overclaimed, evidence that the gate already implements the specific
mechanism this milestone built. The stronger, load-bearing fact for H3 —
that `validation_requirements` is populated by three shipped domains with
names matching their own checks, and consumed by nothing — is unaffected and
independently verified in `test_h3` against real production code.

---

# 3. Contracts added

## 3.1 `VariableBulkLinkage`

`src/engcore/scientific/results/variable_binding.py` —
`variable_bulk_linkage/1`.

```text
VariableBulkLinkage
    variable_name  : str   references a declared ScientificVariable by name
    reference_name : str   references a ScientificDataReference by name
    description    : str   prose; no evidential weight
```

with `check_against(*, problem=None, result=None) -> tuple[BindingIssue, ...]`
and a module function `unlinked_references(result, linkages)`.

Every field earns its place against the measured residue in §2.1 and
nothing else: no axis order, stride, interleaving flag, shape, `problem_id`
or `result_id`. The last two are omitted on the same precedent
`ScientificDataReference` and `QuantityDependency` already established —
scoping by whichever collection holds the record, not by a redundant
identity pair. `check_against` reuses `BindingIssue`/`BindingIssueKind` from
`models/definition.py` rather than minting a parallel issue type.

## 3.2 `ValidationReport.require_admission` / `is_admissible` / `admission_issues`

`src/engcore/scientific/results/validation.py` — three methods added to the
existing `ValidationReport` class. **No new type, no new schema field, no
schema version moved** (`validation_report/1` and `validation_check/1` are
unchanged, asserted in `test_g6`).

```python
admission_issues(requirements: Iterable[str]) -> tuple[str, ...]
is_admissible(requirements: Iterable[str]) -> bool
require_admission(requirements: Iterable[str], *, context: str = "") -> None  # raises ScientificValidationError
```

Cross-references `requirements` (the caller supplies
`problem.validation_requirements`) against `self.checks` by `.name`,
treating `PASS` as the only satisfying outcome — `FAIL`, `WARNING` and
`NOT_RUN` are all unsatisfied, on the same "a check that never ran
contributes no evidence" principle the module already states for
`ValidationLevel`.

---

# 4. Contracts explicitly rejected, and why

| # | Candidate | Verdict | Why the answer was weak |
|---|---|---|---|
| 1 | A field on `ScientificDataReference` for the variable name | **REJECT** | `DATA_REFERENCE_SCHEMA` is exact-string pinned at `/1`; adding a field would move it and make every stored reference unloadable by a pre-milestone reader, for a fact that is not true of the *bytes* the reference names — it is true of how one problem+result pair interprets them |
| 2 | A field on `ScientificVariable` | **REJECT** | A variable is a reusable declaration; welding one solve's bulk artifact onto it would make the same variable, filled by a different solve, a different variable |
| 3 | Axis order / stride / interleaving field on the binding record | **REJECT, narrowly — see the falsifier's C7/C8** | Every consumer this milestone exercised reduces cleanly to one variable per reference. Not proof no domain will ever need it; deferred with a named, precedented widening path (`require_schema_any`, already used elsewhere in this codebase) rather than built speculatively |
| 4 | New `ValidationLevel` member (H2) | **REJECT** | See §5 |
| 5 | New `AdmissionDecision` record modeled on `sria.admission.AdmissionDeclaration` | **REJECT** | See §6, part K of the tests, and the falsifier's C9 |
| 6 | `problem_id`/`result_id` fields on `VariableBulkLinkage` | **REJECT** | Duplicates an implicit scoping convention `ScientificDataReference` and `QuantityDependency` already use; no consumer needed it |

---

# 5. Admissibility Attainment: why no new `ValidationLevel` member (H2)

The measured asymmetry, corroborated across three prior milestones and
re-confirmed here (`test_h1`, `test_h2`): `ValidationLevel` has seven
members, none of which denotes physical admissibility, so a *passing*
admissibility check can never enter `attained_levels` — it structurally
carries `establishes=None` in every shipped domain that writes one.

This milestone's contribution is narrowing *why that is acceptable*: the gap
a real incident actually exposed (`HETERO-NGSPICE` §8.4, §1 point 3) was not
"we cannot express that admissibility was checked and passed" — the check
and its `PASS`/`FAIL` outcome were always expressible. The gap was that
nothing *consumed* the outcome before the value was used. A new
`ValidationLevel` member would have added a second, stronger evidentiary
claim without touching the actual defect, which is an enforcement gap, not a
vocabulary gap. `H2`'s falsification condition — a real consumer needing to
*rank* two admissibility checks rather than merely gate on one — was not
observed, and none is claimed.

---

# 6. Enforced Admission: the proof, and the SRIA distinction

## 6.1 The negative proof (mandatory, §A5)

`tests/test_min_cross_domain_foundation.py` Part J, modeled directly on
`HETERO-NGSPICE` §8.4's already-executed incident and on `kinetics/cstr`'s
own `state_physically_admissible` check:

```text
test_j1 — UNGUARDED consumer: reads result.value(...) directly.
          Succeeds silently on a result whose declared requirement FAILed.
          result.validation.status is FAIL; consumed value returned anyway.
          This is the forbidden outcome, proven real and structural, not
          hypothetical, absent the guard.

test_j2 — GUARDED consumer: calls require_admission(...) before reading
          the value. Raises ScientificValidationError. A sentinel proves
          the value-reading line is never reached.

test_j3 — the same guard does NOT refuse a genuinely satisfied requirement
          — this is admission, not blanket refusal.
```

Required outcome achieved: `FAIL → require_admission(...) raises
ScientificValidationError → the consumer function never reaches its use of
the value`, caught by `pytest.raises` in the test itself. Forbidden outcome
(a warning or an ignorable boolean) does not occur — `require_admission`
returns `None` or raises; there is no third path.

## 6.2 SRIA admission is a different concern (per the governing task)

`sria.admission.AdmissionDeclaration` authenticates an **issuer** accepting
an **evidence record** into a design campaign — HMAC signature, one-way
authorization commitment, arbiter identity. `ValidationReport.
require_admission` states whether a **named check already in the report**
passed. Measured, not merely argued (`test_k1`): the two share no schema
string, no dataclass field, and no method name. `AdmissionDeclaration`'s
`{admitted, issuer_id, issued_signature, arbiter_id}` field set is disjoint
from `ValidationReport`'s.

**The smallest shared invariant is a principle, not a type**: both fail
closed on an unmet declared requirement. Recorded as a design principle
rather than unified into one contract, because unifying them would either
force every scientific result to carry an issuer/signature it has no actor
for, or force SRIA's governance layer to understand `ScientificResult`
internals — both rejected on the same layer-separation grounds the rest of
this codebase already holds.

---

# 7. Falsifier findings and resolutions

`architecture-falsifier`, primary attack *"these concepts only appear
universal because four prior milestones kept selecting consumers that
exhibit them — show the corroboration is real, not selection."* Verdict:
**SURVIVES CURRENT EVIDENCE. No `BLOCKER`, no `BREAKING-RISK`.**

| # | Finding | Class | Resolution |
|---|---|---|---|
| **C1** | **Zero production callers.** Outside their own definitions and this milestone's tests, nothing in `src/` calls `require_admission`, `is_admissible`, `admission_issues` or constructs a `VariableBulkLinkage` — verified by repository-wide grep, repeated here and returning empty | IMPLEMENTATION CONCERN | **Not fixed — recorded as the central limitation of this milestone's evidence.** See §7.1 |
| **C2** | The one real incident that motivated H3 (`HETERO-NGSPICE` §8.4) was fixed **without** this milestone's primitive and stays that way — `coupled.py` is byte-unchanged (`test_g5`), so the real precedent case still uses its domain-local `raise`, not `require_admission` | IMPLEMENTATION CONCERN | **Recorded, not fixed.** Applying the prereg's own §10 falsification criterion honestly, this is evidence *for* the "domain-local pattern, not core" reading being live, not settled — see §7.1 |
| **C3** | The mandatory negative proof exercises `FAIL`, the weaker of its two preregistered options (§9 allowed `FAIL` *or* `NOT_RUN`) — a `FAIL` scenario is already caught by the cheaper `is_usable`, so Part J demonstrates "nobody checks anything" rather than "only `require_admission` would have caught this" | IMPLEMENTATION CONCERN | **Not fixed.** `test_i3` independently proves the `NOT_RUN`-while-`is_usable`-stays-`True` case `require_admission` uniquely closes; Part J's own choice of `FAIL` (matching the real `HETERO-NGSPICE` incident exactly) is accepted as the more realistic scenario rather than the maximally-differentiating one |
| **C4** | Prereg §4.2 attempt 3's claim about `run_verification_gate` does not match the code | Documentation accuracy | **Fixed — deviation D-1, §2.3** |
| **C5** | Typo fragility in name matching | Attacked as a primary challenge item; **held** — a typo raises loudly and unconditionally on first call, not silently | NOT A REAL ISSUE, as posed |
| **C6** | `NOT_RUN`-as-inadmissible has no way to express "intentionally not applicable" | SPECULATIVE | **Correctly deferred** — no current consumer needs the distinction; fails safe (over-refuses) rather than unsafe |
| **C7** | The two-field shape assumes per-variable splitting is free; untested against a producer that can only emit one combined interleaved array at cost | SPECULATIVE | **Correctly deferred**, honestly disclaimed in the record's own docstring; `require_schema_any` is the codebase's existing precedent for a future additive widening |
| **C8** | `check_against` never cross-checks `count` against `len(categories)` when a linkage's variable is categorical — a structurally meaningless linkage can check clean | SPECULATIVE | **Correctly deferred** — no consumer combines the two primitives this way |
| **C9** | Whether SRIA and scientific admission should share a contract | Attacked directly | **Held — NOT A REAL ISSUE.** See §6.2 |

Domain-vocabulary leak, found independently of the falsifier's own scan (by
this repository's *existing* `kinetics/cstr` guardrail,
`test_the_scientific_core_owns_no_cstr_specific_rule`, which a FULL run
caught before this document was written): the `require_admission` docstring
named `kinetics/cstr`'s check names as an illustrative example, and
`variable_binding.py`'s module docstring used "concentration" as an example
quantity — both regex-matched on word boundaries by an existing FULL-suite
test. **Fixed** in commit `90a4f07`, before this document was written, with
domain-neutral phrasing. This is recorded because §H0(B) is a live
hypothesis this milestone is required to test, and the fix demonstrates the
existing guardrail machinery — built for a *different* milestone — catches
a *new* milestone's leak without modification, which is itself corroborating
evidence the lexical-scan approach generalizes.

## 7.1 What C1/C2/C3 mean for this milestone's claim, stated as plainly as
the falsifier stated it

The milestone has **executable proof that `VariableBulkLinkage` and
`require_admission` work correctly when called** — every test in Parts B
through F and I through J constructs real or realistic scenarios and gets
the correct answer, including against one real production `src/` consumer
(`thermal_conduction1d_bulk.py`, Part F) and one real production solve
(`kinetics/cstr`, `test_h3`/`test_i6`).

It does **not** yet have **architectural proof that anything in this
codebase's current production code needs to call them**. The one real
incident that motivated H3 was fixed one layer earlier and remains fixed
that way; nothing in `src/` was changed to adopt either primitive as part of
its own result-production or result-consumption path. This milestone
deliberately did not wire `require_admission` into
`src/engcore/systems/electrothermal/coupled.py` or into `kinetics/cstr`'s
verification gate, for two reasons stated in advance rather than after the
fact: retrofitting a real, working, tested production consumer is a
different and larger change than this milestone's mandate (determine the
minimum foundation, not deploy it everywhere it could apply), and
`coupled.py` carries its own byte-unchanged discipline this milestone
correctly declined to break on its own authority.

**The honest reading, stated in the terms the prereg's own §10 falsification
criterion set up:** H3 is neither cleanly confirmed nor cleanly falsified by
this milestone's own evidence. The primitive is built, correct, minimal, and
reuses existing fields rather than inventing new ones — which is why it
survives falsification with no `BLOCKER`. Whether it is *architecturally
necessary*, as opposed to *architecturally available and correct*, is a
question only a future consumer choosing to adopt it — or a future incident
in a *second* domain that a domain-local fix does not reach in time — can
settle. This document reports that limitation rather than rounding H3 up to
"forced" past what was actually measured.

---

# 8. Serialization impact

One new schema, no existing schema moved:

| Schema | Status |
|---|---|
| `variable_bulk_linkage/1` | **New.** No prior reader exists to break |
| `scientific_data_reference/1` | Unchanged |
| `scientific_result/2` | Unchanged |
| `scientific_problem/1` | Unchanged |
| `validation_check/1` | Unchanged |
| `validation_report/1` | Unchanged |

Asserted in `test_g6`. `VariableBulkLinkage.from_dict` uses strict
`require_schema` (exact match), not `require_schema_any` — there is exactly
one version and no compatibility surface to maintain yet. A future widening
(e.g., an optional axis field) would follow the same additive pattern
`scientific_result/2` already established, per the falsifier's C7
resolution.

# 9. Migration impact

None. No stored record format changed. No existing test was edited,
skipped, reordered or re-toleranced.

---

# 10. Tests

| Suite | Command | Before | After | Delta |
|---|---|---|---|---|
| Targeted | `pytest tests/test_min_cross_domain_foundation.py -q` | — | **42 passed** | +42 |
| FAST | `pytest tests/ -m "not expensive" -q` | **1422 passed**, 565 deselected | **1464 passed**, 565 deselected | **+42, 0 regressions** |
| FULL | `pytest tests/ -q -n auto` | **1960 passed**, 1 skipped, 12 failed, 14 errors | **2002 passed**, 1 skipped, 12 failed, 14 errors | **+42, 0 regressions** |

Both baselines were captured genuinely before any implementation file existed
on this branch (immediately after the FAST check above, before
`docs/min-cross-domain-foundation-prereg.md` was even committed). The FULL
delta is exactly `+42` with the failed/error counts unchanged, matching FAST
exactly — the pre-existing 12 failures and 14 errors are the same set,
before and after, confirmed by diffing the FAILED/ERROR test-id lists between
the two runs.

## 10.1 FULL suite and the pre-existing environment caveat

FULL was run four times on this branch: the true pre-implementation baseline
(§10, `12 failed, 1960 passed`), mid-implementation after `VariableBulkLinkage`
alone (`13 failed` — the domain-word leak this document's §7 records as an
intermediate, self-caught defect), after all three implementation commits
but before the vocabulary fix (`13 failed, 2001 passed`), and the final,
authoritative run after commit `90a4f07`:

```text
2002 passed, 1 skipped, 12 failed, 14 errors  (533.5 s, -n auto)
```

**All 12 failures and 14 errors are pre-existing and environmental, not
introduced by this milestone** — the identical set, by test id, in the
before and after runs. Every one is in `tests/test_heterogeneous_
ngspice.py`, and running that file standalone shows the exact cause:

```text
NgspiceUnavailable: could not launch the ngspice provider as
('wsl.exe', '-e', 'ngspice')
```

The test suite hardcodes a Windows WSL launcher command for the external
`ngspice` binary. This sandbox is Linux, with `ngspice` itself present and
working directly on `PATH` (confirmed: `ngspice-42` responds to `--version`)
— the failure is the launcher command, not the provider's absence. This
matches the same class of documented environment caveat prior milestones
already recorded (`docs/hostile-core-domain-stress-evidence.md`,
`docs/cross-domain-coverage-stress-evidence.md`: *"pytest's default temp
root is not writable in this sandbox... Environment, not code"*). Nothing in
this milestone touches `src/engcore/domains/electrical/` or
`tests/test_heterogeneous_ngspice.py`, confirmed by `test_g5`'s `git diff`
check covering the electrical DC tree.

**Regression count against the true pre-existing baseline**: zero. FAST
(which excludes the `expensive`-tagged `ngspice` suite entirely) is the
clean signal: `1422 → 1464`, exactly `+42`, no failures.

No pre-existing test was edited, skipped, deleted, reordered, or had a
tolerance loosened.

---

# 11. Evidence level, per abstraction

| Claim | Level | Why |
|---|---|---|
| `VariableBulkLinkage` correctly closes the measured binding gap when called | **`L1 EXERCISED`** | Built, executed against two probes and one real production `src/` producer (`thermal_conduction1d_bulk.py`), survives its reduction attacks |
| `VariableBulkLinkage` is architecturally *necessary* to any current production consumer | **`L0`, zero evidence** | Falsifier C1: no `src/` code outside this milestone constructs one |
| Mechanics and species force the *same* two-field shape | **`L1 EXERCISED`** | `test_e2` |
| `require_admission`/`is_admissible`/`admission_issues` correctly enforce a declared requirement when called | **`L1 EXERCISED`** | `test_i1`-`test_i6`, including a real CSTR solve |
| The negative-proof pattern (FAIL → refusal) is real and matches an already-executed incident | **`L1 EXERCISED`** | `test_j1`/`test_j2`, modeled on `HETERO-NGSPICE` §8.4 |
| `require_admission` is architecturally *necessary* to any current production consumer | **`L0`, zero evidence** | Falsifier C1/C2: zero callers; the real incident's fix remains domain-local |
| No new `ValidationLevel` member is needed | **`L1 EXERCISED`** | The rejection was tested, not merely argued (`test_h1`/`test_h2`) |
| SRIA admission and scientific admission share no type | **`L1 EXERCISED`** | `test_k1`/`test_k2`, independently re-verified by the falsifier's C9 |
| `ScientificProblem.validation_requirements` is populated and unconsumed in three shipped domains before this milestone | **`L1 EXERCISED`** | `test_h3`, and confirmed by direct source reading for all three domains |

**No abstraction that was never called from production code is assigned
anything past `L1`, and the specific claim "is architecturally necessary" is
assigned `L0` for both new pieces, honestly, per §7.1.**

---

# 12. Final decision and status

```text
Decision status:   PROPOSED
Evidence:          L1 EXERCISED (both abstractions correct-when-called;
                    architectural necessity is L0 — see §7.1, §11)
Milestone:         COMPLETE
```

**Verdict: KEEP both.** `VariableBulkLinkage` and `ValidationReport.
require_admission` are minimal, correct, reuse existing vocabulary
(`BindingIssue`, `validation_requirements`) rather than inventing new types,
touch no existing schema, and pass every reduction and negative test this
milestone and its two adversarial passes could construct. Neither is
adopted anywhere in production code yet, and that is reported as a real,
load-bearing limitation rather than smoothed over — a future milestone that
either wires one of them into a real consumer, or discovers a second
incident a domain-local fix does not reach in time, is the evidence that
would move either past `L1`.

**Not frozen.** `PROPOSED` means the design is available for use and
revision. In particular: `VariableBulkLinkage`'s no-axis-order shape and
`require_admission`'s exact-name matching are both places a real fourth
consumer should be expected to press on first.

---

# 13. Exact next steps this milestone hands forward

1. **Adoption, not new design.** If a future milestone wires
   `require_admission` into a real consumer (a coupling loop, an inference
   step, an SRIA-ingests-a-result adapter), that is the evidence needed to
   move H3 past `L0` on architectural necessity — this milestone deliberately
   did not do that retrofit itself.
2. **`FIELD0`/spatial fields remain the correct boundary.** Nothing here
   should be stretched to cover a genuinely interleaved, expensive-to-split
   bulk array (falsifier C7) — that is a `FIELD0`-scoped question, not a
   widening of `VariableBulkLinkage`.
3. **A second consumer for `ValidationOutcome`'s `NOT_RUN` vs.
   "intentionally not applicable"** (falsifier C6) remains unforced and
   should stay that way until one appears.
