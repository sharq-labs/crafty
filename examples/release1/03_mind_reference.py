"""Release 1 Example 03: Public V1 attributable D3 design memory."""

from __future__ import annotations

import hashlib
import json

from engcore.design import (
    DesignMemoryLayerA,
    DesignMemoryPolicy,
    DesignMemoryRecord,
    DesignMemoryScope,
)
from engcore.scientific import (
    InvalidScientificProblem,
    ObjectiveDefinition,
    ObjectiveDirection,
    Quantity,
)
from engcore.systems.aerospace.multirotor import run_reference_study


OBJECTIVES = (
    ObjectiveDefinition(
        name="total_mass",
        metric="total_mass",
        direction=ObjectiveDirection.MINIMIZE,
        unit="kg",
    ),
    ObjectiveDefinition(
        name="hover_endurance",
        metric="hover_endurance",
        direction=ObjectiveDirection.MAXIMIZE,
        unit="s",
    ),
)


def _rotor_count_partition(assignments) -> bytes:
    return str(assignments["rotor_count"].value).encode("ascii")


def main() -> None:
    run = run_reference_study(
        count=4,
        attempt_budget=20,
        source_revision="release1-example-03",
    )
    scope = DesignMemoryScope(
        design_space=run.design_space.reference,
        objectives=OBJECTIVES,
        context_reference="release1-mvr0-reference-context-a",
    )
    layer_a = DesignMemoryLayerA.build(
        scope=scope,
        candidates=run.batch.candidates,
        evaluations=run.evaluations,
        partitioner=_rotor_count_partition,
    )
    policy = DesignMemoryPolicy(
        policy_id="release1-public-d3-reference-policy",
        elite_scopes=(("total_mass",), ("hover_endurance",)),
        extreme_tolerances={
            "total_mass": Quantity(0.0, "kg"),
            "hover_endurance": Quantity(0.0, "s"),
        },
        cap=4,
    )
    memory = DesignMemoryRecord.build(layer_a=layer_a, policy=policy)

    other_scope = DesignMemoryScope(
        design_space=run.design_space.reference,
        objectives=OBJECTIVES,
        context_reference="release1-mvr0-reference-context-b",
    )
    cross_scope_rejected = False
    try:
        scope.require_same_scope(other_scope)
    except InvalidScientificProblem:
        cross_scope_rejected = True

    retained = memory.classification.retained_identities
    memory_sha256 = hashlib.sha256(memory.to_json().encode("utf-8")).hexdigest()
    summary = {
        "system": "MVR0 multirotor analytic reference",
        "physical_validation": False,
        "scope_identity": scope.scope_identity,
        "different_context_scope_identity": other_scope.scope_identity,
        "cross_scope_comparison_rejected": cross_scope_rejected,
        "eligible_attributable_entries": len(layer_a.entries),
        "retained_entry_count": len(retained),
        "retained_memory_identities": list(retained),
        "classification_census": memory.classification.summary["per_reason_census"],
        "memory_record_sha256": memory_sha256,
        "source_result_ids": [evaluation.result.result_id for evaluation in run.evaluations],
        "mind_semantics": (
            "Memory retains attributable eligible evidence under declared policy; "
            "retention is not scientific truth."
        ),
    }
    print("MIND V1 - PUBLIC D3 ATTRIBUTABLE MEMORY")
    print("ANALYTIC REFERENCE SYSTEM - NOT PHYSICAL VALIDATION")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
