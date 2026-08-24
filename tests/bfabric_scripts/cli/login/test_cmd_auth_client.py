from __future__ import annotations

import pytest

from bfabric_scripts.cli.login.client_manage import (
    cmd_auth_client_delete,
    cmd_auth_client_show,
    cmd_auth_client_update,
)


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text(
        "GENERAL:\n"
        "  default_config: CRON\n"
        "CRON:\n"
        "  base_url: https://example.com/bfabric\n"
        "  auth_method: client_credentials\n"
        "  client_id: cron\n"
        "  client_secret: s3cret\n"
        "  registration_access_token: reg-tok\n"
        "  registration_client_uri: https://example.com/bfabric/rest/oauth/register/cron\n"
    )
    return path


class TestCmdAuthClientShow:
    def test_reads_with_stored_registration_credentials(self, mocker, config_file, capsys):
        mock_read = mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"]},
        )
        cmd_auth_client_show(config_env="CRON", config_file=config_file)
        mock_read.assert_called_once_with(
            registration_client_uri="https://example.com/bfabric/rest/oauth/register/cron",
            registration_access_token="reg-tok",
        )
        assert "https://old/cb" in capsys.readouterr().out

    def test_errors_when_no_registration_token(self, tmp_path, capsys):
        path = tmp_path / "config.yml"
        path.write_text(
            "GENERAL:\n  default_config: P\nP:\n  base_url: https://example.com/bfabric\n  client_id: cron\n"
        )
        with pytest.raises(SystemExit):
            cmd_auth_client_show(config_env="P", config_file=path)
        assert "registration_access_token" in capsys.readouterr().err


class TestCmdAuthClientUpdate:
    def test_updates_redirect_uri(self, mocker, config_file):
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"], "scope": "read"},
        )
        mock_update = mocker.patch(
            "bfabric_scripts.cli.login.client_manage.update_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://new/cb"]},
        )
        cmd_auth_client_update(
            config_env="CRON",
            config_file=config_file,
            redirect_uri="https://new/cb",
        )
        metadata = mock_update.call_args.kwargs["metadata"]
        # RFC 7592 PUT replaces the document, so unchanged fields must be carried over from the read.
        assert metadata["redirect_uris"] == ["https://new/cb"]
        assert metadata["scope"] == "read"
        assert metadata["client_id"] == "cron"

    def test_requires_at_least_one_change(self, mocker, config_file, capsys):
        mocker.patch("bfabric_scripts.cli.login.client_manage.read_client", return_value={"client_id": "cron"})
        mock_update = mocker.patch("bfabric_scripts.cli.login.client_manage.update_client")
        with pytest.raises(SystemExit):
            cmd_auth_client_update(config_env="CRON", config_file=config_file)
        mock_update.assert_not_called()
        assert "Nothing to update" in capsys.readouterr().err


class TestCmdAuthClientUpdateRotation:
    """B-Fabric rotates the registration token (and secret) on update; both must be re-saved or the
    client becomes unmanageable — the next call would authenticate with a revoked token."""

    def test_persists_rotated_registration_token(self, mocker, config_file):
        import yaml

        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"]},
        )
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.update_client",
            return_value={
                "client_id": "cron",
                "redirect_uris": ["https://new/cb"],
                "registration_access_token": "rotated-tok",
                "client_secret": "rotated-secret",
            },
        )
        cmd_auth_client_update(
            config_env="CRON",
            config_file=config_file,
            redirect_uri="https://new/cb",
        )
        env = yaml.safe_load(config_file.read_text())["CRON"]
        assert env["registration_access_token"] == "rotated-tok"
        assert env["client_secret"] == "rotated-secret"
        # Untouched identity fields must survive the rewrite.
        assert env["client_id"] == "cron"
        assert env["auth_method"] == "client_credentials"
        assert env["registration_client_uri"] == "https://example.com/bfabric/rest/oauth/register/cron"

    def test_leaves_config_alone_when_nothing_rotated(self, mocker, config_file):
        import yaml

        before = config_file.read_text()
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"]},
        )
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.update_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://new/cb"]},
        )
        cmd_auth_client_update(
            config_env="CRON",
            config_file=config_file,
            redirect_uri="https://new/cb",
        )
        assert yaml.safe_load(config_file.read_text()) == yaml.safe_load(before)


class TestCmdAuthClientUpdatePartialRotation:
    """Only ``client_secret`` rotated: the untouched registration token must still survive the write,
    since the writer replaces every auth-owned key wholesale."""

    def test_preserves_registration_token_when_only_secret_rotates(self, mocker, config_file):
        import yaml

        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"]},
        )
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.update_client",
            return_value={
                "client_id": "cron",
                "redirect_uris": ["https://new/cb"],
                "client_secret": "rotated-secret",
            },
        )
        cmd_auth_client_update(
            config_env="CRON",
            config_file=config_file,
            redirect_uri="https://new/cb",
        )
        env = yaml.safe_load(config_file.read_text())["CRON"]
        assert env["client_secret"] == "rotated-secret"
        assert env["registration_access_token"] == "reg-tok"
        assert env["registration_client_uri"] == "https://example.com/bfabric/rest/oauth/register/cron"
        assert env["auth_method"] == "client_credentials"
        assert env["client_id"] == "cron"

    def test_reports_nothing_when_credentials_are_echoed_unchanged(self, mocker, config_file, capsys):
        """A server that echoes the current credentials has rotated nothing, so say nothing."""
        import yaml

        before = config_file.read_text()
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.read_client",
            return_value={"client_id": "cron", "redirect_uris": ["https://old/cb"]},
        )
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.update_client",
            return_value={
                "client_id": "cron",
                "redirect_uris": ["https://new/cb"],
                "client_secret": "s3cret",
                "registration_access_token": "reg-tok",
            },
        )
        cmd_auth_client_update(
            config_env="CRON",
            config_file=config_file,
            redirect_uri="https://new/cb",
        )
        assert "Updated" not in capsys.readouterr().err
        assert yaml.safe_load(config_file.read_text()) == yaml.safe_load(before)


class TestCmdAuthClientDelete:
    """Deleting a client is irreversible, so it must be confirmed and must clear the dead config."""

    def test_refuses_without_confirmation_non_interactively(self, mocker, config_file, capsys):
        mocker.patch("bfabric_scripts.cli.login.client_manage.is_interactive", return_value=False)
        mock_delete = mocker.patch("bfabric_scripts.cli.login.client_manage.delete_client")
        cmd_auth_client_delete(config_env="CRON", config_file=config_file)
        mock_delete.assert_not_called()
        assert "--no-confirm" in capsys.readouterr().err

    def test_deletes_with_no_confirm(self, mocker, config_file):
        mock_delete = mocker.patch("bfabric_scripts.cli.login.client_manage.delete_client")
        cmd_auth_client_delete(config_env="CRON", config_file=config_file, no_confirm=True)
        mock_delete.assert_called_once_with(
            registration_client_uri="https://example.com/bfabric/rest/oauth/register/cron",
            registration_access_token="reg-tok",
        )

    def test_clears_the_dead_credentials_from_config(self, mocker, config_file):
        """The client no longer exists, so leaving its secret and registration token behind would
        only let a later command fail confusingly."""
        import yaml

        mocker.patch("bfabric_scripts.cli.login.client_manage.delete_client")
        cmd_auth_client_delete(config_env="CRON", config_file=config_file, no_confirm=True)
        env = yaml.safe_load(config_file.read_text())["CRON"]
        assert "registration_access_token" not in env
        assert "client_secret" not in env
        assert env["base_url"] == "https://example.com/bfabric"

    def test_leaves_config_alone_when_the_delete_fails(self, mocker, config_file):
        before = config_file.read_text()
        mocker.patch(
            "bfabric_scripts.cli.login.client_manage.delete_client",
            side_effect=RuntimeError("boom"),
        )
        with pytest.raises(SystemExit):
            cmd_auth_client_delete(config_env="CRON", config_file=config_file, no_confirm=True)
        assert config_file.read_text() == before
