"""The loop, and the records it produces.

**Domain-neutral coupling infrastructure. Not universal scientific semantics.**

:func:`run_fixed_point` is a Gauss-Seidel (Picard) fixed-point iteration over a
torn dependency cycle. It sees a set of problems, a directed dependency set, a
plan, and a mapping from problem id to *something that solves that problem*.
Which sciences sit behind those callables is supplied by the caller and is
unreadable from here — which is what makes "the loop does not secretly know
what it is coupling" a checkable claim rather than an assurance, and it is
checked: an AST scan over the executable body refuses every domain token.

It is **not** a scheduler, a participant registry, a transfer operator, an
interpolator, a relaxation framework or a coupling platform. There is no
relaxation factor, no damping, no acceleration, no rollback, no checkpointing,
no event handling and no time synchronization. Two production consumers have
executed against it and neither forced one; a knob nothing measured is a
speculative knob.

It is also **not time marching.** Each participant's own declared conditions are
identical in every iteration; the iterate is a *coupling* iterate, not a time
level. :meth:`FixedPointCouplingPlan.check_against` refuses to seed an endpoint
a declared condition already determines, which is what keeps the two apart.

How the loop knows what feeds what
----------------------------------
It reads the declared
:class:`~engcore.scientific.composition.QuantityDependency` records. Every
transported value is looked up as

    ``result_of(dep.source_problem_id).values[dep.source_quantity]``

and delivered under ``dep.target_quantity``. **No metric name is constructed,
parsed or inferred inside the iteration.** Change a dependency's
``source_quantity`` to a different declared metric of the same dimension and
the loop transports something else and converges somewhere else — which is what
makes the records load-bearing rather than decorative.

The execution order is likewise computed, not written down: the torn edges are
removed and the remainder is topologically sorted. The loop never states an
order, and never chooses a tear.

Why these records are not in ``engcore.scientific``
--------------------------------------------------
Because no universal reader of them exists. There is no planner, no
execution-plan compiler and no scheduler anywhere in the platform, and all
three are deferred. What two consumers *did* measure is that the machinery is
shared by object identity while its serialized identity named one of them —
which is an **ownership** finding, answered by this package, and not evidence
that a coupling plan is a universal scientific record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ..scientific.composition import QuantityDependency
from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.problem import ModelReference, ScientificProblem
from ..scientific.results.provenance import ExecutionBinding, ProvenanceRecord
from ..scientific.results.result import ScientificResult
from ..scientific.serialization import require_schema, schema_string
from ..scientific.units.quantity import Quantity
from .graph import execution_order
from .plan import CouplingOutcome, FixedPointCouplingPlan

__all__ = [
    "COUPLED_ITERATION_SCHEMA",
    "COUPLED_RUN_SCHEMA",
    "CoupledIteration",
    "CoupledRun",
    "run_fixed_point",
]

COUPLED_ITERATION_SCHEMA = schema_string("coupling_iteration")
COUPLED_RUN_SCHEMA = schema_string("coupling_run")


@dataclass(frozen=True)
class CoupledIteration:
    """One pass of the loop: what was solved, and how far the iterate moved.

    ``results`` carries every :class:`ScientificResult` produced in this pass,
    so the value that crossed any declared edge is recoverable as
    ``result_for(dep.source_problem_id).values[dep.source_quantity]``. A
    companion ``CouplingTransfer`` record was designed and dropped for exactly
    that reason: it would have restated what these results already say.

    ``largest_iterate_change`` is the **change in the iterate**, not the
    residual of any equation. Those are different quantities: the iterate
    change measures how far a Gauss–Seidel sweep moved, and the residual
    measures how far the coupled system is from being satisfied. Nothing here
    computes the second, so nothing here may be named for it.

    It is a **difference** stored in a type that means an absolute value.
    ``Quantity`` draws no interval/ratio distinction, so a consumer could call
    ``.to()`` on it with an affine target and get nonsense. The plan's
    ratio-scale refusal is what keeps this field convertible; the limitation is
    stated here because the type cannot state it.
    """

    index: int
    results: tuple[ScientificResult, ...]
    largest_iterate_change: Quantity

    def __post_init__(self) -> None:
        object.__setattr__(self, "index", int(self.index))
        object.__setattr__(self, "results", tuple(self.results))
        if not isinstance(self.largest_iterate_change, Quantity):
            raise InvalidScientificProblem(
                "iterate change must be a Quantity"
            )

    def result_for(self, problem_id: str) -> ScientificResult:
        for result in self.results:
            if result.problem_id == problem_id:
                return result
        raise InvalidScientificProblem(
            f"iteration {self.index} produced no result for problem "
            f"{problem_id!r}"
        )

    def transported(self, dependency: QuantityDependency) -> Quantity:
        """The value that crossed this edge in this pass. Derived, not stored."""
        return self.result_for(dependency.source_problem_id).value(
            dependency.source_quantity
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": COUPLED_ITERATION_SCHEMA,
            "index": self.index,
            "results": [r.to_dict() for r in self.results],
            "largest_iterate_change": self.largest_iterate_change.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CoupledIteration":
        require_schema(payload, COUPLED_ITERATION_SCHEMA)
        return cls(
            index=payload["index"],
            results=tuple(
                ScientificResult.from_dict(r) for r in payload["results"]
            ),
            largest_iterate_change=Quantity.from_dict(
                payload["largest_iterate_change"]
            ),
        )


@dataclass(frozen=True)
class CoupledRun:
    """What the coupling iteration did, and why it stopped.

    ``outcome`` is the **only** statement of coupling convergence anywhere. It
    is not written into any ``ScientificResult.convergence``, any
    ``ValidationReport``, any ``SolverSettings.tolerances``, any
    ``ProvenanceRecord.tolerances``, or any metadata, diagnostics or artifacts
    mapping — and it is never computed from the sub-solves' own convergence.
    Every closed-form participant here reports ``NOT_APPLICABLE`` and the MNA
    solve reports ``CONVERGED`` in every iteration of a run that did not
    converge at all.
    """

    plan: FixedPointCouplingPlan
    outcome: CouplingOutcome
    iterations: tuple[CoupledIteration, ...]
    #: The last value each torn endpoint took, whatever the outcome.
    #:
    #: Named ``final_values`` and **not** ``converged_values``: it is populated
    #: identically on both exit paths, so on an ``ITERATION_LIMIT_REACHED`` run
    #: it holds an iterate six kelvin from the fixed point. A field named
    #: *converged* holding an unconverged number is one name meaning two things
    #: — the defect `MIN-FOUNDATION-ET` caught pre-commit as finding D-1, when
    #: it still cost a rename rather than a schema bump.
    #:
    #: Keyed by the ``(problem_id, quantity)`` pair itself, not by a
    #: ``"{problem}::{quantity}"`` string. Both components already contain
    #: colons, so a composite key would have to be parsed to be read — the
    #: string convention this platform refuses, and the association
    #: :class:`TornEndpoint` exists to carry structurally.
    final_values: Mapping[tuple[str, str], Quantity]
    provenance: ProvenanceRecord

    def __post_init__(self) -> None:
        if not isinstance(self.plan, FixedPointCouplingPlan):
            raise InvalidScientificProblem(
                "a coupled run requires the plan it executed"
            )
        if not isinstance(self.provenance, ProvenanceRecord):
            raise InvalidScientificProblem(
                "a coupled run requires a ProvenanceRecord: an unattributable "
                "iteration is not a scientific result"
            )
        object.__setattr__(self, "outcome", CouplingOutcome(self.outcome))
        iterations = tuple(self.iterations)
        if not iterations:
            raise InvalidScientificProblem(
                "a coupled run with no iterations executed nothing; the budget "
                "guarantees at least one"
            )
        for iteration in iterations:
            if not isinstance(iteration, CoupledIteration):
                raise InvalidScientificProblem(
                    f"coupled run iterations must be CoupledIteration records, "
                    f"got {type(iteration).__name__}"
                )
        object.__setattr__(self, "iterations", iterations)
        object.__setattr__(
            self,
            "final_values",
            {(str(p), str(q)): v for (p, q), v in dict(self.final_values).items()},
        )
        for name, value in self.final_values.items():
            if not isinstance(value, Quantity):
                raise InvalidScientificProblem(
                    f"final value {name!r} must be a Quantity"
                )

    @property
    def criterion_met(self) -> bool:
        """Derived from :attr:`outcome`, never stored beside it."""
        return self.outcome is CouplingOutcome.CRITERION_MET

    @property
    def iterations_run(self) -> int:
        return len(self.iterations)

    @property
    def final_iterate_change(self) -> Quantity:
        return self.iterations[-1].largest_iterate_change

    @property
    def iterate_changes(self) -> tuple[Quantity, ...]:
        return tuple(i.largest_iterate_change for i in self.iterations)

    @property
    def final(self) -> CoupledIteration:
        return self.iterations[-1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": COUPLED_RUN_SCHEMA,
            "plan": self.plan.to_dict(),
            "outcome": self.outcome.value,
            "iterations": [i.to_dict() for i in self.iterations],
            # A list of records, not a mapping keyed by a joined string. The
            # endpoint travels as its two components and is read back without
            # being parsed.
            "final_values": [
                {
                    "problem_id": problem_id,
                    "quantity": quantity,
                    "value": self.final_values[(problem_id, quantity)].to_dict(),
                }
                for problem_id, quantity in sorted(self.final_values)
            ],
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CoupledRun":
        require_schema(payload, COUPLED_RUN_SCHEMA)
        return cls(
            plan=FixedPointCouplingPlan.from_dict(payload["plan"]),
            outcome=CouplingOutcome(payload["outcome"]),
            iterations=tuple(
                CoupledIteration.from_dict(i) for i in payload["iterations"]
            ),
            final_values={
                (entry["problem_id"], entry["quantity"]): Quantity.from_dict(
                    entry["value"]
                )
                for entry in payload["final_values"]
            },
            provenance=ProvenanceRecord.from_dict(payload["provenance"]),
        )


def run_fixed_point(
    problems: Sequence[ScientificProblem],
    executors: Mapping[str, Callable[[Mapping[str, Quantity], str], ScientificResult]],
    plan: FixedPointCouplingPlan,
    *,
    run_id: str,
    software_version: str,
    assumptions: tuple[str, ...] = (),
) -> CoupledRun:
    """Execute a torn dependency cycle to convergence, or to the budget.

    A Gauss–Seidel sweep in the order the *records* imply: cut the torn edges,
    topologically sort what remains, and solve each problem with the values its
    incoming edges transported. Torn targets take the seed on the first pass and
    the previous pass's value afterwards.

    **Nothing in this function names a domain, and nothing in it can.** It sees
    a set of problems, a directed dependency set, a plan, and a mapping from
    problem id to *something that solves that problem*. Which sciences sit
    behind those callables is supplied by the caller and is unreadable from
    here — which is what makes "the loop does not secretly know what it is
    coupling" a checkable claim rather than an assurance, and it is checked by
    an AST scan over this body.

    It is **coupling infrastructure, not universal scientific semantics**. It
    is not promoted into ``engcore.scientific`` because no universal reader of
    a coupling plan or outcome exists; it lives in ``engcore.coupling`` because
    two production system packs execute against this exact object.

    Convergence is the largest change of any torn iterate, compared in one
    ratio-scale unit fixed by the plan. It is **not** derived from any
    participant's own convergence: in the non-convergent cases every sub-solve
    reports success in every one of the fifty iterations that did not converge.

    A sub-solve that refuses an inadmissible value is **not caught**. An
    execution failure and a failure to converge are different findings, and a
    loop that swallowed the first to report the second would be collapsing them.
    """
    seeds = {e.endpoint: e.initial_value for e in plan.torn}
    problems = tuple(problems)
    issues = plan.check_against(problems)
    if issues:
        raise InvalidScientificProblem(
            f"coupling plan {plan.plan_id!r} cannot be executed against this "
            f"composition: " + "; ".join(issues)
        )

    problem_ids = [p.problem_id for p in problems]
    # Three pairing guards. Every domain in this repository has them —
    # ``verify_problem_matches_circuit``, ``verify_problem_matches_body``,
    # ``verify_problem_matches_conductor`` — and the one place that *composes*
    # results is the place that most needs them. An external provider standing
    # in for a participant is exactly the producer most likely to hand back a
    # result carrying its own identity.
    duplicated = sorted({p for p in problem_ids if problem_ids.count(p) > 1})
    if duplicated:
        raise InvalidScientificProblem(
            f"duplicate problem id(s) {duplicated}: two problems under one id "
            f"would collapse into one solve and one attribution"
        )
    uncovered = sorted(set(problem_ids) - set(executors))
    if uncovered:
        raise InvalidScientificProblem(
            f"no executor was supplied for {uncovered}; a problem in the "
            f"composition that nothing solves cannot be ordered into a sweep"
        )

    order = execution_order(problem_ids, plan.uncut)
    if not order:
        raise InvalidScientificProblem(
            f"coupling plan {plan.plan_id!r} leaves a cycle after its declared "
            f"tears; no execution order exists"
        )

    unit = plan.comparison_unit
    tolerance = plan.absolute_tolerance.magnitude_in(unit)
    incoming: dict[str, list[QuantityDependency]] = {p: [] for p in problem_ids}
    for dependency in plan.uncut:
        incoming[dependency.target_problem_id].append(dependency)

    current = dict(seeds)
    iterations: list[CoupledIteration] = []
    outcome = CouplingOutcome.ITERATION_LIMIT_REACHED

    for index in range(1, plan.max_iterations + 1):
        produced: dict[str, ScientificResult] = {}
        for problem_id in order:
            inputs: dict[str, Quantity] = {}
            for dependency in incoming[problem_id]:
                inputs[dependency.target_quantity] = produced[
                    dependency.source_problem_id
                ].value(dependency.source_quantity)
            # Torn targets take the seed on the first pass and the previous
            # pass's value afterwards. This cannot shadow a transported value:
            # the plan refuses two dependencies sharing a target endpoint, so a
            # torn edge's endpoint is never also an uncut edge's. An earlier
            # form had no such refusal, and this assignment then silently
            # discarded the transported value.
            for endpoint, value in current.items():
                if endpoint[0] == problem_id:
                    inputs[endpoint[1]] = value
            result = executors[problem_id](
                inputs, f"{run_id}-{index}-{problem_id}"
            )
            if result.problem_id != problem_id:
                raise InvalidScientificProblem(
                    f"the executor for {problem_id!r} returned a result "
                    f"attributed to {result.problem_id!r}; a composition that "
                    f"accepted that would misattribute every value it "
                    f"transported out of it"
                )
            produced[problem_id] = result

        updated: dict[tuple[str, str], Quantity] = {}
        largest = 0.0
        for endpoint in plan.torn:
            key = endpoint.endpoint
            value = produced[endpoint.dependency.source_problem_id].value(
                endpoint.dependency.source_quantity
            )
            updated[key] = value
            largest = max(
                largest,
                abs(value.magnitude_in(unit) - current[key].magnitude_in(unit)),
            )

        iterations.append(
            CoupledIteration(
                index=index,
                results=tuple(produced[p] for p in order),
                largest_iterate_change=Quantity(largest, unit),
            )
        )
        current = updated
        if largest <= tolerance:
            outcome = CouplingOutcome.CRITERION_MET
            break

    # Every iteration, not only the last. For this consumer every sweep binds
    # the same participants, so the two agree — but this function is generic,
    # and an executor that changed realization mid-run (an adaptive fallback, a
    # provider degrading to a coarser method) would leave those bindings out of
    # a last-iteration-only record. ``ProvenanceRecord`` deduplicates by key,
    # so the union costs nothing and cannot under-claim.
    bindings: list[ExecutionBinding] = []
    for result in [r for iteration in iterations for r in iteration.results]:
        if result.provenance.bindings:
            bindings.extend(result.provenance.bindings)
        else:
            # Producers predating MODEL0-R declare participants without an
            # association. The electrical solver is one; its models are named
            # by the circuit it solved, and pairing them with its solver here
            # states an association it did make. Nothing is inferred about a
            # realization: it stays None, which is a real answer.
            bindings.extend(
                ExecutionBinding(
                    model=ModelReference(model_id, version),
                    realization=None,
                    solver=result.solver,
                )
                for model_id, version in result.models
            )

    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version=software_version,
        bindings=tuple(bindings),
        # ``ProvenanceRecord.inputs`` is ``Mapping[str, Quantity]`` in frozen
        # core, so an endpoint has to be flattened to reach it. Recorded as a
        # stated limitation rather than left silent: this key must be parsed to
        # be read back, and ``CoupledRun.final_values`` is the record that
        # carries the same endpoints structurally.
        inputs={f"{p}::{q}": v for (p, q), v in sorted(current.items())},
        assumptions=(
            "Gauss-Seidel fixed-point iteration over a torn dependency cycle",
            "no relaxation, damping or acceleration is applied",
            "every problem's own declared conditions are identical in every "
            "iteration; the iterate is a coupling iterate and not a time level",
        )
        + tuple(assumptions),
    )

    return CoupledRun(
        plan=plan,
        outcome=outcome,
        iterations=tuple(iterations),
        final_values=dict(current),
        provenance=provenance,
    )
