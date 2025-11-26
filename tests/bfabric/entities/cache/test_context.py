import pytest

from bfabric.entities.cache.context import _get_config_dict


class _Mocky:
    ENDPOINT = "mocky"


@pytest.fixture(params=["str", "entity_type"])
def entity_ref(request):
    # NOTE: entity_type is deprecated
    match request.param:
        case "str":
            return "mocky"
        case "entity_type":
            return _Mocky


@pytest.fixture(params=["single", "list", "dict"])
def cache_config(request, entity_ref):
    match request.param:
        case "single":
            return entity_ref
        case "list":
            return [entity_ref]
        case "dict":
            return {entity_ref: 3}


def test_get_config_dict(cache_config):
    config_dict = _get_config_dict(cache_config, max_size=3)
    assert config_dict == {"mocky": 3}


def test_get_config_dict_lower_case():
    config_dict = _get_config_dict({"MoCkY": 5}, max_size=0)
    assert config_dict == {"mocky": 5}
