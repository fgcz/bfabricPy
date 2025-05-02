from pathlib import Path

from wheel_filename import parse_wheel_filename


def infer_app_module_from_wheel(app_pkg: Path) -> str:
    """Given a wheel file, infers the module name which can be used for the app dispatch."""
    file_name = Path(app_pkg).name
    if file_name.lower().endswith(".whl"):
        # Extract the module name from the wheel file name
        wheel_info = parse_wheel_filename(file_name)
        return wheel_info.project
    else:
        raise ValueError(f"Invalid wheel file name: {file_name}")
