"""``BoundaryOrientation`` — the smallest record that makes a boundary
condition's role injective onto the physical system it describes.

The measured gap (see ``docs/min-field-support-foundation-prereg.md`` §1 for
the full citation trail, re-confirmed against the real, shipped Fluid domain
in this milestone): reversing a prescribed velocity field leaves every
serialized ``BoundaryCondition`` byte-identical, while flipping which end of
the domain is the inflow. The ``(kind, region, value)`` triple is not
injective onto physical systems. This is **not** a Fluid-specific gap: the
lumped electrical DC domain needed the same distinction — a passive-sign
guard — for a two-terminal element with no continuum topology anywhere in
sight.

What this module deliberately is NOT
-------------------------------------
It is not a topology, not an outward-normal field, not a boundary taxonomy,
and it does not know what "inflow"/"outflow"/"inlet"/"wall" mean — those are
domain vocabulary, exactly as `BoundaryCondition.region` already is. It
states one fact only: relative to a **domain-declared reference direction**
(an opaque label, exactly like ``region`` — the core does not interpret it),
a named boundary condition's positive sense is either the same or the
opposite.

The harder case this module refuses to solve, on purpose
-----------------------------------------------------------
The real Fluid domain's own rotational benchmark proved a sharper fact
(`docs/real-fluid-pde-evidence.md` §5): a single named boundary *region* can
be simultaneously half inflow and half outflow — every side of that
benchmark is. No record that assigns *one* sign to an entire named region
can describe that region honestly, and this module does not pretend
otherwise. :func:`classify_sign` **refuses** — raises
:class:`MixedOrientationError` — when the samples it is given disagree in
sign, rather than picking one side and silently mislabelling the other half.
Closing that case for real would need either a per-position orientation
*function* over the boundary, or the boundary discretized into sub-regions
no coarser than the sign change — both reintroduce the mesh/topology
question this milestone's mission explicitly forbids building. The correct,
evidence-grounded behaviour here is refusal, not a wrong answer and not a
topology.

Why standalone, not a field on ``BoundaryCondition``
-------------------------------------------------------
Exactly the reasoning that kept ``VariableBulkLinkage`` and
``QuantityDependency`` standalone, checked against this record specifically:
``boundary_condition/1`` is schema-pinned with ``require_schema`` an exact
string match, so an added field would move the schema and break every
stored boundary condition a pre-milestone reader holds, for a fact ("what
does positive mean here") that is not intrinsic to the condition's kind or
value — it is a fact about how one domain's own convention relates to it.

Why not spatial, and why it still needs samples to be checked
------------------------------------------------------------------
``classify_sign`` takes a plain sequence of signed numbers and knows nothing
about geometry, meshes or coordinates. A caller supplies whatever signed
quantity its own physics defines as "positive in the reference direction" —
a velocity dotted with an outward normal, a prescribed current direction, a
one-dimensional signed flow rate. The function is exercised in this
milestone against the real Fluid domain's real velocity field
(`fluids/transport2d/reference.py::side_orientation`), not a synthetic
array.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from ..errors import InvalidScientificProblem
from ..serialization import require_schema, schema_string

BOUNDARY_ORIENTATION_SCHEMA = schema_string("boundary_orientation")

__all__ = [
    "BOUNDARY_ORIENTATION_SCHEMA",
    "BoundaryOrientation",
    "MixedOrientationError",
    "OrientationSign",
    "classify_sign",
]


class OrientationSign(str, Enum):
    """Which of two directions a boundary condition's positive sense faces,
    relative to a domain-declared reference. The core assigns no physical
    meaning to either member — a domain's own convention (an outward
    normal, a terminal ordering) supplies that, exactly as it supplies the
    meaning of ``BoundaryCondition.region``."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class MixedOrientationError(InvalidScientificProblem):
    """A sample set disagrees in sign: no single :class:`OrientationSign`
    can honestly describe it. Raised, not swallowed into a default — see
    the module docstring's "harder case" section for why this is the
    correct behaviour rather than a gap to close."""


def classify_sign(
    samples: Sequence[float], *, context: str = ""
) -> OrientationSign:
    """Classify a sequence of signed samples as one :class:`OrientationSign`.

    Refuses — raises :class:`MixedOrientationError` — if the samples
    disagree in sign. This is the load-bearing negative-test instrument:
    a representation that can only assign one sign to an entire region
    must fail loudly on a region whose real physics is not single-signed,
    not silently return an arbitrary answer. Samples exactly equal to zero
    (tangent to the reference direction) are informative of neither sign and
    are ignored for classification, but do not by themselves cause a refusal
    -- only a genuine positive/negative disagreement does.
    """
    if not samples:
        raise InvalidScientificProblem(
            f"{context + ': ' if context else ''}cannot classify orientation "
            "of an empty sample set"
        )
    positive = sum(1 for s in samples if s > 0.0)
    negative = sum(1 for s in samples if s < 0.0)
    if positive and negative:
        raise MixedOrientationError(
            f"{context + ': ' if context else ''}samples disagree in sign "
            f"({positive} positive, {negative} negative, of {len(samples)} "
            f"total) — a single BoundaryOrientation cannot describe a region "
            f"whose real physics is not single-signed; this must be refused, "
            f"not silently classified"
        )
    if positive:
        return OrientationSign.POSITIVE
    if negative:
        return OrientationSign.NEGATIVE
    raise InvalidScientificProblem(
        f"{context + ': ' if context else ''}every sample is exactly zero; "
        "orientation is not classifiable from samples with no signed content"
    )


@dataclass(frozen=True)
class BoundaryOrientation:
    """``boundary_name``'s positive sense is ``sign`` relative to
    ``reference`` — a domain-owned label the core does not interpret.

    Deliberately three fields and nothing spatial. See the module docstring
    for what was tried and rejected before this shape.
    """

    boundary_name: str
    reference: str
    sign: OrientationSign
    description: str = ""

    def __post_init__(self) -> None:
        for label in ("boundary_name", "reference"):
            raw = str(getattr(self, label)).strip()
            if not raw:
                raise InvalidScientificProblem(
                    f"boundary orientation requires a non-empty {label}"
                )
            object.__setattr__(self, label, raw)
        object.__setattr__(self, "sign", OrientationSign(self.sign))
        object.__setattr__(self, "description", str(self.description))

    def check_against(
        self, samples: Sequence[float] | None = None
    ) -> tuple[str, ...]:
        """Issue strings; empty means the declared sign is consistent with
        ``samples``, or no samples were supplied to check against.

        Never raises. The hard-refusal path is :func:`classify_sign` itself,
        used directly by a caller that wants an exception rather than an
        issue list — this method exists for callers that want the softer,
        collect-and-report convention every other ``check_against`` in this
        package uses (:class:`VariableBulkLinkage`,
        ``QuantityDependency``).
        """
        if samples is None:
            return ()
        try:
            observed = classify_sign(
                samples, context=f"boundary {self.boundary_name!r}"
            )
        except MixedOrientationError as exc:
            return (str(exc),)
        if observed is not self.sign:
            return (
                f"boundary {self.boundary_name!r}: declared sign "
                f"{self.sign.value!r} does not match the sign observed in "
                f"the supplied samples ({observed.value!r})",
            )
        return ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BOUNDARY_ORIENTATION_SCHEMA,
            "boundary_name": self.boundary_name,
            "reference": self.reference,
            "sign": self.sign.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BoundaryOrientation":
        require_schema(payload, BOUNDARY_ORIENTATION_SCHEMA)
        return cls(
            boundary_name=payload["boundary_name"],
            reference=payload["reference"],
            sign=OrientationSign(payload["sign"]),
            description=payload.get("description", ""),
        )
