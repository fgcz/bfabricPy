import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_order_fasta_specs import ResolveBfabricOrderFastaSpecs

from bfabric.entities import Workunit, Order


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricOrderFastaSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Mock the Order with a FASTA sequence
    mock_order = mocker.MagicMock(name="mock_order", spec=Order)
    mock_order.data_dict = {"fastasequence": "ACGT"}

    # Mock Workunit.find to return a workunit with our mock order
    mock_workunit = mocker.MagicMock(name="mock_workunit")
    mock_workunit.container = mock_order
    mocker.patch.object(Workunit, "find", return_value=mock_workunit)

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.id = 1
    mock_spec.entity = "workunit"
    mock_spec.filename = "test.fasta"
    mock_spec.required = True

    # Call the function under test
    result = resolver([mock_spec])

    # Assert the results
    assert len(result) == 1
    assert result[0].filename == "test.fasta"
    assert result[0].content == "ACGT"
    Workunit.find.assert_called_once_with(id=1, client=mock_client)


def test_call_when_empty(resolver):
    specs = []
    result = resolver(specs)
    assert result == []


def test_get_order_fasta_when_workunit(mocker, resolver, mock_client):
    # Mock the Order with a FASTA sequence
    mock_order = mocker.MagicMock(name="mock_order", spec=Order)
    mock_order.data_dict = {"fastasequence": "ACGT"}

    # Mock Workunit.find to return a workunit with our mock order
    mock_workunit = mocker.MagicMock(name="mock_workunit")
    mock_workunit.container = mock_order
    mocker.patch.object(Workunit, "find", return_value=mock_workunit)

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.id = 1
    mock_spec.entity = "workunit"
    mock_spec.required = True

    # Call the method under test
    result = resolver._get_order_fasta(mock_spec)

    # Assert the result
    assert result == "ACGT"
    Workunit.find.assert_called_once_with(id=1, client=mock_client)


def test_get_order_fasta_when_order(mocker, resolver, mock_client):
    # Mock the Order with a FASTA sequence
    mock_order = mocker.MagicMock(name="mock_order")
    mock_order.data_dict = {"fastasequence": "TAGC"}
    mocker.patch.object(Order, "find", return_value=mock_order)

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.id = 2
    mock_spec.entity = "order"

    # Call the method under test
    result = resolver._get_order_fasta(mock_spec)

    # Assert the result
    assert result == "TAGC"
    Order.find.assert_called_once_with(id=2, client=mock_client)
