"""FLUID-THERMAL-PREP probe — standalone, read-only against the shipped domains.

Answers four questions the preparation document could not answer from source
alone. It imports ``engcore`` but modifies nothing, adds no test, is not
collected by pytest, and asserts nothing about ``src/engcore/scientific``.

P1  Are the shipped ``transport2d`` scalar metrics (``c:centre``, ``c:max``,
    ``c:min``) sensitive to the fluid problem's own physical input D?  And if
    they are, is that sensitivity PHYSICS or DISCRETIZATION ERROR?  The exact
    manufactured solution is ``c*(x,y) = sin(pi x/L) sin(pi y/L)``, whose value
    is independent of D everywhere — so any observed D-dependence of these
    metrics is, by construction, entirely numerical.

P2  Is there a scalar reduction of the SAME solved field whose exact value is
    genuinely D-dependent?  Candidate: the boundary-integrated diffusive efflux

        Phi_D = closed-integral over dOmega of D * |grad c . n| dl

    For c* pinned by Dirichlet data, ``Phi_D = 8 D`` exactly (2D per side,
    per unit depth) — real Fickian physics, exactly linear in D, with a known
    closed form to check the discrete value against.

P3  Does the recommended two-way loop contract, and how fast?

        T -> D(T) -> [fluid solve] -> Phi_D -> hA -> [thermal] -> T

P4  How much of the fluid participant's discretization error reaches the
    COUPLED answer?  Compared against the closed-form coupled fixed point
    obtained by substituting the exact ``Phi_D = 8 D``.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from engcore.domains.fluids.transport2d.problem import (  # noqa: E402
    CENTRE_METRIC,
    MAX_METRIC,
    MIN_METRIC,
    Transport2DDomain,
    Transport2DGrid,
    build_transport2d_problem,
)
from engcore.domains.fluids.transport2d.solver import (  # noqa: E402
    Transport2DSolver,
    solve_transport2d,
)
from engcore.scientific.units.quantity import Quantity  # noqa: E402

SIDE_M = 1.0
OMEGA = 1.0
#: Exact boundary-integrated diffusive efflux of c*, divided by D.
#: On y=0: dc*/dy = (pi/L) sin(pi x/L); integrating over x gives 2.
#: Four sides -> 8.  Independent of the grid and of D.
EXACT_PHI_OVER_D = 8.0


def make_domain(diffusivity: float, n: int) -> Transport2DDomain:
    return Transport2DDomain(
        domain_id=f"probe-D{diffusivity:g}-n{n}",
        side=Quantity(SIDE_M, "meter"),
        diffusivity=Quantity(diffusivity, "m**2/s"),
        angular_rate=Quantity(OMEGA, "1/s"),
        grid=Transport2DGrid(n_cells=n),
    )


def raw_field(domain: Transport2DDomain) -> np.ndarray:
    """The solved field, from the solver's own five-stage lifecycle.

    ``ScientificResult`` deliberately does not carry the array (DATA-BOUNDARY0:
    a result NAMES bulk data, it does not contain it), so a reader that wants
    the values must either resolve the ``ScientificDataReference`` through
    ``engcore.data`` or read the pre-interpretation ``RawSolverOutput``. This
    probe does the latter. That the detour exists at all is itself a finding
    — see the preparation document's contract capability map.
    """
    problem = build_transport2d_problem(domain)
    solver = Transport2DSolver()
    solver.bind_domain(domain, problem.problem_id)
    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    return np.asarray(raw.diagnostics["field"], dtype=float)


def wall_diffusive_efflux(domain: Transport2DDomain, field: np.ndarray) -> float:
    """Discrete ``Phi_D`` over the four sides, in the solver's own scheme.

    Cell-centred FV with ghost-cell Dirichlet treatment: the boundary face
    gradient is ``(c_wall - c_cell) / (dx/2)`` with ``c_wall = 0`` on every
    side of this benchmark, and the face measure in 2D per unit depth is
    ``dx``.  So the outward efflux is ``2 * D * sum(c_boundary_cells)``.
    """
    n = domain.grid.n_cells
    dx = domain.dx_m
    c = field.reshape(n, n)  # row i*n + j -> (i=x, j=y), per solver.py
    edge = np.concatenate([c[0, :], c[-1, :], c[:, 0], c[:, -1]])
    return float(np.sum(domain.diffusivity_m2_s * edge / (dx / 2.0) * dx))


# ---------------------------------------------------------------------------
def p1_metric_sensitivity(n: int = 32) -> None:
    print(f"\nP1 — shipped scalar metrics vs D (n={n}); exact c:centre = 1.000"
          f" for EVERY D")
    print(f"{'D [m2/s]':>10} {'c:centre':>14} {'c:max':>14} {'c:min':>14} "
          f"{'err vs exact':>14} {'wall [s]':>9}")
    values = []
    for diffusivity in (0.01, 0.02, 0.05, 0.10, 0.50):
        domain = make_domain(diffusivity, n)
        started = time.perf_counter()
        result = solve_transport2d(
            domain, run_id=f"p1-{diffusivity:g}", cross_check=False
        )
        wall = time.perf_counter() - started
        centre = result.value(CENTRE_METRIC).magnitude
        values.append(centre)
        print(f"{diffusivity:10.3g} {centre:14.9f} "
              f"{result.value(MAX_METRIC).magnitude:14.9f} "
              f"{result.value(MIN_METRIC).magnitude:14.9f} "
              f"{centre - 1.0:14.6f} {wall:9.4f}")
    spread = max(values) - min(values)
    print(f"  observed spread of c:centre over a 50x change in D: {spread:.6f}")
    print(f"  physical spread of the EXACT solution over the same change: 0.0")
    print(f"  => 100% of the observed sensitivity is discretization error.")


def p2_wall_flux(n: int = 32) -> None:
    print(f"\nP2 — boundary-integrated diffusive efflux Phi_D; exact = 8 D")
    print(f"{'D [m2/s]':>10} {'Phi_D [m2/s]':>16} {'Phi_D/D':>12} "
          f"{'exact':>8} {'rel err':>10}   (n={n})")
    for diffusivity in (0.01, 0.02, 0.05, 0.10, 0.50):
        domain = make_domain(diffusivity, n)
        ratio = wall_diffusive_efflux(domain, raw_field(domain)) / diffusivity
        print(f"{diffusivity:10.3g} {ratio * diffusivity:16.9f} {ratio:12.6f} "
              f"{EXACT_PHI_OVER_D:8.3f} "
              f"{(ratio - EXACT_PHI_OVER_D) / EXACT_PHI_OVER_D:10.4f}")
    print("\n  grid convergence of Phi_D/D at D = 0.5 (Pe_cell small):")
    print(f"{'n':>6} {'Phi_D/D':>12} {'rel err':>12} {'wall [s]':>10}")
    for grid_n in (16, 32, 64, 128):
        domain = make_domain(0.5, grid_n)
        started = time.perf_counter()
        ratio = wall_diffusive_efflux(domain, raw_field(domain)) / 0.5
        wall = time.perf_counter() - started
        print(f"{grid_n:6d} {ratio:12.6f} "
              f"{(ratio - EXACT_PHI_OVER_D) / EXACT_PHI_OVER_D:12.4f} "
              f"{wall:10.4f}")


# --- the two property models a real milestone would declare -----------------
D_REF, T_REF = 0.01, 300.0     # m2/s at 300 K
EXPONENT = 1.75                # Fuller-correlation binary gas diffusivity
RHO_CP = 1.2e3                 # J/(m3 K), air near 300 K
DEPTH_M = 1.0e-3               # the depth that restores extensive scale


def diffusivity_of(temperature: float) -> float:
    return D_REF * (temperature / T_REF) ** EXPONENT


def conductance_of(phi: float) -> float:
    """hA [W/K] = rho_cp [J/(m3 K)] * Phi_D [m2/s] * depth [m]."""
    return RHO_CP * phi * DEPTH_M


def closed_form_fixed_point(heat_w: float, ambient_k: float) -> float:
    """The coupled answer with the EXACT Phi_D = 8 D substituted."""
    temperature = ambient_k + 1.0
    for _ in range(20000):
        conductance = conductance_of(EXACT_PHI_OVER_D * diffusivity_of(temperature))
        updated = ambient_k + heat_w / conductance
        temperature += 0.05 * (updated - temperature)   # damped, probe-only
    return temperature


def p3_loop(heat_w: float, n: int = 32, max_iterations: int = 40,
            ambient_k: float = 300.0) -> None:
    print(f"\nP3 — undamped Gauss-Seidel loop, Q = {heat_w} W, n = {n}")
    temperature = ambient_k
    print(f"{'iter':>5} {'T [K]':>12} {'D [m2/s]':>12} {'Phi_D':>11} "
          f"{'hA [W/K]':>11} {'|dT| [K]':>11}")
    started = time.perf_counter()
    for index in range(1, max_iterations + 1):
        diffusivity = diffusivity_of(temperature)
        domain = make_domain(diffusivity, n)
        phi = wall_diffusive_efflux(domain, raw_field(domain))
        conductance = conductance_of(phi)
        updated = ambient_k + heat_w / conductance
        change = abs(updated - temperature)
        if index <= 6 or change < 1e-4 or index == max_iterations:
            print(f"{index:5d} {updated:12.6f} {diffusivity:12.6g} "
                  f"{phi:11.6f} {conductance:11.6f} {change:11.3e}")
        temperature = updated
        if change < 1e-4:
            elapsed = time.perf_counter() - started
            exact = closed_form_fixed_point(heat_w, ambient_k)
            gain = -EXPONENT * (temperature - ambient_k) / temperature
            print(f"  CONVERGED in {index} sweeps, {elapsed:.2f} s")
            print(f"  Picard gain at the fixed point = {gain:+.4f} "
                  f"(|gain| < 1 required)")
            print(f"  coupled T (discrete fluid leg) = {temperature:.6f} K")
            print(f"  coupled T (exact Phi_D = 8D)   = {exact:.6f} K")
            print(f"  coupling-level error inherited from the fluid "
                  f"discretization = {temperature - exact:+.6f} K "
                  f"({(temperature - exact) / (exact - ambient_k) * 100:+.2f}% "
                  f"of the temperature rise)")
            return
    gain = -EXPONENT * (temperature - ambient_k) / max(temperature, 1.0)
    print(f"  ITERATION LIMIT REACHED ({max_iterations}); last |dT| "
          f"= {change:.3e} K, Picard gain ~ {gain:+.4f}")


def p5_orientation(n: int = 32) -> None:
    """Which wall-normal quantity is single-signed, and which is not."""
    from engcore.domains.fluids.transport2d.problem import ALL_SIDES
    from engcore.domains.fluids.transport2d.reference import side_orientation
    from engcore.scientific.ir.orientation import (
        MixedOrientationError,
        classify_sign,
    )

    print("\nP5 — BoundaryOrientation classifiability, per wall-normal quantity")
    domain = make_domain(0.05, n)
    c = raw_field(domain).reshape(n, n)
    edges = {
        "side-west": c[0, :], "side-east": c[-1, :],
        "side-south": c[:, 0], "side-north": c[:, -1],
    }
    for side in ALL_SIDES:
        orientation = side_orientation(
            side, n_cells=n, side_m=SIDE_M, omega_per_s=OMEGA
        )
        samples = list(getattr(orientation, "normal_components", ()) or ())
        try:
            advective = classify_sign(samples, context=side).value
        except MixedOrientationError:
            advective = "REFUSED (mixed)"
        except Exception as exc:  # pragma: no cover - probe only
            advective = f"n/a ({type(exc).__name__})"
        # Diffusive outward flux is -D * (c_wall - c_cell)/(dx/2) with
        # c_wall = 0, so its sign is the sign of the near-wall field.
        try:
            diffusive = classify_sign(
                [float(v) for v in edges[side]], context=side
            ).value
        except MixedOrientationError:
            diffusive = "REFUSED (mixed)"
        print(f"  {side:12s}  advective u.n: {advective:16s}  "
              f"diffusive dc/dn: {diffusive}")


def p6_contract_probes(n: int = 32) -> None:
    """Three executed checks against the composition contracts as they are."""
    from engcore.scientific.composition import (
        QuantityDependency,
        unresolved_inputs,
    )
    from engcore.domains.fluids.transport2d.problem import FIELD_VARIABLE

    print("\nP6 — composition-contract probes (nothing modified)")
    fluid = build_transport2d_problem(make_domain(0.05, n))

    # (a) a PARAMETER as a dependency target
    to_parameter = QuantityDependency(
        source_problem_id="thermal-lumped-probe",
        source_quantity="steady_state_temperature",
        target_problem_id=fluid.problem_id,
        target_quantity="diffusivity",
        unit_exemplar="m**2/s",
    )
    print(f"  (a) target = fluid PARAMETER 'diffusivity': "
          f"check_against -> {to_parameter.check_against(target_problem=fluid)}")

    # (b) can a records-only reader SEE that the fluid needs a supplier?
    print(f"  (b) unresolved_inputs([fluid_problem]) -> "
          f"{unresolved_inputs([fluid])}")

    # (c) the FIELD variable as a dependency endpoint
    field_edge = QuantityDependency(
        source_problem_id=fluid.problem_id,
        source_quantity=FIELD_VARIABLE,
        target_problem_id="thermal-somewhere",
        target_quantity="wall_field",
        unit_exemplar="dimensionless",
    )
    print(f"  (c) source = fluid FIELD variable {FIELD_VARIABLE!r}: "
          f"check_against -> "
          f"{field_edge.check_against(source_problem=fluid)}")
    print("      (an empty tuple here means the field endpoint CHECKS CLEAN "
          "through problem.variables)")


if __name__ == "__main__":
    p1_metric_sensitivity()
    p2_wall_flux()
    p3_loop(heat_w=6.0)     # weak feedback: |gain| small
    p3_loop(heat_w=40.0)    # strong feedback: |gain| near 1
    p5_orientation()
    p6_contract_probes()
