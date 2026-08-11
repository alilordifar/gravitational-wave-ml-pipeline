-- src/ddl/bronze_template.sql
--
-- ONE template for every domain's Bronze table. Schema is identical across
-- domains — the only variation (detector/gps_* vs lead/patient_id vs
-- anything else) lives inside domain_metadata, not as separate typed
-- columns. This means onboarding a new domain never requires touching
-- this file or writing new DDL by hand.
--
-- Placeholders (substituted by generate_ddl.py): {domain}, {bucket}

CREATE TABLE IF NOT EXISTS signal_platform.{domain}.bronze (
  -- universal, identical for every domain, from build_bronze_rows
  window_id             BIGINT      NOT NULL,
  source_id             STRING      NOT NULL,
  asset_key             STRING      NOT NULL,
  asset_start_time_utc  DOUBLE      NOT NULL,
  start_idx             BIGINT      NOT NULL,
  end_idx               BIGINT      NOT NULL,
  window_duration        DOUBLE     NOT NULL,
  window_num_samples     BIGINT     NOT NULL,
  window_start_time_utc  DOUBLE     NOT NULL,
  sample_rate_hz          DOUBLE    NOT NULL,

  -- domain-specific fields live here, not as typed columns.
  -- LIGO: {"detector": "H1", "gps_start": "...", "gps_end": "..."}
  -- ECG:  {"lead": "II", "patient_id": "42"}
  domain_metadata         MAP<STRING, STRING>,

  -- runtime-computed, set by the notebook at write time
  ingestion_ts            TIMESTAMP NOT NULL,
  event_date              DATE      NOT NULL
)
USING DELTA
PARTITIONED BY (event_date)
LOCATION 's3://{bucket}/bronze/domain={domain}/'
COMMENT 'Bronze for domain={domain}: window-level metadata pointing back to raw assets in S3. No signal arrays stored here.';