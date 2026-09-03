"""Comparison against the committed probes. **Parent process only.**

Everything that reconstructs or computes lives in :mod:`inject`, which imports
no probe. This module imports both probes and does one job: compare what
`inject` produced from records against what the committed consumers produce
from their own module constants.

The split was forced by the adversarial pass. An earlier form did both here,
and because the ground truth in this milestone lives in the probes' module
constants rather than in an `encodings`-held instance, the fresh-process child
was holding the answer while its reported metrics were computed by
`mech.run_shear_case()` and `spc.integrate()` — the probe compared against
itself in two processes. The isolation is now structural: the child imports
`inject`, `inject` imports no probe, and the child reports its own
`experiments.cross_domain_coverage` module list for the parent to assert empty.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from experiments.cross_domain_coverage import mechanics as mech
from experiments.cross_domain_coverage import species as spc

from .inject import (  # re-exported so callers have one import
    CorruptStructure,
    IdentityMismatch,
    MechanicsStructure,
    MissingStructure,
    SpeciesNetwork,
    StructuredReconstructionError,
    UnsupportedStructureSchema,
    assemble_from_records,
    integrate_from_records,
    rebuild_mechanics,
    rebuild_species,
    reconstruct_and_inject,
    solve_from_records,
)

__all__ = [
    "StructuredReconstructionError",
    "MissingStructure",
    "UnsupportedStructureSchema",
    "CorruptStructure",
    "IdentityMismatch",
    "MechanicsStructure",
    "SpeciesNetwork",
    "rebuild_mechanics",
    "rebuild_species",
    "assemble_from_records",
    "solve_from_records",
    "integrate_from_records",
    "reconstruct_and_inject",
    "mechanics_matches_probe",
    "species_matches_probe",
    "probe_baseline",
    "compare_to_probe",
]


def mechanics_matches_probe(structure: MechanicsStructure) -> None:
    """VERIFIED-EQUAL. Raises `IdentityMismatch` on any disagreement.

    A serialization claim: the records round-trip to values equal to the probe's
    constants. It is **not** an executability claim — that is INJ-3's job — and
    the two are reported separately.
    """
    checks: list[tuple[str, Any, Any]] = [
        ("node_coordinates", structure.node_coordinates, mech.NODES),
        ("elements", structure.elements, mech.ELEMENTS),
        ("constrained_dof", structure.constrained_dof, mech.CLAMPED_DOF),
        ("loaded_dof", structure.loaded_dof, (2 * 1 + 1, 2 * 2 + 1)),
        ("youngs_modulus", structure.youngs_modulus_pa, mech.YOUNGS_MODULUS_PA),
        ("poisson_ratio", structure.poisson_ratio, mech.POISSON_RATIO),
        ("thickness", structure.thickness_m, mech.THICKNESS_M),
        ("shear_force", structure.shear_force_n, mech.SHEAR_FORCE_N),
    ]
    for name, rebuilt, original in checks:
        if rebuilt != original:
            raise IdentityMismatch(
                f"col-mech: reconstructed {name} is {rebuilt!r}; the probe "
                f"declares {original!r}"
            )


def species_matches_probe(network: SpeciesNetwork) -> None:
    """VERIFIED-EQUAL against the committed probe's constants."""
    case = spc.case_c()
    checks: list[tuple[str, Any, Any]] = [
        ("species_order", network.species_order, spc.SPECIES),
        ("reaction_order", network.reaction_order, spc.REACTIONS),
        ("stoichiometry", network.stoichiometry, spc.STOICHIOMETRY),
        ("initial", network.initial, case.initial),
        ("k1f", network.k1f_per_s, case.k1f_per_s),
        ("k1r", network.k1r_per_s, case.k1r_per_s),
        ("k2", network.k2_m3_per_mol_s, case.k2_m3_per_mol_s),
        ("end_time", network.end_time_s, case.end_time_s),
        ("n_steps", network.n_steps, case.n_steps),
    ]
    for name, rebuilt, original in checks:
        if rebuilt != original:
            raise IdentityMismatch(
                f"col-species: reconstructed {name} is {rebuilt!r}; the probe "
                f"declares {original!r}"
            )


def probe_baseline(column: str) -> dict[str, float]:
    """What the committed probe computes, from its own module constants."""
    if column == "col-mech":
        case = mech.run_shear_case(mech.PlaneAssumption.PLANE_STRESS)
        return dict(mech.case_metrics(case))
    if column == "col-species":
        state, _trajectory = spc.integrate(spc.case_c())
        return dict(spc.state_metrics(spc.case_c(), state))
    raise StructuredReconstructionError(f"unknown column {column!r}")


def compare_to_probe(report: Mapping[str, Any]) -> dict[str, float]:
    """Largest relative difference per metric, injected against probe."""
    column = str(report["column"])
    baseline = probe_baseline(column)
    produced = report["metrics"]
    if set(produced) != set(baseline):
        raise IdentityMismatch(
            f"{column}: injected metrics {sorted(produced)} do not match the "
            f"probe's {sorted(baseline)}"
        )
    return {
        name: abs(produced[name] - value) / max(1.0, abs(value))
        for name, value in baseline.items()
    }


def probe_stiffness() -> np.ndarray:
    """The probe's own assembly, for the INJ-3 comparison."""
    return mech.global_stiffness(mech.PlaneAssumption.PLANE_STRESS)


def probe_displacement() -> np.ndarray:
    case = mech.run_shear_case(mech.PlaneAssumption.PLANE_STRESS)
    return np.array(case["displacement"])
