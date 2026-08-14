import pytest
import yaml
from bfabric_app_runner.legacy.wrapper_yaml import build_legacy_wrapper_yaml

from bfabric.entities import Application, Dataset, Executable, Order, Project, Resource, Storage, Workunit


def _entity(mocker, cls, entity_id, data):
    """A MagicMock that passes ``isinstance`` for ``cls`` and supports ``entity[key]`` / ``.data_dict``."""
    entity = mocker.MagicMock(spec=cls, name=f"{cls.__name__}{entity_id}")
    entity.id = entity_id
    entity.data_dict = dict(data)
    entity.__getitem__.side_effect = data.__getitem__
    entity.uri = f"https://bfabric.example.com/bfabric/{cls.__name__.lower()}/show.html?id={entity_id}"
    return entity


@pytest.fixture
def mock_input_resources(mocker):
    """Two resources produced by the same upstream application, as a resource-flow workunit would have."""
    producer = _entity(mocker, Workunit, 100, {"name": "upstream"})
    producer.application = _entity(mocker, Application, 20, {"name": "QEXACTIVEHFX_1"})
    storage = _entity(mocker, Storage, 2, {"host": "fgcz-ms.uzh.ch", "basepath": "/srv/www/htdocs/"})
    storage.scp_prefix = "fgcz-ms.uzh.ch:/srv/www/htdocs/"

    resources = []
    for resource_id, relative_path in [(720983, "p2621/first.raw"), (720984, "p2621/second.raw")]:
        resource = _entity(mocker, Resource, resource_id, {"relativepath": relative_path})
        resource.workunit = producer
        resource.storage = storage
        resources.append(resource)
    return resources


@pytest.fixture
def mock_order(mocker):
    order = _entity(mocker, Order, 4854, {"fastasequence": ">seq\rACGT\r"})
    order.project = _entity(mocker, Project, 2621, {})
    return order


@pytest.fixture
def mock_workunit(mocker, mock_input_resources, mock_order):
    workunit = _entity(mocker, Workunit, 181492, {"createdby": "lkunz", "name": "the workunit"})
    workunit.application = _entity(mocker, Application, 224, {"name": "MaxQuant"})
    workunit.application.executable = _entity(
        mocker, Executable, 11851, {"program": "/home/bfabric/sgeworker/bin/fgcz_sge_maxquant_linux.bash"}
    )
    workunit.application_parameters = {"/numThreads": "48", "Rmd": None}
    workunit.input_resources.list = mock_input_resources
    workunit.input_dataset = None
    workunit.container = mock_order
    return workunit


@pytest.fixture
def mock_client(mocker, mock_workunit):
    client = mocker.MagicMock(name="mock_client")
    client.reader.read_id.return_value = mock_workunit
    return client


@pytest.fixture
def config(mock_client):
    return build_legacy_wrapper_yaml(
        client=mock_client, workunit_id=181492, output_path="/work/WU181492/work/result.zip"
    )


class TestApplicationSection:
    def test_parameters_replace_none_with_empty_string(self, config):
        assert config["application"]["parameters"] == {"/numThreads": "48", "Rmd": ""}

    def test_protocol(self, config):
        assert config["application"]["protocol"] == "scp"

    def test_input_groups_scp_urls_by_producing_application(self, config):
        assert config["application"]["input"] == {
            "QEXACTIVEHFX_1": [
                "bfabric@fgcz-ms.uzh.ch:/srv/www/htdocs/p2621/first.raw",
                "bfabric@fgcz-ms.uzh.ch:/srv/www/htdocs/p2621/second.raw",
            ]
        }

    def test_output_is_the_requested_path(self, config):
        assert config["application"]["output"] == ["/work/WU181492/work/result.zip"]


class TestJobConfigurationSection:
    def test_executable_defaults_to_the_application_program(self, config):
        assert config["job_configuration"]["executable"] == "/home/bfabric/sgeworker/bin/fgcz_sge_maxquant_linux.bash"

    def test_executable_override(self, mock_client):
        config = build_legacy_wrapper_yaml(
            client=mock_client, workunit_id=181492, output_path="/out.zip", executable="/opt/legacy.bash"
        )
        assert config["job_configuration"]["executable"] == "/opt/legacy.bash"

    def test_input_groups_ids_and_uris_by_producing_application(self, config):
        assert config["job_configuration"]["input"] == {
            "QEXACTIVEHFX_1": [
                {
                    "resource_id": 720983,
                    "resource_url": "https://bfabric.example.com/bfabric/resource/show.html?id=720983",
                },
                {
                    "resource_id": 720984,
                    "resource_url": "https://bfabric.example.com/bfabric/resource/show.html?id=720984",
                },
            ]
        }

    def test_fastasequence_normalises_carriage_returns(self, config):
        assert config["job_configuration"]["fastasequence"] == ">seq\nACGT\n"

    def test_workunit_fields(self, config):
        assert config["job_configuration"]["workunit_id"] == 181492
        assert config["job_configuration"]["workunit_createdby"] == "lkunz"
        assert (
            config["job_configuration"]["workunit_url"]
            == "https://bfabric.example.com/bfabric/workunit/show.html?id=181492"
        )

    def test_output_carries_no_resource(self, config):
        assert config["job_configuration"]["output"] == {"protocol": "file", "resource_id": 0, "ssh_args": ""}

    def test_log_sections_carry_no_resource(self, config):
        expected = {"protocol": "file", "resource_id": 0, "url": "/dev/null"}
        assert config["job_configuration"]["stdout"] == expected
        assert config["job_configuration"]["stderr"] == expected

    def test_external_job_id_is_a_sentinel(self, config):
        """There is no external job under app-runner, but ``0`` keeps a ``set -u`` consumer working."""
        assert config["job_configuration"]["external_job_id"] == 0


class TestContainer:
    def test_order_container_reports_order_and_its_project(self, config):
        assert config["job_configuration"]["order_id"] == 4854
        assert config["job_configuration"]["project_id"] == 2621

    def test_order_without_project(self, mock_client, mock_order, config_of):
        mock_order.project = None
        config = config_of(mock_client)
        assert config["job_configuration"]["order_id"] == 4854
        assert config["job_configuration"]["project_id"] is None

    def test_project_container(self, mocker, mock_client, mock_workunit, config_of):
        mock_workunit.container = _entity(mocker, Project, 2621, {})
        config = config_of(mock_client)
        assert config["job_configuration"]["order_id"] is None
        assert config["job_configuration"]["project_id"] == 2621
        assert config["job_configuration"]["fastasequence"] == ""

    def test_container_that_is_neither(self, mocker, mock_client, mock_workunit, config_of):
        """The legacy implementation raised AttributeError here."""
        mock_workunit.container = _entity(mocker, Dataset, 5, {})
        config = config_of(mock_client)
        assert config["job_configuration"]["order_id"] is None
        assert config["job_configuration"]["project_id"] is None


class TestInputDataset:
    def test_absent(self, config):
        assert config["job_configuration"]["inputdataset"] is None

    def test_present(self, mocker, mock_client, mock_workunit, config_of):
        mock_workunit.input_dataset = _entity(mocker, Dataset, 77, {"name": "the dataset"})
        config = config_of(mock_client)
        assert config["job_configuration"]["inputdataset"] == {"_id": 77, "name": "the dataset"}


@pytest.fixture
def config_of():
    def build(client):
        return build_legacy_wrapper_yaml(client=client, workunit_id=181492, output_path="/out.zip")

    return build


def test_missing_workunit(mock_client):
    mock_client.reader.read_id.return_value = None
    with pytest.raises(ValueError, match="Workunit 181492 does not exist"):
        build_legacy_wrapper_yaml(client=mock_client, workunit_id=181492, output_path="/out.zip")


def test_input_resource_on_non_scp_storage(mock_client, mock_input_resources, config_of):
    """Interpolating a None scp prefix would produce a URL that only fails once the app runs."""
    mock_input_resources[0].storage.scp_prefix = None
    with pytest.raises(ValueError, match="is not scp-accessible"):
        config_of(mock_client)


def test_serialization_has_no_yaml_aliases(config):
    """stdout and stderr must be distinct dicts, or safe_dump emits an anchor the legacy parsers choke on."""
    serialized = yaml.safe_dump(config)
    assert "&id" not in serialized
    assert "*id" not in serialized


def test_top_level_keys(config):
    assert set(config) == {"application", "job_configuration"}
