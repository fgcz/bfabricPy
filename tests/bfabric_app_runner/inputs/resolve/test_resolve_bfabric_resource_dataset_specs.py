import polars as pl
import pytest
from inline_snapshot import snapshot
import polars.testing
from bfabric.entities import Dataset, Resource
from bfabric_app_runner.inputs.resolve._resolve_bfabric_resource_dataset_specs import ResolveBfabricResourceDatasetSpecs
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile, ResolvedStaticFile
from bfabric_app_runner.specs.inputs.bfabric_resource_dataset import BfabricResourceDatasetSpec
from bfabric_app_runner.specs.inputs.file_spec import FileSourceSsh, FileSourceSshValue


@pytest.fixture
def scenario(request):
    if request.param in ("minimal", "complex", "complex_output_column_conflict", "dataset_only"):
        return request.param
    raise NotImplementedError


@pytest.fixture
def original_dataset_df(scenario):
    if scenario in ("minimal", "dataset_only"):
        return pl.DataFrame({"Resource": [10, 11, 12]})
    elif scenario in ("complex", "complex_output_column_conflict"):
        return pl.DataFrame({"Resource": [10, 11, 12], "OtherColumn": [20, 21, 22]})


@pytest.fixture(autouse=True)
def original_dataset(mocker, original_dataset_df):
    dataset = mocker.MagicMock(nmae="original_dataset_entity", spec=["to_polars"])
    dataset.to_polars.return_value = original_dataset_df
    mocker.patch.object(Dataset, "find").return_value = dataset
    return dataset


@pytest.fixture
def storage(mocker):
    result = mocker.MagicMock(name="storage", spec=["__getitem__"])
    result.__getitem__.side_effect = lambda key: {"host": "storage_host"}[key]
    return result


@pytest.fixture(autouse=True)
def original_resources(mocker, storage):
    resources = []
    for i in range(10, 13):
        resource = mocker.MagicMock(
            name=f"resource_{i}",
            spec=["id", "filename", "storage_relative_path", "storage_absolute_path", "__getitem__"],
        )
        resource.id = i
        resource.filename = f"file_{i}.txt"
        resource.storage_relative_path = f"path/to/file_{i}.txt"
        resource.storage_absolute_path = f"/base/path/path/to/file_{i}.txt"
        resource.storage = storage
        attrs = {"filechecksum": f"checksum_{i}"}
        resource.__getitem__.side_effect = lambda key, _attrs=attrs: _attrs[key]
        resources.append(resource)

    def mock_find_all(ids, client):
        return {r.id: r for r in resources if r.id in ids}

    mocker.patch.object(Resource, "find_all").side_effect = mock_find_all
    return resources


@pytest.fixture
def spec(scenario):
    return BfabricResourceDatasetSpec(
        id=1,
        filename="files",
        **({} if scenario != "complex_output_column_conflict" else {"output_dataset_file_column": "OtherColumn"}),
        output_dataset_only=(scenario == "dataset_only"),
    )


@pytest.fixture
def client(mocker):
    return mocker.MagicMock(name="client", spec=[])


@pytest.fixture
def resolver(client):
    return ResolveBfabricResourceDatasetSpecs(client=client)


class TestInternals:
    """Testing internals, in principle can be deleted but might help for diagnostics."""

    @pytest.mark.parametrize("scenario", ["minimal", "complex"], indirect=True)
    def test_resolve_unfiltered_dataset(self, resolver, spec, scenario):
        dataset = resolver._resolve_unfiltered_dataset(spec=spec)
        assert dataset.columns == [
            "Resource",
            *([] if scenario == "minimal" else ["OtherColumn"]),
            "tmp_resource_filename",
            "tmp_resource_checksum",
            "tmp_resource_relative_path",
            "tmp_resource_source",
        ]
        assert dataset.row(0) == (
            10,
            *([] if scenario == "minimal" else [20]),
            "file_10.txt",
            "checksum_10",
            "path/to/file_10.txt",
            FileSourceSsh(ssh=FileSourceSshValue(host="storage_host", path="/base/path/path/to/file_10.txt")),
        )


class TestResolveSpec:
    @pytest.fixture()
    def result(self, resolver, spec):
        return resolver(specs=[spec])

    @pytest.mark.parametrize("scenario", ["minimal", "complex"], indirect=True)
    def test_result_len(self, result):
        assert len(result) == 4

    @pytest.fixture
    def result_dataset(self, result):
        # there should be only one ResolvedStaticFile
        dataset_files = [f for f in result if f.type == "resolved_static_file"]
        assert len(dataset_files) == 1
        dataset_file = dataset_files[0]
        assert dataset_file.filename == "files/dataset.parquet"
        # read the bytes
        return pl.read_parquet(dataset_file.content)

    @pytest.mark.parametrize("scenario", ["minimal"], indirect=True)
    def test_result_dataset_minimal(self, result_dataset):
        assert result_dataset.columns == ["Resource", "File"]
        assert result_dataset.row(0) == (10, "file_10.txt")

    @pytest.mark.parametrize("scenario", ["complex"], indirect=True)
    def test_result_dataset_complex(self, result_dataset):
        assert result_dataset.columns == ["Resource", "OtherColumn", "File"]
        assert result_dataset.row(0) == (10, 20, "file_10.txt")

    @pytest.mark.parametrize("scenario", ["complex_output_column_conflict"], indirect=True)
    def test_result_dataset_when_conflict(self, result_dataset):
        assert result_dataset.columns == ["Resource", "OtherColumn", "OtherColumn.1"]
        assert result_dataset.row(0) == (10, 20, "file_10.txt")

    @pytest.mark.parametrize("scenario", ["minimal", "complex", "complex_output_column_conflict"], indirect=True)
    def test_result_files(self, result):
        files = [f for f in result if f.type == "resolved_file"]
        files.sort(key=lambda f: f.filename)

        # check all 3 files
        assert files == snapshot(
            [
                ResolvedFile(
                    filename="files/file_10.txt",
                    source=FileSourceSsh(
                        ssh=FileSourceSshValue(host="storage_host", path="/base/path/path/to/file_10.txt")
                    ),
                    link=False,
                    checksum="checksum_10",
                ),
                ResolvedFile(
                    filename="files/file_11.txt",
                    source=FileSourceSsh(
                        ssh=FileSourceSshValue(host="storage_host", path="/base/path/path/to/file_11.txt")
                    ),
                    link=False,
                    checksum="checksum_11",
                ),
                ResolvedFile(
                    filename="files/file_12.txt",
                    source=FileSourceSsh(
                        ssh=FileSourceSshValue(host="storage_host", path="/base/path/path/to/file_12.txt")
                    ),
                    link=False,
                    checksum="checksum_12",
                ),
            ]
        )

    @pytest.mark.parametrize("scenario", ["dataset_only"], indirect=True)
    def test_dataset_only(self, result, result_dataset):
        assert len(result) == 1
        assert result[0].filename == "files/dataset.parquet"
        assert result_dataset.columns == ["Resource", "File"]
        assert result_dataset.row(0) == (10, "file_10.txt")
