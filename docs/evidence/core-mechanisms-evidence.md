# CORE-MECHANISMS — evidence

Six mechanisms, every domain inherits each. A domain defect is one domain's; a
core defect is silently in all five domains and in the sixth nobody has
written. This document records what was measured, not what was intended.

**Not a preregistration.** No prediction was registered before the work; each
section below was written after the measurement it reports, and says so where
a finding contradicted the plan.

---

## 0. Baseline

Environment note: the `.venv` the task list names did not exist in this
checkout. It was recreated (Python 3.14.2, `pip install -e .[dev]`); the
editable install rewrote the **tracked** `src/engineering_ai_core.egg-info/`,
which was restored with `git checkout`. `PYTHONUTF8=1` is required — without
it `subprocess.run(..., text=True)` decodes git output as cp1252 and
`test_ft_coupling_records` dies on a UTF-8 em dash.

Three guards were red before any mechanism was touched, for reasons unrelated
to any scientific claim, and **two of them could not pass on Windows at all**:

| Guard | Why it could not pass | Repair |
|---|---|---|
| `test_executable_scientific_spec.py::test_the_boundary_condition_channel...` | compared `str(PurePath)` — the native separator — against a POSIX literal. Red since `3ad87af` on every Windows checkout. | `.as_posix()` |
| `test_api_mcp_v0_transports.py::test_nothing_a_request_can_say_launches...` | handed an unquoted Windows path to `shlex.split`, whose POSIX rules eat `\` and split on spaces; this repo's checkout path contains a space. The sentinel provider was never launched, so the guard's second half could not pass. | `shlex.join` |
| `test_composite_system0.py::test_t6f...` | reported two untracked read-only architecture studies | named individually |

Committed as `642ae5a`, before any mechanism work. **A guard that cannot pass
measures nothing — it is the mirror of the guard that cannot fail.**

| Tier | Before repair | After repair (`642ae5a`) |
|---|---|---|
| FAST `-m "not expensive"` | 2 failed, 1952 passed | **1954 passed** |
| SCIENTIFIC `-m "not campaign"` | 3 failed, 2573 passed, 1 skipped | **2576 passed, 1 skipped** |

**The benchmark could not be run.** `benchmarks/hard/score_hard.py`, its
`cases_hard` directory and `results_hard.json` **do not exist in this
repository or in any commit of its history** (`git log --all -- '**/score_hard.py'`
is empty; `benchmarks/` contains only `k2_compute_efficiency/` and
`perf_runtime_audit/`). The four metrics — catch rate, false accept, false
reject — are therefore **not measurable here**, and the standing rule that
they must not move is unverifiable rather than verified.

---

## 1. The declared core scope

Eleven historical guards assert `src/engcore/scientific/` is byte-untouched
since their own milestone's base commit. Each is correct about its own
milestone and fails for every later milestone that changes the core, however
correct that work is. CORE-MECHANISMS is the first milestone whose entire
subject **is** the core, so all eleven fire at once.

The repository's established repair is to name the changed files individually
in each guard. Doing that eleven times produces eleven hand-maintained copies
of one list, and a guard from a hand-maintained list guards only what someone
remembered. So the list lives once in `tests/core_mechanisms_scope.py` and each
guard subtracts it.

That is a single point of weakening, so it is a **claim, not a licence**:
`test_the_declared_core_scope_matches_the_tree_exactly` requires the set of
core files changed since `642ae5a` to equal `CORE_FILES` **in both
directions**. A name parked there that nothing changed fails as loudly as an
undeclared core edit.

Five of the eleven read a fixed base commit and were repaired. Four read
`git diff HEAD` — they measure working-tree cleanliness, not milestone scope,
and are green once the work is committed. Two more (`test_api_mcp_v0.py`)
carried the same fixed-base shape.

---

## TASK 1 — the shared UnitRegistry

### The decision, and its cost

**Enforced refusal to allow registry mutation.** Not per-run isolation.

The argument is not that mutation is unlikely; it is that **isolation is only
needed when state can change**. If the definitional content cannot change,
a shared registry is observationally identical to a per-run one, because unit
algebra over a fixed definition set is a pure function of
`(magnitude, unit string)` — and this repository's `Quantity` is its own frozen
`(float, str)` dataclass that holds no pint object, so no cross-registry
interoperation problem arises either way.

Measured costs, on pint 0.25.3 / Python 3.14.2:

| | Cost |
|---|---|
| fresh `pint.UnitRegistry()` + first quantity | **101.8 ms** (min 93.1, max 105.6) |
| warm quantity construction | 3.27 µs |
| `require_pristine_registry()` | **312 µs** |

Per-run isolation costs 101.8 ms per run and buys nothing sealing does not
already give. **The real cost of refusal is stated rather than discovered
later: a domain that needs a unit pint does not define cannot add one at
runtime.** It must be declared in `quantity.py` before the seal, where it is
reviewable and applies to every run identically. That is a genuine capability
this decision forecloses.

### Nothing mutates it today

`grep -rn "\.define(\|load_definitions\|add_context\|enable_contexts\|
set_application_registry\|autoconvert_offset\|default_format\|force_ndarray"`
over `src/`, `tests/` and `benchmarks/` returns **nothing**. Only
`units/quantity.py` and `coupling/scales.py` touch the registry at all, and
both only read.

### That the risk is real

Redefinition changes an answer without changing a count. Measured against an
**unsealed** registry:

```
before: 1 V -> 1000.0 mV
c.define("millivolt = 1e-6 * volt = mV")
after:  1 V -> 1000000.0 mV          # len(_units) unchanged
```

A new definition changes what a later run can even parse: `widget` raises
`UndefinedUnitError` before, and `3 widget = 15.0 m` after.

### Two layers, because one is not enough

**Layer A — the seal.** Every mutator-shaped member of the registry instance
is replaced by a raiser. Applied to the *instance*, not a wrapper, because
pint hands the registry back out: `registry().Quantity(1,"V")._REGISTRY` **is**
the real object (verified), so a proxy would be bypassed by any code holding a
quantity — and every quantity this module returns held one.

The mutator set is a **name-shape rule matched against `dir(registry)`**, not
a list of method names, so a mutator introduced by a future pint release is
sealed when it appears rather than when someone remembers it.

**An over-broad sweep fails loudly, which is the correct direction to be wrong
in.** It did: sealing `_add_ref_of_log_or_offset_unit` broke every degC and
log-unit conversion in the suite. Reading pint's source
(`facets/nonmultiplicative/registry.py:191`) shows it reads
`self._units[offset_unit]` and **returns a `UnitsContainer`** — the "add" is to
that container, a value, not to the registry. It writes nothing, and is the
one named exception. Every other swept name was audited the same way against
pint's source rather than by its name.

**Layer B — the content check.** `require_pristine_registry()` compares the
current definitional tables against the baseline captured at seal time. It
does not care *how* a change arrived — a route the shape rule missed, a direct
write into `reg._units`, a future pint internal. It is the difference between
a guard that knows the ways in and a guard that knows the answer.

### A finding that contradicted the first implementation

The check was first written to compare definition objects **by identity**, on
the argument that pint's three definition types are frozen dataclasses (they
are — asserted by `test_pint_definitions_are_still_frozen`) so rebinding is the
only way to change a meaning.

**That was wrong, and the suite said so.** pint legitimately *rebinds* an
existing name during ordinary lazy expansion: parsing `kg/m**3` replaces
`_units['kilogram']` with a new but **value-equal** `UnitDefinition`. Identity
comparison therefore fires on correct arithmetic. A real redefinition is not
value-equal (`ScaleConverter(scale=0.001)` → `scale=1e-06`), so **equality**
separates the two exactly. Corrected to equality; the frozen-dataclass premise
is still required (the baseline holds the objects themselves, so an in-place
edit would move both sides at once) and is still asserted.

Lazy prefix expansion also *adds* names — `millivolt`, `kilojoule`,
`microampere`, … Measured across 22 prefixed and symbol forms, **every one
decomposes as `<sealed prefix><sealed unit>`**, and a vandal addition
(`widget`) does not. That is the rule the check uses to tell them apart.

### The fail-closed proof

The mechanism is **not opt-in**. `require_pristine_registry()` is called inside
`ProvenanceRecord.__post_init__` — the one place every run already passes
through, because provenance is mandatory on every `ScientificResult`. A domain
cannot decline it by not calling something, including the sixth domain that
does not know it exists.

`test_two_runs_in_one_process_cannot_influence_each_other` constructs the
influence deliberately, in a real second process:

```
RUN 1  (some domain)   registry()._units["widget"] = registry()._units["meter"]
RUN 2  (another domain, opting into nothing)
       ProvenanceRecord(run_id="run-2")
->  UnitRegistryFrozen: provenance 'run-2': the unit registry's definitions
    changed after it was sealed: _units: 'widget' was defined after sealing.
    Every quantity computed in this process is now of unknown meaning; this
    run is refused rather than reported.
```

**The error a domain gets if it does not use the mechanism is above.** It gets
it without asking, at construction of a record it cannot omit.

### A hole this round's own mutation guard found

`test_the_mutation_is_detected[registry-check-not-at-the-run-boundary]` failed
on first run: the influence test spawned its child with bare `sys.executable`,
so the child resolved `engcore` from the **editable install** rather than the
mutated scratch tree, and the mutation test came back green against unmutated
source. Fixed by pinning `PYTHONPATH` to the `src` the parent imported from.
The guard caught a defect in its own guard on the day it was written.

---

## TASK 2 — applicability, from a note on one path to a field on every result

`ScientificResult` had no applicability field at all. The verdict existed on
exactly **one** path: the coupled electro-thermal pack's own
`AdmittedCoupledRun`, projected by the application layer as `model_validity`.

**Not fixed by editing four domains.** Four omitted it because the core
permitted omission; a fifth would omit it for the same reason. The permission
changed.

### Three states, and why three

| State | Meaning | Legal payload |
|---|---|---|
| `ASSESSED` | a validity domain was run | mapping, **possibly empty** — "assessed, and no model declared a domain" is a real answer |
| `NOT_ASSESSED` | a stated position, with a **required** reason | no assessments |
| `UNDECLARED` | nobody said anything | no reason, no assessments |

They cannot be confused: `state` is serialized in every state, round-trips,
and cannot be constructed inconsistently (`NOT_ASSESSED` without a reason is
refused; `UNDECLARED` *with* one is refused — a record that carries a reason
has said something).

`scientific_result` moves to **/3** by the rule DATA-BOUNDARY0 set for /2. A
/2 payload loads as `UNDECLARED`, never as `NOT_ASSESSED`: absence stays
absence.

### The five paths

| Path | Result | What it produced |
|---|---|---|
| `kinetics/cstr` | **ASSESSED** | see below |
| `fluids/transport2d` | **ASSESSED** | was already computing `mesh_validity` and burying it in `metadata["mesh_validity_assessment"]`, an untyped side-channel nothing could check |
| `electrical/dc` | **ASSESSED**, per component | the resistor model's condition is `resistance > 0` and a circuit has many; a per-model verdict would be one answer for components that can disagree |
| `systems/electrothermal` | already carried it | on its own record; `project_run` now derives the wire payload from the typed report so the two cannot drift |
| `domains/thermal/conduction1d` | **UNDECLARED** | **FROZEN TREE.** Reported, not worked around |

### What the CSTR's rescued assessment actually says

The solver computed `assessment = CSTR_MODEL.assess_validity(...)` before any
integration, rendered `assessment.status.value` into a note, and dropped the
rest. The note said, in full:

    'model validity assessment: in_domain'

The structured verdict that now survives on the record says:

    {
      "state": "assessed",
      "assessments": {
        "kinetics.cstr.nonisothermal_first_order": {
          "status": "in_domain",
          "satisfied": ["temperature", "concentration", "k0",
                        "activation_energy", "residence_time"],
          "violated": [], "unknown": []
        }
      }
    }

**Five named conditions**, where the note carried one word. And the reader can
now see something the note actively hid: this is an assessment **of the
declaration, before integration** — not of the trajectory. A run can be
admitted here and still leave the envelope while integrating; that is a
different question, answered by the validation stage. "in_domain" as a bare
string invited exactly that conflation.

### Fail-closed — and its honest limit

`project_run` refuses to project a result that says **nothing**. That is the
boundary where numbers become an answer someone builds on:

    ScientificCoreError: projecting an execution result: model applicability
    is UNDECLARED — the path that produced this result said nothing about
    whether its model applies to the case it was run on. Declare it: pass
    applicability=ApplicabilityReport.assessed(...) with what a ValidityDomain
    said, or ApplicabilityReport.not_assessed('<why>') to state that position
    on the record

**The limit, stated rather than papered over:** making the field mandatory at
construction would require editing `src/engcore/domains/thermal/`, which this
round may not touch. So a result can still be **constructed** undeclared; it
cannot be **projected** undeclared.

Only silence is refused. A stated position projects and is reported. A
stricter form that refused `NOT_ASSESSED` too was written first and backed
out: it destroyed a real capability rather than protecting anything.

### A `pytest.raises` hazard found while migrating

An existing test asserting the bulk-data refusal began passing **for the wrong
reason** — the applicability refusal raised the same exception type first, and
`pytest.raises(ScientificCoreError)` cannot tell two causes apart until the
`match=` is checked. Repaired by declaring applicability in that probe.

---

## TASK 3 — the evidentiary rule, and every route into a ValidationCheck

**The premise did not hold, and the real state was worse.** There is no
`record_check` in this repository and no `GUARD 2`.
`ValidationCheck.__post_init__` enforced **no evidentiary rule on any axis**.
The guard described as "complete on one axis and blind to another" was
complete on none:

    ValidationCheck(name="claims", outcome=PASS,
                    establishes=ValidationLevel.BENCHMARK_VALIDATED)
    # accepted; report.attained_levels -> ['benchmark_validated']

### The full enumeration of routes to a `ValidationCheck`

Measured with a spy on `__post_init__`, not reasoned about.

| # | Route | Before | After |
|---|---|---|---|
| 1 | `ValidationCheck(...)` | ran | ran |
| 2 | `ValidationCheck.from_dict(...)` | ran (delegates to 1) | ran |
| 3 | `dataclasses.replace(...)` | ran (calls `__init__`) | ran |
| 4 | `copy.copy(...)` | **DID NOT RUN** | ran, via `__reduce__` |
| 5 | `copy.deepcopy(...)` | **DID NOT RUN** | ran, via `__reduce__` |
| 6 | `pickle` round-trip | **DID NOT RUN** | ran, via `__reduce__` |
| 7 | `ValidationReport(checks=(...))` | accepted a non-check; refused one only **incidentally**, by `AttributeError` from a duplicate-name scan reaching `.name` | refuses for a stated reason |
| 8 | `ValidationReport.with_check(...)` | takes an already-built check → 1–6 | same |
| 9 | `object.__new__` + `object.__setattr__` | reachable by **no** construction rule | unchanged — vandalism, not a route |

4, 5 and 6 are the finding: three routes that *look* like they copy a record
rather than build one, each reconstructing a frozen dataclass without running
a single rule.

### The rule

A check that **passes** and establishes a quantitative level must carry a
residual against a tolerance, **or** named evidence. `DIMENSIONALLY_VALID` is
exempt: it is not a numerical claim. A passing check whose residual exceeds
its own tolerance is refused outright.

**A stricter form was written first and backed out.** Forbidding `establishes`
on any non-passing check turned the suite red for a good reason: on a
`NOT_RUN` or `FAIL` check that field records *what was attempted*, and "we
tried to establish benchmark validation and could not" is genuinely different
from "we never tried". Only a passing check reaches `attained_levels`, so only
a passing check can make an unbacked claim count. **The same lesson as TASK 2,
learned twice in one round.**

### Two records in the suite could not survive it, and both were defects

* `test_scientific_core.py` asserted a passing benchmark check establishing
  `BENCHMARK_VALIDATED` with nothing attached — the exact shape the rule
  refuses.
* `test_admission_gate_repair.py`'s `_withhold` rebuilt every check from four
  fields, **silently dropping `residual`, `tolerance` and `evidence` from all
  six**, while claiming to change one outcome. Repaired with
  `dataclasses.replace`.

---

## TASK 4 — refuse at construction, and refuse the SAME things

A result holding an unserializable value constructed happily; the process died
later inside `json.dumps` with a `TypeError` naming no field, no record and no
run.

### The disagreement was already real, and ran both ways

| Value | `encode()` | construction (before) | `json.dumps(to_dict())` (before) |
|---|---|---|---|
| `object()` | refuses, naming the type | **accepts** | `TypeError` |
| an `Enum` | **accepts** | accepts | **`TypeError`** |

Two refusals over one value space, disagreeing in both directions.

**The fix is not a second check.** There is now one acceptance rule with two
callers: `require_encodable` does not re-implement anything, it *runs*
`encode`, and `to_dict()` emits `encode(self.metadata)` rather than the raw
mapping. A mutation replacing `encode` with an equivalent-looking `json.dumps`
inside `require_encodable` reddens the suite, because they are not equivalent.

### Reported, not fixed

`_canonical_bytes` in `engcore/design/memory.py` has **no explicit refusal at
all** — the "new explicit refusal" the task refers to does not exist in this
tree. It is a bare `json.dumps` raising `TypeError`. It therefore cannot yet
disagree with the rule installed here, because it states no rule. Left alone,
with a test asserting the gap: that module is the subject of a frozen test
file, and the records it hashes are built from typed references rather than
from the untyped metadata channel this task is about.

---

## TASK 5 — provenance claiming a source that was never there

**The premise named fields that do not exist.** There is no `dependencies`
field on `ProvenanceRecord` and no `from_execution` anywhere in this tree.
What carries the identical defect is every claim the record makes about a
source. Measured before the fix, **all** of these were accepted:

| Claim | Why it is a claim about a source that was never there |
|---|---|
| `parent_run_id = ""` | a lineage claim naming nothing |
| `parent_run_id = "   "` | the same, wearing whitespace |
| `parent_run_id = <its own run_id>` | a record that is its own source |
| `parent_run_id = "  r  "` vs `run_id = "r"` | the same, evading a naive comparison |
| `models = (("", ""),)` | a participant that took part without saying what |
| `derived(..., parent_run_id=<anything>)` | a false lineage claim through the sanctioned API — which **held the truth** |

All refused now. The self-reference case matters most: a source has to have
existed *before* the thing derived from it, so a record naming itself is not a
weak claim but an impossible one.

**Made to fail on purpose**, through the route that is not a keyword argument:
a stored payload whose `parent_run_id` equals its `run_id` no longer loads.
Deserialization is how such a claim actually arrives — nobody types one.

### The guard that has never been seen to fail

`require_sources_exist(known_run_ids)` answers "did that run happen", and it
**cannot** be automatic: this module collects nothing on its own by an explicit
privacy and determinism position, so a record cannot know which runs happened.

**No shipped path calls it.** Every production lineage claim in this repository
is taken from a record already in hand — `resistor_body.py` and
`multirotor/study.py` both pass the `run_id` of a result they are holding — so
it would never fire there. A test measures that claim from the tree rather than
asserting it, so the day a caller appears the statement stops being true
loudly. Recorded as a limit; it is not presented as enforcement.

---

## TASK 6 — a crossing must state WHEN the value it carries is true

**The premise was partly wrong, and measuring it found the real gap.** The
temperature crossing is *not* undeclared and does *not* cross by
`component_id` match: it has been a `QuantityDependency` naming source problem,
source quantity, target problem, target quantity and dimension since
`ET-VERTICAL`, and the association is structural.

What was missing is the **instant** — and the hazard is stated in the
composition module's own docstring with nothing checking it. A lumped body
publishes two kelvin-valued metrics, `final_temperature` and
`steady_state_temperature`, which **converge to different numbers**. A coupling
selects between them by passing a metric NAME. Both carry kelvin, so the
dimension check passes on either.

### The crossing, before and after

Before, the two configurations were distinguishable only by which string a
caller passed. After:

    { "schema": "quantity_dependency/2",
      "source_problem_id": "thermal-lumped-R1",
      "source_quantity": "final_temperature",
      "target_problem_id": "resistance-tcr-R1",
      "target_quantity": "temperature",
      "unit_exemplar": "kelvin",
      "source_instant": "end_of_interval" }

and the steady-state configuration differs **in the record**:

    body-temperature-sets-property-state:R1:
        end_of_interval   vs   asymptotic_steady_state

while the dimension set is **identical** across both — confirming the dimension
check was never going to be what separated them.

### Fail-closed at three levels

* **required, no default** — a coupling that does not state the instant does
  not construct: `TypeError: ... missing 1 required positional argument:
  'source_instant'`. That is the error the sixth domain gets;
* **`quantity_dependency/1` is refused, not defaulted** — there is no honest
  instant to invent for a record whose author never stated one;
* **`transfer_instant_of` refuses an unknown metric** — the next kelvin-valued
  metric that domain publishes must state its time level or no coupling wires
  it.

### One table, not five opinions

The metric to instant mapping lives in the domain that **publishes** the
metrics, not in each of the four system packs that transport a temperature out
of a body. Five packs holding five mappings could disagree about when
`final_temperature` is true — the same defect one level up. A test measures
that exactly one module holds the table. Each pack **derives** the instant from
the metric it is transporting, so the declaration and the value cannot
disagree; a mutation that hard-codes it reddens the suite.

### Can `repair.py` now invert?

**`repair.py` does not exist in this repository**, on any branch, in any
commit. Neither does the inversion capability the task describes, nor the
refusal text it quotes — `grep` over the whole tree returns nothing. So the
question cannot be answered as asked, and is reported rather than answered.

The substantive half **can** be answered: the crossing is now a declared
transfer with a stated source, quantity and instant, readable from the record
without executing anything, and checkable — `check_against` validates the
endpoints and dimension, and the instant makes the two configurations
distinguishable. Whatever inverts a condition can now read *which* temperature,
from *which* problem, at *which* time level, out of a record rather than out of
an orchestration function's control flow.

### NEEDS — what a general transfer framework would require

Deliberately **not** built. The smallest checkable thing was built instead. A
general one would need, at minimum:

1. **Instants that are values, not levels.** `END_OF_INTERVAL` is meaningless
   across participants with different interval lengths. A general framework
   needs a shared time coordinate and a statement of *which* interval.
2. **Support and transfer semantics for non-scalars.** Every crossing here is a
   scalar. A field crossing needs the source support, the target support and
   the interpolation between them — which is why `data_references` is
   deliberately not consulted by endpoint resolution today.
3. **A conservation statement.** Nothing says a transferred flux is conserved
   across the interface; for scalars nobody has needed it, and for a coupled
   energy balance it is the first thing to check.
4. **Reference frames and datums.** Same-dimension, same-instant quantities can
   still disagree about origin — the existing `shares_origin` / ratio-scale
   check in `engcore.coupling.scales` is the seed of this and covers only
   affine scale.
5. **Bidirectional connectors.** `QuantityDependency` is causal and one-way by
   an explicit decision. Potential/flow pairs are a different, much larger
   contract.
6. **A transfer record in provenance.** The declared crossings are inspectable
   *before* a run but are not written into `ProvenanceRecord` after it — so a
   stored result does not carry what fed it. This is the nearest missing piece
   and the one a drone would want first.

---

## The pre-existing defect this round surfaced and did not fix

`tests/test_api_mcp_v0_transports.py::test_both_transports_agree_that_a_size_fault_is_a_transport_fault`
fails intermittently in the full suite and passes alone. Characterized by
hammering the oversize path 60 times against a real server:

     26  HTTPError 413 body=['error']            <- the declared behaviour
     20  HTTPError 413 BODY UNREADABLE ConnectionAbortedError
     12  ConnectionAbortedError [WinError 10053]
      2  ConnectionResetError   [WinError 10054]

**Roughly 57 % of the time a Windows client does not observe the declared
413.** `crafty_http/server.py` answers an oversize request and closes
**without draining the request body** — a deliberate decision, documented
in-source ("the undrained body would otherwise be parsed as the next request
on a keep-alive connection"), whose observable consequence on Windows
contradicts what the guard asserts.

Not fixed: it is outside all six tasks, `src/crafty_http/` is frozen by other
milestones' guards, and it produces no wrong scientific number — both outcomes
are transport faults. Reported because every SCIENTIFIC failure seen in this
round was this one test.

---

## Mutation guards

`tests/mutation_guards.py` carries **24** deliberate defects, one or more per
task. `tests/test_mutation_guards.py` copies the tree, applies each in a
scratch worktree, and runs only the tests that mutation claims to break in a
fresh interpreter, requiring them to fail. All 24 redden the suite.

One of them found a defect in this round's own test on the day it was written:
`registry-check-not-at-the-run-boundary` came back green because the influence
test spawned its child with a bare `sys.executable`, so the child resolved
`engcore` from the editable install rather than from the mutated tree. Fixed by
pinning `PYTHONPATH`.
