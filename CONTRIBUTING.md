# Contributing

This repository contains both scientific optimizer research and supporting engineering infrastructure. Changes must preserve reproducibility and keep benchmark evidence separate from implementation decisions.

## Branches

Use focused branches:

- `research/*` — optimizer or algorithm research
- `validation/*` — frozen external replication campaigns
- `feature/*` — product capabilities
- `refactor/*` — structural changes without intended behavior change
- `chore/*` — repository, CI, packaging, documentation
- `docs/*` — documentation only

Do not develop new optimizer behavior on a validation branch.

## Scientific checkpoints

A commit used for an external validation campaign is immutable evidence. Do not rewrite or silently alter its scientific source.

When a new optimizer hypothesis is tested:

1. state the hypothesis before the long benchmark;
2. keep the frozen baseline available;
3. use only legal black-box observations;
4. preserve exact objective-call accounting;
5. report failures and regressions, not only wins;
6. do not tune against holdout results during the campaign.

## Generated artifacts

Do not commit generated COCO / validation / post-processing outputs such as:

- `exdata/`
- `validation_results/`
- `ppdata/`
- Python bytecode / caches

Store concise evidence in documentation and keep raw external campaign artifacts outside normal source history when practical.

## Pull requests

Every PR should be small enough to review and should explain:

- what changed;
- why it changed;
- whether scientific behavior changed;
- what was tested;
- what claim the evidence supports;
- known limitations.

Repository cleanup and scientific behavior changes should normally be separate PRs.

## Testing

Short deterministic self-tests should run before merge. Full COCO/BBOB campaigns are research validation runs and should not be required for every ordinary PR.

Never report a test as passing unless it was actually executed.
