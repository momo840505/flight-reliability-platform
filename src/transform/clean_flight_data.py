from pathlib import Path

import pandas as pd


# Locate project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "flights_2024_01.csv"
)

PROCESSED_DATA_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

INTERIM_DATA_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "interim"
)

CLEAN_DATA_FILE = (
    PROCESSED_DATA_DIRECTORY
    / "flights_2024_01_clean.parquet"
)

CLEANING_SUMMARY_FILE = (
    INTERIM_DATA_DIRECTORY
    / "flights_2024_01_cleaning_summary.txt"
)


COLUMN_RENAME_MAP = {
    "YEAR": "year",
    "QUARTER": "quarter",
    "MONTH": "month",
    "DAY_OF_MONTH": "day_of_month",
    "DAY_OF_WEEK": "day_of_week",
    "FL_DATE": "flight_date",
    "OP_UNIQUE_CARRIER": "reporting_airline_code",
    "OP_CARRIER_AIRLINE_ID": "reporting_airline_id",
    "TAIL_NUM": "tail_number",
    "OP_CARRIER_FL_NUM": "flight_number",
    "ORIGIN_AIRPORT_ID": "origin_airport_id",
    "ORIGIN": "origin_airport_code",
    "ORIGIN_CITY_NAME": "origin_city_name",
    "ORIGIN_STATE_ABR": "origin_state_code",
    "ORIGIN_STATE_NM": "origin_state_name",
    "DEST_AIRPORT_ID": "destination_airport_id",
    "DEST": "destination_airport_code",
    "DEST_CITY_NAME": "destination_city_name",
    "DEST_STATE_ABR": "destination_state_code",
    "DEST_STATE_NM": "destination_state_name",
    "CRS_DEP_TIME": "scheduled_departure_time",
    "DEP_TIME": "actual_departure_time",
    "DEP_DELAY": "departure_delay_minutes_signed",
    "DEP_DELAY_NEW": "departure_delay_minutes",
    "DEP_DEL15": "departure_delayed_15",
    "DEP_TIME_BLK": "departure_time_block",
    "TAXI_OUT": "taxi_out_minutes",
    "TAXI_IN": "taxi_in_minutes",
    "CRS_ARR_TIME": "scheduled_arrival_time",
    "ARR_TIME": "actual_arrival_time",
    "ARR_DELAY": "arrival_delay_minutes_signed",
    "ARR_DELAY_NEW": "arrival_delay_minutes",
    "ARR_DEL15": "arrival_delayed_15",
    "ARR_TIME_BLK": "arrival_time_block",
    "CANCELLED": "cancelled",
    "CANCELLATION_CODE": "cancellation_code",
    "DIVERTED": "diverted",
    "CRS_ELAPSED_TIME": "scheduled_elapsed_minutes",
    "ACTUAL_ELAPSED_TIME": "actual_elapsed_minutes",
    "AIR_TIME": "air_time_minutes",
    "FLIGHTS": "flight_count",
    "DISTANCE": "distance_miles",
    "DISTANCE_GROUP": "distance_group",
    "CARRIER_DELAY": "carrier_delay_minutes",
    "WEATHER_DELAY": "weather_delay_minutes",
    "NAS_DELAY": "national_air_system_delay_minutes",
    "SECURITY_DELAY": "security_delay_minutes",
    "LATE_AIRCRAFT_DELAY": "late_aircraft_delay_minutes",
}


INTEGER_COLUMNS = {
    "year": "Int16",
    "quarter": "Int8",
    "month": "Int8",
    "day_of_month": "Int8",
    "day_of_week": "Int8",
    "reporting_airline_id": "Int32",
    "flight_number": "Int32",
    "origin_airport_id": "Int32",
    "destination_airport_id": "Int32",
    "scheduled_departure_time": "Int16",
    "actual_departure_time": "Int16",
    "departure_delayed_15": "Int8",
    "scheduled_arrival_time": "Int16",
    "actual_arrival_time": "Int16",
    "arrival_delayed_15": "Int8",
    "cancelled": "Int8",
    "diverted": "Int8",
    "flight_count": "Int8",
    "distance_group": "Int8",
}


FLOAT_COLUMNS = [
    "departure_delay_minutes_signed",
    "departure_delay_minutes",
    "taxi_out_minutes",
    "taxi_in_minutes",
    "arrival_delay_minutes_signed",
    "arrival_delay_minutes",
    "scheduled_elapsed_minutes",
    "actual_elapsed_minutes",
    "air_time_minutes",
    "distance_miles",
    "carrier_delay_minutes",
    "weather_delay_minutes",
    "national_air_system_delay_minutes",
    "security_delay_minutes",
    "late_aircraft_delay_minutes",
]


STRING_COLUMNS = [
    "reporting_airline_code",
    "tail_number",
    "origin_airport_code",
    "origin_city_name",
    "origin_state_code",
    "origin_state_name",
    "destination_airport_code",
    "destination_city_name",
    "destination_state_code",
    "destination_state_name",
    "departure_time_block",
    "arrival_time_block",
    "cancellation_code",
]


DELAY_CAUSE_COLUMNS = [
    "carrier_delay_minutes",
    "weather_delay_minutes",
    "national_air_system_delay_minutes",
    "security_delay_minutes",
    "late_aircraft_delay_minutes",
]


FLIGHT_KEY_COLUMNS = [
    "flight_date",
    "reporting_airline_id",
    "flight_number",
    "origin_airport_id",
    "destination_airport_id",
    "scheduled_departure_time",
]


def extract_hour_from_hhmm(
    time_values: pd.Series,
) -> pd.Series:
    """Extract an hour between 0 and 23 from an HHMM time value."""

    numeric_time_values = pd.to_numeric(
        time_values,
        errors="coerce",
    ).astype("Int64")

    hour_values = (
        numeric_time_values // 100
    ) % 24

    return hour_values.astype("Int8")


def main() -> None:
    """Clean the raw BTS flight data and save it as Parquet."""

    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Raw data file was not found:\n{RAW_DATA_FILE}"
        )

    PROCESSED_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    INTERIM_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("BTS FLIGHT DATA CLEANING")
    print("=" * 70)
    print(f"Reading raw data: {RAW_DATA_FILE}")
    print("This may take approximately 30 to 90 seconds.")

    flight_data = pd.read_csv(
        RAW_DATA_FILE,
        low_memory=False,
    )

    original_row_count = len(flight_data)
    original_column_count = len(flight_data.columns)

    missing_source_columns = sorted(
        set(COLUMN_RENAME_MAP)
        - set(flight_data.columns)
    )

    if missing_source_columns:
        raise ValueError(
            "Cleaning stopped because source columns are missing: "
            f"{missing_source_columns}"
        )

    # Keep only the fields explicitly selected for this project
    flight_data = flight_data[
        list(COLUMN_RENAME_MAP.keys())
    ].copy()

    # Rename database-style columns to readable snake_case names
    flight_data = flight_data.rename(
        columns=COLUMN_RENAME_MAP
    )

    # Parse the official BTS flight date
    flight_data["flight_date"] = pd.to_datetime(
        flight_data["flight_date"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce",
    )

    invalid_date_count = int(
        flight_data["flight_date"].isna().sum()
    )

    if invalid_date_count > 0:
        raise ValueError(
            f"Cleaning stopped because {invalid_date_count:,} "
            "invalid flight dates were found."
        )

    # Remove leading and trailing spaces from text fields
    for column_name in STRING_COLUMNS:
        flight_data[column_name] = (
            flight_data[column_name]
            .astype("string")
            .str.strip()
        )

        flight_data[column_name] = (
            flight_data[column_name]
            .replace("", pd.NA)
        )

    # Apply nullable integer data types
    for column_name, data_type in INTEGER_COLUMNS.items():
        flight_data[column_name] = pd.to_numeric(
            flight_data[column_name],
            errors="coerce",
        ).astype(data_type)

    # Apply memory-efficient floating-point data types
    for column_name in FLOAT_COLUMNS:
        flight_data[column_name] = pd.to_numeric(
            flight_data[column_name],
            errors="coerce",
        ).astype("Float32")

    missing_flight_key_count = int(
        flight_data[
            FLIGHT_KEY_COLUMNS
        ].isna().any(axis=1).sum()
    )

    if missing_flight_key_count > 0:
        raise ValueError(
            f"Cleaning stopped because {missing_flight_key_count:,} "
            "rows have missing flight key values."
        )

    # Remove only exact duplicate rows
    exact_duplicate_count = int(
        flight_data.duplicated().sum()
    )

    flight_data = flight_data.drop_duplicates().copy()

    # Record whether delay-cause details were originally supplied
    flight_data["delay_cause_reported"] = (
        flight_data[
            DELAY_CAUSE_COLUMNS
        ]
        .notna()
        .any(axis=1)
        .astype("boolean")
    )

    # Missing delay-cause values mean no minutes were reported
    flight_data[DELAY_CAUSE_COLUMNS] = (
        flight_data[
            DELAY_CAUSE_COLUMNS
        ]
        .fillna(0)
        .astype("Float32")
    )

    flight_data["total_reported_delay_minutes"] = (
        flight_data[
            DELAY_CAUSE_COLUMNS
        ]
        .sum(axis=1)
        .astype("Float32")
    )

    # Create useful analytical fields
    flight_data["route_code"] = (
        flight_data["origin_airport_code"]
        + "-"
        + flight_data["destination_airport_code"]
    ).astype("string")

    flight_data["is_weekend"] = (
        flight_data["day_of_week"]
        .isin([6, 7])
        .astype("boolean")
    )

    flight_data["scheduled_departure_hour"] = (
        extract_hour_from_hhmm(
            flight_data["scheduled_departure_time"]
        )
    )

    flight_data["scheduled_arrival_hour"] = (
        extract_hour_from_hhmm(
            flight_data["scheduled_arrival_time"]
        )
    )

    flight_data["flight_status"] = pd.Series(
        "Completed",
        index=flight_data.index,
        dtype="string",
    )

    flight_data.loc[
        flight_data["diverted"] == 1,
        "flight_status",
    ] = "Diverted"

    flight_data.loc[
        flight_data["cancelled"] == 1,
        "flight_status",
    ] = "Cancelled"

    flight_data["arrival_on_time"] = pd.Series(
        pd.NA,
        index=flight_data.index,
        dtype="boolean",
    )

    completed_arrival_rows = (
        (flight_data["flight_status"] == "Completed")
        & flight_data["arrival_delayed_15"].notna()
    )

    flight_data.loc[
        completed_arrival_rows,
        "arrival_on_time",
    ] = (
        flight_data.loc[
            completed_arrival_rows,
            "arrival_delayed_15",
        ]
        == 0
    )

    # Sort the dataset into a stable, reproducible order
    flight_data = flight_data.sort_values(
        by=[
            "flight_date",
            "reporting_airline_id",
            "flight_number",
            "origin_airport_id",
            "scheduled_departure_time",
        ],
        kind="stable",
    ).reset_index(drop=True)

    cleaned_row_count = len(flight_data)
    cleaned_column_count = len(flight_data.columns)

    completed_flight_count = int(
        (flight_data["flight_status"] == "Completed").sum()
    )

    cancelled_flight_count = int(
        (flight_data["flight_status"] == "Cancelled").sum()
    )

    diverted_flight_count = int(
        (flight_data["flight_status"] == "Diverted").sum()
    )

    on_time_arrival_count = int(
        (flight_data["arrival_on_time"] == True).sum()
    )

    delayed_arrival_count = int(
        (flight_data["arrival_on_time"] == False).sum()
    )

    # Save using Parquet for smaller size and preserved data types
    flight_data.to_parquet(
        CLEAN_DATA_FILE,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    output_file_size_megabytes = (
        CLEAN_DATA_FILE.stat().st_size
        / 1024
        / 1024
    )

    summary_lines = [
        "BTS FLIGHT DATA CLEANING SUMMARY",
        "=" * 70,
        f"Source file: {RAW_DATA_FILE.name}",
        f"Output file: {CLEAN_DATA_FILE.name}",
        "",
        "ROW AND COLUMN COUNTS",
        "-" * 70,
        f"Original rows: {original_row_count:,}",
        f"Cleaned rows: {cleaned_row_count:,}",
        f"Exact duplicate rows removed: {exact_duplicate_count:,}",
        f"Original columns: {original_column_count}",
        f"Cleaned columns: {cleaned_column_count}",
        "",
        "FLIGHT STATUS",
        "-" * 70,
        f"Completed flights: {completed_flight_count:,}",
        f"Cancelled flights: {cancelled_flight_count:,}",
        f"Diverted flights: {diverted_flight_count:,}",
        f"On-time completed arrivals: {on_time_arrival_count:,}",
        f"Delayed completed arrivals: {delayed_arrival_count:,}",
        "",
        "TRANSFORMATIONS",
        "-" * 70,
        "Column names converted to descriptive snake_case.",
        "Flight date converted to datetime.",
        "Text values trimmed and blank strings converted to null.",
        "Numeric fields converted to nullable numeric types.",
        "Exact duplicate rows removed.",
        "Missing reported delay-cause minutes converted to zero.",
        "Original delay-cause availability retained in delay_cause_reported.",
        "Route, weekend, hour, status and on-time fields created.",
        "",
        "OUTPUT",
        "-" * 70,
        (
            "Parquet file size: "
            f"{output_file_size_megabytes:.2f} MB"
        ),
    ]

    CLEANING_SUMMARY_FILE.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print()
    print("\n".join(summary_lines))
    print()
    print(f"Clean data saved to: {CLEAN_DATA_FILE}")
    print(f"Summary saved to: {CLEANING_SUMMARY_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()