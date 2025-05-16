import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher

import sys

sys.path.append(".")
from app_zip_tools import (
    APP_ZIP_VERSION,
    AppZipManager,
    AppZipValidator,
    validate,
    create,
    run,
)


# Fixtures
@pytest.fixture
def valid_validator():
    """Return a valid AppZipValidator instance"""
    return AppZipValidator(
        version=APP_ZIP_VERSION,
        has_pylock=True,
        wheel_files=["app/package/example-1.0.0-py3-none-any.whl"],
        python_version="3.13",
        has_app_config=True,
    )


@pytest.fixture
def invalid_validator():
    """Return an invalid AppZipValidator instance"""
    return AppZipValidator(
        version="0.0.0",  # Wrong version
        has_pylock=False,  # Missing pylock
        wheel_files=[],  # No wheels
        python_version=None,  # No Python version
        has_app_config=False,  # No app config
    )


@pytest.fixture
def fs():
    """Setup and teardown a fake filesystem"""
    with Patcher() as patcher:
        # Setup basic directory structure
        fs = patcher.fs

        # Create temp directory
        fs.create_dir(".app_tmp")

        # Create dummy files for testing
        fs.create_file("test.zip", contents="")
        fs.create_file("pylock.toml", contents="dependencies = []")
        fs.create_file("wheel_file.whl", contents="wheel content")
        fs.create_file("app.yml", contents="name: TestApp")

        yield fs


@pytest.fixture
def mock_zipfile():
    """Setup mock zipfile"""
    with patch("zipfile.ZipFile") as mock_zip:
        mock_zip_instance = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_zip_instance
        mock_zip_instance.namelist.return_value = [
            "app/app_zip_version.txt",
            "app/pylock.toml",
            "app/package/example-1.0.0-py3-none-any.whl",
            "app/config/python_version.txt",
            "app/config/app.yml",
        ]

        # Setup mock file opens
        mock_zip_instance.open.return_value.__enter__.return_value.read.side_effect = [
            APP_ZIP_VERSION.encode("utf-8"),  # app_zip_version.txt
            "3.13".encode("utf-8"),  # python_version.txt
        ]

        yield mock_zip_instance


# Tests for AppZipValidator
def test_validator_is_valid(valid_validator, invalid_validator):
    """Test the is_valid property"""
    assert valid_validator.is_valid is True
    assert invalid_validator.is_valid is False


def test_validator_get_validation_errors(valid_validator, invalid_validator):
    """Test validation error generation"""
    # Valid validator should have no errors
    assert len(valid_validator.get_validation_errors()) == 0

    # Invalid validator should have 4 errors (and 1 warning)
    errors = invalid_validator.get_validation_errors()
    assert len(errors) == 5
    assert any("version" in error for error in errors)
    assert any("pylock" in error for error in errors)
    assert any("wheel files" in error for error in errors)
    assert any("python_version" in error for error in errors)
    assert any("Warning" in error for error in errors)  # app.yml warning


# Tests for AppZipManager
def test_calculate_checksum(fs):
    """Test checksum calculation"""
    test_file = Path("test_file.txt")
    fs.create_file(test_file, contents="test content")

    checksum = AppZipManager.calculate_checksum(test_file)
    # Known SHA-256 for 'test content'
    expected = "6ae8a75555209fd6c44157c0aed8016e763ff435a19cf186f76863140143ff72"
    assert checksum == expected


def test_validate_app_zip(mock_zipfile):
    """Test validation of an app zip file"""
    with patch.object(AppZipManager, "_print_validation_result"):
        result = AppZipManager.validate_app_zip(Path("test.zip"))
        assert result["valid"] is True
        assert len(result["errors"]) == 0


def test_validate_app_zip_bad_zip():
    """Test validation of an invalid zip file"""
    with (
        patch("zipfile.ZipFile", side_effect=zipfile.BadZipFile),
        patch.object(AppZipManager, "_print_validation_result"),
    ):
        result = AppZipManager.validate_app_zip(Path("bad.zip"))
        assert result["valid"] is False
        assert "Not a valid zip file" in result["errors"]


def test_validate_app_dir(fs):
    """Test validation of an extracted app directory"""
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)

    # Create files needed for a valid app
    fs.create_file(app_dir / "app_zip_version.txt", contents=APP_ZIP_VERSION)
    fs.create_file(app_dir / "pylock.toml", contents="dependencies = []")
    fs.create_dir(app_dir / "package")
    fs.create_file(app_dir / "package/test-1.0.0-py3-none-any.whl", contents="wheel data")
    fs.create_dir(app_dir / "config")
    fs.create_file(app_dir / "config/python_version.txt", contents="3.13")
    fs.create_file(app_dir / "config/app.yml", contents="name: TestApp")

    result = AppZipManager.validate_app_dir(app_dir)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_app_dir_invalid(fs):
    """Test validation of an invalid app directory"""
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)

    # Missing files and wrong version
    fs.create_file(app_dir / "app_zip_version.txt", contents="0.0.0")

    result = AppZipManager.validate_app_dir(app_dir)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


@patch.object(AppZipManager, "_verify_input_files")
@patch.object(AppZipManager, "calculate_checksum")
@patch.object(AppZipManager, "validate_app_zip")
def test_create_app_zip(mock_validate, mock_checksum, mock_verify, fs):
    """Test app zip creation"""
    # Setup mocks
    mock_checksum.return_value = "fake_checksum"
    mock_validate.return_value = {"valid": True, "errors": []}

    output_path = Path("output.zip")
    wheel_paths = [Path("wheel_file.whl")]
    pylock_path = Path("pylock.toml")
    app_yml_path = Path("app.yml")

    with patch("zipfile.ZipFile") as mock_zip:
        mock_zip_instance = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_zip_instance

        AppZipManager.create_app_zip(output_path, wheel_paths, pylock_path, app_yml_path, "3.13")

        # Verify zip file was created with correct content
        mock_zip.assert_called_once_with(output_path, "w")
        assert mock_zip_instance.writestr.call_count >= 3  # At minimum: version, python version, checksums
        assert mock_zip_instance.write.call_count >= 3  # At minimum: pylock, wheel, app.yml

        # Verify validation was performed
        mock_validate.assert_called_once_with(output_path)


@patch.object(AppZipManager, "_is_newer")
@patch.object(AppZipManager, "validate_app_dir")
@patch.object(AppZipManager, "_activate_venv_and_run")
def test_run_app_zip(mock_activate, mock_validate, mock_is_newer, fs):
    """Test running a command from an app zip"""
    # Setup mocks
    mock_is_newer.return_value = False  # Assume zip is not newer than the directory
    mock_validate.return_value = {"valid": True, "errors": []}

    # Setup directory structure
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)
    fs.create_dir(app_dir / "config")
    fs.create_file(app_dir / "config/python_version.txt", contents="3.13")
    fs.create_dir(app_dir / ".venv")  # Pretend venv exists

    # Run the command
    with patch("os.chdir") as mock_chdir:
        AppZipManager.run_app_zip(Path("test.zip"), "python -m app")

        # Verify directory change
        assert mock_chdir.call_count == 2

        # Verify command was run
        mock_activate.assert_called_once()


def test_verify_checksums(fs):
    """Test checksum verification"""
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)
    fs.create_dir(app_dir / "package")

    # Create a wheel file
    wheel_path = app_dir / "package/test-1.0.0-py3-none-any.whl"
    fs.create_file(wheel_path, contents="test wheel content")

    # Create a checksum file with the correct hash
    checksum = AppZipManager.calculate_checksum(wheel_path)
    fs.create_file(app_dir / "checksum.sha256", contents=f"{checksum} test-1.0.0-py3-none-any.whl")

    # This should not raise an exception
    with patch("sys.exit") as mock_exit:
        AppZipManager._verify_checksums(app_dir)
        mock_exit.assert_not_called()


def test_verify_checksums_mismatch(fs):
    """Test checksum verification with mismatched checksums"""
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)
    fs.create_dir(app_dir / "package")

    # Create a wheel file
    wheel_path = app_dir / "package/test-1.0.0-py3-none-any.whl"
    fs.create_file(wheel_path, contents="test wheel content")

    # Create a checksum file with an incorrect hash
    fs.create_file(app_dir / "checksum.sha256", contents="incorrect_checksum test-1.0.0-py3-none-any.whl")

    # This should exit with an error
    with patch("sys.exit") as mock_exit, patch("builtins.print") as mock_print:
        AppZipManager._verify_checksums(app_dir)
        mock_exit.assert_called_once()
        mock_print.assert_called_with("Checksum mismatch for test-1.0.0-py3-none-any.whl")


# Tests for command-line functions
@patch.object(AppZipManager, "validate_app_zip")
def test_validate_command(mock_validate):
    """Test the validate command"""
    mock_validate.return_value = {"valid": True, "errors": []}

    with patch("sys.exit") as mock_exit:
        validate(Path("test.zip"))
        mock_exit.assert_not_called()

    # Test with invalid zip
    mock_validate.return_value = {"valid": False, "errors": ["Invalid"]}

    with patch("sys.exit") as mock_exit:
        validate(Path("test.zip"))
        mock_exit.assert_called_once()


@patch.object(AppZipManager, "create_app_zip")
def test_create_command(mock_create):
    """Test the create command"""
    create(Path("output.zip"), [Path("wheel.whl")], Path("pylock.toml"), Path("app.yml"), "3.13")
    mock_create.assert_called_once_with(
        Path("output.zip"), [Path("wheel.whl")], Path("pylock.toml"), Path("app.yml"), "3.13"
    )


@patch.object(AppZipManager, "run_app_zip")
def test_run_command(mock_run):
    """Test the run command"""
    run(Path("test.zip"), "python -m app")
    mock_run.assert_called_once_with(Path("test.zip"), "python -m app")
