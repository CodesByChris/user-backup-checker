"""Tests for User class."""

from datetime import datetime, timedelta
import pytest
from pytest_lazyfixture import lazy_fixture
from ubc.user_backup_checker import User, user_factory
from .conftest import domainuser, localuser, init_mock_files, init_mock_files_2


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


def test_user_factory(simple_localuser, simple_localuser_2, simple_domainuser, simple_domainuser_2,
                      user_detection_lookup):
    """Tests the base functionality."""
    users = [simple_localuser, simple_localuser_2, simple_domainuser, simple_domainuser_2]
    factory_users = user_factory(user_detection_lookup)

    # Validate users
    assert len(factory_users) == len(users)
    for user in users:
        # Get corresponding user from factory
        user_f = None
        for user_f in factory_users:
            if user_f.username == user.username:
                break
        else:
            assert False  # user not found in users_factory

        # Compare users
        assert user == user_f
        assert hash(user) == hash(user_f)


def test_user_factory_exclude(simple_domainuser, simple_domainuser_2, user_detection_lookup):
    """Tests user_factory's users_to_exclude functionality."""

    # Test excluded simple_domainuser_2
    users_1 = user_factory(user_detection_lookup, {"simple_domainuser_2"})
    assert len(users_1) == 1
    assert users_1[0] == simple_domainuser

    # Test excluded simple_domainuser
    users_2 = user_factory(user_detection_lookup, {"simple_domainuser"})
    assert len(users_2) == 1
    assert users_2[0] == simple_domainuser_2


def test_user_factory_broken_user(simple_domainuser, broken_domainuser, paths_domainuser_homes,
                                  user_detection_lookup, caplog):
    """Tests whether a user with no backup directory is logged."""
    users = user_factory(user_detection_lookup)
    assert len(users) == 1
    assert users[0] == simple_domainuser
    assert len(caplog.records) == 1, "Exactly one log entry expected."
    assert caplog.record_tuples[0][2].startswith("Backup dir not found")


def test_user_factory_duplicate_user(paths_localuser_homes, paths_domainuser_homes,
                                     user_detection_lookup):
    """Tests whether user_factory stops when multiple users with same username exist."""
    username = "my_user"
    localuser(username, paths_localuser_homes[1], init_mock_files)
    domainuser(username, "8", paths_domainuser_homes[1], init_mock_files_2)
    with pytest.raises(Exception, match=f"More than one user has name: {username}"):
        user_factory(user_detection_lookup)
