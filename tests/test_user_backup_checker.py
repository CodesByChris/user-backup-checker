"""Tests for user_backup_checker.py"""

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from pytest import fixture, mark
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


# Test user_factory:
#     - Does it throw an error when the same username exists twice (e.g. local user and domain user)
# Test exit codes (e.g. when no user exists on Synology).
