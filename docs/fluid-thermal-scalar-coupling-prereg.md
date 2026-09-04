# FLUID ↔ THERMAL SCALAR-REDUCTION COUPLING — PREREGISTRATION

**Kind:** preregistration. Written and committed **alone**, before any line of
coupling implementation exists. Everything below is a commitment made in
advance: participants, exchanged quantities, the analytical coupled reference,
the numbers the execution must produce, the architecture it may not change, and
the conditions under which this milestone is to be reported as **failed**.

**Branch:** `fluid-thermal-scalar-coupling`, worktree `crafty-ft-coupling`,
based on `origin/cloud/crafty-post-field-support` @ `6caa1139`.

**Predecessors this executes rather than reopens.**
`docs/fluid-thermal-preparation.md` (FT2) recommended exactly one first
coupling proof and this document preregisters that recommendation.
`docs/electrothermal-vertical-prereg.md` §16 preregistered the condition under
which `FixedPointCouplingPlan` / `CoupledRun` / `run_fixed_point` become
promotion candidates — *a second, materially different coupled consumer written
against them without editing them* — and this milestone **is** that test.
`docs/temporal-semantics-stress-evidence.md` §15.3 R-A and R-B named two
**domain defects** as prerequisites; both are repaired in the two commits that
precede this document (`4352f40`, `012e6c0`) and neither is in scope below.

**Reconnaissance already performed, and declared.** The operating points, the
tolerances and the predicted numbers in §5–§8 were chosen from measurements
made *before* this document, in two places: the preparation's own probe
(`experiments/fluid_thermal_prep/coupling_probe.py`, on the
`fluid-thermal-preparation` branch) and a read-only reconnaissance script under
this session's scratch directory that touched no file in the repository. That
is deliberate and is stated here rather than hidden: a preregistration whose
tolerances are guesses is not a stronger instrument, it is a less informative
one. What this document fixes in advance is the **criteria, the participants,
the reference, the ceiling and the fail conditions** — and those are fixed
before the implementation exists, which is the property that matters. Every
divergence between a number predicted here and a number executed later is to be
recorded in the evidence document; **this file is not edited after commit.**

---

## 1. Participants — exact

### 1.1 Fluid

`src/engcore/domains/fluids/transport2d/` — the shipped 2D steady scalar
advection-diffusion benchmark, **physics unchanged**:

```
    div(u c) − D ∇²c = s(x, y)              on [0, L]²
    u(x, y) = ω(−(y − L/2), (x − L/2))      prescribed, divergence-free
    c = c*(x, y) on all four sides          Dirichlet
    c*(x, y) = sin(πx/L) sin(πy/L)
    s = u·∇c* − D∇²c*                       manufactured, derived analytically
```

Frozen configuration for this milestone: `L = 1.0 m`, `ω = 1.0 /s`, square grid
`n ∈ {8, 16, 32, 64}`. `c` is and stays **dimensionless**; no absolute
concentration or thermodynamic scale is claimed for it, here or anywhere.

`D` is the coupled input. It is a `ScientificParameter` of the fluid problem,
so a fresh `Transport2DDomain` and a fresh `ScientificProblem` are constructed
every sweep — the same rebuild-per-sweep discipline `ET-VERTICAL` already uses
for the DC circuit's resistance.

### 1.2 Thermal

`src/engcore/domains/thermal_lumped.py` — the shipped lumped body,
**physics unchanged**:

```
    C dT/dt = Q_in − hA (T − T_amb)
```

`src/engcore/domains/thermal/conduction1d/` is **not** the thermal participant
and is not touched: it is SHA-256- and set-equality-pinned by
`tests/test_thermal_t1_fidelity_inference.py`.

`hA` is the coupled input. It is a `ScientificParameter` of the thermal
problem, so the thermal problem is likewise rebuilt every sweep. The
transported result metric is `steady_state_temperature` (`T_amb + Q/hA`), and
that choice is load-bearing: `final_temperature` and `temperature` are the same
dimension and a dimension check cannot separate the three.

### 1.3 The two intermediate property problems

Neither is a new contract; each is one `ScientificModelDefinition` + one
`ModelRealizationDefinition` + one closed-form evaluator, structurally
file-for-file the shape of `src/engcore/domains/electrical/material.py`.

* **P — gas diffusivity.** `D(T) = D_ref (T/T_ref)^1.75`.
* **W — wall conductance (scale restoration).** `hA = (ρ c_p) · Φ_D · d`.

**No generic constitutive-relation IR is created.** If closing the loop
requires one, that is a fail condition (§10).

---

## 2. Exchanged quantities — names, units, direction

| # | Quantity | Symbol | Unit | From | To | Endpoint kind |
|---|---|---|---|---|---|---|
| E1 | wall diffusive efflux | `Φ_D` | `m**2/s` | fluid result metric `phi_D:wall` | W problem variable | OBSERVABLE metric → STATE variable |
| E2 | wall conductance | `hA` | `watt/kelvin` | W result metric | thermal problem parameter `ambient_conductance` | metric → PARAMETER |
| E3 | body temperature | `T` | `kelvin` | thermal result metric `steady_state_temperature` | P problem variable | metric → STATE variable |
| E4 | scalar diffusivity | `D` | `m**2/s` | P result metric | fluid problem parameter `diffusivity` | metric → PARAMETER |

Four `QuantityDependency` records, one 4-cycle, **one** `TornEndpoint` cutting
E3 and seeding `T` at sweep 1.

**Every exchanged quantity is a scalar.** No field, no array, no bulk
reference crosses any problem boundary. `ScientificDataReference`,
`VariableBulkLinkage` and the fluid's `c:field` variable are untouched by the
coupling.

**No conversion factor may live in coupling code.** Every factor between E1 and
E2 (`ρ c_p`, `d`) is a declared parameter of problem W and is dimension-checked
by `QuantityDependency.unit_exemplar`. A dimensional error must be a refusal,
not a silent rescale.

### 2.1 Dimensional check, performed in advance

```
    [Φ_D] = m²/s                                   (D · ∂c/∂n · dl, c dimensionless)
    [ρ c_p] = J/(m³·K)
    [d] = m
    [ρ c_p · Φ_D · d] = J/(m³K) · m²/s · m = J/(s·K) = W/K   ✓
    [Q/hA] = W / (W/K) = K                                    ✓
    [D_ref (T/T_ref)^1.75] = m²/s                             ✓
```

---

## 3. Fluid → Thermal: the reduction, and the sign/unit convention actually shipped

`Φ_D` is the **boundary-integrated outward diffusive flux** of `c` over all
four sides, per unit depth, positive outward.

### 3.1 The exact value

`∂c*/∂n` on `y = 0` is `−(π/L) sin(πx/L)` (inward-increasing), so the outward
diffusive efflux density `−D ∇c*·n` is `+D (π/L) sin(πx/L)`, and its integral
over a side is `2D`. Four sides:

```
    Φ_D(exact) = 8 D          [m²/s], independent of ω, exactly linear in D
```

### 3.2 The discrete value — computed from the solved field, never from 8D

**This is the attack surface and it is closed by construction.** `Φ_D` is
computed by summing, over exactly the boundary faces `assemble()` itself
recorded while building the linear system, the outward diffusive flux the
shipped stencil represents:

```
    Φ_D(discrete) = Σ_boundary faces  D · (c_cell − c_ghost)
```

where `c_cell` is the **solved** value in the boundary cell and `c_ghost` is the
**same ghost value the matrix assembly moved to the right-hand side**. Both are
recorded by `assemble()` and carried on `PreparedTransport2DSystem`; the metric
re-derives neither. Consequently a change to the solved field changes `Φ_D`,
and the analytic expression `8D` appears nowhere on the computation path.

### 3.3 The shipped convention differs from the preparation's formula — deliberately

`docs/fluid-thermal-preparation.md` §FT0/P2 computed `Φ_D = 2 D Σ c_edge`, i.e.
a one-sided gradient `(c_wall − c_cell)/(dx/2)` with `c_wall = 0`. That is what
the problem *record*'s `BoundaryCondition(value=0)` states, but it is **not what
`assemble()` implements**: the shipped stencil places a ghost cell one full `dx`
from the boundary cell centre and gives it `c*(ghost centre)`, which is not
`−c_cell`. Measured, at the same grids:

| D | n | prep formula, `Φ/D` | shipped ghost convention, `Φ/D` | exact |
|---|---|---|---|---|
| 0.01 | 32 | 4.6384 (−42.0 %) | 6.3192 (−21.0 %) | 8 |
| 0.01 | 64 | 6.0837 (−24.0 %) | 7.0419 (−12.0 %) | 8 |
| 0.50 | 32 | 7.9224 (−0.97 %) | 7.9612 (−0.49 %) | 8 |

The shipped convention is adopted, and the divergence from the preparation is
preregistered here rather than discovered later. Rationale: it is the flux the
assembled operator actually conserves; it is exactly the boundary data the
linear system was built from; and it is uniformly twice as accurate. **The sign
convention is unchanged: positive means efflux.**

### 3.4 The orientation record

`BoundaryOrientation(boundary_name=<side>, reference="outward_normal",
sign=POSITIVE)` is declared for all four sides and **checked against the solved
field** by a validation check. The preparation measured (P5) that
`classify_sign` accepts the diffusive normal gradient on every side and refuses
the advective normal velocity on every side; this milestone transports only the
former, and does not transport the latter.

---

## 4. Thermal → Fluid, and the scale restoration

```
    P:  D(T)   = D_ref (T / T_ref)^1.75          D_ref = 0.01 m²/s at T_ref = 300 K
    W:  hA(Φ_D) = (ρ c_p) · Φ_D · d              ρ c_p = 1.2e3 J/(m³K), d = 1.0e-3 m
```

The `1.75` exponent is the Fuller-correlation binary-gas temperature scaling. It
is a declared exponent of model P with a declared validity range, not a tuned
constant. `ρ c_p` and `d` are declared parameters of model W. **W is the only
place an absolute thermodynamic scale enters the composition**, and the fluid
domain's refusal to carry one is preserved.

---

## 5. The closed-form coupled reference — MANDATORY, and independent

### 5.1 Derivation

Substituting the exact `Φ_D = 8D`, the coupled fixed point `T*` satisfies

```
    T*  =  T_amb  +  Q / ( ρ c_p · d · 8 · D_ref · (T*/T_ref)^n )      n = 1.75
```

With `T_amb = T_ref = 300 K` and `θ = T*/T_ref` this reduces to the closed
algebraic identity

```
    θ^(n+1) − θ^n  =  Q / (ρ c_p · d · 8 · D_ref · T_ref)              (★)
```

so the reference has an exact scalar identity to check *itself* against,
independent of how the root is found.

### 5.2 Independence — the falsifier's attack, closed in advance

The reference is implemented in a module that

* imports **no** part of the numerical path — not the fluid solver, not the
  thermal solver, not the two property evaluators, not `run_fixed_point`;
* takes every physical constant as an explicit argument, so it shares no
  module-level state with the models;
* finds the root by **bisection on the scalar residual**, a different method
  from the Picard sweep the coupled loop performs;
* is checked against identity (★) to `1e-12`.

A test asserts the import restriction by parsing the module, in the same voice
as `fluids/transport2d/reference.py`'s existing "must not be reachable from the
solver" discipline.

### 5.3 Predicted values

| Q [W] | `T*` closed form [K] | Picard gain `−n(T*−T_amb)/T*` |
|---|---|---|
| 6.0 | **348.163813** | **−0.2421** |
| 40.0 | **481.835346** | **−0.6604** |

---

## 6. Preregistered numerical criteria

Let `T_num(Q, n)` be the coupled fixed point the executed loop reports.

* **PC1 — the loop composes what the records say.** At convergence the coupled
  residual `| T_num − (T_amb + Q/(ρ c_p d Φ̂_D(D(T_num)))) |` must be
  `≤ 1e-3 K`, where `Φ̂_D` is the *discrete* efflux at the same grid. This is
  the composition claim, and it is separate from accuracy.
* **PC2 — agreement with the independent closed form, and its refinement.**
  For `Q = 6.0 W`:
  * `|T_num − T*|` ≤ **20 K** at `n = 16`, ≤ **11 K** at `n = 32`,
    ≤ **6 K** at `n = 64`;
  * strictly decreasing in `n` over `{16, 32, 64}`;
  * consecutive-grid error ratio in **[1.6, 2.4]** (first order, the fluid
    participant's own order).
* **PC3 — the transported reduction against `8D`.** At the coupled operating
  point, `|Φ̂_D/(8D) − 1|` ≤ **0.30** at `n = 32` and ≤ **0.18** at `n = 64`,
  with consecutive-grid ratio in **[1.6, 2.4]**.
* **PC4 — the coupling error is inherited, not created.** The coupled
  temperature error and the fluid flux error must be related by the linearized
  coupled map to within 25 %:
  `T_num − T* ≈ −(T*−T_amb)·ε/(1−g)` with `ε = Φ̂_D/(8D) − 1` and `g` the
  Picard gain. This is what makes "the coupling transported the participant's
  discretization error" a measurement rather than a remark.

### 6.1 Convergence criterion and budget

`FixedPointCouplingPlan(absolute_tolerance = Quantity(1e-4, "kelvin"),
max_iterations = 40)`. The comparison unit is `kelvin` — a ratio scale, as the
plan requires.

---

## 7. Predicted outcomes per case

| Case | Q [W] | n | Predicted outcome | Predicted `T_num` [K] | Predicted sweeps |
|---|---|---|---|---|---|
| **A** nominal convergent | 6.0 | 32 | `CRITERION_MET` | 355.7 ± 1.0 | 13 ± 4 |
| **A′** refinement arm | 6.0 | 16 / 64 | `CRITERION_MET` | 362.0 / 352.1 ± 1.0 | ≤ 25 |
| **B** coupling non-convergence, **both subsolvers valid** | 40.0 | 32 | `ITERATION_LIMIT_REACHED`, last `|ΔT|` in (1e-3, 5e-2) K | ≈ 494 | 40 (budget) |
| **C** scientific-admission failure | 6.0 | 8 | a raised `ScientificValidationError`, **no** coupled result | — | 1 |

**Case B is not a solver failure and must not be reported as one.** Every fluid
solve and every thermal evaluation in it reports success and passes its own
declared validation; what fails is the *coupling criterion*, and the
`|ΔT|` sequence must be shown contracting geometrically at a ratio consistent
with `|gain| ≈ 0.66`.

**No relaxation factor, damping, acceleration or criterion change may be
introduced to make case B converge.** `docs/electrothermal-vertical-prereg.md`
§12.10 already makes that a fail condition and it is re-adopted verbatim here.
The undamped behaviour is to be measured and reported.

---

## 8. Admission requirements — enforced in both directions

* The fluid result must satisfy **every** requirement its own problem declares
  (`dimensional_consistency`, `field_finite`,
  `sparse_dense_assembly_agreement`, `admissibility_bound`, and the new
  `wall_efflux_orientation`) before `Φ_D` may be read. The read goes through a
  guarded reader that calls `ValidationReport.require_admission`; a failure
  **raises** and the exception propagates out of the coupling loop.
* The thermal result must satisfy its own declared requirement
  (`lumped_balance_residual`) before `T` may be read, by the same mechanism.
* **FAIL → deterministic refusal.** There is no path on which a failed
  admission is logged, defaulted, retried or skipped and the loop continues. A
  test catches the raised exception; a test also proves the unguarded read
  would have consumed the inadmissible value, so the guard is shown to be
  load-bearing.
* Case C's failure is **real, not synthetic**: at `n = 8` this benchmark's own
  `admissibility_bound` fails (`c ∉ [0,1]`, violation 6.2e-3 at the coupled
  `D`, peak cell Péclet 6.8).

---

## 9. Architecture-change ceiling

**Hard ceiling: zero files changed under `src/engcore/scientific/`.** Asserted
by a test that diffs the tree.

| Path | Permitted |
|---|---|
| `src/engcore/scientific/**` | **no change of any kind** |
| `src/engcore/systems/electrothermal/**` | **no change** — editing it fails the promotion test by definition |
| `src/engcore/domains/thermal/**` | **no change** (byte- and set-pinned) |
| `src/engcore/domains/fluids/transport2d/**` | additive only: one metric, its variable, its model output, its orientation record, its validation check, one guarded reader |
| `src/engcore/domains/thermal_lumped.py` | **no further change** beyond the already-committed defect repair |
| `src/engcore/systems/fluidthermal/**` | new package, this milestone's own |

No new universal record, no new schema string, no schema version bump, no new
enum member in core, no coupling framework, no scheduler, no participant
registry, no transfer operator, no `ScientificField`, no mesh or topology
contract, no temporal contract.

---

## 10. Fail conditions — this milestone is reported FAILED if any holds

1. Closing the loop requires editing `FixedPointCouplingPlan`, `TornEndpoint`,
   `CoupledRun`, `run_fixed_point`, or anything under
   `src/engcore/scientific/`.
2. A relaxation factor, damping term, acceleration, or a loosened convergence
   criterion is introduced to make case B converge.
3. `Φ_D` is computed from `8D`, from `c*`, or from any expression that does not
   read the solved discrete field.
4. `c:centre`, `c:max` or `c:min` is used as a coupling signal.
5. A `QuantityDependency` endpoint is a field.
6. The closed-form coupled reference shares implementation code with the
   numerical solver.
7. An admission failure is swallowed, defaulted or retried instead of raising.
8. Any preregistered criterion in §6 is missed and the criterion is edited
   rather than the outcome reported.
9. The FULL suite is not `0 failed, 0 errors`, or an existing test is weakened,
   skipped or xfailed to make it so.

---

## 11. Promotion criteria for the coupling abstractions

`FixedPointCouplingPlan` / `TornEndpoint` / `CoupledRun` / `run_fixed_point` are
promotion **candidates** only if **all** of the following hold after execution:

* **PR1** — this second consumer executes against them **unedited** (measured
  by `git diff` on `src/engcore/systems/electrothermal/coupled.py`).
* **PR2** — no core branch, string parse, provider leak or domain name is
  introduced into the loop to make the second consumer fit.
* **PR3** — the second consumer is *materially different* from the first on at
  least three axes: participant kind (PDE vs lumped/algebraic), cycle length
  (4 vs 3), and the presence of a boundary-integral reduction as the
  transported quantity.
* **PR4** — the residue that a promotion would close is **named and measured**,
  not asserted. Specifically: how much of the second pack is a genuine
  duplicate of the first, and what a records-only reader still cannot recover.

Satisfying PR1–PR4 makes them candidates. **It does not promote them.** The
decision is taken separately by `architecture-decision-reviewer` on the
evidence, among: (A) keep pack-local, (B) promote a minimal generic coupling
plan, (C) promote dependency/exchange semantics only, (D) a generic
multiphysics framework. Two packs running similar Python loops is explicitly
**not** sufficient evidence for any of (B), (C) or (D).

---

## 12. Negative results this milestone must produce

* **N1 — `c:centre` is unsuitable, proven not asserted.** A regression test
  must show that the exact manufactured solution's centre value is `1.0` for
  every admissible `D`, that the *computed* `c:centre` nevertheless moves by
  ≈ 0.16 over a 50× change in `D`, and therefore that 100 % of that apparent
  sensitivity is discretization error. The test must be phrased so that a
  future author who wires `c:centre` into a coupling breaks it.
* **N2 — the `QuantityDependency` field-endpoint leak.** A test must record
  that a dependency naming the fluid's `c:field` variable **checks clean**
  today, and that this milestone therefore cannot distinguish a supported
  scalar endpoint from an unsupported field one by contract alone. The
  milestone transports no field and **must not fix the leak** — patching core
  on one consumer's evidence is out of scope, and `ScientificField` is
  explicitly not to be created. If the milestone's own pack can refuse a field
  endpoint locally, that refusal is a pack-local guard and must be labelled as
  one.
* **N3 — dimensional refusal.** A `watt`-valued edge into
  `ambient_conductance`, and a `kelvin`-valued edge into `diffusivity`, must
  each be refused by `QuantityDependency`/`FixedPointCouplingPlan` before any
  solve runs.
* **N4 — records-only invisibility.** `unresolved_inputs` on the fluid problem
  must be shown to report **nothing**, so a records-only reader cannot see that
  `diffusivity` has a supplier. This is the preparation's finding A1, exhibited
  on a real composition for the first time.

---

## 13. Provenance and reconstruction

* The coupled record must permit reconstruction of: each participant's model
  id/version, realization, solver identity and typed inputs; the four exchange
  identities with their units; the sweep count; and the coupling outcome.
* No provider-specific string (`scipy`, `numpy`, a backend name) may appear as
  a *scientific* fact; backends stay on `SolverIdentity.backend`.
* **Fresh-process reconstruction** is tested by launching a genuinely separate
  interpreter, handing it only JSON, and requiring it to rebuild the plan, the
  four dependencies, the torn endpoint and every participant problem, and to
  recompute the execution order — with no Python object from the parent
  process. Whatever it *cannot* rebuild is recorded as a measured gap, at the
  stated evidence level. **No universal `ExecutableScientificSpecification` is
  to be built.**

---

## 14. Performance to be recorded

Per fluid solve, per thermal evaluation, per property evaluation, per coupling
sweep, total loop wall time, and sweep count — for every case in §7, at every
grid.

---

## 15. Out of scope — not started under any circumstance

CasADi/SUNDIALS or any second provider; a temporal contract; field-valued
coupling; `ScientificField`, mesh, topology or support contracts; a generic
multiphysics framework; a coupling scheduler, participant registry or transfer
operator; any change to the frozen thermal tree.

---

## 16. Decision status

`PROPOSED` on completion. Not `DESIGN-FROZEN`. A first execution of a second
coupled pair is evidence for a decision, not the decision.
