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
      - devel
    commands:
      dispatch:
        type: python_env
        pylock: /scratch/leo/code/mzmine_app/pylock.toml
        command: -m mzmine_app.integrations.bfabric.dispatch
        local_extra_deps:
          - /scratch/leo/code/mzmine_app/dist/mzmine_app-4.7.8.dev1-py3-none-any.whl
      process:
        type: python_env
        pylock: /scratch/leo/code/mzmine_app/pylock.toml
        command: -m mzmine_app.integrations.bfabric.process
        env:
          MZMINE_CONTAINER_TAG: "4.7.8.p1"
          MZMINE_DATA_PATH: /home/bfabric/mzmine
        local_extra_deps:
          - /scratch/leo/code/mzmine_app/dist/mzmine_app-4.7.8.dev1-py3-none-any.whl
        prepend_paths:
          - /scratch/leo/code/slurmworker/config/A375_MZMINE/bin
          - /home/bfabric/slurmworker/config/A375_MZMINE/bin
          - /home/bfabric/slurmworker/bin
```
