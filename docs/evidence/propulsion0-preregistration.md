# PROPULSION0 — Electromechanical Propulsion Chain Proof: preregistration

**Status:** preregistered. Committed alone, before any source file changes.
**Branch:** `propulsion0`. **Base commit:** `6b31ddd` (COMPOSITE-SYSTEM0, verdict KEEP,
`PROPOSED / L1 EXERCISED`).
**Independently re-verified FULL baseline at the base commit:** `2385 passed / 0 failed /
0 errors`, single sequential process, 758 s (orchestrator measurement, not taken on trust).
**Measured FAST baseline in this worktree:** `1760 passed / 0 failed / 625 deselected`.

This document is written **before** the implementation and is **not amended afterwards**.
Every divergence from it is recorded in `docs/evidence/propulsion0-evidence.md` as a numbered
deviation.

---

## §1 The claim under test

> One real physical entity — a motor — can participate **simultaneously** in electrical,
> rotational-mechanical and thermal physics, while remaining coupled to material-dependent
> wires, **using the contracts that already exist**; and the minimum architecture that makes
> that true can be measured rather than assumed.

This is a differential proof, not a feature. The deliverable is the **measured list of what
was forced and what was not**. A precise architectural finding (MODIFY / SUPERSEDE) is a
process success; a fake KEEP is not.

**Epistemic level claimed:** `PROPOSED / L1 EXERCISED`. Fixture motor constants and handbook
material data give **MODEL-CONSISTENT** results only. Nothing here is validated against
hardware, and no result in this milestone may be described as physically validated.

---

## §2 Zero-new-contracts gate (run first)

Before any new record is designed, the proof is attempted against the existing contracts, and
each failure is measured rather than assumed. The following are **presumed not needed** and
each must be independently forced by an executable or representational failure before it may
be created:

`PhysicalEntityReference`, `ComponentInstance`, `Port`, `Connector`, `SystemDefinition`,
`MaterialIdentity`, a universal `Material`/`MaterialProperty` hierarchy, `MechanicalSystem`,
`StateVector`, `FanInRule`, per-endpoint coupling tolerances, a `CouplingScheme` abstraction,
a relaxation knob, a new `CouplingOutcome` member, any edit to `src/engcore/scientific/`, and
any edit to `src/engcore/coupling/`.

**Fail condition F1:** any of the above is created without a named, executable failure recorded
in the evidence document.

---

## §3 Architecture selected (after `architecture-decision-reviewer`)

The reviewer returned **ACCEPT WITH CHANGES** on five axes. The selected architecture, with the
reviewer's required changes adopted and its one dissent recorded:

| Axis | Selected | Rejected |
|---|---|---|
| 1 Mechanical representation | **New sibling domain module `src/engcore/domains/mechanical_rotational.py`** holding only *reusable* rotational physics. No inertia `J`. No rpm code (the pint-backed units layer already converts `radian/second` → `revolutions_per_minute` exactly). | pack-local-only; generic mechanics framework (`MechanicalSystem`, `StateVector`, bodies/joints) |
| 2 Motor physical identity | **None.** A pack-local `Motor` record derives all of its problem/element identities from one `component_id`, plus a pack-local typed `DriveElement` protocol instead of `isinstance` dispatch. | `PhysicalEntityReference`; `ComponentInstance`; ports/connectors |
| 3 Material cross-physics | **Pack-local `ThermophysicalConductor` composing the existing `cmat.COPPER` by reference** (no numbers duplicated), with `C = ρ_m·L·A·c_p` computed through a declared model + realization + solver carrying an `ExecutionBinding`. | adding `density`/`specific_heat` to `ConductorMaterial` in `domains/electrical/`; a universal `Material` contract |
| 4 Loss / resistance aggregation | **Derived scientific models, binary arity, instantiated N−1 times** — one model per physical claim, never a generic adder. | pack-local imperative combination; new universal fan-in semantics in `FixedPointCouplingPlan`; hidden `a + b` in orchestration |
| 5 Electromechanical formulation | **Closed-form drive operating point**; the electromechanical cycle disappears and only the three kelvin thermal cycles remain, which the existing `FixedPointCouplingPlan` handles **unedited**. | a cyclic electromechanical formulation, which forces mixed-dimension torn edges and therefore a change to `coupling_fixed_point_plan/1`, `coupling_fixed_point_iteration/1` **and** the externally published `crafty_execution_response/1`; nested/alternating plans, which lose the mechanical-loss heat edge or hide an unreported outer convergence |

### §3.1 Recorded divergence from the reviewer (declared in advance)

The reviewer's axis-3 refinement **(3d)** asked that the composing record be placed in
`domains/` rather than in `systems/propulsion/`, to spare a hypothetical second pack a
system→system import. **This milestone does not adopt (3d)**, for two stated reasons:

1. A composing record placed in `domains/` and importing `domains/electrical/conductor_material`
   *is* the **domain-to-domain import** the promotion trigger names. It would satisfy the trigger,
   not defeat it — the opposite of the result being measured.
2. There is no second consumer. Building the reusable placement for one is the speculative move
   this lineage refuses.

The reviewer's dissent is recorded, and the promotion trigger is restated on the new record with
`domains/` named as the destination on the **second** consumer.

### §3.2 Reviewer's factual corrections adopted

- **C-1.** The DC voltage-source parameter is `Vs:<component_id>`, not `source_voltage:<cid>`.
- **C-2.** `heat_capacity` **is** a declared `ScientificParameter` of the lumped thermal problem
  and therefore a legal `QuantityDependency` target. The reason this milestone derives `C`
  statically is **not** that the contract forbids an edge; it is that `ρ_m` and `c_p` are declared
  temperature-independent here, so a static provenance-bearing derivation is the smaller
  architecture. The edge route exists at zero contract cost the day someone declares `c_p(T)`.

---

## §4 Physics, stated before it is coded

Single series loop across one ideal DC source:

```
 +24 V ──[ wire_a ]──[ R_motor ]──( E = k_e·ω )──[ wire_b ]── gnd
             │            │                          │
          (body_a)     (body_motor, also fed by      (body_b)
                        internal mechanical loss)
```

Governing statements:

| # | Statement | Where it is declared |
|---|---|---|
| G1 | `ρ(T) = ρ_ref (1 + α (T − T_ref))` | existing `cmat.LINEAR_RESISTIVITY_MODEL` — **reused, not re-created** |
| G2 | `R = ρ(T)·L/A` | existing `cmat.GEOMETRIC_RESISTANCE_MODEL` — **reused for the motor winding too** |
| G3 | `C dT/dt = Q_in − hA (T − T_amb)` | existing `lump.LUMPED_CAPACITY_MODEL` — **reused** |
| G4 | `E = k_e·ω` | new `mechanical_rotational.BACK_EMF_MODEL` |
| G5 | `τ_e = k_t·I` | new `mechanical_rotational.TORQUE_PRODUCTION_MODEL` |
| G6 | `τ_loss = b·ω` | new `mechanical_rotational.VISCOUS_ROTATIONAL_LOSS_MODEL` |
| G7 | `τ_load = k_load·ω²` — a **mechanical load law**, explicitly *not* a propeller model, no BEMT, no fluid | new `mechanical_rotational.QUADRATIC_ROTATIONAL_LOAD_MODEL` |
| G8 | `Στ = 0` at steady speed (`dω/dt = 0`); **no inertia J** | new `mechanical_rotational.ROTATIONAL_TORQUE_BALANCE_MODEL` |
| G9 | `R_series = R_a + R_b` (binary, instantiated N−1 times) | new pack-local `SERIES_LOOP_RESISTANCE_MODEL` |
| G10 | `Q_body = P_electrical_dissipation + P_mechanical_dissipation` | new pack-local `MOTOR_HEAT_GENERATION_MODEL` |
| G11 | `C = ρ_m·L·A·c_p` | new pack-local `CONDUCTOR_THERMAL_MASS_MODEL` |
| G12 | The simultaneous solution of {G4,G5,G6,G7,G8} with the loop KVL `V = I·R_loop + E` | new pack-local `DRIVE_OPERATING_POINT_MODEL` |
| G13 | Loop KVL is *also* represented by MNA over the posed `DCCircuit` | existing `dc.RESISTOR_OHM_MODEL`, `dc.IDEAL_VOLTAGE_SOURCE_MODEL`, `dc.KCL_MODEL` — **referenced, and the duplication enforced by reconciliation** |

Closed form for G12 (recorded here so the implementation cannot silently choose another):

```
k_load·ω² + (b + k_t·k_e/R_loop)·ω − k_t·V/R_loop = 0
ω = ( −B + sqrt(B² + 4·k_load·k_t·V/R_loop) ) / (2·k_load),   B = b + k_t·k_e/R_loop
E = k_e·ω ;  I = (V − E)/R_loop ;  τ_e = k_t·I
```

With `k_load > 0`, `b ≥ 0`, `V > 0`, `R_loop > 0` the product of the roots is strictly negative,
so **exactly one root is positive**. `k_load = 0` is a **refusal**, not a second code path:
`k_load > 0` and `R_loop > 0` are `RangeCondition`s in `DRIVE_OPERATING_POINT_MODEL.validity`.

**`rpm` is a presentation conversion performed by the units layer** —
`Quantity(ω, "radian/second").magnitude_in("revolutions_per_minute")`. The constants `60`
and `2π` appear **nowhere** in propulsion code. Asserted structurally (T14).

---

## §5 The energy trap, and where it is enforced

For an ideal DC-equivalent machine in SI, `k_e` (V·s/rad) and `k_t` (N·m/A) are **numerically
equal**, and that is required by energy conservation: `E·I = k_e·ω·I` must equal `τ_e·ω = k_t·I·ω`.

`MachineConstants` declares **both independently** — so that T9 has a real target — and the
identity is **enforced at admission**:

> `admit_drive()` raises `InvalidScientificProblem` when
> `|k_e[V·s/rad] − k_t[N·m/A]| > 1e-12 · max(|k_e|,|k_t|)`, **before any solver object is
> constructed**.

A measured limitation of universal core forces the comparison to be magnitude-based in each
constant's own SI unit rather than through `Quantity.require_compatible`:
`Quantity.is_compatible_with` compares **dimensionality strings**, and pint renders the identical
dimension of `volt*second/radian` as `[mass] * [length] ** 2 / [time] ** 2 / [current]` and of
`newton*meter/ampere` as `[length] ** 2 * [mass] / [time] ** 2 / [current]` — unequal strings for
one dimension. This is recorded as a finding about `src/engcore/scientific/units/quantity.py`
and **is not repaired here** (universal core is byte-untouched by fail condition F2). A test
documents the current behaviour so the defect is visible rather than folklore.

### §5.1 Required accounting, and the second enforcement point

`P_source`, `P_wire_a_loss`, `P_wire_b_loss`, `P_motor_copper_loss`, `P_mechanical_output`,
`P_internal_mechanical_loss`, reconciled to a declared **relative tolerance of `1e-9`**.

`reconcile_drive_energy(run)` is called **inside** `run_propulsion_drive` on the converged path
and **raises** on violation. It is enforcement, not detection: the repository's sharpest historical
failure was a validation `FAIL` whose value was consumed anyway and converged 18 K wrong.

Three relations, each comparing quantities from **independent channels** (never a number against
itself):

- **R1** `P_source` (from `−source_power:V1`, i.e. node voltages × branch current) equals
  `P_wa + P_wb + P_cu + P_mech + P_ml`.
- **R2** circuit `resistor_current:<motor>` equals the machine model's `current`.
- **R3** circuit `source_power:<emf_id>` (absorbed by the back-EMF source, i.e. `E·I` from node
  voltages and branch current) equals the machine model's `converted_power` (`k_e·ω·I`).

`total_source_delivered_power` is **deliberately not consumed anywhere in this milestone**: with a
second voltage source present it is the *net* over all voltage sources and therefore no longer
means "electrical input power". Recorded as finding A4.

On a **non-converged** run (`ITERATION_LIMIT_REACHED`) the reconciliation is **not** applied and
the run is returned with its outcome intact. Failing to converge and violating energy conservation
are different findings and are not collapsed.

---

## §6 Composition: 13 problems, 19 edges, 3 torn (all kelvin)

| # | Problem | Posed by |
|---|---|---|
| P1 | `electrical_dc:<circuit>` | existing `dc.build_dc_problem` |
| P2–P4 | wire_a: resistivity, geometric resistance, lumped thermal | existing builders |
| P5–P7 | wire_b: idem | existing builders |
| P8–P10 | motor winding: idem — **the same `MaterialConductor` mechanism, no second R(T) framework** | existing builders |
| P11 | `series_resistance:<drive>-1` (`R_feed + R_winding`) | new, binary |
| P12 | `series_resistance:<drive>-2` (`partial + R_return`) | new, binary |
| P13 | `drive_operating_point:<motor>` | new |
| P14 | `motor_heat_generation:<motor>` | new, binary |

(14 problems; the table label "13" would have been wrong and is corrected here rather than later.)

Edges (19 + 2 for the second series instance = 21). Per wire and for the winding:
`electrical.resistor_power:<cid> → thermal.heat_input`;
`thermal.final_temperature → resistivity.temperature` **(TORN, kelvin)**;
`resistivity.resistivity → resistance.resistivity`;
`resistance.resistance → electrical.R:<cid>`.
Plus: `resistance_a.resistance → series-1.resistance_a`;
`resistance_motor.resistance → series-1.resistance_b`;
`series-1.series_resistance → series-2.resistance_a`;
`resistance_b.resistance → series-2.resistance_b`;
`series-2.series_resistance → operating_point.loop_resistance`;
`operating_point.back_emf → electrical.Vs:<emf_id>`;
`operating_point.internal_loss_power → motor_heat.mechanical_dissipation`;
`electrical.resistor_power:<motor> → motor_heat.electrical_dissipation`;
`motor_heat.total_dissipation → motor_thermal.heat_input`.

**No endpoint receives two edges.** The plan's fan-in refusal is never tripped, and the three
torn edges all carry kelvin, so the plan's single-scalar-tolerance requirement is satisfied
**without editing `engcore.coupling`**.

Execution order after removing the torn edges is a DAG and is **computed**, never written down.

---

## §7 Contraction, predicted before it is run

The fixed-point map is `T → T'` over the three body temperatures. Evaluated at the reference
operating point below, the numerically differentiated Jacobian is

```
[ 0.024743  -0.000957  -0.006643 ]
[-0.000957   0.024743  -0.006643 ]
[-0.004957  -0.004957   0.040055 ]
```

**Predicted spectral radius ρ(J) = 0.0434** (‖J‖∞ = 0.0500). From a 300 K seed the first sweep
moves 45.2 K, so `45.2 · 0.0434ⁿ ≤ 1e-9 K` predicts **n ≈ 8, i.e. 9 iterations including the
first**. Preregistered prediction: **the run converges in 9 ± 1 iterations at
`absolute_tolerance = 1e-9 K`, with an asymptotic iterate ratio of 0.043 ± 0.005.**

If it does not contract, that is reported as `ITERATION_LIMIT_REACHED` and as a finding. **No
relaxation knob is added** — the coupling package's own reversal trigger 4 forbids adding one
without a measurement, and a knob nothing measured is a speculative knob.

---

## §8 Reference declaration (fixture, MODEL-CONSISTENT only)

| Declaration | Value | Source |
|---|---|---|
| `V_source` | 24 V | fixture |
| `k_t` | 0.0295 N·m/A | fixture, representative small brushed DC machine |
| `k_e` | 0.0295 V·s/rad | fixture; **required equal to `k_t` in SI by G4/G5 energy conservation** |
| `k_load` | 2.444e-7 N·m·s²/rad² | fixture mechanical load law |
| `b` | 2.0e-5 N·m·s/rad | fixture internal viscous loss |
| wire_a, wire_b | copper, L = 1.5 m, A = 5.0e-7 m² | handbook copper via existing `cmat.COPPER` |
| motor winding | copper, L = 6.25 m, A = 3.0e-7 m² | idem |
| `ρ_m`, `c_p` (copper) | 8960 kg/m³, 385 J/(kg·K) | handbook |
| `ρ_m`, `c_p` (aluminium) | 2700 kg/m³, 897 J/(kg·K) | handbook |
| `hA` wires / motor | 0.15 / 0.35 W/K | fixture |
| `T_amb`, `T_0`, interval | 300 K, 300 K, 30 s | fixture |
| seed | 300 K | fixture |

`heat_capacity` is **never declared**: it is derived from G11 for every body.

**Predicted reference answers** (predictions, not fixtures to be frozen — see §11):
`I ≈ 4.862 A`, `ω ≈ 726.2 rad/s`, `rpm ≈ 6935`, `τ_e ≈ 0.1434 N·m`,
`R_a = R_b ≈ 0.05306 Ω`, `R_motor ≈ 0.4238 Ω`, `T_a = T_b ≈ 306.89 K`, `T_motor ≈ 347.17 K`,
`P_source ≈ 116.68 W`, `P_mech ≈ 93.61 W`, `P_internal_mech_loss ≈ 10.55 W`,
`P_copper ≈ 10.02 W`, `P_wire ≈ 1.254 W each`, `C_wire ≈ 2.587 J/K`, `C_motor ≈ 6.468 J/K`.
All three converged temperatures lie inside copper's declared `[200, 450] K`.

---

## §9 Required cases T1–T14, with the prediction each one tests

Tests assert **governing equations, energy accounting, propagation and internal coherence**.
They do **not** freeze a numerical fixture and call it physics.

| Case | What is executed | Preregistered prediction / acceptance |
|---|---|---|
| **T1** | Nominal operating point | Current, terminal voltage, torque, ω, rpm, mechanical power, wire and motor losses, three thermal states, convergence outcome, validity assessments and provenance are all present and mutually consistent. Accept on: G1–G12 hold to `1e-9` relative on the converged record; R1–R3 hold; `rpm` equals `ω·60/2π` recomputed independently in the test |
| **T2** | wire_a copper → aluminium, **one wire only** | `R_a` rises (Al `ρ_ref` is 1.579× Cu's); `T_a` rises; `C_a` **falls** (Al `ρ_m·c_p` = 2.42e6 vs Cu 3.45e6 J/(m³·K)); `I`, `ω`, `rpm`, `T_motor` all fall; wire_b's **declaration, material record, geometry, posed problems and provenance are byte-unchanged**, while its converged `R_b` and `T_b` *do* move (series coupling, not aliasing). A **control case** — a material with aluminium's electrical properties and copper's `ρ_m·c_p` — isolates the thermal-mass pathway and must give a **different** `T_a` from true aluminium |
| **T3** | wire_a area 5.0e-7 → 2.5e-7 m² and → 1.0e-6 m², same material | Area enters **both** `R = ρL/A` (inversely) and `C = ρ_m·L·A·c_p` (directly), so the effects interact. **No naive monotonic direction is preregistered for `T_a`**, because none is mathematically guaranteed over an arbitrary interval; what *is* preregistered is that `R_a` is exactly inversely proportional to area at fixed temperature, that `C_a` is exactly proportional to area, and that both changes are traceable to the single declared area |
| **T4** | wire_a and wire_b independence | Two `MaterialConductor`s, two `ThermalBody`s, two resistivity problems, two resistance problems, two thermal problems, six distinct problem ids, no shared mutable object; changing wire_a's declaration leaves wire_b's records identical |
| **T5** | Motor multi-physics identity | The one `Motor.component_id` yields **seven** distinct identities — circuit resistor, circuit back-EMF source, resistivity problem, resistance problem, thermal problem, operating-point problem, heat-generation problem — all derived from it by published accessors, none colliding, and **no aliasing**: no two of the seven are the same string |
| **T6** | `L ≤ 0`, `A ≤ 0` | Rejected **before execution**. Proven by a spy that counts every solver construction and every circuit solve: the count is **zero** |
| **T7** | `ρ_ref ≤ 0`, `density ≤ 0`, `c_p ≤ 0` | Rejected at declaration/admission, spy count zero |
| **T8** | `k_t ≤ 0`, `k_e ≤ 0`, `k_load ≤ 0` | Rejected at admission, spy count zero. `k_load = 0` is refused rather than branched to a linear form |
| **T9** | **Energy inconsistency.** (a) `k_e = 0.5·k_t`; (b) a corrupted operating-point executor returning a `back_emf` inconsistent with its own `angular_velocity` | (a) `admit_drive` raises **before any solver exists** (spy count zero). (b) `reconcile_drive_energy` raises on the converged run and **no result is returned**. Both gates are shown **capable of failing** by injection, not asserted |
| **T10** | Coupling non-convergence with all sub-solves succeeding | With `max_iterations = 2` the run returns `ITERATION_LIMIT_REACHED`; **every** `ScientificResult` in **every** iteration reports success and every model validity assessment is `IN_DOMAIN`. Non-convergence is not conflated with model invalidity, and the reconciliation is not applied |
| **T11** | Provider substitution, native vs ngspice | The back-EMF is a plain `DCVoltageSource`, so the circuit is composed only of primitives the existing adapter already supports. Expect agreement of `I`, per-element powers and converged temperatures to `≤ 1e-9` relative. **If the existing adapter cannot express it, that portion STOPS, the capability gap is recorded, and ngspice is not expanded for a checkbox** |
| **T12** | Serialization round-trip | `PropulsionDrive.to_dict()/from_dict()` round-trips exactly, including the `ThermophysicalConductor`, the `Motor`, the machine constants and the load law. **No serialization is added for any ephemeral pack-local object.** The round-trip test also records finding A6: object identity (`thermo.conductor_material is cmat.COPPER`) does **not** survive serialization; re-binding goes through `resolve_material(name)`, which makes the **name** the de facto key |
| **T13** | Dimensional incompatibility | A `QuantityDependency` transporting `electromagnetic_torque` (N·m) into `heat_input` (W) is refused by `check_against`/`run_fixed_point` with `WRONG_DIMENSION`. Also recorded: `radian` is dimensionless in the units backend, so `radian/second` and `hertz` share one dimension — the *named* quantity, not the dimension, is what distinguishes angular velocity from frequency here |
| **T14** | Structural / AST | No new module branches on a domain, product or material name: no comparison against a material-name literal, no `if`/`match` on `.name`, no dict keyed by material name driving physics, no `60`/`6.28`/`9.549`/`2*pi` literal anywhere in the propulsion pack or the rotational domain module, and the rotational domain module imports no thermal and no system-pack code |

---

## §10 Fail conditions

| # | Fail condition |
|---|---|
| **F1** | A universal contract from §2 is created without a named executable or representational failure |
| **F2** | `git diff` against this preregistration's commit is non-empty for `src/engcore/scientific/` or `src/engcore/coupling/` |
| **F3** | `src/engcore/systems/electrothermal/`, `src/engcore/systems/fluidthermal/`, `src/engcore/domains/electrical/dc/`, `src/engcore/domains/electrical/conductor_material.py`, `src/engcore/domains/electrical/material.py`, `src/engcore/domains/electrical/ngspice.py`, `src/engcore/domains/thermal_lumped.py`, `src/engcore/domains/thermal/`, `src/engcore/application/`, `src/crafty_http/`, `src/crafty_mcp/` are modified |
| **F4** | Any number reaching a record is computed by caller Python arithmetic rather than by a declared model through a published solver with an `ExecutionBinding` — the bootstrap included |
| **F5** | An energy-inconsistent declaration is *reported* rather than *refused*, or a reconciliation failure is recorded in a field and the value consumed anyway |
| **F6** | A second `R(T)` framework is built instead of reusing `cmat`'s |
| **F7** | Any test freezes a numerical fixture as its only assertion of physics |
| **F8** | An existing architectural test is weakened to pass |
| **F9** | `.pytest_tmp_*` or `src/engineering_ai_core.egg-info` changes are committed |
| **F10** | `rpm` is computed by a hard-coded constant in propulsion or rotational code |
| **F11** | The final FULL run is not sequential, or regresses below `2385 + new` with 0 failures |

---

## §11 Acceptance is not fixture-freezing

Accept only on: the governing equations G1–G13 hold on the converged record; the energy
accounting R1–R3 holds within `1e-9` relative; each intervention actually propagates through the
declared edges; the outputs are internally coherent; and **no test's only assertion is a
hard-coded expected answer**. Where a reference number appears in a test it appears as a *loose
sanity band* alongside an equation-based assertion, never as the assertion itself.

---

## §12 Kill criteria (report MODIFY / SUPERSEDE rather than forcing KEEP)

- **K1** The same motor cannot participate in multiple physics without identity aliasing or
  semantic duplication → a minimal physical-identity contract is justified.
- **K2** One material declaration cannot drive both resistivity and thermal mass without a
  domain-to-domain import or a duplicate → a universal `Material` contract is justified.
- **K3** Loss aggregation cannot be expressed without generic fan-in semantics.
- **K4** The thermal-only fixed point does not contract with a motor present.
- **K5** Reuse of `cmat`'s `R(T)` mechanism for the motor winding is impossible.
- **K6** Energy conservation cannot be enforced at admission, only detected after the fact.
- **K7** The existing `DCCircuit`/ngspice primitives cannot express the back-EMF.
- **K8** A new universal contract turns out to be forced that §2 presumed unnecessary.
- **K9** An existing architectural test can only be satisfied by weakening it.
- **K10** The composition cannot be serialized and re-executed to the same answer.

---

## §13 Files this milestone expects to touch

**New:**
`src/engcore/domains/mechanical_rotational.py`,
`src/engcore/systems/propulsion/__init__.py`,
`src/engcore/systems/propulsion/materials.py`,
`src/engcore/systems/propulsion/models.py`,
`src/engcore/systems/propulsion/drive.py`,
`tests/test_propulsion0.py`,
`docs/evidence/propulsion0-preregistration.md` (this file),
`docs/evidence/propulsion0-evidence.md`,
and a concise update to the master context.

**Expected historical-guard repairs** (narrowest possible, individual files named, original
invariants preserved, each reported explicitly — this class of repair already exists four times
in the repository):

- `tests/test_api_mcp_v0.py` — its scope guard reads `git diff <its own prereg commit> --
  src/engcore/domains/`, so it fails for **every** later milestone that adds a file there.
- `tests/test_composite_system0.py` — its scope guard reads `git diff <its own prereg commit> HEAD`
  over the whole tree, so it fails for **every** later milestone, full stop.

Neither repair may weaken what those milestones claim: universal core, the coupling package and
the sibling packs must still be asserted byte-untouched, and only **new files added later** may be
excluded, named individually so an unexpected addition is still loud.

**Out of scope, and not to be touched:** propeller/BEMT/CFD/flight dynamics, battery
chemistry/SoC, ESC PWM/MOSFET/FOC, dq equations, EM FEM, CAD, generic
component/connector/material/mechanics frameworks, optimisation, planner, API/MCP, UI.

---

## §14 Commit plan

1. **This preregistration, alone** — "Preregister electromechanical propulsion proof".
2. Implementation + targeted tests.
3. Further commits only for falsifier corrections and the evidence document.

`architecture-falsifier` is invoked after implementation with all 20 attacks; every BLOCKER is
closed before completion. Approximately two adversarial rounds.
