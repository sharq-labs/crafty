"""Deterministic serialization helpers for Scientific Core records.

Rules enforced here:

* every serialized record carries an explicit ``schema`` string
  ``"<name>/<version>"`` so readers can refuse unknown formats;
* enums serialize to their ``value`` (stable, human readable);
* mappings serialize with sorted keys so byte-identical inputs produce
  byte-identical JSON;
* pickle is never a scientific record format.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Mapping

from .errors import ScientificCoreError


def schema_string(name: str, version: int = 1) -> str:
    return f"{name}/{version}"


def require_schema(payload: Mapping[str, Any], expected: str) -> None:
    """Reject a payload whose schema is missing or unknown."""
    found = payload.get("schema")
    if found != expected:
        raise ScientificCoreError(
            f"unsupported schema {found!r}; expected {expected!r}"
        )


def encode(value: Any) -> Any:
    """Recursively convert a value into JSON-compatible primitives.

    Objects exposing ``to_dict()`` are delegated to; enums become their value;
    mappings are emitted with sorted keys.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): encode(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [encode(v) for v in value]
        if isinstance(value, (set, frozenset)):
            items.sort(key=lambda v: json.dumps(v, sort_keys=True))
        return items
    raise ScientificCoreError(
        f"cannot serialize value of type {type(value).__name__}"
    )


def to_json(record: Any, *, indent: int | None = None) -> str:
    """Deterministic JSON for any record exposing ``to_dict()``."""
    payload = record.to_dict() if hasattr(record, "to_dict") else encode(record)
    return json.dumps(payload, sort_keys=True, indent=indent)


def decode_mapping(
    payload: Mapping[str, Any] | None,
    factory,
) -> dict:
    """Rebuild ``{name: object}`` maps produced by :func:`encode`."""
    if not payload:
        return {}
    return {str(k): factory(v) for k, v in payload.items()}


def as_tuple(values) -> tuple:
    return tuple(values) if values is not None else ()
