from pathlib import Path

from bfabric_app_runner.commands.command_docker import _collect_mount_options
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
