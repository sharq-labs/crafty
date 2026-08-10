# Scientific Discovery Platform - Release 1 preparation

Status: **PRE-RELEASE 1 - not yet shipped or tagged**

Target distribution: `engineering-ai-core` `1.0.0`

The repository packages the already demonstrated system as:

```text
Lab V1
+ Mind V1
+ Stable Scientific Core
+ Closed Scientific Discovery Loop V0.1
```

Release 1 preparation is product, integration, stability, documentation, and
packaging work over frozen scientific behavior. It is not a new discovery
milestone.

## Current capability

### Stable Scientific Core

The domain-neutral Core provides typed units and values, scientific problems,
model and validity contracts, solver protocols and registries, validation,
uncertainty representation, provenance, ScientificResult, ScientificTwin,
Study/evaluation records, and deterministic schema-bearing serialization.

The Core does not invent numerical methods. Proven adapters bind established
numerical libraries and explicit domain semantics to those contracts.

### Lab V1

Lab V1 declares and executes bounded scientific studies and produces
attributable results and evaluations. Its supported surface includes:

- ScientificTwin, ScientificProblem, and ScientificExperiment;
- typed design spaces, candidates, generation and populations;
- scientific models, solver execution, validation and provenance;
- ScientificResult, ResultBinding and DesignEvaluation;
- honest UNKNOWN/STANDARD/INTERVAL uncertainty records;
- unit-checked objective projection and declared fidelity selection;
- proven electrical DC, normalized 1D conduction, non-isothermal CSTR,
  rotor-hover, and multirotor reference adapters within their documented
  envelopes.

### Mind V1

Mind V1 is a conservative capability demonstrated by the frozen D3-D7 work:

- attributable, scope-bound scientific design memory;
- controlled compatibility/recombination in the synthetic reference;
- deterministic successor generation and exact lineage;
- deterministic next-experiment selection, including one fixture-local
  information-per-compute example;
- closed return of a new result, binding, evaluation and memory observation;
- deterministic semantic checkpoint replay.

This is one bounded Generation 0 to Generation 1 demonstration. It is not a
general Mind engine or an autonomous repeated loop.

### Closed Scientific Discovery Loop V0.1

The frozen D7 evidence demonstrates this exact finite path:

```text
scientific evidence
-> attributable memory
-> compatibility/recombination
-> successor generation
-> next-experiment decision
-> selected scientific execution
-> new ScientificResult and DesignEvaluation
-> attributable memory return
-> STOP
```

Release 1 does not execute Generation 2.

## Public V1 API

The machine-inspectable support contract is
`engcore.release1_api.PUBLIC_V1_MANIFEST`. It partitions supported symbols into
Scientific Core, Lab V1, Mind V1, and proven domain/system namespaces.

Canonical typed imports are namespaced:

```python
from engcore.scientific import Quantity, ScientificProblem, ScientificResult
from engcore.design import DesignSpace, DesignCandidate, DesignEvaluation
from engcore.domains.electrical.dc import DCCircuit, solve_circuit
```

The package root intentionally does not export `DesignSpace`. The historical
untyped optimizer representation remains internally available from
`engcore.models`, while the only supported V1 meaning is
`engcore.design.DesignSpace`.

D4-D7 policies, signal tables, synthetic constants, runners, checkpoint
envelopes, and loop-local objects are experiment-only. Importability of an
internal module is not a Public V1 support promise.

## Build and installation

Release candidates are built from the repository root:

```powershell
python -m pip install build
python -m build
python -m pip install dist/engineering_ai_core-1.0.0-py3-none-any.whl
```

The package requires Python `>=3.11` and the runtime dependencies declared in
`pyproject.toml`. Release acceptance uses a fresh isolated environment and the
built wheel, with the checkout excluded from import resolution.

## Scientific semantics

The public contracts preserve these distinctions:

- Candidate is not ScientificTwin;
- ScientificTwin is not Study;
- Study is not ScientificResult;
- ScientificResult is not memory;
- prediction is not evidence;
- decision is not truth;
- target `FAIL` is not scientific invalidity;
- compatibility is not scientific validity;
- reported uncertainty is not computed uncertainty;
- selected is not automatically valid, feasible, safe, optimal, or true.

Invalid objects, schemas, scopes, result bindings, and evaluation attribution
fail closed through the existing typed errors. Packaging does not introduce
silent fallback behavior.

## Explicit Release 1 limits

Release 1 does **not** claim or introduce:

- autonomous or general scientific discovery;
- repeated-loop convergence or Generation 2+;
- general scientific intelligence or general optimization;
- a general/real UQ framework, Bayesian optimization, BoTorch, or surrogate
  optimization;
- CFD, FEA, new physics domains, or broad multi-fidelity execution;
- PostgreSQL, S3, Redis, queues, distributed workers, or cloud deployment;
- an LLM/AI provider, agentic interface, UI, or web API.

Repository-local deterministic artifacts are sufficient for this release.
Future persistence, orchestration, service, and AI architecture remains
deliberately unresolved.

## Release status and evidence

The closed preparation plan is
[`docs/release-1-preparation-prereg.md`](docs/release-1-preparation-prereg.md).
Frozen D0-D7 documents and artifacts remain the scientific evidence basis.
The `v1.0.0` tag must not be created until every registered Release 1 gate has
passed on the exact release commit.
