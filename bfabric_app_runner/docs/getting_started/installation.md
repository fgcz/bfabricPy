# Installation

## Prerequisites

- **Python**: 3.13 or higher
- **uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it
- **B-Fabric account**: You need valid B-Fabric credentials configured in `~/.bfabricpy.yml` (see the [bfabric Configuration Guide](https://fgcz.github.io/bfabricPy/getting_started/configuration.html))


## Installing as a CLI Tool (Recommended)

The easiest way to install bfabric-app-runner is as an isolated CLI tool using `uv tool`:

```bash
uv tool install bfabric-app-runner
```

To upgrade to the latest version:

```bash
uv tool upgrade bfabric-app-runner
```

### Running a Specific Version

You can run a specific version without installing it globally:

```bash
uv tool run bfabric-app-runner@0.2.1 --help
```

This is useful when an app's `app.yml` specifies a particular `app_runner` version.


## Development Installation

To install from the Git repository for development:

```bash
git clone https://github.com/fgcz/bfabricPy.git
cd bfabricPy
uv sync --package bfabric_app_runner
```


## Verifying Installation

Confirm that the tool is available:

```bash
bfabric-app-runner --help
```

This displays the top-level command groups:

- **run** -- Run a workunit end-to-end
- **prepare** -- Prepare a workunit working directory with a Makefile
- **action** -- Run individual workflow stages (dispatch, inputs, process, outputs, run-all)
- **inputs** -- Manage input files (prepare, clean, list, check)
- **outputs** -- Register output files
- **validate** -- Validate spec files (app-spec, inputs-spec, outputs-spec)


## Next Steps

1. **Configure B-Fabric credentials** if you haven't already: see the [bfabric Configuration Guide](https://fgcz.github.io/bfabricPy/getting_started/configuration.html)
2. **Try the workflow**: [Quick Start Tutorial](quick_start.md)
3. **Learn about app configuration**: [Configuration Guide](configuration.md)
