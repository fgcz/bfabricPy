#!/usr/bin/env python3
"""
Test suite for extract_changelog.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add parent directory to path to import the script
sys.path.append(str(Path(__file__).parents[1]))
from extract_changelog import extract_changelog_entry


class TestExtractChangelog(unittest.TestCase):

    def test_extract_changelog_entry(self):
        # Sample changelog content
        changelog_content = """# Changelog

## [1.1.0] - 2025-04-15
### Added
- New feature X
- New feature Y

### Fixed
- Bug fix A
- Bug fix B

## [1.0.0] - 2025-03-15
### Added
- Initial release
"""

        # Test extracting existing version
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=changelog_content)):
                result = extract_changelog_entry("fake_path.md", "1.1.0")
                self.assertIn("## [1.1.0]", result)
                self.assertIn("New feature X", result)
                self.assertIn("Bug fix B", result)
                self.assertNotIn("## [1.0.0]", result)

        # Test extracting another version
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=changelog_content)):
                result = extract_changelog_entry("fake_path.md", "1.0.0")
                self.assertIn("## [1.0.0]", result)
                self.assertIn("Initial release", result)
                self.assertNotIn("## [1.1.0]", result)

        # Test extracting non-existent version
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=changelog_content)):
                result = extract_changelog_entry("fake_path.md", "2.0.0")
                self.assertEqual(result, "")

        # Test with non-existent file
        with patch("os.path.isfile", return_value=False):
            result = extract_changelog_entry("non_existent_file.md", "1.0.0")
            self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
