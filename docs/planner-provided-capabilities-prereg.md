# PLANNER-PROVIDED-CAPABILITIES — Preregistration

**Milestone:** minimum universal model-discovery surface (Phase 2B) — can a
deterministic caller answer "which scientific models provide capability X?"
**Kind:** small additive contract change on an existing `DESIGN-FROZEN`
record (`ScientificModelDefinition`). Not a Knowledge Graph, not a Planner,
not a ranking engine.
**Date:** 2026-09-03
**Branch:** `planner-provided-capabilities`
**Base:** `cloud/crafty-foundation` @ `c687544`
**Preregistered before implementation.** Everything below was written before
any source file in `src/` was added or edited.

> **This file is immutable.** It records what was committed to before results
> were observed. Executed results and the final classification go in
> `docs/planner-provided-capabilities-evidence.md`.

---

## 1. The single question

> Can a caller deterministically discover "which registered scientific
> models provide capability X" from the existing contracts, without name
> parsing, module inspection, metadata dicts, external side tables, or
> hard-coded model IDs — and if not, what is the smallest additive change
> that makes it possible?

Nothing else is decided here. This milestone does not build a Knowledge
Graph, a Planner, a capability ranking/selection engine, an ontology, or a
model recommender. It does not touch `ModelRealizationDefinition` (which
already has `provided_capabilities`), and it does not touch any Fluid domain
code (there is none on this branch).

---

## 2. Primary hypothesis and null hypothesis

**HYPOTHESIS (H1).** A minimal typed `provided_capabilities` declaration on
`ScientificModelDefinition`, plus a small deterministic query method on
`ModelRegistry`, is sufficient to enable deterministic capability → model
discovery, without requiring a Knowledge Graph or Planner framework.

**NULL / FALSIFYING HYPOTHESIS (H0).** The existing contracts already permit
this discovery (H1 is unneeded — no field should be added), OR a single
field is insufficient and correct discovery genuinely requires graph/ranking
machinery (H1 is too weak — more than "a field + a query method" is needed).

H0 is allowed to win either way. §3 (the zero-contract attempt) is the gate
that lets the "already sufficient" branch of H0 win before any field is
added. §5's required test cases (exactly one match / multiple matches / zero
matches, with multiple matches returned unranked) are the gate that would
show a bare field insufficient, if it turns out to be.

---

## 3. Planned zero-contract attempt (P1)

Before adding any field, the current contract will be exercised directly:
construct two or more `ScientificModelDefinition` records with distinct
scientific purposes, and attempt to answer "which of these provides
capability X" using only:

- `ScientificModelDefinition.required_capabilities` (states what a model
  *needs*, not what it *offers* — the registry already filters on this, in
  the wrong direction for discovery),
- `ScientificModelDefinition.provided_metrics` / `outputs` (states *metric
  names* with unit exemplars, not capability identifiers — a planner would
  have to invent a metric-name-to-capability mapping out of band),
- `ScientificModelDefinition.metadata` (an open, untyped `Mapping[str, Any]`
  — anything read from it is an out-of-band side channel the core does not
  validate or agree on the shape of, which is exactly what this milestone
  is scoped to avoid introducing),
- `model_id` / `domain` string matching (name parsing, explicitly excluded
  by scope).

The expected outcome, to be confirmed by an actual attempted probe (not
assumed): none of the above answers "what does this model provide" without
one of the disallowed mechanisms. This will be written up as recorded
failure reasons in the evidence document, not just asserted.

---

## 4. Planned minimum change (P2)

If §3 confirms the gap, the smallest additive change consistent with
existing style is a new field:

```python
provided_capabilities: frozenset[ScientificCapability] = frozenset()
```

on `ScientificModelDefinition`, reusing
`engcore.scientific.capabilities.ScientificCapability` — the exact type
`ModelRealizationDefinition.provided_capabilities` already uses — rather
than inventing a second capability type or reusing the looser bare-`str`
convention `required_capabilities` happens to use on this same class. The
type is not assumed before inspection; `definition.py` and
`realizations/definition.py` are read first, and the field mirrors
whichever shape is actually load-bearing there.

Candidate default: empty frozenset (nothing declared → nothing claimed),
mirroring `required_capabilities`'s existing default on this same class.
This is provisional pending the backward-compatibility check in §6 — the
alternative (require explicit declaration, i.e. no default / mandatory
field) is rejected only if proven to break existing loadable models; that
proof, not preference, decides it.

Explicitly out of scope for this change: no ranking, no "best model for X",
no inference of capabilities from names or metrics, no registry-wide index
structure beyond a linear scan (the registry is in-memory and small; a
linear scan is the deterministic, auditable baseline until scale evidence
says otherwise).

If a query method is needed on `ModelRegistry`, it returns **all** matches
as a set/tuple, never a single winner — selection is explicitly a later
planner's job, not this milestone's.

---

## 5. Required test cases (P3)

The discovery proof must include, with real (not asserted) test results:

1. **Exactly one match** — one registered model declares capability X, one
   other does not; the query returns exactly that one model.
2. **Multiple matches** — two or more registered models declare capability
   X; the query returns all of them, and the result must not silently rank
   or pick a winner.
3. **Zero matches** — capability X is not declared by any registered model;
   the query returns an empty result, not an error and not a fabricated
   match.

---

## 6. Backward compatibility (P4)

Existing models that do not declare `provided_capabilities` must remain
loadable — both direct construction and `from_dict`/`to_dict` round-trip —
and must simply report no provided capabilities (or whatever the proven
correct default from §4 is), never an inferred one. This will be proven
with an explicit test loading a pre-existing-shaped payload (no
`provided_capabilities` key) through `from_dict`.

---

## 7. What would falsify H1

- The zero-contract attempt in §3 succeeds using only existing contracts —
  H1 is unnecessary.
- A bare field cannot make §5's three cases pass without also requiring
  ranking logic, an index/graph structure, or capability inference from
  names — H1 as stated is too weak and the real minimum is larger.
- Adding the field breaks backward compatibility (existing models become
  unloadable, or serialization stops round-tripping) — H1's claim of
  "minimal" and "additive" fails.

---

## 8. Evidence target

At most an additive, backward-compatible field plus one discovery query
method, proven against the three required cases and backward compatibility,
with targeted + FAST tests passing. No FULL suite run from this worktree
(reserved for integration phase). This branch is not to be merged
automatically on completion of this milestone — that is an integration-phase
decision, not this micro-step's.
