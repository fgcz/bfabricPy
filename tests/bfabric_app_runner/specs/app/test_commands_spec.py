from pathlib import Path

import pytest

from bfabric_app_runner.specs.app.commands_spec import (
    CommandExec,
    CommandPythonEnv,
    CommandsSpec,
)


class TestCommandsSpec:
    @staticmethod
    @pytest.fixture
    def data_command_exec():
        return {"type": "exec", "command": "bash -c 'echo hello world'"}

    @staticmethod
    def test_parse_exec(data_command_exec):
        data = {"dispatch": data_command_exec, "process": data_command_exec}
        parsed = CommandsSpec.model_validate(data)
        expected_command = CommandExec(command="bash -c 'echo hello world'")
        assert parsed.dispatch == expected_command
        assert parsed.process == expected_command
        assert parsed.collect is None

    @staticmethod
    def test_relative_paths_kept_without_spec_dir():
        """Relative paths are only resolved when a spec directory is passed as validation context."""
        parsed = CommandPythonEnv.model_validate({"pylock": "dist/pylock.toml", "command": "-m app"})
        assert parsed.pylock == Path("dist/pylock.toml")
