# `registry.py` (processors) — explained

```python
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
```

Deliberately identical in shape to
[`src/connectors/registry.py`](../../connectors/registry.md): a plain
dict from domain string to callable, plus a `get_*` accessor that fails
loudly (naming every known domain) rather than a `KeyError` a caller has
to trace back. The one difference is what's stored — connectors map to a
*class* (`get_connector` instantiates it), this maps straight to a
*function*, since [`ligo_bandpass.py`](ligo_bandpass.md) has no state to
hold between calls.

This is what onboarding a new domain's Silver processing looks like in
practice: implement a function matching
`(samples: np.ndarray, sample_rate_hz: float) -> np.ndarray`, add one line
to `_REGISTRY`, and [`silver_builder.py`](../silver_builder.md) picks it
up with zero other code changes — the same "add a domain, touch one file"
property the rest of this codebase is designed around.

## In one sentence

`get_processor(domain)` is a one-line lookup from domain string to that
domain's Silver-layer filtering function, keeping
[`silver_builder.py`](../silver_builder.md) from ever needing to know
LIGO-specific code exists.
