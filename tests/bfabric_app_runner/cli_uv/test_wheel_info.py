from pathlib import Path

import pytest

from bfabric_app_runner.cli_uv.wheel_info import infer_app_module_from_wheel, is_wheel_reference


@pytest.mark.parametrize(
    "deps_string, expected_val",
    [
        ("my_package-1.2.3.dev9-py3-none-any.whl", True),
        ("bfabric,my_package-1.2.3.dev9-py3-none-any.whl", False),
        ("numpy,polars", False),
        ("numpy", False),
    ],
)
def test_is_wheel_reference(deps_string: str, expected_val: bool):
    assert is_wheel_reference(deps_string) == expected_val


def test_infer_app_module_from_wheel():
    module = "somewhere/dist/my_package-1.2.3.dev9-py3-none-any.whl"
    assert infer_app_module_from_wheel(Path(module)) == "my_package"
