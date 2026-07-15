# Input specification

The inputs module provides a specification schema to define the inputs required by an app.
You can also use this functionality interactively while prototyping.
The file is usually called `inputs.yml` and lists the different inputs, with information and how to retrieve them and
the filename to save them as.

## General structure

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

## HTTP transport (optional)

By default a `bfabric_resource` is copied from its storage host over SSH (rsync/scp), which needs
SSH/NFS access to that host. You can instead fetch it over HTTP with `access: http`:

```yaml
inputs:
  - type: bfabric_resource
    id: 2700958
    filename: test.zip
    access: http        # default is "ssh"
```

HTTP is portable (works anywhere with web access, no SSH keys) but slower, so it is an add-on rather
than a replacement. It requires an **OAuth-backed client whose token carries the `containers` scope**
(the default `bfabric-cli` scope does not) — with an ordinary config-file (login+password) client
there is no bearer token and `access: http` fails with a clear error. See the
`_http_input_transport` design note for details and current limitations.

The generic `file` input also accepts an HTTP source, always fetched anonymously (the bearer token is
only ever sent to storage-derived URLs):

```yaml
inputs:
  - type: file
    source:
      http:
        url: https://example.org/data/reference.fasta
    filename: reference.fasta
    checksum: <md5>     # optional; verified after download
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
    inputs=[
        BfabricDatasetSpec(type='bfabric_dataset', id=53706, filename='test.csv', separator=',', format='csv'),
        BfabricResourceSpec(type='bfabric_resource', id=2700958, filename='test.zip', check_checksum=True, access='ssh')
    ]
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

The file parses into an `InputsSpec` wrapping a list of typed entries; each entry's `type` field
selects one of the models below.

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs_spec.InputsSpec
```

### B-Fabric-sourced inputs

Fetched from B-Fabric by ID.

Download a single resource by ID:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_spec.BfabricResourceSpec
```

Download a dataset as CSV or Parquet:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_dataset_spec.BfabricDatasetSpec
```

Download a resource that is an archive and extract it (with include/exclude globs):

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec.BfabricResourceArchiveSpec
```

Download every resource referenced by a dataset into a folder, plus a metadata table:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_dataset.BfabricResourceDatasetSpec
```

Write the FASTA sequence attached to an order (or a workunit's order) to a file:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec.BfabricOrderFastaSpec
```

Write a B-Fabric annotation table (e.g. resource-sample mapping) to a file:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_annotation_spec.BfabricAnnotationSpec
```

### Local / generic inputs

Sourced from a path, URL, or inline content rather than by B-Fabric ID.

A generic file from a local path, an SSH host, or an HTTP URL:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.file_spec.FileSpec
```

Write inline text or binary content straight to a file:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.static_file_spec.StaticFileSpec
```

Write an inline YAML document straight to a file:

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.static_yaml_spec.StaticYamlSpec
```
