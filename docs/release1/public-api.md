# Public V1 API

The authoritative support contract is the runtime object
`engcore.release1_api.PUBLIC_V1_MANIFEST`. This document does not maintain a
second symbol allowlist. The summary below is mechanically derived from that
manifest and guarded by `tests/test_release1_documentation.py`.

<!-- PUBLIC_V1_MANIFEST_SUMMARY:BEGIN -->
```json
{
  "category_symbol_counts": {
    "lab_v1": 47,
    "mind_v1": 15,
    "proven_domains_and_systems": 138,
    "scientific_core": 75
  },
  "distribution": {
    "name": "engineering-ai-core",
    "requires_python": ">=3.11",
    "status": "release-1-preparation",
    "version": "1.0.0"
  },
  "identity_sha256": "f4bd71ced1cc6e68d074dbd10a1c074ac78a112be8a9ad0b6250eb1571715163",
  "manifest_schema": "engcore.public_v1_manifest/1",
  "namespace_symbol_counts": {
    "engcore": 1,
    "engcore.design": 49,
    "engcore.domains.electrical.dc": 30,
    "engcore.domains.fluids.aerodynamics": 2,
    "engcore.domains.kinetics.cstr": 64,
    "engcore.domains.thermal.conduction1d": 33,
    "engcore.release1_api": 1,
    "engcore.scientific": 86,
    "engcore.systems.aerospace.multirotor": 9
  },
  "symbol_count": 275
}
```
<!-- PUBLIC_V1_MANIFEST_SUMMARY:END -->

The SHA-256 identity is over canonical JSON (`sort_keys=True`, compact
separators, UTF-8) for the manifest value. It detects drift; it is not a
signature or authenticity claim.

## Manifest schema and categories

Schema `engcore.public_v1_manifest/1` has three top-level fields:

- `schema` identifies the manifest representation;
- `distribution` records package name/version, Python floor, and preparation
  status;
- `categories` maps a support category to module names and exact exported
  symbol tuples.

The categories are `scientific_core`, `lab_v1`, `mind_v1`, and
`proven_domains_and_systems`. A fully qualified `(module, symbol)` entry is the
unit of support. Categories may share a module but never the same fully
qualified symbol.

Inspect the exact current allowlist rather than copying it:

```python
from engcore.release1_api import PUBLIC_V1_MANIFEST

for category, modules in PUBLIC_V1_MANIFEST["categories"].items():
    for module_name, symbols in modules.items():
        print(category, module_name, symbols)
```

## Supported import policy

Use the manifest's direct namespaced routes. Key namespaces are
`engcore.scientific`, `engcore.design`,
`engcore.domains.electrical.dc`,
`engcore.domains.thermal.conduction1d`,
`engcore.domains.kinetics.cstr`,
`engcore.domains.fluids.aerodynamics`, and
`engcore.systems.aerospace.multirotor`.

The supported typed design-space name is
`engcore.design.DesignSpace`. The historical untyped optimizer object formerly
reachable through package-root/legacy modules is not Public V1; the package
root deliberately does not alias it to the typed contract.

Wildcard exports and simple importability outside the manifest do not confer
support. Installed-wheel verification imports every allowlisted symbol and
checks the distribution version and source-tree exclusion.

## Internal and experiment-only modules

Release-internal implementation includes private canonicalization/digest
helpers, registry storage, environment-manifest construction, report layout,
and `engcore.release1_cycle`. The latter is a narrow documented
release-reference seam used only by Example 04; it is not Public V1.

Experiment-only modules include `engcore.design.d4_recombination`,
`engcore.design.d5_generation`, `engcore.design.d6_next_experiment`, and
`experiments.design_d7`. Their synthetic constants, policies, identities,
signal/cost tables, runners, and checkpoint records are not general public
defaults even when directly importable from a checkout.

Public V1 expansion is out of scope for this preparation slice. The manifest
identity must remain unchanged unless an explicitly authorized API change is
made.
