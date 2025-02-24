import pytest
from bfabric_app_runner.specs.config_interpolation import (
    Variables,
    VariablesApp,
    interpolate_config_strings,
)
from mako.exceptions import MakoException


@pytest.fixture
def basic_variables():
    return Variables(app=VariablesApp(id=1000, name="Test Application", version="1.0.0"), workunit=None)


def test_variables_app_model():
    app = VariablesApp(id=2000, name="Test", version="1.0")
    assert app.id == 2000
    assert app.name == "Test"
    assert app.version == "1.0"


def test_variables_model(basic_variables):
    result = basic_variables.as_dict()
    assert isinstance(result, dict)
    assert "app" in result
    assert result["app"].id == 1000
    assert result["app"].name == "Test_Application"
    assert result["app"].version == "1.0.0"


def test_interpolate_simple_string(basic_variables):
    template = "App ${app.name} (${app.id}) version ${app.version}"
    result = interpolate_config_strings(template, basic_variables)
    assert result == "App Test_Application (1000) version 1.0.0"


def test_interpolate_dict(basic_variables):
    data = {
        "name": "${app.name}",
        "metadata": {"id": "${app.id}", "version": "${app.version}"},
    }
    result = interpolate_config_strings(data, basic_variables)
    assert result == {
        "name": "Test_Application",
        "metadata": {"id": "1000", "version": "1.0.0"},
    }


def test_interpolate_list(basic_variables):
    data = ["${app.name}", {"id": "${app.id}"}, ["${app.version}"]]
    result = interpolate_config_strings(data, basic_variables)
    assert result == ["Test_Application", {"id": "1000"}, ["1.0.0"]]


def test_interpolate_non_string_values(basic_variables):
    data = {
        "number": 42,
        "boolean": True,
        "none": None,
        "mixed": ["${app.id}", 123, True],
    }
    result = interpolate_config_strings(data, basic_variables)
    assert result == {
        "number": 42,
        "boolean": True,
        "none": None,
        "mixed": ["1000", 123, True],
    }


def test_interpolate_with_dict_variables():
    variables = {"app": {"id": "2000", "name": "Dict App", "version": "2.0.0"}, "workunit": None}
    template = "${app.name} ${app.version}"
    result = interpolate_config_strings(template, variables)
    assert result == "Dict_App 2.0.0"


def test_invalid_template_syntax(basic_variables):
    invalid_template = "${invalid.syntax"
    with pytest.raises(MakoException):
        interpolate_config_strings(invalid_template, basic_variables)


def test_missing_variable(basic_variables):
    template = "${app.missing}"
    with pytest.raises(Exception):  # Could be more specific depending on Mako's behavior
        interpolate_config_strings(template, basic_variables)


def test_empty_string_template(basic_variables):
    assert interpolate_config_strings("", basic_variables) == ""


def test_complex_nested_structure(basic_variables):
    data = {
        "app_info": {
            "details": [
                {"name": "${app.name}"},
                ["${app.id}", {"version": "${app.version}"}],
                123,
                "${app.name} v${app.version}",
            ]
        },
        "metadata": "${app.id}",
        "constants": [True, None, 42],
    }

    expected = {
        "app_info": {
            "details": [
                {"name": "Test_Application"},
                ["1000", {"version": "1.0.0"}],
                123,
                "Test_Application v1.0.0",
            ]
        },
        "metadata": "1000",
        "constants": [True, None, 42],
    }

    result = interpolate_config_strings(data, basic_variables)
    assert result == expected
