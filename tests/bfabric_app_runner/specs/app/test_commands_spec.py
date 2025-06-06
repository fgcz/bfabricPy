import pytest

from bfabric_app_runner.specs.app.commands_spec import (
    CommandExec,
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
