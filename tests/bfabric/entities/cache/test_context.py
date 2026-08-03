import pytest

from bfabric.entities.core.read_scope import _build_cache_config


@pytest.fixture(params=["single", "list", "dict"])
def cache_config(request):
    match request.param:
        case "single":
            return "mocky"
        case "list":
            return ["mocky"]
        case "dict":
            return {"mocky": 3}


def test_build_cache_config(cache_config):
    assert _build_cache_config(cache_config, max_size=3) == {"mocky": 3}


def test_build_cache_config_lower_case():
    assert _build_cache_config({"MoCkY": 5}, max_size=0) == {"mocky": 5}
