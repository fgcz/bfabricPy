#!/usr/bin/env python3
"""
App Zip Tool
------------
Tool for validating, running, and creating applications packaged in App Zip Format 0.1.0
"""
import os
import shlex
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import cyclopts
from pydantic import BaseModel, Field

app = cyclopts.App(help="App Zip Format 0.1.0 tool")


@app.command()
def validate(zip_path: Path) -> None:
    """Validate an App Zip file against the 0.1.0 specification"""
    result = validate_app_zip(zip_path)
    if not result["valid"]:
        sys.exit(1)


@app.command()
def create(
    output_path: Path,
    wheel_paths: List[Path],
    pylock_path: Path,
    app_yml_path: Optional[Path] = None,
    python_version: str = "3.13",
) -> None:
    """
    Create an App Zip file from pre-built components

    Args:
        output_path: Path where the app zip will be created
        wheel_paths: List of paths to wheel files (.whl)
        pylock_path: Path to the pylock.toml file
        app_yml_path: Path to the app.yml configuration file (optional)
        python_version: Python version to use (default: 3.13)
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    # Create the zip file
    print(f"Creating app zip: {output_path}")
    with zipfile.ZipFile(output_path, "w") as app_zip:
        # Write the app zip version
        app_zip.writestr("app/app_zip_version.txt", "0.1.0")

        # Add the pylock.toml file
        app_zip.write(pylock_path, arcname="app/pylock.toml")

        # Add the wheel files
        for wheel_path in wheel_paths:
            app_zip.write(wheel_path, arcname=f"app/package/{wheel_path.name}")

        # Add the app.yml file if provided
        if app_yml_path:
            app_zip.write(app_yml_path, arcname="app/config/app.yml")

        # Write the python version
        app_zip.writestr("app/config/python_version.txt", python_version)

    print(f"✅ Successfully created app zip: {output_path}")

    # Validate the created zip
    result = validate_app_zip(output_path)
    if not result["valid"]:
        print("Warning: Created zip file failed validation!")
        sys.exit(1)


@app.command()
def run(zip_path: Path, command: str) -> None:
    """
    Run a command from an app zip file

    Args:
        zip_path: Path to the app zip file
        command: Command string to run in the app environment (will be parsed with shlex)
    """
    # Parse the command string into a list of arguments
    command_args = shlex.split(command)

    # Setup paths
    dest_dir = Path("./.app_tmp")
    app_dir = dest_dir / "app"

    # Extract if zip is newer than directory
    if is_newer(zip_path, app_dir):
        print(f"Extracting {zip_path}...")
        dest_dir.mkdir(exist_ok=True)

        # Safe removal of app directory
        if app_dir.exists() and ".app_tmp/app" in str(app_dir):
            shutil.rmtree(app_dir)
        elif app_dir.exists():
            print(f"Error: Unexpected app directory path: {app_dir}")
            sys.exit(1)

        # Extract the zip
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(dest_dir)

    # Validate the app zip
    result = validate_app_dir(app_dir)
    if not result["valid"]:
        print_validation_result(zip_path, result)
        sys.exit(1)

    # Setup environment
    python_version = (app_dir / "config" / "python_version.txt").read_text().strip()
    venv_path = app_dir / ".venv"

    # Change to app directory
    os.chdir(app_dir)

    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        print(f"Creating Python {python_version} virtual environment...")
        subprocess.run(["uv", "venv", "-p", python_version, str(venv_path)], check=True)

        # Install dependencies
        print("Installing dependencies...")
        activate_venv_and_run(
            venv_path,
            [
                ["uv", "pip", "install", "--requirement", "pylock.toml"],
                ["uv", "pip", "install", "--offline", "--no-deps"] + list(Path("package").glob("*.whl")),
            ],
        )

    # Run the command in the virtual environment
    print(f"Running: {command}")
    activate_venv_and_run(venv_path, [command_args])


class AppZipValidator(BaseModel):
    """Validator for App Zip Format 0.1.0"""

    version: str = Field(default="unknown")
    has_pylock: bool = Field(default=False)
    wheel_files: List[str] = Field(default_factory=list)
    python_version: Optional[str] = Field(default=None)
    has_app_config: bool = Field(default=False)

    @property
    def is_valid(self) -> bool:
        """Check if zip structure is valid"""
        valid_version = self.version == "0.1.0"
        valid_pylock = self.has_pylock
        valid_wheels = len(self.wheel_files) > 0
        valid_python = self.python_version is not None

        # app.yml is not required if we're just validating
        # (it's only required for certain functionality)
        return valid_version and valid_pylock and valid_wheels and valid_python

    def get_validation_errors(self) -> List[str]:
        """Generate human-readable error messages"""
        errors = []
        if self.version != "0.1.0":
            errors.append(f"Invalid version: {self.version} (expected 0.1.0)")
        if not self.has_pylock:
            errors.append("Missing pylock.toml file")
        if not self.wheel_files:
            errors.append("No wheel files found in package directory")
        if self.python_version is None:
            errors.append("Missing python_version.txt")
        # Only warn about missing app.yml, as it's not strictly required for validation
        if not self.has_app_config:
            errors.append("Warning: Missing app.yml configuration file (not required for validation)")
        return errors


def validate_app_zip(zip_path: Path) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate if a zip file follows the App Zip Format 0.1.0 specification

    Args:
        zip_path: Path to the zip file

    Returns:
        Dictionary with validation results and errors if any
    """
    result = {"valid": False, "errors": []}

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            file_list = zip_file.namelist()
            validator = extract_zip_info(zip_file, file_list)

            result["valid"] = validator.is_valid
            result["errors"] = validator.get_validation_errors()

            # Print results
            print_validation_result(zip_path, result)

    except zipfile.BadZipFile:
        result["errors"] = ["Not a valid zip file"]
        print_validation_result(zip_path, result)
    except Exception as e:
        result["errors"] = [f"Error validating zip: {str(e)}"]
        print_validation_result(zip_path, result)

    return result


def validate_app_dir(app_dir: Path) -> Dict[str, Union[bool, List[str]]]:
    """Validate an extracted app directory"""
    result = {"valid": False, "errors": []}

    try:
        # Check app_zip_version.txt
        version_file = app_dir / "app_zip_version.txt"
        version = "unknown"
        if version_file.exists():
            version = version_file.read_text().strip()

        # Check python version
        python_version = None
        python_version_file = app_dir / "config" / "python_version.txt"
        if python_version_file.exists():
            python_version = python_version_file.read_text().strip()

        # Build validator
        validator = AppZipValidator(
            version=version,
            has_pylock=(app_dir / "pylock.toml").exists(),
            wheel_files=[str(p) for p in app_dir.glob("package/*.whl")],
            python_version=python_version,
            has_app_config=(app_dir / "config" / "app.yml").exists(),
        )

        result["valid"] = validator.is_valid
        result["errors"] = validator.get_validation_errors()
    except Exception as e:
        result["errors"] = [f"Error validating directory: {str(e)}"]

    return result


def extract_zip_info(zip_file: zipfile.ZipFile, file_list: List[str]) -> AppZipValidator:
    """Extract relevant information from zip contents"""
    # Check version
    version = "unknown"
    version_file = "app/app_zip_version.txt"
    if version_file in file_list:
        with zip_file.open(version_file) as f:
            version = f.read().decode("utf-8").strip()

    # Check python version
    python_version = None
    python_version_file = "app/config/python_version.txt"
    if python_version_file in file_list:
        with zip_file.open(python_version_file) as f:
            python_version = f.read().decode("utf-8").strip()

    return AppZipValidator(
        version=version,
        has_pylock="app/pylock.toml" in file_list,
        wheel_files=[f for f in file_list if f.startswith("app/package/") and f.endswith(".whl")],
        python_version=python_version,
        has_app_config="app/config/app.yml" in file_list,
    )


def print_validation_result(zip_path: Path, result: Dict[str, Union[bool, List[str]]]) -> None:
    """Print validation results in a user-friendly format"""
    zip_name = zip_path.name

    if result["valid"]:
        print(f"✅ {zip_name}: Valid App Zip (format 0.1.0)")
    else:
        print(f"❌ {zip_name}: Invalid App Zip")
        if result["errors"]:
            print("\nValidation errors:")
            for i, error in enumerate(result["errors"], 1):
                print(f"  {i}. {error}")
            print()
        print("The zip file does not conform to App Zip Format 0.1.0 specification.")


def is_newer(zip_path: Path, dir_path: Path) -> bool:
    """Check if zip file is newer than directory"""
    # If directory doesn't exist, zip is "newer"
    if not dir_path.exists():
        return True

    # Compare modification times
    return zip_path.stat().st_mtime > dir_path.stat().st_mtime


def activate_venv_and_run(venv_path: Path, commands_list: List[List[str]]) -> None:
    """Activate virtual environment and run commands"""
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


if __name__ == "__main__":
    app()
