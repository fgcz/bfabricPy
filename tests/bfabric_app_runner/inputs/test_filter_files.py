from bfabric_app_runner.inputs._filter_files import filter_files


def test_filter_files_no_patterns():
    """Test file filtering with no patterns."""
    files = ["file1.txt", "file2.py", "file3.log"]
    result = filter_files(files, [], [])
    assert result == files


def test_filter_files_include_patterns():
    """Test file filtering with include patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "file4.txt"]
    result = filter_files(files, ["*.txt"], [])
    assert result == ["file1.txt", "file4.txt"]


def test_filter_files_exclude_patterns():
    """Test file filtering with exclude patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "file4.txt"]
    result = filter_files(files, [], ["*.log"])
    assert result == ["file1.txt", "file2.py", "file4.txt"]


def test_filter_files_include_and_exclude():
    """Test file filtering with both include and exclude patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "test.txt"]
    result = filter_files(files, ["*.txt"], ["test*"])
    assert result == ["file1.txt"]
