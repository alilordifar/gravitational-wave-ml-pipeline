# src/ddl/provision_domain.py

import sys
import yaml
from pathlib import Path

from src.ddl.generate_ddl import generate_ddl, run_ddl, TEMPLATE_PATH, SILVER_TEMPLATE_PATH

BUCKET = "signal-platform-dev-471112934830"  # single bucket for all domains, for now


def provision_domain(spark, config_path: str, layer: str = "bronze"):
    """
    Design-time step: create the Bronze or Silver table for a domain if it
    doesn't already exist. Idempotent — safe to re-run (DDL has
    IF NOT EXISTS). layer: "bronze" (default) or "silver".
    """
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    domain = cfg["domain"]

    template_path = SILVER_TEMPLATE_PATH if layer == "silver" else TEMPLATE_PATH
    ddl = generate_ddl(domain, BUCKET, template_path=template_path)
    print(f"--- {layer} DDL for domain='{domain}' ---")
    print(ddl)

    run_ddl(spark, ddl)
    print(f"Provisioned: signal_platform.{domain}.{layer}")


if __name__ == "__main__":
    # Usage (in a Databricks notebook cell, `spark` already exists):
    #   from src.ddl.provision_domain import provision_domain
    #   provision_domain(spark, "config/domains/ligo.yaml")                  # Bronze
    #   provision_domain(spark, "config/domains/ligo.yaml", layer="silver")  # Silver
    #
    # From CLI (outside Databricks) this won't work — no `spark` session.
    # This is meant to be called from a notebook, not run standalone.
    raise SystemExit("Run provision_domain(spark, config_path) from a Databricks notebook.")