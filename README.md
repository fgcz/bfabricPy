# bfabricPy

[![PR Checks](https://github.com/fgcz/bfabricPy/actions/workflows/run_unit_tests.yml/badge.svg)](https://github.com/fgcz/bfabricPy/actions/workflows/run_unit_tests.yml)
[![Nightly Integration Tests](https://github.com/fgcz/bfabricPy-tests/actions/workflows/nightly_tests.yml/badge.svg)](https://github.com/fgcz/bfabricPy-tests/actions/workflows/nightly_tests.yml)
[![EDBT'10](https://img.shields.io/badge/EDBT-10.1145%2F1739041.1739135-brightgreen)](https://doi.org/10.1145/1739041.1739135)
[![JIB](https://img.shields.io/badge/JIB-10.1515%2Fjib.2022.0031-brightgreen)](https://doi.org/10.1515/jib-2022-0031)

## Documentation

| Package            | Link                                                                 | Change Log                                                                                                               |
| ------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| bfabric            | [https://fgcz.github.io/bfabricPy](https://fgcz.github.io/bfabricPy) | [bfabric/docs/changelog.md](https://github.com/fgcz/bfabricPy/blob/main/bfabric/docs/changelog.md)                       |
| bfabric-scripts    | [https://fgcz.github.io/bfabricPy](https://fgcz.github.io/bfabricPy) | [bfabric_scripts/docs/changelog.md](https://github.com/fgcz/bfabricPy/blob/main/bfabric_scripts/docs/changelog.md)       |
| bfabric-app-runner | https://fgcz.github.io/bfabricPy/app_runner/                         | [bfabric_app_runner/docs/changelog.md](https://github.com/fgcz/bfabricPy/blob/main/bfabric_app_runner/docs/changelog.md) |

## Introduction

This package implements a Python interface to the [B-Fabric](https://fgcz-bfabric.uzh.ch/bfabric/) system.
Several pieces of functionality are available:

- Python API:
    - General client for all B-Fabric web service operations (CRUD) and configuration management.
    - A relational API for low-boilerplate read access to the B-Fabric system.
- Scripts: Several scripts we use more or less frequently to interact with the system.
- A REST API: A REST API to interact with the B-Fabric system. This allows us to interact with B-Fabric from R
    using [bfabricShiny](https://github.com/cpanse/bfabricShiny).

## Howto cite?

Panse, Christian, Trachsel, Christian and Türker, Can. "Bridging data management platforms and visualization tools to enable ad-hoc and smart analytics in life sciences" Journal of Integrative Bioinformatics, 2022, pp. 20220031. [doi: 10.1515/jib-2022-0031](https://doi.org/10.1515/jib-2022-0031).
