import pandas as pd

from src.transform.clean_flight_data import extract_hour_from_hhmm


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
