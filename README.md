[![Lint & Test](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml)
[![Codecov](https://codecov.io/gh/CodesByChris/user-backup-checker/branch/main/graph/badge.svg)](https://codecov.io/gh/CodesByChris/user-backup-checker)


# User Backup Checker

Integrity checker for user backups performed via Synology Drive.

![UBC report with YAML coloring.](docs/images/ubc.png)

User Backup Checker (UBC) is a backend script for server administrators that warns them about users whose Synology Drive tool no longer performs backups.
Synology Drive is a precious tool enabling multiple users to perform backups and synchronize files to a central Synology server.
However, server administrators have no tool that actively alerts them when specific users stop performing backups, for example, because they forget to unpause Synology Drive or it can no longer reach the server after they change their passwords.
UBC periodically creates a report with the latest backup dates of users for administrators.
Optionally, it can automatically send emails to users with outdated backups and notify them about the problem.

UBC follows these design philosophies:
1. **Minimum configuration effort:**
    1. Dependencies only on _Python 3.8 standard library_, which comes pre-installed on newer Synology DSM versions.
    2. _Single-file solution_ (no caches or config files)
    3. UBC is _read-only_ and does neither modify nor create any files.
        It does not store databases, backup histories, or protocols.
        - Exceptions are actions the runtime environment performs outside UBC, such as Python automatically creating `__pycache__/` or server admins configuring log protocols on DSM to store UBC reports over time.
    4. _Periodic execution:_ UBC can be automated using Synology's default Task Scheduler.
        It does not require a continuous backup supervision process.
2. **Supports local and domain users.**
3. **Privacy-focused: UBC does not collect usage data.**
    UBC itself does not communicate with anything outside the server except for the emails to server admins and users.

UBC is a third-party script that has no association with Synology.


## Setup

Follow these steps to set up UBC on a Synology server.
To complete this setup, you need Synology server admin privileges.
Note that the optional email notifications for users with outdated backups have to be configured separately, see [Configuration](#configuration).

1. Open `ubc/user_backup_checker.py` in a text editor and adjust the settings to your preferences.
    See also [Configuration](#configuration) for the details.
2. Log in to Synology DSM with the admin account intended to run UBC.
    - **Ensure this account has read permissions for all user backup directories; otherwise, UBC cannot validate backups.**
3. Open _File Station_ and navigate to the directory where you wish to store the UBC script.
    For example, let's use `/volume1/homes/admin/`.
4. Upload `ubc/user_backup_checker.py` to this directory.
    The script path should now be: `/volume1/homes/admin/user_backup_checker.py`
5. Open _Control Panel_, then navigate to _Task Scheduler_ &rarr; _Create_ &rarr; _Scheduled task_ &rarr; _User-defined script_.
6. This leads to a _Create task_ dialog, which you can fill in as follows:
    1. _General:_
        - Provide a task name, like `User Backup Checker`.
        - Select the admin account for UBC execution.
        - Select _Enabled_.
    2. _Schedule:_
        - Define the days, times, and frequency for executing UBC.
    3. _Task Settings:_
        - Choose _Send run details by email_ and enter an email address if you wish to receive UBC reports by email.
            - Note: This setting only concerns admin emails.
                UBC directly sends emails to users with outdated backups.
            - Note: this setting requires an email account configured in _Control Panel_ &rarr; _Notification_ &rarr; _Email_.
        - Under _Run command_, write:
            ```
            python3 /volume1/homes/admin/user_backup_checker.py
            ```
            Adjust the path to match your setup.
7. Confirm with _OK_.

Done!


## Configuration


## Copyright

UBC is released under the *GNU Affero General Public License v3.0*

Copyright 2023, ETH Zurich.

Developer: Christian Zingg as employee at Chair of Systems Design, ETH Zurich.
