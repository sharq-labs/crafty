"""Analyze i76-80 holdout and combine i71-80 COCO + lab pairwise evidence."""
from __future__ import annotations

import csv
import json
import math
import re
import shutil
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]
CSV76 = ROOT / "validation_results/bbob_holdout_d3_i76_80_v033/runs.csv"
CSVS = [
    ROOT / "validation_results/bbob_holdout_d3_i71_v033/runs.csv",
    ROOT / "validation_results/bbob_holdout_d3_i72_75_v033/runs.csv",
    ROOT / "validation_results/bbob_holdout_d3_i76_80_v033/runs.csv",
]
SRC_LOGS = [
    ROOT / "exdata/validation_results/bbob_holdout_d3_i71_v033/coco_logs",
    ROOT / "exdata/validation_results/bbob_holdout_d3_i72_75_v033/coco_logs",
    ROOT / "exdata/validation_results/bbob_holdout_d3_i76_80_v033/coco_logs",
]
DEST = ROOT / "exdata/validation_results/_combined_d3_i71_80_v033/coco_logs"
ALGOS = ("cmaes", "ngopt", "stacked", "adaptive_stacked")


def analyze_csv(path: Path, label: str):
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    print("=" * 70)
    print("LAB", label, "n_rows", len(rows))
    bad = [r for r in rows if int(r["evaluations"]) != 60]
    print("budget_mismatches", len(bad))
    nans = [
        r["problem_id"] + ":" + r["algorithm"]
        for r in rows
        if not math.isfinite(float(r["best_f"]))
    ]
    print("nans", nans)

    by = defaultdict(dict)
    for r in rows:
        by[r["problem_id"]][r["algorithm"]] = r

    adapt_better = stack_better = ties = 0
    deltas = []
    for pid, d in sorted(by.items()):
        s = float(d["stacked_v0301"]["best_f"])
        a = float(d["adaptive_stacked_v033"]["best_f"])
        deltas.append((pid, a - s, s, a))
        if abs(a - s) <= 1e-12:
            ties += 1
        elif a < s:
            adapt_better += 1
        else:
            stack_better += 1
    print(
        "PAIRWISE adaptive>",
        adapt_better,
        "stacked>",
        stack_better,
        "ties",
        ties,
    )
    deltas_sorted = sorted(deltas, key=lambda t: t[1])
    print("largest_improve", deltas_sorted[0])
    print("largest_regress", deltas_sorted[-1])
    cat = []
    for pid, dlt, s, a in deltas:
        floor = max(abs(s), 1e-12)
        if (a > 50.0 * floor and a - s > 1.0) or (a - s > 100.0 and a > s):
            cat.append((pid, dlt, s, a))
    print("catastrophic", len(cat))
    for c in cat[:10]:
        print("  CAT", c)

    gen = acc = rej = resg = resa = forced = pol = 0
    active = []
    per_acc = {}
    for r in rows:
        if r["algorithm"] != "adaptive_stacked_v033":
            continue
        md = json.loads(r["metadata_json"])
        g = int(md.get("adaptive_proposals_generated", 0))
        a = int(md.get("adaptive_proposals_accepted", 0))
        j = int(md.get("adaptive_proposals_rejected", 0))
        rg = int(md.get("adaptive_rescue_proposals", 0))
        ra = int(md.get("adaptive_rescue_accepted", 0))
        fr = int(md.get("adaptive_forced_refits", 0))
        upd = int(md.get("adaptive_policy_updates", 0))
        gen += g
        acc += a
        rej += j
        resg += rg
        resa += ra
        forced += fr
        pol += upd
        if a > 0:
            active.append(r["problem_id"])
            per_acc[r["problem_id"]] = a
    print(
        "ADAPTIVE gen",
        gen,
        "acc",
        acc,
        "rej",
        rej,
        "rate",
        acc / gen if gen else 0.0,
    )
    print(
        "active",
        len(active),
        "/",
        len(by),
        "rescue_g/a",
        resg,
        resa,
        "forced",
        forced,
        "identity",
        pol - acc,
    )
    hist = defaultdict(int)
    for v in per_acc.values():
        hist[v] += 1
    print("accept_hist", dict(sorted(hist.items())))
    return {
        "n_problems": len(by),
        "adapt_better": adapt_better,
        "stack_better": stack_better,
        "ties": ties,
        "gen": gen,
        "acc": acc,
        "rej": rej,
        "active": len(active),
        "resg": resg,
        "resa": resa,
        "forced": forced,
        "identity": pol - acc,
        "cat": len(cat),
        "largest_improve": deltas_sorted[0],
        "largest_regress": deltas_sorted[-1],
        "per_acc": per_acc,
        "rows": rows,
        "by": by,
    }


def mean_rank_from_rows(rows):
    by = defaultdict(dict)
    for r in rows:
        by[r["problem_id"]][r["algorithm"]] = r
    ranks = defaultdict(list)
    for pid, d in by.items():
        items = sorted(
            ((alg, float(tr["best_f"])) for alg, tr in d.items()),
            key=lambda t: t[1],
        )
        # average ranks for ties
        i = 0
        while i < len(items):
            j = i
            while j < len(items) and abs(items[j][1] - items[i][1]) <= 1e-12:
                j += 1
            avg = 0.5 * ((i + 1) + j)
            for k in range(i, j):
                ranks[items[k][0]].append(avg)
            i = j
    return {alg: float(np.mean(v)) for alg, v in ranks.items()}


def merge_info_entries(*data_lines: str) -> str:
    path = None
    entries = []
    for line in data_lines:
        m = re.match(r"([^,]+),\s*(.*)", line.strip())
        if not m:
            raise ValueError(line)
        path = m.group(1).strip()
        for part in m.group(2).split(","):
            part = part.strip()
            if part:
                entries.append(part)
    entries = sorted(set(entries), key=lambda e: int(e.split(":")[0]))
    return path + ", " + ", ".join(entries)


def merge_all_logs():
    if DEST.exists():
        shutil.rmtree(DEST)
    # start from last source (i76-80), then merge others' instances in
    base = SRC_LOGS[-1]
    for algo in ALGOS:
        shutil.copytree(base / algo, DEST / algo)

    # Collect info/data from all sources per algo/function
    for algo in ALGOS:
        dst = DEST / algo
        # map func -> list of (info_lines_from_source)
        infos = defaultdict(list)
        for src_root in SRC_LOGS:
            src = src_root / algo
            for info in src.glob("*.info"):
                infos[info.name].append((src, info))

        for name, sources in infos.items():
            # read all
            parsed = []
            for src, info in sources:
                lines = info.read_text(encoding="utf-8").splitlines()
                parsed.append((src, lines))
            header = parsed[-1][1][0]
            comment = parsed[-1][1][1]
            data_line = merge_info_entries(*[ln[1][2] for ln in parsed])
            (dst / name).write_text(
                "\n".join([header, comment, data_line]) + "\n",
                encoding="utf-8",
            )
            # merge data files in instance order by concatenating source blocks
            # Use relative path from merged data line
            rel_dat = data_line.split(",")[0].strip()
            for suffix in (".dat", ".tdat", ".rdat", ".mdat"):
                if rel_dat.endswith(".dat"):
                    rel = rel_dat[:-4] + suffix
                else:
                    rel = rel_dat + suffix
                chunks = []
                for src, _lines in parsed:
                    p = src / rel
                    if p.exists():
                        t = p.read_text(encoding="utf-8", errors="replace")
                        if not t.endswith("\n"):
                            t += "\n"
                        chunks.append(t)
                if chunks:
                    outp = dst / rel
                    outp.parent.mkdir(parents=True, exist_ok=True)
                    outp.write_text("".join(chunks), encoding="utf-8")


def coco_metrics(dirs):
    warnings.filterwarnings("ignore")
    import cocopp

    dsl = cocopp.load(dirs)

    def short(a):
        return str(a).split("/")[-1].split("\\")[-1]

    targets = 10.0 ** np.linspace(2, -8, 51)
    scores = {}
    insts = {}
    for alg in sorted({d.algId for d in dsl}):
        ds = [d for d in dsl if d.algId == alg and d.dim == 3]
        rates = []
        all_inst = []
        for d in ds:
            sr = np.asarray(d.detSuccessRates(targets), dtype=float).reshape(
                -1
            )
            rates.append(sr)
            all_inst.extend(list(getattr(d, "instancenumbers", []) or []))
        scores[short(alg)] = float(np.vstack(rates).mean())
        insts[short(alg)] = sorted(set(all_inst))
    print("COMBINED COCO mean target success:")
    for k, v in sorted(scores.items(), key=lambda kv: -kv[1]):
        print(f"  {k:20s} {v:.6f} instances={insts[k]} n_inst={len(insts[k])}")
    return scores, dsl


def main():
    new = analyze_csv(CSV76, "i76-80")

    # Combined lab pairwise across all three CSVs
    all_rows = []
    for p in CSVS:
        all_rows.extend(csv.DictReader(p.open(encoding="utf-8")))
    print("=" * 70)
    print("COMBINED LAB i71-80")
    mr = mean_rank_from_rows(all_rows)
    print("MeanRank", mr)

    by = defaultdict(dict)
    for r in all_rows:
        by[r["problem_id"]][r["algorithm"]] = r
    a_win = s_win = ties = 0
    gen = acc = active_n = forced = cat = 0
    for pid, d in by.items():
        s = float(d["stacked_v0301"]["best_f"])
        a = float(d["adaptive_stacked_v033"]["best_f"])
        if abs(a - s) <= 1e-12:
            ties += 1
        elif a < s:
            a_win += 1
        else:
            s_win += 1
        floor = max(abs(s), 1e-12)
        if (a > 50.0 * floor and a - s > 1.0) or (a - s > 100.0 and a > s):
            cat += 1
        md = json.loads(d["adaptive_stacked_v033"]["metadata_json"])
        gen += int(md.get("adaptive_proposals_generated", 0))
        acci = int(md.get("adaptive_proposals_accepted", 0))
        acc += acci
        forced += int(md.get("adaptive_forced_refits", 0))
        if acci > 0:
            active_n += 1
    print(
        "combined pairwise adaptive>",
        a_win,
        "stacked>",
        s_win,
        "ties",
        ties,
        "n",
        len(by),
    )
    # two-sided binomial / sign test on non-ties
    n_decided = a_win + s_win
    if n_decided > 0:
        bt = binomtest(a_win, n_decided, p=0.5, alternative="two-sided")
        print(
            "sign_test adaptive_wins",
            a_win,
            "of",
            n_decided,
            "p=",
            float(bt.pvalue),
        )
    else:
        print("sign_test undefined")
    print(
        "combined adaptive gen",
        gen,
        "acc",
        acc,
        "rate",
        acc / gen if gen else 0,
        "active",
        active_n,
        "/",
        len(by),
        "forced",
        forced,
        "cat",
        cat,
    )

    print("=" * 70)
    print("Merging COCO logs i71-80")
    merge_all_logs()
    dirs = [str(DEST / a) for a in ALGOS]
    scores, dsl = coco_metrics(dirs)
    sample = [
        d
        for d in dsl
        if d.algId.endswith("stacked")
        and "adaptive" not in d.algId
        and d.funcId == 1
    ][0]
    print("sanity stacked f1 instances", sample.instancenumbers)

    # ERT finite cells
    targets = np.array([1e2, 1e1, 1e0, 1e-1, 1e-2, 1e-3, 1e-5, 1e-8])
    for name in ("stacked", "adaptive_stacked", "ngopt", "cmaes"):
        if name == "stacked":
            ds = [
                d
                for d in dsl
                if d.algId.endswith("stacked") and "adaptive" not in d.algId
            ]
        else:
            ds = [d for d in dsl if d.algId.endswith(name)]
        finite = total = 0
        for d in ds:
            ert = np.asarray(d.detERT(targets), dtype=float)
            total += ert.size
            finite += int(np.sum(np.isfinite(ert)))
        print(f"ERT finite {name}: {finite}/{total}")

    print("Running cocopp...")
    import cocopp

    cocopp.main(dirs)
    print("DONE")
    print("NEW_SUMMARY_KEYS", {k: new[k] for k in new if k not in {"rows", "by", "per_acc"}})


if __name__ == "__main__":
    main()
