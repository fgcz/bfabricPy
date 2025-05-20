#!/usr/bin/env python3
"""App Zip Tool.
------------
Tool for validating, running, and creating applications packaged in App Zip Format 0.1.0
"""
import os
import shlex
import shutil
import subprocess
import sys
import zipfile
from zipfile import ZipFile
from pathlib import Path

import cyclopts
from pydantic import BaseModel, Field


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

    @property
    def is_valid(self) -> bool:
        """Check if zip structure is valid."""
        return self.version == APP_ZIP_VERSION and self.has_pylock and self.python_version is not None

    def get_validation_errors(self) -> list[str]:
        """Generate human-readable error messages."""
        errors = []
        if self.version != APP_ZIP_VERSION:
            errors.append(f"Invalid version: {self.version} (expected {APP_ZIP_VERSION})")
        if not self.has_pylock:
            errors.append("Missing pylock.toml file")
        if self.python_version is None:
            errors.append("Missing python_version.txt")
        # TODO this is probably not correctly implemented yet
        # Only warn about missing app.yml, as it's not strictly required for validation
        if not self.has_app_config:
            errors.append("Warning: Missing app.yml configuration file (not required for validation)")
        return errors


class AppZipManager:
    """Manager for App Zip operations."""

    @classmethod
    def validate(cls, source: Path) -> dict[str, bool | list[str]]:
        """Validates if a zip file or directory follows the App Zip Format specification.

        Args:
            source: Path to a zip file or directory to validate

        Returns:
            Dictionary with validation results
        """
        result = {"valid": False, "errors": []}

        try:
            if source.is_file() and source.suffix == ".zip":
                with zipfile.ZipFile(source, "r") as zip_file:
                    validator = cls._extract_from_zip(zip_file)
            elif source.is_dir():
                validator = cls._extract_from_directory(source)
            else:
                result["errors"] = ["Invalid source: must be a zip file or directory"]
                return result

            result["valid"] = validator.is_valid
            result["errors"] = validator.get_validation_errors()

            if source.is_file():  # Only print for zip files
                AppZipManager._print_validation_result(source, result)

        except zipfile.BadZipFile:
            result["errors"] = ["Not a valid zip file"]
            if source.is_file():
                AppZipManager._print_validation_result(source, result)
        except Exception as e:
            result["errors"] = [f"Error validating source: {e!s}"]
            if source.is_file():
                AppZipManager._print_validation_result(source, result)

        return result

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
        if not result["valid"]:
            print("Warning: Created zip file failed validation!")
            sys.exit(1)

    @staticmethod
    def run_app_zip(zip_path: Path, command: str) -> None:
        """Run a command from an app zip file."""
        # Parse the command string into a list of arguments
        command_args = shlex.split(command)

        # Setup paths
        app_dir = TEMP_DIR / "app"

        # Extract if zip is newer than directory
        if AppZipManager._is_newer(zip_path, app_dir):
            print(f"Extracting {zip_path}...")
            TEMP_DIR.mkdir(exist_ok=True)

            # Safe removal of app directory
            if app_dir.exists() and ".app_tmp/app" in str(app_dir):
                shutil.rmtree(app_dir)
            elif app_dir.exists():
                print(f"Error: Unexpected app directory path: {app_dir}")
                sys.exit(1)

            # Extract the zip
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                zip_file.extractall(TEMP_DIR)

        # Validate the app zip
        result = AppZipManager.validate(app_dir)
        if not result["valid"]:
            AppZipManager._print_validation_result(zip_path, result)
            sys.exit(1)

        # Setup environment
        python_version = (app_dir / "python_version.txt").read_text().strip()
        venv_path = app_dir / ".venv"

        # Change to app directory
        original_dir = Path.cwd()
        os.chdir(app_dir)

        try:
            # Create virtual environment if it doesn't exist
            if not venv_path.exists():
                print(f"Creating Python {python_version} virtual environment...")
                subprocess.run(["uv", "venv", "-p", python_version, str(venv_path)], check=True)

                # Install dependencies
                print("Installing dependencies...")
                commands = [["uv", "pip", "install", "--requirement", "pylock.toml"]]

                # Add wheel installation command if wheel files exist
                package_dir = Path("package")
                if package_dir.exists() and list(package_dir.glob("*.whl")):
                    commands.append(
                        ["uv", "pip", "install", "--offline", "--no-deps", *list(package_dir.glob("*.whl"))]
                    )

                AppZipManager._activate_venv_and_run(venv_path, commands)

            # Run the command in the virtual environment
            print(f"Running: {command}")
            AppZipManager._activate_venv_and_run(venv_path, [command_args])
        finally:
            # Always return to original directory
            os.chdir(original_dir)

    @staticmethod
    def _verify_input_files(pylock_path: Path, wheel_paths: list[Path], app_yml_path: Path | None) -> None:
        """Verify that all input files exist."""
        # Verify pylock.toml exists
        if not pylock_path.exists():
            print(f"Error: pylock.toml file not found at {pylock_path}")
            sys.exit(1)

        # Verify wheel files exist
        if not wheel_paths:
            print("Error: No wheel files specified")
            sys.exit(1)

        for wheel_path in wheel_paths:
            if not wheel_path.exists():
                print(f"Error: Wheel file not found at {wheel_path}")
                sys.exit(1)

        # Verify app.yml exists if provided
        if app_yml_path and not app_yml_path.exists():
            print(f"Error: app.yml file not found at {app_yml_path}")
            sys.exit(1)

    @staticmethod
    def _print_validation_result(zip_path: Path, result: dict[str, bool | list[str]]) -> None:
        """Print validation results in a user-friendly format."""
        zip_name = zip_path.name

        if result["valid"]:
            print(f"✅ {zip_name}: Valid App Zip (format {APP_ZIP_VERSION})")
        else:
            print(f"❌ {zip_name}: Invalid App Zip")
            if result["errors"]:
                print("\nValidation errors:")
                for i, error in enumerate(result["errors"], 1):
                    print(f"  {i}. {error}")
                print()
            print(f"The zip file does not conform to App Zip Format {APP_ZIP_VERSION} specification.")

    @staticmethod
    def _is_newer(zip_path: Path, dir_path: Path) -> bool:
        """Check if zip file is newer than directory."""
        # If directory doesn't exist, zip is "newer"
        if not dir_path.exists():
            return True

        # Compare modification times
        return zip_path.stat().st_mtime > dir_path.stat().st_mtime

    @staticmethod
    def _activate_venv_and_run(venv_path: Path, commands_list: list[list[str]]) -> None:
        """Activate virtual environment and run commands."""
        # Determine the activation script based on platform
        if sys.platform == "win32":
            activate_script = venv_path / "Scripts" / "activate.bat"
            activate_cmd = f"call {activate_script}"
            shell = True
        else:
            activate_script = venv_path / "bin" / "activate"
            activate_cmd = f"source {activate_script}"
            shell = True

        # Run each command in the activated environment
        for cmd_args in commands_list:
            if isinstance(cmd_args[0], Path):
                cmd_args[0] = str(cmd_args[0])

            cmd_str = " ".join(str(arg) for arg in cmd_args)
            full_cmd = f"{activate_cmd} && {cmd_str}"

            try:
                subprocess.run(full_cmd, shell=shell, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error executing command: {cmd_str}")
                print(f"Return code: {e.returncode}")
                sys.exit(e.returncode)


app = cyclopts.App(help="App Zip Format 0.1.0 tool")


@app.command()
def validate(zip_path: Path) -> None:
    """Validate an App Zip file against the 0.1.0 specification."""
    result = AppZipManager.validate(zip_path)
    if not result["valid"]:
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
