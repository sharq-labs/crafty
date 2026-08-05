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
