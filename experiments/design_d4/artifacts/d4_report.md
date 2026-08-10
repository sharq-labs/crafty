# D4 Compatibility / Recombination Evidence

## Experiment Counts

- proposed_recombinations: `4`
- compatible_count: `3`
- incompatible_count: `1`
- invalid_count: `0`
- materialized_count: `3`
- scientifically_evaluated_count: `3`
- child_underperformed_relevant_parent_count: `2`
- child_improved_preregistered_objective_count: `2`
- compatible_but_target_failing_count: `3`

## Cases A-D

- Case A: INCOMPATIBLE; child_created=False; target=None; outputs=None
- Case B: COMPATIBLE; child_created=True; target=False; outputs={'loss_score': 39.0, 'stability_score': 1.0, 'yield_score': 34.0}
- Case C: COMPATIBLE; child_created=True; target=False; outputs={'loss_score': 5.0, 'stability_score': 76.0, 'yield_score': 46.0}
- Case D: COMPATIBLE; child_created=True; target=False; outputs={'loss_score': 39.0, 'stability_score': 13.0, 'yield_score': 80.0}

## A1-A20

- A1: PASS - D0/D1/D2/D3, ScientificTwin, K-series, MVR0 and MVR1 files were not modified by D4 implementation
- A2: PASS - D4 added a domain-neutral local design module, tests, and experiment harness only
- A3: PASS - selected slots resolve to exact parent candidate, Twin, evaluation, and D3 memory entry; adversarial mismatch tests fail closed
- A4: PASS - compatibility is typed, deterministic, performance-independent, and executed before materialization
- A5: PASS - Case A/N1 is INCOMPATIBLE and creates no child, Twin, or result
- A6: PASS - recombination identity is deterministic across parent/source/input ordering and serialization
- A7: PASS - derivation record round-trips child, sources, parents, parent Twins, D3 entries, compatibility and materialization semantics
- A8: PASS - compatible children have candidate ids distinct from all parents
- A9: PASS - compatible children have Derived Twin references distinct from all parent Twins
- A10: PASS - child candidates, Twins and results do not inherit parent scientific result, evidence, target, Pareto, validation, UQ or adequacy claims
- A11: PASS - child outputs exist only through new D1 child evaluations with child ResultBinding
- A12: PASS - D4 compatibility/derivation/candidate/Twin records serialize deterministically and round-trip
- A13: PASS - parent/source ordering permutations do not change event identity
- A14: PASS - strong components were insufficient: Case A is incompatible and Case B is compatible but poor
- A15: PASS - Case B materialized and underperformed a relevant parent on preregistered objectives
- A16: PASS - compatibility, recombination and retention metadata do not assert feasibility, safety, adequacy, validation, target pass or success
- A17: PASS - PASS - tests/test_design_d4_recombination.py: 8 passed; PASS - py -3 -m pytest -q --basetemp .pytest_tmp_d4_full: 1428 passed, 4 warnings
- A18: PASS - Case C improved at least one preregistered objective relative to both source parents
- A19: PASS - Case D received a valid child result and failed the overall target
- A20: PASS - Q8 architecture evidence is reported from D4 execution

## Adversarial Review

- P0/P1: none
- P2: none
- P3: D4 still inherits the repository's non-cryptographic object identity debt; it validates cheap scientific/compositional content at the boundary but does not prove global authenticity.
- P3: The experiment forced an authoritative local multi-parent derivation record, but one synthetic experiment is not enough evidence to redesign ScientificTwin.parent.
- P3: Compatibility rules, component meaning, interaction equations, and materialization constraints remain system-pack semantics.

## Architecture Pulled

- derivation_lineage: A structured D4-local derivation record was forced; generic Core lineage remains successor evidence, not proven.
- compatibility_assessment_result: A small typed local state/result object was forced; generic compatibility semantics were not.
- recombination_identity: A deterministic D4 event digest was forced for this experiment; generic recombination identity remains unproven.
- derived_candidate_relationship: Existing DesignCandidate generation/parents/operator fields were sufficient when paired with the D4 record.
- multi_parent_lineage: Authoritative multi-parent lineage was forced beside ScientificTwin; the frozen single Twin parent was not changed.

## System/Domain Specific

- compatibility rules and pair matrix
- component slot meaning
- adapter requirements
- synthetic interaction equations
- target thresholds
- child materialization semantics
- system constraints and future admissibility policy
