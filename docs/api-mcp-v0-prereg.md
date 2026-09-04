# API / MCP v0 — PREREGISTRATION

```text
Milestone:              API / MCP v0
Branch:                 api-mcp-v0
Base:                   origin/cloud/crafty-post-coupling-relocation @ 846c75c
Baseline regression:    FULL 2205 passed / 0 failed / 0 errors
                        (FAST measured on this worktree: 1602 passed, 603 deselected)
Decision status sought: PROPOSED. This milestone freezes nothing.
Written:                before any implementation file existed.
```

**This document is immutable once committed.** It is committed alone, before any
implementation. Deviations discovered during execution are recorded in the
evidence document under a `D-n` heading; this file is never edited to match what
happened.

---

## 1. The question

> Can Direct Python, HTTP and MCP invoke the **same** Crafty application
> boundary while preserving exactly the same scientific semantics, admission
> behaviour, execution meaning, convergence, validity and provenance?

This milestone exposes **existing** Crafty scientific execution to external
callers. It is not a product backend, not agent planning, not infrastructure,
and it introduces no new science.

### 1.1 Primary hypothesis — H1

One transport-neutral Crafty application boundary can accept a single versioned
external request and produce a single versioned external response, such that
Direct Python, HTTP (over a real TCP socket, in a separate OS process) and MCP
(over a real stdio pipe, in a separate OS process) each produce **the same**
scientific outputs, units, coupling outcome, sub-solve convergence, validation
verdicts and provenance execution identities, with **no transport-specific
scientific logic anywhere**.

### 1.2 Null hypothesis — H0. It must be allowed to win.

**H0(a).** External exposure requires transport-specific interpretation: at
least one of Direct / HTTP / MCP cannot be served without a scientific decision
made inside that transport's adapter.

**H0(b).** The current internal execution boundary
(`engcore.systems.electrothermal.coupled.run_fixed_point_coupling`) is **not** a
valid reusable application boundary — exposing it forces either a second
scientific architecture (a centralized admission gate, a planner, a provider
framework, a job platform) or a leak of provider/solver internals into the
external contract.

H0 winning is a valid and valuable outcome and will be reported as such. In
particular, if the three transports turn out to be three names for one
in-process function call, §12's differentiation claim is **withdrawn**, not
softened.

### 1.3 What this milestone explicitly does NOT claim

* **No `L2 DIFFERENTIATED`.** Master context §54.1 excludes "a second
  implementation written by the same author, on the same day, against the same
  interface" from "materially different". HTTP and MCP here are exactly that.
  The boundary claim is capped at `L1 EXERCISED` **by preregistration**, before
  any result is known. No amount of agreement between the three paths may
  upgrade it.
* No existing Crafty holding (`MODEL0-R`, `DATA-BOUNDARY0`, `MIN-FOUNDATION-ET`,
  `ET-VERTICAL`, `HETERO-NGSPICE`, `COUPLING-PACK-RELOCATION`, …) is upgraded,
  downgraded or reopened by this milestone.
* Nothing is claimed about authentication, multi-tenancy, concurrency, latency,
  scale, async execution, restart, persistence, or hostile network conditions.

---

## 2. Reviewer decision, taken before this document was written

`architecture-decision-reviewer` was invoked first, on the five options
(A) adapters call the domain/system packs directly, (B) one thin transport-neutral
application service, (C) generic job/workflow platform, (D) transport-specific
application services, (E) no new boundary — publish `CoupledRun.to_dict()`
verbatim and accept constructor arguments. It added (F) a thin versioned
envelope (B's placement, a projected payload) and (G) the service inside the
system pack.

**Verdict: ACCEPT WITH CHANGES — adopt (B), with the response shaped as (F).**

Rejections, with the reviewer's grounds:

| Option | Rejected because |
|---|---|
| (A) | No single place to version; each transport independently decides how to represent a non-convergent run; no structural guard exists today against a transport library entering `coupling/`, `domains/` or `systems/`. |
| (C) | Every component is on this milestone's do-not-start list; premature on all four premature-abstraction criteria; no consumer. |
| (D) | Same divergence as (A) one layer up; a second system pack would cost two services. |
| (E) | Fires `COUPLING-PACK-RELOCATION` reversal trigger 1 by construction (§U.1: "everything is currently free **because zero payloads exist** … a decaying fact"); welds the external contract to `coupling_fixed_point_run/1` and prices §U.2's still-open physics-graph / execution-policy split at a public migration; `require_schema` is exact-string with no migration path. |
| (G) | Puts one domain-named system pack in charge of the platform's external contract — the exact false ownership `COUPLING-PACK-RELOCATION` removed one layer down, one milestone ago. |

The reviewer's changes CH-1…CH-7 are adopted, with **one preregistered
narrowing** (§6.4: no internal passthrough key). Its rulings on sub-decisions
1–6 are adopted as stated and are reproduced where they bind, below.

**One reviewer correction to the brief is recorded here because it changes which
argument load-bears.** The wall-clock non-determinism named in the brief lives
in the *fluid-thermal* pack, not the electro-thermal one. A spike run before
this document was written serialized one CASE A run twice in one process and
diffed: **byte-identical, 162 106 bytes**. So the reproducibility argument does
*not* support the projection; the reversal-trigger and payload-size arguments do.

---

## 3. The consumer — reused, not created

The **existing electro-thermal vertical** (`ET-VERTICAL`, `MIN-FOUNDATION-ET`),
reached through its existing entry point. No new scientific domain, model,
solver, realization or physics is created by this milestone.

Justification for using the full vertical rather than a smaller case: it is the
only executed path in the repository that simultaneously returns meaningful
scientific outputs, a **coupling** outcome distinct from sub-solve convergence,
per-participant validation verdicts, and a multi-solver `ProvenanceRecord`
(arity 5, three solvers, two realizations). A smaller case would make several of
§11's required distinctions untestable.

### 3.1 The four executed configurations, all pre-existing

| Label | Declaration | Expected |
|---|---|---|
| `A` | `R1`: R_ref = 10 Ω, α = 0.00393 /K, T_ref = 293.15 K; body C = 2.5 J/K, hA = 0.05 W/K, T_amb = T_0 = 300 K, Δt = 120 s; V = 5 V; seed 300 K, tol 1e-6 K, budget 50 | `criterion_met`, 10 iterations, T\* = 338.577018 K, R\* = 11.785282 Ω, P\* = 2.121290 W |
| `B` | `A` with `max_iterations = 2` | `iteration_limit_reached`, 2 iterations, **every sub-solve reporting success** |
| `C` | `A` with `reference_resistance = -10 Ω` | admission refusal, **zero executor invocations** |
| `E'`| `A` with `execution_profile = "ngspice"` | real `ngspice-42` subprocess in the electrical slot |

`A` and `B` reproduce `ET-VERTICAL` CASE A and CASE C1 exactly; the numbers above
were confirmed against the current tree before this document was written and are
preregistered as **exact** targets to 1e-6 absolute.

---

## 4. The boundary

```text
  Direct Python ─┐
                 │
  HTTP  (separate process, real TCP socket) ─┼──▶  engcore.application.handle(payload) -> payload
                 │                                       │
  MCP   (separate process, real stdio pipe) ─┘            │
                                                          ▼
                            engcore.systems.electrothermal.coupled.run_fixed_point_coupling
                                                          │
                                                          ▼
                                          engcore.coupling.run_fixed_point  (unchanged)
```

* `engcore.application` is **transport-neutral** and imports no transport
  library, no HTTP library, no MCP SDK, no server and no socket. (CH-1)
* HTTP and MCP framing live **outside `engcore` entirely**, in `src/crafty_http/`
  and `src/crafty_mcp/`. `engcore` therefore gains **no** transport dependency at
  any level. (CH-1)
* **Direct Python IS the service**, not a third adapter: the direct consumer
  calls `engcore.application.handle` in-process. Three adapters and no boundary
  would make duplication unmeasurable. (CH-2)
* `handle(payload: Mapping) -> dict` is the **only** entry point the transports
  may call. It never raises for any caller-caused condition; it returns a
  response payload. (See §7.4 for the one deliberate exception.)
* v0 exposes **one operation**. No generalization over both system packs; the
  fluid-thermal pack is out of scope. (CH-6)

### 4.1 Modules to be created

| Path | Contains | Imports transport libs? |
|---|---|---|
| `src/engcore/application/contract.py` | request/response schema strings, parsing, projection | no |
| `src/engcore/application/catalog.py` | the closed execution-identity and execution-profile enumerations | no |
| `src/engcore/application/service.py` | `handle`, `execute`, failure classification | no |
| `src/crafty_http/server.py` | `http.server` only — stdlib | stdlib only |
| `src/crafty_mcp/server.py` | newline-delimited JSON-RPC 2.0 over stdin/stdout — stdlib | stdlib only |

**Stdlib only, both transports.** No FastAPI, Starlette, Flask, Pydantic,
uvicorn, or `mcp` SDK is installed or imported anywhere. This makes the
"no transport contamination" claim trivially auditable and removes a dependency
whose own types are a moving target (MCP removed JSON-RPC batching between two
2025 spec revisions).

### 4.2 The single edit outside the new packages

`run_fixed_point_coupling` today hard-codes `_executors(system, problems)` and
there is **no path under `src/` that substitutes an external provider into the
coupled loop** — `HETERO-NGSPICE`'s substitution lives in its test. Exposing an
execution profile therefore requires exactly one additive change:

```python
def run_fixed_point_coupling(system, plan, *, run_id="et-coupled",
                             circuit_solver=None) -> CoupledRun
```

where `circuit_solver(circuit: DCCircuit, run_id: str) -> ScientificResult`
defaults to the pack's existing native call. This is the **narrowest** available
seam: it substitutes *how a DC circuit is solved*, not how the coupling is
executed, so no coupling glue moves into the application layer and
`engcore/coupling/` is byte-unchanged.

Preregistered constraints on that edit:

1. `src/engcore/scientific/` — **byte-unchanged**.
2. `src/engcore/coupling/` — **byte-unchanged**.
3. `src/engcore/domains/` — **byte-unchanged**.
4. `src/engcore/systems/fluidthermal/` — **byte-unchanged**.
5. `src/engcore/systems/electrothermal/coupled.py` — one additive keyword and its
   plumbing. It must contain no occurrence of `ngspice`, `spice`, `netlist`,
   `subprocess` or `wsl` (the existing `HETERO-NGSPICE` guard), must mint no
   schema string, and must not change any number: `A`'s ten iterations and three
   metrics must be bit-identical before and after.

All five are asserted by test, not claimed.

---

## 5. External request contract

Schema string: **`crafty_execution_request/1`**.

```json
{
  "schema": "crafty_execution_request/1",
  "execution": "electrothermal.series_self_heating/1",
  "execution_profile": "native",
  "run_id": "caseA",
  "inputs": {
    "source_voltage": {"value": 5.0, "unit": "volt"},
    "stages": [
      {
        "component_id": "R1",
        "reference_resistance":    {"value": 10.0,    "unit": "ohm"},
        "temperature_coefficient": {"value": 0.00393, "unit": "1/kelvin"},
        "reference_temperature":   {"value": 293.15,  "unit": "kelvin"},
        "heat_capacity":           {"value": 2.5,     "unit": "joule/kelvin"},
        "ambient_conductance":     {"value": 0.05,    "unit": "watt/kelvin"},
        "ambient_temperature":     {"value": 300.0,   "unit": "kelvin"},
        "initial_temperature":     {"value": 300.0,   "unit": "kelvin"},
        "duration":                {"value": 120.0,   "unit": "second"}
      }
    ]
  },
  "coupling": {
    "transported_temperature": "final_temperature",
    "seed_temperature": {"value": 300.0, "unit": "kelvin"},
    "tolerance":        {"value": 1e-6,  "unit": "kelvin"},
    "max_iterations": 50
  }
}
```

### 5.1 Parsing rules, preregistered

1. The payload must be a JSON **object**. Anything else → `malformed_request`.
2. `schema` must be **exactly** `"crafty_execution_request/1"`. Any other value,
   including `"crafty_execution_request/2"` and a missing key, →
   `unsupported_schema_version`. No range, no "compatible-with", no coercion.
3. **Unknown keys are refused, at every level** — top level, `inputs`, each
   stage, and `coupling`. A field this reader does not understand is never
   silently dropped. This is the mechanism that makes §11(D) checkable.
4. Every scientific value is a two-key object `{"value": <number>, "unit": <string>}`
   and nothing else. A bare number is refused: §26.6, units remain explicit.
5. Each quantity is converted to that field's **declared canonical unit**
   immediately (`Quantity(value, unit).to(canonical)`). A dimensionally
   incompatible unit is refused there. The unit string's only effect on
   execution is a conversion factor.
6. `transported_temperature` ∈ {`"final_temperature"`, `"steady_state_temperature"`}
   — the two enumerated kelvin-valued metrics `ET-VERTICAL` measured 3.376418 K
   apart. Any other value is refused. It is never used to construct a name.
7. `execution` and `execution_profile` are resolved through **closed literal
   mappings** (§6). No import, no `getattr`, no class name, no path.
8. Bounds, refused as admission failures when exceeded: `max_iterations` ∈
   [1, 200]; `len(stages)` ∈ [1, 8]; HTTP request body ≤ 262 144 bytes.
9. `run_id` is caller-supplied (`ProvenanceRecord` "collects nothing on its
   own"). Default `"crafty-v0"`. It is used only as a provenance string.

### 5.2 What the request structurally cannot express

No arbitrary object or class import. No shell command. No executable path. No
argv. No Python expression. No filename. No untyped metadata escape hatch. No
solver configuration. No provider configuration. No netlist. There is **no
free-form mapping anywhere in the request**: every accepted key is enumerated in
source, and the only free-form strings are `component_id` (which reaches
identifier construction, never a process) and the unit strings (which reach
pint's unit-expression parser and nothing else — audited in §14).

This is **not** a universal scientific DSL. It is one operation's typed input.

---

## 6. Execution selection

### 6.1 The ruling

> **Should external callers choose the concrete solver/provider at all?**

Compared: **(A)** Crafty selects from scientific/capability constraints;
**(B)** v0 exposes a **closed enumerated execution profile** as controlled test
input.

**(B) is selected**, on the reviewer's ground and on `HETERO-NGSPICE` §66.4's
lesson — *a check whose only effect is a field nothing consults is not a guard*.
If the enumeration's only rejectable input maps to nothing that could ever spawn
a process, then "an unknown profile is refused before any subprocess launch" is a
restatement of `KeyError`, not a security claim. Including a profile that
genuinely reaches `subprocess.run` is what makes the refusal load-bearing.

(A) is additionally **not available**: no aggregated registry and no planner
exist (registries are per-domain factory functions; the Scientific Core README
states plainly that no global singleton exists). Choosing (A) in v0 would
require building one, which is a second architecture.

### 6.2 The closed enumerations

```python
EXECUTIONS = {"electrothermal.series_self_heating/1": <builder function>}
PROFILES   = {"native": None, "ngspice": <resolved circuit-solver callable>}
```

Both are **literal dicts in `engcore.application.catalog`**, keyed by exact
string, with no fallthrough, no prefix matching, no normalization and no
default-on-miss. A miss is a refusal that names the admissible set — which is
also this milestone's discovery affordance (§9.2).

The profile name `"ngspice"` is a **Crafty execution-profile identity drawn from
a closed enumeration**. It is never a path, argv element, command, or netlist
fragment; it selects an already-constructed object. The alternative — an opaque
name such as `"external_circuit_provider"` — was considered and rejected:
`ProvenanceRecord` already reports `solver_id = engcore.electrical.dc.ngspice`
and `backend = "ngspice"` truthfully, so an opaque request name that provenance
immediately de-anonymizes is obfuscation, not encapsulation.

**No provider internals are exposed.** The request cannot set the argv, the
timeout, the netlist, the analysis line, the node naming, or the version probe.

---

## 7. External response contract

Schema string: **`crafty_execution_response/1`**.

### 7.1 The five distinctions the response must keep apart

```text
TRANSPORT SUCCESS  !=  EXECUTION SUCCESS  !=  NUMERICAL CONVERGENCE
                   !=  COUPLING CONVERGENCE  !=  SCIENTIFIC VALIDITY
```

| Distinction | Where it lives | Never |
|---|---|---|
| transport success | HTTP status code / JSON-RPC framing — **outside the payload** | never inside `status` |
| execution success | `status` ∈ `executed` / `refused` / `execution_failed` | never the word `success`, never a boolean |
| numerical convergence | `result.participants[i].numerical_convergence` (`ConvergenceState`) | never derived from the coupling outcome |
| coupling convergence | `result.coupling.outcome` (`CouplingOutcome`) | never derived from sub-solve convergence |
| checked-ness of a result | `result.participants[i].validation_status` + `attained_levels` | `NOT_RUN` is never rendered as `pass` |
| model applicability | `result.model_validity` | see §7.3 — reported as **not assessed**, never as valid |

`"status": "executed"` means **the boundary carried out an execution**. It makes
no scientific claim whatsoever.

### 7.2 Shape

```json
{
  "schema": "crafty_execution_response/1",
  "status": "executed",
  "execution": "electrothermal.series_self_heating/1",
  "execution_profile": "native",
  "run_id": "caseA",
  "result": {
    "coupling": {
      "outcome": "criterion_met",
      "criterion_met": true,
      "iterations_run": 10,
      "max_iterations": 50,
      "tolerance": {"value": 1e-06, "unit": "kelvin"},
      "final_iterate_change": {"value": 0.0, "unit": "kelvin"},
      "iterate_changes": [{"value": 0.0, "unit": "kelvin"}]
    },
    "outputs": [
      {"problem_id": "...", "quantity": "...",
       "value": {"value": 0.0, "unit": "..."},
       "uncertainty": {"kind": "unknown", "notes": "..."}}
    ],
    "torn_endpoints": [
      {"problem_id": "...", "quantity": "...", "final_value": {"value": 0.0, "unit": "kelvin"}}
    ],
    "participants": [
      {"problem_id": "...",
       "numerical_convergence": "converged",
       "validation_status": "pass",
       "attained_levels": ["dimensionally_valid"],
       "models": [["...", "0.1.0"]],
       "solver": {"solver_id": "...", "version": "...", "backend": "..."}}
    ],
    "model_validity": {"assessed": false, "reason": "..."},
    "provenance": {
      "run_id": "caseA",
      "software_version": "...",
      "assumptions": ["..."],
      "bindings": [{"model": {"model_id": "...", "version": "..."},
                    "realization": {"realization_id": "...", "version": "..."},
                    "solver": {"solver_id": "...", "version": "...", "backend": "..."}}]
    }
  },
  "refusal": null
}
```

On any non-`executed` status, `result` is `null` and `refusal` is:

```json
{"code": "scientific_admission_refused",
 "stage": "admission",
 "error_type": "InvalidScientificProblem",
 "detail": "..."}
```

`outputs` carries **every** value of **every** participant's final-iteration
result. For configuration `A` that is 13 scalars. It is O(1) in mesh size by
construction — this consumer produces no field-valued output — so §13's
bulk-data rule is satisfied by the consumer, not by a filter.

### 7.3 `model_validity` — an honest absence, preregistered as such

`assess_resistance_validity` is an *existing* function that returns
`OUTSIDE_VALIDATED_DOMAIN` for `ET-VERTICAL` CASE F. It is **not called** by
`run_fixed_point_coupling` and is not part of the executed coupled path.

The application layer will therefore **not** call it, because doing so would put
a scientific assessment in the application layer that the execution path does not
perform — duplicated scientific logic, and precisely the "second architecture"
H0(b) predicts. Instead the response states the absence explicitly
(`"assessed": false`), because `NOT_RUN != PASS` (§26.2).

**This is preregistered as a measured negative finding**, not as a gap to be
patched later in the milestone: *the coupled execution contract does not produce
a model-applicability verdict, so no transport can report one.*

### 7.4 Preregistered narrowing of reviewer change CH-4

CH-4 permits the full internal `CoupledRun.to_dict()` under one explicitly
disclaimed passthrough key. **It is not included in v0.** Grounds:

1. A disclaimed key is still a key clients store. §66.4's lesson has a mirror: a
   field everything consults is not disclaimed by a docstring.
2. It reintroduces the external dependence on `coupling_fixed_point_run/1` that
   CH-4 exists to remove, and with it reversal trigger 1.
3. **Measured:** one CASE A run serializes to **162 106 bytes**, dominated by
   every iteration's full `ScientificResult` set. That is O(iterations × results)
   inline, which §13/`DATA-BOUNDARY0` refuse on principle regardless of the
   present absolute size.

Consequence, stated so it can be held against this milestone: **the external
response is lossy relative to the internal record.** Per-iteration participant
results are not externally reachable in v0. Anyone needing them uses Direct
Python. Adding a projection field later is additive; removing a published
passthrough is not.

---

## 8. Failure taxonomy

No new error hierarchy. The existing taxonomy already carries the load:
`ScientificCoreError` subclasses mean *the science was refused*;
`NgspiceProviderError(Exception)` — deliberately **not** a `ScientificCoreError`
— means *the provider broke*; anything else is a Crafty defect.

### 8.1 Classification rule: class **and** position

Classifying by exception class alone is **wrong**, and the counterexample is in
the tree: `InvalidScientificProblem` is raised both for caller-malformed
declarations *and* at `coupling/execution.py` for an executor returning a result
attributed to the wrong problem — a Crafty defect, which class alone would
report as a caller error.

**Rule.** Anything raised during construction and admission — strictly before
`run_fixed_point` is entered — is a caller-facing refusal. Anything raised during
iteration is an execution failure, whatever its class. The classifier is keyed on
**exception class objects**, never on message strings, is total over an
enumerated set, and its default is its own code `unclassified_internal_failure`,
never a collapse into "error".

### 8.2 The eight cases

| | Condition | `status` | `refusal.code` | HTTP | MCP |
|---|---|---|---|---|---|
| A | body not JSON / not an object / wrong field types | `refused` | `malformed_request` | 400 | result, `isError:false` |
| B | `schema` unknown or missing | `refused` | `unsupported_schema_version` | 400 | result, `isError:false` |
| C | scientific admission rejection (unit, sign, plan, dimension, bound) | `refused` | `scientific_admission_refused` | 422 | result, `isError:false` |
| D | unknown execution identity / unknown profile | `refused` | `unknown_execution` / `unknown_execution_profile` | 400 | result, `isError:false` |
| E | provider execution failure (`NgspiceProviderError`) | `execution_failed` | `provider_execution_failed` | 502 | result, `isError:false` |
| F | sub-solver failure raised **during** iteration | `execution_failed` | `subsolver_execution_failed` | 500 | result, `isError:false` |
| G | coupling did not converge within budget | **`executed`** | `null` | **200** | result, `isError:false` |
| H | coupling converged | `executed` | `null` | 200 | result, `isError:false` |

**G is the load-bearing row.** A valid request that hits its iteration limit is
`status: "executed"`, `outcome: "iteration_limit_reached"`, HTTP **200**. It is
never a 5xx. HTTP status never claims scientific truth.

E and F must map through the boundary **without becoming scientific invalidity or
coupling non-convergence**: on both, `result` is `null`, so there is no coupling
outcome and no validation verdict to misread.

### 8.3 The deliberate transport asymmetry

An MCP tool call that hits any of A–F returns a **successful tool result whose
structured content reports the refusal** (`isError: false`), because an agent
must be able to read the refusal reason and must not be able to retry blindly on
an opaque error. A malformed **JSON-RPC** envelope (bad method, unparsable frame)
is a JSON-RPC error — that is transport, not science.

HTTP maps the same refusals to 4xx/5xx **with the identical response body**.

This asymmetry is preregistered, is framing only, and is the one place the two
transports were free to disagree. **The differential in §12 compares the response
payload, never the framing.**

---

## 9. HTTP surface

**`POST /v0/run` and nothing else.**

Content-Type `application/json`; body ≤ 262 144 bytes; any other method → 405;
any other path → 404. No auth, users, orgs, billing, projects, databases, job
queues, WebSocket, uploads, dashboards, rate limiting, Kubernetes, async workers.

### 9.1 `/v0/validate` — deleted, not deferred-with-a-stub

`FixedPointCouplingPlan.unsupplied()` is documented "**Reported, never
refused**", and `check_against` "cannot check result-metric sources: they do not
exist until a solve has produced them." A `/validate` returning `OK` would
therefore assert admissibility the records cannot establish, for a request that
may still fail mid-iteration — `NOT_RUN` reported as `PASS` at the API layer,
§26.2 in a new costume. It is additive later. **Not built.**

### 9.2 `/v0/capabilities` and `/v0/profiles` — deleted

No aggregated registry exists and no planner exists, so a capabilities endpoint
would publish a discovery surface no caller can act on, and building the
aggregation would put a list of domain names in a would-be-universal layer.

`/v0/profiles` was the reviewer's non-speculative substitute and is **also not
built**, for a reason that only became available after §6.2 was fixed: a refusal
for an unknown execution or profile **names the admissible set**. Discovery is
delivered by the error, so a second endpoint restating it carries no independent
meaning (§15 reduction attack R-4).

---

## 10. MCP surface

**One tool, `crafty_run`, and nothing else.** `crafty_validate` and
`crafty_capabilities` are deleted for the same reasons as §9.1/§9.2.

Protocol: JSON-RPC 2.0, newline-delimited JSON over stdin/stdout, in a **separate
OS process**. Methods implemented: `initialize`, `tools/list`, `tools/call`.
Nothing else.

`tools/list` publishes `crafty_run`'s `inputSchema`, which is generated from the
same catalog constants the validator uses. This is a genuine MCP/HTTP asymmetry
and is recorded as such: MCP has a built-in discovery channel; HTTP in v0 does
not, and §9.2 declines to invent one.

### 10.1 The LLM boundary, preserved

```text
LLM proposes a request  ->  Crafty deterministic admission  ->  Crafty deterministic
execution  ->  Crafty's own validity / convergence / provenance  ->  the agent may
only EXPLAIN
```

The tool handler contains **no scientific logic**: it decodes JSON-RPC, calls
`engcore.application.handle`, and encodes the result. Asserted structurally by
test (§11 fitness), not promised.

The LLM may never certify convergence, validity, evidence admission or scientific
truth. It cannot alter a convergence verdict, select a shell command, choose a
solver outside the closed enumeration, or construct provider semantics, because
none of those is expressible in the request.

---

## 11. Required executed cases

| | Case | Assertion |
|---|---|---|
| **A** | valid convergent run | `criterion_met`, 10 iterations, T\* = 338.577018 K (abs 1e-6), R\* = 11.785282 Ω, P\* = 2.121290 W; **equivalent across Direct, HTTP and MCP** |
| **B** | valid, non-convergent on a legitimate budget (`max_iterations = 2`) | all three paths report execution happened, **every sub-solve success**, coupling `iteration_limit_reached`; HTTP 200 |
| **C** | invalid scientific input (`reference_resistance = -10 Ω`) | refused; **zero executor invocations**, proven by in-process spies on `run_fixed_point`, `solve_circuit` and `subprocess.run` |
| **D** | `"schema": "crafty_execution_request/2"`, and an unknown field | refused loudly; **no field silently dropped** — asserted by sending a request with an extra key that *would* change the answer and requiring refusal, not a differing number |
| **E** | unknown execution identity; unknown execution profile | refused **before any process invocation**, proven cross-process by a sentinel provider that writes a marker file when launched |
| **F** | provider failure — real: server subprocess started with `CRAFTY_NGSPICE_ARGV` pointing at a sentinel that exits non-zero | `execution_failed` / `provider_execution_failed`; `result` is `null`; **no coupling outcome and no validation verdict is emitted**, so provider failure cannot be read as invalidity or non-convergence |
| **G** | injection: executable path as profile; `"; touch <marker>"`; argv-shaped object; unknown provider name; shell-like unit string; unexpected object where a scalar belongs; extra nested field | every one refused; **marker file absent**; `subprocess.run` invocation count zero |
| **H** | transport equivalence on one canonical request | §12 |

Plus, executed with a **real** `ngspice-42` at `/usr/bin/ngspice`: configuration
`A` under `execution_profile = "ngspice"`, agreeing with the native profile to
the §12 tolerance, through the HTTP transport.

---

## 12. Differential proof

The same canonical request payload (configuration `A`, identical `run_id`) is
submitted through all three paths. Compared:

1. **Scientific output quantities and units** — every entry of `result.outputs`,
   matched by `(problem_id, quantity)`. Acceptance: relative difference
   **≤ 1e-12**, with `unit` strings **exactly equal**. The measured value will be
   reported separately and is expected to be `0.0`.
2. **Coupling outcome** — `outcome`, `criterion_met`, `iterations_run` exactly
   equal.
3. **Validity / admission information** — every participant's
   `validation_status` and `attained_levels` exactly equal.
4. **Numerical convergence** — every participant's `numerical_convergence`
   exactly equal.
5. **Provenance execution identities** — the set of
   `(model_id, model_version, realization_id, solver_id, solver_version, backend)`
   tuples exactly equal, and non-empty.
6. **Response schema meaning** — all three carry
   `"schema": "crafty_execution_response/1"` and the same `status`.
7. **Whole-payload structural equality** — the three parsed payloads compare
   equal as Python objects.

(7) is a **measurement, not a contract clause.** Byte-equality is not promised by
`crafty_execution_response/1` and no consumer may rely on it; it is asserted here
because a spike showed it is currently achievable, and an unexplained divergence
would be a finding worth having. If (7) fails while (1)–(6) pass, the milestone
records the difference and (1)–(6) still decide H1.

### 12.1 The differentiation question, ruled in advance

HTTP crosses a real TCP socket to a separate OS process; MCP crosses a real pipe
to a separate OS process. **This is preregistered as sufficient for `L1` and
insufficient for `L2`.** Two transports written by one author on one day against
one interface are not "materially different consumers" (§54.1). If either
transport turns out to be an in-process wrapper, that fact is reported in the
headline and the transport claim is capped further.

---

## 13. Serialization

* Both external schemas are versioned exact strings and neither reuses a
  Scientific Core or coupling schema name.
* The reader accepts **exactly** `crafty_execution_request/1`. A future version
  fails loudly.
* Typed quantities travel as `{"value", "unit"}`; provenance, convergence and
  validation verdicts are preserved as enumerated strings.
* Forbidden in any response, asserted by test over the serialized payload: any
  provider stdout or stderr, any executable path, any argv, any raw Python
  `repr`, any pickle, any traceback, any absolute filesystem path, any netlist.
* No bulk data. This consumer produces none; no `data_references` and no
  `O(mesh)` array can appear. No file upload or download.
* No JSON/YAML fixture carrying a coupling schema string is committed (the
  existing `COUPLING-PACK-RELOCATION` stored-payload guard must keep passing).

---

## 14. Security / process boundary

Crafty has a real external provider reached as
`subprocess.run([*command, "-b"], input=netlist, ...)` where `command` comes from
`shutil.which("ngspice")` or `shlex.split(os.environ["CRAFTY_NGSPICE_ARGV"])`.
This is the concrete RCE surface.

**Claim to be proven:** no field of an external request can become a subprocess
executable, a shell fragment, a filesystem path, a dynamic import, or an
`eval`/`exec` target.

The defence is **structural, not a blacklist**:

1. The only request field that influences process execution is
   `execution_profile`, resolved through a **closed literal dict** to an
   already-constructed object. The string is never concatenated, never split,
   never passed to `shlex`, never passed to `subprocess`, never used in a path.
2. No request field reaches `os.environ`. `CRAFTY_NGSPICE_ARGV` is process
   configuration, set before the server starts, never by a request.
3. The request contains no free-form mapping; every accepted key is enumerated
   in source.
4. Unit strings reach pint's unit-expression parser and nothing else. Measured
   before this document was written: `__import__("os").system(...)`,
   `1;import os`, `ohm; rm -rf /`, `` `id` ``, `/usr/bin/ngspice` and
   `eval("1+1") ohm` are all refused as `UnitCompatibilityError`, and no file was
   created. This will be re-executed as a test.
5. An audit test walks the full request→provider flow and asserts that no
   externally-supplied string appears in any argument of any `subprocess`,
   `os.system`, `importlib`, `eval`, `exec`, `open` or path-construction call.

---

## 15. Reduction attacks — every new abstraction, attacked before it is written

Each must justify itself against existing typed Crafty contracts. Any that cannot
is deleted or deferred.

| | Abstraction | Attack | Preregistered disposition |
|---|---|---|---|
| R-1 | `ExecutionRequest` | Could the request just be the constructor kwargs (option E)? | **Keep.** It is the only place unknown-field refusal, the closed enumerations and the unit-canonicalization can live. Constructor kwargs cannot carry a schema version. |
| R-2 | `ExecutionResponse` | Could it be `CoupledRun.to_dict()`? | **Keep**, per §2 and §7.4 — the internal record's version is not the external contract's version. |
| R-3 | `ApplicationService` as a **class** | Does it hold state? | **DELETE the class.** It holds none. The boundary is module-level functions `handle` / `execute`. A class here would be a namespace with a constructor. |
| R-4 | `CapabilityResponse` | Is there a consumer? | **DELETE.** No registry, no planner; refusals already name the admissible set (§9.2). |
| R-5 | `TransportError` | Do transports need their own error type? | **DELETE.** The boundary never raises for caller-caused conditions; it returns a refusal payload. Each transport maps a code to its own framing with a literal dict. |
| R-6 | `ExecutionProfile` as a **record/dataclass** | Does it carry a field other than its name? | **DELETE the record.** Reduce to a key of a literal dict. If it ever needs a second field, that is a later, additive decision. |
| R-7 | A centralized `admit(request)` gate | Does exposure force one? | **DELETE.** Admission is distributed across the dataclass validators, `check_against`, and `run_fixed_point`'s guards, all of which execute before any executor call. A central gate would duplicate refusals that already live where the knowledge is, and would be exactly the second architecture H0(b) predicts. Instead the **ordering** is proven by spies (§11 C). |
| R-8 | A provider/solver registry | Forced? | **DELETE.** Two entries in a literal dict. |
| R-9 | An `ExecutionOutcome` enum distinct from `CouplingOutcome` | Forced? | **DELETE.** `status` is three enumerated strings on the response; `CouplingOutcome`'s two members travel unchanged. |

---

## 16. Architecture fitness — the sixteen questions, to be answered in evidence

1. frozen scientific-core contract changed? 2. existing scientific schema
changed? 3. migration required? 4. transport-specific branch in scientific core?
5. HTTP/MCP type imported by core? 6. solver/provider internals leaked into
external semantics? 7. arbitrary executable/provider path externally
controllable? 8. metadata escape hatch introduced? 9. duplicated scientific
execution code? 10. Direct/HTTP/MCP use the same boundary? 11. convergence
preserved? 12. validity preserved? 13. provenance preserved? 14. unsupported
schema fails loudly? 15. admission failure stops execution? 16. could a fourth
transport reuse the boundary from its published contract without reading domain
source?

Preregistered expected answers: 1–9 **no**, 10–16 **yes**. Any deviation is a
finding reported in the headline, not a footnote.

---

## 17. Fail conditions

The milestone **fails** — and H0 wins — if any of the following holds at the end:

1. Any file under `src/engcore/scientific/`, `src/engcore/coupling/`,
   `src/engcore/domains/` or `src/engcore/systems/fluidthermal/` is modified.
2. Any transport library or the `mcp` SDK is imported anywhere under
   `src/engcore/`.
3. A scientific decision (a unit choice, a default that changes an answer, a
   convergence interpretation, a validity interpretation) is made inside
   `crafty_http` or `crafty_mcp`.
4. Direct, HTTP and MCP disagree on any comparison field of §12 beyond the stated
   tolerance.
5. A non-convergent run is reported as a failure, or as an HTTP 5xx.
6. A provider failure is reported as scientific invalidity or as coupling
   non-convergence.
7. Any externally supplied string reaches a subprocess argument, a path, an
   import, or an `eval`/`exec`.
8. An unsupported schema version is accepted, or an unknown field is silently
   dropped.
9. A solver or provider executes after an admission rejection.
10. FULL regression is not 0 failed / 0 errors, or any pre-existing test is
    edited to make it pass.

---

## 18. Tests and regression

TARGETED (`tests/test_api_mcp_v0.py`) / FAST (`-m "not expensive"`) / FULL, per
`TEST-INFRA0`. Baseline **FULL 2205 passed / 0 failed / 0 errors**. Tests that
spawn a real HTTP or MCP subprocess, or invoke real `ngspice`, will be labelled
`expensive` in `tests/conftest.py`; the pure-boundary tests stay in FAST. **No
pre-existing test is edited**, no tolerance loosened, no test skipped. Final
counts, warnings and runtime are reported in the evidence document.

---

## 19. Evidence level sought

| Claim | Sought |
|---|---|
| One transport-neutral application boundary serves Direct, HTTP and MCP | `PROPOSED` / `L1 EXERCISED` |
| The external request/response contract preserves the five distinctions | `PROPOSED` / `L1 EXERCISED` |
| No external field can reach process execution | `PROPOSED` / `L1 EXERCISED` for the audited flow; explicitly **not** `L3` — no fuzzing, no hostile network |
| Transport independence at `L2` | **Excluded by preregistration** (§1.3, §12.1) |
| Anything about async, scale, concurrency, auth, persistence | **zero** |

---

## 20. Signature

Written before implementation. Committed alone. Not edited afterwards.
