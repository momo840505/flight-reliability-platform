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

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "interim"
)

VALIDATION_RESULTS_FILE = (
    OUTPUT_DIRECTORY
    / "flights_2024_01_validation_results.csv"
)

VALIDATION_SUMMARY_FILE = (
    OUTPUT_DIRECTORY
    / "flights_2024_01_validation_summary.txt"
)


REQUIRED_COLUMNS = [
    "YEAR",
    "MONTH",
    "DAY_OF_MONTH",
    "FL_DATE",
    "OP_CARRIER_AIRLINE_ID",
    "OP_CARRIER_FL_NUM",
    "ORIGIN_AIRPORT_ID",
    "DEST_AIRPORT_ID",
    "CRS_DEP_TIME",
    "DEP_DELAY_NEW",
    "DEP_DEL15",
    "ARR_DELAY_NEW",
    "ARR_DEL15",
    "CANCELLED",
    "CANCELLATION_CODE",
    "DIVERTED",
    "DISTANCE",
]


FLIGHT_KEY_COLUMNS = [
    "FL_DATE",
    "OP_CARRIER_AIRLINE_ID",
    "OP_CARRIER_FL_NUM",
    "ORIGIN_AIRPORT_ID",
    "DEST_AIRPORT_ID",
    "CRS_DEP_TIME",
]


NON_NEGATIVE_COLUMNS = [
    "DEP_DELAY_NEW",
    "ARR_DELAY_NEW",
    "TAXI_OUT",
    "TAXI_IN",
    "CRS_ELAPSED_TIME",
    "ACTUAL_ELAPSED_TIME",
    "AIR_TIME",
    "DISTANCE",
    "CARRIER_DELAY",
    "WEATHER_DELAY",
    "NAS_DELAY",
    "SECURITY_DELAY",
    "LATE_AIRCRAFT_DELAY",
]


def add_validation_result(
    validation_results: list[dict],
    rule_name: str,
    severity: str,
    failed_row_count: int,
    description: str,
) -> None:
    """Add one validation rule result to the output list."""

    if failed_row_count == 0:
        status = "PASS"
    elif severity == "warning":
        status = "WARNING"
    else:
        status = "FAIL"

    validation_results.append(
        {
            "rule_name": rule_name,
            "severity": severity,
            "status": status,
            "failed_row_count": int(failed_row_count),
            "description": description,
        }
    )


def main() -> None:
    """Validate business and structural rules in the raw dataset."""

    if not RAW_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Raw data file was not found:\n{RAW_DATA_FILE}"
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("BTS RAW DATA QUALITY VALIDATION")
    print("=" * 70)
    print(f"Reading: {RAW_DATA_FILE}")

    flight_data = pd.read_csv(
        RAW_DATA_FILE,
        low_memory=False,
    )

    validation_results = []

    missing_required_columns = sorted(
        set(REQUIRED_COLUMNS)
        - set(flight_data.columns)
    )

    add_validation_result(
        validation_results,
        rule_name="required_columns_present",
        severity="critical",
        failed_row_count=len(missing_required_columns),
        description=(
            "All columns required for the validation process must exist. "
            f"Missing columns: {missing_required_columns}"
        ),
    )

    if missing_required_columns:
        validation_results_table = pd.DataFrame(
            validation_results
        )

        validation_results_table.to_csv(
            VALIDATION_RESULTS_FILE,
            index=False,
        )

        raise ValueError(
            "Validation stopped because required columns are missing."
        )

    flight_dates = pd.to_datetime(
        flight_data["FL_DATE"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce",
    )

    invalid_date_count = int(
        flight_dates.isna().sum()
    )

    add_validation_result(
        validation_results,
        rule_name="valid_flight_dates",
        severity="critical",
        failed_row_count=invalid_date_count,
        description="FL_DATE must contain a valid calendar date.",
    )

    year_mismatch_count = int(
        (
            flight_dates.notna()
            & (
                flight_dates.dt.year
                != flight_data["YEAR"]
            )
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="year_matches_flight_date",
        severity="critical",
        failed_row_count=year_mismatch_count,
        description="YEAR must match the year in FL_DATE.",
    )

    month_mismatch_count = int(
        (
            flight_dates.notna()
            & (
                flight_dates.dt.month
                != flight_data["MONTH"]
            )
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="month_matches_flight_date",
        severity="critical",
        failed_row_count=month_mismatch_count,
        description="MONTH must match the month in FL_DATE.",
    )

    day_mismatch_count = int(
        (
            flight_dates.notna()
            & (
                flight_dates.dt.day
                != flight_data["DAY_OF_MONTH"]
            )
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="day_matches_flight_date",
        severity="critical",
        failed_row_count=day_mismatch_count,
        description=(
            "DAY_OF_MONTH must match the day in FL_DATE."
        ),
    )

    rows_outside_selected_period = int(
        (
            (flight_data["YEAR"] != 2024)
            | (flight_data["MONTH"] != 1)
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="selected_period_is_january_2024",
        severity="critical",
        failed_row_count=rows_outside_selected_period,
        description=(
            "The pilot dataset must contain only January 2024."
        ),
    )

    missing_flight_key_count = int(
        flight_data[
            FLIGHT_KEY_COLUMNS
        ].isna().any(axis=1).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="flight_key_not_missing",
        severity="critical",
        failed_row_count=missing_flight_key_count,
        description=(
            "Columns used to identify a scheduled flight "
            "must not be missing."
        ),
    )

    exact_duplicate_count = int(
        flight_data.duplicated().sum()
    )

    add_validation_result(
        validation_results,
        rule_name="no_exact_duplicate_rows",
        severity="critical",
        failed_row_count=exact_duplicate_count,
        description=(
            "The raw dataset should not contain exact duplicate rows."
        ),
    )

    duplicate_flight_key_count = int(
        flight_data.duplicated(
            subset=FLIGHT_KEY_COLUMNS,
            keep=False,
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="unique_flight_keys",
        severity="critical",
        failed_row_count=duplicate_flight_key_count,
        description=(
            "Each scheduled flight segment should have "
            "a unique flight key."
        ),
    )

    invalid_cancelled_flag_count = int(
        (
            flight_data["CANCELLED"].notna()
            & ~flight_data["CANCELLED"].isin([0, 1])
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="valid_cancelled_indicator",
        severity="critical",
        failed_row_count=invalid_cancelled_flag_count,
        description="CANCELLED must contain only 0 or 1.",
    )

    invalid_diverted_flag_count = int(
        (
            flight_data["DIVERTED"].notna()
            & ~flight_data["DIVERTED"].isin([0, 1])
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="valid_diverted_indicator",
        severity="critical",
        failed_row_count=invalid_diverted_flag_count,
        description="DIVERTED must contain only 0 or 1.",
    )

    negative_value_mask = pd.DataFrame(
        {
            column_name: (
                flight_data[column_name] < 0
            )
            for column_name in NON_NEGATIVE_COLUMNS
        }
    )

    negative_value_count = int(
        negative_value_mask.any(axis=1).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="non_negative_measurements",
        severity="critical",
        failed_row_count=negative_value_count,
        description=(
            "Delay minutes, taxi times, elapsed times, "
            "air time, distance and delay causes "
            "must not be negative."
        ),
    )

    departure_comparison_rows = (
        flight_data["DEP_DELAY_NEW"].notna()
        & flight_data["DEP_DEL15"].notna()
    )

    expected_departure_indicator = (
        flight_data.loc[
            departure_comparison_rows,
            "DEP_DELAY_NEW",
        ]
        >= 15
    ).astype(int)

    departure_indicator_mismatch_count = int(
        (
            expected_departure_indicator
            != flight_data.loc[
                departure_comparison_rows,
                "DEP_DEL15",
            ].astype(int)
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="departure_delay_indicator_consistent",
        severity="critical",
        failed_row_count=departure_indicator_mismatch_count,
        description=(
            "DEP_DEL15 must equal 1 when "
            "DEP_DELAY_NEW is at least 15 minutes."
        ),
    )

    arrival_comparison_rows = (
        flight_data["ARR_DELAY_NEW"].notna()
        & flight_data["ARR_DEL15"].notna()
    )

    expected_arrival_indicator = (
        flight_data.loc[
            arrival_comparison_rows,
            "ARR_DELAY_NEW",
        ]
        >= 15
    ).astype(int)

    arrival_indicator_mismatch_count = int(
        (
            expected_arrival_indicator
            != flight_data.loc[
                arrival_comparison_rows,
                "ARR_DEL15",
            ].astype(int)
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="arrival_delay_indicator_consistent",
        severity="critical",
        failed_row_count=arrival_indicator_mismatch_count,
        description=(
            "ARR_DEL15 must equal 1 when "
            "ARR_DELAY_NEW is at least 15 minutes."
        ),
    )

    cancelled_without_reason_count = int(
        (
            (flight_data["CANCELLED"] == 1)
            & flight_data[
                "CANCELLATION_CODE"
            ].isna()
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="cancelled_flights_have_reason",
        severity="warning",
        failed_row_count=cancelled_without_reason_count,
        description=(
            "Cancelled flights should normally contain "
            "a cancellation reason code."
        ),
    )

    active_flight_with_cancellation_code_count = int(
        (
            (flight_data["CANCELLED"] == 0)
            & flight_data[
                "CANCELLATION_CODE"
            ].notna()
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="active_flights_have_no_cancellation_code",
        severity="warning",
        failed_row_count=(
            active_flight_with_cancellation_code_count
        ),
        description=(
            "Flights that were not cancelled should normally "
            "have no cancellation code."
        ),
    )

    same_origin_destination_count = int(
        (
            flight_data["ORIGIN_AIRPORT_ID"]
            == flight_data["DEST_AIRPORT_ID"]
        ).sum()
    )

    add_validation_result(
        validation_results,
        rule_name="origin_differs_from_destination",
        severity="warning",
        failed_row_count=same_origin_destination_count,
        description=(
            "Origin and destination airports should normally differ."
        ),
    )

    validation_results_table = pd.DataFrame(
        validation_results
    )

    validation_results_table.to_csv(
        VALIDATION_RESULTS_FILE,
        index=False,
    )

    critical_failure_count = int(
        (
            (validation_results_table["severity"] == "critical")
            & (validation_results_table["status"] == "FAIL")
        ).sum()
    )

    warning_count = int(
        (
            validation_results_table["status"]
            == "WARNING"
        ).sum()
    )

    if critical_failure_count > 0:
        overall_status = "FAIL"
    elif warning_count > 0:
        overall_status = "PASS WITH WARNINGS"
    else:
        overall_status = "PASS"

    summary_lines = [
        "BTS RAW DATA QUALITY VALIDATION SUMMARY",
        "=" * 70,
        f"Source file: {RAW_DATA_FILE.name}",
        f"Rows checked: {len(flight_data):,}",
        (
            "Validation rules checked: "
            f"{len(validation_results_table)}"
        ),
        f"Critical rule failures: {critical_failure_count}",
        f"Warnings: {warning_count}",
        f"Overall status: {overall_status}",
        "",
        validation_results_table.to_string(index=False),
    ]

    VALIDATION_SUMMARY_FILE.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    print()
    print(validation_results_table.to_string(index=False))
    print()
    print(f"Overall status: {overall_status}")
    print(
        "Results saved to: "
        f"{VALIDATION_RESULTS_FILE}"
    )
    print(
        "Summary saved to: "
        f"{VALIDATION_SUMMARY_FILE}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()