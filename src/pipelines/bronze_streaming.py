"""

Reads new .json sidecars (raw window metadata) landing under
raw/domain=<domain>/ via Auto Loader (S3 event notifications),
expands each asset into its window-level Bronze rows, and writes
them to signal_platform.<domain>.bronze.

Runs as a Databricks Job (Python Script task), triggered by S3
file arrival. Uses trigger(availableNow=True) — processes what's
currently new, then stops (not a forever-running stream).
"""

import sys
sys.path.append("/Workspace/Users/ali.lordifar@gmail.com/gravitational-wave-ml-pipeline")

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, explode, col, current_timestamp, to_date
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType, MapType, ArrayType
)

from src.connectors.base import RawSignal
from src.utils.s3_paths import compute_asset_key
from src.transformation.bronze_builder import build_bronze_rows

DOMAIN = "ligo"
BUCKET = "signal-platform-dev-471112934830"
RAW_PATH = f"s3://{BUCKET}/raw/domain={DOMAIN}/"
CHECKPOINT_PATH = f"s3://{BUCKET}/_checkpoints/bronze/{DOMAIN}/"
TARGET_TABLE = f"signal_platform.{DOMAIN}.bronze"

# --- shape of the .json sidecar (RawSignal minus 'data') ---
raw_signal_schema = StructType([
    StructField("domain", StringType()),
    StructField("source_id", StringType()),
    StructField("start_time_utc", DoubleType()),
    StructField("sample_rate_hz", DoubleType()),
    StructField("duration_sec", DoubleType()),
    StructField("num_samples", LongType()),
    StructField("extra", MapType(StringType(), StringType())),
])

# --- shape build_bronze_rows() produces, one struct per window ---
window_row_schema = ArrayType(StructType([
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
]))


@udf(returnType=window_row_schema)
def make_bronze_rows(domain, source_id, start_time_utc, sample_rate_hz, duration_sec, num_samples, extra):
    raw = RawSignal(
        data=None,  # Bronze never touches the array — pointers only
        domain=domain, source_id=source_id, start_time_utc=start_time_utc,
        sample_rate_hz=sample_rate_hz, duration_sec=duration_sec,
        num_samples=num_samples, extra=extra or {},
    )
    asset_key = compute_asset_key(domain, source_id, start_time_utc, duration_sec)
    return build_bronze_rows(raw, asset_key, window_duration=2.0)


def run():
    spark = SparkSession.builder.getOrCreate()

    # --- stream: watch raw/ for new .json sidecars only ---
    df_raw = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.useManagedFileEvents", "true")   # ← UC-managed, not useNotifications
        .option("pathGlobFilter", "*.json")
        .schema(raw_signal_schema)
        .load(RAW_PATH)
    )

    df_bronze = (
        df_raw
        .withColumn("windows", make_bronze_rows(
            "domain", "source_id", "start_time_utc", "sample_rate_hz",
            "duration_sec", "num_samples", "extra"))
        .select(explode("windows").alias("w"))
        .select("w.*")
        .withColumn("ingestion_ts", current_timestamp())
        .withColumn("event_date", to_date(col("asset_start_time_utc").cast("timestamp")))
    )

    query = (
        df_bronze.writeStream
        .format("delta")
        .option("checkpointLocation", CHECKPOINT_PATH)
        .trigger(availableNow=True)   # process what's new, then stop
        .toTable(TARGET_TABLE)
    )

    query.awaitTermination()


if __name__ == "__main__":
    run()