from typing import Any

import pytest
import requests
from pydantic import SecretStr

from bfabric.rest.token_data import TokenData, get_token_data, get_raw_token_data


@pytest.fixture
def base_url() -> str:
    return "https://example.com/mock-base-url"


@pytest.fixture
def token_data() -> TokenData:
    return TokenData(
        job_id=1,
        application_id=2,
        entity_class=" Dataset",
        entity_id=3,
        user="illegal_mock_user ",
        user_ws_password="password",
        token_expires="2023-10-01T00:00:00Z",
        caller="https://example.com/mock-caller",
        environment="mock",
    )


@pytest.fixture
def token_data_json() -> dict[str, Any]:
    return {
        "jobId": 1,
        "applicationId": 2,
        "entityClassName": "Dataset",
        "entityId": 3,
        "user": "illegal_mock_user ",
        "userWsPassword": "password",
        "expiryDateTime": "2023-10-01T00:00:00Z",
        "environment": "mock",
        "caller": "https://example.com/mock-caller",
    }


def test_str_strip_whitespace(token_data):
    assert token_data.entity_class == "Dataset"
    assert token_data.user == "illegal_mock_user"


def test_secret_password(token_data):
    assert token_data.user_ws_password.get_secret_value() == "password"


def test_model_dump(token_data):
    dumped = token_data.model_dump()
    assert dumped["job_id"] == 1
    assert dumped["application_id"] == 2
    assert dumped["entity_class"] == "Dataset"
    assert dumped["entity_id"] == 3
    assert dumped["user"] == "illegal_mock_user"
    assert dumped["user_ws_password"] == SecretStr("password")
    assert dumped["token_expires"] == "2023-10-01T00:00:00+00:00"
    assert dumped["environment"] == "mock"


def test_load_entity(mocker, token_data):
    mock_client = mocker.Mock(name="mock_client")
    mock_import_entity = mocker.patch("bfabric.rest.token_data.import_entity")
    entity = token_data.load_entity(client=mock_client)
    assert entity == mock_import_entity.return_value.find.return_value
    mock_import_entity.assert_called_once_with(entity_class_name=token_data.entity_class)
    mock_import_entity.return_value.find.assert_called_once_with(token_data.entity_id, client=mock_client)


def test_get_raw_token_data(mocker, token_data_json, base_url):
    mock_response = mocker.Mock(ok=True, json=lambda: token_data_json)
    mock_requests_get = mocker.patch("requests.get", return_value=mock_response)

    result = get_raw_token_data(base_url=base_url, token="mock-token")
    assert result == token_data_json
    mock_requests_get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})


def test_get_raw_token_data_when_response_error(mocker, base_url):
    mock_requests_get = mocker.patch("requests.get", side_effect=requests.HTTPError("Mocked HTTP error"))
    with pytest.raises(requests.HTTPError):
        get_raw_token_data(base_url=base_url, token="mock-token")
    mock_requests_get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})


def test_get_raw_token_data_when_json_decode_error(mocker, base_url):
    mock_response = mocker.Mock(ok=True, text="Mocked JSON decode error")
    mock_response.json.side_effect = requests.JSONDecodeError("mocked", "mocked", 0)
    mock_requests_get = mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(RuntimeError, match="Get token data failed with message: 'Mocked JSON decode error'"):
        get_raw_token_data(base_url=base_url, token="mock-token")

    mock_requests_get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})


def test_get_token_data(mocker, token_data_json, token_data, base_url):
    mock_get_raw_token_data = mocker.patch("bfabric.rest.token_data.get_raw_token_data", return_value=token_data_json)
    result = get_token_data(base_url=base_url, token="mock-token")
    assert token_data == result
    mock_get_raw_token_data.assert_called_once_with(base_url=base_url, token="mock-token")
