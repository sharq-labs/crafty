"""Scientific quantity contract.

Design position: we do not reimplement dimensional analysis. Pint owns the
unit algebra; this module owns the *contract* — an immutable, serializable
quantity type that the rest of the Scientific Core depends on, so that the
units backend stays replaceable and never leaks into scientific records.

Invariants:

* a Quantity always carries a unit (``"dimensionless"`` is a unit, not an
  absence of one);
* unit strings are normalized on construction, so serialization is
  deterministic;
* incompatible operations raise :class:`UnitCompatibilityError` — the core
  never silently strips or coerces units;
* **a magnitude is always finite.** NaN and ±Inf are refused here, which is
  what keeps them out of parameters, bounds, tolerances, results,
  uncertainties and provenance without a check in each of those types.

  The one sanctioned home for non-finite numbers is
  :class:`~engcore.scientific.solvers.protocol.RawSolverOutput`: a diverged
  backend must be able to report NaN honestly. The boundary is therefore
  *raw backend output may be non-finite; interpreted science may not*.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Mapping

import pint

from ..errors import UnitCompatibilityError, UnitRegistryFrozen
from ..serialization import require_schema, schema_string

QUANTITY_SCHEMA = schema_string("quantity")

_REGISTRY: pint.UnitRegistry | None = None

#: Fingerprint of the registry's definitional content, taken at seal time.
_SEALED_FINGERPRINT: str | None = None

#: The definition OBJECTS themselves, at seal time.
#:
#: Compared by VALUE, and the reason is measured rather than assumed: pint
#: legitimately *rebinds* an existing name during ordinary lazy expansion —
#: parsing ``kg/m**3`` replaces ``_units['kilogram']`` with a new but
#: value-equal ``UnitDefinition``. Comparing by identity therefore fires on
#: correct arithmetic. A real redefinition is not value-equal (redefining
#: ``millivolt`` changes ``ScaleConverter(scale=0.001)`` to ``scale=1e-06``),
#: so equality separates the two exactly.
#:
#: Holding the objects rather than a rendering of them is only sound because
#: pint's three definition types are frozen dataclasses — an in-place change
#: would otherwise move both sides of the comparison at once. That premise is
#: asserted by the accompanying test, not assumed.
_SEALED_OBJECTS: dict[str, dict[str, Any]] | None = None

#: Name-shape rules identifying an entry point that can change what a unit
#: MEANS. Derived by matching against ``dir(registry)`` rather than written out
#: as a list of method names, so a mutator introduced by a future pint release
#: is sealed the moment it appears instead of the moment somebody remembers it.
#: A guard from a hand-maintained list guards only what someone remembered.
_MUTATOR_PREFIXES = (
    "define",
    "_define",
    "_redefine",
    "load_definitions",
    "_add_",
    "add_",
    "remove_",
    "enable_",
    "disable_",
    "set_",
    "_switch_",
)

#: Members whose names match the shapes above but which change no definition.
#:
#: An over-broad sweep fails LOUDLY — it breaks ordinary arithmetic, which is
#: how ``_add_ref_of_log_or_offset_unit`` was found: sealing it broke every
#: degC and log-unit conversion in the suite. That is the correct direction to
#: be wrong in, and it is why the sweep is a shape rule with named exceptions
#: rather than a list of known mutators. A missed mutator would be silent.
#:
#: Each exception was decided by reading pint's source, not by its name:
#: ``_add_ref_of_log_or_offset_unit`` (pint/facets/nonmultiplicative/registry.py)
#: reads ``self._units[offset_unit]`` and RETURNS a ``UnitsContainer``. The
#: "add" is to that container — a value — not to the registry. It writes
#: nothing.
_NOT_MUTATORS = frozenset({
    "define",  # replaced explicitly below, not by the prefix sweep
    "_add_ref_of_log_or_offset_unit",
})


def _mutator_names(reg: pint.UnitRegistry) -> tuple[str, ...]:
    """Every attribute of ``reg`` whose name has the shape of a mutator."""
    found = []
    for name in dir(reg):
        if not any(name.startswith(p) for p in _MUTATOR_PREFIXES):
            continue
        try:
            if not callable(getattr(reg, name)):
                continue
        except Exception:  # pragma: no cover - defensive: pint lazy attributes
            continue
        found.append(name)
    return tuple(sorted(found))


#: The definitional tables that decide what a unit means.
_DEFINITION_TABLES = ("_units", "_prefixes", "_dimensions")


def _definitions(reg: pint.UnitRegistry) -> dict[str, dict[str, Any]]:
    """``{table: {name: definition object}}`` — the content, not a count.

    A count is blind to the dangerous case: *redefining* an existing unit
    leaves the number of units unchanged and changes every conversion that
    uses it. Measured on pint 0.25.3 — redefining ``millivolt`` turns
    ``1 V -> 1000 mV`` into ``1 V -> 1000000 mV``.
    """
    return {
        table: {str(key): value for key, value in getattr(reg, table, {}).items()}
        for table in _DEFINITION_TABLES
    }


def _digest_of(definitions: Mapping[str, Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for table in _DEFINITION_TABLES:
        digest.update(table.encode("utf-8"))
        entries = definitions.get(table, {})
        for key in sorted(entries):
            digest.update(key.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(repr(entries[key]).encode("utf-8"))
            digest.update(b"\x01")
    return digest.hexdigest()


def units_fingerprint() -> str:
    """Stable digest of the sealed definitional content.

    Taken once, at seal time, over the definitions pint loaded from its own
    files. It does **not** move as a process runs, so it is safe to record in
    provenance: two runs that report the same fingerprint were computed under
    the same unit algebra.
    """
    registry()  # ensure sealed
    assert _SEALED_FINGERPRINT is not None
    return _SEALED_FINGERPRINT


def _seal(reg: pint.UnitRegistry) -> pint.UnitRegistry:
    """Refuse every route by which ``reg``'s definitions could change.

    Sealing is applied to the *instance*, not to a wrapper, because pint hands
    the registry back out: ``registry().Quantity(1, "V")._REGISTRY`` is the
    real object. A proxy would be bypassed by any code holding a quantity — and
    every quantity this module returns held one.
    """

    def _refuse(name: str):
        def refuse(*_args: Any, **_kwargs: Any):
            raise UnitRegistryFrozen(
                f"the Scientific Core unit registry is sealed; "
                f"{name}() would change what a unit means for every "
                f"calculation in this process, including ones that have "
                f"already reported an answer. Units are declared once, at "
                f"import; there is no supported runtime redefinition."
            )
        return refuse

    for name in _mutator_names(reg):
        if name in _NOT_MUTATORS:
            continue
        try:
            object.__setattr__(reg, name, _refuse(name))
        except Exception:  # pragma: no cover - read-only descriptor
            pass
    # `define` is sealed by name rather than by sweep so that the single most
    # important route is never dependent on the shape rule matching.
    object.__setattr__(reg, "define", _refuse("define"))
    return reg


def registry() -> pint.UnitRegistry:
    """The single unit registry owned by the Scientific Core.

    Deliberately *not* pint's application registry: that is process-global and
    mutable by any co-resident library, which would make our dimensional
    guarantees depend on unrelated code.

    **The registry is sealed on construction and never changes afterwards.**
    That is the answer to "two runs share one registry": isolation is only
    needed when state can change, and here it cannot, so a shared registry is
    observationally identical to a per-run one — unit algebra over a fixed
    definition set is a pure function of ``(magnitude, unit string)``. The
    alternative, a fresh registry per run, was measured at **101.8 ms** each
    and buys nothing that sealing does not already give.

    The cost of this choice is real and is stated here rather than discovered
    later: a domain that needs a unit pint does not define cannot add one at
    runtime. It must be declared here, before the seal, where it is reviewable
    and applies to every run identically.
    """
    global _REGISTRY, _SEALED_FINGERPRINT, _SEALED_OBJECTS
    if _REGISTRY is None:
        built = pint.UnitRegistry()
        _SEALED_OBJECTS = _definitions(built)
        _SEALED_FINGERPRINT = _digest_of(_SEALED_OBJECTS)
        _REGISTRY = _seal(built)
    return _REGISTRY


def _unexplained_changes(reg: pint.UnitRegistry) -> tuple[str, ...]:
    """Every difference from the sealed baseline that is not pint's own lazy
    materialization of a prefixed unit.

    pint creates ``millivolt`` in ``_units`` the first time anything asks for
    it, from the sealed prefix ``milli`` and the sealed unit ``volt``. That is
    an expansion of sealed content, not a new definition, and it is the only
    difference an untouched registry ever shows — measured across 22 prefixed
    and symbol forms, every one of which decomposed. Anything that does *not*
    decompose that way was put there by something other than pint's reader.
    """
    assert _SEALED_OBJECTS is not None
    problems: list[str] = []
    for table in _DEFINITION_TABLES:
        sealed = _SEALED_OBJECTS[table]
        now = getattr(reg, table, {})
        for name, definition in sealed.items():
            try:
                current = now[name]
            except KeyError:
                problems.append(f"{table}: {name!r} was removed")
                continue
            # Equality, not identity. pint rebinds `kilogram` with a new but
            # value-equal definition while parsing `kg/m**3`, so identity
            # would fire on correct arithmetic; a real redefinition changes
            # the converter and is not equal. See _SEALED_OBJECTS.
            if current != definition:
                problems.append(f"{table}: {name!r} was redefined")
    prefixes = [p for p in _SEALED_OBJECTS["_prefixes"] if p]
    sealed_units = _SEALED_OBJECTS["_units"]
    for name in set(map(str, getattr(reg, "_units", {}))) - set(sealed_units):
        if not any(
            name.startswith(p) and name[len(p):] in sealed_units for p in prefixes
        ):
            problems.append(f"_units: {name!r} was defined after sealing")
    for table in ("_prefixes", "_dimensions"):
        added = set(map(str, getattr(reg, table, {}))) - set(_SEALED_OBJECTS[table])
        problems.extend(f"{table}: {name!r} was defined after sealing" for name in added)
    return tuple(sorted(problems))


def require_pristine_registry(*, context: str = "") -> None:
    """Refuse to proceed if the registry's definitions have moved.

    :func:`_seal` refuses every *call* that could change a definition. This
    refuses on the *content*, and so does not care how a change arrived — a
    route the shape rule failed to match, a direct write into ``reg._units``, a
    future pint internal. It is the difference between a guard that knows the
    ways in and a guard that knows the answer.

    Called at the execution boundary, this is what makes "two runs in one
    process cannot influence each other's arithmetic" enforced rather than
    hoped: run two is refused before it computes, not audited after it
    reported.
    """
    problems = _unexplained_changes(registry())
    if problems:
        prefix = f"{context}: " if context else ""
        raise UnitRegistryFrozen(
            f"{prefix}the unit registry's definitions changed after it was "
            f"sealed: {'; '.join(problems)}. Every quantity computed in this "
            f"process is now of unknown meaning; this run is refused rather "
            f"than reported."
        )


def normalize_unit(unit: str) -> str:
    """Canonical string form of a unit expression.

    Raises :class:`UnitCompatibilityError` for unparsable input.
    """
    text = str(unit).strip()
    if not text:
        raise UnitCompatibilityError(
            "unit must be a non-empty string; use 'dimensionless' explicitly"
        )
    try:
        return str(registry().Unit(text))
    except Exception as exc:  # pint raises several distinct types
        raise UnitCompatibilityError(f"unparsable unit {unit!r}: {exc}") from exc


def dimensionality(unit: str) -> str:
    """Stable string form of a unit's physical dimensionality."""
    try:
        return str(registry().Unit(normalize_unit(unit)).dimensionality)
    except UnitCompatibilityError:
        raise
    except Exception as exc:
        raise UnitCompatibilityError(
            f"cannot determine dimensionality of {unit!r}: {exc}"
        ) from exc


@dataclass(frozen=True)
class Quantity:
    """A scientific value: magnitude plus unit, never one without the other."""

    magnitude: float
    units: str

    def __post_init__(self) -> None:
        magnitude = float(self.magnitude)
        if not math.isfinite(magnitude):
            raise UnitCompatibilityError(
                f"scientific magnitude must be finite, got {magnitude!r}; "
                f"non-finite values belong in RawSolverOutput diagnostics, "
                f"not in an interpreted scientific quantity"
            )
        object.__setattr__(self, "magnitude", magnitude)
        object.__setattr__(self, "units", normalize_unit(self.units))

    # ---- construction -------------------------------------------------
    @classmethod
    def dimensionless(cls, magnitude: float) -> "Quantity":
        return cls(magnitude, "dimensionless")

    @classmethod
    def parse(cls, text: str) -> "Quantity":
        """Parse ``"12 V"`` style input. Bare numbers are rejected: a
        scientific value without a unit is a contract violation, not a
        dimensionless default."""
        raw = str(text).strip()
        try:
            # A bare numeric literal parses as dimensionless in every units
            # backend; accepting it would silently invent a unit.
            float(raw)
        except ValueError:
            pass
        else:
            raise UnitCompatibilityError(
                f"{raw!r} carries no unit; state one explicitly "
                f"(e.g. '{raw} dimensionless')"
            )
        try:
            parsed = registry().Quantity(raw)
        except Exception as exc:
            raise UnitCompatibilityError(
                f"cannot parse quantity {text!r}: {exc}"
            ) from exc
        return cls(float(parsed.magnitude), str(parsed.units))

    # ---- dimensional interface ----------------------------------------
    @property
    def dimensionality(self) -> str:
        return dimensionality(self.units)

    def is_compatible_with(self, other: "Quantity | str") -> bool:
        target = other.units if isinstance(other, Quantity) else other
        return dimensionality(self.units) == dimensionality(target)

    def require_compatible(self, other: "Quantity | str", *, context: str = "") -> None:
        if not self.is_compatible_with(other):
            target = other.units if isinstance(other, Quantity) else other
            where = f" ({context})" if context else ""
            raise UnitCompatibilityError(
                f"incompatible units{where}: {self.units!r} "
                f"[{self.dimensionality}] vs {target!r} [{dimensionality(target)}]"
            )

    def to(self, unit: str) -> "Quantity":
        """Convert to ``unit``. Raises if dimensionally incompatible."""
        target = normalize_unit(unit)
        self.require_compatible(target, context="conversion")
        converted = registry().Quantity(self.magnitude, self.units).to(target)
        return Quantity(float(converted.magnitude), str(converted.units))

    def magnitude_in(self, unit: str) -> float:
        """Numeric magnitude expressed in ``unit`` — the single sanctioned way
        to hand a scientific value to a numeric kernel."""
        return self.to(unit).magnitude

    # ---- minimal arithmetic -------------------------------------------
    # Enough for constraint checks and adapters; full quantity algebra stays
    # in the backend and is not part of this contract.
    def __add__(self, other: "Quantity") -> "Quantity":
        self.require_compatible(other, context="addition")
        return Quantity(self.magnitude + other.to(self.units).magnitude, self.units)

    def __sub__(self, other: "Quantity") -> "Quantity":
        self.require_compatible(other, context="subtraction")
        return Quantity(self.magnitude - other.to(self.units).magnitude, self.units)

    def __mul__(self, other: "Quantity | float") -> "Quantity":
        if isinstance(other, Quantity):
            product = (
                registry().Quantity(self.magnitude, self.units)
                * registry().Quantity(other.magnitude, other.units)
            )
            return Quantity(float(product.magnitude), str(product.units))
        return Quantity(self.magnitude * float(other), self.units)

    def __truediv__(self, other: "Quantity | float") -> "Quantity":
        if isinstance(other, Quantity):
            ratio = (
                registry().Quantity(self.magnitude, self.units)
                / registry().Quantity(other.magnitude, other.units)
            )
            return Quantity(float(ratio.magnitude), str(ratio.units))
        return Quantity(self.magnitude / float(other), self.units)

    def compare(self, other: "Quantity") -> float:
        """Signed difference in *this* quantity's units (>0 if self larger)."""
        self.require_compatible(other, context="comparison")
        return self.magnitude - other.to(self.units).magnitude

    # ---- serialization -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": QUANTITY_SCHEMA,
            "magnitude": self.magnitude,
            "units": self.units,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Quantity":
        require_schema(payload, QUANTITY_SCHEMA)
        return cls(float(payload["magnitude"]), str(payload["units"]))

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.magnitude} {self.units}"


def coerce_quantity(value: Quantity | float | int | str, unit: str) -> Quantity:
    """Interpret ``value`` in the declared context ``unit``.

    A bare number is accepted only because ``unit`` supplies the missing
    context explicitly; a Quantity is converted and dimension-checked. This is
    the one sanctioned entry point for numeric input, and it never guesses.
    """
    if isinstance(value, Quantity):
        return value.to(unit)
    if isinstance(value, str):
        return Quantity.parse(value).to(unit)
    return Quantity(float(value), unit)
