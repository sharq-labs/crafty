# PROPULSION0-EXT — closing four coverage gaps: evidence

**Verdict: KEEP.** `PROPOSED / L1 EXERCISED`. Fixture machine constants and handbook material
data give **MODEL-CONSISTENT** results only; nothing here is validated against hardware.

| | |
|---|---|
| Baseline commit | `62a9fd7` (PROPULSION0, KEEP, `PROPOSED / L1 EXERCISED`) |
| Branch / worktree | `propulsion0-ext` / `/home/user/crafty-prop-ext` |
| Preregistration | `57164d8`, committed alone, **not amended** |
| Baseline FULL (orchestrator, sequential) | 2467 passed / 0 failed / 0 errors, 1172.83 s |
| Baseline FAST (this worktree) | 1840 passed / 0 failed / 627 deselected |
| Final FAST | **1920 passed / 0 failed / 627 deselected** |
| Final FULL (sequential, authoritative) | **2547 passed / 0 failed / 0 errors**, 943.31 s |
| New tests | 80, all FAST |
| Existing tests modified | 1 (one historical scope guard) — §11 |
| New universal contracts forced | **NONE** |
| New source files under `src/` | **NONE** — two existing files edited |
| Adversarial rounds | 2 (`architecture-falsifier`), 8 findings closed, **1 prediction withdrawn** |

This document is an **extension**. `docs/evidence/propulsion0-evidence.md` is a sealed record
and is not rewritten; it gains one pointer line.

---

## §1 What was closed, in one line each

| Gap | Question | Result |
|---|---|---|
| **G1** | do multiple operating points behave as the equations require? | **yes** — nine unconditional relations over 241 algebraic points and five coupled runs, three conditional turning points located where their closed forms say, energy closed everywhere to ≤ 2.2e-14 |
| **G2** | can two motors exist independently in one process? | **yes**, and in *one composition* — 28 problems, six torn endpoints, on the unedited plan and loop; changing one leaves the other bit-identical |
| **G3** | do the four missing negative cases stop before a trusted result? | **yes** — every one refuses before a solver object is constructed |
| **G4** | what *is* efficiency? | a **state-dependent relation**; one pure function added, no field, no schema, no problem, no edge |

---

## §2 G1 — the sweep, and the derivation that made it a relation

### 2.1 What was derived before anything ran

Preregistration §2.2–§2.4 derived, from `F(w) = k_load*w^2 + c*w - d` with
`c = b + k_t*k_e/R > 0` and `d = k_t*V/R > 0`:

* `dF/d(k_load) = w^2 > 0` ⟹ **`dw/d(k_load) < 0`**, and from that single fact nine
  unconditional relations (§2.2's table) — and **only** nine;
* three quantities that are **not** monotone, each with its turning point in closed form:
  `w_P = k_t*V/(2*(b*R + k_t*k_e))` for `P_mech`, `w_conv = V/(2*k_e)` for `P_conv`, and
  `w_eta = (V/k_e)*(1 - sqrt(1 - k_e*k_t/A))` with `A = b*R + k_t*k_e` for efficiency;
* a **tight**, `R`-independent ceiling: `w_noload = V/k_e` is the exact supremum of shaft
  speed over every positive loop resistance, approached as `R → 0` and never attained;
* three quantities for which **no** direction is guaranteed and none was asserted:
  `T_motor` (its heat is a rising copper channel plus a falling mechanical one, and at the
  reference point the two are 10.02 W and 10.55 W), `T_wire`, and the coupled response as an
  algebraic theorem.

At the declared constants and `R = 0.53 Ω`: `w_noload = 813.5593`, `w_P = 401.8845`,
`w_conv = 406.7797`, **`w_eta = 724.3128`** rad/s.

### 2.2 The coupled sweep — low / medium / high, and two more points

Only the load coefficient moves. Every other declaration is byte-identical across the five
runs (`test_g1_the_sweep_moved_only_the_load_declaration` compares the serialized drives with
the load removed and finds **one** payload).

| `k_load` | `w` (rad/s) | `I` (A) | `tau_e` (N·m) | `tau_load` (N·m) | `P_int` (W) | `P_wind` (W) | `P_feed` (W) | `P_mech` (W) | `P_src` (W) | `eta` | `T_wire` (K) | `T_motor` (K) | iters | residual |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `5e-08` | 786.4938 | 1.58164 | 0.0466585 | 0.0309286 | 12.37145 | 1.00349 | 0.12967 | 24.3252 | 37.9595 | 0.640820 | 300.7127 | 330.6771 | 5 | 2.17e-14 |
| **`1e-07` (low)** | 769.9140 | 2.53136 | 0.0746750 | 0.0592767 | 11.85535 | 2.59207 | 0.33357 | 45.6380 | 60.7526 | 0.751211 | 301.8332 | 333.1369 | 7 | 1.47e-14 |
| **`2.444e-07` (medium)** | 726.2262 | 4.86177 | 0.1434222 | 0.1288977 | 10.54809 | 10.01723 | 1.25414 | 93.6089 | 116.6824 | **0.802253** | 306.8924 | 347.1691 | 9 | 1.22e-15 |
| `4e-07` | 683.6382 | 6.80058 | 0.2006172 | 0.1869445 | 9.34722 | 21.02966 | 2.51738 | 127.8024 | 163.2140 | 0.783036 | 313.8349 | 369.6732 | 11 | 2.09e-15 |
| **`6e-07` (high)** | 634.2826 | 8.61269 | 0.2540743 | 0.2413886 | 8.04629 | 37.20748 | 4.17107 | 153.1086 | 206.7045 | 0.740712 | 322.9231 | 403.7951 | 13 | 1.37e-16 |

The `b` family, at the reference `k_load`:

| `b` | `w` (rad/s) | `I` (A) | `tau_load` (N·m) | `P_int` (W) | `P_mech` (W) | `P_src` (W) | `eta` | `T_motor` (K) | iters | residual |
|---|---|---|---|---|---|---|---|---|---|---|
| `2e-06` | 737.3625 | 4.55444 | 0.1328811 | 1.08741 | 97.9815 | 109.3064 | 0.896393 | 320.9426 | 9 | 4.03e-15 |
| `2e-05` | 726.2262 | 4.86177 | 0.1288977 | 10.54809 | 93.6089 | 116.6824 | 0.802253 | 347.1691 | 9 | 1.22e-15 |
| `8e-05` | 687.7244 | 5.78341 | 0.1155926 | 37.83719 | 79.4959 | 138.8018 | 0.572729 | 427.7945 | 9 | 2.21e-14 |

### 2.3 Which monotonicity relations were *derived* as guaranteed, and whether they held

| Relation in `k_load` | Guarantee | Held? |
|---|---|---|
| `w`, `E` decreasing; `I`, `tau_e`, `tau_load`, `P_src` increasing; `tau_loss`, `P_int` decreasing | **unconditional**, at fixed `R` | **yes** — 240/240 consecutive pairs, and 4/4 on the coupled sweep |
| `P_wire` (both leads, and the winding) increasing | unconditional at fixed `R` | **yes**, coupled |
| `P_mech` increasing **while `w > w_P`** | conditional | **yes** — condition re-evaluated at each point's own converged `R`, and shown to *fail* beyond it |
| `P_conv` increasing **while `w > w_conv`** | conditional | **yes**, same |
| `eta` — **no** monotone direction; interior maximum at `w_eta` | conditional, with a location | **yes** (§2.4) |
| `T_motor`, `T_wire` | **not guaranteed; not asserted** | measured, and the two heat channels shown to move in opposite senses |

**Relations in `b`, and the asymmetry that proves the derivation is load-bearing.** `dw/db < 0`
by the same argument, so `w`, `E` fall and `I`, `tau_e`, `P_src` rise exactly as in `k_load`.
But `tau_load` and `P_mech` **reverse** — unconditionally decreasing in `b` where they rose in
`k_load` — and `P_int = b*w^2` becomes ambiguous where it was strictly decreasing. Both are
measured over 241 points. No fixture triple has a reason to behave that way.

**Deviation D-1, recorded not absorbed.** Preregistration §2.8 called `tau_loss = b*w`
ambiguous in `b`. Carrying the differentiation through the balance instead of stopping at
"a rising factor times a falling one" gives
`d(tau_loss)/db = w*(1 - b/(2*k_load*w + b + k_t*k_e/R))`, whose bracket is **strictly
positive for every positive `b`**. The preregistration under-claimed; `tau_loss` is
unconditionally increasing in `b`, it is now asserted over five decades, and the abstention
that *was* necessary — `P_int`, which turns at `b = 2*k_load*w + k_t*k_e/R` — is asserted as a
turning point against that closed form.

### 2.4 The efficiency prediction, and why it is the strongest result in G1

Preregistration §2.7(4) predicted, **before the sweep ran**, that efficiency would *not* be
monotone, that it would rise and then fall, that its maximum would be at the **third of five
points**, and that the turning speed would be `w_eta ≈ 724 rad/s`.

Measured: `0.640820 → 0.751211 → 0.802253 → 0.783036 → 0.740712`. Maximum at index 2. The
converged loop resistance at that point is `0.5299157 Ω`, giving `w_eta = 724.3198` rad/s —
which lies **between** the third point's 726.2262 and the fourth's 683.6382, exactly as
preregistered. The same closed forms locate the `P_mech` and `P_conv` maxima on the dense
algebraic grid to within one grid spacing.

That is prediction, not postdiction: §2.3 and §2.7 are in commit `57164d8`, which precedes
every source change.

### 2.5 Energy and thermal coherence at every point

**Energy: closed at all eight coupled points**, worst residual **2.21e-14** relative against a
declared 1e-9 — four orders inside the budget, and asserted as `< 1e-13` so a regression is
loud rather than merely inside the tolerance.

**Thermal coherence** is asserted as four relations, not as a temperature band: each body sits
strictly between ambient and its own steady-state rise `Q/hA` (the duration is finite, so
neither end is attained); the machine is hotter than either lead; every converged resistance is
exactly `rho(T)*L/A` at that body's own temperature to 1e-12; and every material reports
`IN_DOMAIN`. The range's upper end was chosen for that last reason and the choice is disclosed:
`k_load = 1e-6` leaves copper's declared `[200, 450] K` and was excluded **in advance**, so
"every point is in-domain" is a disclosed selection and **not** a confirmed prediction.

**No point is a fixture.** At every coupled point the back-EMF law, the loop KVL, torque
production, the load law, the viscous law, both power definitions and the speed balance itself
are recomputed from that run's own transported loop resistance and must reproduce the reported
numbers to 1e-12.

---

## §3 G2 — two motors. Independent **YES**, contamination **NO**, provenance **YES**, collision **YES and refused**

### 3.1 Two machines in ONE composition

`PropulsionDrive` has three concrete `isinstance`-checked slots, so two motors in one *drive*
is not expressible (re-measured). The N = 2 question is therefore answered one level up: the two
drives' problems, edges and torn endpoints are unioned into **one** `FixedPointCouplingPlan`
and executed by **one** `run_fixed_point` call — **28 problems, 40 declared edges, six torn
endpoints, 13 iterations, `CRITERION_MET`**, on universal core that was not edited by one byte.

Motor A and Motor B are the same type (`Motor`) with different parameters: 24 V vs 36 V,
`k_t = k_e` 0.0295 vs 0.04, winding 6.25 m vs 8.0 m, different load coefficients.

| Question | Answer | How it was measured |
|---|---|---|
| Can both exist independently? | **YES** | both converge in one composition; each reconciles its own energy balance to < 1e-13; each yields an efficiency in (0,1) |
| Does changing one affect the other? | **NO** | B's load coefficient changed from 5e-7 to 9e-7: B moves, the iteration count changes 13 → 15, and **every one of A's converged temperatures and its speed is bit-identical** |
| Is provenance unambiguous? | **YES, through problem ids** — and the half that is not clean is stated | all 28 problem ids are disjoint and every result names the problem it solved; but both machines share **one `run_id`**, so run-level provenance does not distinguish them |
| Does the union answer equal the stand-alone answer? | **YES, to convergence depth** | agreement ≤ 1e-12 at tolerance 1e-9 and ≤ 1e-15 at 1e-11, shrinking with depth — which is not how an interaction behaves. B is bit-identical at the union's own tolerance |

**What "independent" does and does not mean here (round-1 finding C-9, accepted).** The union
is block-diagonal by construction, so the *data plane* has no mechanism for interaction; what
the bit-equality test genuinely excludes is global mutable state, ordering dependence and any
hidden relaxation inside `run_fixed_point`. The **control plane is shared**: one tolerance, one
iteration budget, one `CouplingOutcome` for both machines, and no per-drive outcome token. A
union in which B exhausts the budget denies A its result even though A converged. That is a
real N = 2 limit and it is recorded rather than carried by the word "independent".

### 3.2 Did problem-id namespacing collide? **YES — and it is refused, not silently merged**

Two drives with distinct `drive_id`s but shared component ids share **11 of the 14** problem ids
`declared_problem_ids` returns; only `electrical_dc:<circuit_id>` and the two
`series_resistance:<drive_id>-n` joins carry a `drive_id`. Counting the three
`conductor_thermal_mass:<cid>` problems `compose` solves before the loop, the honest figures are
**14 of 17 derived ids carry no `drive_id`** (round-2 correction C-11, adopted).

So PROPULSION0's finding **F-1 is confirmed as to the collision**. Its second half is
**FALSIFIED**: F-1 recorded that "`FixedPointCouplingPlan` would accept the union". It does not.
The union is refused **twice, by universal core that was not edited**:

* `FixedPointCouplingPlan.__post_init__`'s fan-in guard sees **12 endpoints receiving more than
  one dependency** and refuses;
* `run_fixed_point`'s duplicate-problem-id guard refuses the union of the two problem lists.

Round 1's qualification is accepted and recorded: every one of the 14 problems has at least one
incoming edge, so **any** id collision between two *composed* drives necessarily trips the
fan-in guard first. The duplicate-id guard is defence in depth, reachable only by a
hand-assembled plan, not a second independent refusal for realizable input.

### 3.3 F-2: the preregistered prediction is **WITHDRAWN as unfalsifiable**, and what replaces it

This is the most important correction in the milestone, and it took two adversarial rounds.

Preregistration P6 predicted that a plan composed for a *different* drive sharing ids would be
accepted and would return a different answer. Round 1 demonstrated it with a plan carrying a
looser tolerance and a distant seed. Round 2 rejected that as a *control* substitution wearing
an identity costume, and produced the decisive field analysis: **a plan composed by `compose` is
a pure function of `(drive_id, the component ids, seed, tolerance, max_iterations,
temperature_metric)`.** No load coefficient, no machine constant, no voltage, no geometry and no
material enters a `FixedPointCouplingPlan`.

**Measured, and now asserted:** two drives differing in *every* physical declaration compose to
plans that compare **equal**; and running one drive with "the other drive's plan" produces a
result **bit-identical** to running it with a plan composed from itself. P6 has no instances. It
is recorded as **withdrawn**, not as confirmed.

**What survives is real, and is not an N = 2 finding.** `compose` and `run_propulsion_drive` are
two independent authorities over one composition, and `_refuse_unresolved_edges` checks only
that the plan's problem ids are a **subset** of this drive's. A plan whose edges transport the
lumped body's *steady-state* temperature instead of its *final* temperature is therefore
accepted by a drive that would never have declared it. Measured: `converged = True`, energy
reconciled to **2.6e-15**, and `T_motor = 359.339 K` against a true `347.169 K` — **12.2 K
wrong**, with every control (plan id, seed, tolerance, budget) identical. That is this
repository's own worst historical defect class, and it bites at **N = 1**.

**Consequence for the next milestone, stated plainly:** drive-scoped problem-id namespacing —
the repair F-2 has been carrying since PROPULSION0 — **would not touch this**. The failure is
plan-to-composition under-identification, not identity collision.

### 3.4 The minimal candidate semantic — written down, deliberately **not built**

Per the brief, this is evidence gathering and is **not enough to force `ComponentInstance`**.
None was created. Recorded so it is retrievable:

* **The failure, exactly:** `run_propulsion_drive(drive, plan)` accepts any plan whose problem
  ids are a subset of `declared_problem_ids(drive)`. Two things it cannot see: (a) a plan
  composed against a different transported quantity; (b) which drive authored it, since at
  equal ids the plans are equal.
* **The minimal candidate:** a **composition token** — one opaque value derived from the
  composition `compose` actually built (the ordered `(source_problem_id, source_quantity,
  target_problem_id, target_quantity)` tuples plus the seed), carried on the plan and recomputed
  and compared in `run_propulsion_drive`. It is *not* an identity contract, *not* a namespace,
  and *not* a `ComponentInstance`.
* **Why it cannot stay pack-local:** the token would have to live on `FixedPointCouplingPlan`,
  which is `engcore.coupling` — a universal record. Recomputing it pack-side without storing it
  is possible but then it is not carried, and a transported plan (distributed execution) is
  exactly the case where nothing on the receiving side can re-derive it. **This is the first
  measured pressure on `engcore.coupling` this lineage has produced, and it is one consumer.**
* **Deletion criteria:** delete it if a second consumer never appears; if `compose` becomes the
  only way to obtain a plan (making the second authority disappear); or if the plan gains the
  transported-quantity choice as a *declared, checked* field, which would close the measured
  half without a token.
* **Not built here** because there is exactly one consumer, the failure is fail-loud only in
  hindsight, and the brief forbids it on this evidence.

### 3.5 A measured cost, recorded not repaired

The pack publishes `compose` for one drive and nothing for two: building the union required the
private `_executors`. The N = 2 composition is expressible but not **published**. One consumer;
not repaired.

---

## §4 G3 — the four negative cases, and the proof nothing executed

Every case refuses **before a solver object exists**. The proof is PROPULSION0's `_SolverSpy`,
which wraps all seven solver factories the pack can reach, plus a **live** circuit spy installed
at the DC boundary. `spy.calls == []` means none was *constructed*, not merely that none ran.

| Case | Refused by | Proof |
|---|---|---|
| **missing mechanical load** | `PropulsionDrive.__post_init__` (`load=None` or wrong type), `TypeError` when omitted, and `RotationalLoad` itself for `k_load = 0` | no drive record exists, so nothing can be executed; `spy.calls == []` |
| **unsupported operating point** | `admit_speed_demand` — a demanded speed `>= V/k_e` has no positive-current solution for **any** `R > 0` | 3 parametrisations incl. the supremum itself; `spy.calls == []` and no problem is posed |
| **impossible torque demand** | `admit_torque_demand` — the declared load law absorbs `tau_d` only at `sqrt(tau_d/k_load)`, bounded by the same ceiling | 3 parametrisations, boundary found by **bisecting the gate**; `spy.calls == []` |
| **efficiency outside its validity range** | `drive_efficiency` — non-positive source, negative loss channel, a balance that does not close, a record that misreports its own residual, and both endpoints of the declared range | 7 constructions, `spy.calls == []`, and the live circuit spy silent |

**The gates are tight and their limit is stated.** `V/k_e` is the **exact supremum** of
achievable speed over all `R > 0` (asserted numerically: the closed form approaches it from
below as `R → 0`), so nothing weaker can be refused without knowing `R`. Refusing is fail-closed
because `R > 0` only raises the voltage a demand needs. **Admission is not a promise:** a demand
is exhibited that the gate admits and the drive then misses.

**The two gates are one ceiling in two units, and are not counted twice.** Preregistration §4
said so before the measurement; the test asserts set-equality of the two refusals; and the
round-2 qualification is adopted — that set-equality test contributes **no independent
evidence**, because composing the ceiling through the load law reproduces the gate's own
expression. The guard that does contribute is
`test_g3_the_torque_ceiling_agrees_with_the_load_models_own_evaluator`, which finds the gate's
boundary by bisection and compares it to `LOAD_TORQUE_METRIC` from the published solver as
`R → 0`, sharing arithmetic with neither.

**Ownership rule recorded on the function** (round-1 finding C-13): `admit_torque_demand`
restates `QUADRATIC_ROTATIONAL_LOAD_MODEL`'s law and **must change whenever `RotationalLoad`
gains a term**. A constant Coulomb or gravity torque would make the ceiling silently wrong, and
the bisection guard is what catches it.

---

## §5 G4 — efficiency, classified

**It is a derived, state-dependent relation over power terms the accounting already computed
and reconciled.** Not a material property, not a model parameter, not a solver output. Each of
the four is a separate executable discrimination:

| Claim | Evidence |
|---|---|
| not a material property | it takes five different values across the sweep while **one** serialized material payload covers all five, and neither material record has a field naming it |
| not a model parameter | no model in the pack or in `domains.mechanical_rotational` names it among its inputs or validity conditions (9+ model records scanned) |
| not a solver output | no `ScientificResult` in any converged run carries such a metric, and no model declares one as an output |
| a relation over terms that already exist | recomputed from **two different problems'** results — the circuit's source power and the machine's mechanical output — and equal to the function's value to 1e-15; repeated calls agree; `dataclasses.asdict` of the accounting is unchanged by calling it |

### What was added, exactly

**One pure function**, `drive_efficiency(accounting)`. **No field, no record, no schema token,
no serialization, no posed problem, no dependency edge, no model, no solver, no capability** —
asserted structurally: `"efficiency"` appears in no serialized drive payload, no
`EnergyAccounting` field, no problem id, no dependency name or quantity, and no schema string;
the composition is still 14 problems, 20 edges and 3 tears; the pack's schema-token count is
unchanged at six.

Three companion names exist because G3's negative cases forced them and for no other reason:
`no_load_speed`, `admit_speed_demand`, `admit_torque_demand`. The public surface grew by
**exactly four names**, asserted.

### The validity range — derived, then corrected

Preregistration §5 said `0 < eta < 1` was a *consequence* of the enforced balance. **Round 1
falsified that using this milestone's own fixtures**, and round 2 found the correction itself
still one premise short. The recorded position:

* the balance plus four non-negative losses derives **`eta <= 1`**;
* adding `mechanical_output >= 0` — a premise the four checked losses do **not** contain —
  gives **`0 <= eta <= 1`**;
* the **strict** endpoints, and the sign of the output, are a **declared refusal scoped to this
  composition**, justified by one property of this drive and not of energy conservation:
  `tau_load = k_load*w^2` with `k_load > 0` gives `P_mech = k_load*w^3 > 0`, and the supply is a
  positive ideal source.

A four-quadrant or regenerative drive (`P_mech < 0`) is therefore **outside what this relation is
declared over**, and the refusal message says so rather than claiming such a record cannot exist.

### Not double-counting, and where the guard cannot reach

No number is stored. The two operands are already-reconciled terms of one record, and the
balance is **recomputed from the six terms** rather than read from `balance_residual`, so a
record that certifies its own consistency is refused too.

**Round-1 finding C-8, closed at the right boundary and measured, not predicted.**
`reconcile_drive_energy` is published, and G2's own two-machine composition calls
`run_fixed_point` directly and never builds a `DriveRun` — so the published pair
`drive_efficiency(reconcile_drive_energy(drive, run))` returned **0.80268** for a
budget-exhausted run against a true **0.80225**, with a 1.4e-14 residual, because *the balance
closes at every iterate*. The convergence gate now sits on the function that produces the
number. **And the limit is stated:** the guard is complete over every `CoupledRun` and is
structurally **absent** at the `EnergyAccounting` record boundary, because no arithmetic over
six terms that balance at every iterate can distinguish a converged state from an unconverged
one. Closing it would require a field on a published record added so a guard could exist — the
exact failure mode §5 of the preregistration refuses.

---

## §6 New contracts: **NONE**

`src/engcore/scientific/` and `src/engcore/coupling/` are byte-identical to the preregistration
commit, asserted from git **and** from the working tree. Every pre-existing domain and system
pack outside `systems/propulsion/` is likewise untouched. **No new file was created under
`src/`**: every new function went into a file PROPULSION0 already added, which is why
PROPULSION0's own scope gates needed no repair.

Every presumed-unnecessary contract in preregistration §6 stayed unnecessary:
`ComponentInstance`, `Port`, `Connector`, `SystemDefinition`, a component framework, a universal
`Material`, a universal energy graph, `EfficiencyModel`, an efficiency metric on any result, a
drive-scoped problem-id namespace, a plan-to-drive binding token, per-endpoint coupling
tolerances, a second `CouplingOutcome` member, a `DriveDemand` record, a torque-demand solver, a
sweep record, an operating-point registry — **none forced**.

---

## §7 Falsifier — two rounds, 8 findings closed, 1 prediction withdrawn

**Round 1: SURVIVES WITH REQUIRED CHANGES.** No BLOCKER. Four MAJOR:

| # | Counterexample | Closed by |
|---|---|---|
| C-7 | the F-2 demonstration was a *control* substitution (loose tolerance, distant seed) presented as an identity failure; the named repair would not have prevented it | replaced with an equal-controls demonstration — then withdrawn entirely in round 2 |
| C-8 | `drive_efficiency(reconcile_drive_energy(drive, unconverged_run))` returns a number through the published path, and G2's own union already takes that path | `CouplingOutcome` guard at the top of `reconcile_drive_energy`; measured 0.80268 vs 0.80225 |
| C-12 | `0 < eta < 1` was declared, not derived, and the milestone's own fixtures reach both endpoints | derivation weakened to what the premises give; refusal message corrected |
| C-13 | `admit_torque_demand` duplicates a law the rotational domain owns, **and the guarding test shared the duplication** | ownership rule on the function; guard now bisects the gate and compares to the model's own evaluator |

Round 1's MINORs C-3 and C-4 (three preregistered relations derived and then never asserted)
were closed with three new tests. C-1, C-2, C-5, C-6, C-9, C-10, C-11, C-14, C-15 are accepted
as qualifications and are stated in this document rather than argued away.

**Round 2: SURVIVES WITH REQUIRED CHANGES.** No BLOCKER. One MAJOR:

| # | Finding | Closed by |
|---|---|---|
| C-1 | **the C-7 repair relocated its counterexample instead of closing it** — the lever moved from one `compose` keyword to another, and the demonstration is bit-identical with the second drive deleted | P6 **withdrawn as unfalsifiable**; the plan's field composition asserted directly; the surviving N = 1 finding stated in §3.3 |

Round 2's MINORs, all adopted: C-3 (state where the convergence guard structurally cannot
reach), C-4 (the missing `mechanical_output >= 0` premise, and a stale claim still standing in
the test that carried its correction), C-5 (the set-equality test contributes no independent
evidence), **C-6 (the circuit spy was INERT — six assertions no implementation could violate,
one of them in a test that solved circuits twice; it is now installed at the DC boundary and a
test proves it can fail)**, C-7 (the 8 × 240 inequalities are two independent propositions at
fixed `R`), C-8 (two assertions weaker than preregistered), C-9 (a frozen exact float in a
module whose docstring forbids them), C-10 (the F4 scan omitted the function these rounds
edited, and a substring check defeated by `torque=`), C-11 (this document).

---

## §8 Deviations from the preregistration

| # | Deviation | Status |
|---|---|---|
| **D-1** | §2.8 called `tau_loss` ambiguous in `b`. It is **unconditionally increasing**; the preregistration under-claimed. | Corrected, derived, and now asserted over five decades. |
| **D-2** | §5 said `0 < eta < 1` is *derived* from the balance. It derives `eta <= 1`; `eta >= 0` needs a premise the checks do not contain; the strict endpoints are declared. | Corrected in code, message and this document. |
| **D-3** | §3.2's prediction **P6** is **withdrawn as unfalsifiable**, not confirmed. | §3.3. |
| **D-4** | §2.6's "every relation in §2.2 on the dense algebraic sweep" excludes `P_wire`: `DriveOperatingPointSolver` produces no element powers, so it is asserted on the coupled sweep only. | Recorded. |
| **D-5** | §2.7(6) ("every material in-domain") is a **disclosed selection**, not a confirmed prediction: the range's upper end was chosen so it holds. | Recorded in §2.5. |

---

## §9 What this proved

1. **A load sweep is a physical relation here, not three fixtures** — nine unconditional
   monotonicity relations derived from one implicit-function argument and checked at 240
   consecutive pairs, plus an asymmetry between the `k_load` and `b` families that no memorised
   number reproduces, plus three turning points located where their closed forms say.
2. **A quantitative prediction made before the run matched**: efficiency is non-monotone, its
   maximum is at the third of five points, and it turns at `w_eta = 724.32` rad/s.
3. **Two machines of the same type ran in ONE composition** — 28 problems, six torn endpoints —
   with **exact** independence, on universal core that was not edited.
4. **The two-motor identity question is answered and F-1 is half falsified**: the collision is
   real, and it is *refused* by unedited universal core rather than silently merged.
5. **Four negative cases refuse before a solver object exists**, two of them from a bound that is
   the exact supremum over every loop resistance.
6. **Efficiency needs no representation beyond one pure function.** Nothing was stored.
7. **NONE of the sixteen presumed-unnecessary contracts was forced.**

## §10 What this did NOT prove

1. **Anything about hardware.** MODEL-CONSISTENT only.
2. **Any topology but one series loop across one ideal source.** Unchanged.
3. **Any transient.** The sweep is a family of steady points.
4. **N ≥ 3**, a machine and a non-machine element kind in one drive, or a fourth `DriveElement`
   kind.
5. **A shared bus between two drives.** Any shared endpoint trips the fan-in guard; only the
   disjoint case was measured.
6. **Control-plane independence at N = 2.** One tolerance, one budget, one outcome.
7. **That efficiency needs no representation in any future composition** — only in this one.
8. **That a hand-assembled `EnergyAccounting` is guarded against non-convergence.** It is not,
   and it cannot be without a field this milestone refuses to add.

---

## §11 Existing tests modified — exactly 1

| File | Defect | Repair | Why it is not weaker |
|---|---|---|---|
| `tests/test_composite_system0.py` | `test_t6f` reads `git diff <CS0 prereg> HEAD` over the **whole tree** and compares against a hand-named allow-list, so it fails for every later milestone however correct | this milestone's **three** new files named individually: the two `docs/evidence/` documents and `tests/test_propulsion0_ext.py` | not one file COMPOSITE-SYSTEM0 asserts unchanged is excluded; **nothing under `src/` was added to the list**, because this milestone adds no source file |

PROPULSION0's own gates needed **no repair**, as predicted in §7 of the preregistration — its
`--diff-filter=MD` plus working-tree read tolerates a successor's additions, and its
`test_the_scope_gates_can_fail_and_do_not_fail_on_an_addition`, which pins the *file set* of its
own source trees, still passes because every new function went into a file that already existed.
No architectural test was weakened.

---

## §12 Test counts

| Tier | Result |
|---|---|
| Targeted (`test_propulsion0_ext.py`) | 80 passed |
| Targeted (`test_propulsion0.py`, unchanged) | 82 passed |
| FAST (`-m "not expensive"`) | 1920 passed / 0 failed / 627 deselected |
| FULL (sequential, `--basetemp=.pytest_tmp_propext_full`, no `-n auto`) | **2547 passed / 0 failed / 0 errors**, 943.31 s |

Baseline FULL was 2467. The delta is **exactly +80**, the number of tests this milestone
adds: nothing was removed, renamed away or deselected. The `--basetemp` directory is covered
by `.gitignore`'s `.pytest_tmp_*/` rule and is not committed.

---

## §13 Commits

| Commit | Contents |
|---|---|
| `57164d8` | Preregister the four coverage gaps — **alone**, not amended |
| `42de91f` | Close four coverage gaps: sweep, two machines, refusals, efficiency |
| `28349cf` | Close four adversarial findings against the extension |
| `e480c49` | Withdraw an unfalsifiable prediction and repair an inert guard |
| `aea9ad2` | Record the extension evidence and update the master context |
| *(final)* | Record the measured FULL result |

---

## §14 Reopen triggers, from measured evidence only

1. **A second consumer of a composed plan, or any transported plan** → §3.4's composition token,
   which is the first measured pressure on `engcore.coupling` this lineage has produced.
2. **A third term on `RotationalLoad`** (a constant Coulomb or gravity torque) →
   `admit_torque_demand`'s restated ceiling is wrong; the bisection guard catches it.
3. **A four-quadrant or regenerative drive** (`P_mech < 0`) → `drive_efficiency`'s declared
   range is wrong for it, and the relation needs a stated sign convention.
4. **N = 2 where one machine may fail to converge** → the shared control plane: one tolerance,
   one budget, one outcome, no per-drive token.
5. **A second consumer of the N = 2 composition** → the pack must publish it; `_executors` is
   private today.
6. **Every PROPULSION0 reopen trigger** (§18 of the sealed record) remains live and unchanged,
   except that F-1's second half is now falsified and F-2 is restated by §3.3.

## §15 Next milestone, chosen from measured evidence

**Recommended: bind a plan to the composition it was built for** — the single measured defect
this milestone produced, reachable at N = 1, fail-loud only in hindsight, and the first pressure
this lineage has put on `engcore.coupling`. It is small, it has a stated minimal candidate and
deletion criteria (§3.4), and it would be the first milestone to *test* whether a universal
coupling record must carry composition identity rather than assuming it must not.

Explicitly **not** recommended on this evidence: drive-scoped problem-id namespacing (§3.3 shows
it would not close the measured failure); `ComponentInstance` (nothing forced it at N = 2); a
per-drive coupling outcome (no consumer that cannot restructure); a transient or inertial
milestone (it reopens the coupling-scheme axis before the cheaper defect is closed); and a
mechanics framework (still no second consumer of any rotational record).
