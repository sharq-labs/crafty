"""``VariableBulkLinkage`` — which declared variable a bulk reference is of.

The measured gap, corroborated by six consumers across two prior milestones
(`docs/cross-domain-coverage-stress-evidence.md` §6.1,
`docs/exec-spec-structured-input-stress-evidence.md` §I):
``ScientificDataReference`` carries ``{name, unit, count, dtype, digest,
digest_algorithm}`` and *no field naming a variable*. A records-only reader
handed an eight-value displacement array, or a three-quantity state
trajectory, cannot say which declared ``ScientificVariable`` — of possibly
several sharing a dimension — the values belong to.

What is NOT the gap, measured before this record was written
---------------------------------------------------------------
``ScientificVariable.categories`` already gives a typed, ordered, named-member
set (`docs/exec-spec-structured-input-stress-evidence.md` §F: "a categorical
`ScientificVariable` carries an **ordered** tuple of named members that
round-trips deterministically... an ordered index set of named entities *is*
representable in universal core today"). The prior milestones' first reading —
that the ordering itself was unrepresentable — was wrong, and is not repeated
here. What remained missing, and what this record supplies, is narrower: the
*binding* of a specific bulk artifact to a specific declared variable. Nothing
here re-invents an ordered-index-set concept that already exists.

What was tried first, and rejected, before this record was written
--------------------------------------------------------------------
* The reference's own free-text ``name`` (``"c:A:trajectory"``) — DATA-
  BOUNDARY0 explicitly sanctions scientific punctuation in names, and a human
  reads it easily. A *records-only reader* cannot: parsing meaning out of a
  name string is exactly the "meaning-in-key" failure mode
  ``EXEC-SPEC-STRUCTURED`` §C catalogued and refused for element connectivity,
  applied load indexing and stoichiometric coefficients alike. Nothing changes
  that refusal here.
* ``ScientificParameter`` carrying the reference name as a string value — data,
  not a typed, checked cross-reference; nothing would verify it resolves or is
  dimensionally consistent.
* ``ScientificResult.metadata`` — the untyped escape hatch this platform
  refuses everywhere else.

Both failure modes are executed, not asserted, in
``tests/test_min_cross_domain_foundation.py``.

What this record deliberately does not carry
----------------------------------------------
No shape, mesh, stride, interleaving, axis order, topology, coordinate frame
or support. ``DATA-BOUNDARY0`` intentionally leaves those undecided
(``docs/scientific-core/README.md`` "Bulk scientific data: identity, not
location"), and nothing here closes that door. The record states only that
*this* reference's values, in the reference's own order, are the values of
*this* variable. A combined array interleaving several variables is not this
record's problem to solve: the reduction attempt that led here found that
splitting such an array into one reference per named quantity (mirroring how
``ScientificResult.values`` already keys distinct scalar metrics one-per-name)
removes the interleaving question entirely, at the cost of one linkage record
per quantity rather than one record naming an axis order. That is the
reduction this record's minimal two-field shape assumes; it is not itself
proof that no domain will ever need axis-order semantics, and none is
claimed.

Why standalone, not a field
------------------------------
Three existing, load-bearing reasons, the same three that kept
``QuantityDependency`` standalone (see the ``MIN-FOUNDATION-ET`` milestone's
evidence document), checked against this record specifically:

* ``ScientificDataReference`` is schema-pinned at ``scientific_data_reference/1``
  with ``require_schema`` an exact string match; adding a field would move the
  schema and make every stored reference unloadable by a pre-milestone reader,
  for a fact ("which variable") that is not true of the *bytes* the reference
  identifies — it is a fact about how one particular problem+result pair
  interprets them.
* ``ScientificVariable`` is a reusable declaration; welding a specific bulk
  artifact's identity onto it would make the same variable, filled by a
  different solve, a different variable.
* A linkage is meaningful only paired with the one problem and the one result
  it names, exactly as a scalar metric name is meaningful only against the
  ``ScientificResult`` that reports it. Neither ``ScientificDataReference`` nor
  ``ScientificVariable`` carries a ``result_id``/``problem_id`` today, and this
  record does not add one either — see "What this record does not decide"
  below.

What this record does not decide
-----------------------------------
It does not carry ``problem_id`` or ``result_id``. Precedent:
``ScientificDataReference`` itself carries no ``result_id`` — it is scoped
implicitly by whichever ``ScientificResult.data_references`` tuple holds it.
A ``VariableBulkLinkage`` is scoped the same way, by whichever collection a
caller holds it alongside; :meth:`check_against` takes the problem and result
to check against as explicit arguments precisely because nothing here can
resolve them on its own. Reusing that existing convention is deliberate:
inventing a redundant identity pair here would duplicate an existing implicit
contract rather than close a gap.

It also enforces no collection-level invariant: nothing here refuses two
linkages naming the same reference, or a set of linkages covering less than
every ``data_reference`` on a result. ``MIN-FOUNDATION-ET``'s evidence
recorded the identical limitation for ``QuantityDependency`` ("No collection
type owns dependency-set invariants") and it is repeated here honestly rather
than silently fixed on zero consumer evidence that any particular rule is
right.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..errors import InvalidScientificProblem
from ..models.definition import BindingIssue, BindingIssueKind
from ..serialization import require_schema, schema_string
from ..units.quantity import dimensionality

VARIABLE_BULK_LINKAGE_SCHEMA = schema_string("variable_bulk_linkage")

__all__ = [
    "VARIABLE_BULK_LINKAGE_SCHEMA",
    "VariableBulkLinkage",
    "unlinked_references",
]


@dataclass(frozen=True)
class VariableBulkLinkage:
    """``reference_name``'s values, in the reference's own order, are the
    values of the declared variable ``variable_name``.

    Deliberately two names and nothing else — see the module docstring for
    what was tried and rejected before this shape, and what it deliberately
    does not carry.
    """

    variable_name: str
    reference_name: str
    description: str = ""

    def __post_init__(self) -> None:
        for label in ("variable_name", "reference_name"):
            raw = str(getattr(self, label)).strip()
            if not raw:
                raise InvalidScientificProblem(
                    f"variable bulk linkage requires a non-empty {label}"
                )
            object.__setattr__(self, label, raw)
        object.__setattr__(self, "description", str(self.description))

    # ---- checking --------------------------------------------------------
    def check_against(
        self, *, problem: Any = None, result: Any = None
    ) -> tuple[BindingIssue, ...]:
        """Report why this linkage does not fit the records it names.

        Returns issues; an empty tuple means every check that could be run
        passed. Reuses :class:`BindingIssue` rather than minting a parallel
        issue type — precedent: ``QuantityDependency.check_against``. Passing
        neither argument checks nothing and says so by returning no issues,
        exactly as ``QuantityDependency`` does: the two sides are knowable at
        different times, and an absent argument is not a failing check.

        ``reference_name`` is resolved against **both**
        ``result.data_references`` (an output field, DATA-BOUNDARY0) and, if
        present, ``problem.data_references`` (an input field, added by
        MIN-FIELD-SUPPORT-FOUNDATION) — a bulk array a linkage names may be
        something a result produced or something a problem statement
        prescribed (a non-uniform initial or boundary field, a field-valued
        coefficient). A single linkage type serves both directions; nothing
        about its shape changed to add this, only where it is allowed to look.
        """
        issues: list[BindingIssue] = []
        variable = None
        if problem is not None:
            for candidate in getattr(problem, "variables", ()):
                if candidate.name == self.variable_name:
                    variable = candidate
                    break
            if variable is None:
                problem_id = getattr(problem, "problem_id", "?")
                issues.append(
                    BindingIssue(
                        self.variable_name,
                        BindingIssueKind.MISSING,
                        f"problem {problem_id!r} declares no variable named "
                        f"{self.variable_name!r}",
                    )
                )

        reference = None
        if result is not None:
            for candidate in getattr(result, "data_references", ()):
                if candidate.name == self.reference_name:
                    reference = candidate
                    break
        if reference is None and problem is not None:
            for candidate in getattr(problem, "data_references", ()):
                if candidate.name == self.reference_name:
                    reference = candidate
                    break
        if reference is None and (result is not None or problem is not None):
            owners = []
            if result is not None:
                owners.append(f"result {getattr(result, 'result_id', '?')!r}")
            if problem is not None:
                owners.append(
                    f"problem {getattr(problem, 'problem_id', '?')!r}"
                )
            subject = owners[0] if len(owners) == 1 else " nor ".join(owners)
            verb = "carries" if len(owners) == 1 else "carry"
            prefix = "" if len(owners) == 1 else "neither "
            issues.append(
                BindingIssue(
                    self.reference_name,
                    BindingIssueKind.MISSING,
                    f"{prefix}{subject} {verb} no data reference named "
                    f"{self.reference_name!r}",
                )
            )

        if variable is not None and reference is not None:
            if dimensionality(variable.unit) != dimensionality(reference.unit):
                issues.append(
                    BindingIssue(
                        self.variable_name,
                        BindingIssueKind.WRONG_DIMENSION,
                        f"variable {self.variable_name!r} carries "
                        f"{variable.unit!r} [{dimensionality(variable.unit)}] "
                        f"but reference {self.reference_name!r} carries "
                        f"{reference.unit!r} [{dimensionality(reference.unit)}]",
                    )
                )
        return tuple(issues)

    # ---- serialization -----------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": VARIABLE_BULK_LINKAGE_SCHEMA,
            "variable_name": self.variable_name,
            "reference_name": self.reference_name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "VariableBulkLinkage":
        require_schema(payload, VARIABLE_BULK_LINKAGE_SCHEMA)
        return cls(
            variable_name=payload["variable_name"],
            reference_name=payload["reference_name"],
            description=payload.get("description", ""),
        )


def unlinked_references(
    result: Any, linkages: Iterable[VariableBulkLinkage]
) -> tuple[str, ...]:
    """Names of ``result.data_references`` that no linkage names.

    The complement of the declared linkages, mirroring
    ``composition.externally_imposed``'s relationship to
    ``unresolved_inputs``. An empty result does not mean every array is
    scientifically meaningful — it means every one this reader could *see*
    has a stated variable.
    """
    named = {linkage.reference_name for linkage in linkages}
    return tuple(
        reference.name
        for reference in getattr(result, "data_references", ())
        if reference.name not in named
    )
