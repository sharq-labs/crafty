# FLUID ↔ THERMAL SCALAR-REDUCTION COUPLING — EVIDENCE

**Kind:** evidence. What executed, what diverged from the preregistration, what
was attacked and survived, what did not, and what is still open.

**Branch:** `fluid-thermal-scalar-coupling`, worktree `crafty-ft-coupling`,
based on `origin/cloud/crafty-post-field-support` @ `6caa1139`.

**Preregistration:** `docs/fluid-thermal-scalar-coupling-prereg.md`, committed
alone at `03d07cb` *before* any coupling implementation existed and **not
edited afterwards**. Every divergence from it is recorded in §G below rather
than corrected in it.

**Commits, in order.** `4352f40` CSTR temporal repair · `012e6c0` lumped
CONTROL-value repair · `03d07cb` preregistration (alone) · `60a27f2` the
coupling and its tests · `fda742a` adversarial-round closures.

**Decision status: PROPOSED.** Not DESIGN-FROZEN. A first execution of a
second coupled pair is evidence for a decision, not the decision.

---

## A. The two prerequisite domain defects, and their repairs

Both were diagnosed by `docs/temporal-semantics-stress-evidence.md` §15.3 as
**domain defects, not contract residues**, and both are repaired in the domain
that owns them.

> **Where that document lives.** It is on the sibling branch
> `origin/temporal-semantics-stress`, which is a *descendant* of this branch's
> baseline and is therefore not in this working tree. Read it with
> `git show origin/temporal-semantics-stress:docs/temporal-semantics-stress-evidence.md`.
> The same is true of `docs/fluid-thermal-preparation.md` and
> `experiments/fluid_thermal_prep/coupling_probe.py`, cited throughout this
> document, which are on `origin/fluid-thermal-preparation`. Neither branch was
> merged or cherry-picked here: this milestone's tree contains only its own
> work, so that "no core file changed" is measurable against a clean baseline. Neither repair changed a universal record; both problems still
serialize under `scientific_problem/2`.

### A.1 DEFECT A — the CSTR misreported itself as steady

**Reproducer, before repair.** `build_cstr_problem(run)` for a run integrating
`[0, 400 s]` returned a problem with `is_time_dependent is False`.

**Root cause, measured rather than read.**
`ScientificProblem.is_time_dependent` is exactly `bool(self.initial_conditions)`
(`src/engcore/scientific/ir/problem.py:392`). `build_cstr_problem` declared
**no** initial conditions and **no** `STATE` variable for either evolving
state, although `ReactorRun` carries both initial values and the horizon. The
same omission left the horizon off the record entirely: the only
`[time]`-dimensioned parameter was `residence_time` = 200 s, so a records-only
reader taking "the `[time]` parameter" for the horizon was silently wrong by
**exactly a factor of two**.

**Repair** (`src/engcore/domains/kinetics/cstr/problem.py`):

* `C_A` and `T` are declared `STATE` variables, named distinctly from the
  `C_A:final` / `T:final` observables;
* each carries an `InitialCondition` at `t = 0 s` holding the run's own
  declared initial value, so `is_time_dependent` is now `True`;
* `end_time` is a declared parameter, distinct from `residence_time`, exactly
  as the sibling `thermal/conduction1d` problem declares its own;
* `verify_problem_matches_run` refuses a record whose declared initial state or
  horizon contradicts the run it is paired with, so the repair is **enforced**
  rather than written down.

**Residue, pinned rather than remembered.** `end_time` and `residence_time`
remain indistinguishable **by dimension**; only their enumerated names separate
them. A universal contract that could separate them is deliberately not
introduced. `tests/test_temporal_domain_defect_repairs.py::
test_defect_a_the_horizon_is_on_the_record_and_is_not_the_residence_time`.

**Serialization impact:** payload content changes (two variables, two
conditions, one parameter, one metadata key). Schema string unchanged.

### A.2 DEFECT B — `thermal_lumped` declared its controls without their values

**Reproducer, before repair.** One body, 40 W against 4 W: `ScientificProblem`
payloads **byte-identical**, final temperatures **15.5640 K apart**. (The
17.10 K figure in the temporal evidence is the same defect at that milestone's
own operating point.) This is the null control that forced the temporal
milestone to withdraw its record-indistinguishability claim.

**Root cause.** `heat_input` and `ambient_temperature` are correctly declared
`CONTROL` variables — that judgement is right and is kept. A
`ScientificVariable` carries no value, so nothing on the record said *at what
value* they were imposed.

**Repair** (`src/engcore/domains/thermal_lumped.py`). The imposed value is
stated with the one existing core record for "this variable holds this value at
this stated instant": an `InitialCondition` carrying `time = 0 s`. That is
exact for a realization whose declared assumption is that the heat input is
constant over the integrated interval.

* `ambient_temperature` is always recorded — the body declares it, so the
  record can always state it, and before this it could not.
* `heat_input` is recorded when supplied. It stays optional because in a
  composition the value arrives across a declared `QuantityDependency`, and a
  record stating a value the loop overrides every sweep would be worse than one
  stating none. **Omission is a real answer.**
* `LumpedThermalSolver.prepare` refuses to solve a record that states an
  imposed heat different from the bound one; `verify_problem_matches_body`
  refuses a contradicted ambient.

**What the repair does NOT do.** Recording a control's value does not make it
resolved: `unresolved_inputs` reports a `CONTROL` regardless of any condition
on it, so a composition still sees both controls as inputs needing a supplier.
Asserted.

**One existing test adapted, and how.**
`tests/test_electrothermal_vertical.py::test_gate_g0b_…` unpacked the thermal
problem's *single* initial condition. It now selects the `STATE` condition by
name, asserts the condition set is exactly `{temperature, ambient_temperature}`,
and **additionally** asserts that the coupled `heat_input` still carries no
declared value. The claim under test is unchanged; the assertion is strictly
stronger.

---

## B. The coupled equations

```
Fluid    P1:  div(u c) − D ∇²c = s(x,y)   on [0,L]²,  u = ω(−(y−L/2), (x−L/2))
              c = c*(x,y) on all four sides,  c* = sin(πx/L) sin(πy/L)
              s = u·∇c* − D∇²c*                                (manufactured)
              reduction:  Φ_D = ∮ −D ∇c·n dl   [m²/s per unit depth]

Property P2:  D(T)      = D_ref (T/T_ref)^n           n = 1.75
Property P3:  hA(Φ_D)   = (ρ c_p) Φ_D d
Thermal  P4:  C dT/dt   = Q − hA (T − T_amb);  transported metric T_ss = T_amb + Q/hA
```

Four problems, four `QuantityDependency` edges, one 4-cycle, one `TornEndpoint`
cutting `T → P2.temperature`, seeded at `T_amb`. Execution order **computed**
from the records after the tear: `P2 → P1 → P3 → P4`.

Frozen configuration: `L = 1 m`, `ω = 1 /s`, `D_ref = 0.01 m²/s` at
`T_ref = 300 K`, `n = 1.75`, `ρ c_p = 1.2e3 J/(m³K)`, `d = 1.0e-3 m`,
`T_amb = T_0 = 300 K`, `C = 600 J/K`, `Q ∈ {6, 40} W`, `n_cells ∈ {8,16,32,64}`.

---

## C. Units, and the dimensional check performed before execution

| Edge | Quantity | Unit | Source | Target |
|---|---|---|---|---|
| E1 | `Φ_D` | `m**2/s` | P1 metric `phi_D:wall` | P3 STATE variable `wall_efflux` |
| E2 | `hA` | `watt/kelvin` | P3 metric `wall_conductance` | P4 parameter `ambient_conductance` |
| E3 (torn) | `T` | `kelvin` | P4 metric `steady_state_temperature` | P2 STATE variable `temperature` |
| E4 | `D` | `m**2/s` | P2 metric `diffusivity` | P1 parameter `diffusivity` |

```
[ρ c_p · Φ_D · d] = J/(m³K) · m²/s · m = J/(s·K) = W/K   ✓
[Q/hA]            = W / (W/K) = K                        ✓
[D_ref (T/T_ref)^1.75] = m²/s                            ✓
```

**No conversion factor lives in coupling code.** `ρ c_p` and `d` are declared
parameters of model P3 with a declared validity domain, a version and a
provenance binding — and the reason they had to be is a contract doing its job:
`QuantityDependency.unit_exemplar` is dimension-checked at both endpoints, so a
`m**2/s` efflux **cannot** be wired into a `watt/kelvin` endpoint. Three
negative tests exercise that refusal (`test_n3_*`,
`test_the_scale_restoration_cannot_be_bypassed_by_wiring_efflux_to_conductance`).

---

## D. The analytical coupled fixed point

Substituting the exact `Φ_D = 8D`:

```
    T*  =  T_amb + Q / ( ρ c_p · d · 8 · D_ref · (T*/T_ref)^n )              (1)
```

With `T_amb = T_ref` and `θ = T*/T_ref` this reduces to the closed algebraic
identity

```
    θ^(n+1) − θ^n  =  Q / (ρ c_p · d · 8 · D_ref · T_ref)                    (★)
```

**Why `8D` is exact.** On `y = 0` the outward normal is `−ŷ`, so the outward
diffusive efflux density is `−D ∇c*·n = +D (π/L) sin(πx/L)`, whose integral
over that side is exactly `2D`. Four sides → `8D`, independent of the grid,
independent of `ω`, exactly linear in `D`.

| Q [W] | `T*` [K] | Picard gain `−n(T*−T_amb)/T*` |
|---|---|---|
| 6.0 | **348.163813** | **−0.24209** |
| 40.0 | **481.835346** | **−0.66042** |

Both match the preregistered §5.3 values to the digits committed.

**Independence — the falsifier's attack 7, closed by construction and verified
by parsing.** `src/engcore/systems/fluidthermal/reference.py` imports
`__future__` and `math` and nothing else (asserted by AST walk plus a
name-reference scan); it takes every constant as an explicit argument; it finds
the root by **bisection on the residual of (1)**, a different method from the
loop's Picard sweep; and it is checked against (★), an algebraically
independent second statement of the same root, to `1.7e-16`.

**What that independence does not buy — falsifier C-7, corrected.** Removing a
shared *code path* is not removing a shared *value*. The test module feeds one
frozen constant table to both the system and the reference, so a mistyped
`D_ref` would move both together. What closes that is different and is now
named in the reference module's own docstring: the test pins the reference's
**absolute** output (348.163813 / 481.835346 K) against a preregistration
written before the implementation existed. One degeneracy survives even that:
`ρ c_p` and `d` appear only as a **product**, here and in model P3, so doubling
one and halving the other is undetectable by every check in this milestone.
Recorded, not fixed.

---

## E. The Fluid numerical reduction against `Φ_D = 8D`

### E.1 The shipped boundary convention — verified, and it is not the preparation's

`docs/fluid-thermal-preparation.md` §FT0/P2 computed `Φ_D = 2 D Σ c_edge`, a
one-sided gradient `(c_wall − c_cell)/(dx/2)` against a wall value of exactly
zero. That is what the problem *record*'s `BoundaryCondition(value=0)` states,
and it is **not what `assemble()` implements**: the shipped stencil places a
ghost cell one full `dx` beyond the boundary-cell centre and gives it
`c*(ghost centre)`, which is not `−c_cell`. Measured:

| D | n | prep formula `Φ/D` | shipped ghost convention `Φ/D` | exact |
|---|---|---|---|---|
| 0.01 | 32 | 4.6384 (−42.0 %) | **6.3192** (−21.0 %) | 8 |
| 0.01 | 64 | 6.0837 (−24.0 %) | **7.0419** (−12.0 %) | 8 |
| 0.50 | 32 | 7.9224 (−0.97 %) | **7.9612** (−0.49 %) | 8 |

The shipped convention is adopted: it is the flux the assembled operator
conserves, it is exactly the boundary data the linear system was built from,
and it is uniformly twice as accurate. **The sign convention is unchanged:
positive means efflux.** Declared by four `BoundaryOrientation` records and
verified against the solve's own per-side numbers by a
`wall_efflux_orientation` validation check, which the fluid problem declares as
an admission requirement.

### E.2 The reduction is COMPUTED — attack 2, refuted, and strengthened

`assemble()` records every diffusive boundary face it built as
`(row, side, ghost_value)`, where `ghost_value` is the very number it moved onto
the right-hand side. `wall_efflux_per_side` sums `D·(c_cell − c_ghost)` over
exactly those faces, reading `field_flat[row]` for each. Three proofs:

* nudging **one** boundary cell by 1.0 moves the reported efflux by exactly
  `D` per boundary face of that cell;
* an independent re-derivation written in the test from `c_star` and the cell
  geometry — not from the recorded faces — agrees to `1e-12`;
* the reported value is **never** `8D` and its deficit halves under refinement.

The falsifier strengthened this beyond what the milestone claimed. Summing the
exact-field discrete flux over a side gives
`D · 2 sin(π/2n) · Σ_i sin((i+½)π/n) = D · 2 sin(π/2n) / sin(π/2n) = 2D`
exactly, at every `n`. So `Φ̂_D = 8D + D·Σ_faces (c_cell − c*_cell)`: the ghost
half integrates to exactly `8D` and **100 % of the observed deficit is
boundary-cell solution error**. The metric is not a disguised closed form; it
is a closed form plus a pure, measurable field error.

### E.3 PC3 — measured

At `D = 0.01`, grid ladder: `Φ/8D − 1` = **−0.3415 / −0.2101 / −0.1198** at
`n = 16/32/64`, ratios 1.63 and 1.75 (preregistered band [1.6, 2.4]).
At the coupled operating point (`D ≈ 0.0130`): **−0.2748 / −0.1665 / −0.0939**,
ratios 1.65 and 1.77. Preregistered bounds ≤ 0.30 at `n=32` and ≤ 0.18 at
`n=64`: **met** (0.167, 0.094).

---

## F. The thermal mapping

`hA = (ρ c_p) Φ_D d` restores the extensive scale, and it is **the only place
an absolute thermodynamic scale enters the composition**. The fluid domain's
refusal to carry one is preserved: `c` is and stays dimensionless.

At the converged `n=32`, `Q=6 W` point: `T = 355.6678 K`,
`D = 0.0130 m²/s`, `Φ_D = 0.08677 m²/s`, `hA = 0.10412 W/K`,
`Q/hA = 55.6678 K` above a 300 K ambient.

**Falsifier C-3 (MAJOR), closed in the declaration.** Model P3's assumption
tuple previously read the field as "the normalized excess
`(T−T_amb)/(T_w−T_amb)`" as though that were a property of its supplier. It is
not. The supplying field is pinned by a **manufactured volumetric source** with
no physical counterpart, and the normalization reference `(T_w − T_amb)` is
defined nowhere in the composition and reconciled with the body's own excess
nowhere. `_W_ASSUMPTIONS` now states all three facts explicitly and adds that
**no conservation is claimed across the interface**: this model relates a wall
efflux to a conductance, it does not assert that the energy leaving the body
equals the energy entering the slice, and the two participants' sources are
unrelated.

---

## G. Iteration sequence, and the divergences from the preregistration

### G.1 Case A — nominal, `Q = 6 W`

| n | outcome | sweeps | `T_num` [K] | `T_num − T*` [K] | last \|ΔT\| [K] |
|---|---|---|---|---|---|
| 16 | `CRITERION_MET` | 16 | 362.028284 | **+13.8645** | 5.06e-05 |
| 32 | `CRITERION_MET` | 13 | 355.667840 | **+7.5040** | 9.56e-05 |
| 64 | `CRITERION_MET` | 12 | 352.115773 | **+3.9520** | 7.42e-05 |

Preregistered §7 predicted 362.0 / 355.7 / 352.1 ± 1.0 K and 13 ± 4 sweeps at
`n=32`. **All met.**

### G.2 Case B — strong feedback, `Q = 40 W`, budget 40

`ITERATION_LIMIT_REACHED` at 40 sweeps, `T = 493.991579 K`
(`T* = 481.835346`, +12.1562 K), last `|ΔT| = 8.241e-03 K`. Preregistered
prediction: `ITERATION_LIMIT_REACHED`, last `|ΔT|` in (1e-3, 5e-2), `T ≈ 494`.
**All met.**

### G.3 Preregistration divergences — four, none corrected in the prereg

1. **PC4's linearized form fails at `n=16`** (30.1 % against a preregistered
   25 % bound; 16.2 % at `n=32`, 8.5 % at `n=64`). The linearization is
   first-order in `ε` and `|ε| = 0.275` at `n=16` is not small. The **exact**
   form of the same statement — a relative flux error `ε` acts on the coupled
   map exactly as replacing `Q` by `Q/(1+ε)`, because `hA` enters only as a
   product with the efflux — agrees to better than `1e-4` relative at **every**
   grid. That exact form is what the test asserts, and the linearized
   divergence is recorded here rather than fixed there.
2. **The shipped boundary convention differs from the preparation's** (§E.1).
   Preregistered in advance in prereg §3.3, so this is a divergence from the
   *preparation*, not from the preregistration.
3. **PC1 as preregistered cannot fail** — see §G.4.
4. **`cross_check` became a declared field.** The preregistration did not
   name it; the falsifier showed it decides an admission outcome from an
   unrecorded keyword. It is now a serialized field of `FluidSlice`.

### G.4 PC1 is a non-falsifiable criterion — falsifier C-1 (MAJOR)

PC1 compares the reported temperature against the coupled relation formed from
the **same sweep's** efflux. Within one Gauss-Seidel sweep the order is
`P2 → P1 → P3 → P4`, so the thermal leg consumes exactly that efflux: the two
sides are one closed form evaluated twice and the residual is round-off **by
construction**, for any run, converged or not.

The criterion is immutable, so it is executed, reported as what it is, and
**demonstrated** non-falsifiable: a one-sweep run with outcome
`ITERATION_LIMIT_REACHED`, sitting more than 20 K from the fixed point, still
satisfies PC1 to `1e-3 K`.

**PC1′, added beside it, states the claim PC1 was meant to make.** A fixed
point relates two consecutive sweeps, so the coupled relation is formed from
the **previous** sweep's efflux. Measured: `≤ 1e-4 K` (the coupling tolerance)
on the converged case; `> 0.1 K` on a truncated four-sweep run; `8.24e-3 K`
(82× tolerance) on case B at its full budget — which is both a clear failure
of PC1′ and a measure of how close to converged case B actually was.

---

## H. Convergence and non-convergence

### H.1 The three required cases

* **(A) nominal convergent** — `Q = 6 W`: `CRITERION_MET`, 12–16 sweeps,
  error against the independent closed form falling first-order (§I of prereg
  PC2: bounds 20/11/6 K, measured 13.86/7.50/3.95 K, ratios **1.848** and
  **1.899**, band [1.6, 2.4] — met).
* **(B) coupling non-convergence with both subsolvers valid** — `Q = 40 W` at
  the 40-sweep budget. **Every** fluid solve reported `CONVERGED`, every
  closed-form evaluation reported `NOT_APPLICABLE` (success), and every result
  passed the requirements its own problem declared, in all forty sweeps of a
  run that did not converge at all. Asserted per sweep, per participant. This
  is **not** a solver failure and is not reported as one.
* **(C) scientific-admission failure** — `n = 8`: a raised
  `ScientificValidationError`, no coupled result. See §I.

### H.2 Why case B did not converge, and the reviewer-required spike

The undamped Gauss-Seidel sweep contracts at `|g|`, the derivative of the
coupled map. Measured tail contraction ratio: **0.7561**, constant to four
digits. Closed-form gain at the exact fixed point: **0.6604**.

`architecture-decision-reviewer` required a spike before any relaxation
classification. **Case B stands exactly as preregistered and as executed;** a
**separate, additionally labelled diagnostic** raises only `max_iterations` to
200 — no damping, no tolerance change, nothing else — and reaches
`CRITERION_MET` at **sweep 56**, `T = 493.995086 K`.

**So case B was a contracting map that exhausted its preregistered budget, not
a genuine non-convergence.** That is the reviewer's stopping condition (i):
the existing typed `max_iterations` field already expresses the whole
situation, **no execution concept is missing**, and relaxation is **not forced
by any executed evidence**.

**Relaxation classification: (B) a pack-local numerical choice — and not even
that, because none was made.** `FixedPointCouplingPlan` has no relaxation field
(asserted over its exact dataclass field set) and this pack adds none, so there
was nothing to tune. Option (A) "already expressible by an existing execution
policy" is **refuted on a measurement**: no execution-policy record exists
anywhere in `src/`. Option (C) "a genuinely missing universal execution
concept" is **not supported**: the spike shows the budget, not the algorithm,
was the binding constraint.

The 0.756-vs-0.660 discrepancy is itself a finding: the fluid's flux error is a
function of `D`, so the discrete efflux grows slightly faster than linearly in
`D` and the **discrete** map's effective exponent exceeds 1.75. The coupled
loop contracts more slowly than the exact physics would.

### H.3 The scope of what was proven — falsifier C-2 (MAJOR)

The manufactured source absorbs both `D` and `ω`, so `c*` — and therefore
`Φ_D(exact) = 8D` — is **independent of the velocity field**, and the
closed-form coupled fixed point contains no `ω` term anywhere. At the exact
level the PDE participant of this composition is the map `D ↦ 8D`.

Measured, as the falsifier required:

| ω [1/s] | `Pe_cell` at `n=32` | executed `T_num − T*` [K] | outcome |
|---|---|---|---|
| 0.1 | 0.170 | **+0.809** | `CRITERION_MET` |
| 1.0 | 1.640 | **+7.504** | `CRITERION_MET` |
| 10 | 16.4 | — | **REFUSED** (admission) |
| 100 | 164 | — | **REFUSED** (admission) |

A 10× change in the advective physics moves the **executed** answer by 6.7 K
while the **exact** answer does not move at all: 100 % of the `ω`-response is
discretization error. That is the `c:centre` lesson (§J) recurring one level
up, and it is now a test rather than a discovery waiting to happen.

**The reassuring half is structural, not lucky.** At `ω ≥ 10` the fluid
participant leaves its own declared admissibility and the coupling **refuses**
rather than transporting the error. The operating points where the transported
number would be most wrong are exactly the ones the admission gate stops.

**Honest statement of what this milestone establishes:** composition mechanics
between a real PDE domain and a real lumped domain, and one verified scalar
reduction whose `D`-dependence is exact physics. It does **not** establish that
PDE↔lumped coupling holds where the PDE's *interior* physics enters the
exchange. The named follow-on that removes this is the source-free,
prescribed-wall-value configuration (preparation §FT8), whose wall Sherwood
number is a genuinely non-trivial function of the Péclet number.

---

## I. Admission refusal

**Enforced by the producer, not by the loop, and for a measured reason.**
`run_fixed_point` transports `result.values[dep.source_quantity]` directly,
knows nothing about validation, and explicitly does not catch a sub-solve that
refuses. So every executor reads its own result through an admission-guarded
reader before returning it. A failure raises out of the loop; there is **no
path** on which it is logged, defaulted, retried or skipped.

| Direction | Failure | Cause | Result |
|---|---|---|---|
| Fluid → Thermal | real, in-loop | `n = 8`: `admissibility_bound` fails (`c ∉ [0,1]`, violation 6.22e-3 at the coupled `D`, `Pe_cell = 6.82`) | `ScientificValidationError`, no coupled result |
| Fluid → Thermal | real, in-loop | `cross_check` off ⇒ `sparse_dense_assembly_agreement` is `NOT_RUN` — "we did not check" is not "it passed" | `ScientificValidationError` |
| Fluid → Thermal | real, in-loop | `ω ≥ 10` at `n = 32` (§H.3) | `ScientificValidationError` |
| Thermal → Fluid | fault-injected, in-loop | a failing `lumped_balance_residual` | `ScientificValidationError` |

The thermal direction is fault-injected because **no declaration of this
participant can be made to fail its own balance residual** — a closed form
satisfies the equation it was derived from, always. What is under test is the
coupling's response to a failing thermal validation, not the thermal solver's
arithmetic.

**The guard is load-bearing, demonstrated not asserted.**
`read_wall_efflux_unguarded` returns a positive number from the same
inadmissible `n=8` result that `read_wall_efflux_with_admission` refuses.

**A measured asymmetry, recorded rather than hidden.**
`fluids/transport2d` publishes its own `validation_requirements` on its problem
record. `thermal_lumped` publishes **none**, so this consumer has to name what
it demands (`THERMAL_ADMISSION_REQUIREMENTS`). A requirement a consumer invents
is weaker evidence than one a producer publishes, and the module says so.

**Open, falsifier C-6 (MINOR):** neither side's *demanded* set survives
serialization. A `CoupledRun` shows which checks ran and their outcomes; it does
not show which were required. No record carries it and none is minted here.

---

## J. The `c:centre` falsification regression

**The hard prohibition of the preparation, preserved as an executable test.**

* **Exact half** (no solve): `exact_centre` is `1.0` to `1e-12` for every
  `D ∈ {0.01, 0.02, 0.05, 0.10, 0.50}`; spread exactly `0.0`. The manufactured
  source pins `c*`, so the centre value **cannot** respond to the fluid's own
  physical input.
* **Executed half**: the computed `c:centre` at `n=32` moves by **0.1614**
  across a 50× change in `D`. **100 % of that apparent sensitivity is
  discretization error.**
* **Contrast, on the same solves**: `Φ_D` changes by a factor of ~50 over the
  same range — its sensitivity is exact physics.
* **The regression a future author trips over**: a test asserts, over the
  pack's *declared dependencies* (not its source text, so it catches a
  rewiring however written), that no edge names `c:centre`, `c:max` or
  `c:min` as source or target, with the reason in the assertion message.

---

## K. The `QuantityDependency` field-endpoint negative result

**Verdict: the leak is real, it is pinned, and it is NOT fixed here.**

`QuantityDependency._declared_unit` resolves a name against
`result.values ∪ problem.variables ∪ problem.parameters`. Its module docstring
argues that `data_references` is deliberately not consulted *so that a field
endpoint returns an honest `MISSING`*. That protection is defeated by the
variable namespace: `transport2d` **must** declare `c:field` as a
`ScientificVariable` so `VariableBulkLinkage` has a binding target. Measured: a
dependency naming `c:field` as its source returns `()` — **checks clean** —
transports `dimensionless`, and implies exactly the field-transfer semantics
the record was written to refuse.

**Why it is not fixed.** Patching core here would mint a contract change on one
consumer's evidence, which `MIN-FOUNDATION-ET` §6 and `DATA-BOUNDARY0` both
refuse; and `ScientificField` is explicitly out of scope. Prereg §12/N2 forbids
it in advance.

**What this pack can honestly say instead.** It transports no field, and that
is proved structurally: no declared edge names `c:field`, every declared source
resolves to a scalar metric or variable, and the fluid problem names no
input-side bulk data. **That is a convention of this pack, not a contract**, and
the test says so in its own name. A different pack wiring `c:field` somewhere
would still check clean.

**Blocker for the future, stated as one:** the first field-valued coupling
attempt will not be refused at declaration time. It will be *accepted* and will
fail — or silently mis-transport — at execution, where no transfer semantics
exists at all. That is a known open contract hole and it belongs in the
promotion decision, not in this milestone's diff.

---

## L. Provenance

**Reconstructible from the serialized `CoupledRun` alone** (round-tripped
through JSON and `from_dict` in a test): the four exchange identities with
their endpoints and units; the coupling outcome; the sweep count; every
participant's model id/version, realization and solver identity (from
`provenance.bindings`); and each participant's typed inputs (from its own
result's `ProvenanceRecord.inputs`, e.g. the fluid's `diffusivity` and the
thermal leg's `heat_input`).

**No provider-specific string became a scientific fact.** `scipy` appears in
`SolverIdentity.backend` and in no model id and no assumption. Asserted.

**Gaps, recorded rather than redesigned.**

1. **The cross-check solver is not in provenance.** `solve_transport2d` runs
   `NativeDenseTransport2DSolver` when `cross_check` is on, and its output
   **gates admission** — yet `ProvenanceRecord.solvers` names only the sparse
   production solver. A second solver ran and decided whether the value could
   be transported, and the record does not name it. Closing it means editing
   fluid-domain provenance beyond this milestone's enumerated additive ceiling;
   recorded as a defect for the next fluid milestone.
2. **Demanded admission sets do not survive serialization** (§I).
3. **The torn-endpoint seed is not recoverable from any record.**
   `ET-VERTICAL` §4's finding, unchanged by a second consumer, asserted here on
   this composition's own records.
4. **The execution mapping `problem_id → callable` is not a record** and could
   not be one today (§M).
5. **`ScientificResult.metadata` carries the per-executor wall time** as a
   stringified float under `coupling_executor_wall_seconds`.
   `docs/min-cross-domain-foundation-evidence.md` §2.1 attempt 4 rejected that
   channel by name as "the untyped escape hatch this platform refuses
   everywhere else". It is used anyway, for one reason and under one
   restriction: **no typed record in this repository carries per-executor
   cost**, and the value is reported and never read by anything that decides.
   The objection is stated in the reading function's own docstring. If a
   consumer ever branches on it, the objection becomes live. (The key is
   deliberately not `wall_seconds_telemetry`: the fluid domain already writes
   that key as a `float` and its refinement gate reads it back typed as one —
   falsifier C-8.)
6. **`ScientificTwin` gained nothing.** `build_coupled_twin` was not reused and
   no twin was built. That is the fifth consecutive milestone in which the twin
   record acquires no evidence, and it is recorded as such.

---

## M. Fresh-process reconstruction

**Result: the coupled specification reconstructs and re-executes in a genuinely
separate interpreter, from JSON alone.**

Two payloads cross a `subprocess` boundary: the system declaration through this
pack's own `to_dict`/`from_dict` (domain-owned plain data, exactly like
`Transport2DDomain.to_dict`), and the coupling plan through
`FixedPointCouplingPlan.to_dict`. Nothing else. The fresh process rebuilds all
four problems, re-runs `plan.check_against` (no issues), recomputes the
execution order from the records, executes the loop, and reports the identical
outcome, sweep count and temperature to `1e-9 K`.

**No universal `ExecutableScientificSpecification` was built.**

**The residue, measured and named rather than papered over.** The payload
carries *declarations*, not *executors*. Which Python callable solves which
problem is supplied by `_executors` in the fresh process, from the
reconstructed declaration — it is not serialized, and **no record in this
repository can carry it**. `plan.to_dict()` carries the graph, the tear, the
tolerance and the budget, and no execution mapping. Evidence level for the
reconstruction claim: **L1, executed** — one consumer, in-process Python
executors, same repository on both sides.

---

## N. Reviewer verdict

`architecture-decision-reviewer`, invoked after the executed coupled result
existed.

* **Promotion question: DEFER.** PR1–PR4 are satisfied and produce
  *candidacy*, which is what the criterion was designed to produce; the FT
  preregistration itself states in advance that this "does not promote them".
  The decisive measurement is that the four facts a records-only reader still
  cannot recover (the seed, the supplier of a valued parameter, the
  participant-error/coupled-outcome relation, the `problem_id → callable`
  mapping) are the **same four** `ET-VERTICAL` measured. A second consumer
  reproducing an identical gap set strengthens evidence *within* L1; it does
  not identify a fact promotion would newly make recoverable. And promotion is
  additive later at zero cost today: **zero readers in
  `src/engcore/scientific/`, zero stored coupling artifacts, four in-repo call
  sites.**
* **Relaxation question: SPIKE REQUIRED.** Executed (§H.2). Option (A) refuted
  on a measurement (no execution-policy record exists anywhere in `src/`);
  outcome (i) reached; classification **(B) pack-local**, with no relaxation
  added.
* **Stress-test result the reviewer recorded:** the current plan shape holds
  for the two consumers built and **breaks for four of six** structurally
  different systems named in Crafty's own roadmap — 2:1 fan-in (refused by
  design), runtime-determined transport direction, mixed-dimension tears, and
  time-window coupling. "A shape that holds for the two consumers built and
  breaks for four of the six named next ones is not a universal contract."
* **The reviewer's negative precedent, which is directly on point:** preCICE —
  a decade-old project whose entire purpose is coupling — broke its
  coupling-scheme configuration at v3.0.0 and *removed* Broyden acceleration
  and second-order extrapolation "due to unclear use-case at high maintenance
  cost", and replaced `min-iteration-convergence-measure` (the exact
  measure+budget pair `FixedPointCouplingPlan` carries). Freezing that pair as
  universal on two consumers would freeze a shape specialists could not get
  right on hundreds.

---

## O. Falsifier verdict

`architecture-falsifier`: **SURVIVES WITH REQUIRED CHANGES. No BLOCKER.**

| # | Attack | Result |
|---|---|---|
| 1 | correct only because both quantities are scalars | **Lands as scoping (MAJOR)**, recorded in §H.3 and §K. Every exchanged quantity is a scalar and that is exactly why the composition is buildable today; the field case is a named open hole, not a solved one |
| 2 | `Φ_D` is the analytical formula in disguise | **NOT A REAL ISSUE**, and refuted more strongly than claimed — the ghost half integrates to exactly `8D`, so 100 % of the deficit is field error (§E.2) |
| 3 | coupling convergence mistaken for physical correctness | **NOT A REAL ISSUE at the record level.** `CouplingOutcome` refuses to reuse `ConvergenceState`; every property model is `SELF_CONSISTENT` with `references=()`; every check that could overclaim sets `establishes=None`. Where it *does* land is C-3, about a declared interpretation, closed in §F |
| 4 | relaxation tuned after seeing the answer | **NOT A REAL ISSUE.** No relaxation field exists to tune; the budget-200 run is a separately labelled diagnostic and case B stands as executed. Disclosed limit: PC2/PC3's numeric bounds were informed by prior probes, so passing them is strong evidence of *reproduction* and weak evidence of *prediction* — declared in the prereg preamble, not hidden |
| 5 | the sensitivity is discretization error again | **NOT A REAL ISSUE as stated** (the `D`-sensitivity is exact) — but restated sharply as C-2 and now measured and tested (§H.3) |
| 6 | a field endpoint still passes undetected | **Lands (MAJOR / BREAKING-RISK)** and stays open by preregistration (§K) |
| 7 | the reference shares implementation code | **NOT A REAL ISSUE** (AST-verified). The narrower shared-*constant* residue is corrected in the docstring and recorded (§D) |
| 8 | the fresh process smuggles state | **NOT A REAL ISSUE** (§M). The one addition was the unrecorded `cross_check`, now a serialized field |

**Required changes, all closed** in `fda742a`: C-1 (PC1 non-falsifiable →
reported as such, PC1′ added), C-2 (scope stated and measured), C-3 (model P3's
declared interpretation corrected), C-5 (`cross_check` serialized), C-7 (two
overclaiming docstrings corrected), C-8 (telemetry key collision renamed).

**Not closed, deliberately.** C-4 (a fluid–thermal run serializes under
`electrothermal_coupled_run/1`) is a **real BREAKING-RISK and a founder
decision, not a refactor**. Renaming the four schema strings would edit
`src/engcore/systems/electrothermal/coupled.py`, which prereg §9 forbids and
which would destroy the PR1 measurement this milestone exists to make. It is
recorded here with its cost: **today** the rename is three strings, three
`require_schema_any` calls and two assertion lines, with zero persisted
payloads anywhere in the tree; **after** any `CoupledRun` is stored or any
third consumer arrives, `require_schema`'s exact-match reader makes it a
migration with no path. This is the single cheapest-now/expensive-later item in
the whole milestone.

Also open, not fixed: C-6 (demanded admission sets unserialized), C-9 (a
tightened `validation_requirements` retroactively invalidates stored results of
that domain, mitigated by the `MODEL_VERSION` bump but not enforced by it), and
the cross-check solver's absence from provenance (§L.1).

---

## P. Core files changed

**Zero files changed under `src/engcore/scientific/`.** Asserted by a test that
diffs the tree against the baseline `6caa1139`, and again against `HEAD`.

**Zero files changed under `src/engcore/systems/electrothermal/`.** Same
measurement. `run_fixed_point`, `FixedPointCouplingPlan`, `TornEndpoint` and
`CoupledRun` are used **by object identity** (also asserted), not copied,
subclassed or re-implemented.

**Zero files changed under `src/engcore/domains/thermal/`** (byte- and
set-pinned).

Complete list of `src/` changes in this milestone:

| File | Change |
|---|---|
| `domains/kinetics/cstr/problem.py` | DEFECT A repair |
| `domains/kinetics/cstr/__init__.py` | three new exported names |
| `domains/thermal_lumped.py` | DEFECT B repair |
| `domains/fluids/transport2d/problem.py` | `phi_D:wall` metric + variable + model output + `METRIC_UNITS` + `EFFLUX_UNIT`/`EFFLUX_REFERENCE` + one validation requirement; `MODEL_VERSION` 0.1.0 → 0.2.0 |
| `domains/fluids/transport2d/solver.py` | `assemble` records diffusive boundary faces; `wall_efflux_per_side`; per-metric units in `extract_metrics` |
| `domains/fluids/transport2d/validation.py` | `wall_efflux_orientations`, the `wall_efflux_orientation` check, two guarded readers |
| `domains/fluids/transport2d/__init__.py` | exports |
| `systems/fluidthermal/` | **new package** (4 files) |

**No new schema string, no schema version moved, no new universal record, no
new core enum member.** Asserted.

The one identity that did move is `TRANSPORT2D_MODEL.version`, deliberately:
the model now states a second declared **output**, and a model that produces
something new is not the same model reference. A stored result citing `0.1.0`
still names a model that really did produce only `c`.

---

## Q. Architecture-fitness result

**PR1 — met.** The second consumer executes the coupling machinery unedited.
Measured by `git diff` against the baseline on
`src/engcore/systems/electrothermal/`, and by object identity.

**PR2 — met.** No branch, string parse, provider leak or domain name entered
`run_fixed_point`. Asserted by an AST scan over its **executable body** with
docstrings and comments stripped (the docstring legitimately discusses the
first consumer, and a scan that could not tell prose from code would be
measuring the comments).

**PR3 — met on three axes, and the reviewer added the sharpest qualification of
the milestone.** The two consumers differ in participant kind (2D finite-volume
PDE vs algebraic/lumped), cycle length (4 vs 3), transported-quantity kind (a
boundary-integral reduction of a field vs scalar element metrics), and
admission (one participant publishes requirements and refuses a real run; the
electrothermal participants publish none). **But on the axes that would stress
the record shape they are identical**: both exchange only scalars, both tear a
single kelvin edge, both use one scalar absolute tolerance, both are
single-process, both rebuild-per-sweep, both hit the parameter-invisibility
finding the same way, and both would be refused by the same fan-in and
mixed-dimension guards. *Two consumers that differ in physics but agree in
exchange topology are one data point about the exchange contract, not two.*

**PR4 — measured.**

* *Reused verbatim, zero edits:* the loop, the plan, the tear, the run and
  iteration records, the graph readers.
* *Duplicated between the packs, ~150 lines:* a system declaration dataclass, a
  `coupled_problems`, a `coupled_dependencies`, a `nominal_plan`, per-problem
  result builders, an `_executors` dispatch table, an entry point. **Every
  duplicated line is domain-specific** — which problems, which metrics, which
  solvers. The shared part needed no edit; the duplicated part could not have
  been shared.
* *Still unrecoverable by a records-only reader,* unchanged by a second
  consumer: the seed, the supplier of a valued parameter, the
  participant-error/coupled-outcome relation, the execution mapping.
* *New pressure this pair adds:* a per-participant admission asymmetry, and a
  genuine non-convergence case in which both subsolvers stay valid.
* *A real packaging defect this pair exposed:* a **fluids** pack must import an
  **electrothermal** pack to obtain the loop, which inverts "domain modules
  depend inward". That is a packaging fact and not evidence for a universal
  contract; the reviewer's option **A′** — relocate to a domain-neutral
  `src/engcore/coupling/` sibling and rename the four schema strings once,
  while nothing is stored — is a separate, smaller decision, and it must
  happen *after* this document records the PR1 measurement or it destroys it.

**Promotion verdict recorded: DEFER (option A), with A′ recommended as its own
next decision.** Revisit on any one of: a consumer with 2:1 fan-in or a
runtime-determined transport direction that the current plan expresses
*without* widening; a universal reader (planner, scheduler, execution-plan
compiler) that must consume a plan it did not construct; a measured fact about
coupling execution that no reader can recover and a universal record would; or
a coupling record persisted outside the repository.

---

## R. Evidence level

| Claim | Level |
|---|---|
| The two domain-defect repairs | **L2 — executed and enforced.** Reproducers recorded before repair; regression tests; the repaired declarations are refused when contradicted |
| `Φ_D` is computed from the solved discrete field | **L3 — executed, and analytically explained.** Three independent proofs plus a paper derivation showing the ghost half is exactly `8D` |
| The coupled numerical result agrees with an independent closed form | **L2 — executed at three grids** with first-order convergence and an exact error-inheritance identity. Weakened by one honest qualifier: PC2/PC3's numeric bounds were informed by prior reconnaissance, so this is strong evidence of reproduction and weaker evidence of prediction |
| Admission failure is a deterministic refusal | **L2 — executed on three real failures** (one from the benchmark's own physics, one from an unrun requirement, one from an out-of-envelope operating point) and one fault injection |
| `c:centre` is unsuitable as a coupling signal | **L3 — proven exactly and measured** |
| The field-endpoint leak | **L2 — measured and pinned**, not closed |
| No core contract was needed | **L2 — measured** by tree diff against the baseline |
| The coupling machinery is reusable across materially different pairs | **L1 — one additional consumer.** Reviewer: two consumers agreeing in exchange topology are one data point about the exchange contract |
| Fresh-process reconstruction | **L1 — executed**, one consumer, in-process Python executors, same repository both sides |
| PDE↔lumped coupling where the PDE's *interior* physics enters the exchange | **L0 — not attempted.** §H.3 |

---

## S. Decision status

**PROPOSED.** Nothing here is DESIGN-FROZEN. The coupling records stay
pack-local; the field-transfer contract stays deferred; the temporal contract
stays deferred; `ScientificField`, mesh and topology stay deferred; no
multiphysics framework, scheduler, participant registry or transfer operator
exists or is proposed.

---

## T. The exact next milestone

**`COUPLING-PACK-RELOCATION` — the reviewer's option A′, and nothing else.**

Move `FixedPointCouplingPlan`, `TornEndpoint`, `CoupledIteration`,
`CoupledRun`, `CouplingOutcome`, `run_fixed_point` and the graph readers from
`src/engcore/systems/electrothermal/coupled.py` into a domain-neutral
`src/engcore/coupling/` sibling — **not** into `src/engcore/scientific/` — and
rename the four `electrothermal_*` schema strings to consumer-neutral ones,
admitting both via the existing `require_schema_any`.

Why it is the next one, in one line each:

* It is the only item in this milestone that is **cheaper now than at any later
  point**: measured today at three strings, three `require_schema_any` calls
  and two assertion lines, with **zero persisted payloads anywhere in the
  tree**; after any stored `CoupledRun` or any third consumer, it is a
  migration with no path (`require_schema` is exact-match and this repository
  has no unfreeze mechanism).
* It fixes a real packaging defect this milestone exposed — a fluids pack
  importing an electrothermal pack — before a third coupled pack inherits it.
* It asserts **no universality**, adds nothing to `engcore/scientific/`, and
  keeps coupling execution out of the layer documented as executing nothing. It
  is therefore not the promotion the reviewer deferred.
* It must run **after** this document, which records the PR1 measurement the
  relocation would otherwise destroy.

Explicitly **not** the next milestone: promoting anything into universal core;
a field-valued coupling; `ScientificField`/mesh/topology; a temporal contract;
a second provider (CasADi/SUNDIALS); a relaxation or acceleration concept.

Named for later, with the reason: the **source-free, prescribed-wall-value**
fluid configuration, whose wall Sherwood number is a genuinely non-trivial
function of the Péclet number. That is what would raise §H.3 from L0 — it is
the configuration in which the PDE's interior physics reaches the coupled
answer as physics rather than as discretization error.

---

## U. Regression counts, and performance

### U.1 Test tiers, before and after

| Tier | Before (baseline `6caa1139`) | After | Delta |
|---|---|---|---|
| FAST (`-m "not expensive"`) | 1537 passed, 565 deselected | **1585 passed, 592 deselected** | +48 |
| **FULL** (no selection) | **2102 passed, 0 failed, 0 errors** | **2177 passed, 0 failed, 0 errors** (983 s) | **+75** |

**No test was weakened, skipped or xfailed.** Two existing assertions were
adapted and both became *stronger*: `tests/test_electrothermal_vertical.py`'s
single-initial-condition unpack now selects the `STATE` condition by name,
asserts the exact condition set, and additionally asserts that the coupled
`heat_input` still carries no declared value (§A.2); and
`tests/domains/fluids/test_transport2d.py`'s fresh-interpreter comparison now
compares each metric in **its own** declared unit rather than assuming every
metric of the domain is dimensionless, and additionally asserts the metric sets
match (§P).

One environment note, recorded because it cost a false failure at the start:
the suite's fresh-interpreter tests launch `sys.executable` with `cwd=REPO_ROOT`
and rely on `engcore` being importable there. `pyproject.toml`'s
`pythonpath = ["src", "."]` applies to the pytest process, not to a subprocess,
so a bare virtualenv without the package installed fails
`test_g1_fresh_process_reconstructs_and_reports_no_issues` for a purely
environmental reason. Resolved by putting `src/` on the interpreter's path.

### U.2 Performance

Measured on this machine, `n_cells` as stated, cross-check on (the production
configuration — with it off the fluid result is inadmissible and the coupling
refuses).

| n | sweeps | total loop [s] | fluid solve [ms/sweep] | thermal [ms/sweep] | `D(T)` [ms/sweep] | `hA(Φ)` [ms/sweep] | sweep total [ms] |
|---|---|---|---|---|---|---|---|
| 16 | 16 | 0.674 | 31.3 | 5.24 | 1.98 | 2.73 | 41.2 |
| 32 | 13 | 1.771 | 125.2 | 5.11 | 2.02 | 2.82 | 135.2 |
| 64 | 12 | 16.236 | 1342.4 | 4.80 | 1.95 | 2.82 | 1351.9 |

Case B (`Q = 40 W`, `n = 32`, 40 sweeps): 4.2 s. The budget-200 diagnostic
(56 sweeps): 5.8 s.

The PDE leg is 76–99 % of every sweep. The other three legs are dominated by
**record construction** — one `ProvenanceRecord` and one `ScientificResult`
each — not by their arithmetic, which is why they are milliseconds and not
microseconds. That is a measurement worth keeping: at this problem size the
platform's own bookkeeping is the same order as a 16×16 PDE solve.

---

## V. Post-milestone strength delta

Per the mission's exact scope — **these six dimensions only**, same 0–5 scale
as the prior audits. No other dimension was re-scored, and no score moves on
an argument that is not measured in §A–§U.

| Dimension | Before | After | Evidence |
|---|---|---|---|
| **Coupling Readiness** | 3/5 | **4/5** | A second, materially different coupled pair **executed** against `run_fixed_point` / `FixedPointCouplingPlan` / `TornEndpoint` / `CoupledRun` **unedited** — measured by `git diff` against the baseline on `src/engcore/systems/electrothermal/` (empty) and by object identity, with an AST scan proving no domain vocabulary entered the loop body (§Q, PR1/PR2). Three things are genuinely new to this platform's coupling evidence: a **closed-form reference for the *coupled* result**, independent by AST and by root-finding method, agreed with at three grids at the participant's own order (§D, §H.1); an executed **non-convergence case in which both subsolvers stay valid in all forty sweeps**, kept undamped and reported as `ITERATION_LIMIT_REACHED` (§H.1/§H.2); and **admission gating a transported value in both directions** (§I). **Held at 4, not 5**, on three measurements, not on caution: `architecture-decision-reviewer` returned **DEFER** on promotion because the four facts a records-only reader cannot recover are the *same four* the first consumer measured; the plan shape **breaks for four of six** structurally different systems named in Crafty's own roadmap (2:1 fan-in refused by design, runtime-determined direction, mixed-dimension tears, time windows); and the two consumers, while differing in physics, **agree in exchange topology** — both scalar-only, single kelvin tear, one scalar tolerance, single-process — so they are one data point about the exchange contract, not two. |
| **Fluid Multiphysics Readiness** | 1/5 | **3/5** | The Fluid domain now *participates* in an executed two-way coupling with a second real production domain, which it never had. Concretely it gained: a declared, versioned reduction (`phi_D:wall`, model version 0.1.0 → 0.2.0) computed from the solved discrete field over the boundary faces the assembly itself recorded (§E.2); four `BoundaryOrientation` records making "positive means efflux" a checked fact rather than a comment, verified against each solve's own per-side numbers; a declared `wall_efflux_orientation` admission requirement; and a guarded reader that **refuses to publish** the transported flux when the fluid result fails its own declared requirements — exercised on three real failures (§I). **Held at 3, not higher**, on the milestone's own sharpest finding: the exchange is scalar-only, and the exact coupled fixed point contains **no advective physics at all** — the manufactured source absorbs both `D` and `ω`, so at the exact level the PDE participant is the map `D ↦ 8D`, and a 10× change in `ω` moves the executed answer by 6.7 K while the exact answer does not move at all (§H.3). Field-valued exchange remains unexpressible, and its endpoint check leaks (§K). The PDE's *interior* physics does not yet reach a coupled answer as physics. |
| **Domain Extensibility** | 4/5 | **4/5 (unchanged)** | The new coupling is an additive pack; **no existing domain was forced to change in order to be coupled** — the thermal participant is used exactly as shipped, and the fluid participant's changes are one new reduction and its supporting records, not a coupling interface. The two domain edits in this milestone are **defect repairs** (§A), not extensibility work, and were required before coupling rather than by it. Nothing is raised, and one measured friction argues against raising it: a new coupled pack must import a **domain-named** system pack (`systems/electrothermal`) to reach the loop, which inverts "domain modules depend inward". That is a real packaging defect this milestone exposed, it is the subject of the next milestone (§T), and until it is fixed a third coupled pack inherits it. Recorded, not scored away. |
| **Core Stability** | 5/5 | **5/5 (unchanged)** | **Zero files changed under `src/engcore/scientific/`**, measured twice — against the baseline `6caa1139` and against `HEAD` — and asserted by a test. Zero files changed under `src/engcore/systems/electrothermal/` and under the byte- and set-pinned `src/engcore/domains/thermal/`. **No new schema string, no schema version moved, no new universal record, no new core enum member** (asserted). FULL regression green with **no test weakened, skipped or xfailed**; the two existing assertions that were adapted (one ET initial-condition unpack, one fluid per-metric unit comparison) each became *stronger*, and both adaptations are stated in §A.2 and §P. The one identity that moved is `TRANSPORT2D_MODEL.version` 0.1.0 → 0.2.0, deliberately and for a stated reason: the model now declares a second output, and a stored result citing 0.1.0 still names a model that really did produce only `c`. Stability was preserved through discipline, not through avoidance of change — 2 835 lines were added under `src/`. |
| **Admission Safety** | 3/5 | **4/5** | This is the first composition in which admission gates a **transported** value rather than a locally consumed one, and the enforcement point was chosen from a measurement rather than by preference: `run_fixed_point` transports `result.values[...]` itself and explicitly does not catch a refusing sub-solve, so the guard had to sit with the **producer**. Every executor reads its own result through an admission-guarded reader before returning it; a failure raises out of the loop and **no coupled result is produced** (§I). Proven on three *real* in-loop failures — the benchmark's own `admissibility_bound` at `n = 8`, a requirement that was `NOT_RUN` because the cross-check was off ("we did not check" is not "it passed"), and an out-of-envelope `ω` — plus a fault injection on the thermal leg, giving both directions. The unguarded reader is kept and tested to show the guard is load-bearing rather than decorative. A new declared requirement (`wall_efflux_orientation`) checks the transported quantity's **sign** against the solve's own numbers, because a sign error in a coupled loop turns cooling into heating and both converge. **Held at 4, not 5**, on three named gaps: the thermal participant publishes no requirements at all, so the consumer must **invent** what it demands — weaker evidence than a producer-published requirement, and labelled as such; the **demanded** set does not survive serialization, so a stored `CoupledRun` shows which checks ran but not which were required (§I, falsifier C-6); and the cross-check solver whose output *gates* admission is absent from provenance (§L.1). |
| **Provenance / Reproducibility** | 4/5 | **4/5 (unchanged)** | Real gains, and they are measured: a serialized `CoupledRun` round-trips and yields all four exchange identities with their endpoints and units, the outcome, the sweep count, every participant's model/realization/solver, and each participant's typed inputs (§L); a genuinely fresh interpreter rebuilds the system and the plan from JSON alone, recomputes the execution order from the records, and re-executes to `1e-9 K` (§M); `cross_check` moved from an unrecorded execution keyword onto the serialized declaration precisely because it decides an admission outcome (falsifier C-5); and the two domain repairs put onto universal records facts that were previously absent — the CSTR's horizon and initial state, the lumped body's imposed control values, both **enforced** against contradiction (§A). **Not raised**, because the gaps that hold it at 4 are unchanged or newly measured, not closed: the torn-endpoint **seed is recoverable from no record** (the first consumer's finding, unchanged); the execution mapping `problem_id → callable` is not a record and could not be one today; demanded admission sets are unserialized; the cross-check solver that gates admission is not in provenance; per-executor cost lives in the untyped `ScientificResult.metadata` bag that this platform rejected by name elsewhere, used here under a stated restriction and a stated objection (§L.5); and — the one this milestone *added* — **a fluid–thermal run serializes under `electrothermal_coupled_run/1`**, so the record's own schema name misattributes it to a different domain pair (falsifier C-4). That last one is the cheapest-now/expensive-later item in the milestone and is the subject of §T. |

**Overall reading.** The two dimensions that moved are the two the milestone
targeted, and each moved by exactly what was executed rather than by what was
built: **Coupling Readiness** 3 → 4 on a second executed pair with an
independent coupled reference and an honest non-convergence, held below 5 by a
reviewer's DEFER and a shape that breaks for four of six named next systems;
**Fluid Multiphysics Readiness** 1 → 3 on the Fluid domain's first real
participation in a coupling, held at 3 by its own measurement that the exact
coupled answer contains none of its advective physics. **Admission Safety**
3 → 4 on the first admission gate placed on a transported value, in both
directions, on real failures. The three unchanged dimensions are unchanged for
stated, measured reasons — including one, Domain Extensibility, where a new
packaging friction was found and deliberately not scored away.
