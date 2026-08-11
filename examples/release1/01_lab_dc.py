"""Release 1 Example 01: execute a typed Electrical DC Lab study."""

from __future__ import annotations

import json

from engcore.domains.electrical.dc import (
    DCCircuit,
    DCVoltageSource,
    ElectricalDCSolver,
    ElectricalNode,
    Resistor,
    build_dc_problem,
    solve_circuit,
)
from engcore.scientific import Quantity


def main() -> None:
    circuit = DCCircuit(
        circuit_id="release1-voltage-divider",
        nodes=(
            ElectricalNode("gnd", is_reference=True),
            ElectricalNode("top"),
            ElectricalNode("mid"),
        ),
        resistors=(
            Resistor("R1", "top", "mid", Quantity(1.0, "kohm")),
            Resistor("R2", "mid", "gnd", Quantity(3.0, "kohm")),
        ),
        voltage_sources=(
            DCVoltageSource("V1", "top", "gnd", Quantity(12.0, "volt")),
        ),
    )
    problem = build_dc_problem(circuit)
    result = solve_circuit(
        circuit,
        run_id="release1-example-01-dc",
        solver=ElectricalDCSolver(),
        problem=problem,
        software_version="engineering-ai-core/1.0.0",
    )

    summary = {
        "study_id": problem.problem_id,
        "model_identities": [list(item) for item in result.models],
        "solver_identity": list(result.solver.key) if result.solver else None,
        "result_id": result.result_id,
        "selected_metrics": {
            "mid_voltage": {
                "magnitude": result.value("node_voltage:mid").magnitude_in("V"),
                "unit": "V",
            },
            "r1_current": {
                "magnitude": result.value("resistor_current:R1").magnitude_in("mA"),
                "unit": "mA",
            },
        },
        "convergence": result.convergence.value,
        "validation": {
            "status": result.validation.status.value,
            "attained_levels": sorted(level.value for level in result.attained_levels),
        },
        "uncertainty": result.uncertainty_of("node_voltage:mid").kind.value,
        "provenance": {
            "run_id": result.provenance.run_id,
            "models": [list(item) for item in result.provenance.models],
            "solvers": [list(item) for item in result.provenance.solvers],
            "formulation": result.provenance.metadata["formulation"],
            "tolerances": dict(result.provenance.tolerances),
        },
    }
    print("LAB V1 - ACTUAL ELECTRICAL DC EXECUTION")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
