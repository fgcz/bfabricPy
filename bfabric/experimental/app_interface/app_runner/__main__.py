from __future__ import annotations

import argparse
from pathlib import Path
from typing import Union
from venv import logger

import yaml
from pydantic import TypeAdapter, BaseModel

from bfabric.bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.app_runner._spec import AppSpec
from bfabric.experimental.app_interface.app_runner.runner import Runner


class ChunksFile(BaseModel):
    # TODO move to better location
    chunks: list[Path]


def main() -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("action", default="run", choices=["run"])
    parser.add_argument("--app-spec", type=Path, required=True)
    parser.add_argument("--workunit-ref", type=TypeAdapter(Union[int, Path]).validate_strings, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--ssh-user", type=str, required=False)
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()

    app_spec = AppSpec.model_validate(yaml.safe_load(args.app_spec.read_text()))
    runner = Runner(spec=app_spec, client=client, ssh_user=args.ssh_user)
    runner.run_dispatch(workunit_ref=args.workunit_ref, work_dir=args.work_dir)
    chunks_file = ChunksFile.model_validate(yaml.safe_load((args.work_dir / "chunks.yml").read_text()))
    for chunk in chunks_file.chunks:
        logger.info(f"Processing chunk {chunk}")
        runner.run_prepare_input(chunk_dir=chunk)
        runner.run_process(chunk_dir=chunk)
        if not args.read_only:
            runner.run_register_outputs(chunk_dir=chunk, workunit_ref=args.workunit_ref)


if __name__ == "__main__":
    main()
