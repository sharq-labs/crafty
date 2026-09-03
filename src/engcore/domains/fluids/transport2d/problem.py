"""The 2D steady scalar advection-diffusion benchmark: domain, model, problem.

THE PHYSICS, STATED ONCE (frozen from FLUID-PDE-PREPARATION, Track B)
-----------------------------------------------------------------------
On the square ``[0, L] x [0, L]`` the normalized field ``c`` obeys

    div(u c) - D grad^2 c = s(x, y)
    u(x, y)  = omega * (-(y - L/2), (x - L/2))     solid-body rotation
    c(x, y)  = c*(x, y)  on the boundary (Dirichlet, all four sides)

``c`` IS DIMENSIONLESS. It is a normalized scalar transport field — species
concentration, a passive scalar, a convective-heat analogue — not a
concentration in mol/L or a temperature in kelvin. Calling it anything with an
absolute scale would claim a material or reference state this benchmark does
not have.

WHY THE BOUNDARY VALUE AND VELOCITY FIELD ARE FIXED
-----------------------------------------------------
They are not configurable, and that is the point, exactly as
``thermal/conduction1d`` fixes its own boundary and initial conditions. This
benchmark exists to verify a solver against an independent closed form:

    c*(x, y) = sin(pi x / L) sin(pi y / L)
    s(x, y)  = u . grad(c*) - D * laplacian(c*)      (derived analytically)

No series, no truncation — the manufactured solution is exact by
construction, so the reference carries zero approximation of its own to be
confused with the solver's discretization error. The rotational velocity
field is not configurable either: it is the specific, non-trivial field
``docs/fluid-pde-preparation.md`` §B7 found forces boundary-orientation
pressure (every side is simultaneously half inflow, half outflow — see
``reference.py``), and that finding is this milestone's mandatory stress
point (F6). A different velocity field would not exercise it.

WHAT IS CONFIGURABLE
----------------------
The physical declaration (``side``, ``diffusivity``, ``angular_rate``) and the
numerical declaration (``n_cells``, a square grid). These are separate on
purpose, exactly as ``ConductionSlab``/``SlabDiscretization`` are separate:
the first says what problem is being posed, the second says how finely it is
being resolved, and a domain that cannot tell those apart cannot report a
discretization error. The benchmark instance this milestone actually runs and
verifies against fixes ``L = 1.0 m``, ``D = 0.01 m^2/s``, ``omega = 1 /s`` —
exactly the preparation's frozen numbers (see
``docs/real-fluid-pde-prereg.md`` §1) — but the declaration is not hard-coded
to those values: ``side`` is a genuine typed physical extent, generalizing the
preparation's unit-square constant the same way ``ConductionSlab.length``
generalizes a fixed slab length.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

from ....scientific.ir.conditions import BoundaryCondition, BoundaryKind
from ....scientific.ir.problem import ModelReference, ScientificProblem
from ....scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from ....scientific.models.definition import (
    InputSourceKind,
    ModelInputSpec,
    ModelOutputSpec,
    ModelType,
    ModelValidationStatus,
    RangeCondition,
    ScientificModelDefinition,
    ValidityDomain,
)
from ....scientific.solvers.capability import SolverCapability
from ....scientific.units.quantity import Quantity
from .errors import Transport2DConfigurationError

# --- units -------------------------------------------------------------------
FIELD_UNIT = "dimensionless"
LENGTH_UNIT = "meter"
DIFFUSIVITY_UNIT = "m**2/s"
ANGULAR_RATE_UNIT = "1/s"

# --- capability, declared in this package and nowhere else -------------------
TRANSPORT2D_ADVECTION_DIFFUSION = SolverCapability(
    "fluids:advection_diffusion_2d",
    "2D steady scalar advection-diffusion in a prescribed velocity field, "
    "cell-centered finite volume",
)

MODEL_VERSION = "0.1.0"

_ASSUMPTIONS = (
    "two spatial dimensions; a single scalar transported field",
    "steady state; no time dependence",
    "the velocity field is prescribed (not solved for) and exactly "
    "divergence-free by construction — this is transport of a scalar in a "
    "given flow, not a momentum equation",
    "constant, field-independent scalar diffusivity",
    "Dirichlet boundary values on all four sides of a square domain, no "
    "internal geometry",
    "normalized dimensionless field; no absolute concentration or "
    "temperature scale, no material and no thermodynamic state are claimed",
)

# FUNDAMENTAL_RELATION, not APPROXIMATION or NUMERICAL_MODEL: the transport
# equation itself is a conservation statement (div(u c) - D grad^2 c = s),
# exactly as thermal/conduction1d's diffusion equation is. The scheme that
# discretizes it (upwind advection, central diffusion, a specific grid) is a
# property of the REALIZATION/SOLVER, not of this scientific claim — see
# solver.py's module docstring for where that line is actually drawn.
TRANSPORT2D_MODEL = ScientificModelDefinition(
    model_id="fluids.transport2d.advection_diffusion",
    version=MODEL_VERSION,
    name="2D steady scalar advection-diffusion",
    domain="fluids",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "div(u c) - D grad^2 c = s on a square domain, with a prescribed "
        "divergence-free velocity field and Dirichlet boundary values, for "
        "a normalized dimensionless scalar field."
    ),
    inputs=(
        ModelInputSpec(
            name="diffusivity",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=DIFFUSIVITY_UNIT,
            description="Scalar diffusivity D; strictly positive.",
        ),
        ModelInputSpec(
            name="side",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=LENGTH_UNIT,
            description="Side length of the square domain.",
        ),
        ModelInputSpec(
            name="angular_rate",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar=ANGULAR_RATE_UNIT,
            description=(
                "Angular rate of the prescribed solid-body rotation field."
            ),
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="c",
            unit_exemplar=FIELD_UNIT,
            description=(
                "Normalized dimensionless scalar transport field over the "
                "domain. Not a concentration or temperature: no absolute "
                "scale is implied."
            ),
        ),
    ),
    assumptions=_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="diffusivity",
                minimum=Quantity(0.0, DIFFUSIVITY_UNIT),
                minimum_inclusive=False,
                description=(
                    "Strictly positive diffusivity; zero is pure advection "
                    "(a different, hyperbolic problem this model does not "
                    "claim) and negative is anti-diffusion, ill-posed."
                ),
            ),
            # Mesh-dependent, so it cannot be a fact about the PHYSICAL
            # problem (see problem_id's fingerprint, which deliberately
            # excludes the grid) — it is supplied through
            # `validity_context(extra=...)` at the point a grid actually
            # exists, per ENCODING_C
            # (docs/hostile-core-domain-stress-evidence.md §J.3): no core
            # change, existing contracts. Stated on the RECIPROCAL cell
            # Peclet number, not the Peclet number itself, so the criterion
            # stays a finite Quantity even in a hypothetical zero-diffusion
            # limit (`Quantity` refuses non-finite magnitudes) — the same
            # reparameterization that milestone measured and adopted.
            RangeCondition(
                name="inverse_peclet_cell",
                minimum=Quantity(0.5, "dimensionless"),
                minimum_inclusive=True,
                description=(
                    "dx*D/(|u|_max) >= 0.5, i.e. peak cell Peclet number <= 2 "
                    "— the diffusion-dominated regime this benchmark's "
                    "convergence order is asymptotically first-order in. "
                    "A coarse mesh legitimately falls outside this; that is "
                    "reported, not treated as an error (see "
                    "docs/fluid-pde-preparation.md §B2)."
                ),
            ),
        ),
        description=(
            "Steady advection-diffusion of a passive scalar in a prescribed, "
            "divergence-free velocity field on a bounded square."
        ),
    ),
    required_capabilities=frozenset({TRANSPORT2D_ADVECTION_DIFFUSION.name}),
    # SELF_CONSISTENT, not BENCHMARK_VALIDATED, for the identical reason
    # DIFFUSION_MODEL uses it: agreement with a manufactured solution of the
    # same equation shows the discretization solves what it claims to solve.
    # It is not an external physical benchmark and involves no measurement.
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
    references=(),
)

TRANSPORT2D_MODELS = (TRANSPORT2D_MODEL,)


def transport2d_solver_capabilities() -> frozenset[SolverCapability]:
    return frozenset({TRANSPORT2D_ADVECTION_DIFFUSION})


# =====================================================================
# Declarations
# =====================================================================

@dataclass(frozen=True)
class Transport2DGrid:
    """How finely the square is resolved. Purely numerical.

    A single ``n_cells`` (square, ``n_cells x n_cells``) rather than
    independent x/y counts: the frozen benchmark (§B2 of the preparation
    document) is posed on a square with a square grid, and every convergence
    number this milestone reproduces was measured on one. Nothing in this
    scheme needs rectangular cells, and inventing that generality here would
    be unexercised.
    """

    n_cells: int

    def __post_init__(self) -> None:
        if isinstance(self.n_cells, bool) or not isinstance(self.n_cells, int):
            raise Transport2DConfigurationError(
                f"n_cells must be an int, got {type(self.n_cells).__name__}"
            )
        if self.n_cells < 2:
            raise Transport2DConfigurationError(
                f"n_cells must be at least 2, got {self.n_cells}"
            )

    @property
    def dof(self) -> int:
        return self.n_cells * self.n_cells

    @property
    def work_proxy(self) -> int:
        """Deterministic proxy for computational work: dof (this is a
        single direct linear solve, not a time march, so there is no second
        factor the way ``SlabDiscretization.work_proxy`` has ``n_steps``)."""
        return self.dof

    def to_dict(self) -> dict[str, Any]:
        return {"n_cells": self.n_cells, "dof": self.dof, "work_proxy": self.work_proxy}

    @classmethod
    def from_dict(cls, payload: Any) -> "Transport2DGrid":
        return cls(n_cells=int(payload["n_cells"]))


def _positive_quantity(value: Any, unit: str, label: str) -> Quantity:
    if not isinstance(value, Quantity):
        raise Transport2DConfigurationError(
            f"{label} must be a Quantity carrying {unit!r}, got "
            f"{type(value).__name__} — a bare number is not a declaration"
        )
    magnitude = value.magnitude_in(unit)
    if not math.isfinite(magnitude) or magnitude <= 0.0:
        raise Transport2DConfigurationError(
            f"{label} must be finite and strictly positive, got {magnitude!r} "
            f"{unit}"
        )
    return value


@dataclass(frozen=True)
class Transport2DDomain:
    """One fully declared benchmark instance.

    The velocity field's functional form and the Dirichlet boundary value
    are not fields: they are fixed by this benchmark and documented in the
    module docstring, exactly as ``ConductionSlab`` fixes its own boundary
    and initial conditions.
    """

    domain_id: str
    side: Quantity
    diffusivity: Quantity
    angular_rate: Quantity
    grid: Transport2DGrid

    def __post_init__(self) -> None:
        if not str(self.domain_id).strip():
            raise Transport2DConfigurationError(
                "domain requires a non-empty domain_id"
            )
        object.__setattr__(self, "domain_id", str(self.domain_id).strip())
        _positive_quantity(self.side, LENGTH_UNIT, "side")
        _positive_quantity(self.diffusivity, DIFFUSIVITY_UNIT, "diffusivity")
        rate = self.angular_rate
        if not isinstance(rate, Quantity):
            raise Transport2DConfigurationError(
                f"angular_rate must be a Quantity carrying {ANGULAR_RATE_UNIT!r}"
            )
        rate_mag = rate.magnitude_in(ANGULAR_RATE_UNIT)
        if not math.isfinite(rate_mag) or rate_mag == 0.0:
            raise Transport2DConfigurationError(
                f"angular_rate must be finite and non-zero, got {rate_mag!r} "
                f"{ANGULAR_RATE_UNIT} — zero rotation degenerates to pure "
                f"diffusion, a different (still solvable, but unexercised) "
                f"benchmark"
            )
        if not isinstance(self.grid, Transport2DGrid):
            raise Transport2DConfigurationError("grid must be a Transport2DGrid")

    # -- convenience accessors in base units --------------------------------
    @property
    def side_m(self) -> float:
        return self.side.magnitude_in(LENGTH_UNIT)

    @property
    def diffusivity_m2_s(self) -> float:
        return self.diffusivity.magnitude_in(DIFFUSIVITY_UNIT)

    @property
    def omega_per_s(self) -> float:
        return self.angular_rate.magnitude_in(ANGULAR_RATE_UNIT)

    @property
    def dx_m(self) -> float:
        return self.side_m / self.grid.n_cells

    @property
    def peak_cell_peclet(self) -> float:
        """Peak |u| dx / D over the domain. Reported for provenance, and the
        exact quantity that explains why this benchmark's convergence order
        is sub-asymptotic below n=32 (see reference.py / the prereg)."""
        peak_speed = abs(self.omega_per_s) * self.side_m * math.sqrt(0.5)
        return peak_speed * self.dx_m / self.diffusivity_m2_s

    def with_grid(self, grid: Transport2DGrid) -> "Transport2DDomain":
        """The same physical domain at a different resolution — used by the
        refinement gate, exactly as ``ConductionSlab.with_discretization``."""
        return Transport2DDomain(
            domain_id=self.domain_id,
            side=self.side,
            diffusivity=self.diffusivity,
            angular_rate=self.angular_rate,
            grid=grid,
        )

    def fingerprint(self) -> str:
        """Identity of the PHYSICAL problem, excluding the discretization."""
        blob = json.dumps(
            {
                "domain_id": self.domain_id,
                "side_m": self.side_m,
                "diffusivity_m2_s": self.diffusivity_m2_s,
                "omega_per_s": self.omega_per_s,
                "boundary": "dirichlet_c_star_all_sides",
                "velocity_field": "solid_body_rotation_about_centre",
                "manufactured_solution": "sin(pi x/L) sin(pi y/L)",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "side_m": self.side_m,
            "diffusivity_m2_s": self.diffusivity_m2_s,
            "omega_per_s": self.omega_per_s,
            "boundary_conditions": "c = c*(x,y) on all four sides",
            "velocity_field": "u = omega*(-(y-L/2), (x-L/2))",
            "field_unit": FIELD_UNIT,
            "grid": self.grid.to_dict(),
            "dx_m": self.dx_m,
            "peak_cell_peclet": self.peak_cell_peclet,
            "fingerprint": self.fingerprint(),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "Transport2DDomain":
        """Reconstruct from a plain dict — the F9 executable-spec residue
        this milestone measures. See ``docs/real-fluid-pde-evidence.md`` §F9
        for exactly what this can and cannot reconstruct."""
        return cls(
            domain_id=payload["domain_id"],
            side=Quantity(float(payload["side_m"]), LENGTH_UNIT),
            diffusivity=Quantity(
                float(payload["diffusivity_m2_s"]), DIFFUSIVITY_UNIT
            ),
            angular_rate=Quantity(
                float(payload["omega_per_s"]), ANGULAR_RATE_UNIT
            ),
            grid=Transport2DGrid.from_dict(payload["grid"]),
        )


# =====================================================================
# The universal problem statement
# =====================================================================

#: The field variable: what VariableBulkLinkage binds to a bulk reference,
#: and what the boundary conditions attach to (see the boundary-orientation
#: module docstring in reference.py for why "one variable, four Dirichlet
#: BoundaryConditions" is exactly what this benchmark needs and exactly
#: what it cannot say more than — F6).
FIELD_VARIABLE = "c:field"
CENTRE_METRIC = "c:centre"
MAX_METRIC = "c:max"
MIN_METRIC = "c:min"

#: Boundary region labels. Compass points chosen for readability; the core
#: treats ``region`` as an opaque label (ir/conditions.py) either way.
SIDE_SOUTH = "side-south"  # y = 0
SIDE_NORTH = "side-north"  # y = L
SIDE_WEST = "side-west"    # x = 0
SIDE_EAST = "side-east"    # x = L
ALL_SIDES = (SIDE_SOUTH, SIDE_NORTH, SIDE_WEST, SIDE_EAST)


def build_transport2d_problem(
    domain: Transport2DDomain, *, problem_id: str | None = None
) -> ScientificProblem:
    """Express the benchmark in the domain-neutral IR.

    The discretization is carried as metadata, not as a parameter — same
    rule ``thermal/conduction1d`` uses: it is a property of *how* the
    problem is being solved, not of *what* problem is being posed.
    """
    variables = (
        ScientificVariable(
            name=FIELD_VARIABLE,
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description=(
                "Scalar transport field c over the square domain. Bulk "
                "values, when produced, are bound to this variable through "
                "a VariableBulkLinkage — see solver.py."
            ),
        ),
        ScientificVariable(
            name=CENTRE_METRIC,
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Field value at the domain centre (L/2, L/2)",
        ),
        ScientificVariable(
            name=MAX_METRIC,
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Maximum field value over all cell centres",
        ),
        ScientificVariable(
            name=MIN_METRIC,
            unit=FIELD_UNIT,
            role=VariableRole.OBSERVABLE,
            description="Minimum field value over all cell centres",
        ),
    )
    parameters = (
        ScientificParameter(
            name="diffusivity", value=domain.diffusivity, description="Scalar diffusivity D"
        ),
        ScientificParameter(
            name="side", value=domain.side, description="Domain side length"
        ),
        ScientificParameter(
            name="angular_rate",
            value=domain.angular_rate,
            description="Rotation rate of the prescribed velocity field",
        ),
    )
    zero = Quantity(0.0, FIELD_UNIT)
    boundary_conditions = tuple(
        BoundaryCondition(
            name=side,
            variable=FIELD_VARIABLE,
            kind=BoundaryKind.DIRICHLET,
            region=side,
            value=zero,
            description=(
                "c = c*(x,y) restricted to this side; c* vanishes on every "
                "side of the unit-square benchmark by construction"
            ),
        )
        for side in ALL_SIDES
    )
    return ScientificProblem(
        problem_id=problem_id or f"fluids-transport2d-{domain.domain_id}",
        name="2D steady scalar advection-diffusion in a rotational field",
        description=(
            "Scalar c on [0, L]^2 with Dirichlet boundary values equal to "
            "the manufactured solution, transported by a prescribed "
            "divergence-free solid-body-rotation velocity field."
        ),
        variables=variables,
        parameters=parameters,
        boundary_conditions=boundary_conditions,
        models=tuple(
            ModelReference(model.model_id, model.version)
            for model in TRANSPORT2D_MODELS
        ),
        required_capabilities=frozenset({TRANSPORT2D_ADVECTION_DIFFUSION.name}),
        validation_requirements=frozenset(
            {
                "dimensional_consistency",
                "field_finite",
                "sparse_dense_assembly_agreement",
                "admissibility_bound",
            }
        ),
        metadata={
            "domain": "fluids",
            "domain_id": domain.domain_id,
            "domain_fingerprint": domain.fingerprint(),
            "boundary_conditions": "c = c*(x,y) on all four sides",
            "velocity_field": "u = omega*(-(y-L/2), (x-L/2))",
            "field_unit": FIELD_UNIT,
            "n_cells": str(domain.grid.n_cells),
            "work_proxy": str(domain.grid.work_proxy),
        },
    )


def verify_problem_matches_domain(
    problem: ScientificProblem, domain: Transport2DDomain
) -> None:
    """Refuse a problem/domain pairing that describes different physics."""
    declared = problem.metadata.get("domain_fingerprint")
    actual = domain.fingerprint()
    if declared and declared != actual:
        raise Transport2DConfigurationError(
            f"problem {problem.problem_id!r} declares domain fingerprint "
            f"{str(declared)[:12]}… but was paired with {actual[:12]}…; the "
            f"problem and the domain describe different physical systems"
        )
