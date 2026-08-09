"""K2 domain execution bridge.

Scientific meaning stays in the CSTR adapter.  This module only constructs the
frozen K2 parameterized reactor declarations, asks the adapter for admitted
predictions, and compacts those predictions into K2's shared forward-row type.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Mapping, Sequence

# Avoid nested BLAS/OpenMP fan-out when K2 uses process-level parallelism.
for _name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import numpy as np

from src.engcore.domains.kinetics.cstr.inference import CSTRInferenceForwardAdapter
from src.engcore.domains.kinetics.cstr.problem import CA_FINAL_METRIC, T_FINAL_METRIC
from src.engcore.inference import (
    AdmittedForwardRow,
    AdmittedForwardTable,
    GaussianObservation,
    InferenceAdmissibilityError,
    ObservationSet,
)
from src.engcore.scientific.units.quantity import Quantity

from .k2_config import (
    CONDITION_BY_ID,
    MULTI_CONDITION_IDS,
    OBSERVABLE_NAMES,
    PARAMETER_NAMES,
    PRIMARY_SEED,
    SIGMA_CONCENTRATION,
    SIGMA_TEMPERATURE,
    TRUTH_COORDINATES,
    chemistry_from_coordinates,
)


@dataclass(frozen=True)
class ForwardTask:
    index: int
    coordinates: tuple[float, float]


def _sigma_for(observable_name: str) -> Quantity:
    if observable_name == CA_FINAL_METRIC:
        return SIGMA_CONCENTRATION
    if observable_name == T_FINAL_METRIC:
        return SIGMA_TEMPERATURE
    raise ValueError(f"K2 has no noise declaration for observable {observable_name!r}")


def evaluate_truth_predictions(
    *, condition_ids: Sequence[str] = MULTI_CONDITION_IDS
) -> dict[str, object]:
    """Evaluate the frozen synthetic truth through the full K1.5 boundary."""
    chemistry = chemistry_from_coordinates(*TRUTH_COORDINATES)
    adapter = CSTRInferenceForwardAdapter()
    predictions: dict[str, object] = {}
    for condition_id in condition_ids:
        condition = CONDITION_BY_ID[str(condition_id)]
        predictions[condition.condition_id] = adapter.evaluate(
            condition.build(chemistry),
            observable_names=OBSERVABLE_NAMES,
            run_id_prefix=f"k2-truth-{condition.condition_id}",
        )
    return predictions


def truth_means(
    *, condition_ids: Sequence[str] = MULTI_CONDITION_IDS
) -> dict[str, Quantity]:
    predictions = evaluate_truth_predictions(condition_ids=condition_ids)
    means: dict[str, Quantity] = {}
    for condition_id, prediction in predictions.items():
        for observable_name in OBSERVABLE_NAMES:
            means[f"{condition_id}:{observable_name}"] = prediction.value(observable_name)
    return means


def observation_set_from_truth_means(
    means: Mapping[str, Quantity],
    *,
    seed: int = PRIMARY_SEED,
    condition_ids: Sequence[str] = MULTI_CONDITION_IDS,
    dataset_id: str | None = None,
) -> ObservationSet:
    """Generate seeded synthetic measurements from already-admitted truth means."""
    rng = np.random.default_rng(int(seed))
    observations: list[GaussianObservation] = []
    for condition_id in condition_ids:
        condition_id = str(condition_id)
        for observable_name in OBSERVABLE_NAMES:
            key = f"{condition_id}:{observable_name}"
            if key not in means:
                raise ValueError(f"missing truth mean {key!r}")
            mean = means[key]
            sigma = _sigma_for(observable_name).to(mean.units)
            noisy = mean.magnitude + float(rng.normal(0.0, sigma.magnitude))
            observations.append(
                GaussianObservation(
                    condition_id=condition_id,
                    observable_name=observable_name,
                    value=Quantity(noisy, mean.units),
                    sigma=sigma,
                    source_ref=f"synthetic-truth-seed:{int(seed)}:{key}",
                )
            )
    return ObservationSet(
        observations=tuple(observations),
        dataset_id=dataset_id or f"K2-seed-{int(seed)}",
    )


def generate_observation_set(
    *,
    seed: int = PRIMARY_SEED,
    condition_ids: Sequence[str] = MULTI_CONDITION_IDS,
) -> ObservationSet:
    """Convenience path for one-off studies; scored runs should reuse truth means."""
    means = truth_means(condition_ids=condition_ids)
    return observation_set_from_truth_means(
        means,
        seed=seed,
        condition_ids=condition_ids,
    )


def _evaluate_task(
    task: ForwardTask,
    observations: ObservationSet,
    condition_ids: tuple[str, ...],
) -> AdmittedForwardRow:
    log_k0, e_over_r_k = task.coordinates
    try:
        chemistry = chemistry_from_coordinates(log_k0, e_over_r_k)
        adapter = CSTRInferenceForwardAdapter()
        predictions = {}
        for condition_id in condition_ids:
            condition = CONDITION_BY_ID[condition_id]
            predictions[condition_id] = adapter.evaluate(
                condition.build(chemistry),
                observable_names=OBSERVABLE_NAMES,
                run_id_prefix=f"k2-grid-{task.index}-{condition_id}",
            )
        return AdmittedForwardRow.from_predictions(
            task.coordinates,
            observations,
            predictions,
        )
    except InferenceAdmissibilityError as exc:
        return AdmittedForwardRow.rejected(task.coordinates, observations, str(exc))


def _worker_count(requested: str | int, tasks: int) -> int:
    if isinstance(requested, int):
        if requested < 1:
            raise ValueError("workers must be at least one")
        return min(requested, max(tasks, 1))
    text = str(requested).strip().lower()
    if text != "auto":
        return _worker_count(int(text), tasks)
    logical = max(1, int(os.cpu_count() or 1))
    # For small batches Windows spawn/IPC can exceed the scientific work.  The
    # cutoff is workload-derived from available task count, not a CPU model.
    if tasks < logical:
        return 1
    return min(logical, tasks)


def build_forward_table(
    points: np.ndarray,
    observations: ObservationSet,
    *,
    condition_ids: Sequence[str] = MULTI_CONDITION_IDS,
    workers: str | int = "auto",
) -> AdmittedForwardTable:
    """Evaluate a complete parameter grid once, serially or through one reused pool."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("K2 points must have shape (N, 2)")
    condition_ids = tuple(str(value) for value in condition_ids)
    tasks = [
        ForwardTask(index=i, coordinates=(float(row[0]), float(row[1])))
        for i, row in enumerate(points)
    ]
    n_workers = _worker_count(workers, len(tasks))
    if n_workers == 1:
        rows = [_evaluate_task(task, observations, condition_ids) for task in tasks]
    else:
        # Candidate rows are expensive and can vary materially in solve work.
        # chunksize=1 is a correctness-neutral load-balancing baseline; K2's
        # later feedback policy may tune it without changing any science.
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            rows = list(
                executor.map(
                    _evaluate_task,
                    tasks,
                    [observations] * len(tasks),
                    [condition_ids] * len(tasks),
                    chunksize=1,
                )
            )
    return AdmittedForwardTable.from_rows(PARAMETER_NAMES, observations, rows)
