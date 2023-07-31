"""Tests for time-based library functions in user_backup_checker.py"""

from datetime import datetime, timedelta
from ubc.user_backup_checker import _round_to_monday, time_difference


def test_round_to_monday():
    """Test _round_to_monday."""
    assert _round_to_monday(datetime(2019, 1, 1)) == datetime(2019, 1, 7, 0, 0, 0)
    assert _round_to_monday(datetime(2019, 1, 2)) == datetime(2019, 1, 7, 0, 0, 0)
    assert _round_to_monday(datetime(2019, 1, 7)) == datetime(2019, 1, 14, 0, 0, 0)


def test_time_difference():
    """Test time_difference."""

    # Regular case
    date_1 = datetime(2019, 1, 1)
    date_2 = datetime(2019, 1, 8)
    assert time_difference(date_1, date_2, False) == timedelta(days=7)
    assert time_difference(date_1, date_2, True) == timedelta(days=5)

    # Regular case, negative
    assert time_difference(date_2, date_1, False) == timedelta(days=-7)
    assert time_difference(date_2, date_1, True) == timedelta(days=-5)

    # Same point in time
    assert time_difference(date_1, date_1, False) == timedelta(0)
    assert time_difference(date_1, date_1, True) == timedelta(0)

    # Difference also in the seconds
    date_3 = datetime(2018, 12, 31, 23, 59, 59)
    assert time_difference(date_3, date_2, False) == timedelta(days=7, seconds=1)
    assert time_difference(date_3, date_2, True) == timedelta(days=5, seconds=1)

    # From weekend to (same) weekend
    date_4 = datetime(2019, 1, 5)
    date_5 = datetime(2019, 1, 6)
    assert time_difference(date_4, date_5, False) == timedelta(days=1)
    assert time_difference(date_4, date_5, True) == timedelta(0)

    # From weekend to non-weekend
    date_6 = datetime(2019, 1, 7, 0, 0, 1)
    assert time_difference(date_4, date_6, False) == timedelta(days=2, seconds=1)
    assert time_difference(date_4, date_6, True) == timedelta(seconds=1)
