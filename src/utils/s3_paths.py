"""
Single source of truth for asset identity and S3 key construction.

Partition layout (Hive-style, generic across domains):

    raw/domain=<domain>/source_id=<source_id>/year=<Y>/month=<M>/day=<D>/<filename>.npy
    raw/domain=<domain>/source_id=<source_id>/year=<Y>/month=<M>/day=<D>/<filename>.json

domain/source_id/year/month/day let S3-aware readers (Spark, Athena, Glue)
prune files without scanning everything under raw/. Every field used here
(domain, source_id, start_time_utc, duration_sec) already exists on every
RawSignal regardless of which domain it came from — no per-domain logic
needed in this file.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

RAW_PREFIX = "raw"


@dataclass(frozen=True)
class AssetKey:
    """
    Identity for one ingested window, plus everything needed to derive
    its S3 location. Built once (usually via compute_asset_key), passed
    around instead of a raw string so partitioning logic lives in one
    place only.
    """
    domain: str
    source_id: str
    start_time_utc: float
    duration_sec: float

    @property
    def partition_prefix(self) -> str:
        dt = datetime.fromtimestamp(self.start_time_utc, tz=timezone.utc)
        return (
            f"domain={self.domain}/source_id={self.source_id}/"
            f"year={dt.year:04d}/month={dt.month:02d}/day={dt.day:02d}"
        )

    @property
    def filename(self) -> str:
        return f"{self.source_id}_{self.start_time_utc:.3f}_{self.duration_sec:.3f}"

    @property
    def npy_key(self) -> str:
        return f"{RAW_PREFIX}/{self.partition_prefix}/{self.filename}.npy"

    @property
    def json_key(self) -> str:
        return f"{RAW_PREFIX}/{self.partition_prefix}/{self.filename}.json"

    def __str__(self) -> str:
        return f"{self.partition_prefix}/{self.filename}"


def compute_asset_key(domain: str, source_id: str, start: float, duration: float) -> AssetKey:
    """
    start is start_time_utc (epoch float, canonical per RawSignal contract).
    """
    return AssetKey(
        domain=domain,
        source_id=source_id,
        start_time_utc=start,
        duration_sec=duration,
    )