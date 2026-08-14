import os
import subprocess

import pytest
from bfabric_app_runner.legacy.shim import (
    NOOP_COMMANDS,
    SHIMMED_COMMANDS,
    UPLOAD_COMMAND,
    UPLOAD_MANIFEST_ENV,
    materialize_shim_dir,
)


@pytest.fixture
def shim_dir(tmp_path):
    return materialize_shim_dir(tmp_path / "shims")


def _run(script, *args, env=None, cwd=None):
    return subprocess.run([str(script), *args], capture_output=True, text=True, env=env, cwd=cwd)


def test_writes_every_shimmed_command(shim_dir):
    assert sorted(p.name for p in shim_dir.iterdir()) == sorted(SHIMMED_COMMANDS)


@pytest.mark.parametrize("command", SHIMMED_COMMANDS)
def test_shim_is_executable(shim_dir, command):
    assert os.access(shim_dir / command, os.X_OK)


def test_materialize_is_idempotent(tmp_path):
    target = tmp_path / "shims"
    assert sorted(p.name for p in materialize_shim_dir(target).iterdir()) == sorted(
        p.name for p in materialize_shim_dir(target).iterdir()
    )


class TestNoopShims:
    @pytest.mark.parametrize(
        "args",
        [
            pytest.param([], id="no_args"),
            pytest.param(["12345"], id="single_id"),
            pytest.param(["0", "0", "0"], id="three_sentinels_as_RESSOURCEID_expands"),
            pytest.param(["not-an-integer"], id="non_integer"),
        ],
    )
    def test_succeeds_on_any_argv(self, shim_dir, args):
        result = _run(shim_dir / "bfabric_setResourceStatus_available.py", *args)
        assert result.returncode == 0
        assert "bfabric_setResourceStatus_available.py" in result.stderr

    def test_upload_is_not_a_noop(self):
        """It records files for registration rather than discarding them."""
        assert UPLOAD_COMMAND not in NOOP_COMMANDS


class TestUploadShim:
    @pytest.fixture
    def payload(self, tmp_path):
        payload = tmp_path / "scratch" / "proteinGroups.txt"
        payload.parent.mkdir()
        payload.write_text("gene\tintensity\n")
        return payload

    @pytest.fixture
    def manifest(self, tmp_path):
        return tmp_path / "chunk" / "legacy_uploads.txt"

    @pytest.fixture
    def env(self, manifest):
        manifest.parent.mkdir(parents=True, exist_ok=True)
        return {UPLOAD_MANIFEST_ENV: str(manifest)}

    def test_records_the_path(self, shim_dir, payload, manifest, env):
        # the workunit id is the real command's second argument and is irrelevant here
        result = _run(shim_dir / UPLOAD_COMMAND, str(payload), "349972", env=env)

        assert result.returncode == 0
        assert manifest.read_text().splitlines() == [str(payload)]

    def test_leaves_the_file_in_place(self, shim_dir, payload, env):
        """No legacy app removes its scratch, so there is no reason to copy possibly-huge output."""
        _ = _run(shim_dir / UPLOAD_COMMAND, str(payload), "349972", env=env)

        assert payload.is_file()

    def test_appends_across_calls(self, shim_dir, payload, manifest, env):
        other = payload.with_name("parameters.txt")
        other.write_text("params\n")

        _ = _run(shim_dir / UPLOAD_COMMAND, str(payload), "349972", env=env)
        _ = _run(shim_dir / UPLOAD_COMMAND, str(other), "349972", env=env)

        assert manifest.read_text().splitlines() == [str(payload), str(other)]

    def test_resolves_a_relative_path(self, shim_dir, payload, manifest, env):
        result = _run(shim_dir / UPLOAD_COMMAND, payload.name, "349972", env=env, cwd=payload.parent)

        assert result.returncode == 0
        assert manifest.read_text().splitlines() == [str(payload)]

    def test_tolerates_missing_file(self, shim_dir, tmp_path, manifest, env):
        """Callers append `|| { echo failed; }`, so a missing file must not abort the app."""
        result = _run(shim_dir / UPLOAD_COMMAND, str(tmp_path / "absent.txt"), "349972", env=env)

        assert result.returncode == 0
        assert "no such file" in result.stderr
        assert not manifest.exists()

    def test_without_manifest_it_is_a_noop(self, shim_dir, payload):
        result = _run(shim_dir / UPLOAD_COMMAND, str(payload), "349972", env={})

        assert result.returncode == 0
        assert "no upload manifest set" in result.stderr
