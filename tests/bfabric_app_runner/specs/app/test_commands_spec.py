import pytest

from bfabric_app_runner.specs.app.commands_spec import (
    CommandShell,
    CommandExec,
    CommandsSpec,
)


class TestCommandShell:
    def test_basic(self):
        """Test basic shell command parsing"""
        cmd = CommandShell(command="echo hello")
        result = cmd.to_shell()
        assert result == ["echo", "hello"]

    def test_with_quotes(self):
        """Test shell command with quoted arguments"""
        cmd = CommandShell(command='echo "hello world"')
        result = cmd.to_shell()
        assert result == ["echo", "hello world"]

    def test_complex_command(self):
        """Test complex shell command with multiple arguments and quotes"""
        cmd = CommandShell(command="python3 -c \"import sys; print('Hello from Python')\" --verbose")
        result = cmd.to_shell()
        assert result == [
            "python3",
            "-c",
            "import sys; print('Hello from Python')",
            "--verbose",
        ]


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
