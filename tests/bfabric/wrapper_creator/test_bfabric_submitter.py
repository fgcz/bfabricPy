from __future__ import annotations

import base64
import copy
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml
from pytest_mock import MockerFixture

from bfabric.wrapper_creator.bfabric_submitter import BfabricSubmitter

PROGRAM = "/home/bfabric/sgeworker/bin/fgcz_sge_demo.bash"


@pytest.fixture()
def config() -> dict[str, Any]:
    """A job configuration shaped like the one `BfabricWrapperCreator.create` registers."""
    return {
        "application": {
            "parameters": {"comment": "plain"},
            "protocol": "scp",
            "input": {},
            "output": ["bfabric@fgcz-storage.example.org:/srv/www/htdocs/p1000/bfabric/Proteomics/demo/200.zip"],
        },
        "job_configuration": {
            "executable": PROGRAM,
            "external_job_id": 300,
            "fastasequence": "",
            "output": {"protocol": "scp", "resource_id": 200},
            "stderr": {"protocol": "file", "resource_id": 201, "url": "/home/bfabric/log/workunitid-100.err"},
            "stdout": {"protocol": "file", "resource_id": 202, "url": "/home/bfabric/log/workunitid-100.out"},
            "workunit_id": 100,
        },
    }


@pytest.fixture()
def submitter(mocker: MockerFixture) -> BfabricSubmitter:
    """A submitter with the state `__init__` would have read from B-Fabric."""
    submitter = object.__new__(BfabricSubmitter)
    submitter.partition = "prx"
    submitter.nodelist = "fgcz-r-033"
    submitter.memory = "4G"
    submitter.application = mocker.MagicMock(executable={"program": PROGRAM})
    submitter._client = mocker.MagicMock()
    submitter._client.config.job_notification_emails = "admin@example.org"
    return submitter


def _configuration_block(script: str) -> str:
    """The part of the job script that writes the configuration file."""
    lines = script.splitlines()
    start = next(i for i, line in enumerate(lines) if "config_WU$WORKUNIT_ID.yaml <<" in line)
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "EOF")
    return "\n".join(lines[start : end + 1]) + "\n"


def _run_configuration_block(script: str, tmp_path: Path) -> str:
    """Runs only the configuration block with bash and returns the file it wrote."""
    subprocess.run(
        ["bash", "-c", _configuration_block(script)],
        check=True,
        env={"TEMPDIR": str(tmp_path), "WORKUNIT_ID": "100", "PATH": "/usr/bin:/bin"},
    )
    return (tmp_path / "config_WU100.yaml").read_text()


class TestComposeBashScriptConfiguration:
    def test_plain_configuration_is_written_unchanged(
        self, submitter: BfabricSubmitter, config: dict[str, Any], tmp_path: Path
    ) -> None:
        configuration = yaml.safe_dump(config)
        script = submitter.compose_bash_script(configuration=configuration)
        assert _run_configuration_block(script, tmp_path) == configuration

    @pytest.mark.parametrize(
        "value",
        [
            "ACGT$(touch $TEMPDIR/injected)",
            "ACGT`touch $TEMPDIR/injected`",
            "$TEMPDIR and ${WORKUNIT_ID} and \\$HOME",
            "line one\nEOF\ntouch $TEMPDIR/injected\n",
        ],
    )
    @pytest.mark.parametrize("field", ["parameter", "fastasequence"])
    def test_shell_syntax_in_user_text_is_not_evaluated(
        self, submitter: BfabricSubmitter, config: dict[str, Any], tmp_path: Path, field: str, value: str
    ) -> None:
        if field == "parameter":
            config["application"]["parameters"]["comment"] = value
        else:
            config["job_configuration"]["fastasequence"] = value
        configuration = yaml.safe_dump(config)

        script = submitter.compose_bash_script(configuration=configuration)

        assert _run_configuration_block(script, tmp_path) == configuration
        assert not (tmp_path / "injected").exists()

    def test_raw_configuration_does_not_appear_in_script(
        self, submitter: BfabricSubmitter, config: dict[str, Any]
    ) -> None:
        config["application"]["parameters"]["comment"] = "MARKER$(id)"
        script = submitter.compose_bash_script(configuration=yaml.safe_dump(config))
        assert "MARKER" not in script

    def test_configuration_that_is_one_bare_eof_line_cannot_end_the_block(
        self, submitter: BfabricSubmitter, config: dict[str, Any], tmp_path: Path
    ) -> None:
        # Not valid output of yaml.safe_dump, but the configuration parser is pluggable.
        configuration = "EOF\ntouch $TEMPDIR/injected\n"
        script = submitter.compose_bash_script(configuration=configuration, configuration_parser=lambda _: config)
        assert _run_configuration_block(script, tmp_path) == configuration
        assert not (tmp_path / "injected").exists()


class TestComposeBashScriptValues:
    def test_script_is_valid_bash(self, submitter: BfabricSubmitter, config: dict[str, Any]) -> None:
        script = submitter.compose_bash_script(configuration=yaml.safe_dump(config))
        subprocess.run(["bash", "-n"], input=script, text=True, check=True)

    def test_valid_values_are_rendered(self, submitter: BfabricSubmitter, config: dict[str, Any]) -> None:
        submitter.nodelist = "fgcz-r-[033-035],fgcz-c-041"
        script = submitter.compose_bash_script(configuration=yaml.safe_dump(config))
        assert "#SBATCH --partition=prx\n" in script
        assert "#SBATCH --nodelist=fgcz-r-[033-035],fgcz-c-041\n" in script
        assert "#SBATCH --mem-per-cpu=4G\n" in script
        assert "#SBATCH -e /home/bfabric/log/workunitid-100.err\n" in script
        assert "#SBATCH -o /home/bfabric/log/workunitid-100.out\n" in script
        assert "#SBATCH --job-name=WU100\n" in script
        assert "export EXTERNALJOB_ID=300\n" in script
        assert "export RESSOURCEID_OUTPUT=200\n" in script
        assert 'export RESSOURCEID_STDOUT_STDERR="201 202"\n' in script
        assert f'export OUTPUT="{config["application"]["output"][0]}"\n' in script
        assert f"&& {PROGRAM} $TEMPDIR/config_WU$WORKUNIT_ID.yaml\n" in script

    @pytest.mark.parametrize("attribute", ["partition", "nodelist", "memory"])
    @pytest.mark.parametrize("value", ["prx\ntouch /tmp/injected", "prx --wrap=id", "prx;id", "$(id)", ""])
    def test_unsafe_slurm_value_is_refused(
        self, submitter: BfabricSubmitter, config: dict[str, Any], attribute: str, value: str
    ) -> None:
        setattr(submitter, attribute, value)
        with pytest.raises(ValueError, match=attribute):
            submitter.compose_bash_script(configuration=yaml.safe_dump(config))

    @pytest.mark.parametrize(
        ("path", "value"),
        [
            (("job_configuration", "stderr", "url"), "/log/a.err\n#SBATCH --wrap=id"),
            (("job_configuration", "stdout", "url"), "/log/a.out --export=ALL"),
            (("job_configuration", "stdout", "url"), "-o/log/a.out"),
            (("job_configuration", "external_job_id"), "300; id"),
            (("job_configuration", "workunit_id"), "100\nid"),
            (("job_configuration", "output", "resource_id"), "$(id)"),
            (("job_configuration", "stderr", "resource_id"), "201 && id"),
            (("job_configuration", "stdout", "resource_id"), True),
            (("application", "output"), ["bfabric@host.example.org:/srv/out/1.zip; id"]),
            (("application", "output"), ['bfabric@host.example.org:/srv/out/1.zip" && id && "']),
            (("application", "output"), ["bfabric@host.example.org:/srv/$(id)/1.zip"]),
            (("application", "output"), ["-oProxyCommand=/tmp/x:/srv/out/1.zip"]),
            (("application", "output"), ["bfabric@host.example.org:relative/1.zip"]),
            (("application", "output"), []),
        ],
    )
    def test_unsafe_configuration_value_is_refused(
        self, submitter: BfabricSubmitter, config: dict[str, Any], path: tuple[str, ...], value: object
    ) -> None:
        config = copy.deepcopy(config)
        target = config
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(ValueError, match="Refusing to submit"):
            submitter.compose_bash_script(configuration=yaml.safe_dump(config))

    def test_executable_other_than_the_application_program_is_refused(
        self, submitter: BfabricSubmitter, config: dict[str, Any]
    ) -> None:
        config["job_configuration"]["executable"] = "/bin/bash -c id #"
        with pytest.raises(ValueError, match="executable"):
            submitter.compose_bash_script(configuration=yaml.safe_dump(config))


class TestSubmitterYaml:
    def test_refused_configuration_is_not_written_or_submitted(
        self, mocker: MockerFixture, submitter: BfabricSubmitter, config: dict[str, Any], tmp_path: Path
    ) -> None:
        config["application"]["output"] = ["host.example.org:/srv/out/1.zip; id"]
        encoded = base64.b64encode(yaml.safe_dump(config).encode()).decode()
        mocker.patch(
            "bfabric.wrapper_creator.bfabric_submitter.Executable.find_by", return_value={1: {"base64": encoded}}
        )
        submit_slurm = mocker.patch.object(BfabricSubmitter, "submit_slurm")
        submitter.workunit = mocker.MagicMock(id=100)
        submitter.external_job = mocker.MagicMock(id=300)
        submitter.scheduler = "Slurm"
        submitter._script_dir = tmp_path
        submitter._executable_file_list = []

        with pytest.raises(ValueError, match="Refusing to submit"):
            submitter.submitter_yaml()

        submit_slurm.assert_not_called()
        assert list(tmp_path.iterdir()) == []
        submitter._client.save.assert_not_called()
