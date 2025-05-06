## Motivation

Using Python packages to define an individual app could allow to make apps more reusable in the future,
by using existing Python package management tools and infrastructures.

Of course, it will still be limited by integration with the environment. To achieve true portability, this issue will
have to be addressed e.g., by partially standardizing the way non-Python dependencies are handled.

## Locking

A Python package in general will not specify all its transitive dependency versions precisely.
However, deployments should be immutable.

To ensure this is possible functionality is provided in `bfabric-app-runner-uv`.

### TODO how it is implemented in practice

- `uv lock` is used to provide a `uv.lock` file. One could standardize to PEP 751 in the future, if alternative tools
    become available, but in `bfabric-app-runner-uv` I think it's acceptable to use uv's custom format for the time being.
