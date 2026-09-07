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
    # ---- TASK 2, applicability as a field of the result -------------
    Mutation(
        name="applicability-collapses-two-states",
        path="src/engcore/scientific/results/applicability.py",
        old="        if state is ApplicabilityState.ASSESSED:\n",
        new="        if state is not ApplicabilityState.UNDECLARED:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_states_cannot_be_constructed_inconsistently",
        ),
        why="'not assessed' allowed to carry assessments — the exact confusion the record exists to prevent",
    ),
    Mutation(
        name="applicability-not-serialized",
        path="src/engcore/scientific/results/applicability.py",
        old='            "state": self.state.value,\n',
        new='            "state": ApplicabilityState.ASSESSED.value,\n',
        breaks=(
            "tests/test_core_mechanisms.py::test_the_three_states_are_impossible_to_confuse",
            "tests/test_core_mechanisms.py::test_every_result_says_something_about_applicability",
            "tests/test_core_mechanisms.py::test_the_frozen_thermal_path_is_visibly_undeclared",
        ),
        why="a reader holding only the payload can no longer tell the three states apart",
    ),
    Mutation(
        name="result-accepts-a-bare-mapping",
        path="src/engcore/scientific/results/result.py",
        old="        if not isinstance(self.applicability, ApplicabilityReport):\n",
        new="        if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_a_bare_mapping_is_refused_as_the_applicability_field",
        ),
        why="the untyped `{}` four domains would have reached for, admitted again",
    ),
    Mutation(
        name="projection-accepts-silence",
        path="src/engcore/application/contract.py",
        old='    report.require_declared(context="projecting an execution result")\n',
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_projection_refuses_an_undeclared_applicability",
        ),
        why="the one place TASK 2 is ENFORCED rather than declared, made inert",
    ),
    Mutation(
        name="cstr-discards-its-assessment-again",
        path="src/engcore/domains/kinetics/cstr/solver.py",
        old="        applicability=ApplicabilityReport.assessed(\n"
            "            {CSTR_MODEL.model_id: assess_run_applicability(run)}\n"
            "        ),\n",
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_every_result_producer_is_accounted_for",
        ),
        why="the original defect restored: the verdict computed, rendered into a note, and dropped",
    ),
    # ---- TASK 3, every route into a ValidationCheck -----------------
    Mutation(
        name="unbacked-level-claim-permitted",
        path="src/engcore/scientific/results/validation.py",
        old="            and self.establishes.value in _LEVELS_REQUIRING_BACKING\n",
        new="            and False\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_a_passing_check_cannot_claim_a_level_it_cannot_back",
        ),
        why="the route the task names, reopened: an evidentiary claim with nothing attached",
    ),
    Mutation(
        name="copy-launders-a-check",
        path="src/engcore/scientific/results/validation.py",
        old="    def __reduce__(self):\n",
        new="    def _disabled__reduce__(self):\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_enumeration_of_routes_into_a_validation_check_is_complete",
            "tests/test_core_mechanisms.py::test_copy_cannot_launder_a_check_past_the_rule",
        ),
        why="copy/deepcopy/pickle rebuilding a frozen record without running one rule",
    ),
    Mutation(
        name="self-contradicting-pass-permitted",
        path="src/engcore/scientific/results/validation.py",
        old="            and not (self.residual <= self.tolerance)\n",
        new="            and False\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_a_passing_check_cannot_contradict_its_own_tolerance",
        ),
        why="a PASS whose residual exceeds its own bound",
    ),
    Mutation(
        name="report-accepts-a-non-check",
        path="src/engcore/scientific/results/validation.py",
        old="            if not isinstance(check, ValidationCheck):\n",
        new="            if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_report_refuses_a_non_check_for_a_stated_reason",
        ),
        why="route 7 back to refusing only incidentally, via AttributeError",
    ),
    # ---- TASK 4, one acceptance rule ---------------------------------
    Mutation(
        name="result-metadata-unchecked-again",
        path="src/engcore/scientific/results/result.py",
        old='            require_encodable(value, context=f"result metadata key {key!r}")\n',
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_an_unrecordable_value_is_refused_at_construction",
            "tests/test_core_mechanisms.py::test_the_two_refusals_cannot_disagree",
        ),
        why="a result that exists in memory and cannot be recorded, admitted again",
    ),
    Mutation(
        name="provenance-metadata-unchecked-again",
        path="src/engcore/scientific/results/provenance.py",
        old='            require_encodable(value, context=f"provenance metadata key {key!r}")\n',
        new="",
        breaks=(
            "tests/test_core_mechanisms.py::test_provenance_refuses_it_too",
        ),
        why="provenance that cannot be written down is provenance that does not exist",
    ),
    Mutation(
        name="two-rules-instead-of-one",
        path="src/engcore/scientific/serialization.py",
        old="    try:\n        encode(value)\n    except ScientificCoreError as exc:\n",
        new="    try:\n        json.dumps(value)\n    except (TypeError, ValueError) as exc:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_two_refusals_cannot_disagree",
        ),
        why="a SECOND acceptance rule that looks equivalent and is not — json.dumps refuses the Enum that encode accepts",
    ),
    # ---- TASK 5, claims about sources --------------------------------
    Mutation(
        name="record-may-be-its-own-source",
        path="src/engcore/scientific/results/provenance.py",
        old="            if parent == run_id:\n",
        new="            if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_a_record_cannot_claim_a_source_it_can_see_is_not_there",
            "tests/test_core_mechanisms.py::test_the_refusal_is_reachable_through_deserialization",
        ),
        why="a provenance record deriving from itself — a source that cannot have existed first",
    ),
    Mutation(
        name="blank-lineage-claim-permitted",
        path="src/engcore/scientific/results/provenance.py",
        old="            if not parent:\n",
        new="            if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_a_record_cannot_claim_a_source_it_can_see_is_not_there",
        ),
        why="a lineage claim naming nothing, indistinguishable in meaning from None but not in the record",
    ),
    Mutation(
        name="derived-accepts-a-false-parent",
        path="src/engcore/scientific/results/provenance.py",
        old='        if "parent_run_id" in overrides and overrides["parent_run_id"] != self.run_id:\n',
        new="        if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_derived_refuses_a_lineage_claim_it_knows_is_false",
        ),
        why="the sanctioned API overwriting the one lineage truth it actually holds",
    ),
    Mutation(
        name="existence-check-never-refuses",
        path="src/engcore/scientific/results/provenance.py",
        old="        if self.parent_run_id not in known:\n",
        new="        if False:\n",
        breaks=(
            "tests/test_core_mechanisms.py::test_the_existence_check_is_opt_in_and_says_so",
        ),
        why="the opt-in check made inert, so a caller that DOES ask gets a false yes",
    ),
)


def mutations_for(task: str) -> tuple[Mutation, ...]:
    """Every mutation whose name starts with ``task``."""
    return tuple(m for m in MUTATIONS if m.name.startswith(task))
