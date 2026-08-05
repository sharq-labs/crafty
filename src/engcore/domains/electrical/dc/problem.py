"""Mapping: DCCircuit -> ScientificProblem.

The universal IR describes *what is being computed*; the circuit describes
*how the system is wired*. This module translates the former from the latter
without smuggling topology into the IR: the problem carries the quantities
and their units, the model references and the required capabilities, while
connectivity travels to the solver through the prepared-solve payload.

Naming convention for the IR entries (stable, machine-parseable):

===========================  ===========================================
``V:<node_id>``              variable, volt, OBSERVABLE — node potential
``I:<vsource_id>``           variable, ampere, OBSERVABLE — branch current
``R:<resistor_id>``          parameter, ohm — element resistance
``Vs:<vsource_id>``          parameter, volt — imposed source voltage
``Is:<isource_id>``          parameter, ampere — imposed source current
``reference_node``           parameter, categorical — declared datum
``analysis_type``            parameter, categorical — ``dc_steady_state``
===========================  ===========================================

Node voltages and source currents are OBSERVABLE, not DESIGN: nothing in a
DC analysis is free to be chosen. A future study that *does* vary a
resistance would add that resistance as a DESIGN variable; the analysis
problem itself has none.
"""

from __future__ import annotations

from ....scientific.ir.problem import ModelReference, ScientificProblem
from ....scientific.ir.values import CategoricalValue
from ....scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from .circuit import DCCircuit
from .components import CURRENT_UNIT, RESISTANCE_UNIT, VOLTAGE_UNIT
from .models import DC_MODELS, ELECTRICAL_DC_LINEAR

ANALYSIS_TYPE = "dc_steady_state"


def node_voltage_name(node_id: str) -> str:
    return f"V:{node_id}"


def source_current_name(component_id: str) -> str:
    return f"I:{component_id}"


def resistance_name(component_id: str) -> str:
    return f"R:{component_id}"


def source_voltage_name(component_id: str) -> str:
    return f"Vs:{component_id}"


def source_current_value_name(component_id: str) -> str:
    return f"Is:{component_id}"


def build_dc_problem(
    circuit: DCCircuit,
    *,
    problem_id: str | None = None,
    objectives=(),
    constraints=(),
) -> ScientificProblem:
    """Build the universal problem statement for a DC circuit analysis.

    ``objectives`` and ``constraints`` are supplied by the caller only —
    a plain analysis declares none, and the domain never invents them.
    """
    variables: list[ScientificVariable] = []
    parameters: list[ScientificParameter] = []

    # Unknowns of the analysis: every non-reference node potential.
    for node_id in circuit.non_reference_node_ids:
        variables.append(
            ScientificVariable(
                name=node_voltage_name(node_id),
                unit=VOLTAGE_UNIT,
                role=VariableRole.OBSERVABLE,
                description=f"Potential of node {node_id!r} w.r.t. the reference",
            )
        )

    # One additional unknown per ideal voltage source (its branch current).
    for source in circuit.ordered_voltage_sources:
        variables.append(
            ScientificVariable(
                name=source_current_name(source.component_id),
                unit=CURRENT_UNIT,
                role=VariableRole.OBSERVABLE,
                description=(
                    f"Current leaving the positive node through "
                    f"{source.component_id!r}"
                ),
            )
        )

    # Configured element values are parameters, carrying their units.
    for resistor in sorted(circuit.resistors, key=lambda r: r.component_id):
        parameters.append(
            ScientificParameter(
                name=resistance_name(resistor.component_id),
                value=resistor.resistance,
                description=(
                    f"Resistance of {resistor.component_id!r} between "
                    f"{resistor.node_a!r} and {resistor.node_b!r}"
                ),
            )
        )
    for source in circuit.ordered_voltage_sources:
        parameters.append(
            ScientificParameter(
                name=source_voltage_name(source.component_id),
                value=source.voltage,
                description=(
                    f"Imposed voltage of {source.component_id!r}: "
                    f"V({source.positive_node}) - V({source.negative_node})"
                ),
            )
        )
    for source in sorted(circuit.current_sources, key=lambda s: s.component_id):
        parameters.append(
            ScientificParameter(
                name=source_current_value_name(source.component_id),
                value=source.current,
                description=(
                    f"Imposed current of {source.component_id!r}: "
                    f"{source.from_node} -> {source.to_node}"
                ),
            )
        )

    # Typed categorical parameters: the datum and the analysis regime are
    # scientific facts about the problem, not metadata.
    parameters.append(
        ScientificParameter(
            name="reference_node",
            value=CategoricalValue(
                circuit.reference_node,
                vocabulary=tuple(sorted(circuit.node_ids)),
            ),
            description="Explicitly declared voltage datum",
        )
    )
    parameters.append(
        ScientificParameter(
            name="analysis_type",
            value=CategoricalValue(
                ANALYSIS_TYPE, vocabulary=(ANALYSIS_TYPE,)
            ),
            description="Linear steady-state DC analysis",
        )
    )

    return ScientificProblem(
        problem_id=problem_id or f"electrical_dc:{circuit.circuit_id}",
        name=f"DC analysis of circuit {circuit.circuit_id!r}",
        description=circuit.description or (
            "Linear resistive DC steady-state analysis by modified nodal "
            "analysis."
        ),
        variables=tuple(variables),
        parameters=tuple(parameters),
        objectives=tuple(objectives),
        constraints=tuple(constraints),
        models=tuple(
            ModelReference(model.model_id, model.version) for model in DC_MODELS
        ),
        required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
        validation_requirements=frozenset(
            {
                "dimensional_consistency",
                "linear_system_residual",
                "kirchhoff_current_law",
                "resistor_constitutive_relation",
                "voltage_source_relation",
                "power_balance",
            }
        ),
    )


def resistor_relation_problem(resistor) -> ScientificProblem:
    """A one-element problem stating a resistor's constitutive relation.

    Used to *bind* :data:`RESISTOR_OHM_MODEL` to a concrete component: the
    model declares generic physical names (``resistance``,
    ``voltage_across``) while a circuit problem necessarily uses per-instance
    names, so binding is verified per component rather than circuit-wide.
    """
    return ScientificProblem(
        problem_id=f"electrical_dc_resistor:{resistor.component_id}",
        name=f"Constitutive relation of resistor {resistor.component_id!r}",
        variables=(
            ScientificVariable(
                name="voltage_across",
                unit=VOLTAGE_UNIT,
                role=VariableRole.OBSERVABLE,
            ),
        ),
        parameters=(
            ScientificParameter(name="resistance", value=resistor.resistance),
        ),
        models=(
            ModelReference("electrical.dc.resistor_ohm", "0.1.0"),
        ),
        required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    )


def voltage_source_relation_problem(source) -> ScientificProblem:
    """A one-element problem stating an ideal source's imposed relation."""
    return ScientificProblem(
        problem_id=f"electrical_dc_vsource:{source.component_id}",
        name=f"Imposed relation of voltage source {source.component_id!r}",
        variables=(
            ScientificVariable(
                name="terminal_voltage",
                unit=VOLTAGE_UNIT,
                role=VariableRole.OBSERVABLE,
            ),
        ),
        parameters=(
            ScientificParameter(name="source_voltage", value=source.voltage),
        ),
        models=(
            ModelReference("electrical.dc.ideal_voltage_source", "0.1.0"),
        ),
        required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    )
