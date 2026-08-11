# src/ddl/provision_domain.py

import sys
import yaml
from pathlib import Path

from src.ddl.generate_ddl import generate_ddl, run_ddl

BUCKET = "signal-platform-dev-471112934830"  # single bucket for all domains, for now


def provision_domain(spark, config_path: str):
    """
    Design-time step: create the Bronze table for a domain if it
    doesn't already exist. Idempotent — safe to re-run (DDL has
    IF NOT EXISTS).
    """
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    domain = cfg["domain"]

    ddl = generate_ddl(domain, BUCKET)
    print(f"--- DDL for domain='{domain}' ---")
    print(ddl)

    run_ddl(spark, ddl)
    print(f"Provisioned: signal_platform.{domain}.bronze")


if __name__ == "__main__":
    # Usage (in a Databricks notebook cell, `spark` already exists):
    #   from src.ddl.provision_domain import provision_domain
    #   provision_domain(spark, "config/domains/ligo.yaml")
    #
    # From CLI (outside Databricks) this won't work — no `spark` session.
    # This is meant to be called from a notebook, not run standalone.
    raise SystemExit("Run provision_domain(spark, config_path) from a Databricks notebook.")