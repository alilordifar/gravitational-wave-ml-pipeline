"""
Thin orchestrator: config -> connector -> dedup check -> fetch (if needed) -> upload.

No business logic lives here beyond wiring. Domain-specific work stays in
connectors; persistence logic stays in S3Uploader; naming stays in s3_paths.
"""

import argparse

import yaml
import boto3

from src.connectors.registry import get_connector
from src.ingestion.uploader import S3Uploader
from src.utils.s3_paths import compute_asset_key


def load_domain_config(domain: str) -> dict:
    with open(f"config/domains/{domain}.yaml") as f:
        return yaml.safe_load(f)


def load_platform_config() -> dict:
    with open("config/platform.yaml") as f:
        return yaml.safe_load(f)


def ingest(domain: str, config: dict, uploader: S3Uploader) -> None:
    connector = get_connector(domain)

    # cheap — no network call, just enables the dedup check below
    start_time_utc = connector.compute_start_time_utc(config)

    asset_key = compute_asset_key(
        domain=domain,
        source_id=connector.get_source_id(config),
        start=start_time_utc,
        duration=config["duration_sec"],
    )

    if uploader.exists_remote(asset_key):
        print(f"[skip] {asset_key} already in S3")
        return

    print(f"[fetch] {asset_key} — not in S3, fetching from source")
    raw = connector.fetch(config)  # expensive — actual network call to GWOSC

    print(f"[upload] {asset_key}")
    uploader.upload(asset_key, raw)
    print(f"[done] {asset_key}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="e.g. ligo")
    args = parser.parse_args()

    platform_config = load_platform_config()
    domain_config = load_domain_config(args.domain)

    uploader = S3Uploader(
        bucket=platform_config["raw_bucket"],
        client=boto3.client("s3", region_name=platform_config["region"]),
    )

    ingest(args.domain, domain_config, uploader)


if __name__ == "__main__":
    main()