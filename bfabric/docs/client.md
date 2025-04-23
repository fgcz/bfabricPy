# Creating a Client

The `Bfabric` class, commonly referred to as the client, provides the main interface in the package to interact
with the B-Fabric system.

In general `Bfabric.connect()` provides a convenient way to create a client instance.
For B-Fabric web apps, there is `Bfabric.connect_webapp()` which parses the webapp token flow.

## Configuration Hierarchy

- If the `BFABRIC_CONFIG_DATA` environment variable is set, it will be used.
- Optionally: Config file (can be disabled with `config_file_env=None`).
    - Explicitly, in Python, specified environment name (e.g. `PRODUCTION`).
    - Explicitly, in environment variable `BFABRICPY_CONFIG_ENV`, specified environment name (e.g. `PRODUCTION`).
    - Default environment according to the config section

## `Bfabric.connect()`

The most basic way to create a client is to use the `Bfabric.connect()` method:

```python
from bfabric import Bfabric

client = Bfabric.connect()
```

If you set `BFABRIC_CONFIG_DATA` it will be respected.
By default, the value of `config_file_env` is set to `"default"`, which means that if no `BFABRIC_CONFIG_DATA` is set,
then `BFABRICPY_CONFIG_ENV` or the default from the `~/.bfabricpy.yml` file will be used.

If you do not want to have this fallback, you should set this option to `None` which is recommended e.g. for tests.

```python
from bfabric import Bfabric

client = Bfabric.connect(config_file_env=None)
```

Of course, you can also specify a name of an environment.
This will take precedence over the `BFABRICPY_CONFIG_ENV` environment variable.
However, if `BFABRIC_CONFIG_DATA` is set, that will be used instead.

```python
from bfabric import Bfabric

client = Bfabric.connect(config_file_env="PRODUCTION")
```

## `Bfabric.connect_webapp()`

Please check the docstring of the method.
In general, you have to pass the `token` received from the webapp request and this factory method
will create a tuple of a `Bfabric` client and `TokenData` which you can process further to e.g. identify the
entity on which the app was launched in B-Fabric.
