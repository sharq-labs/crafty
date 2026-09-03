"""Errors for the 2D scalar advection-diffusion (transport2d) domain."""

from __future__ import annotations

from ....scientific.errors import ScientificCoreError


class Transport2DError(ScientificCoreError):
    """Base error for the 2D advection-diffusion transport domain."""


class Transport2DConfigurationError(Transport2DError):
    """A domain or discretization was declared with values that cannot be
    solved.

    Raised at construction, not at solve time — a non-square-resolvable
    grid or a non-positive diffusivity is not a hard numerical problem the
    solver should try and fail at; it was never a well-posed statement, and
    the earliest honest place to say so is where it was written down.
    """


class Transport2DBindingError(Transport2DError):
    """A problem id was rebound to a different physical domain."""


# No domain-local admission-refusal error is defined here. The mandatory F8
# proof (see validation.read_centre_concentration_with_admission) refuses a
# result by calling ValidationReport.require_admission(...) directly and
# lets ScientificValidationError propagate unwrapped — the point is to
# exercise the Foundation's actual enforcement primitive as a real
# production caller, not to grow a parallel domain-specific error hierarchy
# around it.
