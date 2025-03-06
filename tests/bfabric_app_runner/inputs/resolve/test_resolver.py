import pytest
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs
from bfabric_app_runner.inputs.resolve.resolver import Resolver
from bfabric_app_runner.specs.inputs.bfabric_annotation_spec import (
    BfabricAnnotationSpec,
    BfabricAnnotationResourceSampleSpec,
)
from bfabric_app_runner.specs.inputs.bfabric_dataset_spec import BfabricDatasetSpec
from bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec import BfabricOrderFastaSpec
from bfabric_app_runner.specs.inputs.bfabric_resource_spec import BfabricResourceSpec
from bfabric_app_runner.specs.inputs.static_yaml_spec import StaticYamlSpec
from pytest_mock import MockerFixture


@pytest.fixture
def mock_bfabric(mocker):
    return mocker.MagicMock(name="mock_bfabric_client")


@pytest.fixture
def mock_dataset_resolver(mocker: MockerFixture):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve.resolver.ResolveBfabricDatasetSpecs", autospec=True
    ).return_value


@pytest.fixture
def mock_resource_resolver(mocker: MockerFixture):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve.resolver.ResolveBfabricResourceSpecs", autospec=True
    ).return_value


@pytest.fixture
def mock_yaml_resolver(mocker: MockerFixture):
    return mocker.patch("bfabric_app_runner.inputs.resolve.resolver.ResolveStaticYamlSpecs", autospec=True).return_value


@pytest.fixture
def mock_order_fasta_resolver(mocker: MockerFixture):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve.resolver.ResolveBfabricOrderFastaSpecs", autospec=True
    ).return_value


@pytest.fixture
def mock_annotation_resolver(mocker: MockerFixture):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve.resolver.ResolveBfabricAnnotationSpecs", autospec=True
    ).return_value


@pytest.fixture
def resolver(
    mock_bfabric,
    mock_dataset_resolver,
    mock_resource_resolver,
    mock_yaml_resolver,
    mock_order_fasta_resolver,
    mock_annotation_resolver,
) -> Resolver:
    """Create a Resolver instance with mocked dependencies."""
    return Resolver(client=mock_bfabric)


@pytest.fixture
def mock_resolved_inputs(mocker):
    return mocker.patch(
        "bfabric_app_runner.inputs.resolve.resolver.ResolvedInputs", side_effect=lambda files: mocker.Mock(files=files)
    )


def test_resolver_initialization(
    mock_bfabric,
    resolver,
    mock_dataset_resolver,
    mock_resource_resolver,
    mock_yaml_resolver,
    mock_order_fasta_resolver,
    mock_annotation_resolver,
):
    assert resolver._client == mock_bfabric
    assert resolver._resolve_bfabric_dataset_specs == mock_dataset_resolver
    assert resolver._resolve_bfabric_resource_specs == mock_resource_resolver
    assert resolver._resolve_static_yaml_specs == mock_yaml_resolver
    assert resolver._resolve_bfabric_order_fasta_specs == mock_order_fasta_resolver
    assert resolver._resolve_bfabric_annotation_specs == mock_annotation_resolver


def test_group_specs_by_type(mocker) -> None:
    """Test the _group_specs_by_type static method."""
    # Mock specs
    yaml_spec = mocker.MagicMock(spec=StaticYamlSpec, name="yaml_spec")
    resource_spec = mocker.MagicMock(spec=BfabricResourceSpec, name="resource_spec")
    dataset_spec = mocker.MagicMock(spec=BfabricDatasetSpec, name="dataset_spec")

    # Call the method with a list of specs
    specs = [yaml_spec, resource_spec, dataset_spec, yaml_spec]
    result = Resolver._group_specs_by_type(specs)

    # Verify the correct grouping
    assert len(result) == 3
    assert result[type(yaml_spec)] == [yaml_spec, yaml_spec]
    assert result[type(resource_spec)] == [resource_spec]
    assert result[type(dataset_spec)] == [dataset_spec]


def test_resolve_with_all_spec_types(
    mocker,
    resolver,
    mock_dataset_resolver,
    mock_resource_resolver,
    mock_yaml_resolver,
    mock_order_fasta_resolver,
    mock_annotation_resolver,
    mock_resolved_inputs,
):
    """Test that resolve method routes each spec type to the correct implementation."""
    # Create mock specs of each type
    yaml_spec = mocker.MagicMock(spec=StaticYamlSpec, name="yaml_spec")
    resource_spec = mocker.MagicMock(spec=BfabricResourceSpec, name="resource_spec")
    dataset_spec = mocker.MagicMock(spec=BfabricDatasetSpec, name="dataset_spec")
    order_fasta_spec = mocker.MagicMock(spec=BfabricOrderFastaSpec, name="order_fasta_spec")
    annotation_spec = mocker.MagicMock(spec=BfabricAnnotationSpec, name="annotation_spec")

    grouped_specs = {
        StaticYamlSpec: [yaml_spec, yaml_spec],
        BfabricResourceSpec: [resource_spec],
        BfabricDatasetSpec: [dataset_spec, dataset_spec, dataset_spec],
        BfabricOrderFastaSpec: [order_fasta_spec],
        BfabricAnnotationResourceSampleSpec: [annotation_spec],
        BfabricAnnotationSpec: [annotation_spec],
    }
    mock_group_specs = mocker.patch.object(resolver, "_group_specs_by_type", return_value=grouped_specs)

    # Set up mock return values for each resolver implementation
    mock_yaml_resolver.return_value = ["yaml_file1", "yaml_file2"]
    mock_resource_resolver.return_value = ["resource_file"]
    mock_dataset_resolver.return_value = ["dataset_file1", "dataset_file2", "dataset_file3"]
    mock_order_fasta_resolver.return_value = ["order_fasta_file"]
    mock_annotation_resolver.return_value = ["annotation_file"]

    # Call resolve with all types of specs
    mock_specs = mocker.Mock(spec=[], name="mock_specs")
    result = resolver.resolve(specs=mock_specs)

    # Check that the group_specs_by_type method was called with the correct specs (the mock_specs)
    mock_group_specs.assert_called_once_with(specs=mock_specs)

    # Verify each resolver implementation was called with the correct specs
    mock_yaml_resolver.assert_called_once_with([yaml_spec, yaml_spec])
    mock_resource_resolver.assert_called_once_with([resource_spec])
    mock_dataset_resolver.assert_called_once_with([dataset_spec, dataset_spec, dataset_spec])
    mock_order_fasta_resolver.assert_called_once_with([order_fasta_spec])
    mock_annotation_resolver.assert_called_once_with([annotation_spec])

    # Verify the result contains all the expected files
    expected_files = {
        "yaml_file1",
        "yaml_file2",
        "resource_file",
        "dataset_file1",
        "dataset_file2",
        "dataset_file3",
        "order_fasta_file",
        "annotation_file",
    }
    assert set(result.files) == expected_files
    mock_resolved_inputs.assert_called_once()


def test_resolve_with_empty_specs(resolver):
    """Test the resolve method with an empty list of specs."""
    result = resolver.resolve([])
    assert isinstance(result, ResolvedInputs)
    assert len(result.files) == 0


def test_resolve_static_yaml_specs(
    resolver,
    mock_yaml_resolver,
    mocker: MockerFixture,
    mock_resolved_inputs,
):
    """Test resolving only StaticYamlSpec specs."""
    yaml_spec1 = mocker.MagicMock(spec=StaticYamlSpec)
    yaml_spec2 = mocker.MagicMock(spec=StaticYamlSpec)
    mocker.patch.object(resolver, "_group_specs_by_type", return_value={StaticYamlSpec: [yaml_spec1, yaml_spec2]})
    mock_yaml_resolver.return_value = [mocker.MagicMock(name="yaml_file", type="static_file")]

    # Call the resolve method
    specs = [yaml_spec1, yaml_spec2]
    result = resolver.resolve(specs)

    # Verify results
    mock_yaml_resolver.assert_called_once()
    assert result.files == mock_yaml_resolver.return_value
    mock_resolved_inputs.assert_called_once()


def test_resolve_bfabric_resource_specs(
    resolver,
    mock_resource_resolver,
    mocker: MockerFixture,
    mock_resolved_inputs,
):
    """Test resolving only BfabricResourceSpec specs."""
    resource_spec1 = mocker.MagicMock(spec=BfabricResourceSpec)
    resource_spec2 = mocker.MagicMock(spec=BfabricResourceSpec)
    mocker.patch.object(
        resolver, "_group_specs_by_type", return_value={BfabricResourceSpec: [resource_spec1, resource_spec2]}
    )
    mock_resource_resolver.return_value = [mocker.MagicMock(name="resource_file", type="resource_file")]

    # Call the resolve method
    specs = [resource_spec1, resource_spec2]
    result = resolver.resolve(specs)

    # Verify results
    mock_resource_resolver.assert_called_once()
    assert result.files == mock_resource_resolver.return_value
    mock_resolved_inputs.assert_called_once()


def test_resolve_bfabric_dataset_specs(
    resolver,
    mock_dataset_resolver,
    mocker: MockerFixture,
    mock_resolved_inputs,
):
    """Test resolving only BfabricDatasetSpec specs."""
    dataset_spec1 = mocker.MagicMock(spec=BfabricDatasetSpec)
    dataset_spec2 = mocker.MagicMock(spec=BfabricDatasetSpec)
    mocker.patch.object(
        resolver, "_group_specs_by_type", return_value={BfabricDatasetSpec: [dataset_spec1, dataset_spec2]}
    )
    mock_dataset_resolver.return_value = [mocker.MagicMock(name="dataset_file", type="dataset_file")]

    # Call the resolve method
    specs = [dataset_spec1, dataset_spec2]
    result = resolver.resolve(specs)

    # Verify results
    mock_dataset_resolver.assert_called_once()
    assert result.files == mock_dataset_resolver.return_value
    mock_resolved_inputs.assert_called_once()


def test_resolve_bfabric_order_fasta_specs(
    resolver,
    mock_order_fasta_resolver,
    mocker: MockerFixture,
    mock_resolved_inputs,
):
    """Test resolving only BfabricOrderFastaSpec specs."""
    order_fasta_spec1 = mocker.MagicMock(spec=BfabricOrderFastaSpec)
    order_fasta_spec2 = mocker.MagicMock(spec=BfabricOrderFastaSpec)
    mocker.patch.object(
        resolver, "_group_specs_by_type", return_value={BfabricOrderFastaSpec: [order_fasta_spec1, order_fasta_spec2]}
    )
    mock_order_fasta_resolver.return_value = [mocker.MagicMock(name="order_fasta_file", type="order_fasta_file")]

    # Call the resolve method
    specs = [order_fasta_spec1, order_fasta_spec2]
    result = resolver.resolve(specs)

    # Verify results
    mock_order_fasta_resolver.assert_called_once()
    assert result.files == mock_order_fasta_resolver.return_value
    mock_resolved_inputs.assert_called_once()


def test_resolve_bfabric_annotation_specs(
    resolver,
    mock_annotation_resolver,
    mocker: MockerFixture,
    mock_resolved_inputs,
):
    """Test resolving only BfabricAnnotationSpec specs."""
    annotation_spec1 = mocker.MagicMock(spec=BfabricAnnotationSpec)
    annotation_spec2 = mocker.MagicMock(spec=BfabricAnnotationSpec)
    mocker.patch.object(
        resolver, "_group_specs_by_type", return_value={BfabricAnnotationSpec: [annotation_spec1, annotation_spec2]}
    )
    mock_annotation_resolver.return_value = [mocker.MagicMock(name="annotation_file", type="annotation_file")]

    # Call the resolve method
    specs = [annotation_spec1, annotation_spec2]
    result = resolver.resolve(specs)

    # Verify results
    mock_annotation_resolver.assert_called_once()
    assert result.files == mock_annotation_resolver.return_value
    mock_resolved_inputs.assert_called_once()
