"""Fixtures shared across test files."""

from typing import Callable, Union
import os
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from unittest.mock import patch
from ubc.user_backup_checker import CONFIG, User


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
    desktop_dir.mkdir()
    file_2 = documents_dir / "old_file_2.txt"
    file_2.write_text("f2")
    set_modification_date(file_2, datetime(2020, 1, 8, 0, 0, 0))

    # Create newest_file.txt
    file_3 = documents_dir / "newest_file.txt"
    file_3.write_text("f3")
    set_modification_date(file_3, datetime(2020, 1, 15, 0, 0, 0))


def init_mock_files_2(path_root: Path):
    """Initializes a mock folder tree with given root path.

    Tree is:
    - path_root/
        - Downloads/
            - old_file_1.txt      (timestamp: 2020-08-01 00:00.00, content: "f1")
        - .hidden/
            - newest_file.txt     (timestamp: 2023-01-03 00:00.00, content: "f3")
            - test/
                - old_file_2.txt  (timestamp: 2020-01-15 00:00.00, content: "f2")
    """
    # Create old_file_1.txt
    downloads_dir = path_root / "Downloads"
    downloads_dir.mkdir(parents=True)
    file_1 = downloads_dir / "old_file_1.txt"
    file_1.write_text("f1")
    set_modification_date(file_1, datetime(2020, 8, 1, 0, 0, 0))

    # Create newest_file.txt
    hidden_dir = path_root / ".hidden"
    hidden_dir.mkdir()
    file_3 = hidden_dir / "newest_file.txt"
    file_3.write_text("f3")
    set_modification_date(file_3, datetime(2023, 1, 3, 0, 0, 0))

    # Create old_file_2.txt
    test_dir = hidden_dir / "test"
    test_dir.mkdir()
    file_2 = test_dir / "old_file_2.txt"
    file_2.write_text("f2")
    set_modification_date(file_2, datetime(2020, 1, 15, 0, 0, 0))


def make_localuser(name: str, dir_userhomes: Path, file_initializer: Union[Callable, None]):
    """Initializes a user."""
    backup_dir = dir_userhomes / name / "Drive" / "Backup"
    backup_dir.mkdir(parents=True)
    if file_initializer:
        file_initializer(backup_dir)
    return User(name, backup_dir)


def make_domainuser(user_name: str, user_id: str, dir_userhomes: Path,
                    file_initializer: Union[Callable, None]):
    """Initializes a user."""
    backup_dir = dir_userhomes / user_id / user_name / "Drive" / "Backup"
    backup_dir.mkdir(parents=True)
    if file_initializer:
        file_initializer(backup_dir)
    return User(user_name, backup_dir)


@pytest.fixture
def path_syno_root() -> Path:
    """Yields root of mock root directory ("/") on a Synology."""
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def paths_localuser_homes(path_syno_root) -> Path:
    """Yields root of mock folder tree replicating where Synology stores local users' homes."""
    path_homes = path_syno_root / "volume1" / "homes"
    path_homes.mkdir(parents=True)
    return path_syno_root, path_homes


@pytest.fixture
def paths_domainuser_homes(path_syno_root) -> Path:
    """Yields root of mock folder tree replicating where Synology stores domain users' homes."""
    path_homes = path_syno_root / "volume1" / "homes" / "@DH-D"
    path_homes.mkdir(parents=True)
    return path_syno_root, path_homes


@pytest.fixture
def user_detection_lookup(path_syno_root) -> dict:
    """Constructs user_detection_lookup to find local- and domain-users in the mock file system."""
    return {
        "local": {"home_dirs_glob": f"{path_syno_root}/volume1/homes/[!@.]*/",
                  "backup_subdir": "Drive/Backup/"},
        "domain": {"home_dirs_glob": f"{path_syno_root}/volume1/homes/@DH-D/*/*/",
                   "backup_subdir": "Drive/Backup/"},
    }


@pytest.fixture
def config_test(user_detection_lookup) -> dict:
    """Patches CONFIG to find users in the testing directories."""
    with patch.dict(CONFIG, USER_DETECTION_LOOKUPS=user_detection_lookup):
        yield CONFIG


@pytest.fixture
def empty_localuser(paths_localuser_homes) -> User:
    """Returns a local-user with no files in the backup directory."""
    return make_localuser("empty_localuser", paths_localuser_homes[1], None)


@pytest.fixture
def broken_domainuser(paths_domainuser_homes) -> None:
    """Initializes a user with a Drive folder but no backup directory inside."""
    username = "broken_domainuser"
    dir_backup = paths_domainuser_homes[1] / "8" / username / "Drive"
    dir_backup.mkdir(parents=True)


@pytest.fixture
def simple_localuser(paths_localuser_homes) -> User:
    """Returns a local-user with simple folder tree in backup directory (see init_mock_files)."""
    return make_localuser("simple_localuser", paths_localuser_homes[1], init_mock_files)


@pytest.fixture
def simple_localuser_2(paths_localuser_homes) -> User:
    """Returns a local-user with simple folder tree in backup directory (see init_mock_files_2)."""
    return make_localuser("simple_localuser_2", paths_localuser_homes[1], init_mock_files_2)


@pytest.fixture
def simple_domainuser(paths_domainuser_homes) -> User:
    """Returns a domain-user with simple folder tree in backup directory (see init_mock_files)."""
    return make_domainuser("simple_domainuser", "3", paths_domainuser_homes[1], init_mock_files)


@pytest.fixture
def simple_domainuser_2(paths_domainuser_homes) -> User:
    """Returns a domain-user with simple folder tree in backup directory (see init_mock_files_2)."""
    return make_domainuser("simple_domainuser_2", "8", paths_domainuser_homes[1], init_mock_files_2)
