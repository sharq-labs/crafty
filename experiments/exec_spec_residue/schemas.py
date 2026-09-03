"""The three payload schema strings, in a module that imports nothing.

They live here rather than in :mod:`encodings` for one reason, and it is the
whole credibility of the fresh-process test: :mod:`encodings` imports
:mod:`cases`, which holds the **original in-memory artifacts**. If the
reconstruction bridge imported `encodings` for a constant, every fresh process
that reconstructs anything would also have the originals loaded, and a skeptic
would be right to say the reconstruction could have read them.

So the child process imports `bridge`, `bridge` imports `schemas`, and neither
`cases` nor `encodings` is reachable from that path. The test asserts exactly
that against the child's own `sys.modules`.
"""

from __future__ import annotations

from engcore.scientific.serialization import schema_string

__all__ = [
    "DC_STRUCTURE_SCHEMA",
    "SLAB_STRUCTURE_SCHEMA",
    "CSTR_NUMERICS_SCHEMA",
]

#: The electrical DC column reuses the **domain's own existing schema** rather
#: than minting a parallel one. That the domain already publishes a
#: round-trippable circuit record is the finding; inventing a second name for it
#: would hide that.
DC_STRUCTURE_SCHEMA = "electrical_dc_circuit/1"

#: Defined by this milestone, for measurement only. Neither is proposed as a
#: contract: they exist so the residue can be serialized and counted.
SLAB_STRUCTURE_SCHEMA = schema_string("exec_spec_slab_residue")
CSTR_NUMERICS_SCHEMA = schema_string("exec_spec_cstr_numerics")
