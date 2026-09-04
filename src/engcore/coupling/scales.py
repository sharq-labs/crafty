"""Comparison-unit admissibility for a coupling criterion.

**Domain-neutral coupling infrastructure. Not universal scientific semantics.**
Nothing here knows what any quantity means. The rule is structural — *does zero
of this unit map to zero of its base unit* — and that question has no
dimension: it admits ``rankine`` and refuses ``degC`` by the same arithmetic
that would admit ``pascal`` and refuse a conventional zero anywhere else.

A coupling criterion subtracts two values of a transported quantity and stores
the difference. A difference on an affine scale is not a value of that scale,
so the unit a coupling plan compares in must be a ratio scale. That is the
whole of this module's subject matter.
"""

from __future__ import annotations

from ..scientific.errors import InvalidScientificProblem
from ..scientific.units.quantity import Quantity, registry
from ..scientific.units.validation import require_unit

__all__ = ["is_ratio_scale", "shares_origin"]


def is_ratio_scale(unit: str) -> bool:
    """Does zero of this unit map to zero of its base unit?

    A ratio scale can be subtracted and its difference stored under its own
    unit; an affine scale cannot. The test is structural and carries no
    knowledge of any particular dimension: ``rankine`` passes and ``degC`` does
    not, for the same reason and by the same arithmetic.

    **What this does and does not protect, stated precisely.** The arithmetic
    of the comparison is safe without it: both sides are converted into one unit
    before subtraction, and an affine offset cancels in a difference. What it
    protects is the **stored record**. ``largest_iterate_change`` is a
    *difference* carried in a type that means an *absolute value*, so a
    consumer holding a `4.7e-7 degC` delta and calling ``.to("kelvin")`` on it
    would get `273.15`. Refusing an affine scale for the comparison unit is
    what keeps that record convertible.

    **One provider dependency, recorded rather than hidden.** This reaches past
    the ``Quantity`` contract into the units backend through the units module's
    own ``registry()`` accessor, because the contract publishes no way to name a
    dimension's base unit. A backend without ``get_base_units`` would break this
    function. It is the only such call in this package, this package is
    coupling infrastructure and not universal scientific core, and
    :meth:`~engcore.coupling.FixedPointCouplingPlan.__post_init__` additionally
    applies a pairwise check that uses published contract alone.
    """
    normalized = require_unit(unit, context="coupling comparison unit")
    _, base = registry().get_base_units(normalized)
    return Quantity(0.0, normalized).magnitude_in(str(base)) == 0.0


def shares_origin(unit: str, other: str) -> bool:
    """Do these two compatible units share a zero?

    Published contract only — no units-backend call. It catches the mixed pair
    (a tolerance in kelvin against an edge declared in ``degC``, or the
    reverse), which is the case where a conversion actually happens. It cannot
    catch a wholly affine composition, where every conversion is the identity
    and only the stored label is misleading; :func:`is_ratio_scale` covers that.
    """
    return Quantity(0.0, unit).magnitude_in(other) == 0.0


def _require_ratio_scale(unit: str, *, label: str) -> str:
    normalized = require_unit(unit, context=label)
    if not is_ratio_scale(normalized):
        raise InvalidScientificProblem(
            f"{label} may not use {unit!r}: its zero is conventional, so a "
            f"difference expressed in it is not a value of that unit and does "
            f"not survive conversion. Use a ratio scale, whose zero maps to "
            f"zero in its base unit"
        )
    return normalized
