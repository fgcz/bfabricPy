import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import io

import pytest

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


@pytest.fixture
def valid_app_dir(fs) -> Path:
    app_dir = Path(".app_tmp/app")
    fs.create_dir(app_dir)
    fs.create_file(app_dir / "app_zip_version.txt", contents=APP_ZIP_VERSION)
    fs.create_file(app_dir / "pylock.toml", contents="dependencies = []")
    fs.create_dir(app_dir / "package")
    fs.create_file(app_dir / "package/test-1.0.0-py3-none-any.whl", contents="wheel data")
    fs.create_dir(app_dir / "config")
    fs.create_file(app_dir / "python_version.txt", contents="3.13")
    fs.create_file(app_dir / "config/app.yml", contents="name: TestApp")
    return app_dir


@pytest.fixture
def valid_app_zip(fs, valid_app_dir) -> Path:
    app_zip = Path("app.zip")
    zip_buffer = io.BytesIO()
    base_dir = valid_app_dir.parent

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for file_path in valid_app_dir.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, arcname=str(file_path.relative_to(base_dir)))

    fs.create_file(app_zip, contents=zip_buffer.getvalue())
    return app_zip


class TestValidatorValid:
    @staticmethod
    @pytest.fixture
    def validator():
        """Return a valid AppZipValidator instance"""
        return AppZipValidator(
            version=APP_ZIP_VERSION,
            has_pylock=True,
            wheel_files=["app/package/example-1.0.0-py3-none-any.whl"],
            python_version="3.13",
            has_app_config=True,
        )

    @staticmethod
    def test_is_valid(validator):
        assert validator.is_valid is True

    @staticmethod
    def test_get_validation_errors(validator):
        assert validator.get_validation_errors() == []


class TestValidatorInvalid:
    @staticmethod
    @pytest.fixture
    def validator():
        return AppZipValidator(
            version="0.0.0",  # Wrong version
            has_pylock=False,  # Missing pylock
            wheel_files=[],  # No wheels
            python_version=None,  # No Python version
            has_app_config=False,  # No app config
        )

    @staticmethod
    def test_is_valid(validator):
        assert validator.is_valid is False

    @staticmethod
    def test_validator_get_validation_errors(validator):
        errors = validator.get_validation_errors()
        assert len(errors) == 4
        assert any("version" in error for error in errors)
        assert any("pylock" in error for error in errors)
        assert any("python_version" in error for error in errors)
        assert any("Warning" in error for error in errors)  # app.yml warning


class TestValidateAppZip:
    @staticmethod
    def test_when_valid(mocker, valid_app_zip):
        """Test validation of an app zip file"""
        mocker.patch.object(AppZipManager, "_print_validation_result")
        result = AppZipManager.validate(valid_app_zip)
        assert result["errors"] == []
        assert result["valid"] is True

    @staticmethod
    def test_when_bad_zip(mocker, valid_app_zip):
        """Test validation of an invalid zip file"""
        mocker.patch("zipfile.ZipFile", side_effect=zipfile.BadZipFile)
        result = AppZipManager.validate(valid_app_zip)
        assert "Not a valid zip file" in result["errors"]
        assert result["valid"] is False


class TestValidateAppZipDir:
    @staticmethod
    def test_validate_app_dir(valid_app_dir):
        """Test validation of an extracted app directory"""
        result = AppZipManager.validate(valid_app_dir)
        assert result["errors"] == []
        assert result["valid"] is True

    @staticmethod
    def test_validate_app_dir_invalid(fs):
        """Test validation of an invalid app directory"""
        app_dir = Path(".app_tmp/app")
        fs.create_dir(app_dir)
        fs.create_file(app_dir / "app_zip_version.txt", contents="0.0.0")
        result = AppZipManager.validate(app_dir)
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


class TestCLI:
    @staticmethod
    def test_validate(mocker):
        """Test the validate command"""
        mock_validate = mocker.patch.object(AppZipManager, "validate")
        mock_validate.return_value = {"valid": True, "errors": []}
        mock_exit = mocker.patch("sys.exit")
        validate(Path("test.zip"))
        mock_exit.assert_not_called()

        # Test with invalid zip
        mock_validate.return_value = {"valid": False, "errors": ["Invalid"]}

        mock_exit.reset_mock()
        validate(Path("test.zip"))
        mock_exit.assert_called_once()

    @staticmethod
    def test_create_command(mocker):
        """Test the create command"""
        mock_create = mocker.patch.object(AppZipManager, "create_app_zip")
        create(Path("output.zip"), [Path("wheel.whl")], Path("pylock.toml"), Path("app.yml"), "3.13")
        mock_create.assert_called_once_with(
            Path("output.zip"), [Path("wheel.whl")], Path("pylock.toml"), Path("app.yml"), "3.13"
        )

    @staticmethod
    def test_run_command(mocker):
        """Test the run command"""
        mock_run = mocker.patch.object(AppZipManager, "run_app_zip")
        run(Path("test.zip"), "python -m app")
        mock_run.assert_called_once_with(Path("test.zip"), "python -m app")
