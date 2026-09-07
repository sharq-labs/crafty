"""CORE-MECHANISMS — six mechanisms every domain inherits.

A domain defect belongs to one domain. A core defect is silently in all five
domains and in the sixth nobody has written yet. Everything measured here is
core: the unit registry, the applicability field, the routes to a
``ValidationCheck``, construction-time serializability, dependency existence,
and declared cross-domain transfer.

Each guard in this module was **observed failing before it was written to
pass**. A check that cannot fail is indistinguishable from one that passes,
and one that cannot pass measures nothing; the mutations in
``tests/mutation_guards.py`` are how that stays true after today.
"""

from __future__ import annotations

import copy
import pathlib
import subprocess
import sys

import pytest

from core_mechanisms_scope import BASE, CORE_FILES
from engcore.scientific.errors import UnitRegistryFrozen
from engcore.scientific.units.quantity import (
    Quantity,
    _mutator_names,
    _NOT_MUTATORS,
    registry,
    require_pristine_registry,
    units_fingerprint,
)

# =====================================================================
# THE DECLARED SCOPE
#
# Eleven historical guards assert the universal core is byte-untouched. This
# milestone changes the core on purpose, so each of them subtracts one shared
# list. That list is a single point of weakening, so it is a claim rather than
# a licence: it must match the tree exactly, in both directions.
# =====================================================================


def test_the_declared_core_scope_matches_the_tree_exactly():
    """No undeclared core edit, and no dead entry in the exception list.

    The first direction is what the eleven guards were protecting. The second
    is what stops the list becoming a place to park a name that quietly
    exempts a file nothing actually changed.
    """
    changed = {
        line.strip()
        for line in subprocess.run(
            ["git", "diff", "--name-only", BASE, "HEAD", "--",
             "src/engcore/scientific/"],
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    }
    # ...and the working tree, so an uncommitted core edit is just as loud.
    changed |= {
        line[3:].strip().strip('"')
        for line in subprocess.run(
            ["git", "status", "--porcelain", "--", "src/engcore/scientific/"],
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        if line.strip()
    }
    assert changed - CORE_FILES == set(), sorted(changed - CORE_FILES)
    assert CORE_FILES - changed == set(), sorted(CORE_FILES - changed)


# =====================================================================
# TASK 1 — the shared UnitRegistry
#
# The decision: an ENFORCED REFUSAL to allow registry mutation, not per-run
# isolation. Isolation is only needed when state can change; if it cannot,
# a shared registry is observationally identical to a per-run one, because
# unit algebra over a fixed definition set is a pure function of
# (magnitude, unit string). A fresh registry was measured at 101.8 ms and
# buys nothing sealing does not already give.
#
# The cost, stated rather than discovered later: a domain that needs a unit
# pint does not define cannot add one at runtime.
# =====================================================================


def test_the_registry_refuses_to_define_a_new_unit():
    """The route that changes what a later run can even parse."""
    with pytest.raises(UnitRegistryFrozen) as excinfo:
        registry().define("widget = 5 * meter")
    assert "sealed" in str(excinfo.value)


def test_the_registry_refuses_to_redefine_an_existing_unit():
    """The dangerous route: it changes an answer without changing a count.

    Measured on pint 0.25.3 against an unsealed registry — redefining
    ``millivolt`` turns ``1 V -> 1000 mV`` into ``1 V -> 1000000 mV``, with
    ``len(_units)`` unchanged. That is a wrong number someone builds on.
    """
    before = Quantity(1.0, "volt").to("millivolt").magnitude
    with pytest.raises(UnitRegistryFrozen):
        registry().define("millivolt = 1e-6 * volt = mV")
    assert Quantity(1.0, "volt").to("millivolt").magnitude == before == 1000.0


def test_the_seal_survives_the_reference_pint_hands_back():
    """A wrapper would not be enough, so the seal is not a wrapper.

    ``registry().Quantity(...)._REGISTRY`` **is** the real registry object.
    Every quantity this module has ever returned carried one, so a proxy
    around ``registry()`` would be bypassed by any code holding a quantity.
    """
    leaked = registry().Quantity(1.0, "volt")._REGISTRY
    assert leaked is registry()
    with pytest.raises(UnitRegistryFrozen):
        leaked.define("widget = 5 * meter")


def test_every_mutator_shaped_member_is_sealed():
    """Not a hand-maintained list of method names.

    The seal is applied by matching name shapes against ``dir(registry)``, so
    a mutator introduced by a future pint release is sealed the moment it
    appears rather than the moment somebody remembers it. This asserts the
    sweep actually found members and actually replaced them.
    """
    names = _mutator_names(registry())
    assert len(names) >= 10, names
    assert "define" in names
    sealed = [n for n in names if n not in _NOT_MUTATORS]
    for name in sealed:
        with pytest.raises(UnitRegistryFrozen):
            getattr(registry(), name)()


def test_offset_and_log_unit_arithmetic_still_works():
    """The seal must not break reads that merely LOOK like writes.

    ``_add_ref_of_log_or_offset_unit`` matches the ``_add_`` shape and writes
    nothing — it returns a ``UnitsContainer``. Sealing it broke every degC
    conversion in the suite, which is how it was found. An over-broad seal
    fails loudly; a missed mutator would not. This keeps the loud failure
    available rather than relying on someone re-running the whole suite.
    """
    assert Quantity(0.0, "degC").to("kelvin").magnitude == pytest.approx(273.15)
    assert Quantity(100.0, "degC").to("degF").magnitude == pytest.approx(212.0)
    require_pristine_registry(context="after offset-unit arithmetic")


def test_lazy_prefix_expansion_is_not_mistaken_for_a_mutation():
    """pint materializes ``millivolt`` into ``_units`` on first use.

    That is an expansion of the sealed prefix ``milli`` and the sealed unit
    ``volt``, not a new definition. If the guard could not tell the two
    apart it would fire on ordinary arithmetic and be switched off.
    """
    for expression in (
        "millivolt", "mV", "kilometer", "MPa", "kohm", "GHz", "uA",
        "picofarad", "mol/m**3", "W/(m*K)", "kg/m**3", "centipoise",
    ):
        registry().Unit(expression)
    require_pristine_registry(context="after lazy expansion")


def test_the_content_check_catches_what_no_seal_can_block():
    """A direct write into ``_units`` calls no method, so no seal stops it.

    This is the difference between a guard that knows the ways in and one
    that knows the answer. Both are here on purpose: the seal refuses at the
    moment of mutation, and this refuses at the next run boundary whatever
    route was used.
    """
    units = registry()._units
    units["widget"] = units["meter"]
    try:
        with pytest.raises(UnitRegistryFrozen) as excinfo:
            require_pristine_registry(context="run 2")
        assert "widget" in str(excinfo.value)
    finally:
        units.pop("widget", None)
    require_pristine_registry()


def test_a_changed_definition_is_caught_and_an_equal_rebinding_is_not():
    """Equality, not identity — and the reason is pint's own behaviour.

    Parsing ``kg/m**3`` makes pint REBIND ``_units['kilogram']`` to a new
    but value-equal ``UnitDefinition``. An identity comparison fires on that,
    i.e. on correct arithmetic, and a guard that fires on correct work gets
    switched off. A real redefinition changes the converter
    (``scale=0.001`` -> ``scale=1e-06``) and is not equal, so equality
    separates the two exactly.
    """
    units = registry()._units
    original = units["volt"]

    # An equal rebinding — what pint itself does — must NOT be reported.
    units["volt"] = copy.copy(original)
    try:
        require_pristine_registry()
    finally:
        units["volt"] = original

    # A changed definition must be.
    import dataclasses

    units["volt"] = dataclasses.replace(original, defined_symbol="VV")
    try:
        with pytest.raises(UnitRegistryFrozen) as excinfo:
            require_pristine_registry()
        assert "volt" in str(excinfo.value)
    finally:
        units["volt"] = original
    require_pristine_registry()


def test_pint_definitions_are_still_frozen():
    """The premise the value comparison rests on, asserted rather than
    assumed.

    The sealed baseline holds the definition OBJECTS. That is only sound
    while they cannot change in place — an in-place edit would move both
    sides of the comparison at once and be invisible. The day a pint release
    makes these mutable, this fails instead of the guard quietly weakening.
    """
    import dataclasses

    reg = registry()
    samples = (
        reg._units["meter"],
        next(iter(reg._prefixes.values())),
        next(iter(reg._dimensions.values())),
    )
    for definition in samples:
        assert dataclasses.is_dataclass(definition), definition
        assert definition.__dataclass_params__.frozen, definition


def test_the_fingerprint_is_stable_across_ordinary_work():
    """Safe to record in provenance: it does not move as a process runs."""
    first = units_fingerprint()
    for i in range(100):
        Quantity(float(i), "volt").to("millivolt")
    assert units_fingerprint() == first


# ---------------------------------------------------------------------
# TASK 1, THE FAIL-CLOSED PROOF
#
# The mechanism is not opt-in. It is checked inside ProvenanceRecord, which
# is mandatory on every ScientificResult, so a domain cannot decline it by
# not calling anything — including a domain that does not know it exists.
# ---------------------------------------------------------------------

_INFLUENCE = """
import json
from engcore.scientific.units.quantity import registry, Quantity
from engcore.scientific.results.provenance import ProvenanceRecord

# RUN 1 — a domain vandalises the registry by the one route no seal blocks.
before = Quantity(1.0, "volt").to("millivolt").magnitude
units = registry()._units
units["widget"] = units["meter"]

# RUN 2 — a DIFFERENT domain, which knows nothing about run 1, builds the
# provenance every scientific result is required to carry.
try:
    ProvenanceRecord(run_id="run-2")
    print(json.dumps({"refused": False}))
except Exception as exc:
    print(json.dumps({"refused": True, "type": type(exc).__name__,
                      "message": str(exc)}))
"""


def test_two_runs_in_one_process_cannot_influence_each_other():
    """THE MEASUREMENT. Constructed deliberately, in a real second process.

    Run 1 changes the unit algebra. Run 2 is a different domain that calls
    nothing new and opts into nothing. It is refused before it can report a
    number, because the check lives where every run already has to go.
    """
    # PYTHONPATH is pinned to the `src` THIS process imported engcore from,
    # not left to the interpreter's default. Without it the child resolves
    # engcore from whatever is installed, so the child would exercise a
    # different tree than the parent — which is exactly how a mutation test
    # comes back green against unmutated source.
    import engcore
    import json
    import os

    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONPATH"] = str(
        pathlib.Path(engcore.__file__).resolve().parents[1]
    )
    completed = subprocess.run(
        [sys.executable, "-c", _INFLUENCE],
        capture_output=True, text=True, check=True, env=environment,
    )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["refused"] is True, payload
    assert payload["type"] == "UnitRegistryFrozen", payload
    assert "widget" in payload["message"], payload
