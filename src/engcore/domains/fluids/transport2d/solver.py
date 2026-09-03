"""Transport2DSolver — the production SciPy sparse realization — and
NativeDenseTransport2DSolver, an independent-assembly reference check.

MODEL != REALIZATION != SOLVER, restated concretely for this domain
----------------------------------------------------------------------
``problem.TRANSPORT2D_MODEL`` is the scientific claim: a conservation
statement, ``div(u c) - D grad^2 c = s``. It names no numerical scheme.

The DISCRETIZATION — first-order upwind advection, second-order central
diffusion, a cell-centered finite-volume stencil with ghost-cell Dirichlet
treatment — is the *realization*: one specific way of computing the claim.
It is shared, unchanged, by both solver classes below: :func:`assemble`
builds ONE linear system (as a dense array and as a SciPy CSR matrix,
together, so the two representations are provably the same system, not two
independently-typed-in systems that happen to agree) and each solver class
only chooses how to *factor and solve* it.

Per ``docs/fluid-pde-preparation.md`` §B3 (SciPy sparse ~95x cheaper at
n=64, dense scaling as O(dof^3)): SciPy sparse (``spsolve``) is the
PRODUCTION path — :class:`Transport2DSolver`. Dense NumPy
(``numpy.linalg.solve``) is retained ONLY as an independent-assembly
reference check — :class:`NativeDenseTransport2DSolver` — and is never
claimed as part of the science. Neither solver's identity, capability, or
result carries "scipy" or "numpy" as a scientific fact; both carry it only
as ``SolverIdentity.backend``, exactly where ``thermal/conduction1d`` puts
its own backend string.

FIVE-STAGE LIFECYCLE, held strictly separate (same discipline as Electrical
and Thermal): ``supports`` (capability question, never executes) ->
``prepare`` (assemble) -> ``solve`` (raw floats) -> ``extract_metrics``
(units restored) -> ``validate`` (independent checks, see validation.py).

FLATTENING CONVENTION — DOCUMENTED, NOT TYPED (F5 residue)
--------------------------------------------------------------
Cell ``(i, j)`` (x-index ``i``, y-index ``j``, both 0-based, cell centres at
``(i+0.5)*dx, (j+0.5)*dx``) is row ``i*n + j`` of every vector and matrix
here. Nothing in ``ScientificDataReference`` states this — ``count`` is
documented as "not a shape, mesh, topology or field support" — so this
sentence is the only place the convention is recorded, exactly the residue
``docs/fluid-pde-preparation.md`` §B6 predicted and this milestone confirms
rather than closes (closing it would mean building a shape/topology
contract, explicitly out of scope).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ....scientific.ir.problem import ScientificProblem
from ....scientific.results.data_reference import ScientificDataReference
from ....scientific.results.provenance import ProvenanceRecord
from ....scientific.results.result import ScientificResult
from ....scientific.results.uncertainty import Uncertainty
from ....scientific.results.validation import ValidationReport
from ....scientific.results.variable_binding import VariableBulkLinkage
from ....scientific.solvers.protocol import (
    ConvergenceState,
    PreparedSolve,
    RawSolverOutput,
    SolverIdentity,
    SolverSettings,
)
from ....scientific.units.quantity import Quantity
from .errors import Transport2DBindingError, Transport2DError
from .problem import (
    CENTRE_METRIC,
    FIELD_UNIT,
    FIELD_VARIABLE,
    MAX_METRIC,
    MIN_METRIC,
    TRANSPORT2D_ADVECTION_DIFFUSION,
    TRANSPORT2D_MODELS,
    Transport2DDomain,
    transport2d_solver_capabilities,
    verify_problem_matches_domain,
)
from .reference import c_star, source, velocity
from .validation import Transport2DValidationSettings, build_validation_report

SPARSE_SOLVER_ID = "fluids.transport2d.upwind_central_scipy_sparse"
DENSE_SOLVER_ID = "fluids.transport2d.upwind_central_native_dense"
SOLVER_VERSION = "0.1.0"
SPARSE_BACKEND = "scipy.sparse.linalg.spsolve"
DENSE_BACKEND = "numpy.linalg.solve"


# =====================================================================
# Shared assembly — ONE discretization, two solve paths
# =====================================================================

@dataclass(frozen=True)
class PreparedTransport2DSystem:
    """The assembled system, in both representations, and the grid it lives
    on. Both matrices are built together in one pass (see :func:`assemble`)
    so they are provably the same linear system."""

    domain: Transport2DDomain
    dense: np.ndarray               # (dof, dof)
    sparse: Any                     # scipy.sparse csr_matrix, (dof, dof)
    rhs: np.ndarray                 # (dof,)
    centres: np.ndarray             # (n,) cell-centre coordinates, one axis

    @property
    def n(self) -> int:
        return self.domain.grid.n_cells

    @property
    def centre_index(self) -> int:
        """Flat index of the domain-centre cell. Exact for an even n_cells
        (the centre coordinate then falls in a well-defined middle cell);
        for odd n_cells this is the nearest cell to the centre, not the
        exact geometric centre — documented, not hidden, in the QoI's own
        provenance metadata."""
        mid = self.n // 2
        return mid * self.n + mid


def _index(i: int, j: int, n: int) -> int:
    return i * n + j


def assemble(domain: Transport2DDomain) -> PreparedTransport2DSystem:
    """Build the discretized linear system as BOTH a dense array and a
    SciPy CSR matrix, from one shared loop, over Dirichlet ghost cells.

    Scheme (unchanged from the preparation probe): first-order upwind for
    advection, second-order central differencing for diffusion, a
    finite-volume cell-centered stencil. A ghost-cell value outside the
    domain is the manufactured solution evaluated at the ghost centre
    (Dirichlet), moved to the right-hand side.
    """
    n = domain.grid.n_cells
    side_m = domain.side_m
    diffusivity = domain.diffusivity_m2_s
    omega = domain.omega_per_s
    dx = domain.dx_m

    centres = (np.arange(n) + 0.5) * dx
    dof = n * n
    dense = np.zeros((dof, dof))
    sparse = sp.lil_matrix((dof, dof))
    rhs = np.zeros(dof)

    for i in range(n):
        for j in range(n):
            x, y = centres[i], centres[j]
            ux, uy = velocity(x, y, side_m=side_m, omega_per_s=omega)
            row = _index(i, j, n)
            rhs[row] = source(
                x, y, side_m=side_m, diffusivity_m2_s=diffusivity, omega_per_s=omega
            )
            diagonal = 4.0 * diffusivity / (dx * dx)

            def neighbour(di: int, dj: int, coeff: float) -> None:
                nonlocal diagonal
                ii, jj = i + di, j + dj
                if 0 <= ii < n and 0 <= jj < n:
                    col = _index(ii, jj, n)
                    dense[row, col] += coeff
                    sparse[row, col] += coeff
                else:
                    gx = (ii + 0.5) * dx
                    gy = (jj + 0.5) * dx
                    rhs[row] -= coeff * c_star(gx, gy, side_m=side_m)

            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbour(di, dj, -diffusivity / (dx * dx))

            if ux >= 0.0:
                diagonal += ux / dx
                neighbour(-1, 0, -ux / dx)
            else:
                diagonal += -ux / dx
                neighbour(1, 0, ux / dx)
            if uy >= 0.0:
                diagonal += uy / dx
                neighbour(0, -1, -uy / dx)
            else:
                diagonal += -uy / dx
                neighbour(0, 1, uy / dx)

            dense[row, row] += diagonal
            sparse[row, row] += diagonal

    return PreparedTransport2DSystem(
        domain=domain,
        dense=dense,
        sparse=sparse.tocsr(),
        rhs=rhs,
        centres=centres,
    )


def _values_from_field(field_flat: np.ndarray) -> dict[str, float]:
    return {
        MAX_METRIC: float(np.max(field_flat)),
        MIN_METRIC: float(np.min(field_flat)),
    }


# =====================================================================
# Shared solver scaffolding
# =====================================================================

@dataclass
class _Transport2DSolverBase:
    """Common lifecycle plumbing for both solver classes. Not itself a
    ScientificSolver — each concrete class below declares its own identity
    and its own numerical ``solve``; only ``supports``/``prepare`` (which do
    not depend on which linear-algebra backend is chosen) are shared."""

    settings: Transport2DValidationSettings = field(
        default_factory=Transport2DValidationSettings
    )
    _domains: dict[str, Transport2DDomain] = field(default_factory=dict, repr=False)

    def bind_domain(self, domain: Transport2DDomain, problem_id: str) -> None:
        if not isinstance(domain, Transport2DDomain):
            raise Transport2DError("bind_domain expects a Transport2DDomain")
        key = str(problem_id)
        existing = self._domains.get(key)
        if existing is not None and existing.fingerprint() != domain.fingerprint():
            raise Transport2DBindingError(
                f"problem {key!r} is already bound to a different domain "
                f"(bound {existing.fingerprint()[:12]}…, incoming "
                f"{domain.fingerprint()[:12]}…); rebinding to different "
                f"physics is refused — use a distinct problem id"
            )
        self._domains[key] = domain

    def bound_domain(self, problem_id: str) -> Transport2DDomain | None:
        return self._domains.get(str(problem_id))

    def supports(self, problem: ScientificProblem) -> bool:
        if not isinstance(problem, ScientificProblem):
            return False
        declared = {c.name for c in transport2d_solver_capabilities()}
        if not set(problem.required_capabilities).issubset(declared):
            return False
        domain_models = {m.model_id for m in TRANSPORT2D_MODELS}
        referenced = {r.model_id for r in problem.models}
        if not referenced & domain_models:
            return False
        return TRANSPORT2D_ADVECTION_DIFFUSION.name in problem.required_capabilities

    def prepare(self, problem: ScientificProblem) -> PreparedSolve:
        domain = self.bound_domain(problem.problem_id)
        if domain is None:
            raise Transport2DError(
                f"no domain bound for problem {problem.problem_id!r}; call "
                f"bind_domain() first — the universal IR carries no geometry"
            )
        if not self.supports(problem):
            raise Transport2DError(
                f"problem {problem.problem_id!r} is not a 2D steady "
                f"advection-diffusion transport problem"
            )
        verify_problem_matches_domain(problem, domain)
        system = assemble(domain)
        return PreparedSolve(
            problem=problem,
            solver=self.identity,  # type: ignore[attr-defined]
            settings=self.solver_settings,  # type: ignore[attr-defined]
            payload=system,
            notes=(
                f"{system.n}x{system.n} grid, dof={domain.grid.dof}, "
                f"dx={domain.dx_m:.6g} m, Pe_cell(peak)="
                f"{domain.peak_cell_peclet:.6g}",
            ),
        )

    def extract_metrics(
        self, prepared: PreparedSolve, raw: RawSolverOutput
    ) -> dict[str, Quantity]:
        if not raw.succeeded:
            return {}
        return {name: Quantity(value, FIELD_UNIT) for name, value in raw.values.items()}

    def validate(self, prepared: PreparedSolve, raw: RawSolverOutput) -> ValidationReport:
        system: PreparedTransport2DSystem = prepared.payload
        return build_validation_report(system, raw, self.settings)  # type: ignore[attr-defined]


# =====================================================================
# Production solver: SciPy sparse
# =====================================================================

@dataclass
class Transport2DSolver(_Transport2DSolverBase):
    """The PRODUCTION solver — SciPy sparse direct factorization."""

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(SPARSE_SOLVER_ID, SOLVER_VERSION, backend=SPARSE_BACKEND)

    @property
    def capabilities(self):
        return transport2d_solver_capabilities()

    @property
    def solver_settings(self) -> SolverSettings:
        return SolverSettings(
            tolerances=self.settings.as_mapping(),
            options={
                "advection_scheme": "first_order_upwind",
                "diffusion_scheme": "central_2nd_order",
                "discretization": "cell_centered_finite_volume",
                "backend": SPARSE_BACKEND,
            },
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        return _solve_with_backend(
            prepared, backend="sparse", settings=self.settings
        )


# =====================================================================
# Reference-check solver: dense NumPy
# =====================================================================

@dataclass
class NativeDenseTransport2DSolver(_Transport2DSolverBase):
    """An INDEPENDENT-ASSEMBLY-SHARING reference-check solver, dense NumPy.

    Not the production path (see the module docstring and
    ``docs/fluid-pde-preparation.md`` §B3's cost measurement). Used to
    cross-check the sparse production result at every grid this milestone
    verifies — see validation.py's ``sparse_dense_assembly_agreement``
    check and F3/F7 in the evidence document. Because both solvers consume
    the SAME assembled system (see :func:`assemble`'s docstring), agreement
    between them is an assembly/solver-behaviour consistency check, not
    CROSS_SOLVER_VALIDATED evidence about independently-implemented
    physics — the honest distinction the preparation document's own §B3.1
    already draws, preserved here rather than overclaimed.
    """

    @property
    def identity(self) -> SolverIdentity:
        return SolverIdentity(DENSE_SOLVER_ID, SOLVER_VERSION, backend=DENSE_BACKEND)

    @property
    def capabilities(self):
        return transport2d_solver_capabilities()

    @property
    def solver_settings(self) -> SolverSettings:
        return SolverSettings(
            tolerances=self.settings.as_mapping(),
            options={
                "advection_scheme": "first_order_upwind",
                "diffusion_scheme": "central_2nd_order",
                "discretization": "cell_centered_finite_volume",
                "backend": DENSE_BACKEND,
            },
        )

    def solve(self, prepared: PreparedSolve) -> RawSolverOutput:
        return _solve_with_backend(
            prepared, backend="dense", settings=self.settings
        )


def _solve_with_backend(
    prepared: PreparedSolve,
    *,
    backend: str,
    settings: Transport2DValidationSettings,
) -> RawSolverOutput:
    system: PreparedTransport2DSystem = prepared.payload
    started = time.perf_counter()

    try:
        if backend == "sparse":
            field_flat = spla.spsolve(system.sparse, system.rhs)
            residual = float(np.linalg.norm(system.sparse @ field_flat - system.rhs))
        else:
            field_flat = np.linalg.solve(system.dense, system.rhs)
            residual = float(np.linalg.norm(system.dense @ field_flat - system.rhs))
    except (RuntimeError, ValueError, np.linalg.LinAlgError) as exc:
        return RawSolverOutput(
            convergence=ConvergenceState.FAILED,
            warnings=("system could not be solved",),
            diagnostics={"error_type": type(exc).__name__, "error": str(exc)},
            wall_seconds=time.perf_counter() - started,
        )

    wall = time.perf_counter() - started
    if not np.all(np.isfinite(field_flat)):
        return RawSolverOutput(
            convergence=ConvergenceState.DIVERGED,
            warnings=("solve produced non-finite values",),
            diagnostics={"dof": system.domain.grid.dof},
            wall_seconds=wall,
        )

    values = {
        CENTRE_METRIC: float(field_flat[system.centre_index]),
        **_values_from_field(field_flat),
    }

    # Bulk field output, named identity per DATA-BOUNDARY0 — this is the
    # spatial output F4 requires VariableBulkLinkage to bind (see
    # solve_transport2d below).
    field_reference, field_bytes = ScientificDataReference.for_values(
        FIELD_VARIABLE, field_flat.tolist(), unit=FIELD_UNIT
    )

    return RawSolverOutput(
        convergence=ConvergenceState.CONVERGED,
        values=values,
        residuals={"linear_system_residual": residual},
        iterations=1,  # a single direct factor-and-solve; no outer iteration
        wall_seconds=wall,
        data_references=(field_reference,),
        diagnostics={
            "n_cells": system.n,
            "dof": system.domain.grid.dof,
            "dx_m": system.domain.dx_m,
            "peak_cell_peclet": system.domain.peak_cell_peclet,
            "backend": backend,
            "linear_system_residual": residual,
            "field_bytes_length": len(field_bytes),
            "field": [float(v) for v in field_flat],
        },
    )


# =====================================================================
# Public wrapper
# =====================================================================

def solve_transport2d(
    domain: Transport2DDomain,
    *,
    run_id: str,
    solver: "Transport2DSolver | NativeDenseTransport2DSolver | None" = None,
    problem: ScientificProblem | None = None,
    cross_check: bool = True,
    software_version: str = "engcore.domains.fluids.transport2d/0.1.0",
    git_commit: str | None = None,
    timestamp: str | None = None,
    environment: Mapping[str, str] | None = None,
    parent_run_id: str | None = None,
) -> ScientificResult:
    """Run the full contract lifecycle for one domain and return a result.

    Orchestration only, mirroring ``thermal/conduction1d.solve_slab``. When
    ``cross_check`` is true (the default) the dense reference solver is ALSO
    run against the same assembled system and its agreement with the
    production sparse result becomes a validation check
    (``sparse_dense_assembly_agreement``) rather than a silent assumption.

    **F4 — the mandatory real VariableBulkLinkage caller.** The field output
    is bound to its declared ``ScientificVariable`` here, in production
    code, not only in a test: ``VariableBulkLinkage(FIELD_VARIABLE,
    field_reference.name)`` is constructed and checked with
    ``check_against`` against the actual problem and result before the
    result is returned. If the check reports any issue, construction fails
    loudly rather than shipping a result with an unresolved linkage.
    """
    from .problem import build_transport2d_problem

    solver = solver or Transport2DSolver()
    problem = problem or build_transport2d_problem(domain)
    verify_problem_matches_domain(problem, domain)
    solver.bind_domain(domain, problem.problem_id)

    prepared = solver.prepare(problem)
    raw = solver.solve(prepared)
    metrics = solver.extract_metrics(prepared, raw)

    dense_raw: RawSolverOutput | None = None
    if cross_check and raw.succeeded:
        dense_solver = NativeDenseTransport2DSolver(settings=solver.settings)
        dense_solver.bind_domain(domain, problem.problem_id)
        dense_prepared = dense_solver.prepare(problem)
        dense_raw = dense_solver.solve(dense_prepared)

    report = build_validation_report(
        prepared.payload, raw, solver.settings, dense_raw=dense_raw
    )

    model_identities = tuple((m.model_id, m.version) for m in TRANSPORT2D_MODELS)
    assumptions = TRANSPORT2D_MODELS[0].assumptions

    inputs = {
        "diffusivity": domain.diffusivity,
        "side": domain.side,
        "angular_rate": domain.angular_rate,
    }
    diagnostics = {k: v for k, v in raw.diagnostics.items() if k != "field"}
    provenance = ProvenanceRecord(
        run_id=run_id,
        software_version=software_version,
        git_commit=git_commit,
        models=model_identities,
        solvers=((solver.identity.solver_id, solver.identity.version),),
        inputs=inputs,
        assumptions=assumptions,
        tolerances=solver.settings.as_mapping(),
        environment=dict(environment or {}),
        timestamp=timestamp,
        parent_run_id=parent_run_id,
        metadata={
            "domain_id": domain.domain_id,
            "domain_fingerprint": domain.fingerprint(),
            "advection_scheme": "first_order_upwind",
            "diffusion_scheme": "central_2nd_order",
            "backend": solver.identity.backend,
            "domain_canonical": domain.to_dict(),
        },
    )

    result = ScientificResult(
        result_id=run_id,
        problem_id=problem.problem_id,
        values=metrics,
        models=model_identities,
        solver=solver.identity,
        convergence=raw.convergence,
        validation=report,
        uncertainty={
            name: Uncertainty.unknown(
                "no uncertainty quantification performed; discretization "
                "error is established by the refinement gate, not by one "
                "solve"
            )
            for name in metrics
        },
        assumptions=assumptions,
        warnings=raw.warnings,
        provenance=provenance,
        data_references=raw.data_references,
        metadata={
            "domain_id": domain.domain_id,
            "domain_fingerprint": domain.fingerprint(),
            "numerics": diagnostics,
            "residuals": dict(raw.residuals),
            "iterations": raw.iterations,
            "wall_seconds_telemetry": raw.wall_seconds,
        },
    )

    if raw.succeeded and raw.data_references:
        linkage = VariableBulkLinkage(
            variable_name=FIELD_VARIABLE,
            reference_name=raw.data_references[0].name,
            description=(
                "the concentration field c over the n x n grid, row-major "
                "i*n+j flattening (see solver.py module docstring)"
            ),
        )
        issues = linkage.check_against(problem=problem, result=result)
        if issues:
            raise Transport2DError(
                f"VariableBulkLinkage failed check_against for result "
                f"{run_id!r}: {issues}"
            )

    return result
