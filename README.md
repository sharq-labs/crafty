# Scientific Discovery Platform — Release 1

Status: **PRE-RELEASE 1 — final authorization and tag pending**

Target distribution: `engineering-ai-core` `1.0.0` (Python `>=3.11`)

Scientific Discovery Platform — Release 1 comprises:

- Lab V1
- Mind V1
- Stable Scientific Core
- Closed Scientific Discovery Loop V0.1

One deterministic, attributable, replayable, bounded scientific-discovery
cycle has been demonstrated through typed Study, `ScientificResult`,
`ResultBinding`, `DesignEvaluation`, Design Memory, next-experiment selection,
execution, and evidence return.

That demonstrated cycle uses the frozen D4/D7 synthetic analytic reference
system. It is real typed software execution, but it is **not physical-world
validation** and not evidence of autonomous or repeated discovery.

## What is scientifically executed

Lab V1 executes domain-owned models through typed scientific contracts. The
proven numerical/scientific paths in Release 1 are:

- Electrical DC;
- Thermal `conduction1d`;
- Kinetics CSTR;
- rotor-hover reference physics;
- the multirotor reference system.

Each path is supported only within its documented assumptions and validation
envelope. Additional domains require their own numerical verification and
real-world validation.

The bounded closed-loop reference uses D4/D5/D6/D7 synthetic fixtures and
policies. It must not be interpreted as experimentally validated physics or
real-world discovery.

## Smallest Lab run

Build or obtain the wheel, create a clean environment, and install it:

```powershell
py -3.11 -m venv .venv-release1
.\.venv-release1\Scripts\python -m pip install --upgrade pip
.\.venv-release1\Scripts\python -m pip install dist\engineering_ai_core-1.0.0-py3-none-any.whl
.\.venv-release1\Scripts\python -c "import engcore; print(engcore.__version__)"
```

Then run the real Electrical DC tutorial from the Release 1 bundle:

```powershell
.\.venv-release1\Scripts\python examples\release1\01_lab_dc.py
```

It constructs typed quantities and a circuit/problem, executes
`ElectricalDCSolver`, and prints selected values, validation, uncertainty, and
provenance from the resulting `ScientificResult`. See the complete
[Quick Start](docs/release1/quick-start.md), including POSIX commands and the
explicit release-reference cycle.

## Four executable examples

1. [`01_lab_dc.py`](examples/release1/01_lab_dc.py) — actual Electrical DC Lab
   execution; no Mind.
2. [`02_twin_attributable_evaluation.py`](examples/release1/02_twin_attributable_evaluation.py)
   — exact Candidate/Twin/result/binding/evaluation attribution and a caught
   fail-closed mismatch.
3. [`03_mind_reference.py`](examples/release1/03_mind_reference.py) — Public V1
   D3 attributable memory, classification/retention, and scope separation.
4. [`04_closed_loop.py`](examples/release1/04_closed_loop.py) — the explicit
   release-internal D7-derived synthetic reference seam, two byte-identical
   runs, reload/revalidation, and a stop before Generation 2.

Examples print concise structured summaries and write only Example 04 output
to a caller-controlled directory. They never overwrite frozen D0–D7 artifacts.

## Public V1 API

The only support allowlist is
`engcore.release1_api.PUBLIC_V1_MANIFEST`. Canonical imports remain namespaced:

```python
from engcore.scientific import Quantity, ScientificProblem, ScientificResult
from engcore.design import DesignSpace, DesignCandidate, DesignEvaluation
from engcore.domains.electrical.dc import DCCircuit, solve_circuit
```

The package root intentionally does not export `DesignSpace`; the supported V1
meaning is `engcore.design.DesignSpace`. Importability elsewhere is not a
support promise. D4–D7 runners, policies, constants, and checkpoint records are
experiment-only; `engcore.release1_cycle` is a documented release-reference
seam, not Public V1.

The manifest identity is
`f4bd71ced1cc6e68d074dbd10a1c074ac78a112be8a9ad0b6250eb1571715163`.
See [Public API](docs/release1/public-api.md).

## Scientific meaning

Release 1 keeps Candidate, Twin, Model, Solver, Study, Result, Evaluation,
target status, eligibility, memory, prediction, evidence, and decision
provenance distinct. Numerical verification is not physical validation;
physical validation is not safety certification; synthetic closed-loop
execution is not real-world discovery. The load-bearing definitions are in
[Scientific Semantics](docs/release1/scientific-semantics.md).

## Authoritative Release 1 documentation

- [Architecture](docs/release1/architecture.md)
- [Quick Start](docs/release1/quick-start.md)
- [Closed Loop](docs/release1/closed-loop.md)
- [Scientific Semantics](docs/release1/scientific-semantics.md)
- [Public API](docs/release1/public-api.md)
- [Configuration Inventory](docs/release1/configuration.md)
- [Reproducibility](docs/release1/reproducibility.md)
- [Limitations](docs/release1/limitations.md)
- [Release Checklist](docs/release1/release-checklist.md)

Historical preregistrations and freeze reports remain evidence; they are not
the current product guide.

## Explicit limits

Release 1 has no general physical validation, production Twin registry,
database/object store/cache services, distributed or cloud runtime, CFD, FEA,
general multi-fidelity execution, real/general UQ, BoTorch or Bayesian
optimization, autonomous repeated discovery, Generation 2+, hypothesis
intelligence, LLM/AI orchestration, UI/web service, medical/clinical
validation, or safety/certification claim. See the exhaustive
[Limitations](docs/release1/limitations.md).

## Release state

The release-owned reference artifact is
`artifacts/release1/reference/release1-cycle.json`; the deterministic package
and content inventory is `artifacts/release1/package-manifest.json`. Tag
creation remains **PENDING FINAL AUTHORIZATION**. This preparation does not
create `v1.0.0` and does not move `main`.
