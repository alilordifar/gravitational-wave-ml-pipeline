from astropy.time import Time
from gwpy.timeseries import TimeSeries

from src.connectors.base import SourceConnector, RawSignal
from src.connectors.registry import register

class LigoGwoscConnector(SourceConnector):
    """Fetches LIGO strain data from GWOSC via GWpy."""

    def fetch(self, config: dict) -> RawSignal:
        detector = config["detector"]
        gps_start = config["gps_start"]
        duration = config["duration_sec"]
        sample_rate = config["sample_rate_hz"]

        ts = TimeSeries.fetch_open_data(
            detector,
            gps_start,
            gps_start + duration,
            sample_rate=sample_rate,
        )

        # sanity check — structural only, not scientific (that's Silver's job)
        expected_samples = int(sample_rate * duration)
        if len(ts.value) != expected_samples:
            raise ValueError(
                f"Expected {expected_samples} samples, got {len(ts.value)} — "
                f"check gps_start/duration_sec/sample_rate_hz in config"
            )

        return RawSignal(
            data=ts.value,
            domain="ligo",
            source_id=detector,
            start_time_utc=Time(gps_start, format="gps").unix,
            sample_rate_hz=sample_rate,
            duration_sec=duration,
            num_samples=len(ts.value),
            extra={"gps_start": gps_start, "gps_end": gps_start + duration},
        )