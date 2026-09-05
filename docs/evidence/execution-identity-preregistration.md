# EXECUTION IDENTITY + REPRODUCIBILITY LOCK REFINEMENT: preregistration

**Written before any source change.** To be committed alone and not amended. Every
number below is either a **declaration** (measured on the unchanged tree at `139c9b9`,
stated so it can be re-measured) or a **prediction** (stated so a measurement can
contradict it). Each is labelled.

| | |
|---|---|
| Baseline commit | `139c9b9` (TRUST-HARDENING, PROPOSED, `L1 EXERCISED`) |
| Branch | `trust-hardening` (continues; this milestone is additive to it) |
| Sealed records not to be rewritten | `docs/evidence/trust-hardening-*.md`, `docs/evidence/propulsion0-*.md` |
| Scope | **Part 1** execution identity · **Part 2** reproducibility lock |
| Kind | hardening / decision. **No new physics, no new domain.** |
| Measured FULL at baseline | 2563 passed / 4 failed / 1 skipped, 783 s — all four failures environmental |

**The disposition this milestone is written to defend is that NOTHING NEW IS NEEDED.**
An `ExecutionManifest` is rejected unless §3's forcing criteria are met, and §3 is written
so that they can be met — a criterion that cannot fire is not a criterion.

---

## §0 What is already proved and is NOT re-attempted

- `ProvenanceRecord` carries `run_id`, `software_version`, `git_commit`, `models`,
  `solvers`, `bindings` (model + realization + solver), `inputs`, `assumptions`,
  `tolerances`, `environment`, `timestamp`, `parent_run_id`, `metadata`. The record is
  not re-litigated.
- A fresh process importing **zero** engcore modules replayed a whole shipped coupled run
  from existing records at **0 ULP**, measured under TRUST-HARDENING. The manifest is
  known to be *sufficient to reproduce*; this milestone asks a different question — is it
  sufficient to **read**.
- The applicability verdict, the admission decision, and the separation of numerical
  validation from scientific applicability were settled by TRUST-HARDENING and are not
  reopened. `AdmittedCoupledRun` is ephemeral by design.
- Exact floating-point reproducibility across BLAS kernels is already **measured
  impossible**: 19 `OPENBLAS_CORETYPE` kernels produce four distinct doubles at one
  pinned version tuple. Level 3 is not re-argued; §5 only decides what to *say* about it.

---

## §1 Fail conditions (any one is STOP-and-report)

| # | Condition |
|---|---|
| **F1** | any byte of `src/engcore/scientific/` changes |
| **F2** | any byte of `src/engcore/coupling/` changes |
| **F3** | any byte under `src/engcore/domains/` changes |
| **F4** | any byte of `src/engcore/systems/fluidthermal/` or `src/engcore/systems/propulsion/` changes |
| **F5** | a new record, dataclass or enum member is created anywhere |
| **F6** | a schema string is minted, or an existing schema version bumped |
| **F7** | `ValidationReport`, `ValidityAssessment` or `is_usable` changes meaning; applicability and validation are merged |
| **F8** | a published response key is removed or changes meaning |
| **F9** | machine identity — hostname, path, user, timestamp — is auto-collected anywhere |
| **F10** | an existing assertion is weakened or a tolerance loosened |

F9 is not stylistic. `provenance.py` states the policy: *"this module collects nothing on
its own … auto-harvesting machine identity would be both a privacy problem and a
determinism problem."* Anything recorded stays caller-supplied.

### 1.1 Permitted change set — exhaustive, and possibly empty

```
src/engcore/application/contract.py              Part 1, only if §4 forces it
tests/test_execution_identity.py                 new, the evidence
docs/evidence/execution-identity-preregistration.md   this file, committed alone
docs/evidence/execution-identity-evidence.md     written after execution
```

**No other file may change.** If the measurements force a change outside this list, that
is a STOP-and-report, not a widening.

### 1.2 Baseline failures that are NOT this milestone's to fix

Four, all environmental, all declared in the TRUST-HARDENING evidence §7.1: an untracked
file in the working tree, a Windows path-separator assertion, a cp1252 decode of
`git show`, and a sandboxed `subprocess.Popen` refusal.

---

## §2 Reconciliation — the declaration this milestone starts from

**There are two candidate artifacts, not one**, and they are not the same object:

| | internal `CoupledRun.to_dict()` | external `crafty_execution_response/1` |
|---|---|---|
| size, nominal run | 165 265 bytes | 9 348 bytes |
| who holds it | an in-process Direct Python caller | anything across HTTP or MCP — including an AI agent |
| persisted anywhere? | **no** — nothing in `scientific/`, `systems/`, `domains/`, `coupling/` or `application/` writes a file | no |

Measured by a records-only reader that imports no engcore module and parses no id string:

| Question | internal | response |
|---|---|---|
| 1. what model was executed | YES (5 models) | YES (5 models) |
| 2a. which realization | YES (2) | YES (2) |
| 2b. which configuration | YES (`max_iterations`, declared tolerance) | YES |
| 3. which solver / provider | YES (3, backends named) | YES (3, backends named) |
| 4. which inputs | YES (11 names) | YES (11 names) |
| 5. which operating conditions | YES (supply voltage) | YES (supply voltage) |
| 6. which environment | YES (30/30 leaves) | **NO — absent** |
| 7a. which validation decisions | YES (80 checks) | YES (8 checks) |
| 7b. which applicability / admission decision | **NO — absent** | YES (`assessed: true`) |

**Each artifact answers eight of nine. Their gaps are complementary and the union is
complete.** That is the whole of Part 1's finding, and it is why §3 exists rather than an
implementation plan.

**A correction, recorded because this preregistration would otherwise repeat it.** A first
pass of the reader reported "realization: NO" for the response. That was wrong: the
response *does* project `realization`, and the reader had inspected only the first two
bindings, which are DC models that legitimately have none. The run-level provenance
aggregates realizations correctly (2 of 5 model types have one). **The response's only
gap is `environment`, and `environment` is absent by omission rather than by decision —
the word does not appear in `contract.py` at all.**

---

## §3 Is `ExecutionManifest` forced? — the criteria, before the answer

A new first-class record is **FORCED** only if at least one holds. Each is written so a
measurement can fire it.

* **M1 — a fact reachable from neither artifact.** One of the seven questions cannot be
  answered from the internal record *or* the response.
* **M2 — the union is unobtainable.** Answering all seven requires holding both
  artifacts, and no shipped path produces both to the same consumer.
* **M3 — the union is unjoinable.** A records-only reader holding both cannot tell they
  describe the same execution, because no shared identifier survives into both.
* **M4 — the smallest fix requires a pinned tree.** Closing a gap needs an edit under F1–F4.
* **M5 — a named consumer.** A concrete reader needs a single record carrying all seven,
  and cannot be handed two. "A future auditor might" is not a consumer.

> **Prediction M-0.** **None of M1–M5 fires, and `ExecutionManifest` is REJECTED.**
> M1 fails because the union is complete (§2). M2 and M3 are open questions this
> milestone measures (Experiment A). M4 fails because the response's only gap is a
> projection in `contract.py`, which is unpinned. M5 is expected to fail because the only
> consumer that crosses a process boundary is the response, and the response is one
> record already.
> **Falsified if** any criterion fires on measurement.

---

## §4 Experiments

### Experiment A — fresh-process reconstruction, and the join

Executed by a reader importing **no** engcore module, parsing no id structure, reading no
`metadata`.

> **A-1.** From the response payload alone, a records-only reader answers six of the seven
> questions and **cannot** answer *which environment*. **Falsified if** it answers seven,
> or fewer than six.

> **A-2.** From the internal record alone, a reader answers six of seven and **cannot**
> answer *which applicability/admission decision*. **Falsified if** otherwise.

> **A-3 — the M3 test.** A reader holding both can join them: `run_id` appears in both
> and is equal. **Falsified if** no field is common and equal, which would fire M3 and
> would be the strongest argument for a manifest this milestone could produce.

> **A-4 — the M2 test.** No shipped path hands one consumer both artifacts: an
> HTTP/MCP caller receives only the response; a Direct Python caller holds the run object
> and can serialize the internal record but is never given the response.
> **Falsified if** a shipped path produces both, which would *weaken* M2 rather than fire it.

### Experiment B — environment variation

`OPENBLAS_CORETYPE` swept over the kernels this CPU supports, everything else held.

> **B-1 — Level 1 holds.** `CouplingOutcome`, `iterations_run`, every `ValidationCheck`
> outcome, and the applicability `ValidityStatus` are **identical across every kernel**.
> **Falsified if** any decision differs.

> **B-2 — Level 3 does not hold.** The converged temperature takes more than one distinct
> value across kernels. Declared: four distinct doubles were already measured on the FT
> case. **Falsified if** every kernel agrees bit-for-bit.

> **B-3 — Crafty records the difference.** `provenance.environment.blas_architecture`
> differs between two runs that produced different numbers, so a reader can attribute the
> difference. **Falsified if** two runs producing different numbers record identical
> environments — which is the defect that motivated recording it at all.

> **B-4 — but only where a producer fills it.** The exposed execution fills `environment`;
> most producers in the tree do not. **Falsified if** every producer fills it.

### Experiment C — identity removal attack

A result is constructed with, in turn, its solver identity, environment, inputs and
configuration removed, and pushed through everything that consumes a result.

> **C-1.** Crafty **does not currently refuse** a result whose identity is incomplete.
> `is_usable` stays `True`, `ValidationReport.status` stays `pass`, and the projection
> succeeds. **Falsified if** anything refuses.

> **C-2.** `ProvenanceRecord` **does** refuse the one identity fact it treats as
> load-bearing — a result without provenance cannot be constructed at all, because the
> module's own docstring says *"a number whose origin cannot be reconstructed is not a
> scientific result."* **Falsified if** a result can be built with no provenance.

C-1 passing is **not** by itself a reason to build a completeness gate. Whether an
incomplete-identity result *should* be refused is a decision, and this preregistration
takes the position that it should **not** be refused here: refusing on a missing optional
field would make `environment` mandatory across every producer in the tree, which is F3
and F4 several times over. The honest output is to *report* completeness, not to refuse it
— and only if §3 forces even that.

### Experiment D — composite identity

> **D-1.** Identity survives composition: in a multi-participant coupled run, **every**
> leaf carries its own model, realization, solver and inputs, and the run-level provenance
> aggregates models, solvers and bindings across all participants without loss.
> **Falsified if** any leaf loses identity, or the aggregate drops a participant.

> **D-2 — the previously suspected weakness is NOT present.** "Leaf records had trust
> information; composite runs lost it" was the stated concern. Declared measurement
> contradicting it: the run-level provenance carries 5 model bindings aggregated from 20
> leaf bindings, and 2 of 5 carry realizations — exactly the 2 model types that have one.
> **Falsified if** re-measurement shows aggregate loss.

The EV composite (battery + motor + thermal + controller) is **not** built to test this.
It would require the shared-DC-bus composition that `coupling/plan.py:215-221` refuses on
a torn set spanning two dimensions — F2 — and identity survival is measurable on the
composition that already ships.

---

## §5 Reproducibility — which levels Crafty should guarantee

| Level | Question | Position |
|---|---|---|
| **1 — Decision** | same PASS/FAIL, admission, applicability? | **GUARANTEE**, subject to B-1 |
| **2 — Scientific** | same metrics and physical conclusions, within a declared band? | **GUARANTEE**, subject to a declared band |
| **3 — Numerical** | same exact doubles? | **REFUSE TO GUARANTEE**, and say so in the artifact's own terms |

> **R-1.** Level 3 is not merely unguaranteed but **unachievable on this platform without
> pinning a fact no version number carries**. Declared: four distinct doubles at one fully
> pinned version tuple, differing only by `OPENBLAS_CORETYPE`.

The position this milestone defends: **reproducibility is an attribution claim, not a
determinism claim.** Crafty's job is to record what produced a number precisely enough
that a difference can be *attributed*, not to promise the number will not move. Level 1
and Level 2 are the guarantees a trust layer can actually keep.

**No reproducibility framework, tolerance registry or golden-file harness is built.** The
exposure is 7 long-float equalities in 3 files, of which 2 are environment-dependent, and
TRUST-HARDENING already repaired the one that had drifted.

---

## §6 Presumed unnecessary — reaching for any of these is a visible deviation

`ExecutionManifest`; a generic experiment, fault, environment or field framework; a new
solver abstraction; a new physics or mesh concept; a completeness-enforcement gate; a
`trusted: true/false` boolean anywhere; auto-collected machine identity; a store or
persistence layer.

A `trusted` boolean deserves its own refusal. It would collapse the five distinctions the
response contract exists to keep apart — transport success, execution success, numerical
convergence, coupling convergence, scientific validity — into one token, which is the
failure mode `CouplingOutcome` was minted separately to prevent.

---

## §7 Acceptance

**The expected and preferred outcome is that no source file changes.**

If measurement leaves the response unable to answer *which environment* for a consumer
that has no other artifact, the minimal implementation is **one projection in
`contract.py`**: publish the environment the execution recorded, aggregated from the
leaves the run already carries. No new record, no schema bump, no producer change.

KEEP only if:

1. No F-condition fired.
2. M-0 held, or the criterion that fired is named with its measurement.
3. A-1 … A-4, B-1 … B-4, C-1, C-2, D-1, D-2 and R-1 each held, or each failure is recorded
   as a deviation with the measurement that refuted it.
4. The change set is a subset of §1.1, and is empty unless §7's condition fired.
5. Reviewer and falsifier challenges were run against the *decision*, not against the
   implementation, and their findings are recorded at full strength.

---

## §8 Evidence ceiling

`L1 EXERCISED` for executed behaviour; `L0 REASONED` for every classification and every
position in §5. **No `L2`** — one execution, one composition. **No freeze, and no
promotion of any existing holding.**
