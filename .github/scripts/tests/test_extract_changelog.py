#!/usr/bin/env python3
"""
Test suite for extract_changelog.py using pytest
"""

import sys
from pathlib import Path

# Add parent directory to path to import the script
sys.path.append(str(Path(__file__).parents[1]))
from extract_changelog import extract_changelog_entry


def test_extract_changelog_entry_with_existing_version(mocker):
    # Sample changelog content with escaped brackets
    changelog_content = """# Changelog

## \\[1.1.0\\] - 2025-04-15
### Added
- New feature X
- New feature Y

### Fixed
- Bug fix A
- Bug fix B

## \\[1.0.0\\] - 2025-03-15
### Added
- Initial release
"""

    # Mock file operations
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=changelog_content))

    # Test extracting version 1.1.0
    result = extract_changelog_entry("fake_path.md", "1.1.0")
    assert "## \\[1.1.0\\]" in result
    assert "New feature X" in result
    assert "Bug fix B" in result
    assert "## \\[1.0.0\\]" not in result


def test_extract_changelog_entry_with_another_version(mocker):
    # Sample changelog content with escaped brackets
    changelog_content = """# Changelog

## \\[1.1.0\\] - 2025-04-15
### Added
- New feature X
- New feature Y

### Fixed
- Bug fix A
- Bug fix B

## \\[1.0.0\\] - 2025-03-15
### Added
- Initial release
"""

    # Mock file operations
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=changelog_content))

    # Test extracting version 1.0.0
    result = extract_changelog_entry("fake_path.md", "1.0.0")
    assert "## \\[1.0.0\\]" in result
    assert "Initial release" in result
    assert "## \\[1.1.0\\]" not in result


def test_extract_changelog_entry_with_nonexistent_version(mocker):
    # Sample changelog content with escaped brackets
    changelog_content = """# Changelog

## \\[1.1.0\\] - 2025-04-15
### Added
- New feature X
- New feature Y

## \\[1.0.0\\] - 2025-03-15
### Added
- Initial release
"""

    # Mock file operations
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=changelog_content))

    # Test extracting non-existent version
    result = extract_changelog_entry("fake_path.md", "2.0.0")
    assert result == ""


def test_extract_changelog_entry_with_nonexistent_file(mocker):
    # Mock file check to return False (file doesn't exist)
    mocker.patch("os.path.isfile", return_value=False)

    # Test with non-existent file
    result = extract_changelog_entry("non_existent_file.md", "1.0.0")
    assert result == ""
