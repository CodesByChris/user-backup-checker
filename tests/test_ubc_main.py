"""Tests for main UBC script."""

import pytest
from ubc.user_backup_checker import main


def test_exit_0(config_test, simple_domainuser):
    """Integration test: successful run (exit code 0)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)
    assert exit_code.value.code == 0


def test_exit_2(config_test, paths_localuser_homes, paths_domainuser_homes):
    """Integration test: no users found (exit code 2)."""
    with pytest.raises(SystemExit) as exit_code:
        main(config_test)
    assert exit_code.value.code == 2
