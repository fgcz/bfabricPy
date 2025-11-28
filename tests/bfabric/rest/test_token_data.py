from typing import Any
from json import JSONDecodeError

import pytest
import httpx
from pydantic import SecretStr

from bfabric.rest.token_data import TokenData, get_token_data, get_token_data_async


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


@pytest.mark.parametrize("extra_slash", ["", "/"])
@pytest.mark.asyncio
async def test_get_token_data_async(mocker, token_data_json, token_data, base_url, extra_slash: str):
    mock_response = mocker.Mock()
    mock_response.json.return_value = token_data_json
    mock_response.raise_for_status = mocker.Mock()

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response

    result = await get_token_data_async(
        base_url=f"{base_url}{extra_slash}", token="mock-token", http_client=mock_client
    )

    assert result == token_data
    mock_client.get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_get_token_data_async_when_response_error(mocker, base_url):
    mock_response = mocker.Mock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Mocked HTTP error", request=mocker.Mock(), response=mocker.Mock()
    )

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(httpx.HTTPStatusError):
        await get_token_data_async(base_url=base_url, token="mock-token", http_client=mock_client)

    mock_client.get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})


@pytest.mark.asyncio
async def test_get_token_data_async_when_json_decode_error(mocker, base_url):
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_response.json.side_effect = JSONDecodeError("mocked", "mocked", 0)

    mock_client = mocker.AsyncMock()
    mock_client.get.return_value = mock_response

    with pytest.raises(JSONDecodeError):
        await get_token_data_async(base_url=base_url, token="mock-token", http_client=mock_client)

    mock_client.get.assert_called_once_with(f"{base_url}/rest/token/validate", params={"token": "mock-token"})


def test_get_token_data(mocker, token_data, base_url):
    mock_get_token_data_async = mocker.patch("bfabric.rest.token_data.get_token_data_async", return_value=token_data)
    result = get_token_data(base_url=base_url, token="mock-token")
    assert token_data == result
    mock_get_token_data_async.assert_called_once()
    # Verify the call arguments (base_url and token)
    call_args = mock_get_token_data_async.call_args
    assert call_args.kwargs["base_url"] == base_url
    assert call_args.kwargs["token"] == "mock-token"
