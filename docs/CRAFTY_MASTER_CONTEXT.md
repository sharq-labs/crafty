# CRAFTY — MASTER CONTEXT, STRATEGY & HANDOVER

**Status:** CANONICAL PROJECT CONTEXT  
**Last consolidated:** 2026-09-02  
**Repository:** `sharq-labs/crafty`  
**Original reviewed baseline commit:** `6abdf279141cf032abdb8052f6ee806c3c264953` (`Freeze D3 design memory milestone`)  
**State at this consolidation:** branch `model0r-realization-foundation`, head `68ad1bcaf9ddff70e7c178556ba428e038c67b44` (`MODEL0-R: remove SURROGATE from ModelFormulation`). DATA-BOUNDARY0 is complete and present in the working tree, not yet committed at the time of writing.  

> This document is the source of truth for continuing Crafty across ChatGPT, Claude, Codex, human collaborators, or future sessions.
>
> It intentionally records **technical architecture, scientific philosophy, product vision, commercial goals, funding/acquisition strategy, market positioning, rejected directions, implementation order, and current next step**.
>
> **Do not treat Crafty as only a codebase. The commercial objective is part of the project definition.**

---

# 0. Why this file exists

The project has accumulated a large number of decisions across many discussions. Re-explaining them repeatedly is expensive and risks architectural drift.

From now on:

```text
Chat / AI session = temporary discussion and execution context
GitHub docs        = persistent project memory
```

Any new AI agent or engineer must read this document before proposing major architectural work.

This is a **canonical structured reconstruction of all material decisions and objectives known at consolidation time**. It is not claimed to be a byte-for-byte transcript of every historical chat message.

If a future conversation conflicts with this document, the newer explicit decision must update this file rather than silently diverging.

> **Reading order note, added 2026-09-02.**
>
> **§54–§62 were added on 2026-09-02** and record the current development
> strategy, the two-axis decision model, completed milestone status, the
> current roadmap and the next milestone. **§64 was added later the same day**
> and records the completion of `MIN-FOUNDATION-ET`; it supersedes §62 as the
> current position, and the next milestone is the **ELECTRO-THERMAL VERTICAL
> PROOF**.
>
> Sections 1–53 remain valid as vision, architecture, science and commercial
> context. **Where an earlier section states the current next step or the
> delivery order, §54–§62 and §64 govern.** The affected sections (§30, §41,
> §42, §43, §45, §53) carry an inline amendment note pointing forward.

---

# 1. Founder objective and commercial end goal

Crafty is not being developed only as a research hobby or an academic exercise.

The strategic objective is to build a technically defensible scientific/engineering platform that can eventually be:

1. **Funded** as a deep-tech / engineering-AI company, and/or
2. **Acquired / sold strategically** to a company for which the technology has high strategic value.

The preferred exit is **not** a generic marketplace sale of source code.

Earlier Flippa-style thinking was evaluated and then deprioritized because a marketplace generally rewards proven revenue more than strategic scientific IP.

The intended commercial path is closer to:

```text
Strong scientific IP
        +
Working product
        +
UI + API + MCP
        +
Convincing industrial demonstrations
        +
Scientific benchmarks / validation
        +
optional pilots / revenue
        ↓
Funding or Strategic Acquisition
```

Potential future strategic-buyer categories include:

- CAE / simulation companies
- engineering software companies
- industrial AI companies
- digital twin companies
- EDA / multiphysics companies
- engineering-agent platforms
- large industrial software vendors

Companies previously identified as strategic-fit examples include:

- Cadence
- Siemens
- Synopsys / Ansys
- Dassault Systèmes
- Autodesk
- PTC
- NVIDIA as a potential strategic investor/partner ecosystem participant
- other engineering-AI / scientific-software companies

**No claim is made that any of these companies currently wants to acquire Crafty.** They are examples of organizations whose public strategies overlap with the direction of the technology.

A previous market review ranked **Cadence** as one of the strongest strategic-fit examples because of its active expansion into multiphysics, physical AI and agentic engineering.

---

# 2. Commercial target philosophy

Do not optimize development for a low-value source-code sale.

Optimize for making Crafty:

```text
FUNDABLE
+
ACQUIRABLE
+
TECHNICALLY DIFFICULT TO REPRODUCE
```

The important asset is not merely code volume.

The defensible value should come from the combination of:

- universal scientific contracts
- model validity semantics
- scientific capability planning
- model / realization / solver separation
- cross-domain composition
- multiphysics execution
- uncertainty handling
- evidence / assurance governance
- scientific memory
- closed-loop design and discovery
- deterministic scientific execution beneath AI agents

## 2.1 Indicative valuation thinking discussed previously

These are **planning estimates, not formal valuations or guarantees**.

Historical rough ranges discussed:

### Current / mostly IP stage

- source/IP only: roughly tens to low hundreds of thousands USD depending on buyer
- strategic IP discussion range considered: approximately `$75K–$300K` in the current/early state

### Productized pre-revenue stage

If Crafty has:

- completed architecture
- UI
- API
- MCP
- strong industrial demo
- benchmarks

then prior strategic estimates discussed ranges around:

- `$500K–$2M` depending on quality and buyer

### Strong pre-revenue proof

If Crafty demonstrates multiple very different vertical slices on the same core without domain hacks:

- previous planning range discussed: approximately `$1M–$3M`

### Pilots / external validation

With real company validation or pilots:

- planning discussions moved into approximately `$2M–$7M`

With several paid enterprise pilots:

- approximately `$3M–$10M+` became a conceivable strategic range

With meaningful ARR and growth, traditional SaaS / strategic M&A multiples become more relevant and values can move materially higher.

These ranges must always be re-evaluated against actual traction, buyer interest, IP quality, dependency/licensing risk, scientific proof, team situation and current M&A market.

## 2.2 Key commercial insight

The objective is not:

> "write code worth $1M"

The objective is:

> **build technology that can save or create substantially more than $1M of value for an engineering organization.**

Strategic buyers may then value the technology based on replacement cost, time-to-market, integration value and competitive advantage rather than only MRR.

---

# 3. Funding path

Funding is considered a strong alternative to selling too early.

Potential funding categories discussed:

- deep-tech VCs
- industrial / engineering-AI investors
- accelerator programs
- strategic corporate investors
- scientific/engineering innovation grants where eligible

Examples previously discussed include YC, Techstars and deep-tech grant/investment programs, but no program should be treated as guaranteed or permanently suitable; terms and eligibility must be checked at application time.

If a strong funding offer allows Crafty to reach meaningful industrial proof, funding may be strategically superior to a low acquisition offer.

Illustrative decision logic discussed:

```text
$500K investment with strong upside
vs
$300K acquisition

→ funding may be preferable

$1M+ clean strategic acquisition

→ merits separate serious evaluation
```

No fixed sale threshold is frozen yet.

---

# 4. Market thesis

The market thesis is that engineering organizations increasingly need:

- faster simulation workflows
- AI-assisted engineering
- multiphysics composition
- scientific validation
- automated design exploration
- digital twins
- physical AI
- reliable scientific backends for AI agents

There are already major companies and transactions in this general market, which validates that the problem category is commercially important.

Comparable / adjacent concepts include:

- OpenFOAM
- MOOSE
- Modelica / FMI ecosystem
- PhysicsX
- Neural Concept
- Ansys
- COMSOL
- Siemens / Altair ecosystem
- Dassault Systèmes
- Cadence multiphysics / physical-AI expansion

The existence of competitors is considered **market validation**, not a reason to stop.

However, simply building another multiphysics framework is not sufficient differentiation.

---

# 5. What Crafty should become

The target has evolved beyond optimizer, isolated simulator, or collection of scientific models.

Preferred description:

# **Crafty = Scientific Simulation Operating System**

Also useful:

- Universal Scientific Simulation & Reasoning Core
- Scientific Engineering Intelligence Core
- Scientific execution and decision layer for AI-powered engineering
- Scientific backend for engineering AI agents

The strongest current positioning concept is:

> **Crafty is the scientific execution, composition, assurance and decision layer for AI-powered engineering.**

Crafty should not attempt to memorize every scientific answer.

Instead it should know how to:

```text
represent a problem
↓
identify required scientific capabilities
↓
select compatible scientific models
↓
select computational realizations
↓
select/run solvers
↓
compose multiple physics
↓
validate applicability
↓
quantify uncertainty
↓
produce attributable results
↓
optimize/design
↓
retain scientific knowledge
↓
decide what to do next
```

---

# 6. Core product principle

A critical statement for the entire project:

> **Crafty should not know every answer. Crafty should know how to build, execute, validate and improve a scientific model of a problem.**

Example:

Do **not** build a hard-coded function:

```text
calculate_tire_life()
```

Instead a tire-life request should decompose into concepts such as:

```text
Remaining Useful Life
↓
Wear + Fatigue + Aging
↓
Contact Mechanics
Thermal
Material Response
Load History
Tribology
```

The result should be conditional and uncertainty-aware rather than a magical exact mileage.

---

# 7. Universal architecture principle

The universal core must not contain special-case logic for named products or industries.

**Architecture acceptance rule:**

> If adding a new domain requires writing domain-name-specific conditional logic inside the universal core, treat that as an architecture failure and review the design.

Examples that must NOT appear in universal orchestration logic:

```python
if domain == "radar":
    ...

if system == "air_conditioner":
    ...

if system == "tire":
    ...
```

Domain-specific knowledge belongs in domain/system packs and registered contracts, not universal core branching.

---

# 8. Domain vs System

A major distinction:

```text
Domain = type of physics / scientific capability
System = composition of domains into a real engineered object/problem
```

Examples:

## Tire system

```text
Materials
+
Mechanics
+
Contact
+
Thermal
+
Tribology
+
Fatigue
+
Degradation
```

## Electric motor

```text
Electrical
+
Electromagnetics
+
Mechanical
+
Thermal
+
Materials
+
Controls
```

## HVAC / air conditioner

```text
Thermodynamics
+
Heat Transfer
+
Fluids
+
Refrigeration
+
Electrical
+
Motor / EM
+
Materials
+
Acoustics
+
Controls
+
Optimization
```

## Radar system

```text
Electromagnetics
+
RF
+
Wave Propagation
+
Target Interaction
+
Noise
+
Probability
+
Signal Processing
```

Radar, tire, battery and HVAC should be treated primarily as **system/vertical slices**, not primitive universal domains.

---

# 9. Cross-domain composition is central

One of Crafty's most important future capabilities is cross-domain coupling.

Example electric motor loop:

```text
Electrical
↓
Electromagnetic
↓
Torque
↓
Mechanical
↓
Losses
↓
Thermal
↓
Temperature
↓
Material / resistance changes
↺
```

Example HVAC design trade-offs:

```text
Fan speed ↑
→ airflow ↑
→ cooling may improve

but

fan speed ↑
→ noise ↑
→ electrical power ↑
```

Crafty should eventually handle multi-objective design such as:

```text
Minimize:
- energy consumption
- noise
- temperature
- stress
- cost

Maximize:
- performance
- efficiency
- lifetime
- comfort

Subject to:
- geometry
- safety
- operating limits
- cost
- material constraints
```

This should feed the existing Design / Optimization capabilities and produce Pareto trade-offs.

---

# 10. Scientific Capability Graph

The system should not ask only:

> "Which domain is this?"

The stronger question is:

> **"Which scientific capabilities are required to answer the requested quantity of interest?"**

Proposed reasoning chain:

```text
Question / Goal
↓
Quantity of Interest
↓
Required scientific capabilities
↓
Capability dependencies
↓
Compatible models
↓
Available computational realizations
↓
Required solver capabilities
↓
Executable simulation plan
```

This is referred to as the **Scientific Capability Graph** concept.

It is a core differentiator and should eventually drive automatic scientific planning.

---

# 11. Knowledge Graph vs Physics Execution Graph

Do not conflate knowledge with execution.

Two different graph concepts are required:

## Scientific Knowledge Graph

Contains knowledge such as:

- entities
- materials
- models
- scientific relationships
- capabilities
- validity
- dependencies
- evidence

Potentially very large and extensible.

## Physics Execution Graph

A bounded, explicit, executable graph for one specific simulation/study.

It should be:

- small enough to audit
- deterministic
- versioned/frozen for a run
- explicit about inputs/outputs
- explicit about coupling

The Knowledge Graph may help construct a Physics Graph, but the Knowledge Graph itself is not the simulation runtime.

---

# 12. LLM boundary

Crafty must remain independent of ChatGPT, Claude or any other LLM provider.

LLMs may:

- interpret natural language
- extract engineering intent
- propose candidate problem structures
- explain results
- help research documentation
- act as user interfaces through MCP/API

LLMs must **not** be the authority that:

- computes scientific truth
- certifies a result
- silently chooses invalid physics
- modifies scientific belief directly
- bypasses validity rules
- changes a running Physics Graph without deterministic governance

Target interaction:

```text
User
↓
ChatGPT / Claude / other agent
↓
Structured Scientific Intent
↓
Crafty
↓
Deterministic scientific planning/execution/validation
```

MCP is considered an important future distribution/integration layer so that multiple AI agents can use Crafty as a scientific backend.

---

# 13. Scientific Model != Computational Realization != Solver

This separation is now a major architectural decision.

```text
Scientific Capability
        ↓
Scientific Model
        ↓
Computational Realization
        ↓
Solver Capability
        ↓
Solver
```

Example:

```text
Scientific Model:
Navier–Stokes

Possible realizations:
- analytical / simplified
- reduced-order
- native numerical implementation
- OpenFOAM-based realization
```

The physics must not be defined by the external solver.

A solver is an execution mechanism, not the scientific identity of the model.

This is the motivation for the next proposed milestone `MODEL0-R`.

---

# 14. Fidelity hierarchy

Crafty should eventually reason over fidelity rather than always demanding maximum-cost simulation.

Conceptual fidelity ladder discussed:

```text
L0 Analytical equation
L1 Reduced-order model
L2 Engineering correlation / approximation
L3 Numerical simulation
L4 High-fidelity FEA/CFD/EM
L5 Experimental / calibrated model
```

Selection should depend on:

- required accuracy
- available data
- compute budget
- time budget
- scientific validity
- uncertainty
- risk

The naming and exact implementation must be reconciled with existing Crafty fidelity semantics rather than duplicated blindly.

---

# 15. Unknown / unsupported is a feature

Crafty must never fabricate a scientific answer simply because a user asked for one.

The architecture must preserve distinctions such as:

```text
KNOWN
ESTIMATED
INFERRED
ASSUMED
UNAVAILABLE
UNKNOWN
UNSUPPORTED
```

Future planning should be able to distinguish:

- capability unknown
- capability unsupported
- scientific model unavailable
- computational realization unavailable
- compatible solver unavailable
- required material data missing
- outside validity domain
- insufficient evidence

Example:

```text
Cannot make a reliable tire-life prediction.
Missing fatigue characterization for the material under the requested regime.
```

This is a desired behavior, not a product failure.

---

# 16. Materials / Substance Core vision

Materials must not be modeled as a flat dictionary of constants.

Target concepts include:

```text
Substance
Mixture
EngineeringMaterial
MaterialSample
Composition
Phase
MaterialState
MaterialProperty
MaterialPropertyModel
ValidityDomain
Uncertainty
Provenance
```

Examples:

- gasoline should be represented as a mixture/fuel with composition/state/property models rather than a single chemical species
- coal should be represented as a heterogeneous material/sample rather than `ChemicalSpecies("coal")`
- engineering solids require thermal/mechanical/electrical behavior and constitutive models
- composites require constituents, fractions/orientation and anisotropic/tensor properties

A property must be treated as a contextual scientific claim, conceptually:

```text
Property = f(material, state, temperature, pressure, history, composition, ...)
```

and should carry uncertainty, validity and provenance.

---

# 17. Fields are first-class

For serious PDE/multiphysics work, scalar values are insufficient.

Crafty will need a Field abstraction able to represent concepts such as:

- temperature field
- velocity field
- pressure field
- stress tensor field
- electric field
- magnetic field

Conceptually a Field includes:

```text
Quantity
Unit
Coordinate frame
Spatial representation / mesh
Tensor rank
Time / frequency context
Interpolation semantics
Uncertainty
```

`FIELD0` is therefore a core milestone, not domain-specific infrastructure.

---

# 18. Coupling is a first-class scientific object

Cross-domain coupling is not merely wiring one output to another input.

Serious coupling may require:

- unit transfer
- field transfer
- coordinate transformation
- mesh projection
- time synchronization
- relaxation
- convergence criteria
- rollback
- event handling
- conservation checks
- coupling-error accounting

The Coupler should eventually be a first-class contract/object.

Example:

```text
Model A
↓
Field
↓
Mesh projection
↓
Unit / coordinate conversion
↓
Temporal coupling
↓
Model B
```

---

# 19. Native-first scientific stack decision

The founder prefers Crafty to become scientifically strong without depending on proprietary CAE engines.

Current policy:

> **No proprietary solver is required for Crafty to function.**

And stronger long-term principle:

> **Every essential scientific capability should have a Crafty-native path. External solvers may improve fidelity/performance but must not define the architecture.**

This does **not** mean rewriting every numerical primitive immediately.

General-purpose numerical libraries such as NumPy/SciPy/Pint are acceptable implementation dependencies.

The key distinction is:

```text
General numerical library
→ acceptable internal dependency

External proprietary physics/CAE platform required for Crafty
→ not acceptable as architectural foundation
```

---

# 20. OpenFOAM decision

OpenFOAM is the main external physics solver currently considered acceptable as an optional provider, especially for high-fidelity CFD.

Policy:

```text
Crafty
├── Native scientific/numerical capabilities
└── Optional providers
      └── OpenFOAM for CFD/high-fidelity fluid workflows
```

NOT:

```text
Crafty
↓
OpenFOAM
↓
everything
```

Key phrase:

> **OpenFOAM is a tool available to Crafty; Crafty is not merely a wrapper around OpenFOAM.**

OpenFOAM must adapt to Crafty's solver/realization contracts, not define them.

Proprietary CAE products such as Ansys, COMSOL and PhysicsX should not be required by the core architecture.

They could theoretically receive adapters later if strategically useful, but the current development direction is native-first with OpenFOAM optional.

---

# 21. OpenFOAM-class domain ambition

The founder asked whether each Crafty domain can become as strong as OpenFOAM.

The refined conclusion:

Do not build ten independent OpenFOAM-sized codebases.

Instead build one strong shared scientific/numerical infrastructure and multiple physics engines above it.

```text
                Crafty Scientific/Numerical Kernel
                     /       |       \
                    /        |        \
             Mechanics    Thermal      EM
```

Each domain owns its physics, but **must not reimplement common numerical infrastructure**.

A future domain-engine maturity concept discussed:

```text
D0 — Contract
D1 — Analytical
D2 — Numerical
D3 — Verified
D4 — Validated
D5 — Industrial
D6 — OpenFOAM-Class maturity
```

A high-maturity domain would require more than equations:

- multiple physical models
- multiple numerical formulations
- boundary/initial conditions
- materials integration
- steady/transient support where relevant
- nonlinear regimes where relevant
- convergence testing
- benchmark suites
- experimental/reference validation
- uncertainty characterization
- failure detection
- performance testing
- parallel execution where appropriate
- documentation
- examples/tutorials
- stable extension APIs

It is **not required** that every domain reach D6 immediately.

Depth before breadth is preferred.

---

# 22. Shared Numerical Kernel vision

A major future component is a shared numerical foundation.

Conceptual `NUM0` scope discussed:

```text
Scalar / Vector / Tensor
Dense / Sparse Matrix
Linear systems
Nonlinear systems
Root finding
Integration
Differentiation
ODE
DAE
PDE infrastructure
Mesh
Field
Coordinate systems
Discretization
  - FDM
  - FVM
  - FEM
Time integration
Iterative solvers
Preconditioners
Convergence
Error estimation
Parallelism
```

This does not imply all of the above should be implemented in one milestone.

The numerical kernel must be built incrementally with strong verification.

A future Equation IR concept is important so domains describe physics rather than writing independent solver architectures.

Conceptually:

```text
Domain model
↓
Equation IR
↓
Discretization
↓
Assembly
↓
Numerical system
↓
Solver
```

---

# 23. Mathematical Core

Mathematics is shared infrastructure across all domains.

Long-term mathematical capabilities may include:

- linear algebra
- numerical integration
- ODE / DAE / PDE
- optimization
- root finding
- interpolation
- regression
- Bayesian inference
- Monte Carlo
- sensitivity analysis
- uncertainty propagation
- statistics
- signal processing
- transforms
- geometry

Do not duplicate existing mature Crafty functionality unnecessarily.

---

# 24. Target top-level architecture

Current long-term target:

```text
Crafty Core
├── Scientific IR / contracts
├── Math
├── Materials
├── Fields
├── Geometry / Systems
├── Model Registry
├── Computational Realizations
├── Scientific Capability Graph
├── Solver Registry
├── Physics Graph
├── Solver Orchestration
├── Multiphysics Coupling
├── Simulation Runtime
├── State / History / Degradation
├── Uncertainty
├── Validation / Assurance
├── Evidence / SRIA
├── Optimization
├── Design / Discovery
└── Scientific Memory

Domain Packs
├── Mechanical
├── Structural
├── Thermal
├── Fluids
├── Chemical
├── Electrical
├── Electromagnetic
├── RF / Waves
├── Signal / Probability
├── Acoustics
├── Materials
├── Battery / Electrochemical
├── Controls
└── future domains

System / Vertical Packs
├── HVAC
├── Tire
├── Motor
├── Battery System
├── Drone
├── Aircraft
├── Radar System
└── future systems
```

---

# 25. Current Crafty codebase baseline

At the reviewed baseline commit, Crafty already has significant scientific infrastructure.

Important existing areas include:

- Scientific Core
- typed scientific IR
- units
- model definitions
- validity domains
- model registry
- solver contracts / capabilities / registry
- provenance
- validation semantics
- uncertainty semantics
- experiments
- inference / adequacy capabilities
- optimization research stack
- SRIA
- research decision intelligence
- campaign execution
- Design D0–D3
- Design Memory
- electrical domain work
- thermal domain work
- kinetics domain work
- scientific twin work
- multirotor reference work

The current Scientific Core already contains `ScientificModelDefinition`, typed input/output specifications, validity semantics and `ModelRegistry`.

It also already contains `SolverCapability` and solver-registry concepts.

Therefore the universal architecture should **extend existing abstractions rather than rebuild them**.

---

# 26. Existing scientific philosophy that must be preserved

Important invariants already present in Crafty include:

## 26.1 Numerical convergence != scientific validity

A solver converging does not prove the model represents reality appropriately.

## 26.2 NOT_RUN != PASS

Unperformed validation cannot count as scientific evidence.

## 26.3 Empty validity domain != unlimited validity

Unknown limits must not be interpreted as universal applicability.

## 26.4 Uncertainty must not be invented

Unknown uncertainty is preferable to fabricated precision.

## 26.5 Provenance is mandatory

A number without attribution is not a proper scientific result.

## 26.6 Units remain explicit

Scientific inputs/outputs remain unit-aware; numerical adapters may strip to raw magnitudes only at controlled boundaries.

## 26.7 AI independence

The scientific core must remain usable without any LLM provider.

## 26.8 Domain extension should not require core edits

This principle already exists and should become stronger as Crafty moves toward universal simulation.

> **Clarified 2026-09-02.** The principle targets *domain-specific* edits to
> universal code. Counting edited core lines ("Core Edit Ratio") is only a
> secondary diagnostic; the primary test is the set of semantic questions in
> §59.

---

# 27. SRIA is a differentiator

SRIA should not be discarded during the simulation re-architecture.

Its conceptual evidence flow is:

```text
Candidate Evidence
↓
Critics / Assessments
↓
Arbiter admission
↓
Belief Update Gateway
↓
Scientific Belief
```

Hard invariant:

> **NO SOURCE WRITES SCIENTIFIC BELIEF DIRECTLY.**

Relevant SRIA capabilities already developed include:

- evidence/trust architecture
- computational learning
- assurance
- uncertainty concepts
- research decision intelligence
- bounded sequential campaigns
- persistence/replay concepts

This governance architecture is part of Crafty's differentiation from a simple simulator.

---

# 28. Design / Discovery foundation

Crafty already contains important design/discovery work:

- DesignSpace
- DesignCandidate
- evaluations
- populations
- Pareto archive
- scoped elite
- mixed-variable candidate generation
- study layer
- scientific design memory

D3 Design Memory preserves scientifically useful partial successes rather than only final winners.

Retention concepts include:

- Pareto member
- scoped elite
- near extreme
- near threshold
- diversity representative
- explicit retention

D3 intentionally did **not** yet implement memory-directed generation or full knowledge consolidation.

The long-term goal is to place Design/Discovery **on top of simulation** so Crafty can run closed-loop scientific engineering:

```text
simulate
↓
assess
↓
identify uncertainty / opportunity
↓
design candidates
↓
simulate again
↓
retain useful knowledge
```

---

# 29. Optimizer history / scientific rigor

Crafty has an optimizer research history including:

- V0.2.9 global-first hybrid
- V0.3.0 stacked dual-GP
- V0.3.2 validation lab
- V0.3.3 adaptive optimizer
- V0.3.4 registered ablation

The V0.3.4 campaign was **INCONCLUSIVE** on both primary contrasts.

That negative/inconclusive result is important because Crafty should preserve a culture of scientific honesty rather than forcing superiority claims.

Preregistration, frozen baselines and reproducible testing are part of the project's identity.

---

# 30. Development discipline

> **Amended 2026-09-02.** This workflow remains correct for *executing* a
> milestone. Two clarifications from §54–§56:
>
> * Milestone **selection** is now governed by §54 (risk and reversibility
>   cost), not by position in a layer diagram.
> * The final "Freeze milestone" step is **not** mandatory. A milestone may
>   complete as `PROPOSED` with an evidence record and no freeze document —
>   DATA-BOUNDARY0 did exactly that (§56). Completion and freezing are
>   different axes (§55.3).

New major scientific milestones should follow a disciplined workflow:

```text
Define milestone
↓
Preregister intent / scope / acceptance
↓
Freeze baseline
↓
Implement adjacent layer
↓
Targeted tests
↓
Reference experiment / benchmark
↓
Full regression
↓
Scientific review
↓
Freeze milestone
```

AI-generated code must never be accepted merely because it compiles or its author claims success.

---

# 31. AI-assisted development strategy

The founder has access to extensive Claude usage and wants AI to compensate for being a solo developer.

Recommended role split:

```text
Founder
→ product direction / final decisions

Architecture/review AI
→ architecture, research synthesis, acceptance criteria, critique

Claude / Codex builder
→ implementation, refactoring, tests, documentation

Independent AI reviewer
→ attempt to falsify the builder's implementation

Automated scientific suite
→ final objective evidence
```

Useful pattern:

```text
Claude Builder
↓
Independent fresh-session Claude Reviewer
↓
Adversarial test generation
↓
Automated tests
↓
Reference benchmarks
↓
Human / architecture review
```

Do not ask an LLM to build an enormous subsystem in one prompt.

Break work into small frozen milestones.

---

# 32. Solo-founder constraint

The founder is one person.

This does **not** cancel the large vision.

The execution policy is:

> **Reduce execution scope, not the long-term vision.**

Do not attempt to make every domain industrial/OpenFOAM-class simultaneously.

Instead:

1. build shared universal infrastructure
2. prove it deeply in a small number of domains
3. demonstrate cross-domain composition
4. expand incrementally

The project becomes more feasible because AI can accelerate implementation/review, but scientific validation and scope discipline remain mandatory.

---

# 33. Recommended proof domains / vertical slices

The architecture should eventually be tested on systems that are very different from each other.

Important candidates discussed:

## HVAC / cooling system

Commercially easy to understand and highly cross-domain.

```text
Thermal
Fluids
Electrical
Acoustics
Materials
Controls
Optimization
```

Potential demo objective:

> reduce power consumption and noise while preserving cooling capacity.

This is currently considered one of the strongest early commercial demos.

## Electric motor

```text
Electrical
Electromagnetic
Mechanical
Thermal
Materials
Controls
```

Excellent multiphysics proof.

## Tire

```text
Materials
Mechanics
Contact
Thermal
Tribology
Fatigue
Degradation
```

Strong proof of state/history/material/degradation architecture.

## Battery / energy system

```text
Electrical
Thermal
Electrochemical
Materials
Degradation
Controls
```

## Radar

```text
Electromagnetics
RF
Propagation
Target interaction
Noise
Probability
Signal processing
```

Radar is valuable because it proves the architecture works in a radically different scientific family, but it is not necessarily the first implementation target.

---

# 34. Strong commercial demo concept

A future investor/acquirer should understand Crafty in minutes.

Example:

```text
User:
"Design a cooling system that uses less electricity,
keeps the same cooling capacity,
and produces less noise."

↓

Crafty identifies capabilities

Thermal
+ Fluids
+ Electrical
+ Acoustics

↓

Crafty selects models / realizations

↓

Builds executable physics graph

↓

Runs coupled simulation

↓

Performs design optimization

↓

Returns candidate designs / Pareto trade-offs

↓

Reports assumptions, validity, uncertainty and evidence
```

The critical point is that no `AirConditionerOptimizer` should be hard-coded.

---

# 35. Productization required for funding/acquisition

Even excellent scientific code is difficult to sell if a buyer cannot experience it.

Before serious outreach, Crafty should ideally have:

- clear product UI
- stable API
- MCP server
- architecture documentation
- scientific validation / benchmark reports
- reproducible demos
- dependency/license audit
- clean IP ownership
- automated test report
- short demo video
- acquisition/investor deck
- due-diligence data room

MCP matters because it makes Crafty directly usable by AI agents such as ChatGPT/Claude, but MCP alone is not the value.

The value is the scientific engine exposed through MCP.

---

# 36. Marketing / sales constraint and solution

The founder has explicitly stated that marketing is not a strength and does not want project success to depend on becoming a strong marketer.

For a strategic acquisition, this is manageable.

The eventual process can use a **sell-side technology M&A advisor** or similar specialist.

Conceptual acquisition process:

```text
Crafty prepared for diligence
↓
Valuation / positioning
↓
Buyer universe
↓
Targeted outreach to corp-dev / engineering leadership
↓
NDA
↓
Technical meetings
↓
Competing interest / offers
↓
Negotiation
↓
Due diligence
↓
Transaction
```

Therefore development should focus first on making the asset technically compelling and diligence-ready.

A future M&A advisor can handle much of the buyer outreach and negotiation process.

---

# 37. Why Crafty can be strategically valuable

Crafty's defensible opportunity is **not** merely universal numerical computation.

A stronger interpretation from previous deep research:

> **The defensible opportunity is universal scientific composition and governance.**

This combines capabilities that are often fragmented across tools:

```text
Scientific intent
+
Capability planning
+
Model selection
+
Computational realization selection
+
Solver execution
+
Cross-domain composition
+
Validity
+
UQ
+
Evidence / SRIA
+
Optimization / Design
+
Scientific Memory
```

This is the core strategic thesis.

---

# 38. Adjacent / competing architectures and lessons

## OpenFOAM

Lesson:

- deep domain maturity
- modular scientific software
- runtime-selectable models
- strong numerics/mesh/BC ecosystem
- long-term verification and community development

Crafty should use OpenFOAM as optional CFD capability rather than try to replace it immediately.

## MOOSE

Lesson:

- shared multiphysics infrastructure
- physics modules reuse common kernels / BCs / execution architecture

Crafty should learn the architectural lesson but differentiate through planning, evidence, realization selection, scientific memory and AI-agent backend capabilities.

## Modelica / FMI

Lesson:

- multi-domain model composition and interoperability are already established problem areas

Crafty must offer more than simple component connection.

## PhysicsX / Neural Concept / industrial AI platforms

Lesson:

- engineering AI and simulation acceleration are major funded markets
- AI + simulation + optimization has strong commercial demand

Crafty should not claim to outperform these companies globally without evidence.

---

# 39. Rejected / deprioritized directions

The following approaches have been explicitly rejected or deprioritized:

## 39.1 Do not make Crafty a thin wrapper around proprietary CAE

Ansys / COMSOL / PhysicsX must not be required to make Crafty function.

## 39.2 Do not build all domains at once

Breadth without depth will create fragile pseudo-science.

## 39.3 Do not hard-code product-specific simulators into the universal core

No tire/radar/HVAC special cases in core planning.

## 39.4 Do not let LLMs directly certify science

LLMs are assistants/interfaces, not scientific truth engines.

## 39.5 Do not assume a converged numerical answer is a valid scientific answer

Validity, uncertainty, evidence and convergence stay separate.

## 39.6 Do not optimize for Flippa first

Generic marketplaces are not the strategic target for this asset.

## 39.7 Do not attempt ten OpenFOAM-sized engines independently

Build shared scientific/numerical infrastructure once.

## 39.8 Do not rewrite mature basic numerical work simply for ideological purity

NumPy/SciPy/Pint and similar general libraries can be used where appropriate.

---

# 40. Current architectural conflict discovered

The existing Scientific Core README was written under an earlier philosophy in which numerical algorithms, meshing and discretization were primarily delegated to external scientific packages.

The new direction is more native-first.

This is an **evolution**, not a reason to rewrite the core.

The existing scientific contracts, validity, provenance, solver abstractions and AI-independent philosophy remain highly valuable.

The documentation and architecture should be updated incrementally so Crafty can own a future native numerical runtime while still supporting external providers.

---

# 41. Current next milestone

> **Superseded as the current next step, 2026-09-02.** MODEL0-R's design
> foundation has been delivered (commits `3166cfb`, `68ad1bc`) and is
> `DESIGN-FROZEN` with evidence below `L2` — see §58. The current next
> milestone is `MODEL0-R DIFFERENTIAL PROOF` (§62).
>
> This section is retained because its **statement of the distinction** is
> still canonical.

Do **not** begin by implementing radar, tire, HVAC, FEM, CFD or a large numerical engine.

The immediate proposed milestone is:

# `MODEL0-R — Universal Model / Realization Foundation`

Purpose:

Establish the missing distinction:

```text
Scientific Capability
↓
Scientific Model
↓
Computational Realization
↓
Solver Capability
↓
Solver
```

The existing `ScientificModelDefinition`, `ModelRegistry`, `SolverCapability`, `SolverRegistry`, validity, units, provenance and serialization must be reused rather than duplicated.

MODEL0-R should be additive and backward-compatible.

---

# 42. MODEL0-R intended scope

> **Amended 2026-09-02.** This scope was delivered. One clarification on the
> "Do not implement yet" list below: DATA-BOUNDARY0 moved a solved **field's
> bytes** across a storage boundary (§56). It did **not** define `FIELD0`
> semantics — no shape, support, frame, topology, transfer or interpolation
> exists, and `count` is a count of values and nothing more (§57). The
> deferral of `field` in the list below therefore still stands.

The previously prepared implementation prompt established approximately the following scope:

## Audit first

Review existing:

- scientific models
- solvers
- IR
- results
- serialization
- core documentation
- scientific-core tests
- existing electrical / thermal / kinetics domain patterns

## Add / clarify

- universal `ScientificCapability` identity
- computational formulation classification distinct from epistemic `ModelType`
- fidelity classification only if it does not duplicate existing semantics
- versioned `ModelRealizationDefinition`
- realization registry

## Preserve separation

```text
ScientificCapability != SolverCapability
ScientificModelDefinition != ModelRealizationDefinition
```

## Do not implement yet

- capability graph traversal
- domain resolver
- model resolver
- solver resolver
- knowledge graph
- materials
- geometry
- mesh
- field
- FEM/FVM/FDM
- PDE execution
- multiphysics coupling
- state/history/degradation
- OpenFOAM adapter
- native CFD
- MCP
- UI
- LLM orchestration
- changes to D3

## Completion requirements

- targeted tests
- scientific-core tests
- full repository regression
- no weakened/deleted tests
- backward compatibility evidence
- architecture report
- stop after milestone; do not automatically start the next phase

---

# 43. Long-term milestone sequence

> **Amended 2026-09-02.** This sequence is retained as an **architecture
> work-package catalogue**, not as the delivery order. Delivery is now
> risk-driven and evidence-gated (§54); the current roadmap is §61. The rule
> quoted at the end of this section still holds — the linear ordering does not
> bind.

The exact order may evolve after each preregistered milestone, but the current direction is approximately:

```text
MODEL0-R
Model vs Realization foundation

↓

CAP0
Scientific Capability system / graph foundation

↓

MAT0
Material / Substance / Mixture core

↓

FIELD0
Fields / tensors / coordinates

↓

SYSTEM0
Bodies / components / interfaces / environment

↓

MATH0 / NUM0 foundations
Shared native mathematical/numerical infrastructure

↓

SOLVER0
Native execution contracts/runtime maturation

↓

COUPLE0
Cross-domain / multiphysics coupling

↓

STATE0
Time / state / history / degradation where required

↓

SIM0
General simulation study runtime

↓

UQ0
Uncertainty propagation across composed systems

↓

DISCOVERY0
Design + optimization + memory over simulation

↓

Productization
API + MCP + UI

↓

Industrial vertical slices
HVAC / Motor / Tire / Battery / Radar etc.
```

There have been multiple milestone-order drafts in discussion. The rule is more important than the exact numbering:

> **Build generic contracts and shared execution infrastructure before broad domain expansion.**

---

# 44. Reference acceptance test for universality

A strong architecture proof is to run several systems with radically different physics on the same core.

Example set:

1. HVAC / cooling system
2. electric motor / battery system
3. tire degradation system
4. radar later as a radically different domain family

The core passes the generality test when these can be built primarily through registered capabilities/models/realizations/components/couplings rather than special-case edits to universal code.

---

# 45. Current repository quality / scientific rigor snapshot

Previous reviews characterized Crafty's scientific discipline as a major strength.

Notable baseline data includes:

- D3 full regression around `1420 passed, 0 failed, 0 errors, 4 warnings`
- explicit preregistration/freeze discipline
- negative/inconclusive experiment retention
- provenance
- model adequacy separation
- SRIA assurance / decision layers
- Design Memory

These exact numbers belong to the referenced baseline and should be rechecked after future commits.

> **Updated 2026-09-02.** At DATA-BOUNDARY0 completion the figures are
> `1582 passed, 0 failed` (FULL) and `1087 passed, 495 deselected` (FAST).
> See §56.4.

---

# 46. Known code-quality concerns from previous review

These are not the current priority unless they block the new architecture, but previous review noted examples such as:

- possible shallow immutability in some D3 structures containing mutable mappings
- dual import namespace risk (`src.engcore.*` vs `engcore.*`)
- stale root README/version messaging
- packaging/dependency metadata drift
- serializer hardening opportunities around non-finite JSON
- CI/version coverage improvements
- repository hygiene / generated artifacts

Do not mix unrelated cleanup into a scientific milestone unless necessary.

---

# 47. Product success criteria

Crafty should eventually be able to receive an engineering/scientific objective such as:

> "Design a cooling system that consumes less electricity and creates less noise without reducing cooling capacity."

Then, with deterministic scientific governance, it should be able to:

1. identify the quantity/objectives
2. identify required capabilities
3. discover capability dependencies
4. choose scientific models
5. validate model applicability
6. select computational realizations
7. select compatible solvers
8. build a physics/system graph
9. execute coupled simulation
10. quantify uncertainty
11. assess evidence
12. optimize designs
13. retain useful results in scientific memory
14. explain assumptions and limitations

If evidence or capability is insufficient, it must refuse to fabricate a confident result.

---

# 48. Acquisition-readiness criteria

Crafty should not be considered acquisition-ready only because many tests pass.

A strong strategic package should include:

```text
TECHNOLOGY
- universal architecture
- scientific planning
- cross-domain execution
- UQ / validation / SRIA
- design / optimization / memory

PRODUCT
- UI
- API
- MCP
- reproducible deployment

PROOF
- benchmarks
- validation reports
- 2–3 strong cross-domain demos
- ideally external pilots

DILIGENCE
- clean repository
- clear licensing
- dependency inventory
- IP ownership
- architecture docs
- test evidence
- security / deployment docs

COMMERCIAL STORY
- target buyer problem
- ROI argument
- competitive positioning
- buyer list
- acquisition deck
```

---

# 49. Strategic buyer story

The acquisition story should not be:

> "Crafty has many scientific functions."

A stronger story is:

> **Engineering AI agents can understand language but cannot reliably compose, execute, validate and govern multi-domain physics. Existing solvers are powerful but fragmented by physics/tool/workflow. Crafty is the deterministic scientific composition, execution, assurance and decision layer between AI intent and engineering computation.**

That is the commercial narrative to protect unless future evidence suggests a better one.

---

# 50. Key phrases worth preserving

These phrases capture decisions made during the architecture discussions:

> **Reduce execution scope, not the vision.**

> **OpenFOAM is a tool available to Crafty; Crafty is not a tool built around OpenFOAM.**

> **Every domain owns its physics, but not the shared numerical infrastructure.**

> **Scientific Model != Computational Realization != Solver.**

> **Do not ask only which domain is needed; ask which scientific capabilities are required.**

> **Unknown / unsupported is a valid scientific outcome.**

> **The Knowledge Graph is not the executable Physics Graph.**

> **A converged solver is not automatically a valid scientific model.**

> **The LLM may propose; deterministic scientific systems compute, validate and admit evidence.**

> **If a new domain requires domain-name-specific logic in the universal core, review the architecture.**

> **Crafty's defensible opportunity is universal scientific composition and governance, not simply universal numerical computation.**

> **The goal is not to memorize tire life; the goal is to know how to build a tire-life model from materials, physics and operating conditions and know the limits of confidence.**

---

# 51. Instructions to future ChatGPT / Claude / Codex sessions

Before proposing any significant change:

1. Read this file fully.
2. Inspect the current repository state; do not assume the baseline commit is still current.
3. Identify the last completed frozen milestone.
4. Check whether this document has been updated since that milestone.
5. Preserve all frozen scientific invariants unless the founder explicitly changes them.
6. Do not redesign Crafty from scratch.
7. Do not silently replace the commercial objective with a different product strategy.
8. Distinguish facts from proposals and from speculative valuation estimates.
9. If the repository conflicts with this document, report the conflict before forcing implementation.
10. After an important architectural/business decision, update this document.

Suggested startup instruction for a new AI session:

```text
Read docs/CRAFTY_MASTER_CONTEXT.md completely before proposing or changing anything.
Treat it as the canonical project handover for architecture, science, commercial strategy and current direction.
Then inspect the current repository and report:
1. current code state,
2. latest completed milestone,
3. conflicts with the handover,
4. exact next safe action.
Do not redesign the project from scratch and do not invent missing decisions.
```

---

# 52. Update policy

This file must evolve with the project.

Update it when any of the following changes materially:

- final product vision
- target commercial outcome
- funding vs acquisition strategy
- key buyer positioning
- native-vs-external solver policy
- model/capability architecture
- milestone sequence
- accepted/rejected major design decisions
- completed frozen milestone
- current next step
- major valuation/market assumptions
- a decision's **status** or **evidence level** (§55) changing

Historical scientific milestone reports should remain separate and frozen; this file is the living strategic context connecting them.

---

# 53. Current exact next action at consolidation time

> **Superseded 2026-09-02.** This records the next action as of the
> 2026-09-01 consolidation. MODEL0-R, DATA-BOUNDARY0, the MODEL0-R
> DIFFERENTIAL PROOF and MIN-FOUNDATION-ET have since all completed.
> **The current next action is the ELECTRO-THERMAL VERTICAL PROOF (§64.3,
> §61).** The instruction below not to begin broad domain implementation
> still holds.

**Do not begin broad domain implementation.**

The current intended next development action is:

```text
MODEL0-R
Universal Model / Computational Realization Foundation
```

with backward-compatible extension of the existing Scientific Core.

After MODEL0-R completes and passes targeted + full regression review, reassess and preregister the next milestone rather than automatically continuing.

---

# 54. Development strategy: differential evidence-gated development

**Recorded 2026-09-02.** This supersedes the implicit assumption, present
throughout §41–§43 and §53, that the architecture layer map is also the
delivery plan.

The layer map in §24, and the Layer A–I boundaries in
`docs/architecture-study/07_CRAFTY_ARCHITECTURE_SYNTHESIS_V1.md`, remain
**valid as design structure**. They describe where a concern belongs once it
exists. Nothing in them is retracted.

They are **no longer the delivery roadmap.**

> **Architecture layers != delivery milestones.**

Building the layer map top-to-bottom spends the project's scarcest resource —
a solo founder's execution time — on abstractions whose shape is still a guess,
in an order chosen by tidiness rather than by risk.

## 54.1 The core loop

```text
Risk / architectural hypothesis
        ↓
smallest expensive-to-reverse boundary
        ↓
preregistered proof
        ↓
Consumer A
        ↓
materially different Consumer B when required
        ↓
semantic architecture fitness evaluation
        ↓
adversarial falsification
        ↓
evidence update
        ↓
KEEP / MODIFY / SUPERSEDE / DEFER
```

Each step is already exercised rather than aspirational:

- **Smallest expensive-to-reverse boundary.** Work is selected by what would be
  costly to undo later, not by what comes next in a layer diagram.
- **Preregistered proof.** Hypothesis, fail conditions and predicted results are
  written *before* implementation and are immutable afterwards.
  `docs/data-boundary0-prereg.md` is the reference example.
- **Consumer A / Consumer B.** One consumer *exercises* a contract; it cannot
  *differentiate* it. A second, **materially different** consumer is what
  separates a general boundary from a boundary shaped around its only caller.
  "Materially different" explicitly excludes a second implementation written by
  the same author, on the same day, against the same interface.
- **Semantic fitness evaluation.** §59, not a line-count ratio.
- **Adversarial falsification.** An attempt to break the boundary, bounded by
  the stop rule in §60.
- **Evidence update.** Outcomes are recorded in a separate evidence document
  written *after* execution. Nothing learned afterwards is back-written into
  the preregistration.

## 54.2 Work packages are pulled, not pushed

`CAP0`, `MAT0`, `FIELD0`, `SYSTEM0`, `TOPO0`, `EQIR0`, `DISC0`, `NUM0`,
`STATE0`, `COUPLE0`, `SIM0`, `UQ0`, `DISCOVERY0` and the rest remain **useful
architecture work packages**. Their scoping work is not wasted and their
content is not withdrawn.

They are pulled into delivery **only when a proof or a consumer requires
them**, and then only to the extent that proof requires.

This is a change in *scheduling*, not in architecture.

---

# 55. Two-axis decision model

Every architectural decision carries **two independent statuses**. Conflating
them is how a passing demo becomes a law, and how a well-reasoned distinction
gets deleted for lack of callers.

## 55.1 Decision status — how settled the design is

| Status | Meaning |
|---|---|
| `PROPOSED` | The design exists and is being built on. It may be revised. |
| `DESIGN-FROZEN` | The design is closed to casual revision. Changing it requires an explicit superseding decision. |
| `SUPERSEDED` | A later decision replaced it. Retained for the record, not for use. |

## 55.2 Evidence maturity — how much reality the design has met

| Level | Meaning |
|---|---|
| `L0 REASONED` | Argued. Not executed. |
| `L1 EXERCISED` | Executed against a real consumer. |
| `L2 DIFFERENTIATED` | Executed against two **materially different** consumers that could have disagreed and did not. |
| `L3 STRESSED` | Survived scale, concurrency, latency, hostile input or failure injection. |

## 55.3 The axes are orthogonal

This is the load-bearing part of the model.

- **`DESIGN-FROZEN` does not mean empirically universal.** It is a statement
  about process — the design is closed to casual revision — not a claim about
  physics or about generality.
- **`L0` does not mean the design must remain unfrozen.** A boundary may
  legitimately be frozen on reasoning while its evidence is still thin. That is
  often the right call for a distinction which is expensive to introduce late.
- `DESIGN-FROZEN / L0` and `PROPOSED / L1` are therefore both coherent
  positions, and neither is a contradiction to be repaired.

## 55.4 No stronger status exists

Do not invent `VERIFIED`, `CERTIFIED`, `PROVEN`, `FINAL`, `L4`, or any status
implying evidence Crafty does not hold. If a claim requires a status that is
not in the tables above, the claim is too strong.

## 55.5 Current holdings

| Decision | Decision status | Evidence |
|---|---|---|
| MODEL0-R — Scientific Model / Computational Realization / Solver separation | `DESIGN-FROZEN` | `L2 DIFFERENTIATED`, scoped — see §58 and `docs/model0r-differential-evidence.md` §8 |
| DATA-BOUNDARY0 — scientific data identity vs. storage location | `PROPOSED` | `L1 EXERCISED` — see §56 |
| MIN-FOUNDATION-ET — system composition: which quantity supplies which | `PROPOSED` | `L1 EXERCISED` for the record; `L0 REASONED` for the deferrals — see §64 |
| ET-VERTICAL — closed-loop coupling execution: the plan/outcome records | `PROPOSED` | `L1 EXERCISED` for the executed loop; several claims `L0` or zero — see §65 |
| HETERO-NGSPICE — real external provider substitution: the adapter boundary | `PROPOSED` | `L1 EXERCISED`; the preregistered scoped `L2` was **withdrawn** — see §66 |
| HOSTILE-CORE-STRESS — which distinctions a hostile PDE consumer forces | **none — freezes nothing** | `L0 REASONED` + measured gaps; `L1` for the probe only — see §67 |
| CROSS-DOMAIN-COVERAGE — which gaps are universal across domain families | **none — freezes nothing** | `L0 REASONED` + a measured coverage matrix; `L1` for the probes only — see §68 |
| API-MCP-V0 — the external application boundary: one request/response contract for Direct, HTTP and MCP | `PROPOSED` | `L1 EXERCISED`; `L2` **excluded by preregistration** — see §69 |

---

# 56. DATA-BOUNDARY0 — completed

```text
Decision status:        PROPOSED
Evidence:               L1 EXERCISED
Milestone execution:    COMPLETE
```

**It is not `DESIGN-FROZEN`, and no freeze document was written.** Milestone
completion and design freezing are different things (§55.3). Reading
"complete" as "frozen" is reading the wrong axis.

Records: `docs/data-boundary0-prereg.md` (written before implementation,
immutable) and `docs/data-boundary0-evidence.md` (written after execution).
The resulting contract is documented in `docs/scientific-core/README.md`.

## 56.1 What was demonstrated

Executed against the real solved field of the byte-frozen `Conduction1DSolver`,
at four spatial resolutions:

- a real `Conduction1D` bulk field can leave the scientific control plane;
- `ScientificResult` remains approximately O(1) in bulk field size;
- bulk data can be relocated without changing the scientific result record;
- storage location is not part of scientific data identity;
- corruption, substitution and truncation are detectable;
- missing bulk data is an explicit typed failure, never empty or invented data;
- scalar scientific results remain usable when bulk data is unavailable;
- existing scalar consumers remain compatible, and no existing test, existing
  solver or frozen file was modified;
- `scientific_result` and `raw_solver_output` now use schema `/2`, with
  explicit backward *reading* of `/1` and **loud** failure when an old reader
  meets a `/2` payload.

The schema bump was deliberate: a reader that silently dropped
`data_references` would return a scientific result that understates what was
computed. Loud failure is recoverable; silent understatement of a scientific
claim is not.

## 56.2 The separation this establishes

```text
Scientific Control Plane        engcore.scientific      knows nothing about storage
        !=
Scientific Data Identity        ScientificDataReference content identity,
/ Reference                                             no location
        !=
Runtime / Storage Data Plane    engcore.data            knows locations,
                                                        knows no domain
```

The dependency direction is the load-bearing part and is test-enforced in both
directions: `engcore.scientific` never imports `engcore.data`; `engcore.data`
never imports a named domain pack. Only a domain/orchestration module may
depend on both.

## 56.3 Content identity != scientific equivalence

Recorded explicitly, because the first draft of the evidence overreached here
and was corrected before commit:

> **The digest proves byte-content identity, integrity, relocation stability
> and content addressing. It does not prove numerical or scientific
> equivalence.**

Two computations that are scientifically equivalent to within tolerance will in
general produce **different** digests — hardware, compiler, BLAS, thread count,
reduction order and library version move the last bits without moving the
science. A digest match likewise says nothing about whether either computation
was correct or converged; those remain validation and uncertainty questions on
separate fields of the result.

Tolerance-level comparison of two datasets is a real and different operation.
Nothing in DATA-BOUNDARY0 implements it or substitutes for it.

## 56.4 Regression figures at completion

```text
Targeted (tests/test_data_boundary0.py)      52 passed
FAST     (-m "not expensive")              1087 passed, 495 deselected
FULL                                       1582 passed, 0 failed
```

These belong to this milestone and supersede the older baseline figures quoted
in §45.

---

# 57. What DATA-BOUNDARY0 did **not** prove

These are **known unknowns and deferred evidence, not defects.** Each was
either preregistered as out of scope or recorded honestly afterwards. None is a
repair task.

- heterogeneous **real external provider** — both storage backends were written
  by one author on one day against one interface, which differentiates nothing;
- distributed field ownership;
- large-scale / HPC behaviour;
- GPU / device data;
- remote / object storage;
- shaped or tensor scientific descriptors — `count` is a count of values and is
  deliberately not a shape, mesh, topology or field support;
- `FIELD0` / `TOPO0` semantics — intentionally undefined here;
- transfer / interpolation semantics;
- field uncertainty;
- artifact lifetime and ownership policy at production scale — content
  addressing shares blobs, and there is no retention, reference counting or
  garbage collection.

Also unexercised: non-`float64` dtypes, concurrency, latency, and whether an
empty scientific dataset is ever meaningful (the universal ban on empty data
was removed for lack of evidence either way — an absence of evidence, not
evidence of validity).

**The single thing that would actually raise this to `L2` is a storage backend
Crafty did not write, resolving a reference produced by a solver Crafty did not
write.** Not another in-house backend, and not another domain bridge over the
same two stores.

## 57.1 Process risk discovered

> **Frozen experimental evidence must not imply that production implementation
> is immutable forever.**

`src/engcore/domains/thermal/` is pinned byte-for-byte by three frozen
experiments (T1/T2/T3) because those experiments measured a property of that
exact solver. Pinning is the correct way to protect an experimental claim. It
is **not** a correct way to own production code indefinitely: a defect in a
frozen file today has no sanctioned repair path, and the pin does not
distinguish *"this evidence is about this code"* from *"this code may never
change"*.

DATA-BOUNDARY0 worked *around* the freeze — the bulk path is a bridge module
beside the frozen tree — which was right for a spike and is not a general
answer.

**No unfreeze mechanism is designed here, and none should be improvised.** This
is logged for whichever milestone next needs to change a frozen tree.

---

# 58. MODEL0-R status

The architectural distinction stands and must be preserved:

```text
Scientific Model
        !=
Computational Realization
        !=
Solver Capability
        !=
Concrete Solver
```

```text
Decision status:   DESIGN-FROZEN
Evidence:          below L2
```

The design boundary is `DESIGN-FROZEN`. Its empirical evidence is still below
`L2 DIFFERENTIATED`: one scientific model has not yet been executed through two
materially different realizations.

> **Do not reopen or delete the boundary merely because consumers are sparse.**

Sparse consumers are a statement about evidence maturity, not about design
validity (§55.3). The cost of introducing this separation late — after models,
results and serialized records have assumed the two are one thing — is exactly
why it was made early.

## 58.1 Taxonomy members remain provisional where unexercised

Freezing the *boundary* does not freeze every *member* of every enumeration
inside it.

`ModelFormulation` (`src/engcore/scientific/realizations/definition.py`):

- `ALGEBRAIC`, `ODE`, `DAE`, `PDE` — defensible current members.
- `DISCRETE` — **under-defined and provisional.** It must be clarified by a
  real consumer, or removed, **before anything is allowed to rely on it.**

`SURROGATE` was already removed (commit `68ad1bc`) because it answers a
different question — *by what strategy a realization was obtained*, not *what
mathematical form is posed*. Surrogate character is deferred, not renamed.

**`ModelFormulation` is not redesigned by this documentation update.** The
record above states what is provisional; changing it requires its own decision
and its own consumer.

---

# 59. Architecture fitness evaluation

## 59.1 Core Edit Ratio is a secondary diagnostic

Counting edited lines of universal core when a new domain arrives is cheap and
occasionally informative. It is **not** the measure of architectural fitness
and must not be used as an acceptance gate on its own.

It is easy to score well on it while doing architectural damage — a
domain-aware branch is very few lines — and easy to score badly on it while
doing something correct: DATA-BOUNDARY0's schema `/2` bump touched core
deliberately, after review, and was the right call.

## 59.2 The primary questions are semantic

When a new consumer or domain is added, ask:

1. Did a frozen core contract or schema require change?
2. Did existing serialized records require migration?
3. Was a domain-specific branch added to universal core?
4. Did provider identity leak into scientific semantics?
5. Was untyped metadata used as an escape hatch?
6. Was an existing abstraction duplicated outside core instead of reused?
7. Was a new semantic abstraction required?
8. Was a frozen invariant violated?
9. Could the consumer have been implemented from the **published contract**
   alone, without knowledge of core internals?

A "yes" to 1–6 or 8, or a "no" to 9, is a finding that must be explained. It is
not automatically a failure, but it is never something to pass over silently.

**No CI enforcement of all of this is implemented, and none is required by this
update.** A few individual questions are already test-enforced in narrow places
— the two dependency-direction tests, and the `artifacts`-channel fitness test.

---

# 60. Review stop rule

For a high-impact architecture decision:

- **at most two adversarial reasoning / review rounds;**
- if material uncertainty remains after those two rounds, **obtain executable
  evidence through a spike** rather than a third round of argument.

> **Architecture argument must not substitute indefinitely for evidence.**

Round three and beyond of adversarial reasoning reliably produces more prose
and no more knowledge. A spike that costs a day settles what a week of review
cannot.

---

# 61. Current roadmap — risk-driven

```text
MODEL0-R                              ✅ design foundation exists
                                         DESIGN-FROZEN / evidence < L2
        ↓
DATA-BOUNDARY0                        ✅ PROPOSED / L1 EXERCISED
        ↓
MODEL0-R DIFFERENTIAL PROOF           ✅ DESIGN-FROZEN / L2 DIFFERENTIATED (scoped)
        ↓
MINIMUM FOUNDATION required by the coupled proof
                                      ✅ MIN-FOUNDATION-ET — PROPOSED / L1 (§64)
        ↓
ELECTRO-THERMAL VERTICAL PROOF        ✅ ET-VERTICAL — PROPOSED / L1 (§65)
        ↓
HETEROGENEOUS REAL PROVIDER PROOF     ✅ HETERO-NGSPICE — PROPOSED / L1 (§66)
        ↓
API / MCP v0                             <- next
        ↓
CROSS-ARCHITECTURE HOSTILE PROOF
        ↓
HVAC commercial vertical
        ↓
domain expert validation + V&V / UQ / benchmarks
        ↓
killer demo / pilot / commercial process
```

**This is a risk-driven roadmap, not a frozen sequence.** Later evidence may
reorder it.

"MINIMUM FOUNDATION required by the coupled proof" is deliberately not
enumerated in advance: which of `MAT0`, `FIELD0`, `SYSTEM0`, `TOPO0` or `EQIR0`
gets pulled in, and how much of each, is decided by what the electro-thermal
proof actually requires (§54.2).

The layered sequences in §43 and in the architecture study remain the
work-package catalogue this roadmap draws from.

---

# 62. Current next milestone

# `MODEL0-R DIFFERENTIAL PROOF`

**Primary question:**

> Does the separation between Scientific Model, Computational Realization and
> Solver carry **independently useful information** when ONE scientific model
> is executed through TWO materially different realizations?

This is the `L1 → L2` step for MODEL0-R (§55.2): two realizations of the same
scientific claim that could have disagreed, where the model record stays fixed
and the realization record is what changes.

**Not implemented by this documentation update.** It requires its own
preregistration, written before any source file is added or edited, following
§54.1.

---

# 63. Final project intent

Crafty is being built toward a future where a user or AI agent can state a scientific/engineering objective, while Crafty provides the deterministic scientific machinery required to transform that intent into a defensible simulation/design workflow.

The long-term product should combine:

```text
Scientific representation
+
Capability planning
+
Model validity
+
Computational realization selection
+
Native / optional solver execution
+
Cross-domain composition
+
Multiphysics
+
Uncertainty
+
Evidence / SRIA
+
Optimization / Design
+
Scientific Memory
+
Agent integration through API/MCP
```

The founder's commercial objective is to convert this into **high-value strategic scientific software/IP capable of attracting funding and/or acquisition interest from serious engineering/industrial software companies.**

That objective is part of Crafty's definition and must not be lost when technical work resumes.

---

# 64. MIN-FOUNDATION-ET — completed

```text
Decision status:        PROPOSED
Evidence:               L1 EXERCISED (one abstraction) / L0 REASONED (the deferrals)
Milestone execution:    COMPLETE
```

**Supersedes §62 as the current position.** Records:
`docs/min-foundation-electrothermal-prereg.md` (written and committed before
implementation, immutable) and `docs/min-foundation-electrothermal-evidence.md`
(written after execution). The contract is documented in
`docs/scientific-core/README.md`.

## 64.1 The question and the answer

> What is the **minimum** semantic foundation a real two-way electro-thermal
> consumer *forces*, over and above what Crafty already has?

**Exactly one universal record: `QuantityDependency`** — *the quantity named X
of problem P supplies the quantity named Y of problem Q*, with a dimension.
Eleven of twelve candidate FOUNDATION1 abstractions were deferred; three
designed abstractions were reduced away during implementation and the
adversarial pass.

The null hypothesis lost **on a measurement, not an argument.** The whole
consumer was first built with zero new contracts and one open-loop pass run,
then a records-only reader was asked to recover the wiring:

```text
target                                 dimensionally admissible sources
resistance-tcr-R1 :: temperature                                      5
thermal-lumped-R1 :: heat_input                                       4
thermal-lumped-R1 :: ambient_temperature                              5
electrical … :: R:R1              not detectable at all — a configured
                                  ScientificParameter carrying a value
```

Had any count been 1, no contract would have been added.

## 64.2 What was demonstrated

Real numbers, one resistor self-heating on a lumped body: `T₀ = 300 K`,
`R(T₀) = 10.269205 Ω`, `P = 2.434463 W`, `T₁ = 344.272271 K`,
`R(T₁) = 12.009105 Ω` — **+16.94 %**. One electrical solve, one thermal step,
**no coupled solve**, and the feedback resistance deliberately not fed back.

* Both directions are in the records: electrical → thermal directly, thermal →
  electrical **through a material property**, which is the scientifically
  correct route.
* `ProvenanceRecord.bindings` at **arity 5** over 3 solvers and 2 realizations —
  the first multi-solver record in the repository, and the shape
  `model0r-differential-evidence.md` §9.1 named as untested.
* `required_capabilities` exercised for the first time — and found to be
  **asymmetric by physics**: R(T) genuinely requires a temperature, while a
  lumped balance is satisfied by any heat source, so the capability layer can
  express one direction and structurally cannot express the other.
* A domain can require another domain's science **by identifier without
  importing it**.
* Two measured findings about existing contracts: the electrical domain folds a
  resistance into circuit identity, so a temperature-updated resistor is refused
  as a different system; and `ScientificModelDefinition.check_against` cannot
  bind a reusable model to a multi-instance problem, which is why the DC domain
  does not use it.

## 64.3 What it did **not** establish

Recorded prominently because §55.3 makes evidence and design status orthogonal,
and this milestone's evidence is thinner than its conclusions.

* **The eleven deferrals are `L0 REASONED`, not exercised.** Absence of a class
  is not evidence the concept was not needed. The component-instance deferral in
  particular was confronted and then blocked: the system pack's constructor
  forecloses the 2:1 case, so the fan-in gap is measured at record level instead.
* **`ScientificTwin` as instance authority gained zero evidence.** The twin here
  is a derived record that nothing reads. The preregistration overstated this
  and the evidence document corrects it.
* **Nothing about arity > 1, fan-in combination, bidirectional flow, acausal
  composition, fields, tensors, external providers, concurrency or scale.**
  A directed scalar dependency is strictly weaker than the across/through
  connector pair that Modelica's own specification records as insufficient for
  convective transport — the honest limit on the fluid/HVAC direction.
* **"No domain leakage" is a lexical claim.** The adversarial pass found a
  structural leak — an initial-value-problem assumption inside a universal core
  reader — that contained no domain word and no scan could have caught. It was
  fixed; the lesson is about what the test measures.

`architecture-falsifier` returned **SURVIVES WITH REQUIRED CHANGES**, no
`BLOCKER`. Its one `BREAKING-RISK` — an endpoint name that denoted two different
time levels of one quantity — was closed before commit, when it cost a rename
rather than a schema bump against an exact-match reader.

---

# 65. ET-VERTICAL — completed

```text
Decision status:        PROPOSED
Evidence:               L1 EXERCISED (the executed loop); several claims L0 or zero
Milestone execution:    COMPLETE
```

Full record: `docs/electrothermal-vertical-prereg.md` (immutable, committed
before implementation) and `docs/electrothermal-vertical-evidence.md`. **Not a
freeze.**

**The first genuine closed-loop multiphysics execution in the repository.**
`MIN-FOUNDATION-ET` represented the electro-thermal loop and stopped one
electrical solve short of closing it. This milestone closes it: iteration *n ≥ 2*
solves the electrical problem at a resistance the previous thermal solve
produced.

## 65.1 Zero new universal records, decided by a measurement

`architecture-decision-reviewer` compared six options and selected **A** —
domain-level orchestration, everything in the electro-thermal **system pack**,
nothing in `engcore/scientific`. The decision rested on a count, not an argument:

| Gate | Question | Result |
|---|---|---|
| **G0** | Is the declared dependency set executable as declared? | **0** admissible topological orders, **3** admissible tears, **0** seed-supplying records per tear |
| **G1** | Does anything under `engcore/scientific` read coupling-execution information? | **0** executable identifiers (19 lexical occurrences over 18 lines, all prose declaring the reader's absence) |

G0 says four facts are genuinely missing from the records — which edges are cut,
what value each cut edge's target takes first, when to stop, how long to try.
G1 says no *universal* consumer of those facts exists. `MIN-FOUNDATION-ET` added
its one universal record because a count showed no reader could recover the fact;
there is no analogous count here, so the records are pack-local and the
**promotion criterion is preregistered**: a second, materially different coupled
consumer written against them without editing them.

**No file under `src/engcore/scientific/` was added or edited.** The only
pre-existing file touched anywhere is one system-pack `__init__.py`: +48 lines,
exports only.

## 65.2 What was demonstrated

Ten executed cases, every preregistered analytic prediction reproduced, none
adjusted.

* **The loop closes.** CASE A converges in 10 iterations to `T* = 338.577018 K`,
  `R* = 11.785282 Ω`, `P* = 2.121290 W`. **Iteration 1 reproduces
  `MIN-FOUNDATION-ET`'s open-loop pass to `rel=1e-12`; iteration 2 is the second
  electrical solve that milestone refused to perform**, consuming the
  `R(T₁) = 12.009105 Ω` it computed and threw away.
* **The transported endpoint carries the physics, not its dimension.** Switching
  the source from `final_temperature` to `steady_state_temperature` — **one field
  of one record, no code change** — moves the converged answer by **3.376418 K**.
  Both endpoints are kelvin, both check clean; only the enumerated name separates
  them. This is the executed consequence of `MIN-FOUNDATION-ET`'s D-1 rename.
* **Coupling convergence ≠ numerical convergence.** CASE C2 runs a negative-TCR
  conductor at its double root, where `|g'| = 1` exactly: **50 iterations, every
  sub-solve reporting success, every iterate inside the model's declared validity
  domain, and coupling convergence `False`.**
* **Coupling convergence ≠ scientific validity.** CASE F converges to
  `T* = 498.994793 K` with every sub-solve passing, while
  `assess_resistance_validity` reports `OUTSIDE_VALIDATED_DOMAIN` — the model's
  declared range is 200–450 K. Three independent verdicts, one run.
* **Arity 2 does not force a component-instance concept.** Two conductors in
  series, two bodies, one circuit: converges in 8 iterations, six distinct
  endpoints, no aliasing — because the *electrical domain* names per instance and
  the dependency record never parses the name.
* **No relaxation was required, and a closed form says why.** For a linear-TCR
  conductor with `α > 0`, the fixed-point map contracts **exactly when** the
  resistance is positive at ambient — the same condition. Every configuration
  that would diverge is already refused by the domain as unphysical. Measured
  against the closed form to 1 % in three configurations.

## 65.3 What it did **not** establish

* **H0(B) partially won.** The falsifier proved the loop carried an unstated
  structural assumption — *at most one incoming edge per endpoint* — true of
  exactly the 1:1 topology built first. Two sources on one target resolved
  silently to the last declared, and the run still reported convergence on a
  different physical system. **It contains no domain word, so the AST scan
  structurally could not see it.** This is `MIN-FOUNDATION-ET` finding C-2
  reproduced one layer out. Closed before commit by **refusing** the plan, not by
  inventing a combination rule.
* **`ScientificTwin` as instance authority gained zero evidence for the second
  consecutive milestone.** The twin is built and read by nothing; the test that
  asserts it is not the runtime state could not have failed.
* **`CouplingOutcome` lost its own reduction.** At two members a boolean
  reproduces every assertion. It is kept on a naming argument recorded at `L0`,
  and is the first candidate for deletion.
* **One runner exists.** `QuantityDependency` is now executed rather than
  declared, at arity 2, which strengthens it *within* `L1`. It is not
  differentiation.
* **Nothing about fan-in combination, mixed-dimension norms, fields, tensors,
  acausal or runtime-directed transport, external providers, concurrency,
  restart, or more than two domains.** Each is refused, declared, or absent.

`architecture-falsifier` returned **SURVIVES WITH REQUIRED CHANGES**, no
`BLOCKER`. **Three `BREAKING-RISK` findings, all closed before commit** — the
fan-in resolution above; a field named `converged_values` that held an
unconverged iterate on a budget-exhausted run; and a `"{problem}::{quantity}"`
key whose components already contain colons. Eight further findings were fixed
or measured, including an exported graph reader that reported every edge of a
cyclic graph as lying on the cycle.

Regression: **FULL 1682 → 1744**, FAST 1187 → 1249. No pre-existing test edited.

---

# 66. HETERO-NGSPICE — completed

```text
Decision status:        PROPOSED
Evidence:               L1 EXERCISED (provider boundary); scoped L2 WITHDRAWN
Milestone execution:    COMPLETE
```

Full record: `docs/heterogeneous-ngspice-prereg.md` (immutable, committed before
implementation) and `docs/heterogeneous-ngspice-evidence.md`. **Not a freeze.**

**The first execution path in the repository run by code Crafty did not write.**
Real `ngspice-42` (Ubuntu `noble/universe`, KLU direct solver), reached as
`wsl.exe -e ngspice`, substituted for the native MNA solver — standalone and
inside the electro-thermal coupled loop.

**ngspice was absent from the machine.** Discovery found nothing anywhere, and
execution **stopped** rather than proceeding with a mock; it was installed only
with explicit authorization. The alternative would have made every number below
worthless.

## 66.1 What was demonstrated

* **Standalone equivalence to `2.776e-16`** worst relative difference across all
  13 metrics — machine epsilon, seven orders inside the preregistered `1e-9`.
* **Coupled substitution below coupling semantics.** `ET-VERTICAL`'s
  `run_fixed_point` takes the dispatch table as data, so the substitution is
  **one dict entry**. `coupled.py` is byte-unchanged; there is no
  `native_coupling()`/`ngspice_coupling()` pair. CASE A and CASE E agree to
  `6e-13 K` and `9e-12 K`, with identical iteration counts and identical
  coupling outcomes.
* **Crafty's validity authority applied to a foreign answer.**
  `build_validation_report` is coupled to the native solver's internals, but
  `assemble` is *"pure assembly, no solving"* — so ngspice's solution is
  substituted into the MNA system **Crafty assembled itself**, giving a
  `linear_system_residual` of `1.11e-16`. Verification against the domain's
  equations, not against the provider's own arithmetic.
* **Zero universal-core change**, no schema bump, no new model, no
  `ConvergenceState` member, no provider framework. Core's own docstrings
  already named ngspice three times as an anticipated adapter target, and
  `PreparedSolve.payload` already named *"a compiled netlist"* as its home.
* **Failure taxonomy holds.** Provider failures raise a non-`ScientificCoreError`
  and synthesise no result; a genuine ngspice exit 1 and a missing requested
  quantity are both exercised.

## 66.2 Falsified once, and better for it

`architecture-falsifier` returned **FALSIFIED**: one `BLOCKER`, six
`BREAKING-RISK`, **all closed before commit**.

The `BLOCKER` is the milestone's most valuable finding, and it is a
**reasoning error in the preregistration**. Prereg §9.3 predicted that ngspice
returns a complete set of zeros with exit 0 on a singular circuit, and concluded
that *"every available repair is worse"* — having enumerated two. The
enumeration was incomplete. The decisive fact it missed: **the zero vector is an
exact solution of Crafty's own assembled `A x = z`**, so no check over `(A, x)`
could ever detect it — only `rank(A)` can, and `validate` **already assembles
`A`**. The repair was sitting in an object the adapter constructed anyway.

The two paths now agree on the **science** and differ only on the **numerics**:
native reports `FAILED`/`FAIL`, ngspice reports `CONVERGED` (the provider did
return a complete set) with `validation=FAIL`. A precondition the platform had
*declared but never checked on either path* is now checked.

Two further findings worth carrying: `resistor_power:` — a declared coupling
endpoint — was the only provider-sourced metric no check read, and is now
reconciled against Crafty's own relations; and a shared realization capability
that none of its three records actually provided was replaced by three truthful
ones, after `RealizationRegistry.providing()` was identified as a real consumer
that would have been misled.

## 66.3 What it did **not** establish

* **The scoped `L2` was withdrawn.** The preregistration permitted it for
  `Realization != Solver`, and it is **not claimed**: the native `solve_circuit`
  predates `MODEL0-R` and writes no bindings, so the "two solvers, one
  realization" record exists only inside the test, constructed by the proof.
  What is earned is real — two materially different solvers, one external,
  executed the same three realization records and agreed to `2.8e-16` — but no
  record the *system* produces states it. `MODEL0-R` is not upgraded.
* **Session-stateful providers are sidestepped, not answered.** Process-per-solve
  destroys session state; `ET-VERTICAL` §15.6 named this the sharpest edge and
  it remains open.
* **One provider, one version, one build, one platform, two circuits.** Nothing
  about portability, asynchrony, concurrency, remote execution, field-valued
  output, or a second provider.
* **`ModelRealizationDefinition` cannot state a joint realization.** One DC
  analysis invokes three models that MNA discharges together; the record's
  single `model` field cannot say so. Carried forward as a candidate reopen
  trigger for a `DESIGN-FROZEN` contract, not repaired.

## 66.4 Post-acceptance correction

One further provider-admission risk was closed after the milestone was accepted,
without reopening its architecture. `resistor_power:*` is provider-sourced and
transports directly into `heat_input`; §8.2 D1 had added a *reporting* check for
it. Measured: a provider halving its reported power produced
`validation_status = FAIL` **and the coupling loop transported it anyway**,
converging 18.05 K from the truth — because the loop reads values, not reports.

The reconciliation moved to `extract_metrics`, where provider numbers become
Crafty metrics, and a violation now **raises** `NgspiceExecutionFailure`, so no
result exists to transport. Two independent relations, neither comparing the
power against itself: `I ≈ V_drop/R` (provider voltage against Crafty's
*declared* resistance) and `P ≈ V_drop·I` (three separate provider channels),
plus a passive-sign guard. Four negative cases execute, including the corrupted
provider inside the coupled loop.

**The lesson is general and worth carrying: a check whose only effect is a field
nothing consults is not a guard.**

Regression: **FULL 1744 → 1784**, FAST 1249 → 1262. No pre-existing test edited;
the one edit to `tests/conftest.py` adds tier labels and changes no assertion.

---

# 67. HOSTILE-CORE-STRESS — completed

```text
Decision status:        none — this milestone freezes nothing
Evidence:               L0 REASONED + measured gaps; L1 EXERCISED for the probe only
Milestone execution:    COMPLETE
```

Full record: `docs/hostile-core-domain-stress-prereg.md` (immutable, committed
before implementation) and `docs/hostile-core-domain-stress-evidence.md`. **A
discovery/falsification milestone: no architecture was implemented, and none may
be inferred as approved from it.**

**Ran ahead of `API / MCP v0`**, which §61 permits as a risk-driven reordering.
The deviation is recorded in the preregistration rather than assumed.

## 67.1 The consumer, and why it

`architecture-decision-reviewer` compared five options and selected **1D
transient advection-diffusion** — `∂c/∂t + u ∂c/∂x = D ∂²c/∂x²`, `Pe = 40`,
three frozen cases, two discretizations. A lumped pipe network lost because it
is **isomorphic to the existing `electrical/dc` MNA domain** and so differences
against nothing. A 2D Navier-Stokes skeleton lost on confounding and cost. **2D
scalar transport in a prescribed velocity field lost narrowly**, on one recorded
judgement: its extra pressures target concepts already deferred at `L0`, while
the selected consumer attacks records that exist, are frozen, and had never been
exercised. That judgement carries a preregistered reversal condition.

## 67.2 What was measured

A records-only reader — forbidden by AST scan from importing the probe's domain
— was handed serialized payloads and counted admissible readings, reproducing
`MIN-FOUNDATION-ET` §64.1's instrument. A **steelman encoding was binding**: no
gap could be declared before a maximal honest attempt in existing typed
contracts, because the repository's only PDE domain routes *around* those
contracts (**`BoundaryCondition` has zero producers anywhere in
`src/engcore/domains/`**).

**The two central gaps, both Ledger 1:**

* **Boundary records are not injective onto physical systems.** Reversing the
  transport direction leaves **every serialized `BoundaryCondition`
  byte-identical** while flipping which end is the inflow: 2 admissible
  readings. The fallback *"Dirichlet means inflow"* is killed by the probe's own
  steady case, which has Dirichlet at both ends. **Universal beyond PDEs** —
  §66.4's passive-sign guard needed the same distinction for a two-terminal
  lumped element with no topology anywhere.
* **`validity_context` cannot see structural facts about a problem**, so no
  declarative criterion can reference how many conditions were declared, and no
  model can enumerate the conditions its equation requires
  (`InputSourceKind` has two members, neither a condition).

**What already works, recorded with equal prominence:** `ExecutionBinding`
recovers the realization identity exactly as `MODEL0-R` intended;
`is_time_dependent` is correct once a domain writes real `InitialCondition`
records — the defect is in the *baseline domain*, not the contract;
DATA-BOUNDARY0's storage independence holds unchanged under a field-valued
consumer; and the `MIN-FOUNDATION-ET` repair to `unresolved_inputs` survived the
shot aimed directly at it.

## 67.3 Falsified once, and substantially better for it

`architecture-falsifier` returned **FALSIFIED**: three `BLOCKER`s, three
`BREAKING-RISK`s, **all closed before commit**. The measurements survived; the
**claim layer** did not.

* **The two-ledger rule was blending ledgers.** It booked a finding by *which
  record was inspected* rather than *which record the missing concept belongs
  to*, so one absent concept was Ledger 1 under one question and Ledger 2 under
  another. Closed by stating the rule — *Ledger 1 only when **both** the
  measurement and the remedy live in a record that exists* — and splitting the
  orientation finding accordingly.
* **A claimed dilemma was a false dilemma.** The milestone asserted that no
  encoding gives both a typed mesh-dependent validity criterion and a mesh-free
  problem identity. `ProvenanceRecord.inputs` does — a typed
  `Mapping[str, Quantity]` the probe **already populated**. Withdrawn and
  replaced by the residual that survives: such a criterion is assessable
  **per-run and never pre-run**, which generalizes verbatim to CFL, Courant, y+
  and element aspect ratio.
* **An inexpressibility claim the preregistration had pre-committed not to
  make.** The probe's prose said the platform could not express a physical
  admissibility check. It can, today, with no contract change — so the probe now
  writes it and executes it. What survives is an **asymmetry**: a domain can
  record an admissibility *violation* and structurally cannot record its
  *attainment*, because no `ValidationLevel` member names it.

**One finding was withdrawn outright.** The milestone reported that at `D = 0`
an infinite cell Péclet number cannot be expressed, since `Quantity` refuses
non-finite magnitudes. It is a property of the author's chosen parameterisation,
not of the contract: `Pe ≤ 2` and `1/Pe ≥ 0.5` are the same criterion and the
reciprocal is finite. **`Quantity`'s invariant survives intact.**

**The lesson worth carrying: an instrument that produces counts can itself be
wrong, and this one was — twice — in the direction of flattering its own
hypothesis.** Both errors were false gaps, and both were caught by asking which
typed channel had not been tried.

## 67.4 What it did **not** establish

* **`FIELD0` / `TOPO0` gained nothing.** Every field-semantics finding is
  Ledger 2 — a re-confirmation of an already-recorded `L0` deferral, booked at
  **zero claimed evidence gain**.
* **No existing holding moved.** `MODEL0-R`, `DATA-BOUNDARY0`,
  `MIN-FOUNDATION-ET`, `ET-VERTICAL` and `HETERO-NGSPICE` are unchanged.
  `ScientificTwin` gains zero evidence for the **third** consecutive milestone.
* **Nothing about** vector or tensor rank, 2D/3D topology, field-valued
  coefficients, nonlinearity, coupling, external providers, concurrency, scale,
  field transfer between supports, or **time-varying boundary values** — the
  last a cost of freezing the inflow constant, named by the falsifier and not
  claimed.
* **`QuantityDependency` remains scalar-endpoint-oriented, correctly.** A field
  endpoint reports `MISSING`; a *scalar reduction* of the same field checks
  clean. The only expressible coupling endpoint today is the one that has
  already thrown the field away. The §64.3 convective-transport limit is **not
  closed**.

## 67.5 Next milestone

**`MIN-FOUNDATION-PDE`** — the minimum semantic foundation a real field consumer
forces, scoped to exactly three questions: boundary orientation (`FORCED`), a
route from problem structure into `validity_context` (`FORCED`), and non-uniform
`InitialCondition` (`LIKELY-FORCED`). **Not** three roadmap milestones; the same
evidence-driven method used for electro-thermal.

Entry condition: a **real** consumer, not another probe. The reviewer's rejected
candidate D — 2D scalar transport in a prescribed velocity field — is the
natural choice, because it forces the representational half this milestone
deliberately did not probe.

Explicitly deferred with their own evidence required: `DiscretizationDefinition`
(identity already works; *selection* is the gap), an admissibility
`ValidationLevel`, and every Ledger-2 item. Explicitly rejected: `Mesh`,
`VectorQuantity`, `FieldState`, a general boundary system.

Regression: **FULL 1784 → 1825**, FAST 1262 → 1303. No pre-existing test edited,
no tolerance loosened. `src/engcore/scientific/` and `src/engcore/domains/thermal/`
byte-unchanged, asserted by tests rather than claimed.

---

# 68. CROSS-DOMAIN-COVERAGE — completed

```text
Decision status:        none — this milestone freezes nothing
Evidence:               L0 REASONED + a measured coverage matrix; L1 for the probes
Milestone execution:    COMPLETE
```

Full record: `docs/cross-domain-coverage-stress-prereg.md` (immutable, committed
before implementation) and `docs/cross-domain-coverage-stress-evidence.md`.
**A coverage-discovery milestone: no architecture was implemented.**

**Ran ahead of `API / MCP v0` for the second time**, and consumed the consumer
`MIN-FOUNDATION-PDE` had reserved. Both deviations are recorded in the
preregistration rather than assumed.

## 68.1 The four consumers, and what each differences against

Selected by `architecture-decision-reviewer` over five alternatives, one per
founder-fixed family, each rejected-if-isomorphic against the **whole**
repository rather than against one neighbour:

* **A — two-element plane-stress CST patch.** A 1D bar was rejected as
  isomorphic to the existing MNA solve. The patch breaks that on a **rank-1
  unknown**, a **rank-2 derived tensor** and a **matrix constitutive law**.
* **B — 2D steady advection-diffusion in a rotational field**, verified by a
  manufactured solution. Minimised deliberately; the transport-operator overlap
  with `HOSTILE-CORE-STRESS` is conceded, not discovered.
* **C — closed isothermal three-species batch.** Isothermal to eliminate the
  existing CSTR overlap; **closed** to break the B/C shared lineage that
  Modelica's stream-connector retrofit identifies.
* **D — planar pendulum in Cartesian coordinates**, a genuine DAE. A controlled
  first-order plant was rejected as isomorphic to `thermal_lumped`.

Two **existing** domains — `electrical/dc` and `thermal_lumped`, chosen
milestones ago for other reasons and neither edited — were scored on the same
matrix as a control group.

## 68.2 What was measured

Executed science, all machine-precision: the patch test recovers `σ_xx = E·ε` at
**relative error `0.0`** in both elements with `K = Kᵀ` to `0.0`; `div u` is
**exactly `0.0`**; the weighted invariant `c_A + c_B + 2c_C` holds to `1.1e-14`
while the **naive unweighted sum drifts `4.576`**; the pendulum's two
realizations — which solve **different unknowns** — agree to `2.6e-14 m`.

**Two universal candidates, both from column-varying probes:**

* **`VariableToBulkLinkage`** — all four consumers attach a bulk
  `ScientificDataReference` to a multi-variable problem, and that record carries
  no field naming a variable. Neither the association nor the ordering is
  recorded. This row was **split out of a conflated `ScientificField` row** that
  was understating it by half.
* **`AdmissibilityAttainment`** — four consumers now write four genuinely
  different kinds of admissibility criterion into their records (a
  positive-definite invariant, a maximum-principle excursion, a non-negativity
  excursion, an algebraic residual), and **every one carries
  `establishes=None`** because `ValidationLevel` has no member for it.

**An unplanned finding:** B's coarse grid produces `c_min = −0.0136`, so one
record simultaneously **claims `ANALYTICALLY_VERIFIED`** and carries a failed
admissibility check that can attain nothing.

**Recorded with equal prominence — what the contracts already serve:**
`DynamicState` is **served**, not forced; `MaterialState` and scalar
`PropertyRequirement` are forced by nothing, corroborating
`electrical/material.py`'s recorded "no property hierarchy needed" argument.

## 68.3 Falsified on the claim layer, and three claims withdrawn

`architecture-falsifier` returned **SURVIVES WITH REQUIRED CHANGES**: four
`BLOCKER`s and five `BREAKING-RISK`s, **all against the claims, none against the
executed science**, and all closed.

* **The instrument was mostly not measuring the consumers.** 26 of 29 probes
  returned a column-constant verdict, so those rows' cross-column patterns were
  the author's own `science` declarations re-printed. The response was to make
  the four claim-bearing rows payload-sensitive and to **publish the variance
  itself**: 24 of 30 rows remain column-constant, and the evidence document
  labels them contract-gap measurements rather than coverage measurements.
* **`Domain/Topology` forced by `electrical/dc` — the milestone's headline
  answer to "these gaps are PDE artifacts" — was a FALSE GAP and is withdrawn.**
  `dc/problem.py` records that it translates a circuit *"without smuggling
  topology into the IR"* because connectivity travels by a separate typed
  channel bound by a verified fingerprint. The probe had never been handed that
  artifact. With it, topology is forced only by the two field consumers — the
  exact PDE-shaped profile the claim denied.
* **`AdmissibilityAttainment` was 6/6 from a probe that never read the result**,
  while zero of six columns recorded an admissibility check at all. Now 4/6, and
  exhibited.
* **Five probes answered a *recoverability* question with a *forcing* argument**,
  every one returning "fully representable" — an armed false-negative generator
  that would have silently served a dash to any future consumer declaring a
  port. Fixed.
* **A preregistered steelman was missed**: `ScientificVariable.lower/upper` is an
  existing typed channel for admissibility bounds and was never attempted. It is
  now declared — and no path that inspects a `ScientificResult` reads it.

**The lesson, and it is the second consecutive milestone to earn it: an
instrument that produces a matrix can be measuring its own author.** The defence
is not a better argument but a published measurement of how many of its own
cells vary.

## 68.4 What it did **not** establish

* **No existing holding moved.** `MODEL0-R`, `DATA-BOUNDARY0`,
  `MIN-FOUNDATION-ET`, `ET-VERTICAL`, `HETERO-NGSPICE` and
  `HOSTILE-CORE-STRESS` are unchanged. `ScientificTwin` gains zero evidence for
  the **fourth** consecutive milestone.
* **`L2` is excluded outright.** Four consumers by one author on one branch is
  exactly the lineage §54.1 excludes from "materially different".
* **The row set is uncontrolled.** The control group governs the columns;
  nothing governs the concepts. A concept the author did not list is invisible,
  not absent — **complex-valued quantities** are the recorded counterexample,
  and the control being `electrical/dc` means even the control cannot surface
  them.
* **Zero evidence for coupling.** No `QuantityDependency`, no second problem, so
  `CausalPort` and `PhysicalConnector` are dash by construction and must not be
  counted as measured negatives.
* **`ModelFormulation.DAE` got its first production-shaped use and is still
  insufficient** — it cannot state the index, which unknowns are algebraic, or
  whether the statement or its index-reduced form is meant.

## 68.5 Next milestone

**`MIN-FOUNDATION-PDE`** — unchanged in name from §67.5 and now better scoped.
Four questions: boundary orientation (with the new 2D constraint that **a
boundary region is not the granularity at which orientation lives** — under
rotation every side carries both roles); a route from problem structure into
`validity_context`; **`VariableToBulkLinkage`**, the strongest new input; and
non-uniform `InitialCondition`.

Entry condition unchanged and binding: a **real** consumer, not another probe.
Consumer B was run here as a minimised probe, so the preregistered preference is
**promotion of it into a real domain pack**.

Explicitly deferred: an admissibility `ValidationLevel` member — adding one later
is *additive*, so it fails the "cheaper now than later" test — and rank-1
semantics, on two exhibited consumers.

Regression: **FULL 1825 → 1867**, FAST 1303 → 1345. No pre-existing test edited;
`src/engcore/scientific/`, `domains/thermal/`, `domains/electrical/`,
`thermal_lumped.py` and `experiments/hostile_core_stress/` all byte-unchanged,
asserted by tests rather than claimed.

---

# 69. API-MCP-V0 — completed

```text
Decision status:        PROPOSED
Evidence:               L1 EXERCISED (the boundary and the external contract)
                        L2 EXCLUDED BY PREREGISTRATION
Milestone execution:    COMPLETE
```

Full record: `docs/api-mcp-v0-prereg.md` (immutable, committed before any
implementation file existed) and `docs/api-mcp-v0-evidence.md`. **Not a freeze.**

**The first time existing Crafty scientific execution was reachable from outside
the process.** `architecture-decision-reviewer` compared seven boundaries and
selected one thin transport-neutral application service — `engcore.application`,
occupying the top layer the architecture map has named since before any of this
existed and which had zero occupants — with the response as a **versioned
projection**, not the internal `CoupledRun` verbatim. Publishing
`coupling_fixed_point_run/1` externally would have fired
`COUPLING-PACK-RELOCATION` reversal trigger 1 by construction.

## 69.1 What was demonstrated

The electro-thermal vertical, unchanged, reached three ways: Direct Python in
process, HTTP over a **real TCP socket to a separate OS process**, and MCP over
a **real stdio pipe to a separate OS process**. Both transports are stdlib only
— no FastAPI, no Pydantic, no MCP SDK installed or imported anywhere — and both
live outside `engcore`, so the core gains no transport dependency at any level.

* `ET-VERTICAL` CASE A reproduced exactly through all three: 10 iterations,
  `T* = 338.5770175652607 K`, `R* = 11.785281808946952 Ω`,
  `P* = 2.1212899619439667 W`. **Differential: worst relative difference `0.0`
  across all 13 quantities**, identical units, coupling outcome, per-participant
  verdicts and the 5 provenance bindings over 3 solvers and 2 realizations.
* **A run that exhausts its budget is `status: executed`,
  `outcome: iteration_limit_reached`, HTTP 200** — with every sub-solve still
  reporting success. Five distinctions stay apart externally: transport success,
  execution success, numerical convergence, coupling convergence, validity.
* **Zero universal-core change.** `scientific/`, `coupling/`,
  `systems/fluidthermal/` byte-unchanged. One additive `circuit_solver` keyword
  on the electro-thermal entry point lets a **closed** execution-profile
  enumeration substitute real `ngspice-42` into the coupled loop; it agrees with
  the native profile to `1.8e-15` with an identical iteration count.
* **Nine endpoints and tools were considered and six deleted**, each with a
  reason. `/v0/validate` would report `NOT_RUN` as `PASS`, because
  `unsupplied()` is "reported, never refused". `/v0/capabilities` would publish
  discovery no caller can act on. Both are additive later.

## 69.2 Falsified once, on a reproduced remote code execution

`architecture-falsifier` returned **FALSIFIED** in round one — one `BLOCKER`,
six `BREAKING-RISK` — then **SURVIVES WITH REQUIRED CHANGES** in round two.
All closed before the evidence document was written.

The `BLOCKER` is the milestone's headline. An external request field,
`component_id`, was type-checked only; it flowed into `DCCircuit.circuit_id` and
the provider adapter emitted that identifier into its deck's **title line** —
the one place in a module whose own rule is *"no Crafty identifier ever has to
be SPICE-legal"* where a raw identifier reached deck text. A newline ended the
title, a `.control` block after it executed `shell touch <path>`, **the file was
created**, and the run returned `criterion_met` with every check passing and a
`ProvenanceRecord` describing the circuit that was *declared* rather than the one
solved. Closed by removing the channel (a constant title — the module's own
"assign, never escape" rule) plus a published identifier character class.

**The process lesson is the one to carry: the test written to catch this could
not have.** It asserted `result is None` while the spies made the loop raise, so
an *admitted* hostile request passed too. A security claim was stated at
architectural strength on the basis of a test structurally incapable of
falsifying it. Round two then found the fix for one finding placed *outside* the
failure classifier, and a defect introduced by another fix that only a
cross-process test could see.

## 69.3 Two defects found in the existing platform, not in the API

* **A canonicalizing boundary can starve a downstream guard.** A tolerance of
  `1e-6 degC` was converted to `273.150001 kelvin`; the run converged in **one**
  iteration, **5.695253 K** from the truth, every sub-solve passing.
  `engcore.coupling.scales.is_ratio_scale` exists to refuse exactly this and
  **never ran**, because conversion happened first. Repaired by checking the
  caller's unit before conversion — the existing contract, not a second copy.
* **The executed coupled path assesses no model applicability.**
  `assess_resistance_validity` exists and `ET-VERTICAL` CASE F showed it returns
  `OUTSIDE_VALIDATED_DOMAIN` on a converged run — but nothing in the loop calls
  it, so no transport can report one. The response says `assessed: false`
  (`NOT_RUN != PASS`) rather than inventing a verdict. **A
  converged-but-out-of-domain run is externally indistinguishable from a
  converged-and-in-domain one.**

## 69.4 What it did **not** establish

* **`L2` was excluded by preregistration, before any result existed.** Two
  transports written by one author on one day against one interface are exactly
  what §54.1 excludes. Real socket and pipe boundaries earn that the boundary
  survives a process boundary — not two materially different consumers. And
  whole-payload equality is close to tautological: both transports serialize the
  same object with the same call.
* **The external response is deliberately lossy.** 162 594 bytes internally,
  7 711 externally; per-iteration participant results are unreachable in v0. The
  reviewer permitted a disclaimed passthrough key and it was **not built**.
* **One execution, one system pack, one scalar consumer.** Every execution v0
  can expose is an iterative coupling — `project_run` takes a `CoupledRun` — so
  a single-solve execution needs `crafty_execution_response/2`. Said before
  publication rather than discovered after.
* **Nothing about concurrency, scale, latency, persistence, auth, restart or
  hostile network conditions.** `project_run` **refuses** a result carrying
  `data_references`, loudly and by design: there is no field-valued external
  representation, and that refusal is the concrete trigger for deciding what one
  is.
* **`ScientificTwin` gains zero evidence here either** — nothing on the
  external path builds or reads one, continuing the run §68.4 tracked at four.
  No existing holding moved.

**Two preregistered deviations, both recorded rather than absorbed.** Fail
condition 1 (`domains/` byte-unchanged) was **triggered** to close the RCE —
preserving it would have meant publishing an API with a reproduced remote code
execution behind it, which is §59.1's warning exactly. And `run_id` became
required, because the preregistration's justification for its default ("only a
provenance string") was factually false: it is also `ScientificResult.result_id`.

## 69.5 Next milestone

**`MIN-FOUNDATION-PDE`** — unchanged in name from §67.5 and §68.5, entry
condition unchanged and binding: a **real** consumer, not a probe. This
milestone adds one input to it: the projection's `data_references` refusal is
where a field-valued external response has to be decided.

Regression: **FULL 2205 → 2306**, FAST 1602 → 1681. Four pre-existing test files
edited, all mechanically: one tier label, and a documented exception set plus a
new-tree filter in the two `src/`-untouched guards that already carry the same
pattern for three earlier milestones. No assertion changed, no tolerance
loosened. `src/engcore/scientific/`, `engcore/coupling/` and
`engcore/systems/fluidthermal/` byte-unchanged, asserted by tests rather than
claimed; `engcore/domains/` was **not**, and §69.4 says why.

**`API-MCP-V1` is not next and should not be.** The three gaps v0 measured — an
external representation of model applicability, a second execution shape that is
not an iterative coupling, and anything about concurrency — should each wait for
a second real consumer to force their shape.
