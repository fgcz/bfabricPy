# Deploying Apps

This guide covers how to build and deploy Python applications for use with bfabric-app-runner.

## Build Process

Use [uv](https://docs.astral.sh/uv/) to create reproducible builds. The process produces two artifacts:

- A **wheel** (`.whl`) file containing your application code (no dependencies).
- A **pylock.toml** file that reproducibly specifies all dependencies.

```bash
# Get the current package version
pkg_version=$(uv version --short)

# Build the wheel into a versioned directory
uv build -o "dist/$pkg_version"

# Lock and export dependencies
uv lock -U
uv export --no-emit-project --format pylock.toml > "dist/$pkg_version/pylock.toml"

# Clean up (uv build creates a .gitignore in the output dir)
rm -f "dist/$pkg_version/.gitignore"
```

:::{note}
The pylock file must be named `pylock.toml` (or follow the standard naming convention). This constraint may be relaxed in future versions.
:::

## Deploying to the Server

Copy both the wheel and the pylock file into a versioned directory on the deployment server. A common convention is to organize by version number:

```
/home/bfabric/slurmworker/config/MY_APP/dist/
  4.7.8.dev2/
    pylock.toml
    my_app-4.7.8.dev2-py3-none-any.whl
  4.7.8.dev3/
    pylock.toml
    my_app-4.7.8.dev3-py3-none-any.whl
```

These files can be managed with git-lfs in the slurmworker configuration repository.

## Referencing in app.yml

Once deployed, reference the wheel and pylock files in your `app.yml` using the `${app.version}` template variable. This avoids duplicating paths across multiple version entries.

```yaml
bfabric:
  app_runner: 0.1.0
versions:
  - version:
      - 4.7.8.dev2
    commands:
      dispatch:
        type: python_env
        pylock: /home/bfabric/slurmworker/config/A375_MZMINE/dist/${app.version}/pylock.toml
        local_extra_deps:
          - /home/bfabric/slurmworker/config/A375_MZMINE/dist/${app.version}/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.dispatch
      process:
        type: python_env
        pylock: /home/bfabric/slurmworker/config/A375_MZMINE/dist/${app.version}/pylock.toml
        local_extra_deps:
          - /home/bfabric/slurmworker/config/A375_MZMINE/dist/${app.version}/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.process
        env:
          MZMINE_CONTAINER_TAG: "4.7.8.p1"
          MZMINE_DATA_PATH: /home/bfabric/mzmine
        prepend_paths:
          - /home/bfabric/slurmworker/config/A375_MZMINE/bin
          - /home/bfabric/slurmworker/bin
```

## Validation

After creating or updating your `app.yml`, validate it:

```bash
bfabric-app-runner validate app-spec app.yml
```

You can also provide optional context for template variable resolution:

```bash
bfabric-app-runner validate app-spec app.yml --app-id 123 --app-name my_app
```

The slurmworker repository includes a noxfile that validates all app YAML files at once using `nox`.

## Checklist

1. Build the wheel and export the lock file using the snippet above.
2. Copy the `dist/<version>/` directory to the server.
3. Update `app.yml` to reference the new version.
4. Validate with `bfabric-app-runner validate app-spec`.
