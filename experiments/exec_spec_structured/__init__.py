"""EXEC-SPEC-STRUCTURED — the reversal test `EXEC-SPEC` said had to be run.

`docs/exec-spec-structured-input-stress-prereg.md`. `EXEC-SPEC` decided against a
universal executable-specification record on four columns that were all
scalar-parameter domains, and recorded the limit itself: two committed,
executed consumers carrying non-scalar structure were **not** columns. This is
those two.

    col-mech     experiments/cross_domain_coverage/mechanics.py   CASE A2, plane stress
    col-species  experiments/cross_domain_coverage/species.py     CASE C1

Neither probe is edited. Their physics modules import nothing from `engcore`,
which is what allows a bridge to be written against them without the science
reaching into the representation.

Module roles:

``schemas``     the two structure schema strings, importing nothing
``encodings``   the L2 steelman for both columns, and the executed attempts
``bridge``      records -> reconstructed structure -> execution
``reader``      the records-only reader EXTENSION. Written beside
                `exec_spec_residue.instrument` rather than inside it, because
                `EXEC-SPEC` may not be edited — and the size of this file is
                itself the measurement of option E's per-consumer cost
``residue``     the two residue tables, the overlap analysis, and the
                false-universality attack
``child``       the fresh-process entry point

TWO GRADES OF RECONSTRUCTION, AND THE WEAKER ONE IS LABELLED
-------------------------------------------------------------
**INJECTED** — the reconstructed value is consumed by the computation.
**VERIFIED-EQUAL** — the reconstructed value is compared field-by-field against
the probe's ground truth, and the probe then computes from its own module
constants.

`mechanics.py` reads `NODES` and `ELEMENTS` from module scope, so its geometry
can only be VERIFIED-EQUAL without editing committed evidence. Reporting that as
INJECTED is a preregistered fail condition, and the asymmetry is a finding in
its own right: **in both consumers the structured data lives as source code.**
"""
