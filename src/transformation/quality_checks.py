"""
Pure statistical sanity checks on one window's raw samples. No I/O, no
Spark, no domain-specific science — just the structural checks any signal
window should pass before Silver spends effort filtering it: no NaN/Inf,
not a flatline, not a stretch of exact zeros.

Deliberately domain-agnostic (unlike processors/ligo_bandpass.py): every
domain's windows can run through the same checks, since "the array
contains garbage" isn't a LIGO-specific failure mode. Deeper, domain-aware
checks (e.g. GWOSC data-quality flags, glitch detection) can layer on top
of this later without changing this contract.
"""

import numpy as np


def check_window_quality(samples: np.ndarray) -> dict:
    """
    samples: one window's raw values (e.g. raw_array[start_idx:end_idx]
             sliced from the asset's full .npy array)

    Returns a dict of boolean flags plus a single `is_valid` verdict — the
    row-level fields Silver needs to decide whether a window is worth
    filtering and passing on to Gold. `is_valid` is False whenever any of
    the other flags is True.
    """
    has_nan = bool(np.isnan(samples).any())
    has_inf = bool(np.isinf(samples).any())
    is_flatline = bool(np.nanstd(samples) == 0.0)
    all_zero = bool(np.all(samples == 0.0))

    is_valid = not (has_nan or has_inf or is_flatline or all_zero)

    return {
        "has_nan": has_nan,
        "has_inf": has_inf,
        "is_flatline": is_flatline,
        "all_zero": all_zero,
        "is_valid": is_valid,
    }
