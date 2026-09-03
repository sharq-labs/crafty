"""2D steady scalar advection-diffusion — the first real production Fluid
domain (`REAL-FLUID-PDE-DOMAIN`, promoting `docs/fluid-pde-preparation.md`'s
Track B consumer).

    div(u c) - D grad^2 c = s(x, y)          on [0, L]^2
    u(x, y) = omega * (-(y - L/2), (x - L/2))     prescribed rotation
    c = c*(x, y)                                    Dirichlet, all sides

``c`` is a NORMALIZED DIMENSIONLESS scalar transport field. It is never
reported as a concentration in mol/L or a temperature in kelvin: no absolute
scale, no reference state and no material are claimed anywhere in this
package.

WHAT THIS DOMAIN ADDS THAT THERMAL/ELECTRICAL COULD NOT
------------------------------------------------------------
The first 2D domain, the first domain with a field-valued MODEL INPUT (the
prescribed velocity — never solved for, never a searched variable), the
first real production caller of ``VariableBulkLinkage`` (F4) and of
``ValidationReport.require_admission`` (F8), and the mandatory
boundary-orientation stress point (F6): with this benchmark's rotational
field, every one of the four labelled boundary sides is simultaneously half
inflow and half outflow, which a single ``BoundaryCondition.region`` string
cannot state as one role.

Module roles:

    problem.py     domain and grid declarations, the transport model, the
                   domain capability, and the universal problem statement
    reference.py   the manufactured solution, the prescribed velocity field,
                   and the boundary-orientation check (F6) — verification
                   side only, never imports solver.py
    solver.py      the shared assembly, Transport2DSolver (PRODUCTION, SciPy
                   sparse) and NativeDenseTransport2DSolver (reference-check
                   only), and the solve_transport2d wrapper
    validation.py  per-solve checks, the refinement gate (the only code
                   allowed to award NUMERICALLY_CONVERGED or
                   ANALYTICALLY_VERIFIED), and the two F8 admission
                   consumers

THE PUBLIC SURFACE IS DELIBERATELY SMALL, same discipline as
``thermal/conduction1d``: ``__all__`` is what a *consumer of this domain*
needs. Everything else is an implementation detail, reachable from its own
module when a white-box test genuinely needs it.
"""

from __future__ import annotations

from .errors import (
    Transport2DBindingError,
    Transport2DConfigurationError,
    Transport2DError,
)
from .problem import (
    ALL_SIDES,
    CENTRE_METRIC,
    DIFFUSIVITY_UNIT,
    FIELD_UNIT,
    FIELD_VARIABLE,
    LENGTH_UNIT,
    MAX_METRIC,
    MIN_METRIC,
    ANGULAR_RATE_UNIT,
    SIDE_EAST,
    SIDE_NORTH,
    SIDE_SOUTH,
    SIDE_WEST,
    TRANSPORT2D_ADVECTION_DIFFUSION,
    TRANSPORT2D_MODEL,
    TRANSPORT2D_MODELS,
    Transport2DDomain,
    Transport2DGrid,
    build_transport2d_problem,
)
from .reference import (
    REFERENCE_EXPRESSION,
    REFERENCE_ID,
    SideOrientation,
    c_star,
    exact_centre,
    exact_field,
    side_orientation,
    source,
    velocity,
)
from .solver import (
    DENSE_BACKEND,
    DENSE_SOLVER_ID,
    SPARSE_BACKEND,
    SPARSE_SOLVER_ID,
    SOLVER_VERSION,
    NativeDenseTransport2DSolver,
    Transport2DSolver,
    solve_transport2d,
)
from .validation import (
    ANALYTIC_REL_TOL,
    MIN_OBSERVED_ORDER,
    MIN_RUNGS,
    VERIFICATION_LADDER,
    Transport2DValidationSettings,
    VerificationReport,
    boundary_orientation_report,
    classify_boundary_orientation,
    read_centre_concentration_unguarded,
    read_centre_concentration_with_admission,
    run_verification_gate,
)

__all__ = [
    # declarations
    "Transport2DDomain",
    "Transport2DGrid",
    # problem statement
    "build_transport2d_problem",
    "TRANSPORT2D_MODELS",
    "TRANSPORT2D_MODEL",
    "TRANSPORT2D_ADVECTION_DIFFUSION",
    "FIELD_VARIABLE",
    "CENTRE_METRIC",
    "MAX_METRIC",
    "MIN_METRIC",
    "ALL_SIDES",
    "SIDE_SOUTH",
    "SIDE_NORTH",
    "SIDE_WEST",
    "SIDE_EAST",
    # solving
    "Transport2DSolver",
    "NativeDenseTransport2DSolver",
    "solve_transport2d",
    "SPARSE_SOLVER_ID",
    "DENSE_SOLVER_ID",
    "SOLVER_VERSION",
    "SPARSE_BACKEND",
    "DENSE_BACKEND",
    # the manufactured reference and boundary orientation (F6)
    "c_star",
    "source",
    "velocity",
    "exact_centre",
    "exact_field",
    "side_orientation",
    "SideOrientation",
    "REFERENCE_ID",
    "REFERENCE_EXPRESSION",
    # verification
    "run_verification_gate",
    "VerificationReport",
    "VERIFICATION_LADDER",
    "ANALYTIC_REL_TOL",
    "MIN_OBSERVED_ORDER",
    "MIN_RUNGS",
    "Transport2DValidationSettings",
    # admission (F8)
    "read_centre_concentration_unguarded",
    "read_centre_concentration_with_admission",
    # boundary orientation (MIN-FIELD-SUPPORT-FOUNDATION)
    "classify_boundary_orientation",
    "boundary_orientation_report",
    # units
    "FIELD_UNIT",
    "LENGTH_UNIT",
    "DIFFUSIVITY_UNIT",
    "ANGULAR_RATE_UNIT",
    # errors
    "Transport2DError",
    "Transport2DConfigurationError",
    "Transport2DBindingError",
]
