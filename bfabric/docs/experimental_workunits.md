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

## WorkunitDefinition Structure

A `WorkunitDefinition` contains two main parts:

### Execution Definition

Defines how to execute a workunit:

- **`raw_parameters`**: Parameters to pass to the application (strings)
- **`dataset`**: Input dataset ID (for dataset-flow applications)
- **`resources`**: List of input resource IDs (for resource-flow applications)

```{note}
Exactly one of `dataset` or `resources` must be provided, not both.
```

### Registration Definition

Defines how to register a workunit in B-Fabric:

- **`application_id`**: ID of the executing application
- **`application_name`**: Name of the application
- **`workunit_id`**: Workunit ID
- **`workunit_name`**: Workunit name
- **`container_id`**: Container ID (project or order)
- **`container_type`**: Container type ("project" or "order")
- **`storage_id`**: Storage ID
- **`storage_output_folder`**: Output folder path in storage
- **`user_id`**: ID of user who created the workunit (optional)

## Loading from YAML

### Define Workunit in YAML

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

### Load from YAML File

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

### Load with Caching

Cache the loaded definition to avoid repeated queries:

```python
cache_file = Path("cache/workunit_def.yml")

# Loads from cache if available, otherwise queries B-Fabric
workunit_def = WorkunitDefinition.from_ref(
    workunit=Path("workunit.yml"), client=client, cache_file=cache_file
)
```

### Load from Existing Workunit

Load definition from a workunit already in B-Fabric:

```python
from bfabric import Bfabric
from bfabric import Workunit  # Note: need to import the entity class

client = Bfabric.connect()

# Get workunit from B-Fabric
workunit = Workunit.find(id=200, client=client)

# Convert to definition
workunit_def = WorkunitDefinition.from_workunit(workunit=workunit)
print(f"Loaded definition for workunit #{workunit.id}")
```

## Exporting to YAML

### Save Definition to File

Export a workunit definition to YAML:

```python
from pathlib import Path
from bfabric import Bfabric
from bfabric import Workunit

client = Bfabric.connect()

# Get workunit from B-Fabric
workunit = Workunit.find(id=200, client=client)
workunit_def = WorkunitDefinition.from_workunit(workunit=workunit)

# Save to YAML
output_file = Path("definitions/workunit_200.yml")
workunit_def.to_yaml(output_file)
print(f"Saved definition to {output_file}")
```

## Validations

The workunit definition system performs several automatic validions:

### Execution Validations

- **Either `dataset` or `resources` must be provided**: Not both, not neither

```python
# This will raise ValueError
invalid_def = WorkunitDefinition(
    execution=WorkunitExecutionDefinition(
        dataset=None, resources=[], raw_parameters={}  # Neither provided
    ),
    registration=registration_def,
)
```

```python
# This will raise ValueError
invalid_def = WorkunitDefinition(
    execution=WorkunitExecutionDefinition(
        dataset=123, resources=[1, 2, 3], raw_parameters={}  # Both provided
    ),
    registration=registration_def,
)
```

### Registration Validations

The registration definition ensures all required fields are provided.

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

# 1. Load definition from YAML
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

## Use Cases

### Application Development

Define workunit parameters alongside application code:

```yaml
# my_application_workunit.yml
execution:
  dataset: null
  resources: [1, 2, 3]
  raw_parameters:
    mode: "production"
    timeout: "3600"

registration:
  application_id: 100
  application_name: "MyApp"
  workunit_id: 200
  workunit_name: "StandardRun"
  container_id: 300
  container_type: "project"
  storage_id: 400
  storage_output_folder: "results"
```

### Testing

Load and validate workunit definitions before execution:

```python
from bfabric.experimental.workunit_definition import WorkunitDefinition

try:
    workunit_def = WorkunitDefinition.from_yaml(path=Path("test_workunit.yml"))
    print("Definition is valid!")
except ValueError as e:
    print(f"Invalid definition: {e}")
```

### Workflow Automation

Chain workunit definitions in a pipeline:

```python
# Load multiple workunit definitions
defs = [
    WorkunitDefinition.from_ref(Path("step1.yml"), client=client),
    WorkunitDefinition.from_ref(Path("step2.yml"), client=client),
    WorkunitDefinition.from_ref(Path("step3.yml"), client=client),
]

# Process each definition
for i, workunit_def in enumerate(defs, 1):
    print(f"Step {i}: {workunit_def.registration.workunit_name}")
    # Execute workunit using this definition
    # ...
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
