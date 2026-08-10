# D4 - Compatibility / Recombination V0.1 freeze

Status: **PASS / FROZEN**

Milestone ID: `D4`

## Frozen identities

- Previous stable D3 checkpoint: `6abdf279141cf032abdb8052f6ee806c3c264953`
- Frozen D4 preregistration checkpoint: `b4791f5bc825edb6760e60597041ea9c50d06ca4`
- Final tested D4 implementation checkpoint: `300435ce5175bd4c7cd1de8d3df73c32041ef3c1`
- Preregistration: `docs/design-d4-compatibility-recombination-prereg.md`

The D4 preregistration remained **FROZEN BEFORE IMPLEMENTATION** and was not rewritten after observing tests, experiment counts or adversarial review findings.

## Scope actually delivered

D4 demonstrates controlled compatible recombination with exact lineage and mandatory new scientific evaluation.

The experiment justified D4-local representations for:

- selected source records;
- compatibility result;
- deterministic recombination event identity;
- derivation record;
- derived candidate materialization;
- Derived Twin metadata pointer;
- mandatory new child D1 evaluation.

This one synthetic experiment does **not** prove that these representations belong in generic Core.

## System and domain ownership

The concrete experiment supports keeping these semantics system/domain owned:

- compatibility rules;
- compatibility pair matrix;
- adapter requirements;
- component meaning;
- interaction equations;
- target thresholds;
- child materialization semantics;
- system constraints.

## Compatibility and recombination boundary

D4 freezes the following scientific boundaries:

- compatibility is not scientific validity;
- compatibility is not target success;
- compatibility is not good performance;
- compatibility is not model adequacy;
- compatibility is not safety;
- recombination is not optimization;
- parent success is not inherited child success;
- a Derived Candidate is not a scientifically successful Candidate;
- a Derived ScientificTwin is not a validated Twin;
- the child begins with no inherited scientific truth.

The only valid scientific path is:

```text
parent attributable observations
-> compatibility
-> recombination
-> new Derived Candidate
-> new Derived ScientificTwin
-> NEW evaluation
-> NEW ScientificResult
```

## No-inheritance result

D4 demonstrated that:

- parent `ScientificResult` was **not** inherited;
- parent target status was **not** inherited;
- parent Pareto/scoped-elite status was **not** inherited;
- parent validation, UQ, model adequacy and evidence were **not** inherited.

D3 memory was used only as decision provenance for source selection.

## Cases A-D

### Case A

- compatibility: `INCOMPATIBLE`
- child: none
- Twin: none
- `ScientificResult`: none

Scientific conclusion: individually strong parent components can be incompatible and must fail closed before child materialization.

### Case B

- compatibility: `COMPATIBLE`
- child evaluation: `yield_score = 34`, `loss_score = 39`, `stability_score = 1`
- target: `FAIL`

Scientific conclusion: compatibility does not imply good performance.

### Case C

- compatibility: `COMPATIBLE`
- child evaluation: `yield_score = 46`, `loss_score = 5`, `stability_score = 76`
- target: `FAIL`

Observed: the child improved all preregistered objectives versus the relevant parents.

Scientific conclusion: partial-success parents can combine into a child with improved objective behavior, but improvement does not imply target success.

### Case D

- compatibility: `COMPATIBLE`
- child evaluation: `yield_score = 80`, `loss_score = 39`, `stability_score = 13`
- target: `FAIL`

Scientific conclusion: a successfully evaluated compatible child can still fail the overall target.

## Canonical counts

| Measure | Observed |
|---|---:|
| proposed recombinations | 4 |
| compatible | 3 |
| incompatible | 1 |
| invalid | 0 |
| materialized | 3 |
| scientifically evaluated | 3 |
| underperformed relevant parent | 2 |
| improved at least one preregistered objective | 2 |
| compatible but target-failing | 3 |

## Targeted test gate

D4 targeted suite against implementation source `300435ce5175bd4c7cd1de8d3df73c32041ef3c1`:

- `tests/test_design_d4_recombination.py`;
- `8 passed`;
- `0 failed`;
- `0 errors`.

## Full regression gate

Full repository regression executed against implementation source `300435ce5175bd4c7cd1de8d3df73c32041ef3c1`:

- `1428 passed`;
- `0 failed`;
- `0 errors`;
- `4 warnings`.

The four warnings are the existing known sklearn warnings and are not D4 failures.

## Acceptance criteria

All A1-A20 gates passed.

## Adversarial review

No P0/P1/P2 adversarial blocker exists.

### P3

Successor evidence recorded but not fixed in D4:

- inherited non-cryptographic Core identity/authenticity debt;
- generic derivation lineage requires more evidence;
- generic compatibility-result representation requires more evidence;
- generic recombination identity requires more evidence;
- true generic multi-parent `ScientificTwin` lineage requires more evidence.

These are successor evidence, not D4 blockers.

## Frozen milestone protection

D4 was completed without modifying frozen D0/D1/D2/D3, MVR0, MVR1 or ScientificTwin semantics.

D4-local abstractions were not promoted into Core. D4 did not solve generic multi-parent lineage, identity/authenticity debt, population-level generation, memory-informed generation, evolutionary search, adaptive optimization, Bayesian optimization, next-experiment intelligence or autonomous discovery.

## Frozen boundary

D4 is **complete**.

D4 must not receive further polishing, hardening or successor-milestone implementation as part of this freeze.

## Frozen outcome

D4 is **PASS / FROZEN**.

The milestone demonstrates controlled compatible recombination with exact lineage and mandatory new scientific evaluation, while preserving the boundary that compatibility and recombination create no inherited scientific truth and do not imply validity, performance, target success, model adequacy or safety.
