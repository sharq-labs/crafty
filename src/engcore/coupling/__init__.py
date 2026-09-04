"""Domain-neutral coupling **execution and composition infrastructure**.

`COUPLING-PACK-RELOCATION`. This package is deliberately and explicitly **NOT
universal scientific semantics.** It is not part of `engcore.scientific`, it is
not a promotion into universal Core, and it is not a multiphysics framework.
The distinction it draws is narrow and is the whole point of the package:

    A generic coupling package may **transport identities and values** between
    separately posed problems and **execute a declared plan** over them. It may
    not know what any transported value *means*.

Concretely, it understands: participants (as ``problem_id``\\ s), declared
dependencies between them, which of those are cut, what a cut edge is seeded
with, iteration, the change in an iterate, a stopping criterion in one ratio
scale unit, a budget, an outcome, and provenance references. It understands
**nothing** about electrical power, fluid diffusivity, a temperature-dependent
material law, heat-transfer coefficients, or any scientific equation. Every
object here is scanned for domain vocabulary by test, not trusted to be free of
it.

Why this package exists
-----------------------
Two materially different production coupled systems share this machinery **by
object identity, unedited**:

* ``engcore.systems.electrothermal`` — Electrical ↔ Thermal (`ET-VERTICAL`)
* ``engcore.systems.fluidthermal``   — Fluid ↔ Thermal (`FT-SCALAR-COUPLING`)

`FT-SCALAR-COUPLING` measured that reuse and recorded the two costs of the
machinery living inside a domain-named pack: a fluid ↔ thermal run serialized
under ``electrothermal_coupled_run/1``, and a new coupled pack had to import a
*domain-named* system pack to reach the loop. Both were false ownership. This
package removes it, before any stored payload existed to be broken.

What stays in the system packs
------------------------------
Everything scientific. ``R(T)``, ``I²R``, the electrical → thermal mapping,
``D(T)``, boundary efflux, the ``hA`` mapping, participant construction,
executor construction, result extraction, model identities, and every
``QuantityDependency`` **declaration** — which values flow where is a statement
about physics and is made by the pack that knows the physics. This package
executes what it is handed.

What is deliberately absent
---------------------------
No relaxation, damping, acceleration, Aitken or Anderson field, parameter or
identifier — 40 sweeps → iteration limit and 56 sweeps → convergence were
measured on the same contracting map without one, so nothing forces one. No
scheduler, no participant registry, no transfer operator, no interpolator, no
cross-mesh transfer, no field-valued exchange, no ``ScientificField``, no mesh,
no topology, no temporal semantics, no planner, no provider framework. A knob
no measurement forced is a speculative knob.
"""

from __future__ import annotations

from .execution import (
    COUPLED_ITERATION_SCHEMA,
    COUPLED_RUN_SCHEMA,
    CoupledIteration,
    CoupledRun,
    run_fixed_point,
)
from .graph import cycle_edges, edge_key, execution_order
from .plan import (
    FIXED_POINT_PLAN_SCHEMA,
    TORN_ENDPOINT_SCHEMA,
    CouplingOutcome,
    FixedPointCouplingPlan,
    TornEndpoint,
)
from .scales import is_ratio_scale, shares_origin

__all__ = [
    "COUPLED_ITERATION_SCHEMA",
    "COUPLED_RUN_SCHEMA",
    "CoupledIteration",
    "CoupledRun",
    "CouplingOutcome",
    "FIXED_POINT_PLAN_SCHEMA",
    "FixedPointCouplingPlan",
    "TORN_ENDPOINT_SCHEMA",
    "TornEndpoint",
    "cycle_edges",
    "edge_key",
    "execution_order",
    "is_ratio_scale",
    "run_fixed_point",
    "shares_origin",
]
