from __future__ import annotations

from unittest.mock import patch

from bfabric_scripts.cli.login.register import cmd_login_register


class TestCmdLoginRegister:
    def test_prints_result_as_json(self, capsys):
        result = {"client_id": "new-client", "client_secret": "secret123"}
        with patch("bfabric_scripts.cli.login.register.register_client", return_value=result):
            cmd_login_register(
                base_url="https://example.com/bfabric",
                token="bearer-tok",
                client_name="My App",
                redirect_uri="http://localhost/callback",
            )
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out
        assert '"client_secret": "secret123"' in output.out
        # Warning should be printed when passing token via flag
        assert "insecure" in output.err

    def test_error_handling(self, capsys):
        with patch("bfabric_scripts.cli.login.register.register_client", side_effect=RuntimeError("forbidden")):
            try:
                cmd_login_register(
                    base_url="https://example.com/bfabric",
                    token="bad-tok",
                    client_name="My App",
                    redirect_uri="http://localhost/callback",
                )
            except SystemExit as e:
                assert e.code == 1
        err = capsys.readouterr().err
        assert "forbidden" in err

    def test_prompts_when_token_omitted(self, capsys):
        result = {"client_id": "new-client", "client_secret": "secret123"}
        with (
            patch("bfabric_scripts.cli.login.register.register_client", return_value=result),
            patch("bfabric_scripts.cli.login.register.getpass.getpass", return_value="prompted-token") as mock_getpass,
        ):
            cmd_login_register(
                base_url="https://example.com/bfabric",
                client_name="My App",
                redirect_uri="http://localhost/callback",
            )
        mock_getpass.assert_called_once()
        output = capsys.readouterr()
        assert '"client_id": "new-client"' in output.out
