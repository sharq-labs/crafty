"""The L2 steelman — every representable fact into a channel that already exists.

Preregistration §6 makes this binding: **no gap may be declared before a maximal
honest attempt in existing typed contracts.** `HOSTILE-CORE-STRESS` withdrew two
findings that turned out to be false gaps, both caught by asking which typed
channel had not been tried, and this module exists so the same question is
answered by execution rather than by assertion.

So every entry in :data:`ATTEMPTS` is **run**, and the outcomes are of two kinds
that the adversarial pass required be distinguished:

* **executed refusals** — nine of eleven. A contract was called and either raised
  or accepted; the recorded ``detail`` is that contract's own exception text.
* **executed structural absences** — two of eleven
  (:func:`_attempt_nonuniform_initial_condition_as_bulk`,
  :func:`_attempt_numerics_as_solver_settings`). Nothing raises, because nothing
  can: the finding is that a *field does not exist*, established by reading
  ``dataclasses.fields`` of the live record rather than by calling it.

Neither is an assertion about what a contract would do. Both are measurements.

The channels available, and nothing else:

``ScientificParameter``        a configured value: Quantity, integer, flag, category
``ScientificVariable``         a named quantity with a unit and a role
``InitialCondition``           a variable's value at t0
``BoundaryCondition``          kind + region + value + coefficients
``ScientificDataReference``    bulk float64 identified by content digest
``SolverSettings``             tolerances and options — see the finding about it
``ScientificProblem.metadata`` the untyped escape hatch. **Not a channel.** It is
                               recorded as unavailable, because using it is what
                               this milestone is measuring the cost of.

What this module does NOT do: it does not modify a domain, it does not call a
domain's own ``build_*_problem``, and it does not invent a new record. Each L2
problem is constructed here from core contracts alone, so that what it holds is
exactly what the core can hold.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from engcore.scientific.ir.conditions import (
    BoundaryCondition,
    BoundaryKind,
    InitialCondition,
)
from engcore.scientific.ir.problem import ModelReference, ScientificProblem
from engcore.scientific.ir.values import CategoricalValue, IntegerValue
from engcore.scientific.ir.variables import (
    ScientificParameter,
    ScientificVariable,
    VariableRole,
)
from engcore.scientific.results.data_reference import ScientificDataReference
from engcore.scientific.units.quantity import Quantity

from . import cases
from .schemas import (
    CSTR_NUMERICS_SCHEMA,
    DC_STRUCTURE_SCHEMA,
    SLAB_STRUCTURE_SCHEMA,
)

__all__ = [
    "Channel",
    "AttemptOutcome",
    "EncodingAttempt",
    "ColumnEncoding",
    "ATTEMPTS",
    "ENCODINGS",
    "COLUMNS",
    "DC_STRUCTURE_SCHEMA",
    "SLAB_STRUCTURE_SCHEMA",
    "CSTR_NUMERICS_SCHEMA",
]

COLUMNS: tuple[str, ...] = ("col-dc", "col-slab", "col-cstr", "col-material")

class Channel(str, Enum):
    PARAMETER = "ScientificParameter"
    VARIABLE = "ScientificVariable"
    INITIAL_CONDITION = "InitialCondition"
    BOUNDARY_CONDITION = "BoundaryCondition"
    DATA_REFERENCE = "ScientificDataReference"
    SOLVER_SETTINGS = "SolverSettings"


class AttemptOutcome(str, Enum):
    """What happened when the fact was pushed into the channel."""

    #: The channel accepted it, typed, with its dimension checked.
    WORKS = "works"
    #: A contract refused it outright. The exception text is recorded.
    REFUSED_BY_TYPE = "refused-by-type"
    #: It fits mechanically, but the scientific meaning would live in the
    #: *spelling of a name* rather than in a typed field.
    MEANING_IN_KEY = "meaning-in-key"
    #: The record exists and round-trips, but nothing persistable references it,
    #: so a stored problem cannot carry it.
    NO_PERSISTABLE_HOME = "no-persistable-home"
    #: It fits, and placing it there puts a numerical choice inside the identity
    #: of the physical problem.
    LEAKS_INTO_IDENTITY = "leaks-into-identity"


@dataclass(frozen=True)
class EncodingAttempt:
    """One executed attempt to put one fact into one existing channel."""

    column: str
    fact: str
    channel: Channel
    outcome: AttemptOutcome
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "fact": self.fact,
            "channel": self.channel.value,
            "outcome": self.outcome.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ColumnEncoding:
    """One column at L2, plus whatever L2 could not hold."""

    column: str
    problem: ScientificProblem
    #: The residue, serialized. ``None`` means L2 was sufficient.
    structure_payload: Mapping[str, Any] | None = None
    structure_schema: str | None = None

    def to_payloads(self) -> dict[str, Any]:
        payloads: dict[str, Any] = {"problem": self.problem.to_dict()}
        if self.structure_payload is not None:
            payloads["structure"] = dict(self.structure_payload)
        return payloads


# =====================================================================
# Executed encoding attempts
# =====================================================================

def _try(fn) -> tuple[bool, str]:
    """Run an encoding attempt; return whether a contract accepted it."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - the exception type IS the finding
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def _attempt_incidence_as_bulk() -> EncodingAttempt:
    """Node ids into `ScientificDataReference`. Bulk data is float64 only."""
    ok, detail = _try(
        lambda: ScientificDataReference.for_values(
            "R1:terminals", ["n0", "n1"], unit="dimensionless"
        )
    )
    return EncodingAttempt(
        column="col-dc",
        fact="which nodes element R1 connects, in terminal order",
        channel=Channel.DATA_REFERENCE,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail or "unexpectedly accepted a non-numeric payload",
    )


def _attempt_incidence_as_boundary_condition() -> EncodingAttempt:
    """Incidence as a boundary condition, given every chance to succeed.

    An earlier form of this attempt omitted ``value`` and was refused for that
    reason — a refusal about a missing value, recorded as though it were a
    refusal about incidence. The adversarial pass caught it. Supplied with a
    value the record **is** accepted, because ``region`` is documented as an
    opaque label the core does not interpret, so it will mechanically hold the
    second terminal. The honest outcome is therefore the same one the parameter
    attempt earns: the relation survives only in what a reader chooses to make
    of a label.
    """
    ok, detail = _try(
        lambda: BoundaryCondition(
            name="R1-incidence",
            variable="node_voltage:n0",
            kind=BoundaryKind.DIRICHLET,
            region="n1",
            value=Quantity(0.0, "volt"),
        )
    )
    return EncodingAttempt(
        column="col-dc",
        fact="which nodes element R1 connects, in terminal order",
        channel=Channel.BOUNDARY_CONDITION,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted with a value supplied — and what it asserts is that node "
            "n0's potential is prescribed at 0 V, which is false. The record has "
            "no second terminal, no kind meaning 'is connected to', and its "
            "'region' is an opaque label; carrying 'n1' there makes the incidence "
            "a reading convention rather than a typed fact, and additionally "
            "states a boundary condition the circuit does not have"
        ),
    )


def _attempt_incidence_as_categorical_parameters() -> EncodingAttempt:
    """Incidence as named categorical parameters. Fits; meaning is in the key."""
    ok, detail = _try(
        lambda: (
            ScientificParameter(
                name="R1.node_a",
                value=CategoricalValue("n0", vocabulary=("gnd", "n0", "n1")),
            ),
            ScientificParameter(
                name="R1.node_b",
                value=CategoricalValue("n1", vocabulary=("gnd", "n0", "n1")),
            ),
        )
    )
    return EncodingAttempt(
        column="col-dc",
        fact="which nodes element R1 connects, in terminal order",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.MEANING_IN_KEY if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted. The relation is carried by the substrings '.node_a' and "
            "'.node_b' of a parameter name; a reader must parse the spelling to "
            "recover it, which is source-code convention, not a typed fact. "
            "Same refusal CROSS-DOMAIN-COVERAGE applied to encoding the "
            "stoichiometric matrix as six named integers"
        ),
    )


def _attempt_nonuniform_initial_condition() -> EncodingAttempt:
    """sin(pi x / L) into `InitialCondition`. Its value is one Quantity."""
    profile = [0.1, 0.2, 0.3]
    ok, detail = _try(
        lambda: InitialCondition(variable="u", value=profile)  # type: ignore[arg-type]
    )
    return EncodingAttempt(
        column="col-slab",
        fact="non-uniform initial field u(x,0) = sin(pi x / L)",
        channel=Channel.INITIAL_CONDITION,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail or "unexpectedly accepted a sequence",
    )


def _attempt_nonuniform_initial_condition_as_bulk() -> EncodingAttempt:
    """The same profile as bulk data. The bytes fit; the linkage does not."""
    reference, _payload = ScientificDataReference.for_values(
        "u:initial", [0.1, 0.2, 0.3], unit="dimensionless"
    )
    fields = {f.name for f in dataclasses.fields(reference)}
    names_a_variable = "variable" in fields
    return EncodingAttempt(
        column="col-slab",
        fact="non-uniform initial field u(x,0) = sin(pi x / L)",
        channel=Channel.DATA_REFERENCE,
        outcome=AttemptOutcome.WORKS
        if names_a_variable
        else AttemptOutcome.NO_PERSISTABLE_HOME,
        detail=(
            "the values serialize and verify, but the reference carries "
            f"{sorted(fields)} and no field naming the variable or the ordering "
            "it holds, so nothing states that these numbers ARE u at t0. This is "
            "the VariableToBulkLinkage gap CROSS-DOMAIN-COVERAGE measured across "
            "all four of its consumers"
        ),
    )


def _attempt_discretization_as_parameters() -> EncodingAttempt:
    """n_cells / n_steps as typed integers. Fits; enters problem identity."""
    ok, detail = _try(
        lambda: (
            ScientificParameter(name="n_cells", value=IntegerValue(40)),
            ScientificParameter(name="n_steps", value=IntegerValue(200)),
        )
    )
    return EncodingAttempt(
        column="col-slab",
        fact="mesh resolution (n_cells, n_steps)",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.LEAKS_INTO_IDENTITY
        if ok
        else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted, and the same problem at two resolutions then becomes two "
            "problems with two parameter sets. HOSTILE-CORE-STRESS measured this "
            "as ENCODING_B and did not recommend it; ConductionSlab.fingerprint() "
            "independently excludes the discretization from physical identity"
        ),
    )


def _attempt_numerics_as_solver_settings() -> EncodingAttempt:
    """Integration settings into `SolverSettings`. Typed — and unreachable."""
    problem_fields = {f.name for f in dataclasses.fields(ScientificProblem)}
    reachable = {"solver_settings", "settings", "numerics"} & problem_fields
    return EncodingAttempt(
        column="col-cstr",
        fact="integration method, tolerances, evaluation budget, output density",
        channel=Channel.SOLVER_SETTINGS,
        outcome=AttemptOutcome.WORKS if reachable else AttemptOutcome.NO_PERSISTABLE_HOME,
        detail=(
            "SolverSettings is typed and round-trips, but it is a field of "
            "PreparedSolve, which is runtime-only and never serialized. "
            f"ScientificProblem declares {sorted(problem_fields)} and none of "
            "them reaches it, so a persisted problem cannot carry the numerical "
            "declaration that determines its answer"
        ),
    )


def _attempt_numerics_as_parameters() -> EncodingAttempt:
    """Integration settings as typed parameters. Fits; leaks into the physics."""
    ok, detail = _try(
        lambda: (
            ScientificParameter(
                name="integration_method",
                value=CategoricalValue("BDF", vocabulary=("BDF", "RK45", "Radau")),
            ),
            ScientificParameter(name="rtol", value=Quantity(1e-8, "dimensionless")),
            ScientificParameter(
                name="max_rhs_evaluations", value=IntegerValue(2_000_000)
            ),
        )
    )
    return EncodingAttempt(
        column="col-cstr",
        fact="integration method, tolerances, evaluation budget, output density",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.LEAKS_INTO_IDENTITY
        if ok
        else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted. Every one of them is representable as a typed parameter — "
            "so this is a PLACEMENT gap, not a representation gap. Placing them "
            "here makes the choice of integrator part of the statement of the "
            "physical problem, which the domain's own docstring refuses: 'the "
            "method and tolerance are properties of how the problem is being "
            "solved, not of the problem being posed'"
        ),
    )


def _attempt_dirichlet_boundaries() -> EncodingAttempt:
    """The slab's homogeneous ends as real records. This one works."""
    ok, detail = _try(
        lambda: (
            BoundaryCondition(
                name="left",
                variable="u",
                kind=BoundaryKind.DIRICHLET,
                region="x=0",
                value=Quantity(0.0, "dimensionless"),
            ),
            BoundaryCondition(
                name="right",
                variable="u",
                kind=BoundaryKind.DIRICHLET,
                region="x=L",
                value=Quantity(0.0, "dimensionless"),
            ),
        )
    )
    return EncodingAttempt(
        column="col-slab",
        fact="homogeneous Dirichlet ends u(0,t) = u(L,t) = 0",
        channel=Channel.BOUNDARY_CONDITION,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted, typed and dimension-checked. The production domain does "
            "not write it: ConductionSlab's docstring says 'Boundary and initial "
            "conditions are not fields: they are fixed by this benchmark', and "
            "they appear only as the string literal 'dirichlet_zero_both_ends' "
            "inside fingerprint(). BoundaryCondition has zero producers in "
            "src/engcore/domains/"
        ),
    )


def _attempt_scalar_initial_conditions() -> EncodingAttempt:
    """The CSTR's two scalar initial values. This one works, and is unused."""
    ok, detail = _try(
        lambda: (
            InitialCondition(
                variable="c_A",
                value=Quantity(500.0, "mol/m**3"),
                time=Quantity(0.0, "second"),
            ),
            InitialCondition(
                variable="T",
                value=Quantity(350.0, "kelvin"),
                time=Quantity(0.0, "second"),
            ),
        )
    )
    return EncodingAttempt(
        column="col-cstr",
        fact="initial concentration and temperature",
        channel=Channel.INITIAL_CONDITION,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted. build_cstr_problem writes none, so a transient ODE domain "
            "reports problem.is_time_dependent == False"
        ),
    )


def _attempt_conductor_parameters() -> EncodingAttempt:
    """The conductor's three constants. Already done by the production domain."""
    ok, detail = _try(
        lambda: (
            ScientificParameter(
                name="reference_resistance", value=cases.CONDUCTOR.reference_resistance
            ),
            ScientificParameter(
                name="temperature_coefficient",
                value=cases.CONDUCTOR.temperature_coefficient,
            ),
            ScientificParameter(
                name="reference_temperature",
                value=cases.CONDUCTOR.reference_temperature,
            ),
        )
    )
    return EncodingAttempt(
        column="col-material",
        fact="reference resistance, temperature coefficient, reference temperature",
        channel=Channel.PARAMETER,
        outcome=AttemptOutcome.WORKS if ok else AttemptOutcome.REFUSED_BY_TYPE,
        detail=detail
        or (
            "accepted — and build_resistance_problem already writes exactly these "
            "three, with no metadata at all. This column is the control: it shows "
            "what a fully-encoded domain looks like"
        ),
    )


#: Every attempt, executed at import time so a refusal is a real exception.
ATTEMPTS: tuple[EncodingAttempt, ...] = (
    _attempt_incidence_as_categorical_parameters(),
    _attempt_incidence_as_boundary_condition(),
    _attempt_incidence_as_bulk(),
    _attempt_dirichlet_boundaries(),
    _attempt_nonuniform_initial_condition(),
    _attempt_nonuniform_initial_condition_as_bulk(),
    _attempt_discretization_as_parameters(),
    _attempt_scalar_initial_conditions(),
    _attempt_numerics_as_solver_settings(),
    _attempt_numerics_as_parameters(),
    _attempt_conductor_parameters(),
)


def attempts_for(column: str) -> tuple[EncodingAttempt, ...]:
    return tuple(a for a in ATTEMPTS if a.column == column)


# =====================================================================
# The L2 encodings themselves
# =====================================================================

def dc_encoding() -> ColumnEncoding:
    """Electrical DC at L2, plus the circuit's own serialized structure.

    Every scalar the circuit declares becomes a typed parameter, the datum
    becomes a typed category, and the observables become variables. What cannot
    go in is the incidence — see the three executed attempts above — so the
    residue travels as the domain's OWN `electrical_dc_circuit/1` payload.
    """
    circuit = cases.CIRCUIT
    vocabulary = tuple(sorted(circuit.node_ids))
    variables = [
        ScientificVariable(
            name=f"node_voltage:{node_id}",
            unit="volt",
            role=VariableRole.OBSERVABLE,
            description=f"Potential of node {node_id!r} against the datum.",
        )
        for node_id in vocabulary
    ]
    variables += [
        ScientificVariable(
            name=f"source_current:{source.component_id}",
            unit="ampere",
            role=VariableRole.OBSERVABLE,
            description="Current leaving the positive terminal.",
        )
        for source in circuit.voltage_sources
    ]
    parameters = [
        ScientificParameter(name=f"R:{r.component_id}", value=r.resistance)
        for r in circuit.resistors
    ]
    parameters += [
        ScientificParameter(name=f"Vs:{s.component_id}", value=s.voltage)
        for s in circuit.voltage_sources
    ]
    parameters.append(
        ScientificParameter(
            name="reference_node",
            value=CategoricalValue(circuit.reference_node, vocabulary=vocabulary),
            description="Explicitly declared voltage datum.",
        )
    )
    parameters.append(
        ScientificParameter(
            name="analysis_type",
            value=CategoricalValue("dc_linear", vocabulary=("dc_linear",)),
        )
    )
    problem = ScientificProblem(
        problem_id="exec-spec:electrical_dc",
        name="DC analysis of a two-resistor divider",
        description="Linear resistive DC steady state by modified nodal analysis.",
        variables=tuple(variables),
        parameters=tuple(parameters),
        models=(ModelReference("electrical.dc.resistor_ohm", "0.1.0"),),
        required_capabilities=frozenset({"electrical:dc_linear"}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "kirchhoff_current_law", "power_balance"}
        ),
    )
    return ColumnEncoding(
        column="col-dc",
        problem=problem,
        structure_payload=circuit.to_dict(),
        structure_schema=DC_STRUCTURE_SCHEMA,
    )


def slab_encoding() -> ColumnEncoding:
    """Thermal conduction at L2, with its conditions written as records.

    The production domain does not write them; this encoding does, to prove they
    are representable. What remains is the mesh and the non-uniform initial
    profile, and those travel in a residue payload this milestone defines only
    for the purpose of measuring them.
    """
    slab = cases.SLAB
    problem = ScientificProblem(
        problem_id="exec-spec:thermal_conduction1d",
        name="1-D transient conduction benchmark",
        description="Normalized field, homogeneous Dirichlet ends.",
        variables=(
            ScientificVariable(
                name="u",
                unit="dimensionless",
                role=VariableRole.STATE,
                description="Normalized field over the slab.",
            ),
            ScientificVariable(
                name="u:midpoint",
                unit="dimensionless",
                role=VariableRole.OBSERVABLE,
                description="Field at x = L/2 at the final time.",
            ),
            ScientificVariable(
                name="u:max_abs",
                unit="dimensionless",
                role=VariableRole.OBSERVABLE,
                description="Maximum absolute field value at the final time.",
            ),
        ),
        parameters=(
            ScientificParameter(name="alpha", value=slab.diffusivity),
            ScientificParameter(name="length", value=slab.length),
            ScientificParameter(name="end_time", value=slab.end_time),
        ),
        boundary_conditions=(
            BoundaryCondition(
                name="left",
                variable="u",
                kind=BoundaryKind.DIRICHLET,
                region="x=0",
                value=Quantity(0.0, "dimensionless"),
            ),
            BoundaryCondition(
                name="right",
                variable="u",
                kind=BoundaryKind.DIRICHLET,
                region="x=L",
                value=Quantity(0.0, "dimensionless"),
            ),
        ),
        models=(ModelReference("thermal.conduction1d.linear_diffusion", "0.1.0"),),
        required_capabilities=frozenset({"thermal:conduction_1d_transient"}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "boundary_conditions_held", "field_finite"}
        ),
    )
    return ColumnEncoding(
        column="col-slab",
        problem=problem,
        structure_payload={
            "schema": SLAB_STRUCTURE_SCHEMA,
            "slab_id": slab.slab_id,
            "n_cells": slab.discretization.n_cells,
            "n_steps": slab.discretization.n_steps,
            # Recorded as a string BECAUSE it has no typed home. This is the
            # residue item, written where a reader can see that it is one.
            "initial_profile": "sin(pi*x/L)",
        },
        structure_schema=SLAB_STRUCTURE_SCHEMA,
    )


def cstr_encoding() -> ColumnEncoding:
    """The CSTR at L2: twelve typed scalars and two real initial conditions.

    Every physical fact the reactor needs is a scalar `Quantity`, so all of it
    goes into typed channels with nothing left over. The numerical declaration
    is a different kind of fact and travels separately — see the two executed
    attempts for why.
    """
    run = cases.RUN
    chem, op = run.chemistry, run.operation
    problem = ScientificProblem(
        problem_id="exec-spec:kinetics_cstr",
        name="Non-isothermal CSTR with Arrhenius kinetics",
        description="Coupled species and energy balances, jacket cooling.",
        variables=(
            ScientificVariable(
                name="c_A",
                unit="mol/m**3",
                role=VariableRole.STATE,
                description="Concentration of A in the tank.",
            ),
            ScientificVariable(
                name="T",
                unit="kelvin",
                role=VariableRole.STATE,
                description="Tank temperature.",
            ),
            ScientificVariable(
                name="final_concentration",
                unit="mol/m**3",
                role=VariableRole.OBSERVABLE,
            ),
            ScientificVariable(
                name="final_temperature", unit="kelvin", role=VariableRole.OBSERVABLE
            ),
            ScientificVariable(
                name="max_temperature", unit="kelvin", role=VariableRole.OBSERVABLE
            ),
            ScientificVariable(
                name="conversion", unit="dimensionless", role=VariableRole.OBSERVABLE
            ),
        ),
        parameters=(
            ScientificParameter(name="k0", value=chem.k0),
            ScientificParameter(
                name="activation_energy", value=chem.activation_energy
            ),
            ScientificParameter(name="heat_of_reaction", value=chem.heat_of_reaction),
            ScientificParameter(name="density", value=chem.density),
            ScientificParameter(name="heat_capacity", value=chem.heat_capacity),
            ScientificParameter(name="volume", value=op.volume),
            ScientificParameter(name="flow_rate", value=op.flow_rate),
            ScientificParameter(
                name="feed_concentration", value=op.feed_concentration
            ),
            ScientificParameter(name="feed_temperature", value=op.feed_temperature),
            ScientificParameter(
                name="coolant_temperature", value=op.coolant_temperature
            ),
            ScientificParameter(name="ua", value=op.ua),
            ScientificParameter(name="end_time", value=op.end_time),
        ),
        initial_conditions=(
            InitialCondition(
                variable="c_A",
                value=run.initial_concentration,
                time=Quantity(0.0, "second"),
            ),
            InitialCondition(
                variable="T",
                value=run.initial_temperature,
                time=Quantity(0.0, "second"),
            ),
        ),
        models=(
            ModelReference("kinetics.cstr.nonisothermal_first_order", "0.1.0"),
        ),
        required_capabilities=frozenset({"kinetics:cstr_nonisothermal_transient"}),
        validation_requirements=frozenset(
            {"dimensional_consistency", "state_physically_admissible"}
        ),
    )
    integration = run.integration
    return ColumnEncoding(
        column="col-cstr",
        problem=problem,
        structure_payload={
            "schema": CSTR_NUMERICS_SCHEMA,
            "run_label": run.run_label,
            "method": integration.method,
            "rtol": integration.rtol,
            "atol_concentration": integration.atol_concentration,
            "atol_temperature": integration.atol_temperature,
            "max_rhs_evaluations": integration.max_rhs_evaluations,
            "n_output_points": integration.n_output_points,
        },
        structure_schema=CSTR_NUMERICS_SCHEMA,
    )


def material_encoding() -> ColumnEncoding:
    """The constitutive property at L2. Nothing is left over — the control.

    The temperature is a `STATE` variable carrying no value, exactly as the
    production domain declares it: the problem states that a temperature is
    required and does not assert which one.
    """
    conductor = cases.CONDUCTOR
    problem = ScientificProblem(
        problem_id="exec-spec:resistance_tcr",
        name=f"Temperature-dependent resistance of {conductor.component_id}",
        description="Evaluate R(T) for one conductor at one supplied temperature.",
        variables=(
            ScientificVariable(
                name="temperature",
                unit="kelvin",
                role=VariableRole.STATE,
                description="Conductor temperature; supplied, not chosen.",
            ),
            ScientificVariable(
                name="resistance", unit="ohm", role=VariableRole.OBSERVABLE
            ),
        ),
        parameters=(
            ScientificParameter(
                name="reference_resistance", value=conductor.reference_resistance
            ),
            ScientificParameter(
                name="temperature_coefficient",
                value=conductor.temperature_coefficient,
            ),
            ScientificParameter(
                name="reference_temperature", value=conductor.reference_temperature
            ),
            ScientificParameter(
                name="component_id",
                value=CategoricalValue(
                    conductor.component_id, vocabulary=(conductor.component_id,)
                ),
            ),
        ),
        models=(
            ModelReference("electrical.material.linear_tcr_resistance", "0.1.0"),
        ),
        required_capabilities=frozenset({"core:algebraic"}),
        validation_requirements=frozenset({"dimensional_consistency"}),
    )
    return ColumnEncoding(column="col-material", problem=problem)


#: The four columns at L2, built once.
ENCODINGS: dict[str, ColumnEncoding] = {
    "col-dc": dc_encoding(),
    "col-slab": slab_encoding(),
    "col-cstr": cstr_encoding(),
    "col-material": material_encoding(),
}
