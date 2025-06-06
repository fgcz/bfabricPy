import os
from pathlib import Path

import pytest

from bfabric_app_runner.specs.app.commands_spec import (
    MountOptions,
    CommandDocker,
    CommandShell,
    CommandExec,
    CommandsSpec,
)


class TestMountOptions:
    def test_default_behavior(self, tmp_path):
        """Test collect method with default settings"""
        options = MountOptions()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        mounts = options.collect(work_dir)

        # Should have 2 default mounts: bfabric config and work dir
        assert len(mounts) == 2
        assert mounts[0] == (
            Path("~/.bfabricpy.yml").expanduser().absolute(),
            Path("/home/user/.bfabricpy.yml"),
            True,
        )
        assert mounts[1] == (work_dir.absolute(), work_dir, False)

    def test_with_custom_mounts(self, tmp_path):
        """Test collect method with both read-only and writeable mounts"""
        source_ro = tmp_path / "data"
        source_ro.mkdir()
        target_ro = Path("/container/data")

        source_rw = tmp_path / "shared"
        source_rw.mkdir()
        target_rw = Path("/container/shared")

        options = MountOptions(
            read_only=[(source_ro, target_ro)],
            writeable=[(source_rw, target_rw)],
            share_bfabric_config=False,  # Disable bfabric to simplify test
        )
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        mounts = options.collect(work_dir)

        # Should have 3 mounts: work_dir, read-only, and writeable
        assert len(mounts) == 3
        assert mounts[0] == (work_dir.absolute(), work_dir, False)
        assert mounts[1] == (source_ro.absolute(), target_ro, True)
        assert mounts[2] == (source_rw.absolute(), target_rw, False)

    def test_path_expansion(self):
        """Test that paths are properly expanded"""
        options = MountOptions(
            read_only=[(Path("~/data"), Path("/container/data"))],
            share_bfabric_config=False,
        )
        work_dir = Path("/work")

        mounts = options.collect(work_dir)

        assert len(mounts) == 2
        assert mounts[1][0] == Path("~/data").expanduser().absolute()
        assert mounts[1][1] == Path("/container/data")
        assert mounts[1][2] is True


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


class TestCommandExec:
    @pytest.fixture
    def command_minimal(self):
        return CommandExec(command="echo 'hello world'")

    @pytest.fixture
    def command_full(self):
        return CommandExec(
            command='bash -c \'echo "hello $NAME" && echo "$PATH"\'',
            env={"NAME": "sun"},
            prepend_paths=[Path("/usr/local/bin"), Path("~/bin")],
        )

    def test_minimal(self, command_minimal):
        assert command_minimal.to_shell() == ["echo", "hello world"]
        assert command_minimal.to_shell_env({}) == {}
        assert command_minimal.to_shell_env({"NAME": "world"}) == {"NAME": "world"}

    def test_full(self, mocker, command_full):
        mocker.patch.dict("os.environ", {"HOME": "/home/user"})
        assert command_full.to_shell() == ["bash", "-c", 'echo "hello $NAME" && echo "$PATH"']
        assert command_full.to_shell_env({}) == {
            "NAME": "sun",
            "PATH": "/usr/local/bin:/home/user/bin:",
        }
        assert command_full.to_shell_env({"NAME": "world"}) == {
            "NAME": "sun",
            "PATH": "/usr/local/bin:/home/user/bin:",
        }


class TestCommandDocker:
    def test_basic(self):
        """Test basic docker command generation"""
        cmd = CommandDocker(image="python:3.9", command="python script.py")

        result = cmd.to_shell(Path("/work"))

        expected = [
            "docker",
            "run",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--rm",
            "--mount",
            "type=bind,source=/home/user/.bfabricpy.yml,target=/home/user/.bfabricpy.yml,readonly",
            "--mount",
            "type=bind,source=/work,target=/work",
            "python:3.9",
            "python",
            "script.py",
        ]

        # Replace actual home directory path with /home/user for test stability
        result = [s.replace(str(Path.home()), "/home/user") for s in result]
        assert result == expected

    def test_with_options(self, tmp_path):
        """Test docker command generation with entrypoint, env vars, and custom args"""
        cmd = CommandDocker(
            image="ubuntu:latest",
            command="echo 'hello'",
            entrypoint="/bin/bash",
            env={"DEBUG": "1", "PATH": "/usr/local/bin"},
            mac_address="00:00:00:00:00:00",
            custom_args=["--network=host"],
            hostname="myhost",
            mounts=MountOptions(share_bfabric_config=False),  # Disable bfabric mount for simpler testing
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        result = cmd.to_shell(work_dir)

        expected = [
            "docker",
            "run",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--rm",
            "--mount",
            f"type=bind,source={work_dir.absolute()},target={work_dir.absolute()}",
            "--entrypoint",
            "/bin/bash",
            "--env",
            "DEBUG=1",
            "--env",
            "PATH=/usr/local/bin",
            "--mac-address",
            "00:00:00:00:00:00",
            "--network=host",
            "--hostname",
            "myhost",
            "ubuntu:latest",
            "echo",
            "hello",
        ]

        assert result == expected

    def test_with_complex_command(self):
        """Test docker command generation with a complex command containing spaces and quotes"""
        cmd = CommandDocker(
            image="alpine:latest",
            command="sh -c \"echo 'test with spaces' && ls -la\"",
            mounts=MountOptions(share_bfabric_config=False),
        )

        result = cmd.to_shell(Path("/work"))

        expected = [
            "docker",
            "run",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--rm",
            "--mount",
            "type=bind,source=/work,target=/work",
            "alpine:latest",
            "sh",
            "-c",
            "echo 'test with spaces' && ls -la",
        ]

        assert result == expected


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
