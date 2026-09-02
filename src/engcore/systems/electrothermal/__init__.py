"""Electro-thermal system pack — cross-domain composition, no domain physics.

A *system* pack, not a domain pack. It composes the electrical, material and
thermal packs and owns no physics of its own, which is the only place
cross-domain wiring is allowed to live: a domain module that orchestrated the
system graph would have to know about the other domains.
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

__all__ = [
    "DEPENDENCY_HEAT",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_TEMPERATURE",
    "ElectroThermalResistor",
    "OpenLoopPass",
    "build_electrical_problem",
    "build_twin",
    "candidate_sources",
    "electrothermal_dependencies",
    "electrothermal_problems",
    "run_open_loop_pass",
]
