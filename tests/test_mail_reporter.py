"""Tests for MailReporter."""

from datetime import timedelta
from unittest.mock import MagicMock
from ubc.user_backup_checker import CONFIG, MailClient, MailReporter, StatusReporter


def test_future_recipients(reporter):
    """Tests MailReporter.future_recipients."""
    mail_reporter = MailReporter(reporter, MagicMock(), timedelta(5))
    assert len(mail_reporter.future_recipients) == 2

    names = {u.username for u in mail_reporter.future_recipients}
    assert names == {"future_1", "future_2"}


def test_no_future_recipients(mock_reporter_args):
    """Tests future_recipients when no such users exist whereas others do."""
    mock_reporter_args["users"] = [u for u in mock_reporter_args["users"]
                                   if u.username not in {"future_1", "future_2"}]
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), MagicMock(), timedelta(5))
    assert len(mail_reporter.future_recipients) == 0


def test_no_users(mock_reporter_args):
    """Tests MailReporter for an empty user list."""
    mock_reporter_args["users"] = []
    mail_mock = MagicMock(spec=MailClient)
    mail_reporter = MailReporter(StatusReporter(**mock_reporter_args), mail_mock, timedelta(5))

    # Test status detection
    assert len(mail_reporter.future_recipients) == 0
    assert len(mail_reporter.outdated_recipients) == 0

    # Test that no mails are sent
    mail_reporter.notify_future_recipients(CONFIG["SUBJECT_FUTURE"], CONFIG["MAIL_FUTURE"])
    mail_reporter.notify_outdated_recipients(CONFIG["SUBJECT_OUTDATED"], CONFIG["MAIL_OUTDATED"])
    mail_mock.send_email.assert_not_called()
    mail_mock.get_email_address.assert_not_called()


# - Test outdated_recipients():
#     - 2 persons & one gets mail, the other not
#     - 2 persons & both get mail
#     - 2 persons & none gets mail
#     - no outdated recipients but others,
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
