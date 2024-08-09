# Home

This package connects the [bfabric](https://fgcz-bfabric.uzh.ch/bfabric/) system to the [python](https://www.python.org/) and [R](https://cran.r-project.org/) world while providing a JSON and REST interface using [Flask](https://www.fullstackpython.com).
The [bfabricShiny](https://github.com/cpanse/bfabricShiny) R package is an extension and provides code snippets and sample implementation for a seamless R shiny bfabric integration.
For more advanced users the *bfabricPy* package also provides a powerful query interface on the command-line though using the provided scripts.

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
