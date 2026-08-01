RAW_PREFIX = "raw"

def compute_asset_key(domain: str, source_id: str, start: float, duration: float) -> str:
    return f"{domain}/{source_id}_{start}_{duration}"

def npy_key(asset_key: str) -> str:
    return f"{RAW_PREFIX}/{asset_key}.npy"

def json_key(asset_key: str) -> str:
    return f"{RAW_PREFIX}/{asset_key}.json"