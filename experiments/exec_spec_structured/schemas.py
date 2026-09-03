"""The two structure schema strings, in a module that imports one function.

Same reason as `exec_spec_residue.schemas`: the reconstruction bridge and the
fresh-process child must be able to reach a schema constant without importing
the module that holds the *original* structures. If they could, every fresh
process would have the ground truth loaded and the reconstruction claim would be
unfalsifiable.

Neither schema is proposed as a contract. They exist so the residue can be
serialized, digested and counted, and they are named for the milestone that
measures them rather than for the domain, so that no later reader mistakes them
for domain records.
"""

from __future__ import annotations

from engcore.scientific.serialization import schema_string

__all__ = [
    "MECH_STRUCTURE_SCHEMA",
    "SPECIES_STRUCTURE_SCHEMA",
    "SPECIES_NUMERICS_SCHEMA",
]

#: Node coordinates, element connectivity, constrained degrees of freedom and
#: the load's degree-of-freedom indexing. Measurement only.
MECH_STRUCTURE_SCHEMA = schema_string("exec_spec_mech_structure")

#: Species identities in state order, reaction labels in row order, and the
#: stoichiometric coefficients. Measurement only.
SPECIES_STRUCTURE_SCHEMA = schema_string("exec_spec_species_structure")

#: The integrator's step count and scheme — a SEPARATE payload, and the
#: separation is a correction. An earlier form carried them inside the digested
#: structure record, which collapsed a distinction the preregistration declared
#: binding (scientific reaction-network structure is not integrator
#: configuration) and made the relocation digest cover a solver choice: two
#: payloads identical but for `n_steps` would have had different scientific
#: identities. They travel here, outside the structure digest, because no
#: persistable record reaches `SolverSettings` — which is the gap `EXEC-SPEC`
#: measured on its own kinetics column and did not close.
SPECIES_NUMERICS_SCHEMA = schema_string("exec_spec_species_numerics")
