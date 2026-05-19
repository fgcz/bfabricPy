import pytest
from bfabric.entities import Parameter


@pytest.fixture(params=["normal", "required-false"])
def scenario(request):
    return request.param


@pytest.fixture
def data_dict(scenario):
    data = {"classname": "parameter", "id": 1234, "key": "test_key"}
    if scenario == "normal":
        data["required"] = "true"
        data["value"] = "test_value"
    elif scenario == "required-false":
        data["required"] = "false"
    else:
        raise NotImplementedError
    return data


@pytest.fixture
def parameter(data_dict, bfabric_instance):
    return Parameter(data_dict=data_dict, client=None, bfabric_instance=bfabric_instance)


def test_key(parameter):
    assert parameter.key == "test_key"


def test_value(parameter, scenario):
    if scenario == "normal":
        assert parameter.value == "test_value"
    else:
        assert parameter.value == ""
