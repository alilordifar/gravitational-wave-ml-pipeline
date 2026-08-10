# gravitational-wave-ml-pipeline

A multi-domain signal-data platform, currently exercised end-to-end for
**LIGO gravitational-wave strain data**: ingest raw signal from a source
(GWOSC), land it durably in S3, and build a queryable Delta/Spark **Bronze**
table of window-level metadata on top of it — with a schema and codebase
designed so a second domain (ECG, IoT, ...) can be onboarded without
touching most of the existing code.

This README is the map. Every source file that has real logic in it has its
own `<filename>.md` doc, colocated right next to the code it explains, going
line-by-line through what it does and *why* — written so someone with very
little Python background can follow along. Follow the links below to go
deep on any one piece.

## Architecture at a glance

This is a [medallion architecture](https://www.databricks.com/glossary/medallion-architecture)
pipeline (Bronze → Silver → Gold), built around one idea: **every domain
shares the same code and the same table schema.** The only thing that
varies between LIGO and any future domain is what's inside a single
`domain_metadata` map — nothing else has to change.

```
                     ┌────────────────────────────────────────────┐
                     │   config/domains/<domain>.yaml               │
                     │   (detector, gps_start, duration, sample     │
                     │    rate, window size, table names...)        │
                     └───────────────────┬────────────────────────┘
                                          │
                                          ▼
   ┌───────────────────┐        ┌─────────────────────┐        ┌────────────────────┐
   │  SourceConnector    │──────▶│  scripts/ingest_to   │──────▶│   S3Uploader         │
   │  (per-domain fetch) │       │  _s3.py (orchestrator│       │   (.npy + .json,     │
   │  e.g. LigoGwosc     │       │  + dedup check)      │       │   .json = "commit")  │
   │  Connector           │       └─────────────────────┘        └──────────┬──────────┘
   └───────────────────┘                                                    │
                                                                             ▼
                                                                 s3://<bucket>/raw/domain=.../
                                                                   source_id=.../year=.../...
                                                                             │
                                              ┌──────────────────────────────┘
                                              ▼
                                 ┌─────────────────────────┐
                                 │  s3_reader.py             │  (metadata-only reload)
                                 └────────────┬─────────────┘
                                              ▼
                                 ┌─────────────────────────┐        ┌──────────────────────┐
                                 │  windower.py               │──────▶│  bronze_builder.py     │
                                 │  (pure NumPy window math)  │       │  (merge window +       │
                                 └─────────────────────────┘       │  asset-level fields)   │
                                                                    └───────────┬───────────┘
                                                                                ▼
                                                          spark.createDataFrame(rows) + write
                                                                                ▼
                                              signal_platform.<domain>.bronze  (Delta table,
                                              schema from src/ddl/bronze_template.sql)
                                                                                ▼
                                          ── not yet implemented ──
                                          Silver (cleaned/validated, e.g. quality_checks.py,
                                          processors/ligo_bandpass.py)
                                          Gold (ML-ready features, e.g. feature_engineering/)
```

**Bronze never stores signal arrays.** Every Bronze row points back at a
`.npy` file in S3 (`asset_key` column) rather than duplicating the array
into Delta — see [`src/ddl/bronze_template.sql`](src/ddl/bronze_template.md)
and [`src/transformation/bronze_builder.py`](src/transformation/bronze_builder.md).

## What's implemented vs. what's a stub

| Layer | Status | Files |
|---|---|---|
| **Config** | done | [`config/domains/ligo.yaml`](config/domains/ligo.yaml), [`config/platform.yaml`](config/platform.yaml) — `ecg.yaml`/`iot.yaml` exist but are empty placeholders for future domains |
| **Infra setup** | done | [`scripts/setup_s3.py`](scripts/setup_s3.md) → [`src/utils/aws_setup.py`](src/utils/aws_setup.md) |
| **Connectors** | done (LIGO only) | [`src/connectors/`](src/connectors/base.md) |
| **Ingestion / S3 persistence** | done | [`src/ingestion/uploader.py`](src/ingestion/uploader.md), [`src/utils/s3_paths.py`](src/utils/s3_paths.md), [`scripts/ingest_to_s3.py`](scripts/ingest_to_s3.md) |
| **Bronze (DDL + row-building)** | done | [`src/ddl/`](src/ddl/generate_ddl.md), [`src/transformation/windower.py`](src/transformation/windower.md), [`src/transformation/bronze_builder.py`](src/transformation/bronze_builder.md), [`src/transformation/s3_reader.py`](src/transformation/s3_reader.md) |
| **Silver (quality/cleaning)** | **stub, empty** | [`src/transformation/quality_checks.py`](src/transformation/quality_checks.md), [`src/transformation/processors/ligo_bandpass.py`](src/transformation/processors/ligo_bandpass.md) |
| **Gold (feature engineering)** | **stub, empty** | [`src/feature_engineering/ligo_features.py`](src/feature_engineering/ligo_features.md), [`src/feature_engineering/registry.py`](src/feature_engineering/registry.md) |
| **Notebooks** | present, not documented here | `notebooks/00_run_pipeline.ipynb` → `04_train.ipynb` walk the stages interactively |

The "stub" docs above explain what each empty file is *likely* for, inferred
from its name, location, and references elsewhere in the code — they are
explicitly marked as inference, not a description of real behavior.

## Per-file documentation index

### `src/connectors/` — pluggable per-domain data fetchers

- [`base.py`](src/connectors/base.md) — the `RawSignal` data contract and
  `SourceConnector` abstract base class every domain implements.
- [`ligo_gwosc.py`](src/connectors/ligo_gwosc.md) — the LIGO implementation:
  fetches strain data from GWOSC via `gwpy`, converts GPS time to UTC via
  `astropy`.
- [`registry.py`](src/connectors/registry.md) — `domain string → connector
  class` lookup table, so no code branches on domain name.

### `src/ddl/` — Bronze table schema, generated generically for every domain

- [`bronze_template.sql`](src/ddl/bronze_template.md) — the one SQL template
  every domain's Bronze table is built from; domain-specific fields live in
  a single `MAP<STRING, STRING>` column instead of typed columns.
- [`generate_ddl.py`](src/ddl/generate_ddl.md) — renders the template for a
  given domain/bucket (pure string substitution, not `str.format()`), plus a
  deliberately separate function to actually execute it.
- [`provision_domain.py`](src/ddl/provision_domain.md) — the notebook-facing
  entry point that reads a domain's YAML and calls `CREATE TABLE IF NOT
  EXISTS` for it. Meant to be called from a Databricks notebook, not the CLI.

### `src/utils/` — shared, domain-agnostic infrastructure code

- [`s3_paths.py`](src/utils/s3_paths.md) — `AssetKey`: the single source of
  truth for how an asset's identity turns into a Hive-style S3 path
  (`raw/domain=.../source_id=.../year=.../month=.../day=.../`).
- [`aws_setup.py`](src/utils/aws_setup.md) — idempotent, security-hardened
  S3 bucket creation (blocked public access, enforced ownership, default
  encryption, versioning, HTTPS-only policy).

### `src/ingestion/` and `src/transformation/` — the write and Bronze-build path

- [`uploader.py`](src/ingestion/uploader.md) — `S3Uploader`: writes a
  `RawSignal` as `.npy` (array) + `.json` (metadata), uploaded in that
  specific order so the `.json`'s existence proves the upload is complete.
- [`s3_reader.py`](src/transformation/s3_reader.md) — the read-side mirror:
  reconstructs a metadata-only `RawSignal` + `AssetKey` from a `.json` file,
  without ever downloading the array.
- [`windower.py`](src/transformation/windower.md) — pure NumPy math that
  slices one asset into fixed-length, non-overlapping windows and computes
  each window's real-world start time.
- [`bronze_builder.py`](src/transformation/bronze_builder.md) — merges
  window-level fields with asset-level identity into full Bronze rows,
  ready for `spark.createDataFrame(...)`.
- [`quality_checks.py`](src/transformation/quality_checks.md) *(stub)* and
  [`processors/ligo_bandpass.py`](src/transformation/processors/ligo_bandpass.md)
  *(stub)* — where Silver-layer scientific validation and signal cleaning
  presumably belong.

### `src/feature_engineering/` — Gold layer (not yet implemented)

- [`ligo_features.py`](src/feature_engineering/ligo_features.md) *(stub)*
  and [`registry.py`](src/feature_engineering/registry.md) *(stub)* — where
  LIGO-specific ML feature extraction, and a registry mirroring
  `src/connectors/registry.py`, presumably belong.

### `scripts/` — CLI entry points

- [`setup_s3.py`](scripts/setup_s3.md) — run once (or any time) to
  create/harden the raw-data S3 bucket.
- [`ingest_to_s3.py`](scripts/ingest_to_s3.md) — the main ingestion CLI:
  `config → connector → dedup check → fetch (if needed) → upload`.

## Running the pipeline

All commands assume the repository root as the working directory (several
scripts read config with relative paths — see the individual docs above for
specifics).

```bash
pip install -r requirements.txt

# One-time: create and harden the raw-data S3 bucket
python scripts/setup_s3.py

# Ingest LIGO data for the window described in config/domains/ligo.yaml
python scripts/ingest_to_s3.py --domain ligo
```

Re-running `ingest_to_s3.py` for a config you've already ingested is a fast
no-op — it checks S3 first and skips the (expensive) GWOSC fetch if the
asset's already there. See
[`scripts/ingest_to_s3.py`](scripts/ingest_to_s3.md) for the full
dedup-then-fetch-then-upload flow.

Provisioning a domain's Bronze table currently has to happen from a
Databricks notebook (it needs a live `spark` session):

```python
from src.ddl.provision_domain import provision_domain
provision_domain(spark, "config/domains/ligo.yaml")
```

See [`src/ddl/provision_domain.py`](src/ddl/provision_domain.md) for why
this deliberately can't be run from the CLI.

## Configuration

- [`config/platform.yaml`](config/platform.yaml) — shared across every
  domain: S3 bucket name and AWS region.
- [`config/domains/ligo.yaml`](config/domains/ligo.yaml) — everything
  specific to one ingestion run: detector, GPS start time, duration, sample
  rate, window size, and the Delta catalog/schema/table names for that
  domain's Bronze/Silver/Gold tables.
- `config/domains/ecg.yaml`, `config/domains/iot.yaml` — present but empty;
  placeholders for onboarding those domains later.

## Adding a new domain

Because the schema and orchestration code are domain-generic by design,
onboarding a new domain (say, `ecg`) is meant to require only:

1. Fill in `config/domains/ecg.yaml` (see `ligo.yaml` as a template).
2. Implement an `EcgConnector(SourceConnector)` in `src/connectors/`,
   returning a `RawSignal` per the contract in
   [`src/connectors/base.py`](src/connectors/base.md) — with any
   ECG-specific fields (lead, patient ID, ...) packed into `RawSignal.extra`.
3. Register it: add `"ecg": EcgConnector` to `_REGISTRY` in
   [`src/connectors/registry.py`](src/connectors/registry.md).
4. Provision its Bronze table via
   [`provision_domain(spark, "config/domains/ecg.yaml")`](src/ddl/provision_domain.md)
   — no new DDL to write; it reuses
   [`bronze_template.sql`](src/ddl/bronze_template.md) as-is.
5. Run `python scripts/ingest_to_s3.py --domain ecg`.

No changes to `s3_paths.py`, `windower.py`, `bronze_builder.py`,
`uploader.py`, `s3_reader.py`, or the Bronze DDL template should be
necessary — that's the whole point of routing domain-specific data through
`RawSignal.extra` → `domain_metadata`.

## Repository layout

```
.
├── config/
│   ├── platform.yaml            # shared bucket/region
│   └── domains/                 # one YAML per domain (ligo.yaml is complete; ecg/iot are stubs)
├── scripts/                     # CLI entry points (see docs above)
├── src/
│   ├── connectors/               # per-domain fetch logic + registry
│   ├── ddl/                      # Bronze schema template + generation/provisioning
│   ├── ingestion/                 # S3 write path
│   ├── transformation/            # window computation, Bronze row building, S3 read path,
│   │                               # and stubs for Silver-layer quality checks / processors
│   ├── feature_engineering/       # Gold-layer stubs
│   └── utils/                     # S3 path construction, bucket hardening
├── notebooks/                    # interactive walkthroughs of each pipeline stage
├── data/local_cache/              # local scratch space (not part of the S3-only persistence design)
└── tests/                        # currently empty
```
