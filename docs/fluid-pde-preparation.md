# FLUID PDE ARCHITECTURE PREPARATION — Track B

**Kind:** preparation / reconnaissance. **No architecture was implemented, no
core file was touched.** This document selects a consumer, defines its
benchmark, grounds an execution-path recommendation in one executed probe, and
maps it against the *current* accepted core (baseline `004e3256`). It freezes
nothing and is not a preregistration.

**Branch:** `fluid-pde-preparation`, worktree `crafty-track-b`.
**Constraint honored:** `git diff origin/cloud/crafty-baseline -- src/engcore/scientific` is empty on this branch (asserted below, §"What was and was not touched").

This document does **not** run in a vacuum. Two prior milestones already
probed almost exactly this territory — `HOSTILE-CORE-STRESS`
(`docs/hostile-core-domain-stress-evidence.md`) and `CROSS-DOMAIN-COVERAGE`
(`docs/cross-domain-coverage-stress-evidence.md`, consumer B) — and both
independently converged on the same next step. Track B's job is not to
rediscover that; it is to (a) confirm the convergence with fresh scoring
against the mission's exact criteria, (b) ground the open numerical questions
(convergence order, execution cost) in a fresh executed probe neither prior
milestone ran, and (c) re-map the pressure classification against the current
baseline for a reader who has not read four prior evidence documents.

---

## B1 — Candidate selection

### Scoring

| Criterion | 1. 2D scalar advection-diffusion | 2. Stokes flow (pressure-driven) | 3. Minimal incompressible Navier-Stokes |
|---|---|---|---|
| Scientific realism | Real transport physics (species/heat/momentum-analog transport); a legitimate PDE, not a toy | Real physics; a legitimate simplification of viscous flow | Real physics; the physics of record for CFD |
| Architectural pressure (new, vs. already-served) | High and **targeted**: 2D support, vector-valued field input, orientation-varying boundary (prior evidence already measured this is unresolved) | High but **entangled**: adds a saddle-point (velocity-pressure) coupling and a divergence-free constraint on top of everything transport already needs | Highest, but **maximally entangled**: adds nonlinearity, saddle-point coupling, and time-stepping simultaneously — confounds 3+ pressures at once |
| Implementation cost (probe-scale) | Low — a single scalar Poisson-like linear solve per grid, ~150 lines, seconds of runtime (measured, see §B3) | Medium-high — vector unknowns + a pressure Lagrange multiplier, needs a stable discretization (staggered grid or inf-sup stable pairing) to avoid checkerboarding | High — Stokes cost plus a nonlinear (Picard/Newton) outer loop and, for anything but toy Reynolds numbers, stabilization |
| Analytical/manufactured reference availability | Excellent — smooth manufactured solution, exact at every point, zero approximation in the reference itself (already built and reused here) | Good — Poiseuille / lid-driven-cavity references exist but the cavity's own reference is itself numerical at the corners; manufactured solutions need vector calculus care for the saddle point | Fair — Taylor-Green vortex is a clean manufactured/analytical case, but exercising it usefully requires enough resolution + timestepping to be non-trivial cost |
| Runtime (probe scale) | Seconds (measured: dense solve <1 s up to 4096 DOF; sparse solve <10 ms, see §B3) | Likely seconds-to-tens-of-seconds for a probe-scale mesh, given the larger unknown count (2 velocity components + pressure per node) | Minutes at minimum for a meaningful case; an outer nonlinear loop multiplies the linear-solve cost measured here by 5-20x |
| Boundary-orientation relevance | **Direct and sharp** — with a rotational velocity field, `u·n` changes sign *within* a single boundary side (prior evidence, reused and re-verified here) | Present but usually simpler in practice — canonical Stokes benchmarks (Poiseuille, cavity) mostly use whole-side inflow/outflow/wall, so the "sign varies along one side" pressure is not automatically exercised | Present, same as Stokes, plus a nonlinear inflow/outflow coupling that would confound the finding with convective boundary treatment |
| Distributed-state pressure | Moderate — one scalar field per cell, already shown to force a field-valued *model input* (the prescribed velocity) with no typed home | High — velocity (vector) and pressure (scalar) as *coupled unknowns*, forcing rank and multi-field-per-node questions the mission explicitly says are unprobed and out of scope for a single targeted stress | Highest — same as Stokes plus a time history |
| Future Fluid↔Thermal relevance | High — advection-diffusion of a scalar is structurally identical to convective heat transport (`∂T/∂t + u·∇T = α∇²T + q`); the exact operator a Fluid→Thermal coupling will reuse | High — a validated velocity field is a prerequisite for a *convective heat transfer coefficient*, but Stokes alone (no thermal buoyancy, no energy equation) does not itself touch thermal quantities | High — same relevance, at higher cost, with no marginal thermal-coupling insight over Stokes or over advection-diffusion with a *given* velocity field |
| **Confounding cost** (mission's explicit anti-criterion) | **Low** — isolates 2D support + field-valued input + boundary orientation, and *nothing else* | **Medium-high** — bundles a saddle-point/incompressibility pressure with everything transport already needs, so a representation failure cannot be attributed to one cause | **High** — bundles nonlinearity, saddle-point coupling and (for anything realistic) unsteadiness on top of everything Stokes needs; explicitly the failure mode the mission warns against ("do NOT default to Navier-Stokes just because it sounds more impressive") |

### Verdict: **Candidate 1 — 2D scalar advection-diffusion (in a prescribed, non-trivial velocity field)**

This is not a default choice; it is the choice two independent prior
milestones already arrived at from different starting points:

* `HOSTILE-CORE-STRESS` ran a 1D advection-diffusion probe, found boundary
  orientation `FORCED`, and preregistered its rejected candidate D — *"2D
  scalar transport in a prescribed velocity field"* — as *"the natural
  choice, because it forces the representational half this milestone
  deliberately did not probe"* (vector rank, 2D support, field-valued
  coefficients), explicitly over a 2D Navier-Stokes skeleton, which it
  rejected because it *"fuses six architectural pressures, so a
  representation failure could not be attributed to a cause"*
  (`docs/hostile-core-domain-stress-evidence.md` §B, §Q).
* `CROSS-DOMAIN-COVERAGE` subsequently ran exactly that candidate as a
  **minimised probe** — consumer B, `experiments/cross_domain_coverage/transport2d.py`
  — 2D steady advection-diffusion in a prescribed *rotational* field, verified
  against a manufactured solution — and its own preregistered next step
  states: *"Consumer B was run here as a minimised probe, so the
  preregistered preference is promotion of it into a real domain pack"*
  (`docs/CRAFTY_MASTER_CONTEXT.md` §68.5).

Both prior instruments independently rejected the Navier-Stokes-shaped
option on the same confounding argument the mission itself gives, and both
converged on the same consumer this scoring table selects. Stokes flow was
not previously probed and is scored above for completeness; it loses on the
same confounding axis one notch less severely than Navier-Stokes, and its
marginal architectural pressure over advection-diffusion (a saddle-point
constraint) is not on the mission's list of concepts prior evidence found
`FORCED` or `LIKELY-FORCED` — so paying for it now, before the transport
pressures are resolved, would not reduce net future cost.

**This document therefore treats "promote consumer B toward a real domain"
as the working target for benchmark definition (B2) and pressure mapping
(B4-B9), while adding genuinely new evidence** — a convergence-order
measurement and a solver-cost comparison — that neither prior milestone
produced, because both deliberately minimised to answer a different question.

---

## B2 — Benchmark definition

**Governing equation** (identical to `CROSS-DOMAIN-COVERAGE` consumer B,
restated here as the frozen benchmark statement):

```
div(u c) - D grad^2 c = s(x, y)          on Omega = [0, 1] m x [0, 1] m
u(x, y) = omega * (-(y - 1/2), (x - 1/2))     solid-body rotation, div(u) = 0
D = 0.01 m^2/s        (diffusivity)
omega = 1 /s          (angular rate)
```

`c` is dimensionless and normalized (consistent with every scalar-transport
consumer already in this repository — no absolute scale is claimed).

**Physical domain:** unit square, no internal geometry, single connected
region — deliberately the simplest 2D domain, so any representational
failure is attributable to the transport/boundary/field pressures rather than
to geometric complexity.

**Boundary conditions:** Dirichlet on all four sides, `c = c*(x, y)` (the
manufactured solution restricted to the boundary; `c* = 0` on all four sides
here because `sin(pi x) sin(pi y)` vanishes on the unit square's edges).

**Manufactured solution** (used as both the exact reference and the source of
the forcing term, so the reference carries zero approximation of its own —
an explicit improvement the prior 1D probe's semi-infinite Ogata-Banks
reference could not offer):

```
c*(x, y) = sin(pi x) sin(pi y)
s(x, y)  = u . grad(c*) - D * laplacian(c*)      (derived analytically; exact)
```

**Initial condition:** none — this benchmark is posed **steady**, matching
consumer B. A transient variant is explicitly out of scope here (see
"What was NOT forced" below): it is a legitimate follow-on, not a
requirement of this benchmark.

**Quantities of interest (QoIs), with acceptance tolerances measured against
the exact manufactured solution:**

| QoI | Definition | Acceptance tolerance |
|---|---|---|
| `c:mms_error` | max nodal `\|c_numeric - c*\|` over all cell centres | Not a fixed pass/fail threshold — the correct acceptance criterion is the **observed convergence order** (below), because the benchmark's purpose is to characterize discretization error, not to certify one mesh |
| `c:centre` | field value at the domain centre `(0.5, 0.5)` | Reference value `c* = 1.0` (both `sin(pi*0.5)` factors are `1`); useful as a single scalar QoI a `ScientificResult.values` entry can carry today |
| `admissibility_violation` | `max(0, -c_min, c_max - 1)` — the field must stay in `[0, 1]`, the analytic range of `c*` on this domain | Measured to be **non-zero only at the coarsest probed grid** (`n=8`: `0.0136`) and **exactly zero from `n=16` upward** — see §B3. This is a *discretization* admissibility signature, not a physics one, and should be reported, not silently tolerated |
| observed convergence order `p` | `log2(err(n) / err(2n))` between successive grid doublings | Expected to approach **1** asymptotically (first-order upwind advection dominates the truncation error at the cell Peclet numbers this benchmark's velocity scale produces); **measured** to rise `0.72 -> 0.83 -> 0.90` across three doublings, consistent with that expectation and not yet asymptotic even at `n=64` |

**Convergence expectations:** the scheme (first-order upwind advection,
second-order central diffusion) is formally first-order overall because the
advection term dominates the truncation error whenever the cell Peclet number
exceeds ~2. The benchmark's own velocity scale (`omega=1`, unit square) makes
the *peak* cell Peclet number `8.84` at `n=8` and only drop below `2` at
`n=32` — so a coarse/fine comparison at `n in {8, 16}` (what consumer B ran)
sits **outside** the asymptotic first-order regime, which is the correct,
documented explanation for why its measured error ratio (`0.480 -> 0.292`,
ratio `0.61`) is not yet close to the asymptotic `0.5`. This benchmark
definition makes that explicit rather than leaving it as an unexplained
number, and recommends `n >= 32` as the entry point for any future
convergence claim.

---

## B3 — Numerical execution path

**Compared:** (a) native dense NumPy solve, (b) SciPy sparse solve of the
*identical* assembled linear system, (c) deferring to FEniCSx/PETSc.

**Decision: SciPy sparse is the cheapest credible path. Neither a from-scratch
dense native solver nor an external heavy provider is warranted at this
benchmark's scale**, grounded in an executed probe
(`experiments/fluid_pde_prep/convergence_probe.py`, standalone — imports
nothing from `src/engcore` or from the prior probe's module, re-derives the
same governing equations independently so its numbers are not a re-print).

The probe assembles the **same** discretization (first-order upwind
advection + second-order central diffusion, cell-centred, steady) into both
a dense NumPy array and a SciPy `csr_matrix`, solves both, and checks
agreement — a genuine cross-solver check, not an assumption:

```
   n    dof   Pe_cell    mms_err   order  admiss_viol  native_s   scipy_s  cross_diff
   8     64     8.839    0.47969     n/a     0.013621    0.0002    0.0003    2.22e-16
  16    256     4.419    0.29204   0.716     0.000000    0.0270    0.0005    7.77e-16
  32   1024     2.210    0.16473   0.826     0.000000    0.0288    0.0020    3.22e-15
  64   4096     1.105    0.08826   0.900     0.000000    0.9299    0.0097    5.00e-15
```

(Full JSON output archived by the script's own `main()`; re-runnable with
`uv run python3 experiments/fluid_pde_prep/convergence_probe.py`.)

**What this grounds:**

1. **Correctness of the probe itself**: native and SciPy solve the same
   linear system to `~1e-15` agreement at every grid — the two solvers are
   not independently implemented physics, so this is not
   `CROSS_SOLVER_VALIDATED` evidence about the *model*, but it does confirm
   the assembly matches between the two code paths and gives a working
   example of what `ValidationLevel.CROSS_SOLVER_VALIDATED` could record
   later against a genuinely independent second implementation.
2. **Cost growth**: dense solve time grows from `0.2 ms` (`n=8`, 64 DOF) to
   `930 ms` (`n=64`, 4096 DOF) — consistent with the expected `O(DOF^3)`
   dense factorization cost. SciPy's sparse solve grows from `0.3 ms` to
   `9.7 ms` over the same range — roughly **95x cheaper** at the largest
   probed grid. A benchmark at `n=128` (16384 DOF, needed to push the peak
   cell Peclet below `1`) would push the dense solve to an estimated tens of
   seconds and the sparse solve to well under a second. **This is the
   concrete number behind "select the cheapest credible path": dense native
   does not scale into the regime this benchmark's own convergence
   expectations require; SciPy sparse comfortably does.**
3. **No case for FEniCSx/PETSc at this scale.** The benchmark's linear
   system, assembled directly with a five-point-plus-upwind stencil, is
   solved by `scipy.sparse.linalg.spsolve` in single-digit milliseconds up
   to 4096 unknowns. A general-purpose FEM/PETSc stack would add a real
   dependency, a real build/version-pinning surface, and a real "external
   provider optional, never a dependency of the core" question
   (`docs/scientific-core/README.md`, "What external packages own") for a
   benchmark that does not need it. The reversal trigger below states when
   that changes.

---

## B4 — Core pressure map (against baseline `004e3256`)

| Concern | Classification | Justification (found in code / prior evidence, not asserted) |
|---|---|---|
| Variable ↔ Bulk linkage | **FORCED** | `ScientificDataReference` carries `{name, unit, count, dtype, digest}` and no field naming which `ScientificVariable` (or which component of a multi-component variable) the bulk array instantiates. `CROSS-DOMAIN-COVERAGE` found this forced 4/4 across independently chosen consumers (`docs/CRAFTY_MASTER_CONTEXT.md` §68.2) and it is this benchmark's own field (`c` over 1024+ cells at `n>=32`) that would need it the moment a result is more than one scalar reduction. Track A may already be building `VariableToBulkLinkage`; not present in `src/` at this baseline (checked: `grep -rl VariableToBulkLinkage src/` returns nothing) |
| Field identity | **NOT RELEVANT here / LIKELY-FORCED generally** | Ledger 2 per `HOSTILE-CORE-STRESS` §G — `Q2`/`Q4` (scalar-vs-distributed, spatial support) are structurally `impossible` today. This benchmark does not need `ScientificField` as a *new record* to run (see B6) — it forces the *question*, not the *contract* |
| Component/rank semantics | **DEFER for this benchmark** | `c` is rank-0 (scalar); the velocity is rank-1 but is a **model input**, never a searched/observed `ScientificVariable`, so `ScientificVariable`'s own rank semantics are not exercised. `CROSS-DOMAIN-COVERAGE`'s mechanics consumer already forced rank-1/rank-2 semantics on a *different* consumer; deferred here per the anti-confounding argument in B1 |
| Physical support (spatial domain) | **LIKELY-FORCED** | No field states "`c` is defined over the unit square" — `ScientificParameter` carries `side_m` as a bare scalar extent, not a domain. Re-confirms `HOSTILE-CORE-STRESS` §G/§H (Ledger 2, zero new evidence claimed here) |
| Boundary orientation | **FORCED** | Directly re-verified for this exact benchmark in `experiments/cross_domain_coverage/transport2d.py::inflow_fraction` — with the rotational field, `u.n` changes sign at the midpoint of every one of the four sides, so a single `BoundaryCondition(region="side-n", ...)` record is asked to carry two physically distinct roles at once. See B7 |
| Field-valued input | **FORCED** | `ScientificProblem` has no `data_references` field (that exists only on `ScientificResult`/`RawSolverOutput`); the prescribed rotational velocity and the manufactured source term are both field-valued **model inputs** with no typed home anywhere in a problem statement. Verified by inspection of `src/engcore/scientific/ir/problem.py` (no such field) and corroborated by `HOSTILE-CORE-STRESS`/`CROSS-DOMAIN-COVERAGE` |
| Geometry | **NOT RELEVANT (for this benchmark)** | The unit square with no internal features needs no geometric contract beyond a scalar extent, which already exists (`ScientificParameter`). A curved or multiply-connected domain would force this; deliberately out of scope (see "what is NOT forced") |
| Topology / connectivity | **LIKELY-FORCED** | Same Ledger-2 finding as physical support — a grid's cell adjacency is what the solver probe builds by hand (`index(i,j)`, `neighbour(di,dj,...)` in `convergence_probe.py`), and nothing in the IR names or checks it. Zero new evidence claimed here beyond re-confirming `HOSTILE-CORE-STRESS` §H |
| Initial conditions | **NOT RELEVANT for the steady benchmark as scoped / LIKELY-FORCED for a transient extension** | This benchmark declares no `InitialCondition` because it is posed steady; a transient extension would immediately hit the same "`InitialCondition.value` is one `Quantity`, and a spatially-varying IC has no home" gap `HOSTILE-CORE-STRESS` already found on the 1D domain's `sin(pi x / L)` initial field |
| Boundary conditions | **ALREADY SERVED (kind+value) / FORCED (identity, see above)** | `BoundaryCondition(kind, region, value)` round-trips correctly for Dirichlet with dimension checking (verified: `src/engcore/scientific/ir/conditions.py` requires a `Quantity` value for `DIRICHLET`/`NEUMANN`). The *value* channel is served; *identity/orientation* is not (separate row above) |
| Discretization | **DEFER** | `SlabDiscretization`-style typed resolution records already exist in one domain (`thermal/conduction1d/problem.py`); nothing prevents a 2D analogue, and `HOSTILE-CORE-STRESS` found *identity* already works via `ExecutionBinding`/`ImplementationReference` (realization identity, not selection) — the gap is **selection**, i.e. no typed property lets a planner *choose* upwind vs. central, which is a `DEFER` per that milestone's own fidelity-conflation argument |
| SolverSettings persistence | **PARTIALLY SERVED / EXECUTION SPEC GAP** | `SolverSettings.tolerances: Mapping[str, float]` and `.options: Mapping[str, Any]` exist and are typed for *tolerances*, but grid resolution (`n_cells`) and scheme choice (`upwind` vs `central`) would have to live in the untyped `options` bag — see B8 |
| Solver capability semantics | **ALREADY SERVED** | `SolverCapability("transport", "advection_diffusion_2d")`-style identifiers already declared and used by `experiments/cross_domain_coverage/records.py`; the capability/model/solver separation (`MODEL0-R`) held under this exact consumer per `HOSTILE-CORE-STRESS` §K |
| Provenance | **ALREADY SERVED (for scalars) / EXECUTION SPEC GAP (for mesh-dependent facts)** | `ProvenanceRecord.inputs: Mapping[str, Quantity]` already gives a typed, dimension-checked home for a **run-scoped** fact like `peak_cell_peclet` (measured and reported per-grid in §B3, mirroring `HOSTILE-CORE-STRESS` ENCODING_C). It cannot make that fact *pre-run* assessable — see B8 |
| Admissibility | **PARTIALLY SERVED — asymmetric** | A domain can write an admissibility **violation** check today with no contract change (verified: `admissibility_violation` in this probe and in consumer B both compute and could be attached as a `ValidationCheck` that FAILs); `ValidationLevel` has 7 members (verified: `src/engcore/scientific/results/validation.py`) and **none** denotes a passing physical-admissibility attainment. Measured here too: at `n=8` the field overshoots `[0,1]` by `0.0136`, and nothing structural stops that record from separately claiming `ANALYTICALLY_VERIFIED` |
| Future thermal coupling | **PARTIALLY SERVED, see B9** | `QuantityDependency` exists and is scalar-endpoint-oriented by design; see B9 for the per-quantity breakdown |

---

## B5 — Body/discretization pressure

Tried directly against this benchmark, not asserted: attempted to express
"the unit square being discretized by an `n x n` grid" using only existing
typed contracts.

* **Physical body / geometric domain-support**: no home. `ScientificParameter("side_m", ...)` states an extent, not a shape, a boundary set, or a coordinate system. This is the *same* gap `HOSTILE-CORE-STRESS` found on the 1D slab (`length` as a bare scalar), now measured on a 2D domain where it additionally has to distinguish "extent along x" from "extent along y" from "which of four labelled sides is which physical edge" — three facts a 1D slab could not even pose as distinct.
* **Discretization**: has a working, typed pattern *elsewhere* in the codebase (`SlabDiscretization` in `thermal/conduction1d/problem.py` — `n_cells`, `n_steps`, kept deliberately separate from the physical declaration) that generalizes cleanly to `n_cells_x, n_cells_y` for this benchmark; this is **not a new pressure**, it is a reusable pattern.
* **Boundary region**: served for *labelling* (`BoundaryCondition.region` is a free string, exercised here as `"side-n"` etc.) and **not** for orientation (B7) or for "where along this side" (a time-varying or spatially-varying boundary value on one side has no coordinate channel — `HOSTILE-CORE-STRESS` §C already rejected `BoundaryCondition.coefficients` as a place to smuggle a boundary coordinate, because the coefficient *key* would have to carry the science: `"position"`, `"x"`, `"coord"` are all equally valid and mutually unintelligible).
* **Numerical mesh**: appears in this benchmark only as a *count* (`n_cells_x * n_cells_y`), never as connectivity, coordinates, or cell/face/node association — `HOSTILE-CORE-STRESS` §M's `Mesh: REJECT` verdict is re-confirmed rather than re-discovered: nothing in this benchmark needed one.

**What this benchmark forces separating, concretely:** *physical body* (a
shape claim) from *discretization resolution* (a count, already served by
the `SlabDiscretization` pattern) from *boundary region identity+orientation*
(not served). It does **not** force separating a numerical *mesh* as its own
concept from discretization resolution — at this benchmark's regularity
(a structured square grid), "how many cells" and "what mesh" **coincide** in
practice, and nothing here forces prying them apart. An unstructured or
curved-domain benchmark would force that; this one is deliberately simpler
and says so rather than assuming the harder case.

---

## B6 — Field pressure

Asked concretely, against this benchmark, without assuming `ScientificField`
is needed: what can this benchmark **not** express with
`ScientificVariable` + `ScientificDataReference` + `Quantity` alone?

**Limitation acknowledged up front, per the mission's instruction:**
Track A runs concurrently in a separate worktree this session cannot see. If
a `VariableToBulkLinkage`-shaped concept exists on Track A's branch by the
time this is read, the row below marked *forced* may already be served
there — this document reports against the **baseline** (`004e3256`), where
`grep -rl VariableToBulkLinkage src/` returns nothing (checked above, B4).

| Distinction | What this benchmark forces |
|---|---|
| Field semantic identity ("`c` is the concentration field over the domain") | **Cannot** be stated. `ScientificVariable(name="c", unit="dimensionless", role=OBSERVABLE)` is byte-identical to a lumped scalar declaration — nothing distinguishes "this varies over the domain" from "this is one number". Re-confirms `HOSTILE-CORE-STRESS` Q2/Q4, zero new evidence claimed |
| Discrete field representation (1024 cell-centre values, in what order) | **Partially served.** `ScientificDataReference(name="c:field", unit="dimensionless", count=1024, dtype="float64", digest=...)` names the bulk array with storage-independent identity (verified by relocation test pattern already exercised in `HOSTILE-CORE-STRESS` §F) but **cannot** state that the 1024 values are laid out `i*n+j` on an `n x n` grid — `count` is explicitly documented as *"not a shape, mesh, topology or field support"* (`src/engcore/scientific/results/data_reference.py`) |
| Bulk storage (where the bytes live) | **Fully served, and orthogonal to the above two rows by design.** `ScientificDataReference` carries no path/URI/host — DATA-BOUNDARY0's separation holds unchanged under this benchmark, same as `HOSTILE-CORE-STRESS` measured |
| Mesh support (which physical point each value belongs to) | **Not served, and this benchmark forces the question just as sharply as the 1D probe did** — the difference is that a 1D index unambiguously means "this far along the slab", while a flattened 2D index `i*n+j` requires knowing `n` *and* the flattening convention to recover `(x,y)`, which is carried nowhere in any record and lives only in the probe script's own `index()` closure |

**What is genuinely new here versus the 1D finding:** the flattening
convention. In 1D, "value #57 of 161" already resolves to a physical
location once `n_cells` is known (a single division). In 2D it does not — an
`n x n` flattening needs a stated row-major/column-major convention on top
of the count, which is one more fact with no typed home, and it is a fact a
future consumer reading only records (not source) would have to guess.

---

## B7 — Boundary orientation

**Forced, and forced at a granularity finer than a region label — directly
re-verified for this benchmark**, not assumed from the 1D finding.

`experiments/cross_domain_coverage/transport2d.py::inflow_fraction` computes,
for each of the four labelled sides, the fraction of the side where
`u . n < 0` (flow entering). With the rotational field:

```
every side: inflow_fraction == 0.5
```

Every side is **half inflow, half outflow simultaneously** — reversing the
rotation direction (`omega -> -omega`) keeps every fraction at exactly `0.5`
(so the *fraction* alone is a poison-pill regression proxy: it cannot see
the reversal at all), while the underlying *set* of inflow points on each
side swaps entirely (`orientation_signature` in the same module, exercising
the point-by-point `bool` sequence rather than the aggregate fraction).

**This is strictly sharper than the mission's own framing** ("varies in sign
along a single boundary side"): a simple `"inlet"/"wall"/"outlet"` string or
enum per `BoundaryCondition.region` cannot express it even as a label, because
there is no single correct label for `"side-n"` — it is inlet along half its
length and outlet along the other half, at the same instant, for a *steady*
problem (no time-dependence needed to produce this). `region` would need
either (a) a per-side orientation field that is a *function* of position, or
(b) the boundary discretized into sub-regions no coarser than the sign
change — which reintroduces the mesh/topology question from B5. This
document does **not** propose which; per the mission, that is a Track A
design question, not a Track B answer.

---

## B8 — Solver settings

**Yes, this benchmark's execution materially depends on all five
categories the mission lists.** Classified against `SolverSettings`
(`src/engcore/scientific/solvers/protocol.py` — `tolerances: Mapping[str,
float]`, `options: Mapping[str, Any]`, both provenance-recorded, neither
part of the *problem* statement):

| Concern | Materially affects this benchmark? | Classification | Why |
|---|---|---|---|
| Mesh resolution (`n_cells_x`, `n_cells_y`) | Yes — measured: `mms_error` moves `0.480 -> 0.088` and `peak_cell_peclet` moves `8.84 -> 1.10` across the four probed grids | **SCIENTIFIC SPEC GAP** | `HOSTILE-CORE-STRESS` §J.3's ENCODING_B/C finding applies unchanged: put resolution in `metadata` and the problem's own identity is silent about it (what this benchmark's prior probe did); put it as a typed parameter and two meshes become two different `problem_id`s, which is arguably correct but was not adopted by the existing 1D domain either. Not a `SolverSettings` gap at all — it is upstream, in whether resolution is part of *what problem is being posed* |
| Time step | Not applicable to this steady benchmark; would be a SCIENTIFIC SPEC GAP for a transient extension, same reasoning as `SlabDiscretization.n_steps` in the existing thermal domain |
| Numerical scheme (upwind vs. central, this probe uses both at once for different terms) | Yes — measured: `HOSTILE-CORE-STRESS` §J.2 found scheme choice is expressible as *realization identity* (`ModelRealizationDefinition.name`/`description`/`assumptions`) but **not** as a typed, selectable property; every typed field (`formulation`, `provided_capabilities`, etc.) is identical between the two realizations | **EXECUTION SPEC GAP** | This is not "unrecorded" — it is recorded in free text where a planner cannot select on it. `SolverSettings.options` could carry a string key like `"scheme": "upwind"`, but that is exactly the untyped-bag pattern the mission's constraints (and `docs/scientific-core/README.md`'s fidelity-enum rejection) warn is a weak substitute for a typed field |
| Linear tolerance | This benchmark's linear solve is direct (`spsolve`/`np.linalg.solve`), not iterative, so no *convergence* tolerance applies at this scale; an iterative solver at larger grids would need one, and `SolverSettings.tolerances` already has a typed, finite-checked home for it | **ALREADY SERVED** (for the concern itself); the gap is only that nothing in this benchmark currently exercises it |
| Nonlinear tolerance / iteration limits | Not applicable — this benchmark's governing equation is linear (velocity is *prescribed*, not solved for) | **NOT RELEVANT for this benchmark** — would become relevant only if velocity were solved for (Stokes/Navier-Stokes), which B1 explicitly deferred |
| Provenance of the executed settings | The probe script's own `n`, scheme, and measured `peak_cell_peclet` are exactly the kind of fact `ProvenanceRecord.inputs` already accepts (typed `Quantity`, dimension-checked, run-scoped) — measured working in `HOSTILE-CORE-STRESS` §J.3 ENCODING_C and reused unchanged here | **PROVENANCE GAP is narrow, not absent**: the *value* has a home (`ProvenanceRecord.inputs`); what is missing is a **pre-run** typed home, so `ValidityDomain`/`validity_context` cannot screen a proposed discretization before a solve is spent — the exact residual `HOSTILE-CORE-STRESS` narrowed the "no encoding gives both" claim down to |

**No redesign proposed.** This table classifies; it does not fix.

---

## B9 — Fluid ↔ Thermal future

Without implementing any coupling, per quantity a future Fluid↔Thermal
exchange would need, checked against contracts as they exist at baseline
`004e3256`:

| Exchanged quantity | Can current contracts express it? |
|---|---|
| Temperature field (from Thermal to Fluid, e.g. as a buoyancy source) | **Scalar reduction only.** A single temperature value (`ScientificVariable` + `Quantity`) is fully expressible and could be a `QuantityDependency` endpoint today — matching `HOSTILE-CORE-STRESS` §L's measured finding that "the only expressible coupling endpoint today is the one that has already thrown the field away." A full temperature *field* has exactly the same gap as this benchmark's own `c` field (B6): nameable as a `ScientificDataReference`, not connectable as a `QuantityDependency` endpoint, because that record explicitly refuses to resolve through `data_references` (`"nothing in this record can state how a field is transported between two supports"`, quoted verbatim in `docs/scientific-core/README.md` and re-confirmed by `HOSTILE-CORE-STRESS` §L) |
| Heat flux (from Fluid to Thermal, at a wall) | **Same shape as a Neumann boundary value.** `BoundaryCondition(kind=NEUMANN, value=...)` already carries a flux-shaped `Quantity` with no dimension check forced (core deliberately does not constrain Neumann units, per `docs/scientific-core/README.md`'s condition-validation table) — a scalar wall-averaged flux is expressible; a spatially-varying flux *field* along a wall has the same "no coordinate channel on a boundary condition" gap `HOSTILE-CORE-STRESS` §C already found and rejected `coefficients` as a fix for |
| Wall temperature (boundary value, from Fluid's perspective) | **Expressible today**, scalar case — this is exactly `BoundaryCondition(kind=DIRICHLET, value=<temperature Quantity>)`, dimension-checked, already the pattern this benchmark itself uses for `c` |
| Velocity field (from Fluid to Thermal, as the advecting field in a convective term) | **This is precisely this benchmark's own unresolved field-valued-model-input gap (B4/B6)** — a scalar velocity magnitude is expressible; the vector field driving advection is not, with no typed home in `ScientificProblem` today. A Fluid→Thermal coupling would inherit this gap unchanged, not create a new one |
| Convective heat transfer coefficient `h` | **Expressible as a scalar parameter or a `QuantityDependency` endpoint** (a derived Nusselt-correlation-style scalar), the same shape as any other configured `ScientificParameter`. A *spatially-varying* `h(x,y)` along a wall has the same gap as heat flux above |

**Net finding:** every quantity that is a **scalar reduction** already has a
typed home and a working coupling-declaration path
(`QuantityDependency`, deliberately scalar-endpoint-oriented per
`MIN-FOUNDATION-ET`). Every quantity that is a **field** inherits this
benchmark's own unresolved gaps exactly, with no additional coupling-specific
gap discovered. This means **resolving this benchmark's own representational
gaps (B4-B7) is a strict prerequisite for a real Fluid↔Thermal field
coupling**, not a separate body of work — a finding worth stating plainly for
whoever scopes that milestone.

---

## Estimated implementation effort for the real consumer

Scoped as "promote consumer B into a real domain pack" (the preregistered
preference in `docs/CRAFTY_MASTER_CONTEXT.md` §68.5), **assuming no core
change** (i.e., accepting the ENCODING_A/metadata-carried gaps this document
maps rather than waiting on `MIN-FOUNDATION-PDE`):

* Domain module (`src/engcore/domains/fluids/transport2d/`, mirroring
  `thermal/conduction1d/`'s file layout: `problem.py`, `solver.py`,
  `validation.py`, `errors.py`, `reference.py`) — **small**, on the order of
  the existing `thermal/conduction1d` module (5 files, few hundred lines),
  since the physics and the manufactured reference are already written and
  measured in `experiments/cross_domain_coverage/transport2d.py`.
* Solver adapter satisfying `ScientificSolver` over the SciPy sparse path
  measured in B3 — **small**, the assembly logic already exists and this
  probe additionally validates the sparse path is a drop-in replacement for
  the dense one used by the existing minimised probe.
* Extending the grid to `n>=32` as the benchmark's documented entry point for
  a convergence claim (B2) — **no new code**, a parameter change plus
  re-running the probe pattern already exercised here.
* Everything mapped `FORCED`/`LIKELY-FORCED` in B4 (boundary orientation,
  Variable↔Bulk linkage, physical support/topology) is **explicitly not**
  included in this estimate — those are core-contract questions for
  `MIN-FOUNDATION-PDE`, owned by a different track, and this document's
  mission is preparation, not resolution.

**Rough order of magnitude:** comparable to the existing `thermal/conduction1d`
domain's own implementation size — a small, single-author, few-day-scale
addition once (and only once) the `FORCED` items in B4 have a design, since
attempting the domain module before that would either duplicate the metadata
workarounds this document and its predecessors already measured, or block on
a core change this track is explicitly not authorized to make.

---

## Stop conditions

* Stop before implementing a real domain module if `MIN-FOUNDATION-PDE`'s
  boundary-orientation resolution is not yet designed — building on top of
  the metadata workaround (`ENCODING_A`) this document catalogs would bake in
  exactly the ambiguity `HOSTILE-CORE-STRESS` measured, in production code
  rather than a probe.
* Stop and re-scope if extending past `n=64` (this probe's largest measured
  grid) shows the dense-vs-sparse gap closing rather than widening — that
  would falsify the B3 recommendation and this document's cost argument.
* Stop and consult Track A directly (rather than guessing) if
  `VariableToBulkLinkage` (or an equivalent) lands on the shared baseline
  before the domain module is started — B6's finding should be re-checked
  against it rather than assumed obsolete or assumed unchanged.

## Reversal triggers — conditions under which this consumer choice should be abandoned

* If a future reader determines the domain needs *unsteady* transport with a
  genuinely time-varying boundary value (`c(0,t) = f(t)`) as a first-class
  requirement rather than a follow-on — `BoundaryCondition` has no `time`
  field (named, not measured, by `HOSTILE-CORE-STRESS`'s falisifier pass) and
  this document's benchmark is deliberately steady; a transient requirement
  changes the entry-point benchmark, not just its resolution.
* If evidence emerges that the saddle-point/incompressibility pressure
  (Stokes-shaped) is architecturally forced *independently* of the transport
  pressures this benchmark isolates — i.e., that the two cannot be resolved
  separately in practice — then B1's anti-confounding argument for choosing
  the cheaper, narrower consumer weakens and Stokes should be re-scored.
* If a real (non-probe) consumer of this exact physics turns out to need mesh
  sizes where SciPy's sparse direct solver stops being competitive (roughly
  DOF in the hundreds of thousands to low millions, well beyond anything
  measured here) — at that point deferring to an iterative/multigrid method,
  and only then to an external provider such as PETSc, would be the
  evidence-grounded next step, not before.
* If Track A's core changes make the metadata-carried gaps in B4 (mesh
  resolution in `validity_context`, boundary orientation) cost near-zero to
  close — the effort estimate above should be revisited, since it currently
  assumes no core change is available.

---

## What was and was not touched

```
$ git status --short
(clean)
$ git diff origin/cloud/crafty-baseline -- src/engcore/scientific
(empty)
$ git diff origin/cloud/crafty-baseline -- src/engcore/domains
(empty)
```

New files only, all under `experiments/` and `docs/`:

* `experiments/fluid_pde_prep/convergence_probe.py` — standalone probe,
  imports nothing from `src/engcore` or from
  `experiments/cross_domain_coverage/`.
* `docs/fluid-pde-preparation.md` — this document.

No test file was added under `tests/` for this track — the mission scopes
Track B as preparation with an isolated probe script, and the probe's own
`main()` (executed above, output reproduced in §B3) is the evidence; no
`pytest`-collected test asserts anything about `src/engcore.scientific` from
this branch, so nothing here can be mistaken for a core-contract change.
