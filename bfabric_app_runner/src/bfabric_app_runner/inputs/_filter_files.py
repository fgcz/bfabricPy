import fnmatch
from typing import overload, TypeVar
import polars as pl

T = TypeVar("T")


@overload
def filter_files(
    files: list[str], include_patterns: list[str], exclude_patterns: list[str], *, key: None = None
) -> list[str]: ...


@overload
def filter_files(files: list[T], include_patterns: list[str], exclude_patterns: list[str], *, key: str) -> list[T]: ...


def filter_files(files, include_patterns, exclude_patterns, *, key=None):
    """Filter files based on include and exclude patterns."""
    return [
        file
        for file in files
        if _should_include(file if key is None else file[key], include_patterns, exclude_patterns)
    ]


def filter_dataframe(
    dataframe: pl.DataFrame, column: str, include_patterns: list[str], exclude_patterns: list[str]
) -> pl.DataFrame:
    return dataframe.filter(
        pl.col(column).map_elements(
            lambda x: _should_include(x, include_patterns, exclude_patterns),
            return_dtype=pl.Boolean,
        )
    )


def _should_include(file_path: str, include_patterns: list[str], exclude_patterns: list[str]) -> bool:
    # If include patterns are specified, file must match at least one
    if include_patterns and not any(fnmatch.fnmatch(file_path, pattern) for pattern in include_patterns):
        return False
    # If exclude patterns are specified, file must not match any
    return not (exclude_patterns and any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns))
