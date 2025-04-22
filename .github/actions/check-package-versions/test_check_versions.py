#!/usr/bin/env python3
"""
Test suite for check_versions.py using pytest
"""

import pytest

from check_versions import get_local_version, check_pypi_version, sort_packages, check_packages


def test_get_local_version_existing_dir(mocker):
    """Test get_local_version with existing directory"""
    # Setup
    mocker.patch("subprocess.check_output", return_value="1.0.0\n")
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.chdir")  # Mock os.chdir to prevent actual directory change

    # Test
    result = get_local_version("test_package")
    assert result == "1.0.0"


def test_get_local_version_nonexistent_dir(mocker):
    """Test get_local_version with non-existent directory"""
    # Setup
    mocker.patch("os.path.isdir", return_value=False)

    # Test
    result = get_local_version("non_existent_package")
    assert result is None


def test_get_local_version_subprocess_error(mocker):
    """Test get_local_version with subprocess error"""
    # Setup
    mocker.patch("subprocess.check_output", side_effect=Exception("Command failed"))
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.chdir")

    # Test
    result = get_local_version("error_package")
    assert result is None


@pytest.mark.parametrize(
    "response_status,releases,version,expected",
    [
        # Version exists on PyPI, no release needed
        (200, {"1.0.0": [], "1.1.0": []}, "1.0.0", False),
        # Version doesn't exist on PyPI, release needed
        (200, {"1.0.0": []}, "1.1.0", True),
        # Package doesn't exist on PyPI, release needed
        (404, {}, "1.0.0", True),
    ],
)
def test_check_pypi_version(mocker, response_status, releases, version, expected):
    """Test check_pypi_version with various scenarios"""
    # Setup mock response
    mock_response = mocker.MagicMock()
    mock_response.status_code = response_status
    mock_response.json.return_value = {"releases": releases}

    # Mock requests.get
    mocker.patch("requests.get", return_value=mock_response)

    # Test
    result = check_pypi_version("test_package", version)
    assert result == expected


@pytest.mark.parametrize(
    "packages,priority_order,expected",
    [
        # Normal case with all packages
        (
            ["bfabric_app_runner", "bfabric", "bfabric_scripts"],
            ["bfabric", "bfabric_scripts", "bfabric_app_runner"],
            ["bfabric", "bfabric_scripts", "bfabric_app_runner"],
        ),
        # Case with missing package
        (
            ["bfabric_app_runner", "bfabric"],
            ["bfabric", "bfabric_scripts", "bfabric_app_runner"],
            ["bfabric", "bfabric_app_runner"],
        ),
    ],
)
def test_sort_packages(packages, priority_order, expected):
    """Test sort_packages with different package lists"""
    result = sort_packages(packages, priority_order)
    assert result == expected


@pytest.mark.parametrize(
    "packages,force_packages,expected",
    [
        # Normal check, only bfabric needs release
        (["bfabric", "bfabric_scripts"], [], ["bfabric"]),
        # Force release for bfabric_scripts
        (["bfabric", "bfabric_scripts"], ["bfabric_scripts"], ["bfabric_scripts"]),
    ],
)
def test_check_packages(mocker, packages, force_packages, expected):
    """Test check_packages with different scenarios"""
    # Setup
    mocker.patch(
        "check_versions.get_local_version",
        side_effect=lambda pkg: {"bfabric": "1.0.0", "bfabric_scripts": "2.0.0"}.get(pkg),
    )
    mocker.patch(
        "check_versions.check_pypi_version",
        side_effect=lambda pkg, ver, url: pkg == "bfabric",  # Only bfabric needs release
    )

    # Test
    result = check_packages(packages, force_packages=force_packages)
    assert result == expected
