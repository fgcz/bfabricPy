import os
from pathlib import Path

import pytest

from bfabric_app_runner.commands.command_docker import _collect_mount_options, execute_command_docker, _to_shell
from bfabric_app_runner.specs.app.commands_spec import (
    CommandDocker,
    CommandExec,
)
from bfabric_app_runner.specs.app.commands_spec import (
    MountOptions,
)


class TestCollectMountOptions:
    def test_default_behavior(self, tmp_path):
        """Test collect method with default settings"""
        options = MountOptions()
        work_dir = tmp_path / "work"
        work_dir.mkdir()

        mounts = _collect_mount_options(options, work_dir)

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

        mounts = _collect_mount_options(options, work_dir)

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

        mounts = _collect_mount_options(options, work_dir)

        assert len(mounts) == 2
        assert mounts[1][0] == Path("~/data").expanduser().absolute()
        assert mounts[1][1] == Path("/container/data")
        assert mounts[1][2] is True


class TestExecuteCommandDocker:
    @pytest.fixture
    def execute_command_exec(self, mocker):
        return mocker.patch("bfabric_app_runner.commands.command_docker.execute_command_exec")

    def test_basic(self, execute_command_exec):
        """Test basic docker command generation"""
        cmd = CommandDocker(image="python:3.9", command="python script.py")

        result = _to_shell(cmd, Path("/work"))

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
        result = _to_shell(cmd, work_dir)

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

        result = _to_shell(cmd, Path("/work"))

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

    def test_execute(self, mocker, execute_command_exec):
        """Test execution of a docker command"""
        to_shell = mocker.patch("bfabric_app_runner.commands.command_docker._to_shell")
        to_shell.return_value = ["dummy", "command"]
        cmd = CommandDocker(image="alpine:latest", command="echo 'hello world'")
        execute_command_docker(cmd)
        execute_command_exec.assert_called_once_with(CommandExec(command="dummy command"))
