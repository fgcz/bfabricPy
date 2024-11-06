## Workunit Definition

The idea of the workunit definition is to provide a persistable and comprehensive description of a workunit.
To keep the logic even more modular it is separated into two components, the `execution` and the `registration`
information.

### Creating WorkunitDefinition instances

The `WorkunitDefinition` class is a Pydantic model and can be created by passing a dictionary to the constructor.
However, for convenience and easier integration into command line tools there is a constructor for both creating an
instance from a Bfabric entity, and parsing a YAML file which contains a persisted version of the workunit

### Workunit references

Several functions and command line tools allow providing a "workunit reference". This means, that either the ID or a
path to a local YAML file can be passed to this function.
If the input is a path, then the persisted information will be retrieved to instantiate a `WorkunitDefinition` instance,
whereas if it is an integer, the information will be obtained by querying the B-Fabric API.

Since in some workflows the workunit will be used several times, and in particular not necessarily in the same process,
the usual entity caching mechanism might not be able to cache the requests.
Therefore, in many cases passing a reference to a YAML file is the preferred way to provide the workunit information,
as it will reduce the number of requests to the B-Fabric API (sometimes even to zero).

### Reference

```{eval-rst}
.. automodule:: bfabric.experimental.workunit_definition
    :members:
    :undoc-members:
    :show-inheritance:
```
