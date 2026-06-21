from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

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
    / "flights_2024_01_clean_validation_results.csv"
)

VALIDATION_SUMMARY_FILE = (
    OUTPUT_DIRECTORY
    / "flights_2024_01_clean_validation_summary.txt"
)


REQUIRED_COLUMNS = [
    "flight_date",
    "reporting_airline_id",
    "reporting_airline_code",
    "flight_number",
    "origin_airport_id",
    "origin_airport_code",
    "destination_airport_id",
    "destination_airport_code",
    "scheduled_departure_time",
    "arrival_delayed_15",
    "cancelled",
    "diverted",
    "flight_status",
    "arrival_on_time",
    "route_code",
    "is_weekend",
    "scheduled_departure_hour",
    "scheduled_arrival_hour",
    "delay_cause_reported",
    "total_reported_delay_minutes",
]


FLIGHT_KEY_COLUMNS = [
    "flight_date",
    "reporting_airline_id",
    "flight_number",
    "origin_airport_id",
    "destination_airport_id",
    "scheduled_departure_time",
]


DELAY_CAUSE_COLUMNS = [
    "carrier_delay_minutes",
    "weather_delay_minutes",
    "national_air_system_delay_minutes",
    "security_delay_minutes",
    "late_aircraft_delay_minutes",
]


NON_NEGATIVE_COLUMNS = [
    "departure_delay_minutes",
    "arrival_delay_minutes",
    "taxi_out_minutes",
    "taxi_in_minutes",
    "scheduled_elapsed_minutes",
    "actual_elapsed_minutes",
    "air_time_minutes",
    "distance_miles",
    "carrier_delay_minutes",
    "weather_delay_minutes",
    "national_air_system_delay_minutes",
    "security_delay_minutes",
    "late_aircraft_delay_minutes",
    "total_reported_delay_minutes",
]


def count_true(condition: pd.Series) -> int:
    """Count True values while treating missing values as False."""

    return int(
        condition
        .fillna(False)
        .sum()
    )


def add_result(
    validation_results: list[dict],
    rule_name: str,
    failed_row_count: int,
    description: str,
) -> None:
    """Store one validation result."""

    status = (
        "PASS"
        if failed_row_count == 0
        else "FAIL"
    )

    validation_results.append(
        {
            "rule_name": rule_name,
            "status": status,
            "failed_row_count": int(failed_row_count),
            "description": description,
        }
    )


def main() -> None:
    """Validate the cleaned Parquet flight dataset."""

    if not CLEAN_DATA_FILE.exists():
        raise FileNotFoundError(
            f"Clean data file was not found:\n{CLEAN_DATA_FILE}"
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("BTS CLEAN FLIGHT DATA VALIDATION")
    print("=" * 70)
    print(f"Reading: {CLEAN_DATA_FILE}")

    flight_data = pd.read_parquet(
        CLEAN_DATA_FILE
    )

    validation_results = []

    missing_required_columns = sorted(
        set(REQUIRED_COLUMNS)
        - set(flight_data.columns)
    )

    add_result(
        validation_results,
        rule_name="required_columns_present",
        failed_row_count=len(missing_required_columns),
        description=(
            "All required cleaned and derived columns must exist. "
            f"Missing columns: {missing_required_columns}"
        ),
    )

    if missing_required_columns:
        pd.DataFrame(
            validation_results
        ).to_csv(
            VALIDATION_RESULTS_FILE,
            index=False,
        )

        raise ValueError(
            "Validation stopped because required columns are missing."
        )

    empty_dataset_count = int(
        len(flight_data) == 0
    )

    add_result(
        validation_results,
        rule_name="dataset_is_not_empty",
        failed_row_count=empty_dataset_count,
        description="The cleaned dataset must contain flight records.",
    )

    invalid_date_count = int(
        flight_data["flight_date"]
        .isna()
        .sum()
    )

    add_result(
        validation_results,
        rule_name="flight_date_not_missing",
        failed_row_count=invalid_date_count,
        description="Cleaned flight dates must not be missing.",
    )

    rows_outside_january_2024 = count_true(
        (
            flight_data["flight_date"].dt.year != 2024
        )
        |
        (
            flight_data["flight_date"].dt.month != 1
        )
    )

    add_result(
        validation_results,
        rule_name="date_period_is_january_2024",
        failed_row_count=rows_outside_january_2024,
        description=(
            "The pilot dataset must contain only January 2024."
        ),
    )

    missing_flight_key_count = int(
        flight_data[
            FLIGHT_KEY_COLUMNS
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    add_result(
        validation_results,
        rule_name="flight_key_not_missing",
        failed_row_count=missing_flight_key_count,
        description=(
            "All cleaned flight-key fields must be present."
        ),
    )

    duplicate_flight_key_count = int(
        flight_data.duplicated(
            subset=FLIGHT_KEY_COLUMNS,
            keep=False,
        ).sum()
    )

    add_result(
        validation_results,
        rule_name="flight_key_is_unique",
        failed_row_count=duplicate_flight_key_count,
        description=(
            "Each scheduled flight segment must have "
            "a unique flight key."
        ),
    )

    invalid_status_count = count_true(
        ~flight_data["flight_status"].isin(
            [
                "Completed",
                "Cancelled",
                "Diverted",
            ]
        )
    )

    add_result(
        validation_results,
        rule_name="flight_status_is_valid",
        failed_row_count=invalid_status_count,
        description=(
            "Flight status must be Completed, Cancelled or Diverted."
        ),
    )

    both_cancelled_and_diverted_count = count_true(
        (flight_data["cancelled"] == 1)
        & (flight_data["diverted"] == 1)
    )

    add_result(
        validation_results,
        rule_name="flight_not_cancelled_and_diverted",
        failed_row_count=both_cancelled_and_diverted_count,
        description=(
            "A flight must not be marked as both cancelled and diverted."
        ),
    )

    expected_status = pd.Series(
        "Completed",
        index=flight_data.index,
        dtype="string",
    )

    expected_status.loc[
        flight_data["diverted"] == 1
    ] = "Diverted"

    expected_status.loc[
        flight_data["cancelled"] == 1
    ] = "Cancelled"

    status_mismatch_count = int(
        (
            flight_data["flight_status"]
            .fillna("<MISSING>")
            != expected_status
        ).sum()
    )

    add_result(
        validation_results,
        rule_name="flight_status_matches_indicators",
        failed_row_count=status_mismatch_count,
        description=(
            "Flight status must agree with cancelled "
            "and diverted indicators."
        ),
    )

    expected_arrival_on_time = pd.Series(
        pd.NA,
        index=flight_data.index,
        dtype="boolean",
    )

    completed_rows = (
        flight_data["flight_status"]
        == "Completed"
    )

    completed_rows_with_arrival_result = (
        completed_rows
        & flight_data[
            "arrival_delayed_15"
        ].notna()
    )

    expected_arrival_on_time.loc[
        completed_rows_with_arrival_result
    ] = (
        flight_data.loc[
            completed_rows_with_arrival_result,
            "arrival_delayed_15",
        ]
        == 0
    )

    actual_arrival_values = (
        flight_data["arrival_on_time"]
        .astype("string")
        .fillna("<NA>")
    )

    expected_arrival_values = (
        expected_arrival_on_time
        .astype("string")
        .fillna("<NA>")
    )

    arrival_status_mismatch_count = int(
        (
            actual_arrival_values
            != expected_arrival_values
        ).sum()
    )

    add_result(
        validation_results,
        rule_name="arrival_on_time_is_consistent",
        failed_row_count=arrival_status_mismatch_count,
        description=(
            "arrival_on_time must match arrival_delayed_15 "
            "for completed flights."
        ),
    )

    expected_route_code = (
        flight_data["origin_airport_code"]
        .astype("string")
        + "-"
        + flight_data[
            "destination_airport_code"
        ].astype("string")
    )

    route_code_mismatch_count = int(
        (
            flight_data["route_code"]
            .fillna("<MISSING>")
            != expected_route_code
            .fillna("<MISSING>")
        ).sum()
    )

    add_result(
        validation_results,
        rule_name="route_code_is_consistent",
        failed_row_count=route_code_mismatch_count,
        description=(
            "route_code must equal origin code plus destination code."
        ),
    )

    expected_weekend = (
        flight_data["day_of_week"]
        .isin([6, 7])
    )

    weekend_mismatch_count = int(
        (
            flight_data["is_weekend"]
            .astype("boolean")
            .astype("string")
            != expected_weekend
            .astype("boolean")
            .astype("string")
        ).sum()
    )

    add_result(
        validation_results,
        rule_name="weekend_indicator_is_consistent",
        failed_row_count=weekend_mismatch_count,
        description=(
            "Saturday and Sunday must be marked as weekend."
        ),
    )

    invalid_departure_hour_count = count_true(
        flight_data[
            "scheduled_departure_hour"
        ].notna()
        & ~flight_data[
            "scheduled_departure_hour"
        ].between(0, 23)
    )

    add_result(
        validation_results,
        rule_name="scheduled_departure_hour_is_valid",
        failed_row_count=invalid_departure_hour_count,
        description=(
            "Scheduled departure hour must be between 0 and 23."
        ),
    )

    invalid_arrival_hour_count = count_true(
        flight_data[
            "scheduled_arrival_hour"
        ].notna()
        & ~flight_data[
            "scheduled_arrival_hour"
        ].between(0, 23)
    )

    add_result(
        validation_results,
        rule_name="scheduled_arrival_hour_is_valid",
        failed_row_count=invalid_arrival_hour_count,
        description=(
            "Scheduled arrival hour must be between 0 and 23."
        ),
    )

    negative_measurement_count = int(
        (
            flight_data[
                NON_NEGATIVE_COLUMNS
            ] < 0
        )
        .any(axis=1)
        .sum()
    )

    add_result(
        validation_results,
        rule_name="measurements_are_non_negative",
        failed_row_count=negative_measurement_count,
        description=(
            "Unsigned delay, taxi, elapsed, distance "
            "and delay-cause values must not be negative."
        ),
    )

    expected_total_delay = (
        flight_data[
            DELAY_CAUSE_COLUMNS
        ]
        .sum(axis=1)
    )

    total_delay_difference = (
        flight_data[
            "total_reported_delay_minutes"
        ]
        - expected_total_delay
    ).abs()

    total_delay_mismatch_count = count_true(
        total_delay_difference > 0.01
    )

    add_result(
        validation_results,
        rule_name="total_reported_delay_is_consistent",
        failed_row_count=total_delay_mismatch_count,
        description=(
            "Total reported delay must equal the sum "
            "of all five delay-cause fields."
        ),
    )

    unreported_delay_with_nonzero_total_count = count_true(
        (
            flight_data[
                "delay_cause_reported"
            ] == False
        )
        & (
            flight_data[
                "total_reported_delay_minutes"
            ] != 0
        )
    )

    add_result(
        validation_results,
        rule_name="unreported_delay_has_zero_total",
        failed_row_count=(
            unreported_delay_with_nonzero_total_count
        ),
        description=(
            "Rows without reported delay causes "
            "must have a zero reported-delay total."
        ),
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
        "BTS CLEAN FLIGHT DATA VALIDATION SUMMARY",
        "=" * 70,
        f"Source file: {CLEAN_DATA_FILE.name}",
        f"Rows checked: {len(flight_data):,}",
        f"Columns checked: {len(flight_data.columns)}",
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

    print()
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