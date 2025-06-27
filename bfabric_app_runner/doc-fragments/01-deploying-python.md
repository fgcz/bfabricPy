## Deploying python apps

To deploy a python app using uv:

```bash
uv lock -U
uv export --no-emit-project --format pylock > pylock.toml
uv build
```

- This creates a .whl file and a pylock.toml file.
- For a reproducible environment you can now specify these two files.
- The .whl file will contain your code and no dependencies.
- The pylock.toml file will reproducibly specify the dependencies.

These files should be copied into a versioned directory in the server/repo.

This information can now be referenced in the YAML for instance this is an example (but you will have to change paths and variables for your use case):

```yaml
bfabric:
  app_runner: 0.1.0
versions:
  - version:
      - 4.7.8.dev2
    commands:
      dispatch:
        type: python_env
        pylock: /home/bfabric/slurmworker/config/A375_MZMINE/dist/mzmine_app-${app.version}-pylock.toml
        local_extra_deps:
          - /home/bfabric/slurmworker/config/A375_MZMINE/dist/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.dispatch
      process:
        type: exec
        pylock: /home/bfabric/slurmworker/config/A375_MZMINE/dist/mzmine_app-${app.version}-pylock.toml
        local_extra_deps:
          - /home/bfabric/slurmworker/config/A375_MZMINE/dist/mzmine_app-${app.version}-py3-none-any.whl
        command: -m mzmine_app.integrations.bfabric.process
        env:
          MZMINE_CONTAINER_TAG: "4.7.8.p1"
          MZMINE_DATA_PATH: /home/bfabric/mzmine
        prepend_paths:
          - /home/bfabric/slurmworker/config/A375_MZMINE/bin
          - /home/bfabric/slurmworker/bin
```
