# FLUID ↔ THERMAL COMPOSITION PREPARATION — Track B

**Kind:** preparation / reconnaissance. **No coupling was implemented, no
production module was touched.** This document compares three candidate
Fluid↔Thermal couplings, recommends exactly one as the first composition
proof, classifies the quantities it would exchange, maps what the current
composition contracts can and cannot express for it, answers the temporal
question independently, and lists exact blockers. It freezes nothing and is
not a preregistration.

**Branch:** `fluid-thermal-preparation`, worktree `crafty-ft-prep`, based on
`origin/cloud/crafty-post-field-support` @ `6caa1139`.
**Constraint honored:** the only new files are `docs/fluid-thermal-preparation.md`
and `experiments/fluid_thermal_prep/coupling_probe.py`. Nothing under
`src/` changed — asserted in "What was and was not touched" below.

Its two direct predecessors are `docs/fluid-pde-preparation.md` §B9 (which
classified the exchangeable quantities *before* either the Fluid domain or
`ScientificProblem.data_references` existed) and
`docs/min-foundation-electrothermal-evidence.md` +
`docs/electrothermal-vertical-evidence.md` (the only coupling this platform
has actually executed). This document's job is to re-ask §B9's question
against the code that now exists, and to answer it with measurements rather
than with a reading of the source.

---

## FT0 — What was measured, before anything was argued

`experiments/fluid_thermal_prep/coupling_probe.py` is a standalone probe. It
imports the shipped `fluids/transport2d` domain read-only, adds no test, and
touches no core module. Six measurements, all reproduced below verbatim from
its output.

### P1 — the shipped scalar metrics are sensitive to `D`, and the sensitivity is 100% numerical

```
P1 — shipped scalar metrics vs D (n=32); exact c:centre = 1.000 for EVERY D
  D [m2/s]       c:centre          c:max          c:min   err vs exact  wall [s]
      0.01    0.832861663    0.832861663    0.001621880      -0.167138    0.0338
      0.02    0.906062281    0.906062281    0.001678772      -0.093938    0.0337
      0.05    0.958597646    0.958597646    0.001953285      -0.041402    0.0310
       0.1    0.977998130    0.977998130    0.002152811      -0.022002    0.0293
       0.5    0.994260010    0.994260010    0.002358785      -0.005740    0.0290
  observed spread of c:centre over a 50x change in D: 0.161398
  physical spread of the EXACT solution over the same change: 0.0
  => 100% of the observed sensitivity is discretization error.
```

**This is the single most consequential finding of this track.** The Fluid
domain's manufactured solution is `c*(x,y) = sin(πx/L) sin(πy/L)` with the
source term `s = u·∇c* − D∇²c*` derived analytically from it. The exact
solution is therefore **independent of `D` and of `ω`**: `c:centre` is exactly
1 for every admissible input. The 16% spread the solver reports across a 50×
change in `D` is entirely the first-order upwind scheme's cell-Péclet-driven
error.

A coupling loop closed on `c:centre` would therefore look completely
healthy — it is smooth, monotone, strongly input-sensitive, and it would
converge — while transporting **nothing but discretization error**. That is
the most dangerous possible failure mode for a first composition proof: a
physically inert loop that is numerically lively. It rules out the
zero-domain-change variant of the cheapest candidate, and it is not something
a reading of the source would have shown.

### P2 — one scalar reduction of the same field *is* physically load-bearing

```
P2 — boundary-integrated diffusive efflux Phi_D; exact = 8 D
  D [m2/s]     Phi_D [m2/s]      Phi_D/D    exact    rel err   (n=32)
      0.01      0.046383900     4.638390    8.000    -0.4202
      0.02      0.121616531     6.080827    8.000    -0.2399
      0.05      0.358050118     7.161002    8.000    -0.1049
       0.1      0.757210462     7.572105    8.000    -0.0535
       0.5      3.961184718     7.922369    8.000    -0.0097

  grid convergence of Phi_D/D at D = 0.5 (Pe_cell small):
     n      Phi_D/D      rel err   wall [s]
    16     7.870457      -0.0162     0.0087
    32     7.922369      -0.0097     0.0264
    64     7.957904      -0.0053     0.5906
   128     7.978123      -0.0027     8.2786
```

The boundary-integrated diffusive efflux `Φ_D = ∮ D |∇c·n| dl` has the exact
value `8 D` (2·D per side, per unit depth, from `∂c*/∂n = (π/L)sin(π·/L)`
integrated over a side). Unlike `c:centre`, its **exact** value carries genuine,
non-degenerate dependence on the Fluid problem's own physical input, and its
discrete value converges to that exact value at approximately first order.
It is Fick's law at a wall — real physics, with an independent closed form to
check the transported number against.

### P3/P4 — the recommended loop contracts, and the coupling amplifies the fluid's error

```
P3 — undamped Gauss-Seidel loop, Q = 6.0 W, n = 32
 iter        T [K]     D [m2/s]       Phi_D    hA [W/K]    |dT| [K]
    1   407.796024         0.01    0.046384    0.055661   1.078e+02
    ...
   18   365.216655    0.0141092    0.076668    0.092001   7.699e-05
  CONVERGED in 18 sweeps, 0.47 s
  Picard gain at the fixed point = -0.3125 (|gain| < 1 required)
  coupled T (discrete fluid leg) = 365.216655 K
  coupled T (exact Phi_D = 8D)   = 348.163813 K
  coupling-level error inherited from the fluid discretization = +17.052842 K
      (+35.41% of the temperature rise)

P3 — undamped Gauss-Seidel loop, Q = 40.0 W, n = 32
    ...
   40   506.214386     0.025151    0.161644    0.193973   1.957e+00
  ITERATION LIMIT REACHED (40); last |dT| = 1.957e+00 K, Picard gain ~ -0.7129
```

Three separable results:

* The loop **converges** at a weak-feedback operating point (18 sweeps,
  0.47 s wall at `n=32`), so the proof is feasible and cheap to run.
* At a strong-feedback operating point (`|gain| ≈ 0.71`) an **undamped**
  Gauss–Seidel sweep is oscillatory and does not converge in 40 sweeps.
  `FixedPointCouplingPlan` carries **no relaxation factor** (deliberately;
  `coupled.py` module docstring: "no relaxation factor, no damping, no
  acceleration"), and `docs/electrothermal-vertical-prereg.md` §12.10 makes
  silently tuning one a *fail condition*. The recommended proof must
  therefore report the gain and accept `ITERATION_LIMIT_REACHED` as an honest
  outcome, not tune its way out of it.
* The Fluid participant's −0.42 relative flux error at `D≈0.014, n=32`
  arrives in the **coupled** answer as +17 K, i.e. **+35% of the whole
  temperature rise**. A coupling proof that does not report the participant's
  own discretization error alongside the coupled result is not reporting the
  coupled uncertainty at all. No contract in this repository relates a
  participant's `ValidationReport` to the coupled outcome, and that is a
  finding, not a defect to hide.

### P5 — which wall-normal quantity `BoundaryOrientation` can classify

```
P5 — BoundaryOrientation classifiability, per wall-normal quantity
  side-south    advective u.n: REFUSED (mixed)   diffusive dc/dn: positive
  side-north    advective u.n: REFUSED (mixed)   diffusive dc/dn: positive
  side-west     advective u.n: REFUSED (mixed)   diffusive dc/dn: positive
  side-east     advective u.n: REFUSED (mixed)   diffusive dc/dn: positive
```

`classify_sign` (`src/engcore/scientific/ir/orientation.py`) **refuses** the
advective normal velocity on every side — the rotational field makes every
side half-inflow, half-outflow, exactly as `docs/real-fluid-pde-evidence.md`
§5 measured. It **accepts** the diffusive normal gradient on every side,
because `c ≥ 0` inside and `c = 0` on the wall makes `∂c/∂n` single-signed.
So the contract that exists can honestly describe the sign convention of the
quantity the recommended coupling transports, and cannot describe the one
the rejected candidates would transport.

### P6 — three executed checks against the composition contracts

```
P6 — composition-contract probes (nothing modified)
  (a) target = fluid PARAMETER 'diffusivity': check_against -> ()
  (b) unresolved_inputs([fluid_problem]) -> ()
  (c) source = fluid FIELD variable 'c:field': check_against -> ()
      (an empty tuple here means the field endpoint CHECKS CLEAN through problem.variables)
```

* **(a)** A `ScientificParameter` is a legal `QuantityDependency` endpoint.
  `_declared_unit` (`composition/dependency.py:298`) resolves
  `result.values → problem.variables → problem.parameters`, so
  `diffusivity` — a parameter, not a variable — checks clean as a target.
* **(b)** …but `unresolved_inputs` reports only `CONTROL` variables and
  `STATE` variables no declared condition determines. The Fluid problem
  declares four `OBSERVABLE` variables and three parameters, so it reports
  **nothing**: a records-only reader cannot see that this problem has a
  coupled input at all. The module already states this limitation in prose;
  the recommended proof would be the first consumer to *exhibit* it.
* **(c)** **New finding, and the sharpest one in this section.**
  `QuantityDependency`'s module docstring (line 94) states that
  `ScientificResult.data_references` is "deliberately **not** consulted"
  precisely so that a field endpoint returns an honest `MISSING` rather than
  "a clean check that implies a transfer semantics no contract provides."
  That protection **does not hold** for `fluids/transport2d`. The field is
  declared as a `ScientificVariable` named `c:field` (`problem.py:409`,
  `FIELD_VARIABLE`) — it has to be, so that `VariableBulkLinkage` can bind
  the bulk array to it — and `_declared_unit` finds it in
  `problem.variables`. A `QuantityDependency` naming the whole 2D field as
  its source therefore **checks clean today**, transports a
  `dimensionless` unit, and implies exactly the field-transfer semantics the
  record was written to refuse. The guard was placed on the wrong door.

---

## FT1 — The three candidate couplings, scored

Scoring: **5 = best**, **1 = worst**, per criterion as defined by the mission.
"New architectural pressure" is scored *relative to what `ET-VERTICAL`
already proved*, and higher is not automatically better — a first proof that
adds pressure the platform has no evidence to resolve is worse, not better.

| Criterion | **1. Scalar-reduction coupling** | **2. Same-grid field coupling** | **3. Conjugate-heat-transfer-like coupling** |
|---|---|---|---|
| **Scientific legitimacy** | **4** — real physics *if and only if* the transported scalar is `Φ_D` and not `c:centre` (P1/P2). Wall diffusive flux and a temperature-dependent diffusivity `D(T)` are both textbook. Honest ceiling: with the manufactured source term pinning `c`, the exact `Φ_D = 8D` is analytically simple, so the Fluid leg is *verifiable* rather than *rich* | **4** — a co-located fluid/solid temperature field exchange is real physics, but there is no second 2D domain to exchange with (see below), so the "second domain" would have to be invented for the proof — and a domain invented to be coupled is a prop | **5** — CHT is the canonical multiphysics problem; interface continuity of `T` and of `q·n` is exactly what industrial codes solve |
| **Composition-testing value** | **4** — executes the preregistered promotion test for the ET records (`docs/electrothermal-vertical-prereg.md` §16: a second, materially different coupled consumer written against them **without editing them**); first coupling whose participant emits a *bulk field*; first to exhibit the parameter-endpoint blind spot (P6b) and the field-endpoint leak (P6c) on real records | **5** — maximal: it would force the field-transfer declaration the core deliberately deferred | **5** — maximal, plus interface sub-region and boundary-field semantics |
| **Implementation cost** | **4** — one new metric on a non-frozen domain, one small property module, one plan; ~0.5 s per converged loop at `n=32` | **2** — needs a second 2D domain that does not exist, a field-valued *input* channel on a solver (none exists), and a new core contract | **1** — needs all of the above plus interface topology, boundary sub-regions, and spatially varying boundary data |
| **Forces cross-mesh / cross-discretization transfer?** | **5 — no.** Only scalars cross the boundary between problems; each participant keeps its own discretization and never sees the other's | **4 — no cross-*mesh*, but yes cross-*contract*.** Same grid makes the transfer operator the identity, which removes interpolation but **not** the requirement to declare that a field was transported at all. The contract that would name it is the same one either way | **1 — yes.** A 1D or lumped solid against a 2D fluid boundary is different support *and* different discretization by construction. Explicitly premature |
| **Runtime** | **5** — measured: 0.03 s per fluid solve at `n=32`, 18 sweeps, 0.47 s total (P3). 8.3 s per solve at `n=128` if a converged flux is wanted | **3** — two 2D solves per sweep | **2** — two 2D solves plus interface assembly per sweep |
| **New architectural pressure vs. what ET already proved** | **low, and deliberately so** — same record shapes, new participant kind. Adds three *measured* boundary findings without demanding a new contract to fix them | **high** — demands a field-transfer contract on one consumer's evidence | **very high** — demands field transfer, boundary-field values, interface topology, and orientation-per-sub-region, all at once |
| **Blocked by a byte-freeze?** | **no** — `fluids/transport2d` is not pinned; `thermal_lumped.py` sits outside the frozen tree | **yes, partly** — the only other real thermal PDE domain, `src/engcore/domains/thermal/`, is SHA-256 pinned *and* set-equality pinned (`tests/test_thermal_t1_fidelity_inference.py::test_every_thermal_source_file_is_pinned`), so no file may be added to or changed in it | **yes** — same freeze, plus it is 1D and cannot present a 2D interface |
| **Total (of 30, excluding the freeze row)** | **26** | **20** | **15** |

### The freeze row deserves its own sentence

`src/engcore/domains/thermal/` — the only real thermal *PDE* domain in the
repository — is byte-pinned by three frozen experiments, and
`test_every_thermal_source_file_is_pinned` asserts **set equality** over its
`*.py` files, so a new file cannot be added to that package either. Any
candidate whose thermal participant is a conduction PDE is therefore blocked
before any contract question is reached. This alone removes candidates 2 and
3 from "first proof" contention on a hard, mechanical ground, independent of
every score above.

---

## FT2 — Recommendation

> **Recommended first coupling proof: Candidate 1 — a two-way
> scalar-reduction coupling between `fluids/transport2d` and
> `thermal_lumped`, closed on the boundary-integrated diffusive efflux
> `Φ_D` (Fluid → Thermal) and on a temperature-dependent diffusivity `D(T)`
> (Thermal → Fluid).**
>
> Explicitly **not** closed on `c:centre`, `c:max` or `c:min`.

### Why it beat the alternatives

1. **It is the only candidate that is not blocked before it starts.** The
   thermal PDE tree is byte- and set-pinned. Candidates 2 and 3 need a
   thermal field participant; there is exactly one, and it cannot be
   touched or extended.
2. **It is the only candidate that does not force the deferred
   field-transfer contract.** Candidate 2's "same grid" removes
   *interpolation*, which is a real saving, but it does not remove the need
   for a record that says a field crossed from one problem to another —
   and that record would be minted on one consumer's evidence, which is
   exactly what `MIN-FOUNDATION-ET` §6 and `DATA-BOUNDARY0` refuse to do.
3. **It executes a preregistered test rather than inventing one.**
   `docs/electrothermal-vertical-prereg.md` §16 already names the condition
   under which `FixedPointCouplingPlan` / `CoupledRun` become promotion
   candidates: a second, materially different coupled consumer written
   against them **without editing them**. A Fluid↔Thermal pair is a
   different domain pair. This proof is that test, and its outcome is
   informative in both directions.
4. **Its low new-pressure score is the argument for it, not against it.**
   The mission warns against automatically picking the most complex. The
   three findings this proof would put on the record (P6a/P6b/P6c) are
   contract findings that *cost nothing to obtain* under candidate 1 and
   would be drowned under candidates 2 and 3 by the larger contracts those
   require. Measuring a boundary is cheaper than moving it, and this
   platform's discipline is to measure first.
5. **It has an independent closed form for the coupled answer.** Because
   `Φ_D = 8D` exactly, the coupled fixed point can be computed analytically
   and the executed loop checked against it (P3/P4 does exactly this). No
   prior coupling proof in this repository has had a closed form for the
   *coupled* result, only for the participants.

### The honest weakness of the recommendation, stated up front

The Fluid participant is a manufactured-solution verification benchmark. Its
exact solution is pinned by an analytically derived source term, so **every**
functional of its exact solution is either independent of `D` or exactly
proportional to `D`. The Fluid leg of this loop is therefore analytically
reducible to one multiplication. That is a genuine limitation on how much
*physics* the coupling exercises — it is not a limitation on how much
*composition* it exercises, which is what this proof is for. The immediate
follow-on that removes it is named in "What is explicitly NOT forced" below:
a source-free configuration with a prescribed non-zero wall value, whose wall
Sherwood/Nusselt number is a genuinely non-trivial function of the Péclet
number. That configuration should not be bundled into the first proof,
because it would confound "does the composition work" with "is the new fluid
configuration correct".

---

## FT3 — Equations and setup sketch for the recommended proof

### Participants

**A. Fluid** — the shipped `fluids/transport2d` domain, unchanged in physics:

```
    div(u c) − D ∇²c = s(x, y)          on [0, L]²
    u(x, y) = ω(−(y − L/2), (x − L/2))  prescribed, divergence-free
    c = c*(x, y) on all four sides,     c* = sin(πx/L) sin(πy/L)
    s = u·∇c* − D∇²c*                   manufactured
```

New reported scalar (the only domain-pack addition on this side):

```
    Φ_D = ∮ D |∇c · n| dl   [m²/s per unit depth]      exact value 8 D
```

`c` is and stays **dimensionless**. Read physically, it is the normalized
excess `θ = (T − T∞)/(T_w − T∞)` of a passive scalar; the domain claims no
absolute scale, and this proof does not make it claim one.

**B. Fluid properties (Thermal → Fluid)** — one new
`ScientificModelDefinition` + `ModelRealizationDefinition`, exactly the shape
of `electrical/material.py`'s `R(T) = R_ref(1 + α(T − T_ref))`:

```
    D(T) = D_ref (T / T_ref)^1.75         Fuller-correlation binary-gas scaling
```

Real physics, and the direct structural analogue of the one property model
this platform has already proved.

**C. Scale restoration (Fluid → Thermal)** — one new model, the piece that
converts a dimensionless-field wall flux into an extensive conductance:

```
    hA = (ρ c_p) · Φ_D · d        [J/(m³K)]·[m²/s]·[m] = [W/K]
```

Dimensionally exact, and it is the *only* place an absolute thermodynamic
scale enters. The Fluid domain's refusal to carry one is preserved: the scale
lives in this model, declared, versioned and checkable, not smuggled into the
fluid's units.

**D. Thermal** — the shipped `thermal_lumped` body, unchanged:

```
    C dT/dt = Q_in − hA (T − T_amb)
```

with the coupled endpoint being its `ambient_conductance` parameter and the
transported result metric being `steady_state_temperature` (or
`final_temperature`; the two differ, and only the enumerated name separates
them — the same "two configurations, one field apart" property `coupled.py`
already documents).

### Dependency graph, and the tear

```
        ┌───────────────── T ──────────────────────────────┐
        │                                                  │
        ▼                                                  │
  [B: D(T)] ──D──▶ [A: fluid] ──Φ_D──▶ [C: hA(Φ_D)] ──hA──▶ [D: thermal]
```

Four `QuantityDependency` records, one cycle, one `TornEndpoint` seeding `T`
at iteration 1 — structurally identical to `ET-VERTICAL`'s
`properties → circuit → bodies` with one extra stage. `execution_order`
computes the sweep; nothing writes it down.

### Convergence discipline

The Picard gain at the fixed point is `−1.75·(T* − T_amb)/T*`. The proof must
**report** it, must run at least one operating point with `|gain| < 1` (P3
measured `−0.31`, converging in 18 sweeps) and at least one with `|gain|`
approaching 1 (P3 measured `−0.71`, not converged in 40 sweeps), and must
report the second as `ITERATION_LIMIT_REACHED` rather than introducing a
relaxation factor. `docs/electrothermal-vertical-prereg.md` §12.10 already
makes tuning one a fail condition.

---

## FT4 — Exchanged-quantity classification

Grounded in the recommended proof and in what the two real domains compute
today. "Support" means the geometric set a quantity lives on: a lumped body,
a 2D cell-centred grid, a boundary curve.

| Exchanged quantity | Scalar or field | Support | Discretization | Steady or transient | Direction | Where it lives today |
|---|---|---|---|---|---|---|
| **Body temperature `T`** (Thermal → property model) | **scalar** | lumped body (no support) | none — the lumped model has no mesh | Thermal is **transient**; the *transported* value is a per-sweep converged scalar (`steady_state_temperature`, or `final_temperature` at a fixed `t₀+Δ`) | **one-way**, closing the cycle | `thermal_lumped.TEMPERATURE` (`STATE`, kelvin) and the two kelvin metrics; already a working `QuantityDependency` endpoint in `ET-VERTICAL` |
| **Diffusivity `D`** (property model → Fluid) | **scalar** | whole fluid domain (uniform coefficient) | none — it is a model coefficient, not a discretized field | Fluid is **steady**; `D` is constant within a sweep | **one-way** | `transport2d` `ScientificParameter` `diffusivity` (`m**2/s`). **Legal endpoint (P6a), invisible to `unresolved_inputs` (P6b)** |
| **Wall diffusive flux `Φ_D`** (Fluid → scale model) | **scalar** — a *reduction of a field over a boundary*, not a field | reduced from the 2D grid onto the boundary curve, then integrated to a point | produced on the fluid's own grid; **no other participant ever sees that grid** | steady | **one-way** | **Does not exist yet.** One new `ModelOutputSpec` + result metric on `transport2d`. Nothing about it is field-shaped once integrated |
| **Convective conductance `hA`** (scale model → Thermal) | **scalar** | lumped body | none | steady within a sweep | **one-way** | `thermal_lumped` `ScientificParameter` `ambient_conductance` (`watt/kelvin`). Same endpoint class as `D`: legal, invisible |
| **Wall temperature `T_w`** (would-be Fluid boundary value) | **scalar** *if uniform*, **field** if not | boundary curve | uniform: none. Non-uniform: the fluid boundary discretization | steady | one-way | **Not used by the recommended proof.** Uniform case is `BoundaryCondition(kind=DIRICHLET, value=Quantity)` and is expressible today. Non-uniform case is a *field on a boundary* and is **not** expressible — see FT5 |
| **Convective coefficient `h(x,y)`** (spatially varying) | **field** | boundary curve | fluid boundary discretization | steady | would be two-way | **Not used.** Same gap as non-uniform `T_w` |
| **Velocity field `u`** (Fluid → any consumer) | **field**, and vector-valued | 2D cell centres / faces | fluid grid | steady | would be one-way | **Not used, and not expressible.** `transport2d` prescribes `u` analytically and never publishes it; `ScientificVariable` is scalar-valued and `ScientificDataReference` carries `count`, explicitly "not a shape" |
| **Full scalar field `c`** (Fluid → any consumer) | **field** | 2D cell centres | fluid grid; row `i·n + j` by a **documented, untyped** convention (`solver.py` module docstring) | steady | would be two-way for CHT | Named by `ScientificDataReference` + `VariableBulkLinkage`; **names clean as a `QuantityDependency` endpoint (P6c) while no transfer semantics exists** |

**Net.** Every quantity the recommended proof exchanges is a **scalar**, on
**no shared support**, with **no shared discretization**, exchanged
**steady-within-a-sweep**, in a **two-way cycle assembled from four one-way
edges**. That is the entire reason it can be built today. The moment any row
below the fourth is admitted, a contract that does not exist is required.

---

## FT5 — Contract capability map

For each contract: what it **can** express for the recommended proof, and
what it **cannot**. Cited to file and field.

### `QuantityDependency` — `src/engcore/scientific/composition/dependency.py`

Fields: `source_problem_id, source_quantity, target_problem_id,
target_quantity, unit_exemplar, name, description`.

**CAN**
* Declare all four edges of the recommended cycle. Endpoint names resolve
  through `_declared_unit` (line 298) across
  `result.values ∪ problem.variables ∪ problem.parameters`.
* Carry a **parameter** endpoint. Measured (P6a): a dependency targeting the
  fluid's `diffusivity` parameter returns `()` from `check_against`. Both
  coupled inputs of the recommended proof (`diffusivity`, `ambient_conductance`)
  are parameters, and both are legal.
* Refuse a dimensional wiring error: `unit_exemplar` is checked by
  `dimensionality`, so `Φ_D` in `m**2/s` cannot be wired into a
  `watt`-valued endpoint. This is what forces the scale-restoration model **C**
  to exist as a declared model rather than as an implicit conversion —
  a contract doing its job.

**CANNOT**
* **Be seen by a records-only reader as an unresolved input.** Measured
  (P6b): `unresolved_inputs([fluid_problem])` returns `()`. The function
  reports only `CONTROL` variables and `STATE` variables no condition
  determines; the fluid problem declares four `OBSERVABLE` variables and
  three parameters. So `externally_imposed` cannot distinguish "this fluid
  problem's diffusivity is supplied by a thermal solve" from "nobody has
  thought about it". The module already states this ("A quantity a domain
  models as a configured `ScientificParameter` carries a value, so it reads
  as resolved even when a composition in fact supplies it"); this proof would
  be the first real second consumer to exhibit it.
* **Honestly refuse a field endpoint.** Measured (P6c): a dependency naming
  `c:field` as its source **checks clean**. The docstring's protection
  (line 94: `ScientificResult.data_references` "deliberately **not**
  consulted") assumed field-valued quantities would only ever be reachable
  through `data_references`. `fluids/transport2d` declares its field as a
  `ScientificVariable` (`FIELD_VARIABLE = "c:field"`, `problem.py:409`)
  because `VariableBulkLinkage` requires a declared variable to bind to — so
  the field is reachable through `problem.variables`, and the guard is
  bypassed. **This is a contract finding the recommended proof would put on
  the record; it is not a blocker for it, because the proof does not use a
  field endpoint.**
* Say anything about *how* a value is transported, when, or in what order —
  by design ("no mapping, no interpolation, no coordinate transform, no
  relaxation factor, no convergence criterion, no schedule").

### `VariableBulkLinkage` — `src/engcore/scientific/results/variable_binding.py`

Fields: `variable_name, reference_name, description`.

**CAN**
* Bind the fluid's solved array to its declared `c:field` variable, on the
  **result** side — already done in production (`transport2d/solver.py:568`).
* Bind an **input-side** array named by `ScientificProblem.data_references`
  to a declared variable: `check_against` resolves `reference_name` against
  `result.data_references` first and `problem.data_references` second, with
  a tested precedence rule. So the *input half* of a field-coupled problem is
  representable today, which it was not before `MIN-FIELD-SUPPORT-FOUNDATION`.
* Check dimensional agreement between the variable and the reference.

**CANNOT**
* **Relate two problems.** It carries no `problem_id` and no `result_id`
  (stated explicitly in its docstring, "What this record does not decide").
  A linkage on the fluid's result and a linkage on a thermal problem's input
  are two independent facts; nothing joins them.
* Express shape, mesh, stride, axis order, topology, coordinate frame or
  support — all explicitly disclaimed.
* Therefore: **it cannot express a field transfer**, only two independent
  bindings. Note the near-miss worth recording: because
  `ScientificDataReference` is *content-addressed*, a consumer could place
  the fluid's `c:field` reference verbatim into a downstream problem's
  `data_references`, and the identical digest would **prove** the bytes are
  the same array — no interpolation, no transfer operator, byte-exact. What
  is missing is not the mechanism but the **declaration**: nothing states
  that the downstream problem's input came from the upstream result, and
  inferring it from an equal digest is precisely the meaning-in-key failure
  mode the platform refuses. The recommended proof needs none of this.

### `ScientificDataReference` — `src/engcore/scientific/results/data_reference.py`

Fields: `name, unit, count, dtype, digest, digest_algorithm`.

**CAN**
* Name the fluid's bulk field with content identity, integrity and
  relocation stability, on either the result or (now) the problem side.

**CANNOT**
* Carry "no mesh, topology, coordinate frame, tensor rank, conformity or
  field support" — its own words. `count` is "a count of values and is *not*
  a shape".
* Therefore it cannot say that two arrays live on the same support, which is
  the *first* thing candidate 2 would need to state and check. Candidate 2's
  "same grid" claim is, today, unverifiable from records: two 1024-value
  `dimensionless` references are indistinguishable from two arrays on
  unrelated 32×32 grids.
* It also cannot be reached by the recommended proof's transported values at
  all — `Φ_D` is a scalar metric, and the fluid's array stays where it is.

### `BoundaryOrientation` — `src/engcore/scientific/ir/orientation.py`

Fields: `boundary_name, reference, sign: OrientationSign, description`.

**CAN**
* State the sign convention of the recommended proof's transported wall
  quantity. Measured (P5): the diffusive normal gradient is single-signed on
  all four sides, so `classify_sign` classifies it and
  `BoundaryOrientation.check_against(samples)` can verify a declared sign
  against the real solved field.
* Make "positive `Φ_D` means efflux, not influx" a checkable record rather
  than a comment — which matters, because a sign error in a coupled loop
  changes a cooling problem into a heating one and both converge.

**CANNOT**
* Describe the advective normal velocity on any side of this benchmark.
  Measured (P5): `classify_sign` **refuses** all four, as designed. The
  recommended proof therefore must not transport an advective wall flux —
  and does not.
* Attach to a sub-region, carry a spatial function, or say *where* on the
  boundary the sign flips. Refusal is the contract's documented, correct
  behaviour, not a gap this proof needs closed.

### `ScientificProblem.data_references` — `src/engcore/scientific/ir/problem.py:165`

**CAN**
* Name input-side bulk data on a problem statement (schema `/2`, with `/1`
  payloads loading as `()` by version), unique-name-checked alongside
  objectives, constraints and boundary conditions.
* Be bound to a declared variable by `VariableBulkLinkage` (above), with a
  documented precedence rule over a scalar `InitialCondition` /
  `BoundaryCondition.value` for the same variable.

**CANNOT — and this is the mission's explicit question, answered**
* **It does not change what `QuantityDependency` can name.**
  `_declared_unit` (`dependency.py:298`) reads
  `values → problem.variables → problem.parameters` and **never** touches
  `problem.data_references`. The new field added an input-side *home* for a
  field; it did not add an input-side *endpoint*. So:
  * A field endpoint still cannot be named through `data_references` — as
    intended.
  * But a field endpoint **can** be named through `problem.variables`
    whenever a domain declares its field as a variable, which
    `transport2d` does (P6c). The net effect of the last milestone is that
    field endpoints are now *half*-expressible in a way nothing checks:
    nameable, dimension-checkable, and semantically empty.
* It relates nothing to a `BoundaryCondition`. A non-uniform boundary field
  can be named as a problem-level `data_reference` bound to a *variable*,
  but there is no record binding a reference to a **named boundary
  condition** or region. `BoundaryCondition.value` is a single
  `Quantity | None` and `coefficients` is a `Mapping[str, Quantity]` —
  `HOSTILE-CORE-STRESS` §C already rejected `coefficients` as the home for
  spatial data. This is the exact wall candidate 3 hits.

### Bonus: `FixedPointCouplingPlan` — `src/engcore/systems/electrothermal/coupled.py`

Not universal core, but it is what the recommended proof would reuse.

**CAN** carry the dependency set, the torn endpoints with dimension-checked
seeds, a ratio-scale absolute tolerance and an iteration budget; refuse a
seed that overrides a declared condition; compute the sweep order; and run
the loop with no knowledge of which sciences are behind the executors.

**CANNOT** carry a relaxation factor, a divergence test, per-edge
tolerances, or any relation between a participant's own
`ValidationReport`/`Uncertainty` and the coupled outcome. P3/P4 measured why
each of those absences bites for this pairing. **None of them blocks the
proof**; all of them are things the proof would report.

---

## FT6 — Is temporal semantics a prerequisite?

**Answer: no. It is orthogonal to the recommended proof, and it would be a
prerequisite only for the two candidates already rejected on other grounds.**
This assessment is made independently of Track A, whose results are not
visible from here and are not depended on.

The argument, from the two real domains:

* The **Fluid** participant is **steady by construction**. Its model's
  assumption tuple states "steady state; no time dependence"
  (`transport2d/problem.py`), its problem declares **no**
  `initial_conditions`, and its solve is a single direct factorization
  (`iterations=1`, "no outer iteration"). There is no time level to
  synchronize on the fluid side because there is no time.
* The **Thermal** participant is transient, but the coupled quantity is a
  *converged* scalar: `steady_state_temperature` is the `t → ∞` limit, and
  `final_temperature` is the value at one fixed interval end. `ET-VERTICAL`
  already proved that the interval is *not* advanced between coupling
  iterations — "the thermal problem's initial condition is the same in every
  iteration; the iterate is a **coupling** iterate, not a time level" — and
  `FixedPointCouplingPlan.check_against` mechanically refuses to seed an
  endpoint a declared condition already determines, precisely so a coupling
  iterate cannot masquerade as a time step.
* Therefore the recommended proof is a **steady ↔ steady-limit** coupling.
  No participant needs to know another's time level, no time-level tag needs
  to appear on a transported quantity, and no time-synchronization semantics
  is exercised or required.

**Where temporal semantics *would* become a prerequisite**, stated so the
cross-track decision has both halves:

* A **transient conjugate** proof (candidate 3 in its natural form) needs it
  immediately: interface heat flux and interface temperature must be
  exchanged *at the same time level*, and the whole question of implicit vs.
  explicit coupling, sub-cycling, and time-step ratio between participants
  becomes load-bearing. `QuantityDependency`'s own docstring names this
  hazard exactly: "For a transient composition the time level of the
  transported quantity is the whole semantic content, so a dimension check
  cannot be the thing that protects it."
* Any coupling that transports `final_temperature` while **also** advancing
  the thermal interval between sweeps needs it, because the coupling iterate
  and the time level would then be the same number wearing two names.
* A field coupling (candidate 2) needs it as soon as either participant is
  transient, for the same reason.

**Cross-track consequence:** if Track A concludes that temporal semantics
needs a new contract, that conclusion does **not** gate this proof, and this
proof should not wait for it. If Track A concludes it does not, that also
does not change this proof. The one thing worth re-checking after Track A
lands is narrower: whether anything it adds makes the
`final_temperature` / `steady_state_temperature` / `temperature` name
ambiguity — three kelvin-valued quantities on one problem, separable only by
name — cheaper to state than it is today. That is a recommendation to
re-check, not a dependency.

---

## FT7 — Exact blockers

### BLOCKED — needs a new contract (and therefore is **not** in the recommended proof)

| # | What | Why it is blocked |
|---|---|---|
| B1 | Transporting the **field** `c` (or any field) between two problems | No record can state that a field was transported. `QuantityDependency` carries no mapping/interpolation/support and — measured (P6c) — cannot even *refuse* the endpoint honestly when the field is a declared variable. `VariableBulkLinkage` carries no problem/result identity and no support. `ScientificDataReference` carries no shape or support |
| B2 | Asserting that two arrays live on the **same support** | `ScientificDataReference.count` is documented as "not a shape". Two 1024-value references on genuinely identical grids and on unrelated grids are byte-indistinguishable as records |
| B3 | A **spatially varying** boundary value or coefficient (`T_w(x)`, `h(x)`, non-uniform `q·n`) | `BoundaryCondition.value` is a single `Quantity \| None`; `coefficients` is `Mapping[str, Quantity]` and was already rejected as a home for spatial data (`HOSTILE-CORE-STRESS` §C). `ScientificProblem.data_references` can name a field but binds only to a **variable**, never to a named boundary condition or region |
| B4 | Any coupling whose thermal participant is a **conduction PDE** | `src/engcore/domains/thermal/` is SHA-256 pinned **and** set-equality pinned; the tree can be neither modified nor extended. This is mechanical, not architectural |
| B5 | Orientation of a **mixed-sign** boundary quantity | `classify_sign` refuses by design (measured, P5, on all four sides for `u·n`). Closing it needs per-position orientation or sub-region decomposition — i.e. the topology contract this milestone series has repeatedly deferred |

### AWKWARD BUT EXPRESSIBLE — no new contract needed; the proof would document each

| # | What | The awkwardness |
|---|---|---|
| A1 | Both coupled inputs (`diffusivity`, `ambient_conductance`) are **parameters** | Legal endpoints (P6a) but invisible to `unresolved_inputs`/`externally_imposed` (P6b). A records-only reader cannot tell a coupled parameter from a configured one. Workaround: none needed — the explicit `QuantityDependency` states it. Cost: the completeness check `ET-VERTICAL` relied on (the "N0 gate") is weaker here, and the proof must say so |
| A2 | Rebuilding a participant per sweep | Changing a *parameter* means constructing a new `Transport2DDomain` and a new `ScientificProblem` each iteration, because parameters are frozen on the problem record. `ET-VERTICAL` already does exactly this in `stage_problems`; `run_fixed_point`'s executor callable absorbs it. Cost: a per-sweep `problem_id` stability discipline, since `run_fixed_point` refuses a result whose `problem_id` does not match |
| A3 | Three kelvin-valued quantities on the thermal problem | `temperature` (STATE at t₀), `final_temperature`, `steady_state_temperature` — dimensionally identical; only the enumerated name separates them, and `coupled.py` already documents that choosing between the last two changes the answer by 3.4 K in the ET consumer. Expressible; a silent-wrong-answer hazard that must be tested, not assumed |
| A4 | No relaxation factor in `FixedPointCouplingPlan` | Measured (P3): the `|gain| ≈ 0.71` operating point does not converge undamped in 40 sweeps. Expressible outcome — `ITERATION_LIMIT_REACHED` exists precisely for this. Adding damping is a **fail condition** per `electrothermal-vertical-prereg.md` §12.10, so the honest move is to report both operating points |
| A5 | The participant's discretization error does not reach the coupled record | Measured (P4): +17 K, +35% of the temperature rise, at `n=32`. Each participant's `ValidationReport` and `Uncertainty` exist on its own `ScientificResult`; `CoupledRun` holds the per-iteration results, so the information is *present* but no record *relates* participant error to coupled error. Expressible by reporting both; not expressible as a single coupled uncertainty |
| A6 | Reading the fluid's array requires leaving the result record | A `ScientificResult` names bulk data, it does not contain it. Computing `Φ_D` inside the domain (as a declared metric) avoids this entirely — which is why the recommendation puts the reduction *in the fluid domain* rather than in the coupling. A coupling that reduced a field itself would need a resolver and would be doing physics in the loop |

### NOT A BLOCKER, contrary to what §B9 of the predecessor predicted

`docs/fluid-pde-preparation.md` §B9 concluded that "resolving this
benchmark's own representational gaps (B4–B7) is a strict prerequisite for a
real Fluid↔Thermal field coupling". That remains true **for a field
coupling**. It is **not** true for the recommended scalar coupling: boundary
orientation now has a record and classifies the transported quantity (P5),
`VariableBulkLinkage` shipped and is exercised in production, and the
recommended proof transports no field at all. The predecessor's finding is
narrowed, not overturned.

---

## FT8 — What is explicitly NOT forced by this recommendation

Recorded so that a later reader cannot mistake the proof's scope for a
mandate.

* **No field-transfer contract**, no transfer operator, no interpolation, no
  projection, no conservative remapping.
* **No mesh, topology, support, coordinate-frame or shape contract**
  (`FIELD0` / `TOPO0` stay deferred).
* **No boundary sub-regions**, no per-position orientation, no spatially
  varying boundary values.
* **No promotion of `FixedPointCouplingPlan` / `CoupledRun` into universal
  core.** The proof *runs* the promotion test; passing it makes them
  candidates, and the decision is a separate one made on the evidence.
* **No relaxation, damping, acceleration, rollback, checkpointing or
  divergence detection**, and no coupling scheduler or participant registry.
* **No time-synchronization semantics** (FT6).
* **No change to `src/engcore/scientific/`.** Every finding in FT5 is
  recorded as a measurement, not fixed by an edit. In particular the P6c
  field-endpoint leak is **reported, not patched**: patching it would be
  minting a contract change on one consumer's evidence, and the proof does
  not depend on it.
* **No new fluid configuration.** The source-free, prescribed-wall-value
  configuration that would give the fluid leg non-trivial `Nu(Pe)` physics is
  named as the immediate follow-on and deliberately excluded from the first
  proof, so that "does the composition work" is not confounded with "is the
  new configuration correct".
* **No claim that `c` is a temperature.** The dimensionless field stays
  dimensionless; the absolute scale lives in one declared scale-restoration
  model and nowhere else.

---

## Estimated implementation effort

Scoped as "execute the recommended proof", assuming **no universal core
change**:

* **`Φ_D` as a declared metric on `fluids/transport2d`** — one
  `ModelOutputSpec`, one entry in `extract_metrics`, one `ScientificVariable`,
  one validation check against the closed form `8D`, plus a
  `BoundaryOrientation` declaring the efflux sign. The arithmetic is written
  and measured in this document's probe. **Small** (~100–150 lines across
  `problem.py`, `solver.py`, `validation.py`). The domain is not frozen.
* **Two property models** (`D(T)` and `hA(Φ_D)`), one new module beside
  `thermal_lumped.py` or under `systems/`, mirroring
  `electrical/material.py` file-for-file: two `ScientificModelDefinition`s,
  two `ModelRealizationDefinition`s, two tiny closed-form solvers, two
  problem builders. **Small** (~250–350 lines), and the pattern is copy-shaped
  from an existing, proved module.
* **The composition** — four `QuantityDependency` records, one
  `FixedPointCouplingPlan`, one torn endpoint, four executors, reusing
  `run_fixed_point` **unedited**. **Very small** (~150 lines); if it is not
  very small, the promotion test has failed and that is the finding.
* **Tests** — closed-form check of `Φ_D` against `8D` with a stated grid
  tolerance; the converging and non-converging operating points; the coupled
  answer against the analytic fixed point; a negative test that a
  `watt`-valued edge into `ambient_conductance` is refused by dimension; a
  test recording that `unresolved_inputs` reports nothing (A1); and a test
  recording that a `c:field` endpoint checks clean (P6c) so the leak is
  pinned rather than remembered. **Small-to-medium.**
* **Runtime** — measured: 0.03 s per fluid solve at `n=32`, 18 sweeps,
  0.47 s per converged loop. At `n=128` (needed if the flux is wanted to
  ~0.3%) a solve is 8.3 s, so a converged loop is ~2.5 minutes; that belongs
  in a slow tier, not the default one.

**Rough order of magnitude:** comparable to `MIN-FOUNDATION-ET`, and smaller
than `ET-VERTICAL` — a small, single-author, few-day-scale milestone,
because every record it needs already exists and every number it must agree
with has a closed form.

---

## Stop conditions

* **Stop before writing anything** if the intended transported scalar is
  `c:centre`, `c:max` or `c:min`. P1 shows that loop transports only
  discretization error. This is the one hard stop in this document.
* **Stop and re-scope** if the proof cannot be written without editing
  `FixedPointCouplingPlan`, `TornEndpoint`, `CoupledRun` or `run_fixed_point`.
  That is the preregistered promotion test (`electrothermal-vertical-prereg.md`
  §16) failing, and the correct output is that finding — not an edit that
  makes the second consumer fit.
* **Stop** if closing the loop requires a `QuantityDependency` whose endpoint
  is a field. The proof is defined to need none; needing one means the scope
  drifted into candidate 2.
* **Stop** if a relaxation factor, damping term or convergence-criterion
  change is reached for. `electrothermal-vertical-prereg.md` §12.10 makes it a
  fail condition, and P3 shows exactly which operating point will tempt it.
* **Stop and consult** the temporal track directly, rather than guessing, if
  the proof finds itself advancing the thermal interval between coupling
  sweeps. That converts a steady↔steady-limit coupling into a transient one
  and changes FT6's answer.
* **Stop before touching `src/engcore/domains/thermal/`** — it is byte- and
  set-pinned and there is no unfreeze path.

## Reversal triggers — conditions under which this recommendation should be abandoned

* **If a second real thermal domain lands that is 2D and not frozen**, the
  same-grid field coupling (candidate 2) becomes far cheaper than scored
  here, and its score should be recomputed — its cost score of 2 is almost
  entirely "the domain does not exist".
* **If the P6c field-endpoint leak is closed in core** (by consulting
  declared variables' bulk linkage before admitting an endpoint, or
  equivalently), then a field endpoint would once again fail honestly, and
  the argument that candidate 1 is the only one that "does not force the
  deferred contract" weakens — because the contract would then have a
  defined, checkable boundary to build against.
* **If the manufactured-solution degeneracy is judged fatal** — i.e. a
  reviewer holds that a coupling whose fluid leg reduces to `Φ_D = 8D`
  analytically is not a composition proof at all — then the recommendation
  should be upgraded in place to the source-free, prescribed-wall
  configuration named in FT8, accepting the added cost and the loss of the
  manufactured reference for that configuration. The dependency graph, the
  contract map, and FT6's answer are unchanged by that upgrade; only the
  fluid domain's configuration changes.
* **If `thermal_lumped` acquires a `CONTROL`-role conductance** (or the
  coupled input otherwise becomes a variable), finding A1 evaporates and the
  proof loses one of its three contract findings — still worth running, but
  re-score its composition-testing value before committing.
* **If a coupling *runtime* is adopted from outside** (preCICE or similar),
  this entire comparison is about a decision that was made elsewhere, and the
  question becomes which records that runtime needs — not which coupling is
  cheapest to hand-write.

---

## What was and was not touched

```
$ git diff 6caa1139 -- src/
(empty)
$ git status --short
?? docs/fluid-thermal-preparation.md
?? experiments/fluid_thermal_prep/
```

New files only:

* `docs/fluid-thermal-preparation.md` — this document.
* `experiments/fluid_thermal_prep/coupling_probe.py` — the standalone probe.
  It imports `engcore` read-only, is not collected by `pytest`, adds no test
  and asserts nothing about `src/engcore/scientific`.

No test was added or changed on this branch, and the full suite was not run:
a sibling track is working concurrently on the same baseline and this cycle
expects zero production changes from Track B.
