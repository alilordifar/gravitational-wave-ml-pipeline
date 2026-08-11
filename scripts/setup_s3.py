"""Run once (or any time) to create/harden the raw data S3 bucket."""

import yaml

from src.utils.aws_setup import ensure_raw_bucket


def main():
    with open("config/platform.yaml") as f:
        platform_config = yaml.safe_load(f)

    ensure_raw_bucket(
        bucket=platform_config["raw_bucket"],
        region=platform_config["region"],
    )


if __name__ == "__main__":
    main()