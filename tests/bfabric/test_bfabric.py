import datetime
import re
from pathlib import Path

import pytest
from pydantic import SecretStr

from bfabric import Bfabric, BfabricAPIEngineType, BfabricClientConfig, BfabricAuth
from bfabric.config.config_data import ConfigData
from bfabric.engine.engine_suds import EngineSUDS


@pytest.fixture
def mock_config():
    return BfabricClientConfig(engine=BfabricAPIEngineType.SUDS, base_url="https://example.com/api/")


@pytest.fixture
def mock_auth():
    return BfabricAuth(login="_test_user", password="y" * 32)


@pytest.fixture
def mock_engine(mocker):
    return mocker.MagicMock(name="mock_engine", spec=EngineSUDS)


@pytest.fixture
def bfabric_instance(mock_config, mock_engine):
    return Bfabric(config_data=ConfigData(client=mock_config, auth=None))


def test_from_config_when_no_args(mocker, mock_config, mock_auth):
    mock_get_system_auth = mocker.patch("bfabric.bfabric.get_system_auth")
    mock_engine_suds = mocker.patch("bfabric.bfabric.EngineSUDS")

    mock_get_system_auth.return_value = (mock_config, mock_auth)

    client = Bfabric.from_config()

    assert isinstance(client, Bfabric)
    assert client.config == mock_config
    assert client.auth == mock_auth
    mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)


def test_from_config_when_explicit_auth(mocker, mock_config, mock_auth):
    mock_get_system_auth = mocker.patch("bfabric.bfabric.get_system_auth")
    mock_engine_suds = mocker.patch("bfabric.bfabric.EngineSUDS")

    mock_config_auth = mocker.MagicMock(name="mock_config_auth")
    mock_get_system_auth.return_value = (mock_config, mock_config_auth)

    client = Bfabric.from_config(config_env="TestingEnv", auth=mock_auth)

    assert isinstance(client, Bfabric)
    assert client.config == mock_config
    assert client.auth == mock_auth
    mock_get_system_auth.assert_called_once_with(config_env="TestingEnv", config_path=None)


def test_from_config_when_none_auth(mocker, mock_config, mock_auth):
    mock_get_system_auth = mocker.patch("bfabric.bfabric.get_system_auth")
    mock_engine_suds = mocker.patch("bfabric.bfabric.EngineSUDS")

    mock_get_system_auth.return_value = (mock_config, mock_auth)

    client = Bfabric.from_config(config_env="TestingEnv", auth=None)

    assert isinstance(client, Bfabric)
    assert client.config == mock_config
    with pytest.raises(ValueError, match="Authentication not available"):
        _ = client.auth
    mock_get_system_auth.assert_called_once_with(config_env="TestingEnv", config_path=None)


def test_from_config_when_engine_suds(mocker, mock_config, mock_auth):
    mock_get_system_auth = mocker.patch("bfabric.bfabric.get_system_auth")

    mock_config = mocker.MagicMock(
        name="mock_config", engine=BfabricAPIEngineType.SUDS, spec=BfabricClientConfig, base_url="not_a_url"
    )
    mock_get_system_auth.return_value = (mock_config, mock_auth)

    client = Bfabric.from_config()

    assert isinstance(client, Bfabric)
    assert client.config == mock_config
    assert client.auth == mock_auth
    mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)


def test_from_config_when_engine_zeep(mocker, mock_auth):
    mock_get_system_auth = mocker.patch("bfabric.bfabric.get_system_auth")

    mock_config = mocker.MagicMock(
        name="mock_config", engine=BfabricAPIEngineType.ZEEP, spec=BfabricClientConfig, base_url="not_a_url"
    )
    mock_get_system_auth.return_value = (mock_config, mock_auth)

    client = Bfabric.from_config()

    assert isinstance(client, Bfabric)
    assert client.config == mock_config
    assert client.auth == mock_auth
    mock_get_system_auth.assert_called_once_with(config_env=None, config_path=None)


def test_from_token(mocker, mock_config):
    mock_load_config_data = mocker.patch(
        "bfabric.bfabric.load_config_data", return_value=ConfigData(client=mock_config, auth=None)
    )
    mock_get_token_data = mocker.patch(
        "bfabric.bfabric.get_token_data", return_value=mocker.MagicMock(user="test_user", user_ws_password="x" * 32)
    )
    mocker.patch.object(Bfabric, "_log_version_message")

    client, data = Bfabric.from_token(token="test_token")

    assert client.auth.login == "test_user"
    assert client.auth.password == SecretStr("x" * 32)
    assert data == mock_get_token_data.return_value

    mock_get_token_data.assert_called_once_with(client_config=mock_config, token="test_token")
    mock_load_config_data.assert_called_once_with(
        config_file_env="default", config_file_path=Path("~/.bfabricpy.yml"), include_auth=False
    )


def test_query_counter(bfabric_instance):
    assert bfabric_instance.query_counter == 0


def test_config(bfabric_instance, mock_config):
    assert bfabric_instance.config == mock_config


def test_auth_when_missing(bfabric_instance):
    with pytest.raises(ValueError, match="Authentication not available"):
        _ = bfabric_instance.auth


def test_auth_when_provided(mock_config, mock_engine, mock_auth):
    bfabric_instance = Bfabric(ConfigData(client=mock_config, auth=mock_auth))
    assert bfabric_instance.auth == mock_auth


def test_with_auth(mocker, bfabric_instance):
    mock_old_auth = mocker.MagicMock(name="mock_old_auth")
    mock_new_auth = mocker.MagicMock(name="mock_new_auth")
    bfabric_instance._auth = mock_old_auth

    with bfabric_instance.with_auth(mock_new_auth):
        assert bfabric_instance.auth == mock_new_auth

    assert bfabric_instance.auth == mock_old_auth


def test_with_auth_when_exception(mocker, bfabric_instance):
    mock_old_auth = mocker.MagicMock(name="mock_old_auth")
    mock_new_auth = mocker.MagicMock(name="mock_new_auth")
    bfabric_instance._auth = mock_old_auth

    with pytest.raises(ValueError, match="Test exception"):  # noqa
        with bfabric_instance.with_auth(mock_new_auth):
            raise ValueError("Test exception")

    assert bfabric_instance.auth == mock_old_auth


def test_read_when_no_pages_available_and_check(mocker, bfabric_instance):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_engine = mocker.patch.object(bfabric_instance, "_engine")
    mock_result = mocker.MagicMock(name="mock_result", total_pages_api=0, assert_success=mocker.MagicMock())
    mock_engine.read.return_value = mock_result

    result = bfabric_instance.read(endpoint="mock_endpoint", obj="mock_obj")

    assert result == mock_result.get_first_n_results.return_value
    mock_engine.read.assert_called_once_with(
        endpoint="mock_endpoint",
        obj="mock_obj",
        auth=mock_auth,
        page=1,
        return_id_only=False,
    )
    mock_result.assert_success.assert_called_once()
    mock_result.get_first_n_results.assert_called_once_with(100)


def test_read_when_pages_available_and_check(bfabric_instance, mocker):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_compute_requested_pages = mocker.patch("bfabric.bfabric.compute_requested_pages")
    mock_engine = mocker.patch.object(bfabric_instance, "_engine")

    mock_page_results = [
        mocker.MagicMock(
            name=f"mock_page_result_{i}",
            assert_success=mocker.MagicMock(),
            total_pages_api=3,
            errors=[],
        )
        for i in range(1, 4)
    ]
    mock_page_results[0].__getitem__.side_effect = lambda i: [1, 2, 3, 4, 5][i]
    mock_page_results[1].__getitem__.side_effect = lambda i: [6, 7, 8, 9, 10][i]
    mock_page_results[2].__getitem__.side_effect = lambda i: [11, 12, 13, 14, 15][i]

    mock_engine.read.side_effect = lambda **kwargs: mock_page_results[kwargs["page"] - 1]
    mock_compute_requested_pages.return_value = ([1, 2], 4)

    result = bfabric_instance.read(endpoint="mock_endpoint", obj="mock_obj")

    mock_compute_requested_pages.assert_called_once_with(
        n_page_total=3, n_item_per_page=100, n_item_offset=0, n_item_return_max=100
    )
    assert result.errors == []
    assert mock_engine.mock_calls == [
        mocker.call.read(
            endpoint="mock_endpoint",
            obj="mock_obj",
            auth=mock_auth,
            page=1,
            return_id_only=False,
        ),
        mocker.call.read(
            endpoint="mock_endpoint",
            obj="mock_obj",
            auth=mock_auth,
            page=2,
            return_id_only=False,
        ),
    ]
    assert len(result) == 6
    assert result[0] == 5
    assert result[5] == 10


def test_save_when_no_auth(bfabric_instance, mocker):
    mock_engine = mocker.patch.object(bfabric_instance, "_engine")

    with pytest.raises(ValueError, match="Authentication not available"):
        bfabric_instance.save("test_endpoint", {"key": "value"})

    mock_engine.save.assert_not_called()


def test_save_when_auth_and_check_false(bfabric_instance, mocker):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_engine = mocker.patch.object(bfabric_instance, "_engine")
    method_assert_success = mocker.MagicMock(name="method_assert_success")
    mock_engine.save.return_value.assert_success = method_assert_success

    result = bfabric_instance.save("test_endpoint", {"key": "value"}, check=False)

    assert result == mock_engine.save.return_value
    method_assert_success.assert_not_called()
    mock_engine.save.assert_called_once_with(
        endpoint="test_endpoint", obj={"key": "value"}, auth=mock_auth, method="save"
    )


def test_save_when_auth_and_check_true(bfabric_instance, mocker):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_engine = mocker.patch.object(bfabric_instance, "_engine")
    method_assert_success = mocker.MagicMock(name="method_assert_success")
    mock_engine.save.return_value.assert_success = method_assert_success

    result = bfabric_instance.save("test_endpoint", {"key": "value"})

    assert result == mock_engine.save.return_value
    method_assert_success.assert_called_once()
    mock_engine.save.assert_called_once_with(
        endpoint="test_endpoint", obj={"key": "value"}, auth=mock_auth, method="save"
    )


def test_delete_when_no_auth(bfabric_instance, mocker):
    mock_engine = mocker.patch.object(bfabric_instance, "_engine")

    with pytest.raises(ValueError, match="Authentication not available"):
        bfabric_instance.delete("test_endpoint", {"key": "value"})

    mock_engine.delete.assert_not_called()


def test_delete_when_auth_and_check_false(bfabric_instance, mocker):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_engine = mocker.patch.object(bfabric_instance, "_engine")
    method_assert_success = mocker.MagicMock(name="method_assert_success")
    mock_engine.delete.return_value.assert_success = method_assert_success

    result = bfabric_instance.delete(endpoint="test_endpoint", id=10, check=False)

    assert result == mock_engine.delete.return_value
    method_assert_success.assert_not_called()
    mock_engine.delete.assert_called_once_with(endpoint="test_endpoint", id=10, auth=mock_auth)


def test_delete_when_auth_and_check_true(bfabric_instance, mocker):
    mock_auth = mocker.MagicMock(name="mock_auth")
    bfabric_instance._auth = mock_auth

    mock_engine = mocker.patch.object(bfabric_instance, "_engine")
    method_assert_success = mocker.MagicMock(name="method_assert_success")
    mock_engine.delete.return_value.assert_success = method_assert_success

    result = bfabric_instance.delete(endpoint="test_endpoint", id=10)

    assert result == mock_engine.delete.return_value
    method_assert_success.assert_called_once()
    mock_engine.delete.assert_called_once_with(endpoint="test_endpoint", id=10, auth=mock_auth)


def test_exists_when_true(bfabric_instance, mocker):
    mock_read = mocker.patch.object(Bfabric, "read")
    mock_read.return_value.__len__.return_value = 1

    assert bfabric_instance.exists(endpoint="test_endpoint", key="key", value="value")

    mock_read.assert_called_once_with(
        endpoint="test_endpoint",
        obj={"key": "value"},
        max_results=1,
        check=True,
        return_id_only=True,
    )


def test_exists_when_true_and_extra_args(bfabric_instance, mocker):
    mock_read = mocker.patch.object(Bfabric, "read")
    mock_read.return_value.__len__.return_value = 1

    assert bfabric_instance.exists(
        endpoint="test_endpoint",
        key="key",
        value="value",
        query={"extra": "arg"},
        check=False,
    )

    mock_read.assert_called_once_with(
        endpoint="test_endpoint",
        obj={"key": "value", "extra": "arg"},
        max_results=1,
        check=False,
        return_id_only=True,
    )


def test_exists_when_false(bfabric_instance, mocker):
    mock_read = mocker.patch.object(Bfabric, "read")
    mock_read.return_value.__len__.return_value = 0

    assert not bfabric_instance.exists(endpoint="test_endpoint", key="key", value="value")

    mock_read.assert_called_once_with(
        endpoint="test_endpoint",
        obj={"key": "value"},
        max_results=1,
        check=True,
        return_id_only=True,
    )


def test_upload_resource(bfabric_instance, mocker):
    mock_save = mocker.patch.object(Bfabric, "save")

    resource_name = "hello_world.txt"
    content = b"Hello, World!"
    workunit_id = 123
    check = mocker.MagicMock(name="check")

    bfabric_instance.upload_resource(resource_name, content, workunit_id, check)

    mock_save.assert_called_once_with(
        endpoint="resource",
        obj={
            "base64": "SGVsbG8sIFdvcmxkIQ==",
            "workunitid": 123,
            "name": "hello_world.txt",
            "description": "base64 encoded file",
        },
        check=check,
    )


def test_get_version_message(mock_config, bfabric_instance):
    mock_config.base_url = "dummy_url"
    line1, line2 = bfabric_instance._get_version_message()
    pattern = r"bfabricPy v\d+\.\d+\.\d+ \(EngineSUDS, dummy_url, U=None, PY=\d\.\d+\.\d+\)"
    assert re.match(pattern, line1)
    year = datetime.datetime.now().year
    assert line2 == f"Copyright (C) 2014-{year} Functional Genomics Center Zurich"


def test_log_version_message(mocker, bfabric_instance):
    mocker.patch.object(Bfabric, "_get_version_message", return_value=("line1", "line2"))
    mock_logger = mocker.patch("bfabric.bfabric.logger")
    bfabric_instance._log_version_message()
    assert mock_logger.info.mock_calls == [mocker.call("line1"), mocker.call("line2")]
