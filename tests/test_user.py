"""Tests for User class."""

from datetime import datetime, timedelta
import pytest
from pytest_lazyfixture import lazy_fixture
from ubc.user_backup_checker import User, user_factory


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
                      path_syno_root):
    """Tests the base functionality."""
    users = [simple_localuser, simple_localuser_2, simple_domainuser, simple_domainuser_2]

    # Collect users from factory
    user_detection_lookups = {
        "local": {"home_dirs_glob": f"{path_syno_root}/volume1/homes/[!@.]*/",
                  "backup_subdir": "Drive/Backup/"},
        "domain": {"home_dirs_glob": f"{path_syno_root}/volume1/homes/@DH-D/*/*/",
                   "backup_subdir": "Drive/Backup/"},
    }
    factory_users = user_factory(user_detection_lookups)

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

# Test user_factory:
#     - Does it throw an error when the same username exists twice (e.g. local user and domain user)
#     - Test exclude_users
#     - Test logging broken users in user_factory
# Test exit codes (e.g. when no user exists on Synology).
