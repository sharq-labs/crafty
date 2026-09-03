"""Records -> executable domain objects. The execution side, not the reader.

This module MAY import domains: reconstructing a `DCCircuit` obviously requires
knowing what one is. What it may not do — and does not do — is smuggle
information that the records did not carry. Every value it puts into a rebuilt
artifact comes from a typed field of a serialized record, and where it cannot,
it raises rather than filling the gap from the domain's own defaults.

Two directions are exercised deliberately, because they are not the same claim:

``col-dc``    the artifact payload reconstructs the circuit; the problem's typed
              parameters are used to **verify** it. Records -> artifact, where the
              artifact carried the structure all along.
``col-slab``  the problem's typed parameters reconstruct the artifact; the residue
``col-cstr``  payload supplies only what no typed channel could hold.
``col-material`` the problem alone reconstructs the artifact. Nothing is left over.

The identity check is deliberately **typed**, following
`material.py::verify_problem_matches_conductor`: parameter values are compared
against the rebuilt artifact through `Quantity`, with dimensions checked. It does
not consult `problem.metadata`, and it does not consult a fingerprint. That is
the point — a fingerprint proves two objects are the same; typed parameters prove
*what the object is*, and only the second survives being read by something that
does not already hold the original.
"""

from __future__ import annotations

from typing import Any, Mapping

from engcore.domains.electrical.dc import DCCircuit, solve_circuit
from engcore.domains.electrical.material import (
    ResistancePropertySolver,
    TemperatureDependentConductor,
    build_resistance_problem,
)
from engcore.domains.kinetics.cstr import (
    IntegrationSettings,
    ReactorChemistry,
    ReactorOperation,
    ReactorRun,
    solve_reactor,
)
from engcore.domains.thermal.conduction1d import (
    ConductionSlab,
    SlabDiscretization,
    solve_slab,
)
from engcore.scientific.ir.problem import ScientificProblem
from engcore.scientific.units.quantity import Quantity

from .schemas import (
    CSTR_NUMERICS_SCHEMA,
    DC_STRUCTURE_SCHEMA,
    SLAB_STRUCTURE_SCHEMA,
)
from .instrument import read_problem

__all__ = [
    "ReconstructionError",
    "MissingStructure",
    "UnsupportedStructureSchema",
    "CorruptStructure",
    "IdentityMismatch",
    "rebuild_circuit",
    "rebuild_slab",
    "rebuild_run",
    "rebuild_conductor",
    "execute",
    "EXECUTABLE_COLUMNS",
]


class ReconstructionError(Exception):
    """Reconstruction refused. Deliberately not a `ScientificCoreError`.

    Failing to rebuild a problem is not a scientific finding about nature, in
    exactly the way `NgspiceExecutionFailure` is not: the same separation, drawn
    at the same kind of boundary.
    """


class MissingStructure(ReconstructionError):
    """The records do not include the structure this domain needs."""


class UnsupportedStructureSchema(ReconstructionError):
    """The structural payload declares a schema this reader does not accept."""


class CorruptStructure(ReconstructionError):
    """The structural payload is present, well-labelled and not loadable."""


class IdentityMismatch(ReconstructionError):
    """The problem and the structure describe different physical systems."""


EXECUTABLE_COLUMNS: tuple[str, ...] = ("col-dc", "col-slab", "col-cstr", "col-material")


def _require_structure(
    structure: Mapping[str, Any] | None, expected_schema: str, column: str
) -> Mapping[str, Any]:
    if structure is None:
        raise MissingStructure(
            f"{column}: no structural payload was supplied, and the problem "
            f"record cannot carry what this domain needs to execute"
        )
    declared = structure.get("schema")
    if declared != expected_schema:
        raise UnsupportedStructureSchema(
            f"{column}: structural payload declares schema {declared!r}; this "
            f"reconstruction accepts exactly {expected_schema!r}. No attempt is "
            f"made to interpret an unknown or foreign payload"
        )
    return structure


def _parameter(problem: ScientificProblem, name: str) -> Quantity:
    try:
        value = problem.parameter(name).value
    except Exception as exc:  # noqa: BLE001 - absence is the finding
        raise MissingStructure(
            f"the problem declares no parameter {name!r}: {exc}"
        ) from None
    if not isinstance(value, Quantity):
        raise IdentityMismatch(
            f"parameter {name!r} is {type(value).__name__}, not a Quantity"
        )
    return value


def _agrees(left: Quantity, right: Quantity, *, unit: str) -> bool:
    return abs(left.magnitude_in(unit) - right.magnitude_in(unit)) <= 1e-12 * max(
        1.0, abs(right.magnitude_in(unit))
    )


# =====================================================================
# col-dc — the artifact carries the structure; the problem verifies it
# =====================================================================

def rebuild_circuit(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
) -> DCCircuit:
    """Rebuild the circuit, then prove the problem describes *that* circuit."""
    problem = read_problem(problem_payload)
    structure = _require_structure(structure_payload, DC_STRUCTURE_SCHEMA, "col-dc")
    try:
        circuit = DCCircuit.from_dict(structure)
    except Exception as exc:  # noqa: BLE001 - a load failure is a typed outcome
        raise CorruptStructure(
            f"col-dc: the structural payload declares {DC_STRUCTURE_SCHEMA} and "
            f"does not load as one: {type(exc).__name__}: {exc}"
        ) from None

    for resistor in circuit.resistors:
        stated = _parameter(problem, f"R:{resistor.component_id}")
        if not _agrees(stated, resistor.resistance, unit="ohm"):
            raise IdentityMismatch(
                f"col-dc: the problem states R:{resistor.component_id} = {stated} "
                f"but the structure declares {resistor.resistance}"
            )
    for source in circuit.voltage_sources:
        stated = _parameter(problem, f"Vs:{source.component_id}")
        if not _agrees(stated, source.voltage, unit="volt"):
            raise IdentityMismatch(
                f"col-dc: the problem states Vs:{source.component_id} = {stated} "
                f"but the structure declares {source.voltage}"
            )
    for source in circuit.current_sources:
        # Added after the adversarial pass: the chosen case has no current
        # source, so this loop never ran and the identity check had a hole no
        # negative test could reach. An element type that is verified only when
        # the example happens to contain one is not verified.
        stated = _parameter(problem, f"Is:{source.component_id}")
        if not _agrees(stated, source.current, unit="ampere"):
            raise IdentityMismatch(
                f"col-dc: the problem states Is:{source.component_id} = {stated} "
                f"but the structure declares {source.current}"
            )
    declared_reference = problem.parameter("reference_node").context_value()
    if str(declared_reference) != circuit.reference_node:
        raise IdentityMismatch(
            f"col-dc: the problem declares datum {declared_reference!r} but the "
            f"structure declares {circuit.reference_node!r}"
        )
    return circuit


# =====================================================================
# col-slab / col-cstr / col-material — the problem carries the physics
# =====================================================================

def rebuild_slab(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
) -> ConductionSlab:
    """Rebuild the slab from typed parameters plus the mesh residue.

    The initial profile is **checked, not carried**: the domain hard-codes
    ``sin(pi x / L)`` inside its solver, so a payload declaring anything else
    would reconstruct an object that computes a different problem than the
    records describe. Refusing is the only honest option, and the need to refuse
    is itself the measurement.
    """
    problem = read_problem(problem_payload)
    structure = _require_structure(
        structure_payload, SLAB_STRUCTURE_SCHEMA, "col-slab"
    )
    profile = structure.get("initial_profile")
    if profile != "sin(pi*x/L)":
        raise UnsupportedStructureSchema(
            f"col-slab: the records declare initial profile {profile!r}, and the "
            f"domain's solver hard-codes sin(pi*x/L). No record can state a "
            f"non-uniform initial field, so a different profile is not "
            f"reconstructable — it is unrepresentable"
        )
    # The same refusal, for the boundary conditions, and it was missing.
    #
    # The adversarial pass found that this encoding writes two BoundaryCondition
    # records the solver never reads — homogeneous Dirichlet ends are compiled
    # into `assemble()` — so editing them in the persisted payload changed
    # nothing and was refused by nothing. Records that cannot influence the
    # computation must not be allowed to *describe* it differently.
    declared = tuple(
        sorted(
            (c.kind.value, c.region, None if c.value is None else c.value.magnitude)
            for c in problem.boundary_conditions
        )
    )
    implemented = (("dirichlet", "x=0", 0.0), ("dirichlet", "x=L", 0.0))
    if declared != implemented:
        raise UnsupportedStructureSchema(
            f"col-slab: the records declare boundary conditions {declared}, and "
            f"the domain's solver implements exactly {implemented}. The solver "
            f"reads no boundary record, so a differing declaration would produce "
            f"a result that the records misdescribe"
        )
    try:
        discretization = SlabDiscretization(
            n_cells=int(structure["n_cells"]), n_steps=int(structure["n_steps"])
        )
    except Exception as exc:  # noqa: BLE001
        raise CorruptStructure(f"col-slab: {type(exc).__name__}: {exc}") from None
    return ConductionSlab(
        slab_id=str(structure.get("slab_id", "reconstructed")),
        length=_parameter(problem, "length"),
        diffusivity=_parameter(problem, "alpha"),
        end_time=_parameter(problem, "end_time"),
        discretization=discretization,
    )


def rebuild_run(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None,
) -> ReactorRun:
    """Rebuild the reactor from typed parameters, typed conditions, and numerics.

    Every physical fact comes from a `ScientificParameter` or an
    `InitialCondition`. Only the numerical declaration comes from the residue
    payload, and only because no persistable record can hold it.
    """
    problem = read_problem(problem_payload)
    structure = _require_structure(
        structure_payload, CSTR_NUMERICS_SCHEMA, "col-cstr"
    )
    initial = {c.variable: c.value for c in problem.initial_conditions}
    for required in ("c_A", "T"):
        if required not in initial:
            raise MissingStructure(
                f"col-cstr: no initial condition for {required!r}; a transient "
                f"problem cannot be reconstructed without its initial state"
            )
    try:
        chemistry = ReactorChemistry(
            k0=_parameter(problem, "k0"),
            activation_energy=_parameter(problem, "activation_energy"),
            heat_of_reaction=_parameter(problem, "heat_of_reaction"),
            density=_parameter(problem, "density"),
            heat_capacity=_parameter(problem, "heat_capacity"),
        )
        operation = ReactorOperation(
            volume=_parameter(problem, "volume"),
            flow_rate=_parameter(problem, "flow_rate"),
            feed_concentration=_parameter(problem, "feed_concentration"),
            feed_temperature=_parameter(problem, "feed_temperature"),
            coolant_temperature=_parameter(problem, "coolant_temperature"),
            ua=_parameter(problem, "ua"),
            end_time=_parameter(problem, "end_time"),
        )
        integration = IntegrationSettings(
            method=str(structure["method"]),
            rtol=float(structure["rtol"]),
            atol_concentration=float(structure["atol_concentration"]),
            atol_temperature=float(structure["atol_temperature"]),
            max_rhs_evaluations=int(structure["max_rhs_evaluations"]),
            n_output_points=int(structure["n_output_points"]),
        )
    except ReconstructionError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise CorruptStructure(f"col-cstr: {type(exc).__name__}: {exc}") from None
    return ReactorRun(
        run_label=str(structure.get("run_label", "reconstructed")),
        chemistry=chemistry,
        operation=operation,
        initial_concentration=initial["c_A"],
        initial_temperature=initial["T"],
        integration=integration,
    )


def rebuild_conductor(
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None = None,
) -> TemperatureDependentConductor:
    """Rebuild the conductor from the problem alone. No residue exists."""
    if structure_payload is not None:
        raise UnsupportedStructureSchema(
            "col-material: this column has no residue; a structural payload "
            "would be a second source of truth for facts the problem already "
            "carries"
        )
    problem = read_problem(problem_payload)
    component = problem.parameter("component_id").context_value()
    return TemperatureDependentConductor(
        component_id=str(component),
        reference_resistance=_parameter(problem, "reference_resistance"),
        temperature_coefficient=_parameter(problem, "temperature_coefficient"),
        reference_temperature=_parameter(problem, "reference_temperature"),
    )


# =====================================================================
# Execution
# =====================================================================

def execute(
    column: str,
    problem_payload: Mapping[str, Any],
    structure_payload: Mapping[str, Any] | None = None,
    *,
    run_id: str = "exec-spec",
    provider: str = "native",
    temperature: Quantity | None = None,
) -> dict[str, float]:
    """Reconstruct and run, returning the metrics as plain floats.

    Plain floats because this crosses a process boundary as JSON in the
    fresh-process test. The units are not lost — they are asserted in-process
    against the same `ScientificResult` the domain returns.
    """
    if column == "col-dc":
        circuit = rebuild_circuit(problem_payload, structure_payload)
        if provider == "ngspice":
            from engcore.domains.electrical.ngspice import solve_circuit_with_ngspice

            result = solve_circuit_with_ngspice(circuit, run_id=run_id)
        else:
            result = solve_circuit(circuit, run_id=run_id)
    elif column == "col-slab":
        result = solve_slab(rebuild_slab(problem_payload, structure_payload), run_id=run_id)
    elif column == "col-cstr":
        result = solve_reactor(rebuild_run(problem_payload, structure_payload), run_id=run_id)
    elif column == "col-material":
        conductor = rebuild_conductor(problem_payload, structure_payload)
        solver = ResistancePropertySolver()
        problem = build_resistance_problem(conductor)
        solver.bind_conductor(
            conductor,
            problem.problem_id,
            temperature=temperature or Quantity(350.0, "kelvin"),
        )
        prepared = solver.prepare(problem)
        raw = solver.solve(prepared)
        metrics = solver.extract_metrics(prepared, raw)
        return {name: q.magnitude for name, q in metrics.items()}
    else:
        raise ReconstructionError(f"unknown column {column!r}")
    return {name: q.magnitude for name, q in result.values.items()}
