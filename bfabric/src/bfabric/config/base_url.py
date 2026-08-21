"""The type of a B-Fabric instance base URL."""

from __future__ import annotations

from pydantic import AnyHttpUrl, GetCoreSchemaHandler, TypeAdapter, ValidationError
from pydantic_core import core_schema


class BaseUrl(str):
    """A validated B-Fabric instance base URL, without a trailing slash, e.g. ``https://x.uzh.ch/bfabric``.

    A ``str`` subclass, because the value is interpolated into request URLs and used as a cache key --
    while still being a type the checker can tell apart from a string that never passed through here.
    Construction is idempotent, which is what a cache key needs.
    """

    def __new__(cls, value: str) -> BaseUrl:
        if isinstance(value, cls):
            return value
        try:
            url = TypeAdapter(AnyHttpUrl).validate_python(value)
        except ValidationError as error:
            raise ValueError(f"Not a valid http(s) URL: {value!r}") from error
        # The strip has to come after validation: AnyHttpUrl re-adds the slash for an empty path.
        return super().__new__(cls, str(url).rstrip("/"))

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        _ = source_type, handler
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
