# PLANNER-PROVIDED-CAPABILITIES — Evidence

Preregistered in `docs/planner-provided-capabilities-prereg.md`, which was
committed alone, before any source file was touched. This document records
what actually happened.

**This branch (`planner-provided-capabilities`) is not to be merged
automatically.** Whether and how to integrate it is an integration-phase
decision, not this micro-step's to make.

---

## 1. P1 — zero-contract attempt

An actual probe was run (not assumed) against the pre-change contracts,
constructing two `ScientificModelDefinition` records and trying to answer
"which of these provides capability X" using only what already existed.
Script: `/tmp/.../scratchpad/p1_probe.py`; results:

| Attempted mechanism | Outcome |
|---|---|
| `required_capabilities` / `ModelRegistry.list(capability=...)` | Answers "needs X", the **opposite** question — a model can require a capability it does not provide, and vice versa. Confirmed: both fixture models had empty `required_capabilities` yet the question was about what they *offer*. |
| `provided_metrics` / `outputs` | States metric names with unit exemplars (e.g. `"temperature"`), not capability identifiers. No method exists to map a metric name to a `ScientificCapability`; `AttributeError` when such a method was probed for. Inventing that mapping would be exactly the out-of-band inference this milestone excludes. |
| `metadata` (`Mapping[str, Any]`) | Confirmed empty and untyped by contract — nothing populates or validates a capability convention there. Reading it would be an unenforced side-channel. |
| `model_id` / `domain` string matching | `domain="thermal"` on a model named `thermal.diffusion` — matching this against a capability namespace is name parsing, explicitly excluded, and also unsound in general (nothing enforces domain equals capability namespace). |

**Conclusion: the zero-contract attempt fails**, for the reasons above and
not by assumption — H0's "already sufficient" branch does not win.

---

## 2. P2 — the field added

```python
provided_capabilities: frozenset[ScientificCapability] = frozenset()
```

added to `ScientificModelDefinition`
(`src/engcore/scientific/models/definition.py`).

- **Type**: `ScientificCapability` (from `engcore.scientific.capabilities`),
  not a new type and not the bare-`str` convention its sibling
  `required_capabilities` happens to use on this same class. This was
  decided only after reading both `ModelRealizationDefinition` (which
  already types its own `provided_capabilities` this way) and
  `ScientificCapability` itself — the exact same identity type is reused,
  so `ScientificModelDefinition.provided_capabilities` and
  `ModelRealizationDefinition.provided_capabilities` are drawn from one
  capability space, not two.
- **Default**: empty `frozenset()`. Justified in §4 below by the
  backward-compatibility proof, not by preference: a model that declares
  nothing is simply undiscoverable by capability (proven, not an error, and
  not an inferred value).
- **Normalization**: run through the existing `scientific_capabilities()`
  helper in `__post_init__`, so a string identifier (`"thermal:heat_conduction"`)
  or a `ScientificCapability` instance are both accepted and stored
  normalized, exactly as `ModelRealizationDefinition` already does.
- **New method**: `ScientificModelDefinition.provides(capability) -> bool`,
  mirroring `ModelRealizationDefinition.provides`.
- **New registry method**:
  `ModelRegistry.providers_of(capability) -> tuple[ScientificModelDefinition, ...]`
  in `src/engcore/scientific/models/registry.py` — a linear scan over the
  registry returning **all** matches in deterministic `(model_id, version)`
  order. It does not rank, does not pick a winner, and does not build an
  index or graph structure; that is out of scope by design (see prereg §4).
- **Serialization**: `to_dict()` emits `"provided_capabilities"` as sorted
  canonical identifier strings (via `capability_identifiers()`); `from_dict()`
  reads it with a default of `()` when absent.

No Knowledge Graph, Planner, ranking engine, ontology, or model recommender
was introduced. No Fluid code was touched (none exists on this branch).

---

## 3. P3 — discovery proof (executed)

`tests/test_planner_provided_capabilities.py`, all passing:

| Case | Test | Result |
|---|---|---|
| **Exactly one match** | `test_discovery_exactly_one_match` | A `thermal:heat_conduction`-providing model and an unrelated elasticity model are registered; `providers_of(CONDUCTION)` returns exactly `(conduction_model,)`. |
| **Multiple matches** | `test_discovery_multiple_matches_are_all_returned_unranked` | Two distinct models (`thermal.diffusion.fd`, `thermal.diffusion.fem`) both declare the same capability; `providers_of` returns **both**, in deterministic `(model_id, version)` order, and does not silently choose a winner. A third, unrelated model is confirmed absent from the result. |
| **Zero matches** | `test_discovery_zero_matches_is_an_empty_result_not_an_error` | A capability no registered model declares returns `()` — not an exception, not a fabricated match. |

Additional discovery tests executed: string-identifier input is accepted
(`test_discovery_accepts_a_capability_identifier_string_too`);
`providers_of` is confirmed to answer the opposite question from
`list(capability=...)` (`test_discovery_answers_provides_not_requires`);
`provides()` mirrors the realization-layer method
(`test_model_provides_method_mirrors_realization_provides`); an invalid,
non-namespaced identifier is rejected rather than silently coerced
(`test_invalid_capability_identifier_is_rejected_not_coerced`).

---

## 4. P4 — backward compatibility (executed)

- `test_legacy_payload_without_the_field_still_loads` — a payload shaped
  exactly like a pre-this-milestone `ScientificModelDefinition` record (no
  `provided_capabilities` key) loads via `from_dict` without error.
- `test_legacy_payload_reports_no_provided_capabilities_not_an_inferred_one`
  — that record reports `provided_capabilities == frozenset()`, and
  `.provides(CONDUCTION) is False` even though the record's own `domain`
  and `model_id` both say "thermal" — proving nothing is inferred from
  names.
- `test_legacy_model_is_simply_undiscoverable_by_capability_not_an_error` —
  registering that model and querying `providers_of` for any capability
  returns `()`, not an error.
- `test_model_without_the_field_constructs_directly_too` — direct
  construction without the keyword also defaults correctly.
- `test_serialization_round_trips_with_the_new_field` /
  `..._with_an_empty_declared_set` / `test_json_round_trip_is_stable` —
  `to_dict()` → `from_dict()` and `to_json()` round-trip both a populated
  and an empty `provided_capabilities` set correctly, including through
  the plain-JSON layer.

This confirms the empty-frozenset default is correct (not merely
convenient): it is what makes every pre-existing model payload continue to
load with unchanged, non-inferred behavior.

MODEL0-R's own existing legacy-record test
(`tests/test_model0r_realization_foundation.py::test_legacy_model_record_re_serializes_byte_identically`)
was updated in place to expect the one additive key
(`"provided_capabilities": []`) rather than asserting the payload is
untouched byte-for-byte — its underlying claim (MODEL0-R itself perturbed
nothing) still holds; this is a later, separate, documented milestone
adding one key. `test_model_definition_gained_no_realization_fields` was
likewise updated to include the new field while continuing to assert that
no *realization*-layer field (`realization`, `formulation`, `fidelity`,
`realizations`, `required_solver_capabilities`) leaked into the model
layer.

Four other pre-existing static architecture-fitness guards
(`test_cross_domain_coverage.py`, `test_exec_spec_structured_input.py`,
`test_executable_scientific_spec.py`, `test_hostile_core_domain_stress.py`)
assert `src/engcore/scientific/` (or all of `src/`) is byte-unchanged
relative to their own milestone's `HEAD`. Each predates this milestone and
did not anticipate it, exactly as the earlier
`ngspice-cross-platform-portability` milestone found for its own two files.
Each guard now excludes exactly
`src/engcore/scientific/models/definition.py` and
`src/engcore/scientific/models/registry.py` from its comparison — the two
files this milestone is documented and authorized to touch — and still
fails if any other file under its guarded path changes.

---

## 5. Targeted + FAST test results

```
pytest tests/test_planner_provided_capabilities.py \
       tests/test_scientific_core.py \
       tests/test_model0r_realization_foundation.py \
       tests/test_model0r_differential.py \
       tests/test_executable_scientific_spec.py \
       tests/test_min_foundation_electrothermal.py \
       tests/test_heterogeneous_ngspice.py \
       tests/test_hostile_core_domain_stress.py \
       tests/domains/electrical/test_dc_integration.py -q
```
→ **488 passed**

```
pytest tests/ -m "not expensive" -q
```
→ **1479 passed, 565 deselected**

No FULL suite was run from this worktree — reserved for the integration
phase, per scope.

---

## 6. Evidence level and classification

- H1 (a minimal typed `provided_capabilities` field + one deterministic,
  unranked query method is sufficient for capability → model discovery)
  **survives**: the zero-contract attempt failed for the documented
  reasons, the field plus `providers_of` answers all three required
  discovery cases correctly, and backward compatibility holds with a
  justified (not merely assumed) empty default.
- H0 did not win on either branch: the existing contract was not already
  sufficient (§1), and the minimal field was not shown insufficient — no
  test required ranking, an index/graph, or name-based inference to pass.
- Scope discipline held: no Knowledge Graph, Planner, ranking engine,
  ontology, or model recommender exists on this branch. No Fluid production
  code was touched.
- Evidence level: **additive, backward-compatible, test-proven minimal
  discovery surface** — the smallest change consistent with existing style
  that makes "which models provide capability X" answerable
  deterministically. Selection/ranking among multiple providers remains
  explicitly unimplemented and out of scope, as prereg §4 required.
