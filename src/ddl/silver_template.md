# `silver_template.sql` — explained

The Silver-layer counterpart to
[`bronze_template.sql`](bronze_template.md), generated the exact same way
(via [`generate_ddl.py`](generate_ddl.md), pointed at
`SILVER_TEMPLATE_PATH` instead of `TEMPLATE_PATH`) — same `{domain}`/
`{bucket}` placeholders, same `IF NOT EXISTS` idempotency, same
`PARTITIONED BY (event_date)` scheme.

```sql
CREATE TABLE IF NOT EXISTS signal_platform.{domain}.silver (
  ...
)
USING DELTA
PARTITIONED BY (event_date)
LOCATION 's3://{bucket}/silver/domain={domain}/'
COMMENT 'Silver for domain={domain}: quality-checked, bandpass-filtered window samples, ready for Gold feature engineering.';
```

## Carried-through columns

The first ten columns, plus `domain_metadata`, are identical to
[`bronze_template.sql`](bronze_template.md) — every field
[`silver_builder.py`](../transformation/silver_builder.md) copies straight
through from its input Bronze row via `{**row, ...}`. Silver never
recomputes window boundaries or timing; it only adds to what Bronze
already established.

## What's new: quality flags and `filtered_samples`

```sql
  has_nan                 BOOLEAN   NOT NULL,
  has_inf                 BOOLEAN   NOT NULL,
  is_flatline              BOOLEAN  NOT NULL,
  all_zero                 BOOLEAN  NOT NULL,
  is_valid                 BOOLEAN  NOT NULL,

  filtered_samples          ARRAY<DOUBLE>,
```

The five `BOOLEAN` columns map one-to-one onto the dict
[`check_window_quality()`](../transformation/quality_checks.md) returns.
`filtered_samples` is the one genuinely new kind of column in this
platform so far: **it stores actual signal values inside Delta**, unlike
every Bronze column (which only ever stores metadata plus a pointer back
to the raw `.npy` in S3 — see that file's table comment). This is safe
here specifically because a *window* (a few thousand samples, ~64KB as
float64) is small enough to live as a table cell, where a whole *asset*
(potentially millions of samples) isn't. `filtered_samples` is `NULL`
whenever `is_valid=false` — [`silver_builder.py`](../transformation/silver_builder.md)
never runs the (expensive, and scientifically meaningless on garbage
data) bandpass filter on a window that already failed its quality checks.

## `LOCATION 's3://{bucket}/silver/domain={domain}/'`

Same bucket as Bronze, different top-level prefix (`silver/` instead of
`bronze/`) — so a domain's Bronze and Silver tables live side by side in
S3, distinguishable at a glance, using the identical
`domain=<domain>/` scoping pattern.

## In one sentence

`silver_template.sql` extends Bronze's schema with five quality-flag
columns and one `ARRAY<DOUBLE>` column holding the actual filtered window
samples — the first table in this platform that stores real signal data
rather than only metadata, made safe by the fact that a window (not a
whole asset) is small enough to fit.
