# Output specification

The outputs module provides a specification schema to define the outputs that were created by an app and should be registered.
The file is usually called `outputs.yml` and lists the different output files, with information how to register them.

## General structure

Generally the structure is a yaml file containing a key `outputs` which is a list of dictionaries, each representing an
output file.
Each output has a `type` key which identifies the output type.
This will allow us to extend this logic to different sources in the future.

An example file could look like:

```yaml
outputs:
- type: bfabric_copy_resource
  local_path: /tmp/work/hello.txt
  store_entry_path: WU123456_hello.txt
- type: bfabric_dataset
  local_path: /tmp/work/hello.csv
  separator: ","
  name: Hello Dataset
- type: bfabric_link
  name: Results Report
  url: https://example.com/report/123
```

## Commands

### Validation

The output file can be validated with the command:

```bash
bfabric-app-runner validate outputs-spec outputs.yml
```

Which on success will output a pretty-printed version of the outputs file.
Validation will also be performed by all other commands, so this is not strictly necessary.

### Register files

To perform the registration to B-Fabric the following can be used:

```bash
bfabric-app-runner outputs register outputs.yml 1234
```

Please note:

- The workunit reference (an integer workunit ID or a path to a workunit definition YAML file) must
  be specified, so the correct information can be retrieved.
- Several actions might require a particular user to be possible, e.g. the `bfabric_copy_resource` will require a user
    with permission to create the particular file over SSH.

## Reference

Each entry's `type` field selects one of the models below.

Copy a local file into B-Fabric storage as a resource:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.CopyResourceSpec
```

Register a local table as a B-Fabric dataset. The `format` field selects the reader — `csv` (the
default, a delimited text file) or `parquet`; `separator` and `has_header` apply to `csv` only:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.SaveDatasetSpec
```

Attach a link to the workunit (or another entity):

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.SaveLinkSpec
```

The `update_existing` field on each output uses the shared `UpdateExisting` enum, which controls
what happens when an output with the same name already exists:

```{eval-rst}
.. autoclass:: bfabric_app_runner.specs.outputs_spec.UpdateExisting
    :members:
    :undoc-members:
```
