# Incremental Loading Design

The current pilot dataset covers January 2024. A production-style extension should support monthly incremental loading.

## Goal

Load new monthly BTS flight files without rebuilding the full warehouse every time.

## Proposed Source Layout

```text
data/raw/
  flights_2024_01.csv
  flights_2024_02.csv
  flights_2024_03.csv
```

Each file should be treated as an immutable source extract.

## Control Table

Add a pipeline control table:

```sql
CREATE TABLE IF NOT EXISTS warehouse.load_batch (
    batch_id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL UNIQUE,
    reporting_year INT NOT NULL,
    reporting_month INT NOT NULL,
    source_row_count BIGINT NOT NULL,
    loaded_row_count BIGINT NOT NULL,
    load_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    load_completed_at TIMESTAMPTZ,
    status TEXT NOT NULL
);
```

## Incremental Load Steps

1. Detect raw files not present in `warehouse.load_batch`.
2. Validate each raw file independently.
3. Clean and transform each file into monthly Parquet output.
4. Upsert dimensions such as date, airline, and airport.
5. Insert facts using a stable source flight key.
6. Reconcile source row count to inserted fact rows.
7. Mark the batch as completed only after all checks pass.

## Idempotency

The loader should be safe to rerun:

- source files are immutable;
- duplicate source files are rejected by `source_file`;
- fact rows use stable natural keys or deterministic surrogate keys;
- failed batches can be retried after rollback or cleanup.

## Portfolio Value

Incremental loading demonstrates:

- production-style data engineering thinking;
- batch metadata management;
- source-to-target reconciliation;
- idempotent pipeline design;
- readiness for scheduled monthly refreshes.
