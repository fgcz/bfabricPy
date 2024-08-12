# Home

This package connects the [bfabric](https://fgcz-bfabric.uzh.ch/bfabric/) system to the [python](https://www.python.org/) and [R](https://cran.r-project.org/) world while providing a JSON and REST interface using [Flask](https://www.fullstackpython.com).
The [bfabricShiny](https://github.com/cpanse/bfabricShiny) R package is an extension and provides code snippets and sample implementation for a seamless R shiny bfabric integration.
For more advanced users the *bfabricPy* package also provides a powerful query interface on the command-line though using the provided scripts.

Please see below for how to install bfabricPy.

## Installation

The package is not available on PyPI as of now, but can be installed directly from GitHub and a `stable` branch is available for your convenience.

If you are only interested in running the command line scripts, installation with `pipx` is recommended as it will create a separate virtual environment for bfabricPy and make it possible to upgrade your installation later easily.

```bash
pipx install "git+https://github.com/fgcz/bfabricPy.git@stable"
```

Note that `pipx` is also useful in scripts, if you want to run a particular version without forcing the global installation of that version (simply replace "stable" with a tag of your chosing):

```bash
pipx run --spec "git+https://github.com/fgcz/bfabricPy.git@stable" bfabric_read.py --help
```

If you want to add it to a `pyproject.toml` the syntax for specifying a git dependency is as follows:

```toml
[project]
dependencies = [
    "bfabric @ git+https://github.com/fgcz/bfabricPy.git@stable"
]
```

## Configuration

Create a file as follows: (note: the password is not your login password, but the web service password available on your profile page)

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
