import csv
import json
from collections import defaultdict
from pathlib import Path

rows = list(
    csv.DictReader(
        Path(
            "validation_results/bbob_holdout_d3_i71_v033/runs.csv"
        ).open(encoding="utf-8")
    )
)
by = defaultdict(dict)
for r in rows:
    by[r["problem_id"]][r["algorithm"]] = r

adapt_better = stack_better = ties = 0
no_acc = []
print(
    "pid,s,a,delta,acc,gen,steps,rescue_a,forced"
)
for pid in sorted(by):
    s = float(by[pid]["stacked_v0301"]["best_f"])
    a = float(by[pid]["adaptive_stacked_v033"]["best_f"])
    md = json.loads(
        by[pid]["adaptive_stacked_v033"]["metadata_json"]
    )
    acc = int(md["adaptive_proposals_accepted"])
    gen = int(md["adaptive_proposals_generated"])
    upd = int(md["adaptive_policy_updates"])
    print(
        f"{pid},{s:.6g},{a:.6g},{a - s:.6g},"
        f"{acc},{gen},{upd},"
        f"{md.get('adaptive_rescue_accepted')},"
        f"{md.get('adaptive_forced_refits')}"
    )
    if abs(a - s) <= 1e-12:
        ties += 1
    elif a < s:
        adapt_better += 1
    else:
        stack_better += 1
    if acc == 0:
        no_acc.append(pid)

print("COUNTS", adapt_better, stack_better, ties)
print("NO_ACC", no_acc)

pol = 0
acc_tot = 0
for r in rows:
    if not r["algorithm"].startswith("adaptive"):
        continue
    md = json.loads(r["metadata_json"])
    pol += int(md["adaptive_policy_updates"])
    acc_tot += int(md["adaptive_proposals_accepted"])
print(
    "policy_updates",
    pol,
    "accepted",
    acc_tot,
    "identity_executed",
    pol - acc_tot,
)

print("REGRESSIONS_ON_ACCEPT:")
for pid in sorted(by):
    md = json.loads(
        by[pid]["adaptive_stacked_v033"]["metadata_json"]
    )
    if int(md["adaptive_proposals_accepted"]) == 0:
        continue
    s = float(by[pid]["stacked_v0301"]["best_f"])
    a = float(by[pid]["adaptive_stacked_v033"]["best_f"])
    if a > s + 1e-12:
        floor = max(abs(s), 1e-12)
        print(
            pid,
            "abs",
            a - s,
            "rel",
            (a - s) / floor,
        )
