"""Readers of a declared dependency set. They report; they choose nothing.

**Domain-neutral coupling infrastructure. Not universal scientific semantics.**
Every function here takes
:class:`~engcore.scientific.composition.QuantityDependency` records and a set of
problem ids and answers a question about the *graph* they describe: what order
admits them, which of them lie on a cycle, and what identifies an edge. None of
them knows what a transported value means, and none of them selects which edge
to cut — three edges of a 3-cycle are equally admissible tears and nothing in
any record ranks them.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from ..scientific.composition import QuantityDependency

__all__ = ["cycle_edges", "edge_key", "execution_order"]


def edge_key(dependency: QuantityDependency) -> tuple[str, str, str, str]:
    """The identity of an edge: its two endpoints, and nothing else.

    One notion of edge identity, used everywhere. An earlier form tested torn
    membership by whole-record equality and computed the uncut set by this quad,
    so two records differing only in ``unit_exemplar`` were distinct for one
    purpose and identical for the other — the near-duplicate hazard
    `MIN-FOUNDATION-ET` recorded as known unknown 6, met for the first time.
    """
    return (
        dependency.source_problem_id,
        dependency.source_quantity,
        dependency.target_problem_id,
        dependency.target_quantity,
    )


def _edges(dependencies: Iterable[QuantityDependency]) -> list[tuple[str, str]]:
    return [(d.source_problem_id, d.target_problem_id) for d in dependencies]


def execution_order(
    problem_ids: Sequence[str], dependencies: Iterable[QuantityDependency]
) -> tuple[str, ...]:
    """A deterministic order in which these problems may be solved.

    Kahn's algorithm with a sorted tie-break, so the order is a function of the
    records and not of insertion. Returns an empty tuple when no order exists —
    which is the answer for a cycle, not an error, because reporting that a
    composition is cyclic is exactly what a reader of a composition is for.

    It **reports**. It never chooses which edge to cut: three edges of a
    3-cycle are equally admissible tears, nothing in any record ranks them, and
    the only rule that would select one keys on a domain modelling a computed
    quantity as a configured parameter — an undeclared accident, not a law.
    """
    remaining = {str(p) for p in problem_ids}
    incoming: dict[str, int] = {p: 0 for p in remaining}
    outgoing: dict[str, list[str]] = {p: [] for p in remaining}
    for source, target in _edges(dependencies):
        if source not in remaining or target not in remaining or source == target:
            continue
        outgoing[source].append(target)
        incoming[target] += 1

    ready = sorted(p for p in remaining if incoming[p] == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for target in sorted(outgoing[node]):
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
                ready.sort()
    return tuple(order) if len(order) == len(remaining) else ()


def cycle_edges(
    problem_ids: Sequence[str], dependencies: Iterable[QuantityDependency]
) -> tuple[QuantityDependency, ...]:
    """The dependencies that lie on the cyclic core. Reports; chooses nothing.

    Computed by peeling: repeatedly discard any node with no incoming edges
    (nothing feeds it, so it cannot be downstream of a cycle) and any node with
    no outgoing edges (it feeds nothing, so it cannot be upstream of one). What
    remains is exactly the part of the graph a topological order cannot reach,
    and the edges among it are the ones that must be cut.

    An earlier form asked :func:`execution_order` for the settled set — which
    that function discards whenever an order does not exist — so on any cyclic
    graph the settled set was empty and **every** edge was reported as cyclic.
    On the first consumer's own composition, a pure 3-cycle, that was
    indistinguishable from the right answer. It was wrong for `A→B, B→C, C→B`,
    where it named `A→B`.
    """
    nodes = {str(p) for p in problem_ids}
    edges = [
        d
        for d in dependencies
        if d.source_problem_id in nodes
        and d.target_problem_id in nodes
        and d.source_problem_id != d.target_problem_id
    ]
    remaining = set(nodes)
    while True:
        sources = {d.source_problem_id for d in edges
                   if d.source_problem_id in remaining
                   and d.target_problem_id in remaining}
        targets = {d.target_problem_id for d in edges
                   if d.source_problem_id in remaining
                   and d.target_problem_id in remaining}
        core = remaining & sources & targets
        if core == remaining:
            break
        remaining = core
        if not remaining:
            break
    return tuple(
        d
        for d in edges
        if d.source_problem_id in remaining and d.target_problem_id in remaining
    )
