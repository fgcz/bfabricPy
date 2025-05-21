#!/usr/bin/env python3
"""App Zip Tool.
------------
Tool for validating, running, and creating applications packaged in App Zip Format 0.1.0
"""
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from zipfile import ZipFile

import cyclopts
from pydantic import BaseModel, Field
from loguru import logger

# Constants
APP_ZIP_VERSION = "0.1.0"
TEMP_DIR = Path(".app_tmp")


class AppZipValidator(BaseModel):
    """Validator for App Zip Format 0.1.0."""

    version: str = "unknown"
    has_pylock: bool = False
    wheel_files: list[str] = Field(default_factory=list)
    python_version: str | None = None
    has_app_config: bool = False

    def get_validation_errors(self) -> tuple[list[str], list[str]]:
        """Generate human-readable error messages."""
        errors = []
        warnings = []
        if self.version != APP_ZIP_VERSION:
            errors.append(f"Invalid version: {self.version} (expected {APP_ZIP_VERSION})")
        if not self.has_pylock:
            errors.append("Missing pylock.toml file")
        if self.python_version is None:
            errors.append("Missing python_version.txt")
        if not self.has_app_config:
            warnings.append("Missing app.yml configuration file (not required for validation)")
        return errors, warnings


class ValidationResult(BaseModel):
    path: Path
    errors: list[str]
    warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def print(self) -> None:
        """Print validation results in a user-friendly format."""
        zip_name = self.path.name

        if self.is_valid:
            print(f"✅ {zip_name}: Valid App Zip (format {APP_ZIP_VERSION})")
        else:
            print(f"❌ {zip_name}: Invalid App Zip")
            print("\nValidation errors:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
            print()
            print(f"The zip file does not conform to App Zip Format {APP_ZIP_VERSION} specification.")

        if self.warnings:
            print("\nValidation warnings:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")


class AppZipManager:
    """Manager for App Zip operations."""

    @classmethod
    def validate(cls, source: Path) -> ValidationResult:
        """Validates if a zip file or directory follows the App Zip Format specification."""
        try:
            if source.is_file():
                with zipfile.ZipFile(source, "r") as zip_file:
                    validator = cls._extract_from_zip(zip_file)
            else:
                validator = cls._extract_from_directory(source)
            errors, warnings = validator.get_validation_errors()
            return ValidationResult(path=source, errors=errors, warnings=warnings)
        except zipfile.BadZipFile:
            return ValidationResult(path=source, errors=["Not a valid zip file"])
        except Exception as e:
            return ValidationResult(path=source, errors=[f"Unknown error validating source: {e!s}"])

    @staticmethod
    def _read_zip_file(zip_file: ZipFile, path: str, default: str | None = None) -> str | None:
        if path in zip_file.namelist():
            with zip_file.open(path) as f:
                return f.read().decode("utf-8").strip()
        return default

    @classmethod
    def _extract_from_zip(cls, zip_file) -> AppZipValidator:
        """Extract app info from a zip file."""
        file_list = zip_file.namelist()
        return AppZipValidator(
            version=cls._read_zip_file(zip_file, "app/app_zip_version.txt", "unknown"),
            python_version=cls._read_zip_file(zip_file, "app/python_version.txt"),
            has_pylock="app/pylock.toml" in file_list,
            wheel_files=[f for f in file_list if f.startswith("app/package/") and f.endswith(".whl")],
            has_app_config="app/config/app.yml" in file_list,
        )

    @staticmethod
    def _read_file(path: Path, default: str | None = None) -> str | None:
        return path.read_text().strip() if path.exists() else default

    @classmethod
    def _extract_from_directory(cls, app_dir) -> AppZipValidator:
        """Extract app info from a directory."""
        return AppZipValidator(
            version=cls._read_file(app_dir / "app_zip_version.txt", "unknown"),
            python_version=cls._read_file(app_dir / "python_version.txt"),
            has_pylock=(app_dir / "pylock.toml").exists(),
            wheel_files=[f"app/package/{p.name}" for p in app_dir.glob("package/*.whl")],
            has_app_config=(app_dir / "config" / "app.yml").exists(),
        )

    @staticmethod
    def create_app_zip(
        output_path: Path,
        wheel_paths: list[Path],
        pylock_path: Path,
        app_yml_path: Path | None = None,
        python_version: str = "3.13",
    ) -> None:
        """Create an App Zip file from pre-built components."""
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Verify files exist
        AppZipManager._verify_input_files(pylock_path, wheel_paths, app_yml_path)

        # Create the zip file
        print(f"Creating app zip: {output_path}")
        with zipfile.ZipFile(output_path, "w") as app_zip:
            # Write the app zip version
            app_zip.writestr("app/app_zip_version.txt", APP_ZIP_VERSION)

            # Add the pylock.toml file
            app_zip.write(pylock_path, arcname="app/pylock.toml")

            # Add the wheel files
            for wheel_path in wheel_paths:
                app_zip.write(wheel_path, arcname=f"app/package/{wheel_path.name}")

            # Add the app.yml file if provided
            if app_yml_path:
                app_zip.write(app_yml_path, arcname="app/config/app.yml")

            # Write the python version
            app_zip.writestr("app/python_version.txt", python_version)

        print(f"✅ Successfully created app zip: {output_path}")

        # Validate the created zip
        result = AppZipManager.validate(output_path)
        result.print()
        if not result.is_valid:
            print("Warning: Created zip file failed validation!")
            sys.exit(1)

    @classmethod
    def run_app_zip(cls, zip_path: Path, command: str) -> None:
        """Run a command from an app zip file."""
        # Create cache directory if it doesn't exist
        cache_base_dir = Path.cwd() / ".app_cache"
        cache_base_dir.mkdir(exist_ok=True)

        # Generate a cache directory name that includes filename and fingerprint
        fingerprint = AppZipManager._generate_fingerprint(zip_path)
        cache_dir_name = f"{zip_path.name}__{fingerprint}"
        app_cache_dir = cache_base_dir / cache_dir_name
        app_dir = app_cache_dir / "app"

        # Extract if needed
        if not app_dir.exists():
            cls._extract_app_to_cache(zip_path, app_cache_dir, cache_base_dir)
        else:
            print(f"Using cached app from {app_cache_dir}")

        # Validate the app
        result = cls.validate(app_dir)
        result.print()
        if not result.is_valid:
            sys.exit(1)

        # Run in virtual environment
        cls._run_in_venv(app_dir, command)

    @classmethod
    def _extract_app_to_cache(cls, zip_path: Path, app_cache_dir: Path, cache_base_dir: Path) -> None:
        logger.info(f"Extracting {zip_path} to {app_cache_dir}...")
        app_cache_dir.parent.mkdir(parents=True, exist_ok=True)

        # Extract to a temporary directory first
        with tempfile.TemporaryDirectory(dir=cache_base_dir) as extract_temp_dir:
            extract_temp_path = Path(extract_temp_dir) / "extract"
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                if any(zip_info.filename.startswith("..") for zip_info in zip_file.infolist()):
                    raise ValueError("Error: Potentially unsafe path in zip")
                zip_file.extractall(extract_temp_path)

            # Move the extracted content to the final temporary directory
            shutil.move(str(extract_temp_path), str(app_cache_dir))
            logger.debug(f"Extracted app to {app_cache_dir}, contents: {list(app_cache_dir.glob('*'))}")

    @staticmethod
    def _generate_fingerprint(zip_path: Path) -> str:
        """Generate a simple fingerprint for the zip file.

        Combines file size, modification time, and a hash of the first 4KB.
        """
        stat = zip_path.stat()

        # Read first 4KB for a content fingerprint
        with open(zip_path, "rb") as f:
            content_sample = f.read(4096)

        # Create a hash of the content sample - using 12 characters for better uniqueness
        # MD5 produces 32 hex chars, we're using 12 which gives us 16^12 = 2^48 possible values
        # This provides a good balance of collision resistance while keeping the path length reasonable
        content_hash = hashlib.md5(content_sample).hexdigest()[:12]

        # Combine size, mod time and content hash in a simple format
        return f"s{stat.st_size}_t{int(stat.st_mtime)}_h{content_hash}"

    @classmethod
    def _run_in_venv(cls, app_dir: Path, command: str) -> None:
        """Set up virtual environment and run the command."""
        # Parse command
        command_args = shlex.split(command)

        # Setup virtual environment
        python_version = (app_dir / "python_version.txt").read_text().strip()
        venv_path = app_dir / ".venv"

        # Change to app directory
        original_dir = Path.cwd()
        os.chdir(app_dir)

        try:
            # Create virtual environment if it doesn't exist
            if not venv_path.exists():
                print(f"Creating Python {python_version} virtual environment...")
                cls._create_empty_uv_venv(venv_path, python_version)

                # Install dependencies
                print("Installing dependencies...")
                commands = [["uv", "pip", "install", "--requirement", "pylock.toml"]]

                # Add wheel installation if needed
                package_dir = Path("package")
                if package_dir.exists() and list(package_dir.glob("*.whl")):
                    commands.append(
                        ["uv", "pip", "install", "--offline", "--no-deps", *list(package_dir.glob("*.whl"))]
                    )

                cls._activate_uv_venv_and_run(venv_path, commands)

            # Run the command in the virtual environment
            print(f"Running: {command}")
            cls._activate_uv_venv_and_run(venv_path, [command_args])
        finally:
            # Always return to original directory
            os.chdir(original_dir)

    @staticmethod
    def _verify_input_files(pylock_path: Path, wheel_paths: list[Path], app_yml_path: Path | None) -> None:
        """Verify that all input files exist."""
        if not pylock_path.exists():
            msg = f"Error: pylock.toml file not found at {pylock_path}"
            raise ValueError(msg)

        for wheel_path in wheel_paths:
            if not wheel_path.exists():
                msg = f"Error: Wheel file not found at {wheel_path}"
                raise ValueError(msg)

        if app_yml_path and not app_yml_path.exists():
            msg = f"Error: app.yml file not found at {app_yml_path}"
            raise ValueError(msg)

    @classmethod
    def _create_empty_uv_venv(cls, venv_path: Path, python_version: str) -> None:
        """Creates an empty virtual environment using uv."""
        subprocess.run(["uv", "venv", "-p", python_version, str(venv_path)], check=True)

    @staticmethod
    def _activate_uv_venv_and_run(venv_path: Path, commands_list: list[list[str]]) -> None:
        """Activate virtual environment and run commands."""
        # Determine the activation script based on platform
        if sys.platform == "win32":
            activate_script = venv_path / "Scripts" / "activate.bat"
            activate_cmd = f"call {activate_script}"
        else:
            activate_script = venv_path / "bin" / "activate"
            activate_cmd = f"source {activate_script}"

        # Run each command in the activated environment
        for cmd_args in commands_list:
            if isinstance(cmd_args[0], Path):
                cmd_args[0] = str(cmd_args[0])

            cmd_str = " ".join(str(arg) for arg in cmd_args)
            full_cmd = f"{activate_cmd} && {cmd_str}"

            try:
                subprocess.run(full_cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error executing command: {cmd_str}")
                print(f"Return code: {e.returncode}")
                sys.exit(e.returncode)


app = cyclopts.App(help="App Zip Format 0.1.0 tool")


@app.command()
def validate(zip_path: Path) -> None:
    """Validate an App Zip file against the 0.1.0 specification."""
    result = AppZipManager.validate(zip_path)
    result.print()
    if not result.is_valid:
        sys.exit(1)


@app.command()
def create(
    output_path: Path,
    wheel_paths: list[Path],
    pylock_path: Path,
    app_yml_path: Path | None = None,
    python_version: str = "3.13",
) -> None:
    """Create an App Zip file from pre-built components.

    Args:
        output_path: Path where the app zip will be created
        wheel_paths: List of paths to wheel files (.whl)
        pylock_path: Path to the pylock.toml file
        app_yml_path: Path to the app.yml configuration file (optional)
        python_version: Python version to use (default: 3.13)

    """
    AppZipManager.create_app_zip(output_path, wheel_paths, pylock_path, app_yml_path, python_version)


@app.command()
def run(zip_path: Path, command: str) -> None:
    """Run a command from an app zip file.

    Args:
        zip_path: Path to the app zip file
        command: Command string to run in the app environment (will be parsed with shlex)

    """
    AppZipManager.run_app_zip(zip_path, command)


if __name__ == "__main__":
    app()
