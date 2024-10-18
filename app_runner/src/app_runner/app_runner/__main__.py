from __future__ import annotations

import argparse
from pathlib import Path
from typing import Union

import yaml
from pydantic import TypeAdapter

from bfabric.bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from app_runner.app_runner._spec import AppSpec
from app_runner.app_runner.runner import run_app


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
    run_app(
        app_spec=app_spec,
        workunit_ref=args.workunit_ref,
        work_dir=args.work_dir,
        client=client,
        ssh_user=args.ssh_user,
        read_only=args.read_only,
    )


if __name__ == "__main__":
    main()
