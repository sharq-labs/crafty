# Architecture

## Current validated optimizer layer

The current research architecture separates the frozen stacked baseline from the V0.3.3 adaptive path.

```text
Black-box observations
        |
        v
Shared GP model fit
(RBF + Matern-2.5)
        |
        +----------------------+
        |                      |
        v                      v
Identity proposal       Adaptive proposal
(baseline knobs)        (evidence-gated knobs)
        |                      |
        +----------+-----------+
                   |
                   v
          Candidate Safety Arbiter
                   |
                   v
        ONE true objective evaluation
```

The adaptive proposer may become active only from legal online diagnostics derived from evaluated observations and existing model diagnostics. Rescue proposals use the same arbitration path and do not bypass safety checks.

## Core invariants

- no benchmark identity in optimizer decisions;
- no known optimum or `fopt` access;
- no hidden objective evaluations;
- exact objective budget accounting;
- external validation checkpoints remain immutable;
- benchmark infrastructure is evidence infrastructure, not optimizer logic.

## Repository direction

The intended long-term separation is:

```text
engcore/
├── optimization/
│   ├── stacked/
│   └── adaptive/
├── validation/
├── benchmarks/
├── core/
└── cli/
```

This structural migration should happen in a dedicated refactor PR after frozen validation campaigns, so refactoring cannot be confused with algorithmic performance changes.

## Scientific-platform direction

The optimizer is one component of a broader model-independent scientific system. Future layers should be added around, not inside, optimizer logic:

```text
Scientific Problem
      |
      v
Scientific IR
      |
      v
Solver / Simulation Orchestrator
      |
      v
Scientific Result + Validation + Uncertainty
      |
      v
Optimizer / Experiment Selection
```

Numerical truth should come from validated mathematical and scientific solvers. Language models, if used, should remain replaceable planning / explanation adapters rather than sources of numerical truth.
