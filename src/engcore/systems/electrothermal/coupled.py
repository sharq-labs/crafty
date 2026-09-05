"""Closed-loop electro-thermal coupling: the composition, and how it is solved.

`ET-VERTICAL`, relocated by `COUPLING-PACK-RELOCATION`. The loop this module
closes::

        seed T⁽⁰⁾
            ↓
    ┌── T⁽ⁿ⁾ ──▶ R(T⁽ⁿ⁾) ──▶ electrical solve ──▶ P⁽ⁿ⁾ ──▶ thermal solve ──┐
    │                                                                       │
    └──────────────────── T⁽ⁿ⁺¹⁾  ◀── iterate change |T⁽ⁿ⁺¹⁾ − T⁽ⁿ⁾| ◀──────┘

Iteration *n ≥ 2* solves the electrical problem at a resistance the previous
thermal solve produced. That is the whole difference from `run_open_loop_pass`,
and it is what makes this a coupled execution rather than a representation.

Where the machinery lives, and why it is not here
-------------------------------------------------
The plan, the torn endpoint, the outcome enum, the iteration and run records,
the graph readers and the fixed-point loop itself now live in
``engcore.coupling`` — imported here, not defined here. They were minted by
this pack, and `FT-SCALAR-COUPLING` then executed a second, materially
different coupled pair against them **unedited, by object identity**, which
made a domain-named owner false in two measurable ways: a fluid ↔ thermal run
serialized under ``electrothermal_coupled_run/1``, and a fluids pack had to
import an *electrothermal* pack to reach a loop that names no domain.
`COUPLING-PACK-RELOCATION` moved them, executable source byte-for-byte
unchanged. See ``docs/coupling-pack-relocation-evidence.md``.

**None of that is a promotion into universal scientific Core.**
``engcore.coupling`` is coupling execution/composition infrastructure. No
universal reader of a coupling plan or a coupling outcome exists anywhere in
the platform, and this milestone did not invent one.

What this module keeps, and why
-------------------------------
Everything scientific: the stage co-identity convention, the series circuit,
the three declared dependency edges, the tear rule this pack's callers use, the
twin, the per-problem executors, and the entry point. A generic package may
transport identities and values and execute a plan; it must not know that a
transported watt is Joule dissipation or that a transported kelvin is the state
coordinate of a temperature-dependent resistance. Those statements are made
here, by the pack that knows the physics.

How the loop knows what feeds what
----------------------------------
It reads the declared :class:`~engcore.scientific.composition.QuantityDependency`
records this module builds. Every transported value is looked up as

    ``result_of(dep.source_problem_id).values[dep.source_quantity]``

and delivered under ``dep.target_quantity``. **No metric name is constructed,
parsed or inferred inside the iteration.** Change a dependency's
``source_quantity`` to a different declared metric of the same dimension and
the loop transports something else and converges somewhere else — which is
what makes the records load-bearing rather than decorative, and is exercised by
the two configurations described below.

The execution order is likewise computed, not written down: the torn edges are
removed and the remainder is topologically sorted. With the edges declared here
that yields *properties → circuit → bodies*, but the loop never states it.

Two configurations, one field apart
-----------------------------------
The thermal problem publishes three kelvin-valued quantities — ``temperature``
(the state at t₀), ``final_temperature`` (t = duration) and
``steady_state_temperature`` (t → ∞). A dimension check cannot tell them apart.
Selecting the second gives the self-consistent end-of-interval state; selecting
the third gives the coupled steady state. They differ by 3.4 K on identical
inputs, and only the enumerated *name* separates them.

It is not time marching
-----------------------
The thermal problem's initial condition is the same in every iteration; the
iterate is a *coupling* iterate, not a time level. Advancing the initial
condition between iterations would make ``|T⁽ⁿ⁺¹⁾ − T⁽ⁿ⁾|`` a time-stepping
increment and reporting it as coupling convergence would collapse the two. Two
things prevent it: :meth:`~engcore.coupling.FixedPointCouplingPlan.check_against`
refuses to seed an endpoint a declared condition already determines, and every
iteration's thermal provenance records the same t₀.

Offset units are refused, and precisely why
-------------------------------------------
``Quantity(0.001, "kelvin").magnitude_in("degC")`` is ``-273.149``, and ``degC``
has the same dimensionality as ``kelvin``, so no dimension check can see a
mismatch between them. The arithmetic of the comparison survives it — both
sides are converted into one unit before subtraction and an affine offset
cancels in a difference — but the **stored record** does not:
``largest_iterate_change`` is a difference carried in a type that means an
absolute value. ``engcore.coupling.scales`` refuses an affine comparison unit
for that reason, structurally and without any temperature knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from ...coupling import (
    CoupledRun,
    FixedPointCouplingPlan,
    TornEndpoint,
    run_fixed_point,
)
from ...domains import thermal_lumped as lump
from ...domains.electrical import material as mat
from ...domains.electrical.dc import (
    DCCircuit,
    DCVoltageSource,
    ElectricalNode,
    Resistor,
    build_dc_problem,
    solve_circuit,
)
# Same non-exported import the sibling module already needs: the DC package
# publishes no metric-name helper (MIN-FOUNDATION-ET finding C-11). Reusing the
# sibling's constant rather than re-deriving the convention a second time keeps
# one source of truth per name inside this pack.
from ...domains.electrical.dc.problem import resistance_name
from ...scientific.composition import QuantityDependency
from ...scientific.errors import (
    InvalidScientificProblem,
    ScientificValidationError,
)
from ...scientific.models.definition import ValidityAssessment, ValidityStatus
from ...scientific.ir.problem import ModelReference, ScientificProblem
from ...scientific.results.provenance import ExecutionBinding, ProvenanceRecord
from ...scientific.results.result import ScientificResult
from ...scientific.results.uncertainty import Uncertainty
from ...scientific.twins.definition import (
    ScientificTwin,
    TwinDatum,
    TwinDatumRole,
    TwinKind,
)
from ...scientific.units.quantity import Quantity
from .resistor_body import RESISTOR_POWER_METRIC

#: How one DC circuit gets solved. **The only substitution seam in this pack.**
#:
#: `API-MCP-V0`. Introduced additively so an external caller may select, from a
#: closed enumeration owned by the application layer, *which* concrete circuit
#: solver runs inside the electro-thermal loop. The default is this pack's own,
#: so every pre-existing caller and every stored number is unchanged.
#:
#: Note what this seam deliberately is **not**. It is not a provider framework,
#: not a registry, not a plugin system and not a capability lookup. It is one
#: keyword argument whose type is the callable the pack already had. The
#: substitution therefore stays strictly *below* coupling semantics — the plan,
#: the dependency records, the tear, the iteration and the outcome are
#: untouched — which is the property the real-external-provider milestone
#: measured, and which a registry sitting here would have obscured.
#:
#: This pack cannot name any concrete substitute and does not import one. It
#: receives a callable and calls it. Which implementations exist, and which
#: external identity selects which, is a fact about the *application layer* and
#: is unreadable from here.
CircuitSolver = Callable[[DCCircuit, str], ScientificResult]


# This pack publishes its own declarations only. The generic coupling records
# and the loop are `engcore.coupling`'s and are imported above for this
# module's own use; re-exporting them here would restate the false ownership
# `COUPLING-PACK-RELOCATION` removed. A guard test asserts they stay out.
__all__ = [
    "CircuitSolver",
    "CoupledElectroThermalSystem",
    "CoupledStage",
    "DEPENDENCY_HEAT",
    "DEPENDENCY_RESISTANCE",
    "DEPENDENCY_TEMPERATURE",
    "build_coupled_twin",
    "coupled_dependencies",
    "coupled_problems",
    "native_circuit_solver",
    "nominal_plan",
    "run_fixed_point_coupling",
    "stage_problems",
]


#: Prose labels for the declared edges. Nothing branches on them.
DEPENDENCY_HEAT = "joule-dissipation-heats-body"
DEPENDENCY_TEMPERATURE = "body-temperature-sets-property-state"
DEPENDENCY_RESISTANCE = "property-resistance-sets-circuit-element"

SOURCE_ID = "V1"
REFERENCE_NODE = "gnd"


# =====================================================================
# The system declaration
# =====================================================================

@dataclass(frozen=True)
class CoupledStage:
    """One conductor and the thermal body it dissipates into.

    The two share a ``component_id``, and that co-identity remains a
    **convention of this pack**: no universal record states that a conductor
    declaration and a body declaration describe one physical object. A
    ``ComponentInstance`` to state it was tested and deferred at arity 1 by
    `MIN-FOUNDATION-ET`; this milestone runs it at arity 2 to find out whether
    arity forces it.
    """

    conductor: mat.TemperatureDependentConductor
    body: lump.ThermalBody

    def __post_init__(self) -> None:
        if not isinstance(self.conductor, mat.TemperatureDependentConductor):
            raise InvalidScientificProblem(
                "stage conductor must be a TemperatureDependentConductor"
            )
        if not isinstance(self.body, lump.ThermalBody):
            raise InvalidScientificProblem("stage body must be a ThermalBody")
        if self.conductor.component_id != self.body.body_id:
            raise InvalidScientificProblem(
                f"conductor {self.conductor.component_id!r} and body "
                f"{self.body.body_id!r} must share an id in this system pack; "
                f"no universal record states that two declarations describe one "
                f"physical object, so this pack keeps them aligned by "
                f"construction"
            )

    @property
    def component_id(self) -> str:
        return self.conductor.component_id


@dataclass(frozen=True)
class CoupledElectroThermalSystem:
    """N self-heating conductors in series across one ideal source.

    Series, deliberately. Across an ideal voltage source, parallel elements do
    not interact, and a multiplicity case in which the instances cannot
    influence each other exercises nothing. In series, heating one conductor
    changes the loop current, which changes every other conductor's
    dissipation — so the N coupling cycles are genuinely coupled through the
    circuit and an identity confusion between them would change the answer.

    With ``N = 1`` this is exactly the physics of `MIN-FOUNDATION-ET`'s
    single-resistor system.
    """

    stages: tuple[CoupledStage, ...]
    source_voltage: Quantity
    system_id: str = "electrothermal-series"

    def __post_init__(self) -> None:
        object.__setattr__(self, "stages", tuple(self.stages))
        if not self.stages:
            raise InvalidScientificProblem("a coupled system requires a stage")
        seen: set[str] = set()
        for stage in self.stages:
            if not isinstance(stage, CoupledStage):
                raise InvalidScientificProblem("stages must be CoupledStage")
            if stage.component_id in seen:
                raise InvalidScientificProblem(
                    f"duplicate component id {stage.component_id!r}: two stages "
                    f"sharing an id would alias every endpoint that names it"
                )
            seen.add(stage.component_id)
        if not isinstance(self.source_voltage, Quantity):
            raise InvalidScientificProblem("source_voltage must be a Quantity")
        self.source_voltage.require_compatible(
            "volt", context="coupled source voltage"
        )

    @property
    def component_ids(self) -> tuple[str, ...]:
        return tuple(s.component_id for s in self.stages)

    @property
    def circuit_id(self) -> str:
        return f"{self.system_id}-{'-'.join(self.component_ids)}"

    def power_metric(self, component_id: str) -> str:
        """The DC domain's published power metric for one element."""
        return RESISTOR_POWER_METRIC.format(component_id=component_id)

    def _node_ids(self) -> tuple[str, ...]:
        """``n0 … n(N-1)`` plus the reference. ``n0`` is the source's positive."""
        return tuple(f"n{i}" for i in range(len(self.stages))) + (REFERENCE_NODE,)

    def circuit_at(self, resistances: Mapping[str, Quantity]) -> DCCircuit:
        """The series circuit with every element set to one evaluated value."""
        nodes = self._node_ids()
        resistors = []
        for index, stage in enumerate(self.stages):
            try:
                value = resistances[stage.component_id]
            except KeyError:
                raise InvalidScientificProblem(
                    f"no resistance supplied for {stage.component_id!r}"
                ) from None
            resistors.append(
                Resistor(stage.component_id, nodes[index], nodes[index + 1], value)
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
        )


# =====================================================================
# Representation
# =====================================================================

def coupled_problems(
    system: CoupledElectroThermalSystem, resistances: Mapping[str, Quantity]
) -> tuple[ScientificProblem, ...]:
    """``(electrical, property…, thermal…)`` — ``2N + 1`` separately posed problems.

    The electrical resistance has to be supplied to *build* the electrical
    problem, because the DC domain carries it as a configured
    ``ScientificParameter`` and folds it into the circuit's canonical identity.
    That is the configuration/state conflation `MIN-FOUNDATION-ET` measured; it
    is why every iteration builds a **fresh** electrical problem, and why the
    problem *record* differs between iterations while its ``problem_id`` does
    not.
    """
    problems = [build_dc_problem(system.circuit_at(resistances))]
    for _, prop, thermal in stage_problems(system):
        problems += [prop, thermal]
    return tuple(problems)


def stage_problems(
    system: CoupledElectroThermalSystem,
) -> tuple[tuple[CoupledStage, ScientificProblem, ScientificProblem], ...]:
    """``(stage, property problem, thermal problem)``, associated structurally.

    The one place the correspondence between a declared stage and the two
    problems posed for it is stated. An earlier form returned a flat tuple and
    let three separate functions recover the correspondence by slicing it —
    ``problems[1:1+n]`` and ``problems[1+n:1+2n]`` — which is the positional
    association ``ExecutionBinding`` exists to prevent and which
    :class:`TornEndpoint`'s own docstring argues against. A caller passing a
    reordered sequence got a silently mis-wired composition that still
    converged.
    """
    return tuple(
        (
            stage,
            mat.build_resistance_problem(stage.conductor),
            lump.build_lumped_thermal_problem(stage.body),
        )
        for stage in system.stages
    )


def coupled_dependencies(
    system: CoupledElectroThermalSystem,
    problems: Sequence[ScientificProblem],
    *,
    temperature_metric: str = lump.TEMPERATURE_METRIC,
) -> tuple[QuantityDependency, ...]:
    """``3N`` directed edges: dissipation heats, temperature sets, resistance sets.

    ``temperature_metric`` selects which of the thermal problem's kelvin-valued
    result metrics is transported. It is the **only** difference between the
    end-of-interval configuration and the coupled-steady-state configuration,
    and the two converge to different temperatures. A dimension check cannot
    distinguish them; only the enumerated name can.
    """
    declared = {p.problem_id for p in problems}
    electrical = next(
        (p for p in problems if p.problem_id.startswith("electrical_dc:")), None
    )
    if electrical is None:
        raise InvalidScientificProblem(
            "the supplied problems contain no electrical analysis to wire into"
        )

    edges: list[QuantityDependency] = []
    for stage, prop, thermal in stage_problems(system):
        cid = stage.component_id
        for problem in (prop, thermal):
            if problem.problem_id not in declared:
                raise InvalidScientificProblem(
                    f"stage {cid!r} poses problem {problem.problem_id!r}, which "
                    f"is not among the supplied problems; the correspondence "
                    f"between a stage and its problems is stated, not inferred "
                    f"from position"
                )
        edges.append(
            QuantityDependency(
                source_problem_id=electrical.problem_id,
                source_quantity=system.power_metric(cid),
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
                target_problem_id=prop.problem_id,
                target_quantity=mat.TEMPERATURE,
                unit_exemplar=mat.TEMPERATURE_UNIT,
                name=f"{DEPENDENCY_TEMPERATURE}:{cid}",
                description=(
                    "The body temperature is the state coordinate at which "
                    "this conductor's resistance is evaluated."
                ),
            )
        )
        edges.append(
            QuantityDependency(
                source_problem_id=prop.problem_id,
                source_quantity=mat.RESISTANCE_METRIC,
                target_problem_id=electrical.problem_id,
                target_quantity=resistance_name(cid),
                unit_exemplar=mat.RESISTANCE_UNIT,
                name=f"{DEPENDENCY_RESISTANCE}:{cid}",
                description=(
                    "The evaluated resistance is the value this circuit "
                    "element takes."
                ),
            )
        )
    return tuple(edges)


def nominal_plan(
    system: CoupledElectroThermalSystem,
    dependencies: Sequence[QuantityDependency],
    *,
    seed: Quantity,
    tolerance: Quantity = Quantity(1e-6, "kelvin"),
    max_iterations: int = 50,
    plan_id: str | None = None,
) -> FixedPointCouplingPlan:
    """Build the plan this milestone's cases use: cut every temperature edge.

    **This is a caller-side convenience and it does select a tear by a rule** —
    ``d.target_quantity == mat.TEMPERATURE``. Saying it is "stated, never
    inferred" would be false of *this* function; what is true, and what the
    constraint actually requires, is that **the loop and the graph readers
    infer nothing**: :func:`execution_order` reports three admissible tears per
    cycle and ranks none, and :class:`FixedPointCouplingPlan` accepts whatever
    tear it is handed. The choice is made here, by a caller, and is then a
    typed field of a record rather than control flow.

    The rule is also narrower than it reads: ``mat.TEMPERATURE`` and
    ``lump.TEMPERATURE`` are **both** the string ``"temperature"``, so an edge
    targeting the thermal problem's ``temperature`` *state variable* would
    match this filter too. That edge is refused by
    :meth:`FixedPointCouplingPlan.check_against`, because seeding a quantity a
    declared initial condition already determines is time marching wearing the
    name of coupling.
    """
    torn = tuple(
        TornEndpoint(dependency=d, initial_value=seed)
        for d in dependencies
        if d.target_quantity == mat.TEMPERATURE
    )
    return FixedPointCouplingPlan(
        plan_id=plan_id or f"{system.system_id}-fixed-point",
        dependencies=tuple(dependencies),
        torn=torn,
        absolute_tolerance=tolerance,
        max_iterations=max_iterations,
    )


def build_coupled_twin(
    system: CoupledElectroThermalSystem,
    *,
    twin_id: str | None = None,
    version: str = "0.1.0",
) -> ScientificTwin:
    """The scientific instance description. **Not the runtime state.**

    The twin is immutable and versioned. It is built once, it is not an input to
    :func:`run_fixed_point_coupling`, and it is not re-versioned per iteration.
    A coupling iterate is not a scientific declaration: it is a working value
    that exists only while the loop runs and is superseded by the next one.
    Making the twin carry it would require one twin version per iteration for a
    single interval — ten of them for the nominal case — and would give
    ``ScientificTwin`` a second meaning.
    """
    declarations: list[TwinDatum] = [
        TwinDatum(
            name=f"source_voltage:{SOURCE_ID}",
            value=system.source_voltage,
            role=TwinDatumRole.CONTROL,
        )
    ]
    models: list[ModelReference] = [
        ModelReference(mat.LINEAR_TCR_MODEL.model_id, mat.LINEAR_TCR_MODEL.version),
        ModelReference(
            lump.LUMPED_CAPACITY_MODEL.model_id, lump.LUMPED_CAPACITY_MODEL.version
        ),
    ]
    for stage in system.stages:
        cid = stage.component_id
        conductor, body = stage.conductor, stage.body
        declarations += [
            TwinDatum(f"reference_resistance:{cid}", conductor.reference_resistance,
                      TwinDatumRole.PARAMETER),
            TwinDatum(f"temperature_coefficient:{cid}",
                      conductor.temperature_coefficient, TwinDatumRole.PARAMETER),
            TwinDatum(f"reference_temperature:{cid}",
                      conductor.reference_temperature, TwinDatumRole.PARAMETER),
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
    return ScientificTwin(
        twin_id=twin_id or system.system_id,
        version=version,
        kind=TwinKind.CONCEPT,
        name="Self-heating conductors in series with lumped thermal bodies",
        description=(
            "N conductors whose resistance depends on their temperature, each "
            "thermally represented as a lumped body exchanging with an ambient, "
            "in series across an ideal DC voltage source."
        ),
        models=tuple(models),
        declarations=tuple(declarations),
        assumptions=(
            "each conductor and its thermal body are the same physical object",
            "the whole dissipated power of an element enters its body",
            "the resistance is evaluated at the transported temperature and "
            "held constant over the integrated interval",
        ),
    )


# ---- per-problem execution, supplied by this pack --------------------------

def _property_result(
    *, run_id: str, stage: CoupledStage, problem: ScientificProblem,
    temperature: Quantity,
) -> ScientificResult:
    solver = mat.ResistancePropertySolver()
    solver.bind_conductor(stage.conductor, problem.problem_id,
                          temperature=temperature)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(mat.LINEAR_TCR_MODEL.model_id,
                           mat.LINEAR_TCR_MODEL.version)
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version="engcore.domains.electrical.material/0.1.0",
        bindings=(
            ExecutionBinding(
                model=model,
                realization=prepared.payload.realization.reference(),
                solver=solver.identity,
            ),
        ),
        inputs=dict(problem.parameter_values()) | {mat.TEMPERATURE: temperature},
        assumptions=mat.LINEAR_TCR_MODEL.assumptions,
        environment=scientific_environment(),
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
                "temperature coefficient"
            )
            for name in metrics
        },
        assumptions=mat.LINEAR_TCR_MODEL.assumptions,
        provenance=provenance,
    )


def _thermal_result(
    *, run_id: str, stage: CoupledStage, problem: ScientificProblem,
    heat_input: Quantity,
) -> ScientificResult:
    solver = lump.LumpedThermalSolver()
    solver.bind_body(stage.body, problem.problem_id, heat_input=heat_input)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)
    model = ModelReference(lump.LUMPED_CAPACITY_MODEL.model_id,
                           lump.LUMPED_CAPACITY_MODEL.version)
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
        inputs=dict(problem.parameter_values()) | {
            lump.HEAT_INPUT: heat_input,
            lump.AMBIENT_TEMPERATURE: stage.body.ambient_temperature,
            # The state at t0. Identical in every iteration: the loop iterates
            # the coupling, it does not march time.
            lump.TEMPERATURE: stage.body.initial_temperature,
        },
        assumptions=lump.LUMPED_CAPACITY_MODEL.assumptions,
        environment=scientific_environment(),
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


#: TRUST-HARDENING P2. The resolved numerical stack, recorded on every result
#: this pack produces.
#:
#: `ProvenanceRecord.environment` has existed, typed and serialized, since the
#: record was minted, and **no producer in the tree filled it**. That is not a
#: cosmetic gap. A frozen baseline in this repository drifted with the source,
#: the interpreter, the CPU and every declared dependency version held fixed:
#: what moved was the SIMD kernel OpenBLAS selects from CPUID at load time.
#: Version strings alone cannot express that — two runs producing different
#: numbers would record byte-identical environments — so `architecture`, which
#: `numpy.show_runtime()` reports and nothing else in the stack tracks, is
#: recorded beside them.
#:
#: This is caller-supplied, not auto-collected. `provenance.py` refuses to
#: collect anything itself, on privacy grounds, and that policy stands: nothing
#: here records a hostname, a path, a user or a timestamp. Only the resolved
#: numerical stack, which is a scientific input to the answer.
_ENVIRONMENT_CACHE: dict[str, str] | None = None


def scientific_environment() -> Mapping[str, str]:
    """The numerical stack that produced a result, for `ProvenanceRecord`.

    Cached: it cannot change within a process, and `show_runtime` is not cheap
    enough to call once per sub-solve of a fixed-point loop.
    """
    global _ENVIRONMENT_CACHE
    if _ENVIRONMENT_CACHE is not None:
        return _ENVIRONMENT_CACHE

    import contextlib
    import io
    import platform

    import numpy
    import scipy

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        numpy.show_runtime()
    # `show_runtime` pretty-prints nested dicts rather than returning them, so
    # the architecture arrives as one line of a repr. Take the quoted value and
    # nothing else; an unrecognised format records the empty string rather than
    # a fragment that would look like a real reading.
    architecture = ""
    for line in buffer.getvalue().splitlines():
        if "'architecture'" in line:
            _, _, tail = line.partition("'architecture'")
            parts = tail.split("'")
            architecture = parts[1] if len(parts) > 1 else ""
            break

    _ENVIRONMENT_CACHE = {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "blas_architecture": architecture,
    }
    return _ENVIRONMENT_CACHE


def native_circuit_solver(
    circuit: DCCircuit, run_id: str
) -> ScientificResult:
    """This pack's own way of solving one DC circuit. The default seam.

    Published so that the *default* and any substitute have the same type, and
    so a caller can state "solve it the way this pack always did" explicitly
    rather than by passing ``None``.
    """
    return solve_circuit(
        circuit,
        run_id=run_id,
        problem=build_dc_problem(circuit),
        environment=scientific_environment(),
    )


def _electrical_result(
    *, run_id: str, system: CoupledElectroThermalSystem,
    resistances: Mapping[str, Quantity],
    circuit_solver: CircuitSolver,
) -> ScientificResult:
    return circuit_solver(system.circuit_at(resistances), run_id)


def _executors(
    system: CoupledElectroThermalSystem,
    problems: Sequence[ScientificProblem],
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]]:
    """problem_id -> how this pack solves it, given its transported inputs.

    This mapping is the *only* place the loop learns which science sits behind
    which problem, and it is built here, in the system pack, from declarations
    the caller supplied. The iteration below reads a dependency graph and a
    dispatch table; it contains no electrical or thermal branch of its own.
    """
    electrical = next(
        p for p in problems if p.problem_id.startswith("electrical_dc:")
    )
    table: dict[str, Callable[[Mapping[str, Quantity], str], ScientificResult]] = {}

    def electrical_call(inputs: Mapping[str, Quantity], run_id: str):
        resistances = {
            stage.component_id: inputs[resistance_name(stage.component_id)]
            for stage in system.stages
        }
        return _electrical_result(
            run_id=run_id, system=system, resistances=resistances,
            circuit_solver=circuit_solver,
        )

    table[electrical.problem_id] = electrical_call

    for stage, prop, thermal in stage_problems(system):

        def property_call(inputs, run_id, _stage=stage, _problem=prop):
            return _property_result(
                run_id=run_id, stage=_stage, problem=_problem,
                temperature=inputs[mat.TEMPERATURE],
            )

        def thermal_call(inputs, run_id, _stage=stage, _problem=thermal):
            return _thermal_result(
                run_id=run_id, stage=_stage, problem=_problem,
                heat_input=inputs[lump.HEAT_INPUT],
            )

        table[prop.problem_id] = property_call
        table[thermal.problem_id] = thermal_call
    return table


@dataclass(frozen=True)
class AdmittedCoupledRun:
    """A coupled run, and the applicability of its models at the state it reached.

    **Two verdicts, kept apart, because they answer different questions.**
    ``run`` carries the numerical verdicts: did each sub-solve converge, and did
    the checks that ran pass. ``applicability`` carries a separate question the
    ``ValidationReport`` deliberately does not answer — *was the model valid at
    this physical condition* — and it is held on its own field, never converted
    into a :class:`ValidationCheck`. See
    :func:`engcore.domains.electrical.material.assess_resistance_validity`, whose
    docstring states the separation this record exists to preserve.

    **Ephemeral. Not serialized, and deliberately not a universal contract.** It
    exists because the verdict has nowhere else to live: ``ScientificResult`` and
    ``CoupledRun`` are frozen against a preregistration commit, and an
    application layer that computed the verdict itself would be performing a
    scientific act it did not execute. The same shape already ships one package
    away, as ``engcore.systems.propulsion.DriveRun``.

    Delete this record, and fold its contents back, when any one of these becomes
    true: a later milestone permitted to edit universal core gives
    ``ScientificResult`` or ``CoupledRun`` a typed applicability field; a second
    system pack needs the same carrier, at which point it should be promoted
    rather than duplicated; or the admission decision turns out to need nothing
    but the ``CoupledRun``.
    """

    run: CoupledRun
    applicability: Mapping[str, ValidityAssessment]

    @property
    def inapplicable(self) -> tuple[str, ...]:
        """Component ids whose model was outside its declared validity domain.

        ``UNKNOWN`` is not reported here: a condition that could not be tested is
        not a condition that failed, and conflating them would put NOT_RUN and
        FAIL on one footing — the distinction the whole validation module exists
        to keep.
        """
        return tuple(
            component_id
            for component_id, assessment in sorted(self.applicability.items())
            if assessment.status is ValidityStatus.OUTSIDE_VALIDATED_DOMAIN
        )


def assess_coupled_applicability(
    system: CoupledElectroThermalSystem, run: CoupledRun
) -> dict[str, ValidityAssessment]:
    """Was each stage's resistance model applicable at the state it converged to?

    **Assess, never refuse.** Returning a finding is the whole contract; the
    decision to act on it belongs to :func:`require_coupled_admission` and to
    nothing else. ``power_chain.assess_run_applicability`` states the same rule
    for its own consumer, and this is the same rule for this one.

    **Evaluated on the converged state, and only there.** The coupling is
    Gauss-Seidel from a seed, so intermediate iterates overshoot the fixed point
    and re-approach it: a sweep can leave the declared domain while the answer
    the run settles on sits inside it. Measured on this pack, four of eight
    swept supply voltages converge in-domain having passed through iterates up to
    64 K outside it. Assessing per iterate — or refusing there — would destroy
    four correct answers, which is why this reads ``run.final_values`` and
    nothing else.
    """
    assessments: dict[str, ValidityAssessment] = {}
    for stage, property_problem, _thermal in stage_problems(system):
        endpoint = (property_problem.problem_id, mat.TEMPERATURE)
        temperature = run.final_values.get(endpoint)
        if temperature is None:
            raise InvalidScientificProblem(
                f"the run carries no final value for {endpoint!r}; it did not "
                f"execute this system"
            )
        assessments[stage.component_id] = mat.assess_resistance_validity(
            property_problem, temperature
        )
    return assessments


def require_coupled_admission(admitted: AdmittedCoupledRun) -> None:
    """Raise unless every model was applicable at the state the run reached.

    **The admission decision, and the only thing here that refuses.** It reads a
    verdict it did not compute and decides whether the result may be consumed.
    Assessment reports; admission refuses; they are separate functions on
    purpose, because the same verdict is a finding to one caller and a stop to
    another.

    A caller that wants the numbers anyway can hold the
    :class:`AdmittedCoupledRun` and read them: nothing here mutates a record,
    and a refused run's results still construct, serialize and round-trip. A
    failed run is still evidence. What this protects is the *shipped* path, whose
    consumer cannot be relied upon to ask.
    """
    inapplicable = admitted.inapplicable
    if not inapplicable:
        return
    detail = "; ".join(
        f"{component_id!r}: {', '.join(admitted.applicability[component_id].violated)} "
        f"outside the declared validity domain"
        for component_id in inapplicable
    )
    raise ScientificValidationError(
        f"admission refused; the run converged to a state at which the model is "
        f"not declared valid: {detail}. The numbers are what the equations give; "
        f"the model is not claimed to hold there"
    )


def run_admitted_coupling(
    system: CoupledElectroThermalSystem,
    plan: FixedPointCouplingPlan,
    *,
    run_id: str = "et-coupled",
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> AdmittedCoupledRun:
    """Iterate the composition, then assess applicability at the state it reached.

    Assessment happens here, in the pack that executed the science, rather than
    in a caller — including the application boundary, which is forbidden from
    performing a scientific act it did not execute. **It does not refuse:** the
    record is returned whatever the verdict, and
    :func:`require_coupled_admission` is the separate step that decides.
    """
    run = run_fixed_point_coupling(
        system, plan, run_id=run_id, circuit_solver=circuit_solver
    )
    return AdmittedCoupledRun(
        run=run, applicability=assess_coupled_applicability(system, run)
    )


def run_fixed_point_coupling(
    system: CoupledElectroThermalSystem,
    plan: FixedPointCouplingPlan,
    *,
    run_id: str = "et-coupled",
    circuit_solver: CircuitSolver = native_circuit_solver,
) -> CoupledRun:
    """The electro-thermal entry point: build the composition, then iterate it.

    Everything domain-specific happens here — the problems, and the dispatch
    table that says how each of them is solved. :func:`run_fixed_point` receives
    both as data and runs the iteration without being able to name either.

    ``circuit_solver`` is the one substitution seam (see :data:`CircuitSolver`).
    It defaults to :func:`native_circuit_solver`, so a caller that does not pass
    it gets exactly the execution this function performed before the seam
    existed — asserted numerically, not assumed.
    """
    problems = coupled_problems(
        system,
        {stage.component_id: stage.conductor.reference_resistance
         for stage in system.stages},
    )
    return run_fixed_point(
        problems,
        _executors(system, problems, circuit_solver),
        plan,
        run_id=run_id,
        software_version="engcore.systems.electrothermal.coupled/0.1.0",
        assumptions=(
            "the resistance is evaluated at the transported temperature and "
            "held constant over the integrated interval; this is an implicit "
            "statement over one interval and carries a coupling error that is "
            "not quantified here",
            "the whole dissipated power of an element enters its body",
        ),
    )
