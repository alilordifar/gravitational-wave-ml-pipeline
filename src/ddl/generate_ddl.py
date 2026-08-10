"""
src/ddl/generate_ddl.py

Generates (and optionally runs) Bronze DDL for a given domain, from the
single shared template. This is the "orchestrator can take care of
everything" piece: given just a domain name and a bucket, it produces a
ready-to-run CREATE TABLE statement — no per-domain SQL file needed.

Usage (design-time, deliberate step — not auto-triggered on yaml save):

    from src.ddl.generate_ddl import generate_ddl, run_ddl

    ddl = generate_ddl(domain="ecg", bucket="signal-platform-dev-471112934830")
    run_ddl(spark, ddl)   # only when you actually want to create/confirm the table
"""

from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent / "bronze_template.sql"


def generate_ddl(domain: str, bucket: str, template_path: Path = TEMPLATE_PATH) -> str:
    """
    Pure string substitution — deliberately NOT str.format(), since the
    template's example JSON comments (e.g. {"detector": "H1"}) contain
    literal braces that collide with format() placeholder syntax.
    """
    template = template_path.read_text()
    return template.replace("{domain}", domain).replace("{bucket}", bucket)


def run_ddl(spark, ddl: str) -> None:
    """
    Executes the generated DDL. Kept as an explicit, separate call from
    generate_ddl() on purpose — generating and reviewing the SQL is safe
    and side-effect-free; actually running it against a production catalog
    is a deliberate action that shouldn't happen implicitly.
    """
    spark.sql(ddl)