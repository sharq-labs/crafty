# D5 - Generation 1 / Memory-Informed Candidate Generation V0.1 freeze

Status: **PASS / FROZEN**

Milestone ID: `D5`

## Frozen identities

- Previous frozen D4 checkpoint: `0cb5e5b72d67a6e77cc17f388d1b3e4c17581ca2`
- Frozen D5 preregistration checkpoint: `ab91741880b70499abdc0d2a29d58ab487fd30c6`
- Final tested D5 implementation checkpoint: `a80defa51df6c773d5bfca275ed9bedf4fee84e2`
- Preregistration: `docs/design-d5-generation1-prereg.md`

The D5 preregistration remained **FROZEN BEFORE IMPLEMENTATION** and was not
rewritten after observing Generation 1 results, gate outcomes, experiment
artifacts or adversarial review findings.

## Scope actually delivered

D5 demonstrates one controlled, deterministic successor population:

```text
Generation 0
-> Evidence
-> D3 Memory
-> D4 Compatibility/Recombination
-> Generation 1
-> NEW Scientific Evidence
```

D5 does not implement autonomous discovery, next-experiment selection,
information gain, uncertainty-aware planning, expected improvement, Bayesian
optimization, active learning, adaptive compute, repeated self-evolution or LLM
scientific orchestration.

## Key scientific conclusion

D5 demonstrated a deterministic Generation 1 population informed by prior
scientific evidence while preserving the boundary that memory-informed
generation is not optimization.

Generation 1 is not scientifically better by definition. Parent success does
not imply child success. Compatibility does not predict performance. Memory is
decision provenance, not scientific truth. Every accepted Generation 1
Candidate begins scientifically **UNKNOWN** and requires a new Candidate
identity, new ScientificTwin identity/reference, new D1 evaluation and new
ScientificResult before any scientific claim exists.

No parent scientific result or status was inherited.

## Generation 0 evidence

- population: `d5-g0-baseline-population-v0.1`
- generator: `d5-enumerated-baseline-v0.1`
- size: `4`
- evaluated: `4`
- target pass: `0 / 4`
- Pareto count: `4`

| Candidate | yield_score | loss_score | stability_score |
|---|---:|---:|---:|
| `d4-parent-a` | 64.0 | 30.0 | 9.0 |
| `d4-parent-b` | 58.0 | 20.0 | -7.0 |
| `d4-parent-c` | 39.0 | 18.0 | 44.0 |
| `d4-parent-d` | 29.0 | 6.0 | 51.0 |

| Objective | Range |
|---|---|
| `yield_score` | `29 .. 64` |
| `loss_score` | `6 .. 30` |
| `stability_score` | `-7 .. 51` |

## Generation 1 proposal outcomes

- proposal budget: `5`
- accepted/materialized: `4`
- scientifically evaluated: `4`
- compatibility rejected: `1`
- invalid: `0`
- target pass: `0 / 4`
- Pareto count: `3`
- duplicates: `0`
- novel assignments: `4 / 4`

### Proposal A

- compatibility: `INCOMPATIBLE`
- child: none
- Twin: none
- ScientificResult: none

### Proposal B

- compatibility: `COMPATIBLE`
- candidate: `d5-g1-candidate:sha256:368feb9dbff47c0e25ee646b6e07ac6cb3f2cf72b6d10e593c34c304d8c05803`
- result: `yield_score = 34.0`, `loss_score = 39.0`, `stability_score = 1.0`
- target: `FAIL`

### Proposal C

- compatibility: `COMPATIBLE`
- candidate: `d5-g1-candidate:sha256:6baab165ea9dd0799e3c370a46bf50a73147fa1ed0bf9dc25e1937ff96cad4ae`
- result: `yield_score = 46.0`, `loss_score = 5.0`, `stability_score = 76.0`
- target: `FAIL`

### Proposal D

- compatibility: `COMPATIBLE`
- candidate: `d5-g1-candidate:sha256:b8a794291bfcfef1510c35ab21b9ac56506e8ba7d688a1b227c650306366e72d`
- result: `yield_score = 80.0`, `loss_score = 39.0`, `stability_score = 13.0`
- target: `FAIL`

### Proposal E

- compatibility: `COMPATIBLE`
- candidate: `d5-g1-candidate:sha256:f7cd94af81b7dfc3228e8802cb9b75ca2fa7b8bb44e6f7da60658cb21a003994`
- result: `yield_score = 64.0`, `loss_score = 30.0`, `stability_score = 9.0`
- target: `FAIL`

## Generation 1 summary

| Measure | Observed |
|---|---:|
| proposals | 5 |
| accepted | 4 |
| evaluated | 4 |
| compatibility rejected | 1 |
| invalid | 0 |
| target pass | 0 |
| Pareto count | 3 |
| duplicates | 0 |
| novel assignments | 4 |
| parent-relative improvement count | 2 |
| parent-relative underperformance count | 3 |
| no-inheritance result blocks | 1 |
| no-inheritance status blocks | 1 |
| deterministic round-trip | true |

| Objective | Range |
|---|---|
| `yield_score` | `34 .. 80` |
| `loss_score` | `5 .. 39` |
| `stability_score` | `1 .. 76` |

## Important observed result

Generation 1 produced mixed scientific outcomes:

- some candidates improved preregistered objectives;
- some candidates underperformed relevant parents;
- all Generation 1 candidates failed the overall target;
- Pareto structure changed from `4` Generation 0 members to `3` Generation 1
  members.

This is not a D5 failure. It is evidence that memory-informed proposal is not
guaranteed improvement and that Generation 1 is not optimization.

## Architecture actually pulled

D5 justified local experiment-level representations for:

- `GenerationLineage`;
- `PopulationDerivation`;
- `EvidenceInformedProposal`;
- local `GenerationPlan` identity;
- explicit no-inheritance guard.

These are not frozen as generic Core abstractions.

## System and experiment ownership

The concrete experiment supports keeping these outside generic Core:

- parent selection;
- proposal policy/order;
- diversity policy;
- repair proposal `E`;
- compatibility rules;
- recombination/materialization;
- interaction equations;
- target thresholds;
- exploration fraction;
- accepted population target.

## Targeted test gate

D5 targeted suite against implementation source
`a80defa51df6c773d5bfca275ed9bedf4fee84e2`:

- `tests/test_design_d5_generation.py`;
- `10 passed`;
- `0 failed`;
- `0 errors`.

## Full regression gate

Full repository regression executed against implementation source
`a80defa51df6c773d5bfca275ed9bedf4fee84e2`:

- `1438 passed`;
- `0 failed`;
- `0 errors`;
- `4 warnings`.

The four warnings are the existing known sklearn warnings and are not D5
failures.

## Acceptance criteria

All A1-A23 gates passed.

All N1-N18 adversarial cases passed.

## Adversarial review

### P0/P1

No scientific correctness or evidence-corruption blocker exists.

### P2

No important D5 capability correctness issue remains as a freeze blocker.

### P3

Successor evidence recorded but not fixed in D5:

- repeat lineage/no-inheritance evidence in a non-D4 system before Core
  promotion;
- evaluate whether no-inheritance validation deserves a generic Core boundary;
- proposal identity convergence vs provenance-sensitive identity;
- generic compatibility-rejection artifact representation;
- inherited Core identity/authenticity debt;
- future scaling beyond tiny preregistered populations.

These are successor evidence, not D5 blockers.

## Frozen milestone protection

D5 was completed without modifying frozen D0/D1/D2/D3/D4, ScientificTwin,
MVR0 or MVR1 semantics.

D5-local abstractions were not promoted into Core. D5 did not implement D6,
Bayesian optimization, BoTorch, surrogate models, acquisition functions, active
learning, reinforcement learning, evolutionary frameworks, autonomous loops,
LLM orchestration, databases or UI.

## Frozen boundary

D5 is **complete**.

D5 must not receive further polishing, hardening or successor-milestone
implementation as part of this freeze. Future work belongs to successor
preregistered milestones.

## Frozen outcome

D5 is **PASS / FROZEN**.

The milestone proves the controlled transition from Generation 0 scientific
evidence through D3 memory and D4 compatibility/recombination into one
deterministic Generation 1 population with new scientific evidence, while
preserving the boundary that memory, compatibility, parent results and
generation membership create no inherited scientific truth.
