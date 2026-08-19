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

Paths are resolved relative to the directory containing the `app.yml` (see [Paths](../specs/app_specification.md#paths)), so the deployment directory can be moved or checked out elsewhere without rewriting the spec.

```yaml
bfabric:
  app_runner: 0.1.0
versions:
  - version:
      - 4.7.8.dev2
    commands:
      dispatch:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        local_extra_deps:
          - dist/${app.version}/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.dispatch
      process:
        type: python_env
        pylock: dist/${app.version}/pylock.toml
        local_extra_deps:
          - dist/${app.version}/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.process
        env:
          MZMINE_CONTAINER_TAG: "4.7.8.p1"
          MZMINE_DATA_PATH: /home/bfabric/mzmine
        prepend_paths:
          - bin
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

## Cluster resources and the submitter version

An app version's [`slurm_params`](creating_an_app.md#requesting-cluster-resources) are read by the *submitter*,
which is deployed and versioned separately from the app: the `bfabric.app_runner` pin in `app.yml` governs the
job, not the submitter. A submitter older than the field ignores it, so the app silently runs on the
deployment's default resources.

If a value seems to have no effect, check the submitter deployment's version first, then its log for a
`Could not read` or `does not exist` warning naming the app.yml. Note also that this submitter requires the
application executable's `<program>` to be the bare path of the `app.yml`; an application registered against
the compat wrapper is refused at submit time with an explicit error.

## Checklist

1. Build the wheel and export the lock file using the snippet above.
2. Copy the `dist/<version>/` directory to the server.
3. Update `app.yml` to reference the new version.
4. Validate with `bfabric-app-runner validate app-spec`.
