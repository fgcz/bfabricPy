from __future__ import annotations

import pytest
import yaml

from bfabric.config.config_file import EnvironmentConfig
from bfabric_scripts.cli.login._common import (
    describe_active_reason,
    normalize_base_url,
    require_mutable_config,
    resolve_base_url,
    resolve_config_env,
    resolve_scope,
    resolve_set_default,
    suggest_config_env,
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
        prompt = mocker.patch("bfabric_scripts.cli.login._common.select_or_input")
        assert resolve_config_env("STAGE", tmp_path / "missing.yml") == "STAGE"
        prompt.assert_not_called()

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

    def test_configured_default_is_used_without_prompting(self, tmp_path, mocker):
        """Resolving silently is the point: prompting here is the prompt a zero-argument re-login
        exists to avoid."""
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        prompt = mocker.patch("bfabric_scripts.cli.login._common.select_or_input")
        assert resolve_config_env(None, config_file) == "PROD"
        prompt.assert_not_called()

    def test_interactive_offers_existing_and_allows_new_when_no_default_is_set(self, tmp_path, mocker):
        """The one ambiguous case: environments exist but none of them is the default."""
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default=None)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        prompt = mocker.patch("bfabric_scripts.cli.login._common.select_or_input", return_value="NEWENV")
        assert resolve_config_env(None, config_file) == "NEWENV"
        args = prompt.call_args.args
        # select_or_input offers the existing names as suggestions but lets the user type a new one.
        assert set(args[1]) == {"PROD", "TEST"}

    def test_interactive_cancel_returns_none(self, tmp_path, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default=None)
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_or_input", return_value=None)
        assert resolve_config_env(None, config_file) is None


class TestResolveScope:
    def test_preset_slug_expands(self):
        assert resolve_scope("read-only") == "api:read"
        assert resolve_scope("read-write") == "api:write"
        assert resolve_scope("upload") == "api:write tus"

    def test_raw_string_passthrough(self):
        assert resolve_scope("api:read custom:thing") == "api:read custom:thing"

    def test_non_interactive_without_scope_returns_none(self, mocker):
        # No baked-in default: a headless login must pass --scope explicitly.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_scope(None) is None

    def test_interactive_preset_pick_expands(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="upload")
        assert resolve_scope(None) == "api:write tus"

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


class TestResolveSetDefault:
    def test_explicit_true_honored_without_prompt(self, mocker):
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(True, "PROD") is True
        confirm.assert_not_called()

    def test_explicit_false_honored_without_prompt(self, mocker):
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(False, "PROD") is False
        confirm.assert_not_called()

    def test_re_login_into_existing_env_does_not_prompt(self, mocker):
        """A re-login changes no defaults, so asking about them would be a prompt in the
        zero-argument path that exists precisely to have none."""
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(None, "PROD") is False
        confirm.assert_not_called()

    def test_new_env_non_interactive_defaults_to_true(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm")
        assert resolve_set_default(None, "PROD", is_new_env=True) is True
        confirm.assert_not_called()

    def test_new_env_interactive_prompts_preselected_yes(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        confirm = mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=False)
        assert resolve_set_default(None, "PROD", is_new_env=True) is False
        # The prompt is preselected to "yes".
        assert confirm.call_args.kwargs["default"] is True

    def test_new_env_interactive_cancel_returns_none(self, mocker):
        # A cancelled prompt (confirm -> None) is propagated so the caller aborts the login.
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.confirm", return_value=None)
        assert resolve_set_default(None, "PROD", is_new_env=True) is None


class TestResolveConfigEnvEnvironmentVariable:
    """``BFABRICPY_CONFIG_ENV`` sits between an explicit value and the configured default, matching
    ``ConfigFile.get_selected_config_env`` — so a login lands where a later connect would look."""

    def test_env_var_outranks_the_configured_default(self, tmp_path, monkeypatch, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "TEST")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_config_env(None, config_file) == "TEST"

    def test_explicit_value_outranks_the_env_var(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "TEST")
        assert resolve_config_env("STAGE", config_file) == "STAGE"

    def test_env_var_skips_the_interactive_picker(self, tmp_path, monkeypatch, mocker):
        config_file = tmp_path / "config.yml"
        _write_config(config_file, default="PROD")
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "TEST")
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        prompt = mocker.patch("bfabric_scripts.cli.login._common.select_or_input")
        assert resolve_config_env(None, config_file) == "TEST"
        prompt.assert_not_called()


class TestResolveBaseUrl:
    def test_explicit_value_is_normalized(self):
        assert resolve_base_url("example.com/bfabric/", None) == "https://example.com/bfabric"

    def test_falls_back_to_the_recorded_base_url(self):
        """This is what removes the retype from a re-login."""
        env = EnvironmentConfig.model_validate({"base_url": "https://recorded.example.com/bfabric"})
        assert resolve_base_url(None, env) == "https://recorded.example.com/bfabric"

    def test_explicit_value_wins_over_the_recorded_one(self):
        env = EnvironmentConfig.model_validate({"base_url": "https://recorded.example.com/bfabric"})
        assert resolve_base_url("https://typed.example.com/bfabric", env) == "https://typed.example.com/bfabric"

    def test_first_login_non_interactive_returns_none(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_base_url(None, None) is None

    def test_first_login_interactive_opens_the_instance_picker(self, mocker):
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="fgcz-demo")
        assert resolve_base_url(None, None) == "https://fgcz-bfabric-demo.uzh.ch/bfabric"


class TestResolveScopeFromEnvironment:
    def test_recorded_scope_is_replayed(self):
        env = EnvironmentConfig.model_validate({"base_url": "https://example.com", "scope": "api:write tus"})
        assert resolve_scope(None, env) == "api:write tus"

    def test_explicit_scope_wins_over_the_recorded_one(self):
        env = EnvironmentConfig.model_validate({"base_url": "https://example.com", "scope": "api:read"})
        assert resolve_scope("upload", env) == "api:write tus"

    def test_env_without_scope_still_prompts(self, mocker):
        """A 1.16.0-era environment has no ``scope``; it prompts once rather than reusing the cached
        *granted* scope, which would bake in a silent server-side drop."""
        env = EnvironmentConfig.model_validate({"base_url": "https://example.com", "auth_method": "oauth"})
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=True)
        mocker.patch("bfabric_scripts.cli.login._common.select_choice", return_value="read-only")
        assert resolve_scope(None, env) == "api:read"

    def test_env_without_scope_headless_returns_none(self, mocker):
        env = EnvironmentConfig.model_validate({"base_url": "https://example.com", "auth_method": "oauth"})
        mocker.patch("bfabric_scripts.cli.login._common.is_interactive", return_value=False)
        assert resolve_scope(None, env) is None


class TestSuggestConfigEnv:
    def test_derives_from_a_known_instance(self):
        assert suggest_config_env("https://fgcz-bfabric-demo.uzh.ch/bfabric", []) == "fgcz-demo"

    def test_derives_from_the_host_for_an_unknown_instance(self):
        assert suggest_config_env("https://bfabric.example.com/bfabric", []) == "bfabric-example-com"

    def test_suffixes_when_the_name_is_taken(self):
        assert suggest_config_env("https://fgcz-bfabric-demo.uzh.ch/bfabric", ["fgcz-demo"]) == "fgcz-demo-2"
        assert (
            suggest_config_env("https://fgcz-bfabric-demo.uzh.ch/bfabric", ["fgcz-demo", "fgcz-demo-2"])
            == "fgcz-demo-3"
        )


class TestRequireMutableConfig:
    def test_allows_when_no_override_is_set(self, monkeypatch):
        monkeypatch.delenv("BFABRICPY_CONFIG_OVERRIDE", raising=False)
        assert require_mutable_config() is True

    def test_refuses_and_names_the_variable(self, monkeypatch, capsys):
        monkeypatch.setenv("BFABRICPY_CONFIG_OVERRIDE", '{"base_url": "https://example.com"}')
        assert require_mutable_config() is False
        assert "BFABRICPY_CONFIG_OVERRIDE" in capsys.readouterr().out


class TestDescribeActiveReason:
    def test_marks_the_configured_default(self, monkeypatch):
        monkeypatch.delenv("BFABRICPY_CONFIG_OVERRIDE", raising=False)
        assert describe_active_reason("PROD", "PROD") == "  (default)"
        assert describe_active_reason("TEST", "PROD") == ""

    def test_env_var_overrides_the_default_marker(self, monkeypatch):
        """The invisible case: the default is *not* what is in effect."""
        monkeypatch.delenv("BFABRICPY_CONFIG_OVERRIDE", raising=False)
        monkeypatch.setenv("BFABRICPY_CONFIG_ENV", "TEST")
        assert describe_active_reason("TEST", "PROD") == "  (active via BFABRICPY_CONFIG_ENV)"
        assert describe_active_reason("PROD", "PROD") == ""

    def test_override_pins_everything(self, monkeypatch):
        monkeypatch.setenv("BFABRICPY_CONFIG_OVERRIDE", '{"base_url": "https://example.com"}')
        assert describe_active_reason("PROD", "PROD") == "  (config pinned by BFABRICPY_CONFIG_OVERRIDE)"
