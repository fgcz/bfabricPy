import sys
import zipfile
from pathlib import Path
from typing import List, Dict, Union, Optional

import cyclopts
from pydantic import BaseModel, Field

app = cyclopts.App()


@app.command()
def validate(zip_path: Path) -> None:
    result = is_valid_app_zip(zip_path)
    print_validation_result(zip_path, result)
    if not result["valid"]:
        raise SystemExit(1)


class AppZipValidator(BaseModel):
    """Model for validating App Zip Format 0.1.0"""

    version: str = Field(..., description="Version from app_zip_version.txt")
    has_pylock: bool = Field(..., description="Presence of pylock.toml")
    wheel_files: List[str] = Field(..., description="List of wheel files in package directory")
    python_version: Optional[str] = Field(None, description="Python version from config/python_version.txt")
    has_app_config: bool = Field(..., description="Presence of app.yml")

    @property
    def is_valid(self) -> bool:
        """Check if the zip file is valid according to the spec"""
        return (
            self.version == "0.1.0"
            and self.has_pylock
            and len(self.wheel_files) > 0
            and self.python_version is not None
            and self.has_app_config
        )

    def get_validation_errors(self) -> List[str]:
        """Return a list of validation errors"""
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


def is_valid_app_zip(zip_path: str) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate if a zip file follows the App Zip Format 0.1.0 specification

    Args:
        zip_path: Path to the zip file

    Returns:
        Dictionary with validation results and errors if any
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            file_list = zip_file.namelist()

            # Check app_zip_version.txt
            version_file = "app/app_zip_version.txt"
            version = "unknown"
            if version_file in file_list:
                with zip_file.open(version_file) as f:
                    version = f.read().decode("utf-8").strip()

            # Check pylock.toml
            has_pylock = "app/pylock.toml" in file_list

            # Check for wheel files in package directory
            wheel_files = [f for f in file_list if f.startswith("app/package/") and f.endswith(".whl")]

            # Check python_version.txt
            python_version = None
            python_version_file = "app/config/python_version.txt"
            if python_version_file in file_list:
                with zip_file.open(python_version_file) as f:
                    python_version = f.read().decode("utf-8").strip()

            # Check app.yml
            has_app_config = "app/config/app.yml" in file_list

            # Validate structure
            validator = AppZipValidator(
                version=version,
                has_pylock=has_pylock,
                wheel_files=wheel_files,
                python_version=python_version,
                has_app_config=has_app_config,
            )

            return {"valid": validator.is_valid, "errors": validator.get_validation_errors()}

    except zipfile.BadZipFile:
        return {"valid": False, "errors": ["Not a valid zip file"]}
    except Exception as e:
        return {"valid": False, "errors": [f"Error validating zip: {str(e)}"]}


def print_validation_result(zip_path: str, result: Dict[str, Union[bool, List[str]]], file=sys.stdout):
    """
    Print validation results in a user-friendly format

    Args:
        zip_path: Path to the validated zip file
        result: Validation result dictionary
        file: Output stream (default: sys.stdout)
    """
    zip_name = Path(zip_path).name

    if result["valid"]:
        print(f"✅ {zip_name}: Valid App Zip (format 0.1.0)", file=file)
    else:
        print(f"❌ {zip_name}: Invalid App Zip", file=file)
        if result["errors"]:
            print("\nValidation errors:", file=file)
            for i, error in enumerate(result["errors"], 1):
                print(f"  {i}. {error}", file=file)
            print(file=file)
        print("The zip file does not conform to App Zip Format 0.1.0 specification.", file=file)


if __name__ == "__main__":
    app()
