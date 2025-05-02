from pathlib import Path

from bfabric_app_runner.cli_uv.wheel import infer_app_module_from_wheel


def test_infer_app_module_from_wheel():
    module = "somewhere/dist/my_package-1.2.3.dev9-py3-none-any.whl"
    assert infer_app_module_from_wheel(Path(module)) == "my_package"
