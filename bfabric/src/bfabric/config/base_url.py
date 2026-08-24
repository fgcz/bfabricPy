"""The type of a B-Fabric instance base URL."""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, GetCoreSchemaHandler, TypeAdapter, ValidationError
from pydantic_core import core_schema

_SERVLET = "bfabric"
"""The path segment every B-Fabric instance is served under.

Already assumed throughout: ``EngineSUDS`` fetches ``{base_url}/{endpoint}?wsdl`` and ``EntityUri``
rejects a URI whose first path segment is not this, so a base URL that stops short of the servlet
(or reaches past it) cannot work. Requiring it here turns a later 404 -- or an
``Unsupported B-Fabric instances`` mismatch against a URI-derived instance -- into one error at
config load.
"""


def _segments(path: str) -> list[str]:
    return [segment for segment in path.split("/") if segment]


def _nearest_instance_url(canonical: str) -> str:
    """The instance URL *canonical* was probably meant to be: truncated at its ``bfabric`` segment, else appended.

    Covers the two mistakes actually seen: a bare host, and a URL reaching past the servlet root
    (a REST endpoint copied out of a log).
    """
    parts = urlsplit(canonical)
    segments = _segments(parts.path)
    if _SERVLET in segments:
        segments = segments[: segments.index(_SERVLET) + 1]
    else:
        segments.append(_SERVLET)
    return f"{parts.scheme}://{parts.netloc}/" + "/".join(segments)


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
        canonical = str(url).rstrip("/")
        parts = urlsplit(canonical)
        segments = _segments(parts.path)
        # The last path segment, not a string suffix -- `https://bfabric` would pass that while
        # naming a host rather than a servlet. A query or fragment is refused too: it would survive
        # into every interpolated request URL.
        if not segments or segments[-1] != _SERVLET or parts.query or parts.fragment:
            raise ValueError(
                f"{value!r} is not a B-Fabric instance URL: it must end in {'/' + _SERVLET!r} -- "
                f"did you mean {_nearest_instance_url(canonical)!r}?"
            )
        return super().__new__(cls, canonical)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        _ = source_type, handler
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())
