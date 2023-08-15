"""Tests for main UBC script."""

import pytest
from ubc.user_backup_checker import main


def test_exit_0(config_test, simple_domainuser):
    """Integration test: successful run (exit code 0)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)
    assert exit_code.value.code == 0


def test_exit_0_with_reporting(config_test, simple_domainuser, broken_domainuser,
                               paths_domainuser_homes, caplog, capsys):
    """Integration test: one healthy user and one broken user found (exit code 0 + log)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)

    # Test exit code
    assert exit_code.value.code == 0

    # Test log
    assert len(caplog.records) == 1
    assert caplog.record_tuples[0][2].startswith("Backup dir not found")

    # Test output (i.e. protocol)
    missing_backup_dir = paths_domainuser_homes[1] / "8" / "broken_domainuser" / "Drive" / "Backup"
    expected = dedent(f"""
        Outdated users:
        - simple_domainuser  (2020-01-15)


        Users with future files:
        [None]


        OK users:
        [None]


        For an explanation of each position see the documentation in user_backup_checker.py


        Log:
        - Backup dir not found (user 'broken_domainuser'): '{missing_backup_dir}'
    """)
    assert capsys.readouterr().out == expected


def test_exit_2(config_test, paths_localuser_homes, paths_domainuser_homes):
    """Integration test: no users found (exit code 2)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)
    assert exit_code.value.code == 2


def test_exit_2_broken_user(config_test, broken_domainuser, caplog):
    """Integration test: no users found (exit code 2) for one broken user (log only)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)
    assert exit_code.value.code == 2
    assert len(caplog.records) == 1
    assert caplog.record_tuples[0][2].startswith("Backup dir not found")
