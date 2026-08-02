from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np


@dataclass
class RawSignal:
    """What every connector hands back, regardless of domain."""
    data: np.ndarray
    domain: str
    source_id: str          # e.g. "H1" for LIGO, would be a device_id for IoT
    start_time_utc: float   # UTC epoch seconds — canonical across all domains
    sample_rate_hz: float
    duration_sec: float
    num_samples: int
    extra: dict = field(default_factory=dict)  # domain-specific stuff (e.g. gps_start for ligo)


class SourceConnector(ABC):
    """One contract, every domain implements it the same way."""

    @abstractmethod
    def fetch(self, config: dict) -> RawSignal:
        """
        config comes from config/domains/<domain>.yaml, already loaded as a dict.
        Must return a RawSignal with start_time_utc as UTC epoch seconds —
        do any GPS/local-time conversion here, inside the connector.
        """
        raise NotImplementedError