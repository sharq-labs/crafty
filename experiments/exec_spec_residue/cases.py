"""The four frozen cases — the domains' own values, not new ones.

Every number here is taken from a value the repository already uses, so that the
residue is measured against production domains as they stand rather than against
a case invented to make a point:

``CIRCUIT``   the `HETERO-NGSPICE` divider (`tests/test_heterogeneous_ngspice.py`)
``SLAB``      the conduction benchmark's declared length/diffusivity/end time
``RUN``       the Seborg CSTR parameterization used by `domains/kinetics/cstr`
``CONDUCTOR`` a copper-like conductor for the resistance property model

This module imports domain packages deliberately: it holds the *ground truth*
artifacts that the encoding must be able to reproduce. The records-only reader
never imports it.
"""

from __future__ import annotations

from engcore.domains.electrical.dc import (
    DCCircuit,
    DCVoltageSource,
    ElectricalNode,
    Resistor,
)
from engcore.domains.electrical.material import TemperatureDependentConductor
from engcore.domains.kinetics.cstr import (
    IntegrationSettings,
    ReactorChemistry,
    ReactorOperation,
    ReactorRun,
)
from engcore.domains.thermal.conduction1d import ConductionSlab, SlabDiscretization
from engcore.scientific.units.quantity import Quantity

__all__ = ["CIRCUIT", "SLAB", "RUN", "CONDUCTOR", "CONDUCTOR_TEMPERATURE"]


def _q(magnitude: float, unit: str) -> Quantity:
    return Quantity(magnitude, unit)


#: A three-node divider: one ideal source and two series resistors. Chosen
#: because `HETERO-NGSPICE` already drives this exact circuit through both the
#: native MNA path and the external provider, so the provider half of this
#: milestone reuses an already-proven comparison rather than a new one.
CIRCUIT = DCCircuit(
    circuit_id="exec-spec-divider",
    nodes=(
        ElectricalNode("n0"),
        ElectricalNode("n1"),
        ElectricalNode("gnd", is_reference=True),
    ),
    resistors=(
        Resistor("R1", "n0", "n1", _q(10.0, "ohm")),
        Resistor("R2", "n1", "gnd", _q(20.0, "ohm")),
    ),
    voltage_sources=(DCVoltageSource("V1", "n0", "gnd", _q(12.0, "volt")),),
    description="Two-resistor divider driven by one ideal voltage source.",
)

#: The 1-D conduction benchmark. `n_cells` is even because the midpoint QoI is
#: read as a nodal value; the domain refuses an odd mesh.
SLAB = ConductionSlab(
    slab_id="exec-spec-slab",
    length=_q(1.0, "m"),
    diffusivity=_q(1.0e-4, "m**2/s"),
    end_time=_q(100.0, "s"),
    discretization=SlabDiscretization(n_cells=40, n_steps=200),
)

#: The non-isothermal CSTR, in the tabulated parameterization the domain uses.
RUN = ReactorRun(
    run_label="exec-spec-reactor",
    chemistry=ReactorChemistry(
        k0=_q(7.2e10 / 60.0, "1/s"),
        activation_energy=_q(8750.0 * 8.314462618, "J/mol"),
        heat_of_reaction=_q(-5.0e4, "J/mol"),
        density=_q(1000.0, "kg/m**3"),
        heat_capacity=_q(239.0, "J/(kg*K)"),
    ),
    operation=ReactorOperation(
        volume=_q(0.1, "m**3"),
        flow_rate=_q(0.1 / 60.0, "m**3/s"),
        feed_concentration=_q(1000.0, "mol/m**3"),
        feed_temperature=_q(350.0, "kelvin"),
        coolant_temperature=_q(290.0, "kelvin"),
        ua=_q(5.0e4 / 60.0, "W/K"),
        end_time=_q(600.0, "second"),
    ),
    initial_concentration=_q(500.0, "mol/m**3"),
    initial_temperature=_q(350.0, "kelvin"),
    integration=IntegrationSettings(
        method="BDF",
        rtol=1.0e-8,
        atol_concentration=1.0e-8,
        atol_temperature=1.0e-8,
        max_rhs_evaluations=2_000_000,
        n_output_points=501,
    ),
)

#: A conductor whose resistance depends on its temperature, and the temperature
#: it is evaluated at. The temperature is deliberately kept OUT of the conductor:
#: `material.py` binds `(conductor, temperature)` together, and separating them
#: here is part of what this milestone measures.
CONDUCTOR = TemperatureDependentConductor(
    component_id="exec-spec-conductor",
    reference_resistance=_q(10.0, "ohm"),
    temperature_coefficient=_q(3.9e-3, "1/K"),
    reference_temperature=_q(293.15, "kelvin"),
)

CONDUCTOR_TEMPERATURE = _q(350.0, "kelvin")
