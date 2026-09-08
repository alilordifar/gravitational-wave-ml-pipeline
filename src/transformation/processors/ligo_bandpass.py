"""
LIGO-specific frequency-domain cleaning: a Butterworth bandpass filter,
applied zero-phase (filtfilt) so it doesn't shift the signal in time —
important since window timing (window_start_time_utc) has to stay accurate
for downstream matched-filtering / event alignment in Gold.

Default band (20 Hz-2000 Hz) is where LIGO's detectors are most sensitive
and astrophysical signals are expected to live; below it, seismic noise
dominates, above it, the data is dominated by other instrumental noise.

Kept Spark-free, same reasoning as windower.py: this runs once per window
(thousands of samples), not at Spark scale — Spark enters one layer up, in
src/pipelines/silver_batch.py.
"""

import numpy as np
from scipy.signal import butter, filtfilt

LOW_FREQ_HZ = 20.0
HIGH_FREQ_HZ = 2000.0
FILTER_ORDER = 4


def apply_bandpass(
    samples: np.ndarray,
    sample_rate_hz: float,
    low_freq_hz: float = LOW_FREQ_HZ,
    high_freq_hz: float = HIGH_FREQ_HZ,
    order: int = FILTER_ORDER,
) -> np.ndarray:
    """
    samples: one window's raw values
    sample_rate_hz: the asset's sample rate (e.g. 4096 for LIGO H1)

    Returns a new array, same shape as `samples`, with everything outside
    [low_freq_hz, high_freq_hz] attenuated. filtfilt applies the filter
    forward then backward, cancelling the phase shift a single pass would
    introduce, at the cost of running the filter twice.
    """
    nyquist = sample_rate_hz / 2.0
    if high_freq_hz >= nyquist:
        raise ValueError(
            f"high_freq_hz={high_freq_hz} must be < Nyquist ({nyquist}) "
            f"for sample_rate_hz={sample_rate_hz}"
        )

    b, a = butter(order, [low_freq_hz / nyquist, high_freq_hz / nyquist], btype="band")
    return filtfilt(b, a, samples)
