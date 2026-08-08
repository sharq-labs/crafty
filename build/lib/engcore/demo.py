from .models import Variable, DesignSpace
from .domain import cooling_benchmark
from .engine import SmartExperimentEngine

def main():
    space = DesignSpace([
        Variable("fan_diameter_mm", 100, 260, "mm"),
        Variable("blade_pitch_deg", 10, 42, "deg"),
        Variable("rpm", 900, 4200, "rpm"),
        Variable("duct_area_cm2", 80, 520, "cm^2"),
    ])

    engine = SmartExperimentEngine(space, cooling_benchmark, seed=7)
    result = engine.run(
        initial_trials=32,
        smart_trials=68,
        candidate_pool=4096,
        patience=18,
    )

    best = result["best"]
    print("=" * 64)
    print("Engineering AI Core V0.1 — Smart Experiment Demo")
    print("=" * 64)
    print(f"Experiments actually run: {result['trials_run']}")
    print(f"Best score: {best.score:.4f}")
    print("Best design:")
    for k, v in space.as_dict(best.x).items():
        print(f"  {k:20s}: {v:.4f}")
    print("Metrics:")
    for k, v in best.metadata.items():
        if k != "reasons":
            print(f"  {k:20s}: {v}")
    print("=" * 64)
    print("NOTE: this is a synthetic benchmark, not validated engineering physics.")

if __name__ == "__main__":
    main()
