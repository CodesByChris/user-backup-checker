[![Lint & Test](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml/badge.svg)](https://github.com/CodesByChris/user-backup-checker/actions/workflows/lint-and-test.yml)
[![Codecov](https://codecov.io/gh/CodesByChris/user-backup-checker/branch/main/graph/badge.svg)](https://codecov.io/gh/CodesByChris/user-backup-checker)


# User Backup Checker

Integrity checker for user backups performed via Synology Drive.

User Backup Checker (UBC) is a backend script for server administrators that warns them about users whose Synology Drive tool no longer performs backups.
Synology Drive is a precious tool enabling multiple users to perform backups and synchronize files to a central Synology server.
However, server administrators have no tool that actively alerts them when specific users stop performing backups, for example, because they forget to unpause the tool or the tool cannot reach the server anymore.
UBC periodically creates a report with the latest backup dates of users.
Optionally, it can automatically send emails to users with outdated backups and notify them about the problem.

UBC is a third-party script that has no association with Synology.
