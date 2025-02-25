## App specification

### Commands

Each app defines the following core commands:

- dispatch
- process
- collect (optional)

These can be specified with:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandsSpec
```

#### Shell Commands

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandShell
```

#### Docker Commands

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandDocker

.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.MountOptions
```

### App Version Template file

TODO to be written

### Reference

TODO: not clear if this same document should also explain the individual steps, or if it would make sense to first
describe the app anatomy in a separate document with figures etc. and then list how to specify it

## Reference

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app_spec
    :members:
    :undoc-members:
    :show-inheritance:
```
