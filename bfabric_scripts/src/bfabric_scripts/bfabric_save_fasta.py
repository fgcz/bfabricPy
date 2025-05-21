#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path

from bfabric import Bfabric

FASTAHTTPROOT = "/fasta/"
BFABRICSTORAGEID = 2
BFABRIC_APPLICATION_ID = 61


def save_fasta(container_id: int, fasta_file: Path) -> None:
    """Save a fasta file to bfabric."""
    client = Bfabric.connect()

    print("Reading description from stdin")
    description = sys.stdin.read()

    if not fasta_file.exists():
        raise FileNotFoundError(fasta_file)

    with fasta_file.open("rb") as f:
        md5 = hashlib.md5(f.read()).hexdigest()

    resources = client.read(endpoint="resource", obj={"filechecksum": md5}).to_list_dict()
    if resources:
        print("resource(s) already exist.")
        # TODO this logic was mostly carried over from before, does it still make sense?
        try:
            resources = client.save(
                endpoint="resource",
                obj={"id": resources[0]["id"], "description": description},
            )
            print(json.dumps(resources.to_list_dict(), indent=2))
            return
        except Exception:
            pass

    workunit = client.save(
        endpoint="workunit",
        obj={
            "name": f"FASTA: {fasta_file.name}",
            "containerid": container_id,
            # TODO make configurable if needed in the future
            "applicationid": BFABRIC_APPLICATION_ID,
        },
    ).to_list_dict()
    print(json.dumps(workunit, indent=2))

    obj = {
        "workunitid": workunit[0]["id"],
        "filechecksum": md5,
        "relativepath": f"{FASTAHTTPROOT}{fasta_file.name}",
        "name": fasta_file.name,
        "size": fasta_file.stat().st_size,
        "status": "available",
        "description": description,
        "storageid": BFABRICSTORAGEID,
    }

    resource = client.save(endpoint="resource", obj=obj).to_list_dict()
    print(json.dumps(resource, indent=2))

    workunit = client.save(endpoint="workunit", obj={"id": workunit[0]["id"], "status": "available"}).to_list_dict()
    print(json.dumps(workunit, indent=2))


def main() -> None:
    """Parses command line arguments and calls `save_fasta`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("container_id", help="container_id", type=int)
    parser.add_argument("fasta_file", help="fasta_file", type=Path)
    args = parser.parse_args()
    save_fasta(container_id=args.container_id, fasta_file=args.fasta_file)


if __name__ == "__main__":
    main()
