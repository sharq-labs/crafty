MODE_CONFIGS = {
    # These are test configurations, not claimed global optima.
    "fast": {
        "refit_interval": 8,
        "global_restarts": 6,
        "global_raw_samples": 128,
        "maxiter": 70,
        "acquisition_timeout_sec": 4.0,
        "local_regions": 0,
        "fallback_guard_points": 1024,
        "duplicate_recovery_points": 1024,
        "stagnation_trigger": 6,
        "pulse_interval": 8,
        "pulse_restarts": 12,
        "pulse_raw_samples": 256,
        "pulse_maxiter": 100,
        "pulse_timeout_sec": 5.0,
        "pulse_local_regions": 0,
    },
    "balanced": {
        "refit_interval": 6,
        "global_restarts": 12,
        "global_raw_samples": 256,
        "maxiter": 100,
        "acquisition_timeout_sec": 5.0,
        "local_regions": 0,
        "fallback_guard_points": 2048,
        "duplicate_recovery_points": 2048,
        "stagnation_trigger": 6,
        "pulse_interval": 6,
        "pulse_restarts": 20,
        "pulse_raw_samples": 512,
        "pulse_maxiter": 160,
        "pulse_timeout_sec": 8.0,
        "pulse_local_regions": 1,
    },
    "quality": {
        "refit_interval": 4,
        "global_restarts": 20,
        "global_raw_samples": 512,
        "maxiter": 160,
        "acquisition_timeout_sec": 8.0,
        "local_regions": 0,
        "fallback_guard_points": 4096,
        "duplicate_recovery_points": 4096,
        "stagnation_trigger": 5,
        "pulse_interval": 5,
        "pulse_restarts": 28,
        "pulse_raw_samples": 1024,
        "pulse_maxiter": 220,
        "pulse_timeout_sec": 12.0,
        "pulse_local_regions": 1,
    },
}


def get_mode(name):
    key = str(name).lower()

    if key not in MODE_CONFIGS:
        raise KeyError(
            f"Unknown mode {name!r}. "
            f"Choose one of: {', '.join(MODE_CONFIGS)}"
        )

    return dict(MODE_CONFIGS[key])
