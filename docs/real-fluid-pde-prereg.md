# REAL FLUID PDE DOMAIN — Preregistration

**Milestone:** `REAL-FLUID-PDE-DOMAIN` — promote the prepared 2D scalar
advection-diffusion consumer (`docs/fluid-pde-preparation.md`, Track B) into
the first real, production Fluid domain package, using existing universal
Core contracts with zero or near-zero Core change.
**Kind:** domain-implementation milestone, not a Core-design milestone.
**Decision status target:** the domain package itself is a real, usable
addition (not `PROPOSED`/frozen in the Core-design sense — domain packages are
not Core contracts). Any Core-contract observation this milestone makes is at
most `PROPOSED`, same convention as prior milestones.
**Evidence target:** at most `L1 EXERCISED` for any Core-adjacent claim
(`VariableBulkLinkage`/`require_admission` real-caller status). `L2` is
excluded in advance for the same reason `MIN-CROSS-DOMAIN-FOUNDATION` excluded
it: one author, one branch.
**Date:** 2026-09-03
**Branch:** `real-fluid-pde-domain`, worktree `/home/user/crafty-fluid`, cut
from `cloud/crafty-foundation @ c687544` with
`docs/fluid-pde-preparation.md` and `experiments/fluid_pde_prep/
convergence_probe.py` cherry-picked on top unchanged (they were not, in fact,
an ancestor of `c687544` in this worktree's history — cherry-picked verbatim
from `fluid-pde-preparation @ 436d905`/`2e4054e` rather than re-derived, so
the preparation's own numbers are reused, not re-invented).

**Preregistered before implementation.** Everything below was written before
any file under `src/engcore/domains/fluids/transport2d/` was added.

> **This file is immutable.** Deviations, corrections, adversarial findings
> and the final classification go in `docs/real-fluid-pde-evidence.md` and
> nowhere else.

---

## 1. Scientific benchmark (frozen, taken verbatim from preparation)

Not re-derived, not re-selected. Restated exactly as
`docs/fluid-pde-preparation.md` §B2 froze it:

```
div(u c) - D grad^2 c = s(x, y)          on Omega = [0, 1] m x [0, 1] m
u(x, y) = omega * (-(y - 1/2), (x - 1/2))     solid-body rotation, div(u) = 0
D = 0.01 m^2/s        (diffusivity)
omega = 1 /s          (angular rate)
c*(x, y) = sin(pi x) sin(pi y)                (manufactured solution)
s(x, y)  = u . grad(c*) - D * laplacian(c*)   (derived analytically, exact)
```

Dirichlet `c = c*` on all four sides of the unit square (`c* = 0` on every
side). Steady. No internal geometry. `c` is dimensionless.

**One deliberate, declared generalization over the frozen benchmark:** the
domain declaration carries a `side` `Quantity` (physical extent) as a typed
field, separate from the discretization, exactly as
`thermal/conduction1d.ConductionSlab.length` does — with the manufactured
solution and rotation center generalized to `sin(pi x/L) sin(pi y/L)` and
`(L/2, L/2)` so the declaration is a genuine physical statement rather than a
hard-coded constant. The benchmark instance actually run uses `L = 1.0 m`,
reproducing the preparation's numbers exactly; this is stated up front so a
reader does not have to verify by inspection that the generalization is
inert at the benchmark's own parameter.

## 2. Numerical reference and expected convergence (taken from the executed probe)

`experiments/fluid_pde_prep/convergence_probe.py` (already executed, not
re-run to produce these numbers — re-run only to confirm the production
assembly reproduces them, see §7):

```
   n    dof   Pe_cell    mms_err   order  admiss_viol  native_s   scipy_s
   8     64     8.839    0.47969     n/a     0.013621    0.0002    0.0003
  16    256     4.419    0.29204   0.716     0.000000    0.0270    0.0005
  32   1024     2.210    0.16473   0.826     0.000000    0.0288    0.0020
  64   4096     1.105    0.08826   0.900     0.000000    0.9299    0.0097
```

**Expected convergence, restated as a falsifiable prediction:** the
production assembly (first-order upwind advection + second-order central
diffusion, cell-centered, ghost-cell Dirichlet) reproduces this table to
float tolerance when the identical scheme is re-implemented as production
code. Observed order rises `0.72 -> 0.83 -> 0.90`, sub-asymptotic even at
`n=64` (peak cell Péclet only drops below 2 at `n=32`), so **this milestone
does not expect, and will not claim, an analytic-agreement tolerance as tight
as `thermal/conduction1d`'s `1e-3`.** Whatever `ANALYTIC_REL_TOL` this
milestone declares for the centre-point QoI is set *after* running the
production assembly once (§7), exactly as `thermal/conduction1d`'s own
`validation.py` docstring discloses doing, and for the same reason: honesty
about how the threshold was chosen costs less than pretending it was
preregistered blind.

**Grid ladder, preserved exactly**: `n in {8, 16, 32, 64}` — the prep
document's own probed range. No grid size is added or dropped without a
documented reason (a stop condition below covers the one case that would
force a change).

## 3. Execution path (taken from the executed probe)

SciPy sparse (`scipy.sparse.linalg.spsolve`) is the production path. A dense
NumPy solve is retained as an independent-assembly *reference check*, never
as part of the scientific claim — SciPy and NumPy dense are both
**implementation details of two separate `ScientificSolver` adapters**, not
part of the `ScientificModelDefinition`. No FEniCSx/PETSc dependency is
added; the probe already found no case for one at this scale (§B3 of the
preparation document), and nothing in this milestone changes that scale.

## 4. Core contracts expected to suffice (stated before implementation)

| Concern | Contract expected to serve it, unchanged |
|---|---|
| Problem statement | `ScientificProblem`, `ScientificVariable`, `ScientificParameter` |
| Boundary values | `BoundaryCondition(kind=DIRICHLET, region=<side label>, value=Quantity(0, "dimensionless"))`, four instances |
| Solver lifecycle | `ScientificSolver` protocol (`supports/prepare/solve/validate/extract_metrics`), `PreparedSolve`, `RawSolverOutput`, `SolverSettings` |
| Result | `ScientificResult`, `ProvenanceRecord`, `ValidationReport`/`ValidationCheck` |
| Field output | `ScientificVariable` (role `OBSERVABLE`, one per field) + `ScientificDataReference.for_values` + `VariableBulkLinkage` — the mandatory F4 real caller, attempted first per §5 below |
| Admission | `ValidationReport.require_admission`/`is_admissible`/`admission_issues` — the mandatory F8 real caller |
| Model identity | `ScientificModelDefinition(model_type=FUNDAMENTAL_RELATION)` — a conservation law, not a fitted correlation, mirroring `thermal/conduction1d.DIFFUSION_MODEL`'s own classification |
| Capability | `SolverCapability("fluids:advection_diffusion_2d", ...)`, declared in this package only |

**Expected to NOT be needed**, per the preparation document's own B4-B9
mapping, restated as a prediction this milestone tests rather than assumes:
`ScientificField`, a mesh/topology contract, `MatrixValue`,
`StructuredScientificValue`, a component/connector framework, a new
`ValidationLevel` member, a new universal executable-spec record.

## 5. Expected pressure points (predictions, tested in §F4-F9 below)

1. **Field identity / flattening convention (B6).** Predicted: `count` on
   `ScientificDataReference` still cannot state the `n x n` row-major
   flattening. This residue is expected to persist and will be documented,
   not solved — solving it would mean building a shape/topology contract,
   which is out of scope per the mission's non-goals.
2. **Boundary orientation (B7).** Predicted: re-verifying against the real
   production velocity field and the real production grid reproduces the
   preparation's finding — every side is exactly half inflow, half outflow,
   with no single `region` label capable of stating that. Expected outcome:
   documented as a finding, not fixed with a topology framework.
3. **VariableBulkLinkage as first real caller (F4).** Predicted: the field
   output `c:field` (the concentration over the `n x n` grid) is exactly the
   "spatial output" shape `VariableBulkLinkage` was built for and never
   exercised against in production. If, once attempted, the field genuinely
   does not fit this shape (e.g., because more than one linkage per result is
   needed and that combination was never tested), that is reported honestly
   rather than forced.
4. **Admission as a real refusal path (F8).** Predicted: a result can be
   constructed that fails a declared `validation_requirements` name (e.g. an
   admissibility check on `c in [0, 1]` deliberately run on a grid too coarse
   to satisfy it, or a synthetically corrupted check), and a genuine
   Fluid-domain downstream function (not a copy of the Foundation's own unit
   test) that reads `result.value("c:centre")` without a guard will do so
   silently; the same function gated by `require_admission` will raise
   `ScientificValidationError` and never reach the read. This mirrors the
   Foundation milestone's own negative-proof pattern (`HETERO-NGSPICE` §8.4),
   applied here for the first time to a domain that milestone did not touch.
5. **Executable reconstruction (F9).** Predicted: the domain-local
   `Transport2DDomain`/`Transport2DGrid` declarations serialize to a plain
   dict (mirroring `ConductionSlab.to_dict()`), reconstruct from that dict
   with no original-object identity retained, and re-solving from the
   reconstruction reproduces the original result's values to float tolerance.
   No universal executable-spec record is invented; this is a domain-owned,
   versioned dict shape, exactly as `docs/fluid-pde-preparation.md` and the
   governing mission both require.

## 6. Allowed production-domain additions

New files only, under `src/engcore/domains/fluids/transport2d/` (mirroring
`thermal/conduction1d`'s five-file layout: `problem.py`, `solver.py`,
`validation.py`, `errors.py`, `reference.py`, plus `__init__.py`), and new
tests under `tests/domains/fluids/`. Nothing under
`src/engcore/domains/fluids/aerodynamics/` is touched — that package predates
this milestone and is unrelated physics.

## 7. Prohibited universal-Core additions

No file under `src/engcore/scientific/` is edited by this milestone unless a
genuine, measured blocker forces it — and if that happens, the correct
response is to **stop and report the blocker**, not to opportunistically fix
it inside this milestone (per the governing mission). Explicitly prohibited
regardless of convenience: `ScientificField`, a `Mesh`/topology contract,
Equation/Relation IR, `MatrixValue`, `StructuredScientificValue`, a new
`ValidationLevel` member, a new universal executable-spec record, a
component/connector framework, a generic boundary-orientation contract. A
verification run of `experiments/fluid_pde_prep/convergence_probe.py`'s
scheme, reimplemented as production code, is not a Core change and is
explicitly permitted (§2).

## 8. Scientific correctness thresholds

Set honestly, in the order they are determined:

* **Observed order.** Must rise monotonically across the four-rung ladder and
  every successive value must equal the preparation's own recorded numbers
  (`0.716`, `0.826`, `0.900`, each within `1e-3` absolute) when computed by
  the production assembly — this is a **reproduction** check, not a fresh
  threshold, and its failure would mean the production code does not
  implement the scheme the preparation probed.
* **Sparse/dense cross-check.** `max|c_sparse - c_dense|` at every grid
  `<= 1e-9` (looser than the preparation's observed `~1e-15` by several
  orders of magnitude, to absorb solver/platform variation without weakening
  the claim being made — agreement of two solvers of the *same assembled
  system*, not independent physics).
* **Admissibility.** `max(0, -c_min, c_max - 1) == 0` exactly required from
  `n=16` upward (matches the preparation's own finding); a non-zero value at
  `n=8` is expected and reported, not treated as a failure of the *n=8* run
  in isolation.
* **Centre-point analytic agreement (`ANALYTIC_REL_TOL`).** Determined
  *after* running the production assembly once at `n=64` and observing the
  actual centre-point relative error (§2's table gives the *max-abs* error,
  not the centre-point error specifically, so this number is not yet known
  and is not preregistered blind) — recorded in the evidence document with
  the same disclosure `thermal/conduction1d/validation.py` already gives for
  its own post-hoc-informed thresholds.

## 9. Architecture fitness criteria

* Zero or near-zero `src/engcore/scientific/` diff (§7).
* `VariableBulkLinkage` and `require_admission` each gain at least one real
  `src/engcore/domains/fluids/` caller, honestly — not a decorative one built
  only to generate evidence (§F4/§F8 predictions above; if either genuinely
  does not fit, that is reported, not forced).
* Model, Realization-adjacent identity (two independent `ScientificSolver`
  adapters over one assembly), and Solver stay three distinct concepts in the
  code, matching `thermal/conduction1d`'s separation.
* `architecture-falsifier` finds no unresolved `BLOCKER` against the five
  named attacks in the governing mission (§F11).

## 10. Stop conditions

* Stop and report a blocker, rather than build around it, if the field output
  genuinely cannot be expressed with `ScientificVariable` +
  `VariableBulkLinkage` + `ScientificDataReference` at all (not merely
  imperfectly — completely).
* Stop and report a blocker if `BoundaryCondition` cannot even *label* the
  four sides consistently with the existing `_require_condition_dimensions`
  invariant (i.e., if the Dirichlet value cannot be declared without a Core
  change) — predicted not to happen, since `thermal/conduction1d` already
  demonstrates the pattern.
* Stop before claiming reproduction of the preparation's convergence numbers
  if the production assembly's `n=64` observed order falls outside
  `0.90 +/- 0.02` — that would mean the production code does not implement
  the probed scheme, and the discrepancy must be found and fixed (in the
  production code, never by re-tuning the target).

## 11. Reversal conditions

* If extending the sparse-vs-dense comparison to `n=128` shows the
  preparation's cost-gap trend *reversing* (dense becoming competitive) —
  this would falsify §3's execution-path grounding and is not expected but is
  checked if convenient, not required at production scale (this milestone
  does not need `n=128` to satisfy §2's frozen ladder).
* If the falsifier (§F11) finds a `BLOCKER` in any of the five named attacks
  that cannot be closed by documentation alone, the affected claim is
  downgraded in the evidence document rather than argued past.

## 12. Tests

Targeted (`pytest tests/domains/fluids/test_transport2d*.py -q`), Foundation
targeted (`pytest tests/test_min_cross_domain_foundation.py -q`, to confirm
this milestone has not broken the Foundation's own tests), then FAST
(`pytest tests/ -m "not expensive" -q`). **FULL is explicitly not run** — it
is reserved for the later integration phase, per the governing mission, and
running it here would waste resources concurrently with the sibling Planner
track's own testing.

## 13. Git

This document is committed alone as the first commit beyond the cherry-picked
preparation evidence, with message "Preregister real fluid PDE domain".
Implementation, tests and the evidence document follow in separate,
separately-described commits, per the governing mission's preference for
multiple commits over one giant commit.
