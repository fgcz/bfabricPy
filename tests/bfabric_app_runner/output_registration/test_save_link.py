import pytest

from bfabric.results.result_container import ResultContainer
from bfabric_app_runner.output_registration.register import _save_link
from bfabric_app_runner.specs.outputs_spec import SaveLinkSpec, UpdateExisting


@pytest.fixture()
def mock_client(mocker):
    return mocker.MagicMock()


@pytest.fixture()
def mock_workunit_definition(mocker):
    mock = mocker.MagicMock()
    mock.registration.workunit_id = 42
    return mock


@pytest.fixture()
def spec():
    return SaveLinkSpec(name="test_link", url="https://example.com", entity_type="Workunit")


def test_save_link_no_existing(mock_client, mock_workunit_definition, spec):
    """Test that _save_link works when no existing link is found."""
    mock_client.read.return_value = ResultContainer(results=[], total_pages_api=None, errors=[])
    mock_client.save.return_value = ResultContainer(results=[{"id": 123}], total_pages_api=None, errors=[])

    _save_link(spec, mock_client, mock_workunit_definition)

    mock_client.save.assert_called_once()
    saved_data = mock_client.save.call_args[0][1]
    assert saved_data["name"] == "test_link"
    assert saved_data["url"] == "https://example.com"
    assert saved_data["parentid"] == 42
    assert saved_data["parentclassname"] == "Workunit"


def test_save_link_existing_with_no_raises(mock_client, mock_workunit_definition):
    """An existing link with update_existing=NO must raise before saving."""
    spec = SaveLinkSpec(
        name="test_link", url="https://example.com", entity_type="Workunit", update_existing=UpdateExisting.NO
    )
    mock_client.read.return_value = ResultContainer(results=[{"id": 7}], total_pages_api=None, errors=[])

    with pytest.raises(ValueError, match="already exists"):
        _save_link(spec, mock_client, mock_workunit_definition)

    mock_client.save.assert_not_called()


def test_save_link_missing_with_required_raises(mock_client, mock_workunit_definition):
    """A missing link with update_existing=REQUIRED must raise before saving."""
    spec = SaveLinkSpec(
        name="test_link", url="https://example.com", entity_type="Workunit", update_existing=UpdateExisting.REQUIRED
    )
    mock_client.read.return_value = ResultContainer(results=[], total_pages_api=None, errors=[])

    with pytest.raises(ValueError, match="does not exist"):
        _save_link(spec, mock_client, mock_workunit_definition)

    mock_client.save.assert_not_called()
