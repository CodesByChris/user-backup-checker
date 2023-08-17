"""Tests for StatusReporter class."""

from textwrap import dedent
from ubc.user_backup_checker import CONFIG, StatusReporter


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
