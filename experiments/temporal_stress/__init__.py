"""TEMPORAL-SEMANTICS-STRESS probe pack.

Discovery only. Nothing here is a contract, nothing here is imported by
``src/``, and nothing here defines a temporal type. The pack exists to answer
one preregistered question — ``docs/temporal-semantics-stress-prereg.md`` §1 —
by measuring what four already-executing consumers can and cannot say about
time through the universal records they already produce.

Four modules:

``reader``
    The instrument. A records-only reader that imports no domain, parses no
    name's internal structure and reads no ``metadata``. Criterion F2 is
    decided by what this reader can and cannot recover.
``separations``
    A1/Q1. Varies physical time, solver step, coupling iterate and wall-clock
    independently across the four consumers and records the consequences.
``exposure``
    A4/A6/Q4/Q6. Two schedules on one lumped body reaching the same final
    state at the same final time with different accumulated exposure.
``encodings``
    Z1-Z8. The zero-new-contract attempts, each recording both what it
    achieved and what it could not.
"""
