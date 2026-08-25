"""The type of a B-Fabric instance base URL."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, TypeAdapter, ValidationError
from pydantic_core import core_schema


class BaseUrl(str):
    """A validated B-Fabric instance URL, of the form ``http[s]://<host>/bfabric``."""

    def __new__(cls, value: str) -> BaseUrl:
        if isinstance(value, cls):
            return value
        try:
            url = TypeAdapter(AnyHttpUrl).validate_python(value)
        except ValidationError as error:
            raise ValueError(f"Not a valid http(s) URL: {value!r}") from error
        # Check that the URL ends in `/bfabric`.
        parts = urlsplit(str(url).rstrip("/"))
        segments = [segment for segment in parts.path.split("/") if segment]
        if segments[-1:] != ["bfabric"] or parts.query or parts.fragment:
            raise ValueError(f"{value!r} is not a B-Fabric instance URL: it must end in '/bfabric'")
        return super().__new__(cls, parts.geturl())

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: object, _handler: object) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
