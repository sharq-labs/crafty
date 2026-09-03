"""The L2 steelman for both columns, and the executed encoding attempts.

Every attempt below is **run**. Where a contract refuses, the recorded detail is
that contract's own exception text; where the finding is that a field does not
exist, it is established by reading `dataclasses.fields` of the live record.

The channels available are exactly those that already exist:
`ScientificParameter`, `ScientificVariable`, `InitialCondition`,
`BoundaryCondition`, `ScientificDataReference`. `ScientificProblem.metadata` is
**not** a channel — using it is what this milestone is measuring the cost of, and
both encodings carry an empty metadata mapping, asserted by test.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from engcore.scientific.ir.conditions import InitialCondition
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.values import CategoricalValue, IntegerValue
from engcore.scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableKind,
    VariableRole,
)
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.units.quantity import Quantity
from experiments.cross_domain_coverage import mechanics as mech
from experiments.cross_domain_coverage import species as spc

from .schemas import (
    MECH_STRUCTURE_SCHEMA,
    SPECIES_NUMERICS_SCHEMA,
    SPECIES_STRUCTURE_SCHEMA,
)

__all__ = [
    "Channel",
    "AttemptOutcome",
    "EncodingAttempt",
    "ColumnEncoding",
    "ATTEMPTS",
    "ENCODINGS",
    "COLUMNS",
    "attempts_for",
]

COLUMNS: tuple[str, ...] = ("col-mech", "col-species")


class Channel(str, Enum):
    PARAMETER = "ScientificParameter"
    VARIABLE = "ScientificVariable"
    INITIAL_CONDITION = "InitialCondition"
    BOUNDARY_CONDITION = "BoundaryCondition"
    DATA_REFERENCE = "ScientificDataReference"


class AttemptOutcome(str, Enum):
    WORKS = "works"
    #: A contract raised. Its own message is recorded.
    REFUSED_BY_TYPE = "refused-by-type"
    #: Mechanically accepted; the science would live in the spelling of a name.
    MEANING_IN_KEY = "meaning-in-key"
    #: The bytes fit and nothing states what they are.
    UNLINKED_BULK = "unlinked-bulk"
    #: Not residue at all: derivable from facts that are already representable.
    DERIVABLE = "derivable"


@dataclass(frozen=True)
class EncodingAttempt:
    column: str
    fact: str
    channel: Channel
    outcome: AttemptOutcome
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "fact": self.fact,
            "channel": self.channel.value,
            "outcome": self.outcome.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ColumnEncoding:
    column: str
    problem: ScientificProblem
    structure_payload: Mapping[str, Any] | None = None
    structure_schema: str | None = None
    #: Numerical declaration, kept OUT of the structure payload so that the
    #: scientific identity digest does not cover a solver choice.
    numerics_payload: Mapping[str, Any] | None = None

    def to_payloads(self) -> dict[str, Any]:
        payloads: dict[str, Any] = {"problem": self.problem.to_dict()}
        if self.structure_payload is not None:
            payloads["structure"] = dict(self.structure_payload)
        if self.numerics_payload is not None:
            payloads["numerics"] = dict(self.numerics_payload)
        return payloads


def _try(fn) -> tuple[bool, str]:
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - the exception type IS the finding
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


# =====================================================================
# col-mech attempts
# =====================================================================

def _attempt_constitutive_matrix_as_parameter() -> EncodingAttempt:
    """The 3x3 D as a single typed value. `ScientificValue` is scalars only."""
    matrix = mech.constitutive_matrix(mech.PlaneAssumption.PLANE_STRESS)
    ok, detail = _try(
        lambda: ScientificParameter(name="D", value=matrix)  # type: ignore[arg-type]
    )
    return EncodingAttempt(
        column="col-mech",
        fact="constitutive matrix D (3x3, pascal)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail or "unexpectedly accepted a matrix",
    )


def _attempt_constitutive_matrix_is_derivable() -> EncodingAttempt:
    """And it does not need a home: D = f(E, nu, plane assumption).

    Executed, not argued. `constitutive_matrix` takes `youngs_modulus_pa` and
    `poisson_ratio` as parameters, and all three inputs are representable today
    — two `Quantity` parameters and one `CategoricalValue`. So the matrix is
    **derived data**, not irreducible input, and a residue that included it
    would be counting a computed quantity.
    """
    e = Quantity(mech.YOUNGS_MODULUS_PA, "pascal")
    nu = Quantity(mech.POISSON_RATIO, "dimensionless")
    assumption = CategoricalValue(
        mech.PlaneAssumption.PLANE_STRESS.value,
        vocabulary=tuple(sorted(a.value for a in mech.PlaneAssumption)),
    )
    rebuilt = mech.constitutive_matrix(
        mech.PlaneAssumption(assumption.value),
        youngs_modulus_pa=e.magnitude_in("pascal"),
        poisson_ratio=nu.magnitude_in("dimensionless"),
    )
    original = mech.constitutive_matrix(mech.PlaneAssumption.PLANE_STRESS)
    worst = float(abs(rebuilt - original).max())
    return EncodingAttempt(
        column="col-mech",
        fact="constitutive matrix D (3x3, pascal)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.DERIVABLE if worst == 0.0 else AttemptOutcome.REFUSED_BY_TYPE,
        detail=(
            f"recomputed from two Quantity parameters and one CategoricalValue; "
            f"worst element difference {worst:.3e}. "
            f"SCOPE, corrected after the adversarial review: D is derivable "
            f"whenever the constitutive law is a closed-form function of a fixed "
            f"set of NAMED SCALARS plus a category — which includes orthotropic "
            f"and transversely isotropic laws, not only isotropic ones. What "
            f"breaks derivability is not anisotropy as such but (a) fixed-arity "
            f"component ORDERING once the constant count makes name-keying "
            f"unmanageable, (b) a MATERIAL FRAME, which no contract can state, "
            f"and (c) a field-valued or state-dependent property. None of the "
            f"three is measured here"
        ),
    )


def _attempt_connectivity_as_parameters() -> EncodingAttempt:
    """Element connectivity as named integers. Fits; meaning is in the key."""
    ok, detail = _try(
        lambda: tuple(
            ScientificParameter(name=f"element{e}.node{i}", value=IntegerValue(node))
            for e, element in enumerate(mech.ELEMENTS)
            for i, node in enumerate(element)
        )
    )
    return EncodingAttempt(
        column="col-mech",
        fact="element connectivity (2 triangles x 3 node indices, ordered)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted as six IntegerValue parameters — and the relation lives in "
            "the substrings 'element' and '.node'. Vertex ORDER is load-bearing "
            "here (it fixes the signed area and therefore the sign of B), so a "
            "reader must recover both membership and sequence from spelling"
        ),
    )


def _attempt_coordinates_as_bulk() -> EncodingAttempt:
    """Node coordinates as bulk data. The bytes fit; nothing says what they are."""
    flat = [c for node in mech.NODES for c in node]
    reference, _payload = ScientificDataReference.for_values(
        "mesh:coordinates", flat, unit="meter"
    )
    fields = {f.name for f in dataclasses.fields(reference)}
    return EncodingAttempt(
        column="col-mech",
        fact="node coordinates (4 nodes x 2 components, metres)",
        channel=Channel.DATA_REFERENCE,
        outcome=AttemptOutcome.UNLINKED_BULK,
        detail=(
            f"eight float64 values serialize and verify, and the reference "
            f"carries {sorted(fields)}: count is 8, and nothing states that it is "
            f"4x2 rather than 8x1 or 2x4, which node each pair belongs to, or "
            f"that these are positions at all. count is documented as 'not a "
            f"shape'"
        ),
    )


def _attempt_body_identity_as_a_label() -> EncodingAttempt:
    """Name the BODY the mesh discretizes, independently of the mesh.

    Added after the adversarial review split the connectivity residue into
    "which body" and "how it is meshed". The split needs its own executed
    attempt or the item is not admissible under §13.3.

    Two channels are tried. A `CategoricalValue` accepts a label and states no
    geometry. A `BoundaryCondition` carries a `region`, which is the closest
    thing to a named spatial entity anywhere in the core — and it cannot be used
    standalone, because a boundary condition is a condition *on a variable* and
    requires a kind and a value.
    """
    label_ok, label_detail = _try(
        lambda: ScientificParameter(
            name="body",
            value=CategoricalValue("unit-square-plate", vocabulary=("unit-square-plate",)),
        )
    )
    from engcore.scientific.ir.conditions import BoundaryCondition, BoundaryKind

    region_ok, region_detail = _try(
        lambda: BoundaryCondition(
            name="body-region", variable="", kind=BoundaryKind.OTHER, region="plate"
        )
    )
    return EncodingAttempt(
        column="col-mech",
        fact="which body is discretized (the domain the mesh covers)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if label_ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=(
            label_detail
            or (
                "a CategoricalValue accepts the string 'unit-square-plate' and "
                "states nothing about extent, shape or dimension: two different "
                "bodies with the same label are indistinguishable, and the same "
                "body under two labels is two bodies. "
                f"The nearest spatial concept in the core is BoundaryCondition."
                f"region, and it cannot be used standalone — "
                f"{region_detail or 'it was accepted, which would make a region a condition'}"
            )
        ),
    )


def _attempt_constraints_as_boundary_conditions() -> EncodingAttempt:
    """Clamped DOF as boundary conditions. Needs a variable per component."""
    from engcore.scientific.ir.conditions import BoundaryCondition, BoundaryKind

    ok, detail = _try(
        lambda: BoundaryCondition(
            name="clamp-node0-x",
            variable="u_x:n0",
            kind=BoundaryKind.DIRICHLET,
            region="left-edge",
            value=Quantity(0.0, "meter"),
        )
    )
    return EncodingAttempt(
        column="col-mech",
        fact="constrained degrees of freedom (4 of 8)",
        channel=Channel.BOUNDARY_CONDITION,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted — one record per constrained component, each naming a "
            "variable that must itself be spelled 'u_x:n0'. The record can say a "
            "component is prescribed; it cannot say that u_x and u_y are two "
            "components of ONE vector quantity at one node, so the DOF numbering "
            "(2*node + component) survives only as a convention"
        ),
    )


def _attempt_loads_as_parameters() -> EncodingAttempt:
    """Applied nodal load. The magnitude is a Quantity; the target is a key."""
    ok, detail = _try(
        lambda: (
            ScientificParameter(
                name="load:n1.y", value=Quantity(mech.SHEAR_FORCE_N, "newton")
            ),
            ScientificParameter(
                name="load:n2.y", value=Quantity(mech.SHEAR_FORCE_N, "newton")
            ),
        )
    )
    return EncodingAttempt(
        column="col-mech",
        fact="applied load, and which degrees of freedom receive it",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "the magnitude is a first-class dimensional Quantity; WHERE it is "
            "applied is the substring '.y' of a name. The scalar half is "
            "perfectly served and the structural half is not"
        ),
    )


# =====================================================================
# col-species attempts
# =====================================================================

def _attempt_stoichiometry_as_parameter() -> EncodingAttempt:
    """The 2x3 integer table as one typed value. Same closed union, same refusal."""
    ok, detail = _try(
        lambda: ScientificParameter(
            name="stoichiometry", value=spc.STOICHIOMETRY  # type: ignore[arg-type]
        )
    )
    return EncodingAttempt(
        column="col-species",
        fact="stoichiometric matrix nu (2 reactions x 3 species)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail or "unexpectedly accepted a nested tuple",
    )


def _attempt_stoichiometry_as_named_integers() -> EncodingAttempt:
    """Six named integers. Fits, and CROSS-DOMAIN-COVERAGE already refused it."""
    ok, detail = _try(
        lambda: tuple(
            ScientificParameter(
                name=f"nu_{reaction}_{species}", value=IntegerValue(coefficient)
            )
            for r, reaction in enumerate(spc.REACTIONS)
            for s, species in enumerate(spc.SPECIES)
            for coefficient in (spc.STOICHIOMETRY[r][s],)
        )
    )
    return EncodingAttempt(
        column="col-species",
        fact="stoichiometric matrix nu (2 reactions x 3 species)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted as six IntegerValue parameters named 'nu_R1_A' and so on — "
            "the exact encoding CROSS-DOMAIN-COVERAGE refused in writing, because "
            "the reaction/species pairing lives in the key. Refused again here "
            "for the same reason, and recorded rather than used"
        ),
    )


def _attempt_stoichiometry_as_bulk() -> EncodingAttempt:
    """The coefficients as bulk float64. The bytes fit; the meaning does not."""
    flat = [float(v) for row in spc.STOICHIOMETRY for v in row]
    reference, _payload = ScientificDataReference.for_values(
        "reaction:stoichiometry", flat, unit="dimensionless"
    )
    return EncodingAttempt(
        column="col-species",
        fact="stoichiometric matrix nu (2 reactions x 3 species)",
        channel=Channel.DATA_REFERENCE,
        outcome=AttemptOutcome.UNLINKED_BULK,
        detail=(
            f"six values, count={reference.count}, dtype float64 — integers "
            f"silently widened to floats, no row/column extent, no statement of "
            f"which axis is reactions and which is species, and no link to the "
            f"three concentration variables the columns index. Storing nu here "
            f"would make DATA-BOUNDARY0 the home of a model, which it refuses to "
            f"be"
        ),
    )


def _attempt_species_identity_as_categorical() -> EncodingAttempt:
    """Species identities as a category vocabulary. Works — and says little."""
    ok, detail = _try(
        lambda: ScientificParameter(
            name="species_order",
            value=CategoricalValue("A", vocabulary=tuple(spc.SPECIES)),
        )
    )
    return EncodingAttempt(
        column="col-species",
        fact="species identities, in state order",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "a CategoricalValue carries a vocabulary tuple, which serializes as "
            "a list and reloads as a tuple — so the ORDERED set of names IS "
            "representable, and an earlier form of this note wrongly said it was "
            "not. What is unstateable is the BINDING: nothing says that "
            "vocabulary position is state-vector position, or that it indexes "
            "nu's columns"
        ),
    )


def _attempt_ordered_index_set_as_variable() -> EncodingAttempt:
    """The channel the steelman declared and never tried, until the pass caught it.

    `Channel.VARIABLE` was listed among the five channels §7.1 requires be
    exhausted and appeared in no attempt — a §13.4 trip, and exactly the check
    `HOSTILE-CORE-STRESS` recorded as the one that catches a false gap: *"asking
    which typed channel had not been tried."*

    It is executed here, and it **narrows the finding**. A categorical
    `ScientificVariable` carries an ordered tuple of named members that round
    trips deterministically. So the ordered index set is representable, and the
    residue is one step smaller and one step sharper than first recorded.
    """
    ok, detail = _try(
        lambda: ScientificVariable(
            name="species",
            unit="dimensionless",
            kind=VariableKind.CATEGORICAL,
            role=VariableRole.OBSERVABLE,
            categories=tuple(spc.SPECIES),
        )
    )
    round_trip = ()
    if ok:
        variable = ScientificVariable(
            name="species",
            unit="dimensionless",
            kind=VariableKind.CATEGORICAL,
            role=VariableRole.OBSERVABLE,
            categories=tuple(spc.SPECIES),
        )
        round_trip = ScientificVariable.from_dict(variable.to_dict()).categories
    ordered = round_trip == tuple(spc.SPECIES)
    return EncodingAttempt(
        column="col-species",
        fact="species identities, in state order",
        channel=Channel.VARIABLE,
        outcome=AttemptOutcome.MEANING_IN_KEY if ordered else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            f"accepted, and the order survives serialization: categories "
            f"round-trip as {round_trip}. So an ORDERED INDEX SET OF NAMED "
            f"ENTITIES is representable today, in universal core, and this "
            f"milestone's first reading — that it was not — was wrong. The "
            f"residue narrows to the BINDING: no record states that this "
            f"ordering is the one indexing nu's columns or the state vector, "
            f"which is why rebuild_species must read species_order from a "
            f"domain payload and refuses a transposed axis rather than guessing"
        ),
    )


def _attempt_initial_composition_as_conditions() -> EncodingAttempt:
    """Three scalar initial concentrations. This one genuinely works."""
    ok, detail = _try(
        lambda: tuple(
            InitialCondition(
                variable=f"c:{name}",
                value=Quantity(value, "mol / m**3"),
                time=Quantity(0.0, "second"),
            )
            for name, value in zip(spc.SPECIES, spc.case_c().initial)
        )
    )
    return EncodingAttempt(
        column="col-species",
        fact="initial composition (three scalar concentrations)",
        channel=Channel.INITIAL_CONDITION,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or "accepted, typed, dimension-checked, one record per species",
    )


def _attempt_rate_constants_as_parameters() -> EncodingAttempt:
    """Rate constants of two different dimensions. Also genuinely works."""
    case = spc.case_c()
    ok, detail = _try(
        lambda: (
            ScientificParameter(name="k1f", value=Quantity(case.k1f_per_s, "1/s")),
            ScientificParameter(name="k1r", value=Quantity(case.k1r_per_s, "1/s")),
            ScientificParameter(
                name="k2",
                value=Quantity(case.k2_m3_per_mol_s, "m**3 / (mol * second)"),
            ),
        )
    )
    return EncodingAttempt(
        column="col-species",
        fact="rate constants (two dimensions)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted. Note the dimensions differ between k1f and k2 because the "
            "reaction orders differ — so the units already encode reaction order, "
            "and a reader can see that k2 is second-order without being told. "
            "That is real information the unit contract carries for free"
        ),
    )


def _attempt_conserved_weights_derivation() -> EncodingAttempt:
    """Can the conserved weights be recovered without nu? Executed answer: no."""
    case = spc.case_c()
    _final, trajectory = spc.integrate(case.with_steps(200))
    weighted = spc.conservation_drift(trajectory)
    naive = spc.naive_drift(trajectory)
    return EncodingAttempt(
        column="col-species",
        fact="conserved combination c_A + c_B + 2 c_C",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.UNLINKED_BULK if naive > weighted else AttemptOutcome.WORKS,
        detail=(
            f"executed: the weighted invariant drifts {weighted:.3e} and the "
            f"unweighted sum a reader without nu would form drifts {naive:.3e} — "
            f"a factor of {naive / max(weighted, 1e-300):.3g}. The weights come "
            f"from the null space of nu and from nowhere else, so a reader "
            f"holding every typed record this platform can produce reports a "
            f"violated conservation law for a perfectly conserved system"
        ),
    )


ATTEMPTS: tuple[EncodingAttempt, ...] = (
    _attempt_constitutive_matrix_as_parameter(),
    _attempt_constitutive_matrix_is_derivable(),
    _attempt_connectivity_as_parameters(),
    _attempt_body_identity_as_a_label(),
    _attempt_coordinates_as_bulk(),
    _attempt_constraints_as_boundary_conditions(),
    _attempt_loads_as_parameters(),
    _attempt_stoichiometry_as_parameter(),
    _attempt_stoichiometry_as_named_integers(),
    _attempt_stoichiometry_as_bulk(),
    _attempt_species_identity_as_categorical(),
    _attempt_ordered_index_set_as_variable(),
    _attempt_initial_composition_as_conditions(),
    _attempt_rate_constants_as_parameters(),
    _attempt_conserved_weights_derivation(),
)


def attempts_for(column: str) -> tuple[EncodingAttempt, ...]:
    return tuple(a for a in ATTEMPTS if a.column == column)


# =====================================================================
# The L2 encodings
# =====================================================================

def mechanics_encoding() -> ColumnEncoding:
    """CASE A2 at L2, plus the geometry/topology residue.

    Every scalar is a typed parameter, including the two that generate ``D``.
    The residue payload carries what no channel holds: coordinates, connectivity,
    the constrained-DOF set and the load's DOF indexing.
    """
    variables = [
        ScientificVariable(
            name=f"u_{component}:n{node}",
            unit="meter",
            role=VariableRole.STATE,
            description=f"Displacement component {component} of node {node}.",
        )
        for node in range(mech.N_NODES)
        for component in ("x", "y")
    ]
    variables += [
        ScientificVariable(
            name=f"sigma_{component}:e{element}",
            unit="pascal",
            role=VariableRole.OBSERVABLE,
        )
        for element in range(len(mech.ELEMENTS))
        for component in ("xx", "yy", "xy", "zz")
    ]
    variables += [
        ScientificVariable(name="u_x:max", unit="meter", role=VariableRole.OBSERVABLE),
        ScientificVariable(name="u_y:max", unit="meter", role=VariableRole.OBSERVABLE),
    ]
    variables += [
        ScientificVariable(
            name=f"von_mises:e{element}", unit="pascal", role=VariableRole.OBSERVABLE
        )
        for element in range(len(mech.ELEMENTS))
    ]
    problem = ScientificProblem(
        problem_id="exec-spec-structured:mechanics-shear",
        name="Two-element plane-stress patch, shear case",
        description=(
            "Linear isotropic constant-strain triangles; left edge clamped, "
            "right edge sheared."
        ),
        variables=tuple(variables),
        parameters=(
            ScientificParameter(
                name="youngs_modulus", value=Quantity(mech.YOUNGS_MODULUS_PA, "pascal")
            ),
            ScientificParameter(
                name="poisson_ratio",
                value=Quantity(mech.POISSON_RATIO, "dimensionless"),
            ),
            ScientificParameter(
                name="thickness", value=Quantity(mech.THICKNESS_M, "meter")
            ),
            ScientificParameter(
                name="shear_force", value=Quantity(mech.SHEAR_FORCE_N, "newton")
            ),
            ScientificParameter(
                name="plane_assumption",
                value=CategoricalValue(
                    mech.PlaneAssumption.PLANE_STRESS.value,
                    vocabulary=tuple(sorted(a.value for a in mech.PlaneAssumption)),
                ),
                description=(
                    "Which 2D reduction of 3D elasticity is asserted. Changes "
                    "the constitutive law, not the mesh."
                ),
            ),
        ),
        models=(ModelReference("exec-spec-structured.mechanics.cst_patch", "0.1.0"),),
        required_capabilities=frozenset({"mechanics:linear_elastostatics_2d"}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "stiffness_symmetry", "force_equilibrium"}
        ),
    )
    return ColumnEncoding(
        column="col-mech",
        problem=problem,
        structure_payload={
            "schema": MECH_STRUCTURE_SCHEMA,
            "node_coordinates": [list(node) for node in mech.NODES],
            "coordinate_unit": "meter",
            "elements": [list(element) for element in mech.ELEMENTS],
            "element_kind": "constant_strain_triangle",
            "constrained_dof": list(mech.CLAMPED_DOF),
            "dof_per_node": 2,
            "dof_index_rule": "2*node + component, component 0=x 1=y",
            "loaded_dof": [2 * 1 + 1, 2 * 2 + 1],
        },
        structure_schema=MECH_STRUCTURE_SCHEMA,
    )


def species_encoding() -> ColumnEncoding:
    """CASE C1 at L2, plus the reaction-network residue.

    Rate constants, initial composition and the horizon are typed. The residue
    payload carries the species order, the reaction labels and the stoichiometric
    coefficients — and `n_steps`, which is not structure at all but the
    integrator's step count.
    """
    case = spc.case_c()
    variables = [
        ScientificVariable(
            name=f"c:{name}",
            unit="mol / m**3",
            role=VariableRole.STATE,
            description=f"Concentration of species {name}.",
        )
        for name in spc.SPECIES
    ]
    variables += [
        ScientificVariable(
            name="conserved:weighted", unit="mol / m**3", role=VariableRole.OBSERVABLE
        ),
        ScientificVariable(
            name="conserved:naive", unit="mol / m**3", role=VariableRole.OBSERVABLE
        ),
    ]
    problem = ScientificProblem(
        problem_id="exec-spec-structured:species-batch",
        name="Closed isothermal three-species batch",
        description="Two reactions among three species, constant volume.",
        variables=tuple(variables),
        parameters=(
            ScientificParameter(name="k1f", value=Quantity(case.k1f_per_s, "1/s")),
            ScientificParameter(name="k1r", value=Quantity(case.k1r_per_s, "1/s")),
            ScientificParameter(
                name="k2",
                value=Quantity(case.k2_m3_per_mol_s, "m**3 / (mol * second)"),
            ),
            ScientificParameter(
                name="temperature", value=Quantity(case.temperature_k, "kelvin")
            ),
            ScientificParameter(
                name="end_time", value=Quantity(case.end_time_s, "second")
            ),
        ),
        initial_conditions=tuple(
            InitialCondition(
                variable=f"c:{name}",
                value=Quantity(value, "mol / m**3"),
                time=Quantity(0.0, "second"),
            )
            for name, value in zip(spc.SPECIES, case.initial)
        ),
        models=(ModelReference("exec-spec-structured.species.batch_network", "0.1.0"),),
        required_capabilities=frozenset({"chemistry:batch_reaction_network"}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "conservation_invariant"}
        ),
    )
    return ColumnEncoding(
        column="col-species",
        problem=problem,
        structure_payload={
            "schema": SPECIES_STRUCTURE_SCHEMA,
            "case_id": case.case_id,
            "species_order": list(spc.SPECIES),
            "reaction_order": list(spc.REACTIONS),
            "stoichiometry": [list(row) for row in spc.STOICHIOMETRY],
            "stoichiometry_axes": ["reaction", "species"],
        },
        structure_schema=SPECIES_STRUCTURE_SCHEMA,
        # SEPARATE, after the adversarial pass: carrying these inside the
        # structure payload made the scientific identity digest cover a solver
        # choice, so two payloads differing only in step count would have been
        # two different sciences. They still have no persistable home — that is
        # the SolverSettings gap EXEC-SPEC measured and did not close.
        numerics_payload={
            "schema": SPECIES_NUMERICS_SCHEMA,
            "n_steps": case.n_steps,
            "integrator": "rk4-fixed-step",
        },
    )


ENCODINGS: dict[str, ColumnEncoding] = {
    "col-mech": mechanics_encoding(),
    "col-species": species_encoding(),
}
