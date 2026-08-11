# bfabric-scripts

Command line tools for [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/), built on the
[bfabric](https://pypi.org/project/bfabric/) client.

## Installation

```bash
pip install bfabric-scripts
```

## Usage

Everything is reachable through the `bfabric-cli` entry point, which shares its configuration with the `bfabric`
client:

```bash
# Read the 10 most recent resources, showing selected columns
bfabric-cli api read resource --limit 10 --columns id,name,relativepath

# Filter by attribute, passed as key/value pairs
bfabric-cli api read resource createdby pfeeder createdafter 2024-05-01

# Export machine-readable output
bfabric-cli api read resource --limit 100 --format json --file results.json
```

The command groups are `api`, `auth`, `dataset`, `executable`, `external-job`, `feeder` and `workunit`; run
`bfabric-cli <group> --help` for the commands in each. A handful of legacy scripts (`bfabric_read.py` and friends)
remain available as separate entry points.

## Useful commands

### List not available analysis workunits

```bash
bfabric-cli workunit not-available
```

## Links

- [Documentation](https://fgcz.github.io/bfabricPy)
- [Changelog](https://github.com/fgcz/bfabricPy/blob/main/bfabric_scripts/docs/changelog.md)
- [Source and issue tracker](https://github.com/fgcz/bfabricPy)
