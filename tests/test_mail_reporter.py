"""Tests for MailReporter."""

from datetime import datetime, timedelta
from functools import partial
from operator import attrgetter
from unittest.mock import call, MagicMock
import pytest
from ubc.user_backup_checker import (CONFIG, MailClient, MailReporter, StatusReporter,
                                     time_difference)
from .conftest import mock_user


# Test recipients
def test_recipients(reporter):
    """Tests MailReporter.future_recipients and MailReporter.outdated_recipients."""
    mail_reporter = MailReporter(reporter, MagicMock(), timedelta(days=5))
    assert mail_reporter.future_recipients == reporter.future_users
    assert mail_reporter.outdated_recipients == [reporter.users[4]]  # only outdated_1 is recipient
    # Note: alphabetic ordering is implicitly also tested (lists).


@pytest.mark.parametrize("_name_start, _get_recipients", [
    ("future_", attrgetter("future_recipients")),
    ("outdated_", attrgetter("outdated_recipients"))
])
def test_no_recipients_but_others(mock_reporter_args, _name_start, _get_recipients):
    """Tests future_recipients or outdated_recipients when none exist whereas other users do."""
    mock_reporter_args["users"] = [u for u in mock_reporter_args["users"]
                                   if not u.username.startswith(_name_start)]
    tolerance = timedelta(days=5)
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), MagicMock(), tolerance)
    assert not _get_recipients(mail_reporter)


# Test user notification
def _make_call_future(user, _, subject, email_template):
    message = email_template.format(path=user.newest_path, date=user.newest_date)
    return call(user, subject, message)


def _make_call_outdated(user, reporter, subject, email_template):
    date = user.newest_date
    n_days = time_difference(date, reporter.reference_date, reporter.exclude_weekends).days
    unit = "weekdays" if reporter.exclude_weekends else "days"
    message = email_template.format(date=date, outdated_days=f"{n_days} {unit}")
    return call(user, subject, message)


@pytest.mark.parametrize("_mode", ["future", "outdated"])
def test_user_notification(reporter, _mode):
    """Tests notify_future_recipients or notify_outdated_recipients."""
    do_future = _mode == "future"
    mail_mock = MagicMock(spec=MailClient)
    mail_reporter = MailReporter(reporter, mail_mock, timedelta(days=5))

    # Notify users
    if do_future:
        subject = CONFIG["SUBJECT_FUTURE"]
        email_template = CONFIG["MAIL_FUTURE"]
        mail_reporter.notify_future_recipients(subject, email_template)
    else:
        subject = CONFIG["SUBJECT_OUTDATED"]
        email_template = CONFIG["MAIL_OUTDATED"]
        mail_reporter.notify_outdated_recipients(subject, email_template)

    # Validate mails
    if do_future:
        make_call = partial(_make_call_future, subject=subject, email_template=email_template)
        recipients = mail_reporter.future_recipients
    else:
        make_call = partial(_make_call_outdated, subject=subject, email_template=email_template)
        recipients = mail_reporter.outdated_recipients

    assert mail_mock.send_email.call_count == len(recipients)
    assert mail_mock.send_email.call_args_list == [make_call(r, reporter) for r in recipients]


def test_email_intervals():
    """Tests whether emails are sent only at the given interval."""
    tolerance = timedelta(days=5)
    reminder_interval = timedelta(days=3)
    user = mock_user("user", datetime(2023, 8, 15), is_outdated=True, is_in_future=False)
    expected_mails = [
        (datetime(2023, 8, 23), True),
        (datetime(2023, 8, 24), False),
        (datetime(2023, 8, 25), False),
        (datetime(2023, 8, 26), False),
        (datetime(2023, 8, 27), False),
        (datetime(2023, 8, 28), True),
        (datetime(2023, 8, 29), False),
        (datetime(2023, 8, 30), False),
        (datetime(2023, 8, 31), True),
    ]
    for date_of_check, is_mail_due in expected_mails:
        reporter = StatusReporter([user], date_of_check, tolerance, tolerance, True)
        mail_reporter = MailReporter(reporter, MagicMock(spec=MailClient), reminder_interval)
        assert (user in mail_reporter.outdated_recipients) == is_mail_due


# Test special cases
def test_outdated_recipients_tolerance_date():
    """Tests whether an outdated user receives the first email on the day right after tolerance."""
    user = mock_user("gets_mail", datetime(2023, 8, 2), is_outdated=True, is_in_future=False)
    tolerance = timedelta(days=5)
    reporter = StatusReporter([user], datetime(2023, 8, 10), tolerance, tolerance, True)
    mail_reporter = MailReporter(reporter, MagicMock(spec=MailClient), tolerance)
    assert mail_reporter.outdated_recipients == [user]


def test_skipping_mails_on_weekends():
    """Tests whether no emails are sent on weekends if CONFIG["EXCLUDE_WEEKENDS"] is True."""

    # Setup
    tolerance = timedelta(days=5)
    reference_date = datetime(2023, 8, 19)
    users = [
        mock_user("outdated_week", datetime(2023, 8, 8), is_outdated=True, is_in_future=False),
        mock_user("outdated_weekend", datetime(2023, 8, 5), is_outdated=True, is_in_future=False),
        mock_user("future", datetime(2023, 8, 30), is_outdated=False, is_in_future=True),
    ]
    reporter = StatusReporter(users, reference_date, tolerance, tolerance, True)
    mail_mock = MagicMock(spec=MailClient)
    mail_reporter = MailReporter(reporter, mail_mock, tolerance)

    # Check no recipients
    assert not mail_reporter.future_recipients
    assert not mail_reporter.outdated_recipients

    # Trigger email functions
    mail_reporter.notify_future_recipients(CONFIG["SUBJECT_FUTURE"], CONFIG["MAIL_FUTURE"])
    mail_reporter.notify_outdated_recipients(CONFIG["SUBJECT_OUTDATED"], CONFIG["MAIL_OUTDATED"])
    mail_mock.send_email.assert_not_called()


def test_no_users(mock_reporter_args):
    """Tests MailReporter for an empty user list."""
    mock_reporter_args["users"] = []
    mail_mock = MagicMock(spec=MailClient)
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), mail_mock, timedelta(days=5))

    # Test status detection
    assert not mail_reporter.future_recipients
    assert not mail_reporter.outdated_recipients

    # Test that no mails are sent
    mail_reporter.notify_future_recipients(CONFIG["SUBJECT_FUTURE"], CONFIG["MAIL_FUTURE"])
    mail_reporter.notify_outdated_recipients(CONFIG["SUBJECT_OUTDATED"], CONFIG["MAIL_OUTDATED"])
    mail_mock.send_email.assert_not_called()
    mail_mock.get_email_address.assert_not_called()
