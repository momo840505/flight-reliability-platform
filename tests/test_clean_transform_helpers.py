import pandas as pd
import pytest

from src.transform.clean_flight_data import (
    COLUMN_RENAME_MAP,
    clean_flight_dataframe,
    extract_hour_from_hhmm,
)


def test_extract_hour_from_hhmm_handles_standard_values() -> None:
    values = pd.Series([5, 59, 100, 930, 2359])

    result = extract_hour_from_hhmm(values)

    assert result.tolist() == [0, 0, 1, 9, 23]


def test_extract_hour_from_hhmm_wraps_2400_and_preserves_missing() -> None:
    values = pd.Series([2400, 2460, None, "bad"])

    result = extract_hour_from_hhmm(values)

    assert result.iloc[0] == 0
    assert result.iloc[1] == 0
    assert pd.isna(result.iloc[2])
    assert pd.isna(result.iloc[3])


# ---------------------------------------------------------------------------
# clean_flight_dataframe()
#
# These build a tiny synthetic DataFrame using the *raw* BTS column names
# (the left-hand side of COLUMN_RENAME_MAP), matching the shape of the real
# flights_2024_01.csv file, so the tests exercise the exact same code path
# as main() does -- just without needing the real ~500k-row file on disk.
# ---------------------------------------------------------------------------

RAW_COLUMNS = list(COLUMN_RENAME_MAP.keys())


def make_raw_flight_row(**overrides) -> dict:
    """A single valid, fully-populated raw BTS flight record.

    Every field individual tests care about can be overridden by keyword;
    everything else is a plausible default so the row passes the
    data-quality guardrails (valid date, complete flight key) unless a
    test is specifically exercising one of those guardrails.
    """

    base = dict(
        YEAR=2024,
        QUARTER=1,
        MONTH=1,
        DAY_OF_MONTH=1,
        DAY_OF_WEEK=1,  # Monday
        FL_DATE="01/01/2024 12:00:00 AM",
        OP_UNIQUE_CARRIER="AA",
        OP_CARRIER_AIRLINE_ID=19805,
        TAIL_NUM="N123AA",
        OP_CARRIER_FL_NUM=100,
        ORIGIN_AIRPORT_ID=12478,
        ORIGIN="JFK",
        ORIGIN_CITY_NAME="New York, NY",
        ORIGIN_STATE_ABR="NY",
        ORIGIN_STATE_NM="New York",
        DEST_AIRPORT_ID=12892,
        DEST="LAX",
        DEST_CITY_NAME="Los Angeles, CA",
        DEST_STATE_ABR="CA",
        DEST_STATE_NM="California",
        CRS_DEP_TIME=800,
        DEP_TIME=805,
        DEP_DELAY=5,
        DEP_DELAY_NEW=5,
        DEP_DEL15=0,
        DEP_TIME_BLK="0800-0859",
        TAXI_OUT=15,
        TAXI_IN=8,
        CRS_ARR_TIME=1100,
        ARR_TIME=1058,
        ARR_DELAY=-2,
        ARR_DELAY_NEW=0,
        ARR_DEL15=0,
        ARR_TIME_BLK="1100-1159",
        CANCELLED=0,
        CANCELLATION_CODE=None,
        DIVERTED=0,
        CRS_ELAPSED_TIME=300,
        ACTUAL_ELAPSED_TIME=293,
        AIR_TIME=270,
        FLIGHTS=1,
        DISTANCE=2475,
        DISTANCE_GROUP=10,
        CARRIER_DELAY=None,
        WEATHER_DELAY=None,
        NAS_DELAY=None,
        SECURITY_DELAY=None,
        LATE_AIRCRAFT_DELAY=None,
    )
    base.update(overrides)
    return base


def make_raw_flight_data(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)[RAW_COLUMNS]


def test_route_code_and_hour_extraction() -> None:
    raw = make_raw_flight_data([make_raw_flight_row()])

    cleaned = clean_flight_dataframe(raw)

    row = cleaned.iloc[0]
    assert row["route_code"] == "JFK-LAX"
    assert row["scheduled_departure_hour"] == 8
    assert row["scheduled_arrival_hour"] == 11


def test_is_weekend_flag() -> None:
    raw = make_raw_flight_data(
        [
            make_raw_flight_row(OP_CARRIER_FL_NUM=1, DAY_OF_WEEK=1),  # Mon
            make_raw_flight_row(OP_CARRIER_FL_NUM=2, DAY_OF_WEEK=6),  # Sat
            make_raw_flight_row(OP_CARRIER_FL_NUM=3, DAY_OF_WEEK=7),  # Sun
        ]
    )

    cleaned = clean_flight_dataframe(raw)
    by_flight = cleaned.set_index("flight_number")

    assert by_flight.loc[1, "is_weekend"] == False
    assert by_flight.loc[2, "is_weekend"] == True
    assert by_flight.loc[3, "is_weekend"] == True


def test_flight_status_transitions() -> None:
    raw = make_raw_flight_data(
        [
            make_raw_flight_row(OP_CARRIER_FL_NUM=1),  # normal -> Completed
            make_raw_flight_row(
                OP_CARRIER_FL_NUM=2, CANCELLED=1, ARR_DEL15=None, DEP_DEL15=None
            ),
            make_raw_flight_row(OP_CARRIER_FL_NUM=3, DIVERTED=1, ARR_DEL15=None),
        ]
    )

    cleaned = clean_flight_dataframe(raw)
    by_flight = cleaned.set_index("flight_number")

    assert by_flight.loc[1, "flight_status"] == "Completed"
    assert by_flight.loc[2, "flight_status"] == "Cancelled"
    assert by_flight.loc[3, "flight_status"] == "Diverted"


def test_cancelled_takes_priority_over_diverted() -> None:
    """A row flagged both DIVERTED=1 and CANCELLED=1 is an edge case the
    BTS data can technically contain. The original inlined logic applied
    the diverted assignment first and the cancelled assignment second, so
    cancelled wins -- this test locks in that same precedence for the
    refactor."""

    raw = make_raw_flight_data(
        [
            make_raw_flight_row(
                OP_CARRIER_FL_NUM=1,
                CANCELLED=1,
                DIVERTED=1,
                ARR_DEL15=None,
                DEP_DEL15=None,
            )
        ]
    )

    cleaned = clean_flight_dataframe(raw)

    assert cleaned.iloc[0]["flight_status"] == "Cancelled"


def test_arrival_on_time_only_set_for_completed_flights_with_known_delay() -> None:
    raw = make_raw_flight_data(
        [
            make_raw_flight_row(OP_CARRIER_FL_NUM=1, ARR_DEL15=0),  # on time
            make_raw_flight_row(OP_CARRIER_FL_NUM=2, ARR_DEL15=1),  # delayed
            make_raw_flight_row(
                OP_CARRIER_FL_NUM=3, CANCELLED=1, ARR_DEL15=None, DEP_DEL15=None
            ),  # not completed -> unknown
        ]
    )

    cleaned = clean_flight_dataframe(raw)
    by_flight = cleaned.set_index("flight_number")

    assert by_flight.loc[1, "arrival_on_time"] == True
    assert by_flight.loc[2, "arrival_on_time"] == False
    assert pd.isna(by_flight.loc[3, "arrival_on_time"])


def test_delay_cause_reported_and_total_minutes() -> None:
    raw = make_raw_flight_data(
        [
            make_raw_flight_row(OP_CARRIER_FL_NUM=1),  # no delay causes reported
            make_raw_flight_row(
                OP_CARRIER_FL_NUM=2,
                CARRIER_DELAY=10,
                WEATHER_DELAY=0,
                NAS_DELAY=5,
            ),
        ]
    )

    cleaned = clean_flight_dataframe(raw)
    by_flight = cleaned.set_index("flight_number")

    assert by_flight.loc[1, "delay_cause_reported"] == False
    assert by_flight.loc[1, "total_reported_delay_minutes"] == 0.0

    assert by_flight.loc[2, "delay_cause_reported"] == True
    assert by_flight.loc[2, "total_reported_delay_minutes"] == 15.0


def test_exact_duplicate_rows_are_removed_and_counted() -> None:
    """Regression test for a refactor bug: exact_duplicate_count must be
    computed on the fully prepared (renamed, date-parsed, string-cleaned,
    type-cast) DataFrame -- the same point the original inlined logic
    computed it, right before drop_duplicates() -- never on the raw,
    untyped input. A count taken from the raw frame is not equivalent and
    silently reports the wrong number."""

    unique_row = make_raw_flight_row(OP_CARRIER_FL_NUM=1)
    other_row = make_raw_flight_row(OP_CARRIER_FL_NUM=2, TAIL_NUM="N456AA")
    raw = make_raw_flight_data([unique_row, dict(unique_row), other_row])

    cleaned = clean_flight_dataframe(raw)

    assert cleaned.attrs["exact_duplicate_count"] == 1
    assert len(cleaned) == 2
    assert sorted(cleaned["flight_number"].tolist()) == [1, 2]


def test_missing_source_columns_raise_value_error() -> None:
    raw = make_raw_flight_data([make_raw_flight_row()]).drop(columns=["TAIL_NUM"])

    with pytest.raises(ValueError, match="source columns are missing"):
        clean_flight_dataframe(raw)


def test_invalid_flight_date_raises_value_error() -> None:
    raw = make_raw_flight_data([make_raw_flight_row(FL_DATE="not-a-date")])

    with pytest.raises(ValueError, match="invalid flight dates"):
        clean_flight_dataframe(raw)


def test_missing_flight_key_value_raises_value_error() -> None:
    raw = make_raw_flight_data(
        [make_raw_flight_row(ORIGIN_AIRPORT_ID=None)]
    )

    with pytest.raises(ValueError, match="missing flight key values"):
        clean_flight_dataframe(raw)


def test_blank_strings_become_missing() -> None:
    raw = make_raw_flight_data(
        [make_raw_flight_row(CANCELLATION_CODE="   ")]
    )

    cleaned = clean_flight_dataframe(raw)

    assert pd.isna(cleaned.iloc[0]["cancellation_code"])
