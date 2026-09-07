"""Scientific Core error taxonomy.

Deliberately compact. Every error here marks a distinct failure mode that a
caller can reasonably act on; we do not create a class per message.
"""

from __future__ import annotations


class ScientificCoreError(Exception):
    """Base class for every Scientific Core failure."""


class InvalidScientificProblem(ScientificCoreError):
    """A problem/IR object violates its declared invariants."""


class UnitCompatibilityError(ScientificCoreError):
    """Units are unparsable, or dimensionally incompatible where compatibility
    was required. Raised instead of silently dropping or coercing units."""


class ModelNotFoundError(ScientificCoreError):
    """No registered model matches the requested identity."""


class ModelValidityError(ScientificCoreError):
    """A model's validity domain is malformed, or a model was used where its
    validity could not be established."""


class InvalidScientificCapability(ScientificCoreError):
    """A scientific capability identifier is malformed, or a declared
    capability set is self-contradictory."""


class InvalidModelRealization(ScientificCoreError):
    """A computational realization record violates its declared invariants."""


class RealizationNotFoundError(ScientificCoreError):
    """No registered computational realization matches the requested identity.

    Deliberately distinct from :class:`ModelNotFoundError` and
    :class:`SolverNotFoundError`: "the science is unknown to us", "the science
    is known but nothing implements it" and "something implements it but no
    solver can run it" are three different answers, and a future planner must
    be able to tell a user which one it hit."""


class SolverNotFoundError(ScientificCoreError):
    """No registered solver can support the problem."""


class AmbiguousSolverError(ScientificCoreError):
    """More than one solver matches and no selection rule was supplied.
    The core never silently picks one."""


class DuplicateRegistrationError(ScientificCoreError):
    """An identity is already present in a registry."""


class ScientificValidationError(ScientificCoreError):
    """A validation report is malformed, or claims a validation level that was
    not actually established by a passing check."""


class UnitRegistryFrozen(ScientificCoreError):
    """Something tried to change the unit registry's definitions.

    Deliberately its own class rather than a :class:`UnitCompatibilityError`:
    "these two units do not match" is a fact about one calculation, and a
    caller can reasonably handle it. "the meaning of a unit was changed
    underneath a process" is a fact about *every* calculation in that process,
    including ones that already finished, and the only correct handling is to
    stop. See :mod:`engcore.scientific.units.quantity`.
    """
