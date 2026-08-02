from src.connectors.base import SourceConnector
from src.connectors.ligo_gwosc import LigoGwoscConnector

_REGISTRY: dict[str, type[SourceConnector]] = {
    "ligo": LigoGwoscConnector,
}


def get_connector(domain: str) -> SourceConnector:
    try:
        connector_cls = _REGISTRY[domain]
    except KeyError:
        raise ValueError(
            f"No connector registered for domain={domain!r}. "
            f"Known domains: {sorted(_REGISTRY)}"
        )
    return connector_cls()