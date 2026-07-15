from pathlib import Path
from typing import Literal

import pytest
from bfabric.config.bfabric_auth import OAUTH_LOGIN
from bfabric_app_runner.inputs.prepare.prepare_context import PrepareContext
from bfabric_app_runner.inputs.prepare.prepare_folder import (
    prepare_folder,
    _prepare_input_files,
    _clean_input_files,
    _needs_bearer_token,
    _resolve_token_provider,
)
from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedInputs, ResolvedFile, ResolvedStaticFile
from bfabric_app_runner.specs.inputs.file_spec import FileSourceHttp, FileSourceHttpValue, FileSourceLocal
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
    mock_resolved_inputs.files = []
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
    mock_prepare.assert_called_once_with(
        input_files=mock_resolved_inputs,
        working_dir=target_folder,
        context=PrepareContext(ssh_user=ssh_user, token_provider=None),
    )


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
    mock_prepare.assert_called_once_with(
        input_files=mock_filtered_inputs,
        working_dir=target_folder,
        context=PrepareContext(ssh_user=None, token_provider=None),
    )


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
    mock_resolved_inputs.files = []
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
        input_files=mock_resolved_inputs,
        working_dir=inputs_yaml.parent,
        context=PrepareContext(ssh_user=None, token_provider=None),
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

    context = PrepareContext(ssh_user=ssh_user, token_provider=lambda: "tok")

    # Call the function
    _prepare_input_files(input_files=mock_resolved_inputs, working_dir=working_dir, context=context)

    # Verify
    mock_prepare_resolved_file.assert_called_once_with(
        file=mock_resolved_file, working_dir=working_dir, context=context
    )
    mock_prepare_resolved_static_file.assert_called_once_with(file=mock_static_file, working_dir=working_dir)


def _http_resolved(url: str, auth: Literal["bfabric"] | None) -> ResolvedFile:
    return ResolvedFile(
        source=FileSourceHttp(http=FileSourceHttpValue(url=url, auth=auth)),
        filename="x.txt",
        link=False,
        checksum=None,
    )


def test_needs_bearer_token_true_when_auth_http_present():
    inputs = ResolvedInputs(
        files=[
            ResolvedFile(source=FileSourceLocal(local="/a.txt"), filename="a.txt", link=False, checksum=None),
            _http_resolved("https://host/x", auth="bfabric"),
        ]
    )
    assert _needs_bearer_token(inputs) is True


def test_needs_bearer_token_false_for_anonymous_http_and_non_http():
    inputs = ResolvedInputs(
        files=[
            ResolvedFile(source=FileSourceLocal(local="/a.txt"), filename="a.txt", link=False, checksum=None),
            _http_resolved("https://host/x", auth=None),
        ]
    )
    assert _needs_bearer_token(inputs) is False


def test_prepare_folder_skips_token_when_no_http(mocker, mock_inputs_spec_read_yaml, mock_resolver):
    # An OAuth token fetch must not be triggered (nor crash prepare) when no HTTP input needs it.
    mock_client = mocker.MagicMock()
    mock_resolve_token = mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._resolve_token_provider")
    mocker.patch("bfabric_app_runner.inputs.prepare.prepare_folder._prepare_input_files")

    mock_inputs_spec_read_yaml.return_value = mocker.MagicMock()
    resolved = ResolvedInputs(
        files=[ResolvedFile(source=FileSourceLocal(local="/a.txt"), filename="a.txt", link=False, checksum=None)]
    )
    mock_resolver.return_value.resolve.return_value = resolved

    prepare_folder(
        inputs_yaml=Path("/x/inputs.yml"),
        target_folder=Path("/x"),
        client=mock_client,
        ssh_user=None,
        filter=None,
        action="prepare",
    )

    mock_resolve_token.assert_not_called()


def test_resolve_token_provider_when_oauth(mocker):
    mock_client = mocker.MagicMock()
    mock_client.auth.login = OAUTH_LOGIN
    mock_client.auth.password.get_secret_value.return_value = "jwt-token"
    provider = _resolve_token_provider(mock_client)
    assert provider is not None
    # The provider reads the token live, so it reflects a refresh under the client.
    assert provider() == "jwt-token"


def test_resolve_token_provider_when_password_login(mocker):
    mock_client = mocker.MagicMock()
    mock_client.auth.login = "some_user"
    assert _resolve_token_provider(mock_client) is None
    mock_client.auth.password.get_secret_value.assert_not_called()


def test_resolve_token_provider_when_no_auth(mocker):
    mock_client = mocker.MagicMock()
    type(mock_client).auth = mocker.PropertyMock(side_effect=ValueError("Authentication not available"))
    assert _resolve_token_provider(mock_client) is None


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
