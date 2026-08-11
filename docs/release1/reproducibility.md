# Release 1 reproducibility

Release 1 reproducibility is deterministic software replay with explicit
scientific and environment attribution. It is not independent scientific
replication or physical validation.

## Serialization and identities

Public Core and D0–D3 records that support persistence serialize with an
explicit `/1` schema and deterministic field/key ordering. Unknown or changed
schemas fail closed. Identity-bearing records use canonical JSON inputs and
declared digest semantics; output paths, wall-clock time, hostname, username,
and mutable globals do not enter scientific identities.

Package version, scientific schema, model version, and solver version are
separate:

- package/distribution version: `engineering-ai-core` `1.0.0`;
- record schemas: for example `scientific_result/1`,
  `design_result_binding/1`, `design_evaluation/1`, and
  `design_memory_record/1`;
- domain model/solver versions: recorded by each domain result and provenance;
- release reference envelope: `engcore.release1_cycle/1`.

Changing package version does not silently rename scientific schemas or domain
model/solver identities.

## Artifact hashing

The release-owned cycle artifact is
`artifacts/release1/reference/release1-cycle.json`. It records the reference
module SHA-256, Public V1 manifest identity, scientific configuration,
environment metadata, and complete typed cycle graph. The package/release
inventory at `artifacts/release1/package-manifest.json` records SHA-256 and byte
size for curated docs/examples/reference content and, where built, wheel and
sdist files.

SHA-256 here is a deterministic change/equality check. Release 1 does not
implement signing, a trusted timestamp, key management, or a chain of custody;
therefore these hashes are not claims of cryptographic authenticity.

## Replay procedure

`run_release1_cycle` loads the frozen D7 `loop.py` only through a caller-supplied
explicit file path, builds exactly one bounded cycle, writes canonical JSON
atomically to a caller-controlled path, discards the loaded module, reloads
the artifact through typed parsers, rederives the reference graph, and compares
it exactly.

Example 04 performs two fresh executions with the same release commit and
reference. It checks byte equality and cycle identity, then separately reloads
and revalidates. Installed-wheel verification runs from outside the checkout
and rejects an `engcore` import resolved under the source tree. The frozen
reference file is read by path; it is not added to Public V1 or `sys.path`.

## Environment recording

The cycle environment section uses sorted keys and records:

- distribution name and installed version;
- caller-supplied release Git commit;
- Python implementation, semantic version, and full version string;
- operating-system, platform version/release, machine, and architecture;
- exact installed versions of `numpy`, `scipy`, `scikit-learn`, and `pint`.

Domain results separately record model, solver, typed inputs, assumptions,
tolerances, validation, uncertainty, and other domain provenance. Environment
recording supplements rather than replaces scientific attribution.

## What deterministic replay proves

It proves that, under the recorded software/reference/dependency environment
and identical declared inputs, the implemented canonicalization, typed
parsers, validation graph, synthetic decision, selected execution, evidence
return, and identities reproduce exactly.

It does not prove that the synthetic D7 system represents nature, that a domain
model is physically valid outside its evidence envelope, that results are
safe/certified, that a discovery process converges, that another
implementation independently replicates the science, or that an artifact came
from a trusted signer.

Numerical dependencies and platforms may differ outside the exact recorded
environment. Domain-specific floating-point tolerances remain domain-owned;
Release 1 does not replace them with a global reproducibility tolerance.
