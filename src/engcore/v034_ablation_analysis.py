"""Registered statistical analysis for the V0.3.4 three-way ablation.

Pre-registered alongside docs/ablation-protocol-v034.md. This module IS the
registered analysis: it is committed and tagged with the apparatus before the
campaign runs, and it is the only analysis whose outputs feed the
pre-declared decision rules.

Primary endpoints (matched complete cases only — every arm completed):

  Contrast 1:  B vs A   (stacked_fresh_weights_v034 vs stacked_v0301)
  Contrast 2:  C vs B   (adaptive_stacked_v034 vs stacked_fresh_weights_v034)

For each contrast, on paired per-problem best_f (minimization):
  wins / losses / ties (tie = exact best_f equality, the lab convention),
  exact two-sided paired sign test on non-ties,
  Holm correction across the two primary contrasts (family alpha = 0.05),
  Clopper-Pearson CI for the win probability among non-ties at the
  Bonferroni-adjusted 97.5% level (family 95%),
  effect size: win probability and rank-biserial delta = 2*p_hat - 1.

Decision semantics (pre-registered):
  CI entirely above 0.50 -> POSITIVE evidence for the contrast
  CI entirely below 0.50 -> HARMFUL evidence for the contrast
  CI crossing 0.50       -> INCONCLUSIVE

Secondary endpoints (descriptive, never decision-driving):
  - all-case robustness: same contrasts over ALL attempted cases with a
    failed arm scored as a loss to a completed arm (both failed = tie).
    A treatment-dependent failure is evidence about that treatment.
  - practical-relevance band: win-share in [0.42, 0.58] is descriptively
    flagged as "small practical effect at this design size"; this band has
    NO decision authority.

Per-arm accounting (attempted / completed / failed / excluded, with failure
reasons) is reproduced here from the journal so the registered report cannot
omit failures. NON_CONVERGED is reported as not-applicable: the legacy lab
evaluator contract has no such status; it exists in the Scientific
Foundation contracts only.
"""

from __future__ import annotations

import argparse
import json
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


def _sign_test(wins, losses):
    """Exact two-sided sign test + Clopper-Pearson CI on non-ties."""
    n = wins + losses
    if n == 0:
        return {
            "n_nonties": 0,
            "p_value": None,
            "win_probability": None,
            "ci_low": None,
            "ci_high": None,
            "rank_biserial": None,
        }
    from scipy.stats import binomtest
    bt = binomtest(wins, n, p=0.5, alternative="two-sided")
    ci = bt.proportion_ci(confidence_level=CI_LEVEL, method="exact")
    p_hat = wins / n
    return {
        "n_nonties": n,
        "p_value": float(bt.pvalue),
        "win_probability": p_hat,
        "ci_low": float(ci.low),
        "ci_high": float(ci.high),
        "rank_biserial": 2.0 * p_hat - 1.0,
    }


def _holm(p_values):
    """Holm step-down adjusted p-values (None-safe)."""
    indexed = [(i, p) for i, p in enumerate(p_values) if p is not None]
    indexed.sort(key=lambda t: t[1])
    m = len(indexed)
    adjusted = [None] * len(p_values)
    running = 0.0
    for rank, (i, p) in enumerate(indexed):
        val = min(1.0, (m - rank) * p)
        running = max(running, val)
        adjusted[i] = running
    return adjusted


def _verdict(stats):
    if stats["n_nonties"] == 0 or stats["ci_low"] is None:
        return "INCONCLUSIVE (no non-tied cases)"
    if stats["ci_low"] > 0.5:
        return "POSITIVE evidence"
    if stats["ci_high"] < 0.5:
        return "HARMFUL evidence"
    return "INCONCLUSIVE"


def _contrast(runs, cases, arm_hi, arm_lo):
    """Paired contrast over `cases`. A missing run record for a case in
    `cases` means the arm failed there: failure loses to a completed arm;
    two failures tie (failure is a first-class outcome, not missing data).
    For matched-complete case lists the failure branches never trigger."""
    wins = losses = ties = 0
    for pid in cases:
        arms = runs.get(pid, {})
        hi, lo = arms.get(arm_hi), arms.get(arm_lo)
        if hi is None and lo is None:
            ties += 1
        elif hi is None:
            losses += 1  # arm_hi failed, arm_lo completed
        elif lo is None:
            wins += 1
        else:
            if hi["best_f"] < lo["best_f"]:
                wins += 1
            elif hi["best_f"] > lo["best_f"]:
                losses += 1
            else:
                ties += 1
    total = wins + losses + ties
    win_share = (wins + 0.5 * ties) / total if total else None
    result = {
        "arm": arm_hi,
        "baseline": arm_lo,
        "cases": total,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_share": win_share,
        "practical_band_note": (
            "within [0.42, 0.58] descriptive small-effect band"
            if win_share is not None
            and PRACTICAL_BAND[0] <= win_share <= PRACTICAL_BAND[1]
            else "outside descriptive small-effect band"
        ),
        **_sign_test(wins, losses),
    }
    return result


def analyze(journal_path):
    runs, failures, completion = load_journal(journal_path)

    failed_pids = set()
    for f in failures:
        failed_pids.add(f["problem_id"])

    all_arms = {ARM_A, ARM_B, ARM_C}
    matched = sorted(
        pid for pid, arms in runs.items()
        if set(arms) >= all_arms and pid not in failed_pids
    )
    attempted = sorted(set(runs) | failed_pids)

    primary = {}
    for name, hi, lo in CONTRASTS:
        primary[name] = _contrast(runs, matched, hi, lo)
    holm_adj = _holm([primary[n]["p_value"] for n, _, _ in CONTRASTS])
    for (name, _, _), adj in zip(CONTRASTS, holm_adj):
        primary[name]["p_value_holm"] = adj
        primary[name]["verdict"] = _verdict(primary[name])

    robustness = {}
    for name, hi, lo in CONTRASTS:
        robustness[name] = _contrast(runs, attempted, hi, lo)
        robustness[name]["verdict_descriptive"] = _verdict(
            robustness[name]
        )

    report = {
        "kind": "v034_ablation_analysis",
        "schema": "ablation-analysis/1",
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
        "primary_matched_paired": primary,
        "secondary_all_case_robustness": robustness,
        "registered_semantics": {
            "family_alpha": FAMILY_ALPHA,
            "ci_level_per_contrast": CI_LEVEL,
            "multiplicity": "Holm-adjusted p-values reported; CIs at "
                            "Bonferroni-adjusted level (family 95%)",
            "decision": "CI>0.50 positive; CI<0.50 harmful; else "
                        "inconclusive; practical band descriptive only",
        },
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--journal", required=True,
                   help="path to progress.jsonl of the campaign")
    p.add_argument("--out", default=None,
                   help="write ablation_analysis.json here "
                        "(default: alongside the journal)")
    args = p.parse_args()

    report = analyze(args.journal)
    out = Path(args.out) if args.out else (
        Path(args.journal).parent / "ablation_analysis.json"
    )
    out.write_text(json.dumps(report, indent=2, sort_keys=True),
                   encoding="utf-8")

    print("V0.3.4 ablation — registered analysis")
    print("=" * 72)
    print(f"matched cases: {report['matched_cases']}   "
          f"attempted: {report['attempted_cases']}   "
          f"with failures: {len(report['failed_cases'])}")
    for name in ("B_vs_A", "C_vs_B"):
        c = report["primary_matched_paired"][name]
        print(f"\nPRIMARY {name}: {c['arm']} vs {c['baseline']}")
        print(f"  W/L/T = {c['wins']}/{c['losses']}/{c['ties']}  "
              f"win_share={c['win_share']:.3f}" if c['win_share'] is not None
              else "  no cases")
        if c["p_value"] is not None:
            print(f"  sign test p={c['p_value']:.4g} "
                  f"(Holm-adjusted {c['p_value_holm']:.4g}); "
                  f"win probability {c['win_probability']:.3f} "
                  f"CI[{c['ci_low']:.3f}, {c['ci_high']:.3f}] "
                  f"({CI_LEVEL:.1%}); "
                  f"rank-biserial {c['rank_biserial']:+.3f}")
        print(f"  VERDICT: {c['verdict']}   ({c['practical_band_note']})")
    for name in ("B_vs_A", "C_vs_B"):
        r = report["secondary_all_case_robustness"][name]
        print(f"\nSECONDARY robustness {name} (failures count as losses): "
              f"W/L/T = {r['wins']}/{r['losses']}/{r['ties']}  "
              f"descriptive: {r['verdict_descriptive']}")
    print(f"\nReport: {out}")


if __name__ == "__main__":
    main()
