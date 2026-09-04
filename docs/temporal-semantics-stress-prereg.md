# TEMPORAL SEMANTICS STRESS — Preregistration

**Milestone:** `TEMPORAL-SEMANTICS-STRESS`
**Kind:** discovery / decision. **No architecture will be implemented.**
**Decision status:** none. This milestone freezes nothing and promotes nothing.
**Branch:** `temporal-semantics-stress`
**Baseline:** `origin/cloud/crafty-post-field-support` @ `6caa113`
(2102 passed / 0 failed / 0 errors).

> This document is written **before** any probe, test or experiment file on this
> branch exists. It is **immutable** once committed. Every divergence between
> what is predicted here and what is measured is recorded as a deviation in
> `docs/temporal-semantics-stress-evidence.md`, never back-written into this
> file.

---

# 0. Hard scope rule

Writable in this milestone: `experiments/**`, `docs/**`, and test files
dedicated to this stress. **Nothing under `src/` may be created, edited or
deleted**, universal Scientific Core (`src/engcore/scientific/**`) most of all.

If measurement concludes that a core contract must change, that conclusion is
recorded as a **RECOMMENDATION for a future milestone**. It is not implemented
here. A recommendation that arrives with an implementation is a violation of
this preregistration, not a bonus.

---

# 1. The single question

> **What is the smallest universal temporal semantics actually FORCED by
> multiple materially different sciences already executing in this
> repository?**

The question is deliberately *not* "which temporal classes should Crafty
have". Candidate names — `TimeDomain`, `TemporalState`, `Timeline`, `Event`,
`History`, `TimeSeries` — are named here **only so that this document can
record that none of them is admitted as evidence**. A name is not a
measurement. Every residue below is required to be reached from executed
consumer behaviour, and any residue that can only be described by naming a
class it would need is recorded as **NOT FORCED**.

A prior audit scored Temporal Readiness 1/5 with Physical Time / Solver Time
Step / Optimization Iteration PARTIAL, Coupling Iteration
PARTIAL-but-structurally-distinguished, and Wall-clock Runtime / Time-varying
Input / History / Events / Accumulated Exposure / Aging MISSING. **That audit
is not evidence for this milestone.** It is restated once, here, as the prior
to be re-measured executably, and the evidence document must report its own
measurement even where that measurement contradicts the audit.

---

# 2. Consumers, fixed before execution

Four, all pre-existing, all already executed in the baseline suite. No consumer
is invented for this stress; no fifth is added to inflate a count.

| # | Consumer | Governing form | Physical time enters as | Author lineage |
|---|---|---|---|---|
| **C1** | `engcore.domains.thermal_lumped` | linear 1st-order ODE, closed form `T(t)=T_ss+(T0−T_ss)e^{−t/τ}` | `duration` `ScientificParameter` + one `InitialCondition` | `MIN-FOUNDATION-ET` |
| **C2** | `engcore.domains.kinetics.cstr` | stiff 2-state nonlinear ODE, `scipy.solve_ivp` BDF/Radau adaptive | `ReactorOperation.end_time`, domain-local | `KINETICS-K1..K4` |
| **C3** | `engcore.systems.electrothermal.coupled` | Gauss–Seidel/Picard fixed point over a torn dependency cycle | *not at all* — the iterate is not a time level | `ET-VERTICAL` |
| **C4** | `experiments/cross_domain_coverage/dynamics.py` | index-3 constrained DAE, fixed-step RK4 | `end_time` parameter + four `InitialCondition`s at `t=0` | `MIN-CROSS-DOMAIN` |

**Material difference is claimed on four independent axes** and will be
asserted in the evidence document with the measured facts backing each:
governing mathematics (linear ODE / stiff nonlinear ODE / algebraic fixed point
/ index-3 DAE); time discretisation (none — closed form / adaptive implicit /
none — no time axis / fixed-step explicit); solver backend (`math.exp` /
`scipy.integrate.solve_ivp` / hand-written Picard loop / hand-written RK4); and
authoring milestone. C3 is included **precisely because it has no physical time
axis** — a temporal stress that only sampled time-marching consumers could not
separate physical time from iteration.

A fifth consumer is admitted only if a probe *requires* it to decide a
question, and the evidence document must then state which question. Two
candidates are named in advance and both are expected to stay unused:
`domains/fluids/transport2d` (declared steady; contributes a negative control
at most) and `domains/thermal/conduction1d` (byte-pinned by frozen experiments
T1/T2/T3 — **must not be touched or imported in a way that changes it**).

---

# 3. Measured-baseline facts to be re-verified, not assumed

These were read from source while writing this preregistration. They are stated
as **predictions to be re-verified executably**, because a fact read from a
docstring is not a measurement.

| B# | Predicted baseline fact | Where |
|---|---|---|
| B1 | `ScientificProblem.is_time_dependent` is **derived solely from `initial_conditions` being non-empty** | `ir/problem.py` |
| B2 | `build_cstr_problem` declares **no `InitialCondition` and no `end_time`** anywhere on the universal problem, so a genuinely transient stiff integration reports `is_time_dependent is False` | `kinetics/cstr/problem.py` |
| B3 | `InitialCondition.time` exists as `Quantity \| None` and is **unvalidated against anything** — no dimension check, no ordering, no relation to any other record | `ir/conditions.py` |
| B4 | C1 spells time levels into metric names: `temperature` (t₀ state), `final_temperature` (t=duration), `steady_state_temperature` (t→∞); all kelvin | `thermal_lumped.py` |
| B5 | C2 spells time levels into metric names with a different convention: `C_A:final`, `T:final`, `T:max`, `t:T_max` | `kinetics/cstr/problem.py` |
| B6 | `ThermalBody.physical_key` **excludes** `duration`; `ReactorRun.physics_fingerprint` **includes** `end_time_s`. Two consumers disagree on whether the horizon is scientific identity | C1 vs C2 |
| B7 | `IntegrationSettings.n_output_points` is documented as reporting resolution that never changes the integration path, and travels as **metadata**, not as a parameter | C2 |
| B8 | `RawSolverOutput` carries `iterations` and `wall_seconds`; `ScientificResult` carries **neither** | `solvers/protocol.py`, `results/result.py` |
| B9 | C2's dense trajectory (`TransientTrajectorySample`) is domain-local, never serialised, and **not** reachable from any universal record | `kinetics/cstr/solver.py` |
| B10 | `ScientificDataReference` carries `{name, unit, count, dtype, digest, digest_algorithm}` and **no time coordinate, ordering statement or sample-index semantics** | `results/data_reference.py` |

Any of B1–B10 that fails to reproduce is a deviation and is reported as one.

---

# 4. The temporal questions

Each question is answered by executed behaviour, and each has a stated
"answered NO by" condition so it can lose.

| Q | Question | Answered NO by |
|---|---|---|
| **Q1** | Are Physical Time, Solver Time Step, Coupling Iteration, Optimization Iteration and Wall-clock Runtime **behaviourally** distinct — i.e. can one be varied while the others are held fixed, with a measurable, differently-signed consequence? | any pair that cannot be independently varied, or whose variation produces indistinguishable records |
| **Q2** | Can a records-only reader state *at what time level* a reported value holds, without parsing a metric name, reading metadata, or importing the domain? | if it can |
| **Q3** | Can a time-varying input (`ambient_temperature(t)`, feed `T_f(t)`, drive torque `τ(t)`) be encoded with `ScientificParameter` / `ScientificVariable` / `ScientificProblem.data_references` / `VariableBulkLinkage` **without** metadata, callables, arbitrary Python, or source-code interpretation? | if a full encoding exists |
| **Q4** | Can two histories reaching the **same current scalar state** be distinguished by any current typed contract, when a history-dependent quantity differs between them? | if any typed contract separates them |
| **Q5** | Can "an event occurs at physical time t_e" and "before vs after the event" be stated without hiding it in solver code? | if any typed contract states it |
| **Q6** | Is an accumulated exposure `E(t)=∫₀ᵗ f(T(τ))dτ` a state variable, a derived observable, a history, or a relation result — decided by what existing contracts express? | n/a — this is a classification, and "all four are equally expressible" is a legitimate answer |
| **Q7** | Can `data_references` + `VariableBulkLinkage` say *what* a bulk time history is, but not *when* each sample exists? Which of {variable identity, sample ordering, time coordinate, storage layout, physical-time semantics} is expressible? | if the time coordinate is recoverable from a universal record |
| **Q8** | Does the prose-only scalar/bulk precedence rule become ambiguous or unsafe when stressed temporally (scalar t₀ + non-uniform initial field; representative scalar input + time-varying bulk series)? | if no ambiguous case can be constructed |
| **Q9** | Which of {start time, duration, time coordinate, time-varying boundary/input, event schedule, solver dt, output sample interval} change **scientific identity**, as opposed to execution specification, result sampling, or runtime policy? | n/a — classification |
| **Q10** | Does the science **separate** the residues, or is one generic temporal object the honest minimum? | if the residues cannot be varied independently of one another |

---

# 5. Forcing criteria — binding

A measured residue is recorded as **FORCED** only if **all five** hold. Any
residue failing one is recorded at its actual strength (`OBSERVED`,
`SINGLE-CONSUMER`, `NOT FORCED`) and explicitly refused as a contract
recommendation.

* **F1 — Multiplicity.** At least **two** of C1–C4 exhibit it, and those two
  are materially different on at least two of the four axes in §2.
* **F2 — Records-only irrecoverability.** A reader holding only
  `ScientificProblem` / `ScientificResult` / `ScientificDataReference` /
  `VariableBulkLinkage` / `QuantityDependency` / `RawSolverOutput`, importing
  no domain module, parsing no name's internal structure, and reading no
  metadata, cannot recover the fact.
* **F3 — Steelman exhausted.** A maximal honest attempt with the existing
  typed contracts (§6) has been executed and has failed, or has produced an
  ambiguity that no dimension check can catch.
* **F4 — Boundary-safe.** The fact is O(1) in history length; or, if O(N), it
  is demonstrated that it must live **outside** the universal control-plane
  record, preserving DATA-BOUNDARY0.
* **F5 — Named consumer of the fact.** A concrete downstream reader needing it
  is named — planner, reconstruction, composition/transport, cross-result
  comparison, or validation. "A future system might" is not a consumer.

**Two-ledger rule** (inherited from `HOSTILE-CORE-STRESS` §10.1). Every finding
is booked in exactly one of two ledgers and the evidence document keeps them
visually separate:

* **Ledger A — measured residue**: a fact a records-only reader demonstrably
  could not recover, with the executed attempt attached.
* **Ledger B — expressible after all**: a fact the steelman *did* encode. These
  are recorded with equal prominence. A milestone that reports only Ledger A is
  not measuring; it is advocating.

---

# 6. Zero-new-contract attempts — required before any residue is declared

Each is executed. Each records what it achieved (Ledger B) as well as what it
could not (Ledger A).

* **Z1** — Encode the time level of a value by **enumerated metric name**
  (`final_temperature`, `T:final`) and ask a records-only reader to compare two
  results at "the same time level". *Predicted: fails; two conventions already
  disagree (B4 vs B5), and neither is parseable without meaning-in-key.*
* **Z2** — Encode the time level as a distinct `ScientificVariable` per level
  (`temperature_t0`, `temperature_t1`), relying on `ScientificVariable.name` +
  `role`. *Predicted: representable; the relation "same physical quantity,
  different time" is not.*
* **Z3** — Encode `t` as an ordinary `ScientificParameter` carrying seconds,
  and the sampled input as a second parameter. *Predicted: expresses a value at
  a time, never a function of time.*
* **Z4** — Encode a time-varying input as **two** `ScientificDataReference`s
  (one values array, one time array) bound by two `VariableBulkLinkage`s to two
  declared variables. *Predicted: variable identity and unit succeed; the
  pairing "sample i of A corresponds to sample i of B" and "B is the
  independent coordinate of A" do not.*
* **Z5** — Encode an event with `InitialCondition.time` on a second problem
  segment (problem-splitting at `t_e`). *Predicted: representable as two
  problems; the fact that they are two segments of one physical timeline, and
  the discontinuity between them, is not.*
* **Z6** — Encode accumulated exposure as (a) a `STATE` `ScientificVariable`
  with an `InitialCondition` of 0, and (b) an `OBSERVABLE` metric on the
  result. *Predicted: both encode; nothing distinguishes them, which is itself
  the finding.*
* **Z7** — Encode history distinguishability with `QuantityDependency` chains
  between per-segment problems. *Predicted: expresses supply, not order or
  elapsed time.*
* **Z8** — Encode a non-uniform initial field **and** a scalar
  `InitialCondition` for one variable, plus a representative scalar input and a
  time-varying bulk series, and ask a records-only reader which is
  authoritative. *Predicted: the prose rule is unreadable by any reader; the
  temporal case additionally has no rule at all, because the existing prose
  covers spatial non-uniformity.*

---

# 7. Predictions, stated so this milestone can lose

Each is falsifiable. The evidence document reports HELD / REFUTED for each.

* **P1** — All five of {physical time, solver step, coupling iteration,
  optimization iteration, wall-clock} are behaviourally separable. **Risk of
  loss:** optimization iteration may have no executed consumer in this
  repository at all, in which case P1 is REFUTED for that member and it is
  reported as *not measured here*, not as *distinct*.
* **P2** — A concrete time-level collision exists with **identical dimension,
  identical physical variable, different temporal meaning**, indistinguishable
  by typed contracts. **Risk of loss:** if `ScientificVariable.role` or
  `metric_units` separates them after all.
* **P3** — Time-varying input has a **non-empty** residue after Z3+Z4.
  **Risk of loss:** if the two-reference + two-linkage encoding is judged
  complete for a records-only reader.
* **P4** — Two histories with equal current state, unequal exposure, are
  indistinguishable by every current typed contract. **Risk of loss:** if any
  contract (provenance `parent_run`, `QuantityDependency` chains) recovers the
  distinction.
* **P5** — At least one residue is **NOT** forced by ≥2 consumers, i.e. the
  honest answer includes refusals. A milestone in which every candidate is
  forced is evidence of a badly designed instrument, and the evidence document
  must say so if that happens.
* **P6** — The science **separates** at least two residues (they vary
  independently), so outcome (G) "one giant TemporalModel" is not the minimum.
  **Risk of loss:** if every residue turns out to require every other.
* **P7** — `wall_seconds` is runtime policy, not scientific identity, and this
  is provable by showing two runs with identical science and different
  `wall_seconds`.

---

# 8. Falsification criteria for the milestone itself

This milestone **fails** — and must say so — if any of:

* A residue is declared FORCED without an executed steelman attempt (F3).
* A residue is declared FORCED on one consumer (F1).
* A recommendation is made whose motivating fact a records-only reader could
  in fact recover (F2 violated).
* Any file under `src/` is created, edited or deleted.
* The recommendation section names a contract that no measured residue
  requires.
* Ledger B is empty. That would mean the instrument found nothing expressible,
  which for a platform with an executed transient ODE consumer is implausible
  and indicates the instrument, not the platform, is broken.

---

# 9. Explicitly forbidden in this milestone

No `TimeSeries`, `TimeDomain`, `Timeline`, `TemporalState`, `Event`,
`EventSchedule`, `History`, `Trajectory` or `TemporalModel` type is defined,
even in `experiments/`. No event engine. No tire wear, fatigue, aging, battery,
corrosion or damage physics. No interpolation, resampling or transfer operator.
No scheduler. No time-synchronisation runtime. No modification of the frozen
thermal tree. No universal record is made to scale O(N) with history length.

The accumulated-exposure probe (A6) is limited to a **single scalar
accumulator** `E(t)=∫₀ᵗ f(T(τ))dτ` with `f` a fixed, declared, monotone
function of temperature, computed by trapezoid over an already-computed
trajectory. It is an instrument for a representation question, not a degradation
model, and the evidence document must state that it makes no physical claim.

---

# 10. Evidence ceiling, declared before running

* **L1 EXERCISED** — maximum, and only for the behaviour the probe pack itself
  executes.
* **L0 REASONED** — everything else, including every recommendation, every
  refusal, and every classification in A9/A11.
* **No L2, no L3.** One author, one repository, four consumers of which three
  were written by the same lineage of milestones.
* **No existing holding is upgraded.** DATA-BOUNDARY0 stays `L1`;
  MIN-FOUNDATION-ET stays `L1`/`L0`; MIN-FIELD-SUPPORT stays where it is.
* The recommended minimal temporal foundation is delivered at **`PROPOSED`,
  not built**, and its own evidence level is stated separately and may be lower
  than L1 because nothing implements it.

---

# 11. Reversal conditions — when this milestone's conclusions must be revisited

Stated in advance so that a later milestone can check them mechanically.

* **R1** — A fifth consumer whose physical time is not a scalar interval
  (cyclic/periodic time, multiple independent time scales, retarded time,
  frequency-domain) executes. The independent-coordinate finding must be
  re-measured; a scalar-only conclusion does not survive it.
* **R2** — Any planner, execution-plan compiler or scheduler is implemented.
  F5 changes meaning the moment a universal reader exists.
* **R3** — A second coupled consumer executes with a coupling iterate that *is*
  advanced in physical time (a true time-marching co-simulation). The
  coupling-iteration/physical-time separation measured on C3 alone would then
  rest on a consumer that is no longer representative.
* **R4** — A consumer needs to *compare* two results at a common time level
  across domains. Today no consumer does; that is the main reason a time-level
  contract can be deferred, and it is the reason that would end.
* **R5** — Bulk time histories are required to cross a process or storage
  boundary as scientific claims rather than as domain-local gate evidence.
  B9/Q7 would then be load-bearing.
* **R6** — Any consumer needs to reconstruct a result from its records alone
  (replay/audit). History-vs-state stops being a representation question and
  becomes a reconstruction requirement.

---

# 12. Required probes, tests and output

**Probes** — under `experiments/temporal_stress/`:

* a records-only temporal reader (no domain imports, no name parsing, no
  metadata reads) — the instrument for F2;
* a separation probe exercising C1–C4 for Q1;
* a two-history exposure probe (single scalar accumulator) for Q4/Q6;
* an encoding-attempt module holding Z1–Z8.

**Tests** — `tests/test_temporal_semantics_stress.py`, targeted, fast, marked
so they do not enter the expensive tier.

**Output** — `docs/temporal-semantics-stress-evidence.md`, written after
execution, with the seventeen numbered sections the cycle requires, both
ledgers kept separate, every deviation from this document recorded, and an
explicit statement of what is **recommended not to be built**.

**Test discipline.** Targeted tests plus at most the FAST tier
(`-m "not expensive"`). The FULL suite is **not** run: a sibling track is
testing concurrently and this cycle expects zero production changes, so a FULL
run would measure their work, not this one.

---

# 13. Stop rule

Adversarial review is limited to **two serious rounds total** across
`architecture-decision-reviewer` (A12) and `architecture-falsifier` (A13). A
third round is evidence that the measurement, not the review, is inadequate.

If the honest conclusion is that **little or nothing universal is forced yet**,
that is recorded plainly as the outcome. It is a valid and valuable result, and
this document exists partly so that outcome cannot be quietly avoided.
