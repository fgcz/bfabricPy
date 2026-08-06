"""The ``auth`` command surface itself: nothing else exercises the wiring in ``cli_auth.py``."""

from __future__ import annotations

import pytest

from bfabric_scripts.cli.cli_auth import cmd_auth

EXPECTED_COMMANDS = {
    "pat",
    "login",
    "device-code",
    "register",
    "register-webapp",
    "status",
    "logout",
    "remove",
    "activate",
    "list",
}


def _registered_names(app) -> set[str]:
    return {name for name in app if not name.startswith("-")}


class TestAuthCommandSurface:
    def test_every_expected_command_is_registered(self):
        assert EXPECTED_COMMANDS <= _registered_names(cmd_auth)

    @pytest.mark.parametrize("name", sorted(EXPECTED_COMMANDS))
    def test_each_command_resolves_to_a_handler(self, name):
        assert cmd_auth[name] is not None

    def test_default_is_gone(self):
        """Renamed to ``activate`` with no alias: ``auth`` is days old and marked experimental, so
        there is no install base to carry."""
        assert "default" not in _registered_names(cmd_auth)
        with pytest.raises(KeyError):
            _ = cmd_auth["default"]

    def test_no_unexpected_commands(self):
        assert _registered_names(cmd_auth) - EXPECTED_COMMANDS == set()


class TestTopLevelLoginAlias:
    def test_login_is_reachable_at_the_top_level(self):
        from bfabric_scripts.cli.__main__ import app

        assert app["login"] is not None

    def test_it_is_the_same_handler_as_auth_login(self):
        from bfabric_scripts.cli.__main__ import app
        from bfabric_scripts.cli.login.oauth_login import cmd_auth_login

        assert app["login"].default_command is cmd_auth_login

    def test_destructive_commands_are_not_aliased_to_the_top_level(self):
        """Only logging in earns a second spelling; nothing that deletes state does."""
        from bfabric_scripts.cli.__main__ import app

        top_level = _registered_names(app)
        assert {"logout", "remove", "activate"} & top_level == set()
