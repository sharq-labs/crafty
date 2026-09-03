# MINIMUM CROSS-DOMAIN FOUNDATION — Preregistration

**Milestone:** `MIN-CROSS-DOMAIN-FOUNDATION` — of the three candidates repeatedly
pressured by prior evidence (Variable↔Bulk Binding, Admissibility Attainment,
Enforced Admission), what is the *smallest* universal foundation actually
forced, and does any of it belong in core at all?
**Kind:** foundation-scoping milestone, building on `CROSS-DOMAIN-COVERAGE`,
`EXEC-SPEC-STRUCTURED`, `HOSTILE-CORE-STRESS` and `HETEROGENEOUS-NGSPICE`.
**Decision status target:** at most `PROPOSED`.
**Evidence target:** at most `L1 EXERCISED`. `L2` is excluded in advance — every
consumer here is exercised by one author on one branch, exactly the lineage the
repository's own convention excludes from `L2`.
**Date:** 2026-09-03
**Branch:** `min-cross-domain-foundation`, cut from `004e325`
(`origin/cloud/crafty-baseline`).

**Preregistered before implementation.** Everything below was written before
any source file was added or edited on this branch beyond this document.

> **This file is immutable.** What was decided *before* results were observed
> lives here. Deviations, corrections, adversarial findings and the final
> classification go in `docs/min-cross-domain-foundation-evidence.md` and
> nowhere else. This is **not** a freeze document.

---

## 1. The single question

> Of the three concepts four separate prior milestones have now pressured —
> Variable↔Bulk Binding, Admissibility Attainment, Enforced Admission — which
> ones are actually forced into universal core by executable evidence, in
> what *exact* minimal shape, and which are better answered by contracts that
> already exist or by a consumer/domain-local mechanism?

This is explicitly a **narrowing** milestone, not a green-field one. Every
candidate below already has a name, a corroboration count and a stated verdict
in `docs/cross-domain-coverage-stress-evidence.md`,
`docs/exec-spec-structured-input-stress-evidence.md`,
`docs/hostile-core-domain-stress-evidence.md` and
`docs/heterogeneous-ngspice-evidence.md`. Nothing here relitigates those
verdicts; this milestone spends the evidence they already produced and adds
one more executed data point per candidate, honestly attempted at zero new
contracts first.

---

## 2. What is already known, and is not re-derived here

Read as accepted background, cited rather than re-argued:

1. **`VariableToBulkLinkage`** — forced independently by six consumers across
   two milestones (`CROSS-DOMAIN-COVERAGE`'s A/B/C/D, `EXEC-SPEC-STRUCTURED`'s
   mechanics and species columns), `UNIVERSAL-CANDIDATE`, `Ledger 1`, never
   implemented. Narrowed twice already: it is not a container problem — an
   ordered index set of named entities is already representable via
   `ScientificVariable.categories` — and the residue is specifically a
   *binding*: nothing states that a `ScientificDataReference`'s flat values
   are the values of a named `ScientificVariable`, in what order.
2. **`AdmissibilityAttainment`** — forced by four of six consumers in
   `CROSS-DOMAIN-COVERAGE` (the two controls score `P`, not `F`, because they
   carry no result to read), `UNIVERSAL-CANDIDATE`, `Ledger 1`. The measured
   asymmetry: `ValidationLevel` has seven members and none denotes physical
   admissibility, so a *passing* admissibility check has nowhere to register
   (`establishes=None`) while a *failing* one is fully expressible
   (`outcome=FAIL`). Explicitly `DEFER`red twice before now, on the stated
   ground that adding a `ValidationLevel` member is additive and must not be
   rushed ahead of a consumer that needs to *gate* on it.
3. **Detection ≠ Enforcement, executed and fixed once already.**
   `docs/heterogeneous-ngspice-evidence.md` §8.4 ran a provider that halved
   its reported element power through the coupled electro-thermal loop. The
   validation report correctly flipped to `FAIL`. The loop transported the
   value anyway and converged confidently 18.052948 K away from the honest
   answer, because *"the loop reads `result.value(...)` and does not read
   validation reports — nor should it have to. A check whose only effect is a
   field nothing consults is not a guard."* The fix that shipped was
   **domain-local**: the reconciliation moved into `extract_metrics`, and a
   violation now **raises**, so no `ScientificResult` is ever synthesized for
   the coupling loop to read. No universal core contract was touched.
4. **An existing, unconsumed core field.** `ScientificProblem` already
   declares `validation_requirements: frozenset[str]` (a name-only set of
   which checks a result must satisfy). All three shipped domains
   (`electrical/dc`, `thermal/conduction1d`, `kinetics/cstr`) populate it, and
   `kinetics/cstr`'s validator produces `ValidationCheck` records whose
   `name`s are the *literal same strings*. Nothing in the repository
   cross-references the two. `ScientificResult.is_usable` checks convergence
   and "no failed check" globally; it does not check that a *specific*
   declared requirement was even run.

Points 3 and 4 are the strongest inputs this milestone starts from, and they
were not built for this milestone — they were found while reading the
existing evidence and the existing contracts before writing this document, as
the mission requires (§A1: "check what's actually available"; §A3: "ask
whether existing contracts already represent each").

---

## 3. Hypotheses

**H1 — Variable↔Bulk Binding is forced, and its minimal shape is a standalone
two-name binding record, not a container, not a field on
`ScientificDataReference`, and not solved by `ScientificVariable.categories`
alone.**

**H2 — Admissibility Attainment does *not* force a new `ValidationLevel`
member.** The evidentiary-strength axis (`UNVERIFIED` →
`EXPERIMENTALLY_VALIDATED`) already has a place to put a passing admissibility
check (`DIMENSIONALLY_VALID` at minimum, or no level at all — precedent:
`kinetics/cstr`'s own admissibility check already runs with
`establishes=None`). What is missing is not a stronger evidentiary claim; it
is that nothing enforces the check ran and passed *before* the result is
used. Rejecting a new enum member is falsifiable: if a real consumer needs to
compare admissibility strength across two results (as opposed to gating
consumption on one), that would force a level.

**H3 — Enforced Admission is forced, and its minimal shape is not a new
record.** It is a function (or method) that cross-references two fields that
already exist and are already populated —
`ScientificProblem.validation_requirements` and
`ScientificResult.validation.checks` — and raises when a declared requirement
was not run, or ran and did not pass. This is smaller than `H0` in the
governing task spec because it reuses two typed fields the platform already
ships rather than inventing an admission-decision record.

**H0(A) — Zero contracts survive everywhere.** If H3's cross-reference is
already achievable by composing `ValidationReport.require_level` and
`ScientificResult.is_usable` without a new method, no new code is forced at
all beyond a test proving it. Predicted to fail, because `require_level`
checks *levels*, not *named requirements*, and `is_usable` checks the report
*globally*, not against a *specific declared set of names* — a result could
satisfy `is_usable` while a `NOT_RUN` requirement the problem explicitly
listed was never assessed at all, and nothing today reports that.

**H0(B) — the new abstractions, if built, are domain vocabulary in
disguise.** Refuted if `VariableBulkLinkage` and the admission method survive
a lexical scan for domain words and a construction using a domain this
milestone does not import.

---

## 4. Zero-new-contract attempts committed to *before* implementation

Each will be attempted, executed as a test, and its failure mode recorded —
not asserted from prose, per the repeated correction in every prior milestone
that skipped this step.

### 4.1 Variable↔Bulk Binding

| # | Attempt | Predicted outcome |
|---|---|---|
| 1 | `ScientificDataReference.name` as a descriptive string (`"c:A:trajectory"`) with no further record | **REJECTED** — a records-only reader cannot parse a name into a typed `ScientificVariable` reference without the string-parsing this platform repeatedly refuses (`meaning-in-key`, per `EXEC-SPEC-STRUCTURED` §C) |
| 2 | `ScientificVariable.categories` alone, no binding record | **REJECTED, but informatively** — categories give an ordered named-member *set*; nothing states that a *specific* `ScientificDataReference` instantiates that variable at all |
| 3 | `ScientificParameter` carrying the reference name as a string value | **REJECTED** — a parameter value is data, not a typed cross-reference; nothing checks it resolves or is dimensionally consistent |
| 4 | `ScientificResult.metadata` | **REJECTED** — untyped escape hatch, explicitly banned everywhere else in this codebase |
| 5 | Splitting one combined array into N per-variable `ScientificDataReference`s, one per named quantity, relying on the reference's own free-text `name` to imply which variable | **PARTIALLY WORKS for identity, still fails to close the gap** — `DATA-BOUNDARY0` explicitly sanctions free-text scientific names (`phase/alpha`, `species:H2O`), but a free-text name is still not a *typed, checked* cross-reference to a declared `ScientificVariable`; the reduction is recorded because it changes what the minimal binding record needs to carry (nothing about interleaving/stride, since each reference then holds exactly one variable's values) |

### 4.2 Admissibility Attainment / Enforced Admission

| # | Attempt | Predicted outcome |
|---|---|---|
| 1 | `ValidationReport.require_level(...)` | **REJECTED as a full solution** — it gates on an evidentiary *level*, and admissibility checks in every shipped domain deliberately `establishes=None` (recorded, correctly, as not being evidence about numerical adequacy) |
| 2 | `ScientificResult.is_usable` | **REJECTED as a full solution** — global over the whole report (any `FAIL` anywhere flips it), not scoped to the *specific* names a problem declared required; a `NOT_RUN` requirement does not by itself flip `is_usable` unless something else in the report also fails |
| 3 | `ScientificProblem.validation_requirements` read manually by each consumer | **REJECTED as a universal answer, though it is what `kinetics/cstr`'s verification gate already does ad hoc** — `run_verification_gate` hand-rolls exactly this cross-reference once, which is itself evidence a shared primitive is warranted rather than evidence none is needed |
| 4 | A new `ValidationLevel` member (`PHYSICALLY_ADMISSIBLE` or similar) | **REJECTED, see H2** |
| 5 | A new universal `AdmissionDecision` record, modeled on `sria.admission.AdmissionDeclaration` | **REJECTED in advance unless forced** — SRIA's admission machinery authenticates *who* may accept an *evidence record* into a design campaign (issuer signatures, one-way authorization commitments); it answers a governance question, not a scientific one, and conflating the two was explicitly forbidden by the governing task. The smallest shared invariant, if any, is recorded as a *principle* (fail closed on an unmet declared requirement), not a shared type |

---

## 5. Forcing conditions

A candidate proceeds past zero-contract only if **all** of the following are
measured, not argued:

- **F1 (existence of the gap).** At least two materially different existing
  consumers (not invented ones) exhibit the same unrepresentable or
  unenforced fact.
- **F2 (residue, not container).** The exact fact that cannot be expressed is
  named precisely — not "arrays need a home" but the specific missing
  cross-reference or the specific missing enforcement call.
- **F3 (reduction survives).** The zero-contract attempts in §4 are executed,
  not merely reasoned about, and their failure is demonstrated by a test.
- **F4 (no cheaper existing-contract answer).** Nothing already shipped
  (`ValidationReport`, `ScientificVariable.categories`,
  `ProvenanceRecord.bindings`, `QuantityDependency`) already answers the
  question under a different name.

## 6. Rejection conditions

A candidate is **rejected** (recorded as `DEFER` or `REJECT`, nothing built)
if any of:

- The gap is representable using an existing typed contract once actually
  attempted (not merely asserted representable in a prior document).
- The gap is real but the fix that closes it is domain-local and does not
  generalize — the `HETERO-NGSPICE` precedent (§2.3) is the standing example
  of exactly this outcome, and this milestone must show it either does or
  does not generalize rather than assume it either way.
- Closing it would require bulk data, mesh, topology, shape or support
  semantics — those stay deferred per `DATA-BOUNDARY0`,
  `HOSTILE-CORE-STRESS` and `CROSS-DOMAIN-COVERAGE`, and any candidate that
  drifts there is rescoped down rather than built.
- Fewer than two materially different consumers force it at execution time
  (not at design time).

---

## 7. Consumers used for A1 (Variable↔Bulk Binding)

Per the governing task's own instruction, real already-existing consumers are
used rather than an invented domain:

1. **`experiments/cross_domain_coverage/mechanics.py`** — CASE A2 shear.
   Eight-value displacement field over four nodes × two components
   (`u_x`, `u_y`). Committed at `38783ed`; **not edited by this milestone.**
2. **`experiments/cross_domain_coverage/species.py`** — CASE C1. A
   three-species concentration trajectory, `(c_A, c_B, c_C)` over N output
   points. Committed at `38783ed`; **not edited by this milestone.**
3. **`src/engcore/domains/thermal_conduction1d_bulk.py`** — the one existing
   *production* `src/` producer of a `ScientificDataReference`
   (`solve_slab_with_bulk_field`), single-variable, over the frozen,
   byte-pinned `thermal/conduction1d` solver. **Not edited.** Used only to
   prove the binding record works against a real shipped producer, not only
   against a probe.

If a third structured consumer proves cheap and informative once (1) and (2)
are attempted, it is added; none is invented in advance.

---

## 8. Reduction tests (to be executed, not reasoned)

For every abstraction actually built:

- **R1.** Remove it; show the specific fact it carried becomes either
  unrepresentable, string-parsed, or silently ambiguous — with a failing test
  demonstrating which.
- **R2.** Show it survives being fed a consumer from a domain this milestone
  does not import (mirrors `MIN-FOUNDATION-ET`'s `test_d3` and
  `EXEC-SPEC-STRUCTURED`'s isolation guard).
- **R3.** Show it adds no field a lexical AST scan flags as domain vocabulary.
- **R4.** Show it does not duplicate an existing record (`BindingIssue`,
  `ValidationCheck`, `ScientificDataReference`) — reuse over duplication,
  exactly as `QuantityDependency` reused `BindingIssue` rather than minting a
  parallel type.

## 9. Negative test (A5, mandatory)

A `ScientificResult` is constructed whose `ValidationReport` contains a check
matching one of the owning problem's `validation_requirements` names, with
`outcome=FAIL` (or `NOT_RUN`) — plausible-looking numeric values, e.g. a
negative species concentration or a resistance-derived power outside a
declared admissibility bound, chosen to resemble the already-executed
`HETERO-NGSPICE` 18 K incident and the `kinetics/cstr`
`state_physically_admissible` check. A downstream "consumer" (a small
function standing in for a coupling loop or an inference step) is required to
call the new admission primitive before using `result.value(...)`.

Required outcome, proven by the test actually catching an exception:
`FAIL → require_admission(...) raises ScientificValidationError → the
consumer function never reaches its use of the value`.
Forbidden outcome: a warning, a log line, or a boolean the consumer is free to
ignore.

A companion test constructs the same scenario **without** calling the new
primitive, to show the silent-consumption failure mode is real and structural
(not hypothetical) absent the guard — mirroring the `HETERO-NGSPICE` "before
fixing" measurement.

---

## 10. Falsification criteria

- **H1 falsified** if the two consumers in §7 do not force the *same* residue
  (e.g. one needs ordering information the other does not, in a way no single
  minimal record covers) — in which case the record is either widened with a
  measured justification or the milestone reports two distinct, smaller
  findings instead of one.
- **H1 falsified** if `ScientificVariable.categories` plus the existing
  `ScientificDataReference.name` string, used together, are found to close
  the gap without a records-only reader ever parsing a name — this would be
  a genuine H0(A) win and is actively tested for, not assumed impossible.
- **H2 falsified** if a real consumer (not hypothesized) needs to *rank* or
  *compare* two admissibility checks, rather than merely gate on one — in
  which case a `ValidationLevel` member is reconsidered on that evidence.
- **H3 falsified** if the `HETERO-NGSPICE` pattern (fix at the domain-local
  boundary, no core change) is found to fully generalize — i.e., if every
  consumer this milestone builds can be made safe by a domain-local `raise`
  with no shared primitive, then H3 is downgraded to "domain-local pattern,
  not core", and that is reported as the answer rather than forced anyway.
- **Any candidate** is dropped if it drifts toward `FIELD0`, `TOPO0`,
  `DISC0`, `EQIR0`, a generic relation/matrix artifact, a component/connector
  framework, a planner, or a fluid domain (§A8 non-goals).

## 11. Expected evidence level

At most **`L1 EXERCISED`**. `L2 DIFFERENTIATED` is excluded in advance: every
consumer touched here is examined by one author on one branch, which is
exactly the lineage `docs/cross-domain-coverage-stress-evidence.md` §14 and
`docs/min-foundation-electrothermal-evidence.md` §13 both name as
insufficient for `L2`. Decision status will be recorded as `PROPOSED` and
explicitly **not** `DESIGN-FROZEN`, regardless of outcome.

## 12. What is out of scope regardless of outcome

Per the governing task's non-goals (§A8), restated here as a binding
preregistered constraint: no `ScientificField`, mesh, topology, Equation/
Relation IR, `MatrixValue`, `StructuredScientificValue`, component/connector
framework, generic planner, fluid domain, API/MCP/UI, provider framework,
runtime scheduler or HPC framework. If any candidate's honest minimal shape
turns out to require one of these, the candidate is rescoped down or dropped,
not built anyway.

## 13. Review and falsification plan

`architecture-decision-reviewer` is invoked once, after the zero-contract
attempts and the reduction tests have produced measurements — not before —
on the three candidates as framed by this document, each compared against
its existing-contract alternative and a domain-local alternative.

`architecture-falsifier` is invoked once against whatever is actually built,
with the primary challenge: *"These concepts only appear universal because
the four prior milestones kept selecting consumers that exhibit them — show
the corroboration is real, not selection."* At most one further corrective
round follows either invocation, per the governing task's two-round limit
across A7+A9; after that, the executed evidence stands as reported, including
any BLOCKER closed by narrowing or dropping rather than by adding scope.

## 14. Tests

Targeted tests for whatever is built, then FAST (`pytest tests/ -m "not
expensive"`), then FULL (`pytest tests/`), using the project's own virtual
environment. Baseline recorded before any implementation commit:

```text
FAST (not expensive):  1422 passed, 565 deselected
```

FULL baseline is recorded in the evidence document once the background
measurement in this session completes; no existing test is skipped, reordered
or loosened, and any FULL-only failure introduced by this milestone is fixed
in the new code, never in an existing test.

---

## 15. Git

This document is committed alone, as the first commit on this branch beyond
the verified baseline, with message "Preregister minimum cross-domain
foundation". Implementation, tests and the evidence document follow in
separate, separately-described commits.
