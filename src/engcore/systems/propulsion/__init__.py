"""Propulsion system pack: one machine in three physics at once.

`PROPULSION0`. A series electromechanical drive — source, feed lead, machine,
return lead, mechanical load — in which one motor participates simultaneously
in electrical, rotational-mechanical and thermal physics while remaining
coupled to material-dependent wires.

Three modules, split by what each owns:

======================  ==================================================
:mod:`.materials`       one material declaration supplying resistivity,
                        TCR, density and specific heat, and the thermal
                        mass it derives
:mod:`.models`          the three claims that belong to the assembly: the
                        binary series join, the two-channel machine heat,
                        and the closed-form drive operating point
:mod:`.drive`           the declarations, the composition, the two
                        enforcement points and the run
======================  ==================================================

The reusable rotational physics is **not** here: it is in
``engcore.domains.mechanical_rotational``, because a back-EMF law and a torque
balance are claims about any machine and any shaft, not about this topology.

Nothing in this pack edits ``engcore.scientific`` or ``engcore.coupling``, and
nothing in it re-publishes a name either of those owns.
"""

from .drive import (
    DriveElement,
    DriveRun,
    DriveWire,
    EnergyAccounting,
    Motor,
    PropulsionDrive,
    ThermalDeclaration,
    admit_drive,
    assess_run_applicability,
    build_drive_twin,
    compose,
    declared_problem_ids,
    derive_thermal_masses,
    drive_dependencies,
    drive_plan,
    drive_problems,
    native_circuit_solver,
    reconcile_drive_energy,
    run_propulsion_drive,
)
from .materials import (
    ALUMINIUM_THERMOPHYSICAL,
    CONDUCTOR_THERMAL_MASS_MODEL,
    COPPER_THERMOPHYSICAL,
    ThermophysicalConductor,
)
from .models import (
    DRIVE_OPERATING_POINT_MODEL,
    MOTOR_HEAT_GENERATION_MODEL,
    SERIES_LOOP_RESISTANCE_MODEL,
)

__all__ = [
    "ALUMINIUM_THERMOPHYSICAL",
    "CONDUCTOR_THERMAL_MASS_MODEL",
    "COPPER_THERMOPHYSICAL",
    "DRIVE_OPERATING_POINT_MODEL",
    "DriveElement",
    "DriveRun",
    "DriveWire",
    "EnergyAccounting",
    "MOTOR_HEAT_GENERATION_MODEL",
    "Motor",
    "PropulsionDrive",
    "SERIES_LOOP_RESISTANCE_MODEL",
    "ThermalDeclaration",
    "ThermophysicalConductor",
    "admit_drive",
    "assess_run_applicability",
    "build_drive_twin",
    "compose",
    "declared_problem_ids",
    "derive_thermal_masses",
    "drive_dependencies",
    "drive_plan",
    "drive_problems",
    "native_circuit_solver",
    "reconcile_drive_energy",
    "run_propulsion_drive",
]
