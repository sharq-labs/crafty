"""EXEC-SPEC-RESIDUE — measure what a record cannot carry, before deciding.

Discovery instrument for `docs/executable-scientific-spec-prereg.md`. It lives
under `experiments/` for a structural reason: that directory is outside `src/`,
so nothing here can be promoted into production core by accident, and this
milestone forbids touching `src/engcore/` at all.

The question is **not** "should Crafty have an executable specification record?".
It is:

    After a maximal honest re-encoding of each existing domain into typed
    contracts that ALREADY EXIST, what information remains that no existing
    contract can carry?

Four columns, four production domains that bind an out-of-band Python artifact:

``col-dc``        electrical DC — a resistive network. Lumped, structural.
``col-slab``      thermal conduction 1-D — a transient PDE benchmark.
``col-cstr``      kinetics CSTR — a stiff nonlinear ODE.
``col-material``  temperature-dependent resistance — a constitutive property.

Module roles:

``cases``       the frozen source artifacts, taken from the domains' own values
``encodings``   the L2 steelman: every representable fact into an existing typed
                channel, plus the *executed* encoding attempts that failed
``instrument``  the records-only reader. Imports `engcore.scientific`; forbidden
                from importing anything under `engcore.domains`, asserted by AST
                scan rather than by convention
``bridge``      records -> executable domain objects. This one MAY import
                domains: it is the execution side, not the reader
``residue``     the residue table and the preregistered decision rule
``child``       the fresh-process entry point, run as a separate interpreter

The split between ``instrument`` and ``bridge`` is the whole design: a reader
that may not know the domain measures what is recoverable; a bridge that does
know the domain measures what is executable. Collapsing them would let domain
knowledge answer a question about records.
"""
