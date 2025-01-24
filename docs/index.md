# Home

This package implements a Python interface to the [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/) system.
Several pieces of functionality are available:

- Python API:
    - General client for all B-Fabric web service operations (CRUD) and configuration management.
    - A relational API for low-boilerplate read access to the B-Fabric system.
- Scripts: Several scripts we use more or less frequently to interact with the system.
- A REST API: A REST API to interact with the B-Fabric system. This allows us to interact with B-Fabric from R using [bfabricShiny](https://github.com/cpanse/bfabricShiny).

Please see below for how to install bfabricPy.

## Installation

The package is not available on PyPI as of now, but can be installed directly from GitHub and a `stable` branch is available for your convenience.

If you are only interested in running the command line scripts, installation with `uv tool` is recommended as it will create a separate virtual environment for bfabricPy and make it possible to upgrade your installation later easily.

```bash
uv tool install -p 3.13 "git+https://github.com/fgcz/bfabricPy.git@stable"
```

If you want to add it to a `pyproject.toml` the syntax for specifying a git dependency is as follows:

```toml
[project]
dependencies = [
    "bfabric @ git+https://github.com/fgcz/bfabricPy.git@stable"
]
```

## Updating

If you installed with `uv`, you can update the package to the most recent release with the following command:

```bash
uv tool upgrade bfabric
```

## Configuration

Create a file as follows: (note: the password is not your login password, but the web service password available on your profile page)

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric
```

You can also append an additional config section for the TEST instance which will be used for instance when running the integration tests:

```yaml
TEST:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric
```

When you run an application using bfabricPy, and it does not explicitly set the config when calling `Bfabric.from_config`, you can adjust the
environment that is used by setting the environemnt variable `BFABRICPY_CONFIG_ENV` to the name of the config section you want to use.
Command line scripts will log the user and base URL that is used, so you can verify that you are indeed using the correct environment.
