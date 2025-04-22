from pathlib import Path

import pytest

from extract_changelog import extract_changelog_entry


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).parents[3]


def test_extract_changelog(repo_root):
    path = repo_root / "bfabric" / "docs" / "changelog.md"
    result = extract_changelog_entry(str(path), "1.13.24")
    assert "2025-04-08" in result
    assert "### Removed" in result
