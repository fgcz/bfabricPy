#!/usr/bin/env python3
"""
App Zip Validator
----------------
Validates Python application zip files according to App Zip Format 0.1.0
"""
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Union

import cyclopts
from pydantic import BaseModel, Field

app = cyclopts.App(help="Validate App Zip Format 0.1.0 packages")


@app.command()
def validate(zip_path: Path) -> None:
    """Validate an App Zip file against the 0.1.0 specification"""
    result = validate_app_zip(zip_path)
    if not result["valid"]:
        sys.exit(1)


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
        return (
            self.version == "0.1.0"
            and self.has_pylock
            and len(self.wheel_files) > 0
            and self.python_version is not None
            and self.has_app_config
        )

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
        if not self.has_app_config:
            errors.append("Missing app.yml configuration file")
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


if __name__ == "__main__":
    app()
