"""
Unit tests for Phase 2 preprocessing and calendar handling.

These tests verify:
- expected annual hourly counts;
- DST handling in Europe/Madrid and Europe/London;
- UTC elapsed-hour preservation;
- boolean metadata normalization.
"""

import pandas as pd

from src.preprocessing.audit_datasets import (
    expected_year_index,
    normalize_boolean,
)


# ============================================================
# ANNUAL CALENDAR TESTS
# ============================================================

def test_2012_leap_year_has_8784_hours():

    index = expected_year_index(
        2012,
        "Europe/Madrid",
    )

    assert len(index) == 8784
    assert index.is_unique


def test_2013_has_8760_hours():

    index = expected_year_index(
        2013,
        "Europe/Madrid",
    )

    assert len(index) == 8760
    assert index.is_unique


def test_2014_has_8760_hours():

    index = expected_year_index(
        2014,
        "Europe/Madrid",
    )

    assert len(index) == 8760
    assert index.is_unique


# ============================================================
# EUROPE/MADRID DST TESTS
# ============================================================

def test_madrid_spring_dst_day_has_23_hours():

    index = expected_year_index(
        2013,
        "Europe/Madrid",
    )

    spring_day = index[
        index.date
        == pd.Timestamp(
            "2013-03-31"
        ).date()
    ]

    assert len(spring_day) == 23


def test_madrid_autumn_dst_day_has_25_hours():

    index = expected_year_index(
        2013,
        "Europe/Madrid",
    )

    autumn_day = index[
        index.date
        == pd.Timestamp(
            "2013-10-27"
        ).date()
    ]

    assert len(autumn_day) == 25


# ============================================================
# EUROPE/LONDON DST TESTS
# ============================================================

def test_london_spring_dst_day_has_23_hours():

    index = expected_year_index(
        2013,
        "Europe/London",
    )

    spring_day = index[
        index.date
        == pd.Timestamp(
            "2013-03-31"
        ).date()
    ]

    assert len(spring_day) == 23


def test_london_autumn_dst_day_has_25_hours():

    index = expected_year_index(
        2013,
        "Europe/London",
    )

    autumn_day = index[
        index.date
        == pd.Timestamp(
            "2013-10-27"
        ).date()
    ]

    assert len(autumn_day) == 25


# ============================================================
# UTC CONVERSION TESTS
# ============================================================

def test_madrid_2013_preserves_8760_elapsed_hours_in_utc():

    local_index = expected_year_index(
        2013,
        "Europe/Madrid",
    )

    utc_index = local_index.tz_convert(
        "UTC"
    )

    assert len(utc_index) == 8760
    assert utc_index.is_unique


def test_london_2013_preserves_8760_elapsed_hours_in_utc():

    local_index = expected_year_index(
        2013,
        "Europe/London",
    )

    utc_index = local_index.tz_convert(
        "UTC"
    )

    assert len(utc_index) == 8760
    assert utc_index.is_unique


# ============================================================
# BOOLEAN METADATA TESTS
# ============================================================

def test_normalize_boolean():

    input_series = pd.Series(
        [
            True,
            False,
            "True",
            "False",
            "1",
            "0",
        ]
    )

    result = normalize_boolean(
        input_series
    )

    expected = [
        True,
        False,
        True,
        False,
        True,
        False,
    ]

    assert result.tolist() == expected


# ============================================================
# CALENDAR BOUNDARY TEST
# ============================================================

def test_2013_madrid_calendar_boundaries():

    index = expected_year_index(
        2013,
        "Europe/Madrid",
    )

    assert (
        index[0]
        == pd.Timestamp(
            "2013-01-01 00:00:00",
            tz="Europe/Madrid",
        )
    )

    assert (
        index[-1]
        == pd.Timestamp(
            "2013-12-31 23:00:00",
            tz="Europe/Madrid",
        )
    )
