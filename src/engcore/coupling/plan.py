"""The pre-execution declaration: what is cut, seeded, compared and budgeted.

**Domain-neutral coupling infrastructure. Not universal scientific semantics.**
A dependency set containing a cycle has **zero** admissible execution orders.
Making it executable requires four facts no existing record carries: which
edges are cut, what value each cut edge's target takes at iteration 1, when to
stop, and how long to try. :class:`FixedPointCouplingPlan` carries exactly
those, and nothing else.

These records **transport identities and values**. They do not know what any
transported value means — not its science, not its equation, not its material
law. That boundary is the reason this package exists separately from the system
packs that build the plans, and it is checked rather than asserted: an AST scan
over the executable source of every object here refuses any domain vocabulary.

This is **not** a promotion into universal scientific Core. No universal reader
of a coupling plan or a coupling outcome exists anywhere in the platform;
``engcore.coupling`` is execution/composition infrastructure shared by the
system packs, one layer below them and one layer above nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from ..scientific.composition import QuantityDependency
from ..scientific.errors import InvalidScientificProblem
from ..scientific.ir.problem import ScientificProblem
from ..scientific.serialization import require_schema, schema_string
from ..scientific.units.quantity import Quantity
from .graph import edge_key
from .scales import _require_ratio_scale, shares_origin

__all__ = [
    "FIXED_POINT_PLAN_SCHEMA",
    "TORN_ENDPOINT_SCHEMA",
    "CouplingOutcome",
    "FixedPointCouplingPlan",
    "TornEndpoint",
]

TORN_ENDPOINT_SCHEMA = schema_string("coupling_torn_endpoint")
FIXED_POINT_PLAN_SCHEMA = schema_string("coupling_fixed_point_plan")


class CouplingOutcome(str, Enum):
    """Why the coupling iteration stopped. **Never a scientific verdict.**

    Deliberately **not** :class:`~engcore.scientific.solvers.protocol.ConvergenceState`.
    Both closed-form participants here report ``NOT_APPLICABLE``, which
    ``RawSolverOutput.succeeded`` and ``ScientificResult.is_usable`` treat as
    success; reusing that enum would make "the coupled loop converged" and "a
    closed-form evaluation happened" the same serialized token, permanently, on
    a record that is already at ``scientific_result/2``.

    Members are limited to the ones a production consumer has actually
    executed. A ``DIVERGED`` member is deliberately absent: nothing here
    implements a divergence test, and `MODEL0-R` already had to delete an enum
    member (``SURROGATE``) that was minted from intuition.
    """

    CRITERION_MET = "criterion_met"
    ITERATION_LIMIT_REACHED = "iteration_limit_reached"


@dataclass(frozen=True)
class TornEndpoint:
    """One cut edge of the dependency cycle, paired with the seed it needs.

    The pairing is **structural**, not positional: two parallel tuples of
    dependencies and seeds would carry the association in an index, which is
    exactly the defect ``ExecutionBinding`` exists to prevent one level down.

    The seed supplies ``dependency.target_quantity`` of
    ``dependency.target_problem_id`` at iteration 1. It is not recoverable from
    any record — measured by both production consumers, see
    ``docs/coupling-pack-relocation-evidence.md`` §L — and it is deliberately
    not inferred.
    """

    dependency: QuantityDependency
    initial_value: Quantity

    def __post_init__(self) -> None:
        if not isinstance(self.dependency, QuantityDependency):
            raise InvalidScientificProblem(
                "torn endpoint requires a QuantityDependency"
            )
        if not isinstance(self.initial_value, Quantity):
            raise InvalidScientificProblem(
                "torn endpoint seed must be a Quantity — a bare number carries "
                "no unit and cannot be checked against the edge it seeds"
            )
        if self.initial_value.dimensionality != self.dependency.dimension:
            raise InvalidScientificProblem(
                f"torn endpoint seed carries {self.initial_value.units!r} "
                f"[{self.initial_value.dimensionality}] but the edge transports "
                f"{self.dependency.unit_exemplar!r} [{self.dependency.dimension}]"
            )

    @property
    def endpoint(self) -> tuple[str, str]:
        """``(problem_id, quantity)`` of the endpoint this seed supplies."""
        return (self.dependency.target_problem_id, self.dependency.target_quantity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TORN_ENDPOINT_SCHEMA,
            "dependency": self.dependency.to_dict(),
            "initial_value": self.initial_value.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TornEndpoint":
        require_schema(payload, TORN_ENDPOINT_SCHEMA)
        return cls(
            dependency=QuantityDependency.from_dict(payload["dependency"]),
            initial_value=Quantity.from_dict(payload["initial_value"]),
        )


@dataclass(frozen=True)
class FixedPointCouplingPlan:
    """Everything needed to execute a cyclic dependency set, stated before it runs.

    A dependency set that contains a cycle has **zero** admissible execution
    orders. Making it executable requires four facts that no existing record
    carries: which edges are cut, what value each cut edge's target takes at
    iteration 1, when to stop, and how long to try. This record carries exactly
    those and nothing else.

    It is a record rather than a set of keyword arguments for the same reason
    ``QuantityDependency`` is: it must be inspectable *before* anything runs.
    A ``float`` tolerance additionally could not be checked at all — the
    dimension check against the torn edge, and the refusal of an affine scale,
    are only possible because the tolerance carries its unit.
    """

    plan_id: str
    dependencies: tuple[QuantityDependency, ...]
    torn: tuple[TornEndpoint, ...]
    absolute_tolerance: Quantity
    max_iterations: int

    def __post_init__(self) -> None:
        plan_id = str(self.plan_id).strip()
        if not plan_id:
            raise InvalidScientificProblem("coupling plan requires a plan_id")
        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        object.__setattr__(self, "torn", tuple(self.torn))

        if not self.dependencies:
            raise InvalidScientificProblem(
                "a coupling plan over no dependencies composes nothing"
            )
        if not self.torn:
            raise InvalidScientificProblem(
                "a coupling plan must cut at least one edge; an uncut cycle has "
                "no admissible execution order"
            )

        declared = {edge_key(d) for d in self.dependencies}
        for endpoint in self.torn:
            if edge_key(endpoint.dependency) not in declared:
                raise InvalidScientificProblem(
                    f"torn edge {endpoint.dependency.name or endpoint.endpoint!r} "
                    f"is not one of the plan's declared dependencies; cutting an "
                    f"edge the composition does not contain states nothing"
                )

        # Fan-in is REPORTED as unrepresentable, never resolved by accident.
        #
        # Two edges into one endpoint are individually valid records — each
        # checks clean, and MIN-FOUNDATION-ET measured exactly that. What no
        # record states is how to combine them: sum, override, or split. A
        # dict of transported values keyed by target quantity would resolve it
        # silently by declaration order, which is a combination rule invented
        # from one consumer and hidden in an insertion order. Refused instead,
        # in the same voice as the mixed-dimension refusal below.
        for label, keys in (
            (
                "dependencies",
                [(d.target_problem_id, d.target_quantity) for d in self.dependencies],
            ),
            ("torn edges", [e.endpoint for e in self.torn]),
        ):
            duplicated = sorted({k for k in keys if keys.count(k) > 1})
            if duplicated:
                raise InvalidScientificProblem(
                    f"{len(duplicated)} endpoint(s) receive more than one of "
                    f"this plan's {label}: {duplicated}. No record states "
                    f"whether they sum, override or split, so the composition "
                    f"is refused rather than combined by invention"
                )

        if not isinstance(self.absolute_tolerance, Quantity):
            raise InvalidScientificProblem(
                "coupling tolerance must be a Quantity — the criterion belongs "
                "to coupling execution and a bare float cannot be checked "
                "against the quantity it stops"
            )
        magnitude = self.absolute_tolerance.magnitude
        if not math.isfinite(magnitude) or magnitude <= 0.0:
            raise InvalidScientificProblem(
                f"coupling tolerance must be finite and strictly positive, got "
                f"{magnitude!r} {self.absolute_tolerance.units}"
            )
        _require_ratio_scale(
            self.absolute_tolerance.units, label="coupling tolerance"
        )

        dimensions = {e.dependency.dimension for e in self.torn}
        if len(dimensions) != 1:
            raise InvalidScientificProblem(
                f"the torn edges transport {len(dimensions)} different "
                f"dimensions ({sorted(dimensions)}); one scalar tolerance "
                f"cannot serve them and no record states how to normalize "
                f"between them. Refused rather than normalized by invention"
            )
        (dimension,) = dimensions
        if self.absolute_tolerance.dimensionality != dimension:
            raise InvalidScientificProblem(
                f"coupling tolerance carries "
                f"{self.absolute_tolerance.units!r} "
                f"[{self.absolute_tolerance.dimensionality}] but the torn edges "
                f"transport [{dimension}]"
            )
        # Published-contract check, in addition to the backend-assisted one:
        # the tolerance and every torn edge must share a zero, or a conversion
        # between them is not a conversion of a difference.
        for endpoint in self.torn:
            for unit in (
                endpoint.dependency.unit_exemplar,
                endpoint.initial_value.units,
            ):
                if not shares_origin(unit, self.absolute_tolerance.units):
                    raise InvalidScientificProblem(
                        f"{unit!r} and {self.absolute_tolerance.units!r} do not "
                        f"share a zero, so a difference converted between them "
                        f"is not a difference"
                    )

        budget = int(self.max_iterations)
        if budget < 1:
            raise InvalidScientificProblem(
                f"coupling budget must allow at least one iteration, got {budget}"
            )
        object.__setattr__(self, "max_iterations", budget)

    @property
    def comparison_unit(self) -> str:
        """The one unit both sides of every comparison are converted into."""
        return self.absolute_tolerance.units

    @property
    def torn_endpoints(self) -> tuple[tuple[str, str], ...]:
        return tuple(e.endpoint for e in self.torn)

    @property
    def uncut(self) -> tuple[QuantityDependency, ...]:
        """The dependencies that remain, and are therefore ordered, not seeded."""
        cut = {edge_key(e.dependency) for e in self.torn}
        return tuple(d for d in self.dependencies if edge_key(d) not in cut)

    def unsupplied(
        self, problems: Iterable[ScientificProblem]
    ) -> tuple[tuple[str, str, str], ...]:
        """Inputs this plan supplies no edge for. **Reported, never refused.**

        Core's :func:`externally_imposed` answers this, and its answer is
        deliberately ambiguous: an input with no supplier is either genuinely
        imposed by the environment or forgotten, and **no record distinguishes
        the two**. An input the environment really does impose and an input
        somebody forgot to wire read identically here.

        So this reports and the caller decides. A plan that omits a required
        edge is therefore *not* refused before the first iteration — which is a
        measured limitation of the records, recorded rather than papered over,
        and the reason the failure surfaces from the executor instead.
        """
        from ..scientific.composition import externally_imposed

        return externally_imposed(problems, self.dependencies)

    def check_against(
        self, problems: Iterable[ScientificProblem]
    ) -> tuple[str, ...]:
        """Every reason this plan cannot be executed against these problems.

        Reported before the first iteration. A dependency that names a quantity
        no record enumerates, or transports a dimension the endpoint does not
        carry, is a **malformed declaration** — not a scientific finding — so
        the caller raises on a non-empty result rather than recording it.

        Sources that are result metrics cannot be checked here: they do not
        exist until a solve has produced them. The asymmetry is real and is not
        papered over.
        """
        by_id = {p.problem_id: p for p in problems}
        issues: list[str] = []
        for dependency in self.dependencies:
            for side, problem_id in (
                ("target", dependency.target_problem_id),
                ("source", dependency.source_problem_id),
            ):
                if problem_id not in by_id:
                    issues.append(
                        f"{side} problem {problem_id!r} is not part of the "
                        f"composition"
                    )
            target = by_id.get(dependency.target_problem_id)
            if target is not None:
                for issue in dependency.check_against(target_problem=target):
                    issues.append(
                        f"{issue.kind.value}: {issue.name}: {issue.detail}"
                    )

        # A torn endpoint whose target is already determined by a declared
        # condition is refused. The seed would override the condition, and for
        # a STATE variable pinned by an initial condition that override is
        # precisely time marching wearing the name of coupling.
        for endpoint in self.torn:
            target = by_id.get(endpoint.dependency.target_problem_id)
            if target is None:
                continue
            determined = {c.variable for c in target.initial_conditions}
            determined |= {c.variable for c in target.boundary_conditions}
            if endpoint.dependency.target_quantity in determined:
                issues.append(
                    f"seeded_over_condition: "
                    f"{endpoint.dependency.target_quantity}: problem "
                    f"{target.problem_id!r} already determines it by a declared "
                    f"condition; seeding it would override the condition, and "
                    f"for a state variable that is time marching rather than "
                    f"coupling"
                )
        return tuple(issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FIXED_POINT_PLAN_SCHEMA,
            "plan_id": self.plan_id,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "torn": [e.to_dict() for e in self.torn],
            "absolute_tolerance": self.absolute_tolerance.to_dict(),
            "max_iterations": self.max_iterations,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FixedPointCouplingPlan":
        require_schema(payload, FIXED_POINT_PLAN_SCHEMA)
        return cls(
            plan_id=payload["plan_id"],
            dependencies=tuple(
                QuantityDependency.from_dict(d) for d in payload["dependencies"]
            ),
            torn=tuple(TornEndpoint.from_dict(e) for e in payload["torn"]),
            absolute_tolerance=Quantity.from_dict(payload["absolute_tolerance"]),
            max_iterations=payload["max_iterations"],
        )
