from __future__ import annotations

from pathlib import Path

import pytest
from logot import Logot, logged
from pytest_mock import MockerFixture

from bfabric.wrapper_creator.slurm import SLURM


@pytest.fixture()
def mock_slurm() -> SLURM:
    return SLURM(slurm_root=Path("/tmp/test_slurm"))


@pytest.mark.parametrize("path", ["/tmp/hello/world.txt", Path("/tmp/hello/world.txt")])
def test_sbatch_when_success(mocker: MockerFixture, mock_slurm: SLURM, path: Path | str) -> None:
    mock_is_file = mocker.patch.object(Path, "is_file", return_value=True)
    mocker.patch("os.environ", new={"x": "y"})
    mock_run = mocker.patch("subprocess.run", return_value=mocker.MagicMock(stdout="stdout", stderr="stderr"))
    stdout, stderr = mock_slurm.sbatch(script=path)
    assert stdout == "stdout"
    assert stderr == "stderr"
    mock_run.assert_called_once_with(
        [Path("/tmp/test_slurm/bin/sbatch"), Path(path)],
        env={"SLURMROOT": Path("/tmp/test_slurm"), "x": "y"},
        check=True,
        shell=False,
        capture_output=True,
        encoding="utf-8",
    )
    assert mock_is_file.call_count == 2


def test_sbatch_when_script_not_exists(mocker: MockerFixture, mock_slurm: SLURM, logot: Logot) -> None:
    mocker.patch("bfabric.wrapper_creator.slurm.Path", side_effect=lambda x: x)
    mock_script = mocker.MagicMock(name="script", is_file=lambda: False)
    result = mock_slurm.sbatch(script=mock_script)
    assert result is None
    logot.assert_logged(logged.error(f"Script not found: {mock_script}"))


def test_sbatch_when_sbatch_not_exists(mocker: MockerFixture, mock_slurm: SLURM, logot: Logot) -> None:
    mocker.patch("bfabric.wrapper_creator.slurm.Path", side_effect=lambda x: x)
    mock_script = mocker.MagicMock(name="script", is_file=lambda: True)
    mock_sbatch = mocker.patch.object(mock_slurm, "_sbatch_bin", mocker.MagicMock(is_file=lambda: False))
    result = mock_slurm.sbatch(script=mock_script)
    assert result is None
    logot.assert_logged(logged.error(f"sbatch binary not found: {mock_sbatch}"))
