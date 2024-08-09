# Home

This package connects the [bfabric](https://fgcz-bfabric.uzh.ch/bfabric/) system to the [python](https://www.python.org/) and [R](https://cran.r-project.org/) world while providing a JSON and REST interface using [Flask](https://www.fullstackpython.com).
The [bfabricShiny](https://github.com/cpanse/bfabricShiny) R package is an extension and provides code snippets and sample implementation for a seamless R shiny bfabric integration.
For more advanced users the *bfabricPy* package also provides a powerful query interface on the command-line though using the provided scripts.

## Installation

The package can be installed like any other Python package, so if you are familiar you might not need to read this section.
Currently, it's only available from GitHub.

The best way to install the package depends on your use case, i.e. whether you want to:

1. Use the command line scripts
2. Use the Python API
3. Develop on the package

The command line scripts are currently included in all cases.

### Command line scripts

To use the command line scripts, it's recommended to install `bfabricPy` with [pipx](https://pipx.pypa.io/).
If you don't have `pipx` installed, refer to the [pipx documentation](https://pipx.pypa.io/stable/installation/) for instructions.

You can execute a command using a specific version of `bfabricPy` with the `pipx run` command.
This command handles the dependencies of multiple concurrent installations:

```bash
pipx run --spec "git+https://github.com/fgcz/bfabricPy.git@stable" bfabric_read.py --help
```

To install a specific version of bfabricPy on your system and make the command available without `pipx run` prefix, use the following command:

```bash
pipx install "git+https://github.com/fgcz/bfabricPy.git@stable"
bfabric_read.py --help
```

### Python API

If you're interested in using the Python API of `bfabricPy`, you have two options:

#### 1. Configure it in your `pyproject.toml` file.

```toml
[project]
dependencies = [
    "bfabricPy @ git+https://github.com/fgcz/bfabricPy.git@stable"
]
```

#### 2. Install the `bfabricPy` package directly using pip.

```bash
pip install git+https://github.com/fgcz/bfabricPy.git
```

### Development

As a bfabricPy developer: (i.e. an editable install)

```{bash}
pip install -e ".[dev]"
```

## Configuration

Create a file as follows: (note: the password is not your login password, but the web service password)

```{yaml}
# ~/.bfabricpy.yml

GENERAL:
  default_config: PRODUCTION

PRODUCTION:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric.uzh.ch/bfabric
```

You can also include an additional config for the TEST instance

```{yaml}
TEST:
  login: yourBfabricLogin
  password: yourBfabricWebPassword
  base_url: https://fgcz-bfabric-test.uzh.ch/bfabric
```
