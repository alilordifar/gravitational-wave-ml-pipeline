"""
Reads signal_platform.<domain>.bronze, skips any asset_key already present
in signal_platform.<domain>.silver, groups the rest by asset_key so each
raw .npy is downloaded from S3 exactly once regardless of how many windows
it contains, then quality-checks and bandpass-filters every window and
appends the result to signal_platform.<domain>.silver.

Runs as a Databricks Job (Python Script task) or directly from a notebook
cell. A plain batch job, not a stream: Bronze is written asset-by-asset in
full batches (see src/pipelines/bronze_streaming.py), so a left-anti join
on asset_key is enough to make re-runs cheap and idempotent — no
checkpoint needed.
"""

import sys
sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")

import io

import boto3
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


def process_asset(pdf: pd.DataFrame) -> pd.DataFrame:
    """
    Runs once per distinct asset_key (via groupBy(...).applyInPandas below)
    on an executor — a separate process from the driver — so everything it
    needs is imported inside the function body rather than relied upon from
    module scope, same pattern as bronze_streaming.py's UDF.
    """
    sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")
    from src.transformation.silver_builder import build_silver_rows

    asset_key = pdf["asset_key"].iloc[0]
    client = boto3.client("s3")
    buf = io.BytesIO(client.get_object(Bucket=BUCKET, Key=asset_key)["Body"].read())
    raw_array = np.load(buf)

    bronze_rows = pdf.to_dict(orient="records")
    silver_rows = build_silver_rows(bronze_rows, raw_array, domain=DOMAIN)
    return pd.DataFrame(silver_rows, columns=[f.name for f in SILVER_ROW_SCHEMA.fields])


def run():
    spark = SparkSession.builder.getOrCreate()

    df_bronze = spark.table(SOURCE_TABLE)

    if spark.catalog.tableExists(TARGET_TABLE):
        already_done = spark.table(TARGET_TABLE).select("asset_key").distinct()
        df_bronze = df_bronze.join(already_done, on="asset_key", how="left_anti")

    if df_bronze.isEmpty():
        print(f"[skip] no new Bronze rows to process for domain={DOMAIN}")
        return

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
