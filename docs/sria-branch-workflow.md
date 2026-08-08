# SRIA Branch Workflow

`main` is the stable integrated project line. It holds known-good scientific
checkpoints and receives merges from `dev` only when the project deliberately
freezes a stable checkpoint.

`dev` is the active scientific development line. Normal SRIA work happens
directly on `dev`, including K2, K3, K4, K5, Decision Engine work, solver
improvements, performance work, experiments, regressions, bug fixes, refactors,
and inference work.

Normal workflow:

1. Work on `dev`.
2. Code, experiment, measure, fix, test, and continue on `dev`.
3. At meaningful stable checkpoints, run final validation.
4. Merge `dev` into `main`.

Do not create a new branch simply because a test failed, a P1/P2 appeared, an
experiment is running, performance is being improved, a new K stage begins, or a
reviewer asks for a fix. Fix it directly on `dev`.

Experiments are identified by preregistration, scientific ID, run/campaign ID,
artifact directory, commit SHA, and result/evidence files. A failed experiment is
evidence/artifact history; it does not require a permanent Git branch.
