# API Reference

Complete API documentation for bfabric-app-runner classes and modules.

## Documentation Style

This section uses **auto-generated documentation** directly from the Python code using Sphinx
autodoc and autodoc_pydantic extensions.

## App Specification

The app specification defines application versions, commands, and B-Fabric integration metadata.

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app.app_spec
    :members:
    :undoc-members:
    :show-inheritance:

.. autopydantic_model:: bfabric_app_runner.specs.app.app_spec.AppSpec
.. autopydantic_model:: bfabric_app_runner.specs.app.app_spec.BfabricAppSpec
.. autopydantic_model:: bfabric_app_runner.specs.app.app_spec.AppSpecTemplate
```

### App Versions

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app.app_version
    :members:
    :undoc-members:
    :show-inheritance:

.. autopydantic_model:: bfabric_app_runner.specs.app.app_version.AppVersion
.. autopydantic_model:: bfabric_app_runner.specs.app.app_version.AppVersionMultiTemplate
```

### Commands

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.app.commands_spec
    :members:
    :undoc-members:
    :show-inheritance:

.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandsSpec
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandShell
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandExec
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandDocker
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.CommandPythonEnv
.. autopydantic_model:: bfabric_app_runner.specs.app.commands_spec.MountOptions
```

## Input Specifications

Input specs define how to retrieve and prepare input files for processing.

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.inputs_spec
    :members:
    :undoc-members:
    :show-inheritance:
```

### Input Types

```{eval-rst}
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_spec.BfabricResourceSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_dataset_spec.BfabricDatasetSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_archive_spec.BfabricResourceArchiveSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_resource_dataset.BfabricResourceDatasetSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_order_fasta_spec.BfabricOrderFastaSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.bfabric_annotation_spec.BfabricAnnotationSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.file_spec.FileSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.static_file_spec.StaticFileSpec
.. autopydantic_model:: bfabric_app_runner.specs.inputs.static_yaml_spec.StaticYamlSpec
```

## Output Specifications

Output specs define how to register processing results back into B-Fabric.

```{eval-rst}
.. automodule:: bfabric_app_runner.specs.outputs_spec
    :members:
    :undoc-members:
    :show-inheritance:

.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.CopyResourceSpec
.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.SaveDatasetSpec
.. autopydantic_model:: bfabric_app_runner.specs.outputs_spec.SaveLinkSpec
```

## Runner

The runner orchestrates the full application execution lifecycle.

```{eval-rst}
.. automodule:: bfabric_app_runner.app_runner.runner
    :members:
    :undoc-members:
    :show-inheritance:
```
