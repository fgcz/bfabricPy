# bfabric-app-runner Documentation

bfabric-app-runner provides a framework for developing and running applications that integrate with the [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/) system. It handles workunit processing, input/output staging, and app execution lifecycle.

## Installation

To install the most recent released version:

```bash
uv tool install bfabric_app_runner
```

To install a development version:

```bash
uv tool install bfabric_app_runner@git+https://github.com/fgcz/bfabricPy.git@main#egg=bfabric_app_runner&subdirectory=bfabric_app_runner
```

## Documentation Map

- **[Getting Started](getting_started/index)** -- Install, configure, and run your first workunit
- **[User Guides](user_guides/index)** -- Creating apps, working with inputs/outputs, deploying, and the CLI reference
- **[Architecture](architecture/overview)** -- How the runner orchestrates the dispatch → inputs → process → outputs lifecycle
- **[Input](specs/input_specification) / [Output](specs/output_specification) / [App](specs/app_specification) specifications** -- Field-level reference for the YAML spec files
- **[API Reference](api_reference/index)** -- Orientation hub linking the spec references and the Python runner API
- **[Workunit Definition](workunit_definition.md)** -- The persisted workunit definition format
- **[Resources](resources/index)** -- Links, contributing, and the changelog

## Table of Contents

```{toctree}
:maxdepth: 2
getting_started/index
user_guides/index
architecture/overview
specs/input_specification
specs/output_specification
specs/app_specification
api_reference/index
resources/index
workunit_definition
changelog
```
