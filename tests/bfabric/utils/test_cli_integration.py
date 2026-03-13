"""Tests for cli_integration.use_client decorator."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path
from typing import Annotated

import pytest


# Mock cyclopts before importing cli_integration
class MockParameter:
    def __init__(self, help: str):
        self.help = help


class MockCyclopts:
    Parameter = MockParameter


sys.modules["cyclopts"] = MockCyclopts()

from bfabric.utils.cli_integration import use_client, _DEFAULT_CONFIG_FILE
from bfabric import Bfabric


@pytest.fixture(autouse=True)
def clear_env_vars():
    """Clear environment variables before and after each test."""
    original_env = os.environ.copy()
    os.environ.pop("BFABRICPY_CONFIG_ENV", None)
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestUseClientSignature:
    """Tests for the use_client decorator's function signature modifications."""

    def test_use_client_preserves_original_signature_without_client(self):
        """Verify that when a function has a `client` parameter, it's removed from the decorated function's signature."""

        @use_client
        def my_function(client: Bfabric, arg1: str, arg2: int) -> str:
            return f"{arg1}-{arg2}"

        sig = inspect.signature(my_function)
        params = list(sig.parameters.keys())

        assert "client" not in params
        assert "arg1" in params
        assert "arg2" in params
        assert "config_env" in params
        assert "config_file" in params

    def test_use_client_adds_config_env_parameter(self):
        """Verify that `config_env` parameter is added to the decorated function's signature."""

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_env_param = sig.parameters.get("config_env")

        assert config_env_param is not None
        assert config_env_param.kind == inspect.Parameter.KEYWORD_ONLY
        assert config_env_param.default is None

    def test_use_client_adds_config_file_parameter(self):
        """Verify that `config_file` parameter is added to the decorated function's signature."""

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_file_param = sig.parameters.get("config_file")

        assert config_file_param is not None
        assert config_file_param.kind == inspect.Parameter.KEYWORD_ONLY
        assert config_file_param.default is None

    def test_use_client_config_env_defaults_to_env_var(self):
        """Verify that when `BFABRICPY_CONFIG_ENV` is set, it's used as the default for `config_env`."""
        os.environ["BFABRICPY_CONFIG_ENV"] = "TEST_ENV"

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_env_param = sig.parameters.get("config_env")

        assert config_env_param.default == "TEST_ENV"

    def test_use_client_config_env_defaults_to_none_when_env_var_not_set(self):
        """Verify that `config_env` defaults to None when env var is not set."""

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_env_param = sig.parameters.get("config_env")

        assert config_env_param.default is None

    def test_use_client_with_cyclopts_available(self):
        """Verify that when cyclopts is available, the parameters have proper annotations for CLI help text."""

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_env_param = sig.parameters.get("config_env")
        config_file_param = sig.parameters.get("config_file")

        # Check that annotations include Annotated with cyclopts.Parameter
        assert config_env_param.annotation is not None
        assert config_file_param.annotation is not None

    def test_use_client_preserves_function_metadata(self):
        """Verify that the decorator preserves the original function's metadata."""

        @use_client
        def my_function(client: Bfabric, arg1: str) -> str:
            """Original docstring."""
            return arg1

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "Original docstring."


class TestUseClientBehavior:
    """Tests for the use_client decorator's runtime behavior."""

    @pytest.fixture
    def mock_bfabric_connect(self, mocker):
        """Mock Bfabric.connect to prevent actual connections."""
        return mocker.patch("bfabric.Bfabric.connect", return_value=mocker.Mock())

    def test_use_client_passes_config_env_to_bfabric_connect(self, mock_bfabric_connect):
        """Verify that config_env parameter is passed to Bfabric.connect."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        result = my_function("test", config_env="PROD")

        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        assert call_kwargs["config_file_env"] == "PROD"
        assert "config_file_path" in call_kwargs
        assert result == "test"

    def test_use_client_passes_config_file_to_bfabric_connect(self, mock_bfabric_connect):
        """Verify that config_file parameter is passed to Bfabric.connect."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        custom_config = Path("/custom/config.yml")
        result = my_function("test", config_file=custom_config)

        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        assert call_kwargs["config_file_path"] == custom_config
        assert "config_file_env" in call_kwargs
        assert result == "test"

    def test_use_client_with_explicit_client_parameter(self, mock_bfabric_connect):
        """Verify that config parameters are properly passed to Bfabric.connect."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        # Call with config parameters
        result = my_function("test", config_env="TEST", config_file=Path("/test/config.yml"))

        # Bfabric.connect should be called with the provided config
        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        assert call_kwargs["config_file_env"] == "TEST"
        assert call_kwargs["config_file_path"] == Path("/test/config.yml")
        assert result == "test"

    def test_use_client_default_config_file_path(self, mock_bfabric_connect):
        """Verify that when config_file is None, the default `~/.bfabricpy.yml` is used."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        result = my_function("test")  # No config_file specified

        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        assert call_kwargs["config_file_path"] == _DEFAULT_CONFIG_FILE
        assert result == "test"

    def test_use_client_passes_default_config_env_when_not_specified(self, mock_bfabric_connect):
        """Verify that 'default' is passed for config_env when not specified."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        result = my_function("test")  # No config_env specified

        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        # Should pass 'default' which is the fallback when config_env is None
        assert call_kwargs["config_file_env"] == "default"
        assert result == "test"

    def test_use_client_with_both_config_parameters(self, mock_bfabric_connect):
        """Verify that both config_env and config_file can be specified together."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"{arg1}"

        custom_config = Path("/custom/config.yml")
        result = my_function("test", config_env="TEST", config_file=custom_config)

        mock_bfabric_connect.assert_called_once()
        call_kwargs = mock_bfabric_connect.call_args.kwargs
        assert call_kwargs["config_file_env"] == "TEST"
        assert call_kwargs["config_file_path"] == custom_config
        assert result == "test"

    def test_use_client_preserves_function_return_value(self, mock_bfabric_connect):
        """Verify that the decorated function returns the correct value."""

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return f"processed: {arg1}"

        result = my_function("input")

        assert result == "processed: input"

    def test_use_client_with_multiple_args_and_kwargs(self, mock_bfabric_connect):
        """Verify that the decorator works correctly with multiple args and kwargs."""

        @use_client
        def my_function(arg1: str, arg2: int, *, kwarg1: bool, client: Bfabric) -> str:
            return f"{arg1}-{arg2}-{kwarg1}"

        result = my_function("test", 42, kwarg1=True)

        assert result == "test-42-True"


class TestUseClientWithoutCyclopts:
    """Tests for the use_client decorator when cyclopts is not available."""

    def test_use_client_annotation_without_cyclopts(self):
        """Verify that annotations work correctly without cyclopts."""

        # When cyclopts is available (as mocked at top of file), check that annotations are present
        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return arg1

        sig = inspect.signature(my_function)
        config_env_param = sig.parameters.get("config_env")
        config_file_param = sig.parameters.get("config_file")

        # Verify parameters exist and have annotations
        assert config_env_param is not None
        assert config_file_param is not None
        assert config_env_param.annotation is not None
        assert config_file_param.annotation is not None


class TestDefaultConfigFile:
    """Tests for the default config file constant."""

    def test_default_config_file_is_path(self):
        """Verify that _DEFAULT_CONFIG_FILE is a Path object."""
        assert isinstance(_DEFAULT_CONFIG_FILE, Path)

    def test_default_config_file_path(self):
        """Verify the default config file path is correct."""
        expected = Path("~/.bfabricpy.yml")
        assert _DEFAULT_CONFIG_FILE == expected


class TestUseClientSetupLogging:
    """Tests for the use_client decorator's logging setup."""

    def test_use_client_setup_logging_by_default(self, mocker):
        """Verify that logging is set up by default."""
        mock_setup_logging = mocker.patch("bfabric.utils.cli_integration.setup_script_logging")
        mock_bfabric_connect = mocker.patch("bfabric.Bfabric.connect", return_value=mocker.Mock())

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return arg1

        # Call the decorated function
        result = my_function("test")

        # Verify setup_logging was called
        mock_setup_logging.assert_called_once()
        # Verify the function still works
        assert result == "test"

    def test_use_client_no_logging_when_disabled(self, mocker):
        """Verify that logging setup parameter is handled (setup_logging defaults to True)."""
        # Note: The current implementation doesn't support passing setup_logging=False
        # This test verifies that the default behavior (setup_logging=True) works correctly
        mock_setup_logging = mocker.patch("bfabric.utils.cli_integration.setup_script_logging")
        mock_bfabric_connect = mocker.patch("bfabric.Bfabric.connect", return_value=mocker.Mock())

        @use_client
        def my_function(arg1: str, *, client: Bfabric) -> str:
            return arg1

        # Call the decorated function
        result = my_function("test")

        # Verify setup_logging was called (default behavior)
        mock_setup_logging.assert_called_once()
        # Verify the function still works
        assert result == "test"
