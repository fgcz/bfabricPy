from unittest.mock import MagicMock

import pytest
import zeep
from pydantic import SecretStr

from bfabric.engine.engine_zeep import EngineZeep, _zeep_query_append_skipped
from bfabric.errors import BfabricRequestError
from bfabric.results.result_container import ResultContainer


@pytest.fixture
def engine_zeep():
    return EngineZeep(base_url="http://example.com/api")


@pytest.fixture
def mock_auth():
    return MagicMock(login="test_user", password=SecretStr("test_pass"))


@pytest.fixture
def mock_zeep_client():
    return MagicMock(spec=zeep.Client, settings=MagicMock())


def test_read(engine_zeep, mock_auth, mock_zeep_client, mocker):
    mocker.patch.object(engine_zeep, "_get_client", return_value=mock_zeep_client)
    mock_convert = mocker.patch.object(engine_zeep, "_convert_results")

    obj = {"field1": "value1"}
    engine_zeep.read("sample", obj, mock_auth)

    expected_query = {
        "login": "test_user",
        "page": 1,
        "password": "test_pass",
        "query": {
            "field1": "value1",
            "includedeletableupdateable": False,
            "includefamily": zeep.xsd.SkipValue,
            "includeassociations": zeep.xsd.SkipValue,
            "includeplates": zeep.xsd.SkipValue,
            "includeresources": zeep.xsd.SkipValue,
            "includeruns": zeep.xsd.SkipValue,
            "includechildren": zeep.xsd.SkipValue,
            "includeparents": zeep.xsd.SkipValue,
            "includereplacements": zeep.xsd.SkipValue,
        },
        "idonly": False,
    }
    mock_zeep_client.service.read.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_save(engine_zeep, mock_auth, mock_zeep_client, mocker):
    mocker.patch.object(engine_zeep, "_get_client", return_value=mock_zeep_client)
    mock_convert = mocker.patch.object(engine_zeep, "_convert_results")

    obj = {"field1": "value1"}
    engine_zeep.save("resource", obj, mock_auth)

    expected_query = {
        "login": "test_user",
        "password": "test_pass",
        "resource": {
            "field1": "value1",
            "name": zeep.xsd.SkipValue,
            "sampleid": zeep.xsd.SkipValue,
            "storageid": zeep.xsd.SkipValue,
            "workunitid": zeep.xsd.SkipValue,
            "relativepath": zeep.xsd.SkipValue,
        },
    }
    mock_zeep_client.service.save.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_save_method_not_found(engine_zeep, mock_auth, mock_zeep_client, mocker):
    mocker.patch.object(engine_zeep, "_get_client", return_value=mock_zeep_client)
    mock_zeep_client.service.save.side_effect = AttributeError("Service has no operation 'save'")

    with pytest.raises(
        BfabricRequestError,
        match="ZEEP failed to find save method for the sample endpoint.",
    ):
        engine_zeep.save("sample", {}, mock_auth)


def test_delete(engine_zeep, mock_auth, mock_zeep_client, mocker):
    mocker.patch.object(engine_zeep, "_get_client", return_value=mock_zeep_client)
    mock_convert = mocker.patch.object(engine_zeep, "_convert_results")

    engine_zeep.delete("sample", 123, mock_auth)

    expected_query = {"login": "test_user", "password": "test_pass", "id": 123}
    mock_zeep_client.service.delete.assert_called_once_with(expected_query)
    mock_convert.assert_called_once()


def test_delete_empty_list(engine_zeep, mock_auth, mock_zeep_client, mocker):
    mocker.patch.object(engine_zeep, "_get_client", return_value=mock_zeep_client)

    result = engine_zeep.delete("sample", [], mock_auth)

    assert isinstance(result, ResultContainer)
    assert result.results == []
    assert result.total_pages_api == 0
    mock_zeep_client.service.delete.assert_not_called()


def test_get_client(engine_zeep, mocker):
    mock_zeep_client = mocker.patch("zeep.Client", return_value=MagicMock(spec=zeep.Client))

    client = engine_zeep._get_client("sample")

    assert client == mock_zeep_client.return_value
    mock_zeep_client.assert_called_once_with("http://example.com/api/sample?wsdl")

    # Test caching
    client2 = engine_zeep._get_client("sample")
    assert client2 == client
    mock_zeep_client.assert_called_once()  # Should not be called again


def test_convert_results(engine_zeep, mocker):
    mock_serialize_object = mocker.patch("bfabric.engine.engine_zeep.serialize_object")
    mock_clean_result = mocker.patch("bfabric.engine.engine_zeep.clean_result")

    mock_response = MagicMock()
    mock_response.sample = [MagicMock(), MagicMock()]
    mock_response.__getitem__.side_effect = {
        "sample": mock_response.sample,
        "numberofpages": 2,
    }.__getitem__

    mock_serialize_object.side_effect = [{"result1": "value1"}, {"result2": "value2"}]
    mock_clean_result.side_effect = lambda x, **kwargs: x

    result = engine_zeep._convert_results(mock_response, "sample")

    assert isinstance(result, ResultContainer)
    assert result.results == [{"result1": "value1"}, {"result2": "value2"}]
    assert result.total_pages_api == 2
    assert mock_serialize_object.call_count == 2
    assert mock_clean_result.call_count == 2


def test_convert_results_no_results(engine_zeep):
    mock_response = MagicMock()
    mock_response.__getitem__.side_effect = {"numberofpages": 0}.__getitem__
    del mock_response.sample

    result = engine_zeep._convert_results(mock_response, "sample")

    assert isinstance(result, ResultContainer)
    assert result.results == []
    assert result.total_pages_api == 0


def test_zeep_query_append_skipped():
    query = {"existing": "value"}
    skipped_keys = ["key1", "key2"]

    result = _zeep_query_append_skipped(query, skipped_keys)

    assert result == {
        "existing": "value",
        "key1": zeep.xsd.SkipValue,
        "key2": zeep.xsd.SkipValue,
    }
    assert query == {"existing": "value"}  # Original query should be unchanged

    result_inplace = _zeep_query_append_skipped(query, skipped_keys, inplace=True)
    assert result_inplace == {
        "existing": "value",
        "key1": zeep.xsd.SkipValue,
        "key2": zeep.xsd.SkipValue,
    }
    assert query == result_inplace  # Original query should be changed

    query_with_existing = {"key1": "value1", "key2": "value2"}
    result_no_overwrite = _zeep_query_append_skipped(query_with_existing, skipped_keys)
    assert result_no_overwrite == query_with_existing

    result_overwrite = _zeep_query_append_skipped(query_with_existing, skipped_keys, overwrite=True)
    assert result_overwrite == {"key1": zeep.xsd.SkipValue, "key2": zeep.xsd.SkipValue}


if __name__ == "__main__":
    pytest.main()
