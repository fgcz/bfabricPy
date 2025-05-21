import io
import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dirty_equals import IsStr
from inline_snapshot import snapshot

sys.path.append(".")
from app_zip_tools import (
    APP_ZIP_VERSION,
    AppZipManager,
    AppZipValidator,
    validate,
    create,
    run,
    ValidationResult,
)


@pytest.fixture
def valid_app_dir(fs) -> Path:
    app_dir = Path("/workdir/app_dir")
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
    app_zip = Path("/workdir/app.zip")
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for file_path in valid_app_dir.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, arcname=str(Path("app") / file_path.relative_to(valid_app_dir)))

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
    def test_get_validation_errors(validator):
        assert validator.get_validation_errors() == ([], [])


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
    def test_validator_get_validation_errors(validator):
        errors, warnings = validator.get_validation_errors()
        assert set(errors) == snapshot(
            {"Invalid version: 0.0.0 (expected 0.1.0)", "Missing pylock.toml file", "Missing python_version.txt"}
        )
        assert set(warnings) == snapshot({"Missing app.yml configuration file (not required for validation)"})


class TestValidateAppZip:
    @staticmethod
    def test_when_valid(mocker, valid_app_zip):
        """Test validation of an app zip file"""
        result = AppZipManager.validate(valid_app_zip)
        assert result.errors == []
        assert result.is_valid is True

    @staticmethod
    def test_when_bad_zip(mocker, valid_app_zip):
        """Test validation of an invalid zip file"""
        mocker.patch("zipfile.ZipFile", side_effect=zipfile.BadZipFile)
        result = AppZipManager.validate(valid_app_zip)
        assert result.errors == ["Not a valid zip file"]
        assert result.is_valid is False


class TestValidateAppZipDir:
    @staticmethod
    def test_validate_app_dir(valid_app_dir):
        """Test validation of an extracted app directory"""
        result = AppZipManager.validate(valid_app_dir)
        assert result.errors == []
        assert result.is_valid is True

    @staticmethod
    def test_validate_app_dir_invalid(fs):
        """Test validation of an invalid app directory"""
        app_dir = Path(".app_tmp/app")
        fs.create_dir(app_dir)
        fs.create_file(app_dir / "app_zip_version.txt", contents="0.0.0")
        result = AppZipManager.validate(app_dir)
        assert result.errors == snapshot(
            ["Invalid version: 0.0.0 (expected 0.1.0)", "Missing pylock.toml file", "Missing python_version.txt"]
        )
        assert result.is_valid is False


def test_create_app_zip(mocker):
    """Test app zip creation"""
    mocker.patch.object(AppZipManager, "_verify_input_files")
    mock_validate = mocker.patch.object(AppZipManager, "validate")
    mock_validate.return_value = ValidationResult(errors=[], path=Path("test.zip"))

    output_path = Path("output.zip")
    wheel_paths = [Path("wheel_file.whl")]
    pylock_path = Path("pylock.toml")
    app_yml_path = Path("app.yml")

    mock_zip = mocker.patch("zipfile.ZipFile")
    mock_zip_instance = MagicMock()
    mock_zip.return_value.__enter__.return_value = mock_zip_instance

    AppZipManager.create_app_zip(output_path, wheel_paths, pylock_path, app_yml_path, "3.13")

    # Verify zip file was created with correct content
    mock_zip.assert_called_once_with(output_path, "w")
    assert mock_zip_instance.writestr.call_count >= 2  # At minimum: version, python version
    assert mock_zip_instance.write.call_count >= 3  # At minimum: pylock, wheel, app.yml

    # Verify validation was performed
    mock_validate.assert_called_once_with(output_path)


def test_run_app_zip(fs, mocker, valid_app_zip):
    """Test running a command from an app zip"""
    mock_validate = mocker.patch.object(AppZipManager, "validate")
    mock_validate.return_value = ValidationResult(errors=[], path=valid_app_zip)
    mock_create_venv = mocker.patch.object(AppZipManager, "_create_empty_uv_venv")
    mock_activate_run = mocker.patch.object(AppZipManager, "_activate_uv_venv_and_run")

    # Run the command
    os.chdir("/workdir")
    mock_chdir = mocker.patch("os.chdir")
    AppZipManager.run_app_zip(valid_app_zip, "python -m app")

    # Verify directory change
    assert mock_chdir.call_count == 2

    # Verify command were run
    assert mock_activate_run.mock_calls == [
        mocker.call(mocker.ANY, [["uv", "pip", "install", "--requirement", "pylock.toml"]]),
        mocker.call(mocker.ANY, [["python", "-m", "app"]]),
    ]
    expected_path = IsStr(regex=r"/workdir/\.app_cache/app\.zip__s\d+_t\d+_h[a-f0-9]{12}/app/.venv")
    assert str(mock_activate_run.call_args_list[0][0][0]) == expected_path
    assert str(mock_activate_run.call_args_list[1][0][0]) == expected_path
    mock_create_venv.assert_called_once()
    assert mock_create_venv.call_args_list[0][0] == (mocker.ANY, "3.13")
    assert str(mock_create_venv.call_args_list[0][0][0]) == expected_path


class TestCLI:
    @staticmethod
    @pytest.fixture
    def zip_path():
        return Path("test.zip")

    @staticmethod
    @pytest.fixture
    def validation_result_valid(zip_path):
        return ValidationResult(errors=[], path=zip_path)

    @staticmethod
    @pytest.fixture
    def validation_result_invalid(zip_path):
        return ValidationResult(errors=["Invalid"], path=zip_path)

    @staticmethod
    def test_validate_when_valid(mocker, zip_path, validation_result_valid):
        mocker.patch.object(AppZipManager, "validate", return_value=validation_result_valid)
        validate(Path("test.zip"))

    @staticmethod
    def test_validate_when_invalid(mocker, zip_path, validation_result_invalid):
        mocker.patch.object(AppZipManager, "validate", return_value=validation_result_invalid)
        with pytest.raises(SystemExit):
            validate(Path("test.zip"))

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
