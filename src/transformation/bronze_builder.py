"""
Merges per-window metadata (from windower.compute_windows) with asset-level
identity (from RawSignal / AssetKey) to produce full Bronze rows.

Fully domain-generic, and now schema-generic too: domain-specific fields
(detector, gps_start, lead, patient_id...) are packed into a single
domain_metadata dict rather than spread as top-level keys. This matches
the Bronze schema, which is now identical across every domain (see
src/ddl/bronze_template.sql) — domain_metadata is a MAP<STRING, STRING>
column, so every value here is cast to str() to match.
"""

from src.transformation.windower import compute_windows
from src.connectors.base import RawSignal
from src.utils.s3_paths import AssetKey


def build_bronze_rows(
    raw_signal: RawSignal,
    asset_key: AssetKey,
    window_duration: float = 2.0,
) -> list[dict]:
    """
    raw_signal: the connector's output for this asset (has sample_rate_hz,
                start_time_utc, num_samples, and domain-specific fields in .extra)
    asset_key: identity used to derive the S3 path Silver will read from
    window_duration: seconds per window

    Returns one dict per window — the full Bronze row shape, ready for
    spark.createDataFrame(). raw_signal.extra is packed whole into a
    domain_metadata dict (values cast to str for MAP<STRING,STRING>
    compatibility) rather than spread as top-level keys. This function
    makes no assumptions about what's inside .extra, so it works unmodified
    for any domain whose connector populates it with that domain's own
    fields — the Bronze table schema never needs to change either.
    """
    window_rows = compute_windows(
        asset_start_time_utc=raw_signal.start_time_utc,
        total_samples=raw_signal.num_samples,
        sample_rate_hz=raw_signal.sample_rate_hz,
        window_duration=window_duration,
    )

    domain_metadata = {k: str(v) for k, v in raw_signal.extra.items()}

    for row in window_rows:
        row["source_id"] = raw_signal.source_id
        row["asset_key"] = asset_key.npy_key
        row["sample_rate_hz"] = raw_signal.sample_rate_hz
        row["asset_start_time_utc"] = raw_signal.start_time_utc
        row["domain_metadata"] = domain_metadata

    return window_rows