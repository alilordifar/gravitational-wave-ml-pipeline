"""
Reads signal_platform.<domain>.bronze, skips any asset_key already present
in signal_platform.<domain>.silver, downloads each remaining raw .npy
exactly once (via Spark's own S3 access — see "Why Spark, not boto3"
below), then quality-checks and bandpass-filters every window and appends
the result to signal_platform.<domain>.silver.

Runs as a Databricks Job (Python Script task) or directly from a notebook
cell. A plain batch job, not a stream: Bronze is written asset-by-asset in
full batches (see src/pipelines/bronze_streaming.py), so a left-anti join
on asset_key is enough to make re-runs cheap and idempotent — no
checkpoint needed.

Why Spark, not boto3: a plain `boto3.client("s3")` call inside a UDF has
no AWS credentials on Serverless/Unity-Catalog-governed compute — those
environments deliberately don't expose raw AWS keys to arbitrary code.
Spark's own readers (spark.read, readStream) already have access to this
bucket through Databricks' governed storage credential (that's how Bronze
reads/writes it), so raw bytes are pulled via
`spark.read.format("binaryFile")` on the driver instead, then handed to
executors as a broadcast variable — no boto3, no credential problem.
"""

import sys
sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")

import io

import numpy as np
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import current_timestamp, to_date, col
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType,
    BooleanType, MapType, ArrayType
)

DOMAIN = "ligo"
BUCKET = "signal-platform-dev-471112934830"
SOURCE_TABLE = f"signal_platform.{DOMAIN}.bronze"
TARGET_TABLE = f"signal_platform.{DOMAIN}.silver"

# --- shape build_silver_rows() produces, one struct per window ---
SILVER_ROW_SCHEMA = StructType([
    StructField("window_id", LongType()),
    StructField("source_id", StringType()),
    StructField("asset_key", StringType()),
    StructField("asset_start_time_utc", DoubleType()),
    StructField("start_idx", LongType()),
    StructField("end_idx", LongType()),
    StructField("window_duration", DoubleType()),
    StructField("window_num_samples", LongType()),
    StructField("window_start_time_utc", DoubleType()),
    StructField("sample_rate_hz", DoubleType()),
    StructField("domain_metadata", MapType(StringType(), StringType())),
    StructField("has_nan", BooleanType()),
    StructField("has_inf", BooleanType()),
    StructField("is_flatline", BooleanType()),
    StructField("all_zero", BooleanType()),
    StructField("is_valid", BooleanType()),
    StructField("filtered_samples", ArrayType(DoubleType())),
])


def load_raw_arrays(spark, asset_keys: list[str]) -> dict:
    """
    Downloads each distinct asset's raw array exactly once, on the driver,
    via Spark's binaryFile reader (governed S3 access, not boto3). Returns
    {asset_key: np.ndarray}, meant to be wrapped in a broadcast variable
    before being used inside a pandas UDF running on executors.
    """
    raw_arrays = {}
    for asset_key in asset_keys:
        content = (
            spark.read.format("binaryFile")
            .load(f"s3://{BUCKET}/{asset_key}")
            .select("content")
            .first()["content"]
        )
        raw_arrays[asset_key] = np.load(io.BytesIO(content))
    return raw_arrays


def run():
    spark = SparkSession.builder.getOrCreate()

    df_bronze = spark.table(SOURCE_TABLE)

    if spark.catalog.tableExists(TARGET_TABLE):
        already_done = spark.table(TARGET_TABLE).select("asset_key").distinct()
        df_bronze = df_bronze.join(already_done, on="asset_key", how="left_anti")

    if df_bronze.isEmpty():
        print(f"[skip] no new Bronze rows to process for domain={DOMAIN}")
        return

    asset_keys = [r.asset_key for r in df_bronze.select("asset_key").distinct().collect()]
    raw_arrays_bc = spark.sparkContext.broadcast(load_raw_arrays(spark, asset_keys))

    def process_asset(pdf: pd.DataFrame) -> pd.DataFrame:
        """
        Runs once per distinct asset_key (via groupBy(...).applyInPandas
        below) on an executor. Defined here, inside run(), so it closes
        over raw_arrays_bc — the broadcast variable is what actually ships
        each asset's array to executors, not a per-call network fetch.
        """
        sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")
        from src.transformation.silver_builder import build_silver_rows

        asset_key = pdf["asset_key"].iloc[0]
        raw_array = raw_arrays_bc.value[asset_key]

        bronze_rows = pdf.to_dict(orient="records")
        silver_rows = build_silver_rows(bronze_rows, raw_array, domain=DOMAIN)
        return pd.DataFrame(silver_rows, columns=[f.name for f in SILVER_ROW_SCHEMA.fields])

    df_silver = (
        df_bronze
        .groupBy("asset_key")
        .applyInPandas(process_asset, schema=SILVER_ROW_SCHEMA)
        .withColumn("ingestion_ts", current_timestamp())
        .withColumn("event_date", to_date(col("asset_start_time_utc").cast("timestamp")))
    )

    (
        df_silver.write
        .format("delta")
        .mode("append")
        .option("mergeSchema", "true")
        .saveAsTable(TARGET_TABLE)
    )
    print(f"[done] wrote {TARGET_TABLE}")


if __name__ == "__main__":
    run()
