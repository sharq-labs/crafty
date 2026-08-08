"""Guarded V0.3.5 ablation entry point.

The registered V0.3.4 arena is preserved byte-for-byte.  V0.3.5 reuses its
validated scientific apparatus while hardening the *artifact boundary*:

- ``adaptive_stacked_v035`` is a new scientific identity;
- the output directory is atomically claimed before any campaign starts;
- manifest and progress journal use exclusive creation and strict JSON;
- every journal record is bound to one campaign id;
- summary JSON is written strictly from a temporary legacy rendering, so no
  NaN/Infinity artifact is ever committed to the scientific output directory.

There is deliberately no resume mode yet.  A crashed/claimed directory is
considered spent; using a fresh output path is safer than mixing campaigns.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .adaptive_stacked_engine_v035 import AdaptiveStackedGPBOEngineV035
from .v035_ablation_analysis import _strict_json_value, strict_json_dumps


_LOCK_NAME = ".v035-campaign.lock"


def _requested_out(argv: list[str]) -> Path:
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            raise SystemExit("--out requires a directory")
        return Path(argv[i + 1])
    return Path("validation_results/v035_ablation_smoke")


def _guard_empty_output(out_dir: Path) -> None:
    """Human-readable preflight check; atomic claim happens separately."""

    if not out_dir.exists():
        return
    if not out_dir.is_dir():
        raise SystemExit(f"Refusing campaign: --out is not a directory: {out_dir}")
    if any(out_dir.iterdir()):
        raise SystemExit(
            "Refusing campaign: output directory is not empty. "
            "Use a new --out directory; V0.3.5 does not silently append or "
            "overwrite scientific campaign state."
        )


def _claim_output(out_dir: Path, campaign_id: str) -> tuple[int, Path]:
    """Atomically claim a campaign output directory.

    ``O_EXCL`` closes the check/use race for two processes targeting the same
    path.  The lock file is intentionally retained after completion (or crash)
    so a scientific directory can never be accidentally reused.
    """

    out_dir = Path(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    try:
        out_dir.mkdir()
    except FileExistsError:
        if not out_dir.is_dir():
            raise SystemExit(
                f"Refusing campaign: --out is not a directory: {out_dir}"
            )
        # This is a preflight convenience only. The O_EXCL lock below is the
        # authoritative race-safe claim.
        entries = list(out_dir.iterdir())
        if entries:
            raise SystemExit(
                "Refusing campaign: output directory is not empty. "
                "Use a new --out directory."
            )

    lock_path = out_dir / _LOCK_NAME
    try:
        fd = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o644,
        )
    except FileExistsError as exc:
        raise SystemExit(
            "Refusing campaign: output directory is already claimed by "
            "another or previous V0.3.5 campaign."
        ) from exc

    os.write(
        fd,
        (
            f"campaign_id={campaign_id}\n"
            f"pid={os.getpid()}\n"
            "status=running\n"
        ).encode("utf-8"),
    )
    os.fsync(fd)
    return fd, lock_path


def _finish_claim(fd: int, campaign_id: str, *, status: str) -> None:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(
            fd,
            (
                f"campaign_id={campaign_id}\n"
                f"pid={os.getpid()}\n"
                f"status={status}\n"
            ).encode("utf-8"),
        )
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_text_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())


def _copy_exclusive(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Path(src).open("rb") as source, Path(dst).open("xb") as target:
        shutil.copyfileobj(source, target)
        target.flush()
        os.fsync(target.fileno())


def _make_progress_journal_class(campaign_id: str):
    class V035ProgressJournal:
        """Append during one run, but create the journal exclusively."""

        def __init__(self, path):
            self.path = Path(path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = self.path.open("x", encoding="utf-8", newline="")

        def write(self, payload):
            record = dict(payload)
            record["campaign_id"] = campaign_id
            line = strict_json_dumps(record, sort_keys=True) + "\n"
            self._fh.write(line)
            self._fh.flush()
            os.fsync(self._fh.fileno())

        def close(self):
            try:
                self._fh.close()
            except Exception:
                pass

    return V035ProgressJournal


def _write_manifest_v035(
    out_dir,
    args,
    functions,
    dimensions,
    instances,
    *,
    campaign_id: str,
):
    """V0.3.5-owned strict manifest writer."""

    from . import v034_ablation_arena as arena

    expected_cases = len(functions) * len(dimensions) * len(instances)
    manifest = {
        "kind": "v035_ablation_manifest",
        "schema": "ablation-manifest/2",
        "campaign_id": campaign_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv[1:],
        "config": {
            "functions": functions,
            "dimensions": dimensions,
            "instances": instances,
            "budget_multiplier": int(args.budget_multiplier),
            "base_seed": int(args.seed),
            "stacked_mode": args.stacked_mode,
            "screen_device": args.screen_device,
            "refinement_backend": args.stacked_refinement_backend,
            "coco_observer": args.coco_observer,
            "seed_formula": "base_seed + 10000*instance + 100*function + dim",
        },
        "arms": dict(arena.SCIENTIFIC_IDS),
        "expected_cases": expected_cases,
        "expected_runs": expected_cases * len(arena.SCIENTIFIC_IDS),
        "git": arena._git_state(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "threading": arena._threading_state(),
            "packages": {
                name: arena._package_version(name)
                for name in (
                    "numpy",
                    "scipy",
                    "scikit-learn",
                    "torch",
                    "gpytorch",
                    "botorch",
                    "cocoex",
                )
            },
        },
        "hardening": {
            "strict_json": True,
            "exclusive_manifest": True,
            "exclusive_progress_journal": True,
            "atomic_output_claim": True,
            "resume": False,
        },
    }

    path = Path(out_dir) / "manifest.json"
    _write_text_exclusive(
        path,
        strict_json_dumps(manifest, indent=2, sort_keys=True),
    )
    return path


def _strict_write_results(traces, out_dir):
    """Render legacy tabular output in temp storage, publish strict artifacts.

    This avoids even a transient non-standard ``summary.json`` in the final
    campaign directory. Trace metadata is sanitized before the legacy CSV
    writer runs, so its embedded ``metadata_json`` field is standards-compliant
    too.
    """

    from .validation.arena import write_results as legacy_write_results

    for trace in traces:
        trace.metadata = _strict_json_value(dict(trace.metadata or {}))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="v035_results_") as tmp:
        tmp_dir = Path(tmp)
        summary, summary_text, csv_path, _json_path, txt_path = (
            legacy_write_results(traces, tmp_dir)
        )

        clean_summary = _strict_json_value(summary)
        final_csv = out_dir / "runs.csv"
        final_json = out_dir / "summary.json"
        final_txt = out_dir / "summary.txt"

        _copy_exclusive(csv_path, final_csv)
        _write_text_exclusive(
            final_json,
            strict_json_dumps(clean_summary, indent=2, sort_keys=True),
        )
        _copy_exclusive(txt_path, final_txt)

    return clean_summary, summary_text, final_csv, final_json, final_txt


def run_adaptive_stacked_v035(*args, **kwargs):
    """Reuse the validated adapter while substituting the V0.3.5 engine."""

    from . import adaptive_stacked_engine as legacy_module
    from .validation.optimizers import run_adaptive_stacked

    original = legacy_module.AdaptiveStackedGPBOEngine
    legacy_module.AdaptiveStackedGPBOEngine = AdaptiveStackedGPBOEngineV035
    try:
        trace = run_adaptive_stacked(*args, **kwargs)
    finally:
        legacy_module.AdaptiveStackedGPBOEngine = original

    trace.algorithm = "adaptive_stacked_v035"
    trace.metadata = dict(trace.metadata or {})
    trace.metadata["engine_id"] = "adaptive_stacked_v035"
    trace.metadata["review_hardening"] = {
        "exploration_starts_refinement_visible": True,
        "adaptive_generation_failure_fallback": "identity",
    }
    return trace


def main() -> None:
    argv = list(sys.argv[1:])
    out_dir = _requested_out(argv)
    _guard_empty_output(out_dir)

    campaign_id = uuid.uuid4().hex
    lock_fd, _lock_path = _claim_output(out_dir, campaign_id)
    completed = False

    # Make the default output V0.3.5-specific when the caller did not supply it.
    if "--out" not in argv:
        sys.argv.extend(["--out", str(out_dir)])

    from . import v034_ablation_arena as arena

    original_runner = arena.run_adaptive_stacked
    original_id = arena.SCIENTIFIC_IDS["adaptive_stacked"]
    original_journal = arena._ProgressJournal
    original_manifest = arena._write_manifest
    original_write_results = arena.write_results

    arena.run_adaptive_stacked = run_adaptive_stacked_v035
    arena.SCIENTIFIC_IDS["adaptive_stacked"] = "adaptive_stacked_v035"
    arena._ProgressJournal = _make_progress_journal_class(campaign_id)
    arena._write_manifest = lambda out, args, funcs, dims, insts: (
        _write_manifest_v035(
            out,
            args,
            funcs,
            dims,
            insts,
            campaign_id=campaign_id,
        )
    )
    arena.write_results = _strict_write_results

    try:
        arena.main()
        completed = True
    finally:
        arena.run_adaptive_stacked = original_runner
        arena.SCIENTIFIC_IDS["adaptive_stacked"] = original_id
        arena._ProgressJournal = original_journal
        arena._write_manifest = original_manifest
        arena.write_results = original_write_results
        _finish_claim(
            lock_fd,
            campaign_id,
            status="complete" if completed else "incomplete",
        )


if __name__ == "__main__":
    main()
