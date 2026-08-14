from __future__ import annotations

import pytest

from bfabric_scripts.cli.login.register_webapp import cmd_login_register_webapp


class TestCmdLoginRegisterWebapp:
    def test_requires_service_user_choice(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(app_name="My App", web_url="http://localhost:8060")
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "--service-user" in err
        assert "--no-service-user" in err

    def test_rejects_service_user_and_no_service_user_together(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                service_user="trace",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "mutually exclusive" in err

    def test_no_service_user_passes_validation(self, mocker, capsys):
        mocker.patch(
            "bfabric.Bfabric.connect",
            side_effect=RuntimeError("connect failed"),
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                no_service_user=True,
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Could not connect to B-Fabric" in err

    def test_service_user_passes_validation(self, mocker, capsys):
        mocker.patch(
            "bfabric.Bfabric.connect",
            side_effect=RuntimeError("connect failed"),
        )
        with pytest.raises(SystemExit) as exc_info:
            cmd_login_register_webapp(
                app_name="My App",
                web_url="http://localhost:8060",
                service_user="trace",
            )
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "Could not connect to B-Fabric" in err
