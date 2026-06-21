import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENVIRONMENT_FILE = PROJECT_ROOT / ".env"

CLEAN_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "flights_2024_01_clean.parquet"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "interim"
)

VALIDATION_RESULTS_FILE = (
    OUTPUT_DIRECTORY
    / "warehouse_validation_results.csv"
)

VALIDATION_SUMMARY_FILE = (
    OUTPUT_DIRECTORY
    / "warehouse_validation_summary.txt"
)


def get_database_settings() -> dict:
    """Load PostgreSQL settings from the local .env file."""

    load_dotenv(ENVIRONMENT_FILE)

    database_settings = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DATABASE"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
        "connect_timeout": 10,
    }

    missing_settings = [
        setting_name
        for setting_name, setting_value
        in database_settings.items()
        if setting_name != "connect_timeout"
        and not setting_value
    ]

    if missing_settings:
        raise ValueError(
            f"Missing database settings: {missing_settings}"
        )

    return database_settings


def add_result(
    validation_results: list[dict],
    rule_name: str,
    expected_value: int,
    actual_value: int,
    description: str,
) -> None:
    """Add one warehouse validation result."""

    status = (
        "PASS"
        if expected_value == actual_value
        else "FAIL"
    )

    validation_results.append(
        {
            "rule_name": rule_name,
            "status": status,
            "expected_value": int(expected_value),
            "actual_value": int(actual_value),
            "description": description,
        }
    )


def fetch_single_value(
    cursor: psycopg.Cursor,
    query: str,
) -> int:
    """Execute a query that returns one numeric value."""

    cursor.execute(query)

    return int(cursor.fetchone()[0])


def main() -> None:
    """Compare the PostgreSQL warehouse with the clean Parquet data."""

    if not CLEAN_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Clean data file was not found:\n"
            f"{CLEAN_DATA_FILE}"
        )

    if not ENVIRONMENT_FILE.exists():
        raise FileNotFoundError(
            f"Environment file was not found:\n"
            f"{ENVIRONMENT_FILE}"
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("POSTGRESQL WAREHOUSE VALIDATION")
    print("=" * 70)

    clean_data = pd.read_parquet(
        CLEAN_DATA_FILE
    )

    expected_fact_count = len(clean_data)

    expected_date_count = int(
        clean_data["flight_date"].nunique()
    )

    expected_airline_count = int(
        clean_data[
            "reporting_airline_id"
        ].nunique()
    )

    expected_airport_count = len(
        set(
            clean_data[
                "origin_airport_id"
            ].dropna().astype(int)
        )
        |
        set(
            clean_data[
                "destination_airport_id"
            ].dropna().astype(int)
        )
    )

    expected_completed_count = int(
        (
            clean_data["flight_status"]
            == "Completed"
        ).sum()
    )

    expected_cancelled_count = int(
        (
            clean_data["flight_status"]
            == "Cancelled"
        ).sum()
    )

    expected_diverted_count = int(
        (
            clean_data["flight_status"]
            == "Diverted"
        ).sum()
    )

    expected_on_time_count = int(
        (
            clean_data["arrival_on_time"]
            == True
        ).sum()
    )

    expected_delayed_count = int(
        (
            clean_data["arrival_on_time"]
            == False
        ).sum()
    )

    expected_unknown_arrival_count = int(
        clean_data[
            "arrival_on_time"
        ].isna().sum()
    )

    database_settings = get_database_settings()

    validation_results = []

    with psycopg.connect(
        **database_settings
    ) as connection:

        with connection.cursor() as cursor:

            actual_date_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.dim_date;
                """,
            )

            actual_airline_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.dim_airline;
                """,
            )

            actual_airport_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.dim_airport;
                """,
            )

            actual_fact_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight;
                """,
            )

            actual_completed_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight
                WHERE flight_status = 'Completed';
                """,
            )

            actual_cancelled_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight
                WHERE flight_status = 'Cancelled';
                """,
            )

            actual_diverted_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight
                WHERE flight_status = 'Diverted';
                """,
            )

            actual_on_time_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight
                WHERE arrival_on_time = TRUE;
                """,
            )

            actual_delayed_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight
                WHERE arrival_on_time = FALSE;
                """,
            )

            actual_unknown_arrival_count = (
                fetch_single_value(
                    cursor,
                    """
                    SELECT COUNT(*)
                    FROM warehouse.fact_flight
                    WHERE arrival_on_time IS NULL;
                    """,
                )
            )

            orphan_date_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight AS fact
                LEFT JOIN warehouse.dim_date AS date_dim
                    ON fact.date_key = date_dim.date_key
                WHERE date_dim.date_key IS NULL;
                """,
            )

            orphan_airline_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight AS fact
                LEFT JOIN warehouse.dim_airline AS airline_dim
                    ON fact.airline_key =
                       airline_dim.airline_key
                WHERE airline_dim.airline_key IS NULL;
                """,
            )

            orphan_origin_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight AS fact
                LEFT JOIN warehouse.dim_airport AS airport_dim
                    ON fact.origin_airport_key =
                       airport_dim.airport_key
                WHERE airport_dim.airport_key IS NULL;
                """,
            )

            orphan_destination_count = fetch_single_value(
                cursor,
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight AS fact
                LEFT JOIN warehouse.dim_airport AS airport_dim
                    ON fact.destination_airport_key =
                       airport_dim.airport_key
                WHERE airport_dim.airport_key IS NULL;
                """,
            )

    add_result(
        validation_results,
        "date_dimension_count",
        expected_date_count,
        actual_date_count,
        "Date dimension count must match unique source dates.",
    )

    add_result(
        validation_results,
        "airline_dimension_count",
        expected_airline_count,
        actual_airline_count,
        "Airline dimension count must match unique airlines.",
    )

    add_result(
        validation_results,
        "airport_dimension_count",
        expected_airport_count,
        actual_airport_count,
        "Airport dimension count must match unique airports.",
    )

    add_result(
        validation_results,
        "fact_flight_count",
        expected_fact_count,
        actual_fact_count,
        "Fact-table count must match the clean source dataset.",
    )

    add_result(
        validation_results,
        "completed_flight_count",
        expected_completed_count,
        actual_completed_count,
        "Completed flight count must match the clean data.",
    )

    add_result(
        validation_results,
        "cancelled_flight_count",
        expected_cancelled_count,
        actual_cancelled_count,
        "Cancelled flight count must match the clean data.",
    )

    add_result(
        validation_results,
        "diverted_flight_count",
        expected_diverted_count,
        actual_diverted_count,
        "Diverted flight count must match the clean data.",
    )

    add_result(
        validation_results,
        "on_time_arrival_count",
        expected_on_time_count,
        actual_on_time_count,
        "On-time completed arrivals must match.",
    )

    add_result(
        validation_results,
        "delayed_arrival_count",
        expected_delayed_count,
        actual_delayed_count,
        "Delayed completed arrivals must match.",
    )

    add_result(
        validation_results,
        "unknown_arrival_count",
        expected_unknown_arrival_count,
        actual_unknown_arrival_count,
        "Unknown arrival outcomes must match.",
    )

    add_result(
        validation_results,
        "no_orphan_date_keys",
        0,
        orphan_date_count,
        "Every fact row must match a date dimension row.",
    )

    add_result(
        validation_results,
        "no_orphan_airline_keys",
        0,
        orphan_airline_count,
        "Every fact row must match an airline dimension row.",
    )

    add_result(
        validation_results,
        "no_orphan_origin_keys",
        0,
        orphan_origin_count,
        "Every origin key must match an airport dimension row.",
    )

    add_result(
        validation_results,
        "no_orphan_destination_keys",
        0,
        orphan_destination_count,
        "Every destination key must match an airport dimension row.",
    )

    validation_results_table = pd.DataFrame(
        validation_results
    )

    validation_results_table.to_csv(
        VALIDATION_RESULTS_FILE,
        index=False,
    )

    failed_rule_count = int(
        (
            validation_results_table["status"]
            == "FAIL"
        ).sum()
    )

    overall_status = (
        "PASS"
        if failed_rule_count == 0
        else "FAIL"
    )

    summary_lines = [
        "POSTGRESQL WAREHOUSE VALIDATION SUMMARY",
        "=" * 70,
        (
            "Validation rules checked: "
            f"{len(validation_results_table)}"
        ),
        f"Failed rules: {failed_rule_count}",
        f"Overall status: {overall_status}",
        "",
        validation_results_table.to_string(
            index=False
        ),
    ]

    VALIDATION_SUMMARY_FILE.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print(
        validation_results_table.to_string(
            index=False
        )
    )

    print()
    print(f"Overall status: {overall_status}")
    print(
        f"Results saved to: {VALIDATION_RESULTS_FILE}"
    )
    print(
        f"Summary saved to: {VALIDATION_SUMMARY_FILE}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()