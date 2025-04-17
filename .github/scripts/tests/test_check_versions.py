#!/usr/bin/env python3
"""
Test suite for check_versions.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the script
sys.path.append(str(Path(__file__).parents[1]))
from check_versions import get_local_version, check_pypi_version, sort_packages, check_packages


class TestCheckVersions(unittest.TestCase):

    @patch("subprocess.check_output")
    def test_get_local_version(self, mock_check_output):
        # Setup
        mock_check_output.return_value = "1.0.0\n"

        # Test with existing directory
        with patch("os.path.isdir", return_value=True):
            with patch("os.chdir"):  # Mock os.chdir to prevent actual directory change
                result = get_local_version("test_package")
                self.assertEqual(result, "1.0.0")

        # Test with non-existent directory
        with patch("os.path.isdir", return_value=False):
            result = get_local_version("non_existent_package")
            self.assertIsNone(result)

        # Test with subprocess error
        mock_check_output.side_effect = Exception("Command failed")
        with patch("os.path.isdir", return_value=True):
            with patch("os.chdir"):
                result = get_local_version("error_package")
                self.assertIsNone(result)

    @patch("requests.get")
    def test_check_pypi_version(self, mock_get):
        # Setup mock response for existing version
        mock_response_exists = MagicMock()
        mock_response_exists.status_code = 200
        mock_response_exists.json.return_value = {"releases": {"1.0.0": [], "1.1.0": []}}

        # Setup mock response for non-existing version
        mock_response_not_exists = MagicMock()
        mock_response_not_exists.status_code = 200
        mock_response_not_exists.json.return_value = {"releases": {"1.0.0": []}}

        # Setup mock response for package not found
        mock_response_not_found = MagicMock()
        mock_response_not_found.status_code = 404

        # Test existing version
        mock_get.return_value = mock_response_exists
        result = check_pypi_version("test_package", "1.0.0")
        self.assertFalse(result)  # Should not need release

        # Test non-existing version
        mock_get.return_value = mock_response_not_exists
        result = check_pypi_version("test_package", "1.1.0")
        self.assertFalse(result)  # Should need release

        # Test package not found
        mock_get.return_value = mock_response_not_found
        result = check_pypi_version("non_existent_package", "1.0.0")
        self.assertTrue(result)  # Should need release

    def test_sort_packages(self):
        # Setup
        packages = ["bfabric_app_runner", "bfabric", "bfabric_scripts"]
        priority_order = ["bfabric", "bfabric_scripts", "bfabric_app_runner"]

        # Test sorting
        result = sort_packages(packages, priority_order)
        self.assertEqual(result, ["bfabric", "bfabric_scripts", "bfabric_app_runner"])

        # Test with missing package
        packages = ["bfabric_app_runner", "bfabric"]
        result = sort_packages(packages, priority_order)
        self.assertEqual(result, ["bfabric", "bfabric_app_runner"])

    @patch("check_versions.get_local_version")
    @patch("check_versions.check_pypi_version")
    def test_check_packages(self, mock_check_pypi, mock_get_local):
        # Setup
        mock_get_local.side_effect = lambda pkg: {"bfabric": "1.0.0", "bfabric_scripts": "2.0.0"}.get(pkg)
        mock_check_pypi.side_effect = lambda pkg, ver, url: pkg == "bfabric"  # Only bfabric needs release

        # Test normal check
        result = check_packages(["bfabric", "bfabric_scripts"])
        self.assertEqual(result, ["bfabric"])

        # Test force release
        result = check_packages(["bfabric", "bfabric_scripts"], force_packages=["bfabric_scripts"])
        self.assertEqual(result, ["bfabric_scripts"])


if __name__ == "__main__":
    unittest.main()
