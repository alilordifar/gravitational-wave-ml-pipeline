"""
Pure window-metadata computation. No I/O, no Spark — just NumPy vector math.

Given one ingested asset's identity and sampling info, returns the row-level
metadata Bronze needs: which slice of the asset each window covers, and when
that window starts in real-world time.

Deliberately kept Spark-free: the row count per asset (thousands, not
millions) doesn't justify distributed computation overhead. Spark enters
only at the DataFrame-creation boundary, in the notebook, not here.
"""

import numpy as np


def compute_windows(
    asset_start_time_utc: float,
    total_samples: int,
    sample_rate_hz: float,
    window_duration: float,
) -> list[dict]:
    """
    asset_start_time_utc: UTC epoch seconds when sample 0 of the asset was recorded
                           (RawSignal.start_time_utc for the whole ingested file)
    total_samples: length of the full raw array (RawSignal.num_samples)
    sample_rate_hz: samples per second
    window_duration: seconds per window (e.g. 2.0)

    Returns one dict per window, ready to hand to spark.createDataFrame().
    Any trailing samples that don't fill a complete window are dropped
    (floor division) rather than padded — partial windows aren't valid
    ML examples.
    """
    window_size = int(sample_rate_hz * window_duration)
    if window_size <= 0:
        raise ValueError("sample_rate_hz * window_duration must be > 0")

    num_windows = total_samples // window_size

    window_ids = np.arange(num_windows)
    start_idx = window_ids * window_size
    end_idx = start_idx + window_size
    window_start_time_utc = asset_start_time_utc + (start_idx / sample_rate_hz)

    return [
        {
            "window_id": int(window_ids[i]),
            "start_idx": int(start_idx[i]),
            "end_idx": int(end_idx[i]),
            "window_duration": float(window_duration),
            "window_num_samples": window_size,
            "window_start_time_utc": float(window_start_time_utc[i]),
        }
        for i in range(num_windows)
    ]