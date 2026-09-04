# API / MCP v0 — EVIDENCE

```text
Milestone:              API / MCP v0
Decision status:        PROPOSED — this milestone freezes nothing
Evidence:               L1 EXERCISED (the boundary and the contract)
                        L2 EXCLUDED BY PREREGISTRATION, before any result was known
Milestone execution:    COMPLETE
Branch:                 api-mcp-v0
Base:                   origin/cloud/crafty-post-coupling-relocation @ 846c75c
Preregistration:        docs/api-mcp-v0-prereg.md, commit 3f2e6dd, immutable
```

**The preregistration was not edited.** Every departure from it is recorded
below under a `D-n` heading. There are three, and one of them triggered a
preregistered fail condition.

---

# A. Reviewer verdict

`architecture-decision-reviewer`, invoked **before** the preregistration was
written, on five candidate boundaries plus two it added.

> **ACCEPT WITH CHANGES — adopt (B), with the response shaped as (F).**

| Option | Ruling |
|---|---|
| (A) adapters call the domain/system packs directly | **Rejected.** No single place to version; each transport independently decides how to represent a non-convergent run; no structural guard existed against a transport library entering `coupling/`, `domains/` or `systems/`. |
| (B) one thin transport-neutral application service | **Selected.** |
| (C) generic job/workflow/execution platform | **Rejected.** Every component is on the do-not-start list; premature on all four premature-abstraction criteria; no consumer. |
| (D) transport-specific application services | **Rejected.** Same divergence as (A) one layer up. |
| (E) no new boundary — publish `CoupledRun.to_dict()` verbatim | **Rejected**, and it was the strongest alternative. It fires `COUPLING-PACK-RELOCATION` reversal trigger 1 *by construction*: §U.1 records that every remaining naming and shape question about `coupling_fixed_point_run/1` is free "**because zero payloads exist** … a decaying fact", and an external API response is the mass production of stored payloads by parties Crafty cannot migrate. `require_schema` is exact-string with no migration path. |
| (F) thin versioned envelope — B's placement, a projected payload | **Adopted for the response.** |
| (G) the service inside the system pack | **Rejected.** It puts one domain-named pack in charge of the platform's external contract — the exact false ownership `COUPLING-PACK-RELOCATION` removed one layer down, one milestone earlier. |

Changes CH-1…CH-7 were adopted, with one preregistered narrowing (§7.4 of the
prereg: no internal passthrough key). Its rulings on the six sub-decisions were
adopted as stated: a separate projection; a closed execution-profile enumeration
that genuinely reaches a process; no new error hierarchy but class-**and**-position
classification; `/validate` deferred; `/capabilities` deferred; and **no
centralized admission gate** — prove the ordering instead.

**One reviewer correction changed which argument load-bears.** The brief
attributed the case against a verbatim passthrough to non-reproducibility. The
reviewer found the wall-clock non-determinism lives in the *fluid-thermal* pack,
not the electro-thermal one. A spike run before the preregistration serialized
one nominal run twice in one process and diffed: **byte-identical**. So the
reproducibility argument does not support the projection; the reversal-trigger
and payload-size arguments do.

---

# B. The selected application boundary

```text
  Direct Python  ────────────────────────────────┐
                                                 │
  HTTP   real TCP socket, separate OS process  ──┼──▶  engcore.application.handle
  MCP    real stdio pipe,  separate OS process ──┘        (payload -> payload)
                                                              │
                                                              ▼
                     engcore.application.executions.electrothermal_series.prepare
                                                              │
                                                              ▼
                        systems.electrothermal.run_fixed_point_coupling
                                                              │
                                                              ▼
                             engcore.coupling.run_fixed_point  (byte-unchanged)
```

`engcore.application` is a **module of functions, not a class**. It owns no
physics, no equation, no numerical method, no convergence rule, no validity
rule, no tolerance, and no unit conversion beyond restating a caller's value in
the unit the receiving declaration already declares.

Both transports live **outside `engcore` entirely** (`src/crafty_http/`,
`src/crafty_mcp/`), and both are **stdlib only** — `http.server` and a
newline-delimited JSON-RPC 2.0 loop. FastAPI, Starlette, Flask, Pydantic,
uvicorn and the `mcp` SDK are neither installed nor imported anywhere. `engcore`
therefore gains no transport dependency at any level, which makes the
"no transport contamination" claim auditable by reading two short files.

Direct Python **is** the service, not a third adapter: the direct consumer calls
`handle` in process, so duplication across transports is measurable rather than
definitional.

---

# C. Candidates rejected, and the two that were reduced away during execution

Beyond §A's option table, six abstractions named in the preregistration's
reduction attacks were deleted before they were written, and both new ones were
attacked again after the falsifier:

| | Abstraction | Disposition |
|---|---|---|
| R-1 | `ExecutionRequest` | **Kept.** The only place unknown-field refusal, the closed enumerations and unit canonicalization can live. Constructor kwargs cannot carry a schema version. |
| R-2 | `ExecutionResponse` | **Kept**, as a projection function rather than a record — `project_run(CoupledRun) -> dict`. |
| R-3 | `ApplicationService` class | **Deleted.** It holds no state; it would be a namespace with a constructor. |
| R-4 | `CapabilityResponse` | **Deleted.** A refusal for an unknown execution or profile already *names the admissible set*. |
| R-5 | `TransportError` | **Deleted.** The boundary never raises for a caller-caused condition. Asserted: neither transport defines an exception class. |
| R-6 | `ExecutionProfile` record | **Deleted.** Reduced to a key of a literal dict. |
| R-7 | a centralized `admit(request)` gate | **Deleted.** Admission stays distributed where the knowledge is; the **ordering** is measured instead (§N). |
| R-8 | a provider/solver registry | **Deleted.** Two entries in a literal dict, owned by the execution. |
| R-9 | `ExecutionOutcome` enum | **Deleted.** `status` is three enumerated strings; `CouplingOutcome`'s two members travel unchanged. |

**Two abstractions survive that the preregistration did not anticipate**, both
forced by the adversarial pass: `provider_failure_types()` on the execution
module (so the universal layer can classify a provider failure without naming a
provider) and `request_fragment()` (so the published contract is derived from the
enforced one rather than transcribed beside it).

---

# D. External request contract

`crafty_execution_request/1`. **Not** built with `schema_string`: it is not a
member of the Scientific Core's record family and a reader must not be able to
mistake it for one.

```json
{
  "schema": "crafty_execution_request/1",
  "execution": "electrothermal.series_self_heating/1",
  "execution_profile": "native",
  "run_id": "api-v0-case-a",
  "inputs": {
    "source_voltage": {"value": 5.0, "unit": "volt"},
    "stages": [{"component_id": "R1",
                "reference_resistance":    {"value": 10.0,    "unit": "ohm"},
                "temperature_coefficient": {"value": 0.00393, "unit": "1/kelvin"},
                "reference_temperature":   {"value": 293.15,  "unit": "kelvin"},
                "heat_capacity":           {"value": 2.5,     "unit": "joule/kelvin"},
                "ambient_conductance":     {"value": 0.05,    "unit": "watt/kelvin"},
                "ambient_temperature":     {"value": 300.0,   "unit": "kelvin"},
                "initial_temperature":     {"value": 300.0,   "unit": "kelvin"},
                "duration":                {"value": 120.0,   "unit": "second"}}]
  },
  "coupling": {
    "transported_temperature": "final_temperature",
    "seed_temperature": {"value": 300.0, "unit": "kelvin"},
    "tolerance":        {"value": 1e-6,  "unit": "kelvin"},
    "max_iterations": 50
  }
}
```

**What holds it together, and what it structurally cannot say.**

* Exact schema string. Not a range, not a minimum, no coercion.
* **Unknown keys are refused at every level** — top level, `inputs`, each stage,
  `coupling`, and inside each quantity object. Seven probe sites, all asserted.
* Every scientific value is `{"value", "unit"}` and nothing else. A bare number
  is refused; `True` is refused, because `bool` is an `int` in Python and would
  become `1.0`.
* Every quantity is restated in the receiving declaration's own unit
  immediately, so the caller's unit string can only ever be a conversion factor.
* `transported_temperature` and `execution_profile` are **enumerated**, resolved
  through closed literal dicts with no prefix match, case folding, normalization
  or default-on-miss.
* `component_id` and `run_id` are constrained to a published identifier pattern
  (§P).
* Bounds refused, never clamped: `max_iterations ∈ [1, 200]`, `len(stages) ∈
  [1, 8]`, serialized request ≤ 262 144 bytes.
* **No free-form mapping anywhere.** No `metadata`, no `options`, no `extra`. No
  class name, no import, no path, no argv, no shell string, no Python
  expression, no netlist, no solver configuration.

There is **no default anywhere in `inputs` or `coupling`**, and after D-2 no
default in the envelope either. Every field is required. This is deliberate: a
default here is a default that changes an answer or selects an implementation.

The contract is machine-readable — `engcore.application.describe.request_json_schema()`,
7 835 bytes, derived from the same constants the validator enforces, with
`additionalProperties: false` wherever properties are declared and one
`allOf`/`if`/`then` clause per execution stating which profiles that execution
admits.

---

# E. External response contract

`crafty_execution_response/1`. Its own identity, deliberately: neither schema
string reuses a Scientific Core or coupling name, and a test asserts no internal
schema string appears anywhere in a response.

## E.1 The five distinctions, and where each lives

```text
TRANSPORT SUCCESS != EXECUTION SUCCESS != NUMERICAL CONVERGENCE
                 != COUPLING CONVERGENCE != SCIENTIFIC VALIDITY
```

| Distinction | Field | Never |
|---|---|---|
| transport success | HTTP status line / JSON-RPC envelope — **outside the payload** | never inside `status` |
| execution success | `status` ∈ `executed` / `refused` / `execution_failed` | never the word *success*, never a boolean |
| numerical convergence | `result.participants[i].numerical_convergence` | never derived from the coupling outcome |
| coupling convergence | `result.coupling.outcome` | never derived from the sub-solves |
| checked-ness | `result.participants[i].validation_status` + `attained_levels` | `NOT_RUN` is never rendered as `pass` |
| model applicability | `result.model_validity` | reported as **not assessed** — see §E.3 |

`"status": "executed"` means *the boundary carried out an execution*. It makes
no scientific claim: a run that hit its iteration budget without converging is
`executed` too.

## E.2 What the projection carries, and what it deliberately loses

For the nominal case: 13 outputs across 3 participants, each with unit and an
explicit `uncertainty` (all `unknown` — §26.4, unknown uncertainty travels as
*unknown*, never as absence); the coupling block including the full
iterate-change history, one scalar per sweep; the torn endpoints keyed by their
two components rather than a joined string; per-participant verdicts; and
provenance with **5 `ExecutionBinding`s over 3 solvers and 2 realizations**.

**Measured:** the internal `CoupledRun` serializes to **162 594 bytes**; the
external response to **7 711 bytes** — a factor of **21.1**. The difference is
every iteration's full `ScientificResult` set, which is `O(iterations × results)`
inline data.

**The external contract is therefore lossy, and that is stated rather than
presented as a feature:** per-iteration participant results are not externally
reachable in v0. Anyone needing them uses Direct Python. Adding a projection
field later is additive; removing a published passthrough key is not.

Reviewer change CH-4 permitted a disclaimed passthrough key. It was **not
built** (prereg §7.4), on three grounds: a disclaimed key is still a key clients
store; it reintroduces the external dependence on `coupling_fixed_point_run/1`
that CH-4 exists to remove; and the size measurement above.

`project_run` **raises** rather than emitting a response when any projected
result carries `data_references`. `crafty_execution_response/1` has no
representation for bulk data, and `DATA-BOUNDARY0` already ruled that loud
failure beats silent understatement of a scientific claim. This is not reachable
from the wired consumer, which is scalar; it is reachable the day a field-valued
execution is exposed, and the function is domain-neutral so it cannot rely on
the consumer being scalar.

## E.3 `model_validity` — an honest absence, and a measured negative finding

Crafty *has* a model-applicability assessment for this domain:
`assess_resistance_validity`, which `ET-VERTICAL` CASE F showed returns
`OUTSIDE_VALIDATED_DOMAIN` on a run that converged with every check passing.

**It is not called by `run_fixed_point_coupling`, so it is not part of the
executed path, so no transport can report it.** The application layer does not
call it either, because that would be a scientific assessment performed by a
layer that did not execute the science — the second architecture the null
hypothesis predicts. The response says so explicitly:

```json
"model_validity": {"assessed": false, "reason": "... NOT_RUN is not PASS."}
```

**Consequence, stated plainly: a converged-but-out-of-domain run and a
converged-and-in-domain run are externally indistinguishable in v0.** That is a
gap in the *executed coupled contract*, surfaced by exposing it, not a gap this
milestone introduced. It is the sharpest thing this milestone learned about the
existing execution path.

## E.4 The scope of `result`, published before the fact

Every execution v0 can expose is an **iterative coupling**: `project_run` takes
a `CoupledRun`, and that is a published requirement of the execution-module
protocol. So `result.coupling` and `result.torn_endpoints` are properties of a
torn fixed-point iteration, not of "a Crafty execution". A single-solve
execution has no honest value for `outcome`, and `torn_endpoints: []` would not
mean *none* but *the question does not apply*. Such an execution requires
`crafty_execution_response/2`, which the exact-string reading makes loud and
additive. **No result-shape abstraction was built for it**: one consumer, one
shape.

---

# F. HTTP surface

**`POST /v0/run` and nothing else.** Content-Type `application/json`; body
≤ 262 144 bytes; any other method on that path → 405; any other path → 404.

No auth, users, organizations, billing, projects, databases, job queues,
WebSocket, uploads, dashboards, rate limiting, orchestration or async workers.

**Deleted, each with its reason:**

* `POST /v0/validate` — `FixedPointCouplingPlan.unsupplied()` is documented
  *"Reported, never refused"*, and `check_against` cannot check sources that are
  result metrics because they do not exist until a solve has produced them. A
  `/validate` returning *OK* would assert admissibility the records cannot
  establish, for a request that may still fail mid-iteration: `NOT_RUN` reported
  as `PASS`, at the API layer. Additive later.
* `GET /v0/capabilities` — no aggregated registry and no planner exist, so it
  would publish discovery no caller can act on, and building the aggregation
  would put a list of domain names into a would-be-universal layer.
* `GET /v0/profiles` — the reviewer's non-speculative substitute, deleted on a
  smaller argument: a refusal for an unknown execution or profile **names the
  admissible set**, so a second surface restating it carries no independent
  meaning.

**The status line never claims a scientific verdict.** `STATUS_FOR_CODE` is a
literal, total mapping over the eight refusal codes, and it has **no entry for a
non-convergent run**, because a non-convergent run is not a refusal.

| Code | HTTP |
|---|---|
| `malformed_request`, `unsupported_schema_version`, `unknown_execution`, `unknown_execution_profile` | 400 |
| `scientific_admission_refused` | 422 |
| `provider_execution_failed` | 502 |
| `subsolver_execution_failed`, `unclassified_internal_failure` | 500 |
| *(no refusal — including a run that did not converge)* | **200** |

Routing faults (404, 405), an unreadable `Content-Length` (400) and an oversize
body (413) return `{"error": "..."}` with **no schema string, no `status`, no
refusal code** — they are transport facts and the boundary never saw a request.
`decode_failure` is reserved for a body that *was* read and could not be
decoded.

---

# G. MCP surface

**One tool, `crafty_run`.** `crafty_validate` and `crafty_capabilities` deleted
for the same reasons as their HTTP counterparts. Protocol: JSON-RPC 2.0,
newline-delimited over stdin/stdout, in a separate OS process; `initialize`,
`tools/list`, `tools/call`, and nothing else.

`tools/list` publishes `request_json_schema()` as the tool's `inputSchema` — the
same object derived from the validator's constants. **This is a genuine
HTTP/MCP asymmetry and is recorded rather than repaired:** MCP has a built-in
discovery channel; HTTP in v0 does not, and §F declines to invent one.

## G.1 The declared framing asymmetry

A **scientific** refusal — malformed request, unsupported version, unknown
execution, inadmissible declaration, provider failure — is a *successful tool
call whose structured content reports the refusal* (`isError: false`). An agent
must be able to read why Crafty refused; an opaque error invites a blind retry,
and a retry loop against a deterministic refusal is the failure mode this
framing prevents. A malformed **JSON-RPC envelope** is a JSON-RPC error.

HTTP maps the same refusals to 4xx/5xx **with the identical payload**. The two
transports therefore disagree about framing and agree about everything the
payload says. That was preregistered (§8.3) as the one place they were free to
disagree, and the differential compares the payload and never the framing.

## G.2 The LLM boundary

```text
LLM proposes  ->  Crafty admission  ->  Crafty execution
              ->  Crafty's convergence / validation / provenance
              ->  the agent may only EXPLAIN
```

The tool handler decodes a frame, calls `handle`, and encodes the result. It
cannot interpret validity, alter a convergence verdict, choose a solver outside
the closed enumeration, select a command, or construct provider semantics —
**because none of those is expressible in the request**, not because the handler
declines. The tool description tells the agent in as many words that a
budget-exhausted run is a successful execution and must not be retried as an
error.

---

# H, I, J. Direct, HTTP and MCP results

`ET-VERTICAL` CASE A, reproduced through each path, to the preregistered exact
targets.

| | Direct | HTTP (socket, separate process) | MCP (stdio, separate process) |
|---|---|---|---|
| `status` | `executed` | `executed`, HTTP **200** | `executed`, `isError: false` |
| `coupling.outcome` | `criterion_met` | `criterion_met` | `criterion_met` |
| iterations | 10 | 10 | 10 |
| `final_temperature` | **338.5770175652607 K** | same | same |
| `resistance` | **11.785281808946952 Ω** | same | same |
| `resistor_power:R1` | **2.1212899619439667 W** | same | same |
| participants | 3 | 3 | 3 |
| provenance bindings | 5 (3 solvers, 2 realizations) | 5 | 5 |

Preregistered targets were `338.577018 K`, `11.785282 Ω`, `2.121290 W`,
10 iterations, to `1e-6` absolute. **None was adjusted.**

**Both transports crossed real boundaries.** A test asserts
`http.pid != os.getpid()`, `mcp.pid != os.getpid()`, `http.pid != mcp.pid`, and
that both child processes are alive — because if these were in-process wrappers
the whole differential would collapse to "one function returned the same value
three times".

---

# K. Differential comparison

Same request document, same `run_id`, all three paths.

| | Compared | Result |
|---|---|---|
| 1 | 13 scientific quantities, matched by `(problem_id, quantity)` | **worst relative difference 0.0.** Preregistered acceptance was `≤ 1e-12`. |
| 2 | unit strings, compared as strings and never converted | identical |
| 3 | coupling block (`outcome`, `criterion_met`, `iterations_run`, tolerance, iterate-change history) | identical |
| 4 | per-participant `validation_status` and `attained_levels` | identical |
| 5 | per-participant `numerical_convergence` | identical |
| 6 | provenance execution identities, as `(model, version, realization, solver, version, backend)` tuples | identical and non-empty |
| 7 | whole parsed payload | structurally equal on all three |

Repeated on the **non-convergent** case, because agreement on a converged run
does not show the transports agree about *disagreement*: all three report
`executed` / `iteration_limit_reached`, HTTP 200, MCP `isError: false`, payloads
identical. And on a **refusal**: identical payloads, HTTP 422, MCP a completed
call.

**What (7) is worth, said plainly.** Both transports serialize the same dict
object produced by the same `handle`, with the same `json.dumps(..., sort_keys=True)`.
Structural equality therefore measures that **neither transport mutates the
payload** — worth knowing, and close to tautological. It is a measurement, not a
clause of `crafty_execution_response/1`, and no consumer may rely on it.

The load-bearing comparisons are 1–6, and what they establish is that the same
boundary is reachable across a process boundary by two different wire protocols
without either perturbing a scientific number, a unit, a verdict or an identity.

---

# L. Convergent case

Configuration A above. `criterion_met` in 10 sweeps.

The transported endpoint remains load-bearing through the external contract:
switching `transported_temperature` from `final_temperature` to
`steady_state_temperature` — **one enumerated string in the request, no code
change** — moves the converged answer by **3.376418 K**. Both are kelvin, so no
dimension check can separate them. This is `ET-VERTICAL`'s measurement,
reachable from outside, and it is why the field is an enumeration rather than a
free string.

Real `ngspice-42` at `/usr/bin/ngspice`, substituted into the electrical slot of
the coupled loop through the `ngspice` execution profile, over HTTP:
`criterion_met`, **identical iteration count**, `final_temperature` agreeing
with the native profile to **relative 1.8e-15**. Provenance reports
`solver_id = engcore.electrical.dc.ngspice`, `backend = ngspice` truthfully;
nothing else in the response differs.

---

# M. Non-convergent case

Configuration A with `max_iterations = 2`.

```text
status                        executed          <- the boundary handled it
coupling.outcome              iteration_limit_reached
coupling.criterion_met        false
iterations_run                2
participants[*].numerical_convergence   converged / not_applicable
participants[*].validation_status       pass
HTTP status                   200
MCP isError                   false
```

**Every sub-solve reports success in a run whose coupling did not converge.**
This is `ET-VERTICAL`'s sharpest single measurement carried outward intact. A
boundary that computed one from the other would report this run as converged, or
would report three healthy solves as failures.

`torn_endpoints[*].final_value` is named for what it is on **both** exit paths:
on a budget-exhausted run it holds an unconverged iterate, and a field called
`converged_value` would be one name meaning two things. Asserted by test that
the string does not appear.

---

# N. Admission rejection — DETECTION != ENFORCEMENT

Six inadmissible requests, one per distinct admission site, none of whose
refusals is written in the application layer:

| Request | Refused by |
|---|---|
| `reference_resistance = -10 Ω` | `TemperatureDependentConductor.__post_init__` |
| `heat_capacity` in volts | `Quantity.require_compatible` |
| `source_voltage` unit `kilohm` | pint, via `normalize_unit` |
| `heat_capacity = 0` | `ThermalBody`'s positivity check |
| `tolerance` in `degC` | `engcore.coupling.scales.is_ratio_scale` — see §Q |
| duplicate `component_id` | `CoupledElectroThermalSystem.__post_init__` |

All six return `status: refused`, `code: scientific_admission_refused`,
`stage: admission`, `result: null`, HTTP 422.

**The proof is instrumentation, not inspection.** Three chokepoints are
monkeypatched to raise if reached — the coupling loop itself
(`run_fixed_point`), the pack's own native circuit solve (`solve_circuit`), and
`subprocess.run` — and the assertion is
`(spies.loop, spies.native_solve, spies.process) == (0, 0, 0)`.

**And it is stronger than "no process launched."** `PROFILES[profile]()` is the
**last** statement of `prepare`, after every admission check, so an
inadmissible request never reaches profile resolution — **not even a solver
object is constructed.** That distinction is worth stating because a resolver
could in principle open a file, read a case directory or contact a licence
server, none of which the three chokepoints would see. Asserted with a probe
that also fires on an admissible request, so it can fail.

A refusal also carries **no scientific verdict of any kind**: a test asserts the
strings `criterion_met`, `iteration_limit_reached`, `converged`,
`validation_status` and `attained_levels` are absent from a refusal payload.

**No `admit()` gate was introduced.** A test asserts no function named `admit`,
`validate_request` or `check_request` exists in the application layer. Admission
stays where the knowledge is; what this milestone adds is a measurement of the
ordering.

**Two honesty requirements follow, and both are honoured.** `unsupplied()` is
"reported, never refused", so *admitted* does not mean *will execute* — and the
external contract has no state meaning *validated*, which is also why
`/v0/validate` does not exist. And the guarantee earned is exactly a spy count
over the enumerated hostile inputs and the six sites above, not a structural
ordering property.

---

# O. Provider failure

Two ways, both executed.

**In process**, with `NgspiceInvocation.run` patched to raise:
`status: execution_failed`, `code: provider_execution_failed`,
`error_type: NgspiceExecutionFailure`, `result: null`, HTTP 502.

**Across a real socket**, with the HTTP server process started against a
sentinel provider that records its own launch and exits non-zero: same
classification, and the sentinel's marker file proves the process really ran.

**A provider failure is never a scientific verdict.** `result` is `null`, so
there is no coupling outcome, no participant list and no validation status to
misread. A test asserts those strings are absent from the payload, along with
the provider's path, the interpreter path and any traceback.

The classifier honours a split the domain already made: `NgspiceProviderError`
deliberately does **not** inherit `ScientificCoreError`, so "the provider was
not installed" can never be read as "the science does not hold". After the
adversarial pass, the universal layer no longer knows a provider's name — it
asks the resolved execution module which failures mean *a provider broke*.

**A hostile provider configuration does not degrade the native path**: the same
server serves configuration A on the `native` profile correctly while its
provider is a failing sentinel. Asserted.

---

# P. Injection and the process boundary

## P.1 The finding: a reproduced remote code execution

`architecture-falsifier` found, and this milestone then **executed**, the
following. `inputs.stages[i].component_id` was type-checked only. It flowed into

```text
component_id -> CoupledElectroThermalSystem.circuit_id
             -> DCCircuit.circuit_id
             -> build_netlist's deck TITLE LINE:  f"crafty {circuit.circuit_id}"
             -> subprocess.run([*command, "-b"], input=netlist)
```

A newline inside the identifier ends the title; every character after it is
parsed by the provider as deck input. Sending

```json
"component_id": "R1\n.control\nshell touch /tmp/crafty-injection-proof\n.endc"
```

with `execution_profile: "ngspice"` **created the file**, and the run returned
`status: executed`, `coupling.outcome: criterion_met`, every sub-solve passing,
and a `ProvenanceRecord` describing the circuit that was *declared* rather than
the one that was solved. Provenance that lies is worse than provenance that is
absent.

The provider adapter's own rule, in its own docstring, is *"no Crafty identifier
ever has to be SPICE-legal"* — `_provider_names` **assigns** `n{i}`, `r{i}`,
`v{i}` and escapes nothing, deliberately. The title line was the one place that
rule was not applied.

## P.2 Two independent repairs

1. **The channel is removed, not filtered.** The deck title is now the constant
   `"crafty circuit"`. The provider ignores it; Crafty's circuit identity
   travels on the prepared solve and in provenance, where it is checked. This is
   the load-bearing repair and it applies the module's own "assign, never
   escape" rule.
2. **Defence in depth at the boundary.** An externally supplied Crafty name is
   constrained to `^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$`, applied to
   `component_id` and `run_id`, published in the schema as `pattern` +
   `maxLength`. It is compiled with `\A`/`\Z` rather than `^`/`$`, because
   Python's `$` also matches before a trailing newline while JSON Schema's does
   not — so the naive form would have been *stricter published than enforced*,
   on exactly the character the class exists to refuse. A 16-probe test asserts
   the two forms agree.

## P.3 The test that could not have caught it, and why

The original injection test asserted `response["result"] is None`. But `_Spies`
makes the coupling loop **raise**, so an *admitted* hostile request also
produced `result is None` and the test passed while the request was accepted.
The test could not distinguish "refused" from "admitted, then blocked by the
spy".

It now asserts `(spies.loop, spies.native_solve, spies.process) == (0, 0, 0)`.
The cross-process sentinel list gained `component_id` and `run_id` mutations
under the `ngspice` profile — the sentinel records `argv`, not stdin, so it
could not have detected netlist injection even had it been attempted.

**This is the milestone's most valuable finding and it is a process finding:
the security claim was stated at architectural strength on the basis of a test
that could not have falsified it.**

## P.4 What is executed now

* The reproduced exploit string, as a named regression, under **both** profiles.
* 13 hostile strings × 6 string-valued fields, in process, all refused with
  zero invocations of all three chokepoints and no marker file.
* Executable paths, shell fragments, command substitution, backticks, argv-shaped
  objects, traversal, `file://`, NUL bytes, over-length names, leading dots.
* Over a **real socket** to a server whose provider is a launch recorder: every
  hostile profile, every unknown execution, an unsupported schema version, and
  an inadmissible declaration — **marker file absent**. Then one legitimate
  provider request: marker present, `provider_execution_failed`, 502. Both
  halves in one test so ordering cannot drift.
* Shell-like **unit strings** die in pint's unit-expression parser, which is the
  only parser any external free-form string reaches:
  `__import__("os").system(...)`, `eval("open(...)")`, `1;import os`,
  `ohm; rm -rf /`, backticks, `/usr/bin/ngspice`, `ohm|sh` — all
  `UnitCompatibilityError`, no file created.
* A source audit asserting the application layer and both transports call no
  `eval`, `exec`, `__import__`, `import_module`, `system`, `popen`, `spawn*`,
  `exec*`, `check_output`, `check_call`, and import no `subprocess`, `shlex`,
  `pickle` or `os.path`. And touch no `environ`/`getenv`/`putenv`, so a request
  can never reach `CRAFTY_NGSPICE_ARGV`.
* Each profile resolver takes **zero arguments** — asserted by `inspect` — which
  is the structural reason no external string can influence a provider
  invocation: there is nowhere for one to go.

## P.5 The claim, restated to be exactly true

> **No field of an external request can become a subprocess executable, a shell
> fragment, a filesystem path, a dynamic import, or an `eval`/`exec` target.**

Separately, and not a contradiction: numeric **magnitudes** do reach provider
input text, as `%.17g` of a `Quantity`-checked finite float, so the reachable
alphabet from a request in provider stdin is `[0-9+-.eE]`. `Quantity` refuses
non-finite magnitudes, so `nan` and `inf` cannot be sent.

This claim was **false in the first implementation** and was found by adversarial
review rather than by the milestone's own tests. That is recorded here in the
claim itself, not in a footnote.

---

# Q. The affine-tolerance defect, found by measurement

Independent of the falsifier, and found while writing the admission tests.

A request with `"tolerance": {"value": 1e-6, "unit": "degC"}`:

```text
canonicalized to    273.150001 kelvin
outcome             criterion_met
iterations_run      1
reported            344.272271 K
truth               338.577018 K
error               5.695253 K
```

Every sub-solve passed, every record was self-consistent, and nothing anywhere
reported a problem. `engcore.coupling.scales.is_ratio_scale` exists precisely to
refuse this — and **could not fire**, because the application layer's unit
canonicalization had already turned `degC` into a perfectly acceptable kelvin
before the plan ever saw it.

**The general lesson: a boundary that canonicalizes can disable a downstream
guard, and the guard's absence is invisible because it never runs.** The
`COUPLING-PACK-RELOCATION` guard was not weakened, deleted or bypassed; it was
starved.

Repaired by checking `is_ratio_scale` on **the caller's unit, before
conversion** — the existing contract, not a second copy of the rule — through a
`difference` argument on `parse_quantity`. It is **required and keyword-only**
with no default, so the unsafe answer is never the silent one and a new field
cannot be added without answering the question. An absolute temperature in
`degC` (`seed_temperature`, `ambient_temperature`) still works and still
converts correctly.

The constraint is now **published as well as enforced**: the schema's `unit`
description for `tolerance` says a conventional-zero unit is REFUSED even though
dimensionally compatible. The drift guard records every `parse_quantity` call
actually made during one admission — 11 of them — and resolves each to its
published schema node, asserting the constraint text appears if and only if the
field is a difference.

---

# R. Abstractions introduced

| Name | Why it survived reduction |
|---|---|
| `crafty_execution_request/1` / `crafty_execution_response/1` | The external contract must version independently of the internal records. `require_schema` is exact-string with no migration path. |
| `handle(payload) -> payload` | The single boundary. A function, not a class. |
| `RefusalCode` (8 members) | The A–H taxonomy, none collapsed to "error". Non-convergence is deliberately **not** a member. |
| `ExternalRequestRefused` | One new exception, carrying a fact no existing Crafty error carries: *this document is not a request*. `ScientificCoreError` means the science was refused; `NgspiceProviderError` means the provider broke; neither can say this. |
| `IDENTIFIER_PATTERN` / `require_identifier` | Defence in depth for §P. |
| the execution-module protocol (`EXECUTION_ID`, `PROFILES`, `prepare`, `request_fragment`, `provider_failure_types`) | Five published names, no base class. It is what keeps the universal layer from naming a domain. |
| `CircuitSolver` + `circuit_solver` keyword (system pack) | The narrowest available seam: it substitutes *how a DC circuit is solved*, not how the coupling is executed. One keyword whose type is the callable the pack already had. |

## R.1 Abstractions deleted or deferred

R-3…R-9 above, plus, after the adversarial rounds: the platform-wide `PROFILES`
dict (relocated onto the execution), the `circuit_solver=None` silent fallback,
the `run_id` default, and the `difference=False` default. Deferred with their own
evidence required: async, a second execution, a result-shape abstraction, an
HTTP discovery endpoint, and any bulk-data representation.

---

# S. Architecture fitness — the sixteen questions

| # | Question | Answer |
|---|---|---|
| 1 | frozen scientific-core contract changed? | **No.** `src/engcore/scientific/` byte-unchanged, asserted. |
| 2 | existing scientific schema changed? | **No.** All seven core and coupling schema strings asserted unmoved. |
| 3 | migration required? | **No.** Nothing serialized changed. |
| 4 | transport-specific branch in scientific core? | **No.** `engcore/coupling/`, `engcore/domains/thermal*`, `engcore/systems/fluidthermal/` byte-unchanged. |
| 5 | HTTP/MCP type imported by core? | **No.** A guard now covers `scientific/`, `coupling/`, `domains/`, `systems/` **and** `application/` — the pre-existing guard covered only the first (reviewer CH-3). |
| 6 | solver/provider internals leaked into external semantics? | **No.** The profile name is a Crafty identity from a closed enumeration; argv, timeout, deck, analysis statement, node naming and version probe are all unreachable. Provenance reports the concrete solver truthfully and independently. |
| 7 | arbitrary executable/provider path externally controllable? | **No — after two repairs.** It **was** (§P), through a channel no one had looked at. |
| 8 | metadata escape hatch introduced? | **No.** No free-form mapping anywhere; an extra key at any of seven levels is refused. |
| 9 | duplicated scientific execution code? | **No.** One entry point, one call. A test asserts the one execution-specific module contains no arithmetic beyond `+` and `|`. |
| 10 | Direct/HTTP/MCP use the same boundary? | **Yes**, and Direct *is* the boundary rather than a third adapter. |
| 11 | convergence preserved? | **Yes**, per participant and per coupling, never derived from one another. |
| 12 | validity preserved? | **Partly, and reported as such.** Validation verdicts and attained levels travel; model applicability is reported as *not assessed* because the executed path assesses none (§E.3). |
| 13 | provenance preserved? | **Yes.** 5 bindings, 3 solvers, 2 realizations, identical across all three paths. |
| 14 | unsupported schema fails loudly? | **Yes.** Six probes including a plausible `/2` and two internal schema strings. |
| 15 | admission failure stops execution? | **Yes**, measured at three chokepoints across six admission sites (§N). |
| 16 | could a fourth transport reuse the boundary from its published contract? | **Yes**, with two caveats now closed: the contract publishes the `(execution, profile)` relation and the ratio-scale constraint, both of which it originally stated falsely. `MAX_REQUEST_BYTES` and identifier uniqueness are published as prose, since JSON Schema cannot express them. |

The only "yes" in 1–9 is question 7's historical form, and it is the milestone's
headline finding rather than a footnote.

---

# T. Falsifier findings

Two rounds, the maximum §60 permits.

## T.1 Round one — **FALSIFIED**

One `BLOCKER`, six `BREAKING-RISK`, all closed.

| | Finding | Closed by |
|---|---|---|
| **C-1** | **BLOCKER.** RCE through `component_id` → deck title line → provider stdin. Reproduced. | §P.2, both halves, plus the repaired test |
| C-2 | The "transport-neutral" boundary was hard-wired to one domain's solver seam: `catalog.py` imported `CircuitSolver`, and `execution` / `execution_profile` were validated independently, so a fluid coupling with `"ngspice"` would have parsed. | `PROFILES` relocated onto the execution; profile validated against the resolved execution; schema publishes the relation |
| C-3 | HTTP dressed routing faults in the scientific response envelope; MCP did not. | `_routing_fault` returns `{"error": ...}` — extended in round two to size faults |
| C-4 | `project_run` silently dropped `data_references`, the exact reader `DATA-BOUNDARY0` bumped a schema to prevent. | raises instead — and see N-1 |
| C-5 | The published schema was **false about `tolerance`** — the one field Q's measurement was about — and the drift guard checked names, not constraints. | constraint published; guard rebuilt (§Q) |
| C-7 | `difference` defaulted to the unsafe value. | required keyword-only |
| C-8 | `run_id` defaulted, and the preregistration's justification ("only a provenance string") was **factually false** — it also becomes `ScientificResult.result_id`. | required and identifier-constrained (D-2) |

## T.2 Round two — **SURVIVES WITH REQUIRED CHANGES**

No `BLOCKER`. It verified every round-one repair as real, found C-3 and C-5
incomplete, and found C-4 *real in intent, incomplete in placement*. Three
`BREAKING-RISK`, all closed:

| | Finding | Closed by |
|---|---|---|
| **N-1** | **C-4's own repair sat outside the classifier.** `project_run` was evaluated in the success `return`, outside every `except`, so its refusal escaped `handle` — contradicting *"the classifier is total"* and prereg §4. On HTTP a dropped connection; on MCP a terminated server. The test that added the refusal called `project_run` directly and could not see it. | a fourth `_PROJECTION` stage inside the `try`; test routed through `handle`; plus a test that `handle` returns a payload for ten shapes of input and never raises |
| N-2 | Two size guards, two kinds of object: HTTP answered an oversize body with a boundary envelope while MCP's new frame guard answered the same fact with a JSON-RPC error — a *second* undeclared divergence created by round one's own fix. | both routed as transport faults, plus `Connection: close` so an undrained body is not parsed as the next request; the missing MCP test added |
| N-7 | The response is coupling-shaped and the published protocol did not say so: `prepare(...).run(...)` must return a `CoupledRun`, which is why `result.coupling` and `result.torn_endpoints` exist. A single-solve execution has no honest `outcome`. | documentation only (§E.4), asserted by test. **No result-shape abstraction built.** |

Also closed from round two's lower-severity list: the drift guard's four holes
(N-3), the untested MCP frame guard (N-5), `provider_failure_types` failing open
(N-6b, now asserted present for every execution), and the two unpublished
enforced refusals (N-4).

**Round two also found a latent defect this milestone's own repairs introduced:**
the relocated provider resolver's relative import was one level too deep, so
*every* `ngspice` request classified as `unclassified_internal_failure` /
`ImportError` instead of running. It was caught by re-running the cross-process
test; nothing in process would have seen it. Two in-process tests now cover it.

## T.3 Findings recorded and deliberately not fixed

`_admit_element_power`, the provider's admission gate, is **NaN-transparent**:
`float("nan")` parses, and every `abs(a - b) > tol` comparison against NaN is
`False`, so both reconciliation relations and the passive-sign guard pass.
Nothing unsafe escapes — `Quantity` refuses non-finite magnitudes on the very
next line — but the resulting `UnitCompatibilityError` is raised *inside* the
loop, so a provider emitting `nan` is classified `subsolver_execution_failed`
(500, case F) when the true condition is *the provider returned something it
could not deliver* (502, case E). **§8.2's E/F assignment does not hold for that
input.** Repairing it means editing the provider's admission gate, which is
outside this milestone's scope; it is carried forward in §U.

---

# U. Known unknowns

1. **Model applicability is externally invisible** (§E.3). The single most
   valuable thing exposure taught us about the existing coupled contract.
2. **A provider emitting `nan` is misclassified** as a sub-solver failure rather
   than a provider failure (§T.3).
3. **Nothing about concurrency, scale, latency, persistence, auth, restart or
   hostile network conditions.** `ThreadingHTTPServer` ships and is untested
   under concurrency. `MAX_ITERATION_BUDGET = 200` is the only work bound, and
   one 200-sweep provider run is 200 subprocess launches inside one request.
4. **One execution, one system pack, one scalar consumer.** Fluid-thermal
   satisfies the protocol on inspection — its entry point returns a `CoupledRun`
   — but has not been wired. A **single-solve** execution does not fit v0 and
   needs `crafty_execution_response/2` (§E.4).
5. **The ordering guarantee is a spy count**, over the enumerated hostile inputs
   and six admission sites, not a structural property. Prereg R-7 chose that
   trade deliberately.
6. **The response is lossy** (§E.2), and `run_id` reuse can mint two results
   sharing a `result_id` — published, unenforced, because enforcing it needs
   state the boundary deliberately does not hold.
7. **Whole-payload equality is close to tautological** (§K).
8. **The exec-spec exception sets grow monotonically with no expiry**, so those
   two guards' meaning decays with each milestone that adds to them.

---

# V. Per-claim evidence

| Claim | Decision status | Evidence |
|---|---|---|
| One transport-neutral boundary serves Direct, HTTP and MCP with no transport-specific scientific logic | `PROPOSED` | **`L1 EXERCISED`** |
| The external contract keeps the five distinctions apart | `PROPOSED` | **`L1 EXERCISED`** |
| No external field becomes a subprocess executable, shell fragment, path, dynamic import or eval/exec target | `PROPOSED` | **`L1 EXERCISED`** for the audited flow — and it was **false** in the first implementation. Not `L3`: no fuzzing, no hostile network. |
| No solver runs, no solver object is constructed and no process launches after an admission refusal | `PROPOSED` | **`L1 EXERCISED`**, three chokepoints × six sites, a resolver probe, and a cross-process sentinel |
| Budget exhaustion is `executed` / `iteration_limit_reached` / HTTP 200 | `PROPOSED` | **`L1 EXERCISED`** |
| A provider failure never becomes invalidity or non-convergence | `PROPOSED` | **`L1 EXERCISED`**, with the `nan` exception recorded in §T.3 |
| Transport independence at `L2` | — | **EXCLUDED BY PREREGISTRATION.** Two transports by one author on one day against one interface are what §54.1 excludes from "materially different consumers". |
| Anything about async, scale, concurrency, auth, persistence | — | **zero** |

**No existing Crafty holding moved.** `MODEL0-R`, `DATA-BOUNDARY0`,
`MIN-FOUNDATION-ET`, `ET-VERTICAL`, `HETERO-NGSPICE`, `HOSTILE-CORE-STRESS`,
`CROSS-DOMAIN-COVERAGE`, `EXEC-SPEC`, `MIN-CROSS-DOMAIN-FOUNDATION`,
`MIN-FIELD-SUPPORT-FOUNDATION`, `FT-SCALAR-COUPLING` and
`COUPLING-PACK-RELOCATION` are unchanged. `ScientificTwin` gains zero evidence
from this milestone — it is neither built nor read anywhere on the external
path — continuing the run §68.4 was tracking at four.

---

# W. Deviations from the preregistration

**D-1 — fail condition 1 was TRIGGERED, deliberately.** The preregistration
named `src/engcore/domains/` byte-unchanged. Closing the reproduced RCE (§P)
required one line of `src/engcore/domains/electrical/ngspice.py`: the deck title
became a constant. The alternative was to publish an API with a reproduced
remote code execution behind it in order to preserve a fail condition — scoring
the metric while doing the damage, which §59.1 warns about by name. The change
is one line of executable source plus a comment; a test asserts the diff is
exactly that line and that no Crafty identifier can reach deck text.

**D-2 — `run_id` is required, not optional.** Prereg §5.1.9 made it optional
with default `"crafty-v0"` on the stated ground that it "is used only as a
provenance string". That is **false**: it also becomes
`ScientificResult.result_id`, so every caller omitting it would mint results
whose scientific identity is one shared literal. Requiring a field is a
narrowing that cannot be applied after publication.

**D-3 — `PROFILES` moved from the catalog to the execution module.** Prereg
§6.2 sketched a platform-wide `PROFILES = {"native": None, "ngspice": ...}`.
That shape made the universal layer name a *circuit* and validated the two
enumerations independently. The implementation also improved on the `None`
sentinel: `PROFILES` maps to zero-argument resolvers, so `prepare` has no silent
native fallback.

Two further clarifications, not deviations: `execution_profile` is required (the
prereg permitted no default and the implementation has none), and the published
JSON Schema was not preregistered as a deliverable — it exists because fitness
question 16 needs it.

---

# X. Tests and regression

| Tier | Baseline | Now | Δ |
|---|---|---|---|
| **FAST** (`-m "not expensive"`) | 1602 | **1681** | +79 |
| deselected | 603 | **625** | +22 |
| **FULL** | **2205 passed / 0 failed / 0 errors** | **2306 passed / 0 failed / 0 errors** | +101 |

The FULL figure was measured as two **disjoint and exhaustive** tiers —
`-m "not campaign"` (2302 passed, 257 s) and `-m "campaign"` (4 passed, 541 s) —
because this machine suspends a background process between commands and the
whole suite exceeds one foreground command's budget. An earlier single-process
run of the whole suite on the same tree returned **2305 passed / 0 failed /
0 errors in 854 s**; it was collected one test before the final admission-order
probe was added, which is the entire difference.

New modules:

* `tests/test_api_mcp_v0.py` — 79 tests, FAST. Boundary semantics, the eight
  taxonomy rows, admission ordering with spies, injection, serialization,
  architecture fitness, the reduction attacks, and the two drift guards.
* `tests/test_api_mcp_v0_transports.py` — 22 tests, labelled `expensive`.
  Real HTTP server process over a TCP socket, real MCP server process over a
  stdio pipe, the three-way differential, and real `ngspice-42`.
* `tests/api_v0_case.py` — the shared canonical request, so the three paths are
  demonstrably handed the *same document*.

**Pre-existing tests edited: four, and all four are mechanical.**
`tests/conftest.py` gains one tier label. `tests/test_executable_scientific_spec.py`
and `tests/test_exec_spec_structured_input.py` gain a documented
`_API_MCP_V0_EXCEPTIONS` set and a new-tree prefix filter for their
"`src/` untouched" guards — the exact pattern those files already carry for
three earlier milestones, and it does not weaken their claims, which were true
when they were written. No assertion of any pre-existing test was changed, no
tolerance loosened, no test skipped or deleted.

**Source added:** 2 234 lines across 13 new files under `src/` — the application
layer (5 modules + 2 execution modules) and the two transports. **Source
edited:** 3 files — the additive `circuit_solver` seam and its export, and the
one-line RCE repair.

---

# Y. Final decision

**KEEP.** `PROPOSED` / `L1 EXERCISED`. Nothing is frozen.

The primary question — *can Direct Python, HTTP and MCP invoke the same Crafty
application boundary while preserving the same scientific semantics, admission
behaviour, execution meaning, convergence, validity and provenance?* — is
answered **yes**, at `L1`, with three qualifications that are part of the answer
rather than caveats on it:

1. **The null hypothesis did not win, but it drew blood.** H0(b) predicted that
   exposure would either force a second scientific architecture or leak
   internals. No second architecture was forced — no `admit()` gate, no planner,
   no registry, no job platform, and the internal execution boundary was reused
   unchanged. But the **first implementation did leak**, in the worst available
   way: an external field reached a provider's own command language and executed
   a shell command while the platform reported a converged, validated result. It
   was found by adversarial review, not by the milestone's own tests, and the
   test written to catch it was structurally incapable of doing so.
2. **Exposure surfaced two defects in the existing platform that were not about
   the API at all** — the affine-tolerance hole a canonicalizing boundary
   starved (§Q), and the fact that the executed coupled path assesses no model
   applicability, so no transport can report one (§E.3).
3. **`L2` is not claimed and was excluded before any result existed.** HTTP and
   MCP really did cross a socket and a pipe into separate processes, and the
   differential really is 0.0 across 13 quantities. That is evidence the boundary
   survives a process boundary. It is not evidence of two materially different
   consumers, and §54.1 says so.

---

# Z. Exact next milestone

**`MIN-FOUNDATION-PDE`** — unchanged in name from §67.5/§68.5 and still the
highest-value open question. Its entry condition is unchanged and binding: a
**real** consumer, not a probe, and the preregistered preference is promotion of
the 2-D scalar transport consumer into a real domain pack.

**This milestone adds one input to it and one to the roadmap.**

* `project_run` **refuses** a result carrying `data_references`, loudly, by
  design. `MIN-FOUNDATION-PDE`'s consumer is the first that will produce one, so
  that refusal is the concrete trigger for deciding what a field-valued external
  response *is* — which is `FIELD0`/`DATA-BOUNDARY0`'s deferred question reached
  from the outside for the first time.
* **`API-MCP-V1` is not next and should not be.** The three things v0 measured
  as missing are: an external representation of model applicability (§E.3), a
  second execution shape that is not an iterative coupling (§E.4), and anything
  at all about concurrency. None is worth building before a second real consumer
  exists to force its shape.

Explicitly **not** started, and unchanged: Scientific Planner, natural-language
interface, UI, auth, database, job queue, async runtime, OpenFOAM, FEniCSx,
HVAC, `FIELD0`, `TOPO0`, CasADi.
