"""Fluid ↔ Thermal scalar-reduction coupling — the platform's second coupled pair.

`FT-SCALAR-COUPLING`. A 2D steady scalar advection-diffusion PDE
(`engcore.domains.fluids.transport2d`) and a lumped thermal body
(`engcore.domains.thermal_lumped`), closed on two scalars:

    Fluid  -> Thermal :  Phi_D, the boundary-integrated diffusive efflux
    Thermal -> Fluid  :  D(T),  a temperature-dependent diffusivity

Module roles::

    properties.py  the two property claims that close the cycle — D(T) and
                   hA(Phi_D) — each one model + one realization + one problem
                   builder + one evaluator, and no property hierarchy
    reference.py   the closed-form fixed point of the COUPLED system.
                   Verification side only; imports `math` and nothing else
    coupled.py     the system declaration, the four QuantityDependency edges,
                   the plan, the executors, and the entry point. The loop
                   itself is `electrothermal.coupled.run_fixed_point`,
                   imported unedited

See `docs/fluid-thermal-scalar-coupling-prereg.md` for what was committed in
advance and `docs/fluid-thermal-scalar-coupling-evidence.md` for what executed.
"""

from __future__ import annotations

from .coupled import (
    DEPENDENCY_CONDUCTANCE,
    DEPENDENCY_DIFFUSIVITY,
    DEPENDENCY_EFFLUX,
    DEPENDENCY_TEMPERATURE,
    THERMAL_ADMISSION_REQUIREMENTS,
    FluidSlice,
    FluidThermalSystem,
    HeatedBody,
    coupled_dependencies,
    coupled_problems,
    nominal_plan,
    run_fluid_thermal_coupling,
    sweep_timings,
)
from .properties import (
    DIFFUSIVITY_METRIC,
    WALL_CONDUCTANCE_METRIC,
    WALL_EFFLUX,
    DiffusivityPropertySolver,
    GasDiffusivity,
    POWER_LAW_DIFFUSIVITY_MODEL,
    POWER_LAW_DIFFUSIVITY_REALIZATION,
    WALL_CONDUCTANCE_MODEL,
    WALL_CONDUCTANCE_REALIZATION,
    WallConductanceSolver,
    WallCoupling,
    build_diffusivity_problem,
    build_wall_conductance_problem,
    property_model_registry,
    property_realizations,
)
from .reference import (
    EXACT_EFFLUX_PER_DIFFUSIVITY,
    REFERENCE_EXPRESSION,
    REFERENCE_ID,
    coupled_fixed_point,
    coupled_residual,
    fixed_point_identity_residual,
    picard_gain,
    reference_conductance,
)

__all__ = [
    # system declaration
    "FluidThermalSystem",
    "FluidSlice",
    "HeatedBody",
    # composition
    "coupled_problems",
    "coupled_dependencies",
    "nominal_plan",
    "run_fluid_thermal_coupling",
    "sweep_timings",
    "DEPENDENCY_EFFLUX",
    "DEPENDENCY_CONDUCTANCE",
    "DEPENDENCY_TEMPERATURE",
    "DEPENDENCY_DIFFUSIVITY",
    "THERMAL_ADMISSION_REQUIREMENTS",
    # property claims
    "GasDiffusivity",
    "WallCoupling",
    "build_diffusivity_problem",
    "build_wall_conductance_problem",
    "DiffusivityPropertySolver",
    "WallConductanceSolver",
    "POWER_LAW_DIFFUSIVITY_MODEL",
    "POWER_LAW_DIFFUSIVITY_REALIZATION",
    "WALL_CONDUCTANCE_MODEL",
    "WALL_CONDUCTANCE_REALIZATION",
    "DIFFUSIVITY_METRIC",
    "WALL_CONDUCTANCE_METRIC",
    "WALL_EFFLUX",
    "property_model_registry",
    "property_realizations",
    # the independent coupled reference
    "coupled_fixed_point",
    "coupled_residual",
    "fixed_point_identity_residual",
    "picard_gain",
    "reference_conductance",
    "EXACT_EFFLUX_PER_DIFFUSIVITY",
    "REFERENCE_ID",
    "REFERENCE_EXPRESSION",
]
