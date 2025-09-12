import fnmatch


def filter_files(files: list[str], include_patterns: list[str], exclude_patterns: list[str]) -> list[str]:
    """Filter files based on include and exclude patterns."""

    def should_include(file_path: str) -> bool:
        # If include patterns are specified, file must match at least one
        if include_patterns and not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
            return False
        # If exclude patterns are specified, file must not match any
        return not (exclude_patterns and any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns))

    return [file_path for file_path in files if should_include(file_path)]
