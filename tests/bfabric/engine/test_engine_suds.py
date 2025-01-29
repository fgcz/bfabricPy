from unittest.mock import MagicMock

import pytest
from suds import MethodNotFound
from suds.client import Client

from bfabric.engine.engine_suds import EngineSUDS
from bfabric.errors import BfabricRequestError
from bfabric.results.result_container import ResultContainer


@pytest.fixture
def engine_suds():
    return EngineSUDS(base_url="http://example.com/api")


@pytest.fixture
def mock_auth():
    return MagicMock(login="test_user", password="test_pass")


@pytest.fixture
def mock_suds_service():
    return MagicMock()


@pytest.fixture
def mock_client(mock_suds_service):
    mock_client = MagicMock(spec=Client)
    mock_client.service = mock_suds_service
    return mock_client


def test_read(engine_suds, mock_auth, mock_suds_service, mocker):
    mocker.patch.object(
        engine_suds, "_get_suds_service", return_value=mock_suds_service
    )
    mock_convert = mocker.patch.object(engine_suds, "_convert_results")

    obj = {"field1": "value1"}
    engine_suds.read("sample", obj, mock_auth)

    expected_query = {
        "login": "test_user",
        "page": 1,
        "password": "test_pass",
        "query": {"field1": "value1", "includedeletableupdateable": False},
        "idonly": False,
    }
    mock_suds_service.read.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_save(engine_suds, mock_auth, mock_suds_service, mocker):
    mocker.patch.object(
        engine_suds, "_get_suds_service", return_value=mock_suds_service
    )
    mock_convert = mocker.patch.object(engine_suds, "_convert_results")

    obj = {"field1": "value1"}
    engine_suds.save("sample", obj, mock_auth)

    expected_query = {
        "login": "test_user",
        "password": "test_pass",
        "sample": {"field1": "value1"},
    }
    mock_suds_service.save.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_save_method_not_found(engine_suds, mock_auth, mock_suds_service, mocker):
    mocker.patch.object(
        engine_suds, "_get_suds_service", return_value=mock_suds_service
    )
    mock_suds_service.save.side_effect = MethodNotFound("save")

    with pytest.raises(
        BfabricRequestError,
        match="SUDS failed to find save method for the sample endpoint.",
    ):
        engine_suds.save("sample", {}, mock_auth)


def test_delete(engine_suds, mock_auth, mock_suds_service, mocker):
    mocker.patch.object(
        engine_suds, "_get_suds_service", return_value=mock_suds_service
    )
    mock_convert = mocker.patch.object(engine_suds, "_convert_results")

    engine_suds.delete("sample", 123, mock_auth)

    expected_query = {"login": "test_user", "password": "test_pass", "id": 123}
    mock_suds_service.delete.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_delete_empty_list(engine_suds, mock_auth, mock_suds_service, mocker):
    mocker.patch.object(
        engine_suds, "_get_suds_service", return_value=mock_suds_service
    )

    result = engine_suds.delete("sample", [], mock_auth)

    assert isinstance(result, ResultContainer)
    assert result.results == []
    assert result.total_pages_api == 0
    mock_suds_service.delete.assert_not_called()


def test_get_suds_service(engine_suds, mock_client, mocker):
    mock_client_init = mocker.patch(
        "bfabric.engine.engine_suds.Client", return_value=mock_client
    )

    service = engine_suds._get_suds_service("sample")

    assert service == mock_client.service
    mock_client_init.assert_called_once_with(
        "http://example.com/api/sample?wsdl", cache=None
    )

    # Test caching
    service2 = engine_suds._get_suds_service("sample")
    assert service2 == service
    mock_client_init.assert_called_once()  # Should not be called again


def test_convert_results(engine_suds, mocker):
    mock_suds_asdict = mocker.patch("bfabric.engine.engine_suds.suds_asdict_recursive")
    mock_clean_result = mocker.patch("bfabric.engine.engine_suds.clean_result")

    mock_response = MagicMock()
    mock_response.sample = [MagicMock(), MagicMock()]
    mock_response.__getitem__.side_effect = {
        "sample": mock_response.sample,
        "numberofpages": 2,
    }.__getitem__

    mock_suds_asdict.side_effect = [{"result1": "value1"}, {"result2": "value2"}]
    mock_clean_result.side_effect = lambda x, **kwargs: x

    result = engine_suds._convert_results(mock_response, "sample")

    assert isinstance(result, ResultContainer)
    assert result.results == [{"result1": "value1"}, {"result2": "value2"}]
    assert result.total_pages_api == 2
    assert mock_suds_asdict.call_count == 2
    assert mock_clean_result.call_count == 2


def test_convert_results_no_results(engine_suds):
    mock_response = MagicMock()
    mock_response.numberofpages = 0
    del mock_response.sample

    result = engine_suds._convert_results(mock_response, "sample")

    assert isinstance(result, ResultContainer)
    assert result.results == []
    assert result.total_pages_api == 0


if __name__ == "__main__":
    pytest.main()
