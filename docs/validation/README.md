# Validation Evidence

This directory is for concise, reviewable records of scientific validation campaigns.

## What belongs here

For each important campaign record:

- optimizer / baseline identifiers;
- exact commit or tag;
- suite, dimensions, instances, and budgets;
- algorithms compared;
- fairness / budget audit;
- aggregate metrics;
- paired adaptive-vs-baseline evidence;
- catastrophic regressions or failures;
- conclusion and claim boundary.

## What does not belong here

Do not commit large generated COCO result trees, `ppdata`, caches, or temporary diagnostics merely to preserve a benchmark run.

## Interpretation rules

- Use COCO targets / ECDF / ERT for cross-function benchmark interpretation when available.
- Do not average raw objective-value deltas across unrelated BBOB functions because their scales are not comparable.
- Treat paired matched-problem evidence separately from aggregate ranks.
- Report ties and failures.
- A result on one dimension, budget, or instance set is evidence for that tested regime only.
- Never convert benchmark performance into a universal superiority claim.

## Campaign states

Recommended classification vocabulary:

- `SAFE + BENEFICIAL`
- `SAFE + NEUTRAL`
- `SAFE + INFERIOR`
- `ACTIVE + HARMFUL`
- `BROKEN`

A classification should consider the full evidence package rather than one metric alone.

## Frozen validation branches

A `validation/*` branch is a replication surface. Do not tune or refactor optimizer behavior during a campaign. If a scientific source integrity check fails, stop the campaign and investigate before continuing.
