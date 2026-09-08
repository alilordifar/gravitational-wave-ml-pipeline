import numpy as np

from src.transformation.silver_builder import build_silver_rows


def _bronze_row(window_id, start_idx, end_idx, window_start_time_utc):
    return {
        "window_id": window_id,
        "source_id": "H1",
        "asset_key": "raw/domain=ligo/source_id=H1/year=2015/month=09/day=14/H1_1_1.npy",
        "asset_start_time_utc": 1000.0,
        "start_idx": start_idx,
        "end_idx": end_idx,
        "window_duration": 2.0,
        "window_num_samples": end_idx - start_idx,
        "window_start_time_utc": window_start_time_utc,
        "sample_rate_hz": 4096.0,
        "domain_metadata": {"detector": "H1"},
    }


def test_builds_one_silver_row_per_bronze_row():
    raw_array = np.random.default_rng(0).normal(size=4096 * 4)
    bronze_rows = [
        _bronze_row(0, 0, 8192, 1000.0),
        _bronze_row(1, 8192, 16384, 1002.0),
    ]

    silver_rows = build_silver_rows(bronze_rows, raw_array, domain="ligo")

    assert len(silver_rows) == 2
    for row in silver_rows:
        assert row["is_valid"] is True
        assert row["filtered_samples"] is not None
        assert len(row["filtered_samples"]) == row["window_num_samples"]
        # Bronze fields carried through unchanged
        assert row["source_id"] == "H1"
        assert row["domain_metadata"] == {"detector": "H1"}


def test_invalid_window_has_no_filtered_samples():
    raw_array = np.zeros(8192)  # all-zero -> fails quality check
    bronze_rows = [_bronze_row(0, 0, 8192, 0.0)]

    silver_rows = build_silver_rows(bronze_rows, raw_array, domain="ligo")

    assert silver_rows[0]["is_valid"] is False
    assert silver_rows[0]["filtered_samples"] is None
