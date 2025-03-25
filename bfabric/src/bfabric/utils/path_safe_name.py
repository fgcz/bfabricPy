import re
from typing import Annotated
from pydantic import BeforeValidator

# Regex pattern to match any characters that aren't alphanumeric, underscore, or hyphen
_regex = re.compile(r"[^a-zA-Z0-9_-]+")


def path_safe_name(name: str) -> str:
    """
    Convert a string to a filesystem-safe format by replacing unsafe characters with underscores.

    Args:
        name: The string to be converted to a path-safe format

    Returns:
        A string with all characters not matching [a-zA-Z0-9_-] replaced with underscores

    Example:
        >>> path_safe_name("Hello World!")
        'Hello_World_'
        >>> path_safe_name("file:name.txt")
        'file_name_txt'
    """
    return _regex.sub("_", name)


# Custom type that automatically converts strings to path-safe format
PathSafeStr = Annotated[str, BeforeValidator(path_safe_name)]
"""
A custom Pydantic type that automatically sanitizes strings for safe use in file paths.
When a field is annotated with this type, any unsafe characters will be replaced with underscores.

Example:
    >>> from pydantic import BaseModel
    >>> class FileModel(BaseModel):
    ...     filename: PathSafeStr
    ...
    >>> file = FileModel(filename="my file:name.txt")
    >>> file.filename
    'my_file_name_txt'
"""
