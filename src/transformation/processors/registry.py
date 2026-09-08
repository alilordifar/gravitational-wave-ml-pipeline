"""
Domain -> Silver processor lookup, mirroring src/connectors/registry.py.

Every registered processor takes (samples, sample_rate_hz) and returns a
filtered array of the same shape — the one contract every domain's
processor implements, analogous to SourceConnector.fetch() for ingestion.
This is what lets silver_builder.py stay domain-generic: it never branches
on domain name, it just looks the processor up here.
"""

from src.transformation.processors.ligo_bandpass import apply_bandpass

_REGISTRY = {
    "ligo": apply_bandpass,
}


def get_processor(domain: str):
    try:
        return _REGISTRY[domain]
    except KeyError:
        raise ValueError(
            f"No Silver processor registered for domain={domain!r}. "
            f"Known domains: {sorted(_REGISTRY)}"
        )
