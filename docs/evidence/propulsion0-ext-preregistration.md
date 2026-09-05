# PROPULSION0-EXT — closing four coverage gaps: preregistration

**Written before any source change.** Committed alone and not amended. Every number
below that is not a *declaration* is a **prediction**; every prediction is derived
from the governing equations already in the tree, and each is stated so that a
measurement can contradict it.

| | |
|---|---|
| Baseline commit | `62a9fd7` (PROPULSION0, KEEP, `PROPOSED / L1 EXERCISED`) |
| Branch / worktree | `propulsion0-ext` / `/home/user/crafty-prop-ext` |
| Baseline FULL (orchestrator, sequential) | 2467 passed / 0 failed / 0 errors, 1172.83 s |
| Sealed record not to be rewritten | `docs/evidence/propulsion0-evidence.md` |
| Scope | exactly four gaps: G1 operating points, G2 two motors, G3 four negative cases, G4 efficiency |

**Epistemic ceiling, restated and unchanged.** Fixture machine constants and handbook
material data give **MODEL-CONSISTENT** results only. Nothing here is validated against
hardware. No claim below is a claim about a motor; every claim is a claim about what
this composition does with declarations it was given.

---

## §0 What is already proved and is NOT re-attempted

The Source→Wire→Motor→Load consumer, the Cu→Al differential, the eight derived
identities from one `component_id`, the zero-new-contract gate, the three energy
enforcement points, the ngspice provider substitution and the two adversarial rounds
are **done** and are not rebuilt, re-run for their own sake, or re-argued. This
milestone reuses `tests/test_propulsion0.py`'s harness (`thermal`, `conductor`, `wire`,
`machine`, `mechanical_load`, `build_drive`, `execute`) by import.

---

## §1 Fail conditions (any one is a STOP-and-report, not a workaround)

| # | Condition |
|---|---|
| **F1** | any byte of `src/engcore/scientific/` or `src/engcore/coupling/` changes |
| **F2** | any pre-existing domain or system pack outside `systems/propulsion/` and `domains/mechanical_rotational.py` changes |
| **F3** | a new universal contract is forced (`ComponentInstance`, `Port`, `Connector`, a component framework, a universal material system, a universal energy graph) |
| **F4** | product-specific logic appears — a branch on a material, component or domain name; a manually assigned torque; an rpm constant |
| **F5** | an existing test can only be made to pass by weakening what it asserts |
| **F6** | a gap can only be closed by freezing a fixture number rather than by a governing relation |

`F1`–`F2` are asserted from git **and** from the working tree, reusing PROPULSION0's
own `_touched()` gate semantics (`--diff-filter=MD` plus `git status --porcelain`).

---

## §2 G1 — multiple operating points. **The monotonicity derivation, done first.**

### 2.1 The governing system

At one steady operating point with loop resistance `R` (a control imposed on the
closed form), the drive solves

```
k_load * w^2 + (b + k_t*k_e/R) * w  -  k_t*V/R = 0        (positive root, w > 0)
E        = k_e * w
I        = (V - E)/R
tau_e    = k_t * I
tau_load = k_load * w^2
tau_loss = b * w
P_mech   = tau_load * w = k_load * w^3
P_int    = tau_loss * w = b * w^2
P_conv   = E * I
P_src    = V * I
```

Write `F(w) = k_load*w^2 + c*w - d`, with `c = b + k_t*k_e/R > 0` and `d = k_t*V/R > 0`.
`dF/dw = 2*k_load*w + c > 0` for `w > 0`, so the positive root is unique and the
implicit function theorem gives the sign of every response from the sign of the
corresponding partial of `F`.

### 2.2 Guaranteed monotone in `k_load` — **unconditionally**, at fixed `R`

`dF/d(k_load) = w^2 > 0`, so **`dw/d(k_load) < 0`**. From that one fact:

| Quantity | Relation used | Direction in `k_load` |
|---|---|---|
| `w` | implicit function theorem | **strictly decreasing** |
| `E = k_e*w` | back-EMF law | **strictly decreasing** |
| `I = (V - E)/R` | loop KVL, `R`,`V` fixed | **strictly increasing** |
| `tau_e = k_t*I` | torque production | **strictly increasing** |
| `tau_loss = b*w` | viscous loss | **strictly decreasing** |
| `P_int = b*w^2` | `w > 0` | **strictly decreasing** |
| `tau_load = tau_e - tau_loss` | torque balance | **strictly increasing** |
| `P_src = V*I` | `V` fixed | **strictly increasing** |
| `P_wire = I^2*R_element` | at fixed `R` | **strictly increasing** |

These nine, and only these nine, will be **asserted** as unconditional monotone
relations in `k_load`.

### 2.3 Guaranteed only *conditionally* — with the condition computed, not assumed

Three quantities are **not** monotone in `k_load` over the whole positive range,
and each has a turning point this preregistration computes in closed form.

**`P_mech`.** Eliminating `k_load` through the balance gives `P_mech = d*w - c*w^2`,
an inverted parabola in `w` with its maximum at

```
w_P = d/(2c) = k_t*V / (2*(b*R + k_t*k_e))
```

`P_mech` is increasing in `k_load` **iff `w > w_P`** (because `w` decreases in
`k_load`). Note `P_mech -> 0` as `k_load -> 0` and as `k_load -> inf`, so a
sweep spanning `w_P` is genuinely non-monotone.

**`P_conv = k_e*w*(V - k_e*w)/R`.** Inverted parabola in `w`, maximum at
`w_conv = V/(2*k_e)`. Increasing in `k_load` **iff `w > w_conv`**.

**Efficiency `eta = P_mech/P_src`.** With `A = b*R + k_t*k_e`,

```
eta(w) = (k_t*V*w - A*w^2) / (V^2 - V*k_e*w)
sign(d(eta)/dw) = sign( g(w) ),   g(w) = k_t*V^2 - 2*A*V*w + A*k_e*w^2
```

`g` has roots `w = (V/k_e) * ( 1 +/- sqrt(1 - k_e*k_t/A) )`, both real because
`A >= k_t*k_e`. Only the **lower** root is reachable (see §2.4), so

```
w_eta = (V/k_e) * ( 1 - sqrt(1 - k_e*k_t/A) )
```

and `eta` is **decreasing in `k_load` iff `w < w_eta`**, increasing iff `w > w_eta`.
Therefore `eta` attains an **interior maximum** at `w = w_eta`. When `b = 0`,
`A = k_t*k_e`, the square root vanishes and `w_eta` collapses onto the no-load
speed — i.e. a lossless shaft has no interior efficiency maximum. That degenerate
consistency will be checked too.

### 2.4 The reachable speed ceiling — a tight, `R`-independent bound

Multiplying the balance by `R` and letting `R -> 0` gives `(b*R + k_t*k_e)*w -> k_t*V`,
so `w -> V/k_e`. And `I > 0` requires `V > k_e*w`. Hence

```
w_noload = V/k_e     is the exact SUPREMUM of achievable speed over all R > 0,
                     approached but never attained.
```

This bound uses no loop resistance, so it is computable from declarations alone.
It is the basis of G3's two demand refusals (§4).

### 2.5 NOT guaranteed, therefore NOT asserted — reported as measurement

* **`T_motor`.** The machine's body receives `I^2*R_motor` (increasing in `k_load`)
  **plus** `b*w^2` (decreasing in `k_load`). A sum of an increasing and a decreasing
  term has no guaranteed direction, and at the reference point the two channels are
  10.02 W and 10.55 W — the same size. No monotonicity is preregistered for it.
* **`T_wire`.** Its heat is `I^2*R_a` alone, but `R_a` is itself a function of the
  temperature the loop is solving for, so the sign of the *coupled* response is a
  fixed-point property, not an algebraic one. Not asserted.
* **Anything in the coupled sweep, as an algebraic guarantee.** §2.2's derivation
  holds `R` fixed. Under thermal coupling `R` moves with `k_load`. The nine
  unconditional relations are therefore asserted **twice, for two different
  reasons**: exactly, on a dense fixed-`R` algebraic sweep (where they are theorems);
  and as an *empirical* claim on the coupled sweep, where a violation would be a
  genuine discovery about the feedback and would be reported as one.

### 2.6 The sweeps that will be run

**Dense algebraic sweep (the physical relation, not three fixtures).**
`DriveOperatingPointSolver` bound directly at a fixed loop resistance, over
**≥200 log-spaced `k_load` values spanning `1e-8 … 1e-5`** — three decades, wide
enough to contain `w_P`, `w_conv` and `w_eta`. Asserted: every relation in §2.2
strictly, pairwise, at every one of the ≥199 consecutive pairs; and each of the
three turning points in §2.3 located on the grid to within one grid spacing of its
closed-form position. A second dense sweep over `b` spanning `1e-6 … 1e-3`.

**Coupled sweep (energy and thermal coherence).** Five full runs through
`compose` + `run_propulsion_drive`, `k_load ∈ {5.0e-8, 1.0e-7, 2.444e-7, 4.0e-7,
6.0e-7}` (headline low / medium / high = `1.0e-7` / `2.444e-7` / `6.0e-7`), and three
runs over `b ∈ {2.0e-6, 2.0e-5, 8.0e-5}`. The ranges are bounded above by copper's
declared `[200, 450] K`: the endpoints were scouted **for admissibility only**, and
`k_load = 1.0e-6` is expected to leave the range and is deliberately excluded.

### 2.7 Predictions for `k_load` — stated before the sweep runs

1. All nine relations of §2.2 hold strictly at every consecutive pair, algebraically **and** under coupling.
2. `P_mech` is **increasing throughout**, because every sweep speed exceeds `w_P ≈ 402 rad/s` at the reference loop resistance.
3. `P_conv` is **increasing throughout**, because every sweep speed exceeds `w_conv = V/(2*k_e) ≈ 407 rad/s`.
4. **`eta` is NOT monotone across the coupled sweep.** With `R ≈ 0.530 Ω`, `A = 8.808e-4` and `w_eta ≈ 724 rad/s`, which falls **between** the `2.444e-7` point and the `4.0e-7` point. The sweep's efficiency will therefore rise and then fall, with its maximum at the third of the five points.
5. Energy balance closes at **every** point to better than the declared `1e-9` relative.
6. Every converged temperature stays inside `[200, 450] K` and every material reports `in_domain`.
7. `T_motor` is *expected* to rise across the `k_load` sweep because the copper channel outgrows the mechanical one, but this is **not** asserted as a guarantee (§2.5).

### 2.8 Predictions for `b` — the contrast that proves the derivation is real

`dF/db = w > 0`, so `dw/db < 0` and `I`, `tau_e`, `P_src` rise exactly as in `k_load`.
But `tau_load = k_load*w^2` and `P_mech = k_load*w^3` now **decrease unconditionally**
— `k_load` is fixed and `w` falls — whereas in `k_load` they rose (`tau_load`) or rose
only conditionally (`P_mech`). `tau_loss = b*w` and `P_int = b*w^2` become
**ambiguous** in `b`, where they were strictly decreasing in `k_load`.

That asymmetry is the falsification hook: if the sweep were three fixtures dressed as
physics, there is no reason for `P_mech` to be unconditionally decreasing in one
coefficient and conditionally increasing in the other.

### 2.9 G1 acceptance / falsification

* **Accept** iff every §2.2 relation holds strictly on both sweeps, every §2.3
  turning point is located where its closed form says, `eta`'s interior maximum
  appears where predicted, energy closes everywhere, and every state is in-domain.
* **Falsified** if any §2.2 relation reverses (the derivation is wrong, or the
  coupled feedback is not sign-preserving — either is a reportable finding), if a
  turning point is absent or misplaced, or if any residual exceeds `1e-9`.

---

## §3 G2 — two motors. **Predicted outcome, stated before building it.**

### 3.1 What "two motors" can even mean here

`PropulsionDrive` declares three concrete slots and `isinstance`-checks them, so a
single drive **cannot** hold two machines; PROPULSION0 recorded that as the
`DriveElement`/fixed-slot limit. The reachable N = 2 forms are therefore:

* **(a) two drives run separately in one process**, and
* **(b) two drives whose problems, edges and torn endpoints are unioned into ONE
  `FixedPointCouplingPlan` and executed by one `run_fixed_point` call** — one
  composition containing two machines.

Both will be built. (b) is the real test of the eight-identity result at N = 2.

### 3.2 Predictions

| # | Prediction |
|---|---|
| P1 | With **distinct** `component_id`s, `declared_problem_ids(A)` and `declared_problem_ids(B)` are disjoint, the union plan is admitted by the **unedited** `FixedPointCouplingPlan`, and the union run converges. |
| P2 | Each machine's operating point in the union equals its stand-alone value **to convergence depth**; any residual difference is attributable to the union's shared stopping criterion and will be shown to vanish by running the stand-alone case to the same depth. |
| P3 | Changing B's declaration leaves A's union result **unchanged**. The prediction is exact bit-equality; anything weaker is a finding. |
| P4 | With **shared** `component_id`s the problem ids **collide**, and PROPULSION0's F-1 is confirmed as to the *collision*. **F-1's further claim — that `FixedPointCouplingPlan` "would accept the union" — is predicted to be FALSE**: the plan's fan-in guard and `run_fixed_point`'s duplicate-id guard should each refuse it. Both are pre-existing universal-core guards and neither will be edited. |
| P5 | Exactly **11 of the 14** problem ids carry no `drive_id`; only `electrical_dc:<circuit_id>` and the two `series_resistance:<drive_id>-n` joins do. |
| P6 | **F-2 is confirmed and harmful.** A plan composed for a *different* drive that happens to share `drive_id` and component ids will be accepted by `run_propulsion_drive`, will report `converged = True`, will pass the energy reconciliation, and will return an answer that differs from the drive's own converged answer. |
| P7 | Provenance is unambiguous **only through problem ids**. Two drives in one union share one `run_id`, so run-level provenance does **not** distinguish them. |

### 3.3 What will NOT be built

`ComponentInstance` will **not** be created, and neither will any drive-scoped
namespacing, plan-to-drive binding token, registry or component framework. The brief
is explicit that this is evidence gathering. If identity genuinely fails, the exact
failure, the minimal candidate semantic, why it cannot stay pack-local, and its
deletion criteria are **written down** and nothing is built.

---

## §4 G3 — the four missing negative cases

Each must **refuse before any solver object is constructed**, proved with
`test_propulsion0.py`'s existing `_SolverSpy` (which counts every solver factory the
pack can reach) plus a circuit-solver spy that fails if called.

| Case | Mechanism | New code? |
|---|---|---|
| **missing mechanical load** | `PropulsionDrive.__post_init__` already refuses a non-`RotationalLoad`; a drive with `load=None`, with a wrong-typed load, and with the argument omitted entirely | **none** |
| **unsupported operating point** | a demanded speed `w_d >= V/k_e` has **no** positive-current solution for **any** `R > 0` (§2.4), so it is refusable from declarations alone | one pure refusal function |
| **impossible torque demand** | the declared load law absorbs `tau_d` only at `w_d = sqrt(tau_d/k_load)`; if that speed is at or above `V/k_e` the demand is unmeetable for **any** `R > 0` | one pure refusal function |
| **efficiency outside validity range** | `0 < eta < 1` is a *consequence* of the enforced balance plus positivity of the four loss terms; an accounting violating it, or a run that never converged, must refuse rather than return a number | see §5 |

**Stated limits, in advance.** The two demand refusals are **gates, not feasibility
oracles**: `w < V/k_e` is necessary and, by §2.4, *tight* (it is the exact supremum
over `R > 0`), but it is not sufficient — a drive that is admitted may still fall
short of the demand at its actual loop resistance. Admission is not a promise, and
the refusal direction is fail-closed because `R > 0` only raises the voltage a demand
needs. The two cases are **two projections of one ceiling** in two different declared
units; they are not independent evidence, and this preregistration says so rather
than counting them twice.

---

## §5 G4 — efficiency, classified

**Hypothesis.** Efficiency is **none of** a material property, a model parameter or a
solver output. It is a **derived, state-dependent relation over power terms the
energy accounting has already computed and reconciled**.

Four discriminating predictions, each falsifiable:

1. **Not a material property** — it moves when only `k_load` moves, with every
   material record byte-identical (G1's sweep is the evidence).
2. **Not a model parameter** — no `ScientificModelDefinition` in the pack or the
   rotational domain names it as an input or a parameter, and every composition
   converges without it.
3. **Not a solver output** — no `RawSolverOutput` and no `ScientificResult` in a
   converged run carries an efficiency metric.
4. **A relation, not a state** — it introduces no number that is not already in
   `EnergyAccounting`, and it is not an input to anything.

**Therefore what is added is exactly one pure function** over the existing
`EnergyAccounting`, plus the refusal that G3's fourth case needs. **No field, no
record, no schema token, no serialization, no problem, no dependency edge, no model
and no solver.** If the measurement contradicts the hypothesis — if efficiency turns
out to need a state — that is recorded and the function is deleted rather than
extended.

**The failure mode this is written to avoid:** adding a field so that efficiency
"exists". A second copy of `P_mech/P_src` stored anywhere would be double-counting a
term the reconciliation already owns. The test suite will assert that the function is
a pure relation: same inputs, same output, no attribute set anywhere, and the
composition's numbers unchanged by its existence.

---

## §6 Presumed unnecessary — each to be attempted against existing records first

`ComponentInstance`, `Port`, `Connector`, `SystemDefinition`, a component framework, a
universal `Material`, a universal energy graph, `EfficiencyModel`, an efficiency
metric on any result, a drive-scoped problem-id namespace, a plan-to-drive binding
token, per-endpoint coupling tolerances, a second `CouplingOutcome` member, a
`DriveDemand` record, a torque-demand solver, a sweep/study record, an operating-point
registry. **Prediction: NONE is forced.** Any that is forced will be reported with the
executable failure that forced it, loudly, in the report's item (6).

---

## §7 Existing tests

Predicted modifications: **exactly one file**,
`tests/test_composite_system0.py::test_t6f`, whose `allowed` set is a hand-named
whitelist over the whole tree and therefore fails for every successor milestone. The
repair is the established narrowest one: **name this milestone's three new files
individually** (`tests/test_propulsion0_ext.py`, and the two `docs/evidence/`
documents). Nothing that guard asserts unchanged is excluded.

PROPULSION0's own gates use `--diff-filter=MD` plus a working-tree read and are
predicted **not** to need repair — including
`test_the_scope_gates_can_fail_and_do_not_fail_on_an_addition`, which pins the file
*set* of this milestone's own source trees. To keep that prediction true, **all new
source code goes into the five files PROPULSION0 already added**; no new file is
created under `src/`.

If any other existing test needs to change, it is reported with the reason and with
the proof that the replacement is at least as strong.

---

## §8 Evidence ceiling

* MODEL-CONSISTENT only. No hardware.
* One topology: a single series loop across one ideal source. Unchanged.
* One operating point per run. The sweep is a family of steady points, **not** a transient.
* N = 2 machines. Nothing here says anything about N = 3, about a machine and a
  non-machine element kind in one drive, or about a fourth `DriveElement` kind.
* The dense algebraic sweep holds `R` fixed; it proves the closed form's structure,
  not the coupled system's.
* The two demand refusals are necessary conditions, tight but not sufficient.
* Efficiency is classified for **this** drive's accounting. It is not a claim that
  efficiency needs no representation in any future composition.
