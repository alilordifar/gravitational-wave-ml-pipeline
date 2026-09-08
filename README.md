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
                                                                                │
                                              ┌─────────────────────────────────┘
                                              ▼
                                 ┌─────────────────────────┐
                                 │  silver_batch.py           │  (per-asset S3 download,
                                 │  groupBy(asset_key)        │   once per asset either way)
                                 │  .applyInPandas(...)       │
                                 └────────────┬─────────────┘
                                              ▼
                                 ┌─────────────────────────┐        ┌──────────────────────┐
                                 │  quality_checks.py         │──────▶│  silver_builder.py     │
                                 │  (NaN/Inf/flatline flags)  │       │  (merge quality flags  │
                                 └─────────────────────────┘       │  + filtered samples)   │
                                 ┌─────────────────────────┐        └───────────┬───────────┘
                                 │  processors/ligo_bandpass  │────────────────▲
                                 │  (per-domain, via registry)│
                                 └─────────────────────────┘
                                                                                ▼
                                              signal_platform.<domain>.silver  (Delta table,
                                              schema from src/ddl/silver_template.sql)
                                                                                ▼
                                          ── not yet implemented ──
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
| **Bronze (DDL + row-building)** | done | [`src/ddl/`](src/ddl/generate_ddl.md), [`src/transformation/windower.py`](src/transformation/windower.md), [`src/transformation/bronze_builder.py`](src/transformation/bronze_builder.md), [`src/transformation/s3_reader.py`](src/transformation/s3_reader.md), [`src/pipelines/bronze_streaming.py`](src/pipelines/bronze_streaming.md) |
| **Silver (quality/cleaning)** | done (LIGO only) | [`src/transformation/quality_checks.py`](src/transformation/quality_checks.md), [`src/transformation/processors/ligo_bandpass.py`](src/transformation/processors/ligo_bandpass.md), [`src/transformation/processors/registry.py`](src/transformation/processors/registry.md), [`src/transformation/silver_builder.py`](src/transformation/silver_builder.md), [`src/ddl/silver_template.sql`](src/ddl/silver_template.md), [`src/pipelines/silver_batch.py`](src/pipelines/silver_batch.md) |
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
  EXISTS` for it, for either layer (`layer="bronze"` or `"silver"`). Meant
  to be called from a Databricks notebook, not the CLI.
- [`silver_template.sql`](src/ddl/silver_template.md) — the Silver
  counterpart to `bronze_template.sql`: every Bronze column, plus five
  quality-flag columns and one `ARRAY<DOUBLE>` column holding each
  window's filtered samples.

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
- [`quality_checks.py`](src/transformation/quality_checks.md) — pure,
  domain-agnostic structural checks on one window's raw samples (NaN, Inf,
  flatline, all-zero), returning the flags Silver uses to decide whether a
  window is worth filtering.
- [`processors/ligo_bandpass.py`](src/transformation/processors/ligo_bandpass.md) —
  LIGO's Silver-layer signal cleaning: a zero-phase Butterworth bandpass
  filter (20 Hz-2000 Hz by default).
- [`processors/registry.py`](src/transformation/processors/registry.md) —
  `domain string → processor function` lookup, mirroring
  `src/connectors/registry.py`.
- [`silver_builder.py`](src/transformation/silver_builder.md) — the
  Silver-layer counterpart to `bronze_builder.py`: given one asset's
  Bronze rows plus its raw array, slices out each window, quality-checks
  it, and bandpass-filters it if it passes.

### `src/pipelines/` — the Spark orchestration layer (S3 + Delta I/O)

- [`bronze_streaming.py`](src/pipelines/bronze_streaming.md) — Auto
  Loader-driven: reacts to new `.json` sidecars landing in S3, expands
  each into its window-level Bronze rows, writes to
  `signal_platform.<domain>.bronze`.
- [`silver_batch.py`](src/pipelines/silver_batch.md) — reads whatever's
  new in a domain's Bronze table, groups by `asset_key` so each raw
  `.npy` is downloaded from S3 exactly once, runs `silver_builder.py` per
  asset, and appends to `signal_platform.<domain>.silver`. A plain
  idempotent batch job (left-anti join on `asset_key`), not a stream —
  see that file's doc for why.

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

Provisioning a domain's Bronze or Silver table currently has to happen
from a Databricks notebook (it needs a live `spark` session):

```python
from src.ddl.provision_domain import provision_domain
provision_domain(spark, "config/domains/ligo.yaml")                  # Bronze
provision_domain(spark, "config/domains/ligo.yaml", layer="silver")  # Silver
```

See [`src/ddl/provision_domain.py`](src/ddl/provision_domain.md) for why
this deliberately can't be run from the CLI.

Once Bronze has data in it, build Silver by running (also from a
Databricks notebook, or as a scheduled Databricks Job):

```python
from src.pipelines.silver_batch import run
run()
```

This processes every Bronze asset not already in Silver, quality-checks
and bandpass-filters each window, and appends the result to
`signal_platform.ligo.silver`. Safe to re-run — already-processed assets
are skipped. See [`src/pipelines/silver_batch.py`](src/pipelines/silver_batch.md)
for the full flow, and the "Testing the Silver layer" section below for
running it locally first.

### Testing the Silver layer

The pure Python/NumPy pieces (`quality_checks.py`, `processors/ligo_bandpass.py`,
`silver_builder.py`) need no Spark/AWS and are covered by `tests/`:

```bash
pip install -r requirements.txt   # now includes scipy, pandas, pytest
python -m pytest tests/ -v
```

To exercise the full Spark path locally before pushing to Databricks, use
`notebooks/silver_local.ipynb` (already scaffolded for a local
`SparkSession` reading Bronze parquet via `s3a://`) and call
`src.pipelines.silver_batch.run()` from a cell once `spark` is defined —
see that notebook and [`src/pipelines/silver_batch.py`](src/pipelines/silver_batch.md)
for details.

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
4. Provision its Bronze and Silver tables via
   [`provision_domain(spark, "config/domains/ecg.yaml")`](src/ddl/provision_domain.md)
   and `provision_domain(spark, "config/domains/ecg.yaml", layer="silver")`
   — no new DDL to write; both reuse
   [`bronze_template.sql`](src/ddl/bronze_template.md) /
   [`silver_template.sql`](src/ddl/silver_template.md) as-is.
5. Run `python scripts/ingest_to_s3.py --domain ecg`.
6. Implement an ECG-specific Silver processor (a function
   `(samples, sample_rate_hz) -> filtered_samples`) and register it as
   `"ecg"` in
   [`src/transformation/processors/registry.py`](src/transformation/processors/registry.md)
   — this is the one Silver-layer step that's genuinely domain-specific,
   the same way the connector is on the ingestion side.
7. Run `src.pipelines.silver_batch.run()` (with `DOMAIN = "ecg"`) to build
   Silver.

No changes to `s3_paths.py`, `windower.py`, `bronze_builder.py`,
`uploader.py`, `s3_reader.py`, `quality_checks.py`, `silver_builder.py`,
or either DDL template should be necessary — that's the whole point of
routing domain-specific data through `RawSignal.extra` → `domain_metadata`,
and domain-specific *processing* through `processors/registry.py`.

## Repository layout

```
.
├── config/
│   ├── platform.yaml            # shared bucket/region
│   └── domains/                 # one YAML per domain (ligo.yaml is complete; ecg/iot are stubs)
├── scripts/                     # CLI entry points (see docs above)
├── src/
│   ├── connectors/               # per-domain fetch logic + registry
│   ├── ddl/                      # Bronze + Silver schema templates + generation/provisioning
│   ├── ingestion/                 # S3 write path
│   ├── transformation/            # window computation, Bronze row building, S3 read path,
│   │                               # Silver quality checks + silver_builder.py, and
│   │                               # processors/ (per-domain Silver filtering + registry)
│   ├── pipelines/                 # Spark orchestration: bronze_streaming.py, silver_batch.py
│   ├── feature_engineering/       # Gold-layer stubs
│   └── utils/                     # S3 path construction, bucket hardening
├── notebooks/                    # interactive walkthroughs of each pipeline stage
├── data/local_cache/              # local scratch space (not part of the S3-only persistence design)
└── tests/                        # unit tests for the pure Silver-layer functions
```
