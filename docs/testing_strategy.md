# Testing Strategy

This project uses testing and validation at three levels: Python code health, data quality checks, and warehouse reconciliation.

## 1. Python Code Health

The GitHub Actions workflow runs on every push and pull request. It installs dependencies, runs tests when a `tests/` directory exists, and compiles all Python source files under `src/`.

```bash
python -m pytest -q
python -m compileall -q src
```

## 2. Data Validation

The pipeline already includes validation scripts for:

- raw source files;
- cleaned analytical datasets;
- warehouse reconciliation.

These checks are part of the portfolio value of the project because they show that the platform is not only a Power BI dashboard. It also validates source-to-target data integrity.

## 3. Recommended Unit Tests

Add unit tests for transformation functions that do not require the full raw CSV:

- route-code construction;
- flight-status classification;
- on-time arrival and departure flags;
- scheduled-hour parsing;
- weekend indicator generation;
- delay-cause total calculation.

## 4. Recommended Integration Tests

Add a small fixture dataset with 10-20 synthetic flight rows and test:

- raw validation passes for valid rows;
- clean transformation preserves row counts;
- expected dimensional keys are produced;
- cancelled and diverted flights are classified correctly;
- source-to-target reconciliation catches mismatched counts.

## 5. SQL Smoke Tests

For the PostgreSQL layer, add smoke tests that verify:

- warehouse schemas can be created from SQL files;
- required tables and views exist;
- primary and foreign key constraints are present;
- analytical views return rows for a small fixture load.

## 6. Local PostgreSQL Test Environment

The included `docker-compose.yml` starts a local PostgreSQL instance:

```bash
docker compose up -d postgres
```

Connection settings:

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DATABASE=flight_reliability
POSTGRES_USER=flight_admin
POSTGRES_PASSWORD=flight_password
```

This keeps local setup reproducible without requiring a manually installed PostgreSQL server.
