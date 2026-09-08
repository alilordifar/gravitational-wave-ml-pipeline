# `silver_builder.py` — explained

```python
"""
Builds Silver rows from one asset's Bronze rows plus that asset's raw
array (downloaded once, shared across every window it contains).

Mirrors bronze_builder.py's shape: pure Python/NumPy, no I/O, no Spark —
the S3 download and the Spark write both happen one layer up, in
src/pipelines/silver_batch.py.
"""
```

The Silver-layer counterpart to
[`bronze_builder.py`](bronze_builder.md), sitting at the same altitude:
pure Python taking already-loaded data in and producing plain dicts out,
with all I/O (the S3 download, the Delta write) pushed one layer up into
[`silver_batch.py`](../pipelines/silver_batch.md).

## `build_silver_rows` (lines 15-42)

```python
def build_silver_rows(bronze_rows: list[dict], raw_array: np.ndarray, domain: str) -> list[dict]:
    processor = get_processor(domain)
    silver_rows = []

    for row in bronze_rows:
        samples = raw_array[row["start_idx"]:row["end_idx"]]
        quality = check_window_quality(samples)

        filtered_samples = None
        if quality["is_valid"]:
            filtered_samples = processor(samples, row["sample_rate_hz"]).tolist()

        silver_rows.append({
            **row,
            **quality,
            "filtered_samples": filtered_samples,
        })

    return silver_rows
```

Takes **every Bronze row belonging to one asset** (all sharing the same
`asset_key`, i.e. the same `.npy` file) plus that asset's full raw array —
downloaded exactly once by the caller, since every window in `bronze_rows`
slices into the same array. This mirrors why Bronze rows carry
`start_idx`/`end_idx` rather than their own copy of the samples: one
download serves however many windows an asset was split into.

For each Bronze row:

1. **Slice** — `raw_array[start_idx:end_idx]` pulls out exactly that
   window's samples, using the indices [`windower.py`](windower.md)
   computed at Bronze-build time.
2. **Quality-check** — [`check_window_quality`](quality_checks.md) runs
   the domain-agnostic structural checks (NaN, Inf, flatline, all-zero).
3. **Filter, conditionally** — only when `quality["is_valid"]` is `True`
   does the window get run through
   [`get_processor(domain)`](processors/registry.md) — LIGO's
   [`apply_bandpass`](processors/ligo_bandpass.md), for now. A window that
   failed its quality check keeps `filtered_samples=None` rather than
   being dropped from the output entirely: it's still a useful row
   downstream (e.g. as a labeled negative example, or for debugging what
   fraction of an asset was garbage), just not a filtered one.
4. **Assemble** — `{**row, **quality, "filtered_samples": ...}` carries
   every Bronze field through unchanged (`window_id`, `asset_key`,
   `domain_metadata`, ...), adds the five quality flags, and adds
   `filtered_samples`. This dict shape matches
   [`silver_template.sql`](../ddl/silver_template.md) exactly, minus
   `ingestion_ts`/`event_date` — same deferral pattern as
   [`bronze_builder.py`](bronze_builder.md), where those two are stamped
   on by the pipeline at write time, not here.

`.tolist()` on the filter output matters, not cosmetic: Spark's
`filtered_samples` column is `ARRAY<DOUBLE>`, and a raw `numpy.ndarray`
isn't directly usable inside a Python dict handed to
`spark.createDataFrame` / a pandas UDF return value — it needs to be a
plain Python list of floats first.

## Why `domain` is a parameter, not inferred

Nothing in a Bronze row says what domain it belongs to (the Bronze/Silver
table name — `signal_platform.<domain>.bronze` — carries that instead).
[`silver_batch.py`](../pipelines/silver_batch.md) already knows which
domain's table it's reading, so it just passes that straight through,
rather than this function trying to infer it from row contents.

## In one sentence

`build_silver_rows` takes one asset's Bronze rows and its raw array,
slices out each window, quality-checks it, bandpass-filters it if it
passes, and returns the full Silver row shape — the one place Bronze
metadata and actual signal samples come back together before being
written to Delta.
