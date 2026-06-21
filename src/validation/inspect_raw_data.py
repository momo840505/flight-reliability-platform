from pathlib import Path

import pandas as pd


# Locate the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Define input and output paths
RAW_DATA_FILE = PROJECT_ROOT / "data" / "raw" / "flights_2024_01.csv"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "interim"

PROFILE_REPORT_FILE = OUTPUT_DIRECTORY / "flights_2024_01_profile.txt"
MISSING_VALUES_FILE = OUTPUT_DIRECTORY / "flights_2024_01_missing_values.csv"
DATA_TYPES_FILE = OUTPUT_DIRECTORY / "flights_2024_01_data_types.csv"


# Expected columns from the BTS download
EXPECTED_COLUMNS = [
    "YEAR",
    "QUARTER",
    "MONTH",
    "DAY_OF_MONTH",
    "DAY_OF_WEEK",
    "FL_DATE",
    "OP_UNIQUE_CARRIER",
    "OP_CARRIER_AIRLINE_ID",
    "TAIL_NUM",
    "OP_CARRIER_FL_NUM",
    "ORIGIN_AIRPORT_ID",
    "ORIGIN",
    "ORIGIN_CITY_NAME",
    "ORIGIN_STATE_ABR",
    "ORIGIN_STATE_NM",
    "DEST_AIRPORT_ID",
    "DEST",
    "DEST_CITY_NAME",
    "DEST_STATE_ABR",
    "DEST_STATE_NM",
    "CRS_DEP_TIME",
    "DEP_TIME",
    "DEP_DELAY",
    "DEP_DELAY_NEW",
    "DEP_DEL15",
    "DEP_TIME_BLK",
    "TAXI_OUT",
    "TAXI_IN",
    "CRS_ARR_TIME",
    "ARR_TIME",
    "ARR_DELAY",
    "ARR_DELAY_NEW",
    "ARR_DEL15",
    "ARR_TIME_BLK",
    "CANCELLED",
    "CANCELLATION_CODE",
    "DIVERTED",
    "CRS_ELAPSED_TIME",
    "ACTUAL_ELAPSED_TIME",
    "AIR_TIME",
    "FLIGHTS",
    "DISTANCE",
    "DISTANCE_GROUP",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY",
]


# Columns used to identify an individual scheduled flight segment
FLIGHT_KEY_COLUMNS = [
    "FL_DATE",
    "OP_CARRIER_AIRLINE_ID",
    "OP_CARRIER_FL_NUM",
    "ORIGIN_AIRPORT_ID",
    "DEST_AIRPORT_ID",
    "CRS_DEP_TIME",
]


def main() -> None:
    """Inspect the raw BTS flight dataset and create profiling reports."""

    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Raw data file was not found:\n{RAW_DATA_FILE}"
        )

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("BTS RAW FLIGHT DATA INSPECTION")
    print("=" * 60)
    print(f"Reading file: {RAW_DATA_FILE}")
    print("This may take approximately 30 to 90 seconds.")

    flight_data = pd.read_csv(
        RAW_DATA_FILE,
        low_memory=False,
    )

    row_count = len(flight_data)
    column_count = len(flight_data.columns)

    actual_columns = flight_data.columns.tolist()

    missing_expected_columns = sorted(
        set(EXPECTED_COLUMNS) - set(actual_columns)
    )

    unexpected_columns = sorted(
        set(actual_columns) - set(EXPECTED_COLUMNS)
    )

    exact_duplicate_count = int(
        flight_data.duplicated().sum()
    )

    duplicate_flight_key_count = int(
        flight_data.duplicated(
            subset=FLIGHT_KEY_COLUMNS,
            keep=False,
        ).sum()
    )

    flight_dates = pd.to_datetime(
        flight_data["FL_DATE"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce",
    )

    invalid_date_count = int(flight_dates.isna().sum())

    cancelled_flight_count = int(
        (flight_data["CANCELLED"] == 1).sum()
    )

    diverted_flight_count = int(
        (flight_data["DIVERTED"] == 1).sum()
    )

    delayed_arrival_count = int(
        (flight_data["ARR_DEL15"] == 1).sum()
    )

    unique_airline_count = int(
        flight_data["OP_CARRIER_AIRLINE_ID"].nunique()
    )

    unique_origin_airport_count = int(
        flight_data["ORIGIN_AIRPORT_ID"].nunique()
    )

    unique_destination_airport_count = int(
        flight_data["DEST_AIRPORT_ID"].nunique()
    )

    missing_value_summary = pd.DataFrame(
        {
            "column_name": actual_columns,
            "missing_count": flight_data.isna().sum().values,
        }
    )

    missing_value_summary["missing_percentage"] = (
        missing_value_summary["missing_count"]
        / row_count
        * 100
    ).round(2)

    missing_value_summary = missing_value_summary.sort_values(
        by=["missing_percentage", "column_name"],
        ascending=[False, True],
    )

    missing_value_summary.to_csv(
        MISSING_VALUES_FILE,
        index=False,
    )

    data_type_summary = pd.DataFrame(
        {
            "column_name": actual_columns,
            "data_type": [
                str(data_type)
                for data_type in flight_data.dtypes
            ],
        }
    )

    data_type_summary.to_csv(
        DATA_TYPES_FILE,
        index=False,
    )

    report_lines = [
        "BTS RAW FLIGHT DATA PROFILE",
        "=" * 60,
        f"Source file: {RAW_DATA_FILE.name}",
        f"Number of rows: {row_count:,}",
        f"Number of columns: {column_count}",
        "",
        "DATE COVERAGE",
        "-" * 60,
        f"Minimum flight date: {flight_dates.min().date()}",
        f"Maximum flight date: {flight_dates.max().date()}",
        f"Invalid flight dates: {invalid_date_count:,}",
        "",
        "SCHEMA VALIDATION",
        "-" * 60,
        f"Missing expected columns: {missing_expected_columns}",
        f"Unexpected columns: {unexpected_columns}",
        "",
        "DUPLICATE VALIDATION",
        "-" * 60,
        f"Exact duplicate rows: {exact_duplicate_count:,}",
        (
            "Rows with duplicate flight keys: "
            f"{duplicate_flight_key_count:,}"
        ),
        "",
        "FLIGHT SUMMARY",
        "-" * 60,
        f"Unique airlines: {unique_airline_count:,}",
        f"Unique origin airports: {unique_origin_airport_count:,}",
        (
            "Unique destination airports: "
            f"{unique_destination_airport_count:,}"
        ),
        f"Cancelled flights: {cancelled_flight_count:,}",
        f"Diverted flights: {diverted_flight_count:,}",
        (
            "Flights arriving at least 15 minutes late: "
            f"{delayed_arrival_count:,}"
        ),
        "",
        "OUTPUT FILES",
        "-" * 60,
        f"Missing value report: {MISSING_VALUES_FILE.name}",
        f"Data type report: {DATA_TYPES_FILE.name}",
    ]

    PROFILE_REPORT_FILE.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    print()
    print("\n".join(report_lines))
    print()
    print(f"Profile saved to: {PROFILE_REPORT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()