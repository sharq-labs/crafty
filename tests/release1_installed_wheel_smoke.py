"""Run with the isolated environment's Python from outside the checkout.

This is intentionally a plain Python smoke rather than a pytest dependency of
the wheel.  A non-zero exit means the installed Public V1 contract is broken.
"""

from __future__ import annotations

import argparse
import importlib
from importlib.metadata import version
from pathlib import Path

import engcore
from engcore.release1_api import EXPERIMENT_ONLY_SYMBOLS, PUBLIC_V1_MANIFEST


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forbid-source-prefix", type=Path, required=True)
    args = parser.parse_args()

    package_file = Path(engcore.__file__).resolve()
    forbidden = args.forbid_source_prefix.resolve()
    if package_file.is_relative_to(forbidden):
        raise AssertionError(f"source-tree fallback detected: {package_file}")

    entries: list[tuple[str, str]] = []
    for namespaces in PUBLIC_V1_MANIFEST["categories"].values():
        for module_name, symbols in namespaces.items():
            for symbol in symbols:
                entries.append((module_name, symbol))
                module = importlib.import_module(module_name)
                if not hasattr(module, symbol):
                    raise AssertionError(f"missing {module_name}.{symbol}")

    if len(entries) != len(set(entries)):
        raise AssertionError("duplicate fully-qualified Public V1 declaration")
    if {symbol for _, symbol in entries} & EXPERIMENT_ONLY_SYMBOLS:
        raise AssertionError("experiment-only symbol leaked into Public V1")
    if hasattr(engcore, "DesignSpace"):
        raise AssertionError("legacy root DesignSpace remains ambiguous")
    if version("engineering-ai-core") != "1.0.0" or engcore.__version__ != "1.0.0":
        raise AssertionError("installed distribution version mismatch")

    print(
        f"PASS installed Public V1: {len(entries)} symbols from {package_file}"
    )


if __name__ == "__main__":
    main()
