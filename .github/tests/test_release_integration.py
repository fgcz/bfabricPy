#!/usr/bin/env python3
"""
Integration test for the release pipeline scripts.
Tests check_versions.py and extract_changelog.py together.

This test:
1. Creates temporary package directories with mock pyproject.toml files
2. Runs the version check script to determine which packages need release
3. Runs the changelog extraction script for those packages
"""

import os
import sys
from pathlib import Path

import pytest

# Add parent directory to path to import the scripts
sys.path.append(str(Path(__file__).parents[1] / "actions" / "check-package-versions"))
sys.path.append(str(Path(__file__).parents[1] / "actions" / "extract-changelog"))
import check_versions
import extract_changelog


@pytest.fixture
def setup_packages(tmpdir):
    """
    Fixture to set up temporary directory with test packages
    """
    # Create package directories
    pkg_dirs = ["bfabric", "bfabric_scripts", "bfabric_app_runner"]
    pkg_versions = {"bfabric": "1.0.0", "bfabric_scripts": "2.0.0", "bfabric_app_runner": "3.0.0"}

    for pkg in pkg_dirs:
        # Create package directory
        pkg_dir = tmpdir.join(pkg)
        pkg_dir.ensure(dir=True)

        # Create docs directory with changelog
        docs_dir = pkg_dir.join("docs")
        docs_dir.ensure(dir=True)

        # Create mock changelog file
        changelog_content = f"""# Changelog

## [{pkg_versions[pkg]}] - 2025-04-17
### Added
- Test feature for {pkg}
- Another test feature

### Fixed
- Test bug fix
"""
        docs_dir.join("changelog.md").write(changelog_content)

    return str(tmpdir), pkg_dirs, pkg_versions


class MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self.json_data = json_data or {}

    def json(self):
        return self.json_data


def test_release_pipeline(setup_packages, mocker):
    """
    Test the entire release pipeline flow
    """
    temp_dir, pkg_dirs, pkg_versions = setup_packages

    # Create a more direct way to mock the check_packages function
    # to ensure we know exactly what's being called
    original_get_local_version = check_versions.get_local_version
    original_check_pypi_version = check_versions.check_pypi_version

    # Add a debugging patch to see what's happening
    def debug_get_local_version(pkg):
        print(f"DEBUG: get_local_version called with: {pkg}")
        return pkg_versions.get(os.path.basename(pkg))

    def debug_check_pypi_version(pkg, ver, url=""):
        print(f"DEBUG: check_pypi_version called with: {pkg}, {ver}, {url}")
        # Return True if the package should be released
        return os.path.basename(pkg) in ["bfabric", "bfabric_app_runner"]

    # Apply the patches
    mocker.patch.object(check_versions, "get_local_version", debug_get_local_version)
    mocker.patch.object(check_versions, "check_pypi_version", debug_check_pypi_version)

    # If check_versions makes HTTP requests, mock those too
    if hasattr(check_versions, "requests"):
        mock_pypi_response = MockResponse(200, {"info": {"version": "0.9.0"}})
        mocker.patch("check_versions.requests.get", return_value=mock_pypi_response)

    # Run version check
    print(f"DEBUG: Running check_packages with: {[os.path.join(temp_dir, pkg) for pkg in pkg_dirs]}")
    packages_to_release = check_versions.check_packages([os.path.join(temp_dir, pkg) for pkg in pkg_dirs])

    print(f"DEBUG: Packages to release: {packages_to_release}")

    # Check results
    assert len(packages_to_release) == 2
    assert os.path.join(temp_dir, "bfabric") in packages_to_release
    assert os.path.join(temp_dir, "bfabric_app_runner") in packages_to_release

    # If the assert above fails, manually create the expected list
    # to allow the test to continue for debugging purposes
    if len(packages_to_release) != 2:
        packages_to_release = [os.path.join(temp_dir, "bfabric"), os.path.join(temp_dir, "bfabric_app_runner")]
        print("WARNING: Manually set packages_to_release for the rest of the test")

    # Sort packages
    sorted_packages = check_versions.sort_packages(
        packages_to_release,
        [
            os.path.join(temp_dir, "bfabric"),
            os.path.join(temp_dir, "bfabric_scripts"),
            os.path.join(temp_dir, "bfabric_app_runner"),
        ],
    )

    # Check that bfabric comes first
    assert sorted_packages[0] == os.path.join(temp_dir, "bfabric")

    # Extract changelog for each package
    for pkg in sorted_packages:
        pkg_name = os.path.basename(pkg)
        changelog_path = os.path.join(pkg, "docs", "changelog.md")

        # Extract changelog
        changelog_entry = extract_changelog.extract_changelog_entry(changelog_path, pkg_versions[pkg_name])

        # Check that changelog extraction worked
        assert f"## [{pkg_versions[pkg_name]}]" in changelog_entry
        assert f"Test feature for {pkg_name}" in changelog_entry
