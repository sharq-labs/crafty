from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
import warnings
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

from .models import Variable, DesignSpace
from .domain import cooling_benchmark
from .engine import SmartExperimentEngine


def make_space():
    return DesignSpace([
        Variable("fan_diameter_mm", 100, 260, "mm"),
        Variable("blade_pitch_deg", 10, 42, "deg"),
        Variable("rpm", 900, 4200, "rpm"),
        Variable("duct_area_cm2", 80, 520, "cm^2"),
    ])


def random_search(space, evaluator, trials=500, seed=42):
    rng = np.random.default_rng(seed)
    best_score = -np.inf
    best_result = None
    curve = []

    for _ in range(trials):
        x01 = rng.random(space.dim)
        x = space.denormalize(x01)
        score, feasible, metadata = evaluator(x)

        if feasible and score > best_score:
            best_score = float(score)
            best_result = (x.copy(), float(score), metadata)

        curve.append(best_score)

    return best_result, curve


def smart_search(space, evaluator, total_budget=100, seed=7):
    initial = min(32, max(8, total_budget // 3))
    smart = max(0, total_budget - initial)

    engine = SmartExperimentEngine(space, evaluator, seed=seed)
    result = engine.run(
        initial_trials=initial,
        smart_trials=smart,
        candidate_pool=4096,
        patience=max(16, total_budget),
        min_improvement=1e-6,
    )

    best_so_far = -np.inf
    curve = []
    for r in engine.history:
        if r.feasible and r.score > best_so_far:
            best_so_far = r.score
        curve.append(best_so_far)

    return result, curve


def safe_curve(curve):
    arr = np.array(curve, dtype=float)
    if np.isneginf(arr).all():
        return np.zeros_like(arr)
    first_valid = np.where(np.isfinite(arr))[0]
    if len(first_valid):
        arr[:first_valid[0]] = arr[first_valid[0]]
    return arr


def main():
    out_dir = Path("benchmark_results")
    out_dir.mkdir(exist_ok=True)

    space = make_space()

    # Same maximum budget for fair comparison
    budget = 100

    random_best, random_curve = random_search(
        space, cooling_benchmark, trials=budget, seed=7
    )
    smart_result, smart_curve = smart_search(
        space, cooling_benchmark, total_budget=budget, seed=7
    )

    random_curve = safe_curve(random_curve)
    smart_curve = safe_curve(smart_curve)

    random_score = random_best[1] if random_best else float("-inf")
    smart_best = smart_result["best"]
    smart_score = smart_best.score

    # Save convergence CSV
    csv_path = out_dir / "convergence.csv"
    max_len = max(len(random_curve), len(smart_curve))
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["experiment", "random_best_score", "smart_best_score"])
        for i in range(max_len):
            r = random_curve[i] if i < len(random_curve) else random_curve[-1]
            s = smart_curve[i] if i < len(smart_curve) else smart_curve[-1]
            writer.writerow([i + 1, r, s])

    # Plot convergence
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111)
    ax.plot(range(1, len(random_curve) + 1), random_curve, label="Random Search")
    ax.plot(range(1, len(smart_curve) + 1), smart_curve, label="Smart Experiment Engine")
    ax.set_xlabel("Experiments")
    ax.set_ylabel("Best Score So Far")
    ax.set_title("Random Search vs Smart Experiment Engine")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    graph_path = out_dir / "convergence.png"
    fig.savefig(graph_path, dpi=160)
    plt.close(fig)

    # Save summary
    summary = []
    summary.append("=" * 72)
    summary.append("Engineering AI Core V0.2 — Benchmark")
    summary.append("=" * 72)
    summary.append(f"Budget per method: {budget} experiments")
    summary.append("")
    summary.append(f"Random Search best score: {random_score:.6f}")
    summary.append(f"Smart Engine best score : {smart_score:.6f}")
    summary.append(f"Smart experiments run   : {smart_result['trials_run']}")
    summary.append("")

    if np.isfinite(random_score) and random_score != 0:
        diff = ((smart_score - random_score) / abs(random_score)) * 100.0
        summary.append(f"Smart vs Random score difference: {diff:+.3f}%")

    # Compare how many experiments each method needs to reach 99% of the better final score
    target = 0.99 * max(random_score, smart_score)

    def first_hit(curve, target):
        for i, v in enumerate(curve, start=1):
            if v >= target:
                return i
        return None

    random_hit = first_hit(random_curve, target)
    smart_hit = first_hit(smart_curve, target)

    summary.append(f"Target score (99% of best final): {target:.6f}")
    summary.append(f"Random experiments to target: {random_hit}")
    summary.append(f"Smart experiments to target : {smart_hit}")
    summary.append("")
    summary.append("Smart best design:")
    for k, v in space.as_dict(smart_best.x).items():
        summary.append(f"  {k:20s}: {v:.4f}")

    summary.append("")
    summary.append("NOTE: synthetic benchmark only; not validated engineering physics.")
    summary.append("=" * 72)

    summary_text = "\n".join(summary)
    (out_dir / "summary.txt").write_text(summary_text, encoding="utf-8")

    print(summary_text)
    print(f"\nSaved graph: {graph_path}")
    print(f"Saved CSV  : {csv_path}")


if __name__ == "__main__":
    main()
