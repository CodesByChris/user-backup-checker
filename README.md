[![Lint & Test](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml)
[![Codecov](https://codecov.io/gh/CodesByChris/user-backup-checker/branch/main/graph/badge.svg)](https://codecov.io/gh/CodesByChris/user-backup-checker)


# User Backup Checker

Integrity checker for user backups performed via Synology Drive.

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
2. **Supports local and domain users.**
3. **Privacy-focused: UBC does not collect usage data.**
    UBC itself does not communicate with anything outside the server except for the emails to server admins and users.

UBC is a third-party script that has no association with Synology.


## Copyright

UBC is released under the *GNU Affero General Public License v3.0*

Copyright 2023, ETH Zurich.

Developer: Christian Zingg as employee at Chair of Systems Design, ETH Zurich.
