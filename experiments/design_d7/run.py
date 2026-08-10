from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from experiments.design_d7.loop import experiment_payload


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
CHECKPOINT_PATH = ARTIFACT_DIR / "d7_checkpoint-v0.1.json"
RESULTS_PATH = ARTIFACT_DIR / "d7_results.json"
REPORT_PATH = ARTIFACT_DIR / "d7_report.md"


def _atomic_text(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _report(payload: dict[str, Any]) -> str:
    lines = [
        "# D7 Integrated Scientific Discovery Loop Evidence",
        "",
        "## Closed Return Arrow",
        "",
        f"- selected option: `{payload['selected_option']}`",
        f"- selected ScientificResult: `{payload['selected_result']['result_id']}` = `{payload['selected_result']['values']}`; target `{payload['selected_result']['target']}`",
        f"- D1 evaluation: `{payload['returned_d1_evaluation']['identity']}` / `{payload['returned_d1_evaluation']['status']}`",
        f"- returned D3 entry: `{payload['returned_d3_memory']['identity']}`",
        f"- next-cycle D4 source: `{payload['next_cycle_d4_source_identity']}`",
        "- Generation 2 executed: `false`",
        "",
        "## Generation 0 and Replicate",
        "",
    ]
    for evaluation_id, item in payload["generation0_results"].items():
        lines.append(
            f"- `{evaluation_id}`: candidate `{item['candidate_id']}`, run `{item['run_id']}`, "
            f"result `{item['result_id']}`, values `{item['values']}`, target `{item['target']}`"
        )
    lines += [
        "",
        "## D3 / D4 / D5",
        "",
        f"- exact D3 selected evaluations: `{payload['d3_memory_and_source_selection']['selected_evaluation_ids']}`",
        f"- replicate substituted: `{payload['d3_memory_and_source_selection']['replicate_substituted']}`",
        f"- D4 event: `{payload['d4']['event_identity']}`",
        f"- D4 derivation: `{payload['d4']['derivation_identity']}`",
        f"- D4 child: `{payload['d4']['child_candidate_identity']}` / `{payload['d4']['child_twin_identity']}`",
        f"- D4 child equals D5 member: `{payload['d4_child_equals_d5_member']}`",
        f"- successor result: `{payload['successor_evaluation']}`",
        "",
        "## Typed D5 to D6 Evidence",
        "",
    ]
    for item in payload["decision_evidence_bindings"]:
        lines.append(
            f"- `{item['identity']}` / `{item['digest']}`: candidate `{item['candidate_id']}`, "
            f"evaluation `{item['evaluation_id']}`, result `{item['result_id']}`, run `{item['run_id']}`"
        )
    lines += ["", "## Option Signals and Selection", ""]
    for label, item in payload["signal_table"].items():
        lines.append(
            f"- {label}: information `{item['information_proxy_units']}`, cost `{item['compute_cost']}`, "
            f"ratio `{item['information_per_compute']}`, novelty `{item['novelty']}`, "
            f"disagreement `{item['model_disagreement']}`"
        )
    lines.append("")
    for item in payload["selection_ordering"]:
        lines.append(
            f"- rank {item['rank']}: {item['label']} / `{item['option_identity']}` / "
            f"ratio `{item['information_per_compute']}` / information `{item['information_units']}`"
        )
    lines += [
        "",
        "## Checkpoint / Selected Execution / Return",
        "",
        f"- checkpoint: `{payload['checkpoint']}`",
        f"- selected identities: `{payload['selected_identities']}`",
        f"- ResultBinding: `{payload['selected_result_binding']['identity']}` / `{payload['selected_result_binding']['digest']}`",
        f"- final trace identity: `{payload['object_trace']['final_trace_identity']}`",
        "",
        "## A1-A23",
        "",
    ]
    for gate, status in payload["a1_a23"].items():
        lines.append(f"- {gate}: {status}")
    lines += ["", "## N1-N24", ""]
    for case, result in payload["n1_n24"].items():
        lines.append(f"- {case}: {result['status']} - {result['observed']}")
    lines += ["", "## One Adversarial Scientific Review", ""]
    for severity in ("P0/P1", "P2", "P3"):
        findings = payload["adversarial_review"][severity]
        if findings:
            for finding in findings:
                lines.append(f"- {severity}: {finding}")
        else:
            lines.append(f"- {severity}: none")
    for finding in payload["adversarial_review"].get("Resolved during review", []):
        lines.append(f"- Resolved during review: {finding}")
    lines += ["", "## Architecture Actually Pulled", ""]
    for name, finding in payload["architecture_actually_pulled"].items():
        lines.append(f"- {name}: {finding}")
    lines += ["", "## Informative I1-I7", ""]
    for name, finding in payload["informative_i1_i7"].items():
        lines.append(f"- {name}: {finding}")
    lines += [
        "",
        "## Frozen Semantics",
        "",
        f"Unchanged: `{payload['frozen_semantics_unchanged']}`.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    payload = experiment_payload(
        checkpoint_path=CHECKPOINT_PATH,
        targeted_tests=os.environ.get("D7_TARGETED_TEST_RESULT", "NOT RUN - tests/test_design_d7_integrated_loop.py"),
        full_regression=os.environ.get("D7_FULL_REGRESSION_RESULT", "NOT RUN"),
    )
    _atomic_text(RESULTS_PATH, json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n")
    _atomic_text(REPORT_PATH, _report(payload))
    print(json.dumps({
        "winner": payload["selected_option"],
        "selected_result": payload["selected_result"],
        "returned_evaluation": payload["returned_d1_evaluation"],
        "returned_memory": payload["returned_d3_memory"],
        "next_cycle_d4_source_identity": payload["next_cycle_d4_source_identity"],
        "blocking_gates_passed": payload["blocking_gates_passed"],
    }, sort_keys=True, indent=2))
    if not payload["adversarial_cases_passed"] or payload["adversarial_review_has_p0_p1"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
