"""HOSTILE-CORE-STRESS — the 1D advection-diffusion representation probe.

This package exists to be *attacked*, not to be used. It is a discovery
instrument for `docs/hostile-core-domain-stress-prereg.md`, and it lives under
`experiments/` for a structural reason rather than a stylistic one:
`experiments/` is outside `src/`, so nothing here can be promoted into
production core by accident, and nothing here ships with the package.

Three modules, in the order the milestone reads them:

``transport1d``
    The frozen consumer's physics and numerics. Plain arithmetic; imports
    nothing from `engcore`. It is the thing being represented, kept separate
    from the representation so the representation cannot cheat by reaching
    into it.

``records``
    The **steelman** encoding — the maximal honest expression of that consumer
    using only contracts that already exist in `engcore.scientific`. No new
    contract is defined here, and none may be.

``reader``
    The instrument. A records-only reader that is handed serialized payloads
    and counts admissible readings. It imports `engcore.scientific` and the
    standard library, and it **must not** import `transport1d` or `records` —
    a test asserts this by AST scan, because a reader that can see the domain
    is not measuring what the records say.
"""
