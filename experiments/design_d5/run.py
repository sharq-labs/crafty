from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from engcore.design import d5_generation as d5


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
RESULTS_PATH = ARTIFACT_DIR / "d5_results.json"
REPORT_PATH = ARTIFACT_DIR / "d5_report.md"


def _write_report(payload: dict[str, Any]) -> None:
    metrics = payload["comparison_metrics"]
    lines = [
        "# D5 Generation 1 Evidence",
        "",
        "## Generation 0",
        "",
    ]
    for key, value in metrics["generation0"].items():
        if key != "results":
            lines.append(f"- {key}: `{value}`")
    lines += ["", "## Generation 1 Proposal Outcomes", ""]
    for label, outcome in payload["generation1_proposal_outcomes"].items():
        lines.append(
            f"- {label}: {outcome['compatibility_state']}; "
            f"child_created={outcome['child_created']}; "
            f"target_pass={outcome['target_pass']}; "
            f"result={outcome['scientific_result']}"
        )
    lines += ["", "## Comparison", ""]
    lines.append(f"- pareto_mode: `{metrics['pareto_mode']}`")
    for key, value in metrics["generation1"].items():
        if key != "results":
            lines.append(f"- generation1.{key}: `{value}`")
    lines.append(
        "- parent_relative_objective_improvements: "
        f"`{metrics['parent_relative_objective_improvements']}`"
    )
    lines.append(
        "- parent_relative_underperformance: "
        f"`{metrics['parent_relative_underperformance']}`"
    )
    lines += ["", "## A1-A23", ""]
    for gate, status in payload["a1_a23"].items():
        lines.append(f"- {gate}: {status}")
    lines += ["", "## N1-N18", ""]
    for case, result in payload["n1_n18"].items():
        lines.append(f"- {case}: {result['status']} - {result['observed']}")
    lines += ["", "## Adversarial Review", ""]
    for severity, findings in payload["adversarial_review"].items():
        if findings:
            for finding in findings:
                lines.append(f"- {severity}: {finding}")
        else:
            lines.append(f"- {severity}: none")
    lines += ["", "## Architecture Pulled", ""]
    for concept, evidence in payload["architecture_pulled"].items():
        lines.append(f"- {concept}: {evidence}")
    lines += ["", "## System-Owned Remaining", ""]
    for item in payload["system_owned_remaining"]:
        lines.append(f"- {item}")
    lines += ["", "## Successor Evidence", ""]
    for item in payload["successor_evidence"]:
        lines.append(f"- {item}")
    lines += ["", "## External Frozen Milestones", ""]
    for item in payload.get("external_frozen_milestones_unchanged", ()):
        lines.append(f"- {item}: unchanged")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    targeted_tests = os.environ.get(
        "D5_TARGETED_TEST_RESULT",
        "NOT RUN - tests/test_design_d5_generation.py",
    )
    full_regression = os.environ.get("D5_FULL_REGRESSION_RESULT", "NOT RUN")
    payload = d5.experiment_payload(
        targeted_tests=targeted_tests,
        full_regression=full_regression,
    )
    payload["external_frozen_milestones_unchanged"] = ["MVR0", "MVR1"]
    RESULTS_PATH.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_report(payload)
    print(json.dumps(payload["comparison_metrics"], sort_keys=True, indent=2))
    if not payload["blocking_gates_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
