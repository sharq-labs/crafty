# Crafty — Architecture Status & Strategic Roadmap

## Vision

Crafty is building a **Trusted AI Engineering Simulation Platform**.

The goal is not to replace COMSOL or ANSYS. The goal is to create the trust, reasoning, and execution layer that allows AI agents and engineers to use simulation safely.

---

# Current Position

## Completed Foundations

### Scientific Identity
Crafty can represent:
- Model identity
- Realization
- Solver identity
- Configuration
- Provenance

### Multiphysics Foundation
Supported direction:

Electrical + Mechanical + Thermal + Chemical + Fluid

### Composite Systems
Crafty can represent system-level compositions such as:

Battery → Inverter → Motor → Load → Thermal behavior

### Propulsion
PROPULSION0 / PROPULSION0-EXT established:
- Electrical to mechanical conversion
- Energy reconciliation
- Efficiency analysis
- Operating limits
- Composite system experiments

---

# Trust Architecture

A simulation result is not only a number.

Trusted result:

```
Result
 + Validation
 + Scientific Applicability
 + Admission Decision
 + Execution Identity
 + Reproducibility Evidence
```

Current architecture direction:

```
Solver
  ↓
Numerical Validation
  ↓
Scientific Applicability
  ↓
Admission Decision
  ↓
Consumer
```

---

# Current Milestone

## Execution Identity + Reproducibility Lock

Objective:

Create a trusted execution artifact that can answer:

1. What model ran?
2. Which realization was used?
3. Which solver executed?
4. What inputs were used?
5. What operating conditions existed?
6. What runtime context produced the result?
7. Was it validated?
8. Was it admitted?

Current finding:

A new ExecutionManifest abstraction is not currently forced. Existing provenance, validation, admission, and execution records should be strengthened first.

---

# Reproducibility Strategy

Three levels:

## Level 1 — Decision Reproducibility

Reproduce:
- Accepted
- Rejected

## Level 2 — Scientific Reproducibility

Reproduce:
- Physical conclusions
- Validation results

## Level 3 — Numerical Reproducibility

Exact floating point equality is not guaranteed because of:
- CPU differences
- BLAS implementations
- Runtime differences

Crafty should record and explain these differences.

---

# Current Gaps

## Execution Context
External consumers need enough runtime information to understand how a result was produced without exposing sensitive system information.

## Composite Identity
System compositions must preserve identity:

Battery + Motor + Controller + Thermal

## Trust Path Coverage
Every result consumer must pass through:

Validation + Applicability + Admission

---

# Physics Strategy

Crafty should not become a smaller COMSOL.

Strategic focus:

## System-Level Physics
Own composition, reasoning, and trusted decisions.

## Time / Transient Physics
Important for real systems:

```
t0 → t1 → t2 → t3
```

## Reduced Order Models
Fast engineering models with validity awareness.

## AI-Native Engineering

```
AI Agent
 ↓
Crafty
 ↓
Physics Selection
 ↓
Simulation
 ↓
Validation
 ↓
Trusted Decision
```

---

# Industrial Demo Direction

## EV Traction System

Target:

Battery + Motor + Cooling + Mechanical Load

The objective is not only:

Temperature = X
Efficiency = Y

But:

```
Result
Validation
Applicability
Admission
Evidence
```

---

# Roadmap

## Phase 1 — Trust Foundation
- Execution Identity
- Reproducibility
- Admission completion

## Phase 2 — Composition Identity
- Multi-component identity
- System provenance

## Phase 3 — EV Virtual Laboratory
- Operating scenarios
- Efficiency maps
- Thermal limits

## Phase 4 — Productization
- API
- Dashboard
- Reports
- AI Agent integration

---

# Long-Term Vision

Crafty becomes:

**The trust and intelligence layer that allows AI agents to perform engineering simulation safely.**
