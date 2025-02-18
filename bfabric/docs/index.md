# Home

This package implements a Python interface to the [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/) system.
Several pieces of functionality are available:

- Python API:
    - General client for all B-Fabric web service operations (CRUD) and configuration management.
    - A relational API for low-boilerplate read access to the B-Fabric system.
- Scripts: Several scripts we use more or less frequently to interact with the system.
- A REST API: A REST API to interact with the B-Fabric system. This allows us to interact with B-Fabric from R
    using [bfabricShiny](https://github.com/cpanse/bfabricShiny).

Please see below for how to install bfabricPy.

## Installation

The [bfabric](https://pypi.org/project/bfabric/) and [bfabric-scripts](https://pypi.org/project/bfabric-scripts/)
packages are available on PyPI.
If you want to use the API in your code the `bfabric` package already provides all relevant functionality, whereas
`bfabric-scripts` will provide several command line tools to interact with the B-Fabric system.

### Installing the tool

If you are only interested in running the command line scripts, installation with `uv tool` is recommended as it will
create a separate virtual environment for bfabric-scripts and make it possible to upgrade your installation later
easily.

```bash
uv tool install -p 3.13 bfabric-scripts
```

You can upgrade this installation to the most recent version later with:

```bash
uv tool upgrade bfabric-scripts
```

### Declaring a package dependency

If you want to add it to a `pyproject.toml`, simply add bfabric to your dependencies:

```toml
[project]
dependencies = [
    "bfabric==x.y.z"
]
```

where you replace `x.y.z` with the version you want to use.

If you instead want to install a development version, you can specify the git repository and branch to use:

```toml
[project]
dependencies = [
    "bfabric @ git+https://github.com/fgcz/bfabricPy.git@stable&subdirectory=bfabric#egg=bfabric",
]
```

## Configuration

Create a file as follows: (note: the password is not your login password, but the web service password available on your
profile page)

```yaml
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric
```

You can also append an additional config section for the TEST instance which will be used for instance when running the
integration tests:

```yaml
TEST:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric
```

When you run an application using bfabricPy, and it does not explicitly set the config when calling
`Bfabric.from_config`, you can adjust the
environment that is used by setting the environemnt variable `BFABRICPY_CONFIG_ENV` to the name of the config section
you want to use.
Command line scripts will log the user and base URL that is used, so you can verify that you are indeed using the
correct environment.
