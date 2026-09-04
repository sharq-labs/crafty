# TEMPORAL SEMANTICS STRESS — Evidence

**Milestone:** `TEMPORAL-SEMANTICS-STRESS`
**Kind:** discovery / decision. **No architecture was implemented.**
**Decision status:** none. This milestone freezes nothing and promotes nothing.
**Evidence:** `L1 EXERCISED` for the probe pack's own executed behaviour;
`L0 REASONED` for every classification, refusal and recommendation below.
**No `L2`, no `L3`, no upgrade to any existing holding.**
**Branch:** `temporal-semantics-stress`
**Baseline:** `origin/cloud/crafty-post-field-support` @ `6caa113`
**Preregistration:** `docs/temporal-semantics-stress-prereg.md`, committed at
`ea91863` **before any probe file on this branch was written**. Immutable.
Nothing below is back-written into it.

**Commits:** `ea91863` (prereg, alone) · `67b0860` (probe pack + 37 tests) ·
`a5db46b` (adversarial-review corrections, 42 tests)

**Tests:** 42 targeted (`tests/test_temporal_semantics_stress.py`, 1.8 s).
FAST tier `-m "not expensive"`: **1579 passed / 0 failed / 565 deselected**
(2102 baseline + 42 new = 2144 = 1579 + 565). The FULL suite was deliberately
**not** run: a sibling track was testing concurrently and this cycle changed
no production code, so a FULL run would have measured their work.

**Zero files under `src/` were created, edited or deleted.**
`test_z0_no_source_file_was_modified` asserts this against the branch point on
every run.

> This document is written **after** execution. Where a preregistered
> prediction failed it is recorded as a deviation with the measurement that
> refuted it, and where an adversarial review broke a claim, the claim is
> withdrawn to its measured strength rather than defended.

---

# 0. Headline

**Nothing universal is FORCED yet.** Four executed consumers, ten temporal
questions, eight zero-new-contract attempts and two adversarial rounds produce
one recommendation: **build no universal temporal contract in the next
milestone.** The five binding forcing criteria fail on F5 (a named downstream
consumer) for every candidate, and the one criterion that comes closest —
the time level of a transported or reported endpoint — cannot be typed because
the vocabulary it would need does not exist in the executed consumers.

That is the valuable outcome, and it is stated first so it cannot be lost in
the residue tables that follow.

The second headline is less comfortable. **The falsifier returned `FALSIFIED`
against this milestone's claim layer**, with two BLOCKERs, and both were
correct. One of them — that the two-histories result measured a domain defect
rather than a temporal gap — retired the finding this milestone was most
pleased with. Both are recorded below at full strength, and both were repaired
by measurement rather than by argument.

---

# 1. Physical-time evidence

**Consumer C1** (`engcore.domains.thermal_lumped`), varying only the physical
interval and holding the body, the ambient and the imposed heat fixed:

| duration | `final_temperature` | `steady_state_temperature` | `time_constant` |
|---|---|---|---|
| 50 s | 301.812692 K | 310.0 K | 250.0 s |
| 400 s | **307.981035 K** | 310.0 K | 250.0 s |

The reported state moves **6.168342 K**. The two quantities that are
properties of the *body* rather than of the *window* — the steady state and
the time constant — are bit-identical. And C1's own identity statement,
`ThermalBody.physical_key`, calls the two runs **one body**.

So physical time is a real, executed axis: it changes the answer without
changing the system. `experiments/temporal_stress/separations.py::physical_time_changes_the_answer`.

**Where it lives on the record.** For C1: a `ScientificParameter` named
`duration` carrying seconds, plus one `InitialCondition`. For C2
(`kinetics.cstr`): **nowhere**. See §5.

---

# 2. Solver-step distinction

**Consumer C4** (`experiments/cross_domain_coverage/dynamics.py`, index-3
constrained DAE, fixed-step RK4), varying only the integrator step at a
**fixed** physical horizon of 2.0 s:

| `dt` | max constraint residual `|g|` | energy drift | `x(t_end)` |
|---|---|---|---|
| 4.0e-3 s | 1.998e-09 m² | 5.975e-09 J | 0.476412948870 m |
| 2.5e-4 s | **3.042e-14 m²** | 7.816e-14 J | 0.476412948509 m |

The constraint residual falls by a factor of **65 680**. The physical answer
agrees to **3.6e-10 m**.

**This is the separation, stated as the asymmetry it is:** refining `dt` makes
the answer *better*; changing physical time makes the answer *different*. Two
structurally different consumers, two opposite signatures, both executed.

Corroborating structural fact: C2 already places `method`, `rtol` and
`n_output_points` on `IntegrationSettings` (numerics) and excludes them from
`ReactorRun.physics_fingerprint` (physics). **"Solver step and output sampling
are execution, not science" is not a proposal here — one shipped consumer
already implements it.**

---

# 3. Coupling-iteration distinction

**Consumer C3** (`engcore.systems.electrothermal.coupled`, Gauss–Seidel/Picard
fixed point over a torn dependency cycle). Ten sweeps to `criterion_met`:

```
iterate (K):  344.2723  337.8580  338.6697  338.5651  338.5786
              338.5768  338.5770  338.5770  338.5770  338.5770
final |ΔT|:   4.741e-07 K
```

In **every one of those ten sweeps** the thermal problem's declared initial
condition is 300.0 K and its declared duration is 120.0 s. The state moves;
the clock does not.

**And the separation is enforced, not emergent.** `FixedPointCouplingPlan.check_against`
actively refuses to seed an endpoint that a declared condition already
determines, calling it "time marching wearing the name of coupling". The
falsifier attacked this as circular and the attack did not land, because the
probe and the production code both disclose it — but the honest form of the
finding is: *C3 separates coupling iteration from physical time by
prohibition.* It is not evidence that a coupling loop which genuinely advanced
a clock would stay separate. That is reversal condition **R3**.

**The universal-records half is worse.** A records-only reader handed the
sequence above cannot tell it from a time series. Every value arrives under one
metric name with no time coordinate;
`RecordsOnlyTemporalReader.time_level_of` returns `UNRECOVERABLE`. The
structural distinction lives entirely inside C3's own `CoupledRun` record,
which is a **system-pack** record, not universal core.

**Wall-clock runtime** (C1, five bit-identical solves): `wall_seconds` 550–599 µs,
final temperatures identical. `RawSolverOutput` carries `wall_seconds`;
`ScientificResult.__dataclass_fields__` has no such key. **Already separated by
the contracts.** P7 HELD.

**Optimization iteration: NOT MEASURED.** `ScientificEvaluation` carries
`{candidate, constraint_checks, detail, evaluation_id, metadata,
objective_values, result, status}` — an opaque id, no ordinal, no sequence
position, no typed predecessor. There is nothing to vary, so there is nothing
to separate. **Preregistered prediction P1 is partially REFUTED**, in exactly
the way §7 of the prereg said it could lose. Running a search to manufacture a
lever would have measured a consumer this milestone invented, which §2 forbids.

---

# 4. Time-level collision

**The concrete case.** C1 reports, on one result, in one dimension:

| metric | temporal meaning | unit |
|---|---|---|
| `temperature` (STATE variable) | the state at t₀ | kelvin |
| `final_temperature` | t = duration | kelvin |
| `steady_state_temperature` | t → ∞ | kelvin |

Same physical variable. Same dimension. Three temporal meanings.
`_require_metric_coherence` passes. Every dimension check passes.
`same_quantity_different_time` returns **AMBIGUOUS** over
`[temperature]: ['final_temperature', 'steady_state_temperature']`.

**It is load-bearing, not hypothetical.** C3's `QuantityDependency` selects
between them **by enumerated name**, and the ET-VERTICAL milestone already
measured the consequence: switching the transported endpoint from
`final_temperature` to `steady_state_temperature` — one field, no code change,
both kelvin, both checking clean — moves the converged answer by **3.376 K**.

**A second collision, in `[time]`.** C1's `time_constant` is a *property* of
the body, in seconds. C2's `t:T_max` is an *instant on the physical axis*, in
seconds. One dimension, two categories, no typed separation. A reader given
both returns AMBIGUOUS.

**A third, across consumers.** C1 spells the end-of-horizon level
`final_temperature`; C2 spells it `T:final`. The two conventions share no
name. Aligning them requires parsing a name's internal structure — the
meaning-in-key failure mode `EXEC-SPEC-STRUCTURED` §C catalogued and refused —
so a cross-consumer reader cannot align time levels at all.

**A fourth, inside one composition.** C3's property problem
(`resistance-tcr-R1`) declares a variable named `temperature` with no initial
condition; C3's thermal problem declares a variable named `temperature` with
one. One name, one composition, two meanings: an instantaneous operating point
and a state at t₀. The core's own "one name means one thing" invariant is
*stated and unenforced*, and this is its documented failure mode occurring.

---

# 5. Time-varying-input result

**Ledger B first — the steelman achieved a great deal (Z4, six entries).**

Two `ScientificDataReference`s (an 11-value kelvin array, an 11-value second
array), two declared `ScientificVariable`s, two `VariableBulkLinkage`s. Result:

* **zero** issues from `check_against` on either linkage;
* both arrays' variable identity, unit and dimensional agreement typed and
  checked;
* `unlinked_references` empty;
* content digests give both arrays relocation-stable identity;
* **DATA-BOUNDARY0 intact** — two O(1) records name two O(N) arrays that never
  enter a control-plane record;
* **the coordinate's EXTENT is expressible.** `ScientificVariable` carries
  typed, dimension-checked, finite bounds, so `sample_time` over `[0 s, 600 s]`
  declares cleanly. *(Added after `architecture-falsifier` caught this steelman
  being skipped — the same channel §68.3 recorded being missed one milestone
  earlier.)*
* a reader can **observe** whether two references' counts agree, because
  `count` is a typed field.

**Ledger A — the residue (four entries).**

1. **Nothing states the two arrays were required to correspond.** A 5-sample
   coordinate against an 11-sample value array raises **zero** issues. A reader
   can see 5 ≠ 11; it cannot know that was an error rather than two unrelated
   arrays.
2. **Nothing states that one array is the independent coordinate of the
   other.** `VariableBulkLinkage`'s own docstring says it is a per-array
   statement, and two per-array statements do not compose into a pairing.
   `independent_coordinate` returns AMBIGUOUS.
3. **`sample_time` had to be declared `OBSERVABLE`, and that is false.** It is
   not produced by the solve; it is the axis the solve is posed over.
   `VariableRole` is `{design, state, observable, control}` and an independent
   coordinate is none of them.
4. **The encoding cannot distinguish a time history from a spatial field.**
   Both are "a values array plus a coordinate array", and MIN-FIELD-SUPPORT
   already uses that shape for space. See §10.

**Z3 — time as an ordinary parameter, and the concrete wrongness.** A
`[time]`-dimensioned `ScientificParameter` encodes and validates. But C1's only
one is `duration` = 600 s, which *is* its horizon; C2's only one is
`residence_time` = 200 s, and C2's actual horizon is **400 s**. A reader taking
"the `[time]` parameter" to be the horizon is silently **2× wrong**, and
nothing warns it.

---

# 6. History result — and the claim this milestone withdrew

## 6.1 What was measured

Two piecewise-constant heat schedules on **one** lumped body over `[0, 600 s]`.
The closing power of H_B is solved **exactly** (the balance is affine in Q), not
searched, so the endpoints genuinely meet:

| | H_A (hot→cool) | H_B (cool→hot) |
|---|---|---|
| schedule | 40 W then 4 W | 4 W then 12.0327 W |
| `T(600 s)` | 305.020601515314 K | 305.020601515314 K |
| peak `T` | **315.5374 K** | **305.0206 K** |
| `E = ∫₀⁶⁰⁰ max(T−305, 0) dτ` | **2732.83 K·s** | **0.042 K·s** |

Endpoint difference: **exactly 0.0 K**. Exposure ratio: **64 551×**. Peak
difference: **10.5 K**.

**Solver trajectory vs scientific history, separated by measurement.**
Sampling the *same* history from 202 to 40 002 points changes `E` by
**1.8e-05** relative. Changing the *history* changes it by ~1.0 relative. The
contrast is **five orders of magnitude**, so `E` is a property of the path, not
an artefact of whatever samples an integrator happened to emit. A stored
trajectory is a numerical object; scientific history is not the same thing, and
"we already keep a trajectory" is not an answer to the history question.

## 6.2 The BLOCKER, and the claim withdrawn

`architecture-falsifier` returned a **BLOCKER** against the representation half
of this finding, and it is right.

The original claim was "the two histories are indistinguishable in the
universal records". **That is true, and it does not measure what it said.**
`build_lumped_thermal_problem` declares `heat_input` and `ambient_temperature`
as `CONTROL` variables **with no value on any record**; the value arrives out of
band through `bind_body`. So the null control:

> Two **single-segment** C1 runs, zero schedule, zero path dependence,
> identical everything except the imposed heat: **40 W and 4 W**. Their
> `ScientificProblem` records serialise **byte-identically**. Their final
> temperatures differ by **17.1038 K**.

Record indistinguishability of the two histories is therefore explained by a
**domain defect in C1** — the same class §67.2 named for `is_time_dependent`,
"the defect is in the baseline domain, not the contract" — and **not** by a
temporal representation gap. The claim is withdrawn to that strength.

`experiments/temporal_stress/exposure.py::control_value_null_control`,
`tests::test_a4_the_record_indistinguishability_is_explained_by_a_control_omission`.

**What survives the control, kept and stated separately:** the exact endpoint
agreement, the 64 551× exposure divergence, the 10.5 K peak divergence, and the
sampling independence. Those are physics results about paths, and the null
control does not touch them. `State(t) ⊉ History[0:t]` is true as physics.
Whether the *records* fail to carry history remains **unmeasured in this
repository**, because no domain here records its declared controls.

**Deviation from prereg P4:** P4 predicted "two histories with equal current
state, unequal exposure, are indistinguishable by every current typed
contract". The prediction HELD literally and is REFUTED as evidence, because
the null control shows the indistinguishability has a simpler cause. This is
recorded as a deviation, not restated.

**Z7 — the last steelman.** A `QuantityDependency` chain across segment
problems expresses supply, is walkable by a records-only reader, and is O(1)
per edge. Its whole surface is `{description, name, source_problem_id,
source_quantity, target_problem_id, target_quantity, unit_exemplar}` — **no
elapsed time, no start, no end, no ordering against a clock.** A schedule with
300 s gaps and one without produce identical chains.

---

# 7. Event result

**Ledger B (four entries).** Problem-splitting at the discontinuity is the
honest maximum and it works: each segment is a complete, valid, independently
solvable `ScientificProblem` posed over its own interval; `InitialCondition.time`
carries the **absolute instant** (300.0 s), so *"this value holds at t = 300 s"*
**is** representable per condition; the boundary can sit exactly at the
discontinuity, which C1's constant-input realization requires anyway; and **two
conditions on one variable at two stated instants construct and validate**.

**Ledger A (six entries).**

1. Nothing relates the two problems — no typed field says B follows A, that
   they abut, or that they concern one physical timeline.
2. Nothing says **what** changed at the boundary. `heat_input` is a declared
   `CONTROL` with no value on either record, so the discontinuity is invisible
   in principle (this is §6.2's defect again, and it compounds here).
3. Nothing distinguishes "one system across an event" from "two unrelated
   studies of similar bodies".
4. The reader returns `UNRECOVERABLE` for the event question:
   `InitialCondition.time` states when a condition applies, not that anything
   changed there.
5. **Two conditions on one variable are accepted with no check at all.**
   Nothing orders them; nothing says the later supersedes the earlier (a
   discontinuity) rather than contradicting it (a specification error). The
   reader can only return AMBIGUOUS.
6. An event schedule of n switches needs n+1 problems — O(N) in the event
   count, against prereg **F4**, not against DATA-BOUNDARY0 (no record carries
   bulk bytes here).

**A separate, cheap fact.** `InitialCondition.time` is checked only for
`isinstance(..., Quantity)`. A `Quantity` in **metres** is accepted. And a
repository-wide search finds exactly **one** `InitialCondition(...)` producer
under `src/` — `thermal_lumped.py` — and it does not set `time`. The field is
unvalidated and unused.

---

# 8. Accumulated-exposure result

**The classification A6 asked for is answered by measurement, and it comes out
flat.** `E(t) = ∫₀ᵗ f(T(τ))dτ` encodes:

* as a **STATE** `ScientificVariable` with a zero `InitialCondition` — the core
  validates the condition's dimension against the variable's, and
  `is_time_dependent` becomes True;
* as an **OBSERVABLE** `ScientificVariable`;
* as a reported `ScientificResult` value carrying `K·s`.

All three construct. All three validate. **Nothing typed distinguishes them.**
So "state variable vs derived observable vs relation result" is a *convention*
here, not a fact the records carry.

**The finding that keeps A6 out of the recommendation:** a scalar accumulator
is **O(1)** and needs **nothing new**. What is missing is not a place to put
it. What is missing is (a) that it is a functional **of** another declared
variable — the dependence on temperature is invisible — and (b) the
**accumulation window**: two results reporting 2732.83 K·s over different
windows are indistinguishable. Both are facts a *degradation consumer* would
force, and prereg §9 forbids inventing one here.

**No wear, fatigue, aging, battery, corrosion or damage physics was built.**
The accumulator is an instrument for a representation question and
`exposure.py` says so in its own module docstring.

---

# 9. Data-boundary result

`ScientificDataReference`'s entire typed surface is
`{count, digest, digest_algorithm, dtype, name, unit}`. It says **what** and
never **when**.

Separating the five things prereg Q7 asked about:

| Fact | Expressible today? |
|---|---|
| variable identity | **YES** — `VariableBulkLinkage`, typed and dimension-checked |
| unit of every sample | **YES** — on the reference |
| number of samples | **YES** — `count`, and a reader can compare two |
| sample **ordering** | partial — "in the reference's own order" is stated in the linkage's prose; no field |
| **time coordinate** | **NO** |
| storage layout | deliberately **NO** — that is the point of DATA-BOUNDARY0 |
| physical-time semantics | **NO** |

**DATA-BOUNDARY0 is intact and every encoding attempted preserved it.** An
11-sample and a 4 000 001-sample reference produce identical record shapes with
identical keys and only scalar values. No probe put an array into a record; the
dense trajectories live in probe-local tuples and never reach a
`ScientificResult`.

One correction carried from the falsifier: residues about O(N) growth in the
**number of records** (Z2, Z5, Z7) now cite prereg **F4**, not DATA-BOUNDARY0.
DATA-BOUNDARY0 governs a record *containing* bulk bytes; record-count growth is
a different and lesser concern, and conflating them overstated the residue.
`test_a10_no_residue_miscites_data_boundary0_for_record_count_growth` enforces
the distinction.

---

# 10. Scalar/bulk precedence result

The prose rule on `ScientificProblem.data_references` (MIN-FIELD-SUPPORT,
falsifier finding C.1 of that milestone) reads:

> *the bulk reference is authoritative for that variable's actual
> initial/boundary state; the scalar condition is representative/informational
> only and must never be read by a solver as the complete state.*

**Stressed temporally, the rule is not merely unenforced — it is false.**

| | spatial case | temporal case |
|---|---|---|
| variable | `temperature` (STATE) | `ambient_temperature` (CONTROL) |
| scalar condition | 300 K, representative | 300 K, representative |
| bulk reference | 11-value non-uniform initial field | 11-value time series |
| linkage issues | **0** | **0** |
| typed signature | `{variable_unit: kelvin, reference_unit: kelvin, count: 11, dtype: float64, has_scalar_condition: True}` | **identical** |

For the spatial case the rule is correct: the array *is* the state at t₀. For
the temporal case it is wrong: **a series is a trajectory, not a state at an
instant, and element 0 is not "the state"**. A consumer applying the rule as
written would read one sample of a trajectory as the whole boundary condition.

The two cases agree on **every typed field a records-only reader can see**. The
rule that would separate them lives in a docstring.

**Also measured:** the core accepts an `InitialCondition` on a `CONTROL`
variable without comment. Nothing says a control has no initial value, and
nothing says this one is a representative sample of a trajectory rather than the
control's value at t₀.

**Verdict on Q8: the documentation-only precedence becomes both ambiguous and
unsafe under temporal load.** Typed enforcement will eventually be required —
but **not in its current wording**, which is §17's reversal-adjacent constraint
R-C below.

---

# 11. Identity classification

Answering A9 by what executed consumers actually do, not by preference.

| Temporal value | Classification | Evidence |
|---|---|---|
| **solver `dt` / method / tolerance** | **execution specification** | C2 puts them on `IntegrationSettings`, excluded from `physics_fingerprint`; C4's `dt` refined 16× moves `x(t_end)` by 3.6e-10 m |
| **output sample interval** | **result sampling** | C2's `n_output_points`, documented "reporting resolution only… never changes the integration path", travels as metadata |
| **wall-clock runtime** | **runtime policy** | on `RawSolverOutput`, absent from `ScientificResult`; varies 550–599 µs across bit-identical science |
| **coupling iterate index** | **execution** (of a composition) | C3's sweeps move state with a stationary clock; the index lives on a system-pack record |
| **optimization iteration** | **NOT CLASSIFIED** | no ordinal exists on any record; nothing measured |
| **start time (t₀)** | **scientific problem semantics** | it *is* the `InitialCondition`; changing it changes the problem |
| **duration / horizon** | **DISPUTED — two consumers, opposite answers** | see below |
| **time coordinate of an input** | **scientific problem semantics** | changing `T_amb(t)` changes the physics; but it is unrepresentable (§5) |
| **event schedule** | **scientific problem semantics** | a switch at t_e changes the physics; unrepresentable (§7) |

**The horizon disagreement, recorded rather than adjudicated.**
`ThermalBody.physical_key` is `(body_id, heat_capacity, ambient_conductance)` —
its docstring says the ambient, the initial state and the integration window
are "excluded deliberately", because "the same physical body at a second
ambient, or over a second interval" must not be a second system.
`ReactorRun.physics_fingerprint` hashes `operation.to_dict()`, which contains
`end_time_s`, so 400 s and 800 s **hash differently**.

Two shipped consumers, opposite answers, both defensible, both domain-local,
**nothing universal adjudicating and no universal consumer reading either**.
This milestone records it as an open question. Unifying it on this evidence
would be choosing one domain's convention for every future domain.

**The general finding: not all temporal values are scientific identity, and the
platform already distinguishes three of the four categories correctly without
any temporal contract.** What it does not distinguish is which category the
horizon belongs to.

---

# 12. Residue table

Ledger A only. Ledger B totals are in the column header count and are itemised
in §5, §7 and §8, and in `experiments/temporal_stress/encodings.py`.

Per-attempt ledger balance: **Z1** B3/A3 · **Z2** B2/A3 · **Z3** B3/A4 ·
**Z4** B6/A4 · **Z5** B4/A6 · **Z6** B3/A3 · **Z7** B3/A4 · **Z8** B2/A4.
Total **26 Ledger B / 31 Ledger A**. Ledger B is not empty, so prereg §8's
instrument-failure condition did not fire.

| # | Residue | Consumers | Semantic or numerical | O(1)/O(N) | DATA-BOUNDARY0? | Planner needs? | Reconstruction needs? | **Forced?** |
|---|---|---|---|---|---|---|---|---|
| **R1** | the **time level** at which a reported or transported value holds | C1, C2, C3 (3) | semantic | O(1) | no | no planner exists | yes, but no consumer reconstructs | **NOT FORCED — F5 fails.** Strongest candidate; blocked on vocabulary (§15) |
| **R2** | **pairing** of a values array to its coordinate array | C1 (probe), C4 (probe) | semantic | O(1) record naming O(N) data | preserved | no | yes | **NOT FORCED — F1 marginal, F5 fails.** Belongs to the field track (§15) |
| **R3** | **independence/direction**: which array is the coordinate of which | same as R2 | semantic | O(1) | preserved | no | yes | **NOT FORCED**, same as R2 |
| **R4** | no `VariableRole` member for an independent coordinate | C1 (probe) | semantic, cosmetic | O(1) | n/a | no | no | **NOT FORCED.** Closes the mislabelling, not the silent wrongness |
| **R5** | the **physical horizon** is absent from C2's universal record | C2 (1) | semantic | O(1) | n/a | n/a | yes | **NOT A CORE RESIDUE — domain defect.** §67.2 precedent, corroborated |
| **R6** | declared `CONTROL` values are absent from C1's universal record | C1 (1) | semantic | O(1) | n/a | n/a | yes | **NOT A CORE RESIDUE — domain defect.** §6.2 |
| **R7** | nothing states an **event**, an event time, or a before/after partition | C1 (probe) | semantic | O(N) in events (F4) | n/a | no | yes | **NOT FORCED — F1 and F5 both fail** |
| **R8** | nothing states **elapsed time** along a dependency chain | C1 (probe) | semantic | O(N) in segments (F4) | n/a | no | yes | **NOT FORCED** |
| **R9** | an accumulator's **functional dependence** and **accumulation window** | none executed | semantic | O(1) | n/a | no | yes | **NOT FORCED — no consumer.** Needs a degradation domain |
| **R10** | the scalar/bulk **precedence rule** is prose, and false for a series | C1 (probe), and the shipped fluid consumer for the spatial half | semantic | O(1) | preserved | no | yes | **NOT FORCED as a contract; forced as a CONSTRAINT on the field track** (§15) |
| **R11** | two conditions on one variable are accepted unordered and unreconciled | C1 (probe) | semantic | O(1) | n/a | no | yes | **NOT FORCED** |
| **R12** | `InitialCondition.time` is dimensionally unvalidated | core-wide | semantic | O(1) | n/a | no | no | **NOT FORCED — the cheapest item in the set, and still a core edit** |

**Every row is NOT FORCED.** F5 — "a named downstream consumer; 'a future
system might' is not a consumer" — fails for all twelve, and F1 fails for
several. Two rows (R5, R6) are not core residues at all.

**The F5 spike, run at the reviewer's request.** The reviewer named one check
as decisive: *find a shipped reader that compares two results at a common time
level, or keys anything on a horizon.* One cross-result comparison exists —
C2's verification gate compares a cross-method arm against the finest tolerance
rung — and it does **not** need a time level, for two reasons: both results
come from **one domain**, so one naming convention governs both and exact name
equality suffices; and `ReactorRun.with_integration` replaces only the
numerics, so the horizon is held **identical by construction**. No planner, no
scheduler and no execution-plan compiler exists anywhere under `src/`.
`test_f5_the_only_cross_result_comparison_never_needs_a_time_level` and
`test_f5_no_universal_reader_of_any_temporal_fact_exists` pin both halves.

**The falsifier found a sharper reading of that same gate and it is recorded
here rather than defended:** the gate has a fourth arm that compares
`T:final` (t = end_time) against a Brent-computed steady state (t → ∞), guarded
by a hand-written `_is_stationary` check that judges from a domain-local
trajectory whether the two levels may be identified. F5's admissible list
includes *validation*. So a shipped validation consumer **already performs the
final-vs-asymptotic identification** and had to hand-write the guard because no
record carries the level. It fails F2 only because it is intra-domain and
imports its own metric constants. **It is booked as a near-miss F5 consumer**,
and it is the single strongest reason the DEFER below carries an expiry rather
than being open-ended.

---

# 13. Reviewer verdict

`architecture-decision-reviewer`: **DEFER.**

Weighed eight alternatives, including two the preregistration did not name
(a standalone coordinate record, and placement of the whole coordinate concept
in the field track). Criteria and weights were fixed before any option was
preferred, weighted by irreversibility.

Its findings this milestone adopts:

* **`VariableRole.INDEPENDENT` is the smallest *change* and not the smallest
  *useful* change.** It closes the cosmetic residue (R4) and leaves the two
  that cause silent wrongness (R2, R3). It is the only candidate that touches
  a **serialized enum read by an exact-match constructor** while buying the
  least, and Crafty has a local negative precedent: `ModelFormulation.DISCRETE`
  is recorded as "under-defined and provisional… must be clarified by a real
  consumer, or removed". **Primary source:** CF/netCDF needed **both** an
  `axis` attribute **and** a `coordinates` attribute — a role tag alone does
  not state an association.
* **The coordinate/pairing gap belongs to the field track, not a temporal
  one.** `docs/min-field-support-foundation-evidence.md` records the identical
  gap for the shipped fluid consumer — "Coordinates / flattening — DOMAIN CODE
  ONLY… no typed record" — **deferred four times**. A temporal coordinate
  record would be a second home for one concept, built ahead of the consumer
  that would have shaped it.
* **Reject (G) on measurement, not taste.** §1, §3 and §6 vary independently,
  so P6 HELD and one generic timeline object would fuse separable science.
* **Negative precedent, verified:** preCICE ≤ v2 shipped exactly Crafty's
  current shape — coupling data exchanged with no time coordinate — and v3
  **made `relativeReadTime` mandatory in `readData()`**, breaking every
  adapter, with a published v2→v3 porting guide completed only at v3.2. The
  reviewer and the falsifier disagreed on how far this transfers, and the
  falsifier's narrowing is adopted: `readData()` is a runtime data-plane API
  with no versioned payload, whereas `QuantityDependency` is a declarative
  record and Crafty has a precedented additive-bump mechanism
  (`require_schema_any`, used three times). The shape analogy holds; the cost
  analogy does not — **until the payloads are published externally.**

---

# 14. Falsifier verdict

`architecture-falsifier`: **FALSIFIED** — against the **claim layer**.
**The DEFER recommendation is not falsified** and survived every attack
constructed against it.

| Finding | Class | Disposition |
|---|---|---|
| **C.1** — the two-histories result measures a `thermal_lumped` control-value omission, not a temporal gap; and the test carrying it was true by construction | **BLOCKER** | **Accepted and repaired.** Null control built and executed (§6.2); the representation claim is withdrawn; the physics results are kept and stated separately |
| **C.2** — four reader methods returned one outcome for **every possible argument**, so tests asserting them asserted nothing; third consecutive milestone to earn this | **BLOCKER** | **Accepted and repaired.** The four methods now consult `ProvenanceRecord.inputs`, sibling `count`, repeated conditions and `parent_run_id`; `instrument_variance()` publishes the result |
| **D.1** — routing the residue to the field track risks *typing* a spatial-only precedence rule that §10 shows is false for time | BREAKING-RISK | **Accepted.** Carried as constraint R-C in §15 |
| **D.2** — DEFER has a hidden expiry: four of the five records a temporal fact would attach to use exact-match `require_schema` with no accepted-versions tuple, and API/MCP v0 is the next roadmap item | BREAKING-RISK | **Accepted.** Added as reversal trigger **T7** (§17) |
| **D.3** — the F5 refusal rests on a partial reading of C2's verification gate, which has a fourth arm that identifies t=end_time with t→∞ | BREAKING-RISK | **Accepted.** Recorded in §12 as a near-miss F5 consumer; **T4** widened |
| C3-primary — "you designed temporal semantics around transient thermal integration" | — | **Cannot land as posed** (nothing was designed) but lands in a stronger form: **the instrument is thermal-lumped-shaped.** C1 appears in C3, in the exposure probe and in six of eight Z-attempts. And **exactly one** `InitialCondition(...)` producer exists under `src/`. See §16 |
| E.1–E.12 | NOT A REAL ISSUE / ADDITIVE-FUTURE-EXTENSION / IMPLEMENTATION-CONCERN | Three implementation concerns fixed (§5, §7, §9); the rest recorded as attacks that did not land, including "the C3 separation is circular" (it is enforced *and* disclosed) and "the probe pack violates DATA-BOUNDARY0" (it does not) |

**Stress-case results (conceptual only; nothing implemented).** Tire operating
history — **breaks the claim's generality, not the records**; battery aging —
**bends** on R9's accumulation window; thermal cycling — **breaks** on §10 with
a real physical system behind it; transient CFD — **breaks, but off-track**
(`count` is not a shape: FIELD0/TOPO0, already booked L0 four times); dynamic
structures — **holds**, then bends on `ModelFormulation.DAE`, already recorded
elsewhere; control systems — **bends** on R4, the cosmetic residue; chemical
batch process — C2 already is one and reports `is_time_dependent is False`, a
**domain defect**; distributed/GPU — **not tested**, no consumer, no claim made.

**The falsifier's strongest contribution was an argument for DEFER that this
milestone had not made:** exactly **one** domain under `src/` writes a temporal
universal record. Any temporal contract cut today would be cut from a single
consumer.

---

# 15. The minimal temporal foundation RECOMMENDED — which is: build none

## 15.1 Build nothing universal in the next milestone

Against the preregistered outcome set:

| Outcome | Verdict |
|---|---|
| **(A) no new universal temporal semantics** | **RECOMMENDED** |
| (B) independent-variable / time-coordinate identity only | **DO NOT BUILD.** `VariableRole.INDEPENDENT` closes R4 and leaves R2/R3. Enum member = expensive to reverse, cheapest residue closed |
| (C) time coordinate + temporal binding | **DO NOT BUILD AS TEMPORAL.** The pairing gap is identical in space and time and the spatial consumer already has it, deferred four times. It belongs to the field/coordinate track |
| (D) temporal condition/input semantics | **DO NOT BUILD.** Decomposes into (B)+(C); no residue of its own |
| (E) event semantics | **DO NOT BUILD.** F1 and F5 both fail |
| (F) history / exposure semantics | **DO NOT BUILD.** No consumer; a scalar accumulator already needs nothing new |
| (G) one `TemporalModel` | **REJECTED on measurement.** §1, §3 and §6 vary independently |

**And explicitly, so it cannot be read as an oversight:** do not build
`TimeSeries`, `TimeDomain`, `Timeline`, `TemporalState`, `Event`,
`EventSchedule`, `History`, `Trajectory`, an event engine, an interpolation or
resampling contract, a time-synchronisation runtime, or any universal record
that scales with history length.

## 15.2 What the science does and does not separate

Prereg P6 asked whether the residues vary independently. **They do**, and this
is why (G) is rejected rather than merely disfavoured: physical time (C1
`duration`), solver step (C4 `n_steps`), coupling iterate (C3 sweeps) and
wall-clock (repeat) were each varied on executed code with differently-signed
consequences. Three orthogonal small concepts would be right if any were
forced. None is.

**One caveat the falsifier is owed.** The pairing gap (R2/R3) genuinely is one
concept across space and time. But **time carries properties space does not**,
and the field track will not close them: total order and monotonicity (space
had to *acquire* direction per region via `BoundaryOrientation`);
unboundedness (`ScientificVariable` bounds must be finite, so the `t → ∞` level
central to §4 is not expressible even as a bound); causality;
cyclicity (`BoundaryKind.PERIODIC` exists for space, nothing for time); and
non-storability (a spatial field at one instant is a complete state; a time
series never is — which is exactly why §10's rule breaks). "It belongs to the
field track" is a **real argument for the pairing gap and an evasion for the
rest**, and it is recorded as such.

## 15.3 Four recommendations that are not universal contracts

None may be implemented by this milestone (prereg §0). Each is for a future
milestone with a consumer.

* **R-A (domain, C2).** `build_cstr_problem` declares no `InitialCondition`
  and puts no horizon on the universal record, so a transient stiff
  integration reports `is_time_dependent is False`. This is a **domain
  defect**, corroborated independently by §67.2 with a different consumer.
  Note the residue it does *not* close: even with conditions declared,
  `residence_time` and a horizon remain indistinguishable by dimension.
* **R-B (domain, C1).** `build_lumped_thermal_problem` records no value for
  its declared `CONTROL` variables, so any two runs differing only in an
  imposed control are record-identical (§6.2). Also a domain defect, and the
  reason §6's representation claim was withdrawn.
* **R-C (documentation + a binding constraint on the field track).** The
  precedence sentence on `ScientificProblem.data_references` is **false for a
  time series**. Correcting the prose is a documentation change to an already
  prose-only rule. The binding part is the constraint the field track must
  carry into its own preregistration: *the scalar/bulk precedence rule must
  not be typed in its current wording. A bulk reference bound to a variable is
  authoritative for that variable's values; whether those values are a state
  at one instant or a trajectory over an interval is **not** decided by that
  rule.* Typed as written, the wrong reading stops being undocumented and
  starts being machine-enforced.
* **R-D (core, cheapest in the set, and still a core edit).**
  `InitialCondition.time` is dimensionally unvalidated (a metre passes) and has
  no producer under `src/`. Tightening it costs no schema, no bytes and no key
  — but it belongs to a milestone with a consumer.

---

# 16. Evidence level

**`L1 EXERCISED`** — and only for what the probe pack executed: the four
separations, the exposure and sampling-independence measurements, the null
control, the eight encoding attempts, the instrument's own variance, and the
F5 spike. 42 tests, all sub-second, all in FAST.

**`L0 REASONED`** — every classification in §11, every refusal in §15, the
residue table's forcing verdicts, and all four recommendations in §15.3.

**No `L2`, no `L3`.** No existing holding is upgraded: DATA-BOUNDARY0 stays
`L1`; MIN-FOUNDATION-ET stays `L1`/`L0`; MIN-FIELD-SUPPORT stays where it is.
The recommended foundation is **nothing**, so it has no evidence level of its
own.

**Four limits on this evidence, stated because they bound every claim above.**

1. **One producer.** Exactly **one** `InitialCondition(...)` construction exists
   under `src/`, in `thermal_lumped.py`, and it does not set `time`. C2
   declares none; C4 is in `experiments/`. So exactly one production domain
   writes a temporal universal record — and any temporal contract cut today
   would be cut from a single consumer.
2. **The instrument is thermal-lumped-shaped.** C1 appears in C3's composition,
   three times in the exposure probe, and in six of eight Z-attempts. C4 is the
   only structurally independent consumer and it lives in `experiments/`.
   Prereg §2's "four materially different consumers" is weaker than it reads.
3. **The instrument was reprinting its author until the falsifier caught it.**
   Four reader methods returned one outcome for every argument. This is the
   **third consecutive** Crafty milestone to earn that finding (§67.3, §68.3),
   and the first not to have applied the published defence before review.
   `instrument_variance()` now reports: **7 of 9 methods vary**; the two that
   do not (`is_time_dependent`, `wall_clock`) both return `KNOWN`, so neither
   can inflate a residue. Every method a Ledger A residue rests on varies.
4. **One author, one branch, one repository.**

---

# 17. Reversal triggers

The six preregistered conditions are endorsed as written and restated here with
what this milestone learned about each; **T7** is new, from falsifier D.2.

* **T1** *(prereg R1)* — a consumer whose physical time is not a scalar
  interval: cyclic or periodic time, multiple independent time scales,
  retarded time, or the frequency domain. §15.2 raises this from a possibility
  to an expectation: `BoundaryKind.PERIODIC` exists for space and nothing does
  for time.
* **T2** *(R2)* — any planner, execution-plan compiler or scheduler is
  implemented. **F5 changes meaning the moment a universal reader exists**, and
  every row in §12's table fails on F5 today.
* **T3** *(R3)* — a coupled consumer whose iterate genuinely advances a clock.
  §3's separation rests on `FixedPointCouplingPlan.check_against` **prohibiting**
  it; the day that guard needs a carve-out, the measurement stops being
  representative. preCICE's v2→v3 history says this is where the bill comes due.
* **T4** *(R4, widened per falsifier D.3)* — a consumer needs to compare two
  results at a common time level **across domains**, **or to identify a
  finite-horizon end state with an asymptotic one**. The widening matters: C2's
  verification gate **already does the latter**, intra-domain, with a
  hand-written stationarity guard.
* **T5** *(R5)* — bulk time histories must cross a process or storage boundary
  as scientific claims rather than as domain-local gate evidence.
* **T6** *(R6)* — a consumer must reconstruct a result from its records alone
  (replay/audit). History-vs-state stops being a representation question and
  becomes a reconstruction requirement.
* **T7** *(NEW — falsifier D.2)* — **any external API or MCP surface publishes
  `ScientificProblem`, `ScientificResult`, `ScientificDataReference`,
  `VariableBulkLinkage` or `QuantityDependency` payloads to a consumer outside
  this repository.** Supporting fact: **four of those five use exact-match
  `require_schema` with no accepted-versions tuple** — only
  `scientific_problem`, `scientific_result` and `provenance_record` carry
  `require_schema_any`. Until publication a temporal addition is an internal
  edit; afterwards it is a published-contract break for clients Crafty does not
  control. **This DEFER is correct *because* nothing is published, so its
  expiry is a date, not a judgement.**

---

# 18. Divergences from the preregistration

Recorded here, never back-written into `docs/temporal-semantics-stress-prereg.md`.

| Prereg item | Outcome |
|---|---|
| **P1** — all five axes separable | **PARTIALLY REFUTED.** Optimization iteration has no executed lever and is reported NOT MEASURED, exactly as §7 allowed |
| **P2** — a time-level collision exists | **HELD**, and four distinct collisions were found, not one |
| **P3** — non-empty residue after Z3+Z4 | **HELD** |
| **P4** — two histories indistinguishable by every typed contract | **HELD literally, REFUTED as evidence.** §6.2's null control shows a simpler cause. The claim is withdrawn |
| **P5** — at least one residue NOT forced | **HELD in the strongest form: none is forced** |
| **P6** — the science separates ≥2 residues | **HELD**; this is why (G) is rejected |
| **P7** — wall-clock is runtime policy | **HELD** |
| **B1–B10** baseline facts | **All ten reproduced.** B2 (C2 reports `is_time_dependent is False`) and B3 (`InitialCondition.time` unvalidated) are the two with consequences, both reported above |
| §12 required probes | All four built. §13's two-round stop rule was observed exactly: one reviewer round, one falsifier round |
| §2 "four materially different consumers" | **Weaker than written.** §16 limit 2 records why |
| §5 two-ledger rule | Enforced by `test_a10_every_encoding_attempt_records_both_ledgers`. Ledger B is non-empty (26 entries), so §8's instrument-failure condition did not fire |

**One process note.** The preregistration did not record that this milestone
runs ahead of `MIN-FOUNDATION-PDE`, which the master context names as the next
milestone. That reordering should have been recorded as a deviation in the
preregistration itself, as §67 and §68 did for theirs. It is recorded here
instead, which is second-best.

---

# 19. What this milestone refuses to claim

* That the universal records cannot carry history. **Unmeasured** — §6.2.
* That any temporal residue is forced. **None is** — §12.
* That the four consumers are as materially different as prereg §2 asserted.
  **They are not** — §16.
* That "the coordinate concept belongs to the field track" settles the time
  question. **It settles the pairing half and evades the rest** — §15.2.
* That deferring is free. **It has a dated expiry** — T7.
* That anything here is decided, frozen, or authorised to be built.
