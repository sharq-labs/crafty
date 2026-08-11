from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from engcore.release1_api import PUBLIC_V1_MANIFEST


REPOSITORY = Path(__file__).resolve().parents[1]
EXAMPLES = REPOSITORY / "examples/release1"
REFERENCE = REPOSITORY / "experiments/design_d7/loop.py"
EXAMPLE_PATHS = tuple(sorted(EXAMPLES.glob("*.py")))


def _manifest_modules() -> dict[str, set[str]]:
    declared: dict[str, set[str]] = {}
    for modules in PUBLIC_V1_MANIFEST["categories"].values():
        for module_name, symbols in modules.items():
            declared.setdefault(module_name, set()).update(symbols)
    return declared


def _run_example(path: Path, tmp_path: Path) -> tuple[str, dict[str, object]]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY / "src")
    environment["PYTHONNOUSERSITE"] = "1"
    command = [sys.executable, str(path)]
    if path.name == "04_closed_loop.py":
        command.extend(
            (
                "--reference",
                str(REFERENCE),
                "--output-dir",
                str(tmp_path / "cycle-output"),
                "--release-commit",
                "release1-example-test",
            )
        )
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    json_start = completed.stdout.find("{")
    assert json_start >= 0, completed.stdout
    return completed.stdout, json.loads(completed.stdout[json_start:])


def test_exactly_four_curated_examples_exist() -> None:
    assert [path.name for path in EXAMPLE_PATHS] == [
        "01_lab_dc.py",
        "02_twin_attributable_evaluation.py",
        "03_mind_reference.py",
        "04_closed_loop.py",
    ]


def test_example_imports_respect_public_v1_and_reference_seam() -> None:
    public = _manifest_modules()
    allowed_release_internal = {
        "04_closed_loop.py": {
            ("engcore.release1_cycle", "revalidate_release1_cycle"),
            ("engcore.release1_cycle", "run_release1_cycle"),
        }
    }
    for path in EXAMPLE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        engcore_imports: set[tuple[str, str]] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("src."), path.name
                    assert not alias.name.startswith("experiments."), path.name
                    if alias.name.startswith("engcore"):
                        engcore_imports.add((alias.name, "*"))
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("src."), path.name
                assert not node.module.startswith("experiments."), path.name
                if node.module.startswith("engcore"):
                    engcore_imports.update(
                        (node.module, alias.name) for alias in node.names
                    )
        internal = allowed_release_internal.get(path.name, set())
        for module_name, symbol in engcore_imports:
            if (module_name, symbol) in internal:
                continue
            assert module_name in public, (path.name, module_name, symbol)
            assert symbol in public[module_name], (path.name, module_name, symbol)
        if path.name != "04_closed_loop.py":
            assert not internal


@pytest.mark.parametrize("filename", [path.name for path in EXAMPLE_PATHS])
def test_curated_example_executes(filename: str, tmp_path: Path) -> None:
    stdout, payload = _run_example(EXAMPLES / filename, tmp_path)
    assert payload
    if filename == "01_lab_dc.py":
        assert "ACTUAL ELECTRICAL DC EXECUTION" in stdout
        assert payload["selected_metrics"]["mid_voltage"] == {
            "magnitude": pytest.approx(9.0),
            "unit": "V",
        }
        assert payload["validation"]["status"] == "pass"
        assert payload["uncertainty"] == "unknown"
    elif filename == "02_twin_attributable_evaluation.py":
        assert payload["candidate_id"] == payload["binding"]["candidate_id"]
        assert payload["fail_closed_candidate_mismatch_rejected"] is True
        assert payload["physical_validation"] is False
    elif filename == "03_mind_reference.py":
        assert payload["eligible_attributable_entries"] == 4
        assert payload["retained_entry_count"] >= 1
        assert payload["cross_scope_comparison_rejected"] is True
        assert "not scientific truth" in payload["mind_semantics"].lower()
    else:
        assert "REFERENCE SYNTHETIC SCIENTIFIC SYSTEM" in stdout
        assert "NOT PHYSICAL-WORLD VALIDATION" in stdout
        assert payload["physical_world_validation"] is False
        assert payload["replay"]["byte_identical_fresh_runs"] is True
        assert payload["replay"]["fresh_run_identity_match"] is True
        assert payload["replay"]["reload_revalidation_identity_match"] is True
        assert payload["generation_2_executed"] is False


def test_closed_loop_refuses_frozen_artifact_output() -> None:
    source = (EXAMPLES / "04_closed_loop.py").read_text(encoding="utf-8")
    assert "refusing to write into frozen D7 artifacts" in source
    assert "engcore.release1_cycle" in source
