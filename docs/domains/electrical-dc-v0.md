# Electrical DC V0

> **Electrical DC V0 is a validated linear resistive DC analysis domain.
> It is not a SPICE replacement.**

The first real scientific domain built on Scientific Core V0.0.1. It exists
as much to test the universal contracts as to analyse circuits: it was
implemented without modifying a single line of `engcore.scientific`.

## Scope

**Supported:** resistors, ideal independent DC voltage sources, ideal
independent DC current sources, an explicitly declared reference node.
Linear, steady-state, lumped.

**Not supported (out of V0 scope):** capacitors, inductors, transient or AC
analysis, frequency domain, diodes, transistors, MOSFETs, any nonlinear
element, dependent/controlled sources, SPICE netlist parsing, ngspice,
power electronics, electromagnetic field simulation.

## Scientific claim boundary

This domain establishes results for **linear, steady-state, lumped,
resistive circuits with ideal independent sources**. It establishes nothing
about nonlinear devices, AC or transient behaviour, distributed circuits,
electromagnetics, real source internal impedance (unless you model it
explicitly as a resistor), temperature-dependent resistance, or parasitics.

Models are registered as `SELF_CONSISTENT`, not `BENCHMARK_VALIDATED` and
not `EXPERIMENTALLY_VALIDATED`: agreeing with hand-derived analytical values
in a test suite is internal consistency, not an external benchmark process,
and involves no measurement. Model `references` are deliberately empty —
these are standard textbook relations, but this repository has no curated
reference set yet and citations will not be invented.

## Mathematical formulation

Modified Nodal Analysis, `A x = z`, with the reference node eliminated.

For `N` non-reference nodes and `M` ideal voltage sources the system is
`(N + M) × (N + M)`:

| Unknown | Index range | Ordering |
|---|---|---|
| Non-reference node voltages | `0 … N−1` | node ids sorted |
| Voltage-source branch currents | `N … N+M−1` | component ids sorted |

Ordering is derived by sorting ids, so an identical circuit always assembles
an identical matrix regardless of the order components were added — verified
by test.

### Stamps

Resistor `R` between `a` and `b`, `G = 1/R` (rows/columns for the reference
node dropped):

```
A[a,a] += G    A[b,b] += G    A[a,b] -= G    A[b,a] -= G
```

Current source `I` flowing `from → to` inside the source. Each KCL row states
*sum of currents leaving the node = 0*:

```
z[from] -= I    z[to] += I
```

Voltage source `k` between `p` (positive) and `n` (negative), branch current
`i_k` defined as the current **leaving `p` through the source**:

```
A[p, N+k] += 1    A[n, N+k] -= 1        (i_k enters the KCL rows)
A[N+k, p] += 1    A[N+k, n] -= 1        (the constraint row)
z[N+k] = Vs                             →  V_p − V_n = Vs
```

## Numerical backend

`scipy.linalg.solve(A, z, assume_a="gen")`. No custom matrix inversion, no
heuristic circuit solver, and never `inv(A) @ z`. Mature linear algebra does
the linear algebra; this domain owns the formulation, the units and the
validation.

## Unit conventions

Every electrical value is a Scientific Core `Quantity`. Validation is by
**dimensionality, never by unit string**, so `1 kΩ` and `1000 Ω` are the same
resistance and `500 mV` and `0.5 V` are the same voltage. Wrong dimensions
(a resistance in volts, a source in kilograms) are rejected at component
construction, long before any matrix exists. Raw floats appear only inside
`RawSolverOutput`; `extract_metrics` restores units.

Resistance must be strictly positive: zero is a short (an ideal 0 V source)
and negative resistance is an active device — both need a different
formulation than the conductance stamp used here.

## Sign conventions

| Element | Convention |
|---|---|
| Resistor | `V_ab = V(a) − V(b)`; `I_ab = V_ab / R` positive `a → b`; absorbed `P = V_ab·I_ab = I²R ≥ 0` |
| Voltage source | branch current `I` **leaves the positive node through the source**; absorbed `P = (V_p − V_n)·I`, **negative when delivering** |
| Current source | current flows `from → to` **inside** the source (injected at `to`); absorbed `P = (V_from − V_to)·I`, negative when delivering |

Power balance sums *absorbed* power over every element and must vanish
(Tellegen). No `abs()` is applied anywhere to make a sign work out.

## Validation strategy

A converged linear solve is **not** a validated result. Six independent
checks run on every analysis, all reconstructed from circuit elements and
extracted quantities — the KCL check walks the component list and sums signed
branch currents rather than re-evaluating a row of `A`. Re-using the matrix
would only re-prove that `A x = z` was solved; it could never catch an
incorrect *stamp*. (A test deliberately corrupts a stamp to prove the
distinction is real.)

| Check | What it verifies | Default tolerance |
|---|---|---|
| `dimensional_consistency` | every metric carries the dimension its name implies | exact |
| `linear_system_residual` | `‖A x − z‖` | `1e-9 + 1e-9·‖z‖` |
| `kirchhoff_current_law` | signed current balance at every non-reference node | `1e-9 A` |
| `resistor_constitutive_relation` | `V_ab − I_ab·R` per resistor | `1e-9 V` |
| `voltage_source_relation` | `(V_p − V_n) − Vs` per source | `1e-9 V` |
| `power_balance` | total absorbed power | `1e-9 W + 1e-9·Σ|P|` |

Tolerances live in one `DCValidationSettings` object, are carried in
`SolverSettings`, and are recorded in provenance — never scattered as
literals through production code.

### Validation-level honesty

Only two levels are claimable at runtime: `DIMENSIONALLY_VALID` (from the
dimensional check) and `NUMERICALLY_CONVERGED` (from the residual check).

The physics checks pass or fail but establish **no** level. They demonstrate
internal consistency, not agreement with an external benchmark or a
measurement, and the core's `ValidationLevel` vocabulary has no term for
"internally physically consistent". `ANALYTICALLY_VERIFIED` is **not**
claimed at runtime: analytical comparison happens in the test suite against
independently hand-derived values, not during an analysis.
`BENCHMARK_VALIDATED`, `CROSS_SOLVER_VALIDATED` and
`EXPERIMENTALLY_VALIDATED` are never claimed.

## Failure behaviour

A floating sub-network, or two ideal sources contradicting each other across
the same node pair, produces a singular system. The solver reports
`ConvergenceState.FAILED` with an explanatory warning and **no metrics**.

It never adds epsilon to the diagonal, never falls back to least squares or a
pseudo-inverse, and never picks a datum on the caller's behalf. A system with
no unique solution has no unique solution; inventing a plausible answer would
be the worst possible outcome for a platform whose purpose is trustworthy
results. Note that two *identical* parallel ideal sources are also singular —
consistent, but with indeterminate individual branch currents.

Structurally invalid circuits (no reference node, two reference nodes,
duplicate ids, unknown node references, self-connected components, zero or
negative resistance, wrong dimensions) are rejected at construction and never
reach the solver.

## Scientific Core mapping

| Domain concept | Universal contract |
|---|---|
| `DCCircuit` topology | **stays in the domain** — carried to the solver in `PreparedSolve.payload` as `PreparedDCSystem` |
| node potentials, source currents | `ScientificVariable`, role `OBSERVABLE` (a DC analysis chooses nothing) |
| element values | `ScientificParameter` with `Quantity` values |
| reference node, analysis type | `ScientificParameter` with `CategoricalValue` — typed, not metadata |
| Ohm / KCL / ideal-source relations | three `ScientificModelDefinition`s with typed `ModelInputSpec`/`ModelOutputSpec` |
| `electrical:dc_linear` | domain-local `SolverCapability`; `CoreCapabilities` is never extended |
| analysis output | `ScientificResult` + `ValidationReport` + `ProvenanceRecord` |

IR naming: `V:<node>`, `I:<vsource>`, `R:<resistor>`, `Vs:<vsource>`,
`Is:<isource>`, plus `reference_node` and `analysis_type`.

**Topology deliberately does not enter the universal IR.** `ScientificProblem`
describes *what is computed*; connectivity is domain-specific and reaches the
solver through the prepared-solve payload. A circuit is bound to a solver
instance with `bind_circuit(circuit, problem_id)` — domain-local state, never
a global registry.

**Model binding is per component.** Models declare generic physical names
(`resistance`, `voltage_across`) while a circuit problem necessarily uses
per-instance names (`R:R1`), so binding is verified with small relation
problems (`resistor_relation_problem`). This is what proves the V0.0.1
hardening under a real domain: a parameter *named* `resistance` but carrying
volts is rejected, and a required parameter supplied as a variable is
reported.

## Uncertainty

`UNKNOWN` for every metric, always, in V0. Element values are taken as exact
and no tolerance propagation is performed. Reporting anything else — even
`±0` — would be fabrication.

## Known limitations

* No component tolerances, no Monte Carlo, no sensitivity analysis.
* Dense solve only; fine for V0-scale circuits, unsuitable for large sparse
  networks.
* Near-singular circuits are reported through SciPy's ill-conditioning
  warning path rather than an explicit condition-number policy.
* No `ValidationLevel` exists for "internally physically consistent", so the
  KCL/Ohm/source/power checks establish no level. This is a candidate future
  core addition, not something the domain should work around.
* Ground is explicit by design: a node named `"0"` or `"gnd"` is **not**
  automatically the datum.
