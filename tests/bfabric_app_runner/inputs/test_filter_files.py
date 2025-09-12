from bfabric_app_runner.inputs._filter_files import filter_files

# TODO these test cases should become more explicit before the future gets used widely
#      regarding the full prefix path, i.e. to which part of the path the pattern gets applied


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


def test_filter_files_with_key():
    """Test file filtering with key parameter."""
    files = [{"name": "file1.txt"}, {"name": "file2.py"}, {"name": "file3.log"}]
    result = filter_files(files, ["*.txt"], [], key="name")
    assert result == [{"name": "file1.txt"}]
