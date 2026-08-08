ADAPTIVE_MODE_CONFIGS = {
    "fast": {
        "refit_interval": 6,
        "screen_pool": 50_000,
        "screen_chunk_size": 2048,
        "top_k": 8,
        "refinement_top_k": 4,
        "diversity_radius": 0.035,
        "refinement_maxiter": 40,
        "refinement_timeout_sec": 2.0,
        "refinement_warmup": 10,
        "forced_discrete_interval": 3,
        "refinement_logei_gain": 0.30,
        "stagnation_trigger": 6,
        "pulse_interval": 8,
        "pulse_screen_pool": 100_000,
        "pulse_top_k": 12,
        "pulse_refinement_top_k": 6,
        "pulse_refinement_maxiter": 60,
        "pulse_refinement_timeout_sec": 3.0,
        "uncertainty_trigger": 16,
        "uncertainty_interval": 12,
    },
    "balanced": {
        "refit_interval": 4,
        "screen_pool": 100_000,
        "screen_chunk_size": 2048,
        "top_k": 12,
        "refinement_top_k": 8,
        "diversity_radius": 0.035,
        "refinement_maxiter": 60,
        "refinement_timeout_sec": 3.0,
        "refinement_warmup": 12,
        "forced_discrete_interval": 3,
        "refinement_logei_gain": 0.25,
        "stagnation_trigger": 6,
        "pulse_interval": 6,
        "pulse_screen_pool": 250_000,
        "pulse_top_k": 20,
        "pulse_refinement_top_k": 12,
        "pulse_refinement_maxiter": 100,
        "pulse_refinement_timeout_sec": 5.0,
        "uncertainty_trigger": 14,
        "uncertainty_interval": 10,
    },
    "quality": {
        "refit_interval": 4,
        "screen_pool": 200_000,
        "screen_chunk_size": 2048,
        "top_k": 16,
        "refinement_top_k": 12,
        "diversity_radius": 0.030,
        "refinement_maxiter": 90,
        "refinement_timeout_sec": 5.0,
        "refinement_warmup": 12,
        "forced_discrete_interval": 4,
        "refinement_logei_gain": 0.20,
        "stagnation_trigger": 5,
        "pulse_interval": 5,
        "pulse_screen_pool": 500_000,
        "pulse_top_k": 28,
        "pulse_refinement_top_k": 16,
        "pulse_refinement_maxiter": 140,
        "pulse_refinement_timeout_sec": 8.0,
        "uncertainty_trigger": 12,
        "uncertainty_interval": 8,
    },
}


def get_adaptive_mode(name):
    key = str(name).lower()
    if key not in ADAPTIVE_MODE_CONFIGS:
        raise KeyError(
            f"Unknown mode {name!r}. "
            f"Choose one of: {', '.join(ADAPTIVE_MODE_CONFIGS)}"
        )
    return dict(ADAPTIVE_MODE_CONFIGS[key])
