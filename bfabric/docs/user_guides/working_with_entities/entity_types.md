# Entity Reference

This page provides a complete reference for all B-Fabric entity types. Each entity type is a Python class that represents a B-Fabric object, with specific features and relationships.

## Available Entity Types

The following entity types are available in bfabricPy:

| Entity                   | Description              | Special Features                                                         |
| ------------------------ | ------------------------ | ------------------------------------------------------------------------ |
| **Project**              | Top-level project entity | Container for samples and workunits                                      |
| **Sample**               | Sample within a project  | Has container relationship (Project/Order)                               |
| **Workunit**             | Workunit/job entity      | Rich parameter access, output folder calculation, multiple relationships |
| **Dataset**              | Dataset entity           | DataFrame conversion, export methods, column access                      |
| **Application**          | Application definition   | Technology folder name, storage/executable relationships                 |
| **Executable**           | Executable binary/script | Base64 decoding, parameter definitions                                   |
| **ExternalJob**          | External job reference   | Client entity resolution, workunit association                           |
| **Resource**             | File resource            | Path methods, storage/sample/workunit relationships                      |
| **Storage**              | Storage location         | Base path, SCP prefix                                                    |
| **Parameter**            | Workunit parameter       | Key-value access with special handling for optional values               |
| **User**                 | User entity              | Login-based lookup                                                       |
| **Order**                | Order entity             | Optional project relationship                                            |
| **Workflow**             | Workflow definition      | Workflow steps, template association                                     |
| **WorkflowStep**         | Individual workflow step | Container relationship                                                   |
| **WorkflowTemplate**     | Workflow template        | Template steps definition                                                |
| **WorkflowTemplateStep** | Template step            | Template association                                                     |
| **Plate**                | Plate entity             | Basic entity                                                             |
| **Run**                  | Run entity               | Basic entity                                                             |
| **Instrument**           | Instrument entity        | Basic entity                                                             |
| **MultiplexKit**         | Multiplex kit            | Filtered multiplex IDs                                                   |
| **MultiplexId**          | Multiplex ID             | Basic entity                                                             |

## Entity Base Class

All entities inherit from the `Entity` base class, which provides common functionality:

```{eval-rst}
.. autoclass:: bfabric.entities.core.entity.Entity
    :members:
    :undoc-members:
    :show-inheritance:
```

## Entity Types

### Dataset

Dataset entity with rich data access and export capabilities:

```{eval-rst}
.. autoclass:: bfabric.entities.dataset.Dataset
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Working with Datasets

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a dataset
dataset = reader.read_id(entity_type="dataset", entity_id=12345)

# Get column names and types
print(f"Columns: {dataset.column_names}")
print(f"Types: {dataset.column_types}")

# Convert to Polars DataFrame
df = dataset.to_polars()
print(df)

# Export to CSV
dataset.write_csv("/path/to/output.csv")

# Export to Parquet
dataset.write_parquet("/path/to/output.parquet")

# Get CSV string
csv_string = dataset.get_csv(separator=",")
```

### Workunit

Workunit entity with parameter access and output path calculation:

```{eval-rst}
.. autoclass:: bfabric.entities.workunit.Workunit
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Accessing Workunit Parameters

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a workunit
workunit = reader.read_id(entity_type="workunit", entity_id=123)

# Access parameters by context
app_params = workunit.application_parameters
submitter_params = workunit.submitter_parameters
workunit_params = workunit.workunit_parameters

print(f"Application parameters: {app_params}")
print(f"Submitter parameters: {submitter_params}")

# Calculate output folder
output_folder = workunit.store_output_folder
print(f"Output folder: {output_folder}")
```

### Application

Application entity with technology information:

```{eval-rst}
.. autoclass:: bfabric.entities.application.Application
    :members:
    :undoc-members:
    :show-inheritance:
```

### Executable

Executable entity with base64 decoding:

```{eval-rst}
.. autoclass:: bfabric.entities.executable.Executable
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Decoding Executable Content

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read an executable
executable = reader.read_id(entity_type="executable", entity_id=456)

# Get decoded content as string
if executable.decoded_str:
    print(f"Executable content (first 100 chars): {executable.decoded_str[:100]}")

# Get decoded content as bytes
if executable.decoded_bytes:
    print(f"Executable size: {len(executable.decoded_bytes)} bytes")
```

### ExternalJob

External job with client entity resolution:

```{eval-rst}
.. autoclass:: bfabric.entities.externaljob.ExternalJob
    :members:
    :undoc-members:
    :show-inheritance:
```

### Resource

Resource entity with path methods:

```{eval-rst}
.. autoclass:: bfabric.entities.resource.Resource
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Accessing Resource Paths

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a resource
resource = reader.read_id(entity_type="resource", entity_id=789)

# Get relative and absolute paths
print(f"Relative path: {resource.storage_relative_path}")
print(f"Absolute path: {resource.storage_absolute_path}")
print(f"Filename: {resource.filename}")
```

### Storage

Storage location entity:

```{eval-rst}
.. autoclass:: bfabric.entities.storage.Storage
    :members:
    :undoc-members:
    :show-inheritance:
```

### Parameter

Parameter entity with key-value access:

```{eval-rst}
.. autoclass:: bfabric.entities.parameter.Parameter
    :members:
    :undoc-members:
    :show-inheritance:
```

### User

User entity with login-based lookup:

```{eval-rst}
.. autoclass:: bfabric.entities.user.User
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Finding Users

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Find user by login
user = User.find_by_login(login="myusername", client=client)
if user:
    print(f"Found user: {user.id}")
else:
    print("User not found")

# Or use EntityReader
user = reader.query(entity_type="user", obj={"login": "myusername"}, max_results=1)
if user:
    user_uri = list(user.keys())[0]
    found_user = user[user_uri]
    print(f"User ID: {found_user.id}")
```

### MultiplexKit

Multiplex kit with filtered IDs:

```{eval-rst}
.. autoclass:: bfabric.entities.multiplexkit.MultiplexKit
    :members:
    :undoc-members:
    :show-inheritance:
```

#### Example: Accessing Multiplex Information

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a multiplex kit
kit = reader.read_id(entity_type="multiplexkit", entity_id=123)

# Get enabled IDs as DataFrame
ids_df = kit.ids
print(ids_df)
```

## Relationship Descriptors

Entities use `HasOne` and `HasMany` descriptors to define relationships:

```{eval-rst}
.. autoclass:: bfabric.entities.core.has_one.HasOne
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.core.has_many.HasMany
    :members:
    :show-inheritance:
```

### Example: Using Relationships

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a workunit
workunit = reader.read_id(entity_type="workunit", entity_id=123)

# Access HasOne relationship (returns entity or None)
application = workunit.application
if application:
    print(f"Application: {application['name']}")

# Access HasMany relationship (returns _HasManyProxy)
parameters = workunit.parameters

# Get all parameters as a list
param_list = parameters.list
print(f"Number of parameters: {len(param_list)}")

# Get parameter IDs
param_ids = parameters.ids
print(f"Parameter IDs: {param_ids}")

# Convert to Polars DataFrame
params_df = parameters.polars
print(params_df)

# Iterate over parameters
for param in parameters:
    print(f"  {param.key}: {param.value}")

# Access by index
first_param = parameters[0]
```

### Optional vs Required Relationships

Relationships can be marked as optional:

```python
# Required relationship (will raise ValueError if missing)
class Workunit(Entity):
    application: HasOne[Application] = HasOne(bfabric_field="application")
    # This will raise ValueError if the application reference is missing


# Optional relationship (returns None if missing)
class Workunit(Entity):
    container: HasOne[Order | Project] = HasOne(
        bfabric_field="container", optional=True
    )
    # This returns None if the container reference is missing
```

## UserCreatedMixin

Entities that track creation and modification information inherit from `UserCreatedMixin`:

```{eval-rst}
.. autoclass:: bfabric.entities.core.mixins.user_created_mixin.UserCreatedMixin
    :members:
    :show-inheritance:
```

Entities with this mixin: `Workunit`, `Workflow`, `WorkflowStep`, `WorkflowTemplate`, `WorkflowTemplateStep`

#### Example: Accessing Creation Information

```python
from bfabric import Bfabric

client = Bfabric.connect()
reader = client.reader

# Read a workunit
workunit = reader.read_id(entity_type="workunit", entity_id=123)

print(f"Created at: {workunit.created_at}")
print(f"Modified at: {workunit.modified_at}")
print(f"Created by: {workunit.created_by['login']}")
print(f"Modified by: {workunit.modified_by['login']}")
```

## Additional Entity Types

Basic entity types without special features:

```{eval-rst}
.. autoclass:: bfabric.entities.project.Project
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.sample.Sample
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.order.Order
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.workflow.Workflow
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.workflowstep.WorkflowStep
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.workflowtemplate.WorkflowTemplate
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.workflowtemplatestep.WorkflowTemplateStep
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.plate.Plate
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.run.Run
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.instrument.Instrument
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.multiplexid.MultiplexId
    :members:
    :show-inheritance:
```

## EntityReader Reference

```{eval-rst}
.. autoclass:: bfabric.entities.core.entity_reader.EntityReader
    :members:
    :show-inheritance:
```

## References Manager

```{eval-rst}
.. autoclass:: bfabric.entities.core.references.References
    :members:
    :show-inheritance:
```

## Entity URI

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.EntityUri
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.EntityUriComponents
    :members:
    :show-inheritance:
```

```{eval-rst}
.. autoclass:: bfabric.entities.core.uri.GroupedUris
    :members:
    :show-inheritance:
```
