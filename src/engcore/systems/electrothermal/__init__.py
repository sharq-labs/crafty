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
    AdmittedCoupledRun,
    CircuitSolver,
    CoupledElectroThermalSystem,
    CoupledStage,
    assess_coupled_applicability,
    build_coupled_twin,
    coupled_dependencies,
    coupled_problems,
    native_circuit_solver,
    nominal_plan,
    require_coupled_admission,
    run_admitted_coupling,
    scientific_environment,
    stage_problems,
    run_fixed_point_coupling,
)
# `COMPOSITE-SYSTEM0`. A second, materially heterogeneous composition in this
# pack: wire segments whose resistance is *computed* from a declared material
# property set and a declared geometry, in series with fixed loads. It reuses
# `engcore.coupling` unedited and edits nothing above. Its own
# ``DEPENDENCY_*`` labels are deliberately NOT re-exported: two modules in one
# pack legitimately name similar edges, and collapsing them into one name here
# would make which module a label came from unreadable. Import them from
# ``power_chain`` directly.
from .power_chain import (
    CHAIN_SCHEMA,
    FixedLoad,
    PowerChain,
    WireSegment,
    admit_power_chain,
    assess_run_applicability,
    build_chain_twin,
    chain_dependencies,
    chain_plan,
    chain_problems,
    initial_resistances,
    run_power_chain,
    wire_problems,
)

__all__ = [
    "AdmittedCoupledRun",
    "CHAIN_SCHEMA",
    "CircuitSolver",
    "CoupledElectroThermalSystem",
    "CoupledStage",
    "DEPENDENCY_HEAT",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_TEMPERATURE",
    "ElectroThermalResistor",
    "FixedLoad",
    "OpenLoopPass",
    "PowerChain",
    "WireSegment",
    "admit_power_chain",
    "assess_run_applicability",
    "build_chain_twin",
    "build_coupled_twin",
    "build_electrical_problem",
    "build_twin",
    "candidate_sources",
    "chain_dependencies",
    "chain_plan",
    "chain_problems",
    "coupled_dependencies",
    "coupled_problems",
    "electrothermal_dependencies",
    "electrothermal_problems",
    "initial_resistances",
    "assess_coupled_applicability",
    "native_circuit_solver",
    "nominal_plan",
    "require_coupled_admission",
    "run_admitted_coupling",
    "run_fixed_point_coupling",
    "scientific_environment",
    "run_open_loop_pass",
    "run_power_chain",
    "stage_problems",
    "wire_problems",
]
