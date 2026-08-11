# Release 1 Quick Start

This Quick Start uses the installed `engineering-ai-core` wheel. The Release 1
examples are distributed with the release bundle, not imported as Python
package modules.

## 1. Create a clean environment and install

Windows PowerShell:

```powershell
py -3.11 -m venv .venv-release1
.\.venv-release1\Scripts\python -m pip install --upgrade pip
.\.venv-release1\Scripts\python -m pip install dist\engineering_ai_core-1.0.0-py3-none-any.whl
.\.venv-release1\Scripts\python -c "import engcore; print(engcore.__version__)"
```

POSIX shell:

```sh
python3.11 -m venv .venv-release1
.venv-release1/bin/python -m pip install --upgrade pip
.venv-release1/bin/python -m pip install dist/engineering_ai_core-1.0.0-py3-none-any.whl
.venv-release1/bin/python -c 'import engcore; print(engcore.__version__)'
```

The version command must print `1.0.0`. The package declares Python `>=3.11`.
Use a wheel supplied by the release bundle or built from its exact commit.

## 2. Execute a real Lab scientific model

Windows:

```powershell
.\.venv-release1\Scripts\python examples\release1\01_lab_dc.py
```

POSIX:

```sh
.venv-release1/bin/python examples/release1/01_lab_dc.py
```

This is actual Electrical DC domain execution. The example creates typed
resistance and voltage quantities, constructs a `DCCircuit` and
`ScientificProblem`, invokes `ElectricalDCSolver`, and receives a
`ScientificResult`. Its concise JSON summary exposes:

- `study_id` / problem identity;
- model and solver identities;
- `result_id`;
- the 9 V divider midpoint and 3 mA resistor current;
- convergence and attained validation levels;
- honest `unknown` uncertainty;
- model, solver, input, formulation, and tolerance provenance.

A failed or singular circuit still returns an attributable result with failed
convergence/validation and no invented solution values. Identity or unit
mismatches fail closed with typed scientific errors.

## 3. Inspect attribution and Public Mind memory

```powershell
.\.venv-release1\Scripts\python examples\release1\02_twin_attributable_evaluation.py
.\.venv-release1\Scripts\python examples\release1\03_mind_reference.py
```

Example 02 prints exact Candidate, Twin, design-space, result, binding, and
evaluation identities. It catches one deliberate candidate substitution to
show fail-closed attribution. The multirotor path is an analytic reference,
not physical validation.

Example 03 uses only Public V1 D3 memory. It classifies and retains attributable
eligible observations under an explicit policy and proves a second context has
a different scope identity. Retention is not scientific truth.

## 4. Run the bounded Release 1 reference cycle

This step is **developer/release-reference verification**. It still imports
`engcore` from the installed wheel, but it deliberately reads the frozen
release bundle file `experiments/design_d7/loop.py` through the explicit
release-internal seam. That file is not Public V1 and is not copied into the
wheel as a general Mind API.

```powershell
.\.venv-release1\Scripts\python examples\release1\04_closed_loop.py `
  --reference experiments\design_d7\loop.py `
  --output-dir release1-example-output `
  --release-commit YOUR_RELEASE_COMMIT
```

POSIX:

```sh
.venv-release1/bin/python examples/release1/04_closed_loop.py \
  --reference experiments/design_d7/loop.py \
  --output-dir release1-example-output \
  --release-commit YOUR_RELEASE_COMMIT
```

The first two output lines are deliberately unambiguous:

```text
REFERENCE SYNTHETIC SCIENTIFIC SYSTEM
NOT PHYSICAL-WORLD VALIDATION
```

The example executes one initial Study, admits attributable evidence, records
one Mind decision, executes one selected Generation 1 Study, returns new
evidence to memory, produces two byte-identical fresh artifacts, reloads and
revalidates the typed graph, and prints `generation_2_executed: false`.

Generated files live at:

- `release1-example-output/release1-cycle.json`;
- `release1-example-output/release1-cycle.replay.json`.

The example refuses to write into the frozen D7 artifact directory. The
release-owned read-only reference artifact is
`artifacts/release1/reference/release1-cycle.json`.
