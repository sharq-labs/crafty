STACKED_MODE_CONFIGS = {
    "fast": {
        "refit_interval": 6,
        "screen_pool": 50_000,
        "screen_chunk_size": 2048,
        "top_k": 6,
        "refinement_top_k": 3,
        "diversity_radius": 0.035,
        "refinement_maxiter": 35,
        "refinement_timeout_sec": 2.0,
        "stagnation_trigger": 6,
        "pulse_interval": 8,
        "pulse_screen_pool": 100_000,
        "severe_stagnation_trigger": 14,
        "severe_screen_pool": 250_000,
    },
    "balanced": {
        "refit_interval": 4,
        "screen_pool": 100_000,
        "screen_chunk_size": 2048,
        "top_k": 8,
        "refinement_top_k": 4,
        "diversity_radius": 0.035,
        "refinement_maxiter": 50,
        "refinement_timeout_sec": 3.0,
        "stagnation_trigger": 6,
        "pulse_interval": 6,
        "pulse_screen_pool": 250_000,
        "severe_stagnation_trigger": 12,
        "severe_screen_pool": 500_000,
    },
    "quality": {
        "refit_interval": 4,
        "screen_pool": 200_000,
        "screen_chunk_size": 2048,
        "top_k": 12,
        "refinement_top_k": 6,
        "diversity_radius": 0.030,
        "refinement_maxiter": 80,
        "refinement_timeout_sec": 5.0,
        "stagnation_trigger": 5,
        "pulse_interval": 5,
        "pulse_screen_pool": 400_000,
        "severe_stagnation_trigger": 10,
        "severe_screen_pool": 750_000,
    },
}


def get_stacked_mode(name):
    key = str(name).lower()
    if key not in STACKED_MODE_CONFIGS:
        raise KeyError(
            f"Unknown mode {name!r}. "
            f"Choose one of: {', '.join(STACKED_MODE_CONFIGS)}"
        )
    return dict(STACKED_MODE_CONFIGS[key])
