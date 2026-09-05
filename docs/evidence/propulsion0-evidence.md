# PROPULSION0 — Electromechanical Propulsion Chain Proof: evidence

**Verdict: KEEP.** `PROPOSED / L1 EXERCISED`. Fixture machine constants and handbook material
data give **MODEL-CONSISTENT** results only; nothing here is validated against hardware.

| | |
|---|---|
| Canonical starting commit | `6b31ddd` (COMPOSITE-SYSTEM0, KEEP, `PROPOSED / L1 EXERCISED`) |
| Branch / worktree | `propulsion0` / `/home/user/crafty-propulsion` |
| Preregistration | `4e3b8fe`, committed alone, not amended |
| Baseline FULL (orchestrator, sequential) | 2385 passed / 0 failed / 0 errors, 758 s |
| Baseline FAST (this worktree) | 1760 passed / 0 failed / 625 deselected |
| Final FAST | **1840 passed / 0 failed / 627 deselected** |
| Final FULL (sequential, authoritative) | **2467 passed / 0 failed / 0 errors**, 1192 s |
| New tests | 82 (80 FAST, 2 `expensive`) |
| Existing tests modified | 2, both historical scope guards — see §11 |
| New universal contracts forced | **NONE** |
| Adversarial rounds | 2 (`architecture-falsifier`), 8 findings closed |

---

## §1 What was claimed, and what was measured

> One real physical entity — a motor — can participate **simultaneously** in electrical,
> rotational-mechanical and thermal physics, while remaining coupled to material-dependent
> wires, **using the contracts that already exist**.

**Measured: yes.** One `Motor` record owns eight derived identities across four separately
posed physics problems plus a circuit resistor and a circuit voltage source; the composition
converged; the energy balance closed to 1.22e-15 relative; and **`src/engcore/scientific/` and
`src/engcore/coupling/` are byte-identical to the preregistration commit**, as are every
pre-existing domain and system pack. Asserted from git *and* from the working tree by
`test_gate_universal_core_and_the_coupling_package_are_byte_untouched` and
`test_gate_no_pre_existing_domain_or_pack_was_modified`.

---

## §2 Architecture selected, and the reviewer's decision

`architecture-decision-reviewer` returned **ACCEPT WITH CHANGES** on five axes. Adopted:

| Axis | Selected | Not forced |
|---|---|---|
| Mechanical | new sibling domain module `domains/mechanical_rotational.py`, five reusable claims, no inertia, no rpm code | generic mechanics framework, `MechanicalSystem`, `StateVector` |
| Motor identity | pack-local `Motor` deriving eight ids from one `component_id` | `PhysicalEntityReference`, `ComponentInstance`, `Port`, `Connector` |
| Material | pack-local `ThermophysicalConductor` composing `cmat.COPPER` **by reference** | universal `Material`; fields on the electrical record |
| Aggregation | binary derived scientific models, instantiated N−1 times | generic fan-in in `FixedPointCouplingPlan`; pack-local imperative sums |
| Electromechanical | closed-form drive operating point; the electromechanical cycle disappears | cyclic formulation (would force mixed-dimension tears → three schema changes incl. the published `crafty_execution_response/1`) |

**Reviewer's corrections adopted:** its factual corrections C-1 (`Vs:<cid>`, not `source_voltage:<cid>`)
and C-2 (`heat_capacity` **is** a legal `QuantityDependency` target, so the static derivation is a
size choice and not a contract limit); the binary form of the aggregation models; the
independent-channel requirement on the reconciliation; `k_load > 0` and `R_loop > 0` as refusals
rather than branches; the `DriveElement` protocol; not consuming `total_source_delivered_power`;
and predicting the contraction analytically before running.

**Reviewer's dissent, declared in the preregistration before any code (§3.1) and not adopted:**
it preferred `ThermophysicalConductor` in `domains/` for a hypothetical second pack. A composing
record placed in `domains/` and importing `domains/electrical/conductor_material` **is** the
domain-to-domain import the promotion trigger names — it would satisfy the trigger rather than
measure it — and there is no second consumer. Kept in `systems/propulsion/`, with the trigger
restated on the new record naming `domains/` as the destination on the **second** consumer.

---

## §3 Exact new contracts: NONE universal

Nothing was added to `engcore.scientific` or `engcore.coupling`. Every presumed-unnecessary
contract in preregistration §2 stayed unnecessary, and each was attempted against the existing
records first:

`PhysicalEntityReference`, `ComponentInstance`, `Port`, `Connector`, `SystemDefinition`,
`MaterialIdentity`, universal `Material`/`MaterialProperty`, `MechanicalSystem`, `StateVector`,
`FanInRule`, per-endpoint coupling tolerances, `CouplingScheme`, a relaxation knob, a new
`CouplingOutcome` member — **none forced**.

### New records, all pack-local or single-domain

| Record | Where | Why it exists |
|---|---|---|
| 5 rotational `ScientificModelDefinition`s + 4 realizations | `domains/mechanical_rotational.py` | reusable claims about a machine and a shaft |
| `MachineConstants`, `RotationalLoad` | same | declarations; carry no solver, no state |
| `ThermophysicalConductor` + `CONDUCTOR_THERMAL_MASS_MODEL` + realization + solver | `systems/propulsion/materials.py` | one material declaration across two physics |
| `SERIES_LOOP_RESISTANCE_MODEL`, `MOTOR_HEAT_GENERATION_MODEL`, `DRIVE_OPERATING_POINT_MODEL` + realizations + solvers | `systems/propulsion/models.py` | the three claims that belong to the assembly |
| `DriveWire`, `Motor`, `ThermalDeclaration`, `PropulsionDrive`, `EnergyAccounting`, `DriveRun` | `systems/propulsion/drive.py` | the composition |
| 4 schema strings, all `/1` | pack-local | `propulsion_series_drive`, `propulsion_conducting_element`, `propulsion_thermal_declaration`, `thermophysical_conductor` |

---

## §4 Mechanical capability introduced — stated precisely

**Not** "a Mechanics domain". What exists is: **five algebraic rotational claims about a
single-shaft machine at a steady operating point**, and no solver of its own.

```
E        = k_e * omega          BACK_EMF_MODEL
tau_e    = k_t * I              TORQUE_PRODUCTION_MODEL
tau_loss = b * omega            VISCOUS_ROTATIONAL_LOSS_MODEL
tau_load = k_load * omega^2     QUADRATIC_ROTATIONAL_LOAD_MODEL   (a load law, NOT a propeller)
tau_e    = tau_load + tau_loss  ROTATIONAL_TORQUE_BALANCE_MODEL   (d(omega)/dt = 0, NO inertia)
```

No inertia, no inductance, no transient, no gearbox, no compliance, no torsional dynamics, no
Coulomb friction, no saturation, no commutation, no cogging, no armature reaction, no iron loss,
no windage, no dq axes, no FEM, no fluid. `rpm` is not a model: it is
`Quantity(omega, "radian/second").to("revolutions_per_minute")`, and no `60`, `2*pi`, `9.549` or
`math` import exists anywhere in the new code (`test_t14_no_rpm_constant_appears_anywhere_in_the_new_code`).

### Motor model and its fidelity limits

An **idealised DC-equivalent machine**: one electrical port, one shaft, one lumped transduction
constant, a winding that is a `MaterialConductor` of copper, and a lumped thermal body. Its
resistance is `rho(T)L/A` through the **existing** models; its heat is winding dissipation plus
internal mechanical loss and nothing else. It is not a brushed-DC model, not a BLDC model, not a
PMSM model, and it must not be described as one.

---

## §5 Energy accounting — the proof, with numbers

Reference declaration: 24 V, `k_t = k_e = 0.0295` (SI), `k_load = 2.444e-7 N·m·s²/rad²`,
`b = 2.0e-5 N·m·s/rad`; two copper leads L = 1.5 m, A = 5.0e-7 m², hA = 0.15 W/K; copper winding
L = 6.25 m, A = 3.0e-7 m², hA = 0.35 W/K; ambient 300 K, interval 30 s, seed 300 K.

| Term | Value (W) |
|---|---|
| `P_source` (from `−source_power:V1`, MNA node voltages × branch current) | 116.6824500 |
| `P_wire_a_loss` | 1.2541388 |
| `P_wire_b_loss` | 1.2541388 |
| `P_motor_copper_loss` | 10.0172305 |
| `P_mechanical_output` | 93.6088522 |
| `P_internal_mechanical_loss` | 10.5480895 |
| **Residual** | **−1.42e-13 W = 1.22e-15 relative** |

Declared tolerance **1e-9 relative**. Efficiency 0.802253 (mechanical output / source).
Operating point: `I = 4.861768748 A`, `omega = 726.2261889 rad/s`, `rpm = 6934.94927`,
`tau_e = 0.143422178 N·m`, `E = 21.4236726 V`.
Converged states: `T_wire_a = T_wire_b = 306.8924320 K`, `T_motor = 347.1691119 K`; all three
inside copper's declared `[200, 450] K`.
Derived capacities: `C_wire = 2.5872 J/K`, `C_motor = 6.4680 J/K`.

### Where enforcement happens — T9, the exact points

**Point 1 — `admit_drive`, before any solver object exists.** `k_e` and `k_t` are declared
independently (a pair that cannot be constructed cannot be enforced) and
`require_energy_consistent_constants` refuses any pair differing by more than 1e-12 relative.
Proven with a spy that counts every solver construction in the pack: the count is **zero**
(`test_t9a_an_energy_inconsistent_machine_is_refused_before_any_solver`, and the
creates-energy direction too).

**Point 2 — `DriveOperatingPointSolver.bind_drive`, the record boundary.** Added after round 1
of the falsifier found the published solver could be bound directly with an inconsistent pair,
produce a number, and have it consumed while `validate()` reported `FAIL` — this repository's
own worst historical defect (a validation `FAIL` whose value was consumed anyway, converging
18 K wrong) reproduced one level below the gate meant to prevent it.

**Point 3 — `reconcile_drive_energy`, on the executed path, raising.** Three relations, of which
**R1 is genuinely independent**: its residual is exactly `I·omega·(k_e − k_t)`. R2 (circuit
current vs machine current) and R3 (back-EMF source absorbed power vs converted power) are not
independent of each other — R3 is close to R2 times the same `E`. The preregistration §5.1
called all three independent; **that over-counts by about one, and the correction is recorded
here rather than left standing** (deviation D-3).

All three shown **capable of failing** by injection, not asserted: corrupting exactly one
reported quantity fires exactly one relation
(`test_t9b_the_post_run_reconciliation_raises_on_an_injected_defect`, three parametrisations).
A structural test proves the reconciliation is on the executed path and that no `skip_*` or
`disable_*` keyword exists to turn it off.

**Non-convergence is not reconciled.** On `ITERATION_LIMIT_REACHED` the accounting is `None`:
reconciling a state the loop never reached would report the residual of an equation nothing
claims to have solved.

### The units-layer defect this forced around

`Quantity.is_compatible_with` compares dimensionality **strings**, and the backend renders the
one dimension of `volt*second/radian` and `newton*meter/ampere` two different ways, so they
compare **incompatible**. Recorded, tested
(`test_t13_the_units_layer_cannot_compare_the_two_machine_constants`), **not repaired** —
universal core is byte-untouched by F2. It is **fail-closed**: string equality is strictly
stronger than dimensional equality, so it yields false refusals and never false acceptances.
Its blast radius is wider than this milestone (it can make `Quantity.to`, `QuantityDependency`
dimension checks, `TornEndpoint` seeds and the plan's single-dimension check refuse correct
records) and is carried forward as a reopen trigger.

The check does not assume the two unit strings are SI-coherent. `_SI_COHERENCE_FACTOR` obtains
the comparison basis from the units layer by the one route the defect does not block — the
**ratio** of the two units, which reduces to dimensionless (1.0 as declared; 1000.0 if the
torque unit were respelled in mN·m/A). What that buys is bounded and stated on the constant: the
*check* no longer depends on an unstated agreement between two module constants; the closed
form's arithmetic still multiplies SI floats, so a respelling would surface as a raised
reconciliation failure rather than as a silently passing check. Making the arithmetic itself
unit-string-independent would be speculative hardening and is deliberately not done.

---

## §6 Physical identity — result: **YES, and no contract was forced**

One `Motor.component_id` yields **eight distinct identities**, every one derived by a published
accessor, none colliding with each other or with either lead
(`test_t5_one_motor_owns_eight_identities_and_aliases_none`):

```
R:M1                          a resistor in the circuit
Vs:M1-emf                     a voltage source in the same circuit
conductor_resistivity:M1      a material-property problem
conductor_resistance:M1       a geometry problem
conductor_thermal_mass:M1     a thermal-mass problem
thermal-lumped-M1             a lumped body problem
drive_operating_point:M1      a rotational operating point
machine_heat_generation:M1    a heat-aggregation problem
```

**K1 not triggered.** The motor participates in all three physics in one run without identity
aliasing or semantic duplication. Going from a wire's four derived identities to a motor's eight
is a *quantitative* change, not a new kind. Adding `ComponentInstance` later stays additive
precisely because problem ids remain derived from `component_id`. `COMPOSITE-SYSTEM0` avoided
`ComponentInstance` by not creating a Component; this milestone did the same with a physically
richer object, and that is the result.

**The tripwire `COMPOSITE-SYSTEM0` named in advance** — *a third element kind that poses its own
problems: re-examine the union, do not grow it* — **was fired and answered** with a pack-local
`DriveElement` protocol. **And the answer is honestly downgraded:** the falsifier proved
`DriveElement` is a *type annotation, not an extension point*. A class satisfying all three
members still cannot enter a `PropulsionDrive`, which declares three concrete slots,
`isinstance`-checks them, returns exactly two series joins and assigns circuit nodes positionally
over a fixed five-node span. A fourth element kind is **not** additive today. The docstring now
says so. Building a generic element registry to make it real would be the speculative move this
lineage refuses.

---

## §7 Material cross-physics — did ONE declaration drive BOTH? **YES**

`ThermophysicalConductor(conductor_material=cmat.COPPER, density=…, specific_heat=…, source=…)`
holds the existing catalogue record **by reference** — `COPPER_THERMOPHYSICAL.conductor_material
is cmat.COPPER`, asserted — and adds the two properties the electrical record has no business
declaring. No electrical number is restated anywhere.

`C = rho_m · L · A · c_p` goes through `CONDUCTOR_THERMAL_MASS_MODEL` + realization + published
solver with an `ExecutionBinding`. **Never caller Python arithmetic**, for the reason
`COMPOSITE-SYSTEM0` refused it for `rho L / A`.

### The promotion trigger: premise measured FALSE, trigger DEFERRED not defeated

The trigger says the only two moves are *a domain-to-domain import* and *a duplicate*. A third
move exists that it does not enumerate: **a consumer that already sits above both domains
composes the record**. `power_chain` already imports both `domains/electrical/conductor_material`
and `domains/thermal_lumped`; this pack does the same, and the import direction is strictly
downward. So a universal `Material` contract is **not forced**, and saying so is the correct
result.

What is deferred rather than defeated, stated plainly:

1. The trigger's own condition — *a non-electrical **domain** needs the property* — is never
   satisfied, because the consumer is a system pack. It remains **armed and untested**.
2. One physical copper now has **two declaration records with disjoint property sets, and no
   universal contract binds them.**
3. The in-process link is object identity; the **serialized link is the material's name**. Those
   are not the same guarantee.
4. `CONDUCTOR_THERMAL_MASS_MODEL` self-declares `domain="thermal"`. The falsifier's sharpest
   point on this axis: a thermal-domain *model* does need `rho_m` and `c_p` for the same named
   copper, and has simply been *filed* under `systems/`. The trigger is satisfied in substance
   and unsatisfied only in directory. **Recorded as the honest state, not argued away.**

**New promotion trigger, replacing the deferred one:** the first time a *second pack*, or any
*thermal domain module*, needs `rho_m`/`c_p` for a named material, this record is in the wrong
package and a materials decision is the answer — not a third composition.

**And the "one declaration" claim is now an enforced invariant, not a convention.** The falsifier
found two `ThermophysicalConductor` records over one copper with different densities constructed,
ran, serialized and reached the twin, both captioned *"Declared property of material 'copper'"*.
Its second round then found the first repair — keyed by `id(...)` — *moved* the counterexample
instead of closing it: a record rebuilt by `cmat.material_from_dict` is a fresh object, so the
guard was a no-op on every deserialized drive. It is now keyed by the material's **name**, which
is the identity that survives serialization, and the test exercises three boundaries: same
object, equal-but-distinct object, and the `from_dict` path.

### Cu → Al on one wire only: before / after

| Quantity | copper feed | aluminium feed | change |
|---|---|---|---|
| `R_wire_a` (Ω) | 0.053058751 | 0.085976434 | **+62.0 %** |
| `C_wire_a` (J/K) | 2.5872 | 1.8164 | **−29.8 %** |
| `T_wire_a` (K) | 306.892432 | 312.139413 | +5.25 K |
| `T_wire_b` (K) | 306.892432 | 306.737978 | −0.154 K |
| `R_wire_b` (Ω) | 0.053058751 | 0.053028194 | −0.06 % |
| `C_wire_b` (J/K) | 2.5872 | 2.5872 | unchanged |
| `I` (A) | 4.861768748 | 4.808371 | −1.10 % |
| `rpm` | 6934.949 | 6894.724 | −40.2 |
| `T_motor` (K) | 347.169112 | 346.325905 | −0.843 K |
| `P_mechanical_output` (W) | 93.60885 | 91.98936 | −1.73 % |

`R_wire_a` **and** `C_wire_a` both moved from **one** changed declaration — the electrical and
the thermal property in one record. Wire B's declaration, material record, geometry, posed
problems and provenance are **byte-unchanged**; its converged `R_b` and `T_b` do move, and that
is series coupling, not aliasing — asserted by recomputing `R_b` from wire B's own material law
at its own converged temperature to 1e-9.

**The thermal-mass pathway is isolated by a control case.** A control material carrying
aluminium's electrical properties and copper's `rho_m`/`c_p` converges to a **different**
`T_wire_a` from true aluminium — the two differ by more than 1 K when the *only* difference
between the declarations is density and specific heat, and their resistances differ by exactly
what their own temperatures imply through the shared material law. That differential is what
makes `C` load-bearing rather than decorative.

### Area intervention (T3): before / after

| `A_wire_a` (m²) | `R_a` at the 300 K seed (Ω) | `C_a` (J/K) |
|---|---|---|
| 2.5e-7 | 0.103390356 | 1.2936 |
| **5.0e-7** (reference) | **0.051695178** | **2.5872** |
| 1.0e-6 | 0.025847589 | 5.1744 |

(Quoted at the seed, not at convergence, precisely because the converged
temperatures differ between the three cases — which is the interaction.)

Area enters `R = rho L/A` inversely and `C = rho_m L A c_p` directly, so the two effects
interact. **No naive monotonic direction was preregistered for the converged `T_a`, and none is
asserted** — what is asserted is the exact inverse proportionality of `R` at fixed temperature,
the exact proportionality of `C`, and that the converged resistance equals `rho(T_converged)L/A`
to 1e-12. Both changes trace to the single declared area.

---

## §8 Fan-in — forced? **NO**, and the cost of avoiding it is measured

Two fan-in sites appeared, not one:

* the machine's body receives `P_copper` (circuit) + `P_internal_mechanical_loss` (machine);
* the operating point needs `R_wire_a + R_motor + R_wire_b`.

Both are discharged by **binary derived scientific models with named distinct inputs**, so no
endpoint ever receives two edges and `FixedPointCouplingPlan`'s fan-in refusal is never reached.
`MOTOR_HEAT_GENERATION_MODEL` takes `electrical_dissipation` and `mechanical_dissipation`;
`SERIES_LOOP_RESISTANCE_MODEL` takes `resistance_a` and `resistance_b` and is instantiated
**N−1 = 2** times, so loop length lives in the number of *problem instances*, not in a model
record. Every summed number carries an `ExecutionBinding`.

**The naive alternatives are executably refused by the unedited plan**
(`test_the_naive_fan_in_composition_is_refused_by_the_unedited_plan`,
`test_the_naive_loop_resistance_fan_in_is_refused_too`) — that is what makes the two models
load-bearing rather than decorative. A generic "add two quantities of the same dimension" model
was designed and rejected: it would carry no assumptions and no validity domain and would make
"the two elements carry the same current" and "both channels heat the same body" one claim.

**Measured cost, and a falsified sub-claim.** The two are **not symmetric**, and the module
docstring originally said they were. Chaining is *licensed* by the series claim and *denied* by
the heat claim, because a partial sum of two loss channels is not itself a channel dissipating
into a body. So a four-element loop costs one more **problem instance**, while a third loss
channel (iron loss, say) costs a new **model record**. Both records now state their own rule.
The denial is prose, not enforcement: enforcing "this output may not be an operand of another
instance" would need edge provenance only `engcore.coupling` could carry, and F2 forbids
touching it.

**The mixed-dimension wall is real and was designed around, not legislated away.** Had the
electromechanical loop stayed cyclic, its only tears carry amperes, volts, newton-metres or
radians per second while the thermal loops tear in kelvin — and one plan carries one scalar
tolerance. `test_a_mixed_dimension_tear_would_have_been_refused` executes that refusal. The
closed-form operating point is what keeps all three tears in kelvin and `engcore.coupling`
untouched.

---

## §9 Composition, causal trace and multi-state feedback

**14 problems, 20 declared edges, 3 torn (all kelvin), 9 iterations.**

```
resistivity(3) -> resistance(3) -> series join 1 -> series join 2 -> operating point
                                \-> circuit R:<cid>                /
operating point -> circuit Vs:M1-emf
circuit resistor_power:wire_a -> thermal wire_a           (and wire_b)
circuit resistor_power:M1     -> machine heat electrical_dissipation
operating point internal_loss_power -> machine heat mechanical_dissipation
machine heat total_dissipation -> thermal M1 heat_input
thermal <cid> final_temperature -> resistivity <cid> temperature      [TORN x3, kelvin]
```

Execution order is **computed** from the declared edges by `execution_order`; it is written down
nowhere. The iteration contains no electrical, thermal, material or mechanical branch: the loop
receives a dependency graph and a dispatch table and can name neither.

**Causal trace of one intervention (wire_a Cu→Al):** material record → `rho_ref`, `alpha`,
`rho_m`, `c_p` → `rho(T)` → `R_a` **and** (through the thermal-mass model at declaration time)
`C_a` → series join 1 → join 2 → `R_loop` → operating point → `omega`, `I`, `E`,
`P_internal_loss` → circuit (via `Vs:M1-emf` and `R:<cid>`) → per-element power → three bodies →
three temperatures → back to three resistivities. Every arrow is a declared
`QuantityDependency`, and changing a dependency's `source_quantity` to a different declared
metric of the same dimension makes the loop transport something else and converge somewhere
else.

**Multi-state feedback:** three coupled temperature states, converged jointly. Predicted
**before any run**, in the preregistration §7, from a numerically differentiated Jacobian:
**ρ(J) = 0.0434**, ‖J‖∞ = 0.0500, 9 ± 1 iterations, asymptotic ratio 0.043 ± 0.005.
**Measured:** 9 iterations; iterate changes
`4.524e+01, 1.852e+00, 7.571e-02, 3.188e-03, 1.364e-04, 5.878e-06, 2.543e-07, 1.102e-08, 4.782e-10 K`;
asymptotic ratio **0.0434**. Prediction, not postdiction: §7 is in a commit that precedes every
source change.

**K4 not triggered.** No relaxation knob was added, and none was needed.

---

## §10 Provider substitution — **succeeded, no capability gap**

The machine's back-EMF is an ordinary `DCVoltageSource`, so the circuit is composed only of
primitives the existing ngspice adapter already supported (it iterates `circuit.voltage_sources`
generically and refuses only current sources, of which there are none). **The adapter was not
expanded by one line.**

Native vs ngspice 42: same outcome, same iteration count, and agreement of every converged
temperature and the machine current to **≤ 2.6e-14 relative** (declared expectation 1e-9). The
substituted run's own energy reconciliation also passes. Both tests are `expensive`-marked and
**do execute** (`-m expensive` selects 2, both pass) — round 1 of the falsifier correctly flagged
that a green FAST run did not establish this, and it is now established.

---

## §11 Existing tests modified — exactly 2, both historical scope guards

Not casually. Both read `git diff <their own preregistration commit>` and therefore fail for
**every** later milestone, however correct the later work is. The repository already carries this
class of repair four times; these are the fifth and sixth.

| File | Defect | Repair | Why it is not weaker |
|---|---|---|---|
| `tests/test_api_mcp_v0.py` | its scope guards read `git diff <API-MCP-V0 prereg> -- src/engcore/domains/`, so any later file added there fails them | added `_PROPULSION0_ADDITIONS`, five files **named individually**, unioned with the existing `_COMPOSITE_SYSTEM0_ADDITIONS` | only NEW files are excluded; the assertion that exactly the RCE repair edited a pre-existing file under `src/engcore/domains/` is untouched, and an unexpected addition is still loud |
| `tests/test_composite_system0.py` | `test_t6f` reads `git diff <CS0 prereg> HEAD` over the **whole tree**, so it fails for every later milestone, full stop | added this milestone's nine paths to `allowed`, **named individually** | not one file COMPOSITE-SYSTEM0 asserts unchanged is excluded — universal core, `engcore.coupling`, the Fluid-Thermal pack, the DC domain, `conductor_material.py` and `power_chain.py` all remain covered, and it still reads the working tree |

Nothing else was touched. No architectural test was weakened to pass.

**And this milestone's own gates were built not to repeat the pattern.** They use
`--diff-filter=MD`, so a successor that *adds* a file does not fail a guard about *this*
milestone's edits while any edit to or removal of a pre-existing file stays loud forever; and
they read `git status --porcelain` as well as the commit graph, so an uncommitted edit to
universal core is seen rather than merely absent from HEAD. The falsifier's second round caught
the accompanying meta-test doing the very thing it repaired — pinning the whole `src/` tree
against a frozen tuple — and it is now scoped to this milestone's own trees.

---

## §12 Falsifier findings — 2 rounds, 8 findings closed

**Round 1: SURVIVES WITH REQUIRED CHANGES.** No BLOCKER. Five MAJOR closed:

| # | Counterexample | Closed by |
|---|---|---|
| D-1 | `DriveOperatingPointSolver` is published; a caller could bind an inconsistent `k_e`/`k_t` pair, get a number from `solve()`, and consume it while `validate()` said `FAIL` — the 18-K defect reproduced below its own gate | `bind_drive` refuses at the record boundary |
| D-2 | the check compared two bare SI magnitudes and was correct only because two module unit strings happen to be coherent; respelling one made the law wrong by 1000× with every test passing | `_SI_COHERENCE_FACTOR`, obtained from the units layer via the ratio route |
| D-3 | two unversioned sub-payloads inside a versioned envelope; a field added to a composed record would be absorbed as a default with `require_schema` unable to fire | schema tokens emitted and enforced on both |
| D-4 | two `ThermophysicalConductor` records over one copper with different densities constructed, ran, serialized and reached the twin under one name | refused in `PropulsionDrive.__post_init__` |
| D-5 | this milestone's own scope gates reproduced the self-invalidating pattern it had just repaired twice | `--diff-filter=MD` plus a working-tree read |

Two stated claims **falsified**, corrected in prose rather than by building machinery:
`DriveElement` is not an extension point (§6); the two binary claims are not symmetric (§8).

**Round 2: SURVIVES WITH REQUIRED CHANGES.** No BLOCKER. Three closed:

| # | Finding | Closed by |
|---|---|---|
| MAJOR-1 | **D-4 moved its counterexample rather than closing it** — keyed by `id(...)`, so an equal-but-distinct material landed in another bucket and the guard was a no-op on every deserialized drive | keyed by the material's **name**; test now exercises same-object, equal-but-distinct and `from_dict` |
| MAJOR-2 | D-5's new meta-test reintroduced the guard-rot in the same commit, pinning all of `src/` against a frozen tuple | scoped to this milestone's own trees; both halves of the filter semantics still proved |
| MAJOR-3 | the deferred findings existed only in a session transcript | this document |

Round 2 explicitly confirmed D-1, D-2, D-3 and D-5 close their counterexamples at the boundary
they were aimed at, that the `--diff-filter=MD` delete-and-re-add hole does not exist, that
schema enforcement is complete on every read path, and that the measured evidence holds.

---

## §13 Deviations from the preregistration

| # | Deviation | Status |
|---|---|---|
| **D-1** | §6 summary line said 21 edges; it is **20**. The prose enumerates them correctly; the total was an arithmetic slip. | Recorded; the test asserts 20. |
| **D-2** | §6's table header said 13 problems and then listed 14; corrected inline in the preregistration's own §6 before commit. It is **14**. | No divergence in the executed composition. |
| **D-3** | §5.1 called all three reconciliation relations independent. **R1 is; R2 and R3 are not independent of each other** (R3 ≈ R2 × the same `E`). The over-count is about one. | Corrected in `reconcile_drive_energy`'s docstring and here. |
| **D-4** | §3.1 declared the reviewer's axis-3 placement dissent in advance and did not adopt it. | Deliberate, preregistered, unchanged. |
| **D-5** | `_ThermalDeclaration` was renamed `ThermalDeclaration` and exported after the falsifier observed the pack's public API could not construct its own subject. | Additive. |

---

## §14 What this proved

1. A motor participating **simultaneously** in three physics forces **no new universal
   contract**. `engcore.scientific` and `engcore.coupling` are byte-untouched.
2. **One material declaration** drove both an electrical property and a thermal mass, and the
   promotion trigger's "only two moves" premise is **measurably false** for a consumer above both
   domains. The trigger is deferred, and the deferral is stated in four numbered points.
3. **Fan-in was not forced.** Two fan-in sites were discharged as scientific claims with
   provenance, and the naive alternatives are executably refused by the unedited plan.
4. **Energy conservation is enforced, at three points, and each is shown capable of failing.**
5. The **existing R(T) mechanism was reused unchanged** for a motor winding — no second
   framework (`test_t5_the_motor_winding_reuses_the_existing_rt_mechanism_by_identity` asserts
   the model records are the *same objects*).
6. **A contraction rate predicted analytically before the run matched the measurement**
   (0.0434 vs 0.0434).
7. **Provider substitution held** across the electromechanical boundary with zero adapter change.

## §15 What this did NOT prove

1. **Anything about hardware.** MODEL-CONSISTENT only.
2. **Any topology but one series loop across one ideal source.** `circuit_at` assigns nodes
   positionally over a fixed five-node span; `series_join_ids` returns exactly two; the operating
   point's first assumption says a parallel branch invalidates the closed form outright.
3. **Any transient.** No inertia, no inductance, one operating point.
4. **Two drives in one process** — see the deferred findings below.
5. **A fourth element kind.** `DriveElement` is a type annotation, not an extension point.
6. **A second consumer of anything.** Every new record has exactly one consumer.
7. **Anisotropy, fields, `c_p(T)`, distributed execution.** All out of scope, all stated in the
   records' own assumptions.

---

## §16 Deferred findings — recorded so they are retrievable, not abandoned

| # | Finding | Why deferred |
|---|---|---|
| **F-1** | Problem ids are namespaced by `component_id`, **not** `drive_id` (only `electrical_problem_id` and `series_join_ids` carry it). Two `PropulsionDrive`s in one process sharing an element id collide, and `FixedPointCouplingPlan` would accept the union. | Unreachable at one drive. Fixing it now would be namespacing against a consumer that does not exist. **Reopen the moment a second drive is composed in one process.** |
| **F-2** | A plan is **not bound to the drive it was composed for**: `run_propulsion_drive` validates only that the plan's problem ids are a subset of `declared_problem_ids(drive)`, so any drive with the same component ids is accepted. `compose()` and `run_propulsion_drive()` each rebuild the composition independently. | A wart, not a defect, at one drive. Related to F-1 and should be closed with it. |
| **F-3** | Four `ModelRealizationDefinition` records in `mechanical_rotational.py` have **zero consumers** — the five rotational claims are all discharged jointly with `realization=None`. Seven of the nine new registry and capability factories likewise have no production reader beyond their own `__all__` entry; only `thermal_mass_solver_capabilities` and `propulsion_solver_capabilities` are read, by the two solvers that declare them. | They are honest declarations of *how* each elementary claim would be discharged, and deleting them would leave the domain module unable to state it. But they are abstraction ahead of a consumer, by this project's own standard. **Delete or bind on the next consumer.** |
| **F-4** | The derived heat capacity's provenance **does not survive serialization**. The results carry model, realization, solver and `ExecutionBinding`; the `ThermalBody` carries only the number, and `DriveRun` is deliberately unserialized. So "derived, not declared" is scoped to **in process**. | The `heat_capacity` `QuantityDependency` edge route exists at zero contract cost (reviewer correction C-2) and closes this the day `c_p(T)` is declared. Building it now would be an edge nothing needs. |
| **F-5** | `Quantity.is_compatible_with` compares dimensionality **strings**. Blast radius: `Quantity.to`, `QuantityDependency.check_against`, `TornEndpoint` seeds and `FixedPointCouplingPlan`'s single-dimension check can all refuse correct records. Fail-closed. | Repairing it would violate F2 (universal core byte-untouched). **This is the strongest reopen trigger this milestone produces** — see §18. |
| **F-6** | The pack **forks `MaterialConductor`'s serialization** (geometry + one material, rather than `MaterialConductor.to_dict()`), because embedding that record would put copper's resistivity in one payload twice under two authorities. Nothing pins that the fork stays faithful to the domain record's field set. | The alternative — a redundant encoding with a consistency check — is worse than one authority. The schema token bounds the drift. **Reopen if `MaterialConductor` gains a field.** |
| **F-7** | The `CircuitSolver` seam and `native_circuit_solver` now exist in **two** system packs. Importing the sibling pack for three lines of plumbing would be a lateral system-to-system dependency. | **On the third consumer the seam belongs one level down.** |
| **F-8** | `run_fixed_point` never consults `ScientificResult.is_usable`, so a validation `FAIL` inside the loop is consumed. | Pre-existing universal-core behaviour, byte-untouched under F2. This pack's compensating control (`reconcile_drive_energy`, which raises) is the right local answer. Not a PROPULSION0 defect, but carried forward. |

---

## §17 Kill criteria — none triggered

| | Criterion | Result |
|---|---|---|
| K1 | motor cannot participate in multiple physics without aliasing | **not triggered** (§6) |
| K2 | one declaration cannot drive both properties without an import or a duplicate | **not triggered** (§7) — a third move exists |
| K3 | loss aggregation needs generic fan-in | **not triggered** (§8) |
| K4 | the kelvin-only loop does not contract | **not triggered** — ρ(J) = 0.0434 |
| K5 | the existing R(T) mechanism cannot be reused | **not triggered** — reused by object identity |
| K6 | energy cannot be enforced, only detected | **not triggered** — three enforcement points, each shown able to fail |
| K7 | existing primitives cannot express the back-EMF | **not triggered** (§10) |
| K8 | a presumed-unnecessary universal contract turns out forced | **not triggered** |
| K9 | an architectural test can only be satisfied by weakening it | **not triggered** (§11) |
| K10 | the composition cannot be serialized and re-executed to the same answer | **not triggered** — round-trips exactly and re-executes to 1e-12 |

---

## §18 Reopen triggers

1. **A second drive in one process** → F-1 and F-2 together.
2. **A second pack, or a thermal domain module, needing `rho_m`/`c_p` for a named material** →
   the new promotion trigger; a materials decision, not a third composition.
3. **A non-series topology** (parallel machines, a shunt path, a second source) → the
   closed-form operating point is invalid outright, the electromechanical cycle returns, and axis
   5 reopens with per-endpoint coupling criteria as the live option.
4. **A transient requiring inertia** → same as (3): the balance becomes an ODE and the cycle
   returns.
5. **A second feedback dimension** (battery `R(T, SoC)`) → the plan's single-scalar-tolerance
   limit is reached and `engcore.coupling`'s reversal trigger 6 is genuinely satisfied.
6. **A third consumer of the `CircuitSolver` seam** → F-7.
7. **`c_p(T)`, or any temperature-dependent thermophysical property** → F-4 closes via the
   existing edge route.
8. **`MaterialConductor` gaining a field** → F-6.
9. **Any consumer blocked by the dimensionality-string comparison** → F-5, and it is a universal
   core repair, not a pack repair.

---

## §19 Commits

| Commit | Contents |
|---|---|
| `4e3b8fe` | Preregister electromechanical propulsion proof — **alone** |
| `99acb95` | Exercise one motor in three physics at once — implementation + 73 tests + 2 guard repairs |
| *(round 1)* | Close five adversarial findings against the propulsion proof |
| *(round 2)* | Close the second adversarial round and record the evidence |

## §20 Next milestone, chosen from measured evidence

**Recommended: a second drive in one composition** — two machines, or one machine and one
independent heated element, in one process.

Chosen because it is the **only** reopen trigger this milestone measured that is (a) reachable
without new physics, (b) certain to break something specific and already identified (F-1 problem
id namespacing, F-2 plan-to-drive binding, and the `DriveElement`/`PropulsionDrive` fixed-slot
limit), and (c) the smallest step that tests whether the eight-identity result generalises past
N = 1 — which is the one place this milestone's strongest claim is weakest.

Explicitly **not** recommended on this evidence: a mechanics framework (no second consumer of
any rotational record); a universal `Material` (the trigger is deferred, not fired); per-endpoint
coupling tolerances (no consumer that cannot be reformulated); and a transient/inertial milestone
(it would reopen axis 5 before the N = 2 question is answered, and would arrive carrying an
unmeasured coupling-scheme change).
