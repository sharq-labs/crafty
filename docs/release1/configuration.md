# Release 1 configuration inventory

This is the deterministic Release 1 configuration audit.
No generic global configuration framework is introduced. Scientific values stay with their
owning domain/system; D4–D7 constants stay frozen reference fixtures.

## A. SCIENTIFIC DOMAIN POLICY

| Meaningful item consumed by Release 1 | Authoritative owner | Release treatment |
|---|---|---|
| Electrical DC model identities, MNA formulation, solver settings, dimensional/KCL/Ohm/source/power validation tolerances | `engcore.domains.electrical.dc` model, solver, and validation modules | Domain-owned; Example 01 records the exact settings in result provenance. Never promoted to release defaults. |
| Thermal conduction1d slab/discretization, solver identity, verification ladder, analytic tolerance, contraction criterion, and validation settings | `engcore.domains.thermal.conduction1d` | Domain-owned and versioned beside the thermal adapter. |
| Kinetics CSTR chemistry/operation/integration budgets, model/solver identity, tolerance ladder, invariant/steady-state/stationarity thresholds, and validation settings | `engcore.domains.kinetics.cstr` | Domain-owned. Integration and verification values are not global runtime tuning. |
| Rotor-hover assumptions and equations | `engcore.domains.fluids.aerodynamics` | Domain-owned reference physics with explicit input units and validity checks. |
| Multirotor design variables, topology constraint, analytic mass/endurance coefficients, target specification, objective definitions, and proposal/evaluation policy | `engcore.systems.aerospace.multirotor` | System-pack-owned analytic reference policy; not aircraft certification or a global design default. |
| D3 memory scope, objective projection, partitioner, classification tolerances, explicit retention, and cap | Caller-declared Public V1 `engcore.design` records | Scientific decision policy carried by exact identities. Example 03 declares its own policy locally. |

## B. EXPERIMENT FIXTURE

| Meaningful item consumed by Release 1 | Authoritative owner | Release treatment |
|---|---|---|
| Example 01's 12 V, 1 kΩ/3 kΩ divider and stable run ID | `examples/release1/01_lab_dc.py` | Small tutorial fixture; the domain solver/tolerances still belong to Electrical DC. |
| Examples 02–03 population counts, attempt budgets, source labels, memory contexts, and tutorial retention policy | The individual curated example | Executable reference/tutorial fixture; not a general default. |
| D4 slot vocabulary, parent assignments, synthetic analytic objective equations/values, compatibility identities and expected digests | Frozen D4 reference | Read-only synthetic fixture policy. Not Public V1 and not generalized. |
| D5 successor labels/budgets/lineage; D6/D7 closed option set, signal table, information proxy, compute costs, target thresholds, tie-break, selected option, synthetic IDs, expected identities | Frozen D5/D6/D7 reference | Read-only reference behavior loaded explicitly by Example 04. Not a universal acquisition, optimization, or discovery policy. |

## C. RELEASE CONFIGURATION

| Item | Exact Release 1 value/source | Consumer |
|---|---|---|
| Distribution name/version | `engineering-ai-core` / `1.0.0` from `src/engcore/_version.py` and `pyproject.toml` | Build metadata, manifest, docs, installed checks |
| Supported Python statement | `>=3.11` from `pyproject.toml` and `PUBLIC_V1_MANIFEST` | Package installer and docs |
| Public API contract | `engcore.release1_api.PUBLIC_V1_MANIFEST`; identity `f4bd71ced1cc6e68d074dbd10a1c074ac78a112be8a9ad0b6250eb1571715163` | API docs/import gates/replay |
| Release reference input | Caller-supplied read-only `experiments/design_d7/loop.py`; SHA-256 checked during replay | Example 04 / `engcore.release1_cycle` |
| Release reference artifact | `artifacts/release1/reference/release1-cycle.json` | Read-only replay evidence |
| Package/release inventory | `artifacts/release1/package-manifest.json` | Content/build/hash verification |
| Verification mode | Reference revalidation is read-only; Example 04 generation requires an explicit/caller-controlled output directory and never targets frozen D7 artifacts | Runner and examples |
| Example output locations | Examples 01–03 stdout only; Example 04 defaults to `./release1-example-output/` or accepts `--output-dir` | Curated examples |
| Release commit | Required CLI/input identity for formal replay; the tutorial default is explicitly non-release `release1-installed-wheel-example` | Environment record only, not scientific cycle identity |
| Environment/reproducibility fields | Distribution name/version; release commit; Python implementation/full version; OS/platform/machine/architecture; exact `numpy`, `scipy`, `scikit-learn`, `pint` versions | Release cycle sidecar fields |
| Curated entry points | Exactly `01_lab_dc.py`, `02_twin_attributable_evaluation.py`, `03_mind_reference.py`, `04_closed_loop.py` | Docs and example gates |

No random seed is configured: the four examples and D7 reference are
deterministic without randomness. Adding a decorative seed would misdescribe
the implementation.

## D. INTERNAL IMPLEMENTATION DETAIL

Canonical JSON key ordering/separators, digest prefixes, schema key checks,
registry storage, module discovery, report formatting, temporary `.tmp`
suffixes, atomic replacement, garbage collection of the explicitly loaded
reference module, and test scratch paths are internal. They are not user
scientific policy. Where such behavior contributes to an existing `/1`
identity, that behavior remains fixed for that schema rather than becoming a
generic configuration option.

## Audit conclusion

Release configuration contains packaging, artifact, verification, output, and
environment metadata only. No scientific tolerance, equation, target,
compatibility predicate, retention rule, signal, or cost was moved into a
generic release/global configuration system.
