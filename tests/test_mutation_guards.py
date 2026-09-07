"""Apply every mutation in ``mutation_guards.py`` and require the suite to redden.

This is the executable form of standing rule 1: *make each new guard fail
once, on purpose, and watch it fail*. Doing it once by hand proves the guard
worked on the day it was written. Doing it here proves it still works.

Mechanics: the repository is copied to a scratch tree (source and the named
tests only — no ``.git``, no caches), one substitution is applied, and pytest
is run **in a fresh process** against that tree with only the node ids the
mutation claims to break. If they all still pass, the mutation is undetected
and this fails, naming it.

Marked expensive: each mutation is a separate interpreter start.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from mutation_guards import MUTATIONS, Mutation

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _scratch_tree(destination: pathlib.Path) -> None:
    """A runnable copy: the package, the tests, and the pytest config."""
    shutil.copytree(
        REPO_ROOT / "src", destination / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )
    shutil.copytree(
        REPO_ROOT / "tests", destination / "tests",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(REPO_ROOT / "pyproject.toml", destination / "pyproject.toml")


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m.name)
def test_the_mutation_is_detected(mutation: Mutation, tmp_path: pathlib.Path) -> None:
    tree = tmp_path / "tree"
    _scratch_tree(tree)

    target = tree / mutation.path
    source = target.read_text(encoding="utf-8")
    occurrences = source.count(mutation.old)
    assert occurrences == 1, (
        f"{mutation.name}: `old` matched {occurrences} times in "
        f"{mutation.path}; it must match exactly once or the mutation is not "
        f"the defect it claims to be"
    )
    target.write_text(source.replace(mutation.old, mutation.new), encoding="utf-8")

    environment = dict(os.environ)
    environment["PYTHONUTF8"] = "1"
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "-q", "--no-header", "-p",
         "no:cacheprovider", *mutation.breaks],
        cwd=str(tree), capture_output=True, text=True, env=environment,
    )
    assert completed.returncode != 0, (
        f"{mutation.name}: the suite stayed GREEN with this defect applied "
        f"({mutation.why}). The guard does not guard it.\n"
        f"--- stdout ---\n{completed.stdout[-3000:]}"
    )
