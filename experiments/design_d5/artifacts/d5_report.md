# D5 Generation 1 Evidence

## Generation 0

- population_size: `4`
- evaluated_count: `4`
- target_pass_count: `0`
- target_pass_rate: `0.0`
- pareto_count: `4`
- objective_ranges: `{'yield_score': {'min': 29.0, 'max': 64.0}, 'loss_score': {'min': 6.0, 'max': 30.0}, 'stability_score': {'min': -7.0, 'max': 51.0}}`
- duplicate_assignment_count: `0`

## Generation 1 Proposal Outcomes

- A: INCOMPATIBLE; child_created=False; target_pass=None; result=None
- B: COMPATIBLE; child_created=True; target_pass=False; result={'loss_score': 39.0, 'stability_score': 1.0, 'yield_score': 34.0}
- C: COMPATIBLE; child_created=True; target_pass=False; result={'loss_score': 5.0, 'stability_score': 76.0, 'yield_score': 46.0}
- D: COMPATIBLE; child_created=True; target_pass=False; result={'loss_score': 39.0, 'stability_score': 13.0, 'yield_score': 80.0}
- E: COMPATIBLE; child_created=True; target_pass=False; result={'loss_score': 30.0, 'stability_score': 9.0, 'yield_score': 64.0}

## Comparison

- pareto_mode: `per-generation`
- generation1.proposal_count: `5`
- generation1.compatibility_rejection_count: `1`
- generation1.compatibility_rejection_count_by_state: `{'INCOMPATIBLE': 1, 'INVALID': 0}`
- generation1.accepted_population_size: `4`
- generation1.evaluated_count: `4`
- generation1.target_pass_count: `0`
- generation1.target_pass_rate: `0.0`
- generation1.pareto_count: `3`
- generation1.objective_ranges: `{'yield_score': {'min': 34.0, 'max': 80.0}, 'loss_score': {'min': 5.0, 'max': 39.0}, 'stability_score': {'min': 1.0, 'max': 76.0}}`
- generation1.duplicate_assignment_count: `0`
- generation1.novel_assignment_count: `4`
- generation1.novel_assignment_rate: `1.0`
- generation1.constraint_failure_rate: `0.2`
- generation1.materialized_derived_candidate_count: `4`
- parent_relative_objective_improvements: `2`
- parent_relative_underperformance: `3`

## A1-A23

- A1: PASS - D5 added adjacent implementation/tests/evidence only; frozen D0-D4, ScientificTwin, vertical-slice and K-series semantics unchanged
- A2: PASS - Generation 0 candidates, assignments, Twins, evaluations and population membership are deterministic and order-invariant
- A3: PASS - every D3 entry used by proposals resolves to one Gen0 candidate/Twin/evaluation/result binding
- A4: PASS - every selected slot resolves to the named parent assignment, Twin, evaluation and D3 entry
- A5: PASS - proposal labels A-E, identities, sources and assignments are fixed before evaluation
- A6: PASS - proposal A is rejected before materialization; invalid/forged proposals create no child/Twin/result
- A7: PASS - accepted child candidate/Twin identities are proposal-digest-derived and distinct from Gen0
- A8: PASS - child->proposal->D4 event->parents->D3->compatibility->Twin->evaluation->result lineage round-trips
- A9: PASS - every Gen1 candidate binds a new derived Twin, never a parent Twin
- A10: PASS - no parent result, status, archive, validation, UQ, adequacy, evidence or eligibility is inherited
- A11: PASS - each accepted Gen1 candidate has a new D1 evaluation and new ScientificResult
- A12: PASS - duplicates within Gen1 and across Gen0/Gen1 fail closed
- A13: PASS - insertion order, parent order and serialization round-trip do not change membership or metrics
- A14: PASS - direct objective comparison used only the frozen D5/D4 scientific scope
- A15: PASS - proposal, compatibility, lineage, candidate, Twin, evaluation and comparison records serialize deterministically
- A16: PASS - compatibility, retention, proposal membership, materialization, target and Pareto status do not imply truth/status inflation
- A17: PASS - PASS - tests/test_design_d5_generation.py: 10 passed; PASS - py -m pytest --basetemp D:\engineering-ai-core-k2\.pytest_tmp_d5_full: 1438 passed, 4 warnings
- A18: PASS - all 4 accepted Gen1 assignments are novel relative to Gen0
- A19: PASS - 2 Gen1 candidates improved at least one preregistered objective relative to all lineage parents
- A20: PASS - target-pass rates observed and reported without tuning
- A21: PASS - per-generation Pareto structure observed and reported
- A22: PASS - 1 compatibility rejection avoided materializing proposal A
- A23: PASS - Q8 architecture evidence reported from D5 execution and adversarial review

## N1-N18

- N1: PASS - INVALID; no materialization
- N2: PASS - INVALID; no materialization
- N3: PASS - INCOMPATIBLE; no child/Twin/result
- N4: PASS - Gen0 duplicate rejected: InvalidScientificProblem
- N5: PASS - duplicate Gen1 assignment rejected: InvalidScientificProblem
- N6: PASS - altered generation changes digest and candidate id
- N7: PASS - cross-generation assignment duplicate rejected: InvalidScientificProblem
- N8: PASS - parent result copy rejected: InvalidScientificProblem
- N9: PASS - status inheritance rejected: InvalidScientificProblem
- N10: PASS - compatibility is recomputed from frozen D4 inputs; forged state is ignored
- N11: PASS - materialization mismatch rejected: InvalidScientificProblem
- N12: PASS - permuted proposal input preserved A-E membership
- N13: PASS - missing lineage rejected: InvalidScientificProblem
- N14: PASS - unattributable child result rejected: InvalidScientificProblem
- N15: PASS - incompatible comparison scope rejected: InvalidScientificProblem
- N16: PASS - parent/source order canonicalization preserved identity
- N17: PASS - Twin collision/reuse rejected: InvalidScientificProblem
- N18: PASS - result/evaluation collision rejected: InvalidScientificProblem

## Adversarial Review

- P0/P1: none
- P2: none
- P3: D5 forced an experiment-owned lineage record across D3/D4/D1, but one successor-generation experiment is insufficient evidence to promote it to Core.
- P3: The no-inheritance guard is clearly useful at this boundary; Core promotion should wait for a second non-D4 experiment forcing the same guard shape.
- P3: Policy details remain system-owned: parent slot choices, diversity repair E, target thresholds, compatibility rules, and synthetic equations.

## Architecture Pulled

- GenerationPlan: weak evidence only: D5 needed a deterministic plan identity, but D1 DesignPopulation plus D5-local records were sufficient.
- EvidenceInformedProposal: moderate local evidence: proposal identity needed D3/D1/D4 provenance, but policy remains experiment-owned.
- GenerationLineage: strong D5-local evidence: complete lineage was required to separate decision provenance from scientific evidence.
- PopulationDerivation: moderate local evidence: D5 needed a population-scale derivation artifact, not yet a generic Core abstraction.
- no-inheritance guard: strong local evidence: D5 needed explicit blocks for result/status/evidence leakage into Gen1.

## System-Owned Remaining

- parent selection
- proposal policy
- proposal label ordering
- diversity policy and repair proposal E
- compatibility rules
- recombination/materialization semantics
- interaction equations
- target thresholds
- exploration fraction and accepted-population target

## Successor Evidence

- Repeat the D5 lineage/no-inheritance pattern in a non-D4 system before promoting Core abstractions.
- Consider a generic no-inheritance validator if another experiment also derives scientifically unknown children from evaluated parents.
- Evaluate whether proposal identity should remain provenance-sensitive or converge for identical assignments in later experiments.
- Assess whether D4 compatibility rejection records should become generic population-generation artifacts after another system pack repeats the shape.

## External Frozen Milestones

- MVR0: unchanged
- MVR1: unchanged
