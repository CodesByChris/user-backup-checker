"""Tests for StatusReporter class."""

from datetime import datetime, timedelta
from unittest.mock import Mock
import pytest
from ubc.user_backup_checker import StatusReporter


@pytest.fixture
def mock_setup(empty_localuser) -> tuple[list[Mock], datetime, timedelta, bool]:
    """Returns a test setup.

    Returns:
        A tuple with the following entries:
        0. Six mock users (2 future, 2 OK, 2 outdated),
        1. reference_date,
        2. tolerance (use this value for outdated and future),
        3. exclude_weekends.
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
    return users, reference_date, tolerance, True


def test_status_detection(mock_setup):
    """Tests whether OK, future, and outdated users are correctly determined."""
    users, reference_date, tolerance, exclude_weekends = mock_setup
    reporter = StatusReporter(users, reference_date, tolerance, tolerance, exclude_weekends)

    assert len(reporter.future_users) == 2
    assert all(u.username.startswith("future_") for u in reporter.future_users)

    assert len(reporter.ok_users) == 2
    assert all(u.username.startswith("ok_") for u in reporter.ok_users)

    assert len(reporter.outdated_users) == 2
    assert all(u.username.startswith("outdated_") for u in reporter.outdated_users)
