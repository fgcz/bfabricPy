import pytest
from bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs import ResolveBfabricAnnotationSpecs
from bfabric_app_runner.specs.inputs.static_file_spec import StaticFileSpec


@pytest.fixture
def mock_client(mocker):
    return mocker.MagicMock(name="mock_client")


@pytest.fixture
def resolver(mock_client):
    return ResolveBfabricAnnotationSpecs(mock_client)


def test_call(resolver, mocker, mock_client):
    # Mock the get_annotation function
    mocker.patch(
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
    assert isinstance(result[0], StaticFileSpec)
    assert result[0].filename == "annotation.gff"
    assert result[0].content == "annotation content"

    # Verify the correct methods were called
    from bfabric_app_runner.inputs.resolve._resolve_bfabric_annotation_specs import get_annotation

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
