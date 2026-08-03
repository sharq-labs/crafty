"""Registered statistical analysis for the V0.3.4 three-way ablation.

Pre-registered alongside docs/ablation-protocol-v034.md; committed and
tagged with the apparatus BEFORE the campaign runs. This is the only
analysis whose outputs feed the pre-declared decision rules.

PRIMARY inference is FUNCTION-CLUSTERED: the campaign's 120 cases are
24 BBOB functions x 5 instances, and instances of one function are not
independent draws — treating 120 cases as 120 Bernoulli observations
would overstate evidence. For each primary contrast (B vs A, C vs B):

  per function f (24 clusters):
    instance wins / losses / ties on paired best_f (tie = exact equality)
    function_score = (wins - losses) / (wins + losses)   if wins+losses>0
    direction: POSITIVE (>0) / NEGATIVE (<0) / TIE (==0) /
               ALL_TIED (no non-tied instances)

  primary sample = the 24 function directions:
    exact two-sided sign test on non-tied functions,
    Holm correction across the two primary contrasts (family alpha 0.05),
    Clopper-Pearson CI for function-level win probability at the
    Bonferroni-adjusted 97.5% level (family 95%),
    effect size: function-level win probability, rank-biserial 2p-1.

Decision semantics (pre-registered): CI entirely above 0.50 -> POSITIVE
evidence; entirely below -> HARMFUL; crossing -> INCONCLUSIVE.

SECONDARY (descriptive only, never decision-driving, and never presented
as n=120 independent evidence):
  - case-level wins/losses/ties/win-share over matched cases;
  - all-case robustness (failed arm = loss vs completed arm; two failures
    tie) — a treatment-dependent failure is evidence about that treatment;
  - practical-relevance band [0.42, 0.58] on win-share, descriptive.

Per-arm accounting (attempted/completed/failed/excluded + reasons) is
reproduced from the journal. NON_CONVERGED: not applicable (legacy lab
contract has no such status).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ARM_A = "stacked_v0301"
ARM_B = "stacked_fresh_weights_v034"
ARM_C = "adaptive_stacked_v034"
CONTRASTS = (
    ("B_vs_A", ARM_B, ARM_A),
    ("C_vs_B", ARM_C, ARM_B),
)
FAMILY_ALPHA = 0.05
# Bonferroni across the two primary contrasts: per-contrast CI level 97.5%.
CI_LEVEL = 1.0 - FAMILY_ALPHA / len(CONTRASTS)
PRACTICAL_BAND = (0.42, 0.58)

_FN_RE = re.compile(r"bbob_f(\d+)_i")


def _function_of(problem_id):
    m = _FN_RE.search(problem_id)
    return int(m.group(1)) if m else problem_id  # own cluster if unparsable


def load_journal(path):
    runs, failures, completion = {}, [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        kind = rec.get("kind")
        if kind == "run":
            runs.setdefault(rec["problem_id"], {})[rec["algorithm"]] = rec
        elif kind == "failure":
            failures.append(rec)
        elif kind == "campaign_complete":
            completion = rec
    return runs, failures, completion


def _case_outcome(runs, pid, arm_hi, arm_lo):
    """+1 win / -1 loss / 0 tie for arm_hi vs arm_lo on one case.
    A missing record means the arm failed there: failure loses to a
    completed arm; two failures tie (failure is a first-class outcome)."""
    arms = runs.get(pid, {})
    hi, lo = arms.get(arm_hi), arms.get(arm_lo)
    if hi is None and lo is None:
        return 0
    if hi is None:
        return -1
    if lo is None:
        return 1
    if hi["best_f"] < lo["best_f"]:
        return 1
    if hi["best_f"] > lo["best_f"]:
        return -1
    return 0


def _count(runs, cases, arm_hi, arm_lo):
    wins = losses = ties = 0
    for pid in cases:
        o = _case_outcome(runs, pid, arm_hi, arm_lo)
        wins += o == 1
        losses += o == -1
        ties += o == 0
    total = wins + losses + ties
    win_share = (wins + 0.5 * ties) / total if total else None
    return {
        "cases": total, "wins": wins, "losses": losses, "ties": ties,
        "win_share": win_share,
        "practical_band_note": (
            "within [0.42, 0.58] descriptive small-effect band"
            if win_share is not None
            and PRACTICAL_BAND[0] <= win_share <= PRACTICAL_BAND[1]
            else "outside descriptive small-effect band"
        ),
    }


def _sign_test(wins, losses):
    n = wins + losses
    if n == 0:
        return {"n_nonties": 0, "p_value": None, "win_probability": None,
                "ci_low": None, "ci_high": None, "rank_biserial": None}
    from scipy.stats import binomtest
    bt = binomtest(wins, n, p=0.5, alternative="two-sided")
    ci = bt.proportion_ci(confidence_level=CI_LEVEL, method="exact")
    p_hat = wins / n
    return {"n_nonties": n, "p_value": float(bt.pvalue),
            "win_probability": p_hat,
            "ci_low": float(ci.low), "ci_high": float(ci.high),
            "rank_biserial": 2.0 * p_hat - 1.0}


def _holm(p_values):
    indexed = [(i, p) for i, p in enumerate(p_values) if p is not None]
    indexed.sort(key=lambda t: t[1])
    m = len(indexed)
    adjusted = [None] * len(p_values)
    running = 0.0
    for rank, (i, p) in enumerate(indexed):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[i] = running
    return adjusted


def _verdict(stats):
    if stats["n_nonties"] == 0 or stats["ci_low"] is None:
        return "INCONCLUSIVE (no non-tied clusters)"
    if stats["ci_low"] > 0.5:
        return "POSITIVE evidence"
    if stats["ci_high"] < 0.5:
        return "HARMFUL evidence"
    return "INCONCLUSIVE"


def _clustered_contrast(runs, cases, arm_hi, arm_lo):
    """PRIMARY: function-clustered directions over the case list."""
    by_fn = {}
    for pid in cases:
        by_fn.setdefault(_function_of(pid), []).append(pid)

    per_function = []
    pos = neg = tie = all_tied = 0
    for fn in sorted(by_fn, key=str):
        w = l = t = 0
        for pid in by_fn[fn]:
            o = _case_outcome(runs, pid, arm_hi, arm_lo)
            w += o == 1
            l += o == -1
            t += o == 0
        if w + l == 0:
            direction, score = "ALL_TIED", None
            all_tied += 1
        else:
            score = (w - l) / (w + l)
            if score > 0:
                direction = "POSITIVE"
                pos += 1
            elif score < 0:
                direction = "NEGATIVE"
                neg += 1
            else:
                direction = "TIE"
                tie += 1
        per_function.append({
            "function": fn, "instance_wins": w, "instance_losses": l,
            "instance_ties": t, "function_score": score,
            "direction": direction,
        })

    return {
        "arm": arm_hi, "baseline": arm_lo,
        "n_functions": len(by_fn),
        "positive_functions": pos, "negative_functions": neg,
        "tied_functions": tie, "all_tied_functions": all_tied,
        "per_function": per_function,
        **_sign_test(pos, neg),
    }


def analyze(journal_path):
    runs, failures, completion = load_journal(journal_path)
    failed_pids = {f["problem_id"] for f in failures}
    all_arms = {ARM_A, ARM_B, ARM_C}
    matched = sorted(
        pid for pid, arms in runs.items()
        if set(arms) >= all_arms and pid not in failed_pids
    )
    attempted = sorted(set(runs) | failed_pids)

    primary = {}
    for name, hi, lo in CONTRASTS:
        primary[name] = _clustered_contrast(runs, matched, hi, lo)
    holm_adj = _holm([primary[n]["p_value"] for n, _, _ in CONTRASTS])
    for (name, _, _), adj in zip(CONTRASTS, holm_adj):
        primary[name]["p_value_holm"] = adj
        primary[name]["verdict"] = _verdict(primary[name])

    case_level, robustness = {}, {}
    for name, hi, lo in CONTRASTS:
        case_level[name] = _count(runs, matched, hi, lo)
        robustness[name] = _count(runs, attempted, hi, lo)

    return {
        "kind": "v034_ablation_analysis",
        "schema": "ablation-analysis/2",
        "journal": str(journal_path),
        "matched_cases": len(matched),
        "attempted_cases": len(attempted),
        "failed_cases": sorted(failed_pids),
        "per_arm_accounting": (
            completion.get("per_arm_accounting") if completion else None
        ),
        "non_converged_note": (
            "NON_CONVERGED not applicable: legacy lab evaluator contract "
            "has no such status"
        ),
        "primary_function_clustered": primary,
        "secondary_case_level_descriptive": {
            "note": "descriptive only; instances within a function are "
                    "not independent — this is NOT n=120 evidence",
            **case_level,
        },
        "secondary_all_case_robustness": {
            "note": "descriptive only; failed arm scored as loss vs "
                    "completed arm, two failures tie",
            **robustness,
        },
        "registered_semantics": {
            "family_alpha": FAMILY_ALPHA,
            "ci_level_per_contrast": CI_LEVEL,
            "primary_unit": "BBOB function (24 clusters of 5 instances)",
            "multiplicity": "Holm-adjusted p reported; CIs at Bonferroni-"
                            "adjusted level (family 95%)",
            "decision": "function-level CI>0.50 positive; <0.50 harmful; "
                        "else inconclusive; case-level and robustness "
                        "endpoints are descriptive only",
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--journal", required=True)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    report = analyze(args.journal)
    out = Path(args.out) if args.out else (
        Path(args.journal).parent / "ablation_analysis.json"
    )
    out.write_text(json.dumps(report, indent=2, sort_keys=True),
                   encoding="utf-8")

    print("V0.3.4 ablation — registered analysis (function-clustered)")
    print("=" * 72)
    print(f"matched cases: {report['matched_cases']}   "
          f"attempted: {report['attempted_cases']}   "
          f"with failures: {len(report['failed_cases'])}")
    for name in ("B_vs_A", "C_vs_B"):
        c = report["primary_function_clustered"][name]
        print(f"\nPRIMARY (function-clustered) {name}: "
              f"{c['arm']} vs {c['baseline']}")
        print(f"  functions: +{c['positive_functions']} "
              f"-{c['negative_functions']} ={c['tied_functions']} "
              f"all_tied={c['all_tied_functions']} "
              f"(of {c['n_functions']})")
        if c["p_value"] is not None:
            print(f"  sign test on {c['n_nonties']} non-tied functions: "
                  f"p={c['p_value']:.4g} (Holm {c['p_value_holm']:.4g}); "
                  f"win prob {c['win_probability']:.3f} "
                  f"CI[{c['ci_low']:.3f}, {c['ci_high']:.3f}] "
                  f"({CI_LEVEL:.1%}); "
                  f"rank-biserial {c['rank_biserial']:+.3f}")
        print(f"  VERDICT: {c['verdict']}")
        d = report["secondary_case_level_descriptive"][name]
        print(f"  descriptive case-level: W/L/T "
              f"{d['wins']}/{d['losses']}/{d['ties']} "
              f"win_share={d['win_share']:.3f} ({d['practical_band_note']})")
        r = report["secondary_all_case_robustness"][name]
        print(f"  descriptive robustness (failure=loss): W/L/T "
              f"{r['wins']}/{r['losses']}/{r['ties']}")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
