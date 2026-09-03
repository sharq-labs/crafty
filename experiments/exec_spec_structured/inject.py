"""Reconstruction and injection, with **no probe import anywhere**.

This module exists because the adversarial pass found a real regression against
`EXEC-SPEC`. There, the originals lived in a `cases` module and the bridge
reached its schema constants through `schemas`, so a fresh process genuinely
never held the ground truth. Here the originals are the *committed probes'*
module constants — `mech.NODES`, `spc.STOICHIOMETRY`, `spc.CONSERVED_WEIGHTS` —
and the bridge imported both probes at module level. The inherited guard
filtered for `encodings` and could not see it, so the child was holding the
answer while its `metrics` were computed from the probes rather than from the
records.

The split is the fix, and it is structural rather than promised:

``inject``   reconstruct from records and COMPUTE. Imports numpy,
             `engcore.scientific` and `.schemas`. **No probe, no `encodings`.**
``bridge``   compare what `inject` produced against the committed probes.
             Imports the probes, and is used by the parent process only.

The fresh-process child imports `inject` and nothing else, and reports the
`experiments.cross_domain_coverage` entries of its own `sys.modules` so the
parent can assert the list is empty.

One consequence is worth stating rather than hiding: the plane-stress and
plane-strain constitutive formulas are written out here, six lines, because
reaching `mechanics.constitutive_matrix` would import the probe. That
duplication is the price of the isolation being real, and it strengthens the
derivability claim rather than weakening it — the child computes D from two
scalars and a category with the probe nowhere in the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.units.quantity import Quantity

from .schemas import (
    MECH_STRUCTURE_SCHEMA,
    SPECIES_NUMERICS_SCHEMA,
    SPECIES_STRUCTURE_SCHEMA,
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
]

#: The DOF convention this reconstruction reads. Enforced, not echoed.
DOF_INDEX_RULE = "2*node + component, component 0=x 1=y"
ELEMENT_KIND = "constant_strain_triangle"
COORDINATE_UNIT = "meter"


class StructuredReconstructionError(Exception):
    """Reconstruction refused. Deliberately not a `ScientificCoreError`: failing
    to rebuild a problem is not a statement about nature."""


class MissingStructure(StructuredReconstructionError):
    """The records do not include the structure this consumer needs."""


class UnsupportedStructureSchema(StructuredReconstructionError):
    """The payload declares a schema or convention this does not accept."""


class CorruptStructure(StructuredReconstructionError):
    """Present, well-labelled, and not loadable as what it claims to be."""


class IdentityMismatch(StructuredReconstructionError):
    """The problem and the structure describe different physical systems."""


def _require(structure: Mapping[str, Any] | None, expected: str, column: str):
    if structure is None:
        raise MissingStructure(
            f"{column}: no structural payload was supplied, and the problem "
            f"record cannot carry what this consumer needs"
        )
    declared = structure.get("schema")
    if declared != expected:
        raise UnsupportedStructureSchema(
            f"{column}: payload declares schema {declared!r}; this "
            f"reconstruction accepts exactly {expected!r}"
        )
    return structure


def _parameter(problem: ScientificProblem, name: str) -> Quantity:
    try:
        value = problem.parameter(name).value
    except Exception as exc:  # noqa: BLE001 - absence is the finding
        raise MissingStructure(f"no parameter {name!r}: {exc}") from None
    if not isinstance(value, Quantity):
        raise IdentityMismatch(f"parameter {name!r} is not a Quantity")
    return value


# =====================================================================
# col-mech
# =====================================================================

@dataclass(frozen=True)
class MechanicsStructure:
    node_coordinates: tuple[tuple[float, ...], ...]
    elements: tuple[tuple[int, ...], ...]
    constrained_dof: tuple[int, ...]
    loaded_dof: tuple[int, ...]
    dof_per_node: int
    youngs_modulus_pa: float
    poisson_ratio: float
    thickness_m: float
    shear_force_n: float
    assumption: str

    @property
    def constitutive_matrix(self) -> np.ndarray:
        """D, computed from the reconstructed scalars with no probe present.

        Written out here rather than delegated, so that this module imports no
        probe. Two `Quantity` parameters and one `CategoricalValue` generate the
        whole 3x3 matrix — which is the mechanics column's central measurement.
        """
        e, nu = self.youngs_modulus_pa, self.poisson_ratio
        if self.assumption == "plane_stress":
            factor = e / (1.0 - nu * nu)
            return factor * np.array(
                [[1.0, nu, 0.0], [nu, 1.0, 0.0], [0.0, 0.0, (1.0 - nu) / 2.0]]
            )
        if self.assumption == "plane_strain":
            factor = e / ((1.0 + nu) * (1.0 - 2.0 * nu))
            return factor * np.array(
                [
                    [1.0 - nu, nu, 0.0],
                    [nu, 1.0 - nu, 0.0],
                    [0.0, 0.0, (1.0 - 2.0 * nu) / 2.0],
                ]
            )
        raise IdentityMismatch(f"unknown plane assumption {self.assumption!r}")


def rebuild_mechanics(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
) -> MechanicsStructure:
    problem = ScientificProblem.from_dict(problem_payload)
    structure = _require(structure_payload, MECH_STRUCTURE_SCHEMA, "col-mech")

    # Convention fields are ENFORCED, not echoed — the D-5 defect `EXEC-SPEC`
    # was falsified on, and §66.4's lesson that a field nothing consults is not
    # a guard.
    if str(structure.get("coordinate_unit")) != COORDINATE_UNIT:
        raise UnsupportedStructureSchema(
            f"col-mech: coordinates are declared in "
            f"{structure.get('coordinate_unit')!r}; this reconstruction reads "
            f"metres and does not convert. A silent unit assumption on geometry "
            f"is how a mesh becomes a different body"
        )
    if str(structure.get("element_kind")) != ELEMENT_KIND:
        raise UnsupportedStructureSchema(
            f"col-mech: element kind {structure.get('element_kind')!r} is not "
            f"the constant-strain triangle this probe implements; the same node "
            f"tuple means different shape functions under a different element"
        )
    if str(structure.get("dof_index_rule")) != DOF_INDEX_RULE:
        raise UnsupportedStructureSchema(
            f"col-mech: degree-of-freedom rule "
            f"{structure.get('dof_index_rule')!r} is not the one this "
            f"reconstruction reads. The constrained and loaded indices mean "
            f"nothing without it, and guessing would clamp different nodes"
        )

    try:
        coordinates = tuple(
            tuple(float(c) for c in node) for node in structure["node_coordinates"]
        )
        elements = tuple(
            tuple(int(n) for n in element) for element in structure["elements"]
        )
        constrained = tuple(int(d) for d in structure["constrained_dof"])
        loaded = tuple(int(d) for d in structure["loaded_dof"])
        dof_per_node = int(structure["dof_per_node"])
    except StructuredReconstructionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CorruptStructure(f"col-mech: {type(exc).__name__}: {exc}") from None

    if not coordinates or not elements:
        raise CorruptStructure("col-mech: an empty mesh describes no system")
    n_nodes = len(coordinates)
    for element in elements:
        for node in element:
            if not 0 <= node < n_nodes:
                raise CorruptStructure(
                    f"col-mech: element references node {node}, outside "
                    f"0..{n_nodes - 1}"
                )
    for dof in (*constrained, *loaded):
        if not 0 <= dof < dof_per_node * n_nodes:
            raise CorruptStructure(
                f"col-mech: degree of freedom {dof} is outside the mesh"
            )

    assumption = str(problem.parameter("plane_assumption").context_value())
    return MechanicsStructure(
        node_coordinates=coordinates,
        elements=elements,
        constrained_dof=constrained,
        loaded_dof=loaded,
        dof_per_node=dof_per_node,
        youngs_modulus_pa=_parameter(problem, "youngs_modulus").magnitude_in("pascal"),
        poisson_ratio=_parameter(problem, "poisson_ratio").magnitude_in(
            "dimensionless"
        ),
        thickness_m=_parameter(problem, "thickness").magnitude_in("meter"),
        shear_force_n=_parameter(problem, "shear_force").magnitude_in("newton"),
        assumption=assumption,
    )


def assemble_from_records(structure: MechanicsStructure) -> np.ndarray:
    """INJ-3: assemble K from the reconstructed mesh alone.

    **Not preregistered — a declared deviation against §7 and §13.5.** The
    preregistration stated that baseline fact B3 *forces* VERIFIED-EQUAL for the
    mechanics geometry and that reporting it as INJECTED is a fail condition.
    The adversarial pass showed the inference had no basis: `species.derivative`
    reads its stoichiometry from module scope in exactly the same way and was
    injected anyway. B3 constrains the *probe*, not the milestone. This raises
    the bar the preregistration set rather than lowering it, and the withdrawal
    of B3's inference is recorded in the evidence document.

    Bounded exactly as INJ-2: two constant-strain triangles, one element type,
    no shape-function framework, no quadrature abstraction, no element library.

    What it establishes is **executability from records**, plus one measurement:
    the `twice_area <= 0` refusal makes vertex order load-bearing as a fact
    rather than an assertion. What it does **not** establish is corroboration by
    agreement — this is an operation-for-operation transcription of the probe's
    assembly, so given equal inputs the difference is entailed to be zero.
    """
    nodes = structure.node_coordinates
    n_dof = structure.dof_per_node * len(nodes)
    d_matrix = structure.constitutive_matrix
    stiffness = np.zeros((n_dof, n_dof))
    for element in structure.elements:
        (x1, y1), (x2, y2), (x3, y3) = (nodes[i] for i in element)
        twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        if twice_area <= 0.0:
            raise CorruptStructure(
                f"col-mech: element {element} has non-positive signed area "
                f"{twice_area}; vertex ORDER is load-bearing and this ordering "
                f"describes an inverted element"
            )
        area = 0.5 * twice_area
        b_matrix = (
            np.array(
                [
                    [y2 - y3, 0.0, y3 - y1, 0.0, y1 - y2, 0.0],
                    [0.0, x3 - x2, 0.0, x1 - x3, 0.0, x2 - x1],
                    [x3 - x2, y2 - y3, x1 - x3, y3 - y1, x2 - x1, y1 - y2],
                ]
            )
            / twice_area
        )
        element_k = structure.thickness_m * area * (b_matrix.T @ d_matrix @ b_matrix)
        dofs = [
            structure.dof_per_node * node + component
            for node in element
            for component in range(structure.dof_per_node)
        ]
        for local_row, row in enumerate(dofs):
            for local_column, column in enumerate(dofs):
                stiffness[row, column] += element_k[local_row, local_column]
    return stiffness


def solve_from_records(structure: MechanicsStructure) -> np.ndarray:
    """INJ-3, continued: the shear solve, from records only."""
    stiffness = assemble_from_records(structure)
    n_dof = stiffness.shape[0]
    forces = np.zeros(n_dof)
    for dof in structure.loaded_dof:
        forces[dof] = structure.shear_force_n
    constrained = set(structure.constrained_dof)
    free = [dof for dof in range(n_dof) if dof not in constrained]
    displacement = np.zeros(n_dof)
    displacement[free] = np.linalg.solve(
        stiffness[np.ix_(free, free)], forces[free]
    )
    return displacement


def element_stress_from_records(
    structure: MechanicsStructure, displacement: np.ndarray
) -> list[dict[str, Any]]:
    """Per-element strain and stress, from records only. Part of INJ-3."""
    nodes = structure.node_coordinates
    d_matrix = structure.constitutive_matrix
    nu = structure.poisson_ratio
    results: list[dict[str, Any]] = []
    for element in structure.elements:
        (x1, y1), (x2, y2), (x3, y3) = (nodes[i] for i in element)
        twice_area = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
        b_matrix = (
            np.array(
                [
                    [y2 - y3, 0.0, y3 - y1, 0.0, y1 - y2, 0.0],
                    [0.0, x3 - x2, 0.0, x1 - x3, 0.0, x2 - x1],
                    [x3 - x2, y2 - y3, x1 - x3, y3 - y1, x2 - x1, y1 - y2],
                ]
            )
            / twice_area
        )
        dofs = [
            structure.dof_per_node * node + component
            for node in element
            for component in range(structure.dof_per_node)
        ]
        strain = b_matrix @ displacement[dofs]
        stress = d_matrix @ strain
        sigma_zz = (
            0.0
            if structure.assumption == "plane_stress"
            else nu * (stress[0] + stress[1])
        )
        results.append(
            {
                "element": list(element),
                "strain": [float(v) for v in strain],
                "stress": [float(v) for v in stress],
                "sigma_zz": float(sigma_zz),
            }
        )
    return results


# =====================================================================
# col-species
# =====================================================================

@dataclass(frozen=True)
class SpeciesNetwork:
    species_order: tuple[str, ...]
    reaction_order: tuple[str, ...]
    stoichiometry: tuple[tuple[int, ...], ...]
    initial: tuple[float, ...]
    k1f_per_s: float
    k1r_per_s: float
    k2_m3_per_mol_s: float
    end_time_s: float
    n_steps: int

    @property
    def conserved_weights(self) -> tuple[float, ...]:
        """Weights derived from the reconstructed stoichiometry's null space.

        Left null vector of ``nu``: ``nu . w = 0``, so ``w . c`` is invariant.
        Recovering `(1, 1, 2)` here — from records, with the probe absent from
        the process — is the measurement that the record carries the
        stoichiometric MEANING and not merely six numbers.

        **Scope, recorded rather than implied.** This refuses anything but a
        one-dimensional conserved space, and where the space is larger the SVD
        returns an arbitrary orthonormal basis rather than the chemically
        meaningful non-negative integer moiety vectors. The exact claim the
        measurement supports is *"nu determines the conserved subspace"*, not
        *"nu yields the weights"*.
        """
        matrix = np.array(self.stoichiometry, dtype=float)
        _u, singular, vh = np.linalg.svd(matrix)
        tolerance = max(matrix.shape) * (singular[0] if singular.size else 0.0) * 1e-12
        null_rows = vh[
            [
                i
                for i in range(vh.shape[0])
                if i >= singular.size or singular[i] <= tolerance
            ]
        ]
        if null_rows.shape[0] != 1:
            raise CorruptStructure(
                f"col-species: the reconstructed stoichiometry has a "
                f"{null_rows.shape[0]}-dimensional conserved space; this probe's "
                f"network has exactly one, and a larger space needs a moiety "
                f"basis this measurement does not compute"
            )
        vector = null_rows[0]
        scale = vector[0] if abs(vector[0]) > 1e-12 else vector[vector != 0][0]
        return tuple(float(v / scale) for v in vector)


def rebuild_species(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
    numerics_payload: Mapping[str, Any] | None = None,
) -> SpeciesNetwork:
    """Rebuild the network from records.

    ``numerics_payload`` is **separate**, and that separation is a correction:
    an earlier form carried `n_steps` and the integrator name inside the
    digested *structure* payload, which collapsed a distinction the
    preregistration declared binding (scientific reaction-network structure is
    not integrator configuration) and made the relocation digest cover a solver
    choice.
    """
    problem = ScientificProblem.from_dict(problem_payload)
    structure = _require(structure_payload, SPECIES_STRUCTURE_SCHEMA, "col-species")
    numerics = _require(numerics_payload, SPECIES_NUMERICS_SCHEMA, "col-species")
    try:
        species_order = tuple(str(s) for s in structure["species_order"])
        reaction_order = tuple(str(r) for r in structure["reaction_order"])
        stoichiometry = tuple(
            tuple(int(v) for v in row) for row in structure["stoichiometry"]
        )
        axes = tuple(str(a) for a in structure["stoichiometry_axes"])
        n_steps = int(numerics["n_steps"])
    except StructuredReconstructionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CorruptStructure(f"col-species: {type(exc).__name__}: {exc}") from None

    if axes != ("reaction", "species"):
        raise UnsupportedStructureSchema(
            f"col-species: stoichiometry axes are {axes}; this reconstruction "
            f"reads rows as reactions and columns as species. The axis order is "
            f"not inferable from the numbers"
        )
    if len(stoichiometry) != len(reaction_order):
        raise CorruptStructure(
            f"col-species: {len(stoichiometry)} coefficient rows against "
            f"{len(reaction_order)} declared reactions"
        )
    for row in stoichiometry:
        if len(row) != len(species_order):
            raise CorruptStructure(
                f"col-species: a coefficient row has {len(row)} entries against "
                f"{len(species_order)} declared species"
            )

    initial_by_variable = {
        condition.variable: condition.value for condition in problem.initial_conditions
    }
    initial: list[float] = []
    for name in species_order:
        key = f"c:{name}"
        if key not in initial_by_variable:
            raise MissingStructure(
                f"col-species: no initial condition for {key!r}; a batch cannot "
                f"be reconstructed without its initial composition"
            )
        initial.append(initial_by_variable[key].magnitude_in("mol / m**3"))

    return SpeciesNetwork(
        species_order=species_order,
        reaction_order=reaction_order,
        stoichiometry=stoichiometry,
        initial=tuple(initial),
        k1f_per_s=_parameter(problem, "k1f").magnitude_in("1/s"),
        k1r_per_s=_parameter(problem, "k1r").magnitude_in("1/s"),
        k2_m3_per_mol_s=_parameter(problem, "k2").magnitude_in(
            "m**3 / (mol * second)"
        ),
        end_time_s=_parameter(problem, "end_time").magnitude_in("second"),
        n_steps=n_steps,
    )


def integrate_from_records(network: SpeciesNetwork) -> tuple[tuple[float, ...], float]:
    """INJ-2: ``dc/dt = nu^T r`` from the reconstructed network alone.

    Twenty lines of classical RK4 reading the stoichiometry from the
    reconstructed record. Same caveat as INJ-3: it is a transcription of the
    probe's scheme, so agreement is entailed rather than corroborating. What it
    establishes is that the record carries enough to compute the trajectory.
    """
    nu = network.stoichiometry
    n_species = len(network.species_order)
    weights = network.conserved_weights
    dt = network.end_time_s / network.n_steps

    def rates(state: Sequence[float]) -> tuple[float, ...]:
        c_a, c_b = state[0], state[1]
        return (
            network.k1f_per_s * c_a - network.k1r_per_s * c_b,
            network.k2_m3_per_mol_s * c_b * c_b,
        )

    def derivative(state: Sequence[float]) -> tuple[float, ...]:
        r = rates(state)
        return tuple(
            sum(nu[j][i] * r[j] for j in range(len(r))) for i in range(n_species)
        )

    def add(a: Sequence[float], b: Sequence[float], scale: float) -> tuple[float, ...]:
        return tuple(x + scale * y for x, y in zip(a, b))

    state: tuple[float, ...] = tuple(network.initial)
    invariant = sum(w * c for w, c in zip(weights, state))
    drift = 0.0
    for _ in range(network.n_steps):
        k1 = derivative(state)
        k2 = derivative(add(state, k1, dt / 2.0))
        k3 = derivative(add(state, k2, dt / 2.0))
        k4 = derivative(add(state, k3, dt))
        state = tuple(
            s + dt / 6.0 * (a + 2.0 * b + 2.0 * c + d)
            for s, a, b, c, d in zip(state, k1, k2, k3, k4)
        )
        drift = max(
            drift, abs(sum(w * c for w, c in zip(weights, state)) - invariant)
        )
    return state, drift


# =====================================================================
# The probe-free entry point
# =====================================================================

def reconstruct_and_inject(
    column: str,
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None = None,
    numerics_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Everything the fresh process does. Every number here comes from records.

    No probe is imported on this path, so the returned metrics cannot have been
    read from the ground truth. The parent compares them against the committed
    probes; this function never sees one.
    """
    if column == "col-mech":
        structure = rebuild_mechanics(problem_payload, structure_payload)
        displacement = solve_from_records(structure)
        elements = element_stress_from_records(structure, displacement)
        metrics: dict[str, float] = {}
        for index, entry in enumerate(elements):
            stress = entry["stress"]
            metrics[f"sigma_xx:e{index}"] = stress[0]
            metrics[f"sigma_yy:e{index}"] = stress[1]
            metrics[f"sigma_xy:e{index}"] = stress[2]
            metrics[f"sigma_zz:e{index}"] = entry["sigma_zz"]
            sxx, syy, sxy, szz = stress[0], stress[1], stress[2], entry["sigma_zz"]
            metrics[f"von_mises:e{index}"] = float(
                np.sqrt(
                    0.5
                    * (
                        (sxx - syy) ** 2
                        + (syy - szz) ** 2
                        + (szz - sxx) ** 2
                        + 6.0 * sxy**2
                    )
                )
            )
        n_nodes = len(structure.node_coordinates)
        metrics["u_x:max"] = max(
            abs(displacement[structure.dof_per_node * n]) for n in range(n_nodes)
        )
        metrics["u_y:max"] = max(
            abs(displacement[structure.dof_per_node * n + 1]) for n in range(n_nodes)
        )
        return {
            "column": column,
            "metrics": metrics,
            "displacement": [float(v) for v in displacement],
            "constitutive_matrix": [
                [float(v) for v in row] for row in structure.constitutive_matrix
            ],
            "reconstruction_grade": "injected",
        }
    if column == "col-species":
        network = rebuild_species(
            problem_payload, structure_payload, numerics_payload
        )
        state, drift = integrate_from_records(network)
        weights = network.conserved_weights
        return {
            "column": column,
            "metrics": {
                f"c:{name}": value
                for name, value in zip(network.species_order, state)
            }
            | {
                "conserved:weighted": sum(w * c for w, c in zip(weights, state)),
                "conserved:naive": sum(state),
            },
            "state": list(state),
            "conservation_drift": drift,
            "recovered_weights": list(weights),
            "reconstruction_grade": "injected",
        }
    raise StructuredReconstructionError(f"unknown column {column!r}")
