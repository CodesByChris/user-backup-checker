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
