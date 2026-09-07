"""Mutation guards — proof that the guards in this repository can fail.

A check that cannot fail is indistinguishable from one that passes. Every
entry below names a **deliberate defect** in shipped source and the test that
must go red when it is applied. ``test_mutation_guards.py`` applies each one
to a scratch copy of the tree, runs only the named tests, and requires them to
fail — so a guard that has been quietly hollowed out is reported as a guard,
not discovered as a wrong number.

This file is not a list of things someone remembered to check. It is the
executable form of standing rule 1, and rule 6 of CORE-MECHANISMS requires an
entry here in the *same commit* as any new guard.

Each ``Mutation`` is a literal source substitution:

``path``     file under the repository root
``old``      an exact, unique substring of that file
``new``      what replaces it — the defect
``breaks``   node ids that MUST fail once the substitution is applied
``why``      what the mutation is pretending to be
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    old: str
    new: str
    breaks: tuple[str, ...]
    why: str


MUTATIONS: tuple[Mutation, ...] = (
    # ---- TASK 1, the sealed unit registry ---------------------------
    Mutation(
        name="unseal-define",
        path="src/engcore/scientific/units/quantity.py",
        old='    object.__setattr__(reg, "define", _refuse("define"))\n',
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_registry_refuses_to_define_a_new_unit",
            "tests/test_core_mechanisms.py::test_the_registry_refuses_to_redefine_an_existing_unit",
            "tests/test_core_mechanisms.py::test_the_seal_survives_the_reference_pint_hands_back",
        ),
        why="the single most important route left open while the sweep still runs",
    ),
    Mutation(
        name="seal-sweep-finds-nothing",
        path="src/engcore/scientific/units/quantity.py",
        old="    for name in _mutator_names(reg):\n",
        new="    for name in ():\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_every_mutator_shaped_member_is_sealed",
        ),
        why="the shape sweep silently matching nothing, leaving every mutator but define open",
    ),
    Mutation(
        name="content-check-never-fires",
        path="src/engcore/scientific/units/quantity.py",
        old="    problems = _unexplained_changes(registry())\n",
        new="    problems = ()\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_content_check_catches_what_no_seal_can_block",
            "tests/test_core_mechanisms.py::test_a_changed_definition_is_caught_and_an_equal_rebinding_is_not",
            "tests/test_core_mechanisms.py::test_two_runs_in_one_process_cannot_influence_each_other",
        ),
        why="the layer that catches the route no seal can block, made inert",
    ),
    Mutation(
        name="registry-check-not-at-the-run-boundary",
        path="src/engcore/scientific/results/provenance.py",
        old='        require_pristine_registry(context=f"provenance {run_id!r}")\n',
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_two_runs_in_one_process_cannot_influence_each_other",
        ),
        why="the check made opt-in again by removing it from the one place every run passes through",
    ),
)


def mutations_for(task: str) -> tuple[Mutation, ...]:
    """Every mutation whose name starts with ``task``."""
    return tuple(m for m in MUTATIONS if m.name.startswith(task))
