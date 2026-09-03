"""CONSUMER A — two-element plane-stress patch. Structural / mechanical.

    eps = B u                B is 3x6, constant per constant-strain triangle
    sigma = D eps            D is the 3x3 plane-stress constitutive matrix
    K = sum_e t A_e B^T D B

Unit square [0,1]^2 m, thickness 0.01 m, split along one diagonal into two
constant-strain triangles. Four nodes, eight degrees of freedom. Linear
isotropic steel: E = 210 GPa, nu = 0.3.

WHY 2D AND NOT A BAR
--------------------
A 1D bar, a spring chain or a pin-jointed truss would be **isomorphic to the
existing `electrical/dc` MNA solve**: stiffness maps to conductance,
displacement to node potential, force to current, and a fixed node to the
reference node. That is exactly the trap that killed the lumped pipe network in
the previous milestone, and it would make this consumer difference against
nothing.

The 2D patch breaks the isomorphism on three counts a records reader can
measure:

* the primary unknown is **rank-1 with two components per node**, where MNA
  carries one scalar per node;
* the derived quantity is a **rank-2 symmetric tensor with three independent
  components**, where MNA derives a scalar branch current;
* the constitutive law is a **matrix**, where MNA's is a scalar conductance.

Those three are the whole reason this consumer exists.

WHAT IS DELIBERATELY NOT BUILT
------------------------------
No shape-function framework, no quadrature abstraction, no element library, no
mesh reader, no refinement study. `07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md` §21
forbids beginning a generic FEM implementation, and the line this probe does not
cross is: one hard-coded 3x6 `B`, one 3x3 `D`, one 8x8 assembly, two elements.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np

# --- units, stated once ------------------------------------------------------
LENGTH_UNIT = "meter"
DISPLACEMENT_UNIT = "meter"
STRESS_UNIT = "pascal"
STRAIN_UNIT = "dimensionless"
FORCE_UNIT = "newton"
STIFFNESS_UNIT = "newton / meter"

#: Linear isotropic steel. Not a material record — a material record is one of
#: the things this milestone is measuring the absence of.
YOUNGS_MODULUS_PA = 210.0e9
POISSON_RATIO = 0.3
THICKNESS_M = 0.01

#: The prescribed axial strain of the patch test.
PATCH_STRAIN = 1.0e-3


class PlaneAssumption(str, Enum):
    """Which 2D reduction of 3D elasticity is asserted.

    Not a discretization and not a solver: it changes the **constitutive law**
    and therefore what `sigma_zz` is. Two problems differing only in this member
    are different physics with an identical mesh, identical loads and identical
    unknowns — which is the reverse of the CD/UW pair the previous milestone
    measured, and is why CASE A3 exists.
    """

    PLANE_STRESS = "plane_stress"
    PLANE_STRAIN = "plane_strain"


class MechanicsProbeError(Exception):
    """A configuration this probe refuses."""


#: Node coordinates, metres. Corners of the unit square, counter-clockwise.
NODES: tuple[tuple[float, float], ...] = (
    (0.0, 0.0),  # 0
    (1.0, 0.0),  # 1
    (1.0, 1.0),  # 2
    (0.0, 1.0),  # 3
)

#: Two triangles sharing the 0-2 diagonal. The shared edge is deliberate: it is
#: where per-node component identity has to be consistent between elements, and
#: a single element would not exercise it.
ELEMENTS: tuple[tuple[int, int, int], ...] = ((0, 1, 2), (0, 2, 3))

N_NODES = len(NODES)
N_DOF = 2 * N_NODES


def constitutive_matrix(
    assumption: PlaneAssumption = PlaneAssumption.PLANE_STRESS,
    *,
    youngs_modulus_pa: float = YOUNGS_MODULUS_PA,
    poisson_ratio: float = POISSON_RATIO,
) -> np.ndarray:
    """The 3x3 matrix ``D`` relating stress to strain in Voigt form.

    **This object is the finding.** It is a scientific property of a material,
    it is dimensional (pascal), and there is no typed home for it anywhere in
    the platform: `ScientificValue` is a closed union of scalars, so a
    `ScientificParameter` cannot carry it. The scalar case is already answered —
    `electrical/material.py` implements a state-dependent scalar `R(T)` and
    argues explicitly why no property hierarchy was needed. A rank-2 property
    is a different question, and this is the object that asks it.
    """
    e, nu = float(youngs_modulus_pa), float(poisson_ratio)
    if not 0.0 <= nu < 0.5:
        raise MechanicsProbeError(
            f"Poisson ratio must lie in [0, 0.5), got {nu}; 0.5 is "
            f"incompressible and singular in both reductions"
        )
    if e <= 0.0:
        raise MechanicsProbeError("Young's modulus must be positive")

    if assumption is PlaneAssumption.PLANE_STRESS:
        factor = e / (1.0 - nu * nu)
        return factor * np.array(
            [[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu) / 2.0]]
        )
    factor = e / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return factor * np.array(
        [
            [1.0 - nu, nu, 0.0],
            [nu, 1.0 - nu, 0.0],
            [0.0, 0.0, (1.0 - 2.0 * nu) / 2.0],
        ]
    )


def out_of_plane_stress(
    sigma: np.ndarray, assumption: PlaneAssumption, *, poisson_ratio: float = POISSON_RATIO
) -> float:
    """``sigma_zz``, which the in-plane Voigt vector cannot hold.

    Zero under plane stress by definition; ``nu (sigma_xx + sigma_yy)`` under
    plane strain. A third number belonging to the same tensor as the three the
    solver returns, produced by a modelling assumption rather than by the mesh —
    and there is nowhere on a `ScientificResult` to say that the three reported
    components and this one are components of **one** tensor.
    """
    if assumption is PlaneAssumption.PLANE_STRESS:
        return 0.0
    return float(poisson_ratio) * float(sigma[0] + sigma[1])


def element_geometry(element: tuple[int, int, int]) -> tuple[float, np.ndarray]:
    """Signed area and the 3x6 strain-displacement matrix ``B`` of one CST."""
    (xi, yi), (xj, yj), (xm, ym) = (NODES[n] for n in element)
    twice_area = (xj - xi) * (ym - yi) - (xm - xi) * (yj - yi)
    area = 0.5 * twice_area
    if area <= 0.0:
        raise MechanicsProbeError(
            f"element {element} has non-positive area {area}; node ordering "
            f"must be counter-clockwise"
        )
    b = np.array([yj - ym, ym - yi, yi - yj])
    c = np.array([xm - xj, xi - xm, xj - xi])
    strain_displacement = np.zeros((3, 6))
    for local in range(3):
        strain_displacement[0, 2 * local] = b[local]
        strain_displacement[1, 2 * local + 1] = c[local]
        strain_displacement[2, 2 * local] = c[local]
        strain_displacement[2, 2 * local + 1] = b[local]
    return area, strain_displacement / twice_area


def global_stiffness(
    assumption: PlaneAssumption = PlaneAssumption.PLANE_STRESS,
    *,
    thickness_m: float = THICKNESS_M,
) -> np.ndarray:
    """Assemble ``K`` over both elements. 8x8, symmetric, singular until fixed."""
    d_matrix = constitutive_matrix(assumption)
    stiffness = np.zeros((N_DOF, N_DOF))
    for element in ELEMENTS:
        area, b_matrix = element_geometry(element)
        k_e = thickness_m * area * (b_matrix.T @ d_matrix @ b_matrix)
        dofs = [2 * n + c for n in element for c in (0, 1)]
        for local_row, row in enumerate(dofs):
            for local_col, col in enumerate(dofs):
                stiffness[row, col] += k_e[local_row, local_col]
    return stiffness


def element_stress(
    displacement: np.ndarray,
    element: tuple[int, int, int],
    assumption: PlaneAssumption = PlaneAssumption.PLANE_STRESS,
) -> tuple[np.ndarray, np.ndarray]:
    """``(strain, stress)`` in Voigt form for one element. Both rank-2, in 2D."""
    _, b_matrix = element_geometry(element)
    dofs = [2 * n + c for n in element for c in (0, 1)]
    strain = b_matrix @ displacement[dofs]
    return strain, constitutive_matrix(assumption) @ strain


# =============================================================================
# CASE A1 — the patch test
# =============================================================================

def patch_test_displacement(
    *, axial_strain: float = PATCH_STRAIN, poisson_ratio: float = POISSON_RATIO
) -> np.ndarray:
    """Nodal displacements of the exact uniaxial plane-stress field.

    ``u = (a x, -nu a y)``. Under plane stress this produces
    ``sigma = (E a, 0, 0)`` exactly, which is what makes the patch test a
    machine-precision identity rather than an approximation: every constant-
    strain triangle reproduces a linear displacement field exactly, so any
    departure is an assembly or constitutive error and nothing else.

    Every node of a two-element patch is a boundary node, so this case
    prescribes all eight degrees of freedom and performs no solve. That is the
    classical form of the test.
    """
    displacement = np.zeros(N_DOF)
    for node, (x, y) in enumerate(NODES):
        displacement[2 * node] = axial_strain * x
        displacement[2 * node + 1] = -poisson_ratio * axial_strain * y
    return displacement


def run_patch_test(
    assumption: PlaneAssumption = PlaneAssumption.PLANE_STRESS,
) -> dict[str, object]:
    """CASE A1. Returns the recovered stress in each element and its error."""
    displacement = patch_test_displacement()
    expected_sigma_xx = YOUNGS_MODULUS_PA * PATCH_STRAIN
    per_element = []
    for element in ELEMENTS:
        strain, stress = element_stress(displacement, element, assumption)
        per_element.append(
            {
                "element": element,
                "strain": tuple(float(v) for v in strain),
                "stress": tuple(float(v) for v in stress),
                "sigma_zz": out_of_plane_stress(stress, assumption),
            }
        )
    errors = [
        abs(entry["stress"][0] - expected_sigma_xx) / expected_sigma_xx
        for entry in per_element
    ]
    transverse = [
        max(abs(entry["stress"][1]), abs(entry["stress"][2]))
        for entry in per_element
    ]
    return {
        "assumption": assumption,
        "displacement": tuple(float(v) for v in displacement),
        "elements": tuple(per_element),
        "expected_sigma_xx_pa": expected_sigma_xx,
        "max_relative_error": max(errors),
        "max_transverse_stress_pa": max(transverse),
    }


# =============================================================================
# CASE A2 — a shear load case with free degrees of freedom
# =============================================================================

#: Left edge fully clamped: both components of nodes 0 and 3.
CLAMPED_DOF: tuple[int, ...] = (0, 1, 6, 7)
#: Applied nodal force, newtons, in +y at the two right-hand nodes.
SHEAR_FORCE_N = 1.0e4


def run_shear_case(
    assumption: PlaneAssumption = PlaneAssumption.PLANE_STRESS,
) -> dict[str, object]:
    """CASE A2. Clamp the left edge, shear the right edge, solve the free DOF.

    Verified without a closed form, by two identities that hold for any correct
    linear-elastic assembly: global equilibrium of applied load against
    reactions, and reciprocity ``K = K^T``. Neither is a tolerance; both are
    machine-precision statements.
    """
    stiffness = global_stiffness(assumption)
    forces = np.zeros(N_DOF)
    forces[2 * 1 + 1] = SHEAR_FORCE_N
    forces[2 * 2 + 1] = SHEAR_FORCE_N

    free = [dof for dof in range(N_DOF) if dof not in CLAMPED_DOF]
    k_ff = stiffness[np.ix_(free, free)]
    displacement = np.zeros(N_DOF)
    displacement[free] = np.linalg.solve(k_ff, forces[free])

    reactions = stiffness @ displacement - forces
    per_element = []
    for element in ELEMENTS:
        strain, stress = element_stress(displacement, element, assumption)
        per_element.append(
            {
                "element": element,
                "strain": tuple(float(v) for v in strain),
                "stress": tuple(float(v) for v in stress),
                "sigma_zz": out_of_plane_stress(stress, assumption),
            }
        )
    return {
        "assumption": assumption,
        "displacement": tuple(float(v) for v in displacement),
        "reactions": tuple(float(v) for v in reactions),
        "elements": tuple(per_element),
        "symmetry_residual": float(np.max(np.abs(stiffness - stiffness.T))),
        "equilibrium_residual_n": float(
            abs(sum(reactions[dof] for dof in CLAMPED_DOF if dof % 2 == 1)
                + 2.0 * SHEAR_FORCE_N)
        ),
        "applied_force_n": 2.0 * SHEAR_FORCE_N,
    }


# =============================================================================
# CASE A3 — representation only: the same everything under plane strain
# =============================================================================

def plane_strain_contrast() -> dict[str, object]:
    """CASE A3. Same geometry, material, mesh and loads; different physics.

    Executes the shear case under both assumptions so the contrast is measured
    rather than asserted. The scientifically important output is ``sigma_zz``,
    which is identically zero under plane stress and non-zero under plane
    strain — a component of the same tensor, produced by a modelling
    assumption, with nowhere on any record to say so.
    """
    stress_case = run_shear_case(PlaneAssumption.PLANE_STRESS)
    strain_case = run_shear_case(PlaneAssumption.PLANE_STRAIN)
    return {
        "plane_stress": stress_case,
        "plane_strain": strain_case,
        "sigma_zz_plane_stress_pa": max(
            abs(e["sigma_zz"]) for e in stress_case["elements"]
        ),
        "sigma_zz_plane_strain_pa": max(
            abs(e["sigma_zz"]) for e in strain_case["elements"]
        ),
        "displacement_ratio": (
            max(abs(v) for v in strain_case["displacement"])
            / max(abs(v) for v in stress_case["displacement"])
        ),
    }


# =============================================================================
# Interpreted scalars
# =============================================================================

def von_mises(stress: tuple[float, ...], sigma_zz: float = 0.0) -> float:
    """Von Mises equivalent stress. A **scalar invariant of a rank-2 tensor**.

    Recorded because it is the honest reduction: it is the number a
    `ScientificResult` can hold, and computing it requires the three in-plane
    components *and* ``sigma_zz`` — that is, it requires knowing they belong to
    one tensor. The reduction is available; the fact that licenses it is not.
    """
    sxx, syy, sxy = stress[0], stress[1], stress[2]
    szz = sigma_zz
    return math.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * sxy**2
    )


def strain_energy(case: dict[str, object]) -> float:
    """Total elastic strain energy, ``sum_e (1/2) t A_e eps^T D eps``, in joules.

    A **positive-definite** quantity: `D` is positive definite for
    ``0 <= nu < 0.5``, so the energy stored by any non-zero strain field is
    strictly positive and a negative total is impossible for a physical body.
    """
    assumption = case["assumption"]
    d_matrix = constitutive_matrix(assumption)
    total = 0.0
    for element, entry in zip(ELEMENTS, case["elements"]):
        area, _ = element_geometry(element)
        strain = np.array(entry["strain"])
        total += 0.5 * THICKNESS_M * area * float(strain @ d_matrix @ strain)
    return total


def strain_energy_violation(case: dict[str, object]) -> float:
    """How far the strain energy falls below zero. Zero is the only admissible
    value of this measure.

    A **fourth kind** of admissibility evidence, deliberately unlike the other
    three: not a range excursion (species, transport) and not a residual of an
    algebraic relation (dynamics), but the sign of a positive-definite
    invariant. Recorded because the previous adversarial pass established that
    a claim of "four structurally unrelated kinds" has to be true of the code
    and not just of the prose.
    """
    return max(0.0, -strain_energy(case))


def case_metrics(case: dict[str, object]) -> dict[str, float]:
    """The scalars a `ScientificResult` can currently hold, per element.

    Note what this function is: the place where two rank-1 nodal fields and two
    rank-2 element tensors are crushed into numbers small enough for the control
    plane. The milestone's question is whether anything downstream can tell that
    this happened.
    """
    metrics: dict[str, float] = {}
    for index, entry in enumerate(case["elements"]):
        stress = entry["stress"]
        metrics[f"sigma_xx:e{index}"] = stress[0]
        metrics[f"sigma_yy:e{index}"] = stress[1]
        metrics[f"sigma_xy:e{index}"] = stress[2]
        metrics[f"sigma_zz:e{index}"] = entry["sigma_zz"]
        metrics[f"von_mises:e{index}"] = von_mises(stress, entry["sigma_zz"])
    displacement = case["displacement"]
    metrics["u_x:max"] = max(abs(displacement[2 * n]) for n in range(N_NODES))
    metrics["u_y:max"] = max(abs(displacement[2 * n + 1]) for n in range(N_NODES))
    return metrics
