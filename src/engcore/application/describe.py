"""The request contract, published as data.

`API-MCP-V0` fitness question 16 asks whether a **fourth** transport could be
written against this boundary from its published contract alone, without
reading domain source. This module is the machine-readable half of the answer.

Two rules make that answer honest rather than merely present.

**It is derived, never transcribed.** Each execution builds its own half from
the very constants its ``prepare`` enforces. A hand-written schema is a second
statement of the contract that can drift silently from the first; this one
cannot, and a test asserts the derivation rather than the result.

**It publishes constraints, not only field names.** The first form published
one shared quantity fragment claiming "any dimensionally compatible unit" — false
of a field carrying a *difference*, where an affine unit is dimensionally
compatible and refused. A discovery document that is wrong about the one
distinction this milestone paid a measured error to find would have handed that
error to every consumer built from it.

**And it publishes the relation between the two enumerations.** ``execution``
and ``execution_profile`` are not independent: an execution owns the profiles
that mean anything for it. The schema says so with one ``if``/``then`` clause
per execution rather than with two free-floating enums, so a consumer cannot be
told that every combination is legal.

This lives in the application layer, not in a transport, because *what a request
may contain* is a fact about the boundary. MCP happens to have a discovery
channel that carries it (``tools/list``) and HTTP in v0 does not — an asymmetry
this milestone records rather than repairs, since inventing an HTTP endpoint to
match would be building a surface no measured consumer asked for.
"""

from __future__ import annotations

from typing import Any

from .catalog import EXECUTIONS
from .contract import IDENTIFIER_PATTERN, MAX_REQUEST_BYTES, REQUEST_SCHEMA

__all__ = ["quantity_fragment", "request_json_schema"]


def quantity_fragment(
    unit: str, note: str = "", *, difference: bool = False
) -> dict[str, Any]:
    """Every scientific value in this contract, everywhere, has this shape.

    Two keys, both required, no additional properties. A bare number is not
    acceptable anywhere: units remain explicit.

    ``difference`` mirrors ``parse_quantity``'s own argument, and exists so the
    published constraint and the enforced one are written from the same fact.
    """
    if difference:
        admissible = (
            f"A ratio-scale unit dimensionally compatible with {unit}. This "
            f"field carries a DIFFERENCE, not a value, so a unit whose zero is "
            f"conventional (degC, degF) is REFUSED even though it is "
            f"dimensionally compatible: a difference expressed in one is not a "
            f"value of that unit and does not survive conversion."
        )
    else:
        admissible = (
            f"Any unit dimensionally compatible with {unit}. The value is "
            f"restated in {unit} before it reaches any scientific declaration."
        )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["value", "unit"],
        "description": f"Declared unit: {unit}. {note}".strip(),
        "properties": {
            "value": {"type": "number"},
            "unit": {"type": "string", "description": admissible},
        },
    }


def request_json_schema() -> dict[str, Any]:
    """A JSON Schema for ``crafty_execution_request/1``, built from the catalog.

    ``additionalProperties: False`` at every level is not decoration: the
    validator refuses unknown fields rather than ignoring them, and a published
    schema that permitted them would describe a reader Crafty does not have.
    """
    fragments = {
        identity: module.request_fragment()
        for identity, module in sorted(EXECUTIONS.items())
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": REQUEST_SCHEMA,
        # Two refusals that JSON Schema cannot express, published as prose
        # rather than left to be discovered. They are loud when they fire, so
        # a consumer built from this document works and is merely surprised;
        # it should not have to be.
        "description": (
            f"A Crafty execution request. Both transports additionally refuse "
            f"a serialized request larger than {MAX_REQUEST_BYTES} bytes. "
            f"Identifiers that must be unique within one request (for example, "
            f"stage component ids) are refused as a scientific admission "
            f"failure when they collide, because a duplicate would alias every "
            f"endpoint that names it."
        ),
        "type": "object",
        "additionalProperties": False,
        "required": sorted(
            {
                "schema", "execution", "execution_profile", "inputs",
                "coupling", "run_id",
            }
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
            "execution": {"type": "string", "enum": sorted(fragments)},
            "execution_profile": {
                "type": "string",
                "enum": sorted(
                    {p for f in fragments.values() for p in f["profiles"]}
                ),
                "description": (
                    "Required, deliberately: any default here would be a "
                    "default that selects which implementation computes the "
                    "answer. It is a Crafty identity drawn from a closed "
                    "enumeration owned by the chosen execution — never a path, "
                    "a command, or an argument to one. Which profiles are "
                    "legal depends on `execution`; see the allOf clauses. "
                    "Which concrete solver actually ran is reported "
                    "independently, in the response's provenance."
                ),
            },
            "run_id": {
                "type": "string",
                "pattern": IDENTIFIER_PATTERN,
                "maxLength": 64,
                "description": (
                    "Required. Supplied by the caller, because Crafty collects "
                    "nothing on its own. It becomes both the provenance run id "
                    "AND the scientific result id, so it is an identity rather "
                    "than a label and has no default."
                ),
            },
            # Per-execution shapes are stated in the allOf clauses below. The
            # bare declarations here keep the schema valid for a consumer that
            # ignores conditionals; they promise nothing.
            "inputs": {"type": "object"},
            "coupling": {"type": "object"},
        },
        "allOf": [
            {
                "if": {
                    "properties": {"execution": {"const": identity}},
                    "required": ["execution"],
                },
                "then": {
                    "properties": {
                        "execution_profile": {"enum": fragment["profiles"]},
                        "inputs": fragment["inputs"],
                        "coupling": fragment["coupling"],
                    }
                },
            }
            for identity, fragment in sorted(fragments.items())
        ],
    }
