import pytest
from pydantic import SecretStr

from bfabric.rest.token_data import TokenData


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
        environment="mock",
    )


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
