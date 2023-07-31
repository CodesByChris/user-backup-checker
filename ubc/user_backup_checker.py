"""Scan a Synology server for interrupted user backups performed with Synology Drive.

The validation has three steps:
1. Compile a list of users on the Synology.
2. Determine the most recent modification date among the files in each user's backup directory.
3. For each user, determine whether this date lies within a given number of days in the past.

(Optional) Sending automated emails to affected users. To enable this:
1. Implement `MailClient` (see below). For most Synology setups, this likely means to connect via
   SMTP to an external email address, which user_backup_checker.py can use to send the emails to
   individual users. See also the following Python modules:
   - [`smtplib`](https://docs.python.org/3/library/smtplib.html)
   - [`email`](https://docs.python.org/3/library/email.html)
2. Call main() with an instance of your `MailClient` (sub-)class for the argument `mail_client`.

Exit codes:
    0: Validation completed successfully.
    2: No user found on Synology.
"""

from typing import Optional
from logging import getLogger, WARNING
from logging.handlers import QueueHandler
from datetime import datetime, timedelta
from glob import glob
from os import path, stat, walk
from queue import Queue
from textwrap import dedent
from pathlib import Path
import sys


logger = getLogger(__name__)


# Settings
USERS_TO_EXCLUDE = set()  # usernames to skip
USER_DETECTION_LOOKUPS = {
    "local": {"home_dirs_glob": "/volume1/homes/[!@.]*/", "backup_subdir": "Drive/Backup/"},
    "domain": {"home_dirs_glob": "/volume1/homes/@DH-D/*/*/", "backup_subdir": "Drive/Backup/"},
    # For naming and location of home directories of domain users see:
    #     https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/file_directory_service_user_group?version=7
    # The example above assumes the domain D, hence "@DH-D".
}
EXCLUDE_WEEKENDS = True  # whether Saturdays and Sundays are not counted towards outdated days
TOLERANCE_FUTURE = timedelta(days=1)  # Timespan for future files
TOLERANCE_OUTDATED = timedelta(days=5)  # Timespan for outdated backups

# Settings for individual user emails
REMINDER_INTERVAL = timedelta(days=5)  # Interval for reminder emails after the initial email


# Mail Templates
SUBJECT_OUTDATED = "Outdated backup"
MAIL_OUTDATED = dedent("""
    Dear user,

    Your backup is outdated.

    - Date of last backup:  {date_last_backup}  ({outdated_days} outdated)

    Best regards,
    user_backup_checker.py
""")

SUBJECT_FUTURE = "Non-verifiable backup"
MAIL_FUTURE = dedent("""
    Dear user,

    Your backup contains at least one file whose modification time lies in the future.

    - File:               {path}
    - Modification Time:  {date}

    Because of this file, your backup cannot be validated correctly.

    Best regards,
    user_backup_checker.py
""")

ADMIN_STATUS_REPORT = dedent("""
    Outdated users:
    {outdated_users}


    Users with future files:
    {future_users}


    OK users:
    {ok_users}


    For an explanation of each position see the documentation in user_backup_checker.py

""")


# Time Handling
def _round_to_monday(date: datetime) -> datetime:
    """Rounds date to the *next* Monday at 00:00 o'clock.

    Example:
        >>> # Round Tuesday, 1. January 2019 to Monday, 7. January 2019
        >>> _round_to_monday(datetime(2019, 1, 1))
        datetime(2019, 1, 7, 0, 0)
    """

    # Shift to next Monday
    date += timedelta(days=1)
    while date.isoweekday() != 1:
        date += timedelta(days=1)

    # Shift to midnight
    date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    return date


def time_difference(date_1: datetime, date_2: datetime,
                    exclude_weekends: bool = EXCLUDE_WEEKENDS) -> timedelta:
    """Computes the time difference from date_1 to date_2.

    The difference is positive if date_1 <= date_2 and negative otherwise.

    This function essentially does the same as numpy.busday_count. However, numpy is not part of
    Synology's Python package, and therefore is not used here.

    Args:
        date_1: First point in time.
        date_2: Second point in time.
        exclude_weekends: If True, weekends are omitted in the time-difference computation. If True
            and date_1 or date_2 fall on a weekend, they are rounded to the next Monday, 00:00
            o'clock.

    Returns:
        Computed time difference.
    """

    # Ensure date_1 <= date_2
    if date_1 > date_2:
        return -time_difference(date_1=date_2, date_2=date_1, exclude_weekends=exclude_weekends)

    # Handle times on weekends
    if exclude_weekends and date_1.isoweekday() in {6, 7}:
        date_1 = _round_to_monday(date_1)
    if exclude_weekends and date_2.isoweekday() in {6, 7}:
        date_2 = _round_to_monday(date_2)

    # Compute difference
    day_difference = 0
    while date_1 < date_2:
        if not exclude_weekends or date_1.isoweekday() not in {6, 7}:
            day_difference += 1
        date_1 += timedelta(days=1)
    return (date_2 - date_1) + timedelta(days=day_difference)


# User Class
class User:
    """Collects information about a user on the Synology server."""

    def __init__(self, username: str, dir_backup: Path):
        """
        Raises:
            FileNotFoundError: If the backup directory does not exist.
        """
        self.username = username
        self.dir_backup = dir_backup
        if not dir_backup.is_dir():
            raise FileNotFoundError(f"Backup dir not found (user '{username}'): '{dir_backup}'")
        self._init_newest_file_and_date(dir_backup)

    def is_outdated(self, reference_date: datetime, tolerance: timedelta) -> bool:
        """Determines whether the user has an outdated backup.

        This function essentially computes
            self.newest_date < reference_date - tolerance
        but may also exclude weekends depending on the arguments.

        Args:
            reference_date: Timestamp compared to which the user's backup shall be outdated. To use
                today as the value, use datetime.now().
            tolerance: Tolerance period in which the most recent backup must have occurred to not be
                outdated.

        Returns:
            True if the user's backup is outdated.
        """
        # TODO: Argument to include weekends

        return time_difference(self.newest_date, reference_date) > tolerance

    def is_in_future(self, reference_date: datetime, tolerance: timedelta) -> bool:
        """Determines whether the user has a file with a timestamp in the future.

        This function essentially computes
            self.newest_date > reference_date + tolerance
        but may also exclude weekends depending on the arguments.

        Args:
            reference_date: Timestamp compared to which the user's backup shall be outdated. To use
                today as the value, use datetime.now().
            tolerance: Tolerance period in which the user's newest date is allowed to occur while
                is_in_future still returns False.

        Returns:
            True if the user's backup has a file with a future timestamp.
        """
        # TODO: Argument to include weekends

        return time_difference(reference_date, self.newest_date) > tolerance

    def _init_newest_file_and_date(self, dir_base: Path):
        """Determines the most recent file in dir_base and subtrees and stores its path and date.

        The most recent file is the file with the newest modification timestamp. Note that this
        timestamp may lie in the future.

        If the directory is altered while get_newest_update runs, datetime.now() is returned
        immediately.

        Args:
            dir_base: Root of the folder-subtree to examine.
        """
        self.newest_path = None
        self.newest_date = None
        for sub_root, _, files in walk(dir_base):
            for file in files:
                file_path = path.join(dir_base, sub_root, file)
                try:
                    file_date = stat(file_path, follow_symlinks=False).st_mtime
                    file_date = datetime.fromtimestamp(file_date)
                except FileNotFoundError:
                    # File has been deleted in the meantime, i.e. was updated just now.
                    self.newest_path = file_path
                    self.newest_date = datetime.now()
                    return
                if self.newest_date is None or file_date > self.newest_date:
                    self.newest_path = file_path
                    self.newest_date = file_date


def user_factory(user_detection_lookups: dict, usernames_to_exclude: set[str]) -> list[User]:
    """Collects all users and their backup state on the Synology server.

    Args:
        user_detection_lookups: Lookup for different locations where the Synology stores home
            directories. Typically, this value is USER_DETECTION_LOOKUPS.
        usernames_to_exclude: Exclude users in this list. Typically, this value is USERS_TO_EXCLUDE.

    Returns:
        The collected users.
    """
    users = {}
    for lookup in user_detection_lookups.values():
        # Collect all home directories
        home_dirs = glob(lookup["home_dirs_glob"])
        home_dirs = [Path(home_dir) for home_dir in home_dirs if path.isdir(home_dir)]

        # Create users
        for home_dir in home_dirs:
            name = home_dir.name  # last component of path
            if name in usernames_to_exclude:
                continue
            if name in users:
                raise RuntimeError(f"More than one user has name: {name}")
            try:
                user = User(name, dir_backup=home_dir / Path(lookup["backup_subdir"]))
            except FileNotFoundError as error:
                logger.warning(str(error))
            users[name] = user
    return list(users.values())


# Reporting
class StatusReporter:
    """Reporter for status messages of users with OK, outdated, and future backups."""

    def __init__(self, users: list[User], reference_date: datetime,
                 tolerance_outdated: timedelta, tolerance_future: timedelta):
        """Initializes reporter.

        Args:
            users: Users that shall be included in the status report.
            reference_date: Timestamp compared to which the user's backup shall be outdated or
                future. To use today as the value, use datetime.now().
            tolerance_outdated: Tolerance period in which the most recent backup must have occurred
                to not be outdated.
            tolerance_future: Tolerance period in which the user's newest date is allowed to occur
                while is_in_future still returns False.
        """
        # Store args
        self.users = users.copy()
        self.tolerance_outdated = tolerance_outdated
        self.tolerance_future = tolerance_future
        self.reference_date = reference_date

        # Group users by backup status
        future_users = {u for u in users if u.is_in_future(reference_date, tolerance_future)}
        outdated_users = {u for u in users if u.is_outdated(reference_date, tolerance_outdated)}
        ok_users = {u for u in users if u not in outdated_users | future_users}

        self._issue_index = {
            "future_users": sorted(future_users, key=lambda u: u.username),
            "outdated_users": sorted(outdated_users, key=lambda u: u.username),
            "ok_users": sorted(ok_users, key=lambda u: u.username),
        }

    def get_report(self, message_template: str) -> str:
        """Status report of users with OK, outdated, and future backups.

        Args:
            message_template: Template of the status report. It has to contain the following
                substrings that are replaced with the respective user statuses:
                - {ok_users} (users without problems).
                - {future_users} (users with future-dated files in their backups).
                - {outdated_users} (users with outdated backups).

        Returns:
            The status report.
        """
        width_usernames = max(len(u.username) for u in self.users)
        row = f"- {{name:{width_usernames}}}  ({{date:%Y-%m-%d}})"

        replacements = {}
        for issue_type, issue_users in self._issue_index.items():
            rows = [row.format(name=u.username, date=u.newest_date) for u in issue_users]
            if not rows:
                # No user has this issue type
                rows = ["[None]"]
            replacements[issue_type] = "\n".join(rows)
        return message_template.format(**replacements)

    @property
    def outdated_users(self) -> list[User]:
        """The users with outdated backups, sorted by ascending usernames."""
        return self._issue_index["outdated_users"].copy()

    @property
    def future_users(self) -> list[User]:
        """The users with backups containing future-dated files, sorted by ascending usernames."""
        return self._issue_index["future_users"].copy()

    @property
    def ok_users(self) -> list[User]:
        """The users with neither outdated nor future backups, sorted by ascending usernames."""
        return self._issue_index["ok_users"].copy()


# Email Reporting
class MailClient:
    """Abstract base class for email handling as used by user_backup_checker.py."""

    def get_email_address(self, user: User):
        """Returns the email address of the given user."""
        raise NotImplementedError()

    def send_email(self, receiver: User, subject: str, message: str):
        """Send an email to the provided User."""
        raise NotImplementedError()


class MailReporter:
    """Reporter for sending users emails to warn them about outdated backups or future files.

    Users with future-dated files receive an email everyday, and users with outdated backups receive
    an email after reminder_interval.
    """

    def __init__(self, reporter: StatusReporter, mail_client: MailClient,
                 reminder_interval: timedelta, exclude_weekends: bool):
        """Initializes the reporter.

        Args:
            reporter: StatusReporter containing the lists of outdated and future users.
            mail_client: MailClient
            reminder_interval: Pause between consecutive reminder emails. Only intervals in days are
                accepted (i.e. no hours, minutes, seconds, etc.). reminder_interval only determines
                reminder emails that follow *after* the first email, which in turn is determined by
                `reporter.tolerance_outdated`.
            exclude_weekends: Whether to omit weekends when computing time differences.
        """
        if reminder_interval.seconds != 0 or reminder_interval.microseconds != 0:
            # This check uses that timedelta objects only store days, seconds, and microseconds,
            # see: https://docs.python.org/3/library/datetime.html#datetime.timedelta
            raise RuntimeError("reminder_interval must be a multiple of entire days.")
        self._status_reporter = reporter
        self._mail_client = mail_client
        self._reminder_interval = reminder_interval
        self._exclude_weekends = exclude_weekends
        self._future_recipients = list(reporter.future_users)
        self._outdated_recipients = [u for u in reporter.outdated_users if self._is_mail_due(u)]

    @property
    def future_recipients(self) -> list[User]:
        """The users with future-dated files who will get an email."""
        return self._future_recipients.copy()

    @property
    def outdated_recipients(self) -> list[User]:
        """The users with outdated backups who will get an email."""
        return self._outdated_recipients.copy()

    def notify_outdated_recipients(self, subject: str, email_template: str):
        """Sends an email to the users with outdated backups.

        Args:
            subject: Subject of the emails. The same subject is sent to all users.
            email_template: Template of the email to send to users. It should contain the following
                placeholders, which are replaced individually for each user:
                - {date_last_backup}: Date of the user's last backup.
                - {outdated_days}: Number of days the last backup is in the past compared to today.

        Effects:
            Sends the email to the user.
        """
        day_unit = "weekdays" if self._exclude_weekends else "days"
        reference_date = self._status_reporter.reference_date

        for user in self._future_recipients:
            # Assemble message
            date = user.newest_date
            outdated_days = time_difference(date, reference_date, self._exclude_weekends).days
            message = email_template.format(date_last_backup=date.strftime("%Y-%m-%d"),
                                            outdated_days=f"{outdated_days} {day_unit}")

            # Send message
            self._mail_client.send_email(user, message, subject)
        # TODO: Instead of subject and email_template, notify_outdated_recipients should take a function taking a user as argument and returning subject and message. This avoids the dependence of MailReporter on the concrete fields to be replaced.

    def notify_future_recipients(self, subject: str, email_template: str):
        """Sends an email to the users with future files in their backups.

        Args:
            subject: Subject of the emails. The same subject is sent to all users.
            email_template: Template of the email to send to users. It should contain the following
                placeholders, which are replaced individually for each user:
                - {path}: Path to the future-dated file.
                - {date}: Modification time of the future-dated file.

        Effects:
            Sends the email to the user.
        """
        for user in self._future_recipients:
            message = email_template.format(path=user.newest_path,
                                            date=user.newest_date.strftime("%Y-%m-%d"))
            self._mail_client.send_email(user, subject, message)

    def _is_mail_due(self, user: User) -> bool:
        """Determines whether a notification email to the given user is due on the reference_date.

        This function does not store any databases to determine when emails are sent to users.
        Instead, it assumes that user_backup_checker.py is run once per day.

        Args:
            user: User to check

        Returns:
            True if (i) the user has an *outdated* backup and (ii) the previous email was sent
            exactly the given reminder_interval ago.
        """
        reference_date = self._status_reporter.reference_date.date()  # no hours, minutes, etc.
        tolerance_outdated = self._status_reporter.tolerance_outdated
        assert user.is_outdated(reference_date, tolerance_outdated)

        # Compute day of first email
        date = user.newest_date
        while time_difference(user.newest_date, date, self._exclude_weekends) <= tolerance_outdated:
            date += timedelta(days=1)
        day_first_email = date.date()

        # Check if an email is due on reference_date.
        if reference_date < day_first_email:
            return False
        if reference_date == day_first_email:
            return True
        days_since_first = time_difference(day_first_email, reference_date, self._exclude_weekends)
        return days_since_first % self._reminder_interval == timedelta(0)


# Main
def main(mail_client: Optional[MailClient] = None):
    """Main function of the script."""

    # Configure log to show after report
    message_queue = Queue()
    logger.addHandler(QueueHandler(message_queue))
    logger.setLevel(WARNING)

    # Get users and their backup state
    users = user_factory(USER_DETECTION_LOOKUPS, USERS_TO_EXCLUDE)
    if not users:
        print("ERROR: No user found on Synology.")
        sys.exit(2)

    # Print status report
    reporter = StatusReporter(users, datetime.now(), TOLERANCE_OUTDATED, TOLERANCE_FUTURE)
    print(reporter.get_report(ADMIN_STATUS_REPORT))

    # Notify individual users
    if mail_client:
        mail_reporter = MailReporter(reporter, mail_client, REMINDER_INTERVAL, EXCLUDE_WEEKENDS)
        mail_reporter.notify_outdated_recipients(SUBJECT_OUTDATED, MAIL_OUTDATED)
        mail_reporter.notify_future_recipients(SUBJECT_FUTURE, MAIL_FUTURE)

    # Print log
    if not message_queue.empty():
        print("Log:")
        while not message_queue.empty():
            print(message_queue.get())
    sys.exit(0)


if __name__ == "__main__":
    main(mail_client=None)
