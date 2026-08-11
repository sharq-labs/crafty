# Authoritative Release 1 checklist

Candidate product: **Scientific Discovery Platform — Release 1**

Distribution: `engineering-ai-core` `1.0.0`

Integration basis: `d9679e6d3e61f9b7376f4e96a0cd772d22af6475`

Tag creation: **PENDING FINAL AUTHORIZATION**

`PASS` in this checklist means the linked executable command, artifact, or
tracked-content comparison was run against the final candidate worktree. A
historical report alone is not sufficient evidence. Exact final test counts,
artifact hashes, and the candidate commit are recorded in
`artifacts/release1/package-manifest.json` and the implementation handoff.

## Verification commands

| Evidence ID | Executable evidence |
|---|---|
| DOC | `py -3.14 -m pytest -q tests/test_release1_documentation.py` |
| EXAMPLES | `py -3.14 -m pytest -q tests/test_release1_examples.py` |
| PUBLIC | `py -3.14 -m pytest -q tests/test_release1_public_api.py` |
| CYCLE | `py -3.14 -m pytest -q tests/test_release1_cycle.py` |
| BUILD | `py -3.14 -m build` plus wheel/sdist hash and content inspection in the package manifest |
| INSTALLED | fresh isolated environment; installed Public V1 smoke and all four examples executed from outside the checkout with source fallback rejected |
| REPLAY | installed-wheel cycle generation, fresh-process reload/rederivation, exact identity comparison, and `generation_2_executed == false` |
| TARGETED | affected Release 1, D1, D3–D7, Electrical DC, multirotor, packaging, docs, and example tests |
| FULL | `py -3.14 -m pytest -q` exactly once after all earlier gates pass |
| FROZEN | `git diff --quiet d9679e6d3e61f9b7376f4e96a0cd772d22af6475 -- docs/design-d[0-7]* experiments/design_d[0-7] src/engcore/design/d4_recombination.py src/engcore/design/d5_generation.py src/engcore/design/d6_next_experiment.py` |

## Preregistered V1 gates

| Gate | Status | Executable/artifact evidence |
|---|---|---|
| V1-A1 — Frozen semantics | PASS | FROZEN; frozen D0–D7 tracked paths have no diff from the integration basis. |
| V1-A2 — Lab enumeration | PASS | PUBLIC; `docs/release1/architecture.md`, `public-api.md`, `limitations.md`; domain focused tests in TARGETED. |
| V1-A3 — Mind enumeration | PASS | Example 03 uses Public D3 only; Example 04 labels the D4–D7 seam synthetic/reference-internal; EXAMPLES and DOC. |
| V1-A4 — Typed handoff | PASS | CYCLE substitution/adversarial tests reject wrong Candidate, Twin, binding, Study, model, solver, scope, and dictionary-only evidence. |
| V1-A5 — Bounded workflow | PASS | Example 04, CYCLE, and REPLAY complete one evidence-return cycle with Generation 2 false. |
| V1-A6 — Public API | PASS | PUBLIC and INSTALLED import the exact manifest and reject source/experiment leakage. |
| V1-A7 — Deterministic replay | PASS | CYCLE and REPLAY compare two fresh bytes, typed reload, rederivation, returned identities, and artifact hashes. |
| V1-A8 — Accurate documentation | PASS | DOC, EXAMPLES, and INSTALLED execute/validate the Quick Start and four curated examples; README is the Release 1 landing page. |
| V1-A9 — Explicit limits | PASS | DOC verifies the semantic non-equivalences, limitations inventory, synthetic labels, and absence of affirmative prohibited claims. |
| V1-A10 — Full regression | PASS | FULL, run once after all earlier gates. Exact result is recorded in the package manifest/handoff. |
| V1-A11 — No policy leakage | PASS | PUBLIC manifest identity unchanged; AST import gate confines release internals to Example 04; configuration inventory keeps domain/fixture policy local. |
| V1-A12 — Complete release contents | PASS | `artifacts/release1/package-manifest.json` content hashes cover README, nine authoritative docs, four examples, tests, and reference artifact. |
| V1-A13 — Build/install integrity | PASS | BUILD, INSTALLED, package metadata/content inspection, installed version check, all examples, and installed replay. |

## Completed Release 1 implementation gate families

These gate families map the implemented R1/R2/R3/R6 slices to executable
evidence. Their implementation checkpoints are `964c6a6e...` (R1 packaging)
and `d9679e6d...` (R2/R3/R6 integration); current gates re-execute rather than
trust those commits' prose.

### R1 — Public package/API

| Gate | Status | Evidence |
|---|---|---|
| R1-A1 — Distribution metadata/version synchronized | PASS | DOC, PUBLIC, BUILD, INSTALLED |
| R1-A2 — Public V1 allowlist exact and importable | PASS | PUBLIC, INSTALLED |
| R1-A3 — Legacy `DesignSpace` ambiguity excluded | PASS | PUBLIC installed smoke |
| R1-A4 — Experiment-only D4–D7 symbols excluded | PASS | PUBLIC and Example import AST gate |
| R1-A5 — Wheel/sdist contents and dependencies declared | PASS | BUILD, INSTALLED, package manifest |

### R2 — Frozen Lab/Mind boundary

| Gate | Status | Evidence |
|---|---|---|
| R2-A1 — Lab→Mind uses Candidate + eligible Evaluation + exact scope | PASS | CYCLE |
| R2-A2 — Result provenance contains exact ResultBinding | PASS | Examples 02/04, CYCLE |
| R2-A3 — Mind→Lab carries exact Candidate + full Twin + Study identities | PASS | CYCLE |
| R2-A4 — Candidate/Twin/design-space/Study/model/solver/scope substitution fails closed | PASS | CYCLE and Example 02 |
| R2-A5 — Prediction/decision provenance cannot become evidence | PASS | CYCLE adversarial tests |

### R3 — Bounded orchestration

| Gate | Status | Evidence |
|---|---|---|
| R3-A1 — Initial Study executes and returns attributable evidence | PASS | Example 04, CYCLE |
| R3-A2 — One deterministic Mind selection yields one typed next Study | PASS | Example 04, CYCLE |
| R3-A3 — Selected execution returns new result/evaluation/memory entry | PASS | Example 04, CYCLE |
| R3-A4 — Runner stops before Generation 2 | PASS | Example 04, CYCLE, REPLAY |
| R3-A5 — D7 is loaded by explicit read-only path and remains release-internal | PASS | DOC, INSTALLED, PUBLIC |

### R6 — Replay/reproducibility

| Gate | Status | Evidence |
|---|---|---|
| R6-A1 — Schema-bearing canonical serialization and identities preserved | PASS | CYCLE and targeted serialization tests |
| R6-A2 — Two fresh runs are byte/identity identical | PASS | Example 04 and CYCLE |
| R6-A3 — Fresh process reloads, rederives, and compares the typed graph | PASS | REPLAY and CYCLE |
| R6-A4 — Installed wheel runs without source checkout fallback | PASS | INSTALLED |
| R6-A5 — Environment/dependency and artifact hashes recorded | PASS | Reference artifact and package manifest |
| R6-A6 — Tampered or mismatched record fails closed | PASS | CYCLE adversarial tests |

## Final RF gates

| Gate | Status | Evidence |
|---|---|---|
| RF-A1 — Authoritative Release 1 documentation set exists | PASS | DOC; all nine `docs/release1/` paths |
| RF-A2 — Architecture documentation matches implemented system | PASS | DOC, CYCLE, PUBLIC |
| RF-A3 — Scientific semantic non-equivalences are explicit | PASS | DOC semantic phrase gate |
| RF-A4 — Quick Start works from installed package | PASS | INSTALLED |
| RF-A5 — Example 01 real Electrical Lab execution passes | PASS | EXAMPLES, INSTALLED |
| RF-A6 — Example 02 attributable Twin/evaluation passes | PASS | EXAMPLES, INSTALLED |
| RF-A7 — Example 03 Mind memory reference passes | PASS | EXAMPLES, INSTALLED |
| RF-A8 — Example 04 bounded closed loop/replay passes | PASS | EXAMPLES, INSTALLED, REPLAY |
| RF-A9 — Example 04 identifies synthetic reference/no physical validation | PASS | DOC and EXAMPLES output assertions |
| RF-A10 — Four examples run from isolated installed wheel | PASS | INSTALLED |
| RF-A11 — Public API docs derive from frozen manifest | PASS | DOC manifest-summary drift test; PUBLIC identity unchanged |
| RF-A12 — Configuration inventory avoids genericized domain policy | PASS | DOC configuration classification gate |
| RF-A13 — Reproducibility docs match replay guarantees | PASS | DOC, CYCLE, REPLAY |
| RF-A14 — Limitations/prohibited claims explicit | PASS | DOC limitations and claim gates |
| RF-A15 — Checklist contains V1 + R1/R2/R3/R6 evidence | PASS | DOC checklist ID/evidence gate |
| RF-A16 — Package/release inventory deterministic and complete | PASS | DOC content hash test and BUILD hashes |
| RF-A17 — Frozen D0–D7 semantics/artifacts unchanged | PASS | FROZEN |
| RF-A18 — Full regression passes | PASS | FULL; exact result in final manifest/handoff |
| RF-A19 — No `v1.0.0` tag created | PASS | `git tag --list v1.0.0` returns no tag |

No new scientific model, domain, optimizer, UQ method, Mind engine, or
Generation 2 behavior is authorized by this checklist. Final tag creation is a
separate explicit action after review of the exact eligible commit.
