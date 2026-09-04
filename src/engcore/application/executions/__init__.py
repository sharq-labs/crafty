"""One module per externally exposed execution. v0 exposes exactly one.

An *execution* is a named, versioned operation this deployment offers. A module
here does three things and nothing else:

1. parse that execution's ``inputs`` and ``coupling`` sub-payloads into the
   **existing** typed declarations of the packs that own the science;
2. build the **existing** plan the pack already builds;
3. call the pack's **existing** entry point.

It contains no equation, no numerical method, no tolerance policy, no
convergence rule and no validity rule. Every number it produces is produced by
code that predates this milestone. A test asserts the arithmetic operators are
absent from these modules rather than trusting the claim.
"""

from __future__ import annotations

__all__: list[str] = []
