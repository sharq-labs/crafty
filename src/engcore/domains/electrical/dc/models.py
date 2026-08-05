"""Scientific model records for linear DC circuit analysis.

Three models are declared, each a versioned scientific claim with typed
inputs and outputs, declared assumptions and a validity domain. They are
*representations*: nothing here executes: execution belongs to the solver.

Honesty notes
-------------
* ``validation_status`` is ``SELF_CONSISTENT``, not ``BENCHMARK_VALIDATED``
  and certainly not ``EXPERIMENTALLY_VALIDATED``. Passing unit tests against
  hand-derived analytical values shows internal consistency; it is not an
  external benchmark process and involves no measurement.
* ``references`` are deliberately empty. These relations are standard
  textbook circuit theory, but this repository has no curated reference set
  yet and citations will not be invented. Reference curation is deferred.
"""

from __future__ import annotations

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
from ....scientific.models.registry import ModelRegistry
from ....scientific.solvers.capability import CoreCapabilities, SolverCapability
from ....scientific.units.quantity import Quantity

#: Domain capability. Declared here, in the electrical package — the
#: universal ``CoreCapabilities`` is never extended with domain constants.
ELECTRICAL_DC_LINEAR = SolverCapability(
    "electrical:dc_linear",
    "Linear resistive DC (steady-state) circuit analysis",
)

DC_MODEL_VERSION = "0.1.0"

_DC_ASSUMPTIONS = (
    "lumped-element circuit (no distributed or field effects)",
    "steady-state DC operation (no transients, no reactive elements)",
    "linear, time-invariant elements",
    "ideal independent sources (no internal impedance unless modelled explicitly)",
    "temperature-independent resistance",
    "no parasitics",
)


RESISTOR_OHM_MODEL = ScientificModelDefinition(
    model_id="electrical.dc.resistor_ohm",
    version=DC_MODEL_VERSION,
    name="Resistor constitutive relation (Ohm's law)",
    domain="electrical",
    model_type=ModelType.CONSTITUTIVE_MODEL,
    description=(
        "Relates the voltage across an ideal linear resistor to the current "
        "through it: V = I R, with V measured node_a -> node_b and I "
        "positive in the same direction."
    ),
    inputs=(
        ModelInputSpec(
            name="resistance",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar="ohm",
            description="Element resistance; strictly positive in V0.",
        ),
        ModelInputSpec(
            name="voltage_across",
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar="volt",
            description="V(node_a) - V(node_b).",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="current_through",
            unit_exemplar="ampere",
            description="Current node_a -> node_b.",
        ),
        ModelOutputSpec(
            metric="dissipated_power",
            unit_exemplar="watt",
            description="Absorbed power, V*I = I^2 R (non-negative).",
        ),
    ),
    assumptions=_DC_ASSUMPTIONS,
    validity=ValidityDomain(
        conditions=(
            RangeCondition(
                name="resistance",
                minimum=Quantity(0.0, "ohm"),
                minimum_inclusive=False,      # strictly R > 0
                description=(
                    "Strictly positive resistance; zero is a short and "
                    "negative resistance is an active device, both outside "
                    "V0 scope."
                ),
            ),
        ),
        description="Linear passive resistive operation.",
    ),
    required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


KCL_MODEL = ScientificModelDefinition(
    model_id="electrical.dc.kcl",
    version=DC_MODEL_VERSION,
    name="Kirchhoff current law (nodal charge balance)",
    domain="electrical",
    model_type=ModelType.FUNDAMENTAL_RELATION,
    description=(
        "Algebraic current balance at a node: the signed sum of currents "
        "leaving a node through all connected elements is zero. Expresses "
        "charge conservation for a lumped circuit."
    ),
    inputs=(
        ModelInputSpec(
            name="node_voltage",
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar="volt",
            description="Potential of the node relative to the reference.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="net_current_out",
            unit_exemplar="ampere",
            description="Signed sum of currents leaving the node; zero when satisfied.",
        ),
    ),
    assumptions=_DC_ASSUMPTIONS + (
        "no charge accumulation at nodes (lumped assumption)",
    ),
    validity=ValidityDomain(
        description=(
            "Valid for lumped circuits; not validated for distributed or "
            "high-frequency regimes where the lumped assumption fails."
        )
    ),
    required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


IDEAL_VOLTAGE_SOURCE_MODEL = ScientificModelDefinition(
    model_id="electrical.dc.ideal_voltage_source",
    version=DC_MODEL_VERSION,
    name="Ideal independent DC voltage source relation",
    domain="electrical",
    model_type=ModelType.APPROXIMATION,
    description=(
        "Imposes V(positive_node) - V(negative_node) = source_voltage "
        "irrespective of the current drawn. An idealisation: real sources "
        "have internal impedance and finite compliance."
    ),
    inputs=(
        ModelInputSpec(
            name="source_voltage",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar="volt",
            description="Imposed terminal voltage difference.",
        ),
        ModelInputSpec(
            name="terminal_voltage",
            source_kind=InputSourceKind.VARIABLE,
            unit_exemplar="volt",
            description="V(positive_node) - V(negative_node).",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="source_current",
            unit_exemplar="ampere",
            description=(
                "Branch current leaving the positive node through the "
                "source; negative when the source delivers power."
            ),
        ),
    ),
    assumptions=_DC_ASSUMPTIONS + (
        "zero internal impedance",
        "unlimited current compliance",
    ),
    validity=ValidityDomain(
        description=(
            "Idealisation; not validated against real source behaviour near "
            "current or power limits."
        )
    ),
    required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


IDEAL_CURRENT_SOURCE_MODEL = ScientificModelDefinition(
    model_id="electrical.dc.ideal_current_source",
    version=DC_MODEL_VERSION,
    name="Ideal independent DC current source relation",
    domain="electrical",
    model_type=ModelType.APPROXIMATION,
    description=(
        "Imposes a fixed current from_node -> to_node inside the source, "
        "irrespective of the terminal voltage that develops across it. An "
        "idealisation: real sources have finite output impedance and a "
        "limited compliance voltage."
    ),
    inputs=(
        ModelInputSpec(
            name="source_current",
            source_kind=InputSourceKind.PARAMETER,
            unit_exemplar="ampere",
            description="Imposed current, positive from_node -> to_node.",
        ),
    ),
    outputs=(
        ModelOutputSpec(
            metric="terminal_voltage",
            unit_exemplar="volt",
            description=(
                "V(from_node) - V(to_node) that the surrounding network "
                "develops across the source."
            ),
        ),
    ),
    assumptions=_DC_ASSUMPTIONS + (
        "infinite output impedance",
        "unlimited compliance voltage",
    ),
    validity=ValidityDomain(
        description=(
            "Idealisation; not validated against real source behaviour near "
            "compliance limits."
        )
    ),
    required_capabilities=frozenset({ELECTRICAL_DC_LINEAR.name}),
    validation_status=ModelValidationStatus.SELF_CONSISTENT,
)


DC_MODELS = (
    KCL_MODEL,
    RESISTOR_OHM_MODEL,
    IDEAL_VOLTAGE_SOURCE_MODEL,
    IDEAL_CURRENT_SOURCE_MODEL,
)


def models_for_circuit(circuit) -> tuple[ScientificModelDefinition, ...]:
    """The models a specific circuit actually invokes.

    Attaching every domain model to every circuit would overstate what a
    result depends on: a resistor-only network makes no claim about ideal
    voltage sources, and a reader auditing that result should not be told it
    does. Order is fixed, so the tuple is deterministic.

    Kirchhoff's current law is always present — it is the balance every
    nodal analysis solves, regardless of which element types appear.
    """
    active: list[ScientificModelDefinition] = [KCL_MODEL]
    if circuit.resistors:
        active.append(RESISTOR_OHM_MODEL)
    if circuit.voltage_sources:
        active.append(IDEAL_VOLTAGE_SOURCE_MODEL)
    if circuit.current_sources:
        active.append(IDEAL_CURRENT_SOURCE_MODEL)
    return tuple(active)


def assumptions_for_models(models) -> tuple[str, ...]:
    """Deterministic, de-duplicated union of the models' assumptions.

    First-seen order is preserved so the same active set always yields the
    same sequence — a result's assumption list must not depend on set
    iteration order.
    """
    seen: dict[str, None] = {}
    for model in models:
        for assumption in model.assumptions:
            seen.setdefault(assumption, None)
    return tuple(seen)


def build_dc_model_registry() -> ModelRegistry:
    """A fresh registry containing the DC models.

    Returns a new instance every call: the platform has no global mutable
    model registry, so a caller's model set can never be mutated elsewhere.
    """
    return ModelRegistry(DC_MODELS)


def dc_solver_capabilities() -> frozenset[SolverCapability]:
    """What an Electrical DC solver declares it can do.

    Both the domain capability and the mathematical shape it reduces to: a
    linear system. The latter is what makes the solver discoverable to a
    future planner reasoning about problem form rather than domain.
    """
    return frozenset({ELECTRICAL_DC_LINEAR, CoreCapabilities.LINEAR_SYSTEM})
