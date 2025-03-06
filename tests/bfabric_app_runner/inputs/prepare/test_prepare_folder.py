from pathlib import Path

import pytest
from bfabric_app_runner.inputs.prepare.prepare_folder import (
    prepare_folder,
    _prepare_input_files,
    _clean_input_files,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs, ResolvedFile, ResolvedStaticFile
from bfabric_app_runner.specs.inputs_spec import InputsSpec


@pytest.fixture
def mock_inputs_spec(mocker):
    mock_spec = mocker.MagicMock(spec=InputsSpec)
    mock_spec.inputs = []
    return mock_spec


@pytest.fixture
def mock_resolver(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder.Resolver")


@pytest.fixture
def mock_prepare_resolved_file(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder.prepare_resolved_file")


@pytest.fixture
def mock_prepare_resolved_static_file(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder.prepare_resolved_static_file")


@pytest.fixture
def mock_inputs_spec_read_yaml(mocker):
    return mocker.patch("bfabric_app_runner.specs.inputs_spec.InputsSpec.read_yaml")


@pytest.fixture
def mock_logger(mocker):
    return mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder.logger")


@pytest.fixture
def fs(fs):
    # Return the pytest-fs fixture
    return fs


def test_prepare_folder_prepare_action(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    target_folder = Path("/path/to/target")
    mock_client = mocker.MagicMock()
    ssh_user = "test_user"

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Mock _prepare_input_files
    mock_prepare = mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._prepare_input_files")

    # Call the function
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        client=mock_client,
        ssh_user=ssh_user,
        filter=None,
        action="prepare",
    )

    # Verify
    mock_inputs_spec_read_yaml.assert_called_once_with(inputs_yaml)
    mock_resolver.assert_called_once_with(client=mock_client)
    mock_resolver_instance.resolve.assert_called_once_with(specs=mock_inputs_spec.inputs)
    mock_prepare.assert_called_once_with(input_files=mock_resolved_inputs, working_dir=target_folder, ssh_user=ssh_user)


def test_prepare_folder_clean_action(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    target_folder = Path("/path/to/target")
    mock_client = mocker.MagicMock()

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Mock _clean_input_files
    mock_clean = mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._clean_input_files")

    # Call the function
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        client=mock_client,
        ssh_user=None,
        filter=None,
        action="clean",
    )

    # Verify
    mock_inputs_spec_read_yaml.assert_called_once_with(inputs_yaml)
    mock_resolver.assert_called_once_with(client=mock_client)
    mock_resolver_instance.resolve.assert_called_once_with(specs=mock_inputs_spec.inputs)
    mock_clean.assert_called_once_with(input_files=mock_resolved_inputs, working_dir=target_folder)


def test_prepare_folder_with_filter(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    target_folder = Path("/path/to/target")
    mock_client = mocker.MagicMock()
    file_filter = "test_file.txt"

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Mock filtered inputs
    mock_filtered_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_filtered_inputs.files = [mocker.MagicMock()]  # Non-empty list
    mock_resolved_inputs.apply_filter.return_value = mock_filtered_inputs

    # Mock _prepare_input_files
    mock_prepare = mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._prepare_input_files")

    # Call the function
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        client=mock_client,
        ssh_user=None,
        filter=file_filter,
        action="prepare",
    )

    # Verify
    mock_inputs_spec_read_yaml.assert_called_once_with(inputs_yaml)
    mock_resolver.assert_called_once_with(client=mock_client)
    mock_resolver_instance.resolve.assert_called_once_with(specs=mock_inputs_spec.inputs)
    mock_resolved_inputs.apply_filter.assert_called_once_with(filter_files=[file_filter])
    mock_prepare.assert_called_once_with(input_files=mock_filtered_inputs, working_dir=target_folder, ssh_user=None)


def test_prepare_folder_filter_no_match(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    target_folder = Path("/path/to/target")
    mock_client = mocker.MagicMock()
    file_filter = "nonexistent_file.txt"

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Mock filtered inputs with empty file list
    mock_filtered_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_filtered_inputs.files = []  # Empty list to trigger ValueError
    mock_resolved_inputs.apply_filter.return_value = mock_filtered_inputs

    # Call the function and expect ValueError
    with pytest.raises(ValueError, match=f"Filter {file_filter} did not match any input files"):
        prepare_folder(
            inputs_yaml=inputs_yaml,
            target_folder=target_folder,
            client=mock_client,
            ssh_user=None,
            filter=file_filter,
            action="prepare",
        )

    # Verify
    mock_inputs_spec_read_yaml.assert_called_once_with(inputs_yaml)
    mock_resolver.assert_called_once_with(client=mock_client)
    mock_resolver_instance.resolve.assert_called_once_with(specs=mock_inputs_spec.inputs)
    mock_resolved_inputs.apply_filter.assert_called_once_with(filter_files=[file_filter])


def test_prepare_folder_unknown_action(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    target_folder = Path("/path/to/target")
    mock_client = mocker.MagicMock()
    unknown_action = "unknown"

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Call the function and expect ValueError
    with pytest.raises(ValueError, match=f"Unknown action: {unknown_action}"):
        prepare_folder(
            inputs_yaml=inputs_yaml,
            target_folder=target_folder,
            client=mock_client,
            ssh_user=None,
            filter=None,
            action=unknown_action,
        )


def test_prepare_folder_default_target_folder(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # Setup
    inputs_yaml = Path("/path/to/inputs.yml")
    mock_client = mocker.MagicMock()

    # Mock InputsSpec.read_yaml
    mock_inputs_spec = mocker.MagicMock()
    mock_inputs_spec_read_yaml.return_value = mock_inputs_spec

    # Mock Resolver and resolved inputs
    mock_resolver_instance = mock_resolver.return_value
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolver_instance.resolve.return_value = mock_resolved_inputs

    # Mock _prepare_input_files
    mock_prepare = mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._prepare_input_files")

    # Call the function
    prepare_folder(
        inputs_yaml=inputs_yaml,
        target_folder=None,  # Should default to inputs_yaml.parent
        client=mock_client,
        ssh_user=None,
        filter=None,
        action="prepare",
    )

    # Verify
    mock_inputs_spec_read_yaml.assert_called_once_with(inputs_yaml)
    mock_resolver.assert_called_once_with(client=mock_client)
    mock_resolver_instance.resolve.assert_called_once_with(specs=mock_inputs_spec.inputs)
    mock_prepare.assert_called_once_with(
        input_files=mock_resolved_inputs, working_dir=inputs_yaml.parent, ssh_user=None
    )


def test_prepare_input_files(mocker, mock_prepare_resolved_file, mock_prepare_resolved_static_file):
    # Setup
    working_dir = Path("/path/to/working")
    ssh_user = "test_user"

    # Create mock files
    mock_resolved_file = mocker.MagicMock(spec=ResolvedFile)
    mock_static_file = mocker.MagicMock(spec=ResolvedStaticFile)

    # Create mock resolved inputs
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolved_inputs.files = [mock_resolved_file, mock_static_file]

    # Call the function
    _prepare_input_files(input_files=mock_resolved_inputs, working_dir=working_dir, ssh_user=ssh_user)

    # Verify
    mock_prepare_resolved_file.assert_called_once_with(
        file=mock_resolved_file, working_dir=working_dir, ssh_user=ssh_user
    )
    mock_prepare_resolved_static_file.assert_called_once_with(file=mock_static_file, working_dir=working_dir)


def test_clean_input_files(fs, mocker, mock_logger):
    # Setup with pyfakefs
    working_dir = Path("/path/to/working")
    fs.create_dir(working_dir)

    # Create file1.txt (will exist)
    file1_path = working_dir / "file1.txt"
    fs.create_file(file1_path)

    # file2.txt will not exist initially
    file2_path = working_dir / "file2.txt"

    # Create mock files for ResolvedInputs
    mock_file1 = mocker.MagicMock()
    mock_file1.filename = "file1.txt"
    mock_file2 = mocker.MagicMock()
    mock_file2.filename = "file2.txt"

    # Create mock resolved inputs
    mock_resolved_inputs = mocker.MagicMock(spec=ResolvedInputs)
    mock_resolved_inputs.files = [mock_file1, mock_file2]

    # Call the function
    _clean_input_files(input_files=mock_resolved_inputs, working_dir=working_dir)

    # Verify
    assert not file1_path.exists()  # Should be removed
    assert not file2_path.exists()  # Should still not exist
    mock_logger.info.assert_called_once_with(f"Removed {file1_path}")
