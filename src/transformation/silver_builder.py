"""
Builds Silver rows from one asset's Bronze rows plus that asset's raw
array (downloaded once, shared across every window it contains).

Mirrors bronze_builder.py's shape: pure Python/NumPy, no I/O, no Spark —
the S3 download and the Spark write both happen one layer up, in
src/pipelines/silver_batch.py.
"""

import numpy as np

from src.transformation.quality_checks import check_window_quality
from src.transformation.processors.registry import get_processor


def build_silver_rows(bronze_rows: list[dict], raw_array: np.ndarray, domain: str) -> list[dict]:
    """
    bronze_rows: every Bronze row for ONE asset_key (i.e. sharing one raw
                 .npy file) — must include start_idx, end_idx and
                 sample_rate_hz, as produced by bronze_builder.build_bronze_rows
    raw_array: the full asset array those start_idx/end_idx slice into
    domain: which processor to run on valid windows (see processors/registry.py)

    Returns one Silver row per Bronze row: every Bronze field carried
    through unchanged, plus quality flags from quality_checks.py and (for
    windows that pass those checks) a bandpass-filtered copy of that
    window's samples. Windows that fail quality checks keep
    filtered_samples=None rather than being dropped — a failed window is
    still useful downstream as a labeled negative example, just not as a
    filtered one.
    """
    processor = get_processor(domain)
    silver_rows = []

    for row in bronze_rows:
        samples = raw_array[row["start_idx"]:row["end_idx"]]
        quality = check_window_quality(samples)

        filtered_samples = None
        if quality["is_valid"]:
            filtered_samples = processor(samples, row["sample_rate_hz"]).tolist()

        silver_rows.append({
            **row,
            **quality,
            "filtered_samples": filtered_samples,
        })

    return silver_rows
