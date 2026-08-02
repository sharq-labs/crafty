from src.engcore.models import Variable, DesignSpace
from src.engcore.domain import cooling_benchmark
from src.engcore.engine import SmartExperimentEngine

def test_engine_runs():
    space = DesignSpace([
        Variable("fan_diameter_mm", 100, 260),
        Variable("blade_pitch_deg", 10, 42),
        Variable("rpm", 900, 4200),
        Variable("duct_area_cm2", 80, 520),
    ])
    engine = SmartExperimentEngine(space, cooling_benchmark, seed=1)
    result = engine.run(initial_trials=8, smart_trials=4, candidate_pool=128, patience=4)
    assert result["trials_run"] >= 8
    assert result["best"] is not None
