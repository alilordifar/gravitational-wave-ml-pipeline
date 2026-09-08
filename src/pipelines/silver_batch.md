# `silver_batch.py` — explained

The Spark orchestration layer for Silver — the one file in this pipeline
that actually touches S3, Spark, and Delta for the Silver build, matching
the role [`src/pipelines/bronze_streaming.py`](bronze_streaming.md) plays
for Bronze. Everything else in `src/transformation/` for Silver
([`quality_checks.py`](../transformation/quality_checks.md),
[`processors/ligo_bandpass.py`](../transformation/processors/ligo_bandpass.md),
[`silver_builder.py`](../transformation/silver_builder.md)) is pure
Python/NumPy with no I/O — this file is where those pieces meet real data.

## Batch, not streaming — and why that's a deliberate difference from Bronze

Bronze's pipeline (`bronze_streaming.py`) watches S3 for new `.json`
sidecars arriving via Auto Loader, because raw assets land unpredictably,
one upload at a time. Silver's source is different: it reads from
`signal_platform.<domain>.bronze`, a Delta table that's already fully
written, in complete per-asset batches, by the time this runs. There's no
reason to pay for Auto Loader/streaming-state complexity here — a plain
batch read plus a `left_anti` join against what Silver already has is
enough:

```python
df_bronze = spark.table(SOURCE_TABLE)

if spark.catalog.tableExists(TARGET_TABLE):
    already_done = spark.table(TARGET_TABLE).select("asset_key").distinct()
    df_bronze = df_bronze.join(already_done, on="asset_key", how="left_anti")
```

This is the same "dedup before doing expensive work" pattern
[`scripts/ingest_to_s3.py`](../../scripts/ingest_to_s3.md) uses (`exists_remote`
before fetching) — here at the asset level instead of the S3-object
level. Re-running this job after it already processed everything is a
fast no-op; running it after five new assets landed in Bronze processes
exactly those five, nothing more. No checkpoint file needed, unlike the
streaming Bronze job.

## `process_asset` — one call per distinct asset, not per window

```python
def process_asset(pdf: pd.DataFrame) -> pd.DataFrame:
    sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")
    from src.transformation.silver_builder import build_silver_rows

    asset_key = pdf["asset_key"].iloc[0]
    client = boto3.client("s3")
    buf = io.BytesIO(client.get_object(Bucket=BUCKET, Key=asset_key)["Body"].read())
    raw_array = np.load(buf)

    bronze_rows = pdf.to_dict(orient="records")
    silver_rows = build_silver_rows(bronze_rows, raw_array, domain=DOMAIN)
    return pd.DataFrame(silver_rows, columns=[f.name for f in SILVER_ROW_SCHEMA.fields])
```

Wired up via:

```python
df_bronze.groupBy("asset_key").applyInPandas(process_asset, schema=SILVER_ROW_SCHEMA)
```

`groupBy("asset_key").applyInPandas(...)` is what makes "download each
`.npy` exactly once regardless of window count" actually happen at Spark
scale: Spark itself groups every Bronze row sharing an `asset_key` into
one pandas DataFrame (`pdf`) and hands it to `process_asset` on an
executor — one call per asset, however many windows that asset has (for
LIGO, ~2048 two-second windows per 4096-second asset). Inside, the S3
download happens once, then
[`build_silver_rows()`](../transformation/silver_builder.md) does the
actual per-window slicing/quality-checking/filtering in pure Python.

The re-`import` and `sys.path.append` inside the function body (rather
than relying on module-level imports) is the same pattern
[`bronze_streaming.py`](bronze_streaming.md)'s UDF uses: `process_asset`
runs on an executor process, potentially on a different machine than the
driver, so nothing guarantees module-level state got shipped there —
re-importing inside the function is what makes it self-contained.

`pd.DataFrame(silver_rows, columns=[f.name for f in SILVER_ROW_SCHEMA.fields])`
pins the output's column order to exactly match `SILVER_ROW_SCHEMA`,
since `applyInPandas` maps pandas columns to the declared Spark schema
positionally.

## Stamping `ingestion_ts` / `event_date`

```python
.withColumn("ingestion_ts", current_timestamp())
.withColumn("event_date", to_date(col("asset_start_time_utc").cast("timestamp")))
```

Same deferral as Bronze: [`silver_builder.py`](../transformation/silver_builder.md)
never touches these two columns, exactly like
[`build_bronze_rows()`](../transformation/bronze_builder.md) doesn't —
they're stamped on here, at write time, by the pipeline that knows *when*
it's running.

## The write

```python
(
    df_silver.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(TARGET_TABLE)
)
```

`mode("append")` matches the left-anti dedup above: this job only ever
adds rows for assets it hasn't processed yet, so append (not overwrite or
merge) is correct. `mergeSchema=true` is defensive — harmless when the
schema already matches [`silver_template.sql`](../ddl/silver_template.md)
exactly (which it should, if the table was provisioned via
`provision_domain(spark, config_path, layer="silver")` first), but avoids
a hard failure if a future column gets added to `SILVER_ROW_SCHEMA` before
the table DDL is updated to match.

## In one sentence

`silver_batch.py` reads whatever's new in a domain's Bronze table,
groups it by `asset_key` so each raw `.npy` is downloaded from S3 exactly
once, runs [`build_silver_rows()`](../transformation/silver_builder.md)
per asset to quality-check and bandpass-filter every window, and appends
the result to that domain's Silver Delta table — idempotently, via a
left-anti join, with no streaming checkpoint required.
