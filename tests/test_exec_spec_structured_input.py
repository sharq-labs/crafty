"""EXEC-SPEC-STRUCTURED — the reversal test on two non-scalar sciences.

Preregistration: `docs/exec-spec-structured-input-stress-prereg.md`, committed at
`d744843` before any probe source was written.

The question is not "is there a residue?" — `CROSS-DOMAIN-COVERAGE` answered that
— but whether two unrelated sciences force the **same** expensive-to-reverse
abstraction. Two grades of reconstruction are distinguished throughout, and
reporting the weaker one as the stronger is a preregistered fail condition.
"""

from __future__ import annotations

import ast
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import pytest

from engcore.scientific.errors import ScientificCoreError
from experiments.cross_domain_coverage import mechanics as mech
from experiments.cross_domain_coverage import species as spc
from experiments.exec_spec_residue.instrument import AnswerStatus, PlannerQuestion
from experiments.exec_spec_structured import (
    bridge,
    encodings,
    inject,
    reader,
    residue,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

MECH_TOLERANCE = 1e-9
SPECIES_TOLERANCE = 1e-9


# =====================================================================
# Instrument integrity
# =====================================================================

def test_the_reader_extension_imports_no_domain_and_no_probe():
    """It may know a schema. It may not know the science that wrote it."""
    source = pathlib.Path(reader.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = sorted(
        name
        for name in imported
        if name.startswith("engcore.domains")
        or name.startswith("engcore.systems")
        or "cross_domain_coverage" in name
    )
    assert forbidden == [], f"the reader extension imports {forbidden}"


def test_adding_two_consumers_required_editing_a_reader():
    """P-7, measured as a number rather than argued.

    `EXEC-SPEC` recorded the *domains x consumers* cost of option E as
    unmeasured. This is the measurement: two new consumers required a
    hand-written reader branch each, and the file that holds them is this large.
    """
    extension = pathlib.Path(reader.__file__).read_text(encoding="utf-8")
    assert "MECH_STRUCTURE_SCHEMA" in extension
    assert "SPECIES_STRUCTURE_SCHEMA" in extension
    # The committed EXEC-SPEC reader could not answer either, unextended.
    from experiments.exec_spec_residue import instrument as base

    for column in encodings.COLUMNS:
        payloads = encodings.ENCODINGS[column].to_payloads()
        answer = base.inspect(payloads["problem"], payloads["structure"])[
            PlannerQuestion.STRUCTURE
        ]
        assert answer.status is AnswerStatus.IMPOSSIBLE, column
        assert "does not know" in answer.detail


# =====================================================================
# The executed encoding attempts
# =====================================================================

@pytest.mark.parametrize(
    "column,fact,channel,expected",
    [
        (
            "col-mech",
            "constitutive matrix D (3x3, pascal)",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.REFUSED_BY_TYPE,
        ),
        (
            "col-mech",
            "element connectivity (2 triangles x 3 node indices, ordered)",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.MEANING_IN_KEY,
        ),
        (
            "col-mech",
            "node coordinates (4 nodes x 2 components, metres)",
            encodings.Channel.DATA_REFERENCE,
            encodings.AttemptOutcome.UNLINKED_BULK,
        ),
        (
            "col-mech",
            "constrained degrees of freedom (4 of 8)",
            encodings.Channel.BOUNDARY_CONDITION,
            encodings.AttemptOutcome.MEANING_IN_KEY,
        ),
        (
            "col-species",
            "stoichiometric matrix nu (2 reactions x 3 species)",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.REFUSED_BY_TYPE,
        ),
        (
            "col-species",
            "stoichiometric matrix nu (2 reactions x 3 species)",
            encodings.Channel.DATA_REFERENCE,
            encodings.AttemptOutcome.UNLINKED_BULK,
        ),
        (
            "col-species",
            "initial composition (three scalar concentrations)",
            encodings.Channel.INITIAL_CONDITION,
            encodings.AttemptOutcome.WORKS,
        ),
        (
            "col-species",
            "rate constants (two dimensions)",
            encodings.Channel.PARAMETER,
            encodings.AttemptOutcome.WORKS,
        ),
    ],
)
def test_the_executed_encoding_outcomes(column, fact, channel, expected):
    """One (column, fact, channel) may carry several attempts, deliberately.

    Both matrices were tried twice through `ScientificParameter`: once as a
    single value (refused by the closed scalar union) and once as named
    integers or as a derivation. Asserting uniqueness here would force the
    weaker of the two encodings to be dropped, so the assertion is that the
    recorded outcome is among them.
    """
    matches = [
        a
        for a in encodings.ATTEMPTS
        if a.column == column and a.fact == fact and a.channel is channel
    ]
    assert matches, (column, fact, channel)
    outcomes = {a.outcome for a in matches}
    assert expected in outcomes, [a.detail for a in matches]


def test_the_constitutive_matrix_is_derivable_and_therefore_not_residue():
    """P-1, and it is the mechanics column's central measurement.

    `D` is a 3x3 dimensional matrix with no typed home — and it needs none. For
    an isotropic linear material it is a function of two scalars and one
    category, all representable today. A residue that counted it would be
    counting a computed quantity.
    """
    matches = [
        a
        for a in encodings.ATTEMPTS
        if a.fact == "constitutive matrix D (3x3, pascal)"
        and a.outcome is encodings.AttemptOutcome.DERIVABLE
    ]
    assert len(matches) == 1
    assert "worst element difference 0.000e+00" in matches[0].detail
    assert all(
        item.fact != "constitutive matrix D (3x3, pascal)"
        for item in residue.MECH_RESIDUE
    )


def test_the_stoichiometric_matrix_is_not_derivable_and_therefore_is_residue():
    """P-3. Nothing on any record generates nu."""
    facts = {item.fact for item in residue.SPECIES_RESIDUE}
    assert "stoichiometric matrix nu (2 reactions x 3 species)" in facts


def test_a_reader_without_stoichiometry_reports_a_false_conservation_violation():
    """P-9, executed on the committed probe.

    The weighted invariant is conserved to round-off; the unweighted sum a
    reader without `nu` would form is not. The ratio is the size of the error
    caused by the missing structure.
    """
    case = spc.case_c()
    _final, trajectory = spc.integrate(case)
    weighted = spc.conservation_drift(trajectory)
    naive = spc.naive_drift(trajectory)
    assert weighted < 1e-9
    assert naive > 1.0
    assert naive / max(weighted, 1e-300) > 1e6


# =====================================================================
# Residue tables
# =====================================================================

def test_every_residue_item_carries_all_nine_attributes():
    """FAIL CONDITION §13.3."""
    for item in residue.RESIDUE:
        payload = item.to_dict()
        for key in (
            "classification",
            "shape",
            "scales_with_problem",
            "domain_specific",
            "analogue_in_other_column",
            "changes_scientific_identity",
            "changes_only_discretization",
            "belongs_in_provenance",
            "belongs_under_data_boundary0",
        ):
            assert key in payload, (item.fact, key)
        assert item.note, item.fact


def test_every_residue_item_names_a_failed_attempt():
    for item in residue.RESIDUE:
        assert item.attempts, item.fact
        assert any(
            a.outcome is not encodings.AttemptOutcome.WORKS for a in item.attempts
        ), item.fact


def test_the_two_residue_tables():
    """P-2 and P-3, as exact sets, after the review-required split."""
    assert {item.fact for item in residue.residue_for("col-mech")} == {
        "node coordinates (4 nodes x 2 components, metres)",
        "which body is discretized (the domain the mesh covers)",
        "element connectivity (2 triangles x 3 node indices, ordered)",
        "constrained degrees of freedom (4 of 8)",
        "applied load, and which degrees of freedom receive it",
    }
    assert {item.fact for item in residue.residue_for("col-species")} == {
        "stoichiometric matrix nu (2 reactions x 3 species)",
        "species identities, in state order",
    }


def test_connectivity_carries_body_identity_in_the_representation_measured():
    """The falsifier's counterexample, executed rather than conceded in prose.

    A first correction recorded connectivity as `changes_scientific_identity=
    False` — a mesh refinement leaves the science alone. The adversarial pass
    falsified that from inside this milestone's own executed path: hold the four
    corner coordinates fixed and drop ONE element, and every guard in
    `rebuild_mechanics` passes while what gets assembled is a triangular plate.
    A different body, from a connectivity edit alone.

    So both identity attributes are True, and the model/discretization split is
    a statement about a representation Crafty does not have — it separates only
    once a topology object exists against which a mesh can be checked as one of
    its refinements. This milestone built none.
    """
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    triangular = json.loads(json.dumps(payloads["structure"]))
    triangular["elements"] = [triangular["elements"][0]]  # drop the second CST

    rebuilt = bridge.rebuild_mechanics(payloads["problem"], triangular)
    assert rebuilt.node_coordinates == bridge.rebuild_mechanics(
        payloads["problem"], payloads["structure"]
    ).node_coordinates
    half = bridge.assemble_from_records(rebuilt)
    whole = bridge.assemble_from_records(
        bridge.rebuild_mechanics(payloads["problem"], payloads["structure"])
    )
    assert float(np.abs(half - whole).max()) > 0.0, (
        "dropping an element must change the assembled system"
    )
    # Node 3 is referenced by no element: the body lost a corner, silently.
    assert not half[6:8, :].any()

    connectivity = next(
        item for item in residue.MECH_RESIDUE if item.fact.startswith("element connectivity")
    )
    nu = next(
        item for item in residue.SPECIES_RESIDUE if item.fact.startswith("stoichiometric")
    )
    assert connectivity.changes_scientific_identity is True
    assert connectivity.changes_only_discretization is True
    assert nu.changes_scientific_identity is True
    assert nu.changes_only_discretization is False
    assert "TRIANGULAR PLATE" in connectivity.note


def test_the_body_has_no_carrier_and_the_note_says_so():
    """The fifth residue item is real; its first stated carrier was not."""
    body = next(
        item for item in residue.MECH_RESIDUE if item.fact.startswith("which body")
    )
    assert body.changes_scientific_identity is True
    assert "NO CARRIER EXISTS" in body.note


def test_the_bulk_asymmetry_is_not_claimed_on_dtype():
    """R3. `SUPPORTED_DTYPES` is float64 for BOTH integer tables.

    An earlier note argued nu is excluded from DATA-BOUNDARY0 partly because its
    integer coefficients would be widened. The same is true of the mesh
    connectivity, so that argument does not separate them and the note now says
    so.
    """
    from engcore.scientific.results.data_reference import SUPPORTED_DTYPES

    assert SUPPORTED_DTYPES == frozenset({"float64"})
    nu = next(
        item for item in residue.SPECIES_RESIDUE if item.fact.startswith("stoichiometric")
    )
    assert "does not separate them" in nu.note
    assert not nu.belongs_under_data_boundary0


def test_the_candidate_table_is_labelled_as_carrying_little_weight():
    """R4. A test only the incumbent can pass is confirmation-shaped."""
    source = pathlib.Path(residue.__file__).read_text(encoding="utf-8")
    assert "near-zero evidential weight" in source
    assert "confirmation-shaped" in source


# =====================================================================
# The universality test
# =====================================================================

def test_the_shape_only_candidates_are_rejected_as_false_universality():
    """FAIL CONDITION §13.2. Two matrices are not one abstraction."""
    verdicts = {c.candidate: c for c in residue.CANDIDATES}
    for candidate in (
        residue.Candidate.STRUCTURED_SCIENTIFIC_VALUE,
        residue.Candidate.RELATION_COEFFICIENT_ARTIFACT,
    ):
        assert verdicts[candidate].survives is False
        assert verdicts[candidate].planner_can_act is False


def test_exactly_one_candidate_survives_and_it_is_the_existing_decision():
    survivors = [c.candidate for c in residue.CANDIDATES if c.survives]
    assert survivors == [residue.Candidate.DOMAIN_OWNED_WITH_SHARED_INFRASTRUCTURE]


def test_the_overlap_verdict_is_mixed_not_a_shared_universal_shape():
    """P-4. Outcome D, and the shared part is not a matrix record."""
    result = residue.overlap()
    assert result.verdict is residue.OverlapVerdict.MIXED
    assert len(result.shared_semantic) == 1
    assert "VariableToBulkLinkage" in result.shared_semantic[0]
    assert len(result.not_shared) >= 4


# =====================================================================
# Reconstruction — in process
# =====================================================================

def test_mechanics_reconstruction_is_verified_equal_against_the_probe():
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = bridge.rebuild_mechanics(payloads["problem"], payloads["structure"])
    bridge.mechanics_matches_probe(structure)
    assert structure.node_coordinates == mech.NODES
    assert structure.elements == mech.ELEMENTS
    assert structure.constrained_dof == mech.CLAMPED_DOF


def test_inj_1_the_constitutive_matrix_is_injected_and_exact():
    """INJ-1. Recomputed from reconstructed scalars, compared to the probe's D."""
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = bridge.rebuild_mechanics(payloads["problem"], payloads["structure"])
    probe = mech.constitutive_matrix(mech.PlaneAssumption.PLANE_STRESS)
    assert float(np.abs(structure.constitutive_matrix - probe).max()) == 0.0


def test_inj_3_the_stiffness_is_assembled_from_the_reconstructed_mesh():
    """INJ-3 — a DECLARED DEVIATION, added after the adversarial review.

    The preregistration accepted VERIFIED-EQUAL for mechanics on the ground that
    the probe reads its geometry from module scope. The review observed that the
    species probe has the identical constraint and was injected anyway, so the
    stated reason did not force the weaker grade — the choice not to write an
    assembler did. This writes it, bounded exactly as INJ-2: two constant-strain
    triangles, one element type, no framework.
    """
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = bridge.rebuild_mechanics(payloads["problem"], payloads["structure"])
    assembled = bridge.assemble_from_records(structure)
    probe = mech.global_stiffness(mech.PlaneAssumption.PLANE_STRESS)
    scale = float(np.abs(probe).max())
    assert float(np.abs(assembled - probe).max()) <= 1e-9 * scale

    displacement = bridge.solve_from_records(structure)
    case = mech.run_shear_case(mech.PlaneAssumption.PLANE_STRESS)
    probe_displacement = np.array(case["displacement"])
    magnitude = float(np.abs(probe_displacement).max())
    assert float(np.abs(displacement - probe_displacement).max()) <= 1e-9 * magnitude


def test_inj_3_refuses_an_inverted_element_ordering():
    """Vertex order is load-bearing, and the assembler proves it rather than
    asserting it: reversing a triangle's winding makes the signed area negative
    and is refused."""
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["elements"][0] = list(reversed(structure["elements"][0]))
    rebuilt = bridge.rebuild_mechanics(payloads["problem"], structure)
    with pytest.raises(bridge.CorruptStructure):
        bridge.assemble_from_records(rebuilt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("coordinate_unit", "millimeter"),
        ("element_kind", "quadrilateral"),
        ("dof_index_rule", "node + component*n_nodes"),
    ],
)
def test_the_mechanics_convention_fields_are_enforced_not_echoed(field, value):
    """R7. The defect EXEC-SPEC was falsified on, not repeated.

    Each of these was written into the payload and read by nothing, so a payload
    declaring a different convention reconstructed identically and meant
    different physics. They are now refused.
    """
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure[field] = value
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_mechanics(payloads["problem"], structure)


def test_species_reconstruction_is_verified_equal_against_the_probe():
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    network = bridge.rebuild_species(
        payloads["problem"], payloads["structure"], payloads["numerics"]
    )
    bridge.species_matches_probe(network)
    assert network.stoichiometry == spc.STOICHIOMETRY
    assert network.species_order == spc.SPECIES


def test_inj_2_the_stoichiometry_is_injected_and_reproduces_the_trajectory():
    """INJ-2. The record carries the stoichiometric MEANING, not six numbers.

    Integrated from the reconstructed coefficients alone, with the probe's own
    RK4 scheme, and compared against the probe's final state.
    """
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    network = bridge.rebuild_species(
        payloads["problem"], payloads["structure"], payloads["numerics"]
    )
    injected, drift = bridge.integrate_from_records(network)
    probe_state, _trajectory = spc.integrate(spc.case_c())
    for reconstructed, original in zip(injected, probe_state):
        assert abs(reconstructed - original) <= SPECIES_TOLERANCE * max(
            1.0, abs(original)
        )
    assert drift < 1e-9


def test_the_conserved_weights_are_recovered_from_the_reconstructed_matrix():
    """The sharpest single result: (1, 1, 2) from nu, with no reference to it.

    `species.CONSERVED_WEIGHTS` is never read. The weights come out of the null
    space of the reconstructed coefficients, which is what "the record carries
    the meaning" has to mean.
    """
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    network = bridge.rebuild_species(
        payloads["problem"], payloads["structure"], payloads["numerics"]
    )
    weights = network.conserved_weights
    for recovered, expected in zip(weights, spc.CONSERVED_WEIGHTS):
        assert abs(recovered - expected) < 1e-9


# =====================================================================
# Negative tests
# =====================================================================

def test_d_corrupted_structure_is_rejected():
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["elements"][0][2] = 99  # a node that does not exist
    with pytest.raises(bridge.CorruptStructure):
        bridge.rebuild_mechanics(payloads["problem"], structure)


def test_d2_a_ragged_coefficient_table_is_rejected():
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["stoichiometry"][0] = [-1, 1]  # two entries, three species
    with pytest.raises(bridge.CorruptStructure):
        bridge.rebuild_species(payloads["problem"], structure, payloads["numerics"])


def test_e_unsupported_schema_is_rejected():
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["schema"] = "exec_spec_species_structure/99"
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_species(payloads["problem"], structure, payloads["numerics"])


def test_the_axis_order_of_a_coefficient_table_is_not_inferable():
    """Transposing the axes is refused rather than guessed.

    Nothing in the numbers says which axis is reactions and which is species. A
    reader that guessed would silently integrate a different chemistry.
    """
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    structure = json.loads(json.dumps(payloads["structure"]))
    structure["stoichiometry_axes"] = ["species", "reaction"]
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_species(payloads["problem"], structure, payloads["numerics"])


def test_missing_structure_is_a_typed_failure_for_both_columns():
    for column, rebuild in (
        ("col-mech", bridge.rebuild_mechanics),
        ("col-species", bridge.rebuild_species),
    ):
        payloads = encodings.ENCODINGS[column].to_payloads()
        with pytest.raises(bridge.MissingStructure):
            rebuild(payloads["problem"], None)


def test_structure_for_the_wrong_column_does_not_silently_bind():
    mechanics = encodings.ENCODINGS["col-mech"].to_payloads()
    species = encodings.ENCODINGS["col-species"].to_payloads()
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_mechanics(mechanics["problem"], species["structure"])
    with pytest.raises(bridge.UnsupportedStructureSchema):
        bridge.rebuild_species(
            species["problem"], mechanics["structure"], species["numerics"]
        )


def test_reconstruction_failure_is_not_a_scientific_verdict():
    assert not issubclass(bridge.StructuredReconstructionError, ScientificCoreError)


def test_a_missing_initial_condition_stops_the_species_column():
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    problem = json.loads(json.dumps(payloads["problem"]))
    problem["initial_conditions"] = problem["initial_conditions"][:1]
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_species(problem, payloads["structure"], payloads["numerics"])


# =====================================================================
# Fresh process
# =====================================================================

def _write(directory: pathlib.Path, column: str) -> pathlib.Path:
    directory.mkdir(parents=True, exist_ok=True)
    payloads = encodings.ENCODINGS[column].to_payloads()
    for name in ("problem", "structure", "numerics"):
        if name in payloads:
            (directory / f"{name}.json").write_text(
                json.dumps(payloads[name], sort_keys=True, indent=2), encoding="utf-8"
            )
    return directory


def _run_child(directory: pathlib.Path, column: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), str(REPO_ROOT), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "experiments.exec_spec_structured.child",
            str(directory),
            column,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, f"child failed: {proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_the_fresh_process_never_loads_the_probes():
    """The guard the adversarial pass found pointed at the wrong module.

    In this milestone the ground truth is the committed probes' module
    constants, not an `encodings`-held instance. A guard filtering only for
    `encodings` could not see the child importing `mechanics` and `species`
    through `bridge` — so the child held the answer. Asserted here at the import
    level, before any subprocess runs.
    """
    source = pathlib.Path(inject.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = sorted(
        name
        for name in imported
        if "cross_domain_coverage" in name or name.endswith("encodings")
    )
    assert forbidden == [], f"the injection module imports {forbidden}"


def test_a_mechanics_fresh_process_reconstruction(tmp_path):
    """TEST A. Separate interpreter, records only, probes absent from it.

    Every reported metric is computed in that process from the records: the
    stiffness is assembled, the system solved, and the element stresses
    recovered without any probe on the import path.
    """
    directory = _write(tmp_path / "mech", "col-mech")
    reported = _run_child(directory, "col-mech")
    assert reported["probe_modules_loaded"] == []
    assert reported["encoding_modules_loaded"] == []
    assert reported["reconstruction_grade"] == "injected"

    baseline = bridge.probe_baseline("col-mech")
    assert set(reported["metrics"]) == set(baseline)
    for name, value in baseline.items():
        scale = max(1.0, abs(value))
        assert abs(reported["metrics"][name] - value) <= MECH_TOLERANCE * scale, name

    probe_displacement = bridge.probe_displacement()
    for reconstructed, original in zip(reported["displacement"], probe_displacement):
        assert abs(reconstructed - original) <= MECH_TOLERANCE * max(
            1.0, abs(original)
        )


def test_b_species_fresh_process_reconstruction(tmp_path):
    """TEST B. The trajectory and the invariant, computed from records only."""
    directory = _write(tmp_path / "species", "col-species")
    reported = _run_child(directory, "col-species")
    assert reported["probe_modules_loaded"] == []
    assert reported["encoding_modules_loaded"] == []
    assert reported["recovered_weights"] == pytest.approx(
        list(spc.CONSERVED_WEIGHTS), abs=1e-9
    )
    assert reported["conservation_drift"] < 1e-9

    probe_state, _trajectory = spc.integrate(spc.case_c())
    for reconstructed, original in zip(reported["state"], probe_state):
        assert abs(reconstructed - original) <= SPECIES_TOLERANCE * max(
            1.0, abs(original)
        )


def test_c_results_agree_with_the_committed_probe_baselines(tmp_path):
    """TEST C. The comparison happens HERE, in the parent, which holds both.

    The child computes from records and never sees a probe; this process
    compares what it produced against what the committed consumers produce.
    """
    for column in encodings.COLUMNS:
        directory = _write(tmp_path / f"baseline-{column}", column)
        reported = _run_child(directory, column)
        assert reported["column"] == column
        differences = bridge.compare_to_probe(reported)
        assert max(differences.values()) <= 1e-9, (column, differences)


# =====================================================================
# Relocation
# =====================================================================

def test_f_relocation_does_not_change_scientific_identity(tmp_path):
    """TEST F. Digest over the SCIENTIFIC STRUCTURE only, computed both places.

    The metrics half of this test is no longer vacuous: after the isolation fix
    the child computes them from the records, so comparing two locations
    compares two reconstructions rather than the probe against itself.
    """
    import hashlib

    def digest(directory: pathlib.Path) -> str:
        blob = json.dumps(
            json.loads((directory / "structure.json").read_text(encoding="utf-8")),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    for column in encodings.COLUMNS:
        first = _write(tmp_path / "site-a" / column, column)
        second = tmp_path / "site-b" / "elsewhere" / column
        second.mkdir(parents=True)
        for path in first.iterdir():
            (second / path.name).write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        assert digest(first) == digest(second), column
        assert _run_child(first, column)["metrics"] == _run_child(second, column)["metrics"]

        blob = json.dumps(encodings.ENCODINGS[column].to_payloads(), sort_keys=True)
        for fragment in (str(tmp_path), "site-a", "site-b", "C:\\", "/home/"):
            assert fragment not in blob


def test_the_identity_digest_does_not_cover_a_solver_choice():
    """F11. Two step counts, one chemistry, one scientific identity.

    An earlier form carried `n_steps` and the integrator name inside the
    digested structure payload, so two payloads differing only in step count had
    different scientific identities — collapsing a distinction the
    preregistration declared binding.
    """
    import hashlib

    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    assert "n_steps" not in payloads["structure"]
    assert "integrator" not in payloads["structure"]
    assert payloads["numerics"]["n_steps"] == spc.case_c().n_steps

    def digest(payload) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    coarser = json.loads(json.dumps(payloads["numerics"]))
    coarser["n_steps"] = 4000
    assert digest(payloads["structure"]) == digest(payloads["structure"])
    assert digest(coarser) != digest(payloads["numerics"])


def test_the_numerics_payload_is_required_and_typed():
    """It has no persistable home in core, so its absence must be a refusal."""
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    with pytest.raises(bridge.MissingStructure):
        bridge.rebuild_species(payloads["problem"], payloads["structure"], None)


# =====================================================================
# Planner inspectability — TEST G
# =====================================================================

def test_g_the_reader_answers_the_mechanics_questions_where_claimed():
    payloads = encodings.ENCODINGS["col-mech"].to_payloads()
    answers = reader.domain_questions(
        "col-mech", payloads["problem"], payloads["structure"]
    )
    assert set(answers) == set(reader.MECHANICS_QUESTIONS)
    connected = answers["which entities are connected?"]
    assert connected.status is AnswerStatus.RECOVERABLE
    assert connected.value["edges"] == [
        {"element": 0, "nodes": [0, 1, 2]},
        {"element": 1, "nodes": [0, 2, 3]},
    ]
    # And the one it CANNOT answer cleanly is recorded as ambiguous, not passed.
    unknowns = answers["which variable components are unknown?"]
    assert unknowns.status is AnswerStatus.AMBIGUOUS
    assert "spelling" in unknowns.detail


def test_g2_the_reader_answers_the_species_questions_where_claimed():
    payloads = encodings.ENCODINGS["col-species"].to_payloads()
    answers = reader.domain_questions(
        "col-species", payloads["problem"], payloads["structure"]
    )
    assert set(answers) == set(reader.SPECIES_QUESTIONS)
    assert answers["which species exist?"].value == ["A", "B", "C"]
    assert answers["what stoichiometric relationship exists?"].value["coefficients"] == [
        [-1, 1, 0],
        [0, -2, 1],
    ]


def test_g3_neither_column_can_answer_structure_without_its_payload():
    for column in encodings.COLUMNS:
        problem = encodings.ENCODINGS[column].problem.to_dict()
        answers = reader.inspect(problem, None)
        assert answers[PlannerQuestion.STRUCTURE].status is AnswerStatus.IMPOSSIBLE


# =====================================================================
# Architecture fitness — TEST H
# =====================================================================

#: The one file a later, execution-portability-only milestone
#: (`ngspice-cross-platform-portability`) is documented and authorized to
#: touch: `NgspiceInvocation`'s executable discovery, so the same provider
#: adapter reaches a native Linux `ngspice` as readily as the WSL route this
#: milestone's own machine used. No scientific model, result semantics or
#: validation logic changed there — see
#: docs/ngspice-cross-platform-portability-evidence.md. This guard's own
#: claim (this milestone touches nothing under `src/`) is unaffected: it was
#: true when this milestone was written, and that fact does not change.
_PORTABILITY_EXCEPTION = "src/engcore/domains/electrical/ngspice.py"

#: The two files a later, model-discovery-only milestone
#: (`planner-provided-capabilities`) is documented and authorized to touch:
#: adding a `provided_capabilities` field to `ScientificModelDefinition` and
#: a matching `ModelRegistry.providers_of` query method, so a deterministic
#: caller can answer "which models provide capability X" without name
#: parsing or a metadata side-channel. No exec-spec structured-input
#: behaviour changed there — see
#: docs/planner-provided-capabilities-evidence.md. This guard's own claim
#: (this milestone touches nothing under `src/`) is unaffected: it was true
#: when this milestone was written, and that fact does not change.
_PLANNER_DISCOVERY_EXCEPTIONS = {
    "src/engcore/scientific/models/definition.py",
    "src/engcore/scientific/models/registry.py",
}


def test_h_no_universal_core_or_committed_evidence_was_modified():
    """FAIL CONDITION §13.7."""
    for path in ("src/", "experiments/cross_domain_coverage/", "experiments/exec_spec_residue/"):
        diff = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--", path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        changed = (
            set(diff.stdout.split())
            - {_PORTABILITY_EXCEPTION}
            - _PLANNER_DISCOVERY_EXCEPTIONS
        )
        assert changed == set(), f"{path} was modified: {sorted(changed)}"
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "src/"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    assert untracked.stdout.strip() == ""


def test_no_scientific_problem_schema_moved():
    for encoding in encodings.ENCODINGS.values():
        assert encoding.problem.to_dict()["schema"] == "scientific_problem/1"


def test_no_metadata_was_used_to_carry_science():
    for column, encoding in encodings.ENCODINGS.items():
        assert encoding.problem.metadata == {}, column


def test_a_persisted_problem_is_data_and_only_data():
    for column, encoding in encodings.ENCODINGS.items():
        blob = json.dumps(encoding.to_payloads(), sort_keys=True)
        for forbidden in ("__", "import ", "lambda", "eval(", "exec(", "subprocess"):
            assert forbidden not in blob, f"{column} carries {forbidden!r}"
