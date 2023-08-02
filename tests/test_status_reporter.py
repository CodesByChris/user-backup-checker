"""Tests for StatusReporter class."""

from datetime import datetime, timedelta
from unittest.mock import Mock
from textwrap import dedent
import pytest
from ubc.user_backup_checker import CONFIG, StatusReporter, User


@pytest.fixture
def mock_setup(empty_localuser: User) -> tuple[list[Mock], datetime, timedelta, bool]:
    """Returns a test setup.

    Returns:
        A tuple with the following entries:
        0. users: List of six mock users (2 future, 2 OK, 2 outdated),
        1. reference_date,
        2. tolerance_outdated,
        3. tolerance_future,
        4. exclude_weekends.
    """
    def _mock(name, newest_date, is_outdated, is_future):
        attributes = {"username": name, "newest_date": newest_date, "newest_path": f"/{name}"}
        methods = {"is_in_future.return_value": is_future, "is_outdated.return_value": is_outdated}
        return Mock(spec=empty_localuser, **attributes, **methods)

    reference_date = datetime(2023, 8, 2)
    tolerance = timedelta(days=10)
    users = [
        _mock("future_1",   datetime(2023, 8, 20), is_outdated=False, is_future=True),
        _mock("future_2",   datetime(2030, 1, 1),  is_outdated=False, is_future=True),
        _mock("ok_1",       datetime(2023, 8, 9),  is_outdated=False, is_future=False),
        _mock("ok_2",       datetime(2023, 7, 26), is_outdated=False, is_future=False),
        _mock("outdated_1", datetime(2023, 7, 17), is_outdated=True,  is_future=False),
        _mock("outdated_2", datetime(2000, 1, 1),  is_outdated=True,  is_future=False),
    ]
    return users, reference_date, tolerance, tolerance, True


@pytest.fixture
def reporter(mock_setup: tuple) -> StatusReporter:
    """Returns a reporter for testing."""
    return StatusReporter(*mock_setup)


def test_status_detection(reporter: StatusReporter):
    """Tests whether OK, future, and outdated users are correctly determined."""
    assert len(reporter.future_users) == 2
    assert all(u.username.startswith("future_") for u in reporter.future_users)

    assert len(reporter.ok_users) == 2
    assert all(u.username.startswith("ok_") for u in reporter.ok_users)

    assert len(reporter.outdated_users) == 2
    assert all(u.username.startswith("outdated_") for u in reporter.outdated_users)


def test_report(reporter: StatusReporter):
    """Tests report generation."""
    expected_report = dedent("""
        Outdated users:
        - outdated_1  (2023-07-17)
        - outdated_2  (2000-01-01)


        Users with future files:
        - future_1    (2023-08-20)
        - future_2    (2030-01-01)


        OK users:
        - ok_1        (2023-08-09)
        - ok_2        (2023-07-26)


        For an explanation of each position see the documentation in user_backup_checker.py
    """)
    assert reporter.get_report(CONFIG["ADMIN_STATUS_REPORT"]).strip() == expected_report.strip()
