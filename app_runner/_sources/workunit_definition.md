## Workunit Definition

The idea of the workunit definition is to provide a persistable and comprehensive description of a workunit.
To keep the logic even more modular it is separated into two components, the `execution` and the `registration`
information.

### Creating WorkunitDefinition instances

The `WorkunitDefinition` class is a Pydantic model and can be created by passing a dictionary to the constructor.
However, for convenience and easier integration into command line tools there is a constructor for both creating an
instance from a Bfabric entity, and parsing a YAML file which contains a persisted version of the workunit

### Reference

```{eval-rst}
.. automodule:: bfabric.experimental.workunit_definition
    :members:
    :undoc-members:
    :show-inheritance:
```
