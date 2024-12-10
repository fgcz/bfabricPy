import argparse
from pathlib import Path

from rich.pretty import pprint

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging


def save_resource_description(client: Bfabric, id: int, description_file: Path) -> None:
    description = description_file.read_text()
    obj = {"id": id, "description": description}
    response = client.save(endpoint="resource", obj=obj)
    pprint(response[0], indent_guides=False)


def main() -> None:
    setup_script_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("id", type=int)
    parser.add_argument("description_file", type=Path)
    client = Bfabric.from_config()
    args = parser.parse_args()
    save_resource_description(client=client, **vars(args))


if __name__ == "__main__":
    main()
