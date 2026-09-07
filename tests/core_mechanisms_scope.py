"""The universal-core files CORE-MECHANISMS is authorized to change.

Eleven historical guards assert that ``src/engcore/scientific/`` is
byte-untouched since their own milestone's base commit. Every one of them is
correct about its own milestone and fails for every LATER milestone that
changes the core, however correct that later work is. CORE-MECHANISMS is the
first milestone whose entire subject IS the core — six mechanisms that are
silently in all five domains and in the sixth nobody has written — so all
eleven fire at once.

The repository's established repair is to name the changed files individually
in each guard, so a stray edit stays loud. Doing that eleven times produces
eleven hand-maintained copies of one list, and a guard from a hand-maintained
list guards only what someone remembered. So the list lives here once, and
each guard subtracts it.

That makes this file a single point of weakening, which is why it is not just
a list: ``test_core_mechanisms.py`` asserts that the set of universal-core
files changed since :data:`BASE` is **exactly** :data:`CORE_FILES`. An entry
added here without a real change fails. A core file changed without being
declared here fails. The exception list is a claim, not a licence.
"""

from __future__ import annotations

#: The commit CORE-MECHANISMS starts from — the baseline repair that made the
#: suite measurable on this platform, and the last commit before any mechanism
#: was touched.
BASE = "642ae5a"

#: Every file under ``src/engcore/scientific/`` this milestone changes, named
#: individually and with the task that changes it.
CORE_FILES = frozenset({
    # TASK 1 — the shared UnitRegistry is sealed against mutation.
    "src/engcore/scientific/units/quantity.py",
    "src/engcore/scientific/units/__init__.py",
    "src/engcore/scientific/errors.py",
    "src/engcore/scientific/__init__.py",
    # TASK 1 — the per-run check lives where every run already passes.
    "src/engcore/scientific/results/provenance.py",
    # TASK 2 — applicability becomes a field of the result, with three states
    # that cannot be confused, instead of a note four domains never wrote.
    "src/engcore/scientific/results/applicability.py",
    "src/engcore/scientific/results/result.py",
    "src/engcore/scientific/results/__init__.py",
    # TASK 3 — the evidentiary rule, and the three routes that bypassed it.
    "src/engcore/scientific/results/validation.py",
    # TASK 4 — one acceptance rule, run at construction instead of crashing
    # inside json.dumps.
    "src/engcore/scientific/serialization.py",
})

#: Files OUTSIDE the universal core that this milestone changes, and the
#: historical guards that freeze them. Kept separate from :data:`CORE_FILES`
#: because those guards make a different claim — "this pre-existing domain was
#: not modified" rather than "the core was not modified" — and one list
#: excusing both would be a licence rather than a claim.
DOMAIN_FILES = frozenset({
    # TASK 2 — the four editable paths of five. `domains/thermal/` is frozen
    # by the task's own rules and is reported, not worked around.
    "src/engcore/domains/kinetics/cstr/solver.py",
    "src/engcore/domains/fluids/transport2d/solver.py",
    "src/engcore/domains/electrical/dc/solver.py",
    "src/engcore/application/contract.py",
})
