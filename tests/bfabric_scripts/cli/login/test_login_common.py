from __future__ import annotations

import yaml

from bfabric._oauth._constants import DEFAULT_OAUTH_SCOPE
from bfabric_scripts.cli.login._common import (
    describe_scope,
    describe_token_cache,
    resolve_config_env,
    resolve_scope,
    resolve_set_default,
)


def _write_config(config_file, default="PROD"):
    general = {"default_config": default} if default is not None else {}
    config_file.write_text(
        yaml.dump(
            {
                "GENERAL": general,
                "PROD": {"base_url": "https://prod.example.com", "auth_method": "oauth"},
                "TEST": {"base_url": "https://test.example.com", "auth_method": "oauth"},
            }
        )
    )


class TestResolveConfigEnv:
    def test_explicit_value_returned_as_is(self, tmp_path, mocker):
        # An explicit value short-circuits: no file read, no prompt.
        resolve = mocker.patch("bfabric_scripts.cli.login._common.resolve_choice")
        assert resolve_config_env("STAGE", tmp_path / "missing.yml") == "STAGE"
        resolve.assert_not_called()

    def test_non_interactive_uses_current_default(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="TEST")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_config_env(None, config_file) == "TEST"

    def test_non_interactive_without_default_falls_back_to_production(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default=None)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_config_env(None, config_file) == "PRODUCTION"

    def test_non_interactive_missing_file_falls_back_to_production(self, tmp_path, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_config_env(None, tmp_path / "missing.yml") == "PRODUCTION"

    def test_interactive_offers_existing_and_allows_new(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        resolve = mocker.patch("bfabric_scripts.cli.login._common.resolve_choice", return_value="NEWENV")
        assert resolve_config_env(None, config_file) == "NEWENV"
        args = resolve.call_args.args
        kwargs = resolve.call_args.kwargs
        assert args[0] is None
        assert set(args[1]) == {"PROD", "TEST"}
        assert kwargs["allow_new"] is True
        # The current default is prefilled.
        assert kwargs["default"] == "PROD"

    def test_interactive_cancel_returns_none(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.resolve_choice", return_value=None)
        assert resolve_config_env(None, config_file) is None


class TestResolveScope:
    def test_preset_slug_expands(self):
        assert resolve_scope("read-only") == "api:read openid profile email groups"
        assert resolve_scope("read-write") == DEFAULT_OAUTH_SCOPE
        assert resolve_scope("read-write-upload") == f"{DEFAULT_OAUTH_SCOPE} tus"

    def test_raw_string_passthrough(self):
        assert resolve_scope("api:read custom:thing") == "api:read custom:thing"

    def test_non_interactive_defaults_to_read_write(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_scope(None) == DEFAULT_OAUTH_SCOPE

    def test_interactive_preset_pick_expands(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="read-write-upload")
        assert resolve_scope(None) == f"{DEFAULT_OAUTH_SCOPE} tus"

    def test_interactive_custom_prompts_for_raw_scopes(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="custom")
        text = mocker.patch("bfabric_scripts.cli.login._common.text_input", return_value="api:read containers")
        assert resolve_scope(None) == "api:read containers"
        text.assert_called_once()

    def test_interactive_cancel_returns_none(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value=None)
        assert resolve_scope(None) is None


class TestDescribeScope:
    def test_matched_preset_is_annotated(self):
        # A granted scope equal to a preset (order-insensitive) is annotated with the preset name.
        scope = f"tus {DEFAULT_OAUTH_SCOPE}"  # reordered to prove match is order-insensitive
        described = describe_scope(scope)
        assert "read-write-upload" in described
        assert "tus" in described

    def test_unmatched_scope_shown_raw(self):
        assert describe_scope("api:read custom:thing") == "api:read custom:thing"

    def test_absent_scope_is_not_recorded(self):
        assert describe_scope(None) == "(not recorded)"
        assert describe_scope("") == "(not recorded)"
        # A non-string (unexpected cache shape) must not blow up.
        assert describe_scope(123) == "(not recorded)"


class TestDescribeTokenCache:
    def test_missing_cache(self):
        assert describe_token_cache(None, now=1000.0) == "missing"

    def test_present_without_expiry(self):
        assert describe_token_cache({"access_token": "x"}, now=1000.0) == "present"

    def test_expired(self):
        assert "expired" in describe_token_cache({"access_token": "x", "expires_at": 900}, now=1000.0)

    def test_valid_reports_remaining(self):
        # 2h30m from now.
        described = describe_token_cache({"access_token": "x", "expires_at": 1000 + 9000}, now=1000.0)
        assert "present" in described
        assert "2h" in described


class TestResolveSetDefault:
    def test_explicit_true_honored_without_prompt(self, mocker):
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(True, "PROD") is True
        confirm.assert_not_called()

    def test_explicit_false_honored_without_prompt(self, mocker):
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(False, "PROD") is False
        confirm.assert_not_called()

    def test_non_interactive_defaults_to_true(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(None, "PROD") is True
        confirm.assert_not_called()

    def test_interactive_prompts_preselected_yes(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=False)
        assert resolve_set_default(None, "PROD") is False
        # The prompt is preselected to "yes".
        assert confirm.call_args.kwargs["default"] is True

    def test_interactive_cancel_returns_none(self, mocker):
        # A cancelled prompt (confirm -> None) is propagated so the caller aborts the login.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=None)
        assert resolve_set_default(None, "PROD") is None
