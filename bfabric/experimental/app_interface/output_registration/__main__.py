import argparse
from pathlib import Path

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging
from bfabric.experimental.app_interface.output_registration import register_outputs


def main() -> None:
    setup_script_logging()
    client = Bfabric.from_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("action", default="register", choices=["register"])
    parser.add_argument("--outputs-yaml", type=Path, required=True)
    parser.add_argument("--workunit-id", type=int, required=True)
    parser.add_argument("--ssh-user", type=str, required=False)
    args = parser.parse_args()
    register_outputs(
        outputs_yaml=args.outputs_yaml,
        workunit_id=args.workunit_id,
        client=client,
        ssh_user=args.ssh_user,
    )
