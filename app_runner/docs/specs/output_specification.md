## Output specification

The outputs module provides a specification schema to define the outputs that were created by an app and should be registered.
The file is usually called `outputs.yml` and lists the different output files, with information how to register them.

### General structure

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
bfabric-app-runner outputs register outputs.yml --workunit-id 1234
```

Please note:

- The workunit ID needs to be specified, so the correct information can be retrieved. (TODO but instead of the workunit id it should also be possible to pass the ref)
- Several actions might require a particular user to be possible, e.g. the `bfabric_copy_resource` will require a user
    with permission to create the particular file over SSH.

## Reference

```{eval-rst}
.. automodule:: app_runner.specs.outputs_spec
    :members:
    :undoc-members:
    :show-inheritance:
```
