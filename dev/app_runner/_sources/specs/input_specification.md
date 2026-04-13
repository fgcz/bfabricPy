## Input specification

The inputs module provides a specification schema to define the inputs required by an app.
You can also use this functionality interactively while prototyping.
The file is usually called `inputs.yml` and lists the different inputs, with information and how to retrieve them and
the filename to save them as.

### General structure

Generally the structure is a yaml file containing a key `inputs` which is a list of dictionaries, each representing an
input file.
Each input has a `type` key which identifies the input type.
This will allow us to extend this logic to different sources in the future.

In general the only other input key that will be available for all types is `filename`, which is the name of the file to
save the input as.
Fields like `id` might not be relevant for all types in the future, and depending on the type more specific options
might exist.

An example file could look like this:

```yaml
# file: inputs.yml
inputs:
  - type: bfabric_dataset
    id: 53706
    filename: test.csv
  - type: bfabric_resource
    id: 2700958
    filename: test.zip
```

## Commands

### Validation

The input file can be validated with the command:

```bash
bfabric-app-runner validate inputs-spec inputs.yml
```

Which on success will output a pretty-printed version of the inputs file.
Validation will also be performed by all other commands, so this is not strictly necessary.

For instance, in the above case this would print:

```
InputsSpec(
│   inputs=[
│   │   DatasetSpec(type='bfabric_dataset', id=53706, filename='test.csv', separator=','),
│   │   ResourceSpec(type='bfabric_resource', id=2700958, filename='test.zip', check_checksum=True)
│   ]
)
```

Here you can also see all the extra parameters which were implicitly set.

### Prepare files

The prepare command downloads your files and requires two arguments.
The first is the input file, and the second is the directory to save the files to.
In general to download to the current directory simply use `.` as the second argument:

```bash
bfabric-app-runner inputs prepare inputs.yml .
```

If your files already exist and are up-to-date, it will not download them again.

### List files

You can list the files that are present or will be downloaded:

```bash
bfabric-app-runner inputs list inputs.yml .
```

If you also want to check whether the files are up-to-date, you can pass the `--check` flag:

```bash
bfabric-app-runner inputs list --check inputs.yml .
```

## Reference

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.inputs_spec
    :members:
    :undoc-members:
    :show-inheritance:
```
