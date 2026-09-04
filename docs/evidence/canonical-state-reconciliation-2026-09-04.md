# Canonical state reconciliation — 2026-09-04

Read-only reconciliation performed before `COMPOSITE-SYSTEM0`, per that
milestone's §4. No production code was read or changed to produce this note.
It records measured repository facts and the drift found, so that the next
milestone starts from verified state rather than from a stale summary.

## Verified canonical state

| Fact | Value |
|---|---|
| Most advanced verified commit | `f1ed553a43c44e5f93ffb76a04e09db30c7d12fe` (`api-mcp-v0`) |
| Authoritative regression at that commit | FULL **2306 passed / 0 failed / 0 errors** |
| Ancestry | clean descendant of `cloud/crafty-post-coupling-relocation` @ `846c75c` |
| Working tree | clean |

The FULL figure was re-measured independently in a single uninterrupted
process (797 s) rather than accepted from the milestone report, and agrees
with that milestone's own two-tier measurement (2302 `not campaign` + 4
`campaign`). An earlier single-process figure of 2305 predates the final
admission-order probe and is not the current tree.

## Drift found

**D-1 — canonicalization lag (corrected by this reconciliation).**
`API-MCP-V0` completed, was verified and pushed, but was never published as a
`cloud/*` baseline, because that milestone's final-git section asked only for
a commit. The latest baseline was therefore one milestone behind the latest
verified state. Corrected: `cloud/crafty-post-api-mcp` now points at
`f1ed553`. No historical baseline was moved.

**D-2 — `main` is far behind.** `main` @ `03c30f6` is an ancestor of
`f1ed553`, so there is no divergence, but it trails by 48 commits and roughly
eleven milestones. Left as-is deliberately: this repository advances by
`cloud/*` evidence baselines, not by `main`.

**D-3 — three retained side branches are not in the lineage.**
`fluid-pde-preparation`, `fluid-thermal-preparation` and
`temporal-semantics-stress` are docs/experiments-only outputs of decision
cycles, deliberately never merged. Not a defect; recorded so their absence
from the lineage is not later mistaken for lost work.

**D-4 — documented next milestone differs from the one now directed.**
`CRAFTY_MASTER_CONTEXT.md` §69.5 records the next milestone as
`MIN-FOUNDATION-PDE`, with a binding entry condition (a real consumer, not a
probe). The owner has instead directed `COMPOSITE-SYSTEM0`. That is a
legitimate re-prioritisation, recorded here so the two do not silently
contradict. `MIN-FOUNDATION-PDE` remains open with its entry condition
unchanged; `COMPOSITE-SYSTEM0` does not satisfy or supersede it.

## Scoping facts relevant to COMPOSITE-SYSTEM0

Measured, not assumed, and recorded because they materially change what that
milestone can honestly claim is *forced*:

* `src/engcore/domains/electrical/material.py` (662 lines) already provides a
  typed material-property mechanism: `LINEAR_TCR_MODEL` as a real
  `ScientificModelDefinition`, `LINEAR_TCR_REALIZATION`, a dedicated
  `ResistancePropertySolver`, the capability
  `electrical:temperature_dependent_resistance`, an explicit validity domain
  (200–450 K) and `assess_resistance_validity`. Material-dependent property
  evaluation is therefore **not** a greenfield gap and must not be rebuilt.
* That model is parameterised by `reference_resistance` and
  `temperature_coefficient` — **not** by resistivity, length or area. So
  `R(T) = rho(T)·L/A` is **not** currently expressible: neither geometry nor
  resistivity has a home.
* Material *identity* (copper vs aluminium selecting a property set) does not
  exist today; a caller supplies a reference resistance numerically.
* Closed-loop R(T) coupling already exists and is exercised
  (`systems/electrothermal/`, `coupling/`). It must be reused, not reinvented.

The open question `COMPOSITE-SYSTEM0` must answer honestly is therefore
narrower than it first appears: whether component *instance* identity is
forced beyond what existing per-problem identity already provides, and
whether material identity plus geometry force new semantics — not whether
Crafty can evaluate a temperature-dependent property, which it already can.
