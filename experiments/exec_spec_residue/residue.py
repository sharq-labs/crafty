"""The residue table, and the decision rule that was preregistered before it ran.

A **residue item** is a fact a domain needs in order to execute that no existing
typed contract can carry. Preregistration §6 makes the standard for declaring one
strict: every item here names the channels that were tried and the executed
outcome of each. An item with no failed attempt behind it is a fail condition.

Two readings are reported, and the difference between them is the milestone's
sharpest distinction:

**STRICT** — a residue item exists only when *no* existing contract can carry the
fact at all.

**PLACEMENT** — a residue item also exists when a contract can carry the fact
mechanically, but only by putting it somewhere that makes a different claim than
the science does (a numerical setting inside the statement of the physics, or a
relation inside the spelling of a key).

Reporting only STRICT would say the CSTR is finished, which is false in a way
that matters. Reporting only PLACEMENT would inflate every awkward encoding into
an architectural gap, which is how a platform acquires records it does not need.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .encodings import ATTEMPTS, AttemptOutcome, EncodingAttempt

__all__ = [
    "Reading",
    "ResidueKind",
    "Ledger",
    "ResidueItem",
    "RESIDUE",
    "residue_for",
    "table",
    "decide",
    "Decision",
]


class Reading(str, Enum):
    STRICT = "strict"
    PLACEMENT = "placement"


class ResidueKind(str, Enum):
    """What kind of fact is left over. They are not interchangeable."""

    SCIENTIFIC_STRUCTURE = "scientific-structure"
    CONDITION = "condition"
    DISCRETIZATION = "discretization"
    NUMERICAL_SETTING = "numerical-setting"


class Ledger(str, Enum):
    """`HOSTILE-CORE-STRESS`'s booking rule, carried verbatim.

    A finding is Ledger 1 only when **both** the measurement and the remedy live
    in a record that already exists. Where the remedy needs a record that does
    not exist, it is Ledger 2 and claims zero evidence gain — the concept was
    already recorded as deferred, and measuring a deferral is not discovering it.
    """

    EXISTING_RECORD = "ledger-1: record exists"
    ABSENT_RECORD = "ledger-2: record does not exist"


@dataclass(frozen=True)
class ResidueItem:
    column: str
    fact: str
    kind: ResidueKind
    ledger: Ledger
    readings: tuple[Reading, ...]
    #: Where the fact travels in this milestone's measurement, if anywhere.
    carried_by: str
    note: str = ""

    @property
    def attempts(self) -> tuple[EncodingAttempt, ...]:
        return tuple(a for a in ATTEMPTS if a.column == self.column and a.fact == self.fact)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "fact": self.fact,
            "kind": self.kind.value,
            "ledger": self.ledger.value,
            "readings": [r.value for r in self.readings],
            "carried_by": self.carried_by,
            "note": self.note,
            "attempts": [a.to_dict() for a in self.attempts],
        }


RESIDUE: tuple[ResidueItem, ...] = (
    ResidueItem(
        column="col-dc",
        fact="which nodes element R1 connects, in terminal order",
        kind=ResidueKind.SCIENTIFIC_STRUCTURE,
        ledger=Ledger.EXISTING_RECORD,
        readings=(Reading.STRICT, Reading.PLACEMENT),
        carried_by="electrical_dc_circuit/1 — the domain's own existing record",
        note=(
            "Three channels were tried and none carried it as a typed fact: bulk "
            "data refuses a non-numeric payload outright; a boundary condition is "
            "accepted only by putting the second terminal in an opaque 'region' "
            "label while additionally asserting a prescribed voltage the circuit "
            "does not have; categorical parameters fit only by putting the "
            "relation in the spelling of a name. The remedy already exists and is "
            "already round-trippable — what does not exist is anything requiring, "
            "checking or linking it. "
            "LIMIT, recorded: three of the four columns recover their physics by "
            "that same name-spelling convention (a parameter called 'alpha' "
            "becomes ConductionSlab.diffusivity), and no record publishes it. "
            "What distinguishes this column is not that its fact travels in a "
            "name — it is that its fact ALSO travels in a typed, versioned, "
            "schema-checked record, and the others' do not."
        ),
    ),
    ResidueItem(
        column="col-slab",
        fact="non-uniform initial field u(x,0) = sin(pi x / L)",
        kind=ResidueKind.CONDITION,
        ledger=Ledger.ABSENT_RECORD,
        readings=(Reading.STRICT, Reading.PLACEMENT),
        carried_by="nothing — the solver hard-codes it; the label travels as text",
        note=(
            "InitialCondition.value is one Quantity and refuses a sequence. A "
            "ScientificDataReference holds the values and cannot say which "
            "variable they are, which is the VariableToBulkLinkage gap "
            "CROSS-DOMAIN-COVERAGE measured across all four consumers. Booked "
            "Ledger 2 and zero evidence gain: this is a MIN-FOUNDATION-PDE "
            "question already, re-confirmed rather than discovered."
        ),
    ),
    ResidueItem(
        column="col-slab",
        fact="mesh resolution (n_cells, n_steps)",
        kind=ResidueKind.DISCRETIZATION,
        ledger=Ledger.ABSENT_RECORD,
        readings=(Reading.PLACEMENT,),
        carried_by="a residue payload defined by this milestone for measurement only",
        note=(
            "Representable as two IntegerValue parameters, so it is NOT a strict "
            "residue. Placing it there puts the mesh inside the identity of the "
            "physical problem — HOSTILE-CORE-STRESS's ENCODING_B, which it "
            "measured and did not recommend, and which ConductionSlab.fingerprint() "
            "independently refuses by excluding the discretization. Booked "
            "Ledger 2, zero evidence gain: DiscretizationDefinition is already "
            "DEFER."
        ),
    ),
    ResidueItem(
        column="col-cstr",
        fact="integration method, tolerances, evaluation budget, output density",
        kind=ResidueKind.NUMERICAL_SETTING,
        ledger=Ledger.EXISTING_RECORD,
        readings=(Reading.PLACEMENT,),
        carried_by="a residue payload defined by this milestone for measurement only",
        note=(
            "Every one is representable as a typed parameter, so it is NOT a "
            "strict residue. The gap is that SolverSettings — which is the right "
            "record, is typed, and round-trips — is a field of PreparedSolve, "
            "which is runtime-only. A persisted problem therefore cannot carry "
            "the numerical declaration that determines its answer. Ledger 1: the "
            "record exists; what is missing is a persistable reference to it."
        ),
    ),
)


def residue_for(column: str, reading: Reading) -> tuple[ResidueItem, ...]:
    return tuple(i for i in RESIDUE if i.column == column and reading in i.readings)


def table(reading: Reading) -> dict[str, tuple[ResidueItem, ...]]:
    from .encodings import COLUMNS

    return {column: residue_for(column, reading) for column in COLUMNS}


@dataclass(frozen=True)
class Decision:
    """The outcome of applying the preregistered rule to a measured table."""

    rule: str
    outcome: str
    ledger1_columns: tuple[str, ...]
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "outcome": self.outcome,
            "ledger1_columns": list(self.ledger1_columns),
            "detail": self.detail,
        }


#: Preregistration §9, verbatim. Applied mechanically to the measured table so
#: that no human chooses the outcome after seeing the results.
def decide(reading: Reading = Reading.STRICT) -> Decision:
    measured = table(reading)
    ledger1 = tuple(
        column
        for column, items in measured.items()
        if any(i.ledger is Ledger.EXISTING_RECORD for i in items)
    )
    ledger2_only = tuple(
        column
        for column, items in measured.items()
        if items and all(i.ledger is Ledger.ABSENT_RECORD for i in items)
    )
    if not any(measured.values()):
        return Decision(
            rule="empty everywhere",
            outcome="WITHDRAW THE PROPOSAL SET",
            ledger1_columns=(),
            detail="domains under-populate contracts they already have",
        )
    if len(ledger1) == 1:
        return Decision(
            rule="non-empty for exactly one column",
            outcome="NO UNIVERSAL RECORD — E + F",
            ledger1_columns=ledger1,
            detail=(
                f"Ledger-1 residue in {ledger1[0]} only. State the artifact "
                f"contract for the domain that has irreducible structure; reduce "
                f"the others into contracts that already exist. Ledger-2-only "
                f"columns {list(ledger2_only)} are re-confirmations of recorded "
                f"deferrals and claim zero evidence gain"
            ),
        )
    if len(ledger1) >= 2:
        shapes = {
            i.kind
            for column in ledger1
            for i in measured[column]
            if i.ledger is Ledger.EXISTING_RECORD
        }
        if len(shapes) == 1:
            return Decision(
                rule="non-empty for >= 2 columns with the same shape",
                outcome="UNIVERSAL RECORD JUSTIFIED — placement C (sibling)",
                ledger1_columns=ledger1,
                detail=f"shared residue kind: {sorted(s.value for s in shapes)}",
            )
        return Decision(
            rule="non-empty for >= 2 columns with different shapes",
            outcome="NO UNIVERSAL RECORD — per-kind treatment",
            ledger1_columns=ledger1,
            detail=(
                f"residue kinds {sorted(s.value for s in shapes)} do not share a "
                f"shape, so one record would span unrelated axes — the "
                f"RealizationFidelity failure mode"
            ),
        )
    return Decision(
        rule="Ledger-2 residue only",
        outcome="LEDGER 2 — ZERO EVIDENCE GAIN",
        ledger1_columns=(),
        detail=f"columns {list(ledger2_only)} re-confirm recorded deferrals",
    )
