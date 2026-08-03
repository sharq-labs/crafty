"""Merge i71 + i72-75 COCO logs into combined 5-instance folders (analysis only)."""
from __future__ import annotations

import re
import shutil
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC71 = ROOT / "exdata/validation_results/bbob_holdout_d3_i71_v033/coco_logs"
SRC72 = ROOT / "exdata/validation_results/bbob_holdout_d3_i72_75_v033/coco_logs"
DEST = ROOT / "exdata/validation_results/_combined_d3_i71_75_v033/coco_logs"
ALGOS = ("cmaes", "ngopt", "stacked", "adaptive_stacked")


def merge_info(line71: str, line72: str) -> str:
    """
    Merge instance entries from two info data lines.
    Example line:
      data_f1/bbobexp_f1_DIM3.dat, 72:60|3.4e-05, 73:60|...
    """
    # Keep path from 72-75 (same relative path)
    m72 = re.match(r"([^,]+),\s*(.*)", line72.strip())
    m71 = re.match(r"([^,]+),\s*(.*)", line71.strip())
    if not m72 or not m71:
        raise ValueError(f"bad info lines:\n{line71}\n{line72}")
    path = m72.group(1).strip()
    entries = []
    for part in (m71.group(2) + "," + m72.group(2)).split(","):
        part = part.strip()
        if part:
            entries.append(part)
    # sort by instance number
    def inst_key(e):
        return int(e.split(":")[0])

    entries = sorted(set(entries), key=inst_key)
    return path + ", " + ", ".join(entries)


def merge_algo(algo: str):
    src72 = SRC72 / algo
    src71 = SRC71 / algo
    dst = DEST / algo
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src72, dst)

    for info71 in sorted(src71.glob("*.info")):
        info72 = dst / info71.name
        if not info72.exists():
            raise SystemExit(f"missing {info72}")
        lines71 = info71.read_text(encoding="utf-8").splitlines()
        lines72 = info72.read_text(encoding="utf-8").splitlines()
        # Structure: header, comment, data line
        if len(lines71) < 3 or len(lines72) < 3:
            raise SystemExit(f"unexpected info format {info71}")
        merged_data = merge_info(lines71[2], lines72[2])
        out_lines = [lines72[0], lines72[1], merged_data]
        info72.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

        # Merge companion data files: prepend i71 block before i72-75 blocks
        # Extract relative data path from info
        rel = lines72[2].split(",")[0].strip()
        for suffix in (".dat", ".tdat", ".rdat", ".mdat"):
            # rel ends with .dat; swap suffix
            base_rel = rel
            if base_rel.endswith(".dat"):
                file_rel = base_rel[: -4] + suffix
            else:
                file_rel = base_rel + suffix
            p71 = src71 / file_rel
            pdst = dst / file_rel
            if not p71.exists() or not pdst.exists():
                # some suffixes may be missing; skip quietly if both missing
                if p71.exists() and not pdst.exists():
                    pdst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p71, pdst)
                continue
            text71 = p71.read_text(encoding="utf-8", errors="replace")
            text72 = pdst.read_text(encoding="utf-8", errors="replace")
            if not text71.endswith("\n"):
                text71 += "\n"
            pdst.write_text(text71 + text72, encoding="utf-8")


def coco_metrics(log_dirs):
    warnings.filterwarnings("ignore")
    import cocopp

    dsl = cocopp.load(log_dirs)

    def short(a):
        return str(a).split("/")[-1].split("\\")[-1]

    targets = 10.0 ** np.linspace(2, -8, 51)
    scores = {}
    inst_counts = {}
    for alg in sorted({d.algId for d in dsl}):
        ds = [d for d in dsl if d.algId == alg and d.dim == 3]
        rates = []
        n_inst = []
        for d in ds:
            sr = np.asarray(d.detSuccessRates(targets), dtype=float).reshape(-1)
            rates.append(sr)
            n_inst.append(len(getattr(d, "instancenumbers", []) or []))
        R = np.vstack(rates)
        scores[short(alg)] = float(R.mean())
        inst_counts[short(alg)] = (
            int(np.median(n_inst)) if n_inst else 0,
            sorted(set(sum((list(getattr(d, "instancenumbers", []) or []) for d in ds), []))),
        )
    print("COMBINED 5-instance COCO metrics:")
    for k, v in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(
            f"  {k:20s} mean_target_success={v:.6f} "
            f"instances={inst_counts[k]}"
        )
    return scores, dsl


def main():
    print("Merging observer logs into", DEST)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    for algo in ALGOS:
        merge_algo(algo)
        print("  merged", algo)

    dirs = [str(DEST / a) for a in ALGOS]
    scores, dsl = coco_metrics(dirs)

    # sanity: stacked f1 should have 5 instances
    sample = [d for d in dsl if "stacked" in d.algId and "adaptive" not in d.algId and d.funcId == 1][0]
    print(
        "sanity stacked f1 instances",
        sample.instancenumbers,
        "n=",
        len(sample.instancenumbers),
    )

    print("Running cocopp on combined 4 folders...")
    import cocopp

    cocopp.main(dirs)
    print("DONE")


if __name__ == "__main__":
    main()
