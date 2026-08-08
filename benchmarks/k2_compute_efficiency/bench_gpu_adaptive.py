"""K2 GPU capability + throughput characterization.

Engineering telemetry only — NOT scientific evidence and NOT a scored K2 run.

Goal
----
Measure whether the currently available GPU(s) accelerate the batched numerical
work that K2 can legitimately send to an accelerator. Selection is capability-
and workload-driven: no GPU model names, VRAM sizes, or vendor product tables
are hard-coded into execution policy.

This benchmark intentionally does NOT move the SciPy adaptive stiff CSTR solve
to CUDA. The existing CSTR forward solve remains a CPU workload. Here we
characterize the already-supported Torch/BoTorch posterior/acquisition path,
where large independent batches are a natural GPU workload.

What is measured
----------------
* CUDA availability and per-device capabilities reported by PyTorch.
* Sustained Expected-Improvement scoring throughput over several batch sizes.
* Peak allocated/reserved VRAM.
* CPU baseline using the exact same Torch/BoTorch implementation.
* Numerical parity of GPU scores against a CPU reference (float64).
* Best measured batch size for each device/workload.

The benchmark chooses by measured throughput subject to numerical parity. A
faster GPU result that disagrees with the CPU reference is rejected.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402

from src.engcore.benchmark import make_space  # noqa: E402
from src.engcore.gpu_surrogate import TorchBotorchSurrogate  # noqa: E402
from src.engcore.hard_domain import hard_cooling_benchmark  # noqa: E402
from src.engcore.sampling import sobol_points  # noqa: E402


@dataclass(frozen=True)
class DeviceCapability:
    index: int
    device: str
    name: str
    cuda: bool
    total_vram_mb: float
    free_vram_mb: float
    compute_capability: str
    multiprocessor_count: int


@dataclass(frozen=True)
class Measurement:
    device: str
    device_index: int
    batch_size: int
    pool_size: int
    wall_s: float
    candidates_per_s: float
    max_abs_error_vs_cpu: float
    max_rel_error_vs_cpu: float
    parity_ok: bool
    peak_allocated_mb: float
    peak_reserved_mb: float


@dataclass(frozen=True)
class Recommendation:
    device: str
    device_index: int
    batch_size: int
    candidates_per_s: float
    speedup_vs_cpu: float
    reason: str


def _device_capabilities(torch) -> list[DeviceCapability]:
    devices: list[DeviceCapability] = []
    if not torch.cuda.is_available():
        return devices

    for index in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(index)
        try:
            free_bytes, total_bytes = torch.cuda.mem_get_info(index)
        except TypeError:
            with torch.cuda.device(index):
                free_bytes, total_bytes = torch.cuda.mem_get_info()
        major, minor = torch.cuda.get_device_capability(index)
        devices.append(
            DeviceCapability(
                index=index,
                device=f"cuda:{index}",
                name=str(props.name),
                cuda=True,
                total_vram_mb=float(total_bytes) / 1024**2,
                free_vram_mb=float(free_bytes) / 1024**2,
                compute_capability=f"{major}.{minor}",
                multiprocessor_count=int(props.multi_processor_count),
            )
        )
    return devices


def _batch_candidates(pool_size: int, free_vram_mb: float | None = None) -> list[int]:
    """Geometric batch scan bounded by the actual workload and device memory.

    The upper bound is intentionally conservative and capability-derived.  It is
    only a search bound; measured throughput still decides the winner.
    """
    candidates = []
    value = 64
    while value <= pool_size:
        candidates.append(value)
        value *= 2

    if pool_size not in candidates:
        candidates.append(pool_size)

    if free_vram_mb and free_vram_mb > 0:
        # Avoid asking a small-memory device to sweep absurdly large batches.
        # This is NOT an allocation model; OOM handling remains authoritative.
        soft_cap = max(64, int(free_vram_mb * 1024**2 // (8 * 256)))
        candidates = [v for v in candidates if v <= soft_cap or v == 64]

    return sorted(set(max(1, min(pool_size, v)) for v in candidates))


def _fit_surrogate(*, force_cpu: bool, device_index: int | None, X, y):
    import torch

    if force_cpu:
        surrogate = TorchBotorchSurrogate(X.shape[1], force_cpu=True)
        surrogate.fit(X, y, optimize=False)
        return surrogate

    if device_index is None:
        raise ValueError("device_index is required for CUDA surrogate")

    with torch.cuda.device(device_index):
        surrogate = TorchBotorchSurrogate(X.shape[1], force_cpu=False)
        # TorchBotorchSurrogate stores torch.device('cuda'), which resolves to
        # the current CUDA device inside this context.
        surrogate.fit(X, y, optimize=False)
        return surrogate


def _score(surrogate, candidates, *, batch_size: int, best_y: float):
    surrogate.reset_peak_memory()
    surrogate.synchronize()
    started = time.perf_counter()
    scores = surrogate.expected_improvement_scores(
        candidates,
        best_y=best_y,
        chunk_size=batch_size,
        min_chunk_size=min(64, batch_size),
    )
    surrogate.synchronize()
    wall = time.perf_counter() - started
    memory = surrogate.memory_stats()
    return scores, wall, memory


def _error(candidate: np.ndarray, reference: np.ndarray) -> tuple[float, float]:
    diff = np.abs(candidate - reference)
    max_abs = float(np.max(diff)) if diff.size else 0.0
    scale = np.maximum(np.abs(reference), np.finfo(np.float64).tiny)
    max_rel = float(np.max(diff / scale)) if diff.size else 0.0
    return max_abs, max_rel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=64)
    parser.add_argument("--pool", type=int, default=65536)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--rtol",
        type=float,
        default=1e-10,
        help="Float64 GPU-vs-CPU score parity tolerance.",
    )
    parser.add_argument(
        "--atol",
        type=float,
        default=1e-12,
        help="Float64 GPU-vs-CPU score parity absolute tolerance.",
    )
    parser.add_argument(
        "--output",
        default="benchmarks/k2_compute_efficiency/gpu_adaptive_results.json",
    )
    args = parser.parse_args()

    if args.train < 8 or args.pool < 64 or args.repeats < 1:
        raise ValueError("need --train >= 8, --pool >= 64, --repeats >= 1")

    try:
        import torch
    except Exception as exc:
        raise RuntimeError(
            "PyTorch is required for the GPU benchmark. Install the project GPU "
            "requirements with a CUDA-enabled PyTorch build first."
        ) from exc

    space = make_space()
    X = sobol_points(args.train, space.dim, args.seed)
    y = np.asarray(
        [hard_cooling_benchmark(space.denormalize(p))[0] for p in X],
        dtype=np.float64,
    )
    candidates = sobol_points(args.pool, space.dim, args.seed + 991)
    best_y = float(np.max(y))

    print("=" * 108)
    print("K2 COMPUTE EFFICIENCY — CAPABILITY-DRIVEN GPU CHARACTERIZATION")
    print("Engineering telemetry only; no hardware model names are used for selection")
    print(f"PyTorch      : {torch.__version__}")
    print(f"CUDA runtime : {getattr(torch.version, 'cuda', None)}")
    print(f"CUDA usable  : {torch.cuda.is_available()}")
    print(f"GPU count    : {torch.cuda.device_count() if torch.cuda.is_available() else 0}")
    print(f"Train points : {args.train}")
    print(f"Pool size    : {args.pool:,}")
    print(f"Repeats      : {args.repeats}")
    print("=" * 108)

    # CPU reference: same model implementation, same dtype, same optimize=False
    # state.  The reference is about execution parity, not GP scientific truth.
    cpu = _fit_surrogate(force_cpu=True, device_index=None, X=X, y=y)
    cpu_batch = min(args.pool, 4096)
    cpu_scores, cpu_wall, _cpu_memory = _score(
        cpu, candidates, batch_size=cpu_batch, best_y=best_y
    )
    cpu_rate = args.pool / cpu_wall if cpu_wall else 0.0
    print(f"CPU reference: {cpu_wall:.4f}s | {cpu_rate:,.0f} candidates/s")

    capabilities = _device_capabilities(torch)
    measurements: list[Measurement] = []
    recommendations: list[Recommendation] = []

    if not capabilities:
        print("\nNo usable CUDA device detected by this PyTorch build.")
        print("The benchmark will save CPU capability data and stop without pretending GPU results exist.")
    else:
        for cap in capabilities:
            print("\n" + "-" * 108)
            print(
                f"Device {cap.index}: {cap.name} | CC {cap.compute_capability} | "
                f"VRAM {cap.total_vram_mb:.0f} MB total / {cap.free_vram_mb:.0f} MB free"
            )
            batches = _batch_candidates(args.pool, cap.free_vram_mb)
            print(f"Batch scan: {batches}")

            with torch.cuda.device(cap.index):
                gpu = _fit_surrogate(
                    force_cpu=False,
                    device_index=cap.index,
                    X=X,
                    y=y,
                )

                # One untimed warm-up so CUDA context/kernel initialization does
                # not masquerade as steady-state K2 latency.
                warm_n = min(1024, args.pool)
                _score(
                    gpu,
                    candidates[:warm_n],
                    batch_size=min(warm_n, 1024),
                    best_y=best_y,
                )

                for batch in batches:
                    best_wall = math.inf
                    best_scores = None
                    best_memory: dict[str, Any] | None = None
                    oom = False

                    for _ in range(args.repeats):
                        try:
                            scores, wall, memory = _score(
                                gpu,
                                candidates,
                                batch_size=batch,
                                best_y=best_y,
                            )
                        except (torch.OutOfMemoryError, RuntimeError) as exc:
                            if isinstance(exc, torch.OutOfMemoryError) or "OOM" in str(exc).upper() or "OUT OF MEMORY" in str(exc).upper():
                                oom = True
                                torch.cuda.empty_cache()
                                break
                            raise
                        if wall < best_wall:
                            best_wall = wall
                            best_scores = scores
                            best_memory = memory

                    if oom:
                        print(f"  batch={batch:8,d}  OOM -> larger batches skipped")
                        break

                    assert best_scores is not None and best_memory is not None
                    max_abs, max_rel = _error(best_scores, cpu_scores)
                    parity = bool(
                        np.allclose(best_scores, cpu_scores, rtol=args.rtol, atol=args.atol)
                    )
                    rate = args.pool / best_wall if best_wall else 0.0
                    row = Measurement(
                        device=cap.device,
                        device_index=cap.index,
                        batch_size=batch,
                        pool_size=args.pool,
                        wall_s=float(best_wall),
                        candidates_per_s=float(rate),
                        max_abs_error_vs_cpu=max_abs,
                        max_rel_error_vs_cpu=max_rel,
                        parity_ok=parity,
                        peak_allocated_mb=float(best_memory["max_allocated_mb"]),
                        peak_reserved_mb=float(best_memory["max_reserved_mb"]),
                    )
                    measurements.append(row)
                    print(
                        f"  batch={batch:8,d}  {best_wall:8.4f}s  "
                        f"{rate:12,.0f} cand/s  "
                        f"xCPU={rate / cpu_rate if cpu_rate else 0.0:6.2f}  "
                        f"parity={'PASS' if parity else 'FAIL'}  "
                        f"peak={row.peak_allocated_mb:8.1f} MB"
                    )

                valid = [
                    m for m in measurements
                    if m.device_index == cap.index and m.parity_ok
                ]
                if valid:
                    best = max(valid, key=lambda m: m.candidates_per_s)
                    recommendations.append(
                        Recommendation(
                            device=cap.device,
                            device_index=cap.index,
                            batch_size=best.batch_size,
                            candidates_per_s=best.candidates_per_s,
                            speedup_vs_cpu=(
                                best.candidates_per_s / cpu_rate if cpu_rate else 0.0
                            ),
                            reason=(
                                "highest measured sustained float64 acquisition "
                                "throughput among numerically parity-valid batches"
                            ),
                        )
                    )

    print("\nRecommendations")
    if not recommendations:
        print("  none — no CUDA configuration passed capability/parity measurement")
    else:
        for rec in recommendations:
            print(
                f"  {rec.device}: batch={rec.batch_size:,}  "
                f"{rec.candidates_per_s:,.0f} cand/s  "
                f"speedup_vs_cpu={rec.speedup_vs_cpu:.2f}x"
            )

    payload = {
        "kind": "k2_capability_driven_gpu_characterization",
        "scientific_evidence": False,
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "torch_cuda_runtime": getattr(torch.version, "cuda", None),
            "cuda_available": bool(torch.cuda.is_available()),
            "gpu_count": int(torch.cuda.device_count() if torch.cuda.is_available() else 0),
        },
        "workload": {
            "operation": "Torch/BoTorch Expected Improvement scoring",
            "dtype": "float64",
            "train_points": args.train,
            "pool_size": args.pool,
            "repeats": args.repeats,
            "cpu_reference_batch": cpu_batch,
            "cpu_reference_wall_s": cpu_wall,
            "cpu_reference_candidates_per_s": cpu_rate,
        },
        "devices": [asdict(v) for v in capabilities],
        "measurements": [asdict(v) for v in measurements],
        "recommendations": [asdict(v) for v in recommendations],
        "policy_boundary": {
            "hardware_name_used_for_selection": False,
            "selection_inputs": [
                "CUDA availability",
                "runtime-visible device capacity",
                "measured sustained throughput",
                "memory safety",
                "float64 numerical parity",
            ],
            "cstr_scipy_forward_solver_moved_to_gpu": False,
            "note": (
                "This is a characterization tool. Production execution policy "
                "should later cache/adapt capability-derived settings by matching "
                "device + workload signatures without changing scientific semantics."
            ),
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nSaved: {output}")


if __name__ == "__main__":
    main()
