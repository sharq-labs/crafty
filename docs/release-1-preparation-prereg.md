# Release 1 Preparation preregistration

Status: **CLOSED PREREGISTRATION / NOT IMPLEMENTED**

Release-readiness plan ID: `RELEASE-1-PREPARATION`

Product name: **Scientific Discovery Platform - Release 1**

## Frozen inspection basis

This preregistration was written against the following checkpoints:

- D7 preregistration: `86f8b4879a7e3da4839d53b209f51f09e55a742b`;
- D7 implementation: `bb2dc415fa2c71f53326a2a70f334325cb46180a`;
- D7 freeze and inspection HEAD: `8f5203634a26e536660c532cd6dc728d51709118`.

D0-D7 scientific semantics, preregistrations, freezes, implementation evidence,
and frozen artifacts are inputs to Release 1 Preparation, not editable Release
1 work products. This document is the only preregistration artifact. It adds no
implementation, test, tag, branch movement, database, service, or deployment.

## Primary release question and decision rule

The primary question is:

> Can the frozen Lab V1 + Mind V1 capabilities be exposed as one stable,
> documented, reproducible Release 1 without changing their frozen scientific
> meaning?

The preregistered answer is **YES only if every V1-A1 through V1-A13 gate
passes**. A working demonstration alone is insufficient. Any semantic rewrite
of D0-D7, unverifiable public claim, ambiguous supported import, non-replayable
reference artifact, or unbuildable package makes the release **NOT READY**.

Release 1 is productization, integration, documentation, packaging, and
stability work. It is not D8 and does not authorize new discovery science.

## Exact product and maturity definition

Release 1 is exactly:

```text
Scientific Discovery Platform - Release 1
= Lab V1
+ Mind V1
+ Stable Scientific Core
+ Closed Scientific Discovery Loop V0.1
```

The maturity claim is one bounded, deterministic, attributable, replayable
closed scientific-discovery cycle. `Lab V1` and `Mind V1` are product surfaces
over already demonstrated contracts and experiments; they are not claims that
every scientific domain or every discovery policy is general.

The following non-equivalences are release-level semantics:

- Candidate != ScientificTwin;
- ScientificTwin != Study;
- Study != ScientificResult;
- ScientificResult != memory;
- prediction != evidence;
- decision != truth;
- target `FAIL` != scientific invalidity;
- selected != valid, feasible, safe, optimal, adequate, converged, or true;
- compatibility != scientific validity;
- reported uncertainty != computed uncertainty;
- deterministic replay != independent scientific replication.

## Lab V1: exact supported capability claim

Lab V1 exposes the following capabilities, and no broader ones:

1. **Typed scientific declarations:** unit-bearing `Quantity` values; integer,
   Boolean, and categorical scientific values; variables, parameters,
   objectives, constraints, initial/boundary conditions, model references, and
   uncertainty requirements.
2. **ScientificTwin V0.1:** immutable, versioned system declarations with typed
   data, model references, assumptions, parent references, and attributable
   evidence references. A Twin is not a solver, result, posterior, or truth
   claim.
3. **Problem and Study contracts:** `ScientificProblem` is the domain-neutral
   task declaration. `ScientificExperiment`, with `ExperimentBudget` and
   ordered `ScientificEvaluation` history, is the reusable Release 1 Study
   contract. D7's `LoopStudy` is not a second public Study contract.
4. **Design declarations:** typed `DesignSpace`, `DesignCandidate`, their exact
   references, deterministic population/generation contracts, and mixed
   variable sampling already proven by D0-D2.
5. **Scientific models:** model definitions, typed input/output binding,
   versioned registries, validity domains/assessments, and fail-closed missing,
   duplicate, invalid, and ambiguous-model behavior.
6. **Solvers and execution:** the `ScientificSolver` protocol, identities,
   settings, capabilities, registry selection, prepared solves, raw outputs,
   and convergence states. Lab V1 executes only through already implemented
   domain adapters or the explicitly synthetic reference fixtures; it is not a
   generic scheduler or distributed execution service.
7. **Actually demonstrated adapters:** linear resistive electrical DC,
   normalized 1D transient conduction, non-isothermal CSTR kinetics, the
   reusable rotor-hover relations, and the multirotor reference system. Each
   retains its own documented domain scope, assumptions, validation, and error
   types. Inclusion does not turn any adapter into CFD, FEA, or a general
   physics engine.
8. **ScientificResult:** typed values and units plus problem, model, solver,
   convergence, assumptions, warnings, artifacts, validation, uncertainty, and
   mandatory `ProvenanceRecord` attribution.
9. **Attributable design evidence:** producer-declared `ResultBinding` inside
   result provenance, `DesignEvaluation`, exact candidate/Twin/design-space
   checks, explicit `SelectionEligibility`, and fail-closed binding mismatch.
10. **Validation representation:** `ValidationReport`, checks, outcomes, and
    attained levels, including honest `NOT_RUN` and failure states. Lab V1
    reports only the levels an adapter's implemented checks earned.
11. **Uncertainty representation:** `UNKNOWN`, method-attributed `STANDARD`, and
    method-attributed `INTERVAL` records, plus problem-level `NONE`, `REPORTED`,
    and `QUANTIFIED` requirements. The honest default is `UNKNOWN`; these
    records are not a general UQ engine. Quantified values are claimed only
    where an existing domain workflow actually computed them.
12. **Objective projection:** exact metric lookup, unit conversion, and
    direction-preserving `ProjectedObjective` records from an attributable
    `DesignEvaluation`.
13. **Fidelity contracts:** versioned `FidelityRung`, `FidelityLadder`, and
    `FidelitySelection` declarations and validation. These describe and bind
    an actual selected rung; they do not provide automatic multi-fidelity
    execution, planning, extrapolation, or UQ.
14. **Deterministic serialization where implemented:** schema-bearing `to_dict`
    and `from_dict` records and sorted JSON through `to_json`, with unknown
    schemas rejected.

Lab V1 does not claim production job management, automatic environment
collection, physical-world validation, or support outside the explicitly
documented domain envelopes.

## Mind V1: exact supported capability claim

Mind V1 is the conservative product claim demonstrated by D3-D7:

1. attributable scientific design memory scoped by exact design-space,
   objective, context, candidate, evaluation, and result-binding identities;
2. deterministic comparison, classification, explicit retention, and archive
   behavior over eligible attributable evidence;
3. controlled, scope-bound compatibility assessment and recombination in the
   frozen D4 synthetic reference system;
4. deterministic successor-candidate/Twin generation with exact parent,
   derivation, and generation lineage in the frozen D5 reference;
5. a deterministic next-experiment decision over a closed option set in the
   frozen D6/D7 reference;
6. one explicit information-per-compute decision **example**, whose signal
   table, cost estimates, policy, and tie-breaks are fixture-local rather than
   a universal acquisition function;
7. separation of decision provenance from scientific evidence: predicted or
   inherited parent evidence is not attached to an unevaluated child as new
   evidence;
8. selected Lab execution returning a new `ScientificResult`, valid
   `ResultBinding`, eligible `DesignEvaluation`, D3 memory entry, and an
   attributable source usable by a possible next cycle;
9. deterministic semantic save/reload/revalidation of the frozen D7 reference
   checkpoint and continuation;
10. exactly one bounded Generation 0 -> Generation 1 discovery cycle, followed
    by a stop. Generation 2 is neither executed nor claimed.

Mind V1 is a demonstrated, typed reference capability. Release 1 does not
promote D4-D7's synthetic policies or object graph into a general Mind engine.

## R1 - Public package/API classification

The Release 1 support contract is an explicit allowlist. Presence in the source
tree, direct submodule importability, or historical use by a test does not make
an object Public V1.

### PUBLIC V1

1. **Scientific Core:** the names in `engcore.scientific.__all__` at the D7
   freeze: its error, unit, IR, model, solver, result, validation, uncertainty,
   provenance, Twin, experiment, optimizer-boundary, and serialization groups.
   `OptimizerAdapter`, `CandidateCodec`, `ObjectiveEncoder`, and
   `NumericSearchBackend` are only typed numeric optimizer boundaries; their
   presence is not a general-optimization claim.
2. **Generic design/discovery contracts:** the following exact allowlist from
   `engcore.design`:
   `AssessmentContext`, `GENERATION_BINDING_METADATA_KEY`,
   `CandidateGenerationBatch`, `CandidateGenerationPlan`,
   `CandidateProposal`, `DesignCandidate`, `DesignCandidateReference`,
   `DesignEvaluation`, `DesignEvaluationReference`, `DesignMemoryEntry`,
   `DesignMemoryLayerA`, `DesignMemoryPolicy`, `DesignMemoryRecord`,
   `DesignMemoryScope`, `DesignPopulation`, `DesignSpace`,
   `DesignSpaceReference`, `EntryClassification`, `ExplicitRetention`,
   `FidelityLadder`, `FidelityRung`, `FidelitySelection`,
   `GenerationStrategy`, `MixedVariableSampler`, `ParetoArchive`,
   `ProjectedObjective`, `ProposalDecision`, `ProposalGate`,
   `ProposalRejection`, `RetentionReason`, `ResultBinding`,
   `ScopedEliteArchive`, `SelectionEligibility`, `TwinMaterializer`,
   `assignment_digest`, `bind_generation_to_twin`, `classify_memory`,
   `compare_entries`, `dominates`, `generate_initial_population`,
   `generation_binding_payload`, `merge_layer_a_records`,
   `pareto_member_identities`, `project_objectives`, `reason_overlaps`,
   `require_result_binding`, `validate_generation_binding`,
   `validate_twin_generation_binding`, and `verify_layer_a_attribution`.
3. **Proven domain namespaces:** only each namespace's deliberate `__all__` at
   the D7 freeze is supported for `engcore.domains.electrical.dc`,
   `engcore.domains.thermal.conduction1d`,
   `engcore.domains.kinetics.cstr`,
   `engcore.domains.fluids.aerodynamics`, and
   `engcore.systems.aerospace.multirotor`. Their claims remain domain-local.

Direct source namespaces above remain the canonical import routes. Release 1
does not add a second facade that could diverge from them. The release API
manifest and import-smoke test must encode this allowlist exactly.

### INTERNAL

- `engcore.Variable`, the legacy root `engcore.DesignSpace`,
  `engcore.ExperimentResult`, and `engcore.SmartExperimentEngine` are legacy
  proof-of-concept compatibility names, not the Release 1 Lab/Mind API. They
  must not be silently retargeted to the typed design contracts. Any eventual
  removal or migration requires a separate compatibility decision.
- non-exported helpers, private serialization/digest functions, registry
  storage, solver assembly internals, temporary-file mechanics, report
  formatting, and white-box validation helpers;
- Release 1 example orchestration glue and environment-manifest generation.

### EXPERIMENT-ONLY

- all D4 fixture constants, identities, analytic tables/equations, D4-specific
  records, and convenience functions currently mixed into
  `engcore.design.__all__`, including the `D4*` types, `CHILD_GENERATION`,
  `COMPATIBILITY_CONTEXT_ID`, `MATERIALIZATION_SEMANTICS_ID`,
  `RECOMBINATION_OPERATOR`, `SLOT_SCHEMA_ID`, and D4 synthetic builders/runners;
- `engcore.design.d4_recombination`, `d5_generation`, and
  `d6_next_experiment` policy/fixture objects as complete modules;
- `experiments.design_d7`, including its loop, runner, policies, object graph,
  and report generation;
- K-series, multirotor milestone, benchmark, and adversarial experiment runners
  except for their separately curated public domain/system contracts.

Release implementation must stop presenting D4 names as generic wildcard
exports while preserving direct experiment-module use and frozen semantics.

### FROZEN ARTIFACT

- D0-D7 preregistrations, freeze documents, reports, result JSON, checkpoint
  bytes, expected identities, and test evidence;
- specifically the D7 checkpoint, results, and report under
  `experiments/design_d7/artifacts/` and the three checkpoint commits listed
  above.

Frozen artifacts may be read and compared. Release examples must never
overwrite them.

### FUTURE

- a generic reusable Mind planner, generic compatibility/recombination policy,
  generic next-experiment decision schema, repeated-loop controller, generic
  evidence graph, generalized physics-scope abstraction, generic no-inheritance
  validator, production persistence, service/API layer, and AI/LLM layer.

## R2 - Frozen Lab/Mind boundary

The conceptual boundary is:

```text
LAB  = executes a declared scientific Study and produces attributable results
       and evaluations.
MIND = consumes attributable evidence and decides or derives what to investigate
       next; it does not manufacture scientific evidence.
```

The minimum typed handoff uses existing objects rather than a new Core graph:

- **Lab -> Mind:** `DesignCandidate` + `DesignEvaluation` +
  `DesignMemoryScope`. The evaluation contains the complete
  `ScientificResult`; the result's provenance contains the exact
  `ResultBinding`. Admission must call `validate_candidate`, re-check the
  binding and scope, project declared objectives, and require explicit
  `ELIGIBLE` status before D3 memory admission. A result id or dictionary alone
  is not a handoff.
- **Mind -> Lab:** the selected `DesignCandidate` + full `ScientificTwin` +
  declared `ScientificProblem`/`ScientificExperiment` for reusable Lab paths,
  with the decision artifact identity retained separately as decision
  provenance. The candidate's Twin reference must match the full Twin, and the
  Study must select the domain model/solver and conditions. In the D7 reference
  only, its already frozen `LoopStudy` and decision binding supply this side of
  the handoff; they remain experiment-local.

Release-level orchestration must pass these typed objects and execute their
existing validators. It must not reconstruct the relationship using
caller-authored dictionaries. No new handoff class is preregistered. A future
class requires evidence that the existing aggregate cannot express a required
invariant.

## R3 - Minimum Release 1 orchestration

One supported, finite reference workflow is required:

```text
declared initial Study / scientific task
-> Lab execution
-> attributable DesignEvaluation
-> D3 memory admission
-> D4 compatibility/recombination reference
-> D5 successor generation reference
-> D6/D7 deterministic next-experiment selection
-> selected typed Study + Candidate + Twin
-> Lab execution
-> new ScientificResult + ResultBinding + DesignEvaluation
-> D3 evidence return and replay validation
-> STOP
```

The Release 1 runner is thin integration glue around the frozen D7
`experiment_payload` behavior. It must use a caller-supplied or temporary
output directory, verify the frozen golden artifacts read-only, emit a concise
stable result summary and environment sidecar, reload/revalidate the generated
checkpoint, and stop after the evidence return. It must not call the existing
D7 `main()` against its frozen artifact directory, duplicate the D7 evidence
graph, schedule work, retry indefinitely, or begin Generation 2.

This runner is a documented reference workflow, not a general loop API.

## R4 - Configuration findings and frozen classification

No generic configuration framework is authorized. Values are classified by
scientific ownership:

| Classification | Exact Release 1 treatment |
|---|---|
| Acceptable example fixture | D4 slot vocabulary, parent assignments, analytic objective equations, expected values, case labels; D5 proposal labels/budgets/expected lineage; D6/D7 option sets, signal tables, information-unit proxies, compute costs, target thresholds, tie-breaks, synthetic environment, IDs, and expected digests. Keep in named examples/experiments and label them synthetic; never expose them as general defaults. |
| System/domain policy | Governing model identities, units, validity envelopes, solver tolerances and integration budgets, validation thresholds, domain constraints, objective definitions, concrete fidelity-rung meaning, compatibility predicates, novelty rules, retention policy, and information/cost estimates. Keep beside the owning domain/system or frozen experiment and record the exact policy identity. |
| Release configuration | Distribution version, supported Python statement, chosen four example entry points, output directory, verify-versus-regenerate mode, read-only golden-artifact locations, release commit, and the allowlisted environment-manifest fields. Require explicit output paths; default to verification/read-only behavior. |
| Internal implementation detail | canonical JSON separators/key ordering, digest prefixes, registry storage, report layout, temporary checkpoint suffixes and atomic replace mechanics, module discovery, and test scratch paths. These are not user policy unless changing one would change a frozen identity, in which case the existing behavior remains frozen for that schema. |

Random seeds are release configuration only for examples that actually use
randomness. The D7 reference is deterministic without a random seed; adding a
decorative seed would be misleading.

## R5 - Material stability findings and required disposition

1. **Project identity is stale and contradictory.** `pyproject.toml` says
   version `0.1.0` and "Smart experiment engine proof of concept"; the root
   README presents V0.3.3; `SCIENTIFIC_CORE_VERSION` is
   `0.1.0-v0-foundation`; D7 is V0.1. Release work must separate distribution
   version `1.0.0` from preserved component/schema versions and make package
   metadata and current docs agree.
2. **The root API duplicates `DesignSpace`.** The untyped legacy
   `engcore.DesignSpace` conflicts in name and meaning with
   `engcore.design.DesignSpace`. It stays legacy/internal for Release 1; docs
   and API smoke tests use namespaced typed imports and do not silently alias
   one to the other.
3. **D4 fixture leakage exists.** `engcore.design.__all__` currently mixes
   generic D0-D3 contracts with synthetic D4 identities, policies, tables, and
   runners. Release work must make the exact Public V1 allowlist authoritative
   and remove experiment-only wildcard presentation without changing D4's
   direct module or semantics.
4. **Current documentation is not release-accurate.** The root README is about
   the older stacked optimizer, while `engcore.scientific` and its Core README
   still describe a contracts-only state even though proven domain adapters
   now exist. Current docs must replace these claims while retaining honest
   component history.
5. **Packaging is not release-proven.** There is no explicit build-system or
   build/install gate in the current `pyproject.toml`, no Release 1 API
   manifest, and no curated examples directory. Release work must specify the
   build backend/package discovery, build an sdist and wheel, install the wheel
   in a clean environment, and test imports/examples from the installed
   package rather than only through pytest's source-tree path.
6. **Serialization is strong but not release-inventoried.** Public records use
   sorted serialization and fail-closed schema checks, but Release 1 needs an
   explicit supported schema inventory and round-trip/reference tests. Package
   version `1.0.0` must not rename existing `/1` scientific schemas.
7. **Environment provenance is caller-supplied.** `ProvenanceRecord` correctly
   performs no automatic machine harvesting, and frozen D7 results may have an
   empty environment. The Release 1 runner must create a deterministic-keyed
   environment sidecar and populate caller-controlled provenance where doing
   so does not alter frozen reference identity; it must not rewrite frozen D7
   records.
8. **Fail-closed behavior must survive integration.** Existing typed errors,
   unknown uncertainty, `NOT_RUN` validation, binding checks, validity checks,
   and solver ambiguity are scientifically material. Release glue must not
   catch them broadly and continue, infer eligibility from `is_usable`, invent
   missing metadata, or overwrite evidence after a failed check.
9. **The current D7 runner writes its own frozen artifact paths.** The release
   example must call the underlying behavior with isolated paths and compare
   read-only goldens; an accidental invocation that targets frozen artifacts
   is a release blocker.
10. **Study naming needs one documented meaning.** Public Lab uses
    `ScientificExperiment` as its reusable Study record. D7's `LoopStudy` is a
    reference-local execution record and must not be documented as a competing
    general Study API.

No other cleanup is authorized merely for naming style, formatting, or code
organization.

## R6 - Replay and reproducibility requirements

1. Identity-bearing inputs use the existing canonical ordering, schema,
   digest, and exact reference rules. No timestamp, hostname, output path, or
   mutable global may enter deterministic identities.
2. Every Public V1 serialized Core and D0-D3 record retains its current `/1`
   schema. The supported inventory includes the quantity/typed-value, IR,
   model/validity, solver, result/validation/uncertainty/provenance, Twin,
   experiment/evaluation, design-space/candidate/population/generation,
   fidelity, design-evaluation/binding/objective, archive, and D3 memory schema
   families. D4-D7 schemas remain frozen artifact/experiment schemas, not
   general V1 schemas.
3. `from_dict`/`to_dict` and JSON byte round trips are tested for every Public
   V1 record that currently supports reload. Unsupported domain-specific
   reload is documented rather than simulated with pickle or lossy dicts.
4. The Release 1 reference artifact set is saved under
   `artifacts/release1/reference/`, separate from all D0-D7 goldens, and
   contains the generated checkpoint, result summary, gate summary,
   environment manifest, and SHA-256 manifest.
5. Two fresh executions with identical scientific inputs and software must
   reproduce identity-bearing JSON/checkpoint bytes and scientific identities.
   Human reports may be semantically compared if formatting is explicitly
   non-identity-bearing.
6. A fresh process reloads the saved checkpoint through the existing parser,
   revalidates its complete semantic graph, continues the selected execution,
   and produces the same returned result/evaluation/memory identities.
7. The environment sidecar records, with sorted keys: distribution name and
   version, release git commit, Python implementation and full version,
   operating-system/platform and architecture, and exact installed versions of
   `numpy`, `scipy`, `scikit-learn`, and `pint`; numerical backend identity is
   included where a claimed example depends on it. Hostname, username, secrets,
   and wall-clock time are excluded from identity material.
8. The four examples record model, solver, assumptions, tolerances, inputs,
   and artifact checksums sufficient to attribute and rerun them. Exact package
   recording supplements rather than replaces model/solver provenance.
9. Reproduction uses repository-local files and normal process memory only.
   PostgreSQL, S3, Redis, queues, and production persistence are not required.

## R7 - Required Release 1 documentation

The implementation work must produce this small, authoritative set:

1. `README.md`: current product overview, exact product equation, maturity
   claim, installation, smallest run, four examples, limitations, and links;
2. `docs/release1/architecture.md`: Stable Scientific Core, Lab, Mind,
   ScientificTwin, the typed boundary, evidence flow, ownership, and the one
   bounded sequence;
3. `docs/release1/quick-start.md`: clean installation and the smallest valid
   scientific execution, with expected output and error behavior;
4. `docs/release1/closed-loop.md`: the D7-derived reference workflow, exact
   stop condition, artifact/replay instructions, and interpretation limits;
5. `docs/release1/scientific-semantics.md`: every non-equivalence frozen above,
   especially prediction/evidence, decision/truth, and target FAIL/invalid;
6. `docs/release1/public-api.md`: the exact Public V1 allowlist, supported
   domain namespaces, legacy/internal routes, and experiment-only exclusions;
7. `docs/release1/reproducibility.md`: schemas, identity rules, environment
   manifest, artifact checksums, reload/revalidation, and known platform
   tolerances;
8. `docs/release1/limitations.md`: all excluded scientific, autonomy,
   infrastructure, AI, UI, persistence, and deployment claims;
9. `docs/release1/release-checklist.md`: V1-A1 through V1-A13, package contents,
   version synchronization, and tag criteria.

Documentation code blocks used by the quick start and four examples must be
executable or mechanically sourced from the example files where practical.

## R8 - Four curated examples

Only these four Release 1 tutorial entry points are preregistered:

1. `examples/release1/01_lab_dc.py` - the smallest electrical DC Lab run:
   construct a circuit/problem, execute the existing solver, inspect units,
   convergence, validation, uncertainty, and provenance in `ScientificResult`.
2. `examples/release1/02_twin_attributable_evaluation.py` - use the proven
   multirotor reference path to show a full `ScientificTwin`, candidate,
   producer-side `ResultBinding`, `DesignEvaluation`, eligibility, objective
   projection, and optional declared fidelity. This is an attribution example,
   not a general aerospace optimizer.
3. `examples/release1/03_mind_reference.py` - a concise wrapper over frozen
   D3 memory plus the D4/D5 compatibility/recombination and successor reference;
   print exact sources and lineage and label every equation/policy synthetic.
4. `examples/release1/04_closed_loop.py` - the D7-derived bounded workflow in an
   isolated output directory: decide, execute, return new evidence, save,
   reload, revalidate, compare the read-only golden, and stop before Generation
   2.

Electrical, thermal, kinetics, multirotor, K-series, and D0-D7 historical
experiments remain available as evidence and tests, but are not all converted
into tutorials.

## R9 - Release 1 test strategy

The release suite adds thin gates and reuses frozen tests rather than copying
all adversarial cases:

1. **Core regression:** run the existing complete repository regression once
   on the release candidate; any failure blocks V1-A10.
2. **Lab smoke:** execute one minimal successful run for each domain/system
   namespace claimed Public V1, plus one expected fail-closed case covering
   invalid binding/validity or solver selection.
3. **Mind smoke:** run frozen D3, D4, D5, and D6 focused tests and assert the
   documented memory, recombination, successor, and decision identities.
4. **Lab <-> Mind integration:** execute the exact typed handoffs and reject a
   substituted candidate, Twin, scope, result binding, or Study identity.
5. **Serialization/replay:** generate in one process, reload in a fresh process,
   revalidate, continue, and compare identity-bearing bytes and returned
   identities.
6. **Public import/API smoke:** install the wheel, import every Public V1
   allowlisted name and domain namespace, and assert no experiment-only name is
   in the public manifest/wildcard contract.
7. **Reference closed loop:** execute Example 4, require all D7 blocking and
   adversarial evidence still passes, require evidence return, and assert no
   Generation 2 execution.
8. **Documentation execution:** run the quick start and all four example files
   from the installed package in clean temporary output directories.
9. **Package build/install:** build sdist and wheel from a clean tracked tree,
   inspect contents/metadata, install the wheel in a fresh environment at the
   declared Python floor, and rerun public-import and quick-start gates.

No tests are run during this preregistration. The full regression is reserved
for the implementation release candidate.

## R10 - Version, package, and tag preregistration

The recommended technical version and tag are **`1.0.0`** and **`v1.0.0`**.
That is repository-consistent with the product label Release 1 and correctly
signals the first supported public package contract. It replaces the stale
distribution version `0.1.0`; it does not rewrite Scientific Core's historical
component label, D7 V0.1, domain versions, model/solver versions, or any
serialized `/1` schema.

Before tagging, the release candidate must have:

- synchronized distribution metadata and an importable distribution version;
- an explicit build backend and correct `src` package discovery;
- accurate name, description, README, Python requirement, runtime dependencies,
  license/metadata if present, and no undeclared runtime dependency;
- source distribution and wheel built from a clean tracked tree;
- only intended package modules plus required metadata in those artifacts;
- the Public V1 API manifest, documentation, four examples, release-owned
  reference artifacts/checksums, and release checklist;
- V1-A1 through V1-A13 all recorded PASS against the exact release commit.

Only then may an annotated tag `v1.0.0` point at that exact clean release
commit. The tag message must identify "Scientific Discovery Platform - Release
1", `Lab V1`, `Mind V1`, and `Closed Scientific Discovery Loop V0.1`. This
preregistration creates no tag and does not move `main`.

Python support begins at the existing `>=3.11` floor. Release documentation may
claim only interpreter versions on which the clean wheel/install and release
gates actually pass; untested future interpreters are not a scientific
reproducibility claim.

## D7-local architecture disposition

Default `KEEP LOCAL` is frozen for every reviewed abstraction:

| D7 abstraction | Release 1 disposition | Reason |
|---|---|---|
| `LoopPhysicsScope` | D7 experiment-local | One synthetic integrated path is insufficient evidence for a general physics-scope contract. Public Lab already has design-space, problem, model, solver, conditions, fidelity, and objective records. |
| `LoopAssessmentContext` | D7 experiment-local | Its thresholds and decision/report identities are fixture policy, not general scientific context. |
| authoritative D4 wrapper | D7 experiment-local | It resolves D4 authority for one frozen recombination fixture and must not become generic truth. |
| `LoopDecisionEvidenceBinding` | D7 experiment-local | The full graph is needed to prove D7, while the public boundary already has `ResultBinding`, `DesignEvaluation`, and D3 attribution. |
| D7 option/decision types | D7 experiment-local | Closed option set, signals, compute costs, and tie-breaks are a demonstrated decision example only. |
| checkpoint envelope | D7 experiment-local / frozen artifact | Release replay may invoke and verify it but must not present it as a general persistence format. |
| no-inheritance validator | D7 experiment-local | It protects this synthetic derivation vocabulary; broader promotion requires a second independently forced shape. |
| `LoopStudy` and return-admission records | D7 experiment-local | `ScientificExperiment` is the reusable Lab Study; D7 records retain their exact reference semantics. |

No reviewed D7 abstraction is promoted to Scientific Core or Public V1.
Release-level code may provide a thin runner and stable summary over them but
must not copy or fork their semantic graph.

## Explicit exclusions

Release 1 Preparation does not introduce or claim:

- PostgreSQL, S3, Redis, queues, Kubernetes, distributed workers, cloud
  deployment architecture, production persistence, or object-storage APIs;
- CFD, FEA, new physics domains, a general physics engine, or physical-world
  validation;
- a real/general UQ framework, BoTorch, Bayesian optimization, surrogate
  optimization, or general optimization;
- autonomous repeated discovery, an infinite loop, Generation 2+, convergence
  of a discovery process, hypothesis intelligence/engine, general scientific
  intelligence, or broad autonomous scientific discovery;
- an LLM/AI provider, agentic decision layer, prompt interface, external or
  local model selection, web application, UI, or visualization product.

PostgreSQL and S3 remain explicitly **OUT OF SCOPE**. Release artifacts are
repository-local deterministic files. Persistence architecture is deliberately
post-Release 1.

An LLM is explicitly **NOT REQUIRED**. Lab and Mind must be callable through
typed programmatic Python interfaces with no AI-provider dependency. Choice of
future external versus local/offline AI remains unresolved.

## Exact blocking acceptance gates

- **V1-A1 - Frozen semantics:** content and scientific meaning of frozen D0-D7
  contracts, policies, preregistrations, evidence, checkpoints, and artifacts
  are unchanged; Release code only composes or reads them.
- **V1-A2 - Lab enumeration:** the Lab V1 capability list in this document is
  reflected exactly in the API manifest and docs, with domain envelopes and no
  unsupported execution/UQ/fidelity claim.
- **V1-A3 - Mind enumeration:** the Mind V1 capability list is reflected
  exactly in docs/examples, with fixture-local policy labels and no generic or
  autonomous claim.
- **V1-A4 - Typed handoff:** both Lab -> Mind and Mind -> Lab paths use the exact
  typed objects and validation rules in R2; identity substitution and
  dictionary-only evidence fail closed.
- **V1-A5 - Bounded workflow:** the supported reference workflow completes one
  decision/execution/evidence-return cycle and proves it stops before
  Generation 2.
- **V1-A6 - Public API:** the installed-wheel import/API smoke test passes for
  the exact allowlist; legacy and experiment-only names are not presented as
  Public V1.
- **V1-A7 - Deterministic replay:** two fresh runs and a fresh-process reload
  reproduce the checkpoint/identity-bearing bytes and returned scientific
  identities, with recorded artifact checksums and environment manifests.
- **V1-A8 - Accurate documentation:** quick start and all four documented
  examples execute, their stated outputs/semantics match implementation, and
  stale V0.3.3/contracts-only product claims are removed from current docs.
- **V1-A9 - Explicit limits:** every excluded claim and every release-level
  semantic non-equivalence is present in current documentation.
- **V1-A10 - Full regression:** the existing complete repository suite passes
  on the exact release candidate without weakening or duplicating frozen
  adversarial tests.
- **V1-A11 - No policy leakage:** no D4-D7 synthetic identity, equation,
  threshold, signal, cost, compatibility/retention policy, or target status is
  represented as a generic public truth or default.
- **V1-A12 - Complete release contents:** package metadata, supported imports,
  docs, examples, artifacts, checksums, version synchronization, release
  checklist, exact commit, and annotated-tag criteria are completely specified
  and reviewed.
- **V1-A13 - Build/install integrity:** clean sdist and wheel builds succeed,
  wheel contents are correct, a fresh install at the declared Python floor has
  no undeclared dependency, and public imports plus the quick start pass from
  the installed artifact. This additional gate is required by the inspected
  packaging gap.

No gate may be waived by changing its expected value after seeing release test
results. A failed gate is fixed within this preregistered scope or Release 1 is
declared not ready.

## Exact allowed and forbidden claims

Release 1 may say:

> Scientific Discovery Platform - Release 1 provides Lab V1, Mind V1, a stable
> typed Scientific Core, and Closed Scientific Discovery Loop V0.1. It includes
> one demonstrated deterministic, attributable, replayable, bounded
> scientific-discovery cycle in which selected execution returns new evidence
> through `ScientificResult`, `ResultBinding`, `DesignEvaluation`, and
> attributable memory.

It may also describe the exact typed Lab contracts, the named proven domain
adapters within their envelopes, attributable memory, controlled synthetic
recombination/successor generation, and the deterministic information-per-
compute reference decision.

Release 1 must not say or imply that it provides autonomous/general scientific
discovery, repeated-loop convergence, Generation 2+, general intelligence,
general optimization, hypothesis intelligence, general/real UQ, Bayesian or
surrogate optimization, CFD, FEA, broad multi-fidelity execution, production
persistence, distributed/cloud execution, an AI/LLM product, or scientific
truth/validation beyond the recorded evidence and domain checks.

## Deliberately unresolved after Release 1

The following architecture decisions remain open and receive no placeholder
framework now: generic Mind planner and decision schema; repeated-loop control
and stopping/convergence policy; generic physics/assessment scope contracts;
generic no-inheritance/evidence-graph promotion; production database and
object storage; distributed execution; broader fidelity/UQ/optimization;
hypothesis representation; new physics domains; public service/UI; and whether
any future AI layer is external, local/offline, or absent.

## Closed preregistration and next action

This plan is CLOSED. Implementation must not expand its public claims, examples,
or acceptance model without a separately reviewed preregistration amendment.

The one recommended next action is:

> Implement R1/R5/R10 first as one Release 1 surface-and-packaging slice: create
> the exact Public V1 API manifest/import smoke, correct package metadata/build
> configuration and current README claims, and prove a clean wheel install,
> while leaving every frozen D0-D7 scientific meaning and artifact unchanged.
