"""Tests for user_backup_checker.py"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from pytest_lazyfixture import lazy_fixture
from ubc.user_backup_checker import User


def set_modification_date(file: Path, new_date: datetime):
    """Sets the modification date of a given file to new_date."""
    assert file.exists(), f"File at path must exist: {file}"
    timestamp = new_date.timestamp()
    os.utime(file, times=(timestamp, timestamp))


def init_mock_files(path_root: Path):
    """Initializes a mock folder tree with given root path.

    Tree is:
    - path_root/
        - Documents/
            - old_file_1.txt   (timestamp: 2020-01-01 00:00.00, content: "f1")
            - newest_file.txt  (timestamp: 2020-01-15 00:00.00, content: "f2")
        - Desktop/
            - old_file_2.txt   (timestamp: 2020-01-08 00:00.00, content: "f3")
    """
    # Create old_file_1.txt
    documents_dir = path_root / "Documents"
    documents_dir.mkdir(parents=True)
    file_1 = documents_dir / "old_file_1.txt"
    file_1.write_text("f1")
    set_modification_date(file_1, datetime(2020, 1, 1, 0, 0, 0))

    # Create old_file_2.txt
    desktop_dir = path_root / "Desktop"
    desktop_dir.mkdir(parents=True)
    file_2 = documents_dir / "old_file_2.txt"
    file_2.write_text("f2")
    set_modification_date(file_2, datetime(2020, 1, 8, 0, 0, 0))

    # Create newest_file_1.txt
    file_3 = documents_dir / "newest_file.txt"
    file_3.write_text("f3")
    set_modification_date(file_3, datetime(2020, 1, 15, 0, 0, 0))


@pytest.fixture
def paths_localuser_homes() -> Path:
    """Yields root of mock folder tree replicating where Synology stores local users' homes."""
    with TemporaryDirectory() as temp_dir:
        path_root = Path(temp_dir)
        path_homes = path_root / "volume1" / "homes"
        path_homes.mkdir(parents=True)
        yield path_root, path_homes


@pytest.fixture
def empty_localuser(paths_localuser_homes, name="empty_localuser") -> User:
    """Returns a local-user with no files in the backup directory."""
    backup_dir = paths_localuser_homes[1] / name / "Drive" / "Backup"
    backup_dir.mkdir(parents=True)
    return User(name, backup_dir)


@pytest.fixture
def simple_localuser(paths_localuser_homes, name="simple_localuser") -> User:
    """Returns a local-user with a simple folder tree in backup directory (see init_mock_files)."""
    backup_dir = paths_localuser_homes[1] / name / "Drive" / "Backup"
    init_mock_files(backup_dir)
    return User(name, backup_dir)


@pytest.fixture
def paths_domainuser_homes() -> Path:
    """Yields root of mock folder tree replicating where Synology stores domain users' homes."""
    with TemporaryDirectory() as temp_dir:
        path_root = Path(temp_dir)
        path_homes = path_root / "volume1" / "homes" / "@DH-D"
        path_homes.mkdir(parents=True)
        yield path_root, path_homes


@pytest.fixture
def simple_domainuser(paths_domainuser_homes, id="3", name="simple_domainuser"):
    """Returns a domain-user with a simple folder tree in backup directory (see init_mock_files)."""
    backup_dir = paths_domainuser_homes[1] / id / name / "Drive" / "Backup"
    init_mock_files(backup_dir)
    return User(name, backup_dir)


@pytest.mark.parametrize("infuture_or_outdated", [User.is_in_future, User.is_outdated])
@pytest.mark.parametrize("special_case_0", [False, True])
def test_user_state_discovery(empty_localuser,
                              infuture_or_outdated,
                              special_case_0,
                              reference_date=datetime(2023, 7, 24, 13, 48, 10),
                              tolerance=timedelta(days=10)):
    """Tests User.is_outdated and User.is_in_future."""
    exclude_weekends = True
    plus_or_minus = 1 if infuture_or_outdated is User.is_in_future else - 1

    # Prepare user
    empty_localuser.newest_path = None

    # Test outdated / in future
    empty_localuser.newest_date = reference_date + plus_or_minus * 2 * tolerance
    assert infuture_or_outdated(empty_localuser, reference_date, tolerance, exclude_weekends)

    # Test within tolerance
    if not special_case_0:
        empty_localuser.newest_date = reference_date + plus_or_minus * tolerance / 2
        assert not infuture_or_outdated(empty_localuser, reference_date, tolerance, exclude_weekends)

    # Test exactly at newest_date
    empty_localuser.newest_date = reference_date
    assert not infuture_or_outdated(empty_localuser, reference_date, tolerance, exclude_weekends)

    # Test outside opposite interval
    empty_localuser.newest_date = reference_date - plus_or_minus * 2 * tolerance
    assert not infuture_or_outdated(empty_localuser, reference_date, tolerance, exclude_weekends)


@pytest.mark.parametrize("user", [
    lazy_fixture("simple_localuser"),
    lazy_fixture("simple_domainuser")
])
def test_user_modification_discovery(user):
    """Tests modification discovery."""
    assert user.newest_date == datetime(2020, 1, 15, 0, 0, 0)
    assert user.newest_path == user.dir_backup / "Documents" / "newest_file.txt"


def test_user_folder_missing(paths_localuser_homes, name="broken_localuser"):
    """Expects an error due to a missing backup folder."""
    with pytest.raises(FileNotFoundError):
        User(name, paths_localuser_homes[1] / name / "Drive" / "Backup")


# Test user_factory:
#     - Does it throw an error when the same username exists twice (e.g. local user and domain user)
# Test exit codes (e.g. when no user exists on Synology).
