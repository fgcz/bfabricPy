from __future__ import annotations

from typing import Any

from mako.template import Template


def interpolate_config_strings(data: Any, variables: dict[str, Any]) -> Any:
    """Recursively evaluates all strings in a data structure with Mako templates.

    This will not evaluate Mako templates in the YAML file itself, only in the individual strings.
    Since the current behavior is a subset of evaluating all strings in the YAML file, we could extend this later
    if it becomes necessary. However, it has the risk of making the config files more complex and should be avoided
    if possible.

    :param data: Any Python data structure (dict, list, str, etc.)
    :param variables: Dictionary of template variables and their values
    :return: The data structure with all strings evaluated
    """
    if isinstance(data, dict):
        return {key: interpolate_config_strings(value, variables) for key, value in data.items()}
    elif isinstance(data, list):
        return [interpolate_config_strings(item, variables) for item in data]
    elif isinstance(data, str):
        return str(Template(data).render(**variables))
    else:
        return data
