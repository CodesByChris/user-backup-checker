"""Tests for MailReporter."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
from ubc.user_backup_checker import CONFIG, MailClient, MailReporter, StatusReporter
from .conftest import mock_user


# Test MailReporter.future_recipients
def test_future_recipients(reporter):
    """Tests MailReporter.future_recipients."""
    mail_reporter = MailReporter(reporter, MagicMock(), timedelta(days=5))
    assert mail_reporter.future_recipients == reporter.future_users
    # Note: alphabetic ordering is implicitly also tested (lists).


def test_no_future_recipients(mock_reporter_args):
    """Tests future_recipients when no such users exist whereas others do."""
    mock_reporter_args["users"] = [u for u in mock_reporter_args["users"]
                                   if not u.username.startswith("future_")]
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), MagicMock(), timedelta(days=5))
    assert not mail_reporter.future_recipients


# Test MailReporter.outdated_recipients
def test_outdated_recipients_tolerance_date():
    """Tests whether an outdated user receives the first email on the day right after tolerance."""
    user = mock_user("gets_mail", datetime(2023, 8, 2), is_outdated=True, is_in_future=False)
    tolerance = timedelta(days=5)
    reporter = StatusReporter([user], datetime(2023, 8, 10), tolerance, tolerance, True)
    mail_reporter = MailReporter(reporter, MagicMock(spec=MailClient), tolerance)
    assert mail_reporter.outdated_recipients == [user]


def test_two_outdated_recipients():
    """Tests 2 outdated users & one gets mail, the other not."""
    users = [mock_user("gets_mail", datetime(2023, 8, 2), is_outdated=True, is_in_future=False),
             mock_user("no_mail", datetime(2023, 8, 3), is_outdated=True, is_in_future=False)]
    tolerance = timedelta(days=5)
    reporter = StatusReporter(users, datetime(2023, 8, 17), tolerance, tolerance, True)
    mail_reporter = MailReporter(reporter, MagicMock(spec=MailClient), tolerance)
    assert mail_reporter.outdated_recipients == [users[0]]


def test_no_outdated_recipients(mock_reporter_args):
    """Tests outdated_recipients when no such users exist whereas others do."""
    mock_reporter_args["users"] = [u for u in mock_reporter_args["users"]
                                   if not u.username.startswith("outdated_")]
    tolerance = timedelta(days=5)
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), MagicMock(), tolerance)
    assert not mail_reporter.outdated_recipients


# Test no users
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


# - notify_outdated_recipients():
#     - >1 persons,
#     - no users
#     - Compare produced mails
# - notify_future_recipients():
#     - >1 persons,
#     - no users
#     - Compare produced mail


# - Unify notify_future* and notify_outdated* into combined test functions!
#     - Doesn't work for all tests of the getters! Different logic!
