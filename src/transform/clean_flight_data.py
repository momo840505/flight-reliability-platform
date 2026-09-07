from pathlib import Path

import pandas as pd

from src.contracts import (
    CLEAN_FLIGHT_KEY_COLUMNS,
    DELAY_CAUSE_COLUMNS,
    SOURCE_COLUMN_RENAME_MAP,
    SOURCE_COLUMNS,
    WAREHOUSE_REQUIRED_CLEAN_COLUMNS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_FILE = PROJECT_ROOT / "data" / "raw" / "flights_2024_01.csv"
PROCESSED_DATA_DIRECTORY = PROJECT_ROOT / "data" / "processed"
INTERIM_DATA_DIRECTORY = PROJECT_ROOT / "data" / "interim"
CLEAN_DATA_FILE = PROCESSED_DATA_DIRECTORY / "flights_2024_01_clean.parquet"
CLEANING_SUMMARY_FILE = INTERIM_DATA_DIRECTORY / "flights_2024_01_cleaning_summary.txt"

COLUMN_RENAME_MAP = SOURCE_COLUMN_RENAME_MAP

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
    *DELAY_CAUSE_COLUMNS,
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


def extract_hour_from_hhmm(time_values: pd.Series) -> pd.Series:
    """Return the hour from valid HHMM values; invalid values become missing."""

    numeric = pd.to_numeric(time_values, errors="coerce").astype("Int64")
    hours = numeric // 100
    minutes = numeric % 100

    valid = (
        ((hours.between(0, 23)) & (minutes.between(0, 59)))
        | (numeric == 2400)
    )

    result = pd.Series(pd.NA, index=time_values.index, dtype="Int8")
    result.loc[valid] = (hours.loc[valid] % 24).astype("Int8")
    return result


def _raise_if_invalid_scheduled_times(flight_data: pd.DataFrame) -> None:
    for column_name in ["scheduled_departure_time", "scheduled_arrival_time"]:
        parsed_hour = extract_hour_from_hhmm(flight_data[column_name])
        invalid_count = int(parsed_hour.isna().sum())
        if invalid_count:
            raise ValueError(
                f"Cleaning stopped because {invalid_count:,} rows have invalid "
                f"{column_name} values."
            )


def _raise_if_missing_warehouse_values(flight_data: pd.DataFrame) -> None:
    missing_counts = {
        column: int(flight_data[column].isna().sum())
        for column in WAREHOUSE_REQUIRED_CLEAN_COLUMNS
        if column in flight_data.columns and flight_data[column].isna().any()
    }
    if missing_counts:
        details = ", ".join(
            f"{column}={count:,}" for column, count in sorted(missing_counts.items())
        )
        raise ValueError(
            "Cleaning stopped because required warehouse values are missing: "
            f"{details}"
        )


def clean_flight_dataframe(flight_data: pd.DataFrame) -> pd.DataFrame:
    """Clean and enrich a BTS flight DataFrame."""

    missing_source_columns = sorted(set(SOURCE_COLUMNS) - set(flight_data.columns))
    if missing_source_columns:
        raise ValueError(
            "Cleaning stopped because source columns are missing: "
            f"{missing_source_columns}"
        )

    flight_data = flight_data[SOURCE_COLUMNS].copy()
    flight_data = flight_data.rename(columns=COLUMN_RENAME_MAP)

    flight_data["flight_date"] = pd.to_datetime(
        flight_data["flight_date"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce",
    )
    invalid_date_count = int(flight_data["flight_date"].isna().sum())
    if invalid_date_count:
        raise ValueError(
            f"Cleaning stopped because {invalid_date_count:,} invalid flight dates were found."
        )

    for column_name in STRING_COLUMNS:
        flight_data[column_name] = (
            flight_data[column_name].astype("string").str.strip().replace("", pd.NA)
        )

    for column_name, data_type in INTEGER_COLUMNS.items():
        flight_data[column_name] = pd.to_numeric(
            flight_data[column_name], errors="coerce"
        ).astype(data_type)

    for column_name in FLOAT_COLUMNS:
        flight_data[column_name] = pd.to_numeric(
            flight_data[column_name], errors="coerce"
        ).astype("Float32")

    missing_flight_key_count = int(
        flight_data[CLEAN_FLIGHT_KEY_COLUMNS].isna().any(axis=1).sum()
    )
    if missing_flight_key_count:
        raise ValueError(
            f"Cleaning stopped because {missing_flight_key_count:,} rows have "
            "missing flight key values."
        )

    invalid_status_flags = (
        ~flight_data["cancelled"].isin([0, 1])
        | ~flight_data["diverted"].isin([0, 1])
    )
    invalid_status_flag_count = int(invalid_status_flags.fillna(True).sum())
    if invalid_status_flag_count:
        raise ValueError(
            f"Cleaning stopped because {invalid_status_flag_count:,} rows have "
            "invalid cancelled/diverted indicators."
        )

    both_status_count = int(
        ((flight_data["cancelled"] == 1) & (flight_data["diverted"] == 1)).sum()
    )
    if both_status_count:
        raise ValueError(
            f"Cleaning stopped because {both_status_count:,} rows are marked as both "
            "cancelled and diverted."
        )

    _raise_if_invalid_scheduled_times(flight_data)

    exact_duplicate_count = int(flight_data.duplicated().sum())
    flight_data = flight_data.drop_duplicates().copy()

    flight_data["delay_cause_reported"] = (
        flight_data[DELAY_CAUSE_COLUMNS].notna().any(axis=1).astype("boolean")
    )
    flight_data[DELAY_CAUSE_COLUMNS] = (
        flight_data[DELAY_CAUSE_COLUMNS].fillna(0).astype("Float32")
    )
    flight_data["total_reported_delay_minutes"] = (
        flight_data[DELAY_CAUSE_COLUMNS].sum(axis=1).astype("Float32")
    )

    # Calendar fields are derived from the parsed date so the cleaned output does
    # not depend on duplicated source calendar attributes.
    flight_data["year"] = flight_data["flight_date"].dt.year.astype("Int16")
    flight_data["quarter"] = flight_data["flight_date"].dt.quarter.astype("Int8")
    flight_data["month"] = flight_data["flight_date"].dt.month.astype("Int8")
    flight_data["day_of_month"] = flight_data["flight_date"].dt.day.astype("Int8")
    flight_data["day_of_week"] = (
        flight_data["flight_date"].dt.dayofweek.add(1).astype("Int8")
    )

    flight_data["route_code"] = (
        flight_data["origin_airport_code"]
        + "-"
        + flight_data["destination_airport_code"]
    ).astype("string")
    flight_data["is_weekend"] = flight_data["day_of_week"].isin([6, 7]).astype("boolean")
    flight_data["scheduled_departure_hour"] = extract_hour_from_hhmm(
        flight_data["scheduled_departure_time"]
    )
    flight_data["scheduled_arrival_hour"] = extract_hour_from_hhmm(
        flight_data["scheduled_arrival_time"]
    )

    flight_data["flight_status"] = pd.Series(
        "Completed", index=flight_data.index, dtype="string"
    )
    flight_data.loc[flight_data["diverted"] == 1, "flight_status"] = "Diverted"
    flight_data.loc[flight_data["cancelled"] == 1, "flight_status"] = "Cancelled"

    flight_data["arrival_on_time"] = pd.Series(
        pd.NA, index=flight_data.index, dtype="boolean"
    )
    completed_arrival_rows = (
        (flight_data["flight_status"] == "Completed")
        & flight_data["arrival_delayed_15"].notna()
    )
    flight_data.loc[completed_arrival_rows, "arrival_on_time"] = (
        flight_data.loc[completed_arrival_rows, "arrival_delayed_15"] == 0
    )

    _raise_if_missing_warehouse_values(flight_data)

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
    flight_data.attrs["exact_duplicate_count"] = exact_duplicate_count
    return flight_data


def main() -> None:
    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(f"Raw data file was not found:\n{RAW_DATA_FILE}")

    PROCESSED_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    INTERIM_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("BTS FLIGHT DATA CLEANING")
    print("=" * 70)
    print(f"Reading raw data: {RAW_DATA_FILE}")

    raw_flight_data = pd.read_csv(RAW_DATA_FILE, low_memory=False)
    original_row_count = len(raw_flight_data)
    original_column_count = len(raw_flight_data.columns)

    flight_data = clean_flight_dataframe(raw_flight_data)
    exact_duplicate_count = flight_data.attrs["exact_duplicate_count"]

    flight_data.to_parquet(
        CLEAN_DATA_FILE,
        index=False,
        engine="pyarrow",
        compression="snappy",
    )

    output_file_size_megabytes = CLEAN_DATA_FILE.stat().st_size / 1024 / 1024
    completed_flight_count = int((flight_data["flight_status"] == "Completed").sum())
    cancelled_flight_count = int((flight_data["flight_status"] == "Cancelled").sum())
    diverted_flight_count = int((flight_data["flight_status"] == "Diverted").sum())
    on_time_arrival_count = int((flight_data["arrival_on_time"] == True).sum())
    delayed_arrival_count = int((flight_data["arrival_on_time"] == False).sum())

    summary_lines = [
        "BTS FLIGHT DATA CLEANING SUMMARY",
        "=" * 70,
        f"Source file: {RAW_DATA_FILE.name}",
        f"Output file: {CLEAN_DATA_FILE.name}",
        "",
        "ROW AND COLUMN COUNTS",
        "-" * 70,
        f"Original rows: {original_row_count:,}",
        f"Cleaned rows: {len(flight_data):,}",
        f"Exact duplicate rows removed: {exact_duplicate_count:,}",
        f"Original columns: {original_column_count}",
        f"Cleaned columns: {len(flight_data.columns)}",
        "",
        "FLIGHT STATUS",
        "-" * 70,
        f"Completed flights: {completed_flight_count:,}",
        f"Cancelled flights: {cancelled_flight_count:,}",
        f"Diverted flights: {diverted_flight_count:,}",
        f"On-time completed arrivals: {on_time_arrival_count:,}",
        f"Delayed completed arrivals: {delayed_arrival_count:,}",
        "",
        "OUTPUT",
        "-" * 70,
        f"Parquet file size: {output_file_size_megabytes:.2f} MB",
    ]

    CLEANING_SUMMARY_FILE.write_text("\n".join(summary_lines), encoding="utf-8")
    print("\n".join(summary_lines))
    print(f"Clean data saved to: {CLEAN_DATA_FILE}")
    print(f"Summary saved to: {CLEANING_SUMMARY_FILE}")
    print("=" * 70)


if __name__ == "__main__":
    main()
