import argparse
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

INTERIM_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "interim"
)

FACT_LOAD_FILE = (
    INTERIM_DIRECTORY
    / "fact_flight_load.csv"
)

LOAD_SUMMARY_FILE = (
    INTERIM_DIRECTORY
    / "warehouse_load_summary.txt"
)


FACT_COLUMNS = [
    "date_key",
    "airline_key",
    "origin_airport_key",
    "destination_airport_key",
    "flight_number",
    "tail_number",
    "route_code",
    "scheduled_departure_time",
    "actual_departure_time",
    "scheduled_departure_hour",
    "departure_time_block",
    "scheduled_arrival_time",
    "actual_arrival_time",
    "scheduled_arrival_hour",
    "arrival_time_block",
    "departure_delay_minutes_signed",
    "departure_delay_minutes",
    "departure_delayed_15",
    "arrival_delay_minutes_signed",
    "arrival_delay_minutes",
    "arrival_delayed_15",
    "arrival_on_time",
    "taxi_out_minutes",
    "taxi_in_minutes",
    "scheduled_elapsed_minutes",
    "actual_elapsed_minutes",
    "air_time_minutes",
    "flight_count",
    "distance_miles",
    "distance_group",
    "cancelled",
    "cancellation_code",
    "diverted",
    "flight_status",
    "delay_cause_reported",
    "carrier_delay_minutes",
    "weather_delay_minutes",
    "national_air_system_delay_minutes",
    "security_delay_minutes",
    "late_aircraft_delay_minutes",
    "total_reported_delay_minutes",
]


def parse_arguments() -> argparse.Namespace:
    """Read command-line options."""

    argument_parser = argparse.ArgumentParser(
        description=(
            "Load the cleaned BTS flight dataset "
            "into the PostgreSQL data warehouse."
        )
    )

    argument_parser.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Delete existing warehouse data before loading. "
            "Use this for a complete reload."
        ),
    )

    return argument_parser.parse_args()


def get_database_settings() -> dict:
    """Load PostgreSQL settings from the local .env file."""

    if not ENVIRONMENT_FILE.exists():
        raise FileNotFoundError(
            f"Environment file was not found:\n{ENVIRONMENT_FILE}"
        )

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


def create_date_dimension(
    flight_data: pd.DataFrame,
) -> pd.DataFrame:
    """Create one row for each calendar date."""

    date_dimension = (
        flight_data[
            [
                "flight_date",
                "year",
                "quarter",
                "month",
                "day_of_month",
                "day_of_week",
                "is_weekend",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    date_dimension["date_key"] = (
        date_dimension["flight_date"]
        .dt.strftime("%Y%m%d")
        .astype(int)
    )

    date_dimension["month_name"] = (
        date_dimension["flight_date"]
        .dt.month_name()
    )

    date_dimension["day_name"] = (
        date_dimension["flight_date"]
        .dt.day_name()
    )

    date_dimension = date_dimension.rename(
        columns={
            "flight_date": "full_date",
            "year": "year_number",
            "quarter": "quarter_number",
            "month": "month_number",
            "day_of_month": "day_of_month",
            "day_of_week": "day_of_week_number",
        }
    )

    date_dimension = date_dimension[
        [
            "date_key",
            "full_date",
            "year_number",
            "quarter_number",
            "month_number",
            "month_name",
            "day_of_month",
            "day_of_week_number",
            "day_name",
            "is_weekend",
        ]
    ].sort_values("date_key")

    return date_dimension


def create_airline_dimension(
    flight_data: pd.DataFrame,
) -> pd.DataFrame:
    """Create one row for each airline."""

    airline_dimension = (
        flight_data[
            [
                "reporting_airline_id",
                "reporting_airline_code",
            ]
        ]
        .drop_duplicates()
        .sort_values("reporting_airline_id")
        .reset_index(drop=True)
    )

    airline_versions_per_id = (
        airline_dimension
        .groupby("reporting_airline_id")
        .size()
    )

    conflicting_airline_ids = (
        airline_versions_per_id[
            airline_versions_per_id > 1
        ]
        .index
        .tolist()
    )

    if conflicting_airline_ids:
        raise ValueError(
            "Conflicting airline attributes were found for IDs: "
            f"{conflicting_airline_ids}"
        )

    return airline_dimension


def create_airport_dimension(
    flight_data: pd.DataFrame,
) -> pd.DataFrame:
    """Combine origin and destination airports into one dimension."""

    origin_airports = flight_data[
        [
            "origin_airport_id",
            "origin_airport_code",
            "origin_city_name",
            "origin_state_code",
            "origin_state_name",
        ]
    ].rename(
        columns={
            "origin_airport_id": "airport_id",
            "origin_airport_code": "airport_code",
            "origin_city_name": "city_name",
            "origin_state_code": "state_code",
            "origin_state_name": "state_name",
        }
    )

    destination_airports = flight_data[
        [
            "destination_airport_id",
            "destination_airport_code",
            "destination_city_name",
            "destination_state_code",
            "destination_state_name",
        ]
    ].rename(
        columns={
            "destination_airport_id": "airport_id",
            "destination_airport_code": "airport_code",
            "destination_city_name": "city_name",
            "destination_state_code": "state_code",
            "destination_state_name": "state_name",
        }
    )

    airport_dimension = (
        pd.concat(
            [
                origin_airports,
                destination_airports,
            ],
            ignore_index=True,
        )
        .drop_duplicates()
        .sort_values("airport_id")
        .reset_index(drop=True)
    )

    airport_versions_per_id = (
        airport_dimension
        .groupby("airport_id")
        .size()
    )

    conflicting_airport_ids = (
        airport_versions_per_id[
            airport_versions_per_id > 1
        ]
        .index
        .tolist()
    )

    if conflicting_airport_ids:
        raise ValueError(
            "Conflicting airport attributes were found for IDs: "
            f"{conflicting_airport_ids[:20]}"
        )

    return airport_dimension


def load_date_dimension(
    cursor: psycopg.Cursor,
    date_dimension: pd.DataFrame,
) -> None:
    """Insert or update the date dimension."""

    insert_query = """
        INSERT INTO warehouse.dim_date (
            date_key,
            full_date,
            year_number,
            quarter_number,
            month_number,
            month_name,
            day_of_month,
            day_of_week_number,
            day_name,
            is_weekend
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        ON CONFLICT (date_key)
        DO UPDATE SET
            full_date = EXCLUDED.full_date,
            year_number = EXCLUDED.year_number,
            quarter_number = EXCLUDED.quarter_number,
            month_number = EXCLUDED.month_number,
            month_name = EXCLUDED.month_name,
            day_of_month = EXCLUDED.day_of_month,
            day_of_week_number = EXCLUDED.day_of_week_number,
            day_name = EXCLUDED.day_name,
            is_weekend = EXCLUDED.is_weekend;
    """

    dimension_rows = [
        (
            int(row.date_key),
            row.full_date.date(),
            int(row.year_number),
            int(row.quarter_number),
            int(row.month_number),
            str(row.month_name),
            int(row.day_of_month),
            int(row.day_of_week_number),
            str(row.day_name),
            bool(row.is_weekend),
        )
        for row in date_dimension.itertuples(index=False)
    ]

    cursor.executemany(
        insert_query,
        dimension_rows,
    )


def load_airline_dimension(
    cursor: psycopg.Cursor,
    airline_dimension: pd.DataFrame,
) -> None:
    """Insert or update the airline dimension."""

    insert_query = """
        INSERT INTO warehouse.dim_airline (
            reporting_airline_id,
            reporting_airline_code
        )
        VALUES (%s, %s)
        ON CONFLICT (reporting_airline_id)
        DO UPDATE SET
            reporting_airline_code =
                EXCLUDED.reporting_airline_code;
    """

    dimension_rows = [
        (
            int(row.reporting_airline_id),
            str(row.reporting_airline_code),
        )
        for row in airline_dimension.itertuples(index=False)
    ]

    cursor.executemany(
        insert_query,
        dimension_rows,
    )


def load_airport_dimension(
    cursor: psycopg.Cursor,
    airport_dimension: pd.DataFrame,
) -> None:
    """Insert or update the airport dimension."""

    insert_query = """
        INSERT INTO warehouse.dim_airport (
            airport_id,
            airport_code,
            city_name,
            state_code,
            state_name
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (airport_id)
        DO UPDATE SET
            airport_code = EXCLUDED.airport_code,
            city_name = EXCLUDED.city_name,
            state_code = EXCLUDED.state_code,
            state_name = EXCLUDED.state_name;
    """

    dimension_rows = []

    for row in airport_dimension.itertuples(index=False):
        dimension_rows.append(
            (
                int(row.airport_id),
                str(row.airport_code),
                None if pd.isna(row.city_name)
                else str(row.city_name),
                None if pd.isna(row.state_code)
                else str(row.state_code),
                None if pd.isna(row.state_name)
                else str(row.state_name),
            )
        )

    cursor.executemany(
        insert_query,
        dimension_rows,
    )


def get_airline_key_mapping(
    cursor: psycopg.Cursor,
) -> dict:
    """Return the natural airline ID to warehouse key mapping."""

    cursor.execute(
        """
        SELECT
            reporting_airline_id,
            airline_key
        FROM warehouse.dim_airline;
        """
    )

    return {
        reporting_airline_id: airline_key
        for reporting_airline_id, airline_key
        in cursor.fetchall()
    }


def get_airport_key_mapping(
    cursor: psycopg.Cursor,
) -> dict:
    """Return the natural airport ID to warehouse key mapping."""

    cursor.execute(
        """
        SELECT
            airport_id,
            airport_key
        FROM warehouse.dim_airport;
        """
    )

    return {
        airport_id: airport_key
        for airport_id, airport_key
        in cursor.fetchall()
    }


def create_fact_load_data(
    flight_data: pd.DataFrame,
    airline_key_mapping: dict,
    airport_key_mapping: dict,
) -> pd.DataFrame:
    """Create fact-table rows with dimension surrogate keys."""

    fact_data = flight_data.copy()

    fact_data["date_key"] = (
        fact_data["flight_date"]
        .dt.strftime("%Y%m%d")
        .astype(int)
    )

    fact_data["airline_key"] = (
        fact_data["reporting_airline_id"]
        .map(airline_key_mapping)
    )

    fact_data["origin_airport_key"] = (
        fact_data["origin_airport_id"]
        .map(airport_key_mapping)
    )

    fact_data["destination_airport_key"] = (
        fact_data["destination_airport_id"]
        .map(airport_key_mapping)
    )

    missing_dimension_key_count = int(
        fact_data[
            [
                "date_key",
                "airline_key",
                "origin_airport_key",
                "destination_airport_key",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    if missing_dimension_key_count > 0:
        raise ValueError(
            f"{missing_dimension_key_count:,} fact rows "
            "could not be matched to dimensions."
        )

    boolean_columns = [
        "departure_delayed_15",
        "arrival_delayed_15",
        "arrival_on_time",
        "cancelled",
        "diverted",
        "delay_cause_reported",
    ]

    for column_name in boolean_columns:
        fact_data[column_name] = (
            fact_data[column_name]
            .astype("boolean")
        )

    fact_data = fact_data[FACT_COLUMNS].copy()

    return fact_data


def copy_fact_data(
    cursor: psycopg.Cursor,
    fact_data: pd.DataFrame,
) -> None:
    """Use PostgreSQL COPY to load the fact table efficiently."""

    INTERIM_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"Writing temporary load file: {FACT_LOAD_FILE.name}"
    )

    fact_data.to_csv(
        FACT_LOAD_FILE,
        index=False,
        na_rep="",
    )

    copy_column_list = ", ".join(FACT_COLUMNS)

    copy_query = f"""
        COPY warehouse.fact_flight (
            {copy_column_list}
        )
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            NULL ''
        );
    """

    print(
        f"Copying {len(fact_data):,} fact rows "
        "into PostgreSQL..."
    )

    with FACT_LOAD_FILE.open("rb") as input_file:
        with cursor.copy(copy_query) as copy_process:
            while data_chunk := input_file.read(
                1024 * 1024
            ):
                copy_process.write(data_chunk)


def main() -> None:
    """Load dimensions and facts into PostgreSQL."""

    arguments = parse_arguments()

    if not CLEAN_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Clean Parquet file was not found:\n"
            f"{CLEAN_DATA_FILE}"
        )

    database_settings = get_database_settings()

    print("=" * 70)
    print("POSTGRESQL DATA WAREHOUSE LOAD")
    print("=" * 70)
    print(f"Reading: {CLEAN_DATA_FILE}")

    flight_data = pd.read_parquet(
        CLEAN_DATA_FILE
    )

    source_row_count = len(flight_data)

    print(f"Source rows: {source_row_count:,}")

    date_dimension = create_date_dimension(
        flight_data
    )

    airline_dimension = create_airline_dimension(
        flight_data
    )

    airport_dimension = create_airport_dimension(
        flight_data
    )

    print(
        f"Date dimension rows: {len(date_dimension):,}"
    )
    print(
        f"Airline dimension rows: {len(airline_dimension):,}"
    )
    print(
        f"Airport dimension rows: {len(airport_dimension):,}"
    )

    with psycopg.connect(
        **database_settings
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight;
                """
            )

            existing_fact_count = (
                cursor.fetchone()[0]
            )

            if existing_fact_count > 0:
                if not arguments.replace:
                    raise RuntimeError(
                        "The fact table already contains "
                        f"{existing_fact_count:,} rows. "
                        "Run again with --replace to perform "
                        "a complete reload."
                    )

                print(
                    "Existing warehouse data will be replaced."
                )

                cursor.execute(
                    """
                    TRUNCATE TABLE
                        warehouse.fact_flight,
                        warehouse.dim_date,
                        warehouse.dim_airline,
                        warehouse.dim_airport
                    RESTART IDENTITY CASCADE;
                    """
                )

            print("Loading date dimension...")
            load_date_dimension(
                cursor,
                date_dimension,
            )

            print("Loading airline dimension...")
            load_airline_dimension(
                cursor,
                airline_dimension,
            )

            print("Loading airport dimension...")
            load_airport_dimension(
                cursor,
                airport_dimension,
            )

            airline_key_mapping = (
                get_airline_key_mapping(cursor)
            )

            airport_key_mapping = (
                get_airport_key_mapping(cursor)
            )

            fact_data = create_fact_load_data(
                flight_data,
                airline_key_mapping,
                airport_key_mapping,
            )

            copy_fact_data(
                cursor,
                fact_data,
            )

            cursor.execute(
                """
                ANALYZE warehouse.dim_date;
                ANALYZE warehouse.dim_airline;
                ANALYZE warehouse.dim_airport;
                ANALYZE warehouse.fact_flight;
                """
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_date;
                """
            )
            loaded_date_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_airline;
                """
            )
            loaded_airline_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_airport;
                """
            )
            loaded_airport_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.fact_flight;
                """
            )
            loaded_fact_count = cursor.fetchone()[0]

    if loaded_fact_count != source_row_count:
        raise RuntimeError(
            "Fact row count does not match source data. "
            f"Source: {source_row_count:,}, "
            f"Warehouse: {loaded_fact_count:,}"
        )

    summary_lines = [
        "POSTGRESQL DATA WAREHOUSE LOAD SUMMARY",
        "=" * 70,
        f"Source file: {CLEAN_DATA_FILE.name}",
        f"Source rows: {source_row_count:,}",
        "",
        "LOADED TABLES",
        "-" * 70,
        f"warehouse.dim_date: {loaded_date_count:,}",
        (
            "warehouse.dim_airline: "
            f"{loaded_airline_count:,}"
        ),
        (
            "warehouse.dim_airport: "
            f"{loaded_airport_count:,}"
        ),
        (
            "warehouse.fact_flight: "
            f"{loaded_fact_count:,}"
        ),
        "",
        "STATUS",
        "-" * 70,
        "Warehouse load completed successfully.",
    ]

    LOAD_SUMMARY_FILE.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print()
    print("\n".join(summary_lines))
    print()
    print(f"Summary saved to: {LOAD_SUMMARY_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()