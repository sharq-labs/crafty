"""A power chain: Source -> Wire A -> Load -> Wire B, with self-heating wires.

`COMPOSITE-SYSTEM0`. The consumer that answers whether representing a real
engineered system as reusable component instances with material, state and
connection semantics forces anything new::

    +12 V ──[ wire_A ]──[ load ]──[ wire_B ]── gnd
                │                     │
             (body_A)              (body_B)

Per wire, four declared edges close a 4-cycle::

     electrical.resistor_power:<cid> ──▶ thermal.heat_input
     thermal.final_temperature       ──▶ resistivity.temperature      (TORN)
     resistivity.resistivity         ──▶ geometric_resistance.resistivity
     geometric_resistance.resistance ──▶ electrical.R:<cid>

Seven separately posed problems for the two-wire chain, eight declared
dependencies, two torn endpoints, one twin, and **not one line of new coupling
machinery**: :func:`~engcore.coupling.run_fixed_point` receives a dependency
graph and a dispatch table and runs the iteration without being able to name
either. The iteration below contains no electrical and no thermal branch.

What is different from ``coupled.py``, and why it is a separate module
---------------------------------------------------------------------
``CoupledElectroThermalSystem`` is N *numerically declared* conductors in
series: a caller supplies a reference resistance. This chain declares what each
wire is **made of** and **how big it is**, and the resistance is a *computed
result* of two declared models. That is the whole difference, and it is why the
existing pack is untouched — including every number the API/MCP surface returns
through ``electrothermal.series_self_heating/1``.

Two element kinds, deliberately
-------------------------------
:class:`WireSegment` carries a material, a geometry and a thermal body.
:class:`FixedLoad` carries a resistance and nothing else — no material, no
geometry, no body. A heterogeneous series is what makes the chain a *system*
rather than N copies of one thing, and the union is discriminated by type in a
**system pack**, never in universal core.

The load is thermally isolated on purpose, and the reason is what this
milestone is measuring rather than a limit of any contract. A ``FixedLoad``
declares a temperature-independent resistance, so a thermal body attached to
it would be a **dead-end participant**: nothing downstream reads its state, and
it would change no answer while adding a problem, an edge and an executor to
every record. Representable, and deliberately not represented — this milestone
changes exactly one property, and everything else has to hold still for the
differential to mean anything.

It is NOT a fan-in refusal. A load's body would pose its own thermal problem
with its own ``heat_input`` endpoint fed by one edge, so
:class:`~engcore.coupling.FixedPointCouplingPlan` would admit it. Fan-in
becomes the wall only when two sources feed **one** endpoint — two heat paths
into one body — which nothing here does.

What this module does NOT introduce
-----------------------------------
No ``ComponentInstance``, no ``Port``, no ``Connector``, no
``SystemDefinition``, no ``MaterialBinding``, no composite graph that is both
physical topology and execution schedule. Topology stays in ``DCCircuit``,
where it already was; dataflow stays in ``QuantityDependency``, where it
already was; the execution order is *computed* from the declared edges by
:func:`~engcore.coupling.execution_order` and is written down nowhere.

Series, and what that means for the multiplicity result
--------------------------------------------------------
The wires are in series, so the current is common and changing wire A's
material **does** move wire B's numbers. That is coupling, not aliasing, and a
topology in which two instances could not influence each other would exercise
nothing. What must not happen — and is asserted — is that wire B's
*declaration*, *material property set*, *problems* or *provenance* are touched
by a change to wire A. Wire B's resistance must remain exactly
``rho_B(T_B) L_B / A_B`` for wire B's own material.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ...coupling import (
    CoupledRun,
    FixedPointCouplingPlan,
    TornEndpoint,
    run_fixed_point,
)
from ...domains import thermal_lumped as lump
from ...domains.electrical import conductor_material as cmat
from ...domains.electrical.dc import (
    DCCircuit,
    DCVoltageSource,
    ElectricalNode,
    Resistor,
    build_dc_problem,
)
# The DC package publishes no metric-name helper (MIN-FOUNDATION-ET finding
# C-11); the sibling modules in this pack already reuse this constant rather
# than re-deriving the convention, and so does this one.
from ...domains.electrical.dc.problem import resistance_name
from ...scientific.composition import QuantityDependency
from ...scientific.errors import InvalidScientificProblem
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.models.definition import ValidityAssessment
from ...scientific.results.provenance import ExecutionBinding, ProvenanceRecord
from ...scientific.results.result import ScientificResult
from ...scientific.results.uncertainty import Uncertainty
from ...scientific.serialization import require_schema, schema_string
from ...scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
)
from ...scientific.units.quantity import Quantity
from .coupled import CircuitSolver, native_circuit_solver
from .resistor_body import RESISTOR_POWER_METRIC

__all__ = [
    "CHAIN_SCHEMA",
    "DEPENDENCY_GEOMETRY",
    "DEPENDENCY_HEAT",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_TEMPERATURE",
    "FixedLoad",
    "PowerChain",
    "WireSegment",
    "admit_power_chain",
    "assess_run_applicability",
    "build_chain_twin",
    "chain_dependencies",
    "chain_plan",
    "chain_problems",
    "compose",
    "declared_problem_ids",
    "initial_resistances",
    "run_power_chain",
    "wire_problems",
]

CHAIN_SCHEMA = schema_string("electrothermal_power_chain")

#: Prose labels for the declared edges. Nothing branches on them.
DEPENDENCY_HEAT = "joule-dissipation-heats-body"
DEPENDENCY_TEMPERATURE = "body-temperature-sets-material-state"
DEPENDENCY_GEOMETRY = "material-resistivity-sets-conductor-geometry-input"
DEPENDENCY_RESISTANCE = "conductor-resistance-sets-circuit-element"

SOURCE_ID = "V1"
REFERENCE_NODE = "gnd"


# =====================================================================
# Element declarations
# =====================================================================

@dataclass(frozen=True)
class WireSegment:
    """One conductor and the thermal body it dissipates into.

    The two share a ``component_id``, and that co-identity remains a
    **convention of this pack**: no universal record states that a conductor
    declaration and a body declaration describe one physical object. A
    ``ComponentInstance`` to state it was tested and deferred at arity 1 by
    `MIN-FOUNDATION-ET`, run at arity 2 by `ET-VERTICAL`, and is deferred again
    here — now with a material and a geometry attached, which is the case that
    was supposed to force it and does not.
    """

    conductor: cmat.MaterialConductor
    body: lump.ThermalBody

    def __post_init__(self) -> None:
        if not isinstance(self.conductor, cmat.MaterialConductor):
            raise InvalidScientificProblem(
                "a wire segment requires a MaterialConductor"
            )
        if not isinstance(self.body, lump.ThermalBody):
            raise InvalidScientificProblem("a wire segment requires a ThermalBody")
        if self.conductor.component_id != self.body.body_id:
            raise InvalidScientificProblem(
                f"conductor {self.conductor.component_id!r} and body "
                f"{self.body.body_id!r} must share an id in this system pack; "
                f"no universal record states that two declarations describe "
                f"one physical object, so this pack keeps them aligned by "
                f"construction"
            )

    @property
    def component_id(self) -> str:
        return self.conductor.component_id

    @property
    def material(self) -> cmat.ConductorMaterial:
        return self.conductor.material

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "wire_segment",
            "conductor": self.conductor.to_dict(),
            "body": _body_to_dict(self.body),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "WireSegment":
        return cls(
            conductor=cmat.MaterialConductor.from_dict(payload["conductor"]),
            body=_body_from_dict(payload["body"]),
        )


@dataclass(frozen=True)
class FixedLoad:
    """A series element of declared, temperature-independent resistance.

    It carries no material, no geometry and no thermal body. That is not an
    oversight: this milestone changes **one** legitimate component property —
    the wire material — and everything else in the chain has to hold still for
    the differential to mean anything.
    """

    component_id: str
    resistance: Quantity

    def __post_init__(self) -> None:
        component_id = str(self.component_id).strip()
        if not component_id:
            raise InvalidScientificProblem("a load requires a component_id")
        object.__setattr__(self, "component_id", component_id)
        if not isinstance(self.resistance, Quantity):
            raise InvalidScientificProblem(
                f"load {component_id!r} resistance must be a Quantity"
            )
        self.resistance.require_compatible(
            cmat.RESISTANCE_UNIT, context=f"load {component_id!r} resistance"
        )
        if self.resistance.magnitude_in(cmat.RESISTANCE_UNIT) <= 0.0:
            raise InvalidScientificProblem(
                f"load {component_id!r} requires a strictly positive resistance"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "fixed_load",
            "component_id": self.component_id,
            "resistance": self.resistance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FixedLoad":
        return cls(
            component_id=payload["component_id"],
            resistance=Quantity.from_dict(payload["resistance"]),
        )


#: ``ThermalBody`` predates this milestone and carries no ``to_dict``. Rather
#: than edit a frozen sibling domain for one consumer's serialization, this
#: pack writes the body's own declared fields and reads them back. Recorded as
#: a finding: the electro-thermal packs serialize a body **locally**, and the
#: day a second consumer needs the same thing, the method belongs on the
#: record rather than in two packs.
def _body_to_dict(body: lump.ThermalBody) -> dict[str, Any]:
    return {
        "body_id": body.body_id,
        "heat_capacity": body.heat_capacity.to_dict(),
        "ambient_conductance": body.ambient_conductance.to_dict(),
        "ambient_temperature": body.ambient_temperature.to_dict(),
        "initial_temperature": body.initial_temperature.to_dict(),
        "duration": body.duration.to_dict(),
    }


def _body_from_dict(payload: Mapping[str, Any]) -> lump.ThermalBody:
    return lump.ThermalBody(
        body_id=payload["body_id"],
        heat_capacity=Quantity.from_dict(payload["heat_capacity"]),
        ambient_conductance=Quantity.from_dict(payload["ambient_conductance"]),
        ambient_temperature=Quantity.from_dict(payload["ambient_temperature"]),
        initial_temperature=Quantity.from_dict(payload["initial_temperature"]),
        duration=Quantity.from_dict(payload["duration"]),
    )


_ELEMENT_READERS = {
    "wire_segment": WireSegment.from_dict,
    "fixed_load": FixedLoad.from_dict,
}


# =====================================================================
# The chain
# =====================================================================

@dataclass(frozen=True)
class PowerChain:
    """An ordered series of elements across one ideal DC source.

    Order is declared, not inferred, and it is what determines the node
    assignment. Note honestly what the exercised topology can and cannot
    falsify: in a series loop across an ideal source the current is common, so
    *permuting* the elements changes no number. The ordering is therefore a
    real declared fact that this consumer alone does not put under test.
    """

    chain_id: str
    source_voltage: Quantity
    elements: tuple[WireSegment | FixedLoad, ...]

    def __post_init__(self) -> None:
        chain_id = str(self.chain_id).strip()
        if not chain_id:
            raise InvalidScientificProblem("a power chain requires a chain_id")
        object.__setattr__(self, "chain_id", chain_id)
        object.__setattr__(self, "elements", tuple(self.elements))

        if not isinstance(self.source_voltage, Quantity):
            raise InvalidScientificProblem("source_voltage must be a Quantity")
        self.source_voltage.require_compatible(
            "volt", context="power chain source voltage"
        )
        if self.source_voltage.magnitude_in("volt") <= 0.0:
            raise InvalidScientificProblem(
                "power chain source voltage must be strictly positive"
            )

        if not self.elements:
            raise InvalidScientificProblem("a power chain requires elements")
        seen: set[str] = set()
        for element in self.elements:
            if not isinstance(element, (WireSegment, FixedLoad)):
                raise InvalidScientificProblem(
                    f"a power chain element must be a WireSegment or a "
                    f"FixedLoad, got {type(element).__name__}"
                )
            if element.component_id in seen:
                raise InvalidScientificProblem(
                    f"duplicate component id {element.component_id!r}: two "
                    f"elements sharing an id would alias every endpoint that "
                    f"names it"
                )
            seen.add(element.component_id)
        if not self.wires:
            raise InvalidScientificProblem(
                "a power chain requires at least one wire segment; a chain of "
                "fixed loads has no material, no state and nothing to couple"
            )

    # ---- accessors ------------------------------------------------------
    @property
    def wires(self) -> tuple[WireSegment, ...]:
        return tuple(e for e in self.elements if isinstance(e, WireSegment))

    @property
    def loads(self) -> tuple[FixedLoad, ...]:
        return tuple(e for e in self.elements if isinstance(e, FixedLoad))

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(e.component_id for e in self.elements)

    @property
    def circuit_id(self) -> str:
        return f"{self.chain_id}-{'-'.join(self.component_ids)}"

    @property
    def electrical_problem_id(self) -> str:
        return f"electrical_dc:{self.circuit_id}"

    def wire(self, component_id: str) -> WireSegment:
        for candidate in self.wires:
            if candidate.component_id == component_id:
                return candidate
        raise InvalidScientificProblem(f"unknown wire {component_id!r}")

    def power_metric(self, component_id: str) -> str:
        """The DC domain's published power metric for one element."""
        return RESISTOR_POWER_METRIC.format(component_id=component_id)

    def _node_ids(self) -> tuple[str, ...]:
        """``n0 … n(N-1)`` plus the reference. ``n0`` is the source's positive."""
        return tuple(f"n{i}" for i in range(len(self.elements))) + (REFERENCE_NODE,)

    def circuit_at(self, resistances: Mapping[str, Quantity]) -> DCCircuit:
        """The series circuit with every wire set to one evaluated resistance.

        A load's resistance is a declared constant and is never looked up in
        ``resistances``; a wire's is *always* looked up and is never
        defaulted, because a missing evaluated resistance is a composition
        defect and silently substituting a reference value would hide it.
        """
        nodes = self._node_ids()
        resistors = []
        for index, element in enumerate(self.elements):
            if isinstance(element, FixedLoad):
                value = element.resistance
            else:
                try:
                    value = resistances[element.component_id]
                except KeyError:
                    raise InvalidScientificProblem(
                        f"no resistance supplied for wire "
                        f"{element.component_id!r}"
                    ) from None
            resistors.append(
                Resistor(
                    element.component_id, nodes[index], nodes[index + 1], value
                )
            )
        return DCCircuit(
            circuit_id=self.circuit_id,
            nodes=tuple(
                ElectricalNode(n, is_reference=(n == REFERENCE_NODE)) for n in nodes
            ),
            resistors=tuple(resistors),
            voltage_sources=(
                DCVoltageSource(
                    SOURCE_ID, nodes[0], REFERENCE_NODE, self.source_voltage
                ),
            ),
            description=(
                "Series power chain: one ideal source, wire segments whose "
                "resistance is computed from material and geometry, and "
                "fixed loads."
            ),
        )

    # ---- serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CHAIN_SCHEMA,
            "chain_id": self.chain_id,
            "source_voltage": self.source_voltage.to_dict(),
            # A LIST, because the order is scientific content: it is the
            # series order that assigns nodes. Sorting it would destroy the
            # declaration.
            "elements": [e.to_dict() for e in self.elements],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PowerChain":
        require_schema(payload, CHAIN_SCHEMA)
        elements = []
        for entry in payload["elements"]:
            kind = entry.get("kind")
            reader = _ELEMENT_READERS.get(kind)
            if reader is None:
                raise InvalidScientificProblem(
                    f"unsupported power chain element kind {kind!r}; expected "
                    f"one of {sorted(_ELEMENT_READERS)}"
                )
            elements.append(reader(entry))
        return cls(
            chain_id=payload["chain_id"],
            source_voltage=Quantity.from_dict(payload["source_voltage"]),
            elements=tuple(elements),
        )


# =====================================================================
# Representation
# =====================================================================

def wire_problems(
    chain: PowerChain,
) -> tuple[tuple[WireSegment, ScientificProblem, ScientificProblem,
                 ScientificProblem], ...]:
    """``(wire, resistivity problem, resistance problem, thermal problem)``.

    The one place the correspondence between a declared wire and the three
    problems posed for it is stated. Returning a flat tuple and recovering the
    correspondence by slicing is the positional association ``ExecutionBinding``
    exists to prevent, and it silently mis-wires a composition that still
    converges.
    """
    return tuple(
        (
            wire,
            cmat.build_resistivity_problem(wire.conductor),
            cmat.build_geometric_resistance_problem(wire.conductor),
            lump.build_lumped_thermal_problem(wire.body),
        )
        for wire in chain.wires
    )


def chain_problems(
    chain: PowerChain, resistances: Mapping[str, Quantity]
) -> tuple[ScientificProblem, ...]:
    """``(electrical, resistivity…, resistance…, thermal…)`` — ``3W + 1``.

    The electrical resistance has to be supplied to *build* the electrical
    problem, because the DC domain carries it as a configured
    ``ScientificParameter`` and folds it into the circuit's canonical
    identity. That is the configuration/state conflation `MIN-FOUNDATION-ET`
    measured; it is why every iteration builds a **fresh** electrical problem
    while its ``problem_id`` does not move.
    """
    problems = [build_dc_problem(chain.circuit_at(resistances))]
    for _, resistivity, resistance, thermal in wire_problems(chain):
        problems += [resistivity, resistance, thermal]
    return tuple(problems)


def chain_dependencies(
    chain: PowerChain,
    problems: Sequence[ScientificProblem],
    *,
    temperature_metric: str = lump.TEMPERATURE_METRIC,
) -> tuple[QuantityDependency, ...]:
    """``4W`` directed edges. Which values flow where is stated, never inferred.

    ``temperature_metric`` selects which of the thermal problem's
    kelvin-valued result metrics is transported. A dimension check cannot tell
    ``final_temperature`` from ``steady_state_temperature``; only the
    enumerated name can, and the two converge to different answers.
    """
    declared = {p.problem_id for p in problems}
    if chain.electrical_problem_id not in declared:
        raise InvalidScientificProblem(
            f"the supplied problems contain no electrical analysis "
            f"{chain.electrical_problem_id!r} to wire into"
        )
    electrical = chain.electrical_problem_id

    edges: list[QuantityDependency] = []
    for wire, resistivity, resistance, thermal in wire_problems(chain):
        cid = wire.component_id
        for problem in (resistivity, resistance, thermal):
            if problem.problem_id not in declared:
                raise InvalidScientificProblem(
                    f"wire {cid!r} poses problem {problem.problem_id!r}, which "
                    f"is not among the supplied problems; the correspondence "
                    f"between a wire and its problems is stated, not inferred "
                    f"from position"
                )
        edges.append(
            QuantityDependency(
                source_problem_id=electrical,
                source_quantity=chain.power_metric(cid),
                target_problem_id=thermal.problem_id,
                target_quantity=lump.HEAT_INPUT,
                unit_exemplar=lump.POWER_UNIT,
                name=f"{DEPENDENCY_HEAT}:{cid}",
                description=(
                    "The power absorbed by this element is the heat delivered "
                    "to the body it is thermally represented by."
                ),
            )
        )
        edges.append(
            QuantityDependency(
                source_problem_id=thermal.problem_id,
                source_quantity=temperature_metric,
                target_problem_id=resistivity.problem_id,
                target_quantity=cmat.TEMPERATURE,
                unit_exemplar=cmat.TEMPERATURE_UNIT,
                name=f"{DEPENDENCY_TEMPERATURE}:{cid}",
                description=(
                    "The body temperature is the state coordinate at which "
                    "this material's resistivity is evaluated."
                ),
            )
        )
        edges.append(
            QuantityDependency(
                source_problem_id=resistivity.problem_id,
                source_quantity=cmat.RESISTIVITY_METRIC,
                target_problem_id=resistance.problem_id,
                target_quantity=cmat.RESISTIVITY_METRIC,
                unit_exemplar=cmat.RESISTIVITY_UNIT,
                name=f"{DEPENDENCY_GEOMETRY}:{cid}",
                description=(
                    "The evaluated material resistivity is the value the "
                    "geometric resistance relation integrates over L and A."
                ),
            )
        )
        edges.append(
            QuantityDependency(
                source_problem_id=resistance.problem_id,
                source_quantity=cmat.RESISTANCE_METRIC,
                target_problem_id=electrical,
                target_quantity=resistance_name(cid),
                unit_exemplar=cmat.RESISTANCE_UNIT,
                name=f"{DEPENDENCY_RESISTANCE}:{cid}",
                description=(
                    "The computed resistance is the value this circuit "
                    "element takes."
                ),
            )
        )
    return tuple(edges)


def chain_plan(
    chain: PowerChain,
    dependencies: Sequence[QuantityDependency],
    *,
    seed: Quantity,
    tolerance: Quantity = Quantity(1e-6, "kelvin"),
    max_iterations: int = 50,
    plan_id: str | None = None,
) -> FixedPointCouplingPlan:
    """Cut every temperature edge into a resistivity problem. **Caller-side.**

    This function does select a tear by a rule, and saying otherwise would be
    false. What the constraint actually requires is that **the loop and the
    graph readers infer nothing**: ``execution_order`` ranks no tear and
    ``FixedPointCouplingPlan`` accepts whatever it is handed. The choice is
    made here, by a caller, and then becomes a typed field of a record rather
    than control flow.

    The rule is stated over the **declared resistivity problem ids**, not over
    a quantity name: ``cmat.TEMPERATURE`` and ``lump.TEMPERATURE`` are both the
    string ``"temperature"``, so a name-only filter would also match an edge
    targeting the thermal problem's own state variable — which
    ``check_against`` then refuses, because seeding a quantity a declared
    initial condition already determines is time marching wearing the name of
    coupling.
    """
    resistivity_ids = {
        wire.conductor.resistivity_problem_id for wire in chain.wires
    }
    torn = tuple(
        TornEndpoint(dependency=d, initial_value=seed)
        for d in dependencies
        if d.target_problem_id in resistivity_ids
        and d.target_quantity == cmat.TEMPERATURE
    )
    if len(torn) != len(chain.wires):
        raise InvalidScientificProblem(
            f"expected one temperature edge per wire to tear, found "
            f"{len(torn)} for {len(chain.wires)} wires"
        )
    return FixedPointCouplingPlan(
        plan_id=plan_id or f"{chain.chain_id}-fixed-point",
        dependencies=tuple(dependencies),
        torn=torn,
        absolute_tolerance=tolerance,
        max_iterations=max_iterations,
    )


def build_chain_twin(
    chain: PowerChain, *, twin_id: str | None = None, version: str = "0.1.0"
) -> ScientificTwin:
    """The scientific instance description. **Not the runtime state.**

    Material identity reaches the twin as a
    :class:`~engcore.scientific.twins.definition.TwinDatum`; every other
    declaration reaches it as a ``Quantity``. Note what this makes visible that
    a provenance record cannot: ``ProvenanceRecord.inputs`` is
    ``Mapping[str, Quantity]``, so the *name* of the material has no home
    there and only its three declared quantities travel. Recorded as a
    measured contract gap, not routed around through metadata.
    """
    declarations: list[TwinDatum] = [
        TwinDatum(
            name=f"source_voltage:{SOURCE_ID}",
            value=chain.source_voltage,
            role=TwinDatumRole.CONTROL,
        )
    ]
    models: list[ModelReference] = [
        ModelReference(
            cmat.GEOMETRIC_RESISTANCE_MODEL.model_id,
            cmat.GEOMETRIC_RESISTANCE_MODEL.version,
        ),
        ModelReference(
            lump.LUMPED_CAPACITY_MODEL.model_id, lump.LUMPED_CAPACITY_MODEL.version
        ),
    ]
    seen_models = {m.key for m in models}
    for element in chain.elements:
        cid = element.component_id
        if isinstance(element, FixedLoad):
            declarations.append(
                TwinDatum(f"resistance:{cid}", element.resistance,
                          TwinDatumRole.PARAMETER,
                          description="Declared, temperature-independent load.")
            )
            continue
        material, conductor, body = element.material, element.conductor, element.body
        model = material.resistivity_model()
        reference = ModelReference(model.model_id, model.version)
        if reference.key not in seen_models:
            models.append(reference)
            seen_models.add(reference.key)
        declarations += [
            TwinDatum(f"length:{cid}", conductor.length, TwinDatumRole.PARAMETER),
            TwinDatum(f"cross_sectional_area:{cid}", conductor.cross_sectional_area,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"heat_capacity:{cid}", body.heat_capacity,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"ambient_conductance:{cid}", body.ambient_conductance,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"ambient_temperature:{cid}", body.ambient_temperature,
                      TwinDatumRole.OPERATING_CONDITION),
            TwinDatum(f"temperature:{cid}", body.initial_temperature,
                      TwinDatumRole.STATE,
                      description="Body temperature at the start of the interval."),
        ]
        for parameter in material.resistivity_parameters():
            declarations.append(
                TwinDatum(
                    f"{parameter.name}:{cid}", parameter.value,
                    TwinDatumRole.PARAMETER,
                    description=(
                        f"Declared property of material {material.name!r}. "
                        f"Source: {material.source}"
                    ),
                )
            )
    return ScientificTwin(
        twin_id=twin_id or chain.chain_id,
        version=version,
        kind=TwinKind.CONCEPT,
        name="Power chain of self-heating wire segments and fixed loads",
        description=(
            "Wire segments whose resistance is computed from a declared "
            "material property set and a declared geometry, each thermally "
            "represented as a lumped body exchanging with an ambient, in "
            "series with fixed loads across an ideal DC voltage source."
        ),
        models=tuple(models),
        declarations=tuple(declarations),
        assumptions=(
            "each conductor and its thermal body are the same physical object",
            "the whole dissipated power of an element enters its body",
            "a fixed load dissipates into no represented body",
            "the resistivity is evaluated at the transported temperature and "
            "the resistance is held constant over the integrated interval",
        ),
    )


# =====================================================================
# Admission (enforced) and applicability (reported)
# =====================================================================

def admit_power_chain(chain: PowerChain, *, seed_temperature: Quantity) -> None:
    """Refuse a chain that must not be executed, **before any solver exists**.

    Every structural refusal — dimensions, positivity, id collisions, shared
    conductor/body identity — already happened in a ``__post_init__``, which is
    where a refusal belongs. What is left for this gate is the one thing a
    constructor cannot see: whether each wire's declared **material property
    set is applicable at the temperature this run is about to start from**, and
    whether each geometry is admissible to the geometric model.

    It gates the **declaration and the seed**, which is all a pre-run gate can
    gate. Whether the *converged* state stayed inside a material's range is a
    different question that only exists after a run and is answered by
    :func:`assess_run_applicability` — by reporting, never by refusing.
    """
    if not isinstance(chain, PowerChain):
        raise InvalidScientificProblem("admit_power_chain expects a PowerChain")
    if not isinstance(seed_temperature, Quantity):
        raise InvalidScientificProblem("seed_temperature must be a Quantity")
    seed_temperature.require_compatible(
        cmat.TEMPERATURE_UNIT, context="power chain seed temperature"
    )
    for wire in chain.wires:
        cmat.admit_conductor(wire.conductor, seed_temperature)


def assess_run_applicability(
    chain: PowerChain, run: CoupledRun
) -> dict[str, ValidityAssessment]:
    """Was each material's property set applicable at the state it converged to?

    **Assess, never refuse.** A run that converged outside a declared range is
    a finding about the answer, and refusing it after the fact would destroy
    the very record that makes the finding readable. This closes the gap
    `ET-VERTICAL` measured, where a run converged 49 K outside a declared
    domain with every sub-solve reporting success.
    """
    assessments: dict[str, ValidityAssessment] = {}
    for wire in chain.wires:
        endpoint = (
            wire.conductor.resistivity_problem_id, cmat.TEMPERATURE,
        )
        temperature = run.final_values.get(endpoint)
        if temperature is None:
            raise InvalidScientificProblem(
                f"the run carries no final value for {endpoint!r}; it did not "
                f"execute this chain"
            )
        assessments[wire.component_id] = cmat.assess_material_applicability(
            wire.material, temperature
        )
    return assessments


# =====================================================================
# Per-problem execution, supplied by this pack
# =====================================================================

def _quantity_inputs(problem: ScientificProblem) -> dict[str, Quantity]:
    """The problem's Quantity-valued parameters, and only those.

    ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]`` and refuses
    anything else, so a **typed categorical** parameter — which is exactly how
    material identity is declared — structurally cannot be recorded in
    provenance. The scientific content of "which material" does travel: its
    three declared quantities are all here. The *name* does not, and this
    filter is where that is lost. It is recorded as a measured contract gap,
    and it is deliberately **not** routed around by writing the name into
    ``ProvenanceRecord.metadata``: an untyped escape hatch is the thing this
    platform refuses, and a name smuggled through one would be unreadable by
    every consumer that matters.
    """
    return {
        name: value
        for name, value in problem.parameter_values().items()
        if isinstance(value, Quantity)
    }


def _resistivity_result(
    *, run_id: str, wire: WireSegment, problem: ScientificProblem,
    temperature: Quantity,
) -> ScientificResult:
    material = wire.material
    solver = cmat.resistivity_solver_for(material)
    solver.bind_conductor(wire.conductor, problem.problem_id,
                          temperature=temperature)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model_definition = material.resistivity_model()
    model = ModelReference(model_definition.model_id, model_definition.version)
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.domains.electrical.conductor_material/0.1.0",
        bindings=(
            ExecutionBinding(
                model=model,
                realization=prepared.payload.realization.reference(),
                solver=solver.identity,
            ),
        ),
        inputs=_quantity_inputs(problem) | {cmat.TEMPERATURE: temperature},
        assumptions=model_definition.assumptions,
    )
    return ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=solver.validate(prepared, raw),
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the declared "
                "material property set"
            )
            for name in metrics
        },
        assumptions=model_definition.assumptions,
        provenance=provenance,
    )


def _resistance_result(
    *, run_id: str, wire: WireSegment, problem: ScientificProblem,
    resistivity: Quantity,
) -> ScientificResult:
    solver = cmat.GeometricResistanceSolver()
    solver.bind_conductor(wire.conductor, problem.problem_id,
                          resistivity=resistivity)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        cmat.GEOMETRIC_RESISTANCE_MODEL.model_id,
        cmat.GEOMETRIC_RESISTANCE_MODEL.version,
    )
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.domains.electrical.conductor_material/0.1.0",
        bindings=(
            ExecutionBinding(
                model=model,
                realization=prepared.payload.realization.reference(),
                solver=solver.identity,
            ),
        ),
        inputs=_quantity_inputs(problem) | {
            cmat.RESISTIVITY_METRIC: resistivity
        },
        assumptions=cmat.GEOMETRIC_RESISTANCE_MODEL.assumptions,
    )
    return ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=solver.validate(prepared, raw),
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the declared "
                "geometry"
            )
            for name in metrics
        },
        assumptions=cmat.GEOMETRIC_RESISTANCE_MODEL.assumptions,
        provenance=provenance,
    )


def _thermal_result(
    *, run_id: str, wire: WireSegment, problem: ScientificProblem,
    heat_input: Quantity,
) -> ScientificResult:
    solver = lump.LumpedThermalSolver()
    solver.bind_body(wire.body, problem.problem_id, heat_input=heat_input)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        lump.LUMPED_CAPACITY_MODEL.model_id, lump.LUMPED_CAPACITY_MODEL.version
    )
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.domains.thermal_lumped/0.1.0",
        bindings=(
            ExecutionBinding(
                model=model,
                realization=prepared.payload.realization.reference(),
                solver=solver.identity,
            ),
        ),
        inputs=_quantity_inputs(problem) | {
            lump.HEAT_INPUT: heat_input,
            lump.AMBIENT_TEMPERATURE: wire.body.ambient_temperature,
            # The state at t0. Identical in every iteration: the loop iterates
            # the coupling, it does not march time.
            lump.TEMPERATURE: wire.body.initial_temperature,
        },
        assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
    )
    return ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=((model.model_id, model.version),),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=solver.validate(prepared, raw),
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification is performed on the lumped "
                "thermal declaration"
            )
            for name in metrics
        },
        assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
        provenance=provenance,
    )


def initial_resistances(
    chain: PowerChain, *, seed_temperature: Quantity
) -> dict[str, Quantity]:
    """Every wire's resistance at the seed temperature, **through the models**.

    This exists only to build the *first* electrical problem record, whose
    resistances iteration 1 immediately overwrites across the declared edges.
    It would have been one line of Python arithmetic — and that one line is
    precisely the unmodelled scientific claim this milestone exists to refuse.
    So it executes the two declared models through their published solvers,
    and every resistance that ever appears anywhere in this pack carries an
    ``ExecutionBinding``.

    Evaluated at the **seed**, not at each material's own reference
    temperature: the declared record then reproduces iteration 1 exactly,
    instead of describing a state at which no two wires are simultaneously.
    """
    resistances: dict[str, Quantity] = {}
    for wire, resistivity_problem, resistance_problem, _ in wire_problems(chain):
        rho = _resistivity_result(
            run_id=f"{chain.chain_id}-seed-{wire.component_id}",
            wire=wire, problem=resistivity_problem, temperature=seed_temperature,
        ).value(cmat.RESISTIVITY_METRIC)
        resistances[wire.component_id] = _resistance_result(
            run_id=f"{chain.chain_id}-seed-{wire.component_id}",
            wire=wire, problem=resistance_problem, resistivity=rho,
        ).value(cmat.RESISTANCE_METRIC)
    return resistances


def _executors(
    chain: PowerChain,
    problems: Sequence[ScientificProblem],
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]]:
    """problem_id -> how this pack solves it, given its transported inputs.

    This mapping is the *only* place the loop learns which science sits behind
    which problem, and it is built here, in the system pack, from declarations
    the caller supplied. The iteration itself contains no electrical, thermal
    or material branch of its own.
    """
    table: dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]] = {}

    def electrical_call(inputs: Mapping[str, Quantity], run_id: str):
        resistances = {
            wire.component_id: inputs[resistance_name(wire.component_id)]
            for wire in chain.wires
        }
        return circuit_solver(chain.circuit_at(resistances), run_id)

    table[chain.electrical_problem_id] = electrical_call

    for wire, resistivity, resistance, thermal in wire_problems(chain):

        def resistivity_call(inputs, run_id, _wire=wire, _problem=resistivity):
            return _resistivity_result(
                run_id=run_id, wire=_wire, problem=_problem,
                temperature=inputs[cmat.TEMPERATURE],
            )

        def resistance_call(inputs, run_id, _wire=wire, _problem=resistance):
            return _resistance_result(
                run_id=run_id, wire=_wire, problem=_problem,
                resistivity=inputs[cmat.RESISTIVITY_METRIC],
            )

        def thermal_call(inputs, run_id, _wire=wire, _problem=thermal):
            return _thermal_result(
                run_id=run_id, wire=_wire, problem=_problem,
                heat_input=inputs[lump.HEAT_INPUT],
            )

        table[resistivity.problem_id] = resistivity_call
        table[resistance.problem_id] = resistance_call
        table[thermal.problem_id] = thermal_call
    return table


def declared_problem_ids(chain: PowerChain) -> frozenset[str]:
    """Every problem id this chain poses, computable without solving anything.

    Exists so the composition can be checked for coherence **before** the
    bootstrap in :func:`initial_resistances` executes a single solver. Without
    it, a plan naming a problem that is not part of the composition would be
    caught by ``FixedPointCouplingPlan.check_against`` — but only after two
    solves per wire had already run, which would make "no solver executes
    after a refusal" false for exactly the broken-connection case.
    """
    ids = {chain.electrical_problem_id}
    for wire in chain.wires:
        ids |= {
            wire.conductor.resistivity_problem_id,
            wire.conductor.resistance_problem_id,
            lump.build_lumped_thermal_problem(wire.body).problem_id,
        }
    return frozenset(ids)


def _refuse_unresolved_edges(
    chain: PowerChain, plan: FixedPointCouplingPlan
) -> None:
    declared = declared_problem_ids(chain)
    unresolved = sorted(
        {
            problem_id
            for dependency in plan.dependencies
            for problem_id in (
                dependency.source_problem_id, dependency.target_problem_id,
            )
            if problem_id not in declared
        }
    )
    if unresolved:
        raise InvalidScientificProblem(
            f"coupling plan {plan.plan_id!r} declares edges naming "
            f"{unresolved}, which chain {chain.chain_id!r} does not pose; a "
            f"connection that resolves to nothing is refused before anything "
            f"is executed, not after"
        )


def _seed_of(chain: PowerChain, plan: FixedPointCouplingPlan) -> Quantity:
    """The seed the plan declares for the wires' temperature endpoints.

    Read **structurally**, from the torn endpoints themselves, never from a
    parallel argument a caller could disagree with the plan about.
    """
    seeds = {
        endpoint.initial_value
        for endpoint in plan.torn
        if endpoint.dependency.target_quantity == cmat.TEMPERATURE
    }
    if not seeds:
        raise InvalidScientificProblem(
            f"plan {plan.plan_id!r} tears no temperature endpoint, so this "
            f"pack cannot state the state its first record describes"
        )
    if len(seeds) != 1:
        raise InvalidScientificProblem(
            f"plan {plan.plan_id!r} seeds the wires at {len(seeds)} different "
            f"temperatures; the declared electrical record could then describe "
            f"no single state, so the pack refuses rather than picking one"
        )
    return seeds.pop()


def run_power_chain(
    chain: PowerChain,
    plan: FixedPointCouplingPlan,
    *,
    run_id: str = "power-chain",
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> CoupledRun:
    """Admit the chain, build the composition, then iterate it.

    The admission gate is called **here**, on the executed path, rather than
    left to a caller who may skip it. Detection is not enforcement, and a gate
    that only runs when someone remembers is detection.

    Everything domain-specific happens in this function — the problems, and
    the dispatch table that says how each is solved.
    :func:`~engcore.coupling.run_fixed_point` receives both as data and runs
    the iteration without being able to name either.
    """
    seed = _seed_of(chain, plan)
    _refuse_unresolved_edges(chain, plan)
    admit_power_chain(chain, seed_temperature=seed)
    problems = chain_problems(
        chain, initial_resistances(chain, seed_temperature=seed)
    )
    return run_fixed_point(
        problems,
        _executors(chain, problems, circuit_solver),
        plan,
        run_id=run_id,
        software_version="engcore.systems.electrothermal.power_chain/0.1.0",
        assumptions=(
            "the resistivity is evaluated at the transported temperature and "
            "the resistance is held constant over the integrated interval; "
            "this is an implicit statement over one interval and carries a "
            "coupling error that is not quantified here",
            "the whole dissipated power of an element enters its body",
            "a fixed load dissipates into no represented body",
        ),
    )


def compose(
    chain: PowerChain,
    *,
    seed: Quantity,
    temperature_metric: str = lump.TEMPERATURE_METRIC,
    tolerance: Quantity = Quantity(1e-6, "kelvin"),
    max_iterations: int = 50,
) -> tuple[tuple[ScientificProblem, ...], tuple[QuantityDependency, ...],
           FixedPointCouplingPlan]:
    """Problems, declared edges and a plan — the whole composition in one call.

    A convenience for callers, and nothing more: every piece it returns is
    built by a published function above and can be built without it.

    It admits the chain **before** bootstrapping, for the same reason
    :func:`run_power_chain` does: :func:`initial_resistances` executes real
    solvers, so a gate placed after it would let an inadmissible declaration
    reach an evaluator.
    """
    admit_power_chain(chain, seed_temperature=seed)
    problems = chain_problems(chain, initial_resistances(chain, seed_temperature=seed))
    dependencies = chain_dependencies(
        chain, problems, temperature_metric=temperature_metric
    )
    plan = chain_plan(
        chain, dependencies, seed=seed, tolerance=tolerance,
        max_iterations=max_iterations,
    )
    return problems, dependencies, plan
