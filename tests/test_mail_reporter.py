"""Tests for MailReporter."""

from datetime import timedelta
from unittest.mock import MagicMock
from ubc.user_backup_checker import MailReporter


def test_future_recipients(reporter):
    """Tests MailReporter.future_recipients."""
    mail_reporter = MailReporter(reporter, MagicMock(), reminder_interval=timedelta(5))
    assert len(mail_reporter.future_recipients) == 2

    names = {u.username for u in mail_reporter.future_recipients}
    assert names == {"future_1", "future_2"}


# - Test future_recipients():
#     - >1 persons,
#     - no future recipients but others,
#     - no users
# - Test outdated_recipients():
#     - 2 persons & one gets mail, the other not
#     - 2 persons & both get mail
#     - 2 persons & none gets mail
#     - no outdated recipients but others,
#     - no users
# - notify_outdated_recipients():
#     - >1 persons,
#     - no users
#     - Compare produced mails
#     - no users --> test that nothing is sent
# - notify_future_recipients():
#     - >1 persons,
#     - no users
#     - Compare produced mail
#     - no users --> test that nothing is sent


# - Unify notify_future* and notify_outdated* into combined test functions!
#     - Doesn't work for all tests of the getters! Different logic!
