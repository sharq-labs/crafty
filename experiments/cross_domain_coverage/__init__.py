"""CROSS-DOMAIN-COVERAGE — four consumers, four families, one instrument.

Discovery instrument for `docs/cross-domain-coverage-stress-prereg.md`. It lives
under `experiments/` for a structural reason: that directory is outside `src/`,
so nothing here can be promoted into production core by accident and nothing
ships with the package.

The four consumers, each the cheapest scientifically real member of its family
that is **not isomorphic to something the repository already exercises**:

``mechanics``    A — two-element plane-stress patch. Rank-1 unknown, rank-2
                 derived quantity, matrix constitutive law. A 1D bar was
                 rejected: it is isomorphic to the existing MNA solve.
``transport2d``  B — 2D steady advection-diffusion in a prescribed rotational
                 field, verified by manufactured solution. Minimised: steady,
                 one scheme, two grids.
``species``      C — closed isothermal three-species batch with two reactions
                 and a weighted conservation invariant. Isothermal and closed
                 are deliberate costs, paid to eliminate overlap with the
                 existing CSTR and with consumer B respectively.
``dynamics``     D — planar pendulum in Cartesian coordinates: a genuine
                 constrained-dynamics DAE. A controlled first-order plant was
                 rejected: it is isomorphic to the existing lumped thermal ODE.

``records``      The steelman encodings — every consumer expressed as far as
                 existing typed contracts allow, and no further.
``instrument``   The shared records-only reader. **One** instrument for four
                 consumers; that is the milestone's entire cost case, and
                 writing a per-consumer reader is a preregistered fail
                 condition. It may not import any probe module, asserted by AST
                 scan.

The physics modules import nothing from `engcore`. Keeping the science ignorant
of the representation is what stops the representation from quietly reaching
into it when a record cannot say something.
"""
