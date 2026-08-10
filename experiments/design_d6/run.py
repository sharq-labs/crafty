from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from engcore.design import d6_next_experiment as d6


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
RESULTS_PATH = ARTIFACT_DIR / "d6_results.json"
REPORT_PATH = ARTIFACT_DIR / "d6_report.md"


def _write_report(payload: dict[str, Any]) -> None:
    lines = [
        "# D6 Next Experiment Intelligence Evidence",
        "",
        "## Selection",
        "",
        f"- selected option: `{payload['decision']['identity_payload']['selected_option_label']}`",
        f"- selected option identity: `{payload['decision']['identity_payload']['selected_option_identity']}`",
        f"- decision identity: `{payload['decision']['decision_identity']}`",
        f"- best predicted-performance option: `{payload['best_predicted_performance_option']}`",
        f"- raw information-units winner: `{payload['raw_information_units_winner']}`",
        "",
        "## Signal Table",
        "",
    ]
    for label, row in payload["signal_table"].items():
        lines.append(
            f"- {label}: alpha=({row['alpha_predicted_yield']}, {row['alpha_predicted_loss']}, "
            f"{row['alpha_predicted_stability']}), beta=({row['beta_predicted_yield']}, "
            f"{row['beta_predicted_loss']}, {row['beta_predicted_stability']}), "
            f"uncertainty={row['uncertainty']}, disagreement={row['model_disagreement']}, "
            f"novelty={row['novelty_distance']}, info/cost={row['information_per_compute']}"
        )
    lines += ["", "## Ordering", ""]
    for row in payload["selection_ordering"]:
        lines.append(
            f"- {row['rank']}. {row['label']}: {row['information_per_compute']}; "
            f"info={row['information_units']}; disagreement={row['model_disagreement']}"
        )
    lines += ["", "## Selected Execution", ""]
    execution = payload["selected_execution"]
    lines.append(f"- assignment: `{execution['assignment']}`")
    lines.append(f"- ScientificResult: `{execution['scientific_result']}`")
    lines.append(f"- target_pass: `{execution['target_pass']}`")
    lines.append(
        "- uncertainty/disagreement: "
        f"`{execution['pre_execution_uncertainty']}/{execution['pre_execution_disagreement']}` "
        f"to `{execution['post_execution_uncertainty']}/{execution['post_execution_disagreement']}`"
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
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    targeted_tests = os.environ.get(
        "D6_TARGETED_TEST_RESULT",
        "NOT RUN - tests/test_design_d6_next_experiment.py",
    )
    full_regression = os.environ.get("D6_FULL_REGRESSION_RESULT", "NOT RUN")
    payload = d6.experiment_payload(
        targeted_tests=targeted_tests,
        full_regression=full_regression,
    )
    payload["external_frozen_milestones_unchanged"] = ["MVR0", "MVR1"]
    RESULTS_PATH.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_report(payload)
    print(json.dumps(payload["selection_ordering"], sort_keys=True, indent=2))
    if not payload["blocking_gates_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
