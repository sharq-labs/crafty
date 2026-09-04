"""The request contract, published as data.

`API-MCP-V0` fitness question 16 asks whether a **fourth** transport could be
written against this boundary from its published contract alone, without
reading domain source. This module is the machine-readable half of the answer:
the enumerations, the field names and the declared unit of every field, derived
from *the same constants the validator uses* rather than transcribed beside
them.

That derivation is the point. A hand-written schema is a second statement of
the contract that can silently drift from the first; this one cannot, because
adding a field to the validator's allowlist without adding it here would make
the two disagree, and a test asserts they do not.

It lives in the application layer, not in a transport, because *what a request
may contain* is a fact about the boundary. MCP happens to have a discovery
channel that carries it (``tools/list``) and HTTP in v0 does not — an asymmetry
this milestone records rather than repairs, since inventing an HTTP endpoint to
match would be building a surface no measured consumer asked for.
"""

from __future__ import annotations

from typing import Any

from .catalog import execution_identities, profile_names
from .contract import MAX_ITERATION_BUDGET, MAX_STAGES, REQUEST_SCHEMA
from .executions import electrothermal_series as ets

__all__ = ["QUANTITY_SCHEMA_FRAGMENT", "request_json_schema"]

#: Every scientific value in this contract, everywhere, has this shape. Two
#: keys, both required, no additional properties. A bare number is not
#: acceptable anywhere: units remain explicit.
QUANTITY_SCHEMA_FRAGMENT: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["value", "unit"],
    "properties": {
        "value": {"type": "number"},
        "unit": {
            "type": "string",
            "description": (
                "Any unit dimensionally compatible with the field's declared "
                "unit. The value is restated in the declared unit before it "
                "reaches any scientific declaration."
            ),
        },
    },
}


def _quantity(unit: str, note: str = "") -> dict[str, Any]:
    fragment = dict(QUANTITY_SCHEMA_FRAGMENT)
    fragment["properties"] = dict(QUANTITY_SCHEMA_FRAGMENT["properties"])
    described = f"Declared unit: {unit}."
    fragment["description"] = f"{described} {note}".strip()
    return fragment


def request_json_schema() -> dict[str, Any]:
    """A JSON Schema for ``crafty_execution_request/1``, built from the catalog.

    ``additionalProperties: False`` at every level is not decoration: the
    validator refuses unknown fields rather than ignoring them, and a published
    schema that permitted them would describe a reader Crafty does not have.
    """
    stage = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(ets.STAGE_KEYS),
        "properties": {
            "component_id": {
                "type": "string",
                "description": (
                    "Names one conductor and the thermal body it dissipates "
                    "into. The two share this id by this system pack's own "
                    "convention."
                ),
            },
            **{
                name: _quantity(unit)
                for name, unit in sorted(ets.STAGE_UNITS.items())
            },
        },
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": REQUEST_SCHEMA,
        "type": "object",
        "additionalProperties": False,
        "required": sorted(
            {"schema", "execution", "execution_profile", "inputs", "coupling"}
        ),
        "properties": {
            "schema": {
                "const": REQUEST_SCHEMA,
                "description": (
                    "Exactly this string. Not a range, not a minimum. A "
                    "version is admitted only because somebody checked that "
                    "this reader handles it."
                ),
            },
            "execution": {
                "type": "string",
                "enum": sorted(execution_identities()),
            },
            "execution_profile": {
                "type": "string",
                "enum": sorted(profile_names()),
                "description": (
                    "Required, deliberately. Any default here would be a "
                    "default that selects which implementation computes the "
                    "answer. It is a Crafty identity drawn from a closed "
                    "enumeration — never a path, a command, or an argument to "
                    "one. Which concrete solver actually ran is reported "
                    "independently, in the response's provenance."
                ),
            },
            "run_id": {
                "type": "string",
                "description": (
                    "A provenance label, supplied by the caller. Crafty "
                    "collects nothing on its own."
                ),
            },
            "inputs": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(ets.INPUT_KEYS),
                "properties": {
                    "source_voltage": _quantity("volt"),
                    "stages": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_STAGES,
                        "items": stage,
                    },
                },
            },
            "coupling": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(ets.COUPLING_KEYS),
                "properties": {
                    "transported_temperature": {
                        "type": "string",
                        "enum": sorted(ets.TRANSPORTED_TEMPERATURES),
                        "description": (
                            "Which kelvin-valued thermal result is carried "
                            "back into the conductor's state. Both members are "
                            "kelvin, so no dimension check separates them, and "
                            "the two converge to different temperatures. Only "
                            "this name selects the physics."
                        ),
                    },
                    "seed_temperature": _quantity(
                        "kelvin", "First value of every cut coupling edge."
                    ),
                    "tolerance": _quantity(
                        "kelvin",
                        "Coupling criterion: the largest change of any cut "
                        "iterate between sweeps. Not the residual of any "
                        "equation, and not any sub-solve's own tolerance.",
                    ),
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_ITERATION_BUDGET,
                        "description": (
                            "Sweep budget. Exhausting it is a legitimate "
                            "outcome, reported as iteration_limit_reached, and "
                            "is not an error."
                        ),
                    },
                },
            },
        },
    }
