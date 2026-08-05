"""Electrical DC V0 — linear resistive steady-state circuit analysis.

Scope: resistors, ideal independent DC voltage and current sources, and an
explicitly declared reference node. Solved by modified nodal analysis over
SciPy's dense linear solve.

Not in scope: capacitors, inductors, transients, AC/frequency domain,
diodes, transistors, dependent sources, SPICE netlists, distributed effects.
This is a validated linear resistive DC analysis domain; it is not a SPICE
replacement.
"""

from .circuit import DCCircuit
from .components import (
    DCCurrentSource,
    DCVoltageSource,
    ElectricalNode,
    Resistor,
)
from .mna import PreparedDCSystem, assemble
from .models import (
    DC_MODELS,
    ELECTRICAL_DC_LINEAR,
    IDEAL_VOLTAGE_SOURCE_MODEL,
    KCL_MODEL,
    RESISTOR_OHM_MODEL,
    build_dc_model_registry,
    dc_solver_capabilities,
)
from .problem import (
    build_dc_problem,
    resistor_relation_problem,
    voltage_source_relation_problem,
)
from .solver import ElectricalDCError, ElectricalDCSolver, solve_circuit
from .validation import DCValidationSettings, build_validation_report

__all__ = [
    "DCCircuit",
    "ElectricalNode",
    "Resistor",
    "DCVoltageSource",
    "DCCurrentSource",
    "PreparedDCSystem",
    "assemble",
    "DC_MODELS",
    "RESISTOR_OHM_MODEL",
    "KCL_MODEL",
    "IDEAL_VOLTAGE_SOURCE_MODEL",
    "ELECTRICAL_DC_LINEAR",
    "build_dc_model_registry",
    "dc_solver_capabilities",
    "build_dc_problem",
    "resistor_relation_problem",
    "voltage_source_relation_problem",
    "ElectricalDCSolver",
    "ElectricalDCError",
    "solve_circuit",
    "DCValidationSettings",
    "build_validation_report",
]
