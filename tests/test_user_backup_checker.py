"""Tests for user_backup_checker.py"""

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from pytest import fixture
from ubc.user_backup_checker import User


@fixture
def paths_localuser_homes() -> Path:
    """Returns root of mock folder tree replicating where Synology stores local users' homes."""
    with TemporaryDirectory() as temp_dir:
        path_root = Path(temp_dir)
        path_homes = path_root / "volume1" / "homes"
        path_homes.mkdir(parents=True)
        yield path_root, path_homes


@fixture
def empty_user(paths_localuser_homes, name="empty_user") -> User:
    """Yields a user with no files in the backup directory."""
    user_home_dir = paths_localuser_homes[1] / name
    user_home_dir.mkdir()
    return User(name, user_home_dir)


def test_user_is_outdated(empty_user,
                          reference_date=datetime(2023, 7, 24, 13, 48, 10),
                          tolerance=timedelta(days=10)):
    """Tests User.is_outdated."""

    # Prepare user
    empty_user.newest_path = None

    # Test outdated
    empty_user.newest_date = reference_date - 2 * tolerance
    assert empty_user.is_outdated(reference_date, tolerance)

    # Test within tolerance
    empty_user.newest_date = reference_date - tolerance / 2
    assert not empty_user.is_outdated(reference_date, tolerance)

    # Test exactly at newest_date
    empty_user.newest_date = reference_date
    assert not empty_user.is_outdated(reference_date, tolerance)

    # Test in future
    empty_user.newest_date = reference_date + timedelta(days=10)
    assert not empty_user.is_outdated(reference_date, tolerance)


def test_user_is_outdated_tol0(empty_user, reference_date=datetime(2023, 7, 24, 13, 48, 10)):
    """Tests User.is_outdated for a tolerance of 0."""

    # Prepare user
    empty_user.newest_path = None

    # Test outdated
    empty_user.newest_date = reference_date - timedelta(days=10)
    assert empty_user.is_outdated(reference_date, timedelta(0))

    # Test exactly at newest_date
    empty_user.newest_date = reference_date
    assert not empty_user.is_outdated(reference_date, timedelta(0))

    # Test in future
    empty_user.newest_date = reference_date + timedelta(days=10)
    assert not empty_user.is_outdated(reference_date, timedelta(0))


def test_user_is_in_future(empty_user,
                           reference_date=datetime(2023, 7, 24, 13, 48, 10),
                           tolerance=timedelta(days=10)):
    """Tests User.is_in_future."""

    # Prepare user
    empty_user.newest_path = None

    # Test in future
    empty_user.newest_date = reference_date + 2 * tolerance
    assert empty_user.is_in_future(reference_date, tolerance)

    # Test within tolerance
    empty_user.newest_date = reference_date + tolerance / 2
    assert not empty_user.is_in_future(reference_date, tolerance)

    # Test exactly at newest_date
    empty_user.newest_date = reference_date
    assert not empty_user.is_in_future(reference_date, tolerance)

    # Test in past
    empty_user.newest_date = reference_date - timedelta(days=10)
    assert not empty_user.is_in_future(reference_date, tolerance)


def test_user_is_in_future_tol0(empty_user, reference_date=datetime(2023, 7, 24, 13, 48, 10)):
    """Tests User.is_outdated for a tolerance of 0."""

    # Prepare user
    empty_user.newest_path = None

    # Test in future
    empty_user.newest_date = reference_date + timedelta(days=10)
    assert empty_user.is_in_future(reference_date, timedelta(0))

    # Test exactly at newest_date
    empty_user.newest_date = reference_date
    assert not empty_user.is_in_future(reference_date, timedelta(0))

    # Test in past
    empty_user.newest_date = reference_date - timedelta(days=10)
    assert not empty_user.is_in_future(reference_date, timedelta(0))


# Test user_factory:
#     - Does it throw an error when the same username exists twice (e.g. local user and domain user)
# Test exit codes (e.g. when no user exists on Synology).
