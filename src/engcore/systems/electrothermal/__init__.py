"""Electro-thermal system pack — cross-domain composition, no domain physics.

A *system* pack, not a domain pack. It composes the electrical, material and
thermal packs and owns no physics of its own, which is the only place
cross-domain wiring is allowed to live: a domain module that orchestrated the
system graph would have to know about the other domains.

The generic coupling machinery this pack minted — the plan, the torn endpoint,
the outcome enum, the iteration and run records, the graph readers and the
fixed-point loop — was relocated to :mod:`engcore.coupling` by
`COUPLING-PACK-RELOCATION` once a second production consumer had executed
against it unedited. It is **not** re-exported here: a domain-named pack
publishing a domain-neutral record is the false ownership that milestone
removed. Import it from ``engcore.coupling``.
"""

from .resistor_body import (
    DEPENDENCY_HEAT,
    DEPENDENCY_RESISTANCE,
    DEPENDENCY_TEMPERATURE,
    ElectroThermalResistor,
    OpenLoopPass,
    build_electrical_problem,
    build_twin,
    candidate_sources,
    electrothermal_dependencies,
    electrothermal_problems,
    run_open_loop_pass,
)
from .coupled import (
    CircuitSolver,
    CoupledElectroThermalSystem,
    CoupledStage,
    build_coupled_twin,
    coupled_dependencies,
    coupled_problems,
    native_circuit_solver,
    nominal_plan,
    stage_problems,
    run_fixed_point_coupling,
)

__all__ = [
    "CircuitSolver",
    "CoupledElectroThermalSystem",
    "CoupledStage",
    "DEPENDENCY_HEAT",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_TEMPERATURE",
    "ElectroThermalResistor",
    "OpenLoopPass",
    "build_coupled_twin",
    "build_electrical_problem",
    "build_twin",
    "candidate_sources",
    "coupled_dependencies",
    "coupled_problems",
    "electrothermal_dependencies",
    "electrothermal_problems",
    "native_circuit_solver",
    "nominal_plan",
    "run_fixed_point_coupling",
    "run_open_loop_pass",
    "stage_problems",
]
