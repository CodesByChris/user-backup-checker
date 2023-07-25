"""Scan a Synology server for interrupted user backups performed with Synology Drive.

The validation has these steps:
1. Compile a list of users on the Synology.
2. Determine the most recent modification date among the files in each user's backup directory.
3. For each user, determine whether this date lies within a given number of days in the past.

(Optional) Sending automated emails to affected users. To enable this:
1. Implement `MailHandler.send_email` below. Depending on your Synology setup, this most likely
   requires you to set up an SMTP connection to a valid external email address, which
   user_backup_checker.py can use to send the emails.
2. Use MailReporter instead of Reporter in main().

Exit codes:
    0: Validation completed successfully.
    2: No user found on Synology.
"""

from typing import Any
from datetime import datetime, timedelta
from glob import glob
from os import path, stat, walk
from textwrap import dedent
from pathlib import Path
import sys


# Types
UserData = dict[str, Any]  # i.e. collection of stats about a user's backup
UserDataFrame = dict[str, UserData]  # lookup of "username:data" pairs


# Settings
USERS_TO_EXCLUDE = set()  # usernames to skip
USER_DETECTION_LOOKUPS = {
    "local": {"home_dirs_glob": "/volume1/homes/[!@.]*/", "backup_subdir": "Drive/Backup/"},
    "domain": {"home_dirs_glob": "/volume1/homes/@DH-D/*/*/", "backup_subdir": "Drive/Backup/"},
    # For naming and location of home directories of domain users see:
    #     https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/file_directory_service_user_group?version=7
    # The example above assumes the domain D, hence "@DH-D".
}
TOLERANCE_FUTURE = timedelta(days=1)  # Timespan for future files
TOLERANCE_OUTDATED = timedelta(days=5)  # Timespan for outdated backups
INCLUDE_WEEKENDS = False  # whether Saturdays and Sundays count towards outdated days


# Mail Templates
MAIL_TO_OUTDATED_USER = dedent("""
    Dear user,

    Your backup is outdated.

    - Date of last backup:  {date_last_backup}  ({outdated_days} outdated)

    Best regards,
    user_backup_checker.py
""")

MAIL_TO_FUTURE_USER = dedent("""
    Dear user,

    Your backup contains at least one file whose modification time lies in the future.

    - File:  {path}
    - Modification Time:  {date}

    Because of this file, your backup can not be validated correctly.

    Best regards,
    user_backup_checker.py
""")

MAIL_TO_ADMIN = dedent("""
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
                    include_weekends: bool = INCLUDE_WEEKENDS) -> timedelta:
    """Computes the time difference from date_1 to date_2.

    The difference is positive if date_1 <= date_2 and negative otherwise.

    This function essentially does the same as numpy.busday_count. However, numpy is not part of
    Synology's Python package, and therefore is not used here.

    Args:
        date_1: First point in time.
        date_2: Second point in time.
        include_weekends: Whether or not to count weekend-days into the time-difference. If True and
            date_1 or date_2 fall on a weekend, they are rounded to the next Monday, 00:00 o'clock.

    Returns:
        Computed time difference.
    """

    # Ensure date_1 <= date_2
    if date_1 > date_2:
        return -time_difference(date_1=date_2, date_2=date_1, include_weekends=include_weekends)

    # Handle times on weekends
    if not include_weekends and date_1.isoweekday() in {6, 7}:
        date_1 = _round_to_monday(date_1)
    if not include_weekends and date_2.isoweekday() in {6, 7}:
        date_2 = _round_to_monday(date_2)

    # Compute difference
    day_difference = 0
    while date_1 < date_2:
        if include_weekends or date_1.isoweekday() not in {6, 7}:
            day_difference += 1
        date_1 += timedelta(days=1)
    return (date_2 - date_1) + timedelta(days=day_difference)


# User Class
class User:
    """Collects information about a user on the Synology server."""

    def __init__(self, username: str, dir_backup: Path):
        self.username = username
        self.dir_backup = dir_backup  # TODO: Test if this directory exists.
        self._init_newest_file_and_date(dir_backup)

    def is_outdated(self, reference_date: datetime, tolerance: timedelta) -> bool:
        """Determines whether the user has an outdated backup.

        This function essentially computes
            self.newest_date < reference_date - tolerance
        but may also exclude weekends depending on the arguments.

        Args:
            reference_date: Timestamp compared to which the user's backup shall be outdated. To use
                today as the value, datetime.now() can be used.
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
                today as the value, datetime.now() can be used.
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
            users[name] = User(name, dir_backup=home_dir / Path(lookup["backup_subdir"]))
    return list(users.values())


def status_report(users: list[User], message_template: str,
                  tolerance_outdated: timedelta, tolerance_future: timedelta):
    """Returns a report of users with OK, outdated, and future backups.

    Args:
        users: Users that shall be included in the status report.
        message_template: String containing a template of the message to be printed. It has to
            contain the following substrings that will be replaced with the respective user
            statuses:
            - {ok_users} (users without problems).
            - {future_users} (users with future files in their backups).
            - {outdated_users} (users with outdated backups).
        tolerance_outdated: Tolerance period in which the most recent backup must have occurred to
            not be outdated.
        tolerance_future: Tolerance period in which the user's newest date is allowed to occur while
            is_in_future still returns False.

    Returns:
        The status report.
    """
    # Prepare lists of users
    reference_date = datetime.now()
    future_users = {u for u in users if u.is_in_future(reference_date, tolerance_future)}
    outdated_users = {u for u in users if u.is_outdated(reference_date, tolerance_outdated)}
    ok_users = {u for u in users if u not in outdated_users | future_users}

    issue_index = {
        "future_users": sorted(future_users),
        "outdated_users": sorted(outdated_users),
        "ok_users": sorted(ok_users),
    }

    # Fill template
    width_usernames = max(len(u.username) for u in users)
    row = f"- {{name:{width_usernames}}}  ({{date:%Y-%m-%d}})"

    replacements = {}
    for issue_type, issue_users in issue_index.items():
        rows = [row.format(name=u.username, date=u.newest_date) for u in issue_users]
        if not rows:
            # No user has this issue type
            rows = ["[None]"]
        replacements[issue_type] = "\n".join(rows)
    return message_template.format(**replacements)


# Main
def main():
    """Main function of the script."""

    # Get users and their backup state
    users = user_factory(USER_DETECTION_LOOKUPS, USERS_TO_EXCLUDE)
    if not users:
        print("ERROR: No user found on Synology.")
        sys.exit(2)

    # Print status report
    print(status_report(users, MAIL_TO_ADMIN, TOLERANCE_OUTDATED, TOLERANCE_FUTURE))
    sys.exit(0)


if __name__ == "__main__":
    main()
