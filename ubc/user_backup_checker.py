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

from typing import Any, Tuple
from datetime import datetime, timedelta
from os import path, stat, walk


# Types
UserData = dict[str, Any]  # i.e. collection of stats about a user's backup
UserDataFrame = dict[str, UserData]  # lookup of "username:data" pairs


# Settings
USERS_TO_EXCLUDE = []  # usernames to skip
USER_DETECTION = {
    "local": {"home_dirs_glob": "/volume1/homes/[!@.]*/", "backup_dir": "Drive"},
    "domain": {"home_dirs_glob": "/volume1/homes/@DH-D/*/*/", "backup_dir": "Drive"},
    # For naming and location of home directories of domain users see:
    #     https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/file_directory_service_user_group?version=7
    # The example above assumes the domain D, hence "@DH-D".
}
TOLERANCE_FUTURE = timedelta(days=1)  # Timespan for future files
TOLERANCE_OUTDATED = timedelta(days=5)  # Timespan for outdated backups
INCLUDE_WEEKENDS = False  # whether Saturdays and Sundays count towards outdated days
NOTIFY_USERS = True


# Mail Templates
MAIL_TO_OUTDATED_USER = """
Dear user,

Your backup is outdated.

- Date of last backup:  {date_last_backup}  ({outdated_days} outdated)

Best regards,
user_backup_checker.py
"""

MAIL_TO_FUTURE_USER = """
Dear user,

Your backup contains at least one file whose modification time lies in the future.

- File:  {path}
- Modification Time:  {date}

Because of this file, your backup can not be validated correctly.

Best regards,
user_backup_checker.py
"""

MAIL_TO_ADMIN = """
Outdated users:
{outdated_users}


Users with future files:
{future_users}


OK users:
{ok_users}


For an explanation of each position see the documentation in user_backup_checker.py

"""


# User Class
class User:
    """Collects information about a user on the Synology server."""

    def __init__(self, username: str, dir_backup: str):
        self.username = username
        self.dir_backup = dir_backup
        self.newest_path, self.newest_date = User._get_newest_update(dir_backup)

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

    @staticmethod
    def _get_newest_update(dir_base: str) -> Tuple[str | None, datetime | None]:
        """Determines the most recently updated file in dir_base or a sub-directory.

        The most recent file is the file with the newest timestamp. Note that this timestamp may lie
        in the future.

        If the directory is altered while get_newest_update runs, datetime.now() is returned
        immediately.

        Args:
            dir_base: Root of the folder-subtree to examine.

        Returns:
            Tuple containing first the most recent file's absolute path and then its timestamp.
        """
        newest_path = None
        newest_date = None
        for sub_root, _, files in walk(dir_base):
            for file in files:
                file_path = path.join(dir_base, sub_root, file)
                try:
                    file_date = stat(file_path, follow_symlinks=False).st_mtime
                    file_date = datetime.fromtimestamp(file_date)
                except FileNotFoundError:
                    # File has been deleted in the meantime
                    #     This means that a file exists that has been updated (deleted) just now.
                    return file_path, datetime.now()
                if newest_date is None or file_date > newest_date:
                    newest_path = file_path
                    newest_date = file_date
        return newest_path, newest_date
