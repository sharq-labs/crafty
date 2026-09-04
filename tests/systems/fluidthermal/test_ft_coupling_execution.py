"""FT-SCALAR-COUPLING — the executed coupling.

Everything here runs the real 2D PDE solver and the real thermal evaluator.
The criteria are preregistered in
``docs/fluid-thermal-scalar-coupling-prereg.md`` §6-§8 and this module is not
free to move them; a divergence is recorded in the evidence document, never
fixed by editing a bound.
"""

from __future__ import annotations

import ast
import json
import math
import pathlib
import subprocess
import sys
import textwrap
import time

import numpy as np
import pytest

from engcore.domains import thermal_lumped as lump
from engcore.domains.fluids import transport2d as fluid
from engcore.domains.fluids.transport2d.reference import c_star
from engcore.domains.fluids.transport2d.solver import (
    Transport2DSolver,
    assemble,
    wall_efflux_per_side,
)
from engcore.scientific.errors import ScientificValidationError
from engcore.scientific.results.validation import (
    ValidationCheck,
    ValidationOutcome,
    ValidationReport,
)
from engcore.scientific.units.quantity import Quantity
from engcore.systems.electrothermal import coupled as et
from engcore.systems import fluidthermal as ft
from engcore.systems.fluidthermal import coupled as ftc
from engcore.systems.fluidthermal import properties as prop

# Same-directory import: pytest's prepend import mode puts this directory on
# sys.path, and the frozen declaration lives in exactly one place so no test
# can quietly retune the system it measures.
from test_ft_coupling_records import (  # noqa: F401
    D_REF,
    DEPTH,
    EXPONENT,
    REFERENCE_CONSTANTS,
    RHO_CP,
    T_AMB,
    T_REF,
    make_system,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def run_case(*, n_cells: int, heat_w: float, max_iterations: int = 40,
             cross_check: bool = True, seed_k: float | None = None):
    system = make_system(n_cells=n_cells, heat_w=heat_w)
    if not cross_check:
        system = ft.FluidThermalSystem(
            slice=ft.FluidSlice(
                slice_id=system.slice.slice_id,
                side=system.slice.side,
                angular_rate=system.slice.angular_rate,
                grid=system.slice.grid,
                cross_check=False,
            ),
            medium=system.medium,
            wall=system.wall,
            body=system.body,
            system_id=system.system_id,
        )
    dependencies = ft.coupled_dependencies(system)
    plan = ft.nominal_plan(
        system,
        dependencies,
        max_iterations=max_iterations,
        seed=None if seed_k is None else Quantity(seed_k, "kelvin"),
    )
    started = time.perf_counter()
    run = ft.run_fluid_thermal_coupling(
        system, plan, run_id=f"ft-{heat_w:g}-{n_cells}"
    )
    return system, run, time.perf_counter() - started


def coupled_temperature(system, run) -> float:
    return run.final_values[
        (system.diffusivity_problem_id, prop.TEMPERATURE)
    ].magnitude_in("kelvin")


def final_efflux_and_diffusivity(system, run) -> tuple[float, float]:
    final = run.final
    phi = final.result_for(system.fluid_problem_id).value(
        fluid.PHI_D_METRIC
    ).magnitude_in("m**2/s")
    diffusivity = final.result_for(system.diffusivity_problem_id).value(
        prop.DIFFUSIVITY_METRIC
    ).magnitude_in("m**2/s")
    return phi, diffusivity


# =====================================================================
# Φ_D is COMPUTED from the solved field — falsifier attack 2
# =====================================================================

def test_the_efflux_reads_the_solved_field_and_changes_when_the_field_changes():
    """If the metric were `8D` in disguise, scaling the field would not move it."""
    system = make_system(n_cells=16)
    domain = system.slice.domain_at(Quantity(D_REF, "m**2/s"))
    prepared = assemble(domain)
    solver = Transport2DSolver()
    solver.bind_domain(domain, system.fluid_problem_id)
    problem = fluid.build_transport2d_problem(
        domain, problem_id=system.fluid_problem_id
    )
    raw = solver.solve(solver.prepare(problem))
    field = np.asarray(raw.diagnostics["field"], dtype=float)

    base = sum(wall_efflux_per_side(prepared, field).values())
    doubled = sum(wall_efflux_per_side(prepared, 2.0 * field).values())
    zeroed = sum(wall_efflux_per_side(prepared, 0.0 * field).values())
    # D * sum(c_cell - c_ghost): strictly linear in the solved field, plus a
    # field-independent offset from the Dirichlet ghost data. Both terms are
    # real physics of the shipped stencil; the field term is the one a `8D`
    # implementation could not have, and it is 24% of the total here.
    assert doubled - base == pytest.approx(base - zeroed, rel=1e-12)
    assert abs(base - zeroed) > 0.15 * abs(base)

    # Sharper still: nudge ONE boundary cell and the reported efflux moves by
    # exactly D times that nudge, because the reduction reads that cell.
    row = prepared.boundary_faces[0][0]
    nudged = field.copy()
    nudged[row] += 1.0
    moved = sum(wall_efflux_per_side(prepared, nudged).values())
    corner_faces = sum(1 for r, _, _ in prepared.boundary_faces if r == row)
    assert moved - base == pytest.approx(
        corner_faces * domain.diffusivity_m2_s, rel=1e-12
    )


def test_the_efflux_matches_an_independent_re_derivation_from_geometry():
    """Recomputed in the test from the Dirichlet data and the cell geometry,
    without touching the assembly's recorded boundary faces."""
    system = make_system(n_cells=16)
    domain = system.slice.domain_at(Quantity(0.05, "m**2/s"))
    prepared = assemble(domain)
    solver = Transport2DSolver()
    solver.bind_domain(domain, system.fluid_problem_id)
    problem = fluid.build_transport2d_problem(
        domain, problem_id=system.fluid_problem_id
    )
    raw = solver.solve(solver.prepare(problem))
    field = np.asarray(raw.diagnostics["field"], dtype=float)

    n, dx, diffusivity = domain.grid.n_cells, domain.dx_m, domain.diffusivity_m2_s
    side_m = domain.side_m
    grid = field.reshape(n, n)
    centres = (np.arange(n) + 0.5) * dx
    expected = 0.0
    for index in range(n):
        coordinate = centres[index]
        expected += diffusivity * (
            grid[0, index] - c_star(-0.5 * dx, coordinate, side_m=side_m)
        )
        expected += diffusivity * (
            grid[-1, index] - c_star((n + 0.5) * dx, coordinate, side_m=side_m)
        )
        expected += diffusivity * (
            grid[index, 0] - c_star(coordinate, -0.5 * dx, side_m=side_m)
        )
        expected += diffusivity * (
            grid[index, -1] - c_star(coordinate, (n + 0.5) * dx, side_m=side_m)
        )
    assert sum(wall_efflux_per_side(prepared, field).values()) == pytest.approx(
        expected, rel=1e-12
    )


def test_the_efflux_is_never_exactly_8D_and_converges_to_it():
    """PC3. An implementation that used the closed form would be exact at
    every grid; this one is wrong by a first-order discretization error that
    halves under refinement."""
    errors = {}
    for n_cells in (16, 32, 64):
        system = make_system(n_cells=n_cells)
        result = fluid.solve_transport2d(
            system.slice.domain_at(Quantity(D_REF, "m**2/s")),
            run_id=f"phi-{n_cells}",
        )
        phi = result.value(fluid.PHI_D_METRIC).magnitude_in("m**2/s")
        errors[n_cells] = phi / (8.0 * D_REF) - 1.0
        assert phi != pytest.approx(8.0 * D_REF, rel=1e-6)
    assert errors[16] < errors[32] < errors[64] < 0.0
    for coarse, fine in ((16, 32), (32, 64)):
        assert 1.6 <= errors[coarse] / errors[fine] <= 2.4


# =====================================================================
# N1 — the executed half of the c:centre falsification
# =====================================================================

def test_n1_the_computed_centre_metric_moves_although_the_exact_value_cannot():
    """100% of ``c:centre``'s apparent sensitivity to D is discretization error.

    The exact manufactured solution's centre value is 1.0 for every D (proved
    in the records module). The computed one is not, and it is not by a lot.
    A coupling closed on it would be smooth, monotone, strongly
    input-sensitive, would converge — and would transport nothing but
    numerical error. This test exists so that a future author who wires
    ``c:centre`` into a composition has to read this comment.
    """
    observed = {}
    for diffusivity in (0.01, 0.02, 0.05, 0.10, 0.50):
        result = fluid.solve_transport2d(
            make_system(n_cells=32).slice.domain_at(
                Quantity(diffusivity, "m**2/s")
            ),
            run_id=f"centre-{diffusivity:g}",
            cross_check=False,
        )
        observed[diffusivity] = result.value(
            fluid.CENTRE_METRIC
        ).magnitude_in("dimensionless")
    spread = max(observed.values()) - min(observed.values())
    assert spread == pytest.approx(0.1614, abs=5e-3)
    # Every one of them is below the exact value, and by a margin far larger
    # than the coupling tolerance this milestone runs at (1e-4 K on a ~50 K
    # temperature rise).
    assert all(value < 1.0 for value in observed.values())
    exact_spread = 0.0
    assert spread > 100.0 * max(exact_spread, 1e-9)


def test_n1_the_efflux_by_contrast_carries_real_physical_sensitivity():
    """The contrast that justifies the choice, measured on the same solves."""
    ratios = {}
    for diffusivity in (0.01, 0.50):
        result = fluid.solve_transport2d(
            make_system(n_cells=32).slice.domain_at(
                Quantity(diffusivity, "m**2/s")
            ),
            run_id=f"phi-sens-{diffusivity:g}",
            cross_check=False,
        )
        ratios[diffusivity] = result.value(
            fluid.PHI_D_METRIC
        ).magnitude_in("m**2/s")
    # The EXACT value changes by exactly 50x over this range; the computed one
    # changes by a comparable factor. Its sensitivity is physics, not error.
    assert ratios[0.50] / ratios[0.01] == pytest.approx(50.0, rel=0.3)


# =====================================================================
# Case A — the nominal convergent operating point
# =====================================================================

def test_case_a_the_loop_converges_and_lands_on_the_preregistered_value():
    system, run, wall = run_case(n_cells=32, heat_w=6.0)
    assert run.outcome is et.CouplingOutcome.CRITERION_MET
    assert run.iterations_run == 13
    temperature = coupled_temperature(system, run)
    assert temperature == pytest.approx(355.7, abs=1.0)
    assert run.final_iterate_change.magnitude_in("kelvin") <= 1e-4


def test_case_a_pc1_as_preregistered_is_an_identity_and_cannot_fail():
    """PC1, executed exactly as preregistered — and reported as what it is.

    ``architecture-falsifier`` landed this as finding C-1 and it is right. PC1
    compares the reported temperature against the coupled relation formed from
    the efflux of the SAME sweep. Within one Gauss-Seidel sweep the order is
    diffusivity -> fluid -> wall -> thermal, so the thermal evaluation consumes
    exactly that efflux and the two sides are one closed form evaluated twice.
    The residual is round-off by construction, for any run, converged or not.

    The criterion is preregistered and immutable, so it is executed and
    reported rather than edited — and the next test states the non-trivial
    claim PC1 was meant to make. Recorded as a preregistration divergence in
    the evidence document, section G.
    """
    system, run, _ = run_case(n_cells=32, heat_w=6.0)
    temperature = coupled_temperature(system, run)
    phi, _ = final_efflux_and_diffusivity(system, run)
    predicted = T_AMB + 6.0 / (RHO_CP * DEPTH * phi)
    assert abs(temperature - predicted) <= 1e-3

    # The demonstration that it cannot fail: one sweep, nowhere near the fixed
    # point, an outcome of ITERATION_LIMIT_REACHED — and PC1 still passes.
    one_sweep_system, one_sweep, _ = run_case(
        n_cells=16, heat_w=6.0, max_iterations=1
    )
    assert one_sweep.outcome is et.CouplingOutcome.ITERATION_LIMIT_REACHED
    unconverged = coupled_temperature(one_sweep_system, one_sweep)
    phi1, _ = final_efflux_and_diffusivity(one_sweep_system, one_sweep)
    assert abs(unconverged - (T_AMB + 6.0 / (RHO_CP * DEPTH * phi1))) <= 1e-3
    # …and it is 45 K away from where the loop eventually settles.
    assert abs(unconverged - coupled_temperature(system, run)) > 20.0


def test_case_a_pc1_prime_the_fixed_point_residual_across_two_sweeps():
    """The claim PC1 was meant to make, stated so it CAN fail.

    A fixed point is a statement relating two consecutive sweeps, not one. The
    coupled relation is therefore formed from the PREVIOUS sweep's efflux and
    compared against the final temperature: that residual is zero only when the
    iteration has actually stopped moving, and the one-sweep control below
    shows it is large when it has not.
    """
    system, run, _ = run_case(n_cells=32, heat_w=6.0)
    assert run.outcome is et.CouplingOutcome.CRITERION_MET
    final_t = coupled_temperature(system, run)
    previous = run.iterations[-2]
    previous_phi = previous.result_for(system.fluid_problem_id).value(
        fluid.PHI_D_METRIC
    ).magnitude_in("m**2/s")
    residual = abs(final_t - (T_AMB + 6.0 / (RHO_CP * DEPTH * previous_phi)))
    tolerance = run.plan.absolute_tolerance.magnitude_in("kelvin")
    assert residual <= tolerance

    # The control: the same residual on a deliberately truncated run is orders
    # of magnitude larger, so the criterion above is doing real work. (Case B
    # at its full 40-sweep budget gives ~82x the tolerance — already a clear
    # failure of PC1', and a measure of how close to converged it is.)
    system_b, run_b, _ = run_case(n_cells=16, heat_w=40.0, max_iterations=4)
    assert run_b.outcome is et.CouplingOutcome.ITERATION_LIMIT_REACHED
    final_b = coupled_temperature(system_b, run_b)
    previous_b = run_b.iterations[-2].result_for(
        system_b.fluid_problem_id
    ).value(fluid.PHI_D_METRIC).magnitude_in("m**2/s")
    residual_b = abs(final_b - (T_AMB + 40.0 / (RHO_CP * DEPTH * previous_b)))
    assert residual_b > 1000.0 * tolerance

    system_c, run_c, _ = run_case(n_cells=32, heat_w=40.0)
    final_c = coupled_temperature(system_c, run_c)
    previous_c = run_c.iterations[-2].result_for(
        system_c.fluid_problem_id
    ).value(fluid.PHI_D_METRIC).magnitude_in("m**2/s")
    residual_c = abs(final_c - (T_AMB + 40.0 / (RHO_CP * DEPTH * previous_c)))
    assert residual_c > 50.0 * tolerance


def test_case_a_pc2_agreement_with_the_independent_closed_form_at_n32():
    system, run, _ = run_case(n_cells=32, heat_w=6.0)
    exact = ft.coupled_fixed_point(heat_w=6.0, **REFERENCE_CONSTANTS)
    assert abs(coupled_temperature(system, run) - exact) <= 11.0


def test_case_a_the_answer_does_not_depend_on_the_posing_conductance():
    """``posing_conductance`` poses a record; it is not physics."""
    base_system, base_run, _ = run_case(n_cells=16, heat_w=6.0)
    other = ft.FluidThermalSystem(
        slice=base_system.slice,
        medium=base_system.medium,
        wall=base_system.wall,
        body=ft.HeatedBody(
            body_id=base_system.body.body_id,
            heat_capacity=base_system.body.heat_capacity,
            ambient_temperature=base_system.body.ambient_temperature,
            initial_temperature=base_system.body.initial_temperature,
            duration=base_system.body.duration,
            heat_input=base_system.body.heat_input,
            posing_conductance=Quantity(37.0, "watt/kelvin"),
        ),
        system_id=base_system.system_id,
    )
    dependencies = ft.coupled_dependencies(other)
    run = ft.run_fluid_thermal_coupling(
        other, ft.nominal_plan(other, dependencies), run_id="posing"
    )
    assert coupled_temperature(other, run) == pytest.approx(
        coupled_temperature(base_system, base_run), abs=1e-3
    )


def test_case_a_the_answer_does_not_depend_on_the_seed():
    """A fixed point is a property of the system, not of where iteration began."""
    system_a, run_a, _ = run_case(n_cells=16, heat_w=6.0)
    system_b, run_b, _ = run_case(n_cells=16, heat_w=6.0, seed_k=450.0)
    assert run_b.outcome is et.CouplingOutcome.CRITERION_MET
    assert coupled_temperature(system_b, run_b) == pytest.approx(
        coupled_temperature(system_a, run_a), abs=1e-3
    )
    # …but the PATH is different, so the seed genuinely did something: the
    # first sweep starts from a different temperature and therefore a
    # different diffusivity.
    first_a = run_a.iterations[0].result_for(
        system_a.diffusivity_problem_id
    ).value(prop.DIFFUSIVITY_METRIC).magnitude_in("m**2/s")
    first_b = run_b.iterations[0].result_for(
        system_b.diffusivity_problem_id
    ).value(prop.DIFFUSIVITY_METRIC).magnitude_in("m**2/s")
    assert first_b > 1.5 * first_a


# =====================================================================
# PC2 / PC4 — the refinement arm against the independent reference
# =====================================================================

def test_pc2_the_coupled_error_falls_at_the_participants_own_order():
    exact = ft.coupled_fixed_point(heat_w=6.0, **REFERENCE_CONSTANTS)
    errors = {}
    for n_cells in (16, 32, 64):
        system, run, _ = run_case(n_cells=n_cells, heat_w=6.0)
        assert run.outcome is et.CouplingOutcome.CRITERION_MET
        assert run.iterations_run <= 25
        errors[n_cells] = coupled_temperature(system, run) - exact

    assert errors[16] <= 20.0
    assert errors[32] <= 11.0
    assert errors[64] <= 6.0
    assert errors[16] > errors[32] > errors[64] > 0.0
    for coarse, fine in ((16, 32), (32, 64)):
        assert 1.6 <= errors[coarse] / errors[fine] <= 2.4


def test_pc4_the_coupled_error_is_the_participants_flux_error_transported():
    """The coupling created no error of its own — it inherited one, exactly.

    A relative flux error ``eps`` acts on the coupled map exactly as replacing
    ``Q`` by ``Q/(1+eps)``, because ``hA`` enters only as a product with the
    efflux. So the coupled answer with the discrete flux must be the
    closed-form fixed point AT THAT EFFECTIVE HEAT — an exact prediction, not a
    linearization, and it uses the independent reference module on both sides.
    """
    for n_cells in (16, 32, 64):
        system, run, _ = run_case(n_cells=n_cells, heat_w=6.0)
        phi, diffusivity = final_efflux_and_diffusivity(system, run)
        epsilon = phi / (8.0 * diffusivity) - 1.0
        predicted = ft.coupled_fixed_point(
            heat_w=6.0 / (1.0 + epsilon), **REFERENCE_CONSTANTS
        )
        assert coupled_temperature(system, run) == pytest.approx(
            predicted, rel=1e-4
        )


def test_the_exact_coupled_answer_contains_no_advective_physics_at_all():
    """Falsifier finding C-2, measured. The scope of what was proven.

    The Fluid participant's manufactured source absorbs both ``D`` and
    ``omega``, so its exact solution — and therefore the exact wall efflux
    ``8D`` — is independent of the velocity field. The closed-form coupled
    fixed point contains no ``omega`` term anywhere. So at the EXACT level the
    PDE participant of this composition is the map ``D -> 8D``, and everything
    the executed loop reports about the advective physics is discretization
    error.

    That is the ``c:centre`` lesson (N1) recurring one level up, and it is
    recorded here rather than discovered later. What survives it is real and is
    the reason ``phi_D:wall`` was chosen: its ``D``-dependence is exact
    physics, and ``D`` is the only thing the thermal side actually varies.

    The one genuinely reassuring half: the operating points where the
    advective error would dominate are **refused**, not silently transported.
    """
    exact = ft.coupled_fixed_point(heat_w=6.0, **REFERENCE_CONSTANTS)

    def system_at(omega: float, n_cells: int):
        base = make_system(n_cells=n_cells, heat_w=6.0)
        return ft.FluidThermalSystem(
            slice=ft.FluidSlice(
                slice_id=base.slice.slice_id,
                side=base.slice.side,
                angular_rate=Quantity(omega, "1/s"),
                grid=base.slice.grid,
            ),
            medium=base.medium,
            wall=base.wall,
            body=base.body,
            system_id=base.system_id,
        )

    executed = {}
    for omega in (0.1, 1.0):
        system = system_at(omega, 32)
        run = ft.run_fluid_thermal_coupling(
            system,
            ft.nominal_plan(system, ft.coupled_dependencies(system)),
            run_id=f"omega-{omega:g}",
        )
        executed[omega] = coupled_temperature(system, run) - exact

    # A 10x change in the advective physics moves the EXECUTED answer by ~6.7 K
    # while the EXACT answer does not move at all.
    assert executed[0.1] == pytest.approx(0.81, abs=0.2)
    assert executed[1.0] == pytest.approx(7.50, abs=0.5)
    assert executed[1.0] - executed[0.1] > 5.0

    # And at 100x, the fluid participant leaves its own declared admissibility
    # and the coupling REFUSES rather than transporting the error.
    system = system_at(100.0, 32)
    with pytest.raises(ScientificValidationError, match="admission refused"):
        ft.run_fluid_thermal_coupling(
            system,
            ft.nominal_plan(system, ft.coupled_dependencies(system)),
            run_id="omega-100",
        )


# =====================================================================
# Case B — coupling non-convergence with both subsolvers valid
# =====================================================================

def test_case_b_the_strong_feedback_point_does_not_converge_undamped():
    system, run, _ = run_case(n_cells=32, heat_w=40.0)
    assert run.outcome is et.CouplingOutcome.ITERATION_LIMIT_REACHED
    assert run.iterations_run == 40
    last = run.final_iterate_change.magnitude_in("kelvin")
    assert 1e-3 < last < 5e-2


def test_case_b_is_not_a_solver_failure_every_subsolve_succeeded():
    """The distinction the whole milestone rests on.

    Coupling non-convergence and sub-solver failure are different findings.
    Here every fluid solve converged, every closed-form evaluation reported
    ``NOT_APPLICABLE`` (which is success, not failure), and every result passed
    the requirements its own problem declared — in all forty sweeps of a run
    that did not converge at all.
    """
    system, run, _ = run_case(n_cells=32, heat_w=40.0)
    assert run.outcome is et.CouplingOutcome.ITERATION_LIMIT_REACHED
    for iteration in run.iterations:
        for result in iteration.results:
            assert result.is_usable, (iteration.index, result.problem_id)
        fluid_result = iteration.result_for(system.fluid_problem_id)
        assert fluid_result.convergence.value == "converged"
        problem = ft.coupled_problems(system)[1]
        assert fluid_result.validation.is_admissible(
            problem.validation_requirements
        )


def test_case_b_the_iterate_contracts_geometrically_at_the_picard_gain():
    """Why it did not converge, measured rather than asserted.

    An undamped Gauss-Seidel sweep contracts at |g|, the derivative of the
    coupled map at its fixed point. Here |g| ~ 0.66 by the closed form, so
    each sweep removes only about a third of the remaining error and forty of
    them are not enough for a 1e-4 K criterion on a 180 K rise.
    """
    system, run, _ = run_case(n_cells=32, heat_w=40.0)
    changes = [c.magnitude_in("kelvin") for c in run.iterate_changes]
    ratios = [
        changes[i + 1] / changes[i]
        for i in range(len(changes) - 6, len(changes) - 1)
    ]
    exact = ft.coupled_fixed_point(heat_w=40.0, **REFERENCE_CONSTANTS)
    gain = abs(ft.picard_gain(exact, ambient_k=T_AMB, exponent=EXPONENT))
    assert all(0.5 < r < 0.95 for r in ratios), ratios
    assert sum(ratios) / len(ratios) == pytest.approx(gain, abs=0.15)


def test_case_b_diagnostic_the_budget_was_exhausted_not_the_contraction():
    """SPIKE, required by ``architecture-decision-reviewer`` after case B.

    Case B is preregistered at a 40-sweep budget and is reported exactly as it
    executed: ``ITERATION_LIMIT_REACHED``. This is a **separate, additional**
    diagnostic case that changes ``max_iterations`` and nothing else — no
    relaxation, no damping, no tolerance change — to answer one question the
    preregistered case cannot: was the map contracting, or genuinely
    non-convergent?

    **Answer: contracting.** The same criterion is met at sweep 56. So the
    existing typed ``max_iterations`` field already expresses the whole
    situation, no execution concept is missing, and relaxation is **not forced
    by any executed evidence**. That is the reviewer's stopping condition (i),
    and it is why no relaxation factor was added.

    It also measures something the closed form does not predict: the observed
    contraction ratio is ~0.756, not the exact-fixed-point gain of 0.660. The
    difference is real and is a property of the DISCRETE map — the fluid's
    flux error is itself a function of D, so the discrete efflux grows slightly
    faster than linearly in D and the effective exponent exceeds 1.75. The
    coupled loop contracts more slowly than the exact physics would.
    """
    system = make_system(n_cells=32, heat_w=40.0)
    plan = ft.nominal_plan(
        system, ft.coupled_dependencies(system), max_iterations=200
    )
    run = ft.run_fluid_thermal_coupling(system, plan, run_id="ft-spike-b-200")
    assert run.outcome is et.CouplingOutcome.CRITERION_MET
    assert 40 < run.iterations_run <= 80
    exact = ft.coupled_fixed_point(heat_w=40.0, **REFERENCE_CONSTANTS)
    assert coupled_temperature(system, run) - exact == pytest.approx(
        12.16, abs=0.5
    )
    changes = [c.magnitude_in("kelvin") for c in run.iterate_changes]
    ratios = [changes[i + 1] / changes[i] for i in range(-6, -1)]
    assert all(r == pytest.approx(0.756, abs=0.02) for r in ratios), ratios
    gain = abs(ft.picard_gain(exact, ambient_k=T_AMB, exponent=EXPONENT))
    assert sum(ratios) / len(ratios) > gain


def test_case_b_no_relaxation_factor_exists_anywhere_to_reach_for():
    """§10 fail condition 2, made structural.

    ``FixedPointCouplingPlan`` carries no relaxation field, and this pack adds
    none. There is nothing to tune, which is the strongest form of "it was not
    tuned".
    """
    assert set(et.FixedPointCouplingPlan.__dataclass_fields__) == {
        "plan_id", "dependencies", "torn", "absolute_tolerance",
        "max_iterations",
    }
    for module in ("coupled.py", "properties.py", "reference.py"):
        source = (
            REPO_ROOT / "src/engcore/systems/fluidthermal" / module
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            target.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            for target in (node,)
        }
        for forbidden in ("relaxation", "damping", "omega_relax", "under_relax"):
            assert forbidden not in names


# =====================================================================
# Case C — admission failure is a deterministic refusal
# =====================================================================

def test_case_c_an_inadmissible_fluid_result_stops_the_coupling():
    """Fluid → Thermal admission, proven end to end on a REAL failure.

    At n = 8 this benchmark's own ``admissibility_bound`` fails: the peak cell
    Péclet number is ~6.8 and the first-order upwind field leaves the analytic
    range [0, 1]. The guarded reader raises, ``run_fixed_point`` does not catch
    it, and no coupled result is produced. There is no path on which the value
    is logged, defaulted, retried or skipped.
    """
    with pytest.raises(ScientificValidationError, match="admission refused"):
        run_case(n_cells=8, heat_w=6.0)


def test_case_c_the_unguarded_read_would_have_consumed_it(capfd):
    """The guard is load-bearing, demonstrated rather than asserted."""
    system = make_system(n_cells=8)
    domain = system.slice.domain_at(Quantity(D_REF, "m**2/s"))
    problem = fluid.build_transport2d_problem(
        domain, problem_id=system.fluid_problem_id
    )
    result = fluid.solve_transport2d(domain, run_id="unguarded", problem=problem)
    assert not result.validation.is_admissible(problem.validation_requirements)

    # No guard: a number comes back, and nothing says it should not be used.
    unguarded = fluid.read_wall_efflux_unguarded(problem, result)
    assert unguarded.magnitude_in("m**2/s") > 0.0

    # Guard: refusal.
    with pytest.raises(ScientificValidationError):
        fluid.read_wall_efflux_with_admission(problem, result)


def test_a_requirement_that_did_not_run_is_not_a_satisfied_requirement():
    """A second real refusal, from a different cause than case C.

    With the cross-check solve switched off, ``sparse_dense_assembly_agreement``
    is ``NOT_RUN``. The problem declares it, so the result is inadmissible —
    "we did not check" is not "it passed", and the coupling stops.
    """
    with pytest.raises(ScientificValidationError, match="not_run"):
        run_case(n_cells=16, heat_w=6.0, cross_check=False)


def test_the_thermal_direction_refuses_at_the_guard(monkeypatch):
    """Thermal → Fluid admission, proven end to end by fault injection.

    No declaration of this thermal participant can be made to fail its own
    balance residual — the closed form satisfies the equation it was derived
    from, always — so the failing report is injected. What is being tested is
    the coupling's response to a failing thermal validation, not the
    thermal solver's arithmetic.
    """
    failing = ValidationReport(
        checks=(
            ValidationCheck(
                name="lumped_balance_residual",
                outcome=ValidationOutcome.FAIL,
                detail="injected failure",
            ),
        )
    )
    monkeypatch.setattr(
        lump.LumpedThermalSolver, "validate", lambda self, p, r: failing
    )
    with pytest.raises(ScientificValidationError, match="admission refused"):
        run_case(n_cells=16, heat_w=6.0)


def test_the_thermal_admission_requirement_is_consumer_declared_and_says_so():
    """The measured asymmetry between the two participants.

    ``fluids/transport2d`` publishes its own ``validation_requirements`` on its
    problem record. ``thermal_lumped`` publishes none, so this consumer has to
    name what it demands — weaker evidence than a producer-published
    requirement, and recorded as such rather than hidden behind a
    uniform-looking call.
    """
    system = make_system()
    problems = {p.problem_id: p for p in ft.coupled_problems(system)}
    assert problems[system.thermal_problem_id].validation_requirements == frozenset()
    assert problems[system.fluid_problem_id].validation_requirements
    assert ftc.THERMAL_ADMISSION_REQUIREMENTS == frozenset(
        {"lumped_balance_residual"}
    )


# =====================================================================
# Provenance
# =====================================================================

def test_the_coupled_record_reconstructs_every_participant_and_every_exchange():
    system, run, _ = run_case(n_cells=16, heat_w=6.0)
    payload = json.loads(json.dumps(run.to_dict()))
    restored = et.CoupledRun.from_dict(payload)

    # The four exchange identities, with their units, from the plan alone.
    edges = {
        (d.source_problem_id, d.source_quantity,
         d.target_problem_id, d.target_quantity)
        for d in restored.plan.dependencies
    }
    assert edges == {
        (system.fluid_problem_id, fluid.PHI_D_METRIC,
         system.wall_problem_id, prop.WALL_EFFLUX),
        (system.wall_problem_id, prop.WALL_CONDUCTANCE_METRIC,
         system.thermal_problem_id, lump.AMBIENT_CONDUCTANCE),
        (system.thermal_problem_id, lump.STEADY_STATE_TEMPERATURE_METRIC,
         system.diffusivity_problem_id, prop.TEMPERATURE),
        (system.diffusivity_problem_id, prop.DIFFUSIVITY_METRIC,
         system.fluid_problem_id, "diffusivity"),
    }
    # The outcome and the sweep count.
    assert restored.outcome is run.outcome
    assert restored.iterations_run == run.iterations_run

    # Every participant's model, realization and solver, from the run's own
    # provenance bindings.
    models = {b.model.model_id for b in restored.provenance.bindings}
    assert models == {
        "fluids.transport2d.advection_diffusion",
        "fluids.material.power_law_gas_diffusivity",
        "fluids.thermal.wall_efflux_conductance",
        "thermal.lumped.first_order_capacity",
    }
    solvers = {b.solver.solver_id for b in restored.provenance.bindings}
    assert "fluids.transport2d.upwind_central_scipy_sparse" in solvers
    assert "engcore.thermal.lumped_closed_form" in solvers

    # And each participant's typed inputs, from its own result's provenance.
    fluid_result = restored.final.result_for(system.fluid_problem_id)
    assert "diffusivity" in fluid_result.provenance.inputs
    thermal_result = restored.final.result_for(system.thermal_problem_id)
    assert lump.HEAT_INPUT in thermal_result.provenance.inputs


def test_no_provider_string_became_a_scientific_fact():
    system, run, _ = run_case(n_cells=16, heat_w=6.0)
    fluid_result = run.final.result_for(system.fluid_problem_id)
    assert "scipy" in fluid_result.solver.backend
    for model_id, _ in fluid_result.models:
        assert "scipy" not in model_id and "numpy" not in model_id
    for assumption in fluid_result.assumptions:
        assert "scipy" not in assumption and "numpy" not in assumption


def test_the_thermal_record_now_states_the_imposed_heat_it_was_solved_at():
    """TEMPORAL-DEFECT-B's repair, exercised by a real composition.

    The coupled input (``ambient_conductance``) still carries no supplier on
    the record — that is finding A1 — but the imposed heat, which the
    composition does NOT supply, is now stated and is enforced.
    """
    system, run, _ = run_case(n_cells=16, heat_w=6.0)
    problem = ft.coupled_problems(system)[3]
    conditions = {c.variable: c for c in problem.initial_conditions}
    assert conditions[lump.HEAT_INPUT].value.magnitude_in("watt") == 6.0


# =====================================================================
# Fresh-process reconstruction
# =====================================================================

_FRESH_PROCESS_SCRIPT = """
import json, sys
payload = json.loads(sys.stdin.read())
from engcore.systems import fluidthermal as ft
from engcore.systems.electrothermal.coupled import (
    FixedPointCouplingPlan, execution_order,
)

system = ft.FluidThermalSystem.from_dict(payload["system"])
plan = FixedPointCouplingPlan.from_dict(payload["plan"])
problems = ft.coupled_problems(system)
issues = plan.check_against(problems)
order = execution_order([p.problem_id for p in problems], plan.uncut)
run = ft.run_fluid_thermal_coupling(system, plan, run_id="fresh-process")
print(json.dumps({
    "issues": list(issues),
    "order": list(order),
    "outcome": run.outcome.value,
    "sweeps": run.iterations_run,
    "temperature": run.final_values[
        (system.diffusivity_problem_id, "temperature")
    ].magnitude_in("kelvin"),
    "edges": sorted(
        (d.source_problem_id, d.source_quantity,
         d.target_problem_id, d.target_quantity)
        for d in plan.dependencies
    ),
}))
"""


def test_the_coupled_specification_reconstructs_and_re_executes_in_a_fresh_process():
    """No hidden bound object survives: JSON in, an executed coupling out.

    Two payloads cross: the system declaration through this pack's own
    ``to_dict``/``from_dict`` (domain-owned plain data, exactly like
    ``Transport2DDomain.to_dict``), and the coupling plan through
    ``FixedPointCouplingPlan``'s own universal-ish serialization. Nothing else.
    No universal ExecutableScientificSpecification was built, and what does not
    cross is recorded in the evidence document rather than invented.
    """
    system, run, _ = run_case(n_cells=16, heat_w=6.0)
    plan = ft.nominal_plan(system, ft.coupled_dependencies(system))
    payload = json.dumps(
        {"system": system.to_dict(), "plan": plan.to_dict()}
    )
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(_FRESH_PROCESS_SCRIPT)],
        input=payload, capture_output=True, text=True,
        timeout=300, cwd=str(REPO_ROOT),
    )
    assert completed.returncode == 0, completed.stderr
    fresh = json.loads(completed.stdout.strip().splitlines()[-1])

    assert fresh["issues"] == []
    assert fresh["order"] == [
        system.diffusivity_problem_id,
        system.fluid_problem_id,
        system.wall_problem_id,
        system.thermal_problem_id,
    ]
    assert fresh["outcome"] == run.outcome.value
    assert fresh["sweeps"] == run.iterations_run
    assert fresh["temperature"] == pytest.approx(
        coupled_temperature(system, run), abs=1e-9
    )
    assert len(fresh["edges"]) == 4


def test_the_reconstruction_residue_is_recorded_rather_than_papered_over():
    """What the plain-data projection does NOT carry.

    Named here so the claim above cannot be read as more than it is: the
    payload carries declarations, not executors. Which Python callable solves
    which problem is supplied by :func:`_executors` in the fresh process, from
    the reconstructed declaration — it is not itself serialized, and no record
    in this repository can carry it.
    """
    system = make_system(n_cells=16)
    payload = system.to_dict()
    assert "executors" not in payload
    assert "solver" not in json.dumps(payload)
    assert "realization" not in json.dumps(payload)
    # The plan carries the graph and the tear, and no execution mapping.
    plan = ft.nominal_plan(system, ft.coupled_dependencies(system))
    assert set(plan.to_dict()) == {
        "schema", "plan_id", "dependencies", "torn", "absolute_tolerance",
        "max_iterations",
    }


# =====================================================================
# Performance
# =====================================================================

def test_performance_is_measured_and_recorded():
    system, run, wall = run_case(n_cells=32, heat_w=6.0)
    timings = ft.sweep_timings(run)
    assert len(timings) == run.iterations_run
    for row in timings:
        assert set(row) >= {
            system.diffusivity_problem_id,
            system.fluid_problem_id,
            system.wall_problem_id,
            system.thermal_problem_id,
            "sweep_total",
        }
        # The PDE leg is the majority of every sweep and is several times any
        # closed-form leg. Measured across the whole executor, so the fluid
        # figure includes its assembly - which is where most of its cost
        # actually is, and which `RawSolverOutput.wall_seconds` does not see.
        # The other three legs are dominated by record construction (a
        # ProvenanceRecord and a ScientificResult each), not by their
        # arithmetic, which is why they are milliseconds and not microseconds.
        assert row[system.fluid_problem_id] > 5.0 * max(
            row[system.diffusivity_problem_id],
            row[system.wall_problem_id],
            row[system.thermal_problem_id],
        )
        assert row[system.fluid_problem_id] > 0.5 * row["sweep_total"]
    assert wall < 120.0
