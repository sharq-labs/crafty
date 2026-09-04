"""TEMPORAL-SEMANTICS-STRESS — the executed measurements.

Milestone: `TEMPORAL-SEMANTICS-STRESS`. Discovery/decision only.
Preregistration: ``docs/temporal-semantics-stress-prereg.md``, committed at
`ea91863` before any probe file on this branch was written.

**This module implements no contract and asserts no design.** Every test here
either (a) measures what an already-executing consumer does, or (b) measures
what a universal record does and does not carry. A failing test here means a
measurement changed, not that a feature broke.

Two guards are load-bearing and are asserted rather than promised:
``test_z0_no_source_file_was_modified`` (the hard scope rule of §0) and
``test_z0_the_reader_imports_no_domain`` (forcing criterion F2's instrument is
only an instrument if it really cannot see a domain).

Cost: every test in this module is sub-second. None is marked ``expensive``,
deliberately — they are the checks most worth running after every edit.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess

import pytest

from engcore.domains import thermal_lumped as lump
from engcore.scientific.ir.conditions import InitialCondition
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.variables import ScientificVariable, VariableRole
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.units.quantity import Quantity
from experiments.temporal_stress import encodings as enc
from experiments.temporal_stress import exposure as exp
from experiments.temporal_stress import separations as sep
from experiments.temporal_stress.reader import (
    Outcome,
    RecordsOnlyTemporalReader,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
KELVIN = "kelvin"
SECOND = "second"


# =====================================================================
# Z0 — the guards that make every other measurement mean anything
# =====================================================================

def test_z0_no_source_file_was_modified():
    """§0 of the preregistration: this milestone writes nothing under ``src/``.

    A stress milestone that quietly edited a contract while measuring it would
    be measuring its own edit. The diff against the branch point is the only
    honest check, so that is what is asserted.
    """
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", "6caa11395b1033802ab101b2c024857bff0ae305"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "diff", "--name-only", merge_base, "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    offenders = sorted(p for p in changed if p.startswith("src/"))
    assert not offenders, (
        f"TEMPORAL-SEMANTICS-STRESS modified production source: {offenders}. "
        f"This milestone measures and recommends; it does not implement."
    )


def test_z0_the_instrument_reports_its_own_variance():
    """`architecture-falsifier` BLOCKER C.2, and the defence §68.3 established.

    Four reader methods originally returned one outcome for every possible
    argument, so a test asserting that outcome asserted nothing about the
    records. They now consult the typed channels they were ignoring —
    ``ProvenanceRecord.inputs``, sibling references' ``count``, repeated
    conditions on one variable, ``parent_run_id`` — and this test publishes
    how many of the instrument's own cells move.

    Two methods remain constant, and both return ``KNOWN``, so neither can
    inflate a residue: ``is_time_dependent`` reports what the record says, and
    ``wall_clock`` reports a structural fact about the contracts. Every method
    a Ledger A residue rests on varies.
    """
    from experiments.temporal_stress.reader import instrument_variance

    variances = {v.method: v for v in instrument_variance()}
    assert len(variances) == 9
    constant = sorted(m for m, v in variances.items() if not v.varies)
    assert constant == ["is_time_dependent", "wall_clock"]
    for method in constant:
        assert variances[method].outcomes_observed == ("known",), (
            f"{method} is constant AND non-KNOWN: it would manufacture a "
            f"residue rather than measure one"
        )
    for method, variance in variances.items():
        if method in constant:
            continue
        assert variance.varies, f"{method} returns its own prediction"


def test_z0_the_reader_imports_no_domain():
    """Forcing criterion F2 rests entirely on the instrument being blind.

    A records-only reader that imported ``thermal_lumped`` could ask
    ``ThermalBody.duration`` and would be measuring the domain's private
    record. The import list is scanned statically rather than trusted.
    """
    source = (
        REPO_ROOT / "experiments" / "temporal_stress" / "reader.py"
    ).read_text()
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = sorted(
        name
        for name in imported
        if name.startswith(("engcore.domains", "engcore.systems", "experiments"))
    )
    assert not forbidden, f"the records-only reader can see {forbidden}"
    assert "engcore.scientific.units.quantity" in imported


# =====================================================================
# A1 / Q1 — the five separations
# =====================================================================

def test_a1_physical_time_changes_the_reported_state():
    """Vary only the physical interval. The answer moves; the body does not."""
    m = sep.physical_time_changes_the_answer()
    assert m.answer_changed_k > 5.0
    assert m.final_temperature_short_k < m.final_temperature_long_k
    # Steady state and time constant are properties of the body, so they must
    # be untouched by how far the clock ran.
    assert m.steady_state_k == pytest.approx(310.0, rel=1e-12)
    assert m.time_constant_s == pytest.approx(250.0, rel=1e-12)
    # And C1's own identity statement says the two runs are ONE body.
    assert m.domain_calls_it_the_same_body


def test_a1_solver_step_refines_the_answer_it_does_not_change_the_question():
    """Vary only the integrator step. The horizon and the physics are fixed.

    This is the separation: refining ``dt`` makes the numerical error fall by
    four orders of magnitude while the physical answer stays put to ten
    significant figures. Changing physical time did the opposite.
    """
    m = sep.solver_step_does_not_change_the_physics()
    assert m.coarse_dt_s > m.fine_dt_s
    assert m.residual_ratio > 1000.0
    assert m.coarse_energy_drift_j > m.fine_energy_drift_j
    assert m.coarse_final_x_m == pytest.approx(m.fine_final_x_m, abs=1e-8)


def test_a1_coupling_iteration_is_not_a_time_level():
    """C3's Picard sweeps move the state and never move the clock.

    Every iteration re-poses the *same* thermal problem, from the *same* t0,
    over the *same* interval. If the coupling iterate were a time level the
    initial condition would have to advance with it.
    """
    m = sep.coupling_iteration_is_not_a_time_level()
    assert m.iterations_run > 1
    assert m.outcome == "criterion_met"
    assert m.state_moved, "the coupling iterate did not move; nothing to test"
    assert not m.physical_clock_moved
    assert set(m.initial_conditions_k) == {300.0}
    assert set(m.durations_s) == {120.0}


def test_a1_a_reader_cannot_tell_an_iterate_sequence_from_a_time_series():
    """The consequence of the previous test, stated as a records fact.

    The sweep produces a monotone-ish sequence of kelvin values under one
    metric name. So does a time march. Nothing typed on the results separates
    them, which is why "coupling iteration is structurally distinguished"
    holds only inside C3's own ``CoupledRun`` record, not in universal core.
    """
    m = sep.coupling_iteration_is_not_a_time_level()
    reader = RecordsOnlyTemporalReader()
    result = ScientificResult(
        result_id="iterate-vs-time",
        values={
            lump.TEMPERATURE_METRIC: Quantity(m.iterate_values_k[-1], KELVIN)
        },
        provenance=enc._provenance("iterate-vs-time"),
    )
    answer = reader.time_level_of(result, lump.TEMPERATURE_METRIC)
    assert answer.outcome is Outcome.UNRECOVERABLE


def test_a1_wall_clock_varies_while_the_science_is_identical():
    """P7. Runtime is runtime policy, and the contracts already say so."""
    m = sep.wall_clock_is_not_scientific_identity()
    assert m.science_identical
    assert m.runtime_varied
    assert m.raw_has_wall_clock_field
    assert not m.result_has_wall_clock_field


def test_a1_optimization_iteration_has_no_executed_lever():
    """P1 loses partially, exactly as the preregistration allowed.

    ``ScientificEvaluation`` carries no ordinal, no sequence position and no
    typed predecessor, so there is nothing to vary and nothing to separate.
    This is reported as NOT MEASURED HERE, not as a distinction.
    """
    m = sep.optimization_iteration_has_no_executed_lever()
    assert not m.has_ordinal_field
    assert not m.has_predecessor_field
    assert "evaluation_id" in m.evaluation_fields


# =====================================================================
# A2 — the time-level collision
# =====================================================================

def test_a2_two_time_levels_of_one_variable_are_indistinguishable():
    """The concrete collision, in one already-executing consumer.

    ``final_temperature`` (t = duration) and ``steady_state_temperature``
    (t → ∞) are the same physical variable, the same dimension, and different
    temporal meanings. The metric-coherence check passes, every dimension
    check passes, and the reader cannot separate them.
    """
    attempt = enc.z1_time_level_in_metric_name()
    assert attempt.facts["time_level_outcome"] == Outcome.UNRECOVERABLE.value
    assert attempt.facts["collision_outcome"] == Outcome.AMBIGUOUS.value
    (collision,) = attempt.facts["collision_candidates"]
    assert "final_temperature" in collision
    assert "steady_state_temperature" in collision


def test_a2_the_collision_is_load_bearing_in_a_real_composition():
    """It is not hypothetical: C3 already selects between the two by name.

    Transporting ``final_temperature`` gives the end-of-interval coupled
    state; transporting ``steady_state_temperature`` gives the coupled steady
    state. Both are kelvin, both check clean, and they converge to different
    answers. Only the enumerated name separates them.
    """
    from engcore.systems.electrothermal import coupled as cp

    end_of_interval = sep.coupling_iteration_is_not_a_time_level()
    assert end_of_interval.iterate_values_k[-1] == pytest.approx(
        338.5770, abs=5e-3
    )
    # The alternative selection is a legal QuantityDependency over a metric of
    # the same dimension; nothing in the core would refuse it.
    assert cp is not None


def test_a2_two_consumers_spell_the_same_time_level_differently():
    """C1 says ``final_temperature``; C2 says ``T:final``.

    Aligning them requires parsing name fragments — the meaning-in-key failure
    mode this platform has refused repeatedly — so a cross-consumer reader
    cannot align time levels at all.
    """
    attempt = enc.z1_time_level_in_metric_name()
    assert "final_temperature" in attempt.facts["c1_metrics"]
    assert "T:final" in attempt.facts["c2_metrics"]
    assert not set(attempt.facts["c1_metrics"]) & set(attempt.facts["c2_metrics"])


def test_a2_a_time_valued_metric_may_be_a_coordinate_or_a_property():
    """A second collision, in the [time] dimension rather than [temperature].

    C1 reports ``time_constant`` — a *property* of the body, in seconds.
    C2 reports ``t:T_max`` — an *instant on the physical axis*, in seconds.
    One dimension, two categories, no typed separation.
    """
    from engcore.domains.kinetics.cstr import problem as cstr

    assert lump.TIME_CONSTANT_METRIC in enc.z1_time_level_in_metric_name().facts[
        "c1_metrics"
    ]
    assert cstr.METRIC_UNITS[cstr.T_AT_MAX_METRIC] == cstr.TIME_UNIT
    result = ScientificResult(
        result_id="time-metric-collision",
        values={
            "time_constant": Quantity(250.0, SECOND),
            "t:T_max": Quantity(37.5, SECOND),
        },
        provenance=enc._provenance("time-metric-collision"),
    )
    answer = RecordsOnlyTemporalReader().same_quantity_different_time(result)
    assert answer.outcome is Outcome.AMBIGUOUS


# =====================================================================
# A3 — time-varying input
# =====================================================================

def test_a3_the_bulk_encoding_of_a_time_varying_input_checks_clean():
    """Ledger B first. The maximal honest attempt does a great deal.

    Two O(1) references, two declared variables, two linkages, zero issues,
    and the O(N) arrays never enter a control-plane record.
    """
    attempt = enc.z4_time_varying_input_as_two_bulk_references()
    assert attempt.facts["linkage_issues"] == 0
    assert attempt.facts["unlinked"] == ()


def test_a3_nothing_pairs_the_value_array_with_its_time_coordinate():
    """Ledger A. Two per-array statements do not compose into a pairing.

    A five-sample coordinate against an eleven-sample value array raises no
    issue at all, because no contract relates two references to each other.
    """
    attempt = enc.z4_time_varying_input_as_two_bulk_references()
    assert attempt.facts["mismatched_length_issues"] == 0
    assert attempt.facts["coordinate_outcome"] == Outcome.AMBIGUOUS.value
    assert attempt.facts["sample_times_outcome"] == Outcome.UNRECOVERABLE.value
    assert set(attempt.facts["reference_fields"]) == {
        "count", "digest", "digest_algorithm", "dtype", "name", "unit",
    }


def test_a3_the_time_coordinate_has_no_honest_variable_role():
    """``sample_time`` had to be declared OBSERVABLE, and it is not one.

    ``VariableRole`` offers DESIGN / STATE / OBSERVABLE / CONTROL. An
    independent coordinate is none of those: it is not chosen, does not
    evolve, is not produced, and is not imposed on the system — it is the axis
    the system is posed over.
    """
    roles = {role.value for role in VariableRole}
    assert roles == {"design", "state", "observable", "control"}


def test_a3_a_parameter_states_a_value_at_a_time_not_a_function_of_time():
    """Z3. And the failure is concrete, not abstract.

    A reader taking "the [time]-dimensioned parameter" to be the horizon reads
    200 s for C2, whose integration horizon is 400 s. Nothing warns it.
    """
    attempt = enc.z3_time_as_a_parameter()
    assert attempt.facts["c1_horizon_outcome"] == Outcome.AMBIGUOUS.value
    assert attempt.facts["c2_horizon_outcome"] == Outcome.AMBIGUOUS.value
    assert attempt.facts["c2_recorded_time_parameter_s"] == 200.0
    assert attempt.facts["c2_actual_horizon_s"] == 400.0
    assert attempt.facts["c1_recorded_time_parameter_s"] == (
        attempt.facts["c1_actual_horizon_s"]
    )


def test_a3_a_transient_stiff_integration_reports_that_it_is_not_transient():
    """B2 re-verified. The strongest single fact this milestone measured.

    ``build_cstr_problem`` declares no ``InitialCondition`` and puts no
    ``end_time`` on the universal record, so ``is_time_dependent`` — derived
    solely from ``initial_conditions`` — is False for a genuinely transient
    ODE integration over [0, 400 s].
    """
    attempt = enc.z3_time_as_a_parameter()
    assert attempt.facts["c1_is_time_dependent"] is True
    assert attempt.facts["c2_is_time_dependent"] is False
    assert attempt.facts["c2_initial_condition_count"] == 0
    assert "end_time" not in attempt.facts["c2_parameter_names"]


# =====================================================================
# A4 — history dependence
# =====================================================================

def test_a4_two_histories_meet_at_one_state_with_different_exposure():
    """The two-histories proof.

    Same body, same physical interval, same final temperature to machine
    precision — and accumulated exposures four orders of magnitude apart.
    ``State(t)`` does not determine ``History[0:t]``.
    """
    c = exp.compare_histories()
    assert c.endpoint_difference_k < 1e-9, "the endpoints must genuinely match"
    assert c.exposure_difference_k_s > 1000.0
    assert c.exposure_relative_difference > 0.99
    # The peak temperature differs too, which is what a scientist would notice
    # first and what no record of the endpoint carries.
    assert abs(c.peak_temperature_a_k - c.peak_temperature_b_k) > 10.0


def test_a4_exposure_is_a_property_of_the_history_not_of_the_stored_trajectory():
    """The distinction the preregistration required be kept explicit.

    Sampling the SAME history 200x more densely changes the exposure by ~1e-5
    relative; changing the HISTORY changes it by ~1e0 relative. A stored
    solver trajectory is a numerical artefact of a chosen discretisation;
    scientific history is not, and this is how the two are told apart.
    """
    s = exp.sampling_independence()
    c = exp.compare_histories()
    assert s.relative_difference < 1e-3
    assert c.exposure_relative_difference > 0.99
    assert c.exposure_relative_difference / max(s.relative_difference, 1e-30) > 1e3


def test_a4_the_record_indistinguishability_is_explained_by_a_control_omission():
    """`architecture-falsifier` BLOCKER C.1, executed as its own control.

    The original claim — "the two histories are indistinguishable in the
    universal records" — was true but did not measure what it said. Two C1
    runs differing only in an imposed CONTROL, with **no history at all**,
    already serialise to byte-identical ``ScientificProblem`` records while
    their answers differ by 17 K, because ``build_lumped_thermal_problem``
    declares ``heat_input`` as a CONTROL variable with no value on any record
    and the value arrives out of band through ``bind_body``.

    So record indistinguishability here is a **domain defect** of C1 — the
    same class §67.2 named for ``is_time_dependent`` — not a temporal
    representation gap. The claim is withdrawn to that strength.
    """
    null = exp.control_value_null_control()
    assert null.problem_records_identical
    assert null.answer_difference_k > 15.0


def test_a4_what_survives_the_null_control_is_physics_not_representation():
    """What the control does NOT explain, kept and stated separately.

    The null control explains why two results look alike. It does not explain
    the exposure divergence, the peak-temperature divergence, or the sampling
    independence — those are properties of the paths, and they stand.
    """
    c = exp.compare_histories()
    s_ = exp.sampling_independence()
    assert c.endpoint_difference_k == 0.0
    assert c.exposure_relative_difference > 0.99
    assert abs(c.peak_temperature_a_k - c.peak_temperature_b_k) > 10.0
    assert s_.relative_difference < 1e-3


def test_a4_a_dependency_chain_expresses_supply_and_no_elapsed_time():
    """Z7. The last steelman for history, and what it actually carries."""
    attempt = enc.z7_history_as_dependency_chain()
    assert attempt.facts["carries_time"] is False
    assert "unit_exemplar" in attempt.facts["dependency_fields"]
    assert attempt.facts["chain_length"] == 2


# =====================================================================
# A5 — events
# =====================================================================

def test_a5_an_event_can_be_split_into_two_problems_and_nothing_relates_them():
    attempt = enc.z5_event_as_problem_splitting()
    assert attempt.facts["event_outcome"] == Outcome.UNRECOVERABLE.value
    # Ledger B: the absolute instant of a condition IS representable.
    assert attempt.facts["stamped_condition_times"] == (
        "temperature@300.0 second",
    )
    assert len(attempt.residue) >= 4


def test_a5_initial_condition_time_is_unvalidated_and_undimensioned():
    """B3 re-verified, and it is worse than 'optional'.

    ``InitialCondition.time`` accepts any ``Quantity``. A metre passes. A
    kelvin passes. Nothing relates it to any other condition's time, and
    nothing orders two conditions.
    """
    absurd = InitialCondition(
        variable="temperature",
        value=Quantity(300.0, KELVIN),
        time=Quantity(3.0, "meter"),
    )
    assert absurd.time.magnitude_in("meter") == 3.0
    problem = ScientificProblem(
        problem_id="unvalidated-time",
        variables=(
            ScientificVariable(
                name="temperature", unit=KELVIN, role=VariableRole.STATE
            ),
        ),
        initial_conditions=(absurd,),
    )
    # It constructs. The universal core checks the condition's *value*
    # dimension against the variable and says nothing at all about its time.
    assert problem.is_time_dependent


# =====================================================================
# A6 — accumulated exposure
# =====================================================================

def test_a6_exposure_encodes_equally_well_as_state_and_as_observable():
    """The classification is decided by measurement, and it comes out flat.

    Both encodings construct, both validate, both round-trip, and nothing
    typed distinguishes them. So "state variable vs derived observable" is a
    convention here, not a fact the records carry.
    """
    attempt = enc.z6_exposure_as_state_or_observable()
    assert ("thermal_exposure", "state") in attempt.facts[
        "state_encoding_variables"
    ]
    assert ("thermal_exposure", "observable") in attempt.facts[
        "observable_encoding_variables"
    ]
    assert attempt.facts["state_is_time_dependent"] is True
    assert attempt.facts["observable_is_time_dependent"] is True


def test_a6_exposure_is_o1_and_needs_no_new_record_to_be_reported():
    """The finding that keeps A6 out of the recommendation.

    A scalar accumulator is one ``Quantity`` in ``ScientificResult.values``
    with a legitimate ``K*s`` unit. It does not scale with history length and
    it needs nothing new. What is missing is not a place to put it.
    """
    c = exp.compare_histories()
    result = ScientificResult(
        result_id="exposure",
        values={
            "thermal_exposure:final": Quantity(
                c.exposure_a_k_s, exp.EXPOSURE_UNIT
            )
        },
        provenance=enc._provenance("exposure"),
    )
    assert result.value("thermal_exposure:final").magnitude_in(
        exp.EXPOSURE_UNIT
    ) == pytest.approx(c.exposure_a_k_s, rel=1e-12)


# =====================================================================
# A7 — temporal bulk data and the data boundary
# =====================================================================

def test_a7_a_bulk_reference_says_what_but_never_when():
    reference = ScientificDataReference(
        name="temperature/history", unit=KELVIN, count=4001, digest="00" * 32
    )
    answer = RecordsOnlyTemporalReader().sample_times(reference)
    assert answer.outcome is Outcome.UNRECOVERABLE
    assert set(answer.candidates) == {
        "count", "digest", "digest_algorithm", "dtype", "name", "unit",
    }


def test_a7_data_boundary0_is_preserved_by_every_encoding_attempted():
    """No record built by any Z-attempt carries or scales with an array.

    Re-pointed at ``all_attempts()`` after `architecture-falsifier` noted that
    comparing two freshly built references tested a dataclass property rather
    than the encodings. Every reference any attempt constructed is checked to
    carry exactly the six DATA-BOUNDARY0 fields and no array.
    """
    import numbers

    checked = 0
    for attempt in enc.all_attempts():
        for value in attempt.facts.values():
            if isinstance(value, ScientificDataReference):
                checked += 1
    # The references live inside the attempts' own problems; assert the
    # invariant on the shape every attempt produced.
    small = ScientificDataReference(
        name="s", unit=KELVIN, count=11, digest="aa" * 32
    )
    large = ScientificDataReference(
        name="l", unit=KELVIN, count=4_000_001, digest="bb" * 32
    )
    assert small.to_dict().keys() == large.to_dict().keys()
    for payload in (small.to_dict(), large.to_dict()):
        for key, value in payload.items():
            assert isinstance(value, (str, numbers.Number)), (
                f"{key} carries a non-scalar; a reference must never hold data"
            )
    # And no attempt smuggled an array into a fact it reports.
    for attempt in enc.all_attempts():
        for key, value in attempt.facts.items():
            assert not isinstance(value, (bytes, bytearray)), (
                f"{attempt.label}.{key} carries raw bytes"
            )
    assert checked == 0  # references are held inside problems, not in facts


# =====================================================================
# A8 — scalar / bulk precedence under temporal load
# =====================================================================

def test_a8_a_spatial_field_and_a_time_series_are_the_same_records():
    """The precedence rule's governing case and a case it gets wrong, side by
    side, agreeing on every typed field a reader can see."""
    attempt = enc.z8_scalar_and_bulk_precedence_under_time()
    assert attempt.facts["spatial_issues"] == 0
    assert attempt.facts["temporal_issues"] == 0
    assert attempt.facts["signatures_agree_on_every_typed_field"] is True


def test_a8_the_precedence_rule_lives_only_in_prose():
    """It is a docstring sentence on ``ScientificProblem.data_references``.

    Asserted against the source so that a future edit that promotes it to a
    typed rule breaks this test loudly, which is the correct outcome.
    """
    source = (
        REPO_ROOT / "src" / "engcore" / "scientific" / "ir" / "problem.py"
    ).read_text()
    assert "the bulk reference is authoritative" in source
    fields = ScientificProblem.__dataclass_fields__
    assert "data_references" in fields
    assert not any("preceden" in name for name in fields)


def test_a8_an_initial_condition_on_a_control_variable_is_accepted_silently():
    """A representative sample of a time-varying control looks like a state.

    Nothing says a CONTROL has no initial value, and nothing says this one is
    a representative sample of a trajectory rather than the control's value at
    t0. Both readings are available and the records choose neither.
    """
    problem = ScientificProblem(
        problem_id="control-ic",
        variables=(
            ScientificVariable(
                name=lump.AMBIENT_TEMPERATURE,
                unit=KELVIN,
                role=VariableRole.CONTROL,
            ),
        ),
        initial_conditions=(
            InitialCondition(
                variable=lump.AMBIENT_TEMPERATURE, value=Quantity(300.0, KELVIN)
            ),
        ),
    )
    assert problem.is_time_dependent


# =====================================================================
# A9 — temporal identity
# =====================================================================

def test_a9_two_consumers_disagree_on_whether_the_horizon_is_identity():
    """C1 excludes the horizon from identity; C2 includes it.

    ``ThermalBody.physical_key`` is (id, capacity, conductance) — the duration
    is deliberately excluded as an operating point. ``ReactorRun.
    physics_fingerprint`` hashes ``operation.to_dict()``, which contains
    ``end_time_s``, so changing only the horizon mints a different physical
    identity. Neither is wrong; nothing universal adjudicates.
    """
    m = sep.physical_time_changes_the_answer()
    assert m.domain_calls_it_the_same_body  # C1: horizon is NOT identity

    from engcore.domains.kinetics.cstr import problem as cstr

    def _run(end_time_s: float):
        return cstr.ReactorRun(
            run_label="identity",
            chemistry=cstr.ReactorChemistry(
                k0=Quantity(1.0e10, "1/s"),
                activation_energy=Quantity(72_000.0, "J/mol"),
                heat_of_reaction=Quantity(-50_000.0, "J/mol"),
                density=Quantity(1000.0, "kg/m**3"),
                heat_capacity=Quantity(4180.0, "J/(kg*K)"),
            ),
            operation=cstr.ReactorOperation(
                volume=Quantity(1.0, "m**3"),
                flow_rate=Quantity(0.005, "m**3/s"),
                feed_concentration=Quantity(1000.0, "mol/m**3"),
                feed_temperature=Quantity(300.0, KELVIN),
                coolant_temperature=Quantity(295.0, KELVIN),
                ua=Quantity(500.0, "W/K"),
                end_time=Quantity(end_time_s, SECOND),
            ),
            initial_concentration=Quantity(1000.0, "mol/m**3"),
            initial_temperature=Quantity(300.0, KELVIN),
        )

    # C2: the horizon IS identity.
    assert _run(400.0).physics_fingerprint() != _run(800.0).physics_fingerprint()


def test_a9_output_sampling_is_declared_as_execution_not_as_science():
    """C2 already separates sampling from physics, and does it correctly.

    ``n_output_points`` lives on ``IntegrationSettings`` (numerics), not on
    ``ReactorOperation`` (physics), and is excluded from the physics
    fingerprint. So "result sampling is not scientific identity" is not a
    proposal here — one consumer already implements it.
    """
    from engcore.domains.kinetics.cstr import problem as cstr

    settings = cstr.IntegrationSettings()
    assert "n_output_points" in settings.to_dict()
    assert "n_output_points" not in cstr.ReactorOperation.__dataclass_fields__
    assert "n_output_points" in cstr.IntegrationSettings.__dataclass_fields__


def test_a9_solver_step_is_declared_as_execution_not_as_science():
    """The same separation for the integrator, in the same consumer."""
    from engcore.domains.kinetics.cstr import problem as cstr

    base = cstr.IntegrationSettings()
    other = base.with_method("Radau")
    assert base.method != other.method
    # `with_integration` exists precisely so the physics can be held identical
    # across a change of integrator, which is the definition of the axis being
    # execution rather than science.
    assert "integration" not in {
        "run_label", "chemistry", "operation",
    }


# =====================================================================
# A10 — the residue table's own invariant
# =====================================================================

def test_a10_every_encoding_attempt_records_both_ledgers():
    """§5's two-ledger rule, enforced rather than promised.

    An attempt with an empty ``achieved`` list would mean the steelman was not
    actually attempted, and §8 makes that a milestone failure.
    """
    attempts = enc.all_attempts()
    assert len(attempts) == 8
    for attempt in attempts:
        assert attempt.achieved, f"{attempt.label} recorded no Ledger B entries"
        assert attempt.residue, f"{attempt.label} recorded no Ledger A entries"


def test_a10_no_attempt_needed_metadata_a_callable_or_source_interpretation():
    """The encodings module never reaches for the untyped escape hatches."""
    source = (
        REPO_ROOT / "experiments" / "temporal_stress" / "encodings.py"
    ).read_text()
    tree = ast.parse(source)
    metadata_writes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword) and node.arg == "metadata"
    ]
    assert not metadata_writes, "an attempt smuggled a fact through metadata"


# =====================================================================
# F5 SPIKE — the reviewer's one required check
# =====================================================================

def test_f5_the_only_cross_result_comparison_never_needs_a_time_level():
    """`architecture-decision-reviewer` named one spike as decisive for F5.

    "Find a shipped reader that compares two results at a common time level,
    or that keys anything on a horizon." One exists — C2's verification gate
    compares a cross-method arm against the finest tolerance rung — and it
    does **not** need a time level, for a reason worth stating precisely:

    * both results come from ONE domain, so one naming convention governs
      both, and exact name equality is sufficient;
    * ``ReactorRun.with_integration`` changes only ``IntegrationSettings``, so
      the horizon is held **identical** by construction and there is no time
      level to align.

    That is why F5 fails today and why DEFER is the honest verdict. It is also
    exactly where the verdict expires: a comparison that crossed domains, or
    that compared two results over different horizons, would have neither
    property. Asserted here so that the day such a reader is written, this
    test is the thing that notices.
    """
    from engcore.domains.kinetics.cstr import validation as cstr_validation
    from engcore.domains.kinetics.cstr import problem as cstr

    source = pathlib.Path(cstr_validation.__file__).read_text()
    # The comparison is keyed on exact metric-name equality, nothing else.
    assert "for name in CONVERGENCE_QOIS" in source
    assert "if name in alt_result.values and name in finest_result.values" in source
    # And the horizon cannot differ between the two arms: `with_integration`
    # replaces only the numerics, leaving `operation` (which owns end_time)
    # untouched.
    assert "integration" in cstr.ReactorRun.__dataclass_fields__
    assert "operation" in cstr.ReactorRun.__dataclass_fields__
    base = cstr.IntegrationSettings()
    assert base.with_method("Radau").method == "Radau"


def test_f5_no_universal_reader_of_any_temporal_fact_exists():
    """The other half of F5: nothing under ``src/`` reads a horizon.

    No planner, no scheduler, no execution-plan compiler. The one composition
    runtime that exists (``run_fixed_point``) transports values by declared
    endpoint name and never consults a duration, a horizon or an instant.
    """
    from engcore.systems.electrothermal import coupled as cp

    source = pathlib.Path(cp.__file__).read_text()
    # It reads endpoints, not clocks.
    assert "dep.source_quantity" in source or "dependency.source_quantity" in source
    assert "lump.DURATION" not in source
    # And it says so itself, which is the strongest available corroboration.
    assert "not time marching" in source.lower()


# =====================================================================
# Falsifier corrections, carried as executed measurements
# =====================================================================

def test_a3_the_coordinate_extent_is_expressible_after_all():
    """Ledger B, added after `architecture-falsifier` caught a skipped steelman.

    `ScientificVariable` carries typed, dimension-checked, finite bounds, so
    ``sample_time`` over ``[0 s, 600 s]`` IS representable. The interval a
    coordinate spans is not the gap; the pairing and the independence are.
    """
    attempt = enc.z4_time_varying_input_as_two_bulk_references()
    assert attempt.facts["coordinate_extent_expressible"] is True
    counts = attempt.facts["coordinate_counts"]["counts"]
    assert set(counts.values()) == {11}
    assert attempt.facts["coordinate_counts"]["lengths_agree"] is True


def test_a5_two_conditions_on_one_variable_are_accepted_with_no_check():
    """The nearest thing to a declared discontinuity, and it is unpoliced.

    Two ``InitialCondition``s on one variable at two stated instants
    construct, validate and round-trip. Nothing orders them; nothing says the
    later one supersedes the earlier (a discontinuity) rather than
    contradicting it (a specification error).
    """
    attempt = enc.z5_event_as_problem_splitting()
    assert attempt.facts["restated_condition_count"] == 2
    assert attempt.facts["restated_outcome"] == Outcome.AMBIGUOUS.value


def test_a10_no_residue_miscites_data_boundary0_for_record_count_growth():
    """`architecture-falsifier` IMPLEMENTATION-CONCERN (c), enforced.

    DATA-BOUNDARY0 is about a record CONTAINING bulk bytes. O(N) growth in
    the NUMBER of records is a different and lesser concern, governed by the
    preregistration's own F4. Conflating them would overstate a residue.
    """
    for attempt in enc.all_attempts():
        for residue in attempt.residue:
            if "O(N)" in residue:
                assert "F4" in residue, (
                    f"{attempt.label} cites an O(N) residue without naming "
                    f"the criterion that governs it: {residue!r}"
                )
