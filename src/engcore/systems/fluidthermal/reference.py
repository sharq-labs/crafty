"""The closed-form fixed point of the COUPLED system. Verification side only.

`FT-SCALAR-COUPLING`. This is what the executed coupling is checked AGAINST,
so it must not be reachable FROM the thing it verifies. It imports ``math``
and nothing else: not the Fluid solver, not the Thermal solver, not the two
property evaluators of ``properties.py``, not ``run_fixed_point``, not
``Quantity``. A test parses this module and asserts that import list, in the
same voice as ``fluids/transport2d/reference.py``'s own "never imports
solver.py" discipline.

Every physical constant arrives as an explicit argument. Nothing here reads a
module-level declaration that the numerical path also reads, so the two sides
of the comparison cannot silently share an implementation.

**What that does and does not buy, stated precisely because an earlier draft
overclaimed it.** It removes a shared *code path*. It does **not** remove a
shared *value*: a caller that feeds one declared constant to both the system
and this reference — which is exactly what the test module does, from one
frozen table — would move both sides together, so a mistyped ``D_ref`` would
cancel. What actually closes that hole is elsewhere and is worth naming: the
test module pins the reference's absolute output (348.163813 K and
481.835346 K) against the preregistration, which was written before the
implementation existed. And one degeneracy survives even that: ``rho_cp`` and
``d`` appear only as a product, here and in the wall model, so doubling one
and halving the other is undetectable by every check in this milestone.

WHAT IS BEING SOLVED
--------------------
Three declared relations close into one scalar equation:

    Fluid   (exact):  Phi_D(D)  = 8 D                 [m**2/s], per unit depth
    Fluid property :  D(T)      = D_ref (T/T_ref)^n   [m**2/s]
    Scale restore  :  hA(Phi_D) = rho_cp Phi_D d      [W/K]
    Thermal (exact):  T_ss      = T_amb + Q / hA      [K]

Substituting gives the coupled fixed-point condition

    T = T_amb + Q / ( rho_cp d * 8 * D_ref * (T/T_ref)^n )                (1)

and, writing A = rho_cp d * 8 * D_ref for the conductance at T = T_ref,

    (T - T_amb) * (T/T_ref)^n = Q / A                                     (2)

WHY 8 D IS THE EXACT FLUID LEG
------------------------------
The Fluid benchmark's manufactured solution is c*(x,y) = sin(pi x/L)
sin(pi y/L), pinned by an analytically derived source term. On y = 0 the
outward normal is -y, so the outward diffusive efflux density is
-D grad(c*).n = +D (pi/L) sin(pi x/L), whose integral over that side is
exactly 2D. Four sides give 8D — independent of the grid, independent of
omega, exactly linear in D.

HOW THE ROOT IS FOUND, AND WHY THAT MATTERS
-------------------------------------------
By **bisection on the residual of (1)**, which is a different method from the
Picard sweep the coupled loop performs. A reference that converged by the same
iteration as the thing it checks would only be establishing that the iteration
is reproducible. Bisection needs only a sign change and cannot mimic the
loop's fixed point by construction: the residual is strictly decreasing in T
(the left side grows, the right side falls), so the root is unique and
bracketed.

AN INDEPENDENT CHECK OF THE REFERENCE ITSELF
--------------------------------------------
When ``T_amb == T_ref`` (the operating point this milestone runs), (2) reduces
to a closed algebraic identity in theta = T/T_ref:

    theta^(n+1) - theta^n = Q / (A * T_ref)                                (3)

:func:`fixed_point_identity_residual` evaluates (3) directly. It shares no
code path with the bisection, so agreement between the two is evidence about
the reference rather than about one implementation of it.
"""

from __future__ import annotations

import math

__all__ = [
    "EXACT_EFFLUX_PER_DIFFUSIVITY",
    "coupled_fixed_point",
    "coupled_residual",
    "fixed_point_identity_residual",
    "picard_gain",
    "reference_conductance",
]

#: Phi_D / D for this benchmark's manufactured solution, exactly. Four sides,
#: 2D each. A number derived on paper, stated once, never computed from a grid.
EXACT_EFFLUX_PER_DIFFUSIVITY = 8.0

#: Identity of this reference, for provenance. Not a code path.
REFERENCE_ID = "fluidthermal.scalar_coupling.closed_form_fixed_point"
REFERENCE_EXPRESSION = (
    "(T - T_amb) (T/T_ref)^n = Q / (rho_cp d * 8 D_ref)"
)


def reference_conductance(
    *,
    volumetric_heat_capacity: float,
    depth_m: float,
    reference_diffusivity: float,
) -> float:
    """``A = rho_cp * d * 8 * D_ref`` — the coupled conductance at ``T_ref`` [W/K]."""
    return (
        volumetric_heat_capacity
        * depth_m
        * EXACT_EFFLUX_PER_DIFFUSIVITY
        * reference_diffusivity
    )


def coupled_residual(
    temperature_k: float,
    *,
    heat_w: float,
    ambient_k: float,
    reference_diffusivity: float,
    reference_temperature_k: float,
    exponent: float,
    volumetric_heat_capacity: float,
    depth_m: float,
) -> float:
    """``T_amb + Q/(A (T/T_ref)^n) - T`` — zero exactly at the coupled fixed point."""
    if temperature_k <= 0.0:
        raise ValueError(
            f"temperature must be a positive absolute temperature, got "
            f"{temperature_k!r} K"
        )
    conductance = reference_conductance(
        volumetric_heat_capacity=volumetric_heat_capacity,
        depth_m=depth_m,
        reference_diffusivity=reference_diffusivity,
    ) * (temperature_k / reference_temperature_k) ** exponent
    return ambient_k + heat_w / conductance - temperature_k


def coupled_fixed_point(
    *,
    heat_w: float,
    ambient_k: float,
    reference_diffusivity: float,
    reference_temperature_k: float,
    exponent: float,
    volumetric_heat_capacity: float,
    depth_m: float,
    upper_bracket_k: float = 1.0e7,
    iterations: int = 400,
) -> float:
    """The coupled fixed point ``T*``, by bisection on :func:`coupled_residual`.

    Not by iterating the coupled map. See the module docstring: a reference
    that converged by the same iteration as the thing it checks would establish
    only that the iteration is reproducible.
    """
    for label, value in (
        ("heat_w", heat_w),
        ("ambient_k", ambient_k),
        ("reference_diffusivity", reference_diffusivity),
        ("reference_temperature_k", reference_temperature_k),
        ("volumetric_heat_capacity", volumetric_heat_capacity),
        ("depth_m", depth_m),
    ):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{label} must be finite and positive, got {value!r}")
    if not math.isfinite(exponent):
        raise ValueError(f"exponent must be finite, got {exponent!r}")

    def residual(temperature: float) -> float:
        return coupled_residual(
            temperature,
            heat_w=heat_w,
            ambient_k=ambient_k,
            reference_diffusivity=reference_diffusivity,
            reference_temperature_k=reference_temperature_k,
            exponent=exponent,
            volumetric_heat_capacity=volumetric_heat_capacity,
            depth_m=depth_m,
        )

    low, high = ambient_k, upper_bracket_k
    if residual(low) <= 0.0 or residual(high) >= 0.0:
        raise ValueError(
            "the coupled fixed point is not bracketed by "
            f"[{low!r}, {high!r}] K; widen upper_bracket_k or check the "
            "declared constants"
        )
    for _ in range(int(iterations)):
        middle = 0.5 * (low + high)
        if residual(middle) > 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def fixed_point_identity_residual(
    temperature_k: float,
    *,
    heat_w: float,
    reference_diffusivity: float,
    reference_temperature_k: float,
    exponent: float,
    volumetric_heat_capacity: float,
    depth_m: float,
) -> float:
    """``theta^(n+1) - theta^n - Q/(A T_ref)`` — valid only when ``T_amb == T_ref``.

    A second, algebraically independent statement of the same root, sharing no
    code path with the bisection above. Agreement between the two is evidence
    about the reference; agreement of the bisection with itself would not be.
    """
    theta = temperature_k / reference_temperature_k
    conductance = reference_conductance(
        volumetric_heat_capacity=volumetric_heat_capacity,
        depth_m=depth_m,
        reference_diffusivity=reference_diffusivity,
    )
    return (
        theta ** (exponent + 1.0)
        - theta**exponent
        - heat_w / (conductance * reference_temperature_k)
    )


def picard_gain(
    temperature_k: float, *, ambient_k: float, exponent: float
) -> float:
    """``g = -n (T - T_amb)/T`` — the derivative of the coupled map at ``T``.

    Derived once, on paper, from ``g(T) = T_amb + Q/(A (T/T_ref)^n)``:

        ``g'(T) = -n Q / (A T_ref^-n T^(n+1)) = -n (g(T) - T_amb) / T``

    and at a fixed point ``g(T) = T``. ``|g| < 1`` is what an undamped
    Gauss-Seidel sweep needs to contract, and the ratio between successive
    iterate changes is what it should be measured against. Reported, never
    used to damp anything.
    """
    return -exponent * (temperature_k - ambient_k) / temperature_k
