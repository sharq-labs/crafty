# CRAFTY — MASTER CONTEXT, STRATEGY & HANDOVER

**Status:** CANONICAL PROJECT CONTEXT  
**Last consolidated:** 2026-09-01  
**Repository:** `sharq-labs/crafty`  
**Reviewed baseline commit:** `6abdf279141cf032abdb8052f6ee806c3c264953` (`Freeze D3 design memory milestone`)  

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

Historical scientific milestone reports should remain separate and frozen; this file is the living strategic context connecting them.

---

# 53. Current exact next action at consolidation time

**Do not begin broad domain implementation.**

The current intended next development action is:

```text
MODEL0-R
Universal Model / Computational Realization Foundation
```

with backward-compatible extension of the existing Scientific Core.

After MODEL0-R completes and passes targeted + full regression review, reassess and preregister the next milestone rather than automatically continuing.

---

# 54. Final project intent

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
