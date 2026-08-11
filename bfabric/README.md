# bfabric

Python client for [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/), the data management platform of the Functional
Genomics Center Zurich (FGCZ).

- A general client for all B-Fabric web service operations (CRUD) and configuration management.
- A relational API for low-boilerplate read access to B-Fabric entities.

## Installation

```bash
pip install bfabric
```

Two extras are available: `bfabric[zeep]` swaps the default suds SOAP engine for zeep, and `bfabric[transfer]` adds
resource download and upload.

## Usage

Credentials are read from `~/.bfabricpy.yml`:

```python
from bfabric import Bfabric

client = Bfabric.connect()
results = client.read(endpoint="workunit", obj={}, max_results=5)

for workunit in results:
    print(workunit["id"], workunit.get("status"))
```

See the [getting started guide](https://fgcz.github.io/bfabricPy) for configuring the client, and the user guides for
the relational entity API, caching and error handling.

## Links

- [Documentation](https://fgcz.github.io/bfabricPy)
- [Changelog](https://github.com/fgcz/bfabricPy/blob/main/bfabric/docs/changelog.md)
- [Source and issue tracker](https://github.com/fgcz/bfabricPy)

This package is part of the bfabricPy monorepo, which also publishes
[bfabric-scripts](https://pypi.org/project/bfabric-scripts/) (command line tools) and
[bfabric-app-runner](https://pypi.org/project/bfabric-app-runner/) (application workflows).

## How to cite

Panse, Christian, Trachsel, Christian and Türker, Can. "Bridging data management platforms and visualization tools to
enable ad-hoc and smart analytics in life sciences" Journal of Integrative Bioinformatics, 2022, pp. 20220031.
[doi: 10.1515/jib-2022-0031](https://doi.org/10.1515/jib-2022-0031).
