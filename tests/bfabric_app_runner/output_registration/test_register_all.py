from pathlib import Path

import pytest
from bfabric.entities import Workunit
from bfabric_app_runner.output_registration.register import register_all
from bfabric_app_runner.specs.outputs_spec import CopyResourceSpec


def _resource(mocker, *, id: int, name: str, status: str):
    """A resource as `Workunit.resources` yields it: attribute `id`, item access for the rest."""
    resource = mocker.MagicMock(id=id)
    resource.__getitem__.side_effect = {"name": name, "status": status}.__getitem__
    return resource


class TestRegisterAll:
    """Output registration always creates a fresh resource, never recycling a pre-existing one.

    The workunit resources set up here are what the legacy WrapperCreator left behind: a `pending`
    placeholder output resource plus two `slurm_std*` log resources. Recycling the placeholder's id
    was the legacy `reuse_default_resource` behaviour, removed in #361.
    """

    @pytest.fixture()
    def spec(self, tmp_path) -> CopyResourceSpec:
        local_path = tmp_path / "result.txt"
        local_path.write_text("payload")
        return CopyResourceSpec(local_path=local_path, store_entry_path=Path("result.txt"))

    @pytest.fixture()
    def workunit_definition(self, mocker):
        wd = mocker.MagicMock()
        wd.registration.workunit_id = 5000
        wd.registration.storage_id = 2
        wd.registration.storage_output_folder = Path("out/folder")
        return wd

    @pytest.fixture()
    def client(self, mocker):
        """Client whose `reader.read_id` answers per entity type, with `resources` set by each test."""

        def read_id(entity_type, entity_id):
            entity = mocker.MagicMock()
            if entity_type is Workunit:
                entity.resources = client.workunit_resources
            return entity

        client = mocker.MagicMock()
        client.workunit_resources = []
        client.reader.read_id.side_effect = read_id
        client.reader.query_one.return_value = None
        return client

    @pytest.fixture(autouse=True)
    def _mock_transfer(self, mocker):
        mocker.patch("bfabric_app_runner.output_registration.register.copy_file_to_storage")
        mocker.patch("bfabric_app_runner.output_registration.register.md5_checksum", return_value="checksum")

    @pytest.mark.parametrize(
        "resource_names_and_status",
        [
            pytest.param([], id="no_existing_resources"),
            pytest.param([("App 1 - resource", "pending")], id="legacy_placeholder_only"),
            pytest.param(
                [("App 1 - resource", "pending"), ("slurm_stdout", "available"), ("slurm_stderr", "available")],
                id="legacy_placeholder_with_log_resources",
            ),
            pytest.param([("earlier.txt", "available")], id="resource_created_by_the_app"),
        ],
    )
    def test_registers_a_new_resource(self, client, workunit_definition, spec, mocker, resource_names_and_status):
        client.workunit_resources = [
            _resource(mocker, id=100 + index, name=name, status=status)
            for index, (name, status) in enumerate(resource_names_and_status)
        ]

        register_all(
            client=client,
            workunit_definition=workunit_definition,
            specs_list=[spec],
            ssh_user=None,
            force_storage=None,
        )

        endpoint, resource_data = client.save.call_args.args
        assert endpoint == "resource"
        assert "id" not in resource_data
        assert resource_data["name"] == "result.txt"
        assert resource_data["workunitid"] == 5000
        assert resource_data["relativepath"] == "out/folder/result.txt"
        assert resource_data["status"] == "available"
