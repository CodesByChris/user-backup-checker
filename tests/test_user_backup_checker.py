"""Tests for user_backup_checker.py"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from pytest import fixture, mark
from ubc.user_backup_checker import User


def set_modification_date(file: Path, new_date: datetime):
    """Sets the modification date of a given file to new_date."""
    assert file.exists(), f"File at path must exist: {file}"
    timestamp = new_date.timestamp()
    os.utime(file, times=(timestamp, timestamp))


@fixture
def paths_localuser_homes() -> Path:
    """Yields root of mock folder tree replicating where Synology stores local users' homes."""
    with TemporaryDirectory() as temp_dir:
        path_root = Path(temp_dir)
        path_homes = path_root / "volume1" / "homes"
        path_homes.mkdir(parents=True)
        yield path_root, path_homes


@fixture
def empty_user(paths_localuser_homes, name="empty_user") -> User:
    """Returns a local-user with no files in the backup directory."""
    backup_dir = paths_localuser_homes[1] / name / "Drive" / "Backup"
    backup_dir.mkdir(parents=True)
    return User(name, backup_dir)


@fixture
def simple_user(paths_localuser_homes, name="simple_user") -> User:
    """Returns a local-user with a simple folder tree in the backup directory.

    Tree is:
    - ~/
        - Backup
            - Documents
                - old_file_1.txt   (timestamp: 2020-01-01 00:00.00, content: "f1")
                - newest_file.txt  (timestamp: 2020-01-15 00:00.00, content: "f2")
            - Desktop
                - old_file_2.txt   (timestamp: 2020-01-08 00:00.00, content: "f3")
    """
    backup_dir = paths_localuser_homes[1] / name / "Drive" / "Backup"

    # Create old_file_1.txt
    documents_dir = backup_dir / "Documents"
    documents_dir.mkdir(parents=True)
    file_1 = documents_dir / "old_file_1.txt"
    file_1.write_text("f1")
    set_modification_date(file_1, datetime(2020, 1, 1, 0, 0, 0))

    # Create old_file_2.txt
    desktop_dir = backup_dir / "Desktop"
    desktop_dir.mkdir(parents=True)
    file_2 = documents_dir / "old_file_2.txt"
    file_2.write_text("f2")
    set_modification_date(file_2, datetime(2020, 1, 8, 0, 0, 0))

    # Create newest_file_1.txt
    file_3 = documents_dir / "newest_file.txt"
    file_3.write_text("f3")
    set_modification_date(file_3, datetime(2020, 1, 15, 0, 0, 0))

    return User(name, backup_dir)


@mark.parametrize("infuture_or_outdated", [User.is_in_future, User.is_outdated])
@mark.parametrize("special_case_0", [False, True])
def test_user_problem_discovery(empty_user,
                                infuture_or_outdated,
                                special_case_0,
                                reference_date=datetime(2023, 7, 24, 13, 48, 10),
                                tolerance=timedelta(days=10)):
    """Tests User.is_outdated and User.is_in_future."""
    exclude_weekends = True
    plus_or_minus = 1 if infuture_or_outdated is User.is_in_future else - 1

    # Prepare user
    empty_user.newest_path = None

    # Test outdated / in future
    empty_user.newest_date = reference_date + plus_or_minus * 2 * tolerance
    assert infuture_or_outdated(empty_user, reference_date, tolerance, exclude_weekends)

    # Test within tolerance
    if not special_case_0:
        empty_user.newest_date = reference_date + plus_or_minus * tolerance / 2
        assert not infuture_or_outdated(empty_user, reference_date, tolerance, exclude_weekends)

    # Test exactly at newest_date
    empty_user.newest_date = reference_date
    assert not infuture_or_outdated(empty_user, reference_date, tolerance, exclude_weekends)

    # Test outside opposite interval
    empty_user.newest_date = reference_date - plus_or_minus * 2 * tolerance
    assert not infuture_or_outdated(empty_user, reference_date, tolerance, exclude_weekends)


def test_user_modification_discovery(simple_user):
    """Tests modification discovery."""
    assert simple_user.newest_date == datetime(2020, 1, 15, 0, 0, 0)
    assert simple_user.newest_path == simple_user.dir_backup / "Documents" / "newest_file.txt"


# Test user_factory:
#     - Does it throw an error when the same username exists twice (e.g. local user and domain user)
# Test exit codes (e.g. when no user exists on Synology).
