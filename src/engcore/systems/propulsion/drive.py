"""A series electromechanical drive: source, feed, machine, return, load.

`PROPULSION0`. One motor participating **simultaneously** in electrical,
rotational-mechanical and thermal physics, while staying coupled to
material-dependent wires::

    +24 V ──[ wire_a ]──[ R_motor ]──( E = k_e w )──[ wire_b ]── gnd
                │            │                           │
             (body_a)   (body_motor) ◀── P_copper + P_mech_loss
                                          (one declared model, not a sum)
                │            │                           │
                └────── rho(T), R(T), C(rho_m,c_p) ──────┘

Fourteen separately posed problems, twenty-one declared edges, three torn
endpoints — all three in kelvin — one twin, and **not one line of new coupling
machinery**. ``engcore.coupling`` and ``engcore.scientific`` are byte-untouched.

The motor's physical identity, and why no new contract states it
----------------------------------------------------------------
One :class:`Motor` record owns **eight** distinct identities:

======================================  =========================================
``R:<id>``                              a resistor in the circuit
``Vs:<id>-emf``                         a voltage source in the same circuit
``conductor_resistivity:<id>``          a material-property problem
``conductor_resistance:<id>``           a geometry problem
``conductor_thermal_mass:<id>``         a thermal-mass problem
``thermal-lumped-<id>``                 a lumped body problem
``drive_operating_point:<id>``          a rotational operating point
``machine_heat_generation:<id>``        a heat-aggregation problem
======================================  =========================================

Every one is **derived** from the single ``component_id`` by a published
accessor on this record, none of them collides with another, and no universal
record states the correspondence. That is the measured answer to whether a
motor forces a physical-identity contract: going from a wire's four derived
identities to a motor's eight is a *quantitative* change, not a new kind, and
``PhysicalEntityReference`` / ``ComponentInstance`` / ports were each attempted
against the existing contracts first and none was forced. Adding one later stays
additive precisely because problem ids remain derived from ``component_id``.

What is deliberately NOT introduced
-----------------------------------
No ``ComponentInstance``, ``Port``, ``Connector``, ``SystemDefinition``,
``PhysicalEntityReference``, universal ``Material``, ``MechanicalSystem``,
``StateVector`` or ``FanInRule``; no per-endpoint coupling tolerance, no
relaxation knob, no new ``CouplingOutcome`` member, and no edit anywhere under
``engcore/scientific`` or ``engcore/coupling``.

Two seams are declared locally rather than imported sideways
------------------------------------------------------------
:data:`CircuitSolver` and :func:`native_circuit_solver` restate a seam the
electro-thermal pack also declares. Importing that pack from this one would be a
lateral system-to-system dependency for three lines of plumbing, which is worse
than the restatement. **Recorded as a finding:** the seam now exists in two
packs, and the day a third needs it, it belongs one level down rather than a
third time here.

The energy trap, and the two places it is enforced
---------------------------------------------------
`k_e` and `k_t` are numerically equal in SI because ``E I`` and ``tau_e w`` are
the same power. Both are declared, so an inconsistent pair is *constructible*;
:func:`admit_drive` **refuses** it before any solver object exists. After the
loop, :func:`reconcile_drive_energy` **raises** if the six-term power balance,
the two current representations or the two converted-power representations
disagree beyond a declared relative tolerance. Detection is not enforcement, and
this repository's sharpest historical failure was a validation ``FAIL`` whose
value was consumed anyway and converged 18 K wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from ...coupling import (
    CoupledRun,
    CouplingOutcome,
    FixedPointCouplingPlan,
    TornEndpoint,
    run_fixed_point,
)
from ...domains import mechanical_rotational as rot
from ...domains import thermal_lumped as lump
from ...domains.electrical import conductor_material as cmat
from ...domains.electrical.dc import (
    DCCircuit,
    DCVoltageSource,
    ElectricalNode,
    Resistor,
    build_dc_problem,
    solve_circuit,
)
from ...domains.electrical.dc.problem import (
    resistance_name,
    source_current_name,
    source_voltage_name,
)
from ...scientific.composition import QuantityDependency
from ...scientific.errors import InvalidScientificProblem
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.models.definition import ValidityAssessment, ValidityStatus
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
from . import materials as pmat
from . import models as pmod

__all__ = [
    "DEPENDENCY_BACK_EMF",
    "DEPENDENCY_ELECTRICAL_LOSS",
    "DEPENDENCY_GEOMETRY",
    "DEPENDENCY_HEAT",
    "DEPENDENCY_LOOP_RESISTANCE",
    "DEPENDENCY_MECHANICAL_LOSS",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_SERIES",
    "DEPENDENCY_TEMPERATURE",
    "DEPENDENCY_TOTAL_HEAT",
    "DRIVE_SCHEMA",
    "ENERGY_RELATIVE_TOLERANCE",
    "CONDUCTING_ELEMENT_SCHEMA",
    "THERMAL_DECLARATION_SCHEMA",
    "CircuitSolver",
    "DriveElement",
    "DriveRun",
    "DriveWire",
    "EnergyAccounting",
    "Motor",
    "PropulsionDrive",
    "RESISTOR_POWER_METRIC",
    "ThermalDeclaration",
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

DRIVE_SCHEMA = schema_string("propulsion_series_drive")
#: The two sub-payloads this pack owns. They exist because this pack writes its
#: own conductor encoding (see `_ConductingElement._common_dict`), and an
#: unversioned sub-payload inside a versioned envelope is a migration waiting to
#: happen: `require_schema` cannot fire on a key that is not there, so a field
#: added to a composed record would be silently absorbed as a default and every
#: round-trip test would still pass. `architecture-falsifier` produced exactly
#: that counterexample; these two tokens close it while the payload is still
#: unfrozen and the fix is free.
CONDUCTING_ELEMENT_SCHEMA = schema_string("propulsion_conducting_element")
THERMAL_DECLARATION_SCHEMA = schema_string("propulsion_thermal_declaration")

DEPENDENCY_HEAT = "joule-dissipation-heats-body"
DEPENDENCY_TEMPERATURE = "body-temperature-sets-material-state"
DEPENDENCY_GEOMETRY = "material-resistivity-sets-conductor-geometry-input"
DEPENDENCY_RESISTANCE = "conductor-resistance-sets-circuit-element"
DEPENDENCY_SERIES = "conductor-resistance-joins-the-series-loop"
DEPENDENCY_LOOP_RESISTANCE = "series-loop-resistance-sets-operating-point"
DEPENDENCY_BACK_EMF = "machine-back-emf-opposes-the-supply"
DEPENDENCY_ELECTRICAL_LOSS = "winding-dissipation-heats-the-machine"
DEPENDENCY_MECHANICAL_LOSS = "internal-mechanical-loss-heats-the-machine"
DEPENDENCY_TOTAL_HEAT = "machine-heat-generation-heats-the-body"

SOURCE_ID = "V1"
REFERENCE_NODE = "gnd"

#: The DC package publishes no metric-name helper for element power; the
#: sibling electro-thermal pack already names it, and this pack reuses the same
#: convention rather than re-deriving it. (MIN-FOUNDATION-ET finding C-11.)
RESISTOR_POWER_METRIC = "resistor_power:{component_id}"
RESISTOR_CURRENT_METRIC = "resistor_current:{component_id}"
SOURCE_POWER_METRIC = "source_power:{component_id}"

#: Relative tolerance of the post-run energy reconciliation. It is a *closure*
#: tolerance on arithmetic that should agree to machine precision, not a
#: physical agreement tolerance.
ENERGY_RELATIVE_TOLERANCE = 1e-9


class CircuitSolver(Protocol):
    """``(circuit, run_id) -> ScientificResult``. The one substitution seam."""

    def __call__(self, circuit: DCCircuit, run_id: str) -> ScientificResult: ...


def native_circuit_solver(circuit: DCCircuit, run_id: str) -> ScientificResult:
    """This pack's own way of solving one DC circuit. The default seam.

    Published so the default and any substitute have the same type, and so a
    caller can state "solve it the way this pack always did" explicitly rather
    than by passing ``None``.
    """
    return solve_circuit(circuit, run_id=run_id, problem=build_dc_problem(circuit))


# =====================================================================
# Element declarations
# =====================================================================

class DriveElement(Protocol):
    """What this pack requires of anything it puts in the loop.

    `COMPOSITE-SYSTEM0` named a tripwire in advance: *a third element kind that
    poses its own problems — at that point the union should be re-examined, not
    grown.* This milestone fires it, and this protocol is the re-examination.

    **It is a type annotation, not an extension point, and an earlier draft of
    this docstring wrongly claimed otherwise.** `architecture-falsifier`
    produced the counterexample: a class satisfying all three members still
    cannot enter a :class:`PropulsionDrive`, because that record declares three
    concrete slots, ``isinstance``-checks them, hard-returns the same three from
    :attr:`~PropulsionDrive.conducting_elements`, returns exactly two series
    joins, and assigns circuit nodes positionally over a fixed five-node span.
    A fourth element kind is **not** additive today.

    What the protocol does buy is real but smaller: it names, in one place, the
    three members this pack requires of anything in the loop, so the requirement
    is readable instead of scattered across five call sites. Building a generic
    element list to make it a true extension point would be the speculative move
    this lineage refuses — there is no fourth kind. The honest response to the
    tripwire is this record plus the correction above, not machinery.
    """

    @property
    def component_id(self) -> str: ...

    def declared_problem_ids(self) -> frozenset[str]: ...

    def to_dict(self) -> dict[str, Any]: ...


def _positive(value: Any, unit: str, label: str) -> Quantity:
    if not isinstance(value, Quantity):
        raise InvalidScientificProblem(f"{label} must be a Quantity")
    value.require_compatible(unit, context=label)
    if value.magnitude_in(unit) <= 0.0:
        raise InvalidScientificProblem(
            f"{label} must be strictly positive, got {value}"
        )
    return value


@dataclass(frozen=True)
class ThermalDeclaration:
    """The lumped declaration **minus** the capacity, which is derived.

    ``ThermalBody`` takes ``heat_capacity`` as a constructor field, and here
    that number is a *model output*. So the caller declares everything else and
    the capacity arrives from :data:`~engcore.systems.propulsion.materials.
    CONDUCTOR_THERMAL_MASS_MODEL`, through its published solver, with an
    ``ExecutionBinding`` — never as a line of caller arithmetic.
    """

    ambient_conductance: Quantity
    ambient_temperature: Quantity
    initial_temperature: Quantity
    duration: Quantity

    def __post_init__(self) -> None:
        _positive(
            self.ambient_conductance, lump.CONDUCTANCE_UNIT, "ambient_conductance"
        )
        _positive(self.ambient_temperature, lump.TEMPERATURE_UNIT, "ambient_temperature")
        _positive(self.initial_temperature, lump.TEMPERATURE_UNIT, "initial_temperature")
        _positive(self.duration, lump.TIME_UNIT, "duration")

    def body(self, body_id: str, heat_capacity: Quantity) -> lump.ThermalBody:
        return lump.ThermalBody(
            body_id=body_id,
            heat_capacity=heat_capacity,
            ambient_conductance=self.ambient_conductance,
            ambient_temperature=self.ambient_temperature,
            initial_temperature=self.initial_temperature,
            duration=self.duration,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": THERMAL_DECLARATION_SCHEMA,
            "ambient_conductance": self.ambient_conductance.to_dict(),
            "ambient_temperature": self.ambient_temperature.to_dict(),
            "initial_temperature": self.initial_temperature.to_dict(),
            "duration": self.duration.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ThermalDeclaration":
        require_schema(payload, THERMAL_DECLARATION_SCHEMA)
        return cls(
            ambient_conductance=Quantity.from_dict(payload["ambient_conductance"]),
            ambient_temperature=Quantity.from_dict(payload["ambient_temperature"]),
            initial_temperature=Quantity.from_dict(payload["initial_temperature"]),
            duration=Quantity.from_dict(payload["duration"]),
        )


@dataclass(frozen=True)
class _ConductingElement:
    """Shared structure of anything that is a conductor with a thermal body.

    Not a base class for polymorphism — the pack dispatches on the
    :class:`DriveElement` protocol, not on this type. It exists so that the
    material/geometry/thermal triple is declared once and the co-identity rule
    is checked once.
    """

    conductor: cmat.MaterialConductor
    material: pmat.ThermophysicalConductor
    thermal: ThermalDeclaration

    def __post_init__(self) -> None:
        if not isinstance(self.conductor, cmat.MaterialConductor):
            raise InvalidScientificProblem(
                "a conducting element requires a MaterialConductor"
            )
        if not isinstance(self.material, pmat.ThermophysicalConductor):
            raise InvalidScientificProblem(
                "a conducting element requires a ThermophysicalConductor"
            )
        if self.conductor.material is not self.material.conductor_material:
            raise InvalidScientificProblem(
                f"element {self.conductor.component_id!r} declares electrical "
                f"material {self.conductor.material.name!r} and thermophysical "
                f"material {self.material.name!r}; one physical object has one "
                f"material, and this pack refuses two property sets that are "
                f"not two halves of the same declaration"
            )

    @property
    def component_id(self) -> str:
        return self.conductor.component_id

    @property
    def thermal_mass_problem_id(self) -> str:
        return f"conductor_thermal_mass:{self.component_id}"

    @property
    def thermal_problem_id(self) -> str:
        return f"thermal-lumped-{self.component_id}"

    def declared_problem_ids(self) -> frozenset[str]:
        return frozenset(
            {
                self.conductor.resistivity_problem_id,
                self.conductor.resistance_problem_id,
                self.thermal_problem_id,
            }
        )

    #: The payload writes the material **once**, and the conductor's geometry
    #: beside it — not ``MaterialConductor.to_dict()``.
    #:
    #: This is a measured consequence of the composition, found by executing a
    #: round trip rather than by reasoning. ``MaterialConductor.to_dict()``
    #: embeds its own material, so writing it beside the thermophysical record
    #: would put copper's resistivity in one payload **twice**, under two
    #: authorities that a later edit could make disagree — and reading it back
    #: produced two equal-but-distinct material objects, which broke the
    #: single-declaration invariant this element checks at construction. The
    #: encoding below has exactly one material in it, so the invariant survives
    #: serialization instead of being an in-process-only guarantee.
    #:
    #: **Recorded as a finding:** the electrical record's serialization
    #: granularity is "conductor including material", and a consumer that
    #: composes the material from outside therefore cannot reuse it. That is a
    #: real cost of composing rather than promoting, and it is written down
    #: rather than absorbed.
    def _common_dict(self) -> dict[str, Any]:
        return {
            "schema": CONDUCTING_ELEMENT_SCHEMA,
            "component_id": self.conductor.component_id,
            "length": self.conductor.length.to_dict(),
            "cross_sectional_area": self.conductor.cross_sectional_area.to_dict(),
            "material": self.material.to_dict(),
            "thermal": self.thermal.to_dict(),
        }

    @staticmethod
    def _common_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
        require_schema(payload, CONDUCTING_ELEMENT_SCHEMA)
        material = pmat.ThermophysicalConductor.from_dict(payload["material"])
        return {
            # ONE material object, shared by the electrical and the thermal
            # half of this element — after a round trip exactly as before one.
            "conductor": cmat.MaterialConductor(
                component_id=payload["component_id"],
                material=material.conductor_material,
                length=Quantity.from_dict(payload["length"]),
                cross_sectional_area=Quantity.from_dict(
                    payload["cross_sectional_area"]
                ),
            ),
            "material": material,
            "thermal": ThermalDeclaration.from_dict(payload["thermal"]),
        }


@dataclass(frozen=True)
class DriveWire(_ConductingElement):
    """One lead of the drive loop: a conductor, its material, its body.

    Structurally the same shape ``COMPOSITE-SYSTEM0``'s ``WireSegment`` has,
    with one difference that is the whole point of this milestone: the material
    is a **single declaration supplying four properties**, and the body's heat
    capacity is *derived from it* rather than declared beside it.
    """

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "drive_wire", **self._common_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DriveWire":
        return cls(**cls._common_fields(payload))


@dataclass(frozen=True)
class Motor(_ConductingElement):
    """The machine. A conductor **and** a shaft **and** a body, at one identity.

    Its winding is a :class:`~engcore.domains.electrical.conductor_material.
    MaterialConductor` — the *same* record a wire uses — so its temperature
    dependent resistance goes through the *same* ``rho(T)`` and ``R = rho L/A``
    models. No second ``R(T)`` framework exists anywhere in this milestone, and
    a test asserts the model identities are the same objects.

    What a motor adds over a wire is a shaft: :class:`~engcore.domains.
    mechanical_rotational.MachineConstants`. It adds no new *identity kind*.
    """

    constants: rot.MachineConstants

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isinstance(self.constants, rot.MachineConstants):
            raise InvalidScientificProblem("a motor requires MachineConstants")

    # ---- the eight derived identities, all from one component_id --------
    @property
    def back_emf_source_id(self) -> str:
        return f"{self.component_id}-emf"

    @property
    def operating_point_problem_id(self) -> str:
        return f"drive_operating_point:{self.component_id}"

    @property
    def heat_generation_problem_id(self) -> str:
        return f"machine_heat_generation:{self.component_id}"

    def physical_identities(self) -> tuple[str, ...]:
        """Every identity this one physical object owns, in one place.

        Published so the claim "the motor's physical identity does not collapse
        into any one problem identity" is *readable* rather than asserted, and
        so a collision between any two of them is testable.
        """
        return (
            resistance_name(self.component_id),
            source_voltage_name(self.back_emf_source_id),
            self.conductor.resistivity_problem_id,
            self.conductor.resistance_problem_id,
            self.thermal_mass_problem_id,
            self.thermal_problem_id,
            self.operating_point_problem_id,
            self.heat_generation_problem_id,
        )

    def declared_problem_ids(self) -> frozenset[str]:
        return super().declared_problem_ids() | {
            self.operating_point_problem_id,
            self.heat_generation_problem_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "drive_motor",
            **self._common_dict(),
            "constants": self.constants.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Motor":
        return cls(
            **cls._common_fields(payload),
            constants=rot.MachineConstants.from_dict(payload["constants"]),
        )


# =====================================================================
# The drive
# =====================================================================

@dataclass(frozen=True)
class PropulsionDrive:
    """Source, feed lead, machine, return lead, mechanical load.

    The two leads are declared **separately and by role**, never as a list with
    an index: ``feed`` and ``ret`` are different physical objects with their own
    materials, geometries and bodies, and nothing in this record or anywhere
    downstream lets a change to one reach the other except through the physics
    they share — one loop current.
    """

    drive_id: str
    source_voltage: Quantity
    feed: DriveWire
    motor: Motor
    ret: DriveWire
    load: rot.RotationalLoad

    def __post_init__(self) -> None:
        drive_id = str(self.drive_id).strip()
        if not drive_id:
            raise InvalidScientificProblem("a drive requires a drive_id")
        object.__setattr__(self, "drive_id", drive_id)
        _positive(self.source_voltage, "volt", "drive source voltage")
        for label, element, kind in (
            ("feed", self.feed, DriveWire),
            ("motor", self.motor, Motor),
            ("ret", self.ret, DriveWire),
        ):
            if not isinstance(element, kind):
                raise InvalidScientificProblem(
                    f"drive {drive_id!r} {label} must be a {kind.__name__}"
                )
        if not isinstance(self.load, rot.RotationalLoad):
            raise InvalidScientificProblem(
                f"drive {drive_id!r} requires a RotationalLoad"
            )
        ids = [e.component_id for e in self.elements]
        duplicated = sorted({i for i in ids if ids.count(i) > 1})
        if duplicated:
            raise InvalidScientificProblem(
                f"duplicate component id(s) {duplicated}: two elements sharing "
                f"an id would alias every endpoint that names it"
            )
        if self.motor.back_emf_source_id in ids or (
            self.motor.back_emf_source_id == SOURCE_ID
        ):
            raise InvalidScientificProblem(
                f"the machine's back-EMF source id "
                f"{self.motor.back_emf_source_id!r} collides with a declared "
                f"element or with the supply"
            )
        # ONE physical material, ONE declaration — enforced, not assumed.
        #
        # `architecture-falsifier` found that the per-element check (an
        # element's two property halves must be the same material object) says
        # nothing ACROSS elements: two `ThermophysicalConductor` records over
        # the same `cmat.COPPER` with different densities constructed, ran,
        # serialized and reached the twin, both described as "Declared property
        # of material 'copper'". After serialization the link is the material's
        # NAME, so a name-keyed consumer would have seen one copper with two
        # densities. That is the duplicate this milestone claims not to have
        # created, so it is refused here rather than left to convention.
        by_material: dict[int, pmat.ThermophysicalConductor] = {}
        for element in self.conducting_elements:
            key = id(element.conductor.material)
            first = by_material.setdefault(key, element.material)
            if first != element.material:
                raise InvalidScientificProblem(
                    f"drive {drive_id!r} declares two different "
                    f"thermophysical property sets for one material "
                    f"{element.material.name!r}. One physical material has one "
                    f"declaration; two would serialize under one name and be "
                    f"indistinguishable to any consumer that reads it back"
                )

    # ---- accessors ------------------------------------------------------
    @property
    def elements(self) -> tuple[DriveElement, ...]:
        """The loop in declared electrical order: feed, machine, return."""
        return (self.feed, self.motor, self.ret)

    @property
    def conducting_elements(self) -> tuple[_ConductingElement, ...]:
        return (self.feed, self.motor, self.ret)

    @property
    def circuit_id(self) -> str:
        return f"{self.drive_id}-" + "-".join(e.component_id for e in self.elements)

    @property
    def electrical_problem_id(self) -> str:
        return f"electrical_dc:{self.circuit_id}"

    @property
    def series_join_ids(self) -> tuple[str, str]:
        """The two binary joins of a three-element loop. **N-1 of them.**"""
        return (
            f"series_resistance:{self.drive_id}-1",
            f"series_resistance:{self.drive_id}-2",
        )

    def power_metric(self, component_id: str) -> str:
        return RESISTOR_POWER_METRIC.format(component_id=component_id)

    def circuit_at(
        self, resistances: Mapping[str, Quantity], back_emf: Quantity
    ) -> DCCircuit:
        """The series loop with evaluated resistances and an opposing back-EMF.

        The machine's back-EMF is an **ordinary** ``DCVoltageSource``, oriented
        so that its positive node faces the current arriving from the winding
        and it therefore *absorbs* power. Nothing about the electrical domain is
        extended to represent a motor: the circuit is composed only of
        primitives the DC package — and the external ngspice adapter — already
        support, which is what makes provider substitution possible at all.
        """
        nodes = ("n0", "n1", "n2", "n3", REFERENCE_NODE)
        resistors = []
        for index, element in enumerate(self.conducting_elements):
            cid = element.component_id
            try:
                value = resistances[cid]
            except KeyError:
                raise InvalidScientificProblem(
                    f"no resistance supplied for {cid!r}; a missing evaluated "
                    f"resistance is a composition defect and substituting a "
                    f"reference value would hide it"
                ) from None
            # feed n0-n1, winding n1-n2, and the return lead sits after the
            # back-EMF source, n3-gnd.
            span = (nodes[0], nodes[1]) if index == 0 else (
                (nodes[1], nodes[2]) if index == 1 else (nodes[3], nodes[4])
            )
            resistors.append(Resistor(cid, span[0], span[1], value))
        return DCCircuit(
            circuit_id=self.circuit_id,
            nodes=tuple(
                ElectricalNode(n, is_reference=(n == REFERENCE_NODE)) for n in nodes
            ),
            resistors=tuple(resistors),
            voltage_sources=(
                DCVoltageSource(SOURCE_ID, nodes[0], REFERENCE_NODE,
                                self.source_voltage),
                DCVoltageSource(self.motor.back_emf_source_id, nodes[2], nodes[3],
                                back_emf),
            ),
            description=(
                "Series electromechanical drive: one ideal source, two leads "
                "and a machine winding whose resistances are computed from "
                "declared materials and geometries, and the machine's "
                "back-EMF as an opposing ideal source."
            ),
        )

    # ---- serialization --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DRIVE_SCHEMA,
            "drive_id": self.drive_id,
            "source_voltage": self.source_voltage.to_dict(),
            # By ROLE, not by index. The electrical order is a consequence of
            # the roles, and a list would have hidden the roles behind
            # positions.
            "feed": self.feed.to_dict(),
            "motor": self.motor.to_dict(),
            "return": self.ret.to_dict(),
            "load": self.load.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PropulsionDrive":
        require_schema(payload, DRIVE_SCHEMA)
        # The kind tags are deliberately distinct from the ROLE names above
        # ("feed"/"motor"/"ret"), which appear only as human labels in refusal
        # messages. Sharing the token "motor" between a role label and a
        # payload kind made a structural test unable to tell dispatch from
        # prose; the tags are now unambiguous.
        for key, expected in (("feed", "drive_wire"), ("motor", "drive_motor"),
                              ("return", "drive_wire")):
            kind = payload[key].get("kind")
            if kind != expected:
                raise InvalidScientificProblem(
                    f"drive payload names {key!r} of kind {kind!r}; this "
                    f"composition requires {expected!r}"
                )
        return cls(
            drive_id=payload["drive_id"],
            source_voltage=Quantity.from_dict(payload["source_voltage"]),
            feed=DriveWire.from_dict(payload["feed"]),
            motor=Motor.from_dict(payload["motor"]),
            ret=DriveWire.from_dict(payload["return"]),
            load=rot.RotationalLoad.from_dict(payload["load"]),
        )


# =====================================================================
# Derived declarations: the thermal masses
# =====================================================================

def _thermal_mass_result(
    *, run_id: str, element: _ConductingElement, problem: ScientificProblem
) -> ScientificResult:
    solver = pmat.ConductorThermalMassSolver()
    solver.bind_conductor(element.conductor, element.material, problem.problem_id)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(
        pmat.CONDUCTOR_THERMAL_MASS_MODEL.model_id,
        pmat.CONDUCTOR_THERMAL_MASS_MODEL.version,
    )
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.systems.propulsion.materials/0.1.0",
        bindings=(
            ExecutionBinding(
                model=model,
                realization=prepared.payload.realization.reference(),
                solver=solver.identity,
            ),
        ),
        inputs={
            name: value
            for name, value in problem.parameter_values().items()
            if isinstance(value, Quantity)
        },
        assumptions=pmat.CONDUCTOR_THERMAL_MASS_MODEL.assumptions,
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
                "thermophysical property set"
            )
            for name in metrics
        },
        assumptions=pmat.CONDUCTOR_THERMAL_MASS_MODEL.assumptions,
        provenance=provenance,
    )


def derive_thermal_masses(
    drive: PropulsionDrive, *, run_id: str
) -> tuple[dict[str, lump.ThermalBody], dict[str, ScientificResult]]:
    """Every body's capacity, **through the model**, before the loop is built.

    Derived once rather than transported on an edge, and the reason is stated
    rather than assumed: ``heat_capacity`` *is* a declared parameter of the
    lumped thermal problem and an edge into it would work. The capacity is
    static here only because ``rho_m`` and ``c_p`` are declared
    temperature-independent, so it does not move during the coupling. The day
    someone declares ``c_p(T)``, the edge route exists at zero contract cost.

    What is refused either way is a line of caller arithmetic: this is the same
    discipline that makes the resistance bootstrap execute two real models.

    **The scope of "derived, not declared" is IN PROCESS.** The returned
    results carry model, realization, solver and ``ExecutionBinding``; the
    :class:`~engcore.domains.thermal_lumped.ThermalBody` they feed carries only
    the number, and :class:`DriveRun` — which holds the derivation results — is
    deliberately not serialized. So a persisted artifact records the capacity
    without recording that it came from ``rho_m L A c_p``. The twin's
    ``TwinDatum`` description says so in prose, which is weaker than an
    ``ExecutionBinding``. Recorded as a limitation; the day ``c_p(T)`` is
    declared, the edge route closes it at zero contract cost.
    """
    bodies: dict[str, lump.ThermalBody] = {}
    results: dict[str, ScientificResult] = {}
    for element in drive.conducting_elements:
        problem = pmat.build_thermal_mass_problem(
            element.conductor, element.material,
            problem_id=element.thermal_mass_problem_id,
        )
        result = _thermal_mass_result(
            run_id=f"{run_id}-{element.component_id}",
            element=element, problem=problem,
        )
        results[element.component_id] = result
        bodies[element.component_id] = element.thermal.body(
            element.component_id, result.value(pmat.HEAT_CAPACITY_METRIC)
        )
    return bodies, results


# =====================================================================
# Representation
# =====================================================================

def drive_problems(
    drive: PropulsionDrive,
    bodies: Mapping[str, lump.ThermalBody],
    resistances: Mapping[str, Quantity],
    back_emf: Quantity,
) -> tuple[ScientificProblem, ...]:
    """The fourteen problems, in a stated order: ``1 + 3*3 + 2 + 1 + 1``."""
    problems: list[ScientificProblem] = [
        build_dc_problem(drive.circuit_at(resistances, back_emf))
    ]
    for element in drive.conducting_elements:
        problems += [
            cmat.build_resistivity_problem(element.conductor),
            cmat.build_geometric_resistance_problem(element.conductor),
            lump.build_lumped_thermal_problem(bodies[element.component_id]),
        ]
    problems += [
        pmod.build_series_resistance_problem(drive.series_join_ids[0]),
        pmod.build_series_resistance_problem(drive.series_join_ids[1]),
        pmod.build_operating_point_problem(
            drive.motor.operating_point_problem_id,
            supply_voltage=drive.source_voltage,
            constants=drive.motor.constants,
            load=drive.load,
        ),
        pmod.build_motor_heat_problem(drive.motor.heat_generation_problem_id),
    ]
    return tuple(problems)


def drive_dependencies(
    drive: PropulsionDrive,
    problems: Sequence[ScientificProblem],
    *,
    temperature_metric: str = lump.TEMPERATURE_METRIC,
) -> tuple[QuantityDependency, ...]:
    """Twenty-one directed edges. Which value flows where is stated, never inferred.

    **No endpoint receives two of them.** That is not luck: the two places where
    two sources would otherwise meet one endpoint — the machine's heat input and
    the loop's total resistance — are each routed through a declared model with
    two *distinct* named inputs, so ``FixedPointCouplingPlan``'s fan-in refusal
    is never reached and no combination rule is invented anywhere.
    """
    declared = {p.problem_id for p in problems}
    for required in (
        drive.electrical_problem_id,
        drive.motor.operating_point_problem_id,
        drive.motor.heat_generation_problem_id,
        *drive.series_join_ids,
    ):
        if required not in declared:
            raise InvalidScientificProblem(
                f"the supplied problems contain no {required!r} to wire into"
            )
    electrical = drive.electrical_problem_id
    join_a, join_b = drive.series_join_ids
    motor = drive.motor
    edges: list[QuantityDependency] = []

    def edge(src, sq, tgt, tq, unit, name, description):
        edges.append(
            QuantityDependency(
                source_problem_id=src, source_quantity=sq,
                target_problem_id=tgt, target_quantity=tq,
                unit_exemplar=unit, name=name, description=description,
            )
        )

    # ---- per conducting element: the four-edge self-heating cycle -------
    for element in drive.conducting_elements:
        cid = element.component_id
        resistivity = element.conductor.resistivity_problem_id
        resistance = element.conductor.resistance_problem_id
        thermal = element.thermal_problem_id
        for problem_id in (resistivity, resistance, thermal):
            if problem_id not in declared:
                raise InvalidScientificProblem(
                    f"element {cid!r} poses problem {problem_id!r}, which is "
                    f"not among the supplied problems; the correspondence "
                    f"between an element and its problems is stated, not "
                    f"inferred from position"
                )
        # The machine's winding dissipation does NOT go straight to its body:
        # it is one of two channels and is routed through the heat model.
        if element is not motor:
            edge(electrical, drive.power_metric(cid), thermal, lump.HEAT_INPUT,
                 lump.POWER_UNIT, f"{DEPENDENCY_HEAT}:{cid}",
                 "The power absorbed by this lead is the heat delivered to the "
                 "body it is thermally represented by.")
        edge(thermal, temperature_metric, resistivity, cmat.TEMPERATURE,
             cmat.TEMPERATURE_UNIT, f"{DEPENDENCY_TEMPERATURE}:{cid}",
             "The body temperature is the state coordinate at which this "
             "material's resistivity is evaluated.")
        edge(resistivity, cmat.RESISTIVITY_METRIC, resistance,
             cmat.RESISTIVITY_METRIC, cmat.RESISTIVITY_UNIT,
             f"{DEPENDENCY_GEOMETRY}:{cid}",
             "The evaluated material resistivity is the value the geometric "
             "resistance relation integrates over L and A.")
        edge(resistance, cmat.RESISTANCE_METRIC, electrical, resistance_name(cid),
             cmat.RESISTANCE_UNIT, f"{DEPENDENCY_RESISTANCE}:{cid}",
             "The computed resistance is the value this circuit element takes.")

    # ---- the loop resistance, as N-1 binary joins -----------------------
    edge(drive.feed.conductor.resistance_problem_id, cmat.RESISTANCE_METRIC,
         join_a, pmod.RESISTANCE_A, cmat.RESISTANCE_UNIT,
         f"{DEPENDENCY_SERIES}:{drive.feed.component_id}",
         "The feed lead is the first element of the series loop.")
    edge(motor.conductor.resistance_problem_id, cmat.RESISTANCE_METRIC,
         join_a, pmod.RESISTANCE_B, cmat.RESISTANCE_UNIT,
         f"{DEPENDENCY_SERIES}:{motor.component_id}",
         "The machine winding is the second element of the series loop.")
    edge(join_a, pmod.SERIES_RESISTANCE_METRIC, join_b, pmod.RESISTANCE_A,
         cmat.RESISTANCE_UNIT, f"{DEPENDENCY_SERIES}:{join_a}",
         "The first join's result is the left operand of the second.")
    edge(drive.ret.conductor.resistance_problem_id, cmat.RESISTANCE_METRIC,
         join_b, pmod.RESISTANCE_B, cmat.RESISTANCE_UNIT,
         f"{DEPENDENCY_SERIES}:{drive.ret.component_id}",
         "The return lead is the third element of the series loop.")
    edge(join_b, pmod.SERIES_RESISTANCE_METRIC,
         motor.operating_point_problem_id, pmod.LOOP_RESISTANCE,
         cmat.RESISTANCE_UNIT, DEPENDENCY_LOOP_RESISTANCE,
         "The total loop resistance is what the operating point divides into.")

    # ---- the machine's two couplings back into the loop -----------------
    edge(motor.operating_point_problem_id, pmod.BACK_EMF_METRIC,
         electrical, source_voltage_name(motor.back_emf_source_id),
         "volt", DEPENDENCY_BACK_EMF,
         "The machine's back-EMF is the value its opposing source takes in "
         "the circuit.")
    edge(electrical, drive.power_metric(motor.component_id),
         motor.heat_generation_problem_id, pmod.ELECTRICAL_DISSIPATION,
         lump.POWER_UNIT, DEPENDENCY_ELECTRICAL_LOSS,
         "The power absorbed by the winding is the machine's resistive heat "
         "channel.")
    edge(motor.operating_point_problem_id, pmod.INTERNAL_LOSS_POWER_METRIC,
         motor.heat_generation_problem_id, pmod.MECHANICAL_DISSIPATION,
         lump.POWER_UNIT, DEPENDENCY_MECHANICAL_LOSS,
         "The power absorbed by internal mechanical loss is the machine's "
         "second heat channel.")
    edge(motor.heat_generation_problem_id, pmod.TOTAL_DISSIPATION,
         motor.thermal_problem_id, lump.HEAT_INPUT,
         lump.POWER_UNIT, DEPENDENCY_TOTAL_HEAT,
         "The machine's total generated heat is what its body receives.")
    return tuple(edges)


def drive_plan(
    drive: PropulsionDrive,
    dependencies: Sequence[QuantityDependency],
    *,
    seed: Quantity,
    tolerance: Quantity = Quantity(1e-9, "kelvin"),
    max_iterations: int = 50,
    plan_id: str | None = None,
) -> FixedPointCouplingPlan:
    """Cut every temperature edge into a resistivity problem. **Caller-side.**

    Three tears, and **all three carry kelvin** — which is the whole reason
    ``engcore.coupling`` needed no edit. A formulation that had left the
    electromechanical loop cyclic would have had to tear it in amperes, volts,
    newton-metres or radians per second, and one plan cannot carry torn edges of
    two dimensions because it carries one scalar tolerance. That is a real
    limit; it is recorded, and it was *designed around* rather than legislated
    away.

    The rule is stated over the declared resistivity problem ids, not over a
    quantity name: ``cmat.TEMPERATURE`` and ``lump.TEMPERATURE`` are both the
    string ``"temperature"``, so a name-only filter would also match an edge
    targeting a thermal problem's own state variable.
    """
    resistivity_ids = {
        element.conductor.resistivity_problem_id
        for element in drive.conducting_elements
    }
    torn = tuple(
        TornEndpoint(dependency=d, initial_value=seed)
        for d in dependencies
        if d.target_problem_id in resistivity_ids
        and d.target_quantity == cmat.TEMPERATURE
    )
    if len(torn) != len(drive.conducting_elements):
        raise InvalidScientificProblem(
            f"expected one temperature edge per conducting element to tear, "
            f"found {len(torn)} for {len(drive.conducting_elements)} elements"
        )
    return FixedPointCouplingPlan(
        plan_id=plan_id or f"{drive.drive_id}-fixed-point",
        dependencies=tuple(dependencies),
        torn=torn,
        absolute_tolerance=tolerance,
        max_iterations=max_iterations,
    )


def build_drive_twin(
    drive: PropulsionDrive,
    bodies: Mapping[str, lump.ThermalBody],
    *,
    twin_id: str | None = None,
    version: str = "0.1.0",
) -> ScientificTwin:
    """The scientific instance description. **Not the runtime state.**

    Note what the twin makes visible that a provenance record cannot: material
    identity travels as a :class:`TwinDatum` with a name, whereas
    ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]`` and has no home
    for a name. That gap is `COMPOSITE-SYSTEM0`'s measurement and it is
    unchanged here; it is recorded, not routed around through metadata.
    """
    declarations: list[TwinDatum] = [
        TwinDatum(f"source_voltage:{SOURCE_ID}", drive.source_voltage,
                  TwinDatumRole.CONTROL),
    ]
    models: list[ModelReference] = [
        ModelReference(cmat.GEOMETRIC_RESISTANCE_MODEL.model_id,
                       cmat.GEOMETRIC_RESISTANCE_MODEL.version),
        ModelReference(lump.LUMPED_CAPACITY_MODEL.model_id,
                       lump.LUMPED_CAPACITY_MODEL.version),
        ModelReference(pmat.CONDUCTOR_THERMAL_MASS_MODEL.model_id,
                       pmat.CONDUCTOR_THERMAL_MASS_MODEL.version),
        ModelReference(pmod.SERIES_LOOP_RESISTANCE_MODEL.model_id,
                       pmod.SERIES_LOOP_RESISTANCE_MODEL.version),
        ModelReference(pmod.MOTOR_HEAT_GENERATION_MODEL.model_id,
                       pmod.MOTOR_HEAT_GENERATION_MODEL.version),
        ModelReference(pmod.DRIVE_OPERATING_POINT_MODEL.model_id,
                       pmod.DRIVE_OPERATING_POINT_MODEL.version),
        ModelReference(rot.BACK_EMF_MODEL.model_id, rot.BACK_EMF_MODEL.version),
        ModelReference(rot.TORQUE_PRODUCTION_MODEL.model_id,
                       rot.TORQUE_PRODUCTION_MODEL.version),
        ModelReference(rot.VISCOUS_ROTATIONAL_LOSS_MODEL.model_id,
                       rot.VISCOUS_ROTATIONAL_LOSS_MODEL.version),
        ModelReference(rot.QUADRATIC_ROTATIONAL_LOAD_MODEL.model_id,
                       rot.QUADRATIC_ROTATIONAL_LOAD_MODEL.version),
        ModelReference(rot.ROTATIONAL_TORQUE_BALANCE_MODEL.model_id,
                       rot.ROTATIONAL_TORQUE_BALANCE_MODEL.version),
    ]
    seen = {m.key for m in models}
    for element in drive.conducting_elements:
        cid = element.component_id
        body = bodies[cid]
        material = element.material
        resistivity_model = element.conductor.material.resistivity_model()
        reference = ModelReference(resistivity_model.model_id,
                                   resistivity_model.version)
        if reference.key not in seen:
            models.append(reference)
            seen.add(reference.key)
        declarations += [
            TwinDatum(f"length:{cid}", element.conductor.length,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"cross_sectional_area:{cid}",
                      element.conductor.cross_sectional_area,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"heat_capacity:{cid}", body.heat_capacity,
                      TwinDatumRole.PARAMETER,
                      description=(
                          f"DERIVED from material {material.name!r} and the "
                          f"declared geometry through "
                          f"{pmat.CONDUCTOR_THERMAL_MASS_MODEL.model_id}; not "
                          f"declared independently."
                      )),
            TwinDatum(f"ambient_conductance:{cid}", body.ambient_conductance,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"ambient_temperature:{cid}", body.ambient_temperature,
                      TwinDatumRole.OPERATING_CONDITION),
            TwinDatum(f"temperature:{cid}", body.initial_temperature,
                      TwinDatumRole.STATE,
                      description="Body temperature at the start of the interval."),
            TwinDatum(f"density:{cid}", material.density, TwinDatumRole.PARAMETER,
                      description=(
                          f"Declared property of material {material.name!r}. "
                          f"Source: {material.source}"
                      )),
            TwinDatum(f"specific_heat:{cid}", material.specific_heat,
                      TwinDatumRole.PARAMETER,
                      description=(
                          f"Declared property of material {material.name!r}. "
                          f"Source: {material.source}"
                      )),
        ]
        for parameter in element.conductor.material.resistivity_parameters():
            declarations.append(
                TwinDatum(f"{parameter.name}:{cid}", parameter.value,
                          TwinDatumRole.PARAMETER,
                          description=(
                              f"Declared property of material "
                              f"{material.name!r}. Source: "
                              f"{element.conductor.material.source}"
                          ))
            )
    for parameter in (
        *drive.motor.constants.machine_parameters(),
        *drive.load.load_parameters(),
    ):
        declarations.append(
            TwinDatum(f"{parameter.name}:{drive.motor.component_id}",
                      parameter.value, TwinDatumRole.PARAMETER,
                      description=parameter.description)
        )
    return ScientificTwin(
        twin_id=twin_id or drive.drive_id,
        version=version,
        kind=TwinKind.CONCEPT,
        name="Series electromechanical drive with self-heating leads and machine",
        description=(
            "An idealised DC-equivalent machine driving a quadratic mechanical "
            "load through a single series loop, with two leads and the machine "
            "winding whose resistances are computed from declared materials "
            "and geometries, each thermally represented as a lumped body whose "
            "capacity is derived from the same material declaration."
        ),
        models=tuple(models),
        declarations=tuple(declarations),
        assumptions=(
            "each conductor, its thermal body and — for the machine — its "
            "shaft are the same physical object",
            "the whole dissipated power of a lead enters its body",
            "the machine's body receives its winding dissipation and its "
            "internal mechanical loss, and nothing else",
            "the mechanical output power leaves the system and is not "
            "represented thermally",
            "the resistivity is evaluated at the transported temperature and "
            "the resistance is held constant over the integrated interval",
            "MODEL-CONSISTENT ONLY: the machine constants and the load "
            "coefficients are fixture values and the material data is from a "
            "handbook; nothing here is validated against hardware",
        ),
    )


# =====================================================================
# Admission (enforced) and applicability (reported)
# =====================================================================

def admit_drive(drive: PropulsionDrive, *, seed_temperature: Quantity) -> None:
    """Refuse a drive that must not be executed, **before any solver exists**.

    Four classes of refusal, in the order a reader needs them:

    1. **Energy conservation.** ``k_e`` and ``k_t`` must be the same number in
       SI. A machine that creates energy is refused, not reported.
    2. **Geometry and material applicability**, through the electrical domain's
       own ``admit_conductor`` — reused, not restated.
    3. **Thermal-mass admissibility**: density, specific heat, length and area
       must satisfy the thermal-mass model's declared validity domain. All four
       are parameters, so this is assessable before anything runs.
    4. **The operating point's own validity domain**: supply voltage, both
       machine constants and both load coefficients.

    What it cannot gate is whether the *converged* state stayed inside a
    material's declared range. That question only exists after a run and is
    answered by :func:`assess_run_applicability` — by reporting, never by
    refusing, because refusing after the fact would destroy the record that
    makes the finding readable.
    """
    if not isinstance(drive, PropulsionDrive):
        raise InvalidScientificProblem("admit_drive expects a PropulsionDrive")
    if not isinstance(seed_temperature, Quantity):
        raise InvalidScientificProblem("seed_temperature must be a Quantity")
    seed_temperature.require_compatible(
        cmat.TEMPERATURE_UNIT, context="drive seed temperature"
    )

    rot.require_energy_consistent_constants(drive.motor.constants)

    for element in drive.conducting_elements:
        cmat.admit_conductor(element.conductor, seed_temperature)
        assessment = pmat.assess_thermal_mass_validity(
            element.conductor, element.material
        )
        if assessment.status is not ValidityStatus.IN_DOMAIN:
            raise InvalidScientificProblem(
                f"element {element.component_id!r} is inadmissible: the "
                f"conductor thermal-mass model reports "
                f"{assessment.status.value} (violated: "
                f"{list(assessment.violated)}, unknown: "
                f"{list(assessment.unknown)})"
            )

    operating_point = pmod.build_operating_point_problem(
        drive.motor.operating_point_problem_id,
        supply_voltage=drive.source_voltage,
        constants=drive.motor.constants,
        load=drive.load,
    )
    assessment = pmod.DRIVE_OPERATING_POINT_MODEL.assess_validity(
        operating_point.validity_context()
    )
    if assessment.status is not ValidityStatus.IN_DOMAIN:
        raise InvalidScientificProblem(
            f"drive {drive.drive_id!r} is inadmissible: the operating-point "
            f"model reports {assessment.status.value} (violated: "
            f"{list(assessment.violated)}, unknown: "
            f"{list(assessment.unknown)})"
        )


def assess_run_applicability(
    drive: PropulsionDrive, run: CoupledRun
) -> dict[str, ValidityAssessment]:
    """Was each material's property set applicable at the state it converged to?

    **Assess, never refuse.** A run that converged outside a declared range is a
    finding about the answer.
    """
    assessments: dict[str, ValidityAssessment] = {}
    for element in drive.conducting_elements:
        endpoint = (element.conductor.resistivity_problem_id, cmat.TEMPERATURE)
        temperature = run.final_values.get(endpoint)
        if temperature is None:
            raise InvalidScientificProblem(
                f"the run carries no final value for {endpoint!r}; it did not "
                f"execute this drive"
            )
        assessments[element.component_id] = cmat.assess_material_applicability(
            element.conductor.material, temperature
        )
    return assessments


# =====================================================================
# Energy accounting — the second enforcement point
# =====================================================================

@dataclass(frozen=True)
class EnergyAccounting:
    """Every term of the converged power balance, and the three residuals.

    Deliberately **not serialized**: it is an ephemeral report about one run, it
    is entirely recoverable from that run's own results, and a stored copy would
    be a second authority on numbers the ``CoupledRun`` already carries.
    """

    source_power: Quantity
    feed_loss: Quantity
    return_loss: Quantity
    winding_loss: Quantity
    mechanical_output: Quantity
    internal_mechanical_loss: Quantity
    balance_residual: Quantity
    current_disagreement: Quantity
    converted_power_disagreement: Quantity

    @property
    def relative_balance_residual(self) -> float:
        return abs(
            self.balance_residual.magnitude_in("watt")
        ) / abs(self.source_power.magnitude_in("watt"))


def _relative(actual: float, expected: float) -> float:
    return abs(actual - expected) / max(abs(expected), 1.0)


def reconcile_drive_energy(
    drive: PropulsionDrive,
    run: CoupledRun,
    *,
    relative_tolerance: float = ENERGY_RELATIVE_TOLERANCE,
) -> EnergyAccounting:
    """Three independent reconciliations, and it **raises**. Enforcement.

    A check whose only effect is a field nobody consults is not a guard. This
    repository has the receipt: an external provider's power once disagreed,
    the validation report said ``FAIL``, the value was consumed anyway and the
    coupling converged 18 K from the truth.

    Three relations. ``R1`` is genuinely independent — its residual is exactly
    ``I*omega*(k_e - k_t)``, so it is the one that catches a violated
    conservation law, and an injection test proves it fires. ``R2`` and ``R3``
    are **not** independent of each other: ``R3`` is close to ``R2`` multiplied
    by the same ``E`` both sides consumed, so it adds sign detection at the
    electromechanical boundary rather than a third physical channel. The
    preregistration's §5.1 called all three independent; that over-counts by
    about one, and the correction is recorded rather than left standing.

    ``R1`` the supply's delivered power — from node voltages and the source's
    branch current, computed by modified nodal analysis — against the sum of
    the two lead losses, the winding loss, the mechanical output and the
    internal mechanical loss, which come from three different problems.

    ``R2`` the winding current the circuit computed against the current the
    machine's closed form computed. The two solve the same KVL by different
    routes, which is precisely why the duplication is worth keeping.

    ``R3`` the power the circuit says the back-EMF source absorbed against the
    converted power ``E*I`` the machine reports. This is the electromechanical
    boundary, checked from both sides.

    ``total_source_delivered_power`` is deliberately **not** consumed: with a
    second voltage source in the loop that metric is the *net* over all sources
    and no longer means "electrical input power". One name, two meanings, is a
    defect class this repository has caught before.
    """
    final = run.final
    electrical = final.result_for(drive.electrical_problem_id)
    operating = final.result_for(drive.motor.operating_point_problem_id)

    absorbed_by_supply = electrical.value(
        SOURCE_POWER_METRIC.format(component_id=SOURCE_ID)
    ).magnitude_in("watt")
    source_power = -absorbed_by_supply

    feed_loss = electrical.value(
        drive.power_metric(drive.feed.component_id)
    ).magnitude_in("watt")
    return_loss = electrical.value(
        drive.power_metric(drive.ret.component_id)
    ).magnitude_in("watt")
    winding_loss = electrical.value(
        drive.power_metric(drive.motor.component_id)
    ).magnitude_in("watt")
    mechanical_output = operating.value(
        pmod.MECHANICAL_OUTPUT_POWER_METRIC
    ).magnitude_in("watt")
    internal_loss = operating.value(
        pmod.INTERNAL_LOSS_POWER_METRIC
    ).magnitude_in("watt")

    sinks = (
        feed_loss + return_loss + winding_loss + mechanical_output + internal_loss
    )
    balance = source_power - sinks
    if abs(balance) > relative_tolerance * max(abs(source_power), 1.0):
        raise InvalidScientificProblem(
            f"drive {drive.drive_id!r} does not conserve energy: the source "
            f"delivers {source_power!r} W while the declared sinks account for "
            f"{sinks!r} W (feed {feed_loss!r}, return {return_loss!r}, winding "
            f"{winding_loss!r}, mechanical output {mechanical_output!r}, "
            f"internal mechanical loss {internal_loss!r}). Residual "
            f"{balance!r} W exceeds {relative_tolerance:.1e} relative. A "
            f"result that creates or destroys energy is refused, not reported."
        )

    circuit_current = abs(
        electrical.value(
            RESISTOR_CURRENT_METRIC.format(component_id=drive.motor.component_id)
        ).magnitude_in("ampere")
    )
    machine_current = operating.value(pmod.CURRENT_METRIC).magnitude_in("ampere")
    current_gap = _relative(circuit_current, machine_current)
    if current_gap > relative_tolerance:
        raise InvalidScientificProblem(
            f"drive {drive.drive_id!r}: the circuit computed a winding current "
            f"of {circuit_current!r} A while the machine's own closed form "
            f"computed {machine_current!r} A. Two representations of one loop "
            f"KVL disagree by {current_gap:.3e} relative, above "
            f"{relative_tolerance:.1e}; the composition is refused rather than "
            f"reported."
        )

    absorbed_by_emf = electrical.value(
        SOURCE_POWER_METRIC.format(component_id=drive.motor.back_emf_source_id)
    ).magnitude_in("watt")
    converted = operating.value(pmod.CONVERTED_POWER_METRIC).magnitude_in("watt")
    converted_gap = _relative(absorbed_by_emf, converted)
    if converted_gap > relative_tolerance:
        raise InvalidScientificProblem(
            f"drive {drive.drive_id!r}: the circuit says the back-EMF source "
            f"absorbed {absorbed_by_emf!r} W while the machine reports "
            f"{converted!r} W crossing the electromechanical boundary. The two "
            f"sides of the conversion disagree by {converted_gap:.3e} relative, "
            f"above {relative_tolerance:.1e}."
        )

    return EnergyAccounting(
        source_power=Quantity(source_power, "watt"),
        feed_loss=Quantity(feed_loss, "watt"),
        return_loss=Quantity(return_loss, "watt"),
        winding_loss=Quantity(winding_loss, "watt"),
        mechanical_output=Quantity(mechanical_output, "watt"),
        internal_mechanical_loss=Quantity(internal_loss, "watt"),
        balance_residual=Quantity(balance, "watt"),
        current_disagreement=Quantity(current_gap, "dimensionless"),
        converted_power_disagreement=Quantity(converted_gap, "dimensionless"),
    )


# =====================================================================
# Per-problem execution, supplied by this pack
# =====================================================================

def _quantity_inputs(problem: ScientificProblem) -> dict[str, Quantity]:
    """The problem's Quantity-valued parameters, and only those.

    ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]``, so a typed
    categorical parameter — which is how material identity is declared — cannot
    be recorded there. Measured by `COMPOSITE-SYSTEM0`, unchanged here, and
    deliberately not routed around through ``metadata``.
    """
    return {
        name: value
        for name, value in problem.parameter_values().items()
        if isinstance(value, Quantity)
    }


def _result(
    *, run_id: str, problem: ScientificProblem, solver, prepared, raw,
    metrics, model_definitions, realization, extra_inputs, assumptions,
    uncertainty_note: str,
) -> ScientificResult:
    """One shape for every result this pack produces.

    ``model_definitions`` may name more than one record, and only the **first**
    is paired with ``realization``. The rest carry ``realization=None``, which
    is a true answer rather than a gap: no ``ModelRealizationDefinition`` can
    state that one closed form discharged several model records jointly.
    """
    references = tuple(
        ModelReference(m.model_id, m.version) for m in model_definitions
    )
    bindings = tuple(
        ExecutionBinding(
            model=reference,
            realization=realization.reference() if index == 0 and realization else None,
            solver=solver.identity,
        )
        for index, reference in enumerate(references)
    )
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.systems.propulsion.drive/0.1.0",
        bindings=bindings,
        inputs=_quantity_inputs(problem) | dict(extra_inputs),
        assumptions=assumptions,
    )
    return ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=tuple((r.model_id, r.version) for r in references),
        solver=solver.identity,
        convergence=raw.convergence,
        validation=solver.validate(prepared, raw),
        uncertainty={
            name: Uncertainty.unknown(uncertainty_note) for name in metrics
        },
        assumptions=assumptions,
        provenance=provenance,
    )


def _resistivity_result(
    *, run_id: str, element: _ConductingElement, problem: ScientificProblem,
    temperature: Quantity,
) -> ScientificResult:
    material = element.conductor.material
    solver = cmat.resistivity_solver_for(material)
    solver.bind_conductor(element.conductor, problem.problem_id,
                          temperature=temperature)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    definition = material.resistivity_model()
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        model_definitions=(definition,),
        realization=prepared.payload.realization,
        extra_inputs={cmat.TEMPERATURE: temperature},
        assumptions=definition.assumptions,
        uncertainty_note=(
            "no uncertainty quantification is performed on the declared "
            "material property set"
        ),
    )


def _resistance_result(
    *, run_id: str, element: _ConductingElement, problem: ScientificProblem,
    resistivity: Quantity,
) -> ScientificResult:
    solver = cmat.GeometricResistanceSolver()
    solver.bind_conductor(element.conductor, problem.problem_id,
                          resistivity=resistivity)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        model_definitions=(cmat.GEOMETRIC_RESISTANCE_MODEL,),
        realization=prepared.payload.realization,
        extra_inputs={cmat.RESISTIVITY_METRIC: resistivity},
        assumptions=cmat.GEOMETRIC_RESISTANCE_MODEL.assumptions,
        uncertainty_note=(
            "no uncertainty quantification is performed on the declared geometry"
        ),
    )


def _thermal_result(
    *, run_id: str, body: lump.ThermalBody, problem: ScientificProblem,
    heat_input: Quantity,
) -> ScientificResult:
    solver = lump.LumpedThermalSolver()
    solver.bind_body(body, problem.problem_id, heat_input=heat_input)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        model_definitions=(lump.LUMPED_CAPACITY_MODEL,),
        realization=prepared.payload.realization,
        extra_inputs={
            lump.HEAT_INPUT: heat_input,
            lump.AMBIENT_TEMPERATURE: body.ambient_temperature,
            # The state at t0, identical in every iteration: the loop iterates
            # the coupling, it does not march time.
            lump.TEMPERATURE: body.initial_temperature,
        },
        assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
        uncertainty_note=(
            "no uncertainty quantification is performed on the lumped thermal "
            "declaration"
        ),
    )


def _series_result(
    *, run_id: str, problem: ScientificProblem, left: Quantity, right: Quantity
) -> ScientificResult:
    solver = pmod.SeriesResistanceSolver()
    solver.bind_operands(problem.problem_id, left=left, right=right)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        model_definitions=(pmod.SERIES_LOOP_RESISTANCE_MODEL,),
        realization=prepared.payload.realization,
        extra_inputs={pmod.RESISTANCE_A: left, pmod.RESISTANCE_B: right},
        assumptions=pmod.SERIES_LOOP_RESISTANCE_MODEL.assumptions,
        uncertainty_note="an exact sum of two supplied resistances",
    )


def _heat_result(
    *, run_id: str, problem: ScientificProblem, electrical: Quantity,
    mechanical: Quantity,
) -> ScientificResult:
    solver = pmod.MotorHeatGenerationSolver()
    solver.bind_operands(problem.problem_id, left=electrical, right=mechanical)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        model_definitions=(pmod.MOTOR_HEAT_GENERATION_MODEL,),
        realization=prepared.payload.realization,
        extra_inputs={
            pmod.ELECTRICAL_DISSIPATION: electrical,
            pmod.MECHANICAL_DISSIPATION: mechanical,
        },
        assumptions=pmod.MOTOR_HEAT_GENERATION_MODEL.assumptions,
        uncertainty_note="an exact sum of two supplied dissipation channels",
    )


def _operating_point_result(
    *, run_id: str, drive: PropulsionDrive, problem: ScientificProblem,
    loop_resistance: Quantity,
) -> ScientificResult:
    solver = pmod.DriveOperatingPointSolver()
    solver.verify_problem_matches_drive(
        problem, supply_voltage=drive.source_voltage,
        constants=drive.motor.constants, load=drive.load,
    )
    solver.bind_drive(
        problem.problem_id,
        supply_voltage=drive.source_voltage,
        constants=drive.motor.constants,
        load=drive.load,
        loop_resistance=loop_resistance,
    )
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return _result(
        run_id=run_id, problem=problem, solver=solver, prepared=prepared, raw=raw,
        metrics=solver.extract_metrics(prepared, raw),
        # SIX model records, ONE realization. The five rotational claims are
        # discharged by the same closed form and carry realization=None.
        model_definitions=(
            pmod.DRIVE_OPERATING_POINT_MODEL,
            rot.BACK_EMF_MODEL,
            rot.TORQUE_PRODUCTION_MODEL,
            rot.VISCOUS_ROTATIONAL_LOSS_MODEL,
            rot.QUADRATIC_ROTATIONAL_LOAD_MODEL,
            rot.ROTATIONAL_TORQUE_BALANCE_MODEL,
        ),
        realization=prepared.payload.realization,
        extra_inputs={pmod.LOOP_RESISTANCE: loop_resistance},
        assumptions=(
            pmod.DRIVE_OPERATING_POINT_MODEL.assumptions
            + rot.ROTATIONAL_TORQUE_BALANCE_MODEL.assumptions
        ),
        uncertainty_note=(
            "no uncertainty quantification is performed on the declared "
            "machine constants or load coefficients"
        ),
    )


def initial_state(
    drive: PropulsionDrive,
    bodies: Mapping[str, lump.ThermalBody],
    *,
    seed_temperature: Quantity,
    run_id: str,
) -> tuple[dict[str, Quantity], Quantity]:
    """The resistances and back-EMF the *first* electrical record describes.

    Every number here goes through a declared model and a published solver, for
    the same reason ``COMPOSITE-SYSTEM0``'s bootstrap does: one line of Python
    arithmetic would be an unmodelled scientific claim with no ``ExecutionBinding``.

    Evaluated at the **seed**, so the declared record reproduces iteration 1
    exactly instead of describing a state at which nothing ever is.
    """
    resistances: dict[str, Quantity] = {}
    for element in drive.conducting_elements:
        rho = _resistivity_result(
            run_id=f"{run_id}-seed-{element.component_id}",
            element=element,
            problem=cmat.build_resistivity_problem(element.conductor),
            temperature=seed_temperature,
        ).value(cmat.RESISTIVITY_METRIC)
        resistances[element.component_id] = _resistance_result(
            run_id=f"{run_id}-seed-{element.component_id}",
            element=element,
            problem=cmat.build_geometric_resistance_problem(element.conductor),
            resistivity=rho,
        ).value(cmat.RESISTANCE_METRIC)

    join_a, join_b = drive.series_join_ids
    partial = _series_result(
        run_id=f"{run_id}-seed-{join_a}",
        problem=pmod.build_series_resistance_problem(join_a),
        left=resistances[drive.feed.component_id],
        right=resistances[drive.motor.component_id],
    ).value(pmod.SERIES_RESISTANCE_METRIC)
    loop = _series_result(
        run_id=f"{run_id}-seed-{join_b}",
        problem=pmod.build_series_resistance_problem(join_b),
        left=partial,
        right=resistances[drive.ret.component_id],
    ).value(pmod.SERIES_RESISTANCE_METRIC)

    back_emf = _operating_point_result(
        run_id=f"{run_id}-seed-operating-point",
        drive=drive,
        problem=pmod.build_operating_point_problem(
            drive.motor.operating_point_problem_id,
            supply_voltage=drive.source_voltage,
            constants=drive.motor.constants,
            load=drive.load,
        ),
        loop_resistance=loop,
    ).value(pmod.BACK_EMF_METRIC)
    return resistances, back_emf


def _executors(
    drive: PropulsionDrive,
    bodies: Mapping[str, lump.ThermalBody],
    problems: Sequence[ScientificProblem],
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]]:
    """problem_id -> how this pack solves it, given its transported inputs.

    The only place the loop learns which science sits behind which problem, and
    it is built here from declarations the caller supplied. The iteration itself
    contains no electrical, thermal, material or mechanical branch.
    """
    by_id = {p.problem_id: p for p in problems}
    table: dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]] = {}

    def electrical_call(inputs: Mapping[str, Quantity], run_id: str):
        resistances = {
            element.component_id: inputs[resistance_name(element.component_id)]
            for element in drive.conducting_elements
        }
        back_emf = inputs[source_voltage_name(drive.motor.back_emf_source_id)]
        return circuit_solver(drive.circuit_at(resistances, back_emf), run_id)

    table[drive.electrical_problem_id] = electrical_call

    for element in drive.conducting_elements:
        resistivity = by_id[element.conductor.resistivity_problem_id]
        resistance = by_id[element.conductor.resistance_problem_id]
        thermal = by_id[element.thermal_problem_id]
        body = bodies[element.component_id]

        def resistivity_call(inputs, run_id, _e=element, _p=resistivity):
            return _resistivity_result(
                run_id=run_id, element=_e, problem=_p,
                temperature=inputs[cmat.TEMPERATURE],
            )

        def resistance_call(inputs, run_id, _e=element, _p=resistance):
            return _resistance_result(
                run_id=run_id, element=_e, problem=_p,
                resistivity=inputs[cmat.RESISTIVITY_METRIC],
            )

        def thermal_call(inputs, run_id, _b=body, _p=thermal):
            return _thermal_result(
                run_id=run_id, body=_b, problem=_p,
                heat_input=inputs[lump.HEAT_INPUT],
            )

        table[resistivity.problem_id] = resistivity_call
        table[resistance.problem_id] = resistance_call
        table[thermal.problem_id] = thermal_call

    for join_id in drive.series_join_ids:
        problem = by_id[join_id]

        def series_call(inputs, run_id, _p=problem):
            return _series_result(
                run_id=run_id, problem=_p,
                left=inputs[pmod.RESISTANCE_A], right=inputs[pmod.RESISTANCE_B],
            )

        table[join_id] = series_call

    operating = by_id[drive.motor.operating_point_problem_id]

    def operating_call(inputs, run_id, _p=operating):
        return _operating_point_result(
            run_id=run_id, drive=drive, problem=_p,
            loop_resistance=inputs[pmod.LOOP_RESISTANCE],
        )

    table[operating.problem_id] = operating_call

    heat = by_id[drive.motor.heat_generation_problem_id]

    def heat_call(inputs, run_id, _p=heat):
        return _heat_result(
            run_id=run_id, problem=_p,
            electrical=inputs[pmod.ELECTRICAL_DISSIPATION],
            mechanical=inputs[pmod.MECHANICAL_DISSIPATION],
        )

    table[heat.problem_id] = heat_call
    return table


def declared_problem_ids(drive: PropulsionDrive) -> frozenset[str]:
    """Every problem id this drive poses, computable without solving anything.

    Exists so a plan naming a problem the composition does not pose is refused
    **before** the bootstrap executes a single solver.
    """
    ids = {drive.electrical_problem_id, *drive.series_join_ids}
    for element in drive.elements:
        ids |= element.declared_problem_ids()
    return frozenset(ids)


def _refuse_unresolved_edges(
    drive: PropulsionDrive, plan: FixedPointCouplingPlan
) -> None:
    declared = declared_problem_ids(drive)
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
            f"{unresolved}, which drive {drive.drive_id!r} does not pose; a "
            f"connection that resolves to nothing is refused before anything "
            f"is executed, not after"
        )


def _seed_of(drive: PropulsionDrive, plan: FixedPointCouplingPlan) -> Quantity:
    """The seed the plan declares, read structurally from the torn endpoints."""
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
            f"plan {plan.plan_id!r} seeds the elements at {len(seeds)} "
            f"different temperatures; the declared electrical record could "
            f"then describe no single state, so the pack refuses rather than "
            f"picking one"
        )
    return seeds.pop()


@dataclass(frozen=True)
class DriveRun:
    """What executing a drive produces. **Ephemeral; not serialized.**

    ``accounting`` is ``None`` exactly when the coupling did not converge.
    Failing to converge and violating energy conservation are different
    findings, and reconciling a state the loop never reached would report a
    residual of an equation nothing claims to have solved.
    """

    coupled: CoupledRun
    thermal_masses: Mapping[str, ScientificResult]
    accounting: EnergyAccounting | None

    @property
    def converged(self) -> bool:
        return self.coupled.outcome is CouplingOutcome.CRITERION_MET


def compose(
    drive: PropulsionDrive,
    *,
    seed: Quantity,
    run_id: str = "propulsion-drive",
    temperature_metric: str = lump.TEMPERATURE_METRIC,
    tolerance: Quantity = Quantity(1e-9, "kelvin"),
    max_iterations: int = 50,
) -> tuple[
    dict[str, lump.ThermalBody],
    dict[str, ScientificResult],
    tuple[ScientificProblem, ...],
    tuple[QuantityDependency, ...],
    FixedPointCouplingPlan,
]:
    """Bodies, their derivation provenance, problems, edges and a plan.

    It admits the drive **before** deriving anything, for the same reason
    :func:`run_propulsion_drive` does: the derivation and the bootstrap execute
    real solvers, so a gate placed after them would let an inadmissible
    declaration reach an evaluator.
    """
    admit_drive(drive, seed_temperature=seed)
    bodies, masses = derive_thermal_masses(drive, run_id=f"{run_id}-thermal-mass")
    resistances, back_emf = initial_state(
        drive, bodies, seed_temperature=seed, run_id=run_id
    )
    problems = drive_problems(drive, bodies, resistances, back_emf)
    dependencies = drive_dependencies(
        drive, problems, temperature_metric=temperature_metric
    )
    plan = drive_plan(
        drive, dependencies, seed=seed, tolerance=tolerance,
        max_iterations=max_iterations,
    )
    return bodies, masses, problems, dependencies, plan


def run_propulsion_drive(
    drive: PropulsionDrive,
    plan: FixedPointCouplingPlan,
    *,
    run_id: str = "propulsion-drive",
    circuit_solver: CircuitSolver = native_circuit_solver,
    relative_tolerance: float = ENERGY_RELATIVE_TOLERANCE,
) -> DriveRun:
    """Admit, derive, build, iterate, and then **reconcile or refuse**.

    The admission gate is called here, on the executed path, rather than left to
    a caller who may skip it: a gate that only runs when someone remembers is
    detection, not enforcement.
    """
    seed = _seed_of(drive, plan)
    _refuse_unresolved_edges(drive, plan)
    admit_drive(drive, seed_temperature=seed)
    bodies, masses = derive_thermal_masses(drive, run_id=f"{run_id}-thermal-mass")
    resistances, back_emf = initial_state(
        drive, bodies, seed_temperature=seed, run_id=run_id
    )
    problems = drive_problems(drive, bodies, resistances, back_emf)
    run = run_fixed_point(
        problems,
        _executors(drive, bodies, problems, circuit_solver),
        plan,
        run_id=run_id,
        software_version="engcore.systems.propulsion.drive/0.1.0",
        assumptions=(
            "the resistivity is evaluated at the transported temperature and "
            "the resistance is held constant over the integrated interval; "
            "this is an implicit statement over one interval and carries a "
            "coupling error that is not quantified here",
            "the whole dissipated power of a lead enters its body",
            "the machine's body receives its winding dissipation and its "
            "internal mechanical loss, and nothing else",
            "the mechanical output power leaves the system and is not "
            "represented thermally",
            "MODEL-CONSISTENT ONLY: fixture machine constants and handbook "
            "material data; nothing here is validated against hardware",
        ),
    )
    accounting = None
    if run.outcome is CouplingOutcome.CRITERION_MET:
        accounting = reconcile_drive_energy(
            drive, run, relative_tolerance=relative_tolerance
        )
    return DriveRun(coupled=run, thermal_masses=masses, accounting=accounting)
