# Summary

Describe what changes and why.

# Scope

- [ ] Scientific optimizer behavior changed
- [ ] Validation / benchmark infrastructure changed
- [ ] Documentation only
- [ ] Repository / CI / packaging only

# Scientific integrity

If optimizer behavior changes, state the exact research hypothesis and affected files.

- [ ] No benchmark-specific selectors were added
- [ ] No BBOB function / instance identity is used by optimizer logic
- [ ] No known optimum / `fopt` access was added
- [ ] Exact objective budget is preserved
- [ ] No hidden objective evaluations were added
- [ ] Frozen baseline behavior is unchanged unless this PR explicitly declares a new baseline

# Validation

List the tests actually executed. Do not claim tests that were not run.

```text
<commands and concise results>
```

For long COCO/BBOB campaigns, link or summarize the external validation record instead of committing generated result dumps.

# Reproducibility

- Base commit / tag:
- Head commit:
- Python version:
- Relevant dependency versions:
- Random seed policy:

# Claims

State the strongest claim supported by the evidence and any important limitation.

Avoid universal-superiority claims unless evidence genuinely supports them.
