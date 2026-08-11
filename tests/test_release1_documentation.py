from __future__ import annotations

from collections import defaultdict
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

from engcore import __version__
from engcore.release1_api import PUBLIC_V1_MANIFEST


REPOSITORY = Path(__file__).resolve().parents[1]
DOCS = REPOSITORY / "docs/release1"
AUTHORITATIVE_DOCS = (
    "architecture.md",
    "quick-start.md",
    "closed-loop.md",
    "scientific-semantics.md",
    "public-api.md",
    "configuration.md",
    "reproducibility.md",
    "limitations.md",
    "release-checklist.md",
)
PUBLIC_DOC = DOCS / "public-api.md"
PACKAGE_MANIFEST = REPOSITORY / "artifacts/release1/package-manifest.json"


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _manifest_summary() -> dict[str, object]:
    namespace_counts: defaultdict[str, int] = defaultdict(int)
    for modules in PUBLIC_V1_MANIFEST["categories"].values():
        for module_name, symbols in modules.items():
            namespace_counts[module_name] += len(symbols)
    return {
        "category_symbol_counts": {
            category: sum(len(symbols) for symbols in modules.values())
            for category, modules in PUBLIC_V1_MANIFEST["categories"].items()
        },
        "distribution": PUBLIC_V1_MANIFEST["distribution"],
        "identity_sha256": hashlib.sha256(
            _canonical_json_bytes(PUBLIC_V1_MANIFEST)
        ).hexdigest(),
        "manifest_schema": PUBLIC_V1_MANIFEST["schema"],
        "namespace_symbol_counts": dict(sorted(namespace_counts.items())),
        "symbol_count": sum(
            len(symbols)
            for modules in PUBLIC_V1_MANIFEST["categories"].values()
            for symbols in modules.values()
        ),
    }


def test_authoritative_document_set_and_landing_page_exist() -> None:
    assert [path.name for path in sorted(DOCS.glob("*.md"))] == sorted(
        AUTHORITATIVE_DOCS
    )
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Scientific Discovery Platform — Release 1\n")
    for name in AUTHORITATIVE_DOCS:
        assert f"docs/release1/{name}" in readme


def test_public_api_summary_is_derived_and_does_not_drift() -> None:
    text = PUBLIC_DOC.read_text(encoding="utf-8")
    block = text.split("<!-- PUBLIC_V1_MANIFEST_SUMMARY:BEGIN -->", 1)[1].split(
        "<!-- PUBLIC_V1_MANIFEST_SUMMARY:END -->", 1
    )[0]
    documented = json.loads(block[block.index("{") : block.rindex("}") + 1])
    assert documented == _manifest_summary()
    assert documented["identity_sha256"] == (
        "f4bd71ced1cc6e68d074dbd10a1c074ac78a112be8a9ad0b6250eb1571715163"
    )


def test_every_documented_public_namespace_and_symbol_imports() -> None:
    text = PUBLIC_DOC.read_text(encoding="utf-8")
    for modules in PUBLIC_V1_MANIFEST["categories"].values():
        for module_name, symbols in modules.items():
            assert module_name in text
            module = importlib.import_module(module_name)
            for symbol in symbols:
                assert hasattr(module, symbol), f"missing {module_name}.{symbol}"


def test_distribution_version_is_synchronized_in_authoritative_docs() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert __version__ == "1.0.0"
    assert PUBLIC_V1_MANIFEST["distribution"]["version"] == __version__
    assert pyproject["project"]["requires-python"] == ">=3.11"
    readme = (REPOSITORY / "README.md").read_text(encoding="utf-8")
    quick_start = (DOCS / "quick-start.md").read_text(encoding="utf-8")
    assert "`engineering-ai-core` `1.0.0`" in readme
    assert "must print `1.0.0`" in quick_start


def test_scientific_non_equivalences_are_explicit() -> None:
    semantics = (DOCS / "scientific-semantics.md").read_text(encoding="utf-8")
    required = (
        "Candidate != Twin",
        "Twin != Model",
        "Model != Solver",
        "Study != Result",
        "Result != Evaluation",
        "Evaluation != Target PASS/FAIL",
        "SelectionEligibility != Target PASS",
        "Memory retention != scientific truth",
        "Prediction != evidence",
        "Decision provenance != scientific evidence",
        "Numerical verification != physical validation",
        "Physical validation != safety certification",
        "Synthetic closed-loop execution != real-world discovery",
    )
    assert all(item in semantics for item in required)


def test_architecture_and_closed_loop_honesty_statements_match_implementation() -> None:
    architecture = (DOCS / "architecture.md").read_text(encoding="utf-8")
    assert "LAB owns scientific execution" in architecture
    assert "MIND does not manufacture scientific truth or evidence" in architecture
    assert "DesignMemory is not a Twin" in architecture
    assert "AI/LLM orchestration is not part of Release 1" in architecture

    closed_loop = (DOCS / "closed-loop.md").read_text(encoding="utf-8")
    example = (REPOSITORY / "examples/release1/04_closed_loop.py").read_text(
        encoding="utf-8"
    )
    for phrase in (
        "REFERENCE SYNTHETIC SCIENTIFIC SYSTEM",
        "NOT PHYSICAL-WORLD VALIDATION",
    ):
        assert phrase in closed_loop
        assert phrase in example
    assert "Generation 2 is not executed" in architecture
    assert "`generation_2_executed` must be exactly `false`" in closed_loop


def test_limitations_are_complete_and_affirmative_prohibited_claims_absent() -> None:
    limitations = (DOCS / "limitations.md").read_text(encoding="utf-8").lower()
    required_limits = (
        "no general physical validation",
        "no production digital-twin registry",
        "no postgresql",
        "no s3",
        "no redis",
        "no distributed execution",
        "no cloud runtime",
        "no cfd",
        "no fea",
        "no general multi-fidelity execution",
        "no real/general uq",
        "no botorch",
        "no bayesian optimization",
        "no autonomous repeated discovery",
        "no generation 2+",
        "no hypothesis intelligence",
        "no llm/ai orchestration",
        "no ui or web service",
        "no medical or clinical validation",
        "no safety or certification claim",
    )
    assert all(item in limitations for item in required_limits)

    authoritative = "\n".join(
        (DOCS / name).read_text(encoding="utf-8").lower()
        for name in AUTHORITATIVE_DOCS
    ) + (REPOSITORY / "README.md").read_text(encoding="utf-8").lower()
    prohibited_affirmative_claims = (
        "release 1 provides autonomous discovery",
        "release 1 supports cfd",
        "release 1 supports fea",
        "the d7 cycle is physically validated",
        "d7 is experimentally validated physics",
        "release 1 provides general scientific intelligence",
        "release 1 provides real uq",
        "release 1 provides bayesian optimization",
        "generation 2 is executed",
    )
    assert not any(claim in authoritative for claim in prohibited_affirmative_claims)


def test_configuration_inventory_preserves_policy_ownership() -> None:
    configuration = (DOCS / "configuration.md").read_text(encoding="utf-8")
    lowered = configuration.lower()
    for heading in (
        "A. SCIENTIFIC DOMAIN POLICY",
        "B. EXPERIMENT FIXTURE",
        "C. RELEASE CONFIGURATION",
        "D. INTERNAL IMPLEMENTATION DETAIL",
    ):
        assert heading in configuration
    assert "no generic global configuration framework is introduced" in lowered
    assert "never promoted to release defaults" in lowered
    assert "not a universal acquisition" in lowered
    assert "no scientific tolerance, equation, target" in lowered


def test_referenced_release_artifacts_exist() -> None:
    authoritative = "\n".join(
        (DOCS / name).read_text(encoding="utf-8") for name in AUTHORITATIVE_DOCS
    ) + (REPOSITORY / "README.md").read_text(encoding="utf-8")
    paths = set(re.findall(r"`(artifacts/release1/[^`]+)`", authoritative))
    assert {
        "artifacts/release1/reference/release1-cycle.json",
        "artifacts/release1/package-manifest.json",
    } <= paths
    for relative in paths:
        assert (REPOSITORY / relative).is_file(), relative


def test_release_checklist_aggregates_all_gate_families() -> None:
    checklist = (DOCS / "release-checklist.md").read_text(encoding="utf-8")
    required = (
        [f"V1-A{index}" for index in range(1, 14)]
        + [f"R1-A{index}" for index in range(1, 6)]
        + [f"R2-A{index}" for index in range(1, 6)]
        + [f"R3-A{index}" for index in range(1, 6)]
        + [f"R6-A{index}" for index in range(1, 7)]
        + [f"RF-A{index}" for index in range(1, 20)]
    )
    assert all(gate in checklist for gate in required)
    assert "PENDING FINAL AUTHORIZATION" in checklist
    for evidence in ("DOC", "EXAMPLES", "PUBLIC", "CYCLE", "BUILD", "INSTALLED", "REPLAY", "TARGETED", "FULL", "FROZEN"):
        assert f"| {evidence} |" in checklist


def test_release_owned_content_inventory_is_complete_and_current() -> None:
    payload = json.loads(PACKAGE_MANIFEST.read_text(encoding="utf-8"))
    entries = payload["release_owned_content"]
    by_path = {entry["path"]: entry for entry in entries}
    expected = {
        "README.md",
        *(f"docs/release1/{name}" for name in AUTHORITATIVE_DOCS),
        *(f"examples/release1/{index:02d}_{name}.py" for index, name in (
            (1, "lab_dc"),
            (2, "twin_attributable_evaluation"),
            (3, "mind_reference"),
            (4, "closed_loop"),
        )),
        "tests/test_release1_documentation.py",
        "tests/test_release1_examples.py",
        "tests/release1_installed_examples.py",
        "artifacts/release1/reference/release1-cycle.json",
    }
    assert set(by_path) == expected
    for relative, entry in by_path.items():
        raw = (REPOSITORY / relative).read_bytes()
        assert entry["size_bytes"] == len(raw), relative
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest(), relative

    assert payload["distribution"]["version"] == __version__
    assert payload["public_api"]["canonical_json_sha256"] == _manifest_summary()[
        "identity_sha256"
    ]
    reference = REPOSITORY / payload["release1_reference_cycle"]["artifact"]
    assert payload["release1_reference_cycle"]["artifact_sha256"] == hashlib.sha256(
        reference.read_bytes()
    ).hexdigest()


def test_frozen_d0_d7_paths_have_no_content_diff_and_tag_is_absent() -> None:
    frozen_pathspecs = (
        "docs/design-d[0-7]*",
        "experiments/design_d[0-7]",
        "src/engcore/design/d4_recombination.py",
        "src/engcore/design/d5_generation.py",
        "src/engcore/design/d6_next_experiment.py",
    )
    completed = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *frozen_pathspecs],
        cwd=REPOSITORY,
        check=False,
    )
    assert completed.returncode == 0
    tags = subprocess.run(
        ["git", "tag", "--list", "v1.0.0"],
        cwd=REPOSITORY,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tags.stdout.strip() == ""
