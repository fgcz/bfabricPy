"""Unit tests for ASGI root_path helpers.

Expected helpers (if your implementation puts them elsewhere, adjust the
import below — the names and behaviour are what the tests pin down):

    from bfabric_asgi_auth.middleware import _strip_root_path, _prepend_root_path

`_strip_root_path(scope)` returns the app-local path.
`_prepend_root_path(url, scope)` prepends scope['root_path'] to a
root-relative URL; leaves absolute and relative URLs alone.
"""

from __future__ import annotations

import pytest

from bfabric_asgi_auth.middleware import _prepend_root_path, _strip_root_path


def _scope(path: str = "", root_path: str | None = "") -> dict:
    s = {"type": "http", "path": path}
    if root_path is not None:
        s["root_path"] = root_path
    return s


class TestStripRootPathNoOp:
    """Cases where the helper must return path unchanged."""

    def test_empty_root_path(self) -> None:
        assert _strip_root_path(_scope("/landing", "")) == "/landing"

    def test_missing_root_path_key(self) -> None:
        assert _strip_root_path(_scope("/landing", root_path=None)) == "/landing"

    def test_root_slash_is_treated_as_empty(self) -> None:
        # "/" after rstrip("/") is "" — so no-op.
        assert _strip_root_path(_scope("/landing", "/")) == "/landing"
        assert _strip_root_path(_scope("/", "/")) == "/"

    def test_empty_path(self) -> None:
        assert _strip_root_path(_scope("", "/queue-gen")) == ""

    def test_path_already_stripped_by_upstream(self) -> None:
        # Caddy's `uri strip_prefix` has already removed /queue-gen.
        assert _strip_root_path(_scope("/landing", "/queue-gen")) == "/landing"

    def test_path_totally_unrelated_to_root(self) -> None:
        assert _strip_root_path(_scope("/other/page", "/queue-gen")) == "/other/page"


class TestStripRootPathHappyPath:
    """root_path present in path — strip it."""

    def test_single_segment(self) -> None:
        assert _strip_root_path(_scope("/queue-gen/landing", "/queue-gen")) == "/landing"

    def test_multi_segment(self) -> None:
        assert _strip_root_path(_scope("/queue-gen/a/b/c", "/queue-gen")) == "/a/b/c"

    def test_root_path_with_trailing_slash(self) -> None:
        # "/queue-gen/" should behave identically to "/queue-gen".
        assert _strip_root_path(_scope("/queue-gen/landing", "/queue-gen/")) == "/landing"

    def test_path_is_root_plus_slash(self) -> None:
        # App's index path.
        assert _strip_root_path(_scope("/queue-gen/", "/queue-gen")) == "/"

    def test_path_preserves_query_is_not_this_helper(self) -> None:
        # scope["path"] never contains the query string; scope["query_string"]
        # is separate. This test documents the assumption.
        scope = _scope("/queue-gen/landing", "/queue-gen")
        scope["query_string"] = b"token=abc"
        assert _strip_root_path(scope) == "/landing"


class TestStripRootPathExactMatch:
    """path == root_path (no trailing slash)."""

    @pytest.mark.parametrize(
        "path,root,expected",
        [
            # Policy: return "" on exact match (Starlette's convention is
            # "/"; either is defensible as long as it's consistent).
            ("/queue-gen", "/queue-gen", ""),
            ("/queue-gen", "/queue-gen/", ""),
        ],
    )
    def test_exact_match_returns_empty(self, path: str, root: str, expected: str) -> None:
        assert _strip_root_path(_scope(path, root)) == expected


class TestStripRootPathPrefixBoundary:
    """Critical: must not strip when prefix is not a path boundary."""

    def test_similar_prefix_not_stripped(self) -> None:
        # /queue-genesis is NOT /queue-gen + "/..."; routing-critical case.
        assert _strip_root_path(_scope("/queue-genesis/foo", "/queue-gen")) == "/queue-genesis/foo"

    def test_one_char_off(self) -> None:
        assert _strip_root_path(_scope("/queue-genX", "/queue-gen")) == "/queue-genX"

    def test_no_boundary_slash(self) -> None:
        # "/queue-gen" vs "/queue-genfoo" — must not strip.
        assert _strip_root_path(_scope("/queue-genfoo", "/queue-gen")) == "/queue-genfoo"


class TestStripRootPathCaseSensitivity:
    """URLs are case-sensitive per RFC 3986."""

    def test_case_mismatch_does_not_strip(self) -> None:
        assert _strip_root_path(_scope("/Queue-gen/landing", "/queue-gen")) == "/Queue-gen/landing"

    def test_uppercase_root_does_not_match_lowercase_path(self) -> None:
        assert _strip_root_path(_scope("/queue-gen/landing", "/Queue-Gen")) == "/queue-gen/landing"


class TestStripRootPathUnicode:
    """Non-ASCII paths should work exactly like ASCII."""

    def test_accented_root(self) -> None:
        assert _strip_root_path(_scope("/café/landing", "/café")) == "/landing"

    def test_space_in_root(self) -> None:
        # Unusual but legal as an ASGI string. (URL-encoded on the wire,
        # decoded by the ASGI server before scope.)
        assert _strip_root_path(_scope("/my app/landing", "/my app")) == "/landing"


class TestStripRootPathRedundantSlashes:
    """Don't invent URL normalization — just boundary-check literally."""

    def test_double_slash_in_path_not_matched(self) -> None:
        # "/queue-gen//landing" does NOT start with "/queue-gen/" followed
        # by a non-slash — but it DOES start with "/queue-gen/". Per the
        # reference impl, this strips to "/landing". Document what you want.
        # (If your policy is "don't normalize anything", the result is
        # "//landing" — update this assertion to match your choice.)
        result = _strip_root_path(_scope("/queue-gen//landing", "/queue-gen"))
        assert result in {"/landing", "//landing"}


class TestPrependRootPathNoOp:
    """Cases where the url must be returned unchanged."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/foo",
            "http://example.com/foo",
            "//example.com/foo",  # protocol-relative
        ],
    )
    def test_absolute_url_unchanged(self, url: str) -> None:
        assert _prepend_root_path(url, _scope(root_path="/queue-gen")) == url

    @pytest.mark.parametrize(
        "url",
        [
            "foo",
            "./foo",
            "../foo",
            "foo/bar",
        ],
    )
    def test_relative_url_unchanged(self, url: str) -> None:
        # Browser resolves relative URLs against the current page —
        # no prefix needed.
        assert _prepend_root_path(url, _scope(root_path="/queue-gen")) == url

    def test_empty_root_path(self) -> None:
        assert _prepend_root_path("/landing", _scope(root_path="")) == "/landing"

    def test_missing_root_path(self) -> None:
        assert _prepend_root_path("/landing", _scope(root_path=None)) == "/landing"

    def test_empty_url(self) -> None:
        # Don't crash on empty string — return it unchanged.
        assert _prepend_root_path("", _scope(root_path="/queue-gen")) == ""


class TestPrependRootPathHappyPath:
    """Root-relative URLs (the target case)."""

    def test_slash_becomes_root_plus_slash(self) -> None:
        assert _prepend_root_path("/", _scope(root_path="/queue-gen")) == "/queue-gen/"

    def test_landing(self) -> None:
        assert _prepend_root_path("/landing", _scope(root_path="/queue-gen")) == "/queue-gen/landing"

    def test_multi_segment(self) -> None:
        assert _prepend_root_path("/a/b/c", _scope(root_path="/queue-gen")) == "/queue-gen/a/b/c"

    def test_root_trailing_slash_normalized(self) -> None:
        # root_path="/queue-gen/" must yield the same result as "/queue-gen".
        assert _prepend_root_path("/landing", _scope(root_path="/queue-gen/")) == "/queue-gen/landing"

    def test_preserves_query_string(self) -> None:
        assert (
            _prepend_root_path("/landing?token=abc", _scope(root_path="/queue-gen")) == "/queue-gen/landing?token=abc"
        )

    def test_preserves_fragment(self) -> None:
        assert _prepend_root_path("/landing#section", _scope(root_path="/queue-gen")) == "/queue-gen/landing#section"


class TestPrependRootPathDoublePrefix:
    """Policy question: what if the url already starts with root_path?"""

    def test_double_prefix_policy(self) -> None:
        # Two defensible choices:
        # a) naive concat → "/queue-gen/queue-gen/already"
        # b) idempotent  → "/queue-gen/already"
        # Pick one and document in the helper's docstring. This test just
        # pins the chosen behaviour — update the expected value to match.
        result = _prepend_root_path("/queue-gen/already", _scope(root_path="/queue-gen"))
        assert result in {"/queue-gen/queue-gen/already", "/queue-gen/already"}


class TestPrependRootPathRoundTrip:
    """`strip(prepend(url)) == url` for root-relative URLs — useful invariant."""

    @pytest.mark.parametrize(
        "url,root",
        [
            ("/landing", "/queue-gen"),
            ("/a/b/c", "/queue-gen"),
            ("/", "/queue-gen"),
            ("/landing", ""),
            ("/landing", "/"),
        ],
    )
    def test_roundtrip(self, url: str, root: str) -> None:
        prepended = _prepend_root_path(url, _scope(root_path=root))
        # After prepending and receiving back on the same mount, stripping
        # should yield the original URL.
        scope = _scope(path=prepended, root_path=root)
        assert _strip_root_path(scope) == url
