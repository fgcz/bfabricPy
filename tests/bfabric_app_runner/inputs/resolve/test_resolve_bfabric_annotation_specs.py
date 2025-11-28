from io import StringIO

import pytest
import polars as pl
from bfabric import Bfabric
from bfabric.entities import Resource
from bfabric.entities.core.entity import Entity
from bfabric.entities.core.entity_reader import EntityReader
from bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs import (
    ResolveBfabricAnnotationSpecs,
    get_annotation,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedStaticFile
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import BfabricAnnotationResourceSampleSpec


@pytest.fixture
def bfabric_instance():
    return "https://bfabric.example.org/bfabric/"


@pytest.fixture
def mock_client(mocker, bfabric_instance):
    config = mocker.MagicMock(base_url=bfabric_instance)
    return mocker.MagicMock(name="mock_client", spec=Bfabric, config=config)


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricAnnotationSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Mock the get_annotation function
    get_annotation = mocker.patch(
        "bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs.get_annotation",
        return_value="annotation content",
    )

    # Create mock spec
    mock_spec = mocker.MagicMock(name="mock_spec")
    mock_spec.filename = "annotation.gff"

    # Call the function under test
    result = resolver([mock_spec])

    # Assert the results
    assert len(result) == 1
    assert isinstance(result[0], ResolvedStaticFile)
    assert result[0].filename == "annotation.gff"
    assert result[0].content == "annotation content"

    # Verify the correct methods were called

    get_annotation.assert_called_once_with(spec=mock_spec, client=mock_client)


def test_call_when_empty(resolver):
    specs = []
    result = resolver(specs)
    assert result == []


def test_call_multiple_specs(resolver, mocker, mock_client):
    # Mock the get_annotation function with different return values
    get_annotation_mock = mocker.patch(
        "bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs.get_annotation",
        side_effect=["annotation1", "annotation2"],
    )

    # Create mock specs
    mock_spec1 = mocker.MagicMock(name="mock_spec1")
    mock_spec1.filename = "annotation1.gff"

    mock_spec2 = mocker.MagicMock(name="mock_spec2")
    mock_spec2.filename = "annotation2.gff"

    # Call the function under test
    result = resolver([mock_spec1, mock_spec2])

    # Assert the results
    assert len(result) == 2
    assert result[0].filename == "annotation1.gff"
    assert result[0].content == "annotation1"
    assert result[1].filename == "annotation2.gff"
    assert result[1].content == "annotation2"

    # Verify the get_annotation function was called correctly for each spec
    assert get_annotation_mock.call_count == 2
    get_annotation_mock.assert_has_calls(
        [mocker.call(spec=mock_spec1, client=mock_client), mocker.call(spec=mock_spec2, client=mock_client)]
    )


class TestGetResourceSampleAnnotation:
    @pytest.fixture(params=["standard", "partially_annotated"])
    def scenario(self, request):
        return request.param

    @pytest.fixture
    def resource_ids(self, scenario):
        return [100, 200] if scenario == "standard" else [100, 300]

    @pytest.fixture
    def spec(self, scenario, resource_ids):
        return BfabricAnnotationResourceSampleSpec(
            filename="dummy.csv",
            separator=",",
            resource_ids=resource_ids,
            format="csv",
        )

    @pytest.fixture
    def all_samples(self):
        return {
            101: Entity({"classname": "sample", "id": 101, "name": "test101", "groupingvar": "x"}),
            201: Entity({"classname": "sample", "id": 201, "name": "test201", "groupingvar": "x"}),
        }

    @pytest.fixture
    def all_resources(self, all_samples, bfabric_instance):
        return {
            100: Resource(
                {"classname": "resource", "id": 100, "sample": all_samples[101].data_dict},
                bfabric_instance=bfabric_instance,
            ),
            200: Resource(
                {"classname": "resource", "id": 200, "sample": all_samples[201].data_dict},
                bfabric_instance=bfabric_instance,
            ),
            300: Resource({"classname": "resource", "id": 300}, bfabric_instance=bfabric_instance),
        }

    @pytest.fixture
    def entity_reader(self, mocker, all_resources):
        def _read(entity_type: str, entity_ids: list[int]):
            assert entity_type == "resource"
            return {all_resources[id].uri: all_resources[id] for id in entity_ids}

        reader = mocker.MagicMock(name="entity_reader", spec=EntityReader)
        reader.read_ids.side_effect = _read
        return reader

    @pytest.fixture
    def mock_client(self, mock_client, entity_reader):
        mock_client.reader = entity_reader
        return mock_client

    def test(self, scenario, spec, mock_client, resource_ids):
        result_csv = get_annotation(spec=spec, client=mock_client)
        result_df = pl.read_csv(StringIO(result_csv))
        assert result_df.columns == [
            "resource_classname",
            "resource_id",
            "resource_sample_classname",
            "resource_sample_id",
            "resource_sample_name",
            "resource_sample_groupingvar",
            "sample_classname",
            "sample_name",
            "sample_groupingvar",
        ]
        assert result_df["resource_id"].to_list() == resource_ids
        assert (
            result_df["resource_sample_name"].to_list() == ["test101", "test201"]
            if scenario == "standard"
            else ["test101", None]
        )
