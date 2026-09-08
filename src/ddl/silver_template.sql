-- src/ddl/silver_template.sql
--
-- ONE template for every domain's Silver table, generated the same way as
-- bronze_template.sql (see generate_ddl.py — pass SILVER_TEMPLATE_PATH as
-- template_path). Extends every Bronze column with quality flags and a
-- filtered, window-sized array — small enough (thousands of samples, not
-- millions) to live directly in Delta, unlike Bronze's asset-level arrays.
--
-- Placeholders (substituted by generate_ddl.py): {domain}, {bucket}

CREATE TABLE IF NOT EXISTS signal_platform.{domain}.silver (
  -- carried through from Bronze, unchanged
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

  -- domain-specific fields, same MAP<STRING, STRING> as Bronze
  domain_metadata         MAP<STRING, STRING>,

  -- quality flags, from src/transformation/quality_checks.py
  has_nan                 BOOLEAN   NOT NULL,
  has_inf                 BOOLEAN   NOT NULL,
  is_flatline              BOOLEAN  NOT NULL,
  all_zero                 BOOLEAN  NOT NULL,
  is_valid                 BOOLEAN  NOT NULL,

  -- bandpass-filtered window samples; NULL when is_valid=false. Produced
  -- by whichever processor src/transformation/processors/registry.py
  -- resolves for this domain (LIGO: processors/ligo_bandpass.py)
  filtered_samples          ARRAY<DOUBLE>,

  -- runtime-computed, set by the pipeline at write time
  ingestion_ts             TIMESTAMP NOT NULL,
  event_date               DATE      NOT NULL
)
USING DELTA
PARTITIONED BY (event_date)
LOCATION 's3://{bucket}/silver/domain={domain}/'
COMMENT 'Silver for domain={domain}: quality-checked, bandpass-filtered window samples, ready for Gold feature engineering.';
