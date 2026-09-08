# `bronze_streaming.py` — explained

The Spark orchestration layer for Bronze: the file that actually touches
S3, Spark Structured Streaming, and Delta, sitting above the pure
Python/NumPy pieces in `src/transformation/`
([`windower.py`](../transformation/windower.md),
[`bronze_builder.py`](../transformation/bronze_builder.md)). Runs as a
Databricks Job (Python Script task), triggered by new files landing in
S3.

```python
DOMAIN = "ligo"
BUCKET = "signal-platform-dev-471112934830"
RAW_PATH = f"s3://{BUCKET}/raw/domain={DOMAIN}/"
CHECKPOINT_PATH = f"s3://{BUCKET}/_checkpoints/bronze/{DOMAIN}/"
TARGET_TABLE = f"signal_platform.{DOMAIN}.bronze"
```

`DOMAIN` is hardcoded, the same simplification
[`provision_domain.py`](../ddl/provision_domain.md) makes for `BUCKET` —
one domain running today, not yet parameterized.

## Auto Loader watches for new `.json` sidecars only

```python
df_raw = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.useManagedFileEvents", "true")
    .option("pathGlobFilter", "*.json")
    .schema(raw_signal_schema)
    .load(RAW_PATH)
)
```

`pathGlobFilter="*.json"` matters: [`S3Uploader`](../ingestion/uploader.md)
writes `.npy` first, `.json` last, treating the `.json`'s existence as the
"commit" signal. Filtering to just `.json` files means Auto Loader only
ever reacts to a fully-uploaded asset, never a half-written one. Data
itself is never read here — `raw_signal_schema` matches the `.json`
sidecar's shape (`RawSignal` minus `data`), exactly what
[`s3_reader.py`](../transformation/s3_reader.md) reconstructs on the
batch-backfill path.

## `make_bronze_rows` — a UDF wrapping the pure functions

```python
@udf(returnType=window_row_schema)
def make_bronze_rows(domain, source_id, start_time_utc, sample_rate_hz, duration_sec, num_samples, extra):
    import sys
    sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")
    from src.connectors.base import RawSignal
    from src.utils.s3_paths import compute_asset_key
    from src.transformation.bronze_builder import build_bronze_rows

    raw = RawSignal(data=None, domain=domain, source_id=source_id, ...)
    asset_key = compute_asset_key(domain, source_id, start_time_utc, duration_sec)
    return build_bronze_rows(raw, asset_key, window_duration=2.0)
```

Runs once per new asset (one row of `df_raw`), reconstructs a
metadata-only `RawSignal` (`data=None` — Bronze never needs the array
itself), and delegates the real work entirely to
[`build_bronze_rows()`](../transformation/bronze_builder.md), which
returns one row per window. The imports inside the function body (not at
module scope) exist because a UDF runs on executors — separate processes
that don't automatically inherit the driver's imports — so everything the
function needs gets pulled in fresh, every call.
[`src/pipelines/silver_batch.py`](silver_batch.md) follows the identical
pattern for the same reason.

## Explode, stamp, write

```python
df_bronze = (
    df_raw
    .withColumn("windows", make_bronze_rows(...))
    .select(explode("windows").alias("w"))
    .select("w.*")
    .withColumn("ingestion_ts", current_timestamp())
    .withColumn("event_date", to_date(col("asset_start_time_utc").cast("timestamp")))
)
```

`make_bronze_rows` returns an *array* of window-structs per asset row;
`explode` turns that one array into one row per window, `select("w.*")`
flattens the struct into top-level columns, and the two `withColumn`
calls add the runtime-computed fields
[`bronze_template.sql`](../ddl/bronze_template.md) expects but
`build_bronze_rows()` deliberately doesn't produce (see that file's doc
for why).

## `trigger(availableNow=True)` — a stream that stops

```python
query = (
    df_bronze.writeStream
    .format("delta")
    .option("checkpointLocation", CHECKPOINT_PATH)
    .trigger(availableNow=True)
    .toTable(TARGET_TABLE)
)
query.awaitTermination()
```

Despite using `readStream`/`writeStream`, this isn't a forever-running
job: `availableNow=True` tells Spark to process everything currently
available, then stop — appropriate for a scheduled Databricks Job rather
than an always-on cluster. `CHECKPOINT_PATH` is what makes re-runs
incremental: Spark tracks which `.json` files it's already consumed there,
so the next scheduled run only picks up files that landed since the last
one.

## In one sentence

`bronze_streaming.py` uses Auto Loader to react to newly-committed raw
assets in S3, wraps the pure
[`windower.py`](../transformation/windower.md)/[`bronze_builder.py`](../transformation/bronze_builder.md)
logic in a UDF to expand each asset into its window-level rows, and writes
the result to a domain's Bronze Delta table via a checkpointed,
run-then-stop streaming query.
