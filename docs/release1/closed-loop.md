# Closed Scientific Discovery Loop V0.1

> **REFERENCE SYNTHETIC SCIENTIFIC SYSTEM**
>
> **NOT PHYSICAL-WORLD VALIDATION**

The Release 1 loop is a finite D7-derived integration over the frozen D4
synthetic analytic reference. It executes real typed software and creates real
`ScientificResult`, `ResultBinding`, `DesignEvaluation`, and Design Memory
records. It is not experimentally validated physics, autonomous discovery, or
real-world discovery.

## Exact supported sequence

```text
initial typed Study (Generation 0)
→ LAB synthetic analytic execution
→ ScientificResult + exact ResultBinding + eligible DesignEvaluation
→ attributable D3 memory observation
→ frozen D4/D5/D6/D7 reference compatibility, successor, and decision
→ one selected typed Study (Generation 1)
→ LAB synthetic analytic execution
→ new ScientificResult + exact ResultBinding + eligible DesignEvaluation
→ returned D3 memory observation
→ save, reload, rederive, and compare
→ STOP before Generation 2
```

The decision policy is exactly
`d7-information-per-compute-lexicographic@0.1` over a closed fixture-local
option set. Its signal table, cost proxies, thresholds, identities, tie-break,
and selected option are reference policy, not a universal acquisition
function or public default.

## Typed boundary

The initial and selected Lab observations validate the exact Candidate, Twin,
design-space, Study/problem, model, solver, result binding, eligibility,
physics scope, execution semantics, and memory entry. A substituted identity
or dictionary-only evidence source is rejected.

Mind's decision and prediction identities are recorded as provenance. They do
not become evidence on the unevaluated child. Only the selected execution's
new attributable result is returned as new evidence.

## Execute and replay

From an environment containing the installed wheel and a Release 1 bundle:

```powershell
python examples\release1\04_closed_loop.py `
  --reference experiments\design_d7\loop.py `
  --output-dir release1-example-output `
  --release-commit YOUR_RELEASE_COMMIT
```

Example 04 uses the documented release-internal `engcore.release1_cycle` seam;
it is the only curated example permitted to do so. It loads the frozen D7
module by explicit file path without adding the repository to `sys.path`,
writes only to the caller's output directory, runs twice, compares artifact
bytes and identities, and reloads/revalidates the first artifact.

The authoritative release-owned reference is
`artifacts/release1/reference/release1-cycle.json`, schema
`engcore.release1_cycle/1`. Its D7 source digest and Public V1 manifest identity
are checked during revalidation.

## Stop condition and interpretation

`generation_2_executed` must be exactly `false`. The selected Generation 1
memory entry is exposed as a possible source for a future separately
authorized cycle, but Release 1 does not execute it.

Deterministic replay proves that the implemented software, supplied reference,
scientific inputs, and recorded environment re-create the same identity-bearing
graph. It does not prove independent replication, convergence, physical
validity, safety, or general discovery capability.
