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

