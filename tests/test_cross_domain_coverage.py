"""CROSS-DOMAIN-COVERAGE — the executable half of the milestone.

Preregistration: `docs/cross-domain-coverage-stress-prereg.md`, committed at
`a3db20d` before any probe source file was written.
Evidence: `docs/cross-domain-coverage-stress-evidence.md`, written after this ran.

**This module asserts measurements, not opinions.** Every coverage cell is
derived by :func:`instrument.forcing_verdict` from a records-only
recoverability probe and a per-consumer declaration of what the science
involves. No human chooses a cell, and the matrix is asserted whole so that a
later contract change moves this test rather than silently moving the evidence.

Several preregistered predictions **failed**. Each such test carries the
prediction it settles and says plainly which way it went; the evidence document
records them as deviations rather than restating them.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.ir.variables import VariableRole
from engcore.scientific.realizations.definition import ModelFormulation
from engcore.scientific.results.result import ScientificResult
from engcore.scientific.results.validation import ValidationOutcome
from engcore.scientific.units.quantity import Quantity

from experiments.cross_domain_coverage import dynamics as dyn
from experiments.cross_domain_coverage import instrument as inst
from experiments.cross_domain_coverage import mechanics as mech
from experiments.cross_domain_coverage import records as rec
from experiments.cross_domain_coverage import species as spc
from experiments.cross_domain_coverage import transport2d as tr2

REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_ROOT = REPO_ROOT / "experiments" / "cross_domain_coverage"

ALL_COLUMNS = rec.CONSUMER_COLUMNS + rec.CONTROL_COLUMNS


@pytest.fixture(scope="module")
def columns():
    """Every column, round-tripped through JSON so the reader gets payloads only."""
    raw = rec.coverage_columns()
    return {
        name: (json.loads(json.dumps(payloads)), science)
        for name, (payloads, science) in raw.items()
    }


@pytest.fixture(scope="module")
def matrix(columns):
    return inst.coverage_matrix(columns)


# =============================================================================
# The probes are real science, not props
# =============================================================================

def test_a_patch_test_recovers_the_exact_stress_in_both_elements():
    """CONSUMER A physics. A machine-precision identity, not a tolerance.

    Every constant-strain triangle reproduces a linear displacement field
    exactly, so a uniaxial patch must return ``sigma_xx = E eps_xx`` with zero
    error and zero transverse stress. Any departure is an assembly or
    constitutive error and nothing else.
    """
    result = mech.run_patch_test()
    assert result["max_relative_error"] == 0.0
    assert result["max_transverse_stress_pa"] < 1e-6
    assert len(result["elements"]) == 2
    for entry in result["elements"]:
        assert entry["stress"][0] == pytest.approx(210.0e6, rel=1e-12)
        assert entry["sigma_zz"] == 0.0


def test_a_shear_case_is_symmetric_and_in_equilibrium():
    """CONSUMER A physics. Two identities that hold for any correct assembly."""
    result = mech.run_shear_case()
    assert result["symmetry_residual"] == 0.0
    assert result["equilibrium_residual_n"] < 1e-6
    assert result["applied_force_n"] == pytest.approx(2.0e4)


def test_a_plane_strain_is_different_physics_on_an_identical_mesh():
    """CASE A3. Same geometry, material, mesh and loads; different constitutive
    law, and a non-zero out-of-plane stress that the in-plane record cannot hold.
    """
    contrast = mech.plane_strain_contrast()
    assert contrast["sigma_zz_plane_stress_pa"] == 0.0
    assert contrast["sigma_zz_plane_strain_pa"] > 1e5
    assert 0.9 < contrast["displacement_ratio"] < 1.0


def test_b_velocity_field_is_divergence_free_and_mms_error_falls():
    """CONSUMER B physics.

    The divergence check is asserted rather than assumed: a manufactured source
    derived on the assumption ``div u = 0`` would be wrong if the field were
    not solenoidal, and that error would masquerade as discretization error.

    **No convergence order is claimed.** At peak cell Peclet 8.8 and 4.4 the run
    is deep in the advection-dominated regime where first-order upwind's
    numerical diffusion dominates, so a clean asymptotic rate is not expected at
    these two grids and the preregistration never promised one.
    """
    coarse, fine = tr2.case_b(8), tr2.case_b(16)
    assert tr2.divergence_residual(coarse) == 0.0

    coarse_error = tr2.solution_error(coarse, tr2.solve_transport2d(coarse))
    fine_error = tr2.solution_error(fine, tr2.solve_transport2d(fine))
    assert fine_error < coarse_error
    assert fine_error < 0.35


def test_b_every_boundary_region_carries_both_inflow_and_outflow():
    """The 2D orientation finding, and it is what 1D structurally could not show.

    In 1D a boundary was a point and its role was a single fact, so a region was
    at least the right granularity. Under solid-body rotation ``u . n`` changes
    sign at the midpoint of every side, so each of the four
    `BoundaryCondition` records is being asked to carry two different scientific
    roles at once.
    """
    case = tr2.case_b(8)
    fractions = tr2.orientation_summary(case)
    assert set(fractions) == set(tr2.REGIONS)
    for region, fraction in fractions.items():
        assert 0.0 < fraction < 1.0, f"{region} is uniformly one role"
        assert fraction == pytest.approx(0.5)


def test_b_reversing_the_rotation_swaps_the_inflow_sets_and_no_record_moves():
    """CASE B3. The 2D generalisation of the previous milestone's R1a.

    The fraction alone cannot show this — both directions leave every side
    half-inflow — so the *set* is compared. The sets invert; every serialized
    boundary record is byte-identical.
    """
    forward = tr2.case_b(8)
    reversed_case = forward.with_omega(-forward.omega_per_s)

    for region in tr2.REGIONS:
        ahead = tr2.inflow_signature(forward, region)
        behind = tr2.inflow_signature(reversed_case, region)
        assert ahead == tuple(not flag for flag in behind), region

    ahead_problem = rec.build_transport_problem(forward)
    behind_problem = rec.build_transport_problem(reversed_case)
    assert [b.to_dict() for b in ahead_problem.boundary_conditions] == [
        b.to_dict() for b in behind_problem.boundary_conditions
    ]


def test_c_the_weighted_invariant_holds_and_the_naive_one_does_not():
    """CONSUMER C physics, and the whole point of the consumer.

    ``c_A + c_B + 2 c_C`` is conserved to machine precision. The ``2`` comes
    from the stoichiometric matrix and from nowhere else, so a reader holding
    every typed record this platform can produce would compute the unweighted
    sum and report a violated conservation law for a perfectly conserved system.
    """
    case = spc.case_c(500)
    _, trajectory = spc.integrate(case)

    assert spc.conservation_drift(trajectory) < 1e-12
    assert spc.naive_drift(trajectory) > 1.0
    assert spc.admissibility_violation(trajectory) == 0.0


def test_c_the_linear_sub_case_matches_its_exact_solution():
    """CASE C2. ``k2 = 0`` is a linear reversible pair with a closed form."""
    case = spc.case_c_linear(2000)
    final, _ = spc.integrate(case)
    reference = spc.linear_reference(case, case.end_time_s)

    assert max(abs(a - b) for a, b in zip(final, reference)) < 1e-12
    assert final[1] / final[0] == pytest.approx(spc.equilibrium_ratio(case), rel=1e-6)


def test_d_the_constrained_form_conserves_energy_and_stays_on_the_manifold():
    """CONSUMER D physics. Three independent checks, none a tuned tolerance."""
    case = dyn.case_d(4000)
    result = dyn.run_cartesian(case)

    assert result["max_constraint_residual_m2"] < 1e-9
    assert result["max_energy_drift_j"] < 1e-9
    assert dyn.measured_period_s(case, result) == pytest.approx(
        case.exact_period_s, rel=1e-3
    )


def test_d_two_realizations_with_different_unknowns_agree():
    """The Cartesian and angular forms integrate **different state vectors**.

    Every previous realization pair in this repository — central/upwind,
    native/ngspice — kept the same unknowns and changed how they were computed.
    These change what the unknowns are, and still agree.
    """
    case = dyn.case_d(4000)
    agreement = dyn.realization_agreement(case)
    assert agreement["max_position_difference_m"] < 1e-9


def test_d_initial_conditions_can_be_individually_valid_and_jointly_impossible():
    """CASE D3. The relational-initial-condition finding, measured.

    Each of the four numbers is finite, correctly dimensioned and inside any
    plausible declared range. The inconsistency is a property of the **set**,
    and no record relates one `InitialCondition` to another.
    """
    case = dyn.case_d(10)
    consistent = dyn.initial_consistency(case, case.cartesian_initial())
    assert consistent["g"] == pytest.approx(0.0, abs=1e-15)
    assert consistent["g_dot"] == pytest.approx(0.0, abs=1e-15)

    bad = dyn.inconsistent_initial_state(case)
    residuals = dyn.initial_consistency(case, bad)
    assert abs(residuals["g"]) > 0.1

    problem = rec.build_dynamics_problem(case)
    assert len(problem.initial_conditions) == 4
    for condition in problem.initial_conditions:
        assert isinstance(condition.value, Quantity)


# =============================================================================
# The instrument is honest
# =============================================================================

def test_the_instrument_cannot_see_any_probe():
    """One shared reader, importing no probe module. Asserted by AST scan.

    Preregistration fail condition 11 makes a per-consumer reader a milestone
    failure, because the entire cost case rests on one instrument serving four
    structurally unlike consumers.
    """
    tree = ast.parse((PROBE_ROOT / "instrument.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            if node.level:
                imported.add(f".{node.module or ''}")
    forbidden = {
        name
        for name in imported
        if name.startswith(".")
        or any(
            probe in name
            for probe in ("mechanics", "transport2d", "species", "dynamics", "records")
        )
    }
    assert not forbidden, f"the shared instrument imported {sorted(forbidden)}"


def test_one_instrument_serves_every_column(columns, matrix):
    """Four consumers and two controls, one probe set, no per-column branching."""
    assert set(columns) == set(ALL_COLUMNS)
    assert len(matrix) == len(inst.CONCEPTS)
    for row in matrix.values():
        assert set(row) == set(ALL_COLUMNS)


def test_every_cell_is_derived_by_the_stated_rule(matrix, columns):
    """No cell is a judgement call. Each is `forcing_verdict` of its inputs."""
    for concept, row in matrix.items():
        for name, finding in row.items():
            involved = concept in columns[name][1]
            assert finding.forcing is inst.forcing_verdict(
                involved, finding.recoverability
            )


# =============================================================================
# The coverage matrix — the central measurement
# =============================================================================

#: The measured matrix, asserted whole. `F` forced, `P` pressured, `-` untouched.
#: Column order: A-mechanics, B-transport, C-species, D-dynamics, ctl-dc,
#: ctl-lumped.
EXPECTED_MATRIX: dict[str, str] = {
    "SpatialFieldSemantics": "FF----",
    "VariableToBulkLinkage": "FFFF--",
    "FieldSupport": "FF----",
    "Domain/Topology": "FF--P-",
    "BoundaryIdentity": "PP--F-",
    "BoundaryOrientation-sign": "-F--F-",
    "BoundaryOrientation-normal": "F-----",
    "BoundaryCondition": "PP----",
    "Rank1": "FF-F--",
    "Rank2": "F-----",
    # Was "-F----" before MIN-FIELD-SUPPORT-FOUNDATION added
    # ScientificProblem.data_references; this probe re-checks the live type
    # on every run (instrument._problem_can_reference_bulk), so the same
    # instrument now measures SERVED for B-transport without any edit to
    # this milestone's own probe code — see
    # docs/min-field-support-foundation-evidence.md.
    "FieldValuedInput": "-S----",
    "Constraint": "--PP--",
    "DifferentialAlgebraicPartition": "---F--",
    "RelationalInitialCondition": "---F--",
    "DynamicState": "--SS-S",
    "MaterialIdentity": "PPP-PP",
    "MaterialState": "------",
    "PropertyRequirement-scalar": "----SS",
    "PropertyRequirement-rank2": "F-----",
    "SpeciesIdentity": "--P---",
    "Composition": "--F---",
    "ReactionRelationship": "--F---",
    "CausalPort": "------",
    "PhysicalConnector": "------",
    "DiscretizationDefinition": "PPPP-P",
    "RuntimeState": "------",
    "Event": "------",
    "QuantityIdentity": "PPPPP-",
    "AdmissibilityAttainment": "FFFFPP",
    "TimeVaryingInput": "---F--",
}


def test_the_coverage_matrix(matrix):
    """The milestone's product, asserted cell by cell."""
    measured = {
        concept: "".join(row[name].forcing.value for name in ALL_COLUMNS)
        for concept, row in matrix.items()
    }
    assert measured == EXPECTED_MATRIX


def test_p2_the_by_construction_negatives_are_negative(matrix):
    """PREDICTION P-2 — HELD.

    No consumer is a coupled system and none has a discontinuity, so these
    three rows are all-dash by construction. **Any non-dash here would be an
    instrument error, not a discovery**, and this test is what would catch it.
    """
    for concept in ("CausalPort", "PhysicalConnector", "Event"):
        row = matrix[concept]
        assert all(
            row[name].forcing is inst.Forcing.UNTOUCHED for name in ALL_COLUMNS
        ), concept


def test_column_variance_is_measured_and_published(columns):
    """THE INSTRUMENT'S OWN LIMIT, measured. Closes the adversarial pass's C-1.

    A probe whose recoverability verdict is the same for every payload
    contributes exactly **one global fact about the contracts**; the
    cross-column pattern of that row is then the `science` declarations
    re-printed, not a measurement of the consumers. Such a row is a
    *contract-gap measurement*, and reporting it as evidence that N materially
    different consumers independently need something would be circular.

    **24 of 30 rows are column-constant.** That is the honest limit of this
    method and the evidence document states it in those terms.

    The six that vary are the ones carrying claims, which is what makes the
    corrected claims defensible: `VariableToBulkLinkage`, `Domain/Topology`,
    `AdmissibilityAttainment` and `DynamicState` are genuinely read out of the
    records rather than declared.
    """
    varies = inst.column_variance(columns)
    varying = sorted(name for name, changed in varies.items() if changed)
    assert varying == [
        "AdmissibilityAttainment",
        "BoundaryCondition",
        "BoundaryIdentity",
        "Domain/Topology",
        "DynamicState",
        "VariableToBulkLinkage",
    ]
    assert sum(1 for changed in varies.values() if not changed) == 24


def test_variable_to_bulk_linkage_is_forced_by_all_four_and_measured(matrix, columns):
    """The strongest surviving cross-family result, and it is *exhibited*.

    Split out of a former `ScientificField` row that conflated spatial-field
    semantics with this. The two have different column profiles: spatial
    semantics are an A/B concern, and this linkage gap is exhibited by **all
    four** consumers — each attaches a bulk `ScientificDataReference` to a
    multi-variable problem, and `ScientificDataReference` carries no field
    naming a variable, so neither the association nor the ordering is recorded.

    The probe is column-varying: it returns fully-representable for a payload
    with no bulk data, which is what both controls get.
    """
    row = matrix["VariableToBulkLinkage"]
    assert all(
        row[name].forcing is inst.Forcing.FORCED for name in rec.CONSUMER_COLUMNS
    )
    assert all(
        row[name].forcing is inst.Forcing.UNTOUCHED for name in rec.CONTROL_COLUMNS
    )
    assert inst.column_variance(columns)["VariableToBulkLinkage"] is True


def test_admissibility_is_exhibited_by_four_consumers_not_asserted(matrix, columns):
    """PREDICTION P-5 — HELD, but at 4/6 and only after a correction.

    An earlier version scored this 6/6 from a probe that decoded the result and
    then never read it, while **zero of six columns recorded an admissibility
    check**. The claim was made about criteria living in probe source and test
    assertions, never in a record.

    Now every consumer writes a real check into its `ValidationReport`, and the
    four are of four genuinely different kinds — a positive-definite invariant
    (A), a range excursion under a maximum principle (B), a non-negativity
    excursion (C), and a residual of an algebraic relation (D). The controls
    carry no result, so the question is unreadable for them and they score
    `P`, not `F`.
    """
    row = matrix["AdmissibilityAttainment"]
    assert all(
        row[name].forcing is inst.Forcing.FORCED for name in rec.CONSUMER_COLUMNS
    )
    assert all(
        row[name].forcing is inst.Forcing.PRESSURED for name in rec.CONTROL_COLUMNS
    )

    # The checks exist in the records, and none can claim an attained level.
    for name in rec.CONSUMER_COLUMNS:
        payloads, _ = columns[name]
        result = ScientificResult.from_dict(payloads["result"])
        admissibility = [
            check
            for check in result.validation.checks
            if check.establishes is None and check.tolerance is not None
        ]
        assert admissibility, name
        assert all(check.establishes is None for check in admissibility)


def test_the_four_admissibility_criteria_are_of_four_different_kinds():
    """The pre-committed anti-selection defence, made true of the code.

    Preregistration §8.3 named "four structurally unrelated kinds" as the
    evidence distinguishing a universal from a selection artifact. The
    adversarial pass found that claim contradicted by the source — three were
    deliberately harmonised excursion measures and `mechanics` had no
    admissibility notion at all. `mechanics.strain_energy_violation` is the
    repair: the sign of a positive-definite invariant, which is not an
    excursion measure.
    """
    shear = mech.run_shear_case()
    assert mech.strain_energy(shear) > 0.0
    assert mech.strain_energy_violation(shear) == 0.0

    case = tr2.case_b(8)
    assert tr2.admissibility_violation(tr2.solve_transport2d(case)) >= 0.0

    _, trajectory = spc.integrate(spc.case_c(200))
    assert spc.admissibility_violation(trajectory) == 0.0

    pendulum = dyn.case_d(2000)
    assert dyn.admissibility_violation(pendulum, dyn.run_cartesian(pendulum)) < 1e-9


def test_topology_in_the_control_is_a_domain_artifact_not_a_gap(matrix):
    """WITHDRAWN CLAIM. See evidence deviation D-4.

    An earlier version scored `ctl-dc` as **forcing** `Domain/Topology` and
    cited it as the single best answer to "these gaps are PDE artifacts". That
    was a false gap: `dc/problem.py` records that it translates a circuit
    *"without smuggling topology into the IR"* because connectivity travels
    separately, bound to the problem by a verified fingerprint. The probe was
    never handed that artifact.

    Handing it over changes the cell from `F` to `P`: adjacency is recoverable,
    from a typed **domain** record, by a reader that knows this domain's
    artifact schema. So the control no longer supports the non-PDE claim, and
    the claim is withdrawn.
    """
    row = matrix["Domain/Topology"]
    assert row["ctl-dc"].forcing is inst.Forcing.PRESSURED
    assert row["ctl-dc"].recoverability is inst.Recoverability.REQUIRES_SOURCE
    assert "DOMAIN artifact" in row["ctl-dc"].detail
    forced = [n for n in rec.CONSUMER_COLUMNS if row[n].forcing is inst.Forcing.FORCED]
    assert forced == ["A-mechanics", "B-transport"], (
        "topology is now forced only by the two field consumers, which is "
        "exactly the PDE-shaped profile the withdrawn claim denied"
    )


def test_served_is_distinguishable_from_untouched(matrix):
    """Closes the adversarial pass's correction 10.

    `involved AND fully representable` used to return a dash, making a concept
    the contracts genuinely handle indistinguishable from one no consumer
    touched — a collapse that had already produced two misreadings. `S` now
    says "served".

    The distinction is load-bearing here: `PropertyRequirement-scalar` is `S`
    in both controls because it **is** declared and **is** served, while
    `MaterialState` is a dash because no column declares it. Under the old
    encoding both rows read identically.
    """
    assert matrix["PropertyRequirement-scalar"]["ctl-dc"].forcing is inst.Forcing.SERVED
    assert matrix["MaterialState"]["ctl-dc"].forcing is inst.Forcing.UNTOUCHED
    assert matrix["DynamicState"]["D-dynamics"].forcing is inst.Forcing.SERVED


def test_the_five_conflated_probes_now_answer_structurally(columns):
    """Closes the adversarial pass's C-2 — an armed false-negative generator.

    Five probes answered the *recoverability* question with a *forcing*
    argument ("no consumer here is a coupled system"), all returning
    fully-representable and therefore a dash. Any future consumer that declared
    a port would have been silently served a dash, which is the exact shape the
    previous milestone hit twice.

    They now return the structural answer, and the dash is earned by the
    declaration instead.
    """
    payloads, _ = columns["D-dynamics"]
    for probe in (
        inst.probe_causal_port,
        inst.probe_physical_connector,
        inst.probe_event,
        inst.probe_material_state,
        inst.probe_runtime_state,
    ):
        recoverability, ledger, _ = probe(payloads)
        assert recoverability is inst.Recoverability.IMPOSSIBLE
        assert ledger is inst.Ledger.ABSENT_RECORD
        # And the dash still appears, because nothing declares them involved.
        assert inst.forcing_verdict(False, recoverability) is inst.Forcing.UNTOUCHED


def test_the_runtime_state_contradiction_is_resolved(columns, matrix):
    """Closes the adversarial pass's C-3.

    D's bundle declared `RuntimeState` involved while D's probe asserted
    nothing here maintains state across runs. Two records of one fact
    disagreed and the probe silently won. The declaration was wrong — a
    trajectory is bulk data on **one** result — and it is removed.
    """
    _, science = columns["D-dynamics"]
    assert "RuntimeState" not in science
    assert matrix["RuntimeState"]["D-dynamics"].forcing is inst.Forcing.UNTOUCHED


def test_the_admissibility_bound_steelman_was_attempted(columns):
    """Closes the adversarial pass's C-5 — a preregistered fail condition.

    `ScientificVariable.lower`/`upper` is an existing typed channel for exactly
    this, and an earlier version declared the admissibility gap without ever
    attempting it. The bound is now declared on every species concentration.

    The measurement is what happens next: it is declarable, dimension-checked,
    serialized — and **no path that inspects a `ScientificResult` reads it**,
    so it is a bound that binds nothing. That is a narrower and truer finding
    than "it cannot be expressed".
    """
    payloads, _ = columns["C-species"]
    problem = ScientificProblem.from_dict(payloads["problem"])
    for name in spc.SPECIES:
        variable = problem.variable(f"c:{name}")
        assert variable.lower is not None
        assert variable.lower.magnitude == 0.0

    callers = set(
        subprocess.run(
            ["git", "grep", "-l", "require_within_bounds", "--", "src/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    )
    assert not any("results" in path for path in callers), (
        "no result path consults declared variable bounds"
    )


def test_p1_unique_forcing_counts_are_measured_and_two_fall_short(matrix):
    """PREDICTION P-1 — PARTIALLY FALSIFIED. See evidence deviation D-1.

    Predicted at least three uniquely forced concepts per consumer. Measured
    3 / 2 / 2 / 3 at the time this test was first written: `B` loses
    `BoundaryCondition` and `C` loses `SpeciesIdentity`, both of which came
    back **pressured** rather than **forced** — they are awkwardly
    representable via naming convention and metadata, not impossible.

    The preregistration says a consumer below three "was redundant". The
    measurement does not support that word for either: each still uniquely
    forces two concepts that no other consumer forces at all. What is falsified
    is the threshold, not the consumers.

    UPDATED by `MIN-FIELD-SUPPORT-FOUNDATION`: this instrument's own
    ``probe_field_valued_input`` re-checks ``ScientificProblem`` live on every
    run (``instrument._problem_can_reference_bulk``), not a frozen snapshot.
    That milestone added ``ScientificProblem.data_references``, so
    `FieldValuedInput` now measures `SERVED` for B-transport rather than
    `FORCED` — independent corroboration, from a probe this milestone did not
    write, that the gap it targeted is closed. B-transport's unique-forcing
    count therefore measures 1, not 2, as of this update — see
    docs/min-field-support-foundation-evidence.md.
    """
    unique = inst.unique_forcings(matrix, rec.CONSUMER_COLUMNS)
    assert {name: len(items) for name, items in unique.items()} == {
        "A-mechanics": 3,
        "B-transport": 1,
        "C-species": 2,
        "D-dynamics": 3,
    }
    assert unique["A-mechanics"] == (
        "BoundaryOrientation-normal",
        "PropertyRequirement-rank2",
        "Rank2",
    )
    assert unique["B-transport"] == ("BoundaryOrientation-sign",)
    assert unique["C-species"] == ("Composition", "ReactionRelationship")
    assert unique["D-dynamics"] == (
        "DifferentialAlgebraicPartition",
        "RelationalInitialCondition",
        "TimeVaryingInput",
    )


def test_p3_material_concepts_are_forced_by_nobody(matrix):
    """PREDICTION P-3 — HELD on its substance, FAILED on its control half.

    `MaterialState` and scalar `PropertyRequirement` are forced by **none** of
    the six columns, which directly corroborates `electrical/material.py`'s
    recorded argument that no property hierarchy was needed.

    The prediction also said both would be *pressured* in the control. They are
    not: they come back fully representable, so the derivation rule correctly
    returns a dash. That is a **stronger** negative than predicted, not a weaker
    one — the concepts are served, not awkwardly served.
    """
    for concept in ("MaterialState", "PropertyRequirement-scalar"):
        row = matrix[concept]
        assert all(
            row[name].forcing is not inst.Forcing.FORCED for name in ALL_COLUMNS
        ), concept

    # And the two rows are now visibly different, which they were not before
    # the `SERVED` token existed: the scalar property requirement is declared
    # by both controls and **is served**; material state is declared by nobody.
    assert matrix["PropertyRequirement-scalar"]["ctl-dc"].forcing is inst.Forcing.SERVED
    assert matrix["MaterialState"]["ctl-dc"].forcing is inst.Forcing.UNTOUCHED


def test_dynamic_state_is_already_representable(matrix):
    """PREDICTION (row 13) — FALSIFIED, and it is a win for the contracts.

    `DynamicState` was predicted forced by C and D and pressured in the lumped
    control. It is forced by nobody: `ScientificVariable(role=STATE)` plus
    `InitialCondition` plus `is_time_dependent` represent an evolving state
    cleanly, and the probe returns fully representable for every column that
    has one.
    """
    row = matrix["DynamicState"]
    assert all(row[name].forcing is not inst.Forcing.FORCED for name in ALL_COLUMNS)
    for name in ("C-species", "D-dynamics", "ctl-lumped"):
        assert row[name].forcing is inst.Forcing.SERVED
        assert (
            row[name].recoverability is inst.Recoverability.FULLY_REPRESENTABLE
        )
    assert rec.build_species_problem(spc.case_c(10)).is_time_dependent is True
    assert rec.build_dynamics_problem(dyn.case_d(10)).is_time_dependent is True


def test_the_matrix_returns_negatives(matrix):
    """PREREGISTERED FAIL CONDITION 5, inverted into a passing test.

    *"If the matrix returns 'everything is universal', the instrument cannot
    discriminate and the milestone has FAILED."* It returns concepts forced
    by no consumer at all, so it discriminates.

    Count was 14 before `MIN-FIELD-SUPPORT-FOUNDATION` added
    ``ScientificProblem.data_references``; ``FieldValuedInput`` moved from
    forced-by-B to served (see ``test_p1_...`` above and
    docs/min-field-support-foundation-evidence.md), joining this list, so the
    count is now 15 — the instrument still discriminates, it discriminates
    correctly for one fewer gap because a real gap was actually closed.
    """
    never_forced = [
        concept
        for concept, row in matrix.items()
        if all(
            row[name].forcing is not inst.Forcing.FORCED
            for name in rec.CONSUMER_COLUMNS
        )
    ]
    assert len(never_forced) == 15
    assert set(never_forced) >= {
        "CausalPort",
        "PhysicalConnector",
        "Event",
        "MaterialState",
        "PropertyRequirement-scalar",
        "DynamicState",
    }


def test_ledger_two_concepts_are_exactly_the_absent_record_ones(matrix):
    """The booking rule, carried verbatim and applied per concept.

    A finding is Ledger 1 only when **both** the measurement and the remedy live
    in a record that exists. These six need a record the platform does not
    have, so they are booked at **zero claimed evidence gain**.
    """
    ledger_two = sorted(
        {
            concept
            for concept, row in matrix.items()
            if any(
                row[name].ledger is inst.Ledger.ABSENT_RECORD for name in ALL_COLUMNS
            )
        }
    )
    assert ledger_two == [
        "BoundaryIdentity",
        "BoundaryOrientation-normal",
        "CausalPort",
        "Composition",
        "Domain/Topology",
        "Event",
        "FieldSupport",
        "MaterialState",
        "PhysicalConnector",
        "RuntimeState",
        "SpatialFieldSemantics",
    ], (
        "the set grew by five once the conflated probes stopped calling an "
        "absent record fully representable"
    )


# =============================================================================
# The steelman — what the contracts DID represent
# =============================================================================

def test_every_consumer_encodes_without_a_single_new_contract(columns):
    """Preregistration §7.1. Four consumers, four problem statements, zero
    contract changes — and every one of them round-trips."""
    for name in rec.CONSUMER_COLUMNS:
        payloads, _ = columns[name]
        problem = ScientificProblem.from_dict(payloads["problem"])
        result = ScientificResult.from_dict(payloads["result"])
        assert problem.problem_id
        assert result.problem_id == problem.problem_id
        assert not [
            check
            for check in result.validation.checks
            if check.outcome is ValidationOutcome.FAIL
            and check.name != "maximum_principle_held"
        ], f"{name}: only an admissibility check may fail here"


def test_an_inadmissible_transport_field_fails_only_a_check_that_earns_nothing():
    """AN UNPLANNED FINDING, and the sharpest single result of the milestone.

    Consumer B's coarse grid produces ``c_min = -0.0136`` — a physically
    inadmissible value of a scalar whose manufactured solution lies in
    ``[0, 1]``. Every other check on that record passes: dimensional
    consistency, and a manufactured-solution error that **establishes
    ANALYTICALLY_VERIFIED**.

    So the record simultaneously claims an attained validation level and
    carries a failed admissibility check that can attain nothing, because
    `ValidationLevel` has no member for it. The refinement to 16 cells restores
    admissibility, which confirms the coarse failure is a discretization
    artifact rather than a modelling error — and the platform cannot say that
    either.
    """
    coarse = rec.build_transport_bundle(tr2.case_b(8))
    fine = rec.build_transport_bundle(tr2.case_b(16))

    def admissibility(bundle):
        return next(
            c for c in bundle.result.validation.checks
            if c.name == "maximum_principle_held"
        )

    assert admissibility(coarse).outcome is ValidationOutcome.FAIL
    assert admissibility(coarse).residual > 0.01
    assert admissibility(fine).outcome is ValidationOutcome.PASS

    # ...and the failing record still claims a level, from a different check.
    levels = {level.value for level in coarse.result.validation.attained_levels}
    assert "analytically_verified" in levels
    assert admissibility(coarse).establishes is None


def test_the_dae_formulation_member_gets_its_first_production_shaped_use():
    """`ModelFormulation.DAE` had zero consumers outside `tests/`.

    MODEL0-R evidence §9 item 7 records it as *"still no consumer, still
    provisional"*. Consumer D is the first record-shaped use — and the
    measurement is that the member is **still not sufficient**: it names the
    mathematical form and cannot say the index, cannot say which unknowns are
    algebraic, and cannot distinguish the unreduced statement from the
    index-reduced one that actually ran.
    """
    cartesian, angular = rec.DYNAMICS_REALIZATIONS
    assert cartesian.formulation is ModelFormulation.DAE
    assert angular.formulation is ModelFormulation.ODE
    assert cartesian.model == angular.model, "same scientific model"
    assert cartesian.realization_id != angular.realization_id


def test_the_multiplier_has_no_honest_variable_role():
    """`lambda` is an algebraic unknown and `VariableRole` has no member for it."""
    problem = rec.build_dynamics_problem(dyn.case_d(10))
    multiplier = problem.variable("lambda")
    assert multiplier.role is VariableRole.OBSERVABLE
    assert {role.value for role in VariableRole} == {
        "design",
        "state",
        "observable",
        "control",
    }
    states = [v for v in problem.variables if v.role is VariableRole.STATE]
    assert len(states) == 4, "four differential unknowns, one algebraic, one role set"


def test_the_constraint_record_is_the_wrong_shape_and_still_validates():
    """`ConstraintDefinition` accepts the encoding and means something else.

    It compares a produced metric against a fixed scalar bound — an acceptance
    test. The pendulum's constraint is a relation among unknowns that must hold
    at every instant and that determines the multiplier. The record cannot tell
    the two apart, which is why this is `AMBIGUOUS` rather than `IMPOSSIBLE`.
    """
    problem = rec.build_dynamics_problem(dyn.case_d(10))
    assert len(problem.constraints) == 1
    constraint = problem.constraints[0]
    assert constraint.metric == "constraint_residual:max"
    assert isinstance(constraint.bound, Quantity)


def test_sixteen_scalars_stand_in_for_two_vector_and_two_tensor_fields():
    """CONSUMER A's encoding, measured rather than described."""
    problem = rec.build_mechanics_problem()
    displacements = [v for v in problem.variables if v.name.startswith("u_")]
    stresses = [v for v in problem.variables if v.name.startswith("sigma_")]
    assert len(displacements) == 8
    assert len(stresses) == 8
    assert len({v.unit for v in displacements}) == 1
    assert len({v.unit for v in stresses}) == 1


def test_three_species_are_three_indistinguishable_same_unit_quantities():
    """CONSUMER C's encoding. The problem is that it encodes *cleanly*."""
    problem = rec.build_species_problem(spc.case_c(10))
    concentrations = [v for v in problem.variables if v.name.startswith("c:")]
    assert len(concentrations) == 3
    assert len({v.unit for v in concentrations}) == 1
    assert "species" in problem.metadata, (
        "species identity survives only as a metadata string"
    )


# =============================================================================
# Architecture fitness — prereg §13 fail conditions, asserted
# =============================================================================

def _diff(path: str) -> str:
    return subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


#: The two files a later, model-discovery-only milestone
#: (`planner-provided-capabilities`) is documented and authorized to touch:
#: adding a `provided_capabilities` field to `ScientificModelDefinition` and
#: a matching `ModelRegistry.providers_of` query method, so a deterministic
#: caller can answer "which models provide capability X" without name
#: parsing or a metadata side-channel. No cross-domain-coverage invariant
#: changed there — see docs/planner-provided-capabilities-evidence.md. This
#: guard's own claim (this milestone left the universal core byte-frozen)
#: is unaffected: it was true when this milestone was written, and that
#: fact does not change.
_PLANNER_DISCOVERY_EXCEPTIONS = {
    "src/engcore/scientific/models/definition.py",
    "src/engcore/scientific/models/registry.py",
}

#: The files a later milestone (`MIN-FIELD-SUPPORT-FOUNDATION`) is
#: documented and authorized to touch: an additive `data_references` field
#: on `ScientificProblem` (schema bumped to /2, reader accepts /1 and /2),
#: a new standalone `BoundaryOrientation`/`classify_sign` module, and
#: extending `VariableBulkLinkage.check_against` to also resolve against
#: `problem.data_references` — see
#: docs/min-field-support-foundation-evidence.md. This guard's own claim
#: (this milestone left the universal core byte-frozen) is unaffected: it
#: was true when this milestone was written, and that fact does not change
#: (indeed this milestone's own `FieldValuedInput` probe is the corroborating
#: instrument, see `test_p1_...` above).
_FIELD_SUPPORT_FOUNDATION_EXCEPTIONS = {
    "src/engcore/scientific/ir/problem.py",
    "src/engcore/scientific/ir/__init__.py",
    "src/engcore/scientific/ir/orientation.py",
    "src/engcore/scientific/results/variable_binding.py",
}


def test_no_universal_core_file_was_added_or_edited():
    """FAIL CONDITION 1."""
    core_changed = (
        set(_diff("src/engcore/scientific/").split())
        - _PLANNER_DISCOVERY_EXCEPTIONS
        - _FIELD_SUPPORT_FOUNDATION_EXCEPTIONS
    )
    assert core_changed == set(), sorted(core_changed)
    current = sorted(
        str(p.relative_to(REPO_ROOT)).replace("\\", "/")
        for p in (REPO_ROOT / "src" / "engcore" / "scientific").rglob("*.py")
    )
    tracked = sorted(
        line
        for line in subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "src/engcore/scientific/"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line.endswith(".py")
    )
    assert current == tracked


#: The one file a later, execution-portability-only milestone
#: (`ngspice-cross-platform-portability`) is documented and authorized to
#: touch: `NgspiceInvocation`'s executable discovery, so the same provider
#: adapter reaches a native Linux `ngspice` as readily as the WSL route this
#: milestone's own machine used. No scientific model, result semantics or
#: validation logic changed there — see
#: docs/ngspice-cross-platform-portability-evidence.md. MIN-CROSS-DOMAIN-
#: FOUNDATION's own claim (this milestone left electrical/ as a byte-frozen
#: control group) is unaffected: it was true when this milestone was
#: written, and that fact does not change.
_PORTABILITY_EXCEPTION = "src/engcore/domains/electrical/ngspice.py"


def test_no_thermal_control_or_prior_probe_file_was_edited():
    """FAIL CONDITIONS 2 and 3.

    The frozen thermal tree, both control-group domains, and the previous
    milestone's probe pack — which is committed evidence for an accepted
    milestone — are all byte-unchanged.
    """
    assert _diff("src/engcore/domains/thermal/") == ""
    assert _diff("src/engcore/domains/thermal_lumped.py") == ""
    electrical_changed = set(
        _diff("src/engcore/domains/electrical/").split()
    ) - {_PORTABILITY_EXCEPTION}
    assert electrical_changed == set(), sorted(electrical_changed)
    assert _diff("experiments/hostile_core_stress/") == ""


def test_the_probe_lives_outside_the_shipped_package():
    """FAIL CONDITION: nothing here can be promoted into core by accident."""
    assert PROBE_ROOT.is_dir()
    assert (REPO_ROOT / "src") not in PROBE_ROOT.parents
    hits = subprocess.run(
        ["git", "grep", "-l", "cross_domain_coverage", "--", "src/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert hits == ""


def test_no_bulk_array_reaches_a_scientific_control_record(columns):
    """Nothing O(mesh) or O(steps) crosses into the control plane.

    Checked over the serialized record, because serialization is where an
    accidental array would actually escape. Consumer D's trajectory alone is
    16 004 numbers.
    """

    def largest_sequence(node) -> int:
        if isinstance(node, list):
            return max([len(node)] + [largest_sequence(c) for c in node])
        if isinstance(node, dict):
            values = [largest_sequence(c) for c in node.values()]
            return max(values) if values else 0
        return 0

    for name in rec.CONSUMER_COLUMNS:
        payloads, _ = columns[name]
        assert largest_sequence(payloads["problem"]) < 40, name
        assert largest_sequence(payloads["result"]) < 40, name


def test_no_domain_vocabulary_leaked_into_executable_universal_core():
    """The lexical half, run because a positive hit would be decisive.

    Scanned over **executable content only** — identifiers, string literals and
    attribute names, with comments and docstrings stripped by AST. That is not a
    convenience: `capabilities.py` legitimately names ``solid.linear_elasticity``
    in a docstring as an example of the identifier *grammar* the core
    understands, which is the opposite of a leak. Scanning prose would flag it
    and scanning code does not.

    Stated as the weak claim it is: `MIN-FOUNDATION-ET` §64.3 already recorded
    that the one real leak found in this repository contained **no domain word**,
    so a negative result here proves little. It is run because a positive one
    would still be decisive.
    """
    core = REPO_ROOT / "src" / "engcore" / "scientific"
    forbidden = (
        "stoichiom",
        "pendulum",
        "elastic",
        "poisson",
        "upwind",
        "cross_domain",
        "baumgarte",
        "species",
    )
    hits: list[tuple[str, str]] = []
    for path in core.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        executable: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Skip docstrings; keep every other string literal.
                executable.append(node.value)
            elif isinstance(node, ast.Name):
                executable.append(node.id)
            elif isinstance(node, ast.Attribute):
                executable.append(node.attr)
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                executable.append(node.name)
        for parent in ast.walk(tree):
            if isinstance(
                parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                doc = ast.get_docstring(parent, clean=False)
                if doc is not None and doc in executable:
                    executable.remove(doc)
        blob = " ".join(executable).lower()
        hits += [
            (str(path.relative_to(REPO_ROOT)), token)
            for token in forbidden
            if token in blob
        ]
    assert hits == []
