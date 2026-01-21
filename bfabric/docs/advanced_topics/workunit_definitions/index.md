# Experimental: Workunit Definitions

This guide covers the experimental workunit definition system for defining and managing B-Fabric workunits
using YAML files.

```{warning}
Experimental features may change or be removed in future versions. Use at your own risk.
```

## Overview

Workunit definitions provide a structured way to define workunit execution details and registration information. This is
particularly useful for:

- Developing and testing B-Fabric applications
- Defining workflow parameters in a declarative way
- Persisting workunit configurations in version-controlled YAML files
- Separating workunit logic from execution code

## API Reference

### WorkunitExecutionDefinition

```{eval-rst}
.. autoclass:: bfabric.experimental.workunit_definition.WorkunitExecutionDefinition
    :members:
    :show-inheritance:
```

### WorkunitRegistrationDefinition

```{eval-rst}
.. autoclass:: bfabric.experimental.workunit_definition.WorkunitRegistrationDefinition
    :members:
    :show-inheritance:
```

### WorkunitDefinition

```{eval-rst}
.. autoclass:: bfabric.experimental.workunit_definition.WorkunitDefinition
    :members:
    :show-inheritance:
```

## Loading Workunit Definitions

### From YAML File

Create a YAML file with workunit definition:

```yaml
# workunit.yml

execution:
  dataset: 12345
  raw_parameters:
    param1: "value1"
    param2: "value2"

registration:
  application_id: 100
  application_name: "MyApplication"
  workunit_id: 200
  workunit_name: "ProcessingJob"
  container_id: 300
  container_type: "project"
  storage_id: 400
  storage_output_folder: "output/results"
  user_id: 1
```

Load it in Python:

```python
from pathlib import Path
from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition

client = Bfabric.connect()

# Load from YAML file
workunit_def = WorkunitDefinition.from_ref(workunit=Path("workunit.yml"), client=client)

print(f"Workunit: {workunit_def.workunit_name}")
print(f"Application: {workunit_def.registration.application_name}")
print(f"Dataset: {workunit_def.execution.dataset}")
```

### From Workunit ID

Load definition from a workunit already in B-Fabric:

```python
from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition

client = Bfabric.connect()

# Load from workunit ID (resolves from B-Fabric)
workunit_def = WorkunitDefinition.from_ref(workunit=200, client=client)
print(f"Loaded definition for workunit #{workunit_def.registration.workunit_id}")
```

### With Caching

Cache the loaded definition to avoid repeated queries:

```python
cache_file = Path("cache/workunit_def.yml")

# Loads from cache if available, otherwise queries B-Fabric
workunit_def = WorkunitDefinition.from_ref(
    workunit=Path("workunit.yml"), client=client, cache_file=cache_file
)
```

## Exporting Workunit Definitions

Export a workunit definition to YAML:

```python
from pathlib import Path
from bfabric import Bfabric

client = Bfabric.connect()

# Load from workunit ID
workunit_def = WorkunitDefinition.from_ref(workunit=200, client=client)

# Save to YAML
output_file = Path("definitions/workunit_200.yml")
workunit_def.to_yaml(output_file)
print(f"Saved definition to {output_file}")
```

## Complete Example

### YAML Definition File

```yaml
# proteomics_analysis.yml

execution:
  dataset: 12345
  raw_parameters:
    fdr_threshold: "0.01"
    min_peptide_length: "7"
    database: "uniprot_human"

registration:
  application_id: 100
  application_name: "ProteomicsProcessor"
  workunit_id: 200
  workunit_name: "ProteomicsAnalysis"
  container_id: 300
  container_type: "project"
  storage_id: 400
  storage_output_folder: "proteomics/output"
  user_id: 1
```

### Python Usage

```python
from pathlib import Path
from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition

client = Bfabric.connect()

# 1. Load definition from YAML with caching
yaml_file = Path("workunits/proteomics_analysis.yml")
workunit_def = WorkunitDefinition.from_ref(
    workunit=yaml_file, client=client, cache_file=Path("cache/workunit_defs.yml")
)

# 2. Access components
execution = workunit_def.execution
registration = workunit_def.registration

print(f"Workunit: {registration.workunit_name}")
print(f"Application: {registration.application_name}")
print(f"Input Dataset: {execution.dataset}")
print(f"Parameters: {execution.raw_parameters}")

# 3. Export definition (e.g., for version control)
output_file = Path("definitions/proteomics_analysis_export.yml")
workunit_def.to_yaml(output_file)
```

## Best Practices

1. **Version control YAML files**: Keep workunit definitions in git
2. **Use caching**: Load definitions with `cache_file` to avoid repeated API calls
3. **Validate early**: Catch validation errors before execution
4. **Document parameters**: Use descriptive parameter names in `raw_parameters`
5. **Separate concerns**: Keep application logic separate from workunit definitions

## Next Steps

- {doc}`write_data` - Basic save and delete operations
- {doc}`experimental_data` - Dataset upload and custom attributes
