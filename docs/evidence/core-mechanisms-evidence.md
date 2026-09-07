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
