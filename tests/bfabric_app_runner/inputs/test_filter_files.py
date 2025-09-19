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


def test_filter_files_multiple_patterns():
    """Test file filtering with multiple include and exclude patterns."""
    files = ["file1.txt", "file2.py", "file3.log", "test.txt", "debug.log"]
    result = filter_files(files, ["*.txt", "*.py"], ["*.log", "test*"])
    assert result == ["file1.txt", "file2.py"]


def test_filter_files_with_key():
    """Test file filtering with key parameter."""
    files = [{"name": "file1.txt"}, {"name": "file2.py"}, {"name": "file3.log"}]
    result = filter_files(files, ["*.txt"], [], key="name")
    assert result == [{"name": "file1.txt"}]


def test_filter_files_with_key_complex():
    """Test file filtering with key parameter and complex patterns."""
    files = [
        {"path": "src/main.py", "size": 1024},
        {"path": "tests/test_main.py", "size": 512},
        {"path": "docs/readme.txt", "size": 256},
        {"path": "src/utils.py", "size": 2048},
    ]
    result = filter_files(files, ["src/*.py"], ["*main*"], key="path")
    assert result == [{"path": "src/utils.py", "size": 2048}]


def test_filter_files_no_matches():
    """Test file filtering when no files match include patterns."""
    files = ["file1.txt", "file2.py", "file3.log"]
    result = filter_files(files, ["*.csv"], [])
    assert result == []


def test_filter_files_empty_lists():
    """Test file filtering with empty file list."""
    result = filter_files([], ["*.txt"], ["*.log"])
    assert result == []


def test_filter_files_filename_vs_path_patterns():
    """Test explicit behavior of patterns on filenames vs full paths."""
    files = ["dir1/test.txt", "dir2/test.txt", "test.txt", "dir1/other.txt"]

    # Wildcard pattern matches filename anywhere
    result = filter_files(files, ["*.txt"], [])
    assert result == ["dir1/test.txt", "dir2/test.txt", "test.txt", "dir1/other.txt"]

    # Exact filename pattern only matches root level
    result = filter_files(files, ["test.txt"], [])
    assert result == ["test.txt"]

    # Directory pattern matches files in that directory
    result = filter_files(files, ["dir1/*.txt"], [])
    assert result == ["dir1/test.txt", "dir1/other.txt"]
