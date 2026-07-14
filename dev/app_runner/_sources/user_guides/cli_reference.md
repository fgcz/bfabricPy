# CLI Reference

Complete reference for the `bfabric-app-runner` command-line interface.

## Global Options

Every command that talks to B-Fabric also accepts these options (omitted from the per-command listings below):

| Option | Description |
| -------------- | ------------------------------------------------------------------------------------- |
| `--config-env` | Override the config environment; falls back to `BFABRICPY_CONFIG_ENV` or the file default |
| `--config-file`| Override the config file path (default `~/.bfabricpy.yml`) |

The `outputs` commands additionally accept `--reuse-default-resource` / `--no-reuse-default-resource`, which
controls whether the workunit's auto-created default resource is reused.

## run

### run workunit

Run a workunit end-to-end (dispatch, process all chunks, register outputs).

```bash
bfabric-app-runner run workunit <app_definition> <scratch_root> <workunit_ref>
```

| Argument | Description |
| ---------------- | ------------------------------------------- |
| `app_definition` | Path to the app.yml specification file |
| `scratch_root` | Root directory for scratch/work files |
| `workunit_ref` | Workunit reference (ID or URI) |

## prepare

### prepare workunit

Prepare a workunit for execution (resolve inputs, set up work directory).

```bash
bfabric-app-runner prepare workunit <app_spec> <work_dir> <workunit_ref> [options]
```

| Argument | Description |
| --------------- | ------------------------------------------- |
| `app_spec` | Path to the app.yml specification file |
| `work_dir` | Working directory for the workunit |
| `workunit_ref` | Workunit reference (ID or URI) |

| Option | Description |
| ----------------------- | ---------------------------------------------------------- |
| `--ssh-user` | SSH user for remote file access |
| `--force-storage` | Override the storage location |
| `--force-app-version` | Force a specific application version |
| `--read-only` | Prepare in read-only mode |
| `--use-external-runner` | Use an external runner for execution |

## action

Commands for running individual workflow phases. Each reads its configuration — the work directory, app
reference, and workunit reference — from the `app_env.yml` file that `prepare workunit` writes into the
working directory. Pass it with `--config`, or supply the parameters explicitly with `--work-dir`,
`--app-ref`, and `--workunit-ref`.

### action run-all

Run all stages of a dispatched app.

```bash
bfabric-app-runner action run-all --config app_env.yml
```

### action dispatch

Dispatch a workunit definition (create chunk directories).

```bash
bfabric-app-runner action dispatch --config app_env.yml
```

### action inputs

Prepare input files for a chunk.

```bash
bfabric-app-runner action inputs --config app_env.yml
```

### action process

Process a chunk.

```bash
bfabric-app-runner action process --config app_env.yml
```

### action outputs

Register output files for a chunk.

```bash
bfabric-app-runner action outputs --config app_env.yml
```

## inputs

Commands for managing input files.

### inputs prepare

Download and prepare input files into the target folder.

```bash
bfabric-app-runner inputs prepare <inputs_yaml> [target_folder] [options]
```

| Argument | Description |
| --------------- | ------------------------------------------------ |
| `inputs_yaml` | Path to the inputs YAML specification file |
| `target_folder` | Target directory (optional, defaults to cwd) |

| Option | Description |
| ------------ | ------------------------------------------------- |
| `--ssh-user` | SSH user for remote file access |
| `--filter` | Only prepare inputs matching this filename pattern |

### inputs list

List all defined inputs and their status.

```bash
bfabric-app-runner inputs list <inputs_yaml> [target_folder] [options]
```

| Argument | Description |
| --------------- | ------------------------------------------------ |
| `inputs_yaml` | Path to the inputs YAML specification file |
| `target_folder` | Target directory (optional, defaults to cwd) |

| Option | Description |
| --------- | --------------------------------------------- |
| `--check` | Also check whether each input exists on disk |

### inputs check

Verify that all expected input files are present.

```bash
bfabric-app-runner inputs check <inputs_yaml> [target_folder]
```

| Argument | Description |
| --------------- | ------------------------------------------------ |
| `inputs_yaml` | Path to the inputs YAML specification file |
| `target_folder` | Target directory (optional, defaults to cwd) |

### inputs clean

Remove prepared input files from the target folder.

```bash
bfabric-app-runner inputs clean <inputs_yaml> [target_folder] [options]
```

| Argument | Description |
| --------------- | ------------------------------------------------ |
| `inputs_yaml` | Path to the inputs YAML specification file |
| `target_folder` | Target directory (optional, defaults to cwd) |

| Option | Description |
| ---------- | ------------------------------------------------- |
| `--filter` | Only clean inputs matching this filename pattern |

## outputs

Commands for registering output files in B-Fabric.

### outputs register

Register all outputs defined in a YAML file.

```bash
bfabric-app-runner outputs register <outputs_yaml> <workunit_ref> [options]
```

| Argument | Description |
| --------------- | ------------------------------------------------- |
| `outputs_yaml` | Path to the outputs YAML specification file |
| `workunit_ref` | Workunit reference (ID or URI) |

| Option | Description |
| -------------------------- | ----------------------------------------------- |
| `--ssh-user` | SSH user for remote file transfers |
| `--force-storage` | Override the storage location |

### outputs register-single-file

Register a single output file without an outputs YAML.

```bash
bfabric-app-runner outputs register-single-file <local_path> [options]
```

| Argument | Description |
| ------------ | ----------------------------------- |
| `local_path` | Path to the local file to register |

| Option | Description |
| -------------------------- | ---------------------------------------------------------- |
| `--workunit-ref` (required)| Workunit reference (ID or URI) |
| `--store-entry-path` | Filename in B-Fabric storage |
| `--store-folder-path` | Directory path within storage |
| `--update-existing` | Update behavior: `no`, `if-exists`, or `required` (default `no`) |
| `--ssh-user` | SSH user for remote transfers |
| `--force-storage` | Override the storage location |

## validate

Commands for validating specification files.

### validate app-spec

Validate an app specification file.

```bash
bfabric-app-runner validate app-spec <app_yaml> [options]
```

| Argument | Description |
| ---------- | ----------------------------------- |
| `app_yaml` | Path to the app.yml file |

| Option | Description |
| ------------- | ------------------------------------------------ |
| `--app-id` | Application ID for template variable resolution |
| `--app-name` | Application name for template variable resolution |

### validate app-spec-template

Validate an app specification template (before variable resolution).

```bash
bfabric-app-runner validate app-spec-template <yaml_file>
```

| Argument | Description |
| ----------- | -------------------------------------- |
| `yaml_file` | Path to the app spec template file |

### validate inputs-spec

Validate an inputs specification file.

```bash
bfabric-app-runner validate inputs-spec <yaml_file>
```

| Argument | Description |
| ----------- | ---------------------------------------- |
| `yaml_file` | Path to the inputs YAML file |

### validate outputs-spec

Validate an outputs specification file.

```bash
bfabric-app-runner validate outputs-spec <yaml_file>
```

| Argument | Description |
| ----------- | ----------------------------------------- |
| `yaml_file` | Path to the outputs YAML file |
