from __future__ import annotations

import pytest

from bfabric.config.base_url import BaseUrl
from bfabric.oauth import token_url


class TestTokenUrl:
    def test_appends_path(self):
        assert token_url(BaseUrl("https://example.com/bfabric")) == "https://example.com/bfabric/rest/oauth/token"

    def test_accepts_plain_str(self):
        assert token_url("https://example.com/bfabric") == "https://example.com/bfabric/rest/oauth/token"

    def test_validates_the_base_url(self):
        # Only that the validation happens -- what BaseUrl accepts is tested where BaseUrl lives.
        with pytest.raises(ValueError):
            token_url("https://example.com/notbfabric")
