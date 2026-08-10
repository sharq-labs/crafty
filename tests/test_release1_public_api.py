from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import engcore
from engcore.release1_api import (
    EXPERIMENT_ONLY_SYMBOLS,
    PUBLIC_V1_MANIFEST,
)


def _declared_entries() -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    categories = PUBLIC_V1_MANIFEST["categories"]
    for category, namespaces in categories.items():
        for module_name, symbols in namespaces.items():
            entries.extend((category, module_name, symbol) for symbol in symbols)
    return entries


def _symbols_for(module_name: str) -> set[str]:
    return {
        symbol
        for _, declared_module, symbol in _declared_entries()
        if declared_module == module_name
    }


def test_public_v1_manifest_is_complete_importable_and_unambiguous() -> None:
    entries = _declared_entries()
    qualified = [(module_name, symbol) for _, module_name, symbol in entries]
    assert len(qualified) == len(set(qualified))

    for _, module_name, symbol in entries:
        module = importlib.import_module(module_name)
        assert hasattr(module, symbol), f"missing {module_name}.{symbol}"

    assert _symbols_for("engcore.scientific") == set(
        importlib.import_module("engcore.scientific").__all__
    )
    assert _symbols_for("engcore.design") == set(
        importlib.import_module("engcore.design").__all__
    )
    for module_name in (
        "engcore.domains.electrical.dc",
        "engcore.domains.thermal.conduction1d",
        "engcore.domains.kinetics.cstr",
        "engcore.domains.fluids.aerodynamics",
        "engcore.systems.aerospace.multirotor",
    ):
        assert _symbols_for(module_name) == set(
            importlib.import_module(module_name).__all__
        )


def test_experiment_only_symbols_are_not_public_v1() -> None:
    declared_symbols = {symbol for _, _, symbol in _declared_entries()}
    assert declared_symbols.isdisjoint(EXPERIMENT_ONLY_SYMBOLS)
    assert set(importlib.import_module("engcore.design").__all__).isdisjoint(
        EXPERIMENT_ONLY_SYMBOLS
    )


def test_design_space_has_one_supported_public_meaning() -> None:
    design_space_locations = {
        module_name
        for _, module_name, symbol in _declared_entries()
        if symbol == "DesignSpace"
    }
    assert design_space_locations == {"engcore.design"}
    assert not hasattr(engcore, "DesignSpace")
    assert engcore.__all__ == ["__version__"]


def test_distribution_metadata_in_manifest_matches_runtime() -> None:
    distribution = PUBLIC_V1_MANIFEST["distribution"]
    assert distribution == {
        "name": "engineering-ai-core",
        "version": "1.0.0",
        "requires_python": ">=3.11",
        "status": "release-1-preparation",
    }
    assert engcore.__version__ == distribution["version"]


def test_release_package_inventory_matches_source_and_public_manifest() -> None:
    repository = Path(__file__).resolve().parents[1]
    payload = json.loads(
        (repository / "artifacts/release1/package-manifest.json").read_text(
            encoding="utf-8"
        )
    )

    canonical_public = json.dumps(
        PUBLIC_V1_MANIFEST, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert hashlib.sha256(canonical_public).hexdigest() == payload["public_api"][
        "canonical_json_sha256"
    ]

    source_root = repository / "src"
    modules: list[str] = []
    for source in (source_root / "engcore").rglob("*.py"):
        module = source.relative_to(source_root).with_suffix("").as_posix().replace(
            "/", "."
        )
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        modules.append(module)
    canonical_modules = json.dumps(
        sorted(modules), separators=(",", ":")
    ).encode("utf-8")
    inventory = payload["package_module_inventory"]
    assert len(modules) == inventory["count"]
    assert hashlib.sha256(canonical_modules).hexdigest() == inventory[
        "canonical_json_sha256"
    ]
