"""The canonical external request used by both API/MCP v0 test modules.

Not a test module. It exists so the Direct, HTTP and MCP paths are demonstrably
handed **the same document** — a differential over three transports that each
transcribed their own request would be comparing three requests, not three
transports.

The numbers are `ET-VERTICAL` CASE A, unchanged: one 10 ohm conductor with
alpha = 0.00393 /K on a 2.5 J/K body with hA = 0.05 W/K, across 5 V, integrated
over 120 s from 300 K.
"""

from __future__ import annotations

import copy
from typing import Any

REQUEST_SCHEMA = "crafty_execution_request/1"
RESPONSE_SCHEMA = "crafty_execution_response/1"
EXECUTION = "electrothermal.series_self_heating/1"

#: `ET-VERTICAL` CASE A, reproduced exactly. Preregistered as exact targets.
CASE_A_TEMPERATURE_K = 338.577018
CASE_A_RESISTANCE_OHM = 11.785282
CASE_A_POWER_W = 2.121290
CASE_A_ITERATIONS = 10


def canonical_request(**overrides: Any) -> dict[str, Any]:
    """CASE A as an external request document. Overrides replace top-level keys."""
    request = {
        "schema": REQUEST_SCHEMA,
        "execution": EXECUTION,
        "execution_profile": "native",
        "run_id": "api-v0-case-a",
        "inputs": {
            "source_voltage": {"value": 5.0, "unit": "volt"},
            "stages": [
                {
                    "component_id": "R1",
                    "reference_resistance": {"value": 10.0, "unit": "ohm"},
                    "temperature_coefficient": {"value": 0.00393, "unit": "1/kelvin"},
                    "reference_temperature": {"value": 293.15, "unit": "kelvin"},
                    "heat_capacity": {"value": 2.5, "unit": "joule/kelvin"},
                    "ambient_conductance": {"value": 0.05, "unit": "watt/kelvin"},
                    "ambient_temperature": {"value": 300.0, "unit": "kelvin"},
                    "initial_temperature": {"value": 300.0, "unit": "kelvin"},
                    "duration": {"value": 120.0, "unit": "second"},
                }
            ],
        },
        "coupling": {
            "transported_temperature": "final_temperature",
            "seed_temperature": {"value": 300.0, "unit": "kelvin"},
            "tolerance": {"value": 1e-6, "unit": "kelvin"},
            "max_iterations": 50,
        },
    }
    request.update(copy.deepcopy(overrides))
    return request


def output(response: dict[str, Any], quantity: str) -> dict[str, Any]:
    """The one output entry naming ``quantity``. Raises if absent or ambiguous."""
    matches = [
        entry
        for entry in response["result"]["outputs"]
        if entry["quantity"] == quantity
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly one output named {quantity!r}, found {len(matches)}"
        )
    return matches[0]
